# LiteLLM Patterns: Universal LLM API Gateway Architecture

## Research Date: 2026-02-14

## Why This Matters for Nancy

Nancy orchestrates autonomous agents that need to call different LLM providers. Today that
means Claude (via Anthropic API or CLI), but tomorrow it means OpenAI, Gemini, local models
via Ollama, and whatever ships next month. We need a universal model API layer in Rust that
abstracts provider differences, handles failures gracefully, and tracks costs.

LiteLLM is the dominant open-source solution (31K GitHub stars, used by Netflix, Adobe, Rocket Money).
Its patterns are battle-tested. We don't want to run LiteLLM -- we want to extract its
architectural patterns and implement them natively in Rust.

---

## 1. LiteLLM Core Architecture

### The Big Idea: Adapter Pattern with OpenAI as Lingua Franca

LiteLLM's entire design rests on one decision: **OpenAI's API format is the canonical interface**.
Every provider gets translated to/from OpenAI format. This is the single most important pattern.

```
Your App (OpenAI format)
    |
    v
litellm.completion()         <-- unified entry point
    |
    v
Provider Detection            <-- "anthropic/claude-3" -> provider="anthropic"
    |
    v
Request Transformer           <-- OpenAI messages -> Anthropic messages format
    |
    v
HTTP Call to Provider
    |
    v
Response Transformer          <-- Anthropic response -> OpenAI ChatCompletion format
    |
    v
Your App (OpenAI format)
```

### Why OpenAI Format Won

- OpenAI was first to market with a clean REST API
- Massive ecosystem of tools, SDKs, and tutorials already assume OpenAI format
- Most providers now offer "OpenAI-compatible" endpoints anyway
- The format is simple: messages array, model string, parameters object
- Switching cost for existing apps: change one line (base_url)

### Provider Adapter Pattern (BaseConfig)

Each provider implements a config class extending `BaseConfig` with these methods:

| Method                              | Purpose                                           |
| ----------------------------------- | ------------------------------------------------- |
| `validate_environment()`            | Check API keys, set auth headers                  |
| `get_complete_url()`                | Build the provider-specific endpoint URL          |
| `transform_request()`               | Convert OpenAI-format input to provider's format  |
| `transform_response()`              | Convert provider's response back to OpenAI format |
| `get_sync_custom_stream_wrapper()`  | Handle streaming response translation             |
| `get_async_custom_stream_wrapper()` | Async streaming variant                           |

The adapter does NOT make HTTP calls. A shared `BaseLLMHTTPHandler` handles all HTTP
concerns (timeouts, retries, connection pooling). The adapter only transforms data.

**Key insight: Separation of concerns between data transformation and HTTP transport.**

### Provider Detection Logic

LiteLLM uses a prefix convention: `provider/model-name`

```
"openai/gpt-4"           -> provider = openai
"anthropic/claude-3"      -> provider = anthropic
"azure/gpt-4-deployment"  -> provider = azure
"bedrock/anthropic.claude" -> provider = bedrock
"ollama/llama3"           -> provider = ollama
"groq/llama3-8b-8192"    -> provider = groq
```

For OpenAI-compatible providers, a single JSON config file is enough -- no code needed.
This is a data-driven provider registry pattern.

---

## 2. Request Lifecycle (Life of a Request)

LiteLLM Proxy processes every request through this pipeline:

```
1. REQUEST ARRIVES (/chat/completions, OpenAI-compatible)
   |
2. VIRTUAL KEY VALIDATION
   |- Check Redis cache / in-memory cache for key
   |- If miss: lookup in PostgreSQL
   |- Validate: is key active? under budget? correct permissions?
   |
3. RATE LIMITING (MaxParallelRequestsHandler)
   |- Global server rate limit (RPM/TPM)
   |- Virtual key rate limit
   |- User rate limit
   |- Team rate limit
   |
4. ROUTER (LiteLLM Router)
   |- Select deployment from model group
   |- Apply routing strategy (shuffle, least-busy, latency-based, cost-based)
   |- Pre-call checks (context window, region)
   |
5. PROVIDER ADAPTER (litellm.completion())
   |- Transform request to provider format
   |- Make HTTP call
   |- Transform response to OpenAI format
   |
6. POST-PROCESSING (async, non-blocking)
   |- Log to LangFuse/MLflow/Lunary/etc.
   |- Update RPM/TPM counters
   |- Update spend tracking in DB
   |- Update cost per key/user/team
```

