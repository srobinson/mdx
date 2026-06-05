# Tailer NUL loop, search budget, and bounded retry findings

Date: 2026-06-14
Mode: read only investigation. Findings file is outside the repository.

## Inputs checked

- Required note: `NOTES/transcript-tailer-nul-byte-loop.md`.
- fmm index: `.fmm.db` present, `fmm validate` reported all 747 indexed files up to date.
- Repository state before investigation: `git status --short` returned no tracked changes.

## 1. `search_text` composition and schema

`search_text` is composed in `api/src/transport_matters/session/ingest.py`:

- `build_event` creates the `EventRow` for a normalized turn and sets `search_text=_search_text(turn.parts)` at `api/src/transport_matters/session/ingest.py:74-101`, specifically lines 94 to 99. The same event also carries `raw=dict(record)` and `ir=ir`, so the full transcript record and normalized IR remain separate from the search projection.
- `_search_text` collects chunks from every normalized content part and returns `"\n".join(chunks) or None` with no byte or character budget at `api/src/transport_matters/session/ingest.py:203-208`.
- `_append_search_text` appends `TextBlock` and `ThinkingBlock` text, `ToolUseBlock` name and JSON encoded input, recursively descends `ToolResultBlock.content`, and JSON encodes `UnknownBlock.raw` at `api/src/transport_matters/session/ingest.py:211-223`. This is the unbounded source of the oversized `search_text` class.
- `_turn_ir` extracts inline artifacts and redacts artifact carrying parts in the persisted IR at `api/src/transport_matters/session/ingest.py:125-144`, so large non text payloads already have an artifact path available.

The insert path keeps the same value through to Postgres:

- `event_params` dumps the `EventRow` and wraps `raw` and `ir` as JSONB at `api/src/transport_matters/session/dao_rows.py:74-79`.
- `AsyncSessionDao.insert_event` executes `INSERT_EVENT_SQL` with those parameters at `api/src/transport_matters/session/async_dao.py:111-115`.
- `INSERT_EVENT_SQL` inserts and updates `search_text` directly at `api/src/transport_matters/session/dao_statements.py:119-148`.

The schema is defined in `api/migrations/versions/0001_session_store_foundation.py:upgrade`:

- The `event` table has `search_text text` and `content_tsv tsvector GENERATED ALWAYS AS (to_tsvector('english', coalesce(search_text, ''))) STORED` at `api/migrations/versions/0001_session_store_foundation.py:58-80`.
- The generated column is indexed by `event_fts_gin` at `api/migrations/versions/0001_session_store_foundation.py:86-88`.

This confirms the note's second failure class: the raw `search_text` value can be acceptable as text while the generated `content_tsv` fails the Postgres tsvector limit of 1,048,575 bytes.

## 2. Search text budget boundary

The primary size budget belongs in `api/src/transport_matters/session/ingest.py:_search_text`, with the resulting `EventRow.search_text` already capped before `build_event` hands the event to the DAO.

Boundary rationale:

- `search_text` is a full text index projection. It should be small, bounded, and lossy when needed.
- The canonical payload stays outside the full text projection: `build_event` persists `raw=dict(record)` and `_turn_ir` persists normalized IR plus artifact references at `api/src/transport_matters/session/ingest.py:94-99` and `api/src/transport_matters/session/ingest.py:125-144`.
- Capping in `_search_text` applies to the shared live tailer build path and any replay or backfill code path that uses `build_event`.
- The cap should be byte aware and comfortably below 1,048,575 bytes, because the tsvector size is not a one to one copy of input text.
- A small DAO side guard in `api/src/transport_matters/session/dao_rows.py:event_params` would be useful defense in depth for tests or future direct `EventRow` callers, but the semantic budget belongs where the search projection is produced, not in the SQL statement or the tailer loop.

Recommended boundary shape:

- Add a named constant such as `SEARCH_TEXT_MAX_BYTES` near `_search_text`.
- Accumulate chunks through a bounded helper that truncates on UTF 8 byte length and appends a marker.
- Keep full raw, IR, and artifacts intact. Only `search_text` is truncated.

## 3. Tailer retry loop, cursor advance, and quarantine point

The failed batch does not advance the cursor. It retries the same unread segment forever.

Trace:

- `load_capture_runtime` creates the `TranscriptTailer` with `submit_events`, which calls `writer.submit_blocking(build_event_batch(...))`, then starts the tailer at `api/src/transport_matters/addon_runtime.py:183-193`.
- `TranscriptTailer._run` calls `poll()` every `_DEFAULT_FILE_INTERVAL_S` until stopped at `api/src/transport_matters/index/tailer.py:210-212`. The default interval is 0.25 seconds at `api/src/transport_matters/index/tailer.py:46`.
- `TranscriptTailer.poll` catches every exception from `_poll_cursor` and only logs `tailer poll failed for session ...` at `api/src/transport_matters/index/tailer.py:202-208`.
- `_poll_cursor` reads from `cursor.byte_offset`, parses complete records, snapshots consumed bytes, calls `ingest_records`, then advances `cursor.byte_offset` and `cursor.stat_signature` only after that whole path succeeds at `api/src/transport_matters/index/tailer.py:233-267`.
- `ingest_records` copies `cursor.seq`, `cursor.source_line`, parent state, and model into locals, builds writes, calls `submit_batch` at line 143, then copies the new cursor state back only after `submit_batch` returns at `api/src/transport_matters/index/tailer.py:111-148`.
- `SessionWriter.submit_blocking` re raises commit failures from the future result at `api/src/transport_matters/session/writer.py:50-63`.
- `SessionWriter._commit_batch` runs all event inserts in one transaction and has no catch around `AsyncSessionDao.insert_event` at `api/src/transport_matters/session/writer.py:70-94`.
- `AsyncSessionDao.insert_event` directly executes the insert at `api/src/transport_matters/session/async_dao.py:111-115`.

Cursor persistence location:

- There is no durable tailer cursor persistence. The cursor is the in memory `TailCursor` registered by `TranscriptTailer.register` at `api/src/transport_matters/index/tailer.py:175-178`.
- The in memory logical cursor is persisted back to the `TailCursor` object at `api/src/transport_matters/index/tailer.py:144-148`.
- The byte cursor and stat skip signature are persisted back to the same object at `api/src/transport_matters/index/tailer.py:264-267`.

Existing tests confirm this behavior:

- `test_cursor_state_advances_only_after_submit_success` asserts that a first `submit_batch` failure leaves `byte_offset`, `seq`, parent state, and `stat_signature` unchanged, then a second poll retries and succeeds at `api/src/transport_matters/index/test_tailer.py:245-277`.
- The snapshot failure test asserts that an unchanged file is retried because `byte_offset` and `stat_signature` remain unchanged at `api/src/transport_matters/index/test_tailer.py:338-360`.

Bounded failure, poison quarantine, and dead letter advance should be added in `api/src/transport_matters/index/tailer.py:TranscriptTailer._poll_cursor`, around the `ingest_records(...)` call at lines 256 to 262.

Why that seam:

- `_poll_cursor` has the file source, current byte offset, consumed byte count, parsed records, binding, run id, native session id, and current logical `source_line` through the cursor.
- `poll()` is too late because it only sees an exception and then loops.
- `SessionWriter._commit_batch` is too low because it sees a database batch, not the source byte window or tailer cursor.
- `ingest_records` knows logical source lines, but it intentionally keeps cursor state local until submit succeeds. It does not know the consumed byte window.

Implementation implication:

- Extend the record iteration seam to retain per record byte spans or add a companion helper in `_poll_cursor`, since `iter_complete_records` currently returns only `(records, consumed)` at `api/src/transport_matters/index/tailer.py:49-69`.
- On repeated failure, isolate the poison record, write a bounded dead letter or quarantine record keyed by run id, session id, native session id, source path, source line, and byte span, then advance past that quarantined record so one bad record cannot spin or grow logs without bound.
- Advance only after the quarantine write succeeds. If quarantine persistence fails, keep retry semantics to preserve data safety, but rate limit logs.

## 4. Tailer health visibility hook

The obvious producer hook is `api/src/transport_matters/index/tailer.py:TranscriptTailer.poll` and `TranscriptTailer._poll_cursor`:

- `poll` has the per cursor exception boundary at `api/src/transport_matters/index/tailer.py:202-208`.
- `_poll_cursor` has the successful progress boundary and cursor state at `api/src/transport_matters/index/tailer.py:218-267`.
- `TailCursor.binding` carries `session_id`, `run_id`, and `native_session_id`; `TailCursor` carries `source_line` and `byte_offset` at `api/src/transport_matters/index/tailer.py:72-91`.

The obvious API exposure points are:

- Captured run list: add health fields to `ManagedRunView`, `ManagedRun.view`, `RunViewModel`, and `run_view_model`, then expose them through `GET /api/runs` in `api/src/transport_matters/run_manager.py:137-209` and `api/src/transport_matters/api/v1/run_routes.py:78-105` plus `api/src/transport_matters/api/v1/run_routes.py:234-299`. This is the best per run surface because `RunViewModel` already includes `runId` and `nativeSessionId`.
- Session list: if health is persisted in the session store, add fields to `SessionSummary` and `list_sessions` in `api/src/transport_matters/api/v1/session_routes.py:50-75` and `api/src/transport_matters/api/v1/session_routes.py:127-149`. This is the best per native session history surface.
- `/health` in `api/src/transport_matters/main.py:create_app` at `api/src/transport_matters/main.py:198-200` is only aggregate readiness today and is not sufficient for per run or per native session diagnosis.
