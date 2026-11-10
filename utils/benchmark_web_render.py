"""Compare real baseline/candidate HTML on the localhost native simulator only.

Idle STATUS/render work, not phone Wi-Fi, PWM latency or motor movement.
Separate baseline/candidate servers serve actual HTTP and native WebSockets.
"""
import argparse
import json
import math
from pathlib import Path
import subprocess
from urllib.request import urlopen

ROOT=Path(__file__).resolve().parents[1]


def distribution(values):
    ordered=sorted(values)
    if not ordered:return None
    def p(q):return round(ordered[max(0,math.ceil(len(ordered)*q)-1)],4)
    return {'n':len(ordered),'p50_ms':p(.5),'p95_ms':p(.95),'max_ms':p(1)}


INSTRUMENT=r"""(() => {
  window.__renderCost={frames:0,bytes:0,callback_ms:[]};
  const original=EventTarget.prototype.addEventListener;
  EventTarget.prototype.addEventListener=function(type,listener,options) {
    if(this instanceof WebSocket && type==='message' && typeof listener==='function') {
      const wrapped=function(event) {
        const start=performance.now();
        try { return listener.call(this,event); }
        finally {
          const elapsed=performance.now()-start;
          try { if(JSON.parse(event.data).t==='status') {
            __renderCost.frames++;__renderCost.bytes+=new TextEncoder().encode(event.data).length;
            __renderCost.callback_ms.push(elapsed);
          } } catch {}
        }
      };
      return original.call(this,type,wrapped,options);
    }
    return original.call(this,type,listener,options);
  };
})();"""


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port',type=int,default=8798)
    parser.add_argument('--baseline-port',type=int,default=8800)
    parser.add_argument('--baseline-ref',default='97f9fcd')
    parser.add_argument('--repeats',type=int,default=2)
    parser.add_argument('--idle-ms',type=int,default=3000)
    parser.add_argument('--output',type=Path,default=ROOT/'build/review/web-render-ab.json')
    args=parser.parse_args()
    if args.repeats<1 or args.idle_ms<1000:parser.error('Use positive repeats and idle-ms >=1000')
    if args.port==args.baseline_port:parser.error('Use separate simulator ports; there is one WS owner per server')
    urls={'baseline':f'http://127.0.0.1:{args.baseline_port}/','candidate':f'http://127.0.0.1:{args.port}/'}
    before=subprocess.check_output(['git','show',args.baseline_ref+':esp/motion/web/index.html'],cwd=ROOT)
    after=(ROOT/'esp/motion/web/index.html').read_bytes()
    for mode,url in urls.items():
        with urlopen(url+'sim/state',timeout=3) as response:
            if json.load(response).get('simulator') is not True:raise RuntimeError('Refusing non-simulator endpoint')
        with urlopen(url,timeout=3) as response:served=response.read()
        expected=before if mode=='baseline' else after
        if served.replace(b'\r\n',b'\n')!=expected.replace(b'\r\n',b'\n'):
            raise RuntimeError(mode+' simulator serves different HTML; check --html and baseline-ref')
    from playwright.sync_api import sync_playwright
    rows=[]
    with sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True)
        try:
            for mode in ['baseline','candidate']*args.repeats:
                context=browser.new_context(viewport={'width':390,'height':844})
                try:
                    context.add_init_script(INSTRUMENT)
                    page=context.new_page();errors=[]
                    page.on('pageerror',lambda e:errors.append(str(e)))
                    page.goto(urls[mode],wait_until='networkidle')
                    page.wait_for_selector('#telemetry[data-fresh="true"]')
                    page.evaluate("""() => {
                      __renderCost={frames:0,bytes:0,callback_ms:[],mutations:0,by_type:{}};
                      window.__mutations=new MutationObserver(rows=>{for(const row of rows) {
                        __renderCost.mutations++;
                        __renderCost.by_type[row.type]=(__renderCost.by_type[row.type]||0)+1;
                      }});
                      __mutations.observe(document.body,{subtree:true,childList:true,attributes:true,characterData:true});
                    }""")
                    page.wait_for_timeout(args.idle_ms)
                    row=page.evaluate("""() => {
                      __mutations.disconnect();
                      return {...__renderCost,left:document.getElementById('left-duty').textContent,
                        right:document.getElementById('right-duty').textContent,
                        manual:document.getElementById('manual-mode').getAttribute('aria-pressed')};
                    }""")
                    assert row['left']=='0' and row['right']=='0' and row['manual']=='true' and not errors
                    assert row['frames']>0
                    row.update(mode=mode,idle_ms=args.idle_ms,page_errors=errors)
                    row['mutations_per_status']=row['mutations']/row['frames']
                    rows.append(row)
                finally:context.close()
        finally:browser.close()
    summary={}
    for mode in ('baseline','candidate'):
        selected=[r for r in rows if r['mode']==mode]
        total=sum(r['mutations'] for r in selected);frames=sum(r['frames'] for r in selected)
        summary[mode]={'status_frames':frames,'mutations':total,'mutations_per_status':round(total/frames,3),
                       'status_callback':distribution([v for r in selected for v in r['callback_ms']])}
    report={'scope':'Headless desktop Chromium, 390x844 viewport, idle native simulator. Not real Android/Wi-Fi/PWM.',
            'baseline_ref':args.baseline_ref,'production_candidate_html':True,'automatic_move_commands':False,
            'phone_latency_measured':False,'summary':summary,'runs':rows}
    report['mutation_reduction_percent']=round((1-summary['candidate']['mutations_per_status']/summary['baseline']['mutations_per_status'])*100,2)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='runs'},indent=2))


if __name__=='__main__':main()
