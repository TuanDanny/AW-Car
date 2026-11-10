"""Summarize numeric latency_probe records; never retain serial/ASR/network text."""
import argparse
import json
import math
from pathlib import Path
import re

ACTIONS=('forward','backward','left','right')


def distribution(values):
    ordered=sorted(values)
    if not ordered: return None
    def percentile(p):return round(ordered[max(0,math.ceil(len(ordered)*p)-1)]/1000,3)
    return {'n':len(ordered),'p50_ms':percentile(.50),'p95_ms':percentile(.95),
            'p99_ms':percentile(.99),'max_ms':round(ordered[-1]/1000,3)}


def summarize(text,minimum=10):
    parsed=re.findall(r'latency_probe: action=(forward|backward|left|right) dispatch_us=(\d+) confirm_us=(\d+)',text)
    samples={a:[] for a in ACTIONS}
    for action,start,end in parsed:
        start,end=int(start),int(end)
        if 0<=start<=end<=2000000:samples[action].append((start,end))
    report={'scope':'Real phone PointerEvent timestamp to send and matching Motion setpoint STATUS; not physical PWM edge',
            'status_poll_ms':100,'directions':{},'minimum_per_direction':minimum,
            'budget_note':'Proposed diagnostic budgets, not a certified hardware limit',
            'budgets_ms':{'dispatch_p95':10,'status_p95':150,'status_p99':200,'status_max':300},
            'physical_pwm_measured':False,'motor_motion_measured':False}
    enough=all(len(samples[a])>=minimum for a in ACTIONS);within=True
    for action,values in samples.items():
        send=distribution([x[0] for x in values]);confirm=distribution([x[1] for x in values])
        good=bool(send and confirm and send['p95_ms']<=10 and confirm['p95_ms']<=150 and confirm['p99_ms']<=200 and confirm['max_ms']<=300)
        report['directions'][action]={'dispatch':send,'setpoint_status':confirm,'within_proposed_budget':good if len(values)>=minimum else None}
        within=within and good
    report['enough_samples']=enough;report['pass']=within if enough else None
    core=re.findall(r'simple_diag: samples=(\d+) window=(\d+) submit_us_p50=(\d+) p95=(\d+) p99=(\d+) max=(\d+)',text)
    if core:
        n,window,p50,p95,p99,maximum=map(int,core[-1])
        report['motion_before_spi']={'inputs':n,'window':window,'p50_ms':p50/1000,'p95_ms':p95/1000,'p99_ms':p99/1000,'max_ms':maximum/1000,
                                     'within_existing_3ms_10ms_budget':p99<=3000 and maximum<=10000 if n else None}
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('log',type=Path)
    parser.add_argument('--output',type=Path);parser.add_argument('--minimum',type=int,default=10)
    args=parser.parse_args()
    if args.minimum<1:parser.error('minimum must be positive')
    report=summarize(args.log.read_text(errors='replace'),args.minimum)
    rendered=json.dumps(report,indent=2)+'\n'
    if args.output:args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(rendered)
    print(rendered)
