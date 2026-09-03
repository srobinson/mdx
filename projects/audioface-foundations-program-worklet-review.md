---
title: Audioface foundations program worklet proof review
type: projects
tags: [audioface, foundations, runtime, audioworklet, browser, review, verification]
summary: Independent source and browser verification of ea487fb on the frozen browser worktree; the test-only worklet runs the production ProgramRuntime from real process callbacks, all 22 cases match Node and the references byte for byte in fresh headed and headless sessions, the three negative controls and thirteen checker probes fail as required, and the ramp recursion test genuinely covers its path.
status: draft
project: audioface
related: [audioface-foundations-program-worklet-proof, audioface-foundations-program-runtime-corrections-review, audioface-foundations-worklet-portability-verification]
confidence: high
---

# Audioface foundations program worklet proof review

Checkout `/Users/alphab/.mdx/TMP/pstack/audioface-foundations/worktrees/browser`, branch `probe/foundation-browser`, HEAD `ea487fbb031ec467c24d06ea60008387fc9cb7c7`, sole parent `be881a27706a2a624f1a3ae2a3e2e79974bf0a14`. Eight files, +707/−4, no production, oracle, fixture, adapter, manifest or lockfile change. Tree at 0 changes before and after. Artifacts: `/Users/alphab/.mdx/TMP/pstack/audioface-foundations/program-worklet-review/`. The review brief, the author's brief, digest and report, and the approved specs (`audioface-foundation-document-spec.md` at `c1927508…`, `audioface-foundation-runtime-probes-spec.md` at `6615929b…`, both verified unchanged) govern this pass. Nothing tracked inside any checkout was written.

## Verdict

**Review clean.** The proof does what the brief asks. No finding. Three low observations, none affecting the claim, are listed below.

## Source: what the proof exercises

- **Production runtime from real callbacks.** `program-worklet.ts` registers only `audioface-program-proof`. A `prepare` message on the worklet port (a rendering-thread message task, stated in the file comment) compiles through the existing `compiled` helper (production `compile` with `ENGINE_KERNELS`) and constructs the production `ProgramRuntime` through `runtimeFor` with a `ResourceLedger`. `process` throws if unprepared, counts calls and quantum lengths, and calls `ProgramProofRun.renderInto`, which calls `ProgramRuntime.render` in spans of at most `BLOCK_FRAMES` split at the scheduled command and admission frames, then copies `runtime.outputs.get("main")` into the browser's supplied channel. Samples reaching the page are `OfflineAudioContext.startRendering()` output; the page's `proofReference` runs on the main thread only as a comparison target after capture. There is no main-thread render path into the captured rows.
- **No second interpreter or DSP, no boundary breach.** Reference for the ten oracle cases is the unchanged hand-wired `renderOracle` (`oracle.ts` SHA-256 `f89f80de…`). Reference for the ramp and capacity cases is the same `ProgramRuntime` driven one frame at a time with closed-form cutoff steps, the equivalence the repository already uses. `fixtures.ts` is unchanged (`7242ec8a…`). No engine import of patch exists. Shipping entrypoints are untouched; `build.mjs` only adds a third page.
- **Portable assertions.** Three `assert` calls in `program-support.mjs` became throwing checks with equivalent conditions; every existing caller still uses the same helper.
- **Ramp recursion coverage.** The new `composition-document.test.mjs` case builds a library whose stub `tone` declares `PCH-01.end-hz` and `PCH-01` live, so a ramped `pitch` set must reach the derived row through `rampFor`'s default recursion. Mutation probe: a loader hook swapped `plan.ts` for a copy whose recursion returns `null` (`rampfor-mutation.tap`, `rampfor-mutation-wider.tap`). Only this test fails (expected ramp, actual `null`); the other 51 patch and composition surface tests still pass, so the path had no other coverage and production metadata is unchanged.
- **Required cases are grounded.** `PROGRAM_CASES` lists eleven cases at each of 48000 and 44100 Hz: nested, mapped flat, repeat, other-seed nested and flat, admissions at 299, 300, 364, 428 and 450 around the frame-300 ramp with a second ramp at 480, and a capacity case commanding `DLY-10` to 80 at 37 and 160 at 5003 with a frozen `DLY-11` command refused at 5111. `verifyProofReport` requires frame 48000, one installation, two commands for non-oracle cases, three events, one refusal for capacity, retained program identity, zero disposed bytes, zero live Voices, and unchanged installation work through the capacity edits. `verifyWorkletExecution` requires processor name, `ProgramRuntime` constructor name, absent `window`, 375 calls, the case sample rate, and quantum 128 at both extremes.
- **Distinctions.** Independent reference: the oracle cases (different DSP wiring). Shared-implementation parity: the ramp and capacity references (same runtime, independent driving path) and the Node `renderProof` comparison (identical fixture scheduler). Test-only counters: `renderCalls`, `events`, `refusals`, `retained`, `calls`, `minQuantum`, `maxQuantum`. Production invariants: `snapshot.frame/voices/installations/commands`, ledger `ownedBytes`, `performedInstallationOperations`.
- **Hygiene.** Largest new file 267 lines; largest new function is the 51-line `ProgramProofRun` constructor. `drain`, `capture`, `compiled`, `runtimeFor`, `countStorage` and the fixtures are reused.

