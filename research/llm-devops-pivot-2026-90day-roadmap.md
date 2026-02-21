---
type: research
status: active
confidence: high
created: 2026-05-16
updated: 2026-05-16
target: personal-pivot-roadmap-tactical
audience: senior-devops-veteran-15y-aws-azure-gcp-k8s-streaming
parent: llm-devops-pivot-2026.md
tags:
  - 90-day-roadmap
  - llm-devops-pivot
  - curriculum
  - portfolio-build
  - kubernetes-ai-workloads
  - hands-on
---

# 90-Day Brush-Up — Tactical Drilldown

Sibling artifact to `llm-devops-pivot-2026.md`. The dossier is strategic; this is tactical. Six two-week phases, each with goal, hardware/cost shape, reading list, build, success criteria, and gotchas. Sequenced so each phase produces an artifact that compounds into the next.

## Orientation

**Underlying philosophy.** Read for vocabulary, build for mechanism, ship one public artifact per phase. The market reads commits and writing, not certificates. The 90 days end with three things that did not exist on day zero: a portfolio repo, a public reference write-up, and a KubeCon CFP draft.

**Total infrastructure budget.** Approximately $800-1,400 in cloud spend if you are disciplined about tearing down GPU instances between sessions. Hyperscaler on-demand will triple that. Neo-cloud rentals (RunPod, Lambda, CoreWeave, Spheron) are the right default; reserve hyperscaler for the llm-d phase where managed k8s saves more time than it costs.

**Time budget.** ~20-25 focused hours per week. Stuart has the senior-engineer pattern-recognition speed advantage; the curriculum assumes vocabulary acquisition is the bottleneck, not capability.

**One rule.** Build everything in public from day one. Even if it stays under a friends-only GitHub org for a while, treat every commit message and every README as if a hiring committee will read it. They will.

---

## Weeks 1-2 — Inference Mechanics and the Napkin Math

### Goal

Become fluent in inference economics. By day 14 you can answer: *given model X at context length Y serving Z concurrent users, what do I need in GPUs and what does it cost?* Without running the workload.

### Hardware and cost

- 1× rented H100 (80GB SXM or PCIe) on neo-cloud for ~10-15 cumulative hours
- Estimated spend: $20-30 total
- Provider: RunPod or Lambda for the simplest UX; CoreWeave if you want enterprise feel

### Read (in order)

1. **Aleksa Gordić — Inside vLLM** (cover-to-cover; this is the single highest-leverage piece you can read this entire 90-day period)
2. vLLM official docs — paged attention, continuous batching, prefix caching
3. The original PagedAttention paper (SOSP 2023) — 30 minutes, foundational
4. NVIDIA Developer blog — prefill vs decode bottleneck analysis
5. Mooncake architecture paper — only the abstract + section 1 + section 5 (skim the math)

### Build

- Deploy a 7B-class open-weights instruction-tuned model on vLLM v1 with OpenAI-compatible endpoint
- Hit it from a load tester (locust, vegeta, or k6) at concurrency 1, 10, 50, 100, 200 sustained
- Capture per-concurrency: time-to-first-token, tokens-per-second, GPU utilization, KV-cache footprint
- Plot the throughput curve and identify the inflection where TTFT becomes the constraint
- Toggle prefix caching on/off with a shared system prompt — measure the delta
- Toggle speculative decoding on/off — measure the delta at low and high concurrency

### Deliverable

A markdown one-pager titled "Napkin Math for Open-Weights Inference at 2026 Prices" with the throughput graph, the KV-cache formula worked through for the model you deployed, and a worked example: "to serve 1,000 concurrent users at 4K context, I need N GPUs of class K at $M/hour."

### Success criteria

- You can predict KV-cache OOM given (model_params, layers, heads, head_dim, dtype, concurrent_sequences, ctx_len) without running it
- You can explain in two sentences why prefill is compute-bound and decode is memory-bandwidth-bound
- You can describe the throughput cliff at high concurrency

### Common gotchas

- vLLM v1 changed several CLI flag names; do not trust 2024 blog posts verbatim
- HuggingFace `transformers` is *not* the right serving runtime — vLLM only
- If TTFT explodes earlier than expected, you are probably hitting `max-num-batched-tokens` not GPU FLOPs
- Some neo-cloud H100 instances ship with old CUDA drivers; check `nvidia-smi` first

---

## Weeks 3-4 — llm-d on Managed Kubernetes

### Goal

