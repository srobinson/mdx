# F1 Selector — Selection IA Decision

Date: 2026-07-18
Status: model LOCKED. Ready to spec PR0.
Related: `f1-selector-evolution.md` (PR + gap-state mockups), `f1-selection-query-scout.md` (engine scout).

## Context

Surfacing the selection-query engine forced a broader question: once a dedicated Selector panel owns *selecting*, the CUBE/FACE/EDGE inspector is the wrong home for selection chrome, and its three subject tabs are the wrong UX entirely. Direction: stop adding selection functionality to CUBE/FACE/EDGE, build it only in the new Selector, and progressively strip the inspector down until it dissolves into the Selector.

## Core principle (DECIDED)

A manual canvas pick and an authored query are the **same domain object**: a `SelectionExpression`. A manual pick is the degenerate expression `SELECT <subject> FROM <these ids>` with no predicates. Marquee and layer selection already route through `select-query` today (per the scout). So there is no "manual mode vs query mode" to reconcile. There is one continuum: an empty query that accretes clauses. Every UX decision below follows from this.

## The panel (DECIDED)

One panel replaces both the Selector concept and the CUBE/FACE/EDGE inspector:

```
┌───────────────────────────────────────┐
│  Set N                       CLEAR      │  ← persistent header
├───────────────────────────────────────┤
│  [ SELECTION ]   [ MODIFY ]             │  ← two tabs
├───────────────────────────────────────┤
│  (tab body)                             │
└───────────────────────────────────────┘
```

### Persistent header: `Set N` | CLEAR

The header carries selection **identity**: the count and CLEAR (deselect). Both are harmless, reversible, and relevant on both tabs, so they are always visible. SIMILAR does **not** belong here (it is selection *creation*, and lives in the SELECTION tab). DELETE does **not** belong here either: it is a destructive scene mutation, and a permanently-visible delete is a footgun, so it lives in MODIFY (see below).

### Tab 1 — SELECTION

Quick verbs (SIMILAR, OUTER PERIMETER, ALONG AXIS, EXPOSED, SHELL, INTERIOR, OUTER EDGES) plus the query builder and results.

**Progressive clauses (the key move):** the SELECT / FROM / WHERE / AND readback only *materializes when the selection carries predicates or projections*. A raw manual or marquee pick shows only the verb row and a count ("8 cubes · refine"). Pressing a verb or adding a condition makes the clauses appear, seeded by the current pick as the FROM. Manual selection is therefore not a special screen; it is the query builder before any clauses exist.

### Tab 2 — MODIFY (replaces CUBE/FACE/EDGE tabs)

One polymorphic "act on the selection" surface. The subject is a **consequence of the selection** (homogeneous: all cubes, all faces, or all edges), never a mode the user picks. MODIFY renders the cube / face / edge editor derived from `selection.subject`, with a subject label ("MODIFY · EDGES"), and carries the PART / SET focus toggle.

MODIFY holds both **properties** (dimensions, style, color, opacity, thickness, visibility) and **operations** (ADD NEIGHBOR, SNAP HOME, DELETE) for now. Operations may relocate later once we have mileage using the tool; keeping them here unblocks the build. The name is MODIFY (not PROPERTIES) precisely because it holds operations, not only properties.

The CUBE / FACE / EDGE tabs are removed. Their editors become the three render branches of this one tab.

## Manual selection behavior (DECIDED — the previously unsolved case)

When the user picks from the canvas:

- Both tabs update to the pick. Do **not** force a tab switch.
- MODIFY shows that subject's editor. SELECTION shows verbs + count, no clause noise.
- Tab auto-selection happens only from the empty state: opening the panel on an empty selection defaults to SELECTION (you came to select); picking from empty lands in MODIFY (you grabbed something to act on it).
- After that, respect the user's current tab so selecting never yanks them around. The tab choice is sticky within a session; a keyboard toggle switches tabs for power users.

## Resolved open questions (DECIDED)

1. **No-selection defaults — no new surface.** The old tabs conflated "properties of the current selection" with "defaults for the next cube." Those are different concerns. G23 new-cube inheritance already covers the second: a new cube inherits style from the selected source cube. So "set defaults then place" becomes "style a cube, place the next, it inherits." The only remaining case, the very first seed cube with nothing selected, lives as a scene-level default in the existing `SceneSection`, not in the Selector. The Selector stays strictly about selections that exist.

