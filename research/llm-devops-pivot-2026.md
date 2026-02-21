---
type: research
status: active
confidence: high
created: 2026-05-16
updated: 2026-05-16
target: personal-pivot-roadmap
audience: senior-devops-veteran-15y-aws-azure-gcp-k8s-streaming
tags:
  - devops-2026
  - sre-evolution
  - llm-platform-engineering
  - kubernetes-ai-workloads
  - gpu-scheduling
  - inference-serving
  - streaming-rag
  - agentic-infrastructure
  - mcp
  - llm-finops
  - career-pivot
---

# LLM-Era DevOps Pivot Dossier (mid-2026)

A returning senior's brush-up brief. Three pillars: what the cool kids are running, how AI wraps the loop, where to specialize for LLM workloads at enterprise scale. Anchor date 2026-05-16. Model names intentionally absent throughout. Three parallel deep-research threads compiled this. The pivot-delta section is the load-bearing one.

## Headline findings

1. **The accelerator scheduling primitive is finally unified.** DRA (Dynamic Resource Allocation) went GA in Kubernetes 1.34, NVIDIA donated its GPU DRA Driver upstream at KubeCon EU Amsterdam (March 2026), Google donated a TPU DRA driver in the same window. Every GPU/TPU/accelerator workload in production should now express claims via ResourceClaim. Device plugins are legacy.
2. **llm-d became the canonical k8s LLM inference platform.** Launched May 2025 by Red Hat / Google Cloud / IBM Research / CoreWeave / NVIDIA, joined CNCF Sandbox March 2026, v0.7 (May 2026) shipped predicted-latency scheduling GA and KV-cache-aware routing through the Gateway API Inference Extension (GIE), itself GA in 2026. Disaggregated prefill/decode via Mooncake/NIXL transports is the architectural shift of the last 18 months.
3. **MCP became infrastructure.** Anthropic donated MCP to the Linux Foundation in early 2026. The Agentic AI Foundation (Anthropic, Block, OpenAI as co-founders) is the governance body. There are ~10,000 active public MCP servers; HashiCorp shipped a production terraform-mcp-server, AWS Labs published an MCP suite covering Lambda, ECS, EKS, S3, EC2, RDS. Writing an MCP server is the new "I shipped a Helm chart" credibility marker.
4. **The streaming-to-RAG pipeline is the single highest-leverage pivot axis for a Kafka veteran.** Confluent shipped Flink 2.2 with native `ML_PREDICT` and `VECTOR_SEARCH` SQL functions (Dec 2025); the reference architecture is Kafka topic → Flink processor calls embedding model → vector DB sink → reranker → LLM. Stuart's existing expertise maps almost 1:1.
5. **Durable execution won as the agent platform abstraction.** Temporal raised $300M at a $5B valuation (Feb 2026) with 380% YoY revenue growth, OpenAI runs Codex on Temporal, OpenAI Agents SDK + Temporal GA integration shipped March 2026. Each agent tool call becomes an activity, agent state becomes event history, retries and HITL are primitives. Restate, Inngest, DBOS compete.
6. **Agent sprawl is the new microservices sprawl.** Datadog's State of AI Engineering 2026 names it explicitly: teams add agents faster than they add SLOs, dependency graphs become unobservable, incidents go unattributed. Token-budget governance, MCP scope minimization, and eval-as-CI are the 2026 equivalents of CPU limits, IAM least-privilege, and tests.
7. **Two AWS-related 2026 incidents reshaped the AI-in-CI conversation.** A 13-hour AWS China outage (Feb 2026) traced to an AI coding assistant making destructive environment changes; Amazon.com March 2 and March 5 outages (120k and 6.3M lost orders respectively) both attributed to AI-assisted code changes deployed without proper approval. Amazon ran a 90-day code-safety reset across 335 critical systems. The autonomous-merge pattern is now considered radioactive for non-trivial code.

## Synthesis line

The 2026 enterprise stack is k8s + GPU scheduling + distributed inference + streaming RAG + durable agent execution. A senior streaming/k8s veteran already operates the lower three quarters of that stack with the right primitives; the novel pieces are attention-math at the operator level, post-training pipelines, and the disaggregated inference model. The pivot is a vocabulary acquisition and one production-grade portfolio project away. Compensation premium is real (PwC: 56% wage premium on AI skills, up from 25% the year prior) and concentrated in roles that combine ops experience with LLM-platform expertise.

## 1. What the cool kids are running (devops/SRE frontier in 2026)

### Platform engineering and IDPs

Backstage still holds ~89% market share and 3,400+ adopters but with crippling operational pain — 56% of adopters cite upgrades as their top issue and internal adoption stalls around 10%. The "DIY Backstage is dead" narrative is now mainstream. Backstage v1.49.0 (March 2026) finally made the New Frontend System the default. Score graduated CNCF Sandbox status, with `score-k8s` and `score-compose` as reference implementations and only 50% of maintainers from Humanitec. CNCF launched the CNPE and CNPA certifications. KubeCon EU 2026 had 38 platform-engineering sessions, the largest track; operating thesis: "platform engineering is the control layer for the agentic era."

What to learn first: Score spec + score-k8s + score-compose (small surface, high leverage). Skim one Port and one Cortex case study for the post-Backstage portal shape.

### Kubernetes since 2024

Sidecar containers GA in 1.33 (April 2025) via KEP-753. **DRA GA in 1.34**, the foundational change. **VolumeAttributesClass GA in 1.34** for runtime volume tuning without PVC recreation. **In-place pod resize beta and on-by-default in 1.33**. **Gateway API replaced Ingress as the standard in 2026**, GAMMA (east-west mesh use) GA in Standard channel since 1.1.0, v1.5 in mid-2026 review. CNCF Kubernetes AI Conformance Program launched at KubeCon EU 2026 covering Training, Inference, Agentic workload classes.

