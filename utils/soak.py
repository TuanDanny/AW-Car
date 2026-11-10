"""30-minute WebSocket/native-core soak. Host measurements, never ESP timing."""
from __future__ import annotations
import argparse
import asyncio
from datetime import datetime, timezone
import json
from pathlib import Path
import statistics
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "build/python_packages"))
from aiohttp import ClientSession

async def run(seconds, port, output):
    begin = time.monotonic()
    results = []
    sent = errors = 0
    base = f"http://127.0.0.1:{port}"
    async with ClientSession() as session:
        async with session.post(base + "/sim/event", json={"event": "reset"}) as response:
            assert response.status == 200
        async with session.ws_connect(base + "/ws", origin=base, receive_timeout=3) as ws:
            await ws.receive_json()
            while time.monotonic() - begin < seconds:
                start = time.monotonic_ns()
                action = ["forward", "backward", "left", "right"][(sent // 100) % 4]
                speed = [0, 30, 100][(sent // 25) % 3]
                await ws.send_json({"t": "drive", "action": action, "speed": speed})
                reply = await ws.receive_json()
                sent += 1
                errors += not reply.get("ok", False)
                results.append((time.monotonic_ns() - start) / 1000)
                if sent % 200 == 0:
                    await ws.send_json({"t": "status"})
                    state = await ws.receive_json()
                    assert state["simulator"] and state["fpga"]["connected"]
                    print(f"host-soak elapsed={time.monotonic()-begin:.1f}s commands={sent} rejected={errors}", flush=True)
                await asyncio.sleep(max(0, .05 - (time.monotonic_ns() - start) / 1e9))
            await ws.send_json({"t": "stop"})
            assert (await ws.receive_json())["ok"]
            await ws.send_json({"t": "status"})
            final = await ws.receive_json()
    ordered = sorted(results)
    def p(q):
        return ordered[min(len(ordered)-1, max(0, int(len(ordered)*q+.999)-1))]
    report = {"at_utc": datetime.now(timezone.utc).isoformat(), "environment": "localhost WebSocket + real shared C++ Control; FPGA/Brain simulated",
              "duration_s": time.monotonic()-begin, "commands": sent, "rejected": errors,
              "host_command_ack_us": {"p50": statistics.median(results), "p95": p(.95), "p99": p(.99), "max": max(results)},
              "final": final, "esp_latency_measured": False, "hardware_tested": False,
              "pass": errors == 0 and final["left"] == 0 and final["right"] == 0 and final["mode"] == "manual"}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=True, indent=2))
    if not report["pass"]:
        raise SystemExit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seconds", type=float, default=1800)
    parser.add_argument("--port", type=int, default=8784)
    parser.add_argument("--output", type=Path, default=ROOT / "build/soak.json")
    args = parser.parse_args()
    asyncio.run(run(args.seconds, args.port, args.output))
