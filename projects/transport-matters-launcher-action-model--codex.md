# Launcher action interaction model proposal

## Scope and verified current shape

This proposal covers the command center row model and dispatcher. I verified the current checkout at `main`, `e6951ff`.

Relevant current facts:

| Area | Evidence | Current contract |
|---|---|---|
| Row action model | `www/src/session-canvas/launcher/commandModel.ts` `RowAction` | A row action is only `{ kind: "enter" }` or `{ kind: "command" }`. Key behavior is not row data. |
| Row structure | `www/src/session-canvas/launcher/commandModel.ts` `CommandRow` | Rows own presentation data and an optional `action`. Disabled rows are inert. |
| Dispatcher | `www/src/session-canvas/launcher/useCommandCenter.ts` `useCommandCenter` | `runAction` branches on `action.kind` and on `retry-agents`; `onInputKeyDown` branches on ArrowRight only for `enter` rows. |
| Ark consumption | `www/src/session-canvas/launcher/CommandCenter.tsx` `CommandCenter` | Ark selection funnels through `selectValue`; the component does not need to know action semantics. |
| Row lookup | `www/src/session-canvas/launcher/useLauncherRows.ts` `useLauncherRows` | `rowByValue` already gives the dispatcher the highlighted or selected row. |
| Leaf command owner | `www/src/session-canvas/components/CanvasSurface.tsx` `useCanvasCommandHandler` | Canvas owns leaf commands. `retry-agents` is present only as a no op safeguard because retry is actually command center local. |

Tree note: this checkout does not yet contain a `cycle-theme` ArrowRight branch in `useCommandCenter`. The design below handles the requested behavior without adding one.

## Design goal

Move keyboard behavior onto the row action. `useCommandCenter` should dispatch by generic interaction capabilities:

1. What Enter does.
2. What ArrowRight does.
3. Whether ArrowRight may repeat while the palette stays open.
4. Whether a close is a commit or cancel.

The dispatcher may branch on a small effect algebra. It must not branch on concrete `LauncherCommand.kind` values.

## Proposed TypeScript shapes

Replace `RowAction` with explicit interaction semantics:

```ts
export type CloseDisposition = "commit" | "cancel";

export type RowEffect =
  | { kind: "enter-scope"; scope: LauncherScope }
  | { kind: "command"; command: LauncherCommand }
  | { kind: "retry-agents" };

export type PaletteAfter =
  | { kind: "stay-open" }
  | { kind: "close"; disposition: CloseDisposition };

export type RowInteraction =
  | { kind: "none" }
  | { kind: "perform"; effect: RowEffect; after: PaletteAfter }
  | { kind: "close"; disposition: CloseDisposition };

export type RowInteractionTrigger = "enter" | "arrowRight";

export interface RowAction {
  interactions: Record<RowInteractionTrigger, RowInteraction>;
  /** True only when ArrowRight can fire repeatedly without closing the palette. */
  repeatable?: boolean;
  /** Optional lifecycle for preview style actions. Most rows leave this empty. */
  onClose?: Partial<Record<CloseDisposition, RowEffect>>;
}
```

Narrow `LauncherCommand` back to commands owned outside the command center:

```ts
export type LauncherCommand =
  | { kind: "spawn"; harness: HarnessName; runtimeTemplate?: string }
  | { kind: "reset-view" }
  | { kind: "focus-picker" }
  | { kind: "goto"; path: string }
  | { kind: "cycle-theme" }
  | { kind: "set-canvas-gesture-modifier"; modifier: CanvasGestureModifier };
```

`retry-agents` moves to `RowEffect` because it is local to `useCommandCenter` and should not leak into `CanvasSurface`.

Use helpers so row builders stay terse and consistent:

```ts
const noInteraction = { kind: "none" } satisfies RowInteraction;
const stayOpen = { kind: "stay-open" } satisfies PaletteAfter;
const closeCommit = { kind: "close", disposition: "commit" } satisfies PaletteAfter;

const enterScopeEffect = (scope: LauncherScope): RowEffect => ({ kind: "enter-scope", scope });
const commandEffect = (command: LauncherCommand): RowEffect => ({ kind: "command", command });
const retryAgentsEffect = (): RowEffect => ({ kind: "retry-agents" });

export function enterScopeAction(scope: LauncherScope): RowAction {
  const effect = enterScopeEffect(scope);
  return {
    interactions: {
      enter: { kind: "perform", effect, after: stayOpen },
      arrowRight: { kind: "perform", effect, after: stayOpen },
    },
  };
}

export function commandAction(command: LauncherCommand): RowAction {
  return {
    interactions: {
      enter: { kind: "perform", effect: commandEffect(command), after: closeCommit },
      arrowRight: noInteraction,
    },
  };
}

export function retryAgentsAction(): RowAction {
  return {
    interactions: {
      enter: { kind: "perform", effect: retryAgentsEffect(), after: stayOpen },
      arrowRight: noInteraction,
    },
  };
}

export function repeatableCommandAction(command: LauncherCommand): RowAction {
  const effect = commandEffect(command);
  return {
    interactions: {
      enter: { kind: "perform", effect, after: closeCommit },
      arrowRight: { kind: "perform", effect, after: stayOpen },
    },
    repeatable: true,
  };
}
```

If theme cycling later needs true preview rollback, keep the dispatcher unchanged and give that row `onClose` effects. The command owner can then interpret dedicated command payloads such as `cycle-theme advance`, `cycle-theme commit`, and `cycle-theme cancel`. That is a theme command contract change, not a command center dispatcher change.

## Generic dispatch flow

`useCommandCenter` changes from `runAction(action)` to `dispatchInteraction(row, trigger)`.

```ts
function executeEffect(effect: RowEffect): void {
  switch (effect.kind) {
    case "enter-scope":
      setScope(effect.scope);
      setQuery("");
      return;
    case "command":
      onCommand(effect.command);
      return;
    case "retry-agents":
      retry();
      return;
  }
}

function dispatchInteraction(row: CommandRow | undefined, trigger: RowInteractionTrigger): boolean {
  const action = row?.action;
  if (!action || row.disabled) return false;

  const interaction = action.interactions[trigger];
  switch (interaction.kind) {
    case "none":
      return false;
    case "close":
      close(interaction.disposition);
      return true;
    case "perform":
      executeEffect(interaction.effect);
      if (interaction.after.kind === "close") {
        close(interaction.after.disposition);
      }
      return true;
  }
}
```

Close should accept a disposition:

```ts
function close(disposition: CloseDisposition = "cancel") {
  const closeEffect = pendingCloseLifecycleRef.current?.[disposition];
  pendingCloseLifecycleRef.current = undefined;
  if (closeEffect) executeEffect(closeEffect);

  setOpen(false);
  setScope("root");
  setQuery("");
  restoreFocusRef.current?.focus?.();
  restoreFocusRef.current = null;
}
```

First migration can leave `pendingCloseLifecycleRef` unused. Keeping the disposition in the signature prevents another refactor when preview actions arrive.

Key handling becomes capability based:

```ts
const selectValue = useCallback(
  (value: string | undefined) => {
    const row = value ? rowByValue.get(value) : undefined;
    dispatchInteraction(row, "enter");
  },
  [rowByValue, dispatchInteraction],
);

const onInputKeyDown = useCallback(
  (event: KeyboardEvent<HTMLInputElement>) => {
    const caret = event.currentTarget.selectionStart ?? 0;

    if (event.key === "ArrowRight" && caret >= query.length) {
      const row = highlighted ? rowByValue.get(highlighted) : undefined;
      if (dispatchInteraction(row, "arrowRight")) event.preventDefault();
      return;
    }

    const popsToRoot =
      event.key === "ArrowLeft" ? caret === 0 : event.key === "Backspace" && query.length === 0;
    if (popsToRoot && scope !== "root") {
      event.preventDefault();
      setScope("root");
    }
  },
  [query.length, highlighted, rowByValue, dispatchInteraction, scope],
);
```

Escape, scrim click, interact outside, and hotkey close should call `close("cancel")`. Enter driven command completion calls `close("commit")` through row data.

## Current action mapping

