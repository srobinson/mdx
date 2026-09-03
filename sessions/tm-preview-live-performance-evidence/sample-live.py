"""Read-only live latency/CPU/journal sampler. Run with --run ID --seconds N."""
import argparse, concurrent.futures, datetime, json, pathlib, statistics, subprocess, time, urllib.request
p=argparse.ArgumentParser();p.add_argument('--run',required=True);p.add_argument('--seconds',type=int,default=60);p.add_argument('--gateway',default='http://127.0.0.1:59598');p.add_argument('--pids',default='97301,97312,97313');p.add_argument('--label',default='stream');a=p.parse_args()
root=pathlib.Path.home()/'.transport-matters-preview/workspaces/dev-helioy-transport-matters/ecd9b0df'/a.run
out=pathlib.Path(__file__).parent
urls={'backend':'http://127.0.0.1:8798/health','terminal':a.gateway+'/v1/runs/'+a.run+'/terminal-snapshot?owner=local'}
def request(item):
 name,url=item;t=time.monotonic()
 try:
  with urllib.request.urlopen(url,timeout=2) as r: value=json.load(r)
  return name,{'ms':(time.monotonic()-t)*1000,'text_chars':len(value.get('text','')),'end_marker':'PERF_STREAM_END' in value.get('text',''),'cols':value.get('cols')}
 except Exception as e:return name,{'error':str(e),'ms':(time.monotonic()-t)*1000}
def cpu():
 rows=subprocess.check_output(['ps','-p',a.pids,'-o','pid=,time=,rss='],text=True)
 result={}
 for line in rows.splitlines():
  pid,elapsed,rss=line.split();parts=elapsed.split(':');sec=sum(float(x)*60**i for i,x in enumerate(reversed(parts)));result[pid]={'cpu_s':sec,'rss_kb':int(rss)}
 return result
start=time.monotonic();before=cpu();rows=[]
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool, (out/(a.label+'.jsonl')).open('w') as f:
 while time.monotonic()-start<a.seconds:
  tick=time.monotonic();row={'elapsed_s':tick-start,'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'requests':dict(pool.map(request,urls.items()))}
  row['journals']=[{'exchange':x.parent.name,'bytes':x.stat().st_size,'mtime_ns':x.stat().st_mtime_ns,'snapshot_mtime_ns':(x.parent/'transport.json').stat().st_mtime_ns} for x in root.glob('*/codex-stream.jsonl') if x.exists()]
  rows.append(row);f.write(json.dumps(row)+'\n');f.flush();time.sleep(max(0,.1-(time.monotonic()-tick)))
after=cpu();duration=time.monotonic()-start
summary={'run':a.run,'duration_s':duration,'samples':len(rows),'cpu_percent':{pid:100*(after[pid]['cpu_s']-v['cpu_s'])/duration for pid,v in before.items() if pid in after},'rss_after_kb':{pid:v['rss_kb'] for pid,v in after.items()},'end_marker_observed':any(r['requests']['terminal'].get('end_marker') for r in rows),'journal_samples':sum(bool(r['journals']) for r in rows),'requests':{}}
for name in urls:
 values=[r['requests'][name]['ms'] for r in rows if 'error' not in r['requests'][name]]
 summary['requests'][name]={'errors':sum('error' in r['requests'][name] for r in rows)}
 if values:summary['requests'][name].update(median_ms=statistics.median(values),p95_ms=sorted(values)[int(.95*len(values))],max_ms=max(values),first_quarter_mean_ms=statistics.mean(values[:max(1,len(values)//4)]),last_quarter_mean_ms=statistics.mean(values[-max(1,len(values)//4):]))
(out/(a.label+'-summary.json')).write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary),flush=True)
