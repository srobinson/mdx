# Codex / gpt-image-2 Knowledge Base

**Target model:** OpenAI `gpt-image-2` (snapshot `gpt-image-2-2026-04-21`), released April 2026.
**Scope:** Expert-level prompting craft for Codex CLI and the OpenAI Images / Responses APIs.
**Compiled:** 2026-05-18 from six parallel research agents, ~165 KB of cited primary and community sources.

---

## TL;DR — Twelve principles that change every prompt

1. **Prompt-as-spec, not tag soup.** gpt-image-2 reads instructions. Write like a brief to a DP, not like a search query.
2. **Position equals weight.** The first sentence wins priority. No `:weight` syntax exists. Repetition across slots is the second-strongest emphasis.
3. **Photorealism is the default.** Tagging "photorealistic" on a portrait wastes tokens. Tag style only when departing from photographic realism.
4. **Labelled blocks beat prose for serious work.** Subject / Place / Light / Camera / Framing / Materials Present / Materials Absent / Text / Style. Resists silent prompt rewriting and prevents slop.
5. **Concrete photographic grammar beats praise vocabulary.** `warm directional light from the left, softbox key`, not `stunning cinematic masterpiece 4K`.
6. **Bare camera specs are placebo.** f-stops, ISO, Kelvin, shutter speeds, lens model numbers do nothing alone. Pair them with `shallow depth of field`, `golden hour`, `volumetric light`.
7. **`EXACT TEXT: "..."` for verbatim strings.** Wrap in straight quotes, close with a no-substitution constraint stack. Lifts first-pass text accuracy from ~70% to ~95%.
8. **Anchor-and-freeze via `previous_response_id`.** Generate canonical asset once, then chain edits with verbatim freeze-prompt repeated every turn. Holds character, palette, composition.
9. **One delta per turn.** Stacking deltas cascades into a near-rewrite. Restate the full preserve list every iteration.
10. **Negation works only as a 3-4 item closing clause.** Prefer positive-opposite phrasing. `"not a cat"` leaves cat-shaped probability mass.
11. **Responses API gotcha.** `model` is the chat model (e.g. `gpt-5.4`). `gpt-image-2` is attached as the `image_generation` tool, not as the model field.
12. **`input_fidelity` is gone.** Every reference image processes at high fidelity in v2, so edit-heavy pipelines cost meaningfully more than gpt-image-1.5.

---

## The six layers

| # | Layer | File | Top finding |
|---|-------|------|-------------|
| 01 | Official reference | [`codex-imagegen-01-official-reference.md`](codex-imagegen-01-official-reference.md) | Three endpoints, parameter contract, pricing, Tier 1-5 limits, C2PA watermarking, Codex CLI `$imagegen` skill location |
| 02 | Prompt anatomy | [`codex-imagegen-02-prompt-anatomy.md`](codex-imagegen-02-prompt-anatomy.md) | Position is the only weight; photorealism is default; negation works only as closing constraint clause |
| 03 | Photographic grammar | [`codex-imagegen-03-photographic-grammar.md`](codex-imagegen-03-photographic-grammar.md) | Directional lighting verbs and composition verbs carry the load; bare camera specs are placebo |
| 04 | Text and layout | [`codex-imagegen-04-text-and-layout.md`](codex-imagegen-04-text-and-layout.md) | `EXACT TEXT:` convention + closing constraint stack lifts text accuracy from 70% to 95%+ |
| 05 | Iterative editing | [`codex-imagegen-05-iterative-editing.md`](codex-imagegen-05-iterative-editing.md) | Anchor-and-freeze loop with `previous_response_id`; one delta per turn; restate full preserve list |
| 06 | Anti-slop | [`codex-imagegen-06-anti-slop.md`](codex-imagegen-06-anti-slop.md) | Praise words trigger CGI polish; untethered style nouns collapse to default render; labelled blocks resist both |

Legacy: [`codex-imagegen-controls.md`](codex-imagegen-controls.md) — May 2026 notes, predates this series. Cross-reference only.

