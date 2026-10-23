"""Compile/run self-checking Icarus tests; no external Python dependencies."""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
TESTS = ("tb_encoder_units", "tb_encoder_pair", "tb_encoder_timing",
         "tb_pwm_pair", "tb_motor_pwm_pair", "tb_pwm_timing")


def execute(command: list[str], timeout: float, cwd: Path,
            env: dict[str, str] | None = None) -> None:
    result = subprocess.run(command, cwd=cwd, text=True, capture_output=True,
                            timeout=timeout, env=env)
    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr)
    if result.returncode:
        raise RuntimeError(f"exit {result.returncode}: {command[0]}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--test", action="append", choices=TESTS)
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--waves", action="store_true")
    parser.add_argument("--timeout", type=float, default=120)
    parser.add_argument("--iverilog", default=os.environ.get("IVERILOG", "iverilog"))
    parser.add_argument("--vvp", default=os.environ.get("VVP", "vvp"))
    args = parser.parse_args()
    if args.list:
        print("\n".join(TESTS))
        return 0
    if args.timeout <= 0:
        parser.error("--timeout must be positive")
    compiler, runtime = shutil.which(args.iverilog), shutil.which(args.vvp)
    if not compiler or not runtime:
        parser.error("Icarus/VVP unavailable; set PATH, IVERILOG/VVP or --iverilog/--vvp")
    # Resolve before switching the simulation cwd; child ivl/vvp DLLs may need bin in PATH.
    compiler, runtime = str(Path(compiler).resolve()), str(Path(runtime).resolve())
    tool_env = os.environ.copy()
    tool_env["PATH"] = os.pathsep.join(dict.fromkeys([
        str(Path(compiler).parent), str(Path(runtime).parent), tool_env.get("PATH", "")]))
    build = ROOT / "fpga" / "build"
    build.mkdir(parents=True, exist_ok=True)
    sources = sorted(str(path) for path in (ROOT / "fpga" / "rtl").glob("*.v"))
    try:
        version = subprocess.run([compiler, "-V"], cwd=ROOT, text=True,
                                 capture_output=True, timeout=15, check=True, env=tool_env)
        print(version.stdout.splitlines()[0])
        for name in args.test or TESTS:
            print(f"RUN {name}", flush=True)
            output = build / f"{name}.vvp"
            execute([compiler, "-g2012", "-Wall", "-s", name, "-o", str(output),
                     *sources, str(ROOT / "fpga" / "tb" / f"{name}.sv")], args.timeout, ROOT, tool_env)
            command = [runtime, str(output)]
            if args.waves:
                command.append("+waves")
            execute(command, args.timeout, build, tool_env)
    except (OSError, RuntimeError, subprocess.SubprocessError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1
    print("PASS: all requested FPGA simulations")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
