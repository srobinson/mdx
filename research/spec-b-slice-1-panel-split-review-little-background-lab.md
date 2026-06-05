---
title: SPEC B Slice 1 Panel Split Review for Little Background Lab
type: research
tags: [little-background-lab, code-review, theme-panel, spec-b]
summary: Read only convention review of PR 4 found the panel split stayed mechanical with no real issues.
status: active
source: codebase-analyst
confidence: high
created: 2026-06-12
updated: 2026-06-12
---

## Executive Summary

PR 4 splits `src/theme/theme-panel.ts` into section modules under `src/theme/panel/`. The review found no real SPEC B slice 1 convention issues: file and function sizes stay below limits, the barrel keeps the existing import path, and the diff is a mechanical section extraction with no studio feature implementation.

## Project Metadata

- Language: TypeScript
- Framework and tooling: Vite, Vitest, strict TypeScript
- Build scripts noted only, not run per review instruction: `build`, `test`, `dev`, `preview` in `package.json`
- fmm status: `.fmm.db` and `.fmmrc.toml` are present; `fmm validate` reported indexed files up to date

## Architecture

- `src/theme/theme-panel.ts` is now a 7 line barrel that re exports `mountThemePanel` and panel types.
- `src/theme/panel/types.ts` owns `PanelTab`, `LabSimSettings`, `ThemePanelContext`, and the new `PanelSection` seam.
- `src/theme/panel/mount.ts` composes ordered `PanelSection` arrays by active tab, renders the shell, binds tabs, then binds each active section.
- Theme tab rendering is split across `sections/themes.ts`, `sections/scene.ts`, `sections/accent.ts`, and `sections/material.ts`.
- Settings tab rendering is split into private `simulationSection` and `performanceSection` values in `sections/settings.ts`.

## Key Patterns

- The split follows SPEC B section 2's provider parametric seam: every section exposes `render(ctx)` and `bind(host, ctx)` so markup and event wiring stay colocated.
- The orchestrator remains thin and centralizes only tab selection, body composition, shell injection, and section binding.
- Existing public import shape is preserved through the barrel, so `src/main.ts` can continue importing from `./theme/theme-panel.ts`.

## Detailed Findings

No issues were found for this pass.

Evidence checked:

- Diff scope: only `src/theme/theme-panel.ts` and new `src/theme/panel/**` files changed.
- File size limits: all new files are 100 LOC or less; the barrel is 7 LOC.
- Function and symbol size limits from fmm outlines: largest moved section is `sceneSection` at 93 lines; `mountThemePanel` is 28 lines.
- SPEC B slice 1 scope: `NOTES/specs/spec-b-panel-studio.md` section 2 requires the split first, no feature code, with `PanelSection { render, bind }`. The PR implements that seam without adding identity header, material chips, save or fork controls, import or export UI, custom accent controls, or CSS changes.
- Mechanical extraction: moved code preserves current controls for themes, scene cards, scene params, photo selection, accent swatches, material controls, and settings controls.
- Dependency impact: fmm shows `src/theme/theme-panel.ts` depending only on `src/theme/panel/mount.ts` and `src/theme/panel/types.ts`, with `src/main.ts` as the real downstream consumer.

## Dependencies

- `src/theme/panel/types.ts` depends on ambient photo and scene types plus theme registry settings types.
- Section modules reuse existing theme constants and helpers: `ACCENTS`, `CORNERS`, `BORDERS`, `SHADOWS`, `accentCss`, and photo catalog data through context.
- No new external package dependencies were introduced.

## Relevance to Helioy

This is a clean pre feature split that keeps the Helioy theme studio build ready for later SPEC B work while respecting the hard LOC and DRY constraints.

## Open Questions

- Verification commands were intentionally not run because the review request prohibited build, typecheck, and test execution.
- A future pass should run the SPEC B parity and flagship regression checks once the owner permits verification commands.
