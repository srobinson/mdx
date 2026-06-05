---
title: Launcher NavFrame Navigation Model
type: projects
tags: [frontend, transport-matters, www, launcher, command-center, navigation]
summary: Concrete NavFrame stack design for nested launcher navigation over the existing Ark Combobox.
status: active
source: frontend-engineer
confidence: high
created: 2026-06-19
updated: 2026-06-19
---

# Launcher NavFrame Navigation Model

## Summary

Use one app owned `NavFrame[]` stack as the launcher navigation model. The top frame is the live scope, query, and controlled Ark highlight. Descend pushes a frame. Back pops a frame. The revealed frame already contains its query and highlight, so origin restore is intrinsic and needs no parallel `descentStack`.

This composes with the authoritative action model unchanged: `Lifecycle`, `Interaction`, and `interactionFor` keep their meaning. Only the `descend` verb implementation changes from `setScope` to `pushFrame`, and the global back grammar changes from `setScope("root")` to `popFrame`.

## Grounding

Authoritative inputs read:

- `~/.mdx/research/transport-matters-launcher-navigation-architecture.md`
- `~/.mdx/research/transport-matters-launcher-ark-ui-navigation.md`
- `~/.mdx/projects/transport-matters-launcher-action-model--consensus.md`

Current code symbols inspected:

- `www/src/session-canvas/launcher/commandModel.ts:LAUNCHER_SCOPES`
- `www/src/session-canvas/launcher/commandModel.ts:RowAction`
- `www/src/session-canvas/launcher/commandModel.ts:CommandRow`
- `www/src/session-canvas/launcher/commandModel.ts:buildDomainRows`
- `www/src/session-canvas/launcher/commandModel.ts:buildFlatSearchRows`
- `www/src/session-canvas/launcher/commandModel.ts:buildScopeRows`
- `www/src/session-canvas/launcher/commandModel.ts:filterRows`
- `www/src/session-canvas/launcher/useCommandCenter.ts:useCommandCenter`
- `www/src/session-canvas/launcher/useLauncherRows.ts:useLauncherRows`
- `www/src/session-canvas/launcher/CommandCenter.tsx:CommandCenter`

Current state to preserve:

- `LAUNCHER_SCOPES` is the page id registry.
- `DOMAINS` is the flat root domain registry.
- `buildDomainRows` turns each domain into a row whose action enters that scope.
- `buildScopeRows` resolves rows for one scope. Root with an empty query shows domains; root with a query searches agent, canvas, and settings rows.
- `useCommandCenter` owns `scope`, `query`, open state, close, direct scope open, select, and input key grammar.
- `useLauncherRows` builds the Ark collection and keeps a valid highlight.
- `CommandCenter` keeps one mounted Ark `Combobox.Root` with controlled `inputValue`, controlled `highlightedValue`, `closeOnSelect={false}`, and a window capture Escape close.

## Core types

`commandModel.ts` should define the navigation frame beside the other pure launcher model types.

```ts
export type LauncherDomainScope = Exclude<LauncherScope, "root">;

export interface NavFrame {
  scope: LauncherScope;
  query: string;
  highlightedValue?: string;
}

export function createRootNavFrame(highlightedValue?: string): NavFrame {
  return { scope: "root", query: "", highlightedValue };
}

export function createScopeNavFrame(scope: LauncherScope): NavFrame {
  return { scope, query: "", highlightedValue: undefined };
}

export function domainRowValue(scope: LauncherDomainScope): string {
  return `domain:${scope}`;
}
```

`domainRowValue` keeps `buildDomainRows` and direct `openScope` seeding DRY. It should replace any repeated string construction for `domain:${scope}`.

Runtime invariant:

```ts
const [navStack, setNavStack] = useState<NavFrame[]>(() => [createRootNavFrame()]);
const frame = navStack[navStack.length - 1] ?? createRootNavFrame();
```

The stack is never intentionally empty. Index `0` is always the root frame.

## Single source of navigation state

The top frame replaces the current separate `scope`, `query`, and `highlighted` state:

```ts
const scope = frame.scope;
const query = frame.query;
const highlighted = frame.highlightedValue;
```

All writes go through one top frame updater:

```ts
const updateTopFrame = useCallback((update: (frame: NavFrame) => NavFrame) => {
  setNavStack((stack) => {
    const topIndex = stack.length - 1;
    const current = stack[topIndex] ?? createRootNavFrame();
    return [...stack.slice(0, topIndex), update(current)];
  });
}, []);

const setQuery = useCallback(
  (query: string) => updateTopFrame((frame) => ({ ...frame, query })),
  [updateTopFrame],
);

const setHighlighted = useCallback(
  (highlightedValue: string | undefined) =>
    updateTopFrame((frame) => ({ ...frame, highlightedValue })),
  [updateTopFrame],
);
```

If `useLauncherRows` keeps the auto highlight effect, make it controlled: it receives `highlightedValue` and a setter that updates the top `NavFrame`. It must not keep a second `useState` for highlight.

## Navigation operations

### Reset

Full close and root open clear all navigation state:

```ts
const resetNavigation = useCallback(() => {
  setNavStack([createRootNavFrame()]);
}, []);
```

`close`, root toggle open, and any full dismiss call `resetNavigation`. `commit-close` and `run-close` route through `close`, so they also clear the stack. `run-stay` leaves the stack unchanged.

### Descend

Descend updates the parent frame with the activated row value, then appends the child frame:

```ts
const pushFrame = useCallback((target: LauncherScope, originValue: string) => {
  setNavStack((stack) => {
    const topIndex = stack.length - 1;
    const parent = stack[topIndex] ?? createRootNavFrame();
    const restoredParent = { ...parent, highlightedValue: originValue };
    return [
      ...stack.slice(0, topIndex),
      restoredParent,
      createScopeNavFrame(target),
    ];
  });
}, []);
```

The selected row value is stored only in the parent `NavFrame.highlightedValue`. There is no second descent structure, no parent enum, and no separate restore protocol. This also makes pointer selection reliable, even if Ark has not emitted a highlight change before selection.

### Back

Back pops one frame:

```ts
const popFrame = useCallback(() => {
  setNavStack((stack) => (stack.length > 1 ? stack.slice(0, -1) : stack));
}, []);
```

After the pop, the revealed top frame already has the parent query and highlighted row. Ark receives those values through controlled props and restores the visible state.

### Direct scope open

Hotkeys such as `openScope("agents")` should preserve the current one level back behavior by opening a stack with root as the base frame:

```ts
const openScope = useCallback((target: LauncherScope) => {
  rememberFocus();
  setHasOpened(true);
  setNavStack(
    target === "root"
      ? [createRootNavFrame()]
      : [
          createRootNavFrame(domainRowValue(target as LauncherDomainScope)),
          createScopeNavFrame(target),
        ],
  );
  setOpen(true);
}, [rememberFocus]);
```

Implementation should avoid the cast by narrowing `openScope` targets or adding a small helper that returns the domain row value only for scopes present in `DOMAINS`.

## Ark Combobox integration

Keep a single Ark Combobox. Do not introduce Tree View, Menu, cmdk, or kbar.

`CommandCenter` bindings become:

```tsx
<Combobox.Root
  closeOnSelect={false}
  collection={center.collection}
  highlightedValue={center.highlighted ?? null}
  inputValue={center.query}
  onHighlightChange={(details) => center.setHighlighted(details.highlightedValue ?? undefined)}
  onInputValueChange={(details) => center.setQuery(details.inputValue)}
  onValueChange={(details) => center.selectValue(details.value[0])}
  open
  selectionBehavior="clear"
  value={[]}
>
```

The source of `center.query`, `center.highlighted`, and `center.scope` changes to the top `NavFrame`; the Ark contract does not change.

Key handling stays narrow:

```ts
const onInputKeyDown = useCallback((event: KeyboardEvent<HTMLInputElement>) => {
  const caret = event.currentTarget.selectionStart ?? 0;

  if (event.key === "ArrowRight" && caret >= query.length) {
    const row = highlighted ? rowByValue.get(highlighted) : undefined;
    const advance = row?.action ? interactionFor(row.action).advance : "none";
    if (row?.action && advance !== "none") {
      event.preventDefault();
      applyGesture(row, advance);
    }
    return;
  }

  const wantsBack =
    event.key === "ArrowLeft"
      ? caret === 0
      : event.key === "Backspace" && query.length === 0;

  if (wantsBack && navStack.length > 1) {
    event.preventDefault();
    popFrame();
  }
}, [query.length, highlighted, rowByValue, navStack.length, popFrame, applyGesture]);
```

