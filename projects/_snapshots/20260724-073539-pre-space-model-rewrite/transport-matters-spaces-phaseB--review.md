# Spaces — Phase B architect review (Slices 2, 3, 4, 5)

Date: 2026-06-21
Reviewer: codebase-analyst pane (ARCHITECT, warroom Mode 2)
Base: `main @ 2323169`, tree pristine (verified clean before and after).
Plans: `transport-matters-spaces-slice{2,3,4,5}--plan.md`, against the amended Slice 1 frozen
contract (`SpaceGitIdentity`, `Worktree.is_primary`, casing contract) and requirements R1–R7.
Method: every cited symbol/path/signature verified against the live tree via three parallel
verification passes (fmm + targeted reads). Findings carry file:symbol evidence.

Weighting per directive: Slice 4 (run re-key) highest. Headline findings: **S3-1** (the launcher's
list contract is broken) and **S5-1** (Slice 5 startup wiring is non-viable).

---

## SLICE 4 — run re-key + ResolvedWorktree + drop workspaceId  *(highest weight)*

### S4-1 — [Major] `_spawn_test_view` does not exist; the list-filter test cannot run

Task 2's `test_list_runs_filters_by_space_and_worktree` calls
`harness.manager._spawn_test_view(space_id=..., worktree_id=...)` (slice4 lines 364-365), but no
`_spawn_test_view` exists anywhere in the repo (grep api/www/desktop: zero hits; the harness is
`ManagedRunHarness` at `api/.../api/v1/test_run_routes.py`, no such method). As written the test
fails with `AttributeError`, not the intended filter assertion. **Fix:** the plan must define
`_spawn_test_view` (a seam that inserts a `ManagedRunView` carrying identity without a full spawn) and
list it as a concrete edit, or rewrite the test to spawn through `manager.spawn(SpawnRun(resolved_worktree=…))`
like Task 1's tests do.

### S4-2 — [Major] Task 3 Step 5 (the SessionWriter identity seam) is underspecified

The orchestrator's priority check is "is `ResolvedWorktree` threaded `SpawnRun→ManagedRun→ManagedRunView→SessionWriter`
without leaving `cwd` as the only identity?" Steps 1–4 thread identity precisely with complete code, but
Step 5 — the exact seam where the captured-run `SessionBinding` is built — goes hand-wavy: "Where the
managed run builds the launch binding for captured runs, include these complete fields…" (slice4 lines
706-712). No file, no function, no surrounding code, despite `session/writer.py` being in the Files list.
This is the one place identity can silently drop, and it is the least specified step. **Fix:** name the
binding-construction function and show the complete edit that sources `space_id`/`worktree_id` from the
`ManagedRun` (which Task 1 now carries) into `SessionBinding`. Without it a worker cannot complete the
`→ SessionWriter` half of R1.

### S4-3 — [Minor] `run_view_model` hard-raise vs. the retained cwd-only spawn contract

`run_view_model` is rewritten to `raise RuntimeError` when `view.space_id`/`worktree_id` is None (slice4
lines 535-536). Verified safe today: there is exactly one `SpawnRun` construction site (`_spawn_request`)
and one `manager.spawn` caller (`create_run`), and the desktop CLI-in-canvas path goes through the same
HTTP `/v1/runs` route — so every RunManager run is created via the worktreeId-resolve path and has
identity. But `SpawnRun` still keeps optional `cwd`/`space_id`/`worktree_id` and `_resolve_cwd` keeps a
`Path.cwd()` fallback (slice4 lines 230-234) plus the "CLI internal compatibility path … leave ids None"
(Step 5). So the model permits an identity-less spawn that would crash serialization. **Fix:** either make
identity required on the spawn contract (drop the cwd-only/`Path.cwd()` fallbacks) or document the
invariant "every RunManager run carries identity" so the contradiction is explicit. Positive note: the
old `_workspace_id_for_view(view) = workspace_id(view.cwd)` cwd-recompute is correctly deleted, so no
`GET /runs`/filter/idempotent path recomputes identity from cwd.

### S4-4 — [Minor] `workspaceId` assertion sweep is under-enumerated

Dropping `RunViewModel.workspace_id` breaks api tests asserting `workspaceId` at
`api/.../api/v1/test_run_routes.py:78, 97, 160`. Task 2 names only `test_post_get_attach_detach_and_terminate`
(slice4 line 348). Enumerate all three sites. Blast radius is otherwise contained: no www **runtime**
code reads `RunView.workspaceId` (only the `api.ts:472` type, retyped by Slice 6); no desktop consumer;
`api.test.ts` is stubbed so it does not hit the live API. So Slice 4 landing before Slice 6 leaves only a
stale-but-unused www type, not a runtime break.

---

## SLICE 3 — `/v1/spaces` routes + camelCase DTOs

### S3-1 — [Major / Blocker-adjacent] `GET /v1/spaces` omits the inlined `worktrees[]` the launcher requires

