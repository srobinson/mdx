---
title: Audioface #4 plugin contract review, Fable
type: review
tags: [audioface, plugin-contract, adversarial-review, phase-2]
status: active
created: 2026-09-04
project: audioface-next
source: littleorgans/audioface#4
---

# Plugin contract review: issue #4 as filed

Reviewed read only from `main` at `10ba9fc`. Working tree clean before and after. Baseline verified first hand: `pnpm run check` green, 270 tests, 270 pass, structure verification passed. Research read in the issue's order; Bespoke, middleware, engine review, synthesis and host seam audit all consulted; WAM 2.0, openDAW and MetaSounds studied for the three open questions.

## Verdict

**I sign off conditional on the following changes:** resolve the package home of a plugin module before slice 1 (finding 1), correct the switch enumeration and the Done-when grep (finding 2), add a control-rate out port to the port table (finding 3, which is also the answer to open question 1), define the sound-level seed parent in the contract (finding 4), and state plainly that slice 4 is a scope change proven by unchanged certification rather than a behaviour-preserving refit (finding 5). Every finding has an exact wording change in the last section. The contract itself, the refit strategy, the throwaway eighth unit proof and the recorded decisions are right and none of them needs reopening.

## Findings

### 1. The DRY goal, the package ownership line and ALLOWED_EDGES are jointly unsatisfiable as filed

The issue promises: "Adding a processor touches one module (its descriptor and `process`) and one registry entry, nothing else" (Done when, bullet 1), with "Contract types ... in `packages/contract`, implementations in `packages/engine`, registry rows in `packages/patch`" (Start here). The enforced edges say `packages/engine` and `packages/patch` may each import only `@audioface/contract` (`scripts/verify-structure.mjs:34-48`). `ParameterDefinition` lives in `packages/patch/src/registry/definition.ts:35`. The transcendental seam is rooted at `packages/engine/src` (`verify-structure.mjs:139-141`), so a `process` that calls `sine` must live in engine or the seam moves.

