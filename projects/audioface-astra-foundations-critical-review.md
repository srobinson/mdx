---
title: Audioface critical foundations review
type: projects
tags: [audioface, foundations, architecture, data-model, code-review]
summary: Source assessment at 3221511 with twelve focused behavioral probes, prioritized model corrections, and a bounded path to one runtime architecture.
status: active
created: 2026-09-06
updated: 2026-09-06
project: audioface-next
confidence: high
related: [audioface-foundation-document-spec, audioface-foundation-program-host-spec, audioface-foundation-runtime-probes-spec]
---

# Audioface critical foundations review

The package boundaries and much of the DSP are worth keeping. The data model and runtime capabilities still disagree in several important places. I would pause the prepared Voice contract progression, correct those disagreements, and then build prepared Voices against the corrected model. A broad rewrite would discard useful work. Continuing to add consumers now would make the remaining model changes more expensive.

There are no `V2` source variants at this checkpoint. There are two substantial execution and authoring paths, however. The existing applications use `Patch` and fixed `Voice` rendering. The composition foundations use `Composition`, `ProgramSpec`, and `ProgramRuntime`. Their shared DSP and scheduler reduce duplication, but their parameter semantics and lifetime rules already differ. Removing version suffixes would do nothing to resolve that architectural split.

The strongest evidence against treating this as a finished foundation is behavioral. A declared gain conversion produces the wrong direction of change. A legal live edit is planned as a command that the runtime refuses. One document cannot have two independent retained Sound instances. Library pin identity can depend on array order. These are better next tasks than more draft refinements around a Voice bank.

## Review boundary and evidence

Reviewed source SHA `3221511a59170b3fafaaa6924cf1a25f98a26b37`, branch `probe/foundation-integrated`, in `/Users/alphab/.mdx/TMP/pstack/audioface-foundations/worktrees/integrated`. The source tree was clean before and after review. Git comparison starts at `10ba9fc16cea55271c6d428c8fe64c8df0b9c354`.

I mapped source and traced its principal model, compiler, host, adapter, and DSP paths before reading current specifications and prior review evidence. The structural scan covers every tracked production source file. This is an architectural review with focused behavioral checks, rather than a claim that every line of the repository received exhaustive bug analysis.

Evidence labels used below distinguish new probe results, observed source behavior, inferred design consequences, and documented prototype limits. The prepared Voice drafts are unapproved documents and contribute no implemented capability to this assessment.

Two external programs generated the evidence:

```sh
node /Users/alphab/.mdx/TMP/pstack/audioface-foundations/astra-foundations-critical-review/source-audit.mjs
node /Users/alphab/.mdx/TMP/pstack/audioface-foundations/astra-foundations-critical-review/behavior-probes.mjs
```

Both exited 0. The second contains twelve focused cases using the actual compiler, runtime, and cloned protocol test helpers. Its assertions verify the reported observations, including failures in the reviewed implementation. An exit of 0 does not mean those implementation behaviors are desirable.

The [structural evidence](/Users/alphab/.mdx/TMP/pstack/audioface-foundations/astra-foundations-critical-review/source-audit.json) records 153 tracked production source files and 18,604 lines. The largest are `scope.ts` at 620, `program-preparer.ts` at 603, and `program-host.ts` at 587. The syntax scan found no functions over 150 lines and no static runtime import cycles, including barrel reexports. Dynamic module loading and runtime object reference graphs are outside that cycle calculation. A broader version naming scan covers 254 tracked code files, including tests and scripts.

The [behavioral evidence](/Users/alphab/.mdx/TMP/pstack/audioface-foundations/astra-foundations-critical-review/behavior-probes.json) records the values cited below. No build, full test suite, or browser campaign was rerun. The independent [3221511 browser correction review](/Users/alphab/.mdx/TMP/pstack/audioface-foundations/runtime-host-browser-corrections-review-digest.md) records the existing 503 test gate, 22 browser cases at two sample rates in headed and headless Chrome, five existing event comparisons, ten negative controls, and worker commands during the main thread stall. I inspected the relevant proof source to determine what those results establish.

## The implemented model

