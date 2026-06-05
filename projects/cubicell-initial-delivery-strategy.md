# Cubicell Initial Delivery Strategy

Status: Option B confirmed, Slices 0 through 3 shipped, Slice 4 awaits live UX

Date: 2026-07-24

Original measured source: `27813ba6b2cbb5f1b313e0f9fb04d5ff7dae74a4`.
Slice 4 ownership source: `f7f7db213d36bac09f9c15abc358bde71cd0b34e`.

## Executive decision

Adopt a two tier delivery architecture.

1. Every studio is a lazy bounded context behind one `StudioDescriptor` and
   `StudioHost` contract. Editor is the first studio. Animation Studio becomes
   the second.
2. Three.js, React Three Fiber, and the canvas live in one shared renderer leaf.
   The composition root injects that leaf into each studio through a neutral
   contract. Studios never import other studios.
3. Optional studio features use one `LazyCapability` lifecycle. Recording,
   motion, thumbnails, and panel drag are the first Editor capabilities.
4. A small bootstrap paints one accurate branded loading indicator. It reports
   real milestones while the Editor and renderer load concurrently, then hands
   off only when the scene can accept input.
5. Executable build budgets and source ownership assertions land before any
   split. A GitHub Actions workflow enforces static budgets. Browser timing
   remains explicit local proof until a stable performance runner exists.

Dynamic imports define ownership. `manualChunks` may tune a proven graph later.
Chunk names never define the architecture.

## Confirmed product decisions

1. The first paint is an accurate loading indicator. No partial Editor shell
   hydrates before the canvas is usable.
2. LCP measures that loading indicator and keeps the `2.5 s` gate.
   `time-to-interactive-canvas` separately measures the post-renderer handoff,
   with a `3.0 s` target under the locked profile.
3. The Editor cold route excludes the shared renderer leaf in ownership
   reports. The complete default startup closure still includes bootstrap,
   Editor, renderer, and mandatory shared chunks.
4. Optional panels may show a stable loading slot after canvas interaction is
   ready.
5. A loading toggle reconciles its last intended parity. Two rapid capture
   presses end off. Hold commands never replay.
6. The current `350 KB` gzip and `100 ms` task ceilings remain release targets.
   Delivery work ratchets toward them.

## Measured baseline

### Build provenance

The repository was clean before and after measurement. The production command
was `pnpm build`.

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

The renderer is the largest measured owner. Its `295.49 KB` figure is an
isolated attribution floor, not an emitted chunk measurement. Slice 1 gives the
shared renderer leaf its first exact compressed budget. The renderer remains on
the default startup path while leaving the Editor studio ownership closure.

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

The Slice 4 graph at `f7f7db2` attributes 11,324 B to Motion and 3,980 B to
thumbnails, for 15,304 B of removable source. The candidate removes all 15,304
B from the cold source closure. Motion emits 8,720 B, thumbnails 2,089 B, and
camera motion 804 B as deferred capability increments. The default closure is
430,311 B, down 6,969 B from the exact 437,280 B base. The Editor closure is
364,066 B, down 10,321 B. Default startup remains eight static chunks.

The same graph attributes 228,755 B to two shared Three modules. These bytes
remain anchored by the committed viewport and contribute 0 B to the Slice 4
removal claim. The final ownership gate reports zero classified cold modules,
zero temporary allowances, and no alternate Editor path when the thumbnail
owner is removed.

Further closure must come from measured optional owners:

1. Non-motion panel and selector surfaces, about `29.46 KB` of isolated
   attribution after removing the Motion group from `src/panels`.
2. Optional persistence adapters and recovery surfaces, beginning with
   `memoryProjectStorage.ts` at `3.14 KB`.
3. Feature-owned document, selection, and command paths now pulled into the
   route by panel barrels.
4. Renderer import precision inside the shared leaf, while preserving Three.js
   and the primary canvas on the startup path.

