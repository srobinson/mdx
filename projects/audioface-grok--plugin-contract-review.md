---
title: Audioface plugin contract review (Grok, render shape and Sound ownership)
type: projects
tags: [audioface, plugin-contract, design-review, engine, dsp]
summary: Adversarial review of issue #4. LayerStage cannot be the contract process; sound scoped state needs a Sound in the engine; the two place DRY goal has to respect ALLOWED_EDGES.
status: active
created: 2026-09-04
updated: 2026-09-04
project: audioface-next
confidence: high
related:
  - audioface-2026-09-SYNTHESIS.md
  - audioface-game-audio-middleware-gaps.md
  - audioface-2026-09-engine-review.md
  - audioface-bespoke-synth-modularity.md
  - audioface-2026-09-host-seam-audit.md
---

# Plugin contract review

Baseline `main` at `10ba9fc` (issue #4 as filed). Tree clean. Citations are `git show main:<path>` symbols.

## Verdict

Conditional. A uniform descriptor plus a registry row plus a block process is the right Phase 2. Filing `LayerStage.process` as that process, putting descriptor and process in one module, and hanging sound scoped state on `MasterBus` will make #5 reopen the seven. `MasterLimiter` is not a plugin.

## Findings

1. **The DRY goal as written cannot land under `ALLOWED_EDGES`.** Issue #4 wants one module that holds the descriptor and `process`, plus one registry entry. `scripts/verify-structure.mjs` `ALLOWED_EDGES` lets `packages/patch` import `@audioface/contract` only and `packages/engine` import `@audioface/contract` only. Patch cannot see an engine module. Contract cannot hold a process. A file that both sides import has to live in contract, which is where implementations are forbidden. The two place goal that the graph allows: a `PluginDescriptor` type in contract (no kind union growth), one row in `git show main:packages/patch/src/registry/parameters.ts` `PROCESSOR_DEFINITIONS` (id, parameter keys, role, scope), one engine module that exports `create` and `process`. `verify-structure.mjs` binds the ids 1:1. The throwaway eighth unit is that pair, then deletion.

2. **`LayerStage` is the inner loop for a voice scoped audio insert, not the contract process.** `git show main:packages/engine/src/layer-stage.ts` `SourceGenerator.generate` fills a mono `Float32Array`. `LayerStage.process` works that buffer in place. `git show main:packages/engine/src/voice-renderer.ts` `VoiceRenderer` composes generate, `applyLayerAmplitude`, then `echoed`. A modulator writes control. A sound scoped echo runs after voices mix. WAM 2.0 `WamProcessor.process` already takes `inputs: Float32Array[][]` and `outputs: Float32Array[][]` and ignores AudioParam. openDAW Werkstatt `process(io, block)` has `io.src[0/1]` and `io.out[0/1]`. Filing `LayerStage` as the contract process makes #5's compressor key input and LFO a second break of the seven.

3. **Sound scoped state has no home.** There is no `Sound` type. `git show main:packages/contract/src/voice.ts` `Voice` carries listener, gain, layers, and seed. `git show main:packages/engine/src/master-bus.ts` `MasterBus` pools voices, places each one (`DistanceField`, `StereoImage`), sums, then `MasterLimiter.limit`. Echo state lives in `git show main:packages/engine/src/layer-echo.ts` `echoStage` on the layer, and `git show main:packages/engine/src/voice-lifetime.ts` `authoredLifeFrames` adds `layerTailFrames`. Putting a delay line on `MasterBus` mixes device wide limiting with per Sound FX. Putting it on `Voice` keeps today's per voice echo and fails "a bed with two voices renders one echo".

4. **`MasterLimiter` must stay unnamed.** `git show main:packages/engine/src/master-limiter.ts` says a pack that can tune the limiter can defeat the stress gate, and `verify-structure.mjs` holds the name inside engine. Issue #4 lists limiter next to reverb, delay, and compressor as a sound scoped plugin. That list is the voicing decision's parenthetical. Current code contradicts the limiter half. Keep the foundation limiter. A pack compressor in #5 is a different plugin.

5. **`bindLayer` treats every non filter as delay.** `git show main:packages/patch/src/voice-binding.ts` `bindLayer` maps `isFilterProcessor` to `bindFilter` and `!isFilterProcessor` to `bindEcho`. A third processor kind becomes an echo. The refit has to kill that default, not extend it.

6. **The five switch count is short.** Adding a kind today also touches `git show main:packages/patch/src/patch-recipe.ts` `buildSourceLayer` and `connectionDraftsForLayer`, `git show main:packages/patch/src/patch-resolution.ts` `resolvePatchLayer`, `git show main:packages/contract/src/patch.ts` `LAYER_PROCESSOR_TYPES` / `FILTER_PROCESSOR_TYPES`, and `git show main:packages/contract/src/source.ts` `VoiceSource`. Manifest already walks `SOURCE_DEFINITIONS` and `PROCESSOR_DEFINITIONS` (`git show main:packages/control/src/manifest.ts` `sourceSchema`, `processorMember`), so control is not a sixth hand write. Recipe and resolution are. The eighth unit proof fails while those source switches remain.

7. **Slice 1 fights itself.** "Contract types and the descriptor, no implementation change" and "structure verifier extended so a plugin module is the only place its `kind` string appears" cannot both be true on this tree. The kind strings live in the unions and switches above. A verifier that forbids them fails until slices 2 to 4 move the kinds. Enabling it in slice 1 forces empty plugin modules that reexport today's kinds, which is a parallel path.

8. **Host adapters on the plugin are a pass through.** Phase 1.5 already hosts the kernel through `git show main:packages/control/src/bus-host.ts` `createBusHost`. Offline, worklet, and the null test drive that one process. A per plugin host adapter field has one filler. Native nodes stay Phase 4 and mix tier only (synthesis section 3). Delete the field.

9. **UI descriptor duplicates `ParameterDefinition`.** `git show main:packages/patch/src/registry/definition.ts` `ParameterDefinition` already has label, group, unit, range, response curve, default, authority, lifetime. Manifest projects those. Extra UI facts (meters, custom editor flag, display transform) belong as optional fields on that row or as a thin overlay the plugin names. A second table of labels will drift.

10. **Engine does not honour seek or reset as named operations.** The issue says engine honours reset and seek now. The only reset in engine source is `StampedBus` peak reset on report. Voice begin constructs new biquad and delay state, which is reset by construction. There is no seek. Declare `unsupported` for seek, suspend, virtualise, and restore on the seven. Honesty tests cover `reset: "zeros"` (delay line and biquad silent after `create`) and tail (silence from `echoTailFrames`). Do not invent `ControlIssue` codes for those. `git show main:packages/contract/src/control.ts` `ControlIssueCode` already has `value_out_of_range`, `unparsable_value`, `rejected`. Add codes only for missing asset, unsupported layout, and restore failure when a plugin actually declares restore.

11. **"Each refit is behaviour preserving" contradicts echo to sound scope.** Moving `delay` off the layer changes a two voice bed and a two layer patch with two delay processors. Say the echo slice is an intentional behaviour change, held by a new two voice test, and that the source and filter slices keep today's samples.

12. **Envelope is listed as a voice scoped plugin and is not one of the seven.** `applyLayerAmplitude` is still the answer for where a layer ends (`VoiceLayer` comments, `voice-lifetime.ts` `isSustainingEnvelope`). Leave the envelope as a `VoiceLayer` field this phase. The contract may allow an envelope plugin later. Do not refit it here.

## Amended interfaces

Contract types only. No kind union.

```ts
type PluginId = string;
type PluginRole = "source" | "processor" | "modulator";
type PluginScope = "voice" | "sound";
type PortRate = "control" | "audio";
type ChannelCount = 1 | 2;

type AudioPort = { readonly id: string; readonly channels: ChannelCount };
type ControlPort = { readonly id: string; readonly rate: PortRate };
type EventPort = { readonly id: string };

type Lifecycle =
  | "zeros"
  | "unsupported";

type PluginDescriptor = {
  readonly id: PluginId;
  readonly version: string;
  readonly role: PluginRole;
  readonly scope: PluginScope;
  readonly layouts: readonly ChannelCount[];
  readonly audioIn: readonly AudioPort[];
  readonly audioOut: readonly AudioPort[];
  readonly controlIn: readonly ControlPort[];
  readonly controlOut: readonly ControlPort[];
  readonly eventIn: readonly EventPort[];
  readonly parameters: readonly ParameterKey[];
  readonly seed: "none" | "instance";
  readonly reset: Lifecycle;
  readonly seek: Lifecycle;
  readonly suspend: Lifecycle;
  readonly virtualise: Lifecycle;
  readonly restore: Lifecycle;
  readonly latencyFrames: number;
  readonly tail: "none" | "static" | "from-parameters";
  readonly resources: readonly ResourceDeclaration[];
  readonly meters: readonly string[];
  readonly customEditor: boolean;
};

type RenderBlock = {
  readonly elapsed: number;
  readonly frames: number;
  readonly audioIn: readonly Float32Array[];
  readonly audioOut: readonly Float32Array[];
  readonly controlIn: readonly Float32Array[];
  readonly controlOut: readonly Float32Array[];
};

type PluginInstance = {
  readonly process: (block: RenderBlock) => void;
  readonly tailFrames: () => number;
};

type PluginModule = {
  readonly descriptor: PluginDescriptor;
  readonly create: (input: PluginCreate) => PluginInstance;
};

type VoicingDescriptor = {
  readonly mode: "mono" | "poly";
  readonly maxVoices: number | null;
  readonly priority: "last" | "lowest" | "highest";
  readonly retrigger: "legato" | "retrigger" | "hard";
  readonly steal: "oldest" | "quietest" | "ignore" | "pool";
  readonly portamentoFrames: number | null;
};

type Sound = {
  readonly id: SoundId;
  readonly voicing: VoicingDescriptor;
  readonly listener: ListenerField;
  readonly gain: number;
  readonly layers: readonly [VoiceLayer, ...VoiceLayer[]];
};
```

Role plus ports make illegal graphs unrepresentable, which is the Bespoke factory flag lesson without the assert:

- source: `audioIn` empty, `audioOut` length 1, `controlOut` empty
- processor: `audioIn` and `audioOut` length at least 1
- modulator: `audioOut` empty, `controlOut` length at least 1

`controlIn` / `controlOut` length is 1 at control rate and `frames` at audio rate. One `process`. That is Bespoke `IModulator::Value(samplesIn)` with the rate written on the port.

`LayerStage` stays. A voice scoped audio processor aliases `audioIn[0]` and `audioOut[0]` to the same mono buffer and calls through. Sources fill `audioOut[0]`. Sound scoped processors see the Sound mix (stereo layouts declared, the seven's echo can stay mono in and out on that mix before place).

`PluginCreate` carries converted parameter values and, when `seed: "instance"`, `childSeed(voiceRoot, pluginInstanceId)`. Today's layer seed `childSeed(rootSeed(voice.seed), \`layer/${layer.id}\`)` in `VoiceRenderer` remains the parent; a plugin instance takes a child labeled by `ProcessorId` or the source slot.

Patch registry row, one per plugin:

```ts
type PluginRegistryRow = {
  readonly id: PluginId;
  readonly parameterKeys: readonly ParameterKey[];
  readonly role: PluginRole;
  readonly scope: PluginScope;
};
```

`SOURCE_DEFINITIONS` and `PROCESSOR_DEFINITIONS` become this list. Parameter bodies stay in `PARAMETER_ROWS`. The plugin names keys. The registry remains the one place a row is defined.

Engine `SoundGraph` (name stays inside engine, same rule as `MasterLimiter` and `VoicePool`):

- owns `VoicingDescriptor` and last pitch (instance state, not patch state)
- runs voice scoped instances per `Voice`
- mixes those voices
- runs sound scoped instances once
- places once from `Sound.listener`
- returns a stereo block to `MasterBus`

`MasterBus` sums Sounds, then `MasterLimiter`. Defaults that reproduce today: `mode: "poly"`, `maxVoices: null`, `steal: "pool"`, `portamentoFrames: null`, `retrigger: "retrigger"`. Slice 4 may construct a Sound with two Voices in a test without implementing steal policy. Steal, priority, and portamento behaviour wait for #5.

`BusHost` grows later messages for seek and reset. Plugins declare the response. Do not put those methods on `GameAudio` this phase.

## Answers to questions 1 to 3

**1.** One descriptor. A modulator is a plugin whose only required out port is control. Rate lives on the port (`control` or `audio`). One `process` writes `controlOut`. A second modulator type would duplicate lifecycle, seed, diagnostics, and honesty tests. Specialized "source generates, processor inserts, modulator writes control" is a role discriminant plus port cardinalities, which the middleware field list already allowed. Do not wait for #5 to write this; the seven are all sources and processors, and the type has to exist before the palette grows.

**2.** A new `Sound` object between `Voice` and `MasterBus`. State for a sound scoped plugin lives on that Sound's graph. `MasterBus` stays the device: pool of Sounds (today, one Voice per Sound until voicing behaviour), place already done by the Sound, sum, limit. `Voice.listener` moves to `Sound.listener` so polyphony of one posted event shares an emitter. `GameAudio.trigger` can keep returning a `VoiceId` for the first voice of a new Sound this phase; a `SoundId` on the trigger is #5 if the public host needs it. Do not store delay lines on `MasterBus`.

**3.** The contract needs `RenderBlock` now. `LayerStage` remains the mono in-place adapter used by the filter and, until slice 4, the delay. Side chain in is an extra `audioIn` port. The compressor in #5 then adds a registry row and an engine module. It does not widen `LayerStage` and does not rewrite the seven.

## Reuse map

- Reuse: `packages/engine/src/layer-stage.ts` `SourceGenerator`, `LayerStage`. Voice scoped audio inserts keep this inner loop.
- Reuse: `packages/engine/src/layer-filter.ts` `biquad`, `setNumerator`. One filter plugin, three numerators, one denominator. Mode is a parameter. `FILTER_PROCESSOR_TYPES` collapses.
- Reuse: `packages/engine/src/layer-echo.ts` `echoStage`, `packages/contract/src/echo.ts` `echoTailFrames`. Move the instance from the layer to the Sound graph. Keep the arithmetic.
- Reuse: `packages/patch/src/registry/definition.ts` `ParameterDefinition`. Descriptor half of the contract. Do not add `WamParameterInfo`.
- Reuse: `packages/patch/src/registry/parameters.ts` `PARAMETER_ROWS`, `SOURCE_DEFINITIONS`, `PROCESSOR_DEFINITIONS`. The last two become `PluginRegistryRow`. Rows stay the one definition of a key.
- Reuse: `packages/contract/src/seed.ts` `childSeed`. Instance seed is a labeled child of the voice root, as layers are today.
- Reuse: `packages/control/src/bus-host.ts` `createBusHost`. The host adapter. Plugins do not grow a second one.
- Reuse: `packages/control/src/manifest.ts` walking definition lists. Manifest keeps projecting registry rows. UI extras land on the row.
- Reuse: `packages/engine/src/master-limiter.ts` `MasterLimiter` as foundation, unnamed.
- Reuse: `test/worklet-null.test.mjs` and certification. Source and filter slices hold it. Echo slice adds a two voice equality.
- Existing infra: `scripts/verify-structure.mjs` `ALLOWED_EDGES` plus a new id pairing check (patch registry id equals engine module id; kind string only in that engine module and tests).
- Similar checked and rejected: WAM `WebAudioModule` plus `createGui` on the processor (Bespoke refuse list 2; UI stays a descriptor). openDAW BoxGraph as the runtime (chassis is a rack, graph is specialist). MetaSounds graph as home (UI direction). Inheritance as the contract (Bespoke refuse list 1). Per plugin host adapters (one adapter is hypothetical; BusHost already has two). `RowSet` style generic over role (host seam review of #11). Putting limiter in the palette (engine comment on the stress gate).
- None found: a Sound type, a seek operation, a generic bind that is not `!isFilterProcessor`.

## Quality map

- Duplication / parallel implementation: `LAYER_SOURCE_TYPES` in `patch.ts`, `VoiceSource` kinds in `source.ts`, `SOURCE_DEFINITIONS` in `parameters.ts`, and switches in `voice-binding.ts`, `source-generator.ts`, `patch-recipe.ts`, `patch-resolution.ts`. Collapse to registry row plus engine module.
- Duplication: `FILTER_PROCESSOR_TYPES` three times (`patch.ts`, `PROCESSOR_DEFINITIONS`, `layer-filter.ts` `setNumerator`). One plugin with a mode.
- Boundary / design: `bindLayer` `!isFilterProcessor` implies delay. Replace with `scope` and `role` from the registry row.
- Boundary: `DLY-10` to `DLY-12` sit in group `"filter"` at layer scope. Echo to sound scope has to move their scope with them.
- Boundary: `Voice.listener` is per voice while a Sound scoped echo needs one emitter. Move listener to Sound.
- Dead code / obsolete path: `firstFilterProcessor` as the noise recipe's hardwired bandpass. After one filter plugin, recipe still may insert a filter instance; it should not special case the first processor as "the" filter in the contract.
- File size: `parameters.ts` and `voice-binding.ts` stay under 700. New plugin modules are small. Do not grow `voice-renderer.ts` with a kind switch; it already asks once via `createSourceGenerator`.
- Grooming: refactor `bindLayer` and the source switches during the source and filter slices. Defer recipe sugar if the eighth unit test constructs patches through registry helpers rather than `patch-recipe.ts`. Resolution should walk `parameterKeys` from the row so a new processor does not edit `resolvePatchLayer`.

## Field table

| Field | Home as filed | Disposition |
|---|---|---|
| Stable id, version, role, scope | contract | Keep as `PluginDescriptor` type in contract. Values live on the engine module. |
| Channel layouts | contract | Keep. Seven are mono. Sound scoped echo may declare mono on the Sound mix before place. |
| Typed ports | contract | Keep, with rate on control ports. This answers question 1. |
| Parameter descriptors | reuse `ParameterDefinition` | Keep. Plugin names keys. Rows stay in patch. |
| Seed namespace | contract, engine | Keep. `childSeed` labeled by instance id. |
| Reset, seek, suspend, virtualise, restore | contract; engine honours reset and seek now | Amend: engine honours none of these as operations today. Seven declare `reset: "zeros"` and the rest `unsupported`. Honesty tests on reset and tail. |
| Latency and tail | contract; `layerTailFrames` | Keep. Echo tail moves from layer to Sound. |
| Serialisable state | contract | For the seven, identity over `ParameterValueMap`. No parallel blob. Migration hook is a no op held by a test. |
| Resource declarations | contract | Empty on the seven. Keep the field for #5 samples. |
| One block render | engine, on `LayerStage` | Amend: `RenderBlock` on the contract type; `LayerStage` is the voice scoped audio adapter. |
| Host adapters | control | Delete from the plugin. `BusHost` is the host. |
| UI descriptor | contract | Fold extras into `ParameterDefinition` or a thin overlay. Do not copy labels. |
| Diagnostics | contract as `ControlIssue` codes | Reuse `value_out_of_range`, `unparsable_value`, `rejected`. Add codes when a declaration is real. Underrun is a `WorkletMessage` report, not an issue code. |

## Package ownership

Unchanged graph:

- contract: types (`PluginDescriptor`, `RenderBlock`, `VoicingDescriptor`, `Sound`, branded ids). No process bodies. No `MasterLimiter`, no `VoicePool`, no `SoundGraph` names.
- patch: `PARAMETER_ROWS`, `PluginRegistryRow` list, generic bind from row keys through existing unit conversions (`cyclesPerFrameFromHertz`, `framesFromMilliseconds`, `linearFromDecibels`).
- engine: one module per plugin (`create` / `process` / `tailFrames`), `SoundGraph`, existing `LayerStage` adapters, `MasterBus` summing Sounds.
- control: manifest projection from the registry list; `BusHost` unchanged this slice except later seek messages.
- adapters: still reach engine only through control.

A new `packages/plugins` package would cycle (process needs transcendental and `LayerStage`; renderer needs process). Do not add it.

## DRY goal (replacement text)

Adding a processor adds one engine module and one `PluginRegistryRow`. Contract unions do not grow. Prove with a throwaway eighth unit in a test that registers a row and a module, renders, then deletes both. `grep -n 'case "tone"\\|case "lowpass"' packages/` returns only the plugin's own module. Recipe may stay closed over the shipping seven if the proof does not go through `patch-recipe.ts`. Resolution and bind must already be generic or the proof is false.

## Slice order (replacement)

1. Contract types (`PluginDescriptor`, `RenderBlock`, `VoicingDescriptor`, `Sound`) and the registry row type. No kind locality verifier yet. No process change. Null test green.
2. Sources onto the contract (tone, noise, fm). Kill the source switches in bind, generator, and resolution. Kind locality verifier on source ids only.
3. One filter plugin with three modes; delay still voice scoped. Kill `FILTER_PROCESSOR_TYPES` and `bindLayer`'s non filter default. Kind locality on processor ids.
4. `SoundGraph` in engine; voicing descriptor on `Sound` with today's defaults; echo moves to sound scope; listener and tail move with it. Two voice one echo test. Intentional behaviour change. Verifier covers echo's id.
5. Throwaway eighth unit, then deletion. Kind locality verifier on for every shipping id.

Each slice through the Slice Build Loop.

## Exact issue wording changes

Replace "A plugin is a descriptor plus one `process(block)` function" with: "A plugin is a `PluginDescriptor` plus `create` that returns `process(RenderBlock)`. `LayerStage` remains the mono in-place adapter for a voice scoped audio insert."

Replace the host adapters row with a sentence under the table: "Host adapters stay `BusHost`. Plugins do not declare them."

Replace "engine honours reset and seek now" with: "The seven declare `reset: 'zeros'` and seek, suspend, virtualise, restore as `unsupported`. Honesty tests hold reset and tail. Seek messages on `BusHost` wait until a plugin declares seek."

Replace "Each refit is behaviour preserving" with: "Source and filter refits are behaviour preserving (null test, certification, block boundary). Echo to sound scope is an intentional behaviour change: one echo per Sound, tail on the Sound, held by a two voice test."

In Decisions already taken, replace the parenthetical "reverb, delay, compressor, limiter" with "reverb, delay, compressor". Add: "The foundation `MasterLimiter` stays unnamed and unaddressable."

Replace slice 1's verifier sentence with the slice list above.

Replace the DRY done-when bullet with the DRY goal replacement text.

Replace open questions 1 to 3 with the answers in this review (one descriptor with rate on the port; `Sound` between `Voice` and `MasterBus`; `RenderBlock` now, `LayerStage` as adapter).

## Borrowed contracts, refused shapes

WAM 2.0: borrow `WamDescriptor` identity, `WamProcessor.process(inputs, outputs)` with AudioParam ignored, `getCompensationDelay` as `latencyFrames`, `getState`/`setState` as the serialisable hook. Refuse `createGui` on the processor, URI loading, MIDI and OSC ports, `WamParameterInfo` next to `ParameterDefinition`.

openDAW: borrow `AudioDeviceChain` as an ordered insert rack, `process(io, block)` buffer pair, a registry of device ids. Refuse BoxGraph as the DSP runtime, a MIDI device chain as this contract, Werkstatt-style JS inside the quantum.

MetaSounds: borrow typed pins (audio buffer, scalar, trigger), Source versus Patch as Sound versus reusable graph, constructor pins as frozen parameters. Refuse the graph as the default authoring surface, watched outputs as the game API, `UE.Source.OneShot` as lifetime.

## Signoff

I sign off conditional on the following changes: rewrite the DRY goal to one engine module plus one patch registry row under `ALLOWED_EDGES`; make `RenderBlock` the contract process and keep `LayerStage` as the voice scoped audio adapter; put sound scoped state on a new engine `Sound` between `Voice` and `MasterBus`; drop host adapters and duplicated UI fields from the plugin; move the kind locality verifier after the refit; call echo to sound scope an intentional behaviour change; drop limiter from the sound scoped examples; answer the three questions with one descriptor (rate on the port), `Sound` ownership, and `RenderBlock` now.