| Entity | Identity and authority | Lifetime and representation |
| --- | --- | --- |
| Definition | `DefinitionId` refers to catalogue data, `KernelId` selects engine code | Parameters, scope and ports are declared separately from executable kernel behavior. Library references definitions without a definition revision. |
| Composition | `CompositionId` plus integer revision | Immutable snapshot of placements, links, modulations, exposures and ports. `minted` prevents reuse of generated placement IDs. |
| Placement | Local `PlacementId`, flattened `PlacementKey` | Owns its authored values. A definition placement names a definition. A reference pins a rack revision and overrides its exposures. |
| Library | Arrays of definitions and composition snapshots | `sealLibrary` freezes input in place. `withSnapshot` appends a snapshot and shares unchanged objects. No collection or persistent storage exists. |
| Program | `ProgramKey` hashes normalized content and execution profile | One serializable `ProgramSpec`. Placement references are canonicalized to ordinals for hashing. Demand and compatibility are validated separately. |
| Prepared installation | Command ID, generation, exact resource demand | Sender backing becomes transferred backing. Receiver validates and constructs a candidate runtime. Credit stays reserved through residency. |
| Retained Sound | Successful open command, called `openedBy`, plus a composition ID | Receiver owns one `ProgramRuntime`, applied revision, resource credit and close state. Sender currently permits one Sound per composition ID. |
| Program Voice | Trigger command, wire `VoiceId`, private runtime integer | Mutable graph, captured values, start and release frames. Currently allocated at trigger application and reclaimed after its declared end. |
| Desired state and effect | Composition revision and planner result | `CompositionSurface.apply` commits documents. `ProgramPreparer` tracks desired, applied and command planning revisions separately. |
| Outcome | Command ID and generation | Shared ticket bookkeeping reserves terminal cleanup records. The worker settles caller promises. Main has separate latches for worker failure. |
| Existing event path | Domain event, pack, patch ID, take and Voice ID | `Pack.events` still embeds Patches. `eventVoice` resolves a Patch to a fixed Voice, with event class and listener fields. |

The primary definitions are in [composition.ts](/Users/alphab/.mdx/TMP/pstack/audioface-foundations/worktrees/integrated/packages/contract/src/composition.ts:36), [program.ts](/Users/alphab/.mdx/TMP/pstack/audioface-foundations/worktrees/integrated/packages/contract/src/program.ts:166), and [program-host.ts](/Users/alphab/.mdx/TMP/pstack/audioface-foundations/worktrees/integrated/packages/contract/src/program-host.ts:37).

The intended separation between document revision, installed program identity, Sound lifetime, and trigger identity is good. A live command does not change the installed program's key. The applied revision tells the caller how far that program's live state has advanced. Calling that arrangement stale hashing would miss the deliberate difference between immutable program content and mutable instance state.

Placement values living with their owner are a substantial improvement over the existing flat `Patch.parameters` map. `removePlacement` removes related links, modulations and exposures, while the mint cursor preserves identity. Pinned racks make reuse explicit and stop a library edit from silently changing another document. The compiler also checks scope crossings, reference cycles, link cycles and modulation dependencies.

There is no database model to evaluate. The unresolved persistence question is which validated snapshots and definitions an exported library owns, and how a consumer resolves their exact identities. The current arrays and plain objects are sufficient to explore that contract, but do not enforce it completely.

## Boundaries worth preserving

The dependency direction is clear and currently acyclic. Contract owns shared vocabulary. Patch compiles and classifies authored changes. Engine supplies preparation capabilities and DSP. Control is the composition root that can see both. Platform adapters depend on control and contract. Domains describe events and gates, packs supply content, and the catalogue chooses what a build ships. `scripts/verify-structure.mjs:ALLOWED_EDGES` encodes that arrangement.

The main runtime chain is:

```text
Library -> CompositionSurface -> planEdit / compile -> ProgramSpec
                       worker ProgramPreparer
                                |
                      direct transferred port
                                |
ProgramHost -> existing CommandQueue -> ProgramRuntime -> ProgramGraph
                                                        |
                                                  shared DSP stages
                                                        |
                           per Sound outputs -> MasterBus -> limiter
```

`CommandQueue` remains the only future event scheduler. Program contribution enters `MasterBus` before its limiter. The new path reuses `toneGenerator`, `createFilterStage`, `envelopeAmplitudeAt`, `createEchoLine`, seed functions and curve arithmetic. Those are real shared implementations, not matching copies.

The direct worker/worklet port is also a useful boundary. Main owns device lifetime and caller latches. The worker owns documents and compilation. `ProgramPort` owns native posting and detachment accounting. `ProgramHost` owns receiver resources and application. The sender does not manufacture an applied result from a timeout. Preserving those owners matters more than reducing their file counts.

