# Cubicell SVG 3D Grok: artful type on one face plane

**Agent:** Grok creative scout  
**Branch / tip:** `feat/stencil-build` @ `66b4d8d` (`feat(scene): render seeded face stencils`)  
**Scope:** read only. No code or repo writes.  
**Output contract:** how far artful typography and *apparent* 3D can go on **one** Cubicell face using form only SVG masks, the two Cubicell controlled regions, polarity, motion, camera, and the current face plane.

**Hard exclusions (brief):** cube arranged glyphs, rounded cube geometry, generic text layers, imported SVG appearance.

**Core conclusion:** The live face stencil model already supports a serious monochrome and dual rail typography of *partition*, not of *mesh*. Optical extrusion, negative space lettering, bevel shade systems, anamorphic plane reads, and kinetic depth are in reach as authored form plus role choreography. True volumetric type, multi mask stacking, and live outline morphs are the first honest breaks.

---

## 1. Grounded current model

What is actually on this branch (not proposals).

### Authored face figure

`src/domain/cube.ts`

```ts
type CubeFaceFigure = {
  color: CubePartColor;           // theme | black | white | accent
  fit: "margin" | "bleed";
  region: "form" | "field";
  stencilId: StencilId;           // sha256:... content address
};
```

Face still owns `color`, `opacity`, `visible`. Figure is optional. Unmarked faces stay a single role.

### Two regions, Cubicell controlled

`src/scene/faceStencilShader.ts` mixes **two** resolved colours by one coverage sample:

| Authored `region` | Coverage (atlas R) paints | Uncovered area paints |
| --- | --- | --- |
| `form` | figure colour | face `color` |
| `field` | face `color` | figure colour |

Both colours resolve through `resolveCubePartColor` and workbench face lightness deltas (`scenePolarity.ts`). SVG fill never reaches the GPU. That is the product rule made mechanical.

### Form only SVG

`src/scene/stencilAtlas.ts` rasterizes seeded SVG alpha into a fixed **2048² R8** atlas, **16 slots × 512²**, gutters 1. Field default assets (manicure) invert alpha at atlas write so field source still stores a coherent coverage channel. Helioy is form default, margin; manicure is field default, bleed.

### Fit today

`fit` is authored, packed into the instance attribute (`fitFlag = 32` in `faceStencilShader.ts`), and seed defaults differ. The fragment path does **not** yet change UV scale from margin vs bleed. Treat margin/bleed as **authored intent with a dormant UV hook**, not as proven visual behaviour on this tip. Experiments that need true margin padding or edge bleed scale sit at the edge of *current model* and *minimal extension*.

### Face plane and UV frame

`createCubeFacePlanes` builds unit planes on cube faces. `tests/stencilOrientation.test.ts` pins exterior readable UV frames per face:

| Face | U | V | Outward normal |
| --- | --- | --- | --- |
| front | +X | +Y | +Z |
| back | −X | +Y | −Z |
| left | +Z | +Y | −X |
| right | −Z | +Y | +X |
| top | +X | −Z | +Y |
| bottom | +X | +Z | −Y |

Type reads upright from outside. There is no per face UV offset, rotation, or scale in authoring.

### Motion and polarity available without new fields

| Lever | Owner | What type can use |
| --- | --- | --- |
| Scene polarity black/white | `scene.polarity` | Invert rails; `theme` figure or face colour flips with contrast |
| Figure colour pin | `figure.color` | black/white/accent hold identity across polarity; theme follows |
| Face colour pin | face `color` | Same vocabulary for the other region |
| Figure colour morph | `canTweenCubeFaceFigureColor` when stencilId, region, fit match | Soft role pulse without cutting form |
| Discrete figure cut | stencil/region/fit change | Hard type state change on transition |
| Opacity | face opacity | Fade field or whole plane; not per region |
| Camera pose | orthographic head on, 45°, free orbit, tracks | Square head on is the truth view; orbit reveals planar lie |
| Cube placement | offset, rotation, scale | Whole cube kinetic; form stays glued to the plane |
| Seeded stencils | Helioy, Manicure only in atlas map | Content address stubs; capacity 16 |

