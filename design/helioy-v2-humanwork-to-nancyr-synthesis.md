# Helioy V2: HumanWork to Nancyr Synthesis

Date: 2026-03-11
Status: Concrete synthesis and action plan
Author: Codex

## Purpose

This note synthesizes four threads:

- the original HumanWork design in `/Users/alphab/Dev/LLM/DEV/TMP/memory/docs`
- the Amorphic evolution notes in `/Users/alphab/Dev/LLM/DEV/TMP/memory/docs.amorphic`
- the emerging Helioy product-group thesis
- the current `nancyr` direction as a self-improving collaborative intelligence runtime

The goal is not to preserve every idea.

The goal is to identify:

1. what is already strong in the HumanWork design
2. what should be adopted into Helioy and `nancyr`
3. what should be deferred
4. what the first actionable implementation wedge should be

## Executive Judgment

The original HumanWork design is much stronger than a typical early architecture draft.

Its best qualities are:

- strong separation of concerns
- explicit human authority
- event-derived memory model
- scoped execution semantics
- serious treatment of observability and rewindability

The design already contains the seeds of an enterprise-grade runtime.

What it does **not** yet fully contain is:

- a unified actor model for humans and machines
- a first-class ledger of correction intelligence
- an authority gradient richer than simple preemptive control
- a crisp product wedge that proves the system in reality before the full vision expands

The right move is not to discard HumanWork.

The right move is to **translate it into Helioy terms and sharpen it into a build sequence**.

## What the Current HumanWork Design Gets Right

### 1. Strong Architectural Separation

The separation across:

- control plane
- org
- workspace
- jobs
- execution contexts
- workflows
- memory

is good.

This is visible in:

- [00-README.md](/Users/alphab/Dev/LLM/DEV/TMP/memory/docs/00-README.md)
- [01-ARCHITECTURE.md](/Users/alphab/Dev/LLM/DEV/TMP/memory/docs/01-ARCHITECTURE.md)
- [04-EXECUTION_MODEL.md](/Users/alphab/Dev/LLM/DEV/TMP/memory/docs/04-EXECUTION_MODEL.md)

This matters because enterprise systems fail when execution, control, storage, and learning are collapsed into one abstraction.

The HumanWork design already avoids that mistake.

### 2. Event-Derived Memory Is the Right Backbone

The three-layer memory model is strong:

- Event / Fact Memory
- Status Memory
- Semantic Memory

Source:

- [05-MEMORY_MODEL.md](/Users/alphab/Dev/LLM/DEV/TMP/memory/docs/05-MEMORY_MODEL.md)

This is already close to the right enterprise shape.

The main evolution needed is naming and emphasis:

- Event Memory should become **The Ledger**
- Status Memory stays a projection layer
- Semantic Memory stays an advisory understanding layer

That change is not cosmetic. It clarifies that the immutable behavioral record is the primary learning asset.

### 3. Execution Contexts Are a Strong Primitive

Execution Contexts are one of the best parts of the current design.

They correctly separate:

- durable intent from Jobs
- concrete work from disposable runtime actors
- immutable records from transient execution state

This is important because it gives you:

- rewindability
- replaceable agents
- explicit scope
- safe deletion of transient processes

This should carry forward into `nancyr`.

### 4. Workflows as Guidance, Not Law

The workflow philosophy is correct.

Source:

- [06-WORKFLOWS.md](/Users/alphab/Dev/LLM/DEV/TMP/memory/docs/06-WORKFLOWS.md)

The insistence that workflows are:

- reusable coordination patterns
- guidance
- not execution engines

is exactly right.

This protects the system from becoming brittle process bureaucracy.

### 5. Workspace Isolation Is Enterprise-Credible

The Org / Workspace model is also strong.

Source:

- [03-ORG_WORKSPACE_MODEL.md](/Users/alphab/Dev/LLM/DEV/TMP/memory/docs/03-ORG_WORKSPACE_MODEL.md)

The strict workspace boundary is good because it creates:

- cost attribution
- isolation
- explicit promotion
- controlled cross-workspace learning

That is the kind of thing enterprises actually need.

## Where the Current Design Should Evolve

### 1. Replace "Agent" as the Core Labor Primitive

