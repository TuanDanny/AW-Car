"""Single native project, unresolved physical pads, and preservation of manual edits."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
PCB = ROOT / "hardware/pcb"


class PcbSourceTests(unittest.TestCase):
    def test_one_wiring_sheet_without_legacy_subprojects_or_fabrication(self):
        self.assertEqual([p.name for p in PCB.glob("*.kicad_sch")], ["aw_car.kicad_sch"])
        source = (PCB/"aw_car.kicad_sch").read_text(encoding="utf-8")
        self.assertIn('(paper "A1")', source)
        self.assertNotIn('(sheet ', source)
        self.assertFalse((PCB/"kicad").exists())
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
