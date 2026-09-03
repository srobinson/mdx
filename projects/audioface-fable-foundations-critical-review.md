---
title: Audioface foundations critical review (Fable)
type: projects
tags: [audioface, foundations, review, data-model, architecture, extensibility, scalability]
summary: Independent source-first review of the Audioface foundations at 3221511, covering data model, modularity, extensibility, scalability and the version audit, with bounded probes and a prioritized sequence.
status: active
created: 2026-09-06
updated: 2026-09-06
project: audioface-next
related: [audioface-foundation-document-spec, audioface-foundation-program-host-spec, audioface-foundation-runtime-probes-spec, audioface-foundation-decision]
confidence: medium
---

# Audioface foundations critical review

Reviewer: Fable 5.1, working alone, source first. Target: worktree `/Users/alphab/.mdx/TMP/pstack/audioface-foundations/worktrees/browser`, branch `probe/foundation-browser`, HEAD `3221511a59170b3fafaaa6924cf1a25f98a26b37`, tree clean before and after. Baseline for contrast: main `10ba9fc16cea55271c6d428c8fe64c8df0b9c354`. No source, spec or checkout was modified. Probes live in `/Users/alphab/.mdx/TMP/pstack/audioface-foundations/fable-foundations-critical-review/`. Astra's critical review, digest and probes were not read.

## 1. Verdict

The foundations hold two complete authoring and runtime models under one bus. The inherited patch path (registry rows, Patch, PatchResolver, Voice, VoicePool, MasterBus) ships the content, drives certification, and is what every adapter and the production web page speak. The new composition path (Definition, Composition, Library, compile, ProgramSpec, ProgramPreparer, ProgramHost, ProgramRuntime) is the product direction and is well tested as a protocol, but it has no production caller, covers two of the engine's five DSP stages through a curated string switch, and runs its own voice admission, budget, identity and output model beside the engine's existing ones. There is no `v2` naming and nothing was deleted since main. The duplication is structural rather than nominal.

The strongest foundation choices are real and worth protecting: the contract package as the one dependency for domains and packs, counter based seeds with labeled children, frames and linear units at the engine boundary, one transcendental door, one shared DSP arithmetic used by both paths, `ProgramSpec` as a self validating wire contract, pure document operations over an immutable library, and a structure verifier that enforces all of it.

The deepest defects are three duplicated truths: which kernels exist and what ports, regions and live parameters they have (declared in test fixtures, hardcoded in three engine files, and overriding registry rows); how a voice is admitted, budgeted and placed (VoicePool and VoiceBudget for patches, ResourceLedger and a private voice list for programs); and how a sound is edited and projected to a UI (ControlSurface over patches only). The Prepared Voice direction is premature by one step: a fixed slot bank built on the current curated kernel switch would add a fourth copy of kernel truth and a third admission mechanism. Unify kernels into registered modules and admit program voices through the engine's one pool first.

## 2. Method and evidence classes

Every file under `packages/*/src`, `adapters/*/src`, `apps/*/src`, `catalogue`, `domains/game`, `packs/skirmish`, `scripts/verify-structure.mjs`, the foundations fixtures, oracle and support harnesses was read in full. The package manifests, workspace graph and the diff from main were mapped. The design documents, host spec, runtime probes spec and the lead decision records were consulted after the source pass. The unapproved Prepared Voice draft was read to judge direction only.

Labels used below:

- **Implemented fact**: read directly from source at 3221511, with file and symbol.
- **Tested fact**: proven by an existing test, or by a bounded probe in the review directory.
- **Inference**: follows from source structure without a run.
- **Prototype limit**: a bound the specs declare as an engineering test limit.
- **Speculative**: design direction, not graded as code.

Test coverage reused rather than rerun: the lead reports 503 passing tests at 3221511; the static count of `test(` call sites is 422 because several cases are generated in loops. The 22 browser comparisons, two rates, two modes, negative controls and worker commands during a main thread stall are accepted as recorded.

## 3. Architecture as built

### 3.1 Package graph

Implemented fact. The graph declared in `scripts/verify-structure.mjs` `ALLOWED_EDGES` matches the manifests and imports: contract depends on zod only; patch, engine and measure depend on contract; content on contract and patch; control on all five; adapters and catalogue on contract and control; apps on one adapter and the catalogue; domains on contract; packs on contract, patch and one domain. Engine is imported only by control. There are no cycles. Deep imports and relative escapes are refused by the verifier.

| Layer | Packages | Lines (src) | Owns |
| --- | --- | ---: | --- |
| Vocabulary | contract | 2,400 | ids, seeds, units, patch, composition, program, host protocol, bus protocol, control schema, gates, SHA-256, curves |
| Authoring | patch | 4,700 | registry rows, patch validation, editing, recipe, resolution, voice binding, composition document, scope, links, plan, compile |
| Engine | engine | 3,600 | DSP stages, voice renderer, lifetime, pool, budget, bus, limiter, command queue, kernel preparation, program graph, kernels, runtime, values |
| Measure | measure | 900 | envelope, spectrum, fingerprint, gate verdicts |
| Content | content | 500 | pack and domain loaders |
| Control | control | 3,050 | control surface, manifest, edit, certify, audition, bus host, composition surface, program preparer, host, tickets, envelope, ledger |
| Adapters | cli, http, mcp, web | 2,200 | projections of ControlSurface; web also GameAudio, ProgramClient, worker, worklet |

