"""Simulate candidate STBY clamps read from KiCad's exported XML netlist.

Uses ngspice's real shared library. R/Q connectivity is not reimplemented.
The NPN and driver input models below are declared GENERIC approximations,
not manufacturer-validated transistor/DRV8833 models or safety certification.
"""
import argparse
import ctypes as C
import hashlib
import itertools
import json
import os
from pathlib import Path

from check_awcar_schematic import Netlist, check


class Vector(C.Structure):
    _fields_ = [("name", C.c_char_p), ("type", C.c_int), ("flags", C.c_short),
                ("real", C.POINTER(C.c_double)), ("complex", C.c_void_p), ("length", C.c_int)]


class Spice:
    def __init__(self, dll):
        self.scope = os.add_dll_directory(str(dll.parent)) if os.name == "nt" else None
        self.lib = C.CDLL(str(dll))
        self.messages, self.exits = [], []
        self.send_type = C.CFUNCTYPE(C.c_int, C.c_char_p, C.c_int, C.c_void_p)
        self.exit_type = C.CFUNCTYPE(C.c_int, C.c_int, C.c_bool, C.c_bool, C.c_int, C.c_void_p)
        self.send = self.send_type(self._send)
        self.exit = self.exit_type(self._exit)
        self.lib.ngSpice_Init.argtypes = [C.c_void_p] * 7
        self.lib.ngSpice_Init.restype = C.c_int
        self.lib.ngSpice_Command.argtypes = [C.c_char_p]
        self.lib.ngSpice_Command.restype = C.c_int
        self.lib.ngSpice_Circ.argtypes = [C.POINTER(C.c_char_p)]
        self.lib.ngSpice_Circ.restype = C.c_int
        self.lib.ngGet_Vec_Info.argtypes = [C.c_char_p]
        self.lib.ngGet_Vec_Info.restype = C.POINTER(Vector)
        if self.lib.ngSpice_Init(self.send, None, self.exit, None, None, None, None):
            raise RuntimeError("ngspice initialization failed")
        self.command("version -f")
        self.version_log = list(self.messages)

    def _send(self, message, ident, user):
        self.messages.append(message.decode("utf-8", errors="replace"))
        return 0

    def _exit(self, status, immediate, quitexit, ident, user):
        self.exits.append(status)
        return 0

    def command(self, command):
        if self.lib.ngSpice_Command(command.encode("ascii")):
            raise RuntimeError(f"ngspice command failed: {command}")

    def run(self, lines):
        self.command("destroy all")
        self.messages.clear()
        self.exits.clear()
        data = [line.encode("ascii") for line in lines]
        array = (C.c_char_p * (len(data)+1))(*data, None)
        if self.lib.ngSpice_Circ(array):
            raise RuntimeError("ngspice rejected circuit")
        self.command("run")
        errors = [s for s in self.messages if "error" in s.lower() or "failed" in s.lower()]
        if self.exits or errors:
            raise RuntimeError(f"ngspice simulation failed: {self.exits}, {errors}")

    def vector(self, name):
        p = self.lib.ngGet_Vec_Info(name.encode("ascii"))
        if not p or p.contents.length < 1 or not p.contents.real:
            raise RuntimeError(f"Missing simulation vector: {name}")
        return [p.contents.real[i] for i in range(p.contents.length)]


def resistor(value):
    suffixes = {"k": 1000, "m": .001, "meg": 1e6}
    lower = value.lower()
    for suffix, factor in suffixes.items():
        if lower.endswith(suffix):
            return float(lower[:-len(suffix)]) * factor
    return float(lower)


def circuit(n, vm, allow, beta, pullup, tolerance=1.0, transient=False, cap=100e-12):
    aliases = {"GND": "0", "VM_MOTOR": "vm", "GATE_ALLOW": "allow", "STBY_L": "sleep_l", "STBY_R": "sleep_r"}
    for i, name in enumerate(sorted(n.nets)):
        aliases.setdefault(name, f"n{i}")
    pin = lambda ref, number: aliases[n.pins[(ref, str(number))]]
    lines = ["AW-Car candidate STBY output stages - generic model, NOT complete gate"]
    lines += [f".model QGEN NPN(IS=6.7f BF={beta} VAF=80 IKF=.1 CJE=8p CJC=4p TF=.3n)",
              ".model DZGEN D(BV=6.5 IBV=1u IS=1f)", ".options reltol=1e-5 abstol=1e-12"]
    for ref in sorted(n.components):
        if ref not in {f"{prefix}{i}" for prefix, seq in [("R", (101,102,103,104,111,112,113,114)),
                                                       ("Q", (101,102,111,112))] for i in seq}:
            continue
        if ref.startswith("R"):
            value = resistor(n.components[ref].findtext("value")) * tolerance
            lines.append(f"{ref} {pin(ref,1)} {pin(ref,2)} {value:g}")
        else:
            # KiCad Q_NPN_EBC / 2N3904 logical numbering: 1E, 2B, 3C.
            lines.append(f"{ref} {pin(ref,3)} {pin(ref,2)} {pin(ref,1)} QGEN")
    for side in ("l", "r"):
        lines += [f"Rmodule_{side} vm sleep_{side} {pullup:g}",
                  f"Rinternal_{side} sleep_{side} 0 500k", f"Dz_{side} 0 sleep_{side} DZGEN",
                  f"Cinput_{side} sleep_{side} 0 {cap:g}"]
    if transient:
        lines += [f"Vvm vm 0 PWL(0 0 1m 0 1.001m {vm} 30m {vm})",
                  "Vallow allow 0 PWL(0 0 5m 0 5.001m 3.3 15m 3.3 15.001m 0 30m 0)",
                  ".tran 2u 30m 0 1u"]
    else:
        lines.append(f"Vvm vm 0 DC {vm}")
        lines.append("Rfloat allow 0 1G" if allow is None else f"Vallow allow 0 DC {allow}")
        lines.append(".op")
    return lines + [".end"]


