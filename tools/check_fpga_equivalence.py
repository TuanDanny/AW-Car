"""Prove PWM/guard/safety refactoring against a Git revision with Yosys SAT.

Adds verification-only state observations/invariants to copies under fpga/build.
Sources in fpga/rtl are never modified. Requires the baseline in local Git history.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
CASES = (
    ("command_guard", ("link/command_guard.sv",), {}),
    ("pwm_pair", ("pwm/pwm_pair.sv",), {}),
    ("motor_pwm_pair", ("pwm/pwm_pair.sv", "pwm/motor_pwm_pair.sv"), {}),
    *(("pwm_pair", ("pwm/pwm_pair.sv",), {"PERIOD_CYCLES": period})
      for period in (16, 2048, 65535)),
    *(("motor_pwm_pair", ("pwm/pwm_pair.sv", "pwm/motor_pwm_pair.sv"),
       {"PERIOD_CYCLES": period, "ZERO_CYCLES": 1, "SETUP_CYCLES": 1})
      for period in (1, 2048)),
    ("safety_fsm", ("safety/safety_fsm.sv",), {}),
    *(('safety_fsm', ('safety/safety_fsm.sv',), dict(zip(
        ('WATCHDOG_CYCLES', 'HANDSHAKE_CYCLES', 'CLEAR_CYCLES', 'CLEAR_HOLD_CYCLES'), values)))
      for values in ((1, 1, 1, 1), (9, 3, 5, 1), (3, 13, 5, 5),
                     (3, 7, 5, 8), (3, 7, 17, 4))),
)


def observe(source: str, module: str, reference: bool) -> str:
    """Expose state relationships so induction need not unroll long timers."""
    ports: list[str] = []
    assignments: list[str] = []
    if module == "command_guard":
        ports = ["output logic [15:0] proof_last_sequence"]
        assignments = ["assign proof_last_sequence = last_sequence;"]
    elif module == "pwm_pair":
        ports = ["output logic [31:0] proof_phase, proof_shadow_left, proof_shadow_right",
                 "output logic proof_pending, proof_pwm_left, proof_pwm_right"]
        assignments = [f"assign proof_{name} = {name};" for name in (
            "phase", "shadow_left", "shadow_right", "pending")]
        assignments += ["assign proof_pwm_left = pwm_left_ff;",
                        "assign proof_pwm_right = pwm_right_ff;"]
    elif module == "motor_pwm_pair":
        ports = ["output logic [31:0] proof_phase, proof_shadow_left, proof_shadow_right",
                 "output logic proof_pending, proof_pwm_left, proof_pwm_right",
                 "output logic [31:0] proof_wait_count, proof_pending_left, proof_pending_right, "
                 "proof_active_left, proof_active_right",
                 "output logic [1:0] proof_state, proof_pending_direction"]
        assignments = [f"assign proof_{name} = {name};" for name in (
            "wait_count", "pending_left", "pending_right", "state", "pending_direction")]
        assignments += ["assign proof_active_left = unused_left;",
                        "assign proof_active_right = unused_right;"]
        source = source.replace(".active_left(unused_left),", """
        .proof_phase(proof_phase), .proof_shadow_left(proof_shadow_left),
        .proof_shadow_right(proof_shadow_right), .proof_pending(proof_pending),
        .proof_pwm_left(proof_pwm_left), .proof_pwm_right(proof_pwm_right),
        .active_left(unused_left),""", 1)
    elif module == "safety_fsm":
        ports = ["output logic [31:0] proof_watchdog, proof_handshake, proof_clear, proof_hold_count",
                 "output logic proof_hold, proof_arm_confirmed, proof_prev_safety, proof_prev_gate",
                 "output logic [2:0] proof_state, proof_recovery"]
        assignments = [f"assign proof_{name} = {name};" for name in (
            "state", "recovery", "arm_confirmed", "prev_safety", "prev_gate")]
        counts = ("watchdog_count", "handshake_count", "clear_count") if reference else ("phase_count",) * 3
        hold = "hold_count == 0" if reference else "clear_hold_done"
        remaining = "hold_count" if reference else (
            "((CLEAR_HOLD_CYCLES >= CLEAR_CYCLES || phase_count > CLEAR_READY_COUNT) "
            "? phase_count - CLEAR_READY_COUNT : 0)")
        assignments += [f"""
    assign proof_watchdog = (state == ARM_PENDING || state == ARMED) ? {counts[0]} : 0;
    assign proof_handshake = (state == HANDSHAKE || recovery == WAIT_RELEASE || recovery == READY) ? {counts[1]} : 0;
    assign proof_clear = state == CLEAR_WAIT ? {counts[2]} : 0;
    assign proof_hold = state == CLEAR_WAIT && {counts[2]} != 0 && ({hold});
    assign proof_hold_count = state == CLEAR_WAIT ? {remaining} : 0;
    always_comb begin
        assert (state <= CLEAR_WAIT && recovery <= USED);
        assert ((state != HANDSHAKE && state != ARM_PENDING && state != ARMED && state != CLEAR_WAIT) || recovery == USED);
        assert (session_active == (recovery == USED));
        assert (proof_watchdog < WATCHDOG_CYCLES);
        assert (proof_handshake < HANDSHAKE_CYCLES);
        assert (proof_clear < CLEAR_CYCLES);
        assert (proof_hold_count < CLEAR_HOLD_CYCLES);
    end
