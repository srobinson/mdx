---
title: ALP 2074 and ALP 2076 agent review for Manicure
type: research
tags: [manicure, linear, agent-review, frontend, verification]
summary: Read only review found stale row height line references, ExchangePreview test omissions, snapshot path drift, and manual smoke command drift.
status: active
source: codebase-analyst
confidence: high
created: 2026-04-28
updated: 2026-04-28
---

## Executive Summary

Reviewed Linear ALP 2074 and ALP 2076 against the current Manicure codebase. The implementation targets still exist, but several Linear details are stale or incomplete, especially line references, min height token counts, preview line count tests, snapshot path naming, and manual smoke commands.

## Project Metadata

- Repo: `/Users/alphab/Dev/LLM/DEV/helioy/manicure`
- Topology from fmm: 296 files, 57,233 LOC, split into `api/` and `www/`
- Frontend: React 19, TanStack Query, TanStack Virtual, Vite, Vitest, Playwright
- Backend: Python 3.12 plus FastAPI, Pydantic, mitmproxy, uv, pytest, mypy

## Detailed Findings

### ALP 2074

- File paths are current: `www/src/components/ExchangeTurnCard.tsx`, `ExchangeList.tsx`, `ExchangeList.test.tsx`, `ExchangePreview.tsx`, `ExchangePreview.test.tsx`.
- Class and symbol names are current: `ExchangeTurnCard`, `ExchangePreview`, `ExchangeList`.
- `EXCHANGE_ROW_HEIGHT` is still 196 at `www/src/components/ExchangeList.tsx:25`.
- `ExchangeTurnCard` has four lines containing `min-h-[196px]`, but five class tokens. Lines: `www/src/components/ExchangeTurnCard.tsx:197`, `:205`, `:212`, `:218`. Line 218 contains two tokens.
- The described line references for min height replacement are stale. Current line numbers are around 197 through 218, not 246 through 267.
- The grid row class is current at `www/src/components/ExchangeTurnCard.tsx:218`.
- `ExchangeTurnCard` still reads `entry.user_prompt_preview` at `www/src/components/ExchangeTurnCard.tsx:279` and `:280`.
- `useTurnContent` does not exist yet under `www/src/hooks/`, consistent with ALP 2074 being blocked by ALP 2072.
- `ExchangePreview` has `MAX_LINES = 3` at `www/src/components/ExchangePreview.tsx:17`, mono overflow `max-h-[60px]` at `:76`, and plain text `line-clamp-3` at `:88`.
- The Linear description covers the JSON truncation assertion at `www/src/components/ExchangePreview.test.tsx:27`, but misses the earlier line count assertion at `:19`. Both need to move from 4 to 6 if `MAX_LINES` becomes 5.
- If the intent is to use the taller row for plain previews too, update `line-clamp-3` at `www/src/components/ExchangePreview.tsx:88` to `line-clamp-5`, or explicitly say the 5 line bump only applies to mono previews.

### ALP 2076

- Backend verification command is plausible. Repo `api/justfile` uses `uv run mypy src/` and `uv run pytest` at `api/justfile:50` through `:66`; the issue uses `uv run mypy src/manicure && uv run pytest`.
- Frontend typecheck command should follow the repo script. `www/package.json:25` defines `typecheck` as `tsc -b --noEmit`; `www/tsconfig.json:1` through `:10` is a references file. Prefer `pnpm typecheck` or `npx tsc -b --noEmit` over `npx tsc --noEmit`.
- Playwright command is plausible. `www/playwright.config.ts:25` through `:33` defines chromium, firefox, webkit, and visual projects. `npx playwright test` runs all configured projects.
- Snapshot path in the Files section is stale. Current Playwright snapshot directories use `*.spec.ts-snapshots`, not `__snapshots__`. The likely affected file exists at `www/tests/visual/exchange-list-anchored.spec.ts-snapshots/exchange-list-anchored-subagent-visual-darwin.png`.
- The test level screenshot name is current: `www/tests/visual/exchange-list-anchored.spec.ts:38` uses `exchange-list-anchored-subagent.png`.
- Manual smoke command is stale. Root `justfile:30` requires `just dev <claude|codex> [directory]`. The helper script pins proxy 8787 and web 8788 at `scripts/local-dev-mode.sh:28` through `:37`. Use `just dev claude` and `ANTHROPIC_BASE_URL=http://localhost:8787 claude -p "say hi"`.
- The curl port in the manual smoke step is stale. Direct API should use web port 8788, or the Vite proxy on 5173. The API mount at `/api` is correct via `api/src/manicure/main.py:84` and `api/src/manicure/api/v1/router.py:6`.

## Recommended Linear Patch Text

### ALP 2074 patch

Replace the card dimensions and MAX_LINES sections with:

```markdown
### Card dimensions

* In `www/src/components/ExchangeList.tsx`, bump `EXCHANGE_ROW_HEIGHT` from 196 to 250.
* In `www/src/components/ExchangeTurnCard.tsx`, replace every `min-h-[196px]` class token with `min-h-[250px]`. Current state: four lines contain the class and one line contains two tokens. Verify with `grep -c "min-h-\\[250px\\]" www/src/components/ExchangeTurnCard.tsx` equals 4 and `rg -o "min-h-\\[250px\\]" www/src/components/ExchangeTurnCard.tsx | wc -l` equals 5.
* Replace `grid-rows-[58px_minmax(86px,auto)_48px]` with `grid-rows-[58px_140px_48px]`.
```

Replace the MAX_LINES test note with:

```markdown
### MAX_LINES bump

* In `www/src/components/ExchangePreview.tsx`, bump `MAX_LINES` from 3 to 5.
* Bump mono overflow from `max-h-[60px]` to `max-h-[100px]`.
* If plain text and XML previews should also use the taller row, change `line-clamp-3` to `line-clamp-5`.
* Update `www/src/components/ExchangePreview.test.tsx`: both line count assertions that currently expect 4 rendered lines should expect 6, and the ellipsis index should move from 3 to 5.
```

### ALP 2076 patch

Replace the verification list with:

```markdown
1. Backend: `cd api && uv run mypy src/manicure && uv run pytest`.
2. Frontend: `cd www && pnpm typecheck && pnpm test` or `cd www && npx tsc -b --noEmit && npx vitest run`.
3. Playwright: `cd www && npx playwright test`. Card height changes and the middle row layout change can affect visual snapshots. Review diffs; if intentional, update with `cd www && npx playwright test --project=visual --update-snapshots`. Most likely affected snapshot file: `www/tests/visual/exchange-list-anchored.spec.ts-snapshots/exchange-list-anchored-subagent-visual-darwin.png`.
4. Manual smoke: `just dev claude`, send one Anthropic request through `ANTHROPIC_BASE_URL=http://localhost:8787 claude -p "say hi"`, navigate to the inspector, and confirm both columns populate. Confirm the legacy preview field is gone from the index payload with `curl -s localhost:8788/api/exchanges | jq '.[0]'`; the API mounts at `/api`, not `/api/v1`.
5. Commit intentional Playwright baseline updates separately.
```

Replace the Files section with:

```markdown
## Files

* Possibly modify: `www/tests/visual/*.spec.ts-snapshots/*` for accepted Playwright baselines.
```

## Open Questions

- ALP 2074 should decide whether plain and XML previews should also expand from 3 to 5 visual lines via `line-clamp-5`.
