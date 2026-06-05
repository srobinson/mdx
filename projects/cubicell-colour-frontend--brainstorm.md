# Cubicell Colour Frontend Brainstorm

Scope: clean `main` at `72934382262c5d760b0329d9fb52f7d864cd6443`. Branch `feat/domain-occlusion` is unmerged at `e1f8eed`. No Cubicell colour design specification was found under `~/.mdx/design/`.

## Control Surface Inventory

| Primitive | Current owner | Covers | Missing for colour |
| --- | --- | --- | --- |
| ScrubField | `src/components/ui/scrub-field/ScrubField.tsx:ScrubField` | Numeric scrub, wheel, arrows, typed entry, formatting, disabled state, authored gesture lifecycle | No visual track, hue geometry, colour preview, or string value |
| Segmented | `src/components/ui/segmented/Segmented.tsx:Segmented` | Compact single choice enum with pressed state, focus and hover preview, disabled state | Options carry text labels only. No swatch rendering, wrapping palette grid, or mixed value presentation |
| Switch | `src/components/ui/switch/Switch.tsx:Switch` | Boolean state with native button semantics and neutral or polarity tone | No colour value |
| NumberStepper | `src/components/ui/number-stepper/NumberStepper.tsx:NumberStepper` | Numeric increment, decrement, wheel, arrows, min and max | No free text or colour value |
| Button | `src/components/ui/button/Button.tsx:Button` | Native button attributes, five sizes, four variants, two weights | No colour specific selection or preview contract |
| Label | `src/components/ui/label/Label.tsx:Label` | Presentational text with size, tone, and weight | No field association or error contract |

The kit has no swatch, palette, text field, popover, dialog, slider track, hue dial, saturation plane, gradient stop editor, colour parser, or focus trap. `package.json:dependencies` has no colour picker package. The design system preview currently covers Button and Switch only through `src/design-system/DesignSystem.tsx:DesignSystem`.

Colour controls already exist as text enums. `src/editor/controlBindings.ts:ControlBindingId` includes `cube.color`, `face.color`, and `edge.color`. Their bindings expose Theme, Black, and White through the enum schema. `src/panels/ControlBindingField.tsx:ControlBindingField` renders every enum with Segmented.

The existing panel row path is sufficient for solid colour:

1. `src/panels/CubeSection.tsx:CubeSection` mounts `ControlBindingField` for `cube.color` in the Style tab.
2. `src/panels/panelDefinitions.ts:faceBindingIds` and `edgeBindingIds` register the part colour rows.
3. `src/panels/PartSection.tsx:PartSection` maps those ids to `ControlBindingField`.
4. `src/panels/Inspector.tsx:Inspector` selects CubeSection, FaceSection, or EdgeSection from the current pick mode.

`src/panels/SceneSection.tsx:SceneSection` shows the standard row anatomy: `cc-scrub-field`, a label, and a primitive. It is registered by `src/panels/LeftRail.tsx:LeftRail` under the Scene tab. A part colour control does not need a new panel section.

A control writes authored state through `src/panels/useControlBinding.ts:useControlBinding`: read the working scene, call the binding's `createCommand`, then dispatch through `useEditorCommandDispatch`. `src/editor/commands.ts:createSceneEditorCommand` carries the scene operation. Existing writers are `set-cube-color`, `set-face-state`, and `set-edge-state`. `src/domain/cubeCellOperations.ts:applyCubeOperationToCell` applies the cube colour to all faces and edges. No new store or operation kind is required for one solid colour per part.

## Cost Table

Rough size is an estimate of changed source lines, then test lines. It excludes design iteration and visual tuning.

| Candidate | Existing owner or new owner | UI size | Domain and render size | Reality check |
| --- | --- | ---: | ---: | --- |
| Current Theme, Black, White choice | Existing ControlBindingField and Segmented | 0 | 0 | Already live for cube, face, and edge |
| Visual palette for the current three values | Extend Segmented option rendering, keep text as the accessible name | 40 to 90 + 50 to 100 tests | 0 | Smallest useful visual upgrade |
| Fixed larger palette | Same visual palette plus `partColorOptions` | 50 to 110 + 60 to 120 tests | 40 to 100 + validation tests | Adding persisted tokens changes the compact colour index contract, so version bump and reset apply |
| Native colour input wrapper | New `ColorField` and a `color` ControlValueSchema branch | 80 to 150 + 80 to 140 tests | 120 to 220 + tests | Low code cost, but the opened picker is browser owned and visually inconsistent |
| Custom saturation plane and hue slider | New `ColorField` composed from new pointer controls | 250 to 450 + 180 to 300 tests | Same solid colour domain cost | No reusable pointer surface or popup primitive exists |
| Hue dial | New radial input | 180 to 300 + 120 to 220 tests | Same solid colour domain cost | Hue alone cannot select saturation and lightness, so it is an accessory rather than a complete picker |
| Two stop ramp over selection order | Compose two ColorFields with existing Segmented or ScrubField where applicable | 80 to 160 + 100 to 160 tests after ColorField | 150 to 300 + tests | Needs an authored ordering rule. Rendering resolved solid colours per instance needs no shader change |
| Gradient stops within one face | New stop strip, drag model, stop editor, keyboard model, and ColorField | 350 to 650 + 250 to 450 tests | 400 to 800 + tests | Requires a new authored material shape, wire contract, incremental attribute path, and shader feature |
| Solid per instance render | Existing InstancedMesh colour path | 0 | 0 beyond widening colour resolution | Already one RGB value per instance |
| Composed shader feature owner | Generalize the unmerged shading injection pattern | 100 to 180 + 100 to 160 tests | Included | Useful only for colour that varies across one instance |

