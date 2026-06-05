---
title: Gradient-Waves Scene-Control System — Architecture Design
type: research
tags: [little-background-lab, gradient-waves, scene-contract, palette, day-modulation, randomize, ambient, webgl1]
summary: One unified param model (kind discriminator) rides the existing float bridge and sceneParams record, so palettes, day-modulation, and a shape dice ship with zero renderer and zero persistence changes.
status: active
source: codebase-analyst
confidence: high
created: 2026-06-15
updated: 2026-06-15
---

# Gradient-Waves Scene-Control System — Architecture Design

**Independent design pass (architecture lens).** Branch `feat/gradient-waves`, `little-background-lab`. Cites symbols, not line numbers. No code written; tree pristine.

## Executive summary

The whole system fits **inside the param model we already have**. `AmbientSceneParam` (a float bridge: `id → uniform → number`, persisted in `ThemeSettings.sceneParams`, uploaded as `uniform1f`) is the single rail every new capability can ride if we add one additive discriminator: `kind?: "range" | "choice"`.

- **Palettes** = a `choice` param whose value is a **numeric index** into a scene-local palette list. The index rides `sceneParams` unchanged; the shader resolves index→colors via codegen'd GLSL (the `stateColor` step-chain idiom) emitted from the *same* palette list. No color uniforms, no color serialization.
- **Day-modulation** = an additive `night?: number` property on a `range` param. The slider stays the noon value; a codegen helper emits `mix(night, noon, daylight)` into the shader. Renderer untouched.
- **Randomize** = a general "shape dice" that re-rolls every `randomizable` range param through the existing `ctx.change` path.

**The headline architectural win: no new `ThemeSettings` field and no `normalizeTheme` change.** Everything persists inside the `sceneParams` record that `normalizeTheme` already spreads and `validateSceneParams` already validates. `createAmbientBackground` (the renderer) is **not touched at all**. Blast radius is 4 source files, all additive.

This is the right reading of the "study the material registry" hint: the *lesson* of the material registry is the registry shape (assert-integrity → metadata → defaults → additive persistence). But materials needed a *separate* concept only because they are **cross-scene** and carry non-trivial projection (`tokens`, `legacyGlass`) plus their own `ThemeSettings` fields. Palettes (v1) are **per-scene** and project to nothing but shader color, so the correct altitude is the registry we already have — `sceneRegistry` — with palettes riding it as choice-param options. Standing up a second parallel registry would be the material registry's *weight* without its *justification*.

---

## A. Param model — extend with a `kind` discriminator (one concept, one rail)

**Decision: extend `AmbientSceneParam` additively; do NOT model palette / day-pairs as separate concepts.**

`AmbientSceneParam` (`src/ambient/types.ts`) gains optional, back-compatible properties:

```ts
export interface ChoiceOption {
  label: string;
  swatch?: AmbientSceneSwatch;   // reuse the registry swatch for card previews
}

export interface AmbientSceneParam {
  id: string;
  uniform?: string;
  label: string;
  min: number;
  max: number;
  step: number;
  defaultValue: number;
  kind?: "range" | "choice";     // default "range" → every existing param unchanged
  night?: number;                // range only: day-modulation target (see C)
  options?: readonly ChoiceOption[]; // choice only: discrete picks (see B)
  randomizable?: boolean;        // range only, default true (see D)
}
```

**Why this beats separate concepts.** The value of every param stays a single `number`. That number already has a complete, tested lifecycle:

1. **Persist** — `ThemeSettings.sceneParams: Record<SceneParamId, number>` (`src/theme/types.ts`), copied by `cloneThemeSettings` and `normalizeTheme` via `{ ...settings.sceneParams }`.
2. **Validate** — `validateSceneParams` (`src/theme/validate.ts`) checks finite + within `[min,max]` from registry metadata.
3. **Upload** — `setSceneParamUniforms` in `createAmbientBackground.ts` uploads each `paramId → uniform` as `uniform1f`.
4. **Apply** — `applyTheme` in `src/main.ts` loops `sceneRegistry.paramsFor(sceneId)` and calls `setParam`.

