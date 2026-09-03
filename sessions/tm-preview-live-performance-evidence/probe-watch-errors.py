"""Reproduce watch startup error masking and stale readiness with existing test fakes."""
import asyncio,io,json,logging,pathlib,time
from types import SimpleNamespace
from transport_matters.controlplane.activity import GatewayActivitySnapshot,GatewayResponseError
from transport_matters.controlplane.errors import ControlPlaneError
from transport_matters.controlplane.service import ControlPlaneService
from transport_matters.controlplane.watch_test_support import FakeGateway,FakeAudit,_engine,_principal,_run
from transport_matters.session.listen import SessionEventHub

class BrokenStream(FakeGateway):
 def __init__(self,initial_snapshot):
  super().__init__(_run('run-peer',status='idle',tier='idle'))
  self.initial_snapshot=initial_snapshot;self.fail_now=asyncio.Event();self.failed=asyncio.Event()
 async def stream_workspace_activity(self,_workspace_id,*,owner):
  self.stream_calls+=1
  if self.initial_snapshot and self.stream_calls==1:
   yield GatewayActivitySnapshot(type='snapshot',items=self.items)
   await self.fail_now.wait()
  self.failed.set()
  raise GatewayResponseError(200,'gateway activity stream frame was invalid')

async def scenario(initial_snapshot):
 gateway=BrokenStream(initial_snapshot);audit=FakeAudit();engine=_engine(gateway,SessionEventHub(),audit)
 engine._start_timeout_s=.08
 service=SimpleNamespace(_require_watches=lambda:engine)
 try:
  if initial_snapshot:
   await engine.watch(_principal(),'workspace',('turn_completed',))
   gateway.fail_now.set();await asyncio.wait_for(gateway.failed.wait(),1)
  started=time.monotonic()
  try:
   result=await ControlPlaneService.watch(service,_principal(run_id='run-second' if initial_snapshot else 'run-watcher'),'workspace',('turn_completed',))
   outcome={'returned':'success','changed':result.changed}
  except ControlPlaneError as exc:
   outcome={'returned':'error','code':exc.code,'message':exc.message,'cause':str(exc.__cause__),'root_cause_type':type(exc.__cause__.__cause__).__name__}
  outcome.update(elapsed_ms=(time.monotonic()-started)*1000,stream_attempts=gateway.stream_calls,registered=engine.is_watching('run-second' if initial_snapshot else 'run-watcher'),feed_count=len(engine._feeds))
  if engine._feeds:
   feed=next(iter(engine._feeds.values()));outcome.update(activity_ready=feed.activity_ready.is_set(),wire_ready=feed.wire_ready.is_set(),consumer_done=feed.activity_task.done())
  return outcome
 finally:await engine.aclose()

async def main():
 logs=io.StringIO();handler=logging.StreamHandler(logs);logger=logging.getLogger('transport_matters.controlplane.watch');logger.addHandler(handler)
 try:result={'before_first_snapshot':await scenario(False),'after_initial_readiness':await scenario(True)}
 finally:logger.removeHandler(handler)
 assert result['before_first_snapshot']['code']=='busy_gateway'
 assert result['before_first_snapshot']['root_cause_type']=='TimeoutError'
 assert result['after_initial_readiness']['returned']=='success'
 assert result['after_initial_readiness']['activity_ready']
 result['stream_error_log_count']=logs.getvalue().count('Control plane Activity watch stream dropped')
 out=pathlib.Path(__file__).parent;(out/'watch-errors.json').write_text(json.dumps(result,indent=2)+'\n');(out/'watch-errors.log').write_text(logs.getvalue());print(json.dumps(result))
asyncio.run(main())
