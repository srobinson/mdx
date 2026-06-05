# Transport Matters slice 1b — first-run flag reference inventory

Sweep date: 2026-08-01. Tree: `transport-matters` working tree (assistant seat, read-only).
Scope: whole-repo enumeration of the canvas first-run **query flag** (`firstrun` / `?firstrun=1` / `isFirstRunCanvas` / `firstRun` branch) and the **surface it mounts** (`FirstRunScreen` and `www/packages/canvas/src/firstrun/`). Name-collisions that do not read the flag are listed and labeled.

## Answers the brief asked for

| Question | Fact |
|---|---|
| Surfaces outside the canvas first-run screen that **read the query flag** | **None.** Only `SessionCanvasRoute` calls `isFirstRunCanvas` and branches on the resulting `firstRun` boolean. |
| Anything that **persists the query flag** | **No.** The flag is URL-only (`window.location.search` → `URLSearchParams.get("firstrun") === "1"`). No localStorage, no store slice, no URL rewrite writes or keeps `firstrun`. |
| Related persistence that is **not** the query flag | `FirstRunHint` persists `CANVAS_STORAGE_KEYS.launcherHintSeen` (`transport-matters-launcher-hint-seen`) and legacy `tm.launcher.hintSeen` for the ⌘K discoverability chip; it does not read or write `?firstrun`. |
| Production **producer** of `?firstrun=1` | **None found.** Only a unit test navigates with the flag. |
| Playwright / e2e path with the flag | **Empty** (searched e2e globs and playwright paths). |
| Python / snake_case `first_run` / `FIRST_RUN` constant for this flag | **Empty.** |
| API/backend code that reads the query flag | **Empty.** |

## Flat table

