# CMDK launch-from-empty-DB scout

**Branch:** `ml/s3-cmdk` @ `0c76d520`  
**Repo:** transport-matters worktree `.claude/worktrees/multi-launch`  
**Date:** 2026-07-25  
**Mode:** read-only; reuse map only; no UI design (S4 owns UX)

## Spec (Stuart)

Empty DB → only "Create new space". Spaces always listed (even when count is 1). After input submodal submit, return to previous menu with the new item selected (do not close CMDK). ArrowRight on a Space → its workdirs + "Create new Workdir". Selecting a worktree activates `{spaceId, worktreeId, canvasId}` via its root canvas. Then Agents → `{kind:"spawn"}` succeeds.

---

## 1. ROOT CANVAS AVAILABILITY — **present**

The inventory payload already carries the root canvas id for every existing worktree. No backend field or extra fetch is required for activation.

| Layer | Symbol | Evidence |
| --- | --- | --- |
| Store / ensure | `SpaceStoreWorktreeOps.ensure_worktree_root` | Creates the worktree_root canvas keyed by `worktree.root_canvas_id` |
| Domain record | `WorktreeRecord.root_canvas_id` (alias `rootCanvasId`) | `space.models.WorktreeRecord` |
| Nested in list | `SpaceSummary.worktrees: list[WorktreeRecord]` via `space_summary` | `api.v1.space_contracts.SpaceSummary` / `space_summary` |
| REST list | `list_spaces` → `ListSpacesResponse` | `api.v1.space_routes.list_spaces` embeds full worktrees |
| Transport client | `WorktreeSummary.rootCanvasId` | `@tm/core` `spaceTransport.WorktreeSummary` |
| Create path | `createWorkdir` → `response.worktree` | Same type; dispatcher uses `worktree.rootCanvasId` |
| Frontend rows | `worktreeRowActions(..., worktree.rootCanvasId)` | `workdirRows.worktreeRowActions` / `buildWorktreeRows` |
| Activate | `select-worktree` → `activateWorktree` | `CanvasCommandDispatcher` case `select-worktree` + module-local `activateWorktree` |

**Conclusion:** root canvas id is **present**. Existing worktree rows already bind `select-worktree` with the full triple. Optional `fetchCanvases` / `fetchCanvas` exist but are not needed for this launch path.

---

## 2. DISCLOSURE GATE

**Primary hide rule (client):** `buildSpaceRows` early-returns create-only rows when `!showSwitcher || count <= 1`.

```
buildSpaceRows(spaces, activeSpaceId, count, showSwitcher, status)
  → if (!showSwitcher || count <= 1) return [createSpace, createWorkdir, status…]
  → else append spaceManagementRows for every space
```

**Server flag that feeds it:** `list_spaces` sets `show_switcher=space_count > 1` (`space_routes.list_spaces` → `ListSpacesResponse.show_switcher`).

**Call / thread sites:**

| Symbol | Role |
| --- | --- |
| `space_routes.list_spaces` | Computes `showSwitcher` |
| `fetchSpaces` / `SpaceListResponse.showSwitcher` | Wire type |
| `fetchSpaceInventory` | ORs `page.showSwitcher` across pages |
| `useSpaces` | Exposes `showSwitcher` |
| `useLauncherData` | Maps to `showSpaceSwitcher` |
| `useLauncherRows` / `ScopeRowInputs.showSpaceSwitcher` | Thread into row builder |
| `buildScopeRows` case `"workdir"` | Calls `buildSpaceRows(..., spacesCount, showSpaceSwitcher, ...)` |
| `buildSpaceRows` | **Gate owner** |
| `CommandCenter.spaces.test` / `commandRows.test` | Encode the >1 progressive-disclosure contract as expected behavior |

**Defect vs Stuart:** with one Space, `showSwitcher` is false and the Space row is hidden. Spaces must always list when `count >= 1`.

**Secondary defect:** `createWorkdirRow()` is always prepended, including empty inventory. Spec: empty DB shows only "Create new space".

