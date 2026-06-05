# Cubicell OOM instrumentation scout

Scope: seat C, instrumentation capability. Worktree
`/Users/alphab/Dev/LLM/DEV/helioy/cubicell/.claude/worktrees/performance-audit`,
branch `docs/performance-audit` @ `60da3f7`, tree clean. Read-only pass: no
writes to `src` or `tests`. Every claim below is either a citation to code read
at this head or is labelled UNVERIFIED. Nothing here was profiled.

**Headline.** The crashing `postMessage` is the worker's *reply*, and no
harness in this repo can see worker heap: the repo contains zero heap
instrumentation of any kind, and `Performance.getMetrics` (the only heap source
the prior campaign used) reports the page isolate only. The one choke point the
brief hoped for is real for requests (all three workers go through
`src/shared/workerRequestClient.ts`) but does **not** exist for replies (three
independent `postMessage` sites, no shared worker-side helper). Separately,
reading the commit path shows one keystroke on a transition control ships four
project-scale structured clones through two workers, behind two unbounded
retaining queues, so hypotheses (a) and (b) are not exclusive and the procedure
below is built to separate them.

---

## Reuse Map

### 1. Harnesses that can drive the real app in a browser

The repo has exactly **one** harness that mounts the real app composition, and
it is not one of the `*BrowserDriver` files.

| Harness | Entry | Real app composition? |
|---|---|---|
| `tests/motionCapability.browser.test.ts` | `page.goto(origin)` on the Vite dev server root (`:45`), then `page.waitForSelector(".cube-canvas canvas")` | **YES.** Real `index.html` → `src/main.tsx` → `AppBootstrap` → `StudioHost` → `EditorStudio`. Drives real controls by role: `Expand Motion panel` (`:58`), `Snapshot current scene` (`:64`, `:84`). Captures `pageerror` (`:34`) and asserts it empty (`:86`). |
| `tests/capabilityPrefetch.browser.test.ts` | `page.goto(origin)` (`:36`) | **PARTIAL.** Boots the real app, then injects `prefetchCapabilityClosure` via `addScriptTag` and, for the affordance half, replaces the document with `page.setContent` (`:82`). The prefetch assertions are about an injected function, not the running app. |
| `tests/playbackFrameBrowserDriver.tsx` | `runPlaybackFrameBrowserGate` mounts `EditorStudioTestRoot` under a hand-built store (`:101-141`) | **NO — closest partial.** Real `Studio` and real renderer module (`tests/editorStudioTestSupport.tsx:16-28`), but `createMemoryProjectStorage()` (`:108`), an inert `StudioLifecycle`, and no `main.tsx` / `AppBootstrap` / `StudioHost` / IndexedDB. **Its storage port has no IndexedDB and therefore never exercises the persistence path under suspicion.** |
| `tests/incrementalSceneBrowserDriver.tsx` + `tests/incrementalSceneProductionTree.tsx` | mounts `EditorRendererBinding` + `CubeScene` directly | **NO.** Documented in the boot-ownership scout §3: no bootstrap, no preload, no IndexedDB, no hydration worker, no shell. |
| `tests/motionTimelinePanBrowserDriver.tsx` | mounts one `PieceStateStrip` into a bare div (`:19-75`) | **NO.** A single component plus the panel-drag capability. The `fixture-certifies-fixture` trap in its purest form: it renders neither the panel nor the app. |
| `tests/committedStoreBrowserDriver.ts`, `cubicellStoreBrowserDriver.ts`, `projectStorage*BrowserDriver.ts`, `saveRecoveryBrowserDriver.ts`, `userProjectStateBrowserDriver.ts` | loaded by URL through `tests/indexedDbBrowserLifecycle.ts:112-139` | **NO — but real IndexedDB.** Headless store/persistence drivers with real `createIndexedDbProjectStorage` (`indexedDbBrowserLifecycle.ts:93-110`) and no React tree. Useful as a *persistence-only* control arm: they exercise the worker path with no renderer and no morph evaluator. |
| `tests/thumbnailCapabilityBrowserDriver.tsx`, `demandRenderingBrowserDriver.tsx` | component-level mounts | **NO.** |

Shared infrastructure worth reusing verbatim:

- `tests/viteTestServer.mjs` — a one-line `createServer` wrapper; every browser
  test starts a Vite dev server on `127.0.0.1:0` and reads
  `server.resolvedUrls.local[0]`.
- `tests/indexedDbBrowserLifecycle.ts:26-77` — per-test `BrowserContext`, fresh
  named IndexedDB, deterministic teardown, and `callDriver` (`:112-139`) which
  dynamic-imports any module by URL into the page. The
  `Function("value","return import(value)")` trick (`:97`, `:128`) is the
  supported way to pull repo modules into a live page.
- `vite.config.ts:78-87` — the `chromium` project: `fileParallelism: false`,
  `testTimeout: 30_000`, pattern `tests/**/*.browser.test.ts`. Note there is no
  Vitest browser-mode provider; every "browser test" is a Node test that
  launches Playwright itself.

### 2. Prior-campaign harness (outside the repo, reusable as-is)

`~/.mdx/TMP/cubicell-time-scout/capture.mjs` already implements the pattern the
OOM repro needs, against production preview:

- `Network.enable` / `setCacheDisabled` / `emulateNetworkConditions` (`:207-215`)
- `Emulation.setCPUThrottlingRate` (`:216`)
- `Performance.enable { timeDomain: "timeTicks" }` (`:219`) and
  `Performance.getMetrics` (`:290`) — **this is the only heap sampler that
  exists anywhere in this campaign**, and it returns `JSHeapUsedSize` /
  `JSHeapTotalSize` for the page isolate only.
- `Profiler` at 500 µs (`:220-221`, `:230`, `:289`), `Tracing.start/end` with
  IO stream drain (`:225-254`).

`scripts/measure-initial-delivery.mjs` is the in-repo equivalent but thinner:
`newCDPSession` (`:212`), `Network.*` (`:213-221`), `Emulation.*` (`:222`). No
`Performance`, no `Profiler`, no heap.

