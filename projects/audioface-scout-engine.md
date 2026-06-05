# Audioface Scout: Engine and Render Path

Date: 2026-08-18
Repo: `/Users/alphab/Dev/LLM/DEV/helioy/audioface` at `556b7c8c281b06be725d96c4c9eed192e9a7ce20`
Tree: clean before inspection, after focused verification, and before this report write
Scope: current engine, Phase 1 Patch resolution, Studio and Lab browser consumers, audit rendering, and the acoustic golden master

This report maps current ownership and observed gaps. It does not select a Phase 2 engine design.

## Reuse Map

### Existing owners

| Rewrite capability | Existing owner | Reuse fact |
|---|---|---|
| Authoritative resolved synthesis value | `packages/core/src/patch-resolution.ts` `ResolvedPatch`, `resolvePatch`, `PatchResolver` | Already produces one frozen value with resolved addresses, audible ordered layers, output chain, duration, and metrics. Connection math and mute or solo decisions finish before rendering. |
| Parameter identity and lookup | `packages/core/src/patches.ts` `ParameterAddress`, `parseParameterAddress`, `layerParameterAddress`, `processorParameterAddress`, `patchParameterAddress` | One address grammar covers layer, processor, envelope segment, connection, and output chain children. |
| Parameter metadata and capability declarations | `packages/core/src/parameter-registry.ts` `PATCH_CONTROL_REGISTRY`, `SOURCE_DEFINITIONS`, `PROCESSOR_DEFINITIONS`, `STRUCTURAL_OWNER_DEFINITIONS`, `getParameterDefinition` | One registry owns all 33 current parameter keys, ranges, resolution status, source support, processor support, and structural limits. |
| Patch structure and ordering | `packages/core/src/patches.ts` `Patch`, `PatchLayer`, `LayerProcessor`, `OutputProcessor` | Arrays own layer, processor, envelope segment, connection, and output order. Stable ids already survive resolution. |
| Patch boundary validation | `packages/core/src/patch-validation.ts` `validatePatch`; `packages/core/src/patch-schema.ts` `patchSchema` | Existing validation distinguishes malformed data, unsupported capability, and known orphan values. |
| Current Patch to engine compatibility proof | `packages/core/src/playback.ts` `resolvePatchPlayback`, `toResolvedPlayback`; `packages/core/src/canonical-patches.ts` `projectPatchToAudiofaceTokenDefinition` | These adapters preserve Phase 1 sound through the legacy `AudiofaceLayer` union. They are evidence and migration machinery. The projection is lossy for the Phase 2 render contract. |
| Production engine lifecycle | `packages/engine/src/index.ts` `createAudiofaceEngine`, `AudiofaceEngine` | Already owns lazy browser context creation, injected contexts, resume, volume, scheduled source tracking, cancellation, and one shared output graph. |
| Audio clock placement | `packages/engine/src/index.ts` `resolveStartAt` | Owns the six millisecond scheduling lead and nonnegative millisecond flow offset. |
| Source dispatch | `packages/engine/src/index.ts` `scheduleLayer` | Exhaustive switch over the current legacy tone, noise, and FM source union. |
| Tone construction | `packages/engine/src/index.ts` `scheduleTone` | Owns oscillator creation, waveform selection, start pitch, end pitch, exponential pitch ramp, timing, and routing. |
| Noise construction | `packages/engine/src/index.ts` `scheduleNoise`, `getNoiseBuffer`, `noiseBuffers` | Owns the looping one second noise source, fixed `audioface-v1` sample formula, mono buffer, and context local cache. |
| FM construction | `packages/engine/src/index.ts` `scheduleFm` | Owns sine carrier and modulator creation, modulation gain, frequency modulation edge, modulation decay, timing, and routing. |
| Layer amplitude | `packages/engine/src/index.ts` `createLayerOutput` | One function serves all source kinds and owns the current epsilon, attack floor, linear attack, exponential fall, layer gain, and layer to master edge. |
| Layer filter | `packages/engine/src/index.ts` `connectFilter` | Owns one optional static biquad before the layer gain. Only noise calls it today. |
| Source lifetime | `packages/engine/src/index.ts` `startAndStop` | Owns start, stop, 25 millisecond tail, and scheduled source tracking. |
| Master output | `packages/engine/src/index.ts` `createOutput` | Owns master gain, fixed compressor, and destination routing. |
| Studio browser integration | `apps/studio/src/app/useStudioPlayback.ts` `ensureEngine`, `playResolved`, `auditionFlow`, `stopFlow` | One engine instance serves single auditions and complete flows. Flow events use engine clock offsets. |
| Offline Web Audio adapter | `scripts/audit/render.mjs` `renderResolvedPlayback` | Injects `OfflineAudioContext` into the package engine, schedules through `AudiofaceEngine.playResolved`, calls `startRendering`, and returns the measured signal. |
| Deterministic offline noise | `scripts/audit/render.mjs` `withDeterministicRandom`, `createDeterministicRandom` | Makes the package engine's `Math.random` noise buffer deterministic during synchronous scheduling. |
| Acoustic measurements | `scripts/audit/descriptors.mjs` `describeSignal`, `measureAcousticFingerprint` | Existing mono envelope and spectral measurements cover level, onset, attack, decay, centroid, rolloff, spectral evolution, and audible duration. |
| Acoustic regression gate | `scripts/golden-master/golden-master.mjs` `GOLDEN_MASTER_RENDER_CASES`, `fingerprintToken`, `createGoldenMaster`, `compareGoldenMasters`; `scripts/golden-master/baseline.jsonl` | The current gate renders 23 canonical patches through 10 cases and compares 230 fingerprints. |
| Runnable reference graph | `src/audioface.js` `createAudiofaceEngine` and private scheduler functions | The Lab spike keeps the original JavaScript graph for product comparison. `ARCHITECTURE.md` and `LESSONS.md` exclude it from Studio and production package ownership. |