Do not intercept ArrowLeft when the caret is not at the start. Do not intercept Backspace when the current frame query is nonempty. Do not intercept ArrowRight unless the caret is at the end and the highlighted row has a non `none` advance lifecycle.

Keep the existing window capture Escape behavior from `useCommandCenter`: Escape closes the whole palette before Ark handles the event. It should not pop one frame in this design, because the current product grammar already uses Escape as full dismiss and uses ArrowLeft or empty Backspace for scope back.

## Composition with the action model

The consensus model remains the interaction contract:

```ts
export type Lifecycle = "descend" | "run-close" | "run-stay" | "commit-close" | "none";
export interface Interaction {
  enter: Lifecycle;
  advance: Lifecycle;
}
export function interactionFor(action: RowAction): Interaction;
```

The dispatcher should take a row, because descend needs the activated row value for parent frame highlight:

```ts
const applyGesture = useCallback(
  (row: CommandRow, lifecycle: Lifecycle) => {
    const { action } = row;
    if (!action) return;

    switch (lifecycle) {
      case "descend":
        if (action.kind === "enter") pushFrame(action.scope, row.value);
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
  [pushFrame, fire, close],
);
```

The `action.kind === "enter"` guard is structural narrowing so TypeScript can read `scope`. Behavior still branches only on `Lifecycle`; no command kind dispatch returns.

`selectValue` becomes:

```ts
const selectValue = useCallback(
  (value: string | undefined) => {
    const row = value ? rowByValue.get(value) : undefined;
    if (row?.action) applyGesture(row, interactionFor(row.action).enter);
  },
  [rowByValue, applyGesture],
);
```

`retry-agents`, `cycle-theme`, and every canvas command retain the consensus action model behavior:

- `descend` pushes.
- `run-close` fires then closes, clearing the stack.
- `commit-close` closes without firing, clearing the stack.
- `run-stay` fires and leaves the stack, query, and highlight untouched.
- `none` lets the key fall through.

## Scope and data model

Keep `DOMAINS` flat. It is the root page registry, not a tree:

```ts
interface LauncherDomain {
  scope: LauncherDomainScope;
  title: string;
  subtitle: string;
  accelerator?: string;
}

const DOMAINS: LauncherDomain[] = [/* current domain rows */];
```

Do not turn `DOMAINS` into nested data. General nesting is expressed by rows that enter another scope:

```ts
export type RowAction =
  | { kind: "enter"; scope: LauncherScope }
  | { kind: "command"; command: LauncherCommand }
  | { kind: "effect"; effect: LauncherEffect };
```

Parentage is the stack. A row says where it goes next. The stack says where back returns. This supports deeper nesting without adding a static parent map or hardcoding `root` as every parent.

Frame row resolution stays simple:

```ts
const rows = buildScopeRows(frame.scope, inputs, frame.query);
const visibleRows = filterRows(rows, frame.query);
```

Today, `buildScopeRows` can keep its current switch. When a deeper page ships, add the new page id and page row builder there. If future nested pages need dynamic ids, extend `LauncherScope` deliberately at that time, for example with a typed page id helper, rather than moving the current root domain registry into a speculative tree.

If a future flat search result must descend into a deep page, add an explicit row target path at that point:

```ts
export interface CommandRow {
  value: string;
  title: string;
  subtitle?: string;
  group: string;
  disabled?: boolean;
  action?: RowAction;
  targetPath?: LauncherScope[];
}
```

Do not add this now. Current root flat search returns leaf commands, so the simple single target scope remains sufficient.

## Type to search

Search is per frame.

- Root frame, empty query: show root domains.
- Root frame, nonempty query: preserve current flat search across agents, canvas, and settings rows.
- Non root frame: filter only that scope's rows.
- Descend: push child frame with `query: ""`.
- Back: reveal the parent frame with its previous query and highlighted row.

This preserves current filtering while fixing the lost context on back.

## Behavior mapping

