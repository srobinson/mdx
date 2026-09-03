---
title: Audioface foundations worklet portability verification
type: projects
tags: [audioface, foundations, browser, web-audio, worklet, portability, verification]
summary: Independent verification of fix 80fbd61 on the frozen browser worktree; the seven file delta is clean, and the built null test page that failed at 95efc3b now passes 5 of 5 events headless and headed in Chrome for Testing 152.
status: draft
project: audioface
related: [audioface-foundations-browser-baseline, audioface-foundations-integration, audioface-foundations-composition-build]
confidence: high
---

# Audioface foundations worklet portability verification

Checkout `/Users/alphab/.mdx/TMP/pstack/audioface-foundations/worktrees/browser`, branch `probe/foundation-browser`, HEAD `80fbd6136389e6351aec955fc8fad7324bb6efab`, parent `95efc3bd51c572a8396c7a6573b67322d8803431` (the failing baseline). Seven files, +143/−29, no lockfile or manifest change. Artifacts live in `/Users/alphab/.mdx/TMP/pstack/audioface-foundations/browser-portability-80fbd61/`; the original failed baseline under `browser-baseline/` is untouched.

## Verdict

**Review clean. Browser pass.** The page that reported `data-verdict="error"` at 95efc3b reports `data-verdict="pass"`, `Null test audioface.skirmish PASS 5 events`, at 80fbd61 in the same Chrome for Testing 152.0.7977.42, headless and headed, with every row at 96000 frames, difference 0, tail 0. This is correctness and portability evidence under uncontrolled load, not performance characterisation.

## Source delta

- **Digest.** `packages/contract/src/digest.ts` drops the top level `new TextEncoder()` for a private `utf8()` written in ECMAScript only. String iteration joins valid surrogate pairs; a code point left in D800 to DFFF is an unpaired surrogate and becomes U+FFFD, which is the USVString conversion the standard encoder performs. Three byte and four byte branches follow RFC 3629. `sha256Hex` is otherwise unchanged; canonical JSON is unchanged.
- **Oracle coverage.** `packages/contract/test/digest.test.mjs` keeps the block shape, canonical order and malformed vectors, and adds an exhaustive sweep of all 65536 single UTF-16 code units plus 1728 boundary triples (12 edge units cubed) placed after 55 bytes so each straddles a SHA-256 block boundary, every one compared with Node's `createHash`. A third test imports the module in a subprocess after `delete globalThis.TextEncoder` and checks the digest of `a\uD800😀`. No test borrows an encoder into the worklet realm; the digest test deletes it and the realm gate asserts it absent.
- **Ambient declarations.** `packages/contract/src/encoding-globals.d.ts` is deleted, and no other declaration replaces it. The contract compiles against `lib: ["ES2023"]` alone (`tsconfig.base.json`), so the passing typecheck proves the package reads no host global.
- **Registration gate.** `apps/web/test-support/worklet-realm.mjs` evaluates the real worklet bundle in a bare `vm` context holding only `sampleRate`, `currentFrame`, `currentTime`, a stub `AudioWorkletProcessor` and `registerProcessor`, after asserting `TextEncoder`, `TextDecoder`, `window`, `document`, `Worker`, `performance` and `setTimeout` are undefined. It then requires the `audioface` registration and one silent 128 frame quantum. `apps/web/test/worklet-registration.test.mjs` feeds it `bundleWorklet()`; `test-support/` sits outside the runner's `test/` glob, and the gate is discovered by plain `node --test` (TAP `ok 15`, lead log line 27). Before the fix it fails with the recorded `ReferenceError` (`worklet-portability-before.tap`). It is a gate over the listed globals, not an AudioWorklet emulation, which the file says.
- **Bundler.** `bundle()` moves verbatim from `build.mjs` into `apps/web/bundle.mjs` with the same options plus `absWorkingDir: import.meta.dirname`, so the test can call it from any cwd while builds stay identical. `bundleWorklet()` is the one worklet entry. No second bundler exists.
- **Emitted worklet.** `extract-worklet.mjs` recovered the inlined bundle (`worklet-80fbd61.js`, 676,151 chars, one `registerProcessor`). Its diff against `worklet-95efc3b.js` is a single hunk removing `var UTF8 = new TextEncoder();` (`worklet-diff-95efc3b-80fbd61.patch`). esbuild had already shaken `sha256Hex` out of both worklet bundles; only the eager constructor survived as a side effect, so the worklet code is otherwise byte identical. Remaining host names in the bundle are zod's `typeof navigator` guard, `URL` inside URL validators that run only when such a schema is checked, and `globalThis` config slots; `window` and `document` occur only in comments and error strings.
- **Isolation.** Built from a clean checkout with the unchanged frozen lockfile. The integrated worktree (now `795d803`) was not read.

## Tests and build

