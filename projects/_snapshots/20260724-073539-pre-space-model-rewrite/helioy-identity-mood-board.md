---
title: "Helioy Mood Board & Image Reference Guide"
category: projects
tags: [helioy, identity, mood-board, image-prompts, phase-2]
created: 2026-03-15
author: image-prompt-engineer
status: production-ready
---

# Helioy Mood Board & Image Reference Guide

Production-ready image generation prompts refined against the locked brand strategy and design system. Every prompt uses exact color references from the token system and maps to specific brand touchpoints.

---

## Style Lock

These parameters apply to every prompt in this document unless explicitly overridden. They form the visual consistency layer.

### Global Generation Parameters

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| **Color temperature** | Warm (3200K-4500K equivalent) | Matches amber-gold palette, avoids cool cast |
| **Primary accent** | Amber-gold matching `#d4a54a` | Brand gold-500 |
| **Dark tones** | Warm charcoal matching `#1a1816` with amber undertone | Brand surface-0 |
| **Highlight ceiling** | Warm off-white matching `#f0ebe4` | Brand text-primary, never pure white |
| **Forbidden colors** | Cool blue, neon green, purple, pure black, pure white | Per brand anti-patterns |
| **Material finish** | Matte, brushed, translucent. Never polished metallic or chrome | Warm, not opulent |
| **Light quality** | Directional with visible source logic. No flat ambient fill | Structured light principle |
| **Noise/grain** | Subtle film grain (Kodak Portra 400 equivalent). No digital smoothness | Craft, not generated |
| **Post-processing** | Minimal. Warm grade, no split-toning, no HDR. Slight lift in shadows | Honest photography |

### Camera Defaults

| Parameter | Value |
|-----------|-------|
| **Lens simulation** | Prime lenses only (35mm, 50mm, 85mm, 100mm macro) |
| **Aperture feel** | f/2.8 to f/8 depending on subject. Controlled depth, not extreme bokeh |
| **Perspective** | Eye level or slightly elevated. No dramatic dutch angles |
| **Format** | Medium format digital (Phase One / Hasselblad rendering quality) |

### Negative Prompt Layer (apply to all)

```
No cool blue tones, no neon, no purple haze, no lens flare, no chromatic
aberration, no pure black (#000), no pure white (#fff), no glossy metallic
reflections, no digital smoothness, no HDR tonemapping, no gradient mesh,
no wireframe overlays, no circuit board patterns, no human figures, no text
overlays, no brand logos, no stock photography styling
```

---

## Category 1: Hero Imagery

Large-format images for website heroes, keynote slides, and campaign headers. These carry the brand at its most expressive. 16:9 or 21:9 aspect ratio.

### H1. Caustic Genesis (Primary Hero)

**Touchpoints:** Website homepage hero, conference keynote title slide, GitHub org banner

```
Extreme close-up photograph of golden caustic light patterns projected onto
a matte surface the color of warm charcoal (#1a1816). The caustics are
created by structured light refracting through a faceted crystalline form
just outside the frame. The interference patterns are sharp geometric shapes
with luminous edges that soften into the dark surface, rendered in amber-gold
(#d4a54a) with brighter convergence points approaching warm off-white
(#f0ebe4). The patterns suggest interconnected nodes and branching pathways
without being literal or diagrammatic. A subtle gradient from brighter
(camera left) to darker (camera right) creates depth. The dark surface has
a fine matte texture with a barely perceptible warm undertone, like slate
with amber dust. No visible light source, only the projected patterns.
Shot on 100mm macro lens at f/4, medium format sensor, shallow depth of
field with the sharpest caustic lines in the center third and gentle
softening toward edges. Kodak Portra 400 color rendering. Scientific
photography precision with fine art gallery presentation. Aspect ratio 21:9.
8k resolution.
```

**Variations to generate:**
- Tighter crop on a single convergence point (for social cards)
- Wider composition with more dark negative space camera right (for text overlay areas)
- Subtle animation reference: slow drift of the light patterns (for motion design team)

