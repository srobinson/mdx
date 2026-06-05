# G22 Scout: stage-plan preparation cadence

Scout report, read-only, main @ 277589d. Owners verified: `src/transport/useStagedScene.ts::useStagedScene`, `src/evaluation/sceneTransition.ts::sampleSceneTransition`, `src/evaluation/sceneMorph.ts::prepareSceneMorph`.

## 1. Prep cadence today

Preparation happens in one place in the app: the `plan` memo inside `useStagedScene` (`src/transport/useStagedScene.ts::useStagedScene`). Its key is broken.

- The `source` memo deps are `[morphScrub, transport, workbench]`. During a Compare drag, `morphScrub.t` changes on every pointer event, so `resolveStageSource` re-runs and builds a fresh `ComparisonStageSource` object each tick: new object identity, fresh `a` from `getStateScene`, and a fresh inline `transition: { mode: 'auto', settings: defaultMorphSettings }`.
- The plan memo is keyed on `[morph]`, and `morph` IS that per-tick source object (`comparisonSource` only narrows, it does not stabilize). The key therefore carries `progress`/`timeMs`, the exact values that change every tick. The memo can never hit within a scrub, so `prepareSceneMorph` re-runs per tick.
- Endpoint identity churns independently: `src/domain/workbench.ts::getStateScene` builds a fresh `CubicellScene` per call (`sceneFromPose` spread plus `extractAssemblyScore`), so even a memo keyed on `[morph.a, morph.b]` would miss today. Endpoint stabilization is part of the fix, not an optional nicety.

## 2. Fast path vs fallback

- Fast path: `sampleSceneTransition(a, b, transition, timeMs, preparedPlan)` with a plan present goes straight to `sampleSceneMorph(plan, timeMs)`.
- Fallback: `preparedPlan ?? prepareSceneMorph(a, b, transition.settings)` (`src/evaluation/sceneTransition.ts::sampleSceneTransition`). The fallback runs the full prep: endpoint diff classification, three `planClassMotion` schedules (sort per order mode), shared-edge tween planning, ink classification.
- When playback takes it: always. `useStagedScene` prepares a plan only for `comparison` sources (`comparisonSource(source)` returns `null` for `'piece'`), so every piece frame calls `sampleStageSource(workbench, source, undefined)` → `src/evaluation/pieceAt.ts::samplePieceAt` → `sampleSceneTransition(..., undefined)` → fallback prep. `src/transport/TransportDriver.tsx` drives `setTransportTime` per `requestAnimationFrame`, so during piece playback each rAF frame pays: two `getStateScene` endpoint rebuilds plus one full `prepareSceneMorph` plus the sample. The `preparedPlan` parameter is threaded end to end (`sampleStageSource` → `samplePieceAt` → `sampleSceneTransition`) but nothing ever supplies it on the piece path.

## 3. Cross-link to the parked TX symptom (G17/G18)

**No.** The cadence bug does not explain authored ORDER/EASING/stagger having no visible effect during playback, because per-tick re-prep is deterministic:

- Authored settings reach prep every frame: `samplePieceAt` passes `track.transitions[position.index]` (the authored transition; persistence verified through `src/domain/stateTransition.ts` patch path using `patchMorphSettings`) into `sampleSceneTransition`, and the fallback preps with `transition.settings`. Nothing substitutes defaults on this path.
- Re-prep produces the identical schedule each tick: `src/domain/assemblyOrder.ts::generateAssemblyOrder` is fully deterministic, including `random` (authored `seed` through `seededShuffle`); every other mode is a total order with the cell id as tiebreak. Endpoint scenes are value-identical rebuilds and `isSameCubeCell` compares by value. So the schedule cannot flicker or average out across frames. The cadence bug is pure CPU waste, not signal loss.

