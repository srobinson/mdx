---
title: Audioface foundations runtime host design review
type: projects
tags: [audioface, foundations, runtime, host, worker, worklet, review]
summary: Independent source-grounded refinements for one bounded ticketed installation prototype, with explicit ownership, validation, lifecycle, scheduling, deletion, and browser gates.
status: draft
created: 2026-09-05
updated: 2026-09-05
project: audioface-next
related: [audioface-foundations-runtime-host-next-scout, audioface-foundation-runtime-probes-spec, audioface-foundation-document-spec]
confidence: high
---

# Runtime host design review

Verdict: **refinements**. Recommend one ticketed cross-realm installation unit, subject to lead adjudication of the refinements below. This report authorizes no implementation and changes no specification.

Reviewed clean integrated `30b15bcf8ff3f42b5afd25c296cc0e8afd633e21` at `/Users/alphab/.mdx/TMP/pstack/audioface-foundations/worktrees/integrated`. Fable's scout targets `ea487fbb031ec467c24d06ea60008387fc9cb7c7`. The intervening four-file diff contains test and verifier hygiene only. Source pointers below refer to integrated at the reviewed SHA. Existing source behavior and proposed interfaces are distinguished explicitly.

Inputs were the lead's design-review brief, Fable's complete scout and digest, its allocation probe and JSON, the runtime probe specification, the current document specification, and the lead's runtime decisions. TypeScript, type discipline, review, reuse, subtraction, boundary, reader-load, artifact, and writing guidance were read directly. No agents, source edits, specification edits, builds, broad tests, commits, or remote repository actions were used.

## Changes needed before implementation

| Candidate | Evidence and consequence | Required refinement |
| --- | --- | --- |
| Terminal completion and refund are conflated | [Scout line 107](/Users/alphab/.mdx/projects/audioface-foundations-runtime-host-next-scout.md:107) refunds preparation on any terminal state. `ProgramRuntime.install` at line 102 refunds the previous installation. The new installation remains resident. | Separate ticket completion, sender detachment, and receiver reclamation. `applied` releases ticket work capacity but keeps active storage charged. |
| Cancellation has no independent correlation | [Scout lines 83 and 129](/Users/alphab/.mdx/projects/audioface-foundations-runtime-host-next-scout.md:83) name only the target ticket, then propose refusal after activation. This can produce a second terminal result for the applied ticket. | Give the cancellation request its own existing `CommandId`, plus `target: CommandId`. Return `too-late` on the cancellation request. Preserve the target's terminal result. |
| Kernel binding omits compatibility checks | [program-preparation.ts:84](/Users/alphab/.mdx/TMP/pstack/audioface-foundations/worktrees/integrated/packages/engine/src/program-preparation.ts:84) validates version, state layout, demand, ports, and lifetimes. `bindProgramKernel` at line 66 of program-kernels.ts does not perform these checks. A focused probe passed a wrong version through binding and saw full validation refuse it. | Keep full `validateProgram`, including key recomputation, during bounded audio preparation in this first unit. Envelope validation alone cannot replace it. |
| Hash identity is insufficient for resource admission | `programKey` in contract/program.ts excludes aggregate demand and state descriptors. A focused probe changed aggregate owned bytes without changing the key. Full validation rejected the mismatch. | Validate the received graph and derive demand with engine capabilities. A claimed key never grants installation or credit. |
| A ProgramHost table alone does not integrate audio | [bus-host.ts:215](/Users/alphab/.mdx/TMP/pstack/audioface-foundations/worktrees/integrated/packages/control/src/bus-host.ts:215) drains only `StampedBus`. [master-bus.ts:217](/Users/alphab/.mdx/TMP/pstack/audioface-foundations/worktrees/integrated/packages/engine/src/master-bus.ts:217) limits the already mixed legacy output. ProgramRuntime starts its clock at zero. | Add one contribution point before the existing limiter and align newly opened runtimes with the host clock. Never add program output after protection or introduce another scheduler. |
| Offline acknowledgement ordering can deadlock | [Scout line 121](/Users/alphab/.mdx/projects/audioface-foundations-runtime-host-next-scout.md:121) awaits an outcome before resuming. Activation and tail reclamation require rendering to advance. | Await only nonterminal staging readiness at a suspension, when that browser delivers it. Resume before awaiting applied or reclaimed outcomes. Gate the actual transport behavior first. |
| Rebuild cannot be a counter-only change | [game-audio.ts:183](/Users/alphab/.mdx/TMP/pstack/audioface-foundations/worktrees/integrated/adapters/web/src/game-audio.ts:183) closes a possibly unresolved opening asynchronously. Existing send continuations and listeners retain that opening. | Fence send continuations, outcomes, credits, and close completion by captured generation and device identity. Settle unresolved callers explicitly on generation loss. |
| Existing-page byte identity conflicts with shared changes | [apps/web/src/worklet.ts:1](/Users/alphab/.mdx/TMP/pstack/audioface-foundations/worktrees/integrated/apps/web/src/worklet.ts:1), bundle.mjs, and build.mjs embed the adapter worklet in both existing pages. Shared host, queue, and adapter executable changes alter that bundle. | Replace byte-identical acceptance with recorded hash deltas and fresh unchanged-behavior proof. Keeping frozen executable copies would duplicate the migrated implementation. |
| Allocation observation is weaker than its labels | `test/foundations/storage.mjs` counts every typed constructor's byteLength, including a view over existing backing, as a buffer allocation. A 64-byte preexisting backing produced `{bytes:64,buffers:1,views:0}` for one view. | Refine this existing instrument when testing transfer. Count unique backing, constructed views, and retained ownership separately. Do not create another counter. |

