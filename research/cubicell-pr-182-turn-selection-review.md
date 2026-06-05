---
title: Cubicell PR 182 turn-selection review
type: research
tags: [cubicell, code-review, dry, rotation, authored-operations]
summary: Clean-and-DRY review of feat/turn-rotate-selection; maths verified correct by probe, one user-visible defect and eight cleanliness findings, all resolved in five follow-up commits
status: active
project: cubicell
confidence: high
---

# Cubicell PR 182, turn a cube selection about its shared pivot

Head `01a4980` against `origin/main` `68d76aa`. 20 files, +419/-30.

Reviewed by the parent agent plus a three-runtime panel: codex on the registration surface, grok on the DRY sweep, claude-opus on maths and panel. Every finding below was re-verified by the parent against the source or by running code. The panel's claims are not passed through.

## Verdict

The maths is correct, the wiring is complete, and the headline capability is reachable. One user-visible defect should be fixed before merge. The rest is cleanliness debt: a duplicated CSS rule, a function written twice, a dead flag, a loose type, a half-finished type migration, and an operation name that breaks its siblings' convention while being expensive to change after schema v7 ships.

## Verified correct, by probe rather than by reading

| Claim | Result |
| --- | --- |
| `createRotationBasis` matches three.js `makeRotationFromEuler` XYZ columns | max error 0.000e+0, bit-identical |
| Euler round-trip reproduces the basis, away from gimbal lock | max error 1.182e-13 |
| Unwrap keeps each component within PI of the reference | max 3.141564, bound 3.141593 |
| Quarter turns land on exact quarter multiples, depth-4 walks | deviation 0.000e+0 |
| Five quarter turns author 5PI/2, eight author 4PI | exact |

`createPrincipalEuler` is a faithful port of three.js's XYZ branch, gimbal case included. The alternate solution `[x+PI, PI-y, z+PI]` is algebraically exact; all nine matrix entries check out. Hand-rolling is required, not lazy: `src/domain/**` has zero `three` imports, so routing through `shared/three.ts` would break the layering rule.

The worst-case 8.5e-4 error sits entirely inside three.js's own `0.9999999` gimbal threshold, in 53 of 200,000 random samples, and three.js's `Euler.setFromRotationMatrix` scores an identical 8.519e-4 on the same inputs. Inherited, not introduced. Dismiss any "gimbal precision bug" finding on this evidence.

Rigidity holds for any mix of cube sizes: `turnCell` acts on `renderPosition`, the cube centre, and rotation matrices are orthogonal. `getBaseHomePosition` reads only `placement.coord` and the grid, never `offset`, so grid alignment is invariant under a turn and the authored offsets stay self-consistent.

The centroid pivot is the right choice for a reason the PR does not state: it is the only pivot invariant under its own turn, so four quarter turns return exactly to the start and the inverse is exact. A bounding-volume pivot would recompute and drift. This also makes replay safe, since the operation materializes to `{kind: "ids"}` and stores no pivot.

Registration is complete across all six hand-maintained registries. Scene-family inverses derive generically from `createSceneRestorePatch` diffing before and after, so both new kinds get a correct inverse with no per-operation entry.

Gate re-run locally rather than taken from the checklist: `tsc -b` exit 0, 30/30 contract tests, 3.1s against an 8s budget.

## Fix before merge

### 1. Reset is disabled by the active cube while it acts on the whole selection set

`src/panels/CubeSection.tsx:183` computes `disabled` from `selectedCell.placement.rotation` alone, while `:188` dispatches to `resolvePartEditScope({ editTarget, selectionSet })`, the whole set.

Failure path, confirmed by reading the selection reducer. Turn cube A. Shift-click untouched cube B. `selection.ts` sets `active = additions[0]`, so B becomes the active cube, and `derivePartEditTarget` sets the scope to the selection set because the set is non-empty. B's rotation is `[0,0,0]`, so Reset greys out and the user cannot reset A without deselecting B first. The same root cause makes the readout show B's `0°` while the panel is editing a set that contains a turned cube.

