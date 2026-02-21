---
title: "Blog Series: Little Organs — What Claude Code Taught Me About What Agents Actually Need"
type: projects
tags: [blog, claude-code, littleorgans, agents, MCP, content, series]
summary: "A blog series connecting deep Claude Code experience to the Little Organs agent architecture. Each post stands alone but builds toward the full thesis."
status: draft
created: 2026-03-26
updated: 2026-03-26
project: my-voice
confidence: medium
---

# Little Organs — Blog Series

## Series Arc

The series moves from lived experience to biological insight to architecture to implementation. Each post works standalone but rewards sequential reading. The through-line: everything we need to know about building agents, biology figured out billions of years ago.

## Series Outline

### 1. Context Rot (The Problem)

**Hook:** I have spent the last year living inside Claude Code. Thousands of hours. Millions of tokens. Every long session degrades the same way.

**Thesis:** The context window is not a capacity problem. It is a curation problem. Agents waste tokens rediscovering things they already know. By the time the interesting work starts, half the context is occupied by things that no longer matter.

**Content:**
- What "living inside Claude Code" actually looks like (MCP servers, plugins, multi-agent panes, helioy ecosystem)
- The specific failure mode: 20 turns reasoning about something that could have been known in 2 turns
- Search traces pile up. Dead-end reasoning accumulates. Compression kicks in. Important decisions get evicted.
- Then the agent contradicts its own earlier work because it literally cannot remember what it decided
- Name the problem: context rot
- Show it with real examples from production sessions
- End with the question: what if curation was built into the system, not bolted on?

**Positioning:** Establishes credibility. Shows the depth of experience. Names a problem everyone feels but few articulate precisely.

---

### 2. What Biology Already Knows (The Insight)

**Hook:** I was reading Blaise Aguera y Arcas on life as embodied computation when the connection clicked. Living cells solved this problem billions of years ago.

**Thesis:** Cells do not dump their entire genome into the cytoplasm and hope. They have membranes. Active, selective, intelligent boundaries that control what gets in and when. Gene expression is just-in-time context delivery.

**Content:**
- Von Neumann's Universal Constructor: clean separation between machinery (ribosome/executor) and instructions (DNA/policy)
- How we build agents today: everything in one undifferentiated blob. No membrane. No separation.
- Symbiogenesis as a novelty engine: novel capability emerges from fusion of successful cooperation, not isolated mutation
- The BFF experiment (BrainFuck Fission): abiogenesis in silico. Complex replicating programs emerge from random bytes through symbiogenesis.
- The key principle: embodied computation requires closure between memory and process
- The contrast: our agents have no closure. They do not maintain themselves. They degrade.

**Positioning:** The intellectual foundation. This is the post that separates you from the "prompt engineering tips" crowd. Nobody else in the agent space is drawing from origin-of-life research.

---

### 3. Start With Closure, Not Architecture (The Bootstrapping Sequence)

**Hook:** Most agent frameworks start with architecture. Clean abstractions. Beautiful diagrams. They skip straight to step five and wonder why nothing sustains itself.

**Thesis:** Origin-of-life research tells us there is a bootstrapping sequence you cannot skip. Each step must be earned by establishing the prior one.

**Content:**
- The seven-step bootstrapping sequence for agency:
  1. Energy Flow (task stream)
  2. Boundary (context membrane / responsibility scope)
  3. Primitive Closure (one agent that can reason, act, and evaluate)
  4. Autocatalytic Set (diverse capabilities mutually sustaining each other)
  5. Specialization (clean architecture emerges from evolutionary pressure)
  6. Hypercycles (coupled agents maintaining collective fidelity)
  7. Evolution (behavior improves through observation, critique, memory, selection)
- Why closure matters more than architecture: a closed loop that maintains itself beats a beautiful system that degrades
- The minimum autocatalytic set: 10 capabilities needed for bootstrapped agency (observe, interpret, plan, act, evaluate, remember, prune, delegate, repair, reframe)
- These form a closed loop. Get that loop closing reliably first. Then everything else follows.

**Positioning:** A framework people can apply to their own agent work. This is the post that gets bookmarked.

---

### 4. The Single Cell (The Architecture)

**Hook:** The minimal living unit is not a fleet. It is a cell.

**Thesis:** Instead of distributed agent swarms, start with one cell containing specialized organelles coordinated by an active membrane.

**Content:**
- Why "organelle" and not "microservice" or "sidecar": the biological metaphor carries real architectural meaning
- The five core organelles:
  - **Membrane**: scores relevance, curates and injects context, routes to correct organelle, evicts stale state
  - **Research**: resolves uncertainty gaps, searches with sharp questions, returns evidence-ranked substrate
  - **Doer**: executes narrow tasks, produces observable outputs, minimizes speculation
  - **Critic**: checks correctness, detects assumption drift, issues repair signals
  - **Scribe**: compresses only what matters, stores validated residue, manages confidence decay
- Transport agnosticism: above the adapter layer it is "I need planning / critique / code edit." Below, it routes to CLI (Claude Code, Codex) or Provider API (Anthropic, OpenAI, OpenRouter)
- The delegation cascade: signal-based, not command-based. Membrane curates locally or escalates to Research. Research searches or escalates to Strategist. Thresholds determine escalation.

