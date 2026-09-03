---
title: Audioface Phase 2 data and runtime design
type: design
tags: [audioface, architecture, phase2, data-model, sound, plugins]
summary: Lead proposal for authored ownership, Sound identity, plugin preparation, atomic admission, and rendering guarantees in issue 4.
status: draft
created: 2026-09-05
updated: 2026-09-05
project: audioface-next
source: https://github.com/littleorgans/audioface/issues/4
related: [audioface-astra-initial-review, audioface-astra-phase2-synthesis, sound-runtime-identity-audioface]
---

# Audioface Phase 2 data and runtime design

This is Astra's lead proposal for the ongoing design of [issue 4](https://github.com/littleorgans/audioface/issues/4). It is not an approved implementation specification. The retained Sound product choice in [issue 15](https://github.com/littleorgans/audioface/issues/15) remains open. Baseline source is `10ba9fc16cea55271c6d428c8fe64c8df0b9c354`.

## The caller controls a Sound and releases individual Voices

Proposed usage, with the existing event vocabulary:

```ts
const wind = game.createSound({ event: "ambience-wind", emitter });
const first = wind.trigger({ take: 0, listener: { distance: 0.2 } });
const second = wind.trigger({ take: 1, listener: { distance: 0.6 } });

wind.release(first);
wind.release(second);
wind.dispose();

game.triggerOneShot("gun-ar", { emitter, take: 2 });
```

`createSound`, `SoundHandle`, and `triggerOneShot` are proposed interfaces. Existing `VoiceId`, `EmitterId`, listener fields, and take semantics are reused. Two calls to `createSound` for the same emitter and event produce independent runtime state. The one shot helper uses the same creation, trigger, and retirement machinery with automatic lifetime policy.

One owner decision remains about that usage: explicit handles retain voicing history while idle, while automatic effects retire after their voices and tails finish. This is the recommendation already present in issue 15, not yet an owner decision.

## Keep authored Patch and runtime Sound distinct

The proposed ownership chain is:

```text
Domain event
  Pack.events[event] owns a Patch value
    Patch owns Layers, plugin placements, values, and connections
      preparation pins an authored revision
        Sound instance owns shared plugin state and voicing history
          Voice owns one trigger's execution and voice-scoped plugin state
```

Keep the existing name `Patch` for authored data. A designer may see that Patch presented as a Sound in the interface, but runtime state never enters the authored object. No parallel `AuthoredSound` copy of Patch is introduced.

Keep event-owned content for Phase 2. A control target for pack content is the validated pair of pack id and event id. The existing PatchId remains local authored identity and an input to connection-jitter seed derivation, so identical PatchIds in different bindings cannot collapse editor state. Loose patch surfaces retain PatchId targets and reject duplicate ids at construction.

There is no independently minted binding id stored beside the map key. A `PackEventRef` is a reference derived from the containing pack and event. This avoids two fields that can disagree about the same binding.

Copying content to another event makes an independent authored value. Editing it changes only that binding. Shared authored content would require an explicit pack-owned library and reference semantics. That is a valid alternative, but no recorded product requirement currently calls for shared edit propagation. Do not infer it from matching ids or JavaScript object aliases.

An edited binding has a monotonically increasing revision. A prepared definition identifies its binding, revision, sample rate, and plugin versions. This is runtime preparation identity. Durable content fingerprints and saved certification provenance require separate work and are not claimed by an in-memory revision counter.

## Put parameter values with their structural owner

Each authored plugin placement contains its PluginInstanceId, PluginId, and local parameter values. A layer owns its source and ordered voice processor placements. Patch owns the ordered sound processor placements. Built-in layer amplitude and timing remain explicit during Phase 2, because making amplitude an ordinary modulator belongs to Phase 3.

ParameterAddress remains the common edit and diagnostic address. Generate it from the owning binding, layer or plugin instance, and local parameter key. Do not retain a second authoritative copy of plugin values in a flat root map.

This data refit is a clean schema cutover for owned content and fixtures. Do not add a legacy loader or compatibility aliases. Preserve the existing source seed labels explicitly during conversion.

