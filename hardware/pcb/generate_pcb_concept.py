"""Editable, non-fabrication AW-Car PCB planning diagrams, sourced from CAD layout.

Generates vector SVG and Pillow PNG with no KiCad dependencies. All routing
paths are *corridors*, not circuit nets, pads, traces, current-rated copper,
or verified electrical connectivity.
"""
from __future__ import annotations

import html
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CAD = ROOT.parent / 'cad'
LAYOUT = json.loads((CAD/'layout.json').read_text(encoding='utf8'))

COLORS = {
    'bg': '#F5F8FC', 'ink': '#19344D', 'muted': '#658098',
    'navy': '#183350', 'line': '#CCD9E4', 'white': '#FFFFFF',
    'acrylic': '#DDEFFA', 'board': '#1A8D76', 'brain': '#3A7ECC',
    'motion': '#20A99B', 'fpga': '#7456B8', 'driver': '#D65B61',
    'safety': '#D85D51', 'motor': '#E5AA36', 'wheel': '#343E4C',
    'battery': '#437DD6', 'power': '#E6A13F', 'signal': '#3697CF',
    'gnd': '#586472', 'green': '#258D73'
}


class Canvas:
    def __init__(self, width=1600,height=1000):
        self.w,self.h=width,height
        self.parts=[];self.png_ops=[]

    def shape(self,typ,*args,**kwargs):
        self.png_ops.append((typ,args,kwargs))

    def rect(self,x,y,w,h,fill,stroke='none',r=0,sw=1,opacity=1):
        self.parts.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{r}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}" opacity="{opacity}"/>')
        self.shape('rect',x,y,w,h,fill,stroke,r,sw,opacity)

    def line(self,x1,y1,x2,y2,color,width=2,dashed=False):
        dash=' stroke-dasharray="9 7"' if dashed else ''
        self.parts.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{color}" stroke-width="{width}" stroke-linecap="round"{dash}/>')
        self.shape('line',x1,y1,x2,y2,color,width,dashed)

    def poly(self,points,fill,stroke='none',sw=1,opacity=1):
        seq=' '.join(f'{x:.1f},{y:.1f}' for x,y in points)
        self.parts.append(f'<polygon points="{seq}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}" opacity="{opacity}"/>')
        self.shape('polygon',points,fill,stroke,sw,opacity)

    def ellipse(self,x,y,rx,ry,fill,stroke='none',sw=1,opacity=1):
        self.parts.append(f'<ellipse cx="{x:.1f}" cy="{y:.1f}" rx="{rx:.1f}" ry="{ry:.1f}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}" opacity="{opacity}"/>')
        self.shape('ellipse',x,y,rx,ry,fill,stroke,sw,opacity)

    def text(self,x,y,value,size=20,color=None,weight=400,anchor='start'):
        color=color or COLORS['ink']
        self.parts.append(f'<text x="{x:.1f}" y="{y:.1f}" fill="{color}" font-size="{size}" font-weight="{weight}" text-anchor="{anchor}" font-family="Segoe UI, Arial, sans-serif">{html.escape(str(value))}</text>')
        self.shape('text',x,y,str(value),size,color,weight,anchor)

    def save(self,path):
        svg=f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w}" height="{self.h}" viewBox="0 0 {self.w} {self.h}">\n'+''.join(self.parts)+'</svg>'
        path.write_text(svg,encoding='utf8')
        self.save_png(path.with_suffix('.png'))

    def save_png(self,path):
        try:
            from PIL import Image,ImageDraw,ImageFont
        except ImportError:
            print('Pillow absent; PNG skipped')
            return
        im=Image.new('RGBA',(self.w,self.h),'white')
        d=ImageDraw.Draw(im,'RGBA')
        def col(h,op=1):
            if h=='none':return None
            h=h.lstrip('#')
            return tuple(int(h[i:i+2],16) for i in (0,2,4))+(round(255*op),)
        def font(size,weight):
            path=('C:/Windows/Fonts/arialbd.ttf' if weight>=600 else 'C:/Windows/Fonts/arial.ttf')
            try:return ImageFont.truetype(path,int(size))
            except OSError:return ImageFont.load_default()
        for typ,args,_ in self.png_ops:
            if typ=='rect':
                x,y,w,h,fill,stroke,r,sw,op=args
                d.rounded_rectangle((x,y,x+w,y+h),radius=r,fill=col(fill,op),outline=col(stroke),width=int(sw))
            elif typ=='line':
                x1,y1,x2,y2,c,sw,dash=args
                if not dash:d.line((x1,y1,x2,y2),fill=col(c),width=int(sw))
                else:
                    length=math.hypot(x2-x1,y2-y1)
                    if length:
                        dx,dy=(x2-x1)/length,(y2-y1)/length
                        for i in range(0,int(length),16):
                            j=min(i+9,length)
                            d.line((x1+i*dx,y1+i*dy,x1+j*dx,y1+j*dy),fill=col(c),width=int(sw))
            elif typ=='polygon':
                ps,fill,stroke,sw,op=args
                d.polygon(ps,fill=col(fill,op))
                if stroke!='none':d.line(ps+[ps[0]],fill=col(stroke),width=int(sw),joint='curve')
            elif typ=='ellipse':
                x,y,rx,ry,fill,stroke,sw,op=args
                d.ellipse((x-rx,y-ry,x+rx,y+ry),fill=col(fill,op),outline=col(stroke),width=int(sw))
            elif typ=='text':
                x,y,s,size,color,weight,anchor=args
                ft=font(size,weight)
                if anchor!='start':
                    width=d.textbbox((0,0),s,font=ft)[2]
                    x-=(width/2 if anchor=='middle' else width)
                d.text((x,y-size*.88),s,font=ft,fill=col(color))
        im.convert('RGB').save(path)


