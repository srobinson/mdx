# AM High-Signal Memory Architecture Proposal

Date: 2026-03-11
Status: Proposal
Author: Codex

## Executive Summary

AM's current core problem is not the geometric memory engine itself. The problem is signal discipline across the full pipeline.

Today:

- broad raw memory enters the system
- retrieval can recall mechanically relevant material
- chat can still produce poor answers because recalled material is not sufficiently curated, ranked, or budgeted before it reaches the LLM

This proposal defines a new architecture for AM built around one principle:

**Every token that enters long-term memory or prompt context must earn its place.**

The proposed design combines three layers:

1. **Curated ingestion**
   Incoming data is filtered and normalized before it becomes indexed memory.

2. **Weighted retrieval scoring**
   Recalled memory is ranked using a richer scoring model than raw activation alone.

3. **Zone-based prompt budgeting**
   The final prompt explicitly allocates token budget across instructions, evidence, conversation state, and headroom.

This is the intended high-signal version of AM.

## Why This Proposal Exists

Two observations now seem clear:

### 1. Direct `am_query` can return meaningful memory

The memory engine is capable of surfacing useful material. That means the fundamental retrieval substrate is not broken.

### 2. Final chat answers can still be poor

Bad answers are being produced because raw or weakly curated recall is handed to the LLM too directly.

That means the problem is not just "memory quality." It is the full memory-to-generation pipeline:

- what gets stored
- what gets recalled
- what gets shown to the model
- how the model is asked to use it

## Product Thesis

AM should not be:

- a transcript landfill
- a raw recall dump
- a memory-themed chat shell

AM should be:

- a high-signal memory substrate for human and agent work
- a durable store of what was worth retaining
- a disciplined evidence system for LLM generation

The quality bar is not "can AM recall something related?"

The quality bar is:

- does AM store the right things?
- does AM retrieve the right things?
- does the LLM see the right evidence?
- does the answer reflect that evidence cleanly?

## Current Failure Modes

### Failure Mode 1: Dirty memory enters the system

Examples:

- prior weak assistant summaries
- operational chatter
- UI review fragments
- partial list items
- task-local coordination residue

These are valid artifacts of work, but not all are valid long-term memory.

### Failure Mode 2: Retrieved material is treated as prompt-ready

Recalled material can be:

- mechanically relevant
- semantically noisy
- low-trust
- malformed

But the chat pipeline still risks presenting it as evidence without enough filtering.

### Failure Mode 3: Prompt budget is implicit and sloppy

Without explicit token budgeting:

- evidence quality varies unpredictably
- weak context can monopolize space
- system behavior, evidence, and conversation state compete without discipline

### Failure Mode 4: Assistant output can self-poison the corpus

If mediocre assistant completions are stored and later recalled as evidence, quality degrades over time.

This is the most dangerous long-term loop in the current design.

## Architecture Overview

The proposed pipeline is:

`raw input -> ingestion curation -> indexed memory -> retrieval candidates -> evidence scoring -> prompt budget allocation -> LLM answer -> curated write-back`

This creates a five-stage high-signal system:

1. Ingest only memory-worthy content.
2. Store normalized memory units, not just raw text.
3. Rank candidates using retrieval plus trust-aware scoring.
4. Allocate prompt budget intentionally.
5. Write back curated output, not raw completion sludge.

## Layer 1: Curated Ingestion

### Goal

Prevent low-value content from ever becoming first-class indexed memory.

### Principle

Not every input deserves to become memory.

Inputs should first pass through an ingestion LLM or equivalent classifier/summarizer that decides:

- whether to store the content
- what kind of memory it is
- whether it is durable
- whether it should become conscious memory
- what normalized text should be indexed

### Inputs Covered

This ingestion policy should apply to:

- user / assistant exchanges
- uploaded documents
- synced transcripts
- imported histories
- explicit ingest actions

### Structured Ingestion Output

Each candidate chunk should produce structured output:

```json
{
  "store": true,
  "kind": "architecture",
  "confidence": 0.93,
  "durability": "cross_session",
  "salient": true,
  "summary": "Helioy uses a three-layer orchestration architecture: orchestrator, coordinator, and expert agents.",
  "tags": ["helioy", "architecture", "orchestration"],
  "reason": "Durable architectural fact likely useful across future sessions.",
  "supersedes": []
}
```

