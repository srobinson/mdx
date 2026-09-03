---
title: Audioface foundation ProgramSpec runtime build
type: projects
tags: [audioface, foundations, runtime, program, samples, resources, portability]
summary: The shared curated ProgramSpec executor, exact 48000-frame oracle gate, retained-capacity in-process control path, and portable worklet digest are committed with 360 passing tests and no skips.
status: active
created: 2026-09-05
updated: 2026-09-05
project: audioface-next
related: [audioface-foundations-integration, audioface-foundations-composition-build, audioface-foundations-runtime-prerequisites-build, audioface-foundations-browser-baseline, audioface-foundation-document-spec, audioface-foundation-runtime-probes-spec]
confidence: high
---

# ProgramSpec runtime build

Branch `probe/foundation-integrated` is committed at `795d803570e2a593745248ac82704e09ec45333c`. Its parent is the isolated portability checkpoint `80fbd6136389e6351aec955fc8fad7324bb6efab`, whose parent is merge `95efc3bd51c572a8396c7a6573b67322d8803431`. The integrated worktree is clean. Independent review of the runtime unit remains pending.

Worktree: `/Users/alphab/.mdx/TMP/pstack/audioface-foundations/worktrees/integrated`. The [implementation brief](/Users/alphab/.mdx/TMP/pstack/audioface-foundations/program-runtime-brief.md), [lead decisions](/Users/alphab/.mdx/TMP/pstack/audioface-foundations/program-runtime-decisions.md), and [portability correction](/Users/alphab/.mdx/TMP/pstack/audioface-foundations/worklet-portability-fix-brief.md) define this unit. No other checkout, specification, dependency policy, remote branch, or memory record was changed.

## Merge preflight

Independent checks confirmed a clean starting HEAD at `95efc3b` and its exact parents, runtime `9204eaa9b5be02dffa6b6649110b505c5903b4ff` and composition `41699f487eba5437786a2a8bcaa2316a10f03c08`. The combined diff retained exactly one export each of `kernel-preparation.ts` and `voice-budget.ts`. The barrel introduced no replacement authority. No semantic merge correction was necessary.