**Positioning:** The architectural reveal. Concrete enough to implement against.

---

### 5. The Membrane (Context as a Living Boundary)

**Hook:** The membrane is not a buffer. It is the most important organelle in the cell.

**Thesis:** The membrane performs JIT context curation. It watches the conversation in real time, detects likely intent and missing prerequisites, and retrieves relevant context before the agent wastes tokens searching for it.

**Content:**
- Five membrane operations: Retrieve, Curate, Compress, Place, Evict
- Placement matters: identity at the start (system prompt territory), tasks at the end (recency bias), working memory in the middle
- The JIT context sidecar pattern: do not make the agent earn context by searching for it if the system can infer and deliver it earlier
- Context budget allocation:
  - 30% Identity Core (~45k tokens)
  - 40% Working Memory (~60k)
  - 20% Retrieved Memory (~30k, JIT-paged not preloaded)
  - 10% Communication Buffer (~15k)
- Confidence decay: anything not revalidated decays. Prevents preservation of old truths as current ones.
- Supersession, not overlay: when new context supersedes old, remove old, do not stack. Stacking causes context rot.
- The distinction between useful residue and narrative residue: keep corrections, results, patterns, validated precedent. Evict reasoning traces, dead ends, stale plans.

**Positioning:** The deepest technical post. This is where the rubber meets the road on context engineering.

---

### 6. SUBSTRATE, FRAME, REPAIR (The Communication Protocol)

**Hook:** Agents communicate. The question is whether the communication is typed, directional, and purposeful or whether it is just... chat.

**Thesis:** Three message types, flowing in specific directions, prevent context pollution and enable catalytic closure.

**Content:**
- **SUBSTRATE (upward)**: compressed observations from lower to higher organelles. Lossy OK. 20:1 to 50:1 compression. Signal extraction over narrative.
- **FRAME (downward)**: interpretive scaffolds that configure how lower organelles process. Must be lossless. Small but high-leverage. A 500-token frame reshapes 60k tokens of processing.
- **REPAIR (lateral)**: targeted corrections between peers. Precise, actionable, confidence-aware.
- The message envelope: type, source, target, confidence, priority, TTL, payload, enables, requires, staleness_action
- Why direction matters: substrate up, frame down, repair lateral. Violate directional flow and context pollution results.
- The compression discipline: each stratum holds context at native resolution and communicates only compressed transformations
- Concrete example: 80k tokens of security scan becomes 1k structured substrate message (150:1 compression). The receiver can request lazy decompression if needed.

**Positioning:** Protocol-level thinking. Attracts systems engineers who care about clean abstractions.

---

### 7. Measuring Closure (When Does the System Live?)

**Hook:** How do you know if a system of agents is sustaining itself or slowly dying?

**Thesis:** Closure is measurable. A composite score across six metrics tells you whether your cell is alive, degrading, or broken.

**Content:**
- Closure metrics:
  - Loop completion rate (cycles without stalling)
  - Internal repair rate (REPAIR messages restoring function)
  - Context efficiency (useful work per token)
  - Eviction correctness (stale material removal)
  - Memory yield (remembered items improve later performance)
  - Delegation quality (tasks reach correct organelle)
- The composite closure score (weighted formula)
- What strong closure looks like:
  - Rarely asks for information it already has
  - Rarely repeats failed reasoning
  - Often produces better second attempts than first
  - Gets more coherent under pressure, not less
- Two modes of cognition: live cognition (active session) and consolidation cognition (longer-term memory management, biological "sleep")
- The distinction between a system that does work and a system that maintains itself while doing work

**Positioning:** Gives people a way to evaluate their own agent systems. Measurement attracts the serious builders.

---

### 8. Building the First Cell (The Implementation)

**Hook:** Everything I built over the past year becomes the substrate for the first living cell.

**Thesis:** The first Little Organs cell runs inside Claude Code. The membrane uses attention-matters for recall and context-matters for structured persistence. frontmatter-matters provides code intelligence. helioy-bus handles inter-organelle communication.

**Content:**
- How the existing helioy ecosystem maps to organelles
- The command/event boundary: commands are domain actions (create cell, store memory, delegate task), events are state changes (CellActivated, ContextEvicted, ClosureMeasured)
- The operator experience: start cell, submit task, watch membrane curate, watch delegation, inspect diagnostics, intervene only if system degrades
- State modes: Starting, Operational, Degraded, Recovering, Broken, Closed
- What I expect to learn from the first cell
- Open questions: can membrane-coordinated organelles sustain autonomous work without degrading? Can we measure closure in production?
- Invitation to build together

**Positioning:** The "what's next" post. Converts readers into collaborators or clients.

---

## Publishing Strategy