Minimum required fields:

- `store`
- `kind`
- `confidence`
- `durability`
- `salient`
- `summary`

### Initial Memory Kinds

- `fact`
- `decision`
- `preference`
- `architecture`
- `project_summary`
- `workflow_state`
- `todo`
- `question`
- `noise`
- `duplicate`

### Initial Durability Levels

- `ephemeral`
- `session`
- `cross_session`

### Storage Recommendation

Use a dual-layer model:

1. **Raw source layer**
   Optional but recommended for debugging, auditing, and future reprocessing.

2. **Curated indexed layer**
   The only layer used for normal recall.

This preserves reversibility without letting raw sludge dominate retrieval.

### Assistant Output Policy

Assistant output is a high-risk input source.

Default policy:

- do not index raw assistant completions directly
- pass them through ingestion curation first
- store only if they contain durable, high-value content

This breaks the self-reinforcing assistant-sludge loop.

### Fresh Database Recommendation

This proposal assumes a fresh `brain.db`.

Reason:

- current stored memory likely contains mixed-quality legacy residue
- cleaning a noisy existing corpus is harder than establishing a clean policy from day one

Migration can happen later by reprocessing exports through the new ingestion layer.

## Layer 2: Weighted Retrieval Scoring

### Goal

Make recalled candidates compete on usefulness, not just activation.

### Why This Matters

Even with curated ingestion, multiple candidates may still be relevant. The system needs a richer ranking model than activation score alone.

The transferable insight from systems like Sapling is:

**Introduce named, composable scoring signals instead of one opaque score.**

### Proposed Retrieval Score

Each candidate memory unit gets a composite score:

`final_score = normalized(weighted sum of signals)`

### Initial Scoring Signals

#### 1. Activation relevance

From AM's existing geometric retrieval:

- lexical activation
- interference
- manifold dynamics

This remains essential, but is no longer sufficient.

#### 2. Source trust prior

Suggested ranking:

1. conscious memory
2. uploaded document
3. architecture / spec memory
4. user-authored conversation memory
5. assistant-authored conversation memory
6. review / critique note
7. operational chatter
8. unknown

#### 3. Durability prior

`cross_session > session > ephemeral`

#### 4. Question-type fit

Different questions want different evidence.

Examples:

- project synopsis questions should favor architecture, facts, and summaries
- workflow questions should favor recent workflow-state memory
- memory reflection questions can tolerate broader subconscious material

#### 5. Recency

Useful, but not dominant.

Recency should matter more for workflow questions and less for identity or architecture questions.

#### 6. Anti-sludge penalty

Down-rank content that looks like:

- hedged assistant filler
- malformed summaries
- UI copy
- coordination residue
- prompt boilerplate
- half-finished list fragments

### Candidate Types

Candidates should be treated as semantic memory units, not raw blobs.

Good candidate examples:

- normalized fact summary
- architecture memory
- durable user preference
- project decision
- document-derived finding

Bad candidate examples:

- "Based on the provided information..."
- "Starter prompts..."
- "Close memory explorer"
- "Can you check again..."

### Retrieval Output

Retrieval should ideally produce:

- scored memory units
- source metadata
- trust metadata
- reason for inclusion
- compact excerpts

This should become the basis for prompt evidence selection.

## Layer 3: Zone-Based Prompt Budgeting

### Goal

Make prompt construction explicit, bounded, and explainable.

### Principle

A fixed token window should be partitioned intentionally across concerns.

Without zones, weak evidence can consume too much space and high-value evidence can be crowded out.

### Proposed Zones

#### 1. System behavior zone

Contains:

- stable role instructions
- markdown formatting contract
- rules for handling uncertainty
- rules for salience tagging

This zone should be small and stable.

#### 2. Memory evidence zone

Contains:

- selected conscious evidence
- selected subconscious evidence
- selected novel connections
- optionally a compact synthesized recap

This is the most important budgeted zone.

#### 3. Active conversation zone

Contains:

- recent user / assistant turns needed for continuity

This should preserve conversational flow without overwhelming evidence quality.

#### 4. Headroom zone

