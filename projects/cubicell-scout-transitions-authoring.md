# Cubicell transition authoring scout

Source verified against `/Users/alphab/Dev/LLM/DEV/helioy/cubicell`, `main` at
`ae44cbf369fdd775d9ed7d248763d13b625db86c`.

## Reuse Map

### Transition authoring today

#### Requested motion file walk

| Surface | Current responsibility | Evidence |
| --- | --- | --- |
| Morph field set | Renders duration, scene switch, morph class, order, stagger, easing, and steps. It is presentational and emits typed settings patches. | `src/panels/motion/MorphInspector.tsx:MorphInspector` |
| Right rail motion bodies | Owns State actions, transition edit dispatch, and Build in controls. `TransitionInspector` converts UI changes into a `patch-transition` document operation for the keyframe at the focused gap index. | `src/panels/motion/MotionInspector.tsx:TransitionInspector`, `src/panels/motion/MotionInspector.tsx:StateInspector`, `src/panels/motion/MotionInspector.tsx:ArrivalInspector` |
| Right rail routing | Maps motion focus to the header and body: State, Transition, or Build in. The transition header names both endpoint States. | `src/panels/motion/useMotionInspector.tsx:useMotionInspector` |
| Motion dock orchestration | Owns transport, filmstrip data, card callbacks, focused segment preview, loop window, State selection, and automatic focus after Snapshot. | `src/panels/motion/PieceMotionPanel.tsx:PieceMotionPanel` |
| Filmstrip shell | Renders Build in, State, and Transition cards. A Transition card is a button between adjacent State options and calls `onFocusGap(index)`. | `src/panels/motion/PieceStateStrip.tsx:PieceStateStrip` |
| Focus arbitration | Stores the single `PieceMotionFocus`, remembers the last motion focus when canvas selection takes the inspector, and clears stale gap indexes when the sequence shrinks. | `src/panels/motion/motionFocusController.ts:createMotionFocusController` |
| Camera authoring | Captures, recaptures, or removes a view on the State under the playhead. This control authors State view data from the transport row. | `src/panels/motion/CameraCaptureControl.tsx:CameraCaptureControl`, `src/panels/motion/CameraCaptureControl.tsx:resolveCaptureTargetState` |

#### Field map

| Domain field | Current control and behavior | Evidence |
| --- | --- | --- |
| `Transition.mode` | No Editor control exists. The domain accepts `auto` or `cut`, `patch-transition` can carry `mode`, and the evaluator runs a forced cut. `TransitionInspector` exposes only `Partial<MorphSettings>` to its field component, so persisted or programmatic data is the current authoring path for `cut`. If surfaced, the control belongs in `TransitionInspector` as a labelled `SegmentedField` sibling above `MorphInspector`, because mode is a top level `Transition` field and `TransitionInspector` owns the top level patch. | `src/domain/score.ts:TransitionMode`, `src/domain/structureSequenceOperations.ts:StructureSequenceDocumentOperation`, `src/domain/stateTransition.ts:patchTransition`, `src/evaluation/sceneTransition.ts:sampleSceneTransition`, `src/panels/motion/MotionInspector.tsx:TransitionInspector`, `src/panels/SegmentedField.tsx:SegmentedField` |
| `MorphSettings.durationMs` | `ScrubField` labelled **Duration ms**, range 100 to 8000, step 50, rounded on commit. | `src/panels/motion/MorphInspector.tsx:MorphInspector` |
| `MorphSettings.cutAt` | `ScrubField` labelled **Scene switch**, range 0 to 1, step 0.05. | `src/panels/motion/MorphInspector.tsx:MorphInspector` |
| `MorphSettings.arrive` | The **Cubes** segmented field selects **Entering**, which is the initial class. The class then exposes Order, Stagger ms, Easing, and Steps. | `src/panels/motion/MorphInspector.tsx:MorphInspector`, `src/panels/motion/MotionInspector.tsx:TransitionInspector` |
| `MorphSettings.depart` | The same **Cubes** segmented field selects **Leaving**, then edits the same four `ClassMotion` fields. | `src/panels/motion/MorphInspector.tsx:MorphInspector`, `src/domain/morphSettings.ts:ClassMotion` |
| `MorphSettings.glide` | The same **Cubes** segmented field selects **Moving**, then edits the same four `ClassMotion` fields. | `src/panels/motion/MorphInspector.tsx:MorphInspector`, `src/domain/morphSettings.ts:MorphSettings` |

