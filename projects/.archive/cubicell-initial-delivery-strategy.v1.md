# Cubicell Initial Delivery Strategy

Status: strategy for decision, no implementation

Date: 2026-07-23

Measured source: `docs/performance-audit` at
`27813ba6b2cbb5f1b313e0f9fb04d5ff7dae74a4`

## Executive decision

Adopt a two tier delivery architecture.

1. Every studio is a lazy bounded context behind one shared `StudioDescriptor`
   and `StudioHost` contract. Editor is the first studio. Animation Studio
   becomes the second. New studios add a descriptor and a module without
   changing the application composition root.
2. Optional capabilities inside a studio use one shared `LazyCapability`
   contract. Recording, motion, thumbnails, and panel drag are the first Editor
   capabilities. Their views, commands, loading state, prefetch policy, and
   failure behavior follow the same lifecycle.
3. Dynamic imports define semantic ownership. `manualChunks` may tune a proven
   graph later. Chunk names must never define the architecture.
4. A Vite manifest, raw bundle attribution, and a controlled Chromium startup
   trace become required CI artifacts. Budgets apply to route closures and
   module ownership, so code cannot move between hashed chunks and evade a gate.

This is the only option below that protects Animation Studio from Editor growth
and can also close the current Editor startup gap.

## Decision required from Stuart

