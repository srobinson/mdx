# Scout: S1b trusted launch identity threading

Scope: read only scout of `feat/multi-launch` at
`40c82e456c5d74dcb26e13f910c38c18acbe02d3`. The handoff named
`bcb36c9c` as the S1a baseline. Current HEAD adds the follow up
`fix(session): harden affinity trust boundary`, so this plan targets the
newer tree. The tracked tree was clean when inspected.

This is one PR sized slice. It carries a server resolved Canvas and Worktree
snapshot from the Canvas launch request to the first session upsert. It adds no
migration and no runtime run view field. S4a remains the owner of `canvasId` on
`RuntimeRunView`.

## Reuse Map

### Browser launch identity producer

- Reuse `www/packages/canvas/src/model/paneRecords.ts::ViewerCanvasContext`.
  `ViewerCanvasContext.id` is the durable Canvas UUID and
  `ViewerCanvasContext.launch.spaceId` is the resolved Space selector already
  supplied to every viewer by
  `www/packages/canvas/src/workbench/CanvasPaneLayer.tsx::useCanvasPaneRenderer`.
  The captured run viewer can forward this tuple without adding another
  persisted Canvas field to `CapturedRunRef`.
- Reuse the existing launch chain:
  `www/packages/canvas/src/viewers/registry.tsx` captured run viewer to
  `CapturedRunPane` to `useCapturedRunBinding` to
  `useCapturedRunStore.ensureRun` to
  `www/packages/core/src/transport.ts::createCapturedRunView`.
  This chain already carries `worktreeId`. Extend the same option object with
  `spaceId` and `canvasId`.
- Reuse `www/packages/canvas/src/route.ts::resolveCanvasLaunchIdentity`.
  It marks the route Canvas as verified only after matching the backend
  identity tuple. This is useful browser evidence. The HTTP values remain
  selectors and must still be resolved by Python.

### TypeScript Runtime transport

- Reuse
  `packages/runtime/src/server/runtimeRouter.ts::registerRunRoutes` and
  `CreateRunBody`. Parse `canvasId` with the existing
  `optionalStringFromBody` pattern and pass it into the managed run input.
- Reuse
  `packages/runtime/src/service/runManagerTypes.ts::CreateManagedRunInput`,
  `packages/runtime/src/ports.ts::PrepareCaptureInput`, and
  `packages/runtime/src/service/RunManager.ts::RunManager.createNew`.
  `canvasId` belongs on the prepare request only in S1b.
- Reuse
  `packages/runtime/src/adapters/CaptureRpcClient.ts::prepareCaptureBody`.
  It is the complete TypeScript to Python JSON serializer. A field added only
  to `RunManager.createNew` will otherwise disappear here.
- Reuse
  `packages/runtime/src/service/runManagerSupport.ts::createRunFingerprint`.
  Add `canvasId` to the existing ordered fingerprint. Reusing an idempotency
  key with a different Canvas must raise `idempotency_conflict`.
- Keep
  `packages/runtime/src/domain/runtimeRun.ts::RuntimeRunView`,
  `RunManager.register`, and `ManagedRunFilters` unchanged. S4a owns run
  inventory attribution and Canvas filtering.

### Python request and trusted resolution

- Reuse
  `api/src/transport_matters/api/v1/capture_rpc_routes.py::PrepareCaptureRequest`
  and `CapturedRunRequest.to_domain`. Add `canvasId` as a UUID selector using
  `parse_uuid_id` and the existing `CanvasId` type.
- Reuse
  `api/src/transport_matters/captured_run_models.py::CapturedRunRequest`.
  Add `canvas_id: CanvasId | None`. Dataclass `replace` calls in capture
  resolution will preserve it automatically.
- Reuse
  `api/src/transport_matters/api/v1/launch_resolution.py::resolve_run_worktree`
  and
  `api/src/transport_matters/space/service.py::SpaceCrudService.resolve_launch_worktree`.
  Refactor the common Worktree availability checks into one internal path,
  then add a Canvas aware resolver that uses the same service and database
  connection.
