---
title: Gradient Waves Scene Control System in Little Background Lab
type: research
tags: [little-background-lab, gradient-waves, ambient, theme-system, webgl]
summary: Palette choice should live in a registry while day modulation extends numeric scene params, keeping persistence additive and renderer contracts simple.
status: active
source: codebase-analyst
confidence: high
created: 2026-06-15
updated: 2026-06-15
---

## Executive Summary

`little-background-lab` is a strict TypeScript and Vite theme lab for ambient WebGL backgrounds and pane material controls. For the gradient waves control system, the clean design is to keep scene params numeric, add scene palettes through a registry patterned after pane materials, and make day modulation an optional numeric param property.

## Project Metadata

- Language: TypeScript, strict mode.
- Runtime and build: Vite app, `pnpm build` runs `tsc && vite build`.
- Test runner: Vitest.
- UI stack: React dependency is present, but the active theme panel uses vanilla `render(ctx)` and `bind(host, ctx)` sections.
- fmm status: `.fmm.db` exists and `fmm validate` reported all 45 indexed files up to date.
- Size: fmm reported 45 indexed source files and 6,045 LOC.

## Architecture

### Current seams

- `AmbientSceneParam` is a numeric float bridge with `id`, optional `uniform`, `label`, `min`, `max`, `step`, and `defaultValue` in `src/ambient/types.ts:30`.
- `AmbientSceneBase.params` exposes contextual scene controls, while `loopSeconds` documents the seamless `uTime` contract in `src/ambient/types.ts:41`.
- `createParamUniforms` maps param ids to fragment uniforms in `src/ambient/createAmbientBackground.ts:128`.
- `FragmentAmbientBackground.setSceneParamUniforms` uploads scalar param values every frame in `src/ambient/createAmbientBackground.ts:376`.
- `gradientWavesScene` declares `dayProgress`, `lines`, `amplitude`, `wavelength`, `stagger`, and `sway` in `src/ambient/scenes/gradient-waves.ts:42`.
- Gradient waves currently computes daylight from `uDayProgress` and hardcodes four RGB constants in `src/ambient/scenes/gradient-waves.ts:68` and `src/ambient/scenes/gradient-waves.ts:74`.
- `sceneSection` renders scene params as sliders from data and binds by `data-scene-param` in `src/theme/panel/sections/scene.ts:18` and `src/theme/panel/sections/scene.ts:73`.
- `ThemeSettings` persists scene params as `Record<SceneParamId, number>` and has optional material fields in `src/theme/types.ts:24`.
- `normalizeTheme` rebuilds settings from an explicit field list in `src/theme/validate.ts:111`, so new fields must be copied deliberately.

### Material registry precedent

The pane material system is the best template for palettes:

- `PaneMaterial` defines id, label, swatch, params, tokens, and legacy projection in `src/pane/materials/types.ts:19`.
- `createMaterialRegistry` performs integrity checks and exposes metadata in `src/pane/materials/registry.ts:29`.
- `resolveMaterial` supports additive persistence by preferring `materialId` while preserving legacy `glass` fields in `src/pane/materials/registry.ts:55`.
- `materialSection` renders material cards and data driven param sliders in `src/theme/panel/sections/material.ts:7`.
- Validation copies and range checks material fields without a schema bump in `src/theme/validate.ts:224`.

## Key Patterns

1. **Registry backed extensibility**: Scenes and materials are registered data with metadata projection. Palettes should follow this pattern rather than becoming ad hoc shader constants.
2. **Renderer neutral ids**: Theme JSON keys by param id, never uniform. This is protected by a panel regression test in `src/theme/panel/panel-studio.test.ts:376`.
3. **Validation choke point**: All persisted theme settings pass through `validateThemeDefinition` and `normalizeTheme`, so every additive field needs validation plus explicit cloning.
4. **Loop safety by source separation**: `uTime` loops through `wrapSceneTime` in `src/ambient/createAmbientBackground.ts:36`; `uDayProgress` is external day state. Day modulation should consume day state, not introduce new `uTime` terms.