| Current row or action | New row action helper | Enter | ArrowRight | Repeatable | Close behavior |
|---|---|---|---|---|---|
| Domain row, current `{ kind: "enter" }` | `enterScopeAction(scope)` | Enter scope, clear query, keep palette open | Same as Enter | No | Later dismiss is cancel unless another action commits. |
| Native and template spawn | `commandAction({ kind: "spawn", ... })` | Dispatch spawn, close commit | None | No | Commit close. |
| Canvas commands: reset view, focus picker, goto lab | `commandAction(command)` | Dispatch command, close commit | None | No | Commit close. |
| Settings command: set canvas gesture modifier | `commandAction({ kind: "set-canvas-gesture-modifier", modifier })` | Dispatch command, close commit | None | No | Commit close. |
| Retry agents | `retryAgentsAction()` | Call `retry()`, keep palette open | None | No | No outer command leak. |
| Cycle theme | `repeatableCommandAction({ kind: "cycle-theme" })` | Dispatch cycle theme, close commit | Dispatch cycle theme, keep palette open | Yes | Escape or outside close cancels the palette only. Add `onClose.cancel` later if theme rollback becomes product behavior. |
| Disabled status rows | No action | None | None | No | Inert. |

This table keeps all current kinds expressible without adding a new branch for `cycle-theme`, or for the next repeatable command.

## Migration sketch

1. In `www/src/session-canvas/launcher/commandModel.ts`:
   1. Add `CloseDisposition`, `RowEffect`, `PaletteAfter`, `RowInteraction`, `RowInteractionTrigger`, and the new `RowAction` interface.
   2. Remove `retry-agents` from `LauncherCommand`.
   3. Add action helper factories near the type definitions.
   4. Update row builders:
      1. `buildDomainRows` uses `enterScopeAction(scope)`.
      2. `agentSpawnRows`, `buildCanvasRows`, and gesture modifier rows use `commandAction(command)`.
      3. `agentsStatusRows` uses `retryAgentsAction()` for Retry.
      4. `buildSettingsRows` uses `repeatableCommandAction({ kind: "cycle-theme" })`.
2. In `www/src/session-canvas/launcher/useCommandCenter.ts`:
   1. Replace `runAction` with `executeEffect` and `dispatchInteraction`.
   2. Make `selectValue` dispatch the `enter` interaction.
   3. Make ArrowRight dispatch the `arrowRight` interaction for the highlighted row.
   4. Keep ArrowLeft and Backspace scope pop exactly as today.
   5. Change `close` to accept `CloseDisposition`; Escape and outside dismissal use cancel.
3. In `www/src/session-canvas/launcher/CommandCenter.tsx`:
   1. Keep Ark wiring unchanged except close calls pass cancel explicitly.
   2. Optional follow up: derive footer text from the highlighted row, for example show `→ repeat` when `row.action?.repeatable` is true.
4. In `www/src/session-canvas/components/CanvasSurface.tsx`:
   1. Delete the `retry-agents` no op case after it leaves `LauncherCommand`.
   2. Keep all canvas owned command handling unchanged.
5. Tests:
   1. Update `commandModel.test.ts` expected actions to the new data shape.
   2. Add pure tests for `enterScopeAction`, `commandAction`, `retryAgentsAction`, and `repeatableCommandAction`.
   3. Add a hook level test proving ArrowRight on cycle theme calls `onCommand({ kind: "cycle-theme" })` and leaves `open` true, while Enter closes.
   4. Add a regression test that the dispatcher does not need a command kind branch for repeatable behavior.

## Trade offs

| Choice | Benefit | Cost |
|---|---|---|
| Explicit `interactions` on every action | No hidden defaults, and TypeScript forces ArrowRight to be declared as real behavior or `none`. | Row fixtures become more verbose without helpers. |
| `RowEffect` algebra | Keeps the dispatcher generic while still allowing local effects like retry. | One central switch remains, but it is over effect categories rather than command kinds. |
| `CloseDisposition` now | Escape and Enter close paths become semantically clear, and preview actions have a future seam. | First migration may not use `onClose` yet. |
| Helper factories | Keeps builders DRY and avoids repeated shape literals. | Custom rows need a new helper when a genuinely new interaction pattern appears. |

## Why this resists regressing into kind branches

1. `useCommandCenter` reads `row.action.interactions[trigger]`; it never inspects `action.command.kind`.
2. Adding a new command with ArrowRight behavior is a row builder change, usually one helper call.
3. Local command center work, such as retrying agents, is modeled as a `RowEffect`, so it does not pollute the external `LauncherCommand` union.
4. Tests can assert capability data directly in `commandModel.test.ts`, before React is involved.
5. The model is closed and small. No plugin registry, no dynamic callbacks in row data, and no duplicate key handling tables.
