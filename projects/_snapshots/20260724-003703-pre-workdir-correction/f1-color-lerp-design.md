# F1 Color Lerp Design: color space for piece-state transitions

Scope: color-space math for animated transitions between `CubePartColor` tokens. The code seam is owned by a separate scout; this doc defines the space, the Three.js usage, the helper shape, and where the lerp runs. All API claims verified against the installed `three@0.185.1` source in the f1 worktree (not from memory), plus `@react-three/fiber@9.6.1` dist.

## Context (as found in the worktree)

- Tokens are categorical: `CubePartColor = 'theme' | 'black' | 'white'` (`src/domain/cube.ts:19`). More tokens are planned.
- Resolution is string-valued and theme-owned: `resolveCubePartColor(color, polarity)` returns a hex string from `ScenePolarityConfig` (`src/theme/scenePolarity.ts:24`). `'theme'` resolves to `polarity.contrast`, and black/white remap between artifact (`#050505`/`#ffffff`) and workbench (`#262626`/`#d8d8d8`) palettes. Resolved colors are therefore theme dependent, twice over: polarity (black/white) and mode (artifact/workbench).
- The renderer resolves per frame in `syncInstancedPartMesh` (`src/scene/instancedPartMeshCore.ts:83`): `partColor.set(hexString)` then `mesh.setColorAt(index, partColor)`. Material is `MeshBasicMaterial` with `toneMapped: false`, so the only output transform is the linear-to-sRGB encode.
- Palette today: near-black, white, two workbench grays, and one chromatic accent (`selectionAccent: '#e87d0d'`, an orange).

## Three.js color management facts (r185, verified in source)

- `ColorManagement.enabled` defaults to `true`; R3F v9 sets it to `!legacy` and `legacy` is off by default. `ColorManagement.workingColorSpace` is `LinearSRGBColorSpace`.
- `Color.set('#hex')` routes through `setStyle`/`setHex` with `colorSpace = SRGBColorSpace`, which calls `ColorManagement.colorSpaceToWorking`. A `Color` built from a hex token therefore holds **linear-sRGB** components. (Note the r165+ names: `colorSpaceToWorking` / `workingToColorSpace` / `convert`; the older `fromWorkingColorSpace` / `toWorkingColorSpace` are gone.)
- `Color.lerp` / `Color.lerpColors` are plain component lerps on whatever the components are, so in practice they interpolate in **linear sRGB**. `Color.lerpHSL` interpolates in HSL derived from the working-space components.
- `InstancedMesh.setColorAt` copies components verbatim into the `instanceColor` buffer; the shader consumes them as working-space linear and the renderer applies the sRGB output transfer at the end. Invariant: any `Color` handed to `setColorAt` must hold working-space values, which `color.set(hex)` already guarantees.
- **Three has no OKLab/OKLCH support anywhere**, core or `examples/jsm` (grepped r185). If we want OKLab we write ~20 lines of math ourselves.

## 1. Which color space

