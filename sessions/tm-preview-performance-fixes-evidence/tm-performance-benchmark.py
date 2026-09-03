import asyncio,json,os,statistics,tempfile,time
from pathlib import Path
from unittest.mock import patch
from mitmproxy import websocket
from wsproto.frame_protocol import Opcode
from transport_matters import config
from transport_matters.addon import TransportMattersAddon
from transport_matters.codex.test_transport_support import _codex_flow
from transport_matters.codex import transport
from transport_matters.storage import init_storage,reset_storage,get_storage
from transport_matters.launch_verification_queue import VerificationRequestStore

async def stream(n):
    with tempfile.TemporaryDirectory(prefix='tm-performance-stream.') as folder:
        os.environ['TRANSPORT_MATTERS_RUN_ID']='performance-replay'
        os.environ['TRANSPORT_MATTERS_STORAGE_DIR']=folder
        config.get_settings.cache_clear()
        reset_storage();init_storage(root=Path(folder))
        addon=TransportMattersAddon();flow=_codex_flow();addon.websocket_start(flow)
        async def send(payload,client=False):
            flow.websocket.messages.append(websocket.WebSocketMessage(Opcode.TEXT,client,json.dumps(payload).encode(),timestamp=1776572041+len(flow.websocket.messages)/1000))
            await addon.websocket_message(flow)
        await send({'type':'response.create','model':'gpt-5-codex','instructions':'x'*100_000},True)
        store=await get_storage();times=[];cpu=time.process_time()
        with patch.object(store,'read_exchange',wraps=store.read_exchange) as reads,patch.object(store,'persist_exchange',wraps=store.persist_exchange) as writes,patch.object(transport,'_message_artifact',wraps=transport._message_artifact) as decoded:
            for _ in range(n):
                t=time.perf_counter();await send({'type':'response.output_text.delta','delta':'hello'});times.append((time.perf_counter()-t)*1000)
            metrics={'frames':n,'cpu_ms':(time.process_time()-cpu)*1000,'wall_ms':sum(times),'median_ms':statistics.median(times),'p95_ms':sorted(times)[int(.95*n)],'first_quarter_ms':statistics.mean(times[:n//4]),'last_quarter_ms':statistics.mean(times[-n//4:]),'exchange_reads':reads.call_count,'exchange_rewrites':writes.call_count,'frames_decoded':decoded.call_count}
        await send({'type':'response.completed','response':{'status':'completed'}})
        rows=await store.read_index(10,0);artifacts=await store.read_exchange(rows[0].id)
        assert len(artifacts.transport.messages)==n+2
        assert artifacts.turn.status=='completed'
        print(json.dumps(metrics),flush=True)
        store._io_executor.shutdown(wait=True)

s=VerificationRequestStore(Path.home()/'.mdx/sessions/tm-preview-performance-rescue-evidence')
s.list();times=[]
for _ in range(20):
    t=time.perf_counter();rows=s.list();times.append((time.perf_counter()-t)*1000)
print(json.dumps({'queue_requests':len(rows),'queue_median_ms':statistics.median(times)}),flush=True)
asyncio.run(stream(128));asyncio.run(stream(512))
