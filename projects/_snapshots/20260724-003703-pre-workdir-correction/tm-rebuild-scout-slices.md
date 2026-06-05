---
title: Spaces Slice Salvage + Revert Feasibility Scout
type: research
tags: [transport-matters, spaces, identity-model, revert-feasibility, iterate-vs-rebuild]
summary: The Spaces slices (#161-#166) encode the CORRECT canonical-path identity model, not a wrong one; salvage value is high, revert is expensive; lean ITERATE.
status: active
source: codebase-analyst
confidence: high
created: 2026-06-23
updated: 2026-06-23
---

# Spaces Slice Salvage + Revert Feasibility Scout

**Baseline:** `main @ e3aaecf` (HEAD). **Method:** read-only; working tree verified
pristine before and after (`git status --porcelain` empty); revert probes used only
`git apply --check --reverse` and read-only git. No writes to the repo by me or any subagent.

## TL;DR

The premise under test — that these slices are "rotten / entangled with a **wrong
identity model**" — **does not hold**. Verified against the schema (`0006_spaces_foundation`)
and the front end (`route.ts`): the Spaces model is coherent and hierarchical, and it is the
first thing in the codebase to actually implement the long-standing CLAUDE.md mandate that
"two checkouts of the same project share history." The remaining problems are **DRY / dead-field
cleanup**, not a broken foundation. Reverting is a conflict-laden backend refactor (not a
mechanical `git revert`) because `SpaceId`/`WorktreeId` became load-bearing types woven across
the run/session/proxy/index layers and the later hygiene slices overwrote the Spaces seams.

**Lean: ITERATE.**

## 1. Slice inventory

| # | SHA | Title | Layer | Class | What changed |
|---|-----|-------|-------|-------|--------------|
| 161 | 046281c | identity + schema foundation | back | Spaces | Migration `0006` (tables `space`, `space_git_identity`, `space_worktree`, `canvas`; `session.space_id`+`session.worktree_id` + 2 partial indexes); `space/models.py` (`Space`/`Worktree`/`Canvas`/`SpaceGitIdentity`/`ResolvedWorktree`, UUID id types) |
| 162 | 70f34a8 | detect and persist spaces | back | Spaces | `space/detection.py` (git probe → `DetectedSpace`/`DetectedWorktree`, `repo_instance_key`); `space/store.py` (`SpaceStore`: upsert/resolve/claim git identity); `conftest` fixtures |
| 163 | 29fde3d | expose space routes | back | Spaces | `api/v1/space_routes.py` (501 LOC route module); `main.py` (`_resolve_current_space`, router include) |
| 164 | 5fb3ce0 | **rekey managed runs by worktree** | back | Spaces (deep weave) | `run_models.py`, `run_manager.py`, `run_routes.py`, `captured_run_models.py`, `shared_proxy/*`, `session/{models,dao_statements}.py`, `index/adapters/base.py`, `ingest.py`, `tailer.py` + tests |
| 165 | 70493a4 | backfill session space identity | back | Spaces | `session/backfill.py` (`resolve_session_cwd` → `(space_id, worktree_id)`), `async_dao.py`, `session_routes/models.py`, `main.py` (`_backfill_session_spaces`), re-touches `space/store.py`+`space/models.py` (adds `ResolvedWorktree.from_worktree`) |
| 166 | 3be3c61 | www launcher scopes + Canvas re-key | front | Spaces | all `www/src/session-canvas/*` + `api.ts` + `types.ts` (canvas keyed `space:<spaceId>`, launch posts `worktreeId`) |
| 168 | 357a166 | isolate pytest session store DBs | back (tests) | Hygiene (entangled) | `conftest`, `config.py` (`TEST_DB_PREFIX`, `Settings.session_store_url`), `session/testing.py` (per-worker template DBs), `test_run_routes_support.py` (NEW), `main.py` |
| 169 | e3aaecf | harden test DB isolation | back (tests) | Hygiene (clean) | `session/pool.py` (`_guard_pytest_session_store_url`), `session/testing.py` (`drop_stale_templates`), `conftest`, `config.py`, `main.py` |

No `#167` exists on `main`. `#161-#166` are one Spaces series; `#168/#169` are later test-DB hygiene.

## 2. The identity model is correct (premise refuted at source)

Two identity axes exist, and they **reconcile hierarchically** rather than competing:

- **Space = canonical, cross-checkout.** `space_git_identity.repo_instance_key` is
  `sha256(resolved git_common_dir)` (`detection.repo_instance_key`), with
  `CONSTRAINT space_git_identity_repo_instance_key_uq UNIQUE (repo_instance_key)`
  (`0006_spaces_foundation`). All worktrees of one clone share `git_common_dir` → one Space.
  **This is exactly how CLAUDE.md's "two checkouts of the same project share history" is realized.**
  The pre-existing per-path `workspace_id` (blake2b of resolved cwd) never achieved this.
- **Worktree = per-checkout execution unit.** `space_worktree` keyed by
  `UNIQUE (owner, workspace_slug, workspace_hash)` and `UNIQUE (owner, path)`. A run/pane that
  executes somewhere correctly carries `worktree_id`.

Claims that this is a "wrong model needing rebuild" were checked and **refuted**:

| Claim (rebuild case) | Source-of-truth refutation |
|---|---|
| "Canvas is keyed by `default_worktree_id` (per-checkout)" | `0006`: `canvas.space_id uuid NOT NULL` FK to `space`; `default_worktree_id` is a *nullable* `ON DELETE SET NULL` pointer. Canvas belongs to a **Space**. |
| "Sessions scatter by worktree; director can't address the workspace" | `0006` creates **`session_space_ix ON "session" (owner, space_id, started_at DESC)`** — the cross-checkout addressing path exists alongside `session_worktree_ix`. |
| "Front end keys canvas wrong (not by workspace)" | `route.ts defaultCanvasId` → `space:<spaceId>`; `canvasCacheStorage.canvasCacheKey` namespaces by that; `worktreeSwitchUrl` drops `canvas_id` so same-Space worktree switches keep the shared canvas. |

**Conclusion:** the model honors the North Star (API-first; canonical, cross-checkout identity).
The frontend even moves canvas state from per-checkout fragmentation toward per-Space sharing.

## 3. Real salvage-cost debt (the actual findings — all iterate-level)

1. **Redundant dual key.** `space_id` + `worktree_id` are carried together on `ManagedRun`,
   `SessionRow`, `ProxyRunBinding`, `SharedProxyBindingPayload`, and the captured-run ref, but
   `space_id` is **always derivable** from `worktree_id`: `ResolvedWorktree.from_worktree` sets
   `space_id=worktree.space_id` (`space/models.py`). Collapse to worktree-only-plus-derive.
2. **Retained legacy columns.** `session.workspace_slug`/`workspace_hash` kept alongside the new
   ids; DAO special-cases null with `COALESCE(EXCLUDED.space_id, "session".space_id)`
   (`dao_statements.py`). Transitional dual-keying never cleaned up.
3. **Dead / forward-declared fields.** Front-end `CanvasModel.cwd` retained and hardcoded `null`
   post-rekey; captured-run ref `sessionId?` declared but unpopulated ("Slice 7"); `fetchWorktrees`
   (`api.ts`) added but launcher reads worktrees off inlined `SpaceSummary.worktrees` (likely dead export).
4. **Mid-series rework smell.** `ResolvedWorktree.from_worktree` (the shared run/session resolution
   seam) was extracted only in #165, after #164 had already shipped its own resolution. The shared
   contract arrived a slice late — a smell, not rot.
5. **Nullability split.** Required on in-memory `ManagedRun`, `| None` on persistence/proxy edges,
   forcing the COALESCE special-case above.

None of these is a foundation defect. All are a focused DRY/dead-code pass.

## 4. Revert feasibility map

**Not a clean reverse-order `git revert`.** Concentrated backend conflict job.

- **`git apply --check --reverse` probe (reverse order):**
  - #166 (www): **CLEAN**.
  - #165, #164, #163, #162, #161: **fail to apply** (stricter than revert's 3-way; #161/#162
    fail mainly because #165 re-edited the same files, which 3-way would mostly resolve).
- **Hard conflicts:** `main.py` (#163 `_resolve_current_space`, #165 `_backfill_session_spaces` +
  lifespan) was **rewritten by #168** — `git blame HEAD` shows those lines now owned by `357a166`,
  signature changed to `_resolve_current_space(pool, settings)`. `conftest.py` similarly churned by
  #168/#169 adjacent to #162's `space_store` fixture. `config.py` is **not** a Spaces conflict
  (Spaces never touched it).
- **#164 is the deepest cut:** `SpaceId`/`WorktreeId` are required structural fields and SQL columns
  across `run_manager` (`_ValidatedSpawnRun`), `run_models`, `session/models`, `async_dao`,
  `shared_proxy/{models,binding}`, `index/adapters/base`, `captured_run_models`, `dao_statements`.
  Removing them is a broad surgical edit, not a patch revert.
- **Migration `0006`: reverts safely** — it is the chain head (`down_revision = 0005_…`; nothing
  has `down_revision = 0006`); has a working `downgrade()`.
- **#168/#169:** #169 is cleanly keepable (no Spaces refs). **#168 is entangled** — its NEW
  `test_run_routes_support.py` imports `space.models.{ResolvedWorktree,WorktreeId}` and
  monkeypatches `run_routes.SpaceStore`, and its `main.py` hunks sit on #163/#165 lines. A Spaces
  revert forces manual reconciliation of #168.

**Effort to revert: moderate-to-high** — frontend (#166) + migration trivial; backend (#161-#165)
is roughly a half-day of manual 3-way resolution + a deliberate `SpaceId/WorktreeId` type removal.
Reverting costs about as much as the cleanup in §3, while throwing away a correct foundation.

## 5. Per-slice salvage verdict

| # | Verdict | Evidence (one line) |
|---|---------|---------------------|
| 161 | **keep** | Schema is the correct canonical-path model (`repo_instance_key` UNIQUE on git_common_dir); safe to migrate, chain head. |
| 162 | **keep** | `detection.repo_instance_key` derives Space identity from `git_common_dir` (canonical, cross-checkout); store is sound. |
| 163 | **keep** | API-first surface (`space_routes.py`) — matches twin-clients North Star; no UI-only logic. |
| 164 | **keep + clean** | Correct (a run executes in one checkout → `worktree_id`); debt = redundant `space_id` pairing; this is the most expensive slice to revert. |
| 165 | **keep + clean** | Backfill resolves `cwd → (space_id, worktree_id)`; debt = retained `workspace_slug/hash` + COALESCE special-case. |
| 166 | **keep + clean** | Front end correctly keys canvas by `space:<spaceId>` (honors mandate); debt = dead `CanvasModel.cwd`, forward-declared `sessionId`, likely-dead `fetchWorktrees`. Reverts cleanly if ever needed. |
| 168 | **keep** | Real test-DB isolation hygiene, but couples to `space` symbols in test support + overlaps #163/#165 in `main.py` — keep on main; only a problem if reverting Spaces. |
| 169 | **keep** | Clean, independent hardening (`pool.py` guard, stale-template sweep); no Spaces refs. |

## 6. Overall lean: **ITERATE**

From the salvage + entanglement angle only:

1. **No wrong foundation.** The suspected "wrong identity model" was the rebuild thesis; verified
   against `0006` and `route.ts`, the model is coherent and finally implements the canonical-path
   mandate. There is nothing identity-level to rebuild *away from*.
2. **High salvage value.** Six slices of working schema, detection, store, API, run/session rekey,
   and a re-keyed canvas — the remaining work is a bounded DRY/dead-field cleanup (§3), not rework.
3. **Expensive revert.** `SpaceId`/`WorktreeId` are load-bearing across run/session/proxy/index, and
   #168/#169 overwrote the Spaces seams in `main.py`/`conftest.py`. Reverting is a manual backend
   refactor costing as much as the cleanup, with worse risk.
4. **Hygiene is keepable** (confirming the brief's hypothesis, with the nuance that #168 has
   test-support coupling to space symbols, so it is not *independently* revertible).

**Recommended next step (if pursued):** a single iterate pass — collapse the `space_id`+`worktree_id`
pair to worktree-only-plus-derive, drop retained `workspace_slug/hash` and dead `CanvasModel.cwd`,
remove the dead `fetchWorktrees`/`sessionId` forward-decls — rather than any revert.

## Open questions / caveats

- `apply --check` is stricter than `git revert`'s 3-way merge; the conflict set above is an upper
  bound. Empirical confirmation would need a throwaway `git worktree` (avoided here under the
  no-writes constraint).
- "Salvage + entanglement angle only" per brief — this scout does **not** assess test coverage
  quality, runtime correctness of the rekey, or whether the Spaces UX matches product intent.