| path | symbol | role | fact |
|---|---|---|---|
| `www/packages/canvas/src/route.ts` | `hasCanvasFlag` | consumer | Shared query-param reader: `params.get(name) === "1"` for canvas route flags. |
| `www/packages/canvas/src/route.ts` | `isFirstRunCanvas` | consumer | Sole flag parser: `hasCanvasFlag(search, "firstrun")`; documents 1a mount until doctor gate. |
| `www/packages/canvas/src/route.ts` | `isStressCanvas` | mention | Sibling flag reader for `"stress"`; same helper, not firstrun, listed so the dual-flag pattern is visible. |
| `www/packages/canvas/src/workbench/SessionCanvasRoute.tsx` | `isFirstRunCanvas` import | consumer | Only call site of `isFirstRunCanvas` outside `route.ts`. |
| `www/packages/canvas/src/workbench/SessionCanvasRoute.tsx` | `firstRun` (local) | consumer | `useMemo(() => isFirstRunCanvas(search), [search])` from `window.location.search`. |
| `www/packages/canvas/src/workbench/SessionCanvasRoute.tsx` | activity stream gate | consumer | `useWorkspaceActivityStream({ enabled: !firstRun && ... })` holds stream when flag is set. |
| `www/packages/canvas/src/workbench/SessionCanvasRoute.tsx` | adoption reconciler effect | consumer | Early-returns when `firstRun` so captured-run reconciliation does not run on first-run mount. |
| `www/packages/canvas/src/workbench/SessionCanvasRoute.tsx` | transcript spawn effect | consumer | Skips `spawnOrFocusTranscript` when `firstRun`. |
| `www/packages/canvas/src/workbench/SessionCanvasRoute.tsx` | captured-run prune effect | consumer | Skips prune path when `firstRun`. |
| `www/packages/canvas/src/workbench/SessionCanvasRoute.tsx` | render branch | consumer | `if (firstRun) return <FirstRunScreen />` after stress branch; only production mount of the surface via the flag. |
| `www/packages/canvas/src/workbench/SessionCanvasRoute.tsx` | `FirstRunScreen` import | consumer | Imports surface module for the flag branch. |
| `www/packages/canvas/src/workbench/SessionCanvasRoute.test.tsx` | test `"renders the first-run screen…"` | producer | `window.history.pushState({}, "", "/canvas?firstrun=1")` is the only in-repo navigation that sets the flag. |
| `www/packages/canvas/src/workbench/SessionCanvasRoute.test.tsx` | same test assertions | mention | Asserts heading `"First run"` and absence of workbench empty-state text. |
| `www/packages/canvas/src/route.test.ts` | (file) | mention | Tests `isStressCanvas` only; **does not** assert `isFirstRunCanvas` (gap for retirement tests, not a flag consumer). |
| `www/packages/canvas/src/firstrun/FirstRunScreen.tsx` | `FirstRunScreen` | consumer (surface) | First-run UI root; comment states reached via `?firstrun=1` until 1b; does not parse the flag itself. |
| `www/packages/canvas/src/firstrun/FirstRunScreen.tsx` | `FirstRunErrorBoundary` | consumer (surface) | Error boundary around harness section; BEM `canvas-firstrun__*` classes. |
| `www/packages/canvas/src/firstrun/FirstRunScreen.tsx` | harness DOM ids/classes | mention | `firstrun-harnesses` section id and `canvas-firstrun*` / `--firstrun-index` CSS naming tied to the surface, not query parsing. |
| `www/packages/canvas/src/firstrun/firstrun.css` | `.canvas-firstrun*` / `@keyframes canvas-firstrun-rise` | mention | Stylesheet for the surface; owned by `FirstRunScreen`. |
| `www/packages/canvas/src/firstrun/FirstRunScreen.test.tsx` | `FirstRunScreen` suite | mention | Renders `FirstRunScreen` directly without setting `?firstrun=1`. |
| `www/packages/canvas/src/firstrun/harnessCards.ts` | `harnessCard` / related | mention | Card pure logic for the surface; no flag read. |
| `www/packages/canvas/src/firstrun/harnessCards.test.ts` | suite | mention | Tests harness card pure functions; no flag. |
| `www/packages/canvas/src/firstrun/useHarnessInventory.ts` | `useHarnessInventory` | mention | Fetches `GET /v1/harnesses` for the surface; no flag. |
| `www/packages/canvas/src/firstrun/useHarnessInventory.test.ts` | suite | mention | Hook tests; no flag. |
| `www/packages/canvas/src/firstrun/harnessInventory.testSupport.ts` | test helpers | mention | Fixture helpers for inventory tests; no flag. |
| `www/packages/canvas/src/fetchStatus.ts` | file comment | mention | Comment notes launcher and firstrun both import the shared four-state fetch vocabulary. |
| `www/packages/canvas/src/launcher/commandTypes.ts` | file comment | mention | Comment that firstrun imports `FetchStatus` leaf directly. |
| `www/packages/canvas/src/index.ts` | `SessionCanvasRoute` export | mention | Public package export of the only route that branches on the flag; does not export `isFirstRunCanvas` or `FirstRunScreen`. |
| `www/packages/canvas/src/app.tsx` | lazy `SessionCanvasRoute` | mention | Canvas product entry lazy-loads the route that owns the flag branch. |
| `www/packages/shell/src/rootShell.tsx` | lazy `@tm/canvas` `SessionCanvasRoute` | mention | Dev shell mounts the same route; does not set or read `firstrun`. |
| `api/src/transport_matters/canvas/assets/SessionCanvasRoute-BPQj6bvO.js` | built chunk | mention | Embedded canvas build of the route/surface (source of truth remains `www/packages/canvas`); contains minified `firstrun` strings. |
| `api/src/transport_matters/canvas/assets/SessionCanvasRoute-BEvm1Azr.css` | built CSS | mention | Embedded build of firstrun surface styles (`canvas-firstrun` class names). |
| `NOW.md` | Phase 1 / slice 1a–1b prose | mention | Product plan: screen mounted behind `?firstrun=1` until 1b; 1b retires the flag for doctor gate. |
| `NOW.md` | scout path | mention | Points at `~/.mdx/projects/tm-firstrun-scout.md` (outside repo). |
| `HARNESS-COMPATIBILITY.md` | "First run and startup inventory" | mention | Spec prose for first-run screen harness cards; no query flag literal. |
| `HARNESS-COMPATIBILITY.md` | first-run tests item | mention | Checklist item that first-run tests cover harness/connection counts. |
| `RUNTIME-SURFACING-PLAN.md` | First run harness setup / screen | mention | Plan prose for first-run setup screen and inventory; no `?firstrun` literal. |
| `RUNTIME-SURFACING-S2-PLAN.md` | inventory / first run UI rows | mention | S2 plan ties inventory to first-run screen; no query flag literal. |
| `README.md` | onboarding sentence | mention | Mentions "the first run" as product concept, not the query flag. |
| `api/src/transport_matters/harnesses/inventory.py` | module docstring | mention | Says inventory drives REST, MCP, and the deferred first-run screen. |
| `api/src/transport_matters/harnesses/test_inventory_vocabulary.py` | module docstring | mention | Vocabulary pin "into the first-run screen". |
| `api/src/transport_matters/cli/launch_runtime.py` | session-store prepare docstring | mention | "first-run starter materialization" for channel config/store bootstrap; **not** the canvas query flag. |
| `www/packages/canvas/src/launcher/FirstRunHint.tsx` | `FirstRunHint` | mention (name collision) | ⌘K resting chrome; name contains FirstRun; **does not** read `?firstrun`. |
| `www/packages/canvas/src/launcher/FirstRunHint.tsx` | `hintSeen` / localStorage | mention (name collision) | Persists launcher hint seen keys; **not** the firstrun query flag. |
| `www/packages/canvas/src/launcher/FirstRunHint.test.tsx` | suite | mention (name collision) | Asserts launcher hint localStorage; no `?firstrun`. |
| `www/packages/canvas/src/launcher/CommandCenter.tsx` | `FirstRunHint` usage | mention (name collision) | Renders `FirstRunHint` when command center closed; no flag. |
| `www/packages/canvas/src/infrastructure/persistence/storageKeys.ts` | `launcherHintSeen` | mention (name collision) | Storage key for FirstRunHint only. |
| `www/packages/canvas/src/infrastructure/persistence/storageKeys.test.ts` | key assertion | mention (name collision) | Pins `launcherHintSeen` string value. |
| `packages/activity/src/projections/workspaceActivity.test.ts` | local `firstRun` | mention (false positive) | Local binding `asRunId("run-first")` for activity projection tests; unrelated to canvas flag. |
| `api/tests/fixtures/claude_messages/turn-*/request.ir.json` | embedded NOW.md text | mention (fixture noise) | Captured wire fixtures embed NOW.md content that discusses firstrun; not executable flag logic. |

