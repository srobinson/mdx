# F1 G9 cut transition scout

Scope: live `main` at `277589ddb72c41e6da07768e66e179aa3d104440` on 2026-07-17. Source review was read only. The checkout began with the preexisting tracked change `M LESSONS.md`; its diff hash was `e790dc057347204f7b843442b45bb0241ea39098` before the scout.

## Verdict

`working-capability`, with `deletion=entangled` for deleting both the forced cut mode and `MorphSettings.cutAt`.

Two related behaviors exist:

1. An explicit persisted `Transition.mode === 'cut'` performs a complete scene swap at `cutAt * durationMs`. The Editor transport reaches this branch through a live production path.
2. An ordinary `mode === 'auto'` morph also reads `cutAt`. It selects the source or target value for fields that have no continuous interpolation, using local progress for retained cubes and global progress for scene and grid modes.

The explicit forced cut mode could be removed in a bounded change while retaining `cutAt`. Removing the scalar as well requires a new policy for every discrete field, so full deletion is entangled.

## 1. Complete footprint

### Piece motion production references to `cutAt`

| Layer | File and symbol | Role |
| --- | --- | --- |
| Domain | `src/domain/morphSettings.ts::MorphSettings` | Declares `cutAt: number` as the local progress point for noninterpolated fields. |
| Domain default | `src/domain/morphSettings.ts::defaultMorphSettings` | Defaults `cutAt` to `0.5`. |
| Domain mutation | `src/domain/morphSettings.ts::patchMorphSettings` | Reads a patch, clamps the value to `[0, 1]`, includes it in semantic equality, and returns it in the new settings object. |
| Auto morph evaluator | `src/evaluation/sceneMorph.ts::sampleSceneMorph` | Computes `globalCut` from global progress. It separately compares each retained cube's local progress with `cutAt`. |
| Auto morph cell selection | `src/evaluation/sceneMorph.ts::interpolateCell` | Uses the local cut result to select source or target discrete cell data. Geometry, numeric ink, and color overlays continue through their interpolation paths. |
| Auto morph scene selection | `src/evaluation/sceneMorph.ts::sampleSceneMorph` and `interpolateGridState` | Switches `frameId`, polarity, projection, grid alignment, and grid overflow at the global cut. |
| Forced cut evaluator | `src/evaluation/sceneTransition.ts::sampleSceneTransition` | Computes `cutAtMs` and returns the complete source scene before the boundary and the complete target scene at or after it. Zero duration returns the target immediately. |
| Editor UI | `src/panels/motion/MorphInspector.tsx::MorphInspector` | Renders a `ScrubField` labelled `Scene switch`, writes `{ cutAt: value }`, and reads `transition.cutAt`. |
| Persistence validation | `src/state/scoreValidation.ts::isMorphSettings` | Requires a finite `cutAt` in `[0, 1]`. |

No other piece motion production file reads or writes the scalar.

### Forced cut mode and authoring references

| Layer | File and symbol | Role |
| --- | --- | --- |
| Domain model | `src/domain/score.ts::TransitionMode` and `Transition` | Defines `'auto' | 'cut'` and persists `mode` beside `settings`. |
| Domain default | `src/domain/stateTransition.ts::defaultTransition` | Creates new gaps as `mode: 'auto'` with `defaultMorphSettings`. |
| Domain mutation | `src/domain/stateTransition.ts::TransitionPatch` and `patchTransition` | Accepts an optional mode, preserves the current mode when omitted, and installs the authored mode into the transition array. |
| Domain inheritance | `src/domain/stateTransition.ts::appendKeyframe` and `repairTransitionCount` | New gaps inherit the prior complete transition, including a forced cut mode, or use `defaultTransition`. |
| Domain resolution | `src/domain/stateTransition.ts::resolveTransitionKind` | Maps an explicit cut mode to evaluator kind `cut`; every auto mode maps to `morph`. |
| Document operation | `src/domain/structureOperations.ts::StructureSequenceDocumentOperation` | Exposes optional `mode` and settings on `patch-transition`. |
| Document reducer | `src/domain/structureOperations.ts::applyStructureSequenceOperation` | Passes the operation to `patchTransition` and commits the resulting structure owned score. |
| Public domain surface | `src/domain/index.ts` | Reexports `TransitionMode` and `resolveTransitionKind`. |
| Evaluation | `src/evaluation/sceneTransition.ts::SceneTransitionFrame` and `sampleSceneTransition` | Carries kind `cut | morph` and owns the whole scene cut branch. |
| Validation | `src/state/scoreValidation.ts::isTransition` | Requires mode `auto` or `cut` and valid morph settings. |

