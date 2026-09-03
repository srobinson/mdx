---
title: Audioface direct ProgramRuntime AudioWorklet proof
type: projects
tags: [audioface, foundations, runtime, audioworklet, browser, verification]
summary: Real headed and headless AudioWorklets at ea487fb match Node and independent references byte for byte across 22 cases each, with explicit negative controls.
status: active
created: 2026-09-05
updated: 2026-09-05
project: audioface-next
---

# Direct ProgramRuntime AudioWorklet proof

Commit `ea487fbb031ec467c24d06ea60008387fc9cb7c7`, sole parent `be881a27706a2a624f1a3ae2a3e2e79974bf0a14`, proves actual `ProgramRuntime` execution in a real browser AudioWorklet. All 22 cases pass in fresh headed and headless Chrome sessions. Every captured sample and Float32 byte hash equals production Node rendering and its independent reference. No tolerance was introduced. Independent review of this commit remains pending.

The sole source worktree is `/Users/alphab/.mdx/TMP/pstack/audioface-foundations/worktrees/integrated`, branch `probe/foundation-integrated`. It was clean at the authorized base and is clean at the final commit. Eight files changed, with 707 insertions and four deletions. There are no production runtime changes, dependency changes, other checkout writes, agents, remote pushes, PRs, or merges.

The [lead brief](/Users/alphab/.mdx/TMP/pstack/audioface-foundations/program-worklet-proof-brief.md) governs this unit. Inputs included the program build, corrections, independent corrections review, and existing browser baseline scripts. Verified specification SHA256 values are `c192750843134c617fafc01836248c2288673c114ef08433e971ecd91c088f6e` for the document specification and `6615929b170d3681f0fc994985d9f5186316f87b6d0b7322fbcabe5e12f1555d` for runtime probes. Neither changed.

## Reuse and execution

All source paths in this section are relative to the integrated worktree.

| Existing authority | Reuse in this proof |
| --- | --- |
| `packages/patch/src/composition/compile.ts`, engine `ENGINE_KERNELS` | The existing `compiled` helper calls the production compiler with production kernel preparation capabilities. No compiler copy or engine import of patch was added. |
| `test/foundations/fixtures.ts`, patch `test-support/composition-builders.ts` | Unchanged nested, flat, delay, profile, library, and explicit seed mapping fixtures. |
| `test/foundations/program-support.mjs` | Existing `TRIGGER`, `compiled`, and `runtimeFor`. Three Node assertion calls became equivalent throwing checks so the same helper can load in a browser. Existing callers remain on this helper. |
| `packages/engine/src/program-runtime.ts`, `program-preparation.ts`, `program-graph.ts`, `program-kernels.ts` | Actual installed program validation, reservations, independent Voice state, live commands, retained outputs, and rendering. No executor or DSP arithmetic was copied. |
| Contract `rootSeed`, `voiceSeed`, `childSeed`, `BLOCK_FRAMES`; engine `transcendental.ts` | Existing explicit seed and profile rules, quantum capacity, and math implementation. The additional seed uses `childSeed(TRIGGER.root, "other")`. |
| `test/foundations/oracle.ts`, existing ramp tests | Unchanged hand-wired oracle for nested and flat samples. Command cases use an independently driven per-frame runtime with closed-form steps, following the established ramp reference. |
| `apps/web/bundle.mjs`, `build.mjs`, worklet data URL pattern | Existing bundler and page emitter produce an additional isolated `program-test.html`. Shipping entries and their bundles remain unchanged. |
| `adapters/web/src/differential.ts`, built `null-test.html`, baseline private-session workflow | Existing old-host compatibility page reruns in each new private session. Browser control uses `agent-browser`, with fresh process-specific session names and closed sessions afterward. |
| `test/foundations/storage.mjs` | Existing constructor and subarray instrumentation tests the new fixture renderer without adding another allocation probe. |

The new `scripts/test-support/program-worklet.ts` registers only `audioface-program-proof`. A preparation message selects a case from the fixed fixture list. The worklet message task compiles and prepares its own program and constructs the actual `ProgramRuntime` through `runtimeFor`. The page waits for readiness before starting the offline context. There is no ProgramSpec transfer or reconstruction claim.

