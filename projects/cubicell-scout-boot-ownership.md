# Cubicell boot ownership scout

Scope: code-side map for the runtime profiler. Baseline main @ `60da3f7`, tree clean, fmm index regenerated at that head. All citations are `file:symbol`. Companion scout owns the actual timings; this report is where those timings should be attributed.

## 1. Boot path ownership map

Ordered from navigation to `cubicell:interactive-canvas`. Each entry: what it does, what it blocks.

| # | Owner | Does | Blocks |
|---|-------|------|--------|
| 1 | `viteStudioPreloads.ts:studioPreloadPlugin` | Build-time injects into `dist/index.html`: startup indicator markup (the LCP candidate) and an inline head script that adds `modulepreload` links for the Editor + renderer closure, a streaming progress fetch (hybrid mode, Chromium only), and stylesheet links. | Nothing; it front-loads transfer so later awaits are warm. Source `index.html` has none of this; it exists only in the built artifact. |
| 2 | `src/main.tsx` (module scope) | Evaluates bootstrap chunk: fonts, `index.css`, then `beginRouteLoad(location.pathname)` before render. | First React render of `AppBootstrap`. |
| 3 | `src/studios/catalog.ts:beginStudioLoad` | Starts `import("./editor/EditorStudio")` and `import("../renderer/SharedRendererModule")` concurrently. Chains on `globalThis.__cubicellRoutePreload` only in stream mode; hybrid/native start immediately. | Everything downstream waits on `Promise.all` of these two. |
| 4 | `src/app/AppBootstrap.tsx:AppBootstrap` | Owns the `StudioLifecycle`: `rendererCreated` sets indicator phase "scene"; `interactive` marks `cubicell:interactive-canvas` and removes the indicator. Delegates to `StudioHost`. | Indicator handoff semantics. |
| 5 | `src/studios/StudioHost.tsx:StudioHost` | Awaits `session.modules`, renders `null` until both chunks are evaluated, then mounts `Studio`. | Editor mount on the slower of Editor and renderer transfer+evaluation. |
| 6 | `src/state/cubicellStore.ts` (module scope) | Evaluating the Editor chunk runs `createCubicellStore` at module scope via `retainBrowserRuntime`: `loadCubicellPreferences` (sync localStorage), `createInitialCubicellState`, zustand store assembly, `createProjectDurabilityCoordinator`, and `durability.hydrate()` fires immediately. `src/studios/editor/EditorStudio.tsx` also runs `registerAllCommands()` at module scope. | Store exists before first Editor render; hydration begins during chunk evaluation, concurrent with renderer chunk arrival. |
| 7 | `src/state/projectDurability.ts:createProjectDurabilityCoordinator` (`hydrate` → `publishHydration`) | Opens IndexedDB (`src/persistence/indexedDbProjectStorage.ts:createIndexedDbProjectStorage`), reads hydration bytes, hands decode to `src/persistence/projectRecordHydrationAsync.ts:hydrateProjectRecordsAsync` (worker), applies via `src/state/projectDurabilityHydration.ts:applyHydratedRecords`, sets `hydrationStatus: "ready"`. | `src/studios/editor/EditorStudio.tsx:Studio` returns `null` while `hydrationStatus === "loading"`, so the entire editor shell and canvas wait on hydration. |
| 8 | `src/studios/editor/EditorStudio.tsx:EditorApp` | Mounts shell: `useEditorAppModel`, `StudioShell`, panels, keypad, keyboard, and the four lazy capability owner models (all absent at boot). | First render of `EditorCanvas`. |
| 9 | `src/studios/editor/EditorRendererBinding.tsx:EditorRendererBinding` → `src/scene/CubeScene.tsx:CubeScene` | Binds store subscriptions to the injected `renderer.Canvas` and mounts the R3F `<Canvas>`: WebGL context creation (`onCreated` → `lifecycle.rendererCreated`), demand frameloop. | First frame; shader program compilation happens at first render. |
| 10 | `src/scene/useCubeSceneInstances.ts:useCubeSceneInstances` → `src/scene/incrementalCubeSceneOwner.ts:createIncrementalCubeSceneOwner` (`createOwnerState`) | Cold full-sync scene construction: layout (`src/domain` `createSceneGridLayout` via `src/scene/useStableGridLayout.ts:useStableGridLayout`), per-cell `createCellEntry` → `src/scene/cubeInstances.ts:createCubeCellInstances`, collect, slot registry. | The instance buckets the meshes upload. |
| 11 | `src/scene/InstancedPartMesh.tsx:InstancedPartMesh` → `src/scene/instancedPartMeshCore.ts:syncInstancedPartMesh` | Mount-time full buffer population across ~9 production meshes plus `src/scene/EdgeCoverageLayer.tsx:EdgeCoverageLayer` and `src/scene/SelectionChromeLayer.tsx:SelectionChromeLayer`. | GPU upload of the first frame. |
| 12 | `src/renderer/RendererCommitDriver.tsx:RendererCommitDriver` | R3F `addAfterEffect` after the first frame with `sceneReady` → `onSceneFrameCommitted` → `lifecycle.interactive()`: `performance.mark("cubicell:interactive-canvas")`, indicator removed, then `motion.afterInteractive` / `panelDrag.afterInteractive` may begin lazy loads. | This is the committed-frame milestone the budgets time. |

