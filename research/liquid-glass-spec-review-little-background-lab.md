---
title: Liquid Glass Spec Review for Little Background Lab
type: research
tags: [little-background-lab, liquid-glass, theme-system, ambient-scenes, code-review]
summary: The liquid glass spec is directionally sound but needs tighter material param validation and a single legacy glass projection helper before implementation.
status: active
source: codebase-analyst
confidence: high
created: 2026-06-15
updated: 2026-06-15
---

## Executive Summary

The `docs/superpowers/specs/2026-06-15-liquid-glass-design.md` design spec at commit `8a08b72` was reviewed against the live `feat/liquid-glass` checkout. The additive theme format, material registry direction, scene registry reuse, `uDayProgress` bridge, loop contract, and backdrop filter mitigation all align with current code, but the spec should be corrected before implementation so material params follow existing reject semantics and `materialId` remains the single source of truth for legacy `glass` and `glassAmount` projection.


## Correction Round Signoff, 2026-06-15

A delta-only recheck of spec commit `2369320` found that the amended spec resolves the previous conditions. The checkout was on `feat/liquid-glass` at `2369320`, and `git status --short` was empty before and after the recheck.

Verified deltas:

1. `normalizeTheme` is now specified as the additive carrier for `materialId` and `materialParams`, closing the strip-at-chokepoint issue. The spec cites the current rebuild seam and downstream flows through draft update, storage, and import. See `docs/superpowers/specs/2026-06-15-liquid-glass-design.md:225-230`, `src/theme/validate.ts:117-128`, `src/theme/registry.ts:169-174`, `src/theme/storage.ts:50-52`, and `src/theme/import-export.ts:16`.
2. The spec now requires a single legacy projection at `normalizeTheme`, used by validate, import, storage, panel, and curated themes. The panel sets only `materialId` and `materialParams`, while curated themes derive `glass` and `glassAmount` through the shared projection. See `docs/superpowers/specs/2026-06-15-liquid-glass-design.md:198-206`, `docs/superpowers/specs/2026-06-15-liquid-glass-design.md:234-239`, and `docs/superpowers/specs/2026-06-15-liquid-glass-design.md:248-252`.
3. Legacy material resolution now sources blur from `settings.glassAmount`, not material defaults, preserving open water as `blur(18px)`. See `docs/superpowers/specs/2026-06-15-liquid-glass-design.md:175-194`, `docs/superpowers/specs/2026-06-15-liquid-glass-design.md:293-295`, `src/theme/registry.ts:74-75`, and `src/theme/theme.ts:68-72`.
4. Material param validation now rejects out-of-range values instead of clamping, matching the existing scene param validator. See `docs/superpowers/specs/2026-06-15-liquid-glass-design.md:231-233`, `docs/superpowers/specs/2026-06-15-liquid-glass-design.md:298-299`, and `src/theme/validate.ts:56-72`.
5. Scene `drift` was replaced by static `sway`, with explicit guidance that no scene param may multiply `uTime`; this aligns with the engine's wrapped time contract. See `docs/superpowers/specs/2026-06-15-liquid-glass-design.md:86-97`, `docs/superpowers/specs/2026-06-15-liquid-glass-design.md:248`, `docs/superpowers/specs/2026-06-15-liquid-glass-design.md:301-302`, and `src/ambient/createAmbientBackground.ts:36-37`.
6. The spec now distinguishes selector swatches from `material-chip.ts`, which is the per-theme card preview. See `docs/superpowers/specs/2026-06-15-liquid-glass-design.md:198-210` and `src/theme/panel/material-chip.ts:17-35`.

Conclusion: signed off on `docs/superpowers/specs/2026-06-15-liquid-glass-design.md` at sha `2369320` as currently filed.

## Project Metadata

- Language and runtime: TypeScript, browser app, ESM modules.
- Framework and build: Vite with `tsc` and Vitest, from `package.json` scripts `dev`, `build`, and `test`.
- Key dependencies: React 19, Vite 7, Vitest 4, TypeScript 5, Happy DOM.
- Verification run: `pnpm test` passed 5 files and 61 tests, then `pnpm build` passed with Vite output.
- Git state: branch `feat/liquid-glass`, head `8a08b72`, `git status --short` empty before verdict and after verification.
- Structural context: fmm index available and used for file topology, symbol outlines, symbol reads, and dependency graphs.

## Architecture

### Theme data path

- `ThemeSettings` currently contains scene, photo, accent, shape, glass, and shadow fields only. It has no `materialId` or `materialParams` yet, so the proposed fields can be additive if optional. See `src/theme/types.ts:24-35`.
- `THEME_SCHEMA_VERSION` is still `1`, which matches the spec's no version bump requirement. See `src/theme/types.ts:4`.
- Validation requires existing fields and normalizes a theme into a new object. The current normalizer copies `glass` and `glassAmount` verbatim, which is the seam that must change for material backed themes. See `src/theme/validate.ts:117-128` and `src/theme/validate.ts:135-209`.
- Import calls `normalizeLegacyTheme` and then `validateThemeDefinition`, so import behavior will inherit the validator's material normalization if it is implemented there. See `src/theme/import-export.ts:7-17`.
- Storage loads persisted records by validating every theme and cloning the result, so material fields will persist only if validation and clone preserve them. See `src/theme/storage.ts:48-58` and `src/theme/types.ts:170-174`.

