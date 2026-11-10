"""One-time USB Motion migration, preserving NVS/motioncfg/factory byte-for-byte.

VM off and no motors are mandatory. Only the inactive app, bootloader, partition
table and OTA metadata change. All touched regions are backed up before writing.
Keep USB power stable: bootloader/table migration is not an atomic OTA operation.
"""
import argparse
import atexit
import binascii
import contextlib
from datetime import datetime,timezone
import json
from pathlib import Path
import struct
from flash_esp import partitions,sha,active_ota
from ota_image import inspect_image

ROOT=Path(__file__).resolve().parents[1]


def initial_ota_data():
    data=bytearray(b'\xff'*8192)
    struct.pack_into('<I',data,0,1)
    struct.pack_into('<II',data,24,2,binascii.crc32(data[:4],0xffffffff)&0xffffffff)
    return bytes(data) # seq1 selects ota_0; state2 is VALID, second sector erased.


def validate_layout(old,new):
    names={'nvs','phy_init','factory','motioncfg'}
    if set(old)!=names or any(new.get(name)!=old[name] for name in names):
        raise ValueError('Not the supported legacy layout; no migration')
    if set(new)!=names|{'otadata','ota_0','ota_1'}:
        raise ValueError('Unexpected new partition set')
    for name,offset,size,kind,sub in [('otadata',0x1a0000,0x2000,1,0),
            ('ota_0',0x200000,0x180000,0,0x10),('ota_1',0x380000,0x180000,0,0x11)]:
        p=new[name]
        if (p['offset'],p['size'],p['type'],p['subtype'],p['flags'])!=(offset,size,kind,sub,0):
            raise ValueError('Unexpected OTA layout: '+name)
    regions=sorted((p['offset'],p['offset']+p['size']) for p in new.values())
    if any(a[1]>b[0] for a,b in zip(regions,regions[1:])) or regions[-1][1]>16*1024*1024:
        raise ValueError('Overlapping/out-of-range partitions')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port',required=True)
    parser.add_argument('--vm-off',required=True,action='store_true')
    args=parser.parse_args()
    import serial.tools.list_ports
    import esptool
    import esptool.cmds
    port=next((p for p in serial.tools.list_ports.comports() if p.device.casefold()==args.port.casefold()),None)
    if not port or (port.vid,port.pid)!=(0x1a86,0x55d3): raise ValueError('Motion USB-UART identity mismatch')
    build=ROOT/'build/motion'
    manifest=json.loads((build/'manifest.json').read_text())
    image=build/'simplev1_motion.bin';inspect_image(image,'motion',manifest)
    if manifest.get('test_rollback'): raise ValueError('Cannot bootstrap a deliberately failing image')
    config=(ROOT/'esp/motion/sdkconfig').read_text().splitlines()
    if 'CONFIG_BOOTLOADER_APP_ROLLBACK_ENABLE=y' not in config: raise ValueError('Rollback bootloader required')
    boot=build/'bootloader/bootloader.bin';table=build/'partition_table/partition-table.bin'
    for path in (boot,table):
        if sha(path.read_bytes())!=manifest['images'][path.relative_to(build).as_posix()]['sha256']:
            raise ValueError('Manifest mismatch: '+path.name)
    if boot.stat().st_size>0x8000 or table.stat().st_size>0x1000: raise ValueError('Reserved region exceeded')
    private=ROOT/'build/private'/('motion-migration-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
    private.mkdir(parents=True,exist_ok=False)
    def invoke(function,*values,**keywords):
        with (private/'esptool.log').open('a',encoding='utf-8') as log:
            with contextlib.redirect_stdout(log),contextlib.redirect_stderr(log): return function(*values,**keywords)
    esp=invoke(esptool.connect_esp,port=args.port,chip='esp32s3',initial_baud=115200)
    esp=invoke(esp.run_stub);atexit.register(esp._port.close)
    invoke(esp.change_baud,460800);invoke(esptool.cmds.attach_flash,esp)
    if invoke(esptool.cmds.detect_flash_size,esp)!='16MB': raise ValueError('Expected 16MiB flash')
    def read(offset,size,name):
        data=invoke(esptool.cmds.read_flash,esp,offset,size,no_progress=True)
        (private/name).write_bytes(data);return data
    old_table=read(0x8000,0x1000,'partition-table-before.bin')
    old=partitions(old_table);new=partitions(table.read_bytes());validate_layout(old,new)
    if image.stat().st_size>new['ota_0']['size']: raise ValueError('Application exceeds OTA slot')
    preserved={}
    for name in ('nvs','phy_init','motioncfg','factory'):
        p=old[name];preserved[name]=sha(read(p['offset'],p['size'],name+'-before.bin'))
    read(0,0x8000,'bootloader-before.bin')
    read(new['ota_0']['offset'],new['ota_0']['size'],'ota0-before.bin')
    read(new['otadata']['offset'],new['otadata']['size'],'otadata-before.bin')
    metadata=private/'otadata-valid0.bin';metadata.write_bytes(initial_ota_data())
    if active_ota(metadata.read_bytes(),[new['ota_0'],new['ota_1']])!=new['ota_0']:
        raise ValueError('Initial metadata validation failed')
    # App first. Metadata is written last. Never overwrite the retained factory.
    writes=[(new['ota_0']['offset'],image),(0,boot),(0x8000,table),(new['otadata']['offset'],metadata)]
    verified={}
    for offset,path in writes:
        invoke(esptool.cmds.write_flash,esp,[(offset,str(path))],flash_freq='keep',flash_mode='keep',flash_size='keep')
        back=read(offset,path.stat().st_size,path.stem+'-readback.bin')
        if sha(back)!=sha(path.read_bytes()): raise ValueError('Readback mismatch: '+path.name)
        verified[path.name]=sha(back)
    for name,expected in preserved.items():
        p=old[name]
        if sha(read(p['offset'],p['size'],name+'-after.bin'))!=expected:
            raise ValueError('Preserved region changed: '+name)
    report={'board':'motion','build':manifest['build_id'],'pass':True,'vm_off':True,
            'readback_sha256':verified,'preserved_regions':preserved,
            'boot_slot':'ota_0','boot_state':'valid','backups_private':True}
    (private/'result.json').write_text(json.dumps(report,indent=2)+'\n')
    (ROOT/'build/bringup').mkdir(parents=True,exist_ok=True)
    (ROOT/'build/bringup/motion-migration.json').write_text(json.dumps(report,indent=2)+'\n')
    invoke(esp.hard_reset);print(json.dumps(report,indent=2))


if __name__=='__main__': main()