**Tertiary defect:** `spaceManagementRows` only sets `advance` when `space.worktrees.length > 0`, so a Space with zero workdirs cannot drill. Spec needs always-drill + "Create new Workdir" inside the worktree scope (`buildWorktreeRows` currently has no create row).

---

## 3. SUBMODAL RETURN

**Closes CMDK after input submit:** `useCommandCenter` → `onInputKeyDown` branch for `spaceInput !== null && Enter`:

1. `completeSpaceCommandInput(spaceInput, value)`
2. `onCommand(command)`
3. **`close()`** ← this is the close owner

Incomplete commands stay open via `interactionFor` + `spaceCommandInputFor` returning non-null → `run-stay` → `beginSpaceInput`.

**Existing back / pop (reuse, do not invent):**

| Symbol | Behavior |
| --- | --- |
| `popFrame` | Drop one nav frame; parent retains `highlightedValue` stamped by `pushFrame` |
| `useNavFrameStack.back` | `setStack(popFrame)` |
| `useLauncherInputKeys` | ArrowLeft / Backspace when query empty → `back()` |
| `cancelSpaceInput` | Clears `spaceInput`, query, highlight; **does not close** and **does not pop** |
| `Lifecycle` values | `run-stay`, `run-close`, `descend`, `commit-close`, `none` |

There is **no** dedicated "pop input and preselect row X" helper. Closest reuse:

- Stay open: replace `close()` with `cancelSpaceInput()` after a successful complete (same menu frame).
- Preselect: `setHighlighted(value)` / `updateTopFrame({ highlightedValue })` after inventory refresh once the new row's `value` is known (`space:{id}`, `worktree:{id}`, etc.).
- Drill-in origin highlight already works via `pushFrame(..., originValue)` + `popFrame`.

Completed mutations currently use default `RUN_AND_CLOSE` via `interactionFor` when not collected as input (`COMMAND_INTERACTIONS` has no create-space/create-workdir entries). Input path bypasses that and hard-closes; completed non-input path would also close if ever fired that way.

---

## 4. SELECT-WORKTREE COMMAND — **exists**

| Symbol | Role |
| --- | --- |
| `LauncherCommand` kind `"select-worktree"` | `{ spaceId, worktreeId, canvasId }` |
| `worktreeRowActions` | Enter → `select-worktree`; ArrowRight advance → `agents` scoped by `worktreeId` |
| `buildWorktreeRows` | One live row per worktree; disabled when `missing` |
| `CanvasCommandDispatcher` case `"select-worktree"` | Calls `activateWorktree(command)` |
| `activateWorktree` | `worktreeSwitchUrl` + `initializeVerifiedCanvas` (sets space/worktree/canvas) |
| `createWorkdirWithBootstrap` | On success already calls `deps.activateWorktree({ spaceId, worktreeId, canvasId: worktree.rootCanvasId })` |
| `select-space` / `activateSpace` | Space-only; clears rooted canvas path when empty Space selected (known) |

Bind to these; do not invent a second activation path.

---

## 5. SPAWN ERROR SURFACING

**Swallows into console (pre-pane throw):**

- `useCanvasCommandHandler` → case `"spawn"`: `try { addCapturedRun(...) } catch { console.error("Failed to spawn captured run:", error) }`
- Same file: `"spawn-terminal"` and Space mutation `.catch(console.error)`

Throw source: `requireWorktreeId` / `ROOTED_WORKTREE_REQUIRED_MESSAGE` when `defaultWorktreeId` is null (`worktreeDefaults.requireWorktreeId`, used by `createCapturedRunActions.addCapturedRun`).

**Stuart's backend message** (`capture_rpc_routes`: "Canvas launches require spaceId, worktreeId, and canvasId") is a **POST /v1/runs** rejection after a pane exists. That path already surfaces UI:

| Symbol | Role |
| --- | --- |
| `useCapturedRunBinding` | `setSpawnError(spawnErrorMessage(...))` on `ensureRun` reject |
| `CapturedRunPane` | Renders `spawnError` as an alert banner |
| `spawnErrorMessage` | Formats harness label + detail |

There is **no** workbench-level toast store. Existing owners to route pre-pane failures into:

1. **Preferred for POST-time spawn failures:** already handled by `useCapturedRunBinding` / `CapturedRunPane` — keep using it.
2. **For pre-pane `requireWorktreeId` throws:** same banner pattern is the only established spawn-failure UI; routing would mean either ensuring a rooted identity before `addCapturedRun` (primary fix) or promoting a small workbench error strip owned beside existing pane banners (larger; S4). Do not invent a toast library.

Test lock-in: `CanvasWorkbench` test "surfaces a captured-run spawn failure as a non-fatal error" only asserts `console.error` was called (catch, not crash).

---

## 7. CREATE-PATH ACTIVATION DISCREPANCY — **wired, then overwritten** (high priority)

Design intent is correct and **is** implemented on the write path. Stuart's live failure is explained by a **read/re-init race**, not a missing activate call.

### Write path (create → activate) — works

| Step | Symbol |
| --- | --- |
| Create | `createWorkdirWithBootstrap` → `createWorkdir` returns `WorktreeSummary` with `rootCanvasId` |
| Activate call | `deps.activateWorktree({ spaceId: worktree.spaceId, worktreeId, canvasId: worktree.rootCanvasId })` |
| URL | `activateWorktree` → `worktreeSwitchUrl` (`space_id`, `worktree_id`, `canvas_id`) via `history.replaceState` |
| Verify + store | `initializeVerifiedCanvas` → `resolveCanvasLaunchIdentity(parseCanvasLaunchContext(window.location.search), identity)` → `initializeCanvas` |
| Store fields | `canvasState.createInitialCanvasModel` / `canvasStoreLifecycle.initializeCanvas` set `spaceId`, `defaultWorktreeId`, `canvasId` (only if `canvasIdVerified`), and `launch` |

Same activate path for `select-worktree`. Tests lock the create-time activate call: `CanvasCommandDispatcher.test` expects `activateWorktree` with `ROOT_CANVAS_ID`.

### Read path (spawn) — asymmetric + fragile

| Field | Symbol that **reads** at POST time |
| --- | --- |
| `worktreeId` | Pane ref: `createCapturedRunRef` / `addCapturedRun` → `contentRef.worktreeId` (snapshot of store `defaultWorktreeId` or per-spawn id at spawn gesture) |
| `spaceId` | `viewers/registry` captured-run viewer: `props.canvas.launch.spaceId` (**from `launch`, not `store.spaceId`**) |
| `canvasId` | Same viewer: `props.canvas.id` = store `canvasId` = `defaultCanvasId(launch)`, which is **null unless `launch.canvasIdVerified === true`** |

POST builder: `capturedRunStore.ensureRun` → `createCapturedRunView` threads those options into `POST /v1/runs`. Backend: `capture_rpc_routes._resolved_domain_request` rejects canvas launches when any of space/worktree/canvas is null (`canvas_affinity_required` / "Canvas launches require spaceId, worktreeId, and canvasId").

**Shape disagreement:** write sets both store identity fields and `launch`; spawn reads **`launch.spaceId` + store `canvasId` (verified-gated)** + **pane-ref `worktreeId`**. If `launch` is later replaced with an unverified context, `spaceId` and `canvasId` go null for POST even when `store.defaultWorktreeId` / pane still has a worktree.

### Why create-then-spawn still fails (the overwrite)

`SessionCanvasRoute` owns a competing init:

```
search = window.location.search          // evaluated once at first render
launch = useMemo(parseCanvasLaunchContext(search), [search])  // NOT reactive to replaceState
resolvedLaunch = resolveCanvasLaunchIdentity(launch, meta)
useEffect(() => initializeCanvas(resolvedLaunch), [resolvedLaunch])
```

