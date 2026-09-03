---
title: Audioface foundations prepared Voice scout
type: projects
tags: [audioface, foundations, voice, admission, runtime, browser]
summary: Source grounded proposal for bounded reusable Voice slots in the program host, with exact lifecycle, demand, reset, and browser proof requirements.
status: draft
created: 2026-09-06
updated: 2026-09-06
project: audioface-next
related: [audioface-foundation-program-host-spec, audioface-foundation-runtime-probes-spec, audioface-foundations-runtime-host-browser-build]
confidence: high
---

# Audioface foundations prepared Voice scout

Target `3221511a59170b3fafaaa6924cf1a25f98a26b37` is clean. The active program host specification has SHA256 `3f32506eb9bbbddc3a9500455d3fa177e23aef370cd3ff2dfbd0f7d8f8aa7574`. This scout changes no source or specification.

## Recommendation

Build a fixed bank of receiver owned Voice slots inside each installed `ProgramRuntime`. The caller declares `voiceCapacity` when it opens a Sound. Receiver credit reserves the complete Sound and Voice bank demand before backing allocation, transfer, or graph construction. `ProgramHost.pump()` constructs or resets one slot during each acknowledged preparation opportunity. An open or install reaches its existing `pending: prepared` state only after every requested slot is ready.

A trigger claims one ready slot before queue admission. The existing `CommandQueue` retains the trigger until its frame. At that frame the slot reads the current Sound parameter cells and the trigger into preallocated resolution and binding workspaces, resets its existing kernels, and enters the active order. No `ProgramGraph`, kernel, map, closure, or typed array is constructed in this activation path. A trigger with no ready slot receives the current explicit refusal form. The host does not steal a Voice or drop a trigger.

When a Voice ends, its slot becomes reusable. A later `pump()` resets that dirty slot and returns it to ready state. The slot's receiver credit remains resident for the Sound lifetime. Graceful close, candidate cancellation, and confirmed generation disposal release that credit exactly once.

Delete the special one Voice per window quota after the prepared activation path exists. The existing general limit of 64 command work units per 128 frame window and the global limit of 32 resident Voice slots already bound activation. The current special quota exists to cap construction work. It blocks the second same frame trigger today even when resource capacity remains.

## Current behavior at the pinned source

### One trigger across three realms

1. Main calls `ProgramClient.request` in `adapters/web/src/program-client.ts:101`. It constructs and measures one `WorkerCall`, reserves a caller latch, and posts to the worker.
2. `serveProgramWorker` in `adapters/web/src/worker.ts:35` validates the call. `callProgram` invokes `ProgramPreparer.trigger`.
3. `ProgramPreparer.trigger` in `packages/control/src/program-preparer.ts:189` checks the retained Sound and installed planning base. It admits a ticket and posts one `ProgramOperation` through the existing direct `ProgramPort`.
4. `AudiofaceProcessor.control` in `adapters/web/src/worklet.ts:102` passes that envelope to `ProgramHost.receive` during an AudioWorklet message task.
5. `ProgramHost.operation` in `packages/control/src/program-host.ts:341` admits the receiver ticket and inserts a `ProgramScheduled` entry into the one `CommandQueue`. The entry has `voice: true`.
6. `RealtimeBusHost.render` in `packages/control/src/bus-host.ts:236` drains that queue against the existing device clock. `ProgramHost.apply` calls `ProgramRuntime.trigger` at the eligible frame.
7. `ProgramRuntime.trigger` in `packages/engine/src/program-runtime.ts:154` reserves one Voice demand, resolves modulation into new maps and objects, constructs a new `ProgramGraph`, constructs every Voice kernel and parameter cell, derives source routes and end metadata, then appends the Voice to two resident indexes.
8. The resulting `ProgramOutcome` returns through the same direct port. The worker settles `ProgramPreparer` state and posts the caller result to main.

The compiler, backing allocation, installation validation, and Sound graph preparation already precede activation. Voice graph construction does not. It runs inside the queue drain and therefore inside the `process()` call.

### Actual contracts

The pinned source contains no `PluginDefinition`, `PluginModule`, `PluginInstance`, or `RenderBlock` declarations. The implemented boundaries are:

- `Definition` in `packages/contract/src/composition.ts:40` for kernel identity, parameters, ports, and scope.
- `KernelPreparation` in `packages/contract/src/program.ts:115` for normalized configuration, state layout, and demand.
- `ProgramSpec` in `packages/contract/src/program.ts:195` as the one serializable program.
- `ProgramKernel` in `packages/engine/src/program-kernels.ts:44` as the engine private execution contract.
- `ENGINE_KERNELS` in `packages/engine/src/kernel-preparation.ts:103` as the current curated catalogue.

The prepared Voice unit stays behind these boundaries. It does not add a public plugin contract before that contract exists in source.

### Existing bounds and residency

`PROGRAM_HOST_LIMITS` in `packages/contract/src/program-host.ts:11` allows two Sounds, one candidate per Sound, four programs, 32 Voices, 128 ordinary queue entries, 64 command work units per window, 256 ordinary tickets, and 768 result records. `ResourceLedger` in `packages/control/src/resource-ledger.ts:41` owns the one aggregate receiver account. `programInstanceDemand` in `packages/engine/src/program-preparation.ts:213` derives Voice graph demand from the program.

The program path has no fade state or stealing policy. `ProgramRuntime` holds an admitted Voice through its computed `endFrame`, then refunds it. `tailUntil` retains shared Sound state after the last Voice contribution. `PROGRAM_RESOURCE_LIMITS` caps aggregate `tailFrames` at 100,000,000. The separate legacy path has `VoicePool` capacity 32 and `VoiceBudget` fade capacity 32 at `packages/engine/src/voice-budget.ts:23`. Those limits do not govern program Voice admission.

Two declarations need correction in the prepared Voice build:

- `preparationsPerWindow` has no source consumer. `ProgramHost.pump` enforces its own frame condition instead. Delete the unused declaration.
- `voicesPerWindow` flows into `CommandQueue.checkWindow` and refuses the second trigger in a 128 frame sliding window. Delete this special quota only after activation uses a prepared slot. Triggers continue to consume ordinary command work.

The browser adapter coalesces progress every 1,024 frames in `AudiofaceProcessor.render` at `adapters/web/src/worklet.ts:90`. `ProgramHost.pump` at `packages/control/src/program-host.ts:236` runs in the returned message task. Browser preparation can therefore occur only when the audio clock advances and the direct progress handshake completes.

## Probe evidence

The external probe `prepared-voice-scout/probe-current-burst.mjs` opens the existing fixture and sends two triggers at frame zero. The first applies. The second receives `Audioface commands per render window capacity exceeded.` One Voice remains resident.

`probe-current-voice-state.mjs` measures one current `PAIR` trigger. The trigger constructs seven typed arrays with 52 bytes. Its declared Voice demand is 228 owned bytes, six slots, 36 parameters, six connections, 52 installation operations, and 352 operations per frame. The typed array counter excludes maps, sets, arrays, objects, closures, browser storage, and garbage collection.

The same probe deliberately runs one `ProgramGraph` for 256 frames and then restarts its elapsed counter without resetting its state. Compared with a fresh graph, 127 of the next 128 samples differ. The maximum difference is `0.696728527545929`. This negative control proves that object reuse requires explicit phase, filter, value, route, and end metadata reset. It does not estimate performance.

The current exact SHA browser evidence reports 22 cases in Chrome 152, message tasks up to 5 ms, process calls up to 1 ms, and up to 104 observed typed array bytes in a process span. Those counters have millisecond resolution and do not observe arbitrary JavaScript heap allocation or garbage collection. The current realtime proof issues one Voice trigger, followed by parameter commands. It does not exercise a burst.

## Reuse and quality map

