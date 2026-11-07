"""Generate the single-sheet, editable AW-Car KiCad connection draft.

This is a wiring drawing, not a PCB or a completed safety-gate design.
Logical GPIO/package IDs are deliberately retained, never guessed header pads.
Existing editable sources are protected; regenerate to --output for review first.
"""
import argparse
from collections import defaultdict
import heapq
import itertools
import json
from pathlib import Path
import re
import shutil
import tempfile
import uuid

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "hardware/pcb"
NS = uuid.UUID("35da800e-594c-4b8d-9679-0969abeb6e08")
GRID = 1.27
DIRS = ((1, 0), (0, 1), (-1, 0), (0, -1))


def uid(name):
    return str(uuid.uuid5(NS, name))


def q(value):
    return json.dumps(str(value), ensure_ascii=False)


def snap(n):
    return round(round(n / GRID) * GRID, 4)


def cell(point):
    return tuple(round(v / GRID) for v in point)


def mm(point):
    return tuple(round(v * GRID, 4) for v in point)


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


# All coordinates below describe graphics only. Pin IDs/names/types/nets come
# from the versioned manifest exported from the previous KiCad drawing.
# The axes are symbol-local: positive Y is up; L/R face the connected module.
PORTS = {
    "Brain_Logical": (46, {
        "5V": ("L", 50.8), "3V3": ("L", 45.72), "GND": ("L", 40.64),
        "GPIO4": ("L", 25.4), "GPIO5": ("L", 20.32), "GPIO6": ("L", 15.24),
        "GPIO41": ("L", 0), "GPIO42": ("L", -5.08),
        "GPIO7": ("L", -20.32), "GPIO15": ("L", -25.4), "GPIO16": ("L", -30.48),
        "GPIO17": ("R", 5.08), "GPIO18": ("R", 0)}),
    "Motion_Logical": (50, {
        "5V": ("L", 50.8), "3V3": ("L", 45.72), "GND": ("L", 40.64),
        "GPIO14": ("L", 5.08), "GPIO13": ("L", 0),
        "GPIO15": ("R", 35.56), "GPIO16": ("R", 30.48),
        "GPIO4": ("R", 25.4), "GPIO5": ("R", 20.32), "GPIO6": ("R", 15.24),
        "GPIO7": ("R", 10.16), "GPIO8": ("R", 5.08), "GPIO9": ("R", 0),
        "GPIO10": ("R", -12.7)}),
    "Tang_Logical": (62, {
        "5V": ("L", 60.96), "3V3": ("L", 55.88), "GND": ("L", 50.8),
        "P25": ("L", 35.56), "P26": ("L", 30.48), "P29": ("L", 25.4),
        "P30": ("L", 20.32), "P48": ("L", 15.24), "P51": ("L", 10.16),
        "P33": ("L", 5.08), "P34": ("L", 0),
        "P27": ("L", -50.8), "P28": ("L", -55.88),
        "P35": ("R", 25.4), "P40": ("R", 20.32),
        "P41": ("R", -15.24), "P42": ("R", -20.32), "P49": ("R", -35.56)}),
    "MIC": (32, {"1": ("L", 20.32), "2": ("L", 15.24), "6": ("L", -12.7),
        "4": ("R", 5.08), "3": ("R", 0), "5": ("R", -5.08)}),
    "OLED": (30, {"2": ("L", 12.7), "1": ("L", 7.62),
        "4": ("R", 2.54), "3": ("R", -2.54)}),
    "AMP": (38, {"VCC": ("L", 25.4), "GND": ("L", 20.32),
        "DIN": ("R", 15.24), "BCLK": ("R", 10.16), "LRC": ("R", 5.08),
        "SPK+": ("L", -5.08), "SPK-": ("L", -10.16),
        "GAIN": ("R", -10.16), "SD": ("R", -15.24)}),
    "DRV_Module_Logical": (36, {"VM": ("L", 25.4), "GND": ("L", 20.32),
        "AIN1": ("L", 12.7), "BIN1": ("L", 7.62),
        "AIN2": ("L", 2.54), "BIN2": ("L", -2.54), "STBY": ("L", -15.24),
        "AOUT1": ("R", 12.7), "AOUT2": ("R", 7.62),
        "BOUT1": ("R", -7.62), "BOUT2": ("R", -12.7)}),
    "Motor": (26, {"1": ("L", 2.54), "2": ("L", -2.54)}),
    "Speaker": (28, {"1": ("R", 2.54), "2": ("R", -2.54)}),
    "Gate_Interface": (54, {"1": ("L", 12.7), "2": ("L", 7.62), "3": ("L", 2.54),
        "4": ("R", 12.7), "5": ("R", 7.62), "6": ("R", -2.54), "7": ("L", -10.16)}),
    "Encoder": (30, {"VCC": ("L", 10.16), "GND": ("L", 5.08), "OUT": ("R", 0)}),
    "LVC2G17": (32, {"5": ("L", 15.24), "2": ("L", 10.16),
        "1": ("L", 0), "3": ("L", -5.08), "6": ("R", 0), "4": ("R", -5.08)}),
    "Sensor": (28, {"1": ("L", 12.7), "2": ("L", 7.62),
        "3": ("R", 2.54), "4": ("R", -2.54)}),
    "Expansion": (52, {"1": ("L", 10.16), "2": ("L", 5.08),
        "3": ("R", 10.16), "4": ("R", 5.08), "5": ("L", -7.62)}),
    "Pack": (36, {"1": ("R", 5.08), "2": ("R", -5.08)}),
    "DSN6000AUD": (42, {"IN+": ("L", 5.08), "IN-": ("L", -5.08),
        "OUT+": ("R", 5.08), "OUT-": ("R", -5.08)}),
    "Testpoint": (12, {"1": ("L", 0)}),
}

