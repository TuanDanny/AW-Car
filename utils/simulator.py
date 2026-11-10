"""Local browser simulator using the exact C++ Control compiled for Motion.

No serial, Wi-Fi reconfiguration or hardware writes. /sim/* only exists on localhost.
"""
from __future__ import annotations
import argparse
import asyncio
import contextlib
import ctypes
import json
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "build/python_packages"))
from aiohttp import web, WSMsgType

ACTION = {"neutral": 0, "forward": 1, "backward": 2, "left": 3, "right": 4}

class Native:
    def __init__(self):
        from build_host import BUILD, build, compiler
        manifest = json.loads((BUILD / "manifest.json").read_text()) if (BUILD / "manifest.json").exists() else build()
        library = Path(manifest["library"])
        self.source_hash = manifest.get("source_sha256", "initial-native-build")
        self.dll_path = os.add_dll_directory(str(compiler().parent)) if os.name == "nt" else None
        self.dll = ctypes.CDLL(str(library))
        self.dll.car_create.argtypes = [ctypes.c_uint]
        self.dll.car_create.restype = ctypes.c_void_p
        self.dll.car_destroy.argtypes = [ctypes.c_void_p]
        self.dll.car_event.argtypes = [ctypes.c_void_p, *([ctypes.c_uint] * 5), ctypes.c_ulonglong]
        self.dll.car_event.restype = ctypes.c_int
        self.dll.car_state.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint, ctypes.c_ulonglong]
        self.pointer = self.dll.car_create(100)
        self.start = time.monotonic_ns()
        self.owner = None
        self.fpga = True
        self.brain = True
        self.flags = 3
        self.counts = [0, 0]
        self.commands = 0
        self.rejected = 0
        self.ssid = "Motion giả lập"
        self.wifi_result = 2
        self.spi_seq = 0

    def now(self):
        return (time.monotonic_ns() - self.start) // 1_000_000

    def event(self, kind, a=0, b=0, duration=0, generation=0):
        return bool(self.dll.car_event(self.pointer, kind, a, b, duration, generation, self.now()))

    def state(self):
        buffer = ctypes.create_string_buffer(1024)
        self.dll.car_state(self.pointer, buffer, len(buffer), self.now())
        s = json.loads(buffer.value)
        return {
            **s, "t": "status", "build": "simplev1-host-" + self.source_hash[:12], "simulator": True,
            "fpga": {"connected": s["fpga_connected"], "applied_seq": self.spi_seq,
                     "left_count": s["left_count"], "right_count": s["right_count"],
                     "left_seen": self.counts[0] > 0, "right_seen": self.counts[1] > 0},
            "brain": {"connected": s["brain_connected"], "wifi": bool(self.flags & 1) and self.brain,
                      "cloud": bool(self.flags & 2) and self.brain, "listening": bool(self.flags & 4),
                      "speaking": bool(self.flags & 8), "ssid": self.ssid, "ip": "127.0.0.1",
                      "wifi_result": self.wifi_result},
            "diag": {"uart_rx": 0, "uart_errors": 0, "spi_ok": self.spi_seq, "spi_errors": 0,
                     "latency_count": 0, "latency_p50_us": None, "latency_p95_us": None,
                     "latency_p99_us": None, "latency_max_us": None, "heap": None,
                     "uptime_ms": self.now(), "host_commands": self.commands, "rejected": self.rejected},
        }

    async def ticker(self):
        while True:
            if self.fpga:
                self.event(6, *self.counts)
                self.spi_seq = (self.spi_seq + 1) & 65535
            if self.brain:
                self.event(5, self.flags)
            self.event(0)
            await asyncio.sleep(.005)

    def command(self, obj):
        kind = obj.get("t")
        self.commands += 1
        if kind == "status":
            return self.state()
        if kind == "latency":
            ok = obj.get('action') in ACTION and type(obj.get('dispatch_us')) is int and type(obj.get('confirm_us')) is int and 0 <= obj['dispatch_us'] <= obj['confirm_us'] <= 2000000
            return {"t":"result","ok":ok,"reason":"received" if ok else "invalid_latency_sample"}
        ok = False
        if kind == "stop":
            ok = self.event(3, 2)
        elif kind == "neutral":
            ok = self.event(1, 0, 0)
        elif kind == "mode" and obj.get("mode") in ("manual", "ai"):
            ok = self.event(2, int(obj["mode"] == "ai"))
        elif kind == "drive" and obj.get("action") in ACTION and type(obj.get("speed")) is int and 0 <= obj["speed"] <= 100:
            ok = self.event(1, ACTION[obj["action"]], obj["speed"])
        elif kind == "listen" and type(obj.get("enabled")) is bool and self.brain:
            self.flags = (self.flags | 4) if obj["enabled"] else (self.flags & ~4)
            ok = True
        elif kind == "wifi" and self.brain and isinstance(obj.get("ssid"), str) and isinstance(obj.get("password"), str):
            n, p = len(obj["ssid"].encode()), len(obj["password"].encode())
            if 0 < n <= 32 and (p == 0 or 8 <= p <= 64):
                self.event(3, 2)
                self.ssid = obj["ssid"]
                self.wifi_result = 2
                ok = True
        if not ok:
            self.rejected += 1
        # Firmware consumes its input batch, then ticks, then publishes a
        # snapshot. Do not expose target()'s intermediate Released reason with
        # the previous live duty when a STATUS immediately follows a repeat.
        self.event(0)
        return {"t": "result", "ok": ok, "reason": "received" if ok else "rejected"}

