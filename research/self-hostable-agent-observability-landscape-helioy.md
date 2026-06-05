---
title: Self-Hostable Agent Instrumentation and Observability Landscape
date: 2026-07-03
project: helioy
constraint: self-hostable / OSS only; framework-agnostic; no SaaS
method: deep-research workflow (run wf_200ce778-55f) — 100 agents; 25 claims survived 3-vote adversarial verification (0 refuted); every surviving claim primary-sourced. Report synthesized directly from the verified claim set.
---

# Self-Hostable Agent Instrumentation: State of Play, Mid-2026

## Executive summary

The self-hostable agent-observability space has converged on a single load-bearing standard: the **OpenTelemetry GenAI semantic conventions**. As of mid-2026 they define a provider-agnostic vocabulary for agent runs (agent spans, tool-call spans, token-usage histograms), but they sit at **"Development" stability**, and in **v1.42.0 (June 2026) the entire `gen_ai.*` surface was moved out of the core semconv repo into a dedicated, fast-moving repository**. On top of that standard, a small set of OSS platforms are all genuinely self-hostable on a ClickHouse-centric stack: **OpenLIT** (Apache-2.0, OTel-native, built-in LLM-as-judge evals), **Arize Phoenix** (OpenInference, 40+ framework integrations), and **Langfuse** (MIT outside `ee/`). For trajectory-level evaluation, **agentevals** (MIT) is largely framework-agnostic; for gateway-layer token metering, **agentgateway** (Rust proxy) emits Prometheus histograms keyed on OTel conventions. Net read: you can instrument your own agents end to end on OSS today, but you are building against a spec that is explicitly not frozen.

## The through-line: OpenTelemetry GenAI semantic conventions

This is the spine of the whole space. Everything else either implements it or maps onto it.

- **Status is still pre-stable.** All GenAI spans and metrics (inference, embeddings, retrieval, execute-tool, agent) are at **Development** maturity, meaning breaking changes are expected. Instrumentations must opt in via `OTEL_SEMCONV_STABILITY_OPT_IN=gen_ai_latest_experimental` to emit current conventions. *(Confidence: high, primary + multiple 2026 corroborations)*
- **It is actively maintained.** Roughly monthly cadence, latest **v1.42.0 on 2026-06-12/16**. *(high)*
- **The `gen_ai.*` surface was relocated.** As of v1.42.0, all `gen_ai.*` attributes/metrics/events/spans were deprecated in `open-telemetry/semantic-conventions` and moved to the dedicated `open-telemetry/semantic-conventions-genai` repo (565 commits, ~119 open issues), signalling GenAI is now a separate, fast-evolving workstream. *(high)*
- **The core model is provider-agnostic**, keyed on `gen_ai.operation.name` and `gen_ai.provider.name` (both Required), covering inference, embeddings, retrievals, and tool execution. Not locked to any framework. *(high)*

### Layer 1: Tracing and spans

- The conventions define **agent and multi-agent span operations**: `create_agent`, `invoke_agent`, `plan`, and `invoke_workflow` (coordinated multi-agent execution), plus `execute_tool {gen_ai.tool.name}` (the tool-name template became required in v1.41). *(high)*
- The canonical **span hierarchy** for a multi-step run is a top-level `invoke_agent` span with child `chat` spans per LLM call and `execute_tool` spans per tool invocation, all in one trace. This is exactly the shape you want for sub-agent fan-out. *(high)*

### Layer 2: Token and cost metrics

- Standard span attributes: `gen_ai.usage.input_tokens` and `gen_ai.usage.output_tokens` (both Recommended). The input count **SHOULD include cached tokens** (spec says SHOULD, not MUST). *(high)*
- Standard metrics: **`gen_ai.client.token.usage`** (histogram, unit `{token}`, split by `gen_ai.token.type` into `input`/`output`, attributed by operation and provider) and **`gen_ai.client.operation.duration`** (LLM-call latency histogram, filterable by model). *(high)*

### Layer 3: Eval and trajectory quality

- The conventions extend to **agent-step metrics**: `gen_ai.invoke_agent.duration`, `gen_ai.workflow.duration`, and `gen_ai.execute_tool.duration` (keyed by `gen_ai.tool.name`), pushing telemetry beyond single LLM calls into multi-step execution. *(medium-high; this was the one 2-1 vote, adoption still thin)*
- **agentevals** (`langchain-ai/agentevals`, MIT, v0.0.7 Mar 2026) ships readymade **trajectory evaluators** with strict / unordered / subset / superset match modes, a reference-optional LLM-as-judge, graph-trajectory evaluators, and tool-args matching, installable via pip/npm. *(high)*
- It is **largely framework-agnostic**: it accepts standard OpenAI-format message lists, not only LangChain objects. The one carve-out is graph-trajectory evaluators, which are LangGraph-specific. *(high)*
- **OpenLIT** ships **11 built-in LLM-as-judge eval types** (hallucination, bias, toxicity, safety, instruction-following, completeness, conciseness, sensitivity, relevance, coherence, faithfulness) wired into telemetry. Note: the programmatic SDK module exposes 3 (hallucination/bias/toxicity); the full 11 come from the platform dashboard, both in the OSS product. *(high)*

### Layer 4: Prompt and context observability

- **Arize Phoenix** provides **span replay** in a Playground ("replay traced LLM calls") and **versioned prompt management**, with span kinds for LLM calls, retrieval operations, and agent reasoning. This is the strongest run-inspection/replay story in the verified set. *(high)*
- The OTel GenAI spans themselves carry input/output message content (`gen_ai.input.messages` / `gen_ai.output.messages`, revamped in v1.38.0), which is the standardized substrate for "what actually entered the context window." *(high, via the breaking-change evidence in claim 8)*