| Current behavior | NavFrame behavior |
| --- | --- |
| Open root palette | `navStack = [{ scope: "root", query: "" }]` |
| Root empty query shows domains | `buildScopeRows(frame.scope, inputs, frame.query)` with root and empty query |
| Root typing searches all current flat rows | root frame owns the typed query; `buildScopeRows` and `filterRows` preserve current behavior |
| Enter or ArrowRight on a domain row | `interactionFor(...).enter` or `.advance` returns `descend`; `pushFrame(target, row.value)` |
| In a child scope, query filters that scope | child frame owns its query |
| ArrowLeft at caret start | if stack depth is greater than one, `popFrame()` |
| Backspace with empty query | if stack depth is greater than one, `popFrame()` |
| Backspace with nonempty query | falls through to text editing |
| Pop from Settings to root | root frame is revealed with `highlightedValue: "domain:settings"` |
| Escape | window capture closes the whole palette and resets stack |
| Click scrim or interact outside | `close()` closes and resets stack |
| `openScope("agents")` | stack opens as root plus agents; back returns to root with Agents highlighted |
| `run-close` command | fire effect, close, reset stack |
| `commit-close` command | close, reset stack, do not fire |
| `run-stay` command or effect | fire, keep current frame stack |

## Migration slices

### Slice 1: Consensus action model

Implement the consensus action model as written, except keep the `NavFrame` direction in mind so no new code depends on a lasting `descentStack` abstraction.

- Add `Lifecycle`, `Interaction`, `LauncherEffect`, and `interactionFor` in `commandModel.ts`.
- Move `retry-agents` from `LauncherCommand` to `LauncherEffect`.
- Replace `useCommandCenter.runAction` with `fire` and `applyGesture`.
- Keep current behavior until the nav stack lands.

### Slice 2: NavFrame stack

Replace `scope`, `query`, and `useLauncherRows` internal highlight state with `navStack`.

- Add `NavFrame`, `createRootNavFrame`, `createScopeNavFrame`, and `domainRowValue`.
- Change `useCommandCenter` to derive `scope`, `query`, and `highlighted` from the top frame.
- Change query and highlight setters to update the top frame.
- Change `descend` to `pushFrame`.
- Change back grammar to `popFrame`.
- Change reset paths to set one root frame.
- Make `useLauncherRows` highlight control write to the top frame, not to local state.

### Slice 3: Interactive commands

Apply the consensus command behavior updates after the generic model is in place.

- `cycle-theme` uses `{ enter: "commit-close", advance: "run-stay" }`.
- `retry-agents` remains a local effect with `run-stay` on enter.
- No dispatcher changes should be required for either behavior.

## Verification plan for implementation

When this design is implemented, prove the behavior with focused tests before the repo gates:

- `interactionFor` table test for every row action variant.
- Nav helper tests for root reset, push, pop, and direct scope open.
- Command center keyboard test: Enter Settings, ArrowLeft at caret start, root restores Settings highlight.
- Command center keyboard test: Backspace edits nonempty query and only pops when query is empty.
- Command center keyboard test: ArrowRight at caret end descends; ArrowRight in the middle of input does not.
- Command center test: Escape closes and the next open starts from a single root frame.
- Command center test: `run-stay` leaves the current frame query and highlight intact.
- Existing `commandModel` tests updated for `retry-agents` as `effect`.

Final gates should use repo recipes, not hand rolled equivalents:

```bash
just check
just test
```

## Trade offs

- Updating a small array on every query or highlight change is acceptable because command palettes have shallow stacks. It buys one source of truth and simple restore semantics.
- The selected row value is written into the parent frame during push. That is a small robustness step for pointer selection, and it still keeps restore state inside `NavFrame[]`.
- Keeping `DOMAINS` flat avoids a speculative tree model. Deeper nesting only needs additional rows that enter additional scopes.
- Keeping Escape as full dismiss preserves current product grammar. ArrowLeft and empty Backspace provide frame back.

## Why this removes the bolt on smell

The current and consensus intermediate shapes split one concept across multiple states: `scope`, `query`, `highlighted`, and a planned `descentStack`. `NavFrame[]` makes the navigation frame the unit of state. A parent frame carries the exact query and highlight that should be visible when it is revealed. A child frame carries its own query and highlight. The stack order carries parentage.

The result is minimal and general:

- no library swap
- no duplicate listbox owner
- no static parent tree
- no hardcoded pop to root
- no parallel origin stack
- no command kind branches in the dispatcher
