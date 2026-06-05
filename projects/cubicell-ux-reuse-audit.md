# Cubicell UX reuse audit

Source verified against `/Users/alphab/Dev/LLM/DEV/helioy/cubicell`, `main` at
`6b92c60303b5a2a979bed47af2f87b1efaf147f8`. I reread
`~/.mdx/projects/cubicell-scout-transitions-authoring.md` and inspected all
three supplied screenshots.

## Primary finding

The clearest route to a forbidden third idiom is the proposed count treatment
inside the **Cubes** segmented property. A local count badge, orange Selector
styling, a `PanelTabs` treatment, or Morph Inspector only disabled CSS would
create a third choice language. Keep **Cubes** as the existing property
`SegmentedField`, render the count as part of each option label, and extend the
shared `Segmented` option contract once with native disabled behavior.

The screenshots confirm these boundaries:

* White fill names a set property value in Transition and Modify.
* Orange outline names selection scope in Selector.
* Unavailable selection options remain visible and dimmed through native
  disabled buttons.
* Underlined `PanelTabs` and boxed segmented property choices are the two
  existing treatments. None of the six proposals needs another one.

## Six item reuse map

### 1. Frame policy

**Existing UI component:**
`src/panels/SegmentedField.tsx:SegmentedField`, backed by
`src/components/ui/segmented/Segmented.tsx:Segmented`. A small durable enum such
as Snap, Ease, Hold, or Follow fits the same labelled property control already
used for Cubes, Order, and Easing. `PanelTabs` would give a property the wrong
panel navigation semantics. `Switch` would collapse a three or four value enum
into a binary idiom. `ControlBindingField` fits only after a real
`ControlBinding` owns the field schema and command.

**Existing domain behavior, but no Frame field:**
`src/evaluation/sceneMorph.ts:sampleSceneMorph` already derives grid progress
from the Moving class easing and quantization.
`src/evaluation/sceneMorph.ts:interpolateGridState` already interpolates grid
origin, cell size, gap, and gap overrides, then switches discrete grid fields
at `MorphSettings.cutAt`. `src/domain/score.ts:Transition` has only `mode` and
`settings`; `src/domain/morphSettings.ts:MorphSettings` has no Frame policy.
No gap wide Snap, Hold, or Follow policy was found.

**Searches run:** `rg` across `src/domain`, `src/evaluation`,
`src/panels/motion`, and `src/transport` for `frame`, `extent`, `bounds`,
`layout`, `SNAP`, `EASE`, `HOLD`, `FOLLOW`, and the complete Transition and
Morph Settings definitions. Camera **Frame All** results are unrelated view
commands.

**DRY consequence:** Ease already describes the current layout path. A new
Frame evaluator would duplicate `interpolateGridState`. Snap must also be
distinguished explicitly from the existing whole scene `Transition.mode =
"cut"`. The domain decision must precede the control.

### 2. Counts on Cubes choices

**Existing UI component:**
`src/panels/SegmentedField.tsx:SegmentedField` and
`src/components/ui/segmented/Segmented.tsx:Segmented`. The count belongs in the
existing option label, for example `Entering 2`. `PanelTabs` is panel
navigation. `src/panels/SpatialBuilderControls.tsx:SpatialOptionGroup` is the
orange selection scope idiom and must not be reused here.

**Existing count source:**
`src/evaluation/sceneMorph.ts:prepareSceneMorphTopology` returns
`addedCells`, `removedCells`, and `changedCells`. The exact mapping is Entering
to `addedCells.length`, Leaving to `removedCells.length`, and Moving to
`changedCells.length`. Changed includes pose, size, visibility, face, and edge
changes, so a visible label that claims literal movement is narrower than the
classifier.

**Missing shared seam:** `Segmented` options currently expose only `label` and
`value`. They have no `disabled` field, while
`src/components/ui/button/Button.tsx:Button`,
`src/panels/PanelTabs.tsx:PanelTabs`, and
`src/panels/SpatialBuilderControls.tsx:SpatialOptionGroup` already use native
disabled buttons with the shared muted alpha. Extend `Segmented` once. Do not
add Morph specific disabled markup or CSS.

### 3. Context sentence

**Existing component:** `src/panels/motion/MorphInspector.tsx:MorphInspector`
already renders `morphClassHints` inside `cc-dock-section-copy` using
`src/components/ui/label/Label.tsx:Label` with the muted tone. Extend that one
sentence in place. A summary card, badge, highlighted count, or second help
block would be a new affordance.

**Missing data:** no Frame policy or Frame analysis exists, so a sentence such
as “Frame moves 0.75 on x, carrying 3 cubes” cannot yet name a source of truth.
Once the domain meaning is settled, derive the sentence from the same endpoint
analysis used by the evaluator. Do not add an inspector only extent helper.