---

## Suggested reading order

1. **`06-anti-slop.md`** first. Knowing what produces clip-art prevents writing slop-causing prompts before any technique gets layered on.
2. **`02-prompt-anatomy.md`** next. The structural grammar everything else attaches to.
3. **`03-photographic-grammar.md`** for visual vocabulary that actually moves the output.
4. **`04-text-and-layout.md`** when typography, signage, or layout is in scope.
5. **`05-iterative-editing.md`** when one-shot is insufficient and a series needs consistency.
6. **`01-official-reference.md`** as the contract lookup. Treat as a manual, not a tutorial.

---

## The slop-prevention contract

Reproduced here because it is the cross-cutting deliverable.

```
Subject: <concrete noun + role + state>
Place: <location, time of day, season, weather>
Light: <source direction, quality, colour temperature in words>
Camera: <focal length descriptor, distance, angle, DoF in words>
Framing: <composition rule, headroom, lead room, occlusion>
Materials Present: <textures, surfaces, props>
Materials Absent: <up to 4 exclusions>
Text: EXACT TEXT: "<quoted string>"   (omit if no text)
Style: <medium and reference, only if departing from photorealism>

Render the above verbatim. No extra text. No watermarks. No substitutions.
```

Use this when the default looks generic. Skip the labels for fast iteration once a baseline lands.

---

## Open questions and contradictions

Documented in detail inside each artifact. The unresolved ones:

- **Reasoning parameter name.** Community sources contradict between `quality_mode`, `thinking`, and none at all. OpenAI docs are silent. See `01-official-reference.md`.
- **Subject-first vs scene-first ordering.** OpenAI cookbook leans subject-first; Pixo and NoteGPT lean scene-first. Position-as-weight reconciles the two: lead with whatever you want to dominate.
- **Photorealistic tag.** Some guides say add it, others say remove it. The reconciliation: redundant for portraits and product shots, useful only when the surrounding prompt contains style nouns (`cinematic`, `dramatic`) that might pull the model toward stylisation.
- **Length sweet spot.** Pixo recommends 100-300 words. OpenAI is silent. Empirical: longer prompts work as long as every clause carries information.
- **RTL bidirectional layout.** Arabic-Latin mixed lines not verified in any source. Test before relying.
- **Trademark wordmarks.** Model drifts on protected marks (including OpenAI's own logos in ZDNet's hands-on test). Vector composite for trademark-grade work.

---

## Source authorities

Cross-referenced across the series. Primary tier:

- **OpenAI Cookbook — Image Gen Prompting Guide** (`developers.openai.com/cookbook/examples/multimodal/image-gen-models-prompting-guide`)
- **OpenAI API Docs — Images, Pricing, Changelog** (`developers.openai.com/api/docs/*`)
- **OpenAI Codex CLI Features** (`developers.openai.com/codex/cli/features`)
- **OpenAI Dev Community launch thread** (`community.openai.com/t/introducing-gpt-image-2-available-today-in-the-api-and-codex/1379479`)
- **OpenAI blog launch** (`openai.com/index/introducing-chatgpt-images-2-0/`)

Secondary tier (multi-source verified):

- Pixo, Framia, fal.ai, Imagine.art, NoteGPT, UpUply, Morphic, Apiyi, PixVerse, WaveSpeed, LaoZhang, danielvaughan.com, ZDNet
- GitHub awesome lists: `Anil-matcha/Awesome-GPT-Image-2-API-Prompts`, `ZeroLu/awesome-gpt-image`
- Each individual artifact carries its own Citations section.

---

## Next moves

- Read `06-anti-slop.md` and `02-prompt-anatomy.md` end to end.
- Apply the labelled-block contract to the next imagegen run. Compare output against an unstructured prompt for the same subject.
- Capture wins and surprises back to cm as `kind: lesson` entries tagged `helioy-imagegen` so they aggregate against the `helioy-imagegen-primatives` skill.