Deletion removes owned values and all connections whose source or destination refers to the removed object. New objects receive fresh identities from a persisted monotonic allocation cursor within the Patch. Parsing checks cursor consistency against allocated identifiers. Labels may repeat; identities may not be reused after deletion within an authored lineage.

Changing an existing source's type is different from deleting its owner. Retain only explicitly compatible values. A removed graph endpoint never reconnects itself to a new object with a recycled label.

## An explicit Sound pins a definition

Control mints an opaque SoundInstanceId. GameAudio wraps it in a SoundHandle that owns the host interaction. MasterBus owns the engine Sound. The binding and prepared revision are captured when the handle is created.

The handle starts in `preparing` until the audio host acknowledges creation. Triggers submitted meanwhile queue behind that creation. A correlated create refusal marks the handle `refused`, rejects its pending starts, and refunds reservations. No Voice is reported as admitted merely because the caller received an id. Disposal while preparing closes admission and cancels the queued work. Positive creation acknowledgement is part of the proposed host protocol; the current refusal-only protocol is insufficient for this lifetime.

The proposed lifetime policy is:

| Event | Result |
| --- | --- |
| Create retained Sound | Validate and prepare its definition, create independent runtime identity, permit triggers. |
| Trigger | Prepare one Voice against the pinned definition, then admit it at its frame. |
| Last Voice and tail finish | Retained Sound becomes idle and keeps its logical history. Ephemeral Sound retires. |
| Dispose | Close admission immediately, cancel future starts, release held Voices, let existing one shots and declared tails finish. |
| Repeated dispose | Return the existing closed state without another release or a new tail. |
| Device rebuild | Invalidate prior handles and queued commands. New playback requires new handles. |

Handle admission state and DSP activity are separate. A disposed handle can have draining DSP. An idle retained handle can remain addressable. Releasing one Voice cannot dispose the enclosing Sound.

Device generation is transport identity. It is not added to DSP seeds. Phase 2 does not pretend to restore phase, delay buffers, or voicing history after a rebuild. A future capability may implement exact restoration. Until then, invalidation is explicit and observable.

Idle does not automatically mean free DSP memory. A plugin must declare and implement a supported suspend or restore policy before its buffers can be discarded while promising continuity. Admission accounts for retained and prepared resources.

Host construction requires a validated `HostBudget` with finite positive safe-integer limits for Sound handles, prepared starts, and DSP buffer bytes. There is no unbounded fallback. A plugin configuration declares its maximum owned buffer allocation; the host also accounts for its own buffers. Handle and queue limits bound bookkeeping growth separately. This is not a byte-exact cap on the JavaScript heap. Preparation reserves the budget, cancellation and retirement refund it, and exhaustion returns a diagnostic before mutation. Concrete shipping values require measurements at both supported sample rates during the extension proof. Those values are host capacity policy and cannot be authored by a pack or plugin.

## Authored edits and live runtime controls have different effects

An authored edit creates a new prepared revision for future Sound handles. Existing handles, including their future triggers, retain their pinned revision. Structural hot replacement is outside Phase 2.

Runtime parameter commands target one instance. Reuse `ParameterDefinition.lifetime`, with its existing `frozen` and `live` values. Frozen means captured at the start of the parameter's scope. A voice-scoped frozen value is captured when the Voice is prepared. A sound-scoped frozen value is captured when the Sound is prepared. Do not add a second application field with the same meaning.

Phase 2 declares that distinction and preserves currently supported live listener behavior. Continuous plugin modulation and general runtime parameter updates belong to Phase 3. Do not expose an operational setter merely because the type can describe it.

The editor's preview can dispose its previous handle and create one from the new revision. The old graph drains under its old revision. Seamless sustained graph replacement, automatic state migration, and crossfading between edited graphs require their own behavior and tests.

Control inspection reports authored values, pack character overrides, mutability, and application timing. Derived values are read only. An effective value is meaningful only for a named context: a preview trigger or a running instance at a reported frame. There is no context-free effective number for a parameter changed by velocity, variation, or modulation.

The minus 20 dB authored gain overridden to minus 10 dB is displayed with both values and their provenance. A derived duration cannot accept a set operation. Values travel as structured data; adapters format them without reconstructing parameter meaning.

Remote edit commands carry the revision the client actually read. The server must not replace it with a fresh revision before applying an edit.

