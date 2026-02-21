---
title: K8s-Native Inter-Agent Communication Stack (May 2026)
type: research
tags: [kubernetes, agents, messaging, service-mesh, dapr, nats, kafka, temporal, mcp, a2a, observability, gitops]
summary: Reference architecture and tool inventory for running inter-agent comm on Kubernetes in mid-2026, with migration notes from a single-machine bus and a recommended stack.
status: active
confidence: high
created: 2026-05-20
updated: 2026-05-20
---

## Executive Summary

By May 2026 the k8s-native agent stack has crystallised around a small set of opinionated layers: **Dapr Agents v1.0** (durable agent runtime, CNCF, NVIDIA-backed, KubeCon EU 2026 GA) as the application contract, **NATS JetStream or Strimzi/Redpanda** as the transport, **Temporal Worker Controller** for long-running durable execution, **Istio Ambient or Cilium Service Mesh** for sidecarless mTLS with SPIFFE workload identity, **Agent Gateway (kgateway)** for north-south A2A/MCP/LLM traffic, **KEDA** for event-driven autoscaling, and **OpenTelemetry GenAI semconv** flowing into Tempo/Loki/Prometheus. The CNCF Agentic AI Foundation (Linux Foundation, donated MCP, A2A v1.2) is now the dominant standards body; the Kagenti operator (Red Hat) and AgentRuntime/AgentCard CRDs are the most "prompts-as-resources" project shipping today. The credible k8s-minus alternative is Cloudflare Workflows GA + Durable Objects (Workflows v2 supports 50k concurrent workflows, Dynamic Workflows MIT-licensed for per-tenant code).

## Reference Architecture (mid-2026)

```
                    +----------------------------------------------+
                    |          GitOps Control Plane                |
                    |   ArgoCD / Flux  -> AgentRuntime CRDs,       |
                    |   prompt ConfigMaps, MCP server manifests,   |
                    |   KafkaTopic/KafkaUser, TemporalWorker spec  |
                    +----------------------------------------------+
                                       |
                                       v
+--------------+    +-------------------------------------------------+
| North-South  |    |              Agent Data Plane                   |
| Gateway      |--->|                                                 |
|              |    |   +-------------+   +-------------------+       |
| Agent Gw     |    |   | Dapr Agents |   | LangGraph /       |       |
| (kgateway,   |    |   | sidecar     |   | Kagenti Component |       |
|  Rust, A2A + |    |   | (pubsub,    |   | (AgentCard CRD)   |       |
|  MCP +       |    |   |  state,     |   +-------------------+       |
|  LLM)        |    |   |  workflow)  |          |                    |
|              |    |   +------+------+          v                    |
| LiteLLM /    |    |          |          +------------------+        |
| Portkey      |    |          v          | Temporal Worker  |        |
| (LLM cost,   |    |   +------+------+   | Controller       |        |
|  routing,    |    |   |   NATS JS / |   | (CRD, autoscale  |        |
|  guardrails) |    |   |   Strimzi / |<->|  via KEDA)       |        |
+------+-------+    |   |   Redpanda  |   +------------------+        |
       |            |   |   CloudEvts |          |                    |
       v            |   +------+------+          v                    |
   external         |          |          +------------------+        |
   agents, MCP      |          v          | vLLM / Ray Serve |        |
   clients          |   +------+------+   | (KubeRay, GIE)   |        |
       (A2A v1.2)   |   | Argo Events |   +--------+---------+        |
                    |   | -> Argo WF  |            |                  |
                    |   +-------------+            v                  |
                    |                       GPU node pools            |
                    |                       (Kueue + JobSet)          |
                    +--------+----------------------------------------+
                             |
                             v
        +--------------------------------------+
        |     Identity / Mesh / Policy         |
        |  SPIFFE/SPIRE -> SVIDs per agent     |
        |  Istio Ambient (ztunnel + waypoint)  |
        |   OR Cilium Mesh (eBPF, kernel mTLS) |
        |  Kyverno policy, Gateway API         |
        +--------------------------------------+
                             |
                             v
        +--------------------------------------+
        |       Observability Plane            |
        |  OTel Collector (DaemonSet+Gateway)  |
        |  GenAI semconv: invoke_agent,        |
        |   execute_tool, chat spans           |
        |  Tempo (traces), Loki (logs),        |
        |  Prometheus/Mimir (metrics)          |
        |  Grafana dashboards per agent run    |
        +--------------------------------------+
```

Four planes: control (GitOps + CRDs), data (runtime + bus + model serving), identity/mesh, observability. Everything else is glue.

## 1. K8s-Native Messaging Operators / CRDs