Brush-up order: DRA model (ResourceClaim vs ResourceClaimTemplate, CEL device selectors), then Gateway API (HTTPRoute, GRPCRoute, GAMMA), then native sidecars.

### Service mesh and network

**Cilium has won as the default networking layer.** GKE Dataplane V2, AKS with Azure CNI Powered by Cilium, EKS Cilium-first in greenfield. **Istio Ambient mode is production-ready** in 2026 (ztunnel per node, optional waypoint proxies). **Linkerd's niche shrunk** to ops-simplicity and eBPF-averse compliance environments. **OBI (OpenTelemetry eBPF Instrumentation)** beta'd at KubeCon EU 2026, succeeds Grafana Beyla as the upstream L7 instrumentation. Stat worth carrying: 67% of production k8s clusters now run at least one eBPF observability tool.

Brush-up: eBPF mental model (kernel verifier, map types, hook points), Cilium policy CRDs and Hubble, Istio Ambient (ztunnel/waypoint split).

### CI/CD, GitOps, supply chain

Argo CD still leads by install count; both Argo CD and Flux are CNCF Graduated; **Crossplane graduated CNCF November 2025**. Progressive delivery is commodified. Dagger (Solomon Hykes) is the credible portable-pipelines play; adoption uneven. SBOMs are now mandatory for US federal procurement; EU CRA imposes equivalent obligations. Post-XZ supply chain cost trajectory: ~$80B/year by 2026. The practical attestation pattern: GitHub Artifact Attestations + Kyverno `ValidatingImagePolicy` for deploy-time enforcement. cosign + slsa-github-generator reaches SLSA L2 in an afternoon. containerd image store is now Docker's default for new installs.

Brush-up: SLSA v1.1 provenance shape, in-toto attestation envelope, Sigstore keyless flow with OIDC, Kyverno `ValidatingImagePolicy`.

### IaC and config

HashiCorp bought by IBM ($6.4B). OpenTofu under Linux Foundation. Spacelift reports roughly half their deployments are OpenTofu. **Crossplane v2 (graduated Nov 2025)** with namespaced composite resources by default, claims removed, compositions can include any k8s resource. **KRO (Kube Resource Orchestrator)** from AWS plus **TypeKro** typed TS SDK on top. **Alchemy** (Sam Goodwin) is the pure-TypeScript, ESM-native, no-DSL/YAML IaC play that is winning the typed-infra crowd. **Pulumi ESC** is the secrets/orchestration story. **CDKTF deprecated** so AWS CDK is the only "code-as-infra-on-major-cloud" with first-party momentum.

Brush-up: OpenTofu state encryption + migration story, Crossplane v2 (namespaced XRs, no claims). Skim Alchemy + Score side-by-side to grok the "typed workload, multi-target compile" pattern.

### Observability

OTel logs are stable; profiling is the next standardization frontier (OTLP-native profiles). Datadog ~33% market share, costs scale linearly with host count. Grafana LGTM is now genuinely world-class at roughly half the price. Honeycomb still owns high-cardinality distributed tracing. OpenTelemetry "neutralized instrumentation lock-in as a differentiator." The vendor choice is about query/storage/UI now, not collection.

Brush-up: OTLP logs and profiling SIG output, OTel Collector at scale (tail sampling, exporters, processors), Grafana LGTM end-to-end, one eBPF tool (Hubble or OBI) end-to-end.

### Data streaming evolution (the relevant home turf)

**Kafka 4.0 removed ZooKeeper entirely.** **"Diskless Kafka" is the new architecture** — WarpStream, AutoMQ, Aiven Diskless, Bufstream, Ursa all push storage to S3 with claimed ~85% cost reduction. **WarpStream acquired by Confluent (Sep 2024); Confluent now under IBM (March 2026 closing).** Redpanda offers Serverless on AWS atop its C++ broker. **Iceberg won the table-format war for new builds** — Databricks bought Tabular for $1B+, AWS S3 Tables ships native Iceberg, Snowflake/BigQuery/Confluent Tableflow all native. **Apache Polaris graduated TLP Feb 2026**; Nessie offers Git-like branching; Unity Catalog and Snowflake Open Catalog implement Iceberg REST spec. **Delta = Databricks ecosystem; Hudi = CDC niche; Paimon = Flink streaming-first.** Streaming compute: Flink remains the heavyweight but JVM-heavy; **RisingWave (PostgreSQL-compatible streaming DB) outperformed Flink in 22/27 Nexmark queries**; Materialize for strict-serializable streaming SQL; Arroyo (Rust, SQL) and **Bytewax (Python, on Timely Dataflow)** as lighter alternatives.

Brush-up: Iceberg REST Catalog spec + Polaris or Nessie hands-on, WarpStream or AutoMQ architecture deep-dive, RisingWave for streaming SQL, Bytewax if Python ML pipelines.

### Edge and serverless

Cloudflare Workers + Durable Objects remain the most mature edge compute platform (335+ cities, V8 isolates, stateful via DOs). fly.io "Sprites" (Firecracker microVMs with persistent ext4 + checkpoint/restore) emerged as the "phone-home VM" pattern. **Wasm Component Model + WASI 0.2 is real**: Wasmtime, Spin, wasmCloud all implement it fully. WASI 0.3 preview in Q2 2026 with `wasi:messaging` (native Kafka/NATS interfaces). Wasm density: 20x pod density vs runc reported; 42k req/s at 0.8ms p50 for wasi:http vs 38k/1.1ms for runc Go.

Brush-up: Durable Objects programming model, Wasm Component Model + WASI 0.2 (read a `.wit`), wasmCloud architecture if evaluating Wasm-native deployments.

### Security and supply chain