Hands-on with the canonical 2026 LLM inference platform. End the phase able to articulate the disaggregation argument from the operator's point of view, not the researcher's.

### Hardware and cost

- 2× H100 nodes on GKE or EKS (your choice; GKE is faster to provision LLM-ready clusters, EKS gives a familiar Stuart-style surface)
- Estimated spend: $300-500 if you keep the cluster up intermittently for 14 days and tear down nightly
- Alternative: GCP Vertex AI free credits if available; AWS SageMaker HyperPod trial

### Read (in order)

1. **llm-d v0.7 release notes and architecture docs** — primary source
2. **KServe v0.15 docs** — InferenceService CRD shape
3. **Gateway API Inference Extension (GIE)** Kubernetes blog — the routing semantics
4. **NVIDIA Grove** developer portal — multi-component workload as one CR
5. Hao AI Lab — "Disaggregated Inference 18 Months Later" retrospective
6. The Red Hat / Google Cloud llm-d launch post (May 2025) — for the why behind the project

### Build

- Stand up GKE with the GPU Operator and DRA Driver
- Install KServe + llm-d v0.7 + Gateway API Inference Extension
- Deploy a single model first as a sanity check via KServe `InferenceService`
- Reconfigure for disaggregated prefill/decode pools (start with 1+1 H100 split)
- Wire OTel collector to Langfuse self-hosted; trace one request end-to-end through GIE → prefill → decode
- Compare latency and throughput vs the colocated vLLM from weeks 1-2 at matched concurrency

### Deliverable

A second markdown one-pager titled "Disaggregation in Practice — When It Pays, When It Doesn't" with the latency / throughput / cost comparison vs colocated. Include the GIE config you used and the NIXL transport you ended up on (RDMA if you got it, TCP fallback if not).

### Success criteria

- You can draw the llm-d architecture from memory on a whiteboard
- You can explain why GIE routes differently from a standard L7 load balancer (KV-cache awareness, request-cost awareness)
- You can describe NIXL's role in one sentence
- You know at what concurrency disaggregation starts paying off for your model class

### Common gotchas

- GIE requires Gateway API ≥ 1.4; older clusters will silently fail
- Don't try to learn RDMA networking the same week you learn llm-d; default to TCP transport first
- llm-d's prefill scheduler will appear "stuck" until you correctly configure the predicted-latency input — this is the v0.7 GA feature, read its config schema first
- DRA ResourceClaim vs ResourceClaimTemplate: get the lifecycle right or you will leak resources

---

## Weeks 5-6 — The Streaming-RAG Portfolio Piece (your moat)

### Goal

Ship the artifact that distinguishes you in the market. This phase leverages 15 years of Kafka/Flink fluency directly. It is the deliverable a hiring manager looks at and slots you into staff/principal immediately.

### Hardware and cost

- Confluent Cloud free trial OR self-hosted Kafka 4.0 (KRaft, no ZK) on a small EKS cluster
- Flink 2.2 (Confluent Flink or open-source)
- 1-2× H100 from the weeks-1-2 setup (same neo-cloud account)
- Qdrant Cloud free tier or self-hosted; pgvector on a small RDS as alternative
- Estimated spend: $200-400

### Read (in order)

1. **Confluent blog — "Real-Time Vector Embeddings with Flink"** (the `ML_PREDICT` / `VECTOR_SEARCH` walkthrough)
2. **Flink 2.2 release announcement** (Dec 2025)
3. **Kai Waehner — "The Future of Data Streaming with Apache Flink for Agentic AI"** (Aug 2025) — best framing piece
4. Confluent + Qdrant joint case study
5. AWS — real-time vector embedding blueprint for MSK
6. Honeycomb / ZenML — "Hidden Complexities of Building Production LLM Features" (for the failure modes)

### Build

Pick a public document corpus that updates continuously. Three good candidates:

- **arXiv abstracts feed** — academic, large, daily ingest, easy to demo
- **Hacker News stories + comments** — hot/cold reads, viral spikes test backpressure
- **A subset of Wikipedia recent-changes feed** — well-known, multilingual if you want

Wire the pipeline:

1. Source events into Kafka topic
2. Flink job with `ML_PREDICT` calling an embedding model (small open-weights or hosted), enriching events with the embedding
3. Sink to vector DB (Qdrant) with `namespace == source_id` for multi-tenancy demo
4. Reranker stage (bge-reranker or cohere-rerank) on retrieval
5. Endpoint that takes a query, retrieves, reranks, calls week-3-4 vLLM/llm-d, returns answer with citations
6. **Critical**: measure publish-to-retrievable lag. This is the streaming-RAG metric that matters and that nobody benchmarks publicly.

