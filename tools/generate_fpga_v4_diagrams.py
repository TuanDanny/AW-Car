#!/usr/bin/env python3
"""AW Car V4 editable draw.io: preserve V3 pages and append system + command paths.
Source truth: docs/fpga-drive-plan.md, firmware/shared/fpga-{protocol,safety}.md,
firmware/{brain,motion}/README.md, fpga/rtl/drive_core.sv.
No modifications to V3.
"""
from pathlib import Path
from copy import deepcopy
import hashlib
from html import escape
import xml.etree.ElementTree as ET

BASE = Path(__file__).resolve().parents[1]
V3 = BASE / "docs" / "AW_Car_FPGA_Modular_IO_v3.drawio"
V4 = BASE / "docs" / "AW_Car_FPGA_Modular_IO_v4.drawio"
C = {
    "ink": "#14253B", "muted": "#64748B", "line": "#CBD5E1",
    "violet": "#7C3AED", "vbg": "#F3EDFF",
    "blue": "#2563EB", "bbg": "#EAF2FF",
    "teal": "#07866B", "tbg": "#E4F7F0",
    "orange": "#B77713", "obg": "#FFF3DE",
    "slate": "#475569", "sbg": "#F4F7FB",
}
def rich(title, sub="", lines=()):
    content = '<b style="font-size:16px">' + escape(title) + '</b>'
    if sub: content += '<br/><font color="#52647A" style="font-size:12px">' + escape(sub) + '</font>'
    if lines:
        content += '<br/><font color="#233850" style="font-size:13px">' + '<br/>'.join(escape(x) for x in lines) + '</font>'
    return content

class Page:
    def __init__(self, title, pid, width=1730, height=1250):
        self.diagram=ET.Element("diagram",name=title,id=pid)
        self.model=ET.SubElement(self.diagram,"mxGraphModel",{
            "dx":str(width),"dy":str(height),"grid":"1","gridSize":"10",
            "guides":"1","tooltips":"1","connect":"1","arrows":"1","fold":"1",
            "page":"1","pageScale":"1","pageWidth":str(width),
            "pageHeight":str(height),"math":"0","shadow":"0","background":"#FFFFFF"
        })
        self.root=ET.SubElement(self.model,"root")
        ET.SubElement(self.root,"mxCell",id="0")
        ET.SubElement(self.root,"mxCell",id="1",parent="0")
        self.pageid=pid
    def node(self,key,x,y,w,h,title,sub="",lines=(),*,color="slate",dashed=False,fontsize=15,parent="1"):
        style=("rounded=1;arcSize=12;whiteSpace=wrap;html=1;align=center;"
               "verticalAlign=middle;spacing=10;fontFamily=Arial;"
               f"fontSize={fontsize};fontColor={C['ink']};"
               f"fillColor={C.get(color[0]+'bg',C['sbg'])};"
               f"strokeColor={C.get(color,C['slate'])};strokeWidth=2;")
        # Explicit mapping ensures a consistent color palette across pages.
        cmap={"violet":("vbg","violet"),"blue":("bbg","blue"),
              "teal":("tbg","teal"),"orange":("obg","orange"),
              "slate":("sbg","slate")}
        bg,fg=cmap[color]
        style=style.replace(f"fillColor={C.get(color[0]+'bg',C['sbg'])}",f"fillColor={C[bg]}")
        if dashed: style+="dashed=1;dashPattern=6 5;"
        el=ET.SubElement(self.root,"mxCell",id=key,parent=parent,vertex="1",
                         value=rich(title,sub,lines),style=style)
        ET.SubElement(el,"mxGeometry",{"x":str(x),"y":str(y),
             "width":str(w),"height":str(h),"as":"geometry"})
    def text(self,key,x,y,w,h,txt,*,size=17,color="ink",bold=False,align="left"):
        style=("text;html=1;whiteSpace=wrap;fillColor=none;strokeColor=none;"
               f"fontColor={C[color]};fontSize={size};fontFamily=Arial;"
               f"fontStyle={int(bold)};align={align};verticalAlign=middle;")
        el=ET.SubElement(self.root,"mxCell",id=key,vertex="1",parent="1",
                         value=escape(txt),style=style)
        ET.SubElement(el,"mxGeometry",{"x":str(x),"y":str(y),
                        "width":str(w),"height":str(h),"as":"geometry"})
    def edge(self,key,source,target,caption="",*,color="blue",ex=(1,0.5),en=(0,0.5),
             waypoints=(),dashed=False,bidirectional=False):
        style=("edgeStyle=orthogonalEdgeStyle;rounded=1;orthogonalLoop=1;"
            "jettySize=auto;html=1;endArrow=blockThin;endFill=1;"
            f"strokeColor={C[color]};strokeWidth=2.4;fontFamily=Arial;"
            "fontSize=12;fontColor=#22364D;labelBackgroundColor=#FFFFFF;"
            f"exitX={ex[0]};exitY={ex[1]};exitDx=0;exitDy=0;"
            f"entryX={en[0]};entryY={en[1]};entryDx=0;entryDy=0;")
        if dashed:style+="dashed=1;dashPattern=5 4;"
        if bidirectional:style+="startArrow=blockThin;startFill=1;"
        el=ET.SubElement(self.root,"mxCell",{"id":key,"parent":"1","edge":"1",
               "source":source,"target":target,"value":escape(caption),"style":style})
        geom=ET.SubElement(el,"mxGeometry",{"relative":"1","as":"geometry"})
        if waypoints:
            a=ET.SubElement(geom,"Array",{"as":"points"})
            for x,y in waypoints:ET.SubElement(a,"mxPoint",x=str(x),y=str(y))
    def headline(self,title,subtitle,width=1730):
        self.text("headline",44,25,width-88,51,title,size=29,color="ink",bold=True)
        self.text("subhead",44,91,width-88,35,subtitle,size=14,color="muted")
    def note(self,text,*,x=44,y=1134,w=1640,h=76):
        el=ET.SubElement(self.root,"mxCell",{
            "id":"scope_note","parent":"1","vertex":"1",
            "value":escape(text),
            "style":("rounded=1;arcSize=8;html=1;whiteSpace=wrap;align=center;"
                     "verticalAlign=middle;spacing=10;fillColor=#FFF3DE;"
                     "strokeColor=#D7AD60;fontFamily=Arial;fontSize=14;"
                     "fontColor=#70480F;strokeWidth=1.5;")
        })
        ET.SubElement(el,"mxGeometry",{
            "x":str(x),"y":str(y),"width":str(w),
            "height":str(h),"as":"geometry"
        })