def run(netlist, dll, output):
    check(netlist)
    n = Netlist(netlist)
    output.mkdir(parents=True, exist_ok=True)
    sim = Spice(dll)
    results = []
    for vm, beta, pullup, allow in itertools.product((5.5,6.0,7.4,8.4), (40,100,300),
                                                   (20000,47000,75000), (None,0,.4,2.4,3.3)):
        lines = circuit(n, vm, allow, beta, pullup)
        sim.run(lines)
        volts = [sim.vector("v(sleep_"+side+")")[0] for side in ("l","r")]
        active = allow is not None and allow >= 2.4
        passed = all(v >= 2.5 for v in volts) if active else all(v <= .5 for v in volts)
        results.append(dict(vm=vm, beta=beta, module_pullup=pullup, allow=allow,
                            sleep_l_v=volts[0], sleep_r_v=volts[1], passed=passed))
    transients = []
    for cap in (10e-12,100e-12,1e-9):
        lines = circuit(n, 8.4, 3.3, 40, 47000, transient=True, cap=cap)
        stem = "transient-" + f"{cap:g}"
        (output/(stem+".cir")).write_text("\n".join(lines)+"\n",encoding="ascii")
        sim.run(lines)
        t, vm, allow, left, right = [sim.vector(name) for name in ("time", "v(vm)", "v(allow)", "v(sleep_l)", "v(sleep_r)")]
        with (output/(stem+".csv")).open("w",encoding="ascii") as f:
            f.write("time_s,vm_v,allow_v,sleep_l_v,sleep_r_v\n")
            for row in zip(t,vm,allow,left,right):
                f.write(",".join(f"{v:.9g}" for v in row)+"\n")
        # Settled intervals; the model is not proof of a glitch-free startup.
        off = [i for i,x in enumerate(t) if .002 <= x <= .004 or .016 <= x <= .029]
        on = [i for i,x in enumerate(t) if .006 <= x <= .014]
        rise = next((t[i]-.005 for i in range(len(t)) if t[i]>=.005 and left[i]>=2.5),None)
        fall = next((t[i]-.015 for i in range(len(t)) if t[i]>=.015 and left[i]<=.5),None)
        passed = bool(off and on) and all(max(v[i] for i in off)<=.5 and min(v[i] for i in on)>=2.5 for v in (left,right))
        transients.append(dict(input_capacitance_f=cap, settled_intervals_passed=passed,
                               allow_rise_to_vih_s=rise, allow_fall_to_vil_s=fall,
                               limitation="Settled intervals only; no vendor startup/glitch/driver wake certification."))
    report = {"scope":"CANDIDATE_STBY_CLAMPS_ONLY_NOT_COMPLETE_SAFETY_GATE",
              "netlist_sha256":hashlib.sha256(netlist.read_bytes()).hexdigest(),
              "ngspice_dll_sha256":hashlib.sha256(dll.read_bytes()).hexdigest(),
              "simulator":sim.version_log, "model":"GENERIC_NPN_AND_APPROXIMATE_SLEEP_LOAD_NOT_VENDOR_VALIDATED",
              "dc_cases":results, "dc_passed":sum(r["passed"] for r in results),
              "transients":transients, "passed":all(r["passed"] for r in results) and all(r["settled_intervals_passed"] for r in transients),
              "release_ready":False,
              "limits":["No latch/E-stop/clock watchdog implemented by these output stages.",
                        "Real STBY silicon, pull-up and module current/voltage must be measured.",
                        "No DSN6000AUD regulator, cell/BMS/charger, motor, thermal or PCB model.",
                        "Do not claim cable-open fail-safe or sub-microsecond glitch immunity.",
                        "Driver wake margin from actual nSLEEP threshold must be reviewed with Motion firmware."]}
    (output/"report.json").write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({k:report[k] for k in ("scope","dc_passed","transients","passed","release_ready")},indent=2))
    return report["passed"]


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("netlist",type=Path)
    p.add_argument("--ngspice",type=Path,default=Path("D:/APP/KiCad/bin/ngspice.dll"))
    p.add_argument("--output",type=Path,default=Path("build/kicad-clamp-sim"))
    a=p.parse_args()
    raise SystemExit(0 if run(a.netlist,a.ngspice,a.output) else 1)
