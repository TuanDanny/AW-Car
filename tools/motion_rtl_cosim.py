"""Co-simulate production Motion C++ and real aw_car_top UART/GPIO at 27MHz."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
from build_motion_host import ROOT, DIGEST, build
from motion_simulator import Motion, frame
import struct
import queue
import threading


def run(fpga_root, iverilog, vvp, output="build/motion/rtl-cosim.json"):
    build()
    fpga_root = Path(fpga_root).resolve()
    sources = sorted((fpga_root / "fpga/rtl").rglob("*.sv"))
    target = ROOT / "build/motion/cosim.vvp"
    run_env = dict(os.environ)
    run_env["PATH"] = str(Path(iverilog).resolve().parent) + os.pathsep + run_env.get("PATH", "")
    compiled = subprocess.run([iverilog, "-g2012", "-s", "tb_motion_cosim", "-o", target.as_posix(),
                    *(p.as_posix() for p in sources), (ROOT / "tests/motion_cosim.sv").as_posix()],
                   stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=run_env, text=True)
    (ROOT / "build/motion/rtl-compile.log").write_text(compiled.stdout, encoding="utf-8")
    if compiled.returncode:
        raise RuntimeError(compiled.stdout[-3000:])
    error_log = (ROOT / "build/motion/cosim-stderr.log").open("w")
    process = subprocess.Popen([vvp, str(target)], stdin=subprocess.PIPE,
                               stdout=subprocess.PIPE, stderr=error_log, text=True, bufsize=1, env=run_env)
    lines = queue.Queue()
    def reader():
        for line in process.stdout:
            lines.put(line)
        lines.put("")
    threading.Thread(target=reader, daemon=True).start()
    motion = Motion()
    now = 0
    flags = 4
    idle = True
    report = {"passed": False, "motion_digest": DIGEST, "clock_hz": 27000000,
              "fpga_commit": subprocess.check_output(["git", "-C", str(fpga_root), "rev-parse", "HEAD"], text=True).strip(),
              "rtl_sha256": {p.relative_to(fpga_root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                             for p in sources}, "checks": []}
    last = {}
    started = time.monotonic()

    def view():
        return motion.view(now)

    def advance(ms, freeze=False, safety=True):
        nonlocal now, flags, idle, last
        for _ in range(ms):
            s = view()
            flags = (1 if s["permit"] else 0) | (2 if s["req"] else 0) | (4 if safety else 0)
            flags |= (8 if s["driver"] else 0) | (16 if freeze else 0)
            data = motion.tx(2, now) if idle else b""
            process.stdin.write(f"{flags} {len(data)} {int.from_bytes(data, 'little'):x}\n")
            process.stdin.flush()
            line = lines.get(timeout=10)
            if not line.startswith("@IO "):
                raise RuntimeError(f"RTL fixture failed: {line!r}")
            fields = line.split()
            values = list(map(int, fields[1:12]))
            now, ack, permit, gate, state, fault, ready, left, right, enable, size = values
            idle = bool(ready)
            last = dict(ack=ack, permit=permit, gate=gate, state=state, fault=fault,
                        left_ticks=left, right_ticks=right, gate_enable=enable)
            motion.tick(now, ack | (permit << 1) | (4 if safety else 0) | (gate << 3))
            if size:
                data = bytes.fromhex(fields[12])
                assert len(data) == size
                motion.receive(2, data, now)
            motion.tx(1, now)

    def send(kind, session, seq, v=0, omega=0):
        payload = struct.pack("<hhBH", v, omega, 2, 120) if kind == 3 else b""
        motion.receive(1, frame(1, kind, session, seq, payload), now)

    try:
        advance(30)
        assert view()["fresh"] and last["state"] == 0, (view(), last)
        report["checks"].append("boot_and_status_v2_wire_crc")
        send(1, 101, 1); send(2, 101, 2); advance(80)
        assert view()["state"] == 2 and last["state"] == 3, (view(), last)
        report["checks"].append("real_gpio_pending_status_arm_and_wake")
        send(3, 101, 3, 60, 300); advance(30)
        assert view()["left"] < view()["right"] and last["right_ticks"] > last["left_ticks"] > 0, (view(), last)
        report["checks"].append("real_uart_duty_and_differential_pwm")
        send(4, 101, 4)
        assert not view()["driver"]
        advance(25)
        assert not view()["fault"] and last["state"] == 0 and last["fault"] & 255 == 0, (view(), last)
        report["checks"].append("separate_driver_stop_without_lost_permit_fault")
        send(1, 102, 5); send(2, 102, 6); advance(80)
        assert view()["state"] == 2, (view(), last)
        send(3, 102, 7, 60, 0); advance(10)
        advance(40, freeze=True)
        assert view()["fault"] & 2 and not view()["driver"] and not view()["permit"], (view(), last)
        report["checks"].append("clock_stopped_motion_independent_cutoff")
        advance(35)
        send(1, 103, 8); send(5, 103, 9); advance(100)
        assert view()["state"] == 0 and not view()["fault"] and not view()["driver"], (view(), last)
        report["checks"].append("real_fault_clear_gpio_uart_no_auto_arm")
        report["passed"] = True
    except Exception as error:
        report["error"] = repr(error)
        report["view"] = view()
        report["rtl"] = last
        raise
    finally:
        report["wall_seconds"] = time.monotonic() - started
        report["simulated_us"] = now
        Path(output).parent.mkdir(parents=True, exist_ok=True)
        Path(output).write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        process.stdin.close()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
        error_log.close(); motion.close()
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fpga-root", required=True)
    parser.add_argument("--iverilog", default="iverilog")
    parser.add_argument("--vvp", default="vvp")
    parser.add_argument("--output", default="build/motion/rtl-cosim.json")
    args = parser.parse_args()
    print(json.dumps(run(args.fpga_root, args.iverilog, args.vvp, args.output), indent=2))