`TransitionInspector` keeps the selected morph class as local UI state, defaulting
to `arrive`, and merges each class patch into the complete class value before
dispatch. `MorphInspector` therefore has one typed edit path for all three classes.
Evidence: `src/panels/motion/MotionInspector.tsx:TransitionInspector`,
`src/panels/motion/MorphInspector.tsx:MorphInspector`.

#### How the user selects the transition

1. `PieceStateStrip` places one **Transition** button between each adjacent State pair; its accessible name contains the gap number and both State names. Evidence: `src/panels/motion/PieceStateStrip.tsx:PieceStateStrip`.
2. Clicking the button calls `PieceMotionPanel.focusSegment`, which publishes `{ kind: "gap", index }`, parks the playhead at that segment's start, and derives the focused loop window from the same index. Evidence: `src/panels/motion/PieceMotionPanel.tsx:PieceMotionPanel`.
3. `useMotionInspector` routes that focus to `TransitionInspector(index)` and renders a **Transition** header with source and destination endpoint names. Evidence: `src/panels/motion/useMotionInspector.tsx:useMotionInspector`.
4. A later canvas selection temporarily gives the inspector to cube authoring; clearing it restores the last motion focus. A stale gap is cleared after sequence shrink. Evidence: `src/panels/motion/motionFocusController.ts:createMotionFocusController`.
5. Taking a follow up Snapshot focuses the new gap automatically, while the first Snapshot focuses its new State because no gap exists yet. Evidence: `src/panels/motion/PieceMotionPanel.tsx:PieceMotionPanel`.

The card is a summary rather than an editor. It displays duration plus only the
Entering class's order and easing, while all values are edited in the right rail.
Evidence: `src/panels/motion/PieceMotionPanel.tsx:PieceMotionPanel`,
`src/panels/motion/PieceStateStrip.tsx:PieceStripTransition`.

### Grid size and cube count control

The primary grid size path is:

1. The left rail **grid** tab renders `GridSection`, whose **Size** row is a readout and whose **Edit** button opens the composer. Evidence: `src/panels/LeftRail.tsx:LeftRail`, `src/panels/GridSection.tsx:GridSection`.
2. `GridComposer` appears over the stage and renders `NumberStepper` controls for Width, Height, and Depth plus a derived **Cells** count. Each dimension is constrained to 1 through 24 and the product to 512 cells. Evidence: `src/components/grid-composer/GridComposer.tsx:GridComposer`.
3. Every accepted step calls `updateGridComposerDimensions`, which builds a `GridResizePlan` and dispatches one authored scene operation with `kind: "resize-grid"`; the edit clears selection and resets history because a grid rebuild is a clean slate. Opening the composer on an empty scene also materializes the preferred grid through the same operation. Evidence: `src/app/useSceneOperations.ts:useGridComposerOperations`, `src/domain/scene.ts:createGridResizePlan`, `src/domain/cubeOperations.ts:applySceneOperation`.

Cube count has no stored field. `GridSection` derives dimensions from the cell
set, and `StructureSection` derives its **Cubes** readout from `cells.length`.
There is no direct editable **Cubes** count. The **struct** tab shows that derived
count and offers structural edits: selected row or column headers expose
**+ before**, **+ after**, and **delete**, dispatching `insert-lattice-line` or
`delete-lattice-line`; an empty map slot dispatches `place-cubes`. Canvas Build
also places cubes, and Delete or Backspace resolves through the registered cube
delete command. Evidence: `src/domain/scene.ts:getSceneGridDimensions`,
`src/panels/StructureSection.tsx:StructureSection`,
`src/panels/StructureSection.tsx:StructureHeaderActions`,
`src/panels/useStructureSectionInteractions.ts:useStructureHeaderActions`,
`src/panels/useStructureSectionInteractions.ts:handleStructureCellClick`,
`src/editor/commands.ts:createDeleteSelectionCommand`,
`src/editor/keyboard/keymap.ts:keyboardCommandIds`.

