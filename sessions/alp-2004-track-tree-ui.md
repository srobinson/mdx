---
title: ALP-2004 Track Tree UI
type: sessions
tags: [frontend, manicure, tracks, subagents]
summary: Implemented exchange track tree rendering, persistent collapse state, and track_id API filtering for ALP-2004.
status: active
source: frontend-engineer
confidence: high
created: 2026-04-25
updated: 2026-04-26
---

## Summary

- Redesigned exchange rows to use taller fixed rows, wrapped metric chips, and a separate status chip so token counts no longer collide with completion state.
- Locked root tracks as structural containers only: root track headers are no longer rendered, root exchanges start at depth 0, and subagent track headers remain collapsible.

- Disabled automatic selection of new SSE exchange events so the intercept sidebar no longer jumps to the latest row; manual selection and deletion cleanup remain intact.

Implemented ALP-2004 track support across the exchange list. The frontend now builds a parent and subagent track tree from indexed exchange metadata, renders track headers with full spawn identifiers, display names, status, turn counts, depth indentation, and persistent collapse controls. The API now accepts an optional `track_id` filter for indexed exchanges.

## Architecture Decisions

- Extended shared frontend types with `TrackRole`, `TrackStatus`, `ExchangeTrack`, and `ExchangeTrackStub` so UI tree construction is typed without `any` props.
- Added `buildExchangeTrackTree` in `useExchanges.ts` to group exchanges by `track_id`, preserve first seen ordering, infer root versus subagent roles, and attach nested children through `parent_track_id`.
- Kept `ExchangeList` virtualized by flattening track header and exchange rows before passing them to TanStack Virtual.
- Added `TrackHeader` as a dedicated component for track metadata and collapse controls.
- Stored collapsed track IDs in `uiStore`, scoped by run/session, so collapse state survives remounts without leaking across runs.
- Added `track_id` filtering to the storage interface and disk backend so API consumers can request a single track.
- Addressed code quality review findings for ExchangeList and TrackHeader: exhaustive effect dependency coverage, typed string CSS custom property values, and metric text semantics without `display: contents`.

## Performance Notes

- Frontend production build completed successfully.
- Latest bundle evidence after row redesign: CSS gzip 10.28 kB, JS gzip 112.54 kB, within the 200 kB gzipped target.
- The exchange list remains virtualized. Track tree construction is memoized through `useMemo` in the hook and component paths.

## Deviations from Spec

- Fan out stub rendering is supported through the typed `ExchangeTrackStub` input to `ExchangeList`. The current flat `IndexEntry` list does not expose response content or spawned track side channel data, so production still needs a backend or source layer to provide stubs if strict immediate derivation from parent `tool_use` blocks is required.

## Open Items

- Wire real spawn stub extraction into the data source when the backend exposes parent response tool calls or a spawned track side channel.
- Consider block level focus routing for subagent headers if future exchange payloads expose exact parent spawn block anchors.