### Ambient scene path

- Fragment scenes can declare params with optional uniform bindings and a `loopSeconds` contract. See `src/ambient/types.ts:30-39` and `src/ambient/types.ts:41-59`.
- `sceneRegistry` already provides `all`, metadata, lookup, params, uniform mapping, duplicate id checks, and required swatch metadata. This is a good model for a pane material registry. See `src/ambient/sceneRegistry.ts:37-49`, `src/ambient/sceneRegistry.ts:99-111`, and `src/ambient/sceneRegistry.ts:113-163`.
- The WebGL engine maps scene params to uniforms, stores param values by param id, wraps `uTime` by `loopSeconds`, and uploads bound params each frame. See `src/ambient/createAmbientBackground.ts:128-142`, `src/ambient/createAmbientBackground.ts:232-234`, `src/ambient/createAmbientBackground.ts:345-351`, and `src/ambient/createAmbientBackground.ts:377-379`.
- `main.ts` seeds `dayProgress` from the local clock and pushes all current scene params into the ambient background on theme apply. See `src/main.ts:42-47`, `src/main.ts:78-83`, and `src/main.ts:264-278`.

### Pane material path

- Today `applyThemeTokens` writes exactly the current pane tokens, including `--pane-blur` as `blur(Npx) saturate(120%)` or `none`. This makes `flat` and `frosted` parity achievable if the fallback material emits identical values. See `src/theme/theme.ts:60-73`.
- CSS currently defines base pane tokens, applies `backdrop-filter` on `.canvas-pane-window`, and has a documented 2D transform constraint to preserve backdrop sampling. See `src/styles.css:42-51`, `src/styles.css:77-81`, and `src/styles.css:143-153`.
- The material panel currently owns corner, veil, border, shadow, glass, and blur controls. It will need to become the material selector and param editor described by the spec. See `src/theme/panel/sections/material.ts:6-85`.
- `material-chip.ts` already imports a swatch stop type from the ambient registry and renders a chip from scene swatch plus theme surface values. This makes type-only swatch reuse acceptable, though a neutral shared swatch type could be cleaner later. See `src/theme/panel/material-chip.ts:1-35`.

## Key Patterns

- Registry contracts are preferred over ad hoc branching. `sceneRegistry` is the reference shape for material registry integrity, metadata, params, and lookup behavior.
- JSON validation normalizes into canonical theme objects before import and storage. New optional fields should be preserved or derived at this normalization seam, not only in UI handlers.
- Scene params reject unknown ids and out of range values. Material params should follow this same behavior unless the spec explicitly introduces a separate canonicalization policy.
- Legacy compatibility should be a single projection helper. For liquid glass, the helper should derive `glass` and `glassAmount` from `materialId` plus `materialParams` wherever material backed themes enter or mutate the system.

## Detailed Findings

### 1. Additive non breaking format is viable, with one normalization condition

The spec's additive field plan is compatible with the live format because `ThemeSettings` has no material fields yet and the schema constant remains `1`. See `src/theme/types.ts:4` and `src/theme/types.ts:24-35`.

The condition is that `cloneThemeSettings` must clone `materialParams` when present. Current clone spreads settings but only deep clones `sceneParams` and `accent`, so a material params object would otherwise retain shared identity. See `src/theme/types.ts:170-174`.

### 2. The spec's material param validation wording conflicts with current validator semantics

The spec says material params should be clamped when present, then later says out of range material params are rejected. See `docs/superpowers/specs/2026-06-15-liquid-glass-design.md:201-205` and `docs/superpowers/specs/2026-06-15-liquid-glass-design.md:248-256`.

Current scene param validation rejects unknown params and out of range values via `validateRange`. See `src/theme/validate.ts:56-72`. The material registry should follow that existing contract, or the spec should explicitly define canonicalization and test it. The cleaner path is reject, because it matches the current import contract and error taxonomy.

### 3. Single source of truth needs enforcement outside the panel

The spec correctly says the panel should update `materialId`, `materialParams`, and mirror legacy `glass` plus `glassAmount`. See `docs/superpowers/specs/2026-06-15-liquid-glass-design.md:181-188`.

That is not enough. Imported or stored JSON can arrive without touching the panel. Current `normalizeTheme` copies `glass` and `glassAmount` verbatim, and storage persists the output of validation plus clone. See `src/theme/validate.ts:117-128` and `src/theme/storage.ts:48-58`.

To keep `materialId` as the source of truth, the spec should require one projection helper used by validation, import, storage, panel changes, and curated theme creation. The helper should compute legacy `glass` and `glassAmount` from material params for all material backed themes, or reject mismatched mirrors. Projection is preferable because the spec already frames legacy fields as a compatibility mirror.

