# PR #566 code review, head 22a85d7e

Read only review of `canvas-layout-strategies` at exact head
`22a85d7e7bd855f211ea2e673fe9dca73e46cbe1`, merge base `1a365aa7` (26 files,
+669/-130). Stuart has road tested and UX blessed the branch, so everything
below is code level. No blockers. Seven findings, ranked by value.

Verification run for this review (read only, no edits):

- Targeted vitest over every touched test file: 10 files, 87 tests, all pass.
- `tsc -b --noEmit` on `@tm/canvas`: clean.
- Numeric probes importing the real `engine/layout/grid.ts` under Node type
  stripping (scratchpad scripts, nothing written into the repo).

---

## 1. The hot spot is demoted whenever the partial body row holds exactly one pane

**Where** `www/packages/canvas/src/engine/layout/grid.ts:115-127` (`fillGrid`,
the `leadCount` branch).

**Observed** `leadCount = restIds.length % cols`. When `leadCount === 1` the lead
row is laid out with `inRow = 1`, so `cellW = region.width`: the single lead pane
is stretched to the full region width at the same height as the hot spot row.
`p0` and `p1` come out with identical `x`, `width` and `height`.

Probe against the real module, region `1472x872`, gap 24, targetAspect 4/3:

    n=4  cols=3  p0 1472x424   p1 475x424  p2 475x424  p3 475x424   -> dominant
    n=5  cols=3  p0 1472x275   p1 1472x275  p2..p4 475x275          -> identical

Expand remainder column (`splitW * 0.45` wide, 904 tall), n=4:

    p0 666x285 at y=0
    p1 666x285 at y=309      <- same width, same height as the hot spot
    p2, p3 321x285

**Impact** The module's documented contract is broken at those counts.
`grid.ts:68-70` promises "Adding or removing other panes never changes the
occupant and never removes the slot", and `strategies/gridFill.ts:15-17`
promises "a dominant top row that later additions never demote". Going from 4
to 5 panes on the canvas demotes the hot spot from dominant to
indistinguishable, which is exactly the demotion the comment rules out. The
occupant is still `p0`; its prominence is not.

**Reproduction** Open 5 panes on a 1600x1000 canvas with grid-fill selected: the
top two rows are the same size. In the expand view, open 5 panes and expand one
(remainder of 4): the first two remainder panes are the same size. Affected
counts on the standard canvas: n = 5, 8, 10, 14, 17. In the expand remainder:
n = 4, 6, 8, 11, 14, 17, 20, 22. Portrait canvas: n = 6, 8, 10, 12, 14, 17, 20, 23.
The remainder-of-4 case means five open panes with one expanded, which is a
routine count.

**Basis** Direct execution of `fillGrid` from the branch head, plus the two
comments above.

