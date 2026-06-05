# Canvas / Worktree CRUD — Grok peer review (delete semantics)

Date: 2026-07-22  
Role: peer review (plan), read-only  
Baseline: `feat/multi-launch` @ `b094e80d69ad7d57c5bba0ff8f4d71a986a837f2`  
Inputs: `tm-canvas-worktree-crud-scout.md`, `tm-canvas-worktree-crud-decision-surface.md`  
Checkout: verified clean tracked tree (untracked `.serena/` only, unchanged)

## Verdict

The scout is a strong foundation map. Twin-client DRY and shared `SpaceCrudService` are sound. The locked v1 matrix (CMDK + MCP through one service) is sound.

**I do not sign off on the CRUD plan as drafted for delete.** The locked cascade-stop decision rests on a path that is not what the code implements, is not server-reusable, and cannot inventory runs by canvas. Subtree delete plus `parent_canvas_id` is also under-specified relative to its blast radius (cycle/depth/transaction/receipt), and neither input doc models a canvas tree.

**Sign-off line:** I sign off conditional on: **#1, #2, #3** (numbered findings below). Non-blocking polish: **#4–#8**.

Tree remained pristine after review (`git status` clean aside from pre-existing `?? .serena/`).

---

## Locked decisions (soundness, not reopening)

| Lock | Soundness |
| --- | --- |
| v1 = Canvas + Worktree CRUD via CMDK **and** MCP (scout v1 matrix) | **Sound** for create/read/update. Worktree delete remains highest-risk; OK in v1 only if lifecycle gate + receipts land in the same slice family as scout PR5. |
| Canvas is a **TREE**; subtree delete; model `parent_canvas_id` (nullable, default null = flat) | **Directionally sound**, **underspecified**. No `parent_canvas_id` in `space.models.Canvas`, `0006_spaces_foundation`, or either input doc. Net-new schema + recursive delete semantics. Flat default is migration-safe; cycle/depth/transaction are not locked. |
| CASCADE-STOP runs via existing pane-close → `DELETE /runs/{id}` | **Unsound premise.** Live path is client-only `POST /v1/runs/{id}/terminate`. See finding **#1** (blocking). |
| Worktree delete **blocks on dirty**; force-with-confirm; never silent discard | **Sound policy.** No space-layer dirty primitive today; closest existing helper is harness minting, not Worktree CRUD. See **#3**. |
| Twin-client: CMDK + MCP → one shared service | **Sound.** Matches scout § Decision 3 / decision-surface §3c and launch-contract pattern. |

Decision-surface still lists **15** open delete policy rows. The mail locks only a subset. Remaining open rows still block a complete PR3/PR5 design: durable archive-vs-hard, service-adopted run policy, primary checkout, untracked, session refs, Canvas default_worktree cleanup, git-remove vs archive-row.

---

## PRIMARY — DELETE semantics pressure test

### 1. BLOCKING — Cascade-stop is not the claimed path and is not server-reusable

**Claim under review:** cascade-stop reuses pane-close → `DELETE /runs/{id}`.

**What the code does today:**

| Step | Actual owner |
| --- | --- |
| Pane close | `canvasActions.closePane` → `dismissPane` → `invokePaneDismissLifecycle(..., "close")` |
| Captured-run close | `capturedRunLifecyclePolicy.onClose` → `capturedRunStore.stopRun` |
| Network | `terminateRun` → **`POST /v1/runs/{runId}/terminate`** (`@tm/core` transport; `runtimeRouter.registerRunRoutes`) |
| Server | `RunManager.terminate` |

There is **no** `DELETE /runs/{id}` route on the runtime router. Agents.md text about `DELETE /runs/{id}` is stale relative to `b094e80d`.

**Why this cannot be bulk-reused server-side for canvas subtree delete:**

1. **No canvas membership on runs.** `RuntimeRunView` carries `spaceId` and `worktreeId` only (`packages/runtime` domain). No `canvasId`. Server cannot list “all runs in this canvas subtree.”
2. **Binding is browser-local.** Pane → runKey → runId lives in `capturedRunStore` (localStorage-backed). Other clients, MCP-only operators, and pure REST callers do not share that map.
3. **Origin split.** `stopRun` terminates only non-`service` origin; service-adopted runs are forgotten without terminate. Subtree “cascade-stop” that copies this policy will orphan director-owned processes; a policy that always terminates contradicts today’s clear/close semantics and needs an explicit lock (decision-surface still marks this open).
4. **Fire-and-forget.** `void terminateRun(...).catch(() => {})` swallows failure. Subtree delete receipts cannot use this shape.
5. **In-flight spawn race (client).** `pendingSpawns` / `cancelledKeys` cancel mid-spawn for one runKey. No equivalent for “canvas entering deleting.” A create that wins after durable delete leaves a live run with no durable canvas.

**Better reuse (structure, not new product policy):**