A `choice` param is just a float index with `min:0, max:options.length-1, step:1` — it rides all four steps untouched. A separate "palette concept" (the material pattern) would instead require its own `ThemeSettings` field, its own validation branch, its own `normalizeTheme` line, its own renderer upload, and its own panel section. `kind` is a **presentation + codegen discriminator only** — it never changes the data shape.

**Reject a `color` kind (YAGNI).** Raw HSL / single-hue authoring was already rejected; palettes are *chosen*, not authored. No user-set color value ever needs to exist or serialize, so a color param (which would force vec3 uniforms and a new serialization shape) earns nothing.

---

## B. Palette system — choice param + index→GLSL codegen

**Today:** `gradientWavesScene` hardcodes four `vec3` endpoints (`lightStart/lightEnd/darkStart/darkEnd`) and crossfades them on `daylight`.

**Design:**

1. **Declare palettes scene-locally.** A `palettes` const in `gradient-waves.ts`, each entry the four endpoints plus a `swatch` (reuse `AmbientSceneSwatch` from `sceneRegistry.ts`, so the card preview is DRY with scene cards):
   ```ts
   const PALETTES = [
     { label: "Spring", swatch: {...}, light: { start: [...], end: [...] }, dark: { start: [...], end: [...] } },
     ...
   ];
   ```
2. **Expose as a choice param** whose `options` are *derived* (`PALETTES.map(p => ({ label: p.label, swatch: p.swatch }))`). Keeping color data off the generic `ChoiceOption` keeps the param model reusable for non-palette choices later.
   ```ts
   { id: "palette", uniform: "uPalette", label: "palette", kind: "choice",
     options: PALETTES.map(...), min: 0, max: PALETTES.length - 1, step: 1, defaultValue: 0 }
   ```
3. **Feed the shader by index.** The user's pick is `sceneParams.palette` (a number), uploaded as `uPalette` via the **existing** float bridge — zero renderer change. A codegen helper `paletteGlsl(PALETTES)` emits a GLSL selector built from the *same* `PALETTES` array (single source of truth):
   ```glsl
   vec3 paletteLightStart(float idx) {  // step-chain selection, identical idiom to stateColor()
     vec3 c = LS0; c = mix(c, LS1, step(0.5, idx)); c = mix(c, LS2, step(1.5, idx)); return c;
   }
   ```
   The shader's hardcoded endpoints become `paletteLightStart(uPalette)` etc. The day crossfade is unchanged.

**Why index, not string id.** The float bridge carries only numbers; a string id would break `Record<id, number>` and force a new `ThemeSettings` field + non-float upload — surrendering the "no persistence change" win. **Trade-off surfaced:** numeric indices are positional, so palette lists must be **append-only** (never reorder/remove) to keep stored themes stable. Cheap discipline; document it next to `PALETTES`.

**WebGL1 constraint honored.** GLSL ES 1.00 forbids dynamic indexing of `const` arrays, which is exactly why the step-chain selector (already proven in `stateColor`) is the right primitive, not array subscripting.

**Registry question — no, not yet.** Inline per-scene `palettes` is the minimal seam; scenes already declare their params inline. A global `PaletteRegistry` (material-registry shape) is YAGNI until palettes become cross-scene curated assets. Because the *choice-param surface is stable*, that promotion is non-breaking when/if it's earned.

---

## C. Day-driven param modulation — declarable `night`, scene-constant, shader-side

**Decision: a `range` param declares `night?: number`; the slider remains the NOON value; the night value is a scene constant baked into the shader via codegen. User edits one slider.**

