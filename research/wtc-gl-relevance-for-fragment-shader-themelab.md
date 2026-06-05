---
title: wtc-gl Relevance Assessment for little-background-lab (fragment-shader theme lab)
type: research
tags: [webgl, glsl, fragment-shader, fbo, ping-pong, gpgpu, little-background-lab, wtc-gl]
summary: wtc-gl is a small mini-Three/OGL WebGL library; adopting it is overkill for our single-quad fragment scenes, but its Framebuffer ping-pong primitive and ParticleSimulation GPGPU recipe are the borrowable parts that unlock feedback/particle scenes we can't do single-pass.
status: active
source: github-researcher
confidence: high
created: 2026-06-15
updated: 2026-06-15
---

## Executive Summary

`wtc-gl` (wethegit/wtc-gl, MIT, v1.2.3) is a small TypeScript WebGL abstraction "adapted from and inspired by Three.js and OGL" — a mini scene-graph library: Renderer, Program, Mesh, Geometry, Camera, Texture, RenderTarget, plus higher-level "recipes." For our use case (raw full-screen fragment shaders, single quad, uniform-driven, no geometry/meshes/3D, seamless looping) the library as a whole is overkill: most of its mass is geometry, camera, and scene-graph machinery we deliberately avoid. The valuable parts are two narrow primitives we can study and reimplement without taking the dependency: the `Framebuffer` ping-pong FBO and the `ParticleSimulation` GPGPU recipe. These unlock feedback-trail and particle scene kinds that a single-pass fragment shader cannot express.

## Repo facts