`ProgramProofProcessor.process` calls `ProgramProofRun.renderInto`, which splits supplied output spans at predetermined command and admission frames, calls `ProgramRuntime.render`, and copies from retained runtime output into the browser's supplied channel buffer. It allocates no capture array or subarray. Per-callback telemetry consists only of scalar counters. The page requests the final report after `startRendering` completes. Report construction, serialization, and disposal occur in a separate worklet message task.

The report verifies the processor name, `ProgramRuntime` constructor identity, absent `window`, actual worklet sample rate, callback count, quantum lengths, runtime frame, command and installation counts, retained program identity, refusals, and reservation refund. This evidence requires successful callbacks and audible samples. Module loading alone cannot pass it.

## Samples and command behavior

Each browser session captures 22 cases, each 48,000 frames: 1,056,000 mono samples and 8,250 callbacks. Both sample rates have eleven cases. Each case reports exactly 375 callbacks with observed quantum length 128.

| Cases at each sample rate | Result |
| --- | --- |
| Nested, mapped flat, repeated nested | Exact equality with the unchanged oracle and Node. Repeat and mapping hashes are equal. |
| Additional seed, nested and mapped flat | Exact equality with the oracle and Node. Mapped hashes are equal and differ from the first seed. |
| Voice admission at 299, 300, 364, 428, and 450 | Exact equality with independently commanded per-frame steps and Node. |
| Retained delay capacity and frozen refusal | Exact equality with a separately driven Node reference that omits the refused command. |

The 48 kHz nested sample SHA256 is `d59db0d0a0b4b01d5150e20930d272f581234a6daa92609b05f119fed9064799`. The additional seed is `c9eec6c3d48ad70792f35699060cc2085aaabdd589dbeaa3d0b5548f108396d8`. At 44.1 kHz they are `26a66a4578edc1319d75c177f8ccd691aae3625865f9c643c62bf177d0597adb` and `9dfebd7a58fd367e8062767420b575c00ac14e001368b1c452dc5f9f35d8ce28`. All remaining hashes, profiles, seeds, keys, resources, and raw samples are in the [proof artifacts](/Users/alphab/.mdx/TMP/pstack/audioface-foundations/program-worklet-proof).

The ramp begins at frame 300, moving cutoff from 2000 to 2400 over 128 frames. Admission at 364 receives the remaining ramp, ending at the original frame 428. A second ramp begins at 480 and reaches 2100 at 576. Full 48,000-frame equality with closed-form per-frame steps verifies the endpoint and subsequent samples. These frame stamps remain literal at both sample rates; this is a frame-semantics comparison, not equal wall-clock timing between rates.

The delay case commands 80 ms at frame 37 and 160 ms at frame 5003 within the originally retained 8192-frame line. A direct command to frozen `DLY-11` at 5111 refuses. The program identity remains retained, installation count remains one, successful command count is two, and performed installation work remains unchanged through the edits. Final reports match Node resources and show zero owned bytes after disposal.

Fable's minor `rampFor` coverage observation is addressed by a focused test in `packages/patch/test/composition-document.test.mjs`. The existing stub kernel fixture declares its two related rows live, with the dependent row first. Both inherit the requested ramp through `planEdit`. Production pitch metadata remains frozen.

## Exact gates and artifacts

Commands ran from the integrated worktree. Environment: Node `v24.20.0`, V8 `13.6.233.17-node.53`, pnpm `10.17.1`, Darwin arm64, `agent-browser 0.36.0`. Observed user agents identify headed `Chrome/152.0.0.0` and headless `HeadlessChrome/152.0.0.0`; these are reduced browser versions. No timing or device-support conclusions follow from them.

| Final check | Result and artifact |
| --- | --- |
| `pnpm run check` | Exit 0, 394 tests passed, zero failures or skips, typecheck, lint, format and structure passed. `check-final.log`. |
| `pnpm --filter @audioface/app-web build` | Exit 0 at final SHA. `build-final.log`. |
| Additional strict check of browser TypeScript | Exit 0. `proof-typecheck-final.log`; exact command below. |
| `node scripts/verify-program-worklet.mjs headless .../program-worklet-proof/headless` | Exit 0, all 22 cases, exact samples and bytes, no page errors. `headless/result.json`, `capture.json`, `commands.json`, console, errors, and screenshots. |
| Same command with `headed` and `.../headed` | Exit 0, all 22 cases. Equivalent artifacts under `headed/`. |
| Same verifier with final argument `processor-error` | Expected exit 1, terminal `processorerror`. `final-negative-processor/` and its log. |
| Same verifier with final argument `timeout` | Expected exit 1, terminal timeout. `final-negative-timeout/` and its log. |
| Same verifier with final argument `sample` | Expected exit 1, exactly one corrupted sample at frame 364, difference `0.7578050792217255`. `final-negative-sample/` and its log. |
| Existing `program-runtime-proof.mjs` | Exit 0, exact HEAD, unchanged legacy sample hash, retained resources, old-host VM registration and source sizing. `runtime-recheck.json`. |

