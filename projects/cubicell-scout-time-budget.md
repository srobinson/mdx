# Cubicell initial delivery time budget scout

Measured against `main` at `60da3f7d2fe43da0f3212dc9ee6b9b57d9f79323`.

## Result

The remaining time gap is work shaped.

Production preview contains exactly one main thread task above `100 ms` in
every run. Its traced median is `457.0 ms`. The task contains a `391.3 ms`
median browser `Commit` span and a `61.2 ms` median React Three Fiber frame
callback. The planned `32.60 KB` gzip deletion has `23.1 ms` of conservative
parse plus execute cost under the locked profile. Source mapped samples observe
only `4.0 ms` median in the broader matching panel and persistence families.

Deleting the planned bytes cannot split the terminal `457.0 ms` task because
those sources do not execute inside that task. The task is rooted in the
mandatory renderer.

The traced production committed frame median is `4557.1 ms`. Its gap to the
`3000 ms` ceiling is `1557.1 ms`.

## Production preview

### Reproducibility

Five fresh browser processes:

| Measurement | Runs, ms | Median, ms | Min to max, ms |
| --- | --- | ---: | ---: |
| First WebGL draw entry | `4098.0, 4106.0, 4083.6, 4118.8, 4104.8` | 4104.8 | 4083.6 to 4118.8 |
| Interactive canvas, committed frame | `4542.5, 4571.7, 4538.0, 4569.2, 4557.1` | 4557.1 | 4538.0 to 4571.7 |
| First draw to committed frame | `444.5, 465.7, 454.4, 450.4, 452.3` | 452.3 | 444.5 to 465.7 |
| Maximum observed long task | `448, 469, 456, 453, 457` | 456 | 448 to 469 |
| Traced tasks above 100 ms | `1, 1, 1, 1, 1` | 1 | 1 to 1 |

The trace duration for the terminal task has more precision than the Long Tasks
API. Its runs are `448.9, 469.5, 457.0, 454.0, 458.1 ms`, median `457.0 ms`,
range `448.9 to 469.5 ms`.

### Main thread tasks

Every task at or above `50 ms` before handoff falls into four stable classes.

| Task | Runs | Median, ms | Min to max, ms | Attribution | Phase |
| --- | ---: | ---: | ---: | --- | --- |
| React shell mount after hydration | 5 of 5 | 82.6 | 80.0 to 83.6 | `assets/index-BuQqFceC.js`; source map to `node_modules/react-dom/cjs/react-dom-client.production.js:performWorkOnRootViaSchedulerTask` | Hydration publish and shell mount |
| Initial document layout | 5 of 5 | 89.8 | 87.5 to 97.7 | Browser `Layout`; initiated after `assets/EditorStudio-CMmLFfSz.js`, source map near `src/app/useSnapSize.ts:useSnapSize` | Shell and scene construction |
| Renderer layer commit before the ready frame | 5 of 5 | 55.1 | 52.5 to 74.3 | Browser `Commit`, owned by `src/scene/CubeScene.tsx:CubeScene` through `assets/SharedRendererModule-CZpQTOtw.js` | Renderer and WebGL initialization |
| Initial ready frame task | 5 of 5 | 457.0 | 448.9 to 469.5 | `assets/SharedRendererModule-CZpQTOtw.js`; source map to `node_modules/@react-three/fiber/dist/events-b389eeca.esm.js:loop`, reached from `src/scene/CubeScene.tsx:CubeScene` | First frame commit |

Exactly one production task exceeds `100 ms`. The earlier work is a short
sequence rather than a long tail above the gate.

The terminal task breaks down as follows:

| Child span | Median, ms | Min to max, ms | Attribution |
| --- | ---: | ---: | --- |
| Browser `Commit` | 391.3 | 387.3 to 401.1 | DevTools layer tree commit with `frameSeqId` and `layerTreeId` |
| `FireAnimationFrame` | 61.2 | 57.9 to 64.5 | `node_modules/@react-three/fiber/dist/events-b389eeca.esm.js:loop` |
| Other task work | about 4 | about 2 to 6 | Task dispatch, style update, and trace bookkeeping |

