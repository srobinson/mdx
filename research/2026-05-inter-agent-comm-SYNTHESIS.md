---
title: Inter-agent communication landscape — May 2026 synthesis
date: 2026-05-20
scope: helioy
status: snapshot (decays in ~6 months)
related:
  - 2026-05-inter-agent-comm-novel.md
  - 2026-05-inter-agent-comm-durable.md
  - 2026-05-inter-agent-comm-k8s.md
---

# Inter-agent communication — May 2026 synthesis

Integrating doc over three deep-research layer reports. Each layer report is dense and source-linked; this file is the unified picture, the Helioy fit, and the recommended path forward.

## The three-layer map

```
┌───────────────────────────────────────────────────────────────┐
│  L3 — PROTOCOL / SEMANTIC LAYER (what agents say to each      │
│       other, how they discover & negotiate)                   │
│   MCP · A2A v1.2 · ACP · AG-UI · AP2/x402                     │
│   Linux Foundation governance · 150+ orgs in production       │
│   Frontier R&D: latent-space comms, blackboards, auctions,    │
│       Erlang-actor revival (Turn lang), DID-based identity    │
├───────────────────────────────────────────────────────────────┤
│  L2 — DURABILITY / TRANSPORT LAYER (how messages survive,     │
│       retry, replay, idempotently)                            │
│   Durable execution:  Temporal (Tier S) · Restate · DBOS ·    │
│       Hatchet · Cloudflare Workflows                          │
│   Transport:          NATS JetStream · Kafka · Redis Streams  │
│       Postgres outbox · SQLite WAL (single-machine)           │
│   Observability:      OTel GenAI semconv (ratified Q1 2026)   │
├───────────────────────────────────────────────────────────────┤
│  L1 — RUNTIME / DEPLOYMENT LAYER (where it physically runs)   │
│   K8s-native:   Dapr Agents v1.0 · Kagenti CRDs · Agent       │
│       Gateway (kgateway) · KEDA · Istio Ambient + SPIFFE      │
│   K8s-minus:   Cloudflare Workflows + Durable Objects ·       │
│       Modal · Temporal Cloud                                  │
│   Single-machine:  tmux + SQLite + JetStream-lite             │
└───────────────────────────────────────────────────────────────┘
```

## L3 — the protocol layer has consolidated

The most important boring fact from the 2025-2026 window: **the protocol war ended.** MCP (tools), A2A (delegation), ACP (envelopes), AG-UI (UI streaming), AP2/x402 (value transfer) are now coordinating under the Linux Foundation's Agentic AI Foundation, not competing. A2A v1.2 has 150+ orgs in production with signed Agent Cards and optional gRPC. MCP's Nov 2025 release added server-side agent loops, async tasks, and the extensions system; MCP Apps (Jan 2026) brought sandboxed HTML in chat.

The genuinely creative frontier is narrower than the hype suggests, but real:

- **Latent-space communication** — Interlat (arxiv 2511.09149) and LatentMAS (ICML 2026 Spotlight) let matched-architecture agents exchange last-hidden-states instead of tokens. 24× compression, measurably more exploratory behavior. The "tokens are a downsampling tax" objection is now quantified, not rhetorical. Not production-ready.
- **1980s coordination patterns returned wholesale.** Blackboards (Hayes-Roth 1985) beat master/slave and RAG by 13-57% in recent papers. Contract Net Protocol returned as token-cost auctions. The Turn language (arxiv 2603.08755) lands Erlang mailboxes + confidence operators + capability identity as a first-class agent language.
- **Decentralized identity / gossip meshes** — ANP with W3C `did:wba`; Hyperspace's 67-agent P2P run that rediscovered Kaiming init in 20 hours via GossipSub. Wild-card threads, watch but don't bet.

**Failure-mode vocabulary is now industry-standard.** Willison's lethal trifecta, Meta's Agents Rule of Two (Oct 2025), the Anthropic/OpenAI/DeepMind Attacker Moves Second paper, the Agent Stability Index across 12 drift dimensions, the 17.2× error amplification figure for uncoordinated chains, and Agent Deadlock Syndrome are all named, papered, and citable.

## L2 — durability is the load-bearing layer

This is where the action moved in 2026. The dominant pattern is **boring distributed systems hygiene wrapped around agents** — a durable execution engine holds the workflow graph, a real bus carries traffic, OTel GenAI ties it together.

**Temporal is Tier S right now.** OpenAI Agents SDK Python integration went GA March 2026, OpenAI Codex runs on it, $300M Series D in February 2026. The replay-history-on-crash model handles container restarts in a way LangGraph 1.x cannot. LangGraph protects against application failures, not infrastructure failures; the 2026 reference stack is LangGraph + Temporal/DBOS, not LangGraph alone.

**Two quantified failure facts to internalize:**

1. ~2% of all LLM spans in March 2026 returned errors, with ~8.4M of those being rate limits (Datadog).
2. The GetOnStack incident saw an agent-to-agent infinite loop run 11 days and cost $47k before circuit breakers caught it.

**The universal root cause** is conflating "transient retry" (return cached result, do not re-execute) with "sampling retry" (generate genuinely new response). Idempotency keys + outbox pattern fix it.

The interesting work in 2026 is no longer "how do agents talk" — it is **how do agents fail safely.** Sagas with compensating actions, schema evolution, cost-aware circuit breakers, all borrowed from generic distributed systems and now finally being applied to agent workloads.

## L1 — k8s landed, but k8s-minus is credible

