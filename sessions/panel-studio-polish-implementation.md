---
title: Panel Studio Polish (SPEC B slice 3) — sections 02-04, custom OKLCH slider, interaction matrix
type: sessions
tags: [frontend, little-background-lab, spec-b, theme-studio, panel, accent, oklch, a11y]
summary: Brought sections 02-04 to spec (numbered kickers, scene.params source), added the custom OKLCH hue accent slider, the keyboard/focus matrix, and reduced-motion suppression, on the stacked panel-studio-polish branch.
status: active
source: frontend-engineer
confidence: high
created: 2026-06-12
updated: 2026-06-12
---

## Summary

SPEC B slice 3 of 3 on branch `panel-studio-polish`, stacked off `panel-studio-core@6f875a8`
(PR #6, base `panel-studio-core`, not `main`). Closes out the theme studio interaction surface
against the binding spec `NOTES/specs/spec-b-panel-studio.md` (sec 7, 8, 9) and the brief
(`NOTES/theme-studio-brief.md` sec 5 rhythm, sec 7 palette discipline).

1. **Sections 02 SCENE / 03 ACCENT / 04 MATERIAL kickers** numbered ("02 Scene", "03 Accent",
   "04 Material"). `.theme-kicker` already applies `text-transform:uppercase` + `letter-spacing`,
   and `.theme-section + .theme-section` already gives the tight-within/generous-between rhythm,
   so only the kicker text changed.
2. **Scene params now read `scene.params`** (the spec-designated source on `AmbientSceneBase`,
   optional → guarded `?? []`), keyed by `param.id`. The prior code read `metadata.params`
   (the registry projection); both carry the same id/label/min/max/step/defaultValue, so render
   is byte-equivalent, but the source now matches the spec boundary (metadata carries `swatch`,
   scene carries `params`).
3. **Custom OKLCH hue slider** (sec 8) added to section 03 beside the six curated swatches. Track
   is painted as the hue sweep across `accentBand.h` at fixed `accentBand.l/c` via `accentCss`
   stops (12 stops); thumb filled by `accentCss` of the current accent. Input writes
   `accent:{oklch:{l:accentBand.l,c:accentBand.c,h}}` through `ctx.change(mutate, false)` (live,
   no remount) and reconciles `aria-pressed` across the seven by hand on that no-remount path.
4. **Reduced motion**: `mount` adds `.theme-pane--still` to the pane when `ctx.sim.reducedMotion`;
   `panel.css` suppresses transitions/animations under it (`*` + `!important`, mirroring the
   global OS-level `prefers-reduced-motion: reduce` block in styles.css).
5. **Keyboard / focus**: card actions and the hue control are native focusable elements in tab
   order; `:focus-visible` rings (`--canvas-focus-ring`) extended to scene cards, swatches, photo
   thumbs, seg buttons, the switch track, and the hue slider.
6. **CSS** all in `src/theme/panel/panel.css`, tokens only. Hue track/thumb sizes derived via
   `calc` on `--canvas-pane-padding` (`--hue-track`, `--hue-thumb`); no raw hex/px/alpha (1px
   hairline borders match the established convention throughout the pane CSS).

Gate: `pnpm test` 42 passed (36 pre-existing untouched + 6 new); `pnpm build` green (tsc strict,
JS 21.37 KB gzip).

## Architecture Decisions

- **`aria-pressed` on the range input.** Spec sec 8 says "aria-pressed marks whichever of the
  seven is current." A slider has no native pressed state, so the custom slot carries
  `aria-pressed` on the `<input type=range>` itself — unusual but it keeps one consistent truth
  across all seven members and is exactly what the active-state test asserts. The `.accent-custom`
  label highlights via `:has(.accent-custom__slider[aria-pressed="true"])`.
- **Live active-state reconciliation without remount.** The slider's `input` handler clears every
  swatch's `aria-pressed` and sets its own, then updates `--accent-thumb`, before calling
  `change(_, false)`. This mirrors the identity header's no-remount refresh from slice 2: a
  rerender=false path must hand-maintain any state the (skipped) remount would have fixed.
- **Pane-level reduced-motion hook in `mount`.** `sim.reducedMotion` is a runtime flag with no OS
  signal, so it needs a class hook. The pane shell in `mount.ts` is the only render site for the
  `.theme-pane` element, so the modifier belongs there; `panel.css` keys off it. Kept additive
  (class appended), so no existing selector or test breaks.
- **Swatch background via `ctx.accentCss({id})`** instead of `ACCENTS[id].hex` — one resolver path
  for accent→css across swatches, custom thumb, and track (DRY; same output).

## Performance Notes

Build JS 67.56 KB raw / 21.37 KB gzip; CSS 22.41 KB / 4.38 KB gzip. No runtime perf work. Slider
drag live-couples via `change(_, false)` (no panel remount), same path as veil/blur/scene params.

## Fix Round (orchestrator review, commit `1fea487`)

One finding: spec sec 1 annotates `baselineSettings` as the active entry's original settings
("slider ticks"), but veil/blur/scene-param ranges rendered draft values only, with no baseline
marker. I had deferred this in the first commit, reasoning from the directive's deliverable
enumeration; the orchestrator (correctly) read the spec annotation as a deliverable. Fixed:

- **`rangeControl` (primitives.ts)** — one shared slider helper wrapping the input in
  `.theme-range` so a baseline tick rides the track. Tick at the baseline value's % via
  `rangePercent` (clamped, whole %); absent when baseline is null (tie-break: always shown when
  `baselineSettings` exists). veil + blur (material.ts) and scene params (scene.ts) route through
  it; scene's param-output lookup moved to `closest(".theme-row")` since the input now nests one
  level deeper.
- **panel.css** `.theme-range` / `.theme-range__tick`, tokens only (`--tick-w/-h` via `calc` on
  pane padding, `--tick-color` a panel-local alpha token mirroring `--ring-accent`).
- Tests (42 → 44): endpoint %s (0/50/100), absent-when-null, and the veil tick holding at the
  original value after a draft-only change.

Gate after fix: `pnpm test` 44 passed; `pnpm build` green.

## Delta Round 2 (orchestrator, commit `e8b8ef5`)

Mechanical null-safety: the tick wiring dereferenced `baselineSettings` (`baseline.veil`,
`baseline.glassAmount`, `baseline.sceneParams`) before the null-safe `rangeControl` helper, so a
null baseline would crash the render. Spec sec 1 types `baselineSettings` as `ThemeSettings | null`,
but the **landed `ThemeRegistrySnapshot` declared it non-null** — so the orchestrator's "fix the
call sites" premise (type already nullable) didn't hold. Aligned `types.ts` to the spec
(`ThemeSettings | null`); the registry producer already assigns a non-null clone, so no producer
change. Call sites: `baseline?.veil ?? null`, `baseline?.glassAmount ?? null`, and scene params
`baseline ? (baseline.sceneParams[id] ?? param.defaultValue) : null` (null baseline omits the tick,
never fakes a default). Test: render material + scene sections with `baselineSettings = null` —
no throw, no `.theme-range__tick` (44 → 45). Gate green.

## Lesson

Second time across these slices that I deferred a spec-annotated edge by reasoning from the
directive's bullet list; both times the orchestrator flagged it. The binding spec's annotations
ARE deliverables — the directive enumeration is a summary, not a scope ceiling that overrides the
spec. When the spec specifies a behavior, implement it.

## Open Items

- CDP studio smoke (spec sec 11.4) not run; the directive gate was `pnpm test` + `pnpm build`,
  both green. The DOM is fully unit-covered for the new surface.