| Space | Perceptual uniformity | Hue path | Gray-through-middle | Edge cases for this palette |
|---|---|---|---|---|
| sRGB (gamma) | Poor. Midpoints between saturated hues go dark and muddy | Straight line in gamma cube | Yes | None, but worst visual quality |
| Linear RGB (three's `lerpColors`) | Poor for lightness: perceived lightness is roughly the cube root of linear luminance, so a black-to-white lerp jumps out of black immediately and crawls through the bright half | Straight line in linear cube | Yes | Bad fit: this palette is dominated by black/white/gray endpoints, exactly where the linear lightness ramp is most lopsided |
| HSL (`lerpHSL`) | Poor. L is not perceived lightness (blue and yellow at L 0.5 differ wildly) | Hue angle, avoids gray middle | No | Achromatic endpoints have undefined hue (three reports h=0, red), so black/white to accent transitions sweep through arbitrary hues; gamma-space cylinder inherits sRGB nonuniformity |
| OKLab | Good. Designed for uniform perceived rate of change; L tracks perceived lightness | Straight line in Lab | Only for hue-opposed saturated pairs | None. Achromatic colors are simply a=b=0, no undefined-hue problem; plain component lerp, no angle wrapping |
| OKLCH | Same as OKLab | Hue angle, preserves chroma | No | Undefined hue at achromatic endpoints, which this palette hits constantly; needs shortest-arc hue interpolation logic |

**Recommendation: OKLab (rectangular), implemented explicitly.** Reasoning:

- The palette is neutrals plus accents. Every transition involving black, white, or gray is an OKLCH/HSL edge case (undefined hue) and a linear-RGB worst case (lopsided lightness ramp). OKLab handles all of them with zero special-casing and gives a uniform perceived speed, which is the whole point of animating the change.
- The gray-through-desaturation artifact only bites on hue-opposed saturated pairs (for example red to green). No such token pair exists or is planned near-term. If one appears, upgrade the helper to OKLCH with shortest-arc hue; the OKLab conversion is the first half of that math anyway, so nothing is thrown away.
- OKLab is the CSS Color 4 default direction (`oklab()`, `oklch()`, `color-mix(in oklab, ...)`), so canvas transitions will match any future CSS-side transitions of the same tokens.
- Three's built-in `lerp`/`lerpColors` is **not adequate** (linear-sRGB ramp distortion on the black/white heavy palette) and `lerpHSL` is **not adequate** (achromatic hue edge case plus gamma cylinder). Explicit OKLab math is required, and it is small.

One structural bonus: OKLab is defined from linear sRGB, and three's working color space already is linear sRGB. The `Color` components are exactly the input the OKLab transform wants, so the helper needs no gamma handling at all.

## 2. Concrete Three.js usage

Resolving a token, respecting color management (this is what the sync path already does):

```ts
const color = new Color() // reused scratch, never allocated per frame
color.set(resolveCubePartColor(token, polarity)) // sRGB hex in, working-space linear out
```

OKLab lerp between two working-space colors (Ottosson's reference constants; inputs and outputs are linear sRGB, which matches `ColorManagement.workingColorSpace`):

```ts
import { Color } from 'three'

// Mirrors Color.lerpColors: writes the result into target and returns it.
export function lerpColorsOklab(
  target: Color,
  from: Color,
  to: Color,
  t: number,
): Color {
  const [l1, a1, b1] = oklabFromLinearSrgb(from.r, from.g, from.b)
  const [l2, a2, b2] = oklabFromLinearSrgb(to.r, to.g, to.b)
  return linearSrgbIntoColor(
    target,
    l1 + (l2 - l1) * t,
    a1 + (a2 - a1) * t,
    b1 + (b2 - b1) * t,
  )
}

function oklabFromLinearSrgb(r: number, g: number, b: number) {
  const l = Math.cbrt(0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b)
  const m = Math.cbrt(0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b)
  const s = Math.cbrt(0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b)
  return [
    0.2104542553 * l + 0.793617785 * m - 0.0040720468 * s,
    1.9779984951 * l - 2.428592205 * m + 0.4505937099 * s,
    0.0259040371 * l + 0.7827717662 * m - 0.808675766 * s,
  ] as const
}

function linearSrgbIntoColor(target: Color, L: number, a: number, b: number) {
  const l = (L + 0.3963377774 * a + 0.2158037573 * b) ** 3
  const m = (L - 0.1055613458 * a - 0.0638541728 * b) ** 3
  const s = (L - 0.0894841775 * a - 1.291485548 * b) ** 3
  // Clamp: OKLab midpoints between in-gamut colors can exit sRGB slightly.
  return target.setRGB(
    clamp01(4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s),
    clamp01(-1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s),
    clamp01(-0.0041960863 * l - 0.7034186147 * m + 1.707614701 * s),
    LinearSRGBColorSpace, // components are already working space; skip conversion
  )
}
```

Notes:

- `setRGB` defaults to `ColorManagement.workingColorSpace`, so passing `LinearSRGBColorSpace` explicitly is belt and braces; both are correct today. The helper's stated invariant is that the working color space is linear sRGB (three's default, never overridden in this repo). If a future change redefines the working space, the matrices need a conversion step; assert or document it.
- Zero allocation per call apart from the two small tuples; flatten to scalars if profiling ever cares. Endpoint OKLab coordinates can be cached per (token, polarity) since both sets are tiny, leaving one lerp and one OKLab-to-linear conversion per instance per frame.
- `toneMapped: false` on the materials means the lerped value reaches the screen through the sRGB output transfer only, so what the math produces is what the user sees.
- Easing belongs to the animation timeline (the evaluator's `t`), not to the color math. The helper stays linear in `t`.

## 3. Reusable helper design

Two levels, mirroring three's own API shape:

```ts
// Level 1: pure color-space math, token-agnostic, N-color capable.
lerpColorsOklab(target: Color, from: Color, to: Color, t: number): Color

// Level 2: token-aware convenience for the sync path.
resolveLerpedPartColor(
  target: Color,
  from: CubePartColor,
  to: CubePartColor,
  t: number,
  polarity: ScenePolarityConfig,
): Color // resolves both endpoints via resolveCubePartColor, then lerpColorsOklab
```

Level 1 generalizes to N tokens trivially: it never sees tokens, only resolved colors. Multi-stop transitions (A to B to C) are the timeline's job; it feeds segment-local `t` into pairwise lerps.

**Layer: scene, not domain.** The domain layer is deliberately three-free and categorical (tokens only). The theme layer is string-valued and has no three import today; giving it `Color` math would couple it to the renderer library for no benefit. The helper operates on `Three.Color` and is consumed by `syncInstancedPartMesh`, so it belongs beside it in `src/scene/` (a small `colorSpace.ts` or wherever the seam scout places the sync extension). Level 2's exact home should follow the seam owner's shape for how `InstancedPart` carries the transition (for example `colorFrom`/`colorTo`/`mix`); this doc intentionally does not fix that contract.

## 4. Evaluator vs renderer

**Lerp in the renderer.** Resolved colors are not theme independent:

- `'theme'` resolves to `polarity.contrast`, which flips between black and white polarity.
- `'black'`/`'white'` remap between artifact and workbench palettes (`#050505` vs `#262626`, `#ffffff` vs `#d8d8d8`).

If the evaluator lerped resolved colors it would bake the active theme into evaluation output, so a polarity or mode switch mid-transition would keep animating toward a stale palette, and evaluation output would stop being pure, replayable domain data. The existing architecture already draws this line: parts carry categorical `CubePartColor` and the renderer resolves per frame against the live polarity.

Therefore: the evaluator emits categorical endpoints plus normalized progress (`from` token, `to` token, `t`); the renderer resolves both endpoints against the current polarity each frame and calls the OKLab lerp. A theme flip mid-transition re-resolves correctly for free, and evaluator tests stay hex-free.

## Summary

OKLab, implemented as ~30 lines of explicit math in the scene layer, lerping renderer-resolved endpoint colors per frame from categorical evaluator output. Three's built-ins (`lerpColors` = linear sRGB, `lerpHSL` = gamma HSL) are both wrong for a black/white/gray-heavy token palette, and three r185 ships no OKLab.
