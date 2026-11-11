"""Generate editable A3 KiCad + draw.io from one pin-level wiring model.

Native KiCad wires connect the pins; labels name nets rather than replace wires.
Existing hand edits are protected; --force saves the old sheet outside schematic/.
"""
from __future__ import annotations
import argparse
from collections import defaultdict
from datetime import datetime,timezone
import json
from pathlib import Path
import shutil
import uuid
import xml.etree.ElementTree as ET
from schematic_model import GRID,PARTS,terminals,route_all

ROOT=Path(__file__).resolve().parents[1]
NS=uuid.UUID('ff2c4606-b61b-4854-a0db-e2d555420d11')
def uid(s):return str(uuid.uuid5(NS,s))
def q(s):return json.dumps(str(s),ensure_ascii=False)
def mm(v):return f'{v*GRID:.4f}'.rstrip('0').rstrip('.')
def xy(p):return ' '.join(mm(v) for v in p)
def effects(size=1,justify=''):
    return f'(effects (font (size {size} {size}))'+(f' (justify {justify})' if justify else '')+')'


def segments(edges,pins):
    """Compress straight grid runs without splitting crossings of different nets."""
    graphs=defaultdict(lambda:defaultdict(set))
    for (a,b),net in edges.items():graphs[net][a].add(b);graphs[net][b].add(a)
    lines=[];junctions=[]
    for net,graph in graphs.items():
        ends={point for point,neighbors in graph.items() if len(neighbors)!=2 or
              len({n[0] for n in neighbors})>1 and len({n[1] for n in neighbors})>1}
        ends.update(pin['point'] for pin in pins.values() if pin['net']==net)
        visited=set()
        for start in sorted(ends):
            for neighbor in sorted(graph[start]):
                edge=tuple(sorted((start,neighbor)))
                if edge in visited:continue
                prev,cur=start,neighbor;visited.add(edge)
                while cur not in ends:
                    nxt=next(n for n in graph[cur] if n!=prev)
                    visited.add(tuple(sorted((cur,nxt))));prev,cur=cur,nxt
                lines.append((net,start,cur))
        junctions.extend((net,p) for p,n in graph.items() if len(n)>=3)
    return lines,junctions


def library(part):
    ref=part['ref'];x,y,w,h=part['box'];pins=[]
    for pin in part['pins']:
        number,name,kind,side,px,py,net=pin
        tip=terminals()[ref,number]['point']
        at=(tip[0]-x,y-tip[1]);angle={'L':0,'R':180,'T':270,'B':90}[side]
        pins.append(f'(pin {kind} line (at {xy(at)} {angle}) (length {mm(3)}) '
                    f'(name {q(name)} {effects(.85)}) (number {q(number)} {effects(.7)}))')
    rgb=tuple(int(part['color'][i:i+2],16) for i in (1,3,5))
    # KiCad 10 supports custom symbol fill colors (validated by actual export).
    fill=f'(fill (type color) (color {rgb[0]} {rgb[1]} {rgb[2]} 1))'
    dash='dash' if part['planned'] else 'solid'
    color='(color 175 115 30 1)' if part['planned'] else '(color 55 70 85 1)'
    return (f'(symbol {q(ref)} (pin_numbers hide) (pin_names (offset .65)) (in_bom yes) (on_board no) '
       f'(property "Reference" {q(ref)} (at 0 0 0) {effects()}) '
       f'(property "Value" {q(part["title"])} (at 0 0 0) {effects()}) '
       f'(symbol {q(ref+"_0_1")} (rectangle (start 0 0) (end {mm(w)} {mm(-h)}) '
       f'(stroke (width .254) (type {dash}) {color}) {fill})) '
       f'(symbol {q(ref+"_1_1")} '+ ' '.join(pins)+'))')