Slice 3's `SpaceSummary` is `{spaceId, label, kind, archived, createdAt, updatedAt}` — **no `worktrees`**
(slice3 lines 27-34, 392-400). `list_spaces` even constructs `SpaceSnapshot(item.space, item.git_identity, ())`
with empty worktrees (line 645), and the store's `list_spaces` does not fetch them. But Slice 6's
`SpaceSummary` (consumed by `useSpaces()` → `buildSpaceRows`/`buildWorktreeRows`) **requires
`worktrees: WorktreeSummary[]` inlined** for the single-vs-multi decision and the worktree sub-scope, and
the locked design states a Space is returned "with its worktrees inlined for the launcher's single-vs-multi
decision." As written, the launcher fed by `GET /v1/spaces` sees `space.worktrees === undefined` and
cannot render or descend. **Fix:** inline `worktrees[]` (and `SpaceSnapshot` worktrees) in the list
response, or reconcile the cross-slice `SpaceSummary` contract with Slice 6 (which is already locked and
corrected expecting inlined worktrees). This is the highest-impact cross-slice gap in the set.

### S3-2 — [Minor] `created_at`/`updated_at` typed `object | None`

`SpaceSummary.created_at/updated_at: object | None` (slice3 lines 399-400) instead of `datetime`/`str`.
`model_dump(mode="json")` serializes a datetime held in an `object` field via the fallback any-serializer
(works), and the test pins the value tautologically, so it passes — but the loose type defeats schema
validation and is inconsistent with the typed domain models. Prefer `str | None` (pre-isoformatted) or
`datetime | None`. Otherwise Slice 3 is sound: camelCase via per-field `serialization_alias` + `by_alias=True`
mirroring `RunViewModel`, `kind` derived from `git_identity` presence (no column), owner scoping on every
route, no `workspaceId` reintroduced, detect-only (no worktree create/checkout/remove). Verified: `create_app`,
`lifespan`, `_start_session_store`, `app.state.session_pool`, the include_router block, `session_client`,
`optional_session_pool`, `require_http_origin` all exist as cited.

---

## SLICE 5 — session backfill + empty-cwd legacy

### S5-1 — [Major / Blocker for Task 5] Startup wiring references invented `app.state` singletons

Task 5 Step 3 wires `if app.state.session_dao is not None and app.state.space_store is not None:` (slice5
lines 664-668). Verified: **neither attribute exists.** `app.state` carries `session_event_hub`,
`session_pool`, `session_event_listener`, `shared_proxy_manager`, `run_manager` — no `session_dao`, no
`space_store`. Worse, both `AsyncSessionDao` and `SpaceStore` are **connection-scoped** (`__init__(self, conn)`,
constructed per-request as `async with pool.connection() as conn: AsyncSessionDao(conn)`), so they cannot be
long-lived app.state singletons. **Fix:** model Task 5 on Slice 3's `_resolve_current_space(pool)` —
open one pooled connection at startup and build `SpaceStore(conn)` + `AsyncSessionDao(conn)` there. Also:
the cited file `api/app.py` does not exist; the startup home is `main.py`'s `lifespan`.

### S5-2 — [Major] Task 5 tests use invented helpers; cannot run as written

`settings_with_database_enabled()`, `settings_without_database()`, and `lifespan_context` do not exist
(`config.py` exports only `settings_path`/`settings_example_text`; the lifespan is `main.lifespan`, an
`@asynccontextmanager`, with no `lifespan_context` alias). The test file `api/test_app_startup_spaces.py`
and import targets are net-new. **Fix:** drive startup via the real `lifespan` + a `TestDb`/settings
override the suite already uses; do not cite helpers that must first be invented.

### S5-3 — [Major] SessionRow/Binding edits duplicate Slice 4; the expected-FAIL is stale

Slice 4 already adds `space_id`/`worktree_id` to `SessionRow` (`session/models.py`), `SessionBinding`
(`index/adapters/base.py`), `SESSION_COLUMN_NAMES`, and `UPSERT_SESSION_SQL`. Slice 5 runs **after** Slice 4
(index order 4→5) yet Task 3 Step 3 re-adds the same fields to `SessionRow` (slice5 lines 451-460) and its
expected failure is `TypeError: SessionRow … unexpected keyword argument 'space_id'` (slice5 lines 442-444) —
which cannot happen post-Slice-4. **Fix:** Slice 5 must build on Slice 4's `SessionRow`; its genuinely new
work is `legacy_group` + the session list filters + the backfill, so re-target the failing test to the
DTO (`KeyError: 'spaceId'` / missing `legacyGroup`), not the row constructor.

### S5-4 — [Major] `space_store` pytest fixture does not exist

Task 2 tests take `space_store: SpaceStore` as a fixture (slice5 lines 299-301, 314-316), but no
`space_store` fixture exists anywhere (Slice 2's own store tests construct `SpaceStore(conn, …)` inline and
define none). **Fix:** author the fixture (build `SpaceStore(conn)` over a `TestDb` pool) — ideally in
Slice 2 so Slice 5 can cite it — and `get_worktree(...)` (slice5 line 325) must also be added to `SpaceStore`
(Slice 2 defines `resolve_worktree`/`list_worktrees`, not `get_worktree`).

