import hashlib
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'utils'))
from ota_image import inspect_image


class OtaImage(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.path=Path(self.temp.name)/'app.bin'
        self.data=bytearray(512);self.data[0]=0xe9;self.data[23]=1
        struct.pack_into('<H',self.data,12,9);struct.pack_into('<I',self.data,32,0xabcd5432)
        self.data[80:92]=b'aw_car_brain';self.path.write_bytes(self.data)
        self.manifest={'board':'brain','build_id':'test','images':{'aw_car_brain.bin':{'bytes':512,'sha256':hashlib.sha256(self.data).hexdigest()}}}
    def tearDown(self): self.temp.cleanup()
    def test_correct_role_and_hash(self):
        self.assertEqual(inspect_image(self.path,'brain',self.manifest)['project'],'aw_car_brain')
    def test_corruption_or_stale_manifest(self):
        self.data[-1]^=1;self.path.write_bytes(self.data)
        with self.assertRaisesRegex(ValueError,'SHA256'): inspect_image(self.path,'brain',self.manifest)
    def test_wrong_role_and_wrong_chip(self):
        with self.assertRaisesRegex(ValueError,'another board'): inspect_image(self.path,'motion',self.manifest)
        self.data[12]=0;self.path.write_bytes(self.data)
        with self.assertRaisesRegex(ValueError,'ESP32-S3'): inspect_image(self.path,'brain',self.manifest)
    def test_merged_bootloader_or_wrong_project(self):
        self.data[80:112]=b'bootloader'.ljust(32,b'\0');self.path.write_bytes(self.data)
        with self.assertRaisesRegex(ValueError,'project'): inspect_image(self.path,'brain',self.manifest)
