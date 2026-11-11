"""Pin-level A3 interconnect model. Planned GPIOs are reservations, not firmware.

Coordinates use a 50 mil grid; IDs are logical module pins, never footprint pads.
"""
from collections import defaultdict
import heapq

GRID = 1.27
PARTS = []


def part(ref, title, box, pins, color='#FFFFFF', planned=False):
    # Pin tuples: ID, name, electrical type, side, absolute grid X/Y, net.
    PARTS.append(dict(ref=ref, title=title, box=box, pins=pins,
                      color=color, planned=planned))


part('U1', 'ESP32-S3 BRAIN', (45,63,34,62), [
 ('5V','5V / JP1','power_in','T',52,63,'5V_BRAIN'),
 ('3V3','3V3','power_out','T',70,63,'3V3_BRAIN'),
 ('GPIO18','GPIO18 / UART RX','input','L',45,70,'BM_MOTION_TX'),
 ('GPIO6','GPIO6 / MIC SD','input','L',45,96,'MIC_SD'),
 ('GPIO17','GPIO17 / UART TX','output','R',79,70,'BM_BRAIN_TX'),
 ('GPIO4','GPIO4 / MIC WS','output','R',79,87,'MIC_WS'),
 ('GPIO5','GPIO5 / MIC BCLK','output','R',79,91,'MIC_BCLK'),
 ('GPIO7','GPIO7 / AMP DIN','output','R',79,100,'AMP_DIN'),
 ('GPIO15','GPIO15 / AMP BCLK','output','R',79,104,'AMP_BCLK'),
 ('GPIO16','GPIO16 / AMP LRC','output','R',79,108,'AMP_LRC'),
 ('GPIO41','GPIO41 / OLED SDA','bidirectional','R',79,116,'OLED_SDA'),
 ('GPIO42','GPIO42 / OLED SCL','output','R',79,120,'OLED_SCL'),
 ('GND','GND','power_in','B',62,125,'GND')], '#E9DFFF')
part('U2', 'ESP32-S3 MOTION', (134,63,34,62), [
 ('5V','5V / JP2','power_in','T',140,63,'5V_MOTION'),
 ('3V3','3V3','power_out','T',157,63,'3V3_MOTION'),
 ('GPIO14','GPIO14 / UART RX','input','L',134,70,'BM_BRAIN_TX'),
 ('GPIO16','GPIO16 / MISO','input','L',134,80,'SPI_MISO'),
 ('GPIO13','GPIO13 / UART TX','output','R',168,70,'BM_MOTION_TX'),
 ('GPIO15','GPIO15 / MOSI','output','R',168,84,'SPI_MOSI'),
 ('GPIO4','GPIO4 / SCLK','output','R',168,88,'SPI_SCLK'),
 ('GPIO5','GPIO5 / CS_n','output','R',168,92,'SPI_CS_N'),
 ('GPIO11','GPIO11 / SDA [P]','bidirectional','R',168,102,'SENSOR_SDA'),
 ('GPIO12','GPIO12 / SCL [P]','output','R',168,106,'SENSOR_SCL'),
 ('GPIO10','GPIO10 / STBY','output','R',168,115,'STBY_COMMAND'),
 ('GPIO8','GPIO8 / EDGE L [P]','input','L',134,112,'EDGE_L_DO'),
 ('GPIO9','GPIO9 / EDGE R [P]','input','L',134,118,'EDGE_R_DO'),
 ('GND','GND','power_in','B',151,125,'GND')], '#D9EFFF')
part('U3', 'TANG NANO 9K', (219,63,34,62), [
 ('5V','5V / JP3','power_in','T',226,63,'5V_TANG'),
 ('3V3','3V3','power_out','T',243,63,'3V3_TANG'),
 ('P25','P25 / MOSI','input','L',219,84,'SPI_MOSI'),
 ('P29','P29 / SCLK','input','L',219,88,'SPI_SCLK'),
 ('P30','P30 / CS_n','input','L',219,92,'SPI_CS_N'),
 ('P27','P27 / ENC L [P]','input','L',219,105,'ENC_L_3V3'),
 ('P28','P28 / ENC R','input','L',219,115,'ENC_R_3V3'),
 ('P26','P26 / MISO','output','R',253,70,'SPI_MISO'),
 ('P35','P35 / LEFT IN1','output','R',253,83,'L_IN1'),
 ('P40','P40 / LEFT IN2','output','R',253,91,'L_IN2'),
 ('P41','P41 / RIGHT IN1','output','R',253,106,'R_IN1'),
 ('P42','P42 / RIGHT IN2','output','R',253,114,'R_IN2'),
 ('GND','GND','power_in','B',236,125,'GND')], '#DFF4E7')
