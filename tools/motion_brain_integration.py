"""Execute both production C++ cores together; independent FPGA contract peer."""
import argparse
import importlib.util
import json
from pathlib import Path
import sys
from build_motion_host import build, DIGEST
from motion_simulator import Motion, Fpga
from motion_simulator import decode
from collections import deque


def load_brain(root):
    tools = Path(root).resolve() / "tools"
    sys.path.insert(0, str(tools))
    from build_brain_host import build as build_brain, DIGEST as brain_digest
    build_brain()
    spec = importlib.util.spec_from_file_location("production_brain_bridge", tools / "brain_simulator.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.Brain, brain_digest


def run(brain_root):
    build()
    Brain, brain_digest = load_brain(brain_root)
    brain = Brain()
    motion = Motion()
    fpga = Fpga()
    fpga.edges = True
    now = 0
    seq = 0
    checks = []
    trace = deque(maxlen=50)

    def bstate():
        return brain.state(now)

    def advance(ms, manual=None):
        nonlocal now, seq
        for i in range(ms):
            now += 1000
            brain.command(0, now)
            if manual is not None and i % 50 == 0 and bstate()["authorized"] and bstate()["mode"] == "Manual":
                seq += 1
                s = bstate()
                result = brain.command(7, now, s["epoch"], s["challenge"], seq,
                                       manual[0], manual[1], 120, int(any(manual)))
                assert result == 0, (result, s)
            for _ in range(3):
                data = brain.tx(now)
                if not data:
                    break
                trace.append({"at": now, "brain_tx": decode(data)[1:4],
                              "before": motion.view(now), "ack": fpga.ack})
                motion.receive(1, data, now)
                trace.append({"at": now, "after": motion.view(now)})
            inputs = fpga.pins(motion.view(now), now)
            motion.tick(now, inputs)
            for data in fpga.step(now):
                motion.receive(2, data, now)
            data = motion.tx(2, now)
            if data:
                fpga.receive(data, now)
            data = motion.tx(1, now)
            if data:
                brain.rx(now, data)

    def arm():
        assert brain.command(5, now, bstate()["epoch"]) == 0, bstate()
        advance(100, (0, 0))
        assert bstate()["authorized"] and motion.view(now)["state"] == 2, (bstate(), motion.view(now))

    try:
        brain.command(1, now)
        brain.command(3, now, 1)
        advance(50)
        arm()
        advance(120, (60, 300))
        assert motion.view(now)["right"] > motion.view(now)["left"] > 0
        checks.append("manual_hello_arm_twist_both_cpp_cores")
        brain.command(6, now)
        advance(35)
        assert not bstate()["authorized"] and not motion.view(now)["fault"], (bstate(), motion.view(now))
        checks.append("stop_exact_ack_no_fpga_fault")
        brain.command(4, now, 1)
        advance(35)
        arm()
        assert brain.command(8, now, bstate()["epoch"], 0, 30, 100) == 0
        advance(150)
        assert motion.view(now)["left"] == 0 and motion.view(now)["state"] == 2
        checks.append("ai_short_action_neutral_keeps_arm")
        motion.lib.motion_fault(motion.ptr, 4, now)
        advance(60)
        assert bstate()["fault_flags"] and not bstate()["authorized"], bstate()
        assert brain.command(9, now, bstate()["epoch"]) == 0, bstate()
        advance(150)
        assert not bstate()["clearing"] and not bstate()["fault_flags"], (bstate(), motion.view(now))
        assert not bstate()["authorized"] and motion.view(now)["state"] == 0
        checks.append("web_clear_new_session_actual_motion_gpio_recovery_no_auto_arm")
        arm()
        brain.command(2, now)  # AI survives a closed dashboard.
        advance(100)
        assert bstate()["authorized"]
        brain.command(3, now, 0)  # Cloud loss revokes AI even without Web.
        advance(35)
        assert not bstate()["authorized"] and not motion.view(now)["driver"]
        checks.append("ai_disconnect_contract_and_cloud_loss_stop")
        return {"passed": True, "motion_digest": DIGEST, "brain_digest": brain_digest,
                "simulated_us": now, "checks": checks,
                "limits": "Two compiled cores and Python FPGA peer; no physical UART/WiFi/motor."}
    except Exception:
        (Path("build/motion/brain-integration-failure.json")).write_text(
            json.dumps(list(trace), indent=2) + "\n", encoding="utf-8")
        raise
    finally:
        brain.close(); motion.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--brain-root", required=True)
    parser.add_argument("--output", default="build/motion/brain-integration.json")
    args = parser.parse_args()
    result = run(args.brain_root)
    Path(args.output).write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
