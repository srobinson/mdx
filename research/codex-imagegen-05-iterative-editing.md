---
title: gpt-image-2 Multi-Turn, Reference-Driven, Edit-and-Refine Workflows
type: research
tags: [gpt-image-2, openai, image-generation, codex, multi-turn, inpainting, outpainting, character-consistency, style-transfer, compositing]
summary: Power-user workflows that separate iterative reference-driven editing from single-shot prompting on gpt-image-2 (Responses API, 16-reference edits, masked inpainting, character anchors, staged compositing, Codex CLI loop).
status: active
confidence: high
created: 2026-05-18
updated: 2026-05-18
---

# gpt-image-2 Iterative Editing Workflows

Scope: multi-turn, reference-driven, edit-and-refine techniques for `gpt-image-2` (snapshot `gpt-image-2-2026-04-21`). Sibling agents own the API reference, prompt anatomy, photographic grammar, text rendering, and failure modes. This file stays on workflow.

## Executive Summary

Power users treat gpt-image-2 as a specification compiler, not a creative slot machine. Three structural moves dominate every advanced workflow: (1) the Responses API with `previous_response_id` for stateful multi-turn refinement, (2) the edits endpoint accepting up to 16 reference images with explicit per-image labels, and (3) restating the full preserve list on every iteration to halt silent drift. Masks are PNG with alpha channel where transparent equals "repaint." Character consistency works through an anchor image plus a freeze-prompt re-stated each turn. Outpainting is the standard escape from the 3:1 aspect-ratio ceiling.

## Cheatsheet: 8 Rules for Iterative Work

1. **Label every reference by index and role.** "Image 1: base scene to preserve. Image 2: jacket reference. Image 3: boots reference." Never let the model guess which input is content versus style.
2. **Restate invariants every turn.** The model has no memory of what you wanted preserved two turns ago. Repeat the full preserve list on every follow-up.
3. **One delta per turn.** "Make the light warmer," then evaluate, then "remove the extra chair." Stacking three deltas in one prompt invites cascade edits.
4. **Use Responses API with `previous_response_id` for chains; use Images API for one-shots.** The Responses API exposes the `action` parameter (`auto` / `generate` / `edit`) and carries conversation state.
5. **Masks: transparent = repaint, opaque = preserve.** PNG with alpha channel, identical dimensions to the base image, under 50MB. Expand the mask 10 to 15 px past the exact edit boundary for natural blends.
6. **Character anchor first, freeze-prompt every scene.** Generate the canonical character once. Pass that file as input to every subsequent edit with the identity invariants re-stated.
7. **Name visual components, not vibes.** "Chunky pixel forms, limited arcade palette, bright glow accents" beats "retro arcade vibe."
8. **Bridge to Photoshop when the model resists.** Generate hero plates with gpt-image-2, composite layers in a pixel editor. Round-trip masks through the editor when prompt-only masking drifts.

## Reference Image Workflows

### How the model attends to inputs

- The edits endpoint accepts up to 16 reference images per request.
- `gpt-image-2` always processes inputs at high fidelity. The `input_fidelity` knob exposed on older gpt-image models is **omitted for gpt-image-2** because the model processes every image input at high fidelity automatically.
- When you pass multiple images, the mask (if any) applies to the first image only.
- Without role labels in the prompt, the model heuristically guesses content versus reference based on prompt verbs. This guessing is the single biggest source of misattributed inputs.

### Label syntax that survives drift

```
Image 1: base scene to preserve.
Image 2: jacket reference.
Image 3: boots reference.

Instruction:
Dress the person from Image 1 using the jacket from Image 2
and the boots from Image 3.
Preserve the face, body shape, pose, background, lighting,
and framing from Image 1. No extra accessories.
```

Two patterns that work:

- **Role-then-instruction**: declare each image's role on its own line, then write the instruction below.
- **Inline reference by index**: "Apply the style from Image 1 to the subject in Image 2."

### Weighting influence

There is no numeric weight parameter. Three ways to bias attention:

1. **Order**: the first image carries the most signal for the edits endpoint, and any mask attaches to it.
2. **Prompt emphasis**: "Lean heavily on Image 2 for palette; treat Image 3 only as silhouette guidance."
3. **Preserve-versus-borrow phrasing**: "Preserve everything from Image 1 except the jacket. Borrow only the jacket fabric and color from Image 2."

