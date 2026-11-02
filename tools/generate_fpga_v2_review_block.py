#!/usr/bin/env python3
"""Generate a standalone, editable Draw.io REVIEW schematic for AW-Car FPGA v2.

Intentional isolation: NEVER writes to the V3/V4 Draw.io files.
Source of truth: aw_car_top.sv, drive_core.sv, fpga_link.sv,
firmware/shared/fpga-protocol-v2.md. All port directions are left to right.
"""

from __future__ import annotations

from dataclasses import dataclass
from html import escape
from math import atan2, cos, sin
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs" / "AW_Car_FPGA_RTL_Block_Review_v2.drawio"
PREVIEW = ROOT / "docs" / "AW_Car_FPGA_RTL_Block_Review_v2_preview.png"
WIDTH, HEIGHT = 2640, 1580

COLORS = {
    "background": "#0B1220", "panel": "#111C2D", "grid": "#263447",
    "text": "#EDF4FC", "muted": "#AABBD0", "border": "#3A4C65",
    "blue": "#57A6FF", "teal": "#32D6B1", "violet": "#B99BFF",
    "amber": "#F6C16C", "red": "#FF918E", "slate": "#B5C8E0",
}


@dataclass(frozen=True)
class Node:
    key: str
    x: int
    y: int
    w: int
    h: int
    title: str
    lines: tuple[str, ...]
    accent: str
    external: bool = False


@dataclass(frozen=True)
class Edge:
    key: str
    src: str
    dst: str
    label: str
    accent: str = "blue"
    exit: tuple[float, float] = (1.0, 0.5)
    enter: tuple[float, float] = (0.0, 0.5)
    points: tuple[tuple[int, int], ...] = ()
    dash: bool = False
    label_at: tuple[int, int] | None = None


