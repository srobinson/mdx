---
title: Launcher NavFrame Navigation-Stack Model — Design Proposal (claude)
type: projects
tags: [frontend, transport-matters, www, launcher, command-center, navigation, nav-frame, ark-ui]
summary: One in-house NavFrame[] stack over the existing Ark Combobox; top frame is live scope/query/highlight; descend=push, back=pop, restore-origin intrinsic; collapses flat `scope` + consensus §5 `descentStack` into one source of truth; pure stack ops in commandModel, controlled-highlight inversion in useLauncherRows.
status: active
source: frontend-engineer
confidence: high
created: 2026-06-19
updated: 2026-06-19
---

# Launcher NavFrame Navigation-Stack Model

**Scope:** `www/src/session-canvas/launcher/{commandModel.ts, useCommandCenter.ts, useLauncherRows.ts, CommandCenter.tsx}`. Cite file + symbol; no version-suffixed names. This proposal **composes with** the consensus action model (`interactionFor` / `Lifecycle` / `fire` / effect sink) and **replaces only its §5 navigation mechanism** (`descentStack` + `origin` threading) with a single `NavFrame[]` stack.

## Core idea

Model nested scopes as one app-owned **navigation stack** layered over the single Ark `Combobox` (the cmdk page-stack *pattern*, not the library). The **top frame is the live scope/query/highlight**; descend pushes a frame, back pops one, and the revealed frame still carries the query + highlight it had when it was last on top — so **back-navigation and ←-restore-origin are intrinsic stack properties**, not a parallel structure. The flat `scope` state (`useCommandCenter`) and the planned `descentStack` ref (consensus §5) collapse into this one source of truth. The stack transitions are **pure functions in `commandModel`** (the file's existing charter); `useCommandCenter` only wires them to `setStack`.

---

## 1. The `NavFrame` shape and the stack as the single nav source

A frame is a page identity plus the two pieces of per-page state that must restore on return. Pure, in `commandModel.ts` next to `LauncherScope`:

```ts
// commandModel.ts — pure, deterministic, unit-testable (matches the file charter)

/** One level of the launcher navigation stack. The TOP frame is the live state. */
export interface NavFrame {
  scope: LauncherScope;        // page identity (the existing flat scope union)
  query: string;               // restored when this frame is revealed (per-frame search)
  highlightedValue?: string;   // row to re-highlight when revealed (= restore-origin)
}

/** A fresh base frame. A factory (not a shared const) so every reset is clean. */
export function rootFrame(): NavFrame {
  return { scope: "root", query: "", highlightedValue: undefined };
}

export function topFrame(stack: NavFrame[]): NavFrame {
  return stack[stack.length - 1];
}

/** Push a child scope: per-frame query resets (cmdk "reset search on navigate"). */
export function pushFrame(stack: NavFrame[], scope: LauncherScope): NavFrame[] {
  return [...stack, { scope, query: "", highlightedValue: undefined }];
}

/** Pop one level; never empties the stack (the base root frame is the floor). */
export function popFrame(stack: NavFrame[]): NavFrame[] {
  return stack.length > 1 ? stack.slice(0, -1) : stack;
}

/** Immutable patch of the top frame (query / highlight live writes). */
export function patchTopFrame(stack: NavFrame[], patch: Partial<NavFrame>): NavFrame[] {
  return [...stack.slice(0, -1), { ...topFrame(stack), ...patch }];
}
```

In `useCommandCenter` the stack **replaces both `scope` and `query` useState**; the live values are read off the top frame:

```ts
const [stack, setStack] = useState<NavFrame[]>(() => [rootFrame()]);
const frame = topFrame(stack);          // the live scope / query / highlight
// frame.scope, frame.query, frame.highlightedValue are the single source of truth
```

There is exactly **one** structure answering "where am I and how do I get back." No `scope`, no `query`, no `descentStack`, no `origin` threading.

---

## 2. Nav ops: descend / back / reset

All three are `setStack` wired to the pure helpers — the elegance is that `popFrame` already has the `(prev) => next` shape `setStack` wants:

```ts
const descend = useCallback((scope: LauncherScope) => setStack((s) => pushFrame(s, scope)), []);
const back = useCallback(() => setStack(popFrame), []);   // pops one level; no-op at root
```

- **root** is the base frame; `back` is bounded by `popFrame` (never pops past it).
- **caret-guarded ←/Backspace map to `back`** (§3). `back` pops *one* level (not hardcoded `setScope("root")`), so it scales to N levels for free.
- **restore-origin is intrinsic.** When the user descends, the parent frame is *already* the top frame and *already* holds `highlightedValue = "domain:settings"` (the row the combobox had highlighted — see `buildDomainRows`, value `domain:${scope}`). `pushFrame` lays a new frame on top; the parent frame underneath is never mutated, so it freezes with that highlight + its query. `back` reveals it intact. **No capture step, no `origin` parameter, no `descentStack`.** This is the whole point: the highlight that consensus §5 had to thread and re-apply is just the parent frame, sitting where we left it.

Per-frame query/highlight live writes patch the top frame. `setHighlighted` must keep the `SetStateAction` contract (the auto-highlight effect calls it with a functional updater):

```ts
const setQuery = useCallback((q: string) => setStack((s) => patchTopFrame(s, { query: q })), []);

const setHighlighted = useCallback(
  (next: SetStateAction<string | undefined>) =>
    setStack((s) => {
      const resolved = typeof next === "function" ? next(topFrame(s).highlightedValue) : next;
      return patchTopFrame(s, { highlightedValue: resolved });
    }),
  [],
);
```

Reset paths re-seed the stack instead of clearing `scope`/`query`:

```ts
const close = useCallback(() => {
  setOpen(false);
  setStack([rootFrame()]);
  restoreFocusRef.current?.focus?.();
  restoreFocusRef.current = null;
}, []);

// toggleRoot (open branch) and the open path: setStack([rootFrame()])
// openScope(target): seed a 2-frame stack so ← still returns to root, and pre-highlight
//   the matching domain so backing out lands on it (faithful to descend-from-root).
const openScope = useCallback((target: LauncherScope) => {
  rememberFocus();
  setHasOpened(true);
  setStack(pushFrame([{ ...rootFrame(), highlightedValue: `domain:${target}` }], target));
  setOpen(true);
}, [rememberFocus]);
```

`openScope` seeding `[root, target]` reproduces today's behavior exactly: it opens *inside* a scope, and ← pops to root because `stack.length > 1`. (Today's `setScope(target)` + `scope !== "root"` ← guard is the same observable behavior.)

