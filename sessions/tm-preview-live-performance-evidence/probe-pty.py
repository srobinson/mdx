"""Exercise real PTY input/output through preview at 40 columns. Socket close owns shell cleanup."""
import argparse,asyncio,json,pathlib,shlex,statistics,time
import websockets
p=argparse.ArgumentParser();p.add_argument('--mode',choices=['shell','raw'],default='shell');p.add_argument('--label',default='pty');a=p.parse_args()
async def main():
 samples=[];start=time.time()
 async with websockets.connect('ws://127.0.0.1:8798/api/terminal?cols=40&rows=12',origin='http://127.0.0.1:8798',open_timeout=3) as ws:
  async def until(marker):
   buf=b''
   while marker not in buf:
    value=await asyncio.wait_for(ws.recv(),3)
    buf+=value if isinstance(value,bytes) else value.encode()
   return buf
  if a.mode=='raw':
   code="import sys; print('\\120\\124\\131_READY',flush=True); [print('PTY_ACK_'+line.strip().split()[0],flush=True) for line in sys.stdin]"
   setup='   stty -echo; python3 -u -c '+shlex.quote(code)+'\r'
  else:setup="   printf '\\120\\124\\131_READY\\n'\r"
  await ws.send(setup.encode());await until(b'PTY_READY')
  for i in range(40):
   marker=f'PTY_ACK_{i:03d}'.encode()
   # Octal spelling or a transformed reply prevents echo from satisfying the check.
   command=(f"   {i:03d} {'wrap '*12}\r" if a.mode=='raw' else f"   printf '\\120\\124\\131_ACK_{i:03d}\\n' # {'wrap '*12}\r").encode()
   t=time.monotonic();await ws.send(command);await until(marker);samples.append((time.monotonic()-t)*1000)
   await asyncio.sleep(.15)
 result={'mode':a.mode,'started_unix_s':start,'ended_unix_s':time.time(),'n':len(samples),'cols':40,'rows':12,'leading_spaces':3,'input_bytes':len(command),'median_ms':statistics.median(samples),'p95_ms':sorted(samples)[int(.95*len(samples))],'max_ms':max(samples),'samples_ms':samples}
 (pathlib.Path(__file__).parent/(a.label+'-summary.json')).write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
asyncio.run(main())
