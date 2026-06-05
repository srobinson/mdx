---
title: Captured-run canvas migration (frontend) — lab → core, /canvas as the product surface
type: projects
tags: [frontend, transport-matters, captured-canvas, lab-migration, leak-safety, react, zustand]
summary: Migrate the captured-run pane machinery from the canvas LAB into canvas CORE so /canvas (SessionCanvasRoute) is the captured-run product surface; backend + viewer + seam are already shared, the real gap is the lab-only lifecycle policy + store location + spawn action, not "one button."
status: active
source: frontend-engineer
confidence: high
created: 2026-06-14
updated: 2026-06-14
---

# Captured-run canvas migration — frontend spec

Spec author: frontend-engineer (spec-writing pass, read-only). Cite **file + symbol**, never line numbers.

## TL;DR gap verdict

The owner's belief — "done apart from the UI spawn button" — is **partly true but understated**. Already shared/core: the entire backend, the captured-run **ref type**, the captured-run **viewer**, and the lifecycle **seam dispatch** on the product store. What is still **lab-bound and load-bearing**:

1. **Leak-safety lifecycle policy** (`onClose → stopRun`, `onMinimize/onRestore`) is registered **only** by `lab/labLifecycle.ts`, loaded **only** by `lab/CanvasLabRoute.tsx`. On `/canvas`, `resolvePaneLifecycle("captured-run")` returns `EMPTY`, so a captured-run pane closed on `/canvas` would **never call `stopRun`** → orphaned PTY + proxy + port. This is the #1 gap and is **not** a UI button.
2. **`capturedRunStore`** physically lives in `lab/` yet a **core** viewer (`viewers/terminal/CapturedRunPane.tsx`) already imports it — an illegal `prod → lab` dependency. Must move to `model/`.
3. The shared viewer also reads `useCanvasLabStore.getState().oscColorReplies` — a **second** `prod → lab` import.
4. The captured-run **spawn ref factory** (`addCapturedRun`) exists only on `canvasLabStore`; `canvasStore` has no equivalent.
5. The `/canvas` **spawn button** — the trivial part the owner named.

**Actual remaining gap ≈ 4 real slices + 1 trivial button.** The leak-safety work (items 1–3) is the substance.

---

## SECTION A — Current-state map (verified)

### A1. Captured-run store — `lab/capturedRunStore.ts` → **shareable, must move to core**
- `useCapturedRunStore` (zustand `persist`) owns `ensureRun` (spawn-once via `createCapturedRun` → `POST /api/runs`, persist `runId` under `runKey`), `stopRun` (DELETE + forget, best-effort), `setMinimized` (dock flag, with mid-spawn intent deferral), plus `createCapturedRunKey`, `CapturedRunKey`, `CapturedRunRecord`, `CapturedRunState`, `resetCapturedRunStoreForTests`.
- **Dependencies are all core**: `../../api`, `../../stores/persistence`, `../../types`, `zustand`. **Zero lab imports.** Physically in `lab/` but logically core — a pure relocation.
- **Downstream importers**: `lab/canvasLabStore.ts`, `lab/labLifecycle.ts`, and **`viewers/terminal/CapturedRunPane.tsx` (core viewer)**. The last edge is the layering inversion this migration fixes.
- Persistence: key `FRONTEND_STORAGE_KEYS.capturedRunStore` (`stores/persistence.ts`), `createFrontendPersistStorage()`, `CAPTURED_RUN_STORAGE_VERSION`, `partialize → { runs }`. The key is a route-agnostic constant; relocating the module does not change it.
- **Verdict: core-shareable as-is. Move file, repoint importers. No shape change.**

### A2. Spawn path — ref construction is **lab-bound**, the backend call is **core**
- The `{ kind: "captured-run" }` ref is constructed **only** in `canvasLabStore.useCanvasLabStore.addCapturedRun(provider)`: builds `runKey = createCapturedRunKey(provider)`, label via lab-local `labelFor(state.paneCounters, cliLabel(provider))`, then `spawnPaneLayout(state, runKey, { kind:"captured-run", owner:"local", provider, runKey, label })`.
- Spawn buttons: `lab/ControlsPanel.tsx` / `lab/CanvasLabRoute.tsx` ("Spawn Claude/Codex") call `addCapturedRun`.
- The actual backend call site is **core/shared**: the ref factory only seeds a pane; the real `POST /api/runs` happens inside `capturedRunStore.ensureRun → createCapturedRun` (`www/src/api.ts`), invoked by the viewer on mount. So the spawn *factory* is lab-bound; the spawn *mechanism* is core.
- `labelFor` and `paneCounters` are **non-exported lab-local** helpers/state (fmm finds no exported symbol). `canvasStore` has no `paneCounters` in its model. This is the only genuinely lab-specific logic in `addCapturedRun`.
- **Verdict: lab-bound (ref factory + label counter). Needs a core twin / shared factory.**