| Current owner and symbol | Finding | Disposition for the next build |
| --- | --- | --- |
| `contract/program.ts` `ProgramSpec`, `ProgramTrigger`, `ProgramDemand` | One shared program, trigger, and demand vocabulary already crosses the required boundaries. | Keep. Add no parallel program, trigger, or demand type. Pool size stays host provisioning and does not enter `ProgramKey`. |
| `contract/program-host.ts` `ProgramPreparation`, `PROGRAM_HOST_LIMITS` | Installation has no Voice provisioning count. One preparation limit is dead and the one Voice quota encodes the prototype constructor cap. | Add `voiceCapacity` to open and install preparation. Delete `preparationsPerWindow` and the special Voice window quota after prepared activation lands. |
| `patch/composition/compile.ts` `compile`, `composition/plan.ts` `planEdit` | Compilation and classification already produce the one `ProgramSpec`. | Keep unchanged. Prepared Voice work must not create a second compiler or classifier. |
| `engine/program-preparation.ts` `installationDemand`, `programInstanceDemand` | Voice demand is charged once per active constructor. | Refactor `installationDemand(program, voiceCapacity)` to multiply the existing Voice demand once. Use this function in sender and receiver validation. |
| `engine/program-preparation.ts` `programBacking`, `programStorageLayout`, `validateProgramStorage` | Worker allocation and transfer cover slots with declared state and positive `capacityFrames`. Current curated Voice slots use scalar phase and filter state, so their storage stays inside receiver objects. | Keep the one backing layout and validator. Add no Voice transfer format. Receiver credit covers the fixed Voice objects before their construction. |
| `engine/program-values.ts` resolution functions | Trigger and command validation allocate temporary maps, sets, and objects. `ProgramValue.copyFrom` already preserves the remainder of a live ramp. | Refactor into one reusable indexed resolver with preallocated scratch. Migrate install, command validation, and Voice activation together. Delete the replaced one shot resolution path. |
| `engine/program-graph.ts` `ProgramGraph` and `engine/program-kernels.ts` `ProgramKernel` | The graph precomputes kernel order and routes, but its constructor owns all mutable Voice state. Kernels have no reset contract. | Keep one graph and one kernel path. Add engine private prepare, validate, commit, and reset operations. Reuse existing DSP math. Do not add a second renderer. |
| `source-generator.ts` `toneGenerator`, `layer-filter.ts` `createFilterStage` | Tone phase and filter history are closure state with no reset. | Refactor the existing objects to expose reset to the program kernel. Legacy callers continue to use the same generator and filter arithmetic. Current Voice scope has no delay or echo kernel, so add no speculative Voice delay pool. |
| `engine/program-runtime.ts` `voices`, `admissionOrder`, `trigger`, `reclaim` | A map and an array index the same constructed residents. `trigger` allocates at activation. | Replace resident graph ownership with one fixed slot bank and a fixed active order of slot indexes. Keep numeric Voice identity and sum order. Split slot code into one focused module so `program-runtime.ts` remains below the file and function limits. |
| `engine/program-runtime.ts` `install` | Production cold replacement constructs a candidate runtime in `ProgramHost`; only direct tests call the separate immediate replacement method. | Delete the parallel replacement path. Move its validation cases to candidate construction and host activation tests. Keep `activateAt` for the prepared candidate. |
| `control/program-preparer.ts` `Sound` and `control/program-host.ts` `Sound` | These maps describe different realm ownership. One tracks desired and applied documents; one owns audio resources. | Keep both. Retain `voiceCapacity` with the worker Sound so every cold candidate requests the same bank. |
| `control/program-host.ts` `waiting`, `candidates`, `pump`, `operation` | The existing candidate lifecycle and direct port already pace audio side preparation. | Extend this lifecycle. Construct or recycle one Voice slot per pump opportunity. Claim a ready slot before a trigger enters the queue. Add no preparation queue. Scan existing bounded owners in stable order. |
| `engine/command-queue.ts` `CommandQueue` and `control/bus-host.ts` `RealtimeBusHost` | They already own ordering, frame normalization, cancellation, work windows, and lifecycle reserves. | Keep one queue and clock. Remove only the special Voice count. General work, entries, bytes, lookahead, and lifecycle reserves remain. |
| `engine/voice-pool.ts` `VoicePool`, `engine/master-bus.ts` `prepared`, `GameAudio.trigger` | The legacy pool owns class floors and stealing. `MasterBus.prepare` still constructs one `VoiceRenderer`, `DistanceField`, and `StereoImage` for every start. The pool manages lifetime admission and has no reusable graph resources. | Keep unchanged because public `GameAudio` migration is excluded. Reusing it would import unapproved stealing and spatial policy into the program path. |
| `test/foundations/oracle.ts`, `program-worklet-support.mjs`, `program-browser-support.mjs`, `scripts/verify-program-worklet.mjs` | They already own the independent DSP reference, 22 sample cases, Node comparison, real browser driver, negative controls, and bounded captures. | Extend them. Do not create another oracle, browser driver, or capture format. |
| `scripts/test-support/program-instrumentation.mjs`, `test/foundations/storage.mjs` | They observe typed array construction and elapsed time but exclude the general heap and garbage collection. | Reuse and retain the limitation. Add bounded state counters and browser trace evidence without claiming allocation free execution. |

