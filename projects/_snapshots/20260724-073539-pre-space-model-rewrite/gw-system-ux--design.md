---
title: Gradient-Waves Scene-Control System — Panel UX Design
type: design
tags: [ux-design, little-background-lab, gradient-waves, panel, palette, day-modulation, randomize]
summary: Panel interaction model for palettes, day-driven param modulation, and concern-separated randomize on the gradient-waves scene.
status: active
source: ux-designer
confidence: high
created: 2026-06-15
updated: 2026-06-15
---

# Gradient-Waves Scene-Control System — Panel UX Design

**Scope:** the SCENE section of the little-background-lab control panel (plain-TS DOM, not React), gradient-waves first. Adds three capabilities: (1) preset palettes, (2) day-driven param modulation, (3) concern-separated randomize. My lens is the **panel interaction model and ergonomics**; I lead on D (randomize) and E (full layout) and take a decisive position on the rest.

**Grounding (read against current code):**
- Scene params: `AmbientSceneParam { id, uniform?, label, min, max, step, defaultValue }` (`src/ambient/types.ts:30`). gradient-waves has 6: `dayProgress` (0–1/0.001/0.25), `lines` (5–50/1/24), `amplitude` (0–1/0.01/0.5), `wavelength` (0–1/0.01/0.5), `stagger` (0–1/0.01/0.4), `sway` (0–1/0.01/0.5) (`src/ambient/scenes/gradient-waves.ts`).
- Colors are **baked `vec3` constants** in the fragment shader (`gradient-waves.ts` main(), lines ~74–79), crossfaded by a `daylight` value derived from `uDayProgress`. They are NOT uniforms today.
- `ThemeSettings { sceneId, sceneParams: Record<string,number>, …, materialId?, materialParams? }` (`src/theme/types.ts:24`). No palette or day-pair field exists.
- `normalizeTheme()` (`src/theme/validate.ts:111`) rebuilds settings from an **explicit field list** — the choke point. Any new persisted field must be added there AND in `validateThemeDefinition`.
- Persistence: per-theme, `localStorage` key `little-background-lab.theme-studio.v1`, `ThemeStorageRecordV1 { schema, activeThemeId, themes: ThemeDefinition[] }` (`src/theme/storage.ts`).
- Primitives (`src/theme/panel/primitives.ts`): `rangeControl({attrs,min,max,step,value,baseline?})` (single-thumb), `seg(group, [value,label][], active)`, `switchControl(id, checked)`. No dual-thumb slider.
- `ctx.change(mutate, rerender?)` — `rerender:false` for live drag, default `true` for discrete clicks.

---

## A. Param model

Keep `sceneParams: Record<string,number>` as the single source of truth for **shape** params and the **day clock**. Do not break the flat-record contract. Add three small, orthogonal, **additive** concepts so old themes keep working untouched:

```ts
// 1. Palette: a discrete selection, modelled like materialId. Scene-scoped.
interface AmbientSceneBase {
  // …existing…
  palettes?: readonly ScenePalette[];   // curated, owned by the scene
  defaultPaletteId?: string;
}
interface ScenePalette {
  id: string; label: string;
  light: { start: RGB; end: RGB };      // noon gradient (RGB = [r,g,b] 0..1, shader-native)
  dark:  { start: RGB; end: RGB };      // night gradient
}

// 2. Day-modulation: a per-param capability flag (additive; default = static).
interface AmbientSceneParam {
  // …existing…
  dayModulatable?: boolean;             // true → panel offers the ◐ day-vary toggle
}

// 3. New persisted state on ThemeSettings (both optional → back-compatible).
interface ThemeSettings {
  // …existing…
  scenePaletteId?: string;                       // absent ⇒ scene defaultPaletteId
  sceneParamsNight?: Record<string, number>;     // per-param night value; KEY PRESENCE ⇒ modulation on
}
```

**Core idea for modulation:** `sceneParams[id]` is the **noon** value, `sceneParamsNight[id]` is the **night** value, and the renderer computes `effective = mix(night, noon, daylight)` using the same `daylight` the shader already derives from `uDayProgress`. A param with no night key is static — i.e. exactly today's behaviour. Turning modulation **on** = write a night key; **off** = delete it. No new kinds, no schema fork.

