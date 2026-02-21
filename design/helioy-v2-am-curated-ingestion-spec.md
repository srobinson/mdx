# AM Curated Ingestion Spec

Date: 2026-03-11
Status: Proposal
Owner: Codex

## Summary

This proposal changes AM from a broad raw-memory system into a curated-memory system.

Instead of storing most incoming text directly and trying to fix quality at retrieval time, all incoming data should first pass through an LLM ingestion step. That ingestion step decides:

- whether the content is worth storing
- what type of memory it is
- how durable it is
- whether it should become conscious memory
- what normalized memory text should actually be indexed

The goal is simple:

- start from a fresh `brain.db`
- keep the indexed memory substrate clean
- prevent low-value assistant sludge, workflow chatter, and malformed summaries from ever becoming first-class memory

## Problem

Current failure mode:

- AM stores broad conversational and document memory
- bad or low-value assistant outputs can be re-ingested
- operational chatter can become recall candidates
- later retrieval has to sort signal from too much noise

This causes a structural quality problem:

- if the corpus is dirty, retrieval cannot stay clean for long

In short:

- garbage in becomes memory
- memory becomes future prompt context
- bad memory compounds over time

## Design Direction

Move quality control to ingestion, not just retrieval.

### Current model

`input -> store -> retrieve -> filter for generation`

### Proposed model

`input -> LLM ingestion classifier/summarizer -> curated memory store -> retrieve`

This changes AM from:

- memory of everything that happened

to:

- memory of what was worth retaining from what happened

## Goals

- Maintain a clean indexed memory base.
- Prevent low-value data from entering the recall path.
- Preserve durable insights, facts, decisions, preferences, and useful project knowledge.
- Reduce self-reinforcing assistant-output sludge.
- Make future retrieval simpler and higher quality.

## Non-Goals

- Perfectly preserving all raw history in the recall index.
- Using AM as a verbatim transcript store.
- Replacing the geometric memory model.
- Removing retrieval-time ranking entirely.

## Core Principle

Not all text deserves to become memory.

AM should index curated memory objects, not raw conversational exhaust.

## Fresh Start

This proposal assumes a fresh `brain.db`.

Reason:

- the current corpus likely contains mixed-quality conversational residue
- retroactively cleaning stored memory is harder and noisier than starting with a new ingestion policy
- a fresh database gives a clean baseline for evaluating the new system

Optional migration path:

- export old state
- re-process old memories through the ingestion classifier later if needed

## Ingestion Pipeline

Every input path should use the same ingestion pipeline:

- user/assistant exchange buffering
- document upload
- transcript sync/import
- explicit `am_ingest`

### Proposed pipeline

1. Receive raw input.
2. Chunk it into candidate units.
3. Pass each unit through an ingestion LLM.
4. Receive structured judgment.
5. Store only curated memory objects in the main recall index.
6. Optionally store raw source separately for audit/debug.

## Ingestion LLM Responsibilities

For each candidate chunk, the ingestion model should determine:

- Is this worth storing?
- What kind of memory is it?
- Is it durable or ephemeral?
- Is it novel or redundant?
- Should it become conscious memory?
- What is the normalized memory text?

## Proposed Structured Output

Each ingestion result should look like:

```json
{
  "store": true,
  "kind": "decision",
  "confidence": 0.92,
  "durability": "cross_session",
  "salient": true,
  "summary": "Helioy uses a three-layer orchestration model: orchestrator, coordinator, and expert agents.",
  "tags": ["helioy", "architecture", "orchestration"],
  "reason": "Durable architecture fact likely useful in future sessions.",
  "supersedes": []
}
```

Minimum fields:

- `store`: boolean
- `kind`: string enum
- `confidence`: number
- `durability`: string enum
- `salient`: boolean
- `summary`: string

Optional fields:

- `reason`
- `tags`
- `supersedes`
- `source_class`

## Memory Kinds

Initial kind set:

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

Policy:

- `noise` is not stored
- `duplicate` is only stored if it materially strengthens an existing memory
- `workflow_state` is stored with lower durability by default

## Durability Levels

Initial durability set:

- `ephemeral`
- `session`
- `cross_session`

Meaning:

- `ephemeral`
  not worth indexing for future recall
- `session`
  may matter during the current working arc, but should decay faster
- `cross_session`
  durable memory suitable for long-term recall

## Storage Model