### 3. Instrumentation seams that already exist in `src`

- **`src/transport/activeTransitionPlan.ts:22-27`
  `observeActiveTransitionPlanPreparations`** — a live counter of
  `prepareSceneMorph` calls, already consumed by
  `tests/playbackFrameBrowserDriver.tsx:49-51`. This is the ready-made meter
  for hypothesis (a): plan preparations per second under loop+edit.
- **`src/transport/transportFrameObservation.ts` `observeTransportFrames`** —
  per-frame transport observations (`playbackFrameBrowserDriver.tsx:52-54`),
  giving frame delta and the `p95FrameMs` computation at `:222-225`.
- **`src/studios/editor/EditorStudio.tsx:48-50`** — `globalThis.__cubicellStore`
  is assigned **only under `import.meta.env.DEV`**. In a dev-server run the
  whole store (actions included) is reachable from `page.evaluate`. It is
  absent from `pnpm preview` / `pnpm build` output. This single fact decides
  the repro's server choice; see Procedure.
- `src/app/AppBootstrap.tsx:15` — `performance.mark("cubicell:interactive-canvas")`,
  the existing boot milestone.
- `tests/rendererDrawObserver.ts`, `tests/webGlResourceObserver.ts` — existing
  GPU-side observers, not needed here but they establish the observer idiom.

### 4. Seams for driving auto-loop and transition edits

Everything the repro needs is reachable through existing product seams. **No
new driver code inside `src` or `tests` is required.**

Auto loop:

| Seam | Location |
|---|---|
| `Loop` button, `aria-label="Loop"`, `aria-pressed={loop}` | `src/panels/motion/PieceMotionPanel.tsx:205-214` |
| `toggleLoop` — dispatches loop toggle, and when arming a windowed loop also scrubs to the window top and **starts playback** | `src/panels/motion/PieceMotionPanel.tsx:173-181` |
| Command owners `createTransportLoopToggleCommand`, `createTransportPlayCommand`, `createTransportScrubCommand` | `src/editor/commands` re-export; registry entry `transport-loop-toggle` at `src/interaction/commands/transport.commands.ts:42-48` |
| Store actions `setTransportLoop`, `toggleTransportLoop`, `setTransportLoopWindow` | `src/state/actions/transportActions.ts:9-15`, `:62` |
| Precedent for driving loop from a script | `tests/playbackFrameBrowserDriver.tsx:157-160` (`setTransportRate` / `setTransportLoop(true)` / `setTransportTime` / `setTransportPlaying(true)`) |

Transition-panel control edits:

| Seam | Location |
|---|---|
| Transition card that focuses the inspector: `aria-label="Edit transition ${n}: ${a} to ${b}"` | `src/panels/motion/PieceStateStrip.tsx:184` |
| `Snapshot current scene` (creates the states a transition needs) | `src/panels/motion/PieceStateStrip.tsx:212` |
| `TransitionInspector` → `patchTransition` → `createDocumentEditCommand({ kind: "patch-transition", ... })` | `src/panels/motion/MotionInspector.tsx:251-297` |
| The controls themselves: `Duration ms`, `Scene switch`, `Stagger ms`, `Steps` scrubs plus `Cubes` / `Order` / `Easing` segmented fields | `src/panels/motion/MorphInspector.tsx:73-141` |
| `ScrubField` resting control is a `<button aria-label="${label} value">` | `src/components/ui/scrub-field/ScrubField.tsx:149-159` |
| **Keyboard stepping**: `ArrowUp/ArrowRight` and `ArrowDown/ArrowLeft` call `stepBy` → `changeValue` → `onValueChange` | `src/components/ui/scrub-field/ScrubField.tsx:107-120` |

The keyboard path is the ideal repro actuator, for a reason that matters:
`stepBy` calls **neither `onScrubStart` nor `onScrubEnd`**
(`ScrubField.tsx:107-109` versus the pointer path at `:65-96`), so no history
batch wraps it. Each arrow key is therefore its own authored document edit with
its own full commit cycle — exactly "edited rapidly", and exactly reproducible
by count. A `ArrowUp`/`ArrowDown` pair returns the document to a byte-identical
value, which is what makes "identical repetitions" achievable.

`page.getByRole("button", { name: "Duration ms value" }).press("ArrowUp")` is
the whole actuator. The pointer-drag path (`beginScrub`, `:65-96`) is the
*human* repro and emits one edit per `pointermove`; it is the higher-rate,
less deterministic variant and belongs in a confirmation arm, not the
measurement arm.

### 5. Worker choke point — verified, with one gap

**Requests: single choke point, confirmed.** All three workers are constructed
and driven through `createWorkerRequestClient`:

- `src/state/projectCommitProjection.ts:23-38` → `projectCommitProjectionWorker.ts` (`:28`)
- `src/persistence/storageRecordPreparationAsync.ts:11-26` → `storageRecordPreparationWorker.ts` (`:16`)
- `src/persistence/projectRecordHydrationAsync.ts:16-25` → `projectRecordHydrationWorker.ts` (`:21`)

`rg "new Worker"` over `src` returns exactly those three sites and no others.
Both directions are observable inside the client: the outbound payload at
`src/shared/workerRequestClient.ts:55` (`getWorker().postMessage(payload)`) and
the inbound reply at `:28` (`created.onmessage = ({ data }) => …`). Request and
reply bytes are cheap to size because payloads are `SegmentedJson`
(`{ json: string, arrays: string[][] }`, `src/shared/segmentedJson.ts:6-9`) or a
plain string — `json.length + Σ segment.length`, no re-serialization needed.

**Replies: the choke point does not exist where the crash happens.** The
reported error is
`Failed to execute 'postMessage' on 'DedicatedWorkerGlobalScope'`, i.e. the
worker failing to clone its *result* back. Those three sites are independent
and share no helper:

- `src/state/projectCommitProjectionWorker.ts:42`
- `src/persistence/storageRecordPreparationWorker.ts:26` and `:31`
- `src/persistence/projectRecordHydrationWorker.ts:19`