## Character Consistency

### Anchor-and-freeze pattern

Step 1: generate the canonical character with full specification.

```
Generate a character reference sheet.
Front, three-quarter, and back views on a neutral background.
Character: young woman, mid-twenties, shoulder-length copper hair,
green hooded tunic with brass clasps, soft brown leather boots,
slim athletic build, kind expression with gentle eyes.
Style: watercolor with earthy palette, soft edges, no outlines.
```

Step 2: pass the anchor as input on every subsequent scene with a freeze-prompt.

```python
prompt = """
Continue the story using the same character.

Character Consistency:
- Same copper hair, same green hooded tunic, same brass clasps
- Same facial features, proportions, and color palette
- Same gentle, heroic personality
- Watercolor style, earthy palette

New scene: she crosses a wooden footbridge over a foggy ravine at dawn.

Do not redesign the character.
"""

result = client.images.edit(
    model="gpt-image-2",
    image=[open("character_anchor.png", "rb")],
    prompt=prompt,
)
```

### Identity tokens via descriptive freeze

Character sheets that compile front/back/side views plus facial expressions and callouts compress identity into the densest reference. Three-view sheets outperform single portraits because the model gets pose-invariant features.

### Known limits

- The character-consistency guarantee holds for simple subjects. As scene complexity grows, drift increases.
- Chained generations across independent prompts drift more than single-request multi-output batches (the 8-image multi-output produces tighter consistency within one call).
- For long-running character work, prefer reference-image edits and the Responses API `previous_response_id` chain over independent prompts.

## Mask-Based Inpainting

### Mask contract

- **Format**: PNG with alpha channel.
- **Dimensions**: identical to the base image.
- **Size**: under 50MB (the underlying limit; some wrappers cite 4MB).
- **Semantics**: transparent pixels (alpha = 0) are repainted. Opaque pixels are preserved.
- **Multi-image**: the mask attaches to the first image in the input array.

### Building masks programmatically

```python
from PIL import Image

# Load black-and-white mask: white = edit, black = preserve
bw = Image.open("mask_bw.png").convert("L")

# Convert to RGBA, use the inverted bw as alpha channel
rgba = Image.new("RGBA", bw.size, (0, 0, 0, 0))
rgba.putalpha(bw)  # white -> opaque (preserve), black -> transparent (edit)

# Invert if your convention is white = edit
# alpha = Image.eval(bw, lambda px: 255 - px)
# rgba.putalpha(alpha)

rgba.save("mask.png", "PNG")
```

### Edge treatment

- **Anti-aliased edges blend naturally.** Hard pixelated edges produce visible seams.
- **Expand the mask 10 to 15 px past the exact edit area.** Tight masks force the model into hard boundaries that break lighting continuity.
- For background replacement with a subject cutout, run an alpha-matting tool (e.g., `rembg`, Photoshop Select Subject) before generating the mask. Clean subject edges beat manual brush work.

### Prompting the masked region

The mask is guidance, not a fence. The model uses the mask to localize the change but may still adjust pixels just outside it. Two-part prompt structure:

```
Replace the area inside the mask with a modern minimalist office:
floor-to-ceiling windows, polished concrete floor, late-afternoon light.

Preserve the subject, the foreground furniture, and the lighting
direction on the subject.
```

### Common pitfalls

- **Mask edges too hard**: visible halo at the seam. Soften.
- **Mask shape contradicts prompt**: model will partially follow the mask, partially the prompt. Resolve by making the mask match the described region tightly.
- **Mask covers the wrong image**: when you pass multiple images, the mask hits the first one. Reorder the inputs if the mask was for image 2.
- **Forgetting to restate preserved regions**: even with a mask, the model may make small adjustments outside it on long iterations. Re-state preservation explicitly.

## Outpainting and Canvas Extension

### Native ceiling

gpt-image-2 caps aspect ratio at 3:1. Total pixels must sit between 655,360 and 8,294,400. Both edges must be multiples of 16. Max single edge 3840 px.

### Chained outpainting past 3:1

