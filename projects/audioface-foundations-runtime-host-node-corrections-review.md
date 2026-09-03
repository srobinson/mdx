---
title: Audioface foundation program host Node corrections review
type: projects
tags: [audioface, foundations, host, runtime, lifecycle, review, verification]
summary: Independent verification of the F1 through F4 corrections at 2c6b4b6 with one medium residual on triggers under command lag, two low cleanup residuals, and browser parity.
status: draft
created: 2026-09-05
updated: 2026-09-05
project: audioface-next
related: [audioface-foundation-program-host-spec, audioface-foundations-runtime-host-node-corrections, audioface-foundations-runtime-host-node-review, audioface-foundations-runtime-host-node-build]
confidence: high
---

# Program host Node corrections review

Target `2c6b4b6f7e28ea4ccda3dc1a0f8ac51e72a72f4f` on the frozen browser checkout, parent `a06c93a2319b34fa00f07de98812ec3d8d67c851` (14 files, +818/-239). Active contract `e207f849a1de661c791a138f4fffc7042b158f6cb7a6390d772ae9c0a9ad16f7` verified by hash before and after. The checkout was at exact HEAD with zero changes before and after this review. No source, specification or prior report was edited. No additional agents. Scope was the four corrections and touched hygiene, not a fresh parent review.

Verdict: **findings**. All four corrections do what the digest claims and the original reproductions now pass. One residual of the F1 class remains: a trigger sent while a command is unacknowledged is refused as stale. Two low residuals remain in the cleanup path. Evidence lives in `/Users/alphab/.mdx/TMP/pstack/audioface-foundations/runtime-host-node-corrections-review/` (`environment-before.txt`, `environment-after.txt`, `original-repros.log`, `repro-*.mjs` with logs, `focused.log`, `bounds-rerun.log`, `headless/`, `headed/`, `browser-summary.json`).

## Findings

### R1. Medium. A trigger issued while a live command is unacknowledged is refused as stale

- Location: `packages/control/src/program-preparer.ts:183` (`revision: applied.revision` in the trigger message), `packages/control/src/program-host.ts:414` (`sound.revision !== message.revision` refuses the trigger at execution).
- Observation: `repro-f1-ordered.mjs` case B. Open, trigger, advance a window, then a live edit followed immediately by a trigger. The command applies at frame 129 and advances the host revision to 1. The trigger, authored against applied revision 0, is refused with "Audioface stale trigger revision or program". The same trigger after acknowledgement applies.
- Impact: under real port latency, playing a note while live editing fails whenever a command is in flight, which the F1 correction now makes the ordinary state. The contract's "acknowledgement lag alone is not a reason to prepare a cold replacement" extends in spirit to triggers.
- Basis: changed behavior. F1 gave commands an explicit planning base but left the trigger on the applied base.
- Caveat: the two lines predate the delta (identical at a06c93a), so this is pre-existing exposure widened by F1, not a regression introduced by the fix.
- Minimum correction: author the trigger against the command-planning revision. Queue order guarantees every earlier command has applied or been refused before the trigger executes, and a refused predecessor resets the base so the host's stale check remains honest. Alternatively, the host can accept a trigger whose program key matches and whose revision is at most the current one. This is a lead decision at contract level.

### R2. Low. A duplicated rejected cleanup message can be admitted later without any sender record

- Location: `packages/control/src/program-host.ts:330-383` (unadmitted rejection retains no host history), `packages/control/src/program-preparer.ts:376` (sender withdraws its provisional record).
- Observation: `repro-f2-cleanup.mjs` case S4. A close is rejected by the reserved queue capacity and both realms drop it. When the identical message is delivered again after the capacity frees, the host admits it as pending, closes and reclaims the Sound. The sender still holds the Sound as open, accepts further edits, and its retry close is refused with "cleanup identity already reserved or incompatible".
- Impact: sender and host disagree about the Sound for the rest of the generation.
- Basis: contract requirement that duplicate and stale messages must not activate twice.
- Caveat: requires at-least-once delivery of the same message. A transferred `MessagePort` delivers each message once, and the contract explicitly retains no history for unadmitted requests, so this is an ordering assumption to state for the worker milestone rather than a defect in this delta.

### R3. Low. A local post failure after provisional cleanup admission consumes the record