### H2. Crystallization Threshold (Secondary Hero)

**Touchpoints:** Product landing pages, blog post feature images, documentation site header

```
Macro photograph of a crystallization event in progress on a dark glass
surface tinted warm charcoal (#1a1816). The crystals are forming in
branching geometric patterns that grow outward from a central seed point.
Each crystal structure is lit from below by a warm amber light source
(#d4a54a), making the formations glow against the dark surrounding glass.
The boundary between crystallized and uncrystallized regions is sharply
defined, showing the phase transition as a visible edge. Dendritic branches
connect in hexagonal geometry. The crystal formations are amber and gold
with internal facets catching light at different angles. The uncrystallized
region is dark with a subtle warm sheen. Focus stacked for complete
sharpness across the crystal plane. The color palette is restricted to
amber (#d4a54a), deep gold (#b8912e), warm bronze (#8a6e1a), dark charcoal
(#1a1816), and warm off-white highlights (#f0ebe4). Shot at 5x
magnification on medium format with bellows extension. Scientific
microscopy aesthetic elevated to fine art. Aspect ratio 16:9. 8k resolution.
```

### H3. Solar Chamber (Atmospheric Hero)

**Touchpoints:** About page hero, brand story section, presentation chapter dividers

```
Architectural interior photograph of a circular room with dark concrete
walls tinted warm charcoal (#1a1816). A single oculus in the ceiling admits
a column of golden light. The light beam is visible through fine atmospheric
dust, creating volumetric rays in amber-gold (#d4a54a). Where the light
column strikes the dark floor, it illuminates a geometric brass instrument
or sculptural form that scatters the light into small caustic patterns on
the surrounding surface. The caustic patterns on the floor echo the
branching geometry of crystal formations. The walls are deep charcoal with
barely visible surface texture. The brass element catches warm highlights
(#e0b960) on its edges. The space feels both ancient and contemporary:
observatory precision, brutalist material honesty. Shot on 24mm wide angle
lens from ground level looking slightly upward through the light column
toward the oculus. The composition centers on the vertical axis of light.
Deep depth of field at f/11. Warm color temperature throughout, no cool
shadows. Inspired by the atmospheric quality of James Turrell's skyspaces
crossed with Tadao Ando's material directness. Aspect ratio 9:16 (vertical).
8k resolution.
```

---

## Category 2: Background Textures

Seamless or near-seamless textures for website surfaces, presentation backgrounds, and UI elements. These operate at low contrast and sit behind content. Must remain legible with text overlaid.

### T1. Dark Caustic Field (Primary Background)

**Touchpoints:** Website section backgrounds, presentation slide backgrounds, documentation page texture

```
Subtle caustic light pattern on a matte dark surface (#1a1816). The
caustic lines are rendered at very low opacity in muted amber-gold
(#3d3010 to #8a6e1a range), barely visible against the dark ground.
The pattern suggests a geometric network but reads as texture rather
than illustration at normal viewing distance. Uniform density across
the frame with no bright convergence points. The overall impression
is a dark surface with an embedded warm geometric grain, like looking
at a dark granite countertop that reveals subtle crystalline structure
under oblique light. Shot as a flat texture with even lighting, no
directional shadows, no vignetting. The texture must support readable
text overlay in warm off-white (#f0ebe4) at body size (16px equivalent).
Square format, 4096x4096px, seamless tileable.
```

### T2. Crystal Grain (Subtle Texture)

**Touchpoints:** Card backgrounds (surface-1 equivalent), elevated panel texture, email header backgrounds

```
Extreme macro photograph of a crystalline mineral surface in warm amber
tones. The crystal facets are tiny and uniform, creating a fine geometric
grain pattern. The surface color matches warm dark brown (#222018) with
facet highlights in muted gold (#8a6e1a). The texture is uniform and
non-directional, suitable for seamless tiling. Low contrast between the
facets and the ground. The impression is a sophisticated material texture,
like brushed bronze or fine-grained sandstone with golden mineral
inclusions. Even diffused lighting from directly above. No dramatic
shadows. No specular highlights brighter than #b8912e. Shot on macro
lens at high magnification, focus stacked for uniform sharpness. Square
format, 2048x2048px, seamless tileable.
```