**Kyverno has overtaken OPA Gatekeeper as the simpler, k8s-native default.** **Cedar (AWS-originated)** is the credible Rego alternative for IAM-style policy. eBPF runtime security trio: **Tetragon (Isovalent/Cilium)** detection + enforcement, **Falco (CNCF)** detection, **Tracee (Aqua)** higher overhead but deeper kernel tracing. **SPIFFE/SPIRE became mainstream workload identity** in serious zero-trust deployments. **Confidential Containers + SPIRE integration shipped Jan 2026** (Red Hat) for TEE-attested credential release. Post-XZ (2024) and SolarWinds aftermath drove regulatory teeth via EU CRA and US EO 14028.

Brush-up: Kyverno policy language end-to-end (especially `ValidatingImagePolicy` with cosign), SPIFFE ID format and SPIRE attestation flow, one eBPF runtime tool (Tetragon).

### Top-8 brush-up priority

1. DRA in k8s 1.34
2. Gateway API + GAMMA
3. Cilium + eBPF mental model
4. OTel collector at scale + LGTM stack
5. SLSA v1.1 + Sigstore + Kyverno admission policy
6. Iceberg + REST Catalog (Polaris or Nessie)
7. Diskless Kafka architecture (WarpStream or AutoMQ)
8. Score + one IDP shape (Port or managed Backstage)

Consciously deprioritize: deep Backstage internals, sidecar-Istio tuning, ZooKeeper-era Kafka ops, vanilla Ingress controllers, KubeEdge, OPA Gatekeeper.

## 2. How AI is being leveraged inside the devops loop

### AI coding agents in CI/CD

The pattern that won is *headless coding agent triggered by a CI event, constrained to PR-output rather than direct commit*. Claude Code SDK (renamed Claude Agent SDK late 2025) is the reference implementation; Stripe deployed it across 1,370 engineers; Claude Code accounted for ~4% of all public GitHub commits in Q1 2026. **GitHub shipped Agentic Workflows in February 2026** — agents that run inside GitHub Actions, triggered by issues, PRs, and CI events. Cognition (Devin) acquired Windsurf and remains the only credible "long-running async engineer" product at scale. **The dominant pattern is: agent proposes diff → CI runs → human approves → merge.** Auto-merge for non-trivial app code is now considered radioactive after the Amazon and AWS China incidents.

Lightrun's 2026 State of AI-Powered Engineering Report: **43% of AI-generated code changes require manual debugging in production even after passing QA and staging.** Token-spend is now a first-class CI metric. The widely circulated cautionary tale: "The Agent That Burned $4,200 in 63 Hours" — unguarded retry loop in a LangGraph-orchestrated agent.

Learn first to sound 2026: Claude Agent SDK + Claude Code Action wiring, LLM-as-judge eval patterns, GitHub Agentic Workflows YAML model, per-job token-budget caps.

### AIOps and autonomous remediation

Alert correlation and noise reduction are commodified (BigPanda, Moogsoft, Dynatrace Davis routinely report 95%+ noise reduction). The interesting movement is one rung higher: **autonomous diagnostic agents that close the gap between alert and human-reads-timeline**. Datadog Bits AI SRE tested across 2,000+ customer environments, now triggering rollback/page/ticket actions from the Action Catalog. PagerDuty SRE Agent shipped diagnostic-only GA in Spring 2026; fully autonomous responder gated to H2 2026 early access. **Cleric AI explicitly limits to observe-and-recommend and is winning trust because of that posture** (Gartner Cool Vendor 2025). Resolve.ai is the most aggressive (Splunk founders, unicorn round, 80% autonomous goal) but deployments still keep humans in approval loops for non-trivial actions.

The canonical 2026 cascade case is the **Bluesky April 7 2026 outage**: internal logging service shipped 15-20k URIs in a single batch, TCP ephemeral port exhaustion starved Memcache connections, blocking syscall in the hot path turned a recoverable error into a death spiral. None of the AIOps platforms detected the causal chain in time.

Learn first: Datadog's "How we built a real-world evaluation platform for autonomous SRE agents at scale" engineering blog. Closest thing 2026 has to an actual eval methodology for SRE agents, maps directly onto LLM eval techniques.

### Observability copilots

Natural-language-to-query has matured past demo. **Honeycomb Canvas** renders multi-step investigations as interactive notebooks with agent reasoning visible per step. Charity Majors and team have been vocal that *hallucinations are not the dominant failure mode* when the agent is grounded against actual query results; the harder problem is data fidelity at scale. The expensive hallucination is *plausible-but-causally-wrong* explanations that send a sleep-deprived on-call down the wrong rabbit hole.

Learn first: OpenTelemetry GenAI semantic conventions (so copilots have grounded signal), Honeycomb Agent Timeline rendering of multi-agent traces.

### Incident response and post-mortem automation

Post-mortem draft generation is now a feature, not a product. incident.io, Rootly, FireHydrant all draft post-mortems from incident timeline + Slack threads + PRs + custom fields. **Two categories emerged**: *observability-stitched* post-mortems (Datadog, Honeycomb) pulling telemetry directly into the narrative, vs *chat-transcript* post-mortems (incident.io, Rootly, FireHydrant) summarizing what humans said. Genuine RCA — the causal "and that is why it cascaded" sentence — remains weak. Drafts are good at sequencing and naming components, bad at causation.

### IaC and config generation from prompts

**Pulumi Neo** operates across Pulumi-native and Terraform/OpenTofu/HCL workspaces. HashiCorp shipped the official **terraform-mcp-server** — production-ready MCP integration for plan/apply with state management. The production pattern: *agent generates Terraform draft → policy-as-code (OPA, Sentinel, Checkov) validates → human approves plan → apply*.

The three well-documented failure classes:
- **Hallucinated resources/arguments** — LLMs invent resource types or properties that look plausible but fail at apply.
- **IAM blast radius** — agents over-grant because that "makes it work."
- **Drift-remediation reversing security patches** — autonomous agent detects a manually-patched SG rule as drift and re-applies vulnerable Git state via `terraform apply`. *AI auto-healing reverses your human fix.* Multiple postmortems.