Each real-browser run first proves the ProgramRuntime page, then opens the existing old-host page. Both old-host replays pass all five `audioface.skirmish` events. Screenshots are `program-test.png` and `null-test.png` in each mode directory. The headed ProgramRuntime screenshot was visually inspected and shows all 22 passing rows.

Final built SHA256 values:

```text
program-test.html b2ae817d4b6fc607ad285d8ea1a105aff238d3bca2f0dcba24c9968d79b6648e
index.html        8db6ed638ad32095d5b8a3c3979beed48900a4dd840d2b4f07f0ea49f67c2a31
null-test.html    b484bf05971c65357c7566dd7fd9cc61d68f2ac4a014d8183a2d88888a1cf38a
```

The latter two equal the independently checked base bundles. `oracle.ts` remains `f89f80dea45366ad5dc2c741a54229967f661a1f3b4a0a52b4e9b55a1e3c7a50`; fixtures remain `7242ec8a6b1ea48e408cf1f1944a5c724f018478a435b936cb5f4065e097f92a`.

The additional browser-source check is:

```sh
pnpm exec tsc --ignoreConfig --noEmit --allowJs --strict --noUncheckedIndexedAccess --noImplicitOverride --target ES2024 --module NodeNext --moduleResolution NodeNext --lib ES2024,DOM --allowImportingTsExtensions --skipLibCheck scripts/test-support/program-worklet.ts scripts/test-support/program-worklet-page.ts adapters/web/src/worklet-globals.d.ts
```

Development failures remain visible. `check-initial.log` records Node discovering and executing the initial browser entries under `test/`, where browser globals were absent. Moving those entries to `scripts/test-support` fixed discovery without conditional no-op tests. `proof-typecheck.log` records two pre-existing `fixtures.ts` optional-property errors when additionally enabling `exactOptionalPropertyTypes`. The standalone successful check above omits that option; root production typecheck retains its existing settings, and fixtures remain unchanged. Initial lint requested event listeners and explicit MessagePort transfer lists. The new default-row regression initially expected the inverse of declared row order; its expected order now derives from the same declared key list. These development diagnostics did not require a production behavior change.

The largest new file is 267 lines. The parser recheck reports a maximum new-function size of 51 lines. All touched files are below 700 lines and functions below 150. TypeScript and code hygiene guidance kept the implementation in reusable fixture and verification code, with no alternate compiler, DSP, shipping protocol, or package boundary exception.

## Limits

This is offline equality evidence for the observed Chrome and Node engines. It does not prove real-time deadlines, audible quality, live wire arrival, tickets, generations, asynchronous worker preparation, state transfer, active transitions, game integration, spatial behavior, or shipping browser support.

Compilation and preparation intentionally run in a worklet message task for this proof. The predetermined fixture schedule supplies commands before rendering begins. Voice admission still constructs production Voice state at its scheduled frame. No claim of allocation-free admission, bounded browser installation CPU time, or total JavaScript heap control is made.

The existing Node allocation probe observes zero typed-array buffers and views through the prepared oracle and capacity render paths. It excludes ramp cases that admit a Voice during rendering. Browser typed allocations, ordinary objects, MessagePort serialization, engine allocations, and GC are not instrumented. Main-thread capture is bounded to 22 arrays of 48,000 samples. No per-block sample messages or report objects enter `process`.

Cold replacement still waits for Voices and tails. The original frozen preparation and retained-capacity rules are preserved. Independent Fable review follows this handoff.

The Markdown index refresh refused `/Users/alphab/.mdx/projects` as outside its configured root. Index scope was not expanded. The report and digest were verified directly on disk.