The two large control classes deserve explicit lifecycle types as they grow. Their current nullable fields are not evidence of a bug by themselves. Keep settlement, cancellation, refunds and generation teardown together until focused tests permit a coherent split. A generic transport framework or another queue would add complexity here.

## Prioritized findings

### F1. Parameter resolution metadata is lost before execution

**Must fix before further foundation build. Tested behavior and source defect.**

`ParameterDefinition.resolution` declares conversion and resolution range. `compileSlot` carries initial values and lifetime flags but drops that resolution metadata. `resolveProgramValues` applies curves directly to authored values and checks only that results are finite. The existing `PatchResolver.resolveAddress` converts to the declared resolution domain, applies connections, clamps, and converts back.

The probe starts `AMP-01` at `-6 dB` with a multiplication factor of `0.5`. The program resolver returns `-3 dB`, increasing gain. The parameter's declared linear conversion gives about `-12.0206 dB`, reducing gain. Shared `applyCurve` arithmetic alone does not establish shared parameter semantics.

Source: [compileSlot](/Users/alphab/.mdx/TMP/pstack/audioface-foundations/worktrees/integrated/packages/patch/src/composition/compile.ts:285), [resolveProgramValues](/Users/alphab/.mdx/TMP/pstack/audioface-foundations/worktrees/integrated/packages/engine/src/program-values.ts:83), and [PatchResolver.resolveAddress](/Users/alphab/.mdx/TMP/pstack/audioface-foundations/worktrees/integrated/packages/patch/src/patch-resolution.ts:175).

Carry the minimum authoritative resolution metadata into the compiled parameter representation and share the pure conversion policy. Do not make engine import patch. If composition modulation is intentionally redefined in authored units, that requires an explicit contract decision and different truthful metadata. No such decision was established by the reviewed specs. The current cutoff jitter fixture does not exercise decibel conversion.

### F2. The planner emits a command the runtime knows it cannot apply

**Must fix before further foundation build. Tested behavior and classifier defect.**

`commandsFor` accepts a changed live row when normalized configuration stays equal. It does not classify dependencies captured by modulation. `ProgramRuntime.command` explicitly refuses any command targeting such a dependency.

Through the actual cloned host path, editing `PAIR_JITTERED` cutoff to 2400 produces `accepted: true`, effect `command`, then terminal refusal `Audioface command to a captured modulation dependency refused.` Desired revision is 1 and applied revision remains 0. The protocol reports that divergence correctly, but the effect classification is predictably wrong before submission.

Source: [commandsFor](/Users/alphab/.mdx/TMP/pstack/audioface-foundations/worktrees/integrated/packages/patch/src/composition/plan.ts:140) and [ProgramRuntime.command](/Users/alphab/.mdx/TMP/pstack/audioface-foundations/worktrees/integrated/packages/engine/src/program-runtime.ts:248).

Put the captured dependency rule in the shared classification contract. Choose preparation or an explicit planning refusal under current capabilities. This does not require implementing continuous modulation. Runtime checks should remain as protection against stale or invalid commands.

### F3. Authored lineage is coupled to a single live Sound

**Must settle before expanding the Voice bank API or instance consumers. Tested model restriction.**

`ProgramPreparer.sounds` is a `Map<CompositionId, Sound>`. Open rejects an already present composition. The receiver is keyed by `openedBy`, but independently enforces composition uniqueness at packet admission and activation. Trigger, release and close in the worker API still address a composition.

The probe opens one Sound and then tries to open the same composition with another trigger context. The second request is refused with only one of two Sound slots occupied. Two emitters cannot share an authored Sound while maintaining independent persistent effect state. Copying the document would create unnecessary editing and persistence identities merely to obtain another runtime instance.

Source: [ProgramPreparer.sounds and open](/Users/alphab/.mdx/TMP/pstack/audioface-foundations/worktrees/integrated/packages/control/src/program-preparer.ts:74), [ProgramHost.acceptPacket](/Users/alphab/.mdx/TMP/pstack/audioface-foundations/worktrees/integrated/packages/control/src/program-host.ts:228), and [ProgramHost.activate](/Users/alphab/.mdx/TMP/pstack/audioface-foundations/worktrees/integrated/packages/control/src/program-host.ts:323).