Consequence for the measurement: the client-side reply hook at
`workerRequestClient.ts:28` sees every reply **except the one that crashes**,
because the throwing `postMessage` never delivers. It gives the growth trend up
to failure, not the failing size. Attributing the crash to a specific worker
requires either CDP worker-target sessions (below) or a worker-side edit, which
is out of scope this phase. Which of the three OOMs is **UNVERIFIED**;
`DedicatedWorkerGlobalScope` is the interface name for all three and does not
discriminate.

### 6. Heap measurement: what exists versus what must be added

**Nothing exists.** `rg -i "measureUserAgentSpecificMemory|jsHeap|HeapProfiler|usedJSHeapSize|collectGarbage|expose-gc|performance\.memory"` over `src`, `tests`, and `scripts` returns zero hits.

| Mechanism | Status | Note |
|---|---|---|
| CDP `Performance.getMetrics` → `JSHeapUsedSize` | Available, precedent at `~/.mdx/TMP/cubicell-time-scout/capture.mjs:290` | **Page isolate only.** Blind to worker heaps, which is where the crash is. |
| CDP `HeapProfiler.collectGarbage` | Must be added | The forced-GC primitive. Per target: must be sent on the page session *and* each worker session. |
| CDP `Runtime.getHeapUsage` | Must be added | `usedSize`/`totalSize` per execution context; the way to read a **worker's** heap once attached. |
| CDP `Target.setAutoAttach { autoAttach: true, flatten: true, waitForDebuggerOnStart: false }` | Must be added | The missing piece. Without per-worker sessions no harness in this campaign can observe the isolate that actually OOMs. |
| CDP `HeapProfiler.takeHeapSnapshot` / `startSampling` | Must be added | Only needed once retention is established and the retainer needs naming. |
| `performance.measureUserAgentSpecificMemory()` | Must be added, **likely unavailable** | Requires cross-origin isolation. Neither `vite dev` nor `vite preview` is configured with COOP/COEP headers (`vite.config.ts` sets no `server.headers`), so `crossOriginIsolated` is presumed false. **UNVERIFIED** — probe it before relying on it, and treat a `SecurityError` as expected. |
| `node --expose-gc` | Not applicable | The heap under test is Chromium's, not Node's. |

---

## Quality Map

Read-verified structural findings. None of these is a measurement; each is a
prediction the procedure is designed to confirm or kill.

### A. One keystroke ships four project-scale clones

Per authored edit, following `enqueue` → `drain`:

1. `src/state/cubicellStore.ts:77` — the authored dispatcher calls
   `durability.enqueue(applied, state)` with the **whole post-edit state**.
2. `src/state/projectDurability.ts:150-163` — `enqueue` builds a
   `DurabilityUnit` retaining that state (`createDurabilityUnit`, `:598`),
   pushes it onto `this.units`, and stages a pending write.
3. `:284` — `projectStorageCommitAsync(unit.applied, state, …)` →
   `src/state/projectCommitProjection.ts:117-130`:
   `compactProjectionState(state)` keeps `editor`, `history`, `project`,
   `userProjectState`, `workbench`
   (`src/state/projectCommitProjectionCore.ts:52-60`), then
   `stringifySegmentedJson({ … })` and `postMessage`. **Clone 1, whole
   project.**
4. `projectCommitProjectionWorker.ts:24-30` computes `projectStorageHead`,
   which builds `projectWorkbenchRecords` for the entire workbench
   (`projectCommitProjectionCore.ts:62-80`), then
   `stringifySegmentedJsonSync(commit)` and `postMessage` back. **Clone 2.**
   *This is a candidate for the crashing site.*
5. `:301` — `storage.promote(commit)` →
   `src/persistence/orderedCommitQueue.ts:216-239` →
   `prepareStorageCommitAsync(commit)` → `stringifySegmentedJson({ commit, … })`
   → `postMessage`. **Clone 3, the whole commit.**
6. `storageRecordPreparationWorker.ts:26-29` replies with
   `await stringifySegmentedJson(prepared)`. **Clone 4.** *Also a candidate.*

There is **no debounce, no coalescing, and no rate limit** anywhere on this
path. `enqueue` synchronously pushes and calls `drain` (`:156`).

### B. Two unbounded queues that retain project-scale objects

- `ProjectDurabilityRuntime.units` (`projectDurability.ts:153`) — an array;
  `drain` (`:255-314`) removes a unit only after the commit is promoted. Rapid
  edits during an in-flight drain accumulate units, each retaining a full
  `CubicellState` reference. Zustand structural sharing means the *unchanged*
  subtrees are shared, but every unit pins its own generation of every subtree
  the edit touched, and the projection cost is O(project) regardless.
- `ProjectCommitQueues.preparation` (`orderedCommitQueue.ts:230-238`) — a
  promise chain, not a queue with a bound. Each `submit` chains a closure that
  captures `commit` (a whole-project snapshot) and holds it alive until its
  turn. N rapid edits ⇒ N live commits pinned in the chain.
- `createWorkerRequestClient.pending` (`workerRequestClient.ts:22`) — a `Map`
  entry per in-flight request; cleared on reply (`:31`) or on worker error
  (`:41`). Bounded by in-flight count, not a leak by itself, but it is the
  place where a *lost* reply (the OOM case) leaves a permanently pending entry:
  `onerror` only fires for uncaught worker errors, and a `DataCloneError` thrown
  inside `onmessage` may or may not surface there. **UNVERIFIED.**

**This is the falsifiable core of hypothesis (b): heap should climb with the
number of queued-but-undrained edits, and should return to baseline after the
queue drains and GC runs. If it does not return, the retainer is one of the
three above.**

### C. The morph evaluator is invalidated by the edit, not by the frame

- `src/transport/useStagedScene.ts:132-144` — both memos key on `workbench`.
  Any authored edit produces a new workbench identity, so the source is
  re-resolved and re-sampled.
