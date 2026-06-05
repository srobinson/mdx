# Compose: the arrangement control in the Transition inspector

Composer seat, read-only pass on `feat/transitions-ux @ 4832ead`. Sources: `panels/motion/MorphInspector.tsx`, `panels/motion/MotionInspector.tsx`, `panels/motion/useMotionInspector.tsx`, `panels/motion/motionOptions.ts`, `panels/PanelTabs.tsx`, `panels/panel-tabs.css`, `panels/SegmentedField.tsx`, `evaluation/sceneMorph.ts`, `domain/morphSettings.ts`, `domain/gridLayout.ts`, plus the three chrome screenshots. Every claim about current panel behavior cites the component, not the brief's sketch.

---

## 1. The control: name and option words

**In situ, exactly as rendered:**

```
ARRANGEMENT
[ CONTINUOUS ][ AT SWITCH ]
```

Code labels `"Continuous"` and `"At switch"` (the panel uppercases via CSS, matching `panels/motion/motionOptions.ts:easingOptions` where code says `"Out"` and the panel shows `OUT`). Suggested domain values `"continuous" | "switch"`, a new field on `domain/morphSettings.ts:MorphSettings`, patched through the existing `panels/motion/MorphInspector.tsx:MorphInspectorProps.onTransitionChange` path. Persisted on the transition, so wire version bump and reset per the no-migrations policy; noted, not composed further.

**Default: CONTINUOUS.** This is slice 1's behavior, unconditional today (`evaluation/sceneMorph.ts:sampleSceneMorph` lerps `plan.arrangement.from/to` and feeds the same progress to `interpolateGridState`). The control adds one deliberate departure, not a menu of curiosities.

**Why two options, not three.** The straw man `Snap | Ease | Hold` dissolves under the panel's own semantics:

- *Snap at the start* is the defect slice 1 removed, so it is not offered. A user who genuinely wants the jump early gets it compositionally: AT SWITCH plus SCENE SWITCH near 0.00 is an authored extreme of two controls, never a named preset that dignifies the old bug.
- *Hold until the end* is AT SWITCH with SCENE SWITCH at 1.00. A separate Hold option would be a second timing knob duplicating what `MorphSettings.cutAt` already parametrizes. One timing owner, per its own doc comment: "Point in local progress where non-interpolated fields cut over."
- What remains is one honest binary: does the arrangement interpolate like the continuous channels, or step with the discrete ones. `sampleSceneMorph` already runs exactly those two regimes; the control chooses which family the arrangement joins.

**Why these words.** AT SWITCH deliberately reuses the panel's own term: the field two rows above is SCENE SWITCH (`MorphInspector.tsx` label `"Scene switch"`), and the discrete fields (`frameId`, `polarity`, `projection`, `align`) already step at that fraction in `sampleSceneMorph` via `globalCut`. Same word, same concept, same moment: ubiquitous language, not collision. CONTINUOUS is the ratified word for slice 1's behavior and appears in code only in that sense (tween-continuity comments in `evaluation/sceneMorph.ts` and `evaluation/sharedEdgeTweens.ts`).

**Words audited and rejected** (each is owned elsewhere in this codebase):

| Word | Owner | Cite |
|---|---|---|
| Snap | The Modify panel's "Snap home" action | `panels/CubeSection.tsx` |
| Ease | The EASING field in this very panel | `panels/motion/motionOptions.ts:easingOptions` |
| Hold | Pointer hold gestures | `interaction/interactionCore.ts` |
| Cut | `TransitionMode` | `domain/score.ts:TransitionMode` |
| Blend | Camera track path mode (`"blend" \| "cut"`) | `domain/cameraTrack.ts` |
| Glide | Morph class and camera preferences | `domain/morphSettings.ts:MorphSettings.glide` |
| Travel | View controls ("Travel forward") | `controls/view/viewControlDefinitions.ts` |
| Drift | Working pose diverging from its saved State | `state/pieceSessionSelectors.ts` |
| Frame, Align | `frameId`, `GridFormat.align` | `domain/grid.ts` |

**Idiom.** The row renders as a `panels/SegmentedField.tsx:SegmentedField`, white fill on the active option. Style law: white fill on dark is a property's set value, and this is a set value of the transition, exactly like ORDER and EASING. Nothing here is selection scope, so nothing is orange.

---

## 2. The whole inspector, composed

```
TRANSITION
STATE 1 TO STATE 2

Cubes present only in the next state.          ← contextual sentence slot

DURATION MS [ 1200 ]   SCENE SWITCH [ 0.50 ]

ARRANGEMENT
[ CONTINUOUS ][ AT SWITCH ]

CUBES
  ENTERING 2    LEAVING 0    MOVING 1
  ══════════                                   ← underline on active tab; LEAVING 0 dimmed

ORDER        [ MADE ] [ RADIAL ]
             [ X    ] [ SPIRAL ]
             [ Y    ] [ SHELL  ]
             [ Z    ] [ DICE   ]
STAGGER MS   [ 40 ]
EASING       [ OUT ][ INOUT ][ LINEAR ][ SETTLE ]
STEPS        [ 0 ]
```