### Synthesis primitives and routing actually implemented

| Category | Primitive and behavior | Builder and routing edges |
|---|---|---|
| Tone oscillator | One `OscillatorNode`. Usable Patch waveforms are sine, square, sawtooth, and triangle. Frequency starts at `PCH-01` and ramps exponentially to `PCH-01.end-hz` over `TIM-03`. | `packages/engine/src/index.ts` `scheduleTone`: oscillator to layer gain. |
| FM carrier | One sine `OscillatorNode` at `PCH-01`. | `packages/engine/src/index.ts` `scheduleFm`: carrier to layer gain. |
| FM modulator | One sine `OscillatorNode` at `SRC-08.modulator-hz`. | `packages/engine/src/index.ts` `scheduleFm`: modulator to modulation gain to carrier frequency. |
| FM modulation gain | One `GainNode`. Gain starts at `SRC-09` and falls exponentially to `0.0001` across `TIM-03`. | `packages/engine/src/index.ts` `scheduleFm`: modulation gain to the carrier `frequency` AudioParam. |
| Noise source | One looping `AudioBufferSourceNode` using a one channel, one second buffer. Each sample is `white * 0.66 + low * 2.4`, where `low` is the leaky accumulated white sample. | `packages/engine/src/index.ts` `scheduleNoise`, `getNoiseBuffer`: source to optional biquad or directly to layer gain. |
| Layer filter | Zero or one `BiquadFilterNode`, static type, frequency, and Q. The engine's legacy input admits all Web Audio biquad types. Patch projection admits lowpass, highpass, and bandpass. Only noise can reach the filter. | `packages/engine/src/index.ts` `connectFilter`: noise source to biquad to layer gain. |
| Layer amplitude floor | Gain is set to `0.0001` at layer start. | `packages/engine/src/index.ts` `createLayerOutput`. |
| Layer attack segment | Linear ramp from `0.0001` to `max(0.0001, gain)`. Attack has a 0.5 millisecond floor. | `packages/engine/src/index.ts` `createLayerOutput`. |
| Layer fall segment | Exponential ramp from peak to `0.0001` at `max(TIM-03, AMP-03)`. The saved `AMP-06` decay is not read. There is no hold, sustain, or separately scheduled release. | `packages/engine/src/index.ts` `createLayerOutput`. |
| Tone pitch segment | Exponential frequency ramp between the two absolute pitch endpoints. The curve is fixed. | `packages/engine/src/index.ts` `scheduleTone`. |
| FM index segment | Exponential modulation gain ramp from the resolved index to `0.0001`. The curve and endpoint are fixed. | `packages/engine/src/index.ts` `scheduleFm`. |
| Per layer gain stage | One audio `GainNode` per layer. All layers feed the same master in parallel. | `packages/engine/src/index.ts` `createLayerOutput`: layer gain to master. |
| Master gain stage | One `GainNode`, initial value `volume ?? 0.34`. `setVolume` uses a 12 millisecond `setTargetAtTime` constant. | `packages/engine/src/index.ts` `createOutput`, `createAudiofaceEngine.setVolume`: master to compressor. |
| Output dynamics stage | One `DynamicsCompressorNode`: threshold `-18`, knee `8`, ratio `9`, attack `0.002`, release `0.08`. | `packages/engine/src/index.ts` `createOutput`: compressor to `context.destination`. |
| Source lifetime | Source start is base start plus `TIM-02`. Stop is source start plus `TIM-03` plus 25 milliseconds. FM starts and stops both oscillators. | `packages/engine/src/index.ts` `startAndStop`. |

