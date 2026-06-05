---
title: "Blog Draft: What Biology Already Knows About Agent Architecture"
type: projects
tags: [blog, claude-code, littleorgans, agents, biology, series]
summary: "Post 2 of the Little Organs series. The biological foundations: Von Neumann, membranes, symbiogenesis, and why origin-of-life research is the best guide to agent design."
status: draft
created: 2026-03-26
updated: 2026-03-26
project: my-voice
confidence: medium
related: [blog-claude-code-littleorgans]
---

# What Biology Already Knows About Agent Architecture

*This is Part 2 of a series on Little Organs. [Part 1: Context Rot](/blog/context-rot) established the problem. This post explains where the answer comes from.*

---

Last week I described context rot. The pattern where AI agent sessions degrade because agents have no internal curation. They fill their context with search traces, dead reasoning, and stale assumptions until the useful signal drowns.

I said the answer is not bigger windows. I said biology solved this billions of years ago.

Now I have to back that up.

## The membrane insight

Here is the thing about cells. A cell does not dump its entire genome into the cytoplasm and hope the right proteins get made. That would be insane. You would get every gene expressed at once. Chaos. The cell would die.

Instead, the cell has a membrane. An active, selective boundary that controls what crosses in and out. And inside, gene expression is regulated ... only the genes relevant to current conditions get transcribed. A liver cell has the same DNA as a neuron. The difference is which parts are active at any given moment.

This is just-in-time context delivery. The cell retrieves and expresses only what it needs for current conditions. Everything else stays compressed in the genome, available but not occupying active working space.

Now look at how we build agents. We stuff everything into one context window. System prompt, conversation history, tool results, memory retrievals, task descriptions ... one undifferentiated blob. No membrane. No curation. No separation between what drives behavior and what constitutes working memory. We hand the model 150k tokens of material and hope it attends to the right parts.

We wonder why sessions degrade after 30 turns.

## Von Neumann saw it first

John von Neumann worked out the theory of self-reproducing automata in the 1940s. His Universal Constructor requires a clean separation between two things: the machinery that does the building (the constructor) and the instructions that describe what to build (the blueprint).

In biology, the constructor is the ribosome. The blueprint is DNA. They are coupled but distinct. The ribosome reads DNA and produces proteins. The proteins maintain the cell. The cell maintains the DNA. This is a closed loop.

Von Neumann proved that you cannot build a self-reproducing system without this separation. If the constructor and the blueprint are the same thing, the system cannot copy itself without corrupting itself.

This maps directly to agents. We have a constructor (the LLM, which produces actions and reasoning) and we have instructions (the system prompt, the context, the memory). But we mix them together in the same window. The model's reasoning traces sit alongside the instructions that should be guiding that reasoning. Old outputs contaminate the input for new outputs. The constructor and the blueprint occupy the same space.

Von Neumann would not be surprised that our agents degrade.

## Symbiogenesis: how novelty actually emerges

Lynn Margulis had this theory that everyone thought was wrong until it turned out to be right. Mitochondria were not always part of our cells. They were independent organisms. At some point, one cell engulfed another. Instead of digesting it, the two learned to cooperate. The engulfed organism became the mitochondrion. It kept its own DNA. It handles energy production. The host cell handles everything else.

This is symbiogenesis. Novel capability through fusion of successful cooperation.

The standard story in tech is that you get novelty through iteration. Build, test, refine. Evolution through mutation and selection. Margulis showed that the biggest leaps in biological complexity came from something different. Two systems that worked independently discovered they worked better together and fused into a single organism.

This matters for agents because the dominant approach to building multi-agent systems is hierarchical. An orchestrator at the top. Worker agents below. Clean chains of command. But biology tells us that the most powerful architectures emerge from lateral cooperation, not vertical command. The interesting thing is not one agent telling another what to do. The interesting thing is two agents discovering that each produces something the other needs and forming a self-sustaining loop.

## Life as computation

