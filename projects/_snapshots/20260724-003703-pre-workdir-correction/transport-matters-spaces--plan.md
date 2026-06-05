# Spaces / Canvas / Worktree — Implementation Plan Index (detect-only cut)

> Decomposition of the locked + consensus-reviewed model into PR-sized slices.
> Design: `transport-matters-spaces--proposal.md`. Each slice gets its own full
> bite-sized TDD plan (`docs/superpowers/plans/…` or `~/.mdx/projects/…-slice-N.md`)
> once the decomposition is confirmed.

**Goal:** Add a **Space** aggregate above today's path-keyed `WorkspaceId`, with **Worktree**
(launch target) and **Canvas** (saved pane surface) as orthogonal axes, detect-only first.

**Scope of THIS plan:** detect / persist / observe + the run-path identity re-key. **Out of
scope (preserved for the next iteration):** worktree CRUD (`git worktree add/checkout/remove`) —
Codex's full lifecycle spec stays in `…-spaces-feasibility--brainstorm.md`.

**Tech stack:** Python / FastAPI / Pydantic v2 / psycopg3 / Alembic / Postgres (api); React /
zustand / TS (www). IDs: app-minted **uuid4**, native `uuid` columns, bare serialization,
7-char shortest-unambiguous-prefix for display (littleorgans `lilo-common::id` convention).

**Binding requirements** (from peer-consensus; every slice cites which it satisfies):
R1 ResolvedWorktree handoff · R2 drop `workspaceId` from response DTOs · R3 pane worktree-rooting
(required on spawnable panes, `Canvas.defaultWorktreeId` fallback) · R4 empty-cwd legacy backfill ·
R5 relative `--git-common-dir` resolved against target cwd · R6 reversible migration, ids stay
`text` · R7 doc/UX hygiene (no "Surface", Space-scope chrome, Canvas observe-only for director).

---

## Slice 1 — Identity + schema foundation  *(backend; no behavior change)*

**Builds:** uuid4 typed ids + the four tables + the DTOs everything else depends on.

- Create `api/src/transport_matters/space/__init__.py` (empty package marker) + `api/src/transport_matters/space/models.py` — `SpaceId/WorktreeId/CanvasId`
  (uuid4, `uuid.UUID`-backed, bare-string JSON), `Space`, `Worktree`, `Canvas`, and the
  **`ResolvedWorktree`** DTO `{space_id, worktree_id, cwd, workspace_slug, workspace_hash,
  missing, archived}` *(R1)*.
- Create `api/migrations/versions/0006_spaces_foundation.py` — `space`, `space_git_identity`
  (UNIQUE `repo_instance_key`), `space_worktree` (UNIQUE `(owner, workspace_slug, workspace_hash)`,
  UNIQUE `(owner, path)`), `canvas`; nullable `session.space_id` + `session.worktree_id` + the two
  partial indexes; **real `downgrade()` dropping in dependency order** *(R6)*. uuid PKs; keep
  `session_id/run_id/workspace_slug/workspace_hash` as `text` *(R6)*.
- Tests: model round-trip (uuid→bare string), short-prefix helper (7-char floor), migration
  upgrade+downgrade against a temp DB.

**Depends on:** nothing. **Unblocks:** all.

## Slice 2 — Detection service + Space store  *(backend; the detect+persist core)*

- Create `api/src/transport_matters/space/detection.py` — subprocess-argv git probes
  (`rev-parse --is-inside-work-tree --show-toplevel --git-common-dir --git-dir`,
  `worktree list --porcelain -z`), **relative `--git-common-dir`/`--git-dir` resolved against the
  target cwd / reported toplevel, then hashed** *(R5)*; plain-dir degenerate Space; failure policy
  (not-a-worktree / timeout / missing path / common-dir change / git-unavailable).
