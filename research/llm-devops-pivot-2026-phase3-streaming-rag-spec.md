---
type: research
status: active
confidence: high
created: 2026-05-16
updated: 2026-05-16
target: portfolio-build-spec
audience: senior-devops-veteran-15y-aws-azure-gcp-k8s-streaming
parent: llm-devops-pivot-2026-90day-roadmap.md
grandparent: llm-devops-pivot-2026.md
tags:
  - streaming-rag
  - portfolio-build
  - phase-3-spec
  - confluent-flink
  - kafka-4
  - qdrant
  - exactly-once
  - llm-devops-pivot
---

# Phase 3 Spec — The Streaming-RAG Portfolio Piece

The load-bearing artifact of the 90-day pivot. This spec is opinionated. Stuart can deviate, but every deviation should be a conscious load-bearing decision, not a convenience. The repo this produces is the single piece of work a hiring manager will read first.

The goal of this document is to let you commit clean repo scaffolding on **day 29** (the start of Phase 3 in the 90-day plan), execute focused build work through day 42, and have a publish-ready portfolio piece by end of day 42.

## What this spec optimizes for

1. **Visible craft.** Every choice in the repo should reflect Kafka/Flink fluency that a tutorial-follower would not make. Partitioning schemes, exactly-once semantics, idempotent re-embed strategies, backpressure handling, DLQ patterns — these are what mark the 15-year veteran.
2. **A defensible metric.** Publish-to-retrievable lag at p50/p99 across steady-state and 10x burst. Nobody benchmarks this publicly. Owning the number owns the conversation.
3. **A clean substitution surface.** Every interface should be swappable — embedding model, vector store, reranker, LLM. The reader should see "this person designed a platform, not a demo."
4. **Operational realism.** Day-zero migration tooling (re-embed with a new model), replay tooling (from offset N forward), DLQ inspection. The boring SRE concerns that prove this is production thinking.

## Stack choices (locked)

These are the load-bearing decisions. Reasoning provided so you can defend each in a hiring conversation.

| Layer | Choice | Reason |
|---|---|---|
| **Source corpus** | arXiv abstracts via OAI-PMH | Clean license (CC0 on metadata), daily announcement burst is a natural load shape, AI/ML audience overlap with target hiring committees, semantic richness rewards reranker design |
| **Message bus** | Kafka 4.0 (KRaft) | Removes ZK theater from the repo. Use Confluent Cloud free trial for credibility-signal, or self-hosted on a small EKS for ops-craft signal. Pick one and document the choice. |
| **Stream processor** | Flink 2.2 (Confluent Flink preferred) | The whole point of Phase 3 is `ML_PREDICT` + `VECTOR_SEARCH` SQL. Confluent's managed Flink gives you these out-of-box. Self-hosted Flink 2.2 also has them but more YAML pain. |
| **Embedding model** | Open-weights ~500M-1B embedding model on vLLM | Reuses Phase 1 infrastructure. Demonstrates self-hosted serving. Avoid hosted-API embeddings for the demo (the point is to show the streaming-to-self-hosted-inference shape). |
| **Vector store** | Qdrant (Cloud free tier or self-hosted) | Explicit namespace model maps cleanly to per-tenant isolation. Better filtering DSL than pgvector for the multi-tenant story. |
| **Reranker** | bge-reranker-v2-m3 self-hosted | Cross-encoder, small enough to run on CPU or a fraction of a single GPU. The reranker microservice is where you demonstrate latency-budget discipline. |
| **LLM endpoint** | Phase 2's llm-d if up, else Phase 1's vLLM single-node | Reuses prior work. Avoids new infrastructure cost. |
| **Observability** | OTel Collector → Langfuse (LLM spans) + Tempo (general traces) + Prometheus + Grafana | The hiring-signal stack. Langfuse owns the LLM-specific story; the rest owns the SRE story. |
| **API layer** | FastAPI (Python) or Rust (Axum) | Pick Python if you want speed-to-ship and team-typical for ML platforms. Pick Rust if you want a craft signal that lands in a specific subset of hiring committees. Default: Python. |
| **Schema registry** | Confluent Schema Registry or Apicurio | Use Avro or Protobuf for the wire. Demonstrates schema discipline. JSON is the tutorial choice. |