## Prepare before committing runtime ownership

There are two separate products of preparation:

1. An immutable, structured cloneable definition or Voice plan. It contains data and resource references.
2. Engine-private prepared instances. They contain factories' outputs, buffers, filters, delay state, and reservations.

Functions and PluginInstance objects never cross MessagePort. Both hosts install the same control-composed catalog. The audio side resolves plugin ids and versions against that local installation.

Patch performs generic authored structure and parameter validation against the catalog definition view. Control coordinates binding, trigger, and resource context. Plugin-specific joint constraints belong to the owning engine module, alongside its factory. The proposed pure hook is `PluginModule.prepare(ConfigurationRequest): Preparation<PreparedConfiguration>`. Its request contains effective local parameter values and the actual sample rate. Its result contains cloneable normalized configuration and a maximum DSP byte requirement, or structured issues. The owning module checks combinations such as pitch times ratio there, without constructing DSP or adding kind switches elsewhere.

`PluginModule.create({ configuration, seed }): Preparation<PluginInstance>` constructs engine-private state in the audio realm. The receiving boundary validates serialized configuration against its local module before construction. The host catches unexpected factory or allocation exceptions as refusals too. This adds one preparation operation to PluginModule while preserving the one-module, one-catalog-entry extension rule. Asset-backed preparation will extend its resource context with the real sample source in Phase 3; Phase 2 must not invent an asset loader in patch.

The audio host constructs every required instance and checks resource limits before any shared membership or victim changes. Preparation may allocate and fail. A future start retains prepared instances until its scheduled frame or cancellation.

At commit, the engine first checks current identity, generation, Sound admission state, and pool eligibility. Any refusal occurs before mutation. It then installs all prepared paths and applies the selected steal as one synchronous state transition. Preparation success alone cannot make commit infallible: a Sound may have been disposed while the start waited.

Only the engine owns pool admission. Control never passes a mutable DSP object into the engine from another realm. A preparation failure releases its reservations and produces one correlated refusal. It cannot remove a previous Voice, leave a pool entry without a signal path, or poison the next render.

Future command preparation occurs on receipt, outside `process`. Plugin construction uses local initial state; absolute playback time arrives at activation and in RenderBlock. This allows preparation before the device-to-bus origin is known. A start cannot allocate its signal path when the render loop reaches its timestamp.

The allocation claim must be scoped and measured. Plugin `process` receives reused buffers, port descriptors, and event storage. Starts, queue transitions, fades, sub-block views, and reports also need an allocation audit before claiming the entire host callback is allocation free. The current code does not establish that stronger claim.

## Processing order changes only in the declared behavior slice

During the structural Sound slice, retain the current global VoicePool iteration and each Voice's mono render, distance, stereo placement, and Float32 accumulation order. Sound owns membership and lifecycle while MasterBus can still visit those members globally. An empty Sound chain is not a reason to group the sum differently.

The delay slice adopts this explicit topology:

```text
Voice A layers -> amplitude/gain -> distance A -> stereo image A --+
                                                                 +-> Sound stereo sum
Voice B layers -> amplitude/gain -> distance B -> stereo image B --+         |
                                                                           v
                                                               ordered sound plugins
                                                                           |
                                                              stable master accumulation
                                                                           |
                                                                    MasterLimiter
```

Sound-scoped delay receives the already placed stereo mixture once. Repeats retain the placement of the input they recorded. Later movement affects new input, not the location of samples already in the delay line. This preserves the meaning of per-Voice placement while making the scope change explicit.

Moving to per-Sound buffers also changes floating point association. Keep that in the same declared behavior slice and test it directly. The structural slice must not claim sample identity merely because no plugin changes the samples. Do not keep a second permanent rendering implementation solely to hide the planned scope change.

VoicePool remains the single authority for global class floors and steals. Sound tracks the Voices and fading paths it owns. Per-Sound voicing behavior arrives in Phase 3 above the foundation pool policy.

Sound owns the tail after its Voices stop feeding the chain. Effective latency and tail belong to initialized instances, not immutable plugin metadata. Composition follows actual graph topology: serial tails accumulate and parallel paths require their respective bound; taking the maximum of all inserts is insufficient. Exact formulas and their contracts need tests for the chosen chain semantics.