NODES = [
    # CONTROL: real top-level input -> RX -> parser -> guard -> safety -> motor -> mask -> output.
    Node("rx_port", 48, 292, 195, 134, "MOTION → FPGA", ("rx : UART serial 3.3V", "115200 baud · 8N1", "CMD / HELLO / ARM / DISABLE"), "blue", True),
    Node("uart_rx", 303, 292, 215, 134, "uart_rx.sv", ("2FF sync + sample UART", "rx_byte[7:0]", "rx_valid / framing / break"), "blue"),
    Node("frame_rx", 576, 292, 247, 134, "frame_rx.sv", ("Preamble / v2 / length", "CRC16 + timeouts", "frame_valid · frame_payload"), "blue"),
    Node("guard", 887, 278, 266, 163, "command_guard.sv", ("Session / fresh sequence", "Validate flags / duty / DIR", "CMD events + duty pair"), "violet"),
    Node("safety", 1210, 273, 286, 173, "safety_fsm.sv", ("ARM / RECOVERY / FAULT", "Watchdog 50 ms", "motor_enable / motor_command"), "amber"),
    Node("motor", 1594, 278, 262, 163, "motor_pwm_pair.sv", ("pwm_pair.sv · 20 kHz", "RUN → ZERO → SETUP → LOAD", "raw_left/right + direction[1:0]"), "teal"),
    Node("mask", 1944, 282, 239, 154, "drive_core gating", ("output_allowed = async guards", "AND motor_enable", "pwm_left/right masked"), "red"),
    Node("pwmout", 2260, 280, 326, 127, "FPGA → ADAPTER / GATE", ("pwm_left : 1 bit", "pwm_right : 1 bit", "20 kHz · masked outputs"), "teal", True),
    Node("dirout", 2260, 427, 326, 102, "FPGA → ADAPTER", ("direction[1:0] · left/right", "DIR is NOT masked with PWM"), "amber", True),

    # SAFETY, GPIO, CLOCK/RESET: physical inputs on left; output ports on right.
    Node("safe_gpio", 48, 702, 247, 172, "SAFETY GPIO INPUT", ("motion_permit_async", "recovery_req_async", "safety_ok_async", "gate_fault_n_async"), "red", True),
    Node("sync", 367, 692, 324, 194, "INPUT CDC / RESET SYNC", ("reset_sync.sv  × safety/gate/permit", "input_sync_filter.sv  × controls", "rst_n, inputs_valid, controls[1:0]", "safety_ok, gate_ok, motion_permit"), "blue"),
    Node("clockin", 48, 916, 247, 96, "CLOCK / RESET INPUT", ("clk 27 MHz · arst_n active-LOW",), "slate", True),
    Node("reset", 367, 910, 324, 113, "RESET DISTRIBUTION", ("reset_sync.sv → rst_n", "clk/rst_n to synchronous RTL", "reset asserts async, releases synced"), "slate"),
    Node("safety_port", 1944, 752, 239, 166, "SAFETY OUTPUTS", ("fpga_permit = output_allowed", "gate_clear raw conditions", "recovery_ack / state / fault"), "amber"),
    Node("safetyout", 2260, 739, 326, 189, "FPGA → SAFETY PORTS", ("fpga_permit · recovery_ack", "gate_clear", "safety_state[7:0] · fault[15:0]", "external gate is NOT RTL"), "amber", True),

    # ENCODER -> STATUS v2 path. The encoder pair contains snapshot, not a separate snapshot RTL.
    Node("encoderin", 48, 1205, 247, 142, "2 × IR ENCODER OUT", ("left_out · right_out", "1 GPIO OUT per side", "level shift to 3.3 V if required"), "teal", True),
    Node("encoder", 376, 1190, 338, 173, "pulse_encoder_pair.sv", ("pulse_counter.sv × 2", "2FF + filter; rising edge only", "count / period / age / flags", "snapshot every 10 ms"), "teal"),
    Node("snapbus", 805, 1198, 343, 156, "ENCODER SNAPSHOT BUS", ("snapshot_valid + count_L/R", "period_L/R · age_L/R · flags", "timestamp[31:0] · seq[15:0]", "ready/dropped come from frame_tx"), "teal"),
    Node("frame_tx", 1257, 1195, 271, 160, "frame_tx.sv", ("STATUS v2: payload 34 B", "header + CRC16 → frame 47 B", "ready / valid / byte_last"), "violet"),
    Node("uart_tx", 1663, 1195, 243, 160, "uart_tx.sv", ("UART 115200 8N1", "byte_data / byte_ready", "tx_done after final stop bit"), "violet"),
    Node("txout", 2260, 1200, 326, 143, "FPGA → MOTION UART", ("tx : UART serial 3.3 V", "STATUS v2 / CRC16", "47 B · ~4.08 ms / frame"), "violet", True),
]