Keep document lineage and use the existing open lifetime identity to address runtime instances. Separately decide how an authored edit selects or updates live instances. A new synonymous ID brand is not necessary to correct ownership. This is an implemented prototype restriction, not a failed promise that arbitrary multiemitter support already shipped. It is nevertheless expensive coupling to build further into a public API.

### F4. Library identity is not actually unique

**Near term correction before library import, persistence or reuse outside fixed fixtures. Tested invariant gap.**

`sealLibrary` validates mint cursors and freezes input. It does not reject duplicate definition IDs or duplicate composition/revision pins. `findDefinition` and `findSnapshot` select the first array match. `withSnapshot` prevents a duplicate added later, but does not repair ambiguous initial input.

Two snapshots of `tone-voice@1` with different content are both accepted. Reordering those snapshots changes the same referencing document's effective pitch from 660 to 880 and changes its program key. Array order has become an undocumented authority over a supposedly immutable pin.

Source: [sealLibrary and findSnapshot](/Users/alphab/.mdx/TMP/pstack/audioface-foundations/worktrees/integrated/packages/patch/src/composition/library.ts:17).

Validate uniqueness once at library admission and establish indexed lookups. Validate safe revision values there as well. A storage engine is unnecessary. The present worker chooses a trusted library factory, which limits exposure, but the factory's result can still violate this model invariant while typechecking.

### F5. Definition defaults can recurse without a diagnostic

**Near term correction before expanding the definition catalogue. Tested invariant gap.**

`withDefaults` recursively follows `defaultValue.from` without cycle detection. A type valid definition with `PCH-01` defaulting to `PCH-01.end-hz` and the reverse is accepted by `sealLibrary`. Compilation throws `RangeError: Maximum call stack size exceeded`, rather than returning a structured issue.

Source: [withDefaults](/Users/alphab/.mdx/TMP/pstack/audioface-foundations/worktrees/integrated/packages/patch/src/composition/scope.ts:582).

Check a definition's default dependency graph at its admission boundary, using the existing graph machinery. Also validate referenced rows and unique parameter and port names there. The observed failure is the default cycle. Other missing definition checks are source observations, not additional executed failure cases. Current fixture definitions have no default cycle.

### F6. Compilation can expand far past the host's bounds before refusal

**Near term correction before large libraries or interactive editing. Tested scaling gap.**

`Expander.walk` has reference cycle detection but no expansion or depth budget. Each reference recursively materializes its content. Link resolution repeatedly scans all raw links, and canonical ordering repeatedly filters and sorts pending entries. Program size limits are checked downstream, after expansion and compilation.

The probe uses nine rack documents containing only seventeen authored placements. Eight levels of binary reuse produce 256 compiled slots. Compilation accepts that program before host validation rejects the sixteen slot limit. The observation demonstrates expansion amplification, without making a timing or memory exhaustion claim.

Source: [Expander.walk](/Users/alphab/.mdx/TMP/pstack/audioface-foundations/worktrees/integrated/packages/patch/src/composition/scope.ts:304), [resolveLinks](/Users/alphab/.mdx/TMP/pstack/audioface-foundations/worktrees/integrated/packages/patch/src/composition/links.ts:49), [canonicalOrder](/Users/alphab/.mdx/TMP/pstack/audioface-foundations/worktrees/integrated/packages/patch/src/composition/compile.ts:192), and [ProgramPreparer.open](/Users/alphab/.mdx/TMP/pstack/audioface-foundations/worktrees/integrated/packages/control/src/program-preparer.ts:110).

Pass an explicit compilation budget and stop while expanding. Count visited references, materialized slots and links before allocating more of them. Index library and adjacency lookups before adding caches. `withSnapshot` also appends every revision and `deepFreeze` revisits shared content. The 256 ticket generation cap bounds host commits, but the standalone composition surface has no history collector. A future collector needs pin and export ownership rules, rather than deleting arbitrary old revisions.

### F7. Kernel capability and lifetime policy are spread across core switches

**Must establish the kernel lifetime contract before reusable prepared graphs. Tested scope gap plus extension risk.**

`ENGINE_KERNELS` registers normalization, state layout and demand. It is not a complete executable catalogue. `validateSlot` separately hardcodes scope restrictions, input names, output names and allowed live keys. `bindProgramKernel` and `createProgramKernel` switch on implementation. `ProgramGraph` reads only the first input and specially recognizes `tone` and `envelope` when deriving lifetime.

