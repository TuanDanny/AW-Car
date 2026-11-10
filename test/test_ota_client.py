"""Uploader outcome checks, including a rebuild changing its file during upload."""
import hashlib
import http.client
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest.mock import Mock,patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'utils'))
from awcarctl import Client


class UploadClient(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.path=Path(self.temp.name)/'app.bin'
        self.data=bytearray(512);self.data[0]=0xe9;self.data[23]=1
        struct.pack_into('<H',self.data,12,9);struct.pack_into('<I',self.data,32,0xabcd5432)
        self.data[80:112]=b'simplev1_motion'.ljust(32,b'\0');self.data[176:208]=b'a'*32
        self.path.write_bytes(self.data)
        self.manifest={'board':'motion','build_id':'new','management_key_id':'key',
                       'images':{'simplev1_motion.bin':{'bytes':512,'sha256':hashlib.sha256(self.data).hexdigest()}}}
        self.before={'ota_enabled':True,'ota_state':'valid','boot':'old','build':'old','elf_sha256':'old'}
        self.after={'boot':'new','build':'new','elf_sha256':bytes(self.data[176:208]).hex(),'ota_state':'valid'}
        self.client=Client.__new__(Client);self.client.role='motion';self.client.key_id='key';self.client.key='dummy'
        self.client.connection=Mock();response=Mock();response.status=202;response.read.return_value=b'{}'
        self.client.connection.getresponse.return_value=response
    def tearDown(self): self.temp.cleanup()
    @patch('awcarctl.time.sleep')
    def test_upload_owns_original_bytes_if_build_overwrites_file(self,_):
        self.client.get=Mock(side_effect=[self.before,self.after])
        def write_again(*args,**kwargs):
            self.path.write_bytes(b'rebuilt')
            self.assertEqual(kwargs['body'],self.data)
        self.client.connection.request.side_effect=write_again
        self.assertTrue(self.client.upload(self.path,self.manifest)['pass'])
        self.assertEqual(self.client.connection.request.call_count,1)
    @patch('awcarctl.time.sleep')
    def test_lost_reply_verifies_boot_without_resending(self,_):
        self.client.get=Mock(side_effect=[self.before,self.after])
        self.client.connection.getresponse.side_effect=http.client.RemoteDisconnected()
        result=self.client.upload(self.path,self.manifest)
        self.assertTrue(result['pass']);self.assertFalse(result['upload_acknowledged'])
        self.assertEqual(self.client.connection.request.call_count,1)
    @patch('awcarctl.time.sleep')
    @patch('awcarctl.time.monotonic',side_effect=[0,0,2])
    def test_ack_or_build_alone_does_not_confirm_wrong_elf(self,clock,sleep):
        wrong=dict(self.after,elf_sha256='wrong');self.client.get=Mock(side_effect=[self.before,wrong])
        with self.assertRaisesRegex(ValueError,'not confirmed'):self.client.upload(self.path,self.manifest,timeout=1)
        self.assertEqual(self.client.connection.request.call_count,1)
    def test_key_change_or_unconfirmed_boot_refused_before_post(self):
        self.client.get=Mock(return_value=dict(self.before,ota_state='pending'))
        with self.assertRaisesRegex(ValueError,'health'):self.client.upload(self.path,self.manifest)
        self.client.get.return_value=self.before;self.manifest['management_key_id']='other'
        with self.assertRaisesRegex(ValueError,'another management key'):self.client.upload(self.path,self.manifest)
        self.client.connection.request.assert_not_called()
