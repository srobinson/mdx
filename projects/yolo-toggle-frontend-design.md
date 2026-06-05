---
title: Bypass-permissions launcher toggle — frontend DRY seam
type: projects
tags: [frontend, launcher, command-center, captured-run, design-only]
summary: Single cleanest frontend seam for a launcher "Bypass all permission checks" toggle that rides into the spawn request.
status: active
source: frontend-engineer
confidence: high
created: 2026-06-19
updated: 2026-06-19
---

# Bypass-permissions launcher toggle — frontend seam (DESIGN ONLY)

**Feature.** One launcher Settings entry "Bypass all permission checks". `→` flips it on/off in place. Persisted global preference. When on, every spawned run carries a flag the backend turns into `claude --dangerously-skip-permissions` / `codex --yolo`.

**Recommended seam (one phrase):** mirror `cycle-theme` for the settings toggle, and mirror `oscColorReplies` (NOT `runtimeTemplate`) for the spawn-time flag — one persisted boolean in `capturedRunStore` serves both ends.

**DRY check.** No existing `bypassPermissions` / `yolo` / `skip-permissions` plumbing exists in `www/src` (clean slate). Backend already owns the arg-injection seam (`--dangerously-skip-permissions` appears in `transport_matters test_captured_run_web_separation` via `passthrough` / `default_client_passthrough`), so the frontend only needs to surface a boolean in the spawn body; backend translation is out of frontend scope.

---

## 1. How `buildSettingsRows` builds rows today, and the cleanest pattern to mirror

`commandModel buildSettingsRows(themeName, canvasGestureModifier)` emits two row shapes into `GROUP_SETTINGS`:

- **`cycle-theme`** — a SINGLE row. `action: { kind: "command", command: { kind: "cycle-theme" } }`, subtitle shows live state (`Current: ${themeName}`).
- **`set-canvas-gesture-modifier`** — N rows (one per `CANVAS_GESTURE_MODIFIERS`), each carrying a payload `{ modifier }`, with `trailing: "Current"` on the selected one. This is a multi-row SELECT pattern.

**Cleanest mirror for a boolean toggle = `cycle-theme`, not the gesture modifier.** A boolean is one in-place flip, so it wants ONE row whose `→` re-fires (like cycle-theme cycling), not N selectable rows. Recommended row in `commandModel buildSettingsRows`:

```
{
  value: "settings:bypass-permissions",
  title: "Bypass all permission checks",
  subtitle: bypassPermissions
    ? "On — spawned agents skip permission prompts"
    : "Off — spawned agents prompt for permissions",
  group: GROUP_SETTINGS,
  trailing: bypassPermissions ? "On" : "Off",
  action: { kind: "command", command: { kind: "toggle-bypass-permissions" } },
}
```

Label states: title constant (mirrors `cycle-theme`); `subtitle` + `trailing` reflect current `bypassPermissions` (mirrors how `set-canvas-gesture-modifier` reflects state). Default OFF.

`buildSettingsRows` gains a third param `bypassPermissions: boolean`, threaded exactly like `canvasGestureModifier`:
`commandModel ScopeRowInputs` (add field) → `commandModel buildScopeRows` (`settings` case + `commandModel buildFlatSearchRows` search path both pass it) → `buildSettingsRows`. Upstream: `useCommandCenter UseCommandCenterArgs` → `useLauncherRows` (the `ScopeRowInputs` memo) → `CommandCenter CommandCenterProps` → read in `CanvasSurface`.

## 2. How the gesture-modifier setting persists — the pattern to confirm/reuse

`keymapStore useKeymapStore` is a Zustand store wrapped in `persist` (`zustand/middleware`):
- **localStorage key:** `persistence FRONTEND_STORAGE_KEYS.keymapStore` (`"transport-matters-keymap"`).
- **storage:** `persistence createFrontendPersistStorage()`.
- **slice:** `keymapStore PersistedKeymapSlice { canvasGestureModifier }`, setter `keymapStore KeymapState.setCanvasGestureModifier`, with `version` / `migrate` (`keymapStore migrateKeymapState`) / `merge` / `partialize`.
- **"provider":** there is no React context provider — the value reaches the launcher by a non-reactive/selector store read in `CanvasSurface` (`useKeymapStore((s) => s.canvasGestureModifier)`) passed down as the `canvasGestureModifier` prop.

**Confirmed persistence approach for `bypassPermissions`:** the SAME Zustand `persist` mechanism. But the cleanest HOST is `capturedRunStore useCapturedRunStore`, not `keymapStore` — because that store already persists a sibling **spawn-time global boolean**, `capturedRunStore CapturedRunState.oscColorReplies`, with identical `persist` config (key `persistence FRONTEND_STORAGE_KEYS.capturedRunStore`, `migrate`, `partialize`). Hosting `bypassPermissions` there makes one field serve both the settings toggle and the spawn attach with zero cross-store reads (see §4). Add to `capturedRunStore`:
- field `bypassPermissions: boolean` (default `false`),
- action `toggleBypassPermissions()` (flip in store via `set((s) => ({ bypassPermissions: !s.bypassPermissions }))`) — mirrors the parameterless `themeStore cycleTheme` and the existing `capturedRunStore setOscColorReplies`,
- include `bypassPermissions` in this store's `migrate` and `partialize` next to `oscColorReplies` (default missing → `false`; inverse of `oscColorReplies`'s `!== false` default-true).

## 3. How a row's `→` action is modeled, and the cleanest in-place toggle