There is already a mismatch within the admitted subset. A tone is allowed in the Sound region. The probe renders that Sound without Voices, obtains a peak of `0.999969`, and observes `runtime.idle === true`. `idle` tests only Voice occupancy and Voice driven tails. Cold activation and close use that predicate, so it cannot establish quiescence for an autonomous Sound source.

Source: [ENGINE_KERNELS](/Users/alphab/.mdx/TMP/pstack/audioface-foundations/worktrees/integrated/packages/engine/src/kernel-preparation.ts:103), [validateSlot](/Users/alphab/.mdx/TMP/pstack/audioface-foundations/worktrees/integrated/packages/engine/src/program-preparation.ts:150), [ProgramGraph constructor](/Users/alphab/.mdx/TMP/pstack/audioface-foundations/worktrees/integrated/packages/engine/src/program-graph.ts:40), and [ProgramRuntime.idle](/Users/alphab/.mdx/TMP/pstack/audioface-foundations/worktrees/integrated/packages/engine/src/program-runtime.ts:212).

The smallest immediate correction is to refuse autonomous Sound sources if they are outside the supported model. Supporting them requires a lifetime rule beyond Voice retirement. For extension, place executable port, scope, parameter and lifetime capabilities with the existing kernel owner. Let compilation read pure descriptors and execution read the implementation. Avoid a plugin framework.

Prepared reuse additionally needs explicit reset behavior for oscillator phase, biquad history, captured binding values and clocks. Those are currently closure state in `toneGenerator` and `createFilterStage`. Reusing their output buffers alone does not reset a Voice. Define that contract before preallocating banks. Stereo, arbitrary multiinput kernels and control signal ports are not implemented by the current executor, despite the broader authored type vocabulary.

### F8. Named outputs have no explicit host route

**Near term correction before output or spatial consumers. Tested silent omission.**

The compiler and runtime support named outputs, but `ProgramHost.render` reads only `outputs.get("main")`. It duplicates that mono signal into left and right. The observer also sees only this selected output.

Renaming the fixture output to `signal` still gives applied open and trigger outcomes. Its runtime buffer peaks at `0.582187`, while the host's stereo block is zero. Nothing in the request explains that the output has no device route.

Source: [ProgramHost.render](/Users/alphab/.mdx/TMP/pstack/audioface-foundations/worktrees/integrated/packages/control/src/program-host.ts:497).

Make output selection explicit in control over `{openedBy, outputPort}`. Until that exists, refuse unsupported routing at admission or clearly restrict the executable contract to `main`. Keep the final limiter shared. Spatial support itself is deferred by the host contract, so this finding does not claim an implemented spatial adapter is broken.

### F9. Two active authoring and execution models still carry different behavior

**Must choose the migration boundary before another application consumes the new model. Existing migration debt with tested inherited defect.**

The existing applications and catalogue use `packControlSurface`, `Pack.events: Patch`, `resolvePatch`, `bindVoice`, `VoiceRenderer`, and `VoicePool`. The foundations add `CompositionSurface`, `planEdit`, `ProgramPreparer`, `ProgramRuntime`, and separate resource and lifecycle bookkeeping. `GameAudio` continues the existing event path and report aging. The browser program path is an additional capability exercised by its proof entry.

This split preserves working noise, FM, event classes, listener placement and certification that the new program executor does not yet provide. It also preserves existing defects. A fresh probe removes `layer-02` after setting its pitch to 440, then inserts a tone. `nextMemberId` reuses `layer-02` and the retained parameter map restores 440 instead of the registry default 660. The new composition ownership model solves this problem, but application callers have not migrated to it.

Source: [existing pack contract](/Users/alphab/.mdx/TMP/pstack/audioface-foundations/worktrees/integrated/packages/contract/src/pack.ts:26), [surfaceFor](/Users/alphab/.mdx/TMP/pstack/audioface-foundations/worktrees/integrated/catalogue/audioface/src/index.ts:46), [eventVoice](/Users/alphab/.mdx/TMP/pstack/audioface-foundations/worktrees/integrated/packages/control/src/event-voice.ts:42), and [removeMember](/Users/alphab/.mdx/TMP/pstack/audioface-foundations/worktrees/integrated/packages/patch/src/patch-editing.ts:78). `initialState` in `control/src/surface.ts:92` also keys incoming patches by ID, collapsing duplicates by last array entry.

