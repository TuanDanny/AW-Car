"""Explicit bench-only negative OTA checks. VM/motors must be disconnected.

Writes only a non-running slot; no accepted firmware update is sent here.
Optional --reset-port resets the selected chip while an upload is incomplete.
Raw results remain in build/private unless an output path is selected.
"""
import argparse
import hashlib
import json
from pathlib import Path
import time
from awcarctl import Client
from ota_image import BINARIES, inspect_image

ROOT=Path(__file__).resolve().parents[1]


def reset_device(role,port):
    import serial
    import serial.tools.list_ports
    from esptool.reset import HardReset
    wanted=(0x303a,0x1001) if role=='brain' else (0x1a86,0x55d3)
    actual=next((p for p in serial.tools.list_ports.comports() if p.device.casefold()==port.casefold()),None)
    if not actual or (actual.vid,actual.pid)!=wanted:
        raise ValueError('Reset port identity does not match the chosen board')
    connection=serial.Serial(port=None,baudrate=115200,timeout=.2)
    connection.dtr=False;connection.rts=False;connection.port=port;connection.open()
    try: HardReset(connection,uses_usb=role=='brain')()
    finally:
        try: connection.close()
        except OSError: pass


def wait_state(role,address,before,reset=False):
    start=time.monotonic();client=Client(role,address)
    try:
        while time.monotonic()-start<45:
            try:
                value=client.get('/info')
                if value['ota_state']=='valid' and not value['updating']:
                    unchanged=value['elf_sha256']==before['elf_sha256']
                    boot_ok=value['boot']!=before['boot'] if reset else value['boot']==before['boot']
                    return {'pass':unchanged and boot_ok,'same_elf':unchanged,
                            'boot_check':boot_ok,'recovered_s':time.monotonic()-start}
            except (OSError,ValueError): client.close()
            time.sleep(.5)
    finally: client.close()
    return {'pass':False,'error':'receiver did not recover within 45 seconds'}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('board',choices=['brain','motion'])
    parser.add_argument('--ip')
    parser.add_argument('--vm-off',required=True,action='store_true')
    parser.add_argument('--image',type=Path)
    parser.add_argument('--manifest',type=Path)
    parser.add_argument('--reset-port')
    parser.add_argument('--output',type=Path)
    parser.add_argument('--only',choices=['wrong_project','wrong_sha256','interrupted','reset_incomplete'])
    args=parser.parse_args()
    if args.only=='reset_incomplete' and not args.reset_port: parser.error('--reset-port is required for that case')
    build=ROOT/'build'/args.board
    image=args.image or build/BINARIES[args.board]
    manifest=json.loads((args.manifest or build/'manifest.json').read_text())
    inspect_image(image,args.board,manifest)
    if manifest.get('test_rollback'): raise ValueError('Use a known-good image for the negative transfer tests')
    data=image.read_bytes();digest=hashlib.sha256(data).hexdigest()
    client=Client(args.board,args.ip);before=client.get('/info');client.close()
    if not before.get('ota_enabled') or before.get('ota_state')!='valid': raise ValueError('OTA bootstrap/health required')
    cases=[]
    selected=(args.only,) if args.only else ('wrong_project','wrong_sha256','interrupted')+ (('reset_incomplete',) if args.reset_port else ())
    for case in selected:
        client=Client(args.board,args.ip)
        body=data
        if case=='wrong_project':
            prefix=bytearray(data[:288]);prefix[80:112]=b'NOT_AW_CAR'.ljust(32,b'\0');body=bytes(prefix)
        elif case in ('interrupted','reset_incomplete'): body=data[:1024]
        expected='0'*64 if case=='wrong_sha256' else digest
        headers={'Authorization':'Bearer '+client.key,'Content-Length':str(len(data)),
                 'Content-Type':'application/octet-stream','X-AW-SHA256':expected}
        client.connection.timeout=30
        result={'case':case}
        try:
            client.connection.request('POST','/update',body=body,headers=headers)
            if case in ('interrupted','reset_incomplete'):
                time.sleep(1)
                if case=='reset_incomplete': reset_device(args.board,args.reset_port)
            else:
                response=client.connection.getresponse();result['http_status']=response.status;response.read(2048)
        finally: client.close()
        time.sleep(1)
        result.update(wait_state(args.board,args.ip,before,reset=case=='reset_incomplete'))
        if case in ('wrong_project','wrong_sha256'): result['pass']=result['pass'] and result.get('http_status')==400
        cases.append(result)
        if not result['pass']: break
        client=Client(args.board,args.ip);before=client.get('/info');client.close()
    report={'board':args.board,'vm_off_confirmed':True,'cases':cases,'pass':all(c['pass'] for c in cases)}
    out=args.output or ROOT/'build/private'/('ota-negative-'+args.board+'.json')
    out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2));return 0 if report['pass'] else 1


if __name__=='__main__':
    raise SystemExit(main())
