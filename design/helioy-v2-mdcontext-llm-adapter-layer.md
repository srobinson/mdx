# Helioy V2: Mdcontext LLM Adapter Layer

Date: 2026-03-12
Status: Design direction
Author: Codex

## Purpose

This note defines a practical provider strategy for `mdcontext` if it grows beyond retrieval and context assembly into:

- ingestion-time normalization
- LLM-assisted markdown reformatting
- rewrite-on-disk flows
- AI summarization beyond deterministic compression

The key product question is:

**Can mdcontext let developers use the AI subscriptions they already pay for, instead of forcing API billing from day one?**

The answer is:

- yes, in some cases
- but only through a provider model that separates API-backed adapters from subscription-backed runtime adapters

## Core Distinction

There are two fundamentally different integration models.

### 1. API-Backed Providers

Examples:

- OpenAI API
- Anthropic API
- OpenRouter
- Voyage
- local inference endpoints

Characteristics:

- stable programmatic surface
- clean request/response semantics
- explicit billing
- easiest to automate at scale

### 2. Subscription-Backed Runtime Adapters

Examples:

- OpenAI Codex with ChatGPT-backed access
- Anthropic Claude Code with subscription-backed access where available

Characteristics:

- developer leverages an existing paid product subscription
- integration goes through a product runtime or SDK, not a generic model API
- often cheaper for the individual developer
- ergonomically attractive
- less infrastructure-stable than raw APIs

This distinction should be explicit in the architecture.

## Why This Matters for Mdcontext

`mdcontext` is easier to adopt if it can say:

- use your current subscription if you already have one
- use the API only when you need backend-grade automation

That is a better adoption wedge than:

- index your markdown
- then immediately buy another API plan

For an open-source tool targeting the source community, subscription leverage is a meaningful product advantage.

## Current Product Constraints

### OpenAI

OpenAI separates normal API billing from ChatGPT billing.

Officially:

- ChatGPT subscriptions and the API are billed separately
- a ChatGPT plan does not automatically include standard API usage

Sources:

- https://help.openai.com/en/articles/8156019-how-can-i-move-my-chatgpt-subscription-to-the-api
- https://help.openai.com/en/articles/9039756-billing-settings-in-chatgpt-vs-platform

However, OpenAI also documents Codex usage through eligible ChatGPT plans and provides a Codex SDK/programmatic surface.

Sources:

- https://help.openai.com/en/articles/11369540-using-codex-with-your-chatgpt-plan
- https://openai.com/index/introducing-the-codex-app/
- https://help.openai.com/en/articles/11381614

So the implication is:

- generic OpenAI API calls remain separate billing
- Codex-specific runtime usage may be subscription-backed

### Anthropic

Anthropic also separates normal API Console billing from standard Claude.ai subscription billing.

Officially:

- paid Claude.ai plans do not automatically include API Console usage

Source:

- https://support.anthropic.com/en/articles/9876003-i-subscribe-to-a-paid-claude-ai-plan-why-do-i-have-to-pay-separately-for-api-usage-on-console

Anthropic also documents Claude Code as a product runtime with unified subscription behavior in some plan contexts, especially Team and Enterprise premium-seat environments, and exposes a Claude Code SDK.

Sources:

- https://support.anthropic.com/en/articles/11845131-using-claude-code-with-your-enterprise-plan
- https://docs.anthropic.com/s/claude-code-sdk

So the implication is:

- generic Anthropic API usage remains Console-credit based
- Claude Code can behave more like a product runtime than a generic API endpoint

## Architectural Recommendation

`mdcontext` should not model all LLM access as “provider = API.”

It should use a two-lane adapter architecture:

- `ApiProvider`
- `RuntimeProvider`

### Proposed Interface Split

```typescript
type LlmTask =
  | "summarize_search_results"
  | "normalize_markdown"
  | "rewrite_markdown"
  | "extract_structure"
  | "generate_frontmatter"

interface LlmAdapter {
  id: string
  kind: "api" | "runtime"
  supports(task: LlmTask): boolean
  invoke(request: LlmRequest): Promise<LlmResponse>
}
```

Then implement two classes of adapters.

## Adapter Types

### API Adapters

Examples:

- `openai-api`
- `anthropic-api`
- `openrouter-api`
- `ollama-local`

Best for:

- CI
- backend services
- batch ingestion
- deterministic automation
- headless multi-user deployments

### Runtime Adapters

Examples:

- `codex-runtime`
- `claude-code-runtime`

