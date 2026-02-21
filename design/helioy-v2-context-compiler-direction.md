# Helioy Context Compiler Direction

Date: 2026-03-11
Status: Architecture note
Author: Codex

## Summary

This note answers the next obvious question after separating:

- index / retrieve
- curate / compress

The question is:

**What should the context compiler actually be, and where should it live?**

My recommendation:

- rewrite `mdcontext` in Rust over time
- do not integrate Sapling as a direct dependency
- use Sapling as a reference architecture
- design a Helioy-native context compiler that sits above `fmm` and `mdcontext`

## Recommendation

### 1. Rewrite `mdcontext` in Rust

Yes, I think this is the right direction.

Not because TypeScript is inadequate in principle, but because the Helioy stack is converging around:

- long-running local processes
- structured indexing
- token-sensitive pipelines
- deterministic CLI behavior
- low-overhead orchestration
- strong typed intermediate representations

Rust fits that trajectory better.

### 2. Do not integrate Sapling as a dependency

Yes, I think that is also the right call.

Sapling should be treated as:

- a source of strong ideas
- a reference architecture
- a pattern library

But not as:

- a foundational runtime dependency
- a framework Helioy is forced to conform to

We should leverage the design patterns and build our own Helioy-native version.

## Why Rewrite `mdcontext` in Rust

### Architectural coherence

The Helioy stack already has strong Rust gravity:

- `fmm` is Rust
- `AM` is Rust
- `nancy` / `nancyr` is Rust-oriented

Keeping one major retrieval system in a separate runtime is not fatal, but it does create friction:

- duplicated packaging concerns
- duplicated process/runtime behavior
- separate performance envelopes
- split infrastructure for CLI, MCP, and long-running services

### Better fit for pipeline systems

The future `mdcontext` is unlikely to remain “just a CLI that searches markdown.”
It is more likely to become:

- a long-lived indexer
- a retrieval service
- a summarization feeder
- a document-context provider to a larger compiler pipeline

That wants:

- explicit data structures
- low-latency local storage
- predictable memory use
- concurrency control
- easy integration with other Rust components

### Better shared abstractions

If `fmm`, `mdcontext`, and the context compiler all live in Rust, we can share:

- scoring abstractions
- token budgeting logic
- CLI patterns
- local DB patterns
- structured events
- evaluation harnesses

That is strategically valuable.

## Why Not Depend on Sapling Directly

### Different product center

Sapling is solving a related but not identical problem.

Its center of gravity is:

- conversation compaction
- operation segmentation
- agent runtime context management

Helioy needs a broader context compiler that can handle:

- code candidates from `fmm`
- document candidates from `mdcontext`
- recent working context
- possibly reflective memory from `AM`

So even if Sapling is excellent, its abstractions are not automatically the right primary abstractions for Helioy.

### Control over the model

We should own:

- the boundary between retrieval and compaction
- the scoring model
- the zone budget model
- the source adapters
- the event model

If we depend directly on Sapling, we risk inheriting assumptions that are right for Sapling but wrong for Helioy.

### Philosophy mismatch

Sapling is a strong influence, but Helioy already has its own worldview:

- `fmm` = structure first
- `mdcontext` = compression first
- `AM` = reflective memory
- `nancy` = orchestration

The context compiler should emerge from those existing product truths, not be bolted on from the outside.

## What We Should Steal from Sapling

We should absolutely borrow the following patterns:

### 1. Explicit scoring signals

Context should not be ranked by one opaque score.

Use named, weighted signals such as:

- recency
- source overlap
- file overlap
- dependency relevance
- outcome significance
- source trust
- operation type

### 2. Zone-based budgeting

Prompt space should be partitioned intentionally.

For example:

- instructions
- active context
- retrieved evidence
- headroom

### 3. Compaction as a pipeline

Context curation should be a dedicated pipeline, not an ad hoc formatter.

### 4. Source-aware truncation

Different sources should compress differently:

- code structure
- doc sections
- recent conversational context
- logs / tool output

### 5. Regressionable evaluation

Context quality should be benchmarked with deterministic fixtures, not judged only by taste.

## What We Should Not Copy Blindly

### Operation abstraction

Sapling's "operation" model is promising, but Helioy should not adopt it unchanged.

We probably need a broader unit, something like:

- context fragment
- work unit
- evidence unit

Because Helioy must combine multiple source systems, not just one conversation history.

### Runtime coupling

Do not couple the compiler too tightly to one agent runtime implementation.

The compiler should be usable by:

- `nancy`
- future CLIs
- testing harnesses
- MCP endpoints

## Proposed Helioy Architecture

### Layer 1: Retrieval systems

- `fmm` returns code candidates
- `mdcontext` returns document candidates
- optional recent conversation adapter returns working-state candidates
- optional `AM` adapter returns reflective-memory candidates

These systems remain source-facing.

### Layer 2: Context compiler

A new Helioy-native component:

- scores candidates
- groups them
- compresses them
- allocates token budgets
- produces final working context

This should be its own crate or subsystem.

Possible names:

- `context-compiler`
- `helioy-context`
- `signal-compiler`

### Layer 3: Orchestration

`nancy` / `nancyr` decides:

- when to invoke each retrieval source
- what task mode is active
- which prompt template to use
- how to route compiled context to agents

## Suggested Migration Path

### Step 1

Keep current `mdcontext` behavior conceptually stable.

Do not mix rewrite and philosophical expansion all at once.

### Step 2

Define the Rust core shape for `mdcontext`:

- parser/indexer
- retrieval API
- search/ranking API
- summary/section output

### Step 3

Build the context compiler as a separate Rust crate.

Do not bury it inside `mdcontext`.

### Step 4

Add adapters:

- `fmm` adapter
- `mdcontext` adapter
- recent-context adapter

### Step 5

Benchmark compiler output against representative tasks.

### Step 6

Only after that, consider whether `AM` should feed into this system at all, and if so, in which modes.

## Strong Recommendation

Do not make `AM` part of the tactical context compiler by default.

Keep it separate for now.

Reason:

- `fmm` and `mdcontext` solve tactical context
- `AM` solves reflective memory

Mixing them too early will blur the philosophical distinction we just clarified.

## Final Position

The right move is:

- **yes** to rewriting `mdcontext` in Rust
- **yes** to learning heavily from Sapling
- **no** to treating Sapling as a direct dependency
- **yes** to building a Helioy-native context compiler on top of `fmm` and `mdcontext`

That gives us:

- architectural coherence
- ownership of core abstractions
- room to adapt the model to Helioy’s product philosophy

