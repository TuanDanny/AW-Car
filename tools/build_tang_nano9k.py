"""Audit/build Tang Nano 9K. Never programs a device or opens a serial port."""
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
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "fpga/targets/tang_nano9k"
BUILD = ROOT / "build/tang-nano9k"
SAMPLERS = (
    "core/core_0/link/receiver/meta_ff_s0",
    "core/core_0/control_sync/meta_ff_0_s0",
    "core/core_0/g_single_out.encoders/left_filter/meta_ff_0_s0",
    "core/core_0/g_single_out.encoders/right_filter/meta_ff_0_s0",
)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_hashes(root=ROOT):
    files = sorted((root / "fpga/rtl").rglob("*.sv"))
    files += sorted(p for p in (root / "fpga/targets/tang_nano9k").iterdir()
                    if p.suffix in {".sv", ".sdc", ".cst", ".tcl", ".gprj", ".json"}
                    and p.name != "timing-evidence.json")
    return {p.relative_to(root).as_posix(): sha(p) for p in files}


def audit(root=ROOT, pin_db=None):
    target = root / "fpga/targets/tang_nano9k"
    data = json.loads((target / "pinout.json").read_text(encoding="utf-8"))
    pins = data["pins"]
    require(len(pins) == 17, "Expected exactly17 scalar physical ports")
    names = [p["signal"] for p in pins]
    numbers = [p["package_pin"] for p in pins]
    require(len(set(names)) == len(set(numbers)) == 17, "Duplicate signal/package pin")
    cst = (target / "aw_car_nano9k.cst").read_text(encoding="utf-8")
    locs = re.findall(r'IO_LOC\s+"(\w+)"\s+(\d+)\s*;', cst)
    ports = re.findall(r'IO_PORT\s+"(\w+)"\s+([^;]+);', cst)
    require(len(locs) == len(ports) == 17, "CST must bind every port exactly once")
    require(dict(locs) == {p["signal"]: str(p["package_pin"]) for p in pins}, "CST pin drift")
    require(set(dict(ports)) == set(names), "CST IO standard port drift")
    for pin in pins:
        require(pin["package_pin"] not in data["reserved_package_pins"], "Reserved/config/peripheral pin")
        voltage = 1.8 if pin["bank"] == 3 else 3.3
        require(pin["vccio"] == voltage, "Wrong bank voltage")
        require(pin["io_standard"] == ("LVCMOS18" if voltage == 1.8 else "LVCMOS33"), "Wrong IO standard")
        require(voltage == 3.3 or pin["signal"] == "arst_n" and pin["header"] is None,
                "External AW-Car IO must be3.3V; reset1.8V is onboard only")
        options = dict(re.findall(r'(\w+)=([\w.]+)', dict(ports)[pin["signal"]]))
        require(options.get("IO_TYPE") == pin["io_standard"] and
                options.get("BANK_VCCIO") == str(voltage) and options.get("PULL_MODE") == pin["pull"],
                "CST electrical drift: " + pin["signal"])
        if pin["direction"] == "output":
            require(options.get("DRIVE") == "4", "Unexpected output drive strength")
    if pin_db:
        db = {int(p["INDEX"]): p for p in json.loads(Path(pin_db).read_text())["PIN_DATA"]}
        for pin in pins:
            package = db[pin["package_pin"]]
            require(package["TYPE"] == "I/O" and package["BANK"] == pin["bank"] and
                    package["NAME"] == pin["package_name"], "Gowin package database mismatch")
    for file in [target / "aw_car_nano9k.sv", root / "fpga/rtl/aw_car_top.sv"]:
        text = re.sub(r'//[^\n]*', '', file.read_text())
        header = text[text.index(") (") + 3:text.index(");")]
        declared = {}
        parts = re.split(r'\b(input|output)\s+(?:wire\s+)?logic\s+', header)
        for index in range(1, len(parts), 2):
            declared.update({x.strip(): parts[index] for x in parts[index + 1].strip().strip(',').split(',')})
        require(declared == {p["signal"]: p["direction"] for p in pins}, "Physical/logical port contract mismatch")
    project = ET.parse(target / "aw_car_nano9k.gprj").getroot()
    require(project.find("Device").attrib == {"name": "GW1NR-9C", "pn": data["part"]}, "Wrong device")
    files = [(target / p.attrib["path"]).resolve() for p in project.findall("./FileList/File")]
    expected = set((root / "fpga/rtl").rglob("*.sv")) | {
        target / ("aw_car_nano9k" + suffix) for suffix in [".sv", ".cst", ".sdc"]}
    require(len(files) == len(expected) and set(files) == expected, "GPRJ source list drift")
    sdc = (target / "aw_car_nano9k.sdc").read_text()
    exceptions = [line for line in sdc.splitlines() if line.startswith("set_false_path")]
    require(len(exceptions) == 1 and all(p + "/D" in exceptions[0] for p in SAMPLERS),
            "Only the four first-stage D pin exceptions are allowed")
    require("*" not in exceptions[0] and "all_clocks" not in exceptions[0], "Blanket timing exception")
    require(re.findall(r'get_pins\s+\{([^}]+)\}', exceptions[0])[0].split() == [p + "/D" for p in SAMPLERS],
            "Unexpected extra false-path endpoint")
    require(set(re.findall(r'get_ports\s+\{([^}]+)\}', exceptions[0])[0].split()) ==
            {"rx", "recovery_req_async", "left_out", "right_out"}, "Unexpected false-path source")
    return {"ports": 17, "package_db_checked": bool(pin_db), "external_io_v": 3.3,
            "onboard_reset_v": 1.8, "board_measurements": "NOT VERIFIED"}