1. `activateWorktree` correctly writes verified identity (live parse of `window.location.search` after `replaceState`).
2. `history.replaceState` does **not** re-render React; `search` in `SessionCanvasRoute` stays the **first-render** query string (often empty on desktop).
3. When `meta` arrives/refetches (`useMeta` / `fetchMeta` → process-cwd affinity, not necessarily the worktree just created), `resolvedLaunch` recomputes from **stale empty launch + meta**.
4. If meta lacks a durable canvas tuple → `resolveCanvasLaunchIdentity` returns **unverified** → `initializeCanvas` sets `canvasId: null` and replaces `launch` with null `spaceId`/`canvasId` (worktree may linger via `?? state.defaultWorktreeId`).
5. If meta has a **different** cwd affinity and launch fields are all null, match rules treat null as wildcard and **adopt meta's triple**, not the created worktree.
6. Spawn then POSTs incomplete or wrong affinity → Stuart's exact backend error.

**Conclusion for PR4:** activation is wired; the bug is **identity not sticky** under `SessionCanvasRoute` re-init. Fix size is larger than "call activateWorktree" (already done): make launch context reactive to URL / stop overwriting a user-selected verified tuple / align spawn reads with the same source of truth. Still frontend-only; no backend field gap.

---

## 8. GRANT ORDERING CONSTRAINT

| Fact | Symbol |
| --- | --- |
| Grant stored for subsequent spawns | `capturedRunStore.controlPlaneGrant` (default `DEFAULT_CONTROL_PLANE_GRANT` / `"none"`) |
| Cycle for next spawn only | `capturedRunStore.cycleControlPlaneGrant` / CMDK `cycle-control-plane-grant` |
| Sent on POST | `ensureRun` always passes `controlPlaneGrant: get().controlPlaneGrant` into `createCapturedRunView` → body always includes grant |
| UI discoverable before spawn | Yes: Settings scope row `"Control plane access"` via `buildSettingsRows` (also reachable under Agents domain settings bundle). Arrow cycles stay-open (`run-stay` advance); Enter is `commit-close` |
| Immutable after prepare | Backend prepare-time grant (parallel MCP scout); UI cycle does not patch live runs |

**Ordering today:** user can set director in Settings **before** Agents → spawn; the next `POST /v1/runs` carries it. Default is `"none"`, so a naive spawn is not MCP-capable until grant is cycled.

**Gaps for "MCP-capable from empty DB":**

- No hard gate that requires director before spawn (ordering is manual, easy to miss).
- Grant lives in Settings, not adjacent to the Agents spawn rows (discoverable but not in the spawn critical path).
- Not a blocker for "spawn succeeds with affinity," but **is** a minimal-change item if the goal includes MCP-ready agents without a second settings pass.

---

## 6. MINIMAL CHANGE SET (revised after §7/§8)

**Verdict: frontend-only.** Root canvas id is on the wire. The load-bearing bug is sticky activation / route re-init, not missing create-time activate.

### FRONTEND-ONLY (priority order)

0. **Sticky verified identity (PR4 size driver)** — Fix `SessionCanvasRoute` so `history.replaceState` activation is not clobbered: make launch parse reactive to URL (popstate / custom event / read `window.location.search` inside memo deps that update), and/or skip `initializeCanvas(resolvedLaunch)` when it would demote an already-verified user selection to unverified/meta-cwd. Align spawn reads: prefer one source (`store.spaceId` + `store.canvasId` + `defaultWorktreeId`, or always `launch` with verified fields). Symbols: `SessionCanvasRoute`, `resolveCanvasLaunchIdentity`, `initializeCanvas`, `defaultCanvasId`, `viewers/registry` captured-run props.  
   **~40–120 LOC** + regression: create workdir → spawn POST body includes full triple. **Flag: can exceed a tiny slice; still one frontend PR.**