def system_diagram():
    p=Page("04 - TOAN HE THONG AW CAR","v4-system",2390,1290)
    p.headline("V4  /  SƠ ĐỒ HỆ THỐNG AW CAR",
       "Từ người điều khiển đến 4 motor TT; dữ liệu đi qua Brain → Motion → FPGA, có encoder và gate an toàn phản hồi",2390)
    # Main path at y=360: two input sources merge only into Brain.
    p.node("mic",50,248,252,124,"Giọng nói", "Người → INMP441",["1 mic, Xiaozhi"],color="violet",dashed=True)
    p.node("web",50,496,252,125,"Thủ công / Web", "Dashboard → Wi-Fi",["Lệnh + dead-man/lease"],color="violet",dashed=True)
    p.node("brain",384,339,310,194,"ESP32-S3 Brain", "Xiaozhi + Web + OLED/Loa",["Hiểu/lọc yêu cầu chuyển động","Gửi UART Brain → Motion"],color="blue")
    p.node("motion",800,339,322,194,"ESP32-S3 Motion", "Bộ điều khiển & Safety",["Lease + cảm biến + PID trái/phải","UART riêng: lệnh duty/dir","GPIO motion_permit"],color="blue")
    p.node("fpga",1230,330,337,212,"FPGA Tang Nano 9K", "drive_core.sv • RTL hiện có",["Link (CRC/session) + Safety FSM","PWM 20kHz / encoder A/B","Watchdog 50ms / STATUS"],color="teal")
    p.node("adapter",1662,351,257,171,"Adapter logic", "Ngoài FPGA, chưa làm",["PWM/DIR → IN1/IN2","Gate độc lập ở nhánh dưới"],color="orange",dashed=True)
    p.node("driver",2017,350,319,173,"2 × DRV8833", "Driver công suất dự kiến",["4 cầu H → 4 motor TT","2 bánh trái / 2 bánh phải"],color="orange",dashed=True)
    # Additional hardware/subsystems below main path, avoid edge crossings.
    p.node("audio",392,797,295,129,"OLED + loa", "OLED I²C / MAX98357A",["Phản hồi giao tiếp/giọng nói"],color="violet",dashed=True)
    p.node("imu",817,782,289,146,"Cảm biến Motion", "MPU6050 & safety sensors",["Kiểm tra nghiêng / vật cản","Nguồn / kẹt (theo BOM)"],color="blue",dashed=True)
    p.node("fpga_enc",1242,789,308,160,"2 Encoder A/B", "Phản hồi bánh đại diện",["left_ab[1:0], right_ab[1:0]","Dự kiến thay V2 1-OUT"],color="teal",dashed=True)
    p.node("gate",1668,799,245,155,"Mạch khóa cứng", "Ngắt driver độc lập",["Motion permit + FPGA permit","safety_ok + gate_fault_n","Fault latch / default OFF"],color="orange",dashed=True)
    p.node("estop",1668,1085,244,99,"E-stop / Nguồn", "Tác động trực tiếp lên gate",[],color="orange",dashed=True)
    p.edge("v_mic","mic","brain","âm thanh",color="violet",ex=(1,.60),en=(0,.30))
    p.edge("v_web","web","brain","yêu cầu",color="violet",ex=(1,.34),en=(0,.78))
    p.edge("v_brain_motion","brain","motion","lệnh → / phản hồi ←",ex=(1,.50),en=(0,.50),color="blue",bidirectional=True)
    p.edge("v_motion_fpga","motion","fpga","UART CMD → / STATUS ←",ex=(1,.48),en=(0,.48),color="blue",bidirectional=True)
    p.edge("v_fpga_adapter","fpga","adapter","PWM / DIR + permit",ex=(1,.50),en=(0,.50),color="teal")
    p.edge("v_adapter_driver","adapter","driver","IN1/IN2",ex=(1,.43),en=(0,.45),color="orange")
    p.edge("v_brain_audio","brain","audio","I²C / I²S",ex=(.5,1),en=(.5,0),color="violet")
    p.edge("v_motion_sensors","imu","motion","IMU / safety",ex=(.5,0),en=(.50,1),color="blue")
    # Note: exact physical wiring is still schematic. Instead of a fictitious motor→sensor
    # connection, encoder is explicitly a measurement on representative wheels.
    p.edge("v_encoder_fpga","fpga_enc","fpga","A/B x2",ex=(.5,0),en=(.5,1),color="teal")
    p.edge("v_estop_gate","estop","gate","cắt độc lập",ex=(.5,0),en=(.5,1),color="orange")
    p.edge("v_gate_driver","gate","driver","driver inhibit",ex=(1,.25),en=(.48,1),
           waypoints=[(1988,850),(1988,614),(2168,614)],color="orange")
    # Independent permits are distinct from UART. Use two outer corridors.
    p.edge("v_motion_gate","motion","gate","Motion permit",color="blue",
           ex=(0,.62),en=(0,.65),waypoints=[(751,457),(751,1051),(1625,1051),(1625,900)],dashed=True)
    p.edge("v_fpga_gate","fpga","gate","FPGA permit",color="teal",
           ex=(.85,1),en=(.72,0),waypoints=[(1530,730),(1845,730)],dashed=True)
    p.note("TRẠNG THÁI: RTL FPGA + protocol v1 đã có kiểm thử. Tích hợp Xiaozhi → Brain → Motion, Web, driver adapter, gate/E-stop và cảm biến V2 vẫn là THIẾT KẾ DỰ KIẾN.",
           x=54,y=1197,w=2280,h=62)
    return p

