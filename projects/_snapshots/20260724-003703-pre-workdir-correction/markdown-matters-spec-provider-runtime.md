---
title: markdown-matters provider runtime extraction
project: markdown-matters
status: ready
created: 2026-04-08
phase: 1 of 2
owner: stuart
---

# Provider Runtime Extraction (Phase 1)

## Why

`markdown-matters` has provider resolution logic in two places. The embedding path resolves credentials, base URLs, model defaults, and pricing through `src/embeddings/openai-provider.ts` and `src/embeddings/provider-factory.ts`. The HyDE path resolves the same concerns independently in `src/embeddings/hyde.ts` with its own constants, fallback rules, and pricing table. PR #24 (`feat/hyde-configurable-provider`, 2026-04-07) introduced the duplication; the regression review on `fix/hyde-no-effect` documents three concrete bugs caused by drift between the two paths:

1. **High.** HyDE auth and provider labeling are still hardwired to OpenAI in `src/embeddings/hyde.ts:175` and `src/embeddings/hyde.ts:219`, even though the embedding factory already supports OpenRouter via `src/embeddings/openai-provider.ts:158`. A caller using `providerConfig.provider = 'openrouter'` with only `OPENROUTER_API_KEY` set can build/query embeddings but `semanticSearch(..., { hyde: true })` fails with `OPENAI_API_KEY not set`. Downstream provider-specific remediation messages are mislabeled as openai.
2. **Medium.** `resolveHydeOptions` in `src/embeddings/semantic-search.ts:802` drops a custom provider baseURL whenever the caller explicitly pins the same HyDE provider. The gate `hydeOptions?.provider === undefined` silently falls back to localhost via `src/embeddings/hyde.ts:191`. Configuration like `{ providerConfig: { provider: 'ollama', baseURL: 'http://my-host:11434/v1' }, hydeOptions: { provider: 'ollama' } }` breaks private Ollama, LM Studio, and OpenRouter proxy deployments as soon as the caller writes the provider name redundantly for clarity.
3. **Medium.** HyDE cost reporting fabricates dollar amounts for non-OpenAI models. The defaults at `src/embeddings/hyde.ts:102` include local and OpenRouter models, but the cost lookup at `src/embeddings/hyde.ts:230` only knows OpenAI model ids and falls back to gpt-4o-mini pricing for everything else. Local inference reports nonzero cost; custom OpenRouter models report wrong cost.

These are not three unrelated bugs. They are direct consequences of having two implementations of the same provider state machine. Fixing them tactically perpetuates the duplication. The durable fix is to extract a use case agnostic provider runtime and migrate both consumers onto it.

## Architectural Shape

Three layers:

- **Provider layer.** Owns transport, auth, endpoint selection, capability availability. Knows nothing about embeddings, HyDE, summarization, or any future feature.
- **Capability layer.** Owns the API surface for `embed`, `generateText`, and (future) `rerank`. Each provider exposes the capabilities it supports.
- **Feature layer.** HyDE, semantic search, and any future consumer asks the runtime for a capability and uses it. Feature code is a consumer, not a second provider implementation.

### Type contract

```ts
type ProviderId = 'openai' | 'openrouter' | 'ollama' | 'lm-studio' | 'voyage'
type Capability = 'embed' | 'generateText' | 'rerank'

interface ProviderRuntime {
  readonly id: ProviderId
  readonly baseURL?: string
  readonly capabilities: {
    readonly embed?: EmbeddingClient
    readonly generateText?: TextClient
    readonly rerank?: RerankClient
  }
}

interface EmbeddingClient {
  embed(
    texts: readonly string[],
    options?: EmbedOptions,
  ): Effect.Effect<EmbeddingResult, EmbeddingError>
}

interface TextClient {
  generateText(
    prompt: string,
    options?: GenerateTextOptions,
  ): Effect.Effect<TextGenerationResult, TextGenerationError>
}

// RerankClient defined as a typed slot in phase 1, no implementation
interface RerankClient {
  rerank(
    query: string,
    documents: readonly string[],
    options?: RerankOptions,
  ): Effect.Effect<RerankResult, RerankError>
}
```

Models bind to capabilities, not features. `gpt-4o-mini` is a generateText model. `text-embedding-3-small` is an embed model. `voyage-rerank-2` is (in phase 2) a rerank model. Nothing is "a HyDE model" or "an embedding feature model."

## Contract Decisions

These are decisions, not options.

1. **Effect throughout.** Every client method returns `Effect.Effect<T, E>`. No mixed Promise/Effect signatures inside the runtime. Existing `OpenAIProvider.embed` returns `Promise`; that signature is replaced during the embedding migration.

2. **No `fallbackProvider` concept.** When the requested provider does not support the requested capability (voyage + generateText), the runtime errors immediately with `CapabilityNotSupported`. No silent substitution. The feature layer sees the error and the feature layer decides what to do; in phase 1 HyDE simply propagates the error upward. The user resolves the mismatch in their config.