def drawio(output,pins,lines,junctions):
    """Editable colored companion with identical pin coordinates and wire paths."""
    scale=4;pixel=lambda n:n*GRID*scale
    doc=ET.Element('mxfile',host='app.diagrams.net',version='26.0.0')
    diagram=ET.SubElement(doc,'diagram',id='awcar-a3',name='AW-Car A3 pin wiring')
    model=ET.SubElement(diagram,'mxGraphModel',page='1',pageScale='1',pageWidth='1680',pageHeight='1188',
                        grid='1',gridSize='5',background='#FFFFFF')
    root=ET.SubElement(model,'root');ET.SubElement(root,'mxCell',id='0');ET.SubElement(root,'mxCell',id='1',parent='0')
    def vertex(ident,text,x,y,w,h,style,parent='1'):
        c=ET.SubElement(root,'mxCell',id=ident,value=text,vertex='1',parent=parent,
                        style='html=1;fontFamily=Arial;'+style)
        ET.SubElement(c,'mxGeometry',x=str(x),y=str(y),width=str(w),height=str(h),**{'as':'geometry'})
        return c
    vertex('title','AW-CAR / PROTOTYPE V2 — A3 WIRING',35,20,1300,28,
           'fillColor=none;strokeColor=none;align=left;fontSize=19;fontStyle=1;')
    for p in PARTS:
        x,y,w,h=p['box'];ref=p['ref']
        vertex(ref,ref+' · '+p['title'],pixel(x),pixel(y),pixel(w),pixel(h),
                'container=1;pointerEvents=0;rounded=0;verticalAlign=top;spacingTop=5;'
                f'fillColor={p["color"]};strokeColor=#374655;fontSize=11;fontStyle=1;'+
                ('dashed=1;' if p['planned'] else ''))
        for number,name,kind,side,px,py,net in p['pins']:
            pin=pins[ref,number];tx,ty=pin['point'];ident=ref+'_'+number
            vertex(ident,'',pixel(tx)-.5,pixel(ty)-.5,1,1,'shape=ellipse;fillColor=none;strokeColor=none;')
            anchor=ident+'_body'
            vertex(anchor,'',pixel(px)-.5,pixel(py)-.5,1,1,'shape=ellipse;fillColor=none;strokeColor=none;')
            stub=ET.SubElement(root,'mxCell',id=ident+'_stub',edge='1',parent='1',source=anchor,target=ident,
               style='html=1;endArrow=none;startArrow=none;strokeWidth=1;strokeColor=#8B5260;')
            ET.SubElement(stub,'mxGeometry',relative='1',**{'as':'geometry'})
            # Body-side labels remain children of their modules.
            if side in 'LR':
                width=min(91,pixel(w)/2-5)
                lx=3 if side=='L' else pixel(w)-width-3
                vertex(ident+'_label',name,lx,pixel(py-y)-7,width,14,
                       'fillColor=none;strokeColor=none;fontSize=9;fontStyle=0;align='+('left;' if side=='L' else 'right;'),ref)
    locations={};dots={(n,p) for n,p in junctions}
    for pin in pins.values():
        if pin['net']:locations[pin['net'],pin['point']]=pin['ref']+'_'+pin['pin']
    def endpoint(net,point):
        key=(net,point)
        if key not in locations:
            ident='n_'+uid(net+str(point));locations[key]=ident
            vertex(ident,'',pixel(point[0])-1,pixel(point[1])-1,2,2,
                   'shape=ellipse;strokeColor=none;fillColor='+('#22704F;' if key in dots else 'none;'))
        return locations[key]
    for index,(net,a,b) in enumerate(lines):
        edge=ET.SubElement(root,'mxCell',id='wire_'+str(index),value='',edge='1',parent='1',
             source=endpoint(net,a),target=endpoint(net,b),
             style='html=1;endArrow=none;startArrow=none;rounded=0;strokeWidth=1;strokeColor=#24654D;')
        ET.SubElement(edge,'mxGeometry',relative='1',**{'as':'geometry'})
    ET.indent(doc);output.write_bytes(ET.tostring(doc,encoding='utf-8',xml_declaration=True))