## Render Path Facts

`src/domain/cubeEdgeState.ts:cubePartColors` is `theme | black | white`. `src/domain/cube.ts:CubeFaceState` and `src/domain/cubeEdgeState.ts:CubeEdgeState` store one `CubePartColor` per face or edge.

`src/scene/cubeInstances.ts:createCubeCellInstances` copies each authored face or edge colour, optional colour tween, opacity, and matrix into a `CubeFaceInstance` or `CubeEdgeInstance`. Both satisfy `src/scene/instancedPartMeshCore.ts:InstancedPart`.

`src/scene/instancedPartMeshCore.ts:syncInstancedPartMesh` writes matrix, colour, and opacity for every occupied slot. `writeColor` calls `resolveInstanceColor`, then `InstancedMesh.setColorAt`. Three's standard instance colour path therefore carries one RGB value to MeshBasicMaterial per instance. The existing injected `instanceOpacity` attribute carries alpha separately.

`src/scene/colorSpace.ts:resolvePartColor` resolves Theme, Black, or White through `src/theme/scenePolarity.ts:resolveCubePartColor`. `resolveLerpedPartColor` already interpolates resolved endpoints in OKLab. A normalized solid RGB literal can reuse that path after the resolver accepts it.

Current main still changes the resolved RGB in `src/scene/instancedPartMeshCore.ts:resolveInstanceColor` using `cubeFaceLightnessDeltaById` or `edgeLightnessDelta`. A pure authored colour therefore does not remain pure on the workbench at this SHA. This is the direct collision with the rejected orientation ramp.

One instance colour cannot express a position varying gradient inside one face. That needs shader inputs, a texture lookup, or more geometry and draw groups. More material meshes are unnecessary for solid per part colour because instance colour already exists.

`src/scene/instanceSlotRegistry.ts:InstanceSlotAttribute` already contains `color`. `changedAttributes` marks it when the part colour or colour tween changes. Widening the existing solid colour value needs no new registry attribute. A new gradient or procedural colour field would need its own attribute name, equality check in `changedAttributes`, inclusion in `fullAttributes`, GPU write in `patchInstancedPartMesh`, and dirty range marking.

Widening `CubePartColor` touches these existing owners:

* Domain: `src/domain/cubeEdgeState.ts:CubePartColor`, `isCubePartColor`, and `cubeEdgeStateOwner`.
* Resolution: `src/theme/scenePolarity.ts:resolveCubePartColor`.
* UI: `src/editor/controlBindings.ts:ControlValueSchema` and the three existing colour bindings.
* Operations: the existing `CubeOperation` carriers remain valid after their value type widens.
* Validation: `src/state/authoredOperationValidation/scene.ts:isCubeOperation`, `isPartPatch`, and `src/state/workbenchValidation/pose.ts:isFaceState` all delegate to `isCubePartColor`. Edge state delegates to `cubeEdgeStateOwner.isState`.
* Persistence: `src/persistence/recordCodecs/compactPose.ts:encodeCell` stores face colours as indexes into `cubePartColors`; `cubeEdgeStateOwner` does the same for edges. Arbitrary colours need a new compact value shape or a pose palette table.
* Wire versions: `src/domain/authoredOperations.ts:authoredOperationSchemaVersion` is 4. `src/persistence/indexedDbSchema.ts:indexedDbProjectStorageVersion` is 9. `createIndexedDbProjectSchema` deletes every object store during upgrade, so a storage version bump performs the required reset.

A project palette has no current owner. A fixed application palette can remain in the control binding. An authored palette needs Project persistence and undo ownership. A preference palette would not travel with exported work and would make authored references dependent on local user state.

## Recommended Substrate

1. Keep the first colour model to one solid value per face or edge. Use the existing `color` field, commands, history, morph, instance slot, and GPU colour owners.
2. Preserve Theme as a semantic token. Add normalized six digit sRGB literals as value strings only after strict validation. String value equality preserves the existing Sets, comparisons, tween endpoints, and incremental colour check.
3. Put the visual control in the existing cube, face, and edge colour rows. Start with a swatch palette. Add a compact custom colour field only if arbitrary input is required by the owner.
4. Use native `instanceColor` for solid colours and for ramps materialized across separate instances. No custom shader is needed.
5. For a later gradient within one face, establish one composed shader feature owner. `feat/domain-occlusion:src/scene/instancedPartShading.ts:applyInstancedPartShading` proves the attribute plus `onBeforeCompile` path and composes its program cache key from enabled features. Extract that mechanism deliberately. Do not merge its occlusion fields or lightness model.
6. Include every enabled colour feature in `customProgramCacheKey`. `onBeforeCompile` is a single material callback, so opacity and future colour injection need one compositor.

