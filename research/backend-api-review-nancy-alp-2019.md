---
title: Backend API Review for Nancy ALP-2019
type: research
tags: [manicure, nancy, alp-2019, backend-review, api, storage]
summary: Read-only backend/API review found one blocking data-loss risk in DiskStorageBackend legacy flat spawn-anchor handling; targeted backend tests and ruff passed.
status: active
source: codebase-analyst
confidence: high
created: 2026-04-27
updated: 2026-04-27
---

## Executive Summary

Reviewed the `api/` diff for branch `nancy/ALP-2019` against `main`, focused on Codex exchange persistence, repair and transport turn tests, `exchange_recorder`, storage cache backfill, and `track_manager` split tests. The main correctness issue is a blocking storage migration hazard: initializing `DiskStorageBackend` deletes the entire configured storage root when any `index.jsonl` row contains legacy flat spawn anchor keys.

## Project Metadata

- Language: Python 3.12 plus, tested here with Python 3.13.0 through `uv`.
- Framework and runtime: FastAPI, mitmproxy, pydantic, aiofiles.
- Build and tools: `pyproject.toml`, `uv`, `pytest`, `ruff`, strict `mypy` config.
- fmm signal: `api/` is indexed and structural fmm tools worked. `api/` topology is 177 files and 36,184 LOC.

## Architecture

Changed backend/API areas:

- Codex exchange persistence: `api/src/manicure/codex/exchange.py`, `api/src/manicure/codex/exchange_derivation.py`.
- Broadcast and persistence helpers: `api/src/manicure/exchange_recorder.py`.
- Storage models and disk backend: `api/src/manicure/storage/base.py`, `api/src/manicure/storage/disk.py`, `api/src/manicure/storage/__init__.py`.
- Track routing: `api/src/manicure/track_manager.py`.
- Tests split from large files into focused modules under `api/src/manicure/codex/`, `api/src/manicure/storage/`, and `api/src/manicure/`.

Key data flow reviewed:

1. Request pipeline classifies a request into a track.
2. Exchange persistence builds an `IndexEntry` with `assignment_index_fields`.
3. Responses update `TrackManager` with spawn tool uses and the parent exchange id.
4. Subsequent subagent assignments carry a nested `SpawnAnchor`.
5. `emit_exchange` emits the nested spawn anchor in SSE payloads.
6. Disk storage persists and reloads `IndexEntry` rows and backfills old `cache_creation_input_tokens` values from `response.ir.json`.

## Key Patterns

- Splitting large tests into scenario focused modules made track-manager and Codex transport behavior easier to review.
- `SpawnAnchor` as a nested pydantic model is cleaner than top-level flat fields and keeps persistence and SSE payload shapes aligned.
- `assignment_index_fields` centralizes the mapping from `TrackAssignment` to persisted and emitted fields, reducing duplicated `if assignment else None` code.

## Detailed Findings

### Blocker: storage initialization can delete all historical exchange data

`DiskStorageBackend.__init__` calls `_drop_legacy_flat_anchor_cache()` before creating or recovering the storage root (`api/src/manicure/storage/disk.py:44-54`). That helper scans `index.jsonl` for legacy top-level keys and then deletes `self._root` with `shutil.rmtree(self._root, ignore_errors=True)` (`api/src/manicure/storage/disk.py:60-88`). The test suite explicitly codifies the deletion of both `index.jsonl` and an exchange artifact directory in `api/src/manicure/storage/test_disk.py` under `TestLegacyFlatAnchorCacheInvalidation`.

This is not a cache-only directory in normal operation. `_DEFAULT_ROOT` is `~/.manicure/exchanges`, containing the append-only index and exchange artifacts (`api/src/manicure/storage/disk.py:38`). A user with one legacy row would lose all recorded exchanges on startup, including rows that are otherwise valid and artifact directories that could have been migrated or reindexed.

Recommended fix: replace destructive root deletion with an in-place index migration or tolerant load path. Accept the legacy flat fields, convert them to `spawn_anchor`, rewrite `index.jsonl` atomically, and preserve artifact directories. If rejecting legacy rows is required, skip or repair only those rows, never delete the entire root.

### Concern: tests assert the destructive migration boundary

`api/src/manicure/storage/test_disk.py` asserts the root wipe behavior rather than guarding against it. The storage tests pass, but they currently prove the risk rather than protect data. Add migration tests that prove legacy flat rows are converted to nested `spawn_anchor` and unrelated exchange artifacts remain present.