Chain shape: transfer (1) overlaps evaluation (2 to 6); hydration (7) overlaps nothing downstream because Studio hard-gates on it; 8 to 12 are strictly sequential after hydration publishes. The profiler should expect the critical path to be max(editor chunk, renderer chunk) evaluation → hydration → mount → construct → compile → commit.

## 2. What is already measured and claimed

Sources: `~/.mdx/projects/cubicell-initial-delivery-strategy.md` (campaign), `docs/slice4-plan.md` (last plan), `PERFORMANCE.md` (ledger), `budgets/initial-delivery.json` (ratchet, schema 5).

### Measurements (exact, provenance recorded)

- Original head `27813ba`: 468.09 KB gzip single entry; Lighthouse locked profile median LCP 4.043 s, largest task median 113 ms, cold run largest task 535 ms, script evaluation 1,003 ms of 1,327 ms main-thread work. Playwright trace: startup script done 3.626 s, 144 ms task at 3.639 s, shell 3.808 s.
- Slice 1 committed-frame baseline: median 4,660.9 ms at `28f357e` (in the budget file, target 3,000).
- Slice 3 historical committed frame: 4,485.5 ms at `0f86f62`.
- Slice 4 (`f7f7db2` base vs candidate, PERFORMANCE.md "Slice 4 measured result"): default closure 437,280 → 430,311 B (−6,969), Editor 374,387 → 364,066 B, renderer 398,195 → 401,874 B (+3,679). Committed frame 4,480.4 → 4,446.0 ms (−34.4). Max main-thread task 426 → 442 ms (+16). TBT 442 → 453 ms. Indicator LCP passes; 3.0 s and 100 ms targets recorded red.
- Current ratchet (budget file, zero-headroom by policy): default-interactive 430,773 B, editor 364,544 B, renderer 402,185 B, bootstrap 62,605 B. Note drift: the ledger's 430,311 B predates #133/#134 re-baselines; the ratchet is the live number.
- Two shared Three modules: 228,755 B attribution, classified `anchoredByDesign` with four camera-math anchor roots. 0 B of it is claimed removable.

### Claims that are ESTIMATES, not measurements

1. **Non-Motion panels ~29.46 KB** (Slice 5 owner 1). Isolated visualizer gzip *attribution* computed at the original `27813ba` graph (983 modules, Vite 8.1.3), by subtracting the Motion group from `src/panels`. Never re-measured after Slices 1 to 4 reshaped the graph (1,007+ modules, Motion gone from panels). Attribution is a ranking metric; it does not sum to emitted gzip.
2. **Optional persistence ~3.14 KB** (`src/persistence/memoryProjectStorage.ts`, Slice 5 owner 2). Same vintage attribution. The module is confirmed still cold: statically imported by `src/state/cubicellStore.ts` as the no-IndexedDB fallback.
3. **Attribution overstates emitted, measured twice.** DnD: 51.61 KB attribution → 29.54 KB emitted chunk (Slice 3 record). Motion+thumbnails: 15,304 B attribution → 6,969 B net default-closure reduction (Slice 4 record, partly because the renderer closure grew 3,679 B in the same change).
4. **Reachability of the product ceilings.** The strategy itself flags this: "Slice 5 treats the remaining gap to the product ceilings as unproven residual closure." No measurement supports 350 KB / 3.0 s / 100 ms being reachable from the named owners. See section 5 for the arithmetic.
5. **The 442 ms max task has no decomposition.** The only phase attribution on record is Lighthouse's script-evaluation split at the original pre-split head. Nothing attributes today's largest task to chunks, hydration, mount, construction, or compile. That attribution is exactly what the parallel profiler should produce.