Compute the predicate over the resolved scope, not over `selectedCell`.

## Cleanliness findings

### 2. `.cc-euler-readout` is declared twice

`src/panels/panels.css:286` and `:294`. The second block adds only `width: 100%`. Merge into the first.

### 3. `resetCubeTurn` is `snapCubeHome` written twice

`src/domain/cube.ts:206-219`. Identical structure, `offset` swapped for `rotation`. One parameterised helper, two named wrappers.

### 4. The `changed` flag is unconditionally true

`src/domain/turnSelection.ts:15-29`. The `selected.length === 0` guard at line 9 forces the map to reach `changed = true`, so line 29's false branch is unreachable, and `CubeTurnDirection = -1 | 1` rules out a no-op turn. Delete the flag.

### 5. `turn-selection` breaks its siblings' naming, and schema v7 makes it costly to fix later

Every other cube operation carries `cube` in its kind: `resize-cube`, `set-cube-offset`, `snap-cube-home`, and this PR's own `reset-cube-turn`. The name is also inaccurate, since the operation takes a `CubeScope` that may be `single` or `ids`, neither of which is a selection. `turn-cube` matches `resize-cube` and pairs with `reset-cube-turn`. The kind string is persisted in authored documents, so renaming after v7 documents exist costs a migration. Decide now.

### 6. The zero-rotation predicate is duplicated, and it is an exact float comparison

`rotation.every((value) => value === 0)` appears in `CubeSection.tsx:183` and again inside `resetCubeTurn` at `cube.ts:215`. Two copies of one rule.

The `=== 0` is separately wrong in kind. Turn sequences produce float residue on axes they did not turn: a cube at `[-3.14159, 0, 1.22e-16]` counts as turned by the exact predicate and reads as `0°` in the panel. Export one predicate using the `areNearlyEqual` tolerance the codebase already has at `worldGeometry.ts:196`.

### 7. `ReturnType<typeof createSceneGridLayout>` where a named type exists

`src/domain/turnSelection.ts`, `getSharedPivot`. `gridLayout.ts:15` exports `SceneGridLayout`. Also, `turnCell` takes six positional parameters, two of which are fields of the same `CubeLayoutPose`; passing `layout[cell.id]` drops two.

### 8. The Vec3 migration was started and abandoned

The PR adds `src/shared/vector.ts` as a canonical home, then has `cubeTopology.ts:1-3` both import and re-export it. Exactly one production caller moved, `shared/three.ts`. Vec3 is now reachable by seven specifiers across roughly 30 call sites: `../domain` (14), `./cubeTopology` (9), `./cube` (2), `./vector` (2), plus three singletons. The PR's own `turnSelection.ts` imports `Vec3` from `./cubeTopology` while importing `rotateAroundAxis` from `../shared/axisRotation`, using both paths in one file.

The `cube.ts:389` re-export predates this PR and is not its fault.

Either finish the migration or drop `shared/vector.ts`. A third home nobody uses is worse than either end state.

### 9. `axisRotation.ts` is a one-algorithm file next to an existing maths module

`src/shared/math.ts` already owns Vec3-shaped maths and spells the tuple inline instead of importing `Vec3`. Private vector helpers remain scattered across `cameraTrack.ts:327-357`, `cameraTrackValidation.ts:270-279`, `exposure.ts:200-205`, `worldGeometry.ts:200-205`, and `compactPose.ts:196`, which reimplements the `isSameVec3` already in `math.ts`. The new file inlines its own cross and dot next to those leftovers.

Most of this sprawl predates the PR. The point is that a fourth one-algorithm file is the wrong direction. One `shared/vec3.ts` holding the type and the operations is the right shape.

## Smaller notes