### Live playback path

The observable production call chain is:

`src/transport/useStagedScene.ts::useStagedScene`
→ `resolveStageSource`
→ `sampleStageSource`
→ `src/evaluation/pieceAt.ts::samplePieceAt`
→ `src/domain/stateTransition.ts::resolveStateTransitionPosition`
→ `src/evaluation/sceneTransition.ts::sampleSceneTransition`
→ complete A or B scene for `mode: 'cut'`, or `prepareSceneMorph` and `sampleSceneMorph` for `mode: 'auto'`.

`src/evaluation/pieceAt.ts::samplePieceAt` reads the authored transition from the attached structure's `StateTransitionTrack`. The result becomes the scene rendered by the shared stage. This is a live Editor transport path.

### Persistence and serialization

| File and symbol | Role |
| --- | --- |
| `src/state/cubicellStore.ts::useCubicellStore` persist options | `partialize` persists the complete Workbench, including structure owned Scores. The current schema is `cubicellStorageVersion = 12`. |
| `src/state/wireEncode.ts::createWireEncoder` | Spreads the Workbench into the wire object. Transition mode and settings are serialized without a special adapter. |
| `src/state/scoreValidation.ts::isStateTransitionTrack`, `isTransition`, and `isMorphSettings` | Decode validation retains the mode and scalar. |
| `src/state/workbenchValidation.ts::readStructureScore` and `completePersistedWorkbench` | Accepts the validated state transition track and repairs it for the owning structure. |
| `src/state/persistedStateNormalization.ts::normalizePersistedState` | Runs the current validation and repair path on every merge. |
| `tests/pieceMotionPersistence.test.ts::Piece motion persistence` | Deep round trips the complete v12 PieceScore, so mode and `cutAt` are covered through object equality. |

### Independent camera namespace

Camera tracks also use the names `cut` and `cutAt`. They are a separate capability and should remain outside any Piece Motion deletion:

- `src/domain/cameraTrack.ts::CameraPosePath`, `CameraPoseSegment`, and `CameraProjectionSegment`
- `src/domain/cameraOperations.ts::patchCameraSegment`
- `src/evaluation/cameraTrack.ts::sampleCameraTrack` and `sampleProjection`
- `src/state/cameraTrackValidation.ts`
- `src/studio/CameraTrackControls.tsx`
- camera operation, evaluator, persistence, and Studio control tests

The repo wide `git grep cutAt` must therefore be filtered by owner. A global deletion would damage the separate authored camera lane.

## 2. Alive or dead

Alive.

For a forced cut, `sampleSceneTransition` executes:

```ts
const cutAtMs = transition.settings.cutAt * transition.settings.durationMs
scene: transition.settings.durationMs === 0 || timeMs >= cutAtMs ? b : a
```

The boundary is observable through the attached Piece transport. Existing proof includes:

- `tests/assetStateInvariants.test.ts::cut sampling swaps exactly at the boundary without interpolation`, which uses `cutAt: 0.4` and verifies A at 399 ms, B at 400 ms, plus zero duration.
- `tests/pieceMotionEvaluation.test.ts::cut transitions swap scenes at the authored cut point`, which drives `applyDocumentOperation` through `samplePieceAt` and verifies different scene cell counts on either side of the boundary.
- `tests/pieceMotionEvaluation.test.ts::forced cuts emit endpoint ink without color metadata`, which verifies the complete endpoint swap and a null morph Moment.
- `tests/stagedScene.test.ts::a forced cut holds the source before its boundary`, which verifies the production stage adapter.

For an auto morph, the scalar remains observable:

- Per cube local cut: `CubeCell.visible`, edge visibility, face visibility, and other discrete cell data select an endpoint in `interpolateCell`.
- Global cut: `frameId`, polarity, projection, grid alignment, and grid overflow select an endpoint in `sampleSceneMorph` and `interpolateGridState`.
- `tests/sceneMorph.test.ts::snaps scene and grid modes at the global cut` verifies the global boundary.

This is more than a half wired scalar. It has domain normalization, document mutation, persistence, two evaluator uses, a live stage consumer, UI authoring, and focused tests.

## 3. UI reality

