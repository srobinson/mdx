# Canvas Reset Assessment

## 1. Diagnosis

`www/packages/canvas/src/session-canvas` is structurally saturated inside one product package. The shell count is 196 TS, TSX, and CSS files. `fmm_list_files` indexes 180 source files and 22,428 LOC under the same tree. The largest indexed source files are `launcher/commandModel.test.ts`, `model/canvasStore.test.ts`, `launcher/commandModel.ts`, `lab/CanvasLabRoute.tsx`, and `model/canvasStore.ts`. The volume is workable only if ownership is obvious. Today it is not.

`fmm_dependency_cycles` found no runtime dependency cycle inside `session-canvas`. With all edges, it found one launcher SCC: `www/packages/canvas/src/session-canvas/launcher/commandModel.ts` depends on `workdirRows.ts`, and `workdirRows.ts` type imports `CommandRow` back from `commandModel.ts`. That is a cleanup target, but it is not the main failure.

The main failure mode is domain direction leakage. Model, interaction, viewer, launcher, lab, and infrastructure concepts are all present, but several files own behavior from more than one domain:

- `www/packages/canvas/src/session-canvas/viewers/registry.tsx` owns `PICKER_PANE_ID`, `paneIdForRef`, `titleForRef`, `viewerIdForRef`, `renderPaneContent`, `registerViewer`, and `resolveViewer`. That file mixes pure pane identity and title policy with React renderer resolution and lazy terminal imports.
- `www/packages/canvas/src/session-canvas/model/canvasStore.ts` exports `useCanvasStore`, imports `PICKER_PANE_ID`, `paneIdForRef`, and `titleForRef` from `viewers/registry.tsx`, and also owns persistence bootstrapping, pane lifecycle, captured run spawning, docking, frame and expand transitions, layout replanning, route initialization, and viewport actions.
- `www/packages/canvas/src/session-canvas/model/spawn.ts` exports `normalizeRef`, `labelFor`, `createCapturedRunRef`, and `createPaneRecord`, but imports `paneIdForRef` and `viewerIdForRef` from `viewers/registry.tsx`. Pane records are model facts, yet their identity is resolved through the React viewer registry.
- `www/packages/canvas/src/session-canvas/model/canvasStore.persistence.ts` rebuilds pane records during persistence merge and imports `titleForRef` from `viewers/registry.tsx`. Persistence is therefore coupled to viewer registration policy.
- `www/packages/canvas/src/session-canvas/dnd/canvasDrop.ts` exports `handleCanvasDrop`, `handleDockDrop`, `paneIdAtPoint`, and `locatorForPaneRef`, but imports `resolvePasteHandle` from `viewers/terminal/pasteRegistry.ts`.
- `www/packages/canvas/src/session-canvas/dnd/paneDndCallbacks.ts` exports `deliveryTargetAt` and `createPaneDndCallbacks`, but imports both `resolvePasteHandle` and `escapeDropLocator` from `viewers/terminal/pasteRegistry.ts`. Drag and drop knows terminal viewer internals.
- `www/packages/canvas/src/session-canvas/components/CanvasSurface.tsx` exports `CanvasSurface` and also contains `useCanvasCommandHandler` and `useCanvasPaneRenderer`. Its direct dependencies include engine, keybindings, stores, launch resolution, DnD, launcher, model, route, viewer registry, pane chrome, dock, route switcher, and backdrop. It is the route surface, workbench composition root, command dispatcher, pane renderer, DnD composer, and launcher bridge at once.
- `www/packages/canvas/src/session-canvas/viewers/terminal/TerminalPane.tsx`, `CapturedRunPane.tsx`, `terminalSession.ts`, and `terminalSocket.ts` mix terminal UI, xterm lifecycle, WebSocket URL construction, captured run attachment, and run status handling. That sits directly on the t3code P1 moving boundary where run lifecycle and terminal are being carved into the TypeScript product plane.
- `www/packages/canvas/src/session-canvas/launcher/commandModel.ts` owns navigation frames, fetch status, row grammar, row grouping, command definitions, runtime template mapping, session rows, settings rows, agent rows, and workdir rows. The `workdirRows.ts` split already tried to relieve size pressure, but the type dependency still points back to `commandModel.ts`.
- `www/packages/canvas/src/session-canvas/lab/CanvasLabRoute.tsx` and `lab/canvasLabStore.ts` import through engine, components, DnD, model, persistence, captured runs, and viewer registry. Lab is useful, but it currently looks like a second canvas implementation rather than a consumer harness.

Repo location is secondary. The code already has a product package, `@tm/canvas`, with an exports map and import graph gates. The actual blocker is unclear ownership inside `session-canvas`.

## 2. Recommendation

Pick A: reorganize `@tm/canvas` in place.

A best matches Stuart's design values because it repairs the boundaries where the facts show they are broken: pane identity, pane lifecycle, interaction delivery, command routing, terminal runtime adapters, and lab ownership. A new repo would add release topology while carrying the same tangled domain model forward. Pre MVP breaking changes make the in place repair cheaper and cleaner.

