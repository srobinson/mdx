# Cubicell Theory — Lens 3: Unasked-For Reach

**Seat:** shapes worktree agent  
**Question (Stuart):** artistic and stickiness capabilities of what we have built, and where we can take it  
**Lens:** what the existing primitives already unlock that nobody has asked for  
**Mode:** exploration, not engineering. No code. No PRs. No builds.

---

## Framing

Do not answer the theory on its own terms. Look at the machine.

The machine already has:

- per-instance shader deformation on edges (round / chamfer / sharp, shape size)
- morph channels between authored states (numeric lerp, color tween, discrete cut)
- a transport (playhead, BPM-adjacent timing substrate)
- camera captured per state
- selection as a query language over parts (faces, edges, shell, interior, junctions)
- occupancy and burial resolution between neighbours
- polarity inversion (black / white workbench)
- screen-space-stable edges (one CSS pixel coverage floor)

Shared geometry facts: cube = 6 face quads + 12 edge bars, instanced, no corner geometry; MeshBasicMaterial with no lighting; edges hold minimum screen thickness; shape reads clean to ~0.4; no recursion and no media content; flat cell array.

The secret is recombination. Each primitive alone is a feature. Stacked, they make a medium.

Spinor lesson from the source text: a full rotation can return you to the same orientation while carrying a phase. Cubicell already does something like that to geometry. Morph a state into itself through burial, polarity, and camera and the viewer is back where they started, changed. That is stickiness. Not more tools. More meaning from the tools already present.

---

## Ranked artefacts (cheapest first)

Cost scale (for this seat only):

- **A** — author only: existing UI, states, score, export
- **B** — tiny glue: a preset, a template scene, a one-shot export recipe, a panel binding already almost there
- **C** — small product surface: one new interaction or recording mode, no domain redesign
- **D** — real new subsystem (listed only to mark the cliff; out of scope for "already unlocks")

### 1. Polarity flip as a finished short film  
**Artefact:** a 8–20 second loop where one structure is authored twice (or once, polarity toggled mid-score). Black world becomes white world without changing mesh topology. Edges stay legible because of screen-space coverage. Camera is part of the piece, so the flip is not a theme switch; it is a cut to an inverted universe that is still the same building.

**Why unasked:** polarity is a workbench preference. Nobody asked for "use polarity as narrative."

**Cost:** A. Two states or one polarity keyframe in the score, camera track, export. Zero new code.

---

### 2. Reveal archaeology (burial as plot)  
**Artefact:** a solid 3×3×3 (or denser) cube. Play starts fully closed. Over time, outer shells hide or thin; interior cells go `revealed`. The piece is the act of excavation. The camera orbits or crawls along a path that only makes sense once voids open. Selection queries already know shell vs interior; the audience watches burial logic become choreography.

**Why unasked:** burial exists so the editor does not draw occluded faces. Nobody asked for "burial is the story."

**Cost:** A–B. Author visibility / opacity morphs + camera. Optional B: a "reveal interior" score cue if not already expressible as state morphs.

---

### 3. Seam typography (letters from flat-seams and convex edges)  
**Artefact:** typefaces built only from cube assemblies where letter strokes are edges that survive junction ownership (flat-seam and convex), and counters are interiors that stay buried or open. Morph between letterforms: "A" state → "B" state. Thickness and shapeSize animate the stroke weight; chamfer/round is the optical finish. Export as looping glyph animations for title cards.

**Why unasked:** edges and junctions are geometry plumbing. Nobody asked for a type foundry that only draws what neighbours leave visible.

**Cost:** A for hand-built glyphs; B for a library of 10–26 letter templates shared as structures. No new renderer.

---

### 4. State-as-shot cinematic score  
**Artefact:** a piece that is only three to five authored states with locked cameras (each state owns its view). Transport plays them as a film: hard cuts or morph blends are the edit. The structure barely moves; the camera and which faces are opaque do all the work. Like a storyboard that is also the final movie.

**Why unasked:** camera-per-state is for authoring convenience. Nobody asked for "the camera is the cast."

**Cost:** A. Already the State + score + export path. Stickiness: people share 15-second clips, not "cube files."

---

### 5. Morph-phase identity (return with a phase)  
**Artefact:** a loop that begins and ends on the same pose and camera, but mid-loop flips polarity, reveals an interior cell, and rounds every edge to 0.4 then back to sharp. Mathematically "home"; emotionally not. Title it like a spinor: *720° of the same building*.

**Why unasked:** morph is for going A→B. Nobody asked for A→¬A→A as the product.

**Cost:** A. Pure authorship discipline.

---

### 6. Selection-query stage lights  
**Artefact:** a live performance mode (or recorded score) where selection queries pulse part sets: all convex edges, all top faces, all interior cubes. Those parts brighten, thicken, or shapeSize-pulse on the beat. The structure becomes a drum machine whose pads are geometric predicates.

**Why unasked:** selection query language is for editing. Nobody asked for it as an instrument.

**Cost:** B–C. If score can already drive part opacity/thickness by target, B. If needs a "query → pulse" modifier, C. Still no new geometry.

---

### 7. Neighbour-owned duets  
**Artefact:** two (or more) cubes share an edge. The shared edge has one visual owner via claim priority. Morph which cube "wins" the edge color and thickness over time. The shared line becomes a conversation: who gets to draw the crease. Scale to a wall of cubes where ownership propagates like a wave.

**Why unasked:** edge ownership is anti-z-fighting. Nobody asked for ownership as drama.

