# S1b review: launch identity threading

Reviewed range: `40c82e456c5d74dcb26e13f910c38c18acbe02d3..119f520d877590ee254e83349c0e916e6198d07d`

Lens: cross component contract completeness and transport.

## Verdict

- Blockers: 0
- Majors: 0
- Minors: 0

No actionable findings.

## Contract proof

### Browser through runtime HTTP

- `www/packages/canvas/src/model/paneRecords.ts`, `ViewerCanvasContext`: exposes the resolved Canvas identifier and launch Space identifier.
- `www/packages/canvas/src/viewers/registry.tsx`, `CapturedRunPane` registration: passes `spaceId`, `worktreeId`, and `canvasId`.
- `www/packages/canvas/src/viewers/terminal/CapturedRunPane.tsx`, `CapturedRunPane`: accepts and forwards the complete selector tuple.
- `www/packages/canvas/src/infrastructure/runtime/useCapturedRunBinding.ts`, `useCapturedRunBinding`: forwards the tuple to `ensureRun` and includes every field in effect identity.
- `www/packages/canvas/src/model/capturedRunStore.ts`, `ensureRun`: forwards the tuple to `createCapturedRunView`.
- `www/packages/core/src/transport.ts`, `createCapturedRunView`: serializes `spaceId`, `worktreeId`, and `canvasId` in the `POST /v1/runs` body.

### Runtime through capture RPC

- `packages/runtime/src/server/runtimeRouter.ts`, `CreateRunBody` and the create route: parse and forward all three selectors.
- `packages/runtime/src/service/runManagerTypes.ts`, `CreateManagedRunInput`: carries the complete selector tuple.
- `packages/runtime/src/service/RunManager.ts`, `RunManager.createNew`: passes the tuple to the capture port.
- `packages/runtime/src/ports.ts`, `PrepareCaptureInput`: declares all three selectors.
- `packages/runtime/src/adapters/CaptureRpcClient.ts`, `prepareCaptureBody`: serializes all three selectors into capture RPC JSON.
- `packages/runtime/src/service/runManagerSupport.ts`, `createRunFingerprint`: includes `canvasId`, so the same idempotency key cannot silently reuse a different Canvas.

### Python resolution and trust boundary

- `api/src/transport_matters/api/v1/capture_rpc_routes.py`, `PrepareCaptureRequest.to_domain`: parses `spaceId`, `worktreeId`, and `canvasId`; calls `affinity_launch_fields(fields, None)` before constructing `CapturedRunRequest`, removing caller supplied affinity fields and the reserved carrier.
- `api/src/transport_matters/captured_run_models.py`, `CapturedRunRequest`: carries the complete selector tuple into capture resolution.
- `api/src/transport_matters/api/v1/capture_rpc_routes.py`, `_resolved_domain_request`: requires the complete tuple for Canvas launches, resolves it server side, replaces the requested directory with the resolved worktree path, and installs the trusted affinity carrier through `affinity_launch_fields(domain.launch_fields, canvas_launch.affinity)`.
- `api/src/transport_matters/api/v1/launch_resolution.py`, `resolve_run_canvas`: resolves worktree and Canvas on one database connection.
- `api/src/transport_matters/space/service.py`, `SpaceService.resolve_launch_worktree` and `SpaceService.get_canvas`: enforce Space membership, active worktree state, path presence, and Canvas anchoring to the resolved worktree.
- `api/src/transport_matters/session/affinity.py`, `build_session_affinity_stamp`, `affinity_launch_fields`, and `affinity_from_launch_fields`: centralize construction, reserved carrier installation, scrubbing, and decoding of the eight field affinity group.

### Capture process through write once session storage

- `api/src/transport_matters/owned_transcript_binding.py`, `build_proxy_run_binding`, `launch_run_context`, and `register_owned_cursor`: decode the trusted carrier, carry the typed group through the launch context and session binding, then scrub launch fields before tailer registration.
- `api/src/transport_matters/shared_proxy/binding.py`, `trusted_binding_affinity` and `bind_trusted_affinity`: decode the reserved carrier and project trusted identity into shared proxy bindings.
- `api/src/transport_matters/index/adapters/base.py`, `affinity_fields`, `RunContext`, and `SessionBinding`: define the single typed affinity projection used by adapters and tailer paths.
- `api/src/transport_matters/index/adapters/claude.py` and `codex.py`, adapter `bind` methods: copy the typed affinity group into provider session bindings.
- `api/src/transport_matters/index/tailer.py`, `register_session_cursor`: preserves the complete group through session identifier reconciliation and child transcript bindings.
- `api/src/transport_matters/addon_runtime.py`, `_make_exchange_cursor_sink`: preserves the group on the alternate exchange cursor path.
- `api/src/transport_matters/session/ingest.py`, `_binding_affinity` and `SessionWriter.build_session`: validate and pass the complete group into the existing write once persistence path.

## Test evidence in the diff

- `www/packages/core/src/transport.test.ts` asserts the exact `POST /v1/runs` body, including `canvasId`.
- `packages/runtime/src/server/runtimeRouter.test.ts` asserts router forwarding of the complete selector tuple.
- `packages/runtime/src/adapters/CaptureRpcClient.test.ts` asserts `canvasId` in capture RPC JSON.
- `packages/runtime/src/service/RunManager.idempotency.test.ts` proves that changing only `canvasId` creates an idempotency conflict.
- `api/src/transport_matters/api/v1/test_capture_rpc_worktree_resolution.py` covers valid resolution, incomplete selector rejection, missing or mismatched Canvas rejection, directory replacement, and caller forgery removal.
- `api/src/transport_matters/session/test_session_affinity_stamp.py` covers Claude and Codex end to end affinity persistence using resolved Space, Worktree, and Canvas records.
- `api/src/transport_matters/shared_proxy/test_core.py` covers the shared proxy carrier round trip into persisted session affinity.

## Verification constraints

- Branch: `feat/multi-launch`
- HEAD: `119f520d877590ee254e83349c0e916e6198d07d`
- Changed files: 50
- Repository working tree: pristine before this verdict
- Gates: not run, per review brief
