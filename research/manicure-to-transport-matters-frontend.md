---
title: Manicure to Transport Matters Frontend Rename Scan
type: research
tags: [manicure, transport-matters, frontend, rename, react, vite]
summary: Narrow tracked frontend scan found 56 case insensitive Manicure occurrences across 22 files, with risk concentrated in visible labels, ManicureIcon, local storage keys, Vite globals, and test selectors.
status: active
source: codebase-analyst
confidence: high
created: 2026-04-29
updated: 2026-04-29
---

## Executive Summary

Tracked frontend scope contains 139 files. I found 56 case insensitive `manicure` occurrences across 22 files in the requested scope.

The rename surface is concentrated in browser visible brand labels, `ManicureIcon`, local storage keys, Vite version globals, package metadata, and tests. CSS, route names, Playwright config, Biome config, tsconfig files, and `www/README.md` have no `manicure` hits in the narrowed tracked scope.

## Scope and Method

Scope was limited to tracked files from:

- `www/src/**`
- `www/tests/**`
- `www/package.json`
- `www/vite.config.ts`
- `www/index.html`
- `www/README.md`
- `www/playwright.config.ts`
- `www/biome.json`
- `www/tsconfig*.json`

Excluded: `node_modules`, caches, dist artifacts, `test-results`, and `playwright-report`.

fmm was used first for structure. fmm reports `www/` as 118 indexed files and 19,019 LOC, with 103 indexed files under `www/src/`. `ManicureIcon` is defined at `www/src/components/ManicureIcon.tsx:1-22` and imported by `app.tsx`, `OverlaysView.tsx`, `RecallView.tsx`, and `TraceView.tsx`.

## Exact Counts

Overall:

- Tracked files in narrowed scope: 139
- Files with case insensitive `manicure`: 22
- Total case insensitive `manicure` occurrences: 56

Category counts are overlapping by design because one occurrence can be both a test selector and a visible brand assertion.

| Category | Occurrences | Notes |
| --- | ---: | --- |
| Visible UI branding and accessible labels | 13 | Product title, headings, SVG title, console copy, operator text |
| Component and icon naming | 18 | `ManicureIcon` symbol, imports, usages |
| API client comments and constants | 10 | API path comments, CLI comments, version globals |
| Local storage keys | 8 | Zustand keys, dismissed panel prefix, tests, visual setup |
| Build time globals and paths | 7 | `MANICURE_VERSION`, `__MANICURE_VERSION__`, Vite output path |
| Test selectors and fixtures | 16 | Unit selectors, visual selectors, fixture cwd, local storage, proxy text |
| Package metadata | 1 | `www/package.json` name |
| Lowercase runtime or comments | 19 | Package name, storage keys, comments, fixture values |

Per file occurrence counts:

| Count | File |
| ---: | --- |
| 8 | `www/src/app.tsx` |
| 5 | `www/src/components/routes/RecallView.tsx` |
| 5 | `www/src/components/routes/TraceView.tsx` |
| 4 | `www/vite.config.ts` |
| 4 | `www/src/components/routes/OverlaysView.tsx` |
| 4 | `www/src/components/editor/DismissablePanel.test.tsx` |
| 3 | `www/src/components/ManicureIcon.tsx` |
| 3 | `www/tests/visual/fixtures/details.ts` |
| 2 | `www/src/api.ts` |
| 2 | `www/src/vite-env.d.ts` |
| 2 | `www/src/lib/formatting.test.ts` |
| 2 | `www/src/components/detail/mutations.ts` |
| 2 | `www/tests/visual/top-bar.spec.ts` |
| 2 | `www/tests/visual/fixtures/setup.ts` |
| 1 | `www/index.html` |
| 1 | `www/package.json` |
| 1 | `www/src/app.test.tsx` |
| 1 | `www/src/stores/overlaysStore.ts` |
| 1 | `www/src/stores/uiStore.ts` |
| 1 | `www/src/components/exchangeListRows.ts` |
| 1 | `www/src/components/detail/CodexTimeline.tsx` |
| 1 | `www/src/components/editor/DismissablePanel.tsx` |

No hits in:

- `www/README.md`
- `www/playwright.config.ts`
- `www/biome.json`
- `www/tsconfig.json`
- `www/tsconfig.app.json`
- `www/tsconfig.node.json`
- `www/src/index.css`

## Key Line References

### Visible UI branding

- `www/index.html:10`, browser title is `Manicure`.
- `www/src/app.tsx:56`, top bar heading is `Manicure`.
- `www/src/app.tsx:127`, waiting state heading is `Manicure`.
- `www/src/components/ManicureIcon.tsx:9`, SVG `aria-label` is `Manicure`.
- `www/src/components/ManicureIcon.tsx:11`, SVG `<title>` is `Manicure`.
- `www/src/components/detail/CodexTimeline.tsx:86`, timeline summary starts with `Manicure applied`.
- `www/src/components/exchangeListRows.ts:76`, dev warning starts with `Manicure ExchangeList`.
- `www/tests/visual/fixtures/details.ts:397`, fixture operator text says `Manicure proxy`.