These are design candidates for adjudication. They are not claims that the already reviewed foundation implementation violates its narrower completed scope.

## Four choices

| Choice | Recommendation | Concrete alternative and tradeoff |
| --- | --- | --- |
| Document realm | Put `createCompositionSurface` and the preparer in the worker for this prototype. Main sends authored requests and displays snapshots. | A compile-only worker is feasible with a main-owned asynchronous transaction that rechecks expected revision before commit. It does not inherently require double compilation, contrary to the scout. It would require splitting the current synchronous surface/plan transaction and maintaining another inter-realm transaction boundary. There is no benefit for this unit. |
| Transport | Transfer a dedicated MessagePort between worker and worklet. Bootstrap and device teardown remain main-owned. Program commands, outcomes, reservations, and cancellation use that one bidirectional path. | Main relay is simpler to observe but makes program delivery depend on a responsive main thread. Keep no relay fallback in the completed unit. Unsupported direct transport is an explicit prototype blocker or inconclusive environment result. |
| Audio validation | Reuse full `validateProgram` after bounded envelope parsing, before graph construction. It runs once per received candidate, outside `process`, within a separately charged preparation allowance. | Worker full validation plus audio structural validation without hashing could reduce cost later. It still needs every version/layout/demand/routing/lifetime check currently colocated with the hash check. Binding alone is insufficient. This unit should measure the existing complete validator before introducing that split. |
| Shared types | Reuse `CommandId` for operation tickets and the successful open ticket for Sound lifetime identity. Reuse `CompositionId`, `ProgramKey`, `VoiceId`, `ExecutionProfile`, `ParameterCommand`, and `ResourceDemand`. | New `ProgramTicket` and `SoundId` brands add identities already represented by the operation and open lifetime in this bounded model. They require no new identity authority here. Keep transport structure separate from authored types and runtime objects. |

The worker choice is a prototype engineering decision. It does not decide the shipping library realm. Full audio validation is a deliberate refinement of Fable's recommendation. It costs hashing and temporary allocations on the rendering thread. No deadline or allocation-free admission claim follows.

## Authority and type outline

The proposed public Sound handle contains `{ generation, openedBy: CommandId }`. The open record also contains its `CompositionId`. Permit one retained instance per composition in this prototype, matching the existing Map in composition-runtime.ts. Reopening uses a new open ticket, so a late release or close cannot target the replacement. Two distinct fixture compositions give two independent Sounds. Multiple simultaneous instances of one document are excluded.

Use `CommandId` as the ticket field everywhere, minted by the worker through existing `toCommandId`. Generation is a validated, monotonic device-lifetime counter. It invalidates old devices. It is neither a revision nor a program identity. Base revision describes the installed state an effect expects. Target revision describes the accepted document state it applies. `ProgramKey` identifies the installed immutable program; a live command advances applied revision without changing that key. `VoiceId` is an opaque wire identity, mapped by control to the existing runtime-local number and owning Sound handle. Never expose an unqualified numeric Voice id across Sounds.

Minimal new contract declarations are envelopes and discriminated results, not duplicate domain records:

