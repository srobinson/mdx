---
title: Audioface Node host residual corrections review
type: projects
tags: [audioface, foundations, host, lifecycle, transport, review, verification]
summary: Independent verification of the R1 and R3 residual corrections at e6ddf9d, with R2 confirmed as a declared transport limitation.
status: draft
created: 2026-09-05
updated: 2026-09-05
project: audioface-next
related: [audioface-foundation-program-host-spec, audioface-foundations-runtime-host-node-residuals, audioface-foundations-runtime-host-node-corrections-review, audioface-foundations-runtime-host-node-corrections]
confidence: high
---

# Node host residual corrections review

Target `e6ddf9da996e0bf87b0fa3eb0be5f1c7f69f539f`, parent `2c6b4b6f7e28ea4ccda3dc1a0f8ac51e72a72f4f`, frozen browser checkout `/Users/alphab/.mdx/TMP/pstack/audioface-foundations/worktrees/browser`, branch `probe/foundation-browser`. The checkout was at the exact target with zero changes before and after the review. Active spec SHA256 `b358d848680b1ae0b3c35ac28978e2508570c23f008530ea12a399a61835925c` verified. Main README hash `f34eb76a9bd6818ccb3ae8243755c6e4598d93efccfe182d5d37bf550f254525` unchanged throughout; it remains the authorized root edit. The main checkout also holds an untracked `output/imagegen/` directory, outside target source and not touched.

Verdict: clean. R1 and R3 are corrected as specified. R2 reproduces exactly as the lead declared it, outside the supported transport contract. No source or spec edits, commits, remote actions, dependency changes or additional agents.

## Delta

Four files, 430 insertions and 27 deletions. `packages/contract/src/program-host.ts` states the transport precondition and adds `ProgramPostNotDeliveredError`. `packages/control/src/program-preparer.ts` extracts `commandBase`, shares it between the planner callback and `trigger`, and routes every non-transfer post through `postEnvelope`. `test/foundations/program-host-support.mjs` accepts an injected post wrapper. `test/foundations/program-residuals.test.mjs` adds 26 tests.

## R1. Verified

`trigger` at `program-preparer.ts:177` now takes its revision from `commandBase` at `:476`, the same lookup the composition planner uses. The applied revision still advances only on observed applied outcomes in `settle`. The host's revision and key checks are untouched in this delta.

Independent probe `repro-r1-trigger.mjs`, seven cases, exit 0:

- Two commands in flight, first refused by lookahead, second refused by base. The dependent trigger authored at revision 2 is honestly refused as stale, no voice is created, planning resets to 0, and a retry authored at 0 applies. A fresh edit afterwards becomes a cold install held as a candidate until the live voice tail ends, then applies at revision 3.
- First refusal received while the second command is still in flight: a trigger authored between them carries revision 0 and applies once the second command is refused.
- Trigger under lag, then a pending install held by a later trigger's voice. Both triggers carry revision 1 and the installed key; both apply against the installed program; the install applies after the tails, planning and applied settle at 2, and the next trigger carries 2.
- Pending install with no live voice: a trigger scheduled past the install frame is refused stale, zero samples, and a retry at revision 1 applies.
- Three unacknowledged 300 frame ramps on two keys with a custom trigger payload: 9,000 samples over ragged spans equal the acknowledged control, nonzero.
- Reordered replies with a refused predecessor: the trigger's refusal arriving first leaves planning at 1; the command refusal then resets it to 0.
- A trigger's applied reply never advances applied revision (0 while planning is 2); a following trigger still authors against planning 2 and applies after the commands settle. Generation loss with a lagged trigger settles unknown once.

The original reviewer scenario now applies at frame 129 against revision 1 (`originals.log`).

## R3. Verified

`postEnvelope` at `program-preparer.ts:314` treats `ProgramPostNotDeliveredError` as an unadmitted refused reply fed through `receive`, so `ProgramTickets.withdraw` remains the only deletion path for provisional cleanup. Every other throw calls `endGeneration` at `:326`. The grant transfer post at `:363` keeps its conservative quarantine and rethrow.

Independent probe `repro-r3-post.mjs`, nine cases, exit 0:

- Typed failure on an explicit cancel withdraws it, sender and host ticket counters unchanged, and a new cancel identity cancels the install.
- Typed failure on the open reserve: retained ordinary refusal, no sender transfer, generation alive, reopen succeeds.
- Typed failure on an install reserve: ordinary refusal, only the resident open transfer remains, planning reset to 0, the next edit installs and applies at revision 2.
- Typed failure on a trigger: retained refusal, planning untouched at 1, next trigger applies.
- Typed error on the grant transfer post: generation ended, application unknown, error propagated out of `receive`, transfer quarantined, backing reclaimed to zero only at teardown.
- Generic throws on trigger and cancel, before and after enqueue: unknown once each, open outcome intact, resident and in-flight transfers retained until teardown. When the cancel was delivered before the throw, the host's reclaim reply still clears that install transfer because `receive` honours reclamation after generation loss.
- Nested paths: the automatic cancel posted inside `apply` fails typed and is withdrawn; the install then applies; a live command failing typed from a later edit retains its refusal with desired 3, applied 2, planning 2; the next edit installs and matches the host.
- A forged unadmitted refusal for an in-flight provisional cleanup withdraws it while the host closes the Sound. This is the R2 family and relies on the trusted host never sending such a reply.
- A plain `Error` with the same message text is not treated as proven non-delivery.

The original generic `port closed` scenario now yields application unknown (`originals.log`, S6).

## R2. Declared transport limitation

Original `repro-f2-cleanup.mjs` S4 still shows the replayed rejected close admitted by the host while the sender has withdrawn it. The spec, the `ProgramPost` comment at `program-host.ts:103` and the author report all state ordered single delivery, no redelivery after unadmitted rejection and new identity retry. Admitted same-identity replay is covered by the author's retry tests and by S7. Adapter conformity belongs to the worker milestone.

## Hygiene observations

None blocks. Low, for the lead's judgement:

- The `ProgramPost` comment says the typed error means no delivery or transfer occurred, yet the transfer post at `program-preparer.ts:363` quarantines it regardless and rethrows out of `receive`, while `postEnvelope` swallows. Conservative and safe; the comment could state that transfer posts are always treated as uncertain.
- `ProgramPostNotDeliveredError` sets no `name`, so instances report `Error`. Classification is by `instanceof`, so no functional effect.
- `commandBase` returns an unnamed inferred shape; acceptable at three call sites.
- A coalesced replan from `reconcile` is always an install because `plan.ts:75` requires the planning revision to equal the document revision for commands. Pre-existing planner rule, outside this delta.

Sizes: largest touched file 587 lines, `receive` 97 lines, no function over 150. Typecheck passes independently. Generated `packages/*/types/` and `apps/web/dist/` are ignored, so the tree stayed clean after build and typecheck.

## Gates

| Gate | Result |
|---|---|
| Original reviewer repros f1-ordered, f2-cleanup, refused-close-strands, lifecycle-queue | exit 0 |
| Focused six test files | 101 pass, 0 fail, 0 skipped |
| Residual file alone | 26 pass |
| Bounds and sizing probe at exact SHA | pass |
| `pnpm run typecheck` | exit 0 |
| Lead full gate log | 468 pass, lint, format, structure pass |

## Browser basis

`pnpm --filter @audioface/app-web build` at e6ddf9d produced `index.html` `814fe871…`, `null-test.html` `b63b3ca6…`, `program-test.html` `742d6401…`, byte-identical to the parent build and to the author's manifest. The prior real browser evidence at 2c6b4b6 (headless and headed, 22 program cases with zero mismatches and five legacy null events) therefore holds by hash equivalence and was not rerun. Worker and browser host integration remains unproven.

## Evidence

`/Users/alphab/.mdx/TMP/pstack/audioface-foundations/runtime-host-node-residuals-review/`: environment before and after, `support.mjs`, four original repros with `originals.log`, `focused.log`, `bounds.json`, `typecheck.log`, `build.log`, `artifact-hashes.txt`, `hygiene-static.txt`, `repro-r1-trigger.mjs` and `repro-r3-post.mjs` with logs.
