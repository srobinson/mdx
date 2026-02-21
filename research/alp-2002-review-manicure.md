---
title: ALP 2002 Review for Manicure Track Manager
type: research
tags: [manicure, review, alp-2002, backend, track-manager, subagent-tracks]
summary: ALP 2002 track manager is accepted after Codex spawn cleanup, fan out, closure, nesting, migration, and reference trace coverage were verified.
status: active
source: codebase-analyst
confidence: high
created: 2026-04-25
updated: 2026-04-25
---

## Executive Summary

Reviewed ALP 2002 through commits `0bb2fa5`, `10b20f1`, and `6202ac5` on branch `nancy/ALP-1847`. Initial review found fan out and closure lifecycle bugs; both were fixed with regression coverage. Final status: `LGTM ALP-2002` sent to the backend engineer with CC to `helioy:general:0:1.2`.

## Project Metadata

- Project: manicure
- Area: `api` Python backend
- Worktree: `/Users/alphab/Dev/LLM/DEV/helioy/manicure-worktrees/nancy-ALP-1847`
- Branch verified: `nancy/ALP-1847`
- Commits reviewed: `0bb2fa5`, `10b20f1`, `6202ac5`
- Test runner: pytest via `uv run pytest`
- Formatter and lint: Ruff
- Type checker: mypy

## Architecture

ALP 2002 introduces a process local, I/O free state machine in `api/src/manicure/track_manager.py`.

Key structures:

- `TrackAssignment` at `api/src/manicure/track_manager.py:14-19` is the persisted classification result.
- `TrackRecord` at `api/src/manicure/track_manager.py:28-35` holds track id, parent id, display name, role, status, and request signature.
- `PendingSpawn` at `api/src/manicure/track_manager.py:38-44` holds unresolved spawn metadata.
- `TrackManager.record_exchange` at `api/src/manicure/track_manager.py:65-77` resolves tool results, assigns the request, observes its signature, then scans the response for spawned children or closure tools.

Persistence and ingest wiring:

- `IndexEntry` includes `track_id`, `parent_track_id`, `track_display_name`, and `track_role` at `api/src/manicure/storage/base.py:116-119`.
- `IndexEntry.default_root_track` at `api/src/manicure/storage/base.py:121-129` defaults legacy rows to the root track.
- HTTP ingest calls `_assign_track` before persisting and emitting SSE at `api/src/manicure/exchange_recorder.py:176-220`.
- Codex provisional and final ingest paths pass assignment fields into stored entries and SSE payloads.

## Detailed Findings

### Accepted: reference trace classification

`api/src/manicure/test_track_manager.py` validates both supplied reference traces:

- Claude trace test at `api/src/manicure/test_track_manager.py:95-127` verifies 3 parent turns and 5 subagent turns, with the subagent track closed.
- Codex trace test at `api/src/manicure/test_track_manager.py:130-158` verifies the `Lagrange` subagent keyed by `019dc432-c4bc-75d2-a8e5-be095061139d`, with closure through `wait_agent`.

### Accepted: fan out isolation

The initial implementation assigned same signature child requests to the same track. Commit `10b20f1` fixed this by claiming unassigned subagent tracks before signature matching in `TrackManager._assign_request` at `api/src/manicure/track_manager.py:263-284`.

Regression coverage is in `test_anthropic_fan_out_keeps_two_concurrent_subagent_tracks_open` at `api/src/manicure/test_track_manager.py:161-189`, where both child first requests use `tools_count=90`.

### Accepted: closure handling

`test_codex_agent_kill_closes_targeted_subagent_track` at `api/src/manicure/test_track_manager.py:192-239` verifies direct `agent_kill` closure.

The second review found successful Codex spawns were not retired from `open_spawns`, so stale spawn tool results could reopen a closed track. Commit `6202ac5` fixed this by popping the pending spawn after successful Codex `agent_id` resolution at `api/src/manicure/track_manager.py:197-219`.

Regression coverage is in `test_codex_resolved_spawn_result_does_not_reopen_closed_track` at `api/src/manicure/test_track_manager.py:242-290`.

### Accepted: nesting, failed spawn, and migration safety

- Nesting coverage: `test_nested_subagent_track_records_parent_track_id` at `api/src/manicure/test_track_manager.py:293-330`.
- Failed Codex spawn coverage: `test_codex_failed_spawn_result_does_not_open_track` at `api/src/manicure/test_track_manager.py:333-364`.
- Legacy index default coverage: `api/src/manicure/storage/test_disk.py` includes a legacy row defaulting to the root track.

## Verification

Ran locally from `api`:

```bash
uv run pytest src/manicure/test_track_manager.py
uv run ruff check src/manicure/track_manager.py src/manicure/test_track_manager.py
uv run mypy src/manicure/track_manager.py
uv run ruff format --check src/manicure/track_manager.py src/manicure/test_track_manager.py
uv run pytest
```

Results:

- Track manager tests: 7 passed
- Ruff check on touched files: passed
- mypy on `track_manager.py`: passed
- Ruff format check on touched files: passed
- Full API test suite: 688 passed

## Dependencies

Critical internal dependencies:

- `manicure.ir` provides `InternalRequest`, `InternalResponse`, `ToolUseBlock`, and `ToolResultBlock` shapes consumed by the pure state machine.
- `manicure.storage.base.IndexEntry` is the persistence boundary for track metadata.
- `manicure.exchange_recorder` and `manicure.codex.exchange` are the ingest callers.

## Relevance to Helioy

ALP 2002 is the base layer for ALP 2003 override isolation and ALP 2004 tree rendering. With fan out, nesting, closure, failed spawn, and legacy defaults verified, downstream override scoping and UI tree grouping have stable track metadata to build on.

## Open Questions

None for ALP 2002. Await ALP 2003 review handoff.
