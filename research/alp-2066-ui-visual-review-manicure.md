---
title: ALP-2066 UI and Visual Acceptance Review for Manicure
type: research
tags: [manicure, alp-2066, ui-review, visual-acceptance]
summary: Read-only review of ALP-2074 and legacy preview removal effects in the detached manicure worktree found no UI acceptance blockers.
status: active
source: codebase-analyst
confidence: high
created: 2026-04-28
updated: 2026-04-28
---

## Executive Summary

Reviewed the detached worktree `/tmp/manicure-alp-2066-review` at `d7f45cb` against base `f21b0c4`, scoped to ALP-2074 UI and visual acceptance. fmm was attempted first, but the detached worktree is not indexed, so inspection fell back to read-only shell and targeted source reads.

## Project Metadata

- Project: Manicure
- Area: `www` React UI
- Worktree: `/tmp/manicure-alp-2066-review`
- Reviewed commit: `d7f45cb80b4ec31b4a3b6b114c521532b5246266`
- Base: `f21b0c4`
- fmm status: not indexed for detached worktree. `fmm_file_outline` reported files missing from index.

## Detailed Findings

No blockers found.

Acceptance evidence:

- `ExchangeTurnCard` imports `useTurnContent` at `www/src/components/ExchangeTurnCard.tsx:2` and calls it from `SettledTurnContentPreview` at `www/src/components/ExchangeTurnCard.tsx:181-182`, with `entry.id` passed at `www/src/components/ExchangeTurnCard.tsx:313-315`.
- Settled content renders two side by side columns with `grid-cols-2` at `www/src/components/ExchangeTurnCard.tsx:183-195`.
- User content reads `data?.user_text` at `www/src/components/ExchangeTurnCard.tsx:185-187`.
- Response content reads `data?.response_text` and passes `data?.stop_reason` at `www/src/components/ExchangeTurnCard.tsx:188-193`.
- Loading ellipsis and silent dash fallback are implemented at `www/src/components/ExchangeTurnCard.tsx:172-178`.
- Open rows still use the transport activity path and settled rows use `SettledTurnContentPreview` at `www/src/components/ExchangeTurnCard.tsx:285-315`.
- No `user_prompt_preview`, `min-h-[196px]`, `line-clamp-3`, `max-h-[60px]`, or old middle grid token remained under `www/src` or visual tests.
- `ExchangeList` row height is `250` at `www/src/components/ExchangeList.tsx:24-25`, consumed by the virtualizer at `www/src/components/ExchangeList.tsx:164-168`.
- Exchange card min height tokens use `min-h-[250px]` at `www/src/components/ExchangeTurnCard.tsx:233`, `241`, `248`, and `254`.
- Card rows use `grid-rows-[58px_140px_48px]` at `www/src/components/ExchangeTurnCard.tsx:254`.
- `ExchangePreview` has `MAX_LINES = 5` at `www/src/components/ExchangePreview.tsx:17`, mono `max-h-[100px]` at `www/src/components/ExchangePreview.tsx:76`, and plain `line-clamp-5` at `www/src/components/ExchangePreview.tsx:88`.
- Tests were updated for lazy two column previews, loading placeholders, fetch skipping for pending rows, and five line preview classification at `www/src/components/ExchangeList.test.tsx:574-619` and `www/src/components/ExchangePreview.test.tsx:13-29`.
- New hook and API tests cover `/turn-content` at `www/src/hooks/useTurnContent.test.tsx:11-45` and `www/src/api.test.ts:18-36`.
- Visual snapshot was updated: `www/tests/visual/exchange-list-anchored.spec.ts-snapshots/exchange-list-anchored-subagent-visual-darwin.png`.

## UI Ship Readiness

Ready for UI ship from this review scope. No visual acceptance blockers found. Tests were inspected but not executed in this read-only review.

## Open Questions

- None for the requested UI and visual scope.
