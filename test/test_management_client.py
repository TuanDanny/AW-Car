"""Exercise the real laptop client against TLS, auth rejection and key mismatch."""
import hashlib
import http.server
import json
from pathlib import Path
import ssl
import subprocess
import sys
import tempfile
import threading
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'utils'))
from awcarctl import Client

SDK_PYTHON=Path('C:/Espressif/python_env/idf6.1_py3.13_env/Scripts/python.exe')


@unittest.skipUnless(SDK_PYTHON.exists(),'SDK Python required only for temporary test certificates')
class ManagementClient(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory=tempfile.TemporaryDirectory()
        cls.key=Path(cls.directory.name)/'motion.key'
        cls.key.write_text('a'*64)
        subprocess.run([str(SDK_PYTHON),str(ROOT/'utils/management_keys.py'),
                        '--generate-certificate',str(cls.key),'motion'],check=True)
        cls.other=Path(cls.directory.name)/'other.key';cls.other.write_text('a'*64)
        subprocess.run([str(SDK_PYTHON),str(ROOT/'utils/management_keys.py'),
                        '--generate-certificate',str(cls.other),'motion'],check=True)
        cls.key_id=hashlib.sha256(cls.key.read_bytes()+cls.key.with_suffix('.crt').read_bytes()).hexdigest()[:12]
        class Handler(http.server.BaseHTTPRequestHandler):
            protocol_version='HTTP/1.1'
            def log_message(self,*args): pass
            def do_GET(self):
                if self.headers.get('Authorization')!='Bearer '+'a'*64:
                    self.send_response(401);self.send_header('Content-Length','0');self.end_headers();return
                content=json.dumps({'role':'motion','key_id':cls.key_id,'ota_enabled':False}).encode()
                self.send_response(200);self.send_header('Content-Length',str(len(content)));self.end_headers();self.wfile.write(content)
        cls.server=http.server.ThreadingHTTPServer(('127.0.0.1',0),Handler)
        cls.server.daemon_threads=True
        context=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(str(cls.key.with_suffix('.crt')),str(cls.key.with_suffix('.tls.key')))
        cls.server.socket=context.wrap_socket(cls.server.socket,server_side=True)
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True);cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown();cls.server.server_close();cls.thread.join();cls.directory.cleanup()

    def client(self,role='motion'):
        return Client(role,'127.0.0.1',self.key,self.server.server_port)

    def test_valid_and_reused_tls_connection(self):
        client=self.client()
        try:
            self.assertFalse(client.get('/info')['ota_enabled'])
            socket=client.connection.sock
            self.assertEqual(client.get('/logs?after=0')['role'],'motion')
            self.assertIs(socket,client.connection.sock)
        finally: client.close()

    def test_invalid_token(self):
        client=self.client();client.key='b'*64
        try:
            with self.assertRaisesRegex(ValueError,'HTTP 401'): client.get('/info')
        finally: client.close()

    def test_wrong_role(self):
        client=self.client('brain')
        try:
            with self.assertRaisesRegex(ValueError,'identity mismatch'): client.get('/info')
        finally: client.close()

    def test_wrong_certificate_is_rejected(self):
        client=Client('motion','127.0.0.1',self.other,self.server.server_port)
        try:
            with self.assertRaises(ssl.SSLCertVerificationError): client.get('/info')
        finally: client.close()

    def test_no_move_route(self):
        client=self.client()
        try:
            with self.assertRaisesRegex(ValueError,'read-only'): client.get('/ws')
        finally: client.close()
