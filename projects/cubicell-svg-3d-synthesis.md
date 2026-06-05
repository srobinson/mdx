# Cubicell SVG and 3D typography synthesis

**Sources:** `cubicell-svg-3d-fable.md`, `cubicell-svg-3d-gpt.md`, and `cubicell-svg-3d-grok.md`  
**Repository state surveyed:** `66b4d8d252fa` on `feat/stencil-build`  
**Scope:** one face figure, no implementation

## Verdict

The current face figure is a two role colour partition on one zero thickness plane. It can support strong typographic art through outlined SVG paths, compound silhouettes, negative space, polarity, transparency, camera, and motion. It cannot give the figure a silhouette, place figure surfaces between faces, or produce geometry based occlusion.

The apparent extrusion disagreement comes from mixing two kinds of cost:

| Question | Answer |
| --- | --- |
| How much authored state could request extrusion? | One optional depth value could be enough. |
| What renders literal occupied volume? | A contour geometry layer with caps, side walls, placement, occlusion, resource reuse, and transition policy. |
| Does the small field keep literal extrusion inside the current face model? | No. The field authors the request. The geometry layer fulfils it. |

Literal inward extrusion is therefore **model breaking** relative to the present single plane figure atom. Its persisted schema can still remain small and reuse the existing figure owner.

Fragment discard is a smaller, different claim. It can reveal real space behind the face, but it gives the figure no volume. Parallax and shaded relief remain shader based 2.5D. A translucent field can expose a rear cube through a plane, but it is not a literal aperture.

## Hard current model boundary

The present atom is:

`one face plane + one alpha coverage sample + two colour roles + one figure state owner`

Within that atom:

- The SVG supplies coverage only. Fill colours, strokes, layers, and semantic glyphs do not survive rasterisation.
- Typography must arrive as paths in an SVG. There is no live font layout or text primitive.
- Coverage selects form and field. It does not provide height, multiple materials, or independently selectable subregions.
- The shader changes colour only. It does not move vertices, discard fragments, write depth, or create side walls.
- `fit` is authored and packed, but has no proven visual effect at this head.
- The atlas has fixed capacity, linear filtering, and no mipmaps. Dense or distant type remains an unproved quality case.
- The face plane retains its rectangular silhouette and exterior readable UV orientation.

The first hard break occurs when the figure needs its own spatial surface, silhouette, or geometry based occlusion. Multiple masks, stacked coplanar layers, live glyph layout, and multi cell words also exceed this atom.

## Strongest typography available now

1. **Compound path optical extrusion.** Bake a hard offset shade or nested shell into one alpha mask. Head on, it can read as sign painted depth. Orbit truthfully exposes the plane.
2. **Letter as partition.** Use form and field as equal design roles. Counters, cut letters, and negative space can make the cube mass feel authored rather than decorated.
3. **Polarity poster.** Combine theme, black, white, and accent roles with pinned figure colour and polarity changes. This gives one stencil distinct identities without a new colour system.
4. **Transparent window composition.** Place another cube behind a translucent face and use the stencil partition to frame actual scene depth. The effect remains a transparent plane composition.
5. **Camera specific type.** Author anamorphic letterforms for a chosen orbit angle, or continue a stroke across adjacent faces. Both use current face instances.
6. **Kinetic type.** Tween figure colour and face opacity while moving or rotating the cube. The depth cue comes from time, parallax, and occlusion already present in the scene.

These directions are strongest when the SVG is treated as a deliberate two value composition. Greyscale detail, thin strokes, and colour rich source art fight the current raster and shader contract.

## Ranked experiment ladder

| Rank | Experiment | Label | Decisive question and gate |
| ---: | --- | --- | --- |
| 1 | **Shell extrusion E** | **CURRENT** | Add one path outlined capital E with a compound offset shell. Show it head on, then orbit to 45 degrees. Pass if Stuart immediately reads bold extruded type head on and accepts the planar reveal in motion. This is the fastest decisive user test. |
| 2 | **Polarity pin poster** | **CURRENT** | Use the same E with pinned black figure, theme field, and a polarity change. Pass if one asset produces two intentional poster identities while remaining recognisably Cubicell. Stop if the role choreography reads like a generic logo sticker. |
| 3 | **Field cut O with rear cube** | **CURRENT** | Put a contrasting cube behind a translucent face and author an O as negative space. Pass if scene depth through the composition is legible and useful. Describe the result as transparency through a plane. |
| 4 | **SDF relief and optical shade** | **MINIMAL EXTENSION** | Replace binary alpha interpretation with a distance field and derive a bevel normal or fixed offset shade in the existing face shader. Pass if type stays crisp and materially more dimensional at the target camera distances without a new draw or state concept. |
| 5 | **Authored discard aperture** | **MINIMAL EXTENSION** | Add one figure region treatment that discards the chosen coverage region in the existing face pass. Pass if seeing the cube interior is the desired product effect. Before adoption, resolve edge antialiasing, ray picking through discarded pixels, opacity, and depth behaviour. |
| 6 | **Literal contour extrusion** | **MODEL BREAKING** | Extrude the same outlined E from its SVG contour and place it from the existing face instance matrix. Test outward first so the opaque host face cannot hide it. Pass only if silhouette and occlusion under orbit add value that experiments 1, 4, and 5 could not supply. Inward volume additionally requires explicit host face cutout or hide semantics. |

The ladder should stop at the first accepted visual answer. Technical possibility alone is not a reason to climb it.

## Recommended next experiment

Run **Shell extrusion E** first. It requires one path outlined SVG and the current figure pipeline, so Stuart can judge the visual thesis directly. The head on and 45 degree pair answers two questions in minutes: whether bold typographic depth is desirable, and whether planar truth during orbit is acceptable.

If the first view fails, stop the face typography direction. If the first view passes and the orbit view also feels acceptable, ship the art direction without renderer expansion. If the orbit view fails specifically because the silhouette remains rectangular, proceed to literal contour extrusion. If the desired effect is looking into the cube, test the discard aperture instead.

## Stop rules

1. **One figure state owner.** Any accepted field extends `CubeFaceFigure` and its existing validation, codec, inheritance, morph, and render impact owner. Never add typography or extrusion state beside it.
2. **One content identity.** Typography remains an outlined SVG addressed by `stencilId` through the existing resolver and atlas. Never add live text, font layout, or a second text primitive to the face path.
3. **One face derivation.** Reuse the existing face instances, slot lifecycle, colour resolution, opacity, and transition data. Reject a second scene scan, transform loop, or figure store.
4. **One plane renderer.** Optical shade, SDF relief, parallax, and discard belong in `faceStencilShader` and its existing material composition. Reject extra coplanar quads and one material per glyph.
5. **One geometry consumer if approved.** Literal extrusion may consume the existing figure state and face instance matrices through the instanced mesh core. Reject a parallel renderer, per glyph React tree, or separate picking and visibility lifecycle.
6. **One delivery path.** An accepted result must reach the live scene and thumbnail through their shared owners. A thumbnail approximation cannot become a parallel visual implementation.
7. **No speculative framework.** Build only the next ranked experiment. Promote an effect to authored state after Stuart accepts its visual and interaction semantics.
8. **Geometry has a strict gate.** Approve literal extrusion only when silhouette or geometry based occlusion is an explicit requirement and the plane experiments have produced contrary evidence.

## Final resolution

A small field can describe inward depth. It cannot make the mask occupy space. Literal occupation starts at contour geometry, and that is a real rendering model extension even when the authoring API remains one number.