### What is not on the face path

No second mask, no SDF, no multi layer, no UV transform knobs, no stroke vs fill channels, no depth offset of form, no cell lattice text on the face, no rounded edge silhouette ownership of type, no imported paint.

---

## 2. What “apparent 3D” means here

On one flat unlit plane, depth is a **lie told by partitions and motion**. The honest vocabulary:

1. **Value stack** — nested outlines or stepped coverage that read as bevel, shade, or extrusion under flat light.  
2. **Polarity stack** — two roles that invert under black/white, creating push/pull mass.  
3. **Anamorphic stack** — form drawn for a privileged camera pose; collapses when the cube turns.  
4. **Kinetic stack** — time swaps region, colour, opacity, or camera so depth appears only in change.  
5. **Topology stack** — form that continues across a shared edge when two faces meet, implying a ribbon or volume the geometry does not have.

Anything that needs a second coverage field, a Z offset mesh, or real glyph extrusion is past this vocabulary.

---

## 3. Concept catalog

### 3.1 Current model (shippable with new SVG forms + existing knobs)

**C1. Optical extrusion (stacked silhouette)**  
SVG is a family of nested outlines of one letter (outer shell, mid band, core counter). Authored as a single coverage field with stepped solid rings (not greys: greys become soft anti alias, not separate roles). With only two roles, extrusion is achieved by **spatial nesting**, not by many colours: form = shell, field = face, counters cut back to field. Classic sign painter “shade” becomes a second solid offset path inside the same stencil, still one alpha.

**C2. Inline / outline constructions**  
Open counters and inline strokes as pure coverage. Form region = stroke letter; field region = reverse letter on a solid face. Same stencil, flip `region`, and the letter becomes a hole. Polarity then decides whether the hole is night sky or paper cut.

**C3. Negative space lettering**  
Manicure already proves field identity: the figure is the *absence*. Typography of cutouts (a face sized “H” window, a word that is only the space between bars). Decisive for Cubicell: the mark is not a logo stamp; it is a **partition of the cube’s mass colour**.

**C4. Bevel shade as dual solid**  
Classic monochrome lettering: main face of the letter plus a hard offset shade band as one compound path. Under orbit the shade stays coplanar (lie intact). Under polarity swap with pinned black figure and theme field, shade mass inverts relative to the stage. No second colour channel required if shade and face share one role and the cube face supplies the other.

**C5. Head on square type poster**  
Orthographic front view is a perfect poster plane. Design the SVG as a full face poster letter (bleed) or a margin seal (margin intent). Camera detent to face normal is the intended read; free orbit is the product’s honesty check.

**C6. Kinetic polarity type**  
Timeline: polarity flip + figure colour morph between accent and theme while stencil and region hold. The letter does not move; the world around it does. Depth cue is figure ground reversal, a known poster technique (Albers, Swiss monochrome posters) performed by Cubicell rails rather than art direction software.

**C7. Face to face continuity (authored, not automatic)**  
Author two stencils that meet at a shared edge so a stroke continues from front to right when both faces are marked. UV frames are exterior readable, so continuity is a **design constraint** on how strokes hit the edge of the 512 tile, not a shader feature. Camera orbit makes the continuous band read as a wrap; head on reads as two posters.

**C8. Anamorphic plane letter**  
Draw the letter pre distorted so that from a 45° keypad view it reads as upright type, and from head on it shears. Pure coverage. Uses camera language already in product. No new fields.

**C9. Counter as window (opacity + field)**  
Field region letter on a translucent face: counters (or the field region) show through to whatever is behind the cube in the lattice. Apparent depth is *real occlusion of other cubes*, not fake extrusion. Still one plane.

**C10. Micro kinetic offset via cube motion**  
Hold the stencil fixed; animate cube `offset` or small rotation. Parallax against the lattice and camera creates depth for a flat mark the same way a painted sign moves on a truck. Form stays honest.

### 3.2 Minimal extension (small, local, still “one plane / form only”)

