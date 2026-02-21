---
title: Track Tool Use Routing Review in Manicure
type: research
tags: [manicure, code-review, track-manager, subagents]
summary: Review of ALP-2005 found stale track_tool_uses issues, then confirmed 21cffb4 fixes the reviewed continuation routing cases.
status: active
source: codebase-analyst
confidence: high
created: 2026-04-25
updated: 2026-04-25
---

## Executive Summary

ALP-2005 adds `track_tool_uses` correlation so fan out subagent continuation turns can route by the tool use id emitted by the owning track. The core continuation routing works for open tracks, but the commit leaves stale mappings active after a subagent is closed.

## Project Metadata

- Project: `manicure`, Helioy provider neutral context control plane for coding agents.
- Language: Python 3.12 plus, tested locally on Python 3.13 through `uv`.
- Package: `api/pyproject.toml`, Hatchling build backend, `uv.lock` present.
- Test framework: `pytest`.
- Structural index: `.fmm.db` is present at repository root, and fmm indexed `api/src/manicure` as 160 files and 34,671 LOC.

## Architecture

`api/src/manicure/track_manager.py` owns process local track classification for ingest exchanges. The `TrackManager` flow is:

1. `record_exchange` classifies a request, then observes the response if present.
2. `classify_request` calls `_resolve_tool_results`, `_assign_request`, then `_observe_request_signature`.
3. `observe_response` registers `tool_use` blocks, including spawns, waits, kills, and general tool calls.
4. `_assign_request` chooses parent, explicit Codex subagent id, unassigned subagent, signature match, then parent fallback.

Relevant symbols:

- `TrackManager.observe_response`: `api/src/manicure/track_manager.py:88-114`
- `TrackManager._resolve_tool_results`: `api/src/manicure/track_manager.py:172-202`
- `TrackManager._assign_request`: `api/src/manicure/track_manager.py:259-304`
- `TrackManager._resolve_wait_result`: `api/src/manicure/track_manager.py:241-257`

## Key Patterns

- Parent side tool result resolution has priority over continuation correlation. `_resolve_tool_results` resolves `open_spawns` and `wait_targets` before consulting `track_tool_uses`.
- Continuation correlation is stateful and depends on tool use ids observed in prior responses.
- Closed tracks are excluded from unassigned and signature match routing, but the new owner map bypasses that status check.

## Detailed Findings

### Medium: late tool results can route to a closed subagent track

`observe_response` records every tool use owner at `api/src/manicure/track_manager.py:95`:

```python
state.track_tool_uses[block.id] = current_track_id
```

`_resolve_tool_results` later accepts that owner without checking the owner track status at `api/src/manicure/track_manager.py:193-201`. If a subagent emits a tool use, then the parent closes that subagent through `agent_kill` or a completed `wait_agent`, a late tool result for the old child tool use still classifies the request onto the closed subagent track.

Local reproduction, run under `api/` with `PYTHONPATH=src`, confirmed the late request was assigned to `TrackAssignment(track_id='toolu_child', track_role='subagent')` while `manager.tracks(ROOT_RUN_ID)['toolu_child'].status == 'closed'`.

Suggested fix:

```python
owner_track_id = state.track_tool_uses.get(result.tool_use_id)
if owner_track_id is not None:
    track = state.tracks.get(owner_track_id)
    if track is not None and track.status != "closed":
        owner_track_ids.add(owner_track_id)
```

Optionally prune `track_tool_uses` entries when a track closes in `agent_kill` and `_resolve_wait_result` to prevent stale owner mappings from accumulating.



### Medium: closed owner fallback can still misroute to an open sibling

Re-review of `a16ba76` found a remaining edge case. `_resolve_tool_results` now ignores a `track_tool_uses` owner when the owner track is missing or closed at `api/src/manicure/track_manager.py:193-197`, but the method returns `None` when no live owner remains. That allows `_assign_request` to continue into signature matching at `api/src/manicure/track_manager.py:295-304`.

In a two child fan out with identical signatures, this can assign a late tool result from closed child A to open sibling child B:

1. Parent spawns `toolu_child_a` and `toolu_child_b`, both `Explore` with `tools_count=90`.
2. Both children claim initial turns, so both have the same signature.
3. Child A emits `toolu_child_a_read`.
4. Parent closes child A with `agent_kill`.
5. A late request carries `tool_result(toolu_child_a_read)`.

Local reproduction on `a16ba76` assigned the late request to `toolu_child_b` while child A was closed and child B was still open. The expected behavior is parent fallback, not sibling reassignment.

Suggested fix: when `_resolve_tool_results` sees a stale owner match and no parent side resolution or live owner resolution wins, force parent assignment before `_assign_request` can run unassigned or signature matching. Add a regression with two identical sibling subagents, close one, then deliver a late tool result for the closed child.



### Clean re-review: 21cffb4 forces parent for stale continuation owners

Re-review of `a16ba76..21cffb4` found no functional issues in the scoped diff. `TrackManager._resolve_tool_results` now tracks `stale_owner_seen` at `api/src/manicure/track_manager.py:177` and returns `state.run_id` at `api/src/manicure/track_manager.py:207-208` when a stale owner was found and no parent side or live owner resolution wins. This prevents `_assign_request` from falling through to unassigned or signature matching for a stale child tool result.

The new regression `test_late_tool_result_for_closed_subagent_does_not_match_sibling_signature` at `api/src/manicure/test_track_manager.py:555-625` covers the prior failure mode: two identical sibling subagents, child A closed, child B open with the same signature, and a late tool result from child A. The request now assigns to the parent track.

## Verification

- `git show 6a729d7 -- api/src/manicure/track_manager.py api/src/manicure/test_track_manager.py` reviewed.
- `uv run pytest -q src/manicure/test_track_manager.py` from `api/` passed on `6a729d7`: 11 tests.
- `uv run pytest -q src/manicure/test_track_manager.py` from `api/` passed on `a16ba76`: 12 tests.
- `uv run pytest -q src/manicure/test_track_manager.py` from `api/` passed on `21cffb4`: 13 tests.
- Direct `pytest -q api/src/manicure/test_track_manager.py` from repository root failed because `manicure` was not on `PYTHONPATH`; the configured project command is through `uv` in `api/`.
- Added Linear comment `d3fbc4ac-1091-4fbb-bb4a-cb9e35ddbd0b` on ALP-2005.
- Added Linear re-review comment `ad47799a-dc2c-4081-aeff-6c5fb0f05818` on ALP-2005 for the sibling signature fallback issue.
- Sent helioy-bus reply to `helioy:general:0:1.2` on topic `alp-2005-review`.
- Sent clean helioy-bus reply for `21cffb4`: `Clean. LGTM ALP-2005`.

## Dependencies

Critical dependencies for this review:

- `manicure.ir`: request, response, message, tool use, and tool result IR types.
- `pytest`: targeted regression tests in `api/src/manicure/test_track_manager.py`.
- `uv`: project environment and dependency resolution for tests.

## Relevance to Helioy

This review protects the multi agent trace model used by Manicure and Helioy UI flows. Track ownership maps should respect lifecycle state, especially when late or out of order tool results arrive after a subagent has been closed.

## Open Questions

- Should closing a track also delete all `track_tool_uses` entries owned by that track, or should `_resolve_tool_results` only ignore closed owners and keep historical mappings?
- Should a late tool result for a closed subagent fall back to the parent track or produce an explicit orphan or ignored assignment?