**Cost:** A if ownership follows existing priority and you morph colors/thickness/opacity on competing cells; C if you need explicit ownership keyframes (would be new).

---

### 8. Screen-stable wireframe cinema at any zoom  
**Artefact:** pieces designed to be watched full-screen then in a phone notification thumbnail. Because edges never drop below one CSS pixel, the silhouette survives brutal scale. Series of "icon-scale" sculptures that are still readable at 64px export and still elegant at 4K.

**Why unasked:** coverage is a readability fix. Nobody asked for "design for both postage stamp and billboard from one authoring."

**Cost:** A. Authoring convention + export sizes. Stickiness: works as avatar, sticker, and installation still.

---

### 9. Negative-space choreography (gaps as dancers)  
**Artefact:** lattice gap overrides animate open and shut. Cubes barely move; the air between them does. Burial and exposure flip as gaps close. A piece that is mostly empty grid breathing. Seam reveal (when enabled) is the ghost of the breath.

**Why unasked:** gaps are layout. Nobody asked for air as the protagonist.

**Cost:** B if gap morphs exist on the score path; C if gap animation needs a dedicated channel. Domain already has gap overrides and seam model.

---

### 10. Double-cover camera (two views, one structure)  
**Artefact:** two states, same cells, two cameras 180° or one full orbit apart, morph or hard cut. The structure is "the same" and the viewer feels two covers of one rotation group. Pair with polarity so cover A is black-world, cover B is white-world.

**Why unasked:** multi-state cameras exist. Nobody asked for a deliberate double-cover aesthetic.

**Cost:** A.

---

### 11. Soft-edge weather  
**Artefact:** global shapeSize and treatment morph across a city of cubes: sharp winter → chamfered rain → round fog. Faces stay flat (no lighting); the weather lives only in the edge cross-section. Because edges are instanced and shaded per instance, a skyline can "melt" without moving a single cell center.

**Why unasked:** edge shape is a per-edge craft control. Nobody asked for climate as a structure-wide morph channel.

**Cost:** A–B. All-edges bindings already exist; score must drive them.

---

### 12. Interior solitary confinement film  
**Artefact:** camera starts outside a dense assembly. Over the piece, everything outside one buried cell fades or hides; the camera ends inside a single cube's void (or on a revealed interior cell). Isolation mode / reveal already exist for editing buried cubes. Make them the climax of a short.

**Why unasked:** isolate is an editor affordance. Nobody asked for "editor isolate as the last act of a movie."

**Cost:** B–C. May need score-driven visibility of non-focus cells and camera inside bounds; mostly authored.

---

### 13. Query-driven generative posters (human still the author)  
**Artefact:** not full gen-AI. A ritual: author a seed assembly, run a fixed set of selection queries (shell edges, concave junctions, top faces), apply a recipe (thicken, round, polarity flip, camera fit), export stills. Each run is a poster variant. Stickiness is the recipe deck, not the model.

**Why unasked:** queries edit. Nobody asked for query packs as a poster press.

**Cost:** B for recipe docs and templates; C for a one-click "poster pack" exporter.

---

### 14. Beat-synced burial (transport as excavator)  
**Artefact:** on each bar, one more shell layer opens or one more interior reveals. The beat is literally removing occlusion. Pair with edge shape pulses on the off-beat. Export as music video without video textures: pure MeshBasic cubes.

**Why unasked:** transport is for piece motion. Nobody asked for transport as a digger.

**Cost:** B if score cues can step visibility sets; C for bar-quantized reveal helper.

---

### Higher cliff (named only so we do not pretend they are free)

- Recursion / cubes-inside-cubes content: **D**, and currently none  
- Image / video / text on faces: **D**, and currently none  
- True lighting / materials: **D** (would change the medium's honesty)  
These are not unasked-for reach of the *current* machine. They are different machines.

---

## What the medium secretly is

Cubicell is not a CAD toy that happens to animate. On current primitives alone it is closer to:

1. **A silhouette instrument** — edges that never die at distance, faces that can vanish by burial.  
2. **A phase machine** — morph and polarity return you home with a difference.  
3. **A queryable sculpture** — selection language is latent stage directions.  
4. **A camera-native film form** — states are shots; transport is the cut list.  
5. **A neighbour drama** — ownership and burial make social geometry without characters.

No media on faces is a feature here, not a lack. The piece cannot hide behind a texture. Stickiness comes from recognizable motion of mass, crease, and void.

---

## Stickiness without new code

People stick to tools that let them finish something others can feel in fifteen seconds.

Cheap stickiness path already open:

1. Author a 4-state piece with cameras.  
2. Morph A→B→C→A with one polarity flip and one interior reveal.  
3. Export a silent loop.  
4. Ship it as the product's own trailer.

That loop is the demo of unasked-for reach. It does not require shape recursion, media, or lighting. It only requires treating burial, polarity, camera, and morph as artistic materials rather than editor utilities.

---

## Single best idea

**Burial archaeology shorts:** dense assemblies that excavate themselves on the transport while the camera owns each reveal.

**Why best:** reuses the most "invisible infrastructure" (occupancy, burial, reveal, edge coverage) as the aesthetic; produces concrete shareable artefacts; cost stays in A–B; cannot be faked in a generic cube editor that lacks neighbour resolution.

**Cost:** A–B (authoring + optional reveal cue sugar).

---

## Done

Lens 3 complete. File: `~/.mdx/projects/cubicell-theory-reach.md`