### Control primitive inventory

| Category | Reusable symbol | Existing use | Reuse rule |
| --- | --- | --- | --- |
| Integer stepper | `NumberStepper` | Width, Height, and Depth in the grid composer. Evidence: `src/components/grid-composer/GridComposer.tsx:GridComposer`. | Use for bounded integer dimensions or counts. It supports buttons, wheel, and arrow keys. Evidence: `src/components/ui/number-stepper/NumberStepper.tsx:NumberStepper`. |
| Numeric field | `ScrubField` | Duration ms and Scene switch in transition authoring. Evidence: `src/panels/motion/MorphInspector.tsx:MorphInspector`. | Use for continuous or finely stepped values. It supports pointer scrubbing, wheel, arrows, and direct numeric entry. Evidence: `src/components/ui/scrub-field/ScrubField.tsx:ScrubField`. |
| Schema driven field | `ControlBindingField` | Grid gap X, Y, and Z in `GridSection`. Evidence: `src/panels/GridSection.tsx:GridSection`. | Reuse when a durable `ControlBinding` already owns label, read, schema, and command creation. It maps boolean, enum, and number schemas to `Switch`, `Segmented`, and `ScrubField`. Evidence: `src/panels/ControlBindingField.tsx:ControlBindingField`. |
| Segmented picker | `Segmented` | Slice axis X, Y, and Z in the Structure panel. Evidence: `src/panels/StructureSection.tsx:StructureSection`. | Use for compact direct choices. It renders pressed buttons rather than a select menu. Evidence: `src/components/ui/segmented/Segmented.tsx:Segmented`. |
| Labelled segmented picker | `SegmentedField` | Cubes, Order, and Easing in the transition inspector. Evidence: `src/panels/motion/MorphInspector.tsx:MorphInspector`. | This is the closest existing transition control for a discrete mismatch policy because it supplies the panel label and full width option layout. Evidence: `src/panels/SegmentedField.tsx:SegmentedField`. |
| Spatial or axis option grid | `SpatialOptionGroup` | Row direction X, Y, and Z in the cube selection builder. Evidence: `src/panels/CubeSpatialBuilder.tsx:CubeRowControls`. | Use inside the Selector's spatial grammar. For the compact transition inspector, `SegmentedField` matches the local convention better. Evidence: `src/panels/SpatialBuilderControls.tsx:SpatialOptionGroup`. |
| Toggle | `Switch` | Floor, Build, Axes, and Isolate in the Scene panel. Evidence: `src/panels/SceneSection.tsx:SceneSection`. | Use for an immediate binary property. Evidence: `src/components/ui/switch/Switch.tsx:Switch`. |
| Slider | No reusable slider component found | Raw range inputs exist for the transport playhead and State comparison. Evidence: `src/panels/motion/TransportPlayhead.tsx:TransportPlayhead`, `src/panels/motion/MotionInspector.tsx:StateComparisonControls`. | Extract a shared slider before adding another range input. The current two uses share `cc-dock-playhead` styling but have separate markup. |
| Dropdown | None found | No `<select>`, `Dropdown`, or reusable Select component exists under `src/components` or `src/panels`. | A dropdown would introduce a new control vocabulary. Prefer `SegmentedField`, `SpatialOptionGroup`, or a deliberate new primitive after the surface and decide gate. |
| Tabs | `PanelTabs` | Scene, grid, and struct in the left rail; selection and modify in Selector. Evidence: `src/panels/LeftRail.tsx:LeftRailTabs`, `src/panels/SelectorPanel.tsx:SelectorPanelHeader`. | Use only for sibling panel modes. It owns tab roles, roving focus, arrow keys, Home, and End. Evidence: `src/panels/PanelTabs.tsx:PanelTabs`. |
| Action | `Button` | Play, Stop, and Loop in the Motion dock. Evidence: `src/panels/motion/PieceMotionPanel.tsx:TransportRow`. | Use for imperative actions and pressed action state. Evidence: `src/components/ui/button/Button.tsx:Button`. |

