# Scout: Canvas overlay boundary

Scout artifact for the canvas-overlay-boundary warroom, phase 1. Tree: `c03edbd9` in
`.claude/worktrees/canvas-overlay-boundary`. Binding owner decision (cm
`019fdb4f-abf7-7a12-a3be-bbda623caa68`): Canvas overlays are automatic and non-blocking; never
Arm, Pause, Forward, Pass Through, Drop, timeout, paused-flow state, or bridged Inspector
breakpoint state. Inspector breakpoint stays a separate concern and is not deleted. This scout
maps what exists; it designs nothing.

Verification note: `/code-review` was launched with this scope; Stuart stopped it mid-run. One
of its angle agents (altitude audit) completed and returned findings before the stop. Findings
below are marked CONFIRMED (I verified against source) or PLAUSIBLE (agent-reported, unverified).

## Current journey, as it exists today

The word "overlay" names a persistent request transform: a named `Override[]` bundle with a
`shared | project(cwd)` scope. The journey the brief describes exists in three fragments with
the middle missing.

**1. Selection and launch: none found.** No launch path, canvas or CLI, carries an overlay.
Searches run: `overlay` across `www/packages/canvas/src` (only screen-space UI overlays:
`LayoutCanvas` overlay slot, `CanvasDragSessionOverlay`, `PaneDock`), `www/packages/canvas/src/launcher/commandTypes.ts`
(none), `packages/*` and `api/.../controlplane` and `api/.../launch` (two incidental comment
uses of the word, no concept). `NOW.md` records the intent: overlay belongs in the launch
specification (`FrozenLaunchSpec` / `candidate_key`), unbuilt.

**2. Overlay authoring and storage: Inspector-only, write-only.** Overlays live in
`www/packages/inspector/src/stores/overlaysStore.ts:useOverlaysStore`, a zustand slice persisted
to browser localStorage (`stores/persistence.ts`, key `INSPECTOR_STORAGE_KEYS.overlaysStore`).
The only creation path is `BreakpointEditor.tsx:handleSaveAsOverlay` → `createDraft` over a
paused flow's override list, then `OverlaysView.tsx` confirms name and scope.
`OverlaysView.tsx` states it in its own doc comment: "The apply-at-intercept pipeline does not
live here yet. This view is pure curation." Nothing reads a confirmed overlay
(`useOverlaysStore` importers: `BreakpointEditor.tsx`, `OverlaysView.tsx`, tests — nothing else).

**3. Request pipeline application: ships, automatic, non-blocking — but fed only by per-run
Inspector edits, never by overlays.** `request_pipeline.py:run_pipeline` applies
`overrides/__init__.py:apply_overrides` over `overrides/state.py:OverrideStore` per scope
`(run_id, track_id)`, producing `curated_ir` plus `OverrideAudit`. Fail-open: any exception
forwards unmodified. `addon_handlers.py:handle_http_request` then decides pausing separately:
`pause_request = not _should_skip_breakpoint(...) and bp.is_armed()`; when not paused, the
curated bytes go out immediately via `request_diff.py:outbound_request_if_changed`. The Codex
websocket path mirrors this in `addon_handlers.py:handle_codex_websocket_message`. The apply
pipeline is correctly independent of arming; pause is a separate branch.

**4. Evidence: persisted and served, barely revealed in Canvas.**
`flow_state.py:capture_request_flow_state` carries `request_ir`, `curated_request_ir`, `audit`;
`exchange_recorder/artifacts.py` persists them; `api/v1/exchanges.py:ExchangeDetailResponse` serves
`request_curated_ir` and `request_audit`. Canvas renders through the locked-decision read-only
fork `www/packages/canvas/src/viewers/resource/ArkExchangeViewer.tsx` /
`ArkExchangePanels.tsx:ExchangeInspectPanel`, which shows curated-first content plus one
sentence: "Showing the request as sent. The pipeline or a breakpoint edit mutated the
original." `request_audit` is fetched and unused in Canvas; no original-vs-curated, no
before/after char counts, no savings. The rich reveal (char accounting, per-block attribution)
exists only in Inspector editor components attached to the paused-flow surface.

## Reuse Map

