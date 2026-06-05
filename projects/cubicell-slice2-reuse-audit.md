# Cubicell Slice 2 reuse and vocabulary audit

Branch: `feat/transitions-ux` at `4832eadaf80863dff03d1b1224c9b6609d562179`.

Repository state was clean before and after the audit. This report is source based except where a probe is explicitly named.

## Verdict

The most consequential finding is confirmed: `MOVING` is false vocabulary for the class it labels. `src/evaluation/sceneMorph.ts:prepareSceneMorphTopology` places a retained cube in `changedCells` for color, opacity, edge state, face visibility, size, visibility, coordinate, offset, rotation, or scale differences. A direct one cube probe changed color, opacity, edge thickness, face visibility, and size independently. Every case returned `changedCount: 1` while placement remained equal. `CHANGING` describes the current classifier. `MOVING` does not.

The strongest reuse constraint is also clear. The arrangement control and the CUBES class selector both belong on `src/panels/SegmentedField.tsx:SegmentedField`, backed by `src/components/ui/segmented/Segmented.tsx:Segmented`. Counts fit the existing string label. Empty options need one generic `dimmed` extension to `Segmented`. A new tab component, count badge, or local empty option style would create a parallel implementation.

## 1. Vocabulary inventory

### Existing claims

| Word | Status | Owning evidence | Consequence |
|---|---|---|---|
| `frame` | Taken in several senses | `src/domain/scene.ts:CubicellScene.frameId`, `src/domain/workbench.ts:GridLock.frameId`, `src/camera/cameraDriverTypes.ts:CameraTrackFrame` | A FRAME control collides with coordinate frame identity and rendered camera frame vocabulary. Calling the control ARRANGEMENT avoids that ambiguity. |
| `glide` | Taken in two different senses | `src/domain/morphSettings.ts:MorphSettings.glide` owns retained changed cube motion. `src/config/cubicellConfig.ts:InputFeelPreferences` owns `glideMoveWorldUnitsPerSecond`, `glideZoomFactorPerSecond`, and `glideZoomMinWorldUnitsPerSecond`. `src/interaction/authority.ts:PoseMode` also contains `glide`. | The claim is correct with one qualification: there is no literal `preferences.glide` field. Three persisted preference fields carry the prefix. A new GLIDE label would collide with cube class motion and camera input motion. |
| `align` | Taken | `src/domain/grid.ts:GridFormat.align`, `src/domain/grid.ts:GridAlign` | This is grid format state, including the value `center`. |
| `overflow` | Taken | `src/domain/grid.ts:GridFormat.overflow`, `src/domain/grid.ts:GridOverflow` | This is grid format state with `allow`, `clamp`, and `hide`. |
| `cut` | Taken in several transition senses | `src/domain/score.ts:TransitionMode`, `src/domain/cameraTrack.ts:CameraPosePath`, `src/domain/cubeEdgeState.ts:CubeEdgeStateMorphChannel` | CUT already means a whole scene transition mode, a camera pose path, and a discrete edge channel. It is especially unsafe as a synonym for an arrangement mode. |
| `arrangement` | Taken in the intended sense | `src/evaluation/sceneMorph.ts:SceneMorphTopology.arrangement`, `src/evaluation/scoreAt.ts:Moment.arrangementOffset`, `src/evaluation/sceneMorph.ts:resolveEditorArrangementProgress` | Slice 1 made ARRANGEMENT the exact implementation term for resolved endpoint alignment and its crossed transient offset. This is the clean label for the new control. |

### Candidate words

`TAKEN, DIFFERENT` is the dangerous class. These words already teach another product meaning.