def title(c,title,subtitle):
    c.rect(0,0,c.w,99,COLORS['navy'])
    c.text(45,45,title,31,'#FFFFFF',700)
    c.text(47,76,subtitle,15,'#BDD3E7')
    c.rect(34,c.h-53,c.w-68,39,'#FFF2DD',r=10)
    c.text(49,c.h-27,'CONCEPT ONLY  /  footprints, current rating, pinout, keep-outs and DRC not validated',16,'#935D2C',600)


def component_color(obj):
    mapping={'brain':'brain','motion':'motion','fpga':'fpga',
             'driver':'driver','screen':'signal','sensor':'motion',
             'speaker':'gnd','estop':'safety','power':'power','safety':'safety',
             'pcb':'board','pcb_power':'board'}
    return COLORS[mapping.get(obj['color'],'gnd')]


def car_transform(x,y):
    scale=2.45
    return 428-y*scale,477+x*scale


def car_panel(c):
    from importlib.util import module_from_spec,spec_from_file_location
    s=spec_from_file_location('awcar_cad',CAD/'generate_aw_car.py')
    mod=module_from_spec(s);s.loader.exec_module(mod)
    c.rect(30,116,810,795,'#FFFFFF',COLORS['line'],18)
    c.text(60,159,'A  /  TOP VIEW OF ACTUAL-STYLE 4WD CHASSIS',21,COLORS['ink'],700)
    c.text(60,186,'Front is UP  |  provisional 260 x 155 mm acrylic / 175 mm with tires',15,COLORS['muted'])
    outline=[car_transform(x,y) for x,y in mod.deck_outline(LAYOUT['top_deck'],LAYOUT['wheel'])]
    c.poly(outline,COLORS['acrylic'],'#90C5DC',3,0.75)
    for front,x in [('F',LAYOUT['wheel']['front_x']),('R',LAYOUT['wheel']['rear_x'])]:
        for side,y in [('L',LAYOUT['wheel']['left_y']),('R',LAYOUT['wheel']['right_y'])]:
            px,py=car_transform(x,y)
            c.rect(px-24.5,py-72,49,144,COLORS['wheel'],'#1B2936',14)
            c.rect(px-15,py-42,30,84,COLORS['motor'],r=7)
            c.text(px,py+5,front+side,18,'#182434',700,'middle')
    # Layout is a concept-only envelope, not a PCB outline to be milled.
    sorted_items=sorted(LAYOUT['components'],key=lambda o:0 if o['id']=='controller_carrier' else 1)
    for obj in sorted_items:
        if obj['zone'] not in ('upper',):continue
        px,py=car_transform(obj['xyz'][0],obj['xyz'][1])
        if obj['shape']=='box':
            a,b,_=obj['size'];w=b*2.45;h=a*2.45
            c.rect(px-w/2,py-h/2,w,h,component_color(obj),'#F6FCFF',8,2,.82)
        else:
            rr=obj['diameter']*2.45/2
            c.ellipse(px,py,rr,rr,component_color(obj),'#FFFFFF',2,.88)
        aliases={'controller_carrier':'CARRIER','brain':'BRAIN','motion':'MOTION','fpga':'FPGA',
                 'drv_left':'DRV-L','drv_right':'DRV-R','oled':'OLED','mic':'MIC',
                 'speaker':'SPK','imu':'IMU','estop':'E-STOP'}
        if obj['id'] in aliases:
            c.text(px,py+5,aliases[obj['id']],13,'#FFFFFF',700,'middle')
    # Battery pack lower-level envelope: place a subtle badge outside the plate.
    x,y=car_transform(0,0)
    c.rect(x-60,y-22,120,45,COLORS['battery'],r=8,opacity=.92)
    c.text(x,y-3,'PACK 2S1P',14,'#FFFFFF',700,'middle')
    c.text(x,y+14,'BELOW DECK',11,'#FFFFFF',500,'middle')
    c.text(61,856,'Acrylic outline is stylized; mounting holes and board headers NOT surveyed.',15,'#6A7B8C')