### 3.2 Two pipelines under one bus

Implemented fact. Both pipelines end in `MasterBus.renderBlock` (`packages/engine/src/master-bus.ts:209`). The patch path arrives as `BusCommand` through `StampedBus`; the program path arrives through the `contribute` callback that `RealtimeBusHost` wires to `ProgramHost.render` (`packages/control/src/bus-host.ts:72`). Both share one `CommandQueue` (entries are `Correlated | ProgramScheduled`) and one worklet processor.

```
Patch path (production, all adapters)
  registry rows ─► Patch ─► validatePatch ─► resolvePatch ─► bindVoice ─► Voice
    ─► BusCommand(start) ─► BusHost/CommandQueue ─► StampedBus.prepare ─► MasterBus.prepare/activate
    ─► VoicePool(admit, class floors, steal) ─► VoiceRenderer ─► DistanceField ─► StereoImage ─► sum ─► limiter

Composition path (tests, browser proof page only)
  Definition + Composition + Library ─► expandComposition ─► compile(ENGINE_KERNELS) ─► ProgramSpec(key)
    ─► ProgramPreparer(worker) ─reserve/grant/transfer─► ProgramHost(worklet) ─► ProgramRuntime
    ─► ProgramGraph voices (private list, ledger) ─► mixdown ─► sound graph ─► output "main"
    ─► contribute: mono into L and R at unity ─► limiter
```

Production reachability, tested fact (probe-static): no file under `adapters/*/src`, `apps/*/src` or `catalogue` references `serveProgramWorker`, `ProgramDeviceOptions` or a `programs:` option. `GameAudio` constructs `RealtimeDevice` without the programs argument (`adapters/web/src/game-audio.ts:67`). The composition path is reached only from `scripts/test-support/program-host-worker.mjs` and the foundations tests.

## 4. Data model (priority one)

### 4.1 Entities reconstructed from source

| Entity | Identity | Where declared | Mutability and lifetime | Validation boundary |
| --- | --- | --- | --- | --- |
| ParameterDefinition (registry row) | `ParameterKey` `XXX-NN[.sub]` | `packages/patch/src/registry/parameters.ts` `PARAMETER_ROWS` | frozen constant | `validatePatchControlRegistry` integrity check |
| Patch | `PatchId`, `schemaVersion: 1` | `packages/contract/src/patch.ts` | immutable; edits return new frozen patch | `patchSchema` (zod) then `validatePatch` |
| Domain, DomainEvent, Scenario, Gate | string ids | contract `domain.ts`, `gate.ts`; data in `domains/*` | frozen data | `validateDomain` |
| Pack | id, `domain` id, `events: Record<eventId, Patch>`, `character` overlay | contract `pack.ts`; data in `packs/*` | frozen | `loadPack` with per patch `safeParsePatch` and resolve once |
| ResolvedPatch | none | contract `resolved.ts`; built by `PatchResolver` | ephemeral | resolver throws typed `PatchResolutionError` |
| Voice, VoiceLayer, VoiceLifetime | `VoiceId`, `VoiceSeed` triple | contract `voice.ts` | frozen once bound; lifetime state machine | `beginVoice`, `assertCyclesPerFrame`, gain asserts at construction |
| ControlManifest, ControlSnapshot | `ControlTarget {kind: "patch", id}` plus revision | contract `control.ts`; projected by `control/manifest.ts` | derived per snapshot | `parseControlEdit`, `applyControlEdits` |
| Definition | `DefinitionId`, `KernelId` | contract `composition.ts`; instances only in `test/foundations/fixtures.ts` and `packages/patch/test-support` | frozen | none at a boundary; `findDefinition` lookup |
| Composition | `CompositionId` lineage, `revision`, `minted` cursor, `schemaVersion: 1` | contract `composition.ts` | immutable snapshots; `applyDocumentEdit` returns new document | `assertCursor` only; structural checks happen at expansion |
| Library | none | contract `composition.ts` | append only via `withSnapshot`; `sealLibrary` deep freezes | cursor check only |
| ProgramSpec, ProgramSlot | `ProgramKey` SHA-256 of canonical content | contract `program.ts`; produced by `compile` | deep frozen | `validateProgram` recomputes key and demand at the receiver |
| KernelPreparation catalogue | kernel id string | `packages/engine/src/kernel-preparation.ts` `ENGINE_KERNELS` | frozen | none; keyed by literal |
| EditPlan, EditEffect, ParameterCommand | none | contract `program.ts`; produced by `planEdit` | ephemeral | `readProgramMessage` re-validates commands on the wire |
| ProgramTrigger | none | contract `program.ts` | frozen per runtime | `resolveProgramValues` range checks |
| Host protocol messages, tickets, credits | `CommandId`, `generation` | contract `program-host.ts`; state in `control/program-host.ts`, `program-preparer.ts`, `program-tickets.ts` | mutable maps | `readProgramMessage`, `readProgramReply`, envelope byte walk |
| ProgramRuntime, ProgramGraph, ProgramKernel, ProgramValue | numeric voice serial | `packages/engine/src/program-*.ts` | mutable, engine private | `bindProgramKernel` at install, trigger and every command |