| Candidate | Classification | Owning evidence | Audit finding |
|---|---|---|---|
| `snap` | **TAKEN, DIFFERENT** | `src/domain/cubeOperations.ts:CubeOperation` has `snap-cube-home`; `src/panels/CubeSection.tsx:CubeSection` shows `Snap home`. | Existing SNAP returns a cube offset to home. An arrangement SNAP would mean temporal discontinuity. |
| `ease` | **TAKEN, DIFFERENT** | `src/domain/cameraTrack.ts:PoseSegment.ease`; `src/domain/morphSettings.ts:ClassMotion.easing`; `src/panels/motion/MorphInspector.tsx:MorphInspector` shows EASING. | EASE already names a curve choice. Using it as a peer mode beside SNAP and HOLD conflates mode with curve. |
| `hold` | **TAKEN, DIFFERENT** | `src/domain/score.ts:AssemblyExit.holdMs`; `src/interaction/commands/registry.ts:CommandRepeat`; `src/panels/AssemblyControls.tsx:AssemblyExitFields` shows `Hold ms`. | HOLD already means an assembly pause and sustained input ownership. An arrangement HOLD adds a third meaning. |
| `settle` | **TAKEN, DIFFERENT** | `src/domain/score.ts:EasingId`; `src/panels/motion/motionOptions.ts:easingOptions` shows `Settle`; `src/export/streamRecorder.ts:settle` owns async completion. | SETTLE is already a visible easing and an internal completion verb. It cannot safely name a separate arrangement behavior. |
| `drift` | Free in API and visible copy | Exact source hits occur only in comments inside `src/panels/motion/PieceMotionPanel.tsx:PieceMotionPanel`, `src/panels/motion/PieceStateStrip.tsx:PieceStateStrip`, and invariant comments. | Available, though comments already use live drift for unsaved State divergence. That latent meaning should be considered before adoption. |
| `anchor` | **TAKEN, DIFFERENT** | `src/domain/cube.ts:CubeResizeAnchor`, `src/domain/relativeOrder.ts:RelativeOrderAnchor`, `src/domain/faceSelectionQuery.ts:FaceSelectionAnchor`, `src/domain/edgeSelectionQuery.ts:EdgeSelectionAnchor`; `src/panels/CubeSection.tsx:CubeSection` exposes resize anchor copy. | ANCHOR already covers resize origin, ordered insertion, and Selector working sets. |
| `centre` | Free exact spelling, unsafe vocabulary fork | `src/domain/grid.ts:GridAlign` and `src/domain/cube.ts:CubeResizeAnchor` both use the American value `center`. | CENTRE has zero exact source hits. Introducing it would split spelling for an existing concept. |
| `offset` | Taken in the same spatial family | `src/domain/cube.ts:CubePlacement.offset`, `src/editor/controlBindings.ts:controlBindingList` shows `Offset X/Y/Z`, `src/evaluation/scoreAt.ts:Moment.arrangementOffset`. | ARRANGEMENT OFFSET already exists as the transient value. OFFSET is accurate but too broad for a mode name. |
| `place` | **TAKEN, DIFFERENT** | `src/domain/cubeOperations.ts:CubeOperation` has `place-cubes`; `src/app/useSceneOperations.ts:useSceneOperations` authors it. | PLACE is an edit command that creates or reveals cubes. |
| `shift` | **TAKEN, DIFFERENT** | `src/editor/affordances.ts:getCombineModeForModifiers` owns Shift selection algebra; `src/editor/keyboard/keymap.ts:getKeyboardShortcutCommandId` owns Shift chords; `src/scene/colorSpace.ts:shiftLightnessForContrast` owns color shift. | SHIFT is already a keyboard modifier and a color operation. |
| `follow` | Free in runtime API and visible copy | The only exact TypeScript hit is a `follow-up snapshot` comment in `src/panels/motion/PieceMotionPanel.tsx:PieceMotionPanel`. | Available in the inspected runtime and panel surface. No behavior owner exists. |
| `keep` | Free as product vocabulary | Exact source hits are generic comments. No type, field, command, or visible control owns it. | Available, but too generic to communicate arrangement behavior without supporting copy. |
| `lock` | **TAKEN, DIFFERENT** | `src/domain/workbench.ts:GridLock`; `src/domain/structureOperations.ts:StructureDocumentOperation` has `set-grid-lock`; `src/domain/documentRestoreOperations.ts:DocumentRestoreOperation` has `restore-grid-lock`. | LOCK already means a durable grid frame constraint. An arrangement LOCK would collide directly with grid lineage. |
| `pin` | Free | Exact TypeScript and TSX search returned zero hits. | Available. |
| `stay` | Free as product vocabulary | Exact hits are generic comments only. No type, field, command, or visible control owns it. | Available. |
| `cross` | Taken in the arrangement stem and vector math | `tests/sceneMorph.test.ts:arrangement crossing` names the Slice 1 behavior; `src/evaluation/scoreAt.ts:Moment.arrangementOffset` documents a crossed arrangement; `src/domain/cameraTrack.ts:cross` is the vector helper. | CROSS matches Slice 1 language, while the same token also means vector cross product internally. The user facing collision is low. |
| `carry` | Free as product vocabulary | Exact hits are explanatory comments only. No type, field, command, or visible control owns it. | Available. |

