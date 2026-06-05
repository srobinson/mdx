# Slice 2 Review — Transcript Ingest onto the Postgres Session Store

Reviewer: backend-engineer (build reviewer). One adversarial pass.
PR #35 `feat/session-2-transcript-ingest` @ `13a1f0d` (vs base `9ba8888`, 887/-172, 11 files).

Verdict: **APPROVE.** 0 blockers, 0 majors. 2 minors (both latent/dormant, non-blocking). `cd api && just ci` is green against Postgres (1239 passed, no skips).

---

## Findings

### Minor 1 — `_parent_seq` mis-points across an interleaved non-turn record

`session/ingest.py:144-147`. `_parent_seq` returns `ctx.seq - 1` when `turn.parent_id == ctx.parent_id`. But in `index/tailer.py:ingest_records`, `parent_id` is threaded only across **turns** (`parent_id = turn.turn_id` only when `turn is not None`), while `seq` advances per **record**. So when a record that normalizes to `None` (codex `turn_context`/`session_meta`, or a claude `summary` line) sits between a parent turn and its child turn, `ctx.seq - 1` points at the **meta event's seq**, not the parent turn's seq.

Repro (records `A(turn)`, `M(meta→None)`, `B(turn)` with `B.parentUuid == A.uuid`):
- A → seq 0, sets `parent_id = A.uuid`
- M → seq 1 (meta event), `parent_id` unchanged
- B → seq 2, `turn.parent_id == ctx.parent_id (A.uuid)` → `parent_seq = 2 - 1 = 1` → points at **M**, not at A (seq 0).

Impact is bounded today: `parent_seq` is currently **write-only** — no SELECT/reconstruction consumes it (`grep parent_seq` → only `dao.py` write + `ingest.py` compute). It is also rebuildable (tier-2 projection), so a later fix + replay corrects historical rows. But the durable column is being written wrong for every session with an interleaved non-turn record, and a future threading reader will trust it.

Suggested fix: thread the parent turn's actual seq alongside `parent_id` in `ingest_records` (e.g. `last_turn_seq = seq - 1` captured where `parent_id = turn.turn_id` is set), and have `_parent_seq` return that instead of assuming `ctx.seq - 1`.

### Minor 2 — backfill binding hardcodes `cwd=""`; session upsert is last-writer-wins on `cwd`

`session/backfill.py:62` builds the replay `SessionBinding` with `cwd=""`. Two coupled facts make this a latent clobber:
1. `cwd` is recoverable on the transcript-only path — claude records carry a top-level `cwd`, codex `session_meta` carries `cwd` — but `_binding` drops it.
2. `session/dao.py:43` upserts `cwd = EXCLUDED.cwd` (last-writer-wins, **not** COALESCE, unlike `cli`/`native_session_id`/`source_descriptor`/`home_dir`).

Not a present-slice bug: the live path sources a real `cwd` from `run_facts.cwd`/`bind_exchange` (`index/ingest.py:134`) and the re-bind preserves it (`index/tailer.py:298`); and `replay_transcript_run` is extraction-only this slice (confirmed: not wired to any writer in non-test code). The risk lands when a future slice wires `replay_transcript_run → SessionWriter`: a backfill running after live capture would upsert `cwd=""` over a real `cwd`. Recommend either sourcing `cwd` from the first record on the replay path, or making the `cwd` upsert preserve a non-empty existing value, before backfill is wired to a writer.

---

## Observations (non-defects)

