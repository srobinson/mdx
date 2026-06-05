# S1a session affinity stamp sink — large-context review + full gate (Grok)

Date: 2026-07-23  
Slice: **S1a** session affinity stamp **sink** (DAO / migration / backfill / codec / row model)  
Spec: `~/.mdx/projects/tm-s1-spec-confirm.md` (S1a) + architect S1 foundation section  
Model of record: cm `019f8a57`  
Range: `d7bfb9ac..bcb36c9c` (23 files, +1016 / −267)  
Commit: `bcb36c9c` feat(session): add immutable affinity stamps  
Reviewer: `multi-launch:general:1:2.4` (read-only review; **sole authoritative local-CI runner**)  
Tree: pristine at `bcb36c9c` before gates  
Note: review judgment is **paired** with opus/gpt; **this gate result is the green/red authority**.

## Verdict

**SHIP on gate for S1a sink.** Session write path, migration 0031, STEP-0 SQL extraction, atomic write-once UPSERT, fill-missing backfill, and neutral `session/affinity.py` cohere with the locked S1a/spec-confirm sink contracts. Launch threading (SessionBinding/RunContext, `resolve_run_affinity`, canvas pane, proxy carrier) is correctly **out of this 23-file slice**.

| Severity | Count | Summary |
|----------|------:|---------|
| blocker | 0 | — |
| major | 0 | — |
| minor | 3 | leftover "space identity" naming on list/update symbols; empty-string not rejected as absent for required snapshot strings; launch carrier helpers production-shipped but only test-wired until S1b |

## Gate (authoritative, independent)

Tree clean at start (`git status --porcelain` empty; `HEAD == bcb36c9c`).

| Gate | Result | Evidence |
|------|--------|----------|
| `just check` | **PASS** | desktop typecheck + 102 tests; shell format/lint/typecheck (biome schema info only); product-plane + common/contract/activity/runtime/gateway/core/inspector/canvas typecheck; api ruff format unchanged + ruff check "All checks passed!" + mypy **685** "Success: no issues found" |
| `just test` | **PASS** | JS: desktop **102** + shell **1273** + common **24** + contract **8** + activity **288** (34 skip) + runtime **190** (2 skip) + gateway **21** = **1906** passed / **36** skipped. API: **3439 passed / 0 failed**. Combined **5345 passed / 36 skipped** |
| `just migration-smoke` (from `api/`) | **PASS** | `pytest -n0 session/test_migrate.py` → **9/9**. Head revision `0031_session_affinity_stamp` (down_revision `0030_space_crud_reset`). Dedicated `test_session_stamp_migration` also passed in full suite (up/down/up column nullability) |

Gate exit codes and summary lines were read from full command output, not piped-tail alone.

## Large-context sweep (23 files)

### What landed (S1a sink map)

| Contract | Implementation | Coherence |
|----------|----------------|-----------|
| Fresh mig 0031, six bare nullable columns, no data backfill | `api/migrations/versions/0031_session_affinity_stamp.py` | Matches (b); reverse-order downgrade |
| STEP-0 SQL extraction under 700 | `session/session_statements.py` (284) owns session SQL; `dao_statements.py` (507) reexports facade | Facade name set **exact** match to `session_statements` public names; no duplicate SQL constants elsewhere |
| Exact write-once UPSERT with `canvas_id` sentinel CASE | `UPSERT_SESSION_SQL` in `session_statements.py` | Matches spec-confirm (c) shape byte-for-byte on affinity arms |
| Backfill candidate + update guards | `LIST… canvas_id IS NULL`; `UPDATE… AND canvas_id IS NULL` + full eight-column SET | Matches (c) runtime backfill SQL |
| Neutral codec module | `session/affinity.py` — `SessionAffinityStamp`, `validate_affinity_group`, `serialize_canvas_path`, launch carrier pair | Matches (e)5 recommended owner |
| Write-boundary validation | `dao_rows.session_params` → `validate_affinity_group(session)` | Partial group rejected before SQL; row decode still accepts legacy partial |
| Ingest atomicity | `ingest._binding_affinity`: no `canvas_id` ⇒ eight nulls; present ⇒ full validated stamp | Matches atomic-group rule; drops partial space/worktree-only binding (intentional) |
| SessionRow columns | six new nullable fields on `SessionRow` | Matches (e)8 |
| Backfill uses root canvas + branch | `get_canvas(rest_caller…, root_canvas_id)` + `ResolvedWorktree.branch_name` + `serialize_canvas_path` | Matches (e)9 / branch threading |
| `ResolvedWorktree.branch_name` | added + `from_worktree` copy | Matches (d) recommendation |
| Tests (architect 2–6) | write-once, atomic never-mixed (+ launch carrier unit), tombstone, backfill fill-missing only, migration | `test_launch_stamps…` correctly deferred with launch path |

### DRY / facade / dangling refs

