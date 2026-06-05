---
title: Captured-Run Lab → Canvas-Core Migration Spec
type: research
tags: [transport-matters, captured-run, canvas, lab-migration, lifecycle, leak-safety, frontend]
summary: Migrate captured-run pane machinery from the canvas lab into canvas core so /canvas (SessionCanvasRoute) is the captured-run product surface; the load-bearing work is the leak-safety lifecycle lift and the store promotion that fixes a prod⊥lab violation, not the spawn button.
status: active
source: codebase-analyst
confidence: high
created: 2026-06-14
updated: 2026-06-14
---

# Captured-Run Lab → Canvas-Core Migration Spec

## Executive Summary

The owner's belief "done apart from the UI spawn button" is **false / understated**. The captured-run **ref type** (`model/paneRecords.ts`) and **viewer** (`viewers/terminal/CapturedRunPane.tsx`, registered in the core `viewers/registry.tsx` static registry) are already canvas-core and render on any surface. But three things are still lab-bound, and one is a near-term **resource leak**:

1. **CRITICAL (leak):** the captured-run `onClose → stopRun` lifecycle policy is registered **only** by `lab/labLifecycle.ts`, which is imported **only** by `lab/CanvasLabRoute.tsx`. `SessionCanvasRoute` (the `/canvas` product route) never imports it, so `resolvePaneLifecycle` returns the empty policy for `captured-run`. The instant a captured-run pane is closed on `/canvas`, the run leaks (PTY + mitmproxy + port held by `RunManager` until idle reap).
2. **Architecture violation:** the core viewer `viewers/terminal/CapturedRunPane.tsx` imports **two** lab modules (`lab/canvasLabStore`, `lab/capturedRunStore`), violating the spec's own `prod ⊥ lab` isolation rule (`NOTES/captured-canvas/07-lab-isolation.md`). The run store and spawn factory still physically live in `lab/`.
3. **Missing product action:** the captured-run ref constructor lives only in `lab/canvasLabStore.addCapturedRun`; `useCanvasStore` has no captured-run spawn action.

**Backend gap = zero.** `RunManager` (`app.state`), `POST/GET/DELETE /runs`, `WS /runs/{id}/terminal`, and `prepare_captured_run` are route-agnostic and already shared. The gap is frontend-only. Estimated **4 PR-sized slices**; the spawn button is the last and smallest.

## Project Metadata

- Frontend: `www/` — React + TypeScript, Zustand stores, Vite, Vitest, Biome.
- Backend: `api/` — Python FastAPI; `transport_matters` package.
- Canvas frontend root: `www/src/session-canvas/` (147 files, ~15.9k LOC). Subtrees: `model/` (core store + types), `components/` (product surface), `viewers/` (shared viewers), `lab/` (proving-ground sandbox).
- Gate recipe (verbatim, from `www/justfile`): `check: format lint typecheck`; `test: pnpm test` (vitest run); `build: pnpm build` (`tsc -b && vite build`). Root `justfile` proxies via `just www <recipe>`. Full gate chain: **`just www check && just www test && just www build`** (equivalently `cd www && pnpm ci`, which is `pnpm lint && pnpm typecheck && pnpm test && pnpm build`). Note: `check` does **not** run tests or build, so all three recipes are required.

---

## SECTION A: Current-State Map (verified, file+symbol)

### A1. Captured-run store — `lab/capturedRunStore.ts` (`useCapturedRunStore`)

**Status: physically lab-bound, but core-shareable (zero lab coupling).** Its only dependencies are top-level (`../../api` for `createCapturedRun`/`deleteRun`, `../../stores/persistence` for `FRONTEND_STORAGE_KEYS`/`createFrontendPersistStorage`, `../../types`). It imports nothing from `lab/` and nothing from `model/`. Owns the run lifecycle: `ensureRun` (spawn-once via `POST /runs`, persist `runId` under `runKey`, with mid-spawn cancel/minimize intent maps), `stopRun` (`DELETE /runs`, the only destructive op), `setMinimized` (dock flag). Persists `{ runs: { [runKey]: { provider, runId, minimized? } } }` under `FRONTEND_STORAGE_KEYS.capturedRunStore` (`"transport-matters-captured-run"`), `CAPTURED_RUN_STORAGE_VERSION = 3`. **Verdict: trivially movable to `model/`; the import specifiers (`../../*`) are identical from `model/` because `lab/` and `model/` are siblings at the same depth.**