The ten largest local modules range only from `3.47 KB` to `2.37 KB` of isolated
attribution. The source cost is distributed, so bounded context ownership is
more durable than isolated file extraction.

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

The first run had tasks of `110 ms` at `3.649 s`, `107 ms` at `3.896 s`,
`535 ms` at `4.052 s`, and `319 ms` at `4.640 s`. The final three belonged to
the startup script. Script evaluation accounted for `1,003 ms` of `1,327 ms`
main thread work. The `461,503` byte compressed script completed near `3.631 s`.

A separate Playwright trace used `562.5 ms` request latency,
`1,474.56 Kbps` downstream, `675 Kbps` upstream, and four times CPU slowdown.
The startup script completed at `3.626 s`; a `144 ms` task began at `3.639 s`;
the Editor shell appeared at `3.808 s`; and final LCP was `4.056 s`.

The task begins immediately after the startup script arrives. Transfer,
evaluation, React mount, hydration, and initial layout all need budget
ownership.

The current trace has no authoritative canvas interaction mark. `3.808 s` is
only the first observed Editor shell. Slice 0 adds
`cubicell:interactive-canvas`, emitted after all of these conditions hold:

1. The shared renderer module has activated.
2. The WebGL context exists.
3. Project hydration has installed the active scene.
4. The first frame for that scene has committed.
5. Pointer and command ports can accept input.

The loading indicator becomes the intended LCP candidate. It is honest because
the product is still loading. The `2.5 s` LCP gate measures how quickly Cubicell
communicates that state. The `3.0 s` interactive canvas gate measures when the
studio becomes useful. Browser proof asserts the LCP entry belongs to the
loading indicator and never claims the canvas painted within `2.5 s`.

## Durable architecture

### Dependency shape

Application bootstrap paints the indicator and loads catalog metadata.
`StudioHost` fetches Editor and `SharedRenderer` concurrently, composes them,
then permits lazy Editor capabilities. Animation later uses the same renderer.
Design System remains a separate lazy studio.

The bootstrap imports no studio, Three.js, React Three Fiber, or capability
implementation. Studios consume neutral domain, persistence, UI, command, and
renderer contracts. They never import each other.

### Accurate startup and default route concurrency

The first rendered surface is one simple branded indicator. It reports `bundle
transferred`, `engine initializing`, `scene loading`, then `scene live` before
removal. It never reports byte percentages.

HTML module preload completion marks the default route and renderer transfer.
Renderer activation marks engine initialization. Project hydration and the
first committed scene frame mark scene loading and scene live.

The production HTML uses manifest derived `modulepreload` links for the default
Editor route and shared renderer. Their downloads start with the tiny
bootstrap. `StudioHost` imports both immediately and awaits them concurrently.
Module preload warms the module graph without evaluating it. This avoids
serializing bootstrap evaluation, Editor transfer, and renderer transfer.

### Shared renderer boundary

The shared renderer leaf owns Three.js, React Three Fiber, Drei, `<Canvas>`,
scene meshes, render scheduling, and WebGL lifecycle. Editor and Animation
Studio consume its eager type contract. `StudioHost` loads and injects one
implementation.

The current path is `src/main.tsx` to `src/app/App.tsx` to
`src/app/ConnectedCubeScene.tsx` to `src/scene/CubeScene.tsx` to the React Three
Fiber `Canvas`.

Slice 1 changes these composition seams:

1. `src/main.tsx` imports only the bootstrap, loading indicator CSS, and eager
   catalog metadata. Its static `App` and `DesignSystem` imports disappear.
2. `src/app/AppBootstrap.tsx` owns loading phases, route generation, and the
   concurrent Editor plus renderer promises.
3. `src/studios/catalog.ts` owns literal studio loaders and budgets.
4. `src/studios/editor/EditorStudio.tsx` receives a renderer slot. It does not
   import `ConnectedCubeScene`, `CubeScene`, Three.js, or React Three Fiber.