"""]
    source = source.replace(");", ",\n    " + ",\n    ".join(ports) + "\n);", 1)
    return source.replace("endmodule", "\n" + "\n".join(assignments) + "\nendmodule", 1)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", required=True, help="Git revision before the optimization")
    parser.add_argument("--yosys", default=os.environ.get("YOSYS", "yosys"))
    parser.add_argument("--timeout", type=float, default=120)
    args = parser.parse_args()
    executable = shutil.which(args.yosys)
    if not executable or args.timeout <= 0:
        parser.error("Yosys must be available and timeout must be positive")
    executable = str(Path(executable).resolve())
    try:
        base = subprocess.check_output(
            ["git", "rev-parse", "--verify", f"{args.base}^{{commit}}"], cwd=ROOT, text=True).strip()
        build = ROOT / "fpga/build/equivalence"
        build.mkdir(parents=True, exist_ok=True)
        for index, (top, paths, parameters) in enumerate(CASES):
            lines: list[str] = []
            label = f"{index:02d}-{top}"
            for version in ("gold", "gate"):
                reads = []
                for relative in paths:
                    source = subprocess.check_output(
                        ["git", "show", f"{base}:fpga/rtl/{relative}"], cwd=ROOT, text=True
                    ) if version == "gold" else (ROOT / "fpga/rtl" / relative).read_text(encoding="utf-8")
                    destination = build / f"{version}-{Path(relative).name}"
                    destination.write_text(observe(source, Path(relative).stem, version == "gold"), encoding="utf-8")
                    reads.append(destination.relative_to(ROOT).as_posix())
                lines.append("read_verilog -formal -sv " + " ".join(reads))
                if parameters:
                    lines.append("chparam " + " ".join(f"-set {key} {value}" for key, value in parameters.items()) + f" {top}")
                lines += [f"hierarchy -top {top}", "proc", "flatten", "opt", "async2sync", "opt",
                          f"rename {top} {version}", f"design -stash {version}"]
            prefix = (build / label).relative_to(ROOT).as_posix()
            lines += ["design -copy-from gold -as gold gold", "design -copy-from gate -as gate gate",
                      "miter -equiv -make_assert -flatten gold gate miter", "hierarchy -top miter", "opt_clean",
                      "sat -verify -prove-asserts -tempinduct -seq 2 -maxsteps 16 -set-init-zero "
                      f"-set-at 1 in_rst_n 0 -set-at 2 in_rst_n 1 -dump_vcd {prefix}-counterexample.vcd"]
            script = build / f"{label}.ys"
            script.write_text("\n".join(lines) + "\n", encoding="utf-8")
            result = subprocess.run(
                [executable, "-Q", "-q", "-l", f"{prefix}.log", "-s", script.relative_to(ROOT).as_posix()],
                cwd=ROOT, capture_output=True, text=True, timeout=args.timeout)
            if result.returncode:
                print(result.stdout + result.stderr, file=sys.stderr)
                raise RuntimeError(f"proof failed: {label}; see {prefix}.log")
            print(f"PASS {label}: {parameters or 'default parameters'}", flush=True)
    except (OSError, RuntimeError, subprocess.SubprocessError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1
    print("PASS: all equivalence cases; synchronous model after async2sync, not physical reset/CDC timing")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