### A2. Spawn path — `lab/canvasLabStore.ts` (`addCapturedRun`)

**Status: lab-bound (the only `{kind:"captured-run"}` constructor in the tree).** `useCanvasLabStore.addCapturedRun(provider)` builds the ref inline: `createCapturedRunKey(provider)` (from `capturedRunStore`) for the per-pane key, `labelFor(state.paneCounters, cliLabel(provider))` for an incremental label (`Claude-1`, `Codex-2`), then `spawnPaneLayout(state, runKey, { kind:"captured-run", owner:"local", provider, runKey, label })`. The label counter (`paneCounters` / `labelFor`) is **lab-only state** (`lab/canvasLabTypes.ts`, `lab/canvasLabStore.persistence.ts`); `useCanvasStore` has no equivalent. The POST itself is deferred: `addCapturedRun` only seeds the pane; the viewer's `ensureRun` performs `POST /runs` on mount (via `createCapturedRun` in `src/api.ts`). The spawn-button UI is in `lab/CanvasLabRoute.tsx` ("Spawn Claude"/"Spawn Codex" → `addCapturedRun`), gated by a managed-CLI availability probe (`lab/capabilitiesStore.ts`).

### A3. Captured-run pane VIEWER — `viewers/registry.tsx` + `viewers/terminal/CapturedRunPane.tsx`

**Status: core (shared), but with a prod→lab import leak.** The captured-run viewer is registered in the **core static `registry` array** in `viewers/registry.tsx` (`id: "captured-run"`, `paneId: (ref) => ref.runKey`, lazy-loads `CapturedRunPane`). It renders on **any** surface, `/canvas` included. The xterm/terminal bridge (`viewers/terminal/terminalSession.ts`, `terminalSocket.ts`, `runTerminalFrames.ts`) is shared and route-agnostic. **The leak:** `viewers/terminal/CapturedRunPane.tsx` imports `useCapturedRunStore` (A1, run lifecycle) **and** `useCanvasLabStore` (A2). The lab-store import is used for exactly one thing: `useCanvasLabStore.getState().oscColorReplies` read at spawn time (an experimental dev toggle). This is the second `prod ⊥ lab` violation and the only remaining use of `useCanvasLabStore` from core.

### A4. Lifecycle policy — `model/paneLifecycle.ts` (core seam) vs `lab/labLifecycle.ts` (registration)

**Status: confirmed lab-route-side registration; the dispatch machinery is already core.** `model/paneLifecycle.ts` is the core seam: `registerLifecycle(kind, policy)` writes a module-local `overrides` map; `resolvePaneLifecycle(ref)` falls back to an empty `PANE_LIFECYCLE_POLICIES` table (ships empty) then `EMPTY`. `lab/labLifecycle.ts` is the **sole** `registerLifecycle` caller; it registers `captured-run` with `onMinimize`/`onRestore` (→ `setMinimized`) and `onClose` (→ `stopRun`). It is imported as a side-effect by `lab/CanvasLabRoute.tsx` and two lab test files only. The hook **dispatch** (`dismissPane`, `invokeDockedPaneCloseLifecycle`, `invokeDockedPaneRestoreLifecycle` in `model/paneAffordances.ts`) is already core and is called by **both** `model/canvasStore.ts` and `lab/canvasLabStore.ts`. So `/canvas` already *runs* the seam on close/minimize/restore; it just resolves the empty policy because nothing registered `captured-run` there. **This is the single load-bearing gap: registration, not dispatch.**

### A5. Persistence — `model/canvasStore.persistence.ts` vs `lab/canvasLabStore.persistence.ts`

**Status: three distinct, independent keys (`FRONTEND_STORAGE_KEYS`).**
- `capturedRunStore` → `"transport-matters-captured-run"`: the `runKey → runId` map. **Already shared** across `/canvas` and `/canvas-lab` (single store), needs no migration.
- `canvasStore` → `"transport-matters-canvas"`: product `/canvas` pane placement/layout.
- `canvasLabStore` → `"transport-matters-canvas-lab"`: lab pane placement/layout (plus `paneCounters`, strategy params, dev toggles).

Pane **placement** is per-surface and does not cross between `canvasStore` and `canvasLabStore`.

### A6. Backend — route-agnostic, already shared (gap is frontend-only)

