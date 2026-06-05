---
title: Audioface engine review, September 2026 (fresh read of the code, no project docs consulted)
type: research
tags: [audioface, web-audio, game-audio, dsp, architecture-review, procedural-audio]
summary: Independent review of the audioface-next engine as it stands at commit 3e6a19b. What it is, what it does well, where it falls short of "a professional layer and plugin tool that exposes every aspect of the Web Audio API", and how far the Web Audio API can be pushed.
status: active
confidence: high
created: 2026-09-03
updated: 2026-09-03
related:
  - audioface-web-audio-ceiling.md
  - audioface-game-audio-middleware-gaps.md
  - audioface-ui-direction.md
  - audioface-2026-09-SYNTHESIS.md
---

# Audioface engine review, September 2026

Read from source only. No markdown inside the repository was opened, by request, so this is what the code says about itself.

Baseline: `pnpm check` green at commit 3e6a19b. 241 tests, typecheck, lint, format and a structure verifier all pass. About 10.6k lines across 206 tracked files, no file over 450 lines.

## 1. What the engine actually is

Audioface today is a deterministic, offline, sample domain procedural sound effect renderer written in plain TypeScript, with a certification harness around it. It is not built on the Web Audio API. The only Web Audio call in the repository is in the web adapter's `Player`, which copies a finished stereo render into an `AudioBuffer` and plays it through an `AudioBufferSourceNode`. Every oscillator, noise generator, filter, envelope, echo, pan law, distance model and limiter is hand written and runs on the main thread when the page renders a sound.

The signal chain per voice:

```
event ─▶ patch (registry values + connections) ─▶ resolve (once, at trigger)
      ─▶ bind to Voice (frames, cycles per frame, linear gains)
      ─▶ per layer: source ─▶ biquad filters ─▶ amp envelope × gain ─▶ echoes
      ─▶ layers sum (mono) × patch gain
      ─▶ distance (one pole air filter + falloff) ─▶ constant power pan × width
      ─▶ master sum ─▶ limiter ─▶ stereo block
```

Vocabulary as the code defines it:

| Term | Meaning in the code |
|---|---|
| Plugin | A frozen data object: event names, voice classes, sustain flags, and certification scenarios. No DSP, no hooks. |
| Pack | A plugin's events answered by patches, plus an optional parameter overlay. |
| Patch | Layers, a flat parameter map keyed by address, and a list of connections. |
| Layer | One source (tone, noise, fm), an ordered processor list (lowpass, highpass, bandpass, delay), an amp envelope, a gain, a delay before it starts, a duration. |
| Connection | Resolve time arithmetic from velocity, variation or another parameter into a destination parameter: add, multiply-lerp, seeded-jitter, resolved-to-authored-ratio. |
| Voice class | bed, interface, world. Decides pool stealing, never sound. |
| Gate | Coverage, spectral, stress, distinctness, held-leak. Pass or fail a scenario's render. |
| Control surface | Snapshot, edit with optimistic revision, certify, audition. The one seam every adapter (CLI, HTTP, MCP, web) speaks. |

Registry: 40 parameter rows with codes like `AMP-03`, each with unit, legal range, response curve, default, authority (patch, output, trigger) and lifetime (frozen or live). Only the three listener rows are live.

## 2. What is genuinely strong

These are not compliments for the sake of balance. They are properties most audio codebases never reach and that should survive whatever comes next.

**Determinism by construction.** Time is frames, level is linear, pitch is cycles per frame. Units convert exactly once, in `voice-binding.ts`. Noise is a counter hashed PRNG (`drawAt(seed, index)`) so every sample is random access with no retained state, and the seed tree is labeled by ids rather than positions, so reordering layers or connections perturbs nothing. Any slicing of a render into blocks is sample identical. This is the property that lets certification gates mean anything and lets an offline bounce equal a realtime callback. Very few engines have it.

**Two independently derived answers held together by tests.** The renderer carries no end gate. The lifetime machine and the envelopes each say when a voice ends, and a seam test forces agreement. The same idea appears between the registry enum and the contract union (`oneOf` narrows by search, not by cast), and between a processor a patch can author and a stage the engine can render (one list, two views). This is how the codebase makes whole classes of silent bugs impossible rather than tested for.

**Voice pool with class floors.** Capacity 32, floors bed 4, interface 8, world 4, so half the pool is reserved and half contested. A burst of world sounds cannot evict the ambience. Steal victim is chosen by least life left, then age, then id, never by loudness, because loudness would be the signal deciding control. The steal ramp is foundation owned and unreachable from content. This is the correct middleware design and it is correctly walled off.

