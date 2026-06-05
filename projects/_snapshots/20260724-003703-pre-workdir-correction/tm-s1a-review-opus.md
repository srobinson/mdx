# S1a review — opus (domain / contract / aggregate / write-once lens)

Reviewer: opus architect, multilaunch warroom. READ-ONLY, no gates run (grok owns
the authoritative gate; builder self-gated). Scoped lens: write-once atomic-group
invariant, affinity domain module, backfill, STEP-0 extraction, migration, DRY.

Target: `git diff d7bfb9ac..bcb36c9c` (S1a `bcb36c9c` "feat(session): add immutable
affinity stamps", 23 files). Spec: `~/.mdx/projects/tm-s1-spec-confirm.md` (S1a
portion) + S1 of `tm-replan-newshape-architect.md`. Model: cm `019f8a57`.

## Verdict (my lens)

**Blockers: 0 · Majors: 0 · Minors: 1 · Builder-trust: TRUST (strong).**

The crown jewel — the write-once atomic-group stamp — is correct and minimal. I
tried to break the invariant along four axes (reingest, partial group, concurrent
first-writers, backfill race) and it holds on all four. S1a is correctly scoped to
the **session persistence layer only**; the launch-identity threading
(`SessionBinding`/`RunContext`/adapters/runtime TS) is a later slice and is absent
from this diff by design.

## 1. Write-once atomic-group SQL — HOLDS (the core guarantee)

`session_statements.py::UPSERT_SESSION_SQL` drives all eight affinity columns off
**one shared predicate** on `ON CONFLICT DO UPDATE`:

```
CASE WHEN "session".canvas_id IS NULL AND EXCLUDED.canvas_id IS NOT NULL
     THEN EXCLUDED.<col> ELSE "session".<col> END
```

Because every affinity column keys off the *same* boolean, the group flips as a
unit or stays as a unit — no column can adopt a value from a different snapshot
than its siblings. Case analysis:

- **Stored `canvas_id` NULL + incoming present** → whole group adopts EXCLUDED
  (fills a legacy/unstamped row atomically). A legacy `space_id`/`worktree_id`
  present without canvas is *replaced* by the full snapshot, never mixed — the
  intended §c behavior.
- **Stored `canvas_id` NOT NULL** → every branch is ELSE → row byte-unchanged.
  Once stamped, immutable forever, including a legitimately-null `parent_canvas_id`
  or `worktree_branch_name`.
- **Incoming `canvas_id` NULL** → predicate false for all → stored preserved. A
  later canvas-less ingest can neither clear nor partially fill a stamp.
- **Concurrent first writers** → Postgres serializes the conflicting row update;
  the second sees the first's committed `canvas_id` and takes ELSE. No interleave
  can splice two snapshots.

The atomicity depends on the invariant *incoming `canvas_id` NOT NULL ⟹ full
required group present*. That invariant is enforced on **both** write paths (§2),
so the SQL can trust the sentinel. **I found no interleaving or value where a
stored affinity byte changes on reingest, and no path where a partial group
lands.**

## 2. Validator is wired on both write paths — enforced, not decorative

- **Live ingest:** `ingest.py::build_session` → `_binding_affinity(binding)`. If
  `canvas_id` is absent it returns eight nulls; otherwise it calls
  `affinity.validate_affinity_group`, which raises `ValueError` on a partial group
  before any SQL. So a binding with `canvas_id` set but `canvas_name` null fails
  closed at ingest rather than persisting a partial stamp. Test
  `test_stamp_group_is_atomic_never_mixed` asserts the `pytest.raises(ValueError)`.
- **Backfill:** `backfill.py::backfill_session_spaces` constructs a
  `SessionAffinityStamp` (pydantic requires the six non-null fields) before calling
  the DAO. A partial resolution cannot reach SQL.

`validate_affinity_group` is airtight: `AFFINITY_REQUIRED_FIELD_NAMES` correctly
omits only the two legitimately-nullable fields (`parent_canvas_id`,
`worktree_branch_name`); all-null → returns `None` (no snapshot); any required
field null with others set → raises. `canvas_id`-present ⟹ full-required-group is
guaranteed.

## 3. serialize_canvas_path — canonical + deterministic

`segment.model_dump(mode="json", by_alias=True)` then
`json.dumps(..., ensure_ascii=False, separators=(",", ":"))`. Key order is the
stable `CanvasPathSegment` field order (no `sort_keys` needed, dict insertion order
is deterministic), UTF-8 preserved, compact separators, aliases (`canvasId`)
retained. Round-trips id/name/kind per segment without loss. The backfill test pins
the exact serialized string
(`[{"canvasId":"…","name":"main","kind":"worktree_root"}]`), locking the format.

## 4. Backfill fill-missing — race closed, root canvas resolved, DRY

- Candidate sentinel is `canvas_id` (`LIST_SESSIONS_MISSING_SPACE_IDENTITY_SQL`
  `WHERE s.canvas_id IS NULL`) — the two nullable fields correctly cannot signal
  presence.
- `UPDATE_SESSION_SPACE_IDENTITY_SQL` carries `AND canvas_id IS NULL`, closing the
  select-to-update race: if a concurrent write stamps the row between select and
  update, the predicate matches zero rows and a present snapshot always wins.
  Cannot overwrite an existing stamp.
- Resolves the honest root Canvas via
  `get_canvas(rest_caller(resolved.space_id, owner=owner), resolved.root_canvas_id)`
  — the previously-discarded `ResolvedWorktree.root_canvas_id` is now used.
