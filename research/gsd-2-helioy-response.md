---
title: "GSD-2 Evaluation: What Matters for Helioy"
date: 2026-03-18
category: research
tags: [gsd, helioy, helix, architecture, evaluation]
summary: "Evaluation of GSD-2 architecture analysis and leverage opportunities through the lens of Helioy ecosystem priorities, with focus on Helix context API design."
---

# GSD-2 Evaluation: What Matters for Helioy

## Overall Assessment

GSD-2 is a well engineered system. 232K LOC across TypeScript and Rust, four clean layers, 10 provider protocols, 230 test files. The architecture shows maturity in areas that matter: provider abstraction, extension lifecycle, streaming primitives, crash recovery.

That said, this is a coding agent. Helioy is a context ecosystem. The overlap is real but narrow. Most of GSD-2's sophistication serves problems Helioy doesn't have (multi-provider LLM routing, terminal UI rendering, tool permission gating). The patterns worth extracting are structural, not domain-specific.

## What Genuinely Transfers

### EventStream (Priority: High)

The 87-line `EventStream<T, R>` is the cleanest pattern in the analysis. Push-based async iterable with completion detection and a terminal result promise. Three properties that matter:

1. Consumer controls pace (back-pressure via async iteration)
2. Completion is semantic (predicate-based, not signal-based)
3. Final result is separable from the event stream

This maps to helioy-bus message streams, but also to Helix. A `helix recall` could return an `EventStream<CandidateEntry, CuratedResult>` where candidates stream as Tantivy finds them, and the final result is the LLM-curated synthesis. The agent can choose to consume candidates directly (fast, raw) or await the curated result (slower, higher quality). That's the comparison mode we discussed.

Worth porting to Rust. The pattern is trivial to implement with `tokio::sync::mpsc` and a `oneshot` for the result.

### AgentMessage / Message Separation (Priority: High)

The distinction between `AgentMessage` (anything in the conversation, including custom types) and `Message` (LLM-compatible subset) with a `convertToLlm()` boundary is directly applicable to Helix.

Helix's internal representation of context entries should be richer than what gets sent to the LLM. Metadata, provenance, confidence scores, adapter source, relationship graph. All of that informs curation but shouldn't cross the boundary into the agent's context window. The proxy agent strips it at the boundary, analogous to `convertToLlm()`.

### Provider Registry with Capabilities (Priority: High)

The `registerApiProvider()` pattern with per-provider `compat` overrides maps cleanly to Helix adapter registration. Each adapter (cm, am, mdm) registers its capabilities and quirks. The proxy routes based on capability match.

The `compat` field is the pragmatic part. Real adapters have real quirks. cm supports scoped hierarchies; am uses geometric memory on S3 hypersphere; mdm is flat document search. The proxy needs per-adapter overrides for query translation, result normalization, and store routing. Don't pretend adapters are uniform. Model their differences as data.

### File-Based State Machine (Priority: Medium)

GSD's `.gsd/` directory state approach (read state from disk, decide next action, no in-memory state across sessions) is directly applicable to helioy-bus warroom orchestration. Crash recovery is free because there's nothing to recover. Just read the disk.

For Helix specifically: the conflict queue (`helix conflicts`) could be a file-based state. Detected overlaps written to disk, curated by agent or human, resolved by the next write operation. No daemon needed to hold conflict state.

## What Looks Valuable But Isn't (For Helioy)

### Extension System Two-Phase Loading

The registration-then-binding pattern solves initialization ordering. It's good engineering. But helioy-plugins loads MCP servers, which already have their own lifecycle protocol. Adopting GSD's extension system would mean building a second plugin architecture alongside MCP. The complexity cost exceeds the benefit.

Where this does matter: if Helix adapters are loaded as plugins rather than compiled in. Then the two-phase pattern prevents adapters from calling the proxy before it's ready. Worth revisiting when Helix's adapter loading strategy is defined.

### Differential TUI Rendering

Clean implementation, wrong problem. Helioy's interface is Claude Code. Building a custom TUI is building a product, not a tool. If we need rich terminal output, use a library. Don't build a rendering engine.

Exception: if helioy-bus monitoring or Helix context browsing ever needs a dashboard, study this. But that's future work.

### Hashline Editing

Clever solution to line-number drift between read and edit. fmm tracks symbols by line ranges. If fmm ever needs edit capabilities, this pattern has merit. For now, fmm is read-only intelligence. File this under "remember it exists."

### JSONL Session Persistence with Compaction

GSD's session format is append-only JSONL with compaction (LLM summarization of old context). The compaction pattern is interesting for cm, but cm already has its own persistence model (SQLite with FTS5). Switching to JSONL would be a regression.

The compaction concept (summarize old entries, preserve key references) is worth abstracting. Not the format.

## What's Missing from the Analysis

The leverage opportunities document doesn't address the hardest problem Helioy faces: **context quality at scale**. GSD-2 solves context quantity (compaction, pruning, session management). Helioy's bet with Helix is that quality beats quantity. LLM curation at write time, LLM synthesis at read time.

Nothing in GSD-2 addresses this. Their context management is mechanical (token counting, summarization). Helix's context management is semantic (overlap detection, conflict resolution, intelligent routing). These are different problems with different solutions.

The second gap: **cross-session context coherence**. GSD sessions are independent. Fresh session, fresh context, read state from disk. This works for a coding agent where the filesystem is the source of truth. For a context ecosystem where the context itself is the product, session independence is a limitation. Helix needs the opposite: every interaction enriches a persistent, curated context graph that grows more valuable over time.

## Revised Priority Order

The leverage document's priority table is reasonable but misweights for Helioy's actual trajectory. Revised:

| Priority | Pattern | Target | Rationale |
|----------|---------|--------|-----------|
| 1 | Provider registry + capabilities | Helix | Core adapter abstraction. Design this first. |
| 2 | AgentMessage/Message separation | Helix | Internal richness, boundary translation. |
| 3 | EventStream | Helix, helioy-bus | Streaming primitive for both recall and bus messages. |
| 4 | File-based state machine | helioy-bus warroom | Crash-recoverable orchestration. |
| 5 | TypeBox schema validation | helioy-plugins | Low effort, immediate value for MCP tool params. |
| 6 | Steering queue | helioy-bus | Non-destructive agent interruption. |
| 7 | Native npm distribution | fmm, am, cm, mdm | Study the pattern. Apply when distributing. |
| 8 | Compaction concept | Helix | Abstract the idea. Not the JSONL format. |

Dropped: Extension two-phase loading (premature), TUI rendering (wrong problem), hashline editing (fmm is read-only).

## Connection to Helix Architecture

Three GSD patterns feed directly into Helix decisions still open:

1. **Provider registry answers "how do adapters plug in?"** Register at runtime, carry capabilities as data, route by capability match. The `compat` field pattern handles adapter quirks without special-casing in the router.

2. **AgentMessage/Message separation answers "what does the proxy's internal representation look like?"** Rich internally (metadata, provenance, confidence, relationships), stripped at the boundary before reaching the calling agent's context window.

3. **EventStream answers "how does `helix recall` return results?"** Stream candidates from Tantivy, deliver curated synthesis as the final result. Agent chooses which to consume. This enables the comparison mode (raw vs curated) without two separate APIs.

These three patterns, combined with the decisions already made (CLI surface, LLM on both paths, Tantivy for candidate retrieval), give Helix a concrete enough shape to start prototyping.
