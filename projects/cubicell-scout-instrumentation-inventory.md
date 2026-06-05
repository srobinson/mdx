# Cubicell measurement inventory

Static inspection covered clean `main` at `71098b4ee211`. No build, test, server, or
browser was run.

## Inventory

### Invocation and CI surface

| Capability | Invocation | Gate status | Threshold owner |
| --- | --- | --- | --- |
| Unit and DOM tests | `pnpm test` | Local. No workflow runs it. | Assertions in `tests/**`; `package.json:scripts.test` |
| Real Chromium tests | `pnpm test:browser` | Local. No workflow runs it. | Assertions in `*.browser.test.ts`; `package.json:scripts.test:browser` |
| All Vitest projects | `pnpm test:all` | Local. No workflow runs it. | Vitest project routing in `vite.config.ts:test.projects` |
| Scene morph benchmark | `pnpm bench:scene-morph` | Manual diagnostic. No pass threshold. | Workload and 120 samples in `tests/sceneMorph.bench.ts:scene morph performance` |
| Static delivery budget | `pnpm check:budget` | Pull request CI gate. | `budgets/initial-delivery.json`; `scripts/check-delivery-budget.mjs:main` |
| Cold startup timing | Run `pnpm build:budget`, then `pnpm measure:initial-delivery` | Manual measurement. It writes an artifact and does not fail on the three performance target booleans. | Profile and 3.0 second target in `budgets/initial-delivery.json:browserBaseline`; 2.5 second LCP and 100 ms task targets in `scripts/measure-initial-delivery.mjs:main` |

The only checked in workflow is
`.github/workflows/delivery-budget.yml:jobs.check`. It runs `pnpm check:budget`
on pull requests. No workflow runs Vitest, Playwright, the scene morph
benchmark, or cold startup timing.

### `PERFORMANCE.md` acceptance gates