`dayProgress` is **the clock, not a shape param**: never modulatable, never randomized (see D).

---

## B. Palette picker UX

A **swatch-card grid**, reusing the existing `.scene-card` button pattern (`data-palette`, `aria-pressed`) so it inherits the selected-ring style and the grid CSS for free. Each card shows the palette's **full identity** regardless of current time of day:

- **Top strip** = noon gradient `light.start → light.end` (left→right CSS `linear-gradient`).
- **Bottom strip** = night gradient `dark.start → dark.end`, divided by a 1px hairline.
- **Text label** below (always present — selection is never color-only; WCAG 1.4.1).

Showing both strips (the whole ramp) beats previewing "at current dayProgress," because two palettes would look identical at noon. Swatches are static CSS computed from the palette colors (`rgb()` from the `0..1` vec3 → `*255`); they need no live redraw. Clicking applies immediately (`ctx.change(s => s.scenePaletteId = id)`, rerender true) and the live canvas updates from the new uniforms.

```
palette                                              🎲
┌──────┐  ┌──────┐  ┌──────┐  ┌──────┐
│▔noon▔│  │▔▔▔▔▔▔│  │▔▔▔▔▔▔│  │▔▔▔▔▔▔│   top half  = noon gradient
│▁nite▁│  │▁▁▁▁▁▁│  │▁▁▁▁▁▁│  │▁▁▁▁▁▁│   bottom half = night gradient
└──────┘  └──────┘  └──────┘  └──────┘
 forest✓   dusk      slate     ember        (text label, aria-pressed on selected)
```

> Curated palette set is the visual-designer's call; the picker UX above is palette-count-agnostic (wraps in the existing grid). Seed with the current baked colors as the `forest` default so nothing changes visually until a user picks another.

---

## C. Day-modulation UX (strongest recommendation)

**Decision: a per-row `◐` day-vary toggle that reveals a paired "night" sub-slider. Not a custom dual-thumb. Not a "swing amount."**

Why this over the alternatives:
- **Two-handle single track** — needs a new primitive, adds keyboard/thumb-target ambiguity, and the existing `rangeControl` is single-thumb. Reject for v1.
- **"Day swing" amount** (one slider + a spread %) — compact but hides the two real endpoints and can only express *symmetric* spreads. It cannot say "wide at noon, barely-tight at night." Reject as primary; it obscures intent.
- **Paired slider reveal** — most legible (you see both actual values), reuses `rangeControl` verbatim (zero new primitives), accessible (two standard, individually-labelled sliders), and maps 1:1 onto the additive storage. **Winner.**

Default is **off** (no night key) so casual users see no extra clutter. Only `dayModulatable` params show the `◐`. When toggled on, the primary row becomes the `☀` noon value and a dimmed, indented `☾ night` sub-row appears directly beneath it.

```
amplitude   ━━━━━●━━━━━  0.50          ◐     ← ◐ off: ordinary static row
─────────────────────────────────────────
amplitude ☀ ━━━━━●━━━━━  0.50          ◑     ← ◐ on: primary = noon value
  ↳ ☾ night ━━●━━━━━━━━  0.20                 dimmed sub-row = night value
```

The `◐/◑` glyph carries an `aria-label` ("vary amplitude across the day") and is a real `<button>` (keyboard-operable). Toggling off deletes the night key (the sub-row collapses); the noon value is untouched. Both sliders use `ctx.change(…, false)` on drag, matching the existing live-slider pattern.

---

## D. Randomize UX (lead)

**Two dice, scoped by concern and by placement. No global dice. The day clock is never rolled.**

| Dice | Rolls | Leaves untouched | Lives |
|------|-------|------------------|-------|
| 🎲 **shape** | `lines, amplitude, wavelength, stagger, sway` | palette, day clock, night values | inline at the right of the **shape** sub-heading |
| 🎲 **palette** | picks a random preset `scenePaletteId` | all shape params, day clock | inline at the right of the **palette** sub-heading |

**Scope = proximity.** Each die sits next to the group it affects, so its blast radius is legible without reading a label. This is the central ergonomic move; a single ambiguous die is what we are avoiding.

