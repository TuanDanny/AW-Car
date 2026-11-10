"""Flash the selected ESP app/assets, preserving partition table, NVS and otadata.

Requires an existing compatible board layout. Does not erase flash or write keys.
All private reads/logs stay below build/private. Explicit --vm-off is physical setup.
"""
from __future__ import annotations
import argparse
import atexit
import binascii
import contextlib
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]

def sha(data): return hashlib.sha256(data).hexdigest()
def partitions(data):
    result={}
    for i in range(0,min(len(data),0xc00),32):
        if data[i:i+2]!=b"\xaa\x50": break
        _,kind,sub,offset,size,name,flags=struct.unpack("<HBBII16sI",data[i:i+32])
        result[name.split(b"\0",1)[0].decode()]={"type":kind,"subtype":sub,"offset":offset,"size":size,"flags":flags}
    if not result: raise ValueError("No ESP partition entries found")
    return result

def active_ota(data,apps):
    valid=[]
    for sector in (0,4096):
        seq=struct.unpack_from("<I",data,sector)[0]
        state,crc=struct.unpack_from("<II",data,sector+24)
        calculated=binascii.crc32(data[sector:sector+4],0xffffffff)&0xffffffff
        if seq!=0xffffffff and state not in (3,4) and crc==calculated:
            if state==1: raise ValueError("OTA pending verification; boot/validate it before changing firmware")
            valid.append(seq)
    return apps[(max(valid)-1)%len(apps)] if valid else apps[0]

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("board",choices=["motion","brain"])
    parser.add_argument("--port",required=True)
    parser.add_argument("--vm-off",action="store_true",required=True)
    args=parser.parse_args()
    import serial.tools.list_ports
    expected=(0x303a,0x1001) if args.board=="brain" else (0x1a86,0x55d3)
    port=next((p for p in serial.tools.list_ports.comports() if p.device.casefold()==args.port.casefold()),None)
    if not port or (port.vid,port.pid)!=expected: raise SystemExit("Port identity does not match selected board; no write")
    build=ROOT/"build"/args.board
    manifest=json.loads((build/"manifest.json").read_text())
    private=ROOT/"build/private"/(args.board+"-"+datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
    private.mkdir(parents=True,exist_ok=True)
    import esptool
    import esptool.cmds
    def invoke(function,*values,**keywords):
        with (private/"esptool.log").open("a",encoding="utf-8") as log:
            with contextlib.redirect_stdout(log),contextlib.redirect_stderr(log):
                return function(*values,**keywords)
    # Keep one serial/stub session. Reopening CLI between reads can toggle USB-UART
    # auto-reset lines and lose the stub; it also permits runtime NVS writes.
    esp=invoke(esptool.connect_esp,port=args.port,chip="esp32s3",initial_baud=115200)
    esp=invoke(esp.run_stub)
    atexit.register(esp._port.close)
    invoke(esp.change_baud,460800)
    invoke(esptool.cmds.attach_flash,esp)
    if invoke(esptool.cmds.detect_flash_size,esp)!="16MB": raise ValueError("Unexpected flash size")
    def read(offset,size,name):
        data=invoke(esptool.cmds.read_flash,esp,offset,size,no_progress=True)
        (private/name).write_bytes(data)
        return data
    table=read(0x8000,0x1000,"partitions-before.bin")
    actual=partitions(table);wanted=partitions((build/"partition_table/partition-table.bin").read_bytes())
    for name,entry in wanted.items():
        if name not in actual or actual[name]!=entry: raise ValueError("Partition mismatch: "+name+"; no migration/erase performed")
    nvs=actual["nvs"]
    nvs_before=read(nvs["offset"],nvs["size"],"nvs-before.bin")
    preserved={"nvs":sha(nvs_before),"partition_table":sha(table)}
    if args.board=="brain":
        ota=actual["otadata"]
        ota_before=read(ota["offset"],ota["size"],"otadata-before.bin")
        preserved["otadata"]=sha(ota_before)
        apps=sorted([p for p in actual.values() if p["type"]==0 and 0x10<=p["subtype"]<=0x1f],key=lambda p:p["subtype"])
        app=active_ota(ota_before,apps);app_name="aw_car_brain.bin"
    else:
        app=actual["factory"];app_name="simplev1_motion.bin"
        if "motioncfg" in actual:
            cfg=actual["motioncfg"]
            preserved["motioncfg"]=sha(read(cfg["offset"],cfg["size"],"motioncfg-before.bin"))
    images=[(app["offset"],build/app_name)]
    if args.board=="brain": images.append((actual["assets"]["offset"],build/"generated_assets.bin"))
    if (build/app_name).stat().st_size>app["size"]: raise ValueError("App exceeds existing slot")
    for offset,path in images:
        if manifest["images"][path.name]["sha256"]!=sha(path.read_bytes()): raise ValueError("Image/manifest hash mismatch")
    # One current-app snapshot per selected release, not a repeated16MiB full backup.
    read(app["offset"],app["size"],"app-before.bin")
    invoke(esptool.cmds.write_flash,esp,[(offset,str(path)) for offset,path in images],
           flash_freq="keep",flash_mode="keep",flash_size="keep")
    verified={}
    for offset,path in images:
        back=read(offset,path.stat().st_size,path.stem+"-readback.bin")
        verified[path.name]=sha(back)
        if verified[path.name]!=sha(path.read_bytes()): raise ValueError("Readback mismatch: "+path.name)
    if sha(read(nvs["offset"],nvs["size"],"nvs-after.bin"))!=preserved["nvs"]: raise ValueError("NVS changed during programming")
    if sha(read(0x8000,0x1000,"partitions-after.bin"))!=preserved["partition_table"]: raise ValueError("Partition table changed")
    for name in ("otadata","motioncfg"):
        if name in preserved:
            p=actual[name]
            if sha(read(p["offset"],p["size"],name+"-after.bin"))!=preserved[name]: raise ValueError(name+" changed")
    invoke(esp.hard_reset)
    report={"at_utc":datetime.now(timezone.utc).isoformat(),"board":args.board,"port":args.port,
            "build_id":manifest["build_id"],"app_offset":hex(app["offset"]),"readback_sha256":verified,
            "nvs_preserved":True,"partition_table_preserved":True,"otadata_preserved":"otadata" in preserved,
            "legacy_motioncfg_preserved":"motioncfg" in preserved,"pass":True,"vm_off_confirmed":True}
    (ROOT/"build/bringup").mkdir(parents=True,exist_ok=True)
    (ROOT/"build/bringup"/(args.board+"-flash.json")).write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(report,indent=2))

if __name__=="__main__": main()
