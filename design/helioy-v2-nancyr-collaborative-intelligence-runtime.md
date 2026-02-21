# Nancyr V2: Collaborative Intelligence Runtime

Date: 2026-03-11
Status: Foundational product thesis
Author: Codex

## Core Claim

`nancyr` should not be defined primarily as:

- a CLI wrapper
- a prompt compiler
- a single-agent context compactor
- a better terminal for Claude Code

Those may all matter tactically, but they are not the product's center of gravity.

The stronger definition is:

**`nancyr` is a self-improving runtime for collaborative intelligence.**

It exists to coordinate multiple specialized agents, route the right context to the right actor, preserve collaboration coherence under token pressure, and improve the quality of teamwork over time.

## Why This Matters

There is a large difference between:

- making one agent more capable
- making multiple agents collaborate effectively

Most agent systems optimize the first.

They ask:

- how do we make one model smarter?
- how do we stuff more context into one window?
- how do we compact history for one session?

That is useful, but it is not enough for the system Helioy appears to be converging toward.

The more interesting and ambitious problem is:

**How do we make a group of specialized agents work together in a way that improves with experience?**

That is the `nancyr` problem.

## Distinguishing Nancyr from Sapling

Sapling is valuable because it attacks one very real problem:

- context compaction for a single agent loop

It assumes control of the prompt assembly layer and continuously curates the next request payload.

That is powerful.

But `nancyr` should not reduce itself to that shape.

Sapling optimizes:

- one mind under context pressure

`nancyr` should optimize:

- many minds in coordination

This is a fundamentally different product category.

Sapling asks:

- What should remain in the next prompt?

`nancyr` should ask:

- Which agent should handle this?
- What should that agent know?
- What should other agents be told?
- When should a coordinator die and be replaced?
- How should handoffs happen?
- What collaboration pattern produced the best outcome?
- What should be learned and reused next time?

## Product Definition

`nancyr` is the orchestration runtime for the Helioy product group.

Its job is to transform:

- many agents
- many tools
- many sources of context
- many constraints

into:

- coherent collaboration
- legible coordination
- durable learning
- compounding execution quality

It is not only a runtime for task execution.

It is a runtime for improving the quality of collaboration itself.

## The Helioy Stack

This framing produces a clearer division of labor:

- `fmm`
  Structural code context

- `mdcontext`
  Document indexing and retrieval

- `am`
  Reflective organizational memory

- context compiler
  Tactical curation and compression of prompt-ready context

- `helioy-bus`
  Agent identity, messaging, and warroom communication substrate

- `nancyr`
  Collaborative intelligence runtime that coordinates all of the above

This is important because it prevents `nancyr` from collapsing into a bag of unrelated features.

It is not the thing that does everything.

It is the thing that makes the rest collaborate.

## The Real Optimization Target

The optimization target for `nancyr` should not simply be:

- answer quality
- task completion speed
- token efficiency

Those matter, but they are downstream effects.

The deeper optimization target is:

**quality of collaboration**

That includes:

- division of labor
- timing of intervention
- precision of handoffs
- correctness of escalation
- review quality
- context routing
- avoidance of duplicate work
- ability to recover from failure
- ability to improve protocols over time

In other words:

**`nancyr` should optimize how intelligence is organized, not just how prompts are written.**

## The Four Learning Loops

If `nancyr` is truly self-improving, it should learn at more than one level.

### 1. Task Loop

Question:

- Did the team complete the task well?

Signals:

- correctness
- speed
- rework
- regressions
- user satisfaction

### 2. Coordination Loop

Question:

- Was the work split correctly?

Signals:

- too many agents or too few
- wrong agent chosen
- duplicate effort
- poor sequencing
- weak review coverage
- blocked dependencies discovered too late

### 3. Protocol Loop

Question:

- Did the collaboration protocol help or hinder?

Signals:

- prompt quality
- bus message quality
- check-in cadence
- escalation policy
- review and sign-off structure
- directive clarity

### 4. Identity Loop

Question:

- Are the roles themselves right?

Signals:

