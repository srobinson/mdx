# Cubicell face media capability inventory (external research lens)

**Date:** 2026-08-09  
**Repo version:** `three@0.185.1` (r185), `@react-three/fiber@9.6.1`, `@react-three/drei@10.7.7`  
**Latest three.js at research time:** r185 (same as installed)  
**Lens:** current state of the art, researched fresh (docs, releases, discourse, examples)

---

## 0. What cubicell does today (baseline)

Faces are instanced `MeshBasicMaterial` quads with:

1. **Colour roles** (per-face color / opacity / visibility).
2. **Seeded SVG stencils** rasterized into a fixed **2048² `DataTexture` atlas** (16 slots × 512px), sampled via **`material.onBeforeCompile`** GLSL injection (`faceStencilShader.ts` + `stencilAtlas.ts`).

That is already a production pattern for “rich figure on a face” under WebGL: one draw call, one atlas sample, no per-face materials.

---

## 1. Shaders: ShaderMaterial vs TSL / NodeMaterial

### 1.1 Two parallel material stacks

| Stack | Entry APIs | Renderer | Custom shader style |
| --- | --- | --- | --- |
| **Classic** | `MeshBasicMaterial`, `ShaderMaterial`, `RawShaderMaterial`, `onBeforeCompile` | `WebGLRenderer` | GLSL strings, includes, program cache keys |
| **Nodes / TSL** | `Mesh*NodeMaterial`, `NodeMaterial`, TSL graph (`colorNode`, `fragmentNode`, …) | **`WebGPURenderer` only** (WebGPU preferred, WebGL2 fallback backend) | JS/TSL, compiles to WGSL or GLSL |

**Authoritative position (three.js maintainers, r164 era, still current architecture):**

