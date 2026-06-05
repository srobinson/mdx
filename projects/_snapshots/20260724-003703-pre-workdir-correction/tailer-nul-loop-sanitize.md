# Tailer NUL loop sanitize investigation

## Summary

Confirmed root cause: decoded NUL characters can reach the event insert as plain `text` parameters and as nested strings inside `jsonb` parameters. Postgres rejects both before the event row is persisted. The tailer then retries the same batch because cursor advancement happens only after the submit path succeeds.

Chosen chokepoint: `api/src/transport_matters/session/dao_rows.py:event_params`.

## Failure path

The source note names `SessionAsyncDao`; the live code symbol is `AsyncSessionDao`.

Confirmed path from the run log and code symbols:

1. `api/src/transport_matters/index/tailer.py:TranscriptTailer.poll` calls `TranscriptTailer._poll_cursor` and logs any exception as `tailer poll failed`.
2. `api/src/transport_matters/index/tailer.py:TranscriptTailer._poll_cursor` reads the file tail, parses complete records, snapshots consumed bytes, calls `ingest_records`, then advances cursor state only after the whole poll succeeds.
3. `api/src/transport_matters/index/tailer.py:ingest_records` normalizes records, builds event writes through the injected `build_record`, then calls the injected `submit_batch`.
4. `api/src/transport_matters/addon_runtime.py:load_capture_runtime.submit_events` builds an `EventBatch` and calls `SessionWriter.submit_blocking`.
5. `api/src/transport_matters/session/writer.py:SessionWriter.submit_blocking` schedules `SessionWriter._commit_batch` on the writer loop and waits for the result.
6. `api/src/transport_matters/session/writer.py:SessionWriter._commit_batch` upserts the session, then calls `AsyncSessionDao.insert_event` for each event.
7. `api/src/transport_matters/session/async_dao.py:AsyncSessionDao.insert_event` executes `INSERT_EVENT_SQL` with `event_params(event)`.
8. `api/src/transport_matters/session/dao_rows.py:event_params` dumps scalar event fields, wraps `raw` with `Jsonb(event.raw)`, wraps `ir` through `jsonb(event.ir)`, then returns the parameter map to psycopg.

The run log confirms the same path ended at psycopg with `PostgreSQL text fields cannot contain NUL (0x00) bytes`.

## Event insert fields with text or jsonb risk

Schema source: `api/migrations/versions/0001_session_store_foundation.py:event table`.

Bind source: `api/src/transport_matters/session/dao_statements.py:INSERT_EVENT_SQL` plus `api/src/transport_matters/session/dao_rows.py:event_params`.

| Column | Type | Bound value | NUL risk |
| --- | --- | --- | --- |
| `session_id` | `text` | `EventRow.session_id` | Low expected risk, generated from binding, but still a Python string accepted by the DAO. |
| `kind` | `text` | `EventRow.kind` | Low expected risk, controlled enum. |
| `native_turn_id` | `text` | `EventRow.native_turn_id` from `NormalizedTurn.turn_id` or `_record_id` | Can carry decoded NUL if provider transcript ids are poisoned. |
| `parent_native_id` | `text` | `EventRow.parent_native_id` from `NormalizedTurn.parent_id` | Can carry decoded NUL if provider transcript parent ids are poisoned. |
| `run_id` | `text` | `EventRow.run_id` | Low expected risk, generated from binding. |
| `provider` | `text` | `EventRow.provider` | Low expected risk, controlled adapter value. |
| `cli` | `text` | `EventRow.cli` | Low expected risk, controlled adapter or binding value. |
| `role` | `text` | `EventRow.role` from the normalized turn | Can carry decoded NUL if provider transcript role strings are poisoned. |
| `model` | `text` | `EventRow.model` from transcript message or cursor model hint | Can carry decoded NUL if provider transcript model strings are poisoned. |
| `raw` | `jsonb` | `Jsonb(event.raw)` | Definite risk. Raw records are decoded transcript JSON. Nested strings can contain decoded NUL. The observed poison had decoded NUL in Claude tool output related fields. |
| `ir` | `jsonb` | `jsonb(event.ir)` | Definite risk. Normalized IR comes from `NormalizedTurn.model_dump(mode="json")`; nested strings in `TextBlock`, `ThinkingBlock`, `ToolUseBlock.input`, `ToolResultBlock.content`, `UnknownBlock.raw`, and provider data can carry decoded NUL. |
| `source_path` | `text` | `EventRow.source_path` | Low expected risk, generated local path, but still a Python string accepted by the DAO. |
| `search_text` | `text` | `_search_text(turn.parts)` | Definite risk. Direct text and tool result text are concatenated without NUL handling. Claude tool stdout can enter here through `ToolResultBlock` text content. |

