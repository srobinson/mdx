---
title: Activity transcript source scout for Transport Matters
type: research
tags: [transport-matters, activity, transcript, harness-support, architecture]
summary: Activity should fan out from the Session tailing commit seam using raw plus IR transcript records, while harness bundle support needs consolidation.
status: active
source: codebase-analyst
confidence: high
created: 2026-07-03
updated: 2026-07-03
---

## Executive Summary

Activity round 2 confirms the amended design: status should derive from transcript and runtime lifecycle, not wire facts or breakpoint seams. The cleanest implementation is an isolated RecordSource fan out beside `SessionWriter`, with Activity consuming `EventWrite` raw plus IR records because important lifecycle metadata is not preserved in `NormalizedTurn` alone.

## Project Metadata

- Language: Python backend, TypeScript frontends.
- Backend framework: FastAPI with process resident run management and a Postgres backed session store.
- Transcript infrastructure: `api/src/transport_matters/index/tailer.py` plus `api/src/transport_matters/session/writer.py`.
- Harnesses: Claude Code and Codex.
- Build topology: `api/`, `www/`, `desktop/`; repo is fmm indexed.

## Architecture

The current tail path is:

1. `TranscriptTailer._poll_cursor` reads complete JSONL records.
2. `_plan_ingest_records` combines each raw record with `TranscriptAdapter.normalize` and provenance.
3. `_start_session_capture.submit_events` builds an `EventBatch`.
4. `ShardedCommitDispatcher.submit` schedules `SessionWriter.submit`.
5. `SessionWriter._commit_batch` writes session and event rows, then sends Postgres notify.

The Activity seam belongs at step 3. This is late enough that raw, normalized, provenance, session, run, workspace, harness, and source metadata all exist, but early enough to stay out of Postgres read paths. The Activity queue must be independent and nonblocking so session commit futures and cursor advancement remain governed only by the existing writer contract.

## Key Patterns

- `api/src/transport_matters/session/ingest.py` `build_event` preserves raw records for both TURN and META events. This is the right source for Activity because raw Codex `event_msg` records carry task lifecycle and token counts.
- `api/src/transport_matters/index/adapters/codex.py` `CodexAdapter.normalize` intentionally skips `event_msg` and `turn_context` as normalized turns. Activity must not depend only on `NormalizedTurn`.
- `api/src/transport_matters/storage/transcript_snapshot.py` `make_transcript_snapshot_writer` provides byte faithful owned transcript copies and is shared by detached and canvas capture paths once cursors are registered.

## Detailed Findings

### RecordSource fan out

Use `api/src/transport_matters/addon_runtime.py` `_start_session_capture`, specifically the nested `submit_events` function, as the fan out point. Do not add Activity to `ShardedCommitDispatcher`; that class owns sharded commit queueing for `SessionWriter` and should remain Session specific. Do not fan out inside `TranscriptTailer._poll_cursor`; any callback exception there can quarantine a window or stop cursor advancement.

### Transcript metadata coverage

Claude sample: `/Users/alphab/.claude/projects/-Users-alphab-Dev-LLM-DEV-helioy-transport-matters/3fc7b26a-5242-436b-a71d-cbffb481cd1c.jsonl`.

- Turn open: record type `user`, `message.role`.
- Tool pending: record type `assistant`, content block `tool_use`, pending until record type `user`, content block `tool_result` with matching `tool_use_id`.
- Turn ended: record type `assistant`, `message.stop_reason` `end_turn`; record type `system`, subtype `turn_duration` also exists.
- Question ask: record type `assistant`, content block `tool_use`, name `AskUserQuestion`.
- Error: record type `user`, content block `tool_result`, field `is_error`.
- Usage: `assistant.message.usage` includes `input_tokens`, `cache_creation_input_tokens`, `cache_read_input_tokens`, and `output_tokens`.

Codex samples: `/Users/alphab/.codex/sessions/2026/07/03/rollout-2026-07-03T12-05-17-019f265d-ecf3-7be2-9ecd-d2fa9e298cb4.jsonl`, `/Users/alphab/.codex/sessions/2026/04/21/rollout-2026-04-21T10-58-00-019dae30-175b-76d3-b7a9-41dd6b90c828.jsonl`, and `/Users/alphab/.codex/sessions/2026/07/03/rollout-2026-07-03T01-39-16-019f2420-cbf8-7353-ab7c-69961c598995.jsonl`.

- Turn open: record type `event_msg`, payload type `task_started`.
- Tool pending: record type `response_item`, payload type `function_call`, pending until payload type `function_call_output`.
- Turn ended: record type `event_msg`, payload type `task_complete`.
- Question ask: record type `response_item`, payload type `function_call`, name `request_user_input`.
- Error: record type `event_msg`, payload type `turn_aborted`, field `reason`.
- Usage: record type `event_msg`, payload type `token_count`, `info.last_token_usage` and `info.total_token_usage` include `input_tokens`, `cached_input_tokens`, `output_tokens`, `reasoning_output_tokens`, and `total_tokens`.

### Detached liveness

Detached capture uses `load_capture_runtime`, `_start_session_capture`, `_register_owned_cursor`, and `make_transcript_snapshot_writer`. Canvas shared capture uses `load_shared_capture_runtime`, `SharedProxyCore.register_binding`, `SharedTranscriptSnapshotWriter`, and the same `register_owned_cursor` plus `TranscriptTailer._poll_cursor`. Poll freshness is equivalent after registration, but failure semantics differ: detached registration errors are logged, while shared canvas registration can fail binding through `SharedProxyControlError`.

### Harness bundle mapping

`api/src/transport_matters/harnesses/__init__.py` is a launch descriptor registry, not a full harness bundle. `api/src/transport_matters/adapters/` is a provider wire adapter registry. Transcript adapters live in `api/src/transport_matters/index/adapters/`, which is live but misnamed. The standard bundle still needs settings adapters, mapping tables with version ranges, capability flags for transcript features, fixtures, unknown record counters, and a conformance kit.

## Dependencies

- `pydantic` models the current harness descriptors, session events, and normalized transcript records.
- `psycopg` and Postgres notify back the session store and live session streams.
- fmm confirmed the live dependency surface for `index/tailer.py`, `index/commit_dispatcher.py`, `session/writer.py`, `harnesses/`, and `adapters/`.

## Relevance to Helioy

This scout preserves the product correction that Canvas Activity is transcript semantic state, while Inspector remains the wire product. It also sharpens the Harness Support Standard by identifying which existing code is seed material and which pieces are still missing.

## Open Questions

1. Should RecordSource publish existing `EventWrite` objects or a narrower Activity DTO?
2. How should Codex context tokens be computed when only `cached_input_tokens` is available?
3. Should tool result errors immediately drive `stalled`, or annotate tool state until turn completion?
4. Should detached cursor registration failure surface in doctor, UI, or launch failure?
5. Should `harnesses/` become the canonical bundle package, or should a new bundle package absorb current harness, wire, and transcript adapters?