- License: MIT (Copyright 2019 We The Collective). No adoption blocker. Lifting GLSL/patterns is fine with attribution.
- Maintenance: active. Last commit 2026-05-26 (#145), regular merges through May 2026.
- Size/deps: single package, ~6.5k LOC of TS in `src/lib`. Sole runtime dependency is `wtc-math` (also MIT, same author) for `Vec2/Vec3/Mat4` etc. Pulling `FragmentShader` recipe drags in Renderer+Program+Mesh+Triangle+Uniform+wtc-math.
- TS: fully typed, ships `.d.ts`, dual ESM/CJS exports, `module` field present. Tree-shakeable in principle (named exports per module) but `src/lib/index.ts` re-exports everything including all of `wtc-math`, so naive `import { FragmentShader }` may pull a lot unless the bundler shakes well.
- Build/tooling: Vite 8 + vite-plugin-glsl + vite-plugin-dts. Same Vite/TS stack as ours.

## Architecture

It is a real (if minimal) WebGL abstraction, not a thin helper:

- `core/Renderer.ts` (732 LOC): context creation, render loop, state caching, render-to-target, viewport, sort/frustum cull.
- `core/Program.ts` (382): shader compile/link, uniform location caching, blend/depth state.
- `core/Uniform.ts` (222): one `Uniform` per value; `bind()` auto-dispatches the correct `gl.uniformNfv/iv` by `kind` (`float`, `float_vec2..4`, `int_*`, `texture`, `texture_array`). Clean type-tagged upload.
- `core/RenderTarget.ts` (211): FBO + attached texture wrapper.
- `core/TransformFeedback.ts` (111): WebGL2 transform-feedback buffers (GPGPU on buffers, not textures).
- `geometry/*`, `core/Camera.ts`, `core/DollyCamera.ts`: the 3D/mesh machinery we do not want.
- `recipes/`: opinionated entry points — `FragmentShader`, `ParticleSimulation`, `ScrollRenderer`.
- `ext/Framebuffer.ts` (232): double-buffered RenderTarget pair with `swap()`, `read`, `write`. The ping-pong primitive.

## Key findings vs our scene contract

### 1. FragmentShader recipe = our exact use case, but thinner contract

`src/lib/recipes/FragmentShader/index.ts` is what we already hand-roll: a full-screen `Triangle` (single full-viewport tri, not a quad — fewer fragments on the diagonal), a `Program`, auto-managed `u_time` and `u_resolution` (`= dimensions * dpr`), `window.resize` -> `u_resolution` + renderer dims, a play/pause RAF loop, and `onBeforeRender/onAfterRender/onInit` hooks. It also exposes a `post` setter that swaps the direct render for an FBO render (one-line opt-in to post-processing).

Gap vs us: their `u_time` is `+= diff * 0.00005` free-running wall-clock seconds — NO loop wrapping. Our hard seamless-loop contract (uTime wrapped mod loopSeconds, `hz(cycles)` integer-cycle helper, params modulate amplitude only) does not exist here and is the thing that makes our scenes special. Adopting their recipe would mean re-imposing our loop discipline on top, so adoption buys us little: we'd inherit their boilerplate-removal but lose nothing by keeping our own host, which is already small and already enforces the loop contract.

Verdict on adoption: skip. We'd add a dependency tree (Renderer/Program/Mesh/wtc-math) to replace a host loop we already own and that already encodes our most important invariant.

### 2. Framebuffer ping-pong — the borrow that matters most

`src/lib/ext/Framebuffer.ts`. Holds two `RenderTarget`s (`#readFB`, `#writeFB`), exposes `read`/`write`, and `swap()` flips them after each `render()`. Usage pattern (from `demos/framebuffer/index.js`, `demos/webcam-ca/index.js`): bind `fbo.read.texture` into a sampler uniform, render the sim shader into `fbo.write`, swap, then bind the fresh `read` into the display pass. Supports float / unsigned-byte / half-float textures and CLAMP/REPEAT/MIRROR wrap modes (relevant for tiling feedback).

Map to us: this is the missing primitive for any scene that needs to read its previous frame — feedback trails, accumulation/decay, reaction-diffusion, flow smearing. Our current `AmbientFragmentSceneDefinition` is strictly single-pass (one fragment string -> screen). To support these we'd add an optional second shader + a tiny ping-pong host. Reimplement ~40 LOC ourselves rather than depend; the design (two targets + swap, prev frame as a uniform sampler) is the lesson. Loop-safety caveat: feedback state is path-dependent and does NOT auto-close at the wrap. A feedback scene must converge to a steady state (decay term) or be reset at loop boundary to honor our seamless-loop contract.

### 3. ParticleSimulation recipe — GPGPU particles, the most novel capability

`src/lib/recipes/ParticleSimulation/index.ts` + `geometry/PointCloud.ts`. Encodes N particles as texels in a `textureSize^2` texture (e.g. 128^2 = 16k particles), each particle a `gl.POINTS` vertex carrying a `reference` attribute (its uv into the data texture). A sim fragment shader updates positions/velocities in the texture via FBO ping-pong; the render pass looks up each point's position from the texture. This is classic texture-as-data GPGPU.

Map to us: this is genuinely something raw single-pass fragment shaders cannot do — true particle systems with persistent per-particle state (swarms, drifting motes, flow-field particles over our liquid-mesh). It is also the heaviest pattern (geometry + two passes + POINTS), and the most at odds with our "single quad, no geometry" rule and our always-on lightweight perf target. Treat as a future "particle scene kind," not core. The reusable idea: pack state into a texture, address it with a per-point reference attribute, advance with a sim shader.

### 4. Uniform auto-dispatch (minor borrow)

`src/lib/core/Uniform.ts` infers the `gl.uniform*` call from a `kind` tag. Our param bridge already names a `uniform` per param; if our host has a switch on uniform type, theirs is a clean reference for covering vec2/vec3/int/texture uniformly. Low priority — we likely already cover the float/vecN cases we use.

### 5. GLSL utilities — copy-paste-ready, no central library

There is NO shared GLSL chunk library in `src` (no noise/sdf module). All GLSL lives inline per demo under `demos/`. Worth lifting into our `scenePrelude` (MIT, attribute):

- `noise(vec2)` value noise + `fbm(vec2)` 5-octave (amp 0.48, lacunarity 2.1) + `hash2(vec2)` — `demos/hero.frag`. Standard, clean fbm.
- `voronoi(vec2)` Worley (smoothed nearest grid point) — `demos/scroll-renderer-homepage/scenes/hero/hero.frag`.
- `hash(vec2)` scalar hash — `demos/scroll-blades/bg.frag`; `hash21a/hash21b` decorrelated hashes — `demos/webcam-ca/sim.frag`.
- `saturate(vec3,float)` desaturate-via-luminance-mix — `demos/webcam-ca/render.frag` (useful for our day/night palette work).
- `seg(vec2,vec2,vec2)` SDF to line segment — `demos/framebuffer/main.frag`.
- `sdRoundBox`, `sdBoxFrame`, raymarch loop constants — `demos/raymarching-webgl2/main.frag` (3D, lower relevance for ambient 2D backgrounds).

Loop-safety caveat for any lifted GLSL: anything driven by uTime must be rewritten to our `hz(cycles)` integer-cycle form before it enters a scene. The noise/sdf/color helpers themselves are time-agnostic and safe to lift as-is.

## New scene kinds this could unlock for us

- Feedback-trail / accumulation scenes (e.g. glowing paths that smear and decay) — needs Framebuffer ping-pong (finding 2).
- Reaction-diffusion / Game-of-Life style organic textures (`demos/webcam-ca`) — needs ping-pong.
- Flow-field particle drift over existing backgrounds (`ParticleSimulation`) — needs GPGPU texture + POINTS (finding 3).

All three require us to extend the scene contract beyond single-pass. The cheapest first step is a 2-pass "fragment + feedback" scene kind reusing the ping-pong design.

## Dependencies

- `wtc-math` (MIT) — vector/matrix math. Only runtime dep. We would not need it for borrowed GLSL or a hand-rolled FBO; we'd only inherit it if we adopted a recipe.

## Relevance to Helioy / little-background-lab

- Adopt the library: no. Overkill; replaces a host we own that encodes our seamless-loop invariant.
- Borrow patterns: yes — `Framebuffer` ping-pong design (highest value), `ParticleSimulation` texture-GPGPU concept (future), and inline GLSL noise/fbm/voronoi/saturate for `scenePrelude`.
- The strategic gap it exposes: our contract is single-pass only. The interesting growth direction is a multi-pass / feedback scene kind, and wtc-gl is a clean, MIT-licensed reference implementation of exactly that wiring.

## Sources consulted

- `package.json`, `README.md`, `LICENSE`, git log (last commit 2026-05-26).
- `src/lib/index.ts` (public API surface).
- `src/lib/recipes/FragmentShader/index.ts`, `src/lib/recipes/ParticleSimulation/index.ts`.
- `src/lib/ext/Framebuffer.ts`, `src/lib/core/Uniform.ts`, `src/lib/core/Renderer.ts` (partial).
- demos: `framebuffer/`, `webcam-ca/`, `raymarching-webgl2/`, `hero.frag`, `scroll-renderer-homepage/scenes/*`.

## Open questions

- Real bundle weight of importing just `FragmentShader` (tree-shake effectiveness vs the catch-all `index.ts` re-export of all of wtc-math) — not measured; would need a trial bundle.
- Whether their `Renderer` does render-on-demand or only RAF (we want a cheap always-on background; their recipes are RAF-driven).
- Exact GLSL source text of the noise/fbm functions (verify quality/precision before lifting) — inspected by name/structure only.