1. Generate a 3840 x 1280 base (3:1) with `images.generate`.
2. Place that image on a larger transparent canvas (e.g., 5760 x 1280) with the base aligned left or centered.
3. Build a PNG mask where the empty extension region is transparent and the existing image area is opaque.
4. Call `images.edit` with the canvas as image, the mask as mask, and a prompt that describes the continuation: "Extend the scene to the right. Continue the same horizon line, lighting direction, color palette, and atmospheric perspective. Add gentle terrain variation that matches the existing geology."
5. Repeat once more on the result to reach roughly 8:1.

Tradeoff: each outpainting step is an extra inference call. Visual cohesion beats stitched panels but cost roughly doubles per expansion.

### Edge continuity techniques

- **Overlap the seam**: when building the canvas, overlap the existing image by 64 to 128 px into the mask region. This gives the model continuous context across the boundary.
- **Describe the seam content**: "The right edge of the original shows a stand of pine trees and a dirt road curving away. Continue both into the new region."
- **Lighting direction is the first thing to drift.** State it explicitly: "sun low and from camera left, long shadows pointing camera right."

## Style Transfer

### Specify components, not labels

Avoid "anime style" or "cyberpunk feel." Name what the eye sees.

```
Use the same visual language as Image 1:
chunky pixel forms, limited arcade palette of magenta, cyan, and yellow,
bright glow accents at light sources, clean silhouette edges,
1980s arcade poster typography energy.

Generate a new scene of a motorcycle chase through a neon desert at night.
```

### Pure style transfer with one image

```python
result = client.images.edit(
    model="gpt-image-2",
    image=[open("style_reference.png", "rb")],
    prompt=(
        "Use the same style from the input image and generate "
        "a man riding a motorcycle on a white background."
    ),
)
```

### Style + subject as separate inputs

When the style reference and the content source are different images, label them and describe the relationship.

```
Image 1: product photo of a steel watch.
Image 2: editorial style reference, high-contrast monochrome,
hard rim light, brutalist typography.

Apply the style from Image 2 to the watch in Image 1.
Preserve the watch geometry, dial layout, and crown position exactly.
```

## Multi-Turn Refinement Methodology

### The single-delta loop

1. Generate the base with a clean, structured prompt.
2. Identify one delta. Write a follow-up that names only that change plus the full preserve list.
3. Evaluate. If satisfied, advance. If drifted, revert and try a smaller delta.
4. Repeat.

Three sequential follow-ups beat one mega-revision. Each follow-up is debuggable in isolation. A failed mega-revision is opaque.

### Delta-instruction syntax

Three-sentence pattern:

```
Change: replace the parked car with a vintage bicycle.

Preserve: the house, fence, driveway concrete, landscaping,
lighting direction, time of day, camera angle, and all reflections.

Constraints: no extra objects, no logo drift, no watermark,
match the bicycle scale and shadow pattern to the existing scene.
```

### When to nudge versus restart

| Symptom | Action |
| --- | --- |
| One element drifted; rest is correct | Nudge with a single-delta edit, re-state preserve list |
| Composition broke; subject moved | Restart with tighter geometry lock in the base prompt |
| Style drifted across two turns | Revert to the last good output, use it as the reference for the next edit instead of relying on conversation context |
| Text rendered wrong | Single-delta edit naming the literal string in quotes plus typography (font, weight, color, placement) |
| Lighting drifted | Restart. Lighting drift cascades fast and is hard to nudge back |

### Responses API multi-turn shape

```python
# Turn 1: generate
r1 = client.responses.create(
    model="gpt-image-2",
    input="Generate a watercolor portrait of a woodland scout.",
    tools=[{"type": "image_generation"}],
)

# Turn 2: edit the prior image
r2 = client.responses.create(
    model="gpt-image-2",
    previous_response_id=r1.id,
    input=(
        "Change only the lighting to golden-hour back light. "
        "Keep the character, pose, outfit, palette, and watercolor "
        "style exactly the same."
    ),
    tools=[{"type": "image_generation", "action": "edit"}],
)
```

The `action` parameter values:

- `auto`: model decides whether to generate fresh or edit prior output.
- `generate`: always create a new image (no carry-over).
- `edit`: force editing the most recent image in the conversation.

`partial_images` (0 to 3) controls how many intermediate renders stream back. Useful for live UIs.

