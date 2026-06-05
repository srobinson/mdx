# Cubicell: rounded cubes as a perimeter style ("shell")

Status: decided 2026-08-17 by Stuart, after review of PR #180 (`feat/renderer-relief`).
Scope: this file is the authority for the reframe. Briefs cite it by path.

## What PR #180 built

A third authored part family, the cube "body": `CubeBodyState = { corners, radius, frameMargin, frameColor }`,
rendered as one shared `RoundedBoxGeometry` template re-radiused per instance in a patched vertex shader
(`src/scene/cubeBodyShader.ts`), with the six face openings discarded in the fragment shader. Faces are inset
panels. Edge segments are skipped at render time for rounded cells. A hardcoded directional light is applied
inside the body shader.

## Review findings that drove the reframe

Reproduced, not inferred:

1. A rounded cell can win a coincident edge claim (`src/domain/edgeClaimResolution.ts` `compareEdgeClaimPriority`)
   and then never draw it (`src/scene/cubeInstances.ts` skips segments for rounded cells). Two adjacent cells at
   zero grid gap, lower coordinate cell rounded: the four shared edges are drawn by nobody.
2. `applyCubeBodyStylePatch` is state relative. `set frameWidth 0.2`, `radius 0.3`, `radius 0.055` leaves
   frame width at 0.3, not 0.2. Persisted `set-cube-body-style` operations replay path dependently.

Confirmed in code:

3. `faceHitTargets` is emitted for every visible face of every cell, rounded or not, and `facePointerHandlers`
   is spread onto four layers; the raycaster has the picking layer enabled for the editor lifetime.
4. `src/control/studioSnapshot.ts` reports `edges.visibleCount` and `layer` from `cell.edges` for cells that
   never draw an edge.
5. `scripts/verifyMcpObservation.ts` compares `description.version` to the same constant the server exports.
6. `CubePartLayerSpec.picking` is read by nothing.
7. `cubeBodyStateOwner.hasValidFields` is not overridden, so `workbenchValidation/pose.ts` accepts
   `radius + frameMargin >= 0.5`.
8. `src/theme/scenePolarity.ts` documents that parts render unlit and that form cues (edge lightness delta,
   per face value ramp) are workbench only, so artifacts and thumbnails keep authored colours. The body shader
   hardcodes a view space light and `createCubePartLayerMesh` applies it to thumbnails too.

Design read: every defect sits on the seam between "body" and "edges", two overlapping concepts for one role,
the cube perimeter.

## Decisions (Stuart, 2026-08-17)

D1. Rounded is a **perimeter style**, not a third part. One perimeter, two styles: `wire` (twelve segments from
    per edge state, as today) and `shell` (the rounded band from the shared shader). The user facing word stays
    "Corners: Sharp / Rounded".
D2. **Frame width equals radius.** No separate width, no margin, no coupling. `frameMargin`, `frameWidth`,
    `getCubeFrameWidth`, and the clamping patcher go.
D3. **Frame colour is the cube's uniform edge colour** (`getCubeUniformPartColor` for edges), not a stored field.
    `frameColor` and its binding go. Frame opacity follows the same rule if it is needed at all.
D4. The body state shrinks to `{ corners, radius }`. Radius stays per cube and morphable.
D5. **The light leaves the shader.** It becomes a workbench only form cue in `scenePolarity.ts` next to
    `edgeLightnessDelta`, plumbed as uniforms. Artifact configs omit it, so thumbnails and export stay flat.
    Whether the same cue should shade sharp cubes is a later scene decision, not this branch.
D6. Shell cells **forfeit edge claims** at claim resolution, so a sharp neighbour inherits the shared edge.
    The render site drop in `cubeInstances.ts` is deleted, not kept as a second guard.
D7. Radius moves to **absolute world units**, like edge thickness, so corners stay circular on non cubic cells.
    The shader has `instanceMatrix` to divide out per axis scale.
D8. Face hit targets are emitted for **shell cells only**. `picking` on the layer spec is deleted.
D9. `verifyMcpObservation.ts` keeps a **literal** protocol version.
D10. Delivery: amend PR #180 in place. Reviewer sees one correct PR. Squash merge means the internal commit
     structure buys review legibility only.

## Known open items, not decided