EDGES = [
    Edge("rx_to_uart", "rx_port", "uart_rx", "rx", "blue", label_at=(271, 260)),
    Edge("byte_bus", "uart_rx", "frame_rx", "byte_data[7:0] + byte_valid", "blue", label_at=(550, 249)),
    Edge("frame_bus", "frame_rx", "guard", "frame_valid + fields", "violet", label_at=(854, 249)),
    Edge("req_safety", "guard", "safety", "requests / command_valid", "amber", label_at=(1177, 249)),
    Edge("motor_auth", "safety", "motor", "motor_enable + motor_command", "amber", label_at=(1543, 249)),
    Edge("raw_pwm", "motor", "mask", "raw_left / raw_right", "teal", label_at=(1899, 249)),
    Edge("pwm_outputs", "mask", "pwmout", "pwm_left / pwm_right", "teal", label_at=(2220, 248)),
    Edge("direction_bypass", "motor", "dirout", "direction[1:0]", "amber", exit=(0.85, 1), enter=(0, 0.5), points=((1816, 517), (2236, 517)), label_at=(2061, 500)),
    Edge("duty_bus", "guard", "motor", "command_left/right[15:0] + direction[1:0]", "violet", exit=(0.47, 0), enter=(0.47, 0), points=((1012, 213), (1717, 213)), label_at=(1360, 190)),
    Edge("auth_back", "safety", "guard", "command_enable · active_session / seq_base / context_load", "amber", exit=(0.22, 1), enter=(0.62, 1), points=((1273, 553), (1052, 553)), label_at=(1172, 578)),
    Edge("pwm_rejected", "motor", "safety", "pwm_rejected", "red", exit=(0.35, 1), enter=(0.88, 1), points=((1685, 603), (1462, 603)), label_at=(1571, 626)),
    Edge("safety_raw_gpio", "safe_gpio", "sync", "GPIO raw", "red", label_at=(333, 674)),
    Edge("clk_reset", "clockin", "reset", "clk / arst_n", "slate", label_at=(333, 898)),
    Edge("sync_to_safety", "sync", "safety", "inputs_valid · controls · safety_ok · gate_ok", "blue", exit=(1, 0.25), enter=(0.15, 1), points=((750, 678), (1253, 678)), label_at=(1054, 658)),
    Edge("rst_fanout", "reset", "sync", "rst_n / clock", "slate", exit=(0.5, 0), enter=(0.5, 1), dash=True, label_at=(766, 885)),
    Edge("gpio_to_mask", "safe_gpio", "mask", "raw async guard inputs (independent of synced FSM)", "red", exit=(1, 0.7), enter=(0.53, 1), points=((765, 945), (2068, 945), (2068, 652)), dash=True, label_at=(1330, 968)),
    Edge("safety_to_mask", "safety", "mask", "motor_enable", "amber", exit=(1, 0.80), enter=(0.11, 1), points=((1520, 649), (1970, 649)), dash=True, label_at=(1797, 637)),
    Edge("safety_to_outputs", "safety", "safety_port", "recovery_ack · gate_clear · state · fault", "amber", exit=(0.9, 1), enter=(0.43, 0), points=((1469, 662), (2046, 662)), label_at=(1771, 682)),
    Edge("safetyports_out", "safety_port", "safetyout", "permit / ack / clear / diagnostics", "amber", label_at=(2220, 716)),
    Edge("encoder_to_rtl", "encoderin", "encoder", "left_out / right_out", "teal", label_at=(337, 1162)),
    Edge("encoder_to_bus", "encoder", "snapbus", "snapshot fields", "teal", label_at=(760, 1162)),
    Edge("bus_to_serializer", "snapbus", "frame_tx", "snapshot_valid + data", "teal", label_at=(1207, 1159)),
    Edge("serializer_uart", "frame_tx", "uart_tx", "byte_valid/data/last + ready", "violet", label_at=(1593, 1159)),
    Edge("tx_to_output", "uart_tx", "txout", "tx serial 115200", "violet", label_at=(2112, 1159)),
    Edge("status_meta", "safety", "frame_tx", "active_session · safety_state · fault", "violet", exit=(0.80, 1), enter=(0.73, 0), points=((1439, 1065), (1455, 1065)), label_at=(1472, 1045)),
    Edge("status_ack", "uart_tx", "safety", "status_sent / status_session / status_state (fpga_link)", "violet", exit=(0.2, 0), enter=(1, 0.94), points=((1710, 1087), (1547, 1087), (1547, 608)), dash=True, label_at=(1789, 1106)),
]


def shape_style(node: Node) -> str:
    stroke = COLORS[node.accent]
    bg = "#17263B" if not node.external else "#142130"
    return (
        "rounded=1;arcSize=12;whiteSpace=wrap;html=1;align=center;"
        "verticalAlign=middle;spacing=9;fontFamily=Arial;fontSize=16;"
        f"fontColor={COLORS['text']};fillColor={bg};strokeColor={stroke};"
        "strokeWidth=2;shadow=0;" + ("dashed=1;dashPattern=7 5;" if node.external else "")
    )


def label_html(node: Node) -> str:
    content = f'<b style="font-size:19px">{escape(node.title)}</b>'
    for line in node.lines:
        content += f'<br/><font color="{COLORS["muted"]}" style="font-size:13px">{escape(line)}</font>'
    return content


