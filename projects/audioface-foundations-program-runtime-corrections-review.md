---
title: Audioface foundations program runtime corrections review
type: projects
tags: [audioface, foundations, runtime, program-spec, review, verification]
summary: Independent verification of be881a2 on the frozen browser worktree; both accepted findings from the 795d803 review are closed by reproduction, the ten file delta is clean, focused tests, typecheck and build pass, and the built pages are byte identical to 795d803.
status: draft
project: audioface
related: [audioface-foundations-program-runtime-review, audioface-foundations-program-runtime-corrections, audioface-foundations-worklet-portability-verification]
confidence: high
---

# Audioface foundations program runtime corrections review

Checkout `/Users/alphab/.mdx/TMP/pstack/audioface-foundations/worktrees/browser`, branch `probe/foundation-browser`, HEAD `be881a27706a2a624f1a3ae2a3e2e79974bf0a14`, sole parent `795d803570e2a593745248ac82704e09ec45333c`. Ten files, +188/−30, no lockfile or manifest change. Tree pristine before and after. Artifacts: `/Users/alphab/.mdx/TMP/pstack/audioface-foundations/program-runtime-corrections-review/`. The brief, the lead's adjudication in `program-runtime-decisions.md` and the document spec at SHA-256 `c1927508…` (verified) govern this pass. Nothing inside any checkout was written.

## Verdict

**Review clean. Both prior findings closed.** No new finding. The delta does what the adjudication asks and nothing else.

| Finding (795d803 review) | State at be881a2 | Evidence |
|---|---|---|
| 1. Voice admitted mid-ramp froze at the instantaneous value | Closed | `ramp-admission.json`, original `ramp-trigger.mjs` now asserts against 2200 and fails with actual 2400 |
| 2. Voice-region frozen edit planned as a command and stranded the document | Closed | `frozen-edits.json`, original `frozen-voice-surface.json` now shows `prepare` and the reclamation refusal |

## Source delta

- **`ProgramValue.copyFrom`** (`program-values.ts`) copies four scalars: start, target, absolute start frame and duration. `ParameterValue` is `number | string | boolean`, so nothing mutable is shared and the deadline `frame + frames` is the original command's, not the admission frame's.
- **`ProgramRuntime.trigger`** (`program-runtime.ts`, now 47 lines) keeps the scalar resolution and graph binding, then for every kernel cell whose row is `live` and not a modulation target copies the installed cell's ramp state. Frozen rows keep the captured scalar; modulated rows keep their admission resolution. Commands still reach the installed cell and every Voice cell separately through `setGraphValue`, so Voice cells stay independent.
- **`commandsFor`** (`plan.ts`) is still the one classifier. After the expanded delta is known it returns `prepare` when any changed row's `ParameterDefinition.lifetime` is `frozen`, before the normalization comparison, so configuration equality cannot turn a frozen edit into a command. This is the same authority `lifetimesOf` (`compile.ts:329`) writes into `ProgramSlot.lifetimes`; there is no second lifetime source. Derived and pinned refusals stay in `document.ts` untouched. The runtime refusal at `program-runtime.ts:213-215` is unchanged.
- **Contract comment** (`program.ts:140-143`) now states the adjudicated rule; the **kernel-preparation comment** adds one sentence about live metadata and touches no code.
- **Tests.** `drain` moved into `program-support.mjs` and its two copies deleted. Five parameterised admission tests (299, 300, 364, 428, 450) compare actual samples with explicit per-frame steps at 128-frame and ragged spans plus a second ramp at 480; one test checks independent cells, retargeting, exact values and zero typed-array storage during rendering and commands. Two parameterised public surface tests cover frozen Voice and Sound edits end to end. Three existing assertions flipped from `command` to `prepare` and one message match from `frozen` to `reclamation`, all matching the adjudication. No skips, no weakened oracle.

## Independent reproductions

`ramp-admission.mjs` (exit 0). Admission at 250, 300, 364, 428, 450 and 520 against a runtime commanded with the closed-form value every frame: 0 mismatches at 128-frame and 1+3+17+113 spans, all audible. Two Voices admitted at 364 and 380 plus the installed cell are three distinct objects reading 2200, 2250, 2396.875 and 2400 at 364, 380, 427 and 428, each holding `frame 300, frames 128`. Retarget at 400 to 2100 over 96 reads 2312.5, 2206.25, 2100 at 400, 448, 496 in all three; mutating one cell leaves the others unchanged. The Voice's `PCH-01` cell equals the installed initial 660, is a distinct object, and a runtime command on it throws `frozen parameter command refused`. In `PAIR_JITTERED` the Voice `FLT-10` cell equals the modulated resolution 1870.797, not the authored 2000, with no ramp state, and a ramp command refuses as a captured modulation dependency. Rendering and a step command after admission: 0 bytes, 0 buffers, 0 views. Every ledger ends at 0 owned bytes.