**M1. Honest fit UV**  
Implement margin inset and bleed scale in the fragment UV path already packing `fitFlag`. Unlocks seal vs full face poster without second atlas. Extension: shader + maybe authored inset scalar later.

**M2. UV transform knobs on figure**  
`rotate` (90° steps first), `mirror`, optional `scale` / `offset` in face UV. Enables typesetting a single letter stamp into corners, stacking repeated marks by authoring several faces differently, and anamorphic fine control without redrawing SVG.

**M3. Second coverage channel or dual slot sample**  
Two atlas slots referenced by one face (shell + shade, or fill + inline) with one progress or fixed layering rule. Still form only, still two *roles*, but three *regions* by stacking. Crossfade between stencils also unlocks letter morphs that today hard cut.

**M4. Greyscale coverage as height proxy (kept form only)**  
Allow soft alpha ramps in the atlas (not hard 0/1) and map mid values with a fixed two stop mix, or treat mid as a third role later. Optical soft bevel without a third authored colour if both ends of the ramp resolve to the existing two roles with a smoothstep. Risk: anti alias vs intentional ramp must be product named.

**M5. Per region opacity or face opacity split**  
Today opacity is whole face. Splitting figure vs field opacity lets counters open onto the interior void while shells stay solid. Touches domain + shader; still one plane.

**M6. Atlas SDF encode (optional generator)**  
Same R8 page, distance field in the channel, threshold in shader. Thin typographic strokes survive zoom better than binary alpha. Still form only; still two roles. Generator cost, not model break.

**M7. Seeded type stencil pack**  
Not a model change: a closed set of letterform and punctuation partitions designed for 512 tiles, exterior UV, and edge continuity. Product unlock without domain growth. Capacity 16 is a hard ceiling today; a type pack must be curated or the atlas policy expands (page size or multi page is a larger decision already named in render scouts).

### 3.3 Model breaking (name them so they stay out of the first type pass)

**B1. Real extrusion / mesh type**  
Tessellated glyph depth, rounded geometry, bevel meshes. Fights instancing and confinement; belongs to a different product fantasy.

**B2. Cube lattice spelling (pixel font grids)**  
`CUBICELL.md` and `TYPOGRAPHY.md` already own this path as *cells*, not face masks. Powerful, but it is not “one face”. Explicitly out of this scout’s frame.

**B3. Imported appearance**  
SVG fill, stroke colour, gradients, filters entering the face. Violates form only; collapses polarity authorship.

**B4. Multi material layered face stack**  
Several coplanar quads with depth bias per letter part. Program and z fight debt; breaks the single face atom.

**B5. Live outline geometry morph**  
True stroke interpolation between glyphs needs either dual coverage crossfade (M3, borderline) or path morph engines. Full path morph is out.

**B6. Selectable figure subregions**  
Selecting the “counter” of a letter as a part. Domain says figure is not a selection subject; keeping that is correct.

**B7. Perspective correct type on non planar or curved faces**  
No curved faces in the atom.

---

## 4. Where the art actually lives

### 4.1 The two role budget is a feature

With only form and field, the designer is forced into poster logic:

- Which mass is the letter?  
- Which mass is the cube skin?  
- Which pin survives a polarity flip?

That is a stronger typographic instrument than a free colour SVG on a cube. The Helioy default (form, accent, margin) and Manicure default (field, black, bleed) are two different *theories of mark*: stamp vs carve. Type should ship with both theories.

### 4.2 Apparent depth techniques that respect the budget

| Technique | How with two roles | Camera / motion ally |
| --- | --- | --- |
| Extrusion | Nested solid rings in one stencil | Head on sells; orbit exposes flatness (honest) |
| Drop shade | Offset duplicate path, same role | Slight cube yaw sells cast |
| Inline | Thin inner contour | Zoom and DPR stress atlas (512 known) |
| Reverse | `region: field` | Polarity flip as performance |
| Window | Field + face opacity | Lattice behind supplies real depth |
| Anamorph | Prewarped SVG | Keypad 45° as privileged pose |
| Wrap | Edge matched pair of stencils | Orbit around shared edge |
| Pulse | Figure colour tween | Score / state transition |