### 4. Flat and frosted token parity is achievable

Today's token writer emits these pane treatment tokens: accent, accent rgb, radius, surface alpha, border color, blur, and shadow. See `src/theme/theme.ts:60-73`.

For parity, `flat` must emit `--pane-blur: none`, and `frosted` must emit `--pane-blur: blur(Npx) saturate(120%)`. The new reflection tokens can default to off in `:root`, as the spec says, so existing themes remain visually unchanged. See `docs/superpowers/specs/2026-06-15-liquid-glass-design.md:140-147` and `docs/superpowers/specs/2026-06-15-liquid-glass-design.md:149-164`.

### 5. Material registry mirroring sceneRegistry is sound

The scene registry already implements the exact shape the material registry needs: definitions, metadata, params, id lookup, duplicate id checks, and required swatch metadata. See `src/ambient/sceneRegistry.ts:37-49`, `src/ambient/sceneRegistry.ts:99-111`, and `src/ambient/sceneRegistry.ts:113-163`.

Reusing `AmbientSceneSwatch` is acceptable if it remains a type-only import, because `material-chip.ts` already uses `AmbientSceneSwatchStop` for presentational swatches. See `src/theme/panel/material-chip.ts:1-9`. A later cleanup could move the swatch type to a neutral UI module, but this is not required for this slice.

### 6. `uDayProgress` reuse and loop design match current engine behavior

The spec's daylight curve is cyclic at `p = 0` and `p = 1`, with midday at `0.25` and night at `0.75`. That aligns with the reference sea convention. See `docs/superpowers/specs/2026-06-15-liquid-glass-design.md:60-71` and `src/ambient/scenes/reference-sea.ts:63-69`.

The renderer supports the exact param bridge needed for `uDayProgress`, `uSoftness`, and `uDrift`: scene params map id to uniform, `main.ts` sets values by id, and the WebGL renderer uploads each bound uniform every frame. See `src/ambient/createAmbientBackground.ts:128-142`, `src/main.ts:264-278`, and `src/ambient/createAmbientBackground.ts:377-379`.

Seamless motion is achievable if the implementation follows the reference sea pattern of integer loop frequencies and tiled drift. See `src/ambient/scenes/reference-sea.ts:17-39` and `src/ambient/types.ts:49-56`.

### 7. Backdrop filter mitigation is sound, but must stay precise

The live code documents that the canvas world uses a 2D transform because `translate3d` would clip descendants' backdrop filter sampling. See `src/main.ts:196-203` and `src/styles.css:77-81`.

The spec's requirement for a non transformed `pointer-events: none` reflection overlay is sound. The implementation should add pseudo element styling to `.canvas-pane-window` without introducing a transformed ancestor of the backdrop filtered pane. See `docs/superpowers/specs/2026-06-15-liquid-glass-design.md:159-164` and `docs/superpowers/specs/2026-06-15-liquid-glass-design.md:260-265`.

### 8. File touch points are mostly complete

The spec covers the right main files: new scene, new material registry, scene registry, theme types, token writer, CSS, validation, import, migrate, panel section, chip, curated theme, and tests. See `docs/superpowers/specs/2026-06-15-liquid-glass-design.md:220-233`.

Two clarifications would make the plan safer:

1. Add storage explicitly as a verification seam, even if source changes are not needed, because material bearing persisted records rely on `validateStorageRecord` and `cloneThemeDefinition`. See `src/theme/storage.ts:42-60`.
2. State that `theme-panel.ts` itself should stay a barrel unless a new export is required. The real theme tab wiring lives in `mount.ts`, where `materialSection` is already part of `THEME_TAB`. See `src/theme/theme-panel.ts:1-8` and `src/theme/panel/mount.ts:1-10`.

## Dependencies

- `src/theme/types.ts` is the central data contract for themes and storage records.
- `src/theme/validate.ts` is the canonical import and storage normalization chokepoint.
- `src/theme/theme.ts` is the runtime CSS token writer.
- `src/ambient/sceneRegistry.ts` is the registry pattern to mirror for pane materials.
- `src/ambient/createAmbientBackground.ts` is the uniform upload and loop timing engine.
- `src/theme/panel/sections/material.ts` and `src/theme/panel/material-chip.ts` are the UI touch points for material selection and chips.

## Relevance to Helioy

The review reinforces a reusable Helioy rule: when adding a new source of truth beside legacy compatibility fields, canonicalize the mirror at the validation boundary and reuse one projection helper across UI, import, storage, and curated data. This avoids drift between exported themes, persisted state, and runtime rendering.

## Open Questions

- Should material registry dependencies be injected through `ThemeValidationDeps`, or should `validate.ts` import a singleton `materialRegistry` directly? Injection matches the existing scene and photo validation style.
- Should the shared swatch type move from `ambient/sceneRegistry.ts` to a neutral UI or theme module before pane materials import it? This is a cleanup question, not a blocker.
- Should invalid material legacy mirrors be rejected or automatically normalized? The spec language favors automatic projection, but tests should lock whichever behavior is chosen.