The current primitives still center "Agent" too much.

Source:

- [02-PRIMITIVES.md](/Users/alphab/Dev/LLM/DEV/TMP/memory/docs/02-PRIMITIVES.md)

The stronger primitive is:

- `Actor`

with:

- `type: human | machine`
- identity
- role
- capabilities
- authority mode
- cost model
- scope binding

Why:

- it unifies human and machine labor
- it supports cost/governance cleanly
- it matches the Amorphic insight that labor should be treated as one observable stream

Recommendation:

- keep `Agent` as a subtype or runtime implementation detail
- elevate `Actor` to the first-class primitive

### 2. Rename Event Memory to The Ledger

The current design says Event Memory is the source of truth.

That is correct, but underpowered in framing.

The ledger language from the Amorphic notes is better.

Why:

- it implies immutability
- it implies value capture, not mere logging
- it makes learning and audit feel native
- it makes enterprise positioning stronger

Recommendation:

- rename Event / Fact Memory to `Ledger`
- describe it as the primary behavioral asset of the system

### 3. Add Correction Events as a First-Class Primitive

This is the biggest missing operational primitive.

The current design has control actions and artifacts, but it does not yet foreground:

- human corrections of machine output
- why those corrections happened
- what pattern they reveal

You need:

```yaml
correction_event:
  id: string
  timestamp: timestamp
  actor_id: string
  target_id: string
  target_type: enum (deliverable, recommendation, decision, message, workflow)
  diff: object
  rationale: string?
  pattern_type: enum (tone, structure, facts, logic, policy, scope, sequencing)
  magnitude: enum (minor, moderate, major, rewrite)
```

This primitive matters because it is the cleanest substrate for self-improvement that does not require mystical assumptions.

### 4. Add an Authority Gradient

The current control model is strong on preemption but too binary.

You need richer collaboration modes:

- instructional
- consultative
- supervisory
- exploratory

This should be carried at least at:

- Execution Context level
- Actor binding level
- maybe Workflow defaults

Why:

- different tasks need different human-machine contracts
- it reflects real enterprise work more accurately
- it provides a better control plane abstraction than simple pause/resume/override

### 5. Promote Deliverables over Artifacts Where Appropriate

"Artifact" is technically fine but weak in organizational language.

"Deliverable" is stronger when discussing value-bearing work products.

Recommendation:

- keep `artifact` internally if needed for low-level system naming
- use `deliverable` at product and org-facing layers

### 6. De-Romanticize Semantic / Geometric Memory in the Core Runtime

The current HumanWork design and the Amorphic notes are strongest when discussing:

- ledgers
- control
- scopes
- checkpoints
- workflows
- corrections

They are weaker when the core runtime starts sounding like:

- resonance-driven implicit coordination
- shared memory as the primary collaboration mechanism

That may become valuable later.

But for the first credible version of `nancyr`, the runtime should rely on:

- explicit ownership
- explicit messages
- explicit checkpoints
- explicit review

Reflective / semantic / geometric memory should remain advisory and secondary in the first wedge.

## Translation into the Helioy Stack

The clearest synthesis now looks like this:

- `fmm`
  code structure and navigation

- `mdcontext`
  document indexing and retrieval

- `am`
  reflective organizational memory

- context compiler
  tactical curation and token budgeting

- `helioy-bus`
  communication substrate for identities, inboxes, and warrooms

- `nancyr`
  collaborative runtime coordinating actors, workflows, deliverables, review, and learning

The HumanWork design should evolve into the conceptual substrate for `nancyr`, not remain a separate parallel philosophy.

## Concrete Primitive Set for Nancyr

The first strong primitive vocabulary should be:

- `Org`
- `Workspace`
- `Actor`
- `Role`
- `Job`
- `ExecutionContext`
- `Workflow`
- `Deliverable`
- `LedgerEvent`
- `CorrectionEvent`
- `Checkpoint`
- `AuthorityLevel`

### Suggested Definitions

**Actor**

> A unit of labor in the system, human or machine, bound to a role and operating under an authority mode.

**Deliverable**

> An immutable work product produced within a Workspace: code, document, decision, analysis, recommendation, review.

**LedgerEvent**

> An append-only record describing something that happened in the system.