```ts
type ProgramAddress = { readonly generation: number; readonly openedBy: CommandId };
type RevisionExpectation = {
	readonly baseRevision: number;
	readonly revision: number;
	readonly baseProgram: ProgramKey;
};
// install/open packets add the existing ProgramSpec, ProgramTrigger, and a bounded
// placement-addressed ArrayBuffer list. Open has no installed base expectation.
// command uses RevisionExpectation plus readonly ParameterCommand[].
// trigger names the expected applied revision and ProgramKey plus ProgramTrigger.
// release names VoiceId. cancel names its own commandId and target commandId.
// close names ProgramAddress. All scheduled effects carry an absolute frame.
```

Move the existing `ProgramTrigger` declaration from engine/program-values.ts:11 into contract and migrate its imports. Move `ProgramDemand` from engine/program-preparation.ts:15 into contract only because the reservation protocol needs the same numeric demand vector. Keep `ProgramReserve`, refund closures, graphs, resource accounts, worker request orchestration, and engine prepared-candidate types out of contract. No contract-to-engine import and no hand-copied ProgramTrigger or demand interface.

Separate `pending` from terminal outcomes structurally. Applied trigger results require a VoiceId. Applied installation results require revision, key, and actual frame. Refusal carries a typed reason. Cancellation requests return `cancelled`, `too-late`, or `unknown` for their target. They cannot rewrite its result. Generation-loss completion carries an explicit unknown-application status as described below. Avoid optional-field bags that admit an applied trigger without a Voice id.

`HostMessage` and `WorkletMessage` gain the necessary program protocol variants. Capability bootstrap is adapter-owned: protocol version, generation, actual ExecutionProfile, supported quantum, and prototype limits. There is no separate serialized executable graph and no alternate classifier.

## Ticket and revision transitions

1. The worker checks public request shape, library/edit bounds, expected document revision, and operation capacity. `surface.apply` remains the sole revision commit path. A rejected authored edit mints no admitted effect ticket and changes nothing. An accepted edit retains its desired revision even if runtime application later fails.
2. A ticket can be waiting for credit, transferring, binding, prepared, or waiting for reclamation. These are nonterminal states. A pending acknowledgement advances neither applied revision nor resident credit.
3. Admission reserves a terminal result slot and necessary cleanup channel capacity before ordinary work. The audio owner records each admitted ticket once. A duplicate phase packet with the same ticket is ignored or returns the cached phase response, without constructing, activating, or refunding again. Conflicting payloads under a retained id are protocol failures.
4. Check generation, Sound open lifetime, base revision, and baseProgram when accepting an effect and immediately before activation or command application. Also require its ticket to remain the Sound's current candidate. Target revisions may skip superseded revisions but cannot go backward. An old completion updates only its own ticket record.
5. Supersession names the pending target ticket. Keep at most one candidate per Sound. Retain one latest desired snapshot while cancelling/reclaiming the old candidate; do not allocate another candidate until its receiver reservation is released. Continue rendering the installed program.
6. The worker retains the installed ProgramSpec and applied revision from confirmed outcomes. Reconcile divergence with the existing `planEdit(desired, library, profile, kernels, [], installed, appliedRevision)`. This already produces a prepare effect when desired and applied revisions differ. It does not commit another revision. Do not call `surface.apply` with a manufactured no-op edit or add a second classifier. Serialize revision-changing submissions per Sound; newer accepted desired state can be coalesced while an effect is unresolved.
7. An eligible command applies through the shared queue at its requested frame, or the first available frame when late. It acknowledges the actual absolute frame. Future triggers declare the applied revision they require, so they cannot silently run the wrong pending program. A trigger intentionally targeting the still-installed revision remains legal.
8. A cold installation activates only after preparation, its requested frame, Voice reclamation, and `tailUntil`. The engine owns the readiness fact and reclamation. Control owns its ticket and the queue insertion. Activation swaps prepared ownership and sets the Sound start frame to the actual activation frame. It performs no graph construction or hash check.
9. A cancellation before activation removes the queued action, stops further candidate work, and produces the target's single cancelled terminal result only after candidate ownership is released. Its own request then completes. After activation, the target remains applied and the cancellation request returns too-late. Equal-frame races use queue insertion order. A ticket already completed is never admitted again.
10. Sound close stops new admissions, cancels its candidate, and schedules idempotent release of resident Voices. It remains pending while Voices and the Sound tail drain. The engine then disposes the installation and control removes the output binding. Only then is close applied and resident credit returned. Repeated close requests observe this same lifetime. Immediate device shutdown is distinct from graceful Sound close.