### Deliverable

A public GitHub repo, fully documented, plus a Medium post titled something like "Streaming RAG over [Corpus]: Architecture Notes from a 15-Year Kafka Veteran's First LLM Pipeline." This single piece of content is your highest-leverage 2026 surfacing artifact.

### Success criteria

- Publish-to-retrievable lag under 10 seconds at steady state, under 30 seconds at 10x burst
- Backfill replay completes without duplicating embeddings (idempotency demonstrated)
- Multi-tenant namespace isolation provably enforced
- Repo README explains the partitioning, ordering, and exactly-once semantics in your specific Kafka/Flink terms — this is what marks you as a streaming veteran, not a tutorial-follower

### Common gotchas

- `ML_PREDICT` rate-limits will surprise you if you embed too aggressively; backpressure must be handled
- Vector DB upsert semantics differ across engines — pgvector and Qdrant handle re-embed-of-existing-doc-id differently
- Reranker latency dwarfs vector retrieval; treat reranking as the critical path
- Avoid the temptation to demo with a static corpus — the streaming-freshness story is the whole point

### Why this phase matters more than the others

Stuart's defensible position in the LLM-devops market is **AI Data Infra**. This week's artifact is the proof-of-craft. Without it, the pivot is a story; with it, the pivot is a portfolio.

---

## Weeks 7-8 — Durable Agent Execution

### Goal

Prove fluency with the agent platform abstraction that won in 2026. By day 56 you can demo an agent that survives infrastructure failure mid-tool-call and resumes correctly.

### Hardware and cost

- Temporal Cloud free tier covers this phase entirely
- Small inference spend against the week-1-2 vLLM endpoint
- Estimated spend: $30-50

### Read (in order)

1. **OpenAI Agents SDK + Temporal GA integration docs** (March 2026)
2. **LangGraph 1.0 checkpoint and human-in-the-loop docs**
3. Temporal "Durable Execution for AI" blog series
4. "The Agent That Burned $4,200 in 63 Hours" Medium postmortem — read for the anti-patterns
5. AgentMode Agent Incident Runbook — the four-phase detect/contain/rollback/postmortem playbook
6. Restate vs Temporal vs Inngest comparison (one piece; pick any reputable 2026 comparison)

### Build

A multi-step agent that performs a non-trivial task: research a topic, fetch sources, summarize, write a draft, post to a destination (Slack/Notion/local file). Tools should include at least one external API call, one LLM call, and one filesystem write.

Layer it correctly:

- **Temporal workflow** wraps the macro lifecycle
- **LangGraph** drives the inner reasoning loop with Postgres checkpointing
- Every tool call is a Temporal activity with retry policy, timeout, and **idempotency key**
- Human-in-the-loop step required before the final destination write — uses Temporal's `await_signal` primitive
- Token budget enforced per-run via a custom Temporal middleware activity that aborts the workflow if exceeded

### Deliverable

Repo + demo video. The demo includes: (a) the agent running happy path, (b) you kill the Temporal worker pod mid-tool-call and the agent resumes after worker restart, (c) the HITL interrupt with manual approval, (d) a token-budget breach correctly aborting.

### Success criteria

- Worker pod kill mid-tool-call: agent completes correctly with no duplicated side effects
- Token budget enforcement: works at granularity of single tool calls
- HITL interrupt: agent state persists across the human delay window
- All tool calls observable in Temporal UI and Langfuse traces

### Common gotchas

- Idempotency keys must be derived deterministically from workflow ID + step ID, not random UUIDs
- LangGraph's Postgres checkpointing and Temporal's event history can disagree if you mix them carelessly; treat LangGraph state as ephemeral within a Temporal activity
- The HITL signal pattern is easy to misuse — make sure the workflow can survive the human taking 72 hours to approve
- Do not test "agent durability" by force-killing your laptop; use `kubectl delete pod` against a real cluster

---

## Weeks 9-10 — Gateway, Governance, and Eval-as-CI

### Goal

Production-grade plumbing. This is where SREs separate from prompt engineers. End the phase with a layer in front of all your previous work that does routing, budgets, observability, and CI eval gates.

### Hardware and cost

- Minimal new infrastructure
- LiteLLM is OSS; Langfuse can be self-hosted or use the free cloud tier; Phoenix or Promptfoo for evals
- Estimated spend: $20-50

