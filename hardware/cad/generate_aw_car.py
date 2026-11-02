"""AW-Car provisional parametric CAD: SCAD, OBJ/MTL, schematic, PNG previews.

No geometry kernel is assumed. All geometry uses mm and simple envelope solids.
These are *not* verified manufacturing drawings or validated electrical wiring.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / 'layout.json'

RGB = {
    'plate': (169, 214, 234), 'stand': (192, 165, 111), 'wheel': (37, 41, 49),
    'hub': (236, 182, 43), 'motor': (235, 176, 43), 'battery': (55, 113, 205),
    'brain': (42, 113, 207), 'motion': (25, 169, 157), 'fpga': (104, 80, 171),
    'driver': (209, 74, 79), 'screen': (27, 146, 189), 'sensor': (50, 177, 185),
    'speaker': (85, 96, 113), 'estop': (224, 55, 65), 'power': (229, 157, 49),
    'safety': (237, 95, 63), 'wire_motor': (215, 64, 61),
    'wire_signal': (50, 165, 228), 'wire_ground': (56, 56, 67),
    'axle': (159, 171, 184), 'encoder_disc': (40, 45, 55),
    'pcb': (30, 130, 115), 'pcb_power': (24, 111, 89),
}


def box(center, size):
    x, y, z = center
    a, b, c = [s/2 for s in size]
    verts = [(x+sx*a, y+sy*b, z+sz*c) for sx,sy,sz in
             [(-1,-1,-1),(1,-1,-1),(1,1,-1),(-1,1,-1),
              (-1,-1,1),(1,-1,1),(1,1,1),(-1,1,1)]]
    faces = [(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),
             (2,3,7,6),(3,0,4,7)]
    return verts, faces


def cylinder(center, radius, height, axis='z', n=32):
    x,y,z = center
    verts = []
    for sign in (-1, 1):
        for i in range(n):
            t=2*math.pi*i/n
            if axis == 'z': verts.append((x+radius*math.cos(t),y+radius*math.sin(t),z+sign*height/2))
            elif axis == 'x': verts.append((x+sign*height/2,y+radius*math.cos(t),z+radius*math.sin(t)))
            else: verts.append((x+radius*math.cos(t),y+sign*height/2,z+radius*math.sin(t)))
    faces=[tuple(reversed(tuple(range(n)))),tuple(range(n,2*n))]
    for i in range(n): faces.append((i,(i+1)%n,(i+1)%n+n,i+n))
    return verts,faces


def ring_y(center, outer_radius, inner_radius, width, n=40):
    """Ring extruded along Y, for the recognizable black tire/yellow rim."""
    x,y,z=center
    vertices=[]
    for yy,rr in [(-width/2,outer_radius),(width/2,outer_radius),
                  (-width/2,inner_radius),(width/2,inner_radius)]:
        vertices.extend((x+rr*math.cos(t*2*math.pi/n),y+yy,z+rr*math.sin(t*2*math.pi/n)) for t in range(n))
    faces=[]
    for i in range(n):
        j=(i+1)%n
        faces.extend([(i,j,n+j,n+i),(2*n+j,2*n+i,3*n+i,3*n+j),
                      (j,i,2*n+i,2*n+j),(n+i,n+j,3*n+j,3*n+i)])
    return vertices,faces


def spoke_y(center, radius, theta_deg, length=20, thick=3, depth=5):
    """One yellow spoke in the wheel face, radial in XZ."""
    theta=math.radians(theta_deg)
    local_v,faces=box((radius,0,0),(length,thick,depth))
    x,y,z=center
    verts=[(x+vx*math.cos(theta)-vz*math.sin(theta),y+vy,
            z+vx*math.sin(theta)+vz*math.cos(theta)) for vx,vy,vz in local_v]
    return verts,faces


def deck_outline(p, wheel):
    """Curved front/rear TT 4WD plate silhouette, NOT traced mounting geometry.

    The photo shows rounded noses, an inset alongside four tires, and wide
    shoulders in the middle. Vertices are purely representational until traced.
    """
    halfx, halfy = p['length']/2, p['width']/2
    sx, sy = p['length']/260, p['width']/155
    notch = p['side_notch_y']
    shoulder = p['waist_shoulder_x']
    front_end = wheel['front_x']+wheel['diameter']/2+5
    rear_start = wheel['rear_x']-wheel['diameter']/2-5
    upper = [
        (-halfx, 0), (-halfx+2*sx, 20*sy), (-halfx+7*sx, 38*sy),
        (-halfx+17*sx, notch), (front_end, notch),
        (-shoulder, halfy-11*sy), (-shoulder+15*sx, halfy),
        (shoulder-15*sx, halfy), (shoulder, halfy-11*sy),
        (rear_start, notch), (halfx-17*sx, notch),
        (halfx-7*sx, 38*sy), (halfx-2*sx, 20*sy), (halfx, 0),
    ]
    # Do not duplicate the two pointed end vertices when mirroring.
    return upper + [(x,-y) for x,y in reversed(upper[1:-1])]


def polygon_area(points):
    return sum(x0*y1-x1*y0 for (x0,y0),(x1,y1) in zip(points,points[1:]+points[:1]))/2


def triangulate_polygon(points):
    """Ear-clipping of this simple, potentially concave, acrylic contour."""
    sign = 1 if polygon_area(points)>0 else -1
    remaining=list(range(len(points)))
    triangles=[]
    def cross2(a,b,c):
        return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
    def inside_triangle(p,a,b,c):
        return all(sign*cross2(v0,v1,p)>=-1e-9 for v0,v1 in ((a,b),(b,c),(c,a)))
    while len(remaining)>3:
        found=False
        for k in range(len(remaining)):
            a,b,c=(remaining[(k-1)%len(remaining)],remaining[k],remaining[(k+1)%len(remaining)])
            if sign*cross2(points[a],points[b],points[c])<=1e-9:continue
            if any(inside_triangle(points[t],points[a],points[b],points[c])
                   for t in remaining if t not in (a,b,c)):continue
            triangles.append((a,b,c))
            del remaining[k]
            found=True
            break
        if not found:raise ValueError('Could not triangulate provisional deck outline')
    triangles.append(tuple(remaining))
    return triangles


def extrude_polygon(outline, z, thickness):
    n=len(outline)
    verts=[(x,y,z) for x,y in outline]+[(x,y,z+thickness) for x,y in outline]
    # Triangulate concave endcap/wheel contour for predictable OBJ viewers.
    ccw=polygon_area(outline)>0
    triangles=triangulate_polygon(outline)
    faces=[]
    for tri in triangles:
        faces.append(tuple(reversed(tri)) if ccw else tri)
        faces.append(tuple(i+n for i in tri) if ccw else tuple(i+n for i in reversed(tri)))
    for i in range(n):
        j=(i+1)%n
        faces.append((i,j,j+n,i+n) if ccw else (j,i,i+n,j+n))
    return verts,faces


class Assembly:
    def __init__(self): self.solids=[]

    def add(self,name,material,mesh,scad):
        self.solids.append((name,material,mesh,scad))

    def cube(self,name,material,xyz,size):
        x,y,z=xyz
        scad=f'translate([{x},{y},{z}]) cube({size}, center=true);'
        self.add(name,material,box(xyz,size),scad)

    def cyl(self,name,material,xyz,diameter,height,axis='z'):
        x,y,z=xyz
        rot={'z':'','x':'rotate([0,90,0]) ','y':'rotate([90,0,0]) '}[axis]
        scad=f'translate([{x},{y},{z}]) {rot}cylinder(h={height}, d={diameter}, center=true, $fn=40);'
        self.add(name,material,cylinder(xyz,diameter/2,height,axis),scad)

    def ring_y(self,name,material,xyz,diameter,inner_diameter,width):
        x,y,z=xyz
        scad=(f'translate([{x},{y},{z}]) rotate([90,0,0]) difference() {{ '
              f'cylinder(h={width}, d={diameter}, center=true, $fn=40); '
              f'cylinder(h={width+0.6}, d={inner_diameter}, center=true, $fn=40); }}')
        self.add(name,material,ring_y(xyz,diameter/2,inner_diameter/2,width),scad)

    def spoke_y(self,name,material,xyz,radius,theta):
        x,y,z=xyz
        scad=(f'translate([{x},{y},{z}]) rotate([0,{-theta},0]) '
              f'translate([{radius},0,0]) cube([20,3,5], center=true);')
        self.add(name,material,spoke_y(xyz,radius,theta),scad)

    def plate(self,name,material,p,wheel):
        z=p['z']; t=p['thickness']
        if p.get('profile')=='curved_tt_4wd':
            points=deck_outline(p,wheel)
            mesh=extrude_polygon(points,z,t)
            scad=f'translate([0,0,{z}]) linear_extrude(height={t}) polygon(points={json.dumps(points)});'
        else:
            mesh=box((0,0,z+t/2),(p['length'],p['width'],t))
            scad=f'translate([0,0,{z+t/2}]) cube([{p["length"]},{p["width"]},{t}], center=true);'
        self.add(name,material,mesh,scad)


def build(data):
    a=Assembly()
    base=data['base']; upper=data['top_deck']; wheel=data['wheel']
    a.plate('LOWER_NOTCHED_ACRYLIC', 'plate', base, wheel)
    a.plate('UPPER_ACRYLIC', 'plate', upper, wheel)
    for k,(x,y) in enumerate(data['standoff']['centers'],1):
        z=(base['z']+base['thickness']+upper['z'])/2
        a.cyl(f'STANDOFF_{k}', 'stand', (x,y,z),
              data['standoff']['radius']*2,upper['z']-base['z']-base['thickness'])
    for name,settings in data.get('pcb_concept',{}).items():
        top_of_support=settings['xyz'][2]-settings['size'][2]/2
        bottom_of_support=(upper['z']+upper['thickness'] if name=='controller_carrier'
                           else base['z']+base['thickness'])
        height=top_of_support-bottom_of_support
        if height<=0:raise ValueError('PCB support height must be positive: '+name)
        for k,(x,y) in enumerate(settings.get('support_xy',[]),1):
            a.cyl('PCB_SUPPORT_'+name.upper()+'_'+str(k),'stand',
                  (x,y,(top_of_support+bottom_of_support)/2),5,height)
    for fx,x in [('FRONT',wheel['front_x']),('REAR',wheel['rear_x'])]:
        for side,y in [('LEFT',wheel['left_y']),('RIGHT',wheel['right_y'])]:
            name=f'{fx}_{side}'
            a.cube('TT_MOTOR_'+name, 'motor',
                   (x,math.copysign(data['tt_motor']['inside_y'],y),data['tt_motor']['z']),data['tt_motor']['size'])
            motor=data['tt_motor']; sign=1 if y>0 else -1
            # Double-ended shaft and slotted-disc *envelope* match the photo,
            # not the actual number of slots or gear ratio of the purchased kit.
            inner_body=abs(motor['inside_y'])+motor['size'][1]/2
            inner_wheel=abs(y)-wheel['width']/2
            gap=inner_wheel-inner_body
            if gap>0:a.cyl('OUTER_SHAFT_'+name,'axle',
                           (x,sign*(inner_body+gap/2),wheel['axle_height']),
                           5,gap,'y')
            a.cyl('INNER_ENCODER_DISC_'+name,'encoder_disc',
                  (x,sign*motor['encoder_disc_y'],wheel['axle_height']),
                  motor['inner_encoder_disc_diameter'],motor['inner_encoder_disc_thickness'],'y')
            a.ring_y('TIRE_'+name,'wheel',(x,y,wheel['axle_height']),wheel['diameter'],
                     wheel['diameter']-14,wheel['width'])
            hub_y=sign*(abs(y)+wheel['width']/2-1)
            a.ring_y('YELLOW_RIM_'+name,'hub',(x,hub_y,wheel['axle_height']),
                     wheel['diameter']-13,wheel['diameter']-23,3)
            for spoke_i in range(5):
                a.spoke_y('YELLOW_SPOKE_'+name+'_'+str(spoke_i),'hub',
                          (x,hub_y,wheel['axle_height']),13.5,spoke_i*72)
            a.cyl('HUB_'+name,'hub',(x,hub_y,wheel['axle_height']),17,3.5,'y')
    # Pack box represents insulated strapped *pack*, not exposed Li-ion cells.
    a.cube('SEALED_2S1P_PACK','battery',data['battery']['xyz'],data['battery']['size'])
    for obj in data['components']:
        if obj['shape']=='box':a.cube(obj['id'].upper(),obj['color'],obj['xyz'],obj['size'])
        else:a.cyl(obj['id'].upper(),obj['color'],obj['xyz'],obj['diameter'],obj['height'])
    # Functional wire-routes: approximate zones, not physical pin connections.
    for side,y in [('left',50),('right',-50)]:
        for x in [-48,0,48]:
            a.cube('MOTOR_HARNESS_'+side+'_'+str(x),'wire_motor',(x,y,80),[43,2.2,2.2])
    for x in [-54,-10,34]:
        a.cube('SIGNAL_HARNESS_'+str(x),'wire_signal',(x,-13,84),[41,2.0,2.0])
    return a


def export_scad(a,data):
    lines=['// Generated by generate_aw_car.py from layout.json; mm; do not machine without survey.',
           '// X(-) front; Y(+) left; Z(+) up. Visible board envelopes only.',
           '// Read README.md before interpreting dimensions as actual measurements.',
           '$fn=40;','module aw_car_assembly() {']
    for name,material,mesh,command in a.solids:
        rr=[round(v/255,4) for v in RGB[material]]
        alpha=0.48 if material=='plate' else 1
        lines.extend(['  // '+name,'  color('+json.dumps(rr)+f', {alpha}) '+command])
    lines.extend(['}','aw_car_assembly();',''])
    return '\n'.join(lines)


def export_obj(a):
    mtl=['# AW-Car illustrative color materials — not mechanical part definitions']
    for name,rgb in RGB.items():
        mtl+=['newmtl '+name, 'Kd '+' '.join(f'{v/255:.5f}' for v in rgb),
              'Ka 0.2 0.2 0.2','Ks 0.1 0.1 0.1','Ns 16',
              f'd {0.5 if name=="plate" else 1.0}','']
    obj=['# AW-Car assembly envelope mesh in mm','mtllib aw_car_assembly.mtl']
    offset=1
    for name,material,(verts,faces),_ in a.solids:
        obj+=['g '+name,'usemtl '+material]
        obj.extend(f'v {x:.4f} {y:.4f} {z:.4f}' for x,y,z in verts)
        obj.extend('f '+' '.join(str(j+offset) for j in f) for f in faces)
        offset+=len(verts)
    return '\n'.join(obj)+'\n', '\n'.join(mtl).rstrip()+'\n'


def bounds(c,sz):
    return [(v-s/2,v+s/2) for v,s in zip(c,sz)]


def shape_bounds(p):
    if p['shape']=='box':return bounds(p['xyz'],p['size'])
    r=p['diameter']/2
    return bounds(p['xyz'],[r*2,r*2,p['height']])


def overlap(b1,b2,margin=0):
    return all(min(a[1],b[1])-max(a[0],b[0])>margin for a,b in zip(b1,b2))


def contained_in_outline(point, outline, margin=0):
    x,y=point
    inside=False
    nearest=math.inf
    for (x0,y0),(x1,y1) in zip(outline,outline[1:]+outline[:1]):
        # Standard even/odd crossing: boundary is accepted only if margin==0.
        if (y0>y)!=(y1>y) and x<(x1-x0)*(y-y0)/(y1-y0)+x0:
            inside=not inside
        dx,dy=x1-x0,y1-y0
        t=max(0,min(1,((x-x0)*dx+(y-y0)*dy)/(dx*dx+dy*dy)))
        nearest=min(nearest,math.hypot(x-(x0+t*dx),y-(y0+t*dy)))
    return inside and nearest>=margin-1e-6


def audit(data):
    w=data['wheel']; base=data['base']; upper=data['top_deck']
    pack=data['battery']; tt=data['tt_motor']; comp=data['components']
    errors=[]; warnings=[]
    if base['z']<=tt['z']+tt['size'][2]/2:errors.append('TT motor intersects lower deck Z')
    if pack['xyz'][2]-pack['size'][2]/2 < data['clearances']['floor_min_mm']:
        errors.append('Battery pack below configured minimum floor clearance')
    if pack['xyz'][2]+pack['size'][2]/2>=base['z']:
        errors.append('Battery overlaps underside of lower plate')
    if w['axle_height']<w['diameter']/2:errors.append('Wheel penetrates ground')
    if w['diameter']/2+abs(w['front_x'])>base['length']/2 or w['diameter']/2+w['rear_x']>base['length']/2:
        warnings.append('Wheels project outside nominal chassis length (may be intentional)')
    x_min=min(abs(w['front_x']),abs(w['rear_x']))-tt['size'][0]/2
    if x_min<pack['size'][0]/2+data['clearances']['motor_battery_gap_mm']:
        errors.append('Battery too close to motor regions in X')
    if abs(w['left_y'])-w['width']/2<base['side_notch_y']:
        errors.append('Tire may intersect curved lower plate alongside wheel')
    if tt['encoder_disc_y']+tt['inner_encoder_disc_thickness']/2>=tt['inside_y']-tt['size'][1]/2:
        errors.append('Encoder disc intersects TT motor envelope')
    if tt['z']+tt['inner_encoder_disc_diameter']/2>=base['z']:
        errors.append('Inner encoder disc collides with lower plate Z')
    if (tt['inside_y']+tt['size'][1]/2)>=abs(w['left_y'])-w['width']/2:
        errors.append('TT motor body overlaps inner tire face')
    if data.get('seller_spec'):
        spec=data['seller_spec']
        outside=(abs(w['left_y'])+abs(w['right_y'])+w['width'])
        if abs(outside-spec['width_with_tires_mm'])>0.01:
            errors.append('Model outside tire width differs from provisional seller width')
        if abs(base['width']-spec['width_without_tires_mm'])>0.01 or abs(base['length']-spec['length_mm'])>0.01:
            errors.append('Plate dimensions differ from seller specification')
        warnings.append('Seller width is inconsistent: 155mm is described as both outside tires and without tires; verify with ruler')
    physical=[o for o in comp if o['zone'] in ('upper','middle','battery')]
    overlaps=[]
    for i,a in enumerate(physical):
        for b in physical[i+1:]:
            if overlap(shape_bounds(a),shape_bounds(b)):
                overlaps.append(a['id']+' vs '+b['id'])
    if overlaps:errors.append('Component envelopes intersect: '+', '.join(overlaps))
    for o in comp:
        if o['zone']!='upper':continue
        bx=shape_bounds(o)
        if bx[0][0]<-upper['length']/2 or bx[0][1]>upper['length']/2 or bx[1][0]<-upper['width']/2 or bx[1][1]>upper['width']/2:
            errors.append(o['id']+' exceeds upper deck footprint')
        outline=deck_outline(upper,w)
        if o['shape']=='box':
            x0,x1=bx[0];y0,y1=bx[1]
            samples=[(x0,y0),(x0,y1),(x1,y0),(x1,y1)]
        else:
            r=o['diameter']/2
            samples=[(o['xyz'][0]+r*math.cos(2*math.pi*k/32),
                      o['xyz'][1]+r*math.sin(2*math.pi*k/32)) for k in range(32)]
        if not all(contained_in_outline(p,outline,2) for p in samples):
            errors.append(o['id']+' exceeds curved upper acrylic footprint (2mm margin)')
    for x,y in data['standoff']['centers']:
        for p in [base,upper]:
            if not contained_in_outline((x,y),deck_outline(p,w),data['standoff']['radius']+2):
                errors.append('Standoff too close to curved deck edge: '+str([x,y]))
    for name,p in data.get('pcb_concept',{}).items():
        back=upper if name=='controller_carrier' else base
        foot=back['z']+back['thickness']
        zlo=p['xyz'][2]-p['size'][2]/2
        if zlo<=foot:errors.append(name+' PCB intersects supporting acrylic plate')
        for xy in p.get('support_xy',[]):
            if not contained_in_outline(xy,deck_outline(back,w),4):
                errors.append(name+' support outside acrylic: '+str(xy))
            if abs(xy[0]-p['xyz'][0])>p['size'][0]/2-2 or abs(xy[1]-p['xyz'][1])>p['size'][1]/2-2:
                errors.append(name+' support outside PCB edge clearance: '+str(xy))
    by_id={o['id']:o for o in comp}
    if by_id['drv_left']['xyz'][1]<=0 or by_id['drv_right']['xyz'][1]>=0:
        errors.append('Motor driver pair must sit on opposite left/right harness zones')
    mic=by_id['mic']['xyz'];speaker=by_id['speaker']['xyz']
    audio_distance=math.dist(mic[:2],speaker[:2])
    if audio_distance<100:warnings.append('Speaker close to microphone: consider acoustical feedback and vibration')
    parts=[(0,0, data['masses']['chassis_g']), (0,0,data['masses']['battery_pack_g'])]
    for x in (w['front_x'],w['rear_x']):
        for y in (w['left_y'],w['right_y']):parts.extend([(x,y,data['masses']['motor_each_g']),(x,y,data['masses']['wheel_each_g'])])
    parts.extend((o['xyz'][0],o['xyz'][1],o['mass_g']) for o in comp)
    total=sum(z for _,_,z in parts)
    cx=sum(x*m for x,y,m in parts)/total;cy=sum(y*m for x,y,m in parts)/total
    if abs(cx)>12 or abs(cy)>12:warnings.append('Estimated center-of-mass offset exceeds 12mm')
    if not errors:warnings.append('Geometry envelopes only: electrical, load, tire sweep, cable bend & fastener clearance not validated')
    return dict(status='PASS' if not errors else 'FAIL', errors=errors,warnings=warnings,
                chassis_length_mm=base['length'],
                chassis_width_without_tires_mm=base['width'],
                wheelbase_mm=w['rear_x']-w['front_x'],
                track_centers_mm=w['left_y']-w['right_y'],
                outside_wheel_width_mm=w['left_y']-w['right_y']+w['width'],
                axle_ground_clearance_mm=w['axle_height']-w['diameter']/2,
                battery_ground_clearance_mm=pack['xyz'][2]-pack['size'][2]/2,
                top_plate_height_mm=upper['z']+upper['thickness'],
                mass_estimate_g=round(total,1),
                estimated_center_xy_mm=[round(cx,1),round(cy,1)],
                microphone_speaker_xy_distance_mm=round(audio_distance,1),
                validation_scope='provisional geometric envelopes; no physical fit or structural simulation')


def wire_svg():
    return '''<svg xmlns="http://www.w3.org/2000/svg" width="1240" height="600" viewBox="0 0 1240 600">
<defs><marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M 0 0 L 10 5 L 0 10 z" fill="#b94c4e"/></marker><marker id="b" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M 0 0 L 10 5 L 0 10 z" fill="#227dab"/></marker></defs>
<rect width="1240" height="600" fill="#f8fafc"/><text x="38" y="48" font-family="Arial" font-size="28" font-weight="bold" fill="#18314c">AW-CAR · Tách vùng dây điện (minh hoạ, không phải sơ đồ đấu chân)</text>
<g font-family="Arial" font-size="17" fill="#152b40">
<rect x="70" y="104" width="1100" height="380" rx="32" fill="#e7edf4" stroke="#8a9bab" stroke-width="2"/>
<rect x="107" y="132" width="1024" height="324" rx="22" fill="#fff" stroke="#aebbc7" stroke-dasharray="8 6"/>
<rect x="496" y="228" width="244" height="134" rx="13" fill="#d8e7fb" stroke="#507fb4"/>
<text x="539" y="268" font-weight="bold">2S1P + BMS</text><text x="514" y="299">Cầu chì / phân phối</text><text x="518" y="329">đặt thấp, giữa xe</text>
<rect x="768" y="142" width="154" height="68" rx="10" fill="#e2d5fc" stroke="#8872b5"/><text x="787" y="181">FPGA Nano 9K</text>
<rect x="276" y="142" width="156" height="68" rx="10" fill="#d7eafc" stroke="#478cc1"/><text x="306" y="181">Brain / UI</text>
<rect x="276" y="372" width="156" height="68" rx="10" fill="#cdf3ec" stroke="#318a7f"/><text x="294" y="410">Motion / PID</text>
<rect x="943" y="247" width="161" height="90" rx="10" fill="#fbdadb" stroke="#bb6164"/><text x="968" y="278">2 x DRV8833</text><text x="957" y="306">4 cầu H riêng</text>
<path d="M 617 228 L 617 163 L 746 163" stroke="#b94c4e" stroke-width="6" fill="none" marker-end="url(#a)"/>
<path d="M 740 302 L 935 302" stroke="#b94c4e" stroke-width="6" fill="none" marker-end="url(#a)"/>
<path d="M 1103 292 L 1151 292 L 1151 135 L 1020 135" stroke="#b94c4e" stroke-width="5" fill="none" marker-end="url(#a)"/>
<path d="M 1103 292 L 1151 292 L 1151 415 L 1020 415" stroke="#b94c4e" stroke-width="5" fill="none" marker-end="url(#a)"/>
<text x="950" y="121">Motor trái x2</text><text x="949" y="442">Motor phải x2</text>
<path d="M 617 362 L 617 407 L 450 407" stroke="#227dab" stroke-width="4" fill="none" marker-end="url(#b)"/>
<path d="M 432 394 L 478 394 L 478 198 L 432 198" stroke="#227dab" stroke-width="4" fill="none" marker-end="url(#b)"/>
<path d="M 432 407 L 707 407 L 707 198 L 761 198" stroke="#227dab" stroke-width="4" fill="none" marker-end="url(#b)"/>
<text x="490" y="390" fill="#227dab">5V logic</text><text x="715" y="391" fill="#227dab">UART / GPIO safety</text>
<path d="M 920 176 L 1011 176 L 1011 247" stroke="#227dab" stroke-width="4" fill="none" marker-end="url(#b)"/>
<rect x="64" y="253" width="178" height="80" rx="10" fill="#ffe4e1" stroke="#bb6c5b"/><text x="91" y="286" font-weight="bold">E-stop NC</text><text x="81" y="312">Gate chốt lỗi OFF</text>
<path d="M 242 292 L 943 292" stroke="#b94c4e" stroke-dasharray="10 7" stroke-width="3" marker-end="url(#a)" opacity=".6"/>
<text x="74" y="530" fill="#b94c4e">ĐỎ: rail motor / inhibit độc lập / dây công suất dọc mép ngoài</text>
<text x="74" y="561" fill="#227dab">XANH: 5V logic / UART / encoder / cảm biến — bó dây khác, GND chung theo sơ đồ</text>
</g></svg>'''


def export_viewer(a, data):
    """No CDN, no OBJ fetch, no WebGL dependency: portable orbitable local HTML."""
    model={'solids':[{'name':n,'color':RGB[m],'material':m,'vertices':v,'faces':f}
                     for n,m,(v,f),s in a.solids],
           'dimensions':data['base'],'wheel':data['wheel'],'seller_spec':data['seller_spec'],
           'components':[{'name':p['label'],'xyz':p['xyz']} for p in data['components']]}
    html=r'''<!doctype html>
<html lang="vi"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>AW-Car · Parametric CAD 3D preview v0.3</title>
<style>
:root{font-family:system-ui,Segoe UI,Arial,sans-serif;background:#eff3f8;color:#152b41}
*{box-sizing:border-box}body{margin:0;display:flex;flex-direction:column;min-height:100vh}
header{background:#152d47;color:white;padding:14px 26px;display:flex;align-items:center;justify-content:space-between;gap:15px;flex-wrap:wrap}
header h1{margin:0;font-size:22px}header p{margin:3px 0 0;color:#bdcbda;font-size:13px}
main{display:grid;grid-template-columns:minmax(0,1fr) 280px;min-height:calc(100vh - 88px)}
.stage{position:relative;min-height:680px;background:linear-gradient(#f9fbfe,#e9eff7)}
#scene{display:block;width:100%;height:100%;cursor:grab;touch-action:none}#scene:active{cursor:grabbing}
.tip{position:absolute;bottom:14px;left:18px;border-radius:9px;background:#ffffffda;padding:9px 12px;font-size:13px;pointer-events:none}
aside{padding:20px;background:#fff;border-left:1px solid #dae2ec;overflow:auto}
h2{font-size:17px;margin:0 0 15px}h3{font-size:13px;letter-spacing:.03em;color:#61748a;margin:22px 0 9px}
.buttons{display:flex;gap:7px;flex-wrap:wrap}button{border:1px solid #bbcada;background:#f4f7fb;color:#203e5e;border-radius:8px;padding:9px 12px;cursor:pointer;font-weight:600}
button:hover,button:focus{background:#d9e9fa}.line{display:flex;align-items:center;gap:9px;margin:12px 0;font-size:14px}
.note{font-size:13px;line-height:1.5;color:#455e76}.warn{background:#fff5e5;border-left:3px solid #c47c21;padding:12px;font-size:13px;line-height:1.5}
.swatches{display:grid;grid-template-columns:1fr 1fr;gap:9px}.swatches>div{font-size:12px;display:flex;gap:6px;align-items:center}
.dot{width:12px;height:12px;border-radius:3px;display:inline-block;flex-shrink:0}
@media(max-width:850px){main{display:flex;flex-direction:column}.stage{height:70vh;min-height:400px}aside{border:0;border-top:1px solid #dae2ec}}
</style></head><body>
<header><div><h1>AW-CAR · 3D CAD Layout v0.3</h1><p>Hai PCB phân nhiệm vụ · pin thấp / nguồn riêng / controller gọn · kích thước tạm thời</p></div><strong>KHÔNG DÙNG ĐỂ GIA CÔNG</strong></header>
<main><section class="stage"><canvas id="scene" aria-label="Mô hình xe AW-Car xoay được"></canvas>
<div class="tip">Kéo để xoay · Cuộn chuột / hai ngón để phóng to · Chọn góc nhìn bên phải</div></section>
<aside><h2>Điều khiển mô hình</h2><div class="buttons"><button id="iso">Phối cảnh</button><button id="top">Từ trên</button><button id="side">Nhìn bên</button><button id="front">Phía trước</button></div>
<label class="line"><input id="hideTop" type="checkbox"> Ẩn tấm trên để xem nguồn/pin</label>
<label class="line"><input id="labels" type="checkbox" checked> Nhãn linh kiện</label>
<h3>Thông số bản bố trí (chưa đo)</h3>
<p class="note"><b>Khung tham chiếu:</b> 260 × 155 mm<br><b>Rộng cả lốp:</b> 175 mm (cần xác nhận)<br><b>Bánh:</b> Ø60 mm, rộng 20 mm (giả định)<br><b>Chiều dài cơ sở:</b> 176 mm (giả định)<br><b>Khoảng tâm vệt bánh:</b> 155 mm (giả định)<br><b>Pin:</b> pack 2S1P/BMS nằm giữa tầng dưới<br><b>Bo điều khiển:</b> 150 × 78 mm (concept)<br><b>Bo phân nguồn:</b> 36 × 25 mm (concept)</p>
<h3>Màu phân hệ</h3><div class="swatches">
<div><span class="dot" style="background:#2a71cf"></span>Brain</div><div><span class="dot" style="background:#19a99d"></span>Motion</div>
<div><span class="dot" style="background:#6850ab"></span>FPGA</div><div><span class="dot" style="background:#d14a4f"></span>Driver</div>
<div><span class="dot" style="background:#3771cd"></span>Pin 2S</div><div><span class="dot" style="background:#e09d31"></span>Nguồn</div>
<div><span class="dot" style="background:#e03741"></span>E-stop</div><div><span class="dot" style="background:#32a5e4"></span>Tín hiệu</div>
</div><h3>Giới hạn</h3><div class="warn">Mô tả người bán có hai cách ghi chiều rộng mâu thuẫn: 155 mm tính ngoài bánh và 175 mm tính cả lốp. CAD tạm lấy 155 mm cho khung, 175 mm cả lốp. Hình dáng bo cong được phác lại từ ảnh, không phải bản scan/đo lỗ gá. KHÔNG khoan/cắt theo CAD này.</div>
<p class="note">Sửa <code>layout.json</code>, chạy <code>python hardware/cad/generate_aw_car.py</code> để tạo lại SCAD/OBJ/ảnh. Mạch an toàn chỉ là vùng chức năng, chưa phải schematic.</p></aside></main>
<script>
const MODEL=__MODEL__;
const canvas=document.getElementById('scene'),ctx=canvas.getContext('2d');
const byId=id=>document.getElementById(id);
let yaw=-0.78,pitch=0.59,zoom=1,hideTop=false,showLabels=true;
let moving=false,px=0,py=0,scheduled=false;
function dot(a,b){return a[0]*b[0]+a[1]*b[1]+a[2]*b[2]}
function cross(a,b){return [a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]]}
function norm(v){const r=Math.hypot(...v)||1;return v.map(x=>x/r)}
function camera(){const c=Math.cos(yaw),s=Math.sin(yaw),cp=Math.cos(pitch),sp=Math.sin(pitch);
  const right=[c,s,0],view=[-s*cp,c*cp,sp],up=[s*sp,-c*sp,cp];return {right,view,up}}
function shade(rgb,m){return `rgb(${rgb.map(n=>Math.max(0,Math.min(255,Math.round(n*m+7)))).join(',')})`}
function frame(){scheduled=false;const rect=canvas.getBoundingClientRect(),w=rect.width,h=rect.height;
  const dpi=Math.min(window.devicePixelRatio||1,2),W=Math.round(w*dpi),H=Math.round(h*dpi);
  if(canvas.width!==W||canvas.height!==H){canvas.width=W;canvas.height=H}
  ctx.setTransform(dpi,0,0,dpi,0,0);ctx.clearRect(0,0,w,h);
  const cam=camera(),factor=Math.min(w/345,h/250)*zoom,origin=[w*.5,h*.55];
  function project(p){return [origin[0]+dot(p,cam.right)*factor,origin[1]-dot(p,cam.up)*factor,dot(p,cam.view)]}
  let polys=[];
  const upper=new Set(['CONTROLLER_CARRIER','BRAIN','MOTION','FPGA','DRV_LEFT','DRV_RIGHT','OLED','MIC','SPEAKER','IMU','ESTOP']);
  for(const body of MODEL.solids){if(hideTop&&body.name==='UPPER_ACRYLIC')continue;
    const layer=upper.has(body.name)?2:(body.name==='UPPER_ACRYLIC'?1:0);
    const vs=body.vertices,pts=vs.map(project);
    for(const face of body.faces){const a=vs[face[0]],b=vs[face[1]],c=vs[face[2]];
      const normal=norm(cross(b.map((v,i)=>v-a[i]),c.map((v,i)=>v-a[i])));
      const brightness=.67+.33*Math.max(0,dot(normal,norm([-0.5,-0.3,1])));
      const p=face.map(i=>pts[i]);polys.push({layer,material:body.material,points:p,z:p.reduce((s,v)=>s+v[2],0)/p.length,color:shade(body.color,brightness),alpha:body.material==='plate'?.37:1})}}
  polys.sort((a,b)=>a.layer-b.layer||a.z-b.z);
  for(const poly of polys){const a=poly.points;ctx.beginPath();ctx.moveTo(a[0][0],a[0][1]);for(let i=1;i<a.length;i++)ctx.lineTo(a[i][0],a[i][1]);ctx.closePath();
    ctx.globalAlpha=poly.alpha;ctx.fillStyle=poly.color;ctx.fill();
    if(poly.material!=='plate'){ctx.strokeStyle='rgba(21,35,50,.16)';ctx.lineWidth=.45;ctx.stroke()}
    ctx.globalAlpha=1}
  if(showLabels){ctx.font='600 12px system-ui,Segoe UI,sans-serif';ctx.textBaseline='middle';
    for(const c of MODEL.components){if(c.name.includes('BMS')&&!hideTop)continue;
      const p=project([c.xyz[0],c.xyz[1],c.xyz[2]+10]);const t=c.name;
      const tw=ctx.measureText(t).width+14;const x=p[0]-tw/2,y=p[1]-24;
      ctx.fillStyle='rgba(255,255,255,.89)';ctx.fillRect(x,y,tw,20);ctx.strokeStyle='rgba(61,81,99,.28)';ctx.strokeRect(x,y,tw,20);
      ctx.fillStyle='#1a344f';ctx.fillText(t,x+7,y+10)}}
  ctx.font='13px system-ui,Segoe UI,sans-serif';ctx.fillStyle='#5d7590';ctx.fillText('X: trước âm · Y: trái dương · Z: lên',18,26)
}
function redraw(){if(!scheduled){scheduled=true;requestAnimationFrame(frame)}}
canvas.addEventListener('pointerdown',e=>{moving=true;px=e.clientX;py=e.clientY;canvas.setPointerCapture(e.pointerId)});
canvas.addEventListener('pointerup',()=>{moving=false});canvas.addEventListener('pointercancel',()=>{moving=false});
canvas.addEventListener('pointermove',e=>{if(!moving)return;yaw+=(e.clientX-px)*.008;pitch=Math.max(.08,Math.min(1.52,pitch+(e.clientY-py)*.006));px=e.clientX;py=e.clientY;redraw()});
canvas.addEventListener('wheel',e=>{e.preventDefault();zoom=Math.max(.35,Math.min(3.2,zoom*Math.exp(-e.deltaY*.001)));redraw()},{passive:false});
byId('iso').onclick=()=>{yaw=-.78;pitch=.59;zoom=1;redraw()};
byId('top').onclick=()=>{yaw=0;pitch=Math.PI/2;zoom=1;redraw()};
byId('side').onclick=()=>{yaw=0;pitch=.08;zoom=1;redraw()};
byId('front').onclick=()=>{yaw=Math.PI/2;pitch=.08;zoom=1;redraw()};
byId('hideTop').onchange=e=>{hideTop=e.target.checked;redraw()};
byId('labels').onchange=e=>{showLabels=e.target.checked;redraw()};
new ResizeObserver(redraw).observe(canvas);redraw();
</script></body></html>'''
    return html.replace('__MODEL__',json.dumps(model,separators=(',',':')))


def render_png(a,data):
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        print('Pillow missing: skipping PNG (SCAD/OBJ/SVG still generated)')
        return {}
    import os
    font_path='C:/Windows/Fonts/arial.ttf'
    bold_path='C:/Windows/Fonts/arialbd.ttf'
    def f(size,bold=False):
        try:return ImageFont.truetype(bold_path if bold else font_path,size)
        except OSError:return ImageFont.load_default()
    camera=(-1.35,-1.65,1.32)
    def normalize(v):
        mag=math.sqrt(sum(x*x for x in v));return tuple(x/mag for x in v)
    def dot(a,b):return sum(x*y for x,y in zip(a,b))
    def cross(a,b):return (a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])
    forward=normalize(camera); right=normalize(cross((0,0,1),forward)); up=cross(forward,right)
    light=normalize((-0.4,-0.25,1))
    def projected(v,kind):
        x,y,z=v
        if kind=='top':return (y,-x)
        if kind=='side':return (x,z)
        return dot(v,right),dot(v,up)
    def make(kind):
        W,H=1600,1080
        im=Image.new('RGB',(W,H),(247,250,253)); d=ImageDraw.Draw(im)
        d.rounded_rectangle((25,22,W-25,96),radius=14,fill=(25,50,78))
        title={'iso':'AW-CAR  /  3D CAD V0.3','top':'AW-CAR  /  TOP VIEW (XY)','side':'AW-CAR  /  SIDE VIEW (XZ)'}[kind]
        d.text((55,41),title,font=f(32,True),fill='white')
        d.text((55,118),'PROVISIONAL DIMENSIONS  |  Board envelopes are placeholders  |  All units mm',font=f(19),fill=(86,104,124))
        transparent=ImageDraw.Draw(im,'RGBA')
        triangles=[]
        upper_set={'CONTROLLER_CARRIER','BRAIN','MOTION','FPGA','DRV_LEFT','DRV_RIGHT','OLED','MIC','SPEAKER','IMU','ESTOP'}
        for name,material,(verts,faces),_ in a.solids:
            layer=2 if name in upper_set else (1 if name=='UPPER_ACRYLIC' else 0)
            for face in faces:
                vv=[verts[i] for i in face]
                x=tuple(vv[1][j]-vv[0][j] for j in range(3))
                y=tuple(vv[2][j]-vv[0][j] for j in range(3))
                normal=normalize(cross(x,y)) if len(vv)>=3 else (0,0,1)
                shade=0.72+0.28*max(0,dot(normal,light))
                color=tuple(int(min(255,v*shade+8)) for v in RGB[material])
                depth=sum(dot(v,forward) for v in vv)/len(vv)
                triangles.append((layer,depth,[projected(v,kind) for v in vv],color,material))
        points=[p for _,_,ps,_,_ in triangles for p in ps]
        lo=[min(p[k] for p in points) for k in range(2)]; hi=[max(p[k] for p in points) for k in range(2)]
        avail=(120,182,1480,880)
        width=hi[0]-lo[0];height=hi[1]-lo[1]
        scale=min((avail[2]-avail[0])/width,(avail[3]-avail[1])/height)
        cx=(lo[0]+hi[0])/2;cy=(lo[1]+hi[1])/2
        center=((avail[0]+avail[2])/2,(avail[1]+avail[3])/2)
        def pix(p):return (int(center[0]+(p[0]-cx)*scale),int(center[1]-(p[1]-cy)*scale))
        for layer,depth,ps,color,material in sorted(triangles,key=lambda x:(x[0],x[1])):
            pixels=[pix(p) for p in ps]
            if material=='plate':
                transparent.polygon(pixels,fill=(*color,100))
            else:
                d.polygon(pixels,fill=color)
                if len(ps)<=8:d.line(pixels+[pixels[0]],fill=tuple(max(0,v-19) for v in color),width=1)
        # Compact annotated legend; symbols match approximate routing/placement, not pins.
        parts=[('BATTERY 2S1P','battery'),('Brain / Motion','brain'),('FPGA Nano 9K','fpga'),
               ('DRV8833 x2','driver'),('E-stop + gate','estop'),('Motor rails','wire_motor'),
               ('Signal / UART','wire_signal')]
        for i,(text,key) in enumerate(parts):
            x=52+i*214
            d.rounded_rectangle((x,947,x+199,1004),radius=10,fill=(232,237,245))
            d.ellipse((x+12,964,x+27,979),fill=RGB[key])
            d.text((x+36,959),text,font=f(16,True),fill=(35,48,67))
        d.text((56,1020),'Actual stock chassis, wheel centers, PCB footprints & mounting holes MUST be measured before fabrication.',font=f(18),fill=(153,69,58))
        return im
    output={}
    for kind,fn in [('iso','aw_car_isometric.png'),('top','aw_car_top.png'),('side','aw_car_side.png')]:
        output[fn]=make(kind)
    return output


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--check',action='store_true',help='run geometry audit only; no file writes')
    args=p.parse_args()
    data=json.loads(DATA.read_text(encoding='utf8'))
    report=audit(data)
    print(json.dumps(report,ensure_ascii=False,indent=2))
    if args.check:return 0 if report['status']=='PASS' else 1
    a=build(data)
    scad=export_scad(a,data)
    obj,mtl=export_obj(a)
    for name,content in [('aw_car_assembly.scad',scad),('aw_car_assembly.obj',obj),
                         ('aw_car_assembly.mtl',mtl),('wiring-plan.svg',wire_svg()),
                         ('aw_car_viewer.html',export_viewer(a,data)),
                         ('clearance-report.json',json.dumps(report,indent=2,ensure_ascii=False)+'\n')]:
        (ROOT/name).write_text(content,encoding='utf8')
    for name,im in render_png(a,data).items():im.save(ROOT/name)
    print(f'Generated {len(a.solids)} envelope solids in {ROOT}')
    return 0 if report['status']=='PASS' else 1


if __name__=='__main__':raise SystemExit(main())