The existing reset draft is directionally correct. I would adopt its core decision: Canvas is a workbench, and moving Canvas out of `www` comes after the workbench shape is understandable. I would strengthen the draft in two ways:

- Bring the terminal and runtime client adapter seam into the first three slices, because t3code P1 is in flight and the current terminal viewer owns run and socket details.
- Treat a future `apps/canvas` move inside this repo as a mechanical follow up. A new dedicated repo should stay off the path unless the repo itself becomes the bottleneck after package boundaries are real.

This also composes with the two plane rule. TypeScript remains the product plane. Python keeps serving the built bundle while the capture plane is maintained. New bounded contexts such as Runtime belong in `@tm/*` workspace packages. Canvas is a browser product surface that consumes those contexts through explicit client adapters.

## 3. Target Shape

Keep the first reset inside `www/packages/canvas/src`. Rename `session-canvas` only after the owners below are real and boundary tests pass without temporary allow lists.

Target source ownership:

```text
www/packages/canvas/src/
  workbench/
    CanvasWorkbench.tsx
    CanvasPaneLayer.tsx
    CanvasCommandDispatcher.ts
    PaneWindow.tsx
    chrome/
    dock/
    controls/
    background/

  model/
    paneRecords.ts
    paneIdentity.ts
    paneLifecycle.ts
    paneAffordances.ts
    paneLayout.ts
    canvasState.ts
    canvasActions.ts
    canvasStore.ts
    worktreeDefaults.ts

  interactions/
    dnd/
    pasteTargets.ts
    gestures/

  launcher/
    commandTypes.ts
    navigation.ts
    commandRows.ts
    templateRows.ts
    sessionRows.ts
    settingsRows.ts
    workdirRows.ts
    CommandCenter.tsx

  viewers/
    registry.tsx
    viewerContracts.ts
    placeholder/
    resource/
    session-picker/
    terminal/
    transcript-chat/

  infrastructure/
    api/
    stream/
    persistence/
    runtime/
    storage/

  lab/
    CanvasLabRoute.tsx
    LabWorkbenchHarness.tsx
    labFixtures.ts
    labControls/
```

Dependency direction:

```text
workbench -> model
workbench -> launcher
workbench -> interactions
workbench -> viewers
workbench -> infrastructure

launcher -> model contracts
launcher -> infrastructure query hooks

interactions -> model contracts
interactions -> paste target contracts

viewers -> model contracts
viewers -> infrastructure hooks

infrastructure -> DTOs and model contracts

model -> engine contracts
model -> pure Canvas contracts

lab -> workbench, model, interactions, viewers, infrastructure
```

Forbidden direction:

```text
model -> viewers
model -> React
model -> Zustand except the store assembly file
model -> browser storage adapters
dnd -> viewers/terminal
infrastructure -> viewers
product files -> lab
```

The most important ownership correction is `paneIdentity.ts`: pane ids, viewer ids, and titles are product model policy. `viewers/registry.tsx` should render pane content only. It may consume identity helpers, but it should not define them.

For the runtime seam, `viewers/terminal` should render terminal panes and bind xterm to a hook. URL construction, run attach URLs, socket protocol, and captured run client behavior should move to `infrastructure/runtime`. When t3code lands `@tm/runtime`, Canvas should consume its public surface or a thin adapter, not import server internals or duplicate route knowledge.

## 4. First Three Slices

### Slice 1: Boundary test and pane identity

Goal: make the most important forbidden edge impossible to reintroduce.

Shippable changes:

- Add `sessionCanvasBoundary.test.ts` under `www/packages/canvas/src/session-canvas`.
- Enforce at least: `model` cannot import `viewers`, `model` cannot import React, `persistence` cannot import `viewers`, `dnd` cannot import `viewers/terminal`, and product files cannot import `lab`.
- Create `www/packages/canvas/src/session-canvas/model/paneIdentity.ts`.
- Move `PICKER_PANE_ID`, `paneIdForRef`, `titleForRef`, `viewerIdForRef`, and the pane title helpers out of `viewers/registry.tsx`.
- Update `model/canvasStore.ts`, `model/spawn.ts`, `model/canvasStore.persistence.ts`, `lab/canvasLabStore.ts`, and tests to use model identity.
- Make `viewers/registry.tsx` consume identity helpers and keep `registerViewer`, `resolveViewer`, `bodyDragForRef`, and `renderPaneContent` as renderer concerns.

Highest risk coupling broken: `model -> viewers/registry.tsx`.

Verification:

```sh
cd www/packages/shell && pnpm exec vitest run "paneRecords|canvasStore|registry|sessionCanvasBoundary"
pnpm --filter @tm/canvas typecheck
```

### Slice 2: Store assembly and workbench composition

Goal: split product orchestration from state transitions and rendering.

Shippable changes:

- Split `useCanvasStore` in `model/canvasStore.ts` into `canvasState.ts`, `canvasActions.ts`, and `canvasStoreLifecycle.ts`, keeping `canvasStore.ts` as the Zustand assembly edge.
- Move `components/CanvasSurface.tsx` to `workbench/CanvasWorkbench.tsx`.
- Extract `useCanvasCommandHandler` into `workbench/CanvasCommandDispatcher.ts`.
- Extract `useCanvasPaneRenderer` into `workbench/CanvasPaneLayer.tsx`.
- Move pane chrome, dock, route switcher, controls, and backdrop under `workbench`.
- Keep behavior preserving and delete old `components` paths as they empty.

Highest risk coupling broken: `CanvasSurface` as route surface, command dispatcher, pane renderer, DnD composer, and launcher bridge.

Verification:

```sh
cd www/packages/shell && pnpm exec vitest run "canvasStore|CanvasSurface|PaneChrome|PaneDock|sessionCanvasBoundary"
pnpm --filter @tm/canvas build
```

### Slice 3: Runtime and interaction adapter seam

Goal: keep Canvas aligned with t3code P1 and make interactions viewer agnostic.

Shippable changes:

- Move `viewers/terminal/pasteRegistry.ts` to `interactions/pasteTargets.ts`.
- Keep `escapeDropLocator`, `registerPasteHandle`, and `resolvePasteHandle` behind a generic paste target contract.
- Update `dnd/canvasDrop.ts`, `dnd/paneDndCallbacks.ts`, and `dnd/useCanvasDropTargets.ts` to depend only on `interactions/pasteTargets.ts`.
- Move `terminalSocket.ts` and run URL construction into `infrastructure/runtime`.
- Move captured run client concerns behind an infrastructure hook or adapter used by `CapturedRunPane.tsx`.
- Leave `TerminalPane.tsx` and `CapturedRunPane.tsx` as viewers that render xterm and status UI.

Highest risk coupling broken: `dnd -> viewers/terminal` and terminal viewer ownership of runtime transport.

Verification:

```sh
cd www/packages/shell && pnpm exec vitest run "canvasDrop|paneDndCallbacks|useCanvasDropTargets|terminalSocket|CapturedRunPane|sessionCanvasBoundary"
pnpm --filter @tm/canvas typecheck
```

Launcher decomposition should follow immediately after these three slices. Move `LauncherCommand`, `CommandRow`, and `RowAction` to `launcher/commandTypes.ts`, move navigation to `launcher/navigation.ts`, and split row builders by domain. That removes the all edge `commandModel.ts` and `workdirRows.ts` cycle and prevents the command palette from becoming the next saturated owner.

## 5. Packaging

For A, the single wheel model is already correct and should be preserved.

Current mechanism:

- `Justfile` builds `@tm/canvas` with `pnpm --filter @tm/canvas build`.
- `www/packages/canvas/vite.config.ts` calls `productViteConfig({ bundleDir: "canvas", base: "/canvas" })`.
- `www/vite.shared.ts` writes that bundle to `api/src/transport_matters/canvas`.
- `api/pyproject.toml` includes `src/transport_matters/canvas/**` as wheel artifacts.
- `api/src/transport_matters/main.py` serves `/canvas`, `/canvas-lab`, and the `/canvas` static mount from that embedded bundle.

So in place refactoring changes source layout only. The output path and wheel contract stay the same.

If B were chosen later, packaging both repos into one wheel is feasible. The concrete mechanisms are:

- CI checks out the Python/tool repo and the Canvas repo side by side, runs the Canvas build with an outDir pointing at `api/src/transport_matters/canvas`, then builds the wheel.
- Or the Canvas repo publishes a versioned private npm package or tarball that contains the built bundle, and the Python/tool repo copies that artifact into `api/src/transport_matters/canvas` before `hatch` builds.
- Or the Python/tool repo vendors Canvas as a git submodule and runs the same build step.

The npm or tarball artifact is the most reproducible B mechanism. The submodule is simpler to understand but creates checkout and branch state friction. The side by side CI checkout is good for integration branches, but weaker as a release source of truth.

The tradeoff with B is release coordination. Every Canvas change must synchronize source, build artifact, Python wheel build, and compatibility with Gateway and Runtime. That cost buys little until the internal ownership boundaries are real.

## 6. Highest Risk

Break `model -> viewers/registry.tsx` first.

This edge corrupts the core model. `viewers/registry.tsx` currently owns `PICKER_PANE_ID`, `paneIdForRef`, `titleForRef`, and `viewerIdForRef` while also owning `renderPaneContent`. Because `model/canvasStore.ts`, `model/spawn.ts`, `model/canvasStore.persistence.ts`, and lab store code consume those helpers, pane identity, persistence rebuild, spawning, docking, and React viewer resolution all share one registry.

The fix is direct:

- Add the boundary test first.
- Move pane identity and title policy to `model/paneIdentity.ts`.
- Make `createPaneRecord` take identity from the model.
- Make persistence rebuild records from model identity.
- Make the viewer registry consume model identity only for renderer lookup compatibility.
- Remove every `model -> viewers` import.

Once that edge is gone, the rest of the reset has a stable axis: the model owns Canvas facts, the workbench orchestrates them, interactions translate gestures, infrastructure owns IO, and viewers render.