| Command | Result | Log |
|---|---|---|
| `node --test packages/contract/test/digest.test.mjs apps/web/test/worklet-registration.test.mjs` | 6 pass, 0 fail, exit 0 | `targeted-tests-80fbd61.tap` |
| `pnpm run typecheck` | exit 0 | `typecheck-80fbd61.log` |
| Lead `pnpm check` | 338 tests, 337 pass, 1 skipped (ProgramSpec sample), lint, format, structure pass | `portability-lead-check-80fbd61.log` |
| `pnpm --filter @audioface/app-web build` | exit 0 | `build-80fbd61.log` |

Built hashes (`dist-sha256.txt`): `null-test.html` `e26687cc572b416653f0069d1a530b7eadb3f4a6714f64cb172999e8dc1831b1` (1,461,211 bytes), `index.html` `b9fb926dda83b22d3a6783fd446a473bd3347ccd4e3706d492b35d15776c4dbb`. Baseline: `6bd4c59c…`, `1644f061…`.

## Browser replay

`browser-baseline/run-null-test.sh` unchanged, `OUT` pointed at the new directory. Sessions `audioface-baseline-headless` and `-headed` did not exist beforehand (only `default`, `tm`, `tm-s2` were listed, none touched); each run launches a fresh Chrome for Testing 152.0.7977.42 process, opens the page from `file://` and installs the worklet from a data URL, so no module or HTTP cache carries over. Every run has `profile.json`, `result.json`, `console.txt`, `errors.txt`, `null-test.png`, `verdict.txt`, `run.log`; `summary.json` folds them.

| Run | Verdict | Rows | Installs | Renders | Wall to verdict | Load (1 min) |
|---|---|---|---|---|---|---|
| headless | pass | 5 × 96000 frames, difference 0, tail 0 | 5 ok, 1,166,491 chars, 20 to 71 ms | 187 to 288 ms | 1.72 s | 49 |
| headed (run 1) | pass in `result.json` | same | 5 ok, 16 to 71 ms | 188 to 282 ms | 1.69 s | 51 |
| headed-2 | pass, end to end | same | 5 ok | as above | 0.94 s | 8 |

Rows in every run: gun-ar, reload-magout, step-dirt, hitmarker, ambience-wind. Page errors empty. Headed runs report UA `Chrome/152.0.0.0`, headless `HeadlessChrome/152.0.0.0`, both Chromium 152.0.7977.42.

**Startup diagnostic** (`diagnose-80fbd61.json`, `diagnose-worklet.js` over `http://127.0.0.1:8765`): the bundle wrapped in try/catch inside the worklet scope reports `error: null`; unwrapped via data URL and blob URL, `addModule` resolves in 12 to 16 ms and `new AudioWorkletNode(ctx, "audioface")` constructs. At 95efc3b the same probe recorded `ReferenceError: TextEncoder is not defined`.

**Headed run 1 anomaly.** `result.json` (11:46:59 local) holds the pass and five rows. The screenshot command then took about 30 s, produced a black image (11:47:29), and the final `get text h1` read `running` (11:47:32), with one browser launch in `run.log`. The control layer re-navigated the page after extraction; nothing in the page or engine explains it. `headed-2` repeated the run end to end with a visible PASS table. Both directories are kept.

## Environment

macOS 26.5.2 (25F84), Apple M2 Max, 12 cores; Node v25.9.0, pnpm 10.17.1, agent-browser 0.36.0. Load averages 48 to 51 during the first runs, 8 at `headed-2`. Default output is now MacBook Pro Speakers; the realtime probe reads 44100 Hz, `baseLatency` 5.8 ms, `outputLatency` 0. Offline contexts render at 48000 Hz as the fixture declares. Worklet scope: quantum 128; `performance`, `setTimeout`, `SharedArrayBuffer` undefined.

## Clean tree

After all work: browser `80fbd61`, 0 changes, only ignored `apps/web/dist/`; main `10ba9fc`, composition `41699f4`, runtime `9204eaa`, integrated `795d803` all 0 changes. The only file touched under `browser-baseline/` is `summarize-results.mjs`, which gained an optional directory argument; no baseline artifact changed.

## Limitations

1. Load was uncontrolled; timings are wall clock context only.
2. Headed run 1 ended with a control layer re-navigation after the pass was extracted; `headed-2` is the clean headed proof.
3. Offline rendering only; no realtime callback ran the engine.
4. One browser build, Chrome for Testing 152.0.7977.42.
5. The default device differs from the baseline (built in speakers at 44.1 kHz versus Traktor S8 at 48 kHz), so realtime probe values are not comparable across reports.
6. The realm gate proves the listed globals absent and registration present; it does not emulate `AudioWorkletGlobalScope`, so browser replay remains the registration proof.
7. Traces were captured but not re-analysed.