**Why the tests miss it** `gridFill.test.ts:62` ("keeps the first pane in the hot
spot at every count past one row") iterates n in {3,4,5,7,9,12,13,16} but asserts
only `p0.x`, `p0.y` and `p0.width`. It never asserts that `p0` is distinguishable
from `p1`. n=5 is in that list and passes.

**Caveat** This is a layout/prominence defect, not a crash, and the branch is UX
blessed. Stuart may have seen these counts and accepted them. If so the fix is to
the two comments, not the code. If not, the shape of the fix is a decision for
the owner: either fold a lone lead pane into the hot-spot row (a hot row of two),
or leave it at one cell width instead of stretching it.

---

## 2. `swapExpandedPane` has no test that exercises the real implementation

**Where** `www/packages/canvas/src/model/canvasActions.ts:368-376`.

**Observed** `grep` over `src` finds `swapExpandedPane` in exactly one test file,
`dnd/paneDndCallbacks.test.ts`, where it is a `vi.fn()` mock (line 44) and the
assertions are `toHaveBeenCalledWith("b")` (lines 229, 240) and
`not.toHaveBeenCalled()` (line 254). No test calls the store action. The reducer
below it, `exchangePaneOrder`, is tested in isolation at
`engine/reducers/layoutState.test.ts:92`.

**Impact** The invariant this PR exists to deliver is asserted nowhere as an end
state. It is documented in three places, all prose:

- `model/canvasState.ts:72-76` "exchanges the two panes' committed order
  positions, then expands paneId ... the remainder hot spot stays pinned to its
  occupant unless that occupant is the pane swapping in"
- `model/canvasActions.ts:372-373` "the outgoing hero inherits the incoming
  pane's committed slot"
- `engine/reducers/layoutState.ts:128-133` the same claim again

Nothing binds the reducer to the action. Deleting the `set(...)` on line 374
leaves every existing test green: the callbacks test only sees its own mock, and
no store test reaches the action. The composition is the load-bearing part and it
is the untested part.

**Reproduction** `rg 'swapExpandedPane' www/packages/canvas/src` returns the
mock call sites and no store-level call site.

**Basis** Grep over the branch head. I did not mutate the source to demonstrate
the surviving-mutant claim, since the review is read only; the grep is sufficient
to show no test can observe the implementation.

**Note** `model/canvasStore.test.ts:419-465` already has the exact harness for
this (spawn panes, `expandPane`, assert `expandedPaneId`), so closing the gap is
cheap. An end-state assertion would be: expand A in order [A,B,C], call
`swapExpandedPane("c")`, assert `layout.order` is `["c","b","a"]`, assert
`expandedPaneId === "c"`, and assert the remainder hot spot occupant is still B.

---

## 3. The column-selection fold is duplicated, and it is the half that matters

**Where** `engine/layout/grid.ts:44-64` (`fillGridColumns`) and
`engine/layout/strategies/gridFit.ts:119-141` (`selectColumns`).

**Observed** Both are the same fold: ascend `cols` from 1 to `count`, compute a
per-candidate plan, minimize a penalty, tie-break with an epsilon band to fewer
rows then fewer columns, seed with `bestCols === 0`. Only the penalty and the
cell derivation differ.

**Impact** The stated purpose of this branch is to stop grid math from drifting.
Commit 287084a0 is "share grid math across layout strategies" and `grid.ts:3-4`
says the shared module exists "so the per-strategy placement loops and the
repeated `n * size + (n - 1) * gap` extents never drift apart". The placement
loop and the extent formula are now shared. The selection fold, which carries the
subtler contract (epsilon semantics, tie-break ordering, seeding), is duplicated
instead.

Drift is already present between the two copies: `fillGridColumns` skips
candidates with non-positive cells (`continue`, line 52) and clamps the result
with `Math.max(1, bestCols)` (line 63); `selectColumns` does neither.

**Basis** Side-by-side read of the two functions at head.

**Shape of the fix** One `selectGridColumns(count, planFor, penaltyFor)` in
`grid.ts` that both call, with the candidate-skip predicate as a parameter.

---

## 4. Dead tie-break branch, carried into the new module, with a comment that
overstates it

**Where** `engine/layout/grid.ts:57` and
`engine/layout/strategies/gridFit.ts:133`, both reading
`(rows === bestRows && cols < bestCols)`.

**Observed** The loop ascends `cols` from 1. After the first assignment
`bestCols` is always strictly less than the current `cols`, so `cols < bestCols`
can never be true. The condition is unreachable in both copies.

**Impact** No runtime effect: fewer-columns-wins is already delivered by the
ascending loop, because an exact tie leaves `better` false and the earlier (lower)
`bestCols` stands. The cost is a reader-load defect. The comments at
`grid.ts:36-37` and `gridFit.ts:117-118` both say "ties break to fewer rows, then
fewer columns", which describes a mechanism that is not the one at work and
invites a future reader to assume the loop direction is free to change. It is
not: reverse the loop and the fewer-columns tie-break silently inverts.

**Basis** Loop-direction read. The `gridFit.ts` copy predates this PR (it was in
`selectFill`/`selectAspect`); `grid.ts:57` is a new occurrence introduced here.

---

## 5. `fillGrid` yields negative heights on a region shorter than its gap budget

**Where** `engine/layout/grid.ts:104-133` and
`engine/layout/strategies/gridFill.ts:36-50` (`planGridFill`, which builds the
region with no non-negative clamp).

**Observed** Probe against the real module:

    fillGrid(ids(4), {x:64, y:64, width:1472, height:-28}, {gap:24, targetAspect:4/3})
      -> every rect { x:64, y:64, width:1472, height:-7 }

`fillGridColumns` skips every candidate (all cells non-positive), returns the
`Math.max(1, 0)` fallback of 1 column, and the hot-spot branch then computes
`hotH`, `bodyH` and `cellH` from a negative region height.

**Reproduction path** `planGridFill` builds
`height: viewport.height - 2 * margin` with a default margin of 64, so a canvas
surface under 128px tall reaches it. `workbench/CanvasWorkbench.tsx:111` guards
only `bounds.width > 0 && bounds.height > 0`, not a minimum. The lab's margin
control goes to 120, which raises the threshold to 240px of surface height.

**Impact** Panes render with a negative CSS height, which the browser drops, so
the panes collapse rather than crash. Recovers on the next resize.

**Caveat, and why this is low severity** `strategies/singleRow.ts:35` has the
identical exposure today (`cellH = viewport.height - 2 * margin`, unclamped), so
grid-fill follows an existing pattern rather than introducing a new class of
defect. `gridFit` and `gridOverflow` are immune because their `minW`/`minH`
floors clamp. The expand path is also safe: `expandLayout.ts:39` passes
`margin: 0` and `splitExpandColumns` already clamps with `Math.max(0, ...)`.

---

## 6. `swapExpandedPane` writes the order in a separate `set` from the replan

**Where** `model/canvasActions.ts:374-375`.

**Observed** Two sequential `set` calls: the order exchange, then
`commitPaneTransition(planPaneExpand(get(), ...))`. The store publishes an
intermediate state in which `layout.order` is swapped and every rect is stale.

**Impact today: none observable.** React 18 batches both writes inside the
pointer-event handler, and `planPaneExpand` cannot return null on this path:
`removeNode` (`engine/reducers/layoutState.ts:107-115`) filters `order` and
`nodes` together, so `order.includes(id)` implies a node exists, and expanded
mode implies at least two open panes.

**Why it is still worth naming** It runs against the convention the file states
for itself. `commitReorder` (`canvasActions.ts:425-429`) folds the order edit and
the replan into a single `set`, and `restorePaneAtIndex`
(`canvasActions.ts:340-342`) carries the comment "Seed, splice to the drop index,
and plan in one set: a single replan, so the pane never flashes at the tail before
its slot". `swapExpandedPane` is the third writer of `layout.order` and the only
one that does not follow it. If `planPaneExpand` ever grows a null branch, the
order swap sticks with no replan and the canvas is left inconsistent.

**Shape of the fix** Build the exchanged layout locally, pass it into
`planPaneExpand` as part of a synthesized state, and commit once.

**Caveat** Latent fragility, not a live bug. Verified as unreachable today.

---

## 7. Two comment nits

**a.** `dnd/paneDndCallbacks.ts:19-21`. The reflow left an orphan:

    // the expanded hero, or commits the order once via movePaneOrder. dnd-kit
    // owns activation, the
    // over target, Escape cancellation, and the in-drag visuals.

Line 20 ends on "the". Cosmetic, but the comments in this file are otherwise
hand-set prose.

**b.** `interactions/dnd/drop-targets.css:18-22`. The block comment that
introduces the cursor language still enumerates only "grabbing while moving, copy
over a delivery target". The new `swap` / `alias` rule at lines 36-40 is
undescribed, while its counterpart `dnd/dragCursor.ts:3-5` was updated to mention
the alias cursor.

---

## Checked and clean

Recording what was inspected and found correct, so the owner knows the scope.

- **`gridFit` scoring refactor is behaviour preserving.** `penalty = -log(score)`
  exactly, so `argmin penalty == argmax score`. The old relative epsilon
  (`score > bestScore * (1 + TIE)`) maps to the new absolute log-space epsilon
  (`penalty < bestPenalty - TIE`) to first order, and the old symmetric aspect
  band `Math.abs(score - bestScore) <= TIE` is reproduced exactly by the
  `A || (B && C)` structure, since the first disjunct already covers the lower
  half of the band.
- **`placeGrid` reproduces both old placement loops exactly.** `rowCount` via
  `Math.min(cols, len - row * cols)` equals the old
  `row === lastRowIndex ? count - row * cols : cols` on every row, and the
  centred last row resolves to the same `margin + (usableW - rowWidth) / 2`
  offset. `rowOffsetX` correctly closes over the post-expansion `cellW`.
- **`exchangePaneOrder` semantics match the hero-swap requirement.** Verified by
  hand on [A(hero),B,C,D]: dropping C on the hero yields [C,B,A,D], the remainder
  becomes [B,A,D], the hot-spot occupant B is untouched, and A lands in C's old
  slot. The self-swap and unknown-pane guards are both present and tested.
  Reversible: swapping back restores the original order.
- **Delivery keeps precedence over swap in both the preview and the release.**
  `resolveCanvasDragTarget.ts:38-64` and `paneDndCallbacks.ts:126-131` order the
  branches identically, and both resolve the target through the same
  `paneIdAtWorldPoint` hit test, so the cursor and the commit cannot disagree.
- **The collision override is sound.** `SortablePane.tsx:26` registers the hero
  with `disabled: { draggable: liftDisabled, droppable: false }`, so the hero is a
  live droppable even though `CanvasWorkbench.tsx:98-101` keeps it out of
  `sortablePaneIds`. `dndSpace.ts:130-134` can therefore see it as the hit and
  return the active pane as its own `over`, which is the same technique the
  delivery target already uses two blocks above. The active pane is in
  `SortableContext.items`, so `overIndex === activeIndex` and no sibling shifts.
- **`expandedPaneId === activeId` is double guarded.** `paneIdAtWorldPoint`
  excludes the active pane, so `hoverId` can never equal `activeId`, and
  `swapExpandedPane` returns early on `expandedPaneId === paneId` anyway.
- **The expand frame no longer overflows.** grid-fill's frame is the full
  remainder region, so `composeExpandFrame` resolves to exactly `viewport.height`
  rather than growing it, which is the improvement over the grid-overflow
  remainder it replaces.
- **`CanvasDragEffect` gained `swap` and every consumer handles it.**
  `dragCursor.ts:12-13` maps it to the alias cursor, `useCanvasDropTargets.ts:299`
  maps it to a native `move` (there is no native swap effect), and
  `dragSessionStore.ts:54` compares `operation` so a place-to-swap transition on
  the same pane still repaints the overlay.
- **No dangling references to the deleted strategy.** No `hero-grid`, `heroGrid`
  or `leftRatio` anywhere in `src`, apps, or `docs/`. `grid-overflow` survives
  only as its own still-registered strategy and its own tests.
- **The `grid-overflow` crossed min/max repair is pre-existing.** The hunk adds
  the explaining comment and a characterization test; `Math.min`/`Math.max` were
  already there. The new test does not fail before the PR, which is correct for a
  characterization test but worth knowing when reading the diff.

---

# Re-review at b5927f4a

Read only re-review at exact head
`b5927f4adb068c60410be77a34259765430b3d28`, one commit
(`fix(canvas): harden grid layouts and hero swaps`) on top of the reviewed
`22a85d7e`. 12 files, +167/-75. Local HEAD matches the stated SHA and
`git status --porcelain` is empty, so the tree is the one the builder gated.

**Verdict: blessed at b5927f4a.** All seven findings are closed, several more
thoroughly than proposed. No new findings. I made no executable change, so the
builder's gate evidence stands unre-run.

## Disposition of each finding

**1. Hot spot prominence — closed as accepted behaviour, comments corrected.**
Stuart accepted the existing layout. `grid.ts:68-71` now reads "Order keeps the
slot's occupant stable. A one-pane partial body row may match its footprint at
larger pane counts", and `strategies/gridFill.ts:15-17` drops "never demote" for
"later counts preserve the hot-spot occupant while stretched partial rows consume
the remaining width". Both statements are true of the code as written. The
contract and the behaviour now agree, which was the requirement.

**2. `swapExpandedPane` test — closed, and the test is sound.** New at
`canvasStore.test.ts:453-489`. I checked it against the trap of asserting an
intermediate: it asserts three observable end states (`expandedPaneId`, the
exchanged `layout.order`, and the hot-spot pane's rect byte-identical across the
swap), never that a collaborator was called.

I initially misread the fixture as two panes, which would have made the "hot
spot" the incoming pane and the rect assertion vacuous or wrong. It is not.
Instrumented run of the real store confirms three open panes and a genuine third
pane in the hot spot:

    ORDER        ["session-picker","transcript:abc","resource:abc:r1"]
    HOTSPOT      session-picker   (=== incoming? false)
    RECT BEFORE  {"x":886,"y":48,"width":666,"height":440}
    ORDER AFTER  ["session-picker","resource:abc:r1","transcript:abc"]
    RECT AFTER   {"x":886,"y":48,"width":666,"height":440}

So the assertion exercises exactly the invariant: the two named panes exchange
slots, the third pane's rect does not move by a pixel. The probe was a throwaway
test file, run and deleted; the tree is clean.

**3. Duplicated fold — closed, and proven equivalent.** `grid.ts:47-69`
introduces a typed generic `selectGridColumns<TPlan>` taking `candidateFor`
(returning null to skip a candidate) and `penaltyFor`. Both `fillGridColumns` and
`gridFit.ts::selectColumns` now call it. The `Math.max(1, bestCols)` clamp moved
into the shared fold, which reaches grid-fit for the first time; that is a no-op
there, since grid-fit's `candidateFor` never returns null and `planGridFit`
returns early on `count === 0`.

Equivalence proven by differential sweep, old fold transcribed verbatim from
`22a85d7e` against the real new `selectGridColumns`, over viewport width x height
x gap x margin x targetAspect x both packing modes x n in 1..24:

    grid-fit column selection: 172800 cases, mismatches=0

**4. Dead tie branch — closed.** `cols < bestCols` is gone from both call sites.
The comments now describe the actual mechanism rather than a branch:
`grid.ts:45-46` "Candidates are visited from fewer to more columns, so an equal
penalty and row count keeps the earlier candidate without another branch", and
`gridFit.ts:117-119` matches. This is the correct fix: the loop direction is now
stated as load-bearing, which it is.

**5. Negative geometry — closed, and harder than proposed.** Rather than a single
region clamp, `grid.ts:167-179` adds `partitionGridAxis(span, count,
preferredGap)`, which clamps the span, collapses to the whole span at count 1, and
clamps the gap itself to `span / (count - 1)` so gaps can never overrun the axis.
`fillGrid` routes every axis partition through it, `hotH` is clamped to the
region height and `hotGap` to what remains. `strategies/gridFill.ts:44-45` and
`strategies/singleRow.ts:35` clamp at their own boundaries too.

Verified by differential sweep over region width x height x gap x targetAspect x
n in 1..20:

    fillGrid sweep:      21600 cases, cols/rows mismatches=0, rect mismatches=41
    degenerate sweep:     1764 cases, negative/NaN rects=0
    containment sweep:    escapes=0

All 41 differing layouts are exactly the cases where the old code emitted a
negative dimension; a classifier pass confirms 41 of 41 and zero unexplained
diffs. So the hardening changes only the geometry that was already broken and
leaves every valid layout bit-identical. Both new boundary tests
(`gridFill.test.ts:97` and `index.test.ts:22`) fail against the old code, which I
confirmed independently through the sweep rather than by mutating the tree.

**6. Two-set order write — closed, better than proposed.**
`canvasActions.ts:372-375` now builds the exchanged layout locally and passes
`{ ...state, layout }` into `planPaneExpand`, so `commitPaneTransition` publishes
one merged `set`. This matches `commitReorder`'s `planCanvasLayout({ ...state,
layout: ordered })` shape exactly. It also removes the latent failure I named:
if `planPaneExpand` ever returns null the order exchange is simply discarded,
because nothing was written before the plan.

**7. Comment nits — closed.** The orphaned wrap at `paneDndCallbacks.ts:20` is
reflowed onto one line, and `drop-targets.css:20-22` now names the alias cursor
over the hero swap target. Two stale comments I had not flagged were also
corrected on their own initiative (`CanvasPaneDnd.tsx:21` and
`CanvasWorkbench.tsx:95-96` no longer say "side column" or "delivery-only"), and
the store test name at `canvasStore.test.ts:407` now says "grid fill" rather than
"grid overflow", matching `EXPAND_REMAINDER_STRATEGY_ID`.

## New findings

None.

Two optional notes, neither worth a cycle and neither a defect:

- `strategies/gridFill.ts:44-45` clamps the region to non-negative and
  `grid.ts:117-118` clamps it again inside `fillGrid`. Defensible as a boundary
  guard at the point the region is constructed plus an invariant in the primitive
  that owns the geometry; equally defensible to keep only the latter.
- The single-row boundary test lives in `index.test.ts`, whose describe block is
  "layout strategy auto-discovery (extensibility proof)". It does reach the
  strategy through `listLayouts()`, so it is not misplaced, but single-row has no
  test file of its own and this is the only geometry assertion in that file.

## Evidence reused, not re-run

The builder owns, at this exact SHA on this clean tree: failing-before boundary
tests, 120 focused tests passing, canvas `tsc` and Biome passing, `just check`
passing, and `just test` passing including frontend 1580, desktop 204 and Python
4468. I made no executable change, so per the brief I did not re-run those. My
own checks at this SHA were investigative, not gates: the new swap store test run
in isolation (1 passed), one throwaway instrumented probe (run and deleted, tree
verified clean), and three differential sweeps importing the real modules from the
scratchpad.