### T3. Warm Paper (Light Mode Background)

**Touchpoints:** Light mode website surfaces, documentation light theme, print materials

```
Close-up photograph of handmade paper with a warm cream tone (#faf8f5).
The paper has visible fiber texture and slight surface irregularity that
catches subtle directional light from the upper left. The texture is warm
and organic without being rough or recycled-looking. Occasional slightly
darker fibers (#e6e2dc) create micro-variation. No watermarks, no visible
particles, no dramatic shadows. The light is soft and even with just enough
directionality to reveal paper surface texture. The overall feeling is
premium stationery, not craft paper. Shot with macro lens at f/8, even
illumination, color-calibrated. Square format, 2048x2048px, seamless
tileable.
```

---

## Category 3: Pattern Elements

Isolated pattern assets that can be extracted, vectorized, or composited into the graphic system. These generate the raw material for the caustic pattern library.

### P1. Caustic Network (Pattern Source)

**Touchpoints:** Extracted as SVG patterns, loading animations, divider elements, favicon texture

```
High-contrast photograph of caustic light patterns on a pure dark surface.
Golden light (#d4a54a) refracted through a multifaceted crystal creates a
network of interconnected geometric shapes on a dark matte surface (#1a1816).
The pattern shows clear geometric relationships: hexagonal clusters
connected by linear caustic lines, branching at 60-degree and 120-degree
angles. The lines vary in brightness from bright gold (#e0b960) at
convergence points to dim amber (#8a6e1a) at the thinnest connecting
filaments. The dark ground between patterns is clean and uniform. No
gradients, no atmospheric haze, no soft focus. Maximum sharpness and
contrast for clean extraction and vectorization. Shot on macro lens with
ring light providing the refractive source. Square format, 4096x4096px.
```

**Post-generation extraction notes:**
- Threshold at 40% brightness to isolate pattern from background
- Trace to SVG using centerline method for consistent stroke weight
- The resulting vector patterns become the brand's repeatable graphic system
- Animate by slowly translating the pattern on a loop (2-4 second cycle)

### P2. Single Facet Detail (Icon Source)

**Touchpoints:** Favicon, CLI prompt icon, npm avatar, app icon base, sticker design

```
A single geometric crystal facet photographed in isolation against a pure
dark background (#1a1816). The facet is a irregular polygon with 5-7 sides,
asymmetric but balanced, suggesting a fragment broken from a larger
crystalline form. The facet is translucent amber with internal geometric
lines visible (lattice structure) when backlit. Front lighting in warm gold
(#d4a54a) reveals surface facet planes. Edge lighting from behind creates a
thin bright rim (#e0b960). The interior lattice lines are finer and dimmer
(#8a6e1a). The facet appears to float on the dark ground with a subtle
caustic shadow beneath it projected in warm amber. The form is geometric
and constructible (built from straight lines and angles), not organic or
freeform. Shot on macro lens at f/5.6 against black velvet. Studio
lighting: one softbox front-right, one strip light behind for rim.
Square format, 2048x2048px.
```

**Post-generation notes:**
- This generates reference material for the logo designer, not the logo itself
- The facet geometry, internal lattice density, and edge character inform the Facet mark
- Generate 8-10 variations and select the one with the strongest silhouette at 16px

### P3. Caustic Divider (Linear Pattern)

**Touchpoints:** Section dividers, horizontal rules, progress bars, nav active indicators

```
A single horizontal band of caustic light on a dark surface (#1a1816).
The caustic pattern runs left to right across the full frame width,
approximately 40px tall in the center with the pattern fading to nothing
at top and bottom edges. The light pattern is amber-gold (#d4a54a) with
brighter nodes (#e0b960) spaced irregularly along its length. The pattern
has geometric structure (angular intersections, not smooth curves) but
reads as a luminous line at small scale. The dark surface above and below
is uniform and clean. Sharp focus throughout. No atmospheric effects. The
pattern should function as a decorative horizontal rule when scaled to
2-4px height while retaining visual interest when displayed at full
resolution. Aspect ratio 8:1 (wide horizontal strip). 4096x512px.
```