**CorrectionEvent**

> A ledger event capturing how a human or authorized actor modified prior output and what that reveals.

**AuthorityLevel**

> The mode governing how tightly a human remains involved in execution.

## Product Thesis for Nancyr

The right thesis is now:

**`nancyr` is a self-improving collaborative runtime that coordinates a unified labor stream of humans and machines, captures corrective intelligence in a ledger, and improves execution quality through better collaboration over time.**

That is more actionable than:

- "human thinking with AI"
- "agent orchestration"
- "workflow automation"

because it names:

- the unit of labor
- the learning mechanism
- the optimization target

## The First Enterprise Wedge

The first believable enterprise wedge should not be "run the whole company."

It should be:

**coordinated scoped delivery for small cross-functional work**

Examples:

- one product feature
- one architecture review
- one incident follow-up
- one release planning exercise
- one research spike

The wedge should prove:

1. a coordinator can split work across specialists
2. review/sign-off improves outcomes
3. human correction data can be captured cleanly
4. the ledger can explain what happened and why
5. the next similar workflow improves

That is enough.

## What to Build First

### Phase 1: Runtime Skeleton

Build:

- Workspace
- Job
- ExecutionContext
- Actor
- Deliverable
- LedgerEvent

Do not start with:

- sophisticated semantic memory
- cross-org learning
- autonomous topology evolution

### Phase 2: Warroom + Bus Discipline

Build:

- stable actor identity
- structured bus messages
- explicit coordinator protocol
- basic specialist role contracts

Messages should include:

- sender
- recipient
- purpose
- workspace/job/context IDs
- required action
- urgency
- related deliverables

### Phase 3: Checkpoints + Review

Build:

- approval checkpoints
- decision checkpoints
- exit checkpoints
- review deliverables
- sign-off and rejection events

This is where enterprise trust begins.

### Phase 4: Correction Intelligence

Build:

- CorrectionEvent schema
- correction capture UI/API
- diff and rationale storage
- pattern extraction reports

This is the start of real self-improvement.

### Phase 5: Authority Gradient

Add:

- per-context authority mode
- escalation triggers
- delegation triggers
- visibility into human intervention rate

### Phase 6: Advisory Memory + Context Services

Then integrate:

- `fmm`
- `mdcontext`
- `am`
- context compiler

These should enrich the runtime, not define it.

## What to Defer

Defer these until the first wedge is real:

- high agent counts
- fully dynamic team topologies
- heavy geometric-memory claims in the core runtime
- deep automatic prompt rewriting everywhere
- fully autonomous planning societies
- enterprise-wide labor replacement narratives

The system will become more ambitious safely only after the collaboration substrate is proven.

## Measurable Proof Criteria

The first real version should be judged by a small set of metrics:

### Collaboration Metrics

- duplicate work rate
- blocked handoff rate
- review catch rate
- rework after sign-off

### Runtime Metrics

- delivery completion rate
- time to completion
- cost per deliverable
- intervention frequency by authority mode

### Learning Metrics

- number of correction events captured
- repeated pattern detection rate
- protocol changes adopted from retrospection
- improvement on repeated workflow classes

If these do not improve, the runtime is not yet real regardless of how sophisticated it sounds.

## Direct Critique

The HumanWork design is already architecturally serious.

Its main risk is not bad structure.

Its main risk is that it can sound complete before it has a wedge.

The Amorphic notes intensify that risk because they are rich, suggestive, and category-shaping.

That is useful for vision.
It is dangerous for sequencing.

So the discipline required now is:

- keep the language of infrastructure
- keep the rigor of event-derived systems
- keep the ambition of unified labor
- but only build what can prove itself in a narrow runtime first

## Final Recommendation

Do not abandon HumanWork.

Translate it.

The right move is:

1. treat HumanWork as the conceptual ancestor
2. fold its strongest primitives into `nancyr`
3. adopt from Amorphic:
   - Actor
   - Ledger
   - CorrectionEvent
   - AuthorityLevel
4. keep `helioy-bus` as communication substrate
5. keep `fmm`, `mdcontext`, and `am` as context services
6. prove the runtime on small, scoped collaborative delivery first

If you do that, the path toward enterprise infrastructure becomes much more believable.
