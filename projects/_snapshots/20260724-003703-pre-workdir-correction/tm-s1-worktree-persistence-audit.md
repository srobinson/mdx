# S1 Worktree persistence audit

Date: 2026-07-22  
Head: `feat/multi-launch` @ `9ac8d10d`  
Read-only. Question: which Worktree facts must be durable vs detection-derived.

---

## 1. `space_worktree` columns (0030)

Source: `0030_space_crud_reset._create_final_space_worktree`

| Column | Class | Notes |
| --- | --- | --- |
| `worktree_id` | **[IDENTITY]** | PK UUID; minted on insert; stable once assigned. |
| `owner` | **[IDENTITY]** | Scopes unique keys `(owner, workspace_slug, workspace_hash)` and `(owner, path)`. |
| `path` | **[IDENTITY]** | Canonical checkout path; `UNIQUE (owner, path)`; nullable for edge cases. |
| `workspace_slug` | **[IDENTITY]** | Path-derived via `workspace.workspace_id` / detection; half of upsert conflict key. Computable from path, but **is** the stable key today. |
| `workspace_hash` | **[IDENTITY]** | Same; other half of conflict key. |
| `space_id` | **[BINDING]** | FK → `space`; **mutable on reconcile** (`ON CONFLICT … SET space_id = EXCLUDED.space_id`). |
| `root_canvas_id` | **[BINDING]** | Unique; FK pair to protected root Canvas; **not** updated on conflict (identity of binding preserved). |
| `provenance` | **[IDENTITY]** (durable TM policy) | `detected \| created`; not rewritable by detection conflict update. Not filesystem-observable. |
| `lifecycle_state` | **[IDENTITY]** (durable TM control) | `creating \| active \| deleting`; gate for S2/S6; not from git. |
| `lifecycle_generation` | **[IDENTITY]** (durable TM control) | Lease generation; not from git. |
| `branch_name` | **[DERIVABLE-ATTR]** | From `git worktree list` / detection. |
| `head_oid` | **[DERIVABLE-ATTR]** | From detection HEAD. |
| `is_primary` | **[DERIVABLE-ATTR]** | From detection primary path; also cleared by `mark_missing_worktrees`. |
| `missing` | **[DERIVABLE-ATTR]** | Path existence / not in active detection set. |
| `created_at` | meta | Insert bookkeeping. |
| `updated_at` | meta | Touch on upsert / mark-missing. |

**Derivable-attr count (clear): 4** — `branch_name`, `head_oid`, `is_primary`, `missing`.  
**Path-derived identity (not pure attrs): 2** — `workspace_slug`, `workspace_hash` (derivable from `path`, but currently the upsert identity).

---

## 2. Stable identity key today

**Path-derived workspace identity, not Space claim.**

- Upsert key: `ON CONFLICT (owner, workspace_slug, workspace_hash)` in `SpaceStore.upsert_worktree`.
- Slug/hash come from `DetectedWorktree` → `workspace_id(path)` in `space.detection._worktree_from_path` / plain-space path.
- Secondary uniqueness: `UNIQUE (owner, path)`.
- Durable row id after mint: `worktree_id`.
- **Space is not identity:** conflict update **rewrites** `space_id` to the newly claimed Space. Git claim is `SpaceStore.claim_git_space` / `space_git_identity.repo_instance_key` (repo common dir hash), separate from Worktree row identity.
- **Canvas↔Worktree binding** is `root_canvas_id` (plus canvas `default_worktree_id` pair). On conflict, `root_canvas_id` and `provenance` are **excluded** from the UPDATE set — binding and ownership class stay on the path-identity row; Space may move under the same path key.

Verdict: **identity = path** (via slug/hash (+ path unique)); binding = `root_canvas_id` / `space_id` (space mutable).

---

## 3. S1 read paths: persisted row vs recompute

