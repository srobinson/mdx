---
title: Databricks AI coding cost reduction stack (Unity AI Gateway, Omnigent, task routing)
type: research
tags: [databricks, unity-ai-gateway, omnigent, cost-control, routing, meta-harness, context-compaction, helioy, gtm]
summary: Databricks cut internal coding-agent unit costs via four layered levers; the stack is Unity AI Gateway (closed, managed) plus Omnigent (Apache-2.0 meta-harness, Databricks-seeded), and Omnigent's cost-policy and compaction code is directly liftable into Helioy.
status: active
source: github-researcher
confidence: high
created: 2026-08-08
updated: 2026-08-08
---

# Databricks AI Coding Cost Reduction Stack

## Executive Summary

Databricks published "Managing AI Coding Costs at Scale" (Patrick Wendell et al., 2026-08-07) describing four layered levers that cut internal coding-agent unit cost. The stack has two halves: **Unity AI Gateway**, a closed managed control plane that went GA on 2026-08-04 and meters every coding agent at the company, and **Omnigent**, an Apache-2.0 Python meta-harness (github.com/omnigent-ai/omnigent, 8.4k stars) that Databricks people seeded and that Databricks itself uses as its internal client-side layer.

The strategically important finding: **Omnigent is the open-source half of the exact product category Helioy occupies**, it is three months old, and its cost-policy engine and context-compaction cascade are readable, well-tested, production-grade implementations of the mechanisms the blog describes. Helioy should lift the mechanisms and avoid competing on the meta-harness surface.

---

## Verdict for Helioy: adopt / borrow / skip

**Adopt (three mechanisms, high value, low effort):**

1. **The progressive-friction cost ladder as a policy plugin.** Omnigent's `policies/builtins/cost.py` implements ASK/DENY gates on two phases only, with USD checkpoints and monotonic approval state. This is the single most liftable artifact in the whole stack. Helioy has warroom agents burning tokens with no gate at all.
2. **Forced downgrade instead of hard stop.** Over budget on an expensive model returns DENY with an instruction to switch models; over budget on a cheap model returns ALLOW. The budget gates *model tier*, not access. This is the correct primitive for a multi-agent fleet.
3. **The three-layer compaction cascade ordered least-lossy-first.** Clear tool results to a fixed marker, then LLM-summarize the prefix, then front-truncate with pair-aware atomic drops. The ordering is the insight.

**Borrow (adapt the shape, not the code):**

4. **Task-level routing with a menu-driven judge.** Omnigent's judge prompt maps SIMPLE/MODERATE/COMPLEX to cheapest/middle/most-capable position in a cost-sorted menu. Position-based rather than model-name-based, so the menu changes without touching the prompt.
5. **The `routes:select` wire contract.** A clean external-router seam Helioy could implement on either side.

**Skip:**

6. **Building a Unity AI Gateway equivalent.** It is a metering and governance control plane tied to Unity Catalog system tables. Not Helioy's problem.
7. **Competing with Omnigent as a meta-harness.** It has 13 harnesses, 701 source files, 1397 test files, a desktop app, and Databricks-adjacent maintainers. Helioy's differentiation is warroom orchestration topology, not harness abstraction.

---

## The published source set

