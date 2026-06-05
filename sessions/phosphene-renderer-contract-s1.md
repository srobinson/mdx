---
title: Phosphene Renderer Contract S1
type: sessions
tags: [frontend, phosphene, renderer, vite-plus]
summary: Added the renderer contract type module and excluded vendored references from Vite+ formatter gating.
status: active
source: frontend-engineer
confidence: high
created: 2026-06-15
updated: 2026-06-15
---

## Summary

Implemented slice S1 for the consensus-hardened renderer migration by adding `src/render/contract.ts` as a types-only module. Added Vite+ formatter exclusion for vendored reference material in `vite.config.ts` using `fmt.ignorePatterns: ["reference/**"]`, leaving `reference/gradient-waves.html` verbatim.

## Architecture Decisions

- Kept the renderer contract additive and unwired, with no runtime logic.
- Reused the existing `Signal` type from `../signal` instead of redeclaring it.
- Centralized the vendored formatter exclusion in the existing Vite+ `fmt` block rather than adding a parallel ignore mechanism.

## Performance Notes

No runtime behavior or bundle code was introduced beyond type declarations. `vp build` completed successfully.

## Deviations from Spec

No contract deviations. The slice expanded allowed changes to include `vite.config.ts` because `vp check` had a pre-existing formatting failure in vendored reference material.

## Open Items

- Future slices will wire the contract into renderer and form modules.
- The production bundle remains above the default Vite warning threshold, unchanged by this slice.