- Reuse `SpaceCrudService.get_canvas` with
  `space.service.rest_caller(resolved.space_id, owner=owner)`. It returns the
  existing `CanvasRecord`, including `canvas_id`, `parent_canvas_id`, `name`,
  `path`, `space_id`, and `anchor_worktree_id`.
- Reuse `api/src/transport_matters/space/models.py::ResolvedWorktree`.
  It already carries `space_id`, `worktree_id`, `root_canvas_id`, `cwd`, and
  `branch_name`. The launch stamp needs `cwd` and `branch_name`. It does not
  need another Worktree DTO.
- Reuse `api/src/transport_matters/space/models.py::CanvasRecord`.
  Its projected `path` is the canonical Canvas ancestry. Do not rebuild the
  path from request text or from browser state.

### Snapshot construction and carrier

- Reuse
  `api/src/transport_matters/session/affinity.py::SessionAffinityStamp`.
  This is the canonical eight field atomic group:
  `space_id`, `worktree_id`, `canvas_id`, `parent_canvas_id`, `canvas_name`,
  `canvas_path`, `worktree_path`, and `worktree_branch_name`.
- Reuse
  `api/src/transport_matters/session/affinity.py::serialize_canvas_path`.
  It serializes `CanvasRecord.path` with the existing alias and compact JSON
  contract.
- Extract the repeated `ResolvedWorktree` plus `CanvasRecord` construction
  now present in
  `api/src/transport_matters/session/backfill.py::backfill_session_spaces`
  into one pure factory in `session/affinity.py`. The launch resolver and
  backfill must call the same factory.
- Reuse
  `api/src/transport_matters/session/affinity.py::affinity_launch_fields`.
  `PrepareCaptureRequest.to_domain` must first call it with `stamp=None` to
  delete caller supplied direct affinity keys and the reserved
  `session_affinity` carrier. After trusted resolution,
  `_resolved_domain_request` calls it with the server built stamp.
- Reuse
  `api/src/transport_matters/session/affinity.py::affinity_from_launch_fields`.
  It already decodes and validates the reserved carrier but has no production
  consumer at current HEAD.
- Reuse the existing internal carrier:
  `captured_run_context._build_provider_invocation` to
  `launch_environment.build_launch_env` to `Settings.launch_fields` to
  `addon_runtime.build_proxy_run_binding` to
  `ProxyRunBinding.launch_fields`.
  `SharedProxyBindingPayload` also serializes `launch_fields`, so one carrier
  can serve the dedicated and shared proxy paths.

### Adapter and session handoff

- Reuse
  `api/src/transport_matters/index/adapters/base.py::RunContext` and
  `SessionBinding`. Declare all eight optional affinity fields on both models.
  Dynamic `model_copy` extras are deliberately rejected by the S1a hardening.
- Reuse
  `api/src/transport_matters/index/adapters/claude.py::ClaudeAdapter.bind`
  and
  `api/src/transport_matters/index/adapters/codex.py::CodexAdapter.bind`.
  Both adapters already copy the common run facts into `SessionBinding`.
  Add the affinity group through one shared helper keyed by
  `AFFINITY_FIELD_NAMES`.
- Reuse
  `api/src/transport_matters/addon_runtime.py::build_proxy_run_binding`.
  Decode the trusted carrier once, set `ProxyRunBinding.space_id` and
  `worktree_id` from that stamp for existing lifecycle consumers, and retain
  the carrier for the complete snapshot.
- Reuse
  `api/src/transport_matters/addon_runtime.py::_launch_run_context`.
  Copy the decoded complete group into `RunContext`.
- Reuse
  `api/src/transport_matters/addon_runtime.py::register_owned_cursor`.
  Keep its `affinity_launch_fields(binding.launch_fields, None)` sanitization
  before the generic launch field merge. Affinity reaches the binding through
  declared adapter fields, so no caller supplied dynamic extra can bypass the
  model.
