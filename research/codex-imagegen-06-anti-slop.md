---
title: gpt-image-2 Anti-Slop Field Guide
type: research
tags: [gpt-image-2, image-generation, prompt-engineering, anti-slop, codex-imagegen]
summary: Catalogue of gpt-image-2 failure modes, slop symptoms, and counter-prompt techniques. Includes red-flag phrase cheatsheet, prompt-rewrite suppression notes, and moderation workarounds.
status: active
confidence: high
created: 2026-05-18
updated: 2026-05-18
---

# gpt-image-2 Anti-Slop Field Guide

Companion document for the codex-imagegen skill set. Sibling docs cover API reference, prompt anatomy, photographic grammar, text rendering, and iterative editing. This file owns the failure-mode catalogue.

## Red Flag Phrases (Cheatsheet)

Words and phrases that almost always trigger slop. Strike them from prompts unless the slop look is intentional.

| Category | Avoid | Reason |
| --- | --- | --- |
| Praise words | `stunning`, `incredible`, `epic`, `masterpiece`, `gorgeous`, `breathtaking`, `insane detail`, `award-winning` | Push model toward generic aesthetic bias. No visual referent. |
| Quality qualifiers | `4K`, `8K`, `ultrarealistic`, `hyperrealistic`, `high quality`, `best quality` | Trigger CGI-render aesthetic, not photographic look. |
| Concept-art language | `concept art`, `cinematic grading`, `glamorization`, `highly detailed`, `intricate` | Pulls toward stylized illustration defaults. |
| Polish cues | `polished`, `studio treatment`, `retouched`, `glamorous`, `flawless skin` | Forces plastic-skin, over-smoothed output. |
| Lighting cliches | `dramatic lighting`, `epic lighting`, `cinematic light` (without anchor) | Defaults to sunset / golden-hour / bloom. |
| Conflicting styles | `photorealistic watercolor`, `realistic illustration` | Sends mixed signals; produces clip-art compromise. |
| Mood-without-thing | `urban transit experience`, `feeling of nostalgia` | Buries the brief; model picks safest visual cliche. |

Substitute language: material specificity (`brushed aluminum`, `chipped paint`, `wet concrete`, `worn fabric`), grounded light (`overcast daylight`, `soft window light`, `incandescent work lamp`, `cool overhead fluorescent`), capture method (`35mm film`, `iPhone photo`, `medium format portrait`), texture truth (`pores`, `fabric wear`, `scuffs`, `dust`).

## 1. The AI Sheen Symptom Catalogue

| Symptom | Diagnosis | Counter-prompt |
| --- | --- | --- |
| Overcooked saturation, "yellow filter" | Default aesthetic bias toward warm, vibrant colour. Reduced but not eliminated in v2. | `neutral white balance, muted color palette, restrained contrast, no color grading` |
| Plastic skin, blurred pores | Model averages toward beauty-retouch aesthetic. Triggered by `portrait`, `beautiful`, `model`. | `visible skin pores, fine vellus hair, uneven skin tone, slight blemishes, oil sheen on T-zone, no retouching` |
| Glassy doll eyes, over-symmetric face | Aesthetic prior plus low-res face area in wide shots. | `asymmetric features, one eye slightly higher, mismatched eye crinkle, natural catchlight only, no beauty filter` |
| Default sunset / golden-hour lighting | `cinematic` and `dramatic` without anchor collapse to this prior. | Specify exact time and light source: `4pm overcast, north-facing window light, no warm cast, flat shadow detail` |
| Default green-foliage / nature background | Untethered outdoor scene defaults here. | Name the place: `gray office carpet, exposed concrete wall, parking structure ceiling, ferry terminal floor`. |
| Default centered subject | Composition silence collapses to centred framing. | `subject occupies right third, gaze leads into negative space on left, horizon at lower fifth` |
| Default eye-level horizon | Same silence prior. | `low angle, camera 30cm from floor, looking up`, or `top-down birdseye, perfectly orthogonal` |
| Default shallow blurred background | Portrait/object prior. | `everything in focus, f/11, full depth of field` or `street photography flat focus, deep depth of field` |
| Bloom / glow halos | Trained on cinema-graded stills. | `no bloom, no lens flare, no halation, clean direct contrast` |
| Tiling grime / steganographic noise | OpenAI provenance watermark embedded during generation; amplifies across session. | Restart chat. In API, regenerate fresh. No prompt-level fix. Source: startupfortune. |