5. `src/renderer/contract.ts` contains erased types for scene input, selection,
   camera, capture registration, scheduler, and interaction callbacks.
6. `src/renderer/SharedRendererCanvas.tsx` owns the current `CubeScene`,
   `<Canvas>`, scene components, and Three runtime imports.
7. The current `ConnectedCubeScene` subscriptions become an Editor renderer
   binding. `StudioHost` passes that neutral binding to the renderer.
8. `stageInteraction.ts` reads renderer contract types instead of importing
   `CubeScene` types.

The composition root renders the studio view with the injected renderer slot.
The renderer stays mounted while capabilities load.

### Studio contract

`StudioDescriptor` is eager and small. It contains `id`, `route`, command
manifest, literal `load`, prefetch policy, and budget. The loaded
`StudioModule` exposes `View` and
`prepare(context: StudioContext): PreparedStudio`.

The descriptor catalog contains data and loader functions only. Importing it
cannot evaluate a studio, renderer, or capability.

### Editor cold route

The Editor studio closure keeps project opening, committed hydration, base
document state, minimum usable layout, command metadata, and keymaps. The
shared renderer closure keeps Three.js and canvas runtime. Capabilities own:

1. Recording controller implementation and indicator view.
2. Motion workspace UI.
3. Thumbnail renderer and cache.
4. DnD implementation for panel and keypad movement.
5. Additional panel feature areas selected by the next bundle report.

The complete default startup closure is bootstrap plus Editor plus shared
renderer plus their mandatory shared imports. Every part is reported
separately and as one interactive closure.

### Shared capability contract

`LazyCapability<T>` moves through `absent`, `loading`, `ready`, `failed`, and
`disposed`; a failed load can retry.

It owns one shared load promise, one loaded implementation, one retry path, a
context generation, and one idempotent disposal path. Concurrent callers join
the same promise. Capability modules have no top level producer registration or
resource acquisition.

Each capability descriptor contains:

1. `load()`, using a literal dynamic import.
2. Its feature slot and loading view.
3. Its command IDs.
4. Its availability policy.
5. Its prefetch policy.
6. Its incremental gzip budget.

#### Generation token

Every studio activation receives a monotonically increasing generation. Route
change, context replacement, and disposal increment it before releasing
resources. A capability captures the generation before `await load()`. If the
current generation differs when the promise resolves, the implementation is
dropped and `activate` is never called.

This closes the load versus dispose race. A late recording module cannot attach
to a dead renderer, reacquire the shared guard, or register
`renderProducers.recording` after its owner has gone away.

#### Transactional activation

Activation is build then commit:

1. `prepare(context)` creates local resources and a partial disposer. It
   publishes no command port, subscription, render producer, or global handler.
2. The host checks the generation again.
3. `commit()` publishes the prepared capability as one ownership transition.
4. A throw during prepare or commit calls the partial disposer.
5. The disposer is idempotent, so rollback and later context disposal cannot
   release the same registration twice.

A capability reaches `ready` only after commit succeeds. Failures leave it in
`failed` with no partial registration.

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
| Loading                    | Reconcile descriptor specific intent            | Keep stable loading state |
| Ready                      | Current dispatch behavior                       | Enabled                   |
| Failed                     | Return a deterministic rejection                | Show retry                |

Each descriptor defines its loading intent reducer. Capture is a toggle, so
every press flips `desiredActive` within the current generation. When the
module commits, it reconciles the last intent once. One press starts recording,
two rapid presses end off, and three end on. The last requested source wins.
Holds and continuous gestures never replay.

This preserves command validity while implementation code is absent. It also
prevents a loading shortcut from leaking into a browser shortcut or dispatching
twice.

### Loading states

There are two loading surfaces:

1. The startup indicator remains the only pre-Editor surface until the
   interactive canvas mark.
2. `FeatureSlot` preserves studio layout while an optional capability loads
   after handoff.