### Recommended model: dual-layer

Use two layers:

1. Raw source layer
   Optional but recommended
   Stores original content for debugging, audits, and future reprocessing

2. Curated memory layer
   The only layer indexed for normal AM recall

This avoids the trap of permanently losing context while still keeping the recall substrate clean.

### Strict model: curated only

Alternative:

- store only curated summaries and promoted memories

Pros:

- simpler
- cleaner

Cons:

- loses auditability
- harder to improve ingestion policy later

Recommendation:

- keep raw storage if the engineering overhead is acceptable
- otherwise still keep curated memory as the only indexed recall path

## Prompting the Ingestion LLM

The ingestion model should be explicitly editorial, not conversational.

Its job is not to answer the user.
Its job is to decide whether the input deserves future memory.

### Ingestion prompt responsibilities

- classify importance
- compress to durable wording
- reject noise
- avoid parroting malformed input
- avoid preserving weak assistant hedging unless the content is genuinely valuable

### Important rule

The ingestion model should produce normalized memory text, not raw transcript text.

That means:

- convert sloppy dialogue into a durable statement when appropriate
- avoid storing boilerplate phrases
- avoid preserving "Based on the provided information..." style filler

## Treatment of Assistant Output

Assistant output is the highest-risk source of contamination.

Default policy:

- do not index raw assistant completions directly
- pass them through the ingestion gate
- store only if they contain durable, high-value information

Assistant output should usually be:

- rejected as `noise`
- stored as a normalized summary
- or promoted to conscious memory if explicitly salient

This breaks the self-reinforcing sludge loop.

## Treatment of User Input

User input should also be curated, not blindly stored.

Examples:

- durable user preference: store
- architectural decision stated by user: store
- transient command like "check this again": probably do not store
- task-local chatter: maybe `session`, not `cross_session`

## Retrieval Implications

If ingestion is curated, retrieval becomes simpler and better:

- fewer noisy candidates
- less need for heavy downstream filtering
- more consistent subconscious recall quality
- lower risk of prompt contamination

Subconscious recall should then mean:

- unpinned but memory-worthy curated content

not:

- arbitrary old chat residue

## Conscious Memory

Conscious memory remains stricter than subconscious memory.

Suggested policy:

- only ingestion items marked `salient=true` enter conscious memory
- conscious memory should be durable by definition
- conscious memories may supersede older weaker versions

## First Iteration Plan

### Phase 1: ingestion gate for chat

Apply the ingestion LLM to:

- buffered user/assistant exchanges

Only curated output enters memory episodes.

### Phase 2: ingestion gate for docs and sync

Apply the same ingestion policy to:

- document upload
- transcript sync
- import flows

### Phase 3: raw-vs-curated dual storage

Add optional raw storage for:

- audit
- reprocessing
- debugging ingestion errors

### Phase 4: policy tuning

Refine thresholds:

- confidence threshold
- durability rules
- source-type rules
- duplicate suppression

## Open Questions

- Should raw source be stored at all?
- Should `workflow_state` be indexed or kept in a separate short-lived lane?
- Which model should run ingestion: cheap and fast, or slower but more reliable?
- Should user-confirmed feedback upgrade low-confidence memories later?
- Should imported legacy memories be forced through re-curation before indexing?

## Acceptance Criteria

- Starting from a fresh `brain.db`, low-value chat sludge should no longer dominate recall.
- Prior assistant answers should not become first-class evidence unless explicitly curated into durable memory.
- Asking a project synopsis question should surface normalized project facts, not malformed prior completions.
- Conscious and subconscious recall should both feel cleaner and more trustworthy after several sessions.
- The memory corpus should remain inspectable and explainable.

## Risks

- Over-filtering may discard useful latent context.
- LLM editorial mistakes may suppress important information.
- Ingestion adds cost and latency.
- A poor ingestion prompt could bias the entire memory base.

## Risk Mitigations

- Start with conservative thresholds.
- Log every ingestion decision.
- Keep optional raw source for reprocessing.
- Make ingestion output inspectable in tooling.
- Allow manual override or promotion of missed memories.

## Recommendation

Adopt curated ingestion as the primary direction.

If the product goal is high-signal memory rather than exhaustive transcript retention, this is the cleaner architecture.

Retrieval-time filtering is still useful, but it should become a secondary refinement layer, not the main defense against bad memory.