## Composition Lock and Content Swap

The pattern: state what stays geometrically constant, then state what swaps.

```
Replace ONLY the white dining chairs in this room with natural oak
wooden chairs.

Preserve: the camera angle, table shape, window light, floor shadows,
reflections on the table, cabinet geometry, refrigerator reflections,
and all surrounding objects. Keep the room otherwise unchanged.
```

When the model still drifts (it will, on complex rooms), add explicit forbidden changes:

```
Do not change: ceiling height, window count, floor color, wall paint,
plant placement, lamp angle, art on walls, rug pattern.
```

## Compositing Workflows

### Staged generation pipeline

For a hero shot with multiple subjects and overlay text, build in passes:

1. **Background plate** (`images.generate`): "Empty cafe interior at 4 pm, soft window light, no people, no signage."
2. **Subject pass** (`images.edit` with background as input): "Add a barista in a denim apron standing behind the counter, mid-thirties, friendly expression, looking off-camera. Preserve background lighting and geometry."
3. **Midground objects** (edit, masked region for the counter): "Add an espresso machine, a tray of pastries, and a clean ceramic milk jug on the counter. Match the existing lighting."
4. **Overlay text** (edit, masked region for top-left): "Render the headline 'DAILY GRIND' in bold condensed sans-serif, off-white color, with subtle drop shadow."

Each pass uses the prior output as the reference image. Each pass restates preservation of the prior layers.

### Photoshop / Affinity bridge

When the model refuses to nail a single element (common with very small text, tight color matching, or specific brand assets), the production move is:

- Generate hero plates with gpt-image-2.
- Export layers and composite in a pixel editor.
- Round-trip masks through the editor: build the mask in Photoshop with the layer panel, export as PNG with alpha, send back to `images.edit` for the patch.
- Use gpt-image-2 for content-aware fills that exceed the pixel editor's content-aware tools, then composite results.

Note: gpt-image-2 does not support transparent backgrounds. For transparent PNG outputs, fall back to gpt-image-1.5 or extract via background-removal post-processing.

## Workflow Recipes

### Recipe 1: Character Anchor Storyboard (6 panels)

**Goal**: a six-panel storyboard where the same character appears in six locations.

1. Generate the character anchor as a three-view sheet on a neutral background. Save as `anchor.png`.
2. For each panel, call `images.edit` with `anchor.png` as input and a per-scene freeze-prompt.
3. Prompt template:

```
Continue the story using the same character from the input image.

Character Consistency:
- [hair color and style]
- [outfit details]
- [build and posture]
- [art style and palette]

New scene: [one-sentence description].
Camera: [angle and distance].

Do not redesign the character. No new accessories.
```

4. Generate all six panels in sequence with the same freeze block.
5. If drift appears by panel 4, regenerate the anchor with tighter specification and restart.

### Recipe 2: Product Insertion into Lifestyle Scene

**Goal**: drop a real product into a generated lifestyle scene without altering the product.

1. Prepare: product photo on neutral background (`product.png`), lifestyle target reference (`scene.png`).
2. Single edit call with both inputs:

```
Image 1: lifestyle scene, kitchen counter at morning, soft daylight.
Image 2: product photo, ceramic coffee mug, matte black, brand mark
on the front center.

Place the product from Image 2 onto the counter in Image 1.
Match the scene's lighting direction (camera left) and color temperature.
Add a soft contact shadow.

Preserve: the product's exact geometry, color, brand mark position,
and surface finish. Preserve the scene exactly except for the addition.
```

3. If product distorts: regenerate with a tighter "do not change the product geometry" line and explicit "the brand mark must remain centered and unchanged."

### Recipe 3: Masked Background Swap

**Goal**: swap a portrait's background while preserving the subject exactly.

1. Run subject segmentation with `rembg` or equivalent to produce a clean alpha cutout.
2. Convert the alpha to a PNG mask where transparent = background area (to repaint), opaque = subject (to preserve).
3. Expand the transparent region by 10 to 15 px around the subject edge to give the model room for natural blending.
4. Call `images.edit`:

```python
client.images.edit(
    model="gpt-image-2",
    image=[open("portrait.png", "rb")],
    mask=open("bg_mask.png", "rb"),
    prompt=(
        "Replace the background with a sunlit linen studio backdrop, "
        "shallow depth of field, warm key light from camera left. "
        "Preserve the subject, the subject's hair edges, and the "
        "subject's lighting exactly. Match shadow direction."
    ),
    size="1024x1024",
    quality="high",
)
```

5. If hair edges go ragged: re-run with a slightly larger transparent region and add "preserve fine hair detail at the edges."

### Recipe 4: 8:1 Cinematic Banner via Chained Outpainting

**Goal**: produce an 8:1 banner that exceeds the native 3:1 ceiling.

1. Generate a 3840 x 1280 base (3:1) with full prompt detail.
2. Place the base on a 5760 x 1280 transparent canvas, aligned left. Build a mask where the right 1920 px is transparent.
3. Call `images.edit` with the canvas and mask. Prompt: "Extend the scene to the right. Continue the same horizon line, sun position (low, camera left), atmospheric haze, and geological style. Maintain depth and scale."
4. Save the result. Place it on a 7680 x 1280 canvas with the new right region transparent. Repeat the edit.
5. Result is roughly 6:1 to 8:1 depending on overlap.
6. Final pass: small global edit to balance color across the seams: "Match color grading and exposure uniformly across the full width. No visible seams."

### Recipe 5: Iterative Style Refinement Loop

**Goal**: dial in a precise illustration style across five turns.

1. Turn 1 (base): clean, structured prompt with rough style direction.
2. Turn 2 (palette delta): "Same composition, same subject, same pose. Change only the palette to cooler tones: deep teal, slate, soft cream. Preserve everything else."
3. Turn 3 (line treatment delta): "Same image as turn 2. Change only the line work to thicker, hand-drawn ink contours. Preserve palette, composition, subject, pose."
4. Turn 4 (texture delta): "Same as turn 3. Add subtle watercolor wash texture in the flat color areas. Preserve line work, palette, composition, subject, pose."
5. Turn 5 (lighting delta): "Same as turn 4. Add a single soft key light from upper left. Preserve everything else."

Each turn restates the full preserve list. If turn 4 breaks the line work, revert to turn 3 and try a smaller texture delta.

### Recipe 6: Three-Image Compositing for a Catalog Shot

**Goal**: combine a model, a garment, and a setting into one editorial frame.

1. Inputs: `model.png` (clean studio model), `garment.png` (flat-lay garment), `setting.png` (location reference).
2. Single edit call:

```
Image 1: model in neutral studio pose.
Image 2: garment, dark forest-green wool overcoat, double-breasted.
Image 3: setting reference, cobblestone alley in fall, late afternoon.

Dress the model from Image 1 in the overcoat from Image 2.
Place the dressed model into the setting from Image 3.

Preserve: the model's face, hair, body proportions, and pose from
Image 1. The overcoat's exact silhouette, button arrangement, and
color from Image 2. The setting's lighting direction, color grade,
and architectural detail from Image 3.

Match the model's lighting to the setting (warm key from camera right,
long shadows). Add appropriate contact shadow at the feet.
```

3. If the overcoat drifts: revert and try a two-step pipeline: dress the model first (Images 1 and 2), then place in setting (result and Image 3).

## Tooling

### Codex CLI ($imagegen skill)

`gpt-image-2` ships built into the Codex CLI under a structured skill at `codex-rs/skills/src/assets/samples/imagegen/SKILL.md`. Three invocation modes:

- Explicit: `codex "$imagegen Generate a six-icon line set at 64x64."`
- Implicit: natural-language requests trigger automatic skill selection.
- Interactive: `/skills` menu.

Multi-turn iteration via image attachment:

```bash
codex -i screenshot.png "Explain this layout and suggest improvements"
codex --image current.png,reference.png "Compare these two layouts"
codex -i mockup-desktop.png -i mockup-mobile.png \
  "Implement this using our existing Tailwind tokens"
```

Outputs land in `~/.codex/generated_images/`. Image turns consume plan limits 3 to 5x faster than text-only turns. Set `OPENAI_API_KEY` explicitly when batch-generating to avoid depleting included quota.

### Python SDK