## The self-hostable project matrix

| Project | License | Framework-agnostic? | Self-host stack | Layer strength |
|---|---|---|---|---|
| **OTel GenAI semconv** | Apache-2.0 (spec) | Yes (the standard) | N/A (wire format) | Defines all four layers |
| **OpenLIT** | Apache-2.0 | Yes (OTel-native; Py/TS/Go SDKs) | `docker compose up -d` → OTLP collector → ClickHouse | Tracing + token/cost + 11 evals |
| **Arize Phoenix** | Elastic/OSS, "zero feature gates" self-host | Yes (OpenInference, 40+ integrations, Py + TS) | pip / Docker `arizephoenix/phoenix` / K8s Helm | Prompt+context replay, tracing |
| **Langfuse** | MIT (except `ee/`) | Yes (OTel ingest) | Docker Compose / K8s Helm / Terraform AWS-Azure-GCP; ClickHouse analytics backend | Tracing + cost + prompt mgmt |
| **agentevals** | MIT | Largely (OpenAI-format messages); graph evals are LangGraph-only | pip / npm library | Eval + trajectory |
| **agentgateway** | OSS (Rust proxy) | Yes (proxy layer, framework-blind) | Self-hosted data-plane proxy; Prometheus scrape | Token/cost metering at the gateway |

The pattern worth noting: **ClickHouse via an OTLP collector is the de-facto self-host backend** (OpenLIT, Langfuse, and effectively Phoenix all land there), and **every surviving claim was primary-sourced**, which is a strong signal the verified set is real and not blog-echo.

## Caveats

- **The standard is not frozen.** GenAI spans and metrics are Development-stability; concrete breaking changes already landed (v1.38.0 removed `gen_ai.prompt`/`gen_ai.completion`, reworked chat-history attributes). Anything you build now needs the experimental opt-in and will need maintenance.
- **Coverage limit of this pass.** The funnel kept the top 25 claims by importance and source quality, and it centered on the OTel standard plus five flagship platforms. Named candidates from the brief that did **not** surface an independently verified claim in this run: OpenLLMetry/Traceloop's SDK (appeared only as corroborating evidence), SigNoz, and the Jaeger/Grafana Tempo backends. Their absence is a sampling artifact, not evidence they lack merit.
- **agentgateway tracks a slightly older OTel revision** (`gen_ai.system` rather than the newer `gen_ai.provider.name`), a minor lag to watch.

## Open questions

1. Where does **OpenLLMetry/Traceloop** (an OSS SDK explicitly named in the brief) sit today relative to OpenLIT, given both claim OTel-native GenAI emission? Worth a targeted follow-up.
2. Which **OSS trace backend** (SigNoz vs Grafana Tempo vs ClickHouse-direct vs Jaeger) is the best fit once you commit to OTel GenAI spans at scale?
3. How mature is **cross-process trace propagation** for genuinely distributed multi-agent systems (separate processes/hosts), as opposed to single-process span trees?
4. What is the concrete migration cost of building on Development-stability conventions now versus waiting for a Stable freeze?

## Sources (all primary, verified)

- OTel GenAI spans spec · `opentelemetry.io/docs/specs/semconv/gen-ai/gen-ai-spans/`
- OTel GenAI metrics spec · `opentelemetry.io/docs/specs/semconv/gen-ai/gen-ai-metrics/`
- OTel GenAI observability blog (2026) · `opentelemetry.io/blog/2026/genai-observability/`
- OTel semantic-conventions releases · `github.com/open-telemetry/semantic-conventions/releases`
- OpenLIT · `github.com/openlit/openlit`
- agentgateway cost tracking · `agentgateway.dev/docs/kubernetes/main/llm/cost-tracking/`
- agentevals · `github.com/langchain-ai/agentevals`
- Arize Phoenix · `github.com/arize-ai/phoenix`
- Langfuse · `github.com/langfuse/langfuse`

---

## Fit for Helioy (the reason you're instrumenting)

Mapping the verified findings onto the two real substrates:

- **One wire format across both.** The OTel GenAI semconv is the convergence point. The Nancy Go + k3s path already gets "free observability" (Prometheus, OTel traces); emitting `gen_ai.*` spans and the token-usage histogram from the agent layer means the Claude Code fleet and Nancy land in **one OTel pipeline** instead of two vocabularies. Adopt it as the contract, but emit behind the experimental opt-in and budget for churn.
- **The fleet has no native OTel GenAI emission.** Claude Code agents do not emit these spans on their own. The capture point is a **proxy or hook layer**, which is exactly what the existing `claude-code-logger` HTTP proxy already does for API traffic. agentgateway is the productionized version of that idea: framework-blind token/cost metering at the gateway, and it is a Rust k8s data-plane proxy, which aligns cleanly with the K8s-shaped v2 endgame.
- **Token economy maps directly.** The token-economy lessons (per-agent, per-session accounting, cache-hit awareness) are precisely `gen_ai.usage.input_tokens`/`output_tokens` with cached-token inclusion plus the `gen_ai.client.token.usage` histogram. This is standardized, not something to invent.
- **Eval layer:** agentevals is the framework-agnostic pick for trajectory scoring (it eats OpenAI-format messages), and it slots next to the warroom/coordinator flows without a framework lock-in.
- **Backend:** ClickHouse via OTLP collector is the OSS gravity well. cm/SQLite stays the knowledge substrate; ClickHouse would be the telemetry substrate.
