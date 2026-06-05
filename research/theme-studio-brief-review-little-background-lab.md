---
title: Theme Studio Brief Review for little-background-lab
type: research
tags: [theme-studio, little-background-lab, community-themes, renderer-seam, review]
summary: Round 2 review found one renderer seam clarification needed after the protected scenes and extensibility delta.
status: active
source: codebase-analyst
confidence: high
created: 2026-06-12
updated: 2026-06-12
---

## Executive Summary

The Theme Studio brief defines the community theme authoring surface for little-background-lab and the import contract transport-matters will consume. Prior portability, validation, accent, save semantics, focus, and module split findings are now reflected in `NOTES/theme-studio-brief.md`; the new v2 delta needs one clarification so the renderer seam is implementable without spec writers inventing theme JSON shape.

A one sentence conditional signoff was sent on the bus to `little-background-lab:general:2:1.1` for topic `theme-brief-v2-consensus`.

## Project Metadata

- Language: TypeScript, CSS, HTML.
- Framework and tooling: Vite 7.3.5, TypeScript 5.9.3, React 19.2.7 dependency present.
- Build system: `pnpm build` runs `tsc && vite build`.
- Indexed structure: `.fmm.db` and `.fmmrc.toml` exist. fmm reports 15 indexed source files and 2,271 LOC under `src/`.
- Verification: `pnpm build` passed on 2026-06-12. `git status --short` was unchanged before and after the build, with only pre-existing untracked `.fmm*`, `.fmmrc.toml`, and `PRODUCT.md` entries.

## Architecture

- `src/main.ts` owns the app shell, scene list, theme state, panel mounting, and live application of theme changes. It registers scenes in a local array at `src/main.ts:32`, initializes the default day progress at `src/main.ts:69-75`, and applies theme changes at `src/main.ts:249-272`.
- `src/theme/theme.ts` defines the current theme contract. `ThemeSettings` carries `sceneId`, `sceneParams`, `photoIndex`, `accentId`, `cornerId`, `veil`, `borderId`, `glass`, `glassAmount`, and `shadowId` at `src/theme/theme.ts:13-27`. The brief now says public JSON migrates from `photoIndex` to `photoKey` at `NOTES/theme-studio-brief.md:59`.
- `src/ambient/types.ts` defines the scene contract. `AmbientSceneParam` is numeric metadata at `src/ambient/types.ts:36-43`; `AmbientSceneDefinition` is currently a WebGL fragment shader contract with `fragmentShaderSource`, optional `params`, and optional `usesPhoto` at `src/ambient/types.ts:45-56`.
- `src/ambient/createAmbientBackground.ts` is the WebGL renderer. It compiles every scene by passing `scene.fragmentShaderSource` to `createProgram` at `src/ambient/createAmbientBackground.ts:121-123`.
- `src/ambient/photos.ts` owns the photo catalog and credits. `PhotoEntry.key` is stable at `src/ambient/photos.ts:21-28`; local photos are sorted and prepended before PICSUM entries at `src/ambient/photos.ts:44-71`.

## Key Patterns

- Live coupling is already implemented: panel controls mutate the shared settings object, then `applyTheme` writes CSS tokens, scene id, scene params, photo texture, photo credit, and panel render at `src/main.ts:249-272`.
- Scene params are metadata driven. The same `AmbientSceneParam` metadata that renders controls can validate imported `sceneParams` before any theme is applied.
- The theme format is now explicitly data only. Renderer extensibility should therefore live entirely in the scene contract and renderer registry, not in `ThemeDefinition.settings`.

## Detailed Findings

### 1. Prior review findings are now incorporated

The brief now uses stable `photoKey` instead of public numeric `photoIndex` at `NOTES/theme-studio-brief.md:59`, defines canonical OKLCH accent serialization at `NOTES/theme-studio-brief.md:60`, requires strict per-cause import validation at `NOTES/theme-studio-brief.md:63`, and requires a pre implementation module split at `NOTES/theme-studio-brief.md:64`.

