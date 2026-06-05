# Scout: Evaluation seam (MODEL.v2 extraction step 2)

Read-only scout, 2026-07-10, by cubicell:general:8:6.1. No source
modified. Basis: main at b156d44. Goal: lift Evaluation (`scoreAt` +
the Moment overlay) behind a stable contract, then re-point consumers.

## 1. Public contract

The pure Evaluation module should export exactly five symbols, all of
which already live in `src/anim/scoreAt.ts`:

| Symbol | Kind | External consumers (file + use) |
| --- | --- | --- |
| `Moment` | type | `src/scene/CubeScene.tsx` (prop type `moment?: Moment \| null`); `src/anim/useTransportMoment.ts` (return type) |
| `scoreAt` | fn | `src/anim/useTransportMoment.ts` (the only production caller); `tests/anim.test.ts` |
| `getMomentCells` | fn | `src/scene/CubeScene.tsx` (`stagedCells`); `tests/anim.test.ts` |
| `applyMomentToLayout` | fn | `src/scene/CubeScene.tsx` (`layout`); `tests/anim.test.ts` |
| `getScoreDurationMs` | fn | `src/panels/BottomDock.tsx` (dock readout); `src/state/cubicellStore.ts` (transport clamp at end of score); `src/anim/TransportDriver.tsx` (loop/stop boundary); `tests/anim.test.ts`, `tests/state.test.ts` |

Nothing currently reachable needs to leave the contract: the file's
non-exported helpers (`applyAssemblyTrack`, `getAssemblyDurationMs`,
`clamp01`) are already private, and every export has a live consumer.
There is no dead surface to trim. `TransportDriver` and
`useTransportMoment` are consumed only by `src/app/App.tsx` and are
NOT part of the Evaluation contract; they are the transport adapter
(section 2).

Dependency direction is healthy and stays as-is: Evaluation depends
only on Domain types plus pure easing math; State (`cubicellStore`),
Panels (`BottomDock`), Scene (`CubeScene`), and the transport adapter
all point at Evaluation, never the reverse.

## 2. Home, naming, and the pure/adapter boundary

Current home is `src/anim/`, three files, no barrel; every consumer
deep-imports `../anim/scoreAt` or the two adapter files directly.

The boundary inside `src/anim/` is already crisp and must be cut along
it:

- **Pure Evaluation core**: `scoreAt.ts` only. Imports are
  domain types (all `import type`) plus `easeOutQuart` from
  `src/motion/easing.ts` (pure function, shared with
  `interaction/morph`, `interaction/orbitDetent`, and
  `motion/cameraMotion`; it stays in `motion/easing` as shared pure
  math). No React, no three, no DOM, no store. This lifts.
- **Transport adapter**: `TransportDriver.tsx` (React, rAF wall
  clock, writes the playhead through the store; the time-source seam)
  and `useTransportMoment.ts` (React, reads session time from the
  store, the only place session time meets the document). These stay
  behind; they are adapter wiring in MODEL.v2's horizontal seams and
  belong to the Transport bounded context vertically.

**Recommendation: rename now, in step 2, not later.** Land the pure
core as `src/evaluation/` (module `scoreAt.ts` + curated `index.ts`
barrel) and move the two adapter files to `src/transport/`. Rationale:
the re-pointing work is identical whether or not we rename (five
production import sites plus two test files), so deferring the rename
means touching the same files twice; and both names are already the
ubiquitous language (`ANIMATION.md` and MODEL.v2 say Evaluation;
ANIMATION.md's primitive and MODEL.v2's first-class category say
Transport). Total blast radius is seven files, smaller than either
domain slice that already shipped.

## 3. Moment staging contract: clause map (the acceptance test)

`CubeScene.tsx` composes document and Moment once at the top
(`stagedCells`, `layout`) and everything below derives from those two.
The four consumers named by MODEL.v2 are `visibleCells`, `instances`,
`chromeCells`, and the neighbor slots.

**Clause 1 — presence-zero cells are absent from every downstream
derivation.** Provenance: `ANIMATION.md` invariant 2 verbatim
("presence zero is absence everywhere"). Honored by `getMomentCells`
(`src/anim/scoreAt.ts`), which filters `scene.cells` into
`stagedCells` in `CubeScene`. All four consumers inherit it through
`stagedCells`: `visibleCells` = `getSelectionVisibleCells(stagedCells,
…)`; `instances` = `useCubeSceneInstances(visibleCells, …)`;
`chromeCells` filters `visibleCells`; `neighborSlots` =
`getSceneShadowShell(stagedCells)` or
`getCubeNeighborSlots(stagedCells, …)`, with the empty-scene seed slot
keyed on `stagedCells.length`.