| Area | Existing producer | What is enforced |
| --- | --- | --- |
| P0 persistence integrity | `tests/cubicellStore.browser.test.ts:largeStoreRestartTest`, using `tests/cubicellStoreBrowserDriver.ts:seedLargeStore`; quota and recovery scenarios live in `tests/cubicellStore.browser.test.ts:authoredDurabilityTests` and `tests/indexedDbStorage.browser.test.ts:describe IndexedDB Project storage in real Chromium` | The 4,500 cube dispatch must complete within 50 ms. If Long Task observation is supported, its maximum must also be at most 50 ms. Exact offline restart, lazy asset reads, failure state, quota recovery, and record integrity are functional assertions. These are local browser gates. |
| P0 incremental authored scene | `tests/incrementalScene.browser.test.ts:test uses no full sync for one authored face edit at 250 and 2025 cells`, using `tests/incrementalSceneBrowserDriver.tsx:runIncrementalSceneBrowserGate` | Exact deterministic counts are enforced at 250 and 2,025 cells: zero full syncs, two patch calls, five affected cells, one edited cell, zero occupancy rebuilds, 156 uploaded bytes, exact dirty ranges, and equality with a full rebuild. `elapsedMs` is reported by the driver and never asserted. |
| P1 GPU capacity and material lifetime | `tests/incrementalScene.browser.test.ts:test keeps live GPU resources flat across capacity bands and reuse cycles`, using `tests/incrementalSceneBrowserDriver.tsx:runGpuCapacityBrowserGate` and `tests/webGlResourceObserver.ts:observeWebGlResources` | Within band growth must create no resources. A band crossing must create and delete buffers, create no shader program, retain mesh and material identities, and return to the baseline live resource count. Three reuse cycles must add no resources. |
| P1 demand rendering | `tests/demandRendering.browser.test.ts:test stops fully idle and wakes every continuous producer`, using `tests/demandRenderingBrowserDriver.tsx:runDemandRenderingBrowserGate` and `tests/rendererDrawObserver.ts:observeRendererDraws` | The settled renderer must issue zero draws during three seconds. Eleven named producers must wake rendering and return to zero idle draws. Playback must produce samples and stop at its terminal time. The 2,025 cell transition reports five frame deltas and a p95 greater than zero. Camera continuity is represented by positive draw counts. This does not measure camera frame pacing or prove an absolute timing budget. |
| P1 camera allocation churn | `tests/interaction.viewLane.test.ts:test reuses storage without carrying values between repeated command kinds`, `tests/interaction.core.test.ts:test writes eased frames into a caller-owned pose`, `tests/interaction.authority.test.ts:test keeps retained eased frame samples independent`, plus source ownership in `src/camera/cameraFrameWriter.ts:useSingleCameraWriterFrame` | Object identity, caller owned destination reuse, retained value independence, and clean repeated orbit, translate, and zoom scratch are enforced by unit tests and TypeScript. No heap, allocation volume, frame pacing, or GC threshold exists. `PERFORMANCE.md:## P1. Camera frame allocation churn` states this accurately. |
| P1 playback plan and shell scope | `tests/appPlaybackBoundary.test.tsx:test transport ticks commit only the staged canvas and capped playhead`, `tests/playbackFrame.browser.test.ts:test uses one render clock with exact playback semantics at 2025 cells`, and `tests/playbackFrameBrowserDriver.tsx:runPlaybackFrameBrowserGate` | One plan preparation, exact loop, scrub and terminal semantics, no transport owned animation frame, no transport frames after pause, no Studio shell render, and a capped playhead publication count are enforced. The driver calculates p95 from 20 renderer frame deltas. The test asserts only `p95FrameMs > 0`. The documented p95 limit of 16.7 ms is not enforced. |
| P1 recording lifetime | `tests/streamRecorder.test.ts:describe recording memory bound and residue`, `tests/streamRecorder.test.ts:describe recording terminal ownership`, and `tests/recordingLifetime.browser.test.ts:test shows a legible budget and leaves no residue across cycles` | Retained chunks are bounded by `src/export/recordingConfig.ts:RECORDING_MAX_RETAINED_BYTES`, currently 256 MiB. Unit tests enforce the cap and cleanup for stop, error, track end, unmount, and repeated cycles. The browser test proves the real capability path can start and stop twice without page errors. Heap residency is inferred from retained byte accounting. Browser heap use is not measured. |
| P1 initial delivery | `scripts/check-delivery-budget.mjs:main`, `scripts/delivery-capabilities.mjs:checkCapabilityIncrements`, and `budgets/initial-delivery.json` | Static JavaScript and CSS closure bytes, chunk counts, capability increments, route preloads, cold ownership, cross Studio imports, and renderer ownership are pull request gates. Current limits live in JSON, including editor JavaScript at 368,972 gzip bytes. The document's 350 KB editor target is therefore not the current executable limit. |
| P1 cold startup | `scripts/measure-initial-delivery.mjs:measurementBootstrap`, `scripts/measure-initial-delivery.mjs:collectRun`, and `scripts/measure-initial-delivery.mjs:main` | Three runs measure first WebGL draw entry, committed canvas mark, LCP, Long Tasks, transfer progress, resource timing, draw duration, and input wake. The script records booleans for committed frame at most 3,000 ms, startup indicator LCP at most 2,500 ms, and maximum Long Task at most 100 ms. Its failure list checks measurement validity, preload behavior, LCP element identity, and input wake. It does not fail when those three timing booleans are false. This is a manual tool. |

The historical browser table in `PERFORMANCE.md:## Scope and evidence` records
120 fps, p95 edit timings, persistence timing, DOM size, bundle size, LCP, and
estimated TBT from the original audit. Most values have no current executable
producer. The cold startup script reproduces the startup class of measurement.
The incremental browser driver replaces wall clock edit timing with deterministic
work counts and keeps elapsed time diagnostic.

### Browser drivers and observers

- `tests/playbackFrameBrowserDriver.tsx:runPlaybackFrameBrowserGate` mounts the
  production Editor Studio renderer on the blank browser page, drives 2,025 cell
  playback, observes `TransportFrameObservation.deltaMs`, and calculates p95 over
  20 samples.
- `tests/demandRenderingBrowserDriver.tsx:runDemandRenderingBrowserGate` uses the
  same production tree. It counts WebGL draw activity for playback, recording,
  eased camera, held camera, trackball, scrub, authored edit, panel drag, resize,
  DPR, and projection producers. Its transition diagnostic calculates p95 over
  five playback samples.
