# Helioy V2 Nancyr Index

Date: 2026-03-11
Status: Entry point
Author: Codex

## Purpose

This is the focused reading and build index for the `nancyr` direction inside `helioy-v2`.

Use this document when the question is:

- what is `nancyr` supposed to be?
- what is the first credible version?
- what is the V1 runtime model?
- how should implementation be split across repos?

## Fast Path

If you only want the shortest useful path, read these in order:

1. [helioy-v2-nancyr-collaborative-intelligence-runtime.md](/Users/alphab/.mdx/design/helioy-v2-nancyr-collaborative-intelligence-runtime.md)
2. [helioy-v2-nancyr-first-credible-version.md](/Users/alphab/.mdx/design/helioy-v2-nancyr-first-credible-version.md)
3. [helioy-v2-nancyr-v1-runtime-spec.md](/Users/alphab/.mdx/design/helioy-v2-nancyr-v1-runtime-spec.md)
4. [helioy-v2-nancyr-v1-schema-pack.md](/Users/alphab/.mdx/design/helioy-v2-nancyr-v1-schema-pack.md)
5. [helioy-v2-nancyr-repo-build-breakdown.md](/Users/alphab/.mdx/design/helioy-v2-nancyr-repo-build-breakdown.md)

That sequence moves from:

- product thesis
- to credible wedge
- to runtime design
- to implementation schema
- to repo execution plan

## Document Map

### Product Thesis

- [helioy-v2-nancyr-collaborative-intelligence-runtime.md](/Users/alphab/.mdx/design/helioy-v2-nancyr-collaborative-intelligence-runtime.md)
  Defines `nancyr` as a self-improving collaborative intelligence runtime, not a CLI wrapper or single-agent optimizer.

### Credible Wedge

- [helioy-v2-nancyr-first-credible-version.md](/Users/alphab/.mdx/design/helioy-v2-nancyr-first-credible-version.md)
  Narrows the ambition to the first believable version: coordinator-centered, small fixed team, structured messaging, review, retrospection.

### Runtime Design

- [helioy-v2-humanwork-to-nancyr-synthesis.md](/Users/alphab/.mdx/design/helioy-v2-humanwork-to-nancyr-synthesis.md)
  Bridges the original HumanWork design and the Amorphic notes into the Helioy / `nancyr` direction.

- [helioy-v2-nancyr-v1-runtime-spec.md](/Users/alphab/.mdx/design/helioy-v2-nancyr-v1-runtime-spec.md)
  Defines the V1 entities, protocols, events, product surfaces, and build sequence.

### Implementation

- [helioy-v2-nancyr-v1-schema-pack.md](/Users/alphab/.mdx/design/helioy-v2-nancyr-v1-schema-pack.md)
  Concrete schemas for entities, events, bus envelopes, and relational storage.

- [helioy-v2-nancyr-repo-build-breakdown.md](/Users/alphab/.mdx/design/helioy-v2-nancyr-repo-build-breakdown.md)
  Assigns responsibilities across `helioy-bus` and `nancyr` and defines the first implementation tickets.

## Recommended Reading Paths

### If the question is "What is `nancyr`?"

Read:

1. [helioy-v2-nancyr-collaborative-intelligence-runtime.md](/Users/alphab/.mdx/design/helioy-v2-nancyr-collaborative-intelligence-runtime.md)
2. [helioy-v2-nancyr-first-credible-version.md](/Users/alphab/.mdx/design/helioy-v2-nancyr-first-credible-version.md)

### If the question is "What should we build first?"

Read:

1. [helioy-v2-nancyr-first-credible-version.md](/Users/alphab/.mdx/design/helioy-v2-nancyr-first-credible-version.md)
2. [helioy-v2-nancyr-v1-runtime-spec.md](/Users/alphab/.mdx/design/helioy-v2-nancyr-v1-runtime-spec.md)
3. [helioy-v2-nancyr-repo-build-breakdown.md](/Users/alphab/.mdx/design/helioy-v2-nancyr-repo-build-breakdown.md)

### If the question is "What should the data model look like?"

Read:

1. [helioy-v2-nancyr-v1-runtime-spec.md](/Users/alphab/.mdx/design/helioy-v2-nancyr-v1-runtime-spec.md)
2. [helioy-v2-nancyr-v1-schema-pack.md](/Users/alphab/.mdx/design/helioy-v2-nancyr-v1-schema-pack.md)

### If the question is "How do HumanWork and Amorphic map into this?"

Read:

1. [helioy-v2-humanwork-to-nancyr-synthesis.md](/Users/alphab/.mdx/design/helioy-v2-humanwork-to-nancyr-synthesis.md)
2. [helioy-v2-nancyr-collaborative-intelligence-runtime.md](/Users/alphab/.mdx/design/helioy-v2-nancyr-collaborative-intelligence-runtime.md)
3. [helioy-v2-nancyr-v1-runtime-spec.md](/Users/alphab/.mdx/design/helioy-v2-nancyr-v1-runtime-spec.md)

## Canonical Build Order

The current canonical build order is:

1. [helioy-v2-nancyr-first-credible-version.md](/Users/alphab/.mdx/design/helioy-v2-nancyr-first-credible-version.md)
2. [helioy-v2-nancyr-v1-runtime-spec.md](/Users/alphab/.mdx/design/helioy-v2-nancyr-v1-runtime-spec.md)
3. [helioy-v2-nancyr-v1-schema-pack.md](/Users/alphab/.mdx/design/helioy-v2-nancyr-v1-schema-pack.md)
4. [helioy-v2-nancyr-repo-build-breakdown.md](/Users/alphab/.mdx/design/helioy-v2-nancyr-repo-build-breakdown.md)
