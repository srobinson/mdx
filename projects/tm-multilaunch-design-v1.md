# Multi-launch (launch_batch) — v1 design, first draft

Status: FIRST DRAFT for peer review. Author: orchestrator, from design chat with Stuart 2026-07-20.
Governing authority: `LAUNCH-CONTRACT.md`. Scout: `~/.mdx/projects/tm-multilaunch-scout.md`.
Canvas relationship dig: `~/.mdx/projects/tm-multilaunch-canvas-relationship.md`.

## Goal

`launch_batch` fans N launch candidates through the now-working single-launch
authority, with per-item failure isolation and server-minted candidate identity,
exposed to BOTH the MCP tool and the ⌘K palette (twin clients). v1 is critical
infra, not a throwaway thin verb: it is the substrate launch profiles and evals
sit on. Build it to that bar.

## Domain model (code-grounded)

Scope chain, with the id/key at each edge (from the canvas dig):

```
Space (owner-scoped project umbrella; space.models.SpaceId / Space.space_id)
 ├─ 1:N Worktree   (space.models.Worktree; worktree_id + path/workspace_slug/hash)
 └─ 1:N Canvas     (space.models.Canvas; canvas_id, optional default_worktree_id)
        └─ 1:N pane        (CLIENT ONLY: paneRecords.CanvasModel.panes; contentRef = runKey, worktreeId)
               └─ N:1 run  (attach by client runKey → capturedRunStore.CapturedRunRecord.runId; NO server join)
                      └─ 1:1 HOME (captured_run_context._prepare_home_and_grant → CLAUDE_CONFIG_DIR|CODEX_HOME)
```

Persisted (Postgres): Space, Worktree, Canvas identity + a server layout jsonb bag.
Client (localStorage, keyed by canvasId): pane records + layout.
Ephemeral: active canvas key (`canvasStoreLifecycle.activeCanvasId`), process-resident
`RunManager` runs map.

Key fact: **run→HOME is 1:1 today**, minted per run. Reusing the single-launch path
per candidate gives each candidate its own config HOME inherently — per-launch agent-state
isolation is free, not a batch feature.

## The three orthogonal axes

A launch is N candidates. Each candidate is a point in a cube:

- **Prompt**: shared first prompt | per-candidate prompt
- **Worktree** (isolation): shared | per-candidate — a separate concern, NOT tied to canvas
- **Canvas** (organization / layer): which canvas the candidate's pane lands in

Candidate shape (this IS the launch-profile item — see below):

```
LaunchCandidate {
  model, effort,
  prompt?,           // absent → inherit the batch's shared first prompt
  worktree_ref,      // shared handle | "new per-candidate"
  canvas_ref         // target canvas for placement
}
```

Use cases, all one verb with different axis settings:
1. 3 candidates → this canvas, shared prompt.
2. 3 candidates → this canvas, per-candidate prompts.
3. 3 → canvas A, 2 → canvas B (the COMMON case: organization / decluttering / drilling
   into layers). Canvas is a layer; the top canvas is the director/orchestrator layer,
   drill in to view workers.

## Profile unification (locked)

The batch launch input **is** a launch profile. Ad-hoc launch = an unnamed inline profile.
A saved profile = the same shape, persisted and named (the WARROOM.md pattern for launches:
ad-hoc launches vs designed/deliberate workflows). Designing the v1 batch input as the
profile shape means "save as profile" later is pure persistence, zero contract rework.

## Eval falls out (deferred, but shaped)

Eval is not a new primitive: run one profile across SEPARATE worktrees with the models
tweaked, then compare outputs. Only the comparison surface is genuinely deferred.
`eval = profile × per-candidate worktree × model variation + comparison`.

## Layered scope

| Layer | What | Reuses |
|-------|------|--------|
| **L0 — batch verb (v1)** | fan N candidates through the reused single-launch authority; per-item isolation; server-minted candidate keys; receipts. Worktree via existing `Worktree`. Canvas placement — SEE OPEN DECISION. | single-launch authority (`ControlPlaneLauncher`), `Worktree`, `LaunchLedger`, gateway idempotency_key |
| **L1 — launch profiles** | persist the L0 input as a named profile | L0 contract shape |
| **L2 — eval** | run a profile across worktrees w/ model variation + comparison | L1 + comparison (new) |
| **(parallel) canvas layering** | canvas hierarchy + drill-down (director layer → worker layer) | canvas entity; net-new hierarchy |

## Locked decisions

- **D1 axes**: three orthogonal axes as above; candidate = profile item.
- **Profile shape**: v1 batch input designed as the profile shape now.
- **HOME isolation**: free via reused single-launch path; not a batch feature.
- **Blast-radius non-negotiables** (from D2): server-minted candidate keys must reach
  `LaunchLedger` and the gateway `idempotency_key` before fanout; NO client-minted
  per-candidate dispatch_id; NO palette `/v1/runs` batch loop (one control-plane batch
  transport, not an N-loop).
- **Canvas layering/drill**: parallel track; L0 must not foreclose it, but it is not v1 payload.

## OPEN DECISION for review — canvas placement in v1

Today run→canvas is CLIENT ONLY. A run carries `spaceId/worktreeId/workspaceId/owner/runId`
but **no `canvas_id`** (`CreateManagedRunInput`, `CapturedRunRequest`, `ManagedRunFilters`
have no canvas field). Panes attach to runs post-hoc, client-side, via
`canvasActions.adoptCapturedRun` / `addCapturedRun` into the active `CanvasModel`.

**Option A — client-side placement (thin, reuse).** Batch returns N receipts; the client
adopts each into its target canvas via the existing `adoptCapturedRun` seam. No new server
substrate. Even use case 3 (split across canvases) works: client adopts receipt i into
canvas X.

**Option B — server-side canvas affinity.** Add `canvas_id` to `CreateManagedRunInput`
(+ capture prepare + `RuntimeRunView`), thread through `RunManager.createWithDisposition`,
add to `ManagedRunFilters`. Grouping becomes a durable, queryable, server-owned launch key.

Orchestrator's initial lean: A (thin, reuse), defer B. But the point of this review is to
pressure-test that against **what we lose by punting server-side**. Reviewers must give a
detailed pro/con and answer, concretely:

1. **Durability / reload**: with client-only placement, does canvas grouping survive a
   page reload, a second client, or a `RunManager`/API restart? What is the reattach story
   for a batch's N panes if the client localStorage is the only grouping record?
2. **Multi-client / director drill**: the director-layer → worker-layer drill implies the
   grouping is meaningful across views. Can a second viewer (or the director on another
   layer) see the batch as a group without server truth?
3. **Query / filter / lifecycle**: with no `canvas_id` on the run, can we ever
   "stop the whole canvas's batch", "list runs in canvas X", or reason about a batch as a
   unit server-side? Is that needed in v1, L1 (profiles), or L2 (eval)?
4. **Migration cost of deferring**: if we ship A now and add B later, is B a clean additive
   migration, or does A bake in a client-authority assumption that B has to unwind?
5. **Contract fidelity**: does A satisfy LAUNCH-CONTRACT.md, or does the contract imply
   server-owned grouping such that A needs an explicit recorded deviation?

Recommend A, B, or a minimal hybrid (e.g. server records canvas_id as an opaque affinity
tag now, no query surface yet). Justify against v1-is-critical-infra: cheap-to-defer vs
expensive-to-unwind.
