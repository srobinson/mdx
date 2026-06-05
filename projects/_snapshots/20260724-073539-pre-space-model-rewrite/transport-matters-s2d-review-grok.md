# S2d adversarial review — PR #296

- **PR:** https://github.com/littleorgans/transport-matters/pull/296
- **Range:** `main @ 7dc7dc3f` … `feat/s2d-block-store @ 670c4c41`
- **Diff source:** `gh pr diff 296` (read-only; shared tree left pristine)
- **Files:** 14 changed, +1316 / −19
- **Reviewer:** grok (adversarial + code-hygiene on the 14 files only)
- **Gates:** not run (deferred to pre-merge full gate)

## Summary

Supersession write path is correct and well tested: immutable create
(`INSERT … ON CONFLICT (block_id) DO NOTHING`), one-way conditional
supersede (`UPDATE … WHERE status='active'`, rowcount-0 = already
superseded), no whole-row upsert, no resurrection path, no
`observed_at` recency guard. Pure / store split, `ExecutorVersionBlock`
composition, secret-safe drift vocabulary, migration 0023 shape, and
`match_release` launch-path non-call all hold.

Two Major issues remain: (1) four-seam drift *emission* is vocabulary
plus a store/audit helper only, with no production call sites at the
plan-named seams; (2) pure `blocks.py` imports `session.quarantine`
and therefore the psycopg stack, breaking the pure-leaf import shape
used by sibling harness modules.

## Verdict counts

| Severity | Count |
|----------|------:|
| Blocker  | 0 |
| Major    | 2 |
| Minor    | 3 |
| Nit      | 3 |

**Craftsmanship:** Strong supersession and store craft; emission and pure-leaf boundary unfinished.

---

## Focus checklist

| Focus | Result |
|-------|--------|
| Create = immutable INSERT ON CONFLICT DO NOTHING | Pass — `blocks_store.py:48-57` |
| Supersede = one-way conditional UPDATE + rowcount-0 | Pass — `blocks_store.py:62-66`, `124-143` |
| No whole-row upsert / no resurrection | Pass — tests `test_stale_active_record_cannot_resurrect_superseded_block`, `test_duplicate_create_is_a_no_op` |
| Recency key = revision, not observed_at | Pass — no timestamp recency on block writes; revision stored, not used as observed_at-style watermark (correct for events) |
| Supersession across all four scopes + restart | Pass scopes; restart covers active only (see Minor) |
| Conditional-upsert idiom reused (not SELECT-then-write / app clock) | Pass — same rowcount interpretation as `persist_connection`; `fetch_all` extracted to `pool.py` |
| Migration 0023 additive, symmetric downgrade, head, roundtrip, CHECK via `sql_text_values` | Pass |
| Secret redaction: closed reason codes + digest only | Pass — no raw output columns; model enforces sha256 digest |
| Multiple active per scope key (no partial unique) | Pass — decision honored |
| `superseded_by` FK-less | Pass |
| Attribution: no block without release+route+model; pause otherwise; no auto create | Pass pure policy; `block_from_evidence` refuses pause cases |
| `match_release` uncalled on launch path | Pass — production callers: none; only tests + probes docstring |
| `blocks.py` pure / `blocks_store.py` I/O | Mostly — pure broken by quarantine import (Major) |
| `compatibility.py` stayed flat (export only) | Pass — rename `_require_sha256_digest` → `require_sha256_digest` |
| `ExecutorVersionBlock` composes `VersionBlock` | Pass — subclass + two identity fields, not 14-field redeclare |
| Four-seam emitters | Under-delivered (Major) |

---

## Issues

