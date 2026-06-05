# Slice 1 review — private grounding notes (reviewer: claude / 3.2)

Scope per orchestrator: slice 1 = the `session/` Postgres foundation + DAO boundary.
Engineer = codex/gpt-5.5. ONE adversarial pass against the PR diff -> `review-slice-1.md`.
Spec: `spec-session-store.md` (round-2, all 6 prior findings RESOLVED — do NOT relitigate
them as design; DO verify the build matches the resolution).

Likely slice-1 surface (foundation only; writer/ingest/fork/export are later slices):
- `session/pool.py` (~80) — AsyncConnectionPool + DATABASE_URL resolution
- `session/models.py` (~190) — frozen Pydantic v2 row models: SessionRow, EventRow, ArtifactRow, InlineArtifact
- `api/migrations/` (~300) — Alembic env + initial migration = §2 DDL
- DAO boundary (no driver leakage past `session/`)
- test harness (unique DB, drop on cleanup, parallel-safe)
- deps: psycopg[binary,pool], alembic; `DATABASE_URL` setting; dev `docker-compose.yml`; doctor check

## Repo invariants (grounded)

- **Python >=3.14** (`api/pyproject.toml`). Verify psycopg3 + alembic resolve on 3.14. Probe with `uv run`, not ambient python.
- **CI** (`api/justfile:ci`): `ruff format --check src/` + `ruff check src/` (NO --fix) + `mypy src/` + `pytest`. A diff that only passes `just check` (auto-fix) can still fail CI.
- **pytest** (`api/pyproject.toml`): `testpaths=[src,tests]`, `asyncio_mode="auto"` (async tests need no marker), `addopts="-v --tb=short"`. **No xdist in dev deps** — serial by default, so "parallel-safe" is good-practice not CI-gated; the real risk is clobbering the dev DB at the default DSN.
- **conftest** (`api/conftest.py`): sets `DEBUG=true` pre-import; `_clear_settings_cache` autouse. New PG harness must override DATABASE_URL per test DB without fighting the settings cache.
- **Import DAG** (`api/CLAUDE.md`): `ir→adapters→rules→pipeline→storage→breakpoint→server`; index/session sit AFTER storage, import `ir`+`canonicalization`(+capture subtree); `storage` MUST NOT import `session`; sink injected at `load_runtime()`. session→storage forward edge OK (backfill read helpers).
- **Privacy boundary** (`test_private_import_boundary.py`): AST scan of `api/src/transport_matters` + `api/tests`. Flags `from x import _name` AND `from pkg._privatemod import ...` when module is `transport_matters*`/relative; skips test_/_support/fixtures/conftest. => `session/*` modules MUST NOT import another module's `_`-prefixed name. Each module keeps its own `_` helpers.
- **Types** (`api/CLAUDE.md`): builtins-only generics (`list[str]`, `X | None`); annotate returns; every `Any` needs a comment.
- **Pydantic v2**: `frozen=True` row models; `model_dump(mode="json")` for JSONB writes.
- **LOC**: file <700, fn <~150. Check Alembic migration + queries don't blow it.
- **No em dashes** (charter acceptance bar).

## Existing patterns to check DRY/consistency against

- **SQLite session table** (`index/schema.py` _DDL): mirrors new PG `session`. Old uniqueness `session_native UNIQUE(run_id, provider, native_session_id) WHERE native_session_id IS NOT NULL`. New spec adds `owner` => `(owner, run_id, provider, native_session_id)` (finding 5). VERIFY migration matches spec §2 exactly (the owner dim is the whole point of finding 5).
- **synth identity** (`index/sessions.py:synth_session_id`, `SESSION_NS`): `uuid5(SESSION_NS, run_id|provider|native)`. PG session_id for readback/codex = same synth. If slice 1 re-declares SESSION_NS or synth, that's a DRY break — must reuse `index/sessions` (a KEPT module).
- **db.py** (`index/db.py`): `connect(path, read_only)`, `transaction(conn)` ctxmgr, PRAGMAs. `session/pool.py` is the psycopg3 analog. DAO boundary = psycopg `Connection`/`Cursor`/`Row` types must NOT leak past `session/` public API; callers get row models / plain dicts, not driver objects.
- **schema_meta drop-rebuild gate** (`index/schema.py`: `_GATED_KEYS`, `is_rebuild_needed`, `_DROP_DDL`): spec §8.2 says this does NOT carry over — Alembic version table replaces it. VERIFY: migration is forward-only, NO drop-and-rebuild, NO `DROP TABLE` of session data, no schema_meta gate ported.

