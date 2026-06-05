---
title: Theme panel module split (SPEC B slice 1)
type: sessions
tags: [frontend, refactor, little-background-lab, theme-panel, parity]
summary: Split src/theme/theme-panel.ts into PanelSection modules with byte-identical render/bind parity, no feature code.
status: active
source: frontend-engineer
confidence: high
created: 2026-06-12
updated: 2026-06-12
---

## Summary

SPEC B slice 1 of 3: pre-implementation module split of `src/theme/theme-panel.ts`
(349 lines, `renderThemeTab` ~127 + `mountThemePanel` ~131) into the spec's layout.
No feature code. Branch `panel-split` off `main@d3aa947`, commit `c4da066`, PR #4 to main.

The seam is `PanelSection { render(ctx): string; bind(host, ctx): void }`: each section
colocates its markup and its event wiring. `mountThemePanel` is now a thin orchestrator
that picks the per-tab section array, renders + joins, injects the shell, then binds each
section plus the tabs.

## Architecture Decisions

- **Barrel kept**: `theme-panel.ts` re-exports `mountThemePanel` + types from `panel/`,
  so `src/main.ts` import is untouched (zero diff). Verified.
- **Modules**: `panel/types.ts` (PanelTab, LabSimSettings, ThemePanelContext, PanelSection),
  `panel/mount.ts`, `panel/primitives.ts` (seg, switchControl), and
  `panel/sections/{themes,scene,accent,material,settings}.ts`. `photoThumbUrl` moved into
  `sections/scene.ts`. The spec's `identity-header.ts` / `material-chip.ts` are NOT created
  here — they exist only to host studio features (slices 2-3), and slice 1 is no-feature.
- **Settings as two sections**: `settingsSections = [simulationSection, performanceSection]`,
  matching the two `<section>` blocks of the old `renderSettingsTab`.
- **Global `.seg__btn` handler split cleanly**: the original single handler covered
  corner/border/shadow (theme tab) AND fps (settings tab). The two tabs are never
  co-rendered (`mountThemePanel` renders one tab's sections), so material binds
  corner/border/shadow and settings binds fps with no double-binding. Selective per-tab
  binding reproduces the original's null-query no-ops for the inactive tab's controls.

## Whitespace parity detail (the gate)

The two tabs use different indentation in their template literals: THEME sections at
4-space indent with a `\n  ` body tail; SETTINGS sections at 2-space indent with a `\n`
tail. Each `section.render` returns its `<section>` block with a single leading `\n<indent>`
and **no trailing whitespace**; `mount.ts` composes with
`sections.map(s => s.render(ctx)).join("\n") + tail` where `tail = activeTab === "theme" ? "\n  " : "\n"`.
`join("\n")` reconstructs the original blank line between sections (`</section>\n\n<indent><section>`),
and the per-tab tail restores the closing indent. Result is byte-identical.

## Verification

- Throwaway parity harness: snapshotted the pristine original to `__orig_theme_panel__.ts`
  at the **same directory depth** (so its relative imports resolve unchanged), then rendered
  original vs. new barrel against identical mock contexts via a capture-only fake host
  (`{ innerHTML, querySelectorAll: () => [], querySelector: () => null }`) — no DOM needed.
  Asserted `innerHTML` equality across both tabs and every conditional branch.
  Byte counts: theme dirty+glass+swatch = 6083B==6083B; theme clean+photo-grid+oklch+local
  = 6398B==6398B; settings = 2066B==2066B. Harness deleted before commit.
- `pnpm test` 26/26 green (no test touches the panel). `pnpm build` (tsc strict + vite) green;
  bundle 59.77 kB / gzip 19.18 kB. No file >700 lines (largest 100), no function >150.

## Deviations from Spec

- Did not create `panel/identity-header.ts` or `panel/material-chip.ts` (both are studio
  features = slices 2-3; slice 1 is no-feature). The orchestrator's deliverable list
  omitted them, consistent with this.
- `primitives.ts` carries only `seg` + `switchControl` (the helpers that exist today).
  The spec lists `rangeRow`/`section`/`kicker` as future primitives; they do not exist yet,
  so nothing to move.

## Open Items

- Slices 2-3 add studio features (identity header, material chips, save/fork, card actions,
  custom OKLCH accent) and the SPEC A/C ↔ B host seam (zip `sceneRegistry.all()` with
  `.metadata()` into `ctx.scenes` of `{scene, metadata}`; today the panel still reads the
  pre-zip `ctx.scenes` + `ctx.sceneMetadata` arrays). The `PanelSection` seam is ready for them.