### Security scanning and remediation

Auto-fix is now table-stakes: GitHub Copilot Autofix, Snyk Agent Fix, Semgrep Autofix (public beta), Pixee. Pixee discloses ~76% merge rate across production customer repos for 2024-2025; nobody else publishes verified rates. Snyk's pre-screening pipeline (validated by Snyk Code engine before LLM is invoked) is the design that's winning vs pure prompt+context approaches.

### Capacity planning and cost optimization

**CAST AI** is the clearest production winner for k8s rightsizing + spot management + cluster autoscaling, consistent 50-70% cost reduction claims that LeanOps/Sealos practitioner reviews substantiate. Kubecost owns visibility-first; nOps competes on AWS-savings-plan optimization. CAST AI's "Agentic Operations for Kubernetes" is the most aggressive autonomous posture in the cost category.

### Self-healing infrastructure and MCP

**MCP changed everything in the last 12 months.** Anthropic donated MCP to the Linux Foundation in early 2026. The Agentic AI Foundation was established with Anthropic, Block, and OpenAI as co-founders. ~10,000 active public MCP servers; most are demos, but the credible production ones: AWS Labs' official MCP suite (Lambda, ECS, EKS, S3, EC2, RDS), hashicorp/terraform-mcp-server, Red Hat's Kubernetes/OpenShift MCP server, kubectl-mcp-server.

**Operator-of-operators pattern** is now standard. Komodor announced extensible multi-agent architecture at KubeCon EU 2026 — Klaudia agent becomes a coordinator that delegates to specialized sub-agents. SUSE Liz Rancher Prime added specialized observability/security/virtualization/fleet/Linux-config agents under one coordinator.

### Runbooks transformed

The shift captured in one phrase: *runbooks encode procedures, not reasoning*. Static markdown runbooks are being rewritten as *agent prompts with tool affordances*. Reported gains where teams committed: 73% MTTD reduction for novel failure modes, 89% acceptance rate on agent-proposed remediations, 41% MTTR reduction on P2/P3s. Failure mode: prompts that drift from system state silently degrade the runbook agent.

### What the SRE persona is being asked to become

The 2024 SRE was Prometheus + Grafana + Terraform + bash + a postmortem template. The 2026 SRE adds:
- An eval methodology for non-deterministic systems
- MCP server authorship
- Agent observability (distinct from app observability)
- Policy-as-code at the action layer (OPA/Sentinel applied to agent actions, not just IaC plans)
- Token-cost governance
- Agent sprawl as a first-class concern

The most reliable filter for "have you actually shipped LLM features in production": *do you have an eval story?* If you cannot describe how you'd know a new prompt or model is better than the old one for a given production task, you have not yet been forced into the conversation that matters. **For a returning senior SRE, transferable credibility is operational rigor; the gap to close is concrete eval-framework experience plus at least one MCP server you wrote yourself.**

Compensation signal: SRE median around $113K (early) to ~$175K (late), roughly flat vs 2024. AI engineering averages have risen sharply: **PwC's 2025 Global AI Jobs Barometer found a 56% wage premium on AI skills (up from 25% the prior year) across nearly a billion job ads.** Premium concentrated in roles that combine ops experience with LLM-platform expertise. The "AI Platform Engineer" / "AI SRE" titles command the highest deltas.

## 3. LLM workloads at enterprise scale (the pivot target)

### GPU cluster management on k8s

Three-layer cake: **GPU Operator** (drivers, container runtime, DCGM exporter, node lifecycle), **DRA** (the canonical accelerator-claim API since 1.34 GA), **higher-order schedulers** on top.

Higher-order scheduler selection matrix that emerged from KubeCon EU and the comparative talks:
- **KAI Scheduler** (NVIDIA, open-sourced from Run.ai acquisition April 2025, donated to CNCF Sandbox at KubeCon EU 2026) — GPU-first AI/ML clusters with topology-aware gang scheduling. Default for new pure-GPU clusters.
- **Kueue** — thin queue layer on top of the default kube-scheduler. Right answer when mixing CPU and GPU batch and you want Kubernetes-native quota/fair-share without replacing the scheduler. Community standard for batch on k8s in 2026 with first-class JobSet, LeaderWorkerSet, and Ray integration.
- **Volcano** — HPC/MPI-style clusters with Slurm-trained operators.
- **Yunikorn** — replaces the default scheduler, strongest where Spark/Flink already run on the same cluster.

Partitioning: MIG is the only hardware-isolated fractional GPU on Ampere/Hopper/Blackwell and is the production default for multi-tenant. MPS is faster but trusted-only. The 2026 pattern: MIG + time-slicing within a MIG instance for burst workloads, fractional GPU via pod annotation through KAI Scheduler for soft sharing.

Topology awareness on H200/B200/GB200 is no longer optional. NVLink/NVSwitch placement: up to 40% multi-GPU comms degradation from naive placement. On GB200 NVL72 racks, NVIDIA Mission Control + NVLink Fabric Manager exposes clique IDs that Kueue/KAI consume. **NVIDIA Grove** (early 2026) declares multi-component inference workloads (prefill pool + decode pool + router) as a single k8s CR with hierarchical gang scheduling and explicit startup order. The canonical disaggregated-serving primitive on k8s.

### Inference serving stacks

Three engines matter: **vLLM, TensorRT-LLM, SGLang**. **Hugging Face put TGI into maintenance mode December 2025** — bug fixes only — Inference Endpoints now route to vLLM by default with SGLang alternative. **NVIDIA NIM** is a packaged vLLM/TRT-LLM image with OpenAI-compatible front door deployed via the NIM Operator on KServe. Triton remains right for mixed-modality fleets (LLM + embeddings + vision + classical ML).

