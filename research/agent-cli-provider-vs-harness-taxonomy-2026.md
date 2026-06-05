---
title: "Provider vs Harness Taxonomy Across Agent CLIs (claude / codex / opencode / pi)"
type: research
tags: [agent-cli, provider, harness, model-vendor, transport-matters, claude-code, codex, opencode, pi, taxonomy]
summary: "Across agent CLIs and the LLM ecosystem, 'provider' means the model VENDOR, not the harness; the claude→anthropic / codex→openai 1:1 coupling is an incidental default that opencode, pi, and even Codex already break."
status: active
confidence: high
created: 2026-06-18
updated: 2026-06-18
---

# Provider vs Harness Taxonomy Across Agent CLIs

## Executive Summary

In transport-matters the term `provider` is ambiguous: it could name the agent **CLI/harness** (claude, codex, opencode, pi) or the **model vendor** (anthropic, openai, …). Web verification (June 2026) is decisive: across every major agent CLI and every ecosystem abstraction (Vercel AI SDK, LiteLLM, OpenRouter, LangChain), "provider" universally means the **model vendor/host**, never the tool. The apparent claude→anthropic / codex→openai 1:1 mapping is an incidental *default*, not a structural law — opencode and pi are multi-vendor by design, and Codex itself is already decoupled via a separate `model_provider` axis. The correct model is three axes: **harness × vendor × model-id**.

## Detailed Findings

### How each CLI names {harness, vendor, model-id}