### Ratchets versus product ceilings

Temporary ratchets (budget file, re-baselined to measured value at zero headroom every time bytes move): the byte ceilings above plus committed-frame baseline runs. Product ceilings (strategy, PERFORMANCE.md acceptance gates): 350 KB gzip editor cold, 2.5 s indicator LCP (currently passing), 3.0 s committed frame, 100 ms max initial task, 200 ms TBT. CI (`delivery-budget.yml`) enforces the static byte/ownership gate only; timing is local proof via `scripts/measure-initial-delivery.mjs`, and the two timing ceilings are recorded red, not blocking.

## 3. Scene construction: is cold boot gated?

**No. `tests/incrementalScene.browser.test.ts` does not gate cold-boot scene construction. It deliberately waits it out.**

Evidence, from `tests/incrementalSceneBrowserDriver.tsx:runIncrementalSceneBrowserGate`:

- The driver mounts, then waits for `mode === "full-sync"` plus mesh-upload quiescence purely as a *settling precondition*. Mutations observed before that point are counted into a discarded `initialMutationCount`; `collecting = true` only afterward.
- `elapsedMs` starts at the authored edit, after the cold construction completed. Every assertion (patch mode, write counts, uploaded bytes, ranges, full-sync count 0) is about the incremental edit. The GPU test likewise baselines *after* initial quiescence.
- The fixture is not the boot path: `tests/incrementalSceneProductionTree.tsx` mounts `EditorRendererBinding` + `CubeScene` directly with a test interaction core, `createMemoryProjectStorage`, and a pre-reset detached workbench. No bootstrap, no preload, no IndexedDB, no hydration worker, no `StudioHost`, no `EditorApp` shell (the fixture-certifies-fixture caveat applies).

So the only paths exercising cold full-sync at scale (250 and 2,025 cells) treat its cost as unbounded setup. Nothing anywhere asserts a bound on `createOwnerState` time, first-sync buffer population, or any cold-boot task length. Separately, the committed-frame measurement runner (`scripts/measure-initial-delivery.mjs`) launches a *fresh browser context per run*: empty IndexedDB, empty project, zero cells. **Every committed-frame and max-task number in the record measures an empty scene.** Cold-boot scene construction at real project sizes is both un-gated and un-measured. At 2,025 cells the construction is O(cells × ~18 parts) with two `Matrix4` constructions and multiplications per part, in one uninterrupted block (section 4, item 6).

## 4. Work-shaped suspects (candidates for the profiler, not conclusions)

Synchronous main-thread blocks on the boot path, with their scheduling shape:

1. **Chunk evaluation of the ~430 KB gzip default closure** — `shared-renderer-core` (Three), `initial-shared`, editor, renderer chunks (`vite.config.ts` codeSplitting groups). One uninterrupted block per chunk by nature. The only measured evaluation figure is 1,003 ms at the pre-split head; the 535/442 ms tasks are consistent with this owner. Anchored by design; bytes can shrink but evaluation cannot be chunked.
2. **Module-scope store creation** — `src/state/cubicellStore.ts` top level: sync localStorage preference read, initial state, store assembly, coordinator creation. One block inside editor-chunk evaluation. Small individually; it rides inside suspect 1's task.
3. **Hydration request serialization** — `src/persistence/projectRecordHydrationAsync.ts:hydrateProjectRecordsAsync` does `JSON.stringify({ records, seed, … })` on the main thread before posting to the worker. One uninterrupted block, O(project bytes).
4. **Hydration response assembly** — `src/shared/segmentedJson.ts:parseSegmentedJson` is chunked (yields every 128-element segment via `src/shared/taskYield.ts:yieldToMain`), but the trailing `restoreSegmentedArrays` graph walk is one unchunked block, O(state).
5. **Hydration publish** — `src/state/projectDurabilityHydration.ts:applyHydratedRecords` → `setState` flips `hydrationStatus`, which renders the entire editor shell in one React commit. One block, O(shell).
6. **Cold full-sync scene construction** — `src/scene/incrementalCubeSceneOwner.ts` `createOwnerState`: occupancy index, per-cell `createCubeCellInstances` (up to 6 faces + 12 edges + hit targets, each two `Matrix4` multiplies), `collectCubeSceneInstances`, slot owner. One uninterrupted block, O(cells). Zero in the measured empty-scene runs; the dominant scaling risk on real projects.
7. **First mesh sync** — `src/scene/instancedPartMeshCore.ts:syncInstancedPartMesh` across ~9 meshes plus edge coverage and selection chrome. One block per mesh, O(instances). Same empty-scene caveat.
8. **WebGL context creation and first-frame shader compilation** — R3F `<Canvas>` mount in `src/scene/CubeScene.tsx` (logarithmic depth buffer materials). Browser-owned single blocks; `rendererCreated` fires at context creation, compile lands at first frame.
9. **Deferred by design, confirmed absent at boot** — motion, thumbnails (idle-deferred WebGL retained), panel drag, recording (`src/capabilities/catalogData.ts:capabilityCatalogData` owners), camera motion (first eased command via the renderer authority port), design system. These are the campaign's wins; the profiler should confirm zero requests before their triggers, which the ownership gate already asserts statically.

Nothing on the boot path is idle-scheduled or time-sliced except the segmented JSON parse (item 4, partially). There is no yield between hydration publish, shell mount, scene construction, and first frame; if hydration resolves after the chunks are evaluated, items 5 through 8 can coalesce into few large tasks.

## 5. Falsifiable condition for Slice 5

Slice 5's named extraction: ~29.46 KB (non-Motion panels) + ~3.14 KB (optional persistence) ≈ 32.6 KB of *isolated attribution*. The gaps: max task 442 ms vs 100 ms ceiling (−342 ms needed) and committed frame 4,446 ms vs 3,000 ms (−1,446 ms needed).

**Condition: Slice 5's byte extraction closes the two timing ceilings only if the profiler attributes at least 1,446 ms of the committed-frame critical path, and at least 342 ms of every over-ceiling task, to transfer plus evaluation of exactly the modules Slice 5 removes.**

Arithmetic that the measurement must beat:

- Transfer: at the locked 1,474.56 Kbps (~184 KB/s), 32.6 KB ≈ 177 ms, and only if attribution translated 1:1 to emitted bytes, which it never has (DnD 51.61 → 29.54; Slice 4 15.3 → 7.0).
- Evaluation: the only measured rate is 1,003 ms per 461.5 KB gzip at 4x CPU ≈ 2.2 ms per KB → 32.6 KB ≈ 71 ms.
- Empirical anchor: Slice 4's measured ratio is 34.4 ms committed-frame per 6,969 emitted B ≈ 4.9 ms per KB → 32.6 KB ≈ 160 ms, with max task moving +16 ms (noise), i.e. byte extraction has so far not moved the largest task at all.
- Upper bound from all three: roughly 160 to 250 ms of the 1,446 ms gap, and ~0 of the 342 ms task gap.

Secondary falsifiable byte condition: reaching the 350 KB gzip gate from the 430,773 B ratchet needs 72,373 B removed; the named Slice 5 owners cover ≈ 33.4 KB of attribution, under half, before the attribution-to-emitted haircut.

If the profiler instead finds the largest tasks dominated by Three/R3F chunk evaluation (anchored by design), WebGL/shader work, or hydration-to-first-frame coalescing, then Slice 5 as specified cannot meet either timing ceiling, and the residual plan needs a work-shaped slice (yield points between hydration publish, mount, construction, and commit; time-sliced construction; compile warming) rather than a byte-shaped one. The strategy already half-concedes this by calling the residual "unproven"; the measurement decides it.
