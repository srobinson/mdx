---
title: Launcher Action Interaction Model — Consensus Design (Authoritative)
type: projects
tags: [frontend, transport-matters, www, launcher, command-center, design, consensus]
summary: Declarative per-action Interaction (lifecycle verbs) for the ⌘K launcher; generic dispatcher with no command.kind branches; retry-as-effect; ←-restore-origin; sliced migration.
status: active
source: frontend-engineer
confidence: high
created: 2026-06-19
updated: 2026-06-19
---

# Launcher Action Interaction Model — Consensus Design

**Authoritative.** Both design agents signed off. This is the artifact the implementer follows. Scope: `www/src/session-canvas/launcher/` plus two touch-points in `www/src/session-canvas/components/CanvasSurface.tsx` and `www/src/stores/themeStore.ts`. Cite file + symbol; no version-suffixed names.

## Problem

Per-command interaction behavior is smeared across `useCommandCenter`'s `runAction` and `onInputKeyDown`, with the *same* command kind decided in both places (`cycle-theme` commits in `runAction`, advances in `onInputKeyDown`; two type guards `isCycleThemeAction` / `isEnterAction` feed them). Every future "steps / stays open / repeats" command repeats that multi-site edit. Goal: make interaction a declarative, reusable capability of an action so the dispatcher is generic and adding a command needs zero dispatcher branches.

## 1. The agreed model

Two axes, deliberately separated:

- **Lifecycle** — what a gesture does to the palette + whether it fires the effect. A **closed verb set**; the dispatcher switches only over this, never over command kind.
- **Effect routing** — *where* a fired action goes: a canvas `command` → `onCommand`; a palette-local `effect` → an internal sink. Routed by `RowAction` *variant*, not by a kind lookup.

```ts
// commandModel.ts — pure, no React, unit-testable (matches the file's existing charter)

/**
 * What a single gesture does to the palette. Closed set — the dispatcher
 * switches over THIS. Illegal mixes (descend AND fire) are unrepresentable.
 */
export type Lifecycle =
  | "descend"       // enter the action's target scope; clear query; stay open
  | "run-close"     // fire the effect, then close
  | "run-stay"      // fire the effect; palette stays open (→ repeats by re-firing)
  | "commit-close"  // close WITHOUT firing (keep whatever was previewed live)
  | "none";         // ignore this gesture; let the keypress fall through

/** Per-action key bindings. ↵/click reads `enter`; → reads `advance`. */
export interface Interaction {
  enter: Lifecycle;
  advance: Lifecycle;
}
```

**"Repeatable" is not a flag** — it is exactly `advance: "run-stay"`. Holding `→` re-fires because `run-stay` neither closes nor moves the highlight, so the same row stays active and fires again.

## 2. RowAction, the effect variant, and resolution

`retry-agents` is a command-center-local effect, not a canvas command. It is removed from `LauncherCommand` and modeled as a third `RowAction` variant. This drops the `CanvasSurface.useCanvasCommandHandler` no-op `case "retry-agents":` (the `switch (command.kind)` stays exhaustive without it).

```ts
// commandModel.ts

/** Leaf canvas effects dispatched out via onCommand. NOTE: no `retry-agents`. */
export type LauncherCommand =
  | { kind: "spawn"; harness: HarnessName; runtimeTemplate?: string }
  | { kind: "reset-view" }
  | { kind: "focus-picker" }
  | { kind: "goto"; path: string }
  | { kind: "cycle-theme" }
  | { kind: "set-canvas-gesture-modifier"; modifier: CanvasGestureModifier };

/** Command-center-local effects: handled inside the hook, never reach onCommand. */
export type LauncherEffect = "retry-agents";

export type RowAction =
  | { kind: "enter"; scope: LauncherScope }          // descend a scope
  | { kind: "command"; command: LauncherCommand }    // canvas effect → onCommand
  | { kind: "effect"; effect: LauncherEffect };      // palette-local → internal sink

const SCOPE_INTERACTION: Interaction = { enter: "descend", advance: "descend" };
const RUN_AND_CLOSE: Interaction = { enter: "run-close", advance: "none" };

/** The ONLY place a canvas command's key behavior is declared. Absent = RUN_AND_CLOSE. */
const COMMAND_INTERACTIONS: Partial<Record<LauncherCommand["kind"], Interaction>> = {
  // Live stepper: → advances the previewed theme and keeps the palette open;
  // ↵ commits the current preview by closing without firing again. (Added in Slice B.)
  "cycle-theme": { enter: "commit-close", advance: "run-stay" },
};

/** Interaction per palette-local effect. */
const EFFECT_INTERACTIONS: Record<LauncherEffect, Interaction> = {
  "retry-agents": { enter: "run-stay", advance: "none" },
};

/** The single, pure action→behavior map. The dispatcher reads only this. */
export function interactionFor(action: RowAction): Interaction {
  switch (action.kind) {
    case "enter":
      return SCOPE_INTERACTION;
    case "command":
      return COMMAND_INTERACTIONS[action.command.kind] ?? RUN_AND_CLOSE;
    case "effect":
      return EFFECT_INTERACTIONS[action.effect];
  }
}
```

