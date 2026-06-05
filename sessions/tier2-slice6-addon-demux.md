---
title: Tier 2 Slice 6 SharedProxyAddon Demux
type: sessions
tags: [backend, transport-matters, tier-2, shared-proxy, addon-demux]
summary: Implemented the shared proxy addon demux, then tightened stale stamped-flow fail closed behavior.
status: active
source: backend-engineer
confidence: high
created: 2026-06-17
updated: 2026-06-17
---

## Summary

Implemented Tier 2 Slice 6 on branch `feat/tier2-slice6-addon-demux`, initial commit `b0817da`, fix-round commit `e356280`, PR #136.

Key decisions:

- Added `SharedProxyAddon` as the shared mitmproxy subprocess addon.
- Added `SharedProxyBindingTable` as the subprocess-side register, deregister, and active-flow table consumed by both the control channel and addon.
- Demux uses `flow.client_conn.sockname[1]` as the primary listen port and `flow.client_conn.proxy_mode.custom_listen_port` as the required cross-check.
- Unmapped or mismatched flows fail closed. HTTP receives 502. Websocket flows are marked closed and killed.
- New-flow hooks stamp run identity on flow metadata. Later hooks resolve by active flow, stamped run id, then stamped listen port, so mid-flow deregister does not leak attribution.
- Stamped run ids are authoritative. If the stamped run id is unmapped, the existing-flow path fails closed and does not fall back to a reused listen port.
- The addon threads the resolved `ProxyRunBinding` into the existing Slice 1 binding-aware kernel in `addon_handlers`, rather than duplicating capture or persistence logic.

## API Contract

No HTTP or websocket API surfaces changed in this slice.

Internal addon contract:

```python
class SharedProxyAddon:
    async def request(flow: http.HTTPFlow) -> None: ...
    def websocket_start(flow: http.HTTPFlow) -> None: ...
    async def websocket_message(flow: http.HTTPFlow) -> None: ...
    async def websocket_end(flow: http.HTTPFlow) -> None: ...
    async def response(flow: http.HTTPFlow) -> None: ...
    async def error(flow: http.HTTPFlow) -> None: ...

class SharedProxyBindingTable:
    def register(payload: SharedProxyBindingPayload) -> ProxyRunBinding: ...
    def deregister(run_id: str) -> SharedProxyBindingPayload | None: ...
    def resolve_new_flow(flow_id: str, listen_port: int) -> ProxyRunBinding | None: ...
    def resolve_existing_flow(flow_id: str, run_id: str | None, listen_port: int | None) -> ProxyRunBinding | None: ...
    def finish_flow(flow_id: str) -> None: ...
```

## Database Changes

None.

## Security Considerations

- Fail closed on missing sockname, missing custom listen port, listen-port mismatch, unmapped listen port, or unmapped run id.
- Regression coverage now includes stale stamped run ids after port reuse, fail-closed behavior across response, websocket start, websocket message, websocket end, and error hooks, plus interleaved open HTTP flows.
- Unmapped-flow logs include only flow id, listen port, and reason. Payloads and auth headers are never logged.
- Runtime bindings require a storage root when reconstructed from control-channel payloads to avoid falling back to process-global default storage.
- No live spawn path is wired in this slice, so production remains one mitmdump per run until Slice 7.

## Performance Notes

- Binding lookup is in-memory dictionary lookup by listen port, run id, or active flow id.
- Active-flow tracking keeps later hooks stable without scanning bindings.
- The addon reuses existing capture, persistence, request pipeline, and websocket handlers, avoiding duplicate processing paths.

Verification:

- `cd api && just check` passed.
- `cd api && .venv/bin/python -m pytest src/transport_matters/shared_proxy/test_addon.py -q` passed with 18 tests in 0.23 seconds.
- `cd api && just test` passed with 1512 tests in 38.08 seconds.

## Open Items

- Slice 7 will wire API-managed captured runs to register with the shared subprocess instead of starting per-run mitmdump.
- Shared subprocess token counter and full shared core construction remain future integration work.
- Metrics are currently an in-process demux counter, not an exported observability endpoint.
