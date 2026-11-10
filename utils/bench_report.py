"""Filter private console logs to command/latency/error evidence. Never copy speech or credentials."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import re

MOTION = re.compile(r'I \((\d+)\) simple_motion: mode=(\w+) gen=(\d+) action=(\w+) duty=(-?\d+)/(-?\d+) spi=(\d+) ack=(\d+) reason=(\w+) rx=(\d+) uart_err=(\d+) spi_err=(\d+)')
DIAG = re.compile(r'simple_diag: samples=(\d+) window=(\d+) submit_us_p50=(\d+) p95=(\d+) p99=(\d+) max=(\d+) heap=(\d+) spi_io=(\d+) frame=(\d+) ack=(\d+) startup=(\d+)')

def summarize(motion: Path, brain: Path | None, after_ms=0, before_ms=None):
    text = motion.read_text(encoding='utf-8', errors='replace')
    if after_ms or before_ms is not None:
        filtered=[]
        for line in text.splitlines():
            stamp=re.search(r'\((\d+)\)',line)
            if stamp and after_ms <= int(stamp[1]) and (before_ms is None or int(stamp[1]) < before_ms):
                filtered.append(line)
        text='\n'.join(filtered)
    rows = []
    for match in MOTION.finditer(text):
        v = match.groups()
        rows.append(dict(at_ms=int(v[0]), mode=v[1], generation=int(v[2]), action=v[3], left=int(v[4]), right=int(v[5]),
                         spi=bool(int(v[6])), ack=int(v[7]), reason=v[8], uart_rx=int(v[9]), uart_errors=int(v[10]), spi_errors=int(v[11])))
    transitions = []
    previous = None
    for row in rows:
        key = row['mode'], row['generation'], row['action'], row['left'], row['right'], row['reason']
        if key != previous:
            transitions.append(row)
            previous = key
    result = {'scope': 'Console command/ACK evidence only. Power/motor state is not inferred. Duty/ACK is not voltage/speed proof',
              'raw_logs_committed': False, 'observations': len(rows), 'transitions': transitions}
    if rows:
        result['last'] = rows[-1]
        result['observed_span_ms'] = rows[-1]['at_ms'] - rows[0]['at_ms']
        result['uart_error_delta'] = rows[-1]['uart_errors']-rows[0]['uart_errors']
        result['spi_error_delta'] = rows[-1]['spi_errors']-rows[0]['spi_errors']
    diagnostics = list(DIAG.finditer(text))
    if diagnostics:
        keys = ['count','window','p50','p95','p99','max','heap','spi_io_errors','spi_frame_errors','spi_ack_errors','spi_startup']
        result['last_diag'] = dict(zip(keys,map(int,diagnostics[-1].groups())))
        result['latency_scope'] = 'Motion accepted input mailbox timestamp to SPI API entry, microseconds; latest256 sample window'
    if brain:
        text = brain.read_text(encoding='utf-8', errors='replace')
        result['brain'] = {'watchdog_events': text.count('Task watchdog got triggered'),
                           'panic_events': text.count('Guru Meditation'), 'backtraces': text.count('Backtrace:'),
                           'fresh_driving_sessions_bound': text.count('driving context bound'),
                           'move_tool_mentions': text.count('% self.car.move'),
                           'rejected_move_callbacks': text.count('Driving context expired/unavailable')}
        frames = re.findall(r'I1 refresh_count=(\d+) max_refresh_us=(\d+)',text)
        if frames:
            result['brain']['last_oled'] = dict(frames=int(frames[-1][0]),max_refresh_us=int(frames[-1][1]))
    return result

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--motion',type=Path,required=True)
    parser.add_argument('--brain',type=Path)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--motion-after-ms',type=int,default=0)
    parser.add_argument('--motion-before-ms',type=int)
    args = parser.parse_args()
    report = summarize(args.motion,args.brain,args.motion_after_ms,args.motion_before_ms)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k!='transitions'},indent=2))
