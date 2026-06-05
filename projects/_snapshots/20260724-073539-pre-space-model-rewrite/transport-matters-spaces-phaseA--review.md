# Spaces — Phase A architect review (Slice 1 + Slice 6 plans)

Date: 2026-06-21
Reviewer: codebase-analyst pane (ARCHITECT, warroom Mode 2)
Base: `main @ 2323169`, tree pristine (verified `git status` clean).
Plans reviewed:
- `transport-matters-spaces-slice1--plan.md` (Identity + schema foundation; Codex-drafted, amended)
- `transport-matters-spaces-slice6--plan.md` (www launcher scopes + Canvas model; self-drafted, fresh-eyes)
Design/requirements: `transport-matters-spaces--proposal.md` (R1–R7), index `transport-matters-spaces--plan.md`.

Method: every cited symbol / path / signature in both plans was verified against the live tree
(fmm + targeted reads via three parallel verification passes). Findings below carry file+symbol
evidence; "verified clean" sections record what was checked and held.

---

## SLICE 1 — Identity + schema foundation

### S1-1 — [Major] Frozen Worktree/Space contract omits fields Slice 6 surfaces (`is_primary`, `kind`, `label`)

Slice 1's own Goal is "Later slices cite the exact type names, DTO fields, table names, constraints."
But the www DTOs Slice 6 builds against (`WorktreeSummary`, `SpaceSummary` in `slice6 Task A`)
carry fields with **no home** in Slice 1's frozen models/schema:

- `WorktreeSummary.isPrimary` (slice6 `buildSpaceRows`/`worktreeTitle` → `"main worktree"` label and
  single-vs-multi ordering depend on it) — `space_worktree` has no `is_primary` column and
  `Worktree` (`space_models.py`) has no `is_primary` field. In a detect-only cut where `GET /v1/spaces`
  (Slice 3) reads the store rather than re-running git each call, the primary flag is unrecoverable
  without persistence.
- `SpaceSummary.kind: "repo" | "plain"` — no `kind` column on `space`, no field on `Space`. Derivable
  from the presence of a `space_git_identity` row, but that derivation is unstated.
- `SpaceSummary.label` vs `Space.name`; `WorktreeSummary.branch` vs `Worktree.branch_name` — a rename
  mapping each later slice must perform.

Evidence: `Worktree` model fields (`space_models.py`, slice1 lines 284-299: `path, workspace_slug,
workspace_hash, branch_name, head_oid, missing, archived`, no `is_primary`); `space_worktree` DDL
(slice1 lines 633-653, no `is_primary`); vs `WorktreeSummary { worktreeId, spaceId, path, branch,
isPrimary, missing }` (slice6 lines 48-59). **Fix:** either persist `is_primary` on `space_worktree`
+ add to the `Worktree` model (detection in Slice 2 already knows it), or state explicitly in Slice 1
that `is_primary`/`kind`/`label`/`branch` are Slice-3 response projections, not frozen domain fields.
As written the "frozen contract" silently misses a field the launcher cannot render without.

### S1-2 — [Minor] Casing contract unstated: domain models dump snake_case; the public wire is camelCase

The Slice 1 models serialize snake_case and the tests assert it (`model_dump() == {"space_id": …}`,
slice1 lines 61-65, 134-142). The shipped public wire is camelCase (`RunView { runId, workspaceId,
sessionId, createdAt }`, `api.ts`). If a later slice returns `Space`/`Worktree`/`Canvas` Pydantic
models directly from `/v1/spaces`, the wire is snake_case and breaks www's camelCase
`SpaceSummary`/`WorktreeSummary` (slice6 Task A/E). Mitigated because the www shapes differ enough to
force separate DTOs anyway — but Slice 1 should state these are internal domain models and that Slice 3
response DTOs apply the existing camelCase alias convention (the one `RunViewModel` already uses).

### S1-3 — [Minor] `space_git_identity` is in "Frozen contracts: tables" but has no row model

The migration creates `space_git_identity (space_id, repo_instance_key, git_common_dir, detected_at)`
(slice1 lines 617-630) and the header lists the table as a frozen contract, but `space_models.py`
defines no `SpaceGitIdentity` model. Slice 2 ("mint/lookup Space by `repo_instance_key`", writes the
identity row — index Slice 2) needs that row shape; the freeze slice is its natural home. Add a frozen
`SpaceGitIdentity` DTO or note it is intentionally a Slice-2 internal.

### S1-4 — [Minor] Task 1 commits without the slice gate; the custom `__eq__` will trip `mypy`

Task 1 ends (Steps 4-5) running only `pytest tests/test_space_models.py`, then commits — it never runs
`just check` (verified: api `just check` = `ruff format` + `ruff check --fix` + `mypy src/`,
`api/justfile`). The writing-plans convention is each task ends green on the gate. Concretely, the new
`_UuidId.__eq__` reads `other._value` on an `object`-typed param
(`return type(self) is type(other) and self._value == other._value`, slice1 lines 223-224) — `mypy`
will report `"object" has no attribute "_value"` (it does not narrow on `type(self) is type(other)`),
so `just check` fails on `space_models.py`. As written, that failure surfaces only in Task 2's gate.
**Fix:** add a `just check && just test` step to Task 1 before its commit, and guard the `__eq__`
(`isinstance(other, type(self))` narrowing, or `cast`).