Confirmed. `prepare_captured_run` (`api/src/transport_matters/captured_run.py`) is a pure spawn-spec/lease factory with no route coupling. `RunManager` (`api/src/transport_matters/run_manager.py`) owns runs and calls `prepare_captured_run`; typed `RunManagerError` codes exist (`run_not_found`, `run_stopped`, `run_stale`, `run_not_attachable`, `run_manager_closed`, `bind_conflict`, etc.). Routes live in `api/src/transport_matters/api/v1/run_routes.py` (`RUNS_ROUTE_PREFIX = "/runs"`, manager resolved from `app.state` via `get_run_manager_from_app`). None of this is `/canvas`- or `/canvas-lab`-aware. **No backend change is required for this migration.**

### Verdict on "done apart from the UI spawn button"

**Understated.** Quantified remaining gap (all frontend):
- **1 critical leak** (A4): lifecycle registration is lab-route-only → close on `/canvas` leaks the run.
- **2 prod→lab import leaks** (A3): `CapturedRunPane.tsx` imports `lab/capturedRunStore` + `lab/canvasLabStore`; the store + spawn factory still live in `lab/`.
- **1 missing product action** (A2): no `spawnCapturedRun` on `useCanvasStore`.
- **The button is real but trivial** and is the *last* piece. The load-bearing work is the lifecycle lift (Slice 1) and the store promotion that restores `prod ⊥ lab` (Slices 1+3).

---

## SECTION B: Migration Spec

Conventions: cite file+symbol, never line numbers; do not break the lab; leak-safety is non-negotiable; reuse existing canvas-core shapes (no new abstractions). Design only.

### Leak-Safety Invariant (non-negotiable, stated explicitly)

`close → onClose(ref) → useCapturedRunStore.stopRun(ref.runKey) → DELETE /api/runs/{runId}` (frees PTY + mitmproxy + port) **must fire wherever a captured-run pane can be closed**:
- on-canvas close (`closePane → dismissPane`, `mode:"close"`),
- dock close (`closeDockedPane → invokeDockedPaneCloseLifecycle`),
- on **both** `/canvas` and `/canvas-lab`,
- **including dock-close after a browser reload**, when the captured-run viewer chunk has not been mounted (the dock chip renders title-only via `titleForRef`, never mounting `CapturedRunPane`).

`minimize`/dock detaches the viewer only (run lives; `setMinimized(true)`); `restore` re-seeds the pane so `ensureRun` re-attaches by the kept `runId` and clears the flag. Because dock-close-after-reload must work without the viewer chunk, the policy registration **must be eager at the route level**, not lazy inside the viewer chunk.

### Slice 1 — Lift captured-run lifecycle to core (leak-safety; FIRST regardless)

**Goal:** every surface that can render or dock a captured-run pane gets `close → stopRun` by construction.

Moves:
1. **Promote the run store:** `lab/capturedRunStore.ts → model/capturedRunStore.ts`. Import specifiers are unchanged (`../../api`, `../../stores/persistence`, `../../types` resolve identically from `model/`). No code change inside the store.
2. **Create the core registration module:** `model/capturedRunLifecycle.ts` — the `registerLifecycle("captured-run", { onMinimize, onRestore, onClose })` body currently in `lab/labLifecycle.ts`, importing `registerLifecycle` from `./paneLifecycle` and `useCapturedRunStore` from `./capturedRunStore`.
3. **Register eagerly on the product route:** add side-effect `import "./model/capturedRunLifecycle";` to `SessionCanvasRoute.tsx`.
4. **Lab consumes core (DRY):** delete `lab/labLifecycle.ts`; change `lab/CanvasLabRoute.tsx` to `import "../model/capturedRunLifecycle";`. One registration, both routes.
5. **Re-point importers of the moved store:** `viewers/terminal/CapturedRunPane.tsx` (`../../lab/capturedRunStore → ../../model/capturedRunStore`), `lab/canvasLabStore.ts` (`./capturedRunStore → ../model/capturedRunStore`), and tests (`viewers/terminal/CapturedRunPane.test.tsx`, `lab/canvasLabStore.test.ts`, `lab/canvasLabStore.persistence.test.ts`, `lab/CanvasLabRoute.test.tsx`). Move `lab/capturedRunStore.test.ts → model/capturedRunStore.test.ts`.