Action/interaction model (`commandModel`, interpreter in `useCommandCenter useLauncherActionInterpreter`):
- A row's `action` is a `commandModel RowAction` (`enter` | `command` | `effect`). `commandModel interactionFor(action)` returns `commandModel Interaction { enter, advance }` — `enter` = `↵`/click lifecycle, `advance` = `→` (ArrowRight) lifecycle (read in `useCommandCenter onInputKeyDown`; `enter` read in `useCommandCenter selectValue`).
- Lifecycles (`commandModel Lifecycle`): `descend | run-close | run-stay | commit-close | none`. The interpreter maps `run-stay` → `fire(action)` and KEEP open; `run-close` → fire + close; `commit-close` → close only. `fire` of a `command` calls `onCommand(action.command)`.
- Defaults: a command with no `COMMAND_INTERACTIONS` entry falls back to `RUN_AND_CLOSE` (`{ enter: "run-close", advance: "none" }`) — `→` does nothing. `set-canvas-gesture-modifier` uses this (multi-row select; `→` inert). **`cycle-theme` overrides it: `COMMAND_INTERACTIONS["cycle-theme"] = { enter: "commit-close", advance: "run-stay" }`** — `→` re-fires in place (cycles, palette stays), `↵` just closes.

**Cleanest single in-place toggle:** copy the `cycle-theme` interaction verbatim.
- Add command kind `{ kind: "toggle-bypass-permissions" }` to `commandModel LauncherCommand` (parameterless, mirrors `cycle-theme` — no `{ enabled }` payload; the store owns the flip).
- Add `COMMAND_INTERACTIONS["toggle-bypass-permissions"] = { enter: "commit-close", advance: "run-stay" }`.
- Result: `→` fires `toggle-bypass-permissions` and stays open (user sees `On`/`Off` flip and can flip back); `↵` commits-and-closes. Exactly the cycle-theme grammar.

## 4. How a spawn request is built, and where `bypassPermissions` attaches (least plumbing)

Spawn chain today:
`commandModel agentSpawnRows` builds `{ kind: "spawn", harness, runtimeTemplate? }` → dispatched via `useCanvasCommandHandler` (`CanvasSurface`, `spawn` case) → `canvasStore addCapturedRun(harness, runtimeTemplate)` → `spawn createCapturedRunRef(provider, label, runtimeTemplate)` (writes `runtimeTemplate` onto the `captured-run` `paneRecords` ref) → `viewers/registry` passes `contentRef.runtimeTemplate` to `CapturedRunPane` → `CapturedRunPane` calls `capturedRunStore ensureRun(runKey, provider, cwd, oscColorReplies, runtimeTemplate)` → `api createCapturedRun(harness, cwd, oscColorReplies, runtimeTemplate)` → `POST /v1/runs` body `{ harness, cwd?, oscColorReplies, runtimeTemplate? }`.

`runtimeTemplate` is threaded through the per-spawn ref because it is **per-row** (each template row launches a different template). **`bypassPermissions` is a GLOBAL preference — every spawn uses the current value — so threading it through command→ref→registry→pane is unnecessary plumbing.** The correct mirror is `oscColorReplies`: a store-resident global spawn-time boolean defaulted inside `capturedRunStore ensureRun` (`oscColorReplies = get().oscColorReplies`) and passed straight to `createCapturedRun`.

**Single attach point (the carrier `runtimeTemplate` already lands in):** `api createCapturedRun`'s `POST /v1/runs` body.
- Add param `bypassPermissions?: boolean` to `api createCapturedRun`; serialize it into the body as a sibling optional field next to `runtimeTemplate`.
- Source the value with ZERO new threading: in `capturedRunStore ensureRun`, read `get().bypassPermissions` (one-line mirror of the existing `oscColorReplies = get().oscColorReplies` default) and pass it to `createCapturedRun`.
- Net frontend plumbing: 1 new store field + 1 toggle action (`capturedRunStore`), 1 new `LauncherCommand` kind + 1 `COMMAND_INTERACTIONS` entry + 1 settings row + the `bypassPermissions` param thread for the row label (`commandModel`), 1 handler case in `CanvasSurface useCanvasCommandHandler`, 1 param on `api createCapturedRun`, 1 read in `ensureRun`. No change to the spawn command, the ref (`spawn createCapturedRunRef`), `paneRecords`, `viewers/registry`, or `CapturedRunPane`.

Backend then reads the new `CreateRunRequest` field and routes it to its existing passthrough seam (`--dangerously-skip-permissions` / `--yolo`) — backend domain, out of scope here.

---

## Recommended seam, summarized

| Concern | Reuse | Change |
|---|---|---|
| Settings row + label states | `commandModel buildSettingsRows` (mirror `cycle-theme` single-row) | 1 row `settings:bypass-permissions`; thread `bypassPermissions` like `canvasGestureModifier` |
| Persistence | `capturedRunStore useCapturedRunStore` `persist` (sibling of `oscColorReplies`) | add `bypassPermissions: boolean` (default false) + `toggleBypassPermissions()`; add to `migrate`/`partialize` |
| `→` toggle wiring | `commandModel` interaction model (mirror `cycle-theme`) | `LauncherCommand` `{ kind: "toggle-bypass-permissions" }` + `COMMAND_INTERACTIONS` `{ enter: "commit-close", advance: "run-stay" }`; `CanvasSurface useCanvasCommandHandler` case → `toggleBypassPermissions()` |
| Spawn attach | `oscColorReplies` (NOT `runtimeTemplate`) | `bypassPermissions?: boolean` body field in `api createCapturedRun`; defaulted in `capturedRunStore ensureRun` via `get().bypassPermissions` |
