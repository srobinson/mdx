---
title: Audioface foundations composition build
type: projects
tags: [audioface, foundations, composition, contract, compiler, build-report, correction]
summary: Deliverable one of the foundation probes after its correction round, committed on probe/foundation-composition at 6c36480 over 3455fb3 and baseline 10ba9fc, with the gates that ran, the disposition of all sixteen review findings, the refinements against the document specification, and the exact integration handoff.
status: draft
created: 2026-09-05
updated: 2026-09-05
project: audioface-next
related: [audioface-foundation-document-spec, audioface-foundation-runtime-probes-spec, audioface-foundation-dispositions, audioface-scout-foundations-authoring]
confidence: medium
---

# Composition build, deliverable one, corrected

Worktree `/Users/alphab/.mdx/TMP/pstack/audioface-foundations/worktrees/composition`, branch `probe/foundation-composition`, baseline `10ba9fc16cea55271c6d428c8fe64c8df0b9c354`. Reviewed commit `3455fb343f2db6c137c73daff749882db8ef24ac`; correction commit `6c364806a4c4a312eb20550981ad86c19167f2c3` on top of it, the reviewed commit not amended. Specification pair unchanged: document `e5bce921c9e55a63ece4e17df4e5ed6237d95f988177a870832ea2168a8c73df`, runtime `6615929b170d3681f0fc994985d9f5186316f87b6d0b7322fbcabe5e12f1555d`. The main checkout and the runtime worktree were not touched; both are clean, main at `10ba9fc` and the runtime worktree at its own head `9204eaa9b5be02dffa6b6649110b505c5903b4ff`. The prior version of this report is preserved at `projects/_versions/audioface-foundations-composition-build.v1.md`.

## What the correction changed, by owner

**Contract.** `ProgramSlot.lifetimes` carries each row's read timing and `programKey` hashes it. `ProgramOutput.wetOnly` sits beside `tail`. `EditEffect` gains `{ kind: "none" }`. `KernelPreparation.normalize` takes the configuration a running instance was built with as an optional fourth argument. `CompositionIssueCode` gains `invalid_modulation`. `sha256Hex` encodes with `TextEncoder`; the handwritten encoder is deleted. `src/encoding-globals.d.ts` declares that one host global for the neutral package and is not emitted.

**Patch.** `library.ts`: `sealLibrary` and `assertCursor`; `withSnapshot` checks the cursor and freezes. `document.ts`: insertion into an empty document, the cursor raised to the high water mark of minted shaped ids before a removal, ramp validation, and modulation validation through the shared rule. `scope.ts`: `identityIssues` over placements, links, modulations and exposures; `modulationIssue`; reference cycles tracked by `lineage@revision` in both walkers. `links.ts`: a cycle over rack ports alone is refused before flattening. `compile.ts`: sum order by seed label then port, independent of scheduling; tail provenance through processors and the wet only classification; lifetimes per slot; `compile(…, seedMap?, previous?)` lending each surviving slot its running configuration; the program deep frozen. `plan.ts`: rack edits accepted as `none`; commands as the expanded value delta with ramps carried through defaults; `planEdit(…, edits, running?)`.

**Engine.** The preallocated delay keeps a running line the time still fits; the exact echo ignores the running configuration.

**Control.** The surface seals its initial library.

**Tests.** `packages/patch/test-support/composition-builders.ts` is the one set of typed builders; `composition.mjs` and `test/foundations/fixtures.ts` consume it. Regressions per finding are listed below.

## Gates that ran

All from the worktree root at `6c36480`, clean before and after.

| Command | Result |
| --- | --- |
| `pnpm run check` | exit 0: typecheck, 309 tests (308 pass, 1 skipped, 0 fail), lint, format, structure. Log: `composition-check-6c36480.log` beside the brief. |
| `pnpm --filter @audioface/app-web build` | exit 0, both bundles emitted, no manifest or lockfile change. |
| Corrected tests against the reviewed sources | 27 tests, 12 pass, 14 fail. A scratchpad copy of the worktree with the eleven changed source files restored from `3455fb3`; the composition document test file fails whole at import, because the boundary function it tests did not exist. Log: `composition-failing-before-3455fb3.tap`. |
| `git diff --stat 3455fb3 -- pnpm-lock.yaml '**/package.json'` | empty. `types/` and `dist/` remain ignored. |

Largest changed source `scope.ts` 612 lines; largest test 391 lines; the longest function is under 150 lines by the lint gate.

## Finding dispositions

All sixteen resolved; none rejected; none unresolved. Each accepted finding has a regression that fails on the reviewed sources and passes at the head.