- `src/transport/activeTransitionPlan.ts:43-60` — the cache hits only when
  from/to revisions are `Object.is`-equal **and**
  `jsonValuesEqual(active.settings, sample.transition.settings)`. A duration or
  easing patch changes `settings`, so the plan is discarded and
  `prepareSceneMorph` re-runs, cost O(cells) —
  `tests/sceneMorph.bench.ts:69-71` benches exactly this at 1000 cells.
- Under loop with **no** edits, `transportTimeMs` changes per frame but the
  plan cache holds; only `sampleSceneMorph` runs per frame, allocating a new
  scene per frame.

So hypothesis (a) has two distinguishable sub-shapes: per-frame *sampling*
churn (loop alone) and per-edit *plan re-preparation* (edit alone), which
multiply under loop+edit. The 4-arm design in the procedure separates them, and
`observeActiveTransitionPlanPreparations` counts the second directly.

### D. Empty-scene trap, inherited

The boot-ownership scout §3 records that every committed-frame number in this
campaign measured **0 cells**, because `scripts/measure-initial-delivery.mjs`
uses a fresh context with an empty IndexedDB. The same trap applies here and is
worse: with 0 cells the commit payload is near-empty and the morph plan is
trivial, so an OOM repro on an empty project would measure nothing and would
"prove" no leak. **Cell count must be an explicit, asserted parameter of every
run.** `tests/playbackFrameBrowserDriver.tsx:111-116` is the precedent: a
45×45×1 = 2025-cell scene with a two-state workbench and a 60 s first
transition.

### E. Notes on the prior static conclusion

A previous static pass concluded "no leak, it plateaus". Two structural reasons
that conclusion could be wrong while looking right:

1. It would have watched the page heap. The crash is in a worker heap, which
   `Performance.getMetrics` does not report.
2. `this.preparation` and `this.units` do drain to empty when input stops, so
   heap *does* plateau once you stop typing. The crash happens while input is
   still arriving. A plateau measured after quiescence is not evidence about
   the in-flight state.

### F. Smaller observations (hygiene lens, not blockers)

- `workerRequestClient.ts:36-42` — `onerror` terminates the worker, nulls the
  handle, and rejects all pending. The next request transparently constructs a
  fresh worker (`:26-27`). A worker that OOMs is therefore silently replaced,
  and the *user-visible* symptom would be one rejected save, not an obvious
  crash. Whether the reported `Uncaught DataCloneError` reaches this handler at
  all is **UNVERIFIED** and worth capturing explicitly in the repro
  (`page.on("pageerror")` plus `worker.on("close")`).
- `parseSegmentedJsonSync` / `stringifySegmentedJsonSync`
  (`segmentedJson.ts:26-38`, `:53-58`) are used in the projection and hydration
  workers, while the preparation worker uses the yielding async variants. The
  sync variants hold both the parsed graph and the full string set live
  simultaneously — the worst moment for worker heap, and precisely the moment
  the failing `postMessage` occurs.
- `src/main.tsx:16` wraps the app in `StrictMode`; under the dev server this
  double-invokes renders and effects. Any per-render allocation count taken in
  dev is a 2× overstatement relative to production. Record which server each
  number came from.

---

## Proposed Repro Procedure

Design rules, from the brief: measure before fixing; identical repetitions;
forced GC between repetitions; heap sampled over time; worker payload bytes and
rate logged. Retention is proven by heap climbing across *identical* operations
*after* a forced GC. Churn shows as sawtooth that returns to baseline.

**Zero repo writes.** The harness lives beside the prior campaign at
`~/.mdx/TMP/cubicell-oom-scout/`, exactly as `cubicell-time-scout` did. It
needs no fixture in `tests/` because every actuator is a real product control
or a real store action.

### Server choice

Run the primary arms against **`pnpm dev`**, because
`src/studios/editor/EditorStudio.tsx:48-50` exposes `__cubicellStore` only when
`import.meta.env.DEV`, and seeding a 2025-cell two-state project through the UI
is not practical. Accept the two dev-mode costs explicitly: `StrictMode`
double-invocation, and an unbundled module graph. Then run one **confirmation
arm** against `pnpm build && pnpm preview` with a project seeded by the dev arm
and left in IndexedDB, driving only real controls, to prove the crash is not a
dev-mode artifact.

### Instrumentation, all injected, none committed

1. **Payload bytes and rate at the one choke point.** `page.addInitScript`
   that wraps the `Worker` constructor before any app module evaluates:
   patch `postMessage` to record `{ t, dir: "out", bytes, scriptUrl }` and
   install an `onmessage` property interceptor on the instance to record
   `{ t, dir: "in", bytes }`. `bytes` for a `SegmentedJson` is
   `json.length + Σ arrays.flat().map(s => s.length)`; for the hydration
   request it is `payload.length`. The worker URL discriminates which of the
   three workers each message belongs to — the discrimination the error message
   itself cannot give.
2. **Worker heaps.** On the page CDP session:
   `Target.setAutoAttach { autoAttach: true, flatten: true, waitForDebuggerOnStart: false }`.
   Keep a session per attached worker target. Per sample tick, on **every**
   session (page + each worker): `HeapProfiler.collectGarbage`, then
   `Runtime.getHeapUsage`. Log `{ t, target, usedSize, totalSize }`.
   `Performance.getMetrics` on the page session is kept as a cross-check
   against the prior campaign's numbers.
3. **Evaluator churn.** In-page, import
   `/src/transport/activeTransitionPlan.ts` by URL (the
   `Function("value","return import(value)")` idiom from
   `tests/indexedDbBrowserLifecycle.ts:97`) and register
   `observeActiveTransitionPlanPreparations` to count `prepareSceneMorph`
   calls. Same for `observeTransportFrames` to get frame deltas.
4. **Failure capture.** `page.on("pageerror")`, `page.on("console")`, and
   `context.on("weberror")` recorded to the run log, so the `DataCloneError`
   is captured with the payload-byte series that preceded it.

### Seeding (asserted, never assumed)

