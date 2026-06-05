# Authoring UX for a Rich Selection Query Language: Prior-Art Report

_Research supplement for warroom `select-ux` (cubicell selection query language authoring surface). 2026-07-10._

## Executive Summary

Every mature tool that exposes selection power converges on the same three-layer shape: a **one-tap "select similar to this" entry point** (exemplar-driven), a **post-hoc refinement surface** that lets you widen/narrow/re-scope *after* the operation runs, and an optional **structured predicate builder** for power users. The single most transferable idea is Blender's *operator-redo panel*: run the selection first with sensible defaults, then expose its compiled parameters as live, editable controls that re-run on every change. The single most avoidable anti-pattern is AutoCAD's modal FILTER dialog: a blank predicate form shown *before* any result, with its own opaque grammar. The "canvas is the control, one-tap first" thesis maps almost perfectly onto the Blender lineage, and the "compiled predicates as toggleable chips" idea is directly validated by Linear/Notion filter builders.

---

## Detailed Findings (by theme)

### Theme 1 — The exemplar-first "select similar" entry point is universal, and it always needs an escape hatch to a threshold

The dominant entry pattern across 3D, CAD, and vector tools is: user selects **one** element, invokes a single command, and the tool generalizes. Blender's **Select Similar (Shift+G)** is the archetype: with one face/edge/vertex selected, it offers a context-sensitive menu of *which* trait to generalize on (area, perimeter, normal, coplanar, material, sharpness for edges, etc.), then selects all matching elements.

The critical detail: for numeric traits it exposes a **Threshold** slider so "similar" is tunable rather than exact-match. This is the whole game for an attribute-predicate language, where negate + tolerance are already built in. The exemplar picks the *dimension*; the threshold picks the *tolerance*; both are the user's mental model already.

- **Transferable pattern:** one element selected -> a compact menu of "generalize on WHICH trait" -> immediate result with a tolerance control. This is the any/all exemplar quantifier plus tolerance, surfaced as two interactions.
- **Ergonomic win:** zero syntax. The user never names a property or types a value; they point at an example and pick an axis of similarity.
- **Pitfall/complaint:** the Shift+G menu is *flat and modal* — you commit to one trait per invocation and can't combine "same area AND same normal" in one gesture. Users build add-ons (e.g. Preselect) precisely because chaining traits requires repeated invocations. **Lesson: the exemplar menu must be multi-select or must feed a refinement surface, not be a one-shot.**

Illustrator's **Select > Same** submenu and Figma's **Edit > Select all with same** are the 2D equivalents. Same strength (one tap), same ceiling: **single axis, no tolerance, no combine.** Figma's is so limited the community ships "Select Similar" plugins to fill the gap. The 2D tools prove the pattern's discoverability *and* prove that a fixed menu without tolerance or composition hits a wall fast — exactly the wall the relation/projection predicates need to clear.

### Theme 2 — The operator-redo panel: run first, refine live (the crown jewel)

Blender's most copyable idea is the **"Adjust Last Operation" / operator-redo panel** (bottom-left of the viewport, re-openable with **F9**). After *any* operator runs, its parameters appear as live controls; editing any of them **re-runs the operator from the pre-op state**. For Select Similar this means: fire it with a default threshold, see the result on-canvas, then drag the threshold and watch the selection breathe in real time.

Why this is the keystone for "canvas is the control":
- It **inverts the CAD order**. CAD shows you a form, then a result. Blender shows you a result, then the form — and the form is optional. You get a defaulted answer on the first tap and only touch controls if the default was wrong.
- The panel is **transient and non-modal**. It floats over the canvas, doesn't block, and evaporates on the next action. State lives with the operation, not in a dialog you dismiss.
- **Extend** is a checkbox *in that panel*, so "add to selection vs replace" is a post-hoc toggle, not a modifier key you had to remember to hold. The combine modes (replace/add/subtract/intersect) map exactly onto this: they belong in the redo panel as a segmented control, defaulting to replace, changeable after the fact.

- **Transferable pattern:** every selection query emits a floating, canvas-anchored refine panel showing its compiled parameters (which predicates fired, threshold, quantifier, combine mode) as live controls; any edit re-runs against the canvas immediately.
- **Ergonomic win:** the user is never asked to predict parameters. They react to a visible result. Purest expression of "one-tap first, progressively disclosed."
- **Pitfall/complaint:** Blender's redo panel is genuinely **hard to discover** and easy to lose — one stray click and it's gone; new users don't know F9 brings it back (design bug T57727). **Lesson: make the refine affordance persistent and obviously re-summonable, not a click-to-dismiss ghost.**

