---
title: ALP-2045 visual fixture split review for Manicure
type: research
tags: [manicure, alp-2045, visual-regression, playwright, fixtures]
summary: ALP-2045 preserves the visual fixture split and barrel contract, but current visual snapshots are stale for unrelated visible state and must be updated or reviewed separately.
status: active
source: codebase-analyst
confidence: high
created: 2026-04-27
updated: 2026-04-27
---

## Executive Summary

ALP-2045 is structurally correct: the monolithic visual fixture file was split into time, paused flow, exchanges, details, and setup modules while keeping the `www/tests/visual/fixtures.ts` barrel. Visual verification is not green, but the failures appear to be stale snapshot baselines for current UI state, not a fixture split regression.

## Project Metadata

- Worktree: `/Users/alphab/Dev/LLM/DEV/helioy/manicure-worktrees/nancy-ALP-2019`
- Branch: `nancy/ALP-2019`
- Frontend: React 19, Vite 8, Playwright visual project
- fmm status: `.fmm.db` present

## Architecture

ALP-2045 moves visual test fixture ownership into focused modules:

- Barrel: `www/tests/visual/fixtures.ts:1-5`
- Time fixtures: `www/tests/visual/fixtures/time.ts:1-7`
- Paused flow fixture: `www/tests/visual/fixtures/pausedFlow.ts:1-43`
- Exchange index fixtures: `www/tests/visual/fixtures/exchanges.ts:6-130`
- Exchange detail fixtures: `www/tests/visual/fixtures/details.ts:8-404`
- Playwright setup: `www/tests/visual/fixtures/setup.ts:36-114`

Existing visual specs still import from `./fixtures`, so import compatibility is preserved.

## Detailed Findings

### Fixture split correctness

The split matches the ALP-2045 spec.

- `www/tests/visual/fixtures.ts:1-5` remains a barrel export.
- `setupVisualTest` owns `page.clock`, `EventSource`, persisted selected exchange state, and API route fulfillment at `www/tests/visual/fixtures/setup.ts:36-114`.
- `mockExchanges` order and IDs match the pre split monolith content from `28096fe^:www/tests/visual/fixtures.ts`.
- `mockCodexTransportSuccessId`, `mockCodexTimelineOpenId`, and `mockCodexTransportDiagnosticId` still derive from `mockExchanges[2]`, `[3]`, and `[4]` at `www/tests/visual/fixtures/exchanges.ts:128-130`.

### Visual test result

Command run:

```bash
pnpm --dir www exec playwright test --project=visual --reporter=list --output=/tmp/mx-visual-all
```

Result: 4 passed, 8 failed.

Passing:

- `exchange-detail-header.spec.ts`, clean and edited cases.
- `exchange-detail-timeline.spec.ts`, completed and open timeline cases.

Failing:

- `exchange-detail-transport.spec.ts`, 2 cases.
- `paused-header.spec.ts`, 4 widths.
- `top-bar.spec.ts`, 2 arm states.

### Visual interpretation

The failures are large enough to reject automatic acceptance of the current snapshots, but they do not indicate ALP-2045 broke fixture wiring.

Observed diff causes:

- Expected paused header snapshots show older left list content, including `transport-handshake` first and `EXCHANGES 4`.
- Actual paused header snapshots show current data ordering with `claude-sonnet-4-5` first and `EXCHANGES 5`.
- Expected top bar snapshots show older version/count text. Actual top bar shows current branch version/count text.
- Transport detail actual renders the intended selected Codex entries from `mockCodexTransportSuccessId` and `mockCodexTransportDiagnosticId`, so selected fixture IDs still route correctly.

This points to stale snapshot baselines from previous UI or data behavior changes, not a regression introduced by splitting the fixture file.

## Key Patterns

Good pattern: fixture modules now have a single responsibility and the old import surface remains stable through a barrel.

Risk pattern: visual snapshots include volatile UI header state such as version strings and exchange counts. These should be intentionally accepted or masked, otherwise unrelated behavior changes will keep invalidating fixture refactors.

## Recommendation

Accept ALP-2045 as a fixture decomposition if code review is the criterion. Do not call visual verification fully green until the 8 failing snapshots are reviewed and updated intentionally.

Preferred next step:

1. Review `/tmp/mx-all-failures-contact.png` or regenerate with the command above.
2. If current UI state is intended, update the 8 affected snapshots in a separate explicit visual baseline update.
3. Consider reducing volatile top bar text in screenshots if it is not the visual contract being tested.

## Open Questions