The document specification explicitly retained the existing path for a later shipping migration. Its presence is therefore authorized integration debt. Its indefinite continuation would be unnecessary dual architecture in a project with no compatibility obligation. Choose one content to runtime route, list the actual features needed to migrate the existing consumers, then migrate and delete those replaced paths in the same bounded unit. Do not delete noise, FM or listener capability merely because the new fixture omits it. Do not port old identity bugs into a compatibility adapter.

### F10. Voice construction and substantial command work remain inside rendering

**Required before a realtime readiness claim. Documented prototype limit, confirmed by a new probe.**

`ProgramHost.apply` invokes `ProgramRuntime.trigger` when the queue drains. Trigger reserves resources, resolves values, constructs maps and a `ProgramGraph`, binds kernels and allocates graph output storage. The probe wraps native constructors only during a one frame `BusHost.render` that applies a queued trigger. It observes eleven Maps, one Float32Array and six Float64Arrays.

Source: [ProgramHost.apply](/Users/alphab/.mdx/TMP/pstack/audioface-foundations/worktrees/integrated/packages/control/src/program-host.ts:418) and [ProgramRuntime.trigger](/Users/alphab/.mdx/TMP/pstack/audioface-foundations/worktrees/integrated/packages/engine/src/program-runtime.ts:154).

Commands also construct prospective values and bind every slot and resident before mutation. Their actual work grows with slot and Voice counts, even though queue admission charges parameter command count. That accounting is a bounded policy at current caps, not calibrated render CPU cost.

Prepared Voices address a real problem. Move construction and admission validation out of scheduled activation, while preserving command predecessor ordering and captured values at their specified frame. Instrument the complete callback call graph. The current browser instrumentation counts typed storage and coarse elapsed milliseconds. It expressly excludes arbitrary JS heap allocation and GC. Neither it nor this constructor probe proves deadlines, heap size or dropout absence.

### F11. Ticket capacity is a session lifetime budget

**Product/runtime decision before sustained use. Documented prototype limit, confirmed by a new probe.**

`ProgramTickets.settle` retains records and never decrements ordinary admission count. The probe settles 256 trigger tickets and observes the next trigger refused for history capacity, despite no pending requests. Open, edits and failed admitted work also consume that finite generation budget. `ProgramPreparer.requests` retains settled request objects, and `ProgramHost.voices` retains trigger identity mappings until generation disposal. These are bounded by the same prototype history policy, rather than unbounded leaks at current limits.

Source: [ProgramTickets.admit and settle](/Users/alphab/.mdx/TMP/pstack/audioface-foundations/worktrees/integrated/packages/control/src/program-tickets.ts:32).

Do not enlarge 256 and call this solved. Sustained use needs an explicit bounded replay and result retention contract that can retire identities safely while preserving cleanup authority. Disposing and reconstructing the audio device every few hundred actions would couple history management to audible lifetime. The current specification deliberately prohibits recycling within a generation, so this is a future contract decision rather than a violation of that specification.

### F12. Some contract fields and exports carry duplicate or unused truth

**Near term deletion and consolidation. Tested hash redundancy plus source observations.**

`CompiledModulation.seedLabel` is derived during compilation and included in `programKey`. Execution ignores it, deriving a seed from the slot label and modulation ID. Changing only that field produces a new valid program key and identical samples in the 256 sample probe. This is redundant identity data, not a hash collision.

Source: [CompiledModulation](/Users/alphab/.mdx/TMP/pstack/audioface-foundations/worktrees/integrated/packages/contract/src/program.ts:150), [programKey](/Users/alphab/.mdx/TMP/pstack/audioface-foundations/worktrees/integrated/packages/contract/src/program.ts:268), and [resolveProgramValues](/Users/alphab/.mdx/TMP/pstack/audioface-foundations/worktrees/integrated/packages/engine/src/program-values.ts:102).

The planner also produces `EditEffect.transfer`, but the current host sends only the new program and performs cold replacement. No production caller consumes that transfer map. `ProgramSpec.latency` and `ProgramOutput.wetOnly` retain planned transition metadata without an implemented transition consumer. Treat those as deferred contract material, not proof of live state transfer.

Additional concrete hygiene issues are the repeated `Waveform` union in `patch/src/patch-recipe.ts:28` and `contract/src/source.ts:3`, and limit fields such as `preparationsPerWindow`, `candidatesPerSound`, and `workPerWindow` with no production read. Actual enforcement uses corresponding literals or other owners. Consolidate or delete those declarations rather than preserving apparent configuration that has no effect.