O1. Two shell cells adjacent at zero gap have coplanar frame bands and no buried face culling. Sharp cubes get
    both. Expect z fighting on the shared band. Not rendered yet. Scout should say whether the buried face index
    already has a seam to hang shell band culling on.
O2. Whether the shell's square opening should become a rounded opening (SDF rounded rectangle discard, one line)
    so the panel corner matches the frame's inner corner. Taste call after Stuart sees it rendered.
O3. Docs: `MODEL.v2.md` and `ARCHITECTURE.md` still say two part families. Update as part of the branch.

## Gates

`pnpm check`, `pnpm test`, `pnpm test:browser`, `tsc -b`, `pnpm check:budget`. Budget ceilings re baseline
to the measured value at zero headroom. Integrator proves on both `pnpm dev` and `pnpm preview`.

## Surface-and-decide gate (2026-08-17, after scout report `cubicell-scout-shell-perimeter.md`)

Quality map dispositions. Refactor during S2: findings 1 (one mesh path via `geometryKind: "shell"` inside
`createInstancedPartMeshWithGeometry`), 4 (exact bucket dispatch), 7 (one named template radius), 8 (render
constants beside siblings, light to polarity), 10 (finish the spec indirection, do not stop halfway), 11
(thumbnails build by `spec.key`), 16 (hit target layer carries down/up handlers only). Dissolve under D2 to D4:
3, 5, 12, 13, 20. Delete: 2 (`picking`). Drive in S1: 9 (`impact.body` reindexes edges), 21 (radius schema per
A5, corner options derived from `cubeCornerStyles`, delete zero caller `asCubePartColor`). Constraint: 14
(`sceneMorph.ts` removes lines in S1, adds none).

Open decisions, resolved:
A1  extend `getCubeUniformPartColor` with a part filter; default part colour on mix; no new helper.
A2  shell colour tween derives from edge tweens; none when edges are mixed.
A3  radius stays in cell units like edge thickness; per axis division on the CPU in `createCubeCellInstances`;
    shader stays matrix free. Recorded deviation from D7's wording; D7's intent (circular corners on non cubic
    cells) is met.
A4  snapshot `bodyStyle: { corners, radius }`; authored edge counts stay; top level `version` dropped.
A5  domain bound finite and >= 0; UI schema owns the max; render clamps radius to half the smallest axis next to
    the panel inset so both agree.
A6  a shell quadrant leaves three structural claims, so the interior edge is drawn by the sharp winner; accept,
    name it in the forfeiture test.
A7  shell band culling and burial against a shell neighbour (O1 plus finding 19) are one follow up, "shell
    adjacency at zero gap", out of this branch. Integrator renders gap 0 so the artifact is seen.
A8  no render vocabulary rename; `body` is the one word across domain and render; "shell" is prose.
A9  shells stay opaque regardless of edge opacity; noted.
A10 (Stuart) gate: in edge pick mode a shell cell is not an edge target and `EdgeSection` shows nothing editable
    for it; edge state stays dormant and reappears on Sharp.
A11 (Stuart) keep `cube.layers` visible for shell cells; "Edges" on a shell means an empty frame.

Delivery: commits land on `feat/renderer-relief` on top of the existing three, one commit per slice, pushed to
PR #180 after each slice clears review; squash merge collapses them.

## S3 additions (2026-08-17, from the S2 review addendum)

A12 Shell draws only when `hasVisibleCubeEdges(cell)`; perimeter visibility is edge visibility under D1, so
    Layers=Faces on a rounded cell means bare panels, as on a sharp cell, and `getCubeLayerMode` stays true of
    the render. Hit targets follow the shell: a rounded cell with hidden faces but a drawn shell has six band
    targets; no shell and hidden faces is an invisible cube.
A13 Per axis unit radius guards a zero size axis (positive floor at the clamp site); no NaN in the attribute.
A14 One slot to part resolver in `InstancedPartMesh` (hygiene, no behaviour change).

Follow ups recorded, out of this branch:
F1  A7 shell adjacency at zero gap (coplanar bands, burial against a shell neighbour).
F2  Cross cube hover on click: `stopPropagation` on pointerup makes R3F cancel the far cube's hover with only
    near cube intersections in the event, so the guard clears to null; pre existing, closable by setting the
    front most intersected cube instead of null. Same family: R3F books every intersected instance so hover
    lands on the farthest cube along the view ray.