def parse_reports(timing, pnr, netlist):
    require("GW1NR-LV9QN88PC6/I5" in timing and "V1.9.11.03" in timing,
            "Unexpected device/tool report; review parser for a new version")
    def number(pattern, text=timing, integer=False):
        match = re.search(pattern, text, re.M)
        require(match is not None, "Missing report field: " + pattern)
        return int(match[1]) if integer else float(match[1])
    result = {"fmax_mhz": number(r'clk_27m\s+27\.000\(MHz\)\s+([\d.]+)\(MHz\)'),
              "setup_violated_endpoints": number(r'<Numbers of Setup Violated Endpoints>:(\d+)', integer=True),
              "hold_violated_endpoints": number(r'<Numbers of Hold Violated Endpoints>:(\d+)', integer=True),
              "paths_analyzed": number(r'<Numbers of Paths Analyzed>:(\d+)', integer=True),
              "endpoints_analyzed": number(r'<Numbers of Endpoints Analyzed>:(\d+)', integer=True)}
    result["delay_models"] = {kind: re.search('<' + kind + r' Delay Model>:(.+)', timing)[1].strip()
                              for kind in ["Setup", "Hold"]}
    body = timing[timing.index("Note:Core Timing Report"):]
    for index, kind in enumerate(["Setup", "Hold", "Recovery", "Removal"], 1):
        start = body.index(f"3.1.{index} {kind} Paths Table")
        table = body[start:body.find("\n3.", start + 5)]
        result["worst_" + kind.lower() + "_slack_ns"] = number(r'^\s+1\s+(-?[\d.]+)\s', table)
    result["tns_ns"] = {kind: number(r'clk_27m\s+' + kind + r'\s+(-?[\d.]+)') for kind in ["setup", "hold"]}
    active = re.findall(r'^\s+(TC_\w+)\s+(\w+)\s', body, re.M)
    require(len(active) == 9 and all(state == "Actived" for _, state in active), "Inactive/missing SDC constraint")
    result["active_constraints"] = len(active)
    result["asynchronous_first_stage_exceptions"] = 4
    # This Gowin text format provides no exhaustive unconstrained-path counter.
    # Never silently turn an absent metric into zero.
    result["unconstrained_path_count"] = None
    result["unconstrained_note"] = "Not enumerated by Gowin automatic report; all17 boundary ports inventoried,9 constraints active;4 first-sampler D pins intentionally excepted. CDC/MTBF and board IO remain separate sign-off."
    result["lut4"] = number(r'\((\d+) LUT,', pnr, integer=True)
    result["alu"] = number(r'LUT, (\d+) ALU,', pnr, integer=True)
    result["logic_cells"] = number(r'^\s+Logic\s+\| (\d+)/8640', pnr, integer=True)
    result["logic_ff"] = number(r'Logic Register as FF\s*\|\s*(\d+)/', pnr, integer=True)
    result["io_ff"] = number(r'I/O Register as FF\s*\|\s*(\d+)/', pnr, integer=True)
    result["latches"] = number(r'Logic Register as Latch\s*\|\s*(\d+)/', pnr, integer=True)
    result["io_latches"] = number(r'I/O Register as Latch\s*\|\s*(\d+)/', pnr, integer=True)
    result["io_ports"] = number(r'I/O Port\s*\|\s*(\d+)/71', pnr, integer=True)
    result["io_buffers"] = number(r'I/O Buf\s*\|\s*(\d+)', pnr, integer=True)
    result["bram_primitives"] = len(re.findall(r'(?m)^(?:SP|SPX9|SDP|SDPX9|DPB|DPX9B)\s+\S+\s*\(', netlist))
    for name in ["clk", "arst_n", "rx", "left_out", "right_out", "motion_permit_async",
                 "recovery_req_async", "safety_ok_async", "gate_fault_n_async"]:
        require("IBUF " + name + "_ibuf" in netlist, "Input cone optimized away: " + name)
    for sampler in SAMPLERS:
        require(sampler in netlist, "CDC sampler optimized away: " + sampler)
    flops = {}
    for name, block in re.findall(r'^DFF\w+\s+(\S+)\s*\((.*?)\);', netlist, re.M | re.S):
        output = re.search(r'\.Q\(([^)]+)\)', block)
        if output:
            flops[output[1].strip()] = name
    for signal in ["por_ready", *(f"por_count[{i}]" for i in range(10))]:
        require(signal in flops, "POR register optimized away: " + signal)
        require(re.search(r'defparam\s+' + re.escape(flops[signal]) + r"\s*\.INIT=1'b0;", netlist),
                "POR INIT missing: " + signal)
    result["mapped_encoder_inputs_present"] = True
    result["por_initialization_checked"] = True
    result["timing_pass"] = (result["fmax_mhz"] >= 27 and
        result["setup_violated_endpoints"] == result["hold_violated_endpoints"] == 0 and
        all(result["worst_" + k + "_slack_ns"] >= 0 for k in ["setup", "hold", "recovery", "removal"]) and
        all(v == 0 for v in result["tns_ns"].values()) and result["latches"] == result["io_latches"] == 0 and
        result["io_ports"] == result["io_buffers"] == 17)
    return result


