---
title: Audioface prepared Voice contract consistency review
type: projects
tags: [audioface, foundations, voice, contract, review, host, probes]
summary: Independent consistency review of the prepared Voice contract draft and host/probes amendments at 3221511, with mechanical materialization of both candidate specifications and two new source probes.
status: draft
created: 2026-09-06
updated: 2026-09-06
project: audioface-next
related: [audioface-foundations-prepared-voice-design-review, audioface-foundations-prepared-voice-design-clarification, audioface-foundation-program-host-spec, audioface-foundation-runtime-probes-spec]
confidence: high
---

# Prepared Voice contract consistency review

Verdict: **issue**. Three blocking findings and five bounded ones. The demand, accounting, history, whole bank, refusal and reset content of the draft is faithful to the accepted decisions and to source. The amendment keying, one reservation-time check, and one activation-time capture are not implementable as written.

## Inputs

Source read only at `3221511a59170b3fafaaa6924cf1a25f98a26b37`, tree clean before and after every probe. Draft hashes match the brief: spec `80559a2a…`, host amendment `86254997…`, probes amendment `8545e9bf…`. Current host spec `3f32506e…`, probes spec `6615929b…`, document spec `c1927508…` unchanged. No source, authoritative spec or author draft was edited.

## Verified consistent

| Draft claim | Authority | Evidence |
| --- | --- | --- |
| `installationDemand(program, voiceCapacity)` adds `voiceCapacity * programInstanceDemand(program, "voice")`; Voice instance demand carries `voices: 1` | `program-preparation.ts:59`, `:233` | demand fit probe: four 8-slot credits exhaust exactly `programs` and `voices` |
| Work charged once, never refunded; residency refunded once at disposal | `resource-ledger.ts:71`, `:73` | construction work probe |
| Cleanup is zero ordinary admission; ordinary tickets never withdrawn; no sender refund on receiver refusal | `program-tickets.ts:34` to `:58`, `:79`; `program-preparer.ts:404` to `:414` | history probe: 2/6, 100/300 vs 16/48, 202/606 vs 34/102, 54 then 55th refused |
| One FIFO candidate per window | `program-host.ts:237` to `:243` | unchanged |
| Readiness refusal before `admit` yields `admitted: false` with no ticket or capacity mutation | `program-host.ts:159` to `:170`, `:352` | existing unadmitted path |
| Echo and delay backing Sound only | `program-preparation.ts:153` | validator rejects Voice-region echo |
| Seeds independent of slot index | `program-values.ts:102` | seed label and modulation id only |
| Reset enumeration complete | `source-generator.ts:118`; `layer-filter.ts:45` to `:50`; `program-kernels.ts:179`, `:198`; `program-values.ts:12` to `:15`; `program-graph.ts:17` | every mutable field named by the draft exists; envelope is pure |
| Live Voice keys limited to unmodulated `FLT-10`; frozen and modulated resolution frame independent | design review activation probe | unchanged |
| Burst and history proof numbers | history probe | match the draft, both amendments and the disposition |

Word counts and writing: spec draft 1,198 words, no em dashes in any draft. Frontmatter carries every required schema field.

## Findings

### F1. Amendment keys are whole sections; the passages are not. Blocking.

Location: host amendment lines 18, 24, 30, 34; probes amendment lines 17, 23, 27, 31. Each key is `Replacement: ## <heading>` and line 16 says the passages "avoid restating unchanged policy".

Observation: the only mechanical reading replaces the entire keyed section. Materialized literally, the host candidate falls from 2,264 to 854 words and the probes candidate from 2,064 to 960. Removed unrelated guarantees, by current line: host spec bounds table `:32` to `:56`, cap policy `:58`, batch and work rules `:60`, 768 record rules `:62`, host edit admission `:64`, document-only edits `:66`, worker ownership and planner `:20`, SeedMap `:22`, bus composition `:24`, full validation, key and demand `:26`, message-task budgeting `:28`, pending and terminal `:80`, close and generation loss `:82`, command planning revision and acknowledgement lag `:84`, trigger revision expectations `:86`, typed non-delivery and uncertain quarantine `:88`, atomic queue plus ticket commit `:90`, one candidate and supersession `:92`, credit before transfer and lost-generation quarantine `:94`, Node first and migrations `:98` to `:106`. Probes spec: descriptors, ledger, fixture fit, scheduler, cancellation, worker chunks and rendering rules `:42` to `:56`; the held fixture with frame stamps and ramp formulas, transfer curation and crossfade policies `:60` to `:73`; spatial gates, `1e-6` tolerance and deadline campaign `:77` to `:87`; reuse table, three deliverables and gates `:91` to `:110`. Full removed text is in `host-loss.txt` and `probes-loss.txt`.

