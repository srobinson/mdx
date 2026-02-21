---
title: Production-grade inter-agent communication, mid-2026
type: research
tags: [agents, durable-execution, observability, messaging, infrastructure, helioy-bus]
summary: Reliability tier list and pattern catalog for inter-agent transports, durable execution engines, idempotency, observability, and backpressure as practiced by serious teams in May 2026.
status: active
confidence: high
created: 2026-05-20
updated: 2026-05-20
---

## Executive Summary

The "agent infra" conversation in 2026 has stopped being about frameworks and started being about boring distributed systems hygiene. The dominant pattern is a durable execution engine (Temporal, Restate, DBOS, Hatchet, Cloudflare Workflows) holding the workflow graph, a battle-tested transport (NATS JetStream, Kafka, Redis Streams, Postgres outbox) carrying messages between agents, and OpenTelemetry GenAI conventions (ratified for client spans early 2026) wiring everything to existing observability stacks. Single-machine systems like `helioy-bus` can borrow nearly all of these patterns: SQLite WAL + outbox + idempotency keys + OTel GenAI spans gets you 80% of what production teams run, without leaving one box.

## Reliability tier list

**Tier S — bet the system on it**
- **Temporal** + first-class agent SDK integration (OpenAI Agents SDK GA March 2026). Event-history replay handles container restarts cleanly. Used in production by OpenAI Codex. $300M Series D Feb 2026.
- **OpenTelemetry GenAI semantic conventions**. Client spans exited experimental in early 2026. Datadog, Honeycomb, New Relic, Langfuse, Phoenix all consume them. Use these or you are reinventing tracing in a year.
- **Postgres as a substrate** (transactional outbox, advisory locks, LISTEN/NOTIFY). The boring choice the serious people pick when they want one fewer thing in the diagram.

**Tier A — solid, picked by competent teams**
- **Restate** (durable RPC + sessions + journals in a single binary, native Pydantic AI + OpenAI Agents SDK integrations Mar/Apr 2026).
- **Hatchet** (Postgres-backed, simpler than Temporal, "billions of tasks/month" claim, YC-backed).
- **DBOS** (lightweight library on top of Postgres; checkpoints at decorated function boundaries; Pydantic AI integration).
- **NATS JetStream** (at-least-once and exactly-once delivery; the message bus Temporal/Restate themselves trust for related workloads).
- **Apache Kafka + Flink** (Confluent Streaming Agents, A2A bridge GA, replayable event streams as agent shared memory).
- **Cloudflare Workflows + Durable Objects** (50k concurrent workflows post May 2026 rearchitecture, hibernate-on-idle is uniquely cheap for long-tail agents).
- **Redis Streams** for in-cluster outbox + durable handoff when state already lives in Redis.
- **Langfuse / Arize Phoenix** for OTel-native multi-agent traces with hierarchical spans.

**Tier B — works with caveats**
- **LangGraph 1.x checkpointing** alone (covers application-level failure, *not* infrastructure-level; pair with Temporal or DBOS for the latter).
- **Postgres LISTEN/NOTIFY** as the only transport (no replay, 8KB payload cap, no consumer groups; fine as a wakeup signal on top of an outbox table).
- **WebSockets** for inter-agent traffic (no replay, no consumer groups, reconnect storms; use SSE one-way or gRPC streaming bidirectionally instead).
- **Inngest / Trigger.dev v3** (great DX, agent-friendly, but heavier SaaS lock-in and weaker for tight multi-agent fan-out).
- **SQLite WAL as a bus** for >10 sustained writes/sec. Below that ceiling it is genuinely excellent. `helioy-bus` lives in this bucket.

**Tier F — avoid for agent traffic**
- **Naked HTTP without idempotency keys**. Retry storm waiting to happen; production reports show 30 to 60% of unexpected inference spend traces to undeduped retries.
- **Exponential backoff without jitter** across multi-agent fleets. Thundering herd on every 429 recovery. Documented Cordum 2026 incident shape: 150 replicas reconnecting on 2s intervals.
- **Mocks of tool calls treated as exactly-once.** Idempotency is on the *callee*, not the retry library.
- **RabbitMQ classic queues for replay-heavy agent traffic.** Streams are fine, but reach for JetStream or Kafka first if replay is a first-class need.
- **Bespoke "I will just retry in a loop" tool wrappers without compensating actions.** Sagas exist for a reason.