Non text columns bound at the same insert are `seq`, `parent_seq`, `is_sidechain`, `ts`, and `source_line`. They are not NUL string carriers.

`content_tsv` is not directly bound. It is generated from `search_text`, so the oversized search text failure class belongs to a separate search text budget fix, not the NUL sanitization chokepoint.

## Tool stdout location

Tool stdout is not a standalone column. It can appear in all three unsafe event payload locations:

1. `raw` jsonb via the decoded raw transcript record.
2. `ir` jsonb after adapter normalization into content blocks.
3. `search_text` text when `_search_text` walks normalized parts and appends direct text from tool results.

Relevant symbols:

- `api/src/transport_matters/index/adapters/claude.py:ClaudeAdapter.normalize`
- `api/src/transport_matters/index/adapters/claude.py:_content_to_parts`
- `api/src/transport_matters/index/adapters/claude.py:_tool_result_content`
- `api/src/transport_matters/session/ingest.py:build_event`
- `api/src/transport_matters/session/ingest.py:_turn_ir`
- `api/src/transport_matters/session/ingest.py:_search_text`
- `api/src/transport_matters/session/ingest.py:_append_search_text`

## Chosen DRY boundary

Use `api/src/transport_matters/session/dao_rows.py:event_params`.

The sanitizer belongs at the DAO bind boundary, before `Jsonb` adaptation and before returning scalar text params to psycopg. It should recursively replace or strip `\x00` in strings, dictionaries, lists, and tuples, then return values with the same JSON compatible shape.

Why this one site suffices for event inserts:

- `event_params` is the single event parameter assembly function used by `api/src/transport_matters/session/async_dao.py:AsyncSessionDao.insert_event`.
- `event_params` is also used by `api/src/transport_matters/session/dao.py:SessionDao.insert_event`, so the same fix covers async runtime writes and sync DAO callers.
- It sees every text and jsonb event insert value in one map, including `raw`, `ir`, and `search_text`.
- It runs immediately before psycopg adaptation, the exact point where Postgres unsafe values become bind parameters.

Why not IR normalization:

- Raw event JSON is intentionally preserved separately from normalized IR and can fail even when the normalized turn is absent.
- Meta events call `_meta_event` with `ir=None`, but still bind `raw` jsonb.
- Adapter level fixes would duplicate logic across Claude, Codex, and future transcript adapters.
- Search text is built after normalization, so IR only sanitization would miss scalar `search_text` unless another fix were added.

Why not only `AsyncSessionDao.insert_event`:

- It would miss `SessionDao.insert_event` because both DAOs share `event_params`.
- The correct DRY seam is the shared parameter adapter, not one DAO method.

## Existing helper search

No reusable Python backend helper was found for recursive NUL or control character sanitization of Postgres text and jsonb payloads.

Searches covered FMM symbol lookup and `rg` patterns for `NUL`, `0x00`, `\\x00`, `\\u0000`, `control char`, `sanitize`, and `escape` under the API and migration tree.

Unrelated findings:

- `www/src/session-canvas/viewers/terminal/pasteRegistry.ts:escapeDropLocator` strips control characters from a frontend PTY drop locator. It is TypeScript UI code and not a backend reuse target.
- `api/src/transport_matters/cli/_helpers.py:_plain` strips ANSI SGR escapes for test assertions. It is not NUL or JSON sanitization.

Reuse target: none.

## Plain text and jsonb confirmation

Confirmed.

Read only psycopg probes against local Postgres showed:

- Plain text bind with a Python string containing `\x00` fails with `psycopg.DataError: PostgreSQL text fields cannot contain NUL (0x00) bytes`.
- Jsonb bind with `Jsonb({"x": "a\x00b"})` fails with `psycopg.errors.UntranslatableCharacter: unsupported Unicode escape sequence`.

The note's claim is therefore correct: plain `text` params and nested `jsonb` strings are both unsafe unless sanitized before adaptation.

## Verification performed

- Used FMM structure tools before source inspection.
- Read the investigation note at `NOTES/transcript-tailer-nul-byte-loop.md`.
- Confirmed the failure stack in the run log.
- Confirmed the code path through the tailer, writer, DAO, and parameter adapter symbols listed above.
- Confirmed text and jsonb NUL rejection with read only psycopg `SELECT` probes.

## Final repo status

Final `git status --short` was clean. I introduced no working tree delta in the repository. The earlier `M TLDR.md` delta was no longer present by the end of the investigation.