Feature slots have fixed ownership and predictable minimum geometry. They must
not shift the canvas, reset selection, rebuild the store, or remount WebGL.
Loading failures stay local to the slot unless the entire studio cannot load.

### Prefetch policy

Prefetch is centralized. It resolves chunk URLs from the build manifest and
adds low priority `<link rel="prefetch">` entries, or an equivalent low priority
fetch, for every file in the capability closure. It never calls `load()` or
`import()`. Dynamic import evaluates top level module code and is reserved for
actual activation.

1. The default Editor and renderer use `modulepreload`, not prefetch, because
   their downloads are mandatory and concurrent with bootstrap.
2. Route focus or pointer intent prefetches another studio's bytes.
3. Capture control intent prefetches recording bytes. A shortcut applies the
   parity reducer above.
4. After interactive canvas, an idle policy prefetches visible optional
   features.
5. Motion activates when the dock is open. Thumbnail construction retains the
   existing idle defer after its bytes and module are ready.
6. Design System never prefetches from Editor.
7. Speculative prefetch is skipped for `saveData` or a rejected connection
   policy.

Prefetch fetches bytes only. It cannot register producers, subscribe to state,
or allocate WebGL resources.

### Animation Studio insertion

Animation Studio contributes:

1. One descriptor in `StudioCatalog`.
2. One lazy route module under its bounded context.
3. Its command manifest.
4. Its route and capability budgets.
5. Its optional feature descriptors.

No Editor import changes are required. Animation provides a neutral renderer
binding and `StudioHost` composes it with the same shared renderer leaf. Static
gates prove both studio isolation and renderer ownership.

## Executable budget gate

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

### Runnable scripts and PR enforcement

The repository currently has no `.github/` directory, workflow, `build:budget`,
or `check:budget` script. Slice 0 adds `pnpm build:budget` for the production
manifest, raw visualizer data, exact gzip files, and closure report. It adds
`pnpm check:budget` to validate the schema, compute emitted closures, enforce
size and ownership rules, and exit nonzero on violations.

A new `.github/workflows/delivery-budget.yml` runs both scripts for pull
requests and `main`. That makes static bundle and ownership checks enforced CI.

Browser timing remains an explicit required local proof attached to the pull
request until a pinned, stable performance runner exists. The document does not
call browser artifacts required CI before that runner is real.

### Artifacts

`build:budget` and browser proof emit the Vite manifest, bundle raw data,
budgets, Lighthouse reports, and long task report under `dist/.vite` and
`artifacts`.

The report names each closure, exact gzip bytes, budget, base delta, largest
added modules, forbidden modules, LCP element, interactive canvas time, TBT,
and every task above 100 ms.

### Closure definitions

1. Bootstrap closure: JavaScript and CSS required to paint the loading
   indicator.
2. Studio cold closure: one studio route and its static imports, excluding the
   shared renderer leaf.
3. Shared renderer closure: Three.js, React Three Fiber, canvas, and static
   renderer imports.
4. Default interactive closure: bootstrap, Editor studio, shared renderer, and
   mandatory shared imports fetched before `cubicell:interactive-canvas`.
5. Capability increment: bytes newly fetched when a capability activates.
6. Initial browser closure: resources fetched before the interactive canvas
   mark, including unexpected dynamic requests.

The manifest proves build topology. The browser trace proves actual request
timing. Both must pass.

### Proposed budgets

| Surface                                      | Ceiling                        |
| -------------------------------------------- | ------------------------------ |
| Bootstrap JavaScript closure                 | 25 KB gzip                     |
| Default interactive JavaScript closure       | 350 KB gzip                    |
| Shared renderer leaf                         | 300 KB attribution provisional |
| Design System incremental route              | 50 KB gzip                     |
| Recording capability increment               | 12 KB gzip                     |
| Motion capability increment                  | 50 KB gzip                     |
| Thumbnail capability increment               | 25 KB gzip                     |
| Panel drag capability increment              | 40 KB gzip                     |
| Loading indicator LCP, locked profile        | 2.5 s                          |
| `time-to-interactive-canvas`, locked profile | 3.0 s                          |
| Any initial main thread task                 | 100 ms                         |
| Initial TBT                                  | 200 ms                         |