For each capability the overlay journey needs: the owning symbol, writers, readers, and current
precedence. Cite these owners in every build brief; a second writer to any of them without a
precedence rule is a defect.

| Capability | Owner | Writers | Readers | Precedence today |
|---|---|---|---|---|
| Overlay persistence (browser) | `overlaysStore.ts:useOverlaysStore` | `BreakpointEditor.tsx:handleSaveAsOverlay` (createDraft); `OverlaysView.tsx` (updateDraft/confirmDraft/discardDraft/remove) | `OverlaysView.tsx` only | Single store; singular `draftId`, second draft replaces first (loud in dev) |
| Standing request edits | `overrides/state.py:OverrideStore` via `get_store()` (module-global, per process) | `api/v1/overrides.py:patch_overrides / delete_overrides / toggle_overrides`; `shared_proxy/addon.py` on `SetOverridesRequest` | `request_pipeline.py:run_pipeline`; `api/v1/overrides.py:get_overrides`, `_snapshot_scope` | Last write per `(kind, target)` per scope; `enabled` defaults True; scope normalized via `state.py:normalize_scope`, no-scope maps to `__legacy__` root; exact-scope lookup only, no shared→project→run cascade |
| Cross-process override sync | `shared_proxy/manager.py:SharedProxyManager.set_overrides` | `api/v1/overrides.py:_sync_shared_overrides` (hand-called in three route handlers) | shared subprocess `OverrideStore` | API-process store is authoritative in intent; sync is per-call-site, see Q1 |
| Application + audit | `overrides/__init__.py:apply_overrides`; `overrides/audit.py` | — | `run_pipeline` | Pure; fail-open in `run_pipeline` |
| Track scoping | `track_manager.py` (`classify_request`) | addon | `run_pipeline` | Track scope wins when assignment exists, else root scope |
| Wire mutation | `request_diff.py:outbound_request_if_changed` | — | `addon_handlers`, `pause_session.py` | Only writes when curated differs |
| Evidence persistence/read | `flow_state.py:capture_request_flow_state` → `exchange_recorder/` → `api/v1/exchanges.py:ExchangeDetailResponse.request_curated_ir/.request_audit` | addon | Inspector detail; Canvas `ArkExchangePanels.tsx` (curated only, audit unused) | Tier-1 then serve; no provenance field distinguishing overlay curation from a breakpoint edit |
| Pause machinery (Inspector-only concern) | `breakpoint.py` module globals `_mode`/`_paused` (`arm/disarm/pause/release/drop`, `PausedFlow`) | `api/v1/breakpoint_routes.py`; `addon_handlers`/`pause_session.py` | same | Per-process globals; `armed_once` consumed at next pause |
| Canvas run hosting | per-run mitmdump with embedded API: `CaptureLeaseRegistry.prepare_capture`, `RunManager`, `addon_runtime.load_runtime`, `web_runtime.start_web_runtime` | — | — | Each canvas run's proxy and breakpoint API live in that run's own process |
| Canvas non-arming guarantee | none — call-site absence | — | — | The run's embedded API exposes `/api/breakpoint/arm` and it would engage; nothing in the Canvas journey calls it (no UI affordance, no client). Plus per-binding `shared_proxy/binding.py:ProxyRunBinding.breakpoint_skip_models` (string-contains model filter, built in `owned_transcript_binding.py` from `config.py:Settings.breakpoint_skip_models`) |
| Overlay-at-launch seam (future) | none found | — | — | `NOW.md` names `FrozenLaunchSpec` / `candidate_key` as the intended home |

## Coupling findings: overlay journey ↔ breakpoint semantics

- **C1 (visible, authoring).** Overlay creation is reachable only through an armed pause:
  `BreakpointEditor.tsx:handleSaveAsOverlay` is the sole `createDraft` caller, and
  `OverlaysView.tsx:EmptyState` instructs "Save a breakpoint edit to begin." Since a canvas run
  is never armed, no overlay can ever be authored from the Canvas surface. CONFIRMED.