def carrier_panel(c):
    c.rect(862,116,707,390,'#FFFFFF',COLORS['line'],18)
    c.text(893,158,'B  /  SIGNAL CARRIER PCB',21,COLORS['ink'],700)
    c.text(893,185,'150 x 78 mm / 1.6 mm  |  only low-current logic paths',15,COLORS['muted'])
    x0,y0=1210,344
    scale=3.35
    pp=LAYOUT['pcb_concept']['controller_carrier']
    w,h=pp['size'][0]*scale,pp['size'][1]*scale
    c.rect(x0-w/2,y0-h/2,w,h,COLORS['board'],'#0F5A4E',14,3,.93)
    # Mounting hole suggestions shown as positions but not real drilled coordinates.
    for xx in (x0-w/2+15,x0+w/2-15):
        for yy in (y0-h/2+15,y0+h/2-15):
            c.ellipse(xx,yy,5,5,'#F1D495','#FFFFFF',1)
    c.line(x0-w/2+20,y0+6,x0+w/2-20,y0+6,'#D9F1E8',2,True)
    for key in ('brain','motion','fpga','imu'):
        o=next(z for z in LAYOUT['components'] if z['id']==key)
        x=x0+o['xyz'][0]*scale
        y=y0-(o['xyz'][1]-pp['xyz'][1])*scale
        sx,sy,_=o['size']
        col=component_color(o)
        c.rect(x-sx*scale/2,y-sy*scale/2,sx*scale,sy*scale,col,'#FFFFFF',6,2)
        c.text(x,y+6,key.upper(),15,'#FFFFFF',700,'middle')
    c.text(904,491,'RF keepout and edge/cutout must be verified on real ESP32 boards.',13,COLORS['muted'])


def power_panel(c):
    c.rect(862,521,707,390,'#FFFFFF',COLORS['line'],18)
    c.text(893,563,'C  /  POWER, GROUND AND MOTOR ROUTING',21,COLORS['ink'],700)
    c.text(893,591,'Conceptual flow; four independent H-bridges in two DRV8833 modules',15,COLORS['muted'])
    items=[(896,635,150,'2S1P + BMS','#497FCD'),(1080,635,153,'FUSE / PDB','#D69635'),
           (1272,635,249,'Motor buck (5-6V test)','#D69635'),
           (1080,722,174,'5V logic buck','#3999BB'),(1301,722,220,'DRV8833 L + R','#D35C5C')]
    for x,y,w,t,color in items:
        c.rect(x,y,w,58,color,r=9)
        c.text(x+w/2,y+34,t,16,'#FFFFFF',700,'middle')
    c.line(1046,663,1080,663,'#CB704F',5)
    c.line(1233,663,1272,663,'#CB704F',5)
    c.line(1159,693,1159,722,COLORS['signal'],5)
    c.line(1395,693,1395,722,'#CB704F',5)
    c.line(1395,781,1395,809,'#CB704F',5)
    c.rect(1267,808,256,48,'#FFF0EC','#D76155',10,2)
    c.text(1395,836,'Motor outputs (x4)',16,'#B3534B',700,'middle')
    c.text(900,823,'GND common / returns kept separate until defined node',14,COLORS['gnd'])
    c.line(913,844,1240,844,'#566779',3,True)
    c.text(893,885,'STOP: NC -> latch -> driver-disable chain, independent of MCU/FPGA clock.',13,'#A34B44',600)