Under the other reading, insertion into the section, the following conflicting clauses survive: host `:45` "Voice constructions per 128-frame window, global | 1", `:60` "Candidate preparation and Voice construction allowances remain consumed", `:106` "Pooled Voice admission ... remain later work"; probes `:44` "Voice demand multiplies by admitted multiplicity", `:42` "Provisional reservations cover candidate construction".

Impact: root cannot apply either reading without either erasing accepted policy or retaining the one-Voice-per-window quota the disposition deletes.

Required change: re-key every passage as an explicit edit against quoted anchors: replace the paragraph beginning "Audio message-task validation" (host `:28`), delete table row `:45`, replace the sentence "Candidate preparation and Voice construction allowances..." (`:60`), insert after `:86`, replace the sentence "Pooled Voice admission..." (`:106`), and likewise for probes `:42`, `:44`, `:54` and an insertion in §5 and §6. Alternatively supply the complete amended section text with unchanged paragraphs carried verbatim. Both drafts must keep the bounds table and the six removed host paragraphs.

### F2. Reservation-time revision check refuses legal triggers. Blocking.

Location: spec draft line 45, "Reservation in `ProgramHost.operation` performs program and revision checks". Host amendment line 26 does not repeat it.

Observation: today the check runs at the trigger's frame (`program-host.ts:420` to `:425`), after queued commands advanced `sound.revision`. A trigger issued after a live command carries the command planning revision (`program-preparer.ts:200`); the host spec `:84` to `:86` requires that. The new probe on the real two-realm path opens `pair-delay`, applies a live `DLY-10` command and triggers in the same window: at receipt the receiver Sound holds revision 0 while the trigger message carries revision 1 and the command is still queued; at the frame both apply and the Sound reaches revision 1.

Impact: a reservation-time revision check would refuse every trigger issued behind an in-flight command, contradicting the accepted acknowledgement-lag policy and existing tests such as `program-residuals.test.mjs:98` to `:100`.

Required change: reservation performs readiness, claim, resolution, seed derivation and binding only. The revision and program check stays at the ordered frame in the existing apply; a failed check settles refused through `finish`, which returns the slot. State that activation of a valid reservation is infallible and that a stale reservation is settled, not activated.

### F3. Filter base captured at activation breaks exact reuse. Blocking.

Location: spec draft line 47, "captures the filter base required by the current closure" listed as activation work; host amendment line 26 "activation only copies live cells"; disposition paragraph 2.

Observation: the closure computes cutoff as `schedule(elapsed) * read(frame) / base` (`program-kernels.ts:196` to `:201`), where `schedule` derives from the binding's `cyclesPerFrame`. The ratio cancels only when `base` is the same value the binding was resolved from. New probe over the `PAIR` fixture with a 128-frame `FLT-10` ramp in flight, reservation at 320 or 301 or 350 and activation at 364 or 363:

| Base source | Maximum cutoff error over 256 frames |
| --- | ---: |
| reservation value the binding used | 6.7e-13 Hz, float64 rounding |
| live cell at the activation frame | 130.8 to 150.0 Hz, every frame |

Impact: the proof comparator "ramp reservations before activation" fails against a fresh trigger under the draft's wording, and the retained binding and its base would disagree.

Required change: the retained binding carries its own base, the `FLT-10` value resolved at reservation; activation copies the live cell through `copyFrom` and captures nothing. The design review's activation probe header said the opposite; its own 25-configuration sweep already showed zero sample differences with the reservation base.

### F4. The readiness refusal message is undefined. Issue.

Location: spec draft line 53 "the existing explicit readiness refusal"; host amendment line 32 "the current explicit refusal message"; proof asserts message text (spec draft line 65, probes amendment line 21).

Observation: the only current per-window Voice refusal text is the queue's "Audioface commands per render window capacity exceeded." (`command-queue.ts:164`), which the draft deletes with `voicesPerWindow`. The ledger's "Audioface program voices capacity exceeded." (`resource-ledger.ts:66`) is a frame-time refusal on an admitted ticket. Neither is a pre-admission readiness message.

