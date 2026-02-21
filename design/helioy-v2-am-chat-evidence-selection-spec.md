# AM Chat Evidence Selection Spec

Date: 2026-03-11
Status: Proposal
Owner: Codex

## Summary

AM retrieval is working, but chat answer quality degrades because raw recalled memory is passed to the LLM with too little curation. The system currently treats "recalled" as if it were "prompt-ready". Those are different states.

This spec proposes a dedicated evidence-selection layer between AM retrieval and LLM generation. The goal is to preserve broad memory storage while making only high-quality, question-appropriate evidence visible to the LLM.

## Problem

Current failure mode:

1. AM stores broad conversational and document memory.
2. `am_query` returns relevant recall candidates.
3. Chat passes recalled material into generation with weak filtering.
4. The LLM synthesizes from noisy evidence:
   - prior low-quality assistant answers
   - UX review fragments
   - operational chatter
   - partially relevant task notes

Observed result:

- retrieval can be mechanically correct
- answer quality can still be poor
- subconscious recall is over-trusted
- prior assistant sludge can become self-reinforcing evidence

This is not primarily a retrieval failure. It is an evidence-selection failure.

## Goals

- Preserve AM as a broad memory system.
- Improve final chat answer quality.
- Prevent low-quality prior assistant outputs from dominating synthesis.
- Favor durable project knowledge over transient workflow chatter.
- Keep the original DAE interaction loop intact:
  - retrieve memory
  - present memory as evidence
  - generate answer
  - write answer back
  - promote salient insights

## Non-Goals

- Replacing the geometric memory engine.
- Removing subconscious recall entirely.
- Turning AM into a document-only RAG system.
- Perfect truth validation.

## Core Principle

Separate three things:

1. Storage
   Broad memory can be stored.

2. Retrieval
   Relevant candidates can be recalled.

3. Evidence selection
   Only the best candidates should be shown to the LLM for answer synthesis.

The system currently has storage and retrieval. It needs explicit evidence selection.

## Proposed Architecture

### Current

`am_query -> raw recall/context -> /api/chat -> LLM`

### Proposed

`am_query -> recall candidates -> evidence selection -> AM_MEMORY_CONTEXT -> LLM`

The `AM_MEMORY_CONTEXT` message should be built from selected evidence, not from unfiltered recalled text.

## Evidence Model

Each recalled item should be classified by:

- source class
- trust level
- question relevance
- memory category
- prompt suitability

### Source Classes

Use these initial source classes:

- conscious-memory
- uploaded-document
- spec-or-architecture-note
- user-authored conversation
- assistant-authored conversation
- operational chatter
- review or critique note
- unknown

### Trust Defaults

Rank from highest to lowest:

1. conscious-memory
2. uploaded-document
3. spec-or-architecture-note
4. user-authored conversation
5. assistant-authored conversation
6. review or critique note
7. operational chatter
8. unknown

Notes:

- Conscious memory is highest because it is explicitly promoted.
- Assistant-authored conversation is not banned, but must be treated as lower-trust evidence by default.
- Operational chatter should almost never reach the LLM for synthesis unless the question is explicitly about workflow.

## Evidence Selection Policy

For each chat question:

1. Run `am_query`.
2. Build a candidate set from:
   - conscious
   - subconscious
   - novel
3. Score each candidate using:
   - AM recall score
   - source-class prior
   - text cleanliness
   - question-match strength
   - anti-sludge penalty
4. Select a compact evidence set for the LLM.

### Anti-Sludge Penalties

Down-rank candidates containing signs of:

- previous assistant hedging
- malformed summaries
- meta-instructions
- UI copy fragments
- task boilerplate
- partial list items
- obviously unrelated operational notes

Examples:

- "Based on the provided information..."
- "Can you check again..."
- "Starter prompts"
- "Boost/demote"
- "Close memory explorer"

These are valid stored memories, but poor synthesis evidence for most questions.

## Prompt Construction

### System Prompt

The system prompt should be stable and behavioral only:

- answer using supplied AM memory context
- format response in clean markdown
- do not present low-confidence fragments as settled fact
- acknowledge uncertainty when evidence is partial
- use `<salient>` tags selectively for durable insights

### Evidence Message

Inject a dedicated message named conceptually:

`AM_MEMORY_CONTEXT`

It should include only selected evidence:

- Conscious
- Subconscious
- Novel
- Optional synthesized recap if useful

Each item should be compact and provenance-bearing:

- seed or title
- source class
- score
- short excerpt
- id

### User Message

The user message remains only the user's question.

## Selection Rules By Question Type

### Identity / Synopsis Questions

Examples:

- "Tell me about Helioy"
- "What is this project?"

Prefer:

- conscious memory
- project specs
- architecture notes
- uploaded docs

Avoid:

- prior assistant summaries
- UX review fragments
- operational workflow chatter

### Workflow / Recent Activity Questions

Examples:

- "What have I been working on?"
- "What changed this week?"

Prefer:

- recent conversation memory
- task execution notes
- recent episodes

### Reflection / Memory Questions

Examples:

- "What patterns keep showing up?"
- "What do you remember about X?"

Allow more subconscious material, but still trim sludge.

## First Iteration Implementation

### Phase 1

Add lightweight heuristics only.

- classify source from episode name / source metadata
- penalize assistant-generated prose patterns
- penalize list-fragment and UI-copy patterns
- cap subconscious evidence count aggressively
- prefer conscious + doc-like memory for synopsis questions

### Phase 2

Promote richer source metadata into stored episodes and neighborhoods.

Potential fields:

- source_type
- authored_by
- origin_session
- imported_from
- durable_hint

### Phase 3

Add feedback loop:

- user signals "helpful / not relevant"
- selected evidence weights adjust over time

## Acceptance Criteria

- Asking "Tell me about Helioy" should no longer surface prior bad assistant summaries as primary evidence.
- `AM_MEMORY_CONTEXT` should be visibly shorter and higher-quality than raw `am_query.context`.
- Conscious memories should consistently outrank transient chat sludge.
- Questions about current workflow should still be able to use conversational memory.
- The final answer should improve without reducing AM's ability to remember broadly.

## Risks

- Over-filtering may hide useful latent connections.
- Simple heuristics may misclassify some high-value assistant-authored content.
- Too much prompt compaction may erase nuance.

Mitigation:

- Keep storage broad.
- Make evidence selection explicit and inspectable.
- Log selected vs discarded candidates for evaluation.

## Open Questions

- Should assistant-authored content be excluded by default for synopsis-style questions?
- Should conscious memories be allowed to supersede low-quality subconscious evidence automatically?
- Should document uploads be treated as near-canonical evidence?
- Do we want per-question-type templates, or one generic selector with feature flags?

## Recommendation

Implement Phase 1 first.

That gives the highest leverage with the least architectural risk:

- no rewrite of AM core
- no loss of memory breadth
- immediate quality improvement in chat synthesis

