---
title: Theme Studio Final Spec Pass for little-background-lab
type: research
tags: [little-background-lab, theme-studio, spec-review, scene-contract]
summary: Final delta verification signed off the three theme studio specs after the scene swatch and photoIndex migration contracts were corrected.
status: active
source: codebase-analyst
confidence: high
created: 2026-06-12
updated: 2026-06-12
---

## Executive Summary

`little-background-lab` is a TypeScript and Vite lab for ambient background, pane chrome, and theme studio work intended to inform Helioy surfaces. A final peer review initially found one B to C scene swatch mismatch, then a correction round updated the live specs to use SPEC C `AmbientSceneMetadata.swatch` through a zipped scene plus metadata panel surface. The corrected three spec set is signed off.

## Project Metadata

- Language: TypeScript, strict mode enabled in `tsconfig.json`.
- Framework and runtime: Vite app with React dependency, DOM and WebGL code in `src/`.
- Build system: `pnpm build`, which runs `tsc && vite build` from `package.json`.
- Current scripts on `main`: `dev`, `build`, and `preview`; no test runner yet in `package.json`.
- Test plan in specs: SPEC A provisions Vitest and adds `pnpm test`; SPEC B and SPEC C then depend on that runner.
- fmm status: fmm tooling was available and reported 15 indexed source files, 2,271 LOC.

## Architecture

The current app has a compact, single package architecture:

- `src/main.ts`: app boot, scene list, theme state, panel mounting, ambient renderer wiring, photo credits.
- `src/ambient/`: renderer contract, WebGL background, photo catalog, and scene literals.
- `src/theme/`: current token model and monolithic theme panel.
- `src/styles.css`: production inspired tokens plus panel, pane, and canvas styling.

The proposed theme studio split keeps these boundaries but adds explicit seams:

- SPEC A owns theme JSON, registry, validation, import, export, persistence, migration, and panel data API.
- SPEC B owns the panel split and user interaction surface.
- SPEC C owns the scene registry, renderer seam, scene metadata, and swatch data.

## Key Patterns

- The specs route theme data through a registry instead of letting the panel inspect storage or curated constants.
- The scene seam separates durable theme data from renderer internals by using stable param ids and legacy uniform bridges.
- The panel split uses section modules with colocated render and bind methods to keep `mountThemePanel` thin.
- Scene swatches now travel through a typed presenter surface: `{ scene: AmbientSceneDefinition; metadata: AmbientSceneMetadata }`.
- Verification remains centered on protected flagship scenes: `reference-sea-ii` and `photo-study`.

## Detailed Findings

### Finding 1: SPEC B scene swatch surface

Status: resolved in correction round, signed off.

Initial issue: SPEC B consumed per scene swatches through `ctx.scenes[].meta` or `meta.swatch`, while SPEC C exposed swatches through `AmbientSceneRegistry.metadata()` or `metadataFor()` as `AmbientSceneMetadata.swatch`.

Correction verified in live files:

- `NOTES/specs/spec-b-panel-studio.md:20-21`: `ThemePanelContext` now declares `scenes: Array<{ scene: AmbientSceneDefinition; metadata: AmbientSceneMetadata }>` and says the host zips `sceneRegistry.all()` with `sceneRegistry.metadata()` by scene id.
- `NOTES/specs/spec-b-panel-studio.md:41`: SPEC B now names `AmbientSceneMetadata.swatch` and the `{ scene, metadata }` shape explicitly.
- `NOTES/specs/spec-b-panel-studio.md:82` and `NOTES/specs/spec-b-panel-studio.md:96`: material chips now use `metadata.swatch`, not `meta.swatch`.
- `NOTES/specs/spec-b-panel-studio.md:144`: the integration note names the merged scene surface from SPEC C.
- `NOTES/specs/spec-c-scene-seam.md:144-156`: SPEC C still owns `AmbientSceneMetadata.swatch` and exposes `metadata()` plus `metadataFor(sceneId)`.
- `NOTES/specs/spec-c-scene-seam.md:213`: SPEC C still says `mountPanel` passes `sceneRegistry.all()` and `sceneRegistry.metadata()`.

