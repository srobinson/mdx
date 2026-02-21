# AM High-Signal Memory Build Plan

Date: 2026-03-11
Status: Execution Plan
Depends on: `am-high-signal-memory-architecture-proposal.md`

## Purpose

This document converts the high-signal memory architecture proposal into an implementation plan.

It is organized by:

1. schema changes
2. backend changes
3. prompt-builder changes
4. rollout and migration
5. evaluation

The build strategy is phased so quality improves early without forcing a risky full rewrite.

## Success Criteria

The project is successful when:

- a fresh `brain.db` remains high-signal after normal use
- bad assistant summaries no longer become dominant recall evidence
- synopsis questions retrieve durable project knowledge
- workflow questions still preserve continuity
- prompt evidence is inspectable, compact, and ranked
- regression tests can detect quality drift

## Phase 0: Ground Rules

### Decisions

- Start with a fresh `brain.db` for the new architecture.
- Keep the geometric recall engine.
- Add an ingestion curation layer before indexed storage.
- Add a scored evidence-selection layer before prompt assembly.
- Preserve the current `AM_MEMORY_CONTEXT` message approach.

### Deliverables

- fresh dev database
- feature flag for curated ingestion
- logging around all ingestion and evidence-selection steps

## Phase 1: Schema and Data Model

### Goal

Introduce the minimum metadata needed to support curated ingestion and trust-aware retrieval.

### New Concepts

Add the following conceptual entities:

- `RawSourceRecord`
- `CuratedMemoryRecord`
- `IngestionDecision`

### Minimum Curated Memory Fields

For each indexed memory unit:

- `id`
- `summary`
- `kind`
- `durability`
- `source_class`
- `confidence`
- `is_salient`
- `created_at`
- `source_ref`
- `tags`
- `supersedes`

### Suggested Enums

#### `kind`

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

#### `durability`

- `ephemeral`
- `session`
- `cross_session`

#### `source_class`

- `conscious_memory`
- `uploaded_document`
- `spec_note`
- `user_conversation`
- `assistant_conversation`
- `review_note`
- `operational_chatter`
- `imported_history`
- `unknown`

### Storage Strategy

Recommended:

- retain raw source separately
- index only curated memory

That means:

- raw imports, transcripts, and exchanges can still be audited
- recall only operates on curated summaries

### Files / Modules Likely Affected

- `am_store` schema and persistence layer
- `am_core` memory structs if metadata needs to travel into retrieval
- `crates/am-cli/src/server.rs`
- import/export serialization paths

### Deliverables

- schema migration plan
- updated Rust structs
- updated export/import shape

## Phase 2: Ingestion Curation Pipeline

### Goal

Ensure incoming data is evaluated before entering the indexed memory layer.

### Scope

Start with chat exchange ingestion only.

Apply the curation step to:

- buffered user/assistant exchange write-back

Do not apply to document upload or sync yet. Keep scope narrow first.

### Pipeline

1. Receive user/assistant exchange.
2. Build ingestion prompt.
3. Call ingestion LLM.
4. Parse structured result.
5. If `store=true`, write curated summary into indexed memory.
6. If `salient=true`, promote into conscious memory.
7. Optionally store raw exchange separately.

### Ingestion Prompt Requirements

The ingestion model must:

- decide if content is worth remembering
- normalize the memory into durable wording
- classify kind, durability, and source
- reject noise
- avoid storing boilerplate or malformed assistant prose

### Output Contract

Define a typed output schema in Rust:

- `store: bool`
- `kind: MemoryKind`
- `durability: Durability`
- `confidence: f32`
- `salient: bool`
- `summary: String`
- `tags: Vec<String>`
- `reason: Option<String>`
- `supersedes: Vec<String>`

### Backend Changes

Add a curation service or module:

- `ingestion_curator.rs` or equivalent

Responsibilities:

- build ingestion prompt
- call model
- validate response
- apply fallback behavior if curation fails

### Failure Policy

If ingestion curation fails:

- do not blindly write raw assistant output into indexed memory
- either:
  - skip storage
  - or place raw source in non-indexed storage only

This failure policy matters.

### Deliverables

- typed ingestion curator
- prompt template
- structured parser/validator
- feature flag to enable curated exchange storage

## Phase 3: Retrieval Scoring Layer

### Goal

Rank recalled candidates using richer signals than activation alone.

### Initial Scoring Signals

Implement named, weighted signals:

- `activation_signal`
- `source_prior_signal`
- `durability_signal`
- `question_fit_signal`
- `recency_signal`
- `anti_sludge_signal`

### Initial Weighting Proposal

Start simple:

- activation: 0.35
- source prior: 0.20
- question fit: 0.20
- durability: 0.10
- recency: 0.10
- anti-sludge penalty: subtractive modifier

These are placeholders, not final truth.

### Question Types

Introduce a lightweight question classifier:

- `synopsis`
- `workflow`
- `reflection`
- `lookup`
- `unknown`