For bounded replay handling, start with a finite per-generation ticket history rather than an unbounded Set or a new acknowledgement/compaction protocol. Proposed fixture limit: 256 ordinary admitted tickets across both Sounds, with separately reserved cleanup requests and terminal records for all live obligations. Exhaustion refuses new ordinary admissions; it does not reclaim history or disable release/cancel/close. A fresh generation resets this quota only after old resource disposition. Duplicate traffic is coalesced. Public ingress cannot bypass the worker to flood the private audio port.

### Generation loss and unreachable acknowledgements

Increment generation and fence old send continuations before initiating device cleanup. Capture generation with each opening promise, listener, transferred port, worker response, and credit. Do not let an old opening install into the new device or close it on failure.

The worker's caller-facing result latch is the single terminal authority. A received applied result wins once. If device loss makes a still-unresolved result unknowable, complete it once as generation-ended with application unknown. A delayed old applied message cannot change that result. Do not assert cancelled/refused when audio might have activated before loss. Exactly-once observation can be guaranteed here; knowledge of unobserved execution across destruction cannot be fabricated.

Quarantine old receiver/transit reservations while closing the old context and ports. Successful explicit host disposal can confirm owner reclamation. Confirmed context closure can retire the old logical realm after all application references and pending continuations are dropped. This is not proof of immediate garbage collection. A timeout settles callers as unavailable but does not mint replacement global memory credit. If closure fails, report quarantined resources and refuse overlap that exceeds the global budget. Never wait forever for an acknowledgement from a destroyed processor, and never reuse old-generation credit in the new realm.

## Resource ownership and transfer

Reuse `ResourceLedger.reserve` and its idempotent refund closure. It is one aggregate account today, with a monotonic performed-work counter at resource-ledger.ts:75. Add disjoint worker, transit, and audio ownership records around that authority. Do not create a second set of demand arithmetic. Audio residency, transient preparation work, protocol occupancy, and performed operations are separate quantities.

| Phase | Owner and charge | Reclamation or transition |
| --- | --- | --- |
| Desired document and compiled ProgramSpec | Worker owns snapshots, compiler scratch, and retained program metadata. Bound whole library and expansion before compilation. | Drop superseded temporary compilation material. Retain accepted document snapshots as the current library does; refuse further authored work at the explicit library bound. This unit adds no snapshot collector. |
| Receiver reservation | Audio reserves the full candidate demand vector, output/scratch/graph allowance, and terminal capacity against its limits. Grant is keyed by the existing ticket and generation. | Grant is consumed once by that ticket, never added repeatedly as an available-byte delta. Revocation requires proof that transfer cannot still arrive. |
| Sender buffer preparation | Worker checks its own allowance before allocating zeroed backing. Reserve receiver credit before transmitting, and preferably before this allocation. | A successful transfer detaches sender backing. Worker releases its resident backing charge then, retaining any metadata it still owns. A failed post leaves owned backing charged until explicitly dropped. |
| Transit | The transferred backing has one physical ownership path and remains covered by receiver reservation. Worker tracks the outstanding transfer without counting a second resident copy of that backing. Structured-cloned metadata exists separately in both realms. | Receive consumes the reservation into receiver-owned state. No refund merely because the sender is detached. |
| Binding/prepared | Audio owns transferred backing, constructed views, graph objects, and all candidate output/scratch storage. Temporary validator/hash allocations have a distinct peak allowance. | Refusal/cancellation drops candidate graphs, all buffer/view references, and pending packet references before returning the reservation. Performed work remains spent. |
| Active | Audio owns the installed candidate, output bindings, and admitted Voices. An applied ticket releases its pending-work slot only. | Old installation is refunded only after the engine no longer retains it. New installation remains fully charged. |
| Draining | The old Sound and released Voices remain audio-owned until the actual engine retirement conditions pass. | Graceful close refunds after retirement/dispose. No active transition or growing list of draining replacement programs is allowed. |
| Device lost | Old generation ownership is quarantined independently of the new device. | Explicit disposal or confirmed realm teardown releases logical ownership. Unknown teardown cannot yield spendable credits. |

