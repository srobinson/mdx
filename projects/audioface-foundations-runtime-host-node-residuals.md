---
title: Audioface Node host residual corrections
type: projects
tags: [audioface, foundations, host, lifecycle, transport, verification]
summary: R1 trigger dependencies and R3 cleanup retries corrected, with R2 recorded as a bounded transport precondition.
status: draft
created: 2026-09-05
updated: 2026-09-05
project: audioface-next
related: [audioface-foundation-program-host-spec, audioface-foundations-runtime-host-node-corrections, audioface-foundations-runtime-host-node-corrections-review]
confidence: high
---

# Node host residual corrections

Implementation checkpoint `e6ddf9da996e0bf87b0fa3eb0be5f1c7f69f539f` is committed and clean in `/Users/alphab/.mdx/TMP/pstack/audioface-foundations/worktrees/integrated`, branch `probe/foundation-integrated`. Parent is `2c6b4b6f7e28ea4ccda3dc1a0f8ac51e72a72f4f`. Independent delta review is pending.

The active host specification has SHA256 `b358d848680b1ae0b3c35ac28978e2508570c23f008530ea12a399a61835925c`. The residual brief and binding decisions authorize R1 and R3 code corrections plus the explicit R2 transport precondition. The prior F1 through F4 implementation remains intact.

## R1 trigger dependency correction

`ProgramPreparer.trigger` now uses `commandBase`, shared with the composition planner callback. That helper returns the installed `ProgramSpec` and explicit command planning revision. The callback's former inline lookup was removed. There is no new revision tracker or scheduling classifier.

Submitting a trigger after live commands expects their projected predecessor revision while retaining the installed program identity. Only observed applied command outcomes advance `appliedRevision`. The receiver's revision and program key checks are unchanged.

The tests cover one and four unacknowledged commands with 257 frame ramps. Their subsequent trigger captures match acknowledged controls for 12,000 Float32 samples using ragged spans. Additional cases cover both equal frame insertion orders, earlier and later trigger frames, conflicting command frame order, refused predecessor reset, and reversed replies.

During opening, a trigger remains unavailable. During a pending installation, it targets the currently installed program. A trigger that executes before the installation applies uses that old program. A trigger that executes after the installation changed the program is refused. Explicit wrong revision and wrong key cases preserve resources, runtime state, and zero samples.

The original reviewer scenario now reports the second trigger applied at frame 129 against revision 1 while the command acknowledgement was still pending.

## R3 confirmed failure before delivery

`ProgramPostNotDeliveredError` is an explicit local adapter assertion that no delivery or transfer occurred. `ProgramPreparer.postEnvelope` handles that error through the existing unadmitted result path. `ProgramTickets.withdraw` remains the sole authority for deleting a provisional unsettled cleanup and releasing its owner pointer.

Release and close tests inject this typed error before enqueue, then allow the same adapter to deliver successfully. Each failed promise resolves refused once. Sender history, receiver history, queue state, and residency remain unchanged. The sender retains no outcome record for the unadmitted cleanup. A subsequent edit succeeds, cleanup retries with a fresh identity, and reclamation reaches zero backing and transfers.

Closing still starts only after host acceptance. The provisional failure never sets closing, so withdrawal leaves the owner usable. No admitted or settled cleanup is withdrawn. Tests also replay admitted pending and terminal cleanup requests and inject a stale unadmitted reply after settlement. They preserve the one retained cleanup record and one caller settlement.

An ordinary edit has already committed its document before posting. Its proven pre-delivery failure therefore remains an admitted, retained refusal. The desired revision advances, the applied revision stays unchanged, and planning resets to the applied revision.

Every other post exception means uncertain delivery. The existing generation ending path resolves unresolved callers with `generation-ended`, application `unknown`, and retains transfer accounting until verified reclamation or disposal. Tests inject generic errors before and after enqueue for release, close, command, and reserve. No uncertain request becomes a retryable unadmitted refusal. An already applied open outcome remains applied.

The original reviewer's generic `Error("port closed")` now produces application unknown and prevents retry within that ended generation. It does not carry the new adapter assertion of proven non-delivery. The typed before-enqueue regressions demonstrate the R3 retry contract. The existing transfer-after-grant error path remains conservative and quarantines its receiver credit.

## R2 transport precondition and limitation

The `ProgramPost` interface and realm pair proof contract now state ordered single delivery within each generation. An envelope rejected before admission ends that attempt. The adapter must not automatically redeliver it. Retry uses a new identity. Same-identity replay remains supported after admission.