- **No duplicated SQL constants** after extraction: production importers (`async_dao`, `controlplane_statements`) import from `session_statements` or the `dao_statements` facade; facade reexport set is complete (0 missing / 0 extra).
- **No leaked unused public symbols** in the new modules beyond the deliberate S1b-ready launch carrier helpers (`affinity_launch_fields` / `affinity_from_launch_fields`), which are covered in `test_stamp_group_is_atomic_never_mixed`.
- **Import-facade integrity**: `dao_statements` reexports with explicit `X as X` blocks; external `from transport_matters.session.dao_statements import …` remains valid for non-session SQL consumers (`wire_store`, etc.).
- **Migration symmetry**: upgrade adds six columns; downgrade drops in reverse order; head/EXPECT constants updated in `session/testing.py`, space CRUD migration head assertion, roundtrip intermediate 0030 stop.

### Explicitly out of S1a (not findings against this commit)

Full S1 still needs (later slice):

- `SessionBinding` / `RunContext` eight-field set (binding still has only `space_id`/`worktree_id`; `_binding_affinity` uses `getattr` so it is forward-compatible)
- `resolve_run_affinity`, canvas pane `spaceId`/`canvasId` forwarding, runtime/capture `canvasId`, proxy payload, membership fix on explicit Space launch
- Architect test `test_launch_stamps_canvas_identity_on_first_session`

This 23-file commit does not claim those seams.

### Minor findings

1. **Naming lag (minor).** Symbols still say "space identity" (`LIST_SESSIONS_MISSING_SPACE_IDENTITY_SQL`, `update_session_space_identity`, `list_sessions_missing_space_identity`) while the sentinel is now `canvas_id` and the payload is the full affinity stamp. Spec-confirm kept the names; rename is hygiene for a follow-up, not a behavior bug.

2. **Empty string treated as present (minor).** `validate_affinity_group` treats only `None` as absent. A required field set to `""` passes the partial check and may persist. Unlikely from server-resolved snapshots; tighten if a hostile/manual writer appears.

3. **Launch carrier helpers unwired in production (minor / expected).** Codec is the correct S1a landing pad; production call sites arrive with S1b. Tests already cover replace-forged-carrier and clear-on-null stamp behavior.

### LOC ceilings

| File | LOC | Note |
|------|----:|------|
| `session/dao_statements.py` | 507 | Well under 700 after STEP-0 |
| `session/session_statements.py` | 284 | New focused owner |
| `session/affinity.py` | 100 | New |
| `session/writer.py` | 682 | Untouched; stays under 700 |
| `packages/runtime/.../RunManager.ts` | 664 | Untouched (launch not in S1a) |

No file over 700 in this slice.

## Spec fidelity checklist (S1a)

| Approval lock / sink contract | Status |
|-------------------------------|--------|
| `canvas_path` as compact JSON of `CanvasPathSegment[]` | **Met** (`serialize_canvas_path`: `mode="json"`, `by_alias=True`, `separators=(",",":")`, `ensure_ascii=False`) |
| `ResolvedWorktree.branch_name` threaded | **Met** |
| `parent_canvas_id` stamped now | **Met** (columns + stamp + backfill + UPSERT) |
| Null initial affinity without verified Canvas | **Met** (ingest nulls full group; tests updated for proxy/ingest) |
| Write-once stored-wins once `canvas_id` present | **Met** (CASE guards + write-once test) |
| Atomic group / no partial write | **Met** (validate + null-if-no-canvas + atomic test including legacy partial replace) |
| Backfill fill-missing only | **Met** (SQL guard + test leaves protected stamp) |
| Migration no data backfill | **Met** |
| STEP-0 under 700 | **Met** |

## Builder-trust verdict

**TRUST (high) for S1a sink delegation.**

| Dimension | Assessment |
|-----------|------------|
| Craftsmanship | Clean STEP-0 extraction before growth; single SQL owner; facade preserved; migration minimal and reversible; affinity module is the right neutral seam |
| Test rigor | Architect sink tests present with real DB + hard-delete tombstone + concurrent-style legacy→full replace; foundation/ingest/proxy tests updated for atomic null behavior; migration dedicated + roundtrip intermediate 0030 |
| Spec/reuse fidelity | UPSERT and backfill SQL match locked shapes; reuses `get_canvas` + `rest_caller` + existing path projection rather than inventing branch detection |
| Shortcuts | None material. Did not fake launch coverage. Did not leave dual SQL definitions. Did not grow files past 700 |

Caveat for Stuart: this trust applies to the **sink** only. Full S1 still needs the launch authority and binding threading before Canvas-pane first-session stamps are live end-to-end.

## Final line (bus)

`0 blocker / 0 major / 3 minor · FULL GATE PASS (check + 5345 passed/36 skip + migration-smoke 9/9 head 0031_session_affinity_stamp) · path ~/.mdx/projects/tm-s1a-review-grok.md · BUILDER-TRUST: HIGH (S1a sink; launch threading deferred S1b)`
