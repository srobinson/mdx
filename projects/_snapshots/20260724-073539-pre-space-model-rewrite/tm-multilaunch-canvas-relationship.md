# Canvas relationship dig (launch_batch scope)

Date: 2026-07-20  
Checkout: multi-launch worktree  
Method: code search + reads (fmm index absent in this worktree: no `.fmm.db`; used `rg` / file reads)

## Disambiguation (do not conflate)

| Sense | What it is | Evidence |
| --- | --- | --- |
| **Canvas (product entity)** | User-switchable, named **group of panes** under a Space; organization + layering | `space.models.Canvas`, client `CanvasModel` |
| **Canvas (built bundle)** | Embedded SPA at `/canvas` from `api/src/transport_matters/canvas/` | `Agents.md` www naming; not a domain model |
| **`launch_kind: "canvas"`** | Product intent flag on capture prepare (`canvas` vs `service`) | `ports.ts::CAPTURE_LAUNCH_KINDS`, `CapturedRunRequest.launch_kind` |

This dig is about the **product entity** only.

## Relationship diagram

```text
                    Space (server)
                   /              \
          Worktree (N)          Canvas (N)   ← named group; server row + client key
             |                     |
          path/cwd            default_worktree_id?
             |                     |
        Workspace                 panes: Record<PaneId, PaneRecord>  (CLIENT store)
     (slug/hash from               |
      canonical path)         contentRef.kind = captured-run | terminal | ...
             |                     |
             |                runKey ──► CapturedRunRecord.runId  (CLIENT)
             |                     |
             └──── workdir ──► RunManager run (flat by runId)
                                   │
                         per-run storage + runtime-home
                         CLAUDE_CONFIG_DIR / CODEX_HOME
```

No edge from **run → canvas** exists server-side today.

---

## 1. Is canvas modeled?

**Yes, dual-layer. Pane membership is client-primary.**

**Server (durable identity + empty-ish layout bag):**

- `api/src/transport_matters/space/models.py::Canvas`, `CanvasId`
- Table `canvas` (migration `0006_spaces_foundation`): `canvas_id`, `space_id`, `name`, `default_worktree_id`, `layout` jsonb, `layout_version`
- `space.store.SpaceStore.list_canvases` / `create_canvas` / `update_canvas`
- REST skins: `api/v1/space_routes.py::list_space_canvases`, `create_canvas`, patch canvas

**Client (live pane group + switch key):**

- `www/packages/canvas/src/model/paneRecords.ts::CanvasModel` holds `canvasId`, `panes`, `layout`, `defaultWorktreeId`
- `canvasState.ts::CanvasStoreModel` / `createInitialCanvasModel`
- `route.ts::CanvasLaunchContext`, `defaultCanvasId` (explicit `canvas_id` URL, else `space:{spaceId}`, else `workspaceHash` / `direct-local`)
- Persistence: `canvasCacheStorage.ts::createCanvasCacheStorage` namespaces **localStorage** by `canvasId`; `canvasStoreLifecycle.ts::initializeCanvas` switches caches without leaking panes

**Searches for “panes are flat only”:** rejected. There is a real `Canvas` type and a non-flat `panes` map. What is **not** found: any run or `RunManager` field carrying `canvasId`; any client sync of open panes into server `canvas.layout` (server layout API exists; product pane state lives in namespaced localStorage).

**Not found:** server “pane” table, run↔canvas join, `RunManager` grouping by canvas.

---

## 2. Cardinality

**Corrected form (not a pure workdir tree):**

| Edge | Cardinality | Where represented |
| --- | --- | --- |
| Space → Canvas | 1:N | Server FK `canvas.space_id`; list/create routes |
| Space → Worktree | 1:N | Server `space_worktree`; worktree path is the practical **workdir** |
| Canvas → default worktree | N:0..1 | `Canvas.default_worktree_id` |
| Canvas → Pane | 1:N | **Client only** `CanvasModel.panes` |
| Pane → Worktree | N:1 (required for captured-run/terminal) | `PaneContentRef.worktreeId` |
| Workdir/workspace → Canvas | **no FK**; UX 1:N under one Space | Canvas keys off space/default id, not path |

**`workdir : canvas : pane == 1:N:N` is approximately true only as product UX** (“same project root, switch named layouts, many panes each”). **Schema is Space-centric**, not workdir-centric. Same worktree path can host panes across multiple canvases; canvases do not own workdirs.

**Persisted grouping key:**

- Server: durable `canvas_id` + name + optional default worktree + opaque `layout` jsonb
- Client: durable-ish **localStorage** blob per `canvasId` (panes, rects, dock, counters)
- Ephemeral process: active `canvasId` in `canvasStoreLifecycle` module + zustand store

---

## 3. Bind point: pane/run → group

**Launch attach path (palette):**

