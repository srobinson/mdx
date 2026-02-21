---
title: gpt-image-2 Photographic and Cinematographic Vocabulary Reference
type: research
tags: [gpt-image-2, image-generation, prompting, photography, cinematography, openai]
summary: Working vocabulary for prompting gpt-image-2 (April 2026) with cinematographer-grade specificity. Covers lens, aperture, lighting, film stock, atmosphere, composition, color grade, and director references with verified responsiveness levels.
status: active
confidence: medium
created: 2026-05-18
updated: 2026-05-18
---

## Cheatsheet: 15 Highest-Leverage Terms

Ordered by impact-per-token in gpt-image-2 prompts based on triangulated community testing.

| Rank | Term | Why it lands |
|------|------|--------------|
| 1 | `shallow depth of field` | Forces subject isolation; cures the busy-background failure mode |
| 2 | `golden hour` | Single most reliable atmosphere token; predictable warm directional light |
| 3 | `35mm film photography` | Locks aesthetic in one phrase: grain, color, contrast roll-off |
| 4 | `low angle` / `eye-level` / `top-down` | Verb-level control over camera position |
| 5 | `softbox` / `octabox key light` | Studio lighting tokens with reliable physical response |
| 6 | `direct on-camera flash` | Specific stylistic anchor for the CCD/point-and-shoot look |
| 7 | `85mm` (with portrait subject) | Triggers portrait compression and background blur |
| 8 | `Rembrandt lighting` | One of the few classical setups gpt-image-2 reproduces faithfully |
| 9 | `volumetric light` / `god rays` | Atmosphere kicker; pairs well with haze/fog |
| 10 | `teal and orange color grade` | Hollywood look in three words; risk of cliche |
| 11 | `anamorphic lens` (with `2.39:1` aspect) | Adds horizontal flares and oval bokeh signature |
| 12 | `shot like a Roger Deakins frame` | Functional style anchor; shifts toward muted naturalism |
| 13 | `subtle film grain` | Adds texture without forcing full vintage aesthetic |
| 14 | `rim lighting` / `backlight creating edge glow` | Separates subject from background reliably |
| 15 | `photorealistic` | Explicit anchor that engages the photoreal head per OpenAI cookbook |

## Core Principle (from OpenAI cookbook)

> "Detailed camera specs may be interpreted loosely, so use them mainly for high-level look and composition."

Translation: gpt-image-2 reads photographic vocabulary as **mood and intent signals**, not physical simulation. Aperture values, ISO numbers, shutter speeds, and color temperatures are largely placebo unless they accompany the visual descriptor of what they produce. Write `shallow depth of field` not `f/1.4`. Write `warm warm-balanced` not `5600K`.

The corollary: gpt-image-2 *reasons* about the prompt before generating (the first OpenAI image model with O-series reasoning). Concrete visual nouns and verbs outperform technical jargon stacks.

## 1. Lens Vocabulary

| Term | Real-world meaning | gpt-image-2 response | Source |
|------|--------------------|----------------------|--------|
| `14mm` / `ultra-wide` | Extreme wide-angle, environmental distortion | Recognized; produces wide field with edge stretch | felloai.com cinematic prompts |
| `24mm wide-angle` | Wide environmental, mild distortion | Strong response; "slight perspective correction" works | imagine.art |
| `35mm` | Street/documentary feel, near-natural | Reliable; most common in tested prompts | OpenAI cookbook, multiple |
| `50mm` | Normal perspective, no compression | OpenAI's own example uses `50mm lens`; works as framing intent | OpenAI cookbook |
| `85mm` | Portrait compression, flattering subject isolation | Works with portrait subjects; produces expected compression | imagine.art prompt 16 |
| `85mm f/1.4` | Aperture spec added | Aperture portion interpreted "loosely" per OpenAI; pair with `shallow depth of field` for guaranteed bokeh | upuply.com |
| `135mm` / `200mm telephoto` | Compressed perspective, isolated subject | Recognized as framing intent; pairs with `compression` | felloai.com |
| `50mm macro` | Close-up with detail | Works for product/object detail shots | upuply.com prompt |
| `medium format` | Hasselblad-style deliberate look | Listed as effective by fal.ai; produces deliberate, composed feel | fal.ai |
| `iPhone` | Mobile camera aesthetic | Very strong response; produces "amateur" look, unedited RAW look | github/Anil-matcha, github/ZeroLu |
| `Hasselblad` | Premium medium-format body | Light response; mostly aesthetic mood, not physical accuracy | github/ZeroLu |

