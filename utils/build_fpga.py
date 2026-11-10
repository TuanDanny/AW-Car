"""Build/test simplev1 FPGA locally. Never opens a serial port or programs a board."""
from __future__ import annotations

import argparse
import binascii
from datetime import datetime, timezone
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
TARGET = ROOT / "fpga/targets/tang_nano9k"
BUILD = ROOT / "build/fpga"
TOP = "simplev1_nano9k"
TESTS = ("tb_pwm_encoder", "tb_spi", "tb_nano9k", "tb_watchdog")
TOOLBIN = Path("D:/Project/AW-Car/build/toolchain/ucrt64/bin")
GOWIN = Path("C:/Gowin/Gowin_V1.9.11.03_Education_x64/IDE")
PINS = {"clk": 52, "arst_n": 3, "spi_mosi": 25, "spi_miso": 26,
        "spi_sclk": 29, "spi_cs_n": 30, "enc_left": 27, "enc_right": 28,
        "drv_left_in1": 35, "drv_left_in2": 40, "drv_right_in1": 41, "drv_right_in2": 42,
        **{f"leds_n[{i}]": pin for i, pin in enumerate((10, 11, 13, 14, 15, 16))}}
SAMPLERS = ("core/link/mosi_meta_s1", "core/link/sclk_meta_s1", "core/link/cs_meta_s1",
            "core/left_encoder/meta_ff_s1", "core/right_encoder/meta_ff_s1")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_hashes():
    paths = sorted((ROOT / "fpga").rglob("*")) + sorted((ROOT / "test/rtl").glob("*"))
    paths += [ROOT / "utils/build_fpga.py", ROOT / "data/fpga_spi_vectors.hex",
              ROOT / "data/fpga_spi_vectors.json", ROOT / "docs/protocol.md",
              ROOT / "esp/shared/include/simple/protocol.hpp", ROOT / "esp/shared/src/protocol.cpp"]
    return {p.relative_to(ROOT).as_posix(): sha(p) for p in paths if p.is_file()}


def check_vectors():
    require(binascii.crc_hqx(b"123456789", 0xffff) == 0x29b1, "CRC reference check")
    vectors = json.loads((ROOT / "data/fpga_spi_vectors.json").read_text(encoding="utf-8"))
    flattened = []
    for item in vectors["vectors"]:
        frame = bytes.fromhex(item["hex"])
        require(len(frame) == 32 and binascii.crc_hqx(frame[:30], 0xffff) == int.from_bytes(frame[30:], "little"),
                "Golden vector CRC mismatch: " + item["name"])
        flattened.extend(frame)
    actual = [int(x, 16) for x in (ROOT / "data/fpga_spi_vectors.hex").read_text().split()]
    require(actual == flattened and len(actual) == 128, "Golden vector files drifted")
    return {"result": "PASS", "vectors": len(vectors["vectors"]), "crc_check": "123456789=29B1"}


def pin_audit(cst, pin_db=None):
    locations = re.findall(r'IO_LOC\s+"([^"]+)"\s+(\d+)\s*;', cst)
    ports = re.findall(r'IO_PORT\s+"([^"]+)"\s+([^;]+);', cst)
    require(len(locations) == len(ports) == 18 and {k: int(v) for k, v in locations} == PINS,
            "Pin inventory differs from the 18-port contract")
    require(len(set(PINS.values())) == 18 and len(dict(ports)) == 18 and set(dict(ports)) == set(PINS),
            "Duplicate/missing pin/port")
    for name, options in ports:
        opts = dict(re.findall(r'(\w+)=([\w.]+)', options))
        onboard = name == "arst_n" or name.startswith("leds_n[")
        pull = "UP" if name in {"arst_n", "spi_cs_n"} or name.startswith("leds_n[") else "DOWN"
        if name in {"clk", "enc_right"}:
            pull = "NONE"
        require(opts.get("IO_TYPE") == ("LVCMOS18" if onboard else "LVCMOS33") and
                opts.get("BANK_VCCIO") == ("1.8" if onboard else "3.3") and opts.get("PULL_MODE") == pull,
                "Electrical setting drift: " + name)
        if name == "spi_miso" or name.startswith(("drv_", "leds_n[")):
            require(opts.get("DRIVE") == "4", "Output drive strength drift: " + name)
    if pin_db:
        db = {p["INDEX"]: p for p in json.loads(pin_db.read_text())["PIN_DATA"]}
        for name, number in PINS.items():
            pin = db.get(number) or db.get(str(number))
            require(pin and pin["TYPE"] == "I/O", "Invalid package pin: " + name)
            require((pin["BANK"] == 3) == (name == "arst_n" or name.startswith("leds_n[")),
                    "Package bank voltage mismatch: " + name)
    return {"result": "PASS", "ports": 18, "package_database_checked": bool(pin_db),
            "right_encoder_pull": "NONE (external level-shifter pull-up required)"}


