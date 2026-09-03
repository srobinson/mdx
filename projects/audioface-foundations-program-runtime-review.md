---
title: Audioface foundations program runtime review
type: projects
tags: [audioface, foundations, runtime, program, review, resources, browser]
summary: Independent review of 795d803, the shared ProgramSpec executor and retained-capacity surface; two findings, the exact 48000-frame oracle gate and resource accounting verified, and the old-host browser fixture replayed clean without exercising ProgramSpec.
status: draft
created: 2026-09-05
updated: 2026-09-05
project: audioface-next
related: [audioface-foundations-program-runtime-build, audioface-foundations-worklet-portability-verification, audioface-foundations-browser-baseline, audioface-foundation-document-spec, audioface-foundation-runtime-probes-spec]
confidence: high
---

# Program runtime review

Target `795d803570e2a593745248ac82704e09ec45333c`, parent `80fbd6136389e6351aec955fc8fad7324bb6efab`, read from `/Users/alphab/.mdx/TMP/pstack/audioface-foundations/worktrees/browser` on `probe/foundation-browser`. HEAD verified before and after; `git status --porcelain` and the untracked listing were empty both times, the only extra content being the ignored `apps/web/dist/` build. 23 files, +1985/−80, no lockfile, manifest or tsconfig change. Repro artifacts: `program-runtime-review-795d803/` beside the brief. Browser captures: `browser-program-runtime-795d803/`. Nothing under `browser-baseline/` or `browser-portability-80fbd61/` changed.

## Verdict

**Findings: 2, both medium, neither blocks the sample or resource claims.** The executor, oracle gate, retained-capacity surface and ledger do what the build report says. The browser fixture passes at the target but exercises the old bus host only; ProgramSpec is not on that path.

## Findings

### 1. A Voice admitted during a live ramp freezes at the ramp's instantaneous value (defect, medium)

`packages/engine/src/program-runtime.ts:160-165` resolves a new Voice from the Sound's authored values through `resolveProgramValues`, whose reads at `packages/engine/src/program-values.ts:74-75` take `ProgramValue.at(frame)`, a scalar. `createProgramKernel` at `packages/engine/src/program-kernels.ts:179-181` wraps that scalar in a fresh `ProgramValue` with no ramp state. Trigger: command `FLT-10` 2000 to 2400 with a 128 frame ramp at frame 300, trigger at frame 364. Impact: that Voice's cutoff stays at 2200 for its whole life while the Sound's authored value and every earlier Voice reach 2400; the document says 2400. Reproduction `ramp-trigger.mjs`: voice value 2200, Sound authored value 2400, the ramped run's samples after the ramp equal a step to 2200 and differ from a step to 2400. Remedy: carry the live key's ramp state (start, target, frame, frames) into the admitted instance instead of a scalar snapshot.

### 2. Voice-region frozen edits are planned as commands, refused by the runtime, and strand the document (contract conflict, medium)

`packages/engine/src/program-runtime.ts:213-215` refuses every command whose lifetime is not `live`. `packages/patch/src/composition/plan.ts:133-165` never reads a lifetime, so a `set` on a frozen Voice row is a `command`. The shared contract at `packages/contract/src/program.ts:140-143` and the document spec section 4 say a frozen command reaches Voices started at or after its frame; the lead decision says runtime commands to genuinely frozen parameters must refuse, in the Sound delay context, and also says to preserve Voice frozen timing. Reproduction `frozen-voice-surface.mjs` through the public surface with a held `pair`: `pitch` 330 is accepted (revision 1) as commands `a.tone/PCH-01` and `PCH-01.end-hz`, refused with "frozen parameter command refused", applied revision stays 0; the next live `cutoff` edit is then a `prepare` and is refused until Voices and the tail retire, `tailUntil` 633,728 frames, about 13.2 s at 48 kHz. Impact: an exposure edit such as pitch on a held Sound cannot be applied at all in this unit, and the document silently diverges. Remedy is the lead's call: either apply Voice-region frozen commands to the Sound's authored values only, so later triggers read them and resident graphs stay untouched, or have the one classifier return `prepare` for frozen rows on an open Sound. Existing tests assert the refusal (`program-runtime.test.mjs:259`, `program-surface.test.mjs:160-165`), so this was built deliberately; the two authorities still disagree.

## Verified requirements