def generate(output,force=False):
    manifest_path=(ROOT/'data/wiring.json') if output.resolve()==(ROOT/'schematic/simplev1.kicad_sch').resolve() else output.with_suffix('.wiring.json')
    generated=[output,output.with_suffix('.kicad_sym'),output.with_suffix('.drawio'),
               output.with_suffix('.kicad_pro'),output.parent/'sym-lib-table',manifest_path]
    if any(p.exists() for p in generated):
        if not force:raise SystemExit('Existing editable files protected: use --force to save a private backup first')
        stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        backup=ROOT/'build/private/schematic-backups'/stamp;backup.mkdir(parents=True)
        for p in generated:
            if p.exists():shutil.copy2(p,backup/p.name)
    pins,paths,edges=route_all();lines,junctions=segments(edges,pins)
    root_id=uid('sheet');libs=[];instances=[];objects=[]
    manifest={'scope':'A3 module interconnect; 8.4V bench + planned sensors, NOT PCB release',
              'paper':'A3 landscape','firmware_changed':False,'pins':[]}
    for p in PARTS:
        ref=p['ref'];x,y,w,h=p['box'];raw=library(p);libs.append(raw)
        embedded=raw.replace(f'(symbol {q(ref)} ',f'(symbol "AWCAR:{ref}" ',1)
        ident=uid(ref)
        props=f'(property "Reference" {q(ref)} (at {mm(x+w/2)} {mm(y+2)} 0) {effects(.95)}) '
        props+=f'(property "Value" {q(p["title"])} (at {mm(x+w/2)} {mm(y+4.3)} 0) {effects(.95)}) '
        # Smaller resistors/jumpers put both names above the body, clear of pins.
        if ref.startswith(('R','JP')):
            props=f'(property "Reference" {q(ref)} (at {mm(x+w/2)} {mm(y-3)} 0) {effects(.8)}) '
            props+=f'(property "Value" {q(p["title"])} (at {mm(x+w/2)} {mm(y-1)} 0) {effects(.75)}) '
        instances.append(f'(symbol (lib_id "AWCAR:{ref}") (at {mm(x)} {mm(y)} 0) (unit 1) '
          f'(in_bom yes) (on_board no) (dnp no) (uuid "{ident}") '+props+
          ' '.join(f'(pin {q(t[0])} (uuid "{uid(ref+":"+t[0])}"))' for t in p['pins'])+
          f' (instances (project {q(output.stem)} (path "/{root_id}" (reference {q(ref)}) (unit 1)))))')
        p['embedded']=embedded
    for index,(net,a,b) in enumerate(lines):
        objects.append(f'(wire (pts (xy {xy(a)}) (xy {xy(b)})) (stroke (width 0) (type default)) (uuid "{uid("wire:"+str(index))}"))')
    for net,point in junctions:
        objects.append(f'(junction (at {xy(point)}) (diameter 0) (color 0 0 0 0) (uuid "{uid(net+str(point))}"))')
    labeled=set()
    for pin in pins.values():
        ref,num,net,point=pin['ref'],pin['pin'],pin['net'],pin['point']
        manifest['pins'].append({'ref':ref,'pin':num,'net':net,'type':pin['kind'],'planned':pin['planned']})
        if not net:
            objects.append(f'(no_connect (at {xy(point)}) (uuid "{uid(ref+num+":nc")}"))');continue
        if net in labeled:continue
        labeled.add(net);justify='right' if pin['side']=='L' else 'left'
        objects.append(f'(label {q(net)} (at {xy(point)} 0) {effects(.75,justify+" bottom")} (uuid "{uid(net+":label")}"))')
    # Post-jumper rails are physically powered in RUN or by onboard USB in DEBUG.
    # Explicit power-source flags describe this; they do not alter wire connectivity.
    for index,net in enumerate(['5V_BRAIN','5V_MOTION','5V_TANG']):
        pin=next(p for p in pins.values() if p['net']==net);ref='#FLG'+str(index+1)
        name='PWR_FLAG';point=pin['point']
        lib=('(symbol "PWR_FLAG" (power) (pin_numbers hide) (pin_names hide) (in_bom no) (on_board no) '+
            '(property "Reference" "#FLG" (at 0 0 0) (effects (font (size 1 1)) hide)) '+
            '(property "Value" "PWR_FLAG" (at 0 0 0) (effects (font (size 1 1)) hide)) '+
            '(symbol "PWR_FLAG_1_1" (pin power_out line (at 0 0 90) (length 0) '+
            '(name "pwr" (effects (font (size 1 1)))) (number "1" (effects (font (size 1 1)))))))')
        if index==0:libs.append(lib)
        instances.append(f'(symbol (lib_id "AWCAR:PWR_FLAG") (at {xy(point)} 0) (unit 1) (in_bom no) (on_board no) (dnp no) '
          f'(uuid "{uid(ref)}") (property "Reference" {q(ref)} (at {xy(point)} 0) (effects (font (size 1 1)) hide)) '
          f'(property "Value" "PWR_FLAG" (at {xy(point)} 0) (effects (font (size 1 1)) hide)) '
          f'(pin "1" (uuid "{uid(ref+":pin")}")) (instances (project {q(output.stem)} (path "/{root_id}" (reference {q(ref)}) (unit 1)))))')
    notes=[('AW-CAR / PROTOTYPE V2 / A3 WIRING',10,12,1.9),
      ('Purple: Brain | Blue: Motion | Green: FPGA | [PLAN]: future wiring, firmware not enabled',10,18,1),
      ('RUN: close JP1/2/3 only with board USB unplugged. DEBUG: open that board jumper BEFORE USB.',10,278,1),
      ('GPIO17/18 Motion UNUSED. Pxx = PACKAGE pin. System input <=8.4V: VM bypasses the DSN.',10,282,1),
      ('DSN 5V: NO-LOAD verified only. AMP buck/load/filters TBD. SPK- is NOT GND.',10,286,.95),
      ('ENC L: change P27 pull to NONE first. TCRT DO / sensor I2C: 0..3V3. Planned pins not enabled.',10,274,.95)]
    for text,x,y,size in notes:
        objects.append(f'(text {q(text)} (at {x} {y} 0) {effects(size,"left")} (uuid "{uid(text)}"))')
    raw=f'(kicad_sch (version 20250114) (generator "eeschema") (generator_version "10.0") (uuid "{root_id}") (paper "A3")\n'
    raw+='(title_block (title "AW-Car prototype v2 - Module wiring") (date "2026-11-11") (rev "A3-2") (company "AW-Car") (comment 1 "Draft: no PCB, no motor/power acceptance"))\n'
    embedded=[p['embedded'] for p in PARTS]+[lib.replace('(symbol "PWR_FLAG"','(symbol "AWCAR:PWR_FLAG"',1)]
    raw+='(lib_symbols\n'+'\n'.join(embedded)+')\n'
    raw+='\n'.join(objects+instances)+'\n)\n'
    output.parent.mkdir(parents=True,exist_ok=True);output.write_text(raw,encoding='utf-8',newline='\n')
    output.with_suffix('.kicad_sym').write_text('(kicad_symbol_lib (version 20241209) (generator "kicad_symbol_editor")\n'+'\n'.join(libs)+'\n)\n',encoding='utf-8',newline='\n')
    (output.parent/'sym-lib-table').write_text(f'(sym_lib_table (version 7) (lib (name "AWCAR") (type "KiCad") (uri "${{KIPRJMOD}}/{output.stem}.kicad_sym") (options "") (descr "Logical plug-in modules, no footprint mapping")))\n',encoding='utf-8',newline='\n')
    project=output.with_suffix('.kicad_pro')
    if not project.exists():project.write_text(json.dumps({'meta':{'filename':project.name,'version':1}},indent=2)+'\n',encoding='utf-8',newline='\n')
    manifest_path.write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8',newline='\n')
    drawio(output.with_suffix('.drawio'),pins,lines,junctions)
    print(json.dumps({'parts':len(PARTS),'pins':len(pins),'nets':len(labeled),'wire_segments':len(lines),'junctions':len(junctions),'output':str(output)}))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'schematic/simplev1.kicad_sch')
    parser.add_argument('--force',action='store_true')
    args=parser.parse_args();generate(args.output,args.force)