## What I Would NOT Build And Why

* No lightness ramp or ambient occlusion. Both spend the authored lightness channel and have failed owner review.
* No new colour store or solid colour operation. Existing domain fields and operations already own the value and undo path.
* No material or mesh per palette colour. It would discard the existing instancing advantage.
* No hue dial as the first control. It is incomplete without saturation and lightness controls and has no reusable primitive here.
* No gradient stop editor before the owner defines whether the gradient runs across selected parts or within each face. Those choices have different state, ordering, persistence, and render contracts.
* No dependency on `feat/domain-occlusion`. It is unmerged, and its visual model was rejected. Only its composed shader injection pattern is reusable.
* No third party picker before measuring its bundle cost and auditing keyboard, focus, and panel fit. No such dependency exists today.

## Open Questions For The Owner

1. Is the first target a visual palette, arbitrary sRGB input, a ramp across selected cubes, or a gradient inside each face?
2. Should literal colours remain fixed when scene polarity changes, while Theme continues to invert?
3. Is a palette fixed by the application, authored per Project, or remembered as a user preference?
4. Should one cube colour continue to set all faces and edges, with face and edge overrides available through their existing panels?
5. Are pure black and pure white reserved exact endpoints that no workbench transform may alter?
6. Is six digit sRGB hex sufficient for v1? Opacity already has a separate authored field.
7. Should colour transitions continue to use the existing OKLab interpolation?
8. If a ramp spans selected parts, which existing order owns it: scene order, spatial axis, selection order, or score order?
9. Should the first custom input use a browser picker, or does the owner require a fully designed in panel picker?

## Consensus Round

### Positions

* **A: concession.** Keep `#050505` and `#ffffff` for neutral parts. An explicitly authored Accent part may move to the proposed rails. The visual report's stated 14.3:1 floor is enough contrast for this opt in channel, and refusing the concession leaves no useful chroma at the white pole.
* **B: edges.** Colour the seams first and leave the black and white face field exact. Edge colour remains a hard geometric seam while making the first experiment easy to attribute and reverse.
* **C: enum.** Add one `accent` role to `src/domain/cubeEdgeState.ts:cubePartColors` and resolve it through `src/theme/scenePolarity.ts:resolveCubePartColor`. This fits compact index persistence, existing Segmented controls, strict validation, and the current label based tween carrier. Freeform colour adds product incoherence and wire cost before it proves value.
* **D: authorship.** The user assigns Accent through the existing edge colour binding and selection scope. Coordinate and burial functions may become later presets or modifiers, but they must not replace the authored role.

### Product Ranking

1. **Accent Role.** It gives the editor a scarce, coherent, authored colour word that survives selection, persistence, undo, export, and later animation.
2. **Axis Ink.** It gives edge direction an immediate readable vocabulary while preserving pure faces, but automatic axis assignment must remain optional.
3. **Enclosure Chroma.** It moves a useful structural signal off lightness, but burial driven colour needs an explicit opt in boundary.
4. **Field Tint.** It can improve editor atmosphere safely, but it does not improve the exported composition.
5. **Facet Hue.** It preserves lightness better than #160, but still system paints authored faces by orientation.
6. **Axis Wash.** It produces range quickly, but a coordinate wash has the weakest connection to author intent and changes the whole composition at once.

**First slice: Accent Role on edges.** It lets an author add one coherent colour to selected seams without changing the pure black and white face field.

### Bounded Grooming

Ride along one consolidation: derive `src/editor/controlBindings.ts:partColorOptions` from `src/domain/cubeEdgeState.ts:cubePartColors`, so the domain role vocabulary is the only membership owner. Keep role labels as UI metadata rather than another hand synchronized membership list.

Defer the face and edge field owner consolidation, TS and CSS token generation, palette ownership, shader feature composition, and procedural colour module. Each crosses additional persistence or package boundaries and is unnecessary for the edge Accent slice.

Correctness prerequisite: remove the rejected `src/theme/scenePolarity.ts:cubeFaceLightnessDeltaById` application from `src/scene/instancedPartMeshCore.ts:resolveInstanceColor`, because the current artifact and thumbnail path changes authored face colours. This is a fidelity repair, separate from the one grooming consolidation.

### Discipline

**Changed:** I changed C from freeform to enum after the UX and scout reports showed that a scarce role is the stronger product constraint and already matches compact persistence, validation, controls, and tween identity.

**Reject:** I reject the UX report's claim that a Pose palette change animates through the existing OKLab tween for free. `src/evaluation/sceneMorph.ts:createPartColorTweens` creates a tween when part labels differ; an unchanged `accent` label with two palette values is invisible to that classifier, and `PartColorTween` does not carry two resolver contexts.