def source_audit():
    for directory in (ROOT / "fpga", ROOT / "test/rtl"):
        for source in directory.rglob("*"):
            if source.suffix.lower() in {".v", ".vh", ".svh", ".vhd", ".vhdl"}:
                raise ValueError("Project HDL must be .sv only: " + str(source))
            if source.suffix == ".sv":
                content = source.read_text(encoding="utf-8")
                require("`default_nettype none" in content, "Missing default_nettype none: " + str(source))
                require(not re.search(r'@\s*\([^)]*(?:posedge|negedge)\s+(?:spi_)?sclk', content),
                        "SPI-generated clock is forbidden: " + str(source))
                if directory.name == "fpga":
                    for line in content[:content.index(");")].splitlines():
                        require(not re.match(r'\s*input\s+(?!wire logic\b)', line),
                                "Module inputs must use explicit wire logic: " + str(source))
    sdc = (TARGET / f"{TOP}.sdc").read_text()
    exceptions = [line for line in sdc.splitlines() if line.startswith("set_false_path")]
    require(len(exceptions) == 1 and "*" not in exceptions[0], "Blanket/additional timing exception")
    require(re.findall(r'get_pins\s+\{([^}]+)\}', exceptions[0])[0].split() == [s + "/D" for s in SAMPLERS],
            "Only the five exact first-sampler D pins may be excepted")
    require(set(re.findall(r'get_ports\s+\{([^}]+)\}', exceptions[0])[0].split()) ==
            {"spi_mosi", "spi_sclk", "spi_cs_n", "enc_left", "enc_right"}, "Unexpected false-path source")
    require(len(re.findall(r'^create_clock\b', sdc, re.M)) == 1 and "create_generated_clock" not in sdc,
            "Exactly one real 27MHz clock is required")
    return "PASS"


def run(command, log, env=None, timeout=1800):
    log.parent.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    with log.open("w", encoding="utf-8") as handle:
        process = subprocess.run([str(x) for x in command], cwd=ROOT, env=env, stdout=handle,
                                 stderr=subprocess.STDOUT, timeout=timeout)
    output = log.read_text(encoding="utf-8", errors="replace")
    require(process.returncode == 0, f"Command failed ({process.returncode}): {log}\n{output[-2500:]}")
    return output, round(time.monotonic() - started, 3)


def rtl_tests(args, env, report):
    result = []
    report["rtl_tests"] = result
    sources = sorted((ROOT / "fpga/rtl").glob("*.sv")) + [TARGET / f"{TOP}.sv"]
    for name in args.test or TESTS:
        item = {"test": name, "result": "FAIL (did not complete)"}
        result.append(item)
        executable = BUILD / f"{name}.vvp"
        compilation, _ = run([args.iverilog, "-g2012", "-Wall", "-s", name, "-o", executable, *sources,
             ROOT / "test/rtl/spi_test_master.sv", ROOT / f"test/rtl/{name}.sv"],
            BUILD / f"{name}-compile.log", env)
        output, elapsed = run([args.vvp, executable], BUILD / f"{name}.log", env)
        require(f"PASS {name}:" in output, "Missing simulator PASS marker: " + name)
        print(output.strip(), flush=True)
        item.update(result="PASS", seconds=elapsed, compiler_diagnostics=compilation.splitlines())
    return result


def audit_mapped(mapped):
    blocks = {name.lstrip("\\"): block for name, block in
              re.findall(r'^DFF\w+\s+(\S+)\s*\((.*?)\);', mapped, re.M | re.S)}
    def pin(block, name):
        match = re.search(r'\.' + name + r'\(([^)]+)\)', block)
        require(match is not None, "Missing mapped FF pin: " + name)
        return match[1].strip().lstrip("\\")
    clocks = sorted({pin(block, "CLK") for block in blocks.values()})
    require(clocks == ["clk_d"], "Unexpected/derived register clock in mapped netlist: " + str(clocks))
    second_stages = ("core/link/mosi_sync_s1", "core/link/sclk_sync_s1", "core/link/cs_sync_s1",
                     "core/left_encoder/sync_ff_s1", "core/right_encoder/sync_ff_s1")
    pads = ("spi_mosi", "spi_sclk", "spi_cs_n", "enc_left", "enc_right")
    for first, second, pad in zip(SAMPLERS, second_stages, pads):
        require(first in blocks and second in blocks, "Missing synchronizer FF: " + first)
        require(pin(blocks[first], "D") == pad + "_d" and
                pin(blocks[second], "D") == pin(blocks[first], "Q"),
                "First/second synchronizer connection drift: " + pad)
    flops = {pin(block, "Q"): name for name, block in blocks.items()}
    for signal in ["por_ready", *(f"por_ticks[{i}]" for i in range(10))]:
        require(signal in flops and re.search(r'defparam\s+' + re.escape(flops[signal]) + r"\s*\.INIT=1'b0;", mapped),
                "Missing configuration INIT=0 for POR: " + signal)
    return {"result": "PASS", "register_clock_nets": clocks, "first_samplers": list(SAMPLERS),
            "second_stages_connected": True, "por_init_zero": True}


