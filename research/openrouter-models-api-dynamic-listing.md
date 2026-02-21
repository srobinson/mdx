---
title: OpenRouter Models API - Dynamic Model Listing
type: research
tags: [openrouter, api, models, rust, typescript, next.js]
summary: GET /api/v1/models (no auth required) returns all models. Official @openrouter/sdk for TS and openrouter-rs/openrouter_api for Rust both have first-class model listing.
status: active
source: quick-research
confidence: high
created: 2026-03-11
updated: 2026-03-11
---

## Summary

OpenRouter exposes `GET https://openrouter.ai/api/v1/models` with no authentication required. It is OpenAI-compatible (same path as `/v1/models`). Both official TypeScript and third-party Rust SDKs wrap this endpoint with typed model objects. The response includes rich metadata: pricing per token per modality, context length, architecture/tokenizer, supported parameters, and modality flags.

---

## Details

### 1. REST Endpoint

```
GET https://openrouter.ai/api/v1/models
```

**Authentication**: Not required for the public list. Bearer token required for `listForUser` (which filters by user provider preferences, privacy settings, and guardrails).

**Query parameters** (all optional):

| Parameter | Type | Description |
|---|---|---|
| `category` | enum | Filter: `programming`, `roleplay`, `marketing`, `marketing/seo`, `technology`, `science`, `translation`, `legal`, `finance`, `health`, `trivia`, `academia` |
| `supported_parameters` | string | Filter by parameter name |
| `use_rss` | boolean | Return RSS format |
| `use_rss_chat_links` | boolean | Include RSS chat links |

**Response shape**:

```json
{
  "data": [
    {
      "id": "openai/gpt-4o",
      "canonical_slug": "openai/gpt-4o",
      "hugging_face_id": null,
      "name": "GPT-4o",
      "created": 1715367049,
      "description": "...",
      "context_length": 128000,
      "pricing": {
        "prompt": "0.0000025",
        "completion": "0.00001",
        "request": null,
        "image": "0.003613",
        "image_token": null,
        "image_output": null,
        "audio": null,
        "audio_output": null,
        "input_audio_cache": null,
        "web_search": null,
        "internal_reasoning": null,
        "input_cache_read": null,
        "input_cache_write": null,
        "discount": 0
      },
      "architecture": {
        "tokenizer": "...",
        "instruct_type": "chatml",
        "modality": "text+image->text",
        "input_modalities": ["text", "image"],
        "output_modalities": ["text"]
      },
      "top_provider": {
        "context_length": 128000,
        "max_completion_tokens": 16384,
        "is_moderated": true
      },
      "per_request_limits": {
        "prompt_tokens": "...",
        "completion_tokens": "..."
      },
      "supported_parameters": ["temperature", "top_p", "tools", ...],
      "default_parameters": { "temperature": 1.0, ... },
      "expiration_date": null
    }
  ]
}
```

**All model fields**:

- `id` - provider/model-name identifier
- `canonical_slug` - URL-safe slug
- `hugging_face_id` - optional HF model ID
- `name` - display name
- `created` - Unix timestamp
- `description` - markdown description
- `context_length` - max input tokens (null if unknown)
- `pricing.prompt` / `.completion` - cost per token as decimal string (USD)
- `pricing.image`, `.audio`, `.web_search`, `.internal_reasoning`, `.input_cache_read`, `.input_cache_write`, `.discount` - optional modality/feature pricing
- `architecture.tokenizer` - tokenizer family (ModelGroup enum)
- `architecture.instruct_type` - prompt format (claude, chatml, llama3, mistral, gemma, etc.)
- `architecture.input_modalities` / `.output_modalities` - `text`, `image`, `video`, `audio`, `file`
- `top_provider.max_completion_tokens` - max output tokens
- `top_provider.is_moderated` - content moderation flag
- `supported_parameters` - which API params this model accepts
- `default_parameters` - temperature, top_p, top_k defaults
- `expiration_date` - ISO 8601 date or null

A separate endpoint returns just the count:
```
GET https://openrouter.ai/api/v1/models/count
```

### 2. OpenAI Compatibility

Yes. OpenRouter uses the same base path `/api/v1` and the same `/models` route. If you point the OpenAI SDK at `https://openrouter.ai/api/v1` and call `client.models.list()`, it works. The response schema is compatible (both return a `data` array with `id` fields). OpenRouter models follow the `provider/model-name` convention for IDs.

### 3. Rust Crates