### Loudest collisions

1. FRAME collides with `frameId`, grid lock identity, and camera frame ownership.
2. SNAP, EASE, HOLD, SETTLE, ANCHOR, SHIFT, and LOCK are all taken in different senses.
3. GLIDE is already split between retained changed cube motion and held camera motion.
4. CENTRE is technically free and would still create a spelling fork with the existing `center` unions.

## 2. Control primitive reuse

| Slice 2 UI | Existing primitive | Evidence and smallest binding |
|---|---|---|
| Arrangement control | `src/panels/SegmentedField.tsx:SegmentedField` | This is the existing labeled option control used by `src/panels/motion/MorphInspector.tsx:MorphInspector` for CUBES, ORDER, and EASING. Add the arrangement options through the same field. |
| CUBES tabs | `src/panels/SegmentedField.tsx:SegmentedField` backed by `src/components/ui/segmented/Segmented.tsx:Segmented` | The control already exists in the exact panel and already owns the boxed option treatment. Preserve it. |
| Counts in tab labels | `src/components/ui/segmented/Segmented.tsx:SegmentedProps.options.label` | Labels are strings. Build `Entering ${count}`, `Leaving ${count}`, and the renamed changed class label directly. `src/panels/SelectionEditTargetToggle.tsx:SelectionEditTargetToggle` already uses a dynamic `Set ${setSize}` segmented label. No badge primitive is needed. |
| Empty but editable tabs | Extend `src/components/ui/segmented/Segmented.tsx:Segmented` | Add `dimmed?: boolean` to the shared option type, emit a `data-dimmed` attribute, and style the existing button with `opacity: var(--cc-alpha-muted)` in `src/components/ui/segmented/segmented.css:.cc-segmented-option`. Keep the button enabled so click and focus behavior remain intact. |

### Disabled state verification

The prior claim still holds.

| Primitive | Source verified behavior |
|---|---|
| `src/components/ui/button/Button.tsx:Button` | Native button props include `disabled`. `src/components/ui/button/button.css:.cc-button:disabled` applies `var(--cc-alpha-muted)`. |
| `src/panels/PanelTabs.tsx:PanelTabs` | Each tab receives native `disabled` from `disabledTabs`. `src/panels/panel-tabs.css:.cc-panel-tab:disabled` applies the same muted alpha. |
| `src/panels/SpatialBuilderControls.tsx:SpatialOptionGroup` | `SpatialOption.disabled` flows to `Button.disabled`, so it reuses the Button behavior and visual. |
| `src/components/ui/segmented/Segmented.tsx:Segmented` | Options expose only `label` and `value`. There is no disabled or dimmed state. |

Native `disabled` would violate the Slice 2 requirement because an empty class must remain editable. The existing disabled implementations provide the visual token only. `Segmented` needs a visual `dimmed` state with normal button semantics. `aria-disabled` would also communicate the wrong interaction contract.

`src/panels/SegmentedField.tsx:SegmentedField` currently repeats the `{ label, value }` option shape. When the core option gains `dimmed`, export one `SegmentedOption` type from `src/components/ui/segmented/Segmented.tsx` and consume it in `SegmentedField`. Extending both anonymous shapes independently would violate DRY.

### Existing tab treatments

