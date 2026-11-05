"""Bounded 30-minute host soak. Runs production C++, never asserts ESP32 timing."""
import argparse
from collections import deque
import ctypes
import hashlib
import json
import os
from pathlib import Path
import time
from build_motion_host import DIGEST, LIB, build
from motion_simulator import Rig


if os.name == "nt":
    class ProcessMemory(ctypes.Structure):
        _fields_ = [("cb", ctypes.c_ulong), ("PageFaultCount", ctypes.c_ulong)] + [
            (name, ctypes.c_size_t) for name in (
                "PeakWorkingSetSize", "WorkingSetSize", "QuotaPeakPagedPoolUsage",
                "QuotaPagedPoolUsage", "QuotaPeakNonPagedPoolUsage",
                "QuotaNonPagedPoolUsage", "PagefileUsage", "PeakPagefileUsage", "PrivateUsage")]

    _memory_info = ctypes.WinDLL("psapi").GetProcessMemoryInfo
    _memory_info.argtypes = [ctypes.c_void_p, ctypes.POINTER(ProcessMemory), ctypes.c_ulong]
    _memory_info.restype = ctypes.c_int


def memory_bytes():
    if os.name == "nt":
        value = ProcessMemory()
        value.cb = ctypes.sizeof(value)
        if _memory_info(ctypes.c_void_p(-1), ctypes.byref(value), value.cb):
            return value.WorkingSetSize
    else:
        try:
            return int(Path("/proc/self/statm").read_text().split()[1]) * os.sysconf("SC_PAGE_SIZE")
        except OSError:
            pass
    return None


def run(seconds=1800, paced=True, output="build/motion/soak.json"):
    build()
    r = Rig()
    r.fpga.edges = True
    if r.arm()["state"] != 2:
        raise RuntimeError("host ARM failed")
    start = time.monotonic()
    latencies = deque(maxlen=65536)
    memory = []
    commands = faults = ticks = 0
    actions = [(60, 0), (60, 300), (60, -300), (0, 300), (0, -300), (-60, 0)]
    try:
        total_ticks = int(seconds * 1000)
        while ticks < total_ticks:
            if paced:
                due = int((time.monotonic() - start) * 1000)
                if ticks >= due:
                    time.sleep(.0005)
                    continue
            if ticks % 50 == 0:
                v, omega = actions[(ticks // 5000) % len(actions)]
                at = time.perf_counter_ns()
                r.send(3, v, omega)
                r.advance(1)
                latencies.append((time.perf_counter_ns() - at) / 1000)
                commands += 1
            else:
                r.advance(1)
            ticks += 1
            if r.view["state"] != 2 or r.view["fault"]:
                faults += 1
                raise RuntimeError(f"unexpected authority loss: {r.view}")
            if ticks % 1000 == 0:
                memory.append({"second": ticks // 1000, "rss_bytes": memory_bytes()})
                if ticks % 60000 == 0:
                    print(f"soak {ticks // 1000}/{seconds}s commands={commands} faults={faults}", flush=True)
        samples = sorted(latencies)
        result = {
            "passed": True, "source_digest": DIGEST,
            "binary_sha256": hashlib.sha256(LIB.read_bytes()).hexdigest(),
            "harness_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "paced": paced, "wall_seconds": time.monotonic() - start,
            "simulated_seconds": ticks / 1000, "commands": commands,
            "faults": faults, "control_steps": ticks,
            "host_receive_step_and_mock_tx_us": {
                "p50": samples[(len(samples) - 1) * 50 // 100],
                "p95": samples[(len(samples) - 1) * 95 // 100],
                "p99": samples[(len(samples) - 1) * 99 // 100], "max": samples[-1]},
            "history_capacity": r.fpga.history.maxlen,
            "status_capacity": r.statuses.maxlen,
            "memory_samples": memory,
            "limits": "Native host + virtual 1ms control clock + Python FPGA peer. Not ESP32/Wi-Fi/GPIO/motor latency."
        }
    except Exception as error:
        result = {"passed": False, "source_digest": DIGEST, "error": str(error),
                  "wall_seconds": time.monotonic() - start, "commands": commands, "ticks": ticks}
        raise
    finally:
        Path(output).parent.mkdir(parents=True, exist_ok=True)
        Path(output).write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        r.close()
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seconds", type=int, default=1800)
    parser.add_argument("--unpaced", action="store_true")
    parser.add_argument("--output", default="build/motion/soak.json")
    args = parser.parse_args()
    result = run(args.seconds, not args.unpaced, args.output)
    print(json.dumps({k: v for k, v in result.items() if k != "memory_samples"}, indent=2))