Source corpus: OpenAI cookbook prompting guide, fal.ai prompting guide, Pixnova review, WeShop edge-test review.

## 2. The Clip-Art / 3D-Render Trap

Default model behaviour when style is unspecified or weakly specified collapses to flat-vector or rendered-CGI looks. This is the single most reported slop pattern.

| Triggering vocabulary | Output trap | Substitute |
| --- | --- | --- |
| `illustration`, `digital art`, `artwork` (alone) | Flat vector clip art | `editorial pen-and-ink illustration on cream stock, visible ink bleed, slight off-register print` |
| `3D`, `3D render`, `render`, `CGI` (alone) | Generic miniature concept model, soft global illumination | `photographed practical miniature, dust on surfaces, fingerprints on plexiglass` (if miniature wanted), else avoid the word |
| `cute`, `friendly`, `mascot` | Pixar-style 3D doll | `linocut, hand-printed, two-color screenprint with mis-registration` |
| `product shot`, `marketing image` | Showroom CGI on infinite white | `phone snapshot on kitchen counter, mid-afternoon, slight motion blur, one off-camera lamp` |
| `clean`, `modern`, `minimal` | Stock-photo emptiness | `lived-in counter clutter, coffee ring, yesterday's mail in frame` |
| Bare style nouns: `futuristic`, `fantasy`, `sci-fi` | Generic concept-art polish | Name an artist, era, or medium: `1979 paperback cover gouache`, `90s ND filter snapshot` |

Counter-prompt template:

```
A real photograph. {subject} in {specific place}. {grounded light source}.
Shot on {camera / film}, {f-stop}, {focal length}.
Visible: {three texture details}.
Not present: 3D render, illustration, CGI, retouching, bloom.
```

Anchor word: `Ask for 'photorealistic' directly` (per OpenAI cookbook) when realism is the target, even though `photorealistic` is on most "avoid" lists for other models. For gpt-image-2 specifically it engages a distinct mode.

## 3. Hand and Finger Anomalies

Materially improved in gpt-image-2 versus prior generations. Yahoo News, WeShop, fal.ai, and Pixnova all report five-finger accuracy in standard tests (holding phone, reaching for cup, typing). Residual failures concentrate in: complex inter-finger occlusion, multiple hands in same frame, hands at small image area, gestures that are rare in training data (sign language, specific instrument fingerings).

| Symptom | Diagnosis | Counter-prompt |
| --- | --- | --- |
| Extra / missing fingers | Hand area too small relative to canvas. | `hands occupy central third of frame, fingers clearly separated, palm visible` |
| Spaghetti fingers | Model blends training-data hand angles. | `simple grip, four fingers wrapping around object, thumb on top, nails visible` |
| Wrong number of joints | Rare pose. | Use common poses. State pose explicitly: `hand at rest on table, palm down, fingers slightly splayed` |
| Merged hand with object | Occlusion failure. | `clear gap between hand and {object}, light shadow under fingers showing separation` |
| Distorted hand at edit time | Edit drift. | Edit at high `input_fidelity`. Add `preserve exact hand position, pose, finger count, ring placement` to every edit. |

## 4. Face Uniformity (Sameface)

The doll-jawline, identical-cheekbone problem persists in v2, especially in groups and crowds. Source: WeShop edge tests, OpenAI dev forum.

| Symptom | Diagnosis | Counter-prompt |
| --- | --- | --- |
| All faces share jawline / cheekbones | Default beauty prior across instances. | Name distinct features per person: `man 1: hooked nose, deep-set eyes, jaw stubble; man 2: round face, wide-set eyes, double chin` |
| Over-symmetric features | Aesthetic prior. | `asymmetric face, one ear higher, eyebrow asymmetry, slight nose deviation` |
| Doll-like eyes | Beauty prior plus low face pixel density. | `tired eyes, fine lines at outer corner, slight redness in sclera, single catchlight from window` |
| Loss of likeness across edits | Edit drift; identity vector erodes. | Use `input_fidelity="high"` for identity edits. Restate likeness anchors every turn: `same person: hooked nose, scar above left eyebrow, gray streak in hair` |
| Idealised age | Default lean toward 25-35, conventionally attractive. | Name age and condition: `52, sun-damaged skin, deep nasolabial folds, gray hair with yellow tobacco staining at temples` |

