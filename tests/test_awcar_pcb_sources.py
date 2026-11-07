"""Single native project, unresolved physical pads, and preservation of manual edits."""
import json
import re
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from tools.generate_awcar_schematic import block

ROOT = Path(__file__).resolve().parents[1]
PCB = ROOT / "hardware/pcb"


class PcbSourceTests(unittest.TestCase):
    def test_one_wiring_sheet_without_legacy_subprojects_or_fabrication(self):
        self.assertEqual([p.name for p in PCB.glob("*.kicad_sch")], ["aw_car.kicad_sch"])
        source = (PCB/"aw_car.kicad_sch").read_text(encoding="utf-8")
        self.assertIn('(paper "A3")', source)
        self.assertNotIn('(sheet ', source)
        # KiCad can create a local KiCad/10.x document directory on Windows;
        # that cache is distinct from the removed hierarchical project.
        self.assertFalse(list((PCB/"kicad").glob("*.kicad_sch")))
        self.assertFalse(list((PCB/"kicad").glob("*.kicad_pro")))
        self.assertFalse(list(PCB.glob("*.kicad_pcb")))
        self.assertFalse(list(PCB.glob("*.gbr")))
        self.assertFalse(list(PCB.glob("pcb-*.svg")))

    def test_local_libraries_and_project_open_without_old_directory(self):
        project = json.loads((PCB/"aw_car.kicad_pro").read_text(encoding="utf-8"))
        self.assertEqual(project["meta"]["filename"], "aw_car.kicad_pro")
        for name in ("aw_car.kicad_sym", "sym-lib-table", "generic-clamp.lib"):
            self.assertTrue((PCB/name).is_file(), name)
        library_table = (PCB/"sym-lib-table").read_text(encoding="utf-8")
        self.assertIn('${KIPRJMOD}/aw_car.kicad_sym', library_table)
        self.assertNotIn('/kicad/', library_table)

    def test_signal_inputs_left_outputs_right_in_native_symbol_library(self):
        raw = (PCB/"aw_car.kicad_sym").read_text(encoding="utf-8")
        checked = 0
        for m in re.finditer(r'\(pin\s+(input|output)\s+\w+\s', raw):
            pin = block(raw, m.start())
            angle = float(re.search(r'\(at\s+[-+.\d]+\s+[-+.\d]+\s+([-+.\d]+)', pin)[1])
            self.assertEqual(angle, 0 if m[1] == "input" else 180, pin)
            checked += 1
        self.assertGreater(checked, 25)

    def test_controller_supply_top_and_ground_bottom(self):
        raw = (PCB/"aw_car.kicad_sym").read_text(encoding="utf-8")
        for name in ("Brain_Logical", "Motion_Logical", "Tang_Logical"):
            match = re.search(r'\(symbol "'+name+r'"\s', raw)
            symbol = block(raw, match.start())
            pins = {}
            for m in re.finditer(r'\(pin\s+\w+\s+\w+\s', symbol):
                pin = block(symbol, m.start())
                number = re.search(r'\(number "([^"]+)"', pin)[1]
                pins[number] = float(re.search(r'\(at\s+[-+.\d]+\s+[-+.\d]+\s+([-+.\d]+)', pin)[1])
            self.assertEqual(pins["5V"], 270)
            self.assertEqual(pins["3V3"], 270)
            self.assertEqual(pins["GND"], 90)

    def test_generator_refuses_to_overwrite_manual_source(self):
        with tempfile.TemporaryDirectory(prefix="awcar-manual-edit-") as directory:
            path = Path(directory)/"aw_car.kicad_sch"
            original = b"manual edits must survive\n"
            path.write_bytes(original)
            result = subprocess.run([sys.executable, str(ROOT/"tools/generate_awcar_schematic.py"),
                "--output", directory], capture_output=True, text=True, timeout=10)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("refusing to overwrite", result.stderr)
            self.assertEqual(path.read_bytes(), original)