| # | Disposition | Correction and evidence |
| --- | --- | --- |
| 1 | Resolved | Library sealed at the surface and at `withSnapshot`; program deep frozen. Surface test asserts the caller's object is frozen and mutation throws; foundations test 3 asserts the program and its profile are frozen. |
| 2 | Resolved | Commands are the expanded delta. Test 5: pitch 330 gives `PCH-01` and `PCH-01.end-hz`, and a 64 frame ramp is carried to both. |
| 3 | Resolved | `lifetimes` on every slot, in the key. Test 3: `FLT-10` live, `FLT-11` frozen, and a library with the cutoff frozen keys differently. |
| 4 | Resolved | A rack edit passes the surface as a new revision with effect `none`. Test 4 now edits `tone-voice` to revision 2 through the surface; the pinned pair keys as before; repin changes it. |
| 5 | Resolved | `after` checked only when supplied. Document test: `p-01`, `p-02`, emptied, `p-03`; an unknown `after` still refuses. |
| 6 | Resolved | `identityIssues` in every walked composition and in the rack plan. Scope test: `duplicate_id` for a twin placement in either storage order, a duplicate link id, a duplicate exposure through a rack. |
| 7 | Resolved | Cursor raised before removal; cursor checked at the library boundary and the mint. Document test: authored `p-04` removed then insert mints `p-05`; NaN, negative, infinite and fractional cursors throw. |
| 8 | Resolved | Cycle over rack port labels refused before flattening. Scope test: the pass through rack with a self link gives `link_cycle`; without it, main reads the mix. |
| 9 | Resolved | `modulationIssue` shared by the document operation and expansion. Document and scope tests: waveform target, trigger ratio, NaN depth, infinite amount, NaN lerp end, NaN exponent and an unknown curve all refuse `invalid_modulation`; a numeric add and a parameter sourced ratio pass. |
| 10 | Resolved | Sum order by seed label then port. Scope test: `z` feeding `a` with `b`, `c` runs `b, c, z, a` and sums `a, b, c`. |
| 11 | Resolved, with an explicit surface limitation | The kernel keeps a running line the time fits; the planner classifies against the running program when its caller holds one. Test 5: 150 to 80 ms commands at the surface; with the grown program in hand, 80 to 160 commands and an insert keeps 16384 frames and transfers `space`. Without the running program the surface prepares on regrowth, conservatively. See obligations. |
| 12 | Resolved per the lead's policy | `tail` propagates through processors; `wetOnly` holds only when every source is a tail port. Scope test: wet through a filter is `tail true, wetOnly false`; wet alone to `aux` is `true, true`; dry alone `false, false`; the fixture's main `true, false`. |
| 13 | Resolved | Ramp validated before acceptance. Document test and test 5: negative, zero, fractional, wrong shape and string frames refuse `value_out_of_range`; the revision does not advance. |
| 14 | Resolved per the lead's policy | Cycles by full pin. Scope test: `versioned@2 → versioned@1 → tone` compiles to `v.prior.tone`; `versioned@1` pinning `versioned@2` refuses `reference_cycle`. |
| 15 | Resolved | `TextEncoder`. Digest test: six malformed and paired surrogate vectors agree with `createHash`, and a lone surrogate hashes as U+FFFD. The synchronous digest stays. |
| 16 | Resolved | One typed builder module; both catalogues built from it. |

## Refinements against the document specification

Each is recorded rather than silent. None changes a contract another unit consumes today.

1. `ProgramSlot.lifetimes` is not in the specification's slot list. The specification names `lifetime` as the source of read timing and the runtime reads the program, not the library, so the program carries it and the key hashes it.
2. `EditEffect` has a third kind, `none`, for an accepted rack edit. The specification's two kinds cannot express the rack edit its test 4 requires.
3. `ProgramOutput.wetOnly` beside `tail`, per the lead's disposition of finding 12.
4. Sum order is seed label then port. With no seed map this is the specification's placement key order; with one, the mapped twin sums as its original, which placement key order cannot promise.
5. `KernelPreparation.normalize` takes the running configuration, and `compile` and `planEdit` take the running program, all optional. The specification's `normalize(values, profile)` cannot express a capacity that only grows.

## Pending integration

- **Retained Sound programs.** The surface holds no running program, so a regrowth within a line the runtime still holds is prepared rather than commanded, and a transfer map after a shrink is computed against a fresh compile. The planner's `running` input closes both once control retains installed programs through the ticket and acknowledgement path. Test 5 records the conservative surface behaviour and the closed planner behaviour side by side.
- **Test 3, sample half.** Still `skip`, unchanged: nested, flat and the oracle through the shared runtime.
- **Stamping and correlation, transfer validation, split echo, envelope semantics.** As in the prior report.
- **Rack validation.** A rack is accepted by its document operations and identity check; a link cycle inside a rack is refused when a sound compiles it, not when the rack is edited.

## Limitations and risks

No sample, browser or performance claim. `sealLibrary` freezes the caller's objects in place, as `packages/content/src/pack.ts` does; a caller that intended to keep mutating its library must copy first. The encoder declaration relies on the Encoding Standard global being present on every host, which Node, workers and pages provide. `scope.ts` is 612 lines.