Use a reservation request/grant/transfer sequence. The grant reserves exact named demand, rather than an approximate byte hint. Duplicate grants cannot be spent twice. For this bounded prototype, send the candidate as one capped packet; it is the only installation chunk in flight for that Sound. Larger packets refuse. General large-graph chunk assembly is excluded.

Use the single ordered worker/audio channel to close cancellation races. The worker stops sending a ticket before its cancel or close barrier. Packets already posted precede that barrier. Audio retains reserved capacity until it has consumed or disposed those packets. A cancellation arriving through a separate main-thread path must first be serialized by the worker. Late packets after a completed barrier violate the private protocol and cannot resurrect ownership.

Receiver rejection after transfer frees receiver-owned backing; it cannot ask the detached sender to free it. The first unit drops rejected backing locally instead of implementing a return pool. Send the reclaim confirmation through reserved lifecycle capacity. Refund only the charge that owner actually holds. Neither reports every eight blocks nor lossy telemetry can be the sole source of reclamation credit.

## Bounded preparation and validation

The private worker port carries prepared internal data, but every realm boundary still parses shape and checks freshness. Main-facing authored requests are public input and must never accept raw executable graphs as an alternate API. A forged ProgramKey cannot bypass any boundary.

Before recursive validators or JSON hashing, use a bounded shape walk over plain data: finite safe integers, bounded strings, depth, arrays, objects, edits, and total entries. Reject cycles, unsupported object kinds, excess fields where they change resource interpretation, SharedArrayBuffer, resizable backing, duplicate backing entries, missing or extra placement storage, wrong lengths, and mismatched profiles. Charge transport bytes from bounded metadata and unique backing byteLength, not JSON.stringify of an ArrayBuffer. Existing JSON command sizing is insufficient for installations.

Then use the existing full `validateProgram` for capability/version/layout/demand/ports/region/order/lifetime/key checks. Derive storage demand using `programStorageDemand` and `programInstanceDemand`. Bind using the same kernels used by execution. No graph traversal or compiler is duplicated in control. A privately constructed engine candidate records successful validation; only its fallible factory can create it. Public ProgramSpec entry points still pass that factory. An asserted key or TypeScript cast cannot create a trusted candidate.

Source limits are 64 slots, 512 connections, and 1,024 parameters in program-preparation.ts:25. `PROGRAM_RESOURCE_LIMITS` provides 4 programs, 32 Voices, and 16,777,216 owned bytes, among other units. These are current prototype limits, not proof that every maximum combination is feasible. The existing queue has 128 ordinary entries, 1,048,576 ordinary bytes, 65,536 bytes per command, 64 commands per 128-frame window, and a separate release reserve.

For the next proof, declare stricter configurable test limits before coding: 2 Sounds; 1 candidate per Sound; 4 active-plus-candidate programs; at most 16 slots, 128 connections, and 256 parameters per program; metadata bounded by 32,768 bytes using a conservative text charge; transferred backing at most 65,536 bytes per installation; total installation envelope at most 98,304 bytes in a separately named installation limit. Check the reused 22 fixtures against these proposed caps in the Node step. The old 65,536-byte BusCommand limit stays unchanged. Do not silently enlarge it or turn these test caps into product limits.

Further initial proof allowances: one full candidate bind and one Voice construction per 128-frame callback window across both Sounds; at most eight program command applications per window, with bounded batch length and retained-Voice multiplicity. Those are deterministic work quotas, not measured safe timing thresholds. Keep global and per-Sound resident demand checks. Count validation, hash blocks, graph/view construction, command validation over residents, activation count, and cleanup work separately. Test exact fit and one unit short.

Worker grants pace candidate delivery. The audio message task can retain one bounded packet while its bind allowance is unavailable; a later worker pump, authorized by a render-progress message, performs binding in a message task. `process` only advances the allowance and publishes bounded progress. It does not construct the graph. A suspended offline context may therefore need to resume before another stage can finish. Never drain an arbitrarily large pending-work list in one callback.