### 4.2 Findings

**D1. Kernel truth is declared in three places and owned by none.** Implemented fact. A kernel's ports, region capability and live parameter keys are (a) declared per Definition in test fixtures (`test/foundations/fixtures.ts:48-92`), (b) hardcoded per kernel id in `validateSlot` (`packages/engine/src/program-preparation.ts:150-190`: `outputs` `["dry","wet"]` for echo and delay, `inputs` `[]` for tone, `live` `["DLY-10","DLY-12"]` or `["FLT-10"]`, envelope must be voice, echo and delay must be sound), and (c) dispatched by string switch in `bindProgramKernel`, `createProgramKernel` and `ProgramGraph`'s end provenance (`program-kernels.ts:78-168, 186-244`; `program-graph.ts:43-48`). Probe-static counts 25 kernel literal switch sites in the engine. `KernelPreparation` is a clean capability interface for normalize, layout and demand, but the executable half has no interface. Consequence: adding a kernel touches at least five engine and registry files plus a definition, and the two halves can disagree without a compile error. This is the single largest extensibility defect.

**D2. Parameter lifetime has three authorities.** Implemented fact. The registry declares every patch authority row `frozen` (`parameters.ts`, default in `definition.ts:110`). The fixture definitions override `FLT-10`, `DLY-10` and `DLY-12` to `live` (`fixtures.ts:63, 83`). The engine hardcodes the same three keys as the only ones allowed to be live (`program-preparation.ts:180-181`). The lead decision of 2026-09-05 chose "explicit live metadata on the curated Sound rows" through Definition authority. As built, the same `ParameterKey` carries opposite semantics in the two paths, and the engine list must be edited by hand to agree with any new definition.

**D3. The composition path cannot express the shipping content.** Tested fact (probe-noise-kernel). `ENGINE_KERNELS` holds tone, lowpass, highpass, bandpass, envelope, echo and delay. A composition placing a `noise` or `fm` definition compiles to `unknown_kernel`. Every one of the five skirmish patches uses a noise layer, and two use fm (`packs/skirmish/src/patches.ts`). The DSP exists (`createNoiseGenerator`, `fmGenerator` in `source-generator.ts`); only the curated switch omits it. This is scope not yet built, but D1 makes it expensive to build.

**D4. Two admission, budget and identity systems.** Implemented fact. Patch voices are admitted by `VoicePool.admit` with three class floors and stealing (`voice-pool.ts:41-56, 110-139`), budgeted by `VoiceBudget` in graph units, faded on steal, and identified by caller `VoiceId`. Program voices are admitted by `ProgramRuntime.trigger` (`program-runtime.ts:154-200`) into a private `Map` and `admissionOrder` array, budgeted by `ResourceLedger` in thirteen demand units, refused rather than stolen when the ledger is full, carry no class, and are identified by `program.${generation}.${commandId}` (`program-host.ts:427`). The two never meet in `MasterBus` except as summed samples. Consequence: a game that mixes a patch bed with a program gunshot has two polyphony policies and two ways to be refused.

**D5. Program output is mono at unity into both channels.** Implemented fact. `ProgramHost.render` reads only the output named `"main"` and adds it to left and right unchanged (`program-host.ts:500-509`). The voice path places every voice through constant power pan, so a centred voice contributes 0.707 per channel (`stereo-image.ts:76-77`). Inference: the same mono signal is about 3 dB louder through the program path, and program sounds have no listener, pan, width or distance. The spec defers spatial routing; the level mismatch is a consequence of doing so at the sum.

**D6. Program identity is bound to placement naming by default.** Tested fact (probe-key-identity). `compile(PAIR)` and `compile(PAIR_FLAT)` produce different keys unless the flat twin is compiled with `SEED_MAP`; the seed label defaults to the placement key (`compile.ts:138`) and enters `programKey` (`program.ts:270`). Transfer survivors are matched by placement key as well (`plan.ts:191-202`). Consequence for a Studio: renaming or re-nesting a brick changes the program's identity and defeats state transfer even when the audio is unchanged. The spec accepts this (document spec section 2). It is a coupling to name now, because a per Sound seed map held by the worker is the only escape and it is preparation data rather than authored identity.

