# Scout: populate the run-scoped OverrideStore for canvas runs

Slice 3 scout report. Read-only investigation on `feat/harvest-gates` (worktree
`.claude/worktrees/harvest-gates`). The prior map `.scratch/canvas-overlay-map.md`
does not exist anywhere on disk; every claim below was verified against source.

## Reuse Map

### 1. Who owns the run-scoped OverrideStore

**Type and construction.** `api/src/transport_matters/overrides/state.py:OverrideStore`.
One module-level instance per process (`state.py:_store`, reached only through
`state.py:get_store`). It is not constructed per run; it is per **process**, keyed
internally by `OverrideScope = (run_id, track_id)` via `state.py:normalize_scope` /
`state.py:root_scope`. The per-run isolation comes from process topology: every
captured run (canvas and detached alike) spawns its own mitmdump addon process,
so `get_store()` inside that process is effectively the run-scoped store.

**Process topology that makes this work.** `captured/run.py:prepare_captured_run`
(canvas path, via `capture_rpc.py:CaptureLeaseRegistry.prepare_capture`) and
`captured/run.py:run_captured_run_on_local_tty` (detached CLI path) both spawn a
per-run mitmdump whose addon boots `addon_runtime.py:load_capture_runtime`. With
`Settings.web_runtime == "embedded"` (the only mode the capture RPC accepts, see
`capture_rpc.py:CaptureLeaseRegistry.prepare_capture` raising
`CaptureExternalRuntimeUnsupported`), the addon also starts
`web_runtime.py:start_web_runtime`, which serves `main.py:create_app` on the run's
`web_port` **inside the same process**. That app mounts
`api/v1/router.py:api_router`, which includes `api/v1/overrides.py` at
`/api/overrides` and `api/v1/breakpoint_routes.py` at `/api/breakpoint`. So the
overrides HTTP surface and the pipeline share one process and one `get_store()`.

**Writers that populate the store on the working (non-canvas) path:**

1. `api/v1/overrides.py:patch_overrides` — the Inspector's breakpoint editor
   PATCHes `/api/overrides?run_id&track_id`; it calls `OverrideStore.upsert` at
   `state.py:scope_from_params(run_id, track_id)`. This is the primary writer.
2. `api/v1/overrides.py:_restore_scope` — rollback writer inside the same module.
3. `shared_proxy/subprocess.py:SharedProxySubprocess.set_overrides` — the shared
   proxy topology's writer: `api/v1/overrides.py:_sync_shared_overrides` forwards a
   snapshot through `shared_proxy/manager.py:SharedProxyManager.set_overrides` when
   the run is registered in `manager.by_run_id`. Not in play for canvas runs
   (embedded topology only), but it is the second writer to know about.

**Exact call chain, arming to populated store to applied overlay (detached run):**

- Human opens the Inspector at the run's `web_port` (embedded `create_app`).
- Arm: POST `/api/breakpoint/arm` → `api/v1/breakpoint_routes.py:arm_breakpoint`
  → `breakpoint.py:arm`.
- Next turn pauses: `addon_handlers.py:handle_http_request` → `bp.is_armed()` →
  `breakpoint.py` pause path (`handle_breakpoint`).
- Edit: Inspector `BreakpointEditor` PATCH `/api/overrides` →
  `api/v1/overrides.py:patch_overrides` → `OverrideStore.upsert` — **the store is
  now populated for scope (run_id, track_id)**.
- Every subsequent turn: `addon_handlers.py:handle_http_request` (Claude) or
  `addon_handlers.py:handle_codex_websocket_message` (Codex) →
  `request_pipeline.py:run_pipeline` → `get_store().get_all(scope)` →
  `overrides/__init__.py:apply_overrides`. This runs on **every** request,
  armed or not; arming only gates the pause, never the apply.

Scope note: `run_pipeline` reads scope `(run_id, track_assignment.track_id)`; the
root track is seeded with `track_id == run_id` in `track_manager.py:TrackManager._state`,
so the root-track scope equals `state.py:root_scope(run_id)`. Subagent tracks get
their own `track_id` and their own (empty) scope.

### 2. What the canvas path does differently

Canvas constructs its run through the identical capture seam
(`www/packages/canvas/src/model/capturedRunStore.ts:ensureRun` →
`@tm/core transport.ts:createCapturedRunView` → POST `/v1/runs` →
`packages/runtime/src/server/runtimeRouter.ts:registerRunRoutes` →
`packages/runtime/src/service/RunManager.ts` →
`packages/runtime/src/adapters/CaptureRpcClient.ts` →
`api/v1/capture_rpc_routes.py` → `capture_rpc.py:CaptureLeaseRegistry.prepare_capture`
→ `captured/run.py:prepare_captured_run`); the one step it never performs is the
client-side write — no Inspector session ever PATCHes `/api/overrides` on the
canvas run's embedded web runtime, so its store stays empty. (The run's `web_port`
is even returned in `CapturedRunSpawnSpec` and parsed by `CaptureRpcClient.ts`,
but it dies there: nothing in `packages/runtime` serializes it to `RunView`, and
no `webPort` reference exists in `www/packages/canvas` or `www/packages/core`.)