The existing validator and graph constructor are synchronous. This first unit bounds one whole validation/construction job; it does not pretend to yield within SHA-256 or a constructor. Worker-side line allocation removes the large zero-fill allocation from audio. Output/scratch storage can be allocated once per bounded candidate or Sound, with views constructed in preparation. Graph wrappers, binding, and hashing remain audio-thread work. If the measured job is too large, reduce supported prototype bounds or separately design incremental preparation. Do not hide that cost outside the process timer. The Web Audio rendering algorithm executes associated rendering-thread tasks as part of its rendering loop. [Web Audio rendering algorithm](https://www.w3.org/TR/webaudio-1.1/#rendering-loop).

Voice admission remains an explicit limitation. `ProgramRuntime.trigger` at line 154 builds ProgramGraph and values at the actual admission frame. The scout's 52 typed bytes omit JavaScript objects and differ from the 228-byte declared fixture Voice demand. A per-window quota bounds multiplicity, but it does not make admission constructor-free. Prepared Voice pooling and full section-3 render-allocation compliance remain later work. Likewise, command validation creates heap objects today.

## One host, clock, and output path

The proposed call path is:

```text
Main authored request -> worker createCompositionSurface -> planEdit / compile
    -> worker preparer -> credited MessagePort -> AudiofaceProcessor
    -> RealtimeBusHost.receive -> bounded ProgramHost preparation/table
    -> the existing CommandQueue -> ProgramRuntime immediate operations

AudiofaceProcessor.process(currentFrame)
    -> RealtimeBusHost.render -> CommandQueue.drain(StampedBus)
    -> MasterBus render span: legacy contributions + ProgramHost contributions
    -> existing MasterLimiter -> existing meters / output
```

ProgramHost is a control-owned component with a bounded Sound table, ticket records, and resource ownership. It has no independent queue, origin, timer, or device listener. RealtimeBusHost supplies the only device-origin translation. Runtime frame counters reflect the spans that host rendered. Opening at host frame 8,000 must initialize the new runtime at that frame, rather than silently starting its scheduling coordinate at zero. Sound elapsed time starts at actual activation.

Introduce one engine-level contribution callback before `MasterLimiter.limit`, plumbed through StampedBus and supplied by control. It receives the existing block, offset, length, and frame. The callback renders retained programs into their separate prepared outputs, then adds selected mono output ports in stable Sound-open order to the shared sum. Keep A and B separately observable before summation. Never duplicate the limiter, sum outputs twice, or mix after protection. The no-program path must preserve legacy samples exactly. Arbitrary spatial bindings and native comparators remain excluded.

Keep pending preparation as bounded ownership data, not another future-event queue. On engine readiness at a render boundary, insert activation into the existing queue at the first eligible absolute frame. Its insertion occurs after entries already queued at that frame, making cancel/trigger races deterministic. Ticket arrival is distinct from activation-entry insertion. Do not leave a blocked installation at the queue head where it would stop unrelated Sounds. Continued triggers against the old revision may keep a replacement pending; there is no forced transition timeout.

Generalize CommandQueue's description to frame plus lifecycle class, while preserving existing behavior. Move `afterQueuedStart` to the host using queue lookup; normalize release against the queued Voice start. Preserve earlier-release replacement atomically, command-byte validation, release entry capacity, preorigin lookahead, late clamping, equal-frame insertion order, cancellation removal, and sliding-window checks. If adding close/cancel scheduling, account their fixed maximum bytes and entries in a separate reserved lifecycle class. Release-only booleans must not accidentally exempt arbitrary install/close payloads from all byte bounds. Terminal replies use reserved outbound records, outside the ordinary inbound queue.

The current queue's window checks inspect queued entries. Add a retained per-render-window spent-work allowance for new program admission/preparation so successive arrivals cannot each evade a quota after earlier entries drain. Reserved release/cancel/close work must be budgeted from the maximum live obligations at admission. Overload refuses new ordinary work and lets audio retire.

## Deletion and consumer map

| Existing owner | Proposed change and consumers that must migrate |
| --- | --- |
| control/composition-runtime.ts, control/index.ts | Delete the synchronous owner and export. Migrate every program-surface.test.mjs case to the same preparer/host protocol through test-only cloned realm endpoints. Keep createCompositionSurface as document authority. |
| engine/program-runtime.ts private prepare/install | Extract one prepared-installation factory; replace the constructor and cold install call sites together. Migrate program-support.mjs and direct constructor/install cases in program-runtime.test.mjs. No compatibility installer remains. Low-level executor tests may use the same factory without becoming another control owner. |
| engine/program-graph.ts, program-kernels.ts, layer-echo.ts | Thread provided storage through the one graph/kernel construction path. Reuse createEchoLine arithmetic. Keep its allocating legacy caller only because legacy Voice migration is explicitly excluded. A transfer test must prove the ProgramSpec path supplies backing rather than falling through that allocation. |
| engine/program-preparation.ts, contract/program.ts, engine/program-values.ts | Move shared numeric demand and trigger declarations, update all imports, retain a single validator and demand calculation. Do not duplicate schema types. |
| engine/command-queue.ts, control/bus-host.ts | Generalize the one queue and retain normalization/cancellation behavior. ProgramHost gets no independent scheduler. Preserve all existing scheduling and bus-host tests. |
| engine/master-bus.ts, stamped-bus.ts | Add the single pre-limiter program contribution point and clock propagation. This necessary integration was absent from the scout's four-engine-file estimate. |
| adapters/web/worklet.ts, worklet-protocol.ts, game-audio.ts | Transfer ports/buffers, parse bootstrap, bind one host, fence device generations and callbacks. Worker adapter delegates to control. No engine or patch import from adapter source. |
| apps/web build and scripts/test-support/program-worklet* | Reuse the bundler and fixtures for program-host proof. When all 22 comparisons run through the host, delete the old proof processor/page and old program-test emission. |
| scripts/verify-program-worklet.mjs | Move/rename into the host verifier with existing clean-tree, forced-build, hash, close, and negative-control logic retained. Since the old verifier retires, do not extract generic helpers with only one remaining consumer. |
| test/foundations/program-worklet-support.mjs and storage.mjs | Reuse schedules, references, comparators, and the allocation instrument. Rename only when imports migrate together. Keep the hand-wired oracle unchanged. |

Keep `GameAudio.pending/aging` only for the explicitly unmigrated legacy BusCommand path. New program operations must never use report aging as authority. No new duplicated legacy implementation is created. The inspected engine/control implementation files are at most 346 lines; source inspection found no prerequisite over-700 file. Enforce 700 lines per file and approximately 150 per function on the actual implementation, not guessed new-file counts.

## Verification sequence for the proposed build

### Node gate before browser integration

Use test-support endpoints that perform structuredClone with transfer and deliver queued messages explicitly. A synchronous shared-object pair would conceal detachment, mutation, and reordering errors. Inject duplicate, stale, delayed, and reordered deliveries at the endpoints without another production transport implementation.

Migrate existing surface/runtime cases as the owner changes. Add focused tests for credit-before-transfer, failed post, wrong version/layout/demand/key, malformed or oversized envelopes, duplicate backing, wrong profile, exact-fit/one-short quotas, and zero typed backing allocation on the supplied-line path. Measure temporary hash storage separately. Preserve frozen-command refusal, installed-capacity shrink/regrowth, and refusal-before-document-commit tests.

Exercise pending install, supersession before/after transfer, cancellation before/at/after activation, out-of-order applied revisions, duplicate terminal packets, close with held Voices, tail retirement, close/reopen with stale Voice ids, generation loss with an applied outcome in flight, stale opening promises, and saturated cleanup/terminal channels. Assert one caller-facing terminal result per admitted ticket and that applied installation bytes stay charged. Replay the same timeline with ragged spans, zero-length boundaries, and nonzero host origin. Open A and B at different host frames and compare separate output captures.

Gate the migrated Node unit with focused foundations, scheduler, bus-host, and relevant package tests, then existing typecheck/structure/check commands. Do not leave two production owner paths between gated steps.

### Browser capability and controlled asynchronous gate

First verify a real worker can exchange messages and transferred backing directly with the real AudioWorklet, using actual installed browser behavior. A Blob-backed worker is a reasonable alternative to an unverified data-URL worker while preserving a one-file page; revoke its URL at teardown. No browser compatibility survey is required. Explicitly report unsupported environments.

Use OfflineAudioContext to produce sample captures with controlled synchronization. Schedule distinct future quantum-aligned suspensions before rendering. The API quantizes suspension timing and rejects invalid or duplicate times. [OfflineAudioContext.suspend](https://www.w3.org/TR/webaudio-1.1/#dom-offlineaudiocontext-suspend).

At suspension, send the worker the next operation. If delivery continues while suspended, wait only for queued/prepared readiness. Resume before waiting for audible application or tail retirement. If rendering-thread message delivery stops while suspended, use a resume-to-next-checkpoint protocol and derive expected samples from recorded actual application frames. Do not claim preselected exact frames for a transport that did not meet them. This first capability result decides the deterministic test procedure.

Reproduce the existing 22 reference comparisons through the host plus the new two-Sound lifecycle cases at 48 kHz and 44.1 kHz. Compare independent pre-sum outputs and the protected sum. A closes and reclaims without changing B's isolated samples. Cold replacement compares the untouched old stream until retirement and a fresh candidate stream after acknowledged activation. It does not adopt a held Voice into a changed program.

### Actual running AudioContext correctness gate

Require at least one real AudioContext with output connected, user activation when needed, and verified advancing currentFrame. Open two Sounds through the worker, then send live edits, triggers, releases, and a pending replacement while audio is running.

Arm the worker before a 500 ms main-thread busy loop. During that interval the worker generates and sends additional commands over its direct port, rather than merely delivering an entire precomputed worklet schedule before the stall. Record bounded worker-send, audio-receive, requested-frame, actual-frame, ticket, and result data. Align main and worker time observations for the stall check; use device frames for execution assertions. Require at least one command created during the stall and processed while the main thread was unavailable. After recovery, compare a bounded audio-side pre-sum capture with a Node replay of the acknowledged actual-frame schedule. Late delivery may pass if it obeys the declared policy and reports the actual frame.

Advancing output plus a wrong revision, duplicate activation/refund, missing terminal completion after recovery, nonfinite samples, or capture mismatch fails. Suspended/unsupported/nonadvancing output is inconclusive. A timeout alone cannot establish successful cancellation or reclamation. Record close/worker/port cleanup and any quarantined ownership. Offline success cannot substitute for this gate. This is correctness under asynchronous delivery, without a realtime deadline or dropout-absence claim.

Final browser runs are headed and headless, with environment, actual quantum, exact source SHA, program/trace/build hashes, source cleanliness before and after, screenshots, and bounded result artifacts. Preserve sample corruption, processor error, and timeout negative controls. Add omitted-transfer, duplicate-credit/refund, and stale-generation fault controls so the verifier is proven to fail on those violations. Existing shipping pages receive fresh legacy null proof because their shared worklet bytes change.

The 5-second warmup/three 30-second randomized workload campaign, device budgets, native spatial equivalence, live transitions, full Voice pooling, shipping GameAudio migration, and sonic acceptance remain excluded. This unit must not claim those sections complete.

## Evidence and remaining adjudication

Read-only commands verified HEAD, full untracked cleanliness, the ea487fb-to-30b15bc changed-file list, all named source consumers, and current file sizes. Two focused Node assertion probes ran successfully on Node v24.20.0. The first confirmed wrong-version binding acceptance/full-validator refusal, unhashed aggregate-demand mutation/full-validator refusal, existing counter behavior for a preexisting buffer view, and sender detachment/receiver backing after structuredClone transfer. The initial invocation omitted the required `PAIR` argument to `compiled` and failed before assertions; the corrected invocation imported PAIR and passed. No source defect is inferred from that invocation error.

The second instantiated the existing `ProgramProofRun` for each of `PROGRAM_CASES`, inspected its program with `programStorageDemand`, and disposed it through `finish` without rendering a sample campaign. All 22 current cases fit the proposed program/backing caps. Observed maxima were 7 slots, 39 parameters, 10 connections, 17,916 bytes of conservatively charged ProgramSpec text, and 32,768 bytes of transferred-line demand. This measures the program body only; the final envelope overhead and the new installation cases still require build-time assertions.

The transfer observation is consistent with the HTML structured-transfer algorithm, which detaches ArrayBuffer backing during transfer. [HTML structured serialization with transfer](https://html.spec.whatwg.org/multipage/structured-data.html#structuredserializewithtransfer). No browser or timing test ran during this design review. The scout's 5.8 KB packet, 39,756 constructor-observed bytes, and Node admission timings remain fixture observations.

Lead decisions needed before the build: adopt full bounded audio validation for this slice; approve the concrete prototype caps and finite ticket-history limit; adopt graceful Sound close plus explicit unknown-application generation-loss completion; replace impossible unchanged-page hash requirements with fresh behavioral proof and recorded changed hashes. No engineering reason remains to add a second compiler, classifier, scheduler, or semantic identifier. Shipping device budgets, sonic policy, and library placement remain owner decisions.

This report and its digest are the only authored files from this review. Source and authoritative specifications remain unchanged. Markdown index refresh was attempted and refused with `Path outside root: /Users/alphab/.mdx/projects`; no index-root expansion was attempted. Both artifacts remain directly readable.
