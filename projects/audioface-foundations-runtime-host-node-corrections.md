---
title: Audioface Node host corrections
type: projects
tags: [audioface, foundations, host, runtime, lifecycle, verification]
summary: F1 through F4 corrected at 2c6b4b6 with 20 regression tests, 442 full tests, bounded cleanup retries, and unchanged browser samples.
status: draft
created: 2026-09-05
updated: 2026-09-05
project: audioface-next
related: [audioface-foundation-program-host-spec, audioface-foundations-runtime-host-node-build, audioface-foundations-runtime-host-node-review]
confidence: high
---

# Node host corrections

Review checkpoint: `2c6b4b6f7e28ea4ccda3dc1a0f8ac51e72a72f4f`, local commit `fix: preserve ordered host edits and retryable cleanup`.

Parent and verified clean starting point: `a06c93a2319b34fa00f07de98812ec3d8d67c851`. Branch `probe/foundation-integrated`, checkout `/Users/alphab/.mdx/TMP/pstack/audioface-foundations/worktrees/integrated`. The final checkout is clean. Independent delta review remains pending.

The active host specification hashes to `e207f849a1de661c791a138f4fffc7042b158f6cb7a6390d772ae9c0a9ad16f7`, verified before edits and after verification. The lead's F1 and F2 decisions govern this correction. No specification, prior report, main README, or other checkout was changed. No additional agents or remote actions were used.

Evidence directory: `/Users/alphab/.mdx/TMP/pstack/audioface-foundations/runtime-host-node-corrections/`.

## F1: ordered live command tickets

Before the correction, the original reproduction cancelled the first live edit. The second became a cold preparation and applied at frame 725248. Four focused regressions were run before production edits; all four failed for the reported behavior.

`ProgramPreparer` now maintains `planningRevision` separately from genuinely applied state. Its public snapshot names the projected value `commandPlanningRevision`. The callback to `createCompositionSurface` explicitly supplies `planningRevision`, and the existing `planEdit` classifier continues to use the installed ProgramSpec and capacity. No second classifier or compiler was added.

Command submission advances the planning base without occupying the installation candidate slot or cancelling a predecessor. The host checks expected bases when the existing queue applies each command, preserving equal-frame order and refusing stale dependencies. The stale-base protocol test therefore observes pending followed by refusal at execution. Its sample comparison is unchanged.

Cold effects wait for outstanding command outcomes, then reconcile the entire latest desired snapshot through `planEdit`. Installs use the actual applied base. Refusal and install settlement reset the planning base. A later applied acknowledgement cannot leave that base behind the actual applied revision, and older applied replies cannot roll the revision back.

The original sequential and unacknowledged two-edit scenarios now both apply two commands at frame 0, with one initial installation and no cancellation or reinstall. New tests compare two and four edits with ramps against acknowledged execution. All 4096 captured samples match, including retained delay state across ragged spans. Additional tests cover reversed applied replies, reordered commands, real queue refusal, complete desired-state reconciliation, pending installation coalescing, and generation loss with unobserved application.

## F2: retryable unadmitted cleanup

The original reproduction consumed the single release and close records after lookahead refusal, disabled the Sound, and retained its resource charge. It now accepts fresh cleanup requests and drains to zero residency.

Local cleanup envelopes pass the existing reader before provisional admission. `ProgramTickets` remains the only cleanup authority. Each provisional cleanup record identifies its owner. `withdraw` removes only a provisional, pending record whose owner still points to that identity. Ordinary edits, confirmed admissions, and terminal records cannot be withdrawn.

Receiver queue insertion and provisional ticket admission commit together. Failure removes any queued entry and withdraws the provisional record, producing an unadmitted refusal. Accepted queue insertion confirms the ticket and produces pending. The sender marks closing only after an admitted host outcome. A legitimate unadmitted refusal resolves the caller, clears the owner pointer, and removes its provisional request bookkeeping. Accepted and settled history remains available for identity replay.

Tests run 800 rejected release attempts and 800 rejected close attempts without retained-history growth. Both operations recover from lookahead, receiver byte capacity, and reserved queue capacity rejection. Local nonfinite, negative-frame, and oversized envelopes consume no record. Valid retries use fresh identities, and playback or editing remains available after rejection. The tests also prove that stale unadmitted replies cannot withdraw a confirmed or settled cleanup, and an unadmitted cancellation can retry after its target reaches the host.

The unchanged 256 ordinary ticket and 768 record saturation tests pass. No second cleanup store or history recycling was introduced.

## F3: empty batches avoid parameter work

`ProgramRuntime.command` validates that the runtime exists, then returns immediately for an empty batch. It does not read the program, resolve parameter values, or bind resident kernels.

The regression instruments resident validation and program access with 32 resident Voices. Eight empty calls perform zero resident validation passes and zero program reads, while preserving the runtime snapshot. A host test applies eight ordered empty batches at the actual frame and advances revision to 8. The ninth is refused by the existing batch cap. Weighted parameter work remains zero.

The review timing reproduction was rerun for continuity. Its measurements are informational. Correctness rests on the structural work probes and the unchanged sample tests; no deadline or allocation guarantee is claimed.

