---
title: CI Track Manager Hermetic Test Fix in Manicure
type: research
tags: [manicure, ci, tests, track-manager, github-actions]
summary: Backend CI failed because two track manager tests depended on Stuart local ~/.manicure captures instead of repository owned fixtures.
status: active
source: codebase-analyst
confidence: high
created: 2026-04-26
updated: 2026-04-26
---

## Executive Summary

GitHub Actions job `73069005652` failed in `backend · test (3.12)` because two `test_track_manager.py` tests read absolute paths under `/home/runner/.manicure/workspaces/...`. Those paths exist on Stuart local machine, which hid the problem locally, but do not exist in CI.

## Project Metadata

- Project: `manicure`
- Area: Python API tests
- CI job: GitHub Actions `backend · test (3.12)`
- Local branch: `nancy/ALP-1847`
- Fix commit: `383ee03 fix(api): make track manager tests hermetic`

## Architecture

`TrackManager` is intentionally process local and I/O free. It classifies exchanges by ingest order from `InternalRequest` and `InternalResponse` objects, then returns `TrackAssignment` records for parent and subagent tracks.

Relevant files:

- `api/src/manicure/track_manager.py`: core track classification logic
- `api/src/manicure/test_track_manager.py`: parent, subagent, continuation, wait, kill, and close tests

## Detailed Findings

### Failure

The CI log showed:

- `FileNotFoundError: /home/runner/.manicure/workspaces/llm-dev-helioy/a9915b95`
- `FileNotFoundError: /home/runner/.manicure/workspaces/dev-helioy-manicure/660bc067`

Both failures came from `api/src/manicure/test_track_manager.py` when `_run_trace` iterated `Path.home() / ".manicure/..."`.

### Root Cause

The tests depended on local runtime capture directories outside the repository. This made the suite non hermetic and environment dependent.

### Fix

`api/src/manicure/test_track_manager.py` now builds inline synthetic traces using existing IR helpers:

- Anthropic trace covers `Agent` spawn, subagent requests, tool result continuation, and close.
- Codex trace covers `spawn_agent`, spawn result with `agent_id`, subagent metadata routing, `wait_agent`, and close.
- `_run_trace` now accepts `(exchange_id, request, response)` tuples and no longer reads disk.

## Verification

- `uv run pytest src/manicure/test_track_manager.py -q`
- `just check`
- `just test`

All passed locally before push. New PR checks started on run `24954097067` after push.
