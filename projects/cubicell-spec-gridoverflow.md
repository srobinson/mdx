# GridOverflow contract spec

Verified against origin/main `5f01f74`. `GridOverflow = "allow" | "clamp" | "hide"` lives on `src/domain/grid.ts:GridFormat.overflow`, one value per scene (`src/domain/scene.ts:CubicellScene.grid`), zero production readers today. Prerequisite: no stored bound exists; `src/domain/scene.ts:getSceneGridDimensions` measures occupied extent only, so a persistent bound field is required before any variant can differ from `allow` (Decision 1).

## 1. Contract

Bound = the stored grid bound (Decision 1/2). A coord is in-bounds when every axis lies inside it. All variants are per structural write; none mutate cells retroactively when the value itself changes (a test can assert: toggling overflow with out-of-bound cells present leaves `scene.cells` identical).

| Surface | allow (today) | clamp | hide |
| --- | --- | --- | --- |
| Placement (`placeCubesAt` seeds, incl. neighbor grow) | Any coord accepted; scene may hold negative coords and gaps | Seed coord clamped per axis to the nearest in-bound coord; the clamped coord then follows existing occupant rules (reveal hidden, no-op on visible, duplicate seeds collapse) | Out-of-bound seeds dropped; `placeCubesAt` returns the same scene reference when every seed drops, so no history entry |
| Lattice insert/delete shift | Shift proceeds unbounded | An insert whose shifted half would exit the bound is a no-op returning the original scene by reference (existing `shiftLattice` no-op path); deletes always fit | Shift proceeds; cells pushed past the bound stay in `scene.cells` but stop rendering; the inverse shift restores them pixel-identical |
| Rendering | All cells render | Nothing to exclude (out-of-bound cells cannot exist) | Cells with out-of-bound coords excluded from every render pass and hit-test, exactly as `visibility: "hidden"` cells are today |
| Persistence round-trip | Value and cells round-trip (already true) | Same; clamped writes persist their clamped coords | Out-of-bound cells persist as ordinary cells; encode → decode → render reproduces the same hidden set |
| Selection | Unchanged | Unchanged | Coordinate scopes (`axis`/`plane`/`pattern` targets) and hit-testing never return out-of-bound cells; id-addressed operations still reach them |
| Morph | `sceneMorph` already copies overflow at the cut | Same | When bounds differ across the cut, the hidden set switches at the cut, matching the existing discrete-cut rule |

Resize (`resizeGridScene`) is the bound writer, not an overflow consumer: the plan's dimensions become the new stored bound, and its existing crop semantics are unchanged under every variant (Decision 4).

Nested grids (recursive by design per `CUBICELL.md`; no nested grid exists in the model today, `src/domain/cube.ts:CubeCell` holds no grid): each grid level judges overflow in its own coordinate space against its own bound. To the outer grid the nested grid is one occupant of one cell, so inner overflow never alters outer coords; an out-of-bound nested-grid cell under outer `hide` hides the entire subtree. Forward contract only; nothing to build now.

## 2. Owners

Searches run: `git grep -n "overflow" origin/main -- src tests` (all readers), `git grep -n "placeCubesAt\|insertLatticeLine\|resizeGridScene\|getSceneGridDimensions"` (placement funnel), `git grep -n "bounds\|Bound"` in `src/domain` (no stored bound exists; `getCellCoordBounds` is extent, not bound).

- Bound storage and defaults: `src/domain/grid.ts:GridFormat`, `withGridFormatDefaults`, `cloneGridFormat`.
- Bound predicate: new `isCoordInGridBounds` in `src/domain/grid.ts` — the one genuinely new symbol; nothing existing answers "is this coord inside the stored bound".
- Placement enforcement: `src/domain/neighbors.ts:placeCubesAt` — the single funnel; `addNeighborCubes` and the `place-cubes` operation already delegate to it.
- Lattice enforcement: `src/domain/lattice.ts:insertLatticeLine` guard before `shiftLattice`, reusing its reference-return no-op.
- Bound writer: `src/domain/scene.ts:resizeGridSceneWithResult` and `createGridResizePlan`.
- Render/hit-test exclusion: the same pass owner that excludes `visibility: "hidden"` today, `src/domain/incrementalCubeRenderResolution.ts` (and its non-incremental counterpart), keyed off the bound predicate.
- Selection exclusion: `src/domain/selectionQuery.ts` occupancy index construction.
- Wire validation: `src/state/workbenchValidation/pose.ts:isGridFormat` / `isPersistedGridFormat` (enum already validated; bound field joins the `hasOnlyKeys` allowlist).

## 3. Wire

Overflow persists per scene: one `GridState` per pose, carried verbatim through `src/persistence/recordCodecs/compactPose.ts` (`g: pose.grid`) and completed by `withGridFormatDefaults`. The variant itself is already on the wire and validated; reading it needs no bump. Adding the bound field to `GridFormat` changes the wire object and the `hasOnlyKeys` allowlist: bump `src/persistence/storageRecordTypes.ts:committedRecordSchemaVersion` and reset. No migrations, single user. Per-placement or per-cell overflow is out of contract.

## 4. Default

`allow`. It is already `defaultGridFormat.overflow` and the `withGridFormatDefaults` fallback, and it is the current de facto behavior: placement is unbounded and neighbor-grown scenes hold coords below zero (stated in `getSceneGridDimensions`'s own comment). With no stored bound present, `clamp` and `hide` also behave as `allow`; nothing changes until a user sets both a bound and a non-default variant.

## 5. Decisions for Stuart

1. Bound source: store it on `GridFormat`, or derive from occupied extent? Recommend stored field written by resize; extent-derived is self-fulfilling (the extent grows with every accepted write, so nothing ever overflows).
2. Bound shape: `dimensions` anchored at origin, or signed min/max bounds? Recommend signed min/max; neighbor growth already produces negative coords, and an origin-anchored bound would misclassify them all.
3. Clamp on lattice insert: reject the whole shift as a no-op, or clamp shifted cells (collapsing coords destructively)? Recommend reject; destructive clamp breaks the inverse-shift identity the lattice tests guard.
4. Resize under `hide`: keep today's crop of out-of-plan cells, or retain them as hidden? Recommend keep crop; resize redefines the bound, overflow governs placement and render only.
5. Exposure: domain-only this cycle with default `allow`, or UI control now? Recommend domain-only; `GridSection` gains the control once a bound exists to display.

## 6. Tests and gates

- `pnpm test` (vitest unit project) with new assertions in: `tests/neighbors.test.ts` and `tests/sceneOperation.placeCubes.test.ts` (clamp remap, hide drop, same-reference no-history on full drop), `tests/lattice.insert.test.ts` (clamp no-op by reference, hide shift round-trip identity), `tests/domain.test.ts` (bound predicate, defaults completion), `tests/poseRevisionIntegrity.test.ts` and `tests/projectRecordCodecs.test.ts` (bound field round-trip, version bump, allowlist), `tests/sceneMorph.test.ts` (already asserts overflow copy; add differing-bound cut).
- `tests/incrementalScene.browser.test.ts` pattern (`observeWebGlResources`) for hide exclusion: hidden-by-overflow cells render zero instances and program count is unchanged; run via `pnpm test:browser`.
- Type gate: `npx tsc --noEmit` (never `pnpm check` in read-only contexts; it runs `oxlint --fix`).
- Rule 6 of the decision sheet applies: every new field name needs a `src/` occurrence and a naming test or an explicit parked marker.