for ref,side,y in [('U4','LEFT',64),('U5','RIGHT',109)]:
    n='L' if side=='LEFT' else 'R'
    part(ref, 'DRV8833 '+side, (282,y,21,33), [
     ('VM','VM','power_in','T',292,y,'VM_8V4'),
     ('AIN1','AIN1','input','L',282,y+9,n+'_IN1'),
     ('BIN1','BIN1','input','L',282,y+13,n+'_IN1'),
     ('AIN2','AIN2','input','L',282,y+17,n+'_IN2'),
     ('BIN2','BIN2','input','L',282,y+21,n+'_IN2'),
     ('STBY','STBY/nSLEEP','input','L',282,y+27,'STBY_'+n),
     ('AO1','AO1','output','R',303,y+8,n+'_AO1'),
     ('AO2','AO2','output','R',303,y+12,n+'_AO2'),
     ('BO1','BO1','output','R',303,y+22,n+'_BO1'),
     ('BO2','BO2','output','R',303,y+26,n+'_BO2'),
     ('GND1','GND1','power_in','B',288,y+33,'GND'),
     ('GND2','GND2','power_in','B',298,y+33,'GND')], '#FFF0D5')
for i,n,bridge,y in [(1,'L','A',70),(2,'L','B',84),(3,'R','A',115),(4,'R','B',129)]:
    part('M'+str(i),'TT '+n+('F' if bridge=='A' else 'R'),(315,y,7,11),[
     ('1','+','passive','L',315,y+4,n+'_'+bridge+'O1'),
     ('2','-','passive','L',315,y+8,n+'_'+bridge+'O2')], planned=True)
part('U6','INMP441',(14,146,22,27),[
 ('VDD','3V3','power_in','T',25,146,'3V3_BRAIN'),
 ('SCK','SCK/BCLK','input','L',14,154,'MIC_BCLK'),
 ('WS','WS','input','L',14,159,'MIC_WS'),
 ('LR','L/R = LEFT','input','L',14,167,'GND'),
 ('SD','SD','output','R',36,158,'MIC_SD'),
 ('GND','GND','power_in','B',25,173,'GND')])
part('U7','MAX98357A',(58,151,25,27),[
 ('VCC','5V AMP','power_in','T',71,151,'5V_AMP'),
 ('DIN','DIN','input','L',58,159,'AMP_DIN'),
 ('BCLK','BCLK','input','L',58,163,'AMP_BCLK'),
 ('LRC','LRC','input','L',58,167,'AMP_LRC'),
 ('GAIN','GAIN / OPEN','passive','L',58,172,None),
 ('SD','SD / OPEN','passive','L',58,176,None),
 ('SPK+','SPK+','output','R',83,158,'SPK_P'),
 ('SPK-','SPK-','output','R',83,164,'SPK_N'),
 ('GND','GND','power_in','B',71,178,'GND')])
part('U8','OLED I2C',(98,146,22,22),[
 ('VCC','3V3','power_in','T',109,146,'3V3_BRAIN'),
 ('SDA','SDA','bidirectional','L',98,154,'OLED_SDA'),
 ('SCL','SCL','input','L',98,160,'OLED_SCL'),
 ('GND','GND','power_in','B',109,168,'GND')])
part('LS1','4 ohm / 3 W',(62,195,21,13),[
 ('1','SPK+','passive','L',62,200,'SPK_P'),
 ('2','SPK-','passive','L',62,205,'SPK_N')])
part('U11','MPU6050 [PLAN]',(130,151,25,26),[
 ('VCC','3V3','power_in','T',142,151,'3V3_MOTION'),
 ('SDA','SDA / 0x68','bidirectional','L',130,159,'SENSOR_SDA'),
 ('SCL','SCL','input','L',130,164,'SENSOR_SCL'),
 ('AD0','AD0 = 0','input','L',130,172,'GND'),
 ('INT','INT / NC','output','R',155,159,None),
 ('XDA','XDA / NC','bidirectional','R',155,165,None),
 ('XCL','XCL / NC','output','R',155,171,None),
 ('GND','GND','power_in','B',142,177,'GND')],planned=True)
