---
title: Claude Turn Numbering in Manicure Exchange List
type: research
tags: [manicure, claude, ui, exchange-list, subagents]
summary: Claude exchange rows can use per track sequence numbers while preserving Codex semantic turn numbers.
status: active
source: codebase-analyst
confidence: high
created: 2026-04-26
updated: 2026-04-26
---

## Executive Summary

Claude rows do not have Codex semantic turn artifacts, so the existing `TURN` cell fell back to `REQ` and `FRAMES` could only show an empty placeholder. The UI can keep the balanced instrument panel by deriving a per track display turn from exchange order and replacing non Codex `FRAMES` with request message count.

## Project Metadata

- Frontend: React 19, TypeScript, Vite, Vitest, Biome.
- Relevant files: `www/src/components/ExchangeList.tsx`, `www/src/components/ExchangeTurnCard.tsx`, `www/src/components/ExchangeList.test.tsx`.
- Data source: `IndexEntry` in `www/src/types.ts` carries `track_id`, `parent_track_id`, request stats, response stats, and optional `codex_turn`.

## Architecture

`buildExchangeTrackTree` groups exchanges by `track_id` and sorts each track's `exchanges` by timestamp in `www/src/hooks/useExchanges.ts:90-108`. `flattenTrackRows` then emits virtual list rows in `www/src/components/ExchangeList.tsx:42-72`. This is the correct place to derive a display sequence because the count naturally resets for each track, including subagent tracks.

`ExchangeTurnCard` owns the card instrument panel. Codex rows should continue to display `codex_turn.turn_index`, including zero based Codex turn labels such as `000`. Claude and other non Codex rows can safely use the per track sequence passed from the list.

## Key Patterns

- Preserve provider specific semantics when they exist. Codex `codex_turn` remains authoritative.
- Use derived presentation state for Claude sequence labels rather than persisting another backend field.
- Keep the bottom three cell layout stable by changing the third metric, not removing it.

## Detailed Findings

### TURN

`formatTurn` previously returned `REQ` when `codex_turn` was absent in `www/src/components/ExchangeTurnCard.tsx:62-65`. Claude never receives `codex_turn`, so every Claude row showed `REQ`.

The patched flow derives `turnSequence = entryIndex + 1` inside each track in `flattenTrackRows`, passes it into `ExchangeTurnCard`, and uses it only when `codex_turn` is missing. This gives parent tracks `001`, `002`, `003` and independently gives each subagent track its own `001`, `002`, `003`.

### FRAMES

`panelMetrics` previously always returned a `Frames` metric, with `...` when `codex_turn` was absent in `www/src/components/ExchangeTurnCard.tsx:122-146`. Claude rows cannot fill this because frames are Codex transport message ranges.

The patched metric keeps `Frames` for Codex rows and uses `Msgs` for non Codex rows, sourced from `entry.req.messages_count`. This preserves the visual balance of the three metric cells without showing a permanently empty value.

### Tests

`www/src/components/ExchangeList.test.tsx` now covers:

- root Claude track rows display `001`, `002`;
- subagent Claude track rows start their own sequence at `001`;
- non Codex metric summary uses `Msgs` instead of empty `Frames`.

## Dependencies

- `@tanstack/react-virtual` controls which rows are rendered, so tests need to account for virtual row height.
- `zustand` persists collapsed track state by session key, so tests should avoid reusing collapsed track IDs when checking subagent row visibility.

## Open Questions

- Whether the label should remain `TURN` for all providers or become `REQ` or `CALL` for Claude. The current implementation keeps `TURN` because the row represents a visible request response exchange within a track.
