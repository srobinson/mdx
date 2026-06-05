# Gradient Waves Scene Control System Proposal

## Headline

Keep `AmbientSceneParam` as the numeric float bridge. Add palettes as a registry backed scene asset, and add day modulation as a small numeric param extension. This keeps color choice, numeric control, day clock, and randomization separated by concern.

## Live architecture facts

- The project is a strict TypeScript, Vite app with React available, but the theme panel is currently vanilla `render(ctx)` plus `bind(host, ctx)`. See `package.json` and `tsconfig.json`.
- fmm is active and current: `.fmm.db` exists, and `fmm validate` reports all 45 files indexed and up to date.
- `AmbientSceneParam` is a range float contract with `id`, optional `uniform`, label, min, max, step, and default value. Theme JSON keys scene params by id, not uniform. See `AmbientSceneParam` in `src/ambient/types.ts:30`.
- `createParamUniforms` maps scene param ids to fragment uniforms, and `FragmentAmbientBackground.setSceneParamUniforms` uploads scalar values every frame. See `createParamUniforms` in `src/ambient/createAmbientBackground.ts:128` and `FragmentAmbientBackground` in `src/ambient/createAmbientBackground.ts:376`.
- `gradientWavesScene` currently hardcodes the day palette in shader constants and computes daylight from `uDayProgress`. See `gradientWavesScene` in `src/ambient/scenes/gradient-waves.ts:68` and `src/ambient/scenes/gradient-waves.ts:74`.
- `sceneSection` renders all scene params as sliders from data, and binds by `data-scene-param`. See `sceneSection` in `src/theme/panel/sections/scene.ts:18` and `src/theme/panel/sections/scene.ts:73`.
- The material registry is the right precedent: typed records, registry integrity checks, metadata projection, panel cards, default params, validation, and additive persistence. See `PaneMaterial`, `createMaterialRegistry`, `resolveMaterial`, and `materialSection` in `src/pane/materials/types.ts:19`, `src/pane/materials/registry.ts:29`, `src/pane/materials/registry.ts:55`, and `src/theme/panel/sections/material.ts:7`.
- `ThemeSettings` is the persistence shape. `validateThemeDefinition` validates known fields, and `normalizeTheme` rebuilds settings from an explicit list, so new fields must be validated and copied there. See `ThemeSettings` in `src/theme/types.ts:24`, `validateThemeDefinition` in `src/theme/validate.ts:151`, and `normalizeTheme` in `src/theme/validate.ts:111`.

## A. Param model recommendation

Do not turn `params` into a universal typed control system with `range | choice | color` kinds.

Keep the current param model as the float bridge and extend it only where the value is still a number:

```ts
interface AmbientSceneParam {
  id: string;
  uniform?: string;
  label: string;
  min: number;
  max: number;
  step: number;
  defaultValue: number;
  dayModulation?: {
    noon: number;
    night: number;
  };
  randomize?: {
    group: string;
    tasteful: { min: number; max: number };
    wild?: { min: number; max: number };
  };
}
```

Rationale:

- Numeric sliders already have a stable storage path through `sceneParams` and a stable renderer bridge through scalar uniforms.
- Palette choice is not a float. Treating it as a param kind would force `ThemeSettings.sceneParams` to stop being `Record<string, number>`, which would disturb validation, migration, and renderer code.
- Day modulation for wavelength is a numeric concern. An optional field on a numeric param gives the declarable noon and night pair requested without inventing a parallel control system.
- Randomization belongs in metadata on the controls it can mutate. The randomizer can discover eligible params by group and write normal settings.

## B. Palette system

Add a small palette registry modeled on the material registry.

Suggested types:

```ts
type Rgb01 = readonly [number, number, number];

interface AmbientDayGradientPalette {
  id: string;
  label: string;
  sceneId: string;
  light: { start: Rgb01; end: Rgb01 };
  dark: { start: Rgb01; end: Rgb01 };
  swatch: AmbientSceneSwatch;
}

interface AmbientPaletteRegistry {
  metadataForScene(sceneId: string): readonly AmbientDayGradientPalette[];
  defaultForScene(sceneId: string): AmbientDayGradientPalette | undefined;
  get(sceneId: string, paletteId: string): AmbientDayGradientPalette | undefined;
  has(sceneId: string, paletteId: string): boolean;
}
```