Via `page.evaluate` against `__cubicellStore`, using the same shapes as
`tests/playbackFrameBrowserDriver.tsx:111-117`: build a filled grid scene, a
two-state workbench, set the first transition duration long enough that the
loop stays inside one transition. Then **assert the cell count from the live
store and abort the run if it is 0.** Every reported number carries its cell
count. Wait for `hydrationStatus === "ready"` and for
`performance.getEntriesByName("cubicell:interactive-canvas").length === 1`
before the first sample.

### The four arms

Each arm: 40 repetitions, `HeapProfiler.collectGarbage` on every session
between repetitions, heap and payload logged per repetition. One repetition is
one **ArrowUp + ArrowDown pair** on `Duration ms value`, which returns the
document to a byte-identical value — that is what makes repetition 40
comparable to repetition 1.

| Arm | Loop | Edits | Isolates |
|---|---|---|---|
| 0 — idle | off | none | Instrument baseline and drift. |
| 1 — edits only | off | 40 pairs | Hypothesis (b) alone: the persistence clone path. |
| 2 — loop only | on, playing | none | Hypothesis (a) alone: per-frame sampling churn, plan cache holding. |
| 3 — loop + edits | on, playing | 40 pairs | The reported crash configuration. |

Then arm 4, the **rate sweep**: repeat arm 3 with inter-edit delays of 250 ms,
100 ms, 50 ms, 16 ms. The queue-retention prediction (Quality Map B) is that
peak heap scales with edits-arriving-per-drain, so heap should be flat at
250 ms and climb sharply below the drain period. If the crash reproduces only
in this arm, it is a rate-dependent queue problem, not a leak.

Finally arm 5, the **live-shape confirmation**: pointer-drag the same scrub
(`ScrubField.tsx:65-96`) rather than keyboard-stepping it, at human speed, with
loop on. This is the owner's actual gesture; it emits one edit per
`pointermove` and adds the history batch the keyboard path skips.

### Reading the result

- Heap after GC climbs monotonically across the 40 identical pairs in arm 1
  or 3 ⇒ **retention**, and the arm-4 sweep plus the per-target heap series
  names which isolate holds it.
- Heap sawtooths and returns to its arm-0 baseline after each GC, while
  payload bytes per second stay high ⇒ **churn**, and the plan-preparation
  count separates evaluator churn from clone churn.
- Arm 2 flat and arm 1 climbing ⇒ (b) alone. Arm 2 climbing and arm 1 flat ⇒
  (a) alone. Both climbing ⇒ the two compound and the fix order is decided by
  the byte series, not by preference.
- If no arm reproduces the crash, the missing variable is scene size or
  project history depth; re-run arm 3 with the cell count and the state count
  swept, and **report non-reproduction as non-reproduction**, not as absence
  of a leak. The static "no leak, it plateaus" conclusion already failed once
  that way.

### Commands

```bash
# primary arms, dev server (needed for __cubicellStore)
cd /Users/alphab/Dev/LLM/DEV/helioy/cubicell/.claude/worktrees/performance-audit
pnpm dev --host 127.0.0.1 --port 45173 --strictPort

node ~/.mdx/TMP/cubicell-oom-scout/capture.mjs \
  --origin http://127.0.0.1:45173 \
  --cells 2025 --states 2 \
  --arm idle       --reps 40 --out ~/.mdx/TMP/cubicell-oom-scout/run/arm0
node ~/.mdx/TMP/cubicell-oom-scout/capture.mjs --origin http://127.0.0.1:45173 \
  --cells 2025 --arm edits     --reps 40 --out ~/.mdx/TMP/cubicell-oom-scout/run/arm1
node ~/.mdx/TMP/cubicell-oom-scout/capture.mjs --origin http://127.0.0.1:45173 \
  --cells 2025 --arm loop      --reps 40 --out ~/.mdx/TMP/cubicell-oom-scout/run/arm2
node ~/.mdx/TMP/cubicell-oom-scout/capture.mjs --origin http://127.0.0.1:45173 \
  --cells 2025 --arm loop+edits --reps 40 --out ~/.mdx/TMP/cubicell-oom-scout/run/arm3

# rate sweep
for d in 250 100 50 16; do
  node ~/.mdx/TMP/cubicell-oom-scout/capture.mjs --origin http://127.0.0.1:45173 \
    --cells 2025 --arm loop+edits --reps 40 --edit-delay-ms $d \
    --out ~/.mdx/TMP/cubicell-oom-scout/run/arm4-$d
done

# production confirmation, real controls only, no store handle
pnpm build && pnpm preview --host 127.0.0.1 --port 44173 --strictPort
node ~/.mdx/TMP/cubicell-oom-scout/capture.mjs --origin http://127.0.0.1:44173 \
  --arm loop+edits --reps 40 --ui-only --out ~/.mdx/TMP/cubicell-oom-scout/run/prod

node ~/.mdx/TMP/cubicell-oom-scout/analyze.mjs \
  ~/.mdx/TMP/cubicell-oom-scout/run \
  ~/.mdx/TMP/cubicell-oom-scout/summary.json
```

Existing repo gates, for a clean-tree check before and after (they do not
measure heap and are not part of the result):

```bash
pnpm test                      # unit project
pnpm test:browser              # chromium project, fileParallelism false
git status --short --branch
```

### What this procedure deliberately does not do

- It does not add a fixture. Every actuator is a shipped control
  (`ScrubField` button, `Loop` button, transition card) or a shipped store
  action. A fixture here would certify the fixture.
- It does not instrument the worker reply sites. That needs three `src` edits
  and belongs to the fix phase, once the measurement says which worker.
- It does not conclude anything. The first deliverable is the four-arm heap
  and byte series; hypotheses (a) and (b) are adjudicated by that data.

---

## Conditions

- Repo baseline: `docs/performance-audit` @ `60da3f7`, `git status --short`
  clean at the time of reading.
- Playwright `^1.61.1` (`package.json`); prior campaign used headless Chromium
  `143.0.7499.4`.
- Read-only pass. No files in `src` or `tests` were modified. No commands
  beyond `git status`, `ls`, `wc`, and `rg` were run; **no browser was
  launched and no measurement was taken.**