- `tests/demandRenderingBrowserDriver.tsx:runHeldCameraGlide` already drives a
  keyboard hold through the production input path. Its current Shift plus Right
  scenario exercises camera travel and records draw liveness only.
- `tests/incrementalSceneBrowserDriver.tsx:runIncrementalSceneBrowserGate`
  measures elapsed edit time for reporting and collects exact render work,
  dirty ranges, uploaded bytes, mesh mutations, and equality with a full rebuild.
- `tests/incrementalSceneBrowserDriver.tsx:runGpuCapacityBrowserGate` and
  `tests/webGlResourceObserver.ts:observeWebGlResources` count WebGL buffer and
  program creation, deletion, and live resources.
- `tests/cubicellStoreBrowserDriver.ts:seedLargeStore` measures synchronous
  dispatch duration. `tests/cubicellStoreBrowserDriver.ts:observeLongTasks`
  records Long Task entries during the large persistence scenario.
- `tests/thumbnailCapabilityBrowserDriver.tsx:runThumbnailLifecycleBrowserGate`
  uses the WebGL resource observer to verify bounded thumbnail resources and
  cleanup. It does not measure frame time.
- `tests/indexedDbBrowserLifecycle.ts:registerIndexedDbBrowserLifecycle` is the
  shared sanctioned path. It loads `tests/browserBlank.html`, installs one
  driver, and invokes exported driver functions. The browser tests create their
  Vite server through `tests/viteTestServer.mjs:createBrowserTestServer`.

### Other timing and work counters in `tests/`

- `tests/sceneMorph.bench.ts:scene morph performance` benchmarks plan preparation
  and 120 scene samples plus grid layout for a 1,000 cell fixture. Vitest reports
  timing statistics. There is no threshold.
- `tests/projectRecordCodecs.test.ts:test round trips an exact 4,500 cube
  Structure and records bytes and duration` and
  `tests/recordCodecMetrics.ts:measureRecord` report encode duration and bytes.
  They assert shape, round trip correctness, and positive bytes. They do not
  assert duration.
- `tests/selectionEditPerformance.test.ts:test indexes selected parts once
  instead of scanning them for every cube` counts exactly 250 selection member
  reads.
- `tests/sceneOperationMaterialization.test.ts:test keeps member reads and scene
  remaps linear on a large edit` caps member reads at eight times selection size
  and cell reads at four times scene size.
- `tests/selectionQuery.test.ts:test stops once a replacement adds a new member`
  and `tests/selectionQuery.test.ts:test many spatial branches build one scene
  index` count scene cell reads.
- `tests/neighbors.test.ts:test resolves 250 face targets with one scene member
  pass` observes indexed scene reads.
- `tests/incrementalRenderPipelineBound.test.ts:test keeps full classify and
  update local at $size cells`,
  `tests/incrementalCubeRenderResolution.test.ts:describe incremental cube
  render resolution bounds`, and
  `tests/incrementalCubeSceneOwner.test.ts:test patches a contiguous authored
  edit to the same result as a full rebuild` cap impacted or rederived cells at
  11.
- `tests/appPlaybackBoundary.test.tsx:test transport ticks commit only the staged
  canvas and capped playhead` counts React commits, child renders, and playhead
  writes.
- `tests/structureSectionWindowing.test.tsx:describe slice viewport window`
  asserts bounded mounted rows, columns, or layers for 250 item surfaces.
- `tests/rendererDrawObserver.ts:observeRendererDraws`,
  `src/scene/instancedPartMeshCore.ts:observeInstancedPartMeshMutations`,
  `src/transport/activeTransitionPlan.ts:observeActiveTransitionPlanPreparations`,
  and `src/transport/transportFrameObservation.ts:observeTransportFrames` are
  reusable event or count seams used by the gates above.

### Instrumentation inside `src/`

- `src/app/AppBootstrap.tsx:AppBootstrap` emits the sole Performance Timeline
  mark, `cubicell:interactive-canvas`, when the renderer lifecycle hands off.
- `src/transport/transportFrameObservation.ts:publishTransportFrame` publishes
  playback frame delta and result data to in process observers.
- `src/transport/activeTransitionPlan.ts:observeActiveTransitionPlanPreparations`
  exposes plan preparation counts.
