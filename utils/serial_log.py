"""Capture console from selected ports without toggling DTR/RTS or sending commands.

Raw logs can contain recognized speech/network identifiers: build/private only.
"""
from __future__ import annotations
import argparse
from datetime import datetime,timezone
import json
from pathlib import Path
import re
import time

ROOT=Path(__file__).resolve().parents[1]
def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ports",nargs="+",required=True)
    parser.add_argument("--seconds",type=float,default=60)
    parser.add_argument("--output",type=Path)
    args=parser.parse_args()
    import serial
    out=args.output or ROOT/"build/private"/("serial-"+datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
    out.mkdir(parents=True,exist_ok=True)
    ports=[];buffers={};files={};stats={}
    try:
        for name in args.ports:
            port=serial.Serial(port=None,baudrate=115200,timeout=0)
            port.dtr=False;port.rts=False;port.port=name;port.open()
            ports.append(port);buffers[name]=b"";files[name]=(out/(name+".txt")).open("wb")
            stats[name]={"bytes":0,"lines":0,"panic":0,"watchdog":0,"backtrace":0,"build":[],"last_motion":None}
        deadline=time.monotonic()+args.seconds
        while time.monotonic()<deadline:
            for port in ports:
                data=port.read(min(max(port.in_waiting,1),8192))
                if not data: continue
                files[port.port].write(data);files[port.port].flush();s=stats[port.port];s["bytes"]+=len(data)
                lines=(buffers[port.port]+data).split(b"\n");buffers[port.port]=lines.pop()
                for line in lines:
                    text=line.decode("utf-8",errors="replace");s["lines"]+=1
                    if "Guru Meditation" in text or "panic'ed" in text: s["panic"]+=1
                    if "Task watchdog got triggered" in text: s["watchdog"]+=1
                    if "Backtrace:" in text: s["backtrace"]+=1
                    match=re.search(r'build=(simplev1-[a-f0-9]+)',text)
                    if match and match[1] not in s["build"]: s["build"].append(match[1])
                    if "simple_motion:" in text and "mode=" in text:
                        text=re.sub(r'\x1b\[[0-9;]*m','',text).strip()
                        s["last_motion"]=text
                        print(f"{port.port} {text}",flush=True)
            time.sleep(.01)
    finally:
        for port in ports: port.close()
        for handle in files.values(): handle.close()
    report={"duration_s":args.seconds,"ports":stats,"raw_logs_private":True,"writes_or_reset":False}
    (out/"summary.json").write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(report,indent=2))

if __name__=="__main__": main()