**D7. A carried field with no reader.** Implemented fact. `CompiledModulation.seedLabel` is built as `${seedLabel}/${modulation.id}` (`compile.ts:279`) and hashed into the key, but the runtime derives the jitter seed as `childSeed(childSeed(root, slot.seedLabel), modulation.id)` (`program-values.ts:102`). Probe-static shows no engine reader of the field. Two encodings of one seed; a future reader would draw a different stream.

**D8. The same registry row jitters differently in the two paths.** Inference from source. The patch resolver seeds a connection as `childSeed(childSeed(rootSeed(voiceSeed), "patch/<id>"), "connection/<id>")` (`patch-resolution.ts:71, 219`). The program path seeds a modulation as `childSeed(childSeed(root, slotSeedLabel), modulationId)`. A pack sound migrated to a composition will not reproduce its takes. This matters the day packs become libraries (document spec section 5 plans exactly that).

**D9. Two trigger shapes.** Implemented fact. `TriggerContext` carries id, velocity, variation, trigger parameters, output parameters and a `VoiceSeed` triple (`resolved.ts:4-13`). `ProgramTrigger` carries a `Seed` pair, velocity and variation (`program.ts:16-20`). Listener and output rows do not exist on the program side.

**D10. Optional field bags where discriminants belong.** Implemented fact. `ProgramOutcome` has three `applied` variants told apart by `"voice" in outcome` and `"reclaimed" in outcome` (`program-host.ts` contract lines 90-92; checked at `program-preparer.ts:396-399`). The preparer's `Sound` record holds five independently nullable fields (`applied`, `planningRevision`, `pending`, `latest`, `closing`), and `ProgramTicket` holds `outcome`, `cancellation`, `cleanup`, `owner`, `provisional`. Illegal combinations are representable and are excluded by roughly a hundred protocol tests rather than by types. The typescript skill's rule applies: model the legal states as a union.

**D11. Composition has no boundary parser.** Implemented fact. `Patch` has `patchSchema` (zod, `contract/schema/patch.schema.ts`). `Composition` and `Library` have none; `sealLibrary` checks cursors and freezes (`library.ts:17-20`). Untrusted composition JSON is accepted into a library and refused only at expansion. A Studio or import boundary has nothing to call.

**D12. Duplicated declarations in barrels.** Implemented fact (probe-static). `Waveform` is declared in `contract/source.ts:3` and again as a literal union in `patch/patch-recipe.ts:28`, both exported. `VoiceRequest` is declared with different shapes in `contract/control.ts:197` and `patch/voice-binding.ts:51`, both exported from package barrels; `control/event-voice.ts` imports one and calls a function typed by the other. `SUMMED = "every subject, summed"` is declared in `control/certify.ts:26` and re-declared in `adapters/web/report.ts:89` to detect summed scenarios by string match: a display string used as a discriminant across a package boundary. `UINT32` is declared in `seed.ts` and `digest.ts`; string comparators `compare` and `compareKeys` in `compile.ts` and `digest.ts`. Echo range checks live in `layer-echo.ts` `share()` and again inline in `bindProgramKernel` (`program-kernels.ts:151-163`).

**D13. Two version integers per kernel.** Implemented fact. `KernelPreparation.version` and `StateLayout.version` are both 1 for every kernel and are compared together in `validateSlot`. `ProgramSlot` carries both. One of them is enough; see section 8.

**D14. What holds together well.** Implemented and tested fact. Values live inside their placement and leave with it (`removePlacement` cascades links, modulations and exposures, `document.ts:249-275`). Ids are minted from a monotonic cursor and never reused (`mintPlacementId`, tests "the cursor steps over an authored id"). Pins are immutable and a library edit cannot move a pinned sound (test 4). `ProgramSpec` is deep frozen, JSON safe, structured cloned across realms and re-validated at the receiver including key and demand recomputation (`validateProgram`, `program-preparation.ts:107-148`). Transferred backing is checked for aliasing, size and detachment (`validateProgramStorage`). Seeds are random access with no retained state, so block slicing cannot move a sample (tests on ragged spans, oracle equality).

## 5. Modularity and layout

**M1. Control is two subsystems in one package.** Implemented fact; tested fact (probe-worker-bundle). The patch control surface, certification and audition (about 1,250 lines) share a package and barrel with the program realm (preparer, host, tickets, envelope, ledger, composition surface, about 1,750 lines). `adapters/web/src/worker.ts` imports `ProgramPreparer` from the barrel, so the worker bundle carries every control file plus seven measure files and three content files (736 KB unminified for the proof worker). Ownership is also blurred: `bus-host.ts` constructs `ProgramHost`, so the realtime scheduler package depends on the program realm.

**M2. `packages/patch` owns three things.** Implemented fact. Registry (900 lines), patch model and resolution (1,500 lines), and the composition compiler (1,900 lines under `src/composition`). The compiler imports two registry functions (`valueInRange`, `defaultParameterValue`). The name no longer says what the package produces, which the placement rule in the arena decision forbids.

