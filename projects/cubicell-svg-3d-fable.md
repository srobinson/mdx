# Cubicell: SVG-derived form on a cube face, and the space between faces

Fable scout report, read-only, at `feat/stencil-build` 66b4d8d (2026-08-07). Source citations are from that tree.

## Verdict on Stuart's belief

"A face mask cannot occupy the space between cube faces" is **true as a description of 66b4d8d and false as a law of the model**.

Today the figure is fragment-only color arithmetic on the face plane. `faceStencilShader.ts:38-54` mixes form/field colors per fragment of an instanced `PlaneGeometry(1,1)`; the figure has zero geometric extent, so it literally cannot occupy any volume. That is an implementation choice of v1, not a model invariant.

Three facts from the source refute the belief as a constraint:

1. **The cube interior is empty and cell-owned.** Faces are shells placed at `±halfSize` on each axis (`cubeGeometry.ts:51-76`), edges are frame boxes on the perimeter (`cubeGeometry.ts:82-107`). Nothing renders inside. A figure extruded inward collides with nothing, needs no neighbor negotiation, and stays inside the cell's bounding box, so spatial queries and visibility resolution remain valid.
2. **Each face already carries a full 3D frame.** The instance matrix is `cellMatrix × transform(face.position, face.rotation, [w, h, 1])` (`cubeInstances.ts`, face instance construction). Any geometry, not just a flat plane, can ride that frame. Depth is a scale-z away.
3. **Real space exists on both sides of a face.** Inward: the empty shell interior. Outward: the grid gap, default `0.5` cell units (`grid.ts:33`), which is seam-layer territory and therefore the riskier side.

The elegant framing: the face is a window, and the model already guarantees the room behind the window is empty. Perceived depth (parallax, interior mapping, cutout) is *honest* here in a way it rarely is in games, because no real geometry will ever contradict the illusion.

## Current implementation, precisely

- **Domain**: `CubeFaceFigure { color, fit: margin|bleed, region: form|field, stencilId }` (`cube.ts:43-48`), an optional inherited field on face state with a morph channel: color-tween when only color changes, discrete-cut otherwise (`cube.ts:61-62`, `canTweenCubeFaceFigureColor`).
- **Assets**: two seeded SVGs (Helioy, Manicure) content-addressed by sha256 (`seededStencils.ts`). Atlas capacity 16 slots.
- **Atlas**: SVG rasterized via canvas to an R8 alpha channel, 512² per slot in a 2048² `DataTexture`, linear filter, **no mipmaps**, 1px gutter (`stencilAtlas.ts`). Field-region sources are pre-inverted at rasterization.
- **Shader**: a `MeshBasicMaterial` onBeforeCompile patch; per-instance vec4 attribute packs figure color in rgb and `slot + regionFlag(16) + fitFlag(32)` in alpha. Fragment mixes figure color against the face's diffuse by sampled coverage.
- **Editor**: one control, `face.stencil` (None/Helioy/Manicure). Region, fit, and figure color exist in the model but have no bindings yet; they arrive via the stencil's `defaultFigure`.
- **Material context**: unlit (`MeshBasicMaterial`, `toneMapped: false`), translucent face mesh does not write depth (`instancedPartMeshCore.ts:141`). Camera is perspective with logarithmic depth, orthographic optional.

