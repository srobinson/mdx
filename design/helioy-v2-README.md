# Helioy V2 README

Date: 2026-03-11
Status: Entry point
Author: Codex

## Purpose

This folder contains the current `helioy-v2` thinking.

The documents here are not random notes. They describe a converging architecture and product thesis for the Helioy product group:

- `fmm`
- `mdcontext`
- `am`
- `nancy` / `nancyr`

The unifying theme is the LLM context problem:

**finite-context intelligence needs better representations than raw source**

Helioy is the product group working on that problem across:

- code
- documents
- reflective organizational memory
- orchestration

## Start Here

If you only read three documents, read these in order:

1. [helioy-v2-context-manifesto.md](/Users/alphab/.mdx/design/helioy-v2-context-manifesto.md)
2. [helioy-v2-product-thesis-context-vs-memory.md](/Users/alphab/.mdx/design/helioy-v2-product-thesis-context-vs-memory.md)
3. [helioy-v2-index-retrieve-vs-curate-compress.md](/Users/alphab/.mdx/design/helioy-v2-index-retrieve-vs-curate-compress.md)

That sequence establishes:

- the overall Helioy thesis
- the division of labor across products
- the architectural boundary between retrieval and compaction

## Document Map

### Foundational Thesis

- [helioy-v2-context-manifesto.md](/Users/alphab/.mdx/design/helioy-v2-context-manifesto.md)
  The public-facing thesis. Helioy as a response to the LLM context problem.

- [helioy-v2-product-thesis-context-vs-memory.md](/Users/alphab/.mdx/design/helioy-v2-product-thesis-context-vs-memory.md)
  The sharper internal distinction between tactical context and reflective memory.

### Nancyr Direction

- [helioy-v2-nancyr-index.md](/Users/alphab/.mdx/design/helioy-v2-nancyr-index.md)
  Focused entry point for the `nancyr` runtime track.

- [helioy-v2-nancyr-collaborative-intelligence-runtime.md](/Users/alphab/.mdx/design/helioy-v2-nancyr-collaborative-intelligence-runtime.md)
  Product thesis for `nancyr` as a self-improving collaborative intelligence runtime.

- [helioy-v2-nancyr-first-credible-version.md](/Users/alphab/.mdx/design/helioy-v2-nancyr-first-credible-version.md)
  Defines the first believable wedge for the product.

- [helioy-v2-humanwork-to-nancyr-synthesis.md](/Users/alphab/.mdx/design/helioy-v2-humanwork-to-nancyr-synthesis.md)
  Synthesizes HumanWork, Amorphic, and Helioy into a concrete runtime direction.

- [helioy-v2-nancyr-v1-runtime-spec.md](/Users/alphab/.mdx/design/helioy-v2-nancyr-v1-runtime-spec.md)
  V1 runtime design.

- [helioy-v2-nancyr-v1-schema-pack.md](/Users/alphab/.mdx/design/helioy-v2-nancyr-v1-schema-pack.md)
  Concrete implementation schemas.

- [helioy-v2-nancyr-repo-build-breakdown.md](/Users/alphab/.mdx/design/helioy-v2-nancyr-repo-build-breakdown.md)
  Repo ownership and first ticket sequence.

### AM Direction

- [helioy-v2-am-chat-evidence-selection-spec.md](/Users/alphab/.mdx/design/helioy-v2-am-chat-evidence-selection-spec.md)
  Retrieval-time evidence filtering for chat.

- [helioy-v2-am-curated-ingestion-spec.md](/Users/alphab/.mdx/design/helioy-v2-am-curated-ingestion-spec.md)
  Ingestion-first approach: clean memory before it enters the system.

- [helioy-v2-am-high-signal-memory-architecture-proposal.md](/Users/alphab/.mdx/design/helioy-v2-am-high-signal-memory-architecture-proposal.md)
  Unified proposal combining curated ingestion, scoring, and prompt budgeting.

- [helioy-v2-am-high-signal-memory-build-plan.md](/Users/alphab/.mdx/design/helioy-v2-am-high-signal-memory-build-plan.md)
  Concrete build plan for the AM high-signal architecture.

### Retrieval vs Compaction

- [helioy-v2-index-retrieve-vs-curate-compress.md](/Users/alphab/.mdx/design/helioy-v2-index-retrieve-vs-curate-compress.md)
  Core boundary: `mdcontext` retrieves, a separate compiler compacts.

### Context Compiler Direction

