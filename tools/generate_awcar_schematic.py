"""Generate editable KiCad connection-review sheets; never create a PCB.

Module pins use explicit logical IDs (GPIO/P-package), not guessed header pads.
Standard passive/BJT graphics are embedded from the installed KiCad library.
Run KiCad ERC and export its netlist separately; generation is not validation.
"""
import argparse
import json
from pathlib import Path
import re
import shutil
import tempfile
import uuid

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "hardware/pcb/kicad"
NS = uuid.UUID("35da800e-594c-4b8d-9679-0969abeb6e08")


def uid(name):
    return str(uuid.uuid5(NS, name))


def q(value):
    return json.dumps(str(value), ensure_ascii=False)


def block(text, start):
    depth, quoted, escaped = 0, False, False
    for end in range(start, len(text)):
        c = text[end]
        if quoted:
            if escaped:
                escaped = False
            elif c == "\\":
                escaped = True
            elif c == '"':
                quoted = False
        elif c == '"':
            quoted = True
        elif c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
            if depth == 0:
                return text[start:end + 1]
    raise ValueError("Unterminated KiCad expression")


def standard(library, name, new_name):
    text = library.read_text(encoding="utf-8")
    match = re.search(r'\(symbol "' + re.escape(name) + r'"\s', text)
    if not match:
        raise ValueError(f"Missing symbol {name}: {library}")
    raw = "\n".join(line.rstrip() for line in block(text, match.start()).splitlines())
    if "(extends " in raw:
        raise ValueError("Resolve inherited symbols explicitly")
    raw = raw.replace(f'"{name}_', f'"{new_name}_')
    return raw.replace(f'(symbol "{name}"', f'(symbol "AWCAR:{new_name}"', 1)


def effects(size=1.0, extra=""):
    return f"(effects (font (size {size} {size})) {extra})"


def snap(number):
    return round(round(number / 1.27) * 1.27, 4)


class Library:
    def __init__(self):
        self.symbols = {}

    def add(self, name, raw):
        self.symbols[name] = raw

    def module(self, name, pins, width=40):
        # pins: logical ID, visible name, electrical type, L/R side
        width = snap(width / 2) * 2
        height = max(sum(p[3] == side for p in pins) for side in "LR") * 5.08 + 5.08
        items = [f'(symbol "AWCAR:{name}" (pin_names (offset 1))',
                 '(in_bom yes) (on_board yes)',
                 f'(property "Reference" "U" (at 0 {snap(height/2+5.08)} 0) {effects()})',
                 f'(property "Value" {q(name)} (at 0 {snap(height/2+2.54)} 0) {effects()})']
        items.append(f'(symbol "{name}_0_1" (rectangle (start {-width/2} {height/2}) '
                     f'(end {width/2} {-height/2}) (stroke (width .254) (type default)) '
                     '(fill (type background))))')
        placed = dict(L=0, R=0)
        items.append(f'(symbol "{name}_1_1"')
        for number, label, kind, side in pins:
            y = snap(height/2 - 5.08 - placed[side]*5.08)
            placed[side] += 1
            x, angle = (-width/2 - 2.54, 0) if side == "L" else (width/2 + 2.54, 180)
            items.append(f'(pin {kind} line (at {x:g} {y:g} {angle}) (length 2.54) '
                         f'(name {q(label)} {effects(.9)}) '
                         f'(number {q(number)} {effects(.75)}))')
        items.append('))')
        self.add(name, "\n".join(items))

    def pins(self, name):
        raw = self.symbols[name]
        result = {}
        for match in re.finditer(r'\(pin\s+\w+\s+\w+\s', raw):
            p = block(raw, match.start())
            xy = re.search(r'\(at\s+([-+.\deE]+)\s+([-+.\deE]+)\s+([-+.\deE]+)', p)
            number = re.search(r'\(number\s+"([^"]+)"', p)[1]
            result[number] = tuple(map(float, xy.groups()))
        return result


