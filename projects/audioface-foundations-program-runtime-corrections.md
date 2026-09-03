---
title: Audioface foundation program runtime corrections
type: projects
tags: [audioface, foundations, runtime, verification]
summary: Local correction of live ramp inheritance and frozen edit classification at be881a2.
status: active
created: 2026-09-05
updated: 2026-09-05
project: audioface-next
---

# Program runtime corrections

Commit `be881a27706a2a624f1a3ae2a3e2e79974bf0a14` corrects both reviewed findings. Its parent is `795d803570e2a593745248ac82704e09ec45333c`. Branch `probe/foundation-integrated` is clean in `/Users/alphab/.mdx/TMP/pstack/audioface-foundations/worktrees/integrated`. Ten files changed, with 188 insertions and 30 deletions. No push, PR, merge, other source checkout changes, additional agents, or dependency changes.

The lead's [correction brief](/Users/alphab/.mdx/TMP/pstack/audioface-foundations/program-runtime-corrections-brief.md) and [lifetime adjudication](/Users/alphab/.mdx/TMP/pstack/audioface-foundations/program-runtime-decisions.md) govern this correction. The document specification SHA256 is `c192750843134c617fafc01836248c2288673c114ef08433e971ecd91c088f6e`, verified directly. Approved specifications and prior reports remain unchanged.

## Reused authorities and precise behavior

| Owner | Correction and retained responsibility |
| --- | --- |
| `engine/src/program-values.ts:ProgramValue` | `copyFrom` copies the existing start, target, absolute start frame, and duration into an existing independent cell. It adds no ramp formula or DSP storage. |
| `engine/src/program-runtime.ts:trigger` | After normal scalar resolution and graph binding, each unmodulated live cell copies its installed automation state. Frozen and modulated cells retain their resolved admission values. Existing command validation and rejection remain unchanged. |
| `patch/src/composition/plan.ts:commandsFor` | The existing expanded value delta now checks `ParameterDefinition.lifetime`. Any changed frozen row requires preparation, including changes reached through defaults. Configuration normalization and retained capacity remain in the same classifier. |
| `patch/src/composition/document.ts` | Existing authored validation, derived value refusal, reference pinning, and atomic batch application remain authoritative and unchanged. |
| `control/src/composition-runtime.ts` | Existing desired and applied revision tracking and whole desired revision replanning remain unchanged. |
| `test/foundations/program-support.mjs` | Moved the existing `drain` helper here and removed its former definition and the repeated surface test loop. |

The TypeScript and hygiene guidance kept the change within these owners. There is no second planner, interpreter, DSP implementation, lifetime flag, or compatibility path. Contract and preparation comments now describe the adjudicated frozen rule.

A ramp started at frame 300 over 128 frames still ends at 428 for a Voice admitted at 364. That Voice starts at cutoff 2200 and continues to 2400. Copying all four scalar fields preserves the original arithmetic and endpoint. Each Voice retains a separate mutable value cell.

Frozen edits require preparation in both Voice and Sound scopes. Until installation succeeds, existing Voices and newly admitted Voices use the installed frozen values. Runtime frozen commands still refuse. A frozen edit with no effective value delta retains the existing empty command policy when desired and applied revisions agree. A same value request during divergence still prepares the whole desired document.

## Regression evidence

Evidence directory: [program-runtime-corrections](/Users/alphab/.mdx/TMP/pstack/audioface-foundations/program-runtime-corrections).

The new assertions ran before production edits. `before.tap` records exit 1 with eight tests: three passed and five failed. Actual sample comparison failed for admission at frames 300 and 364. Frozen Voice, frozen Sound, and the existing frozen metadata case received `command` where the adjudicated rule requires `prepare`. `after.tap` records those same eight tests passing, exit 0.