### No issue found in core spawn anchor propagation

The track-manager changes correctly attach parent exchange anchors when responses contain `Agent` or `spawn_agent` tool uses, and subsequent subagent assignments expose those anchors through `TrackAssignment` and `assignment_index_fields` (`api/src/manicure/track_manager.py:132-184`, `api/src/manicure/track_manager.py:202-257`, `api/src/manicure/track_manager.py:436-475`). The Codex finalize path observes response tool uses with `exchange_id=existing_entry.id` and emits the persisted entry fields back over SSE (`api/src/manicure/codex/exchange.py:386-475`).

### Test quality

The split tests are a net positive. Track manager coverage now includes Anthropic fan out, Codex fan out, nested subagents, kill and wait lifecycle cases, spawn anchor round trip, and late tool result routing. Codex repair and transport tests are easier to localize after the split.

## Dependencies

Critical dependencies touched by this review:

- `pydantic`: `SpawnAnchor` and `IndexEntry` validation and JSON round-trip.
- `aiofiles` and thread-pool storage helpers: disk persistence and atomic rewrites.
- `mitmproxy`: flow state and Codex exchange persistence inputs.
- `pytest` and `ruff`: targeted verification.

## Relevance to Helioy

Manicure is part of the Helioy ecosystem's request capture and agent trace surface. Preserving historical exchange data matters because those traces become operational memory and debugging evidence. A destructive storage migration undermines that memory layer.

## Verification

Commands run from `/Users/alphab/Dev/LLM/DEV/helioy/manicure-worktrees/nancy-ALP-2019/api` unless noted:

```bash
PYTHONDONTWRITEBYTECODE=1 uv run pytest -p no:cacheprovider src/manicure/test_track_manager_core.py src/manicure/test_track_manager_anthropic.py src/manicure/test_track_manager_codex.py src/manicure/test_track_manager_lifecycle.py src/manicure/test_exchange_recorder_emit.py src/manicure/storage/test_disk_cache_backfill.py src/manicure/codex/test_repair_diagnostics.py src/manicure/codex/test_repair_migration.py src/manicure/codex/test_repair_rebuild.py src/manicure/codex/test_repair_safety.py src/manicure/codex/test_transport_turn_close.py src/manicure/codex/test_transport_turn_completion.py src/manicure/codex/test_transport_turn_derivation.py src/manicure/codex/test_transport_turn_pause.py
```

Result: 49 passed in 0.44s.

```bash
PYTHONDONTWRITEBYTECODE=1 uv run pytest -p no:cacheprovider src/manicure/storage/test_disk.py src/manicure/storage/test_disk_atomic_write.py src/manicure/storage/test_disk_delete_recovery.py src/manicure/storage/test_disk_persist.py src/manicure/storage/test_disk_codex_artifacts.py src/manicure/api/v1/test_exchanges_get_codex_artifacts.py src/manicure/api/v1/test_exchanges_pipeline_tokens.py
```

Result: 66 passed in 0.56s.

```bash
uv run ruff check src/manicure/codex/exchange.py src/manicure/codex/exchange_derivation.py src/manicure/exchange_recorder.py src/manicure/storage/base.py src/manicure/storage/disk.py src/manicure/track_manager.py src/manicure/test_track_manager_core.py src/manicure/test_track_manager_anthropic.py src/manicure/test_track_manager_codex.py src/manicure/test_track_manager_lifecycle.py src/manicure/test_exchange_recorder_emit.py src/manicure/storage/test_disk_cache_backfill.py src/manicure/codex/test_repair_diagnostics.py src/manicure/codex/test_repair_migration.py src/manicure/codex/test_repair_rebuild.py src/manicure/codex/test_repair_safety.py src/manicure/codex/test_transport_turn_close.py src/manicure/codex/test_transport_turn_completion.py src/manicure/codex/test_transport_turn_derivation.py src/manicure/codex/test_transport_turn_pause.py
```

Result: all checks passed.

```bash
git diff --check main...HEAD -- api
```

Result: no whitespace errors.

`git status --short` was clean after verification.

## Open Questions

- Should legacy flat spawn anchor rows be migrated in place, or should they remain readable as ignored extra fields? The current implementation chooses data deletion, which should not ship.
- Does the frontend expect `spawn_anchor: null` to be present on every exchange event, or should the SSE payload omit the field when absent? This is more frontend/API contract than backend correctness.