Reserved for:

- model reasoning space
- response generation
- safety against overflow

### Budgeting Rules

Initial policy:

- system zone: small fixed allocation
- evidence zone: capped but expandable if evidence quality is high
- active conversation zone: recent-turn bounded
- headroom: large reserved share

Unused budget should redistribute according to rules, not ad hoc.

### Evidence Formatting

The evidence zone should be a first-class message, conceptually:

`AM_MEMORY_CONTEXT`

This message should contain:

- compact selected evidence only
- provenance
- source class
- score or trust hints
- short excerpt

It should not contain:

- large raw dumps
- malformed transcript fragments
- uncurated old assistant sludge

## Question-Aware Selection Policies

### Identity / Synopsis Questions

Examples:

- "Tell me about Helioy"
- "What is this project?"

Prefer:

- conscious memory
- architecture memories
- project summaries
- document-derived facts

Avoid:

- prior assistant summaries
- UI review fragments
- workflow chatter

### Workflow / Recent Activity Questions

Examples:

- "What have I been working on this week?"
- "Where did we leave off?"

Prefer:

- recent workflow-state memories
- recent user-authored conversation summaries
- task decisions

### Reflection / Memory Questions

Examples:

- "What patterns keep showing up?"
- "What do you remember about X?"

Allow broader subconscious material, but still apply anti-sludge penalties.

## Write-Back Policy

The answer-generation loop should also become curated.

### Current problem

If raw assistant completions are re-ingested directly, quality can decay over time.

### Proposed policy

After answer generation:

1. Extract salient tags as before.
2. Run response content through the same ingestion curation logic.
3. Store only normalized, memory-worthy takeaways in the indexed layer.

This keeps AM self-improving without becoming self-poisoning.

## Observability

This system must be inspectable.

For each answer, log:

- retrieved candidates
- selected evidence
- discarded candidates
- scoring breakdown
- budget allocation
- final evidence payload size

If the system is not inspectable, quality tuning will devolve into guesswork.

## Proposed Implementation Plan

### Phase 1: Prompt discipline

- keep stable system prompt
- use a first-class `AM_MEMORY_CONTEXT` message
- enforce markdown output

This is already partially underway.

### Phase 2: Curated ingestion for chat

- ingestion LLM for user/assistant exchanges
- index normalized memory only
- fresh `brain.db`

### Phase 3: Retrieval scoring

- add named scoring signals
- source priors
- durability priors
- anti-sludge penalties
- question-type fit

### Phase 4: Prompt zones

- explicit token budgets
- redistribution rules
- per-zone caps

### Phase 5: Full-source integration

- apply curated ingestion to:
  - docs
  - transcript sync
  - imports

### Phase 6: Evaluation harness

Build deterministic scenarios to test:

- recall quality
- evidence quality
- answer quality
- prompt budget behavior

This should become regression-testable, not taste-based.

## Evaluation Criteria

The architecture is successful if:

- a fresh `brain.db` remains high-signal after extended use
- synopsis questions surface durable project facts, not malformed prior completions
- workflow questions still preserve continuity
- conscious memory consistently outranks generic subconscious noise
- prompt evidence is visibly shorter, cleaner, and more trustworthy
- final answer quality improves in benchmark prompts

## Risks

### Over-filtering

Important information may be discarded too early.

Mitigation:

- conservative thresholds
- optional raw source retention
- manual promotion path

### Editorial bias from ingestion LLM

The model may over-shape memory or miss subtle importance.

Mitigation:

- structured outputs
- reviewable decisions
- model/prompt iteration

### Cost and latency

Curated ingestion adds model calls.

Mitigation:

- lightweight ingestion model
- batch processing
- selective gating

### Architecture complexity

This is a more serious pipeline than the current one.

Mitigation:

- build in phases
- keep interfaces typed
- expose intermediate artifacts for debugging

## Recommendation

Adopt this architecture direction.

Not because AM retrieval is failing, but because retrieval alone cannot guarantee high-signal memory behavior.

The clean long-term design is:

- **curate what enters memory**
- **score what gets recalled**
- **budget what reaches the model**

That is the path from "interesting geometric memory engine" to "trustworthy memory layer for long-running AI work."

