# S3 sticky-identity scout — canvas launch identity (ml-s3 slice 1)

**Branch:** `ml/s3-cmdk` @ `6413600a` (docs-only above `99510507`; zero code delta, verified via `git diff --stat`)
**Repo:** transport-matters worktree `.claude/worktrees/multi-launch`
**Date:** 2026-07-25
**Mode:** read-only verification of prior claims (`tm-cmdk-launch-scout.md` §7, `tm-bug-archaeology.md`) against the tree. Citations are `file:symbol`.

---

## Verdict on prior-session claims

**CONFIRMED (8):**

1. **Two writers into canvas launch identity, no precedence rule.** Writer A: `workbench/SessionCanvasRoute.tsx:SessionCanvasRoute` effect calling `initializeCanvas(resolvedLaunch)`. Writer B: `workbench/CanvasCommandDispatcher.ts:initializeVerifiedCanvas` (via module-local `activateWorktree`, also the `select-canvas` case). Last writer wins; A can demote B's verified write to unverified (store `canvasId` → null via the `defaultCanvasId` gate in `model/canvasStoreLifecycle.ts:initializeCanvas`).
2. **`buildSpaceRows` disclosure gate.** `launcher/workdirRows.ts:buildSpaceRows` early-returns create rows on `!showSwitcher || count <= 1`; server side `api/v1/space_routes.py:list_spaces` sets `show_switcher = space_count > 1`. With one Space, no Space row.
3. **Drill gates.** `launcher/workdirRows.ts:spaceManagementRows` sets `advance` only when `space.worktrees.length > 0`; `buildWorktreeRows` has no create-workdir row.
4. **Palette closes after input submit.** `launcher/useCommandCenter.ts:onInputKeyDown` Enter branch: `onCommand(command); close()`.
5. **`select-worktree` exists end to end with the full triple** (`launcher/workdirRows.ts:worktreeRowActions` → `CanvasCommandDispatcher` case `"select-worktree"` → `activateWorktree`), and is unreachable in the fresh-DB case: worktree scope is entered only from a Space row's `advance`, and Space rows are hidden at `count <= 1` (claim 2). Reachable with 2+ Spaces.
6. **`WorktreeSummary.rootCanvasId` is on the wire** (`core/src/spaceTransport.ts:WorktreeSummary`); `workbench/spaceCommandDispatcher.ts:createWorkdirWithBootstrap` already activates with it. **No backend work needed.**
7. **Spawn reads the triple from three disagreeing sources.** `worktreeId`: pane ref via `model/canvasActions.ts:addCapturedRun` → `requireWorktreeId(worktreeId ?? get().defaultWorktreeId)` snapshot into `model/spawn.ts:createCapturedRunRef`. `spaceId`: `viewers/registry.tsx` captured-run viewer reads `props.canvas.launch.spaceId`. `canvasId`: same viewer reads `props.canvas.id` = store `canvasId`. All three feed `infrastructure/runtime/useCapturedRunBinding.ts` → `model/capturedRunStore.ts:ensureRun` → `createCapturedRunView` POST; undefined fields are omitted from the body.
8. **Desktop meta affinity is null post-PR1.** `api/v1/meta.py` uses `affinity_from_launch_fields(settings.launch_fields)` only; `cli/desktop_cmd.py:_DESKTOP_BACKEND_STALE_ENV_KEYS` clears `LAUNCH_FIELDS`.

**REFUTED / CORRECTED (2):**