- **Wire/SQLite tier-2 is now unfed in live runtime** (`addon_runtime.py` passes `make_index_sink(None, ...)`; `IndexWriter` no longer constructed). This is the intended wire-parking for this slice — index/* left intact but dormant. Consequence: live wire exchanges land in tier-1 only and are not queryable in any tier-2 index until a later slice builds Postgres wire ingest. Flag only if the interim UI needs wire query continuity.
- **`submit_blocking` timeout safety rests on idempotency, not on cancel** (`session/writer.py:55-58`). On a 5s timeout `future.cancel()` cannot reliably stop an already-running commit, so the row may still land while the caller treats it as failed and leaves the cursor un-advanced. The next poll re-submits and the `ON CONFLICT (session_id, seq) DO UPDATE` makes that safe. Correct as written; worth a one-line comment that the idempotent upsert is load-bearing here.
- **`raw` retains inline image base64 after `ir` redaction** (`session/ingest.py:_turn_ir` redacts `ir.parts` but `raw=dict(record)` keeps the bytes). By design — `raw` must stay byte-faithful for fork/resume; artifact dedup serves search/serving. Not a leak, just no storage saving on `raw`.

---

## Verified strengths (the hard checks)

1. **Durable-commit seam is correct and tested.** `SessionWriter.submit_blocking → CommitResult` schedules `_commit_batch` onto the captured server loop via `run_coroutine_threadsafe`, guards against running on the target loop, and times out (`writer.py:46-60`). The whole batch (session upsert + events + artifacts + `pg_notify`) is one `conn.transaction()` — per-**batch** atomicity, `pg_notify` inside the txn tied to durability (`writer.py:75-94`).
2. **Cursor advances ONLY after commit — my #1 pre-PR risk, directly tested.** `ingest_records` builds `seq`/`parent_id`/`model` in locals and assigns to the cursor **after** `submit_batch` returns; `_poll_cursor` advances `byte_offset` then `stat_signature` last (`tailer.py:108-137, 245-268`). `test_cursor_state_advances_only_after_submit_success` forces a `submit_batch` raise and asserts `byte_offset==0`, `seq==0`, `parent_id is None`, `stat_signature is None`, then a clean retry on the next poll. Tee-failure branch covered by `test_snapshot_failure_does_not_advance_and_retries_next_poll`.
3. **Idempotency/dedup on `(session_id, seq)`** — `ON CONFLICT DO UPDATE`; `test_session_writer_commits...reingest` submits the same batch twice and asserts exactly 2 events.
4. **Meta rows NOT dropped** — `build_event(turn=None)` → `EventKind.META` with `raw`/`ts`/`model`; tested (`meta.kind=="meta"`, `meta.ir is None`, `meta.model=="claude-opus"`).
5. **Replay core is genuinely transcript-only** — `replay_transcript_run` reads `sessions.json` + `transcript_snapshot_path` only; `test_replay_transcript_run...without_wire_index` deletes `index.jsonl` and still yields records. Does **not** reuse the wire-coupled `rebuild.py:replay_run`.
6. **DRY** — reuses `iter_complete_records` (the one iterate seam) and `ingest_records` (the one record→turn loop, now generic over `RecordWrite` via `build_record`/`submit_batch`); legacy SQLite path preserved through the optional `submit`/`_per_record_submit` fallback and `make_index_sink(writer: IndexWriter | None)`.
7. **Import DAG / privacy / LOC** — no back-edge (`index/*` and `storage/*` do not import `session`); `session→storage` is a legal forward edge; `test_private_import_boundary.py` passes; all changed files <700 LOC (ingest 220, writer 114, backfill 109, tailer 336), functions well under 150.

## Verification evidence (run vs Postgres `localhost:55432`)

- `ruff format --check` → 16 files already formatted; `ruff check` → All checks passed.
- `mypy src/` → Success, no issues in 302 source files.
- `pytest` (full suite) → **1239 passed in 8.84s**, no skips. CI `ci.yml` has the `postgres:17` service + `TRANSPORT_MATTERS_TEST_DATABASE_URL`; session tests carry no skip-guard (hard-require PG).

---

## Fix verification @ `1a70b1a` — both minors RESOLVED

Engineer pushed fixes for the two minors; verified the deltas vs this review.

- **Minor 1 RESOLVED.** `TurnContext.parent_seq` (`adapters/base.py:127`) and `TailCursor.parent_seq` (`tailer.py:81`) added; `ingest_records` threads `parent_seq = turn.seq` when a turn is emitted and commits it to the cursor only after `submit_batch` (rollback invariant preserved). `_parent_seq` (`ingest.py:144-147`) now returns `ctx.parent_seq`. New `test_parent_seq_uses_prior_turn_seq_across_meta_record` reproduces a1→`summary`(None)→b1 and asserts `b1.parent_seq == 0` (a1's seq), not the meta's seq 1; `test_cursor_state_advances_only_after_submit_success` extended to assert `cursor.parent_seq` rolls back on failure.
- **Minor 2 RESOLVED.** `backfill._cwd` recovers `cwd` from the first record (top-level or `payload`, via shared `_record_string`) and threads it into `_binding` (no more hardcoded `""`). Upsert is now `cwd = COALESCE(NULLIF("session".cwd, ''), EXCLUDED.cwd)` (`dao.py:43`) — preserves a non-empty existing cwd, backfills an empty one. New tests: `test_session_upsert_preserves_non_empty_cwd` (re-upsert `""` keeps `/real`) and `test_replay_transcript_run_recovers_claude_record_cwd`.
- **CI green @ `1a70b1a`** vs PG: `ruff format` OK, `ruff check` passed, `mypy src/` clean (302 files), `pytest` **1242 passed** (+3 regression tests), no skips. Scope tight — no creep beyond the two minors plus a DRY `_record_string` refactor and house-style comment cleanups in `base.py`.

**Slice 2: APPROVED.**