async def app_context(app):
    native = app["native"]
    ticker = asyncio.create_task(native.ticker())
    yield
    ticker.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await ticker
    native.dll.car_destroy(native.pointer)

async def index(request):
    return web.Response(text=request.app['html'].read_text(encoding="utf-8"), content_type="text/html", headers={"Cache-Control": "no-store"})

async def latency_script(request):
    return web.Response(text=(ROOT/'esp/motion/web/latency.js').read_text(encoding='utf-8'),content_type='text/javascript')

async def websocket(request):
    native = request.app["native"]
    origin = request.headers.get("Origin", "")
    if origin != f"http://{request.host}":
        raise web.HTTPForbidden(text="origin_rejected")
    ws = web.WebSocketResponse(max_msg_size=512)
    await ws.prepare(request)
    old = native.owner
    native.owner = ws
    native.event(3, 8)
    if old is not None and not old.closed:
        await old.close(code=1001, message=b"controller_replaced")
    await ws.send_json(native.state())
    try:
        async for message in ws:
            if native.owner is not ws:
                break
            if message.type == WSMsgType.TEXT:
                try:
                    obj = json.loads(message.data)
                    reply = native.command(obj) if isinstance(obj, dict) else {"t": "result", "ok": False, "reason": "invalid_json"}
                except (ValueError, TypeError):
                    reply = {"t": "result", "ok": False, "reason": "invalid_json"}
                await ws.send_json(reply)
    finally:
        if native.owner is ws:
            native.owner = None
            native.event(4)
    return ws

async def sim_event(request):
    native = request.app["native"]
    obj = await request.json()
    kind = obj.get("event", obj.get("t"))
    ok = True
    if kind == "fpga":
        native.fpga = bool(obj.get("connected", True))
    elif kind == "brain":
        native.brain = bool(obj.get("connected", True))
        native.flags = int(obj.get("flags", native.flags)) & 15
    elif kind in ("ai", "move"):
        generation = int(obj.get("generation", native.state()["generation"]))
        ok = native.event(7, ACTION.get(obj.get("action"), 99), int(obj.get("speed", 30)), int(obj.get("duration_ms", 3000)), generation)
    elif kind == "counts":
        native.counts = [int(obj.get("left", 0)), int(obj.get("right", 0))]
    elif kind == "reset":
        generation = (native.state()["generation"] + 100) & 0xffffffff
        native.dll.car_destroy(native.pointer)
        native.pointer = native.dll.car_create(generation)
        native.fpga = native.brain = True
        native.flags = 3
        native.counts = [0, 0]
    elif kind == "stop":
        native.event(3, 2)
    elif kind == "maintenance":
        native.event(8, int(bool(obj.get("enabled", True))))
    else:
        ok = False
    return web.json_response({"ok": ok, "state": native.state()})

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8783)
    parser.add_argument('--html',type=Path,default=ROOT/'esp/motion/web/index.html',help='Host-only HTML fixture for baseline/candidate comparisons')
    args = parser.parse_args()
    app = web.Application(client_max_size=2048)
    app["native"] = Native()
    app['html'] = args.html.resolve(strict=True)
    app.cleanup_ctx.append(app_context)
    app.add_routes([web.get("/", index), web.get('/latency.js',latency_script), web.get("/ws", websocket), web.get("/sim/state", lambda r: web.json_response(r.app["native"].state())), web.post("/sim/event", sim_event)])
    web.run_app(app, host="127.0.0.1", port=args.port, print=print)

if __name__ == "__main__":
    main()
