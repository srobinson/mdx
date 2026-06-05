---
title: Launcher Action Interaction Model — Declarative Dispatch Proposal
type: projects
tags: [frontend, transport-matters, www, launcher, command-center, design]
summary: Replace the scattered per-kind dispatch branches in useCommandCenter with a declarative per-action Interaction (lifecycle verbs) resolved from a pure table in commandModel.
status: active
source: frontend-engineer
confidence: high
created: 2026-06-19
updated: 2026-06-19
---

# Launcher Action Interaction Model

Independent design proposal. Design only, no code. Scope: `www/src/session-canvas/launcher/`.

## Core idea (one line)

Give every action a declarative **`Interaction`** — a pair of lifecycle verbs, one for `↵`, one for `→` — resolved from a single pure table in `commandModel`, and turn `useCommandCenter` into a generic interpreter that dispatches by **lifecycle verb**, never by command kind.

## The problem, precisely

On `feat/theme-cycle`, per-command behavior is smeared across two handlers in `useCommandCenter`, with the *same* kind decided in both places:

- `runAction` branches four ways: `enter` → descend; `command`+`retry-agents` → `retry()` stay-open; `command`+`cycle-theme` → `close()` only (commit, no dispatch); default → `onCommand` + `close`.
- `onInputKeyDown`'s `ArrowRight` branch decides *again*: `cycle-theme` → `onCommand` + stay-open; `enter` → descend; else nothing.
- Two type guards exist only to feed those branches: `isCycleThemeAction`, `isEnterAction`.

`cycle-theme` is the proof of the smell: its behavior is split across `runAction` (commit on `↵`), `onInputKeyDown` (advance on `→`), and a guard. Every future "stays open / steps / repeats" command (a density stepper, a zoom nudge, a font-size cycle) repeats that three-place edit. That is the edge-case pile Stuart called.

The behaviors live on two axes that are currently tangled:
1. **Lifecycle** — what a gesture does to the palette + whether it fires the effect (close / stay-open / descend / commit-close / ignore).
2. **Effect routing** — *where* a fired command goes (`onCommand` to the canvas, or the hook-local `retry`).

The fix separates them: lifecycle becomes fully declarative data; effect routing collapses to one table-driven sink.

## The abstraction — `commandModel.ts` (pure, unit-testable)

Co-located with the `LauncherCommand` / `RowAction` unions, because these files already own the model as pure data (no React, no stores).

```ts
/**
 * What a single gesture does to the palette. A closed set of verbs — the
 * dispatcher switches over THIS, never over command kinds. Illegal mixes
 * (e.g. "descend AND fire") are unrepresentable.
 */
export type Lifecycle =
  | "descend"       // enter the action's target scope; clear query; stay open
  | "run-close"     // fire the effect, then close the palette
  | "run-stay"      // fire the effect; palette stays open (→ repeats by re-firing)
  | "commit-close"  // close WITHOUT firing (keep whatever was previewed live)
  | "none";         // ignore this gesture (let the keypress fall through)

/** Per-action key bindings. `↵`/click read `enter`; `→` reads `advance`. */
export interface Interaction {
  enter: Lifecycle;
  advance: Lifecycle;
}

/** Entering a sub-scope: ↵ and → both descend; nothing to fire. */
const SCOPE_INTERACTION: Interaction = { enter: "descend", advance: "descend" };

/** Plain leaf command: ↵ runs and closes; → does nothing. The default. */
const RUN_AND_CLOSE: Interaction = { enter: "run-close", advance: "none" };

/**
 * The ONLY place a command's key behavior is declared. Anything absent uses
 * RUN_AND_CLOSE. New "custom-key" command? Add one entry here — the dispatcher
 * never changes.
 */
const COMMAND_INTERACTIONS: Partial<Record<LauncherCommand["kind"], Interaction>> = {
  // Live stepper: → advances the previewed theme and KEEPS the palette open;
  // ↵ commits the current preview by closing without firing again.
  "cycle-theme": { enter: "commit-close", advance: "run-stay" },
  // Refetch the fleet in place; stay open so the loading→result transition shows.
  "retry-agents": { enter: "run-stay", advance: "none" },
};

/** The interaction an action exposes. The single, pure kind→behavior map. */
export function interactionFor(action: RowAction): Interaction {
  return action.kind === "enter"
    ? SCOPE_INTERACTION
    : (COMMAND_INTERACTIONS[action.command.kind] ?? RUN_AND_CLOSE);
}
```

`RowAction` is **unchanged** — interaction is derived, not stored inline. Rationale under Trade-offs (the same command kind is emitted from multiple builders, e.g. `spawn` via `agentSpawnRows` feeds both `buildAgentRows` and `buildFlatSearchRows`; keying by kind is the DRY home, inline literals would duplicate).

