---
title: Audioface foundations runtime Scout
type: projects
tags: [audioface, foundations, scout, runtime, host, reuse]
summary: Independent proposal comparison, runtime reuse and quality findings, recommended dispositions, and bounded architecture probes.
status: draft
created: 2026-09-05
updated: 2026-09-05
project: audioface-next
confidence: high
related: [audioface-foundations-fable--brainstorm, audioface-foundations-astra--brainstorm, audioface-phase2-data-runtime-design]
source: https://github.com/littleorgans/audioface
---

# Runtime foundation Scout

Baseline `10ba9fc16cea55271c6d428c8fe64c8df0b9c354`, clean before and after. Both supplied proposal hashes match. Recommendations below await the lead's disposition. No architecture or shipping capacity is accepted.

## Comparison and resolutions

The [Fable proposal](audioface-foundations-fable--brainstorm.md) and [Astra proposal](audioface-foundations-astra--brainstorm.md) converge on authored data, derived programs, independent runtime state, declared tails, deterministic seeds, and shared Studio/game execution. Their operational contracts differ:

- **Compilation.** Fable's exclusive cost knowledge and free nesting claims are unsupported. A validated native graph can also have resource accounting. Flattening removes traversal overhead; replicated state and DSP remain. Prefer a minimal JS schedule provisionally. Falsifier: the native candidate meets required semantics with lower measured cost and less implementation.
- **Continuous edits.** Commands avoid recompilation only within declared resource and topology limits. `packages/patch/src/voice-binding.ts` `bindEcho` removes zero level echoes; `packages/engine/src/layer-echo.ts` `echoStage` fixes buffer length at construction. Zero to positive level or increased delay can require preparation. Reserve maximum capacity only where the measured cost is acceptable.
- **Structural edits.** Fable's new voices adopting a new program differs from the [prior design](../design/audioface-phase2-data-runtime-design.md), which pins even future triggers on existing handles. Draining leaves an indefinitely held note on the old graph. Recommend explicit activation, bounded compatible state transfer or crossfade, and a visible pending edit when overlap cannot fit. Failed exact transfer does not establish drain as the only alternative. Null tests apply to unchanged signal histories. An inserted filter intentionally changes output.
- **Scopes and clocks.** Neither proposal defines nested independent voice spawning. Initially permit one root voice split, inherited scope below it, and reject recursive or nested spawning. Count every placement and explicit shared bus. Fable forbids Sound controls feeding Voices; Astra proposes broadcast. Define explicit control broadcast separately from audio feedback. Fable also admits explicit block delayed feedback immediately; Astra defers external cycles. Defer that extension until delay and bounded shutdown semantics are specified. Frame based control ticks must survive ragged block slicing; per callback modulation does not guarantee this.
- **Identity.** Embedding divergent copies with the same origin and revision cannot supply a unique program cache key. Keep provenance informational. Key preparation by resolved content, dependencies, sample rate, and execution format. Placement identity owns runtime state; device generation invalidates commands, without becoming a second DSP seed authority. Undo position and immutable revision identity must remain separate.
- **Spatial routing.** Fable and current [issues 4](https://github.com/littleorgans/audioface/issues/4) and [6](https://github.com/littleorgans/audioface/issues/6) retain native nodes after one stereo sum. Independent emitter HRTF requires earlier signals. Probe separate outputs before choosing the boundary. Measure and protect the actual final mix.

Falsify the edit and scope recommendations with one sustained nested instrument: resize delay, change routing, undo repeatedly, release, and recover every reservation without resetting unchanged phase.

## Platform claims need narrower wording

The [Web Audio 1.1 draft](https://www.w3.org/TR/webaudio-1.1/#rendering-loop) places message tasks on the rendering thread and describes configurable quantum size. It does not establish browser support. Read actual output lengths. `outputLatency` estimates device output latency; callback cost needs separate measurement. Native output can be captured through `OfflineAudioContext`; lack of internal state serialization does not prevent signal gates.

Fable's WASM benefits are conditional. Linear memory must be bounded by policy, and JS glue still participates in allocation. WASM has [no built in transcendental functions](https://webassembly.org/docs/faq/); reproducibility depends on the selected library and operations. [Chrome's design patterns](https://developer.chrome.com/blog/audio-worklet-design-pattern) document heap copies and live compilation risks. Audioface still needs comparative measurements. Worker generated audio adds buffering and underrun semantics. [Shared memory serialization](https://html.spec.whatwg.org/multipage/structured-data.html#structuredserializeinternal) requires cross origin isolation; ordinary MessagePort messages do not. Retain MessagePort for initial probes.

## Reuse map

| ID | Capability and existing source | Reuse boundary and rejected substitute |
| --- | --- | --- |
| R1 | `packages/engine/src/source-generator.ts` `createSourceGenerator`, `phaseAccumulator`; `noise-source.ts` `createNoiseGenerator`; `layer-filter.ts` `filtered`; `layer-echo.ts` `echoed`; `amplitude-envelope.ts` `stageLevel` | Reuse algorithms and corresponding engine tests. Stateful closures need explicit configuration/state seams for edits. `stageLevel` already serves filter envelopes. Existing naive waveforms do not establish a band limited synthesis quality floor. |
| R2 | `packages/patch/src/patch-resolution.ts` `PatchResolver.resolveAddress`; `voice-binding.ts` `bindVoice`; `registry/units.ts` `framesFromMilliseconds`, `cyclesPerFrameFromHertz`; `packages/contract/src/seed.ts` `rootSeed`, `childSeed`, `drawAt` | Reuse value resolution, conversions, cycle evidence, and labeled streams. Resolution produces scalar Voice data. Buffer scheduling remains unimplemented. Its parameter graph cannot execute audio feedback or event ports. |
| R3 | `packages/engine/src/voice-lifetime.ts` `beginVoice`, `voiceHasEnded`; `packages/contract/src/echo.ts` `echoTailFrames`; `packages/engine/src/voice-pool.ts` `VoicePool` | Reuse declared lifetime and deterministic selection rules. Tail calculation ends at a defined floor. Class floors encode policy; resource limits need measurement. No Sound owner exists yet. |
| R4 | `packages/control/src/bus-host.ts` `createBusHost`, `onBusClock`; `packages/engine/src/command-queue.ts` `CommandQueue`; `stamped-bus.ts` `StampedBus` | Reuse origin translation, equal frame insertion order, late handling, and refusal correlation. Adapt one scheduling mechanism for bounded, cancellable prepared entries. Host and StampedBus both own queues today. |
| R5 | `packages/engine/src/master-bus.ts` `MasterBus`; `distance-field.ts` `DistanceField`; `stereo-image.ts` `StereoImage`, `ListenerSchedule`; `master-limiter.ts` `MasterLimiter` | Reuse placement arithmetic, final sum protection, and slicing tests. Current placement is per Voice. ListenerSchedule is evaluated per sample, contrary to Fable's per block description. Global listener replacement is not independent emitter tracking. |
| R6 | `adapters/web/src/game-audio.ts` `GameAudio`, `RealtimeDevice`; `worklet.ts` `AudiofaceProcessor`; `packages/contract/src/bus.ts` `HostMessage`, `WorkletMessage` | Reuse device adaptation, actual sample rate, retry, and correlated refusal vocabulary. Add acknowledged lifecycle, generations, cancellation, and independent emitter routing before persistent handles. Rebuild cleanup alone does not prove stale async work rejection. |
| R7 | `packages/control/src/audition.ts` `auditionCommands`, `nullVerdict`; `certify.ts` `certifyPack`; `packages/measure/src/fingerprint.ts` `measureAcousticFingerprint`; `adapters/web/src/differential.ts` `nullTest`; `test/worklet-null.test.mjs` | Reuse signal measurement and host parity fixtures. Audition currently drives StampedBus directly; the Node null test drives BusHost without a browser. Fingerprint tolerances describe reference take variation. Cross browser error bounds remain unproven. Native capture needs a new adapter. |
| R8 | `scripts/verify-structure.mjs` `ALLOWED_EDGES`; engine `test-support/voice.mjs` `testVoice`, `testLayer`; `package.json` scripts | Reuse dependency guards and fixtures. `adapters/web/src/bench.ts` `mountBench` edits sounds and provides no profiler. Searches found no program compiler, asset decoder/cache, resource reservation ledger, state migration, cancellation protocol, WASM backend, or native spatial/reverb implementation. |

Absent capability searches: `rg -n 'compile|budget|reservation|cancel|migrat|stateCodec|SharedArrayBuffer|WebAssembly|PannerNode|ConvolverNode|performance.now|outputLatency|renderSizeHint' packages adapters test scripts apps`, plus filename searches for compile, schedule, budget, profile, WASM, and native source extensions. Matches included comments and mute automation; the listed mechanisms remain absent.

A second case insensitive search covered `decodeAudioData|AudioBufferSourceNode|asset(cache|store|loader)?|WebAssembly|SharedArrayBuffer|new Worker|stateCodec|migrat|cancel|reservation|program|topolog` in those same directories. Sibling filenames in table rows share the preceding directory.

## Quality map

| ID | Evidence and consequence |
| --- | --- |
| Q1 | `MasterBus.start` commits `VoicePool.start` before constructing VoiceRenderer. An isolated Node probe used a validated 12 kHz tone with +48 semitone pitch envelope. `auditionPack` produced a Voice; host receipt refused the combined pitch, then the next render threw `no signal path`. `packages/control/src/event-voice.ts` `eventVoice` checks lifetime only. Joint validation and DSP preparation must precede membership and victim mutation. |
| Q2 | `MasterBus.fade` retains renderers outside VoicePool capacity. A 100 start interface burst at frame zero left 24 active and 76 fading renderers, verified by readonly inspection. `CommandQueue.receive` has unbounded storage; `drain` applies every due entry and shifts the array. `createBusHost` also has an unbounded preorigin waiting list. Bound resident state, message bytes, installation work, event count, and pending program overlap separately. |
| Q3 | `packages/engine/src/command-queue.ts` `renderPart`, `MasterBus.mix`, and `VoiceRenderer.renderBlock` allocate subarray views. A start at frame 64 produced six views during one 128 frame host render. The existing zero view host test renders no voices and no commands. `StampedBus.report` and host replies also allocate. A zero allocation claim requires checking the entire active path. |
| Q4 | `StampedBus.listener` replaces placement globally. `RealtimeDevice.connect` exposes only `outputChannelCount: [2]`. `GameAudio.receive` expires correlation after two reports and has no generation field; `RealtimeDevice.use` runs callbacks against captured opening promises. Reuse requires explicit terminal acknowledgements and generation checks for deferred commands and rebuilds. Cancellation, Sound disposal, and state transfer remain unimplemented. |
| Q5 | `packages/patch/src/patch-recipe.ts` redeclares `Waveform`, already derived from `WAVEFORMS` in contract `source.ts`. Engine `source-generator.ts` and `layer-filter.ts` duplicate positive envelope peak and nonnegative frame validation with differing diagnostic labels. Consolidate shared predicates while retaining module joint constraints. Two queue owners reuse one class, so this is duplicated scheduling ownership rather than copied implementation. |
| Q6 | `packages/contract/src/patch.ts` `EnvelopeSegment` is carried through schema, editing, and manifest projection, but `bindLayer` never sends it to DSP. Remove this authored placeholder with its callers. Closed source/processor switches still implement live behavior; retire them only with their replacement. |
| Q7 | OXC AST inspection of all 182 tracked JS/TS files found no file over 700 lines and no function over 150 lines. Largest file: `scripts/verify-structure.mjs`, 605 lines. No sizing refactor is justified now. |

## Recommended dispositions

| Findings | Disposition and reason |
| --- | --- |
| R1, R2, R3, R7, R8 | Reuse the named algorithms, metadata, fixtures, and guards within their stated limits. |
| R4, Q1, Q2, Q3 | Refactor first, before claiming a bounded runtime prototype. Preserve queue timing tests. |
| R5, Q4 spatial routing | Deviate with reason: preserve independent emitter signals before spatialization. |
| R6, Q4 lifecycle | Refactor during the handle/transition probe, with generation and cancellation tests. |
| Q5, Q6 | Refactor during module/composition replacement; remove duplicated or unconsumed declarations with callers. |
| Q7 | Defer with reason: no size violation exists. |

## Smallest discriminating probes

1. **Admission and scene:** reproduce Q1 to Q3, then prove atomic refusal, bounded queues/fades, reserved release capacity, and complete reclamation. Two moving sources compare custom placement with independent native panners and one shared return. A WASM mixer alone cannot represent whole program performance; compare one identical signal path including copies and setup.
2. **Held edit:** one oscillator, cutoff modulation, and delay. Compare compatible state transfer with aligned crossfade through rapid superseding edits, delay growth, undo, and release. Track phase, audible latency, discontinuities, and peak resident bytes. Refuse when overlap cannot fit while preserving accepted playback. Defer external feedback until its minimum delay and shutdown rule are specified.
3. **Nested replay:** two placements, one explicit shared bus, recorded seeds/commands, and device rebuild. Compare a nested schedule with its equivalently ordered flat version. Assert state isolation, explicit scope crossings, stale command refusal, and identical same backend replay.

Measure compilation, installation, kernel time, total rendering thread work, queue/byte peaks, and captured output separately. Compare maximum and p99.9 work with actual quantum duration; record browser, device, rate, cadence, and event trace. Percentiles and device frame gaps alone cannot prove absence of dropouts. No runtime benchmark ran here.

## Product questions and evidence gate

1. Which devices, browsers, and workload define acceptance? Local probes proceed; a shipping performance verdict remains blocked.
2. Must structural edits immediately affect sustained notes? Reversible assumption: explicit pending state plus bounded transition, never silent replacement failure.
3. Must initial release run third party code? Reversible assumption: curated kernels; arbitrary code invalidates static execution cost trust.

Blockers: **1**, the acceptance profile, affecting shipping verdicts only. Probe design can proceed under the stated assumptions.

Verification: proposal digests matched; three isolated behavioral checks ran through source imports on Node 24.20.0. Seven focused existing tests passed for queue refusal, empty host views, filter/echo chaining, and renderer/bus slicing. No build, full suite, or browser run. Artifact schema, source references, report/digest agreement, word limits, and clean baseline were checked. Only the assigned report and digest were written.

Rerun the focused tests from the repository root:

```sh
node --test --test-name-pattern='one call is the same render|filters chain in order|two echoes chain|moving listener is sampled|queued command refusal|normal host quantum' packages/engine/test/master-bus.test.mjs packages/engine/test/voice-renderer.test.mjs packages/engine/test/layer-filter.test.mjs packages/engine/test/layer-echo.test.mjs packages/control/test/bus-host.test.mjs
```