### 4.3 Prior art (mature, optional anchors)

Not prescriptions; calibration for taste.

- **Sign painting shade systems** — monochrome letter + hard shade band; maps to C4.  
- **Swiss / mid century poster cutouts** — letter as hole in a field; maps to C3 + field region.  
- **Albers nested value** — depth from nested partitions without perspective; maps to C1.  
- **Anamorphic facade lettering** (architectural, Felice Varini adjacent) — maps to C8.  
- **Kinetic typography in motion graphics** — meaning in time; maps to C6 / C10 without leaving the plane.  
- **Japanese monochrome stencils and family crests** — form only, high recognition at low region count; maps to curated stencil packs (M7).

Avoid as defaults: extruded 3D text demos, plastic bevel CSS, and cube pixel fonts (those are either B1 or B2).

---

## 5. Eight concrete visual experiments

Each experiment names setup, which category it stresses, and a **decisive owner test**: a single observation that passes or fails without debate.

### Experiment 1 — Shell extrusion “E”

**Category:** current model  
**Setup:** One cube, front face. Stencil: capital E as three nested solid outlines (outer, mid, counter remaining field). `region: form`, `figure.color: black`, face `color: white`, polarity black stage. Orthographic front.  
**Owner test:** From the head on detent, a stranger names “extruded E” before “flat outline”; after a 45° yaw, they still recognize E and correctly say it is painted on the face, not a solid prism.

### Experiment 2 — Field cut “O” window

**Category:** current model  
**Setup:** Stencil of a thick O where the counter is transparent in source and `region: field` so the O ring is face colour and the counter + exterior use figure colour or vice versa. Place a second cube behind on Z. Front face opacity ~0.85.  
**Owner test:** Counter shows the rear cube’s edge or colour; rotating the camera preserves the O as a hole in the front plane, not a decal floating in space.

### Experiment 3 — Polarity pin poster

**Category:** current model  
**Setup:** Helioy style form letter with `figure.color: accent` and face `color: theme`. Animate only `scene.polarity` black ↔ white.  
**Owner test:** Accent letter identity holds across the flip; theme field inverts; no SVG colour appears; thumbnail and workbench agree on roles (artifact rails vs workbench lightness still differ by design, but partition topology matches).

### Experiment 4 — Anamorphic “A” for 45°

**Category:** current model  
**Setup:** SVG of A pre skewed so the front orthographic view looks sheared and the standard keypad front right 45° view looks upright.  
**Owner test:** At the intended detent the A is legible upright; at pure front it is wrong on purpose; no other face carries type.

### Experiment 5 — Edge wrap stroke

**Category:** current model (dual face, still planar)  
**Setup:** Front and right faces share a continuous horizontal bar that meets the shared vertical edge within one atlas pixel of the tile edge on both stencils. Orbit around the vertical edge.  
**Owner test:** During orbit the bar reads as one band wrapping the corner for at least 30° of motion without a visible jump larger than the edge thickness of the cube’s own edge part.

### Experiment 6 — Kinetic shade pulse

**Category:** current model  
**Setup:** Bevel shade letter (C4). Hold stencil and region. Morph `figure.color` accent ↔ white on a looped state transition; face colour pinned black.  
**Owner test:** Form never pops or crossfades to another silhouette; only role luminance moves; transition kind stays colour tween (not discrete cut) per `canTweenCubeFaceFigureColor`.

### Experiment 7 — Margin seal vs bleed shout (fit honesty)

**Category:** minimal extension if UV fit is dormant; current if implemented  
**Setup:** Same letterform asset, two cubes side by side: `fit: margin` vs `fit: bleed`.  
**Owner test:** Bleed letter kisses or crosses the face edge; margin letter keeps a readable empty frame on all four sides. If both look identical on `66b4d8d`, the experiment **fails as current model** and becomes the acceptance test for M1.

### Experiment 8 — Dual sample crossfade “H” → “I”

