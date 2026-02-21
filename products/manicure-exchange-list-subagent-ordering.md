---
title: ExchangeList Subagent Ordering in Manicure
type: research
tags: [manicure, exchange-list, subagents, react, vertical-slice, bug-analysis]
summary: Subagent tracks are rendered after all parent exchanges because the frontend flattens parent track rows before child tracks and lacks a spawn anchor for natural placement.
status: active
source: codebase-analyst
confidence: high
created: 2026-04-26
updated: 2026-04-26
---

## Executive Summary

Subagent tracks appear at the tail of `ExchangeList` because the UI treats tracks as grouped blocks, not as events in one chronological stream. The backend correctly persists and streams track metadata, but `flattenTrackRows` renders every parent exchange before recursing into child tracks, so children cannot appear at the exchange where they were spawned.

The same behavior applies to Claude and Codex because the problematic code is provider neutral in `www/src/hooks/useExchanges.ts` and `www/src/components/ExchangeList.tsx`.

## Project Metadata

- Repository: `/Users/alphab/Dev/LLM/DEV/helioy/manicure`
- Indexed by fmm: yes, `.fmm.db` exists at repo root, `api/`, and `www/`
- Backend: Python 3.12+, FastAPI, mitmproxy, pydantic, uv build via `api/pyproject.toml`
- Frontend: React 19, Vite 8, TypeScript 5.9, TanStack React Query and Virtual, pnpm 10 via `www/package.json`
- User evidence: `/Users/alphab/Desktop/Screenshot 2569-04-26 at 22.42.01.png`

## Architecture

### Vertical slice

1. Provider traffic is assigned to a track in `TrackManager.record_exchange`, which calls `classify_request` and `observe_response` as needed. See `api/src/manicure/track_manager.py:66-75`.
2. Claude HTTP exchanges and Codex websocket exchanges persist `IndexEntry` records with `track_id`, `parent_track_id`, `track_display_name`, and `track_role`. See `api/src/manicure/exchange_recorder.py:197-209`, `api/src/manicure/codex/exchange.py:236-253`, and `api/src/manicure/storage/base.py:102-129`.
3. The list API returns stored `IndexEntry` rows with optional filtering. See `api/src/manicure/api/v1/exchanges.py:123-144` and `api/src/manicure/storage/disk.py:225-239`.
4. The frontend fetches `/api/exchanges`, reverses the API result, and builds an `ExchangeTrack[]` tree. See `www/src/api.ts:26-43` and `www/src/hooks/useExchanges.ts:134-153`.
5. `ExchangeList` flattens that tree into virtual rows and renders track headers and turn cards. See `www/src/components/ExchangeList.tsx:197-213` and `www/src/components/ExchangeList.tsx:238-272`.

## Key Patterns

### Track assignment is a grouping concern

`TrackRecord` stores identity, parent, display name, role, status, and signature. It does not store a creation timestamp, spawn exchange id, spawn tool id, or insertion anchor. See `api/src/manicure/track_manager.py:28-35`.

### UI tree flattening is depth first by track group

`buildExchangeTrackTree` groups entries by track, sorts exchanges inside each track by timestamp, attaches children by `parent_track_id`, then sorts tracks by draft encounter order. See `www/src/hooks/useExchanges.ts:90-129`.

`flattenTrackRows` then emits rows in this order:

1. subagent track header, if the current track is a subagent
2. all exchanges in the current track
3. all child tracks

See `www/src/components/ExchangeList.tsx:43-74`.

## Detailed Findings

### Confirmed root cause

The bug is in `flattenTrackRows`.

```text
www/src/components/ExchangeList.tsx:49-71
for each track:
  render subagent header
  render every exchange in that track
  recurse into children
```

For the root parent track, `rendersHeader` is false, so the UI renders every root exchange first. Only after that does it recurse into subagent children. A child track therefore cannot appear near the parent exchange that spawned it. It must appear after all root exchanges in the current list window.

### Backend metadata is not the failing layer

The backend records the required track fields:

- `IndexEntry` contains `track_id`, `parent_track_id`, `track_display_name`, and `track_role` in `api/src/manicure/storage/base.py:116-119`.
- Claude persistence writes those fields through `assignment_index_fields` in `api/src/manicure/exchange_recorder.py:197-209`.
- Codex persistence writes the same fields in `api/src/manicure/codex/exchange.py:236-253`.
- SSE includes the same fields in `emit_exchange` at `api/src/manicure/exchange_recorder.py:96-116`.
- The frontend SSE handler preserves them in `www/src/hooks/useExchangeStream.ts:202-227`.

This means the observed tail placement is not caused by missing track metadata.

### Codex is expected to show the same symptom

Codex uses the same persisted index fields and the same frontend tree builder. Codex track detection is provider specific only at the assignment layer:

- `spawn_agent` responses register pending Codex spawns in `api/src/manicure/track_manager.py:100-103` and `api/src/manicure/track_manager.py:157-170`.
- Codex subagent requests can also identify their track through provider metadata in `api/src/manicure/track_manager.py:409-430`.
- Once persisted, Codex and Claude enter the same `buildExchangeTrackTree` and `flattenTrackRows` path.

Therefore a Codex subagent track will also render as a grouped child block after parent exchanges, unless the frontend flattening model changes.

### Secondary ordering problem

`buildExchangeTrackTree` assigns sibling track order from first encounter in the input list. See `www/src/hooks/useExchanges.ts:44-76` and `www/src/hooks/useExchanges.ts:120-129`.

`useExchanges` reverses the API result before tree building. See `www/src/hooks/useExchanges.ts:142-147`. Live SSE also prepends new exchanges in `www/src/hooks/useExchangeStream.ts:222-227`.

Result: sibling subagent ordering is based on whichever track is encountered first in newest first data, not on spawn time or first chronological activity. This can make active subagent groups jump ahead of earlier subagents.

### Local storage evidence

The recent Manicure workspace index at `~/.manicure/workspaces/dev-helioy-manicure/660bc067/index.jsonl` contains the same pattern visible in the screenshot.

For run `0713f931-1665-4a3f-bd9b-e6420c00c0cb`:

- root parent track: 39 exchanges from `2026-04-26T13:56:46Z` through `2026-04-26T15:48:11Z`
- `Explore` subagent: 29 exchanges from `2026-04-26T14:02:34Z` through `2026-04-26T14:05:04Z`
- later backend and frontend subagents from `2026-04-26T15:19Z` and `2026-04-26T15:43Z`

A local emulation of `buildExchangeTrackTree` plus `flattenTrackRows` produced 128 rows. The first subagent row appeared at flattened index 39, exactly after all root track exchanges, even though the first subagent activity started at `2026-04-26T14:02:34Z`.

This proves the placement follows the UI grouping algorithm, not the natural chronological sequence.

## Dependencies

- `@tanstack/react-query`: fetch cache and SSE driven list updates
- `@tanstack/react-virtual`: virtualized row rendering in `ExchangeList`
- FastAPI: `/api/exchanges` endpoint and SSE stream
- mitmproxy: provider traffic capture layer

## Relevance to Helioy

This matters because Manicure is the operator view for Helioy agent traffic. If subagent tracks appear only at the tail, the UI obscures causal flow: parent turn, spawn, subagent work, wait or result, parent continuation. That makes multi agent debugging harder in exactly the workflows Helioy depends on.

## Recommended Direction

1. Decide whether `ExchangeList` should be a chronological event stream with nested track annotations, or a grouped track browser. The screenshot complaint points to the former.
2. Add an anchor concept for child tracks. Strong options are `spawn_exchange_id`, `spawn_tool_use_id`, or `created_at` on the track record or list projection.
3. Change the frontend row builder to interleave child track headers at their anchor, then render the child track subtree there.
4. Add a regression test in `www/src/components/ExchangeList.test.tsx` where a root exchange before spawn, subagent exchange, and root exchange after spawn render in natural causal order.
5. For a smaller interim fix, sort sibling tracks by earliest exchange timestamp and place child groups after the nearest preceding parent exchange. This improves chronology but cannot be exact when a child is registered before its first exchange or when spawn and child timestamps are close.

## Open Questions

- Should historical mode preserve grouped track browsing, or also use chronological interleaving?
- Should pending track stubs appear at the spawn exchange before any child exchange exists?
- Should nested subagents anchor under the parent subagent exchange that spawned them, or under the first observed child exchange when no spawn artifact is available?