### 3. Is the "no explicit block" claim true?

**Confirmed.** `request_pipeline.py:run_pipeline` is the settling symbol: it has
no launch-kind parameter and no canvas condition; its only gates are
`OverrideStore.is_enabled` (defaults `True` in `state.py:OverrideStore.is_enabled`)
and store contents. `addon_handlers.py:handle_http_request` calls it
unconditionally for every parsed request. The only `launch_kind` sensitivity in
the addon (`addon_runtime.py:run_lifecycle_launch_kind` usage) affects lifecycle
event emission, never the override pipeline. A canvas run with a populated store
would apply overlays today.

### 4. The smallest populate slice, bound to existing owners

**The abandoned branch `wip/canvas-overlay` (23a49430) already is this slice, and
it chose the right seam. Verdict: SALVAGE** — rebase onto main and review; do not
rewrite from scratch. Reasons: it populates at launch through owners that all
already exist, it respects the inspector/canvas package boundary, it strips the
transient field from the persisted binding, and it carries a test at every seam
(`test_addon_runtime`, `test_capture_rpc_worktree_resolution::test_prepare_selects_launch_overlays_after_worktree_resolution`,
`runtimeRouter.test.ts`, `CaptureRpcClient.test.ts`, `capturedRunStore.test.ts`,
`transport.test.ts`, `overlaysStore` move tests). Its shape:

- **UI affordance (existing owner, no new surface):**
  `www/packages/inspector` `BreakpointEditor` (SAVE AS OVERLAY →
  `overlaysStore.createDraft`) and `OverlaysView` (name/scope/CONFIRM) already
  exist on this branch as the authoring surface; the wip moves `overlaysStore`
  to `@tm/core/overlaysStore` (same persistence key `transport-matters-overlays`,
  inspector registry re-derives it from the store options) so the canvas bundle
  may read it without violating the "inspector never imports canvas / canvas
  never imports inspector" boundary.
- **Attach at launch:** `capturedRunStore.ts:ensureRun` snapshots confirmed
  (non-draft) overlays into `createCapturedRunView(..., overlays)`.
- **Carry through the product plane:** `runtimeRouter.ts:registerRunRoutes` →
  `RunManager.ts:createRun` (+ `runManagerSupport.ts:createRunFingerprint`) →
  `CaptureRpcClient.ts:prepareCaptureBody`, all as an opaque `overlays` array.
- **Select and stamp:** `capture_rpc_routes.py:_resolved_domain_request` filters
  overlays by scope (`"shared"` or `canonical_path(scope) == canonical_path(domain.directory)`)
  and stamps survivors into `launch_fields[LaunchOverlay.LAUNCH_FIELD]`
  (`overrides/__init__.py:LaunchOverlay`, field `"initial_overrides"`).
- **Populate point:** `addon_runtime.py:load_capture_runtime` validates
  `LaunchOverlay` from `settings.launch_fields` and seeds
  `get_store().upsert(..., scope=root_scope(settings.run_id))` at addon boot.
  This is the answer to "who populates the store for a canvas run".
- **Hygiene:** `owned_transcript_binding.py:build_proxy_run_binding` strips
  `LaunchOverlay.LAUNCH_FIELD` from the binding's persisted `launch_fields`.

This matches the product model: a canvas run is never armed; the overlay applies
via `run_pipeline` on every turn with no pause. Populate-the-store, not
remove-a-guard.

### 5. What the human does to user test

Preconditions: the wip slice merged; canvas web UI open (Electron gateway /
channel web port).

