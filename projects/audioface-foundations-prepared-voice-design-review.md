---
title: Audioface prepared Voice design review
type: projects
tags: [audioface, foundations, voice, admission, runtime, review, design]
summary: Independent source grounded review of the prepared Voice slot proposal at 3221511, resolving preparation versus exact frame activation, overlap accounting and bounded burst semantics with executable evidence.
status: draft
created: 2026-09-06
updated: 2026-09-06
project: audioface-next
related: [audioface-foundations-prepared-voice-scout, audioface-foundation-program-host-spec, audioface-foundation-runtime-probes-spec, audioface-foundations-runtime-host-browser-corrections-review]
confidence: high
---

# Prepared Voice design review

Target `3221511a59170b3fafaaa6924cf1a25f98a26b37`, read only, checkout `/Users/alphab/.mdx/TMP/pstack/audioface-foundations/worktrees/browser` clean before and after every probe. Host spec `3f32506eb9bbbddc3a9500455d3fa177e23aef370cd3ff2dfbd0f7d8f8aa7574`, probes spec `6615929b…`, document spec `c1927508…`, README `f34eb76a…` unchanged. Proposal `34362f19…`, scout digest `82c8cf29…`. The proposal's two probes import the integrated worktree, which is also at the target and clean. No source, spec or proposal edits, no agents, no remote actions.

Verdict: conditional. The architecture is right and reuses the actual runtime, host, preparer, ledger, scheduler, cells and proof automation. Four corrections are required before the contract is written, one deletion is rejected, and the remaining decisions are accepted. Every correction below is grounded in a source line or a probe under `prepared-voice-design-review/`.

## Decisions

| Candidate decision | Verdict | Basis |
| --- | --- | --- |
| Explicit `voiceCapacity` per retained Sound, preserved across cold candidates, carried on open and install preparation and multiplied once by `installationDemand` | Accept | Receiver credit must be recomputable from the packet (`program-envelope.ts:207`, `program-host.ts:247`), so the count belongs on `ProgramPreparation` and the Sound record in both realms. |
| Eight slots per Sound in the bounded proof only | Accept | Exact fit proven below for every fixture at both rates. |
| Explicit refusal when no ready slot exists, before queue admission | Change | It must also precede receiver ticket admission (`program-host.ts:352`), or every readiness refusal spends receiver history exactly as window refusals do today (F3). |
| One scheduler, one ledger, one compiler, no stealing, no second queue | Accept | Nothing in the proposal needs a second owner once F1 removes the activation workspaces. |
| Pooled resources never cross `ProgramKey` or generation | Accept | Candidate banks live in the candidate runtime and die with `dropCandidate` (`program-host.ts:512`). |
| General command work replaces the constructor Voice quota | Change, conditional | Accepted only with the F1 split, where activation is scalar writes over preallocated objects. If resolution or binding stays in `process()`, retain a per window activation bound equal to the resident bound. |
| `pump()` constructs one slot per opportunity and later resets dirty slots | Change | Construct the whole bank inside the runtime constructor under the credit already held; re arm at activation; no pump reset, no `preparing` or `reusable` state (F4). |
| Activation resolves values and validates bindings at the exact frame | Change | Resolution and binding validation move to reservation in the message task; activation cannot fail (F1). |
| Refactor to a preallocated indexed resolver and delete the one shot resolver | Reject | Under F1 the existing resolver is the single owner for install, command and reservation; a second resolver is duplication with no correctness need (F5). |
| Delete `preparationsPerWindow` | Accept | One declaration, zero consumers (`contract/program-host.ts:22`); `pump()` paces itself (`program-host.ts:238`). |
| Delete the public `ProgramRuntime.install` replacement path | Accept | Production callers: the constructor only (`program-runtime.ts:73`); six test lines in `program-runtime.test.mjs` (133, 139, 155, 158, 160, 422) migrate to constructor refusal and host activation cases. |
| Keep legacy `VoicePool`, `MasterBus`, `GameAudio` unchanged | Accept | They own class floors and stealing (`voice-pool.ts:24`, `:127`) and per start spatial construction (`master-bus.ts:119`); the program path never enters them (`bus-host.ts:72`). |