- **One executor.** `ProgramRuntime` owns installation, Voice admission, commands, clock and outputs; `ProgramGraph` executes a flat prepared operation array with sources resolved before rendering; kernels bind through `toneGenerator`, `createFilterStage`, `filterCutoffSchedule`, `envelopeAmplitudeAt` and `createEchoLine`, each with its baseline caller intact. No second compiler, classifier or oracle interpreter; the oracle is unchanged, SHA256 `f89f80dea45366ad5dc2c741a54229967f661a1f3b4a0a52b4e9b55a1e3c7a50`, and reads no program. Timing: modulation resolves at scope admission with a cycle guard and an explicit authored versus resolved read; live values read per frame; the within-Voice sum is compiler order and the cross-Voice sum is admission order in Float32, proved insensitive to backing-map order and sensitive to admission order.
- **Sample gate.** Nested, mapped flat and oracle equality for 48,000 frames runs with no skip (TAP line 48 here), plus ragged spans, reversed placement, repeatability, eight root seeds, 44.1 kHz. `FLT-14=0` is authored in both fixture forms and asserted through the compiler; only `DLY-10` and `DLY-12` on the curated echo and delay rows are live, `DLY-11` and all Voice rows stay frozen (fixtures diff, repro output).
- **Retained capacity.** The surface hands the installed program and applied revision to `planEdit`; 150 to 80 to 160 ms inside 8192 frames stays `command`, one compilation, one installation, unchanged reservations, same ProgramKey, and wet first appears at frame 3840 as `fround(dry × 0.5)`. Growth to 1000 ms prepares and refuses while Voices or tail are held, samples equal an untouched control, desired revision advances and applied does not; after reclamation the divergent base replans the complete document (`plan.ts:75`) and installs.
- **Resources.** Reservation precedes construction in `trigger` and `prepare`, refunds run on failure paths, membership changes only after success. Exact fit, one byte short, aggregate Voice bound, held release, tail retention through live changes, idempotent disposal and performed work not refunded all pass. `declared-vs-physical.mjs` with the shared probe: Sound declared 33,312 bytes against 33,308 typed-array bytes constructed (hashing's transient 10,420 bytes excluded); one Voice declared 228 against 52 physical, the difference being tone and biquad state declared as bytes but held in JS numbers; active render constructs 0 buffers and 0 views. Declared bytes are an upper bound on typed arrays only; JS object allocation in admission and command validation is real and unmeasured.
- **Boundaries and hygiene.** Engine imports contract only; control imports engine and patch; the barrel exposes `ProgramRuntime`, preparation and the `ProgramTrigger` type, keeping graph, kernels and values private. The inline echo update, the private `countStorage` copy and the pending skip are deleted. Largest file 532 lines, largest function 104. `verify:structure`, lint and format pass in the lead gate.

## Observations, not findings

Cold replacement reserves the candidate program and Sound storage before refunding the old owner, so a ledger with `programs: 1` or exact-fit bytes can never replace; that follows the spec's provisional reservation rule and should be stated. Command validation binds every slot twice per batch, constructing generators and filter stages each time, JS allocation outside render as documented. `ProgramGraph` chooses a kernel's end rule by kernel name string rather than a kernel-owned flag. Sound-region sources never extend `tailUntil`. `program-surface.test.mjs:118` restates `drain`.

## Gates at the target

| Command | Result | Log |
|---|---|---|
| `node --test` over program runtime, surface, composition, runtime host, worklet null, kernel, control surface, patch document and worklet registration tests | 96 pass, 0 fail, 0 skip, exit 0 | `focused-tests-795d803.tap` |
| `pnpm run typecheck` | exit 0 | `typecheck-795d803.log` |
| `pnpm --filter @audioface/app-web build` | exit 0 | `build-795d803.log` |
| Lead `pnpm run check` | 360 pass, 0 fail, 0 skip, lint, format, structure | `program-runtime-lead-check-795d803.log` |

Built hashes (`dist-sha256.txt`): `null-test.html` `b484bf05971c65357c7566dd7fd9cc61d68f2ac4a014d8183a2d88888a1cf38a` (1,463,126 bytes), `index.html` `8db6ed638ad32095d5b8a3c3979beed48900a4dd840d2b4f07f0ea49f67c2a31`. Node here is v25.9.0, the author's v24.20.0.

## Browser replay

`browser-baseline/run-null-test.sh` unchanged, `DIST` at the target build, fresh private sessions `audioface-baseline-headless` and `-headed` that did not exist beforehand. Chrome for Testing 152.0.7977.42, macOS 26.5.2, M2 Max, load 6 to 11.

| Run | Verdict | Rows | Installs | Renders | Wall |
|---|---|---|---|---|---|
| headless | pass | 5 × 96000 frames, difference 0, tail 0 | 5 ok, 1,168,030 chars, 12 to 51 ms | 106 to 146 ms | 1.06 s |
| headed | pass | same | 5 ok, 10 to 42 ms | 106 to 156 ms | 1.13 s |

Rows gun-ar, reload-magout, step-dirt, hitmarker, ambience-wind; page errors empty; screenshots show the table; worklet scope quantum 128 with `performance`, `setTimeout`, `SharedArrayBuffer` undefined; realtime probe 44100 Hz on the built-in device.

**Executed path.** `differential.ts` calls `nullTest`, which installs the worklet and drives `createBusHost` through commands; the page renders the audition offline. The extracted worklet bundle `worklet-795d803.js` differs from the parent's by two mechanical hunks only, the envelope and echo line extractions (`worklet-diff-80fbd61-795d803.patch`), and neither it nor the page bundle contains `ProgramRuntime`, `ResourceLedger` or `createInProcessCompositionSurface`. **ProgramSpec is not exercised in the browser.** This replay proves the shared kernel extractions did not disturb the shipping host, nothing more. The next required browser proof is a page or worker that constructs `ProgramRuntime` inside `AudioWorkletGlobalScope` on the bundled `PAIR_DELAY` or `PAIR_JITTERED` program and compares its output to the Node samples (`sampleSha256` `bacb7d54…` in the proof JSON, or the oracle), extending `apps/web/build.mjs` as the probes spec's deliverable three describes.

## Limitations

1. Focused tests only here; the 360 count is the lead's log.
2. Browser evidence is old-host compatibility; no ProgramSpec, realtime, deadline or performance claim.
3. Offline rendering, uncontrolled load, one browser build, default device changed since the baseline.
4. Traces captured, not analysed.
5. Physical measurement covers typed arrays; JS object allocation and GC unmeasured.
6. Reproductions read TS-private fields (`voices`, `installed`) for evidence.
7. The private headed daemon entry stayed listed after the first `close` and cleared on a second; the user's `tm` sessions were never touched.