Use one seed derivation authority. Remove the unused duplicate label or make it the authoritative execution input. Delete speculative public transfer machinery until an authorized consumer needs it, or explicitly isolate its prototype planning role. Keep kernel version and layout checks, which have real receiver validation consumers.

## Extension scenarios

| Requested change | What already composes | Where core knowledge still changes |
| --- | --- | --- |
| Add another rack instance | A pinned reference, local exposure values and placement path are data | Independent persistent Sounds still encounter F3. A nested `sound` reference is refused. Reusable nested parts are racks, not nested Voice spawning. |
| Add noise or a new effect kernel | DSP generators and stages already have reusable functions | New Definition, preparation capability, binder/factory, validator and lifetime logic. About five conceptual touchpoints, across patch-facing metadata and four engine files. Noise's lifetime is especially relevant because graph logic recognizes only tone and envelope as end authorities. |
| Change a supported control | Atomic document edits, ramps and configuration comparison exist | F1 and F2 must agree first. Live execution is currently curated cutoff and delay time/level, not every row marked live in an arbitrary Definition. |
| Add an emitter or spatial output | Separate Sound outputs, `openedBy`, existing `StereoImage`, `DistanceField` and final limiter | F3 and F8, an explicit route and per instance listener ownership. Program messages currently carry no emitter binding. Global listener messages affect the existing fixed Voice path. |
| Add a Studio consumer | Document snapshots, revisions, exposures and typed edits provide a useful base | Current `ControlSchema` projection and all existing adapter controls describe Patch. `ProgramClient` exposes mutation requests, not a general document query/projection API. A Studio needs one projection over the authoritative model, rather than a second editor model. |
| Export or persist a reusable library | Frozen snapshots and explicit composition pins are serializable | Admission invariants, definition identity policy, referenced snapshot closure, retention and schema parsing. Definitions are currently keyed only by ID. No database choice is needed to answer these questions. |
| Add a rendering backend | Platform boundaries and pure measure package are reusable | `ProgramGraph` and the curated binder are JS-specific. No WASM/native executor capability contract or multiinput/stereo kernel execution exists yet. Keep that as future work. |

The foundations already compose nested authored graphs and share DSP. They do not yet offer independently replaceable arbitrary kernels, nested Sound instances, general modulation signals or a stable application-facing composition library. The table names concrete changes needed instead of assuming a generic registration API has solved extensibility.

## Scaling assessment

Resident memory is explicitly reserved and refunded, with candidate overlap counted. That is good groundwork. Numeric storage units do not include exact Map, closure or object header sizes. The old fixed Voice budget and new Program ledger are separate accounts, so their simultaneous use does not establish a unified device workload budget.

Rendering scales with active Voices times their slots, plus persistent Sound slots and output summation. `ProgramGraph` invokes kernels per sample and passes a one sample scratch buffer into reused stages. That preserves the existing arithmetic but adds dispatch and parameter lookup work. No measurements here justify replacing it, and no declaration of operations per frame establishes its device cost.

Same frame bursts are intentionally constrained by one Voice construction per 128 frame window, globally. Two Sounds do not have independent constructor allowances. The queue bounds are real refusal policy, not proof that a gameplay burst is supported. Reserved release and close traffic remain valuable and must survive any new admission policy.

Preparation is also paced. `ProgramHost.pump` uses actual render progress, while the worklet sends at most one outstanding progress message and normally waits 1024 frames between notifications. Thus the one candidate per window cap is not a promise of preparation within 128 frames. Worker delay can increase preparation and command delivery latency while previously active audio continues rendering.

Cold edits wait for old Voices and their conservatively charged Sound tails. A held Voice can prevent adoption indefinitely until released. That is the accepted host milestone policy. It does not implement the held Voice transitions and state preservation experiments described in the earlier probes specification. Tail retention is based on declared worst cases, so it can outlast audible energy without being a leak.

Large authoring graphs have a separate risk from audio residency, as F6 shows. Many edits also repeatedly expand before and after documents and append retained snapshots. Neither a 16 slot receiver cap nor two resident Sounds bounds all worker preparation costs. Bound compilation first, then measure representative workloads. Cache only after the ownership and key semantics are settled.

