"""Validate design-source synchronization and no fictional PCB fabrication files."""
import csv
import importlib.util
import json
from pathlib import Path
import unittest


ROOT=Path(__file__).resolve().parents[1]
PCB=ROOT/'hardware'/'pcb'
CAD=ROOT/'hardware'/'cad'
SPEC=importlib.util.spec_from_file_location('pcb_diagram',PCB/'generate_pcb_concept.py')
GEN=importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GEN)


class PcbConceptTests(unittest.TestCase):
    def test_diagram_data_from_cad(self):
        layout=json.loads((CAD/'layout.json').read_text(encoding='utf8'))
        self.assertEqual(GEN.LAYOUT['pcb_concept'],layout['pcb_concept'])
        self.assertEqual(layout['pcb_concept']['controller_carrier']['size'][0],150)
        self.assertEqual(layout['pcb_concept']['power_distribution']['size'][0],36)

    def test_contracts_have_no_fabricated_physical_pin_numbers(self):
        with (PCB/'connector-contract.csv').open(encoding='utf8',newline='') as f:
            rows=list(csv.DictReader(f))
        self.assertGreaterEqual(len(rows),20)
        self.assertEqual(len({r['designator'] for r in rows}),len(rows))
        self.assertTrue(all(r['pinout_status']=='UNASSIGNED' for r in rows))
        keys={r['designator'] for r in rows}
        for k in ('J_ESTOP','J_GATE','J_OUT_FL','J_OUT_FR','J_OUT_RL','J_OUT_RR','J_FPGA','J_BAT'):
            self.assertIn(k.replace('J_FPGA','J_MOTION_FPGA'),keys)

    def test_svgs_are_present_and_carry_nonfabrication_notice(self):
        for name in ('pcb-system-layout.svg','pcb-routing-corridors.svg'):
            content=(PCB/name).read_text(encoding='utf8')
            self.assertIn('CONCEPT ONLY',content)
            self.assertIn('svg',content)
        self.assertFalse(list(PCB.glob('*.gbr')))
        self.assertFalse(list(PCB.glob('*.kicad_pcb')))


if __name__=='__main__':unittest.main()