- **"`search` is captured once per mount; the route's stale snapshot clobbers."** FALSE as stated. `SessionCanvasRoute` reads `window.location.search` on every render; the `useMemo([search])` picks up a fresh URL on the next re-render. What is true: `history.replaceState` triggers no render, so between Writer B's write and the next route render the route's **prop** (`resolvedLaunch`, passed as `launch` into `CanvasWorkbench` → `CanvasPaneLayer` viewer `canvas.launch`) is stale. The clobber on re-render is a **verification demotion**, not a stale-URL adoption: `route.ts:parseCanvasLaunchContext` always yields `canvasIdVerified: false`, and with meta null (claim 8) `route.ts:resolveCanvasLaunchIdentity` returns unverified, so the effect re-runs `initializeCanvas` and nulls store `canvasId`.
- **"Null launch fields act as wildcards, so a populated meta makes the route adopt meta's triple instead of the user's selection (silent wrong-worktree launch)."** REFUTED at this baseline for the post-selection case. After `activateWorktree`, the URL fields are populated; `resolveCanvasLaunchIdentity`'s match rules then **compare** (no wildcard), and a mismatch demotes to unverified rather than adopting. Wildcard adoption requires an empty URL, i.e. pre-selection meta seeding, which is the intended behavior, and desktop meta is null anyway. The observable failure is a **POST rejection** (`canvas_affinity_required`, surfaced by `useCapturedRunBinding.spawnError` → `CapturedRunPane` banner), not a silent wrong-worktree launch.

### The actual failure, both legs

Fresh desktop, empty DB: create Space → create Workdir (`createWorkdirWithBootstrap` → `activateWorktree` writes verified triple to store + URL) → spawn.

- **Leg 1 (no route re-render before spawn — the common path):** the captured-run viewer's `spaceId` comes from the route's `resolvedLaunch` **prop**, computed at the last route render (empty URL + null meta → all nulls). `CanvasWorkbench` sources `canvasId` from the **store** but `launch` from the **prop** — the spaceId reader bypasses the store entirely, so Writer B's verified store write never reaches it. POST omits `spaceId` → rejected.
- **Leg 2 (any route re-render before spawn, e.g. meta refetch on window focus):** fresh URL parses with the full triple but unverified; meta null → `resolveCanvasLaunchIdentity` returns unverified → `initializeCanvas` demotes store `canvasId` to null. POST omits `canvasId` → rejected.

Either leg reproduces Stuart's exact backend error ("Canvas launches require spaceId, worktreeId, and canvasId"). Root cause is one defect class: **no single owner of the launch tuple, and Writer A can demote Writer B's verified write.**

---

## (a) REUSE MAP — owning symbols, writers, readers, current precedence

All paths relative to `www/packages/canvas/src/` unless noted.

