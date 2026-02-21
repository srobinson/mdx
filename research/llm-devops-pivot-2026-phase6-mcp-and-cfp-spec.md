---
type: research
status: active
confidence: high
created: 2026-05-16
updated: 2026-05-16
target: portfolio-build-spec
audience: senior-devops-veteran-15y-aws-azure-gcp-k8s-streaming
parent: llm-devops-pivot-2026-90day-roadmap.md
sibling: llm-devops-pivot-2026-phase3-streaming-rag-spec.md
grandparent: llm-devops-pivot-2026.md
tags:
  - phase-6-spec
  - mcp-authorship
  - operator-of-operators
  - kubecon-cfp
  - thought-leadership
  - llm-devops-pivot
---

# Phase 6 Spec — MCP Server, KubeCon CFP, and Thought Leadership

The closing two-week phase of the 90-day pivot. Three deliverables stacked, lead with the MCP server because it produces the credibility marker the dossier identifies as the 2026 equivalent of "I shipped a Helm chart." The CFP and the thought-leadership piece reuse Phase 3's metrics; their cost is mostly writing time.

This document is opinionated. Stuart can deviate; every deviation should be conscious.

## What this phase proves

| Deliverable | Signal it sends |
|---|---|
| **Production-shape MCP server** | You understand MCP as the new system-call boundary, not as a toy wrapper. You know the operator-of-operators pattern. You write secure ops surfaces by default. |
| **KubeCon (or equivalent) CFP submission** | You can frame your work as a talk and ship it. You belong on a stage. |
| **One public thought-leadership piece** | You synthesize and write, not just build. Recruiters and engineering leaders find you. |

Together these mark you as someone who builds **and** distributes. The 2026 hiring market reads both signals.

## Part 1 — The MCP server

### What to build (locked recommendation)

**`streaming-rag-mcp` — an MCP server that operates the Phase 3 streaming-RAG platform.**

The pitch:

> The Phase 3 repo is the platform. The Phase 6 MCP server makes that platform operable by agents. Every runbook from `docs/runbooks/` becomes a tool call. Every metric on the Grafana dashboard becomes a resource. The agent can triage, diagnose, replay, re-embed — under explicit human-approved write boundaries — while the human reviews the proposed actions.

This is the operator-of-operators pattern called out in the parent dossier (Komodor Klaudia, SUSE Liz). Building it on top of your own platform is the rare repo that proves both halves: you built the system, *and* you built the agent interface to operate it.

### Alternative candidates considered

| Candidate | Why not lead with it |
|---|---|
| MCP for an old Kafka cluster | Strong on craft, weak on narrative — doesn't compose with Phase 3 |
| MCP for AWS read-only ops | Competes head-on with AWS Labs' official MCP suite. Lose the differentiation battle. |
| MCP for homelab Kubernetes | Surface too small to demonstrate platform thinking |
| MCP for an in-house service at a past employer | IP risk; can't be public |

**Decision:** build `streaming-rag-mcp`. Fall back to Kafka-ops MCP only if Phase 3 slipped and the platform isn't live by day 71.

### The tool surface

The full surface, split by safety class.

#### Read-only tools (no env-var gate)

| Tool | Purpose |
|---|---|
| `pipeline_status()` | Health snapshot across producer, Flink jobs, sink, Qdrant, API |
| `freshness_lag(window_minutes=60)` | p50/p90/p99 of the freshness probe over a window |
| `dlq_inspect(topic, limit=20, since="1h")` | Recent DLQ messages with poison reason classification |
| `consumer_lag(consumer_group)` | Per-partition consumer lag for any group |
| `topic_describe(topic)` | Partition count, replication factor, retention, throughput |
| `tenant_list()` | Configured tenants with their category filters and quotas |
| `tenant_metrics(tenant_id, window_minutes=60)` | Per-tenant QPS, token spend, cache hit rate |
| `query_via_pipeline(query, tenant_id, return_sources=True)` | Exercise the query path; return answer + retrieved doc IDs + reranker scores |
| `eval_status(dataset_id="default")` | Last eval run results with delta vs prior run |
| `embedding_model_info()` | Current model id, version, dimension, throughput |