### A3. Captured-run pane VIEWER — **already core/shared**
- `viewers/registry.tsx` statically registers the `captured-run` viewer in its module-level `registry: ViewerRegistration[]` array: `id:"captured-run"`, `canRender: ref.kind === "captured-run"`, `paneId: ref.runKey`, `title: ref.label ?? cliLabel(ref.provider)`, `render → <Suspense><CapturedRunPane …/></Suspense>` (lazy). It also registers the sibling `terminal` viewer the same way. `registerViewer` (the dynamic API) is used by **no one** (`used_by: []`); all viewers are static.
- The registry is consumed by **both** `canvasStore.ts` (core) and `canvasLabStore.ts` (lab) via `paneIdForRef` / `resolveViewer` / `renderPaneContent` / `titleForRef`. So the viewer selection path is route-agnostic.
- `viewers/terminal/CapturedRunPane.tsx` + the terminal bridge (`TerminalPane`, `terminalSession`, `terminalSocket`, `runTerminalFrames`, `pasteRegistry`) live under shared `viewers/terminal/`. xterm is code-split into the lazy viewer chunk (registry comment), so it is **not** in the eager bundle.
- **The two lab couplings inside the core viewer** (`CapturedRunPane`): `import { useCapturedRunStore } from "../../lab/capturedRunStore"` and, at spawn time, `useCanvasLabStore.getState().oscColorReplies`. Both must be de-lab'd.
- **Verdict: viewer is core; it carries two `prod → lab` imports that must be cut.**

### A4. Lifecycle policy — **confirmed lab-route-side** (the leak)
- `model/paneLifecycle.ts` is the generic seam: `PaneLifecyclePolicy` (`onMinimize/onRestore/onClose`), `registerLifecycle(kind, policy)` writes a module-local `overrides` map, and `resolvePaneLifecycle(ref)` returns `overrides[kind] ?? PANE_LIFECYCLE_POLICIES[kind] ?? EMPTY`. **`PANE_LIFECYCLE_POLICIES` is a static default table currently `{}`** (the "ships empty" the head-start referenced).
- The captured-run policy (`onMinimize/onRestore → setMinimized`, `onClose → useCapturedRunStore.stopRun`) is registered **only** in `lab/labLifecycle.ts`. `fmm_glossary registerLifecycle` → `used_by: [lab/labLifecycle.ts]` (sole caller). `labLifecycle.ts` is imported **only** by `lab/CanvasLabRoute.tsx` (side-effect on mount).
- The **seam dispatch is already core**: `model/paneAffordances.ts` `dismissPane` → `invokePaneDismissLifecycle(ref, mode)`, and `invokeDockedPaneCloseLifecycle(entry) → resolvePaneLifecycle(entry.ref).onClose?.(…)`. `canvasStore.closePane` calls `dismissPane(…, mode:"close")` and `canvasStore.closeDockedPane` calls `invokeDockedPaneCloseLifecycle`. So the **product store already fires `onClose` for whatever policy is resolved** — it just resolves to `EMPTY` for captured-run because the policy is registered lab-side.
- **Verdict: only the policy *registration* is lab-bound. Moving it to the static core table closes the leak for every surface by construction.**

### A5. Persistence — **two independent stores; only the run-id map is route-agnostic**
- Captured-run **run-id map** (`runKey → { provider, runId, minimized? }`): `capturedRunStore` under `FRONTEND_STORAGE_KEYS.capturedRunStore`. Route-agnostic constant — survives the module move unchanged, visible to whichever store seeds the pane.
- Captured-run **pane layout** is owned by the canvas store, and the two stores use **distinct keys**: `canvasStore` (`createCanvasStorePersistOptions`) vs `canvasLabStore` (`canvasLabPersistOptions`). A lab-persisted captured pane does **not** appear on `/canvas`.
- **Verdict: run-id map is shared by construction; pane-layout is per-route and intentionally not shared.**