| Post | Publish Target | Purpose |
|------|---------------|---------|
| 1. Context Rot | Personal blog + Dev.to + LinkedIn | Establishes credibility, names the problem |
| 2. Biology | Personal blog + HackerNews | The differentiator. HN will engage with the origin-of-life angle |
| 3. Closure | Personal blog + Dev.to | The bookmarkable framework |
| 4. Single Cell | Personal blog | Architecture reveal |
| 5. Membrane | Personal blog + paid submission to The New Stack ($300-800) | Deepest technical post, worth pitching |
| 6. Protocol | Personal blog | Attracts protocol-minded engineers |
| 7. Measuring Closure | Personal blog + Dev.to | Practical measurement, attracts builders |
| 8. First Cell | Personal blog + littleorgans.com | Launch post |

**Cadence:** One post per week. 8 weeks total. Cross-promote each post on X with 1-2 tweets pulling out the sharpest insight.

**Revenue angle:** Post 5 (Membrane) is the strongest candidate for paid technical writing submission. Posts 1 and 3 are strong for Dev.to visibility. Post 2 is the HackerNews play.

---

## Post 1 Draft: Context Rot

I have spent the last year living inside Claude Code. Not using it. Living in it. Building an entire ecosystem of MCP servers, custom plugins, multi-agent orchestration, geometric memory systems ... all from within Claude Code sessions. Thousands of hours. Millions of tokens.

Every long session degrades the same way.

### The context window is not a capacity problem

Everyone talks about context windows getting bigger. 200k tokens. A million. As if the problem is capacity.

I run sessions where Claude Code operates across six interconnected Rust projects, navigates dependency graphs, reads structural indexes, queries memory stores, and orchestrates work across multiple agent panes. The context fills up fast. Not because the window is small but because agents are wasteful.

They read files they already read. They search for symbols they found ten minutes ago. They rediscover project structure on every turn. They carry dead reasoning traces like sediment. By the time the interesting work starts, half the context is occupied by things that no longer matter.

### What "living inside Claude Code" looks like

Let me be specific.

**frontmatter-matters** indexes every codebase in my ecosystem. Precomputed AST analysis stored in SQLite. When Claude Code needs to find a symbol, trace a dependency, or understand a file's structure, it calls an MCP tool and gets the answer in one shot. No grep. No glob. No reading files to derive what the index already knows. One tool call replaces 10-50 file reads.

**context-matters** gives agents structured memory that persists across sessions. Facts, decisions, preferences, lessons ... classified by kind and scoped hierarchically. Global knowledge flows down. Session knowledge stays local. When an agent starts a new task, it calls `cx_recall` and gets relevant context from every prior session that touched related work.

**attention-matters** takes this further with geometric memory on the S3 hypersphere. Rather than keyword matching against flat records, it models memory as neighborhoods on a curved manifold. Related memories cluster. Recall follows geodesics. Associations surface that keyword search would never find.

**helioy-bus** connects agents running in separate tmux panes. They send messages, check inboxes, coordinate work. An orchestrator dispatches tasks. Workers report back.

All of this ships as Claude Code plugins. MCP servers that any Claude Code session can install and use immediately.

### The failure mode

After months of building and using these tools, I kept watching the same failure pattern.

Sessions that worked well had the right context at the right time. Not all context. Not a dump of everything possibly relevant. The right slice, delivered before the agent wasted tokens searching for it.

Sessions that went badly had the opposite. The agent spends 20 turns reasoning about something it could have known in 2 turns if the context had been there. Search traces pile up. Dead-end reasoning accumulates. Then compression kicks in and important early decisions get evicted. Then the agent contradicts its own earlier work because it literally cannot remember what it decided.

I started calling this context rot. It happens in every long session. Every single one.

### The prosthetics problem

The tools I built ... frontmatter-matters, context-matters, attention-matters ... are all attempts to solve context rot from the outside. Give the agent better recall. Give it precomputed answers. Give it structured memory.

These help. They help a lot. A session with these tools runs circles around one without them.

But they are prosthetics. External aids bolted onto a system that has no internal curation. The agent still does not manage its own context. It does not decide what to keep and what to evict. It does not compress its own reasoning traces. It does not notice when it is about to rediscover something it already found.

The curation has to come from inside the system. Not from better tools. From the architecture itself.

### What I am building next

I have been working on something called Little Organs. A biologically grounded agent substrate where the core unit is a cell containing specialized organelles coordinated by an active membrane. The membrane does not wait for the agent to ask for context. It delivers context before the agent wastes tokens discovering it needs it.

The biological metaphor is not decoration. Living cells solved this problem billions of years ago. Gene expression is just-in-time context delivery. The membrane is an active, selective, intelligent boundary that controls what gets in, what gets out, and when.

There is a lot to unpack here. How origin-of-life research maps to agent architecture. Why you have to start with closure before architecture. What the membrane actually does at a protocol level. How you measure whether a system of agents is sustaining itself or slowly dying.

I will dig into all of it over the coming weeks.

The starting point is simple. Context is finite. Curation is everything. No amount of clever tooling overcomes the physics of a finite window when the system itself is not managing what occupies that window.

If you are building agents and hitting the same wall ... the wall where sessions degrade, where context fills with garbage, where the agent forgets what it decided three turns ago ... that is context rot. And the answer is not bigger windows.

---

*Stuart Robinson builds AI agent infrastructure at Helioy. His tools ship as MCP servers for Claude Code.*