| Crate | Version | Downloads | Notes |
|---|---|---|---|
| `openrouter-rs` | 0.6.0 | ~9k | Type-safe SDK, most downloads. Has `client.models().list().await?`, `list_by_category()`, `get_model_count()`. |
| `openrouter_api` | 0.5.1 | ~5.5k | Also has models API with `ModelsQuery`, `ModelSort`, filtering and search. |
| `openrouter` | 0.2.0 | ~2.1k | Minimal wrapper, basic API interaction. |

**openrouter-rs** (recommended for idiomatic API):

```rust
use openrouter_rs::OpenRouterClient;

let client = OpenRouterClient::builder()
    .api_key("sk-or-...")
    .http_referer("https://yourapp.com")
    .x_title("My App")
    .build()?;

let models = client.models().list().await?;
let count = client.models().get_model_count().await?;
```

**openrouter_api** alternative with filtering:

```rust
use openrouter_api::{OpenRouterClient, Result};
use openrouter_api::types::models::{ModelsQuery, ModelSort};

let client = OpenRouterClient::new()
    .with_base_url("https://openrouter.ai/api/v1/")?
    .with_api_key(api_key)?;

let models = client.models()?.list().await?;
let filtered = client.models()?.search(
    ModelsQuery::new().with_sort(ModelSort::Name)
).await?;
```

### 4. TypeScript / npm Packages

| Package | Weekly Downloads | Notes |
|---|---|---|
| `@openrouter/ai-sdk-provider` | ~793k | **Official Vercel AI SDK provider.** Best for Next.js. No model listing built-in - use REST directly. |
| `@openrouter/sdk` | ~395k | **Official TypeScript SDK** (Speakeasy-generated). Has full model listing. |
| `@tanstack/ai-openrouter` | ~3.5k | TanStack AI adapter |
| `@langchain/openrouter` | ~1k | LangChain.js integration |

**For Next.js - two patterns**:

**Pattern A: Vercel AI SDK + direct fetch for model list**

Use `@openrouter/ai-sdk-provider` for inference, fetch `/api/v1/models` directly for the picker:

```ts
// No auth needed for public model list
const response = await fetch('https://openrouter.ai/api/v1/models');
const { data } = await response.json();
// data: Array<{ id, name, context_length, pricing, architecture, ... }>
```

**Pattern B: Official @openrouter/sdk**

```ts
import OpenRouter from '@openrouter/sdk';

const client = new OpenRouter({ apiKey: process.env.OPENROUTER_API_KEY });

const { data: models } = await client.models.list();
// models: ModelsListResponse with full typed Model objects

const count = await client.models.count();

// List filtered to user's provider preferences (requires auth)
const userModels = await client.models.listForUser();
```

The `@openrouter/sdk` `Models` class exposes exactly three methods:
- `count(request?, options?)` - GET `/models/count`
- `list(request?, options?)` - GET `/models`
- `listForUser(security, request?, options?)` - GET `/models?` filtered by user settings

For a Next.js model picker, `list()` with no auth is the right call. Cache the result (models don't change minute-to-minute) with a reasonable TTL.

### 5. Caching Recommendation

The models list is large (300+ models) and changes infrequently. Cache server-side with a 1-hour TTL. In Next.js:

```ts
// app/api/models/route.ts
export const revalidate = 3600; // ISR - revalidate every hour

export async function GET() {
  const res = await fetch('https://openrouter.ai/api/v1/models');
  const data = await res.json();
  return Response.json(data);
}
```

---

## Sources

- Live API response: `https://openrouter.ai/api/v1/models` (confirmed returns data with no auth)
- OpenRouter OpenAPI spec: `https://openrouter.ai/openapi.json`
- Official TypeScript SDK source: `https://github.com/OpenRouterTeam/typescript-sdk`
  - `src/sdk/models.ts` - three methods: `count`, `list`, `listForUser`
  - `src/models/model.ts` - full `Model` type definition (Zod-validated)
  - `src/models/publicpricing.ts` - all pricing fields
  - `src/models/modelarchitecture.ts` - architecture/instruct type enums
- `openrouter-rs` v0.6.0: `https://crates.io/crates/openrouter-rs`
- `openrouter_api` v0.5.1: `https://crates.io/crates/openrouter_api`

---

## Open Questions

- Pricing values are returned as decimal strings (e.g. `"0.0000025"`) - parse as `f64`/`number` before displaying. Multiply by 1,000,000 for per-million-token display.
- `listForUser` vs `list`: the user-scoped endpoint filters out models the user has blocked via provider preferences. For a public-facing picker, `list` is correct. For a per-user picker, `listForUser` with their API key is better.
- Free models: pricing of `"0"` on both prompt and completion. Could filter the picker to show free-only with `pricing.prompt === "0"`.
