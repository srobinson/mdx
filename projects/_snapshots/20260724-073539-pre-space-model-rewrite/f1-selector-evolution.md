# Cubicell Selector evolution

Date: 2026-07-18  
Status updated: 2026-07-19 (reconciled to `main` at `f6e728e`, PR #98 merged)  
Image directory: `/Users/alphab/.mdx/projects/f1-selector-evolution`

This sequence develops the selection query capability from one reachable relation verb to subject-aware spatial builders. Every image used the current Cubicell editor as the shell reference and the approved dark, orange, mono caps Selector concept as the visual reference.

## Shipped on main (PR0 through #98)

Ground truth from `gh pr view` and code on `f6e728e`:

| Slice | PR | Head / merge | Scope shipped | Notes vs original mock plan |
| --- | --- | --- | --- | --- |
| PR0 | #94 | `3ebdac3` | Selector panel shell | `Set N` \| CLEAR header; SELECTION \| MODIFY tabs; CUBE/FACE/EDGE inspector dissolved into MODIFY. Code: `src/panels/SelectorPanel.tsx`. |
| PR1 | #95 | `abc9df0` | OUTER PERIMETER verb | First relation verb in SELECTION. Domain compiler remains; UI exposure changed by #98. |
| PR2 | #96 | `baa039a` | Declarative verb registry | Seven verbs in `src/domain/selectionVerbs.ts`: SIMILAR, OUTER PERIMETER, OUTER EDGES, SHELL, INTERIOR, EXPOSED, ALONG AXIS. Registry and compilers still on main. |
| (burial) | #97 | `1dc84de` | Burial-aware cube visibility | Revealed-cube rendering; not Selector UX, but selection visibility depends on it. |
| Live builders | #98 | `f6e728e` | Retained query + live Cube / Face / Edge spatial builders | Supersedes the planned PR3 "read-only locked draft" UX and the PR4/PR5 clause-edit mock path. See below. |

### What #98 actually shipped

Code owners (not the old PR3 mock):

- **Session retention:** `SelectionQueryDraft` (`expression`, `combine`, `against`, `authoredByVerbId`) plus `selectionQueryDraft` / `lastSelectionQueryDraft` on `CubicellEditorSession` (`src/domain/selectionQuery.ts`, `src/state/cubicellState.ts`).
- **Pinned base + live apply:** builders pin `against` and every nonempty refinement dispatches `select-query` with that base (`src/panels/useRetainedSelectionBuilder.ts`). Zero-match previews do not overwrite the last valid selection.
- **Subject builders (SELECTION tab body):**
  - Cube: `CubeSpatialBuilder` — region (selection / rows / slices / all), row axis + every-other, slice orientation, surface filter (all / exposed / interior), SIMILAR on anchors.
  - Face: `FaceSelectionBuilder` — face-id toggles, exposed filter, SIMILAR; subject control to cube/face/edge.
  - Edge: `EdgeSelectionBuilder` — region (selection / entire structure), directions, cube scope (all anchors / active cube), exact Edge ID filter, outer-only, SIMILAR.
- **Shared primitives:** `SpatialBuilderControls`, `SelectionVerbControls`, `SelectionSubjectControl` (visible cube/face/edge pick-mode navigation inside builders), `PanelTabs` styling consolidated.
- **No** SELECT/FROM/WHERE clause readback UI, no APPLY / combine-mode chrome, no LAST QUERY button, no match preview / SHOW ONLY / FOCUS, no generic editable SQL-like clauses. Live spatial controls *are* the editable builder.

Verb UI after #98: builders wire **SIMILAR only** as the anchor verb. The other six verbs remain in the domain registry and tests; they are not rendered as a full seven-button row. Spatial filters cover related intents (exposed / interior surface, outer only, directions, regions) without restoring that row.

## Sequence (historical mock frames)

The images remain provenance for the planned mock path. Status column is current truth on main.

| Slice | Image | Original planned scope | Status 2026-07-19 |
| --- | --- | --- | --- |
| PR1 | [pr1-outer-perimeter-inspector.png](f1-selector-evolution/pr1-outer-perimeter-inspector.png) | Reachable OUTER PERIMETER | **SHIPPED** as #95 (panel shell already PR0; mock still shows Inspector-era framing). |
| PR2 | [pr2-subject-aware-quick-select.png](f1-selector-evolution/pr2-subject-aware-quick-select.png) | Seven named verbs, subject gating | **SHIPPED** as #96 registry; **UI row superseded** by #98 spatial builders (SIMILAR anchors only). |
| PR3 | [pr3-read-only-selector-draft.png](f1-selector-evolution/pr3-read-only-selector-draft.png) | Retained draft, pinned base, locked SELECT/FROM/WHERE readback, combine, APPLY, LAST QUERY | **SUPERSEDED by #98.** Retention and pinned base shipped; read-only clause chrome and APPLY/LAST QUERY UX did not. Live spatial builders replaced that surface. Spec: `f1-selector-pr3-spec.md` (header notes supersession). |
| PR4 | [pr4-results-and-recent-queries.png](f1-selector-evolution/pr4-results-and-recent-queries.png) | Match evidence, full assembly MATCH PREVIEW, SHOW ONLY, FOCUS, recent query list | **Mostly still ROADMAP.** Partial: live match count text in `SpatialResult`. No miniature match preview, SHOW ONLY, FOCUS, or multi-query recents list. One-slot `lastSelectionQueryDraft` restores builder state, not a recents UI. |
| PR5 | [pr5-full-editable-selector.png](f1-selector-evolution/pr5-full-editable-selector.png) | Make verb-authored clauses editable (+ CONDITION, junction multiselect, negate, exemplars, …) | **SUPERSEDED assumption.** Builders are already live and editable. Remaining work is deeper refinement UX (predicate/junction vocabulary, multi-condition authoring, recents), not "unlock a locked draft." |

## Shared product contract

Still true:

1. Quick entry points (verbs where exposed, spatial controls always) author the same `SelectionExpression` the engine evaluates.
2. Subject homogeneity governs reachability; invalid options stay visible and disabled where the UI exposes them.
3. Results use the existing selection aggregate, orange selection chrome, Structure, State timeline, and camera keypad.
4. No blank filter form, raw code, text DSL, or parallel selection mechanism.

Updated by #98:

5. Progressive disclosure is **spatial builder state**, not progressive SELECT/FROM/WHERE clause materialization.
6. Refinement is **live and undoable** against a pinned base; combine chrome is not the primary path (builders commit with `combine: 'replace'`).
7. The full seven-verb button row is no longer the SELECTION tab body; domain `selectionVerbs` remains the named-verb vocabulary for compilers and future re-surface.

## Visual progression (historical mock path)

```text
Inspector verb
    -> compact verb instrument
    -> retained read only query   [planned PR3; superseded]
    -> match evidence and recall  [partial count only]
    -> editable generated query   [superseded: builders already live]
```

Shipped progression on main:

```text
PR0 panel shell
    -> PR1 OUTER PERIMETER
    -> PR2 seven-verb registry
    -> #98 live Cube / Face / Edge spatial builders on retained draft
```

## Gap states

These frames still illustrate the locked one-panel IA from `f1-selector-ia-decision.md`. The persistent header owns Set and Clear. Selection owns building. MODIFY derives cube / face / edge editors from the homogeneous selection subject.

| State | Image | Behavior shown | Status |
| --- | --- | --- | --- |
| Empty selection | [state-empty-selection.png](f1-selector-evolution/state-empty-selection.png) | Opens on Selection with Set 0; Clear disabled; pick on canvas or begin from structure. | **SHIPPED** (empty SELECTION shows a pick hint; no builder until selection exists). |
| Raw manual pick, Properties | [state-manual-pick-properties.png](f1-selector-evolution/state-manual-pick-properties.png) | MODIFY (mock may say PROPERTIES) with subject-derived editor. | **SHIPPED** as MODIFY tab. |
| Raw manual pick, Selection | [state-manual-pick-selection.png](f1-selector-evolution/state-manual-pick-selection.png) | Same Set under Selection with subject-compatible tools. | **SHIPPED** as subject spatial builder (not verb row + empty clauses). |

## Genuine remaining roadmap

Not a re-run of PR3–PR5 mockups. Concrete gaps after #98:

1. **Match evidence beyond count** — assembly match preview, SHOW ONLY, FOCUS (old PR4 mock).
2. **Query recall UX** — multi-slot recent queries / replay list (one last draft exists for restore only).
3. **Named-verb surface** — decide whether to re-expose OUTER PERIMETER, OUTER EDGES, SHELL, INTERIOR, EXPOSED, ALONG AXIS beside or inside builders (compilers already exist).
4. **Deeper predicate authoring** — junction classes, multi-condition AND/OR, negate/tolerance, MATCH EXEMPLARS Any/All, if product still wants that vocabulary beyond spatial filters.
5. **Combine-mode chrome** — add/subtract/intersect against pinned base as first-class UI (engine + draft field support it; builders force replace today).
6. **Pick-mode chrome outside builders** — TAB still works globally; builders add subject control. Parked global pick-mode control remains open per IA note.

Generation method for existing images: built-in ImageGen, one image per historical slice.