High-value adjacent finding: there IS a path where authored settings are provably discarded, and it lives in the same function. `resolveStageSource` hardcodes `transition: { mode: 'auto', settings: defaultMorphSettings }` for the Compare scrub, and the Compare slider (`src/panels/motion/MotionInspector.tsx::StateInspector`) is the only interactive scrub in the editor. If the G17/G18 observation was made by dragging Compare rather than playing the transport, authored ORDER/EASING/stagger have zero effect there by construction. Caveat: Compare pairs a saved State with the live working scene, not a track state pair, so which authored transition it should borrow is a design question for Stuart, not an obvious bug fix. Recommended verification: a live check that authored settings visibly apply during actual transport playback (code says they should today); if they do not, the cause is outside the cadence seam and this scout's evidence chain narrows it to sampling, not prep.

## 4. Plan

Reuse map: the memo seam already exists in `useStagedScene` (source memo plus plan memo); the hook-level cache precedent is `useRef(new Map)` in `src/scene/useCubeSceneInstances.ts`; no domain-level plan cache exists and none is needed. Fix stays inside the existing hook plus one small extraction in `pieceAt.ts`. No new cache module, no runner.

**Step A: split the stable pair from the clock.**

- Comparison: memoize the endpoint pair and transition on `[workbench, morphScrub?.stateId]` (excluding `t`): `a = getStateScene(workbench, state)`, `b = getWorkingScene(workbench)`, transition as a module constant instead of a per-call literal. Key the plan memo on that stable pair. Only `t`/`timeMs` flow per tick into `sampleStageSource`. Result: one prep per Compare session per workbench edit instead of per tick.
- Piece: hoist segment resolution into the hook. Extract an exported `resolvePieceTransitionSegment(workbench, asset, timeMs)` in `src/evaluation/pieceAt.ts` returning the active `{ a, b, transition, index }` (or null when static/none), built from the existing `findStateTransitionTrack` + `resolveStateTransitionPosition` + `getStateScene` calls that `samplePieceAt` already makes, and reuse it inside `samplePieceAt` so segment resolution stays single-sourced. The hook memoizes the segment on `[workbench, asset, position.index]`; `position.index` changes only at segment boundaries, so prep runs once per transition segment. The plan flows through the already-threaded `preparedPlan` parameter. This also stabilizes endpoint scene identity, killing the two per-frame `getStateScene` rebuilds for free.
- Divergence safety: the hook and `samplePieceAt` resolve position from the same `timeMs` in the same render via a pure function, so the prepared plan cannot mismatch the sampled segment.

**Step B: fallback policy.** Keep `preparedPlan ?? prepareSceneMorph(...)` in `sampleSceneTransition`. It is semantically identical (deterministic prep) and keeps the evaluator pure for direct domain callers and tests. After Step A the app seam always supplies a plan, and a prep-count test (below) pins that. Making `preparedPlan` required was considered and rejected: larger blast radius across pure callers for no behavior gain.

**Step C: no semantics changes.** Compare keeps `defaultMorphSettings` in this fix; wiring authored settings into Compare is a G17 design decision, not perf work.

## 5. Blast radius, tests, gates

- Files: `src/transport/useStagedScene.ts` (main change), `src/evaluation/pieceAt.ts` (extract resolver, reuse in `samplePieceAt`), `src/evaluation/index.ts` (export). No domain type changes, no wire or persistence impact, no serialized surface (plans are transient evaluation values).
- Risks: memo dependency correctness. Workbench edits during playback must invalidate the plan (`workbench` in deps covers it); segment boundary crossings re-prep via the `index` dep (correct and desired); Compare open/close re-keys via `stateId`.
- Tests (existing coverage: `tests/stagedScene.test.ts`, `tests/pieceMotionEvaluation.test.ts`, `tests/sceneMorph.test.ts`, perf harness `tests/sceneMorph.bench.ts`). Add:
  1. Prep-count pin: sampling N frames of one transition performs exactly one prep (spy on the evaluation module seam, or assert plan identity via the extracted resolver).
  2. Segment boundary: crossing into the next transition yields a new plan carrying that transition's authored settings.
  3. Invalidation: a workbench edit mid-playback produces a fresh plan.
  4. Resolver unit tests: static hold, transition segment, clamp at last segment (mirrors `resolveStateTransitionPosition` contracts).
- Gates: pnpm test, lint, build. Behavior is identical by construction (deterministic prep), so this is a perf-only change; a transport playback smoke on the live gate is still recommended.