- Create `api/src/transport_matters/space/store.py` — DAO: mint/lookup Space by
  `repo_instance_key`, upsert Worktrees, reconcile against `git worktree list`, resolve a
  `worktreeId` → `ResolvedWorktree`; + tier-1 cache writer
  `~/.transport-matters/spaces/{spaceId}/{space,worktrees}.json`.
- Tests: **process-cwd ≠ target-cwd grouping** *(R5)*; plain dir; repo with one + simulated
  multiple worktrees; missing path → `missing=true`.

**Depends on:** Slice 1. **Unblocks:** 3, 4.

## Slice 3 — `/v1/spaces` routes + observe  *(backend API)*

- Create `api/src/transport_matters/api/v1/space_routes.py`:
  `GET /v1/spaces`, `POST /v1/spaces/resolve`, `GET /v1/spaces/{id}`, `PATCH /v1/spaces/{id}`,
  `GET /v1/spaces/{id}/worktrees?refresh=`, `GET/POST /v1/spaces/{id}/canvases`,
  `PATCH /v1/canvases/{id}`. **No** worktree create/checkout/remove (detect-only). Routes under the
  existing `/v1/` prefix. Director can observe/select a Canvas, not create/mutate beyond layout *(R7)*.
- Wire into the app router; startup resolves the API's own cwd into a current Space.
- Tests: resolve a path → Space+Worktree+canvases; list; refresh reconciles.

**Depends on:** Slice 2. **Unblocks:** 6.

## Slice 4 — Run-path re-key + ResolvedWorktree + drop `workspaceId`  *(backend; the contract change)*

- Modify `run_models.py` — `SpawnRun`, `ManagedRun`, `ManagedRunView` carry `space_id` +
  `worktree_id` (from `ResolvedWorktree`); `RunFilters` gains `space_id`/`worktree_id` *(R1)*.
- Modify `run_manager.py` — accept the resolved identity; keep `cwd` internal; `list` filters by
  space/worktree.
- Modify `api/v1/run_routes.py` — `CreateRunRequest.worktreeId` (resolve via `space.store` →
  `ResolvedWorktree`; CLI still resolves cwd internally); **`RunViewModel` drops
  `workspace_id`/`workspaceId` from the serialized surface**, emits `spaceId` + `worktreeId` *(R2)*.
- Bind `ResolvedWorktree` into the `SessionWriter` path *(R1)*.
- Tests: spawn by `worktreeId`; response has no `workspaceId`, has `spaceId`+`worktreeId`;
  `GET /runs/{id}` and filters carry identity without recomputing from cwd.

**Depends on:** Slices 1–2. **Unblocks:** 5, 6.

## Slice 5 — Session backfill + empty-cwd legacy  *(backend; existing-data migration)*

- Modify `session/backfill.py` — run detection over each existing `session.cwd`; set
  `space_id`/`worktree_id`; missing path → `missing=true` worktree; **`cwd == '' ` → legacy
  unassigned: keep `/v1/sessions?workspaceId=` as a history surface with an "unassigned legacy"
  group AND/OR a legacy Worktree `path=NULL, missing=true` keyed by `workspace_slug/hash`; never
  silently assign to a current Space** *(R4)*.
- Modify `session_routes.py` / `session_models.py` — `spaceId`/`worktreeId` filters alongside the
  retained `workspaceId` legacy filter.
- Tests: normal cwd backfills; missing-path; **empty-cwd lands in legacy, not a current Space** *(R4)*.

**Depends on:** Slice 4. **Unblocks:** 6.

## Slice 6 — www Space/Worktree launcher scopes + Canvas model  *(frontend)*

- Modify `www/src/session-canvas/launcher/commandModel.ts` — replace the disabled Workdir
  `buildDeferredRows` stub with **Space + Worktree scopes**; single-worktree Space skips the
  worktree sub-step; Space scope renders disambiguating chrome vs the `Canvas gesture modifier:
  Space` settings row *(R7)*.