```python
from openai import OpenAI
client = OpenAI()

# Generate
r = client.images.generate(
    model="gpt-image-2",
    prompt="...",
    size="1024x1024",
    quality="high",
    n=1,
)

# Edit with multi-reference
r = client.images.edit(
    model="gpt-image-2",
    image=[open("img1.png", "rb"), open("img2.png", "rb")],
    mask=open("mask.png", "rb"),
    prompt="...",
)

# Responses API multi-turn
r = client.responses.create(
    model="gpt-image-2",
    previous_response_id=prior_id,
    input="...",
    tools=[{"type": "image_generation", "action": "edit"}],
)
```

### Community wrappers

- **`gpt-image` CLI** (`wuyoscar/gpt_image_2_skill`): wraps generate/edit/composite into a CLI with `-p`, `-i` (repeatable), `-m`, `-f`, `--size`, `--quality`, `-n` flags. Ships 29 prompt galleries including character-sheet templates, multi-panel storyboards, brand-system layouts.
- **`ima2-gen`** (`lidge-jun/ima2-gen`): minimal CLI + web UI, dual auth (API key or ChatGPT OAuth), supports parallel generation.
- **Replicate / fal.ai / WaveSpeed**: hosted endpoints with HTTP-friendly request shapes for teams that want a single integration without rotating OpenAI keys.

### Comfy-style chains

No native ComfyUI node existed as of mid-May 2026, but the staged-generation pipeline (background, midground, subject, overlay text) maps cleanly onto Comfy-style graphs when authored as a script: each node is one `images.edit` call passing the prior output as input. Storing intermediate outputs is the only reliable way to revert specific stages without rebuilding the chain.

## Sources Consulted

### Official OpenAI