Stuart's observation and the gap document refer to different surfaces:

- There is no control labelled `CUT`, `Cut`, `cutAt`, `AUTO`, or `Auto` in the F1 Piece Motion UI.
- There is no segmented AUTO/CUT mode selector. `TransitionInspector` only dispatches settings patches and never dispatches `{ mode: ... }`.
- `MorphInspector` still renders the scalar as a scrub labelled `Scene switch`.

The scrub is mounted and reachable, with contextual preconditions:

1. `src/config/cubicellConfig.ts::editorPieceMotionWorkspaceEnabled` is `true`.
2. `src/panels/BottomDock.tsx::BottomDock` mounts `PieceMotionPanel`.
3. Two States create the first transition gap.
4. A new second State focuses that gap automatically, or the user selects a transition card through `PieceStateStrip`.
5. `src/panels/Inspector.tsx::Inspector` sees `focus.kind === 'gap'` and mounts `TransitionInspector` in the shared right rail.
6. `src/panels/motion/MotionInspector.tsx::TransitionInspector` mounts `MorphInspector`, which renders `Scene switch`.

The G9 sentence in `~/.mdx/projects/f1-ui-gap-analysis.md` has mixed freshness:

- “`MorphInspector` still exposes one raw Scene switch scrub for `MorphSettings.cutAt`” is correct.
- “AUTO/CUT has no authored model” is stale. The authored and persisted `TransitionMode = 'auto' | 'cut'` model exists. The missing piece is its Editor control.

The absence of visible CUT wording is therefore confirmed. The scalar control remains present under another label and only appears while a transition card owns the contextual inspector.

## 4. Provenance

The requested `git log -S cutAt` history identifies the first four commits below. Focused file history and blame identify the two later commits that mounted and relocated the unchanged path:

| Commit | Date | Meaning |
| --- | --- | --- |
| `a3e6ff1` `feat(animation): establish scene morph and asset timeline foundation` | 2026-07-14 | Introduced `MorphSettings.cutAt`, the `0.5` default, `TransitionMode = 'auto' | 'cut'`, the explicit whole scene cut branch, auto morph discrete cuts, and their original tests and specifications. |
| `e5c0063` `refactor(domain): split backend readiness seams (#81)` | 2026-07-16 | Connected document transition patches to the existing settings normalization and added the current persistence validation for `cutAt` and `mode`. |
| `f2245a8` `feat(motion): add Editor Piece Motion frontend primitives (F0) (#82)` | 2026-07-16 | Extracted the shared `MorphInspector` and retained the `Scene switch` scrub. The workspace flag was false, so the new F0 workspace was not mounted yet. |
| `b31bce7` `feat(motion): add piece evaluation and Editor session (B2) (#84)` | 2026-07-16 | Connected the attached Piece sampler to `sampleSceneTransition` and added the live path forced cut boundary test. |
| `6403128` `feat(motion): Editor Piece Motion workspace binding and cutover (F1) (#86)` | 2026-07-17 | Mounted Piece Motion in the Editor and changed auto resolution to always morph. Explicit forced cut behavior remained. |
| `333c398` `feat(panels): contextual right-rail inspector and first-class transition cards (#91)` | 2026-07-17 | Moved transition editing into the contextual right rail and retained the same `Scene switch` scrub. |

The active domain design explicitly says a forced cut persists as `mode: 'cut'`, keeps its duration, and swaps at `cutAt`. History searches find no AUTO/CUT selector in `MorphInspector` or its earlier `StripControls` owner. The raw `Scene switch` control existed from the first scene morph panel and survived the F0, F1, and PR 91 moves.

Conclusion: this is a deliberately built working capability with an incomplete Editor surface. It is neither a lost selector nor inert leftover scaffolding.

## 5. Delete versus park

### Delete only the explicit forced cut mode

This narrower deletion is bounded:

1. Remove `TransitionMode`, `Transition.mode`, `TransitionPatch.mode`, and the operation level `mode` field.
2. Simplify `defaultTransition`, `patchTransition`, inheritance assertions, and public exports.
3. Remove `resolveTransitionKind`, `SceneTransitionFrame.kind`, and the forced cut branch in `sampleSceneTransition`.
4. Change persisted transition validation so mode is absent from the accepted current shape.
5. Keep `MorphSettings.cutAt`, `sampleSceneMorph` local and global cut comparisons, and the `Scene switch` scrub. Those belong to auto morph discrete field timing.
6. Update the active asset state timeline specification, which currently promises forced cut persistence and sampling.