The error-state retry row in `agentsStatusRows` (within `buildAgentRows`) changes its action from `{ kind: "command", command: { kind: "retry-agents" } }` to `{ kind: "effect", effect: "retry-agents" }`.

## 3. The generic dispatcher — `useCommandCenter`

```ts
// Palette-local effects: handlers that live in the hook (today: retry only).
const effectSink = useMemo<Record<LauncherEffect, () => void>>(
  () => ({ "retry-agents": retry }),
  [retry],
);

// Route a fired action to its sink. `command` → canvas; `effect` → local.
const fire = useCallback(
  (action: RowAction) => {
    if (action.kind === "command") onCommand(action.command);
    else if (action.kind === "effect") effectSink[action.effect]();
  },
  [onCommand, effectSink],
);

// The interpreter. Switches ONLY over Lifecycle; no command.kind anywhere.
// `origin` is the descending row's value, recorded for ←-restore (Slice B).
const applyGesture = useCallback(
  (action: RowAction, lifecycle: Lifecycle, origin?: string) => {
    switch (lifecycle) {
      case "descend":
        if (action.kind === "enter") {
          if (origin) descentStack.current.push({ parent: scope, originValue: origin });
          setScope(action.scope);
          setQuery("");
        }
        return;
      case "run-close":
        fire(action);
        close();
        return;
      case "run-stay":
        fire(action);
        return;
      case "commit-close":
        close();
        return;
      case "none":
        return;
    }
  },
  [fire, close, scope],
);
```

The `if (action.kind === …)` guards are **structural narrowing** (descend needs a scope, run needs an action to fire), not behavior switches. The `switch` is over the closed `Lifecycle` set — a new command kind adds **zero** cases. Add `default: assertNever(lifecycle)` to force exhaustiveness if a verb is ever introduced.

Both entry points read the table and become trivial:

```ts
const selectValue = useCallback(
  (value: string | undefined) => {
    const row = value ? rowByValue.get(value) : undefined;
    if (row?.action) applyGesture(row.action, interactionFor(row.action).enter, row.value);
  },
  [rowByValue, applyGesture],
);

const onInputKeyDown = useCallback(
  (event: KeyboardEvent<HTMLInputElement>) => {
    const caret = event.currentTarget.selectionStart ?? 0;
    if (event.key === "ArrowRight" && caret >= query.length) {
      const row = activeInputRow(rowByValue, highlighted);
      const advance = row?.action ? interactionFor(row.action).advance : "none";
      if (row?.action && advance !== "none") {
        event.preventDefault();
        applyGesture(row.action, advance, row.value);
      }
      return;
    }
    // ←/Backspace scope-pop — global navigation grammar (see §5).
    const pops =
      event.key === "ArrowLeft" ? caret === 0 : event.key === "Backspace" && query.length === 0;
    if (pops && scope !== "root") {
      event.preventDefault();
      popScope();
    }
  },
  [query.length, highlighted, rowByValue, applyGesture, scope, popScope],
);
```

`activeInputRow`, `close`, `rememberFocus`, `openScope`, `toggleRoot`, the lazy `useRuntimeTemplates` fetch, and the `useLauncherHotkeys` wiring are unchanged. `CommandCenter` keeps `closeOnSelect={false}` and its `onValueChange → selectValue` / `onKeyDown → onInputKeyDown` bindings; the hook still owns every close.

## 4. retry-agents realized as an effect (summary of the graft)