The complete audio paths are:

- Tone: oscillator to layer gain to master gain to compressor to destination.
- Noise without filter: buffer source to layer gain to master gain to compressor to destination.
- Noise with filter: buffer source to biquad to layer gain to master gain to compressor to destination.
- FM audio: carrier to layer gain to master gain to compressor to destination.
- FM control: modulator to modulation gain to carrier frequency.

### ResolvedPatch capability that the package engine does not render

The registry has 33 parameter keys. Twelve reach current sound or scheduling: `SRC-37.enabled`, `SRC-02`, `PCH-01`, `PCH-01.end-hz`, `SRC-08.modulator-hz`, `SRC-09`, `AMP-01`, `AMP-03`, `TIM-02`, `TIM-03`, processor `FLT-10`, and processor `FLT-11`. `SRC-37.enabled` is honored by `PatchResolver.audibleLayers` before engine entry. Filter addresses reach only the first processor on a noise layer.

The other 21 addresses have no complete binding from `ResolvedPatch` to the current engine:

| Address | Resolved state | Current render result |
|---|---|---|
| `layer/<id>/SRC-16` | Migrated patches carry the future seed `audioface-v1`. White, pink, brown, blue, and violet are registered values but cannot pass Phase 1 resolution as authored changes. | `getNoiseBuffer` always builds the fixed blend and never reads the address. Only the seed behavior exists. |
| `layer/<id>/SRC-30` | Registered for the impulse source. | Impulse is a known structure that `PatchResolver.requireImplementedLayer` rejects. No source reads sample count. |
| `patch/AMP-02` | Future seed `0`. | No patch gain node or parameter read. |
| `patch/AMP-16.ramp-ms` | Future seed `2`. | Engine ramps are hard coded in `createLayerOutput` and `setVolume`. |
| `patch/AMP-16.epsilon` | Future seed `0.0001`. | The same value is hard coded in layer gain and FM modulation code. |
| `layer/<id>/PCH-03` | Future neutral seed. | Fine tune is discarded by the legacy projection. |
| `layer/<id>/PCH-09` | Future neutral seed. | Pitch ratio is discarded by the legacy projection. |
| `layer/<id>/PCH-05` | Future neutral seed. | No pitch envelope depth binding. |
| `layer/<id>/PCH-06` | Future seed. | No pitch envelope time binding. |
| `layer/<id>/AMP-04` | Future seed `lin`. | Attack is always linear. No address read. |
| `layer/<id>/AMP-05` | Future seed `0`. | No hold segment. |
| `layer/<id>/AMP-06` | Implemented resolution. Canonical warmth connections can change it. `projectLegacyLayerFields` emits `layer.decay`. | `createLayerOutput` never reads `layer.decay`. Authored and resolved changes are silent. |
| `layer/<id>/processors/<id>/FLT-14` | Future neutral seed. | No filter envelope depth binding. |
| `layer/<id>/processors/<id>/FLT-15.attack-ms` | Future seed `0`. | Filter frequency is static. |
| `layer/<id>/processors/<id>/FLT-15.decay-ms` | Future seed. | Filter frequency is static. |
| `output/OUT-01` | Implemented and present in `ResolvedPatch.parameters`. | `toResolvedPlayback` removes output addresses. Studio separately sends `theme.volume` to `setVolume`; the resolved value has no render contract. |
| `output/OUT-02` | Implemented and present in `ResolvedPatch.parameters`. | No mute behavior. |
| `output/OUT-12.sample-rate` | Implemented and present in `ResolvedPatch.parameters`. | Browser context creation supplies no sample rate. Injected contexts decide their own rate. |
| `output/OUT-12.latency-hint` | Implemented and present in `ResolvedPatch.parameters`. | Browser context creation supplies no latency hint. |
| `patch/output-chain/<id>/FXP-32` | Future output processor parameter. | Any nonempty output chain fails `PatchResolver.requireImplementedOutput`. No DC blocker exists. |
| `patch/TIM-01` | Derived from maximum layer delay plus duration. | `ResolvedPatch.durationMs` is separately calculated from duration only. The engine ignores both top level duration values and schedules each layer directly. |

