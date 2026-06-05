# Cubicell UX: Transition panel composition (Seat A)

Scope: the Transition inspector rendered by `MorphInspector` (shared Editor and Studio by contract), the CUBES class tabs, the new FRAME control, and the filmstrip Transition card in `PieceStateStrip`. Ideation only. All symbols cited by name.

## 1. Panel composition, top to bottom

Exact field order and label text. Unchanged rows marked (as is).

1. `TRANSITION` (as is)
2. `STATE 1 TO STATE 2` (as is)
3. Contextual sentence, now live: the active class count in sentence case, muted. See section 2 for exact strings. Renders in the existing `morphClassHints` slot (`Label size="sm" tone="muted"`), fed by the `prepareSceneMorphTopology` diff instead of static copy.
4. `DURATION MS [1200]` `SCENE SWITCH [0.50]` (as is, one row)
5. `FRAME` with options `SNAP | EASE | HOLD`. `EASE` is the default and renders white filled, per the set-value idiom. Owner decision, not relitigated here.
6. Frame readout sentence, muted, directly under the FRAME control. See section 2.
7. `CUBES` with tabs `ENTERING | LEAVING | MOVING` (as is). Tabs whose population is empty render dimmed per the not-applicable idiom: dimmed label, dimmed border, still in place, still clickable. On inspector open, the active tab is the first non-empty class in order ENTERING, LEAVING, MOVING; if all three are empty, ENTERING stays active and dimmed.
8. `ORDER` (as is)
9. `STAGGER MS` (as is)
10. `EASING` (as is)
11. `STEPS` (as is)

When the active tab's population is empty, the tab-scoped block (ORDER through STEPS) renders dimmed but stays editable. The values are real stored motion; they apply the moment the states change to give the class members. Dimming answers the user's "no visible impact" complaint at the moment it would occur, without hiding or locking anything.

## 2. The four gap shapes

Class sentences use the existing header slot. Frame readout sits under FRAME. All sentence case, muted, product voice.

### (a) Cubes added on one side, frame moves (1 to 2, grown +x)

- Tabs: ENTERING normal and auto-active. LEAVING dimmed. MOVING dimmed (the retained cube did not change pose, so it belongs to no class; the frame carries it).
- Header sentence: `1 cube enters.`
- FRAME: full strength, EASE filled.
- Frame readout: `Frame moves 0.75 on x, carrying 1 cube.`

### (b) Cubes added symmetrically, frame does not move (1 to 3, one each side)

- Tabs: ENTERING normal and auto-active. LEAVING dimmed. MOVING dimmed.
- Header sentence: `2 cubes enter.`
- FRAME: dimmed (label, options, border), still in place, still clickable. The three options are indistinguishable when displacement is zero, so the control is not applicable, and the dim states that.
- Frame readout: `Frame does not move.`

### (c) Cubes removed only (2 to 1, removed from one side)

- Tabs: LEAVING normal and auto-active. ENTERING dimmed. MOVING dimmed.
- Header sentence: `1 cube leaves.`
- FRAME: full strength when removal is asymmetric, since `createSceneGridLayout` recentres over the destination set and the extent centre shifts. Symmetric removal falls into shape (b) treatment.
- Frame readout: `Frame moves 0.75 on x, carrying 1 cube.`

### (d) Pose change only, same cube set

- Tabs: MOVING normal and auto-active. ENTERING dimmed. LEAVING dimmed.
- Header sentence: `2 cubes move.`
- FRAME: the rule is mechanical, not per shape. Dim exactly when the computed frame displacement between source and destination layouts is zero. A pose change that leaves the extent centre alone dims FRAME; one that drags the extent to a side lights it.
- Frame readout: `Frame does not move.` (or the moves sentence when displacement is nonzero)

Degenerate shape, identical states: all three tabs dimmed, FRAME dimmed, header sentence `Nothing changes in this transition.`