The final tests cover admission before, at, during, at the end, and after the ramp using frames 299, 300, 364, 428, and 450. Each compares actual samples against explicit per-frame step commands, both at 128-frame spans and ragged spans. A later ramp at 480 verifies subsequent updates. An additional case verifies separate cells, overlapping retargeting at 400, exact values at 400, 448, and 496, a later step command, reservation accounting, and zero typed-array buffers or views during rendering and commands.

Parameterized public control tests cover frozen Voice pitch and frozen Sound feedback. Both prove active installation refusal, identical continuing playback, preserved installed ownership, truthful revision divergence, full desired revision reconciliation after a subsequent live edit, and successful cold installation after tail retirement. Subsequent scope samples equal a fresh render of the desired document and differ from the previous program. Existing sample oracle, capacity growth refusal, retained delay shrink and regrowth, reservation refunds, pinned reference, and read-only row tests still pass.

## Commands and results

Commands ran from the integrated worktree with Node `v24.20.0`, pnpm `10.17.1`, Darwin arm64.

```sh
node --test --test-name-pattern='Voice admitted at|frozen .* edits prepare|frozen metadata' test/foundations/program-runtime.test.mjs test/foundations/program-surface.test.mjs
node --test test/foundations/program-runtime.test.mjs test/foundations/program-surface.test.mjs test/foundations/composition.test.mjs test/foundations/runtime.test.mjs test/foundations/scheduling.test.mjs test/worklet-null.test.mjs packages/control/test/composition-surface.test.mjs packages/patch/test/composition-document.test.mjs
pnpm run check
pnpm --filter @audioface/app-web build
node /Users/alphab/.mdx/TMP/pstack/audioface-foundations/program-runtime-proof.mjs
git diff --check
git status --short --untracked-files=all
```

| Evidence | Result |
| --- | --- |
| `after-final.tap` | Exit 0 at the final commit, all nine targeted correction cases passed. Uses the first command above with `admitted ramp cells` added to the name pattern. |
| `focused-final.tap` | Exit 0, 81 passed, no failures or skips. |
| `check.log` | Exit 0, typecheck, all 368 tests, lint, format, and structure verification passed. No failures or skips. Final committed source matches this gate. |
| `web-build.log` | Exit 0, actual web build produced `index.html` 1461 KiB and `null-test.html` 1429 KiB. Only test sorting and formatting changed after this build. |
| `proof.json` | Exit 0 at exact commit `be881a27706a2a624f1a3ae2a3e2e79974bf0a14`. Existing AST proof found maximum file size 532 lines and maximum function size 104 lines across the cumulative foundation change. |
| Git checks | Exit 0, clean tree including untracked files, expected parent and branch. |

Development failures are retained. `focused.tap` had one outdated frozen pitch assertion in the generic control test, subsequently reconciled. `check-initial.log` passed all tests then rejected test `sort()` under the existing lint rule. `check-format.log` passed all tests and lint, then requested formatting of `toSorted()`. Both corrections are included in the passing final gate.

The unchanged PAIR_DELAY 48000-frame sample SHA256 is `bacb7d5461ca078ea620b17bcba310e05e87ba43fc1a298cadac982af615c3c2`. Declared reservation totals remain 33312 bytes for the installed Sound, 33540 with one Voice, and zero after disposal. The probe observes typed-array allocation; it makes no general JavaScript heap or physical memory claim.

## Remaining limitations

Cold replacement refuses while Voices or Sound tails remain active. Classification alone does not resolve editing responsiveness. Active transitions and state transfer remain pending. Local synchronous application acknowledgements do not implement worker wire tickets or generations. Modulated targets and dependencies continue to reject live commands under the existing captured modulation rule.

The bundled worklet registration probe still registers `audioface` and renders 128 silent frames in a simulated worklet realm. This is an old-host portability check. No browser run occurred in this correction, and no direct AudioWorklet `ProgramRuntime` equality, shipping performance, or sonic acceptance claim is made. Independent delta review and direct worklet execution remain the next proof units.

The Markdown index refresh refused `/Users/alphab/.mdx/projects` as outside its configured root. Index scope was not expanded. This report and its digest were verified directly on disk.