### NATS JetStream
- **Install:** Helm chart (`nats-io/nats`) deploys StatefulSet + nats-box. No first-party operator anymore; ArgoCD/Flux drive lifecycle. Pair with `nats-jetstream-controller` for Stream/Consumer CRDs.
- **Agent value:** dramatically simpler ops than Kafka, persistent ordered streams, request/reply primitive maps cleanly to RPC-style agent calls. Edge-friendly leaf nodes let an on-prem laptop tail a cluster-resident stream. KEDA has a first-class NATS JetStream scaler.
- **Failure mode:** JetStream needs explicit replication tuning; under-provisioned storage causes silent message loss when streams hit MaxBytes. RAFT leader election can stall pubsub for ~10s during node loss.

### Strimzi (Kafka)
- **Install:** CRD-heavy operator. `Kafka`, `KafkaTopic`, `KafkaUser`, `KafkaConnect`, `KafkaMirrorMaker2` resources. CNCF incubating. v0.50+ in 2026 supports node pools and Cruise Control rebalances.
- **Agent value:** durable log of every agent event/decision is the canonical audit substrate enterprises want. Combine with Schema Registry (Apicurio CRDs) and you get CloudEvents-typed, versioned agent topics. KEDA Kafka scaler scales consumer-side agents on lag.
- **Failure mode:** ZooKeeper-free KRaft mode is stable but cluster recovery from quorum loss is still operator-intensive. Disk pressure under bursty agent traffic causes rolling restarts that compound latency.

### Redpanda Operator
- **Install:** Redpanda Operator with `Redpanda` CRD; 2026 release introduces `NodePool` CR for heterogeneous broker groups. Kafka-API compatible.
- **Agent value:** "Agentic Data Plane" positioning, lower latency than Kafka (no JVM), single binary. Tiered storage offloads cold agent logs to S3.

### RabbitMQ Cluster Operator + Messaging Topology Operator
- **Install:** two CRDs sets: `RabbitmqCluster` for the cluster, `Queue`/`Exchange`/`Binding`/`Policy` from the topology operator.
- **Agent value:** still the best fit when you want classic AMQP semantics (work queues, RPC patterns with reply-to). Streams plugin gives you Kafka-style log topics if you need both.

### KEDA
- **Install:** Helm chart, CRDs `ScaledObject`/`ScaledJob`/`TriggerAuthentication`. CNCF graduated. 60+ scalers.
- **Agent value:** scale agent pods to zero when no events; scale up on Kafka lag, NATS pending, Temporal task queue depth, or Prometheus metric (token-rate, p95 latency). 2026 benchmarks claim 40% idle-GPU reduction. KEDA is now a hard requirement for LangGraph Platform self-hosted on k8s.

