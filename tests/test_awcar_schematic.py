"""KiCad round-trip and harmful wiring mutations, not a hardware simulation."""
import copy
import json
from pathlib import Path
import os
import shutil
import subprocess
import tempfile
import unittest
import xml.etree.ElementTree as ET

from tools.check_awcar_schematic import check
from tools.generate_awcar_schematic import block

ROOT = Path(__file__).resolve().parents[1]
CLI = os.environ.get("KICAD_CLI") or shutil.which("kicad-cli")
if not CLI and Path("D:/APP/KiCad/bin/kicad-cli.exe").exists():
    CLI = "D:/APP/KiCad/bin/kicad-cli.exe"


@unittest.skipUnless(CLI, "KiCad CLI required for native schematic round-trip")
class SchematicContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="awcar-schematic-")
        cls.path = Path(cls.temp.name) / "export.xml"
        result = subprocess.run([CLI, "sch", "export", "netlist", "--format", "kicadxml",
            "-o", str(cls.path), str(ROOT/"hardware/pcb/aw_car.kicad_sch")],
            capture_output=True, text=True, timeout=45)
        if result.returncode:
            raise RuntimeError(result.stdout + result.stderr)
        cls.original = ET.parse(cls.path)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def setUp(self):
        self.tree = copy.deepcopy(self.original)

    def run_check(self):
        self.tree.write(self.path, encoding="utf-8", xml_declaration=True)
        return check(self.path)

    def net(self, name):
        return next(n for n in self.tree.findall("./nets/net") if n.attrib["name"].removeprefix("/")==name)

    def move(self, ref, pin, destination):
        for net in self.tree.findall("./nets/net"):
            for node in list(net):
                if node.attrib.get("ref")==ref and node.attrib.get("pin")==pin:
                    net.remove(node)
                    self.net(destination).append(node)
                    return
        self.fail(f"Missing source pin {ref}.{pin}")

    def test_native_kicad_netlist_matches_contract_but_not_released(self):
        d=self.run_check()
        self.assertTrue(d["pin_contract_passed"])
        self.assertEqual(len(d["checks"]),8)
        self.assertTrue(d["manifest_equivalence_passed"])
        self.assertFalse(d["schematic_release_ready"])

    def test_uart_rx_swap_rejected(self):
        self.move("U2","GPIO14","MTN_TX_BRN_RX")
        with self.assertRaises(ValueError): self.run_check()

    def test_btl_speaker_ground_rejected(self):
        self.move("J4","2","GND")
        with self.assertRaises(ValueError): self.run_check()

    def test_shared_bridge_output_rejected(self):
        self.move("U4","BOUT1","L_AOUT1")
        with self.assertRaises(ValueError): self.run_check()

    def test_raw_5v_encoder_bypass_rejected(self):
        self.move("U3","P27","ENC_L_RAW")
        with self.assertRaises(ValueError): self.run_check()

    def test_joined_module_3v3_outputs_rejected(self):
        self.move("U3","3V3","3V3_BRAIN")
        with self.assertRaises(ValueError): self.run_check()

    def test_sleep_tied_to_vm_rejected(self):
        self.move("U4","STBY","VM_MOTOR")
        with self.assertRaises(ValueError): self.run_check()

    def test_clamp_transistor_emitter_collector_swap_rejected(self):
        self.move("Q101","1","STBY_L")
        self.move("Q101","3","GND")
        with self.assertRaises(ValueError): self.run_check()

    def test_duplicate_pin_in_export_rejected(self):
        node=ET.SubElement(self.net("GND"),"node",ref="U1",pin="GPIO17")
        self.assertIsNotNone(node)
        with self.assertRaises(ValueError): self.run_check()

    def test_future_i2c_bus_short_rejected(self):
        self.move("J21", "3", "SENSOR_SCL_TBD")
        with self.assertRaises(ValueError): self.run_check()

    def test_protected_pack_fuse_bypass_rejected(self):
        self.move("F1", "1", "PACK_FUSED")
        with self.assertRaises(ValueError): self.run_check()

    def test_signal_pins_connected_by_wires_even_without_net_labels(self):
        # Remove every label, then have KiCad independently resolve physical
        # wires. A label-only collection of disconnected modules fails here.
        source = (ROOT/"hardware/pcb/aw_car.kicad_sch").read_text(encoding="utf-8")
        for marker in ("(label ", "(global_label "):
            while marker in source:
                start = source.index(marker)
                expression = block(source, start)
                source = source[:start] + source[start+len(expression):]
        path = Path(self.temp.name)/"wire-only.kicad_sch"
        exported = Path(self.temp.name)/"wire-only.xml"
        path.write_text(source, encoding="utf-8")
        result = subprocess.run([CLI, "sch", "export", "netlist", "--format", "kicadxml",
            "-o", str(exported), str(path)], capture_output=True, text=True, timeout=45)
        self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
        groups = {frozenset((n.attrib["ref"], n.attrib["pin"]) for n in net)
            for net in ET.parse(exported).findall("./nets/net")}
        expected = json.loads((ROOT/"docs/awcar-schematic-parts.json").read_text(encoding="utf-8"))["expected_nets"]
        power = {"GND", "VM_MOTOR", "3V3_BRAIN", "3V3_MOTION", "3V3_TANG", "3V3_SENSORS_TBD",
            "5V_SENSOR_SOURCE_TBD", "5V_BRAIN_SOURCE_TBD", "5V_MOTION_SOURCE_TBD", "5V_TANG_SOURCE_TBD", "5V_AMP_SOURCE_TBD"}
        for name, pins in expected.items():
            if name not in power and not name.startswith("unconnected-"):
                self.assertIn(frozenset(tuple(pin) for pin in pins), groups, name)