class Sheet:
    def __init__(self, lib, stem, title, page, root=None):
        self.lib, self.stem, self.title, self.page = lib, stem, title, page
        self.uuid = uid(stem)
        self.project = "aw_car" if root or stem=="aw_car" else stem
        self.path = "/" + uid("aw_car") + "/" + uid("sheet_" + stem) if root else "/" + self.uuid
        self.parts, self.used, self.count = [], set(), 0
        self.nodes = {}

    def append(self, value):
        self.parts.append(value)

    def text(self, text, x, y, size=1.1):
        self.append(f'(text {q(text)} (at {x} {y} 0) {effects(size, "(justify left)")} '
                    f'(uuid {q(uid(self.stem+"text"+str(len(self.parts))))}))')

    def wire(self, a, b):
        a, b = tuple(map(snap, a)), tuple(map(snap, b))
        self.count += 1
        self.append(f'(wire (pts (xy {a[0]:g} {a[1]:g}) (xy {b[0]:g} {b[1]:g})) '
                    '(stroke (width 0) (type default)) '
                    f'(uuid {q(uid(self.stem+"wire"+str(self.count)))}))')

    def label(self, net, at, angle=0):
        at = tuple(map(snap, at))
        self.count += 1
        self.append(f'(global_label {q(net)} (shape bidirectional) '
                    f'(at {at[0]:g} {at[1]:g} {angle}) {effects(.9,"(justify right)" if angle==180 else "(justify left)")} '
                    f'(uuid {q(uid(self.stem+"label"+str(self.count)))}))')

    def part(self, name, ref, value, x, y, nets, labels=True, metadata=None):
        x, y = snap(x), snap(y)
        self.used.add(name)
        def prop(key, val):
            m=re.search(r'\(property "'+key+r'" "[^\"]*"\s+\(at\s+([-+.\deE]+)\s+([-+.\deE]+)', self.lib.symbols[name])
            px,py=map(float,m.groups()) if m else (0,5.08)
            align="(justify left)" if px>0 else "(justify right)" if px<0 else ""
            return f'(property {q(key)} {q(val)} (at {x+px:g} {y-py:g} 0) {effects(.95,align)})'
        inst = [f'(symbol (lib_id "AWCAR:{name}") (at {x} {y} 0) (unit 1)',
                '(in_bom yes) (on_board yes) (dnp no)',
                f'(uuid {q(uid(self.stem+ref))})',
                prop("Reference",ref), prop("Value",value),
                f'(property "Footprint" "" (at {x} {y} 0) {effects(.9, "(hide yes)")})',
                f'(property "Review_Status" "DRAFT_NOT_FOR_PCB" (at {x} {y} 0) {effects(.9, "(hide yes)")})']
        for key, val in (metadata or {}).items():
            inst.append(f'(property {q(key)} {q(val)} (at {x} {y} 0) {effects(.9, "(hide yes)")})')
        for number, (px, py, angle) in self.lib.pins(name).items():
            self.nodes[(ref, number)] = point = (x+px, y-py)
            inst.append(f'(pin {q(number)} (uuid {q(uid(self.stem+ref+number))}))')
            if number not in nets:
                self.append(f'(no_connect (at {point[0]:g} {point[1]:g}) '
                            f'(uuid {q(uid(self.stem+ref+number+"nc"))}))')
            elif labels:
                direction = -1 if angle == 0 else 1
                end = (point[0]+direction*5.08, point[1])
                self.wire(point, end)
                self.label(nets[number], end, 0 if direction == 1 else 180)
        contexts=[(self.project,self.path)]
        if self.stem=="stby_clamps":
            contexts.append(("stby_simulation","/"+uid("stby_simulation")+"/"+uid("sheet_stby_clamps")))
        inst.append('(instances '+''.join(f'(project {q(p)} (path {q(path)} (reference {q(ref)}) (unit 1)))' for p,path in contexts)+'))')
        self.append("\n".join(inst))

    def save(self):
        raw = ['(kicad_sch (version 20250114) (generator "eeschema") (generator_version "10.0")',
               f'(uuid {q(self.uuid)}) (paper "A3")',
               f'(title_block (title {q(self.title)}) (date "2026-11-07") (rev "0.1 REVIEW") '
               '(company "AW-Car") (comment 1 "DRAFT - NO PCB / NO FABRICATION RELEASE") '
               '(comment 2 "GPIO/package IDs are NOT module header pad numbers"))',
               '(lib_symbols', *[self.lib.symbols[n] for n in sorted(self.used)], ')',
               *self.parts, '(embedded_fonts no))']
        (OUT / (self.stem + ".kicad_sch")).write_text("\n".join(raw)+"\n", encoding="utf-8", newline="\n")


def connector(lib, name, labels):
    lib.module(name, [(str(i), text, "passive", "L") for i, text in enumerate(labels, 1)], 26)