Blaise Aguera y Arcas has been writing about this. His core argument: life is computation. Not metaphorically. Literally. Every living system performs autopoiesis ... self-production. The cell produces the components that maintain the cell. The system computes its own continuation.

The critical insight from his work is about embodied computation. The medium in which computation happens matters. You need closure between memory and process. The computation must be able to read its own state, modify its own state, and persist changes to its own state. Without closure, the system cannot maintain itself. It can produce outputs but it cannot sustain itself.

Our agents have no closure. They produce outputs. They complete tasks. But they do not maintain themselves. They do not manage their own context. They do not evict stale reasoning. They do not notice when they are about to repeat a mistake. They are computers that cannot access their own hard drive.

## The BFF experiment

There is an experiment called BrainFuck Fission that demonstrates something remarkable. You take a minimal programming language (BrainFuck, eight instructions, Turing complete). You create a "primordial soup" of random byte sequences. You run them in a shared environment where programs can read and write to shared memory.

What happens is that complex replicating programs emerge spontaneously. Not through design. Through the same process Margulis described: successful cooperators fuse. A short program that can copy bytes encounters a short program that can seek to a specific memory address. Neither can replicate alone. Together they can. They fuse. The fused program outcompetes both parents.

This is abiogenesis in silico. Life from non-life. Complexity from randomness. Not through top-down design but through bottom-up closure.

The lesson for agents: you do not design the architecture first. You create the conditions for closure. You give agents the ability to cooperate, to share products, to fuse capabilities. The architecture that emerges from closure is more robust than anything you could design upfront.

## What this means for Little Organs

The biological principles translate into concrete architectural decisions.

**Membrane, not buffer.** The boundary around an agent is not a passive container. It is an active curation system that controls what enters and exits the agent's working context. It reads the current state, predicts what the agent will need next, and delivers it. Just like gene expression.

**Organelles, not services.** The components inside a cell are not microservices communicating over HTTP. They are organelles ... specialized, bounded subsystems that share the same cellular medium. They are coupled through chemistry, not APIs. In agent terms: they share typed messages with explicit catalytic dependencies, not generic RPC calls.

**Closure before architecture.** Do not start by designing the perfect multi-agent system. Start by getting one loop to close: observe, interpret, plan, act, evaluate, remember, prune, reframe. When that loop sustains itself, you have earned the right to add complexity.

**Autocatalytic sets, not dependency chains.** The organelles in a cell do not form a linear pipeline. They form a self-sustaining network where each component both enables and is enabled by its neighbors. The membrane curates context for the doer. The doer produces results for the scribe. The scribe stores validated knowledge for the membrane. Remove any one and the loop breaks. This mutual dependency is the source of robustness, not a weakness.

**Cooperation over command.** The most powerful capability in a cell did not come from internal optimization. It came from two independent organisms discovering they were better together. Agent architectures should make lateral cooperation easy and let capability emerge from it. Not everything needs a supervisor.

## The uncomfortable implication

If you take biology seriously, the dominant multi-agent frameworks have the causality backwards.

They start with architecture. Clean abstractions. Supervisor agents, tool-using agents, reflection agents. Beautiful diagrams. Then they try to make the system sustain itself through more engineering. More guardrails. More retry logic. More elaborate prompt chains.

Biology says: start with closure. One loop that can maintain itself. Earn each subsequent level of complexity by demonstrating that the prior level sustains. Architecture is an emergent property of successful closure, not the other way around.

Most agent frameworks are at step five of a seven-step bootstrapping sequence and wondering why the foundations feel shaky.

Next week I will lay out that bootstrapping sequence. The specific steps, derived from origin-of-life research, that you must earn in order. And the minimum autocatalytic set ... the ten capabilities that form the smallest self-sustaining loop.

---

*Stuart Robinson builds AI agent infrastructure at Helioy. His tools ship as MCP servers for Claude Code. This is Part 2 of the Little Organs series.*