Searches for absent controls covered component definitions, exports, raw inputs,
`<select>`, `Dropdown`, `Slider`, axis picker names, and every use under
`src/components` and `src/panels`.

### Panel conventions and candidate homes

#### Structure and naming

* `StudioShell` composes a left rail, right inspector, and bottom dock, with panel headers supplied separately from scroll bodies. Evidence: `src/studios/editor/EditorStudio.tsx:EditorApp`.
* The left rail uses `PanelTabs` for **scene**, **grid**, and **struct**. Selector uses **selection** and **modify**. These top tabs render their terse lowercase identifiers directly. Evidence: `src/state/cubicellState.ts:leftRailTabs`, `src/panels/SelectorPanel.tsx:selectorTabs`, `src/panels/PanelTabs.tsx:PanelTabs`.
* Motion replaces the right rail's ordinary tabs with an object title: **State**, **Transition**, or **Build in**, optionally followed by the object or endpoint names. Evidence: `src/panels/motion/useMotionInspector.tsx:useMotionInspector`, `src/panels/motion/MotionInspector.tsx:InspectorTitle`.
* Field labels use short sentence case nouns or compact measurements: **Duration ms**, **Scene switch**, **Cubes**, **Order**, **Stagger ms**, **Easing**, **Steps**. Buttons use short imperative verbs: **Edit**, **Play**, **Stop**, **Loop**, **Done**, **Set default**. Evidence: `src/panels/motion/MorphInspector.tsx:MorphInspector`, `src/panels/motion/PieceMotionPanel.tsx:TransportRow`, `src/components/grid-composer/GridComposer.tsx:GridComposer`.
* Accessible names are fuller and contextual even when visible copy stays terse. Evidence: `src/panels/motion/PieceStateStrip.tsx:PieceStateStrip`, `src/panels/motion/CameraCaptureControl.tsx:CameraCaptureControl`.

#### Legitimate homes

| Candidate | Argument | Disposition |
| --- | --- | --- |
| `TransitionInspector`, beside the existing `MorphInspector` | This component already owns the selected gap, keyframe lookup, and `patch-transition` dispatch. A policy about how two unequal endpoint States relate belongs here even if it is not a `MorphSettings` field. A surfaced `cut` control belongs here as a labelled `SegmentedField`, because `mode` is a top level `Transition` field. Evidence: `src/panels/motion/MotionInspector.tsx:TransitionInspector`, `src/panels/SegmentedField.tsx:SegmentedField`. | **Recommended. Reuse.** |
| `MorphInspector` itself | Appropriate when the new value is a shared morph setting that must travel with every use of the morph editor. It preserves the intended reusable field boundary while the current Editor host supplies the persistence owner. Evidence: `src/panels/motion/MorphInspector.tsx:MorphInspector`, `src/panels/motion/MotionInspector.tsx:TransitionInspector`. | **Conditional reuse.** Put only shared `MorphSettings` fields here. |
| Transition card in `PieceStateStrip` | The card is the established selection target and summary. A concise badge or one line summary can make the mismatch visible before selection. Evidence: `src/panels/motion/PieceStateStrip.tsx:PieceStateStrip`, `src/panels/motion/PieceMotionPanel.tsx:stripTransitions`. | **Summary only.** Keep editing in the right rail. |
| Transport row | The dock contract says it owns transport and previews, while card editing happens in the shared right rail. `CameraCaptureControl` is a deliberate State view exception tied to the playhead. Evidence: `src/panels/motion/PieceMotionPanel.tsx:PieceMotionPanel`, `src/panels/motion/CameraCaptureControl.tsx:CameraCaptureControl`. | **Do not add the new gap editor here.** |
| Grid or Structure panel | These panels edit the live working scene and grid. They have no selected gap identity and would create a second transition authoring path. Evidence: `src/panels/GridSection.tsx:GridSection`, `src/panels/StructureSection.tsx:StructureSection`. | **Exclude.** Reuse their primitives, not their ownership. |