def parse_timing(text):
    def number(pattern, body=text, integer=False):
        match = re.search(pattern, body, re.M)
        require(match is not None, "Missing STA metric: " + pattern)
        return int(match[1]) if integer else float(match[1])

    result = {"fmax_mhz": number(r'clk_27m\s+27\.000\(MHz\)\s+([\d.]+)\(MHz\)'),
              "setup_violated_endpoints": number(r'<Numbers of Setup Violated Endpoints>:(\d+)', integer=True),
              "hold_violated_endpoints": number(r'<Numbers of Hold Violated Endpoints>:(\d+)', integer=True),
              "paths_analyzed": number(r'<Numbers of Paths Analyzed>:(\d+)', integer=True),
              "endpoints_analyzed": number(r'<Numbers of Endpoints Analyzed>:(\d+)', integer=True)}
    body = text[text.index("Note:Core Timing Report"):]
    for index, kind in enumerate(("Setup", "Hold", "Recovery", "Removal"), 1):
        start = body.index(f"3.1.{index} {kind} Paths Table")
        end = body.find("\n3.", start + 5)
        result["worst_" + kind.lower() + "_slack_ns"] = number(r'^\s+1\s+(-?[\d.]+)\s', body[start:end])
    result["tns_ns"] = {k: number(r'clk_27m\s+' + k + r'\s+(-?[\d.]+)') for k in ("setup", "hold")}
    active = re.findall(r'^\s+(TC_\w+)\s+(\w+)\s', body, re.M)
    result["constraints"] = [{"name": name, "status": status} for name, status in active]
    result["unconstrained_path_count"] = None
    result["scope"] = ("Routed STA at 27MHz with 0.2ns uncertainty and 37.037ns boundary transport budgets; "
                       "five asynchronous first-sampler D pins excepted. No synchronous SPI clock claim. "
                       "Gowin text report does not enumerate all unconstrained paths; board signal integrity/MTBF not measured.")
    result["result"] = "PASS" if (result["fmax_mhz"] >= 27 and
        result["setup_violated_endpoints"] == result["hold_violated_endpoints"] == 0 and
        all(result["worst_" + kind + "_slack_ns"] >= 0 for kind in ("setup", "hold", "recovery", "removal")) and
        all(value == 0 for value in result["tns_ns"].values()) and len(active) == 9 and
        all(status == "Actived" for _, status in active)) else "FAIL"
    return result