Best for:

- local developer workflows
- one-off document normalization
- interactive or semi-attended ingestion
- teams that already pay for subscriptions

These adapters should be treated as:

- product-runtime integrations
- not direct substitutes for clean API infrastructure

## Recommended Product Modes

The cleanest product framing is three modes.

### Mode A: Local Deterministic

No LLM required.

Use:

- parser
- section index
- BM25
- semantic retrieval if local embeddings are configured
- deterministic summarizer

This is the current `mdcontext` strength.

### Mode B: Local AI-Enhanced

Use subscription-backed runtime adapters where available.

Examples:

- `codex-runtime`
- `claude-code-runtime`

Use cases:

- normalize newly ingested markdown
- reformat documents into a canonical house style
- generate better summaries
- infer frontmatter or metadata

This is the easiest sell for many developers.

### Mode C: Headless Automation

Use API-backed providers.

Examples:

- `openai-api`
- `anthropic-api`
- `openrouter-api`

Use cases:

- CI normalization
- large corpus ingestion
- scheduled jobs
- team backends
- multi-tenant hosted workflows

This is the more enterprise-stable path.

## Where Runtime Adapters Fit Best

Runtime adapters are most valuable for:

- local ingestion-time normalization
- local rewrite-on-disk flows
- interactive “clean this corpus” sessions
- summary or transform tasks a developer runs on demand

They are less ideal for:

- unattended large-scale pipelines
- cloud-hosted indexing services
- system-to-system integrations with strong SLA expectations

So the right use of runtime adapters is:

- optional
- developer-facing
- local-first

not:

- core infrastructure assumption

## Mdcontext Capability Mapping

### Current deterministic core

- index markdown
- build structural indexes
- build BM25
- build embeddings
- hybrid search
- deterministic section-aware context assembly

### Candidate LLM-enhanced tasks

- normalize inconsistent markdown on ingest
- rewrite documents into a known canonical format
- generate frontmatter fields
- infer section labels or summaries
- produce richer thematic abstracts than heuristic summarization
- convert ad hoc docs into mdcontext-preferred structure

These tasks should route through the adapter layer, not be hard-coded to one provider.

## Naming Implication

If the product moves in the direction you described, then `mdcontext` is no longer just:

- retrieval

It begins to become:

- ingestion + normalization + retrieval + context assembly

That makes your naming discomfort understandable.

If the tool increasingly supports canonicalization and structure-shaping, a name like:

- `mdx`

starts to imply:

- markdown transformed into a higher-value usable representation

That said, the current codebase still materially behaves as `mdcontext`, not yet as a full canonicalization engine.

## Concrete Design Recommendation

Add a new provider layer with these explicit adapter IDs:

- `openai-api`
- `anthropic-api`
- `openrouter-api`
- `ollama-local`
- `codex-runtime`
- `claude-code-runtime`

Expose them behind task-level capability checks:

```typescript
interface LlmRequest {
  task: LlmTask
  input: string
  instructions?: string
  budget?: {
    maxTokens?: number
    maxCostUsd?: number
  }
}
```

Runtime adapters should advertise only the tasks they can safely support.

For example:

- `codex-runtime`
  - `normalize_markdown`
  - `rewrite_markdown`
  - `summarize_search_results`

- `claude-code-runtime`
  - `normalize_markdown`
  - `rewrite_markdown`
  - `summarize_search_results`

API adapters can support the same tasks, but are better suited for headless workflows.

## Product Messaging Recommendation

The strongest product message is probably:

**mdcontext works great without any LLM.  
When you want AI-enhanced normalization or summaries, it can use either APIs or the coding subscriptions you already pay for.**

That is much easier to sell than:

- install mdcontext
- then configure another provider account

## Practical Constraint to Keep Clear

You should not claim:

- “your OpenAI subscription gives you generic API usage”
- or
- “your Claude subscription gives you generic Anthropic API usage”

Those are not the current product boundaries.

The correct claim is:

- mdcontext can support subscription-backed runtime adapters where the provider exposes a usable product runtime

That is a narrower but solid claim.

## Final Recommendation

For mdcontext, the right long-term provider architecture is:

- deterministic core by default
- optional AI enhancement through an adapter layer
- support both:
  - API-backed providers
  - subscription-backed runtime adapters

This gives the project:

- strong open-source ergonomics
- better adoption among individual developers
- a path to enterprise automation later

The best immediate next step would be to define the adapter interface and make `summarize_search_results` the first shared task across all provider types.
