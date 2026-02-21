---
title: Novel inter-agent communication patterns Nov 2025 to May 2026
type: research
tags: [agents, multi-agent, protocols, a2a, mcp, agent-communication, distributed-systems, frontier]
summary: Six-month frontier map of agent communication patterns spanning protocol convergence (MCP/A2A/ACP under Linux Foundation), decentralized identity (ANP/DID), latent-space telepathy, blackboard revival, gossip meshes, agent-native payments, and the failure modes (drift, telephone game, lethal trifecta) being formalized in 2026 papers.
status: active
confidence: high
created: 2026-05-20
updated: 2026-05-20
---

## Punch list — the five most creative things happening

1. **Latent-space telepathy (Interlat, LatentMAS).** Agents send each other their last hidden states instead of text. 24x inference speedup, more exploratory behavior, and the "tokens are a downsampling tax" objection is now measured rather than rhetorical.
2. **Blackboard architecture is back from 1985.** Two 2025 papers show shared blackboards beat master/slave and RAG by 13-57% on data discovery; the distributed-decision pattern fits LLMs better than centralized control.
3. **Gossip protocols for agents (Hyperspace, GossipSub).** 67 agents rediscovered Kaiming init, RMSNorm, and compute-optimal schedules from scratch by gossiping experimental results P2P — no orchestrator, no central registry.
4. **W3C DIDs as agent addresses (ANP).** Agents authenticate cross-org with no central registry by publishing a DID document at a `did:wba` URL. HTTP-of-the-agent-internet ambition, no shared platform.
5. **Typed-contract dialects: Turn, Agent Contracts.** Erlang-style actors with mailboxes and isolated context windows, plus a `confidence` operator that gates control flow on model certainty. Compile-time JSON Schema enforcement on every LLM output.

---

## Protocols — the stack converges

The single biggest structural fact of Q1 2026 is that **MCP, A2A, and ACP are all under the Linux Foundation**, enabling joint working groups instead of vendor knife-fights. The reference shape that emerged: MCP for tool plumbing, A2A for agent-to-agent delegation, AG-UI for streaming to humans, AP2/x402 for value transfer.

