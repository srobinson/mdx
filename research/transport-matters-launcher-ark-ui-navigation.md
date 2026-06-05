---
title: Ark UI / zag.js Nested Command-Palette Navigation — Idiomatic Architecture for the TM Launcher
type: research
tags: [transport-matters, launcher, ark-ui, zag, navigation]
summary: Ark/zag has no hierarchical Combobox collection and no built-in nested command palette; the Ark-idiomatic answer (and the official Command Menu) is a single flat Combobox + an in-house scope/page stack — exactly TM's current design and the consensus action model. Stay on Combobox.
status: active
confidence: high
created: 2026-06-19
updated: 2026-06-19
---

# Ark UI / zag.js Nested Command-Palette Navigation

**Brief:** Find the Ark-idiomatic way to do nested scope/page navigation (descend → back → restore-selection, full keyboard) for the ⌘K launcher. TM is committed to Ark UI. Grounded in `www/src/session-canvas/launcher/{CommandCenter.tsx, useCommandCenter.ts, useLauncherRows.ts, commandModel.ts}` and the consensus action model (`~/.mdx/projects/transport-matters-launcher-action-model--consensus.md`). Installed: `@ark-ui/react@5.37.2` (current as of June 2026), so every API note below maps to TM's actual surface.

## Executive Summary

Ark UI / zag.js provides **no hierarchical Combobox collection and no built-in nested command-palette primitive.** The Combobox `Collection` is flat; `ItemGroup` is presentational grouping only. The **official Ark "Command Menu" example is a single flat `Combobox` inside a `Dialog`, filtered externally with `matchSorter`, with no scopes and no back navigation** — confirming that "nested scope navigation" is, by design, the application's concern to layer on top, not a framework feature. TM's current launcher (scope as React state, collection rebuilt per scope, one mounted Combobox) and the consensus action model (descend = swap collection + push a descent frame; ←/Backspace = pop + restore highlight via controlled `highlightedValue`) are **already the Ark-idiomatic architecture.** The clear recommendation is **stay on a single `Combobox` + an in-house page/scope stack.** Tree View and Menu both model hierarchy natively but are the wrong interaction model for a search-first palette and would mean fighting Ark's focus model. Nothing in the recommended path requires fighting or replacing Ark.

---

## Detailed Findings

### Q1. Primitive inventory for nested command navigation

| Primitive | Hierarchy? | Searchable (text input)? | Keyboard model | Fit for descend/back/restore palette |
|---|---|---|---|---|
| **Combobox** (current) | No — flat `createListCollection` | Yes — input filters the flat collection | Full: ↑↓ highlight, Enter select, Esc, typeahead-via-input, controlled `highlightedValue` | **Best.** Searchable list + descend/back/restore are layered on by you (scope state + collection swap). Matches official Command Menu. |
| **Menu** | Yes — native nested submenus (`Menu.TriggerItem` + nested `Menu.Root`) | No native filter; character typeahead only | ArrowRight opens submenu / ArrowLeft closes; typeahead; roving focus | Weak. Submenus are **spatial flyouts**, not in-place page replacement, and no per-level search box. |
| **Tree View** | Yes — `createTreeCollection` (`rootNode` + `children`) | No integrated input; "filtering" example bolts an **external** input that rebuilds the collection | Roving-tabindex: ArrowRight expand/descend, ArrowLeft collapse/ascend, ↑↓ move, Enter/Space select, typeahead; controlled `expandedValue`/`focusedValue`/`selectedValue`; `loadChildren` async | Weak for a palette. Accordion-expand-in-place (not replace-view stack); no input-as-query model; you own focus juggling between input and tree. |
| **Listbox** | No — flat `createListCollection` | Yes — `Listbox.Input` + `useListCollection().filter` | ↑↓ highlight, typeahead, multi-select, grid/horizontal | Redundant. A flat selection list with search — offers nothing Combobox doesn't for this case. |
| **Steps** | Linear only | No | next/prev over an ordered set | Wrong shape — fixed linear wizard, not searchable arbitrary-scope browse. |
| **Tabs** | Flat panel switch | No | Left/Right between tabs; `composite` Combobox can compose with Tabs | Could render top-level scopes as tabs, but not searchable nesting. |
| **Collection** (`@ark-ui/react/collection`) | n/a (data utility, not UI) | n/a | n/a | `createListCollection`/`useListCollection` (flat, with `filter`/`limit`/mutate helpers). `createTreeCollection` is its hierarchical sibling (powers Tree View). |

