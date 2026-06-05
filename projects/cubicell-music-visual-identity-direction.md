# Cubicell music visual identity direction

Date: 2026-08-07
Status: direction captured before further product work
Repository: `/Users/alphab/Dev/LLM/DEV/helioy/cubicell`
Implementation worktree: `/Users/alphab/Dev/LLM/DEV/helioy/cubicell/.claude/worktrees/stencil-build`

## Product truth

Cubicell is a spatial layout and choreography engine with addressable surfaces.

The cubes provide structure, hierarchy, orientation, rhythm, reveal, camera, and motion. Faces can carry meaning. The face stencil experiment proved that imported form can live on a face while Cubicell retains control of colour, polarity, composition, and movement.

Shape authoring remains outside the product boundary. Cubicell already has its shape: cubes. Adding general shaping, rounded geometry, or a second content primitive would multiply selection, rendering, persistence, animation, and interaction systems.

## Validated capability

Hands-on owner testing of `feat/stencil-build` at `66b4d8d` concluded that addressable face content has substantial creative potential.

The experiment supports seeded Helioy and Manicure marks through the existing face controls and render pass. Full unit and Chromium gates, production build, budget checks, and live dev and preview flows passed. GPU evidence showed one face draw, fixed shader identity, one atlas texture, and no program or texture churn during stencil edits.

The current figure is a two-role colour partition on a zero-thickness face plane. It can carry outlined typography, logos, marks, negative space, and art-directed optical depth. It cannot occupy the cube interior or produce geometry-based silhouette and occlusion.

## Typography correction

Typography should arrive as content carried by a face, not as cubes arranged into crude glyphs and not as a peer text primitive.

Whole letters, words, wordmarks, titles, numbers, diagrams, and composed title cards can arrive as outlined SVG paths. Cubicell owns their spatial layout, choreography, contrast, reveal, and timing. Live font layout and general text editing are deferred until repeated use proves they are necessary.

The three-family SVG and 3D scout synthesis is recorded at:

`/Users/alphab/.mdx/projects/cubicell-svg-3d-synthesis.md`

Its principal conclusion is that strong optical 3D typography is available within the current planar model. Literal extrusion requires a real contour geometry layer, even if a small state field describes it.

## Product home

Music visual identity is the chosen validation wedge.

The recurring input is a track, artist and track name, logo or mark, optional artwork, mood, and duration. The recurring outputs are:

- a full music visual;
- a seamless loop;
- a vertical social clip;
- a title or brand reveal;
- a live VJ scene;
- a consistent visual identity across those formats.

AI-assisted music increases the number of tracks produced without a corresponding supply of coherent visual identity. Cubicell can occupy the space between generic visualisers, inconsistent generated video, static artwork with effects, and expensive bespoke motion design.

VJ remains the purest expression of the engine, while release visuals and motion identity broaden the practical market.

## Validation campaign

Focus on output before expanding capability.

Create three complete pieces for three materially different tracks using the current engine, typography and marks on faces, camera, choreography, polarity, and existing transitions. Derive a full visual, loop, vertical clip, title reveal, and live scene from each project.

The campaign must answer:

1. Do three tracks produce three genuinely different visual identities?
2. Does Cubicell remain enjoyable and surprising on the third piece?
3. Can a creator reach publishable output quickly?
4. Does the constraint produce authorship or repetition?
5. Would a creator return for the next release?

If every result converges on the same Cubicell demonstration, the gimmick diagnosis is confirmed. If repeated use produces distinct work, the engine has instrument-level depth.

## Scope discipline

Freeze general capability work during validation.

Do not build speculative audio analysis, live typography, a font system, general SVG import, geometry extrusion, SDF relief, multiple atlas pages, new shapes, rounded cubes, or a full VJ suite. Use concierge inputs and the current engine. Productise only workflow breaks that repeat across real pieces.

Maintain one figure state owner, one content identity, one face derivation, one render path, and one delivery path. DRY remains non-negotiable.

## Current repository status

`main` remains unchanged at `7d5e942`.

`feat/stencil-build` is committed through `66b4d8d`:

- `241f03c` owns cube face state through the shared part-state owner;
- `04f12b2` adds Stencil Library assets and persistence;
- `ce81207` adds optional face figure state;
- `004e63a` repairs figure state integrity and colour tweening;
- `66b4d8d` renders seeded face stencils through the existing face pass.

One high persistence finding remains: selecting a bundled seeded stencil resolves through the bundled registry without adding the selected Stencil asset to the project Library. This does not invalidate visual testing, but it must be repaired before merge and persistence approval.

The paused Shell E experiment has uncommitted changes in the stencil worktree, including `assets/marks/shell-e.svg`, seed and option changes, focused tests, and exact budget rebaselines. It was paused because it repeated the already validated face-display capability rather than advancing product-home validation. Preserve these changes until explicitly kept or discarded.

## Decision

Commit to a concentrated validation campaign around music visual identity while keeping the engine general underneath. The next work is complete creative output for real tracks, not broader engine capability.