def gowin_build(args, env, result):
    ide = Path(args.gw_sh).resolve().parent.parent
    result["pin_audit"] = pin_audit((TARGET / f"{TOP}.cst").read_text(), ide / "data/device/GW1NR-9C/QFN88P.json")
    result["gowin"] = {"result": "FAIL (did not complete)"}
    log, elapsed = run([args.gw_sh, TARGET / "build.tcl"], BUILD / "gowin-build.log", env)
    require(not re.search(r'^\s*ERROR', log, re.M) and "Bitstream generation completed" in log,
            "Gowin returned without completing synthesis/PnR/bitstream")
    result["gowin"] = {"result": "BUILD COMPLETED (see STA separately)", "seconds": elapsed,
                       "warnings": [line for line in log.splitlines() if re.search(r'WARN\s+\(', line)]}
    base = BUILD / f"gowin/{TOP}/impl/pnr"
    timing, resource, netlist = [base / f"{TOP}{suffix}" for suffix in (".tr", ".rpt.txt", ".vo")]
    timing_text = timing.read_text(encoding="utf-8", errors="replace")
    result["timing"] = parse_timing(timing_text)
    result["tool_versions"]["gowin"] = re.search(r'<Tool Version>:(.+)', timing_text)[1].strip()
    result["routed_pins"] = pin_audit((base / f"{TOP}.io.cst").read_text())
    mapped = netlist.read_text(encoding="utf-8", errors="replace")
    result["mapped_audit"] = audit_mapped(mapped)
    resource_text = resource.read_text(encoding="utf-8", errors="replace")
    result["resources"] = [line.strip() for line in resource_text.splitlines() if
                           re.search(r'(Logic\s+\||Register as FF|Register as Latch|I/O Port|I/O Buf)', line)]
    for label in ("Logic Register as Latch", "I/O Register as Latch"):
        require(re.search(re.escape(label) + r'\s*\|\s*0/', resource_text), "Mapped latch detected: " + label)
    result["report_sha256"] = {p.relative_to(ROOT).as_posix(): sha(p) for p in
                               (timing, resource, netlist, base / f"{TOP}.io.cst", base / f"{TOP}.fs")}
    executable = BUILD / "mapped.vvp"
    result["post_pnr_simulation"] = {"result": "FAIL (did not complete)", "sdf": False}
    run([args.iverilog, "-g2012", "-s", "tb_nano9k", "-o", executable,
         ide / "simlib/gw1n/prim_sim.v", netlist, ROOT / "test/rtl/spi_test_master.sv",
         ROOT / "test/rtl/tb_nano9k.sv"], BUILD / "mapped-compile.log", env)
    output, seconds = run([args.vvp, executable], BUILD / "mapped.log", env)
    require("PASS tb_nano9k:" in output, "Mapped test did not complete")
    result["post_pnr_simulation"] = {"result": "PASS", "test": "tb_nano9k", "seconds": seconds, "sdf": False,
                                    "scope": "Functional routed netlist with installed Gowin primitives; timing evaluated separately by STA"}
    print("Mapped " + output.strip(), flush=True)
    print(json.dumps(result["timing"], indent=2), flush=True)
    require(result["timing"]["result"] == "PASS", "Actual routed STA violations/inactive constraints: see report")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--iverilog", default=shutil.which("iverilog") or str(TOOLBIN / "iverilog.exe"))
    parser.add_argument("--vvp", default=shutil.which("vvp") or str(TOOLBIN / "vvp.exe"))
    parser.add_argument("--gw-sh", default=os.environ.get("GOWIN_SH") or str(GOWIN / "bin/gw_sh.exe"))
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--rtl-only", action="store_true")
    group.add_argument("--gowin-only", action="store_true")
    parser.add_argument("--test", nargs="+", choices=TESTS, help="Selected RTL benches; default is all including the real 500ms watchdog")
    parser.add_argument("--report", type=Path, default=BUILD / "build-report.json")
    args = parser.parse_args()
    report = args.report if args.report.is_absolute() else ROOT / args.report
    report = report.resolve()
    require(report.is_relative_to(ROOT / "build") or
            report.parent == ROOT / "data" and report.name.startswith("fpga"),
            "Report must stay in this checkout's build/ or data/fpga*")
    BUILD.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ)
    env["PATH"] = str(Path(args.iverilog).resolve().parent) + os.pathsep + env.get("PATH", "")
    result = {"result": "INCOMPLETE", "hardware": "NOT RUN", "programming_performed": False,
              "serial_or_jtag_opened": False, "clock_hz": 27000000, "pwm_hz": 20000,
              "timestamp_utc": datetime.now(timezone.utc).isoformat(),
              "tool_versions": {"python": sys.version.split()[0]},
              "reversal_guard": "40ms in Motion ControlCore only; FPGA adds one zero PWM period (50us) on direct sign reversal",
              "rtl_tests": "NOT RUN", "gowin": "NOT RUN", "timing": "NOT RUN", "post_pnr_simulation": "NOT RUN"}
    started = time.monotonic()
    try:
        result["source_audit"] = source_audit()
        result["golden_vectors"] = check_vectors()
        result["pin_audit"] = pin_audit((TARGET / f"{TOP}.cst").read_text())
        result["source_sha256"] = source_hashes()
        for executable in (args.iverilog, args.vvp):
            require(Path(executable).is_file(), "Missing tool: " + str(executable))
        version, _ = run([args.iverilog, "-V"], BUILD / "iverilog-version.log", env)
        result["tool_versions"]["iverilog"] = version.splitlines()[0]
        if not args.gowin_only:
            rtl_tests(args, env, result)
        if not args.rtl_only:
            require(Path(args.gw_sh).is_file(), "Missing Gowin gw_sh: " + args.gw_sh)
            gowin_build(args, env, result)
        result["result"] = "PASS (selected local checks; hardware not run)"
        return 0
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        result["result"] = "FAIL"
        result["error"] = str(error)
        print("FAIL: " + str(error), file=sys.stderr, flush=True)
        return 1
    finally:
        result["wall_seconds"] = round(time.monotonic() - started, 3)
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print("Report: " + str(report), flush=True)


if __name__ == "__main__":
    raise SystemExit(main())