---

## Category 4: Material Studies

Close-up material references that define the brand's tactile vocabulary. These inform texture choices, illustration style, and physical brand applications (merchandise, packaging, environmental design).

### M1. Amber Resin Block

**Touchpoints:** Material reference for brand illustrations, merch design (acrylic awards, display pieces), packaging inspiration

```
Studio photograph of a polished rectangular block of dark amber resin,
approximately 80mm x 60mm x 40mm, positioned on a matte dark surface
(#1a1816). The resin is translucent with a warm amber tone (#d4a54a at
its thinnest, #8a6e1a at its thickest). Suspended inside the resin is a
delicate geometric wireframe structure made of fine gold wire, suggesting
a polyhedron or molecular lattice frozen mid-formation. The wireframe is
incomplete, as though captured during the act of crystallizing. Studio
lighting: large softbox overhead and slightly behind creates a gradient
through the resin block, revealing the internal wireframe through
transmitted light. A second small light from camera left provides surface
definition. Subtle caustic patterns appear on the dark surface beneath
the block where light passes through. The polished resin faces show
sharp reflections. Shot on 85mm macro lens at f/5.6, medium format.
Product photography precision. The feeling is preserved intelligence
given physical form. Aspect ratio 4:5 (slightly tall). 4096x5120px.
```

### M2. Hammered Gold Surface

**Touchpoints:** Texture reference for UI surfaces, premium tier branding, presentation accents

```
Full-frame close-up of a hammered metal surface in warm gold (#d4a54a base
tone). Geometric facets created by controlled hammer strikes, each facet
approximately 8-12mm across, catching directional warm light at slightly
different angles. This creates a mosaic of value shifts from deep bronze
shadow (#8a6e1a) through gold midtone (#d4a54a) to warm highlight
(#e0b960). Some facets are more polished, others retain a brushed matte
finish, creating subtle texture variation within the pattern. The surface
curves gently, suggesting a form larger than the frame. Single large
softbox from upper camera right. No background visible. Edge-to-edge
material. The finish is warm and matte overall, not mirror-polished or
jewelry-like. Shot on 100mm macro with focus stacking for uniform
sharpness. Square format, 4096x4096px.
```

### M3. Obsidian Slab

**Touchpoints:** Dark surface reference for UI backgrounds, material contrast studies, environmental design

```
Still life photograph of a slab of polished obsidian, approximately 200mm
wide, resting at a slight angle on a dark concrete surface (#1a1816). The
obsidian surface is glossy and deep black-brown (#1a1816 with slight warm
undertone). Where the slab is thinnest at its chipped edges, warm amber
light (#d4a54a) transmits through, revealing internal flow patterns frozen
in the volcanic glass. A single beam of directional warm light enters from
upper frame left, creating a sharp light/shadow boundary across the slab
surface. The glossy obsidian reflects a suggestion of the light source as
a warm blur. The concrete surface beneath has fine aggregate texture in
warm gray (#2e2b24). Minimal composition: one slab, one light source,
one surface. Shot on 50mm lens at f/8, medium format. The mood is
geological time compressed into an object. Aspect ratio 3:2. 6144x4096px.
```

---

## Category 5: Atmospheric References

These images are not for direct brand use. They define the emotional register and environmental context that the brand inhabits. Reference material for the design team.

### A1. Geode Interior

**Touchpoints:** Reference only. Defines the "dark exterior, luminous interior" brand mood.

