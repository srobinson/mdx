---
title: Subagent Rail Border Alignment in Manicure
type: research
tags: [manicure, ui, react, tailwind, polish]
summary: Fixed a 1 CSS px border offset by removing outer horizontal padding from exchange and track rows.
status: active
source: codebase-analyst
confidence: high
created: 2026-04-26
updated: 2026-04-26
---

## Executive Summary

The exchange list subagent rail had a subtle 1 CSS px offset where row borders and rail fills did not share the same outer edge. The accepted fix removes the horizontal `px-1` wrapper padding from exchange cards and track headers so their bordered frames align flush with the rail system.

## Project Metadata

- Language: TypeScript, React
- UI styling: Tailwind utility classes
- Test runner: Vitest with Testing Library
- Relevant files:
  - `www/src/components/ExchangeTurnCard.tsx`
  - `www/src/components/TrackHeader.tsx`

## Architecture

`ExchangeList` renders virtualized rows as `TrackHeader` or `ExchangeTurnCard`. Both components are absolutely positioned full width rows and rely on nested grid columns plus `agentRailStyle(track_id)` for subagent rail coloring.

## Detailed Findings

- `www/src/components/ExchangeTurnCard.tsx` removed `px-1` from the outer row button. This makes the exchange card border align with the same full width coordinate system as the rail.
- `www/src/components/TrackHeader.tsx` removed `px-1` from the outer track header wrapper. This makes track header borders line up with exchange card borders.
- The fix preserves the existing subagent grid column structure, including `grid-cols-[1px_8px_52px_minmax(0,1fr)]`, and avoids changing header border semantics.

## Verification

- `pnpm --dir www test src/components/ExchangeList.test.tsx -- --runInBand` passed with 15 tests.
- `pnpm --dir www typecheck` passed.
- `pnpm --dir www lint` passed.
- `git diff --check` passed.

## Open Questions

- A screenshot comparison at device pixel ratio 2 remains the best validation for this kind of optical 1px alignment fix.