- **`dayProgress` is excluded from every die.** Randomizing the time of day would teleport the scene to night mid-edit — disorienting and off-concept. Time is a deliberate scrub, not a dice outcome.
- **Tasteful vs wild:** one `seg` toggle (`tasteful | wild`), **shape-only**, default **tasteful**. Tasteful draws from curated sub-ranges that always look good; wild uses full min/max. Palette has no such toggle — every preset is curated by definition, so the palette die is always "tasteful."

  | Param | Wild (full) | Tasteful (curated) | Reason |
  |-------|-------------|--------------------|--------|
  | lines | 5–50 | 14–34 | <10 looks empty, >40 looks like noise |
  | amplitude | 0–1 | 0.30–0.70 | avoids flat 0 and clipping 1 |
  | wavelength | 0–1 | 0.35–0.75 | mid-band reads as "waves" |
  | stagger | 0–1 | 0.20–0.70 | keeps bands distinct, not chaotic |
  | sway | 0–1 | 0.30–0.80 | visible motion without thrash |

  > Ranges are a starting point; visual-designer tunes. Snap `lines` to its integer step.

- **No global "randomize everything."** It dilutes the concern separation that is the whole feature, and any honest "everything" would still have to exempt the day clock. Defer indefinitely (YAGNI). If ever wanted, it rolls shape+palette only, still never the clock.
- **Feedback on roll:** the die icon spins 360° (~250ms CSS transform) and the affected slider thumbs animate to their new positions (~200ms thumb transition) so the user *sees* exactly which controls moved — visually reinforcing scope ("shape moved, palette held"). **Respect `ctx.sim.reducedMotion`:** when on, snap instantly, no spin.
- **Undo:** **single-level, transient.** On roll, capture the pre-roll values in panel memory (never persisted) and surface a `↶ undo` ghost-link beside that die; clicking restores them. Rolling clobbers hand-tuned values, so one safety step is high-value; a full undo stack is overkill for a toy lab. The undo affordance clears on the next manual edit or next roll.
- **Labels / a11y:** dice are `<button>` with `aria-label` "Randomize shape (tasteful)" / "Randomize palette" and a tooltip; glyphs are never the only signal.

---

## E. Full SCENE section layout (lead)

All three additions, organized with lightweight sub-headings (`palette / shape / day`) so the now-larger section stays scannable. Scene cards and the existing per-param `theme-row` + `%` readout convention are unchanged.

```
┌─ SCENE ───────────────────────────────────────────────┐
│                                                        │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐                   │  scene cards (existing)
│  │gradient │ │  …      │ │  …      │                   │
│  │ waves  ✓│ │         │ │         │                   │
│  └─────────┘ └─────────┘ └─────────┘                   │
│                                                        │
│  palette                                        🎲     │  palette die (proximity-scoped)
│  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐                   │
│  │▔▔▔▔▔▔│ │▔▔▔▔▔▔│ │▔▔▔▔▔▔│ │▔▔▔▔▔▔│   top=noon ramp   │
│  │▁▁▁▁▁▁│ │▁▁▁▁▁▁│ │▁▁▁▁▁▁│ │▁▁▁▁▁▁│   btm=night ramp  │
│  └──────┘ └──────┘ └──────┘ └──────┘                   │
│  forest✓   dusk     slate    ember                     │
│                                                        │
│  shape                          tasteful│wild    🎲    │  shape die + range toggle
│  lines        ━━━●━━━━━━━━  24                    ◐     │
│  amplitude  ☀ ━━━━━●━━━━━━  0.50                  ◑     │
│    ↳ ☾ night  ━━●━━━━━━━━━  0.20                        │  revealed (amplitude varies)
│  wavelength   ━━━━●━━━━━━━  0.50                  ◐     │
│  stagger      ━━●━━━━━━━━━  0.40                  ◐     │
│  sway         ━━━━●━━━━━━━  0.50                  ◐     │
│                                                        │
│  day                                                   │  the clock — no die, not modulatable
│  time         ━━●━━━━━━━━━━━━━━━━━━━━  25%              │
│  └ scrubs noon ↔ night; drives every ◐ crossfade       │
│                                                        │
└────────────────────────────────────────────────────────┘
```