**Category:** minimal extension (M3)  
**Setup:** Two stencils, H and I, same advance width in the tile. Author a transition that soft mixes coverage rather than discrete cut.  
**Owner test:** Mid transition shows a readable intermediate partition (bars dissolving), not a hard cut frame and not a material or program thrash (fixed `cubicell-face-stencil-v1` key, zero new programs across the morph).

---

## 6. Decision guide for owners

| Desire | First answer |
| --- | --- |
| Beautiful type on a cube face soon | Curated form only letter stencils + form/field + polarity (C1–C6). No domain change. |
| Seal vs full face control | Prove or implement M1 fit UV. |
| Soft letter morphs | M3 dual sample; do not invent path morph first. |
| Words as structure | Separate track: cell typography (`TYPOGRAPHY.md`), not face masks. |
| Plastic 3D logos | Decline (B1/B3). Confinement is the product. |
| Wrap around type | Author edge continuous pairs (C7/Exp 5); optional UV helpers (M2) later. |
| Thin strokes at extreme zoom | M6 SDF or higher slot res; measure before multi page atlas. |

### Sequencing suggestion (not a plan commitment)

1. **Art pack on current model** — five to eight letter experiments (Exp 1–6) as seeded or project stencils within the 16 slot budget.  
2. **Fit UV honesty** — Exp 7 as gate.  
3. **UV transforms** — only if wrap and corner seals need them.  
4. **Dual sample** — only if performance language demands soft type morphs.  
5. Keep cell typography as the path for readable multi letter words in space.

---

## 7. Technical claims checklist (branch evidence)

| Claim | Evidence |
| --- | --- |
| Two regions only | `cubeFaceFigureRegions = ["form","field"]`; shader mix in `faceStencilShader.ts` |
| Form only | Atlas writes alpha / inverted alpha; figure RGB from instance attr, not SVG |
| Fixed atlas 16×512 in 2048 R8 | `stencilAtlas.ts` constants + tests |
| Figure colour can tween when id/region/fit match | `canTweenCubeFaceFigureColor` |
| Else discrete cut | `morphChannel` on figure field; scene morph figure map |
| Exterior readable UVs | `tests/stencilOrientation.test.ts` |
| Fit packed, UV behaviour unproven in fragment | `fitFlag` set in `writeFaceStencilAttribute`; fragment uses region for colour only |
| Opacity is whole face | single `instanceOpacity` path |
| Seeded exemplars | Helioy form/margin/accent; Manicure field/bleed/black |
| Unlit face planes | `MeshBasicMaterial` face instances |
| Polarity rails | `scenePolarities` / `workbenchScenePolarities` |

---

## 8. What requires another mask, layer, or real geometry

| Effect | Needs |
| --- | --- |
| Three independent colour regions on one face | Second coverage or third role (extension or break) |
| Soft silhouette morph between letters | Dual sample (M3) or path engine (B5) |
| Physical letter depth / rounded prism type | Real geometry (B1) |
| Multi letter word as spatial object | Cell typography (B2), not face SVG |
| Painted gradients from file | Imported appearance (B3) |
| Selectable counters | New selection subject (B6) |
| Curved type on bent surfaces | Non planar faces (B7) |

---

## 9. Closing

Cubicell’s face stencil is not a texture slot waiting for logos. It is a **two role partition instrument** glued to an exterior readable plane, driven by polarity and time. Artful typography on that instrument is optical, poster, and kinetic: extrusion as nested coverage, letter as hole, shade as offset solid, depth as camera lie and lattice truth through windows.

The far edge of *apparent* 3D without leaving the model is **edge continuous multi face authorship + polarity performance + anamorphic camera privilege**. The first wall is not taste; it is **one coverage sample and a dormant fit flag**. Climb that wall before inventing geometry.

**Core conclusion (one line):** Apparent type depth on Cubicell is already a two role form craft (cut, stack, invert, orbit); soft morphs and honest margin/bleed are the only small extensions worth wanting before a separate cell typography track owns real words in space.
