---
title: Linear ALP-2018 stale reference review for Manicure
type: research
tags: [manicure, linear, frontend, playwright, snapshots]
summary: ALP-2018 references were current except a stale line-specific useExchangeStream reference, which was replaced with a stable file reference.
status: active
source: codebase-analyst
confidence: high
created: 2026-04-27
updated: 2026-04-27
---

## Executive Summary

Reviewed Linear issue ALP-2018 against the current Manicure repo after frontend refactoring. All referenced frontend files, components, fields, fixtures, Playwright specs, test ids, and snapshot filenames were current except one stale line number on the `useExchangeStream` invalidation reference.

## Project Metadata

- Repo: `/Users/alphab/Dev/LLM/DEV/helioy/manicure`
- Topology from fmm: `api/` and `www/`, 288 indexed files, 54,626 LOC
- Frontend area checked: `www/src/components`, `www/src/hooks`, `www/src/types.ts`, `www/tests/visual`
- Linear issue: ALP-2018, parent ALP-2006

## Architecture

Relevant frontend surfaces:

- `www/src/components/ExchangeDetail.tsx` owns the detail pane, header chips, tabs, `JsonView` usage, and `fetchExchange(id)` query.
- `www/src/types.ts` defines `IndexEntry`, `ExchangeDetail`, `CodexTurnListSummary`, and `CodexTurnSummary`.
- `www/src/hooks/useExchangeStream.ts` updates exchange list cache entries and invalidates the detail query on broadcasts.
- `www/tests/visual/fixtures/exchanges.ts` and `www/tests/visual/fixtures/details.ts` define visual fixture rows and detail payloads.
- `www/tests/visual/exchange-detail-timeline.spec.ts` and `www/tests/visual/exchange-detail-transport.spec.ts` own the affected visual snapshots.

## Detailed Findings

| Reference | Status before update | Evidence from current code | Replacement applied |
| --- | --- | --- | --- |
| `www/src/components/ExchangeDetail.tsx` | Current | File exists and exports `ExchangeDetail`; header chip rendering remains in this component. | None |
| `www/src/components/ExchangeDetail.test.tsx` | Current | File exists and mocks `fetchExchange` with provisional shape payloads containing `entry.res: null` and `response_ir: null`. | None |
| `ExchangeDetail` | Current | Component file exists; type `ExchangeDetail` remains in `www/src/types.ts`. | None |
| `JsonView` and `No response data` | Current | `ExchangeDetail.tsx` imports `JsonView` from `./detail/JsonView` and renders `emptyLabel="No response data"`. | None |
| `response_ir` | Current | Field exists on `ExchangeDetail` in `www/src/types.ts`; `ExchangeDetail.tsx` disables the Response tab when `detail.response_ir == null`. | None |
| `detail.entry.codex_turn` and `entry.codex_turn` | Current | `IndexEntry` has optional `codex_turn?: CodexTurnListSummary | null` in `www/src/types.ts`. | None |
| `detail.turn` | Current | `ExchangeDetail` has optional `turn?: CodexTurnSummary | null` in `www/src/types.ts`; it is distinct from `IndexEntry.codex_turn`. | None |
| `CodexTurnListSummary` | Current | Type exists in `www/src/types.ts` with `status`, frame range, terminal cause, text, and tool call fields. | None |
| `CodexTurnSummary` | Current | Type exists in `www/src/types.ts` with detail payload fields including `turn_id`, `session_id`, timestamps, and cursor. | None |
| `fetchExchange` | Current | `www/src/api.ts` exports `fetchExchange`; `ExchangeDetail.tsx` uses it as the query function. | None |
| `screen.getByTestId("exchange-detail-waiting")` and `queryByTestId("exchange-detail-waiting")` | Planned, not stale | No current implementation exists, but ALP-2018 is asking to add this stable handle. | None |
| `queryClient.invalidateQueries({ queryKey: ["exchange", entry.id] })` | Current behavior, stale line-specific location | Invalidation exists in `www/src/hooks/useExchangeStream.ts`, but not at the old referenced line. | Replaced `(verified at www/src/hooks/useExchangeStream.ts:238)` with `(verified in www/src/hooks/useExchangeStream.ts)` |
| `www/tests/visual/exchange-detail-timeline.spec.ts` | Current | Spec exists and calls `toHaveScreenshot("exchange-detail-timeline-open-codex.png")`. | None |
| `www/tests/visual/exchange-detail-transport.spec.ts` | Current | Spec exists and calls `toHaveScreenshot("exchange-detail-transport-diagnostics.png")`. | None |
| `exchange-detail-timeline-open-codex-visual-darwin.png` | Current | Snapshot exists under `www/tests/visual/exchange-detail-timeline.spec.ts-snapshots/`. | None |
| `exchange-detail-transport-diagnostics-visual-darwin.png` | Current | Snapshot exists under `www/tests/visual/exchange-detail-transport.spec.ts-snapshots/`. | None |
| `mockCodexTimelineOpenId` fixture gate | Current and satisfies described gate | `mockCodexTimelineOpenId = mockExchanges[3].id`; `mockExchanges[3]` has `res: null` and no `codex_turn`, while detail payload has `turn.status: "open"`. | None |
| `mockCodexTransportDiagnosticId` fixture gate | Current and satisfies described gate | `mockCodexTransportDiagnosticId = mockExchanges[4].id`; `mockExchanges[4]` has `res: null` and no `codex_turn`, while detail payload has `turn: null`. | None |

## Linear Update

Updated ALP-2018 in place with one surgical edit:

- Before: `(verified at www/src/hooks/useExchangeStream.ts:238)`
- After: `(verified in www/src/hooks/useExchangeStream.ts)`

## Open Questions

- Snapshot filenames are platform-specific through Playwright. The issue references the current Darwin baseline names. No Linux or Chromium project specific variants were present in the checked snapshot folders.
