---
title: Transport Matters P5 — inspector/canvas package split under the shell
type: sessions
tags: [frontend, transport-matters, monorepo, pnpm-workspace, css-tokens, enforcement]
summary: Split www/ into @tm/inspector and @tm/canvas peers composed by the dev shell, cut index.css once, landed import-graph + dep-lint gates (PR#192)
status: active
source: frontend-engineer
confidence: high
created: 2026-07-02
updated: 2026-07-02
---

# Summary

Phase 5 of the Transport Matters www/ separation shipped on `sep/p5-split`
(2d1ed51, PR#192, not merged). The inspector (Tailwind web product) and
canvas (Ark/BEM desktop product) now live in their own packages with zero
edges between them, composed by a shrunken `@tm/shell` that still emits
one bundle. Four commits, each green on `just check && just test`.

# Architecture Decisions

- **Fork over shared abstraction at the product boundary.** `useFullscreen`
  had consumers in both products with different runtime semantics (engine-
  registered on canvas, window-listener fallback on inspector). Forked per
  product instead of hoisting to core: presentation hooks stay out of the
  data kernel, and the fork mirrors the locked token-duplication decision.
- **Registry split with a composition-level uniqueness test.** The single
  localStorage key registry guaranteed uniqueness by construction; after
  the per-product split, a shell test over both exported registries
  restores that guarantee (both products share one origin).
- **Enforcement is two-layered**: a source-level import-graph sweep (by
  package name, exports-map resolution, fail-closed) plus a manifest-level
  dep-lint. Both were verified red on injected violations before trusting
  them green.
- **Narrow, purposeful exports maps.** Canvas exposes one exact deep entry
  (`./ambient/createAmbientBackground`) solely so the shell composition
  test can mock the WebGL boundary; everything else is `.` + css.

# Performance Notes

- Product boundary preserved in chunking: inspector and canvas remain
  separate lazy chunks off the shell entry. Canvas + canvas-lab merged
  into one chunk (previously two) — acceptable, same product.
- Canvas token/base css moved to the entry css group; component css rides
  the canvas chunk with Vite preload (no FOUC observed).

# Deviations from Spec

- `keymapStore` → canvas (spec said inspector): state is
  `canvasGestureModifier`, all consumers canvas. Inspector placement would
  create the exact edge the phase eliminates.
- Fullscreen `COMMANDS` slice stays canvas (spec said extract to
  inspector): the spec predates P2's `ArkExchangeViewer`, whose Escape
  order depends on engine registration (pinned by desktop e2e). Inspector
  needs no command; it has no engine.

# Verification

- Token partition proven lossless by script (66/66 `@theme` tokens,
  identical values across the two product stylesheets).
- Runtime pass against the built bundle (`vite preview` + Playwright
  driver, stubbed APIs): both routes render, the theme clean break holds
  (canvas themes never retint the inspector), zero console errors.
  Gotchas: `vite preview` bound IPv6-only (use `localhost`, not
  `127.0.0.1`); Tailwind v4 auto-detection is cwd-based, so the inspector
  css needs `@source "./"` once it lives outside the building package.

# CI Fix (baf28aa)

The `frontend e2e` job failed after the split: Playwright specs and
visual fixtures had been repointed at the product package barrels, whose
graphs include component CSS, and Playwright's Node-side transform
cannot parse CSS (Vite-run vitest can, so the unit suite stayed green).
Fix: each product exports its storage key registry on a css-free
`./storageKeys` subpath; root barrels dropped the key re-exports.
Reproduced locally via `just www test-e2e` (66/66, three browsers).
Rule: Playwright-land imports must resolve to css-free leaf modules.

# Open Items

- P6 (two bundles + separate serving) consumes this directly: product
  `main.tsx`/`index.html`/vite configs, dual SpaStaticFiles, Playwright
  matrix. Canvas tokens.css already carries base resets so the standalone
  canvas bundle has them.
- Six pre-existing biome warnings (unused suppressions, `!important`) in
  moved canvas files; content untouched by design in a move-only commit.
