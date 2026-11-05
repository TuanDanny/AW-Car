"""Target audit must reject unsafe/drifting constraints, not merely build them."""
from pathlib import Path
import importlib.util
import json
import shutil
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("tang_target", ROOT / "tools/build_tang_nano9k.py")
target = importlib.util.module_from_spec(spec)
spec.loader.exec_module(target)


class TangNanoTargetTests(unittest.TestCase):
    def fixture(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        root = Path(directory.name)
        shutil.copytree(ROOT / "fpga/rtl", root / "fpga/rtl")
        shutil.copytree(target.TARGET, root / "fpga/targets/tang_nano9k")
        return root

    def test_actual_target_is_complete(self):
        self.assertEqual(target.audit()["ports"], 17)

    def test_duplicate_package_pin_rejected(self):
        root = self.fixture()
        path = root / "fpga/targets/tang_nano9k/pinout.json"
        data = json.loads(path.read_text())
        data["pins"][3]["package_pin"] = data["pins"][2]["package_pin"]
        path.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            target.audit(root)

    def test_33v_signal_cannot_use_18v_bank(self):
        root = self.fixture()
        path = root / "fpga/targets/tang_nano9k/pinout.json"
        data = json.loads(path.read_text())
        data["pins"][2]["bank"] = 3
        path.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError, "bank voltage"):
            target.audit(root)

    def test_cst_remap_or_voltage_drift_rejected(self):
        for before, after in [('"rx" 25;', '"rx" 79;'), ('LVCMOS33', 'LVCMOS18')]:
            with self.subTest(change=after):
                root = self.fixture()
                path = root / "fpga/targets/tang_nano9k/aw_car_nano9k.cst"
                path.write_text(path.read_text().replace(before, after, 1))
                with self.assertRaises(ValueError):
                    target.audit(root)

    def test_blanket_false_path_rejected(self):
        root = self.fixture()
        path = root / "fpga/targets/tang_nano9k/aw_car_nano9k.sdc"
        path.write_text(path.read_text().replace(target.SAMPLERS[0] + "/D", "*/D"))
        with self.assertRaises(ValueError):
            target.audit(root)

    def test_extra_named_false_path_endpoint_rejected(self):
        root = self.fixture()
        path = root / "fpga/targets/tang_nano9k/aw_car_nano9k.sdc"
        path.write_text(path.read_text().replace(target.SAMPLERS[-1] + "/D}",
            target.SAMPLERS[-1] + "/D critical_safety_ff/D}"))
        with self.assertRaisesRegex(ValueError, "extra false-path"):
            target.audit(root)

    def test_missing_or_mismatched_gprj_source_rejected(self):
        root = self.fixture()
        path = root / "fpga/targets/tang_nano9k/aw_car_nano9k.gprj"
        path.write_text(path.read_text().replace("aw_car_nano9k.sv", "tb_nano9k_mapped.sv"))
        with self.assertRaisesRegex(ValueError, "source list"):
            target.audit(root)

    def test_incomplete_report_never_becomes_pass(self):
        with self.assertRaises(ValueError):
            target.parse_reports("27MHz PASS", "", "")

    def test_routed_constraints_must_match_pin_contract(self):
        cst = (target.TARGET / "aw_car_nano9k.cst").read_text()
        target.check_routed_pins(cst)
        with self.assertRaisesRegex(ValueError, "Routed package"):
            target.check_routed_pins(cst.replace('"rx" 25;', '"rx" 79;'))


if __name__ == "__main__":
    unittest.main()
