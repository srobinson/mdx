---
title: ALP-2053 Codex tool count finalization fix in Manicure
type: research
tags: [manicure, codex, sse, derivation, tool-counts, alp-2053]
summary: Manicure now preserves observed Codex tool activity when a turn finalizes before tool completion events arrive.
status: active
source: codebase-analyst
confidence: high
created: 2026-04-27
updated: 2026-04-27
---

## Executive Summary

ALP-2053 was confirmed as a backend Codex derivation bug. Open list summaries projected cursor open tool calls, but terminal summaries discarded those pending calls and emitted `codex_turn.tool_calls: 0`. The fix now lives in `/Users/alphab/Dev/LLM/DEV/helioy/manicure-worktrees/nancy-ALP-2019` and carries pending open tool activity into finalized turn summaries while preserving the no double count behavior when a completed tool item already committed the call.

## Project Metadata

- Project: `manicure`, a context control plane for coding agents.
- Target worktree: `/Users/alphab/Dev/LLM/DEV/helioy/manicure-worktrees/nancy-ALP-2019`.
- Target branch: `nancy/ALP-2019`.
- fmm status: indexed by `.fmm.db` in the worktree root.
- Topology from fmm: 250 files, 51,616 LOC. `api/` contains 164 files and `www/` contains 86 files.
- Backend: Python 3.12 plus, FastAPI, Pydantic, mitmproxy, uv, pytest.
- Frontend: React 19, TypeScript, Vite, TanStack React Query, TanStack Virtual, Zustand, Vitest.

## Architecture

Codex websocket traffic is projected into semantic turn artifacts in `api/src/manicure/codex/derivation_engine.py`. Open turns keep committed counts in `CodexTurnSummary.tool_calls` and retain in flight calls in `cursor.open_tool_calls`. List projection then shows the display count through `CodexTurnListSummary.from_turn` in `api/src/manicure/storage/base.py`.

Terminal turns are cursorless. Before ALP-2053, terminal derivation used only `committed_tool_calls`, so a terminal frame after `response.output_item.added` but before `response.output_item.done` generated a finalized list summary with zero tool calls. SSE then replaced the frontend cached row with that finalized summary.

## Key Patterns

- Open turn raw summaries keep committed counts only. Display projection adds `len(cursor.open_tool_calls)` for open turns.
- Finalized turns cannot keep cursor state, so derivation must fold pending cursor activity into the terminal count before building the cursorless summary.
- `response.output_item.done` removes the call from `open_tool_calls` before terminal finalization, which prevents double counting.

## Detailed Findings

### Root cause verified

`api/src/manicure/codex/derivation_engine.py:251` to `263` commits a tool call only when `response.output_item.done` is processed. `api/src/manicure/codex/derivation_engine.py:310` to `313` now computes terminal counts from both committed calls and remaining open calls. Before the fix, only committed calls were used.

### Fix

`api/src/manicure/codex/derivation_engine.py:313` now computes:

```python
finalized_tool_calls = committed_tool_calls + len(open_tool_calls)
```

The finalized count is used in terminal event data at `api/src/manicure/codex/derivation_engine.py:330` to `336`, terminal `CodexTurnSummary` construction at `api/src/manicure/codex/derivation_engine.py:338` to `356`, websocket close finalization event data at `api/src/manicure/codex/derivation_engine.py:361` to `375`, and interrupted `CodexTurnSummary` construction at `api/src/manicure/codex/derivation_engine.py:377` to `392`.

### Regression tests

- `api/src/manicure/codex/test_derivation_replay.py:174` to `224` adds a replay fixture where `response.output_item.added` is followed directly by `response.completed`.
- `api/src/manicure/codex/test_derivation_replay.py:298` to `316` asserts finalized turn data carries one pending tool call.
- `api/src/manicure/codex/test_derivation_replay.py:319` to `324` asserts completed tool activity is still counted once.
- `api/src/manicure/codex/test_transport_addon.py:334` to `350` now asserts the finalized SSE and stored index entry keep `codex_turn.tool_calls == 1` after open tool activity followed by terminal failure.

### Red green evidence

The new backend regression failed before the fix:

```text
FAILED test_replay_carries_pending_tool_activity_into_finalized_count
{'tool_calls': 0} != {'tool_calls': 1}
FAILED test_addon_websocket_message_projects_open_tool_activity_into_list_summary
assert 0 == 1
```

After the fix was moved to the correct worktree, focused verification passed:

```bash
cd /Users/alphab/Dev/LLM/DEV/helioy/manicure-worktrees/nancy-ALP-2019
uv run --project api pytest \
  api/src/manicure/codex/test_derivation_replay.py::test_replay_carries_pending_tool_activity_into_finalized_count \
  api/src/manicure/codex/test_derivation_replay.py::test_replay_does_not_double_count_completed_tool_activity \
  api/src/manicure/codex/test_transport_addon.py::test_addon_websocket_message_projects_open_tool_activity_into_list_summary \
  -q
```

Result: 3 passed.

Broader Codex verification passed in the correct worktree:

```bash
uv run --project api pytest api/src/manicure/codex -q
```

Result: 98 passed.

Static checks run in the correct worktree:

```bash
uv run --project api ruff check \
  api/src/manicure/codex/derivation_engine.py \
  api/src/manicure/codex/test_derivation_replay.py \
  api/src/manicure/codex/test_transport_addon.py
uv run --project api mypy api/src/manicure/codex/derivation_engine.py
git diff --check
```

Results: ruff passed, mypy passed for the changed source file, and `git diff --check` produced no output.

## Dependencies

No dependency changes were made. The fix is confined to Python backend Codex derivation logic and backend tests.

## Relevance to Helioy

This preserves a stable user visible Codex exchange list metric without frontend fallback logic. It keeps the Manicure backend as the source of truth for Codex turn summaries, which matches the Helioy preference for structural correctness before UI compensation.

## Open Questions

- Full API pytest was not run. The Codex backend suite, focused regression tests, ruff, source mypy, and whitespace checks were run in the correct worktree.
- The finalized `res.tool_calls` statistic remains zero in the addon regression when no completed response item exists. The ExchangeList card prioritizes `codex_turn.tool_calls`, so ALP-2053 is resolved without changing response stats.