- [Image generation guide](https://developers.openai.com/api/docs/guides/image-generation)
- [GPT Image generation prompting guide (cookbook)](https://developers.openai.com/cookbook/examples/multimodal/image-gen-models-prompting-guide)
- [gpt-image-2 model card](https://developers.openai.com/api/docs/models/gpt-image-2)
- [Codex CLI features](https://developers.openai.com/codex/cli/features)
- [Introducing ChatGPT Images 2.0](https://openai.com/index/introducing-chatgpt-images-2-0/)
- [OpenAI Developer Community: gpt-image-2 announcement](https://community.openai.com/t/introducing-gpt-image-2-available-today-in-the-api-and-codex/1379479)

### Practitioner guides

- [fal.ai: prompting gpt-image-2](https://fal.ai/learn/tools/prompting-gpt-image-2)
- [WaveSpeed: gpt-image-2 API guide](https://wavespeed.ai/blog/posts/gpt-image-2-api-guide/)
- [Framia: API best practices](https://framia.pro/page/en-US/news/gpt-image-2-api-best-practices)
- [Framia: post-generation editing guide](https://framia.pro/page/en-US/news/how-to-edit-gpt-image-2-outputs)
- [i-scoop: production playbook](https://www.i-scoop.eu/prompting-gpt-image-2-like-a-pro-guide/)
- [Atlas Cloud: prompts guide](https://www.atlascloud.ai/blog/guides/gpt-image-2-prompts-guide)
- [Daniel Vaughan: Codex CLI visual development](https://codex.danielvaughan.com/2026/04/27/codex-cli-image-generation-gpt-image-2-visual-development-workflows/)
- [BuildFastWithAI: developer breakdown](https://www.buildfastwithai.com/blogs/chatgpt-images-2-0-gpt-image-2-2026)
- [LaoZhang AI: API guide](https://blog.laozhang.ai/en/posts/gpt-image-2-api)

### Tooling

- [wuyoscar/gpt_image_2_skill](https://github.com/wuyoscar/gpt_image_2_skill)
- [lidge-jun/ima2-gen](https://github.com/lidge-jun/ima2-gen)
- [Replicate: openai/gpt-image-2](https://replicate.com/openai/gpt-image-2)

### Aspect ratio and outpainting

- [Apiyi: 3:1 aspect ratio comparison and outpainting workaround](https://help.apiyi.com/en/gpt-image-2-vs-nano-banana-pro-extreme-aspect-ratio-comparison-en.html)

## Source Quality Assessment

Confidence: **high** on documented behavior (mask format, Responses API parameters, 16-image limit, 3:1 cap, anchor pattern), **medium** on the chained-outpainting recipe (the pattern is reported by multiple practitioners but exact prompt phrasing varies), **medium** on character consistency at high scene complexity (acknowledged by practitioners as still imperfect).

OpenAI's own cookbook and developer docs are the primary sources for endpoint shapes and recommended patterns. Practitioner guides from fal.ai, WaveSpeed, and Framia add field experience and pitfalls. Community forum threads on OpenAI's developer community confirm that even in mid-2026 character consistency across chained calls drifts noticeably; this is a known limit, not a configuration error.

Reddit and HackerNews searches yielded near-zero substantive content for gpt-image-2 workflows. The community discussion has moved to OpenAI's own developer forum, X, and vendor blogs.

## Open Questions

- Exact behavior of `input_image_mask` when supplied via `file_id` versus inline upload in the Responses API. The docs describe the field but worked examples are scarce.
- Whether `partial_images` streams masked-region previews or only full-frame previews during edits.
- Whether the `action: "edit"` parameter ever silently falls back to generation when the model judges the prior image incompatible with the requested change. Anecdotally yes, but no formal documentation.
- Whether the 16-image limit applies per turn or across an entire Responses conversation.
- Best practice for managing reference-image token cost on long multi-turn sessions (each carried image accrues input tokens on every turn).

## Actionable Takeaways

1. Default to the Responses API with `previous_response_id` for any workflow longer than one turn. The Images API is a one-shot tool.
2. Build a reusable freeze-prompt template for every recurring character. Re-paste it verbatim on every scene.
3. Always restate the full preserve list on follow-ups. The cost is a few tokens; the savings is hours of regeneration.
4. Mask edges: soft and slightly oversized beat tight and hard. Always.
5. For production catalog or campaign work, treat gpt-image-2 as the plate generator and Photoshop as the compositor. Round-trip masks through both.
6. For batches via Codex CLI, set `OPENAI_API_KEY` explicitly so image turns hit your API budget, not your Codex plan quota.
7. When iterating, one delta per turn. Stop bundling.
8. If output drifts past the third turn, revert to the last good output and use it as the explicit reference for the next edit, instead of trusting conversation context.

## Citations

1. OpenAI, "Image generation guide," https://developers.openai.com/api/docs/guides/image-generation
2. OpenAI Cookbook, "GPT Image Generation Models Prompting Guide," https://developers.openai.com/cookbook/examples/multimodal/image-gen-models-prompting-guide
3. OpenAI, "gpt-image-2 model card," https://developers.openai.com/api/docs/models/gpt-image-2
4. OpenAI, "Codex CLI features," https://developers.openai.com/codex/cli/features
5. OpenAI Developer Community, "Introducing gpt-image-2," https://community.openai.com/t/introducing-gpt-image-2-available-today-in-the-api-and-codex/1379479
6. fal.ai, "GPT Image 2 Prompting Guide and Examples," https://fal.ai/learn/tools/prompting-gpt-image-2
7. WaveSpeed, "GPT Image 2 API Guide for Generation and Editing," https://wavespeed.ai/blog/posts/gpt-image-2-api-guide/
8. Framia, "GPT Image 2 API Best Practices," https://framia.pro/page/en-US/news/gpt-image-2-api-best-practices
9. Framia, "How to Edit GPT Image 2 Outputs," https://framia.pro/page/en-US/news/how-to-edit-gpt-image-2-outputs
10. i-scoop, "Prompting gpt-image-2 like a pro," https://www.i-scoop.eu/prompting-gpt-image-2-like-a-pro-guide/
11. Daniel Vaughan, "Image Generation in Codex CLI," https://codex.danielvaughan.com/2026/04/27/codex-cli-image-generation-gpt-image-2-visual-development-workflows/
12. Apiyi, "gpt-image-2 vs Nano Banana Pro extreme aspect ratio comparison," https://help.apiyi.com/en/gpt-image-2-vs-nano-banana-pro-extreme-aspect-ratio-comparison-en.html
13. GitHub, "wuyoscar/gpt_image_2_skill," https://github.com/wuyoscar/gpt_image_2_skill
14. GitHub, "lidge-jun/ima2-gen," https://github.com/lidge-jun/ima2-gen
15. Replicate, "openai/gpt-image-2," https://replicate.com/openai/gpt-image-2