part('U12','VL53L0X [PLAN]',(170,151,25,26),[
 ('VCC','VIN 3V3','power_in','T',182,151,'3V3_MOTION'),
 ('SDA','SDA / 0x29','bidirectional','L',170,159,'SENSOR_SDA'),
 ('SCL','SCL','input','L',170,164,'SENSOR_SCL'),
 ('XSHUT','XSHUT / NC','input','L',170,172,None),
 ('GPIO1','GPIO1 / NC','output','R',195,172,None),
 ('GND','GND','power_in','B',182,177,'GND')],planned=True)
for ref,n,x in [('U13','L',130),('U14','R',170)]:
    part(ref,'TCRT5000 '+n+' [PLAN]',(x,193,25,20),[
     ('VCC','3V3','power_in','T',x+12,193,'3V3_MOTION'),
     ('DO','DO / EDGE '+n,'output','R',x+25,203,'EDGE_'+n+'_DO'),
     ('AO','AO / NC','output','R',x+25,209,None),
     ('GND','GND','power_in','B',x+12,213,'GND')],planned=True)
for ref,n,y in [('U17','L',152),('U10','R',184)]:
    part(ref,'ENC 1 OUT '+n+(' [PLAN]' if n=='L' else ''),(208,y,21,18),[
     ('VCC','VCC 5V','power_in','T',218,y,'5V_TANG'),
     ('OUT','OUT','output','R',229,y+10,'ENC_'+n+'_5V'),
     ('GND','GND','power_in','B',218,y+18,'GND')],planned=n=='L')
part('U9','LEVEL SHIFT 4CH',(248,138,23,48),[
 ('HV','HV 5V','power_in','T',252,138,'5V_TANG'),
 ('LV','LV 3V3','power_in','T',266,138,'3V3_TANG'),
 ('HV1','HV1 [PLAN]','input','L',248,148,'ENC_L_5V'),
 ('LV1','LV1 [PLAN]','output','R',271,148,'ENC_L_3V3'),
 ('HV2','HV2','input','L',248,170,'ENC_R_5V'),
 ('LV2','LV2','output','R',271,170,'ENC_R_3V3'),
 ('HV3','HV3 / NC','passive','L',248,176,None),
 ('LV3','LV3 / NC','passive','R',271,176,None),
 ('HV4','HV4 / NC','passive','L',248,181,None),
 ('LV4','LV4 / NC','passive','R',271,181,None),
 ('GND1','GND1','power_in','B',253,186,'GND'),
 ('GND2','GND2','power_in','B',266,186,'GND')])
for ref,n,x,y in [('R1','L',260,128),('R2','R',283,157)]:
    part(ref,'1k STBY '+n,(x,y,13,6),[
     ('1','1','passive','L',x,y+3,'STBY_COMMAND'),
     ('2','2','passive','R',x+13,y+3,'STBY_'+n)])
part('J1','BENCH <=8.4V / CC',(10,21,27,25),[
 ('+','+8.4V','power_out','R',37,29,'VM_8V4'),
 ('-','GND','power_out','R',37,39,'GND')],planned=True)
part('U15','DSN6000AUD / 5V',(61,21,38,25),[
 ('IN+','IN+','power_in','L',61,29,'VM_8V4'),
 ('IN-','IN-','passive','L',61,39,'GND'),
 ('OUT+','OUT+ = 5.0V','power_out','R',99,29,'5V_LOGIC'),
 ('OUT-','OUT-','passive','R',99,39,'GND')],planned=True)
part('U16','BUCK AMP 5V / TBD',(175,21,38,25),[
 ('IN+','IN+','power_in','L',175,29,'VM_8V4'),
 ('IN-','IN-','passive','L',175,39,'GND'),
 ('OUT+','OUT+ = 5.0V','power_out','R',213,29,'5V_AMP'),
 ('OUT-','OUT-','passive','R',213,39,'GND')],planned=True)
for ref,net,x,y in [('JP1','5V_BRAIN',112,27),('JP2','5V_MOTION',142,27),('JP3','5V_TANG',232,27)]:
    part(ref,'RUN / USB',(x,y,15,10),[
     ('1','RUN','passive','L',x,y+7,'5V_LOGIC'),
     ('2','5V','passive','R',x+15,y+7,net)],planned=True)