def command_flow(name,manual=False):
    p=Page("06 - THU CONG WEB" if manual else "05 - GIONG NOI XIAOZHI",
           "v4-manual" if manual else "v4-xiaozhi",1730,1350)
    p.headline(
        "V4  /  FLOW ĐIỀU KHIỂN THỦ CÔNG" if manual else "V4  /  FLOW LỆNH GIỌNG NÓI XIAOZHI",
        "Thứ tự dữ liệu đi qua các bộ xử lý, khối RTL và đường phản hồi; dòng 1 →, dòng 2 ←, dòng 3 →."
    )
    p.text("phase1",58,170,1600,30,
           "GIAI ĐOẠN 1  ·  NHẬP LỆNH / KIỂM TRA Ý ĐỊNH  (dự kiến firmware)",
           size=18,color="blue",bold=True)
    p.text("phase2",58,507,1600,30,
           "GIAI ĐOẠN 2  ·  CẤP QUYỀN / ĐIỀU KHIỂN MOTOR  (RTL FPGA đã có)",
           size=18,color="teal",bold=True)
    p.text("phase3",58,844,1600,30,
           "GIAI ĐOẠN 3  ·  ENCODER / TRẢ PHẢN HỒI / PID (RTL có, firmware dự kiến)",
           size=18,color="violet",bold=True)
    x=[55,385,715,1045,1375];w=270; y1=228; y2=565; y3=900;h=177
    # Branch-specific first row
    if manual:
        first=[
            ("01 · Người dùng","Web Dashboard",["Nhấn Tiến / Rẽ / Dừng","Gửi qua Wi-Fi"],"violet"),
            ("02 · ESP32 Brain","Nhận lệnh Web",["Chỉ một phiên điều khiển","Không phát PWM trực tiếp"],"blue"),
            ("03 · Brain kiểm tra","Dead-man + lease",["Giới hạn tốc độ/tuổi lệnh","Mất Web → hết lease"],"blue"),
            ("04 · UART Brain→Motion","Yêu cầu chuyển động",["Setpoint thẳng / quay","Wire format chưa triển khai"],"blue"),
            ("05 · ESP32 Motion","Safety + PID",["Kiểm lease / MPU6050","Tạo duty trái/phải mới"],"blue"),
        ]
    else:
        first=[
            ("01 · Người nói","INMP441",["Thu âm lệnh","Ví dụ: tiến / dừng / rẽ"],"violet"),
            ("02 · ESP32 Brain","Xiaozhi",["Nhận hiểu lệnh giọng nói","Hồi đáp qua loa/OLED"],"blue"),
            ("03 · Brain kiểm tra","Ý định → lệnh an toàn",["Lọc/giới hạn + thời hạn","Không cho AI tạo PWM"],"blue"),
            ("04 · UART Brain→Motion","Yêu cầu chuyển động",["Setpoint thẳng / quay","Wire format chưa triển khai"],"blue"),
            ("05 · ESP32 Motion","Safety + PID",["Kiểm lease / MPU6050","Tạo duty trái/phải mới"],"blue"),
        ]
    for i,(ttl,sub,lines,col) in enumerate(first):
        p.node("r1_"+str(i),x[i],y1,w,h,ttl,sub,lines,color=col)
    second=[
        ("10 · Công suất","2 DRV8833 + 4 motor",["PWM/Dir → adapter/gate","Driver cấp điện motor"],"orange"),
        ("09 · TV3 PWM","motor_pwm_pair",["pwm_pair: PWM 20 kHz","Interlock đổi chiều"],"teal"),
        ("08 · TV1 Safety FSM","safety_fsm",["ARMED + permit mới cho chạy","Watchdog CMD mới 50 ms"],"blue"),
        ("07 · TV2 Link","fpga_link / guard",["UART RX → CRC16 → session","seq mới + duty hợp lệ"],"violet"),
        ("06 · Motion ARM/UART","Recovery và handshake",["req/ack → HELLO → ARM_ZERO","STATUS ARM_PENDING + ACK","permit ↑ → CMD mới"],"blue"),
    ]
    for i,(ttl,sub,lines,col) in enumerate(second):
        p.node("r2_"+str(i),x[i],y2,w,h,ttl,sub,lines,color=col)
    third=[
        ("11 · Đọc encoder","Encoder A/B",["Phản hồi 2 bánh đại diện","Cảm biến V2 chưa hỗ trợ"],"teal"),
        ("12 · TV3 Encoder","encoder_pair",["quadrature_decoder X4","Snapshot đồng thời 10ms"],"teal"),
        ("13 · TV2 STATUS","frame_tx + uart_tx",["Count / timestamp / seq","safety_state / fault + CRC"],"violet"),
        ("14 · ESP32 Motion","Kiểm STATUS + PID",["CRC / age / seq mới","Cập nhật PID; CMD mới"],"blue"),
        ("15 · Người dùng","Phản hồi giao diện" if manual else "Loa / OLED",[
            "Dashboard: vận tốc, lỗi" if manual else "Xiaozhi nói trạng thái",
            "Không trực tiếp điều khiển motor"],"violet"),
    ]
    for i,(ttl,sub,lines,col) in enumerate(third):
        p.node("r3_"+str(i),x[i],y3,w,h,ttl,sub,lines,color=col)
    # Horizontal arrows from row1 LTR, row2 RTL, row3 LTR. All no crossings.
    for i in range(4):
        p.edge("f1_"+str(i),"r1_"+str(i),"r1_"+str(i+1),"",color="blue")
        p.edge("f2_"+str(i),"r2_"+str(i+1),"r2_"+str(i),"",color="teal",ex=(0,.5),en=(1,.5))
        p.edge("f3_"+str(i),"r3_"+str(i),"r3_"+str(i+1),"",color="violet")
    p.edge("turn1","r1_4","r2_4","ARM/CMD",ex=(.5,1),en=(.5,0),color="blue")
    p.edge("turn2","r2_0","r3_0","đo bánh",ex=(.5,1),en=(.5,0),color="teal")
    p.text("feedback_loop",58,1095,1600,36,
           "VÒNG LẶP: 14 → 06  |  Motion tính PID và phát CMD MỚI ở chu kỳ tiếp theo (mục tiêu 100 Hz); không phát lại duty cache.",
           size=14,color="blue",bold=True)
    p.note(
        "AN TOÀN: CMD phải đúng CRC/phiên/sequence + Safety ARMED + Motion permit + gate ngoài. Timeout 50ms → FAULT/motor OFF; mất lease Brain/Motion hoặc E-stop → khóa driver độc lập. STATUS cũ không cứu watchdog.",
        x=55,y=1149,w=1590,h=111
    )
    p.text("future_note",60,1271,1590,31,
        "Chú thích: phần Brain→Motion và Web/Xiaozhi điều khiển xe là kiến trúc dự kiến; FPGA UART/Safety/PWM/Encoder là RTL đã có.",
        size=14,color="muted")
    return p