- `src/scene/instancedPartMeshCore.ts:observeInstancedPartMeshMutations` exposes
  mesh writes and capacity events.
- `src/scene/incrementalCubeSceneOwner.ts:CubeSceneRenderMetrics` reports accepted
  operation, affected cell, edited cell, and occupancy rebuild counts.
- Other `performance.now()` calls in `src/` provide motion clocks, input
  timestamps, or playhead publication cadence. They do not retain measurements.
- No `PerformanceObserver`, heap API, GC observer, profiler, trace integration,
  or frame timing distribution exists in `src/`.

## The Gap

| Question | Honest status |
| --- | --- |
| Sustained per frame pacing | Nearly covered for playback. `runPlaybackFrameBrowserGate` samples the production R3F frame delta and calculates p95, so the basic clock and percentile mechanism exist. Its 20 samples are short, the result discards the distribution, and the assertion accepts every positive value. `runTransitionDiagnostic` uses only five samples. Camera motion has no frame delta sampler. |
| Rare nondeterministic hitch | Uncovered. A p95 can hide the slowest five percent by design. With 20 samples, one isolated worst frame is excluded by the current percentile implementation. Neither driver returns maximum frame time, p99, long frame counts, or raw samples. The held camera path records draw liveness only. |
| Allocation volume or GC pressure | Uncovered. Camera identity tests prove reuse and prevent specific allocating wrappers from returning to the production path. That is strong structural evidence. It cannot state bytes allocated, collection frequency, pause duration, or retained heap. The WebGL resource observer counts GPU object lifecycle, a separate concern. |
| Attribution to code | Uncovered. The persistence and startup Long Task observers identify start time and duration only. No call stack, user timing span, task attribution, heap sample, or trace connects a long frame to camera resolution, rendering, persistence, or GC. |

The audit claim that nothing measures frame pacing is too broad. Playback already
measures a short frame delta distribution and computes p95. The accurate claim is
that no executable threshold protects the documented 16.7 ms playback budget,
no camera scenario samples frame deltas, and no existing result preserves rare
outliers.

## Hitch Experiment

### Smallest repeatable experiment

Extend `tests/demandRenderingBrowserDriver.tsx`. This keeps the existing blank
page lifecycle, production Editor Studio renderer, real keyboard adapter, demand
render scheduler, and WebGL draw observer. It requires no new browser harness.

1. Mount the existing 3 by 3 by 1 demand fixture in Perspective and wait for
   renderer idle through `createDemandHarness` and `waitForRendererIdle`.
2. Warm the lazy camera motion path once before measurement. This excludes the
   deterministic first capability load from the reported random steady state
   symptom.
3. Focus the canvas. Alternate a held `Equal` key and held `Minus` key, two
   seconds each, with immediate key release between directions. The key map
   resolves these to zoom in and zoom out through
   `src/editor/keyboard/keymap.ts:getKeyboardShortcutCommandId`.
   `src/interaction/commands/view.commands.ts:viewRepeat` promotes zoom to a
   sustained hold, and
   `src/interaction/commands/view.commands.ts:resolveZoomForProjection` resolves
   it to a Perspective dolly. Alternating direction avoids parking at a zoom
   bound.
4. Use a driver local `requestAnimationFrame` sampling loop to retain each
   successive callback delta while the key is held. Use
   `observeRendererDraws` to reject a run where demand rendering did not remain
   active. Discard visibility changes and the first two samples around each key
   transition.
5. Return raw deltas plus p50, p95, p99, maximum, and counts at or above 33.4 ms
   and 50 ms. Consolidate the two existing private `percentile95` copies into one
   test helper before adding a third consumer.

Collect 3,000 valid active motion samples. At 60 Hz this is about 50 seconds. If
a hitch has independent probability 0.1 percent per frame, 2,995 samples give a
95 percent chance of seeing at least one:

`ceil(log(0.05) / log(1 - 0.001)) = 2,995`.

For a 0.01 percent per frame event, the equivalent requirement is 29,956
samples, about 8 minutes 20 seconds at 60 Hz. A report of "rarer than once per
thousand frames" therefore requires the longer manual run. Independence is an
approximation, so the artifact must state sample count and duration rather than
claim universal absence.