#### Mutating tools (env-var gated; default `dry_run=True`)

Mutations require `STREAMING_RAG_MCP_ALLOW_WRITES=true` set on the server, AND the caller must pass `dry_run=False` explicitly. Belt-and-suspenders by design.

| Tool | Purpose |
|---|---|
| `dlq_drain(topic, batch_size=100, dry_run=True)` | Drain DLQ entries (re-process or discard) |
| `replay_from_offset(topic, partition, offset, dry_run=True)` | Operational replay |
| `reembed_with_model(model_id, model_version, scope="all", dry_run=True)` | Trigger migration to a new embedding model |
| `tenant_create(tenant_id, category_filter, quota_tokens_per_hour, dry_run=True)` | Provision a tenant |
| `tenant_quota_set(tenant_id, max_tokens_per_hour, dry_run=True)` | Update quotas |
| `eval_run(dataset_id="default", dry_run=True)` | Kick off eval suite |

#### Resources (read-only data surface)

| Resource URI | Returns |
|---|---|
| `streaming-rag://pipeline/health` | JSON health snapshot, refreshed every 30s |
| `streaming-rag://topics` | Topic list with metadata |
| `streaming-rag://tenants` | Tenant configuration |
| `streaming-rag://models/embedding` | Current embedding model |
| `streaming-rag://dashboards/freshness-lag.png` | Live screenshot of the Grafana dashboard (PNG resource) |
| `streaming-rag://runbooks/{name}` | The markdown runbooks from Phase 3 `docs/runbooks/` as MCP resources |
| `streaming-rag://eval/golden_questions.json` | The golden eval dataset |
| `streaming-rag://schemas/arxiv_papers_raw.avsc` | Avro schemas |

Exposing the runbooks as resources is the design move that closes the loop with the parent dossier's "runbooks-as-prompts" framing. The agent reads the runbook, then calls the tools the runbook prescribes.

#### Prompts (templated agent prompts)

| Prompt name | Purpose |
|---|---|
| `triage_pipeline_alert` | Template for first-response triage: pulls `pipeline_status`, `freshness_lag`, `consumer_lag`, `dlq_inspect`, formats into an SRE diagnostic prompt |
| `postmortem_freshness_regression` | Template for drafting a freshness-regression postmortem; pulls metrics over the incident window |
| `tenant_onboarding` | Template for provisioning a new tenant, including the dry-run-first pattern |
| `migration_to_new_embedding_model` | Template for the re-embed migration runbook |

### Stack choices (locked)

| Layer | Choice | Reason |
|---|---|---|
| **SDK** | MCP Python SDK (Anthropic upstream) | Matches Phase 3 stack. Python ML/data tooling ecosystem alignment. |
| **Transport** | Streamable HTTP for production; stdio for local dev | Streamable HTTP is the 2026 production-shape per the MCP roadmap (95% latency reduction). stdio remains the dev-local default. |
| **Auth** | OAuth 2.1 with `.well-known/oauth-authorization-server` discovery, API-key fallback | OAuth is the 2026 production default. API-key keeps local dev frictionless. |
| **Schema validation** | Pydantic v2 with JSON Schema export | The SDK's preferred path; clean tool-input validation |
| **Observability** | OTel SDK + Langfuse exporter | Reuse Phase 3 + Phase 5 observability stack. Every tool call traced. |
| **Audit log** | Append-only JSON log to disk + OTel events to Tempo | Every mutating call logged with: timestamp, principal, tool name, args, dry-run flag, result hash. |
| **Packaging** | Docker image (multi-arch amd64/arm64) + Helm chart | The "we deploy this in production" signal |
| **Tests** | MCP SDK testing harness + pytest + property tests on dry-run idempotency | Catches the most common MCP authoring bug: tools that misreport their effects |
| **CI** | GitHub Actions: lint + tests + image build + Helm lint | Standard 2026 shape |