**Mechanism.** First extract the daylight curve into the prelude (`src/ambient/prelude.ts`) so it is shared and DRY:
```glsl
float daylight(float dayProgress) { return 0.5 + 0.5 * cos((clamp01(dayProgress) - 0.25) * 2.0 * PI); }
```
A codegen helper `dayMix(noonExpr, night)` emits `mix(<night>, <noonExpr>, daylight(uDayProgress))`. For wavelength:
```glsl
float wavelengthEff = mix(WAVELENGTH_NIGHT, uWavelength, daylight(uDayProgress));
float cycles = mix(1.0, 7.0, clamp01(wavelengthEff));   // wide at noon, tight at night
```
`uWavelength` (the user's noon value) still rides `uniform1f` unchanged. **Host and renderer are untouched.**

**Why night is a scene constant, not a second slider (YAGNI for E's "edit both?").** Storing an editable night value would mean a second `sceneParams` entry (`wavelength@night`) and a second slider per modulated param — doubling the control surface for a property that expresses *scene-design intent* (this scene breathes wide→tight across the day), not a per-user knob. Editing both is a clean future add (just another `sceneParams` entry) precisely *because* day-pairs ride the existing record — so deferring it costs nothing later.

**Loop-safety proof.** The seamless-loop contract (`AmbientSceneBase.loopSeconds`) constrains only `uTime` terms: their frequencies must sit on the `2π/loop` grid. Day-modulation reads `daylight(uDayProgress)`, and `uDayProgress` is **wall-clock-seeded and loop-independent** (never wrapped by `wrapSceneTime`); it contains no `uTime` term. Modulating `wavelength` changes only the **spatial** term `x * cycles`, never the `uTime` phase rate `sin(t * hz(1) + ...)`. Therefore the crossfade introduces no `uTime` dependence and cannot alter the loop period. **The one rule to enforce:** a day-paired param must never feed a `uTime` *frequency* (it may freely feed amplitude and spatial terms). State this in the `night` JSDoc.

---

## D. Randomize — one general "shape dice", scoped by concern

**Decision: a single, general shape dice. Scope = every `range` param with `randomizable !== false`. Choice (palette) and the day clock are excluded.**

- **Scope mechanism (declarative):** range params are `randomizable` by default; `gradientWavesScene` marks `dayProgress` `randomizable: false` (randomizing time-of-day is a different concern). Choice params are never in scope in v1 (the dice is shape-only). This cleanly separates the three concerns the brief calls out: shape ≠ palette ≠ day clock.
- **General, not scene-specific:** lives in the scene section; any scene with ≥1 randomizable range param gets the dice for free.
- **Roll model:** uniform random in `[min, max]` snapped to `step`. **Wild within the authored range IS tasteful** — the author already curated ranges (`lines 5–50`, `amplitude 0–1`, …). A separate "tasteful sub-range" mode is YAGNI.
- **Writes through `ctx.change`:** the dice mutates `sceneParams` exactly like a slider drag, so it persists and applies with zero new plumbing.
- **Not seeded:** this is a creative dice, not a test fixture; `Math.random` is fine. Seeded/shareable rolls = future option, noted not built.
- **Separate palette dice: deferred (YAGNI).** One more concept for v1; the choice surface makes it trivial to add later.

---

## E. Panel UX — additive branches in `sceneSection`, no new section file

All changes land in `src/theme/panel/sections/scene.ts` (cohesion: scene controls belong with the scene). The `PanelSection` `render`/`bind` contract and `ctx.change` are sufficient as-is.

- **Param rendering switches on `kind`:**
  - `range` → existing `rangeControl` slider (unchanged).
  - `choice` → a swatch-card grid, reusing the `.scene-grid` / `.scene-card` markup and the swatch the material cards already render. Palette cards show the light/dark gradient pair.
- **Day-paired rows** get a small read-only "↻ day" tag beside the label, signaling the param breathes with the day cycle.
- **Shape dice:** a small button in the scene section (e.g. near the param list header). On click → `ctx.change` setting each randomizable param to a snapped random value, `rerender = true` so sliders update.
- **Requires one additive metadata change:** `AmbientSceneParamMetadata` + `buildMetadata` (`sceneRegistry.ts`) must carry `kind` and `options` through so the panel can render choice cards. Small and additive — no contract break.

---

## F. Persistence — **no new field, no `normalizeTheme` change** (the landmine is sidestepped)

This is the strongest possible answer to the persistence brief: the safest, most non-breaking change is **no persistence change at all.**

- **Palette index** persists inside the existing `sceneParams: Record<SceneParamId, number>`. `normalizeTheme` already carries it via `{ ...settings.sceneParams }`; `validateSceneParams` already validates it (a choice param is `min:0 / max:N-1 / step:1`); `storage.ts` `isNumberRecord` already accepts it; `migrate.ts` is unaffected.
- **Day-modulation** stores **nothing** — `night` is a scene constant in the shader.
- **Dice** writes through `sceneParams`.

Because the new state never escapes the one record that already round-trips, the `normalizeTheme` "silently strips unknown fields" landmine cannot bite — there are no unknown fields. Exported theme JSON simply reads `"sceneParams": { "palette": 2, "wavelength": 0.6, ... }`.

**If a future version adds editable night or a cross-scene top-level `paletteId`,** *then* `normalizeTheme` needs an additive line and a `ThemeSettings` field — modeled exactly on the `materialId` / `materialParams` precedent (the conditional block already in `normalizeTheme`). Not needed for v1.

---

## G. Blast radius + phased build order

**Files touched (all additive):**

| File | Change |
|------|--------|
| `src/ambient/types.ts` | `AmbientSceneParam` gains `kind?`, `night?`, `options?`, `randomizable?`; add `ChoiceOption`. |
| `src/ambient/sceneRegistry.ts` | `AmbientSceneParamMetadata` + `buildMetadata` carry `kind`/`options`. |
| `src/ambient/scenes/gradient-waves.ts` | Add `PALETTES`; palette choice param; `wavelength.night`; `dayProgress.randomizable:false`; replace hardcoded endpoints with `paletteGlsl` + `dayMix` output. |
| `src/ambient/prelude.ts` (or `scenes/shaderCodegen.ts`) | Extract `daylight()`; add `paletteGlsl()` + `dayMix()` codegen helpers. |
| `src/theme/panel/sections/scene.ts` | Choice-card rendering + shape dice (render + bind). |

**NOT touched (the elegance):** `createAmbientBackground.ts` (renderer), `theme/types.ts` (`ThemeSettings`), `theme/validate.ts` (`normalizeTheme`), `theme/storage.ts`, `theme/migrate.ts`, `main.ts` apply loop.

**Phased order (each phase independently shippable, non-breaking):**

1. **Param model + palettes.** `kind`/`choice`/`options` in types + registry metadata; `PALETTES` + palette GLSL codegen; panel choice cards. Ships preset palettes. Renderer + persistence untouched.
2. **Day-modulation.** `night` + `dayMix` + extract `daylight()` to prelude; wavelength day-pair; panel day-breathe tag.
3. **Randomize.** `randomizable` flag + shape dice in panel.

**YAGNI flags (do not build for v1):** color param kind · editable night value · separate palette dice · tasteful/wild sub-range modes · seeded reproducible rolls · global `PaletteRegistry`.

**One discipline to document:** palette lists are **append-only** (numeric indices are positional); never reorder or delete entries, or stored themes shift palette.

---

## Verification notes (claims checked against source)

- Float bridge is float-only: `setSceneParamUniforms` → `setFloat` → `uniform1f`; new uniforms must be in `UNIFORM_NAMES` or `paramUniforms` to get a location in `createProgram`. A choice param declaring `uniform: "uPalette"` is collected automatically (it goes through `createParamUniforms`). ✔
- `normalizeTheme` rebuilds from an explicit field list but copies `sceneParams` wholesale via spread → choice values survive without a code change. ✔
- `validateSceneParams` range-checks each `sceneParams` entry against registry `min/max` → choice index `0..N-1` validates. ✔
- Scene switch resets `settings.sceneParams = {}` (panel `sceneSection.bind`), then `applyTheme` refills from `paramsFor` defaults → palette defaults to index 0. ✔
- `uDayProgress` is in the prelude uniform set, loop-independent (not wrapped by `wrapSceneTime`) → day-modulation is loop-safe. ✔
- No existing randomize/dice affordance in `src/` → greenfield, no DRY conflict. ✔

## Open questions (for the owner, not blockers)

1. How many curated palettes ship in v1 (3–5)? Drives `PALETTES` length and the `max` of the palette param.
2. Should the day-breathe indicator be purely informational, or a future toggle to disable modulation per param?
3. Confirm append-only palette discipline is acceptable, or whether a stable string id (and the accompanying `ThemeSettings` field) is worth the extra machinery now rather than later.