The original duplicate-delivery reproduction still demonstrates the unsupported case. Once queue capacity frees, replaying a previously unadmitted raw close envelope can admit it at the receiver while the sender has withdrawn it. The receiver then closes the Sound and a sender retry is refused. This work does not claim arbitrary rejected-envelope replay resilience and adds no rejection tombstones.

The real worker adapter must prove ordered single delivery, absence of automatic resend after unadmitted rejection, accurate classification of pre-delivery failure, and application-unknown disposition for uncertain delivery. That proof belongs to the next worker and browser milestone.

## Scope and hygiene

Four repository files changed, with 430 inserted and 27 deleted lines. Production changes are confined to the transport contract and preparer. The test helper gains an injected post wrapper around the existing cloned transport. New cleanup cases share `cleanupFor`; parameter edits reuse `applyParameter`. The old inline planner lookup and direct submit post calls were replaced.

| File | Lines before | Lines after |
|---|---:|---:|
| `packages/contract/src/program-host.ts` | 104 | 111 |
| `packages/control/src/program-preparer.ts` | 564 | 587 |
| `test/foundations/program-host-support.mjs` | 112 | 115 |
| `test/foundations/program-residuals.test.mjs` | New | 370 |

The full Node milestone sizing probe reports a maximum file size of 587 lines and maximum function size of 104 lines. Both are within the 700 and 150 line limits. No broad hygiene refactor was undertaken.

The main README is untouched, with SHA256 `f34eb76a9bd6818ccb3ae8243755c6e4598d93efccfe182d5d37bf550f254525` verified during final checks. No other checkout, specification, or prior report was edited. No additional agents, remote actions, worker implementation, or browser host migration occurred.

## Verification

Evidence is under `/Users/alphab/.mdx/TMP/pstack/audioface-foundations/runtime-host-node-residuals/`.

The first four regressions failed before changing `ProgramPreparer`: both trigger cases returned refused and both cleanup cases retained a terminal record. At that point only the typed error declaration and test scaffolding had been added to the parent source. `regressions-before.log` preserves all four failures. `regressions-first.log` records all four passing after the correction.

The expanded test run first exposed two fixture mistakes. Retry tests reused a consumed voice construction window at its boundary, and a queue assertion read `.length` instead of `.entries`. Advancing into the next window and using the actual snapshot field corrected those tests. Receiver capacity rules were preserved. A helper initially named `postMessage` collided with a browser target-origin lint rule and was renamed `postEnvelope`. The project uses `oxfmt`; the unavailable Prettier command made no edits.

Final checkpoint commands are recorded with observed exit zero in `verification-final.json`:

- `pnpm run check`: 468 tests pass, typecheck, lint, formatting, and structure verification pass.
- Six focused foundation test files: 101 tests pass, including all 26 residual and all 20 original correction tests.
- Original reviewer ordered-command and cleanup scripts: exit zero. R1 improvement, R2 unsupported replay, and R3 generic-error quarantine are visible in `repros-final.log`.
- Existing exact-SHA bounds and sizing probe: all prototype caps preserved, including 16 slots, 256 parameters, 128 connections, 32 resident Voices, four program credits, and 32 commands per batch. Exact-fit and excess cases pass. Disposal reclaims backing to zero.
- `node scripts/verify-program-worklet.mjs headless OUTPUT` and the headed equivalent: each performs an actual web build, then passes 22 program comparisons and five legacy null events in a fresh private browser session. Both sessions close.

Both browser runs use Node v24.20.0, agent-browser 0.36.0, and Chrome 152.0.0.0 on macOS arm64. Every captured sample hash matches the parent checkpoint, Node execution, and the independent oracle. All three built page hashes match the parent and each other across browser modes:

| Artifact | SHA256 |
|---|---|
| `index.html` | `814fe8715e780b532449c4c5f8bd5e8b6f862ff336f6631435e25c7d07b5cbdd` |
| `null-test.html` | `b63b3ca60ab9daa2cc441c1afa4b771256307ff94930bcb1a461ea54387c4b82` |
| `program-test.html` | `742d6401bc1143f95b4755606e06b0836eef119314588b919c57079b84ca5098` |

`verify-final.mjs` reruns the checks, asserts exact parent and HEAD, checks clean source around each command, verifies the spec and main README hashes, and compares browser results with the prior checkpoint. It saves command exits and evidence hashes in `verification-final.json`.

Browser evidence exercises the existing direct ProgramRuntime proof. Actual worker transport, new host browser execution, and the advancing AudioContext during a main thread stall remain pending. Voice pooling, active transitions, spatial comparisons, and deadline campaigns remain outside this unit. No performance claim is made.

The Markdown index refresh returned `Path outside root: /Users/alphab/.mdx/projects`. The report and digest are saved and readable. No index configuration was changed.
