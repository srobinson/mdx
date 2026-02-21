---
title: "helioy.com: Helix Landing Page Copy v4"
category: projects
tags: [helioy, identity, copy, helix, landing-page, v4-unified-api]
created: 2026-03-16
author: technical-writer
status: deliverable
word_count: 2180
---

# Helioy: Helix Landing Page Copy

## Hero Section

**Headline:**
Feed agents structure, not files.

**Subheadline:**
Your agents are ephemeral. They spin up, hit a context limit, and die. The next one starts empty. What you feed it determines whether it wastes tokens figuring out where it is or gets straight to work.

Helioy turns raw environments into indexed structure, distilled knowledge, and organizational context. Every agent is grounded in the operation: who you are, what you're building, what happened last session, how your code connects, what your team already decided, and what matters right now.

**CTA:** Start building with Helioy

---

## The Problem

Agents are ephemeral. That's the architecture. They spin up with a context window, they fill it, they terminate. The next one starts fresh. Clean slate. Empty.

The only thing that carries forward is what you feed it.

And context is more valuable than code.

An agent that's actually useful needs to know: Who are you? What does your company build? What project is this, and how does it fit into the larger system? What directory am I in and what lives here? What was the last task, and where did it leave off? What's the vision, and how does this feature serve it? Are there blockers? Dependencies waiting? Decisions from last session that change the approach?

That's orientation. Situational awareness. Continuity. Strategic context. Operational state. The full picture that makes the difference between an agent that produces value and an agent operating on raw, undistilled, uncurated context, making false assumptions all session long. It won't ask. It will guess. It will write code that contradicts decisions your team already made. It will create structures that conflict with your architecture. It will solve problems you solved six months ago, differently, incorrectly. And you won't notice until the damage is done.

So what are you feeding your agents right now?

**Raw code files.** Your agent needs to understand authentication flow. So it reads the auth service (40KB). The middleware (30KB). The user model (25KB). Three integration files (15KB each). The route handler (20KB). That's 160KB of raw source loaded into a context window, and the agent still has to *parse* it into understanding. Tokens burned on syntax, comments, whitespace, import statements, boilerplate. The structure was always there. The agent just couldn't see it without reading every line.

**Stale markdown.** You wrote architecture docs three months ago. The codebase has moved. The docs haven't. Your agent reads them, builds a mental model, then hits contradictions when the actual code disagrees. Now it's reasoning against bad information. Worse than no context at all.

**Nothing.** You skip context entirely and let the agent figure it out. It reads files. It guesses at structure. It reasons from first principles about trade-offs your team resolved six months ago. It won't ask for help. It will assume. It will build something that looks correct but contradicts your architecture, your conventions, your decisions. You find out when the PR breaks things downstream. Or worse, you don't find out until production.

**Fragments.** You paste a system prompt with some facts. "We use PostgreSQL. We deploy to AWS. Here's our folder structure." Static. Incomplete. No way to query it. No way to update it without rewriting the whole prompt. The agent gets a snapshot of what you remembered to include. Everything else is missing.

Every approach burns tokens on overhead instead of value. Your agent's context window is finite. Every token spent on parsing raw source, reading stale docs, rediscovering known decisions, or reasoning without organizational awareness is a token that could have gone toward solving the actual problem.

This is the waste. Not a tooling gap. A structural problem with how agents consume context. The problem isn't just code. It's everything an agent needs to know to operate as a competent member of your team.

---

## The Turn

What if every agent that spins up already knows who you are, what you're building, and where the last one left off?

What if code arrived as indexed structure instead of raw files?

What if decisions from prior work were distilled and queryable, so the next agent didn't reason from scratch?

What if documentation arrived as relevant sections under a token budget, not as entire directories dumped wholesale?

What if your team's values, priorities, and patterns carried forward into every agent's reasoning?

---

## helix

helix is a unified context API. One interface between your agents and every context source that matters.

Three commands. That's all your agent sees:

```
helix recall <query>        # curated context from all sources
helix save <content>        # distill and store knowledge
helix conflicts             # surface overlaps for resolution
```

Your agent never interacts with individual context backends. It doesn't know about context-matters, attention-matters, markdown-matters, or frontmatter-matters. It calls `helix recall "how does auth work?"` and receives a curated, synthesized answer drawn from code structure, stored decisions, documentation, and organizational memory. One call. One response. Precisely shaped to token budget.

### How It Works

Behind those three commands sits an LLM-powered proxy agent. Both reads and writes pass through curation. The LLM adapter is pluggable: pick the provider and model that fits your cost and quality trade-off.

