---
title: gpt-image-2 prompt anatomy and grammar
type: research
tags: [imagegen, gpt-image-2, prompt-engineering, openai, codex, image-models]
summary: Structural blueprint for expert-level gpt-image-2 prompts. Covers component ordering, specificity, negation, emphasis, length, composition primitives, templates, and multi-subject scenes.
status: active
confidence: high
created: 2026-05-18
updated: 2026-05-18
related: [codex-imagegen-controls.md]
---

## Cheatsheet — 12 rules that earn their weight

1. **Prompt is a spec, not a tag soup.** gpt-image-2 runs a reasoning pass before drawing. Write briefs the way you would brief an art director. Stacked keywords from the SDXL/MJ era now occupy semantic space intended for real description and degrade output. [PixVerse](https://pixverse.ai/en/blog/gpt-image-2-review-and-prompt-guide), [Imagine.art](https://www.imagine.art/blogs/gpt-image-2-prompt-guide)
2. **Use OpenAI's canonical order: scene -> subject -> key details -> constraints, with the use case named upfront.** The cookbook is explicit. Override only when the subject must dominate (portraits, product). [OpenAI cookbook](https://developers.openai.com/cookbook/examples/multimodal/image-gen-models-prompting-guide)
3. **Front-load the priority.** Whatever sits in the first sentence becomes the anchor. If your first sentence describes background, background dominates. [NoteGPT](https://notegpt.io/blog/gpt-image-2-prompt-guide-use-cases)
4. **Break long prompts into labeled segments or linebreaks** once you pass a short paragraph. Skimmable sections beat prose. [OpenAI cookbook](https://developers.openai.com/cookbook/examples/multimodal/image-gen-models-prompting-guide), [fal.ai](https://fal.ai/learn/tools/prompting-gpt-image-2)
5. **Concrete nouns beat adjectives.** "Matte terracotta ceramic mug with a chipped rim" outperforms "beautiful mug." Replace every "stunning / epic / masterpiece" with a visual fact. [fal.ai](https://fal.ai/learn/tools/prompting-gpt-image-2), [Imagine.art](https://www.imagine.art/blogs/gpt-image-2-prompt-guide)
6. **Negation works, but spend it carefully.** "No watermark, no extra text, no logo" reliably suppresses unwanted artifacts. Use 1-3 exclusions max; do not lean on "not X" as your primary lever. [OpenAI cookbook](https://developers.openai.com/cookbook/examples/multimodal/image-gen-models-prompting-guide), [Pixo](https://pixo.video/blog/gpt-image-2-prompt-guide)
7. **Emphasis is a function of position, specificity, and repetition.** No `::weight` syntax. To weight a constraint, name it first, name it concretely, and name it again as an explicit constraint at the end.
8. **Stay under ~500 words; 100-300 is the sweet spot.** Past that, earlier instructions get dropped. Thinking Mode extends the budget but does not eliminate the ceiling. [Pixo](https://pixo.video/blog/gpt-image-2-prompt-guide)
9. **Composition is a first-class slot.** Framing, viewpoint, lens, depth of field, light direction, and placement zones ("logo top-right", "subject centered with left negative space") belong in the prompt. [OpenAI cookbook](https://developers.openai.com/cookbook/examples/multimodal/image-gen-models-prompting-guide)
10. **Counter the photorealism default.** gpt-image-2 drifts toward stock-photo aesthetics. If you want illustration, vector, watercolor, or anime, anchor the style explicitly in the first or second sentence. [Pixo](https://pixo.video/blog/gpt-image-2-prompt-guide)
11. **For multi-subject scenes, bind every adjective to a named subject** and state relations as absolute positions ("the red mug on the left of the laptop, slightly behind"). gpt-image-2 understands "left", "behind", "overlapping" reliably. [PixVerse](https://pixverse.ai/en/blog/gpt-image-2-review-and-prompt-guide)
12. **Switch to Thinking Mode at 3+ distinct elements, exact text, or strict spatial layout.** It spends 10-30s planning before drawing and is the single biggest lever for compositional fidelity. [Pixo](https://pixo.video/blog/gpt-image-2-prompt-guide), [PixVerse](https://pixverse.ai/en/blog/gpt-image-2-review-and-prompt-guide)

---

## 1. Prompt-as-spec vs prompt-as-tags

gpt-image-2 is a reasoning-integrated model. Per OpenAI's official announcement it can "research, transform inputs, generate variations, and self-check for context-aware assets" before generation. [OpenAI](https://openai.com/index/introducing-chatgpt-images-2-0/). The Microsoft Foundry post and The New Stack call the architecture O-series reasoning grafted onto a generative image head. The model parses prompts as briefs, not as bag-of-tokens style cues.

Practical consequences:

| SDXL / Midjourney habit | gpt-image-2 equivalent |
|---|---|
| `masterpiece, 8k, ultra-detailed, photorealistic, cinematic, octane render` | Drop entirely. Replace with a single concrete medium descriptor ("photorealistic 35mm film still" or "flat vector illustration"). [PixVerse](https://pixverse.ai/en/blog/gpt-image-2-review-and-prompt-guide) |
| `(red:1.4) cape, (blue:0.7) sky` | "Crimson cape, pale washed-out sky." Move emphasis into adjective specificity, position the important element first. |
| `--no people` | "No people, no figures, no silhouettes" as a constraint line at the end. [OpenAI cookbook](https://developers.openai.com/cookbook/examples/multimodal/image-gen-models-prompting-guide) |
| `(((dragon)))` for emphasis | Put dragon in the first sentence, repeat it in the constraints, name what makes it specific. |
| Comma-separated tag stacks | Sentences. Optionally with labeled sections (Scene:, Subject:, Style:, Constraints:). [fal.ai](https://fal.ai/learn/tools/prompting-gpt-image-2) |

HN practitioners observed that the model "is VERY flexible with the resolution" and "responds to art direction, not search queries." [HN 47852835](https://news.ycombinator.com/item?id=47852835). The Dzine 100-prompt guide puts it bluntly: "The model doesn't parse keyword stacks. It reads briefs." [Dzine](https://www.dzine.ai/blog/chatgpt-image-2-0-prompts/)

A small caveat: comma-separated tag prompts still produce usable output for trivial cases. They simply leave quality on the table. As the OpenAI cookbook notes, "Use the format that is easiest to maintain. Minimal prompts, descriptive paragraphs, JSON-like structures, instruction-style prompts, and tag-based prompts can all work well as long as the intent and constraints are clear." [OpenAI cookbook](https://developers.openai.com/cookbook/examples/multimodal/image-gen-models-prompting-guide)

## 2. Optimal ordering of prompt components

The orderings published by reliable sources disagree about whether to lead with scene or subject. Both are defensible. Pick by use case.

| Source | Recommended order | When to use |
|---|---|---|
| OpenAI cookbook | scene/background -> subject -> key details -> constraints, with use case named upfront | General-purpose, default |
| fal.ai | scene -> subject -> important details -> use case -> constraints | Editorial, environmental shots |
| Pixo (6-element) | subject -> action -> scene -> composition -> lighting -> style | Portraits, product, character-driven |
| NoteGPT | subject -> action -> environment -> composition -> lighting -> style -> text | Portraits, action shots |
| Imagine.art | scene -> subject -> key details -> composition -> lighting -> constraints | UI mockups, infographics |
| PixVerse | job -> subject -> exact text -> composition -> style -> constraints -> output format | Ads, posters, anything copy-heavy |

**Contradiction worth knowing.** OpenAI's cookbook says scene-first; Pixo and NoteGPT say subject-first because the first sentence anchors priority. Reconciliation: the cookbook's "use case upfront" satisfies the priority anchor — leading with `"A product mockup of..."` already foregrounds the subject role. If you skip the use case line, lead with the subject.

**Recommended default for any task:**

```
[Use case / artifact type]. [Subject in one sentence].
Scene: [environment].
Composition: [framing, viewpoint, placement].
Style: [medium, lighting, color palette].
Text: [exact copy in quotes, position].
Constraints: [exclusions and invariants].
```

This is a structural superset of every published order and works whether or not labels are kept.

## 3. Specificity vs vagueness

**The rule.** Every modifier should resolve to a visual fact. "Beautiful" describes a feeling. "Iridescent scales catching dappled forest light" describes a render. [Dzine](https://www.dzine.ai/blog/chatgpt-image-2-0-prompts/)

| Vague (replace) | Concrete (use) |
|---|---|
| stunning lighting | warm orange sidelight from camera-left, long shadows, subtle lens flare |
| epic landscape | wide-angle 16mm shot of a glacial valley at blue hour, foreground rocks, midground river, distant snow peaks |
| beautiful woman | woman in her 30s, curly auburn hair, white linen blazer, looking off-camera left |
| premium product | matte aluminum housing, brushed surface, subtle bevel, scuffed underside |
| futuristic | brutalist white concrete, exposed conduit, magnetic levitation kiosk |

[fal.ai](https://fal.ai/learn/tools/prompting-gpt-image-2), [Pixo](https://pixo.video/blog/gpt-image-2-prompt-guide), [Imagine.art](https://www.imagine.art/blogs/gpt-image-2-prompt-guide)

**Negation: what works.** Direct exclusion clauses at the end of the prompt work reliably for:

- Watermarks, logos, signatures
- Extra text, duplicate text, random lettering
- Specific visual cliches (beauty filter, plastic skin, lens flare)
- Categorical exclusion (no people, no animals, no vehicles)

[OpenAI cookbook](https://developers.openai.com/cookbook/examples/multimodal/image-gen-models-prompting-guide), [Pixo](https://pixo.video/blog/gpt-image-2-prompt-guide), [Anil-matcha awesome-gpt-image-2](https://github.com/Anil-matcha/Awesome-GPT-Image-2-API-Prompts)

**Negation: what fails.** Per the OpenAI cookbook and Pixo, the model struggles when negation is the primary signal. "Not a cat" leaves cat-shaped probability mass. Workarounds:

- Replace "not X" with the positive opposite: "a dog" not "not a cat".
- For attribute negation, name what should be there: "matte finish, no gloss" not just "no gloss".
- Cap exclusion clauses at three or four. More signals less. [Imagine.art](https://www.imagine.art/blogs/gpt-image-2-prompt-guide)

Pixo prescribes a mandatory anti-text suffix for text-light images: `"No extra text, no additional words, no random lettering, no watermarks"`. They report this cuts spurious lettering from ~60% to <10%. [Pixo](https://pixo.video/blog/gpt-image-2-prompt-guide)

## 4. Modifier emphasis in natural language

gpt-image-2 has no Stable Diffusion `(:1.4)` or Midjourney `::2` syntax. Emphasis is expressed by:

| Mechanism | How it works | Example |
|---|---|---|
| **Position** | First sentence anchors priority; first noun in a sentence outweighs later ones | `"A red sports car on a misty mountain road"` weights the car; `"A misty mountain road with a red sports car"` weights the road. [NoteGPT](https://notegpt.io/blog/gpt-image-2-prompt-guide-use-cases) |
| **Specificity gradient** | Detailed elements win attention budget over vague ones | Detailed subject + vague background = the model invests resolution in the subject |
| **Imperative voice** | "Render", "show", "ensure", "the image must" upgrade a clause to a directive | `"Ensure the headline reads 'LEGENDARY' verbatim with no extra text"` outperforms a passive description |
| **Repetition across slots** | Mentioning a constraint in both the subject slot and the constraint slot reinforces it | `"... a crimson cape ... Constraints: cape must be crimson, no orange or pink tint"` |
| **Quotation and ALL CAPS** | Reserved for literal text rendering. Acts as a strong "verbatim" signal | `"The sign reads 'OPEN 24/7' in bold sans-serif"` [OpenAI cookbook](https://developers.openai.com/cookbook/examples/multimodal/image-gen-models-prompting-guide) |
| **Labeled sections** | A `Constraints:` line is treated with higher priority than the same content folded into prose | [fal.ai](https://fal.ai/learn/tools/prompting-gpt-image-2) |

The model interprets quality language ("high-fidelity", "ultra-detailed", "sharp focus") as a polish signal, not a magic word. Useful at the end of the prompt, useless if it replaces specificity. [Imagine.art](https://www.imagine.art/blogs/gpt-image-2-prompt-guide), [Dzine](https://www.dzine.ai/blog/chatgpt-image-2-0-prompts/)

## 5. Length

- **Sweet spot: 100-300 words** in Instant Mode. [Pixo](https://pixo.video/blog/gpt-image-2-prompt-guide)
- **Ceiling: 500 words** in Thinking Mode. Past this, earlier instructions get truncated or de-weighted. [Pixo](https://pixo.video/blog/gpt-image-2-prompt-guide)
- **Floor: one well-formed sentence** for simple subjects. Shorter prompts still work when intent is unambiguous. [OpenAI cookbook](https://developers.openai.com/cookbook/examples/multimodal/image-gen-models-prompting-guide)
- **Past ~500 words**: the model begins to ignore earlier instructions; symptoms include missing subjects, wrong text, drifted composition. Trim or split into iterative refinements.

When verbose wins:
- 7-8 distinct constraints (PixVerse reports gpt-image-2 handles this density well)
- Strict layout requirements (UI mockups, infographics)
- Brand-specific copy with exact text and typography
- Multi-element scenes with spatial relations

When shorter wins:
- Photorealistic single-subject portraits
- Stylized illustrations with one anchored aesthetic
- Iteration passes ("change only X")

Brockman: "GPT Image 2 can generate diverse images even for detailed prompts." [Greg Brockman on X](https://x.com/gdb/status/2048449695622586576). The model handles density better than gpt-image-1.5, but density still has a price.

## 6. Composition primitives

gpt-image-2 accepts composition language as a discrete prompt slot. Spell it out:

| Primitive | Vocabulary that works |
|---|---|
| **Camera angle / viewpoint** | eye-level, low-angle, high-angle, top-down (bird's eye), worm's-eye, three-quarter, profile, dutch angle |
| **Framing** | extreme close-up, close-up, medium close-up, medium shot, full body, wide shot, establishing shot |
| **Focal length** | 24mm wide-angle, 35mm documentary feel, 50mm natural, 85mm portrait, 100mm macro |
| **Aperture / depth of field** | shallow depth of field, deep focus, f/1.4, f/8, creamy bokeh, hyperfocal |
| **Lighting direction** | from camera-left, from camera-right, backlit, top-down softbox, rim light, three-point lighting |
| **Lighting quality** | soft diffuse, hard directional, golden hour, blue hour, overcast daylight, fluorescent, neon, candlelit |
| **Layering** | foreground / midground / background (the awesome-gpt-image repo uses these literally as labels) |
| **Placement zones** | top-left, top-center, top-right, left third, right third, centered, rule-of-thirds, golden-spiral focal point |
| **Negative space** | "generous negative space on the left", "subject centered with breathing room", "tight crop" |
| **Motion cues** | one visible motion element: fabric drift, dust, hair, rain, steam (PixVerse video-ready framing) |

Two practitioner-validated patterns:

**Three-plane staging** (Anil-matcha collection, awesome-gpt-image):

```
Foreground (bottom 1/3): [props or texture]
Midground (middle 1/3): [primary subject and action]
Background (top 1/3): [environment, sky, depth cue]
```

[Anil-matcha](https://github.com/Anil-matcha/Awesome-GPT-Image-2-API-Prompts), [Apiyi panorama template](https://help.apiyi.com/en/gpt-image-2-prompts-collection-april-2026-en.html)

**Photographer-as-prompt** (Pixo Technique 5): "Write prompts like you're describing a photograph, not a fantasy." A real shot has a lens, an aperture, a light source, an angle, a subject distance. Name all five and the model lands realism reliably. [Pixo](https://pixo.video/blog/gpt-image-2-prompt-guide)

Rule of thirds and golden spiral both work as named composition cues. Explicit placement ("subject on the left third intersection", "primary focal point at golden-spiral center") beats either heuristic in isolation.

## 7. Reusable templates

Ten expert-published templates, attributed.

| # | Name | Source | Use case |
|---|---|---|---|
| 1 | Photorealistic Portrait | [Apiyi T4](https://help.apiyi.com/en/gpt-image-2-prompts-collection-april-2026-en.html) | Editorial portraits, brand head shots |
| 2 | Product Mockup | [Apiyi T7](https://help.apiyi.com/en/gpt-image-2-prompts-collection-april-2026-en.html) | E-commerce, packaging concept |
| 3 | Cinematic Film Still | [Apiyi T8](https://help.apiyi.com/en/gpt-image-2-prompts-collection-april-2026-en.html) | Editorial illustration, video covers |
| 4 | Typography Poster | [Apiyi T5](https://help.apiyi.com/en/gpt-image-2-prompts-collection-april-2026-en.html) | Event keys, social headers |
| 5 | Mobile UI Mockup | [Apiyi T6](https://help.apiyi.com/en/gpt-image-2-prompts-collection-april-2026-en.html) | Product demos, design proposals |
| 6 | Isometric Diorama | [Apiyi T2](https://help.apiyi.com/en/gpt-image-2-prompts-collection-april-2026-en.html) | Landing page hero, technical headers |
| 7 | The Layer Method (4 turns) | [Pixo](https://pixo.video/blog/gpt-image-2-prompt-guide) | Anything complex; reduces drift |
| 8 | Edit Equation (Change/Preserve/Realism) | [Framia](https://framia.pro/page/en-US/blog/gpt-image-2-prompt-guide), [fal.ai](https://fal.ai/learn/tools/prompting-gpt-image-2) | Iterative edits |
| 9 | Six-Element Default | [Pixo Tech. 9](https://pixo.video/blog/gpt-image-2-prompt-guide) | General-purpose default |
| 10 | Job/Subject/Text/Comp/Style/Constraints/Format | [PixVerse](https://pixverse.ai/en/blog/gpt-image-2-review-and-prompt-guide) | Ads and copy-heavy work |

### Template 1: Default Six-Element (Pixo)

```
Subject: [what is in frame]
Action: [what is happening]
Scene: [where]
Composition: [framing, viewpoint, focal length]
Lighting: [source, direction, quality]
Style: [medium and aesthetic]
```

### Template 2: Photorealistic Portrait (Apiyi)

```
Photorealistic medium close-up portrait of a [AGE] [ETHNICITY] [GENDER]
with [HAIR] and [DISTINCTIVE FEATURE], wearing [CLOTHING], seated in [LOCATION].
Shot on 35mm full-frame with a 50mm f/1.4 lens, shallow depth of field,
golden hour window light from camera-left, 3200K warm color temperature.
Natural skin texture with visible pores, sharp focus on eyes, slight film
grain, no smoothing or beauty filter. Vertical 4:5 framing.
```

Note: per the source, keep ethnicity / hair / distinctive feature consistent across multiple generations to preserve identity.

### Template 3: Edit Equation (Framia)

```
Change: [exact modification — e.g., "swap the jacket from grey wool to navy linen"]
Preserve: [restate every element that must remain identical — pose, face, lighting,
camera angle, background, props, hands, shadows]
Physical realism: [match textures, shadow direction, light temperature; ensure new
element obeys the same physics as the rest of the image]
```

Re-state the Preserve list on every iteration. Drift compounds otherwise. [fal.ai](https://fal.ai/learn/tools/prompting-gpt-image-2)

### Template 4: Typography Poster (Apiyi)

```
A bold contemporary typographic poster, vertical 2:3 ratio.
Background: [color] gradient with subtle paper grain.
Main headline reads "[HEADLINE]" in oversized geometric sans-serif,
positioned upper-center, color #[HEX].
Subheadline below in smaller serif italic: "[SUBHEAD]".
Bottom-left corner: small label "[LABEL]" with a thin horizontal rule.
Decorative element: one minimal abstract shape in [ACCENT COLOR] in negative space.
Editorial magazine aesthetic, generous margins, clean hierarchy.
Constraints: render headline verbatim, no extra words, no duplicate text.
```

Word cap on rendered text: 1-5 words per line; total under ~15 words per image for first-shot legibility.

### Template 5: Cinematic Film Still (Apiyi)

```
A cinematic still from an imaginary [GENRE] film, shot on Kodak Vision3 500T 35mm.
The frame shows [SUBJECT + ACTION] in a [LOCATION] during [TIME OF DAY].
Color palette: teal shadows and orange highlights, slight halation around
bright areas, organic film grain, anamorphic 2.39:1 widescreen.
Camera: 40mm lens at f/2, slight motion blur on the foreground, deep focus
on the subject's face. Mood: [MOOD ADJECTIVES], inspired by the visual
language of [DIRECTOR REFERENCE].
```

### Template 6: Mobile UI Mockup (Apiyi)

```
A high-fidelity mobile app screenshot, iPhone 15 Pro frame, vertical 9:19.5.
The screen shows a [CATEGORY] app with the following layout:
- Top: status bar (9:41, 100% battery, full signal)
- Header: app name "[APP NAME]" in bold, profile icon on the right
- Main: a [HERO COMPONENT] taking 60% of the screen
- Below: 3 feature cards in a horizontal scroll, each with icon, 2-word title, 1-line description
- Bottom: tab bar with 4 icons (home / explore / notifications / profile)
Design language: pastel palette, 16px rounded corners, subtle drop shadows,
system font (SF Pro), light mode. Render the screen pixel-perfect, all text fully legible.
```

### Template 7: Product Mockup (Apiyi)

```
A close-up product photograph of a [PRODUCT] standing on a [SURFACE]
with a clean [BACKGROUND]. Packaging is [MATERIAL] with [TEXTURE], featuring:
a bold logo "[BRAND]" in [LOGO STYLE], a descriptive line "[DESC]" below,
and a small upper-right badge reading "[BADGE]".
Lighting: large softbox at 45° camera-left, small fill from camera-right,
subtle surface reflection. Shot at f/4, ISO 100, 1/125s, on a 100mm macro lens,
3:4 vertical crop, ultra-sharp focus on the label.
Constraints: no watermark, no extra packaging text.
```

### Template 8: Isometric Diorama (Apiyi)

```
A 45° top-down isometric miniature 3D scene of a [THEME] diorama on a wooden display base.
Soft refined PBR textures, realistic materials, clean unified composition,
minimalist aesthetic. Tiny props integrated: [3 SPECIFIC ELEMENTS].
Studio softbox lighting, subtle ambient occlusion, pastel palette dominated
by [COLOR 1] and [COLOR 2]. Square 1:1 frame, centered subject,
plenty of negative space.
```

### Template 9: The Layer Method (Pixo)

Four turns in one conversation instead of one mega-prompt:

```
Turn 1 — Composition: "A wide shot of a quiet bookstore interior at dusk, customer
browsing the shelf on the left third, warm lamps in the background."
Turn 2 — Style: "Apply: 35mm film, warm tungsten lighting, slight grain, teal/orange
palette, deep focus."
Turn 3 — Typography: "Add a vertical sign that reads 'OPEN LATE' in cream sans-serif,
top-right corner of the window."
Turn 4 — Polish: "Tighten shadows on the bookshelf, add subtle dust particles in
the lamp beam, no smoothing on the customer's coat."
```

Stops at three iterations. Quality degrades past that. [Pixo Tech 7](https://pixo.video/blog/gpt-image-2-prompt-guide)

### Template 10: Ad / Copy-Heavy (PixVerse)

```
Create [ARTIFACT TYPE] for [USE CASE / AUDIENCE].
Main subject: [ONE-SENTENCE DESCRIPTION].
Exact text: "[HEADLINE]" and "[CTA]".
Composition: [FRAMING + TEXT PLACEMENT].
Style and lighting: [VISUAL LANGUAGE].
Constraints: [WHAT MUST NOT CHANGE / NOT APPEAR].
Output format: [ASPECT RATIO + RESOLUTION].
```

## 8. Multi-subject scenes

gpt-image-2 understands "left", "right", "behind", "in front of", "overlapping". Per PixVerse and HN testing, it is "the most spatially aware OpenAI image model to date." [PixVerse](https://pixverse.ai/en/blog/gpt-image-2-review-and-prompt-guide)

### Adjective binding

Ambiguous: `"a red car and a blue truck on a dusty road"` — does dusty bind to road or both vehicles?

Bound: `"A red Porsche, polished. A blue Ford pickup, dust-streaked. Both parked on a dirt road."`

Rules:
- Give each subject its own sentence or clause.
- Place every adjective inside the sentence of the noun it modifies.
- For shared attributes, state them on the scene line, not the subject line: `"Both vehicles share the same warm afternoon light."`

### Relational positioning

Use cardinal layout language, not vague spatial words:

| Vague (replace) | Precise (use) |
|---|---|
| next to | to the left of / to the right of |
| near | within arm's reach of / on the same surface as |
| with | holding / standing beside / mounted on |
| in front of | in front of (kept — works reliably) |
| behind | behind (kept — works reliably) |
| above | directly above / suspended over |

Combine with placement zones for layout-critical work: `"Bottle on the right third, headline on the left third, generous negative space across the bottom."` [PixVerse](https://pixverse.ai/en/blog/gpt-image-2-review-and-prompt-guide)

### Multi-reference compositing (up to 16 input images)

```
Image 1: [role — e.g., "the product"]
Image 2: [role — e.g., "the lighting style reference"]
Image 3: [role — e.g., "the background plate"]

Composition: [how they combine].
Preserve: [what must remain unchanged from each input].
Discard: [what to ignore from each input].
```

[OpenAI cookbook](https://developers.openai.com/cookbook/examples/multimodal/image-gen-models-prompting-guide), [Framia](https://framia.pro/page/en-US/blog/gpt-image-2-prompt-guide)

### When to switch to Thinking Mode

Trigger if any of the following:
- 3+ distinct subjects with named positions
- Exact text in 2+ places
- Conditional rules ("if X, render Y")
- Strict count constraints ("exactly 8 panels in a 2x4 grid")

HN testing confirmed Instant Mode fails on conditional grid rules in one shot. Thinking Mode handles them. [HN 47852835](https://news.ycombinator.com/item?id=47852835)

---

## Contradictions in the source material

1. **Subject-first vs scene-first ordering.** OpenAI cookbook prescribes scene-first. NoteGPT and Pixo argue subject-first because the first sentence anchors priority. **Reconciliation:** if you lead with a use-case sentence ("A product mockup of..."), you satisfy both — the use-case sentence implicitly prioritises the subject role. Without a use-case lead, lead with the subject.
2. **Negative prompts work / negative prompts hurt.** The OpenAI cookbook and Pixo say constraint exclusions reliably suppress watermarks and stray text. Imagine.art and other practitioners say overusing "no X" hurts because the model still retains the negated concept. **Reconciliation:** 1-3 constraint exclusions at the end of the prompt work. More than that, or relying on negation as the primary content signal, degrades output.
3. **"Photorealistic" tag necessary / harmful.** Some sources prescribe always including "photorealistic" for realism. Pixo warns that photorealism is the default and you should counter it for stylised work. **Reconciliation:** if you want photo realism in a non-default style context (e.g. fantasy scene rendered photorealistically), say so. For everyday product, portrait, or scene work, you do not need the tag — camera + lighting language carries it.
4. **Length 100-300 vs 500 vs no maximum.** Pixo is most specific (100-300 Instant, up to 500 Thinking). OpenAI cookbook gives no number, only "start clean, refine in small steps." **Reconciliation:** treat Pixo's numbers as practical ceilings; OpenAI's guidance covers iterative workflow.

---

## Sources

### Primary (OpenAI)

- [Introducing ChatGPT Images 2.0 — OpenAI](https://openai.com/index/introducing-chatgpt-images-2-0/)
- [GPT Image Generation Models Prompting Guide — OpenAI Developers](https://developers.openai.com/cookbook/examples/multimodal/image-gen-models-prompting-guide)
- [gpt-image-1.5 Prompting Guide — OpenAI Developers](https://developers.openai.com/cookbook/examples/multimodal/image-gen-1.5-prompting_guide)
- [Introducing gpt-image-2 — OpenAI Developer Community](https://community.openai.com/t/introducing-gpt-image-2-available-today-in-the-api-and-codex/1379479)
- [Collection of GPT-image-generator 2.0 issues and workarounds — OpenAI Dev Forum](https://community.openai.com/t/collection-of-gpt-image-generator-2-0-issues-bugs-and-work-around-tips-check-first-post/1379535)

### Expert practitioner guides

- [fal.ai — GPT Image 2 Prompting Guide and Examples](https://fal.ai/learn/tools/prompting-gpt-image-2)
- [Pixo — The GPT-Image-2 Prompt Guide: 15 Field-Tested Techniques + The Layer Method](https://pixo.video/blog/gpt-image-2-prompt-guide)
- [Framia — GPT-Image-2 Prompt Guide: 7 Techniques That Work](https://framia.pro/page/en-US/blog/gpt-image-2-prompt-guide)
- [PixVerse — GPT Image 2 Review: Prompt Guide and Use Cases in 2026](https://pixverse.ai/en/blog/gpt-image-2-review-and-prompt-guide)
- [Imagine.art — GPT Image 2 Prompt Guide + 70 Prompts](https://www.imagine.art/blogs/gpt-image-2-prompt-guide)
- [Apiyi — GPT-Image-2 prompt collection: 10 templates April 2026](https://help.apiyi.com/en/gpt-image-2-prompts-collection-april-2026-en.html)
- [NoteGPT — GPT Image 2 Prompt Guide: 30 Real Use Cases](https://notegpt.io/blog/gpt-image-2-prompt-guide-use-cases)
- [Picsart — How to prompt GPT Image 2](https://picsart.com/blog/gpt-image-2-prompts/)
- [Dzine — ChatGPT Image 2.0: 100 Ready-to-Use Prompts](https://www.dzine.ai/blog/chatgpt-image-2-0-prompts/)
- [CrePal — GPT Image 2 Prompt Guide for Better Outputs](https://crepal.ai/blog/aiimage/image-gpt-image-2-prompts/)
- [Build Fast with AI — ChatGPT Images 2.0 Developer Breakdown](https://www.buildfastwithai.com/blogs/chatgpt-images-2-0-gpt-image-2-2026)

### Community / aggregator

- [Anil-matcha / Awesome-GPT-Image-2-API-Prompts (GitHub)](https://github.com/Anil-matcha/Awesome-GPT-Image-2-API-Prompts)
- [ZeroLu / awesome-gpt-image (GitHub)](https://github.com/ZeroLu/awesome-gpt-image)
- [Greg Brockman on X — diverse images for detailed prompts](https://x.com/gdb/status/2048449695622586576)
- [Hacker News — ChatGPT Images 2.0 discussion](https://news.ycombinator.com/item?id=47852835)
- [r/gptimage2 — community subreddit](https://www.reddit.com/r/gptimage2/)

### Confidence

High confidence on: prompt-as-spec architecture, the six-component skeleton, negation conventions, text-in-image rules, composition vocabulary, Thinking Mode triggers, and template structures. These claims appear across 4+ independent sources including OpenAI's own cookbook.

Medium confidence on: exact length ceilings (only Pixo gives numbers), and the subject-first vs scene-first ordering choice. The reconciliation above is best-effort, not authoritative.

Lower confidence on: long-term stability of the anti-text negative suffix and the three-iteration ceiling. Both are practitioner claims; OpenAI has not codified them.

### Open questions

- Will the public API parameter surface (May 2026) expose seed, guidance, or per-element masks? Currently the only documented control is the prompt string and the size/quality/n/output_format params (Build Fast with AI). [codex-imagegen-controls.md](codex-imagegen-controls.md) notes Codex's own surface exposes the prompt only.
- Does the conditional-rule failure mode in Instant Mode survive Thinking Mode reliably, or only in narrow cases? HN testing suggests partial improvement, not full resolution.
- What is the practical limit on simultaneous distinct subjects with named positions? PixVerse says 7-8 constraints; no source has tested 10+ in a structured benchmark.
