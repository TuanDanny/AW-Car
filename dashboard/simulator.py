"""Local-only UI/contract simulator. Reuses compiled ControlCore; no ESP emulation."""

from __future__ import annotations
import argparse
import asyncio
import json
from pathlib import Path
import secrets
import sys
import time
from collections import deque
import ctypes
import os

from aiohttp import web, WSMsgType

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from brain_simulator import Rig

RESULTS = ["OK", "UNSAFE", "BUSY", "BAD_RANGE", "BAD_SEQUENCE", "STALE", "WRONG_MODE"]
ACTIONS = ["forward", "backward", "left", "right", "spin_left", "spin_right"]


def integer(data, key, lo, hi):
    v = data.get(key)
    if type(v) is not int or not lo <= v <= hi:
        raise ValueError(key)
    return v


class Simulator:
    def __init__(self, pin, *, realtime=True):
        self.realtime = realtime
        self.rig = Rig()
        self.ws = None
        self.token = secrets.token_urlsafe(32)
        self.pin = pin
        self.rgb = {"power": False, "r": 32, "g": 32, "b": 32}
        self.events = []
        self.origin = None
        self.clock = time.monotonic_ns() // 1000
        self.offset = 0
        self.last_ws = 0
        self.rig.brain.command(3, 0, 1)
        self.rig.pump()
        self.commands = 0
        self.latencies = deque(maxlen=40000)
        self.rejected = 0
        self.voice_id = 0
        self.voice_epoch = 0
        self.move_received = {}
        self.tx_seen = 0
        self.started = time.monotonic()
        self.max_event_depth = 0
        self.memory_samples = deque(maxlen=400)
        self.last_memory = 0
        self.direction_counts = {}

    def event(self, kind, text):
        self.events.append({"type": "EVENT", "kind": kind, "text": str(text)[:512]})
        self.events = self.events[-100:]
        self.max_event_depth = max(self.max_event_depth, len(self.events))

    def auth(self, req):
        return secrets.compare_digest(req.cookies.get("awcar", ""), self.token)

    async def login(self, req):
        if self.ws and not self.ws.closed:
            return web.json_response({"error": "BUSY"}, status=409)
        try:
            d = await req.json()
        except Exception:
            return web.Response(status=400)
        if not secrets.compare_digest(str(d.get("pin", "")), self.pin):
            return web.Response(status=403)
        r = web.json_response({"ok": True})
        r.set_cookie("awcar", self.token, httponly=True, samesite="Strict")
        return r

    async def pairing(self, req):
        return web.json_response({"hint": "PIN is printed in simulator terminal"})

    async def wifi(self, req):
        if not self.auth(req):
            return web.Response(status=403)
        if self.rig.state["authorized"] or self.rig.state["motion_state"] != 0:
            return web.Response(status=409)
        return web.json_response({"ok": True, "simulated": True})

    async def snapshot(self):
        s = self.rig.state
        return {
            "type": "STATUS",
            **s,
            "data_source": "mock",
            "v_max": 200,
            "omega_max": 1000,
            "rgb": self.rgb,
            "chat_state": "Xiaozhi giả lập · tool được tiêm để kiểm thử",
        }

    async def socket(self, req):
        if not self.auth(req):
            return web.Response(status=403)
        if req.headers.get("Origin") != f"http://{req.host}":
            return web.Response(status=403)
        if self.ws and not self.ws.closed:
            return web.Response(status=409)
        ws = web.WebSocketResponse(max_msg_size=512, heartbeat=5)
        # Reserve before prepare's first await: two concurrent upgrades cannot both win.
        self.ws = ws
        try:
            await ws.prepare(req)
            self.last_ws = self.rig.now
            self.rig.connect()
            await ws.send_json(await self.snapshot())
            async for msg in ws:
                if msg.type != WSMsgType.TEXT:
                    continue
                started = time.monotonic_ns()
                try:
                    d = json.loads(msg.data)
                    if not isinstance(d, dict) or len(msg.data.encode()) > 512:
                        raise ValueError("object/length")
                    kind = d.get("type")
                    s = self.rig.state
                    now = self.rig.now
                    result = 0
                    if kind == "STOP":
                        self.rig.brain.command(6, now)
                    elif kind == "HEARTBEAT":
                        self.last_ws = now
                    elif kind == "SET_MODE":
                        if d.get("mode") not in ("Manual", "AI"):
                            raise ValueError("mode")
                        if integer(d, "epoch", 0, 0xFFFFFFFF) != s["epoch"]:
                            result = 5
                        else:
                            result = self.rig.brain.command(
                                4, now, int(d["mode"] == "AI")
                            )
                    elif kind == "ARM":
                        result = self.rig.brain.command(
                            5, now, integer(d, "epoch", 0, 0xFFFFFFFF)
                        )
                    elif kind == "MOVE":
                        if type(d.get("deadman")) is not bool:
                            raise ValueError("deadman")
                        result = self.rig.move(
                            integer(d, "seq", 0, 0xFFFFFFFF),
                            integer(d, "v_mm_s", -32768, 32767),
                            integer(d, "omega_mrad_s", -32768, 32767),
                            d["deadman"],
                            integer(d, "ttl_ms", 1, 250),
                            integer(d, "epoch", 0, 0xFFFFFFFF),
                            integer(d, "challenge", 1, 0xFFFFFFFF),
                        )
                        self.commands += 1
                        if result == 0:
                            self.last_ws = now
                            # Commit to UART immediately, independently of next STATUS.
                            before = self.rig.motion.total_frames
                            self.rig.pump()
                            if self.rig.motion.total_frames > before:
                                self.latencies.append(
                                    (time.monotonic_ns() - started) / 1e6
                                )
                            key = f"{d['v_mm_s']},{d['omega_mrad_s']}"
                            self.direction_counts[key] = (
                                self.direction_counts.get(key, 0) + 1
                            )
                    elif kind == "RGB":
                        if "on" in d:
                            if type(d["on"]) is not bool:
                                raise ValueError("on")
                            self.rgb["power"] = d["on"]
                        else:
                            self.rgb = {
                                k: integer(d, k, 0, 255) for k in ("r", "g", "b")
                            }
                            self.rgb["power"] = True
                        self.event("rgb", json.dumps(self.rgb))
                    elif kind == "CHAT_TOGGLE":
                        self.event("stt", "你好，小智")
                        self.event("reply", "你好！这是模拟对话。")
                    else:
                        raise ValueError("type")
                    if result:
                        self.rejected += 1
                    self.rig.pump()
                    await ws.send_json(
                        {
                            "type": "ACK",
                            "last_seq": d.get("seq"),
                            "result": RESULTS[result],
                            "stage": "Brain",
                        }
                    )
                    if kind in ("ARM", "STOP", "SET_MODE"):
                        await ws.send_json(await self.snapshot())
                except (ValueError, TypeError, KeyError, json.JSONDecodeError):
                    self.rejected += 1
                    await ws.send_json(
                        {"type": "ACK", "result": "BAD_RANGE", "stage": "Brain"}
                    )
        finally:
            if self.ws is ws:
                self.ws = None
                self.rig.brain.command(2, self.rig.now)
                self.rig.pump()
        return ws

    async def lab(self, req):
        if not self.auth(req):
            return web.Response(status=403)
        d = await req.json()
        op = d.get("op")
        now = self.rig.now
        result = 0
        if op == "voice":
            action = ACTIONS.index(d.get("action", "forward"))
            epoch = d.get("epoch", self.rig.state["epoch"])
            current = self.rig.state["epoch"]
            sid = f"mock-conversation-{current}"
            if self.voice_epoch != current:
                self.rig.brain.gate(0, now, 1, sid)
                self.voice_epoch = current
            self.voice_id += 1
            self.rig.brain.gate(1, now, self.voice_id, sid)
            valid = self.rig.brain.gate(
                2, now, self.voice_id, sid
            ) and self.rig.brain.gate(3, now, self.voice_id, sid)
            self.event("stt", d.get("text", "前进一秒"))
            self.event("tool", f"self.car.move {d.get('action', 'forward')}")
            result = (
                self.rig.brain.command(
                    8, now, epoch, action, d.get("pct", 30), d.get("duration_ms", 1000)
                )
                if valid
                else 5
            )
            self.event("tool_result", RESULTS[result])
        elif op == "ai_online":
            self.rig.brain.command(3, now, int(bool(d["online"])))
        elif op == "motion_online":
            self.rig.motion.online = bool(d["online"])
        elif op == "advance":
            self.offset += integer(d, "ms", 0, 300001) * 1000
            self.rig.advance(d["ms"] * 1000)
        else:
            return web.Response(status=400)
        self.rig.pump()
        return web.json_response({"result": RESULTS[result], **self.rig.state})

    async def report(self, req):
        if not self.auth(req):
            return web.Response(status=403)
        a = sorted(self.latencies)

        def p(q):
            return a[min(len(a) - 1, int((len(a) - 1) * q))] if a else None

        return web.json_response(
            {
                "environment": "host_cpp_core_motion_mock",
                "seconds": time.monotonic() - self.started,
                "commands": self.commands,
                "samples": len(a),
                "latency_ms": {
                    "p50": p(0.5),
                    "p95": p(0.95),
                    "p99": p(0.99),
                    "max": p(1),
                },
                "rejected": self.rejected,
                "events_bound": 100,
                "events_peak": self.max_event_depth,
                "tx_queue_bound": 1,
                "motion_trace_capacity": 256,
                "motion_trace_size": len(self.rig.motion.frames),
                "latency_buffer_capacity": 40000,
                "direction_counts": self.direction_counts,
                "memory_samples": list(self.memory_samples),
                "virtual_time_offset_us": self.offset,
            }
        )

    async def loop(self, app):
        async def run():
            next_send = 0
            alternate = False
            while True:
                now = (
                    time.monotonic_ns() // 1000 - self.clock + self.offset
                    if self.realtime
                    else self.rig.now
                )
                if now - self.last_memory >= 5000000:
                    self.last_memory = now
                    if os.name == "nt":

                        class Memory(ctypes.Structure):
                            _fields_ = [
                                ("cb", ctypes.c_ulong),
                                ("faults", ctypes.c_ulong),
                            ] + [
                                (n, ctypes.c_size_t)
                                for n in (
                                    "peak_working",
                                    "working",
                                    "peak_paged",
                                    "paged",
                                    "peak_nonpaged",
                                    "nonpaged",
                                    "pagefile",
                                    "peak_pagefile",
                                )
                            ]

                        m = Memory()
                        m.cb = ctypes.sizeof(m)
                        # HANDLE is pointer-sized. An untyped ctypes integer
                        # truncates the Win64 pseudo-handle and returns zeros.
                        ok = ctypes.windll.psapi.GetProcessMemoryInfo(
                            ctypes.c_void_p(-1), ctypes.byref(m), m.cb
                        )
                        rss = m.working if ok else None
                    else:
                        import resource

                        rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024
                    self.memory_samples.append(
                        [round(time.monotonic() - self.started, 1), rss]
                    )
                self.rig.pump(max(0, now - self.rig.now))
                ws = self.ws
                if ws and not ws.closed:
                    if self.rig.now - self.last_ws >= 150000:
                        if (
                            self.rig.state["mode"] == "Manual"
                            and self.rig.state["authorized"]
                        ):
                            self.rig.brain.command(6, self.rig.now)
                    send_now = time.monotonic_ns() // 1000
                    if send_now >= next_send:
                        alternate = not alternate
                        next_send = send_now + 50000
                        try:
                            await asyncio.wait_for(
                                ws.send_json(
                                    await self.snapshot()
                                    if alternate
                                    else {
                                        "type": "CHALLENGE",
                                        "epoch": self.rig.state["epoch"],
                                        "challenge": self.rig.state["challenge"],
                                    }
                                ),
                                0.05,
                            )
                            while self.events:
                                await asyncio.wait_for(
                                    ws.send_json(self.events.pop(0)), 0.05
                                )
                        except (ConnectionError, asyncio.TimeoutError, RuntimeError):
                            await ws.close()
                await asyncio.sleep(0.005)

        task = asyncio.create_task(run())
        yield
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    def app(self):
        app = web.Application(client_max_size=512)
        app.router.add_post("/api/login", self.login)
        app.router.add_post("/api/pairing", self.pairing)
        app.router.add_post("/api/wifi", self.wifi)
        app.router.add_get("/ws", self.socket)
        app.router.add_post("/api/lab", self.lab)
        app.router.add_get("/api/report", self.report)
        for name in ("index.html", "style.css", "app.mjs", "control.mjs"):

            async def asset(req, name=name):
                return web.FileResponse(Path(__file__).parent / name)

            app.router.add_get("/" if name == "index.html" else "/" + name, asset)
        app.cleanup_ctx.append(self.loop)
        return app


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--port", type=int, default=8765)
    p.add_argument("--pin", default="123456")
    args = p.parse_args()
    print("LOCAL SIMULATOR ONLY. PIN:", args.pin, flush=True)
    web.run_app(Simulator(args.pin).app(), host="127.0.0.1", port=args.port, print=None)