### 4. Transition mode

**Existing component:** `src/panels/SegmentedField.tsx:SegmentedField` is the
local fit for Auto and Cut. `Switch` expresses a boolean, while mode is the
existing `src/domain/score.ts:TransitionMode` enum.

**Existing write and evaluation path:**
`src/domain/structureSequenceOperations.ts:StructureSequenceDocumentOperation`
already permits `mode` on `patch-transition`.
`src/domain/stateTransition.ts:patchTransition` applies it, and
`src/domain/stateTransition.ts:resolveTransitionKind` plus
`src/evaluation/sceneTransition.ts:sampleSceneTransition` execute it.
`src/panels/motion/MotionInspector.tsx:TransitionInspector` already owns the
gap keyframe and the one `patch-transition` dispatch. Broaden that existing
dispatch seam to carry mode. A second command or writer would duplicate a
complete capability.

### 5. Transition filmstrip summary

**Existing components:**
`src/panels/motion/PieceMotionPanel.tsx:PieceMotionPanel` creates
`stripTransitions`.
`src/panels/motion/PieceStateStrip.tsx:PieceStripTransition` defines the card
summary, and `src/panels/motion/PieceStateStrip.tsx:PieceStateStrip` renders its
two rows and duration value.

Replace the current Entering only `order` and `easing` data with one truthful
gap summary through those same symbols. Reuse the existing card rows and value
typography. Chips, badges, icons, a count color, or a mini segmented control
would introduce a new card idiom. Derive population facts with
`prepareSceneMorphTopology`; do not create a filmstrip classifier.

### 6. State thumbnail from captured view

**Existing components and path:**

* `src/panels/motion/PieceStateStrip.tsx:PieceStripState` and
  `src/panels/motion/PieceStateStrip.tsx:PieceStateStrip` own the State tile and
  thumbnail slot.
* `src/studios/editor/ThumbnailCapabilitySlot.tsx:ThumbnailCardSlot` turns the
  State into a thumbnail request.
* `src/capabilities/thumbnails/ThumbnailCapability.tsx:ThumbnailRenderRequest`
  and `src/capabilities/thumbnails/CapabilityStateThumbnail.tsx:StateThumbnail`
  own loading, failure, object URL lifetime, and image rendering.
* `src/thumbnail/thumbnailCache.ts:createStateThumbnailCache` caches by Pose
  identity.
* `src/thumbnail/thumbnailView.ts:createOrthographicThumbnailView` and
  `src/thumbnail/thumbnailRenderer.ts:renderThumbnail` force an orthographic
  axis view.

**Captured view support:** none found in the thumbnail path. Searches for
`StateCameraView`, `state.view`, `cameraView`, `ThumbnailRenderRequest`, and
every `renderThumbnail` caller found view consumption only in camera playback,
State alignment, capture, and remove. The thumbnail request carries Pose and an
optional axis, never `State.view`.

This is a reuse extension, not a second thumbnail system. Thread the existing
`StateCameraView` through `PieceStripState`, `ThumbnailCardSlot`, and
`ThumbnailRenderRequest`; extend the existing renderer and cache. Pose only
cache identity cannot refresh on recapture or remove, so the cache key and the
`StateThumbnail` effect dependency must include the captured view state.
Perspective capture also requires the existing renderer to accept the captured
projection rather than forcing `OrthographicCamera`. Keep the same tile image,
loading, and failure chrome. A camera badge, overlay, or alternate tile frame
would create another visual treatment without serving the requested behavior.

## Every third idiom risk

1. **Cubes counts:** bespoke badges, superscript counts, count color, local
   disabled classes, hidden zero choices, click no ops, or orange selection
   styling.
2. **Frame:** rendering a new tab row, pill set, dropdown, or Selector style
   option grid instead of `SegmentedField`.
3. **Mode:** a custom Auto or Cut toggle or `Switch` beside a segmented Frame
   row. It should use the same property choice primitive.
4. **Context:** a new summary banner, metric row, or emphasized inline count
   beside the existing muted sentence.
5. **Filmstrip:** chips, status dots, count colors, or miniature controls inside
   a card that is currently a selector and text summary.
6. **Thumbnail:** a captured view badge, inset preview, or second frame around
   the same State card. The requested distinction belongs in image content.
7. **Unavailable state:** a Morph only opacity value or disabled convention.
   Native disabled behavior must be added to the shared segmented primitive and
   use the existing muted alpha token.
8. **Selected empty class:** `TransitionInspector` defaults to Entering. If
   Entering is empty, blindly disabling it leaves the selected control disabled
   while class controls still edit an inapplicable class. The implementation
   needs one shared rule for choosing the first applicable class. An all zero
   gap needs an explicit unavailable class section. Solving either with a new
   visual state would deepen the divergence.