def main():
    nmap = {n.key: n for n in NODES}
    assert len(nmap) == len(NODES)
    assert len({e.key for e in EDGES}) == len(EDGES)
    assert all(e.src in nmap and e.dst in nmap for e in EDGES)
    # This script only owns its REVIEW artifacts; it never writes into V4.

    mxfile = ET.Element("mxfile", host="app.diagrams.net", modified="2026-11-02T00:00:00Z", agent="AW-Car RTL v2 review generator", version="24.7.17", type="device")
    diagram = ET.SubElement(mxfile, "diagram", name="FPGA RTL v2 - REVIEW (independent)", id="fpga-v2-review")
    model = ET.SubElement(diagram, "mxGraphModel", dx=str(WIDTH), dy=str(HEIGHT), grid="1", gridSize="10", guides="1", tooltips="1", connect="1", arrows="1", fold="1", page="1", pageScale="1", pageWidth=str(WIDTH), pageHeight=str(HEIGHT), math="0", shadow="0", background=COLORS["background"])
    graph = ET.SubElement(model, "root")
    ET.SubElement(graph, "mxCell", id="0")
    ET.SubElement(graph, "mxCell", id="1", parent="0")

    def rect(key, x, y, w, h, color=COLORS["panel"], stroke=COLORS["border"], rounded=1):
        cell=ET.SubElement(graph,"mxCell",id=key,parent="1",vertex="1",value="",style=f"rounded={rounded};arcSize=10;whiteSpace=wrap;html=1;fillColor={color};strokeColor={stroke};strokeWidth=1;movable=0;connectable=0;")
        ET.SubElement(cell,"mxGeometry",x=str(x),y=str(y),width=str(w),height=str(h),**{"as":"geometry"})

    def text(key, x, y, w, h, content, size=17, color="text", bold=False):
        cell=ET.SubElement(graph,"mxCell",id=key,parent="1",vertex="1",value=escape(content),style=f"text;html=1;whiteSpace=wrap;fillColor=none;strokeColor=none;align=left;verticalAlign=middle;spacing=0;fontFamily=Arial;fontSize={size};fontColor={COLORS[color]};fontStyle={1 if bold else 0};")
        ET.SubElement(cell,"mxGeometry",x=str(x),y=str(y),width=str(w),height=str(h),**{"as":"geometry"})

    for id_, y, h in [("lane_cmd",163,430),("lane_safe",653,405),("lane_fb",1110,332)]:
        rect(id_, 32, y, 2575, h)
    text("title", 52, 31, 2180, 48, "AW-CAR  |  FPGA RTL — SIGNAL & MODULE BLOCK DIAGRAM", 30, bold=True)
    text("subtitle",52,85,2050,42,"Top: aw_car_top.sv  |  Core: drive_core.sv  |  27 MHz  |  UART v2 115200 8N1  |  Encoder: 1 OUT / side",16,"muted")
    text("io_headers",56,144,2500,24,"INPUT  (external, left)                                      FPGA RTL PROCESSING  (clocked, central)                                                               OUTPUT  (right)",15,"muted",True)
    for k,y,label in [("lc",177,"01  CONTROL PATH  •  MOTION CMD → FPGA MOTOR OUTPUT"),("ls",667,"02  CLOCK / RESET + SAFETY CONTROL  •  INDEPENDENT GPIO AUTHORITY"),("lf",1124,"03  FEEDBACK PATH  •  ENCODER SNAPSHOT → STATUS UART")]:
        text(k,52,y,2510,30,label,17,"muted",True)
    for n in NODES:
        cell=ET.SubElement(graph,"mxCell",id=n.key,parent="1",vertex="1",value=label_html(n),style=shape_style(n))
        ET.SubElement(cell,"mxGeometry",x=str(n.x),y=str(n.y),width=str(n.w),height=str(n.h),**{"as":"geometry"})
    for e in EDGES:
        style=("edgeStyle=orthogonalEdgeStyle;orthogonalLoop=1;rounded=1;html=1;jettySize=auto;endArrow=blockThin;endFill=1;"
            f"strokeColor={COLORS[e.accent]};strokeWidth=2.6;fontFamily=Arial;fontSize=13;fontColor={COLORS['text']};"
            f"labelBackgroundColor={COLORS['background']};"
            f"exitX={e.exit[0]};exitY={e.exit[1]};exitDx=0;exitDy=0;entryX={e.enter[0]};entryY={e.enter[1]};entryDx=0;entryDy=0;")
        if e.dash:style+="dashed=1;dashPattern=6 5;"
        # Labeled arrows plus full waypoint geometry remain editable in draw.io.
        cell=ET.SubElement(graph,"mxCell",id=e.key,parent="1",edge="1",source=e.src,target=e.dst,value=escape(e.label),style=style)
        g=ET.SubElement(cell,"mxGeometry",relative="1",**{"as":"geometry"})
        if e.points:
            pts=ET.SubElement(g,"Array",**{"as":"points"})
            for x,y in e.points:ET.SubElement(pts,"mxPoint",x=str(x),y=str(y))
    text("clk_global", 755, 954, 1040, 36, "clk[27 MHz], rst_n are shared by all synchronous RTL blocks (not separate generated clocks).",15,"slate")
    text("tx_note",54,1476,2480,27,"RTL scope: PWM/DIR are logical outputs; IN1/IN2 mapping, default-OFF gate, power driver, board POR, pinout/STA are OUTSIDE this RTL.",15,"amber")
    text("v2_note",54,1508,2480,30,"Protocol v2: STATUS 34-byte payload / 47-byte frame. Encoder single-OUT does NOT measure actual direction. Recovery-timeout fix is in RTL; physical validation is pending.",14,"muted")
    OUTPUT.write_bytes(ET.tostring(mxfile,encoding="utf-8",xml_declaration=True))
    create_preview()
    # Round-trip validation and no 'TV1/TV2/TV3' ownership labels.
    parsed=ET.parse(OUTPUT).getroot()
    cells=parsed.findall("./diagram/mxGraphModel/root/mxCell")
    assert len(parsed.findall("diagram"))==1
    assert len([c for c in cells if c.get("vertex")=="1"])>=len(NODES)
    assert len([c for c in cells if c.get("edge")=="1"])==len(EDGES)
    assert all("TV1" not in (c.get("value") or "") and "TV2" not in (c.get("value") or "") and "TV3" not in (c.get("value") or "") for c in cells)
    print(f"DRAWIO: {OUTPUT} ({OUTPUT.stat().st_size} bytes)")
    print(f"PREVIEW: {PREVIEW} ({PREVIEW.stat().st_size} bytes)")
    print(f"CELLS: {len(NODES)} nodes, {len(EDGES)} arrows")


