---
title: Audioface foundation program host Node milestone review
type: projects
tags: [audioface, foundations, host, runtime, lifecycle, review, verification]
summary: Independent review of the Node host milestone at a06c93a with two medium and two low findings, hygiene notes, reproduced bounds and browser parity.
status: draft
created: 2026-09-05
updated: 2026-09-05
project: audioface-next
related: [audioface-foundation-program-host-spec, audioface-foundations-runtime-host-node-build, audioface-foundations-runtime-host-consistency-review, audioface-foundations-runtime-host-design-review]
confidence: high
---

# Program host Node milestone review

Target `a06c93a2319b34fa00f07de98812ec3d8d67c851` on the frozen browser checkout, delta from `30b15bcf8ff3f42b5afd25c296cc0e8afd633e21` (26 files, +2709/-351). Contract `68881c707e78dd6a58a6c3b7926dca81450763d64ef1b8d2f39077358dc94014`, verified by hash, including the document-only admission steering. The checkout was at exact HEAD with zero changes before and after this review. No source, specification or prior report was edited. No additional agents.

Verdict: **findings**. The milestone is coherent and the contract's ownership, bounds and lifecycle rules are implemented and proven as claimed. Two behaviors are medium severity because they make the protocol unusable for ordinary use under latency or after one transient refusal. Neither breaks a sample, a refund or a bound. Evidence lives in `/Users/alphab/.mdx/TMP/pstack/audioface-foundations/runtime-host-node-review/` (logs, reproducers, browser results, `browser-summary.json`, `environment-before.txt`, `environment-after.txt`).

## Findings

### F1. Medium. A live edit issued before the previous one is acknowledged becomes a cold reinstall

- Location: `packages/control/src/program-preparer.ts:158` (supersession cancels the in-flight ticket), `:389` (divergence replanned with empty edits), `packages/control/src/composition-surface.ts:79` (planner classifies against the applied revision), `packages/patch/src/composition/plan.ts:75` (any applied lag skips the command path).
- Observation: `repro-live-edit-coalescing.mjs`. With a flush between two live delay edits both apply as commands (revision 2, two runtime commands). Without a flush the first is cancelled, the second is authored as `prepare`, stays pending while the Voice and tail play, and applies at frame 725,248. No live value reaches the running Sound in between.
- Impact: with a real worker and port every edit has acknowledgement latency, so a stream of live edits during playback never lands until every Voice and the tail end, and each new edit cancels the pending install again. The pre-milestone in-process surface never lagged, so this is new exposure of an existing planner rule.
- Basis: contract text "Replan desired/applied divergence through the existing planner" is followed literally; the planner rule is unchanged. The scout report flagged the planner's divergence classification as a host risk.
- Minimum correction: classify an edit against the last authored program when the pending effect is a command (commands compose in queue order), or stop cancelling an in-flight command batch on supersession and let the queue order them. This is a lead decision at contract level, not a silent fix.

### F2. Medium. A refused close or release permanently strands its owner in both realms

- Location: `packages/control/src/program-tickets.ts:41-43` (cleanup record consumed at admission), `packages/control/src/program-preparer.ts:238` (`closing` set before any outcome), `packages/control/src/program-host.ts:415-418` (refusal path after admission).
- Observation: `repro-refused-close-strands.mjs`. A close beyond lookahead is refused. Afterwards the preparer throws "Sound is unavailable" for close and trigger and "Sound is closing" for edits. A direct host close message is refused unadmitted because the cleanup identity is already reserved. The host keeps the Sound resident with its credit charged until generation end. A refused release likewise consumes the Voice's only release record.
- Impact: one transient refusal (lookahead, envelope bytes, or the lifecycle reserve at that instant) makes graceful close impossible for the rest of the generation, which contradicts the contract's requirement that graceful cleanup remain possible.
- Minimum correction: return the cleanup record when its request settles as refused before queueing, and set `closing` only once the close is pending or applied. The 768 record bound is unaffected because a refused request still holds exactly one result record.

### F3. Low. An empty command batch hides a full bind pass

- Location: `packages/control/src/program-host.ts:334` (work charged as `commands.length`), `packages/engine/src/program-runtime.ts:264-270` and `:283-296` (every slot and every resident kernel bound regardless of batch length).
- Observation: `repro-empty-batch-work.mjs`. Eight empty batches are admitted at one frame at zero work units; the ninth is refused by the batch cap. With 32 resident Voices an empty batch costs 125.7 µs against 124.6 µs for a one-command batch. Empty batches are routine: a no-op replan sends `command []` to advance the applied revision.
- Impact: up to eight uncharged bind passes per window, about 1 ms of a 2.67 ms window at 48 kHz on this machine. Bounded by the batch cap, so no unbounded work.
- Minimum correction: skip `runtime.command` for an empty batch and only advance the revision, or charge at least one unit.

