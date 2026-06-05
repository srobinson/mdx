---
title: ⌘K Launcher Design — Authoritative (Action-Interaction Model + NavFrame Stack)
type: projects
tags: [frontend, transport-matters, www, launcher, command-center, action-model, nav-frame, ark-ui, consensus]
summary: The single implementer-facing design for the ⌘K launcher. Folds in the action-interaction model (Lifecycle / interactionFor / generic applyGesture) and replaces its §5 descentStack mechanism with one NavFrame[] navigation stack over the existing Ark Combobox. Top frame = live scope/query/highlight; descend=push, back=pop, restore-origin intrinsic + a click-safety stamp.
status: active
source: frontend-engineer
confidence: high
created: 2026-06-19
updated: 2026-06-19
---

# ⌘K Launcher Design — Authoritative

**This is the doc the implementer follows.** It **supersedes** `~/.mdx/projects/transport-matters-launcher-action-model--consensus.md` (folded in here) and **replaces that doc's §5 `descentStack` mechanism** with the `NavFrame[]` stack. Both design agents signed off on the consensus this consolidates.

**Scope:** `www/src/session-canvas/launcher/{commandModel.ts, useCommandCenter.ts, useLauncherRows.ts, CommandCenter.tsx}`, plus two external touch-points: `www/src/session-canvas/components/CanvasSurface.tsx` (`useCanvasCommandHandler`) and `www/src/stores/themeStore.ts` (`cycleTheme`). Cite file + symbol; no `file:line`; no version-suffixed names.

**Two ideas, separated:**
1. **Action-interaction model** — interaction is a declarative, reusable capability of an action; the dispatcher is generic and switches only over a closed `Lifecycle` verb set, never over command kind.
2. **NavFrame stack** — nested scopes are one app-owned navigation stack over the single Ark `Combobox`; the top frame is the live scope/query/highlight; descend pushes, back pops, restore-origin is intrinsic.

---

## 1. Action-interaction model

### 1.1 Lifecycle + Interaction (pure, `commandModel.ts`)

Two axes: **Lifecycle** (what a gesture does to the palette + whether it fires) and **effect routing** (where a fired action goes, by `RowAction` variant).

```ts
// commandModel.ts — pure, no React, unit-testable.

/** What a single gesture does to the palette. Closed set — the dispatcher
 *  switches over THIS. Illegal mixes (descend AND fire) are unrepresentable. */
export type Lifecycle =
  | "descend"       // enter the action's target scope (push a frame); stay open
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

"Repeatable" is not a flag — it is exactly `advance: "run-stay"`: holding `→` re-fires because `run-stay` neither closes nor moves the highlight.

### 1.2 RowAction, the effect variant, resolution (`commandModel.ts`)

`retry-agents` is a command-center-local effect, not a canvas command. It leaves `LauncherCommand` and becomes a third `RowAction` variant, which deletes the `CanvasSurface.useCanvasCommandHandler` no-op `case "retry-agents":` (the `switch (command.kind)` stays exhaustive once the union member is gone).

```ts
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

/** The ONLY place a canvas command's key behavior is declared. Absent = RUN_AND_CLOSE.
 *  Empty until Slice C adds cycle-theme. */
const COMMAND_INTERACTIONS: Partial<Record<LauncherCommand["kind"], Interaction>> = {};

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

### 1.3 Generic dispatcher (`useCommandCenter.ts`)