3. **No OpenRouter → `OPENAI_API_KEY` compatibility fallback.** If the user selects `provider: 'openrouter'` and `OPENROUTER_API_KEY` is unset, the runtime fails fast. Breaking change for any user relying on the existing compat shim. Documented in CHANGELOG; the runtime error itself does not mention the deprecation.

4. **Pricing data is nested by capability.** `pricing.json` restructures from flat-by-model to:
   ```json
   {
     "embed": {
       "text-embedding-3-small": { "input": 0.02 },
       "text-embedding-3-large": { "input": 0.13 },
       "voyage-3": { "input": 0.06 }
     },
     "generateText": {
       "gpt-4o-mini": { "input": 0.15, "output": 0.6 },
       "gpt-4o": { "input": 2.5, "output": 10 }
     }
   }
   ```
   Pricing is keyed by model. The capability binding is self-evident from the structure. Local providers (ollama, lm-studio) and OpenRouter custom models are absent from the table; lookup miss returns `cost = 0` rather than fabricating gpt-4o-mini pricing.

5. **Error message UX is actionable only.** All runtime errors follow the rule from `~/.claude/projects/-Users-alphab-Dev-LLM-DEV-helioy/memory/feedback_error_messages.md`. Tell the user what to set; do not include deprecation history, version-bump justifications, or design rationale. Examples:
   - Missing key: `OpenRouter requires OPENROUTER_API_KEY. Set OPENROUTER_API_KEY=sk-or-...`
   - Capability mismatch: `voyage does not support generateText. Set hydeOptions.provider to one of: openai, openrouter, ollama, lm-studio.`

## Scope

### In scope (Phase 1)

- New `src/providers/` module containing the runtime types, registry, and OpenAI-compatible HTTP transport adapter.
- One transport adapter for all four OpenAI-compatible providers (openai, openrouter, ollama, lm-studio). Single source of truth for credential resolution, base URL resolution, sentinel keys for local providers, and provider-specific capability availability.
- `voyage` provider registered with `embed` only; no `generateText`, no `rerank`.
- Migrate `src/embeddings/openai-provider.ts` consumers onto `runtime.capabilities.embed`. Delete the file once unused.
- Migrate `src/embeddings/hyde.ts` onto `runtime.capabilities.generateText`. Delete `HydeProviderName`, `DEFAULT_BASE_URLS_BY_PROVIDER`, `DEFAULT_ENV_VARS_BY_PROVIDER`, `DEFAULT_MODELS_BY_PROVIDER`, `PROVIDER_DISPLAY_NAMES`, `PROVIDERS_REQUIRING_API_KEY`, `LOCAL_PROVIDER_API_KEY_PLACEHOLDER`, and `LLM_PRICING`. Direct `import OpenAI from 'openai'` is removed from `hyde.ts`.
- Move `resolveHydeOptions` logic out of `src/embeddings/semantic-search.ts:785-820`. Inheritance becomes a small helper at the feature layer (`hyde.ts` or a sibling), not at the runtime layer.
- `pricing.json` restructured to capability-keyed shape. Both consumers read from the new shape.
- `provider-constants.ts` collapsed into the runtime as the single registry. Existing `inferProviderFromUrl` moves into the runtime.
- Test matrix exercising the same provider resolution paths across `embed` and `generateText`. Cover the three findings from the regression review explicitly.
- Delete the existing provider-constants sync test. It catches constant-set drift but not behavioral drift, and it was the false safety net that let PR #24 ship.

### Out of scope (Phase 2, follow-on sub-issues under the same Linear parent)

- Native API providers via Vercel AI SDK (anthropic, google gemini, deepseek, qwen). Subsumes ALP-220.
- CLI transport adapter for `claude` CLI and other CLI providers in `src/summarization/cli-providers/`.
- Local in-process inference adapter for `Xenova/ms-marco-MiniLM-L-6-v2` cross-encoder rerank in `src/search/cross-encoder.ts`.
- Migration of `src/summarization/provider-factory.ts` consumers.
- Migration of `src/search/cross-encoder.ts` consumers onto the rerank capability.
- Voyage rerank (`voyage-rerank-2`) and Cohere rerank.

Phase 2 is contingent on the phase 1 runtime shape settling. Designing all four transports up front means the runtime has to anticipate edge cases from systems we have not built yet.

## File Layout

```
src/providers/
├── index.ts                       # public exports
├── runtime.ts                     # ProviderRuntime type, capability dispatch
├── registry.ts                    # provider registration, lookup
├── errors.ts                      # CapabilityNotSupported, MissingApiKey, ...
├── pricing.ts                     # capability-keyed pricing lookup
├── transports/
│   └── openai-compatible.ts       # transport adapter for openai/openrouter/ollama/lm-studio
└── capabilities/
    ├── embed.ts                   # EmbeddingClient interface + factory
    ├── generate-text.ts           # TextClient interface + factory
    └── rerank.ts                  # RerankClient interface (typed slot, no impl)

src/embeddings/
├── hyde.ts                        # rewritten: ~50 lines, consumes runtime
├── semantic-search.ts             # resolveHydeOptions removed, runtime-aware
├── openai-provider.ts             # DELETED
├── provider-factory.ts            # DELETED
├── provider-constants.ts          # DELETED (merged into runtime registry)
└── pricing.json                   # restructured to nested-by-capability
```

