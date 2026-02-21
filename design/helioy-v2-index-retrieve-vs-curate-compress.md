# Index/Retrieve vs Curate/Compress

Date: 2026-03-11
Status: Architecture note
Author: Codex

## Summary

`mdcontext` and Sapling-style compaction should be treated as separate concerns.

This distinction is important:

- `mdcontext` should index and retrieve
- a separate context compiler should curate and compress

They solve different problems.
They optimize for different virtues.
They should not be fused prematurely.

## The Core Distinction

### Index / Retrieve

Purpose:

- find relevant source material
- preserve provenance
- maintain structural fidelity
- maximize recall quality

Question answered:

**What relevant source material exists?**

This is the job of:

- `mdcontext` for documents
- `fmm` for code

### Curate / Compress

Purpose:

- rank candidates under scarcity
- preserve continuity under a token budget
- compress low-priority material
- drop irrelevant or low-value material
- assemble model-usable working context

Question answered:

**Given limited context, what deserves to survive and in what form?**

This is the job of:

- a Sapling-inspired context compiler

## Why This Separation Matters

If retrieval and compaction are fused too early:

- retrieval semantics get polluted by budgeting heuristics
- source ranking becomes harder to reason about
- debugging becomes ambiguous
- the system cannot cleanly answer:
  - what was found?
  - what was selected?
  - what was discarded?
  - why?

If they remain separate:

- retrieval stays source-faithful
- compaction stays context-faithful
- intermediate artifacts remain inspectable
- each layer can improve independently

## Different Optimization Targets

### Retrieval wants

- recall
- relevance
- provenance
- structural correctness
- fidelity to source

### Compaction wants

- budget discipline
- continuity preservation
- utility to the next model turn
- compression under scarcity
- graceful lossiness

These are related but different goals.

## Proposed Pipeline

The clean architecture is:

1. source indexing
2. retrieval
3. candidate scoring
4. curation / compression
5. prompt assembly

### Example

1. `fmm` retrieves code structure candidates
2. `mdcontext` retrieves documentation candidates
3. recent conversation state contributes active-turn candidates
4. context compiler ranks and compresses all candidates
5. prompt builder assembles final working context

The LLM should see:

- working context

not:

- raw retrieval output

## `mdcontext` Responsibility

`mdcontext` should remain focused on:

- indexing markdown
- section-aware retrieval
- hybrid ranking
- structured summaries at the document/section level
- returning strong candidates with provenance

It should not become the general-purpose prompt compactor for the whole system.

Its role is:

**document index and retrieval engine**

not:

**global context budget allocator**

## Sapling-Inspired Compiler Responsibility

A separate context compiler should handle:

- semantic grouping of recent work
- scoring candidate context
- token zone budgeting
- compression
- archival
- truncation strategies
- continuity preservation

Its role is:

**turn candidate context into working context**

This is where Sapling’s ideas belong.

## Philosophy

Retrieval is about truth to source.

Compaction is about usefulness to the model.

Those are not the same virtue.

The system needs both, but it should not confuse them.

## Helioy Interpretation

This yields a clean layered view:

- `fmm`
  code index / retrieve

- `mdcontext`
  document index / retrieve

- context compiler
  curate / compress / budget

- `nancy` / `nancyr`
  orchestrate which systems are used and when

- `AM`
  separate reflective memory lane, not tactical prompt compaction

## Design Consequence

Do not ask `mdcontext` to solve the entire context problem by itself.

Ask it to do its job extremely well:

- return the best candidate source material
- with strong structure
- with strong provenance
- with compact but still source-grounded summaries

Then let a separate layer decide:

- what survives
- what is compressed
- what is omitted
- how budget is distributed

## Final Statement

The correct separation is:

- **index/retrieve finds candidates**
- **curate/compress decides what earns prompt space**

That boundary should remain explicit in the Helioy architecture.

