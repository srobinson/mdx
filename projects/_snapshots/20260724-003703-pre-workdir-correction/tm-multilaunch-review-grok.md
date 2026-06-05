# Multi-launch design review (grok)

**Artifact reviewed:** `/Users/alphab/.mdx/projects/tm-multilaunch-design-v1.md`  
**Baseline:** `feat/multi-launch` worktree @ `8c51797e01ef` (matches requested SHA prefix `8c51797e`)  
**Method:** full design read; code verification via `rg` / file reads (no `.fmm.db` in this worktree); cross-check against canvas dig, decision surface, scout, `LAUNCH-CONTRACT.md`  
**Boundary:** read-only. Tree pristine at start and before verdict (`git status` clean).  
**Hat:** design critique, not gate.

---

## 1. Code-grounding audit

| Claim | Verdict | Evidence |
| --- | --- | --- |
| Run creation lacks `canvas_id` on `CreateManagedRunInput` | **Confirm** | `packages/runtime/src/service/runManagerTypes.ts::CreateManagedRunInput` — fields are owner/harness/model/effort/cwd/workspace*/spaceId/worktreeId/agentId/grant/launchKind/name/prompt/delivery/continue/idempotency. No canvas. |
| Same for `CapturedRunRequest` | **Confirm** | `api/.../captured_run_models.py::CapturedRunRequest` — `space_id` / `worktree_id` present; no canvas field. |
| Same for `ManagedRunFilters` | **Confirm** | `ManagedRunFilters`: `owner`, `state?`, `spaceId?`, `worktreeId?` only. |
| Client placement seam is `adoptCapturedRun` / `addCapturedRun` | **Confirm** | `www/.../canvasActions.ts` + `canvasState.ts`. Palette path uses `addCapturedRun`; service/MCP adoption uses `adoptCapturedRun` (also `SessionCanvasRoute`, tests). |
| run→HOME is 1:1 at `_prepare_home_and_grant` | **Confirm** | `captured_run_context.py::_prepare_home_and_grant` mints `runtime_home_root = prepared.resolved_storage / "runtime-home"` per prepare. Reusing single-launch path per candidate yields isolation for free. |
| Space / Worktree / Canvas live in `space.models` | **Confirm** | `Space`, `Worktree`, `Canvas` (+ Id newtypes) in `api/.../space/models.py`. Canvas is Space-scoped with optional `default_worktree_id` and `layout` jsonb. |
| Pane membership is client-only | **Confirm** | Single zustand store + namespaced localStorage (`canvasCacheStorage` / `getActiveCanvasId`). Server `canvas.layout` exists; product pane state is not synced into it. No run↔canvas join table. |
| `RuntimeRunView` also has no canvas | **Confirm (doc omission)** | `packages/runtime/src/domain/runtimeRun.ts` has `runId/spaceId/worktreeId/sessionId/...` — no canvas. Any affinity option must include this surface. |
| Ledger today is `(owner, dispatch_id)` | **Confirm (design implies extension)** | `launch_ledger.py` key is `tuple[str, UUID]` = `(owner, dispatch_id)`. Contract wants `candidate_key`; still missing. Design non-negotiables match scout. |

### Minor imprecisions (not fatal)

1. **“A run carries … workspaceId/owner/runId”** — true on the *create input* path (`CreateManagedRunInput` has workspaceId/owner; capture request has owner). The process-resident list view (`RuntimeRunView`) does **not** expose `workspaceId` or `owner`. Prefer: “create path carries space/worktree/workspace/owner; view surface is runId + spaceId + worktreeId + sessionId.”
2. **Server layout bag** — design is right that Postgres holds canvas identity + layout jsonb; dig is right that it is **not** live pane membership. Worth one explicit sentence so implementers do not write panes into `canvas.layout` thinking that is the product store.
3. **`adoptCapturedRun` targets the active store only** — there is one live `useCanvasStore` keyed by `activeCanvasId`. Multi-canvas placement (use case 3: N→canvas A, M→canvas B) is **not** a free call of `adoptCapturedRun` N times while staring at one canvas; it requires switching canvas context / writing into the correct namespaced cache per target. Design Option A overstates “client adopts receipt i into canvas X” as trivial reuse.

