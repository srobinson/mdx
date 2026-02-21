---
title: ALP-2005 Subagent Continuation Routing
type: sessions
tags: [backend, manicure, track-manager, subagents]
summary: Fixed fan-out subagent continuation routing by correlating tool_result ids with the child track that emitted each tool_use.
status: active
source: backend-engineer
confidence: high
created: 2026-04-25
updated: 2026-04-25
---

## Summary

Implemented ALP-2005 on `nancy/ALP-1847` at commit `6a729d7`. The fix keeps continuation turns for concurrent identical-signature subagents on their originating child track instead of falling back to the parent track.

Key decision: use response `tool_use.id` as the continuation correlation key. `TrackManager.observe_response()` records the owning track for every emitted tool use. `_resolve_tool_results()` keeps parent-side spawn and wait resolution first, then routes continuation tool results by that owner map when exactly one track owns the referenced tool_use ids.

## API Contract

No public API contract changed.

Internal behavior contract:

```python
state.track_tool_uses[tool_use_id] = owner_track_id
```

Resolution precedence:

1. Parent-side `open_spawns` tool results.
2. Parent-side `wait_targets` tool results.
3. Track-owned continuation tool results via `track_tool_uses`.
4. Existing Codex metadata, unassigned track, signature, and parent fallback behavior.

## Database Changes

No database or storage schema changes.

## Security Considerations

No new trust boundary or external input parser was introduced. The fix only records IDs already parsed into frozen internal IR objects. It does not mutate request or response IR.

## Performance Notes

The per-run `track_tool_uses` map is in-memory and keyed by emitted tool_use id. Lookup is O(1). Memory growth is scoped to the existing process-local `TrackManager` run state.

Verification:

- RED verified first: new Anthropic and Codex fan-out continuation tests failed by routing to `run-root`; the parent collision test passed.
- `cd api && uv run pytest src/manicure/test_track_manager.py -q`: 11 passed.
- `cd api && uv run ruff format --check src/ && uv run ruff check src/ && uv run mypy src/ && uv run pytest`: passed, 705 tests passed.
- Replay of `~/.manicure/workspaces/helioy-manicure-worktrees-nancy-alp-1847/dc1dcbca`: child continuation rows route to the two Explore subagent tracks with `track_role=subagent`; the final parent Agent-result row remains parent.

### Review Follow Up

Reviewer found that a late tool_result for a closed subagent could still route to the stale owner in `track_tool_uses`. Added `test_late_tool_result_for_closed_subagent_falls_back_to_parent` and guarded owner resolution so closed or missing owner tracks are ignored.

Follow up verification:

- RED verified first: late child tool_result after `agent_kill` failed by routing to `toolu_child`.
- `cd api && uv run pytest src/manicure/test_track_manager.py -q`: 12 passed.
- `cd api && uv run ruff format --check src/ && uv run ruff check src/ && uv run mypy src/ && uv run pytest`: passed, 706 tests passed.

### Second Review Follow Up

Reviewer found that ignoring a closed `track_tool_uses` owner still allowed `_assign_request()` to route the late tool_result to an open sibling with the same request signature. Added `test_late_tool_result_for_closed_subagent_does_not_match_sibling_signature` and changed `_resolve_tool_results()` to force parent assignment when a stale owner is seen and no parent-side or live-owner resolution wins.

Second follow up verification:

- RED verified first: sibling regression failed by assigning the late result to `toolu_child_b`.
- Targeted regressions passed: late closed owner, sibling signature case, Anthropic continuation, Codex continuation.
- `cd api && uv run pytest src/manicure/test_track_manager.py -q`: 13 passed.
- `cd api && uv run ruff format --check src/ && uv run ruff check src/ && uv run mypy src/ && uv run pytest`: passed, 707 tests passed.

## Open Items

Review follow up has been implemented and is ready for reviewer recheck. The worktree also contains unrelated unstaged UI and storage changes from other work; ALP-2005 commit scope is limited to `track_manager.py`, `test_track_manager.py`, and the plan file.