### Deliberately not chosen

- **Spark Structured Streaming.** The Flink momentum signal is too strong in 2026; demonstrating Spark here muddies the positioning.
- **LangChain / LlamaIndex framework layer.** Builds an opinion-stack you don't need. Compose your own retrieval/rerank/generate flow — three clean Python functions, fully traceable, easy to evolve.
- **pgvector.** Fine in production for many shops, but Qdrant's namespace model gives a cleaner multi-tenancy demo for this specific portfolio piece.
- **Hosted embedding API (Cohere, Voyage, OpenAI).** Hides the inference-platform story; you want self-hosted to demonstrate it.

## System architecture

```
                         ┌──────────────────┐
                         │   arXiv OAI-PMH  │
                         │  (source of truth)│
                         └────────┬─────────┘
                                  │ poll every 5 min
                                  ▼
                       ┌──────────────────────┐
                       │  ingest/arxiv_poller │
                       │ (Python producer)    │
                       │ idempotent by id+ver │
                       └────────┬─────────────┘
                                │ produce
                                ▼
        ┌───────────────────────────────────────────────┐
        │  topic: arxiv.papers.raw                      │
        │  partitioned by: primary_category             │
        │  retention: 7 days, EOS enabled               │
        │  schema: Avro v1 (id, version, title, abstract│
        │          authors, categories, ts_announced)   │
        └────────┬──────────────────────────────────────┘
                 │
                 ▼
   ┌─────────────────────────────────────────────────────┐
   │  Flink job: enrich                                  │
   │  SQL with ML_PREDICT(embedding_model, abstract)     │
   │  async I/O bounded queue, backpressure-safe         │
   │  idempotency key: (id, version, model_id, model_ver)│
   │  DLQ: arxiv.papers.embedding.dlq                    │
   └────────┬────────────────────────────────────────────┘
            │
            ▼
   ┌─────────────────────────────────────────────────────┐
   │  topic: arxiv.papers.enriched                       │
   │  partitioned by: primary_category                   │
   │  schema: Avro v1 (raw fields + embedding[]          │
   │          + embedding_model_id + embedding_model_ver │
   │          + ts_embedded)                             │
   └────────┬────────────────────────────────────────────┘
            │
            ▼
   ┌─────────────────────────────────────────────────────┐
   │  Flink job: sink                                    │
   │  Two-phase commit sink to Qdrant                    │
   │  point_id = hash(id, version, model_id, model_ver)  │
   │  namespace = tenant_id resolved from category map   │
   └────────┬────────────────────────────────────────────┘
            │ upsert
            ▼
   ┌─────────────────────────────────────────────────────┐
   │  Qdrant collection: papers                          │
   │  payload: { id, version, title, abstract, authors,  │
   │             categories, ts_announced, ts_embedded } │
   │  per-tenant namespace isolation                     │
   └────────┬────────────────────────────────────────────┘
            │ query
            ▼
   ┌─────────────────────────────────────────────────────┐
   │  api/server.py                                      │
   │  /query → tenant-scoped retrieval → reranker        │
   │         → LLM (llm-d / vLLM) → answer + citations   │
   │  OTel traces all the way through                    │
   └─────────────────────────────────────────────────────┘
```

## Partitioning, EOS, and the craft writeups

These are the documents in `docs/` that mark you as a streaming veteran. Each is its own README-sized markdown file. The high-level shape:

### `docs/partitioning.md`