The previous save and card accessibility findings are also incorporated. Curated themes fork on save, user themes save in place, and duplicate is the fork path at `NOTES/theme-studio-brief.md:29`; user theme actions are revealed on hover and focus-within at `NOTES/theme-studio-brief.md:31`.

### 2. Protected scenes are named correctly

The new protected scenes section names `reference-sea-ii` and `photo-study` as flagship backgrounds at `NOTES/theme-studio-brief.md:80`. These match code evidence: `referenceSeaTwoScene` has id `reference-sea-ii` at `src/ambient/scenes/reference-sea.ts:372-378`, and `photoStudyScene` has id `photo-study` at `src/ambient/scenes/photo-study.ts:12-18`.

The regression gates also match code. The sea exposes `uDayProgress` as a scene param at `src/ambient/scenes/reference-sea.ts:26` and is seeded from local day progress at `src/main.ts:69-75`. Photo study exposes `uPhotoGrade` at `src/ambient/scenes/photo-study.ts:17-25` and uses it in grading at `src/ambient/scenes/photo-study.ts:50-53`. The photo catalog includes stable keys and optional credits at `src/ambient/photos.ts:21-28`, builds local credit backed entries at `src/ambient/photos.ts:44-59`, appends PICSUM entries at `src/ambient/photos.ts:63-71`, and displays credits through `updatePhotoCredit` at `src/main.ts:199-245`.

### 3. Theme data boundary is coherent

The v2 delta says `ThemeSettings` remains renderer agnostic with `sceneId`, `sceneParams`, `photoKey`, and pane material values, with no embedded code at `NOTES/theme-studio-brief.md:81`. That matches the desired migration path. Current `ThemeSettings` is already data only at `src/theme/theme.ts:13-27`, except for the pending `photoIndex` to `photoKey` migration already specified at `NOTES/theme-studio-brief.md:59`.

### 4. Renderer seam needs one contract clarification

The new section says the scene registry types scenes by renderer kind, with `{ kind: "fragment" }` now and future `{ kind: "module" }` adapters at `NOTES/theme-studio-brief.md:82`. That is the right direction, but it does not explicitly define how today's `AmbientSceneDefinition` changes from a required `fragmentShaderSource` shape into a discriminated renderer contract.

This matters because the current renderer compiles every registered scene as a fragment shader at `src/ambient/createAmbientBackground.ts:121-123`, and every current scene definition relies on `fragmentShaderSource` from `src/ambient/types.ts:45-56`. The brief should state that the fragment variant preserves `fragmentShaderSource`, `params`, and `usesPhoto`, while future module adapters expose only the existing renderer agnostic `ThemeSettings` data surface: `sceneId`, numeric `sceneParams`, `photoKey`, and pane material values.

Bus reply sent:

`conditional: I sign off conditional on the following changes: 1. In "Protected scenes and renderer extensibility", state that the scene registry changes AmbientSceneDefinition from today's fragmentShaderSource-only contract (src/ambient/types.ts AmbientSceneDefinition; src/ambient/createAmbientBackground.ts createAmbientBackground) into a discriminated renderer contract whose fragment variant preserves fragmentShaderSource, params, and usesPhoto, and whose future module adapters expose only the existing ThemeSettings sceneId/sceneParams/photoKey data surface (src/theme/theme.ts ThemeSettings), so spec writers do not invent renderer-specific theme JSON.`

## Dependencies

- `vite`: local dev server and production bundle.
- `typescript`: compile and typecheck gate.
- `react` and `@types/react`: present dependencies, though inspected source currently uses direct DOM rendering.

## Relevance to Helioy

The brief is intended to become the community theme contract consumed by transport-matters. The key Helioy boundary is to keep community themes as safe, portable data while allowing richer renderer code through separate reviewed scene packages.

## Open Questions

- Should the first implementation introduce only the fragment discriminant, or also a renderer registry shell for later module adapters?
- Should module adapters be limited to numeric `AmbientSceneParam` controls for schema version 1, or should richer param kinds wait for schema version 2?
- Which package owns the canonical validator that transport-matters imports?