Composition fix for crowd shots: increase face pixel density. `tight three-quarter framing on group of four, faces fill upper half of frame`.

## 5. Default Composition Tropes

When composition is silent, gpt-image-2 collapses to: centred subject, eye-level horizon, shallow depth, sunset light, foliage background, symmetric framing.

| Default | Break by |
| --- | --- |
| Centred subject | `subject occupies right third`, `rule of thirds with subject on lower-left node`, `subject pushed to extreme edge of frame` |
| Eye-level horizon | `low angle, 20cm from floor`, `top-down orthogonal, no perspective`, `worm's eye view looking up at ceiling` |
| Blurred background | `everything sharp, f/11, deep focus, background detail equally rendered` |
| Symmetric framing | `asymmetric layout, weight to left, empty right two-thirds`, `dutch angle 15 degrees clockwise` |
| Centred horizon | `horizon at lower fifth`, `horizon at upper fifth` |
| Sunset/golden hour | Specify time: `2:30pm flat overcast`, `9am cold blue window light`, `night, sodium streetlight only` |
| Foliage background | Name the place explicitly: `inside a hospital corridor, vinyl flooring, fluorescent overhead`. Forbid: `no plants, no foliage, no greenery`. |

Composition order that works (per fal.ai, imagegen2.com): subject -> place -> light -> camera position -> framing -> texture details -> exclusions.

## 6. Object Scale Errors

| Symptom | Diagnosis | Counter-prompt |
| --- | --- | --- |
| Keys bigger than coffee mug | Model lacks 3D physics; pastes concepts without scale anchor. | Name reference object and dimension: `house key roughly 6cm long, next to a 9oz coffee mug roughly 9cm tall, key shorter than mug` |
| Comically large hands | Hand area amplifies if mentioned without scale. | `hand at natural scale, palm roughly the size of subject's face, fingers proportionate to wrist` |
| Tiny human in landscape | Default landscape mode shrinks subject. | `human in foreground occupies one-third of frame height, landscape recedes behind` |
| Wrong mirror reflection scale | Model flips pixels, not 3D geometry. (Pixnova) | Avoid mirrors when accuracy matters, or state: `mirror reflects subject at correct angle and scale, no warping` |

Pixnova stress test: "chicken chasing butterfly on tropical island" produced odd proportionality across iterations; quality control across edits remains the weakest area.

## 7. Text Rendering Breakdowns

gpt-image-2 advertises 99% text rendering accuracy. Practical limit: short, structured copy. Failure modes start above ~50 words per image or below ~30px effective character height.

| Symptom | Diagnosis | Counter-prompt / What NOT to ask for |
| --- | --- | --- |
| Garbled small text | Pixel density too low for legibility. | Cap text per image at 50 words total. Use `quality="high"`. |
| Wrong kerning, letter substitution | Density compression at low quality. | Quote text exactly. Add `verbatim, no extra characters, no substitutions`. |
| Long paragraph distortion | Beyond model's text fidelity envelope. | Generate the image without the paragraph, composite text in Figma/CSS afterward. |
| Mixed alphabet / multilingual fails at edges | Per OpenAI cookbook, multilingual is supported but weaker. | Use one alphabet per image. |
| Text drifts on edit | Re-rendering re-tokenises text. | Lock with `do not change any text or typography, preserve exact characters and kerning`. |

Hard rule: never ask for editable text inside a generated image when the text must be precisely legal, brand, or contract-critical. Use the image as a layer, overlay text in vector tooling.

## 8. Style Drift in Multi-Turn Sessions

Documented in OpenAI dev forum thread #1379535. Three distinct drift modes:

| Drift mode | Symptom | Counter-technique |
| --- | --- | --- |
| Amplifier effect | Quality degrades over 3-5 generations in single session. Noise compounds. | Restart chat. No prompt fix. |
| Data persistence | Different prompts produce near-identical outputs because the system reuses prior image latents. | Restart chat. Avoid repeating prompts. |
| Preserve-list erosion | Each edit drops constraints the previous turn enforced. | Restate full preserve list every turn: subject, framing, lighting, style. "Repeat the preserve list on each iteration to reduce drift." (OpenAI cookbook) |