- [helioy-v2-context-compiler-direction.md](/Users/alphab/.mdx/design/helioy-v2-context-compiler-direction.md)
  Recommendation to treat Sapling as inspiration, not dependency, and to build a Helioy-native compiler.

- [helioy-v2-context-compiler-crate-map.md](/Users/alphab/.mdx/design/helioy-v2-context-compiler-crate-map.md)
  Proposed Rust crate and module structure for the compiler.

- [helioy-v2-context-compiler-first-build-sequence.md](/Users/alphab/.mdx/design/helioy-v2-context-compiler-first-build-sequence.md)
  First two-week prototype sequence.

## Current Architectural Stance

At the moment, the clearest working model is:

- `fmm` handles code structure and navigation
- `mdcontext` handles document indexing and retrieval
- a separate context compiler handles curation, compression, and token budgeting
- `am` handles reflective organizational memory, not primary repo-state memory
- `nancy` / `nancyr` orchestrates the whole system

That means:

- do not overload `am` with tactical repo memory expectations
- do not overload `mdcontext` with compaction responsibilities
- do not copy Sapling directly; absorb its patterns and build a Helioy-native compiler

## Recommended Reading Paths

### If the question is "What is Helioy?"

Read:

1. [helioy-v2-context-manifesto.md](/Users/alphab/.mdx/design/helioy-v2-context-manifesto.md)
2. [helioy-v2-product-thesis-context-vs-memory.md](/Users/alphab/.mdx/design/helioy-v2-product-thesis-context-vs-memory.md)

### If the question is "What should AM become?"

Read:

1. [helioy-v2-product-thesis-context-vs-memory.md](/Users/alphab/.mdx/design/helioy-v2-product-thesis-context-vs-memory.md)
2. [helioy-v2-am-curated-ingestion-spec.md](/Users/alphab/.mdx/design/helioy-v2-am-curated-ingestion-spec.md)
3. [helioy-v2-am-high-signal-memory-architecture-proposal.md](/Users/alphab/.mdx/design/helioy-v2-am-high-signal-memory-architecture-proposal.md)
4. [helioy-v2-am-high-signal-memory-build-plan.md](/Users/alphab/.mdx/design/helioy-v2-am-high-signal-memory-build-plan.md)

### If the question is "How should mdcontext relate to Sapling?"

Read:

1. [helioy-v2-index-retrieve-vs-curate-compress.md](/Users/alphab/.mdx/design/helioy-v2-index-retrieve-vs-curate-compress.md)
2. [helioy-v2-context-compiler-direction.md](/Users/alphab/.mdx/design/helioy-v2-context-compiler-direction.md)
3. [helioy-v2-context-compiler-crate-map.md](/Users/alphab/.mdx/design/helioy-v2-context-compiler-crate-map.md)
4. [helioy-v2-context-compiler-first-build-sequence.md](/Users/alphab/.mdx/design/helioy-v2-context-compiler-first-build-sequence.md)

### If the question is "What should `nancyr` become and how do we build it?"

Read:

1. [helioy-v2-nancyr-index.md](/Users/alphab/.mdx/design/helioy-v2-nancyr-index.md)
2. [helioy-v2-nancyr-collaborative-intelligence-runtime.md](/Users/alphab/.mdx/design/helioy-v2-nancyr-collaborative-intelligence-runtime.md)
3. [helioy-v2-nancyr-first-credible-version.md](/Users/alphab/.mdx/design/helioy-v2-nancyr-first-credible-version.md)
4. [helioy-v2-nancyr-v1-runtime-spec.md](/Users/alphab/.mdx/design/helioy-v2-nancyr-v1-runtime-spec.md)
5. [helioy-v2-nancyr-v1-schema-pack.md](/Users/alphab/.mdx/design/helioy-v2-nancyr-v1-schema-pack.md)
6. [helioy-v2-nancyr-repo-build-breakdown.md](/Users/alphab/.mdx/design/helioy-v2-nancyr-repo-build-breakdown.md)

## Canonical Entry

The canonical starting points are:

1. [helioy-v2-README.md](/Users/alphab/.mdx/design/helioy-v2-README.md)
2. [helioy-v2-context-manifesto.md](/Users/alphab/.mdx/design/helioy-v2-context-manifesto.md)
3. [helioy-v2-product-thesis-context-vs-memory.md](/Users/alphab/.mdx/design/helioy-v2-product-thesis-context-vs-memory.md)