## Findings

**F1. Activation must not resolve or validate.** Location: proposal "Proposed ownership and state" and "Ordering"; source `program-runtime.ts:154` to `:200`. Observation: the proposal keeps `resolveProgramValues` and binding validation at the activation frame inside the queue drain, which is `process()`. The probes spec requires "Render consumes prepared entries without constructors or validation failures", and the host spec budgets kernel binding as message task work. Probe `probe-activation-split.mjs` case B resolves the same trigger at a reservation frame and at the activation frame: every frozen and modulated key is identical, and the only differing key is the live unmodulated cutoff cell. That follows from source: commands to any modulation dependency are refused (`program-runtime.ts:244` to `:257`), frozen keys are refused (`:242`), and the only live keys are cutoff and delay time and level (`program-preparation.ts:180`). So the complete resolution, the per trigger seeds (`program-values.ts:102`) and `bindProgramKernel` can run at reservation, and a malformed trigger or an out of range modulated pitch refuses before any slot is claimed. Activation then needs only frame dependent scalar work: `ProgramValue.copyFrom` of the live cells (`program-runtime.ts:178`), the filter's base capture (`program-kernels.ts:196`), state zeroing, `started`, `endFrame`, `mixEnds`, the numeric identity and the active order append. Correction: reservation resolves, binds and validates; activation arms and cannot fail. Caveat: the filter base is the one frame dependent number. Case C swept 25 mid ramp configurations and found 0 sample differences between a base captured at reservation and one captured at activation, so identity does not depend on it in the tested arithmetic. Capture it at activation anyway; it is one read and removes the dependence on rounding.

**F2. Reset is not enough; a slot must rebind per trigger.** Location: proposal reset list and `program-kernels.ts:171` to `:246`. Observation: every kernel closure captures its `Binding` at construction: tone pitch, glide and bend (`source-generator.ts:55`), filter kind, Q, base and envelope (`layer-filter.ts:39`), envelope stages and gain. Probe case A shows two triggers on the jittered fixture resolve different cutoffs and bind different filter cycles per frame (0.03987 versus 0.02594). A slot bound once and only "reset" would render the wrong trigger. Correction: the kernel's engine private operation is arm(binding, liveCells, frame) writing numeric binding fields, zeroing state and setting cells. To keep one DSP owner, extract the per sample step and the shape table from `phaseAccumulator`, `waveformShape`, `pitchBend` and reuse `tune` and `setNumerator` as they are; the legacy closures call the same functions.

**F3. Ticket history under a burst.** Location: proposal "Overload" and "Host and protocol proof" step 2. Observation from `probe-burst-accounting.mjs` on the current source with only the constructor quota lifted: 100 interleaved triggers on two Sounds consume 102 ordinary tickets and 306 records on the sender and the same on the receiver whichever boundary refuses, because the receiver admits before enqueue (`program-host.ts:352` then `:372`) and ordinary tickets cannot be withdrawn (`program-tickets.ts:79`). With the quota at 32 the window's Voice counter admits 32 and refuses 68; with it lifted the 64 work unit window admits 64, refuses 36, then the ledger refuses 32 inside the drain with `voices capacity`. All applied Voices land at one frame in sender order, 16 per Sound. Consequences for the proposal: the readiness check must precede `tickets.admit` so the receiver spends nothing on refusals; the sender always spends 3 records per trigger; with two opens a generation holds 254 triggers, so the proposed burst can repeat exactly twice before `ticket history capacity exceeded`, and the third burst fails on the sender at its 55th trigger. Under the bank: 16 admitted, 84 refused unadmitted, 16 of 64 work units, 16 of 128 entries, sender 100 tickets and 300 records per burst, receiver 16 and 48.