Drift control protocol:
1. One change per turn.
2. State what changes and what must not change.
3. Restate identity / scene anchors every turn, even when unchanged.
4. If three iterations have compounded artifacts, regenerate from a clean state with the desired final spec.

## 9. Prompt Rewrite Leakage

OpenAI silently rewrites prompts before forwarding to the model. Behavior confirmed in dev forum thread #1362423 (gpt-image-1) and unchanged in gpt-image-2. No documented API parameter disables it.

| Question | Answer |
| --- | --- |
| Is there an official opt-out? | No. Feature request remains open. |
| What does the rewrite add? | Aesthetic prior reinforcement, "polish" descriptors, safety-pass scrubbing. Exact prompt not exposed. |
| How to detect rewriting? | Inferred. Generated image contains visual elements not in your prompt and absent from prior history. |
| Suppression heuristics | Append `(don't change the prompt, send it as it is)` per OpenAI dev forum workaround. Effectiveness: partial. |
| Structured prompts as defence | Highly structured prompts (numbered lists, explicit constraint blocks) survive rewriting better than prose. |
| Quoting | Quoting text in the prompt (`the text "SUMMER DROP"`) survives rewrite verbatim. Quoting style descriptors does not. |
| API vs ChatGPT | API direct calls to `gpt-image-2` are reported to rewrite less aggressively than ChatGPT-mediated calls (Responses API mainline model revises before passing). Use the image endpoint directly when control matters. |

Practical pattern that minimises rewrite damage:

```
Generate this exact specification. Do not add elements.

Subject: {explicit subject}
Place: {explicit place}
Light: {explicit light}
Camera: {explicit camera}
Framing: {explicit framing}
Materials and textures present: {list}
Materials and elements absent: {list}
Text content: "{verbatim quoted text}"
Style: {one specific style anchor}
```

Numbered or labelled fields resist rewrite better than free prose.

## 10. Moderation False Positives

`moderation_blocked` 400 error class. Source: apiyi help center analysis of seven trigger scenarios.

| Trigger | Example false positive | Workaround |
| --- | --- | --- |
| Living celebrities | Asking for "Taylor Swift portrait" | Name replacement: `a woman in her 30s with long blonde hair, similar styling to a pop singer` |
| Copyrighted IP | "Mario" or "Pokemon" | Abstract: `a plumber character in red overalls and cap, original design` |
| Violence words | `fight`, `war`, `attack` | Substitute: `dynamic cinematic action`, `heroic struggle`, `intense confrontation` |
| Realistic minor depiction | Any prompt with `child` plus realism | Drop realism cue, switch to `illustration` or `cartoon style` |
| Headshot of person | The word `headshot` itself flagged in some windows | Substitute: `tight portrait` or `medium close-up shoulders up` |
| Body / nudity adjacent | `nude colour`, `bare arm` | Rephrase: `beige tone`, `short sleeve revealing arm` |
| Hate symbol false hit | Legitimate historical context | Two-step: generate background separately, composite |

General workarounds:
- Two-step approach: split the prompt across multiple turns so the safety classifier sees only narrower context per call.
- Style downgrade: switch from photoreal to illustration. Reduces classifier sensitivity.
- Edit endpoint: prompts that fail at generation sometimes pass at the edit endpoint with a neutral base image.
- Appeal: documented OpenAI Help Center path with full request ID, 3-10 business day response.

## Symptom -> Diagnosis -> Fix Quick Index

