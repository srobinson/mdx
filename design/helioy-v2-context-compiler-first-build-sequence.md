# Helioy Context Compiler First Build Sequence

Date: 2026-03-11
Status: Execution note
Author: Codex

## Purpose

This document defines the first build sequence for the Helioy context compiler.

It answers:

- what to prototype first
- what to defer
- what success looks like after the first two weeks

The goal is to prove the architecture quickly without prematurely solving the full Helioy context stack.

## First Principle

The first build should validate the separation:

- retrieval produces candidates
- compiler scores and compresses candidates
- orchestration consumes compiled context

It should not attempt to solve every source type, every scoring signal, or every product use case.

## Phase 1 Scope

Build the smallest end-to-end version that proves:

- a Rust compiler core is viable
- `mdcontext` retrieval output can be adapted into compiler candidates
- Sapling-style scoring and budgeting can be expressed cleanly
- compiled context is visibly better than naive concatenation

## Two-Week Prototype Goal

At the end of the first two weeks, we should have:

1. a Rust compiler core
2. an `mdcontext` adapter
3. a recent-context adapter
4. a small set of scoring signals
5. explicit token-budget zones
6. source-aware compression
7. a simple rendered output format
8. deterministic scenario tests

That is enough to prove the direction.

## What To Build First

### 1. `helioy-context-core`

Build the foundational crate first.

Must include:

- `ContextCandidate`
- `ContextFragment`
- `BudgetZone`
- `BudgetPlan`
- `ScoreBreakdown`
- `CompiledContext`

Do not add unnecessary abstractions yet.

### 2. `helioy-context-compiler`

Build a narrow pipeline:

- normalize
- score
- budget
- compress
- render

Skip grouping for the first pass unless it becomes necessary immediately.

### 3. `mdcontext` adapter

Use document retrieval results as the primary input source.

This is the cleanest first source because:

- it is already source-grounded
- it has strong section structure
- it maps naturally to candidate-based compilation

### 4. recent-context adapter

Add a minimal recent-context source:

- recent prompts
- recent tool summaries
- recent work state

Keep it simple.
Do not implement full Sapling-style operation segmentation in the first two weeks.

### 5. Minimal scoring model

Start with only three signals:

- recency
- source trust
- candidate kind prior

These are enough to prove the scoring abstraction.

### 6. Minimal budget zones

Start with three zones:

- instructions
- evidence
- headroom

Defer more nuanced zones like archived context or operation memory.

### 7. Source-aware compression

Implement only:

- document section compression
- recent-state truncation

Do not attempt fancy semantic compression for every source on the first pass.

## What To Defer

The prototype should explicitly defer:

### 1. Full `fmm` integration

This is valuable, but not necessary for proving the compiler architecture.

### 2. Full conversation operation segmentation

Sapling’s operation model is interesting, but it should not be the first abstraction we implement.

### 3. `AM` integration

Keep reflective memory out of the first tactical compiler prototype.

### 4. Cross-encoder reranking

Not needed yet.

### 5. Advanced surplus redistribution

Basic budget allocation is enough for the prototype.

### 6. MCP server surface

Build local CLI/test integration first.

### 7. UI integration

Do not build visual tooling before the compiler proves itself.

## Prototype Output Shape

The first renderer should produce a simple structure like:

```text
SYSTEM_INSTRUCTIONS
...

COMPILED_EVIDENCE
## Documents
- ...

## Recent State
- ...

BUDGET_REPORT
- evidence used: X
- headroom reserved: Y
```

This is not the final UX.
It is a debugable working format.

## Suggested Directory / Crate Start

### Crates

- `helioy-context-core`
- `helioy-context-compiler`

Optional in week 2:

- `helioy-context-adapters`

If speed matters, the first adapter can live in the compiler crate and be split later.

## Concrete Week-by-Week Plan

### Week 1

Focus:

- core types
- compiler pipeline skeleton
- `mdcontext` adapter
- minimal scoring
- minimal budgeting
- deterministic fixtures

Deliverables:

- compileable crates
- adapter from `mdcontext` search/context output to `ContextCandidate`
- test proving scored candidates are selected under budget

### Week 2

Focus:

- recent-context adapter
- compression logic
- renderer
- benchmark scenarios
- diagnostics/tracing

Deliverables:

- compiled output from mixed sources
- simple reports showing selected vs excluded candidates
- scenario comparisons against naive concatenation

## Success Criteria After Two Weeks

We should be able to show:

### 1. Better than naive assembly

Given the same source inputs, the compiler should produce:

- fewer tokens
- better-ordered evidence
- clearer separation of source types

### 2. Inspectability

We should be able to answer:

- what candidates were retrieved?
- how were they scored?
- what was dropped?
- what was compressed?
- why?

### 3. Stable abstractions

The first core types should feel reusable, not like throwaway scaffolding.

### 4. No philosophy drift

The compiler should remain:

- a separate layer from retrieval
- source-aware
- budget-aware

It should not start absorbing all of `mdcontext` or all of orchestration.

## Metrics to Watch

Track simple metrics first:

- candidate count in
- fragments out
- token count before
- token count after
- evidence-zone utilization
- number of excluded candidates

Also track qualitative benchmarks:

- does the output feel more usable than raw retrieval?
- is provenance preserved?
- are the right sections surviving?

## What Success Looks Like

At the end of the first build, we should be able to say:

- We have a Rust context compiler core.
- It consumes `mdcontext`-style retrieval output.
- It can score, budget, and compress candidates.
- It produces a prompt-ready compiled context object.
- It is inspectable and testable.
- It is clearly separate from both retrieval and orchestration.

That is enough to justify the architecture and move into the next stage.

## What Failure Looks Like

The prototype is failing if:

- the types are too vague to be useful
- scoring is opaque
- compression is entangled with retrieval
- adapter boundaries are unclear
- output is not visibly better than simple concatenation

If those happen, stop and simplify before expanding scope.

## Recommended Next Step After Prototype

If the prototype works, the next priority should be:

1. formalize the adapter boundary
2. add `fmm` integration
3. improve budget redistribution
4. evaluate whether operation-style grouping is needed

Only after that should we consider:

- MCP surface
- UI surfacing
- broader `nancy` integration