**Critical design choice: DB writes are NEVER on the hot path.** All post-processing
is async background tasks. The only sync DB operation is the virtual key lookup, and
that's cached in Redis.

---

## 3. Router & Load Balancing

### Model Groups and Deployments

LiteLLM separates **model names** (what the user asks for) from **deployments** (actual
provider endpoints). Multiple deployments can serve the same model name.

```yaml
model_list:
  # Three deployments, all serving "gpt-3.5-turbo"
  - model_name: gpt-3.5-turbo # <-- user-facing alias
    litellm_params:
      model: azure/chatgpt-v-2 # <-- actual deployment
      api_key: ...
      api_base: https://eastus.openai.azure.com/
      rpm: 900 # <-- capacity hint

  - model_name: gpt-3.5-turbo
    litellm_params:
      model: azure/chatgpt-v-3
      api_base: https://westus.openai.azure.com/
      rpm: 10

  - model_name: gpt-3.5-turbo
    litellm_params:
      model: gpt-3.5-turbo # <-- direct OpenAI
      api_key: ...
```

**This is the key abstraction**: callers say "gpt-3.5-turbo", the router picks the
best deployment. This enables transparent failover across providers.

### Routing Strategies

| Strategy                                  | How It Works                         | When to Use                      |
| ----------------------------------------- | ------------------------------------ | -------------------------------- |
| **simple-shuffle** (default, recommended) | Weighted random based on RPM/weight  | General purpose, lowest overhead |
| **least-busy**                            | Fewest active concurrent requests    | High concurrency scenarios       |
| **latency-based**                         | Tracks response times, picks fastest | Latency-sensitive apps           |
| **usage-based**                           | Lowest current TPM/RPM usage         | Respecting rate limits evenly    |
| **cost-based**                            | Cheapest deployment first            | Cost optimization                |
| **custom**                                | Plugin any strategy via trait        | Special routing logic            |

**Performance warning from LiteLLM docs**: Usage-based routing adds significant latency
due to Redis operations. They recommend simple-shuffle for production. Lesson: the
simplest strategy that works is the right one.

### Deployment Health & Cooldowns

When a deployment fails:

- **429 (rate limit)**: Immediate cooldown, 5s default
- **401/404/408**: Non-retryable, immediate cooldown
- **>50% failure rate in current minute**: Cooldown
- Recovery is automatic after cooldown expires

Each deployment gets a deterministic `model_id` hash from its `litellm_params`, enabling
independent health tracking.

### Fallback Chains

If all retries fail for a model group, fall back to a different model group entirely:

```yaml
litellm_settings:
  fallbacks: [{ "gpt-3.5-turbo": ["gpt-4", "claude-3-haiku"] }]
  num_retries: 3
  # After 3 retries on gpt-3.5-turbo deployments fail,
  # try gpt-4 deployments, then claude-3-haiku deployments
```

### Pre-Call Checks

Before routing, the router can filter deployments by:

- Context window size (won't send a 10K token prompt to a 4K deployment)
- Geographic region (EU-only deployments for compliance)
- Available capacity (under RPM/TPM limits)

---

## 4. Virtual Keys, Budgets, and Multi-Tenancy

### Virtual Keys

LiteLLM creates proxy API keys that wrap real provider keys:

```
Client sends: Authorization: Bearer sk-litellm-xxxxx
Proxy maps to: Real OpenAI key, Anthropic key, etc.
```

Benefits:

- Clients never see real API keys
- Revoke access without rotating provider keys
- Different keys can access different model groups
- Budget/rate limits per key

### Budget Hierarchy

```
Global Proxy Budget ($X/month)
  |
  +-- Team Budget ($Y/month)
  |     |
  |     +-- User Budget ($Z/month)
  |     |
  |     +-- Virtual Key Budget ($W/month)
  |
  +-- Team Budget ...
```

Budgets enforce:

- Max spend (USD) with configurable reset periods (30s, 30m, 30h, 30d)
- Max RPM/TPM per key/user/team
- Max parallel requests (semaphore-based)
- Model access restrictions per key

### Cost Tracking

LiteLLM maintains a JSON cost map (`model_prices_and_context_window.json`) with
per-model pricing for input/output tokens. After every request:

1. Count tokens (prompt + completion)
2. Look up per-token cost for the specific model
3. Calculate cost = (input_tokens _ input_price) + (output_tokens _ output_price)
4. Async update to PostgreSQL: increment spend for key, user, team
5. Available via API: `/spend/logs`, `/global/spend`, per-key spend queries

Custom pricing supported: `input_cost_per_token`, `output_cost_per_token`, even
`input_cost_per_second` for inference endpoints like SageMaker.

---

## 5. Streaming Architecture

### The Challenge

Every provider streams differently:

- **OpenAI**: SSE with `data: {"choices": [{"delta": {"content": "..."}}]}`
- **Anthropic**: SSE with `event: content_block_delta` / `data: {"delta": {"text": "..."}}`
- **Google**: SSE or chunked JSON arrays
- **Ollama**: NDJSON (newline-delimited JSON)

### LiteLLM's Solution: CustomStreamWrapper

Each provider adapter can define custom stream handling. The `streaming_handler.py`
normalizes all provider streams into OpenAI's SSE chunk format:

```
data: {"id":"...","object":"chat.completion.chunk","choices":[{"delta":{"content":"token"}}]}
```

The client always sees OpenAI-compatible SSE regardless of which provider is actually
responding. This is the same adapter pattern applied to streaming.

### Streaming + Routing Interaction

Streaming complicates load balancing because:

- You commit to a deployment at stream start
- Token counting happens at stream end
- Failures mid-stream require the full response to be lost

LiteLLM handles this by:

1. Selecting deployment before stream starts (normal routing)
2. Accumulating tokens during streaming for post-request cost tracking
3. If stream fails mid-response, the request fails -- no mid-stream failover

---

## 6. Key Design Decisions & Trade-offs

### What LiteLLM Gets Right

1. **OpenAI as the canonical format** -- lowest adoption friction
2. **Config-driven, not code-driven** -- YAML model_list, not if/else chains
3. **Async post-processing** -- DB writes never block responses
4. **Deployment-level health tracking** -- not model-level
5. **Separation: data transform vs HTTP transport** -- clean adapter pattern
6. **Cost map as data, not code** -- JSON file, easily updated/synced from GitHub

### Where LiteLLM Struggles

1. **Python performance ceiling** -- at sustained high concurrency (1000+ RPS),
   memory grows, tail latency spikes. Bifrost (Go) claims 50x lower latency overhead.
2. **Provider adapter sprawl** -- adding a provider requires touching 5+ files
   (init, main, constants, provider_logic, streaming_handler). This is the main
   pain point of the codebase.
3. **Global mutable state** -- litellm uses module-level globals extensively
   (litellm.api_key, litellm.openai_key, etc.), making testing and isolation hard.
4. **Redis dependency for production** -- cooldown tracking and usage-based routing
   require Redis in multi-instance deployments.

### Provider-Specific Features

How LiteLLM handles features that don't exist in all providers:

| Feature               | Approach                                        |
| --------------------- | ----------------------------------------------- |
| Tool/function calling | Pass through if provider supports, error if not |
| Vision (image inputs) | Adapter transforms image format per provider    |
| Structured output     | Pass through JSON schema where supported        |
| Prompt caching        | Provider-specific param passthrough             |
| Extended thinking     | Provider-specific param passthrough             |

The pattern: **normalize what you can, pass through what you can't**. Provider-specific
params go in `litellm_params` and get forwarded to the adapter.

---

## 7. Alternatives Landscape (2026)

### LiteLLM (Python, Open Source, YC W23)

- **Strengths**: 100+ providers, massive community, most flexible
- **Weaknesses**: Python performance ceiling, complex codebase
- **Best for**: Prototyping, Python-first teams, moderate traffic
- **Stats**: 31K GitHub stars, 8ms P95 latency at 1K RPS

### OpenRouter (Cloud Service)

- **Model**: SaaS marketplace -- one API key, pay per token, OpenRouter handles billing
- **Strengths**: Zero ops, 4.2M users, supports nearly every model
- **Weaknesses**: Not self-hosted, you're routing through their servers (latency, privacy)
- **Best for**: Individual developers, prototyping, when you don't want to manage keys
- **Key difference**: OpenRouter is a marketplace (they resell API access).
  LiteLLM is infrastructure (you bring your own keys).

### Bifrost by Maxim AI (Go, Open Source)

- **Model**: High-performance LLM gateway, Apache 2.0
- **Strengths**: 11us gateway overhead at 5K RPS (50x faster than LiteLLM), Go runtime,
  adaptive load balancing, built-in observability UI, cluster mode
- **Weaknesses**: ~15 providers (vs LiteLLM's 100+), newer ecosystem
- **Best for**: High-traffic production systems where latency matters
- **Stats**: 2.3K GitHub stars, growing fast
- **Key insight for Nancy**: Bifrost proves that a compiled language (Go) massively
  outperforms Python for this use case. Rust would be even better.

### Portkey (Managed + Open Source Gateway)

- **Model**: "Control Panel for Production AI" -- cloud-hosted gateway with open-source core
- **Strengths**: 250+ models, MCP gateway support, detailed observability, guardrails,
  per-customer virtual keys, tiered model access
- **Weaknesses**: Pricing based on "recorded logs" (confusing), managed service dependency
- **Best for**: Enterprise teams with multi-tenant requirements
- **Key insight for Nancy**: Portkey's multi-tenant architecture (per-customer keys,
  tiered model access, budget enforcement) is relevant for Nancy's team/project model.

### Cloudflare AI Gateway (Edge, Managed)

- **Model**: Edge-deployed gateway, part of Cloudflare's platform
- **Strengths**: Global edge deployment, caching, tight Workers integration
- **Weaknesses**: Cloudflare lock-in, limited self-hosting
- **Best for**: Teams already on Cloudflare

### Kong AI Gateway (Go/Lua, Enterprise)

- **Model**: Extension of Kong's API management platform to AI traffic
- **Strengths**: Enterprise API governance, plugin ecosystem, MCP support
- **Weaknesses**: Heavy setup, enterprise pricing (~$500/mo+)
- **Best for**: Enterprises already standardized on Kong

### Rust-Native Alternatives

| Crate                  | Stars | Providers | Notes                                                                                        |
| ---------------------- | ----- | --------- | -------------------------------------------------------------------------------------------- |
| **graniet/llm** (rllm) | 305   | 12+       | Builder pattern, multi-step chains, tool calling, REST API serving. Most mature Rust option. |
| **llm-connector**      | ~110  | 11+       | Protocol/Provider separation, strong typing, universal streaming                             |
| **mozilla-ai/any-llm** | --    | Several   | Mozilla's unified Rust LLM client                                                            |
| **darval/multi-llm**   | 2     | 4         | Type-safe, async-first, early stage                                                          |
| **dongri/llm-api-rs**  | 4     | Several   | Minimal unified client                                                                       |

**None of these are gateways.** They're client libraries. Nobody has built a
production LLM gateway in Rust yet. Bifrost (Go) is the closest compiled-language
alternative.

---

## 8. Patterns to Extract for Nancy's Rust Implementation

### Pattern 1: Canonical Message Format (OpenAI-Compatible)

```rust
// Nancy's canonical types -- OpenAI-compatible
pub struct ChatCompletionRequest {
    pub model: String,
    pub messages: Vec<Message>,
    pub temperature: Option<f64>,
    pub max_tokens: Option<u32>,
    pub stream: Option<bool>,
    pub tools: Option<Vec<Tool>>,
    // ... standard OpenAI params
    pub provider_params: Option<serde_json::Value>, // passthrough for provider-specific
}

pub struct ChatCompletionResponse {
    pub id: String,
    pub model: String,
    pub choices: Vec<Choice>,
    pub usage: Usage,
}
```

### Pattern 2: Provider Adapter Trait

```rust
#[async_trait]
pub trait ProviderAdapter: Send + Sync {
    /// Validate auth, return headers
    fn validate_environment(&self, config: &ProviderConfig) -> Result<HeaderMap>;

    /// Build the full URL for the API call
    fn get_endpoint_url(&self, model: &str, config: &ProviderConfig) -> Result<Url>;

    /// Transform canonical request -> provider-specific body
    fn transform_request(
        &self,
        request: &ChatCompletionRequest,
        config: &ProviderConfig,
    ) -> Result<serde_json::Value>;

    /// Transform provider response -> canonical response
    fn transform_response(
        &self,
        raw: &serde_json::Value,
        model: &str,
    ) -> Result<ChatCompletionResponse>;

    /// Transform a streaming chunk -> canonical SSE chunk
    fn transform_stream_chunk(
        &self,
        chunk: &[u8],
    ) -> Result<Option<ChatCompletionChunk>>;

    /// List of capabilities this provider supports
    fn capabilities(&self) -> ProviderCapabilities;
}

pub struct ProviderCapabilities {
    pub streaming: bool,
    pub tool_calling: bool,
    pub vision: bool,
    pub structured_output: bool,
    pub prompt_caching: bool,
}
```

### Pattern 3: Model Registry (Config-Driven)

```rust
// Data-driven, not code-driven. YAML/TOML config.
pub struct ModelDeployment {
    pub model_name: String,          // user-facing alias ("fast", "smart", "cheap")
    pub provider: ProviderType,      // anthropic, openai, ollama, etc.
    pub model_id: String,            // actual model: "claude-sonnet-4-20250514"
    pub api_base: Option<Url>,
    pub api_key_env: String,         // env var name, never store keys directly
    pub rpm: Option<u32>,
    pub tpm: Option<u32>,
    pub weight: Option<u32>,
    pub order: Option<u32>,          // priority for ordered routing
    pub region: Option<String>,
    pub input_cost_per_token: Option<f64>,
    pub output_cost_per_token: Option<f64>,
    pub context_window: Option<u32>,
}

pub struct ModelRegistry {
    deployments: Vec<ModelDeployment>,
    // model_name -> Vec<DeploymentIndex>
    groups: HashMap<String, Vec<usize>>,
}
```

### Pattern 4: Router with Pluggable Strategy

```rust
#[async_trait]
pub trait RoutingStrategy: Send + Sync {
    async fn select_deployment(
        &self,
        group: &[&ModelDeployment],
        health: &HealthTracker,
        request: &ChatCompletionRequest,
    ) -> Result<usize>;
}

pub struct WeightedShuffleStrategy;   // default, recommended
pub struct LeastBusyStrategy;
pub struct LatencyBasedStrategy;
pub struct CostBasedStrategy;

pub struct Router {
    registry: ModelRegistry,
    strategy: Box<dyn RoutingStrategy>,
    health: HealthTracker,
    num_retries: u32,
    fallbacks: HashMap<String, Vec<String>>, // model_name -> fallback model_names
}
```

### Pattern 5: Health Tracking with Cooldowns

```rust
pub struct DeploymentHealth {
    pub deployment_id: u64,     // hash of deployment config
    pub failures_this_minute: AtomicU32,
    pub total_this_minute: AtomicU32,
    pub cooled_down_until: Option<Instant>,
    pub avg_latency_ms: AtomicU64,
    pub active_requests: AtomicU32,
}

pub struct HealthTracker {
    deployments: DashMap<u64, DeploymentHealth>,
    cooldown_duration: Duration,
    max_failure_rate: f64,      // 0.5 = 50% failure -> cooldown
}
```

### Pattern 6: Cost Tracking

```rust
pub struct CostMap {
    // model_id -> (input_cost_per_token, output_cost_per_token)
    prices: HashMap<String, (f64, f64)>,
}

pub struct RequestCost {
    pub model: String,
    pub input_tokens: u32,
    pub output_tokens: u32,
    pub input_cost: f64,
    pub output_cost: f64,
    pub total_cost: f64,
}

// Async cost recording -- NEVER on the hot path
pub async fn record_cost(cost: RequestCost, key_id: &str, db: &SqlitePool) {
    // fire-and-forget via tokio::spawn
}
```

### Pattern 7: Streaming Normalization

```rust
pub trait StreamNormalizer: Send + Sync {
    /// Parse a raw SSE/NDJSON/chunked line from the provider
    /// Returns None for keep-alive / non-content events
    fn normalize_chunk(&self, raw: &str) -> Result<Option<ChatCompletionChunk>>;
}

// The router returns a unified stream regardless of provider
pub type CompletionStream = Pin<Box<dyn Stream<Item = Result<ChatCompletionChunk>> + Send>>;
```

---

## 9. What Nancy Needs vs What LiteLLM Provides

| Need                       | LiteLLM Equivalent                                       | Nancy Approach                                                  |
| -------------------------- | -------------------------------------------------------- | --------------------------------------------------------------- |
| Call Claude API            | `litellm.completion("anthropic/claude-3.5-sonnet", ...)` | `ProviderAdapter` for Anthropic                                 |
| Call OpenAI API            | `litellm.completion("gpt-4", ...)`                       | `ProviderAdapter` for OpenAI                                    |
| Call local models          | `litellm.completion("ollama/llama3", ...)`               | `ProviderAdapter` for Ollama                                    |
| Orchestrate Claude CLI     | Not supported                                            | Nancy-specific: `AgentBackend` trait (different from model API) |
| Failover between providers | Router fallback chains                                   | Same pattern, Rust Router                                       |
| Track costs                | PostgreSQL spend tracking                                | SQLite (nancyr already uses rusqlite)                           |
| Rate limiting              | MaxParallelRequestsHandler                               | tokio::sync::Semaphore + governor crate                         |
| Config-driven models       | YAML model_list                                          | TOML config (Rust ecosystem standard)                           |
| Streaming                  | CustomStreamWrapper + SSE                                | tokio-stream + async generators                                 |

### What Nancy Does NOT Need from LiteLLM

- Virtual keys / multi-tenant key management (Nancy is single-user/team)
- 100+ provider support (start with 3: Anthropic, OpenAI, Ollama)
- Redis for distributed state (Nancy is single-node for now)
- HTTP proxy server (Nancy embeds the model layer, doesn't expose it)

### What Nancy Needs That LiteLLM Doesn't Have

- **Agent orchestration**: Managing Claude CLI processes, not just API calls
- **File-based IPC**: Nancy's inbox/outbox message passing for agent communication
- **Task state machines**: Agent lifecycle management (planning, executing, reviewing)
- **Multi-worker coordination**: Parallel agent execution with shared context

---

## 10. Recommended Architecture for Nancy's Model Layer

```
nancy::model_api
  |
  +-- types.rs              // Canonical OpenAI-compatible types
  |
  +-- provider/
  |     +-- mod.rs           // ProviderAdapter trait
  |     +-- anthropic.rs     // Claude API adapter
  |     +-- openai.rs        // OpenAI adapter
  |     +-- ollama.rs        // Local model adapter
  |     +-- registry.rs      // Config-driven provider registry
  |
  +-- router/
  |     +-- mod.rs           // Router with deployment selection
  |     +-- strategy.rs      // Routing strategy trait + implementations
  |     +-- health.rs        // Deployment health tracking + cooldowns
  |     +-- fallback.rs      // Fallback chain logic
  |
  +-- cost/
  |     +-- map.rs           // Model pricing data (JSON/TOML)
  |     +-- tracker.rs       // Async cost recording
  |
  +-- stream/
        +-- mod.rs           // Stream normalization + unified stream type
        +-- sse.rs           // SSE parsing utilities
```

### Implementation Priority

1. **types.rs + ProviderAdapter trait** -- the foundation everything else builds on
2. **anthropic.rs** -- Nancy's primary model provider
3. **openai.rs** -- most other tools expect this
4. **ollama.rs** -- local development without API keys
5. **Router + simple-shuffle** -- basic load balancing
6. **Health tracking** -- automatic cooldowns
7. **Cost tracking** -- know what you're spending
8. **Fallback chains** -- production resilience

### Key Rust Advantages Over LiteLLM's Python

1. **Zero-cost abstractions**: The adapter trait compiles to static dispatch, no vtable
   overhead for the common case (use `enum_dispatch` crate)
2. **Fearless concurrency**: tokio + DashMap for health tracking, no GIL
3. **Predictable latency**: No GC pauses, no Python startup overhead
4. **Type safety**: Provider capabilities checked at compile time via feature flags
5. **Memory efficiency**: No per-request allocation overhead from Python objects
6. **Single binary**: No Python environment, no pip, no virtualenv

---

## Sources

- [LiteLLM Docs: Life of a Request](https://docs.litellm.ai/docs/proxy/architecture)
- [LiteLLM Docs: Integrate as a Provider](https://docs.litellm.ai/docs/provider_registration/)
- [LiteLLM Docs: Router / Load Balancing](https://docs.litellm.ai/docs/routing)
- [LiteLLM Docs: Proxy Load Balancing](https://docs.litellm.ai/docs/proxy/load_balancing)
- [LiteLLM Docs: Virtual Keys](https://docs.litellm.ai/docs/proxy/virtual_keys)
- [LiteLLM Docs: Spend Tracking](https://docs.litellm.ai/docs/proxy/cost_tracking)
- [LiteLLM Docs: Budgets & Rate Limits](https://docs.litellm.ai/docs/proxy/users)
- [LiteLLM Docs: Fallback Management](https://docs.litellm.ai/docs/proxy/fallback_management)
- [LiteLLM Docs: Custom Pricing](https://docs.litellm.ai/docs/proxy/custom_pricing)
- [Top 5 LLM Gateways (2026)](https://dev.to/hadil/top-5-llm-gateways-for-production-in-2026-a-deep-practical-comparison-16p)
- [AI Gateways 2026 Landscape (TrueFoundry)](https://www.truefoundry.com/blog/a-definitive-guide-to-ai-gateways-in-2026-competitive-landscape-comparison)
- [LiteLLM vs OpenRouter (DensHub)](https://denshub.com/en/choosing-llm-gateway/)
- [Bifrost GitHub](https://getmax.im/bifrost)
- [graniet/llm Rust crate](https://github.com/graniet/llm)
- [llm-connector crate](https://lib.rs/crates/llm-connector)
- [Portkey AI Gateway](https://portkey.ai/buyers-guide/ai-gateway-solutions)
- [LiteLLM Market Overview (LinkedIn)](https://media.licdn.com/dms/document/media/v2/D4D1FAQFSQgbNvFSO9w/)
