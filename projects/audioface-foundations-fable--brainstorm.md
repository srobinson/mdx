---
title: Audioface foundations brainstorm, Fable
type: projects
tags: [audioface, architecture, foundations, brainstorm, data-model, composition, studio, game-audio]
summary: Independent first principles brainstorm for the Audioface foundation, comparing three architectural shapes and recommending a compiled composition model with Studio and game parity.
status: draft
created: 2026-09-05
updated: 2026-09-05
project: audioface-next
related: [audioface-phase2-data-runtime-design, audioface-astra-phase2-synthesis, audioface-astra-initial-review, sound-runtime-identity-audioface, audioface-fable--plugin-contract-review]
confidence: medium
---

# Audioface foundations brainstorm, Fable

Baseline `10ba9fc16cea55271c6d428c8fe64c8df0b9c354`, tree clean. Labels: **fact**, **recommendation**, **assumption**, **measure**.

## From the vision, before the code

The Studio composes sounds from bricks and hears every edit at once. The game instantiates the same sounds by the hundred under a deadline. The inspiration images agree on what a brick is: a rack with per slot mix, parameters showing their modulators, a matrix of curves and LFOs, macros, tempo sync, presets, undo. Each is a data model statement. So the foundation is a **composition**: a document of placements, links and modulations that nests, exposes parameters and ports, and is instantiated many times. The question is whether the document is also the running object.

## Three shapes

| | A. Document, program, instance | B. Live object graph | C. Closed recipe (current code) |
| --- | --- | --- | --- |
| Authoring | Composition edited as data, revisioned | Nodes created and connected in place | Fixed rack per layer, flat address map |
| Runtime | Compiler flattens a Sound into an ordered program; instances allocate against it | The graph is the runtime; edits mutate live nodes | `Patch` resolves to `Voice` |
| Live edit | Parameters are commands; structure swaps the program | Immediate, in the audio realm | Rebuild the voice |
| Feedback, ordering | Decided at compile, refused or delayed explicitly | Discovered at run, implicit delay | Not expressible |
| Lego expressiveness | Nesting flattens to one program | Native | None |

**Recommendation: A.** Only A knows a Sound's cost, ordering and memory before the audio realm allocates, and makes a nested rack free at run time. B is the right Studio feel; A reaches it with parameter edits as commands and structural edits as a program swap.

**Falsifiers for A.** (1) A structural edit during playback cannot be made inaudible by program swap with state carry and drain only feels dead; B then wins for the Studio. (2) Compile time exceeds what a gesture hides; **measure** in probe 2. (3) Flattening changes summation order so a nested composition and its hand flattened twin differ; the compiler must then define order (probe 3).

**Challenging the first answer.** Astra's design (`design/audioface-phase2-data-runtime-design.md`) is shape A applied to the closed chain: authored `Patch`, cloneable prepared plan, engine private instances, pinned revision, explicit handle states. The vision changes the authored unit. A layer is privileged in `packages/contract/src/patch.ts` `PatchLayer` and `packages/contract/src/voice.ts` `VoiceLayer`, and its stage order is fixed in `packages/engine/src/voice-renderer.ts` `VoiceRenderer`. In a composition a layer is a voice scoped sub composition and the amplitude envelope is a modulator brick. The second change is references. Astra chose event owned patches without references because nothing asked for shared edits; a Lego Studio's reusable racks do, even if v1 copies.

## 1. Domain and data model

**Definition** (fact of the plan). Engine code with typed ports, parameters, scope capability, state codec, resources, seed needs. One module, one catalog entry.

**Composition** (recommendation). A schema version, an origin id, a revision and four collections: placements (a definition or nested composition, with version, local values and scope), links (port to port), modulations (control output to a parameter with depth and curve; `Connection` in `patch.ts` is this with fewer sources) and exposures (parameters and ports lifted to the surface). A **Sound** is the composition an event binds to; it alone splits voice from sound scope and declares voicing.

**References versus copies.** Placements reference definitions by id and version. Nested compositions embed by value in v1 and carry their origin id and revision, so links can arrive without a schema break. Propagation is product question 1.

**Revisions.** Monotonic per composition, the undo cursor and the program pin, as Astra proposed.

**Assets.** Declared by a placement as content hash and role, decoded on the control side before preparation.

**Parameters, modulation, events.** A parameter has an authored value, an optional `Pack.character` override, trigger fields (velocity, variation, pitch) and modulation summed per block. An effective value exists only for a named context. Events are timestamped messages on event ports.

**Time.** Frames are the unit and every brick reads its own elapsed clock, the discipline in `packages/engine/src/layer-stage.ts`. Musical time is a transport brick publishing tempo phase as a control output.

