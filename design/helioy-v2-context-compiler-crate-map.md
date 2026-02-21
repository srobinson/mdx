# Helioy Context Compiler Crate Map

Date: 2026-03-11
Status: Proposed module layout
Author: Codex

## Summary

This document proposes a concrete Rust crate and module layout for the Helioy context compiler.

The goal is to make the earlier architectural direction implementable:

- `fmm` remains a code retrieval engine
- `mdcontext` becomes a Rust document retrieval engine
- a new context compiler sits above both
- `nancy` / `nancyr` consumes the compiler output

This layout is intentionally modular.
Retrieval, scoring, budgeting, compaction, and rendering should be independently testable.

## Design Goals

- Keep retrieval separate from compaction.
- Make scoring signals explicit and composable.
- Support multiple source adapters.
- Make token budgeting inspectable.
- Allow deterministic evaluation fixtures.
- Keep orchestration concerns outside the compiler core.

## Top-Level Shape

Recommended new crates:

- `helioy-context-core`
- `helioy-context-adapters`
- `helioy-context-compiler`
- `helioy-context-eval`

Optional later:

- `helioy-context-mcp`

## Crate Responsibilities

### `helioy-context-core`

Purpose:

- shared types
- core traits
- scoring abstractions
- budget abstractions
- serialization-safe intermediate representations

This crate must have minimal dependencies and become the stable vocabulary of the compiler.

#### Suggested modules

- `types`
- `source`
- `candidate`
- `score`
- `budget`
- `fragment`
- `render`
- `trace`

#### Key types

- `ContextSource`
- `ContextCandidate`
- `ContextFragment`
- `ScoreSignal`
- `ScoreBreakdown`
- `BudgetZone`
- `BudgetPlan`
- `CompiledContext`
- `CompilerTrace`

### `helioy-context-adapters`

Purpose:

- convert retrieval outputs from source systems into compiler candidates

This crate should not own scoring or compaction logic.
It should only translate source-native outputs into the shared context-core model.

#### Suggested modules

- `fmm`
- `mdcontext`
- `recent`
- `am` (optional and off by default)

#### Adapter outputs

Each adapter should produce a normalized stream or vector of `ContextCandidate`.

#### Initial adapters

##### `fmm` adapter

Consumes:

- export lookups
- file outlines
- dependency results
- search results

Produces candidates like:

- `code_structure`
- `symbol_definition`
- `dependency_context`
- `blast_radius_context`

##### `mdcontext` adapter

Consumes:

- section search results
- context summaries
- ranked document sections

Produces candidates like:

- `document_section`
- `document_summary`
- `api_reference_excerpt`

##### `recent` adapter

Consumes:

- recent task state
- turn history
- tool events

Produces candidates like:

- `recent_decision`
- `active_task_state`
- `recent_failure`

This is likely the main place Sapling-inspired ideas will first land.

##### `am` adapter

Optional.

Should be disabled by default for tactical compaction until the philosophical boundary is clearer.

### `helioy-context-compiler`

Purpose:

- group candidates
- score them
- allocate budget
- compress content
- emit final compiled working context

This is the heart of the system.

#### Suggested modules

- `pipeline`
- `grouping`
- `signals`
- `scoring`
- `budgeting`
- `compression`
- `selection`
- `renderer`
- `diagnostics`

#### Core pipeline

Proposed stages:

1. normalize
2. group
3. score
4. budget
5. compress
6. select
7. render

Each stage should take and return typed structures, not mutate arbitrary bags of state.

### `helioy-context-eval`

Purpose:

- deterministic scenario testing
- regression harness
- fixture loading
- before/after comparisons

This should make context quality measurable.

#### Suggested modules

- `fixtures`
- `scenarios`
- `runner`
- `assertions`
- `reports`

## Core Types

### `ContextSource`

Represents where a candidate came from.

Suggested fields:

- `kind`
- `origin_id`
- `path`
- `timestamp`
- `trust_class`

### `ContextCandidate`

A raw retrieved candidate before scoring.

Suggested fields:

- `id`
- `source`
- `kind`
- `title`
- `content`
- `token_estimate`
- `metadata`
- `provenance`

### `ContextFragment`

A post-compression unit eligible for final prompt assembly.

Suggested fields:

- `id`
- `candidate_id`
- `rendered_text`
- `tokens`
- `compression_mode`
- `score_breakdown`

### `ScoreSignal`

Named signal interface.

Suggested trait:

- `name()`
- `weight()`
- `compute(candidate, query, state) -> f32`

### `BudgetZone`

Represents a partition of available context space.

Suggested zones:

- `instructions`
- `retrieved_evidence`
- `recent_state`
- `headroom`

### `CompiledContext`

Final output to orchestration.

Suggested fields:

- `system_text`
- `evidence_text`
- `recent_text`
- `budget_report`
- `trace`

## Pipeline Stages

### 1. Normalize

Convert all adapters into common candidate shape.

Input:

- source-specific retrieval outputs

Output:

- `Vec<ContextCandidate>`

### 2. Group

Group related candidates into larger semantic units where useful.

Examples:

- multiple doc sections from one file
- code symbol + file outline
- recent tool sequence from one task

This is where Sapling-like "operation" ideas may be adapted, but not copied literally.

### 3. Score

Apply named signals.

Initial signals:

- recency
- source_overlap
- file_overlap
- dependency_relevance
- source_trust
- outcome_significance
- candidate_kind_prior

Output:

- scored candidates with full breakdown

### 4. Budget

Allocate token budgets by zone and optionally per group.

Responsibilities:

- min/max per zone
- surplus redistribution
- per-group caps
- headroom preservation

### 5. Compress

Apply source-aware compression.

Examples:

- doc section summary
- code outline compaction
- tool-output truncation
- recent-state summarization

### 6. Select

Choose the final fragments that fit within budget.

This should be transparent and traceable:

- selected
- compressed
- excluded
- why

### 7. Render

Assemble final prompt-ready working context.

Output should be:

- stable
- inspectable
- source-aware
- easy for `nancy` to consume

## Suggested Trait Boundaries

### Adapter trait

```rust
trait CandidateAdapter {
    fn collect(&self, request: &ContextRequest) -> Result<Vec<ContextCandidate>, AdapterError>;
}
```

### Scoring signal trait

```rust
trait EvalSignal {
    fn name(&self) -> &'static str;
    fn weight(&self) -> f32;
    fn score(&self, candidate: &ContextCandidate, ctx: &EvalContext) -> f32;
}
```

### Compressor trait

```rust
trait Compressor {
    fn compress(&self, candidate: &ContextCandidate, budget: usize) -> ContextFragment;
}
```

### Renderer trait

```rust
trait ContextRenderer {
    fn render(&self, compiled: &CompiledContext) -> RenderedContext;
}
```

## Integration with `mdcontext`

If `mdcontext` is rewritten in Rust, it should remain its own crate or package.

Do not bury document retrieval inside the compiler.

Recommended boundary:

- `mdcontext` exposes a retrieval API
- the `mdcontext` adapter consumes that API
- the compiler remains agnostic about document internals

This keeps the architecture clean.

## Integration with `fmm`

Same principle:

- `fmm` remains a structural index
- adapter translates `fmm` outputs into candidates
- compiler does not own code parsing or symbol indexing

## Integration with `nancy`

`nancy` / `nancyr` should depend on the compiler output, not on each compaction detail.

Recommended orchestration boundary:

- `nancy` issues a `ContextRequest`
- compiler returns `CompiledContext`
- `nancy` uses that to build the agent prompt

This keeps orchestration simple and keeps context logic centralized.

## Initial Minimal Viable Implementation

To avoid overbuilding, start with:

### Crates

- `helioy-context-core`
- `helioy-context-compiler`

### Adapters

- `mdcontext`
- `recent`

Leave `fmm` integration for the next pass if needed, unless the use case requires it immediately.

### Signals

- recency
- source trust
- candidate kind prior

### Zones

- evidence
- recent
- headroom

### Compression

- document section truncation
- recent-turn truncation

This is enough to prove the architecture without solving every source domain on day one.

## Evaluation Strategy

Every stage should be testable independently.

Add:

- signal unit tests
- budget redistribution tests
- compression tests
- end-to-end scenario tests

The compiler should produce traces that allow assertions like:

- candidate X was excluded due to low score
- zone Y exceeded cap and redistributed surplus
- fragment Z was compressed from 420 tokens to 90

## Final Recommendation

Build a Helioy-native Rust context compiler with:

- shared typed core
- source adapters
- explicit scoring
- explicit budgets
- source-aware compression
- deterministic evaluation

Do not fold this into `mdcontext`.
Do not bolt it onto `fmm`.
Do not depend directly on Sapling.

Use Sapling for ideas.
Use Helioy’s own product philosophy for the architecture.