Structural gaps are wider than the address table:

- `ResolvedPatchLayer` is an alias of `PatchLayer`, so its public type admits modal, pluck, impulse, and granular sources. Resolution rejects all four.
- The type admits up to four ordered processors on any layer. Resolution permits at most one processor on noise and rejects processors on tone or FM.
- The type carries envelope segments. Resolution rejects any nonempty segment list.
- The type carries an output chain. Resolution rejects any nonempty chain.
- `ResolvedPatch` carries `patchId`, stable layer ids and names, `durationMs`, and ten metrics. The engine sees none of these. Metrics remain useful to inspection and fingerprinting.

### Current engine behavior absent from ResolvedPatch expression

| Current engine behavior | Existing owner | Missing Patch expression |
|---|---|---|
| Fixed master compressor and its five settings | `packages/engine/src/index.ts` `createOutput` | The only output processor type is `dc-block`. No compressor structure or addresses exist. |
| Fixed exponential tone pitch curve | `packages/engine/src/index.ts` `scheduleTone` | Patch carries start and end frequency only. |
| Fixed sine carrier and sine modulator | `packages/engine/src/index.ts` `scheduleFm` | No waveform address exists for either FM oscillator. |
| Fixed FM index fall to `0.0001` | `packages/engine/src/index.ts` `scheduleFm` | No modulation envelope shape, duration, or endpoint address exists. |
| Fixed amplitude fall curve | `packages/engine/src/index.ts` `createLayerOutput` | `AMP-04` describes attack curve only and is future. Envelope segments are structurally present but unreachable and have no registered point parameters. |
| Noise realization seed, one second buffer length, cache policy, and sample formula | `packages/engine/src/index.ts` `getNoiseBuffer`, `noiseBuffers` | `SRC-16` can name `audioface-v1`, but the resolved value carries no realization seed, length, or cache policy. Resolution seed controls parameter jitter, not audio noise samples. |
| Five additional legacy biquad types: lowshelf, highshelf, peaking, notch, allpass | `packages/core/src/tokens.ts` `NoiseLayer`; `packages/engine/src/index.ts` `connectFilter` | `LayerProcessor.type` registers only lowpass, highpass, and bandpass. Direct legacy playback can still reach the other types. |
| Six millisecond lookahead and 25 millisecond stop tail | `packages/engine/src/index.ts` `resolveStartAt`, `startAndStop` | These execution rules have no resolved Patch representation. |
| Every layer mixed in parallel to one master | `packages/engine/src/index.ts` `playResolved`, `scheduleLayer`, `createLayerOutput` | Patch connections are parameter modulation edges. The rendered audio topology is implicit. |
| Twelve millisecond master volume smoothing | `packages/engine/src/index.ts` `createAudiofaceEngine.setVolume` | `OUT-01` carries a static value only. |

### Render front doors and duplicated graph ownership

There are three top level render front doors and two graph implementations.

1. `src/audioface.js` `createAudiofaceEngine` serves the Lab browser spike through `apps/lab/src/app.js` `ensureEngine`. It exposes legacy `play` and `playResolved` methods.
2. `packages/engine/src/index.ts` `createAudiofaceEngine` serves Studio browser playback through `apps/studio/src/app/useStudioPlayback.ts` `ensureEngine`.
3. `scripts/audit/render.mjs` `renderResolvedPlayback` serves Node offline playback. It injects `OfflineAudioContext` into the package engine and calls the same `AudiofaceEngine.playResolved` method as Studio.

`scripts/audit/stage2.mjs` `renderDescriptorSample` and `render` are audit workflows over `renderResolvedPlayback`. `scripts/golden-master/golden-master.mjs` `fingerprintToken` and `createGoldenMaster` are golden workflows over the same adapter. They do not build Web Audio nodes.