| State / capability | Owning symbol | Writers | Readers | Precedence today |
| --- | --- | --- | --- | --- |
| Launch tuple parse | `route.ts:parseCanvasLaunchContext` | n/a (pure) | route, dispatcher, `canvasStoreLifecycle.ts:resolveLaunchCanvasId` (module-load persist keying) | Always yields `canvasIdVerified: false` |
| Verification | `route.ts:resolveCanvasLaunchIdentity` | n/a (pure) | route (identity = meta), dispatcher (identity = command triple) | Identity null/mismatch → unverified; null launch fields fill from identity |
| Store identity (`canvasId`, `spaceId`, `defaultWorktreeId`, `launch`) | `model/canvasStoreLifecycle.ts:initializeCanvas` (+ `selectSpace`), fields seeded by `model/canvasState.ts:createInitialCanvasModel` | **A:** route effect; **B:** `CanvasCommandDispatcher.ts:initializeVerifiedCanvas`; **C:** `activateSpace` → `selectSpace` (explicit reset); **D:** `canvasActions.ts:adoptDefaultWorktree` (gap-fill only, via `worktreeDefaults.ts:adoptDefaultWorktreePatch`) | spawn readers below; persistence keying via `getActiveCanvasId` | **A/B: none — last writer wins.** D is the only writer with an explicit precedence rule (never overwrites) |
| URL (durable medium) | `route.ts:worktreeSwitchUrl` / `spaceSwitchUrl` / `canvasSwitchUrl` | B and C via `history.replaceState` | route (per render), dispatcher (live parse) | replaceState does not render React |
| Spawn `worktreeId` | `canvasActions.ts:addCapturedRun` → `worktreeDefaults.ts:requireWorktreeId` → `spawn.ts:createCapturedRunRef` | spawn gesture snapshot | pane `contentRef.worktreeId` | Per-spawn override wins over store default |
| Spawn `spaceId` | `viewers/registry.tsx` captured-run viewer ← `workbench/CanvasPaneLayer.tsx` `canvas.launch` ← `CanvasWorkbench` **prop** ← route `resolvedLaunch` | route render only | `CapturedRunPane` | **Bypasses the store** |
| Spawn `canvasId` | `CanvasWorkbench.tsx` `useCanvasStore(s => s.canvasId)` → `CanvasPaneLayer` `canvas.id` | store (verified-gated) | `CapturedRunPane` | Store, but demotable by Writer A |
| POST builder | `model/capturedRunStore.ts:ensureRun` → `createCapturedRunView` | — | backend `capture_rpc_routes` | Omits undefined fields; backend rejects incomplete canvas launches |
| Space rows | `launcher/workdirRows.ts:buildSpaceRows` (+ `spaceManagementRows`, `createSpaceRow`, `createWorkdirRow`) | — | `launcher/commandRows.ts:buildScopeRows` case `"workdir"` | Gate: `!showSwitcher \|\| count <= 1` |
| Worktree rows | `launcher/workdirRows.ts:buildWorktreeRows` + `worktreeRowActions` | — | `buildScopeRows` case `"worktree"` | Entered only via Space row `advance` (gated on `worktrees.length > 0`) |
| showSwitcher threading | `launcher/useSpaces.ts` → `launcher/useLauncherData.ts:showSpaceSwitcher` → `commandTypes.ts:ScopeRowInputs` → `buildScopeRows` | server `list_spaces` | `buildSpaceRows` only | Dead after step 1 (client side) |
| Input submodal | `launcher/spaceCommandInput.ts:spaceCommandInputFor` / `completeSpaceCommandInput` (spread preserves `spaceId` on `create-workdir` — verified), `useCommandCenter.ts:beginSpaceInput` / `cancelSpaceInput` / `close` | — | `onInputKeyDown` | Submit path hard-closes |
| Lifecycle table | `launcher/commandRows.ts:COMMAND_INTERACTIONS` / `interactionFor` | — | `useCommandCenter` | Input-collecting commands are `run-stay`; completed ones default `RUN_AND_CLOSE` |
| create-workdir command | `commandTypes.ts` `{ kind: "create-workdir"; path?; spaceId?; spaceName? }`; `spaceCommandDispatcher.ts:createWorkdirWithBootstrap` honors `command.spaceId` first | — | — | Already supports scoped create; no new command kind needed |
| POST failure UI | `useCapturedRunBinding.ts:spawnError` → `CapturedRunPane` banner | — | — | Reuse; do not invent |

**None found:** any existing precedence rule between Writers A and B (searched `rg canvasIdVerified`, `rg initializeCanvas` call sites, `SessionCanvasRoute.test.tsx` — no test locks the demotion behavior either, so the builder is not fighting locked expectations). No workbench toast store (matches prior scout).

---

## (b) QUALITY MAP

1. **Second writer to owned state (THE defect):** Writer A (route effect) demotes Writer B's verified store identity with no precedence rule. `adoptDefaultWorktree` (Writer D) shows the house pattern for a precedence-carrying writer — gap-fill, never overwrite.
2. **Boundary inconsistency in `CanvasWorkbench`:** `canvasId`/`workspaceHash` read from the store, `launch` from the route prop; the viewer then mixes both (`canvas.id` store, `canvas.launch.spaceId` prop). One pane props surface, two sources of truth.
3. **Dead threading after step 1:** client `showSwitcher` chain (`useSpaces.showSwitcher` → `useLauncherData.showSpaceSwitcher` → `ScopeRowInputs.showSpaceSwitcher` → `buildSpaceRows` params). Remove client-side in this slice; the server `ListSpacesResponse.show_switcher` field becomes unconsumed — flag for a later contract cleanup, not this slice.
4. **Reuse, not duplicate:** worktree-scope "Create new Workdir" must be `createWorkdirRow` parameterized with `spaceId`, not a second row builder. `completeSpaceCommandInput` already round-trips `spaceId` via spread.
5. **Known deferred (not this slice):** pre-pane `requireWorktreeId` throw still lands in `console.error` (`useCanvasCommandHandler` case `"spawn"`); browser reload of a worktree-activated desktop canvas re-enters Leg 2 with a fresh store (see flag below).