1. Should the visual baselines be updated as part of ALP-2045 acceptance, or tracked as a separate snapshot refresh after ALP-2019 ordering and version changes?
2. Should visual tests mask the version string or exchange count to reduce unrelated failures?

## Decision

Stuart selected option 1: handle the failing visual snapshots as a separate explicit visual baseline refresh. ALP-2045 remains accepted for fixture decomposition. The snapshot update should be reviewed as its own intentional visual change, not folded silently into the fixture split review.

Suggested refresh command:

```bash
pnpm --dir www exec playwright test --project=visual --update-snapshots
```

Expected affected baseline families:

- `www/tests/visual/exchange-detail-transport.spec.ts-snapshots/`
- `www/tests/visual/paused-header.spec.ts-snapshots/`
- `www/tests/visual/top-bar.spec.ts-snapshots/`

Acceptance criteria for the follow up:

1. Snapshot diffs are reviewed visually before committing.
2. Only intentional baseline PNGs change.
3. `pnpm --dir www test:visual` passes after the refresh.

## Attribution Check Against Earlier ALPs

Question: are the current visual failures caused by ALP-2045, or by earlier ALP-2023, ALP-2025, ALP-2026, or ALP-2024 work?

Method:

- Created temporary detached worktrees under `/tmp/mx-visual-attrib`.
- Reused the current `www/node_modules` via symlink to avoid reinstalling dependencies.
- Ran `pnpm --dir www exec playwright test --project=visual --reporter=list` at these commits:
  - `e7dccaa`: main before ALP-2020
  - `8a8b2bb`: after ALP-2023
  - `d5ab380`: after ALP-2025
  - `fdea6d1`: after ALP-2026
  - `39f0e0b`: after ALP-2024
  - `a44b138`: after ALP-2019 ordering flip
  - `c392ffc`: before ALP-2045
  - `28096fe`: after ALP-2045
  - `3711310`: current head

Result:

- Every checked commit produced the same pass/fail shape: 12 visual tests run, 4 passed, 8 failed.
- Therefore the baseline mismatch was already present at `e7dccaa`, before ALP-2023, ALP-2025, ALP-2026, ALP-2024, and ALP-2045.
- The ALP-2023 through ALP-2024 commits only changed the generated actual screenshots in the header version/hash region. They did not account for the layout/content mismatch.
- ALP-2019 ordering flip at `a44b138` introduced the large content/layout change where the left list ordering and selected exchange region changed. This is separate from ALP-2045 and separate from the specific ALP-2023/2025/2026/2024 commits named in the question.
- ALP-2045 changed only the header commit/version text in the generated actuals. `before-alp2045` to `after-alp2045` diffs are confined to the top header version/hash bbox, not the fixture-rendered body content.

Conclusion:

The visual failures are not caused by ALP-2045. They are also not first caused by ALP-2023, ALP-2025, ALP-2026, or ALP-2024. The suite was already stale before that sequence. The later large visible state change aligns with ALP-2019 ordering behavior, not the ALP-2045 fixture split.

## Snapshot Refresh Executed

Stuart approved regenerating the stale visual baselines after the attribution check showed ALP-2045 did not cause the failures.

Commands run from `/Users/alphab/Dev/LLM/DEV/helioy/manicure-worktrees/nancy-ALP-2019`:

```bash
pnpm --dir www exec playwright test --project=visual --update-snapshots
pnpm --dir www test:visual
```

Result:

- Snapshot update command: 12 passed, 8 snapshots regenerated.
- Verification command: 12 passed.
- Changed files are exactly the 8 expected PNG baselines:
  - `www/tests/visual/exchange-detail-transport.spec.ts-snapshots/exchange-detail-transport-codex-visual-darwin.png`
  - `www/tests/visual/exchange-detail-transport.spec.ts-snapshots/exchange-detail-transport-diagnostics-visual-darwin.png`
  - `www/tests/visual/paused-header.spec.ts-snapshots/paused-1000-visual-darwin.png`
  - `www/tests/visual/paused-header.spec.ts-snapshots/paused-1200-visual-darwin.png`
  - `www/tests/visual/paused-header.spec.ts-snapshots/paused-1440-visual-darwin.png`
  - `www/tests/visual/paused-header.spec.ts-snapshots/paused-1920-visual-darwin.png`
  - `www/tests/visual/top-bar.spec.ts-snapshots/topbar-armed-visual-darwin.png`
  - `www/tests/visual/top-bar.spec.ts-snapshots/topbar-disarmed-visual-darwin.png`

Visual contact sheet for local review was generated at `/tmp/mx-updated-snapshots-contact.png`.

