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
        'enc_left': ('ENC_L_3V3', 27), 'enc_right': ('ENC_R_3V3', 28),
        'drv_left_in1': ('L_IN1', 35), 'drv_left_in2': ('L_IN2', 40),
        'drv_right_in1': ('R_IN1', 41), 'drv_right_in2': ('R_IN2', 42),
    }
    cst = (ROOT/'fpga/targets/tang_nano9k/simplev1_nano9k.cst').read_text()
    locations = {name: int(pin) for name, pin in re.findall(r'IO_LOC\s+"([^"]+)"\s+(\d+)\s*;', cst)}
    io_types = dict(re.findall(r'IO_PORT\s+"([^"]+)"\s+([^;]+);',cst))
    for port, (net, pin) in required.items():
        if locations.get(port) != pin or actual.get(('U3', 'P'+str(pin))) != net:
            raise ValueError('CST/schematic conflict: '+port)
        if 'IO_TYPE=LVCMOS33' not in io_types.get(port,'') or 'BANK_VCCIO=3.3' not in io_types.get(port,''):
            raise ValueError('External connection is not a 3V3 FPGA pad: '+port)
    for pin in ('GPIO17', 'GPIO18'):
        if ('U2', pin) in actual:
            raise ValueError('Damaged Motion pin used: '+pin)
    # Independent end-to-end harness and rail checks, including future reservations.
    contract={
        'BM_BRAIN_TX': {('U1','GPIO17'),('U2','GPIO14')},
        'BM_MOTION_TX': {('U2','GPIO13'),('U1','GPIO18')},
        'MIC_BCLK': {('U1','GPIO5'),('U6','SCK')},
        'MIC_WS': {('U1','GPIO4'),('U6','WS')},
        'MIC_SD': {('U6','SD'),('U1','GPIO6')},
        'AMP_DIN': {('U1','GPIO7'),('U7','DIN')},
        'AMP_BCLK': {('U1','GPIO15'),('U7','BCLK')},
        'AMP_LRC': {('U1','GPIO16'),('U7','LRC')},
        'OLED_SDA': {('U1','GPIO41'),('U8','SDA')},
        'OLED_SCL': {('U1','GPIO42'),('U8','SCL')},
        'SENSOR_SDA': {('U2','GPIO11'),('U11','SDA'),('U12','SDA')},
        'SENSOR_SCL': {('U2','GPIO12'),('U11','SCL'),('U12','SCL')},
        'EDGE_L_DO': {('U13','DO'),('U2','GPIO8')},
        'EDGE_R_DO': {('U14','DO'),('U2','GPIO9')},
        'STBY_COMMAND': {('U2','GPIO10'),('R1','1'),('R2','1')},
        'STBY_L': {('R1','2'),('U4','STBY')},
        'STBY_R': {('R2','2'),('U5','STBY')},
        'VM_8V4': {('J1','+'),('U15','IN+'),('U16','IN+'),('U4','VM'),('U5','VM')},
        '5V_LOGIC': {('U15','OUT+'),('JP1','1'),('JP2','1'),('JP3','1')},
        '5V_BRAIN': {('JP1','2'),('U1','5V')},
        '5V_MOTION': {('JP2','2'),('U2','5V')},
        '5V_TANG': {('JP3','2'),('U3','5V'),('U9','HV'),('U10','VCC'),('U17','VCC')},
        '5V_AMP': {('U16','OUT+'),('U7','VCC')},
        'SPK_P': {('U7','SPK+'),('LS1','1')},
        'SPK_N': {('U7','SPK-'),('LS1','2')},
    }
    for motor,side,bridge,drv in [('M1','L','A','U4'),('M2','L','B','U4'),('M3','R','A','U5'),('M4','R','B','U5')]:
        for pin in ('1','2'):contract[side+'_'+bridge+'O'+pin]={(drv,bridge+'O'+pin),(motor,pin)}
    for net,expected in contract.items():
        nodes={key for key,name in actual.items() if name==net and not key[0].startswith('#')}
        if nodes!=expected:raise ValueError(f'Harness/rail conflict {net}: {nodes!r} != {expected!r}')
    brain=(ROOT/'esp/brain/main/boards/aw-car/config.h').read_text()
    macros=dict(re.findall(r'#define\s+(\w+)\s+GPIO_NUM_(\d+)',brain))
    expected_brain={'AUDIO_I2S_MIC_GPIO_WS':4,'AUDIO_I2S_MIC_GPIO_SCK':5,'AUDIO_I2S_MIC_GPIO_DIN':6,
        'AUDIO_I2S_SPK_GPIO_DOUT':7,'AUDIO_I2S_SPK_GPIO_BCLK':15,'AUDIO_I2S_SPK_GPIO_LRCK':16,
        'DISPLAY_SDA_PIN':41,'DISPLAY_SCL_PIN':42,'BRAIN_UART_TX':17,'BRAIN_UART_RX':18}
    for name,pin in expected_brain.items():
        if macros.get(name)!=str(pin):raise ValueError('Brain firmware pin changed: '+name)
    motion=(ROOT/'esp/motion/main/runtime.cpp').read_text()
    for field,pin in {'mosi_io_num':15,'miso_io_num':16,'sclk_io_num':4,'spics_io_num':5}.items():
        if not re.search(r'\b'+field+r'\s*=\s*'+str(pin)+r'\s*;',motion):
            raise ValueError('Motion firmware SPI pin changed: '+field)
    if not re.search(r'kDriver\s*=\s*GPIO_NUM_10',motion) or not re.search(r'uart_set_pin\(kUart,13,14,',motion):
        raise ValueError('Motion firmware UART/STBY pin changed')
    return {'pass': True, 'native_netlist_pins_checked': checked, 'cst_connections_checked': len(required),
            'independent_harness_rail_checks': len(contract), 'planned_pins_not_firmware_enabled': True,
            'brain_firmware_gpio_checks':len(expected_brain),'motion_firmware_gpio_checks':7,
            'planned_left_encoder_requires_pull_none':True,
            'scope': 'A3 module interconnect with planned 8.4V power and sensors; not PCB/load certification'}

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