**Placebo zone**: bare focal-length numbers without a subject or composition cue do little. `200mm` alone is weaker than `200mm telephoto compression of distant ridges`.

## 2. Aperture and Depth of Field

| Term | Real-world meaning | gpt-image-2 response | Source |
|------|--------------------|----------------------|--------|
| `f/1.4` / `f/1.2` | Extreme shallow DOF | Loose interpretation per OpenAI; pair with descriptor | OpenAI cookbook |
| `f/2.8` | Shallow DOF | Same | imagine.art |
| `f/5.6` | Mid-aperture, moderate DOF | Mostly ignored as physics; no observable change vs f/2.8 | github/Anil-matcha example |
| `shallow depth of field` | Background blur | Strongest, most reliable DOF token | universal |
| `deep focus` | Everything sharp | Recognized; produces tack-sharp foreground-to-background | felloai.com |
| `creamy bokeh` | Smooth out-of-focus highlights | Works; produces round, soft circles | gpt2 community prompts |
| `oval bokeh` / `anamorphic bokeh` | Stretched bokeh from anamorphic | Works when paired with `anamorphic lens` | gptimg2 community prompt |
| `swirly bokeh` | Petzval-style swirl | Inconsistent; placebo-level response |
| `background heavily blurred` | Explicit instruction | Strongest forcing function for bokeh | pixverse.ai |

**Rule**: f-stops are aesthetic-level cues, not physics knobs. The descriptor (`shallow depth of field`, `background heavily blurred`) does the heavy lifting.

## 3. Film Stock and Sensor Language

| Term | Real-world meaning | gpt-image-2 response | Source |
|------|--------------------|----------------------|--------|
| `Kodak Portra 400` | Warm peachy skin tones, soft grain | Recognized; produces warm peachy tones | github/Anil-matcha |
| `Kodak Gold 200` | Warm consumer film, golden cast | Recognized; warm/nostalgic cast | felloai.com |
| `Kodachrome` | Saturated reds and blues, contrasty | Recognized; produces vintage saturated palette | felloai.com |
| `Cinestill 800T` | Tungsten-balanced, halation glow | Halation effect is the giveaway; partial recognition | dzine.ai prompts |
| `Fujifilm Pro 400H` | Pastel greens, soft skin | Recognized as aesthetic cue | chatsmith.io |
| `Ilford HP5` | Classic B&W grain | Light response; pair with `black and white` and `grainy` |
| `35mm film` | Generic film aesthetic | Universal trigger; strongest and most-used film token | universal |
| `ARRI ALEXA` | Cinema digital body | Works as mood/look signal; pairs with cinema descriptors | gptimg2 community |
| `ARRI ALEXA with Cooke S5 lenses` | Specific cine setup | Recognized as cinema-grade aesthetic anchor | community prompts |
| `RED Komodo` | Compact cinema body | Light response; aesthetic only |
| `CCD camera` | Old-school sensor look | Strong response; produces hard-flash 90s/2000s look | github/Anil-matcha |
| `large format` | View camera look | Light response; placebo unless paired with shallow DOF |

**What recognizes**: Kodak family, Cinestill (via halation), ARRI ALEXA, generic `35mm film`, CCD aesthetic. **What's placebo**: bare `Ilford HP5`, `RED Komodo`, `large format` without descriptors.

## 4. Lighting Setups

### Studio and Portrait

| Term | Real-world meaning | gpt-image-2 response | Source |
|------|--------------------|----------------------|--------|
| `three-point lighting` | Key + fill + rim/back | Works; produces standard studio separation | imagine.art |
| `Rembrandt lighting` | Triangle of light on shadow cheek | Strong, recognizable response | zsky.ai, multiple |
| `split lighting` | Half face lit, half dark | Recognized |
| `butterfly lighting` | Light above, shadow under nose | Recognized but less consistent |
| `loop lighting` | Slight loop shadow off nose | Less reliable |
| `broad lighting` | Wide side of face lit | Recognized |
| `short lighting` | Narrow side of face lit | Recognized |
| `softbox` / `octabox key light` | Diffused soft source | Very strong; reliable studio look | BubbleBrain X prompts |
| `chiaroscuro` | High-contrast painterly light | Works; produces deep-shadow dramatic frames | felloai.com |