## Two viable approaches

| Approach | Benefit | Cost and risk | Verdict |
| --- | --- | --- | --- |
| Construct each Voice in the AudioWorklet message task when its trigger arrives | Small source change. The constructor leaves `process()`. | Every trigger still allocates a graph, maps, closures, and typed arrays on the Web Audio rendering thread. Cancellation wastes completed construction. Burst work scales with trigger count. This does not provide already prepared resources. | Reject for this milestone. |
| Prepare a fixed reusable slot bank with each Sound | Construction is bounded by declared residency. A trigger claims existing resources. Same frame burst capacity is explicit. Cancellation, reuse, and disposal have finite owners. | Sound readiness takes several pump opportunities. Idle slots retain memory. Reset requires a careful refactor of the current kernel and value implementation. | Recommend. |

## Proposed ownership and state

The following types remain engine private. Contract carries only `voiceCapacity` because realms must agree on demand.

```ts
type ProgramOpenOptions = {
  readonly seedMap?: SeedMap;
  readonly voiceCapacity: number;
};

type PreparedVoice = {
  readonly graph: ProgramGraph;
  readonly resolution: ProgramResolutionWorkspace;
  readonly mix: ReturnType<ProgramGraph["sources"]>;
  readonly mixEnds: number[];
};

type VoiceSlot =
  | { readonly kind: "preparing"; readonly index: number }
  | { readonly kind: "ready"; readonly index: number; readonly voice: PreparedVoice }
  | {
      readonly kind: "reserved";
      readonly index: number;
      readonly voice: PreparedVoice;
      readonly trigger: ProgramTrigger;
    }
  | {
      readonly kind: "active";
      readonly index: number;
      readonly voice: PreparedVoice;
      readonly id: number;
      readonly started: number;
      readonly endFrame: number;
    }
  | {
      readonly kind: "tail";
      readonly index: number;
      readonly voice: PreparedVoice;
      readonly id: number;
      readonly started: number;
      readonly released: number;
      readonly endFrame: number;
    }
  | { readonly kind: "reusable"; readonly index: number; readonly voice: PreparedVoice }
  | { readonly kind: "disposed"; readonly index: number };
```

`active` covers a one shot and an unreleased sustaining Voice. `tail` begins when a held Voice releases and continues through its release envelope and any declared Voice path tail. The current curated Voice region has no echo or delay slot, but the existing `endFrame` calculation remains authoritative. `ProgramRuntime.tailUntil` continues to describe shared Sound state after Voice contribution ends.

Suggested `ProgramRuntime` responsibilities are:

```ts
readonly voiceReadiness: {
  readonly capacity: number;
  readonly ready: number;
  readonly reserved: number;
  readonly active: number;
  readonly tail: number;
  readonly reusable: number;
};

prepareOneVoice(): void;
reserveVoice(trigger: ProgramTrigger): ProgramVoiceReservation;
activateVoice(reservation: ProgramVoiceReservation): number;
cancelVoice(reservation: ProgramVoiceReservation): void;
```

`ProgramVoiceReservation` is an opaque engine object that names one slot and one runtime. It never crosses a realm. `reserveVoice` validates the trigger shape and claims a ready slot without assigning numeric Voice identity. `activateVoice` runs at `ProgramRuntime.frame`. It resolves values into scratch, validates every binding, then commits all resets atomically. Only a successful commit increments the existing numeric serial and appends the slot index to admission order. A failed activation consumes no Voice identity and leaves the slot ready.

The reset commit restores tone phase, filter histories and coefficient cache, per Voice `ProgramValue` cells, output scalars, release metadata, and mix end metadata. Frozen and trigger modulated values use the new trigger. Live unmodulated values call the existing `ProgramValue.copyFrom`, preserving the exact remaining ramp from the Sound at the activation frame. Slot index never enters a seed. `childSeed` and `drawAt` remain the only random authorities.

## State transitions