- Modify `www/src/session-canvas/model/paneRecords.ts` — `CanvasModel.id` becomes `canvasId`
  (not `workspaceHash`); add optional `spaceId`; **`worktreeId` required on `terminal` +
  `captured-run` pane refs, optional on `resource(url)`; promote `Canvas.defaultWorktreeId` into the
  model** as the fallback for non-rooted panes *(R3)*.
- Modify `canvasStore.ts` + persistence — localStorage as a cache keyed by `canvasId`; one-time
  import of the single legacy canvas blob (one bare key, not per-`workspaceHash`) into the first
  Space's default Canvas.
- Add a nullable durable `sessionId?` to the `captured-run` pane ref (alongside `worktreeId`),
  carried through the guard + persistence + legacy import. This is the pane→session-lineage anchor
  for native resume and internal continuation; the FIELD is persisted now so canvases carry it,
  while populating it on session-bind and the resume behavior are deferred to Slice 7 (no later
  canvas migration needed because the field exists now).
- Modify `www/src/api.ts` — target `spaceId`/`worktreeId`.
- Tests: launcher scope rows; pane ref types; canvas import; `sessionId` round-trips with and without.

**Depends on:** Slices 3 + 4. **Unblocks:** —

---

## Order & parallelism

`1 → 2 → 3`, `1 → 4`, `4 → 5`, `(3,4) → 6`. After Slice 1, Slice 4 can run alongside 2–3.
Six PR-sized slices; each ships working, tested software.

## Build status — 2026-06-21 (drafted · twice-reviewed · corrected)

All six slice plans written in full bite-sized TDD form (~6,400 lines), grounded in the live
TM code, gated on `just check && just test`. Warroom Mode-2: Codex drafted, Claude
architect-reviewed (Phase A = slices 1+6, Phase B = slices 2–5), orchestrator gated + applied
corrections.

| Slice | File | Status |
|---|---|---|
| 1 Identity + schema | `…-spaces-slice1--plan.md` | reviewed (Phase A) + corrected: `is_primary`/`branch_name`/`head_oid`, `SpaceGitIdentity` model, `__eq__` mypy guard, Task-1 gate, casing contract |
| 2 Detection + store | `…-spaces-slice2--plan.md` | reviewed (Phase B); R5 + `is_primary` verified; `space_store` fixture + `get_worktree` added |
| 3 `/v1/spaces` routes | `…-spaces-slice3--plan.md` | reviewed + corrected: `SpaceSummary` inlines `worktrees[]`, typed timestamps |
| 4 Run re-key | `…-spaces-slice4--plan.md` | reviewed + corrected: identity required (no `Path.cwd()`), `SessionWriter` seam concrete, `workspaceId` sweep enumerated |
| 5 Backfill | `…-spaces-slice5--plan.md` | reviewed + corrected twice: startup rewired to `main.lifespan` + pooled conn (no `app.state` singletons), real `lifespan`/`TestDb` tests, no Slice-4 dup, citations fixed |
| 6 www scopes + Canvas | `…-spaces-slice6--plan.md` | reviewed (Phase A) + corrected: `just check && just test` gates, `select-worktree` in `useCanvasCommandHandler`/`CanvasSurface.tsx`, sweep enumeration |

Reviews: `…-spaces-phaseA--review.md`, `…-spaces-phaseB--review.md`. Requirements R1–R7 each
map to a slice (R1→1+4, R2→4, R3→6, R4→5, R5→2, R6→1, R7→6).

## Open at execution time (not blocking the plan)

- The one-time canvas localStorage→server import (Slice 6) is the trickiest user-data step; worth
  its own review.
- Worktree CRUD is the deliberate next iteration; the foundation here must not foreclose it
  (Slice 2's `repo_instance_key` grouping + minted ids already accommodate later-added worktrees).
- The resume `sessionId` anchor was folded into Slice 6 (the `captured-run` pane ref persists it
  now). Native resume on reopen (`--resume` claude / `resume` codex) and internal continuation
  (`parent_session_id`) behavior are deferred to Slice 7; the field exists now so no canvas
  migration is needed later.