### A6. Backend / API — **route-agnostic / shared (gap is frontend-only)**
Verified Python/FastAPI side; no `canvas`/`lab` coupling anywhere in the run surface:
- `RunManager` — `api/src/transport_matters/run_manager.py`; attached server-side in `api/src/transport_matters/main.py:lifespan` as `app.state.run_manager = run_routes.create_run_manager()`.
- HTTP routes — `api/src/transport_matters/api/v1/run_routes.py`: `create_run` (POST `/runs`), `list_runs` (GET `/runs`), `get_run` (GET `/runs/{id}`), `stop_run` (DELETE `/runs/{id}` → frees PTY + lease + ports).
- WS — `run_routes.run_terminal_socket` (`WS /runs/{id}/terminal`) → `bridge_attached_run_terminal` replays the scrollback ring then bridges live PTY I/O; origin-checked via `api/v1/terminal_bridge.py`.
- Shared seam — `api/src/transport_matters/captured_run.py:prepare_captured_run`, used by **both** the detached CLI (`run_captured_run_on_local_tty`) and the canvas pane spawn (through `RunManager`).
- The only `canvas-lab` token is `cli/launch_options.py` (a CLI launch-point alias), not server coupling.
- **Verdict: backend is route-agnostic / shared. The migration is frontend-only.**

---

## SECTION B — Migration spec (PR-sized slices)

### Leak-safety invariant (non-negotiable, applies to every slice)
> Wherever a captured-run pane renders, **close → `stopRun` → `DELETE /api/runs/{runId}`** (frees PTY + proxy + port) must fire by construction. **Minimize/dock detaches the viewer only** (the run keeps running; the WS closes, dropping the viewer count). **Restore reattaches by run id** (`ensureRun` resolves the kept `runId`, replays scrollback). Runs are **process-resident** (do not survive an API restart).

The seam that enforces this is already core (`paneAffordances.dismissPane` / `invokeDockedPaneCloseLifecycle` → `resolvePaneLifecycle`). Slice 1 makes the captured-run policy resolvable on every surface; do it **first**, before any `/canvas` spawn path exists, so close is safe the instant spawn lands.

---

### Slice 1 — Leak-safety: relocate the store + register the policy in core *(first, regardless)*
**Goal:** `resolvePaneLifecycle({kind:"captured-run"})` returns the real policy on **every** surface, with no route-mount side effect.

**Moves (file + symbol):**
1. **Relocate** `lab/capturedRunStore.ts` → `model/capturedRunStore.ts` (pure move; its deps `../../api`, `../../stores/persistence`, `../../types` are already core). Repoint the three importers: `viewers/terminal/CapturedRunPane.tsx`, `lab/canvasLabStore.ts`, and (transitionally) `lab/labLifecycle.ts`.
2. **New** `model/capturedRunLifecycle.ts` exporting `capturedRunLifecyclePolicy: PaneLifecyclePolicy` — the exact object today in `labLifecycle.ts` (`onMinimize/onRestore → useCapturedRunStore.getState().setMinimized(ref.runKey, …)`, `onClose → useCapturedRunStore.getState().stopRun(ref.runKey)`), importing the core store from step 1.
3. **Wire it statically** in `model/paneLifecycle.ts`: seed `PANE_LIFECYCLE_POLICIES["captured-run"] = capturedRunLifecyclePolicy` via a normal `import` (not a side-effect). This mirrors `registry.tsx`'s static `registry` array: the policy is present the moment `paneLifecycle.ts` loads, which is wherever a pane can close — no tree-shake or load-order risk.
4. **Delete** `lab/labLifecycle.ts` and remove its side-effect import from `lab/CanvasLabRoute.tsx`. The lab now resolves the identical policy from the core static table (DRY — no parallel registration). Keep `registerLifecycle` exported (still the runtime-override seam; now used by tests/future only).

**Why static table over relocating the `registerLifecycle` side-effect call:** a side-effect-only import can be reordered or dropped by a bundler; leak-safety must not depend on import ordering. The static `PANE_LIFECYCLE_POLICIES` entry makes the policy a structural fact of `model/`.

