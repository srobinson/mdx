---
title: Audioface foundations browser baseline
type: projects
tags: [audioface, foundations, browser, web-audio, measurement, null-test]
summary: The built null test page at 95efc3b fails in a real Chrome because the composition unit's digest module constructs a TextEncoder at worklet module top level; main's build passes 5 of 5 in the same browser, and a reusable measurement path is recorded.
status: draft
project: audioface
related: [audioface-foundations-integration, audioface-foundations-composition-build, audioface-foundations-runtime-prerequisites-build, audioface-foundation-runtime-probes-spec]
confidence: high
---

# Audioface foundations browser baseline

Frozen checkout `/Users/alphab/.mdx/TMP/pstack/audioface-foundations/worktrees/browser`, branch `probe/foundation-browser`, HEAD `95efc3bd51c572a8396c7a6573b67322d8803431`. No tracked file was changed in any checkout. Every artifact, script and log lives in `/Users/alphab/.mdx/TMP/pstack/audioface-foundations/browser-baseline/` (machine readable roll up in `summary.json`).

## Verdict

**The 95efc3b null test page does not run.** Its `h1` carries `data-verdict="error"` and reads: `Failed to construct 'AudioWorkletNode': AudioWorkletNode cannot be created: The node name 'audioface' is not defined in AudioWorkletGlobalScope.` No event row is produced. The result is identical headless, headed, with and without user activation, and in a control session with no instrumentation script (`control-verdict.txt`).

**Main's page passes.** The tree at `10ba9fc` was exported with `git archive` into the scratchpad, installed offline from the frozen lockfile and built. Its null test page (`sha256 3d2fcca2…`) reports `data-verdict="pass"`, `Null test audioface.skirmish PASS 5 events`, all five rows (gun-ar, reload-magout, step-dirt, hitmarker, ambience-wind) at 96000 frames, difference 0, tail 0, headless and headed. Screenshots: `main-10ba9fc-headed/null-test.png`, `headed/null-test.png`.

So the merge at 95efc3b carries a browser regression that no Node gate sees.

## Root cause, proven in the worklet scope