### Natural and Time-of-Day

| Term | gpt-image-2 response | Source |
|------|----------------------|--------|
| `golden hour` | Most reliable atmosphere token; warm directional | universal |
| `blue hour` | Recognized; cool twilight palette | notegpt.io |
| `overcast daylight` | Recognized; flat soft light | fal.ai |
| `harsh midday sun` | Recognized; deep contrast, short shadows | community |
| `north-window light` | Recognized; soft directional from one side | fal.ai |
| `candlelit` | Recognized; warm pool of light, fall-off |
| `neon` | Very strong; produces magenta/cyan/saturated street look | community |
| `sodium vapor` | Recognized; orange monochromatic street lamp |
| `fluorescent` | Strong; produces green-cast convenience-store look | github/Anil-matcha |
| `bioluminescence` | Recognized for organic blue/green glow | felloai.com |
| `mixed cool street light and warm shop light` | Strong; produces signature noir mixed-temp look | fal.ai |

### Directional Language (highest leverage)

OpenAI explicitly recommends **directional** light language over technical specs:
- `warm directional light from the left`
- `harsh side light, long shadows`
- `backlight creating edge glow`
- `rim light separating subject from background`

These outperform `5600K key + 3200K fill` style technical specs.

## 5. Atmosphere and Weather

| Term | gpt-image-2 response | Source |
|------|----------------------|--------|
| `volumetric light` / `volumetric rays` | Strong; light shafts visible through medium | github/wuyoscar |
| `god rays` | Same as above, more dramatic | community |
| `haze` / `atmospheric haze` | Strong; compresses distance, mutes distant objects | community |
| `fog` | Strong; physical fog with depth |
| `mist` / `sea mist` | Strong | github/wuyoscar |
| `dust particles in light` | Recognized; adds visible specks in beams | framia.pro |
| `lens flare` | Strong; pair with `subtle` to avoid overdoing | photogpt.io |
| `chromatic aberration` | Recognized; magenta/green fringing | dzine.ai |
| `halation` | Recognized when paired with Cinestill or film references | dzine.ai |
| `motion blur` | Recognized |
| `rain` / `wet pavement reflections` | Strong; reflective surface response |
| `snow` | Recognized |
| `smoke` | Recognized |

## 6. Composition

| Term | gpt-image-2 response | Source |
|------|----------------------|--------|
| `rule of thirds` | Works; can pair with `subject in the left third` | dzine.ai |
| `golden ratio` | Light response; less reliable than rule of thirds |
| `leading lines` | Recognized; works for landscape/architecture |
| `negative space` | Strong; produces empty regions for poster/text overlay |
| `dutch angle` / `dutch tilt` | Strong; tilts horizon | dzine.ai |
| `symmetrical composition` | Strong; mentioned in Villeneuve-style prompts | felloai.com |
| `frame within a frame` | Recognized |
| `foreground occlusion` | Works; produces in-focus subject through OOF foreground |
| `two-shot` | Recognized as cine framing |
| `OTS` / `over the shoulder` | Recognized |
| `master shot` / `wide establishing` | Recognized |
| `medium close-up` | Strong; standard cine framing |
| `eye-level` / `low angle` / `top-down` / `high angle` | All strong; verb-level control |
| `bird's eye` | Recognized |
| `worm's eye` | Recognized |

Conversational editing extends this: `"shift the subject to the left third of the frame"` works as a follow-up edit instruction.

## 7. Color Grading