### Read (in order)

1. **LiteLLM proxy enterprise docs** — multi-tenancy, budgets, key management
2. **OpenTelemetry GenAI semantic conventions** (2026 latest stable + experimental drafts)
3. **Phoenix CI integration docs** OR **Promptfoo CI docs** — pick one
4. RouteLLM paper or Portkey routing docs
5. **Datadog "How we built a real-world evaluation platform for autonomous SRE agents at scale"** engineering blog — even if you don't use Datadog, this is the eval methodology
6. **Kong AI Gateway benchmark** for understanding when Kong over LiteLLM matters

### Build

- Stand up LiteLLM as the single proxy in front of everything
- Configure two tiers: a frontier-quality tier and a budget tier (use any two open-weights models with very different cost profiles)
- Implement a small classifier router — even a regex-based one or a 7B classifier — that dispatches by prompt difficulty
- Per-tenant budgets and rate limits demonstrated with two tenant API keys
- Full OTel trace export to Langfuse with cost attribution per tenant
- Build a golden eval dataset (50-100 examples from your week-5-6 RAG pipeline or week-7-8 agent)
- Wire Phoenix or Promptfoo evals into a GitHub Action that runs on PRs to your agent/rag repos, blocking merge on quality regression

### Deliverable

Updated repos with the gateway layer in place. A second public Medium post: "Building the LLM Platform Layer Your SRE Team Wishes It Had." Include the routing cost-graph and the eval-as-CI failure modes you discovered.

### Success criteria

- Cost reduction demonstrated by routing: graph the spend curve with router on vs off
- Per-tenant budget breach triggers correctly
- A deliberate prompt regression in a PR is caught by the eval gate
- One trace in Langfuse showing the full path: gateway → router decision → retrieval → reranker → llm-d inference

### Common gotchas

- LiteLLM's hierarchical budget logic has surprising edge cases — read the docs end-to-end before relying on tier limits
- OTel GenAI conventions are technically still "experimental" status; use `OTEL_SEMCONV_STABILITY_OPT_IN` for dual-emission during transition
- Eval-as-CI runs cost money every PR; cache aggressively and use small datasets for fast feedback
- LLM-as-judge bias: when the judge and the system-under-test are the same model family, scores inflate — diversify

---

## Weeks 11-12 — MCP Authorship and Ecosystem Immersion

### Goal

Ship the credibility markers that close the loop. End the 90 days with one MCP server you wrote, one CFP submitted, and one piece of public-facing thought leadership drafted.

### Hardware and cost

- Minimal — everything from prior phases is enough
- Estimated spend: $20-50

### Read (in order)

1. **MCP 2026 roadmap** (Anthropic / Linux Foundation)
2. **Anthropic MCP TypeScript SDK** docs and the **Python SDK** docs — pick the one you'll use
3. **AWS Labs MCP server suite** — read 2-3 server implementations for shape
4. **HashiCorp terraform-mcp-server repo** — gold-standard reference for an ops MCP server
5. **Komodor multi-agent architecture announcement** (KubeCon EU 2026)
6. Every llm-d, NVIDIA Dynamo, KAI Scheduler, and KubeCon EU 2026 AI Day talk you can find on YouTube — vocabulary saturation

### Build

Pick a service you already know deeply and write an MCP server for it. Strong candidates given your background:

- Your old Kafka cluster (topic introspection, consumer-lag queries, partition reassignment dry-run)
- AWS account read-only ops (cost queries, EKS cluster status, log search)
- Your homelab k8s (kubectl wrapper with safer defaults)
- The streaming-RAG pipeline from weeks 5-6 (ingest control, namespace queries, freshness probes)

Wire it to Claude Code or a local agent. Demo it doing real work. Bonus: package it as a Docker image and write a one-page README that another engineer could follow.

### Other deliverables this phase

- **KubeCon NA 2026 CFP draft** — November 2026 conference, CFP usually closes early July, so this is the right window. Topic should be your weeks-5-6 streaming-RAG portfolio piece reframed as a talk: "Streaming RAG on Kubernetes for the Kafka Veteran: Architecture Notes from a Real Production Pipeline." Aim for AI Day or the Data on Kubernetes track.
- **First public-facing thought-leadership piece** — pick one of:
  - A LinkedIn long-form post that ties the streaming-RAG repo to a hiring-relevant audience
  - A guest piece pitched to The New Stack, InfoQ, or DevOps.com on the same topic
  - A talk proposal to a regional Kafka Meetup or KCD chapter for faster turnaround