## Empty categories (explicit)

| Category | Result |
|---|---|
| Playwright / e2e navigations with `?firstrun=1` | **None** |
| Production UI or launcher navigation that sets `?firstrun` | **None** (only unit test producer) |
| Zustand / canvas store field for the flag | **None** |
| localStorage / sessionStorage for the query flag | **None** |
| URL rewrite that adds or strips `firstrun` | **None** |
| `isFirstRunCanvas` unit tests in `route.test.ts` | **None** (stress covered; firstrun not) |
| Backend / Python reader of the query flag | **None** |
| `first_run` / `FIRST_RUN` identifiers for this flag | **None** |
| Inspector package references | **None** |
| `@tm/core` / `@tm/space-client` flag parsing | **None** (`parseCanvasLaunchContext` is separate launch params) |
| Feature flag in `featureFlags.ts` | **None** (only `canvasOriginOverlay`) |

## Counts

| Bucket | Rows in table above |
|---|---|
| producer | 1 (`SessionCanvasRoute.test.tsx` URL push) |
| consumer (flag parse / branch) | 10 (route helper + SessionCanvasRoute sites) |
| consumer (surface components that are the flag's mount target, not flag readers) | 2 (`FirstRunScreen`, `FirstRunErrorBoundary`) |
| mention (surface module, styles, docs, builds, comments) | 24 |
| mention (name collision / false positive / fixture noise) | 9 |
| **Total table rows** | **46** |
| **Strict flag machinery rows** (producer + flag consumers only) | **11** |

## Retirement blast shape (facts only)

Retiring the flag is one runtime cut at:

1. `isFirstRunCanvas` / `"firstrun"` in `route.ts`
2. `firstRun` branches and `FirstRunScreen` mount in `SessionCanvasRoute.tsx`
3. The single unit test producer/assert in `SessionCanvasRoute.test.tsx`

The `firstrun/` surface module, CSS, harness inventory hooks, docs, and built assets remain as the **screen** under whatever condition replaces the flag. `FirstRunHint` and its localStorage keys are a separate product and do not participate in this flag.