- Per-run stop: `RunManager.terminate` / gateway `terminate_run` (already used by control plane).
- Bulk with receipts: `ControlPlaneService.close` fans out `gateway.terminate_run` and returns per-id `ManageResult` receipts. That is the existing **server** multi-target stop seam.
- Still missing for canvas subtree: inventory of which run IDs belong to the subtree (net-new index or explicit client-supplied set under a server delete lease).

**Required plan fix before build:** rewrite cascade-stop as a **server inventory + terminate port** (or an explicit “client supplies run IDs + server lease blocks new attaches/creates for those canvases”) with structured receipts. Do not cite pane-close / `DELETE /runs/{id}` as the authority.

### 2. BLOCKING — Subtree cascade + `parent_canvas_id` under-specified for orphans, cycles, partial failure

**Present state:** canvas table is a flat per-space row (`0006_spaces_foundation`, `space.models.Canvas`). No parent edge, no self-FK, no delete primitive.

**Nullable `parent_canvas_id` default null** is data-loss-safe for existing rows (backfill = null, layout preserved). Version: new migration after `0006` (or next free number); bump `layout_version` is unrelated and must not be overloaded as schema version for parent edges.

**Gaps the plan must lock before PR3-equivalent work:**

| Risk | Why it bites |
| --- | --- |
| Self-parent / ancestor cycle | A self-referential FK does **not** prevent A→B→A. Service must reject on write (and on reparent) with a cycle walk or recursive CTE; DB CHECK cannot express arbitrary depth. |
| Cross-space parent | Parent must be same `space_id` + `owner` (mirror `_require_worktree_in_space` for worktrees). FK alone to `canvas_id` is insufficient. |
| Depth limit | Unbounded trees + recursive delete + layout cache fan-out need a hard max (or explicit “no max, document O(n)”). |
| Orphan prevention | On parent hard-delete, children must cascade or reparent. Locked policy is **subtree delete** (children go with parent). Siblings/ancestors untouched: correct if delete walks descendants only. |
| Transactional integrity | Durable rows + localStorage panes + process terminates cannot share one DB transaction. Need multi-phase receipt: (1) lease/mark deleting, (2) stop runs, (3) clear caches/events, (4) delete/archive rows deepest-first or single recursive SQL, (5) release lease. Partial failure after (2) must not report full success. |
| Concurrent reparent into deleting subtree | Without a deleting lease on the whole subtree, a sibling can reparent under a node mid-delete and escape or get deleted unintentionally. |
| Dual layout authority | Scout finding: browser cache keys (`route.defaultCanvasId`, `canvasCacheStorage`) are synthetic (`space:…`, workspace hash, `direct-local`). Subtree server delete does not clear other browsers’ caches without events. Zombie namespaces remain unless UUID migration (scout PR2) lands first or alongside. |

**Migration sketch that is data-loss-safe:**

```text
ALTER TABLE canvas
  ADD COLUMN parent_canvas_id uuid NULL
  REFERENCES canvas(canvas_id) ON DELETE ???;
```

`ON DELETE CASCADE` matches subtree delete only if the product wants hard DB cascade; archive-first policies need `ON DELETE RESTRICT` + service-ordered archive. **Do not ship FK ON DELETE until archive-vs-hard is locked.** Default null backfill is safe either way.

### 3. BLOCKING — Worktree dirty + in-flight writers: order of operations not defined

**Locked policy:** block on dirty; force-with-confirm; never silent discard. Sound.

**Present state:**

- No Worktree create/remove/dirty API in `space.*`.
- Observation only: `space.detection.detect_space` via `git worktree list --porcelain`.
- Closest clean-tree helper: `require_clean_worktree` in `harnesses.certification_minting` (`git status --porcelain --untracked-files=all`). Reuse the **pattern**, not that module’s certification error type, behind a Git worktree port.

**Race with live runs writing the tree:**

1. Delete preflight sees clean tree.
2. Run writes files → tree dirty.
3. Or: preflight sees dirty because a run is actively writing; block forever while runs live; force without stopping runs risks `git worktree remove` failure or data loss.

**Required phase order (plan must state):**

```text
acquire worktree launch gate (block new creates)
→ inventory live + pending + TERMINATING runs for worktree
→ stop or wait per policy (still open for live/terminating)
→ re-check dirty / untracked
→ if dirty and not force → fail with receipt (no git remove)
→ if force → git worktree remove --force (or documented equivalent)
→ reconcile DB (archived / missing / row delete)
→ clear Canvas default_worktree_id refs (FK already ON DELETE SET NULL for hard row delete)
→ release gate
```

Scout already requires atomic launch gate because `resolve_run_worktree` completes before PTY register (`RunManager.createNew` / `pendingCreates`). Confirmed: `pendingCreates` is keyed by owner+idempotency only, **not** worktree; `list` filters registered runs only. Finding #12 in scout is accurate.

**Untracked:** locked text says “dirty work”; porcelain with untracked is the honest default if “never silent discard” is serious. Confirm untracked is inside “dirty” or a separate force bit.

### 4. Canvas durable delete still open (archive vs hard)

