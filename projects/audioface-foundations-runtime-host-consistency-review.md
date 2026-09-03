---
title: Audioface foundations runtime host consistency review
type: projects
tags: [audioface, foundations, runtime, host, worker, worklet, contract, review]
summary: Focused consistency check of the refined program host contract against the scout, the independent design review, the lead adjudication and the frozen source at 30b15bc; the choices, lifecycle and deletion rules hold, three bound statements need small corrections before implementation.
status: draft
created: 2026-09-05
updated: 2026-09-05
project: audioface-next
related: [audioface-foundation-program-host-spec, audioface-foundations-runtime-host-design-review, audioface-foundations-runtime-host-next-scout, audioface-foundation-runtime-probes-spec]
confidence: high
---

# Runtime host consistency review

Target document `/Users/alphab/.mdx/design/audioface-foundation-program-host-spec.md`, SHA-256 `bbcb15bff3f5ad1c6702b3a35e7dec35c297b6ab9a3736d881b0616e225c42d9`, 88 lines, verified on disk. Inputs: the design review digest with its appendix, the lead adjudication, the design review report for detail, my scout, the runtime probes specification sections 1 to 3, the document specification section 5, and the runtime decisions record. Source read at frozen browser checkout `30b15bcf8ff3f42b5afd25c296cc0e8afd633e21`, clean before and after (0 changes, 0 untracked). One read-only Node probe ran outside the checkout; its script, log and JSON are in `/Users/alphab/.mdx/TMP/pstack/audioface-foundations/runtime-host-consistency-review/`. No source, specification or report was edited. No agents, builds or broad gates.

## Verdict

**Refinements.** The four choices, the identity reuse, the lifecycle and resource rules, the deletion sequence and the proof gates are consistent with the reviewed inputs and with source. Three bound statements need one line corrections before implementation, listed first. Everything else is accepted with evidence.

## Corrections

| # | Contradiction | Evidence | Minimum correction |
|---|---|---|---|
| 1 | Table row "Bind operations per 128-frame window, global: 1" conflicts with "Command work units per window: 64", because every command application binds every slot and every resident. | `program-runtime.ts` lines 246 to 252 and 265 to 278 call `bindProgramKernel` per slot and per resident on each command; the design review meant one candidate bind (report line 134: "one full candidate bind"). | Rename the row "Candidate preparations (full validation plus graph construction) per window: 1" and state that command validation binds are charged to command work units. |
| 2 | Reserved lifecycle traffic "must remain possible when ordinary capacity is exhausted; document its separate bounds", but the table gives no inbound reserved bound. The 768 records bound history, not queue entries. | The existing scheduler has one reserved class: releases, exempt from entries, bytes and window (`command-queue.ts` lines 77 to 86), sized at or above resident Voices (`bus-host.ts` lines 62 to 75). Program releases, graceful closes and activation entries have no stated class. | Add one row: "Reserved lifecycle queue entries (release, close, activation), global: resident Voices plus two per Sound", 36 at these bounds, each charged at the ordinary envelope cap. State that a cancel takes no queue entry: it removes entries in the message task, as the local cancel does today (`bus-host.ts` lines 149 to 162), and consumes only its reserved result record. |
| 3 | Cancel results are "cancelled, too-late or unknown" (line 70), yet the reserved cancel record is per ordinary ticket (line 58). A cancel naming an unknown target has no record, so an admitted `unknown` result breaks "one result per admitted request" or requires unbounded history. | Existing local cancel returns `unknown` without state (`bus-host.ts` line 151). | State that `unknown` is an unadmitted reply with no retained record; a cancel is admitted only when its target is in the generation's history; the first admitted cancel per target consumes that target's reserved record and any later cancel with a different identity for the same target is refused unadmitted. |

## Accepted choices

- **Worker document authority, direct port.** Consistent across scout section 7, review "Four choices", adjudication and spec lines 20 and 22. `createCompositionSurface` is synchronous and already reserves tickets and generations for a separate owner (`composition-surface.ts` lines 22 and 23).
- **Full bounded validation.** `bindProgramKernel` checks values only (`program-kernels.ts` lines 66 to 170, no version check). `validateSlot` checks version, state layout and per slot demand against `ENGINE_KERNELS` (`program-preparation.ts` lines 91 to 100), `validateProgram` recomputes aggregate demand and the key (lines 74 to 81). `programKey` hashes neither slot demand, slot state nor aggregate demand (`program.ts` lines 69 to 110), so a matching key proves nothing about demand. Spec line 24 states exactly this.
- **Storage validation without a new authority.** After validation, each stateful Sound slot's `demand.capacityFrames` is derived from configuration by `lineDemand` (`kernel-preparation.ts` lines 113 to 124) and equals the line length `createEchoLine` allocates (`layer-echo.ts` lines 39 to 41). Required backing per placement is therefore `capacityFrames` times four bytes from the validated slot, and the packet check reduces to presence, uniqueness and exact length. Sufficient; no duplicate arithmetic needed.
- **Caps before deep work.** Spec line 54 orders field and collection bounds before canonicalization and hashing. `validateProgram` bounds slots first (line 34) but hashes last (line 81), so the 16, 128, 256 and 32,768 checks must precede it, as the spec says.
- **Identities.** `CommandId`, `CompositionId`, `VoiceId`, `PlacementKey` in `ids.ts`; `ProgramKey`, `ParameterCommand`, `ResourceDemand` in `program.ts`. `ProgramTrigger` (`program-values.ts` line 11, depends only on contract `Seed`) and `ProgramDemand` (`program-preparation.ts` line 15, extends contract `ResourceDemand`) can move to contract under `ALLOWED_EDGES` (`verify-structure.mjs` line 35) with import migration in engine index line 13 and `composition-runtime.ts` line 3. `ProgramReserve` stays in engine. Consistent with spec line 62.
- **Message direction.** The appendix's single union mixes inbound `reserve` with outbound `grant` and `reclaimed`. Spec line 64 requires direction validation and line 66 defers to reconciliation. The existing precedent is two unions, `HostMessage` and `WorkletMessage` (`bus.ts` lines 31 to 38); follow it. Observation, already anticipated by the spec.