| Source | Date | What it carries |
|---|---|---|
| [Managing AI Coding Costs at Scale](https://www.databricks.com/blog/managing-ai-coding-costs-scale) | 2026-08-07 | The four levers. Wendell, Bhatia, Gaba, Elsen, Zhou |
| [Unity AI Gateway is Generally Available](https://www.databricks.com/blog/unity-ai-gateway-generally-available) | 2026-08-04 | GA, feature set, customer list |
| [How Databricks manages its own coding agent spend with Unity AI Gateway Budgets](https://www.databricks.com/blog/how-databricks-manages-its-own-coding-agent-spend-unity-ai-gateway-budgets) | ~2026-08 | The daily/monthly budget design. Highest-value doc for Helioy |
| [Introducing AI spend controls with Unity AI Gateway](https://www.databricks.com/blog/introducing-ai-spend-controls-unity-ai-gateway) | ~2026-06 | Budget primitives, system tables |
| [Benchmarking Coding Agents on Databricks' Multi-Million Line Codebase](https://www.databricks.com/blog/benchmarking-coding-agents-databricks-multi-million-line-codebase) | ~2026-07 | The benchmark that justified the GLM default |
| [Axios: Databricks rolls out AI spend controls](https://www.axios.com/2026/06/16/databricks-stop-ai-overspend-tokenmaxxing) | 2026-06-16 | "tokenmaxxing" framing |

### Number provenance, stated honestly

The blog body substantiates exactly two figures. The per-lever breakdown (50/30/10/10) and the "up to 90%" headline come from Wendell's post, and from a savings table rendered as an image in the blog that I could not extract.

**Verbatim from the blog:**

> "Internal results at Databricks suggest that our AI Gateway Smart Router is able to consistently reduce average task cost by more than 30%, while roughly matching the quality of the most expensive model in the working set."

> "At Databricks, relatively simple tuning of our harness and caching settings led to an almost 50% reduction in the number of generated tokens and associated costs, with no observed quality degradation for developers."

Note the tension: the blog attributes ~50% to *token overhead tuning*, while the post attributes ~50% to *model shifting* and only ~10% to context management. Compounding 50/30/10/10 multiplicatively yields ~72% reduction, not 90%. Compounding the blog's own figures (0.5 model shift × 0.7 routing × 0.9 budgets × 0.5 token tuning) yields ~84%. Treat the four percentages as **share-of-savings attribution, directional only**. Do not quote 90% as a compounded fact.

**Benchmark figures (high confidence, stated in prose):**

- GLM 5.2: **$1.28/task**, statistically tied with Opus 4.8 on quality.
- Opus 4.8: **$1.94/task**, 87% task completion.
- Sonnet 5: **$2.09/task**, 81% completion, despite being ~1.7x cheaper per token than Opus. It consumed **1.9x more tokens per task**.
- Same model and thinking effort through different harnesses produced **more than 2x** cost difference at equal quality.
- The Pi harness sent **about 3x less context per turn** than Claude Code or Codex.

That Sonnet result is the load-bearing finding of the entire stack: **token price is a bad proxy for task cost**, so cost control has to be measured at task granularity, not token granularity.

---

## Unity AI Gateway

### What it is

The runtime governance and metering control plane for all AI traffic at Databricks. GA 2026-08-04. Built on Unity Catalog: models, MCP servers, tools, connections, and coding agents are all Unity Catalog *securables*, so existing identity, permissions, lineage, and audit apply to runtime AI calls.

Its own claim: over a quadrillion tokens passed through it in the past year. Named production customers include Rivian (>100B tokens/month), Zepto, STRABAG SE, Magnite, Edmunds, OnePay.

### Lineage

MLflow AI Gateway (open source, `mlflow/mlflow`) is the ancestor and remains the self-hostable option. Mosaic AI Gateway was the prior managed branding. Unity AI Gateway is the current managed product and is **not open source**. Billed in DBUs for gateway features (routing, logging, inference-table writes, permission checks); provider token fees pass through directly.

### Architecture

```
client (coding agent / app)
  → Unity AI Gateway control plane
      · Unity Catalog securable resolution + permissions
      · service policies (guardrails: PII detection/masking, content rules)
      · rate limits
      · traffic splitting + fallbacks
      · budget check (approximate, near-real-time cost estimate)
      · Smart Routing (beta)
  → Foundation Model APIs (native) | external providers | MCP services
  → usage lands in Unity Catalog system tables (system.billing.usage)
```

Doc surface: `docs.databricks.com/aws/en/ai-gateway/` with sections for model APIs, external providers, MCP tools, custom tools, HTTP connections, rate limits, traffic splitting and fallbacks, budgets, service policies, and observability (monitor usage / analyze cost / audit requests).

### Budgets: the design worth stealing

The internal design is a **two-tier coupled budget**, and the coupling is the clever part.

**Daily budget** is runaway protection. Small, auto-resets each evening at lowest-usage hours. Tripping it opens a **self-service acknowledgment**, not an approval: one click in Slack, the portal, or the CLI, and the limit increments immediately. There is **no cap on self-acknowledgements per day**. The system also proactively promotes a user one tier when spend approaches the ceiling, at most once daily, and resets everyone to base tier monthly.

**Monthly budget** is waste prevention. Higher threshold, **manager approval required**, coarse tiers (2x, 5x, effectively unlimited), and promotions are time-limited and revert when the project ends.

**The coupling:** the two are held at a fixed ratio so that "an engineer spending smoothly across the month will never trip the daily limit at all, because the monthly budget divided across working days sits comfortably under the daily threshold." When the monthly limit rises, the daily increment scales proportionally, preserving runaway protection at every tier.

**Effective cap formula:** `min(current_monthly_usage + one_runaway_increment, monthly_maximum)`.

**Enforcement:** 90% threshold fires a Slack warning; the hard limit blocks requests at the gateway. Binary blocking, no throttling. Tiers are implemented as **group membership** in the gateway, deliberately, so "a group listing answers who is above the default and by how much."

**Reported outcome:** monthly interrupt-driven budget tickets fell from hundreds to a small handful, and engineers "stopped rationing" AI usage.

**Product-level budget primitives** (from the spend-controls post and docs): per-user, per-use-case (via resource tags), per-workspace, and org-wide caps, configured under Usage > Budgets. Actions are Send Alert or Block Usage. Limits: max 4 shared thresholds and 20 per-user overrides per budget, 1000 budgets per account. Enforcement is explicitly **approximate** (near-real-time estimates, users may block slightly early, in-flight requests are not interrupted). Currently tracks pay-per-token and `ai_query` batch inference; **not** provisioned throughput or external-model inference.

### Smart Routing (beta)

A stateless proxy in front of the foundation models that routes each request to the lowest-cost model capable of answering it, on signals of quality, cost, performance, availability, and budget. This is the >30% figure. Named peer implementations in the blog: Cursor Router, OpenRouter AutoRouter, Ramp's Router. Related escalation patterns named: Claude's Advisor Tool, Cognition's Devin Fusion.

The external router API is real and reachable, and Omnigent speaks it (contract below).

---

## Omnigent: the open-source half

`github.com/omnigent-ai/omnigent`, Apache-2.0, Python, 8354 stars, 1254 forks, org created 2026-06-09, repo 2026-06-11, actively pushed. 701 source files, **1397 test files**. Self-described status: alpha.

**Provenance matters here.** Top committers include `zeyi.f@databricks.com`, plus `dbczumar` (Corey Zumar), `Tomu Hirata`, `Serena Ruan`, and `Yuan Tang`, all MLflow core maintainers at or around Databricks. Internal Databricks tool names leak into the code (`isaac configure codex`, `ucode`). Read this as a Databricks-incubated OSS project positioned as the neutral client-side complement to the closed gateway. The playbook is MLflow's, repeated.

### Harness abstraction

A harness is the swappable runtime that executes the agent loop. Tools, policies, prompts, and models stay constant across harnesses; only the runtime changes. Two modes: **Direct** (Omnigent owns model and tools) and **Native TUI** (boots the vendor's own TUI in a pane and mirrors it back, ids suffixed `-native`).

Supported: `claude-sdk`/`claude-native`, `codex`/`codex-native`, `cursor`, `goose`, `qwen`, `kimi`, `hermes`, `pi`, `opencode-native`, `kiro-native`, `copilot`, `openai-agents`, `grok`. Plus a generic `acp` harness driving any Agent Client Protocol agent, and a Python entry-point plugin group `omnigent.community.harness`.

Binary resolution precedence: `OMNIGENT_<NAME>_PATH` env var, then `harness.<id>.command` in config, then built-in default.

### Cost policy: the mechanism (`omnigent/policies/builtins/cost.py`, 1000 lines)

Three factory policies, registered in a `POLICY_REGISTRY` scanned at startup:

| Handler | Budget scope |
|---|---|
| `cost.cost_budget` | this session's whole spawn tree |
| `cost.user_daily_cost_budget` | owner's spend across all sessions, current UTC day |
| `cost.subagent_cost_budget` | one child conversation's own subtree |

Config shape:

```yaml
policies:
  cost_budget:
    type: function
    function:
      path: omnigent.policies.builtins.cost.cost_budget
      arguments:
        max_cost_usd: 5.0
        ask_thresholds_usd: [1.0, 2.5]
        expensive_models: ["opus", "gpt-5"]
```

**Only two phases are gated:**

```python
_GATED_PHASES = frozenset({"request", "tool_call"})
```

`request` catches text-only turns before the LLM call; `tool_call` is the native `PreToolUse` block point. Everything else returns ALLOW. This is a deliberately small surface.

**The friction ladder, in branch order:**

1. **Unpriced fail-closed ASK.** If usage carries token counts but no `total_cost_usd`, the budget is unmeasurable, so it asks once and records approval. First turn on an unpriced model always runs (only post-turn data exists at check time).
2. **Hard cap DENY as a forced downgrade.** At or over `max_cost_usd`, DENY only if the current model matches an `expensive_models` substring. Already on a cheap model returns ALLOW. Omitting `expensive_models` sets `block_all_models=True`, a true stop.
3. **Soft checkpoint ASK.** `crossed = max(t for t in thresholds if cost >= t)`, fires once per checkpoint via monotonic `approved_up_to` state. Approving silences that checkpoint and all lower ones; higher ones still fire.

**The DENY message is phase-aware and harness-aware**, which is a detail worth copying. On `request` it addresses the user directly. On `tool_call` it addresses the *model*, because native harnesses hand the reason to the LLM:

> "Relay this to the user verbatim, then stop and wait for them, do not silently re-run the tool right now: [...] This block is NOT permanent: once the user switches to a cheaper model and asks you to continue, actually re-issue the tool call (it will be allowed), do not just repeat this message."

And it adapts the hint per harness: codex gets "in the terminal, run /model and pick a cheaper model to continue."

**Crucially, no code mutates the model as a consequence of budget state.** `PolicyResponse` carries only `result`, `reason`, `state_updates`. The downgrade is achieved *socially*, by denying and instructing. Model is an input, never an output. This keeps the policy engine free of routing concerns.

**Attribution:** `PolicyEngine.record_usage` prices deltas and accumulates into the conversation's `session_usage`; gating reads the **spawn-tree total**, not the local one. Per-user daily rollup lives in table `user_daily_cost` keyed `(workspace_id, user_id, day_utc)` with columns `cost_usd` and `ask_approved_usd`, incremented UPSERT-style so policy reads are O(1). Sub-agent spend with no direct owner falls back to the **root session's owner** rather than being dropped.

**Approval UX:** one shared elicitation across surfaces. Native terminal sessions get a `tmux display-popup -w 80% -h 50%` prompt (`native_cost_popup.py`), the web gets an `ApprovalCard`, and both POST to `/v1/sessions/{id}/elicitations/{eid}/resolve`; whichever answers first wins, and a watcher polls every 1.5s to tear down the popup. Bearer token is passed via `--config-file`, never argv. Default wait budget is 86400s. Concurrent native tool calls hitting the same ASK are serialized by a lock so the human is prompted once and siblings collapse to ALLOW.

CLI reporting: `omnigent usage` shows Today / Last 7 days / Last 30 days / All time plus per-session breakdown, prefaced with "Costs are best-effort estimates."

### Context compaction: the mechanism (`omnigent/runtime/compaction.py`, 945 lines)

**Budget formula:**

```python
budget = int(context_window * trigger_threshold) - system_token_budget
```

with `_DEFAULT_TRIGGER_THRESHOLD = 0.8` and `_DEFAULT_RECENT_WINDOW = 5`. Tool schemas live inside the system string and so are charged against the budget. Token counting is tiktoken over `json.dumps(messages)`, deliberately approximate; the 20% headroom absorbs the error.

**The protected tail is measured in LLM response groups, not messages and not tokens.** Walk backwards counting assistant messages and function calls until `recent_window` groups are seen.

**Three layers, least-lossy first:**

**Layer 1, surgical, no LLM call.** Tool results before the boundary have their entire `output` replaced with a fixed marker:

```python
_TOOL_RESULT_CLEARED = "[Previous tool result cleared — re-call tool if needed]"
```

No byte cap, no token cap, no head/tail retention, no size heuristic. A 3-byte result and a 3MB result are treated identically. Recovery is by re-calling the tool. The `function_call` item itself is untouched so no orphan pairing is created. Binary blocks lose `data` but keep `file_id` for re-fetch, and a regex sweep catches base64 smuggled inline as data URIs. Output annotations are deleted as client-facing metadata the summarizer should not pay for.

**Layer 2, LLM summarization** of everything before the boundary, re-injected as a **synthetic user + assistant pair** rather than a system note, so the model knows it produced the summary and turn-taking attribution stays clean. Progressive summarization is detected by sniffing for `"[This is an automatically generated summary"` in the first block, and the prompt then instructs the summarizer to incorporate rather than discard it, so summaries compound. The summarizer prompt is explicit about what survives:

> "Include: the user's goals, key decisions and why they were made, tool results that matter going forward (paths, values, errors), and any outstanding commitments or next steps. Exclude: verbose tool output, redundant exchanges, and intermediate reasoning that led to a final decision, keep the decision, not the path."

**Layer 3, front truncation**, emergency only, always logs a warning. Drops from the front, and recognises a leading run of parallel `function_call` items followed by their matching outputs, dropping the whole batch atomically by `call_id` set equality.

**Context window resolution order:** `AP_CONTEXT_WINDOW_OVERRIDE` env var, then a window encoded in the model id (`[1m]` suffix on Claude ids yields 1,000,000), then the MLflow catalog (only if all matching entries agree), then litellm `max_input_tokens`, then 128,000 default. A spec-declared window beats the catalog, but an active per-session `model_override` discards it, because "overriding a 1M-window agent down to a small-window model would budget compaction against 1M and under-compact past the real model's limit."

**Cache handling, stated plainly: there is none.** No `cache_control` breakpoint placement, no prefix-stability logic, no deferring compaction to preserve a cache prefix. Both Layer 1 and Layer 2 mutate the prompt prefix and therefore invalidate any provider prefix cache for the whole conversation. Cache appears only in *pricing*:

```python
_FALLBACK_CACHE_READ_INPUT_RATIO: float = 0.10
_FALLBACK_CACHE_WRITE_INPUT_RATIO: float = 1.25
```

with a load-bearing warning that OpenAI's `prompt_tokens` includes cached tokens, so callers must subtract `cached_tokens` before passing `input_tokens` or they double-bill cache reads at full rate.

**This is the gap.** Databricks' blog attributes its ~50% token reduction to "harness and caching settings" tuning, but the OSS meta-harness has no cache-aware compaction at all. Cache-preserving compaction is unbuilt territory.

### Upstream context policies (`omnigent/policies/builtins/context.py`)

Separate from the compactor, no import in either direction. Stated philosophy:

> "the goal is not fewer tokens *used*, but fewer tokens *wasted*, sprawling context filled with stale tool results from a prior task degrades quality without adding value. The recommended response to a denial is to start a fresh session for the new task rather than compacting or summarising in place."

Two policies, both fail-open:

- **`detect_task_switch`** on `request` events. Keeps a sliding window of user messages truncated to 500 chars, calls a structured-output classifier returning `CONTINUATION | TASK_SWITCH`, defaults to ASK. The prompt is deliberately asymmetric: "When in doubt, prefer CONTINUATION, false positives are more harmful than false negatives." Carries an explicit non-security disclaimer, since user text is interpolated into the classifier prompt.
- **`detect_thrashing`** on `tool_result` events. No LLM. Tracks a 1/0 error history via prefix matching (`error:`, `traceback (most recent call last)`, `permission denied`, `enoent:`, ...) over the first 500 chars. Two triggers: 5 consecutive errors, or an 80% error rate over a window of 10. Deliberately over-inclusive on error detection. The window is **not** reset on detection, so it keeps firing until the agent recovers naturally.

### Smart routing (`omnigent/server/smart_routing.py`, 2440 lines)

Two providers: a **built-in LLM judge** using the server's own `llm:` block, or an **external `routes:select` service** (the Databricks gateway router).

**The judge prompt is the borrowable artifact.** It maps complexity to *menu position*, never to a model name:

```
  SIMPLE   → fast: first available model
  MODERATE → balanced: middle available model
  COMPLEX  → powerful: last available model
```

with the menu sorted economy-first by `cost_tier`, and a forced rationale pattern: `"This is a [SIMPLE/MODERATE/COMPLEX] task ([brief reason]); selected [cheapest/mid-range/most capable] model [model-id]."` Verdict is strict JSON against a closed schema. Judge timeout is a hard `ROUTING_REQUEST_TIMEOUT_S = 9.0`, deliberately decoupled from the server `llm:` block's 300s, with the reasoning stated inline: "A judge that slow is not a verdict anybody is still waiting for."

The harness descriptions in the prompt encode real routing intent worth copying:

```
- claude-sdk / claude-native: best for multi-file refactors, test writing, and deep reasoning chains.
- codex / codex-native: best for narrow, well-scoped code changes.
- pi: Multi-model headless harness; best for read-only exploration, review, and cross-vendor verification.
```

**External router config:**

```yaml
routing:
  provider: external
  base_url: https://gateway.example.com/ai-gateway/routing/v1
  router_name: task_v1
  model_prefix: databricks-
  api_key: ${ROUTING_API_KEY}
```

**Wire contract** (`POST {base_url}/routes:select`):

```json
{
  "route_options": [
    { "model": "claude-opus-4-8", "harness": "claude-sdk" },
    { "model": "gpt-5-5", "harness": "codex" },
    { "model": "gpt-5-4-mini", "harness": "pi" }
  ],
  "task": { "prompt": "Refactor the auth module and add tests" },
  "route_selector": { "router_name": "task_v1" }
}
```

Response carries `route_selection` plus a `rationale`. Prompt is truncated to 4000 chars. Prior turns are sent for consistency. `model_prefix` is stripped on the way out and restored on the answer.

Operational hardening worth noting: OAuth bearers are minted **per call** from a Databricks CLI profile so a long-lived server never sends a token stale past the ~1h expiry; a `permanently_unavailable` latch means a workspace without the routing API pays one request, not one per turn; failure returns `None` so the turn proceeds on the agent's default model rather than erroring.

Gateway host validation (`omnigent/databricks_ai_gateway.py`) matches **whole DNS labels** from the right, never string suffixes, explicitly so that neither `evilcloud.databricks.com` nor `....cloud.databricks.com.evil.test` can receive a forwarded token. Canonical form is `<workspace>.ai-gateway.cloud.databricks.com`.

---

## The four techniques, as implementable specs

### 1. Shift defaults to efficient models (~50% share)

**Mechanism:** run a task-level benchmark on your own codebase, then move the default. Databricks built theirs from internal PR history: recent, human-written, strong test suites, self-contained, spread across languages. Tests were held out, intent was rewritten as a prompt with the solution removed, **git history was sealed during runs** so agents could not recover the original, and grading was actual test execution with no LLM judge.

**For Helioy:** the cheap version is a fixed suite of ~20 real tasks from the transport-matters / context-matters history, run per candidate model, graded by `just test`. The expensive part is task curation, not harness plumbing. The Sonnet-vs-Opus result means you **must** measure cost per completed task, never cost per token.

### 2. Task-level routing (~30% share, >30% measured)

**Mechanism:** a client-side classifier picks (harness, model) from a cost-sorted menu before the task starts, distinct from request-level proxy routing which picks per inference call.

**For Helioy:** implement as position-based selection over a cost-sorted menu with a 9s hard timeout and fail-open to default. The natural insertion point is warroom spawn: the coordinator already decides which agent handles which slice, so attach a model tier to that decision. Route reviews and scouts to cheap models, route multi-file refactors to expensive ones. Omnigent's harness descriptions are a usable starting rubric.

### 3. Visibility and adaptive budgeting (~10% share)

**Mechanism:** the two-tier coupled budget above. Daily is self-clearing acknowledgement, monthly is manager approval, the ratio guarantees smooth spenders never see the daily gate.

**For Helioy:** the ladder maps cleanly onto warroom agents. Per-agent session budget with USD checkpoints producing ASK, plus a per-orchestrator daily rollup. The key design choices to copy: gate only two phases, make the checkpoint state monotonic so each threshold fires once, make DENY a forced downgrade rather than a stop, and write the DENY reason **for the model** when it fires on a tool call. Group-membership tiers instead of per-user numbers is the right call for legibility.

### 4. Context bloat management (~10% share, ~50% token reduction measured)

**Mechanism:** the three-layer cascade, plus upstream policies that push toward a fresh session rather than compaction, plus harness and cache setting tuning.

**For Helioy:** Layer 1 alone is high value and cheap. Replacing out-of-window tool results with a fixed marker requires no LLM call and no size heuristics. The `detect_thrashing` policy (5 consecutive errors or 80% over 10) is a genuinely useful warroom circuit breaker that Helioy does not currently have, and it needs no model call.

The blog's ~50% figure came from "harness and caching settings," but the OSS code has zero cache management. Cache-preserving compaction is the open problem: every compaction pass currently invalidates the whole prefix cache, and nothing weighs that cost against the compaction benefit.

---

## Selling to Databricks

**Their vocabulary, use it verbatim:** efficiency frontier (distinct from intelligence frontier, and "advancing far faster"), meta-harness, task-level routing vs request-level routing, progressive friction, spend gates, downshifting, tokenmaxxing (Axios framing), route options / route selector, service policies, securables, cost attribution.

**Their stated position:** hard budgets are a last resort. "Broad, low-friction access plus a predictable cost envelope per developer" is the dual mandate. Any pitch that reads as rationing loses.

**Gaps in their stack:**

1. **No cache-aware compaction.** They claim ~50% savings from cache tuning but shipped no cache-preservation logic in the OSS half. A compaction scheduler that weighs prefix-cache invalidation cost against context savings is unbuilt and directly on their stated critical path.
2. **Budget enforcement does not reach the meta-harness.** Gateway budgets block at the proxy; Omnigent's cost policies live client-side and read `session_usage`. There is no single reconciled ledger. Omnigent reserves a `cost_control.*` label namespace for exactly this and **the consumer does not exist in the repo**. That is a named, empty seam.
3. **Multi-agent topology is absent.** Everything is per-session or per-spawn-tree. Nothing models a fleet of coordinated agents across repos, nothing does dependency sequencing, nothing handles a shared working tree. Helioy's warroom is exactly this layer and it is above where Omnigent stops.
4. **No cost attribution to work items.** Spend attributes to user, session, workspace, and tag. Nothing attributes to an issue or a PR. Helioy's Linear integration makes cost-per-issue natural.
5. **Budget tracking excludes provisioned throughput and external-model inference**, per their own docs. A blind spot they have documented.
6. **Enforcement is approximate and post-hoc.** Near-real-time estimates, in-flight requests uninterrupted. No pre-flight cost prediction.

**Where a third-party product fits:** above the meta-harness, below the gateway. The orchestration layer that decides *how many agents, on what, in what order, at what tier* is the layer that determines cost before a single token is spent. Omnigent routes one task; Unity AI Gateway meters one request. Neither plans a fleet.

**Entry point:** Omnigent is Apache-2.0 with an entry-point plugin system (`omnigent.community.harness`) and an external routing seam. A Helioy contribution that fills the `cost_control.*` advisor gap, or a Helioy warroom that runs Omnigent harnesses, is a credible technical foot in the door with people who are named committers.

---

## Sources Consulted

- Databricks blogs listed in the source table above
- `docs.databricks.com/aws/en/ai-gateway/` index, `/budgets`, `/cost-observability`
- `omnigent.ai/docs/build/harnesses`, `omnigent.ai/docs/build/routing`
- github.com/omnigent-ai/omnigent at HEAD 2026-08-08, files read in full: `omnigent/policies/builtins/cost.py`, `omnigent/policies/builtins/context.py`, `omnigent/runtime/compaction.py`, `omnigent/llms/context_window.py`, `omnigent/server/routes/usage.py`, `omnigent/native_cost_popup.py`, `omnigent/cost_plan.py`, `omnigent/databricks_ai_gateway.py`; partial: `omnigent/server/smart_routing.py`, `omnigent/runner/subagent_routing.py`, `AGENTS.md`, `README.md`
- Supporting: `omnigent/runtime/policies/engine.py`, `builder.py`, `omnigent/db/db_models.py`, `omnigent/llms/summarize.py`

## Open Questions

- The savings table is an image in the blog. The exact per-lever percentages remain unconfirmed from a primary text source.
- Unity AI Gateway's Smart Routing beta is not publicly documented beyond marketing. The `routes:select` contract is known only through Omnigent's client. Router internals (what model does the selection, what features it uses) are undisclosed.
- Whether Omnigent is formally a Databricks project or an independent org with Databricks employees contributing. The org has no company field set and only 4 public repos.
- Whether the `cost_control.plan` advisor exists internally at Databricks and is simply unreleased.
- No public paper or model card for the `task_v1` router.

## Documentation drift found in Omnigent (verified, worth reporting upstream)

- `docs/POLICIES.md:254,274` says `expensive_models: []` disables the hard limit. The code does the opposite: empty or `None` sets `block_all_models=True`, a full stop for every model. The stale default set survives in `cost.py:361-363` and the registry description at `cost.py:991-993`.
- `context.py` factory defaults are `min_turns=1`, `history_window=10`, but the registry `params_schema` declares `2` and `4`, and the `history_window` description text still says "Defaults to 10" next to its own `"default": 4`.
- `compaction.py`'s header docstring describes an automatic proactive/reactive compaction loop that no longer exists. The only caller is the explicit `/compact` control event; automatic compaction is now delegated to the native harnesses.