Two observations worth flagging upstream (not defects in the brief's scope):

- **`fit` is encoded but never consumed.** The shader strips the fit bit (`mod(code, 32)`) and reads only region; margin and bleed render identically today. Either the UV-inset pass is pending or this is declared-but-unhonored state. Worth an explicit decision before the flag calcifies.
- **No mipmaps on the atlas** means distant faces will shimmer/alias on busy marks. Invisible with two clean logos at typical camera distances, visible the moment dense typography lands.

## Perceived depth versus real geometry

The question for bold 3D typography is which of four depth strategies to reach for. They stack.

| Strategy | What it buys | Geometry change | Model change |
|---|---|---|---|
| Shaded relief (SDF normals + painted light) | Bevels, emboss, letterpress; typography that reads dimensional | none | none |
| Parallax / interior recess | Figure visually floats *between* the faces; motion parallax on orbit | none | none |
| Cutout (fragment discard) | Face becomes a literal stencil; you see through the letterforms into the cube | none | one enum value |
| Real inward extrusion | True silhouettes, correct occlusion against edges/faces, casts across the interior | extruded prism per stencil | one numeric field |

Key perceptual facts:

- Fake relief and recess survive orbiting cameras well up to roughly 45° grazing angles; the cube helps because faces turn away before the illusion degrades. In orthographic projection the eye vector is constant, so parallax reads flatter head-on but still shifts as faces rotate.
- The silhouette is the tell. Painted depth never breaks the face's rectangular outline. If Stuart wants letterforms whose *edges* read 3D against the world (the "bold impressive" register), only extrusion or cutout deliver it.
- Cutout is the cheapest true 3D: discard where coverage is low and the space between faces becomes visible *through* the mask. Combined with the opposite face's color or a second stencil behind, this is the strongest single image the current architecture can produce.

## Typographic art direction

The two-color form/field system with polarity-aware color resolution (`resolveTreatedPartColor`, face lightness deltas) is already a stencil-press idiom: think Josef Müller-Brockmann poster, not textured decal. Direction that fits the product:

- **SDF-crisp letterforms** at any zoom, with optional hairline outline or offset shadow from the same distance field. This alone moves stencils from "logo sticker" to "typographic surface".
- **Letterpress/emboss duality mapped to polarity.** Light polarity = debossed (carved in), dark = embossed (raised). One perceptual metaphor, driven by the existing theme system, zero new user-facing concepts.
- **Region flip as a graphic beat.** Form↔field inversion is a one-bit change with a discrete-cut morph channel already defined. A stencil flipping polarity across a morph is a strong, cheap motion signature.
- **Bleed vs margin as compositional stance** once fit is honored: margin = mark, bleed = pattern/texture. The Manicure seed (field+bleed) is already reaching for the second register.
- **Opposing-face duets**: same stencil on front and back faces, one form, one field-inverted; with recess or cutout the pair reads as a single object suspended in the cube.

## Tiers

**Possible today at 66b4d8d (shader/atlas work only, zero model change)**
- SDF atlas (same R8 format, same 512² slots) with crisp edges, outlines, glow.
- Shaded relief: normals from SDF gradient plus a fixed light direction painted in the fragment; consistent with the unlit aesthetic.
- Parallax recess / interior mapping: figure appears sunk between the faces.
- Cutout via discard *could* ship shader-side by repurposing coverage, but honestly belongs behind a model value (below) so it is authored, not hacked.

**One small model extension**
- `region: "cut"` third value: face discards where the form is (or isn't). One enum value, one shader branch, panel option. Real see-through.
- `figure.depth?: number` (signed; negative = recessed): scene renders an extruded prism riding the existing face frame, clamped inward to the cell interior. This is the "mask occupies the space between faces" refutation made literal. Render cost: extruded geometry is per-stencil, so it breaks the single-atlas instancing and costs one instanced draw per (stencil, depth) class; fine at 16-stencil scale.
- A `figureMotion` knob (UV drift/scale tween) for kinetic type; feel constants belong in config/pref knobs per project convention.

**Model-breaking (name and fence off)**
- Figures as free objects between cubes (figure leaves face ownership; new aggregate, new selection/persistence surface).
- Multi-cell volumetric typography (one glyph carved through several cells; breaks cell-local face state).
- SVG-driven lattice composition (stencil coverage decides cube visibility across the grid, cells as pixels). Notably this one *preserves* the cube/face model per cell; it breaks only the "one face" framing, and might be the most Cubicell-native big idea of the three. Adjacent feature, not this track.

## Motion and polarity opportunities

- Figure color tween already flows through the morph system (`color-tween` channel, `figures` tween map in `cubeInstances.ts`); showcase it.
- **Coverage wipe**: animate a threshold across the SDF so letterforms grow from their stroke skeletons on arrive, dissolve on depart. Fits the existing arrive/depart morph-class structure (`morphSettings.ts`); needs one per-instance progress scalar.
- **Press morph**: with `figure.depth`, animate depth 0 → target on arrive; the mark stamps into the cube. A natural fifth `MorphForm` sibling to grow/slide/drop/turn.
- Polarity switches re-resolve figure colors already; adding the emboss/deboss light-direction flip makes theme toggling a depth event, not just a palette event.

## Failure modes

1. **Minification aliasing** (no mips, linear filter, 1px gutter): sparkle on distant dense type. SDF plus fwidth-based antialiasing largely cures it; otherwise mipmapped atlas with wider gutters.
2. **Translucent faces do not write depth**: real extruded figures inside a cube whose faces are semi-opaque will sort wrongly at some angles. Extrusion work must decide depth policy up front.
3. **Cutout vs picking**: discarded fragments still raycast (selection hits the hole). Acceptable for v1, but it will surprise; document or filter by coverage in the hit path later.
4. **Discrete-cut popping**: any stencil/region/fit change hard-cuts mid-morph by design; more expressive figures make the pop more visible. The coverage wipe doubles as the cure.
5. **Grazing-angle breakdown** of parallax at steep angles; bound the parallax depth to a fraction of cell size and the cube's own face turning hides the worst of it.
6. **Atlas ceiling**: 16 slots and seeded-only resolution (`resolveStencilContent` falls back to `unresolved`). User-imported SVGs are the obvious next ask; the sha256 content addressing is already future-proof, the fixed atlas is not.
7. **Headless/thumbnail paths** skip rasterization (`canRasterizeStencils` guard): stencil-bearing thumbnails silently render figureless where canvas/Image are absent. Known and guarded, but any new depth pass must keep that guard.

## Six experiments, ranked by expressive gain vs product risk

1. **SDF atlas + shaded relief typography.** Crisp at all zooms, emboss/deboss with painted light, outline/glow variants. Gain: high (this is "bold impressive 3D typography" for most viewers). Risk: low; confined to `stencilAtlas.ts` + shader patch, no model change, no new user concepts.
2. **Cutout region.** `region: "cut"`, fragment discard; the face becomes a physical stencil revealing the space between faces. Gain: high; the single most striking proof that the belief is false. Risk: low-medium (picking surprise, edge antialiasing wants the SDF from #1 first).
3. **Parallax recess.** Figure reads as suspended midway between the faces; motion parallax on orbit. Gain: medium-high, compounding with #2 (recessed backing plane behind a cutout). Risk: low; shader-only, bound depth to ~0.25 cell.
4. **Real inward extrusion (`figure.depth`).** True 3D letterforms occupying the interior, correct occlusion against edges. Gain: highest ceiling, the literal refutation. Risk: medium; per-stencil geometry breaks atlas instancing, depth/translucency policy needed, morph integration ("press" form) is its own slice.
5. **Stencil-aware motion beats.** Coverage wipe on arrive/depart, region-flip cut, figure color tween showcase. Gain: medium; turns figures from decals into performers, feeds the transport/score system. Risk: low; rides existing morph channels plus one progress scalar.
6. **Kinetic figure (fit + UV animation).** Honor margin/bleed (closing the current dead flag), then tween fit and slow UV drift/rotation for living surfaces. Gain: medium; pattern-register expressiveness, resolves a latent model/shader divergence. Risk: low, but least dramatic on its own, and feel constants must land in knobs, not hardcoded.

Recommended spine: 1 → 2 → 3 are one continuous shader/atlas track with tiny model touches, and together they already deliver "figures occupying the space between faces" perceptually and literally (through the cutout). 4 is the flagship slice when the product wants silhouettes. 5 and 6 are polish multipliers that reuse everything above.