- Also close the two existing alternate producers:
  `addon_runtime._make_exchange_cursor_sink` builds a wire learned
  `SessionBinding`, and
  `index/tailer.py::register_session_cursor` rebuilds `RunContext` before
  adapter binding. Both must copy the same declared affinity group.
- Reuse the shared proxy transport:
  `shared_proxy.models.binding_payload_from_binding` and
  `shared_proxy.addon._runtime_binding_from_payload`. The existing
  `launch_fields` round trip carries the reserved snapshot. Avoid a second
  Canvas snapshot payload.

### Existing consumer

- Reuse
  `api/src/transport_matters/session/ingest.py::build_session` and
  `_binding_affinity`. `_binding_affinity` reads only declared
  `SessionBinding.model_fields`. If `canvas_id` is absent it returns eight
  nulls. If present it requires one valid `SessionAffinityStamp`.
- Reuse the S1a write path:
  `SessionWriter` to `AsyncSessionDao.upsert_session` to
  `session/session_statements.py::UPSERT_SESSION_SQL`. It already applies the
  group once and preserves the stored group on later ingests.
- Reuse the existing S1a tests for atomicity, write once behavior, tombstone
  survival, blank rejection, raw forgery rejection, and backfill. S1b adds
  transport coverage and turns the deferred first session proof green.

## Quality Map

### Trust boundaries

1. `PrepareCaptureRequest.to_domain` currently copies `launchFields`
   verbatim. `register_owned_cursor` strips affinity only at the final merge.
   S1b will begin decoding the reserved carrier, so the request boundary must
   remove every caller supplied affinity value before the server installs its
   own stamp.
2. Request `canvasId`, `spaceId`, `worktreeId`, and `directory` are untrusted
   selectors. The stored name, parent, Canvas path, Worktree path, branch, and
   all IDs must come from `SpaceCrudService` results.
3. A request carrying `canvasId` must force server resolution even if it also
   carries `directory`. Otherwise an explicit directory bypasses
   `_resolved_domain_request` today. Use the resolved Worktree `cwd` as the
   launch directory or reject a conflicting explicit directory.
4. `SpaceCrudService.resolve_launch_worktree` validates membership when
   `space_id` is absent through the default caller. Its explicit `space_id`
   branch only verifies that the Space exists. S1b must require
   `worktree_in_space` in both branches before building a stamp.
5. A Canvas may launch against its default Worktree or a per spawn Worktree
   that differs from `anchor_worktree_id`. Require the selected Canvas and
   selected Worktree to be visible in the same resolved Space. Do not require
   `canvas.anchor_worktree_id == resolved.worktree_id`.

### Cross component contracts

1. The browser has a verified Canvas ID, but
   `createCapturedRunView` accepts only `worktreeId`. Without the browser
   producer change every downstream field remains absent.
2. `canvasId` must appear in `CreateCapturedRunInput`,
   `PrepareCaptureInput`, `prepareCaptureBody`, `PrepareCaptureRequest`, and
   `CapturedRunRequest`. Missing any one seam silently drops the field.
3. `createRunFingerprint` lacks Canvas identity. A replay key could otherwise
   accept a changed placement request as identical.
4. `SessionBinding` currently declares only `space_id` and `worktree_id` from
   the affinity group. Adding values through `model_copy(update=...)` will not
   work because `_binding_affinity` reads `model_dump`, and S1a intentionally
   blocks undeclared fields.
5. `register_session_cursor` performs a second adapter bind. Affinity copied
   only in `register_owned_cursor` would disappear during that rebind.
6. The shared proxy payload already carries `launch_fields`. Reuse that
   carrier so dedicated and shared proxy modes cannot diverge.

### Duplication and grooming

1. `backfill_session_spaces` already constructs a
   `SessionAffinityStamp` from `ResolvedWorktree` and `CanvasRecord`. Extract
   that exact construction and reuse it for live launch resolution.
2. Both adapters need the same eight fields. Use one helper based on
   `AFFINITY_FIELD_NAMES`; do not hand copy the field list twice.
