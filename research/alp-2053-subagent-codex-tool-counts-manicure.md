---
title: ALP-2053 subagent Codex tool count investigation in Manicure
type: research
tags: [manicure, alp-2053, codex, subagents, tool-counts]
summary: The observed subagent screenshot is not a finalization count regression; the selected turn legitimately emitted one tool call, and the later subagent final answer turn has zero tools.
status: active
source: codebase-analyst
confidence: high
created: 2026-04-27
updated: 2026-04-27
---

## Executive Summary

The persisted capture artifacts falsify the first frontend cache hypothesis for the screenshot under review. The main track emitted three shell tool calls in one Codex response, then a final answer turn with zero tool calls. The subagent emitted one shell tool call per Codex response, then a later final answer turn with zero tool calls. The screenshot selects the third subagent tool response, not the final answer response.

## Project Metadata

- Project: Manicure, provider neutral context control plane for coding agents.
- Worktree: `/Users/alphab/Dev/LLM/DEV/helioy/manicure-worktrees/nancy-ALP-2019`.
- Branch: `nancy/ALP-2019`.
- fmm: indexed by `.fmm.db` in the worktree root.
- Backend: Python 3.12 plus, FastAPI, Pydantic, mitmproxy, uv, pytest.
- Frontend: React 19, TypeScript, Vite, TanStack Query, Vitest, pnpm.

## Architecture

Codex turn counts are derived in `api/src/manicure/codex/derivation_engine.py`. Open turns keep committed tool calls in `CodexTurnSummary.tool_calls` and active calls in `cursor.open_tool_calls`. `api/src/manicure/storage/base.py:82-96` projects open list summaries by adding cursor open calls. Terminal turns have no cursor, so the ALP-2053 backend fix folds remaining open calls into finalized `turn.tool_calls` at `api/src/manicure/codex/derivation_engine.py:310-356`.

The ExchangeList card renders the Tools metric from `entry.codex_turn.tool_calls` first. See `www/src/components/ExchangeTurnCard.tsx:130-161`.

## Detailed Findings

### Main and subagent captures have different turn topology

The main capture in the screenshot used session `019dcdbe-8ca4-78e3-ac57-d43d959f1b8b`:

| path | turn | request tool results | response tool uses | final text | tool_calls |
| --- | ---: | --- | --- | --- | ---: |
| `~/.manicure/workspaces/helioy-manicure-worktrees-nancy-alp-2019/ab620626/20260427T080112Z-26246491` | 23 | none | `call_W5I`, `call_CAV`, `call_9ZP` | none | 3 |
| `~/.manicure/workspaces/helioy-manicure-worktrees-nancy-alp-2019/ab620626/20260427T080119Z-d5c52227` | 24 | `call_W5I`, `call_CAV`, `call_9ZP` | none | `Done.` | 0 |

The subagent capture in the screenshot used session `019dcdf5-7d1a-79c0-a4da-3925249d1fe6`:

| path | turn | request tool result | response tool use | final text | tool_calls |
| --- | ---: | --- | --- | --- | ---: |
| `~/.manicure/workspaces/helioy-manicure-worktrees-nancy-alp-2019/ab620626/20260427T080209Z-d53f2f80` | 3 | `call_VLNg` | `call_dAwl` | none | 1 |
| `~/.manicure/workspaces/helioy-manicure-worktrees-nancy-alp-2019/ab620626/20260427T080217Z-b2e2a7f4` | 4 | `call_dAwl` | `call_2Bl` | none | 1 |
| `~/.manicure/workspaces/helioy-manicure-worktrees-nancy-alp-2019/ab620626/20260427T080223Z-ddb4fbf1` | 5 | `call_2Bl` | `call_luN` | none | 1 |
| `~/.manicure/workspaces/helioy-manicure-worktrees-nancy-alp-2019/ab620626/20260427T080228Z-54048bfc` | 6 | `call_luN` | none | `Done.` | 0 |

The selected subagent screenshot shows turn 5. That turn includes a prior tool result in the request and emits the third shell tool call in the response. `tool_calls: 1` is the correct per turn count for that response.

### The final subagent answer turn is correct

The persisted subagent final turn is `20260427T080228Z-54048bfc`. Its artifacts show:

- request contains the final tool result, `call_luNnfRasxN6BTwFWWTL0on0f`
- response content is text, `Done.`
- `turn.json` has `tool_calls: 0`, `text_chars: 5`, `status: completed`

This matches the main final answer turn semantics.

### The failing frontend test encodes the earlier, now falsified hypothesis

`www/src/hooks/useExchangeStream.validation.test.tsx` currently has a failing test named `does not regress observed subagent tool counts during finalization`. It models one exchange id receiving an open subagent row with `tool_calls: 1`, then the same exchange id receiving a finalized row with `tool_calls: 0`, and expects the frontend cache to preserve `1`.

That does not match the inspected subagent capture. The real subagent tool sequence is multiple exchange ids, one per Codex response. The final answer exchange has zero response tool calls. A frontend max preserve rule would be a UI compensation policy, not evidence of the correct backend semantics.

## Test Results

Focused backend verification passed:

```bash
cd api
uv run pytest \
  src/manicure/codex/test_derivation_replay.py::test_replay_carries_pending_tool_activity_into_finalized_count \
  src/manicure/codex/test_derivation_replay.py::test_replay_does_not_double_count_completed_tool_activity \
  src/manicure/codex/test_transport_addon.py::test_addon_websocket_message_projects_open_tool_activity_into_list_summary \
  -q
```

Result: `3 passed`.

The current frontend regression test fails:

```bash
cd www
pnpm vitest run src/hooks/useExchangeStream.validation.test.tsx -t "subagent tool counts"
```

Result: expected `1`, received `0` at `www/src/hooks/useExchangeStream.validation.test.tsx:428`.

## Recommendations

1. Do not add frontend max preserve logic based on this screenshot. It risks masking a bad backend payload and would make finalized server summaries less authoritative.
2. Remove or rewrite the failing frontend test unless a separate product decision says finalized subagent cards must never decrease from a prior live observation for the same exchange id.
3. If another captured subagent finalization shows the same exchange id dropping from an open `tool_calls: 1` to a finalized `tool_calls: 0`, add the backend subagent transport regression proposed in the earlier note. The inspected screenshot does not show that case.
4. Keep the existing backend ALP-2053 fix in `api/src/manicure/codex/derivation_engine.py`; it correctly handles terminal frames that arrive before `response.output_item.done`.

## Relevance to Helioy

This preserves Manicure as the source of truth for Codex turn semantics. It also shows why Helioy capture debugging should compare persisted artifacts, not prompts alone. The same prompt can produce different response topology in parent and subagent sessions.

## Open Questions

- Should ExchangeList ever show cumulative task level tool counts for subagent sessions, separate from per turn tool counts?
- Is the subagent serial tool behavior expected from Codex subagent prompting, or should that be investigated separately from ALP-2053?