1. **Author an overlay** in the Inspector served from the *same origin as the
   canvas* (the channel web port at `/`; canvas is `/canvas` of that origin —
   localStorage is per-origin, so an overlay saved in a per-run Inspector at a
   different port will NOT attach; see Quality Map hazard). Arm a breakpoint,
   pause a turn, make an edit with an unmistakable signature (e.g. toggle a tool
   off, or edit a system part's text), press **SAVE AS OVERLAY**, open the
   **OVERLAYS** route, name it, set scope **shared**, press **CONFIRM**.
2. **Launch a canvas run**: in the canvas, open a captured run pane on any
   worktree (normal launch path; overlays auto-attach, there is no per-launch
   toggle in this slice) and send any prompt.
3. **Observable that proves it applied**, two independent checks:
   - In the canvas exchange viewer for that turn
     (`www/packages/canvas/src/viewers/resource/ArkExchangePanels.tsx:ExchangeInspectPanel`),
     the curated note appears: "Showing the request as sent. The pipeline or a
     breakpoint edit mutated the original." — and the toggled tool is absent /
     the edited system text is what shows.
   - In the Inspector exchange detail (InspectTab), the request audit shows the
     before/after char counts (`OverrideAudit.chars_before` / `chars_after`) on
     the exact block that changed. The per-run Inspector is reachable at the
     canvas run's `web_port` recorded in the run manifest under
     `<channel home>/workspaces/{slug}/{hash}/{run}/`.

## Quality Map

- **File size:** nothing in scope exceeds 700 lines. Watch
  `packages/runtime/src/service/RunManager.ts` (676) and
  `addon_runtime.py` (636 pre-wip; the wip adds ~11): near threshold, do not grow
  them beyond the wip's minimal additions.
- **Second-writer hazard (store):** with the wip, `OverrideStore` gains a third
  writer: `addon_runtime.py:load_capture_runtime` (boot seed), alongside
  `api/v1/overrides.py:patch_overrides` (live edits) and
  `shared_proxy/subprocess.py:SharedProxySubprocess.set_overrides` (shared
  topology). Precedence is sound by construction: the seed runs once at addon
  boot before any traffic; the embedded API writes after and wins; the shared
  proxy writer never coexists with the embedded seed in one process (capture RPC
  rejects external runtime). State this precedence in the PR description.
- **Second-writer hazard (localStorage):** both bundles now persist
  `transport-matters-overlays` per origin. The canvas only sees overlays authored
  in its own origin (channel web port). Overlays authored in a per-run Inspector
  (different port = different origin) silently do not attach. Verify during build
  that the channel-origin Inspector can actually reach a pausable run to author
  from; if not, this is the slice's real UX gap and belongs in the done message,
  not in code contortions.
- **Track scoping:** the seed lands at `root_scope(run_id)`, which the root track
  reads (`TrackManager._state` seeds `track_id = run_id`). Subagent tracks have
  distinct scopes and will not see seeded overlays. Acceptable for this slice;
  say so explicitly rather than widening scope handling.
- **Leak check for review:** the wip strips `initial_overrides` only in
  `owned_transcript_binding.py:build_proxy_run_binding`. Launch fields also
  travel through `launch/environment.py` (env serialization — required, that is
  the transport to the addon) and run lifecycle emission from
  `capture_rpc_routes.py` domain rows. Confirm during review that the field does
  not leak into persisted session rows or `wire_store_observer.py` output beyond
  the intended env hop.
- **Stringly scope:** `LaunchOverlay.scope: str` collapses the UI's
  `OverlayScope = "shared" | {kind, cwd}` union into `"shared" | <cwd string>` on
  the wire. Tolerable for the slice; a review nit, not a blocker.
- **Dead code:** `UNKNOWN_CWD` / `hydrateDraftCwd` sentinel machinery survives the
  move to core; it is still the documented placeholder for a later cwd-hydration
  slice, not removable here.
- **Duplication:** none introduced; the wip's `overlaysStore` move is a true
  rename (old inspector copy deleted, single persistence key re-derived via
  `useOverlaysStore.persist.getOptions().name`). No parallel implementation left.

## Plan

1. **Salvage:** branch from current `main`, cherry-pick or rebase `23a49430`
   (`wip/canvas-overlay`). Resolve drift against the files this worktree already
   has dirty (`addon_runtime.py`, `captured/*`, `cli/*` are mid-flight on
   `feat/harvest-gates`; coordinate with the orchestrator on ordering).
2. **Review pass (builder + reviewer), keyed to the hazards above:** store-writer
   precedence statement; `initial_overrides` leak audit across
   `launch/environment.py`, lifecycle emission, `wire_store_observer.py`;
   localStorage origin story; root-track-only scoping stated in the PR.
3. **Pinning test check:** keep the wip's seam tests; ensure one end-to-end
   pinning test exists that fails without the seed — `test_addon_runtime`'s
   `load_capture_runtime` seed test plus
   `test_prepare_selects_launch_overlays_after_worktree_resolution` together
   cover it; add nothing beyond what is missing.
4. **Gates (verbatim, builder-driven):** `just test-affected` as the inner loop,
   then `just check` and `just test` as merge authority; CI is the verdict.
5. **User test (Stuart):** the click path in Reuse Map section 5; the observable
   is the curated note in the canvas exchange viewer and the before/after char
   counts in the Inspector audit.