def draw_system():
    c=Canvas(1600,1000)
    c.rect(0,0,c.w,c.h,COLORS['bg'])
    title(c,'AW-CAR  |  BEAUTIFUL AND SERVICEABLE BOARD LAYOUT',
          'v0.3 / chassis based on supplied photo  |  two PCB roles  |  low pack / quiet logic / separated motor current')
    car_panel(c);carrier_panel(c);power_panel(c)
    c.save(ROOT/'pcb-system-layout.svg')


def board_drawing():
    c=Canvas(1600,1000)
    c.rect(0,0,c.w,c.h,COLORS['bg'])
    title(c,'AW-CAR  |  ROUTING CORRIDOR CONCEPT',
          'RED: motor power  /  BLUE: low-current signal  /  GRAY: return  /  GREEN: control carrier  |  NOT real copper')
    c.rect(35,125,1530,820,'#FFFFFF',COLORS['line'],18)
    c.text(68,172,'BOARD 1: INTERFACE CARRIER',22,COLORS['ink'],700)
    c.text(68,198,'150 x 78 mm / mount only after PCB dimensions and antenna orientation confirmed',15,COLORS['muted'])
    x0,y0=500,433; scale=5.45
    bw,bh=150*scale,78*scale
    c.rect(x0-bw/2,y0-bh/2,bw,bh,'#197E6E','#0B544D',15,4)
    for side,y in [('signal',y0-60),('gnd',y0+62)]:
        cc=COLORS[side]
        c.line(x0-bw/2+26,y,x0+bw/2-30,y,cc,4,True)
    c.text(230,240,'FRONT / ESP32 ANTENNA OR USB END (VERIFY)',15,'#D8F0E9',700)
    # Modules as envelopes and visual keepout estimates (not pinned to antenna geometry).
    p=LAYOUT['pcb_concept']['controller_carrier']
    for key in ('brain','motion','fpga','imu'):
        o=next(z for z in LAYOUT['components'] if z['id']==key)
        x=x0+o['xyz'][0]*scale;y=y0-(o['xyz'][1]-p['xyz'][1])*scale
        sx,sy,_=o['size'];color=component_color(o)
        c.rect(x-sx*scale/2,y-sy*scale/2,sx*scale,sy*scale,color,'#F5FCFA',10,3)
        c.text(x,y+5,key.upper(),21,'#FFFFFF',700,'middle')
    c.rect(1050,264,460,445,'#EDF4FC','#C7D9E8',12)
    c.text(1081,307,'LOGICAL CONNECTOR GROUPS',20,COLORS['ink'],700)
    items=[('J_LOGIC_5V','power to controller modules'),('J_LINK','Brain <-> Motion UART/command'),
           ('J_FPGA','Motion <-> FPGA UART + permits'),('J_ENC_L / R','V2 pulse inputs via level shift'),
           ('J_SAFETY','E-stop state, gate, fault/status'),('J_SERVICE','USB programming/service clearance')]
    for i,(head,sub) in enumerate(items):
        yy=340+i*54
        c.ellipse(1097,yy,6,6,COLORS['signal'])
        c.text(1113,yy+4,head,16,COLORS['ink'],700)
        c.text(1113,yy+22,sub,13,COLORS['muted'])
    c.rect(88,766,1417,107,'#FFF6E9','#E3BC77',12)
    c.text(113,800,'SEPARATE BOARD 2: PDB / FUSE / POWER SPLIT  (36 x 25 mm concept envelope)',19,'#80572B',700)
    c.text(113,830,'Battery current uses rated wiring/connectors and selected copper stack-up; do not carry four motors through GPIO headers.',16,'#7B613D')
    c.text(113,856,'No 2S raw supply under ESP32 antenna; no traces routed underneath the RF keepout; driver bulk capacitors near VM/GND.',15,'#7B613D')
    c.save(ROOT/'pcb-routing-corridors.svg')


if __name__=='__main__':
    draw_system()
    board_drawing()
    print('Generated AW-Car PCB concept SVG/PNG diagrams from CAD layout.')