Choose one of the strategy variants in
[Surface and decide](#surface-and-decide). The recommendation is Option B.

Approve these product constraints with that choice:

1. Editor canvas, Three.js, React Three Fiber, project opening, command
   metadata, and the minimum usable Editor shell remain on the Editor cold path.
2. Optional panel content may show a stable loading slot after the canvas is
   usable.
3. A shortcut for a loadable discrete command may start its capability load and
   replay once. Hold commands never replay.
4. The current `350 KB` gzip, `2.5 s` LCP, and `100 ms` task ceilings remain the
   release targets. Delivery work ratchets toward them rather than weakening
   them.

## Measured baseline

### Build provenance

The repository was clean before and after measurement. The production command
was:

```text
pnpm build
```

Vite `8.1.3` transformed 983 modules and emitted:

| Asset                      |    Minified |         Vite gzip |
| -------------------------- | ----------: | ----------------: |
| Initial JavaScript         | 1,661.90 KB |         468.09 KB |
| Initial CSS                |    36.57 KB |           6.70 KB |
| Commit projection worker   |    25.85 KB | Not on cold route |
| Storage preparation worker |    38.62 KB | Not on cold route |
| Record hydration worker    |    66.99 KB | Not on cold route |

The brief's prior `1,495 KB / 423 KB gzip` figure did not reproduce at the named
head. The current build is `166.90 KB` larger minified and `45.09 KB` larger
gzip. This strategy uses the verified `468.09 KB` result.

The compressed test server transferred `461,503` bytes for the one startup
script. The small difference from Vite's displayed gzip value comes from the
separate gzip pass used by the test server.

No `React.lazy`, source dynamic import, or Vite split rule exists under `src`.
`main.tsx` statically imports `App`, `DesignSystem`, the command registry, and
the store. The Editor path then reaches every optional surface through static
imports.

### Bundle attribution

`rollup-plugin-visualizer 7.0.1` ran against the real Vite production build with
`template: "raw-data"` and `gzipSize: true`.

Visualizer gzip values compress tree shaken module bodies separately. They are
suited to ranking and percentage attribution. They intentionally do not sum to
the final chunk's gzip bytes. The percentage column uses the visualizer's
`739.19 KB` attribution total.

| Rank | Module group                                            | Isolated gzip attribution | Share |
| ---: | ------------------------------------------------------- | ------------------------: | ----: |
|    1 | Three core, React Three Fiber, Drei, and direct helpers |                 295.49 KB | 40.0% |
|    2 | Cubicell source under `src`                             |                 285.02 KB | 38.6% |
|    3 | React, React DOM, and Scheduler                         |                  99.94 KB | 13.5% |
|    4 | DnD Kit packages                                        |                  51.61 KB |  7.0% |
|    5 | Remaining external packages                             |                   7.12 KB |  1.0% |

The primary renderer is the largest measured owner. The requirement to keep
Three.js and the core Editor renderer on the cold path means delivery work must
reduce the optional portions of Cubicell source, React surface work, and panel
infrastructure around it.

The requested feature attribution is:

| Feature group                           | Included modules | Isolated gzip attribution | Share |
| --------------------------------------- | ---------------: | ------------------------: | ----: |
| Design system                           |                9 |                   1.27 KB | 0.17% |
| Recorder plus recording indicator       |                5 |                   3.48 KB | 0.47% |
| Motion workspace including `BottomDock` |               11 |                  10.77 KB | 1.46% |
| Thumbnail service and renderer          |               10 |                   3.98 KB | 0.54% |

Those four visible candidates total 19.50 KB of isolated gzip attribution, only
2.64 percent of the module attribution. Splitting them is correct for ownership
and future growth. It cannot by itself reduce the current `468.09 KB` entry to
`350 KB`.

The next measured optional owner is DnD Kit. Its 11 modules account for 51.61 KB
of isolated gzip attribution. A forced manual chunk experiment produced a
`29.54 KB` gzip DnD chunk. The same experiment produced a `277.40 KB` gzip
motion and thumbnail chunk while a named Three chunk fell to `2.93 KB`, showing
how manual grouping can reshuffle dependency closure. Semantic dynamic imports
and manifest closure checks are therefore required.

Largest local modules include:

| Rank | Module                                          | Isolated gzip attribution |
| ---: | ----------------------------------------------- | ------------------------: |
|    1 | `src/state/projectDurability.ts`                |                   3.47 KB |
|    2 | `src/persistence/memoryProjectStorage.ts`       |                   3.14 KB |
|    3 | `src/panels/StructureSection.tsx`               |                   3.07 KB |
|    4 | `src/scene/CubeScene.tsx`                       |                   3.00 KB |
|    5 | `src/evaluation/sceneMorph.ts`                  |                   2.93 KB |
|    6 | `src/state/actions/authoredReducer.ts`          |                   2.81 KB |
|    7 | `src/persistence/projectRecordHydration.ts`     |                   2.63 KB |
|    8 | `src/domain/incrementalCubeRenderResolution.ts` |                   2.62 KB |
|    9 | `src/camera/cameraAuthorityRuntime.ts`          |                   2.59 KB |
|   10 | `src/export/streamRecorder.ts`                  |                   2.37 KB |

The source cost is distributed. Broad bounded context ownership will produce
more durable gains than a list of isolated file extractions.

### Cold startup

The production assets were served with real gzip responses. Three Lighthouse
runs used desktop form factor, DevTools throttling, `150 ms` modeled RTT,
`1,600 Kbps` modeled throughput, four times CPU slowdown, a fresh browser
profile, and disabled cache.

| Metric              |    Run 1 |   Run 2 |   Run 3 |  Median |     Target |
| ------------------- | -------: | ------: | ------: | ------: | ---------: |
| LCP                 |  4.571 s | 4.043 s | 4.031 s | 4.043 s |    2.500 s |
| FCP                 |  4.013 s | 3.852 s | 3.839 s | 3.852 s | Diagnostic |
| TBT                 |   754 ms |   65 ms |   58 ms |   65 ms |      Track |
| Time to interactive |  4.959 s | 4.179 s | 4.161 s | 4.179 s | Diagnostic |
| Main thread work    | 1,327 ms |  564 ms |  537 ms |  564 ms | Diagnostic |
| Largest task        |   535 ms |  113 ms |  108 ms |  113 ms |     100 ms |

Every run fails the LCP and long task targets. The first cold run also shows
material startup variance that a single favorable run would hide.

The first run's tasks above 100 ms were:

|   Start | Duration | Attribution          |
| ------: | -------: | -------------------- |
| 3.649 s |   110 ms | Browser unattributed |
| 3.896 s |   107 ms | Startup script       |
| 4.052 s |   535 ms | Startup script       |
| 4.640 s |   319 ms | Startup script       |

Script evaluation accounted for `1,003 ms` of its `1,327 ms` main thread work.
The single startup script transferred `461,503` compressed bytes and completed
near `3.631 s`.

A separate Playwright trace used the applied Fast 3G request profile, `562.5 ms`
request latency, `1,474.56 Kbps` downstream, `675 Kbps` upstream, and four times
CPU slowdown. It recorded:

| Event                            |    Time |
| -------------------------------- | ------: |
| Startup script response complete | 3.626 s |
| Largest startup task begins      | 3.639 s |
| Largest startup task duration    |  144 ms |
| Editor shell present             | 3.808 s |
| Final LCP                        | 4.056 s |

The task begins immediately after the startup script arrives. Transfer,
evaluation, React mount, hydration, and initial layout all need budget
ownership.

## Durable architecture

### Dependency shape

```text
Application bootstrap
  -> StudioCatalog metadata
  -> StudioHost
       -> lazy EditorStudio
            -> core Editor route closure
            -> lazy Editor capabilities
                 -> recording
                 -> motion workspace
                 -> thumbnail renderer
                 -> panel drag
       -> lazy AnimationStudio
            -> core Animation route closure
            -> lazy Animation capabilities
       -> lazy DesignSystemStudio
```

The application bootstrap imports no concrete studio. A studio may import shared
domain, persistence, design primitives, and runtime contracts. A studio must not
import another studio. A feature may import its owner studio's public contract
and shared leaf modules. It must not deep import another feature.

### Studio contract

`StudioDescriptor` is eager and small:

```ts
type StudioDescriptor = {
  id: StudioId;
  route: string;
  commandManifest: readonly CommandManifest[];
  load: () => Promise<StudioModule>;
  prefetch: StudioPrefetchPolicy;
  budget: StudioBudget;
};
```

`StudioModule` owns the route component and activation lifecycle:

```ts
type StudioModule = {
  Component: ComponentType;
  activate(context: StudioContext): StudioLease;
};
```

`StudioLease.dispose()` releases studio scoped subscriptions and resources. The
host has one loading boundary and one error boundary. Route changes dispose the
old lease before activating the next module.

The descriptor catalog contains data and loader functions only. Importing the
catalog must not evaluate Editor, Animation, Design System, Three.js, or feature
implementation code.

### Editor cold route

Keep these on the Editor cold path:

1. React runtime.
2. Three.js, React Three Fiber, and the primary canvas renderer.
3. Project opening and committed project hydration.
4. Base document state and render scheduler.
5. The minimum shell needed to display and operate the canvas.
6. Eager command metadata and keymap definitions.

Move these behind capabilities:

1. Recording controller implementation and indicator view.
2. Motion workspace UI.
3. Thumbnail renderer and cache.
4. DnD implementation for panel and keypad movement.
5. Additional panel feature areas selected by the next bundle report.

The canvas occupies a stable reconciliation slot before and after capability
loads. Loading panel content or DnD must not wrap, replace, or remount the
canvas.

### Shared capability contract

`LazyCapability<T>` has five states:

```text
absent -> loading -> ready
                  -> failed -> loading
ready -> disposed
```

It owns one shared load promise, one loaded implementation, one retry path, and
one disposal path. Concurrent callers join the same promise. A failed load
cannot leave commands, views, or resource producers partially installed.

Each capability descriptor contains:

1. `load()`, using a literal dynamic import.
2. Its feature slot and loading view.
3. Its command IDs.
4. Its availability policy.
5. Its prefetch policy.
6. Its incremental gzip budget.

### Commands and keymaps

Keep the existing command catalog eager and frozen. Late feature registration
would weaken the current registry invariant and make shortcut behavior depend on
load order.

Feature command descriptors delegate to a capability port. The port owns loading
and invocation:

| Availability               | Keyboard behavior                               | UI behavior               |
| -------------------------- | ----------------------------------------------- | ------------------------- |
| Unavailable in this studio | Ignore and preserve browser default             | Hide or disable           |
| Loadable                   | Claim a discrete app command and start one load | Show loading              |
| Loading                    | Coalesce repeats                                | Keep stable loading state |
| Ready                      | Current dispatch behavior                       | Enabled                   |
| Failed                     | Return a deterministic rejection                | Show retry                |

A descriptor explicitly declares whether a discrete action is safe to replay
once after load. Capture toggle is replay safe. Hold commands and continuous
gestures are never replayed. They become usable only after their capability is
ready.

This preserves command validity while implementation code is absent. It also
prevents a loading shortcut from leaking into a browser shortcut or dispatching
twice.

### Loading states

There are two loading surfaces:

1. `StudioHost` renders the application frame and studio route fallback while a
   studio chunk loads.
2. `FeatureSlot` preserves the owning studio layout while an optional capability
   loads.

Feature slots have fixed ownership and predictable minimum geometry. They must
not shift the canvas, reset selection, rebuild the store, or remount WebGL.
Loading failures stay local to the slot unless the entire studio cannot load.

### Prefetch policy

Prefetch is centralized. Individual components do not invent timers.

1. Route intent: prefetch a studio on navigation focus or pointer intent.
2. Editor idle: after project hydration, final LCP, and an idle slot, prefetch
   only capabilities visible in the current layout.
3. Recording: prefetch on capture control focus or pointer intent. A keyboard
   command loads and replays once.
4. Motion: load after the core Editor is interactive when the dock is open.
5. Thumbnails: load the feature module with Motion. Preserve the current idle
   defer before constructing the WebGL backend or rendering a thumbnail.
6. Design system: never prefetch from Editor.
7. Network policy: skip speculative prefetch when `saveData` is true or the
   connection policy rejects it.

Prefetch warms bytes. It never activates resources, subscribes to state, or
registers render producers.

### Animation Studio insertion

Animation Studio contributes:

1. One descriptor in `StudioCatalog`.
2. One lazy route module under its bounded context.
3. Its command manifest.
4. Its route and capability budgets.
5. Its optional feature descriptors.

No Editor import changes are required. Shared domain and rendering contracts
remain neutral. CI proves Animation modules are absent from the Editor route
closure and Editor feature modules are absent from the Animation cold route.

## CI budget gate

### Tool choice

Choose `rollup-plugin-visualizer` with Vite's build manifest.

1. Vite `build.manifest` provides the entry, static import, dynamic import, and
   CSS graph using stable source keys.
2. `rollup-plugin-visualizer` raw data maps source modules to emitted chunks and
   supplies gzip attribution.
3. A small repository owned checker computes route closures, compresses final
   output files, applies budgets, and asserts forbidden module ownership.

`size-limit` and `bundlesize` work well for stable file paths. Cubicell needs
route closure and source membership assertions across hashed chunks.
`manualChunks` changes output shape and is therefore an optimization input, not
a gate.

Official references:

1. [Vite build manifest](https://vite.dev/config/build-options.html#build-manifest)
2. [Rollup Plugin Visualizer raw data and gzip](https://github.com/btd/rollup-plugin-visualizer)
3. [Lighthouse throttling model](https://github.com/GoogleChrome/lighthouse/blob/main/docs/throttling.md)
4. [W3C Long Tasks API](https://www.w3.org/TR/longtasks-1/)

### Required artifacts

Every production build emits:

```text
dist/.vite/manifest.json
artifacts/bundle/raw-data.json
artifacts/bundle/budgets.json
artifacts/startup/lighthouse-*.json
artifacts/startup/long-tasks.json
```

The CI report names the route, exact compressed closure, budget, delta from
base, largest added modules, forbidden modules, LCP, TBT, and every task above
100 ms.

### Closure definitions

1. Bootstrap closure: JavaScript and CSS referenced directly by HTML before a
   studio is selected.
2. Studio cold closure: bootstrap plus the selected studio route chunk and all
   of its static imports.
3. Capability increment: bytes newly fetched when that capability loads after
   its studio cold closure.
4. Initial browser closure: resources fetched before the studio emits its
   `interactive` performance mark.

The manifest proves build topology. The browser trace proves actual request
timing. Both must pass.

### Proposed budgets

| Surface                                 |     Ceiling |
| --------------------------------------- | ----------: |
| Bootstrap JavaScript closure            |  25 KB gzip |
| Editor cold JavaScript closure          | 350 KB gzip |
| Design system incremental route         |  50 KB gzip |
| Recording capability increment          |  12 KB gzip |
| Motion capability increment             |  50 KB gzip |
| Thumbnail capability increment          |  25 KB gzip |
| Panel drag capability increment         |  40 KB gzip |
| Initial LCP, Fast 3G and four times CPU |       2.5 s |
| Any initial main thread task            |      100 ms |
| Initial TBT                             |      200 ms |

Animation Studio must declare its own cold route and capability ceilings before
its first code lands. There is no permissive default.

### Ownership assertions

The gate fails when:

1. Any `src/design-system/**` module belongs to the Editor cold closure.
2. Any Animation Studio module belongs to the Editor cold closure.
3. Any Editor optional capability belongs to the Animation cold closure.
4. Recorder implementation code is fetched before recording capability intent.
5. A studio imports another studio.
6. A feature deep imports another feature.
7. An emitted route or capability has no declared budget.

Assertions use source module IDs from raw visualizer data. Hashed file names
cannot hide a violation.

### Browser gate

Use a pinned Chromium version on a dedicated performance runner. Serve actual
gzip files. Vite preview alone does not provide gzip in this repository's
current setup.

Run three fresh profiles with cache disabled and the locked Fast 3G plus four
times CPU profile. Fail when:

1. Median LCP exceeds `2.5 s`.
2. Any initial page task exceeds `100 ms`.
3. Median TBT exceeds `200 ms`.
4. A capability request occurs before its allowed trigger.
5. The Editor interactive mark appears before project opening is complete or
   before the canvas can accept input.

Store every raw report. Performance claims cite the run set, median, range,
Chrome version, host benchmark index, commit, and compressed response headers.

### Ratchet

The current product cannot pass the target budgets. Land the gate first with the
verified current ceiling as a temporary ratchet:

1. Editor gzip cannot exceed `468.09 KB`.
2. Median LCP cannot exceed `4.043 s`.
3. Largest task cannot exceed the verified run set.

Each delivery slice lowers the ratchet to its measured result. The strict
product targets replace the temporary values when reached. A slice may not
increase one metric to improve another without an explicit decision recorded in
the budget file.

## Reuse map

| Existing primitive                  | Decision                                                                                                 |
| ----------------------------------- | -------------------------------------------------------------------------------------------------------- |
| Vite `manualChunks` state           | None exists; use dynamic imports for ownership and reserve manual grouping for measured tuning.          |
| `createDeferredThumbnailBackend`    | Reuse its idle construction and lifecycle after the thumbnail chunk loads; it does not split code today. |
| `editorPieceMotionWorkspaceEnabled` | Reuse only as temporary descriptor eligibility, then delete it when the catalog owns enablement.         |

Also preserve the frozen command catalog. Route feature implementations through
lazy ports rather than introducing order dependent late registration.

## Surface and decide

### Option A: Studio routes only

Create `StudioCatalog` and lazy route modules for Editor, Animation, and Design
System. Keep the current Editor internals static.

Benefits:

1. Clean future studio ownership.
2. Design System becomes zero bytes in Editor.
3. Smallest structural change.

Costs:

1. Current Editor remains near `468.09 KB` gzip.
2. Recording, Motion, thumbnails, and DnD still evaluate before use.
3. The `350 KB`, LCP, and task targets are unlikely to pass.

Verdict: valid foundation, incomplete delivery strategy.

### Option B: Studio routes plus capability boundaries

Create the studio route contract and the shared capability lifecycle. Apply it
first to recording, motion, thumbnails, and panel drag. Use each new report to
choose the next optional Editor capability until the cold route meets budget.

Benefits:

1. Animation Studio plugs into a durable route contract.
2. Editor optional features use the same lifecycle.
3. Command, loading, prefetch, failure, and budget behavior are defined once.
4. The current performance targets are reachable without deferring Three.js.
5. Module ownership remains understandable as studios grow.

Costs:

1. Requires a deliberate composition root and stable feature slots.
2. Command availability needs one explicit state machine.
3. DnD extraction must preserve canvas reconciliation identity.

Verdict: recommended.

### Option C: Aggressive granular splitting

Split individual panels, hooks, dependencies, and large files wherever a bundle
report shows bytes.

Benefits:

1. Maximum short term control over transfer timing.
2. Can minimize the first request set.

Costs:

1. Many waterfalls and loading states.
2. Weak bounded context ownership.
3. Frequent shared dependency reshuffling.
4. Higher risk of command, subscription, and WebGL lifecycle defects.
5. Animation Studio would inherit a tuning exercise instead of an architecture.

Verdict: reject.

## Independently shippable slices

### Slice 0: measurement and ratchet

1. Add Vite manifest and raw visualizer artifacts.
2. Add the route closure and source ownership checker.
3. Add the compressed Chromium startup harness.
4. Lock the current verified baseline as a temporary ratchet.

Proof: repeat this document's build and browser measurements in CI.

### Slice 1: composition root and route boundaries

1. Add `StudioCatalog`, `StudioHost`, and route error handling.
2. Move Editor and Design System behind literal dynamic imports.
3. Keep the Editor behavior unchanged.
4. Turn on the Design System zero assertion.

Proof: both routes load directly, Editor contains zero Design System modules,
and project hydration plus canvas input still work.

### Slice 2: shared capability runtime and recording

1. Add `LazyCapability`, availability states, and replay policy.
2. Keep recording command metadata eager.
3. Move `createRecordingController`, `useRecordingController`, and the indicator
   implementation behind the recording capability.
4. Load once on first capture intent and preserve every lifetime gate from PR
   #126.

Proof: first capture loads and starts once, later captures reuse the module, all
nine lifetime cases remain green, and recorder code is absent before intent.

### Slice 3: motion and thumbnail ownership

1. Move Motion behind a stable `FeatureSlot`.
2. Load Motion after Editor interactivity when the dock is open.
3. Move thumbnail code with its owner.
4. Preserve `createDeferredThumbnailBackend` so WebGL construction still waits
   for a real thumbnail request and an idle slot.

Proof: no canvas remount, no panel geometry jump, thumbnails retain their
current disposal guarantees, and the capability stays absent when the dock is
closed.

### Slice 4: panel drag and next measured optional owner

1. Move DnD Kit behind an after interactive capability.
2. Reshape the shell so activating DnD never changes the canvas element's parent
   identity.
3. Rebuild and choose any further optional owner from the new attribution
   report.

Proof: drag remains correct, keyboard and canvas input work before DnD is ready,
and Editor cold gzip reaches `350 KB` or the report names the exact remaining
closure.

### Slice 5: strict release budgets

1. Replace temporary ratchets with product ceilings.
2. Tune intent and idle prefetch from browser traces.
3. Make Editor, Design System, and capability budgets required PR checks.
4. Publish the Studio descriptor template for Animation Studio.

Proof: Editor cold JavaScript is at most `350 KB` gzip, LCP is at most `2.5 s`,
no initial task exceeds `100 ms`, and no forbidden studio module crosses a route
boundary.

## Recommendation

Approve Option B and ship Slices 0 through 5 in order.

The architecture should begin with ownership and executable budgets. Design
System and recorder splits are clean first proofs. Motion, thumbnails, and DnD
exercise the feature contract under real UI and WebGL constraints. Animation
Studio can then enter through the same descriptor, loading, command, prefetch,
and CI contracts without reopening initial delivery architecture.
