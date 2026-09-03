# Breakpoints over the shared proxy

The last open slice from the 2026-09-05 incident. Stuart owns the what: breakpoints must work for canvas runs again. This is the how, for partner agreement before code.

## Today

Breakpoint state is module-global in the process that runs the proxy addon: `breakpoint.py` holds the mode and the paused flows, `pause_session._run_pause` parks a flow on an event and emits a `paused` event through `broadcast.emit`, and the inspector reads and drives all of it through the channel backend's `/api/breakpoint/*` routes, which call the backend's own copy of that state. `broadcast` is process-local too: the SSE route reads the backend's queues.

That was one process in the original design. Since the gateway migration the proxy has been a separate process for every canvas run, first per run and now the shared subprocess, so the backend's routes arm a mode nothing reads, list no paused flows, and the proxy's `paused` events reach no subscriber. The feature has been inert for canvas runs for two months. The control channel carries ping, register listener, deregister listener and set overrides.

## Change

Two directions, both through channels the backend already owns.

**Downstream, control messages.** Six new requests on the shared proxy control channel, executed by the subprocess against its own `breakpoint` module:

| request | subprocess does | response |
| --- | --- | --- |
| `breakpoint_arm` / `breakpoint_disarm` | `bp.arm()` / `bp.disarm()` | ack with `breakpoint_mode` |
| `breakpoint_status` | mode plus `[flow_id, paused_at_ms, run_id]` | ack with `breakpoint_status` |
| `breakpoint_paused(flow_id)` | full detail of one paused flow | ack with `paused_flow` |
| `breakpoint_release(flow_id, ir \| null)` | serialize `ir` with the provider adapter as the route does today, then `bp.release`; null keeps the original bytes | ack |
| `breakpoint_drop(flow_id)` | `bp.drop` | ack |
| `breakpoint_re_audit(flow_id)` | re-apply its own override store (already synced by `set_overrides`) to the original IR and recount with its own token counter and the flow's auth headers | ack with `re_audit` |

The detail and re-audit shapes are the route models `PausedFlowDetail` and `ReAuditResponse`, moved to a module both sides import so there is one builder (`paused_flow_detail(pf)`) and one re-audit function. Auth headers never cross the socket: the recount runs where the headers live. The ack model gains optional typed fields; requests stay one per connection.

**Upstream, doorbells.** The subprocess has the session writer and therefore `pg_notify` on `tm_events`. `broadcast` gains a forwarder hook the shared runtime installs; it forwards `paused` and `paused_tokens` as a `breakpoint` NOTIFY payload carrying `run_id`, `flow_id`, `event` and, for tokens, the count. Nothing else is forwarded and the full IR never rides a NOTIFY (8,000 byte limit). The backend's `SessionEventHub` parses the new signal and a `BreakpointBridge` in the lifespan subscribes: on `paused` it pulls `breakpoint_paused(flow_id)` over the control channel and emits the same `paused` payload `_run_pause` builds today into `broadcast` for the run; on `paused_tokens` it emits `paused_tokens` from the signal. The inspector's SSE contract is unchanged.

**Routes.** `breakpoint_routes` dispatch through a `BreakpointPlane` with two members: the local `breakpoint` module (the CLI's embedded launch) and the shared proxy manager (canvas runs). Arm and disarm apply to both. Status merges both. The flow routes (paused, release, release-unmodified, re-audit, drop) try local first, then shared; a flow paused in neither is the existing 404. The manager gains the six methods over `SharedProxyControlClient`.

## Stated behaviour at the edges

- Timeout: `breakpoint_timeout_s` auto-release stays in the subprocess, unchanged.
- Subprocess restart with a flow paused: the flow dies with the process and its harness request fails as it does today when mitmdump dies. The UI's next action on that flow gets the existing 404 and clears. No pretence of continuity.
- Arm is global, as today; a paused flow serializes others behind `pause_serializer` in the subprocess, as today.
- Per-run mitmdump launched by the CLI keeps working through the local member, untouched.

## Proof

- Model round trips for the six requests and the ack fields.
- Subprocess handler tests against a live `breakpoint` module (arm, pause a fake flow, status, paused detail, release with and without IR, drop, re-audit with a fake counter).
- Manager tests with the fake control channel already used by `test_manager.py`.
- Route tests: local flow served locally, shared flow served through a fake manager, 404 when neither, arm reaches both.
- Bridge test: a `breakpoint` NOTIFY signal becomes a `paused` broadcast for the run with the detail pulled through the fake manager; `paused_tokens` passes the count through.
- Road test on preview: arm in the inspector, prompt a canvas run, see the pause, edit and release, see the edited request on the wire; repeat with release-unmodified and drop; a codex websocket run for the websocket branch.

## Size

Roughly: models 120, subprocess 90, manager 60, shared detail module 80, bridge 80, hub signal 40, routes 100, forwarder 20, tests 500. Two handoffs.