**Tests:**
- New `model/paneLifecycle.test.ts` (or extend): assert `resolvePaneLifecycle({kind:"captured-run", …}).onClose` is defined **without importing any lab module**.
- Extend `model/canvasStore.test.ts`: closing a seeded captured-run pane invokes `stopRun` → `DELETE` (mock `deleteRun`/`api`). Add a docked-close case via `closeDockedPane`.
- `lab/canvasLabStore.test.ts` and `lab/capturedRunStore.test.ts` (now `model/capturedRunStore.test.ts`) must stay green — lab close still kills the run, now through the core policy.

**Gate (verbatim):** `cd www && just check` then `cd www && just test`. (`just check` = `format lint typecheck`; root `just check` / `just test` run desktop+www+api.)

---

### Slice 2 — Cut the last `prod → lab` import in the shared viewer (OSC toggle)
**Goal:** `viewers/terminal/CapturedRunPane.tsx` imports **zero** lab modules, so `/canvas` never pulls `lab/` into the product bundle.

**Moves:**
- After Slice 1 the store import is already core. The remaining lab read is `useCanvasLabStore.getState().oscColorReplies` (read once at spawn time — the OSC reply window is CLI startup).
- Lift the OSC setting into the **core** `model/capturedRunStore.ts`: add `oscColorReplies: boolean` (default `true`, matching today's lab default) + `setOscColorReplies(on)`. `CapturedRunPane` reads it from the core store; drop the `useCanvasLabStore` import.
- Repoint the lab control: `lab/ControlsPanel.tsx` / `canvasLabStore.setOscColorReplies` writes to the **core** store setter (lab reads/writes core; never the reverse). The lab affordance is preserved; the dependency direction is now legal (`prod ⊥ lab`, `lab → reads core`).

**Tests:**
- `viewers/terminal/CapturedRunPane.test.tsx`: renders + spawns with **no lab import**; `ensureRun` receives the core `oscColorReplies`.
- Lab control test: toggling OSC flips the core store field; the next spawn reads the new value.

**Gate (verbatim):** `cd www && just check` && `cd www && just test`.

---

### Slice 3 — Core spawn action: `canvasStore.addCapturedRun(provider)`
**Goal:** the product store can seed a captured-run pane with the same ref shape and per-pane run key the lab uses.

**Moves:**
- Add `addCapturedRun(provider: CliName)` to `model/canvasStore.ts:useCanvasStore`, constructing `{ kind:"captured-run", owner:"local", provider, runKey: createCapturedRunKey(provider), label }` and seeding via the core spawn path (`spawnPane` / `insertPane` / `planSpawnedAffordancePaneLayout`). `createCapturedRunKey` and `cliLabel` are already core (`model/capturedRunStore.ts`, `model/paneRecords.ts`).
- **DRY the ref factory:** extract the ref construction into a shared helper (e.g. `model/spawn.ts:createCapturedRunRef(provider, label)`) called by **both** `canvasStore.addCapturedRun` and `canvasLabStore.addCapturedRun`, so the two stores cannot drift. Delete the lab's bespoke ref literal.
- **Label counter decision:** lift the lab-local `labelFor` + `paneCounters` into core model (give `canvasStore`'s initial model a `paneCounters`, mirroring `canvasLabStore`) so labels persist exact titles (`Claude-1`, `Codex-2`) on `/canvas` as they do in the lab. (Alternative: derive the ordinal from existing captured panes — simpler state but loses a stable title across removals. Recommend lifting for parity.)

**Tests:**
- `model/canvasStore.test.ts`: `addCapturedRun("claude")` inserts one captured-run pane with a unique `runKey`; two calls → two independent panes (two run keys, never deduped). Label increments per provider.
- Round-trip: `addCapturedRun` then `closePane` fires `stopRun` (re-confirms Slice 1 on the real spawn path).

**Gate (verbatim):** `cd www && just check` && `cd www && just test`.

---

### Slice 4 — The `/canvas` spawn affordance (the trivial UI)
**Goal:** an operator can spawn Claude/Codex into a `/canvas` pane.

**Moves:**
- Add a "Spawn Claude" / "Spawn Codex" control. **Home:** `components/CanvasCommandBar.tsx` (it already hosts `Focus picker` / `Reset view` / `RouteSwitcher` / `ThemeCycleButton`; add a small provider control in `canvas-command-bar__buttons`). Thread a `onSpawnCapturedRun(provider)` prop from `components/CanvasSurface.tsx`, wired to `useCanvasStore.getState().addCapturedRun`. (If a provider menu is too heavy for the toolbar, drop it into `CommandBarSections.tsx` instead — same handler.)
- No new backend path: `addCapturedRun` seeds the pane; the registered `captured-run` viewer mounts `CapturedRunPane`, which calls `ensureRun → createCapturedRun → POST /api/runs` — the **same** `prepare_captured_run` / `RunManager` seam as `transport-matters claude` and the lab.
- A11y/states: button has a focus ring + keyboard activation; the pane renders the existing 8-state shell (`PaneShell` loading/error/empty in `registry.tsx`, spawn-error banner in `CapturedRunPane`).

**Tests:**
- `components/CanvasCommandBar.test` (or `CanvasSurface.test`): clicking "Spawn Claude" calls `addCapturedRun("claude")`; keyboard-activable; labelled.
- E2E/integration (if the harness mocks `/api/runs`): spawn → pane attaches; close → `DELETE` fires.

**Gate (verbatim):** `cd www && just check` && `cd www && just test`.

---

### Lab disposition — **thin consumer of core, do NOT retire**
Per `NOTES/captured-canvas/07-lab-isolation.md` (lab pulls from core; nothing leaks out; `prod ⊥ lab`), the lab stays as the experimentation surface. After these slices the lab owns only its **layout store + controls**; the captured-run **store, lifecycle policy, viewer, OSC setting, and ref factory are core**, and `canvasLabStore.addCapturedRun` delegates to the shared core factory (Slice 3). `lab/labLifecycle.ts` is deleted (its sole job moved to the core static table). This makes the lab a strict downstream consumer — the intended end state — without breaking it.

### Persistence decision — **do not migrate lab pane-layout; run-id map is already shared**
- The captured-run **run-id map** moves with the store module under the unchanged key `FRONTEND_STORAGE_KEYS.capturedRunStore`; no version bump (shape unchanged). It is route-agnostic, so a pane seeded on either route resolves the same `runId`.
- **Do not** migrate lab-persisted captured **pane-layout** entries into the `/canvas` store. The stores use distinct keys, and **runs are process-resident** (do not outlive an API restart, per project contract + backend `RunManager`), so a cross-route layout handoff would point at dead run ids that fail to re-attach (surfacing as the viewer's spawn-error banner). N/A by the process-resident invariant.

---

## Open questions / risks
1. **OSC toggle home (Slice 2):** confirm default is `true`. Does `/canvas` want a UI for it, or just the safe default with the lab keeping the toggle? Recommendation: core field default `true`, no `/canvas` UI initially, lab toggle writes the core field.
2. **Label counter home (Slice 3):** lift `labelFor`/`paneCounters` to core (parity, stable titles) vs derive ordinal (less state). Recommendation: lift.
3. **Eager-bundle weight:** moving `capturedRunStore` to `model/` adds it to the eager prod bundle. It imports only `api` + `stores/persistence` + `types` + `zustand` (light); **xterm stays lazy** in the viewer chunk. Verify the bundle analyzer (`just www analyze`) shows no eager xterm pull after the move.
4. **`registerLifecycle` retention:** keep the runtime-override seam (tests/future) or remove for minimalism. Recommendation: keep the function, delete only the lab call.
5. **Director roster:** `stopRun` notes "leaves the director roster." Confirm any `/canvas` live-run roster reflects stop the same way the lab does (likely already core via `list_runs`, but verify before Slice 4 ships).
6. **`CLOSE_DELAY_MS` window (`paneAffordances.dismissPane`):** `onClose` fires after a setTimeout; a navigation/unmount during the window must still reach `stopRun`. Confirm existing lab behavior covers this (it does today on `/canvas-lab`); no new risk, but call it out in Slice 1 test coverage.

## Verification posture
Every slice gates on `cd www && just check` (`format lint typecheck`) and `cd www && just test` verbatim. Leak-safety is proven by a **core** test that resolves the captured-run `onClose` without importing any lab module, plus a `canvasStore` close→`DELETE` assertion — not by a comment or a session note.