The renderer's `300 KB` line uses the current `295.49 KB` isolated attribution
as a provisional ceiling. Slice 1 replaces it with exact emitted gzip and keeps
the attribution report beside it. Animation Studio declares its own studio and
capability ceilings before its first code lands.

Slice 0 updates the `PERFORMANCE.md` Initial Delivery budget language:

1. Accurate startup indicator LCP at or below `2.5 s`.
2. Interactive canvas at or below `3.0 s`.
3. Default interactive JavaScript at or below `350 KB` gzip.
4. Shared renderer reported and budgeted separately.
5. Design System contributes zero modules to Editor startup.
6. No initial main thread task above `100 ms`.

The document makes no canvas paint claim at `2.5 s`.

### Ownership assertions

The gate fails when:

1. Any `src/design-system/**` module belongs to the Editor or default
   interactive closure.
2. Any capability source belongs to the Editor studio or default interactive
   closure.
3. A `manualChunks` rule or dependency merge re-hoists capability source into
   any emitted cold chunk.
4. Any studio imports another studio.
5. An Editor path reaches Three.js outside a declared committed frame owner or
   temporary removal owner, or any studio imports React Three Fiber,
   `CubeScene`, or another renderer implementation module.
6. Shared renderer source appears outside the renderer closure, or the required
   renderer leaf is absent from Editor or Animation interactive closure.
7. Recorder implementation bytes are fetched before recording intent.
8. A feature deep imports another feature.
9. An emitted studio, renderer, or capability has no declared budget.

Assertions use source module IDs from raw visualizer data. Hashed file names
cannot hide a violation.

### Browser gate

Use pinned Chromium and serve actual gzip files. Vite preview alone does not
provide gzip in this repository's current setup.

Run three fresh profiles with cache disabled and the locked Fast 3G plus four
times CPU profile. Fail when:

1. Median LCP exceeds `2.5 s`.
2. The final LCP element is not the accurate startup indicator.
3. Median `time-to-interactive-canvas` exceeds `3.0 s`.
4. Any initial page task exceeds `100 ms`.
5. Median TBT exceeds `200 ms`.
6. A capability request occurs before its allowed trigger.
7. The interactive mark precedes renderer activation, project hydration, first
   scene frame, or live input ports.

Store every raw report. Performance claims cite the run set, median, range,
Chrome version, host benchmark index, commit, and compressed response headers.

### Ratchet

The current product cannot pass the target budgets. Slice 0 lands a temporary
ratchet:

1. Editor gzip cannot exceed `468.09 KB`.
2. Median LCP cannot exceed `4.043 s`.
3. Largest task cannot exceed the verified run set.
4. The new interactive canvas mark records a baseline before its target
   becomes blocking.

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

## Decision record

Stuart confirmed Option B: studio routes, a shared renderer leaf, and lazy
capability boundaries.

Option A, studio routes alone, proves route ownership but leaves the Editor near
`468.09 KB` gzip and keeps optional work eager. Option C, granular splitting by
module size, creates waterfalls and weak ownership. Both remain rejected.

Option B gives Animation Studio a stable route and renderer contract while
Editor capabilities share one lifecycle, command, loading, prefetch, failure,
and budget model.

## Ordered mergeable slices

The slices are ordered. Each can merge with its own gate.

### Slice 0: executable measurement and ratchets

1. Add runnable `build:budget` and `check:budget` scripts, Vite manifest output,
   raw visualizer data, and the repository owned closure checker.
2. Add the static bundle and ownership job in
   `.github/workflows/delivery-budget.yml`. Keep browser timing as required local
   proof until a stable browser runner exists.