- Prior art read before scouting:
  `~/.mdx/projects/cubicell-scout-time-budget.md`,
  `~/.mdx/projects/cubicell-scout-boot-ownership.md`.

---

## Proposals

Phase 2. The instrumented-repro plan above is cancelled; the procedure section
is retained as the record of what was mapped, not as work to do. Scope here is
the **failure-mode surface** plus the worker reply asymmetry. Persistence queue
retention and evaluation/input coalescing belong to other seats and are not
proposed on. Still zero writes to `src` or `tests`.

Each defect below is defensible without reference to the OOM's root cause: they
are all bugs in what the app does once *any* save fails.

### P1 — The blocking modal leaves the transport running

- **Defect**: entering a failed save state covers the viewport with a fixed,
  full-bleed `role="alertdialog"`
  (`src/app/PersistenceStatus.tsx:10-18`, `src/app/persistence-status.css:17-25`
  `position: fixed; inset: 0`) while nothing in the five sites that set the
  failed state (`src/state/projectDurability.ts:159-162`, `:325-327`,
  `:340-345`, `:370`, `:393`) touches `editor.transport`, so an auto-loop keeps
  playing behind the dialog and the Loop and Pause controls that would stop it
  are now unreachable.
- **Why it is wrong on its own terms**: this codebase already decided that
  entering an exclusive mode stops the transport.
  `setMorphScrub` (`src/state/actions/transportActions.ts:35-46`) forces
  `playing: false, timeMs: null` when a comparison starts, and
  `src/transport/useStagedScene.ts:54-58` documents the rule: "starting a
  comparison stops the transport, so a live scrub can never race an armed
  clock (the store enforces the exclusion)". An unrecoverable-save dialog is a
  strictly stronger exclusive mode than a comparison scrub — it is modal by
  construction — and it is the only one that does not enforce the exclusion.
  Independently: a running transport samples the morph evaluator every frame
  against a workbench the user can no longer commit, which is work with no
  possible destination.
- **Minimal fix**: stop the transport when the save state becomes `failed` or
  `recovery-failed`. The failed state is already constructed in exactly one
  module (`src/state/projectDurabilitySaveState.ts:15`, `:29`, `:4`), so the
  five setter sites do not each need editing — but the *store write* is what
  must carry the exclusion, not the constructor.
- **Elegant fix**: give the store one `setSaveState` action, placed with the
  other transport exclusions in `createTransportActions`
  (`src/state/actions/transportActions.ts:33`), that applies
  `withTransportPlaying(transport, false, durationMs)` (`:20-31`, already
  exported and already the shared shape) whenever the incoming status is
  `failed` or `recovery-failed`. The durability runtime then calls that action
  instead of `this.store.setState({ saveState })` at its five sites. The rule
  lands next to the rule it mirrors, and the durability runtime stops writing
  editor-session state it does not own.
  Keep the dialog blocking: it is a data-loss decision, and a non-blocking
  banner would let further edits pile onto a branch that cannot commit —
  `authoredDispatcher.ts:39` already refuses them, so a non-blocking dialog
  would present controls that silently do nothing (that is P4).
- **Owner of the decision, in code**: `createTransportActions`
  (`src/state/actions/transportActions.ts:33`). `PersistenceStatus.tsx` is
  presentational and must not own it; it reads `saveState` and renders. The
  transport-stop rule already lives in the store and belongs there.
- **Blast radius**: `src/state/actions/transportActions.ts` (one action),
  `src/state/projectDurability.ts` (five call sites become one action call),
  `src/state/actions/types.ts` (action type). Behaviour change is visible to
  `tests/persistenceStatus.test.tsx` and any test asserting transport state
  across a save failure. No new state: `saveState` and `editor.transport`
  both already exist.
- **Recommendation**: ship. It is the smallest change with the largest
  reduction in user harm, and it reuses `withTransportPlaying` verbatim.

### P2 — The escape hatch is present but not operable

- **Defect**: DISCARD is silently dropped unless it lands while
  `saveState.status === "failed"` — `recoverToLastCommitted` returns early on
  `this.closed || this.recovering || status !== "failed"`
  (`src/state/projectDurability.ts:356-358`) — while the sibling RETRY button
  synchronously flips the status to `"saving"`
  (`src/state/projectDurability.ts:352`), which unmounts the entire dialog
  (`src/app/PersistenceStatus.tsx:10`) until the retry fails and remounts it.
- **Why it is wrong on its own terms**: a control that is rendered, enabled,
  and clickable must either act or say why it did not. `recoverToLastCommitted`
  has three separate silent-return conditions and no feedback path for any of
  them; the DISCARD button carries no `disabled` binding at all
  (`PersistenceStatus.tsx:45-47`) while RETRY does (`:38`). The dialog also
  neither autofocuses nor traps focus, so no keyboard route to the button is
  guaranteed. This is wrong whether or not the main thread is starved.
- **Mechanism split**: the guard-plus-remount cycle above is **verified from
  code** and is sufficient on its own to require many clicks. Whether main-thread
  starvation was the dominant contributor live is **UNVERIFIED** — establishing
  that was the cancelled measurement's job, and I will not assert it.
- **Minimal fix**: make the dialog's mount condition independent of the
  in-flight status. Latch the dialog open once a failure is entered and close
  it only on a resolved outcome, so a retry attempt does not unmount the escape
  hatch mid-gesture; and mirror RETRY's `disabled` binding onto DISCARD so a
  click that cannot act is visibly unavailable rather than silently dropped.
