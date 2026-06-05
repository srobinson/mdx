# Cubicell face typography inventory (external research lens)

**Date:** 2026-08-09  
**Repo version:** `three@0.185.1` (r185), `@react-three/fiber@9.6.1`, `@react-three/drei@10.7.7` (depends on `troika-three-text@^0.52.4`; latest npm is `0.52.5`)  
**Lens:** current state of the art for text on faces / in-scene WebGL text; researched fresh (docs, npm, discourse, product references)

---

## 0. What cubicell does today (baseline)

Faces are instanced `MeshBasicMaterial` quads with:

1. **Colour roles** (per-face color / opacity / visibility).
2. **Seeded SVG stencils** rasterized into a fixed **2048² `DataTexture` atlas** (16 slots × 512px, **RedFormat** monochrome), sampled via **`material.onBeforeCompile`** (`faceStencilShader.ts` + `stencilAtlas.ts`).

Stuart’s pain: **zero text / font / unicode on faces**. Stencils already prove the monochrome-atlas + tint pattern works. Text wants the same contract if it is face content.

---

## 1. Landscape summary (four real options)

| Approach | Mechanism | Bundle / cost | Unicode reality | r185 fit | Face-atlas fit |
| --- | --- | --- | --- | --- | --- |
| **A. Canvas-2D → texture / atlas** | `fillText` / `measureText` → `CanvasTexture` or single-channel `DataTexture` slots | Zero new deps if browser canvas; GPU upload only | Full system shaping via browser (RTL, complex scripts, emoji **as browser paints them**) | First-class (`CanvasTexture`) | **Best match** to current stencil path |
| **B. troika-three-text (SDF)** | Runtime TTF/OTF/WOFF parse (Typr) + on-the-fly SDF atlas in worker; patches materials | npm package ~843KB unpacked + deps (`bidi-js`, troika-utils, `webgl-sdf-generator`); peer `three>=0.125`; **already pulled by drei** | Strong: kerning, ligatures, RTL/bidi, Arabic joining; Noto fallback CDN (~300MB full self-host) | WebGL classic mature; WebGPU material patch fragile | **Poor for instanced faces** (separate meshes, material derive) |
| **C. Bitmap / MSDF atlas (offline)** | Prebuilt glyph sheet + BMFont layout (msdf-bmfont-xml, Angelcode, Hiero) | Atlas PNG + small JSON; shader sample cost only | **Charset-limited** unless huge multi-page atlases | Compatible via custom GLSL / three-bmfont ports | Good if fixed alphabet; weak for free unicode |
| **D. TextGeometry / FontLoader** | typeface.json / TTF → extruded triangle mesh | Facetype.json conversion; high triangle count | Latin-centric in practice; poor complex scripts | Addon `TextGeometry` + `FontLoader`/`TTFLoader` | **Wrong tool for face planes** (geometry weight, not texture) |