**False-reuse failure mode check:** none of the core reuse claims invent a server run→canvas join or a shared HOME. The dangerous overclaim is only the ease of multi-canvas client placement under pure A.

---

## 2. OPEN DECISION — placement authority

### Option map (as I read it)

| | A client adopt | B server affinity + filters | Hybrid (recommended) |
| --- | --- | --- | --- |
| Create path | unchanged | `canvas_id` on create + view + filters | optional `canvas_id` on create + `RuntimeRunView` only |
| Visual panes | `adoptCapturedRun` / `addCapturedRun` | still client (unless you also migrate pane authority) | still client |
| Query “runs in canvas X” | no | yes | deferred |
| MCP / second client | placement is optional ad hoc | can honor affinity | can honor affinity tag; UI still adopts |
| Cost in v1 | lowest code | medium | low–medium, additive |

### Q1 — Durability / reload

| Event | Pure A | Hybrid / B (affinity only) |
| --- | --- | --- |
| Same browser, page reload, API still up | **Survives** via localStorage namespaced by `canvasId`; panes hold `runKey` → reattach by run id | Same for panes; affinity also re-readable from `RuntimeRunView` if you re-list runs |
| Second browser / client | **Lost as shared truth** — other client’s localStorage is empty of your panes | Affinity visible if second client lists runs; still must adopt to see panes |
| `RunManager` / API process restart | **Runs die** (process-resident). Canvas grouping is moot until relaunch. Server `canvas_id` does not resurrect PTYs | Same process-residency limit |
| Cleared localStorage | Grouping gone; runs may still be listable by space/worktree if process up, but ungrouped in UI | Affinity still on run view → client can rebuild panes from server list + tag |

**Reattach story under pure A:** per-run only, if the operator still knows run ids (or the same browser still has localStorage). There is **no** server “batch group” or “canvas membership” to rehydrate from. Receipts from `launch_batch` (if retained by the client or in a durable ledger later) are the only non-local group record — and ledger today is process-lifetime too (`LaunchLedger` comment: process lifetime, no eviction).

### Q2 — Multi-client / director drill

Director-layer → worker-layer drill implies **shared meaning of “this set of runs is the worker layer.”**

- Pure A: grouping is “whatever panes this browser adopted into this canvas cache.” A second viewer, a restored director tab on another machine, or an MCP-launched batch with no browser open **cannot** see the batch as a group without inventing a side channel.
- Twin clients (MCP + ⌘K) make this acute: MCP has no `adoptCapturedRun`. Under pure A, MCP batch receipts are unplaced until some canvas client chooses to adopt — into **its** active canvas, not necessarily the candidate’s `canvas_ref`.
- Therefore pure A **does not implement** the canvas axis for the MCP half of “twin clients.” It only implements “palette places into the open canvas.”

### Q3 — Query / filter / lifecycle

Today you cannot server-side: list runs by canvas, stop-all-on-canvas, or reason about a batch as a unit via canvas.

| Need | When required? |
| --- | --- |
| Fanout + per-item isolation + receipts | L0 — **no canvas_id required** |
| Honor `canvas_ref` on a profile item from MCP | L0 if `canvas_ref` stays on the L0 candidate shape — **affinity required** |
| “Stop the whole canvas’s batch” / filter UI by canvas | canvas-layering / ops — **not v1** |
| Eval comparison unit | L2 — better keyed by `dispatch_id` / profile execution id than by canvas |

So: **full B filters are not v1-critical.** Affinity (write path) becomes critical the moment L0 claims `canvas_ref` as a real axis for both clients.

### Q4 — Migration cost of deferring B

**Cheap to defer (true pure A):** if L0 **drops** `canvas_ref` from the candidate/profile shape and treats canvas placement as “active canvas only, palette path,” adding optional `canvas_id` later is a clean additive migration. No client-authority assumption to unwind beyond “we always adopted into active canvas.”