```
Cross-section photograph of a large geode split open, positioned against
a dark backdrop (#1a1816). The exterior is rough dark stone. The interior
cavity is lined with crystalline formations in warm amber and gold tones
(#d4a54a, #e0b960, #b8912e). The crystals are angular and geometric,
catching studio light that enters the cavity from camera left. The
deepest interior crystals are darker (#8a6e1a), while those near the
opening catch more light and glow warm gold. The contrast between the
rough dark exterior and the luminous crystalline interior is stark. Shot
on medium format with 80mm lens at f/11 for deep focus. Ring light
positioned to illuminate the cavity interior. The image captures the
feeling of discovering structured beauty inside something that appears
plain from the outside. Aspect ratio 1:1. 4096x4096px.
```

### A2. Golden Hour Library

**Touchpoints:** Reference only. Defines the warmth-precision balance of the brand personality.

```
Interior photograph of a minimalist private library or study at golden
hour. Warm amber sunlight (#d4a54a equivalent) enters through a single
tall window, casting long geometric shadows across a dark wood desk and
bookshelves. The walls are warm charcoal (#2e2b24). The desk surface is
dark walnut. Books are arranged with intention, not excess. A single
brass instrument (compass, protractor, or geometric tool) sits on the
desk catching the golden light. Dust particles are barely visible in the
light beam. The space is minimal but not empty. Every object has a reason.
The mood is quiet competence: someone works here who cares about precision
and craft. Shot on 35mm lens at f/4, standing in the doorway looking in.
Shallow enough depth of field to soften the far bookshelf. The color
palette is constrained to warm charcoal, amber gold, dark wood, and
brass. Aspect ratio 16:9. 8k resolution.
```

### A3. Workshop at Night

**Touchpoints:** Reference only. Defines the "maker identity" and craft dimension.

```
Interior photograph of a craftsperson's workshop at night, lit by a
single warm task lamp. The workspace is organized and intentional: tools
in designated places, surfaces clean but showing evidence of use. The
dominant materials are dark wood, matte metal, and stone. The task lamp
casts warm amber light (#d4a54a) in a defined pool, with the rest of the
space falling to warm charcoal darkness (#1a1816). One wall has geometric
diagrams or technical drawings pinned to it, barely visible in the
peripheral light. The atmosphere is focused solitude. Not loneliness.
Productive quiet. Shot on 50mm lens at f/2.8, focused on the lit
workspace, background soft. The image conveys: someone builds things
here with their hands and their mind. The space is the physical
manifestation of the Helioy brand personality. Aspect ratio 3:2.
6144x4096px.
```

---

## Usage Mapping

| Prompt | Primary Touchpoint | Secondary Touchpoints | Format |
|--------|-------------------|----------------------|--------|
| **H1** Caustic Genesis | Website homepage hero | Keynote title slide, GitHub banner, OG image | 21:9, 16:9 crops |
| **H2** Crystallization Threshold | Product landing pages | Blog feature images, docs header | 16:9 |
| **H3** Solar Chamber | About page hero | Brand story section, presentation dividers | 9:16 vertical |
| **T1** Dark Caustic Field | Website section backgrounds | Slide backgrounds, email footers | Square, tileable |
| **T2** Crystal Grain | Card/panel textures (surface-1) | Elevated panel texture | Square, tileable |
| **T3** Warm Paper | Light mode backgrounds | Print materials, letterhead | Square, tileable |
| **P1** Caustic Network | SVG pattern library source | Loading animations, dividers | Square, extractable |
| **P2** Single Facet | Logo/icon reference material | Favicon, CLI icon, npm avatar | Square |
| **P3** Caustic Divider | Section dividers, hr elements | Progress bars, nav indicators | 8:1 horizontal |
| **M1** Amber Resin Block | Brand illustration reference | Merch design, packaging | 4:5 |
| **M2** Hammered Gold | UI texture reference | Premium tier, presentation accents | Square |
| **M3** Obsidian Slab | Dark surface reference | Environmental design | 3:2 |
| **A1** Geode Interior | Mood reference (team only) | n/a | Square |
| **A2** Golden Hour Library | Mood reference (team only) | n/a | 16:9 |
| **A3** Workshop at Night | Mood reference (team only) | n/a | 3:2 |