**Bundle trade-off (decide):** the eager route import pulls the run store (~191 LOC, Zustand, **no xterm**) into the eager `/canvas` bundle; the heavy xterm core stays lazy in the `CapturedRunPane` viewer chunk. This is the **recommended** default — leak-safety outranks shaving a light store, and the dock-close-after-reload case *requires* eager registration. *Alternative (open question, only if bundle weight is measured to matter):* keep the store lazy by making `onClose` resolve the store via dynamic import — `void import("./capturedRunStore").then((m) => m.useCapturedRunStore.getState().stopRun(ref.runKey))` — so `capturedRunLifecycle.ts` stays store-free and eager. Adds async to the close path.

**Seams:** `model/capturedRunStore.ts` (moved), `model/capturedRunLifecycle.ts` (new), `model/paneLifecycle.ts` (unchanged), `SessionCanvasRoute.tsx` (+1 import), `lab/CanvasLabRoute.tsx` (import swap), `lab/labLifecycle.ts` (deleted).

**Tests:**
- New `model/capturedRunLifecycle.test.ts`: after import, `resolvePaneLifecycle({ kind:"captured-run", owner:"local", provider:"claude", runKey:"k" })` returns hooks; `onClose` invokes `useCapturedRunStore.getState().stopRun("k")` (spy on store / `deleteRun`).
- New regression guard (the leak): in `model/canvasStore.test.ts` (or `SessionCanvasRoute.test.tsx`), seed a captured-run pane on `useCanvasStore`, call `closePane`/`closeDockedPane`, assert `stopRun` (→ `deleteRun`) fired. This is the test that would have caught the leak.

**Gate:** `just www check && just www test && just www build`.

### Slice 2 — Core captured-run spawn factory + product store action

**Goal:** give `/canvas` a first-class spawn action without copying the lab's ref construction.