For a clean wire removal, bump `cubicellStorageVersion` from 12 to 13. The current decoder validates a raw transition and returns that object. Without a bump or explicit reconstruction, an extra persisted `mode` key can survive in memory and be written again. The existing migration policy already resets all older versions, so a v13 reset matches the pre release no compatibility rule. Update:

- `src/config/cubicellConfig.ts::cubicellStorageVersion`
- `src/state/cubicellState.ts::CubicellWireState` version comment
- `tests/pieceMotionPersistence.test.ts` v12 test title and exact version assertions
- any plan or current model documentation that names v12 as current

An explicit decoder reconstruction that drops `mode` could avoid a reset, but it creates shape cleanup code for unreleased data. The established repository policy favors the version bump and reset.

### Delete forced cut and `cutAt`

This is entangled. It includes the narrower removal plus:

1. Remove `MorphSettings.cutAt`, its default, patch normalization, UI scrub, and persistence validation.
2. Replace local discrete cell selection in `sampleSceneMorph`.
3. Replace global selection for `frameId`, polarity, projection, grid alignment, and grid overflow.
4. Decide whether each field switches at the start, midpoint, end, or through a channel specific policy.

Hard coding `0.5` would remove authoring while retaining the same cut semantics internally. Switching at the end changes visible behavior for every auto transition. No threshold at all is undefined for categorical and boolean fields. A product decision is required before this deletion can be correct.

Direct test blast radius:

- `tests/assetStateInvariants.test.ts`: auto versus forced cut resolution and exact forced boundary
- `tests/pieceMotionEvaluation.test.ts`: whole scene cut and endpoint ink cases
- `tests/pieceMotionOperations.test.ts`: mode patching, inheritance, and reorder ownership
- `tests/workbenchOperations.test.ts`: mode mutation, settings clamping, and repaired transitions
- `tests/stagedScene.test.ts`: forced cut stage behavior
- `tests/sceneTestHelpers.ts`: forced cut fixture with `cutAt: 0.25`
- `tests/sceneMorph.test.ts`: global discrete switch behavior
- `tests/sharedEdgeRendering.test.ts`: explicit morph settings fixture
- `tests/pieceMotionPersistence.test.ts`: complete score round trip and storage version
- `tests/morphInspector.test.tsx` and `tests/pieceMotionPanel.test.tsx`: transition UI expectations; add an explicit absence assertion if the control is removed

Camera cut tests remain untouched.

### Park behind a flag

There are two distinct parking levels:

**Surface park:** add a dated rationale flag beside `seamSurfacesEnabled` in `src/config/cubicellConfig.ts`, then conditionally omit the `Scene switch` scrub from `MorphInspector`. This hides the only current cut related Editor control. Forced cuts already have no Editor authoring control. Persisted or programmatic `mode: 'cut'` data would still execute, so this parks only the surface.

**Capability park:** retain the v12 fields and add one flag that also makes `sampleSceneTransition` resolve every Piece transition through the morph path while disabled. Keep `cutAt` as the internal threshold for auto morph discrete fields, or specify a fixed replacement threshold. Reject or ignore programmatic mode patches at the application boundary if the flag must prohibit new authored cuts. This preserves dormant persisted data and needs no version bump.

Tests for a true capability park should prove:

- the control is absent while disabled;
- a persisted `mode: 'cut'` evaluates as a morph while disabled;
- the existing cut boundary behavior returns when enabled;
- the independent camera cut lane remains unchanged.

Parking is reversible. Full deletion changes current morph semantics unless the discrete field policy is settled first.

## Verification

- Repository and history scans: `git grep` for `cutAt`, cut mode, snap terminology, `MorphInspector`, and every stage consumer; `git log -S cutAt` plus focused blame and commit diffs.
- Focused tests: 8 files passed, 92 tests passed.
  - `tests/assetStateInvariants.test.ts`
  - `tests/pieceMotionEvaluation.test.ts`
  - `tests/morphInspector.test.tsx`
  - `tests/pieceMotionPanel.test.tsx`
  - `tests/pieceMotionPersistence.test.ts`
  - `tests/pieceMotionOperations.test.ts`
  - `tests/workbenchOperations.test.ts`
  - `tests/sceneMorph.test.ts`
- No source file was edited by this scout. The only authorized write is this report.