The existing browser proof establishes realm execution, sample agreement for chosen fixtures, ordered effects, transfer behavior, cleanup, and progress during a main thread stall. Its 22 cases are combinations of nested/flat seeded fixtures, selected ramp admission frames and capacity cases at two rates. They do not cover gain conversion, duplicate library identity, alternate output names, an autonomous Sound generator, arbitrary graph shapes, long lived ticket reuse, device p99.9, heap pressure or dropouts. More repetitions of the same cases would not answer those questions.

## Version and migration audit

The tracked source, type, export, path and comment scan found no `V2` or `v2` replacement names. `new` in the implementation is ordinary construction or new snapshot terminology. The observed `replacement` occurrences refer to program replacement, queue replacement, or a rejected measurement approach. They do not identify copied versioned implementations.

The explicit `legacy` hit is a test asserting that the old Voice start admission method is absent. `compatibility` in `verify-program-worklet.mjs` names the five existing event comparisons. Production `incompatible` messages reject invalid kernel or cleanup contracts. None of these hits is a compatibility implementation. The MCP server's `0.0.0` is ordinary server metadata.

There are legitimate versions with concrete consumers:

- `Patch.schemaVersion: 1` is checked by the Patch schema parser.
- `Composition.schemaVersion: 1` declares a wire/document format, but its semantic import boundary still needs F4 and F5 work. It does not provide migration support by itself.
- Kernel implementation versions contribute to program identity and receiver compatibility checks.
- State layout versions are checked against engine capability. Actual state transfer remains deferred.
- Generation is a transport and lifetime epoch, and composition revision is an editing concurrency token. Neither is a replacement implementation version.

Git also shows actual deletions. Commit `31df5bb` removed `control/src/composition-runtime.ts` when the host replaced it. Commit `34d1647` removed the standalone program proof worklet/page entries when the real host proof replaced them. `80fbd61` removed the worklet encoding declaration after portable encoding replaced that assumption. Those migrations did remove replaced paths.

Temporary `.v2.draft.md` files and design `_versions` are review history. They are outside source and are not architectural defects. The material dual architecture is F9, regardless of its filenames. The user explicitly permits breaking changes, so compatibility cannot justify keeping both application paths permanently.

## Smallest coherent engineering sequence

1. Correct parameter semantics and classification together. Close F1 and F2 with real gain modulation and modulated live edit tests. Decide and encode autonomous Sound source support from F7. These are current contract disagreements that should be resolved before another foundation build depends on them.
2. Separate the authored target from the opened Sound lifetime in the public host API. Prove two instances of one pinned composition have independent state, close behavior and trigger seeds. State explicitly how edits target instances. Reuse `openedBy` and the current generation protocol.
3. Consolidate kernel capability ownership and define reset/bind/activate behavior for the supported kernels. Preserve shared DSP arithmetic. Remove the redundant seed field and duplicate type/limit declarations as touched cleanup. Build the prepared Voice bank only after this contract can reset state and preserve scheduling semantics.
4. Harden library admission and bound expansion. Close F4, F5 and F6 before accepting larger or persisted libraries. Use indexed authoritative snapshots and the existing graph helpers. Define output selection and close F8 before spatial routing.
5. Complete one application migration unit. Carry the required existing content capabilities through Composition and ProgramSpec, move the actual catalogue and control consumers, then delete replaced Patch-specific editing and execution paths. Preserve domain and measurement boundaries. Keep any required independent oracle in tests, not as another shipped engine.
6. Choose bounded history retirement and product workloads, then run sustained trigger/edit and device timing campaigns. Test reuse, stale cleanup and generation loss under the new F11 policy. Select active transition and spatial behavior separately with audible evidence.

Steps 1 through 3 are the dependency for prepared Voice work. Steps 4 through 6 are explicit subsequent milestones, not permission to add all those systems to the next patch. If the lead wants one immediate correction unit, I recommend step 1.

Keep the package graph, shared DSP, immutable pins, placement-owned values, canonical ordering, one queue, direct port and receiver credit lifecycle. Refactor the parameter and kernel capability contracts and Sound addressing. Delete replaced application paths when their real consumers migrate. Rethink long lived result retention and the definition of an idle Sound before product scale. These recommendations require fewer competing authorities, rather than more frameworks.

## Final state

Only this report, the specified external digest, and the external probe/evidence directory were written. Integrated remains clean at `3221511a59170b3fafaaa6924cf1a25f98a26b37`. No source, authoritative spec, original draft, prior review or main output was changed. The original Astra review and main README hashes were checked unchanged. Prepared Voice progression and Fable remain paused for lead and user discussion.