def terminals():
    result={}
    for p in PARTS:
        for number,name,kind,side,x,y,net in p['pins']:
            dx,dy={'L':(-3,0),'R':(3,0),'T':(0,-3),'B':(0,3)}[side]
            result[p['ref'],number]=dict(ref=p['ref'],pin=number,name=name,kind=kind,
                side=side,body=(x,y),point=(x+dx,y+dy),net=net,
                planned=p['planned'] or '[P]' in name or '[PLAN]' in name)
    return result


def route_all(parts=PARTS):
    """Orthogonal pin router. Different nets cross only straight-through, no dots.

    Reserve every pin and avoid bodies; split same-net branch nodes on export.
    The native KiCad netlist is the independent electrical check of the result.
    """
    pins=terminals();blocked=set();reserved={};occupied=defaultdict(dict);edges={}
    for p in parts:
        x,y,w,h=p['box']
        blocked.update((a,b) for a in range(x-1,x+w+2) for b in range(y-1,y+h+2))
    blocked.update((x,y) for x in range(230,329) for y in range(196,222))
    for pin in pins.values():
        x,y=pin['point'];bx,by=pin['body'];dx=(x>bx)-(x<bx);dy=(y>by)-(y<by)
        for step in range(4):
            q=(bx+step*dx,by+step*dy);reserved[q]=pin['net'] or 'NC';blocked.discard(q)
    nets=defaultdict(list)
    for pin in pins.values():
        if pin['net']:nets[pin['net']].append(pin['point'])
    # Short signal harnesses first; supply trees follow in their remaining lanes.
    ordered=sorted(nets,key=lambda n:(n=='GND',n.startswith(('5V','3V3','VM_')),len(nets[n]),n))
    paths=[]
    for net in ordered:
        print('Routing '+net,flush=True)
        connected={nets[net][0]}
        for target in nets[net][1:]:
            queue=[];dist={};parent={}
            start=(*target,2);dist[start]=0
            gx=min(connected,key=lambda g:abs(target[0]-g[0])+abs(target[1]-g[1]))
            heuristic=lambda q:abs(q[0]-gx[0])+abs(q[1]-gx[1])
            heapq.heappush(queue,(heuristic(target),0,start));found=None
            while queue:
                _,cost,state=heapq.heappop(queue)
                if cost!=dist.get(state):continue
                x,y,axis=state
                if (x,y) in connected:found=state;break
                for dx,dy,na in [(1,0,0),(-1,0,0),(0,1,1),(0,-1,1)]:
                    point=(x+dx,y+dy);nx,ny=point
                    if not (8<=nx<=322 and 16<=ny<=219):continue
                    if point in blocked:continue
                    if point in reserved and reserved[point]!=net:continue
                    edge=tuple(sorted(((x,y),point)))
                    if edges.get(edge,net)!=net:continue
                    # No turn/end on another net; crossing straight paths only.
                    cross=False
                    for q,turn_axis in [((x,y),axis),(point,na)]:
                        for other,axes in occupied[q].items():
                            if other==net:continue
                            if axes!={1-na} or (q==(x,y) and turn_axis!=na):break
                            cross=True
                        else:continue
                        break
                    else:
                        turn=0 if axis in (2,na) else 2.5
                        near=sum(bool(occupied[(nx+a,ny+b)]) for a,b in [(1,0),(-1,0),(0,1),(0,-1)])
                        nc=cost+1+turn+(6 if cross else 0)+near*.1
                        ns=(nx,ny,na)
                        if nc<dist.get(ns,1e30):
                            dist[ns]=nc;parent[ns]=state
                            heapq.heappush(queue,(nc+heuristic(point),nc,ns))
            if found is None:raise RuntimeError('No route for '+net+' to '+str(target))
            path=[];cur=found
            while True:
                path.append(cur[:2])
                if cur==start:break
                cur=parent[cur]
            for a,b in zip(path,path[1:]):
                edge=tuple(sorted((a,b)));edges[edge]=net
                axis=0 if a[1]==b[1] else 1
                occupied[a].setdefault(net,set()).add(axis);occupied[b].setdefault(net,set()).add(axis)
            connected.update(path);paths.append((net,path))
    return pins,paths,edges