**Expensive to unwind (false pure A):** if L0 **ships** `LaunchCandidate.canvas_ref` and “save as profile” freezes that field, while only the launching browser fulfills it:

1. Profiles encode placement intent with **no server binding** → later B must redefine what `canvas_ref` means (intent vs fact) and migrate saved profiles / MCP adapters.
2. Multi-writer placement races (palette + MCP + future director) bake “last adopt wins, no conflict detection.”
3. Tests and docs will teach “batch returns receipts; client places” as the contract, which fights multi-client truth later.
4. Use case 3 (split canvases) will grow client hacks (switch store, multi-cache writes) that a later server tag makes redundant but entangled.

**Hybrid cost of doing a little now:** thread one optional opaque field create→view. No filters, no pane table, no layout authority move. Unwind cost ≈ zero; you can ignore the field until canvas-layering.

### Q5 — Contract fidelity (`LAUNCH-CONTRACT.md`)

- Public `LaunchRequest` has no canvas field. `launch_batch` adds **internal candidate key**, **sealed workspace snapshot**, **optional evaluation artifacts**. Batch does not create a second launch semantic.
- **Pure A does not violate LAUNCH-CONTRACT.** No recorded deviation required for placement-as-client.
- Contract **does** conflict with design-v1 on a different axis: sealed `WorkspaceSnapshot`. Design L0 reuses live `Worktree` and never names the snapshot. Decision surface D1 still open; design-v1 implicitly picks thin foundation without the required contract clarification. That is a **contract fidelity gap**, separate from canvas.

---

## 3. Verdict on placement

### Recommend: **minimal hybrid**

1. Accept optional `canvas_id` (affinity tag) on the create path: `CreateManagedRunInput` → capture prepare identity → `RuntimeRunView`.
2. Map `LaunchCandidate.canvas_ref` → that tag at mint time (server validates canvas belongs to the resolved space / owner).
3. Keep visual placement on `adoptCapturedRun` / `addCapturedRun` (client remains pane authority).
4. **Do not** add `ManagedRunFilters.canvasId`, server pane membership, or “stop by canvas” in v1.
5. Palette: after batch receipts, adopt each receipt into the canvas named by its tag (implement multi-cache adopt honestly; do not pretend active-store-only is enough for use case 3).
6. MCP: receipts carry affinity; any later UI can adopt by tag without guessing.

### What pure A loses (single biggest item)

**Durable, multi-client (including MCP) meaning of `canvas_ref` / batch-as-group.** Placement collapses to the localStorage of whichever browser happened to adopt. That is the expensive-to-unwind loss if profiles freeze the canvas axis now.

### Why not full B in v1

Filters and server-owned pane membership are canvas-layering / ops features. They are not required for fanout correctness. Shipping them in L0 expands blast radius without unblocking profiles or eval.

### Why not pure A

Design already locks **canvas as a third orthogonal axis** and **candidate = profile item**. Pure A makes that axis real only for the ⌘K path into the active canvas. That is not “critical infra substrate for profiles”; it is a palette convenience with a profile-shaped lie.

**Fallback if hybrid is rejected:** pure A **plus** remove `canvas_ref` from the L0 candidate/profile shape (canvas axis deferred to the parallel layering track). That is honest. Pure A **with** `canvas_ref` on the profile shape is the failure mode.

---

## 4. Secondary: three-axis model, profiles, L0/L1/L2

### Three-axis model — sound

Prompt / worktree / canvas as orthogonal axes matches the code topology:

- Worktree is a server Space child and the practical workdir handle.
- Canvas is a Space child for organization; not a workdir owner.
- Prompt is launch payload (`first_prompt` / delivery), independent of both.

Do not bind “new worktree” to “new canvas.” Design is correct here.

### Profile-shape unification — sound, with one guard

Ad-hoc batch input = unnamed profile is the right freeze for “save as profile later.” Guard: **only fields the server can honor for both MCP and palette belong on that shape in L0.** That is the hybrid argument in profile clothing.

