---
title: "Claude-Mem Competitive Synthesis — What Helioy Can Learn"
category: research
tags: [claude-mem, attention-matters, helioy, competitive-intelligence, memory, plugins]
created: 2026-02-28
---

# Claude-Mem Competitive Synthesis

Claude-mem (v10.5.2, by Alex Newman / @thedotmack) is the most mature Claude Code memory plugin in the ecosystem. 4 research documents cover its core architecture, hooks/context injection, search/retrieval, and modes/features. This synthesis distills what matters for Helioy.

## The Fundamental Architecture Difference

| Dimension | claude-mem | Helioy (am + mdcontext) |
|-----------|-----------|------------------------|
| **Observation capture** | Secondary Claude instance processes every tool output (expensive, flexible) | Explicit `am_buffer`/`am_salient` calls (zero cost, deterministic) |
| **Storage** | SQLite + Chroma vector DB (Python dependency) | brain.db (pure Rust, no external deps) |
| **Recall** | FTS5 (deprecated) + Chroma semantic search + 90-day cutoff | Geometric composition on quaternion manifold, no time cutoff |
| **Contradiction handling** | None — purely append-only | Epoch-based Jaccard overlap penalty suppresses stale knowledge |
| **Project scoping** | Per-project namespaces | Unified brain, no project boundaries (cross-project recall by design) |
| **Token cost** | ~2-5K tokens per observation (secondary Claude call) | Zero marginal token cost |
| **Search** | 3-layer progressive disclosure (index → timeline → details) | Budget-aware geometric composition with max_tokens |

**Our core advantage**: Zero marginal cost per memory operation. Claude-mem spawns a secondary Claude instance for every tool output, which means every session burns tokens just to remember. AM's geometric recall has zero API cost.

**Their core advantage**: Automatic capture. No behavior change needed from the LLM — PostToolUse fires for every tool with `matcher: "*"` and the secondary agent extracts structured observations. Our system requires the LLM to actively call `am_buffer`/`am_salient`, which means recall quality depends on prompt compliance.

## What We Should Learn

### 1. Structured Observation Schema

Claude-mem's observation format is well-designed:

```
type: feature | bugfix | discovery | investigation | architecture | ...
title: "One-line summary"
subtitle: "Contextual detail"
narrative: "2-3 sentence explanation"
facts: ["discrete learnings"]
concepts: ["architectural patterns"]
files_read: ["/path/to/file"]
files_modified: ["/path/to/file"]
```

**Takeaway**: AM neighborhoods could benefit from structured metadata fields beyond raw text. The `facts` array (discrete learnings) and `concepts` array (patterns) are particularly useful for retrieval — they create multiple embedding surfaces per observation.

### 2. Progressive Disclosure for Token Economy

The 3-layer search workflow is their best UX innovation:

1. **search** → compact index with IDs (~50-100 tokens/result)
2. **timeline** → chronological context around interesting results
3. **get_observations** → full details ONLY for filtered IDs (~500-1000 tokens/result)

They claim ~10x token savings vs. returning full results upfront.

**Takeaway**: AM's `am_query` returns full context immediately. For large result sets, a two-phase approach (IDs + summaries first, full content on request) would reduce context pollution. The `max_tokens` budget parameter partially addresses this, but the progressive pattern is more explicit.

### 3. Content-Hash Deduplication

SHA-256 truncated to 16 hex chars with a 30-second dedup window. Prevents duplicate observations when the same tool fires multiple times.

**Takeaway**: AM doesn't currently deduplicate buffered exchanges. If `am_buffer` is called with identical content within a short window, it creates redundant data. A content-hash check before insert would be trivial and valuable.

### 4. Token Economics Tracking

Claude-mem tracks `discovery_tokens` per observation — the API cost to produce the observation vs. the cost to consume it as context. This measures memory ROI.

**Takeaway**: AM should track token cost of recall results. When `am_query` returns context, knowing "this recall cost ~800 tokens and was derived from 3 episodes" helps tune budget parameters.

### 5. Transcript Watching (Universal Adapter)

The most architecturally interesting feature. A JSONL adapter with declarative schemas lets claude-mem observe *any* AI tool — not just Claude Code. Configuration defines `transcript_path`, `format`, `entry_type`, and field mappings.

**Takeaway**: This is relevant for Nancy. If Nancy agents use different AI backends (Claude, GPT, Gemini), a universal transcript watcher could funnel all observations into AM without per-backend integration. The declarative schema approach is clean.