Impact after correction: the B to C scene swatch contract is coherent and implementable.

### Finding 2: SPEC A v0 photoIndex migration accessor

Status: resolved in correction round, signed off.

Correction verified in live files:

- `NOTES/specs/spec-a-theme-data.md:163-168`: `ThemePhotoLookup` now includes `photoKeyAt(index: number): PhotoKey | null` as a catalog position accessor used only for v0 `photoIndex` migration.
- `NOTES/specs/spec-a-theme-data.md:265-271`: `migrateThemeSettingsV0` maps `photoIndex` through `photoLookup.photoKeyAt(photoIndex)` and falls back to `defaultPhotoKey()` on `null`.

Impact after correction: the migration spec now has an owned, deterministic way to translate legacy index based local data into portable `PhotoEntry.key` values.

### Clean checks still held

- A to C scene contract: SPEC A consumes `AmbientSceneRegistry` and `paramIdForUniform(sceneId, uniform)` at `NOTES/specs/spec-a-theme-data.md:157-160` and `NOTES/specs/spec-a-theme-data.md:247-271`; SPEC C provides `paramIdForUniform` and `fragmentUniformFor` at `NOTES/specs/spec-c-scene-seam.md:153-164`.
- A to B registry names: `ThemeRegistryEntry`, `dirty`, `baselineSettings`, `selectTheme`, `saveDraft`, `duplicateTheme`, `deleteTheme`, plus `renameTheme` and `exportTheme`, are present in SPEC A and consumed by SPEC B.
- Import shape: SPEC A defines `ImportResult` as `{ ok: true; theme } | { ok: false; error: { cause; message } }` at `NOTES/specs/spec-a-theme-data.md:87-90`; SPEC B consumes that exact shape at `NOTES/specs/spec-b-panel-studio.md:39`.
- Accent API: SPEC A defines `ACCENT_BAND` and `accentCss` at `NOTES/specs/spec-a-theme-data.md:95-107`; SPEC B consumes `accentBand` and `accentCss` at `NOTES/specs/spec-b-panel-studio.md:33-36` and `NOTES/specs/spec-b-panel-studio.md:102`.
- Citation style: a probe found no `file:line` anchors in the three spec files.
- Tooling: `git show main:package.json` shows only `dev`, `build`, and `preview`; `git cat-file -e main:pnpm-lock.yaml` confirmed the pnpm lock exists; SPEC A consistently owns adding Vitest.

## Dependencies

Critical dependencies from `package.json`:

- `vite`: dev server and production build.
- `typescript`: strict typecheck through `tsc`.
- `react` and `@types/react`: present, although the inspected app surface is currently DOM and WebGL focused.

## Relevance to Helioy

The theme studio specs define durable boundaries for community driven themes, renderer neutral scene parameters, and panel UX patterns that can transfer into Helioy session surfaces. The corrected scene swatch seam is especially relevant because it cleanly separates renderer owned scene metadata from panel owned material chips.

## Verification

Initial structural orientation and code claim checks used fmm plus `git show main:<path>` against relevant source files.

Delta verification commands and checks included:

```bash
rg -n 'scenes:|AmbientSceneMetadata|metadata\.swatch|meta\.swatch|\.meta|sceneRegistry\.metadata|metadataFor|missing ctx\.scenes|contracts-consumed|ctx\.scenes' NOTES/specs/spec-b-panel-studio.md NOTES/specs/spec-c-scene-seam.md
rg -n 'ThemePhotoLookup|photoKeyAt|photoIndex maps|defaultPhotoKey|migrateThemeSettingsV0' NOTES/specs/spec-a-theme-data.md
nl -ba NOTES/specs/spec-b-panel-studio.md | sed -n '13,42p;90,96p;138,150p'
nl -ba NOTES/specs/spec-a-theme-data.md | sed -n '161,172p;247,272p'
pnpm build
```

`pnpm build` passed with `tsc && vite build` and Vite reported a successful production build.

## Open Questions

- No blocker remains for the current three spec signoff.
- Implementation should preserve the corrected `{ scene, metadata }` panel surface rather than recreating a scene `meta` property in `AmbientSceneDefinition`.
