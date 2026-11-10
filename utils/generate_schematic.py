"""Generate the simplev1 A3 bench connection reference, never the old carrier PCB.

No guessed footprint/header pad numbers. Existing editable output is protected.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import uuid

ROOT = Path(__file__).resolve().parents[1]
NS = uuid.UUID("ff2c4606-b61b-4854-a0db-e2d555420d11")
def uid(text): return str(uuid.uuid5(NS, text))
def q(text): return json.dumps(str(text), ensure_ascii=False)
def effects(size=1): return f"(effects (font (size {size} {size})))"

# Pin: logical/module ID, display name, electrical type, side, net.
PARTS = [
    ("U1", "ESP32-S3 BRAIN", 65, 105, [
        ("5V", "USB 5V", "power_in", "T", "5V_BRAIN"), ("3V3", "3V3", "power_out", "T", "3V3_BRAIN"),
        ("GPIO18", "RX18", "input", "L", "BM_MOTION_TX"), ("GPIO6", "MIC SD6", "input", "L", "MIC_SD"),
        ("GPIO17", "TX17", "output", "R", "BM_BRAIN_TX"), ("GPIO4", "MIC WS4", "output", "R", "MIC_WS"),
        ("GPIO5", "MIC BCLK5", "output", "R", "MIC_BCLK"), ("GPIO7", "AMP DIN7", "output", "R", "AMP_DIN"),
        ("GPIO15", "AMP BCLK15", "output", "R", "AMP_BCLK"), ("GPIO16", "AMP LRC16", "output", "R", "AMP_LRC"),
        ("GPIO41", "OLED SDA41", "bidirectional", "R", "OLED_SDA"), ("GPIO42", "OLED SCL42", "bidirectional", "R", "OLED_SCL"),
        ("GND", "GND", "power_in", "B", "GND")]),
    ("U2", "ESP32-S3 MOTION", 165, 105, [
        ("5V", "USB 5V", "power_in", "T", "5V_MOTION"),
        ("GPIO14", "RX14", "input", "L", "BM_BRAIN_TX"), ("GPIO16", "MISO16", "input", "L", "SPI_MISO"),
        ("GPIO13", "TX13", "output", "R", "BM_MOTION_TX"), ("GPIO15", "MOSI15", "output", "R", "SPI_MOSI"),
        ("GPIO4", "SCLK4", "output", "R", "SPI_SCLK"), ("GPIO5", "CS5", "output", "R", "SPI_CS_N"),
        ("GPIO10", "STBY10", "output", "R", "STBY_COMMAND"), ("GND", "GND", "power_in", "B", "GND")]),
    ("U3", "TANG NANO 9K", 265, 105, [
        ("5V", "USB 5V", "power_in", "T", "5V_TANG"), ("3V3", "3V3", "power_out", "T", "3V3_TANG"),
        ("P25", "MOSI P25", "input", "L", "SPI_MOSI"), ("P29", "SCLK P29", "input", "L", "SPI_SCLK"),
        ("P30", "CS_N P30", "input", "L", "SPI_CS_N"), ("P28", "ENC_R P28", "input", "L", "ENC_R_3V3"),
        ("P27", "ENC_L P27", "input", "L", None),
        ("P26", "MISO P26", "output", "R", "SPI_MISO"), ("P35", "LEFT IN1 P35", "output", "R", "L_IN1"),
        ("P40", "LEFT IN2 P40", "output", "R", "L_IN2"), ("P41", "RIGHT IN1 P41", "output", "R", "R_IN1"),
        ("P42", "RIGHT IN2 P42", "output", "R", "R_IN2"), ("GND", "GND", "power_in", "B", "GND")]),
    ("U4", "DRV8833 LEFT", 365, 95, [
        ("VM", "VM", "power_in", "T", "VM_5V_BENCH"), ("STBY", "STBY", "input", "L", "STBY_L"),
        ("AIN1", "AIN1", "input", "L", "L_IN1"), ("BIN1", "BIN1", "input", "L", "L_IN1"),
        ("AIN2", "AIN2", "input", "L", "L_IN2"), ("BIN2", "BIN2", "input", "L", "L_IN2"),
        ("AO1", "AO1", "output", "R", "L_AO1"), ("AO2", "AO2", "output", "R", "L_AO2"),
        ("BO1", "BO1", "output", "R", "L_BO1"), ("BO2", "BO2", "output", "R", "L_BO2"),
        ("GND", "GND", "power_in", "B", "GND")]),
    ("U5", "DRV8833 RIGHT", 365, 166, [
        ("VM", "VM", "power_in", "T", "VM_5V_BENCH"), ("STBY", "STBY", "input", "L", "STBY_R"),
        ("AIN1", "AIN1", "input", "L", "R_IN1"), ("BIN1", "BIN1", "input", "L", "R_IN1"),
        ("AIN2", "AIN2", "input", "L", "R_IN2"), ("BIN2", "BIN2", "input", "L", "R_IN2"),
        ("AO1", "AO1", "output", "R", "R_AO1"), ("AO2", "AO2", "output", "R", "R_AO2"),
        ("BO1", "BO1", "output", "R", "R_BO1"), ("BO2", "BO2", "output", "R", "R_BO2"),
        ("GND", "GND", "power_in", "B", "GND")]),
    ("U6", "INMP441", 45, 180, [
        ("VDD", "VDD", "power_in", "T", "3V3_BRAIN"), ("SCK", "BCLK", "input", "L", "MIC_BCLK"),
        ("WS", "WS", "input", "L", "MIC_WS"), ("LR", "L/R", "input", "L", "GND"),
        ("SD", "SD", "output", "R", "MIC_SD"), ("GND", "GND", "power_in", "B", "GND")]),
    ("U7", "MAX98357A", 135, 180, [
        ("VCC", "VCC", "power_in", "T", "5V_BRAIN"), ("DIN", "DIN", "input", "L", "AMP_DIN"),
        ("BCLK", "BCLK", "input", "L", "AMP_BCLK"), ("LRC", "LRC", "input", "L", "AMP_LRC"),
        ("GAIN", "GAIN", "passive", "L", None), ("SD", "SD", "passive", "L", None),
        ("SPK+", "SPK+", "output", "R", "SPK_P"), ("SPK-", "SPK-", "output", "R", "SPK_N"),
        ("GND", "GND", "power_in", "B", "GND")]),
    ("U8", "OLED I2C", 225, 180, [
        ("VCC", "VCC", "power_in", "T", "3V3_BRAIN"), ("SDA", "SDA", "bidirectional", "L", "OLED_SDA"),
        ("SCL", "SCL", "input", "L", "OLED_SCL"), ("GND", "GND", "power_in", "B", "GND")]),
    ("U9", "LEVEL SHIFT 4CH", 310, 232, [
        ("HV", "HV", "power_in", "T", "5V_TANG"), ("LV", "LV", "power_in", "T", "3V3_TANG"),
        ("HV2", "HV2", "input", "L", "ENC_R_5V"), ("LV2", "LV2", "output", "R", "ENC_R_3V3"),
        ("GND", "GND", "power_in", "B", "GND")]),
    ("U10", "ENCODER ONE OUT", 210, 232, [
        ("VCC", "VCC 5V", "power_in", "T", "5V_TANG"), ("OUT", "OUT", "output", "R", "ENC_R_5V"),
        ("GND", "GND", "power_in", "B", "GND")]),
    ("LS1", "SPEAKER 4R 3W", 130, 242, [
        ("1", "SPK+", "passive", "L", "SPK_P"), ("2", "SPK-", "passive", "L", "SPK_N")]),
    ("R1", "1k STBY LEFT", 220, 139, [("1", "1", "passive", "L", "STBY_COMMAND"), ("2", "2", "passive", "R", "STBY_L")]),
    ("R2", "1k STBY RIGHT", 275, 161, [("1", "1", "passive", "L", "STBY_COMMAND"), ("2", "2", "passive", "R", "STBY_R")]),
]

def generate(output):
    root_id=uid("sheet")
    libs=[];instances=[];wires=[];manifest={"scope":"simplev1 USB bench wiring; NOT PCB", "pins":[]}
    for ref,title,cx,cy,pins in PARTS:
        is_resistor=ref.startswith("R")
        w=6.35 if is_resistor else 18.0
        max_side=max(sum(p[3]==s for p in pins) for s in "LR")
        h=3.81 if is_resistor else max(13.97,(max_side+3)*2.54)
        points={}
        for side in "LRTB":
            items=[p for p in pins if p[3]==side]
            for i,p in enumerate(items):
                along=(i-(len(items)-1)/2)*(15.24 if side in "TB" else 5.08)
                points[p[0]]=(-w-3.81,-along,0) if side=="L" else (w+3.81,-along,180) if side=="R" else (along,h+3.81,270) if side=="T" else (along,-h-3.81,90)
        libname="Simple_"+ref
        pin_text=[]
        for number,name,kind,side,net in pins:
            x,y,angle=points[number]
            pin_text.append(f'(pin {kind} line (at {x} {y} {angle}) (length 3.81) (name {q(name)} {effects(.9)}) (number {q(number)} {effects(.8)}))')
        libs.append(f'(symbol "SIMPLE:{libname}" (pin_names (offset .7)) (in_bom yes) (on_board no) '
                    f'(property "Reference" {q(ref)} (at 0 {h+7.62} 0) {effects()}) '
                    f'(property "Value" {q(title)} (at 0 {h+5.08} 0) {effects()}) '
                    f'(symbol "{libname}_0_1" (rectangle (start {-w} {h}) (end {w} {-h}) (stroke (width .254) (type default)) (fill (type background)))) '
                    f'(symbol "{libname}_1_1" {" ".join(pin_text)}))')
        part_id=uid(ref)
        ref_y=cy-h-8.89 if is_resistor else cy-h+2.54
        title_y=cy-h-6.35 if is_resistor else cy-h+5.08
        instances.append(f'(symbol (lib_id "SIMPLE:{libname}") (at {cx} {cy} 0) (unit 1) (in_bom yes) (on_board no) (dnp no) (uuid "{part_id}") '
                         f'(property "Reference" {q(ref)} (at {cx} {ref_y} 0) {effects(1.0)}) '
                         f'(property "Value" {q(title)} (at {cx} {title_y} 0) {effects(.95)}) '
                         +" ".join(f'(pin {q(p[0])} (uuid "{uid(ref+":"+p[0])}"))' for p in pins)
                         +f' (instances (project "simplev1" (path "/{root_id}" (reference {q(ref)}) (unit 1)))))')
        for number,name,kind,side,net in pins:
            x,y,angle=points[number];x+=cx;y=cy-y
            if net is None:
                wires.append(f'(no_connect (at {x} {y}) (uuid "{uid(ref+number+":nc")}"))');continue
            dx,dy={"L":(-5.08,0),"R":(5.08,0),"T":(0,-5.08),"B":(0,5.08)}[side]
            ex,ey=x+dx,y+dy
            wires.append(f'(wire (pts (xy {x} {y}) (xy {ex} {ey})) (stroke (width 0) (type default)) (uuid "{uid(ref+number+":wire")}"))')
            label_angle=0
            justify="right" if side=="L" else "left"
            wires.append(f'(label {q(net)} (at {ex} {ey} {label_angle}) (effects (font (size .9 .9)) (justify {justify} bottom)) (uuid "{uid(ref+number+":label")}"))')
            manifest["pins"].append({"ref":ref,"pin":number,"net":net,"type":kind})
    notes=[("SIMPLEV1 | MOTION HOSTS WEB | SPI TO FPGA",15,15,1.8),
           ("USB bench: no motors attached. Signal-level connection reference, not a PCB release.",15,22,1.1),
           ("Separate USB5V controller supplies; COMMON GND. Do not join the three USB5V rails.",15,29,1),
           ("Tang Pxx = FPGA package pin, not header ordinal. SPI/encoder/DRV pads here are 3V3.",15,36,1),
           ("VM_5V_BENCH: separate USB5V, unloaded bridge measurement only; never laptop USB for motors.",15,43,1),
           ("REMOVE old P48-GPIO6 / P51-GPIO7 and P33/P34-GPIO8/9 pull-up fixture.",15,50,1),
           ("Motion GPIO17/18 damaged: leave unconnected. STBY10 is OUTPUT, never tie to 3V3.",15,57,1),
           ("AIN1/BIN1 share IN1; AIN2/BIN2 share IN2. AO/BO power outputs remain separate.",15,270,1),
           ("Only right encoder fitted: optional left later OUT-HV1/LV1-P27; change P27 pull to NONE.",15,277,1)]
    text="\n".join(f'(text {q(s)} (at {x} {y} 0) (effects (font (size {size} {size})) (justify left)) (uuid "{uid(s)}"))' for s,x,y,size in notes)
    raw=f'(kicad_sch (version 20250114) (generator "eeschema") (generator_version "10.0") (uuid "{root_id}") (paper "A3")\n'
    raw+='(title_block (title "AW-Car simplev1 - Bench interconnect") (date "2026-11-10") (rev "1") (company "AW-Car") (comment 1 "Logical module IDs only - PCB deferred"))\n'
    raw+='(lib_symbols\n'+"\n".join(libs)+')\n'+"\n".join(wires+instances)+"\n"+text+"\n)\n"
    output.parent.mkdir(parents=True,exist_ok=True);output.write_text(raw,encoding="utf-8")
    (ROOT / "data/wiring.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",type=Path,default=ROOT / "schematic/simplev1.kicad_sch")
    parser.add_argument("--force",action="store_true")
    args=parser.parse_args()
    if args.output.exists() and not args.force:
        raise SystemExit("Existing editable schematic protected; choose another --output or explicit --force")
    generate(args.output)