> "Repeatable" needs no separate flag: it is exactly `advance: "run-stay"`. Holding `→` re-fires because `run-stay` neither closes nor moves the highlight, so the same row stays active and fires again. One concept, not two.

## The generic dispatcher — `useCommandCenter.ts`

### 1. Effect routing — one table-driven sink (replaces the `retry-agents` branch)

```ts
// Commands the hook owns locally (not canvas effects). Today: retry only.
const internalCommands = useMemo<Partial<Record<LauncherCommand["kind"], () => void>>>(
  () => ({ "retry-agents": retry }),
  [retry],
);

const runCommand = useCallback(
  (command: LauncherCommand) => {
    const internal = internalCommands[command.kind];
    if (internal) internal();
    else onCommand(command);
  },
  [internalCommands, onCommand],
);
```

This is **effect routing**, orthogonal to interaction. It stays hook-local because `retry` is a hook-scoped handler; a new *canvas* command never touches it.

### 2. The interpreter — `applyGesture` (replaces `runAction`)

```ts
const applyGesture = useCallback(
  (action: RowAction, lifecycle: Lifecycle) => {
    switch (lifecycle) {
      case "descend":
        if (action.kind === "enter") {
          setScope(action.scope);
          setQuery("");
        }
        return;
      case "run-close":
        if (action.kind === "command") runCommand(action.command);
        close();
        return;
      case "run-stay":
        if (action.kind === "command") runCommand(action.command);
        return;
      case "commit-close":
        close();
        return;
      case "none":
        return;
    }
  },
  [runCommand, close],
);
```

The `if (action.kind === …)` are **structural narrowing** (descend needs a scope, run needs a command), not behavior switches. The switch is over the closed `Lifecycle` verb set — a new command kind adds **zero** cases here. Add `default: assertNever(lifecycle)` to force exhaustiveness if a verb is ever added.

### 3. Both entry points read the table

```ts
const selectValue = useCallback(
  (value: string | undefined) => {
    const row = value ? rowByValue.get(value) : undefined;
    if (row?.action) applyGesture(row.action, interactionFor(row.action).enter);
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
        applyGesture(row.action, advance);
      }
      return;
    }
    const popsToRoot =
      event.key === "ArrowLeft" ? caret === 0 : event.key === "Backspace" && query.length === 0;
    if (popsToRoot && scope !== "root") {
      event.preventDefault();
      setScope("root");
    }
  },
  [query.length, highlighted, rowByValue, applyGesture, scope],
);
```

`activeInputRow` stays — it resolves *which* row is active for `→` (highlight or first selectable), a concern independent of behavior.

### What stays global, by design (do not over-abstract)

`←` / `Backspace` scope-pop and the window-capture `Escape`-closes effect are **palette navigation**, not per-action interaction — they act on the palette regardless of the highlighted row. They remain inline in `useCommandCenter` as the global grammar. Folding them into the per-action model would be the wrong kind of generalization. `Combobox.Root` keeps `closeOnSelect={false}`; the hook still owns every close. `onValueChange → selectValue` and `onKeyDown → onInputKeyDown` wiring in `CommandCenter` is untouched.

## Mapping table — every current kind onto the new model

| Action (kind) | `Interaction` | `↵` / click | `→` (advance) | Matches current `feat/theme-cycle` |
|---|---|---|---|---|
| `enter` (domain rows) | `SCOPE_INTERACTION` | `descend` → setScope + clear query, stay open | `descend` → same | `runAction` enter branch + ArrowRight `isEnterAction` branch |
| `spawn` | `RUN_AND_CLOSE` | `run-close` → `onCommand` + close | `none` | default `onCommand`+`close` |
| `reset-view` | `RUN_AND_CLOSE` | `run-close` | `none` | default |
| `focus-picker` | `RUN_AND_CLOSE` | `run-close` | `none` | default |
| `goto` | `RUN_AND_CLOSE` | `run-close` | `none` | default |
| `set-canvas-gesture-modifier` | `RUN_AND_CLOSE` | `run-close` | `none` | default |
| `retry-agents` | `{enter: run-stay}` | `run-stay` → `runCommand` (→ local `retry()`), stay open | `none` | `runAction` retry branch |
| `cycle-theme` | `{enter: commit-close, advance: run-stay}` | `commit-close` → `close()` only, no fire | `run-stay` → `runCommand` (→ `onCommand`), stay open, repeats | `runAction` cycle-theme close-only + ArrowRight cycle branch |

All eight rows reproduce existing behavior exactly. The two-place split for `cycle-theme` and `enter` collapses to one table row each.