Required change: name the exact text and the throwing module in the spec, and state that it is distinct from the ledger text and from "Audioface ticket history capacity exceeded."

### F5. API signatures and the caller and removal map are absent. Issue.

Location: spec draft lines 59 and 61; disposition requires a complete map before deletion; the draft brief asked for exact APIs.

Observation:

- `ProgramPreparer.open(target, trigger, frame, seedMap?)` (`program-preparer.ts:98`) gains `voiceCapacity` with no stated position or shape. The draft names `contract/program-host.ts` as validating the boundary; that module holds types and limits only. The boundary validator is `readProgramMessage` (`program-envelope.ts:114` to `:121`, `:131` to `:134`) and the shared demand site is `installationEnvelopeDemand` (`:207`).
- No signatures for reserve, activate, release or cancel on `ProgramRuntime` or the bank module; no disposition for the `ProgramReserve` callback and the per-trigger charge at `program-runtime.ts:158`, which must go to satisfy "no per activation charge"; tests asserting per-trigger refunds (`program-runtime.test.mjs:34` to `:70`) need a stated migration.
- Callers: 40 `open` sites across `program-seeds`, `program-protocol`, `program-residuals`, `program-surface`, `program-corrections`, `program-host` tests and `program-browser-node.mjs`, plus `adapters/web/src/worker.ts:105` and the client call builder in `adapters/web/src/program-client.ts`; `runtime.install` at `program-runtime.test.mjs:133, 139, 155, 158, 160, 422`; `voicesPerWindow` at `contract/program-host.ts:23`, `command-queue.ts:30`, `:162`, `bus-host.ts:89`, `program-protocol.test.mjs:392`; `preparationsPerWindow` at `contract/program-host.ts:22`; `ScheduledOperation.voice` and the queue's voice counter (`command-queue.ts:15`, `:49`, `:156`, `:254`) become dead with the quota.

Required change: add the signatures and this map to the removals section, and name one shared test constant for capacity beside `TRIGGER` in `test/foundations/program-support.mjs` so every caller gets it consistently.

### F6. Release and cancel token checks are implied, not stated. Minor.

Location: spec draft lines 37 to 41. The token is "valid only while reserved or active" and "Only `ProgramHost.finish` releases a queued reservation".

Required wording: the host's Voice map carries the token; release, duplicate release and cancel compare it and treat a mismatch as the existing idempotent no-op or stale outcome; an applied outcome moves the slot to active rather than releasing it.

### F7. Reserved slots and `idle`. Unanswered choice.

Location: spec draft lines 53 and 55. `idle` gates cold activation and close disposal (`program-host.ts:273`, `:296`, `:310`).

Observation: the draft does not say whether a reserved, not yet active, slot keeps the old runtime non-idle. Today an install activating first makes the later trigger stale at its frame. Holding installs for a reservation up to the 60 second lookahead is the alternative. Root should choose; the default consistent with F2 is that reservations do not block, and are settled stale by the frame check.

### F8. Metadata and versioning. Minor, for root's apply.

`source_sha` and `current_spec_sha256` are outside the schema's field list. The host candidate keeps `updated: 2026-09-05`, the `30b15bc…` baseline sentence at `:16`, and `related` without the new spec slug. Substantive revision requires a `_versions/` copy per the schema.

## Materialization

`materialize.mjs` applied each keyed passage as a whole-section replacement. Every key matched exactly one heading. Candidates, evidence only until F1 is resolved:

| File | SHA256 | Words |
| --- | --- | ---: |
| `prepared-voice-host.candidate.md` | `0d6abfb5350347322db2876a7eb0dbdb151a139a2e1de1d6206fa3696be01ab6` | 854 |
| `prepared-voice-probes.candidate.md` | `a5d92bed9845dfa7c47aae2c9d1e7430bf99235fb1439c2fa5428bc104bb032b` | 960 |

## Evidence

`prepared-voice-contract-review/`: `materialize.mjs`, `materialize-host.log`, `materialize-probes.log`, `host-loss.txt`, `probes-loss.txt`, `probe-revision-at-reservation.mjs` and `.log`, `probe-filter-base.mjs` and `.log`, `environment.txt`. Prior design review and clarification evidence unchanged.