POSITIONS = {
    "J30": (70, 65), "F1": (130, 60), "SW1": (190, 60), "U11": (290, 65), "TP3": (380, 60),
    "U1": (250, 235), "U2": (400, 235), "U3": (580, 235),
    "J2": (95, 215), "J1": (180, 252.78), "U6": (135, 295), "J4": (50, 302.62),
    "U4": (710, 185), "U5": (710, 300),
    "J5": (790, 174.84), "J6": (790, 205.32), "J7": (790, 289.84), "J8": (790, 320.32),
    "U7": (410, 330), "U8": (410, 370.84), "U9": (490, 335), "C9": (535, 380),
    "J20": (135, 385), "J21": (135, 435), "J22": (270, 380), "J23": (270, 430.16),
    "U10": (360, 405), "C10": (410, 405), "J24": (240, 490), "J9": (495, 435),
    "TP1": (350, 300), "TP2": (570, 315),
}
for start, x in ((100, 640), (110, 770)):
    POSITIONS.update({f"Q{start+1}": (x, 470), f"Q{start+2}": (x-45.72, 485.24),
        f"R{start+1}": (x-15.24, 449.68), f"R{start+2}": (x+2.54, 449.68),
        f"R{start+3}": (x-60.96, 470), f"R{start+4}": (x-53.34, 502.26)})


def module(part):
    name = part["symbol"]
    width, ports = PORTS[name]
    width = snap(width / 2) * 2
    height = 2 * (max(abs(v[1]) for v in ports.values()) + 5.08)
    raw = [f'(symbol "AWCAR:{name}" (pin_names (offset 1)) (in_bom yes) (on_board yes)',
        f'(property "Reference" "U" (at 0 {snap(height/2+5.08)} 0) {effects()})',
        f'(property "Value" {q(name)} (at 0 {snap(height/2+2.54)} 0) {effects()})',
        f'(symbol "{name}_0_1" (rectangle (start {-width/2:g} {height/2:g}) '
        f'(end {width/2:g} {-height/2:g}) (stroke (width .254) (type default)) (fill (type background))))',
        f'(symbol "{name}_1_1"']
    geometry = {}
    for pin in part["pins"]:
        number = pin["number"]
        side, y = ports[number]
        x, angle = (-width/2-2.54, 0) if side == "L" else (width/2+2.54, 180)
        geometry[number] = x, snap(y), angle
        raw.append(f'(pin {pin["kind"]} {pin["shape"]} (at {x:g} {snap(y):g} {angle}) (length 2.54) '
            f'(name {q(pin["name"])} {effects(.9)}) (number {q(number)} {effects(.75)}))')
    raw.append('))')
    return "\n".join(raw), geometry, width, height