**M3. Definitions live only in tests.** Implemented fact. The only `Definition` instances are in `test/foundations/fixtures.ts` and `packages/patch/test-support`. `test/foundations` is an ungoverned root (`verify-structure.mjs` `UNGOVERNED_ROOTS`) that reaches into packages by deep relative imports. The contract comment says "a definition is catalogue code"; no catalogue package declares one. The worker's `library` factory has no production implementation.

**M4. Near limit files with dense state.** Implemented fact. `scope.ts` 620, `program-preparer.ts` 603, `program-host.ts` 587 lines against the 700 cap. Functions stay under 150 lines, but `ProgramPreparer.receive` (98 lines) and `settle` (40 lines) coordinate six maps and five nullable fields. Adding the Prepared Voice bank fields to these files as drafted would push both past the limit or force a split under pressure.

**M5. Forwarding depth on the patch path.** Implemented fact. `BusHost` wraps `StampedBus` wraps `MasterBus`; `StampedBus` adds peak meters and a listener override. Three layers sit between `HostMessage` and `VoicePool.admit`. Acceptable with the stated clock reasons, but `StampedBus` has one production caller and could fold into either neighbour.

**M6. Adapters speak one surface.** Implemented fact. CLI, HTTP and MCP project `ControlSurface` only. There is no `ControlManifest` projection for compositions (`manifest.ts` walks `Patch`), so no adapter and no bench can show a composition.