Notes:
- Value readouts keep the existing `%` formatting (`Math.round((v-min)/(max-min)*100)`) for DRY consistency with the current panel; raw values shown above are for clarity. A clock-time label on `day` is optional polish, not v1.
- `lines` has no `◐` if you choose to keep it non-modulatable (integer day-mod can look steppy); mark `dayModulatable` only on the smooth params (`amplitude, wavelength, stagger, sway`). Decision left as a one-line flag per param.
- The code kicker is currently `02 Scene`; the brief calls it the `04 SCENE` section. Use whichever the live numbering dictates — the layout is independent of the number.

---

## F. Persistence

Survives reload (per-theme, in `ThemeSettings`, must round-trip through `normalizeTheme` + `validateThemeDefinition` + `storage`):

1. **`scenePaletteId?: string`** — selected palette. Absent ⇒ `scene.defaultPaletteId` (back-compat for old themes).
2. **`sceneParamsNight?: Record<string,number>`** — per-param night values; key presence = modulation on. Absent ⇒ all static.
3. `sceneParams` (noon/base values) — already persists, unchanged.

Does **not** persist per-theme:
- **Tasteful/wild toggle** — an *editor preference*, not part of the rendered theme; it only affects future rolls. Persist globally as a small panel preference (e.g. alongside `LabSimSettings`), not inside `ThemeSettings`. Putting it in the theme would wrongly travel on export/import.
- **Undo snapshot** — in-memory only; explicitly transient.

> ⚠️ Choke-point: `scenePaletteId` and `sceneParamsNight` must be added to the explicit field list in `normalizeTheme()` and to `validateThemeDefinition` (as optional, mirroring `materialId`/`materialParams`). Miss this and they are silently dropped on save/load.

---

## G. Phasing & YAGNI

**Ship order (feel-per-effort):**
1. **Palettes.** Biggest visual payoff, simplest interaction (pick a card). Contained cost: uniformize the 4 shader colors + wire `scenePaletteId`. Makes the lab feel "designed" on its own.
2. **Dice (shape + palette), tasteful default, single-step undo.** Instant delight, low complexity — shape die just writes `sceneParams`; palette die picks an id. Reuses all existing plumbing.
3. **Day-modulation.** Most complex (new field, shader-side `mix`, paired-slider reveal). Default off ⇒ zero clutter for casual users. Ship last as the "pro" feature.

**YAGNI risks to avoid:**
- No custom dual-thumb slider (use paired single sliders).
- No full undo stack (single-step only).
- No global "randomize everything" (breaks concern separation; would still exempt the clock).
- No raw-HSL / hue-slider palette editing (already rejected — presets only).
- Never randomize the day clock.
- Tasteful/wild stays one toggle, shape-only (not per-die, not per-param).
- Don't persist transient UI (undo snapshot, hover).
- Don't over-genericize day-modulation to "any param, any curve" — it is noon↔night on the existing day curve, full stop.

---

## Engineering action items (for frontend / shader engineer)

1. **[blocking palettes]** Promote the 4 baked `vec3` color constants in `gradient-waves.ts` to uniforms (`uLightStart/End`, `uDarkStart/End`) or a small palette LUT; the renderer uploads them from the selected `ScenePalette`. Seed `forest` = current baked values so the default is visually identical.
2. **[blocking persistence]** Add `scenePaletteId?` and `sceneParamsNight?` to `ThemeSettings`, to `normalizeTheme()`'s explicit field list, and to `validateThemeDefinition` (optional, like `materialId`). Without this they will not survive reload/export.
3. **[blocking day-mod]** Renderer computes `effective = mix(night, noon, daylight)` for each `dayModulatable` param, reusing the shader's existing `daylight` (from `uDayProgress`) as the single source of truth for the curve. Prefer passing both uniforms and mixing in-shader.
4. **[a11y]** Dice/toggles are `<button>` with `aria-label`; palette/state never color-only (text label + `aria-pressed`); honor `ctx.sim.reducedMotion` for roll animations.
5. Reuse `.scene-card` grid for palette swatches; reuse `rangeControl` for the night sub-slider; reuse `seg` for tasteful/wild. No new primitives required for v1.

## Open questions (stakeholder / sibling panes)

- Exact curated palette set and tasteful range tuning → visual-designer.
- Is `lines` (integer) worth modulating, given steppy day transitions? Recommend leaving it static in v1.
- Optional clock-time readout on `day` vs the existing `%` convention — polish call.