class Router:
    """Orthogonal signal wires, with straight unjoined crossings only.

    The drawing is compressed before serialization: unrelated crossings must
    never become wire endpoints/junctions. KiCad's exported netlist is the
    independent final check, not this router's own graph.
    """
    def __init__(self):
        self.blocked = set()
        self.reserved = {}
        self.terminals = set()
        self.graph = defaultdict(lambda: defaultdict(set))
        self.at = defaultdict(set)

    def rectangle(self, x1, y1, x2, y2):
        a, b = cell((x1, y1)), cell((x2, y2))
        self.blocked.update((x, y) for x in range(a[0], b[0]+1) for y in range(a[1], b[1]+1))

    def add(self, net, a, b):
        if a == b:
            return
        dx, dy = b[0]-a[0], b[1]-a[1]
        if dx and dy:
            raise ValueError(f"Nonorthogonal wire {net}: {a} {b}")
        direction = (0 if dx == 0 else (1 if dx > 0 else -1), 0 if dy == 0 else (1 if dy > 0 else -1))
        for _ in range(abs(dx)+abs(dy)):
            nxt = a[0]+direction[0], a[1]+direction[1]
            self.graph[net][a].add(nxt)
            self.graph[net][nxt].add(a)
            self.at[a].add(net)
            self.at[nxt].add(net)
            a = nxt

    def route(self, net, start, targets):
        targets = set(targets)
        if start in targets:
            return
        serial = itertools.count()
        def distance(p):
            return min(abs(p[0]-t[0])+abs(p[1]-t[1]) for t in targets)
        queue = [(distance(start), 0, next(serial), start, -1)]
        cost, parent = {(start, -1): 0}, {}
        end = None
        while queue:
            _, g, _, p, previous = heapq.heappop(queue)
            if g != cost[(p, previous)]:
                continue
            if p in targets and not self.at[p]-{net}:
                end = p, previous
                break
            for direction, (dx, dy) in enumerate(DIRS):
                if previous >= 0 and direction == (previous+2) % 4:
                    continue
                if self.at[p]-{net} and direction != previous:
                    continue
                nxt = p[0]+dx, p[1]+dy
                if not (16 <= nxt[0] <= 642 and 28 <= nxt[1] <= 416):
                    continue
                if nxt in self.blocked or self.reserved.get(nxt, net) != net:
                    continue
                if nxt in self.reserved and nxt not in self.terminals:
                    continue
                others = self.at[nxt]-{net}
                if others:
                    if len(others) > 1 or net in self.at[nxt] or nxt in targets:
                        continue
                    # Cross an existing straight run perpendicularly, never a corner.
                    neighbors = self.graph[next(iter(others))][nxt]
                    vecs = {(n[0]-nxt[0], n[1]-nxt[1]) for n in neighbors}
                    if len(vecs) != 2 or (-dx, -dy) in vecs or (dx, dy) in vecs:
                        continue
                    v1, v2 = tuple(vecs)
                    if v1 != (-v2[0], -v2[1]):
                        continue
                score = g + 1 + (8 if previous >= 0 and direction != previous else 0) + (4 if others else 0)
                state = nxt, direction
                if score < cost.get(state, float("inf")):
                    cost[state] = score
                    parent[state] = p, previous
                    heapq.heappush(queue, (score+distance(nxt), score, next(serial), nxt, direction))
            if len(cost) > 650000:
                raise ValueError(f"Routing search exhausted: {net}")
        if end is None:
            raise ValueError(f"No wire route: {net} from {mm(start)}")
        path = [end[0]]
        while end in parent:
            end = parent[end]
            path.append(end[0])
        for a, b in zip(path, path[1:]):
            self.add(net, a, b)

    def segments(self):
        for net, graph in self.graph.items():
            seen = set()
            def corner(p):
                ns = graph[p]
                return len(ns) != 2 or len({n[0] for n in ns}) != 1 and len({n[1] for n in ns}) != 1
            for a in list(graph):
                if not corner(a):
                    continue
                for b in graph[a]:
                    edge = frozenset((a, b))
                    if edge in seen:
                        continue
                    seen.add(edge)
                    p, previous = b, a
                    while not corner(p):
                        nxt = next(n for n in graph[p] if n != previous)
                        seen.add(frozenset((p, nxt)))
                        previous, p = p, nxt
                    yield net, mm(a), mm(p)