2. **Verb-to-subject matrix — derived from the domain, not authored.** Which verbs apply to cube/face/edge is domain truth: `relationDefs` and the projection definitions declare which subjects each supports (edge-junction is edges; face/cube-exposed are faces/cubes; face-perimeter yields edges). The UI gates verbs off this metadata exposed through the domain barrel, never a hardcoded list. Product decision made here: **verbs may change subject** (OUTER PERIMETER on selected cubes yields edges); the subject flip cascades into MODIFY naturally. A verb is shown when a compiler exists from the current subject to that verb's output.

3. **Tab stickiness — sticky, with the empty-state default only.** Sticky within a session; MODIFY on first-pick-from-empty (editing is the common intent after a click); SELECTION when the panel opens on nothing; respect the current tab otherwise. Keyboard toggle available.

4. **CLEAR vs DELETE — split.** CLEAR (selection identity, reversible) in the header. DELETE (destructive scene mutation) in MODIFY, subject-worded ("DELETE 27 CUBES"), so it is never a permanently-visible one-click footgun.

5. **Tab name — MODIFY.** It holds operations as well as properties, so PROPERTIES would undersell it.

## Migration (DECIDED direction)

- **PR0**: stand up the new Selector panel shell (header + SELECTION | MODIFY tabs). All new selection functionality lands here, never in CUBE/FACE/EDGE.
- **PR1+**: the verb + query evolution (`f1-selector-evolution.md`) builds inside the SELECTION tab of the new panel.
- **Inspector teardown**: progressively remove selection chrome (SIMILAR, PART/SET creation affordances) from CUBE/FACE/EDGE, then fold its property editors and operations into MODIFY. End state: the CUBE/FACE/EDGE inspector is fully dissolved into the Selector; its Set/Clear become the header, its Delete and operations live in MODIFY.

## Pick mode: a separate concern (2026-07-18 finding, PARKED)

PARKED 2026-07-18 (Stuart): TAB (`pickModeCycle`) suffices for now, so do NOT build a visible pick-mode control until real usage shows where the chrome belongs. Revisit after more mileage. The analysis below stands for when we return to it.

The PR1 live gate exposed a gap in this decision. The CUBE/FACE/EDGE inspector tabs did DOUBLE DUTY: they (a) set the canvas pick mode (`pickMode` = cube/face/edge in `src/domain/selection.ts`, what a canvas click selects) and (b) showed that subject's properties. This decision relocated (b) into polymorphic MODIFY but dropped (a). The capability survives (Tab cycles `pickModeCycle`; `pickModeCube/Face/Edge` commands exist in `src/editor/affordances.ts`), but it has NO visible affordance, so a user can only select cubes and cannot discover face/edge picking.

Two concepts were conflated and must stay separated:
- PICK MODE: what a canvas click selects (cube/face/edge). An INPUT control. Needs a visible home in the Selector (compact toggle; lean: top of the SELECTION tab). NOT the old tabs.
- SELECTION SUBJECT: what is currently selected; drives polymorphic MODIFY. A CONSEQUENCE.

Verb reachability model (validated live): canvas picks cubes; pick-mode cycling transforms the current selection cube -> faces -> edges; verbs then act on the landed subject. So face/edge-input verbs (e.g. OUTER PERIMETER) require a prior pivot. This is why OUTER PERIMETER is disabled on a raw cube selection and enabled after TAB -> 6 faces -> then produces the assembly's outline edges.

WHEN UNPARKED: give pick-mode a visible control. Open interaction question to pin with it: when a verb produces edges (subject = edge) while pickMode is still cube, does the next canvas click revert to a cube selection? Does a subject-changing verb also set pickMode?

## Verb combine rule (2026-07-18, from PR1)

A subject-changing verb (output subject != current selection subject) forces `combine = 'replace'`; add/subtract/intersect modifiers are only honored when the verb output subject matches the current selection subject. Cross-subject set algebra is rejected by the engine, so honoring modifiers there would silently no-op.

## Mockups on file

- `f1-selector-evolution.md` — PR1..PR5 evolution + 3 gap-state frames (empty, manual-pick→properties/modify, manual-pick→selection). Note: mockups label the second tab per the earlier PROPERTIES working name; the decision is MODIFY.
