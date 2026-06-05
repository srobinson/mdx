---
title: Tier 2 Slice 5 Shared Proxy Manager
type: sessions
tags: [backend, transport-matters, shared-proxy, mitmproxy, tier-2]
summary: Implemented isolated shared proxy subprocess machinery with hardened supervision and restart rehydration.
status: active
source: backend-engineer
confidence: high
created: 2026-06-17
updated: 2026-06-17
---

## Summary

Implemented Tier 2 Slice 5 on branch `feat/tier2-slice5-shared-proxy-manager`, PR #135.

Commits:

- `a663c57`: initial isolated shared proxy manager, subprocess, and typed UDS control channel.
- `a4d0151`: fix round hardening for readiness, restart rehydration, stale override cleanup, and monitor retry behavior.

The slice adds isolated shared proxy machinery only. It is not wired into `RunManager`, `app.state`, or the live spawn path. Production behavior remains one mitmdump per run until later slices.

Key decisions:

- API process owns the durable mirror in `SharedProxyManager`: `by_run_id`, `by_listen_port`, and override snapshots.
- The API mirror no longer carries write only generation counters. Generation values remain subprocess-owned response metadata.
- Subprocess owns the live mitmproxy `DumpMaster`, the runtime mode list, the per-listen-port binding table, and subprocess-local `OverrideStore` mutations.
- Control uses newline-framed JSON over a Unix domain socket with one request per connection.
- Listener readiness and listener removal are gated by accept-probes, not by mitmproxy internal `is_updating` state.
- Manager readiness now pings the UDS control channel while checking child process exit state, surfacing `SharedProxyProcessExited` with return code and log tail if the subprocess dies early.
- Restart rehydration resends all mirrored bindings and override snapshots after the process supervisor starts a fresh subprocess, and `_needs_rehydrate` remains set until rehydration succeeds.
- The monitor loop survives rehydrate failures and retries with bounded backoff.

## API Contract

Internal UDS contract, documented in `~/.mdx/design/transport-matters-shared-proxy-control-channel-api.md` and implemented in `api/src/transport_matters/shared_proxy/models.py`.

Requests:

```typescript
type SharedProxyControlRequest =
  | { type: "ping" }
  | { type: "register_listener"; binding: SharedProxyBindingPayload }
  | { type: "deregister_listener"; runId: string }
  | { type: "set_overrides"; scope: OverrideScopePayload; payload: OverrideSnapshotPayload };
```

Responses:

```typescript
interface SharedProxyControlAck {
  ok: true;
  proxyGeneration: number;
  modeGeneration: number;
  overridesGeneration: number;
}

interface SharedProxyControlError {
  ok: false;
  code: string;
  message: string;
}
```

Primary symbols:

- `api/src/transport_matters/shared_proxy/manager.py::SharedProxyManager`
- `api/src/transport_matters/shared_proxy/manager.py::SharedProxyProcessExited`
- `api/src/transport_matters/shared_proxy/control.py::SharedProxyControlClient`
- `api/src/transport_matters/shared_proxy/control.py::SharedProxyControlServer`
- `api/src/transport_matters/shared_proxy/subprocess.py::SharedProxySubprocess`
- `api/src/transport_matters/shared_proxy/process.py::SupervisorSharedProxyProcess`
- `api/src/transport_matters/shared_proxy/process.py::SharedProxyProcessExit`

## Database Changes

None. No migrations and no schema changes.

## Security Considerations

- Control channel is UDS only, not TCP reachable.
- Socket parent is owner-only `0700`; socket is `0600`.
- Control payloads are Pydantic validated before dispatch.
- Registration rejects duplicate run ids, duplicate listen ports, reverse bindings without upstreams, and missing listen ports.
- UDS request reads have a bounded idle timeout, so clients cannot hold server tasks open indefinitely without sending a frame.
- Error responses avoid echoing raw request payloads.
- No request or response payload bytes are logged by the new control path.

## Performance Notes

- Registration and deregistration mutate `DumpMaster.options.update(mode=[...])` in place instead of spawning per-run mitmdump processes.
- Accept-probe polling is bounded and local loopback only.
- The manager uses one subprocess name, `shared-mitmdump`, through `ProcessSupervisor`.
- Restart rehydration is serialized under the manager lock to avoid concurrent mode churn.
- Monitor retries use bounded backoff to avoid a dead supervision task and avoid hot looping on repeated subprocess or control failures.

Verification completed:

- `cd api && uv run ruff format src/transport_matters/shared_proxy`, passed.
- `cd api && uv run ruff check src/transport_matters/shared_proxy`, passed.
- `cd api && uv run pytest src/transport_matters/shared_proxy/test_manager.py -q`, 14 passed.
- `cd api && uv run pytest tests/integration/test_shared_proxy_subprocess.py -q`, 2 passed.
- `cd api && uv run mypy src/transport_matters/shared_proxy`, passed.
- `cd api && just check`, passed.
- `cd api && just test`, 1493 passed.

## Open Items

- Slice 6 still needs `SharedProxyAddon` flow-to-run demux using the subprocess binding table.
- Slice 7 still needs Context B `RunManager` integration.
- Slice 8 still needs API-managed per-run mitmdump path removal after Context B cutover.
- Slice 9 still needs 50-run load testing for single subprocess throughput, fd ceilings, shared CA behavior, and high churn `options.update` behavior.
