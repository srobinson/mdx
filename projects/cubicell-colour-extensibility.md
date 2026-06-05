# Cubicell fifth colour extensibility probe

## Result

Added `warm`, a coral rail opposite the green accent:

- Dark polarity: `#fac0c0`
- Light polarity: `#430c1c`

The probe began at 16:10:47 and reached verified green at 16:14:37, 3 minutes 50 seconds. This timing benefits from recent familiarity with the accent change. A competent engineer new to this code should allow 20 to 30 minutes to discover the owners, add the role, interpret the compiler and test failures, and prove persistence, tween, control, and artifact behavior.

## Cost

The final diff contains 12 touched edit sites across 7 files, measured as distinct symbols or test blocks rather than changed lines. Git reports 56 insertions and 13 deletions.

### Production

1. `src/domain/cubeEdgeState.ts:cubePartColors`
   Appended `warm`. This extends `CubePartColor`, runtime validation, edge field encoding, face codec indexing, and generated control options through their existing shared source.

2. `src/theme/themeTokens.ts:themeColorTokens`
   Added `warm` and `warmOnLight` hex rails.

3. `src/theme/scenePolarity.ts:artifactPartColors`
   Excluded `warm` alongside `accent` because both need polarity specific values.

4. `src/theme/scenePolarity.ts:workbenchPartColors`
   Applied the same exclusion to the workbench base map.

5. `src/theme/scenePolarity.ts:scenePolarities`
   Passed the warm rail at both artifact polarity construction sites.

6. `src/theme/scenePolarity.ts:workbenchScenePolarities`
   Passed the same rails at both workbench polarity construction sites.

7. `src/theme/scenePolarity.ts:createPolarityConfig`
   Added the positional `warm` parameter and included it in `partColors`.

### Verification

8. `tests/editorAdapters.test.ts:black and white polarities resolve theme tokens`
   Updated both exact polarity fixtures with the warm rails.

9. `tests/editorAdapters.test.ts:authored hues follow polarity and the workbench reuses the artifact rails`
   Added artifact and workbench assertions for both warm polarities.

10. `tests/colorSpace.test.ts:black to authored hue produces distinct OKLab samples`
    Parameterized the existing accent tween guard over `accent` and `warm`.

11. `tests/cubeEdgeStatePropagation.test.ts:authored hue survives compact pose validation and round trip`
    Parameterized the edge and face persistence proof over `accent` and `warm`.

12. `tests/thumbnailArtifact.test.ts:warm parts survive the artifact path`
    Authored all faces and edges as warm, created the real thumbnail artifact, and checked every emitted face and edge color against the warm artifact rail.

## Compiler guidance versus manual discovery

The first edit added only `cubePartColors.warm` and the two theme tokens. `pnpm exec tsc -b --force` then emitted two errors at `scenePolarity.ts:artifactPartColors` and `scenePolarity.ts:workbenchPartColors` because `ScenePartColors` required `warm`. Those errors identified the polarity owner. Satisfying that owner required five edit sites in `scenePolarity.ts`, so 5 of 12 final edit sites were compiler guided.

The compiler did not identify tests or behavioral proof. The first focused unit run found the stale exact polarity fixture in `tests/editorAdapters.test.ts`. Persistence, tween, and artifact coverage had to be found manually by tracing and searching the existing accent tests.

## Fail open checks

None observed.

- Control: a temporary omission of `warm` from `partColorOptions` made all three cube, face, and edge coverage cases fail. After restoration, the control suite passed and the generated value is present. The label is derived mechanically as `Warm`.
- Persistence: compact face encoding uses `cubePartColors.indexOf`, decoding validates against `cubePartColors.length`, and edge encoding delegates to the field owner. The fifth index required no codec change. Both warm face and edge round trips passed.
- Tweens: the generic `resolveCubePartColor` path required no production change. Five black to warm OKLab samples were distinct.
- Export: the instance and thumbnail paths required no production change. Every warm face and edge in the real thumbnail artifact resolved to `#fac0c0` under black polarity.
- Final focused verification: `pnpm exec tsc -b --force` passed, then 6 relevant test files passed with 93 tests. The control omission probe independently went red with 3 failures.

## Remaining sharp edges

1. High: `scenePolarity.ts:createPolarityConfig` encodes each authored hue as another positional string parameter and repeats it across four calls plus two `Omit` lists. The record type prevents a missing role, which is good, but same typed positional values can be swapped. This was the largest real cost.

2. Medium: behavior coverage is feature named rather than owner derived. Persistence and tween tests were accent specific, so the fifth role worked without those tests noticing until they were manually expanded. Artifact coverage also required a manually discovered new case.

3. Low: face color persistence remains hand rolled in `compactPose.ts`, unlike edge color encoding through `cubeEdgeStateOwner`. This probe required no face codec edit because the manual code correctly consumes `cubePartColors` and its length. The duplication remains a latent drift risk rather than current fifth colour cost.