1. Underline tabs are owned by `src/panels/PanelTabs.tsx:PanelTabs` and `src/panels/panel-tabs.css:.cc-panel-tab`. `src/panels/SelectorPanel.tsx:SelectorPanelHeader` uses them for SELECTION and MODIFY.
2. Boxed option tabs are owned by `src/components/ui/segmented/Segmented.tsx:Segmented`. `src/panels/CubeSection.tsx:CubePanelTabs` uses them for DIMENSIONS and STYLE inside MODIFY. `src/panels/motion/MorphInspector.tsx:MorphInspector` already uses the same treatment for CUBES.

The CUBES control already belongs to the boxed treatment. Converting it to `PanelTabs` or adding a third tab component would be a parallel implementation.

## 3. Data availability for class counts

The data path is local. It needs no store field, selector, command, persistence field, or transport message.

1. `src/panels/motion/usePieceMotionModel.ts:usePieceMotionModel` returns `workbench` and the ordered `sequence` of States.
2. `src/domain/stateTransition.ts:repairStructureStateTransitionTrack` builds keyframes in `asset.stateIds` order. `src/domain/structureSequenceOperations.ts:commitStructureSequence` writes `asset.stateIds` from moved keyframes. Therefore `sequence[index]` and `sequence[index + 1]` are the endpoints for transition index `index`.
3. `src/domain/workbench.ts:getStateScene` rebuilds the scene for either State.
4. `src/evaluation/sceneMorph.ts:prepareSceneMorphTopology` returns the exact three arrays already consumed by playback: `addedCells`, `removedCells`, and `changedCells`.

The component derivation belongs in `src/panels/motion/MotionInspector.tsx:TransitionInspector`, which owns the gap index and endpoint context. `src/panels/motion/MorphInspector.tsx:MorphInspector` should remain presentational and receive counts.

```ts
const classCounts = useMemo(() => {
  const from = sequence[index];
  const to = sequence[index + 1];
  if (!from || !to) return { arrive: 0, depart: 0, glide: 0 };

  const topology = prepareSceneMorphTopology(
    getStateScene(workbench, from),
    getStateScene(workbench, to),
  );
  return {
    arrive: topology.addedCells.length,
    depart: topology.removedCells.length,
    glide: topology.changedCells.length,
  };
}, [index, sequence, workbench]);
```

This is cheap in architecture and linear in scene size. `prepareSceneMorphTopology` maps both endpoint cell sets and compares all six faces and twelve edges of retained cells. The dependency set above also recomputes after any Workbench edit, including transition setting edits whose endpoint poses did not change. That performance cost is explicitly unverified in the browser. It is acceptable for the smallest Slice 2 diff, while it should not be described as constant time or free.

Auto selection belongs beside `src/panels/motion/MotionInspector.tsx:TransitionInspector.selectedClass`. Select the first positive count in `morphClassIds` order when the inspected gap opens or changes. Preserve `arrive` when all counts are zero. No new session or persisted state is required.

## 4. `changedCells` falsification probe

Claim tested: appearance only changes file a retained cube under the current MOVING tab.

Probe method: a Vite SSR loader imported the production `src/evaluation/sceneMorph.ts:prepareSceneMorphTopology`. It created one source cube and five destination variants. Each variant changed exactly one property family and retained the same cube id and placement.

| Variant | `changedCells.length` | Placement equal |
|---|---:|---|
| Face color | 1 | yes |
| Face opacity | 1 | yes |
| Edge thickness | 1 | yes |
| Face visibility | 1 | yes |
| Cube size | 1 | yes |

Probe output named `probe-cube` in `changedIds` for all five cases. The claim is true.

The source explains the result. `src/evaluation/sceneMorph.ts:prepareSceneMorphTopology` checks visibility, offset, rotation, scale, coordinate, and size directly. It then uses `src/domain/cubeEdgeState.ts:cubeEdgeStateOwner.getMorphChanges` for edge color, opacity, thickness, and visibility, followed by face color, opacity, and visibility checks.

Current label ownership is `src/panels/motion/MorphInspector.tsx:morphClassLabels`, where `glide` renders as `Moving`. The classifier means retained and changed. A recolored cube changes and does not move. Renaming this tab is supported by production behavior and probe evidence.

## 5. Smallest Slice 2 diff by symbol

