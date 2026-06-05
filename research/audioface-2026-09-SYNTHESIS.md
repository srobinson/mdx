---
title: Audioface direction, September 2026 synthesis
type: research
tags: [audioface, web-audio, game-audio, synthesis, roadmap, architecture, ui-direction]
summary: Integrating document over one code review and three independent warroom research reports (Opus on the Web Audio ceiling, Codex on game audio middleware, Grok on interface direction). Where they converge, where they disagree, and a recommended sequence.
status: snapshot (decays in about 6 months)
confidence: high
created: 2026-09-03
updated: 2026-09-03
related:
  - audioface-2026-09-engine-review.md
  - audioface-web-audio-ceiling.md
  - audioface-game-audio-middleware-gaps.md
  - audioface-ui-direction.md
---

# Audioface direction, September 2026 synthesis

Four independent reads, produced without coordination:

| Report | Author | Angle | Words |
|---|---|---|---|
| `audioface-2026-09-engine-review.md` | Fable (orchestrator), from source only | What the engine is, what it does well, 15 gaps, the Web Audio ceiling | 2900 |
| `audioface-web-audio-ceiling.md` | Opus 5 | Node inventory, worklet edges, state of the art, 15 missing capabilities, three architectures, hard limits | 2976 |
| `audioface-game-audio-middleware-gaps.md` | GPT 5.6 Sol | Wwise, FMOD, MetaSounds, Godot, Unity primitives mapped to audioface, adaptive music, procedural audio, seven layer architecture, plugin contract, threejs story | 3163 |
| `audioface-ui-direction.md` | Grok 4.6 | Design thesis, ten interface concepts, information architecture, UI stack, risks | 3485 |

## 1. The one finding everyone reached

The engine's foundation is right and the engine is not yet a game audio engine.

Every report, from four different starting points, concluded that the deterministic sample domain kernel (frames, linear gains, seeded random access noise, voice pool with class floors, certification gates) is the asset to protect. Opus put it most sharply: every hard limit of the platform is a reason the "own DSP, own scheduling, browser as sink" design is the correct foundation, and the gap is that the foundation only renders where a game engine must also play, react and sustain.

The identity gap is the first decision. The product is described as "on top of the Web Audio API" and the code uses one Web Audio node as a speaker. Reconciling those is architecture, not a feature.

## 2. Convergence

Ranked by how many of the four reports arrived at the same conclusion independently.

**Four of four**

- Keep the TypeScript kernel. Do not rewrite around native nodes and do not fork a second realtime DSP implementation (Opus calls the two implementation path "the worst to live with").
- Host the kernel in an `AudioWorkletProcessor`. Same code offline, in tests and realtime. Opus and the engine review both propose a differential null test: render a patch offline, render it through the worklet under an `OfflineAudioContext`, require silence when subtracted. Grok arrived at the same requirement from the UI side: the preview picture must come from the real renderer or the UI lies.
- Modulation must become continuous. Modulators (LFO, envelope, follower, random, step, macro, game parameter) become plugins with a per block pass. The existing connection list is the matrix; the sources are missing.
- A uniform DSP plugin contract before the palette grows. Codex's list is the most complete: id and version, typed audio, control and event ports, parameter descriptors, seed namespace, declared response to reset, seek, suspend, virtualise and restore, latency and tail in frames, serialisable state with schema version, resource declarations, one block render definition with host adapters, a UI descriptor, diagnostics. The existing `ParameterDefinition` registry row already covers the descriptor half.
- Sample and wavetable playback are mandatory before a real project can use the tool.
- Music needs its own runtime: a clock on the audio thread with tempo map, transport, quantised transition points, stems, stingers, and beat callbacks that may be late to the game without moving the sound (Codex `MusicClock` and `MusicSession`, Opus item 4, engine review 3.7).

**Three of four**