1. **`buildSpaceRows` (workdirRows)** — Always list spaces when `spaces.length >= 1`. Empty: only `createSpaceRow`. Gate top-level create-workdir when empty.  
   **~15–40 LOC** + test rewrites.

2. **`spaceManagementRows` + `buildWorktreeRows`** — Always advance into worktree scope; add create-workdir row with `spaceId`.  
   **~20–40 LOC**.

3. **`useCommandCenter.onInputKeyDown`** — After input submit, `cancelSpaceInput()` not `close()`.  
   **~5–15 LOC**.

4. **Post-create selection** — Highlight new `space:{id}` / `worktree:{id}` after refresh.  
   **~20–50 LOC**. Medium if cross-layer.

5. **`interactionFor` run-stay** for completed create-space / create-workdir.  
   **~5–10 LOC**.

6. **Grant pre-spawn (MCP)** — Document or enforce director before spawn if product requires MCP day-one: either leave Settings cycle as-is (manual ordering works) or add a small Agents-adjacent grant affordance / soft block when grant is `none` and MCP is expected. Symbols: `buildSettingsRows`, `cycleControlPlaneGrant`, `ensureRun`.  
   **0 LOC** if manual Settings is acceptable; **~15–40 LOC** for Agents-adjacent cycle or soft gate.

7. **Error routing (optional)** — Pre-pane `console.error` in `useCanvasCommandHandler`; POST failures already use `useCapturedRunBinding` / `CapturedRunPane`. Defer new toast.  
   **0–40 LOC**.

### REQUIRES-BACKEND

None for affinity + grant wire-up. Optional later: drop or redefine server `showSwitcher`.

### LOC / slice risk

| Item | Est. LOC | Slice risk |
| --- | --- | --- |
| 0 Sticky activation / route re-init | 40–120 | **High priority; medium size** |
| 1 Disclosure + empty create-only | 15–40 | Low |
| 2 Worktree drill + create-workdir | 20–40 | Low |
| 3 Submodal stay-open | 5–15 | Low |
| 4 Highlight new item | 20–50 | Medium |
| 5 Lifecycle run-stay | 5–10 | Low |
| 6 Grant pre-spawn | 0–40 | Low–medium |
| 7 Error banner | 0–40 | Defer |

**Total for launch that actually works after create:** item **0 is mandatory**; without it, disclosure/UX polish still leaves Stuart's spawn failure. Happy path ≈ **80–220 LOC** frontend if 0+1+2+3; grant/highlight optional.

---

## Reuse map (bind, do not invent)

| Need | Existing owner |
| --- | --- |
| List inventory | `useSpaces` / `fetchSpaceInventory` / `SPACES_QUERY_KEY` |
| Create space / workdir | `createSpace`, `createWorkdir`, `dispatchSpaceMutation`, `createWorkdirWithBootstrap` |
| Root canvas on create | `WorktreeSummary.rootCanvasId` + `activateWorktree` |
| Root canvas on existing | `buildWorktreeRows` → `select-worktree` |
| Activate triple | `activateWorktree` / `worktreeSwitchUrl` / `initializeVerifiedCanvas` |
| Sticky launch identity | **must fix** `SessionCanvasRoute` + `resolveCanvasLaunchIdentity` interaction |
| Input submodal | `spaceCommandInputFor`, `completeSpaceCommandInput`, `beginSpaceInput`, `cancelSpaceInput` |
| Nav pop / back | `popFrame`, `back`, `pushFrame` origin highlight |
| Spawn | `LauncherCommand` `spawn` → `addCapturedRun` → `ensureRun` |
| POST spawn failure UI | `useCapturedRunBinding.spawnError` → `CapturedRunPane` |
| Grant for next spawn | `capturedRunStore.controlPlaneGrant` / `cycleControlPlaneGrant` / Settings row |

---

## Answer line (for bus)

`done: ~/.mdx/projects/tm-cmdk-launch-scout.md — root canvas id present, frontend-only, activation wired-but-overwritten by SessionCanvasRoute, 8 items (sticky-id mandatory)`
