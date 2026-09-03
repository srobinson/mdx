---
title: Audioface prepared Voice design clarification
type: projects
tags: [audioface, foundations, voice, admission, runtime, review, design]
summary: Appendix to the prepared Voice design review at 3221511 resolving whole bank construction work bounds and exact sender versus receiver ticket history for repeated bursts.
status: draft
created: 2026-09-06
updated: 2026-09-06
project: audioface-next
related: [audioface-foundations-prepared-voice-design-review, audioface-foundations-prepared-voice-scout, audioface-foundation-program-host-spec]
confidence: high
---

# Prepared Voice design clarification

Appendix to the design review. Target `3221511a59170b3fafaaa6924cf1a25f98a26b37`, read only, browser checkout clean before and after every probe, host spec `3f32506e…` unchanged. The review report and its three probes are preserved unchanged; two new probes live beside them.

## 1. Whole bank construction

**What existing demand already charges.** `installationDemand` (`program-preparation.ts:59`) sums the storage demand, the Sound region instance demand and one program; `installationEnvelopeDemand` adds the metadata bytes (`program-envelope.ts:211`). Every unit is a `ProgramDemand` field, including `installationOperations`, which is a declared work unit, not storage. The proposal's bank adds `voiceCapacity` times `programInstanceDemand(program, "voice")` (`:213`), so the same vector carries the bank's `voices`, `ownedBytes`, `slots`, `parameters`, `connections` and `installationOperations`. The ledger charges the declared `installationOperations` into `performedInstallationOperations` at reservation and never refunds it (`resource-ledger.ts:71`). Charging bank residency therefore already charges the bank's declared construction work in the existing unit. No aggregate construction contract beyond the credit vector is needed; what the contract must state is that one credit's declared work is the work one pump job performs.

**What per window budgets govern.** The queue's work units, batches and the current `voice` counter govern queued commands and triggers only (`command-queue.ts:137`). Preparation is governed by `pump()`, which prepares one waiting packet per window (`program-host.ts:238`), and by the packet caps applied before construction: 16 slots, 128 connections, 256 parameters, 32,768 metadata bytes and 65,536 backing bytes per program (`program-envelope.ts:185`, `contract/program-host.ts:16` to `:20`), plus 32 resident Voices global. Those caps bound one job's declared work without any new number.

**Counts, from `probe-construction-work.mjs`.**

| Fixture, 48 kHz | Voice ops | Bank of 8 | Bank of 32 | Sound region ops | Credit without bank | Credit with 8 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| pair-delay | 52 | 416 | 1,664 | 8,200 | 8,255 | 8,671 |
| pair | 52 | 416 | 1,664 | 7,208 | 7,263 | 7,679 |
| pair-jittered, flat twin | 53 | 424 | 1,696 | 7,208 | 7,264 | 7,688 |

Worst case under the existing caps, every slot a curated Voice kernel: 416 operations per Voice, 3,328 for eight, 13,312 for the largest bank the global bound allows, against 16,384 for one delay line at the backing cap that a single pump job already performs today. Owned bytes: 228 per Voice, 1,824 for eight, 7,296 for 32.

**Work actually executed in the rendering thread message task.** Today one pump job runs the bounded packet walk, `validateProgram` with the key hash and per slot binding, and the Sound graph over the transferred backing: nine typed arrays and 36 to 40 KB of views, median 0.165 ms in Node. A bank adds, per Voice, six kernel bindings and closures, two Maps, seven small typed arrays of 52 bytes and the mix sources: 56 buffers and 416 bytes for eight, 224 and 1,664 for 32. Measured in Node as a relative figure only: a bank of eight is 0.038 to 0.044 ms median, about a quarter of the existing job; a bank of 32 is 0.148 to 0.155 ms, about nine tenths of it. Maximums over 200 runs stayed under 0.76 ms. This is not a device claim; the proof records the worklet's own message task milliseconds as it already does.