def check_routed_pins(cst, target=TARGET):
    pins = json.loads((target / "pinout.json").read_text())["pins"]
    locs = re.findall(r'IO_LOC\s+"(\w+)"\s+(\d+)\s*;', cst)
    ports = re.findall(r'IO_PORT\s+"(\w+)"\s+([^;]+);', cst)
    require(len(locs) == len(ports) == 17 and dict(locs) ==
            {p["signal"]: str(p["package_pin"]) for p in pins}, "Routed package pin drift")
    for pin in pins:
        options = dict(re.findall(r'(\w+)=([\w.]+)', dict(ports)[pin["signal"]]))
        require(options.get("IO_TYPE") == pin["io_standard"] and
                options.get("BANK_VCCIO") == str(pin["vccio"]), "Routed electrical drift")


def execute(command, log, env=None, timeout=2400, cwd=ROOT):
    with log.open("w", encoding="utf-8") as handle:
        process = subprocess.run(list(map(str, command)), cwd=cwd, env=env, stdout=handle,
                                 stderr=subprocess.STDOUT, timeout=timeout)
    require(process.returncode == 0, f"Command failed ({process.returncode}); see {log}")
    return log.read_text(encoding="utf-8", errors="replace")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gw-sh", default=os.environ.get("GOWIN_SH") or shutil.which("gw_sh"))
    parser.add_argument("--iverilog", default=shutil.which("iverilog"))
    parser.add_argument("--vvp", default=shutil.which("vvp"))
    parser.add_argument("--rtl-tests", choices=["full", "quick", "skip"], default="full")
    parser.add_argument("--audit-only", action="store_true")
    parser.add_argument("--post-map-test", action="store_true")
    args = parser.parse_args()
    BUILD.mkdir(parents=True, exist_ok=True)
    gowin = Path(args.gw_sh).resolve() if args.gw_sh else None
    ide = gowin.parent.parent if gowin else None
    db = ide / "data/device/GW1NR-9C/QFN88P.json" if ide else None
    result = {"pin_audit": audit(pin_db=db), "source_sha256": source_hashes(),
              "commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
              "dirty_tracked_source": bool(subprocess.check_output(["git", "diff", "--name-only"], cwd=ROOT)),
              "hardware": "NOT VERIFIED", "programming_performed": False}
    if args.audit_only:
        print(json.dumps(result["pin_audit"], indent=2))
        return 0
    require(gowin and gowin.is_file(), "Set --gw-sh or GOWIN_SH to installed Gowin gw_sh")
    started = time.monotonic()
    if args.rtl_tests != "skip":
        require(args.iverilog and args.vvp, "Icarus/VVP required for RTL regression")
        command = [sys.executable, ROOT / "tools/run_fpga_tests.py", "--iverilog", args.iverilog,
                   "--vvp", args.vvp, "--timeout", "1800", "--report", "fpga/build/tang-regression-report.json",
                   "--require-module-coverage"]
        if args.rtl_tests == "full":
            command.append("--full-timing")
        execute(command, BUILD / "rtl-regression.log", timeout=14400)
    env = dict(os.environ, AWCAR_BUILD_DIR=str(BUILD / "gowin"), AWCAR_GOWIN_FLOW="all")
    log = execute([gowin, TARGET / "build.tcl"], BUILD / "gowin-build.log", env)
    require("ERROR" not in log and "Bitstream generation completed" in log, "Incomplete Gowin build")
    warnings = [line for line in log.splitlines() if re.search(r'WARN\s+\(', line)]
    require(all("(NL0002)" in line or "(EX3791)" in line and "pwm_pair.sv\":37" in line
                for line in warnings), "New Gowin warning requires review")
    base = BUILD / "gowin/aw_car_nano9k/impl/pnr"
    tr, rpt, vo = [base / ("aw_car_nano9k" + suffix) for suffix in [".tr", ".rpt.txt", ".vo"]]
    result["timing"] = parse_reports(tr.read_text(), rpt.read_text(), vo.read_text())
    check_routed_pins((base / "aw_car_nano9k.io.cst").read_text())
    result["routed_pin_contract"] = "PASS"
    result["warnings"] = warnings
    result["report_sha256"] = {p.name: sha(p) for p in [tr, rpt, vo, base / "aw_car_nano9k.fs"]}
    if args.post_map_test:
        require(args.iverilog and args.vvp, "Icarus/VVP required for post-map test")
        sim_env = dict(os.environ)
        sim_env["PATH"] = str(Path(args.iverilog).resolve().parent) + os.pathsep + sim_env.get("PATH", "")
        test = BUILD / "mapped-functional.vvp"
        execute([args.iverilog, "-g2012", "-s", "tb_nano9k_mapped", "-o", test,
                 ide / "simlib/gw1n/prim_sim.v", vo, TARGET / "tb_nano9k_mapped.sv"],
                BUILD / "mapped-compile.log", sim_env)
        output = execute([args.vvp, test], BUILD / "mapped-functional.log", sim_env, timeout=1200)
        require("PASS tb_nano9k_mapped:" in output, "Missing mapped test PASS marker")
        result["mapped_functional_test"] = "PASS; no SDF, physical timing covered by STA separately"
    result["wall_seconds"] = round(time.monotonic() - started, 3)
    result["rtl_tests"] = args.rtl_tests
    (BUILD / "build-report.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    require(result["timing"]["timing_pass"], "STA/latch/pad audit failed; see build-report.json")
    print(json.dumps(result["timing"], indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        print("FAIL:", error, file=sys.stderr)
        raise SystemExit(1)