## Range extraction

None of the six proposals needs a range input. Frame and mode are discrete
properties, counts and context are text, the filmstrip is a summary, and the
thumbnail is an image. Leave
`src/panels/motion/TransportPlayhead.tsx:TransportPlayhead` and
`src/panels/motion/MotionInspector.tsx:StateComparisonControls` unchanged for
this work.

If a later Frame design introduces continuous scrubbing, first extract one
shared slider primitive under `src/components/ui`. It should own the native
range input, accessible name, min, max, step, value, change conversion, and
shared range styling. Migrate both existing raw range consumers to it before a
third use. Adding another raw `<input type="range">` is duplication.

## Smallest correct count diff by symbol

1. `src/components/ui/segmented/Segmented.tsx:Segmented`: export one shared
   option type with `disabled?: boolean`, accept it, and forward native
   `disabled` to the option button.
2. `src/panels/SegmentedField.tsx:SegmentedField`: consume that exported option
   type instead of redeclaring the `label` and `value` shape. Forward options
   unchanged.
3. `src/components/ui/segmented/segmented.css:.cc-segmented-option`: add the
   shared dimmed unavailable treatment and exclude disabled options from hover.
   Retain the existing white active property treatment and shared muted alpha.
4. `src/panels/motion/MotionInspector.tsx:TransitionInspector`: read
   `workbench` and `sequence` from the existing `usePieceMotionModel`, resolve
   the two endpoint scenes with `src/domain/workbench.ts:getStateScene`, call
   `prepareSceneMorphTopology` once for the selected gap, map its three arrays
   to Morph class counts, and pass them to `MorphInspector`. Add no store field,
   prop chain, command, or new classifier.
5. `src/panels/motion/MotionInspector.tsx:TransitionInspector`: when the
   selected class has count zero, select the first nonempty class through the
   existing `selectedClass` state. Define the all zero behavior before coding
   so the component does not expose editable controls behind a disabled active
   option.
6. `src/panels/motion/MorphInspector.tsx:MorphInspectorProps`: accept the typed
   counts keyed by the existing `MorphClassId`.
7. `src/panels/motion/MorphInspector.tsx:MorphInspector`: derive each visible
   option label from `morphClassLabels` plus its count and mark zero count
   options disabled. Keep `SegmentedField`, `morphClassHints`, and every class
   edit path intact.
8. `tests/morphInspector.test.tsx:MorphInspector`: prove the three accessible
   labels carry live counts, zero choices are disabled and still present, a
   nonempty choice still calls `onClassChange`, and no orange Selector class is
   introduced. Add focused Transition Inspector proof at the existing
   observable dispatch seam when that host receives the topology derivation.

## Count reachability

`src/evaluation/sceneMorph.ts:prepareSceneMorphTopology` is the existing and
authoritative added, removed, and changed classifier.
`src/panels/motion/usePieceMotionModel.ts:usePieceMotionModel` already returns
the selected gap's ordered `sequence` and the `workbench`.
`src/domain/workbench.ts:getStateScene` already reconstructs each State scene
with its correct score. The inspector therefore needs only local pure
derivation and imports. No new model plumbing is required.

`PieceMotionPanel` already receives the same `workbench` and `sequence` from
the same hook, so the filmstrip can call the same classifier. The classifier,
class mapping, and terminology must remain identical across inspector and card.

## Duplication defects to prevent

* A new gap diff or population helper duplicates
  `prepareSceneMorphTopology`.
* A second grid or extent interpolator duplicates `interpolateGridState`.
* An unqualified Frame Ease duplicates the current Moving easing path.
* An unqualified Frame Snap can duplicate `Transition.mode = "cut"`.
* A mode command or store writer duplicates the existing `patch-transition`
  operation.
* A local segmented wrapper duplicates `SegmentedField`.
* Morph specific disabled CSS duplicates the shared control disabled contract.
* Selector orange styling assigns selection semantics to a property.
* A filmstrip only classifier duplicates the evaluator's topology.
* A second dock thumbnail renderer, cache, loading state, or fallback duplicates
  the thumbnail capability.
* A third raw range input duplicates the two range consumers already awaiting
  extraction.

## Binding verdict

* **SegmentedField and Segmented:** Frame, Cubes counts, and Transition mode.
* **ScrubField:** existing duration, scene switch, stagger, and steps only.
* **NumberStepper:** none of the six proposals.
* **Switch:** none of the six proposals.
* **PanelTabs:** none of the six proposals.
* **ControlBindingField:** none until a durable control binding owns a proposed
  field.
* **Button:** existing camera capture, recapture, and remove actions only.
* **Thumbnail capability:** captured view rendering through the existing State
  thumbnail path.