### Issue 1 — Severity: Major
- **File:** plan surface / seam integration (expected: `adapters/base.py`, `index/tailer.py`, session bootstrap, `controlplane/prompt_delivery.py`; actual touch: `session/quarantine.py:19-30` only)
- **Description:** Plan S2d item 2 and scout step 3 require typed drift evidence emitters for four seams (wire parse, transcript reader vs storage, session bootstrap, actuation) with run correlation and audit recording. Delivered: pure constructors (`wire_parse_drift`, `transcript_reader_drift`, `session_bootstrap_drift`, `actuation_drift`), `transcript_failure_is_drift`, and `emit_drift_evidence` (store + audit). Zero production call sites. `rg` over non-test package code finds no imports of constructors or `emit_drift_evidence`. Quarantine gained `is_storage_plane`; adapters, tailer, session lifecycle, and prompt delivery are untouched.
- **S2d/S2f boundary:** Auto block creation and first production `match_release` are correctly deferred to S2f. Live *evidence emission* at the four seams is not S2f ownership (S2f is resolver, launch gating, setup actions, advisory rollout). As written, S2d still owns emitters that record. Vocabulary-only delivery is a deliberate half-slice only if the plan is re-scoped; otherwise this is incomplete S2d.
- **Suggestion:** Either (a) wire thin call sites at each seam that construct typed evidence and call `emit_drift_evidence` when the seam can already detect the closed detail codes, or (b) explicitly re-scope S2d to “vocabulary + store + policy” and move seam wiring to a named follow-up with acceptance tests per seam. Do not leave the plan text claiming four-seam emitters while only quarantine changed.

### Issue 2 — Severity: Major
- **File:** `api/src/transport_matters/harnesses/blocks.py:38` (`from transport_matters.session.quarantine import is_storage_plane`)
- **Description:** `blocks.py` is documented as a pure leaf beside `compatibility` / `connections`. Those pure modules stay free of `session` and psycopg. Importing `session.quarantine` pulls `psycopg` and `psycopg_pool` into the pure harness vocabulary import graph. `transcript_failure_is_drift` is the only consumer; the rest of the module does not need storage-plane types.
- **Suggestion:** Move `transcript_failure_is_drift` next to quarantine (or into a small non-pure seam helper), or invert the dependency so pure blocks never import session. Keep `DriftEvidence` constructors I/O- and DB-stack free.

### Issue 3 — Severity: Minor
- **File:** `api/src/transport_matters/harnesses/blocks_store.py:119-122`
- **Description:** `create_block` inserts the full model dump, including `origin` and `status`. Callers can insert `origin="publisher"` into the executor block table, or insert a row already `status="superseded"` without going through `supersede_block`. Resurrection is still blocked (ON CONFLICT DO NOTHING), but write invariants for executor-origin and create-as-active are application-enforced only.
- **Suggestion:** Reject non-`executor` origin and non-`active` status on create (or force those fields in the store), matching the table’s role as the executor-origin store.

### Issue 4 — Severity: Minor
- **File:** `api/migrations/versions/0023_harness_drift_evidence.py:29-37` vs `api/src/transport_matters/harnesses/blocks.py:67-74`
- **Description:** Closed kind/detail vocabulary is duplicated between migration CHECK pairs and `DRIFT_DETAILS_BY_KIND`. Migration isolation often forces this, but a vocabulary drift will not fail until someone adds a mismatched test. Existing migration tests cover unknown kind and foreign detail pair, not “every Python detail is present in SQL.”
- **Suggestion:** Add a single test that `DRIFT_DETAILS_BY_KIND` equals the migration’s `_DETAILS_BY_KIND` (import both or parse the migration constant) so vocabulary cannot fork silently.

### Issue 5 — Severity: Minor
- **File:** `api/src/transport_matters/harnesses/test_blocks_store.py:115-121`
- **Description:** Restart survival asserts only an active create survives a new pool/store. Superseded status + `superseded_by` restart survival is unproven (though list/active paths are covered in-process).
- **Suggestion:** Extend the restart test: create, supersede, reopen pool, assert list shows superseded and active is empty.