**Claude Code (`claude`)** — The harness's models are effectively fixed to Anthropic.
- `--model sonnet|opus|<full-id>` flag; `"model"` key in `~/.claude/settings.json`.
- Reasoning effort persisted in settings.json (`low|medium|high|xhigh`), written by the `/effort` command.
- No vendor-switch config key. The vendor is always Anthropic; only the *deployment route* is configurable through env vars: `CLAUDE_CODE_USE_BEDROCK`, `CLAUDE_CODE_USE_VERTEX`, plus `ANTHROPIC_DEFAULT_SONNET_MODEL` / `ANTHROPIC_DEFAULT_HAIKU_MODEL` / `ANTHROPIC_DEFAULT_FABLE_MODEL` for the provider-specific model IDs on Bedrock/Vertex/Foundry.
- So: harness = claude, vendor = anthropic (fixed), model-id = `claude-*`. Vendor coupling is real but the *hosting backend* (first-party API vs Bedrock vs Vertex vs Foundry) is decoupled.
- Source: [code.claude.com/docs/en/model-config](https://code.claude.com/docs/en/model-config)

**Codex (`codex`)** — Explicitly DECOUPLED harness/vendor/model.
- `-m/--model` flag; `model` key in `config.toml`; `model_reasoning_effort` (`minimal|low|medium|high`).
- A **separate** `model_provider` key (default `openai`) that references named `[model_providers.<id>]` blocks defining `base_url`, `env_key`, wire API, headers, retries, etc.
- Built-in reserved provider ids: `openai`, `ollama`, `lmstudio`. Custom providers can point at OpenRouter, Azure, DeepSeek, Ollama, or any OpenAI-compatible/Responses-API endpoint (Chat-Completions-only endpoints need a LiteLLM-style translation proxy).
- So Codex already separates vendor (`model_provider`) from model-id (`model`) — the harness↔vendor coupling does **not** hold even for Codex.
- Source: [developers.openai.com/codex/config-reference](https://developers.openai.com/codex/config-reference)

**opencode (sst/opencode)** — MULTI-VENDOR by design (75+ providers via Models.dev).
- Model reference uses the `provider/model-id` form, e.g. `model = "anthropic/claude-sonnet-4-5"`, `small_model = "anthropic/claude-haiku-4-5"`.
- A `provider` block in `opencode.json` configures vendors; supports both native Anthropic format and OpenAI-compatible mode per provider.
- Config layering: remote `.well-known/opencode` → global `~/.config/opencode/opencode.json` → `OPENCODE_CONFIG` → project `opencode.json`.
- Here "provider" explicitly = vendor. One harness, many vendors.
- Sources: [opencode.ai/docs/config](https://opencode.ai/docs/config/), [opencode.ai/docs/providers](https://opencode.ai/docs/providers/)

**pi (earendil-works/pi)** — REAL, shipping CLI. Built by Mario Zechner; ~46k GitHub stars; npm `@mariozechner/pi-coding-agent`.
- Monorepo: `pi-ai` (unified multi-vendor LLM API), `pi-agent-core` (agent loop), `pi-tui`, `pi-coding-agent` (the CLI).
- `pi-ai` supports Anthropic, OpenAI, Google, xAI, Groq, Cerebras, OpenRouter, and any OpenAI-compatible endpoint, with cross-provider context handoffs.
- Custom providers/models added via `~/.pi/agent/models.json` if they speak a supported API (OpenAI / Anthropic / Google). Can auth via API keys or subscriptions (Claude Pro, ChatGPT Plus, GitHub Copilot).
- MULTI-VENDOR. "provider" = vendor.
- Sources: [github.com/earendil-works/pi](https://github.com/earendil-works/pi), [npmjs.com/package/@mariozechner/pi-coding-agent](https://www.npmjs.com/package/@mariozechner/pi-coding-agent)

### What "provider" conventionally means in the ecosystem

Overwhelming convention: **provider = model vendor/host**, not the tool/harness.

- **Vercel AI SDK**: "Providers are the companies or services that host AI models" (xAI, OpenAI, Anthropic). Provider packages follow `@ai-sdk/<vendor>`. Model references use `creator/model-name`; the same model can be served by multiple providers with different pricing/perf. ([vercel.com/docs/ai-gateway/models-and-providers](https://vercel.com/docs/ai-gateway/models-and-providers))
- **LiteLLM / OpenRouter**: model strings use `provider/model`, where the prefix names the vendor/gateway, e.g. `openrouter/anthropic/claude-sonnet-4-...`, `openrouter/openai/gpt-4`. ([docs.litellm.ai/docs/providers/openrouter](https://docs.litellm.ai/docs/providers/openrouter))
- **LangChain**: vendor-named integration packages (`langchain-openai`, `langchain-anthropic`) and `init_chat_model("openai:gpt-4o")` — prefix = vendor.

In none of these does "provider" mean the harness/tool.

### Does harness↔vendor 1:1 truly break?

Yes, decisively:
- **opencode** and **pi** are structurally one-harness-many-vendors.
- **Codex** is already decoupled via `model_provider` (any OpenAI-compatible/Responses endpoint).
- **Claude Code** is the only near-coupled case (models always Anthropic), and even it routes through Bedrock / Vertex / Foundry deployment backends.

The `claude→anthropic` / `codex→openai` mapping is an incidental *default*, not an invariant.

## Sources Consulted

Docs / primary:
- Claude Code model config — https://code.claude.com/docs/en/model-config
- Codex configuration reference — https://developers.openai.com/codex/config-reference
- opencode config — https://opencode.ai/docs/config/
- opencode providers — https://opencode.ai/docs/providers/
- pi repo — https://github.com/earendil-works/pi
- pi npm — https://www.npmjs.com/package/@mariozechner/pi-coding-agent
- Vercel AI SDK models & providers — https://vercel.com/docs/ai-gateway/models-and-providers
- LiteLLM OpenRouter provider — https://docs.litellm.ai/docs/providers/openrouter

Secondary / corroborating: morphllm Codex provider guide, haimaker.ai opencode custom provider setup, Mario Zechner build post (mariozechner.at), DEV Community pi overview.

## Source Quality Assessment

High confidence. Each harness claim is grounded in first-party docs or the project's own repo; the ecosystem-convention claim is corroborated across four independent abstractions (Vercel, LiteLLM, OpenRouter, LangChain) that agree. The one nuance to flag: Claude Code's "vendor coupling" is about *which models* it speaks to (always Anthropic), distinct from *which backend* hosts them (first-party / Bedrock / Vertex / Foundry) — keep those two notions separate when modeling.

## Open Questions

- Does transport-matters need to capture the *deployment backend* axis (Bedrock/Vertex/Foundry/OpenAI-proxy) as a fourth dimension, or fold it into vendor? The wire-observability angle may make backend meaningful (different base URLs / wire formats).
- For Codex with a custom `model_provider`, the observed wire vendor may not be OpenAI — TM's proxy should derive vendor from the actual endpoint, not from the harness name.

## Actionable Takeaways

1. In TM's taxonomy, do **not** let `provider` name the CLI — it collides with the universal ecosystem meaning (vendor). Rename the CLI axis to `harness` (or `agent`/`cli`).
2. Model three axes: **harness** (claude/codex/opencode/pi) × **vendor** (anthropic/openai/google/…) × **model-id**. Optionally a fourth: **deployment backend / base_url** for wire-level fidelity.
3. Treat `claude→anthropic` / `codex→openai` as default seeds, not constraints — the data model must allow one harness to span many vendors (opencode/pi) on day one.
4. Since TM is a wire-observability layer, prefer deriving vendor from the observed upstream endpoint over trusting the launch-time harness label.
