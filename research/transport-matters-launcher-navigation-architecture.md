---
title: Command-Palette Navigation Architecture — Prior Art and a Recommendation for the Transport Matters Launcher
type: research
tags: [transport-matters, launcher, command-center, navigation, architecture]
summary: Every mature command palette models nested scopes as a single navigation/page STACK where back and selection-restore are intrinsic; recommend collapsing the launcher's flat `scope` state + the proposed parallel `descentStack` ref into one app-owned frame stack over the existing Ark Combobox.
status: active
confidence: high
created: 2026-06-19
updated: 2026-06-19
---

# Command-Palette Navigation Architecture — Prior Art and a Recommendation

## Executive Summary

The nested-scope navigation problem is solved identically across every mature command palette: nested scopes are a **navigation stack** (a page stack, a view stack, a step stack, or an action-ancestor chain), and **back + restore-the-prior-selection are intrinsic properties of the stack**, not a flat enum with hardcoded pop-to-root and not a parallel "descent" structure bolted alongside the current-scope state. The library verdict is equally unanimous: cmdk and kbar each own their own input, list, keyboard, focus, and ARIA, so layering them beside our Ark UI / zag Combobox produces two competing listbox owners. The recommendation is therefore to **adopt the cmdk page-stack *pattern* in-house over the existing Ark Combobox** (we already feed per-scope item sets into `createListCollection`, so we are 80% there), and to **replace both the flat `scope` useState and the consensus design's proposed parallel `descentStack` useRef with a single `NavFrame[]` stack whose top frame is the live scope/query/highlight**. This subsumes back-navigation and restore-origin into one source of truth, composes cleanly with the already-agreed `Lifecycle` / `interactionFor` action model (only the implementation of the `descend` verb and the global back grammar change), and is the smaller, more elegant version of the consensus migration's Slice B.

---

## 1. The current state (grounded in our code)

Read directly from `www/src/session-canvas/launcher/`:

- **Flat scope enum.** `commandModel.ts` defines `LAUNCHER_SCOPES = ["root","agents","canvas","workdir","settings","sessions"]` and `type LauncherScope = (typeof LAUNCHER_SCOPES)[number]`. A domain row's action is `{ kind: "enter"; scope }`.
- **Single scope state.** `useCommandCenter.ts` holds `const [scope, setScope] = useState<LauncherScope>("root")`, plus separate `query` and (in `useLauncherRows`) `highlighted` state.
- **Descend = `setScope`.** `runAction` does `if (action.kind === "enter") { setScope(action.scope); setQuery(""); }`.
- **Back is hardcoded pop-to-root.** `onInputKeyDown`: ArrowLeft at caret 0 / Backspace at empty query → `setScope("root")`. Every scope's parent is implicitly root; the model is exactly one level deep; the originating row is **not** restored (the auto-highlight effect resets to `firstSelectableValue`).
- **Forward = ArrowRight at caret end** fires the highlighted row's `enter` action.
- **Root is Raycast-style.** `buildScopeRows("root", …)`: empty query → five domain rows; any query → `buildFlatSearchRows` (flat search across every agent + command).
- **Ark Combobox owns the listbox.** `CommandCenter.tsx` is a thin Ark `Combobox.Root` (`closeOnSelect={false}`, `selectionBehavior="clear"`, controlled `inputValue`/`highlightedValue`, `createListCollection` from `useLauncherRows`). Escape is intercepted by a window-capture listener before Ark's document-level handler.

The consensus action model (`~/.mdx/projects/transport-matters-launcher-action-model--consensus.md`, authoritative, both design agents signed off) cleanly removes per-command `kind` branching via a closed `Lifecycle` verb set and an `interactionFor(action)` table. **That part is correct and this report does not disturb it.** The one place this report recommends a change is consensus **§5**, which keeps a *parallel* `descentStack = useRef<DescentFrame[]>([])` (storing `{ parent, originValue }`) beside `scope` and `query` to implement ←-restore-origin. That parallel structure — three state shapes (`scope`, `query`, `descentStack`) modeling one navigation concept — is the bolt-on the orchestrator flagged. The prior art shows it should be one structure.

---

## 2. The universal pattern: nested scope = a navigation STACK

Across five independent reference implementations, nested navigation is always a stack, and back is always "pop the stack."