Phase 2 uses static accepted configurations for any timing-changing parameter. Live changes that alter latency or tail must declare a supported rescheduling policy before they can be exposed. Phase 3 must resolve that policy before enabling modulation of such parameters.

Native nodes remain after the kernel master sum. Independent native Sound routing or HRTF would require distinct signals before that collapse. Record that unresolved Phase 4 question in issue 6; do not quietly add stems or move the limiter while implementing Phase 2.

## Preserve the seed that reaches the source

Preserve both existing steps:

```text
Voice root: SEED_ROOT -> packId -> eventId -> String(take)
Source:     Voice root -> "layer/<existing LayerId>"
```

In the migration, assign the source plugin a stable seed label corresponding exactly to its existing layer namespace. The generic resolver hashes that label once. Adding `PluginInstanceId` as an additional child after the current layer seed would change the source samples even though the Voice root stayed unchanged.

New plugin placements receive stable instance namespaces. Inserting an unrelated plugin cannot renumber existing instance identities or seed labels.

Keep the accepted Sound branch:

```text
Content root: SEED_ROOT -> packId -> eventId
Sound plugin: Content root -> SoundInstanceId -> PluginInstanceId
```

Mint SoundInstanceId in control and include it in replayable create commands. Offline replay supplies those recorded ids. Opaque means callers do not interpret the id; it does not mean the id must be regenerated randomly during replay. No second public SoundSeedKey is necessary for this design.

Identical pack, event, and take values intentionally reproduce the same Voice stream today. Runtime Voice identities and mutable DSP instances remain separate. Preserve that behavior. Amend the issue's absolute no-alias wording to require independence for distinct seed identities, while explicitly permitting deterministic replay. Automatic take selection may be a later host convenience; it must not silently alter the current seed tree.

## Complete the plugin contract without duplicating the registry

Keep one immutable PluginDefinition and one PluginModule per engine plugin. The definition contains serializable metadata. Module operations contain configuration preparation, factory construction, and any implemented state codecs. Control composes them once; patch receives a definition view of the same catalog.

RenderBlock identifies each audio port and its planar channels. Control ports carry one scalar or a frame buffer according to declared rate. The block carries absolute start, frame count, and local instance age. Events carry a declared port and an offset within `[0, frameCount)`. Port and event storage is prepared and reused.

Supported and unsupported lifecycle operations are explicit variants. Parameters do not stand in for saved DSP state. Exact restoration includes oscillator phase, filter memory, delay contents, and any other state the plugin needs. A stateless plugin can honestly declare an empty state codec; a stateful plugin without a codec declares restoration unsupported.

There are seven legacy unit kinds to refit into five module definitions: tone, noise, FM, one multimode filter, and delay. The amplitude envelope remains part of the Voice layer until the Phase 3 modulator work replaces it.

## Bind implementation to existing owners

| Concern | Existing owner and disposition |
| --- | --- |
| Authored parsing and resolution | `packages/patch/src/patch-validation.ts` `validatePatch`, `patch-resolution.ts` `PatchResolver`, and `resolvePatch`: refactor to catalog-driven ownership. |
| Unit conversions | `packages/patch/src/registry/units.ts`: reuse conversion functions; plugin configuration preparation owns joint constraints. |
| Parameter metadata | `packages/patch/src/registry/definition.ts` `ParameterDefinition`: move to contract and extend one authoritative definition. |
| Editing and revision | `packages/control/src/surface.ts` `packControlSurface`, `apply`; `packages/patch/src/patch-editing.ts`: change pack target identity, cascade deletion, and fresh allocation. |
| Generic controls | `packages/control/src/manifest.ts` and `snapshot.ts`: reuse projection, add mutability and contextual provenance. |
| Host clock and refusals | `packages/control/src/bus-host.ts` `createBusHost`: keep origin translation and correlation; add preparation/activation lifecycle. |
| Scheduling | `packages/engine/src/command-queue.ts` `CommandQueue`: adapt queued entries to prepared, cancellable work. |
| Runtime admission | `packages/engine/src/master-bus.ts` `MasterBus.start`, `voice-pool.ts` `VoicePool.start`: prepare before mutating either owner. |
| DSP arithmetic | `VoiceRenderer`, source generators, `filtered`, `echoed`, `DistanceField`, `StereoImage`, and the transcendental seam: retain arithmetic through mechanical refits. |
| Lifetime | `beginVoice`, `releaseVoice`, `echoTailFrames`, `VoiceLifetime`: reuse lifetime rules; transfer shared tail ownership to Sound in the delay slice. |
| Game host | `adapters/web/src/game-audio.ts` `GameAudio`, `RealtimeDevice`: explicit handles, disposal, and generation invalidation. |