### Knative Eventing
- **Install:** Knative Operator or Helm. CNCF graduated. CRDs: `Broker`, `Trigger`, `Channel`, `Subscription`, `*Source`.
- **Agent value:** CloudEvents-native; the AI triage pattern (Red Hat's reference architecture) decomposes a multi-agent system into Broker + Triggers per agent role. New `RequestReply` resource (2026 roadmap) bridges sync MCP clients to async agent backends.

### Dapr (the favorite)
- **Install:** `dapr-helm` chart. Sidecar injected via mutating webhook. `Component` CRD per resource (pubsub broker, statestore, secret store).
- **Agent value:** **Dapr Agents v1.0 hit GA at KubeCon EU 2026** as the first CNCF-backed cloud-native agent runtime. Tool calling, memory, MCP support, agent orchestration on top of Dapr durability primitives. NVIDIA collab. 3 ms scale-to-zero activation, 30+ pluggable state stores. Failure recovery and durable execution come from Dapr Workflows rather than from the agent author. This is the lowest-friction way to get production agents on k8s today.
- **Failure mode:** sidecar memory tax (~50–150 MB/pod) matters when you have hundreds of agent pods. Component CRDs sprawl quickly.

### Numaflow (Numaproj/Intuit)
- **Install:** Numaflow operator, `Pipeline` and `MonoVertex` CRDs. Rust runtime in 2026 (~40% higher throughput).
- **Agent value:** pipeline-DAG-as-CRD for async agent stages; decouples LLM call latency so downstream stages keep moving. Steps can be any language container.

### KubeMQ / Other niche
- KubeMQ is a Helm-deployed multi-pattern broker (queue, pub/sub, RPC, events) with a `KubemqCluster` CRD; useful when you want one tool for all four patterns but the community is small.

## 2. Service Mesh for Agent Traffic

Two viable bets in mid-2026: Istio Ambient or Cilium Service Mesh. Sidecar Istio is functionally deprecated for new builds.

- **Istio Ambient Mode**: GA late 2024, mainstream by 2026. Split data plane: per-node `ztunnel` for L4 mTLS + SPIFFE identity, optional `waypoint` for L7. Memory reductions over 90%, CPU over 50% vs sidecar. **OpenShift Service Mesh 3.2 ships Ambient as default.** KubeCon EU 2026 announced beta multicluster + experimental Agent Gateway integration. The right pick when you want full L7 policy on agent traffic without sidecar tax.
- **Cilium Service Mesh**: eBPF-based, kernel-level mTLS and workload identity, no sidecar, no per-node ztunnel either. Default CNI on GKE/EKS/AKS by 2026, 5000+ production deployments. 40–60% lower latency than sidecar approaches. Best when network is already Cilium and you don't need rich L7 policy.
- **Linkerd**: still the simplest, but losing ground to Ambient/Cilium for new k8s-native agent stacks.

For inter-agent comm specifically, the mesh delivers: per-agent mTLS, SPIFFE SVIDs that survive pod restarts (matters because agents are ephemeral), retry/timeout/circuit-break without touching agent code, and policy ("only agent X may call MCP server Y"). At scale this is irreducible — without it, agent code grows its own retry and auth plumbing and rots.

## 3. Agent Runtime on K8s

### Dapr Agents
See above. The default for new k8s-native builds in mid-2026.

### Kagenti (Red Hat)
- **Install:** operator + `Component`, `AgentCard`, `AgentRuntime` CRDs. Slated for Red Hat AI H2 2026.
- **Agent value:** the cleanest "agent-as-Kubernetes-resource" model shipping. AgentCard CRDs serve as an in-cluster A2A registry. SPIFFE sidecars injected automatically. Zero-trust patterns documented at next.redhat.com.

### LangGraph Platform (now "LangSmith Deployment")
- **Install:** Helm chart `langgraph-cloud`; requires KEDA. LangGraphPlatform CRD manages deployments. Each agent becomes a Service behind an Ingress.
- **Agent value:** turn-key for LangGraph authors; GA Oct 2025. Stateful, long-running agents with checkpointing. Self-hosted lets data stay in your VPC.
- **Floor cost:** ~1 vCPU/4 GB per deployment plus Postgres and Redis; realistically $200/mo per agent service on a small EKS cluster.

### Temporal on K8s
- **Install:** Helm chart for the server; Worker Controller is a separate operator (`TemporalWorkerDeployment` CRD) that handles versioning, draining, autoscaling, HPA/PDB attachment.
- **Agent value:** durable execution where every step is checkpointed, agents survive pod crashes mid-tool-call. **3000+ paying customers as of early 2026** (The New Stack). Multi-Region Replication GA with 99.99% SLA. Nexus GA enables cross-namespace agent orchestration. Best fit for long-sleeping agents (human-in-the-loop) and "ambient agents" (Temporal's term).

### Argo Workflows + Argo Events
- **Install:** Argo operator or Helm; `Workflow`, `WorkflowTemplate`, `CronWorkflow`, `EventSource`, `Sensor` CRDs. CNCF graduated.
- **Agent value:** DAG-as-YAML for agent pipelines; cheap, well-understood, thousands of concurrent workflows on commodity clusters. Argo Events ingests 20+ source types and triggers workflows. The "Celery replacement, 11x cost reduction" pattern (CloudRaft) is becoming canonical.

### Kueue + JobSet
- **Install:** Kueue v0.17 (Kubernetes 1.29+), `ClusterQueue`/`LocalQueue`/`Workload`; JobSet for grouped jobs.
- **Agent value:** fair-share GPU quota across teams/agents, gang scheduling for multi-agent eval batches. 2026 MultiKueue priorities make this multi-cluster.

### vLLM / Ray Serve (LLM serving layer)
- **Install:** KubeRay operator + `RayService` CRD, or vLLM Helm chart. Gateway API Inference Extension v1.3.1 went GA Feb 2026 with model-aware routing and KV-cache-aware scheduling.
- **Agent value:** the layer agents *talk to*. Prefix-cache-aware routing (PrefixCacheAffinityRouter) gives 2.5x throughput on shared-prefix agent traffic. OpenAI-compatible API means agents authored against any SDK work.

### LLM Gateways
- **LiteLLM Proxy**: Helm chart (beta). Cheapest open option; OpenAI-compatible; multi-provider routing. **Warning:** March 2026 supply-chain compromise (PyPI .pth payload) — pin versions and run only signed images.
- **Portkey**: full AI control plane; observability + guardrails + governance; the right pick when compliance teams own the gateway.
- **Helicone**: acquired in 2026; strong observability but uncertain roadmap.
- **Agent Gateway (Solo.io/kgateway)**: Rust-based, A2A + MCP + LLM gateway in one. Implements Kubernetes Gateway API, integrates with Kyverno for policy. Now the leader for k8s-native agent egress.
- **Kong AI Gateway** and **Envoy AI Gateway**: viable, especially when you already run Kong or Envoy.

### Cloudflare Workflows (k8s-minus alternative)
- **Install:** none — serverless. MIT Dynamic Workflows library lets per-tenant code differ at runtime. Workflows v2 supports 50,000 concurrent workflows.
- **Agent value:** Durable Object Facets give each agent isolated SQLite. Agents Week 2026 added 20+ features. AgentWorkflow class extends Workflows with bidirectional WebSocket + RPC to Agents SDK. The right answer if you can live within Cloudflare's runtime model.

## 4. K8s-Native Event Standards

- **CloudEvents (CNCF graduated)** is the lingua franca. Every modern broker (NATS, Knative, Dapr, Kafka via headers) emits/accepts CloudEvents.
- **AsyncAPI 3.0** for schema definition of event channels; AsyncAPI tooling generates client SDKs and docs.
- **Schema Registry**:
  - **Apicurio Registry**: CNCF sandbox issue #461. Multi-format (Avro, Protobuf, JSON Schema, OpenAPI, AsyncAPI, GraphQL). Kubernetes operator. KubernetesOps storage variant uses ConfigMaps via Watch API — zero external dependencies, fully GitOps-able.
  - **Karapace**: simpler Kafka-only registry.
- **MCP (Model Context Protocol)**: donated to Agentic AI Foundation 2026; 97M installs by Mar 25. 2026 roadmap focuses on transport scalability behind load balancers — critical for k8s deployment.
- **A2A v1.2 (Linux Foundation)**: JSON-RPC 2.0 over HTTPS + streamable HTTP. Signed Agent Cards. 150+ orgs in production (Google, MSFT, AWS, Salesforce, SAP, ServiceNow).

## 5. Multi-Tenant / Multi-Cluster Patterns

- **Namespace-per-tenant**: still the default; cheap, integrates with NetworkPolicy/RBAC/Kyverno. Fine for soft multi-tenancy.
- **vCluster**: virtual clusters; "hard multi-tenancy" spectrum work landed across 2025-2026 (private nodes, auto nodes). Showcased at NVIDIA GTC 2026 for NVLinked GPU partitioning. The right answer when one tenant must not be able to see another's pods or CRDs.
- **SPIFFE/SPIRE**: workload identity. Every Kagenti pod gets a SPIFFE SVID at boot. HashiCorp's writeup (2026) frames this as table-stakes for agentic AI because agents are non-deterministic and ephemeral, classical identity doesn't fit.
- **MultiKueue**: multi-cluster job dispatch for batch agent workloads, 2026 priority.
- **Istio Ambient multicluster** (beta KubeCon EU 2026) and **Cilium Cluster Mesh** are the data-plane multi-cluster options.

## 6. Observability on K8s for Agents

- **OTel Collector**: DaemonSet (node-local) + Deployment (gateway) is the standard topology. Grafana Alloy is the unified collector now shipping.
- **GenAI semantic conventions** (OpenTelemetry SIG): client spans graduated from experimental early 2026; agent + framework spans stable in practice through Q1 2026. Top-level `invoke_agent` span, child `chat` spans per LLM call, `execute_tool` for each tool. Attributes: `gen_ai.system_instructions`, `gen_ai.input.messages`, `gen_ai.output.messages`. **Datadog, Honeycomb, New Relic** all support natively. LangChain, CrewAI, AutoGen, AG2 emit OTel-compliant spans natively or via small instrumentation packages.
- **Stack**: **Tempo** (traces), **Loki** (logs), **Prometheus/Mimir** (metrics). The Grafana LGTM stack is the canonical bundle on k8s.
- **Agent-specific dashboards**: p95 latency per agent role, token-rate, tool-call success rate, cost-per-run. Sidecar Grafana Agent batches and compresses traces, cutting egress ~40% (2026 reference).

## 7. GitOps for Agent Configs

- **ArgoCD** and **Flux** both manage CRDs cleanly in 2026; the sync-wave pattern (CRDs in wave 0, CRs in wave 1) is well-documented.
- **Prompts as CRDs**: not a standard yet. Most production teams use `ConfigMap`s with prompt templates, owned by separate Git repos, and use Kustomize overlays for environments. **Kagenti's `Component` CRD** is the closest thing to a prompt-as-resource model: agent spec, prompt, MCP tool list, identity policy all in one YAML.
- **Pinterest's MCP ecosystem** (InfoQ Apr 2026) is the highest-fidelity production example: domain-specific MCP servers behind a central registry, JWT for human-in-the-loop, mesh identity for service-to-service. Every MCP server goes through Security/Legal/Privacy/GenAI review before promotion. Prompts and tool schemas land as PRs reviewed by CODEOWNERS.

## 8. Production Deployments in the Wild

- **Pinterest** (InfoQ, Apr 2026): production-scale MCP, central registry, two-layer authz model.
- **Spotify** (The New Stack, 2026): "agentic-first development" — internal devs working through agents, not writing code directly. Built on Backstage + custom agent platform.
- **Anthropic**: MCP tunnels + self-hosted sandboxes for secure agent-to-internal-tool comm (The New Stack).
- **Intuit/Argo team**: Numaflow + Argo Workflows + Argo Events as the agentic pipeline stack.
- **Microsoft (Open Source Summit NA 2026)**: founding member of Agentic AI Foundation; Semantic Kernel + AutoGen on Azure Kubernetes Service.
- **Adobe (KubeCon EU 2026)**: "Enterprise-Scale Migrations Using Agentic Workflows with Human-in-the-loop."
- **Netflix (KubeCon EU 2026)**: "Is the Agent in the Room with Us Right Now?" — agent observability talk by Rutigliano and Halaney.
- **CoreWeave**: Kueue for AI training workload scheduling.

KubeCon NA 2025 (Atlanta, Nov 2025) declared the AI-native era; KubeCon EU 2026 (Amsterdam, Mar 23 was Agentics Day) made AI-agents-on-Kubernetes the headline track.

## 9. The K8s-Minus Alternative

- **Cloudflare Workers + Durable Objects + Workflows**: most compelling non-k8s stack. Workflows GA in 2026; v2 supports 50k concurrent; Dynamic Workflows (MIT) lets workflow code differ per tenant. Sub-cent storage per Durable Object. The right answer for solo builders and edge-first products.
- **Modal**: $87M Series B, $1.1B valuation in 2026. gVisor sandboxes, sub-1s start, GPU access. Python SDK only. Sandbox pricing ~3.75x base advertised. The default for agentic code-execution sandboxes.
- **Fly Machines**: KVM hardware-isolated VMs via REST API. **GPUs deprecated after August 2026** — CPU-only going forward. Still excellent for low-latency global agent deployments where GPUs aren't required.
- **Railway**: $20/vCPU/mo + $10/GB/mo, zero-config GitHub deploys. The "I just want to ship" tier.
- **Cloud Run**: serverless, scale-to-zero, good for bursty agent traffic. Cheaper than GKE for low-frequency workloads.
- **Nomad + Consul**: HashiCorp's k8s-minus alternative — viable, used in regulated environments where k8s is too heavy, but fading in mind-share.

The "k8s is overkill" camp is real and growing for solo builders. For enterprise the gravity is still k8s — every major AI platform vendor (Anthropic, LangChain, Dapr, Kagenti, Argo, Pinecone, Weaviate, Ray, vLLM) has a Helm chart or operator first.

## Migration: Single-Machine Bus to K8s-Resident Bus

**What stays**
- Your event schema. CloudEvents + AsyncAPI + Apicurio carries forward verbatim. The whole point of CloudEvents is that the same payload works on disk, on tmux pipe, on NATS, on Kafka.
- Agent business logic. If agents speak via pubsub/RPC primitives, swapping the transport is mechanical.
- Your tool contracts. MCP servers don't care where they run; you change the URL.

**What changes**
- **Transport.** Local SQLite/file-based bus -> NATS JetStream (closest semantic match) or Strimzi (when you want durable audit log). Local request/reply -> NATS `req-reply` or HTTP behind a service.
- **Identity.** From `pid`/process owner to **SPIFFE SVIDs** via SPIRE. Every agent gets a workload identity at boot. This is the biggest mental shift: agents are no longer "trusted because they're on my laptop"; they're trusted because they hold a cert signed by SPIRE.
- **Discovery.** From a static config file to `AgentCard` CRDs (Kagenti) or a central registry (Pinterest's pattern). A2A handles cross-cluster discovery.
- **Durability.** From "process restart loses state" to **Temporal workflows** or **Dapr Workflows**. Activities checkpoint after each tool call.
- **Scaling.** From `tmux new-window` to **KEDA ScaledObject** on queue depth. Scale-to-zero in seconds.
- **Observability.** From `tail -f` to OTel + Tempo + Loki + Prometheus. Grafana dashboards by `invoke_agent` span tree.

**What's irreducibly different**
- **Cold-start latency.** A pod takes 2-5s to start even with KEDA; tmux fork is microseconds. For sub-second agent responses, keep a warm pool (`minReplicas: 1`).
- **Network failure modes.** Local IPC never partitions. K8s pods do, frequently. Every agent call becomes a distributed call; you must adopt retries, idempotency, deadlines.
- **Cost.** A 3-node EKS cluster floors at ~$300/mo before any workload. NAT egress, control-plane fees, persistent volumes add another $100-300. The cheapest "real" k8s agent platform runs at ~$500/mo for a hobby footprint.
- **Operations.** GitOps means every change is a PR. That's the whole point, and it's a tax. Be ready.

**Recommended migration path for a Helioy-style solo build**
1. Adopt CloudEvents on the local bus first. No k8s yet.
2. Containerize agents (single Dockerfile each); run them under Docker Compose for a week.
3. Stand up a single-node k3s cluster (~$15/mo on a Hetzner CX22), deploy Dapr, point its pubsub component at local NATS-in-Helm. Now you have a real Component CRD, real sidecar pubsub.
4. Add OTel Collector + Tempo/Loki on-cluster. Wire the GenAI semconv emitters.
5. Add Temporal Worker Controller when you hit your first "agent died mid-task" pain.
6. Add SPIFFE/SPIRE + Istio Ambient when you have >5 agents and need fine-grained inter-agent authz.
7. Only at this point would you graduate to a managed EKS/GKE cluster.

## The Bet — Recommended Stack for the Next 18 Months

If you must pick one k8s-native stack today: **Dapr Agents v1.0 as the runtime, NATS JetStream as the bus, Temporal Worker Controller for durable execution, Istio Ambient for mesh and SPIFFE identity, Agent Gateway (kgateway) for A2A/MCP/LLM north-south, KEDA for autoscaling, OTel + LGTM for observability, ArgoCD for GitOps.** Dapr Agents won the CNCF-backed agent runtime slot at KubeCon EU 2026, has NVIDIA's engineering weight behind it, and abstracts the broker so you can swap NATS for Kafka without code changes. NATS is the lowest-ops broker that still gives durability via JetStream — the only reason to choose Strimzi over it is regulated audit-log requirements. Temporal's 3000-customer base, multi-region GA, and Worker Controller k8s operator make it the safest durable-execution bet. Istio Ambient eliminates the sidecar tax and ships SPIFFE identity for free. Agent Gateway is the only k8s gateway that natively speaks all three agent protocols (A2A, MCP, LLM). The OTel GenAI semconv just left experimental; the dashboard work is finally portable across vendors. This stack is boring on purpose — every component is CNCF, every component has an operator, every component has a Helm chart, and every component has prod references at companies you've heard of.

## Sources

KubeCon and CNCF:
- [CNCF — Schedule for KubeCon EU 2026](https://www.cncf.io/announcements/2025/12/10/cncf-unveils-schedule-for-kubecon-cloudnativecon-europe-2026/)
- [Kubermatic — KubeCon EU 2026 Recap: Agents, Sovereignty, Rules of the Road](https://www.kubermatic.com/blog/kubecon-eu-2026-recap/)
- [CNCF — Cloud native agentic standards](https://www.cncf.io/blog/2026/03/23/cloud-native-agentic-standards/)
- [CNCF — Nearly Doubles Certified Kubernetes AI Platforms](https://www.cncf.io/announcements/2026/03/24/cncf-nearly-doubles-certified-kubernetes-ai-platforms/)
- [CNCF — The great migration: every AI platform converging on Kubernetes](https://www.cncf.io/blog/2026/03/05/the-great-migration-why-every-ai-platform-is-converging-on-kubernetes/)
- [Harness — KubeCon NA 2025 Recap: Dawn of the AI Native Era](https://www.harness.io/blog/kubecon-2025-recap)
- [O'Reilly — KubeCon + CloudNativeCon NA 2025 Recap](https://www.oreilly.com/radar/kubecon-cloudnativecon-na-2025-recap/)

Messaging and brokers:
- [Signisys — Dapr Agents v1.0 GA at KubeCon EU 2026](https://www.signisys.com/blog/cncfs-dapr-agents-v1-0-delivers-production-reliability-for-ai-agent-frameworks/)
- [jangwook.net — Dapr Agents v1.0: How to make AI agents survive in Kubernetes](https://jangwook.net/en/blog/en/dapr-agents-v1-cncf-production-ai-framework/)
- [NATS docs — JetStream](https://docs.nats.io/nats-concepts/jetstream)
- [Strimzi — Apache Kafka on Kubernetes](https://strimzi.io/)
- [RabbitMQ Operators overview](https://www.rabbitmq.com/kubernetes/operator/operator-overview)
- [Redpanda Self-Managed Operator release notes](https://docs.redpanda.com/current/get-started/release-notes/operator/)
- [Knative — Building a Resilient AI Triage System with Event-Driven Agents](https://knative.dev/blog/articles/knative-eventing-eda-agents/)
- [Numaflow](https://numaflow.numaproj.io/)
- [TNS — Intuit's Numaflow](https://thenewstack.io/intuits-numaflow-abstracts-away-infrastructure-for-ml-engineers/)

Service mesh and identity:
- [Tigera — Sidecarless mTLS: Istio Ambient and ztunnel](https://www.tigera.io/blog/sidecarless-mtls-in-kubernetes-how-istio-ambient-mesh-and-ztunnel-enable-zero-trust/)
- [Cloud Native Now — Service Mesh Comeback in 2026](https://cloudnativenow.com/contributed-content/why-service-mesh-is-poised-for-a-dramatic-comeback-in-2026/)
- [Red Hat — OpenShift Service Mesh 3.2 with Istio Ambient](https://www.redhat.com/en/blog/introducing-openshift-service-mesh-32-istios-ambient-mode)
- [InfoQ — Istio Evolves for the AI Era](https://www.infoq.com/news/2026/04/istio-ai-multicluster/)
- [algeriatech — Service Mesh 2026: Cilium Wins](https://algeriatech.news/service-mesh-cilium-consolidation-2026/)
- [HashiCorp — SPIFFE: Securing the identity of agentic AI](https://www.hashicorp.com/en/blog/spiffe-securing-the-identity-of-agentic-ai-and-non-human-actors)
- [vCluster — Multi-tenancy for AI infrastructure](https://www.vcluster.com/)

Agent runtimes and orchestration:
- [Red Hat — How Kagenti ADK simplifies production AI agent management](https://developers.redhat.com/articles/2026/05/04/how-kagenti-adk-simplifies-production-ai-agent-management)
- [Red Hat — Zero trust AI agents on Kubernetes (Kagenti)](https://next.redhat.com/2026/03/05/zero-trust-ai-agents-on-kubernetes-what-i-learned-deploying-multi-agent-systems-on-kagenti/)
- [Red Hat — Who's really calling? Securing agent-to-agent communication](https://next.redhat.com/2026/05/13/securing-agent-to-agent-communication/)
- [Temporal — Orchestrating ambient agents](https://temporal.io/blog/orchestrating-ambient-agents-with-temporal)
- [Temporal — Worker Controller Autoscaling](https://temporal.io/blog/safe-versioned-worker-deployments-on-kubernetes-now-with-autoscaling)
- [TNS — Temporal hits 3,000 paying customers](https://thenewstack.io/temporal-durable-execution-ai-workflows/)
- [LangChain — LangGraph Platform GA](https://www.langchain.com/blog/langgraph-platform-ga)
- [LangChain Helm charts](https://github.com/langchain-ai/helm/blob/main/charts/langgraph-cloud/README.md)
- [Argo Workflows](https://argoproj.github.io/workflows/)
- [Fast.io — Argo Workflows for AI Agents](https://fast.io/resources/argo-workflows-ai-agents/)
- [Kueue overview](https://kueue.sigs.k8s.io/docs/overview/)
- [Red Hat — Kueue 1.3](https://developers.redhat.com/articles/2026/04/16/red-hat-build-kueue-1-3-batch-workload-kubernetes)

LLM serving and gateways:
- [premai — Deploying LLMs on Kubernetes: vLLM, Ray Serve, GPU Scheduling 2026](https://blog.premai.io/deploying-llms-on-kubernetes-vllm-ray-serve-gpu-scheduling-guide-2026/)
- [Ray docs — RayServe LLM on Kubernetes](https://docs.ray.io/en/latest/cluster/kubernetes/examples/rayserve-llm-example.html)
- [Solo.io — Agent Gateway overhaul (A2A, MCP, K8s Gateway API)](https://www.solo.io/blog/updated-a2a-and-mcp-gateway)
- [Solo.io — Agentgateway](https://www.solo.io/products/agentgateway)
- [CNCF — kgateway project spotlight](https://www.cncf.io/blog/2025/07/23/project-spotlight-kgateway/)
- [dev.to — LLM proxy landscape 2026 (LiteLLM compromise, Helicone acquired)](https://dev.to/stockyarddev/the-llm-proxy-landscape-in-2026-helicone-acquired-litellm-compromised-and-whats-next-3oon)
- [Spheron — AI Gateway Setup 2026: LiteLLM, Portkey, Kong](https://www.spheron.network/blog/ai-gateway-litellm-portkey-kong-gpu-cloud/)
- [MarkTechPost — LiteLLM Agent Platform on Kubernetes](https://www.marktechpost.com/2026/05/16/meet-litellm-agent-platform-a-kubernetes-based-self-hosted-infrastructure-layer-for-isolated-agent-sandboxes-and-persistent-session-management-in-production/)

Observability:
- [OpenTelemetry — Semantic conventions for GenAI systems](https://opentelemetry.io/docs/specs/semconv/gen-ai/)
- [OpenTelemetry — Inside the LLM Call: GenAI Observability](https://opentelemetry.io/blog/2026/genai-observability/)
- [Datadog — Native OTel GenAI Semconv support](https://www.datadoghq.com/blog/llm-otel-semantic-convention/)
- [Markaicode — Agent Architecture with Grafana 2026](https://markaicode.com/architecture/agent-architecture-with-grafana/)

Production deployments:
- [InfoQ — Pinterest Deploys Production-Scale MCP Ecosystem](https://www.infoq.com/news/2026/04/pinterest-mcp-ecosystem/)
- [TNS — Spotify's agentic-first development](https://thenewstack.io/dogfooding-and-platforms-spotifys-agentic-first-development/)
- [TNS — Anthropic MCP Tunnels and Sandboxes](https://thenewstack.io/anthropic-mcp-tunnels-sandboxes/)
- [Microsoft Open Source Blog — Agentic systems at OSS Summit NA 2026](https://opensource.microsoft.com/blog/2026/05/18/from-open-source-to-agentic-systems-microsoft-at-open-source-summit-north-america-2026/)
- [InfoQ — Cloudflare Dynamic Workflows](https://www.infoq.com/news/2026/05/cloudflare-dynamic-workflows/)
- [Cloudflare — Workflows GA: production-ready durable execution](https://blog.cloudflare.com/workflows-ga-production-ready-durable-execution/)

K8s-minus alternatives:
- [Starmorph — AI Agent Deployment: Cloud Platforms Compared 2026](https://blog.starmorph.com/blog/ai-agent-deployment-cloud-platforms-compared)
- [Northflank — Best agent cloud platforms 2026](https://northflank.com/blog/best-agent-cloud-platforms)

Standards:
- [Solo.io — What Is Agent2Agent Protocol (A2A)](https://www.solo.io/topics/ai-infrastructure/what-is-a2a)
- [Google Cloud — A2A protocol upgrade](https://cloud.google.com/blog/products/ai-machine-learning/agent2agent-protocol-is-getting-an-upgrade)
- [Anthropic — Donating MCP to Agentic AI Foundation](https://www.anthropic.com/news/donating-the-model-context-protocol-and-establishing-of-the-agentic-ai-foundation)
- [TNS — MCP roadmap 2026](https://thenewstack.io/model-context-protocol-roadmap-2026/)
- [Apicurio Registry](https://www.apicur.io/registry/)

## Source Quality Assessment

- **High confidence**: CNCF announcements, KubeCon EU 2026 schedule, InfoQ on Pinterest/Cloudflare, Red Hat on Kagenti, TNS on Temporal/Anthropic/Spotify. These are primary or near-primary.
- **Medium confidence**: oneuptime.com tutorial series (current but vendor blog); Markaicode and dev.to posts (useful but secondary).
- **Watch-outs**:
  - LiteLLM has had a 2026 supply-chain compromise; treat any LiteLLM install as a security event.
  - "Agentic mesh" remains more marketing than spec; vendors mean different things by it.
  - Apicurio CNCF status (sandbox-issue still open) — incubation timeline uncertain.
  - Fly.io GPU deprecation (Aug 2026) is recent enough that not all comparisons reflect it.

## Open Questions

- Will Dapr Agents stay ahead of Kagenti, or will Red Hat's OpenShift-AI bundle win in enterprise?
- Does anyone besides Pinterest have a published MCP-server-as-CRD playbook?
- What does Kueue + Temporal Worker Controller look like together? Both want to schedule, both want to autoscale.
- Will NATS JetStream stay the simple default, or will Redpanda displace it for agent workloads on the strength of Kafka API compatibility?

## Actionable Takeaways

1. **For a solo builder migrating Helioy:** start with CloudEvents on the local bus, containerize, k3s + Dapr + NATS, OTel from day one. Don't adopt SPIFFE or Istio Ambient until you actually have multiple agents.
2. **For a team standing up an enterprise k8s agent platform tomorrow:** Dapr Agents + NATS JetStream + Temporal + Istio Ambient + Agent Gateway + KEDA + OTel/LGTM + ArgoCD. Floor cost ~$500/mo at minimum; realistic prod is $3-10k/mo before model spend.
3. **Don't build:** a custom agent broker, custom workload identity, custom LLM gateway. Every one of these has a CNCF-quality OSS option in 2026.
4. **Pin and audit:** LiteLLM versions (PyPI compromise), Apicurio (sandbox-status), Fly.io GPU plans (deprecated Aug 2026).
5. **Watch:** Agentic AI Foundation governance, Kagenti graduation to Red Hat AI H2 2026, the Knative Eventing `RequestReply` resource for MCP-bridge use cases.