## Migration sketch

**`commandModel.ts` gains** (~25 LOC, pure, fits its "deterministic functions of inputs" charter; file is 372 LOC, well under the 700 ceiling):
- `Lifecycle` type, `Interaction` interface.
- `SCOPE_INTERACTION`, `RUN_AND_CLOSE` consts; `COMMAND_INTERACTIONS` table.
- `interactionFor(action)` — the single pure kind→behavior map.

**`useCommandCenter.ts` loses**: `isCycleThemeAction`, `isEnterAction` guards; the `cycle-theme` branch in `runAction`; the `cycle-theme` + `enter` branches in `onInputKeyDown`'s `ArrowRight`.

**`useCommandCenter.ts` gains**: `internalCommands` + `runCommand` (effect router); `applyGesture` (verb interpreter, replaces `runAction`). `selectValue` and `onInputKeyDown` shrink to "look up lifecycle, apply." `activeInputRow` unchanged. Net: the hook holds zero per-command-kind knowledge.

**`CommandCenter.tsx`, `useLauncherRows.ts`**: untouched. Combobox props, row rendering, highlight/scroll, fleet status all unaffected.

**Tests**: `interactionFor` becomes a pure table test — assert each `LauncherCommand["kind"]` and `enter` yield the expected `Interaction`. Behavior coverage moves out of React key-event simulation into a deterministic unit test, mirroring the existing `commandModel` test style.

## Why it resists regressing into kind-branches

- **The dispatcher cannot see kinds.** `applyGesture` switches only over `Lifecycle`. To special-case a command kind there, you would have to introduce a `command.kind` read into a generic interpreter — an obvious, reviewable smell, with the declarative table sitting right next to the command union as the path of least resistance.
- **One source of truth, one axis.** Behavior is keyed once by command kind in `COMMAND_INTERACTIONS`, not smeared across `↵` and `→` handlers. The duplication that let `cycle-theme` drift between `runAction` and `onInputKeyDown` is structurally gone: both handlers now route through `applyGesture`, differing only in which verb (`enter` vs `advance`) they pull.
- **Additivity.** New default command → zero edits (falls through to `RUN_AND_CLOSE`). New custom-key command → one `COMMAND_INTERACTIONS` entry. New genuinely-new capability (e.g. a `descend-and-run` verb) → one `Lifecycle` case, caught by `assertNever`. Each extension touches exactly one declarative site.

## Trade-offs and honest cons

- **`interactionFor` is still a function with a lookup — "did you just move the switch?"** Partly: but it moved *out of the renderer hook into the pure model*, collapsed from two smeared handlers into one kind→`Interaction` map, became *data* (a `Record`), and the dispatcher no longer knows kinds at all. The eliminated thing is the *duplication across `↵` and `→`*, not the existence of a mapping.
- **One residual hook-side branch — `internalCommands` (retry routing).** Kept as a table, not a switch, and it is *effect routing*, not interaction. It is correctly hook-local because `retry` is hook-scoped; no canvas command ever touches it. Could inline as a single `if (command.kind === "retry-agents")`, but the record keeps "zero control-flow branches" literally true for ~3 lines.
- **No revert-on-cancel.** `cycle-theme` applies live on each `→`, so `commit-close` (`↵`) and cancel (`Escape`/scrim) both just `close()`. A future "preview then revert on Escape" command would need a `cancel` lifecycle + a snapshot; deliberately not built now (YAGNI).

### Alternatives considered and rejected

- **Closures on rows** (`onEnter: () => void` per row): rejected — rows are built in pure `commandModel.ts` with no access to `onCommand`/`retry`/`setScope`. Closures would drag row-building into hook scope and break the unit-testable pure-model charter. The data+interpreter split preserves it.
- **Capability booleans** (`{ closesOnEnter, repeatsOnAdvance, descends, fires }`): rejected — boolean soup admits illegal combinations and forces the dispatcher to AND flags together (more branches). The closed `Lifecycle` verb set makes illegal states unrepresentable.
- **Inline `Interaction` literal on every row** (runner-up): viable and maximally "declarative on the data," but DRY-worse — `spawn` is emitted from two builders, so its interaction would be written twice. Keying by command kind in one table is the DRY home; `interactionFor` reconstitutes it per action.

## Idiomatic fit

Matches the existing split: `commandModel` stays the pure, deterministic, unit-testable model; `useCommandCenter` stays the "state + grammar" interpreter; `useLauncherRows` / `CommandCenter` stay untouched. No new files, no plugin registry, no version-suffixed names — one type, one interface, one table, one pure function in the model; one router + one interpreter in the hook.
