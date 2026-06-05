---
title: Dotted Point Cloud Face Architecture Audit for littleorgans
type: research
tags: [littleorgans, avatar, point-cloud, lip-sync, three-js, webgl, headtts, headaudio, piper, visemes]
summary: Conditional audit of the littleorgans dotted point cloud face recommendation found point correspondence and motion layer framing defects.
status: active
source: codebase-analyst
confidence: high
created: 2026-06-07
updated: 2026-06-07
---

## Executive Summary

The reviewed cm decision recommends a dotted point cloud talking face for littleorgans using Three.js points, ARKit 52 plus Oculus 15 morph targets, HeadTTS, TalkingHead, and HeadAudio. The broad direction is viable, but sign off is conditional because the proposed point bake would scramble point correspondence and the motion layer assumes HeadTTS owns synthesis despite the existing native MLX/CUDA voice stack.

## Project Metadata

- Artifact reviewed: cm decision `019e9e40-c55f-7c03-abab-d03197e031fa`, scope `global/project:helioy`.
- Related voice architecture: cm decision `019e9a41-e744-7fb2-bacd-d9069a68607e`.
- Target product: littleorgans Electron plus web application.
- Render stack under review: Three.js, React Three Fiber, WebGL, `THREE.Points`, `BufferGeometry.morphAttributes.position`.
- Motion interface under review: ARKit 52 plus Oculus 15 blendshape and viseme weights.
- Voice stack context: native local first cascaded MLX/CUDA voice architecture, with Kokoro, Kyutai, Piper, or similar TTS candidates.

## Architecture

The intended architecture has three layers:

1. Identity: an abstract CC0 head authored with ARKit 52 and Oculus 15 morph targets.
2. Motion: speech timing becomes viseme or blendshape weights.
3. Render: a point cloud renders the deformed face, ideally using GPU morph targets rather than CPU point updates.

The clean contract is the morph weight vector. Any runtime driver that emits ARKit 52 and Oculus 15 weights can drive the point rig. Identity and rig composition remain build time decisions because changing the head mesh, target names, or target count requires re baking the point cloud assets.

## Key Patterns

### Morph the face, render as dots

The durable idea is to animate a face rig and render the result as points. This keeps the problem inside known morph target and shader paths instead of inventing an audio to point cloud animation system.

### Persist surface correspondence, not random seeds

Point cloud morph targets require each point index to represent the same surface point across all targets. Random sampling must happen once on the neutral mesh, then each target is evaluated at the same stored surface coordinate.

### Use the selected TTS as the timing authority

The primary lip sync path should use timing information from the actual native TTS engine selected by littleorgans. HeadTTS can be used only when it owns synthesis. HeadAudio is a fallback for opaque audio without transcript, phoneme, viseme, or blendshape timing.

## Detailed Findings

### 1. Three.js Points morphs are feasible in principle

Three.js `Points` exposes `morphTargetDictionary`, `morphTargetInfluences`, and calls `updateMorphTargets()` when constructed. The current WebGL renderer enables morph targets based on `geometry.morphAttributes.position`, uploads morph targets into a `DataArrayTexture`, and uses `MORPHTARGETS_COUNT` in shader chunks. This supports the basic feasibility of a morphable point cloud.

The remaining open question is performance, not API existence. The recommendation should keep `200k points at 60fps in Electron` as an empirical benchmark.

Verified source pointers:

- `three.js/src/objects/Points.js`: `morphTargetInfluences` and `updateMorphTargets()` are present in `Points`.
- `three.js/src/renderers/webgl/WebGLMorphtargets.js`: morph target data is encoded into `DataArrayTexture` layers and driven by `morphTargetInfluences`.
- `three.js/src/renderers/shaders/ShaderChunk/morphtarget_vertex.glsl.js`: shader loops over `MORPHTARGETS_COUNT`.

### 2. Shared seed MeshSurfaceSampler baking is wrong

The reviewed cm entry says to bake one morph target per blendshape by sampling the head per blendshape with a shared seed. This does not guarantee point correspondence.

`MeshSurfaceSampler` selects faces from a cumulative area weighted distribution. A shared random number stream only reuses random values. If a blendshape changes triangle areas, the cumulative distribution changes. The same random value can binary search to a different face, so point index `i` can represent different surface locations across targets.

Required correction:

1. Sample once on the neutral mesh.
2. Persist per point `(faceIndex, barycentric u, v, w)`.
3. For each ARKit or Oculus target, evaluate the same face and barycentric coordinates against that target's deformed vertices.
4. Store those evaluated positions as the morph target for the point geometry.