| If you see this | The cause is | Try this |
| --- | --- | --- |
| Output looks like CGI miniature | Default render prior triggered by `3D`, `render`, or weak style | Switch to photographic anchor: `35mm film, available light` |
| Subject dead-centre | Composition silence | Specify rule-of-thirds or extreme framing |
| Foliage you didn't ask for | Outdoor default | Name the place |
| Sunset you didn't ask for | Cinematic default | Specify time and light direction |
| Plastic skin | Beauty prior | Add texture and imperfection details |
| Doll-like sameface across people | Beauty prior across instances | Name distinct features per face |
| Tiling grime / noise | OpenAI watermark amplification | Restart session |
| Outputs identical despite changing prompt | Session data persistence | Restart session |
| Garbled small text | Density limit | Composite externally |
| Drift across edits | Constraint erosion | Restate full preserve list every turn |
| Unexpected style additions | Prompt rewrite leakage | Use structured labelled prompt, suppression footer, direct API call |
| Innocuous prompt blocked | Moderation false positive | Substitute trigger word, two-step composite, style downgrade |

## Citations

OpenAI primary:
- [GPT Image Generation Models Prompting Guide](https://developers.openai.com/cookbook/examples/multimodal/image-gen-models-prompting-guide)
- [Disable GPT-Image-1 default prompt rewrite (Dev Forum)](https://community.openai.com/t/disable-gpt-image-1-default-prompt-rewrite/1362423)
- [Collection of GPT-image-generator 2.0 issues (Dev Forum #1379535)](https://community.openai.com/t/collection-of-gpt-image-generator-2-0-issues-bugs-and-work-around-tips-check-first-post/1379535)
- [Multiple gpt-image-1 high fidelity edits lead to grainy result](https://community.openai.com/t/multiple-gpt-image-1-high-fidelity-edits-lead-to-grainy-result/1320474)
- [GPT Image 2 Model Reference](https://developers.openai.com/api/docs/models/gpt-image-2)

Third-party reviews and stress tests:
- [GPT Image 2 looks impressive until you start testing the edges (WeShop)](https://www.weshop.ai/blog/gpt-image-2-looks-impressive-until-you-start-testing-the-edges/)
- [GPT Image 2 Review: 48-Hour Stress Test (Pixnova)](https://pixnova.ai/blog/gpt-image-2-full-review/)
- [GPT Image 2 grime artifacts expose OpenAI's quiet watermark strategy (Startup Fortune)](https://startupfortune.com/gpt-image-2s-grime-artifacts-expose-openais-quiet-watermark-strategy/)
- [No more extra fingers? The good, bad and ugly of ChatGPT Images 2.0 (Yahoo)](https://ca.news.yahoo.com/no-more-extra-fingers-good-192040734.html)
- [I Tested GPT Image 2 So You Don't Have To (Geekvibes)](https://geekvibesnation.com/i-tested-gpt-image-2-so-you-dont-have-to-heres-what-openais-image-ai-actually-gets-right-and-wrong/)
- [OpenAI Unveils New Image Generator to Usher in an AI Slop Renaissance (Gizmodo)](https://gizmodo.com/openai-unveils-new-image-generator-to-usher-in-an-ai-slop-renaissance-2000749159)

Prompting guides:
- [GPT Image 2 Prompting Guide (fal.ai)](https://fal.ai/learn/tools/prompting-gpt-image-2)
- [GPT Image 2 Prompt Guide (Imagine.art, 70 prompts)](https://www.imagine.art/blogs/gpt-image-2-prompt-guide)
- [GPT Image 2 Prompt Guide (imagegen2.com)](https://imagegen2.com/blog/gpt-image-2-prompt-guide)
- [ChatGPT Images 2.0 prompt library (Morphic)](https://morphic.com/resources/how-to/chatgpt-images-2.0-prompts)

Moderation:
- [Fixing gpt-image-2 moderation_blocked 400 error (Apiyi)](https://help.apiyi.com/en/fix-gpt-image-2-moderation-blocked-error-en.html)
- [How to Get Around ChatGPT Content Policy for Images (GlobalGPT)](https://www.glbgpt.com/hub/how-to-get-around-chatgpt-content-policy-for-images/)
- [I Cannot Write This Because It Violates Our Content Policy (arXiv 2506.14018)](https://arxiv.org/html/2506.14018)

Photorealism technique (cross-model background):
- [Prompt Design for DALL-E: Photorealism (Merzmensch)](https://medium.com/merzazine/prompt-design-for-dall-e-photorealism-emulating-reality-6f478df6f186)
- [Photorealism issue realism with dalle-3 (OpenAI Dev Forum)](https://community.openai.com/t/photorealism-issue-realism-with-dalle-3/546247)