**Composition.** One candidate per window is unchanged: `waiting` is first in first out by arrival and `pump()` takes one packet. The bank is built inside the `ProgramRuntime` constructor of that packet, so the credit's whole declared work executes in that one job and the candidate reaches `pending: prepared` after one pump, exactly as today. Cancellation before activation is `dropCandidate`, which disposes the runtime and its bank and reclaims the credit once. Fairness needs no cursor because there is no per slot queue; a busy Sound cannot delay another packet. A retired slot is ready at `reclaim` because activation arms it, so recycling needs no pump.

**Authority replacing the one Voice construction per window quota.** Construction: one preparation job per window, whose declared work is its credit's `installationOperations`, bounded by the per program caps and the global Voice bound; the ledger records it. Activation: general command work at one unit per trigger, bounded above by ready slots. The queue's `voice` counter and `voicesPerWindow` are deleted with that pairing; `preparationsPerWindow` was already dead.

**Recommendation.** Whole bank construction with the credit as the explicit aggregate bound. Cold start stays one pump after credit. The rendering thread burst grows by the bank's declared share, five percent of the fixtures' declared credit and about a quarter of the measured job for eight slots, and never beyond one permitted delay line even for 32. Staged preparation with a fair cursor and coalesced progress would cost nine acknowledged opportunities per Sound, about 192 ms at 48 kHz in the browser, plus cursor and coalescing state, and it would only be justified by a measured browser message task budget that root has not set. If the proof's recorded message task time for a bank job proves unacceptable, staging is the fallback, with the numbers above as the comparison.

## 2. Ticket and record costs

**Authorities.** Both realms use `ProgramTickets.admit` (`program-tickets.ts:32`): an open or trigger reserves three records and one ordinary ticket, another ordinary kind two; cancel, release and close reuse the owner's reserved records and count nothing. The sender admits before posting (`program-preparer.ts:193`). Ordinary tickets cannot be withdrawn (`program-tickets.ts:79`), so a receiver refusal, admitted or not, refunds nothing on the sender (`program-preparer.ts:404` to `:414`). The receiver admits a trigger at `program-host.ts:352`; the accepted contract moves the readiness check before that line.

**Exact costs, from `probe-history-costs.mjs`.**

| Event | Sender ordinary and records | Receiver ordinary and records |
| --- | --- | --- |
| Two opens | 2 and 6 | 2 and 6 |
| One 100 trigger burst, 16 ready | 100 and 300 | 16 and 48 |
| 84 readiness refusals | included above, no refund | 0 and 0 |
| 2 cancels, 14 releases, 2 closes | 0 and 0 | 0 and 0 |
| After two bursts | 202 and 606 | 34 and 102 |
| Third burst | 54 admitted, then refused | 16 more admitted, 50 and 150 |

The sender's two limits coincide: with two opens, the 255th trigger is refused because ordinary reaches 256 and reserved reaches 768 together. The real two realm path on the current source confirms the arithmetic and the boundary: bursts one and two land 32 Voices each at one frame, the sender holds 102 then 202 ordinary tickets whether the queue refuses 68 or not, releases and full retirement change neither count, and the third burst throws synchronously from `preparer.trigger` at its 55th call with `Audioface ticket history capacity exceeded.`, leaving the sender at 256 and 768.

**Finite expectations for the next proof with unchanged sender policy.** Exactly two full 100 trigger bursts per generation with two opens; each yields 16 applied and 84 refused with `admitted: false` and the readiness message. The third burst is a separate labeled case: 54 triggers admitted on the sender, of which 16 apply and 38 are readiness refusals, then the 55th refuses on the sender. No in generation recycling, no refund and single ordered delivery are preserved; no ready credit protocol is added.

**Avoiding mislabeling.** A sender history refusal is synchronous and never has a ticket: in the browser the worker posts a `program-outcome` without a preceding `program-ticket` (`worker.ts:83` to `:90`). A readiness refusal always has a ticket and an unadmitted result. The proof asserts three things per refusal: the presence or absence of the ticket, the message text, and the counts, sender ordinary equal to two plus one hundred per burst and receiver ordinary equal to two plus sixteen per burst. A readiness assertion that does not check the sender count would pass on history exhaustion by accident.

## Evidence

`prepared-voice-design-review/`: `probe-construction-work.mjs` and `.log`, `probe-history-costs.mjs` and `.log`, `environment-clarification.txt`. Original review probes and logs unchanged.