Graph construction duplication between the production browser path and offline Node is zero. Both execute the package engine's `createOutput`, `scheduleLayer`, `scheduleTone`, `scheduleNoise`, `scheduleFm`, `createLayerOutput`, `connectFilter`, `startAndStop`, and `getNoiseBuffer`.

The second graph is the ruled Lab spike. Nine declarations have the same names in `src/audioface.js` and `packages/engine/src/index.ts`:

- `noiseBuffers`
- `createAudiofaceEngine`
- `scheduleNoise`
- `scheduleTone`
- `scheduleFm`
- `createLayerOutput`
- `connectFilter`
- `startAndStop`
- `getNoiseBuffer`

Two more graph blocks duplicate behavior under different structure. Root `scheduleToken` corresponds to package `playResolved` plus `scheduleLayer`. Root inline master construction corresponds to package `createOutput`.

The copies have drifted. The package engine owns offsets, tracked sources, and `stopAll`. The Lab engine owns legacy token resolution, sequence seeds, and return values. Root `connectFilter` retains an unused `source` argument. `ARCHITECTURE.md` treats the Lab graph as runnable product memory, although root `package.json` still publishes it through the `./audio` export.

### Offline channel decision

Offline rendering is strictly mono in `scripts/audit/render.mjs` `renderResolvedPlayback`:

- `OfflineAudioContext` receives `1` as its channel count.
- The result returns `buffer.getChannelData(0)` only.
- `scripts/audit/descriptors.mjs` consumes one `Float32Array`.
- `packages/engine/src/index.ts` `getNoiseBuffer` also creates one channel, and the graph contains no panner, merger, splitter, or stereo source.

Two separate changes are required before stereo can be proved. The offline adapter and fingerprint contract must retain and measure both channels. Meaningful stereo also needs engine graph behavior and Patch controls that can produce independent left and right information. Changing the offline context to two channels alone would measure device upmix or dual mono. `README.md` already requires channel specific fingerprints before pan or stereo width lands.

### None found

- No direct `ResolvedPatch` renderer or scheduler. Search: `rg -n "renderResolvedPatch|renderPatch|schedulePatch|playPatch|ResolvedPatchRenderer|PatchRenderer" packages apps scripts test -g '*.{ts,tsx,mjs}'`.
- No pan, panner, channel merger, channel splitter, or channel routing owner. Search: `rg -n "StereoPanner|createStereoPanner|createPanner|ChannelMerger|ChannelSplitter|createChannelMerger|createChannelSplitter|\\bpan\\b|channelCount|channelInterpretation" packages apps scripts test -g '*.{ts,tsx,mjs}'`.
- No engine implementation for DC block, pitch envelope, filter envelope, or Patch envelope segments. Search: `rg -n "createIIRFilter|dc-block|filter envelope|pitch envelope|envelopeSegments|EnvelopeSegment" packages/engine scripts/audit scripts/golden-master -g '*.{ts,mjs}'`.
- No typed shared context contract for browser and offline rendering. Search: `rg -n "BaseAudioContext|OfflineAudioContext" packages -g '*.ts'`.

## Quality Map

### Q1. Resolved decay is silent

`packages/core/src/patch-resolution.ts` `PatchResolver.resolvePatchLayer` resolves `layer/<id>/AMP-06`. `packages/core/src/canonical-patches.ts` `connectionDraftsForLayer` routes warmth into it, and `projectLegacyLayerFields` emits `layer.decay`. `packages/engine/src/index.ts` `createLayerOutput` never reads that property.

A focused offline probe changed only decay from 5 milliseconds to 80 milliseconds on the same tone. All 9,600 rendered samples were byte identical. Existing `test/patch-resolution.test.mjs` coverage stops after asserting the projected property.

### Q2. Resolved duration disagrees with scheduling

`packages/core/src/patch-resolution.ts` `PatchResolver.deriveParameter` derives `patch/TIM-01` from maximum `TIM-02 + TIM-03`. `PatchResolver.resolve` calculates `ResolvedPatch.durationMs` from `TIM-03` alone. `packages/core/src/playback.ts` `toResolvedPlayback` copies the shorter sibling into `token.duration`. The engine schedules the source after `TIM-02`.

