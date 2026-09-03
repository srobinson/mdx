"""Read the current Activity SSE snapshot and exercise the production frame parser."""
import hashlib,json,pathlib,time,urllib.request
from transport_matters.sse import IncrementalSseFrames,MAX_INCREMENTAL_SSE_TAIL_BYTES
url='http://127.0.0.1:59598/v1/workspaces/dev-helioy-transport-matters%2Fecd9b0df/activity/stream?owner=local'
t=time.monotonic()
with urllib.request.urlopen(url,timeout=3) as r:line=r.readline();status=r.status
wire=line+b'\n';payload=json.loads(line[5:]);outputs={}
for name,limit in [('production_default',MAX_INCREMENTAL_SSE_TAIL_BYTES),('diagnostic_snapshot_size',len(wire))]:
 parser=IncrementalSseFrames(max_tail_bytes=limit);frames=[]
 for offset in range(0,len(wire),65536):frames.extend(parser.feed(wire[offset:offset+65536]))
 outputs[name]={'frames':len(frames),'snapshot_equal':frames==[payload]}
result={'status':status,'read_and_parse_ms':(time.monotonic()-t)*1000,'snapshot_bytes':len(line),'snapshot_sha256':hashlib.sha256(line).hexdigest(),'items':len(payload['items']),'default_limit':MAX_INCREMENTAL_SSE_TAIL_BYTES,'parsers':outputs}
assert outputs['production_default']['frames']==0, 'Expected current oversized snapshot failure'
assert outputs['diagnostic_snapshot_size']['snapshot_equal'], 'Snapshot must remain valid with sufficient framing budget'
(pathlib.Path(__file__).parent/'watch-reproduction.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