| Event | Transition | Accounting |
| --- | --- | --- |
| Receiver grants open or install | No slot state yet | Reserve installation demand plus `voiceCapacity * programInstanceDemand(program, "voice")` before sender backing allocation or transfer. |
| `ProgramHost.pump` builds one initial slot | `preparing -> ready` | Credit already covers the object and numeric storage. Record actual preparation work once. |
| All requested slots are ready | candidate becomes prepared | Emit the existing `pending: prepared`; later queue the existing activation entry. |
| Trigger envelope passes identity, revision, program, ready capacity, and queue checks | `ready -> reserved` | No allocation and no new resource credit. Queue work remains spent if later cancelled. |
| Trigger reaches its ordered frame | `reserved -> active` | Resolve and reset in preallocated workspaces. Assign identity and append in queue order. |
| Release reaches its ordered frame | `active -> tail` | Keep the slot and all credit until `endFrame`. A repeated release retains current idempotent behavior. |
| One shot or released Voice reaches `endFrame` | `active or tail -> reusable` | Remove it from the active order. Do not refund the resident bank. |
| A later pump resets one dirty slot | `reusable -> preparing -> ready` | No new residency. Record reset work. Until then, overload receives an explicit refusal. |
| Queued trigger cancellation or queue admission rollback | `reserved -> ready` | Remove the one existing queue entry. Consume no numeric Voice identity. |
| Candidate cancellation | all candidate slots become `disposed` | Drop the runtime and return its receiver credit once. |
| Graceful close | reserved triggers cancel, active Voices release, Sound tail drains, then all slots become `disposed` | Return credit only after runtime disposal and actual Sound reclamation. |
| Generation loss | states remain quarantined | Settle callers as application unknown. Return no credit until `confirmDisposal` or device teardown. |

## Ordering, replacement, and overload

The current queue remains the only ordered clock. A same frame command posted before a trigger updates the Sound cells before `activateVoice` reads them. A same frame trigger posted first captures the earlier values. Equal frame triggers receive numeric identities and enter the active order in queue order. This preserves the existing Float32 summation order.

A cold candidate owns a separate slot bank built for its `ProgramKey`. The host never reuses slots across different programs. Candidate preparation can overlap an active Sound only when the existing global ledger has capacity for both complete banks. An exact resource limit passes. One unit short refuses before backing allocation or transfer. The old Sound and samples remain unchanged.

If a cold activation precedes a queued trigger for the old program, `ProgramHost` removes that trigger through the existing scheduler, returns its reservation, and settles the retained ticket with the existing stale program refusal. If the trigger precedes the candidate at the same frame, it activates first and the candidate waits for Voice and Sound tail reclamation. No second queue or timeout decides the race.

When close applies, the host removes the Sound's remaining reserved triggers, returns their slots, releases active Voices, and waits for `ProgramRuntime.idle`. Ready and reusable slots do not keep `idle` false. Active or tail Voices and `tailUntil` do. Close refunds the full bank only after disposal.

The prepared bank changes overload from a constructor quota to actual readiness:

- A missing ready slot refuses only that trigger before queue admission.
- A full ordinary queue returns the claimed slot to ready and refuses only that trigger.
- Invalid trigger modulation at activation settles that admitted trigger as refused and returns the unchanged slot to ready.
- No condition steals, truncates, or silently drops a Voice.
- The 32 resident slot limit, 64 work units per window, queue entry and byte limits, ticket records, and lifecycle reserves remain active.

## Resource residency and work

`installationDemand(program, voiceCapacity)` becomes the single demand calculation used by the worker reserve request, receiver validation, and direct Node construction. It adds the current installation demand to the current Voice instance demand multiplied by the requested capacity. The count must be a nonnegative safe integer no larger than the global Voice limit. Zero supports a Sound that needs no triggerable Voice. A Sound retains the same count across cold preparation.

`ResourceLedger` remains the only receiver ledger. Its reserved snapshot counts every slot in preparing, ready, reserved, active, tail, and reusable state. Reuse changes no resident count. Candidate cancellation, graceful close, and confirmed disposal return the exact vector once.

The current `performedInstallationOperations` counter increments the full declared amount when credit is reserved. Incremental slot construction would make that name inaccurate. Refactor the same ledger to record actual declared preparation or reset work when work begins. Keep the counter monotonic. Resource refund never subtracts performed work. The existing ledger owns this telemetry. Add no second account.