A focused probe with 200 milliseconds of delay and 100 milliseconds of duration produced `ResolvedPlayback.token.duration = 100` milliseconds. The scheduled acoustic extent is 300 milliseconds before the engine's fixed tail.

### Q3. Valid attack values disagree with the graph

`packages/core/src/parameter-registry.ts` `PATCH_CONTROL_REGISTRY` permits resolved `AMP-03` down to 0.35 milliseconds. `packages/engine/src/index.ts` `createLayerOutput` floors attack at 0.5 milliseconds. The valid resolution domain therefore does not match Web Audio behavior.

The registry also permits a 40 millisecond attack with a 4 millisecond layer duration. `createLayerOutput` schedules the peak at 40 milliseconds, while `startAndStop` stops the source at 29 milliseconds. That valid source ends before reaching peak gain.

### Q4. The render boundary discards Patch structure

`packages/core/src/playback.ts` `toResolvedPlayback` rebuilds a temporary Patch from the resolved values, clears connections, projects it to legacy `AudiofaceLayer`, and returns only `ResolvedPlayback`. `AudiofaceEngine.playResolved` then reads only `playback.token.layers`.

This boundary removes stable ids, processor arrays beyond one noise filter, envelope segments, output chain, output addresses, Patch duration, and parameter identity. The public `ResolvedPatch` type simultaneously admits source and child states that `PatchResolver` cannot return. The rewrite starts with a contract mismatch, not an empty engine.

### Q5. Output values have two owners

`packages/core/src/playback.ts` `outputParameterMap` creates `OUT-01`, `OUT-02`, sample rate, and latency hint values. `toResolvedPlayback` removes every output address. Studio separately calls `AudiofaceEngine.setVolume(theme.volume)`. Golden rendering separately passes `playback.theme.volume`, while Stage 2 intentionally omits it and stays on engine default `0.34`.

The current behavior is pinned by `test/golden-master.test.mjs` `shared offline rendering keeps stage 2 on the engine default volume`. The resolved output map does not own what the engine receives.

### Q6. Offline deterministic noise mutates global state

`scripts/audit/render.mjs` `withDeterministicRandom` replaces global `Math.random` while the engine synchronously builds its cached noise buffer. It restores the original function in `finally`, so current serial golden and audit calls are stable. Concurrent `renderResolvedPlayback` calls can interleave seeds because the mutation is process global.

Core also owns a deterministic generator at `packages/core/src/runtime.ts` `seededRandom`, but it has a different algorithm and sound identity. Reuse requires an explicit compatibility decision.

### Q7. Offline render length can truncate valid Patch timing

`scripts/audit/render.mjs` `OFFLINE_RENDER_SECONDS` fixes the default window at 750 milliseconds. The registry permits 500 milliseconds of layer delay and a resolved duration up to 350 milliseconds. `resolveStartAt` adds six milliseconds. A valid resolved source can therefore extend to 856 milliseconds before the fixed stop tail.

`scripts/golden-master/golden-master.mjs` `assertRenderWindow` rejects current golden cases that approach 700 milliseconds. Stage 2 has no equivalent guard, and the fixed buffer has already truncated any signal beyond its end.

### Q8. Browser and offline context reuse is runtime only

`packages/engine/src/index.ts` `AudiofaceEngineOptions.context` is typed as `AudioContext`. `scripts/audit/render.mjs` passes `node-web-audio-api` `OfflineAudioContext` from untyped JavaScript. The shared graph works at runtime, but TypeScript does not describe the context capability the engine actually accepts.

### Q9. Engine tests pin text more than behavior

`test/engine.test.mjs` checks API presence, start offset arithmetic, cancellation bookkeeping, and source text markers. It does not execute each parameter address against a Web Audio graph.

The acoustic golden master supplies strong end to end evidence for the 23 canonical patches. Its 230 fingerprints are mono and omit phase and polarity by documented policy. It does not cover noncanonical valid boundaries such as 0.35 millisecond attack, long delay, extra legacy filter types, custom waveform, or every discarded resolved address.

`packages/core/src/patch-schema.ts` `legacyLayerSchema` accepts waveform `custom`. `packages/engine/src/index.ts` `scheduleTone` assigns it to `oscillator.type` and never calls `setPeriodicWave`. Canonical Patch migration rejects custom, so this is limited to legacy compatibility input.

### Q10. The Lab graph is a deliberate duplicate with a public export