The authored winding survives repeated turns about one axis but not a gimbal crossing. Turn five times about Z to reach `Z 450°`, then once about Y, and Z reads `360°` while the pose stays exact to 2.2e-16. The contract test asserts the revolution invariant unconditionally. Add a comment on `createPrincipalEuler` naming the limit.

`aria-label` is derived by a ternary while `turnActions` already carries `direction`, `glyph`, and `label`. Make it a fourth field so direction meaning has one source.

`CubeTurnDirection = -1 | 1` restates `AxisSign` at `cubeTopology.ts:6`. `export type CubeTurnDirection = AxisSign` keeps the domain name and reuses the definition. Defensible either way.

`.cc-panel-divider` is a third hand-rolled copy of `border-top: 1px solid var(--cc-panel-border)`, alongside `grid-composer.css:76` and `motion.css:619`, and does not replace them.

"Raw Euler" is developer wording in a user panel. The readout earns its place as the only surface showing a full revolution stayed authored as `360°`, but the value grows without bound and renders as `-1620° -1260° 1440°` in a narrow three-column grid.

Two test-coverage gaps, neither a defect in shipped behaviour. The committed test never applies the inverse returned for `reset-cube-turn`, so a Reset undo regression would pass. And `previousAuthoredSchema` at `authored-operation.contract.test.ts:78` is pinned to 5 while the schema is now 7, so the test proves v5 is rejected and never exercises v6, the version whose in-flight outbox entries the bump actually invalidates. That constant has gone stale across two consecutive bumps, so derive it as `authoredOperationSchemaVersion - 1` rather than fixing the literal again.

## The PR's own open question, answered

The PR body asks whether the multi-cube path is reachable, given `CubeSection` renders only when a single `selectedCell` exists.

It is reachable, and the premise misreads `selectedCell`, which resolves the active member of a selection rather than proving a single selection. With two or more cubes selected, `selection` stays non-null and points at the active member, `derivePartEditTarget` returns `"selection-set"` without the user touching a toggle, and `resolvePartEditScope` then hands `turnSelection` every id. `Snap home`, already shipped, sits in the same component behind the same guard and uses the identical resolver, so Turn is exactly as reachable as an operation already in production.

The real gap is discoverability: nothing on screen says the button acts on the set. That applies to Snap home identically and predates this PR.

## Resolution

Every finding above was fixed on the branch and pushed. Decision trail at
`~/.mdx/sessions/cubicell-pr-182-cleanup.tsv`.

| Commit | What it closed |
| --- | --- |
| `39a7694` | Reset enablement, the shared tolerant predicate, snapCubeHome and resetCubeTurn deduped, areNearlyEqual moved to shared/math to break a cycle |
| `d89f021` | Renamed the operation to `turn-cube`, CubeTurnDirection aliases AxisSign |
| `e11a3e1` | Dead `changed` flag, `ReturnType` for `SceneGridLayout`, turnCell parameters, duplicate CSS rule, aria into the table, winding limit documented |
| `a453de5` | One home for Vec3 and the vector maths; shared/vector.ts and shared/axisRotation.ts deleted along with three re-export hops |
| `8d3613d` | Reset undo assertion, previousAuthoredSchema derived from the source constant |

Two things were deliberately not changed. The two `border-top` rules in
`grid-composer.css` and `motion.css` stay as they are, because a 1px border in
two unrelated components is not shared-utility duplication. The Euler readout
stays scoped to the active cube, because showing one cube's raw angles is a
defensible display choice in a way a button that will not light is not.

Proof beyond the suite. The fix was driven in the running app: with the turned
cube in the selection set and an untouched cube active, Reset was enabled while
the readout read `X 0° Y 0° Z 0°`, clicking it cleared the turned cube, and
Reset then went disabled. Turning the set moved both cubes to `[0, PI/2, 0]`.
No page errors. The maths probe was re-run after the rotation code moved
modules: basis against three.js still 0.000e+0, eight quarter turns still
exactly 4PI.