Queue work remains a separate existing time window allowance. Every trigger consumes one general command work unit even when later cancelled. Initial construction and recycle happen through the single paced `pump()` path. `pump()` examines the bounded Sound and candidate records in stable order and performs one job. It first restores an active Sound's reusable slot, then advances the oldest candidate. This scan performs lifecycle orchestration. It adds no queue.

## Before and after behavior

| Scenario | Current | Proposed next unit |
| --- | --- | --- |
| Two same frame triggers with free resident capacity | First applies. Second refuses because `voicesPerWindow` is one. | Both apply when two ready slots exist. |
| Trigger activation | Constructs and binds a complete Voice graph inside `process()`. | Claims an existing graph and commits bounded reset at the ordered frame. |
| Invalid trigger modulation | New graph construction fails and its provisional demand refunds. | Preallocated validation fails before reset commit. The ready slot remains clean. |
| Voice retirement | Graph and demand refund. | Slot becomes reusable, then ready after paced reset. Bank demand stays resident. |
| Repeated seed after reuse | New construction starts clean by construction. | Reused slot must match the old samples exactly. |
| Open or cold install readiness | Sound graph prepared. Voice graphs remain future trigger work. | Existing prepared outcome means the Sound graph and full requested Voice bank are ready. |
| Resource snapshot with no active Voices | `voices` is zero. | Reserved `voices` equals bank capacity. Readiness counters distinguish occupancy. |

## Bounded build and proof proposal

Use an explicit proof configuration of eight slots per Sound. This value applies only to the proof. The owner selects any shipping default later. Two active Sounds plus two simultaneous cold candidates occupy the current global maximum of 32 slots. The exact fit exercises the existing bound without enlarging it.

### Engine and Node proof

1. Add a failing reset test beside `program-runtime.test.mjs` using the current negative probe. Prepare one slot, trigger it, retire it, recycle it, and trigger again. Compare every sample with the current fresh graph behavior and the independent oracle.
2. Cover eight distinct roots, repeated roots, alternating slots, and reversed physical slot storage. Assert seed identity, admission order, and isolated mutable cells.
3. Trigger during each tested point of the current ramps at frames 299, 300, 364, 428, and 450. Compare with the existing per frame reference. Apply a later live command and prove that every active Voice inherits it without sharing a `ProgramValue` cell.
4. Prove invalid trigger modulation changes no slot, serial, resource count, or next samples.
5. Prove release during attack, held release, one shot completion, Sound tail overlap, recycle, and repeated recycle. Assert every state count and exact disposal.
6. Check demand exact fit and one unit short for count, bytes, slots, parameters, connections, operations, and transfer envelope. Cancellation and reset never refund work.

### Host and protocol proof

1. Migrate open calls to explicit `{ seedMap, voiceCapacity }`. Verify clone safety, envelope bounds, retained capacity across reconcile, and unchanged `ProgramKey`.
2. Send 100 same frame triggers across two Sounds with eight ready slots each. The first 16 in sender order apply. The remaining 84 receive the explicit prepared capacity refusal. No trigger enters the legacy `VoicePool`.
3. Cancel reserved triggers before activation. Race trigger, live command, cold activation, release, and close at equal frames. Preserve one terminal result per ticket and the current frame reporting.
4. Hold a Voice while a cold candidate reaches full readiness. Cancel the candidate once, then release and activate another. Prove no slot, transfer, ticket, or credit survives its owner.
5. End the generation with ready, reserved, active, tail, reusable, and candidate slots present. Caller outcomes become application unknown once. Credit remains until confirmed disposal, then reaches zero.

### Real browser proof

Extend `program-worklet-support.mjs`, `program-browser-support.mjs`, and `verify-program-worklet.mjs`. Keep the existing 22 cases and four channel capture. Add one controlled offline burst timeline at both 48 kHz and 44.1 kHz:

- Open two Sounds with eight slots each and wait for their existing applied outcomes.
- Schedule eight triggers per Sound at one frame with known roots and order. Refuse the next trigger for each Sound.
- Capture each Sound before summation and the protected stereo result. Compare browser bytes with the Node host and the independent oracle timeline.
- Drain every Voice and the shared Sound tail. Advance progress until all slots return to ready.
- Repeat the burst with the same roots assigned to different physical slots. Require exact per Sound and mixed samples.
- Run ragged Node spans and actual 128 frame browser quanta. Record requested and applied frames.