- Reuses `SessionAffinityStamp` + `serialize_canvas_path`. **No forked identity
  path.** `test_backfill_fills_missing_canvas_only` proves fill-missing fills and a
  protected already-stamped row is left byte-unchanged.

## 5. Row decode / column parity — legacy rows still readable

All six new `SessionRow` fields default `None`, so legacy rows (canvas columns
null) validate through `dao_rows.one_session`. `SESSION_COLUMN_NAMES` (hence
`RETURNING {SESSION_COLUMNS}` and every SELECT), the INSERT column/VALUES list, and
`session_params` (derived from `model_dump`) all carry the same eight affinity
fields — INSERT/RETURNING/params parity is intact.

## 6. STEP-0 extraction — clean facade, zero duplicated SQL

Session-row SQL moved to `session_statements.py`; `dao_statements.py` re-exports
every session constant via explicit `import X as X` and retains only the
event/wire/artifact SQL it still owns. `SESSION_WORKSPACE_ID_SQL` /
`workspace_id_sql` are defined once (in `session_statements`) and re-exported, not
redefined. `async_dao.py` now imports the session constants directly from
`session_statements`; `controlplane_statements.py` still imports through the
`dao_statements` facade and resolves via the re-export. No duplicated constant, no
dangling reference.

## 7. Migration 0031 — correct

Adds the six columns (`canvas_id`/`parent_canvas_id` uuid, `canvas_name`/
`canvas_path`/`worktree_path`/`worktree_branch_name` text), all nullable (bare
`ADD COLUMN`), matching the spec table. `down_revision = 0030_space_crud_reset`;
`downgrade` drops in reverse. No data backfill in the migration (runtime backfill
owns historical rows). The f-string `ALTER TABLE` interpolates only the hardcoded
`_COLUMNS` tuple (no user input) — no injection surface; consistent with the 0030
raw-SQL idiom.

## Minor 1 (informational, low severity) — atomic-group staging nulls live affinity until the threading slice

`build_session._binding_affinity` returns eight nulls whenever `canvas_id` is
absent on the binding — which is **always** in S1a, because `SessionBinding` is not
threaded with canvas identity until the later slice. This *discards*
`binding.space_id`/`binding.worktree_id` at ingest even though those two attributes
exist on the binding. This is the intended atomic-group contract (space/worktree
enter only as part of a full canvas snapshot or via backfill), and it is **not** a
production regression: `build_proxy_run_binding` already leaves those fields null in
production (scout §1), so live bindings carry null affinity today regardless.
Consequence to flag: in S1a every live launch is written with null affinity and
relies entirely on startup backfill; live-launch stamping only actually turns on in
the threading slice. Recommend the orchestrator confirm no read surface (session
list space/worktree filters) is expected to reflect live stamps before threading
lands — backfill covers historical rows, so the interim is benign. No code change
required for S1a.

Nit (not counted): `_binding_affinity` uses `assert stamp is not None` for type
narrowing after the `canvas_id`-present guard; unreachable when `None`, but stripped
under `python -O`. Harmless. Leave as-is or narrow with an explicit branch.

## Test rigor — red-first, observable end-state

The four write-path tests assert what the database actually stores, and are red at
base (columns/fields absent):
- `test_stamp_is_write_once_across_reingest`: two *different* full snapshots, assert
  `stored_first == stored_second` (row bytes). Exercises the sentinel ELSE branch.
- `test_stamp_group_is_atomic_never_mixed`: legacy space/worktree set, then a full
  incoming snapshot; asserts stored == incoming's full shape (legacy did **not**
  survive → no mixing) **and** a partial upsert raises. Also proves
  `affinity_launch_fields` strips a forged caller carrier.
- `test_snapshot_survives_hard_delete_as_tombstone`: real Space service creates a
  canvas, stamps a session, `DELETE FROM canvas`, asserts the canvas is gone **and**
  the session still reads the frozen snapshot. FK-free tombstone proven live.
- `test_backfill_fills_missing_canvas_only`: fills a missing row (full group incl.
  serialized `worktree_root` path) and leaves a protected row unchanged.

Honest scoping: the spec's test #1 `test_launch_stamps_canvas_identity_on_first_session`
is **correctly deferred** — it needs `SessionBinding` canvas threading, which is not
in S1a. Not a gap.

## Builder-trust: TRUST (strong) — supports large delegation

This is a gpt build; Stuart is gauging delegation. On the highest-stakes property in
the slice, the implementation is right and elegant:
- **Craftsmanship:** the single-sentinel guard driving all eight columns off one
  predicate is the minimal correct shape for an atomic write-once group; the
  neutral `affinity.py` module single-sources validation, path serialization, and
  the launch carrier codec across ingest, backfill, and (future) launch.
- **Test rigor:** observable end-state, red-first, adversarial (forge-strip,
  legacy-not-mixed, hard-delete tombstone, protected-not-overwritten).
- **Spec + reuse fidelity:** followed the confirmed spec's SQL, sentinel, backfill
  race guard, and STEP-0 extraction precisely; reused `ResolvedWorktree.branch_name`
  / `get_canvas` rather than forking a second identity resolver.
- **Shortcuts:** none found in my lens. Scope discipline (no premature threading) is
  a positive signal, not a cut corner.

## Scope note

Verdict scoped to write-once/domain/contract/STEP-0/migration/DRY. **Deferred:** the
full launch-identity threading slice (not in this diff); `just check`/`just test`/
`migration-smoke` → grok. My lens found the core guarantee sound.