| Term | gpt-image-2 response | Source |
|------|----------------------|--------|
| `teal and orange color grade` | Very strong; classic Hollywood look. Risk: applied by default to too many prompts | dzine.ai, gptimg2 |
| `bleach bypass` | Recognized; high contrast, desaturated, retained silver look | felloai.com |
| `day-for-night` | Recognized; blue cast with retained highlights |
| `Kodachrome warmth` | Recognized when paired with `vintage` or `saturated` |
| `Technicolor saturation` | Recognized; punchy reds and greens | felloai.com |
| `muted desaturated naturalism` | Strong; counters the model's default saturation tendency |
| `muted earth-tone color grading` | Strong; produces consistent restrained palette | morphic.com |
| `monochromatic palette` | Strong; single-hue compositions |
| `complementary palette` (with named colors) | Works best when you name the two colors: `magenta and cyan rim lighting` |
| `cool shadows, warm highlights` | Works; produces split-toned look |
| `Roger Deakins-inspired color grading with teal shadows and warm skin tones` | Strong; this exact phrasing reported as effective | felloai.com / community |

**Anti-pattern**: The model has been trained on Hollywood "orange and teal" so heavily that it can apply this even when you do not ask. To counter, specify `muted` or `naturalistic palette` explicitly.

## 8. Cinematic and Director References

This is the most disputed area. Two camps of guidance exist:

**Pro-reference camp**: Named directors and cinematographers shift output measurably.
- `like a still from a Denis Villeneuve film` works; pair with `symmetrical composition, contemplative mood, minimal set design` | notegpt.io
- `shot like a Roger Deakins frame` works; produces muted naturalism | community
- `Wes Anderson-style symmetry, pastel palette, centered framing` works | medium/heck-yeah
- `Greig Fraser anamorphic` light response; partial recognition

**Skeptic camp**: Specific cinematographers are placebo unless paired with the visual descriptor that defines them.
- The pixo.video and framia.pro guides notably **omit** all named cinematographer references, recommending instead direct visual specification: "70mm lens, low angle, foreground dust particles, golden hour, silhouette against the ridge"

**Synthesis**: Director names work as **mood anchors**, not as physics simulators. The phrase "shot like Deakins" gives the model a stylistic compass, but the technical specifics still need to be in the prompt. The composite `Roger Deakins-inspired color grading with teal shadows and warm skin tones, anamorphic 2.39:1, ARRI ALEXA, soft directional key, deep shadow` is what actually moves output. Director name alone is decorative.

| Reference | Practical response | Notes |
|-----------|-------------------|-------|
| Roger Deakins | Mood anchor for muted naturalism, deep shadows | Pair with composition specifics |
| Denis Villeneuve | Mood anchor for minimal symmetrical sci-fi | Pair with `symmetrical, contemplative` |
| Wes Anderson | Strong; pastel-palette centered framing is a well-trained pattern | The most predictable director reference |
| Christopher Doyle | Light response | Less consistent |
| Emmanuel Lubezki | Recognized for natural-light flowing aesthetic | Inconsistent |
| Greig Fraser | Light response | Niche |
| Vermeer (painting reference) | Strong for window-light portraits | Worth knowing |

## Style-by-Phrase Combos That Stack Reliably

Field-tested combinations from BubbleBrain and community prompts that consistently produce intended look:

```
Analog 35mm film photography, soft airy Japanese-style aesthetic,
gentle diffused natural window light, slight overexposure,
pastel tones, low contrast, soft highlights
```

```
Professional studio fashion photography, ultra-clean high-end
digital editorial portrait, pure white seamless cyclorama,
massive soft octabox key light + large softbox fill light,
flawless even illumination
```

```
35mm color film photography with harsh direct on-camera flash,
specular highlights on skin and clothing, strong catchlights in
eyes, warm peachy skin tones with flash highlights, cyan shadows
```

```
Cinematic film still, anamorphic 2.39:1 aspect ratio, shot on
ARRI ALEXA with Cooke S5 lenses, shallow depth of field with
characteristic oval bokeh, neon signage creating magenta and
cyan rim lighting on the subject
```

```
35mm film photography inside a Brooklyn bodega at 2am,
overhead fluorescent tubes mixed with the red glow of a
lottery sign, shallow depth of field, muted earth-tone color
grading, no oversharpening
```

## Placebo Zone (sounds expert, doesn't move the model)

These terms appear sophisticated but show little to no observable effect in community testing:

- Specific shutter speeds (`1/250s`)
- Specific ISO numbers (`ISO 400`)
- Specific color temperatures in Kelvin (`5600K`)
- f-stops without accompanying DOF descriptor
- Bare lens model numbers without a focal-length or context (`Cooke S5` alone)
- `large format` without subject context
- Niche cinematographer names without paired visual descriptors
- `swirly bokeh` (Petzval-specific signature)
- Specific film developer names (`HC-110`, `Rodinal`)
- `Zone System` reference
- `panchromatic` / `orthochromatic` distinctions

The pattern: anything that requires the model to simulate physics rather than recognize an aesthetic pattern tends to fail.

## Sources Consulted

**OpenAI primary**:
- [GPT Image Generation Models Prompting Guide (OpenAI Cookbook)](https://developers.openai.com/cookbook/examples/multimodal/image-gen-models-prompting-guide)
- [Introducing gpt-image-2 (OpenAI Community)](https://community.openai.com/t/introducing-gpt-image-2-available-today-in-the-api-and-codex/1379479)
- [Introducing ChatGPT Images 2.0 (OpenAI)](https://openai.com/index/introducing-chatgpt-images-2-0/) (403 to WebFetch)

**Prompt guides**:
- [Pixo: 15 Field-Tested Techniques + Layer Method](https://pixo.video/blog/gpt-image-2-prompt-guide)
- [Framia: 7 Techniques That Work](https://framia.pro/page/en-US/blog/gpt-image-2-prompt-guide)
- [Imagine.art: 70 Prompts Guide](https://www.imagine.art/blogs/gpt-image-2-prompt-guide)
- [Photogpt.io: Prompt Guide and Review](https://photogpt.io/blog/gpt-image-2-prompt)
- [UpUply: 20 Copy-Paste Examples](https://www.upuply.com/blog/GPT-Image-2-prompt-guide)
- [fal.ai: Prompting Guide and Examples](https://fal.ai/learn/tools/prompting-gpt-image-2)
- [NoteGPT: 30 Real Use Cases](https://notegpt.io/blog/gpt-image-2-prompt-guide-use-cases)
- [Morphic: ChatGPT Images 2.0 Library](https://morphic.com/resources/how-to/chatgpt-images-2.0-prompts)
- [zsky.ai: 38 AI Lighting Prompts](https://zsky.ai/blog/ai-lighting-prompts)
- [felloai: 7 Cinematic Prompts That Actually Work](https://felloai.com/7-chatgpt-prompts-for-cinematic-photos-that-actually-work/)

**GitHub prompt collections**:
- [Anil-matcha/Awesome-GPT-Image-2-API-Prompts](https://github.com/Anil-matcha/Awesome-GPT-Image-2-API-Prompts)
- [ZeroLu/awesome-gpt-image](https://github.com/ZeroLu/awesome-gpt-image)
- [magiccreator-ai/awesome-gpt-image-2-prompts](https://github.com/magiccreator-ai/awesome-gpt-image-2-prompts)
- [EvoLinkAI/awesome-gpt-image-2-prompts](https://github.com/EvoLinkAI/awesome-gpt-image-2-prompts)
- [wuyoscar/gpt_image_2_skill](https://github.com/wuyoscar/gpt_image_2_skill)

**X/Twitter expert posts** (referenced via search, individual fetches blocked by paywall):
- BubbleBrain portrait prompts (analog 35mm Japanese aesthetic, studio fashion octabox)
- Riccardo Wolf travel-poster style tests
- Blake Robbins arena test leaks
- Arena.ai leaderboard data (+242 lead over Nano-banana-2)

**Photography reference baseline**:
- ARRI on Roger Deakins workflow with ALEXA
- Cinestill vs Portra comparisons (decafjournal, maxkent, emulsive)

## Source Quality Assessment

**Confidence: medium**. Most claims triangulate across 3+ guides and align with OpenAI's own cookbook stance that camera specs are interpreted loosely. The strongest evidence is for: directional lighting language, focal length as framing intent, `35mm film` as universal trigger, `shallow depth of field` as the most reliable DOF cue, and `golden hour` as the most reliable atmosphere cue.

**Lower confidence** on: specific cinematographer reference responsiveness (camps disagree), exotic film stocks beyond Kodak/Cinestill, classical lighting setups beyond Rembrandt. Direct empirical testing in the user's own pipeline is recommended for any term marked "light response" or "inconsistent."

**Known gaps**:
- Reddit/HN have near-zero high-signal threads on gpt-image-2 photographic prompting; community discussion is fragmented across X and prompt-aggregator sites.
- Several primary X posts return 402 to WebFetch; relied on search-result extracts.
- OpenAI's own announcement page returned 403; the cookbook entry is the authoritative replacement.

## Open Questions

- Does gpt-image-2 distinguish between `Kodak Portra 400` and `Kodak Portra 800` at perceptible levels, or does it collapse to "Portra family"?
- Do bare cinematographer references work consistently in non-portrait subjects (architecture, product, landscape)?
- How stable is the response to chained references like "shot like Deakins on an Alexa with Cooke S5 anamorphics, Roger Deakins-style teal shadows"? Risk of compounding noise vs. stacking signal.
- Does the model's reasoning step (O-series integration) reduce or increase placebo-term sensitivity compared to gpt-image-1?

## Actionable Takeaways

1. **Lead every prompt with a visual descriptor, not a camera spec.** `Shallow depth of field, golden hour, low angle` beats `f/1.4, 5600K, 18mm`.
2. **Stack max one director reference per prompt**, and always pair with the visual descriptors that define their style.
3. **Treat film stocks as palette/grain anchors**, not as physics simulators. `Kodak Portra 400` says "warm peachy soft." `Cinestill 800T` says "halation, tungsten cast."
4. **Default to `muted` or `naturalistic palette`** unless you actively want the teal-and-orange Hollywood look (the model leans there by default).
5. **For studio looks**, name the light shape: `octabox key + softbox fill`. For natural looks, name the source and direction: `north-window light, soft directional from left`.
6. **Use the cheatsheet 15 terms as scaffolding**, then enrich with subject- and scene-specific visual nouns.
7. **Verify in pipeline**: pick five terms marked "light response" or "inconsistent" and run A/B prompts to map your own confidence levels.

## Citations

1. OpenAI Cookbook: GPT Image Generation Models Prompting Guide — https://developers.openai.com/cookbook/examples/multimodal/image-gen-models-prompting-guide
2. Pixo "GPT-Image-2 Prompt Guide: 15 Field-Tested Techniques + The Layer Method (2026)" — https://pixo.video/blog/gpt-image-2-prompt-guide
3. Framia "GPT-Image-2 Prompt Guide: 7 Techniques That Work" — https://framia.pro/page/en-US/blog/gpt-image-2-prompt-guide
4. fal.ai "GPT Image 2 Prompting Guide and Examples" — https://fal.ai/learn/tools/prompting-gpt-image-2
5. UpUply "Master GPT Image 2: 20 Copy-Paste Examples" — https://www.upuply.com/blog/GPT-Image-2-prompt-guide
6. Imagine.art "GPT Image 2 Prompt Guide + 70 Prompts" — https://www.imagine.art/blogs/gpt-image-2-prompt-guide
7. Morphic "ChatGPT Images 2.0 prompt library" — https://morphic.com/resources/how-to/chatgpt-images-2.0-prompts
8. NoteGPT "GPT Image 2 Prompt Guide: 30 Real Use Cases" — https://notegpt.io/blog/gpt-image-2-prompt-guide-use-cases
9. Felloai "7 ChatGPT Prompts for Cinematic Photos That Actually Work" — https://felloai.com/7-chatgpt-prompts-for-cinematic-photos-that-actually-work/
10. zsky.ai "38 AI Lighting Prompts — Golden Hour, Rembrandt, Neon" — https://zsky.ai/blog/ai-lighting-prompts
11. Anil-matcha GitHub: Awesome-GPT-Image-2-API-Prompts — https://github.com/Anil-matcha/Awesome-GPT-Image-2-API-Prompts
12. ZeroLu GitHub: awesome-gpt-image — https://github.com/ZeroLu/awesome-gpt-image
13. magiccreator-ai GitHub: awesome-gpt-image-2-prompts — https://github.com/magiccreator-ai/awesome-gpt-image-2-prompts
14. BubbleBrain X posts on portrait prompts — https://x.com/BubbleBrain/status/2046115431144902732
15. ARRI on Roger Deakins workflow — https://www.arri.com/news-en/roger-deakins-cbe-asc-bsc-on-his-journey-to-arri-large-format