### Theme 3 — Named/reusable selection primitives: the topology library (Blender + Rhino)

Beyond "similar," mature 3D tools ship a **library of named topological selections** that are exactly the relation and projection predicates, already validated as useful primitives:

- **Select Sharp Edges** — selects edges whose dihedral angle exceeds a threshold. This *is* the edge-junction/convex/concave classification, exposed as a named command with an angle slider. Note it too has a post-op threshold.
- **Select Boundary Loop** — from a face region, selects only the contour edges; it even auto-switches from Face mode to Edge mode on run. This is precisely the **face-perimeter projection** ("outer top edges"). The mode auto-switch is a UX tell: a projection *changes the element type of the result*, and the tool makes that visible by flipping the active select mode.
- **Select Linked (L / Ctrl+L)** — grows selection across connectivity, with **delimiters** (stop at seams, sharp edges, materials, UV islands). The delimiter concept is a lightweight relation predicate stacked onto a flood-fill.
- **Rhino Named Selections** — save any selection by name and restore it later. The "I built a good selection, let me name and reuse it" pattern.

- **Transferable pattern:** ship the relation/projection predicates as **named, one-tap verbs** ("Outer Top Edges," "Exposed Faces," "Convex Seams") with a single threshold each, not only as clauses in a query grammar. Most usage is one named verb; the grammar is the power-user floor beneath it.
- **Ergonomic win:** discoverability by browsing a verb list beats recalling a syntax. Users find capability they didn't know to ask for.
- **Pitfall/complaint:** naming is hard and the list grows unwieldy. Blender's Select menu is a deep, nested tree navigated by muscle memory. **Lesson: a searchable command palette ("select...") beats a deep menu; keep the named-verb surface flat and filterable.**

### Theme 4 — Structured predicate builders (CAD): powerful, precise, and where UX goes to die

AutoCAD **QSELECT** is the canonical structured builder: a modal dialog with **Apply to** (Entire drawing / Current selection — the *scope*), **Object type**, **Property**, **Operator** (Equals, Not Equal, Greater/Less Than, Wildcard Match — negate + comparators), **Value**, and **Include/Exclude in new set** (combine modes). The older **FILTER** command adds *saved, named, reusable* filter definitions with grouped AND/OR logic.

This is the most complete feature-for-feature analog to the language — and also the least loved. The complaints are consistent:
- It is **modal and blind**: you build the whole predicate against a blank slate, hit OK, and *only then* see what you caught. No live preview. Get it wrong, reopen, rebuild.
- **One property per rule** in QSELECT; multi-property requires chaining QSELECT calls or dropping into FILTER's clunkier grouped grammar.
- FILTER's grammar (with `**Begin OR` / `**End OR` bracket rows) is notoriously arcane.

Fusion 360 took the opposite, lighter tack: instead of a predicate dialog, **selection *priority* filters** (Body / Face / Edge / Component priority; only one active at a time) plus semantic helpers like **Seed and Boundary** (pick a seed face + boundary edges -> selects the enclosed region) and **Select by Name**. Fusion's bet: **filter the *element type* the canvas will pick, then let direct manipulation do the rest** — far closer to "canvas is the control" than QSELECT's form.

- **Transferable pattern:** the *fields* of QSELECT (scope / type / property / operator / value / include-exclude) are the correct decomposition of a predicate — steal the schema. Fusion's element-type priority is the right "what am I even selecting" pre-filter.
- **Ergonomic win (Fusion):** constraining the pickable element type removes the #1 source of mis-selection without any dialog.
- **Pitfall/complaint (AutoCAD):** modal + blind + one-rule-per-pass + arcane grouping. **This is the anti-pattern to consciously invert.** Never show the builder before a result exists.

### Theme 5 — Expression/procedural selection (Houdini, Grasshopper): the ceiling, not the floor

Houdini's **Group SOP** and **Group Expression SOP** represent the maximal-power end: selection as a VEX expression evaluated per point/primitive/vertex, with built-in modes for **bounding-region, by normal direction, by edge angle, by primitive angle**. Groups are **named, persistent, and reusable downstream** — the selection *is* a first-class named entity in the graph, decoupled from any transient viewport state.

The transferable insight is architectural, not visual: Houdini **separates the selection *definition* (the group, a named reusable query) from the *current viewport highlight*.** The query persists; the highlighted ids are just its current evaluation. This is the correct data model for the engine — and it matches tldraw's signal architecture (Theme 6).