The [lead's combined gate log](/Users/alphab/.mdx/TMP/pstack/audioface-foundations/integration-lead-check-95efc3b.log) records 334 passes and the expected sample skip, followed by successful lint, formatting, and structure checks. The [rerunnable proof](/Users/alphab/.mdx/TMP/pstack/audioface-foundations/program-runtime-proof.mjs) verifies the exact parents and barrel exports again.

## Runtime and reuse

[ProgramRuntime](/Users/alphab/.mdx/TMP/pstack/audioface-foundations/worktrees/integrated/packages/engine/src/program-runtime.ts) owns one installed immutable program, Sound state, prepared Voice instances, the absolute frame, and output storage. [ProgramGraph](/Users/alphab/.mdx/TMP/pstack/audioface-foundations/worktrees/integrated/packages/engine/src/program-graph.ts) resolves routing references before rendering and executes a flat operation array. Audio links remain the compiled DAG. No conversion to a fixed layer chain occurs.

The executor supports the curated mono tone, lowpass, highpass, bandpass, Voice envelope, and Sound echo or delay kernels. It validates kernel version, state layout and version, declared demand, execution profile, supported ports, scope, and capacity before membership changes. Unsupported channel shapes and spans refuse. A render span is 0 through 128 frames, and callers read only the requested prefix of each retained output buffer.

The [kernel bindings](/Users/alphab/.mdx/TMP/pstack/audioface-foundations/worktrees/integrated/packages/engine/src/program-kernels.ts) reuse `toneGenerator`, `createFilterStage`, `filterCutoffSchedule`, and `envelopeAmplitudeAt`. Existing source, filter, and envelope callers share those implementations. `createEchoLine` owns the sole delay update arithmetic, consumed by the baseline in-place echo and the new split ports. The previous inline echo update was deleted.

Kernel Float32 rounding remains unchanged. Prepared port cells use Float64 storage so the split wet product stays unrounded until summation, matching the original `dry + level * delayed` arithmetic. Final output buffers are Float32. Voice output sums use explicit compiler order, followed by committed Voice admission order. Reordering the private Voice backing map does not change samples.

[ProgramValues](/Users/alphab/.mdx/TMP/pstack/audioface-foundations/worktrees/integrated/packages/engine/src/program-values.ts) resolves compiled modulation at scope admission through the existing `applyCurve`, `childSeed`, and `drawAt`. Tests distinguish authored from resolved parameter reads, including a dependency on a later audio slot. The dependency walk stays outside rendering. Sound clocks begin at installation, and Voice clocks begin at admission.

The existing `MasterBus` and `createBusHost` retain their shipping callers and finite scheduling guarantees. Their execution path was not retired. The [allocation probe](/Users/alphab/.mdx/TMP/pstack/audioface-foundations/worktrees/integrated/test/foundations/storage.mjs) was extracted from the baseline test and extended for both runtimes, with the previous private copy deleted.

## Exact sample evidence and approved refinements

The formerly skipped test in [composition.test.mjs](/Users/alphab/.mdx/TMP/pstack/audioface-foundations/worktrees/integrated/test/foundations/composition.test.mjs) now executes the nested fixture, its legal flat twin with explicit seed mapping, and the hand-wired oracle for 48,000 frames. All samples match exactly, with no tolerance. It also checks repeatability, shuffled placement storage, and ragged spans. Additional tests cover eight root seeds and exact oracle equality at 44.1 kHz.

The oracle file is unchanged from the merge. Its SHA256 is `f89f80dea45366ad5dc2c741a54229967f661a1f3b4a0a52b4e9b55a1e3c7a50`.

Two fixture refinements have explicit lead approval:

- Both fixture forms now author `FLT-14=0`. They previously inherited the registry's 24-semitone sweep, while the independent oracle explicitly used no sweep. Compiler assertions verify zero in both forms. No oracle arithmetic or expected waveform changed.
- Only curated Sound `DLY-10` and `DLY-12` rows become live. `DLY-11` stays frozen, as do Voice pitch and envelope rows. Legacy registry metadata is unchanged. The existing slot lifetimes and ProgramKey hashing carry the refinement.

The two approved specification files remain unchanged, with SHA256 values `e5bce921c9e55a63ece4e17df4e5ed6237d95f988177a870832ea2168a8c73df` and `6615929b170d3681f0fc994985d9f5186316f87b6d0b7322fbcabe5e12f1555d`.

## Installed capacity and local acknowledgement

[createInProcessCompositionSurface](/Users/alphab/.mdx/TMP/pstack/audioface-foundations/worktrees/integrated/packages/control/src/composition-runtime.ts) retains the actual successfully installed ProgramSpec and its applied revision. The existing document transaction supplies both to `planEdit`. The planner remains the sole edit classifier.

The [surface regressions](/Users/alphab/.mdx/TMP/pstack/audioface-foundations/worktrees/integrated/test/foundations/program-surface.test.mjs) open an 8192-frame line, shrink its delay from 150 to 80 ms, then regrow to 160 ms. Both edits apply as commands, with one initial compilation and installation, unchanged reservations, and the original installed ProgramKey. A separate output capture proves that the 80 ms command moves the first wet samples to frame 3840.

A 1000 ms request produces preparation. With active Voices or a retained tail, installation refuses and playback matches an untouched control sample for sample. Cold resource exhaustion likewise refunds the candidate and preserves the old owner. Document acceptance still advances the desired revision. The applied revision advances only after successful synchronous application.

An optional `appliedRevision` argument now lets the existing planner detect divergence. The next desired edit then prepares the complete latest document against installed capacity, rather than issuing an incomplete delta. Tests recover after tail reclamation and install that revision successfully.

Local application occurs at `ProgramRuntime.frame`. Frozen commands refuse atomically, including mixed batches. Live filter steps and explicit 128-frame ramps match per-frame reference steps and ragged partitioning. Commands to captured modulation dependencies refuse until continuous modulation has an explicit execution contract.

This local acknowledgement does not establish a worker ticket, generation, device presentation time, or wire acknowledgement. This prototype opens one runtime per composition in each surface. Separate shipping Sound identity remains future integration work.

## Resources and reclamation

[ResourceLedger](/Users/alphab/.mdx/TMP/pstack/audioface-foundations/worktrees/integrated/packages/control/src/resource-ledger.ts) is the control-owned aggregate account. Reservation precedes Sound and Voice DSP construction. Failed candidates refund without changing membership or installed state. Voice storage remains charged through the authored release. Sound storage remains owned until explicit disposal or successful cold replacement, including its declared maximum tail.

Default experimental limits are 4 program owners, 32 Voices, 2304 slot records, 36864 parameter records, 18432 connection records, 16,777,216 declared numeric storage bytes, 4,194,304 buffer frames, and 4096 buffer channels. The maximum supported alignment is 8 bytes. Further named limits cover per-frame operations, installation operations, copies, latency, and tails. Each program admits at most 64 slots, 64 output ports, 1024 parameters, and 512 connections. These are test bounds, with no device or shipping approval.

The [machine-readable proof](/Users/alphab/.mdx/TMP/pstack/audioface-foundations/program-runtime-proof.json) records the delay fixture:

| State | Declared numeric storage | Voices | Program owners |
| --- | ---: | ---: | ---: |
| Installed Sound, no Voice | 33,312 bytes | 0 | 1 |
| Sound and one Voice | 33,540 bytes | 1 | 1 |
| After disposal | 0 bytes | 0 | 0 |

Its line capacity is 8192 frames and reserved tail is 720896 frames. Tests prove exact fit, one byte short refusal, aggregate exhaustion, no early tail refund after live changes, and idempotent disposal. Performed installation work remains recorded after reservation refunds. Alignment is a capability check, not an additive residency counter.

Prepared storage includes kernel lines and state, scalar port cells, one kernel scratch per region instance, the mixdown cell, and independent output buffers. JavaScript objects have bounded graph counts but no claimed physical byte size. Canonicalization, hashing, admission, and command validation can allocate ordinary JavaScript objects and temporary storage outside rendering. They are not browser installation-budget proof.

The shared allocation probe observes zero typed-array construction and zero subarray views through ragged active rendering, live commands, release, reports, reclamation, and disposal. This does not establish zero JavaScript allocation. Iteration, lifecycle arrays, returned snapshots, and garbage collection remain separate concerns. Refund means release of this owner's references, without a physical GC claim.

## Worklet portability checkpoint

Fable's [browser baseline](/Users/alphab/.mdx/projects/audioface-foundations-browser-baseline.md) proved that eager `TextEncoder` construction prevented registration at the merge. The seven-file checkpoint `80fbd61` replaces that dependency with one portable UTF-8 encoder and deletes the obsolete global declaration. SHA-256 arithmetic remains shared and synchronous. Surrogate replacement follows the [UTF-8 and TextEncoder contract](https://encoding.spec.whatwg.org/#interface-textencoder).

The new gate bundles the actual app worklet through the same bundler as the web build, evaluates it without Window or Worker-only globals, verifies `audioface` registration, constructs the processor, and renders 128 silent frames. It reproduced the original ReferenceError before the fix. Six focused tests pass afterward, including every individual UTF-16 code unit and 1728 boundary triples against Node's standard hash implementation.

The [checkpoint proof](/Users/alphab/.mdx/TMP/pstack/audioface-foundations/worklet-portability-index-proof.log) bundled 98 modules exclusively from the staged checkpoint, with no uncommitted runtime dependency. The final runtime bundle also passes the restricted-global gate. Real browser replay by the independent verifier remains pending in this handoff. No universal claim about SharedArrayBuffer or performance globals is made.

## Gates and remaining work

Environment: Node `v24.20.0`, pnpm `10.17.1`, macOS arm64. Commands ran in the integrated worktree.

| Check | Result | Evidence |
| --- | --- | --- |
| Focused program, surface, composition, resource, scheduling, kernel, and host regressions | 104 pass, 0 fail, 0 skip | [Focused log](/Users/alphab/.mdx/TMP/pstack/audioface-foundations/program-runtime-focused-final.tap) |
| `pnpm run check` | Exit 0, 360 pass, 0 fail, 0 skip, plus typecheck, lint, format and structure | [Full gate](/Users/alphab/.mdx/TMP/pstack/audioface-foundations/program-runtime-check.log) |
| `pnpm --filter @audioface/app-web build` | Exit 0, both pages emitted | [Build log](/Users/alphab/.mdx/TMP/pstack/audioface-foundations/program-runtime-web-build.log) |
| `node .../program-runtime-proof.mjs` | Exact merge, current program/resource values, worklet registration, sizing | [Proof JSON](/Users/alphab/.mdx/TMP/pstack/audioface-foundations/program-runtime-proof.json) |

The final full gate and actual web build each ran once after executable changes settled. Earlier focused checks found and corrected a strip-only TypeScript syntax issue, a held-release lifetime issue, and unused-import or instrumentation lint findings. No behavioral assertion was weakened. The largest changed file is 532 lines and the largest function is 104 lines by the parser proof.

The exact focused command was:

```sh
node --test test/foundations/program-runtime.test.mjs test/foundations/program-surface.test.mjs test/foundations/composition.test.mjs test/foundations/runtime.test.mjs test/foundations/scheduling.test.mjs test/worklet-null.test.mjs packages/engine/test/source-generator.test.mjs packages/engine/test/layer-echo.test.mjs packages/engine/test/layer-filter.test.mjs packages/engine/test/amplitude-envelope.test.mjs packages/control/test/composition-surface.test.mjs packages/patch/test/composition-document.test.mjs
```

The exact final proof command was:

```sh
node /Users/alphab/.mdx/TMP/pstack/audioface-foundations/program-runtime-proof.mjs
```

The runtime implementation commit changes 23 files, with 1985 insertions and 80 deletions. The portability checkpoint is separate. The architecture sketch considered block buffers and a prepared scalar schedule; the latter became the small shared executor. Its [source-grounded sketch](/Users/alphab/.mdx/TMP/pstack/audioface-foundations/program-runtime-sketch.md) records the ownership choice.

Remaining obligations are independent code review, actual corrected browser replay, worker transport and tickets, generation checks, device scheduling, game integration, spatial adapter isolation, native comparison, active program transfer or transition comparators, and performance or sonic acceptance. Active structural replacement currently refuses until Voices and the Sound tail retire. No state transfer is attempted or claimed. Tone glides require an explicit duration on the tone slot. Arbitrary plugins, continuous modulation updates, and multichannel kernels remain outside this curated runtime. Passing these Node samples establishes those samples in this environment.

The Markdown index refresh rejected `/Users/alphab/.mdx/projects` as outside its configured root. The report and digest were verified directly on disk; index roots were not broadened.