3. Keep one server resolver. Refactor `resolve_run_worktree` internals and
   build Canvas resolution on that shared path.
4. Do not add a parallel affinity environment variable. The reserved,
   sanitized `session_affinity` launch field already crosses the subprocess
   boundary and shared proxy JSON boundary.

### STEP 0 line limits

- `api/src/transport_matters/addon_runtime.py` is exactly 699 lines. It has one
  line of capacity under the hard 700 line limit. Before adding S1b logic,
  extract the owned transcript binding cluster
  `build_proxy_run_binding`, `_launch_run_context`,
  `register_owned_cursor`, and `_register_owned_cursor` into a focused module,
  then import those symbols from `addon_runtime`.
- `packages/runtime/src/service/RunManager.ts` is 664 lines. The S1b edit is a
  field forward only. Keep it below 700 and place tests in existing test
  files.
- No other named production file is near the limit. The next largest relevant
  production files are `index/tailer.py` at 549,
  `capture_rpc_routes.py` at 509, and `www/packages/core/src/transport.ts` at
  475 lines.

### Open product contract

The only open decision is absence handling for `canvasId` on
`launchKind="canvas"`.

Recommendation: after the browser producer is wired, reject a Canvas launch
without `spaceId`, `worktreeId`, and `canvasId`. Do not silently substitute
`ResolvedWorktree.root_canvas_id`, because that would record placement in the
protected root when the launch originated from a user Canvas. Service and
detached launches may omit Canvas identity and remain unstamped until their
own placement contract supplies one.

## Plan

### Slice count

One PR sized slice, including the required STEP 0 extraction. No migration.
No run inventory field. No delete behavior.

### Tests first

1. Add the crown test
   `api/src/transport_matters/session/test_session_affinity_stamp.py::test_launch_stamps_canvas_identity_on_first_session`.
   Use the real Space service and test database to create a Worktree and user
   Canvas. Send only opaque selectors plus forged affinity launch fields
   through capture resolution. Carry the resolved request through launch
   settings, proxy binding, adapter binding, and the first session writer
   upsert. Parameterize Claude and Codex. Assert the stored row contains the
   exact eight server values before any backfill runs.
2. Extend
   `api/src/transport_matters/api/v1/test_capture_rpc_worktree_resolution.py`.
   Prove that:
   - a valid Space, Worktree, and Canvas tuple produces the canonical
     `SessionAffinityStamp`;
   - caller supplied direct affinity fields and the reserved carrier are
     removed;
   - a Canvas or Worktree outside the resolved Space is rejected with the
     existing `space_mismatch` domain error;
   - a missing Canvas is `canvas_not_found`;
   - a request Canvas cannot pair with a bypassing explicit directory.
3. Extend
   `api/src/transport_matters/index/adapters/test_claude.py::TestBindLocate`
   and
   `api/src/transport_matters/index/adapters/test_codex.py::TestBindLocate`
   with one test each that a complete RunContext affinity group survives
   `bind`.
4. Replace
   `api/src/transport_matters/shared_proxy/test_core.py::test_shared_proxy_payload_round_trip_leaves_session_affinity_for_backfill`
   with a positive round trip test. Supply the trusted carrier and assert the
   first persisted session has the complete snapshot after shared proxy JSON
   serialization.
5. Extend
   `api/src/transport_matters/session/test_session_affinity_stamp.py::test_raw_launch_affinity_forgeries_do_not_reach_session_params`
   so it proves sanitization at `PrepareCaptureRequest.to_domain`, then proves
   that server installed affinity does reach declared binding fields.
6. Extend the TypeScript contract tests:
   - `www/packages/core/src/transport.test.ts` asserts `spaceId`,
     `worktreeId`, and `canvasId` in the exact POST body.
   - `www/packages/canvas/src/model/capturedRunStore.test.ts` and the captured
     run viewer test assert the current `ViewerCanvasContext` tuple reaches
     `createCapturedRunView`.
   - `packages/runtime/src/server/runtimeRouter.test.ts` asserts `canvasId`
     reaches the fake capture port.
   - `packages/runtime/src/service/RunManager.test.ts` asserts `createNew`
     forwards `canvasId`.
   - `packages/runtime/src/adapters/CaptureRpcClient.test.ts` asserts the RPC
     JSON body contains `canvasId`.
   - `packages/runtime/src/service/RunManager.idempotency.test.ts` asserts the
     same idempotency key with a different `canvasId` conflicts.

