---
title: Native Resume Feasibility in Transport Matters
type: research
tags: [transport-matters, spaces, slice7, native-resume, session-store]
summary: Spaces Slice 7 native resume should rebuild harness native session homes from TM Tier 1 transcript snapshots, while internal continuation stays a separate child session model.
status: active
source: codebase-analyst
confidence: high
created: 2026-06-22
updated: 2026-06-22
---

## Executive Summary

Transport Matters can support native resume after desktop quit by treating the harness native session file as rehydratable state. The recommended design is to rebuild a TM owned resume home from the byte faithful Tier 1 transcript snapshot and then launch through a harness neutral resume strategy.

Primary brainstorm artifact: `/Users/alphab/.mdx/projects/transport-matters-resume-feasibility--brainstorm.md`.

## Project Metadata

- Repository: `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters`
- Verified branch and head: `main` at `3be3c61`
- fmm index: `.fmm.db` present
- Backend: Python 3.14, FastAPI, Pydantic, psycopg, Alembic
- Frontend: React 19, Vite, TypeScript, Zustand, TanStack Query, xterm
- Check interpreter: `api/.venv/bin/python` reported Python 3.14.5

## Architecture

Native resume crosses four seams:

1. **Run lifecycle.** `RunManager` is process resident. It stores runs in `_runs` (`api/src/transport_matters/run_manager.py:126`) and closes active runs on shutdown (`api/src/transport_matters/run_manager.py:275-279`). `main.lifespan` creates the manager on app state and closes it during cleanup (`api/src/transport_matters/main.py:221-227`). Reopen must spawn a new run rather than attach to an old process.
2. **Tier 1 transcript ownership.** Run storage is `{slug}/{hash}/{run_id}` (`api/src/transport_matters/workspace.py:71-92`). Transcript snapshots live at `<run_dir>/transcripts/<session_id>.jsonl` (`api/src/transport_matters/storage/disk_layout.py:69-81`). The tailer writes consumed native bytes before normalization (`api/src/transport_matters/index/tailer.py:378-385`).
3. **Harness session mechanics.** `LaunchProfile` owns per harness behavior. Claude currently starts new managed sessions with `--session-id <id>` (`api/src/transport_matters/cli/launch_profile.py:139-149`). Codex starts owned sessions with `resume <id>` after seeding a rollout (`api/src/transport_matters/cli/launch_profile.py:163-206`). Slice 7 needs explicit native resume intent so Claude can use `--resume <native_session_id>`.
4. **Canvas session anchor.** Captured run refs allow `sessionId?: string` (`www/src/session-canvas/model/paneRecords.ts:170-178`), but `createCapturedRunRef()` does not populate it (`www/src/session-canvas/model/spawn.ts:31-46`). The backend already computes `RunViewModel.sessionId` (`api/src/transport_matters/api/v1/run_routes.py:409-439`), but the frontend `createCapturedRun()` returns only `runId` (`www/src/api.ts:457-467`).

## Key Patterns

- **Derived durability beats live process retention.** Keep RunManager process scoped and rebuild the harness native home from TM data on reopen.
- **Session id belongs in the pane.** The stable canvas anchor is TM `sessionId`; `runId` is only the current process attachment.
- **LaunchProfile is the correct polymorphic seam.** Runtime templates should declare capability, while `LaunchProfile` owns native flags and home layout.
- **Internal continuation remains separate.** `continueFromSessionId` already creates continuation launch metadata and lineage, but it is a child session path, not native same session resume.

## Detailed Findings

### Recommended mechanism

Use a durable resume home materialized from Tier 1:

1. Resolve the pane `sessionId` to `SessionRow`.
2. Read `native_session_id`, `harness`, `run_id`, `workspace_slug`, `workspace_hash`, `home_dir`, `source_descriptor`, and `template_provenance`.
3. Derive the Tier 1 transcript snapshot path.
4. Copy or symlink it into a resume home under the harness expected native location.
5. Spawn a new captured run with native resume argv and the same TM session anchor.

Whole native home preservation is a fallback if smoke tests prove transcript only reconstruction is insufficient. Reconstructing native files from Postgres events is too lossy for the first native resume implementation.

### Schema state

Current main already has the earlier missing classification columns:

- `SessionRow.native_session_id`: `api/src/transport_matters/session/models.py:72`
- `SessionRow.session_purpose` and `session_visibility`: `api/src/transport_matters/session/models.py:78-79`
- `SessionRow.parent_session_id` and `forked_at_seq`: `api/src/transport_matters/session/models.py:82-83`
- Migration `0004_session_purpose_visibility`: `api/migrations/versions/0004_session_purpose_visibility.py:18-38`
- Spaces identity migration: `api/migrations/versions/0006_spaces_foundation.py:84-104`

A DB migration is not required for the minimal Tier 1 rehydrate design. Optional observability could add a small resume state table or manifest keyed by `session_id`.

### Frontend gap

The data path for `sessionId` stops too early. `run_routes` computes it, but `www/src/api.ts` discards it. Slice 7 should return `{ runId, sessionId }`, store both in `CapturedRunRecord`, and patch matching captured run pane refs by `runKey`.

### Internal continuation

Internal continuation is partially implemented:

- API input: `CreateRunRequest.continue_from_session_id` at `api/src/transport_matters/api/v1/run_routes.py:103`
- Launch field construction: `api/src/transport_matters/api/v1/run_routes.py:339-362`
- Parent metadata and `resume_context`: `api/src/transport_matters/api/v1/run_continuation.py:28-61`
- Session lineage persistence: `api/src/transport_matters/session/ingest.py:69-97`

Remaining work is agent readable prior session tooling and UI or director affordances. This path is feasible and should be built as a continuation feature, not as the desktop reopen native resume substitute.

## Dependencies

- `RunManager` and run routes for spawn, stale attach handling, and public `sessionId` propagation.
- `DiskStorageLayout`, `TranscriptTailer`, and `make_transcript_snapshot_writer` for Tier 1 native transcript bytes.
- `LaunchProfile`, `runtime_home`, and `launch_environment` for native home and argv construction.
- `SessionRow`, `AsyncSessionDao`, and session route models for session lookup and lineage.
- Frontend canvas store and captured run store for persisting `sessionId` separately from `runId`.

## Relevance to Helioy

This design preserves the Helioy north star: API first, with UI and director agents as equal clients. A native resume endpoint gives both the desktop canvas and a future director agent the same operation: resume this durable session in this worktree.

## Open Questions

1. Does Claude `--resume <id>` accept a reconstructed `CLAUDE_CONFIG_DIR` with only the transcript plus normal auth source?
2. Does Codex `resume <id>` require the original date path, or will any matching rollout under `CODEX_HOME/sessions` work?
3. Should resume homes copy Tier 1 snapshots or symlink them?
4. How much final tail drain is needed during graceful desktop shutdown to avoid a snapshot lag?
5. Should session bind events be added now for future harnesses whose session id is learned after launch?
