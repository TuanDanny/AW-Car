"""Audit/hash, scan then program the identified Tang. Default SRAM, never OTP/keys.

Operator must confirm VM disconnected before invoking --vm-off. Runtime acceptance
needs Motion SPI after programming; valid configuration is not byte readback proof.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT=Path(__file__).resolve().parents[1]
PROGRAMMER=Path("C:/Gowin/Gowin_V1.9.11.03_Education_x64/Programmer/bin/programmer_cli.exe")
FS=ROOT/"build/fpga/gowin/simplev1_nano9k/impl/pnr/simplev1_nano9k.fs"

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vm-off",action="store_true",required=True)
    parser.add_argument("--location",type=int,required=True)
    parser.add_argument("--mode",choices=["sram","flash"],default="sram")
    args=parser.parse_args()
    text=FS.read_text()
    for marker in ("//CRCCheck: ON","//SecurityBit: ON","//Part Number: GW1NR-LV9QN88PC6/I5"):
        if marker not in text: raise SystemExit("Bitstream audit failed: "+marker)
    digest=hashlib.sha256(FS.read_bytes()).hexdigest()
    expected=int(re.search(r'//UserCode: (0x[0-9a-fA-F]+)',text)[1],16)
    base=[str(PROGRAMMER),"--cable-index","4","--location",str(args.location)]
    directory=ROOT/"build/bringup";directory.mkdir(parents=True,exist_ok=True)
    scan=subprocess.run(base+["--scan"],capture_output=True,text=True,timeout=30)
    (directory/"jtag-scan.log").write_text(scan.stdout+scan.stderr,encoding="utf-8")
    if scan.returncode or "0x1100481B" not in scan.stdout or "1 device(s) found" not in scan.stdout or re.search(r'\b(error|failed)\b',scan.stdout,re.I):
        raise SystemExit("JTAG scan did not confirm one GW1NR-9C; no write performed")
    if args.mode=="flash":
        acceptance=directory/"spi-acceptance.json"
        if not acceptance.exists(): raise SystemExit("Flash requires successful SRAM/SPI acceptance first")
        evidence=json.loads(acceptance.read_text())
        if not evidence.get("pass") or evidence.get("fpga_sha256")!=digest:
            raise SystemExit("SRAM/SPI evidence does not match this bitstream")
    command=base+["--device","GW1NR-9C","--chain_index","0","--chain_size","1","--frequency","2.5MHz", "--operation_index","2" if args.mode=="sram" else "5","--fsFile",str(FS)]
    run=subprocess.run(command,capture_output=True,text=True,timeout=120)
    (directory/f"fpga-{args.mode}.log").write_text(run.stdout+run.stderr,encoding="utf-8")
    if run.returncode or re.search(r'\b(error|failed|failure)\b',run.stdout+run.stderr,re.I) or "Finished." not in run.stdout:
        raise SystemExit("Programmer did not report successful programming; see complete log")
    reloaded=False
    if args.mode=="flash":
        # Prove that the running configuration comes back from embedded Flash,
        # rather than merely reading UserCode from the previous SRAM image.
        reload=subprocess.run(base+["--device","GW1NR-9C","--operation_index","1"],capture_output=True,text=True,timeout=30)
        (directory/"fpga-flash-reload.log").write_text(reload.stdout+reload.stderr,encoding="utf-8")
        if reload.returncode or re.search(r'\b(error|failed|failure)\b',reload.stdout+reload.stderr,re.I) or "Finished." not in reload.stdout:
            raise SystemExit("Embedded Flash reload failed; do not claim persistence")
        reloaded=True
    codes=subprocess.run(base+["--device","GW1NR-9C","--operation_index","0"],capture_output=True,text=True,timeout=30)
    (directory/"fpga-codes.log").write_text(codes.stdout+codes.stderr,encoding="utf-8")
    all_text=run.stdout+run.stderr+codes.stdout+codes.stderr
    status_match=re.findall(r'Status Code is:\s*(0x[0-9a-fA-F]+)',all_text)
    user_match=re.findall(r'User Code is:\s*(0x[0-9a-fA-F]+)',all_text)
    status=int(status_match[-1],16) if status_match else 0
    user=int(user_match[-1],16) if user_match else None
    passed=(run.returncode==codes.returncode==0 and not re.search(r'\b(error|failed|failure)\b',all_text,re.I)
            and "Finished." in run.stdout and "Finished." in codes.stdout
            and user==expected and status&0xf00f==0xf000)
    report={"at_utc":datetime.now(timezone.utc).isoformat(),"mode":args.mode,"sha256":digest,
            "usercode":f"0x{expected:08X}","status":f"0x{status:08X}","pass":passed,
            "crc_on":True,"security_on":True,"byte_readback_verified":False,"spi_runtime_tested":False}
    report["reloaded_from_embedded_flash"]=reloaded
    (directory/"fpga-programming.json").write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(report,indent=2))
    if not passed: raise SystemExit("Programming not accepted; see complete captured logs")

if __name__=="__main__": main()
