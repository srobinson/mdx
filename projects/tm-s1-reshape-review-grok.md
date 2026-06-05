# S1 reshape code review + full gate (Grok)

Date: 2026-07-22  
PR: #316  
Head: `feat/multi-launch` @ `855bd0a938c68123a24178d7c92953e10b720721`  
Authority: `tm-s1-reshape-proposal.md` v3  
Tree: clean (detached at head)

## Gate (authoritative, independent)

Postgres: `TRANSPORT_MATTERS_TEST_DATABASE_URL=postgresql://tm:tm@127.0.0.1:5432/postgres`

| Gate | Result | Counts |
| --- | --- | --- |
| `just check` | **pass** | desktop 102; shell format/lint/typecheck; api ruff + mypy 671 files |
| `just test` | **pass** | API **3383 passed / 0 failed**; JS packages green (shell unit **1256** in `just test-js` shell vitest) |
| Shell unit (explicit) | **pass** | **1256** tests (168 files) within full `just test` path |
| Browser e2e (`www/packages/shell` `just test-e2e`) | **pass** | **69 passed** (23 specs × chromium/firefox/webkit) |
| `just migration-smoke` | **pass** | **9/9** |

Engineer claim (full green, e2e 23 chromium, smoke 9) **verified**. Cross-browser e2e is 69 = 23×3.

## Migration 0030 realism

`revision = 0030_space_crud_reset`, `down_revision = 0029_native_connection_origin`.

### Upgrade path (clean rewrite)

1. `DROP` `space_git_identity`, `canvas`, `space_worktree`, `space` (order avoids FK hangers).
2. Recreate durable `space` with nullable `name`, `is_default`, partial unique `space_default_owner_uq` on `(owner) WHERE is_default`.
3. `space_worktree` without `space_id`, without `branch_name` / `head_oid` / `is_primary` / `missing`; path + workspace uniqueness; provenance + lifecycle retained.
4. `canvas` with `anchor_worktree_id NOT NULL`; parent scoped by `(owner, anchor_worktree_id)`; root shape CHECK; anchor FK `ON DELETE CASCADE`; default worktree FK deferred `NO ACTION`.
5. `space_worktree_link` M:N with named-space-only trigger (rejects links on default Space).
6. SQL `worktree_in_space(owner, space_id, worktree_id)` = default ⇒ all owner worktrees, else junction.
7. Deferred reciprocal root pair triggers on anchor axes.
8. Stamps: `session.space_id` and `run_lifecycle_event.space_id` **uuid → text** (no FK).

No half-applied branch: single upgrade body, no dual-write of old/new columns.

### Downgrade

Restores legacy 0006-shaped tables including `space_git_identity` and runtime worktree columns; stamp cast uses `NULL::uuid` (history wiped). Acceptable under reset policy.

## Coherence vs proposal v3

| Proposal claim | Implementation |
| --- | --- |
| Detection never writes membership | `reconcile_detection` ensures default Space + `upsert_worktree` + `ensure_worktree_root` only; no `space_worktree_link` writes |
| Runtime facts projected | `projection.py` + `ProjectedWorktree`; store INSERT lists only durable columns |
| Default membership computed | `worktree_in_space` + `is_default`; link trigger blocks default materialization |
| Principal → Space | `resolve_workspace_caller` resolves path Worktree, then **default Space** + membership check (S1-correct) |
| Same-Space visibility | `_require_worktree_in_space` via SQL predicate |
| Director virtual | `director_tree` over Spaces; no Director canvas row |
| Single service path | Production call sites use `SpaceCrudService` only |

### Leak check (persisted git / Space membership)

- **No** production `space_git_identity` / `claim_git` path.
- Store upsert conflict updates **path only** (not org, not git facts).
- `repo_group_key` / branch / HEAD / primary / missing live on detection + projected models, not durable INSERT.
- Session/run stamps remain free-form text IDs of durable Space UUID strings, not `git:…` labels.

No leak of git authority into durable Space membership found.

## Hygiene

| Module | LOC | Note |
| --- | --- | --- |
| `space/service.py` | 613 | Under 700; dense but one facade |
| `space/store.py` | 506 | Persistence only after reshape |
| `space/projection.py` | 111 | Clean seam |
| `space/detection.py` | 349 | Classifier + enrichment |
| `0030_space_crud_reset.py` | 429 | Large but single revision |

No parallel Space CRUD service. Focused `spaceTransport.ts` carries `repoGroupKey`, `anchorWorktreeId`, `isDefault`.

## Early vs late slice coherence

Foundation + reshape land as one head. Service/store/projection/detection/migration agree on anchor axes and default membership. No leftover dual schema writers. Acceptable “low then full effort” residue: none that breaks the model.

## Findings

### Blockers

None for merge relative to reshape authority + green full gate.

### Suggestions (non-blocking)

1. **`resolve_canvas_caller` / `resolve_worktree_caller` always bind default Space** via `_default_caller`. Correct for S1 (only default Space). When named Spaces land, callers must select Space by request or membership, not silently default.
2. **`ensure_worktree_root` uses `ON CONFLICT DO NOTHING`** (no name refresh). Matches “branch changes never rename roots”; path renames that should retitle roots need an explicit later policy.
3. **Downgrade stamp wipe** (`USING NULL::uuid`) is sharp; document in release notes if anyone downgrades a populated DB (unlikely).

## Builder trust

**High.** Migration matches the locked organizational model; runtime projection is cleanly separated; membership predicate is real SQL; full gate and multi-browser e2e pass independently.

## Verdict

**review: clean**  
**gate: check pass · test 3383/0 · e2e 69/0 (23×3) · smoke 9/9**