3. Record the interactive canvas baseline and rewrite `PERFORMANCE.md` with the
   loading indicator LCP gate, interactive canvas target, and separate renderer
   budget.

Gate: scripts exit nonzero for budget, Design System zero, capability closure,
manual chunk rehoisting, studio import, and renderer ownership violations.

Delivery win: none. This slice makes later claims executable.

### Slice 1: startup, studio routes, and shared renderer

1. Add the accurate startup indicator and hand it off only after the scene is
   live.
2. Add `StudioCatalog`, `StudioHost`, and concurrent module preload for the
   default Editor and shared renderer closures.
3. Move Three, R3F, Canvas, scene rendering, and the scheduler into the shared
   renderer leaf. Inject that leaf into Editor through a neutral contract.
4. Move Design System behind its literal route import and enable its zero
   assertion.

Gate: both studios load directly, the default route has no bootstrap waterfall,
the indicator is the final LCP element, the scene handoff works, renderer
ownership passes, and Editor includes zero Design System modules.

Delivery win: about `1.27 KB` of isolated Design System attribution. This proves
ownership and the zero assertion. No LCP victory is claimed.

### Slice 2: capability runtime and recording

1. Add `LazyCapability` with generation invalidation, transactional activation,
   partial disposal, availability states, and last intent parity replay.
2. Keep recording command metadata eager. Move the controller, hook, and
   indicator implementation behind the capability.

Gate: every recording lifetime case from PR #126 remains green, rapid toggle
parity is correct, late loads cannot activate into disposed contexts, activation
throws leak nothing, and recorder code is absent before intent.

Delivery win: about `3.48 KB` of isolated attribution.

### Slice 3: panel drag, the first material win

1. Move DnD Kit behind an after interactive capability.
2. Preserve the canvas parent identity while DnD activates.

Gate: drag works, keyboard and canvas input work before DnD is ready, no canvas
remount occurs, and the measured closure falls by the expected owner.

Delivery win: `51.61 KB` isolated gzip attribution. The exact manual split
experiment produced a `29.54 KB` gzip DnD chunk.

### Slice 4: motion and thumbnails

1. Move Motion behind a stable `FeatureSlot` and load it after interactivity
   when the dock is open.
2. Move thumbnail code with its owner while retaining the deferred backend and
   idle WebGL construction.

Gate: no geometry jump or canvas remount, thumbnail disposal remains correct,
and both owners stay absent when their triggers do not occur.

Measured result: all 15,304 B of isolated Motion and thumbnail source
attribution left the cold closure. Browser tests prove stable geometry, stable
primary canvas identity, one reused offscreen thumbnail context, and disposal.
Three remains anchored by the committed viewport.

### Slice 5: measured residual closure and product ceilings

1. Rebuild and extract the next measured owners: non Motion panels at about
   `29.46 KB`, optional persistence and recovery including
   `memoryProjectStorage` at `3.14 KB`, and feature operations pulled in through
   panel barrels.
2. Tighten renderer import precision without fragmenting its shared ownership.
3. Replace temporary ratchets with product ceilings only when measurements pass.
4. Publish the Animation Studio descriptor against the same renderer contract.

Gate: Editor cold JavaScript is at most `350 KB` gzip, loading indicator LCP is
at most `2.5 s`, interactive canvas is at most `3.0 s`, no initial task exceeds
`100 ms`, and every closure rule passes.

The shared renderer remains a mandatory attribution floor. The current default
closure is 430,311 B. Under the locked profile, committed frame is 4,446.0 ms
versus 4,480.4 ms at the exact base and 4,485.5 ms historically. The maximum
task median is 425 ms. Loading indicator LCP passes, while the 350 KB,
3.0 second, and 100 ms release ceilings remain open.

## Final recommendation

Ship Option B through these ordered slices. Slice 3 is the first material
transfer win. Slice 5 owns the measured residual rather than relying on
unverified estimates.