**Certification as a first class artifact.** A pack is not just heard, it is measured: a nine number acoustic fingerprint with quantization and tolerances derived from take spread, distinctness distances in tolerance units, gates that carry their own thresholds and no identities. The comment on `gate.ts` about a bound only being a gate when a gap separates pass from fail is a real methodological stance. This is a differentiator no DAW plugin and no game middleware ships.

**Control surface with optimistic concurrency.** Snapshot, edit with expected revision, refuse an edit the engine could not play (with the engine's own reason), rebuild the view from the patch. Adapter neutrality is tested. The MCP adapter means an agent can already drive the tool.

**Engineering hygiene.** Small files, one owner per concept, a structure verifier that rejects version literals outside the catalog and enforces declared package edges, branded ids, exhaustive `assertNever` switches, zero runtime dependencies in the engine. Comments explain why, and often record the bug that motivated the shape.

## 3. Gaps against the stated product

The product statement: a visually stunning, layer and plugin oriented professional tool that exposes every aspect of the Web Audio API for AAA sound effects and music scores in threejs games.

### 3.1 Identity gap: the engine does not sit on the Web Audio API

This is the first thing to decide, because everything else follows from it. The graph, the nodes, the AudioParam automation, the worklet, the panner, the convolver, the compressor, the analyser: none of it is used. The engine is a self contained DSP kernel and Web Audio is a speaker.

That is not a mistake. It is a choice with a large upside (determinism, certification, identical offline and realtime) and a large cost (every DSP feature is hand built, the browser's optimised native nodes go unused, and "exposes every aspect of the Web Audio API" is currently false).

The reconciliation is architectural, not a patch: host the deterministic kernel inside an `AudioWorkletProcessor` as the voice tier, and use the native graph as the mix tier where determinism matters less and the browser does the heavy lifting (buses, sends, convolution reverb, HRTF panning, dynamics). Section 5 expands this.

### 3.2 No realtime path

`MasterBus.render(block)` is designed for a callback (any length, fixed internal cadence, one clock) but nothing calls it from one. The web adapter renders the whole event offline then plays it. Consequences:

- A held bed with a live listener cannot work in the browser today. The listener schedule machinery exists and is unreachable from the page.
- Game integration (trigger on collision, release on state change, move with the camera) has no entry point.
- Every edit on the bench re-renders the whole sound on the main thread, then uploads a buffer. Fine for 2.5 s one shots, wrong for anything longer.

### 3.3 Modulation is resolve time only

Connections are arithmetic evaluated once when a voice starts. There are no LFOs, no per block modulators, no envelope followers, no step sequencers, no sample and hold, no random walk, no macro knobs, and no way for a game parameter to move a filter cutoff while a sound plays. The only time varying inputs are the amp envelope, the filter AD envelope, the pitch bend, the glide, and the listener field.

For a tool whose reference images are Serum 2, Europa and Reason, modulation is the product. The modulation matrix visible in the Europa screenshot (source, amount, destination, scale) is the shape to aim for, but with continuous sources.

### 3.4 Source palette is small and aliases

Three sources: naive tone (sine, square, saw, triangle), noise (five colours), two operator sine FM. The square and sawtooth shapes are naive piecewise functions with no band limiting, so above a few hundred hertz they alias audibly. For an "AAA" claim this is the first thing a sound designer will hear. Missing entirely:

- Sample playback (one shot, looped with loop points, pitched, reversed, random start)
- Wavetable with position and warp
- Granular and time stretch
- Additive and spectral
- Physical models: Karplus Strong string, modal resonators for impacts, waveguide, bowed and blown
- Multi operator FM with algorithms, feedback, operator envelopes
- Oscillator sync, PWM, unison and detune, sub oscillator, ring and amplitude modulation
- Formant and vowel
- Live input (MediaStream) for reactive design

### 3.5 Processor palette is small

Three biquad shapes and one feedback echo. Nothing else. Missing:

- Filters: notch, peak, low and high shelf, allpass, ladder (Moog), state variable, comb, formant, multimode with drive
- Dynamics: compressor, limiter per bus, gate, expander, transient shaper, sidechain, multiband
- Distortion: waveshaper with curves, saturation, bitcrush, sample rate reduction, wavefolder
- Time: reverb (the code explicitly acknowledges its absence), chorus, flanger, phaser, ping pong delay, tempo synced delay, diffusion
- Spectral: EQ, vocoder, frequency shifter, pitch shifter
- Utility: stereo widener, mid side, DC blocker, gain, mute, solo

Also, processors are per layer only. There is no patch level effect chain, no bus, no send, and no master chain beyond the limiter.

### 3.6 Topology is fixed

A layer is a strict series: source, filters, envelope, echoes. Layers are mono and sum. Stereo happens once. There is no way to route layer A's output into layer B's filter, no parallel processing, no feedback path, no per layer pan, no crossfade between layers by velocity or a game parameter (the blend container from middleware), no switch container.

### 3.7 Time is capped and there is no music

Patch duration is capped at 2.5 s, layer duration at 2 s, layer delay at 500 ms, echo time at 1 s. Sustain exists only as a held envelope level. There is no loop, no tempo, no transport, no clip, no sequence, no note events, no scale or chord awareness, no stinger, no transition, no quantisation. Half of the stated product (music scores) has no surface at all.

### 3.8 Spatialisation is two dimensional

Pan, width, distance. Distance is a good one pole air model with a falloff law. Missing: 3D position and orientation, HRTF, Doppler, cone attenuation, occlusion and obstruction, reverb zones and early reflections, listener orientation, emitter velocity. The threejs integration story (listener from camera, emitters on Object3D) does not exist yet.

### 3.9 Mixing model is absent

No buses, no groups, no sends, no ducking, no sidechain, no HDR window, no mixer snapshots or states, no game parameter (RTPC) system beyond the listener. The voice pool floors are hard coded and not adjustable per project.

### 3.10 Registry rows with no consumer

`OUT-01` output gain, `OUT-02` mute, `OUT-12.sample-rate`, `OUT-12.latency-hint` and `AMP-16.ramp-ms` are declared with `authority: "output"` and documented as "applied by the adapter". The web adapter's `Player` reads none of them: it constructs a default `AudioContext`, never passes `sampleRate` or `latencyHint`, and has no gain or mute node. Either the adapter honours them or the rows should not exist yet.

### 3.11 The word "plugin" is taken

In this codebase a plugin is a data only declaration of events and scenarios. In the product vision a plugin is a DSP unit a designer stacks in a layer. The existing meaning is valuable (it is what keeps content from touching the engine) but the name will collide the moment the product vocabulary arrives. Renaming the existing concept to something like "domain" or "event set" before the collision is cheap now and expensive later.

### 3.12 Extending the engine touches five places

Adding one processor kind today means editing the contract union, the registry rows, the processor definition list, the voice binding, the engine stage, and the validation. That is the right cost for a closed, certified set. It is the wrong cost for a product whose point is a large, growing plugin palette. A DSP plugin contract (parameter descriptor, modulation inputs, tail and latency reporting, seed, state serialisation, UI descriptor) is the missing abstraction. The existing registry `ParameterDefinition` is a strong start for the descriptor half.

### 3.13 Performance shape

Per sample work is a chain of closures: `output.process(envelope × generator.sample())` with `filtered()` and `echoed()` composed by `reduce`. Coefficients retune per sample whenever a filter envelope moves. This is fine offline for 2.5 s. At 32 realtime voices with several layers each it is a risk inside a 128 frame worklet quantum on a mid range laptop, and there is no SIMD, no WASM, no block level processing inside a stage. Block processing (process a Float32Array, not a sample) is the standard shape and it also matches what a worklet hands you.

### 3.14 Cross engine determinism caveat

Oscillators use `Math.sin`, envelopes use `Math.expm1`, colours use `**`. V8, JavaScriptCore and SpiderMonkey do not promise bit identical transcendental results. Within one engine renders are sample identical, which is what the tests assert. Across browsers the fingerprint tolerances absorb the difference, but any future claim of "bit identical everywhere" needs a table based or polynomial sine owned by the engine. Worth knowing before it becomes a promise.

### 3.15 Interface

The bench is semantic HTML: `details` and `summary` blocks, native range inputs, a 960 by 96 canvas waveform, a gate report. It is honest and accessible and it is a debugging tool, not the product. Nothing about it is layer or plugin shaped yet.

## 4. How far can the Web Audio API be pushed

Short answer: as far as the CPU budget of one render thread, with the browser's own nodes as free accelerators.

**Native nodes** (oscillator, buffer source, biquad, IIR, delay, gain, convolver, dynamics compressor, wave shaper, panner with HRTF, stereo panner, channel split and merge, analyser, media stream source and destination, constant source) are a fixed but well optimised toolkit. Every AudioParam accepts sample accurate automation curves (`setValueCurveAtTime`, ramps, `setTargetAtTime`) and can be driven by any node's output, so a native oscillator can be an LFO into any parameter with a-rate precision. The convolver gives production quality reverb for the cost of an impulse. The panner gives HRTF. The compressor gives ducking when its input is a summed side chain bus. None of this is deterministic across browsers and none of it is inspectable sample by sample, which is why the certification path should not depend on it.

**AudioWorklet** is where the ceiling actually is. Anything expressible as `process(inputs, outputs, parameters)` at 128 frames per call (now adjustable through `renderSizeHint` in Web Audio 1.1) can run on the audio thread. WebAssembly with SIMD inside a worklet reaches within a small factor of native. Emscripten ships a Wasm Audio Worklets API, and Faust, RNBO and Elementary all compile to this target, which is proof the ceiling is high enough for commercial synths. Constraints: no allocation in the hot path (GC pauses are audible), message port latency between main thread and worklet is one or more quanta, `SharedArrayBuffer` needs cross origin isolation headers, and a worklet cannot see the output device buffer size.

**Determinism.** `OfflineAudioContext` renders deterministically for a given browser build but not across browsers for native nodes. A worklet running the audioface kernel is deterministic to the same degree the kernel is (section 3.14).

**Hard limits nobody pushes past.** The audio thread has no guaranteed realtime priority on every platform. Output latency is what the device and the browser give (`baseLatency`, `outputLatency` are readable, not settable, beyond `latencyHint`). Autoplay policy requires a gesture. Channel count is bounded by the device. Safari lags on newer features (sinkId, render size, MIDI). Web MIDI is absent in Safari. There is no host synced clock beyond `currentTime` and `performance.now()` correlation.

**The practical ceiling** is therefore: a worklet kernel for everything that must be exact, deterministic or novel (all synthesis, all per voice processing, the voice pool, the certification path), and the native graph for everything that benefits from browser optimisation and does not need to be measured (bus mixing, convolution reverb, HRTF, sidechain ducking, output metering through `AnalyserNode`). That split also matches how the code is already drawn: everything up to the master sum is exact and everything after it is placement and mix.

## 5. Recommended direction

Stated as a direction, not a plan. The detail belongs to the three research reports listed under `related` and to the synthesis.

1. **Keep the kernel.** The deterministic frame based core, the seed tree, the pool, the gates and the control surface are the moat. Do not rewrite them around native nodes.
2. **Move the kernel into a worklet.** One `AudioWorkletProcessor` hosts `MasterBus` and calls `render(block)` per quantum. Same code offline and realtime, which is the promise the renderer comments already make. Messages in: start, release, listener updates, parameter changes. Messages out: voice states, meters.
3. **Add a native mix tier after the kernel.** Buses as `GainNode` groups, sends into `ConvolverNode` reverbs, `DynamicsCompressorNode` for ducking, `PannerNode` HRTF as an alternative to the kernel's pan when 3D is wanted, `AnalyserNode` for the UI. Honour the `OUT-*` rows here.
4. **Define the DSP plugin contract** before adding a second effect. Descriptor (reuse `ParameterDefinition`), block process function, modulation input ports, tail and latency reporting, seed label, serialisable state, and a UI descriptor. Refit the four existing processors and three sources to it, then grow the palette against one contract rather than five files.
5. **Make modulation continuous.** Modulators as plugins too (LFO, envelope, follower, random, step, game parameter), with a per block modulation pass and a matrix the UI can draw.
6. **Band limit the oscillators.** PolyBLEP or wavetable oscillators before anyone records the current saw.
7. **Lift the time cap and add a clock.** Loops, a transport, tempo, quantised triggers and stingers are the entry to music. The pool and the gates already know how to handle held voices.
8. **Rename the data plugin** to avoid the vocabulary collision.
9. **Design the UI as layers and racks** with the modulation matrix and the gate report as first class, and render meters and scopes on the GPU. The `ui-direction` report carries the concepts.

## 6. Questions the owner should answer

- Is cross browser bit identity a goal, or is fingerprint tolerance the promise? It changes whether the kernel may use `Math.sin`.
- Does the certification harness extend to music (tempo, loops, transitions), or does music get a different kind of gate?
- Should the native mix tier be measurable at all, or is it explicitly outside certification?
- How large a plugin palette is the target for the first release? It sets whether the contract can stay closed for one more milestone.