## §2 DDL conformance checklist (migration must match spec exactly)

- event PK `(session_id, seq)` — NOT native id (finding 1). native_turn_id/parent_native_id are NON-key attrs.
- event FK `session_id references session(session_id) on delete cascade`.
- `event_kind_ck check (kind in ('turn','meta'))`; default 'turn'.
- `content_tsv tsvector generated always as (to_tsvector('english', coalesce(search_text,''))) stored` — GENERATED STORED, english config (Open Q B resolved to english).
- GIN: `event_ir_gin using gin(ir)` (default jsonb_ops, supports @> and ?), `event_fts_gin using gin(content_tsv)`.
- `event_native_ix on (session_id, native_turn_id)`.
- session: `session_status_ck in (active,completed,archived)`; `session_fork_ck check ((parent_session_id is null) = (forked_at_seq is null))`; self-FK `parent_session_id references session(session_id)`.
- session indexes: native_uq (owner,run_id,provider,native_session_id) partial; browse (workspace_hash, started_at desc); owner (owner, started_at desc); parent (parent_session_id).
- artifact: PK `hash`, `bytes bytea not null`, `size_bytes bigint`.
- event_artifact: PK (session_id, seq, artifact_hash); FK to artifact(hash); composite FK (session_id,seq)->event ON DELETE CASCADE.
- timestamptz everywhere (not timestamp); defaults now().

## Hunt list (adversarial)

1. **Migration correctness vs §2**: every column/constraint/index above present + typed right. Forward-only (no drop-rebuild, finding-aligned). Reversible `down`? (durable store = forward-only per spec, but Alembic convention wants a downgrade — check what the team's lefthook/convention expects; spec says forward-only so an empty/raise downgrade may be intentional — judge, don't reflexively flag).
2. **psycopg3 pool/txn**: AsyncConnectionPool opened at startup, closed at shutdown; bounded max_size; not opened at import time (no eager connect on module import — breaks tests/CI w/o a DB). `open()`/`close()` lifecycle correct for psycopg_pool API (open=False then await pool.open() vs deprecated constructor-open warning). Async vs sync: server async, but slice 1 may only have the pool.
3. **DAO boundary**: no psycopg Connection/Cursor/Row leaking past `session/` public surface; SQL centralized (not scattered string concat); parameterized (no f-string SQL interpolation — SQLi). identifiers via psycopg.sql.Identifier if any dynamic.
4. **config-driven DSN**: DATABASE_URL via Settings (pydantic-settings, `config.py`), dev default `postgresql://tm:tm@localhost:5432/transport_matters`; NO hardcoded provisioning/credentials in code paths other than the documented dev default; secret not logged.
5. **test harness**: creates a UNIQUE db name per run (uuid/worker-scoped), CREATE/DROP DATABASE on a maintenance/autocommit conn to the `postgres` db (can't run inside a txn); drops on teardown even on failure (fixture finalizer); does NOT target the dev `transport_matters` DB (else a dev's real data is dropped — CRITICAL). Tests skip cleanly when no PG available? (CI has no postgres service unless added — verify a postgres service is wired into CI or tests are gated/skipped; a hard import-time connect would red the whole suite).
6. **tests ACTUALLY prove**: round-trip (insert session+event, read back equal); constraints fire (status ck, fork ck pair, native_uq partial, FK cascade); FTS (content_tsv populated + websearch_to_tsquery match); GIN containment (ir @> filter). A test that only creates tables proves nothing.
7. **import-DAG / LOC / privacy breaches**: session→storage only forward; no storage→session; no cross-module `_` import; files <700 / fns <150.
8. **DRY vs repo**: reuse `index/sessions.synth_session_id` + `SESSION_NS`; reuse `config.get_settings`; reuse blake2b helper pattern (`index/blocks.py:block_hash`) rather than re-rolling; don't duplicate `disk_layout`/`session_facts` readers.

Verdict rule: find >=1 substantive issue OR positively justify "none found" with evidence.
COMMS: reply ONLY to orchestrator (transport-matters:general:1:2.1). One-liners: "grounded" then "done: review-slice-1.md". Never message engineer. No debate.

---

# Slice 1 ADDENDUM — settings.toml config layer (2nd review pass, same PR #34)

Contract: `~/.mdx/projects/littleorgans-settings-config-contract.md` (written for Rust `lilo`;
engineer translates to TM/Python). Append findings to `review-slice-1.md` under a new
"settings.toml" section. Delta lands on the slice-1 branch; orchestrator will ping with the delta.