**Clause 2 — arriving cells scale through `applyMomentToLayout`.**
Provenance: the easing of presence during arrival is grounded in
`ANIMATION.md` inv 2 ("easing 0 to 1 during arrival"); the specific
mechanism (presence multiplies pose scale in `applyMomentToLayout`,
`src/anim/scoreAt.ts`) is a code contract. Honored where `layout` is
built in `CubeScene`. Consumers: `instances` (via
`useCubeSceneInstances(visibleCells, layout, …)`) and
`neighborSlotInstances` (via `createNeighborSlotInstances(…, layout,
…)`).

**Clause 3 — arrived pose references stay referentially stable.**
Provenance: pure code contract, twice over. `applyMomentToLayout`
keeps the exact pose reference when presence >= 1 and returns the
input `layout` object untouched when nothing is mid-arrival; upstream,
`useStableGridLayout` (`src/scene/useStableGridLayout.ts`) keeps
`baseLayout` pose refs stable across recomputes. Consumer:
`instances`, whose per-cell cache in `useCubeSceneInstances` misses
only on pose-reference change; `neighborSlotInstances` also memoizes
on `layout` identity.

Existing tests already pin all three clauses: `tests/anim.test.ts` has
"getMomentCells drops presence-zero cells and keeps the array
reference when nothing filters" and "applyMomentToLayout scales
arriving poses and preserves arrived pose references", plus the
`scoreAt` describe block (tolerant references, deleted-id skip per
inv 4). The extraction's acceptance test is: these tests pass
unchanged except for the import path, and `CubeScene`'s staging block
diff is import-only.

## 4. Purity and quality

- **Purity confirmed.** `scoreAt.ts` imports five `import type`
  bindings from `../domain` and one pure function from
  `../motion/easing`. No React, three, DOM, or store anywhere in the
  pure core. The two adapter files are the only React in `src/anim/`.
- **One DRY item.** `scoreAt.ts` declares a private `clamp01` while
  `src/shared/math.ts` exports `clamp` (already used by four files).
  Fold `clamp01(v)` into `clamp(v, 0, 1)` during the lift; zero
  behavior change.
- **No dead code, no leaks.** Every export is consumed; no other file
  reaches into `src/anim/` beyond the five production import sites
  listed above (verified by import sweep).
- **Boundary enforcement: oxlint works, mirror the domain guard.**
  `.oxlintrc.json` already enforces the domain barrel with
  `no-restricted-imports` patterns `**/domain/*` + `*/domain/*` and an
  override freeing `src/domain/**` and `tests/**`. The identical
  pattern pair for `evaluation` (and `transport`) enforces the new
  barrels; barrel imports (`…/evaluation`) pass, deep paths
  (`…/evaluation/scoreAt`) fail. No boundary test needed. Decide
  whether `tests/**` keeps its exemption or the anim tests move to the
  barrel; recommend the barrel, it costs one line.

## 5. Ordered plan (PR-sized slices, bound to the contract)

1. **Slice E1 — Evaluation behind the contract.** Move
   `src/anim/scoreAt.ts` to `src/evaluation/scoreAt.ts`; add curated
   `src/evaluation/index.ts` exporting exactly `Moment`, `scoreAt`,
   `getMomentCells`, `applyMomentToLayout`, `getScoreDurationMs`;
   re-point `CubeScene.tsx`, `BottomDock.tsx`, `cubicellStore.ts`, the
   two anim-internal imports, and `tests/anim.test.ts` +
   `tests/state.test.ts` to the barrel; add the oxlint guard patterns;
   fold `clamp01` into `shared/math.clamp`. Gates: full suite green,
   lint clean, `tests/anim.test.ts` semantically untouched,
   `CubeScene` staging block import-only diff.
2. **Slice E2 — Transport adapter home.** Move `TransportDriver.tsx`
   and `useTransportMoment.ts` to `src/transport/` with their own
   barrel and guard; re-point `App.tsx`; delete the now-empty
   `src/anim/`. Gates: suite green, no file imports `src/anim`
   anywhere.
3. **Docs follow-through (same PR as E2 or immediately after).**
   Update `ARCHITECTURE.md` items for the new homes and mark MODEL.v2
   extraction step 2 done.

Then step 3 (`ViewPose` and pose math) proceeds per MODEL.v2's
sequence, unchanged.