- Location: `packages/control/src/program-preparer.ts:310` (`submit` settles a refused outcome when `post` throws).
- Observation: `repro-f2-cleanup.mjs` case S6. With a post that throws for the close, the close settles refused, the record is retained (records 1 to 2), and a second close throws "cleanup identity already reserved".
- Impact: the Sound cannot be closed gracefully for the generation.
- Caveat: after envelope validation a real port does not throw for plain data, so this is reachable only through a harness post. Correction is one line: withdraw a provisional cleanup in the catch instead of settling it.

## Hygiene observations

- `hasCommands` (`program-preparer.ts:454`) scans every submission on each apply and settle. Bounded by 256 tickets, so acceptable for the prototype.
- `Sound.applied` and `Sound.planningRevision` are two nullable fields with a coupled invariant; one object would make the state unrepresentable when inconsistent.
- `readProgramMessage` returns an unnamed shape consumed through `ReturnType<typeof readProgramMessage>` at `program-host.ts:97`.
- `Credit.metadataBytes` is a mutable slot written after grant (`program-host.ts:201`), the only mutable field on the record.
- The F3 regression test patches TypeScript-private members (`validateResidents`, `installed`) from JavaScript. My instrumentation instead proxies the installed state and admission order and observes zero property reads.
- Sizes from the author's probe rerun: largest touched file 569 lines, largest touched function 97 lines (the 104-line function is in an untouched kernel file).

## Verified

- F1: two and five rapid edits with 200-frame ramps, delivered unacknowledged, apply as ordered commands at the requested frame with one compilation, one preparation, no install and no cancel; 3,000 captured samples over ragged spans equal acknowledged execution. Planning base reads 2 or 5 while applied reads 0 before acknowledgement; both agree afterwards. A command in flight followed by a frozen edit and a live edit coalesces the cold snapshot, cancels the superseded candidate and installs the whole desired state at revision 3. Four applied replies delivered in reverse settle every ticket applied at revision 4 with no rollback. A three-command chain refused at the host (lookahead, then two stale bases) with a fourth edit authored before the refusals arrive reconciles into one install carrying every value at revision 4. The original coalescing reproduction now applies both edits at frame 0.
- F2: lookahead rejection of release and close resolves the caller refused, leaves sender records, host records and queue unchanged, and a new identity later applies and reclaims to zero residency. Reserved-capacity rejection rolls back queue and tickets together. Edits and triggers remain accepted after rejection. Three hundred rejected release plus close pairs leave history unchanged. The Sound reports closing only after the host accepts. A stale unadmitted reply after confirmation is ignored. The original stranding reproduction now prints `undefined` for withdrawn identities and my promise assertions prove the refused outcomes.
- F3: with 32 resident Voices, eight empty batches perform zero property reads on the installed state and admission order and leave the snapshot unchanged, against 273 reads for a one-command batch. At the host, eight empty batches apply at the actual frame advancing the revision to 8 with zero runtime commands, the ninth is refused by the batch cap, and a real command three blocks later applies against revision 8.
- F4: ten unrelated malformed kinds naming a credited open (bad reserve, cancel, command, trigger, release, close, install without storage, install with storage, wrong generation, uncredited identity) leave the credit intact and the legitimate packet installs. A malformed true transfer reclaims once, a repeat and an aliased variant produce nothing, and the genuine packet replays refused. A malformed open naming a credited install is ignored. Resident-phase duplicates preserve residency. A malformed install matching identity and phase reclaims once.
- Hygiene: exactly one envelope stringification per received reserve, open, trigger, command, release and close. Seventeen slots and 280 parameters are refused by the shared bounds before any deep validation; sixteen slots with bogus kernels pass the shallow host check and fail the engine validator. The shared formatter truncates at 256 characters. A release queued before its still-pending trigger is bumped and applies after it. The legacy cancel path reports program entries as unknown.
- Gates: focused suites 75 tests pass (exit 0). The author's bounds and sizing probe passes against the browser checkout. The full check is taken from the lead log at this commit (442 tests, zero failures or skips).

## Browser regression proof

Fresh private headless and headed sessions each built the web app and ran all 22 program cases at both rates with zero node and oracle mismatches, plus the legacy null fixture with five events passing. Sample hashes equal the parent run at a06c93a and the author's final runs. Artifact hashes equal the author's (`814fe871…`, `b63b3ca6…`, `742d6401…`) and differ from the parent, as expected for changed shared host code. Source clean before and after each session. Chrome 152, agent-browser 0.36.0, Node v25.9.0.

## Limitations

No real worker, transferred port or advancing AudioContext was exercised; this is regression parity on the existing direct worklet path, not integration proof. Timings in the F3 log are informational only. The full `pnpm run check` was not rerun here.