- Topic-level partitioning by `primary_category` (cs.AI, cs.LG, math.CO, …). Justification: natural workload locality, deterministic re-partitioning, replay friendliness.
- Co-partitioning between `arxiv.papers.raw` and `arxiv.papers.enriched` so a single Flink task handles a category end-to-end.
- Key cardinality analysis: arXiv has ~150 active subject categories; for 12 partitions this gives ~12 categories per partition with manageable skew.
- Discussion of the *bad* partitioning choice (random / by-id) and why it would prevent replay reasoning.
- Re-partitioning runbook: how to grow from 12 to 24 partitions without losing exactly-once.

### `docs/exactly-once.md`

- Kafka EOS enabled producer-side (`transactional.id` strategy explained).
- Flink checkpointing with two-phase commit sink to Qdrant. Walk through the commit/abort protocol.
- Qdrant idempotent upsert via deterministic point ID: `point_id = sha256(arxiv_id || version || model_id || model_ver)[:32]`.
- Failure scenarios walked through with state diagrams:
  - producer crash mid-batch
  - Flink checkpoint failure
  - Qdrant unavailable during sink
  - downstream API consumer crash
- Property test code that demonstrates exactly-once under fault injection (chaos-style).

### `docs/multi-tenancy.md`

- Two demo tenants: `tenant_a` (all categories) and `tenant_b` (cs.* only).
- Tenant resolution at API layer via API-key → tenant_id → namespace mapping.
- Qdrant namespace per tenant; assertion that namespace boundaries are enforced (with a deliberate cross-tenant query test that proves isolation).
- Per-tenant rate limits and token budgets at the API/gateway layer.
- The fair-share scheduling argument: how this maps directly to Kafka quotas you already know.

### `docs/freshness-metric.md`

- Definition: publish-to-retrievable lag = `ts_first_queryable - ts_announced`.
- Measurement methodology: synthetic announcement watermark probe injected into the pipeline every 10 seconds.
- Reported numbers at p50/p90/p99/p99.9 for:
  - steady state (median arXiv announcement rate, ~50 papers/hour off-peak)
  - daily burst (the 14:00 UTC announcement burst, ~500 papers in 10 minutes)
  - synthetic 10x burst (HN posting velocity replay)
- Discussion of where the lag accumulates (poller interval vs Flink async I/O queue depth vs Qdrant upsert latency vs cache propagation).
- The honest section: where you cheated and why (e.g., embedding model batch size hides per-item latency).

### `docs/failure-modes.md`

- Poison messages: arXiv abstracts that the embedding model rejects.
- DLQ inspection runbook: `scripts/dlq_inspect.py`.
- Replay-from-offset: `scripts/replay_from_offset.py`.
- Re-embed-with-new-model: `scripts/reembed_with_new_model.py` — the migration story. Demonstrates that point IDs collide cleanly when the model version changes, so re-embedding doesn't break the running query path.
- Backpressure under embedding model overload: bounded queue, drop-oldest vs block-producer trade-off.
- Schema evolution: how to add a field to `arxiv.papers.enriched` without breaking running consumers.

## Repository skeleton