**F4. Per slot pump construction and pump reset add latency and a starvation path.** Location: proposal "Resource residency and work" and the pump scan. Observation: `pump()` prepares one packet per window (`program-host.ts:238`), and the browser posts progress every 1,024 frames (`worklet.ts:90`), so readiness of one eight slot Sound would take nine opportunities: at least 1,161 frames in Node and 9,216 frames, about 192 ms at 48 kHz, in the browser; the four program fit needs 36. Recycling a retired slot would wait for a further opportunity. The proposed scan order, an active Sound's dirty slot before the oldest candidate, lets a busy Sound starve candidate preparation indefinitely. Correction: construct the whole bank in the `ProgramRuntime` constructor under the credit already reserved; the ledger already charges the declared work at reservation (`resource-ledger.ts:71`), and the bank's declared work is `voiceCapacity` times the voice region's `installationOperations` (101 for the pair fixture against a sound region that hashes the program). A retired slot is ready at `reclaim` because activation arms it. `pump()` is unchanged. Root may instead keep one slot per pump as a contract choice, with the latency above stated.

**F5. The resolver replacement is duplication.** Location: proposal reuse map row for `program-values.ts`. With F1 there is no allocation free resolution requirement at activation, and reservation runs in the message task where allocation is budgeted. Keep `resolveProgramValues` as the single owner; add no workspace types. The `ProgramResolutionWorkspace` and `PreparedVoice.resolution` fields disappear.

**F6. Host file size.** `program-host.ts` is 587 lines. Reservation bookkeeping, readiness refusal, cancel and close and cold activation returns and the terminal release add roughly 60 to 90 lines. Keep reservation state in the engine bank module and give the host one map and one release point in `finish()` for trigger tickets, so the host stays under 700 without a split; plan the split of `receive()` envelope correlation if it does not.

## The split, by realm

| Step | Realm and task | Work | Can fail |
| --- | --- | --- | --- |
| Credit | Worklet message task | `installationDemand(program, voiceCapacity)` reserved once; `voices` unit counts the bank | Yes, before transfer |
| Prepare | Worklet message task, `pump()` | Packet validation, sound graph, whole Voice bank: graphs, kernels, cells, mix sources, `mixEnds`, one `Float64Array` per kernel | Yes, candidate dropped |
| Reserve | Worklet message task, `operation()` | Trigger shape, revision and program checks, `resolveProgramValues`, `bindProgramKernel` per slot, VoiceId string, ready slot claim, then `tickets.admit` and enqueue with rollback of the claim on enqueue failure | Yes, unadmitted |
| Activate | `process()` at the ordered frame | `copyFrom` live cells, filter base, zero phase and biquad history, `started`, `endFrame`, `mixEnds`, serial, active order append, existing `finish` reply | No |
| Retire | `process()` in `reclaim` | Remove from active order, slot ready | No |
| Release credit | Message task | Candidate cancel, close after `idle`, `confirmDisposal`; once, with the runtime | No |

Equal frame order is unchanged: a command queued before a trigger updates the Sound cells before `copyFrom`, and the active order is queue order, so the `Math.fround` sum order at `program-runtime.ts:320` is preserved. Slot index never enters a seed and never orders summation.

## Accounting and residency

| Dimension | Owner and bound | Under the bank |
| --- | --- | --- |
| Resident bank | ledger `voices`, 32 global (`resource-ledger.ts:6`) | Sum of `voiceCapacity` over active and candidate programs; static partition |
| Active and tail | runtime active order | At most the Sound's bank; no fade state; legacy pool and fade capacity untouched |
| Ready credits | runtime readiness counters, not a ledger unit | Capacity minus reserved minus active; the trigger refusal boundary |
| Queue | 128 entries, 1 MiB, 60 s lookahead, 36 lifecycle | A reserved slot is held for the trigger's whole queue life |
| Ticket history | 256 ordinary, 768 records per generation, both realms | 3 records per trigger; sender always spends |
| Work | 64 units per 128 frames | One unit per trigger; activation is scalar writes under F1 |

`probe-demand-fit.mjs` reserves four proposed eight slot credits for each of `pair-delay`, `pair`, `pair-jittered` and `pair-flat-jittered` at 48 kHz and 44.1 kHz through the real `ResourceLedger`: exact fit; the exhausted units are exactly `programs` and `voices`; one more Voice refuses with `voices capacity`, a fifth program with `programs capacity`, and a nine slot fourth program refuses. Every other unit keeps large headroom.