The WebGL wrapper observed 12 initial draw submissions per run. Their native
call duration totaled `0.0 to 0.3 ms`. The large span sits around frame and
layer commit work. No source mapped panel or persistence function is the hot
owner.

The runtime ownership path is:

`src/scene/CubeScene.tsx:CubeScene` mounts the React Three Fiber `Canvas`.
`node_modules/@react-three/fiber/dist/events-b389eeca.esm.js:loop` drives the
ready frame. `node_modules/three/build/three.module.js:WebGLRenderer.render`
submits it. `src/renderer/RendererCommitDriver.tsx:RendererCommitDriver`
publishes the after effect. `src/app/AppBootstrap.tsx:AppBootstrap` records
`cubicell:interactive-canvas`.

### Phase breakdown

The total is the measured `4557.1 ms` committed frame median.

| Phase | Boundary | Median, ms | Min to max, ms | Fraction |
| --- | --- | ---: | ---: | ---: |
| HTML navigation | Navigation start through HTML response end | 583.6 | 577.6 to 584.9 | 12.80% |
| Module delivery | HTML response end through `src/studios/StudioHost.tsx:StudioHost` modules ready | 3120.5 | 3117.1 to 3127.7 | 68.47% |
| Script parse plus execute | CDP `ScriptDuration + V8CompileDuration` through handoff | 305.9 | 297.5 to 316.1 | 6.71% |
| Store hydration | First IndexedDB open through the final startup transaction event | 30.9 | 28.5 to 32.0 | 0.68% |
| Scene and shell construction | Ready modules and hydrated store through first draw, excluding renderer init | 249.9 | 244.6 to 260.0 | 5.48% |
| Renderer and WebGL init | First successful WebGL context request through `CubeScene` `onCreated` | 131.4 | 124.7 to 144.3 | 2.88% |
| First frame commit | First WebGL draw entry through `RendererCommitDriver` after effect | 452.3 | 444.5 to 465.7 | 9.93% |

Script CPU is an overlay within the wall clock phases. Hydration also occurs at
the tail of module delivery. Those two fractions are diagnostic and are not
additive with the wall spans.

The largest wall block is navigation plus module delivery at `3705.3 ms`,
`81.31%` of the traced total. The largest contiguous main thread block is the
terminal task at `457.0 ms`. Its largest child is browser `Commit` at
`391.3 ms`.

Phase boundaries use these live owners:

- Module readiness:
  `src/studios/StudioHost.tsx:StudioHost`
- IndexedDB startup:
  `src/persistence/indexedDbProjectStorage.ts:createIndexedDbProjectStorage`
  and `src/persistence/indexedDbProjectStorage.ts:openDatabase`
- Hydration publication:
  `src/state/projectDurability.ts:ProjectDurabilityRuntime.publishHydration`
- WebGL creation:
  `src/scene/CubeScene.tsx:CubeScene`
- Committed frame:
  `src/renderer/RendererCommitDriver.tsx:RendererCommitDriver`
- Interactive mark:
  `src/app/AppBootstrap.tsx:AppBootstrap`

## Transfer versus work

The current default interactive closure is exactly `430,773 B` gzip across
eight static chunks. `pnpm build:budget` and
`scripts/check-delivery-budget.mjs` both report that value at zero headroom.

The planned Slice 5 deletion is approximately:

- Non Motion panels and selectors: `29.46 KB` gzip
- Optional persistence and recovery: `3.14 KB` gzip
- Total: `32.60 KB` gzip

That total is `7.568%` of the current default interactive closure.

### Measured execution

The production CPU profiles were sampled every `500 microseconds` and mapped
through hidden source maps generated from byte identical JavaScript.

The broader source family match, all `src/panels/**` outside Motion plus all
`src/persistence/**`, consumed:

`1.6, 4.0, 4.9, 4.2, 3.5 ms`, median `4.0 ms`, range `1.6 to 4.9 ms`.

This match is broader than the named `32.60 KB` candidate and therefore does
not undercount by excluding another matching panel or persistence family.
Sampling can miss sub interval execution, so the byte proportional calculation
below is the conservative estimate.

Total startup script parse plus execute is `305.9 ms` median. Uniform cost per
gzip byte gives:

`305.9 ms × 32,600 B / 430,773 B = 23.1 ms`.

`23.1 ms` is the conservative parse plus execute estimate for deleting the
planned JavaScript entirely. It covers `1.49%` of the measured `1557.1 ms`
interactive gap.

### Transfer ceiling

At `1474.56 Kbps`, serial transfer of `32,600 B` takes `172.7 ms`.
The production chunks preload in parallel, so `172.7 ms` is an upper ceiling
for critical path transfer removal. The mandatory
`shared-renderer-core` chunk remains `187.35 KB` gzip and still anchors the
renderer path.

Even granting the full serialized transfer ceiling:

`23.1 ms parse and execute + 172.7 ms transfer = 195.9 ms`.

That absolute ceiling covers `12.58%` of the measured time gap and leaves
`1361.2 ms`. Actual critical path transfer saving is lower when the removed
bytes are parallel with the mandatory renderer chunk.

The byte deletion does not touch the terminal task attribution. The time gates
remain work shaped.

## Development versus preview

Development used the same profile. The Vite server was warmed once so server
transformation did not contaminate the five reported runs. Every reported run
still used a fresh browser process and empty browser context.

### Development reproducibility

| Measurement | Median, ms | Min to max, ms |
| --- | ---: | ---: |
| First WebGL draw entry | 152356.3 | 152234.8 to 152380.3 |
| Interactive canvas | 152833.1 | 152688.5 to 152867.1 |
| First draw to committed frame | 467.1 | 453.7 to 510.8 |
| Maximum Long Tasks API task | 461 | 452 to 506 |
| Traced tasks above 100 ms | 4 | 3 to 5 |

The development traced task counts are `4, 5, 3, 3, 4`.

| Task class | Above 100 ms | Duration evidence, ms | Script URL and symbol | Phase |
| --- | ---: | --- | --- | --- |
| Three streamed module compile | 2 of 5 | `103.3, 101.3`; other runs `95.4 to 97.3` | `/node_modules/.vite/deps/three.module-BU6RBvxS.js`; `v8.compileModule` | Module delivery |
| Drei streamed module compile task | 5 of 5 | median 168.3, range 162.0 to 174.1 | `/node_modules/.vite/deps/@react-three_drei.js`; `v8.compileModule` | Module delivery |
| React scheduler shell mount | 5 of 5 | median 150.3, range 147.4 to 153.6 | `/node_modules/.vite/deps/scheduler-CqIEFxql.js:performWorkUntilDeadline` | Shell mount |
| Initial layout | 2 of 5 | `104.2, 100.3`; other runs `90.6 to 96.8` | Browser `Layout` after React Three Fiber mount | Shell and scene construction |
| Initial ready frame task | 5 of 5 | median 462.8, range 452.9 to 507.1 | `/node_modules/.vite/deps/react-three-fiber.esm-DIWMWIjM.js:loop` | First frame commit |

Development phase medians:

| Phase | Median, ms | Min to max, ms | Fraction of 152833.1 ms |
| --- | ---: | ---: | ---: |
| HTML navigation | 582.3 | 577.3 to 585.4 | 0.38% |
| Module delivery | 151230.6 | 151130.5 to 151243.9 | 98.95% |
| Script parse plus execute | 1372.8 | 1341.0 to 1413.0 | 0.90% |
| Store hydration | 37.2 | 36.1 to 39.9 | 0.02% |
| Scene and shell construction | 374.5 | 365.2 to 387.1 | 0.25% |
| Renderer and WebGL init | 171.7 | 153.7 to 180.1 | 0.11% |
| First frame commit | 467.1 | 453.7 to 510.8 | 0.31% |

Development and preview disagree strongly in delivery shape. Development spends
about `151.8 s` reaching loaded modules under the locked latency profile, while
preview spends about `3.7 s`. They agree in terminal work shape: both end with
one React Three Fiber frame task whose largest child is browser `Commit`, and
both have a terminal task around `0.46 s`.

## Conditions

- Machine: Apple M2 Max, 12 CPU cores, 96 GB memory
- Operating system: macOS 26.5.2
- Load sampled after the runs: `3.62, 4.11, 4.40`
- Browser: headless Chromium `143.0.7499.4`
- Viewport: `1024 × 768`
- CPU: four times slowdown through CDP
- Network: `562.5 ms` latency, `1474.56 Kbps` down,
  `675 Kbps` up
