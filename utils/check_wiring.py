"""Check a native KiCad XML netlist against the wiring contract and FPGA CST."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]

def check(path: Path):
    xml = ET.parse(path).getroot()
    actual = {}
    for net in xml.findall('./nets/net'):
        name = net.attrib['name'].lstrip('/')
        for node in net.findall('node'):
            actual[node.attrib['ref'], node.attrib['pin']] = name
    pins = json.loads((ROOT/'data/wiring.json').read_text(encoding='utf-8'))['pins']
    checked = 0
    for pin in pins:
        if pin['net'] is None:
            continue
        key = pin['ref'], pin['pin']
        if actual.get(key) != pin['net']:
            raise ValueError(f'Native netlist mismatch {key}: {actual.get(key)!r} != {pin["net"]!r}')
        checked += 1
    # Independent deployment contract, not derived from the schematic generator.
    required = {
        'spi_mosi': ('SPI_MOSI', 25), 'spi_miso': ('SPI_MISO', 26),
        'spi_sclk': ('SPI_SCLK', 29), 'spi_cs_n': ('SPI_CS_N', 30),
        'enc_right': ('ENC_R_3V3', 28),
        'drv_left_in1': ('L_IN1', 35), 'drv_left_in2': ('L_IN2', 40),
        'drv_right_in1': ('R_IN1', 41), 'drv_right_in2': ('R_IN2', 42),
    }
    cst = (ROOT/'fpga/targets/tang_nano9k/simplev1_nano9k.cst').read_text()
    locations = {name: int(pin) for name, pin in re.findall(r'IO_LOC\s+"([^"]+)"\s+(\d+)\s*;', cst)}
    for port, (net, pin) in required.items():
        if locations.get(port) != pin or actual.get(('U3', 'P'+str(pin))) != net:
            raise ValueError('CST/schematic conflict: '+port)
    for pin in ('GPIO17', 'GPIO18'):
        if ('U2', pin) in actual:
            raise ValueError('Damaged Motion pin used: '+pin)
    return {'pass': True, 'native_netlist_pins_checked': checked, 'cst_connections_checked': len(required),
            'scope': 'logical USB bench interconnect, not a PCB/ERC/power certification'}

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('netlist', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    report = check(args.netlist)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(report))