### The State and Play split

1. A State may own one captured `StateCameraView`, and `CameraCaptureControl` writes that view to the State selected by the active card or resolved under the playhead. Evidence: `src/domain/workbench.ts:State`, `src/panels/motion/CameraCaptureControl.tsx:CameraCaptureControl`.
2. `compilePieceCameraTrack` derives the camera route from those State views and the State transition timing, while `useCameraTrackFrame` samples the derived track only during Play at the piece score clock. Evidence: `src/domain/pieceCameraTrack.ts:compilePieceCameraTrack`, `src/studios/editor/useCameraTrackFrame.ts:useCameraTrackFrame`.
3. A transition remains gap owned through `PieceMotionFocus { kind: "gap" }` and `TransitionInspector`, so new transition authoring belongs in that gap body while State view capture stays attached to the target State. Evidence: `src/panels/motion/motionFocusContext.ts:PieceMotionFocus`, `src/panels/motion/MotionInspector.tsx:TransitionInspector`.

## Quality Map

| Finding | Fact and risk | Disposition before design |
| --- | --- | --- |
| Dormant `Transition.mode` authoring | `cut` is working and tested, but the Editor cannot author it. A new transition design could accidentally imply that all existing fields are surfaced, or add another policy while leaving the foundational mode invisible. Evidence: `src/domain/score.ts:TransitionMode`, `src/evaluation/sceneTransition.ts:sampleSceneTransition`, `src/panels/motion/MotionInspector.tsx:TransitionInspector`. | **Decide.** Surface mode in the new control, explicitly park it, or remove it as a product decision. |
| Raw range duplication | Transport and State comparison each own raw range markup with shared styling and no reusable slider symbol. A third range would deepen duplication. Evidence: `src/panels/motion/TransportPlayhead.tsx:TransportPlayhead`, `src/panels/motion/MotionInspector.tsx:StateComparisonControls`. | **Refactor first if needed.** Extract one slider primitive before a new slider use. |
| Transition summary represents only Entering | The card derives its order and easing from `settings.arrive`; Leaving, Moving, Scene switch, Steps, and Stagger stay invisible until inspection. A new mismatch policy could become another hidden material behavior. Evidence: `src/panels/motion/PieceMotionPanel.tsx:PieceMotionPanel`, `src/panels/motion/PieceStateStrip.tsx:PieceStripTransition`. | **Reuse with a summary decision.** Add one compact signal only if the policy materially changes the gap's identity. |
| Mixed transport and State mutation row | `CameraCaptureControl` writes State view data from the transport row, using playhead derived targeting. This intentional exception already makes the row span transport and authoring boundaries. Evidence: `src/panels/motion/CameraCaptureControl.tsx:CameraCaptureControl`, `src/panels/motion/PieceMotionPanel.tsx:TransportRow`. | **Contain.** Keep the new gap control in the inspector. |
| Shared morph claim has one live host | `MorphInspector` describes Editor and Studio reuse, while the current source mount is `TransitionInspector`; Studio reuse remains a design contract rather than a second live host. Evidence: `src/panels/motion/MorphInspector.tsx:MorphInspector`, `src/panels/motion/MotionInspector.tsx:TransitionInspector`. | **Validate before widening.** Shared wire fields belong here; Editor specific endpoint analysis belongs in `TransitionInspector`. |
| Focus behavior spans controller and dock orchestration | The controller owns focus memory and selection synchronization; `PieceMotionPanel` adds preview scrub, camera alignment, same State toggling, and Snapshot focus rules. A new control that writes focus independently could bypass those coupled behaviors. Evidence: `src/panels/motion/motionFocusController.ts:createMotionFocusController`, `src/panels/motion/PieceMotionPanel.tsx:PieceMotionPanel`. | **Reuse.** Consume the focused gap from `usePieceMotionModel`; add no second focus owner. |
| Gap settings stay bound to gap positions during reorder | Moving State keyframes reorders States while leaving transition settings in their gap slots. Any endpoint specific mismatch state stored elsewhere could silently diverge after reorder. Evidence: `src/domain/stateTransition.ts:moveKeyframe`. | **Preserve or decide.** Store the new value with `Transition` when it describes the gap, and test reorder semantics. |