### Success criteria

- MCP server merged into a public repo with a working README
- CFP submitted to at least one venue
- One piece of public-facing content posted, with non-bot engagement

### Common gotchas

- MCP server transport: use Streamable HTTP for production-shape demos; stdio for local dev
- Tool naming and descriptions matter enormously — agents read these to decide tool calls
- Permissions scoping: do not give your MCP server admin kubeconfig; the "agent with admin kubeconfig" anti-pattern is the most common mistake
- CFP timing: KubeCon submissions get hundreds of proposals; specificity wins over breadth

---

## Beyond Day 90 — The First Real Bets

By day 91 you have:

- Six markdown one-pagers / blog posts establishing public expertise
- Three substantial GitHub repos (RAG pipeline, durable agent, MCP server)
- One CFP in the pipeline
- Working production-grade fluency in: vLLM, llm-d, Gateway API Inference Extension, Confluent Flink 2.2 ML/VECTOR_SEARCH, Temporal + LangGraph, LiteLLM, OTel GenAI, MCP

What to commit to next, in roughly this order:

1. **Pick the specialization track for your resume top-line.** AI Data Infra is the recommended lead given your background; the artifacts from weeks 5-6 make that pitch self-evident.
2. **Update the LinkedIn headline and CV.** Use the positioning language from the dossier verbatim. The market reads the headline first.
3. **Schedule three coffee chats per week for four weeks** with people from your target companies — staff engineers and engineering directors on AI platform / inference / streaming teams. Mention the streaming-RAG repo by name.
4. **Submit the CFP, write the next 2-3 pieces of content** keyed to gaps you found while building.
5. **Decide on the 6-month bet**: contractor at $200/hr taking on streaming-RAG retainers, or full-time staff at a target company. The market will reward both; the choice is lifestyle, not capability.

## What this roadmap intentionally omits

- **Frontier model training internals.** You will not retrain a 70B model in 90 days. Read enough Megatron-FSDP / verl / OpenRLHF to talk credibly. Do not try to ship a training run.
- **Custom CUDA / Triton kernels.** Below your level of leverage in 2026. The vendors (NVIDIA, vLLM, SGLang maintainers) own this surface.
- **Building your own vector DB or LLM serving engine.** Consumption-of-platform skills outvalue creation-of-platform for this pivot.
- **Generic ML engineer skills (classical models, scikit-learn, classical training loops).** The job is platform engineering for LLMs, not data science.

## Checkpoint cadence

End each two-week phase with a short personal retrospective. The pattern that works for senior engineers learning new domains: every Friday, write 200 words on the question *what did I get wrong this week that I would not have gotten wrong in my old domain?* That delta is the vocabulary acquisition rate. After 90 days, the delta should be approaching zero.

## Reference list (consolidated)

- Aleksa Gordić — Inside vLLM
- vLLM official docs (paged-attention, continuous-batching, prefix-caching)
- PagedAttention paper (SOSP 2023)
- llm-d v0.7 architecture docs + GIE Kubernetes blog
- KServe v0.15 docs
- NVIDIA Grove developer portal
- Hao AI Lab — Disaggregated Inference 18 Months Later
- Confluent Flink ML_PREDICT / VECTOR_SEARCH blog
- Flink 2.2 release notes
- Kai Waehner — Streaming for Agentic AI
- Honeycomb / ZenML — LLMOps lessons
- OpenAI Agents SDK + Temporal integration docs (March 2026)
- LangGraph 1.0 checkpoint docs
- LiteLLM proxy enterprise docs
- OpenTelemetry GenAI semantic conventions
- Phoenix CI integration docs / Promptfoo CI docs
- Datadog Bits AI SRE eval platform engineering blog
- Kong AI Gateway benchmark
- MCP 2026 roadmap
- Anthropic MCP TypeScript / Python SDK docs
- AWS Labs MCP server suite
- HashiCorp terraform-mcp-server repo
- Komodor KubeCon EU 2026 multi-agent architecture
- KubeCon EU 2026 AI Day talks (YouTube)

## Closing note

This roadmap is opinionated and prescriptive. Stuart can deviate freely — the principle is *one artifact per phase, public from day one, leveraging existing craft where possible*. The cool kids of 2026 are not necessarily smarter than the cool kids of 2024; they have just been forced into a new vocabulary on top of unchanged primitives. The pivot is not a rebuild. It is a translation.
