# Codex Imagegen Controls

Date: 2026-05-02

This note documents the image generation interface exposed to Codex in this
session. It is an operational note, not a public API guarantee.

## Tool Shape

Codex calls image generation through a single tool input:

```json
{
  "prompt": "Create a 1500x500 banner image..."
}
```

The exposed control surface is the prompt. I do not see separate parameters
for seed, sampler, model, guidance scale, reference weight, number of images,
mask, edit strength, negative prompt, or output path.

Generated images are saved by the platform under:

```text
/Users/alphab/.codex/generated_images/<session-id>/<image-id>.png
```

If an image needs to live somewhere else, copy it and leave the original in
place unless the user explicitly asks to delete it.

## Practical Levers

The usable controls are prompt level constraints.

| Lever | How it is controlled |
| --- | --- |
| Format | State exact dimensions or aspect ratio, for example `1500x500`, `3:1 banner`, `2048x1152`, `16:9 website hero`. |
| Subject | Describe the actual thing to depict: mothership, product object, diagram, landscape, mechanism. |
| Style | Describe the art direction: cosmic editorial, cool studio, paper schematic, diorama. |
| Composition | Specify subject placement, copy zones, camera angle, safe margins, crop behavior, and visual weight. |
| Reference use | Attach an image and state its role, for example shape reference, palette reference, motif, or style reference. |
| Text policy | Say no in image text, or provide exact text and exact placement. |
| Constraint strength | Use a `Forced:` block for non negotiable instructions. |
| Suppression | Use an `Avoid:` block for unwanted artifacts and common failure modes. |
| Iteration | Inspect the result, then generate again with targeted corrections. |

## Reference Images

Attached images can influence generation, but Codex controls them through
language. There is no visible numeric reference strength.

Good reference instructions name the job of the image:

```text
Use the attached Helioy logo as a subtle hull architecture motif.
Do not paste it as a flat decal.
Do not make the whole ship match the logo silhouette.
```

Bad reference instructions are ambiguous:

```text
Use this image.
Make it like this.
Same vibe.
```

For logo work, the best results come from separating roles:

```text
Use the attached mark as a geometry reference only.
Keep the subject an actual spacecraft first.
Incorporate the mark as split circular apertures, crescent light wells,
and a clean vertical docking channel.
No wordmark. No flat logo decal.
```

## Text Handling

By default, image generation should not create readable text. Generated text is
unreliable and tends to invent artifacts.

Default policy:

```text
Do not render any in image text: no title, subtitle, headline, labels, status
text, readable signage, UI panels, button copy, or wordmark.
```

Only opt in when the exact text is supplied:

```text
Text: title "HELIOY" centered in the lower third, no other text.
```

## Helioy Imagegen Layering

`$helioy-imagegen` acts as a prompt compiler. It combines four layers:

1. Register: visual style.
2. Composition: frame and layout.
3. Argument: visual claim, optional.
4. Subject: user brief.

Example:

```text
$helioy-imagegen cosmic-editorial:hero-with-anchor Helioy mothership banner
```

In that invocation:

1. `cosmic-editorial` controls palette, atmosphere, lighting, painterly finish,
   and technical overlay.
2. `hero-with-anchor` controls the right anchored subject and left copy zone.
3. No argument layer is used.
4. `Helioy mothership banner` supplies the subject.

The register does not lock the subject. The same `cosmic-editorial` style can
produce a logo aperture, an actual mothership, a landscape, a product hero, or
a diagram remaster if the subject and composition call for it.

## Prompt Pattern

A reliable prompt structure:

```text
Create a 1500x500 general banner image, 3:1.

Style:
[visual register, palette, lighting, finish]

Subject:
[what the image should actually depict]

Composition:
[placement, safe margins, copy zone, camera, crop]

Reference handling:
[what the attached image controls, and what it must not control]

Intent:
[the visual claim in one sentence]

Forced:
[non negotiable constraints, including text policy]

Avoid:
[failure modes, unwanted genres, artifacts, text, watermark]
```

## Example: Actual Mothership With Helioy Mark

```text
Create a 1500x500 general banner image, 3:1.

Style: cosmic editorial cinematic sci fi matte painting. Deep nocturne palette
with near black navy, indigo, midnight blue, violet, ultramarine, and blue
purple atmospheric planes. Low distant horizon glow in magenta, rose, muted
coral, and restrained warm amber. Cool white, pale lavender, and icy blue rim
light on key ship edges. Painterly atmospheric depth, soft haze, layered mist,
thin cloud strata, quiet cinematic grain, premium editorial finish.

Subject: an actual vast space mothership for Helioy, a believable interstellar
carrier ship with immense scale, calm engineering confidence, and ecosystem
scale. The ship should read as a real spacecraft first: elongated command
spine, broad layered hull plates, deep hangar cavities, antenna masts, heat
radiators, docking bays, engine nacelles, recessed maintenance trenches, and
carefully organized surface detail.

Reference handling: incorporate the Helioy logo mark subtly as ship design
language. Use the mark as a recurring architectural motif: a split circular
aperture embedded near the central hangar mouth, two crescent shaped illuminated
hull insets, and a clean vertical light channel inside a docking bay. The mark
should be recognizable to someone who knows it, but it must not dominate the
ship or turn the entire mothership into the logo silhouette.

Composition: wide hero banner with left 35 to 45 percent as calm low contrast
negative space for deterministic text overlay. Place the mothership right of
center, occupying the right 55 to 65 percent of the canvas, angled in three
quarter view from slightly below. Keep the entire ship inside the frame with 10
to 15 percent padding and no edge bleed.

Forced: actual space mothership, not logo shaped. Incorporate the Helioy mark
only as subtle hull architecture and light motifs. Left copy zone empty. Do not
render any in image text: no title, subtitle, headline, labels, status text,
readable signage, UI panels, button copy, or wordmark. No watermark. No human
figures.

Avoid: flat pasted logo, full ship shaped like the logo, black on white logo
treatment, dense all over star fields, random particles, laser grid, neon rain,
cyberpunk city, cockpit UI, readable text, random greebles, aggressive weaponry,
explosions, flames, horror tone, daylight sky, hard white background, edge
bleed.
```

## Known Limits

1. Exact logo fidelity is not guaranteed unless the model strongly follows the
   reference image.
2. Text generation should be avoided unless exact strings are necessary.
3. The tool does not expose deterministic seeds, so exact regeneration is not
   available.
4. Image iteration is prompt based. There is no visible mask or layer editing
   interface.
5. Dimensions in the prompt guide the generator, but the platform may choose
   its own internal render size.

## Working Rule

Treat imagegen as a high level visual compiler:

```text
reference images + structured prompt constraints -> generated bitmap
```

Use explicit role assignment for references, strong composition constraints,
and short forced rules. Do not rely on vibe alone.
