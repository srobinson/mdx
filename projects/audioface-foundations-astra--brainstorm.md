---
title: Audioface foundations, Astra brainstorm
type: projects
tags: [audioface, foundations, architecture, ownership, realtime, brainstorm]
summary: Independent architectural comparison, ownership model, bounded execution proposal, and three falsifiable probes for Sound Studio and game delivery.
status: draft
created: 2026-09-05
updated: 2026-09-05
project: audioface-next
confidence: speculative
source: https://github.com/littleorgans/audioface/issues/4
related: [audioface-astra-initial-review, audioface-phase2-data-runtime-design, audioface-astra-phase2-synthesis, sound-runtime-identity-audioface]
---

# Audioface foundations

## Starting from the experience

Product facts: exceptional browser game audio performance, flexible composition, and an outstanding Sound Studio are required. Device budgets, browser floor, plugin distribution, and shared edit propagation remain unspecified.

I inspected all seven supplied Desktop images. `16.56.31` emphasizes signal progression through processing. `12.36.54` pairs an effect rack with an editable modulation curve. `12.38.17` and `12.34.04` combine waveforms, grains, musical controls, and animated macros. `12.44.44`, `12.43.47`, and `12.43.28` isolate macro motion, timeline alignment, and pitch constraints.

Recommendation: make the playable instrument the primary view. A waveform, macro, or modulation gesture edits stable musical objects. Rack and graph views expose the same composition. Persist presentation separately from executable meaning. Render meters from bounded snapshots of actual playback, without feeding display cadence into modulation.

## Architectural alternatives

My initial hypothesis was an immutable authored document compiled into an execution plan, with separately owned running state.

| Shape | Strength | Cost and failure condition |
| --- | --- | --- |
| Native graph with custom worklet islands | Browser nodes own routing, automation, convolution, and spatial processing. Direct graph edits fit audition. | Crossings, native state opacity, and backend differences complicate reproducibility and resource accounting. Loses if required modulation or edit continuity cannot be expressed. |
| Compiled plan with explicit instances | Compiler resolves references, schedules operations, assigns buffers, and accounts for replicated state before admission. Studio and game share execution. | Compiler and installation add complexity. Loses if loading or edits cannot meet responsiveness and audio budgets. |

Prefer compiled plans, initially executing existing JavaScript DSP. Compare selective WASM kernels and native spatial processing experimentally. Compilation here means lowering data into an ordered schedule, not generating arbitrary code. Do not build several complete backends.

Challenge to my first answer: native HRTF and convolution could outperform custom equivalents while providing acceptable fidelity. If the probes show that native graphs meet every required semantic and budget with less machinery, choose that shape. Ownership and revision contracts survive either choice.

## Ownership comes before plugin breadth

Proposed foundational objects have distinct owners:

| Object | Owner and semantics |
| --- | --- |
| Definition revision | Document store owns immutable composition data, stable placement identities, local parameter values, connections, and exposed controls. |
| Reference | Placement pins a definition revision plus explicit overrides. Reuse shares immutable data; each placement gets independent runtime state. |
| Asset | Asset store owns content identified by hash and decoded variants identified by decode recipe, channels, and sample rate. Programs pin assets until retirement. |
| Program | Compiler owns resolved definitions, module versions, asset dependencies, execution order, buffer layout, and resource bounds. Immutable and cacheable. |
| Sound instance | Runtime owns a program binding, voicing history, shared processors, and active Voices. Control exposes an opaque handle. |
| Voice | Sound owns one note or trigger execution, including its local DSP and release state. Grain pools remain bounded internals of granular modules. |
| Emitter and mix bus | Game adapter owns emitter transforms. Runtime owns explicit shared effect buses and their lifetimes. Neither identity is inferred from event names. |

Copying creates an independent definition lineage. Referencing pins existing content. Updating references is an explicit document transaction by default. Matching labels, IDs, or object aliases never imply sharing. An event binds a definition reference to a game meaning; event vocabulary is optional for direct Studio audition.

Undo restores document revisions and references, including deleted objects' original identities. Fresh insertion gets fresh identity. Deletion removes owned values and incident connections atomically. Persist documents, dependency revisions, and asset metadata. Runtime checkpoints are separate, optional capabilities. Undo changes the audition target through the normal live update protocol; it does not rewind elapsed sound.

Retained Sounds keep logical history until disposal. Automatic effects use the same machinery with automatic retirement. Disposal closes admission, cancels scheduled starts, releases Voices, then drains declared tails. Infinite feedback requires explicit lifetime and a bounded shutdown fade. Silence alone never retires state. Logical handles and resident DSP have separate budgets. Device replacement invalidates execution generations unless an explicit restore capability succeeds.

## Composition needs execution semantics