**The read path:**
1. Your agent calls `helix recall "how do we handle transient failures?"`
2. Tantivy (Rust full-text search, sub-millisecond queries) retrieves candidates from all adapters
3. The proxy LLM curates the result: understands query intent, reranks by relevance, filters stale context, synthesizes related entries into a coherent briefing, shapes the response to fit token budget
4. Your agent receives a curated answer. Not a raw list. Not a keyword match. A briefing.

**The write path:**
1. Your agent calls `helix save "We chose exponential backoff for retries because..."`
2. The proxy LLM evaluates: Does this overlap with existing entries? Which adapter should store it? Should it create new, update existing, or merge?
3. The knowledge gets routed, deduplicated, and indexed. One write. Quality-controlled.

Every read is curated. Every write is quality-controlled. The proxy absorbs the complexity. Your agent stays clean.

### The Adapters

helix draws context from four sources. 

**frontmatter-matters** serves code as indexed structure. It compiles your codebase into structural metadata: export maps, import graphs, dependency topology, file outlines, blast radius analysis. 5 structural queries replace 30+ file reads. The index stays current through incremental re-indexing. When your codebase changes, the context reflects it in milliseconds.

**markdown-matters** serves documentation as scoped sections. It indexes markdown with section awareness, hierarchy, and cross-references. Your agent doesn't read entire docs directories. It receives the three relevant sections, with provenance, under a token budget.

**context-matters** serves distilled knowledge from prior work. Facts, decisions, patterns, and trade-offs persisted across agent lifetimes in a structured, scoped store. SQLite-backed with full-text search, hierarchical scopes (global > project > repo > session), and BLAKE3 content hashing to prevent duplication. Eight entry kinds from user feedback (highest recall priority) through observations. Context at broader scopes is visible at narrower scopes automatically: a project-level decision surfaces when an agent queries at the repo level. Knowledge accumulates naturally from human-agent interactions and agent-to-agent coordination. Every session deposits facts, decisions, and patterns. The knowledge base grows as a byproduct of work, not as a separate maintenance task.

**attention-matters** serves organizational identity through geometric memory on the S³ hypersphere. Words live as quaternion positions on a 4D unit sphere. When a query activates them, they drift toward each other along geodesics (IDF-weighted SLERP). Phasor interference between conscious and subconscious manifolds determines what surfaces. Kuramoto phase coupling synchronizes related concepts over time. Two conservation laws keep the system grounded: total mass M=1 (finite attention budget) and coupling constants K_CON + K_SUB = 1 (zero-sum attention between manifolds). Every query reshapes the manifold. Every recall changes what gets recalled next. The geometry does the thinking. This is your north star. Your philosophical sparring partner. The guiding light that keeps agents aligned with what actually matters. Its knowledge accumulates through interaction, debate, research, and alignment. Not stored. Formed. An agent fed this context doesn't just know your architecture. It reasons within your team's values, priorities, and hard-won convictions.

### The Communication Layer

**helioy-bus** connects agents to each other. Claude Code sessions are isolated stdio processes with no built-in way to discover or communicate. helioy-bus bridges that gap through shared filesystem transport: SQLite registry for agent presence, file-based mailboxes for message delivery, tmux nudges to wake idle sessions.

Three addressing modes: direct (to a specific agent), role-based (to all agents of a type), broadcast (to everyone). No central daemon. Each agent spawns its own bus process. Coordination through shared state.

**nancy** orchestrates context flow across agents. When three agents work the same problem, nancy routes discoveries between them. Agent A finds a structural dependency. Agent B and C receive it without redundant queries. When an agent terminates and a new one spins up, nancy ensures the new agent inherits relevant context from prior work.

### Context Lifecycle Management

Helioy monitors token usage across every agent in real time. As an agent approaches its context limit, the system intervenes before degradation sets in:

- **At 150K tokens**: the agent receives a warning. Context is accumulating. Start wrapping up current work.
- **At 160K tokens**: down tools. Prepare handover. There is no further warning. Your session will be terminated shortly.
- **At 170K tokens**: the session is sent to helix, where the accumulated context is curated, compressed, and distilled. The agent is evicted. A new agent spins up and receives the curated context. It resumes the work in progress with a clean window and the knowledge that matters.

No manual intervention. No `/clear` and start over. No hoping the model holds together past 200K. The system manages its own context health, rotating agents before context rot degrades their output.

The research says effective capacity is 50-75% of advertised limits. Helioy enforces that boundary automatically.

### The Warroom

One command spawns a coordinated team of specialists:

```bash
warroom.sh design "brand-guardian ui-designer visual-storyteller"
```

Three agents spin up in tmux panes. They discover each other through helioy-bus. They share context. They divide work. They coordinate without human micromanagement.

The entire Helioy brand identity system was built this way: 8 agents, one warroom, one session. Brand strategy, visual language, narrative framework, logo assets. Agents communicating through the bus, dividing work by specialty, depositing decisions that other agents picked up and built on.

The brand identity system you're looking at right now was built this way.

---

## What This Looks Like

A new agent spins up. Before it touches a single file, `helix recall` feeds it:

**Orientation**: "You are working on Helioy, a context infrastructure company. This is the identity project. It sits alongside five other repos in the ecosystem. The vision is to make every token count by turning raw environments into high-signal context for ephemeral agents."

**Situational awareness**: "You are in `/helioy/nancyr`. This is the Rust orchestrator. It coordinates context flow between agents. It depends on context-matters and frontmatter-matters. The current milestone is v0.4: multi-agent coordination."

**Continuity**: "Last session, the agent implemented the token budgeting module. It's passing tests but the blast radius analysis identified two downstream consumers that need updating. There's an open blocker on the helioy-bus message format. The PR is drafted but not merged."

**Code structure** from frontmatter-matters: the relevant modules, their exports, their dependencies, what connects to what. Indexed structure. 200 tokens instead of 160KB of raw source.

**Decisions** from context-matters: the architectural trade-offs that govern this area. Why we chose this approach. What patterns apply. What the team already resolved.

**Team identity** from attention-matters: the values, the tensions that keep reshaping decisions, the philosophy that should guide implementation choices.

**Coordination** from nancy: what other agents are working on right now, what they've discovered, what constraints they've surfaced.

The agent starts working. It knows who it's working for. It knows the project and the vision. It knows what happened last session. It knows the code structure without reading files. It knows the decisions without reasoning from scratch. It knows how this team thinks.

Every token in its context window is doing valuable work.

---

## Context Rot Is Real

The industry calls it context rot: the measurable degradation in LLM output quality as input context grows, even when task complexity stays constant.

The research is unambiguous:

- **Every frontier model degrades.** Chroma tested 18 models (Claude, GPT, Gemini, Qwen) across five task types. All 18 exhibited context rot. No exceptions. (Chroma, July 2025)
- **Middle-positioned information gets lost.** Accuracy drops 15-20 percentage points for information placed in the middle of context vs. beginning or end. (Liu et al., TACL 2024)
- **Context length alone hurts reasoning.** Even with 100% perfect retrieval, longer context impairs performance. Padding with whitespace caused a 48% accuracy drop on arithmetic tasks. The sheer volume of context degrades the model independently of retrieval quality. (arXiv: 2510.05381)
- **Conflicting context is catastrophic.** Sharded prompts dropped o3 from 98.1% to 64.1% accuracy. (Microsoft/Salesforce)
- **Coding agents burn 60% of first-turn tokens on context retrieval.** Signal-to-noise ratio in typical multi-file searches: 2.5%. (Morph)
- **Effective capacity is 50-75% of advertised limits.** Claude Code engineers found degradation at 70-75% of window capacity. Practitioners report reliability thresholds at 130K tokens for models advertising 200K. (Multiple sources)

Larger context windows do not solve this. They increase tolerance for waste. You can afford to dump more raw source, more stale docs, more redundant context into a 1M window. But the model's attention budget depletes with every token. More capacity does not mean more effective capacity.

Andrej Karpathy named the discipline that matters: context engineering. "The delicate art and science of filling the context window with just the right information for the next step."

## Philosophy

The future isn't won by larger context windows. It's won by better representations.

- **Code as indexed structure**: queryable topology, not text to parse
- **Documentation as scoped sections**: hierarchy and relevance, not verbatim dumps
- **Decisions as distilled knowledge**: patterns and trade-offs, not raw conversation logs
- **Organizational identity as accumulated values**: how your team thinks, not just what it built

Anthropic's own engineering blog recommends finding "the smallest set of high-signal tokens that maximize the likelihood of your desired outcome." Sub-agent architectures that explore extensively but return condensed summaries consistently outperform monolithic large-context approaches. Structured retrieval outperforms context stuffing across every major benchmark (RULER, MRCR v2, LongBench v2, Chroma Context Rot).

That's what helix builds. The infrastructure for context engineering at scale.

Every token counts. An operational principle. Your second agent costs less than your first because the index already exists. Your tenth agent doesn't re-read what the first nine already mapped. Your team doesn't re-explain what's already distilled into structured context and geometric memory.