def generate(kicad_root, overwrite=False):
    OUT.mkdir(parents=True, exist_ok=True)
    existing = [p for p in OUT.iterdir() if p.suffix in (".kicad_sch", ".kicad_sym", ".kicad_pro", ".lib") or p.name=="sym-lib-table"]
    if existing and not overwrite:
        raise ValueError("Existing editable KiCad sources: refusing to overwrite. Use --overwrite only after reviewing manual edits; sources will be backed up.")
    if existing:
        parent=ROOT/"build/kicad-source-backups"
        parent.mkdir(parents=True,exist_ok=True)
        backup=Path(tempfile.mkdtemp(prefix="before-regenerate-",dir=parent))
        for path in existing:
            shutil.copy2(path,backup/path.name)
        print(f"Previous editable source preserved at {backup}")
    lib = Library()
    symbols = kicad_root / "share/kicad/symbols"
    lib.add("R", standard(symbols / "Device.kicad_sym", "R", "R"))
    lib.add("C", standard(symbols / "Device.kicad_sym", "C", "C"))
    lib.add("Fuse",standard(symbols/"Device.kicad_sym","Fuse","Fuse"))
    lib.add("Switch",standard(symbols/"Switch.kicad_sym","SW_SPST","Switch"))
    lib.add("NPN", standard(symbols / "Transistor_BJT.kicad_sym", "Q_NPN_EBC", "NPN"))
    lib.add("D",standard(symbols/"Device.kicad_sym","D","D"))
    lib.add("VDC",standard(symbols/"Simulation_SPICE.kicad_sym","VDC","VDC"))
    lib.add("VPULSE",standard(symbols/"Simulation_SPICE.kicad_sym","VPULSE","VPULSE"))
    brain = [("5V", "5V input - source TBD", "passive", "L"), ("GND", "GND", "passive", "L"),
             ("GPIO6", "MIC SD", "input", "L"), ("GPIO18", "UART RX", "input", "L"),
             ("3V3", "local 3V3", "power_out", "R")]
    brain += [(f"GPIO{n}", label, "output" if n not in (41,42) else "bidirectional", "R")
              for n,label in [(4,"MIC WS"),(5,"MIC BCLK"),(7,"AMP DIN"),(15,"AMP BCLK"),
                              (16,"AMP LRCLK"),(17,"UART TX"),(41,"OLED SDA"),(42,"OLED SCL")]]
    lib.module("Brain_Logical", brain)
    motion = [("5V", "5V input - source TBD", "passive", "L"), ("GND", "GND", "passive", "L")]
    motion += [(f"GPIO{n}", label, "input", "L") for n,label in [(14,"Brain RX"),(16,"FPGA RX"),
                  (6,"recovery ACK"),(7,"FPGA permit"),(8,"safety OK"),(9,"gate fault_n")]]
    motion += [(f"GPIO{n}", label, "output", "R") for n,label in [(13,"Brain TX"),(15,"FPGA TX"),
                  (4,"motion permit"),(5,"recovery REQ"),(10,"driver permit")]]
    motion += [("3V3", "local 3V3", "power_out", "R")]
    lib.module("Motion_Logical", motion)
    pins = json.loads((ROOT/"fpga/targets/tang_nano9k/pinout.json").read_text())["pins"]
    fpga = [("5V", "5V input - source TBD", "passive", "L"), ("GND", "GND", "passive", "L")]
    fpga += [(f'P{p["package_pin"]}', p["signal"], p["direction"], "L" if p["direction"] == "input" else "R")
             for p in pins if p.get("header")]
    fpga += [("3V3", "local 3V3", "power_out", "R")]
    lib.module("Tang_Logical", fpga, 46)
    connector(lib,"OLED",["GND","VCC 3V3","SCL","SDA"])
    connector(lib,"MIC",["VDD 3V3","GND","BCLK","WS","SD","L/R=GND"])
    lib.module("AMP",[("VCC","VCC 5V","passive","L"),("GND","GND","passive","L"),
        ("DIN","DIN","input","L"),("BCLK","BCLK","input","L"),("LRC","LRC","input","L"),
        ("GAIN","GAIN","passive","L"),("SD","SD","passive","L"),
        ("SPK+","SPK+","output","R"),("SPK-","SPK-","output","R")],32)
    connector(lib,"Speaker",["SPK+ (floating)","SPK- (floating)"])
    connector(lib,"Sensor",["VCC TBD","GND","signal A TBD","signal B TBD"])
    drv = [(p,p,"input","L") for p in ("AIN1","AIN2","BIN1","BIN2","STBY")]
    drv += [(p,p,"passive" if p in ("VM","GND") else "output","R") for p in ("VM","GND","AOUT1","AOUT2","BOUT1","BOUT2")]
    lib.module("DRV_Module_Logical",drv,34)
    connector(lib,"Motor",["motor terminal 1","motor terminal 2"])
    connector(lib,"Gate_Interface",["driver_permit","fpga_permit","gate_clear","safety_ok","gate_fault_n","ALLOW to clamps","GND"])
    connector(lib,"Testpoint",["test point"])
    lib.module("Encoder",[("VCC","5V","passive","L"),("GND","GND","passive","L"),
                           ("OUT","single OUT","output","R")],28)
    lib.module("LVC2G17",[("1","1A","input","L"),("3","2A","input","L"),
                          ("2","GND","passive","L"),("5","VCC 3V3","power_in","L"),
                          ("6","1Y","output","R"),("4","2Y","output","R")],30)
    connector(lib,"Expansion",["I2C SDA - GPIO TBD","I2C SCL - GPIO TBD","TCRT left - GPIO TBD","TCRT right - GPIO TBD","GND"])
    connector(lib,"Pack",["PROTECTED pack +","pack return"])
    lib.module("DSN6000AUD",[("IN+","IN+","passive","L"),("IN-","IN-","passive","L"),
                             ("OUT+","OUT+ adjust 5V","passive","R"),("OUT-","OUT-","passive","R")],38)
    sheets=[]
    s=Sheet(lib,"controllers","Brain - Motion - Tang: verified logical connections",2,True)
    s.text("VERIFIED GPIO CONTRACT | module header numbering/footprints NOT selected",20,20,1.5)
    s.text("Motion GPIO17/18 damaged: do not use. Keep each board's 3V3 rail separate.",20,29)
    s.part("Brain_Logical","U1","ESP32-S3 Brain module",70,100,{
        "5V":"5V_BRAIN_SOURCE_TBD","GND":"GND","3V3":"3V3_BRAIN","GPIO6":"MIC_SD",
        "GPIO18":"MTN_TX_BRN_RX","GPIO17":"BRN_TX_MTN_RX","GPIO4":"MIC_WS","GPIO5":"MIC_BCLK",
        "GPIO7":"AMP_DIN","GPIO15":"AMP_BCLK","GPIO16":"AMP_LRCLK","GPIO41":"OLED_SDA","GPIO42":"OLED_SCL"})
    s.part("Motion_Logical","U2","ESP32-S3 Motion module",210,100,{
        "5V":"5V_MOTION_SOURCE_TBD","GND":"GND","3V3":"3V3_MOTION","GPIO14":"BRN_TX_MTN_RX",
        "GPIO13":"MTN_TX_BRN_RX","GPIO15":"MTN_TX_FPGA_RX","GPIO16":"FPGA_TX_MTN_RX",
        "GPIO4":"MOTION_PERMIT","GPIO5":"RECOVERY_REQ","GPIO6":"RECOVERY_ACK","GPIO7":"FPGA_PERMIT",
        "GPIO8":"SAFETY_OK","GPIO9":"GATE_FAULT_N","GPIO10":"DRIVER_PERMIT"})
    fnet={25:"MTN_TX_FPGA_RX",26:"FPGA_TX_MTN_RX",27:"ENC_L_CONDITIONED",28:"ENC_R_CONDITIONED",
          29:"MOTION_PERMIT",30:"RECOVERY_REQ",33:"SAFETY_OK",34:"GATE_FAULT_N",35:"DRV_L_IN1",
          40:"DRV_L_IN2",41:"DRV_R_IN1",42:"DRV_R_IN2",48:"RECOVERY_ACK",49:"GATE_CLEAR",51:"FPGA_PERMIT"}
    s.part("Tang_Logical","U3","Tang Nano9K - package IDs",345,100,{"5V":"5V_TANG_SOURCE_TBD","GND":"GND",
          "3V3":"3V3_TANG",**{f"P{k}":v for k,v in fnet.items()}})
    s.text("All shown external Tang GPIO are 3V3. Onboard reset/LED bank1V8 must not be connected to these rails.",20,190)
    s.text("USB/battery source selection pending. This sheet does not authorize joining USB VBUS to buck output.",20,200)
    s.part("Testpoint","TP1","Motion local 3V3",210,225,{"1":"3V3_MOTION"})
    s.part("Testpoint","TP2","Tang local 3V3",345,225,{"1":"3V3_TANG"})
    sheets.append(s)
    s=Sheet(lib,"power_review","Protected 2S and DSN6000AUD - source selection PENDING",8,True)
    s.text("POWER REVIEW ONLY: cell/BMS/charger/fuse ratings and USB VBUS paths are NOT selected or tested.",20,20,1.35)
    s.part("Pack","J30","2S protected pack output ONLY",70,70,{"1":"PACK_PROTECTED_PLUS","2":"GND"})
    s.part("Fuse","F1","RATING_TBD",170,65,{"1":"PACK_PROTECTED_PLUS","2":"PACK_FUSED"})
    s.part("Switch","SW1","MAIN_SWITCH_DC_RATING_TBD",265,65,{"1":"PACK_FUSED","2":"VM_MOTOR"})
    s.part("DSN6000AUD","U11","DSN6000AUD removable module",100,165,{"IN+":"VM_MOTOR","IN-":"GND","OUT+":"5V_DSN_UNVERIFIED","OUT-":"GND"})
    s.part("Testpoint","TP3","Adjust/test 5V BEFORE boards",230,155,{"1":"5V_DSN_UNVERIFIED"})
    s.text("VM_MOTOR branches directly to motor drivers and to the logic converter input. NO motor buck; E-stop circuit pending.",20,220)
    s.text("5V_DSN_UNVERIFIED -> board/amp source-selection network PENDING; board 5V nets intentionally remain separate.",20,230)
    s.text("Do NOT substitute raw 18650 cells for J30. BMS/common-vs-separate charge ports and charger must match the actual pack.",20,240)
    s.text("Converter listing is not proof of continuous 5V load/ripple/thermal behavior. Place the physical fuse close to the pack.",20,250)
    s.text("No direct DSN/USB VBUS connection is approved. GPIO power-off/backfeed, switch DC rating and fuse/wire sizing remain blockers.",20,260)
    sheets.append(s)
    s=Sheet(lib,"audio_oled","Brain peripherals - removable harness pin proposals",3,True)
    s.text("Carrier connector order proposed below; match cables to actual module silkscreen before assembly.",20,20,1.3)
    s.part("OLED","J1","OLED 0.96 I2C",70,75,{"1":"GND","2":"3V3_BRAIN","3":"OLED_SCL","4":"OLED_SDA"})
    s.part("MIC","J2","INMP441",180,75,{"1":"3V3_BRAIN","2":"GND","3":"MIC_BCLK","4":"MIC_WS","5":"MIC_SD","6":"GND"})
    s.part("AMP","U6","MAX98357A module (logical pins)",300,75,{"VCC":"5V_AMP_SOURCE_TBD","GND":"GND","DIN":"AMP_DIN","BCLK":"AMP_BCLK","LRC":"AMP_LRCLK","SPK+":"SPK_PLUS","SPK-":"SPK_MINUS"})
    s.part("Speaker","J4","4ohm 3W speaker",300,160,{"1":"SPK_PLUS","2":"SPK_MINUS"})
    s.text("J4 connects to the amplifier OUTPUT terminal, not directly to ESP32. Neither speaker terminal is GND.",20,215)
    s.text("AMP GAIN/SD left open only if the real breakout's default bias is verified. Check both module sides.",20,225)
    s.text("Local 100n/10u decoupling and bulk capacitor sizing require converter/audio load checks; not signed off.",20,235)
    sheets.append(s)
    s=Sheet(lib,"drivers","Two DRV modules - one H bridge per motor",4,True)
    s.text("DRAFT: STBY silicon/net/pull-up must be verified on the actual modules. NC is NOT assumed nFAULT.",20,20,1.3)
    for side,x,ref,base in [("L",90,"U4",5),("R",275,"U5",7)]:
        s.part("DRV_Module_Logical",ref,f"DRV8833 module {side}",x,85,{
            "AIN1":f"DRV_{side}_IN1","BIN1":f"DRV_{side}_IN1","AIN2":f"DRV_{side}_IN2","BIN2":f"DRV_{side}_IN2",
            "STBY":f"STBY_{side}","VM":"VM_MOTOR","GND":"GND",
            **{p:f"{side}_{p}" for p in ("AOUT1","AOUT2","BOUT1","BOUT2")}})
        for j,letter in enumerate("AB"):
            s.part("Motor",f"J{base+j}",f"{side} motor {j+1}",x+50,160+j*45,{"1":f"{side}_{letter}OUT1","2":f"{side}_{letter}OUT2"})
    s.text("AIN/BIN share only LOGIC inputs. Motor/H-bridge outputs stay separate; motor polarity is verified with wheels raised.",20,248)
    s.text("VM is protected 2S directly (no motor buck). Fuse/current/wire ratings and VM decoupling remain to be selected.",20,258)
    sheets.append(s)
    s=Sheet(lib,"safety_contract","Required safety interface - actual latch/watchdog circuit PENDING",5,True)
    s.text("THIS IS AN INTERFACE CONTRACT, NOT AN IMPLEMENTED SAFETY GATE",20,20,1.7)
    s.part("Gate_Interface","J9","Gate/latch/watchdog required interface",100,95,{
        "1":"DRIVER_PERMIT","2":"FPGA_PERMIT","3":"GATE_CLEAR","4":"SAFETY_OK","5":"GATE_FAULT_N","6":"GATE_ALLOW","7":"GND"})
    for i,text in enumerate([
        "Required: hardware E-stop/undervoltage independently force driver OFF; logic/audio remain powered.",
        "Fault latches until a NEW clear edge while both permits are LOW; releasing E-stop never clears it.",
        "Static FPGA permit HIGH is insufficient: independent edge/heartbeat watchdog must detect lost FPGA clock.",
        "ALLOW requires both permits, safety_ok, latch healthy AND the independently qualified live indication.",
        "No tied-HIGH health pins, software-only E-stop or bypass jumper to simulate a working gate.",
        "Candidate STBY clamps on next sheet are ONLY the output stage; they do not implement the latch/watchdog.",
        "Current firmware remains LOCKED. Physical ARM/power test awaits gate design and electrical review."]):
        s.text(text,20,160+i*10)
    sheets.append(s)
    s=Sheet(lib,"stby_clamps","Candidate default-OFF STBY output stage - simulation required",6,True)
    s.text("Candidate: 2x NPN per driver; raw VM never connects to a GPIO. Not a complete safety gate.",20,20,1.35)
    s.text("Rpull assumes real STBY is nSLEEP with only a resistor pull-up. Verify module; stop if tied directly to VM.",20,30)
    for offset,side,idx in [(0,"L",0),(190,"R",1)]:
        prefix=100+idx*10
        x=offset
        defs=[("R",f"R{prefix+1}","47k",124+x,80,{"1":"VM_MOTOR","2":f"CLAMP_BASE_{side}"}),
              ("R",f"R{prefix+2}","47k",142.54+x,80,{"1":"VM_MOTOR","2":f"STBY_{side}"}),
              ("R",f"R{prefix+3}","10k",80+x,100,{"1":"GATE_ALLOW","2":f"RELEASE_BASE_{side}"}),
              ("R",f"R{prefix+4}","100k",80+x,135,{"1":f"RELEASE_BASE_{side}","2":"GND"}),
              ("NPN",f"Q{prefix+1}","2N3904 candidate",140+x,100,{"1":"GND","2":f"CLAMP_BASE_{side}","3":f"STBY_{side}"}),
              ("NPN",f"Q{prefix+2}","2N3904 candidate",95+x,120,{"1":"GND","2":f"RELEASE_BASE_{side}","3":f"CLAMP_BASE_{side}"})]
        for name,ref,value,px,py,net in defs:
            s.part(name,ref,value,px,py,net,False,metadata={"Circuit_Block":"STBY_CLAMP", "Simulation_Model":"GENERIC_NPN_NOT_VENDOR_CHARACTERIZATION",
                "Sim.Library":"generic-clamp.lib","Sim.Name":"QGEN","Sim.Pins":"3=1 2=2 1=3"} if name=="NPN" else None)
        # Explicit wires, independently checked through KiCad's exported XML netlist.
        for ref,pin,net in [(f"R{prefix+1}","1","VM_MOTOR"),(f"R{prefix+2}","1","VM_MOTOR"),
                            (f"R{prefix+3}","1","GATE_ALLOW"),(f"R{prefix+4}","2","GND"),
                            (f"Q{prefix+1}","1","GND"),(f"Q{prefix+2}","1","GND")]:
            point=s.nodes[(ref,pin)]; end=(point[0],point[1]+(-8 if net!="GND" else 8));s.wire(point,end);s.label(net,end)
        rb=s.nodes[(f"R{prefix+1}","2")];qb=s.nodes[(f"Q{prefix+1}","2")];rc=s.nodes[(f"Q{prefix+2}","3")]
        corner=(rb[0],qb[1]);s.wire(rb,corner);s.wire(corner,qb);s.wire(rc,(rc[0],qb[1]));s.wire((rc[0],qb[1]),corner)
        ra=s.nodes[(f"R{prefix+3}","2")];qr=s.nodes[(f"Q{prefix+2}","2")];rd=s.nodes[(f"R{prefix+4}","1")]
        node=(ra[0],qr[1]);s.wire(ra,node);s.wire(node,qr);s.wire(node,rd)
        rp=s.nodes[(f"R{prefix+2}","2")];qc=s.nodes[(f"Q{prefix+1}","3")];s.wire(rp,qc);s.label(f"STBY_{side}",(rp[0],rp[1]));
        # Junctions at the two branched base nets.
        for point in (corner,node):
            point=tuple(map(snap,point))
            s.append(f'(junction (at {point[0]:g} {point[1]:g}) (diameter 0) (color 0 0 0 0) (uuid {q(uid(side+str(point)))}))')
    s.text("ALLOW LOW/floating -> release transistor OFF -> VM biases clamp ON -> STBY LOW, including loss of logic supply.",20,185)
    s.text("ALLOW HIGH -> release sinks clamp base -> STBY rises through the verified pull-up. No high-voltage GPIO feedback.",20,195)
    s.text("Prototype/measure before use. Transistor, module pull-up, startup behavior, wake margin and cable-open behavior remain review items.",20,205)
    s.text("No footprint is assigned. Generic simulation is NOT a TI DRV8833 / vendor transistor / production safety certification.",20,215)
    sheets.append(s)
    s=Sheet(lib,"sensors","Encoder conditioning and future sensor harnesses",7,True)
    s.text("Encoder single OUT is NOT quadrature. Proposed 5V-tolerant LVC buffers; verify actual module electrical levels.",20,20,1.3)
    s.part("Encoder","U7","left encoder module",70,70,{"VCC":"5V_SENSOR_SOURCE_TBD","GND":"GND","OUT":"ENC_L_RAW"})
    s.part("Encoder","U8","right encoder module",70,130,{"VCC":"5V_SENSOR_SOURCE_TBD","GND":"GND","OUT":"ENC_R_RAW"})
    s.part("LVC2G17","U9","SN74LVC2G17 candidate",220,90,{"1":"ENC_L_RAW","3":"ENC_R_RAW","2":"GND","5":"3V3_MOTION","6":"ENC_L_CONDITIONED","4":"ENC_R_CONDITIONED"})
    s.part("C","C9","100n",270,110,{"1":"3V3_MOTION","2":"GND"})
    s.part("Sensor","J20","MPU6050 harness - order proposed",70,210,{"1":"3V3_SENSORS_TBD","2":"GND","3":"SENSOR_SDA_TBD","4":"SENSOR_SCL_TBD"})
    s.part("Sensor","J21","VL53L0X blue - verify pull-ups",200,210,{"1":"3V3_SENSORS_TBD","2":"GND","3":"SENSOR_SDA_TBD","4":"SENSOR_SCL_TBD"})
    s.part("Sensor","J22","TCRT5000 left DO",320,80,{"1":"5V_SENSOR_SOURCE_TBD","2":"GND","3":"TCRT_L_RAW"})
    s.part("Sensor","J23","TCRT5000 right DO",320,135,{"1":"5V_SENSOR_SOURCE_TBD","2":"GND","3":"TCRT_R_RAW"})
    s.part("LVC2G17","U10","SN74LVC2G17 candidate",325,205,{"1":"TCRT_L_RAW","3":"TCRT_R_RAW","2":"GND","5":"3V3_MOTION","6":"TCRT_L_GPIO_TBD","4":"TCRT_R_GPIO_TBD"})
    s.part("C","C10","100n",380,185,{"1":"3V3_MOTION","2":"GND"})
    s.part("Expansion","J24","Motion future GPIO - NOT assigned",200,145,{"1":"SENSOR_SDA_TBD","2":"SENSOR_SCL_TBD","3":"TCRT_L_GPIO_TBD","4":"TCRT_R_GPIO_TBD","5":"GND"})
    s.text("Sensor SDA/SCL and TCRT Motion GPIO assignments are pending firmware/physical-board review. Do not invent header pad numbers.",20,255,.95)
    sheets.append(s)
    sheets.sort(key=lambda sheet:sheet.page)
    root=Sheet(lib,"aw_car","AW-Car - removable-module connection review",1)
    root.text("AW-CAR | SCHEMATIC REVIEW 0.1",20,20,2.3)
    root.text("Schematic first. PCB, module pad numbers, connectors, source switching and gate circuit are NOT released.",20,32,1.25)
    for i,child in enumerate(sheets):
        x=25+(i%2)*190;y=50+(i//2)*47;su=uid("sheet_"+child.stem)
        root.append(f'(sheet (at {x} {y}) (size 160 30) (stroke (width .254) (type solid)) '
                    f'(fill (color 0 0 0 0)) (uuid {q(su)}) '
                    f'(property "Sheetname" {q(str(child.page)+"_"+child.stem)} (at {x} {y-2} 0) {effects(1.2,"(justify left)")}) '
                    f'(property "Sheetfile" {q(child.stem+".kicad_sch")} (at {x} {y+32} 0) {effects(.95,"(justify left)")}) '
                    f'(instances (project "aw_car" (path {q("/"+root.uuid)} (page {q(child.page)})))))')
        descriptions={
            "controllers":"UART / recovery / permit; verified logical GPIO IDs",
            "audio_oled":"OLED / mic / amplifier / floating speaker outputs",
            "drivers":"Two removable modules; four independent H bridges",
            "safety_contract":"REQUIREMENTS ONLY - latch/watchdog circuit pending",
            "stby_clamps":"Candidate output stage; generic SPICE bench available",
            "sensors":"Encoder conditioning / sensor harness / GPIO TBD",
            "power_review":"Protected 2S / fuse / DSN6000AUD; USB paths TBD"}
        root.text(descriptions[child.stem],x+5,y+12,1.1)
        root.text("Double-click sheet to inspect connections.",x+5,y+21,.95)
    root.text("Confirmed: 2 ESP32-S3 + Tang Nano9K + 2 DRV modules; 2S direct VM; separate DSN6000AUD logic supply.",20,255)
    root.text("Pending: battery/BMS/charger/fuse ratings, USB backfeed strategy, actual module headers, sensors and gate/watchdog selection.",20,264)
    for sheet in [root,*sheets]:
        sheet.save()
    # Separate native simulation bench: it includes the SAME clamp sheet.
    # The sources/load models here are test stimuli, never carrier components.
    bench=Sheet(lib,"stby_simulation","SPICE bench ONLY - candidate STBY output stages",1)
    bench.text("SIMULATION BENCH ONLY - generic transistor and approximate driver-input load",20,20,1.5)
    bench.part("VDC","V1","8.4",60,65,{"1":"VM_MOTOR","2":"GND"},metadata={"Sim.Device":"V","Sim.Type":"DC","Sim.Params":"dc=8.4","Sim.Pins":"1=+ 2=-"})
    bench.part("VPULSE","V2","ALLOW test pulse",60,130,{"1":"GATE_ALLOW","2":"GND"},metadata={"Sim.Device":"V","Sim.Type":"PULSE","Sim.Params":"y1=0 y2=3.3 td=5m tr=1u tf=1u tw=10m per=30m","Sim.Pins":"1=+ 2=-"})
    for x,side,start in [(200,"L",200),(330,"R",210)]:
        bench.part("R",f"R{start+1}","47k",x,65,{"1":"VM_MOTOR","2":f"STBY_{side}"})
        bench.part("R",f"R{start+2}","500k",x,110,{"1":f"STBY_{side}","2":"GND"})
        bench.part("C",f"C{start+1}","100p",x,155,{"1":f"STBY_{side}","2":"GND"})
        bench.part("D",f"D{start+1}","DZGEN",x,200,{"1":f"STBY_{side}","2":"GND"},metadata={"Sim.Library":"generic-clamp.lib","Sim.Name":"DZGEN","Sim.Pins":"2=1 1=2"})
    bench.append(f'(sheet (at 90 205) (size 85 35) (stroke (width .254) (type solid)) (fill (color 0 0 0 0)) '
        f'(uuid {q(uid("sheet_stby_clamps"))}) '
        f'(property "Sheetname" "Same_STBY_clamps" (at 90 202 0) {effects(1.1,"(justify left)")}) '
        f'(property "Sheetfile" "stby_clamps.kicad_sch" (at 90 242 0) {effects(1.0,"(justify left)")}) '
        f'(instances (project "stby_simulation" (path {q("/"+bench.uuid)} (page "2")))))')
    bench.text(".tran 2u 30m 0 1u",20,245)
    bench.text("Plot GATE_ALLOW / STBY_L / STBY_R. This bench does NOT include the latch, heartbeat watchdog, converter or motors.",20,255)
    bench.save()
    (OUT/"generic-clamp.lib").write_text('* Generic approximations only; NOT manufacturer-validated 2N3904/DRV8833 models.\n'
        '.model QGEN NPN(IS=6.7f BF=40 VAF=80 IKF=.1 CJE=8p CJC=4p TF=.3n)\n'
        '.model DZGEN D(BV=6.5 IBV=1u IS=1f)\n',encoding="ascii",newline="\n")
    (OUT/"aw_car.kicad_pro").write_text(json.dumps({"meta":{"filename":"aw_car.kicad_pro","version":1},
        "text_variables":{"REVIEW_STATUS":"DRAFT_NOT_FOR_PCB"}},indent=2)+"\n",encoding="utf-8",newline="\n")
    (OUT/"stby_simulation.kicad_pro").write_text(json.dumps({"meta":{"filename":"stby_simulation.kicad_pro","version":1}},indent=2)+"\n",encoding="utf-8",newline="\n")
    library_raw='(kicad_symbol_lib (version 20250114) (generator "kicad_symbol_editor")\n'
    for name,raw in lib.symbols.items():
        library_raw+=raw.replace(f'"AWCAR:{name}"',q(name),1)+"\n"
    (OUT/"aw_car.kicad_sym").write_text(library_raw+")\n",encoding="utf-8",newline="\n")
    (OUT/"sym-lib-table").write_text('(sym_lib_table (version 7) (lib (name "AWCAR") (type "KiCad") '
        '(uri "${KIPRJMOD}/aw_car.kicad_sym") (options "") (descr "AW-Car review symbols; module pin IDs logical only")))\n',encoding="utf-8",newline="\n")
    print(f"Generated {len(sheets)+1} native KiCad review sheets at {OUT}")


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--kicad-root",type=Path,default=Path("D:/APP/KiCad"))
    p.add_argument("--overwrite",action="store_true",help="explicitly regenerate existing sheets after preserving a build backup")
    a=p.parse_args()
    generate(a.kicad_root,a.overwrite)