### Implementation order

1. Perform STEP 0. Move the owned transcript binding cluster out of
   `addon_runtime.py` without behavior changes. Run the focused addon and
   shared proxy tests before adding S1b logic.
2. Extend the browser producer. Pass `props.canvas.launch.spaceId` and
   `props.canvas.id` through `CapturedRunPane`,
   `useCapturedRunBinding`, `EnsureRunOptions`, and
   `createCapturedRunView`. Keep Canvas identity out of the persisted pane
   ref.
3. Extend TypeScript transport contracts. Add `canvasId` to
   `CreateRunBody`, `CreateManagedRunInput`, `PrepareCaptureInput`,
   `RunManager.createNew`, `CaptureRpcClient.prepareCaptureBody`, and
   `createRunFingerprint`. Leave `RuntimeRunView` unchanged.
4. Extend the Python request vocabulary. Add parsed `canvas_id` to
   `PrepareCaptureRequest` and `CapturedRunRequest`. Sanitize raw
   `launch_fields` in `to_domain` with
   `affinity_launch_fields(fields, None)`.
5. Single source snapshot construction. Add a pure
   `SessionAffinityStamp` factory for `ResolvedWorktree` plus `CanvasRecord`
   and refactor `backfill_session_spaces` to use it.
6. Extend trusted resolution. Refactor
   `launch_resolution.resolve_run_worktree` so Worktree availability checks
   remain one implementation. Add the Canvas aware resolver on the same
   connection. Require Space membership for the Worktree and Canvas. In
   `_resolved_domain_request`, resolve any request with `canvas_id`, replace
   `directory`, `space_id`, and `worktree_id` from the result, then install
   the trusted reserved carrier with `affinity_launch_fields`.
7. Complete the typed handoff. Declare the eight optional fields on
   `RunContext` and `SessionBinding`. Decode the reserved carrier in the
   extracted proxy binding helper, populate existing
   `ProxyRunBinding.space_id` and `worktree_id`, and copy the complete group
   through `_launch_run_context`, both adapters,
   `_make_exchange_cursor_sink`, and `register_session_cursor`.
8. Keep `register_owned_cursor` sanitization around the generic launch field
   merge. Reuse a single affinity field mapping helper in adapters, tailer,
   and `session.ingest._binding_affinity`.
9. Apply the open contract ruling. With the recommended ruling, reject a
   Canvas launch whose Space, Worktree, or Canvas selector is absent. Update
   standalone smoke and route fixtures to send a resolved tuple. Leave
   service and detached launches nullable.

### Verification

Fast loop:

```bash
pnpm --filter @tm/core test
pnpm --filter @tm/canvas test
pnpm --filter @tm/runtime test
just api test -n0 \
  src/transport_matters/session/test_session_affinity_stamp.py \
  src/transport_matters/api/v1/test_capture_rpc_worktree_resolution.py \
  src/transport_matters/index/adapters/test_claude.py \
  src/transport_matters/index/adapters/test_codex.py \
  src/transport_matters/shared_proxy/test_core.py
```

Authoritative repository gates:

```bash
just check
just test
```

Final proof:

- Run the crown test by exact node ID and observe the first session row before
  backfill.
- Search `canvasId` across the browser to Runtime to capture request chain and
  verify every producer and consumer is represented.
- Search `SESSION_AFFINITY_LAUNCH_FIELD` and verify the public request
  sanitizer precedes the only trusted writer.
- Confirm `addon_runtime.py` and `RunManager.ts` remain below 700 lines.
- Confirm the tracked tree contains only the intended implementation and test
  files.