**Spatial identity.** `EmitterId` stays a game identity. Listener and emitter transforms are runtime inputs sampled per block, `ListenerSchedule` in `packages/engine/src/stereo-image.ts` generalised to a transform pair. Distance and image become sound scoped bricks, not fixed stages in `MasterBus`.

**Runtime state, lifecycle.** A SoundInstance pins a program and owns sound scoped state and voicing history; a Voice owns one trigger's state. Retain Astra's lifecycle table, tails by declaration, no silence detection (`packages/engine/src/voice-pool.ts` `VoicePool.retire`).

**Persistence, undo.** Compositions persist as JSON; programs are derived. Undo is an edit log with inverses over `ControlEdit` and `packControlSurface`. Certification records composition hash and revision, closing the provenance gap in `packages/contract/src/certification.ts`.

**Game delivery boundary.** A pack is domain bindings, compositions, assets and a catalog pin; the game API sees exposures and events only.

**Foundation now:** definition, composition, scope rule, revision pin, program shape, lifecycle, seed tree, budgets, edit log. **Can wait:** link propagation, presets, transport beyond tempo phase, scene scope, granular bricks, streaming.

## 2. Flexibility

Connection rules precise enough to compile (recommendation):

- Audio to audio requires equal channel layout; changing layout is an explicit brick.
- Control reaches a parameter only through a modulation entry; rate changes go through explicit bricks.
- Voice outputs reach sound scope only through the Sound's mixdown port; sound outputs never feed voice inputs.
- A cycle is legal only through a declared feedback brick owning one block of delay and declaring that tail. Every other cycle is refused at compile with the placements named.

A placement inherits its parent's scope; only the Sound splits. Shared effects across Sounds need a third scope, scene, reserved now. The instrument surface projects exposures plus provenance (authored, character, modulated by, derived), half of which `packages/control/src/manifest.ts` does today; rack and matrix views read the same document.

## 3. Execution

Facts from primary documentation. The render quantum defaults to 128 frames and Web Audio API 1.1 adds `renderSizeHint` with a `hardware` category, so a kernel must not assume 128 (specification section 1.2.1; MDN `AudioWorkletProcessor.process`). `SharedArrayBuffer` needs a cross origin isolated context with COOP and COEP headers, and `postMessage` throws otherwise (MDN). Hosting pages may lack those headers, so `MessagePort` is the baseline and a shared ring an optional optimisation. Chrome's worklet guidance names the copy between the Wasm heap and audio arrays as a cost.

| Concern | Where | Note |
| --- | --- | --- |
| Audio callback | `process`, one quantum | Program interpretation only; no allocation, no lookup by string |
| Other audio realm work | Port receipt in the worklet global scope | Same thread as the callback; preparation on receipt spends deadline time and must be measured |
| Preparation, scheduling | Control side; `CommandQueue` frame stamps | Validate, compile, reserve budget; retain the queue |
| Memory | Preallocated per program at admission | Program declares bytes; a host budget refuses before mutation |
| Bounded admission | `VoicePool` floors plus per Sound limits | The pool stays the only steal authority |
| Overload | Device frame gaps, render time per quantum | Degrade by class and Sound virtualisation, never by signal level |
| Telemetry | Report cadence in `createBusHost` | Add render time, missed deadlines, `outputLatency` |

JIT compiled Float32 loops are not obviously slower than Wasm; **measure**. Wasm buys fixed memory, no GC in the audio realm, SIMD and bit equal transcendentals across engines, at the price of a copy per quantum and a second toolchain. Native nodes buy convolution and HRTF but nothing a gate can read. **Recommendation:** the compiler emits a program a JS interpreter runs today; a Wasm interpreter of the same program is probe 1's variant, not a rewrite. Native nodes stay after the master sum until probe 1 says otherwise.

## 4. Studio and game parity

One compiler, one host. `createBusHost` in `packages/control/src/bus-host.ts` runs offline in Node and inside the worklet, with equality held by `test/worklet-null.test.mjs`. Parameter edits are commands smoothed per block; structural edits produce a new program the host swaps. Foundation policy is Astra's drain: new voices take the new program, old voices finish. State carry, where surviving placements keep filter memory and delay lines, is probe 2.

Packaged delivery ships compositions and assets with the catalog pin; the game compiles at load with the same compiler. Reproducibility, honestly: bit equality holds offline within one build on one JS engine, because `Math` transcendentals differ across engines and `packages/engine/src/transcendental.ts` exists to replace them. Across browsers the promise is fingerprint tolerance through `measureAcousticFingerprint` and `ACOUSTIC_TOLERANCES` in `packages/measure/src/fingerprint.ts`.

## 5. Three executable probes