### Slice 1 — verified clean (checked, held)

- Migration style: raw `op.execute("""…""")` SQL matches every existing migration 0001-0005
  (`op.execute('CREATE INDEX …')` in 0001; `ALTER TABLE … ADD COLUMN` in 0004). No `op.create_table`
  convention to honour. ✓
- Revision wiring: `down_revision = "0005_session_template_provenance"` is valid — 0005's
  `revision` is exactly that string (`0005`'s own down_revision is `0004_session_purpose_visibility`). ✓
- R6 (reversible downgrade, ids stay text): downgrade drops indexes → session cols → canvas →
  space_worktree → space_git_identity → space (correct dependency order, slice1 lines 699-712). uuid PKs;
  `session_id/run_id/workspace_slug/workspace_hash` stay `text` (asserted by `_SPACES_TEXT_COLUMNS`).
  `repo_instance_key` is `text`. The test correctly stops the downgrade chain at `0002` and never hits
  `0001` (which `raise`s — forward-only, as the proposal notes). ✓
- `test_migrate.py` integration: all replaced/called helpers exist exactly as named
  (`_reset_to_unmigrated`, `_session_columns` returns `frozenset` so `.isdisjoint` works,
  `_assert_*_present/absent`, `_dead_letter_indexes`, `test_alembic_upgrade_and_downgrade_smoke`).
  `connect()` (from `session.pool`) sets `row_factory=dict_row`, so the new helpers' `row["table_name"]`
  string indexing is correct. `migrate.{apply_migrations,current_revision,migration_head,alembic_config}`
  and `command.downgrade` all exist. ✓
- R1 (ResolvedWorktree shape): `{space_id, worktree_id, cwd, workspace_slug, workspace_hash, missing,
  archived}` matches the proposal R1 exactly. ✓
- Pydantic v2 + `ConfigDict(frozen=True)` and `from __future__ import annotations` are the established
  style. Typed-id wrappers are genuinely new (api ids are plain `str` today) but this is the locked
  Decision-1 littleorgans `lilo-common::id` convention, so it is intended divergence, not drift. ✓
- short-prefix test math is correct (7-char floor; `"12345678-"` for the len==9 predicate). ✓

---

## SLICE 6 — www launcher scopes + Canvas model

### S6-1 — [Major] Gates are bare `pnpm`, not the repo recipe `just check && just test`

Every task gates on `pnpm typecheck && pnpm test` and the final verification on
`pnpm typecheck && pnpm test && pnpm lint`. The canonical www gate (verified `www/justfile`) is
`just check` = `pnpm format` + `pnpm lint:fix` + `pnpm typecheck`, and `just test` = `pnpm test`. The
plan **never runs `pnpm format`**, so a worker's well-typed, test-passing code can still carry biome
formatting drift that commits clean locally and then fails CI `just check`. (It also uses read-only
`pnpm lint`, where the recipe uses `pnpm lint:fix`.) Slice 1 gates correctly on `just check && just test`;
Slice 6 should too. **Fix:** replace every `pnpm typecheck && pnpm test [&& pnpm lint]` with
`just check && just test` (run from `transport-matters/www/`).

### S6-2 — [Major] Task F points at the wrong file for the `select-worktree` handler

Task F Step 5 + Files list locate the `onCommand` switch in `CommandCenter.tsx` ("the host that owns
`onCommand`"). It does not live there: `CommandCenter.tsx` only forwards `onCommand` to
`useCommandCenter`. The actual command switch is `useCanvasCommandHandler` in
**`CanvasSurface.tsx`** (switch ~L89, cases `spawn / reset-view / focus-picker / goto / cycle-theme /
toggle-bypass-permissions / set-canvas-gesture-modifier`; the `goto` case the plan says to mirror is
~L99). So Task F is two edits in two files, which the plan conflates:

- `CommandCenter.tsx` — construct `useSpaces()` + `activeWorktreeId` and pass them into the
  `useCommandCenter({…})` call (where `useCommandCenter` is built). ✓ correct location.
- `CanvasSurface.tsx` — add the `select-worktree` case (with `parseCanvasLaunchContext` +
  `initializeCanvas`) to `useCanvasCommandHandler`. **Missing from Task F's Files list and commit.**

Note `CanvasSurface.tsx` is already edited in Task A (state.id → canvasId, L226), so Task F edits it a
second time. As written, a worker following the Files list edits `CommandCenter.tsx` and the
select-worktree dispatch — the whole point of the launcher feature — lands nowhere. **Fix:** add
`src/session-canvas/components/CanvasSurface.tsx` to Task F Files + commit and split Step 5 into the two
hosts explicitly.

### S6-3 — [Minor] `CapturedRunPane.cwd` is already dead; "replace `cwd={…}`" has nothing to replace

Task E Step 4 says "pass it to ensureRun … replacing any `cwd={…}` it [registry] passes today."
`registry.tsx`'s captured-run render maps only `runKey`/`provider`/`runtimeTemplate` — it has never
passed `cwd`. `CapturedRunPane` declares `cwd?` (L16), destructures it (L36), and lists it in the effect
deps (L60), but the prop is unfed/dead. The "any `cwd={…}`" hedge technically covers zero, so the task
is still completable, but the instruction reads as if a mapping exists. **Fix:** state plainly "add
`worktreeId={props.pane.contentRef.worktreeId}` to the captured-run registration (no `cwd` mapping
exists today)" and remove the now-truly-dead `cwd` deps when swapping to `worktreeId`.

### S6-4 — [Minor] Two load-bearing claims lean on `tsc` without enumeration

(a) `CanvasModel.id → canvasId` (Task A) names only `CanvasSurface.tsx:226` and relies on `tsc` to find
other `.id` readers (persistence partialize/merge, lab store). (b) "the only production terminal site is
the lab" (Task B Step 9) makes `worktreeId` required on terminal refs safe only if no production path
builds a terminal ref. `tsc` catches literal constructions but not a factory or `as`-cast. Both are
acceptable for a typed rename/field-add, but Task A's Files list should acknowledge the sweep the way
Task B/E do, and a one-line grep confirming no production terminal-ref construction would de-risk Task B
before the field is made required.

### Slice 6 — verified clean (checked, held)

- R3 fully covered: `worktreeId` required on `terminal`+`captured-run`, optional on `resource(url)`
  (Task B union + guard); `defaultWorktreeId` promoted into `CanvasModel` (Task A). `CanvasId` is already
  exported from `paneRecords.ts` (so Task A importing only `SpaceId`/`WorktreeId` from `types` is
  correct). ✓
- R7 covered for the www cut: Space rows titled by project label (never bare "Space"), test asserts no
  row reads like the `Canvas gesture modifier: Space` settings row; no "Surface" rename. ✓
- R1/R2 covered: `api.ts` `createCapturedRun(cwd)` → `(worktreeId)`, `RunView`/`RunFilters` drop
  `workspaceId` and add `spaceId`/`worktreeId`, query forwards `space_id`/`worktree_id`. Verified
  current `RunView` has `workspaceId` and `RunFilters` is `{state?}` only — the rewrite is accurate. ✓
- Symbol/signature accuracy is high: `buildScopeRows(scope, inputs, query)` and the `case "workdir":
  return buildDeferredRows("Workdir")` it replaces both exist as quoted; `NavFrame`,
  `createScopeNavFrame`, `pushFrame`, `topFrame`, `LauncherCommand`, `RowAction`, `ScopeRowInputs`,
  `CommandRow` match the plan's assumed shapes. The plan correctly accounts for the two real drifts the
  verification surfaced and that it already handles: `createCanvasStorePersistOptions()` takes no args
  today (Task D adds `getCanvasId`), and `CanvasPersistOptionsConfig` has no `storage` field today
  (Task D adds it + overrides the hardcoded `storage:` line). `useNavFrameStack`/`descend` carry no
  `param` today (Task F adds it). All three are correctly anticipated by the plan. ✓
- `requestApiJson(path, fallback, init?)` exists (real caller `fetchRuntimeTemplates`), so the new
  `fetchSpaces`/`fetchWorktrees` are well-founded; `useRuntimeTemplates` exists and is a faithful mirror
  for `useSpaces`. ✓
- Format/TDD discipline otherwise solid: every task is failing-test → FAIL → impl → PASS → commit, with
  complete code (no `TODO`/`implement later`); the `tsc`-driven sweeps enumerate exact files; a
  self-review section maps each spec bullet to a task. ✓

---

## Summary

- **Slice 1:** 1 Major (S1-1 frozen-contract gap: `is_primary`/`kind`/`label`), 3 Minor (S1-2 casing,
  S1-3 missing `space_git_identity` model, S1-4 Task-1 gate timing + `__eq__` mypy). Schema/migration/
  test-integration mechanics verified correct.
- **Slice 6:** 2 Major (S6-1 bare `pnpm` gate omits `pnpm format`; S6-2 `select-worktree` handler
  targets the wrong file / `CanvasSurface.tsx` omitted from Task F), 2 Minor (S6-3 dead `cwd` mapping,
  S6-4 unenumerated `tsc` sweeps). Symbol accuracy and R1/R2/R3/R7 coverage otherwise strong.

Highest-impact fixes: S6-2 (Task F lands the feature in the wrong file), S1-1 (a launcher field with no
home in the frozen schema), S6-1 + S1-4 (gate hygiene that lets CI-red commits through).