### S5-5 — [Minor] Citation drifts + cost + no-op migration

- `SessionViewRow` → the real type is `SessionListRow` (`session/models.py`); `PublicSessionModel` → the
  real DTO is `SessionView` using `ConfigDict(alias_generator=_to_camel, …)`, **not** per-field
  `serialization_alias` (so adding fields needs no explicit alias — the plan's "mirror RunViewModel
  serialization_alias" is the wrong convention for this model). `dao: SessionDao` (sync) lacks the async
  `list_session_views`; the scanner needs `AsyncSessionDao` (`session/async_dao.py`).
- Task 6 migration is effectively a no-op: Slice 1 already ships nullable `session.space_id`/`worktree_id`,
  `space_worktree.missing`, and partial indexes `session_space_ix`/`session_worktree_ix`. The proposed
  `idx_session_space_id` plain index would **duplicate** the Slice 1 partial index; rely on the preflight
  grep and add nothing.
- `resolve_session_cwd` → `resolve_cwd` → `detect_space` runs git subprocesses **per present-cwd session**
  at startup inside `lifespan`. Idempotent (only None-identity rows), but a large history means a slow,
  subprocess-heavy startup. Consider batching or a note.

Positive: R4 is well covered — empty-cwd is provably never resolved/assigned (`backfill_session_spaces`
`if not cwd: legacy_unassigned += 1; continue`, slice5 lines 212-215), `legacyGroup:"unassigned"` is
surfaced, and `/v1/sessions?workspaceId=` is retained as the legacy history filter, with an explicit
"Failure Modes to Guard Against" section reinforcing it.

---

## SLICE 2 — detection + Space store

### S2-1 — [Minor] Space `name` is taken from whichever worktree first triggers detection

`detect_space` sets `name=toplevel.name` (slice2 line 294), where `toplevel` is `--show-toplevel` of the
target cwd. Detecting first from a **linked** worktree names the Space after the linked dir, not the repo's
primary; since `upsert_detection` sets `name` only on INSERT (`_insert_space`), the name sticks and surfaces
as the Slice 3 `label`. Space identity is correctly keyed by `repo_instance_key` (so re-detection reuses the
same `space_id`), but the label is order-dependent. **Fix:** derive `name` from the **primary** worktree's
toplevel (the record whose `.git == common_dir`), not the detection entry point.

### S2-2 — [Minor] Detection cost: ~2N+2 git subprocesses per Space

`_worktree_from_path` runs `git branch --show-current` + `git rev-parse HEAD` per existing worktree
(slice2 lines 360-361), on top of the initial `rev-parse` probe and `worktree list`. For an N-worktree repo
that is ~2N+2 subprocess spawns per detection, and detection runs on every `resolve_cwd`/refresh and on every
present-cwd session during Slice 5 backfill. Functionally correct; worth a note or a `--porcelain` HEAD/branch
read from the `worktree list` output to avoid the per-worktree fan-out.

Verified clean: R5 is satisfied — relative `--git-common-dir` is resolved against the target cwd
(`_resolve_git_path(value, base=resolved_target)`, with the git probe run at `cwd=resolved_target`), and
`test_relative_git_common_dir_is_resolved_against_target_cwd_not_process_cwd` (process-cwd ≠ target-cwd)
pins it. `is_primary` detection (`.git == common_dir`) is correct for primary vs linked and survives detecting
from a linked worktree. `workspace_id(cwd)` returns `WorkspaceId` with `.slug`/`.hash` as the plans assume;
`create_async_pool`/`connect` use `dict_row`; minted worktree ids are stable across re-detection (ON CONFLICT
preserves `worktree_id`). The frozen-dataclass `SpaceDetectionError(RuntimeError)` is unusual but valid.

---

## Summary

- **Slice 4 (highest weight):** 2 Major (S4-1 `_spawn_test_view` missing; S4-2 SessionWriter seam
  underspecified), 2 Minor (hard-raise vs cwd-only contract; workspaceId assertion sweep). The contract
  drop itself is contained.
- **Slice 3:** 1 Major (S3-1 list response omits inlined `worktrees[]` — breaks the Slice 6 launcher),
  1 Minor (object-typed timestamps).
- **Slice 5:** 4 Major (S5-1 invented app.state singletons / conn-scoped store; S5-2 invented test helpers
  + wrong paths; S5-3 SessionRow duplication + stale expected-FAIL; S5-4 missing `space_store` fixture +
  `get_worktree`), 1 Minor (citation drifts + backfill cost + no-op migration).
- **Slice 2:** 2 Minor (order-dependent Space `name`; detection subprocess cost). Detection/R5/is_primary
  mechanics verified correct.

Highest-impact: **S3-1** (the launcher cannot work against the spec'd list endpoint) and **S5-1/S5-2**
(Slice 5's startup wiring + tests reference symbols that do not exist and a store shape that cannot be an
app.state singleton). **S4-1/S4-2** are the load-bearing Slice 4 gaps.