- **Transferable pattern:** treat a compiled query as a nameable, re-evaluable object distinct from "the ids currently glowing." Persist the query; recompute the ids reactively.
- **Ergonomic win:** re-running the same named selection after the model changes just works; the query re-evaluates.
- **Pitfall/complaint:** expression syntax is a wall for non-technical users. **Do not make the expression the primary surface.** It should be the "reveal the compiled query as editable text" affordance under the chips, for the 5% who want it.

### Theme 6 — Reactive selection state (tldraw): keep the query separate from the selected ids

tldraw's architecture is the reference implementation for "query state separate from selected ids." Selection is an **atom** (`_selectedShapeIds = atom(...)`) and the resolved shapes are a **computed** signal derived from it. Anything downstream (highlight rendering, the refine panel, counts) subscribes and updates automatically; only affected shapes re-render.

For this design that dictates the data flow: a **compiled query** is the atom (predicates + quantifier + combine mode + threshold); the **highlighted ids** are a computed derivation; the **refine chips and on-canvas count** are subscribers. Editing a chip mutates the query atom; the ids and highlight fall out reactively. This is what makes "drag threshold -> selection breathes" feel instant, expressed as a clean state model.

- **Transferable pattern:** query = source of truth (atom); selected ids = derived (computed); UI = reactive subscribers. Never store ids as the primary state and reverse-engineer the query.
- **Pitfall/complaint:** if users hand-edit the raw id set (manual add/subtract clicks), you must decide whether that detaches from the query or becomes another combine layer. **Decide early: is a manual click a new `add` clause on the query, or does it drop you to a raw-id "custom" state?** (Recommend: manual clicks become an explicit `+add`/`-subtract` clause chip, so the query stays the source of truth.)

### Theme 7 — Filter chips / pills (Linear, Notion): the exact UI for "compiled predicates as toggleable chips"

**Linear:** press **F** to open the filter menu, type-to-filter the property, and each active filter renders as a **pill with three independently-clickable zones**: the **property** ("Assignee"), the **operator** ("is" / "is not"), and the **value**. Clicking the operator zone flips is<->is-not; clicking the value opens a picker. The filter *type* is fixed once created, but every other part is live-editable in place. Add another filter and they compose. This is a near-perfect on-canvas representation of *one predicate*: **property = the trait, operator = negate/comparator, value = the target + tolerance.** A row of these chips = the compiled predicate set, each independently editable and dismissible.

**Notion:** starts with flat AND-chips, but a simple filter can be **promoted to an "advanced filter" with nested filter groups** combining AND/OR up to three levels deep. This is the graceful path from a simple predicate list to combine modes (add=OR-ish, intersect=AND, subtract=AND NOT). The key UX move: **the simple case is flat chips; complexity is *opt-in* via "add filter group," not paid up front.**

- **Transferable pattern:** render each compiled predicate as a **three-zone pill** (trait . operator . value), independently editable and removable; a "+" adds a predicate; combine mode is a group-level control. Promote to nested groups only on demand.
- **Ergonomic win:** the query is legible and directly manipulable *without a grammar*. Users read their own selection back as plain chips and tweak one zone at a time.
- **Pitfall/complaint:** Linear locks the filter *type* after creation (delete-and-re-add to change trait); nested groups (Notion) become hard to read past two levels. **Lesson: keep chips flat by default, cap visible nesting, make trait-swapping cheap.**

---

## Synthesis: UX Patterns Most Worth Stealing

Ordered by leverage for a "one-tap-first, progressively-disclosed" surface:

1. **Result-first, form-second (Blender operator-redo).** Every selection fires immediately with sensible defaults; a floating, canvas-anchored **refine panel** exposes the compiled query as live controls that re-run on every edit. The spine of the whole authoring surface. Invert AutoCAD entirely: never a blank form before a result. Make the panel **persistent and obviously re-summonable** (Blender's #1 failing).

2. **Exemplar -> "generalize on which trait" (Select Similar / Select Same).** One-tap entry: select a cube/face/edge, get a compact menu of *which* attribute or relation to generalize on, land a result instantly. The any/all exemplar quantifier as a two-interaction gesture with **zero syntax**. Unlike Blender/Figma, make it **multi-trait** by feeding the result straight into the chip surface (pattern 3) instead of being one-shot.

3. **Compiled predicates as three-zone chips (Linear).** Show the resulting query on-canvas as a row of pills: **trait . operator(negate/compare) . value(+tolerance)**, each zone independently editable, each chip dismissible, a "+" to add. Query legible and directly manipulable without exposing grammar. Combine mode is a group-level segmented control on the chip row, defaulting to replace.

4. **Named topological verbs as first-class one-taps (Select Sharp / Boundary Loop / Rhino Named Selections).** Ship the relation/projection predicates as flat, searchable command-palette verbs ("Outer Top Edges," "Exposed Faces," "Convex Seams"), each with a single threshold. Most users invoke one verb; the grammar is the floor beneath it. Prefer a **filterable palette over a deep nested menu**. When a projection changes result element-type (perimeter -> edges), make that visible the way Blender flips select mode.

5. **Element-type pre-filter (Fusion selection priority).** A lightweight, always-visible toggle for "what am I selecting right now — cubes / faces / edges" removes the largest class of mis-selection *before* any predicate, and constrains the exemplar tap's meaning. Cheap, high-value.

6. **Query-as-source-of-truth, ids-as-derived (tldraw signals + Houdini named groups).** Store the compiled query (atom), derive highlighted ids (computed), let chips/count/highlight subscribe. Makes live-refine feel instant and keeps everything in sync. Bonus: Houdini-style **nameable, reusable, re-evaluable selections** almost for free.

## Top Anti-Patterns to Avoid

1. **The modal blind predicate builder (AutoCAD FILTER/QSELECT).** Building a full predicate against a blank slate, committing, then seeing results — with a bespoke grammar and one-property-per-pass. Complete, powerful, and *hated*. The engine's power must never be gated behind a pre-result form.

2. **One-shot, single-axis exemplar with no composition (Figma "Select all with same", Blender Shift+G's flat menu).** "Same fill" that can't become "same fill AND same size," can't tune tolerance, and forgets itself. Teaches users the tool is shallow. The exemplar tap must flow into an editable, composable, tolerance-aware surface.

3. **Expression syntax as the primary surface (Houdini/Grasshopper).** Maximal power, wall for non-technical users. Keep raw compiled-query text as a *reveal-on-demand* affordance beneath the chips, never the front door. (Secondary: Blender's **discoverability tax** — power the user can't find or get back.)

---

## The one-image design brief

Put the **AutoCAD QSELECT dialog** and the **Linear filter row** side by side. They encode the *same* predicate schema; one is dreaded, one is loved. The delta — **modal-blind vs. live-legible-inline** — is the entire design brief.

## Open Questions (for the warroom)

1. **Manual clicks vs. query state:** when a user hand-clicks a cube while a query is active, does it become an explicit `+add` clause chip (query stays source of truth) or drop to a detached "custom" id set? Recommend the former.
2. **Projection element-type transitions:** face-perimeter turns a face selection into an edge selection. Blender signals this by flipping select mode. What is the on-canvas signal, given cube/face/edge/state element classes?
3. **Combine-mode discoverability:** Linear/Notion make AND/OR opt-in via "add group." Do the four combine modes deserve equal billing, or is replace-default with add/subtract as modifier-clicks sufficient for v1?
4. **Naming/reuse (Houdini/Rhino):** is a saved/named-selection feature in scope for the first authoring surface, or a fast-follow once the chip model exists?

## Actionable Takeaways

- **Prototype the refine panel first, not the grammar.** The operator-redo + chip-row combination (patterns 1 + 3) is the highest-leverage thing to mock. Everything else hangs off it.
- **Build the exemplar tap to *emit chips*, not results directly.** Resolves the Figma/Blender one-shot ceiling and unifies "select similar" with the query builder.
- **Storyboard three tiers explicitly:** (1) one-tap exemplar or named verb -> instant result; (2) tweak the floating chips/threshold -> live refine; (3) "reveal query" text for power users.
- **Adopt tldraw's atom->computed data model now**, before UI, so live-refine and the count badge are reactive by construction.

## Sources

Blender: Select Similar / Select Sharp Edges / Advanced selection (Boundary Loop, Linked) manuals; T57727 redo-panel discoverability. CAD: AutoCAD QSELECT (Autodesk help) + FILTER; Fusion 360 selection filters + priority. Vector: Illustrator select-same; Figma select-all-with-same. Procedural: Houdini Group SOP / Group Expression SOP; Rhino Named Selections. Web: tldraw signals + Editor.ts (selectedShapeIds atom / getSelectedShapes computed). Filter chips: Linear filters; Notion advanced database filters; Bricx Labs + Pencil&Paper filtering-UX analyses.

_Confidence: high on mechanics (primary vendor docs / source); medium on sentiment/complaint claims (community consensus, corroborated by T57727 and the proliferation of Figma "Select Similar" plugins)._
