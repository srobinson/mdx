# Helioy Context Manifesto

## The Problem

LLMs do not primarily suffer from a lack of intelligence.

They suffer from a lack of usable context.

Raw environments are too large, too noisy, too expensive, and too undifferentiated to be the primary substrate for finite-context intelligence.

Codebases are too big to read linearly.
Documentation is too verbose to paste wholesale.
Conversation history is too messy to trust as future memory.

The real engineering problem is context formation.

## The Thesis

Helioy exists to turn raw environments into high-signal context for finite-context intelligence.

That is the product thesis.

Not search for its own sake.
Not memory for its own sake.
Not orchestration for its own sake.

Context.

Useful, compressed, structured, trustworthy context.

## The Product Group

Helioy is the product group that includes:

- `fmm`
- `mdcontext`
- `am`
- `nancy` / `nancyr`

These are not separate ideas.
They are different answers to the same problem.

## `fmm`

`fmm` solves code context.

It assumes that brute-force file reading is waste.
The model should not rediscover code structure from scratch every time.

So `fmm` compiles code into structural metadata:

- exports
- imports
- dependencies
- outlines
- blast radius

It answers the question:

**What does the codebase structurally contain?**

## `mdcontext`

`mdcontext` solves document context.

It assumes that raw markdown is an inefficient prompt material.
Structure, hierarchy, and budget matter more than verbatim dumps.

So `mdcontext` compiles documents into:

- indexed sections
- ranked results
- compressed summaries
- token-bounded context

It answers the question:

**What do the documents mean within a finite context budget?**

## `AM`

`AM` solves reflective memory.

It should not be understood primarily as repo memory.
That is too narrow and too tactical.

`AM` is for the slower, more consequential layer:

- who are we
- what do we value
- what are our goals
- what keeps shaping those goals
- what decisions and tensions recur
- where are we headed

`AM` answers the question:

**What is becoming true through repeated dialogue over time?**

This is why `AM` feels different.
It is not just retrieval.
It is memory formation through conversation.

## `nancy` / `nancyr`

`nancy` is the orchestration harness.

It is the runtime that decides how context moves:

- which tool to consult
- which representation to use
- what to pass to which agent
- how to keep execution coherent under token pressure

It answers the question:

**How does high-signal context become coordinated action?**

## Tactical Context vs Reflective Memory

This distinction matters.

### Tactical context

Used for:

- code navigation
- document lookup
- implementation decisions
- immediate execution

Optimized for:

- precision
- compression
- determinism
- low waste

This is the domain of:

- `fmm`
- `mdcontext`

### Reflective memory

Used for:

- organizational identity
- strategic continuity
- durable beliefs
- recurring tensions
- long-horizon meaning

Optimized for:

- salience
- synthesis
- continuity
- debate
- interpretation

This is the domain of:

- `AM`

## The Deeper Claim

The future is not won by larger context windows alone.

Larger windows mostly increase tolerance for waste.

The deeper advantage comes from better intermediate representations:

- representations of code
- representations of documents
- representations of memory
- representations of organizational meaning

Helioy is building those representations.

## Final Statement

Helioy is a context company.

It builds systems that transform raw environments into usable context for AI.

- `fmm` gives structure to code
- `mdcontext` gives structure to docs
- `AM` gives structure to organizational memory
- `nancy` turns those structures into execution

The goal is not more information.

The goal is:

**the right context, in the right form, at the right time**