- **Elegant fix**: additionally route the escape hatch through the input path
  that does not depend on React committing the dialog. It already exists:
  `src/editor/keyboard/KeyboardShortcuts.tsx:20-74` installs a
  document-level capture keydown listener that dispatches commands on the
  `synchronous` lane (`src/interaction/commands/transport.commands.ts:7`, `:19`,
  `:56`), which is precisely the lane built for input that must land under
  load. `space` is already bound to `transport.play.toggle`
  (`src/editor/keyboard/keymap.ts:83`,
  `src/editor/affordances.ts:382-386`), so **the app already ships a
  transport kill switch that works with the viewport covered** — it is simply
  never mentioned by the dialog, and it is suppressed whenever focus sits on a
  button, because `isButtonKeyboardActivation`
  (`src/editor/keyboard/keyboardEventGuards.ts`, cited from
  `KeyboardShortcuts.tsx:30-32`) hands Space to the focused button. Naming the
  shortcut in the dialog copy and keeping focus off the buttons until the user
  moves it there converts an existing capability into a working escape hatch
  with no new machinery. Note that P1 makes this moot for the loop case by
  stopping the transport before the dialog appears; P2 remains necessary for
  the dialog's own buttons.
- **Blast radius**: `src/app/PersistenceStatus.tsx` (mount condition, one
  `disabled` binding, copy), `src/state/projectDurability.ts:356-358` (report
  the refusal instead of returning bare). `tests/persistenceStatus.test.tsx`
  will need updating. No new state management; the latch is derivable from
  `saveState` plus the existing `recovering` flag.
- **Recommendation**: ship the minimal fix with P1. Defer the keyboard-copy
  half until someone can confirm the focus behaviour in the live app — the
  suppression rule is verified, the live focus position is not.

### P3 — "Project recovery unavailable" is a dead end

- **Defect**: the `recovery-failed` branch renders a title, a message, and
  "No unsaved work was discarded." with **no actions at all** —
  `src/app/PersistenceStatus.tsx:29-30` versus the `failed` branch's action row
  at `:36-48` — leaving page refresh as the only exit from a full-viewport
  modal.
- **Why it is wrong on its own terms**: the state is reached from exactly one
  place, `recoveryFailureSaveState(error)` at
  `src/state/projectDurability.ts:370`, which fires when
  `preflightCommittedRecovery` throws — that is, when the *preflight* could not
  verify the last committed state. The runtime explicitly returns before
  touching storage (`:371`), so nothing has been discarded and nothing is
  corrupt; the unsaved work is still in memory and the committed branch is
  still on disk. A recoverable situation is being presented as terminal. The
  copy already says so ("No unsaved work was discarded") and then offers no way
  to act on it.
- **Minimal fix**: offer "Try recovery again" bound to the existing
  `recoverToLastCommitted` action (`src/state/cubicellStore.ts:112`), gated so
  it can re-enter from `recovery-failed` — today `:357` admits only `failed`,
  which is why the state is absorbing. The preflight is idempotent and its
  failure may be transient (an IndexedDB read), so re-running it is the
  correct first offer.
- **Elegant fix**: the same button plus "Continue without saving", which
  dismisses the dialog and leaves the session live and explicitly unsaved. The
  user's work is intact in memory; the honest options are *retry the
  verification* or *keep working, knowing saves are down*. Both reuse existing
  actions; neither needs new state, since "dismissed" is the same dialog latch
  P2 introduces.
- **Blast radius**: `src/app/PersistenceStatus.tsx` (one action row, reusing
  the existing `.persistence-failure-actions` grid at
  `persistence-status.css:53-56`), `src/state/projectDurability.ts:357` (widen
  the admitted status). `tests/persistenceStatus.test.tsx`.
- **Recommendation**: ship the minimal fix. Take the "Continue without saving"
  half only if the owner wants it — it is a product call about whether an
  unsaveable session should stay editable, not an engineering one.

### P4 — Authored edits latch off silently

- **Defect**: local authored edits are refused with no signal whenever
  `pendingRecovery` is true or `saveState.status === "failed"` —
  `src/state/actions/authoredDispatcher.ts:37-40` returns the state unchanged,
  and `src/state/actions/checkpointDispatcher.ts:25-30` does the same — and
  `pendingRecovery` is set by `applyProjectPendingHydration`
  (`src/state/projectPendingHydration.ts:42`, `:57`) in a path whose save
  status is `"saving"`/`"syncing"`, **not** `"failed"`, so the dialog is absent
  and the only visible state is the small "SAVING"/"SYNCING" readout
  (`src/app/PersistenceStatus.tsx:56-63`).
- **The stuck latch, identified**: `pendingRecovery` clears only when another
  hydration publish runs with an empty pending set — `committed` carries
  `pendingRecovery: false` (`src/state/projectDurabilityHydration.ts:142`) and
  `applyProjectPendingHydration` short-circuits on `pending === null`
  (`projectPendingHydration.ts:15`). The re-publish is triggered from inside
  `publishHydration` (`src/state/projectDurability.ts:226-230`) or after a
  drain empties (`:315-321`). Both are unreachable while `this.blocked` is
  true, because `drain` returns immediately at `:256`. So a failure that sets
  `blocked` alongside `pendingRecovery` latches authored editing off with no
  dialog and no route back.
- **What "knocks it loose"**: `checkpointUserProjectState`
  (`src/state/projectDurability.ts:131-141`) is the one durability entry point
  that does **not** apply the `pendingRecovery` guard the two dispatchers
  apply. It is called from the editor actions on unrelated session changes
  (`src/state/cubicellStore.ts:105-107`), pushes a unit, and — when `blocked`
  has since cleared — sets `saving` and drains, which reaches the re-publish
  that clears the flag. An unrelated editor change is therefore exactly the
  channel that restores editing, which matches the reported symptom. Two
  dispatchers guard on `pendingRecovery`, one does not; that asymmetry is the
  defect, independent of anything else here.
- **Why it is wrong on its own terms**: a refusal that returns the identical
  state object is indistinguishable from a no-op input. The control snaps back
  to its store value (`ScrubField` renders `value` from props,
  `src/components/ui/scrub-field/ScrubField.tsx:158`) and nothing anywhere
  tells the user the edit was rejected. Silent rejection of user input is a
  defect at any root cause.
- **Minimal fix**: make the refusal visible. Both dispatchers already detect
  it at a single line each; surface it through the existing save-state readout
  (`PersistenceStatus.tsx:56-63`) so `pendingRecovery` reads as a distinct
  "recovering, editing paused" status rather than an indefinite "SYNCING".
