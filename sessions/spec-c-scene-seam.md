---
title: SPEC C scene renderer seam implementation
type: sessions
tags: [frontend, ambient, theme-studio, scene-registry]
summary: Implemented the canonical ambient scene registry and renderer neutral scene param seam.
status: active
source: frontend-engineer
confidence: high
created: 2026-06-12
updated: 2026-06-12
---

## Summary

Implemented SPEC C on branch `scene-seam` at commit `24b3a97`, opened PR #2, and notified the orchestrator with `done: scene-seam 24b3a97 PR#2`.

The change adds a discriminated ambient scene contract, a canonical `src/ambient/sceneRegistry.ts`, renderer neutral scene params, legacy uniform bridging, scene swatch metadata, and fragment renderer narrowing.

## Architecture Decisions

- `AmbientSceneDefinition` is now a union of `AmbientFragmentSceneDefinition` and typed only `AmbientModuleSceneDefinition`.
- `sceneRegistry` is the single scene lookup surface for app integration, validation, migration, metadata, swatches, and fragment uniform bridging.
- `createAmbientBackground` compiles only fragment scenes, stores runtime param values by param id, and maps active scene params to GLSL uniforms at draw time.
- `main.ts` imports `sceneRegistry` instead of local scene literals and passes `sceneRegistry.all()` plus `sceneRegistry.metadata()` to the panel.
- `src/theme/types.ts` imports canonical scene registry types instead of keeping a temporary duplicate interface.

## Performance Notes

- `pnpm build` passed with JS bundle gzip size 15.26 kB, under the 200 kB target.
- Renderer behavior remains one WebGL program per fragment scene with the existing shared quad buffer and shared photo texture.

## Deviations from Spec

- Browser screenshots were not captured because the in app Browser backend was unavailable. Verification used unit tests, TypeScript build, Vite build, `fmm validate`, `git diff --check`, and a local dev server `curl` smoke check.

## Open Items

- SPEC B can consume `AmbientSceneMetadata.swatch` for material chip theme cards.
- Future module scene adapters remain typed only and unsupported at runtime by design for this slice.