Authoritative survey of WebGL text techniques (geometry, canvas, bitmap, SDF, MSDF): [CSS-Tricks, Techniques for Rendering Text with WebGL](https://css-tricks.com/techniques-for-rendering-text-with-webgl/).

---

## 2. troika-three-text (MSDF-class runtime SDF)

### 2.1 Maturity (as of 2026-08)

- **Package:** `troika-three-text@0.52.5` (npm modified 2026-07-24); docs last update 2026-07-24.
- **Docs:** [protectwise.github.io/troika/troika-three-text](https://protectwise.github.io/troika/troika-three-text/)
- **Repo:** [github.com/protectwise/troika](https://github.com/protectwise/troika)
- **Ecosystem:** Official path for `@react-three/drei` **`<Text />`** ([drei Text](https://github.com/pmndrs/drei#text)); A-Frame, threepipe plugins; still listed among top three.js tools in 2026 roundups.
- **Peer:** `three >= 0.125.0` → **r185 is fine**.

### 2.2 How it works

1. Parses **.ttf / .otf / .woff** (**.woff2 not supported**).
2. Generates **SDF atlas on demand** (default `sdfGlyphSize=64`, power-of-two); optional **GPU-accelerated SDF** (`gpuAccelerateSDF: true`).
3. Layout + shaping in a **web worker** (can force main thread for CSP: `configureTextBuilder({ useWorker: false })`).
4. Builds glyph quads and **derives / patches any Three.js Material** with SDF sampling + derivatives AA.
5. API: `new Text()`, set props, `sync()` (async; `synccomplete` event).

### 2.3 Unicode / shaping

| Capability | Status |
| --- | --- |
| Kerning, ligatures | Yes |
| RTL / bidi | Yes (`direction: 'auto'|'ltr'|'rtl'`) |
| Joined scripts (Arabic) | Yes (docs) |
| Fallback fonts | [unicode-font-resolver](https://github.com/lojjic/unicode-font-resolver/) → Google Noto ranges; default jsDelivr CDN; **full self-host ~300MB** |
| Complex Indic / CJK shaping depth | Better than naive glyph maps; not HarfBuzz-complete for every edge case; countertype/three-text claims richer TeX layout if needed |
| Color emoji | **Not a first-class path.** SDF is monochrome distance; color emoji fonts / CBDT/COLR do not map cleanly. Expect tofu, mono outlines, or browser-dependent fallbacks—not Apple/Google color emoji fidelity |
| Variable fonts | Limited relative to geometry/vector engines |

### 2.4 Bundle size (practical)

| Layer | Size signal |
| --- | --- |
| `troika-three-text` unpacked | ~843 KB (npm `dist.unpackedSize`) |
| Direct deps | `bidi-js`, `troika-three-utils`, `troika-worker-utils`, `webgl-sdf-generator@1.1.1` |
| cubicell today | **Already present** via `@react-three/drei` → `troika-three-text@0.52.4` (nested pnpm). Face path does not import it yet; **no extra install** if only using drei `Text` for non-face labels |

Tree-shaken app impact is smaller than unpacked, but workers + SDF generator are not free. Compare to canvas: **zero bytes**.

### 2.5 Limits that matter for cubicell

- **Per-string meshes**, not instanced face slots. Does not plug into the 16-slot RedFormat atlas without a custom “render troika to RTT then copy slot” bridge.
- Material patching is **classic WebGL-oriented**. WebGPU / TSL path: known friction ([discourse: Troika three text and WebGPU](https://discourse.threejs.org/t/troika-three-text-and-webgpu/55737)).
- Async first paint: use `preloadFont({ font, characters })` for known alphabets.
- CSP: worker via blob/eval-style may need `useWorker: false`.

**Role for cubicell:** world-space labels, HUD billboards, editable captions **off** the instanced face material—not the first tool for “text as face stencil content.”

---

## 3. Canvas-2D rasterization → texture (face-native path)

### 3.1 Pattern

```text
canvas.measureText / fillText
  → ImageData or canvas element
  → CanvasTexture | copy into DataTexture (R channel)
  → same onBeforeCompile sample + face tint as stencils
```

This is the **oldest and still production-default** “arbitrary string on a surface” path ([CSS-Tricks canvas section](https://css-tricks.com/techniques-for-rendering-text-with-webgl/); three.js `CanvasTexture`).

### 3.2 Crispness techniques (current best practice)

| Technique | Why |
| --- | --- |
| **Oversample** | Render at 1.5–2× face texels (e.g. 512 slot → draw at 768–1024) then downsample, or lock face UV density |
| **Padding / gutters** | Cubicell already uses `stencilAtlasGutter = 1`; text needs more (4–8 px) so AA fringes do not bleed into neighbors |
| **Mipmaps** | Enable when camera distance varies a lot; pair with `LinearMipmapLinearFilter`. For **near-fixed face size**, many apps set `generateMipmaps = false` + `LinearFilter` (stencils already do this) |
| **Anisotropy** | `texture.anisotropy = renderer.capabilities.getMaxAnisotropy()` for glancing cube angles |
| **magFilter** | `LinearFilter` for soft AA; `NearestFilter` only for intentional pixel fonts |
| **colorSpace** | Treat monochrome mask as data or sRGB carefully; keep mask in R and tint in shader (matches stencil) |
| **`needsUpdate`** | Set only when the string or style changes—not every frame |

Forum signal on blur after migration: [discourse “canvas text more blurry”](https://discourse.threejs.org/t/after-migration-canvas-text-more-blurry/66540); filter/anisotropy guidance: [discourse crispness thread](https://discourse.threejs.org/t/why-doesnt-my-canvas-texture-look-crisper-and-accurate-when-i-zoom-it/46122).

### 3.3 Determinism caveats (critical for creative-canvas product)

| Risk | Reality |
| --- | --- |
| **Font metrics** | OS + browser differ (ascent, kerning, hinting). Same CSS font-family → different pixel boxes |
| **Font availability** | Must **self-host** (e.g. existing `@fontsource/geist-mono`) and wait for `document.fonts.ready` before measure/fill |
| **Emoji / color fonts** | Platform-dependent color emoji; COLR/CBDT/SVG-in-OT; **not stable** across Safari/Chrome/Firefox |
| **Subpixel AA** | Canvas may use LCD AA; converting to single-channel grayscale loses subpixel and can look muddy—prefer grayscale fill on transparent then take alpha or max(RGB) |
| **RTL / bidi** | Browser handles if you set canvas text direction / use full strings; do not hand-split graphemes without a segmenter |
| **Locale shaping** | Best of the free options for complex scripts **if** a covering font is loaded |

**Role for cubicell:** **primary recommendation for face text.** Extend `stencilAtlas` (or a parallel text atlas with dynamic slots) with `ctx.fillText` monochrome masks. Keeps one draw path, face tint, and instancing.

---

## 4. TextGeometry and bitmap-font approaches

### 4.1 TextGeometry (three.js addon)

- **API:** `TextGeometry` + `Font` from `FontLoader` (typeface.json) or `TTFLoader` path; drei wraps as **`<Text3D />`** via three-stdlib.
- **Docs index:** [three.js TextGeometry addon](https://threejs.org/docs/#examples/en/geometries/TextGeometry)
- **Cost:** high triangle density; CSS-Tricks example: one paragraph ≈ **185k triangles**.
- **Unicode:** limited to glyphs in the typeface file; no bidi/layout engine.
- **Face fit:** extruded 3D logos / titles only. **Do not use for face content.**

### 4.2 Offline bitmap / MSDF atlases

**Generators:**

| Tool | Notes |
| --- | --- |
| [Angelcode BMFont](https://www.angelcode.com/products/bmfont/) | Classic BMFont format |
| [msdf-bmfont-xml](https://github.com/soimy/msdf-bmfont-xml) | MSDF/SDF BMFont + spritesheet; CLI |
| [msdf-bmfont-web](https://github.com/donmccurdy/msdf-bmfont-web) | Browser generator |
| [Hiero](https://github.com/libgdx/libgdx/wiki/Hiero) | Bitmap + effects |
| [msdfgen](https://github.com/Chlumsky/msdfgen) | Upstream MSDF engine |

**Runtime consumers (three):** legacy [three-bmfont-text](https://github.com/Jam3/three-bmfont-text); TS port [three-text-geometry](https://github.com/gumob/three-text-geometry) claims ~10× faster than canvas for animated glyph meshes.

**Unicode reality:** atlas size explodes with full Unicode. Fine for **Latin UI chrome**, icons, pixel aesthetic. Bad for user free-text worldwide without multi-page atlases + fallbacks.

**Face fit:** possible (sample MSDF in `onBeforeCompile`), but **charset policy** is product work. Canvas + self-hosted font defers policy to the font file.

---

## 5. Font subsetting tooling

Needed for self-hosting without multi-MB Noto dumps.

| Tool | Role |
| --- | --- |
| **[fonttools](https://github.com/fonttools/fonttools) `pyftsubset`** | Industry standard subset by unicode ranges / glyphs / text files |
| **[glyphhanger](https://github.com/filamentgroup/glyphhanger)** | Crawl site / strings → subset (Chrome + fonttools) |
| **HarfBuzz subset** | Fast binary subset; used in pipelines behind many tools |
| **@fontsource / google-webfonts-helper** | Pre-subset families; cubicell already has `@fontsource/geist-mono` |
| **unicode-font-resolver (troika)** | Runtime range → Noto file; optional self-host of data packages |

**Practice for face text:** pick one UI font, subset to product locales (e.g. Latin + digits + punctuation first), load via FontFace API, rasterize after `fonts.ready`. Expand ranges as markets demand.

---

## 6. What comparable grid / voxel / creative-canvas products do

| Product class | In-scene text approach | Takeaway for cubicell |
| --- | --- | --- |
| **Minecraft** (Java fonts) | Composable **providers**: bitmap glyph PNGs, space, optional TTF, unihex/Unifont fallback; monochrome emoji in Mojangles; no full color-emoji fidelity ([minecraft.wiki/Font](https://minecraft.wiki/w/Font)) | Grid/creative worlds accept **bitmap + fallback**, monochrome glyphs tinted by color codes |
| **Voxel engines** | Bitmap fonts on HUD or baked into face textures; rarely full HarfBuzz in-world | Keep face text simple; HUD can be richer |
| **Tinkercad / print CAD** | Extruded text as **solid geometry** for manufacturing | Maps to TextGeometry—not face painting |
| **Spline / Figma 3D embeds** | Often **HTML/CSS overlay** or baked textures for labels; not glyph engines on every surface | Prefer DOM for editor chrome; WebGL for face-baked content |
| **WebGL marketing sites** | Mix: canvas labels, troika for 3D type, MSDF for hero titles | Same split: face bake vs free-floating type |

**Pattern:** creative grids that put text **on blocks** use **texture glyphs** (bitmap or raster), not extruded meshes. Unicode beyond Latin is a **fallback font layer**, not infinite atlases.

---

## 7. Fit matrix for cubicell faces

| Need | Recommended | Avoid |
| --- | --- | --- |
| Short labels on faces, monochrome + face tint | **Canvas → RedFormat atlas slot** (extend stencil pipeline) | TextGeometry |
| Free unicode user text on faces | Canvas + self-hosted subset + `fonts.ready`; accept platform emoji limits | Pure offline MSDF of full Unicode |
| Floating 3D titles / billboards | **drei `<Text />` / troika** (already in tree) | Baking every label into face atlas |
| Pixel / brand icon set | Offline MSDF or bitmap atlas | Runtime full-font SDF for icons only |
| Color emoji fidelity on faces | Treat as **image content** (media scout path), not fonts | Expecting SDF/troika to paint COLR emoji |
| WebGPU migration later | Canvas textures still work; troika material patch may need rework | Coupling face text to troika shaders |

---

## 8. Capability inventory (can / cannot today with r185 + stack)

| Capability | On classic WebGL r185 now | Notes |
| --- | --- | --- |
| Monochrome face text via atlas | **Can** (no new dep) | Mirror stencil rasterizer with `fillText` |
| Latin UI strings | **Can** | Subset Geist Mono or product font |
| RTL / Arabic on faces | **Can** via canvas if covering font loaded | Test shaping; do not roll own bidi |
| Full Unicode via troika | **Can** for **meshes** | Not instanced faces without bridge |
| Color emoji as first-class face glyphs | **Weak** | Platform-dependent; prefer image slots |
| Extruded 3D type | **Can** (Text3D / TextGeometry) | Wrong for faces |
| Zero-deps face text | **Can** | Canvas + FontFace |
| Deterministic cross-OS pixel match | **Cannot guarantee** | Self-host fonts; snapshot tests on one browser |

---

## 9. Sources (primary)

| Source | URL |
| --- | --- |
| Troika three-text docs | https://protectwise.github.io/troika/troika-three-text/ |
| troika-three-text npm | https://www.npmjs.com/package/troika-three-text |
| unicode-font-resolver | https://github.com/lojjic/unicode-font-resolver/ |
| CSS-Tricks WebGL text techniques | https://css-tricks.com/techniques-for-rendering-text-with-webgl/ |
| three.js CanvasTexture | https://threejs.org/docs/#api/en/textures/CanvasTexture |
| three.js TextGeometry (addon) | https://threejs.org/docs/#examples/en/geometries/TextGeometry |
| msdf-bmfont-xml | https://github.com/soimy/msdf-bmfont-xml |
| Angelcode BMFont | https://www.angelcode.com/products/bmfont/ |
| Minecraft font providers | https://minecraft.wiki/w/Font |
| discourse Troika intro | https://discourse.threejs.org/t/troika-3d-text-library-for-sdf-text-rendering/15111 |
| discourse Troika + WebGPU | https://discourse.threejs.org/t/troika-three-text-and-webgpu/55737 |
| WebGLFundamentals glyph atlas | https://webglfundamentals.org/webgl/lessons/webgl-text-glyphs.html |
| drei Text (troika wrapper) | installed `@react-three/drei@10.7.7` → `troika-three-text@0.52.4` |

---

## 10. Verdict

**For face text: canvas (or equivalent) monochrome raster into the existing atlas + tint path is the least-resistance, r185-native answer; troika (already via drei) is for free-floating labels, not instanced faces; TextGeometry is the wrong tool; offline MSDF only if the alphabet is closed.**

Unicode is a **font + browser shaping** problem on the canvas path, not a three.js version gap. Color emoji is an **image** problem, not a font-SDF problem.