No new workspace package, mutable shared registry, legacy loader, parallel Patch representation, or general session framework is required.

## Fit the existing six slices

1. **Contract and catalog.** Finalize cloneable definitions versus engine-private instances, catalog views, configuration preparation, seed labels, timing capabilities, and the proposed ownership references. Keep runtime behavior unchanged.
2. **Extension proof.** Add the permanent fixture and exercise real catalog-driven validation, preparation, controls, offline execution, and worklet execution. Include factory failure before pool mutation. Do not accept a fixture that only tests metadata or a private alternate renderer.
3. **Sound structure.** After issue 15 is decided, add handles, generations, pinned revisions, disposal, event-owned editor targets, and referential deletion. Preserve actual source seeds, per-Voice placement, and global accumulation. Only support lifecycle operations with executable proofs.
4. **Sources.** Move tone, noise, and FM definitions and configuration preparation into their modules. Convert authored placements, keep existing source seed labels, and delete the replaced unions, rows, and switches together.
5. **Filter.** Replace the three filter kinds with one multimode plugin. Preserve the filter arithmetic and ordering while deleting the old dispatch.
6. **Delay.** Move delay to Sound scope, adopt the declared Sound stereo topology and tail ownership, and prove the deliberate behavior change.

Correctness repairs needed to make a slice trustworthy can precede its main refit. They must carry their own regression proof. Do not let the existing atomic admission bug survive until a later plugin happens to expose it.

## Required proof

- Equal PatchIds under different events remain independently editable and audible. Duplicate ids in a loose PatchId-keyed surface are rejected.
- Delete and reinsert a layer or plugin without reviving values, links, or seed identity.
- Two retained handles on the same emitter/event remain independent. Dispose cancels queued starts and drains current Voices/tails. Rebuild invalidates handles and old commands.
- An invalid 12 kHz tone multiplied by 16 is refused before changing membership. The next render succeeds and an existing Voice is unchanged.
- Derived controls reject writes. Character overrides remain visible. Effective values identify their trigger or instance context. Remote stale edits fail.
- Future starts use prepared engine state at activation. Audit allocation under starts, releases, reports, sub-block boundaries, and ordinary plugin processing separately.
- Source seed halves and rendered samples match baseline after structural, source, and filter slices. Test interleaved membership in several Sounds, not just one Sound per trigger.
- The delay slice constructs one stereo delay for two differently placed Voices. Sound retirement waits for the composed tail. No signal silence heuristic decides retirement.
- The test plugin reaches the same execution path as shipping plugins, offline and in the real browser worklet. Lifecycle claims each have behavioral proof.

## Type sketch and verification status

The [contract sketch](audioface-phase2-contract-sketch.ts) imports the existing source types and sketches the proposed binding reference, prepared data, runtime handle, contextual control value, multiport block, and capability shapes. TypeScript rejects sending a runtime PluginInstance as cloneable preparation data, substituting VoiceId for SoundInstanceId, and passing a derived control through the authored setter. The sketch is partial and has no runtime implementation.

The baseline source review passed type checking, all 270 Node tests, lint, structure verification, and the web build. Both independent candidates supplied strict TypeScript sketches. The lead sketch passes strict TypeScript 7 checking against the real baseline contract imports. A scratch Float32 proof demonstrated that summing `[0.5, -0.5, 2^-26]` globally produces `2^-26`, while grouping the first and third samples first produces zero.

Those results ground this design. They do not prove the proposed implementation. Runtime handles, the generic plugin pipeline, resource limits, and cancellation are still design work. The independent comparison and final design checks are recorded in the companion synthesis artifact.
