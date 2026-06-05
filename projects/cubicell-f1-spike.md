# Cubicell F1 video and shader render strategy spike

Measured 2026-08-09 from `main` commit `3725921ae23cd4088b3891b310889c8861ca05eb` in the isolated `f1-spike` worktree. The harness uses Three `0.185.1`, headless Chromium through Playwright `1.61.1`, a fixed 3 by 3 production grid, production face matrices, `createInstancedPartMesh` and `syncInstancedPartMesh`, `observeWebGlResources`, `observeRendererDraws`, and `summarizeFrameTimes`. Each row contains N animated 256 px canvas video stand-ins plus one raymarch style `ShaderMaterial` source. The camera pose changes every frame. Each case receives 24 warmup frames and 120 measured frames at 768 by 768. Frame duration covers canvas updates, texture work, source rendering, scene rendering, and `gl.finish()`.

## Numbers

| Video stand-ins plus one shader | Strategy | Display draws per frame | Total draws per frame | Programs compiled | Texture upload or copy calls per frame | Frame p50 ms | Frame p95 ms |
|---:|---|---:|---:|---:|---:|---:|---:|
| 1 + 1 | Dynamic atlas | 1 | 2 | 2 | 3 | 0.20 | 0.30 |
| 1 + 1 | Dedicated layer | 2 | 2 | 2 | 1 | 0.30 | 0.60 |
| 4 + 1 | Dynamic atlas | 1 | 2 | 2 | 9 | 0.50 | 0.60 |
| 4 + 1 | Dedicated layer | 5 | 5 | 2 | 4 | 0.50 | 1.10 |
| 8 + 1 | Dynamic atlas | 1 | 2 | 2 | 17 | 0.80 | 0.90 |
| 8 + 1 | Dedicated layer | 9 | 9 | 2 | 8 | 0.80 | 1.40 |

The dynamic atlas keeps the visible media bucket at one draw and the full frame at two draws because the raymarch source costs one offscreen draw. Dedicated media reaches 5 and 9 total draws at four and eight video sources. Both strategies compile two programs, confirming that dedicated materials share programs but cannot share draw submissions. Atlas traffic follows `2N + 1`: one canvas upload and one atlas copy per video, plus one raymarch target copy. Dedicated traffic follows `N`. Despite the extra copies, the atlas matched dedicated p50 at four and eight videos and reduced p95 from 1.10 to 0.60 ms and from 1.40 to 0.90 ms. At one video, both submit two total draws and atlas also measured lower. This Chromium run favors the dynamic atlas through eight videos for draw scaling and tail time, with upload bandwidth as its explicit cost. The absolute times are synthetic headless measurements and should guide the strategy choice rather than serve as hardware budgets.

## Ownership audit

1. The spike touches only ephemeral camera, canvas, texture, atlas, and shader state owned by its browser driver. Production `syncInstancedPartMesh` remains the sole matrix and colour writer. The driver writes only its new per instance media rectangle and generated texture contents.
2. The changed values are consumed by the test only: the atlas shader consumes media rectangles and the atlas; dedicated `MeshBasicMaterial` instances consume canvas textures; the raymarch material consumes time; the draw, upload, resource, and frame observers consume submissions and timings. Every consumer ran in Chromium.
3. No production capability, domain state, persistence path, UI, or alternate benchmark infrastructure was added. The worktree contains one browser driver and one browser test.
4. Verification commands and raw tails follow.

## Verification

Command:

```text
../../../node_modules/.bin/oxfmt --write tests/f1MediaStrategyBrowserDriver.ts tests/f1MediaStrategy.browser.test.ts && ../../../node_modules/.bin/oxlint tests/f1MediaStrategyBrowserDriver.ts tests/f1MediaStrategy.browser.test.ts && ../../../node_modules/.bin/tsc -b --pretty false
```

Raw tail, exit 0:

```text
No config found, using defaults. Please add a config file or try `oxfmt --init` if needed.
Finished in 13ms on 2 files using 12 threads.
```

Command:

```text
../../../node_modules/.bin/vitest run tests/f1MediaStrategy.browser.test.ts --project chromium --disableConsoleIntercept
```

Raw tail, exit 0:

```text
f1-media-strategy-metrics [{"displayDrawsPerFrame":1,"frameTimeP50Ms":0.19999998807907104,"frameTimeP95Ms":0.30000001192092896,"programs":2,"strategy":"dynamic-atlas","textureUploadCallsPerFrame":3,"totalDrawsPerFrame":2,"videoSourceCount":1},{"displayDrawsPerFrame":2,"frameTimeP50Ms":0.29999998211860657,"frameTimeP95Ms":0.6000000238418579,"programs":2,"strategy":"dedicated-layer","textureUploadCallsPerFrame":1,"totalDrawsPerFrame":2,"videoSourceCount":1},{"displayDrawsPerFrame":1,"frameTimeP50Ms":0.5,"frameTimeP95Ms":0.5999999940395355,"programs":2,"strategy":"dynamic-atlas","textureUploadCallsPerFrame":9,"totalDrawsPerFrame":2,"videoSourceCount":4},{"displayDrawsPerFrame":5,"frameTimeP50Ms":0.5,"frameTimeP95Ms":1.100000023841858,"programs":2,"strategy":"dedicated-layer","textureUploadCallsPerFrame":4,"totalDrawsPerFrame":5,"videoSourceCount":4},{"displayDrawsPerFrame":1,"frameTimeP50Ms":0.800000011920929,"frameTimeP95Ms":0.9000000059604645,"programs":2,"strategy":"dynamic-atlas","textureUploadCallsPerFrame":17,"totalDrawsPerFrame":2,"videoSourceCount":8},{"displayDrawsPerFrame":9,"frameTimeP50Ms":0.800000011920929,"frameTimeP95Ms":1.4000000059604645,"programs":2,"strategy":"dedicated-layer","textureUploadCallsPerFrame":8,"totalDrawsPerFrame":9,"videoSourceCount":8}]

 Test Files  1 passed (1)
      Tests  1 passed (1)
   Start at  13:39:17
   Duration  8.86s (transform 178ms, setup 213ms, import 223ms, tests 8.33s, environment 0ms)
```

Command:

```text
git diff --check && git status --short && git diff --stat && wc -l tests/f1MediaStrategyBrowserDriver.ts tests/f1MediaStrategy.browser.test.ts
```

Raw tail, exit 0:

```text
?? tests/f1MediaStrategy.browser.test.ts
?? tests/f1MediaStrategyBrowserDriver.ts
     553 tests/f1MediaStrategyBrowserDriver.ts
      55 tests/f1MediaStrategy.browser.test.ts
     608 total
```

Main checkout isolation check:

```text
git status --short && git rev-parse HEAD && git branch --show-current
```

Raw tail, exit 0:

```text
3725921ae23cd4088b3891b310889c8861ca05eb
main
```