### F4. Low. A malformed message naming a credited identity cancels that operation

- Location: `packages/control/src/program-host.ts:105-119`.
- Observation: `repro-malformed-known-id.mjs`. A malformed `reserve` or `cancel` carrying the identity of a granted open refunds its credit and refuses it; the genuine packet arriving later is replayed as refused and its transferred backing dropped. A well-formed `install` reusing a pending open identity does the same through the credit mismatch.
- Impact: needs a sender bug or corruption on a direct port. The refund happens once and the ledger returns to zero, so no credit is minted.
- Minimum correction: restrict the correlation path to raw messages whose kind is open or install and which carry storage.

## Hygiene observations

- `validateProgramPacket` (`program-envelope.ts:186-196`) copies the connection and parameter counting loop of `validateProgram` (`program-preparation.ts:87-96`) with tighter limits. The contract asks to extend the validator, not duplicate it. A shared count helper removes the copy.
- Every message is charged twice: the reader walks and stringifies it, then `operation` calls `programEnvelopeBytes` again (`program-host.ts:338`) and `installationEnvelopeDemand` walks the whole packet again (`program-envelope.ts:211`). This is rendering-thread work.
- Error truncation exists as `errorText` (`program-host.ts:548`) and three `String(error).slice(0, 256)` copies in `program-preparer.ts`, with different prefixes.
- `"schedule" in entry` narrowing appears six times in `bus-host.ts`; `schedule()` takes nine positional arguments; `ScheduledOperation.starts` and `releases` are `string | null` rather than `CommandId`; the three `applied` outcome variants are told apart by field presence rather than a discriminant.
- Window retention of spent work switches on when `batchesPerWindow` is defined (`command-queue.ts:220`), so legacy commands in a programs-enabled host gain retention they lack today. The shipping worklet passes no `programs`, so shipping behavior is unchanged.
- All changed files are at or under 550 lines and every function under 150 lines (author probe rerun, exit 0).

## Verified claims

- Ownership: `ProgramTrigger` and `ProgramDemand` have single declarations in contract; the engine re-export is gone; `composition-runtime.ts` is deleted with zero references in the tree; one planner, one queue and clock, one pre-limiter contribution in `MasterBus.renderBlock`, Sounds summed in open order.
- Document-only admission: admission precedes `surface.apply`; the raw surface is private; `document-committed` never advances applied state and a forged `applied` result cannot settle it; the 257th edit is refused with library identity and revision unchanged.
- Validation: bounded walk before stringify or hashing; wrong version, lowered unkeyed demand, missing, mismatched, aliased and detached backing, oversized metadata and wrong sample rate are refused with one reclaim and a zero ledger.
- Credits and quarantine: full vector credit before transfer; detachment verified by the sender; transit and residency remain charged; generation loss settles once as unknown and holds credit until confirmed disposal.
- Tickets: 256 ordinary, 768 records, one cancellation identity per known target, unknown targets unadmitted with no history, one thousand alternates leave history unchanged.
- Queue: activation, release and close occupy the reserved class; a cancel removes one entry and adds none; release and close are admitted while 128 ordinary entries are queued (`repro-lifecycle-queue.mjs`).
- Samples: two Sounds at origin 777 with ragged spans, a refused stale command and a refused second trigger in one window each equal their single-runtime control (`repro-isolation.mjs`).

## Browser regression proof

Fresh private headless and headed sessions each built the web app and ran all 22 program cases at 48 kHz and 44.1 kHz with zero node and oracle mismatches, plus the legacy null fixture with five events passing. Sample hashes equal the baseline run at 30b15bc. Artifact hashes changed to `c81ed95b…`, `9b14a5ad…` and `c6c932e1…`, matching the author's values. Source was clean before and after each session. Chrome 152, agent-browser 0.36.0, Node v25.9.0.

## Limitations

No real worker, transferred port or advancing AudioContext was exercised; candidate pacing is proven only under the Node fixture's explicit `pump` calls. Timings above are single-machine indications, not a budget. The lead's full `pnpm run check` at this commit is taken from the lead log; this review reran the focused 55 tests (exit 0) and the author's bounds probe (exit 0).
