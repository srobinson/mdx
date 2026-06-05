---
title: Transport Matters Slice 8 Delta Verification
type: research
tags: [transport-matters, transcript-canvas, slice-8, delta-verification, frontend]
summary: Slice 8 consensus fixes at 648deb4 were verified green against b0368a7, and the bus reply was sent.
status: active
source: codebase-analyst
confidence: high
created: 2026-06-09
updated: 2026-06-09
---

## Executive Summary

Slice 8 delta verification passed on branch `feat/transcript-canvas-slice-8` at `648deb4b22cafbb4a497ac0bf38fcaafdfeb24c1`. The required consensus fixes from `review-slice-8.md` are closed, the requested frontend gate is green, and the bus reply `deltas verified` was delivered to `transport-matters:general:1:2.1`.

## Project Metadata

- Repository: `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters`
- Branch: `feat/transcript-canvas-slice-8`
- Delta verified: `git diff b0368a7 648deb4`
- Frontend package: `www`
- Stack: React, TypeScript, Vite, Vitest, pnpm
- Structural index: `.fmm.db` present at repo root, and `fmm_list_files` reported `www/src` as 233 files and 28,237 LOC

## Architecture

Slice 8 wires real resource viewers into the transcript canvas. The delta changes the stylesheet ownership model from entry point side effects to viewer local side effects: `www/src/main.tsx:5-7` now imports only global canvas and placeholder styles, while each resource viewer or primitive imports its own co-located CSS.

This matters because the canvas route is lazy loaded. CSS owned by the viewer module becomes reachable only when that viewer is reachable, which keeps style reachability tied to render reachability rather than a manual global list.

## Key Patterns

- CSS reachability is now structural. `cssColocation.test.ts` recursively discovers every resource viewer stylesheet and requires a sibling source module to import it.
- URL sanitization is shared. Markdown links and binary download actions use the same `safeHref` primitive.
- Truncation copy is centralized. `TruncationNote` owns the default wording and lets markdown pass its source specific variant.

## Detailed Findings

### M1 closed: exchange viewer CSS is reachable

Original condition: `review-slice-8.md:60-64` required closing the missing `exchange-viewer.css` import.

Evidence:

- `www/src/main.tsx:5-7` no longer carries the six resource viewer stylesheet imports.
- `www/src/session-canvas/viewers/resource/ProviderExchangeResourceViewer.tsx:1-3` imports `./exchange-viewer.css` directly.
- `ProviderExchangeResourceViewer.tsx:19-21` renders the `canvas-exchange` wrapper that depends on that stylesheet.
- `www/src/session-canvas/viewers/resource/cssColocation.test.ts:10-20` recursively discovers CSS files, `:23-28` finds co-located non-test modules, and `:45-53` asserts every stylesheet has at least one sibling importer.
- A temp fail-before run copied the new `cssColocation.test.ts` into the `b0368a7` resource tree and ran Vitest with `--root` pointing at that tree. It exited `EXPECTED_FAIL_EXIT=1` with 7 failing cases, including `exchange-viewer.css is imported by a co-located module`. This proves the guard would have caught the original missing import pattern.
- The same algorithm over the current tree reported `missing_count=0` for all 7 resource CSS files.
- The production build CSS includes `.canvas-exchange` in `api/src/transport_matters/www/assets/SessionCanvasRoute-BvFrpCQf.css`.

### m1 closed: binary download URL uses shared `safeHref`

Evidence:

- `www/src/session-canvas/viewers/resource/primitives/safeHref.ts:7-21` owns the shared scheme allowlist.
- `BinaryResourceViewer.tsx:3` imports `safeHref` and `:31` computes `downloadHref` before rendering a navigable anchor.
- `BinaryResourceViewer.tsx:43-48` uses the sanitized `downloadHref` for the `<a href>`.
- `BinaryResourceViewer.test.tsx:56-63` covers an unsafe `javascript:alert(1)` download URL degrading to a disabled button with no link.
- `markdown.tsx:2` imports the same primitive, and the markdown renderer calls it at `markdown.tsx:202`.

### m2 closed: truncation note is shared

Evidence:

- `www/src/session-canvas/viewers/resource/primitives/TruncationNote.tsx:3-21` defines `TRUNCATION_NOTE` and the shared `TruncationNote` component.
- `TextResourceViewer.tsx:5,26` imports and uses `TruncationNote` for default truncation copy.
- `JsonResourceViewer.tsx:6,46` imports and uses `TruncationNote` for default truncation copy.
- `MarkdownResourceViewer.tsx:6,42-46` uses the same component with its source specific message.

### Required negative checks passed

- `git diff --name-only b0368a7 648deb4 -- www/src/index.css` produced no changed file, so `index.css` was untouched.
- Repo-wide `rg -n 'dangerouslySetInnerHTML' .` returned no matches.
- `rg -n 'innerHTML' www/src` returned no matches.
- `git status --short` was empty after verification and build.

## Verification Commands

Observed command and result:

```bash
cd www && pnpm lint && pnpm typecheck && pnpm test && pnpm build
```

Result:

- Biome checked 269 files with no fixes applied.
- Vitest reported 83 passed test files and 537 passed tests.
- Vite build completed and emitted `SessionCanvasRoute-BvFrpCQf.css`, which contains `.canvas-exchange`.
- Wrapper printed `EXIT=0`.

Fail-before probe:

```bash
pnpm exec vitest run src/session-canvas/viewers/resource/cssColocation.test.ts --root "$tmp/www" --reporter=dot
```

Result against the temp `b0368a7` resource tree with the new test copied in:

- `EXPECTED_FAIL_EXIT=1`
- 7 failed cases, including `exchange-viewer.css is imported by a co-located module`

## Dependencies

- React provides the viewer component model.
- Vitest provides the CSS co-location regression guard and viewer tests.
- Vite owns production asset generation, including the CSS bundle checked for `.canvas-exchange`.
- pnpm runs the frontend scripts.

## Relevance to Helioy

This delta hardens the transcript canvas viewer layer. The CSS co-location guard is a useful Helioy pattern for lazy loaded UI surfaces where missing side effect imports can ship unstyled panes while lint, typecheck, and ordinary tests remain green.

## Open Questions

None for the requested delta verification.