- Browser profile: one fresh browser process and context per run
- HTTP cache: initially empty per fresh context, enabled during the single
  navigation so production preload behavior remains representative
- Service workers: blocked
- IndexedDB: fresh context, empty startup database
- Tracing: Playwright navigation with CDP DevTools timeline, V8, loading, and
  user timing categories
- CPU sampling: CDP profiler at `500 microseconds`
- Production server: `pnpm preview`
- Development server: `pnpm dev`, warmed once before the five measured runs

The profiler and trace add diagnostic overhead. The prior unprofiled locked
measurement is `4446.0 ms`; the traced median here is `4557.1 ms`. This report
does not treat that harness difference as a product delta.

## Method

The browser init hook recorded:

- Long Tasks API entries
- IndexedDB open and transaction events
- WebGL context creation
- WebGL draw entry, exit, count, and span
- Startup indicator phase changes
- App shell insertion
- `cubicell:interactive-canvas`
- Navigation and resource timing

CDP recorded:

- Main thread `RunTask` events
- Nested `FunctionCall`, `FireAnimationFrame`, `Layout`, and `Commit` events
- CPU profiles
- `ScriptDuration`, `V8CompileDuration`, and `TaskDuration`

Trace timestamps were aligned to page time with a
`console.timeStamp("cubicell-time-scout-anchor")` marker. Production call
frames were mapped through a later `vite build --sourcemap hidden`. JavaScript
SHA 256 hashes were identical before and after the hidden source map build.
Source maps were therefore used only for attribution and did not change the
measured assets.

## Raw commands

```text
pnpm build
pnpm preview --host 127.0.0.1 --port 44173 --strictPort
node ~/.mdx/TMP/cubicell-time-scout/capture.mjs preview http://127.0.0.1:44173 ~/.mdx/TMP/cubicell-time-scout/pilot 1
node ~/.mdx/TMP/cubicell-time-scout/capture.mjs preview http://127.0.0.1:44173 ~/.mdx/TMP/cubicell-time-scout/full 5

pnpm dev --host 127.0.0.1 --port 45173 --strictPort
node ~/.mdx/TMP/cubicell-time-scout/capture.mjs dev http://127.0.0.1:45173 ~/.mdx/TMP/cubicell-time-scout/pilot-dev 1
node ~/.mdx/TMP/cubicell-time-scout/capture.mjs dev http://127.0.0.1:45173 ~/.mdx/TMP/cubicell-time-scout/full 5

pnpm exec vite build --sourcemap hidden
node ~/.mdx/TMP/cubicell-time-scout/analyze.mjs \
  ~/.mdx/TMP/cubicell-time-scout/full \
  ./dist \
  ~/.mdx/TMP/cubicell-time-scout/summary.json

pnpm build:budget
node scripts/check-delivery-budget.mjs
git status --short --branch
git diff --check
```

## Artifacts

- Report:
  `~/.mdx/projects/cubicell-scout-time-budget.md`
- Capture harness:
  `~/.mdx/TMP/cubicell-time-scout/capture.mjs`
- Analysis harness:
  `~/.mdx/TMP/cubicell-time-scout/analyze.mjs`
- Aggregate JSON:
  `~/.mdx/TMP/cubicell-time-scout/summary.json`
- Five production traces and profiles:
  `~/.mdx/TMP/cubicell-time-scout/full/preview-run-*`
- Five development traces and profiles:
  `~/.mdx/TMP/cubicell-time-scout/full/dev-run-*`

## Verification

- `pnpm build`: passed
- `pnpm build:budget`: passed
- `node scripts/check-delivery-budget.mjs`: passed
- Playwright `pageerror` and failed request arrays across the ten reported
  runs: empty
- Development server console: one Three Clock deprecation warning and one
  `ResizeObserver loop completed with undelivered notifications` message per
  measured navigation
- Source map JavaScript hash comparison: identical
- Repository `git diff --check`: passed
- Repository baseline after measurement: branch
  `docs/performance-audit`, tracked tree clean