### Issue 6 — Severity: Nit
- **File:** `api/src/transport_matters/session/quarantine.py:19-38`
- **Description:** `STORAGE_PLANE_EXCEPTIONS` / `is_storage_plane` were added, but `classify` still hardcodes `(PoolTimeout, FutureTimeoutError)` and a separate `psycopg.Error` branch instead of sharing the timeout pair constant. Behavior is unchanged; DRY is incomplete.
- **Suggestion:** Name the timeout pair once and reuse it in both `is_storage_plane` and `classify`.

### Issue 7 — Severity: Nit
- **File:** `api/src/transport_matters/harnesses/blocks.py:308-328`
- **Description:** `merge_executor_blocks` appends every provided block, including superseded. `match_release` filters `status == "active"`, so outcomes are correct if callers pass `list_blocks`. Surprising if a caller expects merge to mean “matchable set.”
- **Suggestion:** Document that callers should pass `active_blocks()`, or filter `status == "active"` inside merge.

### Issue 8 — Severity: Nit
- **File:** `api/migrations/versions/0023_harness_drift_evidence.py:60`
- **Description:** `evidence_digest` is `text NOT NULL` with no sha256 shape CHECK. Model validation covers the store path; raw SQL can store non-digests (same posture as 0022 block table). Defense in depth only.
- **Suggestion:** Optional CHECK `evidence_digest ~ '^[0-9a-f]{64}$'` if you want storage-layer parity with the model.

---

## Code hygiene (14 files only)

| File | LOC | Notes |
|------|----:|-------|
| `blocks.py` | 328 | Under 700; pure leaf broken by session import |
| `blocks_store.py` | 215 | Clean I/O sibling; good SQL comment discipline |
| `compatibility.py` | 550 | Flat; export rename only; headroom preserved |
| `connections_store.py` | 408 | `fetch_all` extracted; no block write crammed in |
| `quarantine.py` | 49 | Small; storage-plane API added |
| `0023_…py` | 84 | Additive; symmetric DROP TABLE only |
| tests (blocks/store/migration) | 312+153+135 | Real assertions; good supersession matrix |

- No file over 700; no function near 150.
- DRY wins: `fetch_all` in `pool.py`; builders in `connections_test_support`.
- DRY gap: kind/detail vocabulary dual definition (Minor 4); classify vs storage-plane constants (Nit 6).
- Ownership: pure model vs store split matches scout recommendation; no 14-field redeclaration trap.

## Supersession proof (primary risk)

| Case | Test | Assertion quality |
|------|------|-------------------|
| Four scopes | `test_supersession_across_every_scope` | Parametrized version/route/target/release; active empty; status+superseded_by set |
| Idempotent / first writer | `test_supersede_is_idempotent_and_first_writer_wins` | Real: second superseder does not overwrite `superseded_by` |
| Missing block | `test_supersede_missing_block_raises` | Real raise |
| Resurrection | `test_stale_active_record_cannot_resurrect_superseded_block` | Replayed active create leaves superseded |
| Restart | `test_blocks_survive_restart` | Active only (Minor 5) |
| Evidence idempotency | `test_drift_evidence_round_trip_and_idempotency` | First write wins on conflict |
| Audit mirror | `test_emit_drift_evidence_writes_store_and_audit` | Deterministic dispatch_id; closed status/reason only |

## What is solid (do not re-litigate)

- Immutable create + one-way supersede SQL is the right fix class for the S2c snapshot fights.
- No launch-path `match_release` leak.
- No automatic block creation from live evidence.
- Migration 0023, head revision, `reset_to_unmigrated`, roundtrip present/absent path.
- Secret redaction posture (closed codes + digest) matches S2c lesson.
- `ExecutorVersionBlock` composition and compatibility export rename are clean.

## Recommended merge bar

- **Not clean** until Major 1 is either fixed (seam wiring) or the plan/acceptance text is explicitly re-scoped, and Major 2 (pure leaf → session import) is fixed.
- After that, run the deferred full gate: `just check`, `just test`, `cd api && just migration-smoke`.