## 1. Durable execution engines — the dominant 2025 to 2026 story

Durable execution is the load-bearing primitive of 2026 agent infra. The mental model: code declares workflow steps; the engine journals every step and every external call; on crash, the engine replays the journal and resumes at the failure point, returning cached results for steps that already completed.

- **Temporal** ([temporal.io](https://temporal.io/blog/announcing-openai-agents-sdk-integration)) — March 2026 brought OpenAI Agents SDK Python integration to GA; agents run as Temporal workflows, tool calls as activities. Container dies, workflow replays history, picks up at the next step. Replay 2026 added Temporal Workers on AWS Lambda (auto-scaled by Temporal Cloud). Heavyweight operationally, unmatched for multi-hour, multi-agent flows where restart-is-acceptable does not work.
- **Restate** ([docs.restate.dev/ai/patterns/durable-agents](https://docs.restate.dev/ai/patterns/durable-agents)) — single binary, no separate DB or broker, supports durable RPC + sessions + concurrency control + human-in-the-loop. April 2026 Pydantic AI integration; works framework-agnostically with Vercel AI SDK, OpenAI Agents, Google ADK, LangChain. Closest competitor to Temporal for new builds; lower op overhead.
- **DBOS** ([dbos.dev](https://www.dbos.dev/)) — library, not a platform. Decorate Python or TypeScript functions; checkpoints persist into your existing Postgres. The right choice when you already run Postgres and do not want to add infrastructure. Less flexible than Temporal for complex multi-agent fan-out.
- **Hatchet** ([github.com/hatchet-dev/hatchet](https://github.com/hatchet-dev/hatchet)) — Postgres-backed orchestration engine; "every task invocation is durably logged"; AI agents land as durable functions. Python, TypeScript, Go, Ruby. Simpler op model than Temporal.
- **Cloudflare Workflows + Durable Objects** ([developers.cloudflare.com/workflows/get-started/durable-agents](https://developers.cloudflare.com/workflows/get-started/durable-agents)) — May 2026 control plane rearchitecture: 50,000 concurrent workflow instances per account (up from 4,500), 300/sec creation rate. Each agent is a Durable Object with its own SQLite. Hibernates when idle, near-zero cost when inactive. Uniquely good for long-tail agent fleets.
- **Inngest, Trigger.dev v3** — strongest TypeScript DX, agent-friendly primitives (event-driven steps, durable resumes, human-in-the-loop gates). Cleaner ergonomics than Temporal; fewer escape hatches for hairy multi-agent topologies. Inngest wins zero-config; Trigger.dev v3 wins self-host.

**LangGraph 1.x is *not* durable execution.** It checkpoints application-level state into Postgres or DynamoDB and protects against application crashes; it does not protect against container restarts in the middle of a step. The 2026 reference architecture is LangGraph + Temporal (or DBOS): LangGraph holds the agent control flow graph, Temporal wraps it for infrastructure-level durability. ([agentmarketcap 2026-04-10](https://agentmarketcap.ai/blog/2026/04/10/durable-agent-execution-production-temporal-modal-event-sourced) quantifies the gap: agents show >91% failure rates on complex office tasks without durability; checkpoint-based recovery cuts wasted processing by 60%+ on multi-step workflows.)

## 2. Transports for inter-agent traffic

- **NATS JetStream** ([docs.nats.io](https://docs.nats.io/nats-concepts/jetstream)) — JetStream is what serious agent control planes pick when they want lightweight, fast, durable streams with consumer groups and replay. Core NATS publish acks are local only; JetStream acks are durable. Active 2026 patterns published on reconnect jitter sizing for AI agent control planes (Cordum, "150 replicas reconnecting every 2s creates retry pressure that arrives in waves rather than smoothly"). When to reach for it: you outgrew Redis Pub/Sub and want consumer groups + replay without Kafka op cost. When not: if Postgres + outbox is enough, you do not need another box.
- **Apache Kafka + Flink (Confluent Streaming Agents)** ([confluent.io/blog/multi-agent-orchestrator-using-flink-and-kafka](https://www.confluent.io/blog/multi-agent-orchestrator-using-flink-and-kafka/)) — Kafka acts as the agents' "short-term shared memory"; Flink is the routing/processing engine. Topics like `agent_messages` and `incoming_leads` hold the event log; agent definitions enforce input/output schemas via Confluent's stream governance. The A2A protocol now bridges into Flink natively, so external A2A agents on LangChain or SAP can hand off via replayable Kafka streams. Best when you already run Kafka or want true cross-vendor agent meshes.
- **Redis Streams** ([dev.to/redis/building-reliable-agents-with-the-transactional-outbox-pattern-and-redis-streams](https://dev.to/redis/building-reliable-agents-with-the-transactional-outbox-pattern-and-redis-streams-45e6)) — when state lives in Redis already, do the outbox in Redis: hash tag `{tenant}` ensures atomic `MULTI/EXEC` writes the state and the stream entry together. Per-tenant streams give natural partitioning. Also the canonical pattern for resumable LLM token streams (Upstash).
- **Postgres LISTEN/NOTIFY + outbox** ([thinhdanggroup.github.io/postgres-as-a-message-bus](https://thinhdanggroup.github.io/postgres-as-a-message-bus/)) — the boring choice. Outbox table writes are atomic with state changes (one transaction); NOTIFY signals workers to drain; logical replication is the push-based variant. Notifications are transactional: rollback means no NOTIFY. Caveat: NOTIFY payloads cap at 8KB and there are no consumer groups, so always pair with an outbox table for replay and at-least-once. Best on-ramp for teams that already run Postgres.
- **SQLite + WAL** ([dev.to/minnzen/building-a-durable-message-queue-on-sqlite-for-ai-agent-orchestration](https://dev.to/minnzen/building-a-durable-message-queue-on-sqlite-for-ai-agent-orchestration-335m); [sqlite.org/wal.html](https://sqlite.org/wal.html)) — one writer, many readers, no contention, ACID across messages and state. The right primitive for a single-machine agent bus (which is what `helioy-bus` is). Ceiling is roughly 10 sustained writes/sec before queue buildup; for solo dev agent fleets you will never see this. Use `litequeue` patterns or roll a `messages(id, status, claimed_by, payload, idempotency_key)` table with `SELECT ... FOR UPDATE SKIP LOCKED` semantics emulated via short transactions.
- **gRPC streaming vs WebSockets vs SSE** — for agent IO: SSE for one-way LLM token streams (every major LLM API uses it); WebSockets for bidirectional UI traffic; gRPC bidi streaming for service-to-service control planes you control. WebSockets *across* an agent fleet add reconnect storms; prefer a real bus.

## 3. Event sourcing for replayable agents

Event-sourced agent state is finally a recognized pattern in 2026. The orchestrator records every accepted agent intention into an append-only log; state is derived by folding the log; replay reproduces the exact decision history.

- Use it when audit, replay-with-new-model evaluation, or compliance (e.g. ESAA-Security) matter. The Anthropic multi-agent research system uses an artifact pattern (subagents store work externally, pass references to the lead agent) precisely to avoid losing information through stages.
- Tools: Kurrent (formerly EventStoreDB), Marten for .NET, EventSourcingDB are the dedicated stores; Postgres tables with `(stream_id, version, event_type, payload, ts)` are perfectly fine for most agent workloads.
- The big payoff for agent systems: deterministic replay against a *new* model lets you A/B reasoning chains, which is exactly the workflow LangSmith and Braintrust have built UI for.

## 4. Idempotency and exactly-once for tool calls

The single most under-engineered area in solo agent systems. The clarifying distinction from Tian Pan's April 2026 piece ([tianpan.co](https://tianpan.co/blog/2026-04-20-idempotency-llm-pipelines)) is between *transient retries* (operation succeeded, response lost) and *sampling retries* (output failed validation, want a different answer). They demand opposite behavior.

Production patterns:

- **Idempotency keys on every side-effecting tool call.** Key is a hash of the logical unit of work (document hash + extraction timestamp + action type), not the inference request. Downstream system stores the key + result; duplicates return cached result.
- **Semantic deduplication for agent actions.** Embed the tool call, compare cosine similarity to recent calls; threshold ~0.85 to ~0.9 for "same intent." Real deployments report 20 to 45% cache hit rates.
- **Completion records before irreversible actions.** Write intent + idempotency key to a durable log *before* executing; on recovery you can distinguish "started but unconfirmed" from "never started."
- **Saga + compensating actions for multi-step.** Each step succeeds or its compensation reverses it; compensations execute in reverse order; compensations must themselves be idempotent. Temporal has first-class sagas; for DIY, the state machine is `Pending -> InProgress -> Succeeded` or `Pending -> InProgress -> Compensating -> Compensated -> Failed`.
- **Separate retry policy from sampling policy.** Two knobs, never one. Conflating them is the documented root cause of duplicate emails, double-charges, and duplicate writes.

## 5. Observability for multi-agent traffic

OpenTelemetry GenAI semantic conventions ([opentelemetry.io/docs/specs/semconv/gen-ai/gen-ai-agent-spans](https://opentelemetry.io/docs/specs/semconv/gen-ai/gen-ai-agent-spans/)) are the standard. Client spans exited experimental in early 2026; agent and framework spans are still experimental but stable in practice. Adopt them now. Top-level `invoke_agent` span with child `chat` spans per LLM call and `execute_tool` spans per tool invocation, attributes covering `gen_ai.request.model`, `gen_ai.usage.input_tokens`, `gen_ai.response.finish_reasons`, etc.

Vendor positioning for multi-agent specifically:

- **Langfuse** — OTel-native, hierarchical span model renders nested multi-agent traces cleanly, self-host free. Best default for framework-agnostic multi-agent stacks. ([langfuse.com](https://langfuse.com/faq/all/best-phoenix-arize-alternatives))
- **Arize Phoenix** — fully OSS, strong on subagent hallucination eval (LLM-as-judge at subagent output layer). Best for RAG-heavy and evaluation-first workflows.
- **LangSmith** — unmatched LangChain/LangGraph integration depth; LangGraph state-diff tracing and replay-against-new-model eval are the killer features.
- **Braintrust** — closed source, evaluation-first; pair with Helicone or Langfuse for raw observability.
- **Helicone** — Apache 2.0 reverse proxy in front of LLM providers; cheapest possible "log every request, change one base URL." No evals to speak of, but great as the data layer for something else.
- **Weights & Biases Weave** — only if your ML team already lives in W&B.

The agent-specific observation: prefer tools that group distributed traces across services. Langfuse and OTel-native vendors do this natively; older single-call-focused tools struggle to render handoffs between agents as one trace.

## 6. Schema and contract management

- **Protobuf** for inter-service agent control planes. Schema evolution discipline: never reuse field numbers; additions are safe; proto3 makes fields effectively optional. Pair with a schema registry (Confluent's, Apicurio, or roll your own table of `(schema_id, version, proto, compatibility_mode)`).
- **JSON Schema** for human-facing or REST-fronted agent traffic and for tool argument validation. Pydantic models in Python emit JSON Schema for free and are the de facto contract layer for the OpenAI Agents SDK and Pydantic AI.
- **MessagePack** or **CBOR** where you want JSON's flexibility and Protobuf's compactness without the IDL discipline; reasonable for `helioy-bus`-class workloads.
- **Tool-schema versioning.** When an upstream agent gets a new tool, downstream agents should not break. Include a `tool_schema_version` field on every dispatch; capability negotiation on handshake (the A2A protocol's "agent cards" formalize this with cryptographic signatures since v1.2).

## 7. Backpressure, rate limiting, circuit breakers

The most quotable finding of 2026: in March 2026, 2% of all LLM spans in a measured corpus returned errors; nearly a third of those (8.4 million) were rate-limit errors. Backpressure is not optional.

The four-pattern stack ([tianpan.co 2026-04-15](https://tianpan.co/blog/2026-04-15-backpressure-llm-pipelines)):

1. **Token bucket queuing** — consume tokens proportional to *estimated input + max_tokens*, not request count. A 50-token prompt and a 10,000-token prompt have radically different costs but identical RPM.
2. **Priority lanes** — P0 interactive, P1 non-interactive automation, P2+ batch. Reported 40 to 90% SLO improvement vs FCFS.
3. **Circuit breakers with token-budget awareness** — trip on token consumption rate at 85% of TPM, on P95 latency exceeding 3x baseline, on hourly cost cap, on consecutive 429 count. Not just error rate.
4. **Load shedding** — 503 immediately when queue depth exceeds threshold; *do not* accept and fail later. Add session-level token budget caps because "tool call outputs consume roughly 100x more tokens than user messages."

Concrete cautionary tale: the GetOnStack incident, an undetected agent-to-agent infinite loop ran 11 days and drove costs from $127/week to $47,000. Circuit breakers with cost-velocity triggers catch this.

Always: exponential backoff *with jitter*. Without jitter, ten agents that hit 429 simultaneously retry simultaneously and hit 429 again.

## 8. Public case studies and shipping architectures

- **Anthropic multi-agent research system** ([anthropic.com/engineering/multi-agent-research-system](https://www.anthropic.com/engineering/multi-agent-research-system)) — orchestrator-worker with Opus 4 lead, Sonnet 4 subagents (+90.2% vs single-agent). Lead agent checkpoints plan to Memory to survive 200k token truncation. Built systems that "resume from where the agent was when errors occurred" instead of restarting. Rainbow deployments to avoid disrupting in-flight agents. Synchronous subagent execution is a known limitation. Artifact pattern: subagents store work externally, pass references back. Multi-agent uses ~15x more tokens than chat; only justified when task value is high.
- **OpenAI Codex on Temporal** — confirmed via Temporal's GA announcement and the Replay 2026 keynote. Container restarts replay workflow history; LLM calls and tool invocations are durable activities.
- **Cloudflare Agents SDK + Workflows** — `AgentWorkflow` class extends Workflows with bidirectional Agent RPC + WebSocket broadcast. Each agent is a Durable Object; hibernation makes long-tail agent fleets cheap.
- **Confluent Intelligence (Streaming Agents)** — Kafka as agent shared memory, Flink as router, A2A bridge for cross-vendor handoff. Production references across Microsoft, AWS, Salesforce, SAP, ServiceNow (via A2A v1.2 Linux Foundation adoption with 150+ organizations).

## 9. What this means for `helioy-bus`

A single-machine, solo-builder agent bus does not need Temporal or NATS to be production-grade. The pattern that maps cleanly to SQLite:

1. **Outbox table as the bus.** `messages(id, ts, from_agent, to_agent, kind, payload, idempotency_key, status, claimed_by, claimed_at, attempts)`. Atomic insert with whatever state change triggered it.
2. **Idempotency keys on every side-effecting tool call.** Downstream tool checks the key, returns cached result on duplicate. The dedup table is a sibling of the outbox.
3. **Claim semantics via short transactions.** `UPDATE messages SET status='claimed', claimed_by=:agent WHERE id IN (SELECT id FROM messages WHERE status='pending' ORDER BY ts LIMIT 1)` style.
4. **Compensations registered with the message.** Same row carries a `compensation_kind` and `compensation_payload`. A saga is just an ordered list of completed message IDs with reverse-order compensation on failure.
5. **Two-knob retry.** Library retries transient errors (network, 5xx) with jitter; agent reasoning loop handles sampling retries (re-prompt with error feedback) explicitly.
6. **OTel GenAI spans wrapping every dispatch.** `invoke_agent` parent span, child `execute_tool` per side-effecting call. Export to Langfuse (self-hosted) or Phoenix.
7. **Backpressure as a queue depth check.** Reject (or pause) new dispatches when claimed-but-unfinished message count exceeds N. No need for token buckets at solo scale, but priority lanes (urgent vs background tasks) cost almost nothing to add.
8. **Schema versioning on the message envelope.** `kind` + `kind_version` columns; consumers reject unknown versions explicitly.

This is exactly the Postgres outbox pattern at single-machine scale, and it inherits the same correctness properties. The day you outgrow it, the migration target is Restate or Hatchet (Postgres-shaped) rather than Temporal (operationally heavier).

## Synthesis — the boring durable stack of mid-2026

A "boring, durable, production" inter-agent comm stack in mid-2026 looks like this. State and outbox live in one transactional store (Postgres or, for single-machine, SQLite WAL); a durable execution engine (Temporal, Restate, DBOS, or Hatchet) owns the workflow graph and replays history on crash; a real bus (NATS JetStream, Kafka, or Redis Streams) carries inter-agent traffic with consumer groups and replay; every side-effecting tool call has an idempotency key with a callee-side dedup window, and multi-step flows compose into sagas with explicit compensations. The wire format is Protobuf or JSON Schema-validated JSON with a schema registry, the envelope carries `kind` plus version, and the message envelope is OpenTelemetry-traced with GenAI semantic conventions so traces stitch across agents. Backpressure is token-bucket + priority-lane + cost-aware circuit breakers, never exponential backoff without jitter, and the whole thing is observable end-to-end in Langfuse or Phoenix or whatever OTel-native vendor the team already runs. Replace any tier with a tier from `helioy-bus`-scale (SQLite outbox + DBOS + OTel) and you have the same shape at zero op cost. The interesting work in 2026 is no longer "how do agents talk" — it is "how do agents fail safely."

## Sources consulted

**Durable execution**
- [Temporal: OpenAI Agents SDK GA](https://temporal.io/blog/announcing-openai-agents-sdk-integration)
- [Temporal: Replay 2026 announcements](https://temporal.io/blog/replay-2026-product-announcements)
- [Temporal Series D coverage](https://www.xgrid.co/resources/why-temporal-series-d-matters-for-agentic-ai-execution/)
- [Restate: Durable Agents](https://docs.restate.dev/ai/patterns/durable-agents)
- [Restate: AI examples (A2A, MCP)](https://github.com/restatedev/ai-examples)
- [DBOS: Pydantic AI integration](https://pydantic.dev/articles/pydantic-ai-dbos)
- [DBOS: Why Postgres for durable execution](https://www.dbos.dev/blog/why-postgres-durable-execution)
- [Hatchet on GitHub](https://github.com/hatchet-dev/hatchet)
- [Cloudflare: Build a Durable AI Agent](https://developers.cloudflare.com/workflows/get-started/durable-agents/)
- [InfoQ: Cloudflare Dynamic Workflows](https://www.infoq.com/news/2026/05/cloudflare-dynamic-workflows/)
- [Cloudflare Workflows GA](https://blog.cloudflare.com/workflows-ga-production-ready-durable-execution/)
- [AgentMarketCap: durable agent execution 2026](https://agentmarketcap.ai/blog/2026/04/10/durable-agent-execution-production-temporal-modal-event-sourced)
- [AgentMarketCap: LangGraph vs Temporal](https://agentmarketcap.ai/blog/2026/04/08/langgraph-vs-temporal-long-running-agent-workflows-2026)
- [Zylos: durable execution patterns](https://zylos.ai/research/2026-02-17-durable-execution-ai-agents)

**Transports**
- [Cordum: NATS reconnect jitter for agent control planes](https://cordum.io/blog/ai-agent-nats-reconnect-jitter-storm-control)
- [Cordum: NATS publish confirmation vs JetStream ack](https://cordum.io/blog/ai-agent-nats-publish-confirmation-core-vs-jetstream)
- [Confluent: multi-agent orchestrator using Flink and Kafka](https://www.confluent.io/blog/multi-agent-orchestrator-using-flink-and-kafka/)
- [Confluent Intelligence A2A update](https://siliconangle.com/2026/02/26/confluent-intelligence-adds-streaming-agents-mix-enable-agent-agent-collaboration/)
- [Sean Falconer: Kafka, A2A, MCP, Flink](https://thenewstack.io/a2a-mcp-kafka-and-flink-the-new-stack-for-ai-agents/)
- [Redis: building reliable agents with outbox + streams](https://dev.to/redis/building-reliable-agents-with-the-transactional-outbox-pattern-and-redis-streams-45e6)
- [Upstash: resumable LLM streams](https://upstash.com/blog/resumable-llm-streams)
- [ThinhDA: Postgres as a message bus](https://thinhdanggroup.github.io/postgres-as-a-message-bus/)
- [Event-Driven.io: push-based outbox with logical replication](https://event-driven.io/en/push_based_outbox_pattern_with_postgres_logical_replication/)
- [SQLite WAL docs](https://sqlite.org/wal.html)
- [Building a durable message queue on SQLite for agents](https://dev.to/minnzen/building-a-durable-message-queue-on-sqlite-for-ai-agent-orchestration-335m)

**Protocols**
- [A2A Protocol: 150+ orgs adoption](https://www.linuxfoundation.org/press/a2a-protocol-surpasses-150-organizations-lands-in-major-cloud-platforms-and-sees-enterprise-production-use-in-first-year)
- [A2A v1 production status](https://stellagent.ai/insights/a2a-protocol-google-agent-to-agent)
- [WebSockets vs SSE vs gRPC for AI streaming](https://techai-explained.github.io/techai-explained/articles/websockets-vs-sse-vs-grpc/)

**Observability**
- [OTel GenAI agent spans spec](https://opentelemetry.io/docs/specs/semconv/gen-ai/gen-ai-agent-spans/)
- [OTel blog: inside the LLM call GenAI observability](https://opentelemetry.io/blog/2026/genai-observability/)
- [Langfuse vs Phoenix/Arize](https://langfuse.com/faq/all/best-phoenix-arize-alternatives)
- [Braintrust: best LLM tracing tools 2026](https://www.braintrust.dev/articles/best-llm-tracing-tools-2026)
- [Laminar: Langfuse alternatives 2026](https://laminar.sh/article/langfuse-alternatives-2026)

**Idempotency, sagas, retries**
- [Tian Pan: idempotency in LLM pipelines](https://tianpan.co/blog/2026-04-20-idempotency-llm-pipelines)
- [MightyBot: fault-tolerant agent pipelines](https://mightybot.ai/blog/fault-tolerant-ai-agent-pipelines/)
- [Temporal: sagas + compensating actions](https://temporal.io/blog/compensating-actions-part-of-a-complete-breakfast-with-sagas)
- [Agent Factory: Saga & Monitor workflow patterns](https://agentfactory.panaversity.org/docs/Deploying-Agent-Factories-in-the-Cloud/dapr-actors-workflows/workflow-patterns-saga-monitor)

**Backpressure**
- [Tian Pan: backpressure for LLM pipelines](https://tianpan.co/blog/2026-04-15-backpressure-llm-pipelines)
- [TrueFoundry: 3-layer gateway rate limiting](https://www.truefoundry.com/blog/rate-limiting-ai-agents-preventing-llm-api-exhaustion)
- [Datadog State of AI Engineering](https://www.datadoghq.com/state-of-ai-engineering/)
- [Hendricks: circuit breaker patterns for agents](https://brandonlincolnhendricks.com/research/circuit-breaker-patterns-ai-agent-reliability)

**Case studies**
- [Anthropic: multi-agent research system](https://www.anthropic.com/engineering/multi-agent-research-system)
- [InfoQ: Temporal-OpenAI public preview](https://www.infoq.com/news/2025/09/temporal-aiagent/)
- [Cloudflare Agents Week 2026](https://www.cloudflare.com/agents-week/updates/)

## Source quality assessment

High confidence on the durable-execution landscape: Temporal, Restate, DBOS, Hatchet, Cloudflare all have first-party docs and recent (Feb to May 2026) integration announcements with concrete code paths. Anthropic's multi-agent system post is primary source and rare. OTel GenAI conventions are official spec, ratification dates confirmed. Tian Pan's backpressure and idempotency pieces are independent technical analysis with named incidents (GetOnStack, Cordum) and quantified claims that triangulate against Datadog's State of AI Engineering numbers.

Medium confidence on positioning of observability vendors: most comparison articles come from one vendor analyzing competitors, so individual claims (e.g. "Langfuse renders nested spans cleanly") are accurate but rankings are biased.

Low confidence on the specific market share / adoption numbers; A2A's "150+ organizations" is from Linux Foundation press, plausible but unaudited. Anthropic's "+90.2% vs single-agent" is internal eval; treat as directional.

Gaps: no public postmortems from Cursor, Replit, Devin, Sourcegraph, or Codeium that name specific transport or durability infrastructure. They likely use a mix of Temporal/Restate-class engines + custom buses, but only Anthropic and OpenAI (via Temporal partnership) have been fully transparent.

## Open questions

- What does `helioy-bus` look like at "two-machine" scale? Does the SQLite outbox + DBOS pattern survive a second physical node, or does it require migration to Postgres + Restate?
- Is the A2A protocol stable enough to bet on for a solo system? V1.2 with cryptographic agent cards landed early 2026, but the spec is still moving.
- What is the actual cost ratio of "OTel GenAI spans for every inter-agent message" vs sampling? At Anthropic scale this matters; at solo scale it probably does not.
- How do teams handle agent-version skew during deployment? Anthropic mentions rainbow deployments; nobody else has published their pattern.

## Actionable takeaways

1. **For `helioy-bus`:** Add an outbox table + idempotency keys + OTel GenAI spans. Three weekend's work. Buys you most of the reliability of a "real" production stack.
2. **For the day you outgrow it:** Restate or Hatchet are the cleanest migration targets. Both are Postgres-shaped and ship Pydantic AI / OpenAI Agents SDK adapters.
3. **Wire OTel GenAI conventions now**, not later. The instrumentation cost compounds.
4. **Separate retry-policy from sampling-policy in every tool wrapper.** This is the single highest-leverage change in agent systems and is criminally under-applied.
5. **Read the Anthropic multi-agent post and the Tian Pan pieces directly.** They are the highest signal-per-word in this corpus.