This can be heuristic at first:

- "tell me about", "what is", "overview" => synopsis
- "this week", "recently", "working on" => workflow
- "patterns", "remember", "recall" => reflection

### Sludge Heuristics

Down-rank text matching patterns such as:

- "Based on the provided information"
- "I can offer the following"
- UI copy fragments
- partial bullet scaffolding
- coordination chatter

### Module Boundary

Add a scoring layer after `am_query` candidate recall and before prompt evidence assembly.

Possible module:

- `evidence_selector.rs`

### Deliverables

- named signal functions
- normalized scoring output
- logs showing selected and discarded candidates

## Phase 4: Prompt Builder and Budget Zones

### Goal

Make prompt construction explicit and inspectable.

### Zones

Split prompt assembly into:

- `system_zone`
- `memory_evidence_zone`
- `conversation_zone`
- `headroom_zone`

### Initial Budget Proposal

Example only:

- system: 10%
- memory evidence: 25%
- conversation: 20%
- headroom: 45%

These should be configurable, not hard-coded forever.

### Prompt Builder Changes

Refactor `/api/chat` prompt assembly so:

- system prompt remains stable
- `AM_MEMORY_CONTEXT` is built only from selected evidence
- recent conversation is separately bounded
- evidence truncation is source-aware

### Source-Aware Formatting Rules

- conscious memory: allow richer formatting
- document/spec memory: medium excerpt length
- assistant-derived memory: very short excerpt or summary only
- operational chatter: excluded by default

### Deliverables

- prompt budget config
- builder that returns budget diagnostics
- structured evidence sections with provenance

## Phase 5: Expand Curated Ingestion to Other Sources

### Goal

Apply the same quality discipline to all ingestion paths.

### Add curation to:

- document upload
- transcript sync
- import flows
- explicit ingest endpoint

### Additional Requirement

Document uploads may need chunk-level curation rather than exchange-level curation.

Recommended strategy:

- chunk raw doc
- curate per chunk
- index only accepted summaries

### Deliverables

- unified ingestion interface
- source-specific chunking rules

## Phase 6: Inspectability and Tooling

### Goal

Make the pipeline debuggable.

### Required Debug Surfaces

For a given answer, inspect:

- raw retrieval candidates
- scoring breakdown
- selected evidence
- discarded evidence
- prompt zone sizes
- final `AM_MEMORY_CONTEXT`
- ingestion decisions for write-back

### UI Possibility

Later, the chat UI can expose:

- "why this memory was selected"
- "why this memory was ignored"

Not required for first implementation, but the backend should support it.

### Deliverables

- structured logs
- optional debug endpoints or inspect commands

## Phase 7: Evaluation Harness

### Goal

Make quality regression-testable.

### Build a benchmark suite with fixed scenarios

At minimum:

- project synopsis question
- workflow continuity question
- preference recall question
- architecture lookup question
- noisy conversation poisoning scenario

### Evaluate

For each scenario, compare:

- selected evidence quality
- final answer quality
- evidence compactness
- presence of sludge

### Metrics

- irrelevant evidence count
- assistant-sludge inclusion count
- conscious memory inclusion rate
- synopsis correctness
- workflow continuity quality

### Deliverables

- fixture corpus
- deterministic evaluation runner
- baseline vs new-pipeline comparison

## Rollout Plan

### Step 1

Land schema additions behind flags.

### Step 2

Introduce curated exchange ingestion with fresh dev database.

### Step 3

Add evidence selector and logging.

### Step 4

Switch `/api/chat` to use selected evidence only.

### Step 5

Expand curated ingestion to docs and sync.

### Step 6

Run benchmark scenarios and tune weights.

## Migration Strategy

### Recommended

- Do not migrate existing noisy `brain.db` into the new indexed path by default.
- Start clean.
- Keep export tooling for optional reprocessing later.

### Optional Legacy Import Mode

Allow:

- import old raw memory
- re-run ingestion curation over it
- only accepted curated memories enter the new index

## Risks and Safeguards

### Risk: Over-filtering

Safeguard:

- conservative thresholds
- raw-source retention
- manual promotion path

### Risk: Ingestion model drift

Safeguard:

- strict structured output validation
- benchmark suite
- inspectability

### Risk: Complexity

Safeguard:

- phase the work
- keep interfaces narrow
- add one layer at a time

## Recommended Build Order

If we want the highest leverage path:

1. Fresh DB and schema metadata
2. Curated exchange ingestion
3. Retrieval scoring layer
4. Prompt budget zones
5. Expanded source ingestion
6. Benchmark harness

## Immediate Next Tasks

### Backend

- define metadata enums and structs
- add ingestion curator module
- add curated exchange storage path
- add evidence selector module

### Chat

- keep stable system prompt
- build `AM_MEMORY_CONTEXT` from selected evidence only
- expose debug info during development

### Ops

- add feature flags
- define fresh-db startup path for dev
- add evaluation fixtures