## Plan

1. **Decide the domain owner before drawing the control.** Classify the new value as a gap policy on `Transition`, a shared evaluator setting in `MorphSettings`, or a State property. Use the first for endpoint relationship policy, the second only when every morph host must expose it, and the third only when it remains true outside any particular gap. Evidence: `src/domain/score.ts:Transition`, `src/domain/morphSettings.ts:MorphSettings`, `src/domain/workbench.ts:State`.
2. **Reuse the existing selection route.** The Transition card continues to select `{ kind: "gap", index }`; `useMotionInspector` continues to resolve the one right rail body; the new control reads the exact transition through `TransitionInspector`. Evidence: `src/panels/motion/PieceStateStrip.tsx:PieceStateStrip`, `src/panels/motion/useMotionInspector.tsx:useMotionInspector`, `src/panels/motion/MotionInspector.tsx:TransitionInspector`.
3. **Use `SegmentedField` for a small discrete policy.** It already carries Cubes, Order, and Easing inside this inspector, supports terse visible labels, and avoids introducing a dropdown. Use `NumberStepper` for bounded integer dimensions or counts and `ScrubField` for continuous timing only. Evidence: `src/panels/SegmentedField.tsx:SegmentedField`, `src/components/ui/number-stepper/NumberStepper.tsx:NumberStepper`, `src/components/ui/scrub-field/ScrubField.tsx:ScrubField`.
4. **Dispatch through the existing document operation.** Extend the existing `patch-transition` payload only if the wire needs a new gap field; do not add a parallel command or store writer. Evidence: `src/domain/structureSequenceOperations.ts:StructureSequenceDocumentOperation`, `src/domain/stateTransition.ts:patchTransition`, `src/panels/motion/MotionInspector.tsx:TransitionInspector`.
5. **Keep the card as a selector and summary.** Add a compact mismatch or policy summary only when it helps users choose the right gap before opening it. Derive that summary beside the existing `PieceStripTransition` mapping. Evidence: `src/panels/motion/PieceMotionPanel.tsx:PieceMotionPanel`, `src/panels/motion/PieceStateStrip.tsx:PieceStripTransition`.
6. **Resolve `Transition.mode` in the same design round.** Record one surface and decide disposition before implementation so the new UX does not preserve an unexplained dormant authoring path. Evidence: `src/domain/score.ts:TransitionMode`, `src/evaluation/sceneTransition.ts:sampleSceneTransition`.
7. **Prove the observable authoring seam.** Test selecting a specific gap, seeing the endpoint title and current value, changing the control, and observing one `patch-transition` against that gap's keyframe. Cover unequal cube counts, unequal grid dimensions, zero duration, State reorder, Snapshot created gaps, canvas selection takeover and restore, and a card summary if one is added. Evidence: `src/panels/motion/PieceStateStrip.tsx:PieceStateStrip`, `src/panels/motion/motionFocusController.ts:createMotionFocusController`, `src/domain/stateTransition.ts:moveKeyframe`.
8. **Run live proof after tests.** In the real Editor, create two unequal States, select their Transition card, change the new control, loop the focused segment, and verify the result belongs only to that gap while State selection and camera capture retain their current behavior. Evidence: `src/panels/motion/PieceMotionPanel.tsx:PieceMotionPanel`, `src/panels/motion/CameraCaptureControl.tsx:CameraCaptureControl`.

Recommended primitive for the first mockup: `SegmentedField`.