class Sheet:
    def __init__(self):
        self.items, self.symbols, self.nodes, self.stubs = [], {}, {}, {}
        self.router = Router()
        self.counter = itertools.count()

    def add(self, kind, text):
        self.items.append(text + f' (uuid {q(uid(kind+str(next(self.counter))))}))')

    def text(self, text, x, y, size=1.15):
        self.add("text", f'(text {q(text)} (at {snap(x):g} {snap(y):g} 0) {effects(size, "(justify left)")}')
        self.router.rectangle(x, y-size, x+len(text)*size*.62, y+size)

    def label(self, net, point, angle=0):
        x, y = mm(point)
        justify = "(justify right bottom)" if angle == 180 else "(justify left bottom)"
        if self.router.at[point] != {net}:
            raise ValueError(f"Label on unrelated crossing: {net}")
        self.router.reserved[point] = net
        self.router.terminals.add(point)
        self.add("label", f'(label {q(net)} (at {x:g} {y:g} {angle}) {effects(.85, justify)}')

    def part(self, part, raw, geometry, size):
        ref, name = part["ref"], part["symbol"]
        self.symbols[name] = raw
        x, y = map(snap, POSITIONS[ref])
        width, height = size
        if name in ("R", "C", "NPN", "Fuse", "Switch"):
            self.router.rectangle(x-width/2, y-height/2, x+width/2, y+height/2)
            if name == "Switch":
                self.router.rectangle(x-22.86, y-12.7, x+22.86, y-6.35)
            else:
                self.router.rectangle(x+6.35, y-2.54, x+17.78, y+2.54)
        else:
            self.router.rectangle(x-width/2-1.27, y-height/2-8.89, x+width/2+1.27, y+height/2+1.27)
        def prop(key, val, yy):
            return f'(property {q(key)} {q(val)} (at {x:g} {yy:g} 0) {effects(1)})'
        # Long values remain searchable metadata; concise visible labels fit each block.
        values = {"J9": "Safety gate interface - REQUIRED", "J24": "Future Motion GPIO - TBD",
            "U1": "ESP32-S3 Brain", "U2": "ESP32-S3 Motion", "U3": "Tang Nano 9K (package IDs)",
            "J30": "2S PROTECTED pack", "SW1": "MAIN switch - rating TBD", "TP3": "5V TEST before boards"}
        visible = values.get(ref, part["value"])
        if ref.startswith("Q"):
            visible = "2N3904*"
        if ref in ("J20", "J21"):
            visible = "MPU6050" if ref == "J20" else "VL53L0X blue"
        if ref in ("U6", "U9", "U10", "U11"):
            visible = {"U6": "MAX98357A", "U9": "SN74LVC2G17*", "U10": "SN74LVC2G17*", "U11": "DSN6000AUD"}[ref]
        if ref == "J1":
            visible = "OLED 0.96 I2C"
        if ref == "TP1": visible = "Motion 3V3"
        if ref == "TP2": visible = "Tang 3V3"
        # Standard discrete graphics use labels to the right, leaving their pins clear.
        if name in ("R", "C", "NPN", "Fuse", "Switch"):
            prop_ref = f'(property "Reference" {q(ref)} (at {x+6.35:g} {y-1.27:g} 0) {effects(.9, "(justify left)")})'
            prop_val = f'(property "Value" {q(visible)} (at {x+6.35:g} {y+1.27:g} 0) {effects(.9, "(justify left)")})'
            if name == "Switch":
                prop_ref, prop_val = prop("Reference", ref, y-10.16), prop("Value", visible, y-7.62)
        else:
            prop_ref = prop("Reference", ref, y-height/2-5.08)
            prop_val = prop("Value", visible, y-height/2-2.54)
        inst = [f'(symbol (lib_id "AWCAR:{name}") (at {x:g} {y:g} 0) (unit 1)',
            '(in_bom yes) (on_board yes) (dnp no)', f'(uuid {q(uid(ref))})', prop_ref, prop_val,
            f'(property "Footprint" "" (at {x:g} {y:g} 0) {effects(.9, "(hide yes)")})',
            f'(property "Review_Status" "DRAFT_NOT_FOR_PCB" (at {x:g} {y:g} 0) {effects(.9, "(hide yes)")})',
            f'(property "Description" {q(part["value"])} (at {x:g} {y:g} 0) {effects(.9, "(hide yes)")})']
        for key, val in part["properties"].items():
            inst.append(f'(property {q(key)} {q(val)} (at {x:g} {y:g} 0) {effects(.9, "(hide yes)")})')
        for number, (px, py, angle) in geometry.items():
            point = cell((x+px, y-py))
            self.nodes[ref, number] = point
            inst.append(f'(pin {q(number)} (uuid {q(uid(ref+number))}))')
            net = part["nets"].get(number)
            if not net or net.startswith("unconnected-"):
                xx, yy = mm(point)
                self.add("nc", f'(no_connect (at {xx:g} {yy:g})')
                self.router.reserved[point] = "NC"
                continue
            # Pin orientation points inward; extend outward in the opposite direction.
            direction = {0: (-1, 0), 180: (1, 0), 90: (0, 1), 270: (0, -1)}[round(angle)]
            end = point[0]+4*direction[0], point[1]+4*direction[1]
            self.stubs[ref, number] = end
            self.router.terminals.add(end)
            self.router.add(net, point, end)
            for i in range(5):
                self.router.reserved[(point[0]+i*direction[0], point[1]+i*direction[1])] = net
        inst.append(f'(instances (project "aw_car" (path {q("/"+uid("aw_car"))} '
            f'(reference {q(ref)}) (unit 1)))))')
        self.items.append("\n".join(inst))

    def connect(self, manifest):
        power = {"GND", "3V3_BRAIN", "3V3_MOTION", "3V3_TANG", "3V3_SENSORS_TBD", "VM_MOTOR",
            "5V_SENSOR_SOURCE_TBD", "5V_BRAIN_SOURCE_TBD", "5V_MOTION_SOURCE_TBD",
            "5V_TANG_SOURCE_TBD", "5V_AMP_SOURCE_TBD"}
        preferred = ["BRN_TX_MTN_RX", "MTN_TX_BRN_RX", "MTN_TX_FPGA_RX", "FPGA_TX_MTN_RX",
            "MOTION_PERMIT", "RECOVERY_REQ", "RECOVERY_ACK", "FPGA_PERMIT", "SAFETY_OK", "GATE_FAULT_N",
            "DRV_L_IN1", "DRV_L_IN2", "DRV_R_IN1", "DRV_R_IN2"]
        nets = manifest["expected_nets"]
        order = preferred + sorted(set(nets)-set(preferred))
        for net in order:
            if net.startswith("unconnected-"):
                continue
            pins = [tuple(p) for p in nets[net]]
            ends = [self.stubs[p] for p in pins]
            if net in power:
                if net == "VM_MOTOR":
                    self.router.route(net, self.stubs["U11", "IN+"], [self.stubs["SW1", "2"]])
                for p, end in zip(pins, ends):
                    pin = self.nodes[p]
                    # Labels on the far end of short power stubs, pointing away from body.
                    self.label(net, end, 180 if end[0] < pin[0] else 0)
                continue
            # Join closest endpoints first; long branches then meet the existing tree.
            a, b = min(itertools.combinations(range(len(ends)), 2),
                key=lambda ij: abs(ends[ij[0]][0]-ends[ij[1]][0])+abs(ends[ij[0]][1]-ends[ij[1]][1]))
            for i in [b] + [j for j in range(len(ends)) if j not in (a, b)]:
                # Exclude disconnected stubs from target set; every wire has a physical path.
                targets = set()
                frontier = [ends[a]]
                while frontier:
                    p = frontier.pop()
                    if p in targets:
                        continue
                    targets.add(p)
                    frontier.extend(self.router.graph[net][p]-targets)
                targets = {p for p in targets if p not in self.router.reserved or p in self.router.terminals}
                self.router.route(net, ends[i], targets)
            # KiCad already names discrete base nodes from their transistor pin.
            # Avoid redundant auto-net text overlapping small transistor graphics.
            if net.startswith("Net-("):
                continue
            # Put the name on the longest horizontal run, away from module labels.
            runs = [(p, z) for nn, p, z in self.router.segments() if nn == net and p[1] == z[1]]
            if runs:
                p, z = max(runs, key=lambda pair: abs(pair[0][0]-pair[1][0]))
                left, right = sorted((cell(p), cell(z)))
                candidates = [(x, left[1]) for x in range(left[0]+1, right[0])]
                anchor = next((p for p in candidates if self.router.at[p] == {net}), ends[a])
                self.label(net, anchor)
            else:
                self.label(net, ends[a])

    def save(self, output):
        for net, a, b in self.router.segments():
            self.add("wire", f'(wire (pts (xy {a[0]:g} {a[1]:g}) (xy {b[0]:g} {b[1]:g})) '
                '(stroke (width 0) (type default))')
        for net, graph in self.router.graph.items():
            for p, neighbors in graph.items():
                if len(neighbors) > 2:
                    if self.router.at[p] != {net}:
                        raise ValueError(f"Junction on unrelated crossing: {net}")
                    x, y = mm(p)
                    self.add("junction", f'(junction (at {x:g} {y:g}) (diameter 0) (color 0 0 0 0)')
        raw = ['(kicad_sch (version 20250114) (generator "eeschema") (generator_version "10.0")',
            f'(uuid {q(uid("aw_car"))}) (paper "A1")',
            '(title_block (title "AW-CAR - OVERALL WIRING / SO DO DAU NOI CHUNG") '
            '(date "2026-11-07") (rev "0.2 CONNECTION DRAFT") (company "AW-Car") '
            '(comment 1 "ONE SHEET - REMOVABLE MODULES - PCB DEFERRED") '
            '(comment 2 "Logical GPIO/package IDs; header pad assignment pending"))',
            '(lib_symbols', *[self.symbols[n] for n in sorted(self.symbols)], ')',
            *self.items, '(embedded_fonts no))']
        (output/"aw_car.kicad_sch").write_text("\n".join(raw)+"\n", encoding="utf-8", newline="\n")
        library = ['(kicad_symbol_lib (version 20250114) (generator "kicad_symbol_editor")']
        library += [raw.replace(f'"AWCAR:{name}"', q(name), 1) for name, raw in sorted(self.symbols.items())]
        (output/"aw_car.kicad_sym").write_text("\n".join(library)+")\n", encoding="utf-8", newline="\n")