## 3. Where FRAME sits, and dim versus hide

FRAME sits in the transition-wide band, directly after the DURATION MS and SCENE SWITCH row and before CUBES. The panel already has exactly two zones: gap-wide above CUBES, tab-scoped below it. Everything below CUBES holds its value per tab, and users have learned that. A gap-wide control trailing the tab block would read as belonging to the active tab, which is precisely the confusion (settings with no visible owner) this redesign exists to remove. FRAME is a property of the gap, so it lives with the gap's other properties.

Dimmed, never hidden, when the frame does not move. Three reasons. The style law already defines not-applicable as dimmed and in place (Selector's EDGES, SHELL, INTERIOR). Hiding causes layout jumps as the user edits states and the displacement flickers across zero. And a dimmed FRAME teaches the vocabulary even in transitions where it is moot, so the user is not surprised by it the first time a frame actually moves.

## 4. Component mapping

No new primitives.

| Control | Component | Precedent |
|---|---|---|
| FRAME segmented | `SegmentedField` | Same as EASING |
| Frame readout | `Label size="sm" tone="muted"` | Same as the class hint |
| Live class sentence | Existing `morphClassHints` slot in `MorphInspector`, string derived from the `prepareSceneMorphTopology` diff | Existing slot |
| Dimmed CUBES tabs | `Segmented`, with a per-option `dimmed` flag added to its option type | One-line extension: the dimmed idiom exists in the Selector, `Segmented` merely predates any inapplicable option; a parallel tab component would be the defect |
| Dimmed tab block | CSS state on the existing `cc-dock-assembly` container | No component change |
| Filmstrip card | Existing Transition card in `PieceStateStrip`, with `PieceStripTransition` reshaped to carry class deltas | Existing card |

Domain note, not UI: FRAME maps to one new field on `MorphSettings` (for example `frame: "snap" | "ease" | "hold"`), consumed where `createSceneGridLayout` and `interpolateGridState` compose the recentre. SNAP names the current measured behavior. No migration branches, per project policy.

## 5. Filmstrip Transition card

Today the card shows the Entering class's order and easing (`MADE` over `OUT`) plus duration, which describes nothing when nothing enters. Replace the two class rows with one population summary row derived from the topology diff, keep duration as is:

- `+1 CUBE` for growth, `-2 CUBES` for removal, `+1 -2` combined
- `3 MOVE` when only pose changes
- `STILL` when nothing changes
- Duration row unchanged: `1200 ms`

Order and easing come off the card entirely. The card is a summary of what the transition does; how it does it lives one click away in the inspector. `PieceStripTransition` drops `easing` and `order` in favor of the delta counts.

## 6. Departures from the orchestrator's proposal

1. **Drop FOLLOW.** SNAP, EASE and HOLD each name a user-visible intent. FOLLOW (presence-weighted) is a tuning variant of EASE with no mental model a user can predict, and it can be added later behind the same segmented control if EASE proves insufficient. KISS.
2. **No counts on the tab labels.** A number inside a segmented option exists nowhere in the product, and the style law already routes counts through prose readouts. The live sentence carries the count; the dimmed tab carries the emptiness. Both reuse existing idioms; a count badge would be a third.
3. **FRAME gets its own readout line.** The header sentence stays bound to the active class. One slot serving two subjects would flicker between "1 cube enters." and frame copy as the user moves between controls.
4. **HOLD has a cost the proposal does not name.** Anchoring retained cubes makes frame placement path-dependent: after a HOLD gap the piece no longer sits at the destination state's canonical centred layout, the next transition inherits that displacement, and per-State captured camera views were authored against the canonical layout. HOLD is still worth shipping, but this consequence needs an explicit owner decision (likely: HOLD displaces only during the gap's own composition, and the readout states the carried offset).

One adjacent observation, out of scope but recorded: `TransitionMode "cut"` remains without any editor control. FRAME SNAP is not that control and should not be conflated with it.