Primary sources:

- Three.js `MeshSurfaceSampler` docs: if no weight attribute is selected, sampling is distributed by area.
- Three.js `MeshSurfaceSampler` source: `build()` computes face weights from triangle area and stores a cumulative distribution.

### 3. HeadTTS should not be the core motion primary for littleorgans

The reviewed cm entry frames HeadTTS as the primary lip sync path because it emits audio, phonemes, and Oculus visemes inline. That only works if HeadTTS owns synthesis.

The related voice architecture decision for littleorgans chooses a native local first cascaded voice stack targeting Apple Silicon MLX and NVIDIA CUDA. That stack has its own TTS candidates, including Kokoro, Kyutai, Piper, and Chatterbox style options. If littleorgans keeps that architecture, HeadTTS cannot provide authoritative timings for audio generated by a different TTS.

Required correction:

- Primary motion contract: selected native TTS emits timed phonemes, timed visemes, or blendshape timing.
- Convert native phoneme alignment to Oculus 15 visemes.
- Feed those weights into TalkingHead style external timed viseme or blendshape input, then into the point morph rig.
- HeadTTS becomes optional only if littleorgans adopts it as the actual in browser TTS.
- HeadAudio becomes fallback only for opaque audio, such as cloud speech without timing metadata.

Primary sources:

- HeadTTS documents inline phonemes, visemes, start times, and durations for its own synthesis.
- TalkingHead accepts external visemes, timings, durations, and blendshape animations for `speakAudio()` and streaming input.
- HeadAudio documents audio driven real time viseme detection, but also states lower accuracy than text driven lip sync and a 50 to 100 ms compensation path.

### 4. Piper refutation should be corrected

A surviving architecture should not lean on a blanket claim that Piper cannot emit phonemes or timings. Piper uses phonemization internally, and piper1-gpl documents experimental audio alignments through patched models.

Relevant detail:

- piper1-gpl alignment docs expose `phonemes`, `phoneme_ids`, and per phoneme ID sample counts.
- Older Piper maintainer discussion notes that `w_ceil * 256` gives audio samples per phoneme, but older native export required changes.

The safe framing is that Piper timings are possible through patched or modified models, not that Piper is currently a complete turnkey viseme source for every deployment.

### 5. Swappability must be split by layer

The morphable point geometry preserves runtime driver swappability if the driver emits the same ARKit 52 plus Oculus 15 weight contract. It does not make identity or rig composition hot swappable.

The corrected claim:

- Runtime swappable: motion source. Any driver emitting ARKit 52 or Oculus 15 weights can drive the same baked point rig.
- Build time only: identity mesh, target names, target count, and rig composition. Changing these requires re bake and asset re ship.

Raw storage also matters. A naive `200k points * 67 targets * 3 floats * 4 bytes` position target payload is about 160 MB before compression or texture packing. The architecture should prefer reduced target count, compressed assets, or morph texture packing where practical.

## Dependencies

- Three.js: point rendering, buffer geometry, morph target shader and WebGL texture path.
- React Three Fiber: React integration around Three.js, not load bearing for the morph feasibility claim.
- HeadTTS: optional in browser Kokoro TTS with phoneme and Oculus viseme timings.
- TalkingHead: useful reference for external timed viseme and blendshape contracts.
- HeadAudio: audio driven fallback for opaque audio sources.
- Piper or piper1-gpl: possible native TTS alignment source through phoneme IDs and duration outputs.
- Kyutai TTS: native streaming TTS candidate with timing claims that should be validated against the selected runtime.

## Relevance to Helioy

This audit clarifies the architectural seam littleorgans should standardize: native voice timing to ARKit 52 and Oculus 15 motion weights, then render agnostic point morphing. The result keeps the face interface compatible with the existing local first voice architecture instead of replacing it with a browser only TTS path.

## Open Questions

1. Benchmark 50k, 100k, and 200k points at target Electron settings on actual target hardware.
2. Pick the first native TTS timing provider and prove its phoneme or viseme alignment quality with real generated audio.
3. Decide the v1 morph target subset. Full ARKit 52 plus Oculus 15 may be unnecessary for the first talking face.
4. Measure asset size and load time for attribute based morphs versus morph textures or compressed assets.

## Final Sign Off

After the orchestrator applied the three consensus edits to cm `019e9e40-c55f-7c03-abab-d03197e031fa`, I re-read the revised entry live and verified the render correspondence, native TTS motion primary, HeadTTS and HeadAudio demotions, Piper correction, and swappability split. I sent the clean sign off line on the bus: `I sign off on the littleorgans face architecture as currently filed`.