`frozen-edits.mjs` (exit 0). For Voice `pitch` 330 and Sound `DLY-11` 0.4 through `createInProcessCompositionSurface`: effect `prepare` with no commands, application refused "awaits Voice and Sound tail reclamation", desired 1 applied 0, installed program object unchanged, reservations unchanged, runtime commands 0, 5000 frames equal to a control surface before and after a further Voice. The runtime refuses the same row as a command. A live `cutoff` edit while diverged prepares the whole desired document carrying the frozen value, is refused, desired 2 applied 0, playback still equal. After draining to `tailUntil` (642,920 and 730,216 frames) the same edit installs at revision 3, installations 2, the new program carries the frozen value, a same-value edit is `command []` applied without a third installation, and the next Voice's 20,000 ragged frames equal a fresh render of the desired document and differ from the previous program. Same value with no divergence is `command []`. `DLY-10` 80 commands within the line; 400 prepares and refuses with reservations unchanged.

The original 795d803 scripts rerun verbatim: `ramp-trigger.mjs` exits 1 on its own assertion (actual 2400, expected 2200) with ramped samples now equal to the step-to-2400 run; `frozen-voice-surface.mjs` reports `prepare` and the reclamation message. The author's `before.tap` fails exactly the mid-ramp samples at 300 and 364 and three `command` versus `prepare` cases, which is the original defect pair.

## Gates and build

| Command | Result | Log |
|---|---|---|
| `node --test` over the eight author files plus every `packages/patch` and `packages/engine` test | 203 pass, 0 fail, 0 skip, exit 0 | `focused-be881a2.tap` |
| `pnpm run typecheck` | exit 0 | `typecheck-be881a2.log` |
| `pnpm --filter @audioface/app-web build` | exit 0 | `build-be881a2.log` |
| Lead `pnpm run check` | 368 pass, 0 fail, 0 skip, lint, format, structure pass | `program-runtime-corrections-lead-check-be881a2.log` |

Cited passing tests include the derived and pinned refusals, retained delay shrink and regrowth, failed growth, failed cold installation refund, nested/flat/oracle sample equality, the second sample rate and eight-seed jitter proofs. Oracle `oracle.ts` SHA-256 `f89f80de…` and the probes spec `6615929b…` are unchanged.

## Browser basis

`dist/null-test.html` `b484bf05971c65357c7566dd7fd9cc61d68f2ac4a014d8183a2d88888a1cf38a` (1,463,126 bytes) and `dist/index.html` `8db6ed638ad32095d5b8a3c3979beed48900a4dd840d2b4f07f0ea49f67c2a31` are byte identical to the 795d803 build (`dist-sha256.txt` in both directories). The delta's executable code is in `program-values.ts`, `program-runtime.ts` and `plan.ts`, none of which reach either page, and the two comment edits are stripped by esbuild. **Basis: exact hash equivalence**; the 795d803 headed and headless passes in `browser-program-runtime-795d803/` carry forward and no replay ran. This still proves nothing about `ProgramRuntime` inside an AudioWorklet, which remains the next unit.

## Observations (not findings)

- Every derived default in the registry hangs off a frozen row (`PCH-01`, `AMP-06`), so `rampFor`'s default recursion in `plan.ts` is now unreachable from the fixtures and the removed assertion in composition test 5 was its only coverage.
- The frozen check now precedes the `unknown_kernel` refusal in `commandsFor`; a changed frozen row on an unknown kernel prepares and the compile explains it. Library integrity only.

## Clean tree

After all work: browser `be881a2`, integrated `be881a2`, composition `41699f4`, runtime `9204eaa`, main `10ba9fc`, all 0 changes and 0 untracked; only ignored build outputs under the browser worktree.

## Limitations

1. No browser replay; the basis is hash equivalence, and ProgramSpec is still not exercised in the browser.
2. Focused tests only here on Node v25.9.0; the 368-test full gate is the lead's artifact.
3. Failing-before evidence is the author's `before.tap` and my 795d803 reproductions; 795d803 source was not rebuilt here.
4. The per-frame step reference is the equivalence the repo's own ramp test establishes; `oracle.ts` is ramp unaware.
5. Reproductions read private cell fields and mutate one cell directly to show independence.
6. Load averages 27 to 38, uncontrolled; timings not reported.
7. Cold replacement still refuses while Voices or the tail are active, as adjudicated.
