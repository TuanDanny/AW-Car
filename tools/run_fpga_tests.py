"""Compile/run self-checking Icarus tests; no external Python dependencies."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
TESTS = ("tb_encoder_units", "tb_encoder_pair", "tb_encoder_timing",
         "tb_common_matrix", "tb_crc16_matrix", "tb_guard_sequence",
         "tb_uart_matrix", "tb_frame_tx_random",
         "tb_safety_matrix",
         "tb_pwm_pair", "tb_motor_pwm_pair", "tb_pwm_timing", "tb_pwm_widths",
         "tb_uart", "tb_frame_rx", "tb_frame_tx", "tb_command_guard", "tb_fpga_link",
         "tb_safety_fsm", "tb_safety_timing", "tb_drive_core", "tb_drive_defaults")


def execute(command: list[str], timeout: float, cwd: Path,
            env: dict[str, str] | None = None) -> str:
    result = subprocess.run(command, cwd=cwd, text=True, capture_output=True,
                            timeout=timeout, env=env)
    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr)
    if result.returncode:
        raise RuntimeError(f"exit {result.returncode}: {command[0]}")
    return result.stdout


def declared_modules(sources: list[Path]) -> dict[str, str]:
    """Inventory project module declarations, ignoring comments (not a HDL parser)."""
    inventory = {}
    for source in sources:
        content = re.sub(r"/\*.*?\*/|//[^\n]*", "", source.read_text(encoding="utf-8"), flags=re.S)
        for name in re.findall(r"^\s*module\s+(\w+)\b", content, flags=re.M):
            if name in inventory:
                raise RuntimeError(f"duplicate RTL module: {name}")
            inventory[name] = str(source)
    return inventory


def elaborated_modules(executable: Path) -> list[str]:
    """Read Icarus VVP's elaborated module types, rather than guessing from filenames."""
    return sorted(set(re.findall(r'\.scope module,\s+"[^"]*"\s+"([^"]+)"',
                                 executable.read_text(encoding="utf-8", errors="replace"))))


def require_pass_marker(name: str, stdout: str) -> None:
    # The nominal-default wrapper reuses the complete drive_core scenario.
    marker = "tb_drive_core" if name == "tb_drive_defaults" else name
    if not re.search(rf"^PASS {re.escape(marker)}(?=:|\s*$)", stdout, flags=re.M):
        raise RuntimeError(f"missing self-checking PASS marker: {name}")


def module_evidence(inventory: dict[str, str], results: dict) -> dict:
    evidence = {name: [test for test, result in results.items()
                      if result["status"] == "passed" and name in result["modules"]]
                for name in sorted(inventory)}
    return {"metric": "elaborated_in_passing_testbench",
            "modules": evidence,
            "covered": sum(bool(tests) for tests in evidence.values()),
            "total": len(evidence),
            "missing": [name for name, tests in evidence.items() if not tests],
            "line_branch_toggle_coverage": "not_measured",
            "physical_timing": "not_measured"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--test", action="append", choices=TESTS)
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--waves", action="store_true")
    parser.add_argument("--full-timing", action="store_true",
                        help="run the 2-second integrated scenario at nominal 27 MHz")
    parser.add_argument("--report", type=Path, help="write JSON test results and module-level evidence")
    parser.add_argument("--require-module-coverage", action="store_true",
                        help="fail unless every declared RTL module is elaborated by a passing test; requires --report")
    parser.add_argument("--timeout", type=float, default=120)
    parser.add_argument("--iverilog", default=os.environ.get("IVERILOG", "iverilog"))
    parser.add_argument("--vvp", default=os.environ.get("VVP", "vvp"))
    args = parser.parse_args()
    if args.list:
        print("\n".join(TESTS))
        return 0
    if args.timeout <= 0:
        parser.error("--timeout must be positive")
    if args.require_module_coverage and not args.report:
        parser.error("--require-module-coverage requires --report")
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
    source_paths = sorted((ROOT / "fpga" / "rtl").rglob("*.sv"))
    sources = [str(path) for path in source_paths]
    results, inventory = {}, {}
    report = {"schema_version": 1, "status": "failed", "tests": results,
              "full_timing": args.full_timing}
    current_test = None
    try:
        if args.report:
            inventory = declared_modules(source_paths)
            if not inventory:
                raise RuntimeError("no RTL module declarations found")
            report["source_sha256"] = {path.relative_to(ROOT).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
                                       for path in source_paths + sorted((ROOT / "fpga" / "tb").glob("*.sv"))}
        version = subprocess.run([compiler, "-V"], cwd=ROOT, text=True,
                                 capture_output=True, timeout=15, check=True, env=tool_env)
        print(version.stdout.splitlines()[0])
        report["compiler"] = version.stdout.splitlines()[0]
        for name in args.test or TESTS:
            current_test = name
            results[name] = {"status": "failed", "modules": []}
            started = time.monotonic()
            print(f"RUN {name}", flush=True)
            output = build / f"{name}.vvp"
            parameters = ["-Ptb_drive_core.SCALE=1"] if args.full_timing and name == "tb_drive_core" else []
            execute([compiler, "-g2012", "-Wall", "-s", name, "-o", str(output),
                     *parameters, *sources, str(ROOT / "fpga" / "tb" / f"{name}.sv")], args.timeout, ROOT, tool_env)
            command = [runtime, str(output)]
            if args.waves:
                command.append("+waves")
            stdout = execute(command, args.timeout, build, tool_env)
            if args.report:
                require_pass_marker(name, stdout)
                results[name]["modules"] = elaborated_modules(output)
                results[name]["functional_counts"] = {
                    key: int(value) for key, value in re.findall(r"^COVER (\S+) (\d+)$", stdout, flags=re.M)}
            results[name].update(status="passed", duration_seconds=round(time.monotonic()-started, 3))
        if args.report:
            evidence = module_evidence(inventory, results)
            if args.require_module_coverage and evidence["missing"]:
                raise RuntimeError("RTL modules without a passing test: " + ", ".join(evidence["missing"]))
        report["status"] = "passed"
    except (OSError, RuntimeError, subprocess.SubprocessError) as error:
        report["error"] = str(error)
        if current_test and results[current_test]["status"] != "passed":
            results[current_test]["error"] = str(error)
        print(f"FAIL: {error}", file=sys.stderr)
        return 1
    finally:
        if args.report:
            report["coverage"] = module_evidence(inventory, results)
            destination = args.report if args.report.is_absolute() else ROOT / args.report
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
            print(f"Module evidence: {report['coverage']['covered']}/{report['coverage']['total']}; report {destination}")
    print("PASS: all requested FPGA simulations")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
