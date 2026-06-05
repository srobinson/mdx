---
title: Phosphene T0 Dotted Face Spike
type: sessions
tags: [frontend, phosphene, react, three-js, webgl]
summary: Implemented and corrected the static dotted point cloud face spike for phosphene T0.
status: active
source: frontend-engineer
confidence: high
created: 2026-06-07
updated: 2026-06-07
---

## Summary

Implemented the T0 static phosphene face in the Vite+ React app. The scaffold UI was replaced with a full viewport black React Three Fiber canvas that renders `public/head.glb` as white GPU points with shader lighting, round dot masking, subtle twinkle, breathing displacement, and idle yaw motion.

A reviewer fix round corrected the dot scale, Suspense load behavior, StrictMode disposal risk, device pixel ratio handling, and light direction space.

## Architecture Decisions

- `src/App.tsx` owns the shell, canvas camera, Suspense boundary, and asset load error boundary.
- `src/DottedFace.tsx` owns point sampling, material creation, animation, fallback geometry, and shader uniforms.
- Sampling uses `MeshSurfaceSampler` once per loaded source and captures position, normal, and per point randomness into buffer attributes.
- Loaded meshes are sampled from the first `THREE.Mesh` in `head.glb`. Sampled positions are fitted to a stable view height so the camera does not depend on source asset units.
- The fallback path uses a procedural ellipsoid head proxy only when the GLB load fails or no mesh is present. The Suspense load fallback is `null` to avoid sampling a throwaway 80k point proxy.
- Dot size uses `DOT_SIZE = 0.06` with the original perspective attenuation constant and a `uPixelRatio` uniform sourced from `gl.getPixelRatio()`.
- `uLightDir` is transformed from the world direction into view space every frame before shading against view space normals.
- `<points dispose={null}>` avoids the reviewed StrictMode double disposal path for the generated point geometry and shader material.
- `tsconfig.app.json` enables TypeScript strict mode for app source.

## Performance Notes

- `vp check src/App.tsx src/DottedFace.tsx src/index.css tsconfig.app.json` passed with formatting, lint, and type checking clean.
- Full `vp check` is currently blocked by formatting in reviewer provided `review-phosphene-t0.md`, outside the implementation files.
- `vp build` passed. Production output reported `dist/assets/index-D3OIOC7p.js` at 316.80 kB gzip, above the 200 kB target due to the Three.js and R3F stack in one initial chunk.
- `vp test --passWithNoTests` passed earlier because the scaffold has no test files.
- Runtime smoke checks: Vite dev served the app at `http://127.0.0.1:5173/`; `public/head.glb` parsed with `GLTFLoader`; first mesh was `LeePerrySmith` with 9,279 vertices; `MeshSurfaceSampler` returned a finite position and unit normal.
- Visual verification used Playwright screenshot capture against `vp dev` at 1200 by 900. The screenshot at `/tmp/phosphene-t0.png` showed discrete dots and a lit readable face.
- Real proof artifact captured after `vp build` and `vp preview`: `shot-t0.png` at 1200 by 1600, 670,653 bytes, max luminance 255, 461,019 non-black pixels. Manual inspection confirmed discrete dots forming a lit face.
- Vite dev logged a Three.js deprecation warning for `THREE.Clock`; no code change was made because it comes from the active rendering stack rather than the phosphene component code.

## Deviations from Spec

- No phosphene specific design spec existed under `~/.mdx/design/`; implementation followed the bus architecture brief, reviewer notes, and cm research snapshot instead.
- The Suspense fallback is intentionally empty. The procedural proxy remains reserved for asset error cases.

## Open Items

- Reduce or split the initial Three.js bundle if the 200 kB gzip target becomes a hard T0 gate.
- Add tests once a project test harness and render strategy are established.
- Revisit R3F or Three.js clock usage if the upstream deprecation warning becomes actionable in app code.
