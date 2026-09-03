---
title: Audioface foundation program host contract
type: design
tags: [audioface, foundations, host, worker, lifecycle, resources]
summary: Bounded prototype contract for worker preparation, ticketed installation, ownership and browser verification.
status: active
created: 2026-09-05
updated: 2026-09-05
project: audioface-next
related: [audioface-foundation-document-spec, audioface-foundation-runtime-probes-spec, audioface-foundations-runtime-host-next-scout, audioface-foundations-runtime-host-design-review]
confidence: medium
---

# Program host prototype

This specification refines the approved foundation runtime probes for one executable unit. Source baseline is `30b15bcf8ff3f42b5afd25c296cc0e8afd633e21`. Lead adjudication incorporates Fable's scout and Astra's independent design review. Fable independently accepted the choices and lifecycle with three narrow bound corrections, incorporated below. The lead authorizes implementation against this corrected contract. Prototype limits below are engineering test limits, not shipping budgets. No sonic transition policy or product library placement is selected.

## Ownership and execution

The worker owns `createCompositionSurface`, desired revision, the existing `planEdit` and `compile` calls, and preparation. Main owns bootstrap and device lifetime. Transfer a direct worker/worklet `MessagePort`; do not introduce a relay fallback or second scheduler. Preserve one serializable `ProgramSpec`, one compiler and one classifier. Replan desired/applied divergence through the existing planner against installed state without an additional authored commit.

Opening a retained Sound may supply an optional existing `SeedMap` as a compilation input. Snapshot caller data at open and retain that immutable map for the Sound lifetime. All compilation, planning, reconciliation and cold re-preparation for that Sound use it through the existing authorities. A fresh open without a map uses the existing placement-label defaults; unmapped placements retain existing compiler behavior. The map does not change authored placement identity or introduce a library persistence policy. Effective seed labels remain part of normal ProgramSpec content and ProgramKey derivation. Worker request representation must be structured-clone safe and bounded by the input metadata policy; do not retain unbounded map data or add a second compiler/message kind. Prove mapped-flat versus nested equality before and after cold re-preparation, caller-mutation isolation, and unchanged default behavior.

Audio `ProgramHost` composes into the existing realtime bus host with its queue, clock and admission rules. Add a stable ordered contribution before the existing limiter, preserving separate Sound outputs until summation. Align new runtimes to the host's current absolute frame. No post-limiter mixing or private secondary queue.

Compile, key generation and backing allocation run off the rendering thread. Receiver performs bounded envelope/structural checks before full existing `validateProgram`, including key recomputation, implementation versions and authoritative demand validation. Binding alone accepted an incorrect kernel version in the review probe; changing aggregate demand preserved the key but failed full validation. Never treat a matching key as demand validation. Supplied buffers must match declared, independently validated requirements. Extend the existing validator if needed; do not duplicate it.

Audio message-task validation, hashing, graph construction, buffer views and kernel binding still consume rendering-thread work. Budget and instrument them independently of process callbacks. This unit does not certify allocation-free Voice admission or realtime deadlines. Activation uses staged state at the eligible render boundary. Unexpected validation/construction failures preserve old playback and ownership.

## Prototype bounds

| Quantity | Limit |
| --- | ---: |
| Resident Sounds | 2 |
| Prepared candidates per Sound | 1 |
| Total active plus candidate programs | 4 |
| Resident Voices, global | 32 |
| Slots per program | 16 |
| Connections per program | 128 |
| Parameters per program | 256 |
| Conservatively charged installation metadata, including envelope fields | 32,768 bytes |
| Transferred backing per installation | 65,536 bytes |
| Complete installation envelope plus backing | 98,304 bytes |
| Candidate preparations per 128-frame window, global | 1 |
| Voice constructions per 128-frame window, global | 1 |
| Program command batches per 128-frame window, global | 8 |
| Parameter commands per batch | 32 |
| Reserved lifecycle queue entries for release, close and activation | Resident Voices plus two per Sound, 36 here |
| Reserved lifecycle envelope | 65,536 bytes per entry |
| Ordinary queue entries | 128 |
| Ordinary queued bytes | 1,048,576 bytes |
| Ordinary command envelope | 65,536 bytes |
| Command work units per 128-frame window, global | 64 |
| Ordinary lookahead | 60 seconds, converted to profile sample frames |
| Ordinary admitted tickets per generation | 256 |
| Total retained result records per generation, including reserved cleanup | 768 |

