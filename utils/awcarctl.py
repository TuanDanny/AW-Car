"""Find AW-Car boards and poll bounded diagnostic samples over the router LAN.

No driving commands. Upload requires the device's USB OTA bootstrap first.
"""
import argparse
import hashlib
import http.client
import json
from pathlib import Path
import re
import time
import ssl
from management_keys import key_file, read_key
from ota_image import BINARIES, inspect_image

ROOT = Path(__file__).resolve().parents[1]


class Client:
    def __init__(self, role, address=None, key_path=None, port=3232):
        if role not in ('brain', 'motion'):
            raise ValueError('unknown board role')
        self.role = role
        self.address = address or ('awcar-' + role + '.local')
        if not re.fullmatch(r'[a-zA-Z0-9.-]+', self.address):
            raise ValueError('Use a hostname or IPv4 address')
        private = Path(key_path) if key_path else key_file(ROOT, role)
        self.key = read_key(private)
        certificate = private.with_suffix('.crt')
        self.key_id = hashlib.sha256(self.key.encode() + certificate.read_bytes()).hexdigest()[:12]
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        context.check_hostname = False  # STA IP changes; trust only this exact board certificate.
        context.load_verify_locations(cafile=str(certificate))
        self.certificate_der = ssl.PEM_cert_to_DER_cert(certificate.read_text(encoding='ascii'))
        self.connection = http.client.HTTPSConnection(self.address, port, timeout=4, context=context)

    def close(self):
        self.connection.close()

    def _json(self, path):
        if self.connection.sock is None:
            self.connection.connect()
            if self.connection.sock.getpeercert(binary_form=True) != self.certificate_der:
                self.close()
                raise ValueError('Server certificate does not match the selected board')
        self.connection.request('GET', path, headers={'Authorization': 'Bearer ' + self.key})
        response = self.connection.getresponse()
        raw = response.read(65537)
        if response.status != 200:
            self.close()
            raise ValueError('Management request rejected: HTTP ' + str(response.status))
        if len(raw) > 65536:
            self.close()
            raise ValueError('Management reply exceeds size limit')
        return json.loads(raw)

    def get(self, path):
        if path not in ('/info',) and not re.fullmatch(r'/logs\?after=[0-9]{1,20}', path):
            raise ValueError('Only read-only info/log routes are supported')
        reply = self._json(path)
        if reply.get('role') != self.role or reply.get('key_id') != self.key_id:
            raise ValueError('Board/key identity mismatch; use the key used for its USB build')
        return reply

    def upload(self,path,manifest,expect_rollback=False,timeout=120):
        candidate=inspect_image(path,self.role,manifest)
        if bool(manifest.get('test_rollback'))!=expect_rollback:
            raise ValueError('A rollback test image requires --expect-rollback; a normal update must not use that flag')
        before=self.get('/info')
        if not before.get('ota_enabled') or before.get('ota_state')!='valid':
            raise ValueError('USB OTA bootstrap or local health confirmation is required first')
        if manifest.get('management_key_id')!=self.key_id:
            raise ValueError('The new firmware uses another management key; do not rekey through this OTA path')
        if self.connection.sock: self.connection.sock.settimeout(30)
        acknowledged=False
        try:
            with path.open('rb') as source:
                self.connection.request('POST','/update',body=source,headers={
                    'Authorization':'Bearer '+self.key,'Content-Type':'application/octet-stream',
                    'Content-Length':str(candidate['bytes']),'X-AW-SHA256':candidate['sha256']})
                response=self.connection.getresponse();body=response.read(2048)
                if response.status!=202:
                    raise ValueError('OTA rejected HTTP '+str(response.status)+': '+body.decode(errors='replace'))
                acknowledged=True
        except (OSError,http.client.HTTPException):
            # The reply can be lost during reboot. Verify the running image;
            # never automatically send the firmware a second time.
            pass
        finally: self.close()
        self.connection.timeout=4
        deadline=time.monotonic()+timeout;saw_trial=False
        while time.monotonic()<deadline:
            time.sleep(1)
            try: current=self.get('/info')
            except (OSError,ValueError,http.client.HTTPException): self.close();continue
            new_boot=current.get('boot')!=before.get('boot')
            if new_boot and current.get('elf_sha256')==candidate['elf_sha256']: saw_trial=True
            if expect_rollback:
                good=saw_trial and new_boot and current.get('elf_sha256')==before.get('elf_sha256') and current.get('ota_state')=='valid'
            else:
                good=new_boot and current.get('build')==candidate['build'] and current.get('elf_sha256')==candidate['elf_sha256'] and current.get('ota_state')=='valid'
            if good:
                return {'role':self.role,'pass':True,'rollback_test':expect_rollback,
                        'upload_acknowledged':acknowledged,'trial_observed':saw_trial,
                        'candidate':candidate,'running_build':current['build'],'ota_state':current['ota_state']}
        raise ValueError('OTA outcome not confirmed; inspect board/logs before retrying')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    discover = commands.add_parser('discover', help='Resolve the two .local hostnames or use fallback IPs')
    discover.add_argument('--brain-ip')
    discover.add_argument('--motion-ip')
    for command in ('info', 'logs', 'upload'):
        sub = commands.add_parser(command)
        sub.add_argument('board', choices=['brain', 'motion'])
        sub.add_argument('--ip', help='Fallback when .local discovery is unavailable')
        sub.add_argument('--key-file', type=Path)
        if command == 'logs':
            sub.add_argument('--seconds', type=float, default=60)
            sub.add_argument('--interval', type=float, default=1)
        if command == 'upload':
            sub.add_argument('--file',type=Path)
            sub.add_argument('--manifest',type=Path)
            sub.add_argument('--expect-rollback',action='store_true',help='Only for a deliberately failing trial firmware')
    args = parser.parse_args()
    try:
        if args.command == 'discover':
            result = []
            for role in ('brain', 'motion'):
                try:
                    client = Client(role, getattr(args, role + '_ip'))
                    result.append({'role': role, 'address': client.address, 'info': client.get('/info')})
                    client.close()
                except (OSError, ValueError) as error:
                    result.append({'role': role, 'online': False, 'error': str(error)})
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0 if all('info' in item for item in result) else 1
        client = Client(args.board, args.ip, args.key_file)
        if args.command == 'info':
            print(json.dumps(client.get('/info'), ensure_ascii=False, indent=2))
            return 0
        if args.command == 'upload':
            directory=ROOT/'build'/args.board
            image=args.file or directory/BINARIES[args.board]
            manifest=json.loads((args.manifest or directory/'manifest.json').read_text())
            result=client.upload(image,manifest,args.expect_rollback)
            client.close();print(json.dumps(result,indent=2));return 0
        if args.interval < .2 or args.interval > 10 or args.seconds < 0:
            parser.error('interval must be 0.2..10 seconds; seconds >= 0 (0 means until Ctrl+C)')
        deadline = time.monotonic() + args.seconds if args.seconds else float('inf')
        cursor = 0
        boot = None
        while time.monotonic() < deadline:
            try:
                batch = client.get('/logs?after=' + str(cursor))
                if boot is not None and boot != batch.get('boot'):
                    cursor = 0
                    boot = batch.get('boot')
                    continue
                boot = batch.get('boot')
                if batch.get('dropped'):
                    print('Older diagnostic samples overwritten:', batch['dropped'], flush=True)
                for item in batch.get('samples', []):
                    print(f"{args.board} {item['ms']}ms #{item['seq']} {item['text']}", flush=True)
                cursor = int(batch['next'])
            except (OSError, ValueError) as error:
                print('Log connection unavailable:', str(error), flush=True)
                client.close()
            time.sleep(args.interval)
        return 0
    except KeyboardInterrupt:
        return 0
    except (OSError, ValueError) as error:
        parser.exit(1, str(error) + '\n')


if __name__ == '__main__':
    raise SystemExit(main())
