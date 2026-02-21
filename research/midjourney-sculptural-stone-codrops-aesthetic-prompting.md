---
title: Midjourney Sculptural Stone Aesthetic - Codrops SlideshowAnimations Prompting Analysis
type: research
tags: [midjourney, prompting, ai-art, codrops, sculptural, stone, product-photography, studio-lighting]
summary: Reverse-engineered the Codrops SlideshowAnimations Midjourney aesthetic and compiled prompting techniques to reproduce it
status: active
source: deep-research
confidence: high
created: 2026-03-17
updated: 2026-03-17
---

## Executive Summary

The Codrops SlideshowAnimations demo uses Midjourney-generated images of abstract geometric stone forms photographed in a dark studio environment. Manoela Ilic (crnacura) credited Midjourney in the README and article but did not publish the specific prompts used. By analyzing all five images from the demo and cross-referencing Midjourney prompting literature, this report provides a detailed visual breakdown and actionable prompt formulas to reproduce this aesthetic.

## Visual Analysis of the Codrops Images

Having examined all five images (img/1.jpg through img/5.jpg), the consistent visual language is:

**Subject Matter:**
- Large, geometric stone forms with angular facets and organic curves
- Dual-tone color: terracotta/coral red pigment on portions of the stone, natural dark grey/charcoal stone on the remainder
- Some images show a single monolithic form; others show stacked or balanced stone compositions (img/3.jpg has two stones balanced on each other)
- Forms reference Isamu Noguchi, brutalist sculpture, and Japanese stone garden aesthetics
- Surface texture is matte, porous, slightly rough. Visible pitting and grain in the stone surface. Zero glossy or polished areas

**Lighting:**
- Low-key studio lighting from the upper left, creating a pronounced light-to-shadow gradient across each form
- Single dominant light source (likely a large softbox simulation) with minimal fill
- Subtle edge lighting separating the subject from the background
- Shadow falloff on the ground plane is gradual and natural
- The lighting evokes museum or gallery exhibition photography

**Background and Environment:**
- Dark charcoal-to-black gradient background (not pure black; there is a subtle warmth)
- Smooth, matte ground plane in medium grey concrete/stone
- Some images include a small rectangular stone pedestal/plinth (img/1.jpg); others place the form directly on the ground surface
- No visible horizon line; the background fades seamlessly
- The overall tonal range is narrow and controlled: dark greys, charcoal, terracotta red

**Composition:**
- Subject centered or slightly right of center
- Full form visible with generous negative space above and to the sides
- Widescreen aspect ratio (approximately 16:9 or 3:2)
- Low camera angle, approximately eye-level with the base of the sculpture
- Shallow depth of field with the form in sharp focus throughout