```
streaming-rag-2026/
├── README.md                      # the 200-word calling card (see below)
├── ARCHITECTURE.md                # the diagram + 1500-word technical narrative
├── docs/
│   ├── partitioning.md
│   ├── exactly-once.md
│   ├── multi-tenancy.md
│   ├── freshness-metric.md        # the metric nobody benchmarks publicly
│   ├── failure-modes.md
│   └── runbooks/
│       ├── replay-from-offset.md
│       ├── reembed-with-new-model.md
│       └── dlq-triage.md
├── infra/
│   ├── kafka/                     # docker-compose for local; terraform for cloud
│   │   ├── docker-compose.yml
│   │   └── README.md
│   ├── flink/
│   │   ├── docker-compose.yml
│   │   └── jobmanager.conf
│   ├── qdrant/
│   │   └── docker-compose.yml
│   └── observability/
│       ├── otel-collector.yaml
│       ├── langfuse/
│       ├── prometheus/
│       └── grafana/
│           └── dashboards/
│               └── freshness-lag.json
├── ingest/                        # source connector
│   ├── arxiv_poller.py            # OAI-PMH client → Kafka producer
│   ├── schemas/
│   │   └── arxiv_papers_raw.avsc
│   ├── tests/
│   │   ├── test_poller_idempotency.py
│   │   └── test_schema_evolution.py
│   └── README.md
├── flink-jobs/
│   ├── enrich/
│   │   ├── enrich.sql             # ML_PREDICT call
│   │   ├── model_registration.sql
│   │   └── README.md
│   ├── sink/
│   │   ├── sink_to_qdrant.sql     # VECTOR_SEARCH-compatible sink
│   │   └── README.md
│   └── tests/
│       └── test_eos_under_failure.py
├── api/                           # query path
│   ├── server.py                  # FastAPI app
│   ├── retrieval.py               # Qdrant client + namespace resolution
│   ├── reranker.py                # bge-reranker microservice client
│   ├── generate.py                # vLLM / llm-d call
│   ├── tenant.py                  # API-key → tenant_id resolution
│   ├── otel.py                    # tracing setup
│   ├── tests/
│   │   ├── test_tenant_isolation.py
│   │   └── test_full_query_path.py
│   └── README.md
├── reranker-service/              # standalone bge-reranker microservice
│   ├── server.py
│   ├── Dockerfile
│   └── README.md
├── eval/
│   ├── golden_questions.json      # 100 hand-crafted Q&A for arXiv
│   ├── freshness_bench.py
│   ├── retrieval_eval.py          # recall@k, mrr
│   ├── end_to_end_eval.py         # LLM-as-judge for final answer
│   └── README.md
├── loadtest/
│   ├── steady_state.py            # off-peak announcement rate replay
│   ├── daily_burst.py             # 14:00 UTC burst replay
│   ├── synthetic_10x.py           # HN velocity scaled to arXiv shape
│   └── README.md
├── scripts/
│   ├── replay_from_offset.py
│   ├── dlq_inspect.py
│   ├── reembed_with_new_model.py
│   ├── watermark_probe.py         # the freshness measurement probe
│   └── tenant_setup.py
├── .github/
│   └── workflows/
│       ├── ci.yml                 # lint + unit tests
│       ├── integration.yml        # full docker-compose stack on push to main
│       └── eval-gate.yml          # blocks PRs on eval regression
├── docker-compose.yml             # one-command local-dev stack
├── Makefile                       # one-command lifecycle
├── pyproject.toml
└── .pre-commit-config.yaml
```

### The Makefile surface

A reader who runs `make help` should see the platform thinking immediately.

```
make help               # list targets
make up                 # bring up full local stack
make down               # tear down
make seed               # seed arXiv historical for a date range
make poll               # start the live poller
make enrich             # start the Flink enrich job
make sink               # start the Flink sink job
make api                # start the API server
make query Q="..."      # one-shot query against the API
make probe              # emit a freshness watermark probe
make bench-steady       # run steady-state load test
make bench-burst        # run daily burst load test
make bench-10x          # run synthetic 10x burst
make eval               # run eval suite
make dlq                # inspect DLQ
make replay FROM=...    # replay from offset
make reembed MODEL=...  # re-embed with a different model
```

## The README that closes the loop

This is the single most polished writing in the entire repo. Hiring committees skim READMEs first. Treat the opening paragraph as the calling card and write it last, after the metrics are real.

### Calling-card opening (template)

> Streaming RAG over arXiv: a working reference architecture for live retrieval over a continuously updating corpus. Built to demonstrate three load-bearing patterns from the 2026 LLM-platform stack: Confluent Flink 2.2 `ML_PREDICT` and `VECTOR_SEARCH` for streaming embedding enrichment, exactly-once delivery with two-phase-commit sinks to Qdrant, and a measured publish-to-retrievable lag of **p50 [X]s / p99 [Y]s** at steady state.
>
> Built by a 15-year streaming-platform veteran (Kafka, Flink, Pulsar at scale) translating a familiar craft into the new vocabulary. The architecture decisions are documented as their own files in `docs/`. Read those first.