**The k8s-native stack converged** around Dapr Agents v1.0 (CNCF, NVIDIA-backed, GA at KubeCon EU 2026) as the runtime, NATS JetStream or Strimzi as the bus, Temporal Worker Controller for durable execution, Istio Ambient or Cilium for sidecarless mTLS + SPIFFE identity, Agent Gateway (kgateway, Rust) for A2A/MCP/LLM north-south traffic, KEDA for autoscaling, OTel GenAI semconv into Tempo/Loki/Prometheus.

**Standards consolidated under the Agentic AI Foundation.** MCP was donated to AAIF; A2A v1.2 is now the cross-vendor agent-to-agent protocol with 150+ orgs in production (Google, Microsoft, AWS, Salesforce, SAP, ServiceNow). CloudEvents remains the event lingua franca; AsyncAPI + Apicurio handle schema.

**Prompts-as-CRDs is real but small.** Kagenti (Red Hat) ships `AgentCard`, `AgentRuntime`, and `Component` CRDs with SPIFFE-injected sidecars, slated for Red Hat AI H2 2026. Pinterest's MCP ecosystem (InfoQ Apr 2026) is the highest-fidelity production pattern published so far. Everyone else uses ConfigMaps + GitOps.

**The k8s-minus alternative is credible for solo builders.** Cloudflare Workflows GA + Durable Objects + Dynamic Workflows (MIT, per-tenant code) supports 50k concurrent workflows at near-zero idle cost; Modal dominates sandboxed agentic execution ($87M Series B). Fly.io GPUs deprecated after August 2026.

**Cost floor:** ~$500/mo for a hobby k8s footprint; realistic enterprise floor $3-10k/mo before model spend.

**Heads-up:** LiteLLM had a March 2026 PyPI supply-chain compromise. Pin versions.

## Where Helioy sits — and the shortest path forward

```
                    helioy-bus today          mid-term target          enterprise k8s
                    (single machine)          (single machine,         (north star)
                                              hardened)
L3 protocol         custom JSON envelopes  →  A2A v1.2 envelope     →  same A2A,
                    + tmux pane addressing    over local socket        Agent Gateway routes
L2 durability       in-memory mailbox      →  SQLite outbox +       →  Temporal Worker
                    (lossy on restart)        idempotency keys +       Controller + NATS
                                              OTel GenAI spans         JetStream
L1 runtime          tmux panes             →  same                  →  Dapr Agents + KEDA
                                                                       + Kagenti CRDs
```

### Move 1 — wrap envelopes in A2A v1.2 (now)

helioy-bus today uses a custom JSON envelope addressed by tmux pane. Re-shape the envelope to match A2A v1.2. Cost: small. Payoff: every future move (k8s, Dapr, Agent Gateway, Pinterest-style production) already speaks this wire format. No vendor lock since A2A is LF-governed.

**Why:** the protocol war ended. Building anything net-new on a custom envelope in mid-2026 is a self-inflicted migration tax.

### Move 2 — SQLite outbox + idempotency keys + OTel GenAI spans (when durability matters)

The durable layer report's explicit recommendation for helioy-bus: this combo gets ~80% of a production durability stack at single-machine cost.

- **SQLite outbox** — message persists to a WAL-mode table before delivery. Crash-safe replay. Aligns with the SQLite-FTS5 pattern already in use elsewhere in Helioy (claudex).
- **Idempotency keys** — every tool call gets a deterministic key; retries return cached result, never re-execute. Prevents GetOnStack-class retry-storm bugs.
- **OTel GenAI semconv** — ratified Q1 2026; works with Tempo/Loki/Prometheus or Langfuse/Phoenix without rewriting later.

### Move 3 — when single-machine breaks, jump to Restate or Hatchet (NOT Temporal first)

Both are Postgres-shaped, both have native Pydantic AI / OpenAI Agents SDK adapters, both run on a single managed Postgres. Temporal is correct at enterprise scale but operationally heavier — only reach for it when the cluster is real, the SRE is real, and the workflow count is real. For Helioy's likely first multi-host phase, Restate/Hatchet is the right rung.

**Why:** "Tier S" does not mean "use first." It means "right answer at scale." Choose tools by team size, not landscape rank.

## What we are NOT doing

- **Not building latent-space comms** (Interlat / LatentMAS) — frontier R&D, requires matched-architecture agents.
- **Not adopting libp2p / gossip / DID identity layers** — wild-card threads.
- **Not jumping straight to k8s** — k8s-minus is credible for solo-builder scale and the idle cost is near-zero.
- **Not adopting LangGraph alone** — protects application failures, not infrastructure failures. Pair with Temporal/DBOS or skip.

## Source layer reports

- [`2026-05-inter-agent-comm-novel.md`](./2026-05-inter-agent-comm-novel.md) — frontier patterns, latent-space comms, protocol stack consolidation, failure-mode vocabulary.
- [`2026-05-inter-agent-comm-durable.md`](./2026-05-inter-agent-comm-durable.md) — Tier S/A/B/F durability stack, postmortems, idempotency, OTel GenAI.
- [`2026-05-inter-agent-comm-k8s.md`](./2026-05-inter-agent-comm-k8s.md) — k8s reference architecture, Dapr Agents / Kagenti / kgateway, migration path, k8s-minus alternative.

## cm cross-references

- Reference entry `019e4579-fc97-7783-9bad-1e9cbba85309` — three-layer map + artifact pointers, scope `global/project:helioy`.
- Decision entry `019e457a-5df5-7211-9a88-983e3ead8c9e` — helioy-bus migration path (the three Moves above), scope `global/project:helioy`.