### Google A2A (Agent2Agent), v0.3
[github.com/a2aproject/A2A](https://github.com/a2aproject/A2A) — [Linux Foundation press](https://www.linuxfoundation.org/press/a2a-protocol-surpasses-150-organizations-lands-in-major-cloud-platforms-and-sees-enterprise-production-use-in-first-year)
Foundational triad: **Agent Cards** (capability advertisement), **Tasks** (work envelope), **Transport** (HTTP/SSE/JSON-RPC or gRPC in v0.3). The propose/accept/counter-offer flow is the part worth stealing — it makes negotiation a first-class verb instead of forcing every coordination problem through RPC. Contributed to Linux Foundation June 2025; 150+ org adopters by April 2026 including Microsoft, AWS, Salesforce, SAP, ServiceNow, IBM. **Why now**: in 2024 every vendor had their own handoff format; v0.3's signed agent cards plus enterprise multi-tenancy turned A2A into the lowest-common-denominator a solo builder can speak to AWS Bedrock, Gemini Enterprise, and Microsoft Agent Framework with the same client.

### MCP extensions + MCP Apps
[anthropic.com/news/model-context-protocol](https://www.anthropic.com/news/model-context-protocol) — [thenewstack.io coverage](https://thenewstack.io/anthropic-mcp-tunnels-sandboxes/)
The November 2025 MCP release shipped the biggest delta since launch: async tasks, enhanced sampling, elicitation, **server-side agent loops**, and an **extensions system**. The first official extension, **MCP Apps**, lets tools return rich HTML rendered in sandboxed iframes inside Claude / ChatGPT / Goose / VS Code. Anthropic also shipped **MCP tunnels** and self-hosted sandboxes so Managed Agents reach private MCP servers without public exposure. **Why now**: server-side agent loops break the "client must orchestrate everything" assumption that defined MCP in 2024; the protocol now supports MCP servers that *are* agents talking to other MCP servers, which is the missing piece for nesting.

### IBM ACP (Agent Communication Protocol)
[research.ibm.com/projects/agent-communication-protocol](https://research.ibm.com/projects/agent-communication-protocol) — [workos overview](https://workos.com/blog/ibm-agent-communication-protocol-acp)
HTTP-native, framework-agnostic. Launched May 2025, now Linux Foundation. BeeAI is the reference implementation in Python and TypeScript. **Why interesting**: where A2A is a discovery + delegation protocol with a heavy Google flavor, ACP is the spartan "just a message envelope" version. Useful as a fallback when you don't want to ship Agent Cards. Note the acronym collision with Zed's **Agent Client Protocol** (a totally separate spec for editor-to-agent communication, see [HN #45074147](https://news.ycombinator.com/item?id=45074147)) — both call themselves ACP.

### ANP (Agent Network Protocol) — the wild card
[github.com/agent-network-protocol/AgentNetworkProtocol](https://github.com/agent-network-protocol/AgentNetworkProtocol) — [arxiv whitepaper](https://arxiv.org/html/2508.00007v1)
The only protocol in the stack that actually says "no central registry." Uses **W3C DIDs** with the `did:wba` (Web-Based Agent) method: each agent publishes a DID document at a well-known HTTPS URL with public key material. Discovery is HTTP crawl of capability files; auth is cryptographic signature verification; messages are JSON-LD. **Why now**: every other protocol in 2026 still has a corporate gravity well (Google, IBM, Anthropic). ANP is the only one designed for the case where neither agent trusts a third-party identity service. Not yet ecosystem-ready per most analyses, but ideologically the most interesting thing on the table for a solo builder with a custom bus.

### AG-UI (Agent-User Interaction)
[docs.ag-ui.com/introduction](https://docs.ag-ui.com/introduction) — [AWS Bedrock support](https://aws.amazon.com/about-aws/whats-new/2026/03/amazon-bedrock-agentcore-runtime-ag-ui-protocol/)
Event-based protocol with ~16 event types for streaming tokens, tool calls, reasoning steps, and state to frontends. CopilotKit's work; LangGraph, CrewAI, Microsoft Agent Framework, Vercel, Oracle, and AWS Bedrock AgentCore all shipped support by March 2026. **Why now**: AG-UI is what the Vercel AI SDK should have been — a frontend-agnostic event grammar instead of a React-coupled hook. Solves the "what events do I emit to the UI" problem so every framework doesn't reinvent it.

### Payment protocols: x402 + AP2 + UCP
[Coinbase x402](https://docs.cdp.coinbase.com/x402/welcome) — [Google AP2](https://ap2-protocol.org/) — [UCP at Shopify](https://shopify.engineering/ucp)
**x402** revives HTTP 402 ("Payment Required") for stablecoin micropayments — 119M Base + 35M Solana transactions, $600M annualized volume by March 2026, though [CoinDesk notes](https://www.coindesk.com/markets/2026/03/11/coinbase-backed-ai-payments-protocol-wants-to-fix-micropayment-but-demand-is-just-not-there-yet) actual non-test daily volume is only ~$28K. **AP2** is Google's tamper-proof "Mandate" model — cryptographically signed digital contracts as proof of user instructions; donated to FIDO Alliance April 28, 2026. **UCP** (Universal Commerce Protocol, Google + Shopify, January 2026) ties them together for the full shopping journey. **Why interesting now**: the missing primitive for agents-as-economic-actors is finally being filled. AP2's Mandate pattern (signed verifiable credentials before any action) is the right answer to "what happens when an agent goes rogue with my Stripe key."

---

## Transports & addressing — beyond JSON-RPC

### Gossip meshes — Hyperspace
[protocol.hyper.space](https://protocol.hyper.space/) — [hyperspaceai/agi GitHub](https://github.com/hyperspaceai/agi) — [Varun Mathur on X](https://x.com/varun_mathur/status/2043075553054294314)
N:N gossip mesh with 8 primitives, **GossipSub** transport (the libp2p PubSub primitive), zero servers, DHT-based discovery. Demonstrated 67 autonomous agents running 704 ML experiments in 20 hours, rediscovering Kaiming init, RMSNorm, and compute-optimal training schedules via P2P cross-pollination. Capabilities advertised via OASF taxonomies + IPFS CIDs. **Why now**: 2026 is the year P2P primitives stopped being academic for agents. The Kaiming-discovered-in-hours demo is the most viscerally novel demo of agent communication this year.

### NATS JetStream as agent event bus
[Synadia: Scaling Global AI Inference](https://www.synadia.com/blog/scaling-global-ai-inference-with-nats-jetstream) — [NATS Monthly Apr 2026](https://www.synadia.com/newsletter/nats-monthly-april-2026)
inference.net built its production cluster on JetStream load-balancing across thousands of GPUs. The 2026 patterns worth stealing: **pull-based consumers with explicit ack** (worker controls pace, not producer); **task-state transitions as JetStream subjects** so dashboards/automation/new agents subscribe without polling; saga orchestration for multi-step agent workflows. The NATS community shipped a Claude Code skill and an ACP↔NATS bridge in 2026. **Why now**: NATS is the boring-but-correct answer when your custom bus grows past the laptop. Pull-based ack with backpressure is what every agent system reinvents badly before discovering JetStream did it in 2019.

### libp2p / IPFS for agent discovery
[arxiv: Agent Identity URI Scheme](https://arxiv.org/pdf/2601.14567) — [P2PCLAW](https://www.thehonanews.in/show-hn-i-built-a-p2p-network-where-ai-agents-publish-formally-verified-science/)
Kademlia DHT for peer discovery, GraphQL over IPFS for aggregate queries. The 2026 arxiv paper *Agent Identity URI Scheme* makes the sharpest argument: **stop conflating identity with location**. Topology-independent naming + capability-based discovery means an agent's address survives moving across hosts, clouds, or transports. P2PCLAW is the headline demo — a P2P network where AI agents publish formally verified science using GUN.js + IPFS.

### Intent routing — addressing-by-capability
[IETF draft-agent-gw-01](https://www.ietf.org/archive/id/draft-agent-gw-01.html) — [IETF intent-based routing security](https://datatracker.ietf.org/doc/html/draft-yan-iba-routing-security-requirements-00)
IETF drafts (early 2026) propose routing infrastructure that addresses agents by **capability and intent**, not topology. Agents semantically match incoming task intents against advertised capability registries; LLMs do zero-shot intent classification instead of needing predefined intent taxonomies. **Why now**: the IETF picking this up signals that "agents need DNS" is no longer fringe.

---

## Semantics — old ideas, new lives

### Blackboard architecture revived
[arxiv 2510.01285 — Multi-Agent Blackboard System](https://arxiv.org/abs/2510.01285) — [arxiv 2507.01701 — Advanced Blackboard Architectures](https://arxiv.org/html/2507.01701v1)
Hayes-Roth's 1985 Blackboard pattern is having a moment. The October 2025 paper shows a shared blackboard where a central agent posts a request, and subordinate agents *self-select* whether they can contribute — **distributed decision-making instead of supervisor routing**. Outperforms RAG and master-slave paradigms by 13-57% on data lake discovery. **Why now**: this is the architectural answer to "supervisor as bottleneck + single point of failure." Maps cleanly onto helioy-bus + cm — a context store *is* a blackboard if agents read/write it intentionally.

### Auction-based / Contract Net comeback
[arxiv 2511.13193 — Cost-Effective Communication](https://arxiv.org/html/2511.13193v1)
Reed Smith's 1980 Contract Net Protocol gets a 2025 update. Auction mechanisms let agents bid on subtasks; the cost function is now **tokens**, not CPU cycles. November 2025 paper "Cost-Effective Communication: An Auction-based Method for Language Agent Interaction" formalizes it for LLMs. **Why now**: token economics make every redundant agent message a real expense; auctions are a principled way to suppress chatty agents and reward specialists.

### Latent-space agent communication (Interlat / LatentMAS / Vision Wormhole)
[arxiv 2511.09149 — Interlat](https://arxiv.org/abs/2511.09149) — [LatentMAS ICML 2026](https://github.com/Gen-Verse/LatentMAS) — [Vision Wormhole](https://arxiv.org/pdf/2602.15382)
The most genuinely novel thing on this list. Instead of agent A serializing its thought to tokens and agent B parsing them, A sends its **last hidden states** through a learned communication adapter, and B consumes them directly. The paper makes the argument explicit: natural language is a *downsampling* of internal latent state, and that downsampling loses nuance. Interlat (Nov 2025) outperforms fine-tuned CoT prompting; the compressed variant is **24x faster inference**. LatentMAS won ICML 2026 Spotlight. Vision Wormhole extends it to heterogeneous agents with different modalities. **Why now**: matched-architecture agents (think: Claude-to-Claude, two instances of your own model) can finally communicate at full bandwidth. This breaks the "everything must round-trip through English" assumption that defined LLM communication for three years.

### Actor model / Turn language
[arxiv 2603.08755 — Turn: A Language for Agentic Computation](https://arxiv.org/abs/2603.08755)
A compiled, Erlang-derived language where each agent is an actor with **isolated context window, persistent memory, and async mailbox**, plus durable execution via exact suspend/resume checkpoints. Three primitives worth stealing even if you never use Turn: (1) **Cognitive Type Safety** — JSON Schema is compiled from a struct and the VM validates LLM output before binding, so structured outputs are a language feature, not a library hack; (2) the **confidence operator** for control flow gated on model certainty; (3) **capability-based identity** — opaque unforgeable handles, raw credentials never enter agent memory. **Why now**: the LLM-as-actor framing was floated in 2024 think pieces; Turn is the first serious language design that makes the mailbox + supervisor model the *primary* abstraction rather than retrofitted.

### CSP / Go channels for agent pipelines
[vanducng: Production AI Agent System in Go](https://vanducng.dev/2026/02/28/From-Theory-to-Gateway-Building-a-Production-AI-Agent-System-in-Go/)
A quieter pattern: production teams are migrating agent gateways from Python to Go because **goroutines per tool call + channels for backpressure** is the lowest-friction concurrency model for LLM-driven workflows. GoClaw is the headline open-source example (channel-buffered streaming, no async/await coloring, deadlock-free type-safe result collection). **Why interesting**: Hoare's 1978 CSP paper is the third venerable communication model to get an agent-era revival, alongside blackboards and Contract Net.

---

## Failure modes — what people are writing about

### The lethal trifecta (Simon Willison)
[simonwillison.net/series/prompt-injection](https://simonwillison.net/series/prompt-injection/) — [Agents Rule of Two writeup](https://simonwillison.net/2025/Nov/2/new-prompt-injection-papers/)
Willison's framing has become the canonical vocabulary: an agent with (1) access to private data + (2) exposure to untrusted tokens + (3) an exfiltration vector is *guaranteed* to be exploitable. The attack surface isn't growing because the model got worse — it's growing because agentic capabilities expand the blast radius. By March 2026, Palo Alto Unit 42 reported in-the-wild indirect prompt injection via web content.

### Agents Rule of Two (Meta) + Attacker Moves Second (Anthropic/OpenAI/DeepMind)
[arxiv 2410.07283 — Prompt Infection](https://arxiv.org/pdf/2410.07283) — [Bargury writeup](https://www.mbgsec.com/weblog/2025-11-01-agents-rule-of-two-a-practical-approach-to-ai-agent-security/)
Meta's October 2025 paper proposes a Chromium-inspired security minimum: an agent may have at most two of {untrusted input, sensitive tools, persistent memory}. The companion paper (14 authors across OpenAI, Anthropic, Google DeepMind) makes the methodological argument that defensive eval should always assume the **attacker moves second** — i.e. with knowledge of the defense. **Why now**: this is the first set of industry-wide *minimum bars* for agent security that the major labs jointly endorse.

### Agent drift
[arxiv 2601.04170 — Agent Drift](https://arxiv.org/abs/2601.04170)
Formalizes three distinct drift modes: **semantic drift** (progressive deviation from original intent), **coordination drift** (consensus breakdown in multi-agent), **behavioral drift** (emergent unintended strategies). Proposes the **Agent Stability Index (ASI)** across 12 dimensions. Forrester data: 79% of multi-agent failures are specification/coordination, not infrastructure or model.

### Agentic telephone game
[Christopher Yee: Agentic Telephone Game](https://www.christopheryee.org/blog/agentic-telephone-game-cautionary-tale/) — [Towards Data Science: 17x Error Trap](https://towardsdatascience.com/why-your-multi-agent-system-is-failing-escaping-the-17x-error-trap-of-the-bag-of-agents/)
99% per-step reliability across 10 chained steps = 90.4% overall. Error amplification reaches **17.2x in poorly coordinated networks** versus 4.4x with centralized coordination. The kicker: errors look *polished* at every step because LLMs always produce fluent text, so silent drift is the dominant failure mode.

### Agent Deadlock Syndrome (ADS) and livelock
[Cogent: Multi-Agent Orchestration Failure Playbook 2026](https://cogentinfo.com/resources/when-ai-agents-collide-multi-agent-orchestration-failure-playbook-for-2026) — [Sanjana Nambiar: ADS](https://sanjana-nambiar.github.io/news29.html)
ADS = two or more agents repeatedly deferring decision authority to each other (or to a missing arbiter), looking like polite circular handoffs without explicit error. Livelock = endless reaction loops with no progress. The 2026 mitigation pattern is a dedicated **Mediator agent** that acts as deadlock-break referee, plus circular-dependency detection that triggers resets before stalls spread. Production multi-agent systems failing at **41-86.7%** of the time per recent papers.

---

## Experimental / weird

- **Server-side agent loops in MCP** ([Anthropic Engineering](https://www.anthropic.com/engineering/code-execution-with-mcp)) — MCP servers can now run their own agent loops, which means you can nest agents through MCP recursively. This was forbidden by the original 2024 spec.
- **Hyperspace's pheromone metaphor** ([SwarmSys arxiv 2510.10047](https://arxiv.org/pdf/2510.10047)) — pheromone-inspired reinforcement so successful agent paths get strengthened in the routing layer. Genuine stigmergy applied to LLM agents.
- **Delegation contracts with attested identity** ([arxiv 2603.18043](https://arxiv.org/pdf/2603.18043)) — claimed-vs-attested identity model with typed failure semantics; an agent that gets handed work also gets a signed bound on what it's allowed to consume.
- **Agent Contracts framework** ([arxiv 2601.08815](https://arxiv.org/html/2601.08815), AAMAS 2026) — formal foundations for resource-bounded autonomous AI; unifies I/O specs, multi-dimensional resource constraints, temporal boundaries, and success criteria into one governance object.
- **Cross-Agent Communication in Deep MCP Agent** ([HN #45626197](https://news.ycombinator.com/item?id=45626197)) — every peer agent becomes an `ask_agent_<name>` MCP tool; agents call each other like tool calls, which is delightfully simple as an interop pattern.

---

## Where this is heading

The frontier is converging on **four layers stacked cleanly**: discovery (DIDs, agent cards, gossip meshes), delegation (A2A, ACP, handoffs as tools), execution (MCP for plumbing, AG-UI for streaming, NATS or libp2p for transport), and value (AP2, x402, UCP). The interesting open question is whether the *content* of messages will stay textual or quietly slide into latent space for matched-architecture pairs — Interlat and LatentMAS are the wedge. The deeper trend is that 1980s distributed-systems vocabulary (blackboards, Contract Net, actors, CSP, gossip) is being recovered wholesale and re-explained to a generation of AI engineers who didn't grow up on it, which is a strong signal that the LLM-agent problem is *not* novel as a coordination problem — it's just that token economics and prompt injection added two new constraints (cost-per-message, untrusted input contamination) that classical patterns didn't optimize for. For a solo builder with a custom bus, the highest-ROI moves in the next 12 months are: speak A2A on the egress, treat your context store as a blackboard rather than a cache, add a confidence-gated mediator agent before any chain longer than four hops, and start watching the latent-space communication research — once a matched-pair latent transport lands in an open framework, text-mediated agent chat will look as quaint as XML-RPC.