**M7. Boundaries worth preserving.** Implemented fact. Domain vocabulary cannot enter the foundation (verifier reads every domain's ids and greps `packages`). Measure never sees a name (`ScenarioSignals` positions, `certify.ts` `label`). The limiter and pool names cannot leave the engine. Transcendentals go through one module so a table can replace them. The engine never imports the patch model. These are elegant and enforced, and none of them is threatened by the recommendations below.

## 6. Extensibility walked through

| Scenario | Data or registration only? | Touchpoints today | Notes |
| --- | --- | --- | --- |
| New DSP kernel (program path) | No | `kernel-preparation.ts` (+1 entry), `program-kernels.ts` (Binding union, bind case, create case), `program-preparation.ts` `validateSlot` (region, ports, live keys), `program-graph.ts` (end provenance if source like), registry `parameters.ts` rows and `SOURCE_DEFINITIONS`/`PROCESSOR_DEFINITIONS` (integrity check `supportIssues` refuses an unbacked layer row), a Definition, tests | Five engine and registry files before the definition. Noise and fm are the concrete case (D3). |
| New processor (patch path) | No | contract `patch.ts` type lists, registry rows, processor and structure rows, `voice-binding.ts` (filters versus echoes split), contract `voice.ts` `VoiceLayer` field, `voice-renderer.ts` chain, `voice-budget.ts` demand, `manifest.ts` member types | About eight files. Curated as well. |
| Compose and reuse a nested Sound | Yes for racks | `insert` reference, `exposure`, `repin`, `copyComposition` | Tested. Only racks are referenceable; a Sound cannot reference a Sound; exposures are single level names; regions are fixed to voice and sound. |
| Change a parameter or control mapping | Partly | `modulate` edit, `set` with ramp; classification by `planEdit` | Live commands exist for three keys (D2). A command to any parameter that is a modulation target or source is refused (`program-runtime.ts:244-257`), so a knob mapped through a modulation needs a cold reinstall. |
| Add an emitter, spatial or output adapter | No | Program path: `ProgramHost.render` reads `"main"` and sums dual mono; the `observe` hook indexes worklet outputs by iteration order (`worklet.ts:42-46`), which shifts when the first Sound closes. Patch path: one live listener for every voice once a `listener` command arrives (`stamped-bus.ts:39, 60`), per voice placement only at trigger time | Neither path has an emitter concept. Adding one touches `BusCommand`, `StampedBus`, `MasterBus`, `GameAudio` and the program path separately. |
| Studio consumer, export, persistence | Partly | `Composition` and `Library` are plain JSON; `planEdit` and `CompositionSurface` are pure and revisioned | Missing: composition schema (D11), manifest projection (M6), library retention policy (S3), a governed Definition catalogue (M3). The shapes allow all four; none exists. |

Honest capability statement. The composition document layer is a real Lego set for racks: reusable, pinned, versioned, copyable, cascaded on removal, and compiled to one canonical program. The kernel layer beneath it is a fixed set of seven curated bricks with hand maintained edges. The runtime beneath that is a second engine beside the first.

## 7. Scalability

All statements below are structural. No device, p99, dropout, heap or GC claim is made.

**S1. Trigger bursts are refused on the program path.** Tested fact (probe-burst). With `PROGRAM_HOST_LIMITS.voicesPerWindow` 1 (`contract/program-host.ts:23`) enforced by `CommandQueue.checkWindow` (`command-queue.ts:137-166`), four triggers stamped on one frame yield one `applied` and three `refused: Audioface commands per render window capacity exceeded.` A trigger 128 frames later is also refused because the window bound is inclusive. The patch path admits 32 same frame starts and correlates refusals for 100 (tests "32 interface starts leave the bed floor available", "100 host starts have correlated refusals"). Prototype limit by declaration; a product blocker for gameplay until removed.

**S2. Resident caps.** Prototype limit. Two Sounds, one candidate per Sound, four programs, 32 program voices with no stealing (`program-runtime.ts:158` throws when the ledger refuses), 256 ordinary tickets and 768 records per generation with no retirement of settled tickets (`program-tickets.ts:54-58`; test "host edit exhaustion" shows the 257th edit throws). A session that performs more than 256 host operations must end its generation. The structural path is retirement of settled and acknowledged tickets, which the host spec deliberately excluded to keep replay idempotent.

**S3. Library growth is unbounded.** Tested fact (probe-library-growth). Two hundred accepted edits grow the library from 2 to 202 full snapshots, 212 KB of JSON, with one snapshot pinned. `latestSnapshot` and `findSnapshot` scan the array (`library.ts:36-52`), and expansion calls them per placement. Live editing sessions need an index by lineage and a pin aware retention rule.

**S4. Command application cost and where it runs.** Inference from source. `ProgramRuntime.command` re-resolves every slot, re-binds every installed slot, and re-binds every kernel of every resident voice through `validateResidents` (`program-runtime.ts:230-297`); `bindProgramKernel` constructs generators and filter stages for validation (`program-kernels.ts:93, 118`). Program commands are applied at their frame inside `queue.drain` during `BusHost.render` (`bus-host.ts:222-234, 262`), so this work runs in the process callback and scales with slots times voices. Installation validation, including the pure JavaScript SHA-256 over canonical program JSON, runs in the worklet's message task on the rendering thread (`worklet.ts:117-120` pump), paced to one preparation per 128 frame window. The host spec acknowledges both; neither is measured.

**S5. Sample serial kernel execution.** Inference. `ProgramGraph.tick` runs every kernel once per frame through block DSP called with a length of one (`program-graph.ts:71-77`; `program-kernels.ts:189-190, 203-207`), with per sample `Map.get` value reads and, for echo, `framesFromMilliseconds` per sample (`program-kernels.ts:237`). `reclaim()` walks the voice list every frame (`program-runtime.ts:313`). The patch path renders per voice per block. Per frame work in the program path is therefore an order of magnitude more function calls than the same graph on the patch path. Measurement is required before any deadline claim; the structure is the point.

**S6. Noise cost by construction.** Inference. Pink, brown and blue noise draw sixteen hashed octaves per sample per layer (`noise-source.ts:58-81`). This is a deliberate trade for loop freedom and random access, and every shipping skirmish sound is noise led. It is the likely dominant CPU term of the patch path and should be the first thing measured.

**S7. Determinism.** Tested fact. Sum order is canonical (seed label then port), voice mix uses admission order independent of storage (test "Voice mix uses admission order"), seeds are counter based, and nested, flat and hand wired oracle renders match sample for sample at two rates. Cross browser bit identity is explicitly not promised (`transcendental.ts`).

## 8. Version and layer audit

Tested fact (probe-static): no tracked source file contains `v2`, `V2`, `compat`, `deprecat` or `legacy` outside one test title ("the pool has no legacy Voice start admission path", `packages/engine/test/voice-pool.test.mjs:24`). Nothing was deleted between main and 3221511; 113 files changed, 15,151 insertions, 591 deletions. The `.v2.candidate.md` and `.v2.draft.md` files are review artifacts in the task directory, not source.

Version fields and their justification:

| Field | Location | Role | Verdict |
| --- | --- | --- | --- |
| `Patch.schemaVersion: 1` | `contract/patch.ts:78`, checked by zod | format identity for persisted packs | justified |
| `Composition.schemaVersion: 1` | `contract/composition.ts:109` | format identity | justified, but unchecked because no schema exists (D11) |
| `KernelPreparation.version`, `ProgramSlot.version` | `program.ts:116, 169` | kernel implementation compatibility for state transfer | justified; all 1 |
| `StateLayout.version` | `program.ts:59` | layout compatibility | redundant with the kernel version (D13) |
| `generation` | host protocol | transport epoch | justified |

Old and new host paths. Both `HostMessage`/`WorkletMessage` and `ProgramHostMessage`/`ProgramReply` reach one worklet processor through two ports, and a third union (`WorkerControl`/`WorkerNotice`) drives the worker. The runtime holds two voice models (D4). This is dual architecture inside the runtime, arrived at honestly as a probe and never named as such in source. It is coherent temporary debt only if the retirement of one model is scheduled; today nothing schedules it, and the unapproved Prepared Voice draft keeps "legacy VoicePool, MasterBus, and GameAudio unchanged and out of scope", which would extend the split.

Migration and deletion opportunities that compatibility does not protect: `patch-recipe.ts` and `patch-editing.ts` leave with the pack to library migration (document spec section 7); `StampedBus` can fold; `StateLayout.version` can go; `CompiledModulation.seedLabel` can go or gain a reader; the duplicated types in D12 can go now.

## 9. Correctness candidates noticed in passing

Each is a candidate for triage, with its caveat.

1. `packages/control/src/program-host.ts:505-508` Program output summed at unity into both channels. Impact: about 3 dB louder than a centred patch voice for the same mono signal; a cross path null test would fail. Caveat: spatial routing is explicitly deferred.
2. `packages/patch/src/composition/compile.ts:279` and `packages/engine/src/program-values.ts:102` Two encodings of the modulation seed; the carried one is never read. Impact: latent divergence, none today.
3. `adapters/web/src/worklet.ts:43` and `packages/control/src/program-host.ts:500-505` Output channel chosen by Sound iteration index. Impact: a listener on output 2 hears a different Sound after the first Sound closes. Caveat: proof only hook.
4. `packages/engine/src/command-queue.ts:153` Window test `queued.frame - first <= width` is inclusive, so a 128 frame window spans 129 frames (probe-burst, spaced trigger 0 refused). Caveat: prototype cap that the Prepared Voice draft removes.
5. `packages/patch/src/voice-binding.ts:51` and `packages/contract/src/control.ts:197` Two exported `VoiceRequest` types with different shapes. Impact: a caller importing the wrong one gets a confusing type error rather than a wrong voice; still a naming defect.

## 10. Priorities

Justified by cost of change, correctness exposure and extensibility.

### Must fix before further build

**P1. One kernel authority.** Replace the curated switches with a registered kernel module: `{ id, version, inputs, outputs, scope, liveKeys, normalize, stateLayout, demand, bind, create }` in `packages/engine`, registered once in `ENGINE_KERNELS`, with `validateSlot`, `bindProgramKernel`, `createProgramKernel` and `ProgramGraph` end provenance reading the module instead of the kernel id. Derive Definition ports and scope from the module so a definition cannot disagree with the engine. Then add noise and fm modules over the existing generators. Cost now: small, seven kernels, one package. Cost later: every kernel added and every Prepared Voice reset rule hardens the switch.

**P2. One lifetime authority.** Either the kernel module declares which of its keys are live, or the registry row does, and the fixture overrides and the engine's hardcoded list are deleted. Frozen must stay captured at scope start as decided.

**P3. A governed Definition catalogue and a Composition boundary.** Move definitions out of `test/foundations` into a package the verifier governs (a `kernels` or `definitions` entry under `catalogue/` or `packages/`), and give `Composition` and `Library` a zod schema and a `loadLibrary` that seals at the boundary. Until this exists the composition path has no production entry.

**P4. Decide the voice seam before adding a voice bank.** The engine should have one definition of a voice: a lifetime plus a mono render over a block, admitted by `VoicePool` with a class, budgeted by one ledger, placed by `DistanceField` and `StereoImage`, and summed once. Program voices should be admitted through that pool rather than a private list, and `ProgramHost.render` should stop summing dual mono. This merges `ResourceLedger` and `VoiceBudget` into one demand account and gives program sounds stealing, class floors and placement for free. This is a design decision for the owner; it is listed as a must because every host feature built before it deepens D4.

### Near term cleanup

- Split `packages/control` into control (surface, certify, audition, bus host) and host (preparer, host, tickets, envelope, ledger, composition surface); the worker imports host only (M1).
- Move `src/composition` out of `packages/patch` into its own package or rename the package to say what it owns (M2).
- Delete the duplicates in D12; give `CertifiedScenario` a `mix` field so the report stops matching a display string.
- Drop `CompiledModulation.seedLabel` or make the runtime read it (D7). Drop `StateLayout.version` (D13).
- Model `ProgramOutcome`, the preparer's `Sound` and `ProgramTicket` as discriminated unions (D10).
- Index the library by lineage and add pin aware retention (S3). Retire settled and acknowledged tickets within a generation (S2).
- Fold `StampedBus` into `MasterBus` or `BusHost` (M5).

### Product and future decisions

- Voice policy for program sounds under load: steal within class as the patch path does, or refuse.
- Emitter and spatial model, and named output routing for both paths (D5, extensibility row 5).
- Persistence format and Studio manifest for compositions (M6, D11).
- Pack to library migration: `Pack.events` mapping to composition pins, and the seed labeling change it implies (D8).
- Whether seed labels become authored placement data so Studio refactors keep identity (D6).
- Sonic transition policy and shipping budgets, unchanged from the specs.

## 11. Prepared Voice direction

Speculative, judged as direction only; the drafts are unapproved and not implemented. The v2 draft provisions a fixed per Sound bank of prepared graphs with a slot state machine, reservation tokens, an aggregate demand formula, and a reset list that enumerates every curated kernel's internal fields (tone phase, biquad history, tuned cutoff, coefficients). It removes `voicesPerWindow`, which probe-burst shows is the burst blocker, and the per trigger ledger charge. Both removals are right.

It is premature by one step. Building the bank on the current kernel switch puts kernel state knowledge in a fourth place (D1) and adds a third admission mechanism beside `VoicePool` and the ledger (D4), while declaring the engine's pool out of scope. Do P1 first so each kernel module owns `reset` and `transfer` of its own state, and make P4's decision so the bank is "prepared graphs waiting in the one pool" rather than a parallel pool. The bank itself then becomes a small change.

## 12. Smallest coherent next sequence

1. Kernel modules (P1) with no behaviour change: existing 22 comparisons, oracle and null tests must stay green. Delete the switch sites.
2. Noise and fm kernel modules; a skirmish shaped composition compiles and renders; extend the oracle with one noise voice.
3. Lifetime authority (P2); delete fixture overrides and the engine list.
4. Definition catalogue package plus composition schema and library loader (P3); the worker's library factory gets a production implementation.
5. Voice seam decision (P4) recorded, then program voices admitted through `VoicePool` and placed through the image; `ProgramHost.render` routes named outputs; one ledger.
6. In parallel and independent of the above: control and host package split, duplicate deletion, library retention, ticket retirement, discriminated unions.
7. Only then revisit Prepared Voice as prepared graphs in the pool.

## 13. What to keep, refactor, delete, rethink

**Keep.** Contract vocabulary, seeds and units; engine DSP stages and the transcendental seam; `VoicePool`, `VoiceBudget` and lifetime; measure, certify, domains and packs as data; composition document operations, library, expansion, `compile`, `planEdit`; `ProgramSpec` with receiver validation; the reserve, grant and transfer protocol's ownership rules; `verify-structure.mjs`.

**Refactor.** `program-kernels.ts`, `program-preparation.ts` and `program-graph.ts` into kernel modules; control into control and host; patch into registry, patch and composition; the protocol state records into unions; `StampedBus` into a neighbour.

**Delete.** Duplicate `Waveform`, `VoiceRequest`, `SUMMED`, `UINT32`, comparator and echo range checks; `CompiledModulation.seedLabel` unless read; `StateLayout.version`; `voicesPerWindow` and `preparationsPerWindow` once the bank or pool admission replaces them; `patch-recipe.ts` and `patch-editing.ts` with the pack migration.

**Rethink.** Two voice models under one bus; placement key bound identity for a Studio; the program path's dual mono output; whether the worker owns the library or a persistence boundary does.

## 14. Probes

Directory: `/Users/alphab/.mdx/TMP/pstack/audioface-foundations/fable-foundations-critical-review/`. Each probe imports the worktree by absolute path and writes nothing into it. Node v25.9.0.

| Probe | Command | Result |
| --- | --- | --- |
| Burst | `node probe-burst.mjs` | open applied; same frame triggers: 1 applied, 3 refused "commands per render window capacity exceeded"; spaced 256 frame triggers: first refused (inclusive window), next two applied at frames 384 and 640; runtime voices 3 |
| Kernel coverage | `node probe-noise-kernel.mjs` | `ENGINE_KERNELS` = tone, lowpass, highpass, bandpass, envelope, echo, delay; compile with noise and fm definitions refuses `unknown_kernel` at `n` and `f` |
| Library growth | `node probe-library-growth.mjs` | snapshots 2 to 202 after 200 accepted edits; 212,726 JSON bytes retained; 1 snapshot pinned |
| Key identity | `node probe-key-identity.mjs` | nested key `8094404a…`; flat unmapped `6f5fb926…` (differs); flat mapped equals nested; seed labels default to placement keys |
| Worker bundle | `node probe-worker-bundle.mjs` | 736,485 bytes; files by package: contract 29, engine 25, control 22, patch 21, measure 7, content 3; all 22 control files present including certify and audition |
| Static audit | `./probe-static.sh` | HEAD 3221511 clean; one `legacy` hit in a test title; no program path production callers; definitions only in test support; 25 kernel literal switch sites; duplicates as listed in D12; 422 static test call sites |

Logs: `probe-*.log` beside each script.

## 15. Uncertainty

- Performance statements (S4, S5, S6) are structural inferences; nothing here was timed and no device budget is implied.
- The 503 test count is the lead's; the static count of 422 call sites is mine and does not contradict it.
- D8 (seed divergence between paths) is read from source and not exercised; it becomes observable only when a pack sound is expressed as a composition, which D3 currently prevents.
- The Prepared Voice judgement is about direction; the drafts were not graded as code.
- Browser behaviour is taken from the recorded checkpoint evidence; no browser was rerun for this review because no source changed.

## 16. Done line

`review: ready sha=3221511a59170b3fafaaa6924cf1a25f98a26b37 model=fable-5.1 data-model=two-authoring-models-three-kernel-truths architecture=clean-edges-dual-runtime extensibility=curated-kernels-racks-good scalability=burst-refused-history-unbounded version-audit=no-v2-dual-host-paths priorities=P1-kernel-modules,P2-lifetime,P3-catalogue+schema,P4-voice-seam report=/Users/alphab/.mdx/projects/audioface-fable-foundations-critical-review.md digest=/Users/alphab/.mdx/TMP/pstack/audioface-foundations/fable-foundations-critical-review-digest.md tree=clean`