Starvation without policy: triggers scheduled far ahead hold slots for up to the 60 s lookahead, so present triggers on that Sound receive explicit refusals until cancellation or activation frees them. This is the accepted behavior of claim at admission and needs a proof case, not a policy.

## Transitions challenged

| Transition | Rollback and identity | Refund and wake |
| --- | --- | --- |
| Reserve then enqueue fails | Claim returned before the throw reaches `receive`; no serial consumed | No credit involved; ticket unadmitted |
| Cancel before frame | `scheduler.remove` plus reservation return in `finish()` | Record consumed as today |
| Cold activation with a queued trigger on the old runtime | `activate()` refuses and removes those triggers with the stale program message; old bank disposed with the old runtime | Old credit reclaimed once (`program-host.ts:315`) |
| Trigger before candidate at one frame | Trigger activates, candidate requeues (`program-host.ts:310`) | Unchanged |
| Live edit while reserved | Cells change; `copyFrom` at activation reads them; modulation dependencies cannot change | None |
| Close | Remaining reserved triggers of the Sound refused and removed; `releaseAll`; `idle` ignores ready and reserved slots | Bank refunded with the runtime after `idle` |
| Candidate cancellation | All candidate slots die with the runtime | Once via `dropCandidate` |
| Generation loss | Tickets settle; reservations released with them; runtimes quarantined | Only `confirmDisposal` refunds |

Reset completeness for the curated Voice region, which admits only tone, three biquads and envelope (`program-preparation.ts:151`): tone phase (`source-generator.ts:118`); biquad `x1 x2 y1 y2`, `tunedCutoff`, coefficients and the captured absolute frame (`layer-filter.ts:45` to `:50`, `program-kernels.ts:198`); envelope has no state; per kernel cells; `outputs`; `released`, `endFrame`, `mixEnds`. Echo and delay lines are Sound region only, so no line is ever reused across Voices.

## Types and boundaries

`voiceCapacity` on `ProgramPreparation`, validated in `readProgramMessage` as a nonnegative safe integer no larger than the host bound. The slot union needs `ready`, `reserved` and `active` with `released: number | null`, matching the current `ResidentVoice`; `preparing`, `reusable` and the separate `tail` variant carry nothing. `ProgramVoiceReservation` stays engine private. The bank goes to one engine module beside `program-runtime.ts` (365 lines). With the bank in the credit, the runtime's `reserve` callback and the `building` toggle at `program-host.ts:250` become dead in the host path; pass an explicit no op reserve rather than a mutable flag.

## Next executable unit

Engine: kernel arm with shared arithmetic; bank module; `reserveVoice`, `activateVoice`, `cancelVoice`; `countStorage` zero and zero graph constructions per activation; the scout's no reset negative control kept as a failing control; eight roots, repeated roots, reversed physical storage; reservation before a ramp with activation at 299, 300, 364, 428 and 450 compared with the fresh trigger reference; invalid modulated pitch refused at reservation with no slot or serial change.

Host: `voiceCapacity` in open and install envelopes and demand; readiness refusal unadmitted; one release point for reservations; cancel, close, cold activation and generation end returns; the 100 trigger burst twice with the ticket counts above and a third burst refused on the sender; exact 32 fit and one short; a future reservation blocking a present trigger until cancel.

Browser: one interleaved eight plus eight burst case at both rates in `verify-program-worklet.mjs`, headed and headless, the 22 cases and ten controls retained, artifact hashes recorded, per activation typed storage and graph constructions recorded. Structural proof only; no deadline, dropout, heap or garbage collection claim.

Gates as the proposal lists them, plus the focused runtime, host, protocol and browser tests.

## Limits

No implementation was attempted. The activation split was verified on the curated kernel set; a future Voice region kernel with state that depends on a live value would need the same analysis. The base capture sweep is 25 configurations on one fixture. Browser numbers are quoted from the existing exact SHA evidence.

## Evidence

`/Users/alphab/.mdx/TMP/pstack/audioface-foundations/prepared-voice-design-review/`: `environment-before.txt`, `environment-after.txt`, `probe-demand-fit.mjs` and `.log`, `probe-activation-split.mjs` and `.log`, `probe-burst-accounting.mjs` and `.log`.