### README structure

1. Calling-card paragraph (above)
2. The measured numbers table (steady-state, daily burst, 10x synthetic burst)
3. Quickstart (`make up && make poll && make query Q="..."`)
4. Architecture diagram (inline ASCII or linked PNG)
5. Links into the craft writeups in `docs/`
6. Migration story: re-embed with a new model in one command
7. What is intentionally not in this repo (the omitted-by-design section)
8. Production hardening checklist (one-line items, links to issues)
9. License (MIT or Apache 2.0)
10. Author bio paragraph (links to LinkedIn, the parent dossier write-up on Medium, KubeCon CFP if accepted)

## Eval suite (the gate that proves rigor)

### Golden dataset

100 hand-crafted questions over arXiv abstracts, with reference answers and reference source paper IDs. Spread across:

- Factoid recall (50): "Who introduced PagedAttention?" — exact match on paper ID
- Synthesis (30): "What are the dominant approaches to disaggregated inference?" — set match on paper IDs
- Negative cases (10): "What does paper 1234.56789 say about X?" — answer should refuse / say not in source
- Time-sensitive (10): "What papers were announced this week on RLVR?" — tests freshness path

### Metrics

| Metric | Target | Failure mode it catches |
|---|---|---|
| Retrieval recall@10 | ≥ 0.85 | broken embedding pipeline |
| Retrieval MRR@10 | ≥ 0.50 | reranker not pulling weight |
| LLM-as-judge faithfulness | ≥ 0.90 | hallucination beyond cited sources |
| LLM-as-judge groundedness | ≥ 0.95 | citation/answer mismatch |
| Negative-case refusal | 100% | unjustified confident answer |
| Freshness-probe p99 | ≤ 30s steady, ≤ 90s burst | pipeline slowdown |

### CI gate

The GitHub Action `eval-gate.yml` runs on every PR. It executes the retrieval and freshness metrics against a fixed snapshot of the corpus and blocks merge on regression > 2% on any metric. The LLM-as-judge evals run nightly only (too expensive per-PR).

## Observability dashboard

One Grafana dashboard, `freshness-lag.json`, is the visual centerpiece of the demo. Panels:

1. **Freshness lag histogram** — p50/p90/p99/p99.9, last hour, last day
2. **Per-stage latency breakdown** — poll → produce → enrich → sink → queryable
3. **Embedding model throughput** — requests/sec, queue depth, backpressure events
4. **DLQ rate** — per source category
5. **Tenant query rate and cost** — per-tenant tokens/sec and $/hour
6. **Qdrant query latency** — p50/p99
7. **Reranker latency** — the cross-encoder is often the critical path
8. **End-to-end query latency** — TTFT and total

Screenshot this dashboard during a 10x burst. Embed in the README and the Medium post. This is the visual that sells.

## Cost shape

| Item | Provisioning | Daily cost |
|---|---|---|
| Confluent Cloud free trial | Auto, $400 credit | $0 for first ~30 days |
| Self-hosted EKS small cluster (alt) | 1× t3.large + 2× t3.medium | ~$5 |
| Qdrant Cloud free tier | Auto | $0 (within 1GB limit) |
| Embedding inference (vLLM on H100) | 1× H100 from Phase 1 (run intermittently) | $30 if up 12 hrs |
| API/reranker host | small EC2 or local | ~$2 |
| Observability | self-hosted | $0 |
| **Total over 14 days (intermittent)** | | **$200-400** |

## 14-day execution schedule

### Day 29 (Phase 3, Day 1) — repo skeleton, decisions logged