**Color Palette:**
- Dominant: charcoal grey (#3a3a3a to #1a1a1a)
- Accent: terracotta/coral red (#c45a3a to #e87060)
- Ground: medium grey (#6a6a6a)
- The red pigment appears applied to the stone surface, like painted concrete or red oxide pigment

## Confirmed Facts About the Images

1. **Generated with Midjourney.** The GitHub README states: "Images generated with Midjourney." The Codrops article states: "The images were generated with Midjourney, feel free to use them in your projects!"
2. **No prompts were published.** Neither the repo, article, nor Manoela Ilic's X account (@crnacura) contain the specific prompts used.
3. **Licensed CC BY 4.0** (from the separate "Free AI Generated Images Vol. 1" article; the SlideshowAnimations repo is MIT licensed).
4. **Codrops uses BigJpg for upscaling** their Midjourney images (confirmed in the Vol. 1 article). The demo images may have been upscaled with this tool.
5. **The article was published September 2023**, placing the generation in the Midjourney v5.x era (v5.2 was current at the time).

## Prompt Reconstruction

Based on visual analysis and Midjourney prompting research, here are prompt formulas that should closely reproduce this aesthetic.

### Core Prompt Template

```
large abstract geometric stone sculpture, angular facets, terracotta red pigment on matte grey stone,
on a stone plinth, dark studio background, low-key gallery lighting, single softbox from upper left,
matte concrete texture, porous surface, museum exhibition photography --ar 16:9 --style raw --stylize 200
```

### Prompt Breakdown by Component

**Subject descriptors (vary these across the series):**
- `large abstract geometric stone sculpture, angular facets`
- `monolithic stone form with sharp geometric planes`
- `brutalist stone sculpture, stacked balanced forms`
- `abstract basalt form with angular cuts and organic curves`
- `massive geometric stone, irregular polyhedron`

**Material and texture (keep consistent):**
- `matte grey stone with terracotta red pigment`
- `porous concrete texture, rough matte surface, no gloss`
- `raw stone with red oxide paint, visible grain and pitting`
- `dual-tone stone, coral red and charcoal grey, matte finish`

**Environment (keep consistent):**
- `dark studio background, seamless grey floor`
- `on a small rectangular stone pedestal`
- `dark charcoal backdrop, matte concrete ground plane`
- `museum exhibition setting, dark gallery`

**Lighting (keep consistent):**
- `low-key studio lighting, single softbox from upper left`
- `gallery exhibition lighting, dramatic side light`
- `museum spotlight, soft shadows, subtle edge light`
- `chiaroscuro lighting, moody, dark background`

**Photography style (keep consistent):**
- `museum exhibition photography`
- `editorial still life photography`
- `shot on medium format camera`
- `product photography, shallow depth of field`

### Recommended Parameters

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| `--ar` | `16:9` or `3:2` | Matches the widescreen compositions in the demo |
| `--style raw` | - | Removes Midjourney's artistic embellishments; produces more photographic, less "AI art" results |
| `--stylize` | `150-250` | Low enough for realism, high enough for aesthetic quality. The default (100) may be too plain; 1000 would over-stylize |
| `--v` | `5.2` (original) or `6.1`/`7` (current) | v5.2 was current when these were made. v6.1+ will produce sharper results |
| `--seed` | Fixed value for a series | Same seed + same style descriptors = consistent composition and mood across variations |
| `--no` | `glossy, shiny, reflective, smooth, polished` | Negative prompting to reinforce the matte texture |

### Five Example Prompts (One Per Image)

**Image 1** (terracotta geometric form on small stone plinth):
```
large geometric stone sculpture, irregular convex polyhedron, terracotta red pigment on matte
grey basalt, on a small rectangular stone pedestal, dark charcoal studio background, low-key
gallery lighting from upper left, porous matte surface texture, museum exhibition photography
--ar 3:2 --style raw --s 200 --no glossy shiny reflective polished
```

**Image 2** (angular two-toned form, coral and dark charcoal):
```
abstract angular stone form, sharp geometric facets, coral red and dark charcoal stone,
dual-tone surface, sitting on matte concrete floor, dark studio background, dramatic side
lighting from left, matte porous texture, editorial sculpture photography
--ar 3:2 --style raw --s 200 --no glossy shiny reflective polished
```

**Image 3** (two balanced stones, red on grey):
```
two balanced stone forms stacked, red pigmented stone balanced on grey basalt boulder,
abstract geometric shapes, dark moody studio background, gallery exhibition lighting,
single light source from upper left, matte rough surface, museum photography
--ar 3:2 --style raw --s 200 --no glossy shiny reflective polished
```

**Image 4** (large rough stone with red paint streak, seated on base):
```
large abstract rough stone sculpture, irregular geometric form, red oxide paint on dark grey
stone surface, sitting on natural stone base, medium grey studio background, soft directional
lighting from left, matte concrete texture, gallery photography
--ar 3:2 --style raw --s 200 --no glossy shiny reflective polished
```

**Image 5** (triangular terracotta form, dark lower half):
```
abstract triangular stone form, terracotta red upper surface fading to dark charcoal,
rough matte stone texture, visible grain, on matte grey concrete surface, dark studio
background with subtle gradient, low-key spotlight from upper left, still life photography
--ar 3:2 --style raw --s 200 --no glossy shiny reflective polished
```

## Techniques for Maintaining Consistency Across a Series

### Method 1: Fixed Seed
Use `--seed <number>` with the same value across all prompts. This fixes the initial noise pattern, producing similar composition, camera angle, and tonal qualities. Vary only the subject description while keeping environment, lighting, and material descriptors identical.

### Method 2: Style Reference (--sref)
Available in v6+. Generate one image you like, then use `--sref <image_url>` on subsequent prompts. The `--sw` parameter (0-1000, default 100) controls how strongly the style reference affects output. For a tight series, use `--sw 300-500`.

### Method 3: Style Reference Codes
Midjourney has 5657+ built-in style codes accessible via `--sref <number>`. Use `--sref random` to discover codes, then lock in a code that matches the aesthetic. The Isamu Noguchi style from Midlibrary is relevant here.

### Method 4: Image Prompt + Describe
Upload one of the Codrops images as an image prompt (`/describe` to reverse-engineer, or use it directly as `<image_url> [your prompt]`). This is the most direct path to matching the exact aesthetic.

### Method 5: Combine Seed + Style Reference
`--seed 12345 --sref <url_or_code> --sw 300` gives you both compositional consistency (seed) and aesthetic consistency (sref).

## Artist References That Evoke This Aesthetic

Including artist names in prompts can steer Midjourney toward specific visual languages:

- **Isamu Noguchi**: Abstract stone sculpture, geometric yet organic, Zen-influenced spatial harmony
- **Eduardo Chillida**: Monumental geometric forms, iron and stone, negative space
- **Anish Kapoor**: Monolithic forms, surface pigment, contemplative scale
- **Lee Ufan**: Minimal stone and steel, gallery installations, negative space
- **Richard Serra**: Massive geometric steel/stone forms, industrial materiality
- **Barbara Hepworth**: Organic abstract stone forms, pierced sculptures

Prompt usage: `abstract stone sculpture in the style of Isamu Noguchi, ...`

## Related Midjourney Photography Terms

These terms, when included in prompts, help achieve the specific photographic quality seen in the Codrops images:

| Term | Effect |
|------|--------|
| `low-key lighting` | Dark background, dramatic shadows |
| `chiaroscuro` | Strong light/dark contrast |
| `gallery exhibition photography` | Clean, professional, museum-quality presentation |
| `editorial still life` | Controlled, curated, magazine-quality |
| `seamless backdrop` | Eliminates visible edges between wall and floor |
| `single light source` | Creates the directional shadow pattern |
| `medium format photography` | Implies shallow DOF, high detail, tonal richness |
| `shot on Hasselblad` | Similar to above; Midjourney responds to camera names |
| `matte` + `porous` + `rough` | Reinforces non-reflective surface quality |
| `brutalist` | Evokes raw, geometric, massive concrete/stone forms |

## Post-Processing Notes

- **BigJpg** was confirmed as Codrops' upscaling tool (2x or 4x upscale of Midjourney outputs)
- Midjourney v5.2 default output was 1024x1024; upscaling to 2048+ was common practice
- Modern Midjourney (v6.1, v7) outputs higher resolution natively, reducing the need for external upscaling
- The images show no evidence of significant color grading beyond what Midjourney produced; the tonal palette appears to come directly from the prompt

## Sources Consulted

### Primary Sources
- [GitHub: codrops/SlideshowAnimations README](https://github.com/codrops/SlideshowAnimations) - confirmed Midjourney attribution
- [Codrops Article: Some Ideas for Fullscreen Image Slideshow Animations](https://tympanus.net/codrops/2023/09/27/some-ideas-for-fullscreen-image-slideshow-animations/) - confirmed Midjourney, no prompts shared
- [Codrops: Free AI Generated Images Vol. 1](https://tympanus.net/codrops/2023/06/12/free-ai-generated-images-vol-1/) - confirmed BigJpg upscaling, showed prompt patterns for other image sets
- Direct visual analysis of img/1.jpg through img/5.jpg from the demo

### Midjourney Prompting Guides
- [God of Prompt: Best Midjourney Prompts for Product Photography](https://www.godofprompt.ai/blog/best-midjourney-prompts-for-product-photography)
- [Aituts: Midjourney Product Photography](https://aituts.com/midjourney-product-photography/)
- [Midlibrary: Isamu Noguchi Style](https://midlibrary.io/styles/isamu-noguchi)
- [Midlibrary: Product Photography Style](https://midlibrary.io/styles/product-photography)
- [OpenArt: 25 Midjourney Prompts for Sculpture](https://openart.ai/blog/post/midjourney-prompts-for-sculpture)
- [Imagine with Rashid: 20 Midjourney Prompts for Still Life Photography](https://imaginewithrashid.com/20-midjourney-prompts-for-still-life-photography/)

### Consistency Techniques
- [Midjourney Docs: Style Reference](https://docs.midjourney.com/hc/en-us/articles/32180011136653-Style-Reference)
- [SREF Code Repository](https://sref-midjourney.com/)
- [Weird Wonderful AI Art: Guide to SREF](https://weirdwonderfulai.art/resources/a-guide-to-sref-style-reference-in-midjourney/)
- [David W Litwin: Ultimate Guide to Style Consistency in Midjourney](https://davidwlitwin.medium.com/the-ultimate-guide-to-style-consistency-with-prompt-accuracy-in-midjourney-5bec8d62aeeb)
- [PromptHero: Midjourney Sculpture Prompts](https://prompthero.com/search?model=Midjourney&q=sculpture)

### Lighting and Parameters
- [Aiarty: 50+ Midjourney Lighting Prompts](https://www.aiarty.com/midjourney-prompts/midjourney-lighting-prompts.htm)
- [Aituts: Midjourney Camera Prompts](https://aituts.com/midjourney-camera-prompts/)
- [Aiarty: Midjourney Product Photography Prompts](https://www.aiarty.com/midjourney-prompts/midjourney-product-photography-prompts.htm)

## Source Quality Assessment

**High confidence** on the visual analysis and prompt reconstruction. I examined all five source images directly and identified consistent patterns across them. The prompting techniques are well-documented across multiple independent guides.

**Medium confidence** on the exact prompt Manoela Ilic used. She did not publish her prompts for this specific project. The prompt formulas above are reverse-engineered from visual analysis, not confirmed originals.

**Gap**: Manoela Ilic's Discord/Midjourney history would be the only way to confirm the exact prompts. Her X account (@crnacura) does not contain Midjourney prompt discussions.

## Open Questions

1. Did Ilic use `--style raw` or default aesthetic mode? The photographic quality suggests raw mode, but v5.2's default was already capable of this look.
2. Were the images generated as a batch with a shared seed, or individually curated from separate generations?
3. Was there any color grading or post-processing beyond BigJpg upscaling?
4. What specific Midjourney version was used? v5.2 was current in September 2023, but v5.1 was also in use.

## Actionable Takeaways

1. **Fastest path to reproduction**: Upload one of the Codrops images to Midjourney as an image prompt, or use `/describe` on it to get Midjourney's own interpretation of the prompt, then refine from there.

2. **For a new series in this style**: Use the core prompt template above, fix `--seed` and `--sref` to maintain consistency, vary only the subject description across images.

3. **Key prompt ingredients** (in order of importance):
   - Subject: `abstract geometric stone sculpture` or `monolithic stone form`
   - Material: `matte grey stone with terracotta red pigment, porous rough surface`
   - Environment: `dark studio background, matte concrete floor`
   - Lighting: `low-key gallery lighting, single softbox from upper left`
   - Style: `museum exhibition photography` or `editorial still life`
   - Parameters: `--style raw --s 200 --ar 16:9 --no glossy shiny reflective`

4. **The terracotta/charcoal dual-tone is the signature element.** Without it, you get generic stone sculpture. The phrases "terracotta red pigment on grey stone" or "red oxide paint on dark basalt" are what produce the distinctive color split.

5. **Artist references that steer toward this look**: "in the style of Isamu Noguchi" is the single most effective artist reference. Eduardo Chillida and Lee Ufan are secondary options.