1. **Extract the ref factory to core:** add `createCapturedRunRef(provider, label?)` to `model/spawn.ts` (or co-located with `model/capturedRunStore.ts`), wrapping `createCapturedRunKey(provider)` + `{ kind:"captured-run", owner:"local", provider, runKey, label }`. Refactor `lab/canvasLabStore.addCapturedRun` to call it (DRY; the lab keeps its `labelFor`/`paneCounters` label, passing the result as the `label` arg).
2. **Add the product action:** `useCanvasStore.spawnCapturedRun(provider)` in `model/canvasStore.ts` — build the ref via `createCapturedRunRef`, call the **existing** generic `spawnPane(ref, { focus:true })`. No `kind===` branch needed: `spawnPane → normalizeRef → paneIdForRef` already returns `ref.runKey` as the dedupe key (per the registry's captured-run `paneId`).
3. **Label for /canvas v1:** default `cliLabel(provider)` (no numeric suffix); the lab's incremental counter stays lab-only. *(Polish, not v1: a light per-provider counter on `canvasStore` if product wants `Claude-2`.)* Do **not** pull lab's `paneCounters` into core.

**Seams:** `model/spawn.ts` (+`createCapturedRunRef`), `model/canvasStore.ts` (+`spawnCapturedRun`), `lab/canvasLabStore.ts` (refactor `addCapturedRun` to reuse).

**Tests:** `model/canvasStore.test.ts` — `spawnCapturedRun("claude")` inserts one pane keyed by the run key; calling again yields a distinct pane (distinct key); `spawn.test.ts` for `createCapturedRunRef` shape. **Gate:** as above.

### Slice 3 — /canvas spawn affordance (the trivial UI) + finish the prod⊥lab decouple

1. **Buttons:** add "Spawn Claude"/"Spawn Codex" to `components/CanvasCommandBar.tsx` (new prop `onSpawnCapturedRun(provider: CliName)`), wired in `components/CanvasSurface.tsx` to `useCanvasStore().spawnCapturedRun`. Mirrors the lab buttons in `CanvasLabRoute.tsx`. Same `createCapturedRun` / `POST /runs` path (Slice 2 → `spawnPane` → `CapturedRunPane.ensureRun`).
2. **Decouple `oscColorReplies` (removes the last core→lab import):** change `viewers/terminal/CapturedRunPane.tsx` to stop reading `useCanvasLabStore.getState().oscColorReplies`. Rely on `ensureRun`'s existing default (`oscColorReplies = true`); drop the `useCanvasLabStore` import. The lab's experimental toggle (`lab/ControlsPanel.tsx` / `setOscColorReplies`) becomes either a lab-only preference threaded through the store at spawn, or default-only. After this, `CapturedRunPane.tsx` imports **zero** `lab/` modules → `prod ⊥ lab` restored for the viewer.
3. **Availability (optional polish):** the lab's managed-CLI availability probe (`lab/capabilitiesStore.ts`) can be promoted to disable the buttons when a CLI isn't installed. Not required for v1 — a spawn failure already surfaces as an alert banner in `CapturedRunPane`.

**Seams:** `components/CanvasCommandBar.tsx`, `components/CanvasSurface.tsx`, `viewers/terminal/CapturedRunPane.tsx`.

**Tests:** `components/CanvasCommandBar.test.tsx` (button → callback), `components/CanvasSurface` wiring; update `viewers/terminal/CapturedRunPane.test.tsx` to drop the lab-store dependency and assert default `oscColorReplies`. **Gate:** as above.

### Slice 4 — Enforce the prod⊥lab isolation invariant

The spec's `07-lab-isolation.md` mandates `prod ⊥ lab` and its enforcement note suggests "a lint/AST or store-boundary guard … (mirrors the api⊥cli import-boundary test pattern)." No such test exists today, and the current state violates the rule (Slice 3 fixes the last violation).

- Add an import-boundary test (Vitest, mirroring the api⊥cli AST/glob pattern): **no file under `session-canvas/` outside `lab/` may import from `session-canvas/lab/`.** Walk every `.ts`/`.tsx` outside `lab/`, parse imports (module-body **and** function-local), assert none resolve into `lab/`. After Slices 1+3 the two known violations (`CapturedRunPane.tsx`) are gone, so the test passes and locks the invariant.
- This realizes the deliberate **promotion seam** `07-lab-isolation.md` anticipated ("promotion is a no-op today"): the captured-run store + lifecycle + spawn factory are the first real lab→core graduation.

**Seam:** new `session-canvas/labBoundary.test.ts` (or under `model/`). **Gate:** as above.

### Lab disposition (recommendation)

**Thin consumer of core. Do NOT retire the lab.** After migration the lab keeps `canvasLabStore` (layout-strategy experimentation, `paneCounters`, dev toggles, strategy controls) but consumes the **core** captured-run store, **core** lifecycle registration, and **core** spawn factory. This is consistent with `07-lab-isolation.md` (lab is a permanent proving ground that `reads prod`), satisfies "do not break the lab," and removes the dependency inversion (today core depends on lab). Retiring the lab is out of scope and would lose the layout-strategy sandbox; the orchestrator's "scaffolding to migrate from" framing is satisfied by emptying the lab of *product-bound* captured-run code, not by deleting the route.

### Persistence decision

**No migration. N/A for pane placement; the runId map is already shared.**
- `capturedRunStore` (`"transport-matters-captured-run"`, the `runKey → runId` map) is a single store used by both surfaces — already shared, no migration.
- Lab pane **placement** (`"transport-matters-canvas-lab"`) does **not** migrate into `/canvas` (`"transport-matters-canvas"`). Justification: (a) runs are **process-resident** — they do not survive an `api` restart, so there is no durable run worth rescuing across a migration; (b) the lab is a proving ground with no real user runs to preserve; (c) the `runId` map is already shared, so a still-live run could be re-attached by key if ever needed, with no schema change. Writing placement-migration code would add risk for zero product value.

### Open Questions / Risks

- **Bundle vs eager registration (Slice 1):** ship the light run store eager on `/canvas` (recommended, simplest, safest) or keep it lazy via a dynamic-import `onClose`? Decide with a bundle measurement; default to eager.
- **`oscColorReplies` fate (Slice 3):** drop the lab toggle's effect on captured panes (default-only) or thread a per-run preference through the (now core) store so the lab toggle still bites? Recommend default-only for v1; revisit if the dev toggle is still wanted.
- **Label scheme (Slice 2):** `cliLabel(provider)` for v1 vs a core per-provider counter for `Claude-2`. Product call; trivial either way.
- **Availability gating (Slice 3):** promote `capabilitiesStore` to core to disable buttons, or rely on the in-pane error banner? Polish, not blocking.
- **Risk — dock-close-after-reload:** the highest-value correctness case; the eager route-level registration (Slice 1) is what covers it. Any "lazy registration in the viewer chunk" shortcut reintroduces the leak. The Slice 1 regression test must include `closeDockedPane` without first mounting the viewer.
- **Risk — test import churn:** moving `capturedRunStore` touches several lab test imports; run the full `just www test` (not a scoped subset) before claiming green.