## Detailed Findings

### Param model

Do not make `AmbientSceneParam` a broad `range | choice | color` union. That would force `ThemeSettings.sceneParams` away from `Record<string, number>` and would ripple through renderer upload, validation, migration, tests, and panel bindings.

Recommended extension:

- Keep params numeric.
- Add optional `dayModulation: { noon: number; night: number }` for numeric day pairs.
- Add optional `randomize` metadata for dice eligible ranges.
- Keep palettes outside params in a palette registry.

### Palette system

Create a palette registry similar to `materialRegistry`. A gradient waves palette should hold a curated light and dark gradient pair, each with start and end RGB values plus a swatch. `ThemeSettings` should store only the selected palette id.

For the shader, replace hardcoded colors with uniforms such as `uGradientStart` and `uGradientEnd`. The host should compute current colors from the selected palette and the same daylight curve used for numeric day modulation, then upload vec3 uniforms per frame.

### Day modulation

Resolve day driven numeric values in the renderer host:

1. Resolve `dayProgress`.
2. Compute daylight with the existing cosine curve.
3. For params with a day pair, upload `mix(night, noon, daylight)` to the existing scalar uniform.
4. For all other params, upload the static value.

For gradient waves, `wavelength` is the first consumer. Lower values produce wider waves and higher values produce tighter waves because the shader maps wavelength through `mix(1.0, 7.0, uWavelength)` in `src/ambient/scenes/gradient-waves.ts:88`.

### Randomize

Use separate dice by concern:

- Shape dice mutates only declared wave shape controls: `lines`, `amplitude`, `wavelength`, `stagger`, and `sway`.
- Palette dice mutates only the active scene palette id.
- Neither dice touches `dayProgress`.
- Tasteful ranges should ship first. Store optional wide ranges for later, but do not expose them initially.
- Persist concrete settings, not a random seed. Exported theme JSON then reproduces the outcome.

### Persistence

Add two optional `ThemeSettings` fields:

```ts
scenePaletteId?: string;
sceneDayParamPairs?: Record<SceneParamId, { noon: number; night: number }>;
```

Validation should accept missing fields, validate present palette ids against the active scene, and validate each day pair against a declared numeric param range. `normalizeTheme` should copy `scenePaletteId` and deep clone `sceneDayParamPairs`. `cloneThemeSettings` should also deep clone pairs so snapshots remain immutable.

No schema bump is needed because the fields are optional and additive, matching the material registry precedent.

## Dependencies

- `src/ambient/types.ts`: scene param contract and loop contract.
- `src/ambient/createAmbientBackground.ts`: renderer upload path for scalar params, `uTime`, and future palette uniforms.
- `src/ambient/sceneRegistry.ts`: scene metadata and param lookup surface.
- `src/pane/materials/registry.ts`: registry pattern for palette design.
- `src/theme/types.ts`: persisted settings shape.
- `src/theme/validate.ts`: strict validation and normalization choke point.
- `src/theme/panel/sections/scene.ts`: active UI seam for palette cards, dice controls, and day pair controls.
- `src/main.ts`: `applyTheme` is the host choke point that validates settings, applies theme tokens, selects scenes, and sets ambient params.

## Relevance to Helioy

This design keeps the lab aligned with Helioy's broader preference for registry backed extension points and explicit persistence seams. It also avoids a premature generic control framework while still giving gradient waves the three requested capabilities: curated palettes, day driven numeric modulation, and separated randomization.

## Open Questions

- Whether `dayProgress` should remain a lab scrubber seeded once at startup, or become a live wall clock provider inside the renderer.
- Whether future scenes need different palette roles beyond two stop gradients.
- Whether the first UI should expose editable noon and night pairs immediately, or start with declared defaults and add editing after palette selection lands.