### Pass, fail, and interpretation

- Scenario validity: the page remains visible, every active sample window
  contains production renderer activity, both key directions complete, and the
  final camera pose remains finite.
- Sustained budget pass on the reference machine: p95 is at most 16.7 ms, using
  the budget already stated in `PERFORMANCE.md`.
- Hitch pass: zero active motion deltas at or above 50 ms across 3,000 valid
  samples.
- Hitch fail: at least one active motion delta at or above 50 ms. This represents
  roughly three missed 60 Hz frame intervals and matches the Long Task boundary
  already used elsewhere in the repository.
- Environment invalid: a matched idle control also produces 50 ms outliers or
  the browser loses visibility. Repeat the run before assigning the stall to
  camera motion.

Zero hitches in 3,000 samples refutes an incidence of 0.1 percent per frame or
higher at approximately 95 percent confidence. It cannot prove that no hitch
exists.

This should be an opt in manual diagnostic, never a general CI gate. If it
reproduces the stall, frame times alone cannot attribute the cause. A single
DevTools Performance or CDP trace with allocation and GC detail would then be
the next investigation step. That exceeds the existing driver setup and needs
the owner's explicit approval.

## Reuse Map

| Needed capability | Existing owner | Reuse decision |
| --- | --- | --- |
| Drive a production browser scenario | `tests/indexedDbBrowserLifecycle.ts:registerIndexedDbBrowserLifecycle`, `tests/browserBlank.html`, `tests/viteTestServer.mjs:createBrowserTestServer`, and `tests/editorStudioTestSupport.tsx:EditorStudioTestRoot` | Reuse unchanged. |
| Drive keyboard camera holds | `tests/demandRenderingBrowserDriver.tsx:dispatchKey`, `tests/demandRenderingBrowserDriver.tsx:runHeldCameraGlide` | Reuse the same event path. Replace the scenario keys with alternating Equal and Minus for the diagnostic. |
| Prove demand rendering stayed active | `tests/rendererDrawObserver.ts:observeRendererDraws` | Reuse unchanged. |
| Collect playback frame deltas | `src/transport/transportFrameObservation.ts:observeTransportFrames` | Reuse for playback. It publishes only when transport advances, so it cannot observe camera only frames. |
| Collect camera frame deltas | None found | Add driver local animation frame sampling. Keep it in tests. |
| Aggregate percentiles | Private `percentile95` in both `tests/playbackFrameBrowserDriver.tsx` and `tests/demandRenderingBrowserDriver.tsx` | No shared owner exists. Extract one small test helper, migrate both callers, then add p50, p95, p99, maximum, and long frame counts. |
| Compare with a frame threshold | Vitest assertions provide the failure mechanism. `PERFORMANCE.md:## P1. Playback derivation and subscription scope` owns 16.7 ms. | Use 16.7 ms p95 and 50 ms outlier thresholds only in the opt in reference machine diagnostic. |
| Report a failure | Existing browser tests use returned result objects, `console.info`, and Vitest assertions. `scripts/measure-initial-delivery.mjs:main` also shows a JSON artifact pattern. | Return and print one compact result. An artifact is optional and unnecessary for the first slice. |
| Run in CI | `.github/workflows/delivery-budget.yml:jobs.check` owns static delivery CI. | No frame timing CI owner exists. Do not add the diagnostic to CI. |
| Measure allocation or GC | None found | Exclude from the first slice. A browser trace is a later, approval bound investigation after a reproduced hitch. |
| Attribute a long frame | None found | Exclude from the first slice. |

Exact repository searches used for the negative findings:

```text
rg -n --glob 'src/**' 'PerformanceObserver|performance\.(mark|measure|getEntries|clearMarks|clearMeasures)|measureUserAgentSpecificMemory|performance\.memory|HeapProfiler|Runtime\.getHeapUsage|Tracing\.start|FinalizationRegistry|--trace-gc|\bgc\('
rg -n --glob 'tests/**' --glob 'scripts/**' 'percentile|quantile|p95|PerformanceObserver|performance\.memory|measureUserAgentSpecificMemory|HeapProfiler|Runtime\.getHeapUsage|Tracing\.start|--trace-gc|\bgc\('
rg -n --hidden 'check:budget|test:browser|test:all|vitest|playwright|bench|perf|measure|pnpm test' .github/workflows package.json
rg --files tests | rg -i '(playback|demand|performance|perf|budget|frame|render|browser|camera|timing|count|resource|observer|startup|delivery)'
rg -n --glob 'tests/**' --glob 'src/**' --glob 'scripts/**' 'performance\.(now|mark|measure|getEntries)|PerformanceObserver|requestAnimationFrame|p95|percentile|longtask|durationMs|elapsedMs|frameMs|drawCalls|uploadedBytes|allocation|garbage|\bGC\b'
```

## CI Viability

Machine variance is handled only for the manual initial delivery measurement.
`budgets/initial-delivery.json:browserBaseline` pins Chromium
`143.0.7499.4`, network latency and throughput, and four times CPU slowdown.
`scripts/measure-initial-delivery.mjs:main` requires that browser version and
reports the median and range of three fresh context runs. The host CPU and GPU
remain outside the lock, and the performance target booleans do not control its
exit code.

The browser acceptance tests use whichever local Chromium Playwright supplies.
They have no hardware profile, warmup policy shared across tests, baseline
normalization, or CI runner. The existing frame timing assertions avoid flakes
by asserting only that p95 is positive. The 50 ms persistence browser assertion
is a local threshold with the same host variance.

The static delivery gate is viable in CI because it compares deterministic
build graph ownership, chunk counts, and exact gzip bytes against checked in
limits on one named runner class. Frame pacing depends on scheduler load,
display cadence, browser, CPU, GPU, and thermal state. An absolute camera frame
threshold on the current pull request runners would be disabled quickly.

Keep the camera experiment manual and tied to the reference machine. Unit test
the percentile and outlier aggregation with fixed synthetic deltas. CI can
protect the calculation and scenario wiring without judging real wall clock
performance.

## Do Not Build

- No production telemetry service, metrics registry, upload endpoint, dashboard,
  session store, or persisted trace format.
- No new Playwright harness, development server, preview server, or browser
  control path. Use the existing blank page driver lifecycle.
- No in product FPS overlay, profiler panel, performance HUD, or debug settings
  surface.
- No general heap profiler, allocation tracker, GC observer abstraction, or CDP
  tracing library in the repository.
- No CI frame timing gate on shared runners.
- No percentile dependency. The existing calculation is four lines and should
  become one shared test helper.
- No instrumentation throughout camera, interaction, renderer, and scheduler
  layers before a long frame has been reproduced.
- No recursive composition benchmark before recursive composition exists. The
  measurement shape can accept that workload later.

## Plan

1. Extract the duplicated frame summary logic from the playback and demand
   drivers into one small test helper. Preserve current p95 behavior, then add
   p50, p99, maximum, and 33.4 ms and 50 ms outlier counts. Add deterministic
   unit tests for aggregation.
2. Add one opt in diagnostic export to
   `tests/demandRenderingBrowserDriver.tsx`. Reuse `createDemandHarness`,
   `dispatchKey`, `waitForRendererIdle`, and `observeRendererDraws`. Drive the
   warmed alternating Equal and Minus hold scenario and collect 3,000 active
   animation frame deltas.
3. Add one opt in browser test entry that prints the compact result and enforces
   the reference machine thresholds. Normal `pnpm test:browser` should skip it.
   Provide one explicit manual command. Do not add a workflow.
4. Run one controlled red proof against the aggregation or threshold, restore
   it, then run the focused unit test and the manual browser diagnostic on the
   approved reference machine. A source only implementation cannot close the
   owner reported hitch.
5. If the timing diagnostic reproduces a 50 ms frame, request approval for one
   trace based attribution session. Keep allocation and GC work out of the
   repository until that evidence requires it.

### Recursion readiness

The proposed result shape is workload independent: raw frame deltas, summary
percentiles, outlier counts, scenario metadata, and renderer activity. When
recursive composition lands, the existing demand driver can mount a nested grid
fixture and run playback or camera motion through the same collector. Only the
fixture factory and metadata change. The collector does not need redesign.
Attribution and allocation remain separate manual investigation concerns.