**Probe 1, busy spatial scene.** Hypothesis: a JS program interpreter renders S sounds with V voices, each with distance and image bricks and one sound chain, inside the quantum period at 48 kHz on a mid range laptop. Measure: render time per quantum at p50 and p99, device frame gaps, GC pauses. Falsifier: p99 above the quantum period at the owner's chosen S and V. Smallest scope: extend `adapters/web/src/bench.ts` with synthetic compositions and a Wasm mixer variant.

**Probe 2, sustained modulated instrument with edits during playback.** Hypothesis: parameter commands are click free, and a structural swap with state carry is null against a continuous render for unchanged placements. Measure: discontinuity at the swap frame, edit to audible latency. Falsifier: delay and biquad state cannot be carried exactly; then drain is the only policy. Smallest scope: one held Sound, an LFO on cutoff, a filter brick inserted and removed mid note, one feedback cycle, offline.

**Probe 3, reusable composition through a small game API.** Hypothesis: a rack exposing three macros and one event port instantiates through create, set and trigger calls, serves two events with different defaults, and its flattened program matches a hand flattened twin. Measure: compile time and sample equality nested versus flat. Falsifier: summation order differs. Smallest scope: control and engine in Node.

## 6. Reopen list

| Disposition | Item | Reason |
| --- | --- | --- |
| Retain | `rootSeed`, `childSeed`, `drawAt` in `packages/contract/src/seed.ts` | Label keyed streams; add the sound scoped parent from issue 4 |
| Retain | `beginVoice`, `voiceHasEnded` in `packages/engine/src/voice-lifetime.ts`; `VoicePool.start`, `retire` | Declared lifetime, class floors, deterministic steal |
| Retain | `MasterBus.render` and `VoiceRenderer.render` slicing invariance; `CommandQueue`; `createBusHost`; `nullVerdict`; `ALLOWED_EDGES` in `scripts/verify-structure.mjs`; refusal correlation in `GameAudio` | Parity, structure, honesty |
| Retain | DSP in `filtered`, `echoed`, `DistanceField`, `StereoImage`, `MasterLimiter` | Arithmetic unchanged, held by fingerprints |
| Challenge | `PatchLayer`, `VoiceLayer`, fixed order in `VoiceRenderer` | Becomes a voice scoped composition |
| Challenge | `Patch.parameters` flat map; `ControlTarget` by `PatchId` | Values move to placements (Astra agrees); targets become composition references |
| Challenge | `Connection`, `ConnectionCurve` in `patch.ts` | Seed of the matrix; widen sources to control outputs |
| Challenge | Event owned `Patch` without references; `LISTENER_FIELDS` | Origin id and version; transforms in, placement bricks out |
| Discard | `EnvelopeSegment`, `envelopeSegments` | No behaviour |
| Discard | `LAYER_SOURCE_TYPES`, `LAYER_PROCESSOR_TYPES`, `firstFilterProcessor`; `PatchRecipe` dispatch in `buildPatch` | Closed unions issue 4 retires; a composition builder replaces the recipe |

Reuse candidates for Scout: `packages/contract/src/ids.ts` and `address.ts`; `parseControlEdit` and the edit path; `ParameterDefinition` and unit conversions under `packages/patch/src/registry`; measure, certify, host and adapters whole. Intentional sonic changes are the envelope as a modulator and placement as bricks; any other drift against fingerprints is a regression.

## 7. Unknowns and product questions

Biggest unknowns: the render budget on target devices; whether Wasm pays for its copy; cross origin isolation in hosting contexts; exact state carry; audio rate modulation cost; asset memory per Sound.

1. **Shared racks: reference or copy?** Default: reference by versioned origin; copies pin a version; propagation is an explicit upgrade, never silent.
2. **Who compiles for the game?** Default: the game, at load, with the same compiler; precompiled export only if probe 3 shows start up cost.
3. **Is cross browser bit equality a promise?** Default: no. Bit equality within a build offline; fingerprint tolerance across platforms.

## Decision table for the next phase

| Decision | Recommendation | Owner | Evidence |
| --- | --- | --- | --- |
| Shape | A, with program swap | Lead | Probes 2 and 3 |
| Authored unit | Composition with placements, links, modulations, exposures; layer becomes a sub composition; feedback only through a declared brick | Lead | Scout reuse map of `packages/patch` |
| Execution seam | JS program interpreter; Wasm as probe variant; native after the master sum; no shared memory dependency | Lead | Probe 1, hosting survey |
| Live structural edit | Drain now; state carry if probe 2 passes | Lead | Probe 2 |
| Astra lifecycle, budget model, slices 4 to 6 | Retain the first two; resequence the slices around bricks in a composition rather than plugins in layer and sound arrays | Lead | Scout dispositions |
| Product questions 1 to 3 | Defaults above | Stuart | Product judgment |