TM translation of the contract:
- `LILO_*` -> `TRANSPORT_MATTERS_*`; `$LILO_HOME` -> `~/.transport-matters` (`storage_roots.default_storage_root()` = `Path.home()/".transport-matters"`).
- serde+toml crate -> `tomllib` (stdlib, already used in `cli/home_seed.py:269`) + Pydantic v2 model. NO new framework (no figment/config/dynaconf).
- `DEFAULT_ADMIN_URL` (Rust) == TM's `session_config.DEFAULT_DATABASE_URL` + `DEFAULT_TEST_ADMIN_DATABASE_URL` (both `:5432`). Contract decision 7: DELETE the silent default; resolution fails LOUD with guidance, never connects to a guessed host.

Current (slice-1) surface to diff against:
- `config.py`: `database_url: str = DEFAULT_DATABASE_URL` (non-optional, silent default), `session_pool_min/max_size`. pydantic-settings `env_prefix=TRANSPORT_MATTERS_`, `.env`, `extra=ignore`.
- `pool.py:resolve_database_url(url=None, settings=None)` -> `settings.database_url` (never raises).
- `testing.py`: admin url = `os.environ.get("TRANSPORT_MATTERS_TEST_ADMIN_DATABASE_URL", DEFAULT_TEST_ADMIN_DATABASE_URL)` -- a SECOND, direct os.environ read (not via Settings). The "don't duplicate env reads" check targets this exact split.
- `env_keys.py`: single source for project-owned keys; has `DATABASE_URL`; the test-admin literal lives in `testing.py` (NOT registered) -- consistency gap to fix.
- `docker-compose.yml`: `"${TRANSPORT_MATTERS_POSTGRES_PORT:-5432}:5432"` (no host-iface bind).