## Acceptance Criteria

These criteria are inherited by every sub-issue under the Linear parent.

- One source of truth for provider auth, base URL, capability availability, and pricing lookup. No parallel implementation in `hyde.ts` or anywhere else.
- `hyde.ts` does not `import OpenAI from 'openai'`. It consumes the runtime.
- Embeddings and HyDE can use different models without duplicating provider logic. Model selection lives at the feature layer; provider resolution lives at the runtime layer.
- OpenRouter auth works consistently for both embeddings and HyDE: setting only `OPENROUTER_API_KEY` makes both work.
- Explicit custom base URLs (private Ollama, self-hosted LM Studio, OpenRouter proxies) are honored by both embeddings and HyDE regardless of whether the caller writes `hydeOptions.provider` redundantly.
- Cost reporting returns 0 for local providers and unknown models rather than fabricating gpt-4o-mini pricing.
- Voyage + HyDE produces a `CapabilityNotSupported` error with actionable remediation, not a silent fall through.
- Missing `OPENROUTER_API_KEY` produces a fail-fast error pointing the user at the correct env var. No mention of deprecation history.
- Provider-matrix test coverage exercises the same resolution paths across `embed` and `generateText`, including the three findings.
- The `provider-constants` sync test is deleted; it does not exist in any form after phase 1.
- All client methods return `Effect.Effect<T, E>`. No Promise return types inside `src/providers/`.

## Sub-issue Decomposition

The sub-issues below correspond 1:1 to local task chain (#3 onward). Each is independently completable in roughly 30-120 minutes of focused work.

1. **Scaffold `src/providers/` runtime types and registry.** Capability-typed runtime interface. ProviderId union. Effect-returning client method contracts. RerankClient interface defined as typed slot, no implementation. No consumers wired yet. File layout above.

2. **Implement OpenAI-compatible HTTP transport adapter.** Single transport for openai/openrouter/ollama/lm-studio. Resolves credentials, base URL, sentinel keys for local providers. Surfaces both `embed` and `generateText` capabilities. Mark voyage as `embed`-only at registration time.

3. **Restructure `pricing.json` to nested-by-capability.** Migrate the existing flat structure. Add the four generateText models from `hyde.ts`'s `LLM_PRICING`. Update the pricing lookup to read from the new shape. Lookup miss returns 0.

4. **Migrate embeddings consumer onto runtime.** Replace `OpenAIProvider` construction in `semantic-search.ts` and any other call sites with `runtime.capabilities.embed`. Delete `provider-factory.ts` and `openai-provider.ts` once unused.

5. **Migrate HyDE consumer onto runtime, delete duplication.** Rewrite `hyde.ts` to consume `runtime.capabilities.generateText`. Delete the eight duplicated constants and the inline `LLM_PRICING`. Remove the direct `import OpenAI from 'openai'`. Move `resolveHydeOptions` logic out of `semantic-search.ts` into a small inheritance helper at the feature layer.

6. **Wire fail-fast errors for capability mismatches and missing keys.** Implement `CapabilityNotSupported` for voyage + generateText. Drop the OpenRouter → `OPENAI_API_KEY` compat fallback with a clean missing-key error. All error messages follow the actionable-only rule.

7. **Add provider-matrix tests across embed and generateText.** Test the same resolution paths across both capabilities. Cover the three findings from the regression review explicitly: openrouter auth, custom-host inheritance, non-OpenAI cost reporting. Delete the existing `provider-constants` sync test.

8. **Verify three findings are gone, open PR.** Run the full test suite. Manually exercise the three findings from the review. Open the refactor PR with a conventional-commit title and a link back to this spec.

## Code Review

After phase 1 sub-issues are complete, spawn `helioy-tools:engineering-code-reviewer` (or `clinical-reviewer`) with this spec as input. The reviewer validates:

- The runtime has a single source of truth for each concern (auth, baseURL, pricing, capability availability)
- No provider plumbing exists outside `src/providers/`
- All three findings are exercised by tests and pass
- Error messages match the actionable-only rule
- The Effect contract is consistent across all client methods
- Phase 2 work has not crept in

## Memory References

- **Pattern memory.** `cm: 019d69d1-abd5-7ff3-95ee-8f4a532f0cbd` — *Never duplicate provider/credential plumbing in a parallel module.* Provides the rule that this refactor exists to enforce.
- **Lesson memory.** `cm: 019d69d2-0812-7531-bde6-3155e7d8083f` — *Type-narrowing-aversion is a duplication smell.* The rationalization that let PR #24 ship.
- **Decision memory.** `cm: 019d6ad8-fde3-7252-b700-b5697a5742dc` — *Provider runtime refactor: scope, phasing, and contract decisions.* The session decisions captured in cm at repo scope.
- **Feedback memory.** `cm: 019d6ad7-bb24-7442-92b1-b1e378251f3d` — *Error message UX: actionable only.* The rule for runtime error wording.