> Node materials are supported only with `WebGPURenderer` (which can target WebGPU *or* WebGL2). Classic `WebGLRenderer` had limited/legacy node support and that path was removed.  
> Source: [discourse r164 nodes thread](https://discourse.threejs.org/t/r164-nodes-no-longer-working-with-webgl-webgl2/64909) (Mugen87): *“We have decided to support the new node material only with `WebGPURenderer`…”*

**Critical migration fact for cubicell:**

> `ShaderMaterial`, `RawShaderMaterial`, and **`onBeforeCompile` will not work on `WebGPURenderer`**.  
> Source: same thread, Mugen87. The replacement path is TSL / node materials.

TSL itself is a JS node graph that **transpiles to WGSL (WebGPU) or GLSL (WebGL2 backend of WebGPURenderer)** so one shader codebase can target both backends: [TSL docs](https://threejs.org/docs/TSL.html), [Field guide to TSL and WebGPU](https://blog.maximeheckel.com/posts/field-guide-to-tsl-and-webgpu/) (2025-10).

### 1.2 Does TSL work on classic `WebGLRenderer`?

**No, not as the primary/supported path.**

- Official story since ~r164: nodes/TSL → `WebGPURenderer` only.
- GitHub issue [#30185 “WebGLRenderer: Add support for Node Materials”](https://github.com/mrdoob/three.js/issues/30185) was milestoned **r184**.
- In **r184**, WebGLRenderer gained a **NodeMaterial compatibility layer** ([PR #32851](https://github.com/mrdoob/three.js/pull/32851), listed in [r184 release notes](https://github.com/mrdoob/three.js/releases/tag/r184)). Treat this as a **compat/migration aid**, not as “ship TSL on classic WebGLRenderer as the long-term design.” Production guidance and examples still orient around `import { WebGPURenderer } from 'three/webgpu'` + node materials.

**Practical rule for cubicell:**

- Stay on **classic WebGL + `onBeforeCompile`** for the existing stencil path (what we ship today).
- Any **TSL / compute / modern post** requires **`WebGPURenderer`** (or a deliberate dual-path experiment).

### 1.3 WebGPURenderer maturity (as of r185)

| Claim | Evidence | Caveat |
| --- | --- | --- |
| First-class in three.js | Full docs, massive r183–r185 changelog surface for WebGPU/TSL | Still under active development |
| Dual backend | Tries WebGPU; can force WebGL via `forceWebGL: true` ([docs](https://threejs.org/docs/pages/WebGPURenderer.html)) | Feature parity not perfect vs decade of WebGLRenderer |
| “Production-ready” marketing | e.g. [utsobo 2026 summary](https://www.utsubo.com/blog/threejs-2026-what-changed) (r171 zero-config imports) | Forum consensus still mixed |
| Real-world caution | [Feb 2026 discourse](https://discourse.threejs.org/t/webgpu-renderer-vanilla-three-js-vs-r3f-maturity-and-pitfalls/89661): WebGL still safest for ship; WebGPU catching up | [Jan 2026 perf regression report](https://discourse.threejs.org/t/webgpu-significant-performance-drop-and-shadow-quality-regression-in-r182-vs-webgl-r170/89322); maintainers: “still actively developed” |
| Ecosystem | R3F supports WebGPU; Threlte historically warned early stage ([docs](https://threlte.xyz/docs/learn/advanced/webgpu/)) | Check R3F/drei version matrix before switching |

**r185 is current latest** ([releases](https://github.com/mrdoob/three.js/releases)): HTMLTexture HTML-in-Canvas updates, extensive TSL/WebGPURenderer work, InstancedMesh + render bundles improvements, etc. Cubicell is not “behind” on three version for media capability.

---

## 2. VideoTexture: current best practice

### 2.1 API surface (r185, installed)

From `node_modules/three/src/textures/VideoTexture.js` (r185):

- Construct with `HTMLVideoElement`.
- `generateMipmaps = false` by default.
- Uses **`video.requestVideoFrameCallback`** when available to set `needsUpdate` only on real frame advances (CPU/GPU friendly vs per-rAF blind updates).
- **WebGPU note in source:** when using video with `WebGPURenderer`, set `texture.colorSpace = THREE.SRGBColorSpace`.

Related r185 types:

| Class | Role |
| --- | --- |
| **`VideoTexture`** | Standard path: bind HTML video element |
| **`VideoFrameTexture`** | Manual frames via `setFrame()`; intended for **WebCodecs** decoded frames |
| **`HTMLTexture`** | Texture from HTML element; listens for parent canvas paint events; r184–r185 work on **HTML-in-Canvas / WICG** signatures |
| **`CanvasTexture`** | 2D canvas as texture (generative / animated CPU draw) |
| **`ExternalTexture`** | External GPU resources (WebGPU-oriented) |

### 2.2 Autoplay policies (browser, not three)

Must treat as product constraints:

1. **Muted + playsInline + loop** for reliable autoplay without gesture (Chrome/Safari/iOS).
2. **User gesture** required for audio-on playback.
3. **iOS** historically fragile: `playsInline`, muted, correct codec, and sometimes visibility/play after user interaction ([iOS VideoTexture notes](https://blog.markkulab.net/post/resolve-three-js-video-texture-is-not-working-in-ios)).

**R3F/drei helper** [`useVideoTexture`](https://drei.docs.pmnd.rs/loaders/video-texture-use-video-texture) defaults (current docs):

```ts
muted = true
loop = true
playsInline = true
start = true
unsuspend = 'loadedmetadata'
crossOrigin = 'anonymous'
// optional HLS config
```

That is the de facto R3F best practice; cubicell already depends on drei.

Official example: [webgpu_materials_video](https://threejs.org/examples/webgpu_materials_video.html) (video material under WebGPU path).

### 2.3 Codecs / HDR / format constraints

| Topic | Practice |
| --- | --- |
| **Codecs** | H.264 (mp4) still widest; VP9/AV1 where you control clients; always dual-source if you care about Safari vs Chrome |
| **Resolution** | Prefer ≤1080p for multi-face grids; 4K video textures on mobile are a known pain ([community reports](https://www.reddit.com/r/threejs/comments/5rftcy/threejs_4k_video_texture_mobile_no/)) |
| **Color** | Set `texture.colorSpace = SRGBColorSpace` (especially WebGPU path); washed-out video is usually color-space, not shader bugs ([discourse](https://discourse.threejs.org/t/videotexture-is-bright-and-washed-out/60287)) |
| **HDR video** | Not a first-class “drop HDR10 stream on a mesh” path. HDR *images* for lighting use `HDRLoader` / UltraHDR; video HDR is browser/decode dependent and rare in mesh apps |
| **Streaming** | HLS via video element + hls.js (drei supports hls options); WebCodecs → `VideoFrameTexture` for custom pipelines |
| **CORS** | Cross-origin video needs `crossOrigin` + server CORS headers or GPU will taint / fail upload |

### 2.4 Performance model for a *cube grid*

Per active `VideoTexture`:

- Decoder cost (CPU/HW decode).
- Upload / texture update each new frame (`requestVideoFrameCallback` helps avoid redundant uploads).
- Fragment cost of sampling large textures on many instances.

**Scaling implications for cubicell:**

| Strategy | Draw calls | Decode cost | Fit for grid |
| --- | --- | --- | --- |
| One video material, many instances share same `VideoTexture` | Low | 1 decoder | Good for “all faces same channel” |
| Unique video per face | Explodes | N decoders | Bad beyond handful of faces |
| Video atlas (render several videos into one RT / canvas) | Medium | N decodes still | Hard; rare |
| Poster + play on focus | Low idle | On demand | Best product default |

Recommend: **shared streams + selection-driven play**, not N independent videos across a grid.

---

## 3. How modern three.js apps put rich media on mesh faces

### 3.1 Pattern inventory

| Pattern | Mechanism | Pros | Cons | cubicell fit |
| --- | --- | --- | --- | --- |
| **A. Texture atlas (static)** | Rasterize assets into `DataTexture` / canvas atlas; sample by UV/slot index | 1 draw, GPU cheap | Fixed capacity, update cost on change | **Already shipping** for stencils |
| **B. Per-instance map attributes** | Instanced UV offsets into atlas or `DataArrayTexture` layers | Scales with instances | Complex UV math; array texture support varies | Natural extension of A |
| **C. Material `map` = image** | `TextureLoader` / KTX2 compressed maps | Simple | Per-material or multi-draw if unique | Fine for rare unique faces |
| **D. VideoTexture map** | Video → material map / emissiveMap | True motion media | Autoplay, decode, VRAM | Viable as **sparse** face media type |
| **E. CanvasTexture / HTMLTexture** | 2D canvas or HTML element → texture | Generative, DOM-ish content | CPU paint; HTMLTexture browser API maturity | Good for animated glyphs, UI-on-face prototypes |
| **F. Render targets (RTT)** | Secondary scene → `WebGLRenderTarget` / `rtt` node → sample on face | Live 3D “portal” faces, shadertoy-like offscreen | Extra render cost per RT | High-end “studio face” |
| **G. Shadertoy-style fragment** | `ShaderMaterial` or TSL `colorNode` with time/noise | Fully generative, no assets | Classic path tied to WebGL; TSL needs WebGPURenderer | Per-face FX without bitmaps |
| **H. CSS3D hybrid** | `CSS3DRenderer` + `CSS3DObject` overlays | Real DOM (video tags, iframes, forms) | Not true mesh shading; depth/occlusion fights; dual renderers | Overlays / editor chrome, weak for shaded cube faces |
| **I. HTMLMesh (addon)** | Rasterize DOM into mesh interactive texture | Clickable HTML in-world | Heavy, niche | Experiment only |
| **J. Compressed textures** | KTX2 / Basis Universal | VRAM ~10× win vs PNG | Build pipeline | Images on faces at scale |

References for RTT / face mapping:

- [Maxime Heckel: WebGL render targets](https://blog.maximeheckel.com/posts/beautiful-and-mind-bending-effects-with-webgl-render-targets/) (portaled scenes as textures; notes UV mapping puts the RT on **each face** of a box when using box UVs).
- three.js examples family: materials video, render-to-texture demos; WebGPU video material example above.

### 3.2 “Shadertoy per face” design choices

1. **Shared program, per-instance uniforms/attributes** (time offset, seed, palette) — matches cubicell’s instancing DNA.
2. **Classic:** extend current `onBeforeCompile` block (like stencils) with time + noise branches keyed by instance attribute.
3. **TSL:** `MeshBasicNodeMaterial` + `colorNode` driven by `time`, `instanceIndex`, textures — only after WebGPURenderer migration.
4. **Offscreen shadertoy → atlas RT:** one fullscreen pass writes N tiles into an atlas each frame; faces sample tiles — amortizes unique FX into one RT update.

### 3.3 CSS3D hybrids (honest assessment)

`CSS3DRenderer` places transformed DOM in 3D space. Good for:

- Floating panels, captions, true `<video>` controls, accessibility.

Bad for:

- Occlusion by opaque cube faces (DOM sits in a second layer).
- Lighting, fog, postprocessing consistent with the WebGL scene.
- Hundreds of faces.

For cubicell’s **shaded grid**, prefer **GPU textures** (atlas / video / RT). Use CSS3D only for **editor UI in world space**, not as the primary face media substrate.

---

## 4. Capability matrix: what r185 cubicell can / cannot do *today*

Assume current stack: **R3F default `WebGLRenderer`**, instanced faces, `MeshBasicMaterial` + `onBeforeCompile` stencils. No WebGPURenderer switch yet.

| Media type | Can ship on current stack? | How | Blockers / notes |
| --- | --- | --- | --- |
| Solid colour roles | **Yes** | Existing | — |
| SVG / stencil figures | **Yes** | Atlas + `onBeforeCompile` | Fixed 16-slot atlas capacity |
| Static images (PNG/JPEG/WebP) | **Yes** | `Texture` / KTX2 as map; or bake into atlas | Unique maps break pure single-material instancing unless atlased |
| Compressed image atlases | **Yes** | KTX2Loader / basis | Pipeline work, not three version |
| Canvas-generated animation | **Yes** | `CanvasTexture` + `needsUpdate` | CPU cost; throttle updates |
| HTML-as-texture | **Partial** | `HTMLTexture` (r184+) | Depends on browser HTML-in-Canvas support |
| Video on face | **Yes (sparse)** | `VideoTexture` or drei `useVideoTexture` | Autoplay policies; don’t N-way decode |
| WebCodecs video | **Yes** | `VideoFrameTexture.setFrame` | Custom decode pipeline |
| Live portal / mini-scene on face | **Yes** | `WebGLRenderTarget` + sample | Extra passes; budget carefully |
| GLSL custom face FX | **Yes** | Extend `onBeforeCompile` or `ShaderMaterial` | Stays WebGL-only path |
| TSL / NodeMaterial face FX | **No (without renderer change)** | Needs `WebGPURenderer` (+ node materials) | Current `onBeforeCompile` path incompatible with WebGPURenderer |
| Compute-driven generative faces | **No on classic WebGL path** | TSL compute on WebGPU backend | Requires WebGPU device + renderer migration |
| CSS3D DOM faces | **Technically yes** | Dual renderer | Wrong tool for core face media |
| HDR video faces | **Not practical** | — | Browser/ecosystem limited; not a three gap |

---

## 5. Version constraints and what “upgrading” would buy

### 5.1 Version position

| Package | Installed | Latest (research) | Gap |
| --- | --- | --- | --- |
| three | **0.185.1 (r185)** | r185 | **None** |
| @react-three/fiber | 9.6.1 | (peer three ≥0.156) | Fine |
| @react-three/drei | 10.7.7 | (peer three ≥0.159) | Fine |

**Upgrading three further buys nothing today** (already on tip). Future r186+ would bring incremental TSL/WebGPU/HTMLTexture polish, not a new media class.

### 5.2 What a *renderer* upgrade (WebGL → WebGPURenderer) would buy

Not a package bump alone: an architectural switch.

**Gains:**

- First-class **TSL** custom materials (write once, WGSL/GLSL backends).
- **Compute shaders** for generative / particle / simulation-backed faces.
- Modern **RenderPipeline** / node postprocessing (r183+) instead of EffectComposer GLSL stack.
- Future three.js gravity: new effects land on nodes first.
- r185 improvements: better InstancedMesh + render bundles, texture array rendering, WebXR+WebGPU, etc.

**Costs (cubicell-specific):**

- **Rewrite face stencil path:** `onBeforeCompile` GLSL injection must become TSL/`colorNode` (or equivalent).
- Audit all materials, shadows, tone mapping, color space.
- R3F `gl` factory / async `await renderer.init()`.
- Accept residual WebGPU bugs/perf variance on some GPUs; keep `forceWebGL` escape hatch.
- Ecosystem (drei helpers, third-party) uneven on WebGPU.

### 5.3 What *not* to wait for

- Video, images, canvas, RT portals, atlas: **already fully available on r185 WebGL**.
- “Need latest three for media faces” is false for cubicell’s version.

---

## 6. Recommended media taxonomy for face design (product-shaped)

Ordered by least resistance given cubicell’s instanced architecture:

1. **Colour + stencil atlas** (shipped) — symbolic figures, zero decode.
2. **Extended atlas** — images, more glyphs, optional animated sprite sheets (`spritesheetUV` exists in TSL; classic path can do UV animation in GLSL).
3. **CanvasTexture / HTMLTexture** — rare dynamic labels, generative 2D.
4. **VideoTexture (shared or sparse)** — media faces with poster + play-on-select.
5. **RenderTarget portals** — “live studio” faces; budgeted count.
6. **GLSL generative** (extend `onBeforeCompile`) — shadertoy aesthetic without WebGPU.
7. **TSL / WebGPU** — only when compute, unified post, or long-term material strategy justifies the migration tax.

---

## 7. Sources (primary)

### three.js official

- [WebGPURenderer docs](https://threejs.org/docs/pages/WebGPURenderer.html)
- [TSL docs](https://threejs.org/docs/TSL.html)
- [Releases: r185 (latest), r184, r183](https://github.com/mrdoob/three.js/releases)
- [webgpu_materials_video example](https://threejs.org/examples/webgpu_materials_video.html)
- Installed sources: `three@0.185.1` `VideoTexture.js`, `VideoFrameTexture.js`, `HTMLTexture.js`

### Maintainer / forum

- [r164: nodes no longer with classic WebGL](https://discourse.threejs.org/t/r164-nodes-no-longer-working-with-webgl-webgl2/64909) (Mugen87: TSL + WebGPURenderer only; ShaderMaterial/onBeforeCompile incompatible)
- [WebGPU maturity vs R3F, Feb 2026](https://discourse.threejs.org/t/webgpu-renderer-vanilla-three-js-vs-r3f-maturity-and-pitfalls/89661)
- [WebGPU perf drop r182, Jan 2026](https://discourse.threejs.org/t/webgpu-significant-performance-drop-and-shadow-quality-regression-in-r182-vs-webgl-r170/89322)
- [Issue #30185 WebGLRenderer Node Materials](https://github.com/mrdoob/three.js/issues/30185)
- [VideoTexture color space](https://discourse.threejs.org/t/videotexture-is-bright-and-washed-out/60287)

### Guides / ecosystem

- [Field guide to TSL and WebGPU (Maxime Heckel, 2025-10)](https://blog.maximeheckel.com/posts/field-guide-to-tsl-and-webgpu/)
- [TSL introduction article](https://threejsroadmap.com/blog/tsl-a-better-way-to-write-shaders-in-threejs)
- [Render targets as textures](https://blog.maximeheckel.com/posts/beautiful-and-mind-bending-effects-with-webgl-render-targets/)
- [drei useVideoTexture](https://drei.docs.pmnd.rs/loaders/video-texture-use-video-texture)
- [Threlte WebGPU notes](https://threlte.xyz/docs/learn/advanced/webgpu/)
- [Three.js 2026 change summary (utsobo)](https://www.utsubo.com/blog/threejs-2026-what-changed)
- [iOS VideoTexture constraints](https://blog.markkulab.net/post/resolve-three-js-video-texture-is-not-working-in-ios)

### Local codebase anchors

- `package.json` → `three@^0.185.1`
- `src/scene/faceStencilShader.ts` — `onBeforeCompile` stencil program
- `src/scene/stencilAtlas.ts` — 2048 atlas, 16×512 slots, `DataTexture` RedFormat

---

## 8. One-line verdict

**r185 already unlocks images, video, canvas, RTT portals, and GLSL face FX on WebGL; TSL/compute need a WebGPURenderer migration that would rewrite the existing onBeforeCompile stencil path, not a package upgrade.**