### cmdk (pacocoursey / Vercel) — app-owned page stack
cmdk has **no built-in sub-menu primitive**; it owns list filtering, keyboard traversal, selection, and the listbox ARIA, while **the page stack is application state you compose on top**. The canonical idiom:

```tsx
const [pages, setPages] = useState<string[]>([])
const page = pages[pages.length - 1]          // current page = top of stack; undefined at root
// descend:
onSelect={() => setPages([...pages, 'projects'])}
// back (the load-bearing idiom):
onKeyDown={(e) => {
  if (e.key === 'Escape' || (e.key === 'Backspace' && !search)) {
    e.preventDefault()
    setPages((pages) => pages.slice(0, -1))     // pop
  }
}}
```

The `!search` guard means Backspace only navigates back when the input is already empty (otherwise it edits text). cmdk provides **no intrinsic restore-on-pop** — the app owns push/pop and any per-page state. Items per page are rendered conditionally on `page`. (This is exactly our `buildScopeRows(scope, …)` switch — we already implement cmdk's "different items per page" idiom; we just key it on a single `scope` state instead of a stack.) Source: pacocoursey/cmdk README and the "Nested items" guide.

### kbar (timc1) — internal descent over an action tree
kbar models actions as a **tree via `parent` ids**: each `Action` has an optional `parent`, and each materialized `ActionImpl` precomputes a root-first `ancestors: ActionImpl[]` chain plus `children`. Selecting a parent with children **descends by setting `currentRootActionId`** in kbar's own reducer; matches then filter to that root's `children`. Back is Backspace-on-empty popping to the parent:

```js
// KBarSearch.tsx
if (currentRootActionId && !search && event.key === "Backspace") {
  const parent = actions[currentRootActionId].parent;
  query.setCurrentRootAction(parent);     // undefined at top → back to root
}
```

The `ancestors` chain gives multi-level back for free. Critically, **kbar owns the descent state internally** (a reducer field), unlike cmdk where the app owns it. Search resets on root change via a `useEffect` keyed on `currentRootActionId`. There is no first-class breadcrumb; the search placeholder doubles as the context label. Source: timc1/kbar `main` source (`types.ts`, `action/ActionImpl.ts`, `KBarSearch.tsx`, `useMatches.tsx`).

### Raycast extension API — a stack of view components, intrinsic back
Raycast maintains a **navigation stack of view components**: the root command is the bottom, `push()` adds a view, `pop()` returns. `useNavigation()` returns `{ push, pop }`; the idiomatic descent is the declarative `<Action.Push target={<DetailView/>} />`. **Back is built into Raycast** ("When a user presses `ESC`, we automatically pop to the previous component"; `⌘-esc` pops to root). Each pushed view gets its **own search bar, `navigationTitle`, `searchBarPlaceholder`, and selection** — a changelog entry confirms cross-view search leakage was treated as a *bug* (v1.31.0), i.e. per-view input isolation is by design; per-view state retention on pop is the documented-component-isolation consequence. Lesson: navigation is a stack of views with intrinsic back and per-view state, never a flat scope enum. Source: developers.raycast.com (navigation, list, actions, changelog).

### VS Code QuickInput — back BUTTON primitive, app-owned step stack
VS Code ships only the back **button** (`QuickInputButtons.Back`: predefined icon/tooltip/top-left location, `Alt+←`); the **stack and the back semantics are the extension's**. The official `multiStepInput.ts` sample owns `private steps: InputStep[] = []` and implements back as a thrown `InputFlowAction.back` sentinel caught in a `stepThrough` loop that pops frames; accumulated answers are preserved by threading a mutable `state: Partial<State>` through every step. This is a **wizard / linear-flow** model (ordered steps), distinct from the **tree / scope** model of cmdk/kbar/Raycast. It is the right shape only for ordered prerequisite collection (e.g. a create-resource flow), not for an open-ended command hierarchy like ours. Source: microsoft/vscode-extension-samples `quickinput-sample/src/multiStepInput.ts`; VS Code API reference.

### UX references (Linear, Superhuman, Spotlight/Alfred)
- **Linear** popularized the contextual cmd+K that surfaces only context-applicable actions and uses select-to-descend, Backspace/Escape-to-return (the cmdk lineage). [medium-high confidence on contextual descent; medium on the exact Backspace mechanic — inferred from the cmdk pattern Linear is built on].
- **Superhuman** emphasizes **restoring the originally-focused element on dismiss** (track focus before open, return to it on close) — our code already does this via `restoreFocusRef`. Their writeup does not document nested-submenu back. [high confidence on focus-restore].
- **Alfred / Raycast**: Alfred defaults to a fallback search when nothing matches; Raycast generalizes this into a keyboard-first model with a built-in back stack (Escape pops one level, preserving prior screen/query). [medium confidence; secondary/observational].
- **Cross-cutting principle**: descending should preserve the parent's query + highlight so backing out restores prior context; dismissing the whole palette restores prior focus.

**Synthesis:** the only architectural variation is *who owns the stack* (app-owned in cmdk/VS Code; library-internal in kbar/Raycast). The stack itself, and "back = pop," and "restore the level you return to," are invariant. A flat enum with hardcoded pop-to-root is not present in any mature implementation.

---

## 3. Library vs in-house: keep Ark, adopt the *pattern*

**What Ark/zag Combobox already owns** (confirmed at zagjs.com/components/react/combobox and ark-ui.com/docs/components/combobox): the listbox keyboard interactions (ArrowDown/Up, Home/End, Enter-to-select, Escape-to-close), input focus management, open/close, highlight state, selection, and the WAI-ARIA combobox/listbox/option roles. It explicitly **does not own filtering** — items flow through `createListCollection` and the app filters in `onInputValueChange`. This is precisely the seam our launcher already uses.

**Adopting cmdk as a library beside Ark = two owners (reject).** cmdk's `Command` primitive *also* owns input handling, list rendering, arrow/Enter keyboard nav, automatic filtering+scoring, selection, and its own combobox/listbox/option ARIA roles. Layering it on Ark yields double key handling (both intercept Arrow/Enter/Escape), focus-trap conflicts, two filtering passes (zag's collection vs cmdk's scorer), and duplicate/colliding ARIA roles (two `role="listbox"` in one widget breaks the a11y tree).

**Adopting kbar as a library beside Ark = worse (reject).** kbar ships its own portal, positioner, `KBarSearch` input, reducer-driven nav, and `useMatches` — a *complete* palette, not a primitive. Beside Ark that is two full palettes (two inputs, two state machines, two portals).

**Adopt the cmdk page-stack PATTERN in-house (recommended).** Keep Ark Combobox as the sole listbox/keyboard/focus/ARIA owner. Add a small app-owned navigation stack that only swaps which item set is fed into `createListCollection` per level and handles Backspace-on-empty / Escape / → at the input level. This is cmdk's pattern minus the package: one keyboard owner, one filtering pass, one ARIA tree, **zero new dependencies**. Because Ark delegates filtering and item-supply to the app collection, per-level item sets are the intended extension point — and our `buildScopeRows` switch is already that extension point.

---

## 4. Composition with the agreed action model (the key requirement)

The consensus model has two orthogonal axes that this nav change must not disturb: **Lifecycle** (what a gesture does to the palette — `descend | run-close | run-stay | commit-close | none`, the only thing the dispatcher switches over) and **effect routing** (`command` → `onCommand`, `effect` → local sink, by `RowAction` variant). The nav stack swaps only the *implementation* of the `descend` verb and the global back grammar; the grammar and the `interactionFor` table are untouched.

- **"Enter scope" becomes "push frame".** Inside `applyGesture`, the `descend` case currently does `setScope(action.scope); setQuery("")`. Under the stack it becomes `pushScope(action.scope)` = `setStack(s => [...s, { scope: action.scope, query: "", highlightedValue: undefined }])`. `SCOPE_INTERACTION = { enter: "descend", advance: "descend" }` is unchanged; an `enter` action still descends on both ↵ and →.
- **Back stays global grammar.** `popScope` = `setStack(s => s.length > 1 ? s.slice(0, -1) : s)`. It remains the ←/Backspace-on-empty handler in `onInputKeyDown`, plus is reachable from Backspace-on-empty exactly as cmdk/kbar do. It reads/writes only the stack — never a command kind, so the no-kind-branching property is preserved.
- **Origin threading disappears.** Consensus §5 threads `origin = row.value` through `applyGesture`/`selectValue`/`onInputKeyDown` to push `{ parent, originValue }` onto `descentStack`. With the unified stack this is unnecessary: at descend time the *parent frame already holds* `highlightedValue = "domain:settings"` (the row the combobox had highlighted). Popping reveals that frame with its highlight intact. **Restore-origin is automatic.** Remove the `origin` parameter and the `descentStack` ref entirely.

Net effect on the action model: `interactionFor`, `Lifecycle`, `fire`, the effect sink, and the §2–§4/§6–§11 design are all preserved verbatim. Only §5 (the navigation-state mechanism) is replaced by the frame stack.

---

## 5. Data model: keep flat scope IDs, let the *stack* carry the tree

Two separable questions:

**(a) Runtime nav state — stack? Yes, unambiguously.** Replace `scope`/`query`/`highlighted`/`descentStack` with:

```ts
// commandModel.ts (pure, unit-testable — matches the file's existing charter)
export interface NavFrame {
  scope: LauncherScope;        // page identity
  query: string;               // restored when this frame is revealed
  highlightedValue?: string;   // row to re-highlight when revealed (restore-origin)
}
// useCommandCenter.ts
const [stack, setStack] = useState<NavFrame[]>([{ scope: "root", query: "", highlightedValue: undefined }]);
const frame = stack[stack.length - 1];   // the live scope/query/highlight
```

The **top frame is the live state**: Ark binds `inputValue = frame.query` and `highlightedValue = frame.highlightedValue`; `setQuery`/`setHighlighted` update the top frame immutably. Frames below the top are never mutated after descent, so restore-on-pop is free. There is **one** source of truth for "where am I and how do I get back."

**(b) Scope definitions — tree or flat registry? Keep `LauncherScope` flat.** The scope union is a registry of *page identities* (like cmdk's `pages: string[]` page names). The parent/child relationship is supplied at runtime by the stack (`parent of current = stack[len-2].scope`), so no static tree and no hardcoded "parent = root" is needed — deep nesting (agents → `agent:claude` → models) works by pushing more frames; back pops one level. `buildScopeRows(scope, …)` stays the per-scope page registry (add a `case` + builder per new scope). A static `parent`-tree (kbar style) is required **only** for "type-to-search-across-all-scopes that descends into a deep result," where a flat-search hit must reconstruct the ancestor stack — model that, when needed, as an optional `targetStack: LauncherScope[]` on the row so `descend` can push multiple frames at once. Today's root flat-search fires leaf commands (spawn / cycle-theme) that do not descend, so this is **YAGNI** until a searchable nested scope ships.

**Search across scopes coexists with the stack.** Root's Raycast model (empty → domains; query → flat search) is just the bottom frame; flat-search hits are fire-and-close leaves that never touch the stack. Per-frame query (descend pushes `query: ""`) matches cmdk's "reset search on navigate," and restoring the parent's query on pop matches Raycast's per-view search bar.

---

## 6. Back + restore-origin as intrinsic stack behavior

This is the orchestrator's core concern and the frame stack resolves it directly:

- `popScope` pops the top frame; the revealed frame still carries its `query` and `highlightedValue`; the combobox re-renders restored. **No parallel `descentStack`.**
- The load-bearing reliance from consensus §5 still holds and is now simpler: `useLauncherRows`' auto-highlight effect keeps a still-valid highlight rather than resetting to `firstSelectableValue`. Because the revealed frame's `highlightedValue` (the `domain:<scope>` row) is valid in the parent's rows, the effect preserves it. The frame *is* the saved highlight, so there is no separate `setHighlighted(origin)` batched-with-`setScope` choreography to get right.
- `close` / `toggleRoot` / `openScope` reset `stack` to `[{ scope: "root", query: "", highlightedValue: undefined }]`, so every fresh open starts clean (the equivalent of the consensus note to clear `descentStack` on those paths).

**Design alternative (for completeness):** the references literally describe a *snapshot/restore* variant — keep `query`/`highlighted` as separate live state, store only `{ scope, savedQuery, savedHighlight }` in frames, snapshot live→frame on descend and restore frame→live on pop. It keeps per-keystroke state off the stack but reintroduces a live-vs-saved duality and snapshot-timing edge cases (precisely the bolt-on subtlety we are trying to retire). Prefer the top-frame-is-live model; the per-keystroke array spread is negligible for a handful of frames.

---

## 7. Anti-patterns to avoid (the "what not to do")

1. **A descent structure parallel to the scope state** (consensus §5 `descentStack` ref beside `scope`/`query`). Three shapes modeling one concept; unify into one frame stack. *This is the named anti-pattern.*
2. **Flat scope enum with hardcoded pop-to-root** (`setScope("root")`). Does not scale past one level; loses the originating selection. Replaced by `popScope` over the stack.
3. **Per-command `kind` branching in the dispatcher.** Already solved by `interactionFor`; the nav stack must not reintroduce it — `descend`/`popScope` read scope/stack only.
4. **A second keyboard/listbox owner** (cmdk/kbar as a library beside Ark) → double key handling, focus traps, two filter passes, duplicate ARIA roles. Reuse Ark; add only the Backspace-on-empty / → / window-capture-Escape grammar at the input level (as the code already does).
5. **Losing query/selection on navigate.** A bare `setScope` + `setQuery("")` discards context; mature palettes restore it on pop. The frame stack restores intrinsically.
6. **Forgetting to reset the stack on full close/open** → stale frames leak into the next session. Reset to a single root frame on every dismiss/open.
7. **A static scope tree built before it is needed.** Deep nesting works from the stack alone; only "search-then-descend-deep" needs ancestor paths. Defer.

---

## 8. Recommendation for our launcher

**Headline:** Replace the flat `scope` useState and the consensus design's proposed parallel `descentStack` useRef with a **single app-owned `NavFrame[]` navigation stack** (top frame = live scope/query/highlight) layered over the **existing Ark Combobox** — i.e. adopt cmdk's page-stack *pattern*, not cmdk/kbar the *library*. Back and restore-origin become intrinsic stack operations; the agreed `Lifecycle` / `interactionFor` action model is preserved and only the `descend` verb and global back grammar change implementation.

Concrete shape:
- **`commandModel.ts`**: add the pure `NavFrame` type. `buildScopeRows`/`filterRows`/`groupRows`/`interactionFor` unchanged. `LauncherScope` stays a flat union (page-id registry).
- **`useCommandCenter.ts`**: `stack: NavFrame[]` replaces `scope` + `query` + the planned `descentStack`; `frame = stack.at(-1)`; `setQuery`/`setHighlighted` update the top frame; `pushScope(scope)` implements the `descend` lifecycle; `popScope()` implements ←/Backspace-on-empty; `close`/`toggleRoot`/`openScope` reset the stack. Drop the `origin` parameter threaded through `applyGesture`/`selectValue`/`onInputKeyDown`.
- **`useLauncherRows.ts`**: derive rows from `frame.scope`/`frame.query`; the auto-highlight effect preserves the restored highlight (it already does).
- **`CommandCenter.tsx`**: bind `inputValue`/`highlightedValue` to the top frame; otherwise unchanged (Ark stays the listbox owner).

**Migration (composes with the consensus slice plan):**
- **Slice A (consensus, unchanged):** behavior-preserving declarative refactor onto `Lifecycle` / `interactionFor`. Descend still `setScope`; back still pops to root.
- **Slice B′ (this report, replacing consensus §5's mechanism):** introduce `NavFrame[]` as the single nav source of truth; `descend` → push frame; `popScope` → pop frame; restore-origin intrinsic. Delete the `descentStack` ref + `origin` threading the consensus draft planned. Strictly smaller than the consensus §5. Tests: push/pop, restore-origin (enter Settings → ← → "Settings" re-highlighted at root), reset-on-close, and a forward-looking multi-level push/pop once a second nesting level lands.

This subsumes ←-restore-origin and the action model under one structure, scales to arbitrary nesting, adds no dependency, and keeps Ark as the single keyboard/focus/ARIA owner.

---

## Sources Consulted

**Reference implementations (source-level):**
- cmdk — github.com/pacocoursey/cmdk (README "Sub-menus / pages"); the "Nested items" guide (Mintlify mirror). App-owned `pages` stack; Backspace-on-empty pop; no intrinsic restore.
- kbar — github.com/timc1/kbar `main` (`src/types.ts`, `src/action/ActionImpl.ts`, `src/KBarSearch.tsx`, `src/useMatches.tsx`, `src/useStore.tsx`). Action tree via `parent`; internal `currentRootActionId` descent; `ancestors`; Backspace-on-empty pop.
- Raycast — developers.raycast.com/api-reference/user-interface/navigation, /list, /actions, /misc/changelog. View stack; `useNavigation` push/pop; `Action.Push`; intrinsic Escape-back; per-view search bar.
- VS Code — github.com/microsoft/vscode-extension-samples `quickinput-sample/src/multiStepInput.ts`; code.visualstudio.com/api/references/vscode-api (QuickInputButtons.Back). App-owned step stack; `InputFlowAction.back` sentinel; threaded `Partial<State>`.

**Library architecture (for the combine-vs-pattern verdict):**
- zag.js Combobox — zagjs.com/components/react/combobox (owned keys, focus, no filtering).
- Ark UI Combobox — ark-ui.com/docs/components/combobox (`createListCollection`, ARIA roles).

**UX references (behavior-level):**
- Linear changelog — linear.app/changelog/2019-10-07-contextual-command-menu, /2019-12-18-new-command-menu.
- Superhuman — blog.superhuman.com/how-to-build-a-remarkable-command-palette/ (focus-restore on dismiss).
- Alfred/Raycast comparisons — joshcollinsworth.com/blog/alfred-raycast, raycast.com/raycast-vs-alfred, evantravers.com/articles/2023/02/16/raycast-review-as-an-longtime-alfred-user.

**Our code + prior design:**
- `www/src/session-canvas/launcher/{commandModel.ts, useCommandCenter.ts, CommandCenter.tsx, useLauncherRows.ts}`.
- `~/.mdx/projects/transport-matters-launcher-action-model--consensus.md` (authoritative action model; §5 is the mechanism this report refines).

## Source Quality Assessment

- **High confidence**: the stack-as-the-model finding and the library-combining verdict — corroborated across five independent primary sources (verbatim code idioms from cmdk, kbar, VS Code; official Raycast and Ark/zag docs). The composition recommendation follows directly from our own code, which already uses the Ark collection seam the pattern needs.
- **Medium confidence**: the exact Backspace-to-go-back mechanic in Linear (inferred from its cmdk lineage, not vendor-documented) and the Alfred/Raycast back behavior (secondary/observational writeups). These are UX corroboration, not load-bearing for the recommendation.
- **Inference flagged**: Raycast per-view state *retention on pop* is the documented consequence of view-component isolation plus the leakage-bug fix, not a single explicit sentence.
- kbar's docs site is JS-rendered (fetch returned only the title); all kbar quotes are from `main` source, which is authoritative.

## Open Questions

1. **Multi-frame descend for search-then-descend.** When a flat-search hit should land deep in a nested scope, the row needs a `targetStack` path. Not needed today (root flat-search fires leaves), but worth a one-line type affordance when the first searchable nested scope ships.
2. **Breadcrumbs.** None of cmdk/kbar/Raycast ship a first-class breadcrumb; the scope tag / placeholder doubles as the context label. Our `scopeTag` already does this. Decide whether multi-level nesting wants a true breadcrumb derived from the stack (`stack.map(f => f.scope)`).
3. **Per-frame vs global query at deeper levels.** Confirm the desired UX once a real two-level scope exists: cmdk resets query on push; restoring the parent query on pop (per-frame) is the Raycast behavior and the stronger default.
4. **Escape semantics.** Today Escape closes the whole palette (window-capture). cmdk/Raycast use Escape to pop one level. Decide whether Escape should pop-one (matching the references) or remain full-dismiss (our current grammar, with ←/Backspace as the per-level back). Recommend keeping full-dismiss to avoid retraining users; ←/Backspace covers per-level back.

## Actionable Takeaways

1. **Refine consensus §5, keep §1–§4/§6–§11.** Bring the `NavFrame[]` recommendation back to the design agents as a replacement for the `descentStack` ref + `origin` threading. It is smaller, removes a parallel structure, and the action model is untouched.
2. **Do not add cmdk or kbar as dependencies.** Adopt the page-stack pattern over the existing Ark Combobox.
3. **Sequence as Slice A (consensus declarative refactor) → Slice B′ (frame stack).** Slice B′ deletes more than it adds relative to the consensus draft.
4. **Test restore-origin and reset-on-close explicitly**, plus a forward-looking multi-level push/pop so the architecture is proven for deeper nesting before the second scope level ships.