Connections declare audio, control, or event type, channel layout, units, rate, and scope. Rate and channel conversions are explicit. Fan in requires a declared mixer. Nested compositions expose ports and macros and expand into stable instance paths. Recursive definitions are rejected. Scope belongs to placement within supported execution contexts, so a delay can run per Voice, per Sound, or on a shared bus without three implementations.

Shared effects are explicit bus references, never accidental sharing of a plugin object. Crossing from Voice to Sound needs aggregation; Sound controls reaching Voices need declared broadcast semantics. Per grain state stays within the granular module unless a probe establishes a broader need.

Recommend normalized modulation mapping: authored base, optional runtime override, automation, then ordered modulation contributions, followed by declared limiting and smoothing. Expose authored, overridden, and effective values with instance and frame context. Structural and resource changing parameters require preparation. Continuous parameters declare scalar or per sample evaluation.

Use absolute integer audio frames and event offsets. Break equal frame ties by recorded sequence. Represent musical positions separately and compile through a versioned tempo map with an explicit rounding rule. Define free running versus retriggered modulation phase now. A full music arrangement system can wait.

Initially reject external feedback cycles. Later accept only explicit delay boundaries with a documented minimum delay, bounded storage, and stability policy. Never insert a hidden block delay. Internal delay feedback remains available through a bounded kernel. Parallel latency compensation and composed tail bounds belong to compilation; changing either requires a transition policy.

## Bounded audio execution

The worklet's message tasks participate in rendering thread work. Moving construction outside `process()` does not remove its deadline impact. The [Web Audio rendering model](https://www.w3.org/TR/webaudio-1.1/#rendering-loop) specifies this sequencing; version 1.1 is a draft, not a browser support guarantee.

Separate preparation and activation:

1. A worker validates documents, resolves dependencies, compiles schedules, and prepares asset data through supported decoding facilities. No runtime function objects cross realms.
2. The host reserves voices, grains, buffers, queued events, installation work, and transition overlap. Flow control caps message count and bytes before sending.
3. Audio installation uses preallocated slots and bounded initialization steps. Module loading and unsplittable construction happen before playback. A module needing unbounded live construction cannot promise seamless edits.
4. Activation checks generation and current capacity, then commits atomically at a frame. Failure preserves active membership and refunds reservations.

Rendering performs bounded kernel loops, scheduled events, and mixing. No waits, memory growth, graph discovery, or asset work. Limits cover event bursts, subblock splits, fading victims, retained tails, and pending programs. Reserve release and disposal capacity. Coalesce replaceable transform updates before admission. Refuse excess starts with correlated results; reduce optional telemetry first. Virtualization requires explicit phase and resume semantics.

