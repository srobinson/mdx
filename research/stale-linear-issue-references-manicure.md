---
title: Stale Linear Issue References in Manicure Frontend Cards
type: research
tags: [manicure, linear, frontend, testing]
summary: ALP-2015 and ALP-2016 were reviewed and updated for stale frontend list card references after refactoring.
status: active
source: codebase-analyst
confidence: high
created: 2026-04-27
updated: 2026-04-27
---

## Executive Summary

ALP-2015 and ALP-2016 were reviewed against the current Manicure frontend. Two stale reference groups were found and updated in Linear: the Codex terminal status literal and the current visual spec inventory.

## Project Metadata

- Repo: `/Users/alphab/Dev/LLM/DEV/helioy/manicure`
- Relevant area: `www/`
- Primary language: TypeScript with React, Vitest, Testing Library, and Playwright visual tests
- Structural index: fmm available for this repo

## Architecture

The list UI renders `ExchangeList` rows through `ExchangeTurnCard`. The waiting treatment is controlled by `ExchangeTurnCard` and observable through stable test IDs such as `exchange-row-${entry.id}`, `exchange-status-${entry.id}`, and `exchange-primary-metric-${entry.id}`. Visual fixtures live under `www/tests/visual/fixtures/`, with list shape in `exchanges.ts` and detail shape in `details.ts`.

## Key Patterns

- List row state uses the `IndexEntry` shape from `www/src/types.ts`.
- Codex detail payloads use `ExchangeDetail.turn`, separate from `IndexEntry.codex_turn`.
- Playwright visual specs are organized under `www/tests/visual/` and include both detail pane and list related coverage.

## Detailed Findings

### ALP-2015

Updated stale terminal status wording from `completed | failed | stopped` to `completed | failed | interrupted`.

Evidence:

- `www/src/types.ts` defines `CodexTurnStatus` as `"open" | "completed" | "failed" | "interrupted"`.
- `www/src/components/ExchangeTurnCard.tsx` maps `interrupted` to the displayed `STOPPED` label in `statusDisplay`.

### ALP-2016

Updated stale Playwright inventory wording.

Evidence:

- `www/tests/visual/exchange-list-anchored.spec.ts` exists, so the issue could no longer state that no list view Playwright spec exists.
- Existing visual specs include `exchange-detail-header.spec.ts`, `exchange-detail-timeline.spec.ts`, `exchange-detail-transport.spec.ts`, `top-bar.spec.ts`, and `paused-header.spec.ts`.

## Dependencies

- fmm MCP tools for structure and symbol lookup
- Linear MCP tools for issue retrieval and in place description updates

## Relevance to Helioy

This keeps Nancy worker issues aligned with current repo structure, reducing execution errors from stale file, type, fixture, and spec references.

## Open Questions

None for this scope. Ambiguous references were left unchanged unless clearly stale.