---

## Abstraction Guide

How to extract repeatable design elements from generated imagery.

### Tier 1: Direct Extraction (becomes brand assets)

**Caustic patterns (P1, P3, elements from H1)**
1. Generate at high resolution with maximum contrast between pattern and ground
2. Apply brightness threshold (40%) to isolate the light pattern
3. Trace to SVG using centerline vectorization (Potrace or equivalent)
4. Normalize stroke weights to 1px, 2px, 4px variants
5. The resulting SVG patterns are the core of the repeatable graphic system
6. Animate by slow translation (CSS `transform: translate`) at 0.5-2px/second

**Facet silhouette (P2)**
1. Generate 8-10 variations of the single facet
2. Select for strongest silhouette recognition at 16x16px
3. Trace outer boundary to SVG path
4. Internal lattice lines become a secondary detail layer visible at 48px+
5. This feeds the logo designer directly

### Tier 2: Texture Application (becomes surface treatments)

**Crystal grain (T2), Hammered gold (M2)**
1. Generate as seamless tileable textures
2. Reduce to 10-15% opacity for UI surface application
3. Apply as CSS `background-image` on surface-1 and surface-2 tokens
4. Must pass contrast testing: text-primary (#f0ebe4) at 16px on textured surface must maintain 7:1+

**Warm paper (T3)**
1. Generate as seamless tileable
2. Apply at full or near-full opacity as light mode base surface
3. Verify contrast with text-primary-light (#1a1816)

### Tier 3: Reference Only (informs decisions, never used directly)

**Atmospheric references (A1, A2, A3)**
- These define the emotional register of the brand
- Used in team alignment meetings and design reviews
- Shared with external collaborators to communicate brand feeling
- Never cropped, filtered, or repurposed as brand assets

**Material studies (M1, M3)**
- Inform physical brand applications (packaging, awards, display pieces)
- Reference for choosing materials in environmental design
- Guide illustration style when structural diagrams need material treatment

### What Never Becomes a Pattern

- Full hero images (H1, H2, H3) are singular compositions, not pattern sources
- Atmospheric perspective and volumetric light effects (H3) cannot be extracted
- Material-specific qualities (resin transparency, obsidian reflection) are reference, not reproducible in UI

---

## Generation Priority Order

For immediate brand development, generate in this sequence:

1. **P1** (Caustic Network) and **P2** (Single Facet): These feed the logo and pattern system directly
2. **H1** (Caustic Genesis): The primary hero image establishes the visual standard
3. **T1** (Dark Caustic Field): The primary background texture, needed for all surfaces
4. **H2** (Crystallization Threshold): Secondary hero for product pages
5. **T2** (Crystal Grain) and **T3** (Warm Paper): Surface textures for both modes
6. **P3** (Caustic Divider): UI element patterns
7. **M1** (Amber Resin): Material reference for the broader team
8. **A1** (Geode Interior): Team alignment reference
9. Remaining material studies and atmospheric references as needed

---

## Platform Notes

### For Midjourney
- Append `--ar [ratio] --v 7 --style raw --no blue, neon, purple, pure black, pure white, lens flare`
- Use `--chaos 15` for pattern generation (P1, P3) to increase geometric variation
- Use `--chaos 5` for material studies (M1-M3) for consistency

### For DALL-E / GPT-4o
- These prompts are written in natural language and work directly
- Prepend "I NEED a photorealistic image:" for best results
- Negative prompt elements should be woven into the positive description

### For Stable Diffusion / Flux
- Convert negative prompt section to the negative prompt field
- Add quality tokens: `masterpiece, best quality, highly detailed, 8k uhd, dslr`
- Weight brand colors using emphasis syntax: `(amber gold #d4a54a:1.3)`
- Use ControlNet with depth/edge maps for pattern consistency across variations

---

*This document is the production reference for all Helioy image generation. Prompts are aligned to the brand strategy (source of truth) and design system foundations (exact tokens). All color references use the locked hex values. Ready for generation.*