### Deliberately not chosen

- **Generic SDK wrappers (FastMCP-style high-level frameworks).** They hide the protocol; for a credibility artifact you want the raw SDK pattern visible.
- **Adding non-streaming-RAG tools** (kubectl, AWS, etc.). Keeps the scope focused. Bolt-on tools dilute the "platform operator" narrative.
- **A web UI for the MCP server.** The MCP server IS the UI; the agent is the user. A separate UI competes with the agent.
- **Auto-merge or auto-apply for any mutating tool.** Hard rule. The dossier's failure-mode catalogue (Amazon March 2026, AWS China Feb 2026, the IaC drift-reversal pattern) makes this non-negotiable.

### System architecture

```
                  ┌────────────────────────┐
                  │  Claude Code / Cursor /│
                  │  custom MCP client     │
                  └──────────┬─────────────┘
                             │
                  ┌──────────▼─────────────┐
                  │  Streamable HTTP       │
                  │  /mcp endpoint         │
                  └──────────┬─────────────┘
                             │
                  ┌──────────▼─────────────┐
                  │  OAuth 2.1 layer       │
                  │  (or API-key fallback) │
                  └──────────┬─────────────┘
                             │
                  ┌──────────▼─────────────┐
                  │  streaming-rag-mcp     │
                  │  - tool dispatch       │
                  │  - dry-run guard       │
                  │  - audit log writer    │
                  │  - OTel tracer         │
                  └────┬───────────────┬───┘
                       │               │
       ┌───────────────┘               └───────────────┐
       │                                               │
       ▼                                               ▼
┌──────────────┐                            ┌──────────────────┐
│  Phase 3     │                            │  Phase 3         │
│  Kafka /     │                            │  Qdrant / API /  │
│  Flink ops   │                            │  Eval / Grafana  │
│  surface     │                            │  surface         │
└──────────────┘                            └──────────────────┘
```

### Repository skeleton

```
streaming-rag-mcp/
├── README.md                       # the calling card
├── ARCHITECTURE.md                 # the diagram + protocol decisions
├── docs/
│   ├── tool-surface.md             # full tool/resource/prompt catalog
│   ├── security-model.md           # the dry-run + env-var gate writeup
│   ├── permissions-and-scopes.md   # OAuth scope design + API-key model
│   ├── observability.md            # audit log + OTel + Langfuse integration
│   ├── transport-choices.md        # Streamable HTTP vs stdio, when each
│   ├── operator-of-operators.md    # the design narrative
│   └── runbooks/
│       ├── deploy-helm.md
│       ├── rotate-credentials.md
│       └── add-a-new-tool.md
├── src/
│   └── streaming_rag_mcp/
│       ├── __init__.py
│       ├── server.py               # main MCP server entrypoint
│       ├── tools/
│       │   ├── readonly.py
│       │   ├── mutating.py
│       │   └── _dry_run.py         # the dry-run guard decorator
│       ├── resources/
│       │   ├── pipeline.py
│       │   ├── topics.py
│       │   └── runbooks.py
│       ├── prompts/
│       │   ├── triage.py
│       │   ├── postmortem.py
│       │   └── tenant_onboarding.py
│       ├── clients/
│       │   ├── kafka.py
│       │   ├── flink.py
│       │   ├── qdrant.py
│       │   └── api.py
│       ├── auth.py
│       ├── audit.py
│       └── observability.py
├── tests/
│   ├── conftest.py
│   ├── test_readonly_tools.py
│   ├── test_mutating_tools_dry_run.py
│   ├── test_mutating_tools_write_guard.py     # critical safety test
│   ├── test_resources.py
│   ├── test_prompts.py
│   ├── test_audit_log_integrity.py
│   ├── test_protocol_compliance.py             # MCP SDK harness
│   └── integration/
│       └── test_against_live_phase3.py
├── docker/
│   ├── Dockerfile
│   └── entrypoint.sh
├── helm/
│   └── streaming-rag-mcp/
│       ├── Chart.yaml
│       ├── values.yaml
│       └── templates/
│           ├── deployment.yaml
│           ├── service.yaml
│           ├── serviceaccount.yaml
│           ├── ingress.yaml
│           └── networkpolicy.yaml
├── examples/
│   ├── claude-code-config.json     # ready-to-use Claude Code wiring
│   ├── cursor-config.json
│   └── curl-smoke-test.sh
├── .github/
│   └── workflows/
│       ├── ci.yml
│       ├── docker-build.yml
│       └── helm-lint.yml
├── Dockerfile
├── docker-compose.yml              # local dev: server + phase-3 stack pointer
├── Makefile
├── pyproject.toml
└── .pre-commit-config.yaml
```