- Create the repo with the full directory tree empty
- Write the README skeleton with placeholder metric values
- Commit each `docs/*.md` file as a stub with section headers only
- Write `ARCHITECTURE.md` with the diagram (ASCII or draw.io)
- First commit message: "Repo skeleton. Stack decisions locked in ARCHITECTURE.md."

### Day 30 — Kafka up, schema registered

- Decide Confluent Cloud vs self-hosted; document in `infra/kafka/README.md`
- Create topics: `arxiv.papers.raw`, `arxiv.papers.enriched`, `arxiv.papers.embedding.dlq`
- Register Avro schemas
- Verify EOS configuration end-to-end with a synthetic producer + consumer

### Day 31 — arXiv poller online

- Implement `ingest/arxiv_poller.py` using OAI-PMH (`oai_dc` metadata format)
- Idempotent on `(id, version)` — exactly-once produce semantics
- Backfill 7 days of history; switch to live polling at 5-min intervals
- Write tests for idempotency and schema evolution

### Day 32 — Embedding model on vLLM, end-to-end smoke

- Bring up the Phase 1 vLLM endpoint with an embedding-capable model
- Hand-call the embedding endpoint from a Python script
- Sanity-check latency and throughput; note batch behavior

### Day 33 — Flink enrich job (the headline feature)

- Write `flink-jobs/enrich/enrich.sql` using `ML_PREDICT`
- Register the embedding model in Confluent Flink (or self-hosted equivalent)
- Wire DLQ for embedding failures
- Confirm async I/O bounded queue under backpressure (deliberately throttle the embedding endpoint and verify behavior)

### Day 34 — Qdrant up, sink wired

- Stand up Qdrant; create the `papers` collection with namespace isolation
- Write `flink-jobs/sink/sink_to_qdrant.sql` with VECTOR_SEARCH-compatible schema
- Verify deterministic point ID generation
- Run end-to-end: arXiv → Kafka → Flink enrich → Kafka enriched → Flink sink → Qdrant
- First measurable freshness number lands today

### Day 35 — Slack-friendly checkpoint: measure baseline freshness

- Run the watermark probe for 1 hour
- Record p50/p90/p99 freshness lag
- Commit a "Day 7" progress doc in `docs/` with current numbers
- Identify the biggest contributor to lag (probably the embedding model batch interval)

### Day 36 — API path, retrieval, reranker

- Implement `api/retrieval.py` with tenant-scoped Qdrant queries
- Stand up the reranker microservice (`reranker-service/`)
- Implement `api/generate.py` to call vLLM / llm-d
- Full query path works: `make query Q="..."` returns an answer with citations

### Day 37 — Multi-tenancy enforced

- Implement tenant resolution in `api/tenant.py`
- Write the cross-tenant isolation test in `api/tests/test_tenant_isolation.py` — must fail loudly if isolation breaks
- Demo two tenants with different category filters

### Day 38 — Observability fully wired

- OTel Collector deployed
- Langfuse self-hosted up; LLM spans flowing
- Tempo + Prometheus + Grafana up
- Build the `freshness-lag.json` dashboard
- Verify end-to-end trace from poller → answer

### Day 39 — Eval suite

- Hand-craft 100 golden questions and reference answers
- Implement `eval/retrieval_eval.py`, `eval/end_to_end_eval.py`, `eval/freshness_bench.py`
- Run baseline eval; record numbers in `eval/README.md`
- Wire `.github/workflows/eval-gate.yml`

### Day 40 — Load tests and the 10x burst

- Implement `loadtest/steady_state.py`, `loadtest/daily_burst.py`, `loadtest/synthetic_10x.py`
- Run all three; capture metrics
- Identify the breaking point — does Flink backpressure correctly? Does the embedding queue overflow? Does the DLQ fill?
- Tune one knob; re-run; document the before/after

### Day 41 — Migration story and runbooks

- Implement `scripts/reembed_with_new_model.py` — the migration story
- Demonstrate re-embedding with a different model while the query path stays live
- Write the three runbooks in `docs/runbooks/`
- Implement `scripts/replay_from_offset.py` and `scripts/dlq_inspect.py`