- `LauncherCommand` loses `{ kind: "retry-agents" }`.
- `RowAction` gains `{ kind: "effect"; effect: LauncherEffect }`; `LauncherEffect = "retry-agents"`.
- The retry row's action becomes `{ kind: "effect", effect: "retry-agents" }`.
- `fire` routes `effect` actions to `effectSink` (`retry`); `command` actions always go to `onCommand` — no command-kind routing branch remains.
- `CanvasSurface.useCanvasCommandHandler`: delete `case "retry-agents":` (verified present today as a no-op: "Owned inside the command center… never dispatched out"). The exhaustive `switch` compiles without it once the union member is gone.

## 5. ← restores the originating selection (descent-origin)

When `←`/`Backspace` pops a scope, return to the **parent** scope with the row that descended into the just-left scope **re-highlighted** (enter Settings → `←` → back at root with "Settings" highlighted, not the first row). This is global navigation state, not a per-action capability.

A small descent stack in the hook holds, per descent level, the scope to return to and the row value to re-highlight. Generalizable beyond today's single root↔scope level.

```ts
interface DescentFrame {
  parent: LauncherScope;  // scope to return to on pop
  originValue: string;    // row in `parent` that descended; re-highlight on pop
}
const descentStack = useRef<DescentFrame[]>([]);
```