Consequence: no single module can hold a descriptor typed as `ParameterDefinition` and a `process` the engine renders, while being visible to the registry (patch) for its rows and to the renderer (engine) for its stage. Engine cannot import patch; patch cannot import engine. As filed, "one module" forces either a split (descriptor in patch, process in engine: two modules, the promise broken) or a re-declaration of the rows (the issue's own DRY law broken).

Resolution, recommended: move `ParameterDefinition` and its constructors to contract (it imports only contract types already, `definition.ts:1-13`), house plugin modules in one new leaf package (working name `packages/palette`) whose edge is contract only, and let both engine and patch import it. The transcendental seam root extends to cover it in the same verifier slice the issue already plans. The registry in patch keeps the assembled list, which is the "one registry entry". The alternative, plugin modules in engine with aggregation lifted to control, contradicts "registry rows in `packages/patch`" and blinds validation in patch to the descriptors; do not take it. Either way the issue must name the answer before slice 1, because slice 1 writes these types into their homes.

### 2. The five-place enumeration is wrong in both directions, and the Done-when grep fails on files no slice refits

Run today, the issue's own gate `grep -n 'case "tone"\|case "lowpass"' packages/` returns six sites, not the listed five's remainder:

- `packages/patch/src/voice-binding.ts:112` (listed, place 3)
- `packages/engine/src/source-generator.ts:21` and `layer-filter.ts:136` (listed, place 4)
- `packages/patch/src/patch-resolution.ts:140` — **not listed anywhere in the issue**
- `packages/patch/src/patch-recipe.ts:122,207` — **not listed anywhere in the issue**

`resolvePatchLayer` (`patch-resolution.ts:132-155`) is a genuine per-kind switch: it hand-picks which addresses resolve per source type. It must become descriptor-driven (resolve the definition's `parameterKeys`) or the gate fails and adding a source still touches resolution. `patch-recipe.ts` switches on the recipe builder's own closed union; a new plugin never touches a recipe, so either the recipe is refitted too or the gate is scoped to exclude it, explicitly.

In the other direction, place 5 as listed, "validation and the manifest projection in control", is already definition-driven and switch-free: `patch-validation.ts:229,234` and `control/src/manifest.ts:93,157` iterate `SOURCE_DEFINITIONS`/`PROCESSOR_DEFINITIONS`. Adding a kind touches them only through the registry entry, which is the end state the issue wants. Validation also lives in patch, not control. The refit list should name resolution and the recipe and drop validation.

### 3. The port table cannot express a modulator

The field table declares "Typed ports: audio in and out, control in with rate, event in". There is no control **out**. Open question 1's better branch ("a modulator is a plugin whose only out port is control rate") is unrepresentable against the filed table. Adding `control out with rate` resolves the question and the table together; see the open question 1 answer below.

### 4. The seed namespace is voice-anchored and a sound-scoped plugin has no voice

"Deterministic seed namespace (a child of the voice seed keyed by plugin instance id, as layers are today)" cannot serve a `scope: sound` plugin: it runs once over mixed voices, so no voice seed exists to parent from. The echo refit will not force the answer because the echo draws no randomness, which means the gap survives this phase silently and lands on #5's first stochastic sound-scoped plugin (a reverb's diffusion, a granular bed).

The chain to reuse already exists: `rootSeed` is `childSeed(childSeed(childSeed(SEED_ROOT, packId), eventId), take)` (`packages/contract/src/seed.ts:23-25`). The sound-level parent is the same chain minus the take, extended by the sound instance and the plugin instance id. Define it in contract in slice 1, next to `rootSeed`, so the namespace has two documented parents keyed by `scope`.

### 5. Slice 4 is a scope change, not a behaviour-preserving refit, and the tail moves owners

"Refit the seven" claims every refit is behaviour preserving. Six are. The echo is not, as a semantic matter: today an echo runs per layer, after the envelope and layer gain, before the patch gain, the distance filter and the pan (`voice-renderer.ts:63`, then `master-bus.ts:195-198`). At sound scope it runs after placement, over the mixed stereo bus. Repeats stop being placed and start carrying the mix's placement; an echo on layer A but not layer B is inexpressible. This is invisible in shipping content only because no shipping patch authors an echo (`packs/skirmish/src/patches.ts`, `packs/reference/src/patches.ts`: no delay processor, no echo recipe), so certification-unchanged is the true proof, and the null test holds trivially because it compares the same engine against itself on both paths.

Related: "the voice lifetime already consumes tail (`layerTailFrames`)" is listed under "already deep and must survive unchanged in behaviour", but slice 4 removes echoes from layers, so the echo tail leaves the voice lifetime (`voice-lifetime.ts:87,109`) and must be consumed by the Sound's lifetime instead. That ownership move is correct and should be stated, because it is the first behavioural consequence of the Sound object in open question 2.

### 6. Two smaller points

- "`MasterLimiter` and `VoicePool` names may not leave the engine" is true today by convention (no reference outside engine; both are `export *`ed from `packages/engine/src/index.ts`) but no verifier check holds it. Slice 1 already extends the verifier for kind strings; encode this rule in the same pass or strike the sentence.
- The voicing descriptor's SFX reading includes "cut quietest". The pool's steal deliberately never reads loudness ("never by loudness, because loudness would be the signal deciding control", `master-bus.ts` and the pool comments), and that wall is a recorded strength. No contradiction, because the Sound's priority is content policy above the pool's foundation-owned steal, but the issue should say so in one sentence so the wall visibly survives.

## Open questions, resolved

### Q1. One descriptor; the rate lives on the port; the role is derived

A modulator shares the descriptor. Its distinguishing fact is its port set: control-rate out, no audio out. Prior art, studied for this question: two of three agree and the third is the cautionary counter-model. WAM 2.0 has no modulator class; a modulator is an ordinary plugin whose shared `WamIODescriptor` sets `hasAutomationOutput: true` and emits automation events, which is literally a control-out declaration on one descriptor. MetaSounds has no modulator category either; rate is a pin datatype (`FAudioBuffer` audio-rate versus `float`/`FTrigger` block-rate) on one uniform `FVertexInterface`, so anything with only float or trigger outputs is a de facto modulator. openDAW is the fork: modulators are a separate device category on their own control pointer graph, which means two graphs, two factories and every extension touching both, the five-place cost this issue exists to delete, paid twice. Bespoke's `IModulator.Value(samplesIn)` supplies the read shape (one object sampled at block or sample rate, the reader deciding), and the Bespoke review's borrow 3 already says to pair that read with "an explicit rate on the port, which Bespoke never wrote down".

Concrete types:

```ts
export type PortRate = "control" | "audio";

export type PluginPorts = {
  readonly audioIn: readonly AudioPort[];    // [] for sources and modulators; a key input is one of these, flagged
  readonly audioOut: readonly AudioPort[];
  readonly controlIn: readonly ControlPort[];  // each { id, rate, ... }
  readonly controlOut: readonly ControlPort[]; // modulators; rate on the port
  readonly eventIn: readonly EventPort[];
};

export function pluginRole(ports: PluginPorts): "source" | "processor" | "modulator" {
  if (ports.audioOut.length > 0 && ports.audioIn.length === 0) return "source";
  if (ports.audioOut.length > 0) return "processor";
  return "modulator";
}
```

Apply the issue's own deletion test to the stored `role` field: it is derivable from the ports, so either derive it (`pluginRole`) or store it and integrity-check it against the ports the way the registry already checks rows (`registry/integrity.ts`). Deriving is smaller. The field table's first row then reads "Stable id, semantic version, `scope` (voice, sound)" and role becomes a contract function, which also makes an illegal role and port combination unrepresentable, the exact upgrade the Bespoke review's borrow 2 asked for over debug asserts.

### Q2. A Sound instance in the engine, owned by the master bus, between voice placement and the master sum

Today there is no Sound in the engine (verified: no such symbol in `packages/engine/src` or `packages/contract/src`); voices place themselves and sum straight into the master (`master-bus.ts:195-205`). Three forces pick the same answer:

- Portamento's "last pitch held as instance state" needs a home that outlives any voice. That home and the sound-scoped chain state are the same lifetime.
- Finding 5's tail move needs an owner with a lifetime: a Sound is sounding while any of its voices sounds or its chain's tail is above the floor, which is `layerTailFrames` generalised (`echo.ts:27-41` is the precedent, reused not rebuilt).
- `MasterBus` at 235 lines already owns the pool, steal fades, the mix and the limiter. Maps of chain state, portamento pitch and sound seeds keyed by SoundId would smear a transient lifetime into a permanent module; the refactoring threshold and the deletion test both point at an object.

This matches openDAW's shape exactly: the chain owner is an `AudioUnitBinding` per audio unit holding the ordered device collections, voice pools nest inside device state inside that binding, and `voicing-mode` (monophonic or polyphonic) is declared on the instrument device itself, which is this issue's "voicing is a property of the Sound" arrived at independently. FMOD's event instance owning its effect state is the middleware form of the same answer. MetaSounds is the opposite pole (a whole graph instantiated per voice, nothing chain-shared) and shows what refusing a Sound object costs: sound-scoped state has nowhere to live. Concrete:

```ts
// contract
export type SoundId = Brand<string, "SoundId">;
export type Voicing = {
  readonly mode: "mono" | "poly";
  readonly maxVoices: number | null;        // above the pool's class floors, never instead of them
  readonly priority: "last" | "lowest" | "highest";
  readonly retrigger: "legato" | "retrigger" | "hard";
  readonly portamentoMs: number;            // 0 is none; last pitch is instance state
};
// Voice gains: readonly soundId: SoundId;

// engine, private to the bus
type SoundInstance = {
  readonly id: SoundId;
  readonly chain: readonly PluginRender[];  // sound scoped, built once
  readonly bus: StereoBlock;                // voices place into it; chain works it; master sums it
  readonly seed: Seed;                      // the sound-level parent from finding 4
  lastPitch: number | null;                 // portamento
  tailFrames: number;                       // max chain tail, consumed by the sound's lifetime
};
```

Control mints `SoundId` per event instance; `MasterBus` creates the instance when the first voice carrying it starts and retires it when the last voice retires and the tail elapses, the same shape as `fading` today. Defaults (`poly`, `maxVoices: null`, let the pool steal) reproduce current behaviour, as the issue requires. The bus stays the registry and the clock; the Sound owns the state. This is the issue's option "a new Sound object between the voice and the bus", with the bus as its owner, and it is the option to file.

### Q3. `LayerStage` is not the render definition; adopt the channel-planar block now, because slice 4 already needs it

The issue defers the richer block to #5's compressor. It cannot wait that long: the sound-scoped echo in **this phase** processes the post-placement stereo bus, and `LayerStage` carries one mono `Float32Array` (`layer-stage.ts:12-14`). A mono-only render definition cannot carry the seven plus the echo through slice 4 without a second render shape, which is exactly the parallel-implementation smell the issue bans.

Concrete, the smallest shape that carries both scopes and #5's key input without breaking the seven again:

```ts
export type RenderBlock = {
  // Planar, length fixed by the descriptor's channel layout: [mono] at voice scope,
  // [left, right] at sound scope. Same buffers every call; nothing allocates.
  readonly channels: readonly [Float32Array, ...Float32Array[]];
  // Present exactly when the descriptor declares a key input; null through Phase 2.
  readonly key: readonly Float32Array[] | null;
};

export type PluginRender = {
  readonly process: (block: RenderBlock, elapsed: number) => void;
};
```

`elapsed` keeps the layer's (or sound's) own clock, so slice invariance and the "same frames however the render is sliced" property transfer verbatim from `layer-stage.ts`'s contract comment. `SourceGenerator` and `LayerStage` collapse into this one type, which the host seam audit's smaller note already scheduled for this phase; the fills-versus-works-in-place distinction becomes a descriptor fact (a source role writes every sample), so the mono fast path pays no zeroing it does not pay today. On declaring extra inputs, prior art splits three ways: WAM 2.0 declares nothing (host graph wiring), openDAW binds side chains dynamically at init (`bind_sidechain(path)` returning a port id resolved at render), MetaSounds fixes the vertex interface at class declaration time with typed pins. Take the MetaSounds position: descriptor-fixed, because a certification gate can only measure a graph whose shape was declared, and a dynamically bound input is a graph the descriptor never admitted to. WAM 2.0's `process(inputs, outputs, parameters)` is the planar shape `RenderBlock.channels` reduces to. One more prior-art fact worth having in the issue: none of the three declares tail (only WAM 2.0 even declares latency, via `getCompensationDelay`); the tail-in-frames field is ahead of all three, and its justification is internal, `VoiceEcho.tailFrames` carried "so nothing downstream derives it a second way".

One consequence to name in the issue: dissolving `VoiceSource`/`VoiceFilter`/`VoiceEcho` into descriptor-registered plugins retires the `assertNever` exhaustiveness and the "narrowed by search" enum-to-union seam (`voice-binding.ts:247-260`) that the codebase's two-answers pattern leans on. The replacement safety is descriptor completeness at load (validation already refuses unknown kinds through the registry lookups) plus the slice 1 verifier rule that a kind string appears only in its module. That trade is right; it should be written down, because it is the one place this phase spends a compile-time guarantee to buy openness.

## Field table audit

| Field | Verdict |
|---|---|
| id, version, role, scope | Sound, except role: derive from ports (Q1). |
| Channel layouts | Sound; consumed immediately by Q3's `channels`. |
| Typed ports | **Incomplete: no control out** (finding 3). |
| Parameter descriptors | Right reuse; `ParameterResolutionConversion` (`definition.ts:16`) plus `units.ts` already hold every conversion `bindVoice` performs (hertz to cycles per frame, ms to frames, dB to linear, semitones and cents to ratio); extend the conversion enum and binding goes fully generic, which is what empties the voice-binding switch. Home conflicts with edges (finding 1). |
| Seed namespace | **Voice-anchored; sound scope unserved** (finding 4). |
| reset, seek, suspend, virtualise, restore | "engine honours reset and seek now" is generous: reset is reconstruction, and seek against stateful stages (biquad, delay line, phase accumulator) can only be render-and-discard, never a jump; the honesty test needs that definition of seek written into it or it will pass vacuously. |
| Latency and tail | Right, with the tail's owner moving at sound scope (finding 5). `VoiceEcho.tailFrames` ("carried so nothing downstream derives it a second way") is the exact precedent. |
| Serialisable state, schema version | Sound; note plugin state (delay lines, biquad state) is engine-side and its serialisation is what virtualise and restore will consume; declaring now, implementing later is fine. |
| Resource declarations | Sound; #5 consumes. |
| Render definition | "engine, on the existing `LayerStage` shape" — **superseded by Q3**: on the `RenderBlock` shape, which `LayerStage` becomes. |
| Host adapters | Sound; `createBusHost` exists with two adapters, the seam is real. |
| UI descriptor | Sound; manifest projection is the consumer and is already definition-driven. |
| Diagnostics | Sound; `ControlIssue` exists (`contract/src/control.ts:153`). |

## Reuse map

What the refit consumes rather than rebuilds, verified in source:

- `ParameterDefinition` and constructors: `packages/patch/src/registry/definition.ts` (moves to contract, finding 1).
- Unit conversions: `packages/patch/src/registry/units.ts`, already the only converter `bindVoice` uses.
- Registry entry shape: `SOURCE_DEFINITIONS`/`PROCESSOR_DEFINITIONS` (`registry/parameters.ts:119,134`) generalise into the plugin list; `registry/lookup.ts` and `registry/integrity.ts` are the aggregation and the completeness check, both already written.
- Validation and manifest: already definition-driven (`patch-validation.ts:229`, `manifest.ts:93,157`); they inherit the contract through the registry with no per-kind edits.
- Seed tree: `rootSeed`/`childSeed` (`contract/src/seed.ts`); finding 4 adds one parent, no new mechanism.
- Tail declaration: `echoTailFrames`, `VoiceEcho.tailFrames`, `layerTailFrames` (`contract/src/echo.ts`); the contract's tail field is this, generalised.
- Render clock and slice invariance: `layer-stage.ts`'s `elapsed` contract, transferred verbatim to `RenderBlock`.
- Host seam: `createBusHost` (`control/src/bus-host.ts`), `StampedBus`, `CommandQueue`, `GameAudio`; the contract's host adapters row lands on an existing, twice-adapted seam.
- Holding tests: `test/worklet-null.test.mjs`, the lifetime/envelope seam test, block boundary tests, certification of both packs; all pre-exist and are the named gates.
- Biquad shape: the three-numerators-one-denominator claim is literally true in `layer-filter.ts:126-160` (`setNumerator`); the one-filter-three-modes plugin is a transcription, not a redesign.

## Quality map

- **Deep and right:** descriptor plus one `process`; refusal of inheritance and of an object that draws (Bespoke refuse 1 and 2, honoured); native nodes only after the master sum (recorded, consistent with the tier resolution in the synthesis); the closed palette until #5; the throwaway eighth unit as a falsifiable proof of the DRY goal, then deleted. The last is the best sentence in the issue.
- **Correctly walled:** the steal ramp and pool floors stay foundation-owned; the voicing descriptor adds content policy above them, not into them (finding 6 asks for one sentence to make that visible).
- **The one spent guarantee:** compile-time exhaustiveness over source and processor kinds is traded for load-time descriptor completeness plus a verifier rule (Q3's consequence). Right trade, currently unstated.
- **Slice order:** sound, with slice 3 (delay refit at voice scope) then slice 4 (scope flip) being the mechanical-move-then-reshape discipline done properly; the only correction is honesty about slice 4's semantics (finding 5).

## Exact wording changes proposed

1. **Start here, package line** — after "registry rows in `packages/patch`, composition in `packages/control`", add: "Plugin modules live in `packages/palette`, a leaf importing contract only; engine and patch both import it; `ParameterDefinition` moves to contract; the transcendental seam extends over `packages/palette/src`. Slice 1 lands this with the verifier change." (Or the owner's chosen alternative; the issue must choose, finding 1.)
2. **Where we start, list** — replace item 5 "validation and the manifest projection in control" with: "5. the per-kind address resolution in `packages/patch/src/patch-resolution.ts` `resolvePatchLayer`; validation and the manifest projection are already definition-driven and follow the registry entry." Add after the list: "The recipe builder (`patch-recipe.ts`) switches on its own authoring union; it is refitted in slice 2 or the Done-when grep excludes it, and the choice is explicit."
3. **The contract, ports row** — "Typed ports: audio in and out, control in and out with rate per port, event in".
4. **The contract, first row** — drop "role (source, processor, modulator)" as a stored field; add "role is derived from the ports (`pluginRole`)", or keep it stored with an integrity check against the ports.
5. **The contract, seed row** — "a child of the voice seed keyed by plugin instance id for voice scope; for sound scope, a child of the pack and event chain (the voice seed's parent, without the take) keyed by sound instance and plugin instance id, defined in contract beside `rootSeed`".
6. **The contract, render row** — replace "engine, on the existing `LayerStage` shape" with "engine, on a planar `RenderBlock` (`channels` fixed by the declared layout, optional `key` when the descriptor declares one); `SourceGenerator` and `LayerStage` collapse into it; `[mono]` at voice scope, `[left, right]` at sound scope".
7. **Refit the seven** — after "Each refit is behaviour preserving", add: "except slice 4: moving the echo to sound scope changes where repeats sit in the chain (post-placement, whole-sound). No shipping patch authors an echo, so the proof is certification unchanged, not sample equality of an echoed render."
8. **What is already deep, tail sentence** — extend "the voice lifetime already consumes tail (`layerTailFrames`)" with "; slice 4 moves echo tails from the voice lifetime to the Sound's lifetime, which is the first behavioural duty of the Sound object".
9. **Done when, grep bullet** — either scope the command (`grep -n 'case "tone"\|case "lowpass"' packages/ --include='*.ts' | grep -v patch-recipe` with the recipe exemption argued) or, better, keep the strong form and add patch-resolution and patch-recipe to the refit so it passes honestly. Also note the verifier rule from slice 1 is the durable gate; the grep is a smoke check (a renamed kind string dodges a grep, not the verifier).
10. **Decisions already taken, voicing bullet** — add one sentence: "The Sound's priority policy is content; the pool's steal remains foundation-owned and never reads loudness, so a pack still cannot hold a slot it has lost."
11. **Open questions** — replace with the three resolutions above (Q1 shared descriptor, rate on port, control out added; Q2 Sound instance owned by the bus, `SoundId` on `Voice`, voicing defaults reproducing today; Q3 `RenderBlock` now, forced by slice 4, not by #5).
12. **Start here** — optional: strike or enforce "`MasterLimiter` and `VoicePool` names may not leave the engine" via the slice 1 verifier pass (finding 6).

## Prior art consulted

- **Web Audio Modules 2.0** (`@webaudiomodules/api` `types.d.ts`): one plugin shape (`WamNode` paired with `WamProcessor`); the shared `WamDescriptor`/`WamIODescriptor` declares control output as `hasAutomationOutput: true`; parameters are `WamParameterInfo` objects (the `ParameterDefinition` analogue); control is a timestamped event stream, not `AudioParam` automation; render is the planar Web Audio `process`; latency via `getCompensationDelay`, no tail. Supports Q1 (no descriptor fork; control out on the shared descriptor) and Q3 (planar channels).
- **openDAW** (github.com/andremichelle/openDAW): chain owner is `AudioUnitBinding` holding ordered device collections; voice pools live inside device state; `voicing-mode` is declared on the instrument device. Supports Q2 directly and the recorded voicing decision independently. Its separate modulator device category on its own control graph is the Q1 counter-model this review recommends against; its dynamic `bind_sidechain` is the Q3 alternative refused in favour of descriptor-fixed inputs. Its `reset` semantics (clear sounding state, keep parameters and bindings) is the definition the declared-response honesty test should adopt.
- **MetaSounds** (`FNodeClassMetadata`, `FVertexInterface`): no modulator category; rate is a pin datatype (`FAudioBuffer` versus `float`/`FTrigger`) on one fixed vertex interface declared at class time. Supports Q1 (rate on the port, role from the pins) and Q3 (inputs fixed at descriptor time). Its whole-graph-per-voice instancing is the anti-model for Q2.
- **BespokeSynth** (`audioface-bespoke-synth-modularity.md`): borrows 2 and 3 and refuses 1 and 2 are all honoured by the filed contract; this review's Q1 role-derivation closes the one gap borrow 2 left (illegal role and port combinations unrepresentable rather than asserted).
- None of the three declares tail; the contract's tail field rests on the internal `VoiceEcho.tailFrames` precedent, which is sufficient.

## Verification

- `pnpm run check` at `10ba9fc`: green (typecheck, 270/270 tests, lint, format, structure verification). Observed directly.
- `git status --porcelain`: clean before review and at verdict. No file in the repository was created, modified or staged by this review; the issue was not edited.
- Every file and line cited above was read from source in this session.
