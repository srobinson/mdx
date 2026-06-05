---
title: Tier 2 Slice 1 ProxyRunBinding
type: sessions
tags: [backend, transport-matters, tier-2, shared-proxy, proxy-run-binding]
summary: Implemented and tightened the Slice 1 ProxyRunBinding identity refactor for addon capture paths.
status: active
source: backend-engineer
confidence: high
created: 2026-06-16
updated: 2026-06-16
---

## Summary

Implemented Tier 2 Slice 1 on branch `feat/tier2-slice1-proxy-run-binding`, initial commit `66ebd84`, follow-up fix commit `0c66e8f`, PR #130.

Key decisions:

- Added `api/src/transport_matters/shared_proxy/binding.py::ProxyRunBinding` as the frozen run identity object.
- Added `api/src/transport_matters/addon_runtime.py::build_proxy_run_binding` as the single construction path from `Settings` plus `StorageBackend`.
- Threaded the binding through addon handlers, HTTP recorders, Codex exchange persistence, Codex provisional rewrite, flow state, and recent auth.
- Preserved Context A fallback through `resolve_run_storage()` and Settings based breakpoint fields, so standalone CLI behavior remains intact.
- Stored run id and listen port in `RequestFlowState` metadata, not a mutable binding object.
- Removed redundant `ProxyRunBinding.storage_dir` after review because the threaded `storage` backend owns run storage for Slice 1.
- Kept `upstream` and `default_client_passthrough` as explicitly commented forward-carry fields for Slice 5 shared-proxy routing.
- Replaced `counting.py` binding `Any` annotations with a `TYPE_CHECKING` only `ProxyRunBinding` import.
- Unified empty auth clearing so binding holder state, `_recent_auth_binding`, and module-global `_recent_auth` clear together.

## API Contract

No public HTTP API contract changed in this slice.

Internal contract added:

```python
@dataclass(frozen=True, slots=True)
class ProxyRunBinding:
    run_id: str | None
    cli: str | None
    working_dir: Path | None
    storage: StorageBackend
    listen_port: int | None
    upstream: str | None
    agent_home_dir: Path | None
    owned_native_session_id: str | None
    owned_source_descriptor: str | None
    launch_fields: Mapping[str, Any]
    default_client_passthrough: tuple[str, ...]
    breakpoint_skip_models: tuple[str, ...]
    recent_auth: RecentAuthHolder
```

`capture_request_flow_state()` now accepts and records lightweight `run_id` and `listen_port` values.

## Database Changes

No database schema or migration changes.

## Security Considerations

- Recent auth is now held on the per run binding for addon paths rather than only in a process global variable.
- The binding stores only the filtered auth header set already used by `count_tokens` lazy recounts.
- Empty auth clears now remove stale module-global auth as well as binding auth.
- No raw request bytes or credentials are added to flow metadata.
- Context A fallbacks remain for standalone CLI and breakpoint paths, which are still one run per process.

## Performance Notes

- The change is behavior preserving for Slice 1 and keeps one mitmdump per run.
- Storage lookup is direct from the binding on addon capture paths, avoiding future shared proxy cross run coupling.
- Added regression `api/src/transport_matters/test_proxy_run_binding.py::test_binding_routes_http_capture_without_global_identity`, proving binding storage and run id win over process global settings and storage.
- Added regressions `api/src/transport_matters/test_counting.py::test_empty_recent_auth_clear_without_binding_clears_global` and `api/src/transport_matters/test_counting.py::test_empty_recent_auth_clear_with_binding_clears_holder_and_global` for recent auth clearing.

Verification:

- Fail-first proof: `cd api && .venv/bin/python -m pytest src/transport_matters/test_counting.py -k 'empty_recent_auth_clear' -q` failed before the fix on `test_empty_recent_auth_clear_with_binding_clears_holder_and_global` because `get_recent_auth()` returned stale global auth.
- Targeted proof: `cd api && .venv/bin/python -m pytest src/transport_matters/test_counting.py -k 'empty_recent_auth_clear' -q` passed after the fix.
- Targeted proof: `cd api && .venv/bin/python -m pytest src/transport_matters/test_counting.py src/transport_matters/test_proxy_run_binding.py -q` passed with 24 tests.
- Gate: `cd api && just check` passed.
- Gate: `cd api && just test` passed with 1457 tests.

## Open Items

- Later Tier 2 slices still need run scoped API storage and meta reads.
- Later shared proxy slices must replace the Context A fallback on Context B paths with demux resolved bindings for multiple concurrent runs.
- The embedded lazy token recount route still reads the most recent active binding while Slice 1 remains one binding per process.