History shows the original root graph, then package native Studio playback, then deliberate package parity with Lab. Later commits added offsets and cancellation to the package graph only. The offline adapter was then consolidated around the package engine.

`ARCHITECTURE.md` assigns playback ownership to `packages/engine` and classifies root `src` as a runnable spike. Root `package.json` still exports `src/audioface.js` as `./audio`. The repo therefore has one documented production owner and a second package visible reference owner.

Current parity tests compare resolved token values and package source markers. They do not render both graphs, so scheduler drift can pass.

### Q11. Consumer lifecycle cleanup is incomplete

`apps/studio/src/app/useStudioPlayback.ts` `useStudioPlayback` lazily creates an engine and can stop a flow. Its effect updates volume only. No unmount cleanup stops remaining scheduled sources or closes the browser context.

### Q12. Audit calculations have local duplication

- `scripts/audit/descriptors.mjs` `energyWeightedCentroid` and `energyWeightedMetric` perform the same weighted reduction.
- `describeSignal` and `measureAcousticFingerprint` repeat full, early, and late frame construction with different region rules.
- `ACOUSTIC_QUANTIZATION`, `ACOUSTIC_TOLERANCES`, and `ACOUSTIC_METRICS` repeat the same nine metric identities across audit and golden files.
- `SILENCE_FLOOR_DB` owns minus 60 dB measurement behavior, while `createGoldenMaster` writes the same value into metadata as a separate literal.

The similarly named Stage 2 and golden decay metrics are semantically different. Stage 2 uses a coarse minus 30 dB decay; golden measurement uses a fine minus 60 dB active region. They should remain distinct.

### Threshold and verification facts

No inspected file exceeds 700 lines and no inspected function exceeds about 150 lines. The closest files are `packages/core/src/parameter-registry.ts` at 669 lines, `apps/lab/src/app.js` at 654, and `packages/core/src/canonical-patches.ts` at 649. Any material addition to those files must respect the hard threshold.

Focused verification at the requested commit:

- `node --test test/engine.test.mjs test/patch-resolution.test.mjs test/golden-master.test.mjs`: 33 passed, 0 failed.
- `pnpm run audio:golden`: matches 23 tokens across 10 render cases and 230 fingerprints.
- Focused decay probe: 9,600 samples, 0 differences after changing only projected decay.
- Focused duration probe: 200 millisecond delay plus 100 millisecond duration reported 100 milliseconds at the playback boundary.

## Plan

No implementation shape is selected here. The evidence orders the Phase 2 decisions and proof work.

1. Record the authoritative render boundary before code moves. Current architecture names `packages/engine`; the remaining disposition is the root `./audio` export and the runnable Lab spike graph.
2. Turn the 33 address inventory into an explicit Phase 2 behavior matrix. Preserve the 12 current bindings. Give each of the 21 gaps a visible disposition. Include source, processor, envelope segment, output chain, and output context structure. No address may disappear through the legacy adapter without a recorded decision.
3. Resolve the three current semantic contradictions before judging rewrite parity: silent `AMP-06`, duration without delay, and attack values outside the graph's executable timing. Each needs a focused failing behavioral case and a ruled expected result.
4. Preserve one production graph across browser and offline contexts. Keep the current shared scheduling evidence while making the accepted context capability explicit in TypeScript.
5. Use the existing source builders, common layer output, filter builder, source lifetime, output stage, scheduling clock, and cancellation behavior as the baseline inventory. Decide each reverse gap deliberately: compressor policy, fixed curves, FM waveforms, noise realization, timing tail, and implicit mix topology.
6. Extend behavioral coverage at the address to Web Audio boundary. Keep the 230 fingerprint gate as the sound identity check. Add narrow graph checks for noncanonical valid boundaries and every newly audible address.
7. Gate stereo separately. First add channel specific offline output and fingerprints. Then evaluate any Patch and engine behavior that creates independent channels. A two channel context with mono nodes is insufficient evidence.
8. Keep audit cleanup separate from acoustic changes. The descriptor reductions and metric metadata have clear local owners, but their distinct region and decay semantics must remain intact.
9. For implementation verification, run focused engine, Patch resolution, and golden tests after each bounded change. Finish with `pnpm run audio:golden`, `pnpm run check`, a clean baseline diff unless sound change was explicitly approved, and a pristine tree audit against the exact reviewed commit.