### L0 / L1 / L2 + parallel canvas-layering — mostly sound

| Layer | Assessment |
| --- | --- |
| L0 batch verb | Right critical path: candidate keys, ledger key extension, gateway idempotency, one control-plane transport (no palette `/v1/runs` N-loop). Aligns with scout D2 non-negotiables. |
| L1 profiles | Clean if L0 shape is honest (including canvas affinity or canvas_ref deferred). |
| L2 eval | Correctly “profile × worktree isolation × model variation + comparison.” Comparison surface is the only real new product. |
| Parallel canvas layering | Correctly parallel. Hierarchy/drill must not block L0. |

### Does L0 foreclose profiles / eval / canvas-layering?

| Concern | Foreclosed by current draft? |
| --- | --- |
| Profiles | **Risk under pure A + canvas_ref on candidate.** Hybrid or drop canvas_ref → no. |
| Eval | **No.** Eval needs worktree isolation (snapshot D1) more than canvas. |
| Canvas layering / drill | **No** if L0 does not claim server pane authority or a frozen “one canvas per batch” policy. Hybrid affinity is upward-compatible. |
| Sealed workspace snapshot | **Silent foreclosure of contract completeness.** Thin L0 without recorded clarification is the open D1 hole. |

### Blast-radius non-negotiables — agree

Server-minted candidate keys to ledger **and** gateway `idempotency_key` before fanout; no client-minted per-candidate `dispatch_id`; no palette N-loop on `/v1/runs`. These are correct and higher priority than canvas filters.

---

## 5. Additional design gaps (outside the five questions)

1. **D1 snapshot isolation** — `LAUNCH-CONTRACT.md` says batch adds a sealed workspace snapshot. Design-v1 L0 uses existing `Worktree` / live workdir and never records a contract clarification. Decision surface still asks A vs B. **Ship-blocking documentation**, even if product chooses thin foundation.
2. **Multi-canvas adopt mechanics** — if use case 3 stays in v1, specify the client algorithm (switch `initializeCanvas` / write non-active cache / batch adopt helper). “Call `adoptCapturedRun`” is incomplete.
3. **Receipt durability** — process-resident ledger + process-resident runs mean “batch as a unit” dies on API restart regardless of canvas. If v1 is critical infra, say whether batch receipts are only live-process or need durable audit (launcher already has audit hooks; batch should state reuse).
4. **`LaunchLedger` key extension** — design assumes contract key; code is still 2-tuple. Call it out as L0 code work, not “already true.”
5. **Palette trusted adapter** — decision surface flags origin-checked Canvas→control-plane entry so ⌘K does not forge owner/candidate keys. Design-v1 underweights this relative to scout; twin-client convergence depends on it more than on canvas filters.

---

## 6. Sign-off

**Verdict:** **hybrid** (optional server `canvas_id` affinity on create + view; client keeps pane placement; no filters in v1).

**Single biggest loss if pure A ships with `canvas_ref` on the profile shape:** multi-client/MCP cannot treat canvas placement as truth; the third axis becomes browser-local fiction and is expensive to unwind once profiles persist it.

**Tree:** pristine after review; no code writes.

### Sign-off line

**I sign off conditional on:**

1. Placement decision recorded as **minimal hybrid** (or pure A **with `canvas_ref` removed from L0 candidate/profile shape**).
2. Explicit L0 work: optional `canvas_id` create→`RuntimeRunView` (if hybrid); honest multi-canvas adopt path if use case 3 stays in v1.
3. Contract clarification for **sealed workspace snapshot** (thin foundation deferral recorded, or snapshot in L0 scope) — do not ship silent conflict with `LAUNCH-CONTRACT.md`.
4. L0 non-negotiables unchanged: server `candidate_key` to ledger + gateway idempotency; single batch transport for MCP and palette (no `/v1/runs` N-loop).
5. Design fixes for minor grounding: `RuntimeRunView` field list; active-store-only limit of `adoptCapturedRun`; ledger key still 2-tuple today.
