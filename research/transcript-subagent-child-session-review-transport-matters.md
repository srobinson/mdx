---
title: Transcript Subagent Child Session Review for Transport Matters
type: research
tags: [transport-matters, transcript-canvas, subagents, codex, review]
summary: PR #53 now materializes transcript subagents as child sessions and fixes Codex structured items replay dedupe.
status: active
source: codebase-analyst
confidence: high
created: 2026-06-08
updated: 2026-06-08
---

## Executive Summary

PR #53 moves transcript subagents from virtual sidechain timeline projections to first class child sessions. The original head had a real Codex replay dedupe defect for structured `items` spawns and a source line fidelity issue in backfill. Fix commit `6bd71c3` closes both issues and passed the full API CI gate.

## Project Metadata

- Project: `transport-matters`
- Area reviewed: API transcript ingest, session store, timeline projection
- Language: Python 3.14, with Pydantic models and Postgres session storage
- Build and test system: `just`, `uv`, `ruff`, `mypy`, `pytest`
- PR: #53, branch `feat/transcript-canvas-slice-4`
- Original reviewed head: `f983f2135099286dfe6669afe915daced9c271d4`
- Final verified fix head: `6bd71c353ea1dca9824851f917caa8eb024c8049`

## Architecture

- `api/src/transport_matters/index/subagents.py` discovers provider child transcripts and records parent spawn links.
- `api/src/transport_matters/index/tailer.py` registers child `TailCursor` instances from discovered child transcripts and dedupes replayed Codex prefixes in live tailing.
- `api/src/transport_matters/session/backfill.py` mirrors child transcript discovery for replay paths.
- `api/src/transport_matters/session/ingest.py` persists `SessionBinding` child linkage into `SessionRow`.
- `api/src/transport_matters/session/timeline.py` projects child `session` rows as `SubagentRef` and `SubagentSummary` timeline targets.

## Key Patterns

- Child sessions reuse the existing `session.parent_session_id` and `session.forked_at_seq` schema instead of adding a subagent table.
- `subagentId` is derived as `subagent-session:<child_session_id>`, which keeps the ID reversible and avoids hashing.
- Live tailing separates stored `seq` from source file `source_line`, allowing replayed Codex prefix records to be skipped without losing the original source line.
- The final fix shares replay filtering between live tailing and backfill through `iter_without_replayed_prefix_with_source_lines`.

## Detailed Findings

### Closed blocker: Codex structured `items` spawns now dedupe replayed context

The original head extracted only `arguments["message"]` when recording Codex `spawn_agent` calls. Real captured Codex tool schema supports either `items` or `message`: `api/TMP/codex-capture/03-20260417T093725.401329Z.ws-payload.json:419-451`. For `items` plus `fork_context:true`, the original code stored `replay_anchor_text=None`, so child tailing yielded the replayed parent prefix.

Fix commit `6bd71c3` adds `_spawn_prompt_text` and `_items_text` in `api/src/transport_matters/index/subagents.py:269-286`. `_record_codex_spawn_links` now uses that helper at `api/src/transport_matters/index/subagents.py:129-139`. If `fork_context` is true and no prompt text can be derived, the fix stores an empty anchor so ingestion fails closed instead of keeping the replay prefix.

Coverage was added in `api/src/transport_matters/session/test_subagents.py:148-176`. The new test proves the structured `items` spawn produces only child owned events and preserves source lines `[3, 4]`.

### Closed minor: backfill now preserves original child source lines after dedupe

The original backfill path enumerated filtered child records from zero, diverging from live tailing source line behavior. Fix commit `6bd71c3` adds `iter_without_replayed_prefix_with_source_lines` in `api/src/transport_matters/index/subagents.py:74-86`. Backfill uses it at `api/src/transport_matters/session/backfill.py:105-110`, yielding child rows with original file source lines after skipped replay records.

Coverage was added in `api/src/transport_matters/session/test_subagents.py:179-214`. The test asserts backfill stores only `(3, "response_item")` and `(4, "response_item")` for the child session.

### Non findings

- The earlier syntax blocker was withdrawn after revalidation. The exact original blob compiled under the repo interpreter, `api/.venv/bin/python` 3.14.5. Ambient Python 3.13.2 fails on the same syntax, but `api/pyproject.toml:8` declares `requires-python = ">=3.14"`.
- The focused subagent tests import `subagents.py` indirectly through `tailer.py`.
- Virtual sidechain projection is removed from runtime symbols: no `_append_virtual_sidechains`, `_sidechain_root_id`, `SubagentMode`, `subagent-sidechain`, or `virtual-sidechain` runtime references remain in the reviewed branch.
- Schema supports N child sessions through parent and fork columns in the session foundation migration.
- Wire guardrail held. The reviewed diff did not edit proxy, breakpoint, pause, request pipeline, exchange recorder, track manager, or Codex continuity files.

## Dependencies

- Pydantic models for transcript and timeline data contracts.
- Psycopg and Postgres for session and event persistence.
- Ruff, mypy, and pytest as the API quality gate.

## Relevance to Helioy

This review reinforces that transcript projections should preserve native provider shapes without reintroducing virtual sidecar abstractions. It also shows why Codex tool call coverage must include both `message` and structured `items` arguments when replay or child session linking depends on spawn metadata.

## Verification

- `cd api && just ci` at `6bd71c3`: passed, including ruff format check, ruff check, mypy, and `1215 passed in 15.57s`.
- Focused current tests at `6bd71c3`: `test_tailer_materializes_codex_items_subagent_and_dedupes_replay` and `test_backfill_preserves_codex_items_subagent_source_lines` both passed.
- Fail before check at `f983f21` with the new tests copied in: both tests failed. Tailer kept `[0, 1, 2, 3, 4]` child events instead of `[0, 1]`; backfill kept replay prefix rows instead of only source lines 3 and 4.
- Bus signoff sent for PR #53 after peer confirmation on topic `canvas-build-s4-signoff`.

## Open Questions

- Should future Codex replay dedupe prefer provider markers over prompt text once a stable child owned marker exists?
- Should `ReplayRecord` become a named dataclass if more source metadata is added beyond source line preservation?