def main():
    source_bytes=V3.read_bytes()
    source_hash=hashlib.sha256(source_bytes).hexdigest()
    source=ET.fromstring(source_bytes)
    pages=source.findall("diagram")
    assert len(pages)==3, "Need original V3 exactly 3 pages"
    result=ET.Element("mxfile",{
        "host":"app.diagrams.net","version":"24.7.17","type":"device",
        "agent":"drawio-skill 3.4.3, AW-Car preserved V3 and added V4 flow"
    })
    for idx,p in enumerate(pages):
        clone=deepcopy(p)
        clone.set("name","[V3] "+(p.get("name") or str(idx+1)))
        result.append(clone)
    for page in (system_diagram(), command_flow("Xiaozhi"), command_flow("Web",manual=True)):
        result.append(page.diagram)
    result_str=ET.tostring(result,encoding="utf-8",xml_declaration=True)
    # Verify V3 three diagram models were not changed. Titles in tabs may change.
    roundtrip=ET.fromstring(result_str)
    for a,b in zip(pages,roundtrip.findall("diagram")[:3]):
        assert ET.tostring(a.find("mxGraphModel"))==ET.tostring(b.find("mxGraphModel"))
    V4.write_bytes(result_str)
    assert hashlib.sha256(V3.read_bytes()).hexdigest()==source_hash
    print("V3 intact sha256:",source_hash)
    print("Output:",V4,"bytes:",V4.stat().st_size)
    for page in result.findall("diagram"):
        cs=page.findall("./mxGraphModel/root/mxCell")
        print("  ",page.get("name"),"vertex:",sum(x.get("vertex")=="1" for x in cs),
              "edge:",sum(x.get("edge")=="1" for x in cs))

if __name__=="__main__":
    main()