`packages/contract/src/digest.ts:54` holds `const UTF8 = new TextEncoder();` at module top level. The contract barrel re-exports it (`packages/contract/src/index.ts:8`), and the worklet bundle pulls the whole barrel through control, so the statement runs when the AudioWorklet module is evaluated. Chromium exposes `TextEncoder` to `Window, Worker, SharedStorageWorklet, ShadowRealm` only, with an open TODO to make it `Exposed=*` ([text_encoder.idl](https://chromium.googlesource.com/chromium/src/+/main/third_party/blink/renderer/modules/encoding/text_encoder.idl)); `AudioWorkletGlobalScope` is not in that list ([audio_worklet_global_scope.idl](https://chromium.googlesource.com/chromium/src/+/main/third_party/blink/renderer/modules/webaudio/audio_worklet_global_scope.idl)).

Evidence chain:

- `extract-worklet.mjs` recovers the inlined worklet bundle from each built page (`worklet-95efc3b.js`, 676,183 chars; `worklet-10ba9fc.js`, 656,719 chars).
- In Node under a stub of only the worklet globals, main's bundle registers `audioface`; the 95efc3b bundle throws `ReferenceError: TextEncoder is not defined` at line 258, the digest module.
- In Chrome, `diagnose-worklet.js` wraps the bundle in a try/catch inside the worklet scope: `diagnose-95efc3b.json` records `ReferenceError: TextEncoder is not defined at …:260:14`; `diagnose-10ba9fc.json` records `error: null` and `audioface` registered. Data URL and blob URL behave the same, so size and scheme are not factors.
- `git grep` places `new TextEncoder` in `41699f4` (composition, first at `3455fb3`) and in neither `9204eaa` nor `10ba9fc`.

Chrome resolves `addModule` even though the module threw, and nothing reaches the page console (`console.txt`, `errors.txt` empty). The HTML worklets algorithm says to reject with the script's error to rethrow ([worklets](https://html.spec.whatwg.org/multipage/worklets.html)); observed Chrome 152 does not, so a resolved install proves nothing about registration. The Node null test twin runs on Node globals, where `TextEncoder` exists, which is why 335 tests pass. Fix direction is the lead's call: a lazily constructed encoder inside `sha256Hex`, or keeping digest out of the worklet bundle. A cheap Node gate that evaluates the built worklet bundle in a `vm` context holding only worklet globals and asserts the registration would have caught this; not added here.

## Environment

| Item | Value |
|---|---|
| Code | `95efc3bd51c572a8396c7a6573b67322d8803431`; `null-test.html` sha256 `6bd4c59c…`, `index.html` `1644f061…` (`dist-sha256.txt`) |
| Build | `pnpm --filter @audioface/app-web build` exit 0 (`build-95efc3b.log`), frozen lockfile install by the lead (`browser-install.log`) |
| Node / pnpm | v25.9.0 / 10.17.1 |
| OS / CPU | macOS 26.5.2 (25F84), Apple M2 Max, 12 cores, 96 GiB, arm64 |
| Browser | Chrome for Testing 152.0.7977.42 launched by agent-browser 0.36.0 over CDP, private sessions `audioface-baseline-*`; the user's Chrome 152.0.7977.82 and its tabs were not used |
| Modes | headless (UA `HeadlessChrome/152.0.0.0`) and headed, both run |
| Audio device | default output Native Instruments Traktor Kontrol S8, USB, 48 kHz, 4 out; Traktor Pro 4 held it concurrently; built in speakers at 44.1 kHz also present |
| Load | 1 minute load averages 487 to 690 on 12 cores throughout (a VM, VS Code, other agents building). Not a quiescent machine. |

## Measurements

Wall time is main thread `performance.now()` from `capture-init.js`, which wraps the Web Audio constructors, `addModule` and `startRendering` before page code runs. It measures nothing on the rendering thread.

| Metric | 10ba9fc (pass) | 95efc3b (error) |
|---|---|---|
| Page open to verdict | 2.90 to 2.91 s | 0.75 to 0.87 s |
| Worklet install, first `addModule` (1.13 M char data URL) | 126 to 131 ms | 135 to 260 ms (resolves, nothing registered) |
| Worklet install, later contexts | 28 to 62 ms | n/a |
| `v8.compileModule` (trace), main thread / worklet thread | 25 to 27 ms / 17.5 to 21.5 ms | 26 to 27 ms / 16.7 to 35.3 ms |
| Offline render, 96000 frames, per event | 323 to 502 ms (4 to 6 times faster than real time) | none |

Realtime `AudioContext` probe (`extract.js`), both builds, both modes: sampleRate 48000, `baseLatency` 0.005333 s (256 frames), `outputLatency` 0 before and after resume, `sinkId` empty (default device), `renderCapacity` undefined. Without user activation the context is created `suspended` and `resume()` did not settle within 2 s (`headless-no-activation/`), as Chrome's autoplay policy describes ([autoplay](https://developer.chrome.com/blog/autoplay)); after one real CDP click the context constructs `running` in headed and headless mode.

Worklet scope probe: render quantum 128 frames, the spec default ([Web Audio 1.1](https://www.w3.org/TR/webaudio-1.1/)); `performance`, `setTimeout` and `SharedArrayBuffer` undefined (`crossOriginIsolated` false from `file://`); `Atomics`, `WebAssembly`, `console` present.

## What the tools genuinely expose

`agent-browser profiler start --categories …disabled-by-default-webaudio.audionode…` yields a Chrome trace (`profile.json`) with a named `Offline AudioWorklet thread` carrying `AudioWorkletHandler::Process` slices per render quantum, `v8.compileModule` on both threads and V8 GC events on the worklet thread (100 to 103 in the passing runs). This is the only genuine per callback duration source; page JS cannot see it.

Completeness gap: the passing runs captured 57 and 76 `Process` slices spanning 85 to 109 ms out of 3750 quanta rendered. Captured durations: min 306 µs, median 437 to 557 µs, max 27 to 45 ms (the first quantum, warmup) against a 2.667 ms quantum at 48 kHz. Under offline rendering there is no deadline, and the machine was loaded, so these are not callback statistics. The trace buffer or thread flush behaviour must be fixed before the next probe relies on it.

Metric by metric: wall time obtained; callback duration trace only and partial; scheduled frame error not obtained (needs worklet side logging of command frame versus `currentFrame`); reported device latency `baseLatency` only, `outputLatency` read 0; sample continuity proven offline by the null test (difference 0) and not measured in real time (needs an in worklet continuity counter or device loopback).

## Reproducible path

```
browser-baseline/run-null-test.sh headless|headed [pack]   # build page, verdict, rows, console, screenshot, trace, result.json
DIST=<page> OUT=<dir> browser-baseline/run-null-test.sh …   # any built page, any output directory
node browser-baseline/summarize-results.mjs                 # summary.json
node browser-baseline/extract-worklet.mjs <page> <out.js>   # bundle for worklet scope diagnosis
browser-baseline/diagnose-worklet.js                        # eval on an http served page
```

## Smallest next browser experiments (not built)

- **Independent moving outputs**: offline, two emitters into separate spatial paths; capture each pre sum output through its own `AudioWorkletNode` output and assert B's capture is unchanged while A moves or mutes.
- **Stalled UI**: realtime context, a 500 ms main thread busy loop; an in worklet continuity counter (missing today) reports gaps in `currentFrame`.
- **Bounded overload**: double voice demand until the host refuses; read `Process` durations from a trace once completeness is fixed.
- **JS versus native matched input**: offline, identical precomputed mono input into JS placement and `StereoPannerNode`, maximum absolute error 1e-6 per the probe spec.

## Limitations

1. The 95efc3b page yields no row; the baseline for the reviewed host comes from main's build.
2. Load averages 487 to 690 on 12 cores; nothing here characterises performance.
3. Trace per quantum coverage is 1.5 to 2 percent of rendered quanta.
4. `outputLatency` read 0 in every mode; device latency is unmeasured.
5. Headless audio device identity is not observable from the page.
6. Offline rendering only; no realtime callback ran the engine.
7. No scheduled frame error or realtime continuity instrumentation exists in the fixture.
8. A resolved `addModule` does not prove registration in Chrome 152.
9. Chrome for Testing 152.0.7977.42, not the user's Chrome build or any other browser; no coverage claimed elsewhere.

Checkouts after the work: browser worktree clean at 95efc3b, main clean at 10ba9fc, composition at 41699f4 and runtime at 9204eaa clean. Nothing under `apps/web/dist` is tracked.