## Browser runs (all mine, fresh private sessions, clean tree)

| Run | Exit | Evidence |
|---|---|---|
| `verify-program-worklet.mjs headless` | 0, 22 cases | `headless/result.json`: every row 48000 frames, 375 calls, quantum 128, `window` undefined, `ProgramRuntime`, 0 Node and 0 reference mismatches; page errors and console empty; old-host null page pass with 5 rows |
| `verify-program-worklet.mjs headed` | 0, 22 cases | `headed/result.json`, same checks; `program-test.png` inspected, 22 PASS rows |
| `processor-error` | 1 | terminal `48000-nested: processorerror`, 0 rows |
| `timeout` | 1 | terminal `48000-nested: timeout`, 0 rows |
| `sample` | 1 | Node comparison `mismatches 1, first 364, maxDifference 0.7578050792217255`, page verdict pass, 0 rows accepted |

All 22 sample hashes in both modes are identical to each other and to the author's headed and headless runs (`sample-sha256.txt`); 48000 nested `d59db0d0…`, other seed `c9eec6c3…`, 44100 nested `26a66a45…`, other seed `9dfebd7a…`. Repeat and mapped-flat hashes equal their nested case and the other seed differs, in both modes. Ramp rows report 377 or 378 render calls, 3 events, 2 commands; capacity rows report 1 refusal and unchanged installation work (8307 → 8307); every row disposes to 0 bytes.

## Checker probes (`probes/`)

The real `verify-program-worklet.mjs` was driven with a stand-in `agent-browser` on `PATH` that answers from the author's headless capture, mutated per variant (`fake-agent-browser.cjs`, `mutate-capture.mjs`, `summary.txt`). Control exits 0 with 22 cases, proving the checker recomputes Node and reference samples offline. Zero cases, an omitted row, a truncated capture (47999), an omitted frame in the report, a `NaN` sample, a `null` sample, a missing callback (374), a wrong runtime name, one corrupted sample, swapped rows, a stale refusal count, and a page error each exit 1 with the expected message.

## Gates and build

| Command | Result | Log |
|---|---|---|
| `node --test` over the worklet, composition-document and program-runtime tests | 58 pass, 0 fail, 0 skip | `focused-ea487fb.tap` |
| `pnpm run typecheck` | exit 0 | `typecheck-ea487fb.log` |
| `pnpm --filter @audioface/app-web build` | exit 0 | `build-ea487fb.log` |
| Lead `pnpm run check` | 394 pass, 0 fail, 0 skip, lint, format, structure | `program-worklet-lead-check-ea487fb.log` |

Built hashes here equal the author's: `program-test.html b2ae817d4b6fc607ad285d8ea1a105aff238d3bca2f0dcba24c9968d79b6648e`, `index.html 8db6ed63…` and `null-test.html b484bf05…` unchanged from the reviewed base (`dist-sha256.txt`), so the old-host page carries its prior basis and was also replayed in both sessions.

## Observations (not findings)

1. Nonfinite samples cannot reach the Node checker through the JSON capture: `NaN` serialises to `null` and lands as 0. The page's own `compareProof` throws before the row is pushed, so the run still fails; the Node `Nonfinite` branch is reachable only by the probe's string value. Test-only.
2. The verifier records `dirty` but does not assert it; a dirty tree passes (my first runs, preserved under `first-run-with-stray-log/`, show `?? .log`). Tree cleanliness rests on the reviewer.
3. The closed-form cutoff steps and the `FLT-10` command helper now exist in both `program-runtime.test.mjs` (lines 260 to 270) and `program-worklet-support.mjs` (`cutoff`, `proofReference`). A shared test helper would remove the copy. Test-only hygiene.

## Clean tree

Browser and integrated `ea487fb`, composition `41699f4`, runtime `9204eaa`, main `10ba9fc`, all 0 changes after the work. My own stray untracked `.log` at the browser worktree root, written by a failed shell loop during the first headless attempt, was deleted; the affected runs were kept aside and every canonical run here reports `dirty` empty.

## Limitations

1. Offline equality only; no realtime deadline, wire, ticket, worker preparation or shipping-support evidence. Preparation runs on the rendering thread's message task by design.
2. Chrome reports a reduced user agent (152.0.0.0 headed, HeadlessChrome 152.0.0.0); exact build not captured.
3. Node v25.9.0 here against the author's v24.20.0; equality held on both.
4. Ramp and capacity references share the runtime; only the oracle cases are DSP-independent.
5. Checker probes exercise the Node side through a stand-in browser; the three browser negatives are the only in-browser failure paths.
6. Allocation evidence is the existing Node typed-array probe, excluding ramp admissions; no browser heap measurement.
7. Load averages 6 to 10, uncontrolled; no timings reported.