Not fully locked. Table has `archived`. Scout PR3 allows either. Subtree + parent FK ON DELETE CASCADE implies hard delete preference; archive implies soft tree walks (`WHERE archived = false`) and unique-name collisions. **Must lock before migration choice in #2.**

### 5. Session refs on Worktree hard delete

Confirmed: `session.space_id` / `session.worktree_id` are indexed without FK (`0006_spaces_foundation`). Hard Worktree row delete leaves dangling history. Tombstone vs retain-dangling is still open; plan should default **retain** (history) unless product wants clear.

---

## SECONDARY

### Reuse-map fidelity

| Claim | Verdict |
| --- | --- |
| Canvas C/R-list/U via `SpaceStore` + `space_routes`; no get-one, no delete | **Accurate** |
| Worktree reads + detection upsert; no user C/U/D; no `git worktree add/remove` in product code | **Accurate** |
| MCP: no Space/Canvas/Worktree CRUD tools; control-plane tools only | **Accurate** (`create_control_plane_mcp`) |
| `_require_worktree_in_space` route-only; store does not enforce same-space | **Accurate** |
| Patch COALESCE cannot clear `default_worktree_id` with explicit null | **Accurate** (`SpaceStore.update_canvas`) |
| Detection sets `archived = false` on match | **Accurate** |
| `listRuns` discards pagination after first page | **Accurate** (`listRuns` returns `response.items` only; server default limit 50) |
| `clearCanvas` / `stopRun` not safe as server delete | **Accurate**; decision-surface Deviate #11 correct |
| Stub `DEFAULT_SPACE_ID` / `DEFAULT_WORKTREE_ID` on views | **Accurate** (`RunManager`) |
| Size: `SessionCanvasRoute.test.tsx` 707, `test_controlplane_skins.py` 695, `RunManager.ts` 664, `runtimeRouter.test.ts` 656, `space/store.py` 627, `canvasActions.ts` 554, `transport.ts` 525, `controlplane_mcp.py` 515, `registerRunRoutes` ~159 | **Accurate** (paths abbreviated; real homes under `www/packages/canvas`, `packages/runtime`, `api/src/...`) |
| Size: `useCommandCenter` **143** lines | **Stale/wrong** — `useCommandCenter.ts` is **345** lines. Still “add focused hooks,” but do not trust 143. |

Symbol names in the reuse map are generally good. Prefer package-qualified paths in implementation briefs.

### Twin-client truly one path

Sound. Exclude direct `SpaceStore` from MCP and browser-owned delete safety by construction. Extract same-space validation and owner-scoped get into the service (scout quality findings 2–3).

### Slice buildability

Scout PR1 → PR5 order remains right **if** delete locks complete:

1. Service + read parity  
2. Canvas C/U + UUID identity migration (should precede or couple with subtree delete because cache keys)  
3. Canvas delete (needs #1–#2 + archive/hard)  
4. Worktree create (+ defined update subset)  
5. Worktree delete lifecycle (needs #3 + remaining open rows)

Putting **tree parent edge** in PR2 (schema + reparent guards) rather than only PR3 avoids bolting hierarchy onto a flat CRUD mid-flight.

### Forecloses multi-launch or batch?

**Does not foreclose.** Tree gives optional hierarchy; null parent keeps today’s flat multi-pane canvas. Multi-launch can remain many panes on one canvas or sibling canvases under a parent. Risk is product confusion (pane tree vs canvas tree), not technical foreclosure. Batch worktree ops are not blocked by the matrix; they need the same service + gate.

---

## Findings index (for orchestrator synthesis)

| # | Sev | Topic |
| --- | --- | --- |
| **1** | **Blocking** | Cascade-stop path false; client-only POST terminate; no canvasId on runs; need server inventory + receipts |
| **2** | **Blocking** | `parent_canvas_id` / subtree: cycle, same-space, depth, multi-phase receipt, concurrent reparent, FK ON DELETE vs archive |
| **3** | **Blocking** | Worktree dirty: phase order with launch gate + run stop; reuse porcelain pattern; define untracked |
| 4 | Major | Durable archive vs hard still open; drives FK and tree walk |
| 5 | Major | Session worktree refs dangling on hard delete |
| 6 | Major | Dual canvas identity (UUID vs synthetic cache) must not lag subtree delete |
| 7 | Minor | `useCommandCenter` size claim wrong (345 not 143) |
| 8 | Minor | Stale `DELETE /runs/{id}` language in Agents.md / briefs |

---

## Sign-off

I sign off conditional on:

1. Replace cascade-stop authority with a server-side inventory + terminate/receipt path (not pane-close / not `DELETE /runs/{id}`); decide service-origin runs.
2. Specify `parent_canvas_id` migration + cycle/same-space/depth guards + multi-phase subtree receipt + interaction with archive-vs-hard.
3. Specify Worktree delete phase order (gate → stop/wait runs → dirty check → force → git → DB) and whether untracked counts as dirty.

Until then, PR1–PR2 (shared service, reads, Canvas C/U, UUID migration, parent edge with write guards only) can proceed; **do not start Canvas subtree delete or Worktree delete implementation.**