`templateRows.ts::spawnCommand`  
→ `CanvasCommandDispatcher` / `useCanvasCommandHandler`  
→ `canvasActions.ts::addCapturedRun`  
→ `spawnCapturedRunPane` (pane with `runKey` in current store)  
→ `useCapturedRunBinding` / `capturedRunStore.ts::ensureRun`  
→ `transport.ts::createCapturedRunView` → `POST /v1/runs`  
→ `RunManager.createWithDisposition`  
→ capture prepare (`prepare_captured_run` / `build_captured_run_context`)  
→ PTY + `WS /runs/{id}/terminal` attach by **run id only**

**What a run carries today** (`runManagerTypes.ts::CreateManagedRunInput`, `CapturedRunRequest`):  
`owner`, harness, model/effort, cwd/workspaceRoot/workspaceId, **spaceId**, **worktreeId**, agentId, grant, launchKind, name, prompt/delivery, continueFrom, idempotencyKey.

**No `canvasId` / group affinity on the run.**  
`ManagedRunFilters` filters by owner, state, spaceId, worktreeId only.  
Client bind is **pane `runKey` → `CapturedRunRecord.runId`** inside the active canvas’s stores. Service launches can enter the same canvas only via `adoptCapturedRun` after the fact.

---

## 4. Ephemeral home

**Strictly per-run today.**

- Mint path: `captured_run_context.py::_prepare_home_and_grant`  
  `runtime_home_root = prepared.resolved_storage / "runtime-home"`  
  → `cli.runtime_home.plan_runtime_home` / `prepare_runtime_home`
- Child env: `launch_environment` maps managed home to **`CLAUDE_CONFIG_DIR` / `CODEX_HOME`**; also `RUNTIME_HOME`
- Durable run tree: `workspace.run_root` → `~/.transport-matters/workspaces/{slug}/{hash}/{run}/` (workspace identity from canonical path)

**One workdir + multiple panes ⇒ multiple runs ⇒ multiple HOMEs.** Homes are not shared per canvas or per workdir.

---

## 5. Vocabulary reconcile

| Term | Canonical definition | Conflation flags |
| --- | --- | --- |
| **worktree** | Git-backed Space row (`Worktree` path, branch, primary/missing); client also uses `worktreeId` as **spawn root** for panes | Overloaded: git topology vs “cwd handle” on every spawn |
| **workdir / target path** | Process CWD for a launch (`CreateManagedRunInput.cwd`, `CapturedRunRequest.directory`, launch contract `workdir`) | Contract “workdir” ≈ resolved worktree path or explicit directory |
| **workspace** | Capture unit: identity from **canonical path** (`workspace.workspace_id` → slug/hash); storage under `~/.transport-matters/workspaces/...` | Distinct from Space; two checkouts of same path share history |
| **canvas** | Named **pane group** under a Space (org + layering); switchable via URL/`canvasId` + per-id client cache | Bundle dirname `api/.../canvas/`; `launch_kind=canvas`; colloquial “the canvas app” |

---

## 6. Bearing on `launch_batch`

| Question | Fact |
| --- | --- |
| Do N batch candidates become N panes in ONE canvas? | **Not automatically.** N candidates ⇒ N independent runs/HOMEs. They become panes only if the **active client canvas** calls `addCapturedRun` / `adoptCapturedRun` N times (or one batch adopt helper). |
| Does ⌘K / director land in current canvas or flat runs? | **⌘K:** current canvas (`addCapturedRun` on active store). **Director/control-plane service launch:** flat runs at `RunManager`; no canvas key; optional later `adoptCapturedRun` into whatever canvas is open. |
| Existing grouping to reuse? | **Reuse for UI placement:** active `CanvasModel` + `adoptCapturedRun` / spawn path. **Reuse for identity:** server `Canvas` under Space if you need named multi-layout. **Do not invent** `run.canvasId` unless you add affinity substrate. **Do not** treat server `canvas.layout` as live pane membership (client localStorage owns panes today). |

**Implication for batch scope:** batch verb remains a **launch/identity** concern (dispatch + candidate_key + fanout). Canvas is a **presentation placement** concern after receipts exist. Coupling batch semantics to “one canvas” would be new product policy, not an existing server invariant.

---

## Reuse vs missing (canvas grouping specifically)

| | |
| --- | --- |
| **Reuse** | Server `Canvas` / Space APIs for named multi-canvas identity; client `CanvasModel`, `defaultCanvasId`, namespaced cache, `addCapturedRun` / `adoptCapturedRun` into the **current** canvas; run filters by space/worktree |
| **Missing** | Run→canvas affinity; server-authoritative pane membership; any batch→canvas placement contract; shared HOME per canvas (explicitly not present; per-run homes stay) |

**Verdict for scope decision:** canvas **is modeled** (Space-scoped named entity + client pane group). It is **not** a launch-ledger dimension. `launch_batch` should not wait on canvas substrate; optional post-launch adopt into the active canvas is the existing grouping seam.