- Buses, sends and returns as the place shared effects live. Convolution reverb on a send bus is the single largest perceptual upgrade (Opus 5, Codex reverb zones row, engine review 3.5).
- Spatialisation driven by the threejs camera: listener from camera, emitters on `Object3D`, occlusion by raycast smoothed then automated onto gain and filter, reverb zones as crossfaded sends. Codex names Resonance Audio as an existing Web Audio ambisonic scene that accepts a threejs listener matrix.
- Sidechain dynamics must be owned DSP: `DynamicsCompressorNode` has no key input (Opus hard limits, Codex, engine review).
- Band limit the oscillators. The naive saw and square alias; PolyBLEP or wavetable oscillators are the fix (engine review 3.4, Opus item 8 by implication, Codex source families).
- The gate report is first class UI, not a footer (Grok's Gate dock, engine review's certification as differentiator, Codex's profiler row).

**Two of four, and worth keeping**

- Registry rows `OUT-01`, `OUT-02`, `OUT-12.*`, `AMP-16.ramp-ms` are declared and consumed by nothing; honour them in the worklet host or delete them (engine review 3.10, Opus item 15 on observability and device selection).
- Rename the data only "plugin" (event set plus scenarios) before the DSP plugin vocabulary arrives (engine review 3.11; Grok's information architecture uses "Plugin" for the DSP device and "Sound" for the designed object, which collides directly).
- Playback containers (round robin, weighted random, blend by game parameter, switch) are middleware behaviour designers expect and need no new DSP (Opus item 11, Codex containers row).
- Virtual voices: separate logical instances from rendered voices, advance a virtual cursor without DSP, restore a real voice at position (Codex). The current pool never refuses and never virtualises.

## 3. Disagreements and how to resolve them

**How much of the signal path should be native Web Audio nodes?**
Codex would compile standard filters, delays, waveshaping, compression and convolution to native nodes and keep the pure renderer as the reference backend. Opus and the engine review keep everything inside a layer in the kernel and use native nodes only after the master sum.
Resolution: native node output is not identical across browsers and cannot be inspected sample by sample, so anything a certification gate reads must stay in the kernel. That is the whole voice tier. Native nodes earn their place on the mix tier, after the kernel, where determinism is not promised: bus gains, `ConvolverNode` reverb, `PannerNode` HRTF as an option, `AnalyserNode` for the UI, output gain and mute. The two positions are compatible once the seam is named: the kernel ends where the master sum ends, which is exactly where the code already changes from "exact" to "placement".

**AudioParam automation or a ring buffer for control?**
Codex uses `AudioParam` automation for native nodes; Opus routes all control through one `SharedArrayBuffer` ring of timestamped events and avoids dozens of AudioParams.
Resolution: both, by tier. Kernel control goes through one message channel with frame stamps (ring buffer when cross origin isolation is available, `MessagePort` otherwise). Native mix tier nodes take `AudioParam` automation, which is what they are good at.

**Is AudioWorklet a baseline requirement?**
Grok's risk list says requiring AudioWorklet or WebGPU strands the tool and names Web Audio, Canvas and WebGL 2 as baseline. Opus and Codex make the worklet the core.
Resolution: AudioWorklet has shipped in every major engine since Safari 14.1 (2021) and is baseline. What must not be required is `SharedArrayBuffer` (needs COOP and COEP headers the host page controls) and WebGPU. Fall back to `MessagePort` and CPU FFT respectively.

**Rust or WASM now, or later?**
Opus considers a full Rust rewrite (the Glicol architecture) and rejects it in favour of a single TypeScript block processor with WASM dropped in per hot kernel after profiling. Codex assumes WASM for heavier DSP. Nobody argued for a rewrite now.
Resolution: TypeScript block processors first, allocation free, then WASM for named hot spots. The current per sample closure chain is the thing to replace either way (engine review 3.13).

## 4. What the interface research adds

Grok's thesis: a professional sound tool is a machine you look at while you listen, and the picture of the signal is the primary control. Ten concepts, of which four are load bearing for the first release:

- **Chassis.** A layer is a stack of plugin slots (source on top, inserts below, empty slot invites a plugin, drag to reorder, LED bypass). The forty parameters disappear into the plugins that own them. Modelled on Phase Plant lanes and the Reason rack.
- **Drop rings.** Drag a modulator onto a control, a ring appears, pull for depth, every connection also lands in a matrix. Cables are reserved for audio rate routing and the specialist graph. Modelled on Serum 2, Vital, Massive X, Pigments.
- **Gate dock.** Each certification gate as a row with verdict, measured value, threshold and a deep link into the chassis or voice inspector. Modelled on Wwise's loudness meter and voice inspector.
- **Event in the room.** A scene pane with a listener and draggable emitters in threejs, attenuation curves, RTPC bindings, and a voice inspector that explains why a voice is quiet. Modelled on FMOD's 3D preview and sandbox.

Information architecture nouns to hold stable across UI, engine and threejs bindings: Scene, Sound, Layer, Plugin, Rack, Bus, Modulation, Macro, RTPC, Attenuation, Gate report, Voice. Grok's warning: do not collapse Sound and Scene, do not collapse Plugin and Parameter, do not bury the voice pool in a details block.

UI stack: DOM and ARIA for every control (a canvas pixel is not a button), Canvas 2D in an `OffscreenCanvas` worker for meters and small scopes, WebGL 2 for spectrograms, wavetables and ring overlays, threejs only in the scene pane, WebGPU compute as a capability gated FFT path, Web MIDI for learn. The named failure mode is "pretty ranges": restyling the current bench with dark knobs and calling it done.

## 5. Recommended sequence

Each phase ends in something a designer can hear or a test can hold. The order follows dependencies, not importance.

0. **Owner decisions** (see section 6). Cross browser bit identity or tolerance. Certification scope for music and mix tier. First release palette size.
1. **Kernel into the worklet.** Refactor stages to allocation free block processors. One `AudioWorkletProcessor` hosts `MasterBus`. Frame stamped control channel. Differential null test between offline and worklet renders. Honour or delete the `OUT-*` and `AMP-16` rows here. This unlocks held beds with a live listener in the browser, which the code was designed for and cannot do today.
2. **DSP plugin contract.** Define it against Codex's field list and the existing registry rows. Refit the three sources and four processors to it. Rename the data plugin. After this, adding a processor touches one module.
3. **Sound quality floor.** Band limited oscillators. Sample source with loop points. Continuous modulators (LFO, macro, game parameter) and the per block modulation pass. This is where Chassis and Drop rings become buildable, because there is finally something to drop.
4. **Mix tier.** Buses, sends and returns as native gain graph after the kernel. Convolver reverb on a send. Sidechain ducker in the kernel with a key input. Optional `PannerNode` HRTF. `AnalyserNode` taps for the UI. threejs listener and emitter binding, raycast occlusion, reverb zones.
5. **Music runtime.** Clock on the audio thread, tempo map, transport, quantised transitions, stems, stingers, beat callbacks. Lift the 2.5 s cap as part of this, since loops and beds are what the cap excluded.
6. **Interface.** Chassis and Drop rings first (the engine is already a layer stack with a matrix), Gate dock and Event in the room second (the engine already has gates and a listener), Kit well (presets, A/B, undo) third.

Phases 1 and 2 are the enabling work and should not be skipped to reach 3 or 6 faster; both Opus and Grok independently warned that shipping a second DSP path or a restyled bench is the way this product fails.

## 6. Decisions only the owner can make

- Is cross browser bit identity a goal? It decides whether the kernel may use `Math.sin` and `Math.expm1` or needs its own tables.
- Does certification extend to music (tempo, loops, transitions) and to the native mix tier, or is the mix tier explicitly outside the gates?
- How large is the first release plugin palette? It decides whether the contract can stay closed for one more milestone.
- Which vocabulary wins for "plugin": the DSP device (product) or the event set (code)? Both cannot keep the name.
- Baseline browser matrix. Safari on iOS lacks Web MIDI, mutes with the hardware switch, and lags on `sinkId` and render size. Is iOS Safari a first class target?

## 7. Sources worth reading first

From the three reports, the references that most changed the picture:

- openDAW (andremichelle), pure TypeScript DAW with a box graph data layer, one worklet running BlockRenderer then ClipSequencing then AudioUnits then DeviceChains per quantum, heavy work in Web Workers. The closest existing architecture to where audioface should go. Cited in `audioface-web-audio-ceiling.md`.
- Web Audio API 1.1 First Public Working Draft (W3C, November 2024): `sinkId`, `renderCapacity`, `renderSizeHint`, `outputLatency`. Cited in the ceiling report and this synthesis.
- Emscripten Wasm Audio Worklets: zero JS garbage guarantee on the audio thread, three sync paths (AudioParam, atomics, function dispatch).
- Web Audio Modules 2.0: the only browser plugin interop standard, worth studying for the contract even if not adopted.
- Wwise HDR user guide and Steam Audio C API guide, cited in the middleware report, for the mix and propagation models.
- Resonance Audio Web getting started, for a working ambisonic scene that already accepts a threejs listener matrix.
- Phase Plant documentation and the Serum 2 modulation guide, for Chassis and Drop rings.
- Cables.gl accessibility note and the rebuild of its editor from SVG to WebGL, for why controls are DOM and pictures are GPU.

## 8. Owner decisions recorded 2026-09-03

Stuart answered section 6 the same day:

1. Cross browser bit identity is a secondary goal. Seams and architecture must accommodate it later (an engine owned sine and exp table can drop in behind the source and envelope stages); no cycles on it before a shippable product.
2. Certification scope for music and the mix tier: parked.
3. First release palette size: options requested, see the orchestrator's reply and the follow up entry in the context store.
4. The data only event set drops the word "plugin". "Plugin" is reserved for the product's DSP plugin vocabulary.
5. No iOS Safari support. Desktop browsers are the target matrix, which frees `SharedArrayBuffer`, Web MIDI and `sinkId` from fallback obligations where the host page can set the isolation headers.