- **C2 (visible, evidence).** The only Canvas-visible overlay evidence is the curated note in
  `ArkExchangePanels.tsx`, whose text names breakpoints ("The pipeline or a breakpoint edit
  mutated the original") and which cannot distinguish overlay curation from a breakpoint edit —
  no provenance travels on `ExchangeDetail`. CONFIRMED.
- **C3 (implementation, invariant).** "A canvas run is never armed" is UI/call-site absence,
  not a boundary (Opus reconciliation). Canvas runs today use a per-run mitmdump with the API
  embedded in the same process (`CaptureLeaseRegistry.prepare_capture`, `RunManager`,
  `addon_runtime.load_runtime`, `web_runtime.start_web_runtime`), so that run's
  `/api/breakpoint/arm` is present, reachable, and would engage; it never fires only because
  nothing in the Canvas journey calls it. Per `docs/ARCHITECTURE.md` boundary standard this is
  the weakest enforcement tier. Armability is undeclared on the run; `ProxyRunBinding` (where
  `breakpoint_skip_models` already lives) is the natural declaration point.
- **C4 (implementation, API).** `api/v1/overrides.py` couples override CRUD to paused-flow
  state: `_update_scoped_paused_preview` / `_paused_scope` read `bp.get_paused()` and rewrite a
  paused flow's `curated_ir`/`audit` on every mutation. It degrades to no-op with no paused
  flow, so the automatic path works, but the route module is written against breakpoint state.
  Sub-finding (PLAUSIBLE): the scopeless branch grabs an arbitrary paused flow
  (`next(iter(paused.values()))`) and overwrites its preview with `__legacy__`-scope overrides a
  run-scoped pipeline will never apply.
- **C5 (naming).** Three senses of "overlay" coexist: the request overlay (this feature), canvas
  screen-space UI overlays (`LayoutCanvas` overlay prop, `CanvasDragSessionOverlay`), and the
  Inspector paused-flow fullscreen overlay (`uiStore.ts` — "clearPausedFlow ... clears the
  overlay"). Plus the unrelated runtime home overlay (`cli/home_overlay.py`). Briefs must
  disambiguate; ubiquitous-language risk is high. CONFIRMED.
- **C6 (gap, not coupling).** Overlays never reach `OverrideStore`. The journey's middle is
  absent; `OverrideStore` is the reuse owner when it is built. A second overlay-application
  store would be a second writer to owned state with no precedence rule.

## Quality Map

- **Q1 — CONFIRMED correctness defect, scoped to shared-proxy-bound runs.**
  `api/v1/overrides.py:delete_overrides` with no scope calls `store.clear()` (whole API-process
  store), then `_sync_shared_overrides` early-returns on `run_id is None`: shared-subprocess
  stores are never told, so runs bound through `SharedProxyManager` keep applying overrides the
  UI just confirmed cleared. Today's Canvas runs (per-run mitmdump, embedded API) are not on
  that path. Root shape: two `OverrideStore` singletons reconciled by hand at three call sites;
  publication belongs on the store/manager seam (enforce-at-boundary standard), so a future
  writer (MCP verb, director API) cannot forget it.
- **Q1b — CONFIRMED lossy rollback in the same route.** On the scopeless branch,
  `delete_overrides` snapshots only the `__legacy__` root scope (`previous =
  _snapshot_scope(scope)`), then calls `store.clear()` across all scopes; if the subsequent sync
  raises, `_restore_scope` puts back only the `__legacy__` snapshot and every other scope's
  overrides are silently lost.
- **Q2 — REJECTED for embedded Canvas (Opus reconciliation).** The altitude agent flagged
  `meta?.cwd` in `BreakpointEditor.tsx:handleSaveAsOverlay` as the backend's cwd rather than the
  run's. With the per-run embedded API, meta.cwd is the run's own backend, so the stamp is
  correct on today's Canvas path. Revisit only if a shared multi-workspace backend arrives.
- **Q3 — OUT OF SCOPE for the current Canvas journey (Opus reconciliation).**
  `shared_proxy/models.py:_infer_mode_kind` dispatches on harness name (`== "codex"`) against
  the dispatch-on-capability doctrine; real, but it sits on the shared-proxy path today's Canvas
  runs do not use.
- **Q4 — UI-only storage.** Overlays exist only in one browser profile's localStorage: no
  backend resource, no `@tm/contract` type, invisible to the director and the ⌘K twin client.
  Violates the North Star API-first rule the moment overlays become behavior. The Python
  `overrides` package already owns the override model and scoping vocabulary.
- **Q5 — duplication seam.** The HTTP and Codex-websocket handlers duplicate the
  pipeline→skip→pause→persist sequence (`handle_http_request` ~88 lines,
  `handle_codex_websocket_message` ~132 lines, approaching the 150 limit). Groom when touched.
- **Q6 — hygiene baseline.** No file in scope exceeds 700 LOC (largest: `addon_handlers.py`
  496, `overrides/__init__.py` 430). `__legacy__` root-scope sentinel (`state.py:LEGACY_SCOPE_ID`)
  is live legacy vocabulary on every unscoped call. Overlays being write-only is a recorded
  feature gap, not dead code.

## Decision needed (dispositions for Stuart, per the surface-and-decide gate)

1. **Overlay application binds to `OverrideStore`?** Reuse (recommended): applying an overlay =
   writing its `Override[]` into `OverrideStore` at run (or track) scope, on the existing
   `PATCH /v1/overrides` + `SetOverridesRequest` path. Deviation would mean a second writer.
2. **Overlay storage moves behind the API?** Q4: keep localStorage (deviate, UI-only) or move
   overlays to a backend-owned resource so launch, director, and Canvas can read them. The
   North Star rule points at the latter; sequencing is Stuart's call.
3. **Authoring entry decoupled from pause?** C1: does the Canvas journey need an overlay
   authoring/selection path that does not require arming a breakpoint? (This is an entry-point
   question, not a pause-behavior question.)
4. **Canvas evidence reveal.** C2: render `request_audit` (already served) in
   `ArkExchangePanels`, with provenance wording that does not lean on breakpoint language.
   Reuse-bound: the field exists; only the Canvas fork renders nothing.
5. **Declare non-armability at the boundary.** C3: make "this run never pauses" a declared
   property (e.g. on `ProxyRunBinding`, checked at the `handle_http_request` pause branch)
   rather than topology luck. Does not touch Inspector breakpoint behavior on its own surface.
6. **Fix Q1 now or with the slice?** It is a live correctness defect on the automatic path
   independent of any new work.

## Reuse-bound next steps (no design, no code yet)

- Any build slice binds to: `OverrideStore` + `run_pipeline` (application), `PATCH
  /v1/overrides` + `SharedProxyManager.set_overrides` (propagation),
  `ExchangeDetail.request_audit` (evidence), `ArkExchangePanels.ExchangeInspectPanel` (Canvas
  reveal), `FrozenLaunchSpec`/`candidate_key` (launch selection, when that slice comes).
- No slice touches `breakpoint.py`, `breakpoint_routes.py`, `pause_session.py`,
  `useBreakpoint`, or `uiStore.pausedFlow` except to *read nothing from them* — the boundary is
  that Canvas code holds zero imports from the pause machinery (already true; keep it pinned).

## Proof gates

- Existing anchors: `shared_proxy/test_addon.py` (runs with `is_armed` False),
  `api/v1/test_overrides.py:TestBypassPreview`, `overrides/test_facade.py`,
  `test_addon_phases.py` (audit/token stamping), `api/v1/test_breakpoint.py`.
- Q1 pinning test (fails before fix): scopeless `DELETE /v1/overrides` while a run is bound in
  `SharedProxyManager.by_run_id` must clear the subprocess scope too — assert via
  `SharedProxyManager` control traffic or subprocess store state.
- Q1b pinning test (fails before fix): scopeless `DELETE /v1/overrides` whose sync raises must
  restore every scope that existed before the clear, not only `__legacy__`.
- Boundary test for C3 once dispositioned: a canvas-hosted run whose binding declares
  non-armability forwards without pausing even when that run's own `/api/breakpoint/arm` is
  called (observable end-state: response completes, no `PausedFlow` entry).
- Canvas boundary pin: import-graph test that `www/packages/canvas` never imports breakpoint
  hooks/stores (extend the existing inspector↔canvas boundary test in the shell suite).
- Merge authority: `just check` and `just test`; CI is the verdict.