---

## (c) PLAN

Ordered; each step binds to the reuse map. Builder note (gpt-sol seam blind spot): steps 0b and 0c are cross-file seams — the defect is invisible inside any single file.

**Step 0 — sticky identity (size driver).**
- **0a. Precedence rule at the route (needs owner sign-off, decision 1):** recommended shape — when meta is null, resolve against the store's own verified identity: `resolveCanvasLaunchIdentity(launch, meta ?? storeVerifiedIdentity())`, where `storeVerifiedIdentity` exposes `{spaceId, worktreeId: defaultWorktreeId, canvasId}` from `useCanvasStore` when store `canvasId !== null` (invariant: non-null store `canvasId` ⇒ was verified). A URL triple written by Writer B then re-verifies instead of demoting; a genuinely different URL still mismatches and demotes. Alternative rejected: a demotion guard inside `initializeCanvas` couples the store to route semantics and risks legitimate canvas switches.
- **0b. Align the spawn `spaceId` reader on the store:** `CanvasWorkbench` subscribes `useCanvasStore(s => s.spaceId)` and threads it into `CanvasPaneLayer`'s viewer `canvas` props (new field beside `id`); `viewers/registry.tsx` captured-run viewer passes `props.canvas.spaceId` instead of `props.canvas.launch.spaceId`. After 0b all three POST fields trace to the store (worktreeId already snapshots the store default at gesture time).
- **0c. Regression tests (must fail before the fix, assert the observable):** (i) Leg 1 — verified store init via `initializeVerifiedCanvas`-shaped write, no route re-render, spawn → assert `CapturedRunPane`/POST receives the full triple; (ii) Leg 2 — after verified init, force a route re-render with meta null → assert store `canvasId` is not demoted and spawn POST still carries the triple. Home: `SessionCanvasRoute.test.tsx` + `CanvasPaneLayer.test.tsx` (no existing test locks the old behavior).

**Step 1 — `buildSpaceRows`:** list spaces whenever `spaces.length >= 1` (drop `showSwitcher`/`count` gate); empty inventory → `createSpaceRow` only (gate `createWorkdirRow` when empty). Remove the dead client `showSwitcher` threading (quality item 3). Update `commandRows.test.ts` + `CommandCenter.spaces.test.tsx`, which lock the old disclosure contract.

**Step 2 — drill + scoped create:** drop the `worktrees.length > 0` gate on `spaceManagementRows` `advance`; append `createWorkdirRow(spaceId)` in `buildWorktreeRows` (spaceId from the nav `param`). Dispatcher path already honors `command.spaceId`.

**Step 3 — submodal stays open:** `useCommandCenter.ts:onInputKeyDown` success branch calls `cancelSpaceInput()` instead of `close()`. Update the input-flow tests.

**Decisions for the owner (2):**
1. Step 0a seam location: route-side store-identity fallback (recommended) vs store-side demotion guard.
2. Row composition when spaces exist: keep top-level "Create new Workdir" alongside always-listed spaces, or move it exclusively into worktree scope? Spec fixes the empty case only.

**Flagged gap (out of user-story scope):** browser reload of a worktree-activated desktop canvas still loses the verified triple (fresh store, meta null) — needs a backend verification read (e.g. inventory/`fetchCanvases` match) in a later slice.

**Gates (repo recipes, verbatim):** builder loop `just check` + `just test-affected`; authoritative pre-merge full `just check` + `just test` (grok, idle tree). No backend changes expected, so the api suite should be untouched.

---

## Bus line

`done: ~/.mdx/projects/tm-s3-sticky-identity-scout.md confirmed 8 / refuted 2 / decisions needed 2`
