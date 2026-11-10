import copy
from pathlib import Path
import struct
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'utils'))
from migrate_motion_ota import initial_ota_data,validate_layout
from flash_esp import active_ota


def entry(kind,sub,offset,size):
    return {'type':kind,'subtype':sub,'offset':offset,'size':size,'flags':0}


class Migration(unittest.TestCase):
    def setUp(self):
        self.old={'nvs':entry(1,2,0x9000,0x4000),'phy_init':entry(1,1,0xd000,0x1000),
                  'factory':entry(0,0,0x10000,0x180000),'motioncfg':entry(1,2,0x190000,0x6000)}
        self.new=copy.deepcopy(self.old)
        self.new.update(otadata=entry(1,0,0x1a0000,0x2000),ota_0=entry(0,16,0x200000,0x180000),
                        ota_1=entry(0,17,0x380000,0x180000))
    def test_preserve_legacy_and_reject_relocation(self):
        validate_layout(self.old,self.new)
        for name in self.old:
            altered=copy.deepcopy(self.new);altered[name]['offset']+=4096
            with self.assertRaises(ValueError):validate_layout(self.old,altered)
    def test_reject_unexpected_slot_metadata_or_second_migration(self):
        for name in ('ota_0','ota_1','otadata'):
            changed=copy.deepcopy(self.new);changed[name]['offset']+=4096
            with self.assertRaises(ValueError):validate_layout(self.old,changed)
        with self.assertRaises(ValueError):validate_layout(self.new,self.new)
    def test_initial_valid_slot_and_pending_refusal(self):
        data=initial_ota_data();apps=[self.new['ota_0'],self.new['ota_1']]
        self.assertEqual(len(data),8192);self.assertEqual(data[4096:],b'\xff'*4096)
        self.assertEqual(struct.unpack_from('<II',data,24),(2,0x4743989a))
        self.assertEqual(active_ota(data,apps),apps[0])
        pending=bytearray(data);struct.pack_into('<I',pending,24,1)
        with self.assertRaisesRegex(ValueError,'pending'):active_ota(pending,apps)