def generate(kicad_root, output, overwrite=False):
    output = output.resolve()
    existing = [p for p in output.glob("*") if p.suffix in (".kicad_sch", ".kicad_sym", ".kicad_pro", ".lib") or p.name == "sym-lib-table"]
    if existing and not overwrite:
        raise ValueError("Existing editable KiCad sources: refusing to overwrite. Use --output for a candidate, or --overwrite after reviewing manual edits (backup preserved).")
    if existing:
        parent = ROOT/"build/kicad-source-backups"
        parent.mkdir(parents=True, exist_ok=True)
        backup = Path(tempfile.mkdtemp(prefix="before-regenerate-", dir=parent))
        for path in existing:
            shutil.copy2(path, backup/path.name)
        print(f"Previous editable source preserved at {backup}")
    output.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((ROOT/"docs/awcar-schematic-parts.json").read_text(encoding="utf-8"))
    sheet = Sheet()
    for p in manifest["parts"]:
        name = p["symbol"]
        if name in PORTS:
            raw, geometry, width, height = module(p)
        else:
            source, original = {"R": ("Device", "R"), "C": ("Device", "C"), "Fuse": ("Device", "Fuse"),
                "Switch": ("Switch", "SW_SPST"), "NPN": ("Transistor_BJT", "Q_NPN_EBC")}[name]
            raw = standard(kicad_root/f"share/kicad/symbols/{source}.kicad_sym", original, name)
            geometry = {pin["number"]: (pin["x"], pin["y"], pin["angle"]) for pin in p["pins"]}
            width, height = (5.08, 5.08) if name != "NPN" else (7.62, 7.62)
        sheet.part(p, raw, geometry, (width, height))
    for text, x, y, size in [
        ("AW-CAR | SO DO DAU NOI CHUNG | 1 TRANG", 25, 20, 2.8),
        ("Connection review: visible signal wires; power labels share named rails. Module sockets / harness order still to be verified.", 25, 28, 1.3),
        ("01  NGUON 2S + DSN6000AUD", 25, 40, 1.7),
        ("BMS 2S + charger 8.4V: NOT SELECTED. J30 is protected pack output only; not raw cells / not charger input.", 25, 97, 1.15),
        ("5V_DSN_UNVERIFIED is TEST ONLY. Do not join it to board 5V/USB until source isolation is reviewed.", 25, 103, 1.15),
        ("02  AUDIO / OLED", 25, 145, 1.7),
        ("03  BRAIN <-> MOTION <-> FPGA | 3.3V LOGIC", 250, 125, 1.7),
        ("Motion GPIO17/18 DAMAGED - NEVER USE. UART uses GPIO13/14 to Brain and GPIO15/16 to Tang.", 250, 133, 1.1),
        ("04  DRV8833 x2 / 4 MOTOR TT 9V", 640, 130, 1.6),
        ("Each motor has its own bridge. AIN/BIN share logic only.", 640, 138, 1.05),
        ("No parallel H-bridge outputs. STBY = nSLEEP: verify module.", 640, 143, 1.05),
        ("05  CAM BIEN / ENCODER 1 OUT", 25, 350, 1.7),
        ("Sensor supply / GPIO / physical connector order pending.", 25, 358, 1.1),
        ("06  SAFETY GATE INTERFACE + STBY CANDIDATE", 445, 388, 1.6),
        ("J9 is a REQUIRED UNBUILT gate/latch/watchdog/E-stop interface, NOT an implemented gate.", 445, 395, 1.05),
        ("* NPN + input-buffer candidates: generic models only; packages, ratings and real STBY circuit unverified.", 445, 528, 1.05),
        ("CHUA CHOT PCB: connectors/pads, BMS/charger/fuse, USB isolation and full independent safety gate.", 25, 548, 1.35),
        ("E-stop must disable motor drive and latch until controlled reset; Brain/OLED/Dashboard remain powered. No motor-power test authorization.", 25, 555, 1.15),
        ("Logic labels are NOT physical header pad numbers. Motor VM and USB/5V must never reach GPIO. Ground common; BTL speaker floats.", 25, 562, 1.15),
    ]:
        sheet.text(text, x, y, size)
    sheet.connect(manifest)
    sheet.save(output)
    (output/"aw_car.kicad_pro").write_text(json.dumps({"meta": {"filename": "aw_car.kicad_pro", "version": 1},
        "text_variables": {"REVIEW_STATUS": "DRAFT_NOT_FOR_PCB"}}, indent=2)+"\n", encoding="utf-8", newline="\n")
    (output/"sym-lib-table").write_text('(sym_lib_table (version 7) (lib (name "AWCAR") (type "KiCad") '
        '(uri "${KIPRJMOD}/aw_car.kicad_sym") (options "") (descr "AW-Car logical module IDs, NOT header pad numbers")))\n', encoding="utf-8", newline="\n")
    (output/"generic-clamp.lib").write_text('* Generic approximations only; NOT manufacturer-validated 2N3904/DRV8833 models.\n'
        '.model QGEN NPN(IS=6.7f BF=40 VAF=80 IKF=.1 CJE=8p CJC=4p TF=.3n)\n'
        '.model DZGEN D(BV=6.5 IBV=1u IS=1f)\n', encoding="ascii", newline="\n")
    print(f"Generated one A1 native KiCad wiring sheet, {len(manifest['parts'])} parts, at {output}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kicad-root", type=Path, default=Path("D:/APP/KiCad"))
    parser.add_argument("--output", type=Path, default=OUT)
    parser.add_argument("--overwrite", action="store_true", help="regenerate editable sources with a build backup")
    args = parser.parse_args()
    generate(args.kicad_root, args.output, args.overwrite)