settings.toml checklist (the orchestrator's hunt):
1. Precedence env-over-toml, highest wins: explicit arg -> `TRANSPORT_MATTERS_DATABASE_URL` env -> `settings.toml [database] url` -> LOUD error (no built-in DSN default). test url: `TM_TEST_DATABASE_URL`?? `TM_DATABASE_URL`?? `[database] test_url` ?? `[database] url` ?? loud error. Verify the chain order is actually implemented, not just claimed.
2. Silent default DSN DELETED: grep that `session_config.DEFAULT_DATABASE_URL` / `DEFAULT_TEST_ADMIN_DATABASE_URL` and the `database_url: str = <default>` are GONE; field is `str | None` or resolution raises. `rg "localhost:5432"` -> no hits in app code (compose comment/example may move to 55432).
3. Resolvers don't duplicate env reads: ONE env mechanism. If pydantic-settings reads the env key, the toml layer sits BENEATH it (settings_customise_sources or a resolver that consults Settings, not a fresh os.environ read). The `testing.py` direct os.environ read must be unified or layered, not a parallel second reader of the same key.
4. tomllib + Pydantic only: no new dep in pyproject; tomllib import; a Pydantic model for the toml shape (deny/ignore unknown -- contract used `deny_unknown_fields`; TM Settings uses `extra=ignore`, watch the mismatch for the toml model specifically).
5. `settings.example.toml` committed at REPO ROOT (not api/); live file path = `storage_dir/settings.toml` = `~/.transport-matters/settings.toml`. Loader: missing file -> defaults (NOT error); present-but-malformed -> error.
6. Hermetic tests + 3 required: (a) malformed toml -> raises; (b) missing toml -> defaults; (c) loud-error path: env unset + toml absent -> guidance error naming the env key + the toml path, NOT a connection attempt. Tests must set env first so they never depend on a real `~/.transport-matters/settings.toml` (and must not read the dev's real home -- use load_from(tmp_path) or monkeypatch storage_dir).
7. Compose: rename `TRANSPORT_MATTERS_POSTGRES_PORT` -> `TRANSPORT_MATTERS_DOCKER_PG_PORT`, default `55432`, bind `127.0.0.1:${...}:5432` (contract adds the loopback bind = don't expose PG on all interfaces). Align stray `:5432` mentions to `:55432`. Register the new var in `env_keys.py` + `.env.example`.
8. Minimal scope: ONLY `[database] url`/`test_url`. proxy_port/web_port/storage_dir/cli/run_id/etc stay pure env. No broad migration.
9. DAG/LOC/privacy/DRY: loader placement (config.py vs a new `session_config.py`/settings module) must not cycle (config.py is imported widely; storage_roots is stdlib-only). New test-admin + docker-port keys in env_keys.py (DRY single source). LOC < 700/fn < 150.

Watch-fors (likely bug surface):
- Loud error must fire at RESOLUTION, not only at connect (a `str | None` field that defaults None but pool.connect blindly passes None to psycopg = a different, unguided error).
- `get_settings()` is `@lru_cache`d; a toml source read once is fine, but tests that swap toml/env must `get_settings.cache_clear()` (conftest autouse already does this per-test).
- `extra=ignore` on the toml model would SILENTLY swallow a typo'd `[databse]` table -> defaults -> loud error that confuses the operator. Contract wanted `deny_unknown_fields`. Flag if unknown toml keys are silently ignored.
- Don't break the migration/alembic path: `env.py`/`testing.py:alembic_config` call `sqlalchemy_url(database_url)`; if database_url can now be None, those paths need the loud resolver too.

---

# SLICE 2 — transcript ingest + transcript-only replay core (review -> review-slice-2.md)

Branch `feat/session-2-transcript-ingest` (post-slice-1 baseline @ 9ba8888, clean). `retire-map.md`
referenced by orchestrator but ABSENT in ~/.mdx/projects (note it; not load-bearing for slice 2 since
index/* deletion is a LATER slice). Engineer may be active in THIS working copy -> do NOT switch branches;
read working tree (it's the clean baseline).

## Baseline mechanics (grounded, the seam slice 2 retargets)

`index/tailer.py` (KEPT/retargeted module):
- `iter_complete_records(data) -> (records, consumed)`: consumed = past LAST `\n`; half-written trailing
  line waits; malformed lines skipped (warn, not fatal). THE single record-iterate seam. Slice 2 MUST reuse.
- `ingest_records(records, cursor, source_path, submit)`: the ONE record->turn loop. Per record:
  model_hint -> cursor.model; build TurnContext(seq=cursor.seq, parent_id=cursor.parent_id, model);
  `turn = adapter.normalize(record, ctx)`; **`cursor.seq += 1`**; `if turn is not None: submit(build_transcript_job(turn, binding)); cursor.parent_id = turn.turn_id`.
  -> Currently DROPS None (meta) records. MUTATES cursor in place (seq always; parent_id/model on turns).
- `_poll_cursor(cursor)`: (1) stat guard skip-unchanged; (2) read from byte_offset; (3) iter_complete_records;
  (4) tee `data[:consumed]` to tier-1 snapshot BEFORE normalize (idempotent by file size); (5) ingest_records
  (fire-and-forget submit to SQLite queue); (6) `cursor.byte_offset += consumed`; (7) `cursor.stat_signature = signature` LAST.
  Both byte_offset + stat advance ONLY after the whole poll succeeds (a mid-poll raise leaves both, next poll re-reads).
- `stop(drain=True)`: _stop.set(); thread.join(); if drain: self.poll(). Called BEFORE writer.stop (close order).
- Loop seam today: `IndexWriter` captures loop via EXPLICIT `loop` param (NOT get_running_loop); `submit`=queue.put_nowait (fire-and-forget, overflow drops+dirty); commit = BEGIN IMMEDIATE -> per-job SAVEPOINT -> COMMIT -> `_emit_events` -> `loop.call_soon_threadsafe(emit, job.event)` (live emit AFTER commit). start=daemon thread; stop=sentinel+join+flush.

`index/rebuild.py`:
- `_replay_transcript(writer, layout, owned, slug, workspace_hash, started_at)` (250-294): TRANSCRIPT-ONLY core to extract. Reads OwnedSessionFacts; session_id = native if minted else `synth_session_id(run_id, provider, native)`; decode descriptor -> source_path + home_dir; reads `layout.transcript_snapshot_path(session_id).read_bytes()`; `iter_complete_records`; builds SessionBinding+TailCursor; `ingest_records(records, cursor, source.path, writer.submit)`. NO wire calls.
- `replay_run(writer, run_dir)` (71-101): WIRE-FIRST (90-96: `_read_exchange` -> `bind_exchange` -> `build_wire_job` -> submit) THEN transcript (99-101). The new backfill must NOT reuse this.
- `backfill(writer, workspaces_root, run_id=None)` (107-111): iter_run_dirs -> replay_run per run.
- Wire-touching (EXCLUDE from transcript-only backfill): `replay_run`, `_read_exchange`, `build_wire_job`, `_write_wire`.

`storage/session_facts.py`: `read_run_session_facts(storage_root) -> RunSessionFacts | None` (reads sessions.json); `OwnedSessionFacts` fields = run_id, cli, native_session_id, minted, source_descriptor, home_dir.

## Slice-2 hunt (orchestrator's checks + my sharp edges)

1. DURABLE-COMMIT SEAM (top): new `_poll_cursor` builds a batch + `submit_blocking(batch) -> CommitResult`; advance byte_offset + stat_signature ONLY after `CommitResult.ok`. On timeout/error: leave cursor un-advanced, log/mark dirty, next poll re-reads + re-submits. `_commit_batch` = ONE `conn.transaction()` for the whole poll (session upsert + all events + artifacts + pg_notify), NOT per-event savepoints (per-batch atomicity -> clean re-read). [lesson_durable_store_needs_commit_ack_seam, lesson_per_job_savepoint_not_batch_atomic]
2. **CURSOR ROLLBACK ON FAILURE (my #1 adversarial find):** ingest_records MUTATES cursor.seq/parent_id/model in place. If the batch-build advances the cursor and the commit FAILS while byte_offset stays, the re-poll re-reads the same bytes but cursor.seq is already advanced -> the same record gets a DIFFERENT (session_id, seq) on retry -> duplicate rows or seq gap. The §3.2 "re-submit is safe, deterministic" claim REQUIRES cursor state be deterministic from byte_offset. VERIFY: either (a) cursor seq/parent_id/model are snapshotted pre-batch and RESTORED on commit failure, or (b) the batch is built into a local copy and the cursor is only mutated after CommitResult.ok. If neither -> BLOCKER (skipped/duplicated bytes on any commit hiccup). Test it: force a commit failure, re-poll, assert seq continuity + no dup rows.
3. TEE/ADVANCE GATING: snapshot tee stays idempotent (re-tee harmless) AND byte_offset must not advance on commit failure. A "can't keep up"/timeout branch must NOT log+return success (that advances past un-persisted) — it must leave the cursor un-advanced (effectively raise/no-advance). [lesson_tee_advance_gate_and_degraded_branch]
4. THREAD-SAFETY: submit_blocking from tailer thread -> `run_coroutine_threadsafe(self._commit_batch(batch), self._loop).result(timeout=commit_timeout_s)`; loop captured at start (explicit, like IndexWriter), not get_running_loop in the thread. Backpressure = submit_blocking blocks the tailer thread. Shutdown order: stop tailer (drain poll commits synchronously) THEN close writer+pool. Timeout/cancellation handled.
5. NOTIFY tied to durability: `pg_notify` enqueued INSIDE the txn (delivered only on commit). [lesson_emit_only_at_terminal_not_provisional_seam]
6. IDEMPOTENCY: event upsert ON CONFLICT (session_id, seq) DO UPDATE (slice-1 `_INSERT_EVENT_SQL`); re-submit deterministic GIVEN cursor rollback (see #2).
7. META NOT DROPPED: new ingest submits EVERY record (turn->kind='turn'+ir; None->kind='meta', raw only). Meta advances seq + may set model, NOT parent_id. Verify (codex session_meta/turn_context land as meta; model continuity preserved).
8. REPLAY CORE TRANSCRIPT-ONLY: `session/backfill.py:replay_transcript_run(writer, run_dir)` reuses `_replay_transcript` logic (sessions.json + snapshot bytes), reuses `iter_complete_records`, NO `_read_exchange`/`bind_exchange`/`build_wire_job`, NO index.jsonl wire read. grep the new backfill for wire imports.
9. DRY: ingest_records generalized via injected `build_event` callback, REUSED by live-tail + backfill (no parallel record->turn loop, no second iter_complete_records in session/). build_transcript_job retired at live path. Verify SQLite callers (rebuild.replay_run/_replay_transcript) still compile (build_event default = build_transcript_job, or they pass it) since index/* stays intact this slice.
10. INDEX/* INTACT: SQLite modules (db/schema/writer/ingest/queries/blocks/models/maintenance/rebuild) NOT deleted. tailer/adapters/sessions MAY be modified (retargeted). Verify the SQLite path's tests still pass (or are adapted) — the "left intact" + "retarget the shared tailer" tension.
11. DAG: tailer stays sink-agnostic (Callable injection); NO `index -> session` import (SessionWriter built + injected at load_runtime). session -> storage read helpers OK (forward). storage never imports session. No cross-module `_` import. LOC<700/fn<150.
12. `cd api && just ci` GREEN vs PG (55432), NO skips. Plus a forced-commit-failure test for #2/#3.

Append findings to review-slice-2.md. COMMS: reply ONLY to orchestrator; "grounded" then "done: review-slice-2.md". Never message engineer.
