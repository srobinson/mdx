"""Fixed watch engine against the live preview Gateway and Postgres notifications.

Only final notification delivery and audit persistence use existing in-memory fakes.
The listener uses LISTEN/SELECT only. No backend restart or live database mutation.
"""
import argparse,asyncio,json,pathlib,time
from urllib.parse import urlsplit
from transport_matters.api.v1.run_proxy import RunRouteProxy
from transport_matters.config import Settings,resolve_database_url
from transport_matters.controlplane.models import ControlPlanePrincipal,ControlPlaneGrantRole
from transport_matters.controlplane.service import ControlPlaneService
from transport_matters.controlplane.watch_test_support import FakeGateway,FakeAudit,FakeReads,_engine
from transport_matters.session.listen import SessionEventHub,SessionEventListener

p=argparse.ArgumentParser();p.add_argument('--target',required=True);p.add_argument('--seconds',type=int,default=240);a=p.parse_args()
async def main():
 home=pathlib.Path.home()/'.transport-matters-preview';out=pathlib.Path(__file__).parent
 settings=Settings.load_from(home/'settings.toml',env_settings=Settings(channel='preview',storage_dir=home))
 database_url=resolve_database_url(settings);assert urlsplit(database_url).path=='/transport_matters_preview'
 proxy=RunRouteProxy(gateway_url='http://127.0.0.1:59598',settings=settings)
 gateway=FakeGateway();gateway.stream_workspace_activity=proxy.stream_workspace_activity;gateway.read_completed_turns=proxy.read_completed_turns
 hub=SessionEventHub();listener=SessionEventListener(database_url,hub);audit=FakeAudit();engine=_engine(gateway,hub,audit)
 principal=ControlPlanePrincipal(run_id='dd117da2-e994-4ec5-8515-8bc0e68ba303',role=ControlPlaneGrantRole.OBSERVER,workspace_id='dev-helioy-transport-matters/ecd9b0df',owner='local')
 service=ControlPlaneService(reads=FakeReads(),activity=gateway,watches=engine)
 try:
  await listener.start()
  async with asyncio.timeout(5):
   while listener.connection_pid is None:await asyncio.sleep(.01)
  started=time.monotonic();result=await service.watch(principal,a.target,('turn_completed',))
  feed=next(iter(engine._feeds.values()))
  ready={'registered':result.changed,'elapsed_ms':(time.monotonic()-started)*1000,'workspace_items':len(feed.activity),'database':'transport_matters_preview','listener_pid':listener.connection_pid,'target':a.target}
  (out/'live-ready.json').write_text(json.dumps(ready,indent=2)+'\n');print(json.dumps(ready),flush=True)
  async with asyncio.timeout(a.seconds):await gateway.delivery_started.wait()
  await asyncio.sleep(.1)
  final={**ready,'notifications':gateway.deliveries,'delivery_attempts':gateway.delivery_attempts,'audit_statuses':[row.outcomes[0].status for row in audit.actions]}
  assert any('finished turn' in text for text in gateway.deliveries)
  (out/'live-result.json').write_text(json.dumps(final,indent=2)+'\n');print(json.dumps(final),flush=True)
 finally:
  await engine.aclose();await listener.aclose();await proxy.close()
asyncio.run(main())