---

## 3. Ark Combobox integration (one listbox owner, claim only nav keys)

`CommandCenter.tsx` stays the thin Ark composition — **no JSX change**, because the hook still returns `scope` / `query` / `highlighted` (now read off the top frame):

- `highlightedValue={center.highlighted ?? null}` ← `frame.highlightedValue`; `onHighlightChange → setHighlighted` writes the top frame (so arrowing in root keeps root's frame current, and it freezes on descend).
- `inputValue={center.query}` ← `frame.query`; `onInputValueChange → setQuery` patches the top frame.
- **collection swapped per scope** already happens: `useLauncherRows` derives `visibleRows`/`collection` from `frame.scope` + `frame.query` via `buildScopeRows` → `createListCollection`. Ark re-runs filtering/keyboard/highlight on the new flat collection, blind to scopes (correct — nav is dispatched from `onInputKeyDown`).
- **caret guards** in `useCommandCenter.onInputKeyDown` claim only the nav keys; everything else (↑↓ / Enter / Home / End / typeahead) falls through to Ark untouched:

```ts
const onInputKeyDown = useCallback(
  (event: KeyboardEvent<HTMLInputElement>) => {
    const caret = event.currentTarget.selectionStart ?? 0;
    if (event.key === "ArrowRight" && caret >= frame.query.length) {
      const row = frame.highlightedValue ? rowByValue.get(frame.highlightedValue) : undefined;
      const advance = row?.action ? interactionFor(row.action).advance : "none";
      if (row?.action && advance !== "none") {
        event.preventDefault();
        applyGesture(row.action, advance);   // SCOPE_INTERACTION.advance === "descend"
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

- **window-capture Escape stays** (closes the whole palette before Ark's document-level handler), and **`closeOnSelect={false}` stays** (descend must not dismiss). Unchanged from today. The ←/Backspace grammar covers per-level back; Escape remains full-dismiss (no retraining).
- No double-handling: `preventDefault` fires **only** on the claimed keys (→ at caret-end, ← at caret-0, Backspace on empty). The `stack.length > 1` guard replaces the `scope !== "root"` guard — the correct invariant ("is there a frame to pop").

---

## 4. Composition with the action-model consensus (verbatim, except descend→push / back→pop)

`Lifecycle`, `Interaction`, `interactionFor`, `SCOPE_INTERACTION`, `COMMAND_INTERACTIONS`, `EFFECT_INTERACTIONS`, `fire`, and the effect sink are **untouched**. Only the `descend` case body and the back grammar change — and they get *smaller*:

```ts
const applyGesture = useCallback(
  (action: RowAction, lifecycle: Lifecycle) => {   // ← `origin` param DELETED
    switch (lifecycle) {
      case "descend":
        if (action.kind === "enter") descend(action.scope);   // was: setScope + setQuery("")
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

const selectValue = useCallback(
  (value: string | undefined) => {
    const row = value ? rowByValue.get(value) : undefined;
    if (row?.action) applyGesture(row.action, interactionFor(row.action).enter);  // no origin
  },
  [rowByValue, applyGesture],
);
```

- `enter` action still descends on both ↵ and → (`SCOPE_INTERACTION = { enter: "descend", advance: "descend" }`, unchanged).
- `commit-close` / `run-close` → `close()` clears the stack to `[rootFrame()]`.
- `run-stay` is unaffected: it neither pushes nor pops, so `cycle-theme`'s `→`-stepper and `retry-agents` keep working — they re-fire on the same top frame.
- The dispatcher still **switches only over `Lifecycle`** and reads `scope`/`stack` only inside `descend`/`back` — never a command kind, so the no-kind-branching property holds.

**Net:** consensus §1–§4, §6–§11 preserved verbatim; §5's `DescentFrame` / `descentStack` ref + the `origin` parameter threaded through `applyGesture` / `selectValue` / `onInputKeyDown` are **deleted**. Slice B′ removes more than it adds.

---

## 5. Scope / DOMAINS data model — flat registry, the *stack* carries the tree

**Keep `LauncherScope` a flat union and `DOMAINS` a flat registry.** The scope union is a registry of *page identities* (cmdk's `pages: string[]`). The parent/child relationship is supplied **at runtime by the stack** — parent of current = `stack[stack.length - 2].scope` — so there is no static tree and no hardcoded "parent = root."

- **A frame resolves its rows** exactly as today: `buildScopeRows(frame.scope, inputs, frame.query)` → `filterRows` → `createListCollection`. Adding a deeper scope = add one `LauncherScope` member + one `buildScopeRows` case + (if it is enterable from a parent) a domain/sub-domain row whose action is `{ kind: "enter", scope }`. **Zero nav plumbing** — deeper nesting works because `descend` pushes another frame and `back` pops one.
- **DOMAINS stays flat**, keyed by `scope`. It does **not** become a nested tree. A static `parent`-tree (kbar style) is required *only* for "type-to-search-across-all-scopes that descends into a deep result," where a flat-search hit must reconstruct its ancestor stack. Today root flat-search (`buildFlatSearchRows`) fires **leaf** commands (spawn / cycle-theme) that never descend, so this is **YAGNI**. When the first searchable nested scope ships, add an optional `targetStack?: LauncherScope[]` to the `enter` action and let `descend` push multiple frames at once — a one-line type affordance, not a tree refactor.

This is the deliberate non-over-engineering line: generalizable to N levels via the stack, with the static tree deferred until a feature actually needs ancestor reconstruction.

---

## 6. "Type to search" — per-frame (scoped) query

Query is **per-frame**, matching today's per-scope filtering:

- Each `NavFrame` owns its `query`. `descend` pushes `query: ""` (cmdk "reset search on navigate"); `back` restores the parent's `query` **intrinsically** (it is in the revealed frame) — the Raycast per-view search-bar behavior.
- Root's two-mode behavior is just the base frame's `buildScopeRows("root", …)` switch, **unchanged**: empty query → `buildDomainRows` (the five domains); any query → `buildFlatSearchRows` (flat search across every agent + command). The frame model does not touch this; root is simply the bottom frame, and flat-search hits are fire-and-close leaves that never push/pop.
- It lives in the frame (`frame.query`), bound to Ark's `inputValue`; there is no separate global query state.

---

## 7. Migration, mapping, trade-offs

### Slice sequence (composes with the consensus plan)

- **Slice A (consensus, unchanged):** behavior-preserving declarative refactor onto `Lifecycle` / `interactionFor`. Descend still `setScope`; ← still pops to `root`. Ships first.
- **Slice B′ (this design, replacing consensus §5's mechanism):** introduce `NavFrame[]` as the single nav source.
  1. `commandModel.ts`: add `NavFrame` + pure `rootFrame` / `topFrame` / `pushFrame` / `popFrame` / `patchTopFrame`. `buildScopeRows` / `filterRows` / `groupRows` / `firstSelectableValue` / `interactionFor` untouched; `LauncherScope` stays flat.
  2. `useCommandCenter.ts`: `stack` replaces `scope` + `query`; derive `frame`; `setQuery` / `setHighlighted` patch the top frame; `descend` / `back`; `close` / `toggleRoot` / `openScope` re-seed the stack. **Delete** the planned `descentStack` ref + the `origin` parameter.
  3. `useLauncherRows.ts`: **controlled-highlight inversion** — drop its internal `const [highlighted, setHighlighted] = useState(...)`; receive `highlighted` + `setHighlighted` as args (frame-backed, from `useCommandCenter`). Keep the auto-highlight effect verbatim, now writing through the passed setter:

     ```ts
     // useLauncherRows args gain: highlighted: string | undefined;
     //                            setHighlighted: Dispatch<SetStateAction<string | undefined>>;
     useEffect(() => {
       setHighlighted((current) =>
         current && visibleRows.some((row) => row.value === current && !row.disabled)
           ? current
           : firstSelectableValue(visibleRows),
       );
     }, [visibleRows]);   // unchanged body; now normalizes the TOP FRAME's highlight
     ```
     `useCommandCenter` passes `scope: frame.scope, query: frame.query, highlighted: frame.highlightedValue, setHighlighted` in and consumes `{ collection, grouped, rowByValue, fleetStatus }` out.
  4. `CommandCenter.tsx`: **no change** — `center.scope` / `center.query` / `center.highlighted` now read off the top frame; all Ark bindings, the window-capture Escape, `closeOnSelect={false}`, and the scroll-into-view effect are identical.

### Current → NavFrame mapping (behavior preserved)

| Today (`main` + consensus §5 draft) | NavFrame model |
|---|---|
| `scope` useState (`useCommandCenter`) | `topFrame(stack).scope` |
| `query` useState (`useCommandCenter`) | `topFrame(stack).query` |
| `highlighted` useState (owned by `useLauncherRows`) | `topFrame(stack).highlightedValue` (owned by the stack) |
| `descend`: `setScope(action.scope); setQuery("")` | `descend(scope)` = `setStack(pushFrame)` |
| `←`/`⌫`: `setScope("root")` (hardcoded pop-to-root) | `back()` = `setStack(popFrame)` (pop one level) |
| ← guard `scope !== "root"` | `stack.length > 1` |
| consensus §5 `descentStack` ref + `DescentFrame` | **gone** — parent frame *is* the saved highlight |
| consensus §5 `origin` threaded through dispatch | **gone** — no capture needed at descend |
| restore-origin = batched `setHighlighted(origin)` on pop | intrinsic: revealed frame already holds the highlight |
| `close` resets `scope` + `query` (+ clear `descentStack`) | `close` re-seeds `stack` to `[rootFrame()]` |
| auto-highlight effect (`useLauncherRows`) | same effect, normalizes the top frame |

### Tests (Slice B′)

- **Pure (`commandModel.test.ts`):** `pushFrame` resets query + clears highlight; `popFrame` is a no-op at the base; `patchTopFrame` only touches the top; `popFrame` preserves the revealed frame's `query` + `highlightedValue` (restore-origin at the data level).
- **Hook/keyboard (new `useCommandCenter` test, the grammar is currently only covered indirectly):** enter Settings via ↵/→ then ← → back at root with `domain:settings` re-highlighted (not the first row); descend resets query, back restores the parent query; `close` / `openScope` re-seed the stack; a forward-looking two-level `push → push → pop → pop` to prove the architecture before a second nesting level ships.

### Trade-offs

- **Top-frame-is-live vs snapshot/restore.** Top-frame-is-live spreads the stack array on each keystroke (negligible for a handful of frames) but keeps **one** source of truth. The snapshot/restore alternative (separate live `query`/`highlighted`; frames store `savedQuery`/`savedHighlight`; snapshot on descend, restore on pop) keeps per-keystroke writes off the stack but **reintroduces the live-vs-saved duality and snapshot-timing edge cases** — exactly the bolt-on subtlety we are retiring. Choose top-frame-is-live.
- **Controlled-highlight inversion of `useLauncherRows`.** Moving `highlighted` out of `useLauncherRows` into the frame is minor churn (its effect now writes through a prop), and it is the move that makes restore-origin free. The hook becomes fully controlled — cleaner, with no second highlight owner.

### Why this resists the prior bolt-on / hardcoding smell

- **One structure, one concept.** `scope` + `query` + the planned `descentStack` (three shapes modeling one navigation) collapse to a single `NavFrame[]`. The named anti-pattern (a descent structure *parallel* to the scope state) cannot recur — there is nothing to run parallel to.
- **No hardcoded pop-to-root.** `back` pops one frame and scales to arbitrary depth; the one-level-deep assumption (`setScope("root")`, "every parent is root") is gone.
- **Dispatcher stays kind-blind.** `applyGesture` switches only over `Lifecycle`; `descend`/`back` read `scope`/`stack` only. Re-introducing a `command.kind` read would be an obvious, reviewable smell with the pure stack helpers sitting right next to the model.
- **Pure, testable core.** The stack transitions live in `commandModel` (deterministic, unit-tested) and `useCommandCenter` is a thin `setStack` wiring — the established file-charter split, not new machinery.

---

## Open questions (non-blocking)

1. **Breadcrumbs.** None of cmdk/kbar/Raycast ship one; `scopeTag` doubles as the context label. If multi-level nesting lands, derive a breadcrumb from `stack.map((f) => f.scope)` rather than adding state.
2. **Search-then-descend-deep.** Needs `targetStack?: LauncherScope[]` on the `enter` action so `descend` can push several frames. Defer until the first searchable nested scope exists.
3. **`openScope` pre-highlight.** Seeding the root frame with `highlightedValue: "domain:${target}"` is a small faithful improvement over today (← from an opened scope lands on its domain). Confirm desired; trivially droppable to `[rootFrame(), { scope: target, … }]` if not.