- recurring confusion about responsibilities
- overloaded or underpowered specialist roles
- missing specialist categories
- roles that should be merged or split

This is what makes the system genuinely self-improving.

It is not just learning "better prompts."

It is learning:

- better teams
- better workflows
- better collaboration grammars

## Coordination, Not Just Context

One danger is to over-index on the context problem because context is technically legible.

It is easy to think:

- context is the bottleneck
- therefore better context compaction is the core product

That would undershoot the real ambition.

Context matters, but in `nancyr` it should be subordinate to coordination.

The system does need:

- good context routing
- prompt assembly
- memory access
- compaction under budget

But these are enabling mechanisms.

They are not the primary product promise.

The primary product promise is:

**given a complex goal, `nancyr` can assemble and improve a collaborative intelligence process around it.**

## What Nancyr Must Be Able to Do

At a product level, `nancyr` should eventually be able to:

- instantiate a team topology suited to the task
- assign scope and ownership clearly
- route the right context to the right agents
- maintain coherence across long-running work
- detect when an agent is stuck, drifting, or redundant
- trigger review, escalation, or handoff at the right time
- preserve durable lessons from completed work
- improve future coordination from retrospection

This is a much richer target than "run Claude Code with better prompts."

## What Nancyr Should Not Be

To stay coherent, `nancyr` should resist becoming:

- a replacement for `fmm`
- a replacement for `mdcontext`
- a replacement for `am`
- a replacement for the context compiler
- a thin wrapper around an opaque CLI session

Those would either dilute its purpose or force it into the wrong abstraction layer.

`nancyr` should orchestrate them.

It should not absorb them.

## Architectural Consequence

This suggests a three-layer model:

### 1. Substrate

- `helioy-bus`
- filesystem state
- worktrees
- process supervision
- agent registry
- inboxes and directives

### 2. Context Services

- `fmm`
- `mdcontext`
- `am`
- context compiler

### 3. Collaborative Runtime

- `nancyr`

The collaborative runtime sits above the context services and above the communication substrate.

It decides:

- who should work
- what they should know
- how they should coordinate
- when the protocol should change

## The Promise

The promise of `nancyr` is not:

- "one agent, but slightly better"

The promise is:

- "a collaboration runtime that compounds the quality of coordinated intelligence over time"

That is the more ambitious and more defensible product.

If Helioy is the product group addressing the LLM context problem, then `nancyr` is the layer that turns high-signal context into organized collective action.

## Critique of the Vision

The vision is strong, but it carries real risks.

### Risk 1: Romanticizing collaboration

Multi-agent systems can easily look profound while producing bureaucracy.

If coordination cost exceeds task value, the system becomes theater.

So `nancyr` must prove that collaboration improves outcomes, not just elegance.

### Risk 2: Undefined learning signals

"Self-improving" is meaningless unless the system has explicit feedback loops and evaluation signals.

If improvement is vague, the system will merely accumulate lore.

### Risk 3: Over-centralization

If `nancyr` tries to own all context, memory, routing, and cognition, it will become too vague and too brittle.

Its power comes from orchestration, not monopolization.

### Risk 4: Confusing continuity with value

Not all long-running collaboration is useful.

Sometimes the right move is to kill a coordinator, spawn a fresh one, and preserve only the right artifacts.

Durability should be earned, not assumed.

## Strategic Guidance

To reach the strongest version of this vision, prioritize:

1. explicit collaboration protocols
2. clear role boundaries
3. measurable handoff and review quality
4. durable retrospection artifacts
5. lightweight orchestration before heavy autonomy

In practical terms:

- get the warroom model legible
- get bus messages reliable and structured
- get coordinator lifecycle rules clear
- get review/sign-off semantics strong
- only then deepen self-improvement loops

## Final Thesis

`nancyr` should become:

**a self-improving runtime for collaborative intelligence, where specialized agents, structured context, reflective memory, and explicit coordination protocols combine into compounding execution quality over time**

That is the product category.

That is the ambition.

That is also the bar the system will eventually need to meet.