### Component and icon naming

- `www/src/components/ManicureIcon.tsx:1`, exports `ManicureIcon`.
- `www/src/app.tsx:6`, imports `./components/ManicureIcon`.
- `www/src/app.tsx:54`, `:121`, `:125`, renders `ManicureIcon`.
- `www/src/components/routes/OverlaysView.tsx:5`, `:97`, `:108`, imports and renders `ManicureIcon`.
- `www/src/components/routes/RecallView.tsx:1`, `:21`, `:27`, imports and renders `ManicureIcon`.
- `www/src/components/routes/TraceView.tsx:1`, `:21`, `:27`, imports and renders `ManicureIcon`.

### API client strings and build time globals

- `www/src/api.ts:76`, comment references `api/src/manicure/api/v1/exchanges.py`.
- `www/src/api.ts:251`, comment references `manicure start`.
- `www/vite.config.ts:7`, `:11`, uses `MANICURE_VERSION`.
- `www/vite.config.ts:27`, defines `__MANICURE_VERSION__`.
- `www/src/vite-env.d.ts:3`, `:5`, declares the same build global.
- `www/src/app.tsx:60`, renders `v{__MANICURE_VERSION__}`.
- `www/vite.config.ts:43`, build output is `../api/src/manicure/www`.

### Local storage keys

- `www/src/stores/uiStore.ts:87`, persisted store key is `manicure-ui`.
- `www/src/stores/overlaysStore.ts:147`, persisted store key is `manicure-overlays`.
- `www/src/components/editor/DismissablePanel.tsx:6`, key prefix is `manicure.panel.dismissed.`.
- `www/tests/visual/fixtures/setup.ts:70`, visual fixture writes `manicure-ui`.
- `www/src/components/editor/DismissablePanel.test.tsx:22`, `:44`, `:66`, `:67`, tests assert dismissed panel keys.

### Test selectors and fixtures

- `www/src/app.test.tsx:118`, asserts heading named `Manicure`.
- `www/tests/visual/top-bar.spec.ts:10`, `:22`, waits for heading named `Manicure`.
- `www/src/lib/formatting.test.ts:12`, fixture cwd includes `helioy/manicure`.
- `www/tests/visual/fixtures/setup.ts:9`, fixture cwd includes `manicure-worktrees`.
- `www/tests/visual/fixtures/details.ts:68`, fixture header value is `manicure`.
- `www/tests/visual/fixtures/details.ts:399`, fixture guidance says `manicure codex --debug`.

### Package metadata

- `www/package.json:2`, package name is `manicure`.

## Rename Risks

- **Persistent state loss:** Renaming `manicure-ui`, `manicure-overlays`, or `manicure.panel.dismissed.` resets user route selection, overlay drafts, and dismissed notices unless migrated. `DismissablePanel.tsx:3-6` explicitly warns the prefix is stable and a rename resets dismissals.
- **Build packaging break:** `www/vite.config.ts:43` outputs into `api/src/manicure/www`. Changing this before the backend package path changes will break wheel asset placement.
- **Global name compatibility:** `MANICURE_VERSION` and `__MANICURE_VERSION__` are used across config, types, and UI. A rename should account for release scripts and any external build environment.
- **Visual snapshot churn:** Top bar and icon changes affect Playwright visual baselines. Snapshot file names do not contain `manicure`, but rendered pixels and selectors do.
- **Concept collision:** Lowercase `transport` already means HTTP or websocket transport in the app. Use `Transport Matters` for brand UI and reserve `transport` for protocol concepts.
- **Fixture truth:** `x-openai-proxy: manicure` in `www/tests/visual/fixtures/details.ts:68` may be captured protocol evidence. Coordinate before rewriting it as brand text.

## Recommended Sequencing

1. Confirm new casing for browser UI. Recommended display label is `Transport Matters`; use `transport-matters` only for package and path identifiers.
2. Rename visible labels and icon accessibility together: `index.html`, `app.tsx`, and `ManicureIcon.tsx`.
3. Decide whether `ManicureIcon` becomes `TransportMattersIcon` with the same SVG, or whether the icon asset changes. Rename imports in the three placeholder routes at the same time.
4. Handle local storage as a deliberate migration. Either preserve old keys with a one time migration or accept a documented preference reset.
5. Rename Vite globals and package metadata only after release scripts and backend output path are ready. Keep a temporary `MANICURE_VERSION` fallback if builds may still set it.
6. Update tests and fixtures after implementation. Rebaseline visual snapshots after visible brand or icon changes.

## Work Log

- Interrupted prior broad scan and narrowed to tracked frontend files only.
- Recomputed counts from `git ls-files` under the requested scope.
- Wrote this artifact only. The target repo was not modified.
- `session-logger` skill is not available in this session, so this Work Log is included here.