F3  Store version bump 13 to 14 in S3 for records written by the branch before S1 (not a follow up, recorded
    for the PR body).
F4  Neighbour slot yield keys on face pick planes, not on cube visibility: a sharp cell in edges only mode draws
    twelve visible segments yet emits no face planes, so it never yields a slot, which contradicts the yield
    rule's intent (`useCubeSceneInteractions.ts` around the `getFaceYieldDistance` check). Pre existing, widened
    in scope by A12 only in that the shell variant now behaves correctly. Out of this branch.
F5  A12's accepted cost: in face pick mode a click through a shell opening selects the hidden face behind it,
    because hit planes follow the shell rather than face visibility. Correct per A12; flagged for Stuart's eye.
F6  Should `ModifyTab`'s section follow `editor.pickMode` in general rather than `selection.kind`? The pick mode
    is the part family being edited, so the coherent model is pickMode chooses the section and the selection
    supplies the cubes. S3 commit 3 fixes only the shell dormant case to keep sharp cell behaviour identical.
    Stuart's call, out of this branch.

## Measured after S3 (2026-08-18, from Stuart's screenshots)

Two defects and two design facts, all measured on real WebGL through the production render path.

Defect, fixed in 914082e. Shell cubes were not watertight. `roundedPanelOutsetRatio` pushed panels 1e-3 along
their own normal, a vestige of the pre reframe design where the body drew a full box. Since the shader discards
the whole flat rectangle nothing was left to z fight, so the outset only opened a ribbon around every face
perimeter: hairlines at corners, a wedge at the silhouette, background through double sided layers from inside.
Panels now sit in the face plane with `roundedPanelSeamOverlap = 0.001` applied strictly in plane. Sealed
interior non white pixels went from 2262/2061/451 to 1/0/0 at radius 0.05/0.2/0.45. Stuart confirmed visually.

Defect, fixed in 1e6f8e9. An authored radius below the seam overlap made the panel inset negative, growing the
panel past its own face. Reachable through the command layer and through a cell axis thinner than twice the
overlap, though not through the slider. The inset floors at zero.

Fact: a rounded cube cannot mark its own folds through authoring. Measured in preview with media faces, a sharp
cube's twelve edges mark every fold at 250 sRGB levels over 100% of its length; a rounded cube's fold falls
inside a flat band and is unmarked over 97 to 98% of its length. Media only marks a fold where the artwork
happens to differ across it (7 to 48%). The workbench reveals folds through `bodyLight` across 29 levels;
artifact polarity omits it, so preview, thumbnails, and export show none. The unlit artifact policy is therefore
asymmetric: it works for sharp cubes because their form is authored geometry, and fails for shells because their
form is curvature. Open decision for Stuart, recorded as F7.

Fact: not defects, confirmed by measurement. Head on corner wedges are correct silhouette, zero background
pixels inside the analytic rounded square at any radius; the straight diagonal reading is the 4 segment corner
arc, whose chord spans 0.176 world units at radius 0.45 with sag under 2 px, matching prediction. Media shrink
is `1 - 2r`: artwork keeps 80% of face area at radius 0.05, 36% at 0.2, 16% at 0.3, 1% at 0.45. Band weight
against wire edges is 16x at an interior junction and 7x at the silhouette, and both are tunable by pairing
radius against authored edge thickness, as Stuart demonstrated.

F7  Should the shell band carry its shading in artifact polarity, as a scoped exception to the flat policy, so
    rounded cubes read in preview, thumbnails, and export? The alternative is that shells stay a workbench only
    form. Nothing else in the authored model can mark a fold on a shell.

## A10 correction (2026-08-17, S3 commit 3)

A10 was not true as shipped in S3 commits 1 and 2. Edge pick mode on a rounded cell recorded `pickMode: "edge"`
but preserved the prior selection, and `ModifyTab` mounts its section from `selection.kind`, so the panel kept
showing FaceSection and `PartSection`'s `dormantNote` was unreachable: dead code introduced by this branch.
Commit 3 mounts the edges section when pick mode is edge and the selected cube has no edge targets, so the
dormant note renders and A10 reads true. Sharp cell behaviour is unchanged in every pick mode.