**Source:** Ark UI MCP `list_components`, `list_examples`, `get_component_props`, `get_example` for combobox / tree-view / menu / listbox / steps (all framework `react`).

### Q2. Is the Combobox Collection hierarchical? Can a scope stack layer over it?

**The collection is flat.** `Combobox.Root`'s `collection` prop is typed `ListCollection<T>`; `createListCollection({ items, itemToValue, itemToString, isItemDisabled })` takes a flat `T[]`. There is no nested-item or child concept. `Combobox.ItemGroup` / `ItemGroupLabel` are **render-time visual grouping only** — they do not create a data hierarchy or navigation level. The zag.js combobox docs corroborate: "a combobox is an input with a popup that lets you select a value from a collection," with flat `items` and no nested-item support beyond `ItemGroup`.

**Yes — a page/scope stack layers cleanly over one Combobox while keeping filtering, keyboard, typeahead, and focus intact.** This is precisely what TM does today and what the consensus model formalizes: keep a single `Combobox` mounted; on descend, **swap the flat collection** for the sub-scope's rows (memoized `createListCollection`, or imperative `api.setCollection`) and reset the query; Ark's keyboard/typeahead/highlight/focus operate on whatever flat collection is current and are blind to scopes (correctly — scope nav is dispatched from your `onValueChange`/`onInputKeyDown`, not Ark). Relevant Root props for this: controlled `highlightedValue` + `onHighlightChange` (restore-selection), `inputBehavior="autohighlight"`, `selectionBehavior="clear"` (TM uses this), `closeOnSelect={false}` (so descend doesn't close), `composite` (default true, keeps composite keyboard coordination). `@ark-ui/react/collection` also offers `useListCollection({ filter, limit })` if you want Ark to own filtering/virtual-limit instead of TM's manual `filterRows` (see Q7).

### Q3. Menu nested submenus vs Combobox for sub-scopes — can they compose?

**Menu** gives genuinely native nested submenus: a nested `Menu.Root` behind a `Menu.TriggerItem` opens a sub-menu, with ArrowRight-to-open / ArrowLeft-to-close and typeahead built in (verified in the official `menu/nested` example). **But Menu is not a filterable palette** — there is no text input; you only get character typeahead, and each submenu is a **separately positioned flyout** to the side, not an in-place replacement of the list under a persistent search box.

The only official composition is **"Menu with Combobox"** (ark-ui.com/examples/menu-with-combobox): a Combobox rendered inside Menu content to make a *single* dropdown searchable. That adds search to **one** level; it does not yield a per-level-searchable multi-level palette. Net: Menu is the wrong body for a search-first command palette. Combobox + Menu compose only as "searchable single menu," which is not the launcher's shape.

### Q4. Tree View (zag tree) for hierarchical scope navigation

Tree View is the only primitive with first-class hierarchy and a descend/ascend keyboard model (ArrowRight/Left to expand/collapse, controlled `expandedValue`/`focusedValue`, `onFocusChange` as a restore-selection analog, `loadChildren` for async children — which would map neatly to TM's lazy specialist fetch). **However:**

- **No integrated search input.** The official `tree-view/filtering` example wires an *external* `<input>` and calls `setCollection` to rebuild a filtered tree (and that example's naive filter only matches top-level nodes — there is even an open Ark issue, #2667, about combobox/tree filtering keyboard nav). You own the input and the input↔tree focus coordination.
- **Expansion is in-place accordion, not a replace-view page stack.** A command palette's "descend into Settings" replaces the visible list; a tree expands a branch beneath its parent. Different UX.
- **Roving-tabindex widget, not input-focused.** Adopting it abandons the Combobox input-as-query model the launcher is built around.

Fit for the launcher: **weak.** Tree View suits a persistent, expandable hierarchy (a file tree), not a search-first, one-level-at-a-time palette.

### Q5. Keeping Ark owning internal keys while adding scope navigation

The integration pattern that avoids double-handling and focus-trap conflicts — and which TM already implements — is:

1. **One Combobox stays mounted across scopes.** Let Ark own ↑↓ highlight, Enter selection, typeahead, highlight, and input focus *within the current flat collection*.
2. **Claim only the scope-nav keys** in `Combobox.Input`'s `onKeyDown`, guarded by caret position so you never steal a key Ark needs: `→` at caret-end descends (only when the active row's `advance` lifecycle says so); `←` at caret-0 and `Backspace` on empty query pop the scope. `preventDefault`/`stopPropagation` *only* on the keys you claim; everything else falls through to Ark untouched. (This is exactly `useCommandCenter.onInputKeyDown` today, and the consensus model keeps it.)
3. **Own Escape with a window-capture listener.** Ark's Combobox dismisses Escape via a **document-level** capture listener that only closes its own listbox / clears input. A **window-level** capture listener runs earlier in the capture path (window precedes document), so TM closes the whole palette and `stopPropagation` before Ark consumes the key. This is the established, correct seam for "Escape always closes the whole palette" and is the one place you deliberately pre-empt Ark.
4. **Scope change = swap collection + reset query + set highlight, in one batch.** Restore-selection on pop is a controlled `highlightedValue` write batched with the `setScope`, landing on the descent-origin row (the consensus doc's `descentStack`/`DescentFrame` "descent-origin restore"). TM's auto-highlight effect keeps a still-valid highlight rather than resetting to first — that ordering is the load-bearing contract.
5. **Do not mount a second focus-trapping widget** (Menu/Tree) inside the open palette — that is where focus-trap and double-keyboard conflicts arise. Keep `closeOnSelect={false}` so descend doesn't dismiss; consider `persistFocus` on `Combobox.Item` (used in the official Command Menu) to stop pointer-out from clearing the keyboard highlight.

### Q6. Official / community nested command-palette implementations on Ark

- **Official Ark "Command Menu"** (`website/src/components/command-menu.tsx`): `Dialog.Root` → `Combobox.Root open disableLayer inputBehavior="autohighlight" selectionBehavior="clear" loopFocus={false}`, flat `createListCollection`, filtering done **outside Ark** via `matchSorter` (rebuilding the collection; search collapses groups into one "Search Results:" group), `Combobox.Item ... persistFocus`, and selection does `router.push(value)`. **No scopes, no descend, no back.** This is the canonical Ark command palette and it is single-level by design. TM's launcher is a superset of it.
- **Official "Menu with Combobox"**: searchable single menu (see Q3).
- **Relevant per-component examples** (Ark MCP): combobox `grouping`, `async-search`, `auto-highlight`, `rehydrate-value`, `custom-object`, `limit-results`, `virtualized`; tree-view `filtering`, `controlled-expanded`, `controlled-selected`, `async-loading`, `lazy-mount`; menu `nested`, `menu-in-dialog`; listbox `filtering`, `group`.
- **No official multi-level command palette, and no notable community Ark/zag nested-palette implementation surfaced.** The widely-documented "nested pages" pattern is **cmdk's** (a `pages` stack array; push on select, pop on Backspace/Escape when query empty) — which is a *userland* state pattern, not a framework primitive, and is exactly the in-house stack TM/the consensus model already use. Ark has no equivalent built-in; you bring your own stack.

### Q7. Recommendation — the Ark-idiomatic architecture for TM's nested launcher

**Stay on a single `Combobox` + an in-house page/scope stack.** This is the Ark-idiomatic answer, it mirrors the official Command Menu, and it is what the consensus action model already specifies. Concretely:

- **Keep** `CommandCenter.tsx`'s one `Combobox.Root` with `collection={center.collection}`, `closeOnSelect={false}`, controlled `highlightedValue`/`inputValue`, window-capture Escape, and `onInputKeyDown` scope grammar.
- **Descend** = push a `DescentFrame{ parent, originValue }`, `setScope(target)`, clear query → `useLauncherRows` rebuilds the flat collection for the new scope (`createListCollection`). Ark re-runs filtering/keyboard/highlight on the new flat list automatically.
- **Back** (`←`/`Backspace`) = pop the frame, `setScope(parent)`, and `setHighlighted(originValue)` in the same batch → controlled `highlightedValue` restores the originating row (descent-origin restore, §5 of the consensus doc).
- **Composes with the declarative model** with zero new Ark surface: `descend` is the `SCOPE_INTERACTION` lifecycle; the dispatcher (`applyGesture`) switches only over `Lifecycle`, never over Ark internals. The page-stack lives entirely in `useCommandCenter`; `CommandCenter`/`useLauncherRows` stay thin Ark compositions.

**Reject** the alternatives, for concrete reasons:
- **Tree View** — abandons the input-as-query model, accordion-expands instead of replacing the view, and forces manual input↔tree focus management (Q4).
- **Menu** — not searchable per level; nesting is spatial flyouts, not in-place pages (Q3).
- **Hierarchical Combobox collection** — does not exist and is not on the roadmap; `ItemGroup` is presentational only (Q2).

**Optional, non-blocking refinement:** migrate TM's manual `filterRows` + `createListCollection` to `useListCollection({ filter, limit })` from `@ark-ui/react/collection` if you later want Ark to own filtering/virtualization. TM's custom title+subtitle substring filter and domain grouping currently argue for keeping the manual path; treat this as a minor consolidation, not a requirement.

**Nothing in this path requires fighting or replacing Ark.** The only thing Ark cannot provide natively — the nesting itself — is correctly the application's concern, and the existing seam (collection swap + claimed nav keys + window-capture Escape + controlled highlight) is the idiomatic way to own it.

---

## Sources Consulted

**Ark UI MCP server (primary, `@ark-ui/react`, framework=react):**
- `list_components`, `list_examples` (combobox, tree-view, menu, listbox, collection, steps)
- `get_component_props`: combobox (confirmed `collection: ListCollection<T>` flat; `highlightedValue`, `inputBehavior`, `selectionBehavior`, `composite`, `closeOnSelect`), tree-view (`createTreeCollection`, `expandedValue`/`focusedValue`/`selectedValue`, `loadChildren`, `typeahead`)
- `get_example`: tree-view `basic` + `filtering`, menu `nested`, listbox `filtering`, combobox `grouping`/registry

**Official Ark source (GitHub `chakra-ui/ark`):**
- `website/src/components/command-menu.tsx` — the official ⌘K Command Menu (Dialog + flat Combobox + matchSorter; no nesting)

**Docs / web:**
- Combobox — Zag.js: https://zagjs.com/components/react/combobox (flat collection; `setCollection`; `useListCollection` with `limit`)
- Combobox | Ark UI: https://ark-ui.com/docs/components/combobox
- Command Menu | Ark UI: https://ark-ui.com/examples/command-menu
- Menu with Combobox | Ark UI: https://ark-ui.com/examples/menu-with-combobox
- Ark issue #2667 — combobox keyboard nav bug in filtering example: https://github.com/chakra-ui/ark/issues/2667
- cmdk nested-pages prior art (userland `pages` stack pattern): https://github.com/pacocoursey/cmdk, https://uxpatterns.dev/patterns/advanced/command-palette

**TM code grounded against:** `CommandCenter.tsx`, `useCommandCenter.ts`, `useLauncherRows.ts`, `commandModel.ts`; consensus action model `~/.mdx/projects/transport-matters-launcher-action-model--consensus.md`.

## Source Quality Assessment

**High confidence.** Findings triangulate across three independent primary sources: the Ark UI MCP server (live API for the installed 5.37.2), the official Ark Command Menu source on GitHub, and the zag.js docs — all agree the Combobox collection is flat and there is no built-in nested-palette primitive. The TM code and consensus design were read directly. The one gap: the ark-ui.com/examples pages are JS-rendered, so the `menu-with-combobox` *source* was inferred from its description plus the `menu/nested` and `command-menu` sources rather than read line-for-line; the architectural conclusion does not depend on that detail.

## Open Questions

- **`useListCollection` filter parity:** does its built-in `filter` cover TM's title+subtitle substring + grouping semantics, or would adopting it regress the current filter? (Resolvable by reading `@ark-ui/react/collection` source; not blocking.)
- **Multi-level depth:** TM today is effectively root↔scope (one level). The `descentStack` generalizes to N levels; if deeper nesting is ever wanted, confirm the controlled-highlight restore still holds when several collection swaps stack (expected to, since each pop is one batched scope+highlight write).
- **Ark issue #2667:** verify the combobox filtering keyboard-nav bug does not affect TM's collection-swap path (TM rebuilds collections rather than mutating in place, which likely sidesteps it).

## Actionable Takeaways

1. **Proceed with the consensus action model as written** — it is the Ark-idiomatic nested-palette architecture; this research found no better Ark-native path and no reason to deviate.
2. **Do not introduce Tree View or Menu** for scope nesting; both lose the search-first input model and add focus conflicts.
3. **Keep the four seams** that make Combobox own keyboard while you own nav: single mounted Combobox, collection swap per scope, claimed nav keys with caret guards, window-capture Escape, controlled `highlightedValue` for restore.
4. **Consider `persistFocus` on `Combobox.Item`** (as the official Command Menu does) to keep keyboard highlight stable against pointer movement.
5. **Optionally evaluate `useListCollection`** as a later consolidation of `filterRows` + `createListCollection`; not required for the nested-nav work.