def create_preview():
    """Render a review PNG using the SAME node coordinates; draw.io XML is authoritative."""
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        print("Pillow absent; editable Draw.io is still generated")
        return
    image = Image.new("RGB", (WIDTH, HEIGHT), COLORS["background"])
    d = ImageDraw.Draw(image)
    from pathlib import Path as _P
    fontpath = _P(r"C:\Windows\Fonts\arial.ttf")
    boldpath = _P(r"C:\Windows\Fonts\arialbd.ttf")
    def font(n,bold=False):
        file=boldpath if bold else fontpath
        return ImageFont.truetype(str(file),n) if file.exists() else ImageFont.load_default()
    small, mid, big = font(15), font(17), font(22,True)
    for y,h in [(163,430),(653,405),(1110,332)]:
        d.rounded_rectangle((32,y,2607,y+h),radius=15,fill=COLORS["panel"],outline=COLORS["border"],width=2)
    d.text((52,31),"AW-CAR | FPGA RTL — SIGNAL & MODULE BLOCK DIAGRAM",font=font(31,True),fill=COLORS["text"])
    d.text((52,88),"Top: aw_car_top.sv  |  Core: drive_core.sv  |  Clock 27 MHz  |  UART v2 115200 8N1  |  1 OUT / encoder",font=mid,fill=COLORS["muted"])
    d.text((52,141),"INPUT (external, left)                         FPGA RTL PROCESSING (central)                                                   OUTPUT (right)",font=font(16,True),fill=COLORS["muted"])
    for y,txt in [(177,"01  CONTROL PATH · MOTION CMD → FPGA MOTOR OUTPUT"),(667,"02  CLOCK / RESET + SAFETY CONTROL · INDEPENDENT GPIO AUTHORITY"),(1124,"03  FEEDBACK PATH · ENCODER SNAPSHOT → STATUS UART")]:
        d.text((52,y),txt,font=font(18,True),fill=COLORS["muted"])
    pos={n.key:n for n in NODES}
    # Arrows behind nodes. Manual waypoint geometry shown consistently with Draw.io.
    for e in EDGES:
        a,b=pos[e.src],pos[e.dst]
        pts=[(int(a.x+e.exit[0]*a.w),int(a.y+e.exit[1]*a.h)),*e.points,(int(b.x+e.enter[0]*b.w),int(b.y+e.enter[1]*b.h))]
        c=COLORS[e.accent]
        if e.dash:
            for p,q in zip(pts,pts[1:]):
                length=max(abs(q[0]-p[0]),abs(q[1]-p[1]));segments=max(1,int(length/16))
                for i in range(segments):
                    if i%2==0:
                        u=i/segments;v=(i+1)/segments
                        d.line((p[0]+(q[0]-p[0])*u,p[1]+(q[1]-p[1])*u,p[0]+(q[0]-p[0])*v,p[1]+(q[1]-p[1])*v),fill=c,width=2)
        else:d.line(pts,fill=c,width=3,joint="curve")
        p,q=pts[-2],pts[-1];ang=atan2(q[1]-p[1],q[0]-p[0]);tip=q
        wings=[(tip[0]-13*cos(ang)+6*sin(ang),tip[1]-13*sin(ang)-6*cos(ang)),(tip[0]-13*cos(ang)-6*sin(ang),tip[1]-13*sin(ang)+6*cos(ang))]
        d.polygon([tip,*wings],fill=c)
        if e.label_at:
            x,y=e.label_at;box=d.textbbox((0,0),e.label,font=small);w=box[2]-box[0]
            d.rounded_rectangle((x-w/2-5,y-4,x+w/2+5,y+21),radius=4,fill=COLORS["background"])
            d.text((x-w/2,y),e.label,font=small,fill=c)
    for n in NODES:
        border=COLORS[n.accent]
        fill="#15263C" if not n.external else "#142130"
        d.rounded_rectangle((n.x,n.y,n.x+n.w,n.y+n.h),radius=15,fill=fill,outline=border,width=3)
        heading=big
        while d.textbbox((0,0),n.title,font=heading)[2] > n.w-22 and heading.size>14:
            heading=font(heading.size-1,True)
        bbox=d.textbbox((0,0),n.title,font=heading)
        tx=n.x+(n.w-(bbox[2]-bbox[0]))/2
        d.text((tx,n.y+16),n.title,font=heading,fill=COLORS["text"])
        offset=55
        for line in n.lines:
            f=small
            while d.textbbox((0,0),line,font=f)[2]>n.w-18 and f.size>11:
                f=font(f.size-1)
            bb=d.textbbox((0,0),line,font=f)
            d.text((n.x+(n.w-(bb[2]-bb[0]))/2,n.y+offset),line,font=f,fill=COLORS["muted"])
            offset+=21
    d.text((755,967),"clk / rst_n to all synchronous RTL blocks",font=mid,fill=COLORS["slate"])
    d.text((54,1475),"RTL: DRV8833 IN1/IN2 adapter is inside drive_core; independent hardware gate and board pin constraints remain external.",font=font(16,True),fill=COLORS["amber"])
    d.text((54,1506),"v2 STATUS = 34 B payload / 47 B frame · single-OUT encoder has no direction · Recovery-timeout fix tested in RTL; physical validation pending",font=mid,fill=COLORS["muted"])
    image.save(PREVIEW,optimize=True)


if __name__ == "__main__":
    main()