### Required owners

| File and symbol | Smallest responsibility |
|---|---|
| `src/domain/morphSettings.ts:MorphSettings` | Own the arrangement mode if the control authors a stored value. Add its default and normalization through `defaultMorphSettings` and `patchMorphSettings`. Avoid a panel local mode type. |
| `src/evaluation/sceneMorph.ts:resolveEditorArrangementProgress` | Resolve the authored arrangement mode into the explicit progress already consumed by `sampleSceneMorph`. Keep interpolation in the existing evaluation seam. |
| `src/evaluation/pieceAt.ts:resolvePieceSample` | Pass the transition arrangement setting to the shared resolver for piece playback. |
| `src/transport/stagedScene.ts:resolveStageSource` | Pass the same setting for State to live comparison. This is the other production caller. |
| `src/state/scoreValidation.ts:isMorphSettings` | Admit only the exact new persisted field and mode values. The decoder is strict. |
| `src/state/authoredOperationValidation/structureSequence.ts:isMorphSettingsPatch` | Admit the same field at the document operation boundary. |
| `src/components/ui/segmented/Segmented.tsx:Segmented` | Add the one generic `dimmed` option state and export its option type. |
| `src/components/ui/segmented/segmented.css:.cc-segmented-option` | Reuse `var(--cc-alpha-muted)` for `data-dimmed` while preserving pointer and focus behavior. |
| `src/panels/SegmentedField.tsx:SegmentedField` | Reuse the exported shared option type so `dimmed` crosses the wrapper without a second declaration. |
| `src/panels/motion/MotionInspector.tsx:TransitionInspector` | Derive endpoint topology counts, own first nonempty class selection, and pass arrangement plus counts into the presentational inspector. |
| `src/panels/motion/MorphInspector.tsx:MorphInspector` | Render the arrangement `SegmentedField`, dynamic count labels, empty option dimming, accurate class copy, and the renamed `glide` label. |
| `tests/sceneMorph.test.ts:arrangement crossing` | Prove each authored arrangement mode at start, interior sample, and exact endpoint. Preserve exact endpoint identity. |
| `tests/morphInspector.test.tsx:MorphInspector` | Prove count labels, empty option dimming, empty option clickability, arrangement patches, and first nonempty selection through the container test seam. |
| Persistence and operation boundary tests using `src/state/scoreValidation.ts:isMorphSettings` and `src/state/authoredOperationValidation/structureSequence.ts:isStructureSequenceOperation` | Prove accepted values and rejection of unknown or invalid values. |

All listed production files remain below the 700 line threshold. `src/evaluation/sceneMorph.ts` is 502 lines and is the largest proposed production touch. `src/panels/motion/MorphInspector.tsx:MorphInspector` is well below the function threshold.

### Parallel implementations to reject

1. A new arrangement interpolation function in the panel would duplicate `resolveEditorArrangementProgress`.
2. A second endpoint diff or count classifier would duplicate `prepareSceneMorphTopology`.
3. A new tab component would duplicate `Segmented` or `PanelTabs`.
4. A local empty option CSS class in `MorphInspector` would duplicate the shared muted visual and leave the next `Segmented` consumer without the capability.
5. A local arrangement mode union in the panel would duplicate `MorphSettings` and drift from persistence validation.
6. Direct pose reconstruction in the panel would duplicate `getStateScene`.
7. Native `disabled` on empty class options would change the required behavior and prevent editing stored values.

## Verification

Direct behavioral probe: production `prepareSceneMorphTopology` loaded through Vite SSR, five isolated appearance and size variants, all classified as changed with equal placement.

Targeted tests:

```text
pnpm exec vitest run tests/sceneMorph.test.ts tests/morphInspector.test.tsx
Test Files  2 passed (2)
Tests       25 passed (25)
```

Repository evidence searches covered `src/domain`, `src/evaluation`, `src/panels`, `src/components`, `src/editor`, `src/state`, `src/camera`, and TSX user facing strings. No browser interaction was run. Dimmed option behavior remains a proposed change, so its runtime behavior is explicitly unverified until Slice 2 implements and tests it.