- **Elegant fix**: additionally close the escape from `blocked`. Either apply
  the same guard to `checkpointUserProjectState` so all three entry points
  agree (and the flag never clears by accident), or make the re-publish reachable
  when blocked clears, so the latch has one deliberate exit instead of one
  accidental one. Choosing between those two is queue-lifecycle work and
  therefore the persistence seat's call, not mine; the guard asymmetry is the
  finding I hand them.
- **Blast radius**: `src/app/PersistenceStatus.tsx` (one status branch) is
  self-contained. The guard-symmetry half touches
  `src/state/projectDurability.ts:131-141` and interacts with the drain
  lifecycle, so it must be sequenced with the persistence seat's work.
- **Recommendation**: ship the visibility half now; hand the guard asymmetry to
  the persistence seat rather than fixing it here.

### P5 — Worker replies have no shared boundary

- **Defect**: requests funnel through one client
  (`src/shared/workerRequestClient.ts:16-62`, all three workers constructed at
  `:27` from `src/state/projectCommitProjection.ts:28`,
  `src/persistence/storageRecordPreparationAsync.ts:16`,
  `src/persistence/projectRecordHydrationAsync.ts:21`), while replies are three
  independent `postMessage` sites with no shared helper —
  `src/state/projectCommitProjectionWorker.ts:42`,
  `src/persistence/storageRecordPreparationWorker.ts:26` and `:31`,
  `src/persistence/projectRecordHydrationWorker.ts:19`.
- **Why it is wrong on its own terms** (three counts, none of which needs the
  crash):
  1. **Duplication.** Two of the three workers hand-build a byte-identical
     error envelope — `projectCommitProjectionWorker.ts:33-41` and
     `storageRecordPreparationWorker.ts:30-38` are the same eight lines with a
     different result key. The response types are the same envelope three
     times: `{ id, commit?, error? }`, `{ id, prepared?, error? }`,
     `{ id, result }`.
  2. **The third worker has no error handling at all.**
     `projectRecordHydrationWorker.ts:17-30` has no `try`, so any throw becomes
     an uncaught worker error, reaches `created.onerror`
     (`workerRequestClient.ts:36-42`), and terminates the worker and rejects
     every pending request — where the other two would have replied with a
     typed error and lost only their own request. Same contract, three
     different failure semantics.
  3. **The client's contract is asymmetric.** It defines `resolveResponse` for
     the reply but owns nothing on the worker side that produces it, so the
     invariant "every request receives exactly one reply carrying its id" is
     asserted in one module and implemented in three.
- **Minimal fix**: extract the shared error envelope and the
  `{ id, … } | { id, error }` response type into the existing protocol modules,
  and give the hydration worker the `try`/`catch` the other two already have.
  That alone removes the duplication and equalises the three failure semantics.
- **Elegant fix**: a `createWorkerResponder` in `src/shared/`, sibling to
  `createWorkerRequestClient` and the mirror of it: it owns `onmessage`,
  request parsing, invoking the handler, replying, and building the error
  envelope. Each worker becomes its handler function plus one registration
  call, and the request/reply contract is stated once in one file.
- **What it would have made possible here**: the reply that OOMs is thrown by
  `postMessage` itself, inside the worker's own message handler
  (`DedicatedWorkerGlobalScope`). With a responder owning that call, the throw
  is caught at the boundary and answered with an error envelope carrying the
  request id — the pending promise rejects with a real message, the existing
  main-thread synchronous fallbacks stay available
  (`projectCommitProjection.ts:114-116`,
  `storageRecordPreparationAsync.ts:32-34`,
  `projectRecordHydrationAsync.ts:32-36`), and the save fails one commit at a
  time. Today the same throw escapes the handler, kills the worker, rejects
  every pending request at `workerRequestClient.ts:40`, and the worker is
  silently reconstructed on the next request (`:26-27`). **A reply that OOMs
  currently kills the worker instead of degrading, and that is a property of
  the missing boundary, not of the payload size.** It is also the reason the
  crash surfaced as an uncaught `DataCloneError` rather than as a save error.
- **Blast radius**: three worker files plus their three protocol modules; the
  client is unchanged, since `resolveResponse` already discriminates on the
  error field. No product behaviour changes on the success path. Covered by
  the existing persistence tests; the hydration worker's new catch is
  currently untested territory (`rg` finds no test asserting worker-throw
  behaviour for any of the three, so the fix should bring one).
- **Recommendation**: take the minimal fix now (it is small, and the hydration
  worker's missing `catch` is a live defect on its own), and the responder
  when someone next touches worker code. Do not bundle it with P1-P4: different
  layer, different reviewer.

### Ranking

By (user harm × confidence) / cost:

| # | Harm | Confidence | Cost | Note |
|---|---|---|---|---|
| **P1** transport keeps running behind the modal | High — the loop keeps producing the pressure while the relief control is covered | High — precedent and helper both exist (`setMorphScrub`, `withTransportPlaying`) | Very low — one action, five call sites collapse into it | **Ship first** |
| **P4** silent authored-edit latch (visibility half) | High — app reads as broken, no error shown | High — guard and clearing path both read directly | Low for the readout; the guard asymmetry is another seat's | Ship the readout with P1 |
| **P3** recovery dead end | Medium — refresh is the only exit, but the state is rarer | High — one branch, one action, no side effects | Very low | Ship with P1 |
| **P5** reply asymmetry (minimal half) | Medium — one worker's throw rejects every pending request | High — duplication and the missing `catch` are on the page | Low minimal / medium responder | Separate change |
| **P2** escape hatch operability | High — but the dominant live mechanism is unverified | Medium — the guard-and-remount cycle is verified; starvation's share is not | Medium | Minimal half with P1; keyboard copy deferred |

**Ship first: P1.** Stopping the transport when a save fails is the only item
that reduces harm during the incident rather than after it, it is the cheapest
change on the list, and it makes the app obey a rule it already wrote down for
the weaker case. Every other item improves how the user escapes the failure;
P1 stops the app from making the failure worse while they try.