### The Makefile surface

```
make help               # list targets
make dev                # run server in stdio mode for local Claude Code
make serve              # run server in Streamable HTTP mode (production shape)
make test               # unit + integration tests
make test-safety        # only the write-guard tests
make audit-tail         # tail the audit log
make claude-wire        # print Claude Code config snippet
make docker-build       # multi-arch docker build
make helm-lint          # lint Helm chart
make helm-template      # render templates for review
make e2e                # full end-to-end against live phase-3
```

### The five craft writeups for `docs/`

These mark the platform-engineer identity in the same way Phase 3's craft writeups marked the streaming-veteran identity.

#### `docs/tool-surface.md`

Full enumerated catalog of every tool, resource, and prompt with: input schema, output schema, safety class, example invocation, example response. A hiring committee or a fellow MCP author can read this once and understand the entire server.

#### `docs/security-model.md`

The dry-run-first + env-var-gate design. State the three layers:

1. Server-level gate: `STREAMING_RAG_MCP_ALLOW_WRITES=true` required for any mutation.
2. Call-level gate: every mutating tool defaults `dry_run=True`. Caller must pass `dry_run=False` explicitly.
3. Audit-level enforcement: every mutating call writes an append-only audit record before execution.

Failure scenarios walked through:

- Agent prompt-injected into calling a mutating tool with `dry_run=False`
- Operator forgot to set `STREAMING_RAG_MCP_ALLOW_WRITES=false` on staging
- Audit log unavailable mid-call (tool refuses to execute)

Cite the dossier's failure cases (Amazon March 2026, IaC drift-reversal) as the design justification. This is where you prove you've read the postmortems.

#### `docs/permissions-and-scopes.md`

OAuth scope design. Suggested scope taxonomy:

- `streaming-rag:read` — all read-only tools and resources
- `streaming-rag:eval` — eval runs (read-only effect, but rate-limited)
- `streaming-rag:tenant:read`
- `streaming-rag:tenant:write` — tenant_create, tenant_quota_set
- `streaming-rag:ops:read` — DLQ inspect, consumer lag
- `streaming-rag:ops:write` — DLQ drain, replay, reembed (the dangerous ones)

API-key model maps API keys to scope sets. Pre-shared keys for local dev; OAuth for production.

#### `docs/observability.md`

Every tool call emits an OTel span with attributes: `mcp.tool.name`, `mcp.tool.dry_run`, `mcp.tool.principal`, `mcp.tool.arg_hash`, `mcp.tool.result_hash`. Spans export to Tempo for general tracing and to Langfuse for agent-conversation-correlated tracing. Audit log is append-only JSON, one record per mutating call, separately persisted to disk. The two paths are independent so an OTel outage doesn't compromise the audit chain.

#### `docs/operator-of-operators.md`

The design narrative. Single document explaining:

- The Komodor Klaudia + SUSE Liz reference designs from KubeCon EU 2026
- How `streaming-rag-mcp` is one of many specialized servers that compose into an "AI SRE coordinator" pattern
- Where this server's boundary lies (it operates Phase 3, not arbitrary services)
- How another team could write a similar server for their platform — i.e., this repo is also a teaching artifact

### Security: the load-bearing tests

`tests/test_mutating_tools_write_guard.py` is the test that proves the safety design works. Every mutating tool must satisfy four properties verified by property tests:

1. **Default dry-run.** Calling without explicit `dry_run=False` returns the planned action without executing.
2. **Env-var gate.** Calling with `dry_run=False` but `STREAMING_RAG_MCP_ALLOW_WRITES=false` raises a `WriteGuardError`.
3. **Audit record precedes execution.** Mutating execution path requires audit log write to succeed first.
4. **Idempotent dry-run.** Repeated dry-run calls return identical planned-action descriptions.

Run this test in CI on every PR. The README links to this test as the safety-design proof.

### The README that closes the loop

Same calling-card discipline as Phase 3. Opening 200 words written *last*, after the demo works end-to-end. Template:

> `streaming-rag-mcp` is the agent-operable control plane for the [streaming-RAG-2026](#) platform. It exposes 16 tools, 8 resources, and 4 templated prompts over the MCP protocol. Mutating operations default to dry-run mode and require an explicit server-side allow-writes flag; every mutation is recorded to an append-only audit log before execution. The full tool surface is documented in [`docs/tool-surface.md`](#); the security model in [`docs/security-model.md`](#).
>
> Built as the second half of a 2026 LLM-DevOps pivot by a 15-year streaming-platform veteran. The first half is the platform itself ([streaming-rag-2026](#)); this repo is the operator-of-operators interface on top, following the design pattern Komodor and SUSE shipped at KubeCon EU 2026. Read [`docs/operator-of-operators.md`](#) for the design narrative.

### Demo artifact (the GIF that sells)

Day 82 deliverable: a 60-second screen recording showing:

1. Open Claude Code with `streaming-rag-mcp` configured
2. Prompt: "What's the freshness lag right now and is anything wrong with the pipeline?"
3. Agent calls `pipeline_status` + `freshness_lag` + `consumer_lag` in parallel; reports back
4. Prompt: "There are messages in the DLQ — what's poisoning them?"
5. Agent calls `dlq_inspect`; shows poison-reason classification
6. Prompt: "Drain them, but show me what you'd drain first."
7. Agent calls `dlq_drain(dry_run=True)`; returns the planned action; pauses
8. Operator approves; agent calls with `dry_run=False`; audit log entry visible in a separate terminal pane

This 60-second loop is the single most shareable artifact for LinkedIn / Twitter / Medium / KubeCon demo reel.

### Cost shape

| Item | Daily cost |
|---|---|
| Phase 3 cluster (already up from prior phase) | $0 marginal |
| MCP server compute (laptop or t3.small) | ~$1 |
| LLM inference for demo runs | ~$2-5 |
| Container registry, GitHub Actions | $0 (free tier) |
| **Total over 14 days** | **$20-50** |

### 14-day execution schedule

Day numbers below assume Phase 6 starts on day 71 of the 90-day plan. Adjust if Phase 3 or 4 slipped.

#### Day 71 — Repo skeleton, decisions logged

- Create repo with the full directory tree
- Stub READMEs in every directory
- Commit `ARCHITECTURE.md` with the diagram and the three locked decisions (Python SDK, Streamable HTTP transport, OAuth + API-key auth)
- First commit: "Repo skeleton. Stack decisions locked in ARCHITECTURE.md."

#### Day 72 — Minimum-viable server

- Implement `src/streaming_rag_mcp/server.py` with stdio transport
- Two read-only tools live: `pipeline_status()` and `freshness_lag()`
- Wire to local Phase 3 cluster via thin client wrappers
- `make dev` launches the server; smoke test from Claude Code locally

#### Day 73 — Read-only surface complete

- All 10 read-only tools implemented
- Pydantic input/output schemas
- Unit tests for each
- `docs/tool-surface.md` first draft

#### Day 74 — Resources surface

- All 8 resources implemented
- Runbook resources read from the live Phase 3 `docs/runbooks/` directory at load time (so they stay in sync)
- Tests for resource URI parsing and content delivery

#### Day 75 — Security model and dry-run guard

- Implement `tools/_dry_run.py` decorator
- Implement `auth.py` with API-key validation
- Implement `audit.py` with append-only JSON log
- Write `docs/security-model.md`
- Write the load-bearing safety test file `tests/test_mutating_tools_write_guard.py`
- The four property tests must pass before any mutating tool ships

#### Day 76 — Mutating tools behind the guard

- All 6 mutating tools implemented behind the dry-run guard
- Tests for each in `tests/test_mutating_tools_dry_run.py`
- The `test_mutating_tools_write_guard.py` suite stays green
- Manual end-to-end on staging: `dlq_drain(dry_run=True)` returns a plan; `dlq_drain(dry_run=False)` actually drains

#### Day 77 — Live-fire test + Claude Code demo

- Wire production-shape Streamable HTTP transport
- Test against live Phase 3 cluster end-to-end
- Configure Claude Code to use the server via `examples/claude-code-config.json`
- Record the first rough demo (raw, unedited; for self-review)

#### Day 78 — Helm chart and Docker image

- `Dockerfile` multi-arch build (amd64 + arm64)
- Helm chart with values for: image tag, OAuth config, scope mapping, network policy
- `make docker-build` and `make helm-lint` both clean
- Push image to GHCR (free tier) tagged `:dev`

#### Day 79 — Audit log + OTel instrumentation

- Every tool call emits an OTel span with the documented attributes
- Spans flow to Tempo (general) and Langfuse (LLM-correlated)
- Audit log writes are atomic and survive partial writes (fsync after each record)
- Write `docs/observability.md`

#### Day 80 — Prompts

- All 4 prompts implemented
- Each prompt is exercised in the demo flow on day 82
- Test that prompts return well-formed templates with current resource URIs interpolated

#### Day 81 — Test harness completion

- `tests/test_protocol_compliance.py` using the MCP SDK testing harness
- Integration test `tests/integration/test_against_live_phase3.py` runs in CI nightly (not per-PR)
- `make test` covers everything; `make test-safety` covers only the write-guard properties
- CI green on main

#### Day 82 — README polish + the demo GIF

- README opening paragraph finalized with the actual tool/resource counts
- Record the 60-second demo (screen + voiceover or captions)
- Convert to GIF; embed in README
- Final pass on all `docs/` files
- Repo goes public

#### Day 83 — KubeCon CFP + thought-leadership piece (parallel)

Both deliverables (Part 2 and Part 3 below) get drafted today. They reuse the Phase 3 + Phase 6 artifacts as their source material.

#### Day 84 — Publish and surface

- Merge the Medium / blog post
- Submit the CFP
- Cross-post per the cross-post checklist
- Pin the repo on GitHub
- Update LinkedIn headline and pinned project

## Part 2 — The CFP

### Venue selection

KubeCon NA 2026 (November 2026) is the recommended target, but its CFP window may already have closed by day 83 depending on the actual start date of the pivot. Here is the venue menu with typical CFP windows so the deliverable is always shippable.

| Venue | Typical CFP window | When the conference runs | Track to target |
|---|---|---|---|
| **KubeCon + CloudNativeCon NA** | May–early July | November | AI Day, Data on Kubernetes Day |
| **KubeCon + CloudNativeCon EU** | October–December | March–April | AI Day, Data on Kubernetes Day |
| **Kafka Summit (London / SF)** | 3–4 months ahead | Spring + Fall | Real-Time Analytics & AI |
| **Ray Summit** | Late spring | September | Production AI Infrastructure |
| **MLOps World** | Rolling | Multiple per year | AI Platform Engineering |
| **AI Engineer Summit / World's Fair** | Rolling | Multiple per year | Infrastructure track |
| **KCD (Kubernetes Community Days) chapter events** | Rolling, often quarterly | Year-round | Wherever local; great first-talk venue |
| **PromCon / SRECon** | 4–6 months ahead | Annual + regional | AI for SRE |

**Decision rule:** submit to whichever venue's CFP is open on day 83 plus the next KubeCon. Aim for two submissions in flight at any given time.

### Talk pitch (the locked angle)

**Title:** *Streaming RAG on Kubernetes: Architecture Notes from a 15-Year Kafka Veteran's First LLM Pipeline*

**Track:** AI Day / Data on Kubernetes Day at KubeCon; Real-Time Analytics & AI at Kafka Summit.

**Format:** 25–35 minute talk (KubeCon standard).

**Abstract** (target 200 words, three paragraphs):

> Most RAG demos retrieve over a frozen snapshot. Production systems need fresh retrieval: a document published this minute should be queryable within seconds. This talk presents a working reference architecture for streaming RAG over a continuously updating corpus, built with Kafka 4.0, Confluent Flink 2.2's `ML_PREDICT` and `VECTOR_SEARCH`, Qdrant with namespace-isolated multi-tenancy, and self-hosted inference on Kubernetes.
>
> The architecture is opinionated. We will walk through the partitioning scheme that enables replay reasoning, the exactly-once delivery semantics across Kafka, Flink, and the vector store, and the publish-to-retrievable lag metric that we measured at p50 [X]s, p99 [Y]s under steady state and p99 [Z]s under a synthetic 10x announcement burst. We will demonstrate the migration story: re-embedding the entire corpus with a new model while the query path stays live.
>
> The talk also covers the operator surface — an MCP server that exposes pipeline operations as agent tool calls, with a default-deny security model designed against the failure modes documented in the 2026 production outage catalogue. Attendees will leave with a reproducible reference architecture, the measured numbers, and an honest accounting of where the design bends under pressure.

**Why this abstract will rank:**

- Specific metrics in the title-adjacent sentence
- Cites 2026 production failure context (program committees love grounding)
- Promises a reproducible reference (committees prefer talks attendees can leverage)
- The "15-year Kafka veteran's first LLM pipeline" framing is the differentiator angle — distinct from the "AI researcher discovers Kubernetes" cliché that floods CFPs

**Speaker bio** (3 sentences, write once, reuse everywhere):

> 15 years operating streaming and Kubernetes infrastructure at scale (Kafka, Flink, Pulsar; AWS / Azure / GCP on EKS / AKS / GKE). Returned to production work in 2026 after two years studying LLM systems. Currently building open-source reference architectures for streaming RAG and agent-operable platforms.

### CFP submission checklist

- Abstract under the venue's word limit
- Talk outline (5–7 bullets with rough timestamps)
- One technical detail the program committee can verify (link to the repo or a published blog)
- Speaker bio
- One past-talk reference (or "first conference talk" if not — be honest, KubeCon accepts new speakers)
- Diversity / track relevance fields filled honestly
- Submit at least 7 days before deadline (slush) and write the talk outline assuming acceptance

### If the talk is accepted

The talk artifact has already been built. The deck is a derivative of the README and the docs/ folder. The demo is the 60-second GIF expanded to 5 minutes live. Total marginal preparation cost: ~20-30 hours over the run-up to the conference, primarily on rehearsal and Q&A prep.

## Part 3 — The thought-leadership piece

### Format selection

| Format | Effort | Reach | Recommendation |
|---|---|---|---|
| **Medium long-form** | 6-10 hrs writing | Wide, evergreen | **Lead with this** |
| **dev.to cross-post** | 1 hr (canonical URL) | Different audience cluster | **Do this too** |
| **LinkedIn long-form** | 4 hrs (rewrite for the audience) | Hiring-relevant audience | **Do this third** |
| **Guest post on The New Stack / InfoQ / DevOps.com** | Pitch + 10-15 hrs once accepted | Highest credibility, slowest turnaround | Pitch but don't gate publication on acceptance |
| **HN Show HN** | 1 hr | Spiky but unreliable | Try once after Medium publishes |

### The piece itself (locked angle)

**Title:** *Streaming RAG on Kubernetes: A 15-Year Kafka Veteran's Notes on the 2026 LLM-Platform Stack*

**Outline** (target 2,500-3,500 words):

1. **Hook (200 words).** The thing that surprised me. Either: "the new LLM platform stack is mostly the same primitives I already operate" or "the freshness metric nobody benchmarks publicly is the most interesting number in production RAG." Pick one based on which line lands best when read aloud.
2. **The architecture diagram and why it looks familiar** (300 words). Kafka topic → stream processor with embedding enrichment → vector store → retrieval → reranker → generation. The streaming-pipeline shape that every Kafka veteran already knows, with three new pieces bolted on.
3. **The freshness metric** (400 words). Definition. Why it matters. The numbers we measured. The honest accounting of where the lag accumulates.
4. **The partitioning decision** (300 words). Why `primary_category` and not `arxiv_id`. The replay story. The re-partitioning runbook in two paragraphs.
5. **Exactly-once across three systems** (400 words). Kafka EOS, Flink two-phase-commit sink, Qdrant deterministic point ID. The failure scenarios I walked through and what each design choice protects against.
6. **The MCP server that operates the platform** (400 words). The operator-of-operators pattern. The default-deny security model. The 60-second demo GIF embedded inline.
7. **What I'd build next** (300 words). The honest "the next 3 things I would do if this were funded" list. This section is what hiring managers read most closely.
8. **What this is not** (200 words). The deliberately-omitted scope. Calibration matters as much as ambition.
9. **Code, docs, and CFP** (closing 150 words). Links to the two repos, the talk submission, the LinkedIn DM-me line.

### Distribution sequence (day 84)

1. Publish Medium primary
2. Cross-post to dev.to with canonical URL pointing to Medium
3. LinkedIn long-form rewrite (target audience: hiring managers and senior platform engineers — different tone than Medium)
4. MLOps Community Slack #share-your-work
5. r/dataengineering with a non-promotional framing
6. Hacker News Show HN (post timing: 8–10 AM Pacific weekday for best surface area)
7. Pitch The New Stack and InfoQ via their guest-post email aliases
8. DM the piece to 5 specific senior engineers / engineering directors at target companies (not a cold pitch; a "thought you might find this useful" share)

## Cross-cutting risks

| Risk | Mitigation |
|---|---|
| Phase 3 slipped, so the MCP server has no platform to operate | Fall back to a Kafka-ops MCP using a public test cluster; descope to read-only tools |
| MCP SDK breaking changes during the build window | Pin to a specific SDK version in `pyproject.toml`; document upgrade path in `docs/runbooks/` |
| KubeCon NA CFP already closed by day 83 | Use the venue menu in Part 2; always have two CFPs in flight |
| Medium piece lands flat | Distribution is multiplied by 7 venues; cross-post discipline carries the day |
| Demo GIF reveals a bug | Re-record after fix; do not ship with known bugs in the demo |
| Audit log fails write but tool execution proceeds | Test that codifies "audit-then-execute" ordering is in the safety suite |

## What Phase 6 intentionally omits

- A frontend for the MCP server (the agent is the UI)
- Auto-merge / auto-apply for any mutating tool (hard constraint from the failure-mode catalogue)
- Cross-platform tools (kubectl, AWS, etc.); keep scope tight to the streaming-RAG platform
- Marketing speak in the README (specific numbers + safety design carry the credibility)
- Trying to ship the MCP server *and* the CFP *and* the thought-leadership piece on the same day; Day 83 is a parallel-work day with Day 84 reserved for publish

## Closing principle

By end of day 84 the public surface looks like this:

- Two public repos that compose: `streaming-rag-2026` (the platform) and `streaming-rag-mcp` (the operator interface)
- One published Medium post + three cross-posts + two pitches in flight
- One CFP submitted (minimum) and one more in pipeline
- A 60-second demo GIF on LinkedIn and embedded in both READMEs
- A LinkedIn headline and CV top-line that reads exactly the same way as the dossier's positioning paragraph

Each artifact reinforces the others. The MCP server is unreadable without the platform repo. The platform repo is operationally incomplete without the MCP server. The CFP and the thought-leadership piece both reference both repos. The demo GIF is the single visual that ties them together.

This is the closing move of the 90-day pivot. Build to be operated, write to be read, present to be hired.