4. Dismissed for this task: the CSS and TypeScript hex twins exist for black, white, and selection accent, but authored part hue rails are consumed only by the TypeScript and Three.js path. Adding `warm` required no CSS token. The twin issue is real for shared UI and scene tokens, but it does not constrain adding another authored cube colour today.

## Worktree

All changes are confined to `/Users/alphab/Dev/LLM/DEV/helioy/cubicell/.claude/worktrees/fifth-colour` on `probe/fifth-colour`. The scratch branch is intentionally dirty with the seven measured files. No commit was created.

## After a7083972

### Untouched baseline

The isolated `/Users/alphab/Dev/LLM/DEV/helioy/cubicell/.claude/worktrees/fifth-after` worktree was clean at `a708397227521fd18c991518fa2c2b84d200d4e3` before the probe.

`pnpm test` passed before any edit:

```text
Test Files  187 passed (187)
     Tests  2609 passed (2609)
  Duration  12.15s
```

This confirms the polarity refactor itself has zero observed unit behavior regression and preserves the requested 2609 pass baseline.

### After cost

The same `warm` role now costs 9 edit sites across the same 7 files, down from 12 across 7:

1. `src/domain/cubeEdgeState.ts:cubePartColors`
2. `src/theme/themeTokens.ts:themeColorTokens`
3. `src/theme/scenePolarity.ts:artifactPartColorsByPolarity.black`
4. `src/theme/scenePolarity.ts:artifactPartColorsByPolarity.white`
5. `tests/editorAdapters.test.ts` polarity fixtures and authored hue test
6. `tests/colorSpace.test.ts` authored hue tween case
7. `tests/cubeEdgeStatePropagation.test.ts` authored hue persistence case
8. `tests/thumbnailArtifact.test.ts` warm artifact case

The numbered file list contains 8 rows because the two `editorAdapters` test blocks are separate edit sites. Counting distinct symbols and test blocks exactly as in the before measurement gives 9 edit sites. Git reports 49 insertions and 9 deletions.

The production cost fell from 7 edit sites across 3 files to 4 across 3. All three removed production edits are automatic now:

- `scenePolarities` consumes the exhaustive artifact rail record without a role specific call edit.
- `workbenchScenePolarities` consumes derived exhaustive workbench records without a role specific call edit.
- `createPolarityConfig` accepts the complete `partColors` record without a role specific parameter or object assembly edit.

No former error became a silent pass.

### Decisive omission proof

After adding `warm` to `cubePartColors` and adding its two tokens, both warm rail entries were deliberately omitted. `pnpm exec tsc -b --force` exited 2 with eight `TS2741` errors. The errors covered both artifact maps, both derived workbench maps, and all four polarity consumers.

Adding only these two entries made all eight errors disappear:

- `artifactPartColorsByPolarity.black.warm`
- `artifactPartColorsByPolarity.white.warm`

No workbench map, polarity constructor, or config builder edit was needed. The compiler therefore caught 2 of the 9 final edit sites. The lower compiler count reflects three automatic downstream steps, not three silent gaps.

### Behavior verification

After the two rail entries and the same proof edits used in the before probe:

```text
Test Files  6 passed (6)
     Tests  93 passed (93)
```

`pnpm exec tsc -b --force` and `git diff --check` also passed. Persistence still accepts the fifth index without a codec edit, tweens require no production edit, the generated control includes the fifth union member, and every warm face and edge survives the real thumbnail artifact path.

### Sharp edges after refactor

1. Medium: behavioral proof remains manually discovered. The compiler identifies the two rail entries, but persistence, tween, exact polarity fixture, and artifact coverage are still feature named and must be expanded by hand.

2. Low: face color persistence remains hand rolled in `compactPose.ts`. It correctly consumes `cubePartColors` and its length, so the fifth index still needs no codec change. The latent drift risk remains.

3. Dismissed for authored colour cost: CSS and TypeScript hex twins still exist for shared black, white, and selection colors, but adding another authored part role requires no CSS token.

Positional polarity wiring is gone as a sharp edge. The exhaustive rail records are materially safer and reduce the production edit surface by three sites.

### Refactor bytes

The `satisfies Record<ScenePolarity, ScenePartColors>` type constraint erases. The implementation around it does not. The refactor replaced two flat shared runtime maps plus positional accent arguments with two nested per-polarity runtime records:

- `artifactPartColorsByPolarity`, containing separate black and white subobjects
- `workbenchPartColorsByPolarity`, containing separate black and white subobjects created with object spreads

It also changed config construction from positional values plus `{ ...partColors, accent }` inside `createPolarityConfig` to passing prebuilt config objects. The additional emitted object structure, repeated property keys, and module initialization spreads are the runtime bytes. They sit in the shared scene polarity module, so the same small payload appears in editor studio, shared renderer, and their combined default interactive closure. The observed gzip increases are 34, 35, and 33 bytes respectively. This is an acceptable but real runtime cost of prebuilt exhaustive maps, not type metadata and not measurement noise being hidden by a baseline.

The after scratch branch remains intentionally dirty with the same seven measured files and no commit.