### 6. Granular Document Embedding Strategy

Each observation field (narrative, individual facts, concepts) becomes a separate Chroma document rather than embedding the whole observation. A fact like "JWT tokens expire after 1 hour" matches queries about "token expiration" even if the narrative is about authentication setup.

**Takeaway**: If AM ever adds embedding-based retrieval alongside geometric recall, this granular strategy is clearly superior to whole-document embedding.

### 7. Modes as JSON Prompt Configuration

34 mode files define domain-specific observer behaviors: `code.json` (25 prompt fragments), `email-investigation.json` (fraud analysis), language variants. Modes use partial override inheritance — `code--chill.json` only specifies changed fields.

**Takeaway**: The partial override pattern is elegant. Helioy skills currently use SKILL.md markdown files. For skills that need configurable behavior (e.g., different memory aggressiveness per project type), a JSON mode layer with inheritance could complement SKILL.md definitions.

### 8. OpenClaw SSE Observation Feed

Real-time streaming of observations to messaging channels (Telegram, Discord, Slack). Provides visibility into agent work for remote monitoring.

**Takeaway**: Directly relevant to Nancy. When agents are executing autonomously, streaming their observations to a monitoring channel is essential for the "visibility and control over AI agent fleets" value proposition.

## What We Should NOT Learn

### 1. Secondary Claude Instance for Observation Extraction

Spawning a full Claude Code instance per session to extract observations is architecturally expensive. It doubles API cost for memory. Our explicit `am_buffer`/`am_salient` approach is fundamentally cheaper and more predictable.

### 2. 90-Day Recency Hard Cutoff

All semantic search results older than 90 days are dropped. This is a crude solution to recency bias. AM's geometric decay is continuous and tunable — no arbitrary cliff.

### 3. FTS5 → Chroma Migration (Breaking Change)

They fully deprecated SQLite FTS5 in favor of Chroma vector search, creating a hard dependency on Python/uvx. Without Python installed, text search returns empty results. This is fragile. AM's zero-dependency Rust approach avoids this class of problem entirely.

### 4. Per-Project Scoping

Each project gets its own namespace. Cross-project recall requires explicit project targeting. We already decided (and validated) that unified brain.db with no project boundaries is superior — it enables lateral associations that project scoping suppresses.

### 5. AGPL-3.0 License

The viral copyleft license means any derivative must also be AGPL. We can study patterns but cannot incorporate code.

## Threat Assessment

Claude-mem has mindshare (trending on GitHub, Solana memecoin, Discord community, 26+ language translations). But technically:

- **Expensive**: Every observation costs API tokens
- **Fragile**: Hard Python dependency for search, secondary Claude process for capture
- **Append-only**: No contradiction handling, no learning from feedback
- **Time-limited**: 90-day cutoff means long-running projects lose history
- **Project-siloed**: No cross-project recall without explicit targeting

AM is architecturally superior on every dimension except automatic capture (no LLM behavior change needed) and progressive disclosure UX. Both gaps are closable:

1. **Automatic capture**: A PostToolUse hook that calls `am_buffer` with tool output would eliminate the need for LLM compliance. No secondary Claude instance needed — just extract key-value pairs from the hook stdin JSON.
2. **Progressive disclosure**: Add an `am_query_index` command that returns IDs + summaries without full content, enabling the two-phase retrieval pattern.

## Priority Actions

1. **Content-hash dedup for am_buffer** — Prevent redundant episodes from repeated calls. Low effort, immediate value.
2. **PostToolUse hook for automatic capture** — Buffer tool outputs into AM without requiring LLM to call am_buffer. Closes the biggest competitive gap.
3. **Token cost tracking in am_query** — Report how many tokens each recall result consumed. Enables ROI measurement.
4. **Observation streaming for Nancy** — SSE feed of agent observations to monitoring channels. Critical for the enterprise visibility story.
5. **Budget-aware progressive retrieval** — Two-phase query (index first, details on request) for large result sets.

## Detailed Research Documents

- [Core Architecture](/Users/alphab/.mdx/research/claude-mem-core-architecture.md)
- [Hooks & Context Injection](/Users/alphab/.mdx/research/claude-mem-hooks-context-injection.md)
- [Search & Retrieval](/Users/alphab/.mdx/research/claude-mem-search-retrieval.md)
- [Modes, Plugin & Advanced Features](/Users/alphab/.mdx/research/claude-mem-modes-features.md)