JavaScript retains existing algorithms with low integration cost. WASM offers explicit memory and reusable DSP libraries, but crossings, copies, initialization, and kernel size can erase gains. Native nodes reduce owned DSP code but still require measured graph setup and transition costs. A worker producing audio ahead introduces buffering latency and underrun policy. [Chrome's design patterns](https://developer.chrome.com/blog/audio-worklet-design-pattern) describe these tradeoffs and warn that buffering does not extend a callback's execution budget.

Measure rendering thread work, including handlers, separately from kernel time. Compare maximum and p99.9 duration with `quantumFrames / sampleRate`. Use browser traces and output capture, plus bounded counters for lateness, refusals, queue occupancy, memory reservations, and telemetry loss. A zero allocation `process()` measurement alone is insufficient. Trusted kernel resource declarations require measurement; arbitrary JavaScript or WASM cannot be made deadline safe merely by declaring a cost.

## Audition and delivery share semantics

Studio auditions the packaged program through the game runtime. Parameter gestures schedule ramps against the audio clock. Structural edits prepare a new program, then activate at a frame using bounded state transfer or a latency aligned crossfade. Reserve both programs and their tails. If capacity is unavailable, keep the accepted version sounding and report the pending edit.

Preserve independent emitter signals until spatialization. A single stereo master sum cannot subsequently receive independent per emitter HRTF. Probe separate outputs into native panners against custom spatial processing. Put final output protection after the actual final mix; certification names the signal it measures.

Delivery includes program digest, exact module and asset identities, exposed controls, capabilities, and capacity requirements. Games load, instantiate, trigger, automate, release, and dispose through a small API. Record command ordering, seeds, and effective frames for replay. Exact samples require the same backend, numerical operations, asset decoding, and execution policy. Across platforms or backends, test declared timing and signal tolerances plus listening quality. Intentional sonic changes receive new reference renders.

## Three proposed executable probes

These are proposed experiments. Run each load for 60 seconds after warmup, doubling instance count from one until failure. Record device, browser, sample rate, quantum, and command trace. This sweep does not establish shipping capacity.

| Probe | Smallest useful prototype and hypothesis | Measurements and falsifier |
| --- | --- | --- |
| Busy spatial game | One Three.js scene, two moving emitter paths, one procedural sound, one sample, and a shared reverb. Increase simultaneous instances and trigger bursts. Compare compiled custom spatial output with native panner outputs. Hypothesis: independent movement survives bounded admission. | Trace callback plus handler time, captured dropouts, trigger lateness, transform traffic, CPU, and memory. Falsify on state corruption after refusal, lost spatial independence, or failure below the subsequently selected device budget. |
| Sustained modulated instrument | One held instrument with an LFO, curve, two macros, and delay. Edit ramps, tempo, routing, and delay configuration during playback, including undo and rapid superseding edits. Hypothesis: ordinary gestures preserve continuity within bounded resources. | Measure gesture to audible latency, discontinuities against a scheduled reference, phase drift, installation time, overlap bytes, and release completion. Falsify on stuck notes, growing queues, unbounded initialization, or required edits needing an audible restart. |
| Reusable game composition | One nested composition referenced twice, one copy, two independent handles on one emitter, and one explicit shared bus. Export, reload, replay, and rebuild the device. Hypothesis: reference sharing and runtime independence coexist behind a small API. | Check revision hashes, override isolation, replay samples on one backend, stale command refusals, and full reservation recovery. Falsify on unintended edit propagation, aliased DSP, changed pinned playback, or leaked resources. |

## Reopen decisions and commission Scout

Source baseline is `10ba9fc16cea55271c6d428c8fe64c8df0b9c354`, verified clean. Current issues [4](https://github.com/littleorgans/audioface/issues/4), [15](https://github.com/littleorgans/audioface/issues/15), and their linked [5](https://github.com/littleorgans/audioface/issues/5), [6](https://github.com/littleorgans/audioface/issues/6), [7](https://github.com/littleorgans/audioface/issues/7), and [8](https://github.com/littleorgans/audioface/issues/8) were read live.

I challenged the [initial review](audioface-astra-initial-review.md), [prior design](../design/audioface-phase2-data-runtime-design.md), [type sketch](../design/audioface-phase2-contract-sketch.ts), [synthesis](audioface-astra-phase2-synthesis.md), and [Sound identity investigation](../research/sound-runtime-identity-audioface.md) against the expanded brief.

| Disposition | Evidence and next decision |
| --- | --- |
| Retain, provisionally | `scripts/verify-structure.mjs` `ALLOWED_EDGES`: control composes; patch and engine remain independent. Retain one metadata authority from `packages/patch/src/registry/definition.ts` `ParameterDefinition`. |
| U1: challenge fixed chains | `packages/patch/src/voice-binding.ts` `bindLayer` partitions processors into filters and echoes. Prove order, typed connections, scope placement, and nesting before extending the catalog. |
| U2: replace admission and preparation | `packages/engine/src/master-bus.ts` `MasterBus.start` mutates the pool before constructing DSP. `packages/engine/src/command-queue.ts` `CommandQueue.drain` applies scheduled starts during rendering. Decide installation bounds through probes. |
| U3: discard final sum as spatial boundary | `adapters/web/src/game-audio.ts` `RealtimeDevice` creates one stereo output. Issue 6's independent spatialization needs earlier signals. Choose routing and backend from the scene probe. |
| U4: challenge event owned copies | `packages/contract/src/pack.ts` `PackEvents` embeds patches; `packages/control/src/surface.ts` `initialState` keys them by PatchId. Resolve revision ownership and reference semantics before reusable compositions. |
| U5: challenge audition restart and broad lifecycle promises | The prior design's pinned handles and receive time construction do not establish seamless structural edits. Prove transitions before claiming restore, seek, or virtualization. |

Initial reuse candidates include `packages/engine/src/layer-filter.ts` `filtered`, `packages/engine/src/layer-echo.ts` `echoed`, `packages/engine/src/voice-lifetime.ts` `beginVoice`, `packages/contract/src/seed.ts` `childSeed`, and `packages/control/src/bus-host.ts` `createBusHost`. Preserve useful algorithms and `test/worklet-null.test.mjs` behavioral evidence. Full reuse dispositions belong to Scout. Retire replaced unions and dispatch together. Old fingerprints must not dictate the new topology.

## Three product questions

1. Which devices, browsers, and game audio workloads define acceptance? Recommended default: select representative desktop and constrained devices, then measure budgets. No support floor is assumed.
2. Should editing a reusable definition update existing authoring placements automatically? Recommended default: pinned revisions with an explicit update action. Running games remain pinned.
3. Must the first release execute third party plugin code? Recommended default: curated kernels and user compositions; defer arbitrary code distribution.

The five engineering decisions U1 through U5 and these three product choices remain unresolved. Full arrangement, collaboration, arbitrary plugin distribution, and universal state migration can wait. Identity, references, clocks, connection semantics, resource admission, and the live transition boundary cannot.

Verification covers artifact schema, source symbols at the pinned baseline, referenced sources, and repository cleanliness. No runtime implementation or performance proof is claimed.