Existing `PROGRAM_RESOURCE_LIMITS` constrain remaining demand units. Installation envelopes have their own byte cap; ordinary commands retain their existing cap. Metadata includes routing/identity/storage descriptors and envelope overhead. Bound fields and collection sizes before canonicalization, deep validation or allocation. Demonstrate fixture fit and exact-fit/one-short rejection; never enlarge caps silently.

A batch cannot hide work. Each contained parameter command consumes a command work unit; an ordinary legacy command consumes one. The batch limit and total command-work limit both apply. Preserve existing release normalization, frame-window accounting, equal-frame insertion order and late-command actual-frame reporting. Reserved lifecycle traffic must remain possible when ordinary capacity is exhausted, within its separate entry and envelope bounds. Cancellation takes no queue entry, matching the existing local cancellation path. Candidate preparation and Voice construction allowances remain consumed across repeated calls within the same window; command binding is charged through command work units.

For every ordinary ticket, reserve one cancellation result record. For trigger/open tickets also reserve one release/close result record. The worst case is 768 records. Only a known target admits a cancellation request. The first admitted cancellation consumes its reserved record; later cancellations with other identities are refused without admission. Unknown targets receive an unadmitted unknown reply with no retained history. Retries reuse their identities; do not recursively admit unlimited cancellation requests or recycle history within a generation. Ordinary exhaustion rejects new work while reserved cleanup remains possible. A rejected unadmitted request cannot require unbounded history. Reset only after old-generation disposition.

Every accepted host edit consumes ordinary admission capacity, including unopened compositions, racks, document-only edits and edits with no runtime effect. Reserve that capacity before calling the document surface: its commit must not precede the host admission decision. Keep the raw mutable surface private to the preparer; retain existing immutable snapshot access and validation behavior. Do not reject otherwise legal authoring solely because no Sound is open, or introduce a second host API to bypass this budget.

A document-only edit settles its admitted ticket once with an explicit document-commit result and accepted revision. It does not claim audible application, advance an installed Sound's applied revision, reserve receiver credit or allocate audio storage. An edit with a runtime effect retains separate authored acceptance and eventual application outcomes. Exhaustion must leave the document revision and retained history unchanged. This bounds host-owned acceptance through the existing ticket budget without introducing a product library collector.

## Identity and protocol

Reuse `CommandId` for requests and the successful open ticket as `openedBy`, identifying Sound lifetime. Reuse existing `CompositionId`, `ProgramKey` and `VoiceId`. Move needed existing `ProgramTrigger` and `ProgramDemand` declarations into contract with caller migration; do not copy them or add synonymous brands.

The supported transport preserves sender order and delivers each posted envelope once within a generation. An envelope rejected before admission ends that attempt and must not be automatically redelivered; retry cleanup with a new identity. Same-identity replay is supported for already admitted requests. Arbitrary replay of previously unadmitted cleanup is outside this bounded prototype transport contract; no unbounded rejection tombstone history is introduced. The real worker/port milestone must verify that its adapter honors these requirements. If delivery becomes uncertain, use generation-loss/application-unknown disposition rather than assuming rejection and replaying.

Messages distinguish reserve, grant, reclaimed, open, install, command, trigger, release, cancel and close. Every correlated message carries command identity and generation. Grants bind the request identity, generation and exact receiver demand. Install carries openedBy, base revision, target revision, base program, requested frame, ProgramSpec and supplied storage. Commands carry the same ownership/base expectations and bounded parameter commands. Triggers carry expected installed revision/program and explicit trigger data. Storage entries identify placement and transferable backing. Direction, stage and payload validation must prevent an acknowledgement from being interpreted as a new admitted operation.

These are required semantics, not permission to create a single permissive union with optional fields. Encode the concrete legal variants and reuse existing shared declarations. The review appendix supplies the candidate shapes; reconcile them with this specification and existing identities.

## Outcomes and retirement

Pending is nonterminal. Every admitted request has one terminal result and one caller latch settlement. Cancellation has its own command identity and target ticket. Its result is cancelled, too-late or unknown; it cannot rewrite an already applied target. Deterministic equal-frame order resolves races. Duplicate, stale, mismatched-base and reordered messages must not activate twice, refund twice or roll back a newer revision.

Graceful close releases Voices, drains tails, disposes and refunds, then reports applied with the actual frame and reclaimed confirmation. While draining it may report pending. Device teardown is a distinct operation. Generation loss settles unresolved callers once with generation-ended and application unknown. It cannot fabricate cancellation or application when execution was not observed.

