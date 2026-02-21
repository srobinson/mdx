---
title: gpt-image-2 Official API Reference
type: research
tags: [gpt-image-2, openai, codex, image-generation, api-contract]
summary: Ground-truth contract for OpenAI gpt-image-2 (released 2026-04-21). Endpoints, parameters, output specs, pricing, safety, Codex CLI integration.
status: active
confidence: high
created: 2026-05-18
updated: 2026-05-18
---

# gpt-image-2 Official API Reference

OpenAI's flagship image model, released 2026-04-21 (snapshot `gpt-image-2-2026-04-21`). Successor to `gpt-image-1.5`. This document captures the API contract only; creative prompting technique lives elsewhere.

## TL;DR for prompters

1. Two model IDs work today: `gpt-image-2` (tracks latest snapshot) and `gpt-image-2-2026-04-21` (pinned).
2. Three endpoints: `POST /v1/images/generations`, `POST /v1/images/edits`, and the `image_generation` tool inside `POST /v1/responses`. For Responses, put a mainline model (e.g. `gpt-5.4`) in `model` and attach the tool. (source: https://blog.laozhang.ai/en/posts/gpt-image-2-api)
3. Prompt budget is large: `prompt` accepts up to 32,000 characters (source: https://developers.openai.com/api/reference/resources/images/methods/generate). Skip resolution words like "4K" or "8K" in the text; `size` is the only control that affects output dimensions.
4. `quality` is `low | medium | high | auto`. At 1024x1024 the cost ratio is roughly 1 : 9 : 35 (low : medium : high). Iterate at `low`, finalize at `high`.
5. `size` accepts presets (`1024x1024`, `1536x1024`, `1024x1536`, plus larger 2K/4K presets) or arbitrary `WIDTHxHEIGHT`. Both edges must be multiples of 16, max edge 3840, aspect ratio between 1:3 and 3:1, total pixels 655,360 to 8,294,400 (source: https://developers.openai.com/api/docs/guides/image-generation).
6. Transparent backgrounds are NOT supported on gpt-image-2. Requesting `background: "transparent"` fails. Use gpt-image-1.5 if you need alpha (source: https://wavespeed.ai/blog/posts/gpt-image-2-api-guide/).
7. `input_fidelity` is gone. gpt-image-2 always processes reference images at high fidelity, so edits using references are more expensive than they were on gpt-image-1.5 (source: https://fal.ai/learn/tools/gpt-image-2-vs-gpt-image-1-5).
8. Edits accept up to 16 reference images, PNG/WebP/JPG, each less than 50MB. Optional `mask` is a PNG with alpha; transparent pixels are the regions to regenerate (source: https://developers.openai.com/api/reference/python/resources/images/methods/edit).
9. Outputs are always base64-encoded for gpt-image-2 (no `response_format: "url"`). Output format selectable: `png` (default), `jpeg`, `webp`. C2PA metadata is embedded; a pixel-level watermark is also present on gpt-image-2 outputs.
10. Org Verification is required before gpt-image-2 calls go through. Moderation has two stages (prompt and generated image); refusals come back as `400` with no retry value.

## 1. Model identification

| Field | Value | Source |
|---|---|---|
| Family | GPT Image | https://developers.openai.com/api/docs/models/gpt-image-2 |
| Generation | 3rd (gpt-image-1 -> gpt-image-1.5 -> gpt-image-2) | https://developers.openai.com/api/docs/changelog |
| Latest alias | `gpt-image-2` | https://developers.openai.com/api/docs/models/gpt-image-2 |
| Pinned snapshot | `gpt-image-2-2026-04-21` | https://developers.openai.com/api/docs/models/gpt-image-2 |
| Release date | 2026-04-21 (API + Codex) | https://developers.openai.com/api/docs/changelog |
| Performance tier | Highest | https://developers.openai.com/api/docs/models/gpt-image-2 |
| Speed tier | Medium | https://developers.openai.com/api/docs/models/gpt-image-2 |
| Fine-tuning | Not supported | https://developers.openai.com/api/docs/models/gpt-image-2 |
| Function calling | Not supported on the image endpoint itself | https://developers.openai.com/api/docs/models/gpt-image-2 |
| Streaming | Supported on generations and edits; partial frames over SSE | https://developers.openai.com/api/reference/resources/images/generation-streaming-events |

Pin to the snapshot for production. Aliases will rotate when the next snapshot ships.

## 2. API surface

### 2.1 Endpoints

| Endpoint | Modality | Notes |
|---|---|---|
| `POST /v1/images/generations` | text -> image | Pure text-to-image. Streaming optional. |
| `POST /v1/images/edits` | text + image(s) (+ mask) -> image | Up to 16 reference images; mask inpaints. |
| `POST /v1/responses` with `tools: [{ "type": "image_generation" }]` | text + image in conversation -> image | Mainline model in `model` field; image tool runs gpt-image-2 internally. |
| `POST /v1/batch` | batch wrapping the above | 50% discount; 24h SLA. |

Sources: https://developers.openai.com/api/docs/models/gpt-image-2, https://developers.openai.com/api/docs/guides/image-generation, https://developers.openai.com/api/docs/changelog.

There is no separate `/variations` endpoint for gpt-image-2. Variations are produced by re-running `generations` with `n>1`, or by editing with no mask.

### 2.2 Request shape: `/v1/images/generations`

```json
POST /v1/images/generations
{
  "model": "gpt-image-2",
  "prompt": "...",
  "n": 1,
  "size": "1024x1024",
  "quality": "auto",
  "background": "auto",
  "output_format": "png",
  "output_compression": 100,
  "moderation": "auto",
  "stream": false,
  "partial_images": 0,
  "user": "stable-end-user-id"
}
```

### 2.3 Request shape: `/v1/images/edits`

`multipart/form-data` with these fields:

| Field | Type | Notes |
|---|---|---|
| `model` | string | `gpt-image-2` |
| `image` | file or repeated file | Up to 16; PNG/WebP/JPG; less than 50MB each |
| `mask` | file | Optional; PNG with alpha; applied to first `image` |
| `prompt` | string | Up to 32,000 chars |
| `n` | int | 1 to 10 |
| `size` | string | Preset or `WIDTHxHEIGHT` |
| `quality` | string | `low | medium | high | auto` |
| `background` | string | `auto | opaque` (transparent unsupported) |
| `output_format` | string | `png | jpeg | webp` |
| `output_compression` | int | 0 to 100 (jpeg/webp only) |
| `moderation` | string | `auto | low` |
| `partial_images` | int | 0 to 3 |
| `stream` | bool | true to enable SSE |
| `user` | string | End-user attribution |

Sources: https://developers.openai.com/api/reference/python/resources/images/methods/edit, https://developers.openai.com/api/docs/guides/image-generation.

`input_fidelity` is rejected for gpt-image-2; pass it only on gpt-image-1 / gpt-image-1.5.

### 2.4 Response shape (non-streaming)

```json
{
  "created": 1745000000,
  "background": "opaque",
  "output_format": "png",
  "quality": "high",
  "size": "1024x1024",
  "data": [
    {
      "b64_json": "...",
      "revised_prompt": "..."   // optional
    }
  ],
  "usage": {
    "total_tokens": 4322,
    "input_tokens": 122,
    "output_tokens": 4200,
    "input_tokens_details": { "text_tokens": 122, "image_tokens": 0 }
  }
}
```

gpt-image-2 outputs are always `b64_json`. Hosted URLs (`response_format: "url"`) are a DALL-E artifact and are silently ignored. Source: https://developers.openai.com/api/reference/resources/images/methods/generate.

### 2.5 Streaming events

When `stream: true` and `partial_images > 0`, SSE delivers:

| Event | Fields |
|---|---|
| `image_generation.partial_image` | `type`, `b64_json`, `created_at`, `size`, `quality`, `background`, `output_format`, `partial_image_index` |
| `image_generation.completed` | `type`, `b64_json`, `created_at`, `size`, `quality`, `background`, `output_format`, `usage` |
| `image_edit.partial_image` | same shape as generation partial |
| `image_edit.completed` | same shape as generation completion |

Source: https://developers.openai.com/api/reference/resources/images/generation-streaming-events.

Each partial frame adds 100 image output tokens to the bill. Fast generations may complete before all partials are emitted; treat partial count as a ceiling.

### 2.6 Responses API tool form

```json
POST /v1/responses
{
  "model": "gpt-5.4",
  "input": "Generate a product hero image for the new SKU and explain the composition.",
  "tools": [
    {
      "type": "image_generation",
      "action": "auto",
      "quality": "high",
      "size": "1536x1024",
      "background": "auto",
      "output_format": "png",
      "partial_images": 2,
      "input_image_mask": { "file_id": "file_abc" }
    }
  ]
}
```

Critical: `model` is a chat-capable mainline model (e.g. `gpt-5.4`). gpt-image-2 is invoked by the tool, not by `model`. Image inputs in the conversation are referenced through file IDs, base64 data URLs, or fully qualified URLs. Source: https://developers.openai.com/api/docs/guides/image-generation, https://blog.laozhang.ai/en/posts/gpt-image-2-api.

The `action` parameter controls generate vs edit behavior:

| Value | Behavior |
|---|---|
| `auto` (default) | Model decides between new generation and editing prior image |
| `generate` | Force fresh generation, ignore prior images |
| `edit` | Force edit of an image already in the conversation |

## 3. Parameter reference

### 3.1 `prompt`

| Property | Value |
|---|---|
| Type | string |
| Required | yes |
| Min length | 2 chars (source: https://developers.openai.com/api/reference/resources/images/methods/generate) |
| Max length | 32,000 chars for all GPT image models |
| Tokenization | Counted as text input tokens; billed at $5.00 per 1M (source: https://developers.openai.com/api/docs/pricing) |

Prompt rewriting: a `revised_prompt` field MAY appear in `data[].revised_prompt` and in Responses tool output. On DALL-E-3 this was always the rewritten copy; on gpt-image-2 the field reflects safety / clarity rewrites when they happen and is otherwise omitted. Treat its presence as a signal of silent rewrites.

### 3.2 `size`

| Mode | Allowed values |
|---|---|
| Preset | `auto`, `1024x1024`, `1536x1024`, `1024x1536` |
| Extended presets in some clients | `1024x768`, `2048x2048`, `2048x1152`, `3840x2160`, `2160x3840` |
| Arbitrary | `WIDTHxHEIGHT` with both dims divisible by 16 |
| Bounds | max edge 3840, aspect 1:3 to 3:1, total pixels 655,360 to 8,294,400 |
| Experimental zone | above 2560x1440 marked experimental in third-party docs (source: https://runware.ai/docs/models/openai-gpt-image-2 inferred from search snippet) |

Source for bounds: https://developers.openai.com/api/docs/guides/image-generation, https://wavespeed.ai/blog/posts/gpt-image-2-api-guide/.

### 3.3 `quality`

| Value | Use |
|---|---|
| `low` | Drafts, ideation, thumbnails. Cheapest per image. |
| `medium` | Balanced |
| `high` | Final assets, small text, dense detail |
| `auto` (default) | Model picks; biased toward `medium` |

There is no documented `quality: "thinking"` parameter on the public API. Third parties report a `quality_mode` flag or a `thinking` knob (off / low / medium / high); none of these are confirmed in the official OpenAI model page or image generation guide as of writing. Treat reasoning-on-image as an internal behavior of the model that may activate automatically on complex prompts. Sources: https://dev.to/tokenmixai/gpt-image-2-api-developer-guide-pricing-thinking-mode-and-production-integration-2026-28p5 (community), https://developers.openai.com/api/docs/models/gpt-image-2 (does not mention).

### 3.4 `n`

| Property | Value |
|---|---|
| Range | 1 to 10 (per https://developers.openai.com/api/reference/python/resources/images/methods/edit) |
| Default | 1 |
| Cost | Linear; each image incurs its own output tokens |
| Coherence | Same prompt across `n>1` may share style; not guaranteed identity-stable |

Batched `n` calls share request overhead and per-call rate-limit cost. Use them for style sweeps.

### 3.5 `background`

| Value | Behavior on gpt-image-2 |
|---|---|
| `auto` (default) | Opaque background chosen by model |
| `opaque` | Solid background, format may be jpeg or png |
| `transparent` | REJECTED on gpt-image-2; use gpt-image-1.5 |

Source: https://wavespeed.ai/blog/posts/gpt-image-2-api-guide/.

### 3.6 `output_format` and `output_compression`

| Format | When to use | Compression |
|---|---|---|
| `png` (default) | Lossless, alpha, charts and UI | Ignored |
| `jpeg` | Latency-sensitive, photographic, no alpha | 0 to 100 |
| `webp` | Smaller artifacts, supports alpha but gpt-image-2 won't emit alpha | 0 to 100 |

`jpeg` is observably faster than `png` per OpenAI's guide. Source: https://developers.openai.com/api/docs/guides/image-generation.

### 3.7 `moderation`

| Value | Behavior |
|---|---|
| `auto` (default) | Standard filtering for prompt and generated image |
| `low` | Looser content filtering, still hard caps on disallowed content |

Source: https://developers.openai.com/api/docs/guides/image-generation. Setting `low` does NOT disable safety classifiers; it widens latitude inside policy.

### 3.8 `response_format`

DALL-E carryover. For gpt-image-2 the value is forced to base64. Setting `url` does not error but is ignored. Treat as deprecated for this model.

### 3.9 `user`

Pass a stable per-end-user identifier. Used by OpenAI abuse monitoring; mandatory if you serve untrusted users.

### 3.10 Seed

Not exposed for gpt-image-2. Image generation across GPT image models is not reproducible by seed; passing `seed` is ignored. Determinism is not a guarantee even with images in chat completions. Source: https://medium.com/@fahad.a.arsal/i-thought-gpt-4s-seed-made-it-deterministic-until-i-used-an-image-1d77b8caf908.

### 3.11 `partial_images`

| Property | Value |
|---|---|
| Range | 0 to 3 |
| Default | 0 |
| Cost | 100 image output tokens per partial frame |
| Effective only when | `stream: true` |

### 3.12 Reference inputs (edits)

| Property | Value |
|---|---|
| Max count | 16 reference images |
| Per-file size | less than 50MB |
| Practical recommendation | less than 1.5MB; large files dominate latency (source: https://help.apiyi.com/en/gpt-image-2-upload-best-practices-en.html, community) |
| Accepted formats | PNG, WebP, JPG |
| Input fidelity | Always high; no opt-out |
| Mask | One PNG with alpha; applied to first reference |

When you pass `image_urls` plus a mask, only the first image is masked; the rest serve as style or content references.

## 4. Output specifications

| Aspect | gpt-image-2 |
|---|---|
| Max resolution | 3840 x 2160 (4K landscape) or 2160 x 3840 (4K portrait) |
| Min resolution | 655,360 total pixels (e.g. ~810x810 square) |
| Aspect ratios | 1:3 to 3:1 |
| Increment | both edges multiples of 16 |
| Encoding | base64 always |
| Formats | png (default), jpeg, webp |
| Alpha | Not emitted; png is opaque |
| Hosted URL | Not supported |
| C2PA metadata | Embedded on all outputs |
| Pixel watermark | Present, imperceptible, survives most re-encoding (source: https://glitchwire.com/news/x-user-claims-to-have-extracted-gpt-image-2s-hidden-watermark-heres-what-that-me/) |

C2PA confirms generative origin; the pixel watermark is content-bound and survives screenshots. Commercial use is permitted by OpenAI Terms; the watermark does not restrict licensing.

## 5. Limits and constraints

### 5.1 Token and size limits

| Limit | Value |
|---|---|
| Prompt | 32,000 chars |
| Reference images per edit | 16 |
| Per-file upload | less than 50MB |
| Mask file size | less than 4MB on dall-e-2 path; mirrored for safety on gpt-image-2 |
| Max image edge | 3840 px |
| Min total pixels | 655,360 |
| Max total pixels | 8,294,400 |
| Aspect range | 1:3 to 3:1 |

### 5.2 Rate limits

Image-per-minute (IPM) and tokens-per-minute (TPM) are tracked separately per usage tier:

| Tier | TPM | IPM |
|---|---|---|
| Tier 1 | 100,000 | 5 |
| Tier 2 | 250,000 | 20 |
| Tier 3 | 800,000 | 50 |
| Tier 4 | 3,000,000 | 150 |
| Tier 5 | 8,000,000 | 250 |

Source: https://developers.openai.com/api/docs/models/gpt-image-2.

### 5.3 Safety classifier behavior

Two-stage moderation per https://help.apiyi.com/en/fix-gpt-image-2-moderation-blocked-400-error-en.html (community summarization, consistent with OpenAI policy posts):

| Stage | When | What it scans | Failure mode |
|---|---|---|---|
| Pre-inference | After request, before model | Prompt text and reference images | `400 moderation_blocked` |
| Post-inference | After image generated | Generated pixels | `400 moderation_blocked`, image discarded, not billable |

Refusals are 400-class errors. Retrying the same prompt will fail again. The response body carries a `safety_violations` field identifying the category. Categories include hate, violence, sexual content, self-harm, public figures, copyrighted likenesses.

### 5.4 Silent rewrites vs hard rejections

- Hard rejection: 400 with `moderation_blocked`. Prompt or reference image hits a categorical rule. No bill.
- Silent rewrite: request succeeds, `revised_prompt` returned. The model rewrote your prompt to dodge a soft violation. Billed normally. Inspect this field if outputs feel sanitized.

Source: https://developers.openai.com/api/docs/guides/image-generation, https://developers.openai.com/cookbook/examples/multimodal/image-gen-models-prompting-guide.

### 5.5 Org verification

API access to gpt-image-2 requires API Organization Verification in the developer console. Without it the model returns a permission error. Source: https://developers.openai.com/api/docs/guides/image-generation.

## 6. Pricing

### 6.1 Token rates

| Lane | Standard ($ / 1M tokens) | Batch ($ / 1M tokens) |
|---|---|---|
| Text input | $5.00 | $2.50 |
| Image input | $8.00 | $4.00 |
| Cached image input | $2.00 | $1.00 |
| Image output | $30.00 | $15.00 |

Sources: https://developers.openai.com/api/docs/pricing, https://wavespeed.ai/blog/posts/gpt-image-2-pricing-2026/.

Batch API (`/v1/batch`) cuts every lane by 50% with a 24h SLA.

### 6.2 Per-image cost (standard, USD)

OpenAI publishes these as estimates from the in-docs calculator, not list prices. Real numbers depend on prompt size and reference inputs.

| Size | Low | Medium | High |
|---|---|---|---|
| 1024 x 1024 | $0.006 | $0.053 | $0.211 |
| 1024 x 1536 (portrait) | $0.005 | $0.041 | $0.165 |
| 1536 x 1024 (landscape) | $0.005 | $0.041 | $0.165 |
| 3840 x 2160 (4K) | ~$0.012 | ~$0.10 | ~$0.401 |

Sources: https://developers.openai.com/api/docs/guides/image-generation, https://wavespeed.ai/blog/posts/gpt-image-2-pricing-2026/.

Practical implications:

- Output token cost dominates. The size and quality knobs move the bill more than prompt length.
- Edit calls add reference image tokens at the high-fidelity rate (no low-fidelity option exists). For a 1024x1024 reference you can expect ~3,050 image input tokens (source: https://help.openai.com/en/articles/11128753-gpt-image-api, community-confirmed via https://fal.ai/learn/tools/gpt-image-2-vs-gpt-image-1-5).
- Batch API halves the bill if you can tolerate the 24h SLA.
- Each `partial_images` frame adds 100 output tokens (~$0.003 each).

### 6.3 Cost shape vs gpt-image-1.5

| Per-image (high) | 1.5 | 2 |
|---|---|---|
| 1024x1024 | $0.133 | $0.211 |
| 1024x1536 | $0.200 | $0.165 |
| 3840x2160 | n/a | $0.401 |

Source: https://fal.ai/learn/tools/gpt-image-2-vs-gpt-image-1-5.

gpt-image-2 is more expensive at 1024x1024 high, cheaper at portrait, and unlocks resolutions the prior model could not produce. Edit-heavy workflows pay more on gpt-image-2 because input_fidelity always rides high.

## 7. Differences from predecessors

| Dimension | gpt-image-1 | gpt-image-1.5 | gpt-image-2 |
|---|---|---|---|
| Release | Apr 2025 | Dec 2025 | Apr 2026 |
| Resolutions | 3 presets | 3 presets | Presets + arbitrary up to 3840 |
| `input_fidelity` | low / high | low / high | Removed; always high |
| `background: transparent` | Supported | Supported | NOT supported |
| Token pricing units | per 1K | per 1K | per 1M (10x cleaner accounting) |
| Multilingual text rendering | Weak | Improved | Strong: CJK and Latin near-correct |
| Reasoning before generation | None | None | Internal "thinking" stage for complex prompts |
| Multi-aspect coordinated outputs | No | Limited | Generate multiple aspect ratios in one prompt |
| Reference image limit | 10 | 16 | 16 |
| Watermark | C2PA only | C2PA only | C2PA + pixel watermark |
| Streaming partial frames | No | Yes | Yes |

Sources: https://developers.openai.com/cookbook/examples/multimodal/image-gen-models-prompting-guide, https://fal.ai/learn/tools/gpt-image-2-vs-gpt-image-1-5, https://wavespeed.ai/blog/posts/gpt-image-2-vs-gpt-image-1-5/.

Migration notes:

- Replace `model="gpt-image-1.5"` with `model="gpt-image-2"`. The prompt may need trimming; gpt-image-2 follows prose better and resents adjective stacks. Roughly 70% of older prompts improve simply by deleting filler (source: community).
- Drop any `input_fidelity` argument.
- Drop any `background: transparent` argument or move that workload to gpt-image-1.5.
- If you metered cost from per-1K token math, switch to per-1M.

## 8. Codex CLI integration

### 8.1 Invocation

Three entry points (source: https://codex.danielvaughan.com/2026/04/27/codex-cli-image-generation-gpt-image-2-visual-development-workflows/):

```bash
# Explicit skill invocation
codex "Create a dark-mode dashboard header banner $imagegen"

# Implicit skill selection (model routes by intent)
codex "Generate a set of SVG-style icons for a settings page"

# Interactive skill picker
codex
> /skills   # then choose imagegen
```

### 8.2 Skill source

The built-in skill ships at `codex-rs/skills/src/assets/samples/imagegen/SKILL.md` inside the Codex repository. The Codex changelog entry "Add gpt-image-2 to bundled OpenAI Docs skill (#19443)" landed in Codex CLI 0.128.0 on 2026-04-30. Source: https://developers.openai.com/codex/changelog.

### 8.3 Authentication

Two modes:

| Mode | How | Cost lane |
|---|---|---|
| ChatGPT plan (Plus, Pro, Team) | Default OAuth login via Codex | Counts against plan limits; image turns consume 3 to 5x faster than text turns |
| API key | Set `OPENAI_API_KEY` | Bills against API account at standard rates |

Sources: https://developers.openai.com/codex/cli/features, https://developers.openai.com/codex/changelog.

For batch generation, the API-key mode is the only practical option; plan limits exhaust quickly.

### 8.4 Output location

Generated images land in `$CODEX_HOME/generated_images/`, defaulting to `~/.codex/generated_images/`. Move to your project tree as a follow-up step. Source: https://codex.danielvaughan.com/2026/04/27/codex-cli-image-generation-gpt-image-2-visual-development-workflows/.

### 8.5 Skill CLI surface

The bundled skill exposes a wrapper that maps to `/v1/images/generations` and `/v1/images/edits`. Community-maintained variants (e.g. https://github.com/wuyoscar/gpt_image_2_skill) document a representative flag set:

| Flag | Values | Notes |
|---|---|---|
| `-p, --prompt` | string | Required |
| `-f, --file` | path | Output path; default timestamped png |
| `-i, --image` | path (repeatable) | Routes to `/v1/images/edits`; up to 16 |
| `-m, --mask` | png path | Mask for first image |
| `--size` | `1k | 2k | 4k | portrait | landscape | square | WIDTHxHEIGHT` | Default `1024x1024` |
| `--quality` | `auto | low | medium | high` | Default `high` in the skill |
| `-n` | int | Batch count |
| `--background` | `auto | opaque` | Transparent rejected |
| `--moderation` | `auto | low` | Default `low` in some skills |
| `--format` | `png | jpeg | webp` | Output encoding |
| `--compression` | 0 to 100 | jpeg / webp only |

Codex App's built-in `image_gen` tool does not currently expose the full size grammar; see https://github.com/openai/codex/issues/19175 for the gap.

### 8.6 Environment variables

| Variable | Purpose |
|---|---|
| `OPENAI_API_KEY` | Switch billing to API account; read from process env, then `.env`, then `~/.env` |
| `CODEX_HOME` | Override default `~/.codex` root; image outputs nest under it |

### 8.7 Configuration

The imagegen skill respects `config.toml` for opt-out. Disable in `~/.codex/config.toml` if you need to keep Codex strictly text-only. Source: https://codex.danielvaughan.com/2026/04/27/codex-cli-image-generation-gpt-image-2-visual-development-workflows/.

## 9. Known gaps in official documentation

| Topic | Status | Where I fell back |
|---|---|---|
| Exact "thinking" / reasoning parameter name | Not documented on the OpenAI model page or guide; multiple community sources contradict each other (`quality_mode`, `thinking`, internal-only) | https://dev.to/tokenmixai/..., https://framia.pro/page/en-US/news/gpt-image-2-api-best-practices |
| Per-size pricing table beyond three sizes | Calculator only; not published as a table | https://wavespeed.ai/blog/posts/gpt-image-2-pricing-2026/ |
| `safety_violations` response field schema | Mentioned in error guides; not enumerated officially | https://help.apiyi.com/en/fix-gpt-image-2-moderation-blocked-400-error-en.html |
| Pixel watermark technical details | Not in OpenAI docs; demonstrated by independent researcher | https://glitchwire.com/news/x-user-claims-to-have-extracted-gpt-image-2s-hidden-watermark-heres-what-that-me/ |
| Mask max file size on gpt-image-2 | Documented at 4MB for dall-e-2; not restated for GPT image models | inferred from https://developers.openai.com/api/reference/python/resources/images/methods/edit |
| Reference image practical size cap | Official 50MB; community recommends 1.5MB for latency | https://help.apiyi.com/en/gpt-image-2-upload-best-practices-en.html |
| Codex `image_gen` built-in tool flag surface | Not exposed in Codex CLI features doc | https://github.com/openai/codex/issues/19175 |

## 10. Citations

Primary OpenAI sources:

- https://developers.openai.com/api/docs/models/gpt-image-2
- https://developers.openai.com/api/docs/guides/image-generation
- https://developers.openai.com/api/docs/pricing
- https://developers.openai.com/api/docs/changelog
- https://developers.openai.com/api/reference/resources/images/methods/generate
- https://developers.openai.com/api/reference/python/resources/images/methods/edit
- https://developers.openai.com/api/reference/resources/images/generation-streaming-events
- https://developers.openai.com/codex/cli/features
- https://developers.openai.com/codex/changelog
- https://developers.openai.com/cookbook/examples/multimodal/image-gen-models-prompting-guide
- https://community.openai.com/t/introducing-gpt-image-2-available-today-in-the-api-and-codex/1379479

Secondary corroboration:

- https://fal.ai/learn/tools/gpt-image-2-vs-gpt-image-1-5
- https://fal.ai/learn/tools/prompting-gpt-image-2
- https://wavespeed.ai/blog/posts/gpt-image-2-api-guide/
- https://wavespeed.ai/blog/posts/gpt-image-2-pricing-2026/
- https://wavespeed.ai/blog/posts/gpt-image-2-vs-gpt-image-1-5/
- https://blog.laozhang.ai/en/posts/gpt-image-2-api
- https://codex.danielvaughan.com/2026/04/27/codex-cli-image-generation-gpt-image-2-visual-development-workflows/
- https://github.com/openai/codex/issues/19175
- https://github.com/wuyoscar/gpt_image_2_skill
- https://help.apiyi.com/en/fix-gpt-image-2-moderation-blocked-400-error-en.html
- https://help.apiyi.com/en/gpt-image-2-upload-best-practices-en.html
- https://glitchwire.com/news/x-user-claims-to-have-extracted-gpt-image-2s-hidden-watermark-heres-what-that-me/
- https://dev.to/tokenmixai/gpt-image-2-api-developer-guide-pricing-thinking-mode-and-production-integration-2026-28p5
- https://framia.pro/page/en-US/news/gpt-image-2-api-best-practices
- https://runware.ai/docs/models/openai-gpt-image-2