- **Record** on `descend` (in `applyGesture`): push `{ parent: scope, originValue: origin }` (the current scope + the descending row's `value`, threaded from the call site).
- **Restore** on pop:

```ts
const popScope = useCallback(() => {
  const frame = descentStack.current.pop();
  setHighlighted(frame?.originValue);   // batched with setScope; see reliance below
  setScope(frame?.parent ?? "root");
}, [setHighlighted]);
```

**Reliance (must hold):** `useLauncherRows`' auto-highlight effect keeps the current highlight when it is still a valid, non-disabled row in the new `visibleRows`, else falls back to `firstSelectableValue`. Because `setHighlighted(origin)` is batched with `setScope(parent)` and `origin` (the `domain:<scope>` row) is valid in the parent's rows, the effect **keeps** the origin instead of resetting to the first row. This ordering is the load-bearing contract: the restore writes the same `highlighted` state the effect reads, and the effect's functional update preserves a still-valid value. `close()` continues to reset scope/query/highlight independently (full dismiss clears the stack implicitly on next open).

`reset` paths (`close`, `toggleRoot`, `openScope`) should clear `descentStack.current = []` so a fresh open starts clean.

## 6. Kept global (not per-action)

- **Escape closes**, always, via the existing window-capture listener (runs before Ark's document-level handler).
- **`←`/`Backspace` scope-pop** grammar (now `popScope`, §5).

These act on the palette regardless of the highlighted row; folding them into the per-action model would be the wrong generalization.

## 7. DEFERRED — YAGNI

The commit/cancel `CloseDisposition` + `onClose` rollback seam is **explicitly deferred**. `cycle-theme` applies live on each `→`, so commit (`↵`) == cancel (`Escape`/scrim) == `close()`; `commit-close` covers today. A future "preview then revert on Escape" command would add a `cancel` lifecycle + a snapshot. Not built now.

## 8. Full mapping table

| Action (kind) | `Interaction` | `↵` / click | `→` (advance) | Effect sink |
|---|---|---|---|---|
| `enter` (domain rows) | `SCOPE_INTERACTION` | `descend` → record origin, setScope, clear query | `descend` → same | — (scope nav) |
| `command` · `spawn` | `RUN_AND_CLOSE` | `run-close` → `onCommand` + close | `none` | `onCommand` |
| `command` · `reset-view` | `RUN_AND_CLOSE` | `run-close` | `none` | `onCommand` |
| `command` · `focus-picker` | `RUN_AND_CLOSE` | `run-close` | `none` | `onCommand` |
| `command` · `goto` | `RUN_AND_CLOSE` | `run-close` | `none` | `onCommand` |
| `command` · `set-canvas-gesture-modifier` | `RUN_AND_CLOSE` | `run-close` | `none` | `onCommand` |
| `command` · `cycle-theme` | `{enter: commit-close, advance: run-stay}` | `commit-close` → close only, no fire | `run-stay` → `onCommand(cycle-theme)`, stay open, repeats | `onCommand` |
| `effect` · `retry-agents` | `{enter: run-stay, advance: none}` | `run-stay` → `retry()`, stay open | `none` | `effectSink` |

## 9. Slice-able migration plan

### Slice A — behavior-preserving declarative refactor (NO UX change)

Refactor `useCommandCenter` onto the declarative model, reproducing **current `main` behavior** exactly.

- Add to `commandModel`: `Lifecycle`, `Interaction`, `SCOPE_INTERACTION`, `RUN_AND_CLOSE`, `EFFECT_INTERACTIONS`, `interactionFor`. `COMMAND_INTERACTIONS` is **empty** in this slice (no command overrides yet — `cycle-theme` keeps `main`'s `RUN_AND_CLOSE`: `↵` cycles once and closes).
- Introduce the `effect` `RowAction` variant + `LauncherEffect`; remove `retry-agents` from `LauncherCommand`; repoint the retry row; delete the `CanvasSurface` no-op case.
- Replace `runAction` with `fire` + `applyGesture`; rewrite `selectValue` and `onInputKeyDown` to read `interactionFor`. Delete `isCycleThemeAction`, `isEnterAction`. `←`/`Backspace` still pop to `root` (no origin restore yet); `applyGesture` may accept `origin` but it is unused this slice.
- **Verification:** no behavioral change. Existing launcher tests (`commandModel`, command-center keyboard/e2e) pass unchanged; add a pure `interactionFor` table test (assert each kind/effect → expected `Interaction`).

### Slice B — theme-cycle interactive behavior + ←-restore + cycleTheme NONE stop

- **One-line model change** proves the design: add `COMMAND_INTERACTIONS["cycle-theme"] = { enter: "commit-close", advance: "run-stay" }`. The `→`-stepper and `↵`-commit now work through the **unchanged** dispatcher — no `applyGesture` / `onInputKeyDown` edits.
- **←-restore-origin** (§5): add `DescentFrame`/`descentStack`, record on `descend`, `popScope` restoring highlight; clear the stack on `close`/`openScope`/`toggleRoot`.
- **`themeStore.cycleTheme`** (`www/src/stores/themeStore.ts`): wrap through `cycleThemeStops` = `[open-water (default), ...presetThemes without open-water, null]` where the trailing `null` is the **unthemed NONE stop**; `next = stops[(currentIndex + 1) % stops.length]`. This restarts at `open-water` after the NONE stop. (Reference impl: `feat/theme-cycle` `themeStore.cycleTheme` / `cycleThemeStops` at `db28b2e`.)
- **Verification:** `→` on the Cycle-theme row advances preview through every preset then the unthemed stop then back to open-water, palette open throughout; `↵` commits the current preview and closes without an extra step; enter Settings → `←` re-highlights "Settings" at root. Add focused tests for `cycleThemeStops` wrap (incl. NONE stop) and the descent-origin restore.

## 10. Why it resists regressing into kind-branches

- **The dispatcher cannot see kinds.** `applyGesture` switches only over `Lifecycle`; to special-case a kind you would have to add a `command.kind` read into a generic interpreter — an obvious, reviewable smell, with the declarative table sitting right next to the union as the path of least resistance.
- **One source of truth, one axis.** Behavior is keyed once by command kind in `COMMAND_INTERACTIONS` (and effect in `EFFECT_INTERACTIONS`), never smeared across `↵` and `→`. Both handlers route through `applyGesture`, differing only in which verb they pull. The duplication that let `cycle-theme` drift is structurally gone.
- **Additivity.** New default canvas command → zero edits. New custom-key command → one `COMMAND_INTERACTIONS` entry. New palette-local effect → one `LauncherEffect` member + one `EFFECT_INTERACTIONS` + one `effectSink` entry (TS forces all three). New genuinely-new verb → one `Lifecycle` case, caught by `assertNever`.

## 11. Idiomatic fit

No new files, no plugin registry, no version-suffixed names. `commandModel` stays the pure, deterministic, unit-testable model (the kind→behavior table and `interactionFor` live here); `useCommandCenter` stays the state-plus-grammar interpreter (`fire`, `applyGesture`, `popScope`, `descentStack`); `useLauncherRows` and `CommandCenter` are untouched except the retry row repoint. Two external touch-points: `CanvasSurface` (drop no-op) and `themeStore` (Slice B wrap).