Command effects are not installation candidates. Ordered live command tickets may be in flight per Sound within ordinary bounds, each authored against its predecessor's revision. Do not automatically cancel an earlier command when a later live edit arrives. The host applies them in queue order and refuses a stale base. Maintain an explicit command-planning base distinct from the installed Sound's genuinely applied revision. Advance that base on command submission and reset it to the applied revision on command refusal or installation settlement. Only a host applied outcome advances the audible applied revision. Reuse the existing classifier against the installed program and its capacities; acknowledgement lag alone is not a reason to prepare a cold replacement.

Triggers issued after submitted live commands use the command-planning revision as their expected predecessor revision, together with the installed program identity. Keep strict receiver revision and program checks; do not accept arbitrary earlier revisions merely because the program key matches. A trigger during a pending installation targets the currently installed program unless a different activation dependency is explicitly represented.

A cleanup request that the receiving realm cannot queue is rejected before admission, consumes no retained result record, and may be retried under a new identity. Once queued, it is admitted, retains its reserved record through one terminal result, and retries reuse that identity. Validate local envelope constraints before provisional cleanup admission. If the receiver rejects without admission, remove only the sender's provisional unsettled cleanup record, release its owner pointer, and restore local closing state. Do not withdraw an admitted ordinary edit whose document commit already occurred or erase terminal history. A local send failure proven to occur before delivery also withdraws only provisional unsettled cleanup state, restores the owner, and permits a new-identity retry. Do not retain a terminal cleanup record for a request that was never delivered or admitted. A transport error with uncertain delivery instead follows application-unknown and quarantine rules. Ordinary edits already committed remain admitted and retain their history.

Queue insertion and ticket admission must commit together or roll back together. Mark a Sound as closing when cleanup is accepted by the host; an unadmitted rejection cannot permanently disable it.

One candidate and one latest bounded desired snapshot may coexist per Sound. Supersession names the affected ticket. Cancellation before activation reclaims the candidate; after activation it is too late. Cold installation waits for prepared state, requested frame and old Voice/tail reclamation. Frozen edits require preparation in both scopes; runtime frozen commands remain refused. No audible transfer or overlap policy is introduced.

Credit precedes transfer and reserves the full receiver demand vector. Sender backing charge ends only on verified detachment while transit remains accounted. Applied releases pending-work capacity, never resident audio storage. Receiver owns rejected transferred backing and returns credit only after logical reclamation. Distinguish storage from performed work; work is not refunded. Lost-generation resources stay quarantined until confirmed disposal or teardown. Timeout alone cannot create reusable credit. Prove terminal/lifecycle result capacity survives ordinary saturation and that old device loss cannot leave caller latches unresolved forever.

## Coherent implementation and proof

Deliver Node protocol/state ownership first, then actual worker/port browser execution as one bounded unit. Use cloned transfers in Node tests, not shared mutable endpoints. Migrate `composition-runtime.ts` callers/tests into the realm-pair path and delete the replaced implementation. Reuse echo math with supplied lines. Preserve existing scheduler and limiter consumers; do not duplicate the host. Retain legacy report aging only for explicitly unmigrated legacy callers.

Migrate all 22 existing program comparisons to the real host path before deleting superseded proof processor/page/verifier glue. Keep independent oracle arithmetic and shared capture/session helpers. Shared host edits may change embedded worklets in existing pages, so record artifact deltas and rerun legacy null tests; byte identity is not required for changed shared code.

Required tests include two-Sound isolation, nonzero origin, ragged spans, stamped commands, delayed installation, supersession, cancellation before/after activation, stale generation/base, saturation of each bound, exact refunds, active residency after applied, transfer refusal, close with resident Voices and full generation teardown. Probe malformed version/demand/storage packets. Distinguish new backing allocation from constructing views in instrumentation.

Use actual worker and transferred port in headed/headless browser runs. Controlled offline suspend/resume makes async scenarios reproducible; resume before awaiting activation that needs rendering progress. Also run an actually advancing AudioContext with worker-created commands during a 500 ms main-thread stall. Unsupported or nonadvancing realtime output is inconclusive; observed invariant failures are failures. Preserve exact SHA, hashes, environment, actual frames, correlated outcomes and bounded captures. This is correctness evidence, not deadline or dropout certification.

Pooled Voice admission, active transitions, spatial comparators, deadline campaigns and broad production migration remain later work. If implementation reveals a necessary dependency, present a bounded source-grounded conflict before expanding this unit.
