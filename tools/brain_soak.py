"""Real elapsed-time WebSocket load, with separate host-only latency evidence."""

import argparse
import asyncio
import json
from pathlib import Path
import time
import tracemalloc
import aiohttp
from collections import deque


async def run(url, seconds, report):
    tracemalloc.start()
    start = time.monotonic()
    state = {}
    seq = 0
    sent = 0
    acks = 0
    rejected = {}
    errors = []
    peak_queue = 0
    waiting = {}
    rtts = deque(maxlen=40000)
    async with aiohttp.ClientSession(
        cookie_jar=aiohttp.CookieJar(unsafe=True)
    ) as session:
        r = await session.post(url + "/api/login", json={"pin": "123456"})
        r.raise_for_status()
        async with session.ws_connect(url + "/ws", origin=url) as ws:

            async def receive():
                nonlocal acks, state
                async for msg in ws:
                    if msg.type == aiohttp.WSMsgType.TEXT:
                        d = json.loads(msg.data)
                        if d["type"] == "STATUS":
                            state = d
                        elif d["type"] == "CHALLENGE":
                            if state.get("epoch") == d["epoch"]:
                                state["challenge"] = d["challenge"]
                        elif d["type"] == "ACK":
                            acks += 1
                            at = waiting.pop(d.get("last_seq"), None)
                            if at is not None:
                                rtts.append((time.monotonic_ns() - at) / 1e6)
                            if d["result"] != "OK":
                                rejected[d["result"]] = rejected.get(d["result"], 0) + 1

            task = asyncio.create_task(receive())
            while not state:
                await asyncio.sleep(0.005)
            seq += 1
            await ws.send_json({"type": "ARM", "seq": seq, "epoch": state["epoch"]})
            limit = time.monotonic() + 2
            while not state.get("authorized"):
                if time.monotonic() > limit:
                    raise RuntimeError("ARM not confirmed")
                await asyncio.sleep(0.005)
            start = time.monotonic()
            next_send = start
            while time.monotonic() - start < seconds:
                if not state.get("authorized"):
                    errors.append({"at": time.monotonic() - start, "state": state})
                    break
                seq += 1
                sent += 1
                waiting[seq] = time.monotonic_ns()
                peak_queue = max(peak_queue, len(waiting))
                v, w = [
                    (60, 0),
                    (-60, 0),
                    (60, 300),
                    (60, -300),
                    (0, 300),
                    (0, -300),
                    (0, 0),
                ][(sent // 20) % 7]
                await ws.send_json(
                    {
                        "type": "MOVE",
                        "seq": seq,
                        "epoch": state["epoch"],
                        "challenge": state["challenge"],
                        "v_mm_s": v,
                        "omega_mrad_s": w,
                        "ttl_ms": 120,
                        "deadman": bool(v or w),
                    }
                )
                next_send += 0.05
                await asyncio.sleep(max(0, next_send - time.monotonic()))
            seq += 1
            await ws.send_json({"type": "STOP", "seq": seq})
            await asyncio.sleep(0.2)
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        evidence = await (await session.get(url + "/api/report")).json()
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    ordered = sorted(rtts)

    def percentile(q):
        return (
            ordered[min(len(ordered) - 1, int((len(ordered) - 1) * q))]
            if ordered
            else None
        )

    evidence.update(
        {
            "actual_load_seconds": time.monotonic() - start,
            "sent": sent,
            "acks": acks,
            "rejections": rejected,
            "errors": errors,
            "load_python_memory_current": current,
            "load_python_memory_peak": peak,
            "ack_rtt_ms": {
                "p50": percentile(0.5),
                "p95": percentile(0.95),
                "p99": percentile(0.99),
                "max": percentile(1),
            },
            "requests_inflight_peak": peak_queue,
            "status": "passed"
            if not errors and sent >= int(seconds * 19) and not rejected
            else "failed",
        }
    )
    Path(report).write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(evidence), flush=True)
    if evidence["status"] != "passed":
        raise SystemExit(1)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--url", default="http://127.0.0.1:8766")
    p.add_argument("--seconds", type=int, default=1800)
    p.add_argument("--report", default="build/brain/soak.json")
    a = p.parse_args()
    asyncio.run(run(a.url, a.seconds, a.report))