vLLM v1 is default since v0.8.0. Continuous batching pushes GPU utilization >80% vs 30-40% on static batching. Prefix caching now costs <1% throughput even at 0% hit rate. Speculative decoding gives ~21% throughput / ~20% latency improvement on ShareGPT-like workloads but underperforms baseline at very high concurrency.

**Disaggregated prefill/decode is the architectural shift of the last 18 months.** Mooncake (Moonshot AI's serving infra for Kimi) is the most-documented production deployment; Mooncake Transfer Engine is now in PyTorch ecosystem, integrated into vLLM v1 as a KV connector and into TensorRT-LLM. **NVIDIA NIXL** (Inference Xfer Library) is the wire-speed KV transport across RDMA/InfiniBand, RoCE/UCX, TCP fallback, NVMe-oF, S3. SGLang's EPD (Encode-Prefill-Decode) variant adds a third pool for multimodal encoders.

**Canonical k8s shape for multi-model inference in 2026: llm-d on KServe.** llm-d launched May 2025 by Red Hat/Google Cloud/IBM Research/CoreWeave/NVIDIA, joined CNCF Sandbox March 2026. v0.7 (May 2026) shipped predicted-latency scheduling GA. Demonstrates 13.9x throughput improvement with hierarchical KV offloading at 250 concurrent users vs naive GPU-only on 4×H100. **KServe** (CNCF Incubating since Nov 2025) is the InferenceService CRD; **llm-d** plugs vLLM-based disaggregated serving underneath; **Gateway API Inference Extension (GIE)** — Kubernetes SIG project, GA in 2026 — provides KV-cache-aware and request-cost-aware routing, replacing naive L7 load balancing for LLM endpoints. NVIDIA Dynamo collaborates with llm-d and ships the same primitives commercially.

Reality check: disaggregation only pays off at scale where prefill and decode load ratios diverge enough to amortize KV transfer cost. Below ~100 concurrent users, colocated vLLM pod still wins.

### Training and fine-tuning infrastructure

NVIDIA NeMo + Megatron-LM remain the reference for from-scratch frontier-dense training. **Megatron-FSDP** ships a DTensor-based distributed checkpoint format (`fsdp_dtensor`) that lets you save under one parallelism layout and load under a different one — the production answer to "we resharded mid-training." DeepSpeed lives but FSDP has won OSS mind-share. Composer, axolotl, JAX/Pallas on TPU round out the choices.

**RL post-training is the entire game now.** "The Death of RLHF" is the prevailing 2026 narrative — modular post-training stack: SFT → DPO/SimPO → GRPO+RLVR. Three frameworks:
- **verl** (ByteDance) — production choice at scale, HybridFlow architecture minimizes weight-transfer between rollout and training. Dec 2025 milestone: GRPO+LoRA on a 1T-param model across 64 H800.
- **OpenRLHF** — Ray + vLLM based, async RL and async agentic RL.
- **TRL (HuggingFace)** — lowest barrier, single-GPU GRPO works.

Fault tolerance: sharded distributed checkpoints (DTensor + torch.distributed.checkpoint) are the standard. AWS SageMaker HyperPod (continuous provisioning on Slurm, automatic Slurm topology mgmt) and Kubeflow Trainer with Kueue gang scheduling are the two reference cluster-management patterns. Pattern: **shard everything, checkpoint every N steps to object store, validate the checkpoint is loadable on a different parallelism shape, controller restarts the JobSet/LeaderWorkerSet on detected node failure.**

### Model lifecycle and registry

MLflow owns OSS experiment tracking + basic registry; W&B owns polished SaaS; ZenML wraps both plus LLM-specific concerns. BentoML owns OSS packaging-and-serving with Pythonic API surface above raw vLLM/Triton.

**The 2026 shift: model-as-OCI-artifact.** ORAS makes it trivial to push model weights into any OCI registry (Harbor, Artifactory, ECR, ACR, GAR) with metadata annotations. Docker itself adopted the OCI Artifact format for model packaging. Weights, tokenizer, config, model card stored as OCI manifest layers in the same registry as container images — same RBAC, signing (cosign/sigstore), vulnerability scanning, and replication. KAITO and AIKit are the k8s operators that pull model OCI artifacts at pod init.

### Vector and retrieval infrastructure

Consolidation finished. Production-grade set: **pgvector, Qdrant, Weaviate, Milvus, LanceDB**, with Pinecone (managed) and Vespa for the extreme end. Turbopuffer is the object-storage-backed cost-disruptor.

Defaults: pgvector for ~70% of agent workloads (under 10M vectors, on a DB the team already operates). Above 10M go to Qdrant/Weaviate/Milvus self-hosted or Pinecone managed. Above 1B vectors only Vespa and Milvus distributed survive.

**Hybrid retrieval is no longer optional.** Pure vector underperforms BM25 + vectors + metadata filter + reranker on almost every production workload. Reference shape: OpenSearch/Elasticsearch or Vespa for BM25 + vector hybrid, cross-encoder reranker (bge-reranker, cohere-rerank, or local) re-scoring top-k. Incremental index updates via CDC (Debezium → Kafka → sink connector). Multi-tenancy is per-namespace, `namespace == tenant_id` universal.

### Observability for LLM workloads

**OpenTelemetry GenAI semantic conventions are the standard substrate** in 2026. Datadog, New Relic, Dynatrace all natively understand the GenAI attribute set. OTel-instrumented agent code ships traces to any backend without SDK swaps. **OpenLLMetry** (Traceloop) is the fastest path to coverage — auto-instruments 20+ LLM SDKs and frameworks; Traceloop filed to donate to OTel Feb 2025, expected to become the official GenAI instrumentation layer once trademark cleanup completes.

Specialized backends: Langfuse (self-hostable OSS), Phoenix (Arize OSS), Helicone (proxy, simplest install), LangSmith (LangChain hosted), Arize (enterprise polish; $70M Feb 2025; OpenInference defines ten span kinds vs OTel's two). Picking is largely about deployment model.

Trace contents: token counts (prompt/completion/cache hit), model id, tool calls as child spans, retrieval spans with doc IDs and scores, eval scores (faithfulness/relevance/toxicity) as span attributes, cost as derived metric. The CI pattern that landed in 2026: **eval pipelines that run on PRs**, blocking merge if reference dataset quality regresses.

### Cost, capacity, FinOps

**API economics 2026.** Frontier reasoning: $15-30/1M input. Production mid-tier: ~$2-3/1M input, ~$10-15/1M output. Budget tier: $0.10-0.50/1M. The 60-300x spread between premium and budget is what makes routing economically necessary, not aesthetic.

**Self-host break-even** ~50-100M tokens/month to justify the engineering and on-call cost. Above ~10B tokens/month self-hosting wins decisively against frontier API pricing for everything except reasoning-mode workloads.

**GPU pricing arbitrage.** H100: $1.49/hr on neo-clouds (RunPod, Lambda, CoreWeave, Spheron) to $6.88/hr AWS on-demand to $12.29/hr Azure on-demand. **Hyperscalers run 3-6x neo-cloud spot price.** Spot/preemptible gives 60-75% off on-demand. Standard 2026 pattern: **steady-state inference on reserved neo-cloud capacity, burst on hyperscaler spot, training jobs entirely on spot with checkpoint/resume.**

**Capacity planning math.** Prefill is compute-bound, decode is memory-bandwidth-bound. The phases want different hardware ratios — the entire economic argument for disaggregation. KV cache per token = `2 × n_layers × n_heads × d_head × dtype_bytes`. For a 70B-class model: ~256KB/token. 4K context burns ~1GB KV per active sequence. On H100 (80GB) serving 70B FP16 (140GB weights, so 2× H100), ~20GB left for KV → about 20 concurrent 4K-context sequences before throughput collapses. PagedAttention buys 2-4x effective batch by eliminating fragmentation.

### Multi-tenancy and the LLM gateway category

The LLM gateway emerged as its own category in 2025-2026. Three serious players:
- **LiteLLM** — open-source self-hosted OpenAI-compatible proxy across 100+ providers. Hierarchical org/team/user multi-tenancy with per-tenant budgets and rate limits. No native guardrails.
- **Portkey** — SaaS-first, SDK-first developer experience. Strong on guardrails, semantic caching, prompt management.
- **Kong AI Gateway** — leverages mature Kong API mgmt; benchmarks 859% faster than LiteLLM, 228% faster than Portkey at the data plane. Heavy to operate if not already a Kong shop.

**Model routing matured into a discrete product layer.** A 7B classifier dispatching to the right tier in ~300-430ms reportedly cuts cost 30-70% (RouteLLM claims 85% cost reduction at 95% of frontier quality). The hard part is the *training data* for the router — most teams underestimate the work to build a labeled `(prompt → correct tier)` dataset for their workload.

### Data pipelines for AI — Stuart's home turf

**Streaming embeddings is now mainstream.** Confluent shipped Flink-native `ML_PREDICT` and `VECTOR_SEARCH` SQL functions in **Flink 2.2 (Dec 2025)**, letting a single Flink job enrich an event stream with embeddings or sentiment and write to the vector store. AWS shipped real-time vector embedding blueprints for MSK. Reference architecture: **Kafka topic → Flink processor calls embedding model → vector DB sink → reranker → LLM**, all event-driven. Document update lands on a Kafka topic, embedding pipeline regenerates and upserts, vector DB fresh within seconds.

**Feature stores adapted.** Feast 0.10 ships native vector search and MongoDB as online+offline store. Tecton offers managed streaming features hitting inference within seconds — fintech and e-commerce production patterns. **The new role: feature store as the serving plane for embeddings, not just numerics.**

**This is the axis where Stuart's existing skills are the moat.** Every senior LLM platform team in 2026 needs someone who can reason about partitioning, exactly-once semantics, backfill, replay, DLQ patterns. The "AI data engineer" role is essentially "Kafka/Flink veteran who learned what an embedding model is." Senior contractor pay band reported at $150-250/hr.

### Agentic infrastructure at scale

**Durable execution is the platform abstraction agents converge on.** Temporal raised $300M at $5B in February 2026 (380% YoY revenue growth, 9.1T lifetime action executions, 1.86T from AI-native customers, OpenAI runs Codex on Temporal). Restate launched commercially March 2026 (lightweight, workflow-as-code, in-process). Inngest shipped Temporal-compatible workflows February 2026. DBOS competes on the Postgres-native angle. **OpenAI Agents SDK + Temporal GA integration** (March 2026) is the canonical "make my agent loop durable" pattern: each tool call is a Temporal activity, agent state is event history, retries and HITL become primitives.

**LangGraph 1.0** (October 2025) is the agent-internal control-flow primitive — Postgres checkpointing for step-level recovery within an agent. Pattern: **Temporal for the macro lifecycle, LangGraph for the inner reasoning loop.**

Sandboxes — four serious players: **E2B** (150ms Firecracker cold start, scales to thousands of concurrent), **Daytona** (27-90ms cold start, $24M Series A Feb 2026), **Modal** (only one where the sandbox can hold a GPU), **Vercel Sandbox**.

MCP server fleets. 2026 roadmap dominated by enterprise productionization: stateless transport (Streamable HTTP in v2.1 reportedly cut latency 95%), `.well-known` capability discovery, SSO/OAuth flows, audit trails. **MCP gateways** are now a category — centralize auth, log every tool invocation, enforce policy across the agent fleet.

### Security and governance

**Prompt injection is unsolved.** OWASP LLM01. 2026 best-practice stack is layered: input guardrails (PII detection, jailbreak classifier, topic restriction), output guardrails (PII redaction, hallucination check, citation enforcement), runtime guardrails (tool authorization, sensitive-action HITL).

**EU AI Act enforcement reality.** Core obligations enforceable from **August 2, 2026**. High-risk legacy and biometric systems get to 2027. Article 12 requires *automatic* event logging integrated into core design — bolting on an audit layer afterward does not satisfy. Article 99 fines: €35M / 7% of global turnover for prohibited practices, €15M / 3% for high-risk violations. The compliance shift: **automated model cards as build-time artifacts** generated from experiment tracker + data versioner, continuous documentation-as-code, immutable audit trails.

## 4. The pivot delta (the load-bearing section)

### What Stuart already deeply owns, mapped to LLM-platform equivalents

| Already owns | Maps almost 1:1 to |
|---|---|
| Kafka partitioning, consumer groups, exactly-once | Streaming embedding ingestion, RAG pipeline backfill/replay, event-driven agent triggers |
| Flink stateful processing, watermarks, checkpoints | Real-time feature stores feeding inference, online embedding refresh, agent state machines |
| k8s scheduler internals, taints, affinities | DRA + Kueue + KAI/Volcano + Grove (same primitives, accelerator instead of CPU) |
| StatefulSets, JobSets, LeaderWorkerSet | Distributed training (Megatron, FSDP), disaggregated inference pools |
| EKS/AKS/GKE node-group autoscaling, spot pools | GPU spot strategies, neo-cloud bursting, mixed reserved+spot capacity plans |
| API gateways (Kong, Envoy, Gateway API) | LLM gateway (LiteLLM/Portkey/Kong AI), Inference Gateway Extension |
| Multi-tenant quotas and fair-share in Kafka | LLM tenant quotas, token budgets, per-tenant routing |
| OCI registries, image signing, supply chain (cosign, SLSA) | Model-as-OCI-artifact, weight signing, model provenance |
| OpenTelemetry, Prometheus, Grafana | OTel GenAI semantic conventions, Langfuse/Phoenix as OTel backends |
| Capacity planning for streaming throughput | KV cache sizing, prefill/decode capacity ratios |
| Workflow orchestrators (Airflow, Argo Workflows) | Temporal / Restate / Inngest for durable agent execution |
| CDC, Debezium, sink connectors | Vector index incremental update pipelines |
| FinOps for cloud spend | LLM FinOps (same discipline, new unit economics) |
| Disaster recovery, multi-region failover | Multi-region inference failover, KV cache replication |

### The genuinely new vocabulary to internalize

1. **Attention math at the operator level**: KV cache, paged attention, prefix caching, prefill vs decode, what a single H100 actually costs per generated token. Not derivation — napkin math: "for model X at context Y serving Z concurrent users, the math says I need N GPUs of class K."
2. **Post-training landscape**: SFT vs DPO vs GRPO vs RLVR. Which framework (verl, OpenRLHF, TRL) for which scale.
3. **Agent execution semantics**: idempotency keys for tool calls, durable replay vs re-execution, HITL as an interrupt primitive, MCP as the new system call boundary.
4. **The disaggregation mental model**: why prefill and decode want different hardware ratios, why Mooncake/NIXL exists, why Grove declares multi-component workloads as one CR.
5. **Eval as CI**: golden dataset, judge model, regression gates. Quality monitoring is harder than uptime monitoring because the signal is noisy and continuous.
6. **Model routing as a first-class architecture concern**: not just A/B test infra, but a trained classifier in the request path.

## 5. 90-day brush-up roadmap

| Weeks | Focus | Deliverable |
|---|---|---|
| 1-2 | Run vLLM on a rented H100; hand-roll OpenAI-compatible endpoint. Read Aleksa Gordić "Inside vLLM" cover-to-cover. | Working endpoint with measured prefill/decode breakdown |
| 3-4 | Stand up llm-d on GKE/EKS with two H100s. Configure GIE. Trace one request end-to-end through the inference gateway. | Single multi-model inference platform, traces in Langfuse |
| 5-6 | Build canonical streaming RAG: Kafka → Flink with `ML_PREDICT` + `VECTOR_SEARCH` → Qdrant → vLLM. | Portfolio piece. Leverages existing skills. |
| 7-8 | Wrap an agent in Temporal + LangGraph. Make it survive pod restart mid-tool-call. | Durable-execution-for-agents pattern enterprises hire for |
| 9-10 | Add LiteLLM gateway, model routing, per-tenant quotas, full OTel instrumentation to Langfuse. Wire CI eval gates. | Full production-grade reference stack |
| 11-12 | Read every llm-d, NVIDIA Dynamo, KAI Scheduler, KubeCon EU 2026 AI Day talk. Write one MCP server for a service you own and wire it to Claude Code. | Vocabulary becomes natural. MCP credibility marker shipped. |

## 6. Positioning language

The credible self-presentation is *not* "I want to learn AI." It is:

> "I have operated streaming and k8s infrastructure at scale for 15 years. The AI platform stack in 2026 is k8s + GPU scheduling + distributed inference + streaming RAG + durable agent execution. The novel pieces are KV-cache math, post-training pipelines, and disaggregation. Everything else is the same primitives I already operate."

The market reads that statement and knows where to slot him — staff/principal SRE or platform engineer on a model-serving or AI data infra team. Not junior ML engineer.

### Where to surface

- **KubeCon AI Day** talks (Amsterdam March 2026 set the canon)
- **Ray Summit**
- **MLOps Community** Slack and newsletter
- **ZenML LLMOps case-study series** (457+ as of early 2026) — best ambient-knowledge corpus on what teams actually deploy
- **NVIDIA Technical Blog**, **Red Hat Developer**
- Practitioner anchors: **Kai Waehner** (streaming + AI), **Frank Denneman** (GPU topology), **Aleksa Gordić** (inference internals), **Charity Majors / Liz Fong-Jones** (observability for agentic systems)

### Skill specialization tracks to choose from

Three sub-pivots within the LLM-DevOps category, each with different effort/payoff curves:

| Track | What it is | Best fit for Stuart? |
|---|---|---|
| **AI Data Infra** | Streaming RAG, embedding pipelines, real-time feature stores, vector index lifecycle | **Strongest** — direct lift from Kafka/Flink. Highest immediate credibility. |
| **Model Serving Platform** | k8s + GPU scheduling + llm-d + KServe + GIE + multi-tenancy | **Strong** — direct k8s lift, requires attention-math acquisition |
| **Agentic Platform** | Temporal/Restate, MCP server fleets, agent observability, sandbox infra | **Medium** — newer domain, no direct prior craft, but high pay-band growth |

All three converge in mature stacks. Picking one to lead the resume with is largely a question of which interview conversation he wants first.

## 7. Sources index

### Authoritative practitioner / engineering blogs
- Aleksa Gordić — Inside vLLM
- Datadog engineering blog — Bits AI eval platform
- Honeycomb / ZenML LLMOps lessons
- Cloudflare internal AI engineering stack
- Frontier AI substack — structure vs flexibility for agents
- Kai Waehner — streaming for agentic AI
- Frank Denneman — topology-aware multi-GPU VM placement
- Hao AI Lab — disaggregated inference 18 months later

### Conference and ecosystem coverage
- KubeCon EU Amsterdam 2026 recaps (Kubermatic, Port, Intuit Engineering, Efficiently Connected, TechTarget)
- NVIDIA at KubeCon 2026 announcement
- Red Hat Summit May 2025 — llm-d launch
- CNCF announcements (Crossplane v2 graduation, Polaris TLP, KAI Scheduler sandbox, llm-d sandbox)
- MCP Dev Summit roadmap (The New Stack)

### Vendor primary sources (treated skeptically, capability claims only)
- vLLM benchmarks, llm-d blog, Mooncake PyTorch ecosystem announcement
- NVIDIA Grove, NIXL, KAI Scheduler
- Temporal $300M raise, OpenAI Agents SDK + Temporal integration
- Honeycomb Canvas, Honeycomb agent observability launch
- Pulumi Neo, hashicorp/terraform-mcp-server
- PagerDuty Spring 2026 release, Datadog Bits AI SRE
- Anthropic MCP / Agentic AI Foundation donation
- CAST AI agentic operations, Pixee SAST 2026
- GitHub Copilot Autofix responsible-use docs, Snyk Agent Fix

### Postmortems and incident writeups
- InfraZen April 2026 — AI Broke Production recap (Amazon March outages, AWS China Feb outage, Bluesky April 7)
- The $4,200 Agent Postmortem (LangGraph retry loop)
- Autonomous IaC Drift Reverses Security Patches (InstaTunnel)
- VentureBeat — 43% AI code requires production debugging (Lightrun 2026 State of AI Engineering Report)

### Comparative tool surveys (2026)
- MarkTechPost — Best Vector Databases 2026
- CallSphere — Vector DB benchmarks
- Spheron — GPU cloud pricing comparison 2026
- CloudZero — LLM API pricing 2026, K8s cost guide 2026
- Kong — AI Gateway benchmark (LiteLLM/Portkey/Kong AI)
- Prommer, Neubird — AI SRE tool comparisons
- The New Stack — AI merges with platform engineering 2026, LLMs broke the SRE runbook, MCP enterprise roadmap
- DevOps.com — Death of the Toil
- Dev.to — Agent Sprawl is Your Next Production Incident
- LeanOps — K8s cost tools 2026

### Regulatory and compliance
- OWASP LLM Prompt Injection Prevention Cheatsheet
- Practical AI Act — model cards as build-time artifacts
- Raconteur — EU AI Act technical audit guide for 2026 deadline
- AquilaX — supply chain artifact signing SLSA
- Nirmata — GitHub Artifact Attestations + Kyverno enforcement

### Career compensation
- PwC Global AI Jobs Barometer 2025 — 56% wage premium on AI skills
- Pin — AI compensation benchmarks 2026

## Confidence and caveats

**High confidence:** the k8s 1.34 DRA GA, llm-d CNCF Sandbox status, MCP donation to Linux Foundation, Temporal raise, Confluent Flink 2.2 ML_PREDICT/VECTOR_SEARCH, Hugging Face TGI maintenance mode, NVIDIA KAI Scheduler donation, Crossplane v2 graduation, Polaris TLP graduation. All verified by primary sources cited.

**Medium confidence:** vendor-reported productivity / cost numbers (50-70% k8s cost reduction, 73% MTTD reduction, 89% acceptance) — directionally correct but vendor-favorable. PagerDuty fully-autonomous SRE Agent is gated to H2 2026 early access; production outcomes are months away. EU AI Act enforcement starts August 2, 2026; case law and enforcement priorities still developing.

**Lower confidence:** compensation deltas from talent platforms (point-in-time, self-selected sample). The exact attribution of Amazon March 2026 outages to "AI-assisted code changes deployed without approval" is from secondary reporting, not first-party RCA. The Bluesky April 7 incident is well-documented but the AIOps-failure framing is from one InfraZen recap, not multiple sources.

## Open questions for Stuart to decide

1. **Track selection.** AI Data Infra (highest leverage from existing skills) vs Model Serving Platform (more k8s-heavy) vs Agentic Platform (newest, fastest-growing). The dossier recommends AI Data Infra first; second pivot into either of the other two is straightforward once the first is in production.
2. **Self-host vs API.** The 50-100M tokens/month break-even is the practical floor for justifying a self-hosted stack on rented GPUs. Below that, the right enterprise infra job is "build the routing/governance/observability layer in front of frontier APIs." Above that, it's "build the inference platform itself."
3. **Where to surface first.** A KubeCon AI Day proposal for KubeCon NA 2026 (November), a Kafka Summit talk on streaming RAG, a Medium series on the pivot itself, or all three. The talk-circuit visibility compounds.