### Day 42 — Polish, write the Medium post, publish

- Polish the README calling-card paragraph with the actual measured numbers
- Take dashboard screenshots during a burst
- Write the Medium post (target 1,500-2,500 words) — use the structure: hook → architecture diagram → the freshness metric → the partitioning decision → the exactly-once walkthrough → the migration story → "here is what I'd build next"
- Push the repo public; merge the Medium post; share to one venue (MLOps Community Slack #share-your-work is the lowest-friction high-quality venue)

## Cross-posting checklist

Where to publish the Medium post for compounding signal:

- **Medium** (primary)
- **dev.to** (cross-post with canonical URL)
- **Confluent Community / Confluent blog guest pitch** (their Flink + vector marketing team will amplify)
- **MLOps Community Slack #share-your-work**
- **r/dataengineering** (the meta-discussion crowd reads here)
- **Hacker News Show HN** (if you have karma; if not, ask a friend)
- **LinkedIn long-form** (target a hiring-relevant audience)
- **Kafka Summit talk proposal** (uses the same artifact)

## The publish-day calling card paragraph (template, fill at end)

> I built a streaming RAG pipeline over arXiv that achieves publish-to-retrievable lag of **p50 [X]s / p99 [Y]s** at steady state, **p99 [Z]s** during the daily 14:00 UTC announcement burst, and survives a synthetic 10x burst at **p99 [W]s** without dropping messages. Stack: Kafka 4.0, Confluent Flink 2.2 with `ML_PREDICT` and `VECTOR_SEARCH`, Qdrant with namespace-isolated multi-tenancy, self-hosted embedding model on vLLM, bge-reranker, llm-d for generation, full OpenTelemetry tracing into Langfuse. Repository, architecture writeup, exactly-once semantics walkthrough, and the migration story (re-embed with a new model on a live query path) all in the repo. The why: I spent 15 years operating Kafka and Flink at scale. The 2026 LLM platform stack is the same primitives I already know, with three new pieces I had to learn: streaming inference, vector index lifecycle, and disaggregated serving. This is the working translation.

## What this spec intentionally omits

- Production hardening beyond the demo (proper TLS, SSO, secret rotation, network policies). Listed in the README "production hardening checklist" section as a credibility signal.
- A frontend. The artifact is the platform; a UI dilutes the signal.
- Comparison benchmarks against other RAG architectures. Tempting but bounds your claim to controversy you don't need.
- Custom model training or fine-tuning. Out of scope; Phase 3 is platform.
- Anything that competes for the "AI Data Infra" identity signal — keep the message clean.

## Risk register (the things that can sink the artifact)

| Risk | Likelihood | Mitigation |
|---|---|---|
| Confluent Cloud free trial expires mid-build | Low | Switch to self-hosted Kafka 4.0 in `infra/kafka/`; document the swap as a feature, not a fallback |
| Embedding model on vLLM is too slow for steady-state | Medium | Batch tuning; in worst case, use a smaller embedding model (256-dim instead of 768) — document the trade-off |
| arXiv OAI-PMH rate-limits the poller | Low | Polite poller with 5-min interval is well within limits; document the rate-limit math |
| Qdrant Cloud free tier 1GB cap | Medium | 7-day rolling retention on the vector store; document the retention policy |
| Eval LLM-as-judge inflation when judge and answerer are same family | Medium | Use a different model family for judge (if Phase 1 model is one open-weights family, judge with another); document the choice |
| Day 42 slip | Medium | Cut the synthetic 10x burst test if needed; cut nothing else. The 10x burst is the most impressive metric but the daily burst alone is sufficient |

## Closing principle

The hiring committee reads the README. The first reviewer who actually opens the repo reads the docs/ folder. The engineer who eventually wants to hire you reads the code. Each layer should pay off the layer above it.

Build to be read.