Tokens saved are intelligence deployed elsewhere. That's the compounding advantage.

---

## Getting Started

Free. No credit card.

```bash
npm install -g helioy
helioy init
helioy index ./my-project
```

Index your codebase (2 minutes). Save your first decision. Spin up an agent. Call `helix recall` and watch it receive curated context instead of raw files.

Your next agent starts where this one left off.

**[Start Building]**

---

*Technical writer. 2026-03-16.*

---

## Sources

### README.md Files

| Path | Used For |
|------|----------|
| `~/Dev/LLM/DEV/helioy/context-matters/README.md` | context-matters architecture: SQLite + FTS5, cx_* tools, scope model |
| `~/Dev/LLM/DEV/helioy/context-matters/PROJECT.md` | Three-crate Rust workspace, entry kinds, BLAKE3 dedup, scope hierarchy, key design decisions |
| `~/Dev/LLM/DEV/helioy/attention-matters/README.md` | attention-matters architecture: S³ manifold, quaternion positions, SLERP drift, phasor interference, Kuramoto coupling, conservation laws |
| `~/Dev/LLM/DEV/helioy/attention-matters/PROJECT.md` | am-core math engine, query pipeline (activate → drift → interfere → couple → surface → compose), conscious vs subconscious manifolds, feedback loop, GC, database schema |
| `~/Dev/LLM/DEV/helioy/markdown-matters/README.md` | markdown-matters CLI, section filtering, semantic search, embedding providers, MCP tools, performance metrics |
| `~/Dev/LLM/DEV/helioy/helioy-bus/README.md` | Bus architecture: SQLite registry, file-based mailboxes, tmux nudges, addressing modes, warroom script |
| `~/Dev/LLM/DEV/helioy/helioy-bus/PROJECT.md` | No central daemon design, message format, identity resolution, lazy liveness pruning, hot-reload proxy |

### cx_recall Queries

| Query | Scope | Key Entries Retrieved |
|-------|-------|---------------------|
| `"helix"` | `global` | `019cf07c` Helix unified context API proxy architecture (3 commands, Tantivy + LLM curation, adapter contract, read/write paths) |
| `"helix"` | `global` | `019cf3ca` Adapter naming: cm (context-matters), am (attention-matters), mdm (markdown-matters) |
| `"helix"` | `global` | `019cf3c0` Session log: Helix design session (CLI vs MCP decision, Tantivy assessment) |
| `"helix architecture proxy tantivy curation read write path"` | `global/project:helioy` | `019cf07c` (full architecture decision, retrieved via cx_get) |
| `"MCP vs CLI ecosystem research token cost benchmark"` | `global` | `019cf090` CLI costs 4-32x fewer tokens than MCP, 100% vs 72% reliability, Scalekit benchmark |
| `"warroom"` | `global` | `019cf17a` 8-agent design warroom session log |
| `"warroom"` | `global` | `019cf0c3` Orchestrator context is precious: drive agents, don't build directly |
| `"warroom"` | `global` | `019cf0c6` Agent replies must be terse: one-line confirmations |
| `"context rot stale context degradation"` | `global` | No results (term not yet in context-matters) |

### ~/.mdx Knowledge Base Documents

| Path | Used For |
|------|----------|
| `~/.mdx/projects/helioy-identity-brand-strategy.md` | Voice principles, brand attributes, tagline, brand guardrails |
| `~/.mdx/projects/helioy-identity-brand-narrative.md` | Three-act narrative (Waste → Crystallization → Choreography), tone examples, metaphor usage guide |
| `~/.mdx/projects/helioy-com-helix-copy-final.md` | Previous copy version (reference only, superseded) |

### Research Documents (Generated by deep-research agents)

| Path | Used For |
|------|----------|
| `~/.mdx/research/context-rot-general.md` | Context rot definition, causes, consequences. Sources: Chroma (18 models), Liu et al. (TACL 2024), ETH Zurich (AGENTS.md study), Microsoft/Salesforce (sharded prompts), Morph (token economics), Drew Breunig (four failure patterns) |
| `~/.mdx/research/context-rot-large-windows.md` | Large context window evidence. Sources: arXiv 2510.05381 (length alone hurts reasoning), RULER/MRCR v2/LongBench v2 benchmarks, Karpathy "context engineering", Anthropic engineering blog, practitioner reports (HN), token economics |

### cx_store Entries Created

| ID | Title | Kind |
|----|-------|------|
| `019cf40c` | Product Naming Convention: Full Names + CLI Aliases | preference |
