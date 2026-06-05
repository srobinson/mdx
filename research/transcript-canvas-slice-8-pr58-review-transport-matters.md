---
title: Transcript Canvas Slice 8 PR58 Review
type: research
tags: [transport-matters, transcript-canvas, pr58, frontend, review]
summary: PR58 real resource viewers passed the frontend gate but needs one major CSS import fix and two minor hardening or DRY fixes before signoff.
status: active
source: codebase-analyst
confidence: high
created: 2026-06-09
updated: 2026-06-09
---

## Executive Summary

PR#58 implements real session canvas resource viewers for markdown, image, text, JSON, binary, native record JSON, and provider exchange content. The implementation passes the full frontend gate, but the provider exchange wrapper CSS is authored and never imported, so exchange panes ship without the only `.canvas-exchange` sizing rule.

## Project Metadata

- Project: `transport-matters`
- Branch: `feat/transcript-canvas-slice-8`
- PR: #58, head `b0368a7cd106de8a1271fe5c029a763d42bfeb36`
- Frontend: TypeScript, React, Vite, TanStack Query, Vitest, Biome
- Backend contract checked: Python FastAPI session resource content models via Pydantic camelCase aliases
- Gate run from `www`: `pnpm lint && pnpm typecheck && pnpm test && pnpm build`

## Architecture

Slice 8 adds a resource content client boundary at `www/src/session-canvas/api/resourceContent.ts`. The frontend response union mirrors the backend resource content union with camelCase payload fields such as `mediaType`, `contentProvenance`, `bytesBase64`, `tooLarge`, `downloadUrl`, `exchangeId`, and `initialView`. Query parameters remain snake case at `resourceContent.ts:118-120`.

`ResourcePane` fetches one resource through `useResourceContent`, maps the union through `resolveResourceContent`, then renders either a stable pane state or a concrete viewer. The viewer registry now routes resource refs to `ResourcePane` and provider exchange refs to `ProviderExchangeResourceViewer` while preserving registry owned dedupe keys at `www/src/session-canvas/viewers/registry.tsx:78-91`.

## Key Patterns

- Typed response union maps to a small viewer selection function in `www/src/session-canvas/viewers/resource/resourceState.ts:53-75`.
- Markdown rendering uses React nodes instead of raw HTML. `safeHref` rejects dangerous protocols and control characters at `www/src/session-canvas/viewers/resource/markdown.tsx:135-149`.
- Provider exchanges reuse `ExchangeDetail` through `ProviderExchangeResourceViewer`, with canvas passing a no-op `onMissing` and mapping `initialView` to existing detail tabs at `www/src/session-canvas/viewers/resource/ProviderExchangeResourceViewer.tsx:11-40`.
- Shared primitives exist for line numbered text, copy controls, and JSON tree rendering under `www/src/session-canvas/viewers/resource/primitives/`.

## Detailed Findings

### Gate proof

The full frontend gate passed from `www`:

- `pnpm lint`: exit 0
- `pnpm typecheck`: exit 0
- `pnpm test`: 81 files passed, 526 tests passed
- `pnpm build`: exit 0

### Major finding

**M1: `exchange-viewer.css` is never imported, so exchange pane wrapper styles are absent from the bundle.**

Evidence:

- `www/src/main.tsx:8-13` imports the resource primitive, markdown, text, JSON, image, and binary CSS files, but omits `exchange-viewer.css`.
- `www/src/session-canvas/viewers/resource/ProviderExchangeResourceViewer.tsx:19` renders `<div className="canvas-exchange">`.
- `www/src/session-canvas/viewers/resource/exchange-viewer.css:5-12` contains the only `.canvas-exchange` rule. It supplies full height flex column sizing and `overflow: hidden`.
- A post build probe found no `canvas-exchange` in `api/src/transport_matters/www/assets/*.css`, so the class is not bundled.

Impact: provider exchange panes lose the intended full height wrapper around `ExchangeDetail`. This can break the reused detail component's internal flex and scroll containment inside the canvas pane.

Fix: add the side effect import for `./session-canvas/viewers/resource/exchange-viewer.css` in `www/src/main.tsx` with the other resource viewer CSS imports.

### Minor findings

**m1: Binary download links bypass the existing safe href pattern.**

`www/src/session-canvas/viewers/resource/BinaryResourceViewer.tsx:41` writes `content.downloadUrl` directly to an external anchor. The URL is backend owned, so this is low risk, but applying the existing `safeHref` style scheme check would align with markdown link hardening.

**m2: The truncated content note is duplicated.**

`www/src/session-canvas/viewers/resource/TextResourceViewer.tsx:25` and `www/src/session-canvas/viewers/resource/JsonResourceViewer.tsx:45` share the exact text `Partial content shown (truncated by the server).` `MarkdownResourceViewer.tsx:41-43` has a near variant. A small shared note primitive would keep the viewer copy DRY.

### Checklist verification

- Six discriminable wire kinds are represented by `ResourceContentResponse` at `www/src/session-canvas/api/resourceContent.ts:90-96`.
- Viewer selection keys on `kind`, refines markdown by `mediaType`, and treats `native-record` JSON as the JSON tree with a provenance label at `resourceState.ts:53-75`.
- Repo wide probe found no `dangerouslySetInnerHTML`; markdown XSS tests cover script tags, image onerror payloads, `javascript:` links, fenced script text, and handler attributes at `www/src/session-canvas/viewers/resource/markdown.test.tsx:9-66`.
- Missing reasons map to stable pane states at `resourceState.ts:83-101`, with backend message passthrough for missing responses at `resourceState.ts:73-74`.
- Dedupe is registry owned for resources and provider exchanges at `registry.tsx:78-91`; tests cover deterministic pane ids and provider exchange dedupe at `registry.test.ts:5-59`.
- File sizes are under the 700 line limit. The largest changed file is `www/src/components/ExchangeDetail.tsx` at 463 lines.
- `www/src/index.css` is untouched by the PR diff.

## Dependencies

- TanStack Query powers `useResourceContent` and `ExchangeDetail` data fetching.
- React renders markdown as escaped React nodes and viewer bodies.
- Vite controls CSS inclusion through side effect imports, which is why the missing `exchange-viewer.css` import is user visible despite passing TypeScript and unit tests.
- Backend Pydantic `TimelineModel` uses alias generation to emit camelCase wire fields from snake case Python models at `api/src/transport_matters/session/timeline_models.py:36-41`.

## Relevance to Helioy

The review reinforces the session canvas rule that co-located CSS is only effective when routed through an imported side effect. For future canvas viewer slices, CSS presence should be asserted either by a component style import test, a build artifact probe, or a convention that every viewer CSS file is imported next to the other viewer CSS side effects.

## Open Questions

- Should binary resource downloads reuse the markdown `safeHref` helper directly, or should a shared URL policy helper live outside the markdown module?
- Should truncated resource notes be unified across text, JSON, and markdown with one shared `TruncatedNotice` primitive?
- Should provider exchange pane layout get a computed style test to prove `.canvas-exchange` is bundled and applied?
