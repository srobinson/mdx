# Scout: Shape tab reuse map

Read at 2bfdfc4 (spike/shape-shader, on main ae44cbf). Goal: a third cube-panel tab driving
edge treatment + shapeSize through the existing control path. Read-only scout.

## (a) Registration points for a new ControlBindingId

| Point | Owner | Cost |
|---|---|---|
| Id union | `src/editor/controlBindings.ts:ControlBindingId` | add literal(s) |
| Binding object (createCommand, label, read, schema in one place) | `controlBindings.ts:ControlBinding`, e.g. `cubeEdgeThicknessBinding` | one object per id |
| Registry | `controlBindings.ts:controlBindingList` | append; `controlBindingIds` and `controlBindingsById` derive from it |
| Field renderer | `src/panels/ControlBindingField.tsx` | ZERO: renders boolean/enum/number schemas generically (enum fits treatment, number fits shapeSize) |
| Grouped id lists | `src/panels/panelDefinitions.ts` (`edgeBindingIds` etc., `satisfies readonly ControlBindingId[]`) | only if the per-edge Part panel also gets the fields |
| Enumerating tests | `tests/panels.test.tsx` "control binding integrity" iterates `controlBindingIds` | ZERO manual work: derived, validates uniqueness/label/schema automatically |
| Exhaustive switches on the id | none found (`rg "switch.*bindingId|case \"cube\." src tests`) | - |

Tab itself: `src/state/cubicellState.ts:CubePanelTab` ("dimensions" | "style") + `setCubePanelTab`
(`src/state/actions/types.ts`), rendered by `src/panels/CubeSection.tsx:CubePanelTabs` (Segmented
options + one branch per tab). Editor-session state, not wire; adding "shape" is a union literal,
one Segmented option, one branch.

## (b) Are ephemeral bindings a thing?

No. All 17 registered bindings' `createCommand` implementations call
`createSceneEditorCommand` (18 call sites in `controlBindings.ts`, one per binding plus none
elsewhere); the consumer `src/panels/useControlBinding.ts:useControlBinding.setValue` dispatches
the returned `EditorCommand` through `useEditorCommandDispatch`. Proof symbols:
`ControlBinding.createCommand: (value, context) => EditorCommand | null` and the grep above —
no binding writes a store, ref, or global. A Shape tab driving the spike store would be the
FIRST ephemeral binding, a new pattern rather than reuse.

## (c) PR #148 edge-field descriptor owner and the cost of a new field

Owner: `src/domain/cubeEdgeState.ts:cubeEdgeStateOwner = createCubeEdgeStateOwner({...})`
(commit 5f01f74 "single owner for edge field schema (#148)"). One
`defineCubeEdgeStateField` entry carries decode/encode/isEncoded (codec), isValue (validation),
defaultValue, distance (equality/selection), inherit, morphChannel, renderAttribute.

Derived automatically from the table, zero extra work:
- `CubeEdgeState` type, `defaultState`, `isState`/`isPatch` (op validation:
  `src/state/authoredOperationValidation/scene.ts` uses `owner.isPatch` for `set-edge-state`).
- Wire codec: `src/persistence/recordCodecs/compactPose.ts` uses `owner.encode/decode/areEqual`.
- Hydration: `src/state/workbenchValidation/pose.ts` uses `owner.isState/hasValidFields`.
- Morph: `src/evaluation/sceneMorph.ts` uses `owner.getMorphChanges/interpolateMorph`
  ("discrete-cut" fits treatment — `visible` already uses it; "numeric-lerp" fits shapeSize).
- Render impact: `CubeEdgeRenderAttribute` derives from the table
  (`src/domain/authoredRenderImpact.ts`); `src/domain/incrementalCubeRenderResolution.ts` treats
  any non-"resolution" edge attribute as reindex+re-resolve — a new "shape" attribute rides the
  same lane thickness uses, no special-casing found.
- Selection aspects: `src/domain/selectionAspects.ts` uses `owner.matches/distance`.

Not automatic, step by step for treatment + shapeSize:
1. Move the vocabulary to the domain: `EdgeShapeTreatment`/`edgeShapeTreatments` currently live in
   `src/scene/edgeShapeShader.ts`; controlBindings (editor layer) must not import scene, so the
   union moves into `cubeEdgeState.ts` beside `cubePartColors` and the shader imports it.
2. Two `defineCubeEdgeStateField` entries (treatment: discrete-cut, encode as index like color;
   shapeSize: numeric-lerp like opacity).
3. Wire bump: encoded pose arrays grow → `src/persistence/indexedDbSchema.ts:
   indexedDbProjectStorageVersion` 5 → 6, reset (no migrations, project rule).
4. Renderer read: `src/scene/cubeInstances.ts` currently spreads the spike global into edge
   instance data; replace with per-edge reads from `cell.edges[edgeId]` at that same site. The
   shader attributes (`edgeShapeShader.ts:edgeShapeAttributeNames`, `instancedPartMeshCore.ts`,
   `edgeCoverageCore.ts`) are already per-instance and proven — untouched.
5. Tests that pin the wire shape update: `tests/cubeEdgeStateOwner.test.ts` hardcodes encoded
   arrays (`[2, 0.4, 0.08, 0]`); `cubeEdgeStatePropagation`, `authoredRenderImpact`, morph tween
   suites extend by one field each.

## (d) Spike duplication and dead-code risk

`src/scene/edgeShapeSpike.ts` is a global second writer by design and says so: its doc comment
orders its own deletion ("Delete this module, its control, and the four call sites... once
treatment and shapeSize travel on the edge state through set-edge-state"). The four call sites:
1. `src/scene/cubeInstances.ts` — spreads `readEdgeShapeSpike()` into every edge instance.
2. `src/scene/incrementalCubeSceneOwner.ts` — cache key suffixed `|spike:${version}` (a staleness
   mask that must not survive: real per-edge state already invalidates through render impact).
3. `src/scene/useCubeSceneInstances.ts` — `useEdgeShapeSpikeVersion()` re-render hook.
4. `src/studios/editor/EditorStudio.tsx` — mounts `EdgeShapeSpikeControl`.
Plus `src/scene/EdgeShapeSpikeControl.tsx` (its own duplicate of ScrubField/Segmented wiring).
If the panel drives the spike store instead, every one of these stays alive AND the control
pattern forks (ephemeral binding vs authored binding) — exactly the parallel implementation ban.

## (e) Recommendation: REAL

One line: the spike's own deletion note names set-edge-state as the destination, and SPIKE-GRADE
would create the repo's first ephemeral control binding plus keep a second writer alive, while
REAL rides five single-owner derivations that already exist.

Costs:
- REAL: ~11 files. Domain table +2 fields with vocabulary move (1), wire bump (1), renderer read
  swap + spike deletion (5: cubeInstances, incrementalCubeSceneOwner, useCubeSceneInstances,
  EditorStudio, delete spike module + control), bindings +2 ids (1), tab union + branch (2),
  plus test updates (owner arrays, propagation, impact, morph) and new binding coverage. Undo,
  persistence, State capture, and morph come free.
- SPIKE-GRADE: ~4 files (tab union, CubeSection branch, panel wiring to `setEdgeShapeSpike`,
  keep spike alive) but breaks invariant (b), skips undo/persistence/State capture entirely
  (captured States would not carry shape), and leaves the cache-key hack in the hot scene owner.

done: 5 sections, 7 registration points, 17/17 bindings authored, 5 spike sites named.
