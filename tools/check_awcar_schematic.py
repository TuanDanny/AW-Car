"""Check KiCad-exported XML connectivity against the AW-Car firmware contract.

This is a topology check, not ERC, a footprint check, or electrical sign-off.
"""
import argparse
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]


class Netlist:
    def __init__(self, source):
        self.root = ET.parse(source).getroot()
        self.pins = {}
        self.nets = {}
        self.components = {c.attrib["ref"]: c for c in self.root.findall("./components/comp")}
        for net in self.root.findall("./nets/net"):
            # A root-sheet local label has a leading '/' in KiCad XML.
            # Do not flatten child-sheet paths: those would hide hierarchy mistakes.
            name = net.attrib["name"].removeprefix("/")
            if name in self.nets:
                raise ValueError(f"Duplicate net name: {name}")
            nodes = {(n.attrib["ref"], n.attrib["pin"]) for n in net.findall("node")}
            self.nets[name] = nodes
            for node in nodes:
                if node in self.pins:
                    raise ValueError(f"Duplicate pin: {node}")
                self.pins[node] = name

    def require(self, name, *pins):
        for ref, pin in pins:
            actual = self.pins.get((ref, pin))
            if actual != name:
                raise ValueError(f"{ref}.{pin}: expected {name}, got {actual}")

    def together(self, *pins):
        names = [self.pins.get(pin) for pin in pins]
        if None in names or len(set(names)) != 1:
            raise ValueError(f"Required connection is open/incorrect: {pins}: {names}")
        return names[0]


def check(source):
    n = Netlist(source)
    checks = []
    inputs = json.loads((ROOT / "docs/awcar-schematic-design-inputs.json").read_text(encoding="utf-8"))
    refs = {"BRAIN": "U1", "MOTION": "U2", "FPGA": "U3"}
    for row in inputs["net_contract"]:
        pins = [(refs[p["module"]], ("P" if p["module"] == "FPGA" else "") + p["logical_pin"])
                for p in row["endpoints"]]
        n.require(row["net"], *pins)
    checks.append("firmware_uart_and_recovery_permit_contract")
    if ("U2", "GPIO17") in n.pins or ("U2", "GPIO18") in n.pins:
        raise ValueError("Damaged Motion GPIO17/18 used")
    checks.append("damaged_motion_pins_unused")
    for net, ref, pin in [("MIC_WS", "U1", "GPIO4"), ("MIC_BCLK", "U1", "GPIO5"),
                         ("MIC_SD", "U1", "GPIO6"), ("AMP_DIN", "U1", "GPIO7"),
                         ("AMP_BCLK", "U1", "GPIO15"), ("AMP_LRCLK", "U1", "GPIO16"),
                         ("OLED_SDA", "U1", "GPIO41"), ("OLED_SCL", "U1", "GPIO42")]:
        n.require(net, (ref, pin))
    n.require("SPK_PLUS", ("U6", "SPK+"), ("J4", "1"))
    n.require("SPK_MINUS", ("U6", "SPK-"), ("J4", "2"))
    if n.pins[("J4", "1")] == n.pins[("J4", "2")] or "GND" in (
            n.pins[("J4", "1")], n.pins[("J4", "2")]):
        raise ValueError("BTL speaker output shorted or grounded")
    checks.append("audio_oled_gpio_and_floating_speaker")
    for side, ref, p1, p2 in [("L", "U4", "P35", "P40"), ("R", "U5", "P41", "P42")]:
        n.require(f"DRV_{side}_IN1", ("U3", p1), (ref, "AIN1"), (ref, "BIN1"))
        n.require(f"DRV_{side}_IN2", ("U3", p2), (ref, "AIN2"), (ref, "BIN2"))
        n.require("VM_MOTOR", (ref, "VM"))
        n.require("GND", (ref, "GND"))
    motor_nets = [n.pins[(ref, p)] for ref in ("U4", "U5")
                  for p in ("AOUT1", "AOUT2", "BOUT1", "BOUT2")]
    if len(set(motor_nets)) != 8 or {"GND", "VM_MOTOR"} & set(motor_nets):
        raise ValueError("Independent H-bridge outputs shorted")
    checks.append("four_independent_h_bridges_and_correct_direction_inputs")
    rails = [n.pins[(ref, pin)] for ref in ("U1", "U2", "U3") for pin in ("5V", "3V3")]
    if len(set(rails)) != 6:
        raise ValueError("Unreviewed shared module power source/3V3 rail")
    checks.append("local_3v3_rails_and_pending_usb_sources_separate")
    for side, start, driver in [("L", 100, "U4"), ("R", 110, "U5")]:
        qc, qr = f"Q{start+1}", f"Q{start+2}"
        rb, rp, ri, rd = (f"R{start+i}" for i in range(1, 5))
        n.require("VM_MOTOR", (rb, "1"), (rp, "1"))
        n.require(f"STBY_{side}", (qc, "3"), (rp, "2"), (driver, "STBY"))
        n.require("GND", (qc, "1"), (qr, "1"), (rd, "2"))
        n.require("GATE_ALLOW", (ri, "1"))
        base = n.together((qc, "2"), (rb, "2"), (qr, "3"))
        release = n.together((qr, "2"), (ri, "2"), (rd, "1"))
        if base in ("VM_MOTOR", "GATE_ALLOW", "GND") or release in ("VM_MOTOR", "GATE_ALLOW", "GND", base):
            raise ValueError("Clamp isolation/base network shorted")
    checks.append("both_candidate_stby_clamps_no_vm_to_gpio")
    n.require("ENC_L_RAW", ("U7", "OUT"), ("U9", "1"))
    n.require("ENC_R_RAW", ("U8", "OUT"), ("U9", "3"))
    n.require("ENC_L_CONDITIONED", ("U9", "6"), ("U3", "P27"))
    n.require("ENC_R_CONDITIONED", ("U9", "4"), ("U3", "P28"))
    n.require("3V3_MOTION", ("U9", "5"), ("U10", "5"))
    checks.append("single_out_encoder_raw_and_3v3_conditioned_nets_separate")
    baseline = json.loads((ROOT / "docs/awcar-schematic-parts.json").read_text(encoding="utf-8"))
    expected = {name: {tuple(pin) for pin in pins} for name, pins in baseline["expected_nets"].items()}
    if n.nets != expected:
        different = [name for name in sorted(set(n.nets) | set(expected)) if n.nets.get(name) != expected.get(name)]
        raise ValueError(f"Connection differs from reviewed manifest: {different}")
    if set(n.components) != {p["ref"] for p in baseline["parts"]}:
        raise ValueError("Component inventory differs from reviewed manifest")
    checks.append("all_nets_and_components_match_reviewed_manifest")
    return {"pin_contract_passed": True, "manifest_equivalence_passed": True, "checks": checks, "components": len(n.components),
            "nets": len(n.nets), "exported_netlist_sha256": hashlib.sha256(Path(source).read_bytes()).hexdigest(),
            "schematic_release_ready": False,
            "limits": "Logical module IDs only; power/gate/USB/footprints unresolved. Not ERC/electrical/hardware sign-off."}


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("netlist", type=Path)
    p.add_argument("--output", type=Path)
    a = p.parse_args()
    result = check(a.netlist)
    text = json.dumps(result, indent=2) + "\n"
    if a.output:
        a.output.parent.mkdir(parents=True, exist_ok=True)
        a.output.write_text(text, encoding="utf-8")
    print(text, end="")