Place gradient waves palettes in a dedicated source file, for example `src/ambient/palettes/gradient-waves.ts`, then export a registry from `src/ambient/paletteRegistry.ts`. Use material registry patterns: duplicate id checks per scene, metadata projection, and a default lookup. Do not put palettes inside `ThemeSettings`; settings should store only the selected id.

For gradient waves, replace the four hardcoded shader colors with uniforms:

```glsl
uniform vec3 uGradientStart;
uniform vec3 uGradientEnd;
```

The host computes the current colors from the selected palette and the daylight curve, then uploads `uGradientStart` and `uGradientEnd` via `uniform3f`. This centralizes the daylight curve for palette crossfade and day driven params. The shader keeps its scene logic and simply uses `startCol = uGradientStart` and `endCol = uGradientEnd`.

This requires `createProgram` to collect palette uniform names in addition to existing scalar param uniforms. Current uniform collection is in `createProgram` at `src/ambient/createAmbientBackground.ts:111`. Add a `setPaletteUniforms` step beside `setSceneParamUniforms` in `FragmentAmbientBackground.renderFrame`.

## C. Day modulation

Add declarable day modulation to numeric params and resolve it in the renderer host, not separately in each shader.

Daylight function:

```ts
const daylightFromDayProgress = (dayProgress: number) =>
  0.5 + 0.5 * Math.cos((clamp01(dayProgress) - 0.25) * 2 * Math.PI);
```

Upload rule for each param in the active scene:

1. Resolve `dayProgress` from `sceneParams.dayProgress`, then from the local day default.
2. Compute daylight once.
3. For a param with an active day pair, upload `mix(night, noon, daylight)` to its existing uniform.
4. For every other param, upload the current static value from `sceneParams` or the declaration default.

For gradient waves, start with `wavelength` only:

```ts
{
  id: "wavelength",
  uniform: "uWavelength",
  label: "wavelength",
  min: 0,
  max: 1,
  step: 0.01,
  defaultValue: 0.5,
  dayModulation: { noon: 0.22, night: 0.74 },
  randomize: { group: "wave-shape", tasteful: { min: 0.18, max: 0.78 } }
}
```

That gives wide waves at noon and tighter waves at night because the shader maps wavelength to cycles with `mix(1.0, 7.0, uWavelength)` in `gradientWavesScene` at `src/ambient/scenes/gradient-waves.ts:88`.

Loop safety proof:

- `wrapSceneTime` only wraps `uTime`; see `wrapSceneTime` in `src/ambient/createAmbientBackground.ts:36` and the `uTime` upload in `FragmentAmbientBackground` at `src/ambient/createAmbientBackground.ts:345`.
- Day modulation consumes `uDayProgress`, not `uTime`. It therefore cannot introduce a new nonperiodic `uTime` term.
- Existing loop tests require every declared `loopSeconds` to divide the 24 hour day, and gradient waves declares a 600 second loop. See `src/ambient/sceneRegistry.test.ts:58` and `src/ambient/sceneRegistry.test.ts:92`.
- For a seamless capture, hold `uDayProgress` fixed during the captured loop, as the current wall clock seeded day input is an external state. Interactive wall clock drift remains an external crossfade and does not change the internal `uTime` loop contract.

## D. Randomize model

Use separate dice by concern.

Recommended dice:

1. **Shape dice** in the gradient waves scene controls. It mutates only params tagged with `randomize.group === "wave-shape"`: `lines`, `amplitude`, `wavelength`, `stagger`, and `sway`. It never touches `dayProgress`, palette, material, photo, accent, or pane settings.
2. **Palette dice** next to palette cards. It chooses another curated palette id for the active scene. It never changes wave shape or the day clock.
3. No global dice until more scenes declare randomize groups. The mechanism can be general, but visibility should be scene driven.

Use tasteful ranges as the default. Store optional wild ranges in metadata for a later power affordance, but do not ship a wild dice in the first pass. Tasteful ranges keep randomize useful rather than noisy.

Reproducibility should come from persisted settings, not a persisted seed. A dice click writes concrete `sceneParams`, `sceneDayParamPairs`, and `scenePaletteId`. Exported theme JSON then reproduces the result exactly. Tests can inject a deterministic RNG into the randomizer utility. No `sceneRandomSeed` field is needed.

## E. Panel UX

Keep the panel grammar consistent: cards, swatches, segmented groups, sliders. No dropdowns, raw RGB, raw HSL, or modal editor.

Scene section layout:

1. Scene cards.
2. Palette cards for the active scene, with one small palette dice button in the row header.
3. Day control remains visible as the lab time scrubber.
4. A **Wave shape** group with the shape dice in the group header.
5. Normal sliders for nonmodulated params.
6. For a day modulated param, show a compact twin control: `wavelength noon` and `wavelength night`. Each is a standard range control with its own baseline tick.

Do not expose editing of individual palette colors in this slice. The product decision rejected raw HSL and single hue sliders. Preset palette cards are enough.

When the user changes scenes, clear `sceneParams`, `sceneDayParamPairs`, and `scenePaletteId`, then let the registry provide defaults for the new scene. `sceneSection.bind` already clears `sceneParams` on scene change in `src/theme/panel/sections/scene.ts:77`; extend that reset there.

## F. Persistence

Add exactly two optional fields to `ThemeSettings`:

```ts
interface ThemeSettings {
  scenePaletteId?: string;
  sceneDayParamPairs?: Record<SceneParamId, { noon: number; night: number }>;
}
```

Validation rules in `validateThemeDefinition`:

- `scenePaletteId` is optional. When present, it must be a string and `paletteRegistry.has(settings.sceneId, settings.scenePaletteId)` must pass.
- `sceneDayParamPairs` is optional. When present, it must be a record. Every key must match a param on `settings.sceneId` that declares `dayModulation`. `noon` and `night` must be finite numbers within that param's min and max.
- Missing fields remain valid, so no schema bump is required.
- Add import causes for `unknown scene palette` and `unknown day param pair`, mirroring the existing material causes in `ImportErrorCause` at `src/theme/types.ts:64`.

Normalization in `normalizeTheme`:

- Copy `scenePaletteId` only when it is a valid string.
- Deep clone `sceneDayParamPairs` after validation.
- Keep the current material projection untouched. The new fields are additive siblings of `materialId` and `materialParams`, not replacements.

Cloning in `cloneThemeSettings`:

- Add a nested clone for `sceneDayParamPairs` so snapshots and dirty checks are immutable. `cloneThemeSettings` currently clones `sceneParams`, `accent`, and `materialParams` in `src/theme/types.ts:174`.

Storage and export need no new schema version. `ThemeStorageRecordV1` stores full `ThemeDefinition` values, so carrying optional fields through validation and normalization is enough.

## G. Blast radius and phased build order

### Files touched

- `src/ambient/types.ts`: add `dayModulation` and `randomize` to numeric params, plus optional palette control metadata if the registry needs a scene declaration hook.
- `src/ambient/paletteRegistry.ts` and `src/ambient/palettes/gradient-waves.ts`: new registry and curated palettes.
- `src/ambient/sceneRegistry.ts`: include day modulation and randomize metadata in `AmbientSceneParamMetadata`, and preserve duplicate param checks.
- `src/ambient/createAmbientBackground.ts`: retain param definitions per program, compute daylight, resolve day modulated param values, collect palette uniforms, upload vec3 palette colors.
- `src/ambient/scenes/gradient-waves.ts`: declare palettes, replace hardcoded RGB constants with uniforms, add day modulation metadata on wavelength, add randomize metadata on shape params.
- `src/theme/types.ts`: add optional settings fields, clone nested records, add import causes.
- `src/theme/validate.ts`: validate and normalize the optional fields.
- `src/theme/panel/sections/scene.ts`: render palette cards, palette dice, shape dice, and twin noon or night controls.
- `src/main.ts`: pass selected palette and day pairs from validated settings into the ambient background. Keep `applyTheme` as the choke point.
- Tests: `src/ambient/sceneRegistry.test.ts`, `src/theme/theme-data.test.ts`, `src/theme/panel/panel-studio.test.ts`, and a focused palette registry test.

### Build order

1. Add palette registry and tests, with gradient waves palettes only.
2. Extend `ThemeSettings`, validation, normalization, cloning, and tests for optional field round trips and invalid ids.
3. Extend renderer uniform support for vec3 palette colors, then switch gradient waves from hardcoded colors to palette uniforms.
4. Add day modulation metadata and renderer resolution for `wavelength`, with tests proving static params still work and day pairs validate.
5. Add panel palette cards and twin noon or night controls.
6. Add randomizer utility with injectable RNG, then bind shape dice and palette dice.

### YAGNI guardrails

- No generic `range | choice | color` param union in this slice.
- No raw palette editor.
- No shader code generation.
- No persisted random seed.
- No universal dice shown on scenes that did not declare a randomize group.
- No schema bump unless a future breaking export format needs one.
