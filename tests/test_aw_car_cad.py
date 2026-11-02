"""Geometry-envelope checks for the provisional, non-manufacturing CAD layout."""
import copy
import importlib.util
import json
from pathlib import Path
import unittest


CAD = Path(__file__).resolve().parents[1] / 'hardware' / 'cad'
SPEC = importlib.util.spec_from_file_location('awcar_cad_generator', CAD / 'generate_aw_car.py')
GEN = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GEN)


class CadEnvelopeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.layout=json.loads((CAD/'layout.json').read_text(encoding='utf-8'))

    def test_nominal_layout_passes_but_is_not_manufacturing_validated(self):
        result=GEN.audit(self.layout)
        self.assertEqual(result['status'],'PASS',result['errors'])
        self.assertGreaterEqual(result['battery_ground_clearance_mm'],10)
        self.assertLess(abs(result['estimated_center_xy_mm'][0]),12)
        self.assertLess(abs(result['estimated_center_xy_mm'][1]),12)
        self.assertGreater(result['microphone_speaker_xy_distance_mm'],100)
        self.assertEqual(result['chassis_length_mm'],260)
        self.assertEqual(result['chassis_width_without_tires_mm'],155)
        self.assertEqual(result['outside_wheel_width_mm'],175)
        self.assertEqual(result['track_centers_mm'],155)
        self.assertLess(abs(result['estimated_center_xy_mm'][0]),8)
        self.assertTrue(any('inconsistent' in w for w in result['warnings']))
        self.assertIn('no physical fit',result['validation_scope'])

    def test_revised_two_pcb_roles_and_separate_power(self):
        p=self.layout['pcb_concept']
        self.assertEqual(p['controller_carrier']['size'][:2],[150,78])
        self.assertEqual(p['power_distribution']['size'][:2],[36,25])
        components={o['id']:o for o in self.layout['components']}
        for name in ('controller_carrier','power_distribution'):
            self.assertEqual(components[name]['xyz'],p[name]['xyz'])
        self.assertLess(self.layout['battery']['xyz'][2],components['power_distribution']['xyz'][2])
        self.assertLess(components['power_distribution']['xyz'][2],components['controller_carrier']['xyz'][2])
        self.assertNotIn('bms',components,'Integrated BMS must not be represented as a second loose board')
        self.assertLess(components['buck_logic']['xyz'][0],components['buck_motor']['xyz'][0])
        self.assertGreater(components['drv_left']['xyz'][1],0)
        self.assertLess(components['drv_right']['xyz'][1],0)

    def test_controller_above_carrier_without_collision(self):
        objs={o['id']:o for o in self.layout['components']}
        top=GEN.shape_bounds(objs['controller_carrier'])[2][1]
        for k in ('brain','motion','fpga','imu'):
            z_bottom=GEN.shape_bounds(objs[k])[2][0]
            self.assertGreaterEqual(z_bottom-top,3.0)

    def test_curved_plate_is_symmetric_nonrectangular_and_triangulated(self):
        pts=GEN.deck_outline(self.layout['base'],self.layout['wheel'])
        self.assertGreater(len(pts),20)
        self.assertLess(abs(GEN.polygon_area(pts)),260*155)
        self.assertEqual(len(GEN.triangulate_polygon(pts)),len(pts)-2)
        self.assertAlmostEqual(min(x for x,y in pts),-130)
        self.assertAlmostEqual(max(x for x,y in pts),130)
        self.assertAlmostEqual(max(y for x,y in pts),77.5)
        self.assertEqual(pts[1][0],pts[-1][0])
        self.assertEqual(pts[1][1],-pts[-1][1])

    def test_plate_and_tire_dimensions_checked(self):
        bad=copy.deepcopy(self.layout)
        bad['wheel']['left_y']=70
        self.assertIn('width differs',str(GEN.audit(bad)['errors']))

    def test_encoder_disc_clearance_checked(self):
        bad=copy.deepcopy(self.layout)
        bad['tt_motor']['encoder_disc_y']=26
        self.assertIn('Encoder disc intersects',str(GEN.audit(bad)['errors']))

    def test_visible_wheels_and_encoder_discs_match_reference_identity(self):
        a=GEN.build(self.layout)
        names=[n for n,m,mesh,s in a.solids]
        for prefix,count in [('TIRE_',4),('YELLOW_RIM_',4),
                             ('YELLOW_SPOKE_',20),('INNER_ENCODER_DISC_',4)]:
            self.assertEqual(sum(n.startswith(prefix) for n in names),count)

    def test_battery_floor_collision_detected(self):
        bad=copy.deepcopy(self.layout)
        bad['battery']['xyz'][2]=14
        self.assertEqual(GEN.audit(bad)['status'],'FAIL')

    def test_same_deck_board_collision_detected(self):
        bad=copy.deepcopy(self.layout)
        bad['components'][0]['xyz']=bad['components'][1]['xyz'].copy()
        self.assertIn('intersect',str(GEN.audit(bad)['errors']))

    def test_wrong_driver_side_detected(self):
        bad=copy.deepcopy(self.layout)
        next(x for x in bad['components'] if x['id']=='drv_right')['xyz'][1]=10
        self.assertIn('opposite left/right',str(GEN.audit(bad)['errors']))

    def test_model_exports_are_self_contained_and_in_sync(self):
        a=GEN.build(self.layout)
        self.assertGreater(len(a.solids),40)
        scad=GEN.export_scad(a,self.layout)
        obj,mtl=GEN.export_obj(a)
        html=GEN.export_viewer(a,self.layout)
        self.assertIn('module aw_car_assembly',scad)
        self.assertEqual(obj.count('\ng '),len(a.solids))
        self.assertIn('newmtl wheel',mtl)
        self.assertNotIn('__MODEL__',html)
        self.assertIn('id="scene"',html)
        self.assertNotIn('https://',html)


if __name__=='__main__':unittest.main()