Run fresh private headless and headed Chrome sessions. Retain the existing sample, outcome, worker, processor, and timeout negative controls. Add a reset negative control in Node that skips reset and must fail the sample comparison. Browser source corruption and stale outcome controls must still exit 1.

Record process and message task calls, typed storage, Voice construction count, reset count, readiness high water marks, refused triggers, active order, resource peaks, and browser trace garbage collection events. The build passes only if activation constructs zero program graphs and zero typed storage. This assertion is narrower than whole callback allocation.

### Exact gates

```text
node --test test/foundations/program-runtime.test.mjs
node --test test/foundations/program-host.test.mjs test/foundations/program-protocol.test.mjs
node --test test/foundations/program-browser.test.mjs
pnpm run check
pnpm --filter @audioface/app-web build
node scripts/verify-program-worklet.mjs headless <evidence>/headless
node scripts/verify-program-worklet.mjs headed <evidence>/headed
```

Run all five existing browser fault modes in both browser modes. Record exact source SHA, artifact hashes, browser version, sample rate, quantum size, outcomes, queue peaks, resource snapshots, and clean tree state.

## Performance limits

This proposal proves finite ownership, exact samples, and prepared graph reuse. It does not establish a shipping pool size, realtime deadline, dropout absence, browser heap allocation freedom, or garbage collection safety.

Initial slot construction and recycle still run in AudioWorklet message tasks on the Web Audio rendering thread. The worker cannot construct JavaScript closures or engine objects for transfer. `countStorage` observes typed arrays and views only. `Date.now()` has millisecond resolution. Browser trace observations remain local to the tested device.

The reset refactor removes known graph, kernel, map, closure, and typed array constructors from trigger activation. Existing queue bookkeeping, ticket outcomes, map mutations, and command validation can still allocate JavaScript heap objects. Report those operations separately. Make no whole callback allocation claim.

## Decisions

Engineering can proceed with these choices after design review:

- One explicit `voiceCapacity` per retained Sound, preserved across cold candidates.
- Eight slots per Sound only in the bounded proof.
- Explicit refusal when no ready slot exists.
- One existing scheduler, one ledger, one compiler, and no Voice stealing.
- Pooled resources never cross `ProgramKey` or generation boundaries.
- General command work replaces the constructor specific one Voice quota.

Owner decisions remain outside this unit:

- The shipping default and per Sound distribution of the global Voice budget.
- Any future Voice class, priority, stealing, or audible overload policy.
- Accepted device memory, preparation latency, deadline, and garbage collection budgets.
- Public `GameAudio` migration and product library placement.

These owner decisions do not block a parameterized proof with explicit capacity and current refusal semantics.

## Scout verification

Both external probes exit zero at the pinned SHA. The focused runtime, host, protocol, and Node browser command passes 72 tests. `pnpm run check` passes 503 tests plus typecheck, lint, formatting, and structure verification. The final artifact check records the report and digest hashes, the 700 word digest limit, the unchanged specification and README hashes, exact `HEAD`, and clean integrated tree.

## Evidence

- `/Users/alphab/.mdx/TMP/pstack/audioface-foundations/prepared-voice-scout/probe-current-burst.mjs`
- `/Users/alphab/.mdx/TMP/pstack/audioface-foundations/prepared-voice-scout/probe-current-burst.json`
- `/Users/alphab/.mdx/TMP/pstack/audioface-foundations/prepared-voice-scout/probe-current-voice-state.mjs`
- `/Users/alphab/.mdx/TMP/pstack/audioface-foundations/prepared-voice-scout/probe-current-voice-state.json`
- `/Users/alphab/.mdx/TMP/pstack/audioface-foundations/prepared-voice-scout/verification.json`
- Current browser baseline: `/Users/alphab/.mdx/TMP/pstack/audioface-foundations/runtime-host-browser-corrections/headless-final/result.json`
- Independent correction review: `/Users/alphab/.mdx/TMP/pstack/audioface-foundations/runtime-host-browser-corrections-review-digest.md`