## F4: credited transfer identity and phase

Malformed-message reclamation requires an open or install kind carrying storage, the current generation, a matching credited identity and operation kind, and the phase that is awaiting transfer. Unrelated malformed reserve or cancel traffic cannot refund that credit. A well-formed install that reuses a credited open identity is ignored without changing its ownership.

The legitimate transfer remains installable after unrelated malformed traffic. A malformed actual transfer is refused and reclaimed once. Duplicate malformed traffic during candidate or resident phases preserves the existing owner and charge. Repeated rejected transfers and stale-generation traffic cannot release residency or refund twice. The prior malformed version, demand, and backing tests remain green.

## Touched-code reuse and deletion

`validateProgramBounds` shares the existing validator's bounded parameter and connection counting with the host. Full `validateProgram` and storage validation remain authoritative before runtime binding. The cheap bounded envelope check still precedes hashing and deep validation.

`readProgramMessage` returns its measured envelope and metadata charges. The receiver carries those charges into queue admission and installation demand instead of walking and charging the same envelope again. A regression observes one envelope stringification for each received command and installation. Sender-created storage uses the already checked descriptor demand.

`programErrorText` replaces the four truncation implementations. `ProgramScheduled.kind` replaces repeated property-presence checks in the bus host. Scheduling takes the existing `ScheduledOperation` shape instead of nine positional values. `starts` and `releases` now use `CommandId`. The sample and correction tests share `applyParameter` through the existing realm-pair support.

Replaced counting, truncation, scheduling, and command-supersession paths were removed. The original queue, clock, ledger, pre-limiter summation, and sample oracles remain in use. The checkpoint changes 14 files, with 818 insertions and 239 deletions, including 416 lines of new regression tests.

## Verification at the final commit

All executable checks below ran against `2c6b4b6f7e28ea4ccda3dc1a0f8ac51e72a72f4f`.

| Check | Result | Evidence |
| --- | --- | --- |
| Full `pnpm run check` | 442 tests pass; typecheck, lint, formatting, and structure pass | `check-final.log` |
| Focused host, protocol, surface, runtime, and correction tests | 75 pass, including 20 correction tests | `focused-final.log` |
| Original six reviewer reproductions | Corrected F1 through F4, retained lifecycle and isolation behavior | `repros-final.log` |
| Bounds and sizing | 16 slots, 256 parameters, 128 connections fit; first excesses refused; 32 Voices and four program credits fit | `bounds-final.json` |
| Sizing across the Node milestone | Largest file 569 lines; largest function 104 lines | `bounds-final.json` |
| Headless real AudioWorklet proof | 22 cases, zero Node or oracle mismatches, five legacy events pass | `headless-final/result.json` |
| Headed real AudioWorklet proof | 22 cases, zero Node or oracle mismatches, five legacy events pass | `headed-final/result.json` |
| Artifact and source verification | Samples equal the parent in both modes; exact SHA and clean tree | `verification-final.json` |

Both browser runs execute `pnpm --filter @audioface/app-web build` before launching fresh private `agent-browser` sessions. They close those sessions after capture. Environment: Node v24.20.0, macOS arm64, agent-browser 0.36.0, Chrome 152.0.0.0.

The rebuilt artifact hashes are:

| Artifact | SHA256 |
| --- | --- |
| `index.html` | `814fe8715e780b532449c4c5f8bd5e8b6f862ff336f6631435e25c7d07b5cbdd` |
| `null-test.html` | `b63b3ca60ab9daa2cc441c1afa4b771256307ff94930bcb1a461ea54387c4b82` |
| `program-test.html` | `742d6401bc1143f95b4755606e06b0836eef119314588b919c57079b84ca5098` |

All three artifacts differ from the parent. Headed and headless artifact hashes agree, and all 22 sample hashes match their parent counterparts in both modes. `verification-final.json` records previous artifact hashes and hashes of the key logs and browser results.

The original reproduction runner imports the unchanged reviewer scripts while substituting only the integrated checkout loader. It records the current SHA and tree state. The legacy cleanup script queries retained history, so its unadmitted outcomes now print `undefined`. The new tests verify that the corresponding promises resolve refused and that the history was removed intentionally.

Rerunnable verification artifacts are `run-review-repros.mjs` and `verify-final.mjs` in the evidence directory. The unchanged `runtime-host-node-build/verify-node-bounds.mjs` supplies bounds and sizing checks. Browser commands are recorded in each run's `commands.json`.

## Remaining work

The requested Markdown index refresh failed with `Path outside root: /Users/alphab/.mdx/projects`. The report and digest exist and are readable. Index configuration was left unchanged.

This checkpoint awaits independent delta review. The new ProgramHost still uses cloned Node messages and explicit preparation pumping. Browser evidence exercises the existing direct ProgramRuntime worklet proof and the legacy fixture. Actual worker bootstrap, transferred ports, the new host browser path, and an advancing AudioContext during a main-thread stall remain later work. Voice pooling, active transitions, spatial comparisons, and deadline campaigns are also deferred.