**Where and why.** The panel already has a scope seam: everything above the CUBES row patches the whole transition (`onTransitionChange` in `panels/motion/MorphInspector.tsx`), everything below patches the selected class (`onMotionChange`). The arrangement is one value per transition, not per class (`sampleSceneMorph` resolves one offset pair for the whole gap in `prepareSceneMorphTopology`), so the row sits above the CUBES tabs with the other transition-scoped controls. It sits directly under the DURATION MS / SCENE SWITCH row so that AT SWITCH's referent is on screen one row above it; the option explains itself by adjacency.

**The contextual sentence.** The slot exists today under the title and is driven by the active CUBES tab (`panels/motion/MorphInspector.tsx:morphClassHints`). With the arrangement control added, the slot follows the last-touched group, which is the inspector's own idiom (the floating slot itself is last-touched-wins across State / Transition / Selection). On open it shows the auto-selected class hint. Exact sentences:

Per arrangement state, shown when the user touches the control:

- CONTINUOUS: `Position and spacing cross the whole transition smoothly.`
- AT SWITCH: `Position and spacing jump at the scene switch.`

Per CUBES tab, unchanged from `morphClassHints`, shown when the user touches a tab:

- Entering: `Cubes present only in the next state.`
- Leaving: `Cubes absent from the next state.`
- Moving: `Cubes shared by both states.`

The sentences avoid "grid", "frame", "align", and "placement" (all owned: `frameId`, `GridFormat.align`, `CubePlacement`); "position and spacing" is the user-facing reading of what the arrangement actually is (alignment offset plus origin, cell size, and gaps, per `domain/gridLayout.ts:getSceneGridAlignment` and `evaluation/sceneMorph.ts:interpolateGridState`).

---

## 3. Tab treatment, counts, and the empty state

**Idiom: the SELECTION underline.** Of the two existing treatments, the underline is the deliberate selected-tab idiom (`panels/panel-tabs.css:.cc-panel-tab[aria-selected="true"]`, rendered by `panels/PanelTabs.tsx:PanelTabs`); the boxed outline seen on MODIFY in the screenshot is that same component's `:focus-visible` ring, not a second selected-state design. The CUBES row becomes a `PanelTabs` instance, which brings the underline, keyboard arrow navigation, and correct `role="tab"` semantics for free. No third treatment is introduced; the row stops masquerading as a set value (its current `SegmentedField` white fill wrongly claims "this is a property value" for what is navigation between class editors).

**Counts in labels.** `ENTERING 2  LEAVING 0  MOVING 1`. The counts come from the same classification the canvas renders: `evaluation/sceneMorph.ts:prepareSceneMorphTopology` (`addedCells` → Entering, `removedCells` → Leaving, `changedCells` → Moving), so the label and the animation can never disagree. `PanelTabs` currently renders raw tab ids; the builder maps tab id to a label string, the same pattern `MorphInspector.tsx:morphClassLabels` already uses.

**Dimmed but editable, concretely.** A zero-count tab renders its label at the existing dim token `--cc-alpha-muted` (`styles/tokens.css`), the panel's ratified "not applicable, still in place" treatment, while remaining clickable. It is *not* passed to `PanelTabs`'s `disabledTabs`, because disabled means not-allowed cursor and unreachable by arrow keys (`panels/panel-tabs.css:.cc-panel-tab:disabled`), and the owner ratified authoring-before-cubes-exist. Clicking `LEAVING 0` selects it, underline and full opacity on the label, body controls (ORDER, STAGGER MS, EASING, STEPS) live and editable; the settings simply have no subjects yet.

**Auto-select on open.** `panels/motion/MotionInspector.tsx:TransitionInspector` currently hardcodes `useState<MorphClassId>("arrive")`. Composed: initial selection is the first class in arrive, depart, glide order with a nonzero count; all empty falls back to arrive.

---

## 4. What the user sees on the canvas

- **CONTINUOUS**: in a gap whose endpoints arrange differently, the whole scene translates and re-spaces steadily from the first frame to the last, with no jump anywhere.
- **AT SWITCH**: the scene holds the outgoing position and spacing, then steps to the incoming ones in one visible jump at the SCENE SWITCH fraction, the same instant the frame, polarity, projection, and align already step (`evaluation/sceneMorph.ts:sampleSceneMorph`, the `globalCut` branch).
- **The common case is invisible.** When both endpoints resolve the same arrangement (same align, origin, spacing, and extent centre; for example symmetric growth), the two options render identical frames and the control has no visible effect. Most transitions are in this case; the control earns its row only in arrangement-changing gaps, which is also why it must not pretend the old first-frame jolt was one of its options.

---

## Proposal in one line

`ARRANGEMENT  [ CONTINUOUS | AT SWITCH ]`, transition-scoped, seated under SCENE SWITCH; CUBES become underline tabs with counts, dimmed-but-editable when empty.