## Accepted lifecycle and bounds

- **Tickets and records.** 256 ordinary tickets, one reserved cancel record each, one reserved release or close record for trigger and open tickets, worst case 768: arithmetic holds. Reset after old generation disposition matches quarantine (line 76).
- **Batch accounting.** 8 batches of at most 32 with 64 work units per window means at most two full batches per window; the 32 cap is a per message bound. Both apply as written. The existing window check counts entries, not contained commands (`command-queue.ts` lines 107 to 120), so the implementation weights program entries by contained commands and legacy entries by one. Spec line 56 says so. Existing runtime batch cap is 1,024 (`program-runtime.ts` line 214); 32 is stricter and must be enforced by the host before the runtime.
- **Per window quotas as retained allowances.** Candidate preparation and Voice construction happen in message tasks and admission, not as queue entries, so their per window limits need a retained spent allowance per rendered window, as the design review states (report line 166). Not contradictory; a note for the implementer.
- **Cold activation.** Waits on prepared state, requested frame and Voice and tail reclamation: matches the current guard (`program-runtime.ts` lines 95 to 97) and the recorded cold replacement limitation in the runtime decisions. Frozen commands refused (line 223). Consistent.
- **Applied keeps storage charged.** At activation the replaced installation is refunded once the engine drops it (`program-runtime.ts` lines 99 to 102 today); the new installation stays charged. Spec line 76 could say the first half explicitly. Observation.
- **Graceful close versus device loss.** Spec line 72 and appendix `CloseResult` agree. The legacy adapter clears pending and aging silently on rebuild (`game-audio.ts` lines 101 to 108); generation ended with application unknown replaces that for program callers while legacy aging stays for unmigrated callers (line 80).
- **Reconciliation without a commit.** `planEdit` with an empty edit list and a diverged applied revision skips command classification and compiles the desired document against the running program, producing a prepare effect (`plan.ts` lines 75 and 82 to 93). `surface.apply` requires a non empty edit tuple (`composition-surface.ts` line 28), so the worker calls the planner directly, which is what line 20 says.
- **Pre limiter contribution and origin.** `MasterBus.renderBlock` sums then limits (`master-bus.ts` lines 202 to 218). `ProgramRuntime` starts its clock at zero with no start frame input (line 52), so alignment to the host frame is a required constructor input. Consistent with line 22.
- **Deletion coherence.** `composition-runtime.ts` is exported from control index line 5 and consumed by `program-surface.test.mjs`; deletion with test migration is one unit (line 80). No approved specification requires shipping page byte identity; only the host spec mentions it, to drop it (line 82).
- **Proof rules.** Offline suspend and resume, then an advancing `AudioContext` with a 500 ms stall (line 86); test limits are not acceptance (lines 16 and 86); pooled admission deferred and no allocation free claim (lines 26 and 88). Consistent with adjudication and review.

## Fit probe

`cap-fit.mjs` compiled all 22 proof cases through the existing test helpers and validator, Node v25.9.0.

| Quantity | Observed maximum | Cap |
|---|---:|---:|
| Slots, parameters, connections | 7, 39, 10 | 16, 256, 128 |
| Charged program text | 17,916 | 32,768 |
| Install envelope text with identity, revisions, trigger and storage descriptors | 19,200 | 32,768 |
| Transferred backing | 32,768 | 65,536 |
| Envelope plus backing | 51,476 | 98,304 |
| 32 ramped commands as one ordinary envelope | 9,567 | 65,536 |

All 22 fit, matching the appendix's maxima. Two Sounds with active plus candidate of the largest fixture and 32 resident Voices fit `PROGRAM_RESOURCE_LIMITS` in every unit, with `programs` and `voices` at exact fit.

## Open

Correction 2's reserve size, the activation entry class and the retained allowance are implementation decisions the spec can settle in one row and two sentences. Real browser transport, timing and allocation remain unmeasured, as every input states.

## Limitations

Read-only. Node v25.9.0 here versus v24.20.0 for the authors. The probe charges text with the existing three bytes per code unit rule and estimates the envelope shape from the appendix; the build must assert the real one.