| Path | Behavior |
| --- | --- |
| `SpaceCrudService.list_worktrees` | **Persisted only.** `_require_space` → `SpaceStore.get_space_snapshot` (or store list) → `WorktreeRecord.from_worktree`. No `detect_space`. |
| `SpaceCrudService.get_worktree` | **Persisted only.** `SpaceStore.get_worktree` SQL → row map. |
| `SpaceCrudService.get_space_snapshot` | **Persisted only.** One SQL with `jsonb_agg` over `space_worktree` + canvas. |
| `SpaceStore.list_worktrees` / `get_worktree` | **Persisted only.** SELECT all columns including branch/HEAD/missing. |
| `SpaceCrudService.reconcile_detection` | **Write path.** Detection in → `upsert_worktree` + `ensure_worktree_root` + optional `mark_missing_worktrees` → then `get_space_snapshot` (returns **just-written** rows, not a live re-projection without persist). |
| `SpaceCrudService.reconcile_worktrees` | Director-only: `resolve_cwd` → detect + reconcile, then `WorktreeRecord` from refreshed snapshot (**persist then read**). |
| REST/MCP list/get Worktree | Adapter → service reads above; no client-side recompute. |

**Rule today:** all public S1 reads serve **DB cache of last reconciliation**. Fresh FS facts only appear after a reconcile write.

---

## 4. Blast-radius sizer (hypothetial reshape)

**Target shape:** persist only identity + canvas binding (+ provenance/lifecycle for later slices); project git/branch/HEAD/primary/missing at runtime from detection.

### Columns

| Action | Columns |
| --- | --- |
| Stop persisting as source of truth | **4** DERIVABLE: `branch_name`, `head_oid`, `is_primary`, `missing` |
| Keep as durable identity | `worktree_id`, `owner`, `path`, (`workspace_slug`/`workspace_hash` or collapse to path-only key) |
| Keep as binding | `space_id`, `root_canvas_id` |
| Keep as durable policy/control | `provenance`, `lifecycle_state`, `lifecycle_generation`, timestamps |
| Optional collapse | If identity is path-only, `workspace_slug`/`workspace_hash` become pure projection (+2) — **bigger** key redesign |

### Symbols to touch (rough **~18–22** production + **~8–12** test)

**Schema / models (~4)**  
`0030_space_crud_reset._create_final_space_worktree` · `space.models.Worktree` · `space.models.WorktreeRecord` · pair-check trigger if it assumes column set

**Store write/read (~6)**  
`SpaceStore.upsert_worktree` (conflict UPDATE set) · `mark_missing_worktrees` · `_worktree_from_row` · `list_worktrees` SQL · `get_worktree` SQL · `get_space_snapshot` jsonb_agg order by

**Service (~5)**  
`SpaceCrudService.list_worktrees` (join/project detection?) · `get_worktree` · `reconcile_detection` · `reconcile_worktrees` · `_materialize_missing_worktree`

**Detection already has attrs (~1)**  
`space.detection.DetectedWorktree` (source of projection)

**API / browser DTOs (~4)**  
`space_routes` Worktree DTO projection · `space_mcp` result shape · `@tm/core` `spaceTransport.WorktreeSummary` · `workdirRows` (titles use `branchName` / `isPrimary`)

**Tests (high churn, ~10 files)**  
`space/test_store.py` · `space/test_service.py` · `space/test_models.py` · `space/test_space_crud_migration.py` · `space/testing.py` builders · `api/v1/test_space_routes*` / `test_space_mcp*` · canvas `commandModel.testSupport` / `commandRows` · core `transport.test` / `spaceTransport`

**Stays out of reshape (per ask):** canvas tree, session/transcript stamps, `root_canvas_id` binding.

### What does *not* shrink if you only drop the 4 attrs

- Upsert still needs a durable key (`path` or slug/hash).  
- `space_id` move-on-conflict and plain→git binding bugs remain identity problems, not attr-cache problems.  
- Lifecycle/provenance still durable for S5/S6.

---

## Bottom line

1. **4 columns** are pure filesystem observation today (`branch_name`, `head_oid`, `is_primary`, `missing`); S1 **always returns them from the row**, never live-detects on read.  
2. **Stable identity = path** (slug/hash key), not Space; Space is a mutable binding; Canvas root is a stable binding on that path-row.  
3. Making git/branch a runtime projection is a **moderate S1 reshape** (~20 production symbols + test builders), not a one-file tweak — and identity/binding columns stay.