`fire` routes by variant; `applyGesture` switches only over `Lifecycle`. **Delta vs the consensus doc: `applyGesture` takes the ROW** (not just the action), so `descend` can stamp the activated row's value as the restore-origin (§2.3). No `origin` parameter is threaded separately.

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
const applyGesture = useCallback(
  (row: CommandRow, lifecycle: Lifecycle) => {
    const action = row.action;
    if (!action) return;
    switch (lifecycle) {
      case "descend":
        // descend stamps the activated row as the parent's restore-origin (§2.3).
        if (action.kind === "enter") descend(action.scope, row.value);
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
  [fire, close, descend],
);
```

The `if (action.kind === …)` guards are **structural narrowing** (descend needs a scope), not behavior switches. Add `default: assertNever(lifecycle)` to force exhaustiveness if a verb is ever introduced.

Both entry points read the table and stay trivial:

```ts
const selectValue = useCallback(
  (value: string | undefined) => {
    const row = value ? rowByValue.get(value) : undefined;
    if (row?.action) applyGesture(row, interactionFor(row.action).enter);
  },
  [rowByValue, applyGesture],
);
// onInputKeyDown → see §3.2 (caret-guarded → advance / ← / Backspace).
```

---

## 2. NavFrame stack

### 2.1 The frame + pure stack ops (`commandModel.ts`)

A frame is a page identity plus the two pieces of per-page state that must restore on return. The stack transitions are pure (the file's existing charter); `useCommandCenter` only wires them to `setStack`.

```ts
/** One level of the launcher navigation stack. The TOP frame is the live state. */
export interface NavFrame {
  scope: LauncherScope;        // page identity (the existing flat scope union)
  query: string;               // per-frame search; restored when revealed
  highlightedValue?: string;   // row to re-highlight when revealed (= restore-origin)
}

export function topFrame(stack: NavFrame[]): NavFrame {
  return stack[stack.length - 1];
}

/** A child frame: per-frame query resets (cmdk "reset search on navigate"). */
export function createScopeNavFrame(scope: LauncherScope): NavFrame {
  return { scope, query: "", highlightedValue: undefined };
}

/** The base frame. Defined via the scope factory so there is one shape. */
export function createRootNavFrame(): NavFrame {
  return createScopeNavFrame("root");
}

/** The combobox item value for a domain row. DRY: used by buildDomainRows + openScope seeding. */
export function domainRowValue(scope: LauncherScope): string {
  return `domain:${scope}`;
}

/** Descend: stamp the activated row's value into the PARENT frame (click-safe
 *  restore-origin, §2.3), then push the child. */
export function pushFrame(stack: NavFrame[], scope: LauncherScope, originValue: string): NavFrame[] {
  const parent: NavFrame = { ...topFrame(stack), highlightedValue: originValue };
  return [...stack.slice(0, -1), parent, createScopeNavFrame(scope)];
}

/** Pop one level; never empties the stack (the base root frame is the floor). */
export function popFrame(stack: NavFrame[]): NavFrame[] {
  return stack.length > 1 ? stack.slice(0, -1) : stack;
}

/** Immutable patch of the top frame (live query / highlight writes). */
export function updateTopFrame(stack: NavFrame[], patch: Partial<NavFrame>): NavFrame[] {
  return [...stack.slice(0, -1), { ...topFrame(stack), ...patch }];
}
```

`buildDomainRows` switches its `value:` to `domainRowValue(scope)` (was the inline `domain:${scope}` literal).

### 2.2 Top-frame-is-live wiring (`useCommandCenter.ts`)

The stack **replaces** the flat `scope` + `query` useState, the consensus §5 `descentStack` ref, **and** `useLauncherRows`' internal highlight `useState`. There is one structure answering "where am I and how do I get back."

```ts
const [stack, setStack] = useState<NavFrame[]>(() => [createRootNavFrame()]);
const frame = topFrame(stack);   // the live scope / query / highlight

const descend = useCallback(
  (scope: LauncherScope, originValue: string) =>
    setStack((s) => pushFrame(s, scope, originValue)),
  [],
);
const back = useCallback(() => setStack(popFrame), []);  // pops one level; no-op at root

const setQuery = useCallback((q: string) => setStack((s) => updateTopFrame(s, { query: q })), []);

// Keeps the SetStateAction contract: the auto-highlight effect calls it with an updater.
const setHighlighted = useCallback(
  (next: SetStateAction<string | undefined>) =>
    setStack((s) =>
      updateTopFrame(s, {
        highlightedValue: typeof next === "function" ? next(topFrame(s).highlightedValue) : next,
      }),
    ),
  [],
);
```

Reset paths re-seed the stack instead of clearing `scope`/`query` (and implicitly drop any descent — no separate stack to clear):

```ts
const close = useCallback(() => {
  setOpen(false);
  setStack([createRootNavFrame()]);
  restoreFocusRef.current?.focus?.();
  restoreFocusRef.current = null;
}, []);

// toggleRoot (open branch) + the open path: setStack([createRootNavFrame()]).

// openScope: seed a 2-frame stack so ← still returns to root, and pre-highlight the
// matching domain so backing out lands on it (faithful to descend-from-root).
const openScope = useCallback((target: LauncherScope) => {
  rememberFocus();
  setHasOpened(true);
  setStack(pushFrame([createRootNavFrame()], target, domainRowValue(target)));
  setOpen(true);
}, [rememberFocus]);
```

### 2.3 Restore-origin: intrinsic + the click-safety stamp

- **Keyboard ↵ / arrowing:** as the user arrows, Ark's `onHighlightChange` writes the top frame's `highlightedValue` live, so the parent frame *already* holds the highlighted row when descend fires. Backing out reveals it intact — intrinsic, no parallel structure.
- **Pointer click (the delta-1 robustness fix):** a click fires Ark's `onValueChange` and may **not** have emitted a preceding `onHighlightChange`, so the parent frame's highlight could be stale. `pushFrame(stack, scope, originValue = row.value)` therefore **stamps the activated row's value into the parent frame** before pushing the child. Restore-origin is correct for ↵, →, **and** click, with zero dependence on Ark's internal event ordering.

Crucially the origin lands in the **unified frame**, not a parallel `descentStack` — single-source-of-truth holds. `back` (= `popFrame`) reveals the parent frame with its stamped `highlightedValue` + its `query`; the auto-highlight effect (§3.3) keeps the still-valid highlight rather than resetting to first. `back` is bounded by the base frame (`popFrame` no-ops when `stack.length === 1`) and pops **one** level, so it scales to arbitrary depth with no hardcoded pop-to-root.

---

## 3. Ark Combobox integration

One mounted `Combobox` is the sole listbox / keyboard / focus / ARIA owner; the app owns only the nav grammar. `CommandCenter.tsx` needs **no structural change** — the hook still returns `scope` / `query` / `highlighted`, now read off the top frame.

### 3.1 Controlled bindings (`CommandCenter.tsx`, unchanged)

- `highlightedValue={center.highlighted ?? null}` ← `frame.highlightedValue`; `onHighlightChange → setHighlighted` writes the top frame.
- `inputValue={center.query}` ← `frame.query`; `onInputValueChange → setQuery` patches the top frame.
- `collection={center.collection}` is swapped per scope (rebuilt by `useLauncherRows` from `frame.scope` + `frame.query`); Ark re-runs filtering/highlight on the new flat collection, blind to scopes.
- `closeOnSelect={false}` (descend must not dismiss), `selectionBehavior="clear"`, `value={[]}` — unchanged.
- `onValueChange → selectValue`, `onKeyDown → onInputKeyDown`, `onInteractOutside → close`, scrim → close — unchanged.

### 3.2 Caret-guarded nav keys (`useCommandCenter.onInputKeyDown`)

Claim only the nav keys; everything else (↑↓ / Enter / Home / End / typeahead) falls through to Ark untouched. `preventDefault` fires **only** on claimed keys. `back` is bounded by `stack.length > 1` (the correct "is there a frame to pop" invariant, replacing the old `scope !== "root"` guard).

```ts
const onInputKeyDown = useCallback(
  (event: KeyboardEvent<HTMLInputElement>) => {
    const caret = event.currentTarget.selectionStart ?? 0;
    if (event.key === "ArrowRight" && caret >= frame.query.length) {
      const row = frame.highlightedValue ? rowByValue.get(frame.highlightedValue) : undefined;
      const advance = row?.action ? interactionFor(row.action).advance : "none";
      if (row?.action && advance !== "none") {
        event.preventDefault();
        applyGesture(row, advance);            // SCOPE_INTERACTION.advance === "descend"
      }
      return;
    }
    const pops =
      event.key === "ArrowLeft" ? caret === 0 : event.key === "Backspace" && frame.query.length === 0;
    if (pops && stack.length > 1) {
      event.preventDefault();
      back();
    }
  },
  [frame.query.length, frame.highlightedValue, rowByValue, applyGesture, stack.length, back],
);
```

### 3.3 `useLauncherRows` controlled-highlight inversion

`useLauncherRows` **drops** its internal `const [highlighted, setHighlighted] = useState(...)` and receives them as args (frame-backed, from `useCommandCenter`). The auto-highlight effect body is **unchanged**; it now normalizes the top frame's highlight through the passed setter. The hook becomes fully controlled — no second highlight owner.

```ts
// useLauncherRows args gain:
//   highlighted: string | undefined;
//   setHighlighted: Dispatch<SetStateAction<string | undefined>>;
// (scope, query, templates, status, themeName, canvasGestureModifier as today.)

// unchanged body — keeps a valid, selectable row highlighted as the set narrows:
useEffect(() => {
  setHighlighted((current) =>
    current && visibleRows.some((row) => row.value === current && !row.disabled)
      ? current
      : firstSelectableValue(visibleRows),
  );
}, [visibleRows]);
```

`useCommandCenter` passes `{ scope: frame.scope, query: frame.query, highlighted: frame.highlightedValue, setHighlighted, … }` in and consumes `{ collection, grouped, rowByValue, fleetStatus }` out. `useCommandCenter`'s return shape is unchanged (`scope`, `query`, `highlighted` now derive from the top frame), so `CommandCenter` and its scroll-into-view effect are identical.

### 3.4 Escape stays full-dismiss

The existing **window-capture** Escape listener (runs before Ark's document-level handler) stays and **closes the whole palette** from any state. ←/Backspace covers per-level back; Escape is **not** repurposed to pop one level (no retraining). Unchanged from today.

---

## 4. Data model

- **`LauncherScope` stays a flat union; `DOMAINS` stays a flat registry** keyed by `scope` (`{ scope, title, subtitle, accelerator }`), rendered by `buildDomainRows`. The scope union is a registry of *page identities*, not a tree.
- **Parentage is carried by the stack** — parent of current = `stack[stack.length - 2].scope`. No static parent-tree, no hardcoded "parent = root."
- **A frame resolves its rows** exactly as today: `buildScopeRows(frame.scope, inputs, frame.query)` → `filterRows` → `createListCollection`. Adding a deeper scope = one `LauncherScope` member + one `buildScopeRows` case + (if enterable) a row whose action is `{ kind: "enter", scope }`. Deeper nesting then works because `descend` pushes another frame and `back` pops one — **zero nav plumbing**.
- **Per-frame query.** Each frame owns its `query`; descend resets it to `""`; back restores the parent's intrinsically. Root's two-mode behavior is **unchanged**: empty query → `buildDomainRows` (the five domains); any query → `buildFlatSearchRows` (flat search across every agent + command, the Raycast model). Flat-search hits are fire-and-close leaves that never push/pop.
- **DEFERRED (YAGNI):** "type-to-search-across-all-scopes that descends into a deep result" needs an ancestor path to rebuild the stack. Model it then as an optional `targetPath?: LauncherScope[]` on the `enter` action so `descend` pushes multiple frames at once — a one-line type affordance, not a tree refactor. Not built now (today's root flat-search fires leaves).

---

## 5. Mapping tables

### 5.1 Action → behavior

| Action (kind) | `Interaction` | `↵` / click | `→` (advance) | Sink |
|---|---|---|---|---|
| `enter` (domain rows) | `SCOPE_INTERACTION` | `descend` → push frame, stamp origin = row.value | `descend` → same | — (nav) |
| `command` · `spawn` | `RUN_AND_CLOSE` | `run-close` → `onCommand` + close | `none` | `onCommand` |
| `command` · `reset-view` | `RUN_AND_CLOSE` | `run-close` | `none` | `onCommand` |
| `command` · `focus-picker` | `RUN_AND_CLOSE` | `run-close` | `none` | `onCommand` |
| `command` · `goto` | `RUN_AND_CLOSE` | `run-close` | `none` | `onCommand` |
| `command` · `set-canvas-gesture-modifier` | `RUN_AND_CLOSE` | `run-close` | `none` | `onCommand` |
| `command` · `cycle-theme` (Slice C) | `{enter: commit-close, advance: run-stay}` | `commit-close` → close only, no fire | `run-stay` → `onCommand(cycle-theme)`, stay open, repeats | `onCommand` |
| `effect` · `retry-agents` | `{enter: run-stay, advance: none}` | `run-stay` → `retry()`, stay open | `none` | `effectSink` |

### 5.2 Current `main` → NavFrame (behavior preserved)

| Today (`main`) | NavFrame model |
|---|---|
| `scope` useState (`useCommandCenter`) | `topFrame(stack).scope` |
| `query` useState (`useCommandCenter`) | `topFrame(stack).query` |
| `highlighted` useState (owned by `useLauncherRows`) | `topFrame(stack).highlightedValue` (owned by the stack) |
| descend: `setScope(action.scope); setQuery("")` | `descend(scope, row.value)` = `setStack(pushFrame)` |
| `←`/`⌫`: `setScope("root")` (hardcoded pop-to-root) | `back()` = `setStack(popFrame)` (pop one level) |
| ← guard `scope !== "root"` | `stack.length > 1` |
| (consensus §5 draft) `descentStack` ref + `origin` thread | **gone** — origin stamped into the parent frame |
| restore-origin = batched `setHighlighted(origin)` on pop | revealed frame already carries the stamped highlight |
| `close` resets `scope` + `query` | `close` re-seeds `stack` to `[createRootNavFrame()]` |
| `domain:${scope}` literal (buildDomainRows) | `domainRowValue(scope)` (also used by openScope seeding) |
| auto-highlight effect (`useLauncherRows`) | same effect body, normalizes the top frame via the passed setter |

---

## 6. Slice plan

Each slice ships independently and **gates on the www recipes** (`www/justfile`), run in `www/`: `just check` (format + lint + typecheck), `just test`, `just test-e2e`.

### Slice A — action-model refactor (behavior-preserving, NO UX change)

Refactor `useCommandCenter` onto the declarative model, reproducing current `main` behavior exactly.

- Add to `commandModel`: `Lifecycle`, `Interaction`, `SCOPE_INTERACTION`, `RUN_AND_CLOSE`, `EFFECT_INTERACTIONS`, `interactionFor`. `COMMAND_INTERACTIONS` is **empty** (no overrides yet — `cycle-theme` keeps `RUN_AND_CLOSE`).
- Introduce the `effect` `RowAction` variant + `LauncherEffect`; remove `retry-agents` from `LauncherCommand`; repoint the retry row; delete the `CanvasSurface.useCanvasCommandHandler` no-op case.
- Replace `runAction` with `fire` + `applyGesture` (taking the row); rewrite `selectValue` and `onInputKeyDown` to read `interactionFor`. Delete `isCycleThemeAction` / `isEnterAction`. `←`/`Backspace` still `setScope("root")`; descend still `setScope` + `setQuery("")` (the stack arrives in Slice B).
- **Gate:** no behavioral change. Existing launcher tests (`commandModel.test.ts`, `useLauncherHotkeys.test.ts`, e2e) pass unchanged; add a pure `interactionFor` table test (each kind/effect → expected `Interaction`). `just check && just test && just test-e2e`.

### Slice B — NavFrame stack (replaces the descentStack mechanism)

- `commandModel`: add `NavFrame`, `topFrame`, `createScopeNavFrame`, `createRootNavFrame`, `domainRowValue`, `pushFrame`, `popFrame`, `updateTopFrame`. Switch `buildDomainRows` value to `domainRowValue(scope)`.
- `useCommandCenter`: `stack` replaces `scope` + `query`; derive `frame`; `setQuery`/`setHighlighted` patch the top frame; `descend(scope, originValue)` / `back`; `close`/`toggleRoot`/`openScope` re-seed the stack. `applyGesture` stamps `row.value` on descend. `←`/`Backspace` → `back()` bounded by `stack.length > 1`. **No `descentStack`, no separate `origin` thread.**
- `useLauncherRows`: controlled-highlight inversion (frame-backed `highlighted` + `setHighlighted` args; drop the internal `useState`; effect body unchanged).
- `CommandCenter`: unchanged.
- **Gate:** restore-origin works for ↵, →, **and click** (enter Settings → `←` → back at root with `domain:settings` re-highlighted); descend resets query, back restores the parent query; `close`/`openScope` re-seed; a forward-looking two-level `push → push → pop → pop`. Pure tests in `commandModel.test.ts` (`pushFrame` stamps parent + resets child query; `popFrame` no-op at base + preserves revealed frame state; `updateTopFrame` touches only the top) + a `useCommandCenter` keyboard/nav test. `just check && just test && just test-e2e`.

### Slice C — cycle-theme interactive + themeStore wrap

- **One-line model change** proves the design: `COMMAND_INTERACTIONS["cycle-theme"] = { enter: "commit-close", advance: "run-stay" }`. The `→`-stepper and `↵`-commit now work through the **unchanged** dispatcher — no `applyGesture` / `onInputKeyDown` edits.
- `themeStore.cycleTheme` (`www/src/stores/themeStore.ts`): wrap through `cycleThemeStops` = `[open-water (default), ...presetThemes without open-water, null]` where the trailing `null` is the **unthemed NONE stop**; `next = stops[(currentIndex + 1) % stops.length]` (restarts at `open-water` after NONE).
- **Gate:** `→` on Cycle-theme advances preview through every preset → the unthemed stop → back to open-water, palette open throughout; `↵` commits the current preview and closes without an extra step. Tests for `cycleThemeStops` wrap (incl. NONE stop) + the stepper. `just check && just test && just test-e2e`.

---

## 7. Why it resists the bolt-on / hardcoding smell + idiomatic fit

- **One structure, one concept.** `scope` + `query` + the planned `descentStack` + `useLauncherRows`' internal highlight (four shapes modeling one navigation) collapse to a single `NavFrame[]`. The named anti-pattern (a descent structure *parallel* to the scope state) cannot recur — there is nothing to run parallel to. The click-safety origin lands **in** the frame, not beside it.
- **No hardcoded pop-to-root.** `back` pops one frame and scales to arbitrary depth; the one-level assumption (`setScope("root")`, "every parent is root") is gone.
- **Dispatcher stays kind-blind.** `applyGesture` switches only over `Lifecycle`; `descend`/`back` read `scope`/`stack` only. Re-introducing a `command.kind` read into the generic interpreter would be an obvious, reviewable smell, with the declarative table + pure stack helpers sitting right next to the unions as the path of least resistance.
- **Behavior keyed once.** Each command's key behavior lives once in `COMMAND_INTERACTIONS` (effects in `EFFECT_INTERACTIONS`), never smeared across `↵` and `→`. The duplication that let `cycle-theme` drift is structurally gone. Additivity: new default command → zero edits; custom-key command → one `COMMAND_INTERACTIONS` entry; new effect → one `LauncherEffect` + one `EFFECT_INTERACTIONS` + one `effectSink` entry (TS forces all three); new verb → one `Lifecycle` case caught by `assertNever`.
- **Pure, testable core; established split.** `commandModel` stays the pure, deterministic model (the kind→behavior table, `interactionFor`, and the stack transitions); `useCommandCenter` stays the state-plus-grammar interpreter (`fire`, `applyGesture`, `descend`, `back`, thin `setStack` wiring); `useLauncherRows` and `CommandCenter` stay thin Ark compositions. No new files, no plugin registry, no version-suffixed names. Two external touch-points only: `CanvasSurface` (drop no-op) and `themeStore` (Slice C wrap).
