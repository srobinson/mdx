---
title: "attention-matters Gap Analysis: Mapping Honcho Personalization Patterns to DAE Geometric Memory"
type: research
tags: [attention-matters, honcho, gap-analysis, personalization, geometric-memory, s3-hypersphere]
summary: "Systematic mapping of Honcho's personalization capabilities against am's current state, identifying gaps and geometric approaches to fill them."
status: active
source: codebase-analyst
confidence: high
created: 2026-03-22
updated: 2026-03-22
---

## Executive Summary

attention-matters (am) is a 23K LOC Rust workspace implementing the DAE (Daemon Attention Engine), a geometric memory system representing identity as continuous orientation on the S3 hypersphere using quaternions. It provides 12 MCP tools for query, ingestion, feedback, and context composition. Compared to Honcho's text-based personalization pipeline (Deriver/Dialectic/Dreamer), am has strong geometric foundations but lacks several capabilities needed for a complete personalization vertex: automated observation extraction from conversations, offline consolidation, perspectival memory, derivation lineage, and cached biographical summaries.

## 1. Current am Capabilities

### Data Model

The DAE system has a three-level hierarchy:

| Entity | Purpose | Key Fields |
|--------|---------|------------|
| **Episode** | Collection of neighborhoods (one document/conversation) | `id`, `name`, `is_conscious`, `timestamp`, `neighborhoods[]` |
| **Neighborhood** | Cluster of word occurrences around a seed on S3 (~3 sentences) | `id`, `seed: Quaternion`, `occurrences[]`, `source_text`, `neighborhood_type`, `epoch`, `superseded_by` |
| **Occurrence** | Single word instance on the manifold | `word`, `position: Quaternion`, `phasor: DaemonPhasor`, `activation_count`, `id`, `neighborhood_id` |

Supporting types:
- **Quaternion**: Unit quaternion (w, x, y, z) on S3. Operations: SLERP, geodesic distance, weighted centroid, Hamilton product, random/random_near.
- **DaemonPhasor**: Phase angle on the unit circle with golden-angle spacing. Used for interference computation.
- **NeighborhoodType**: Enum of `Memory | Decision | Preference | Insight | Ingested`. Decisions score 3x and get `[DECIDED]` prefix in recall. Preferences get `[PREFERENCE]` prefix.

### Storage

SQLite-backed (rusqlite) via `am-store`. Single `brain.db` file at `~/.attention-matters/`. Schema v7 with WAL mode, foreign keys, compound indexes for GC. Conversation buffer table for accumulating exchanges before episode creation.

### Geometric Operations

**Query pipeline** (`QueryEngine::process_query`):
1. Tokenize query, deduplicate words
2. Activate all matching occurrences across all episodes (increment `activation_count`)
3. Drift activated occurrences toward each other (pairwise SLERP for <200 mobile, centroid-based for larger sets)
4. Compute interference between subconscious and conscious occurrences
5. Apply Kuramoto phase coupling between co-activated words

**Scoring** (`rank_candidates`): IDF-weighted activation score, phasor interference modulation, vividness boost (>50% surfaced occurrences), recency decay (hyperbolic, 0.01 rate), overlap suppression (contradiction proxy via word overlap threshold), decision/preference 3x multiplier, diminishing returns on repeated recall.

**Context composition**: Three recall categories (Conscious, Subconscious, Novel). Budget-aware composition with configurable token limits and min-entries per category.

**Feedback loop** (`apply_feedback`): Boost SLERPs occurrences toward query centroid (0.15 factor * IDF * plasticity). Demote reduces activation_count by 2 (saturating), increasing plasticity and GC eligibility.

### MCP Tool Surface (12 tools)

| Tool | Purpose |
|------|---------|
| `am_query` | Full query pipeline with optional token budget |
| `am_query_index` | Two-phase retrieval: compact index (IDs, scores, summaries) |
| `am_retrieve` | Fetch full content for selected neighborhood IDs |
| `am_activate_response` | Strengthen connections from assistant response text |
| `am_salient` | Mark text as conscious memory (decisions, preferences, insights) |
| `am_buffer` | Buffer conversation exchange, auto-episode after 3 exchanges |
| `am_ingest` | Ingest document as memory episode |
| `am_stats` | System statistics (N, episodes, conscious count, DB size) |
| `am_export` | Export full DAE state as JSON |
| `am_import` | Import full DAE state from JSON |
| `am_feedback` | Boost/demote recalled neighborhoods |
| `am_batch_query` | Multi-query with amortized IDF |

### Consolidation Mechanisms (existing)

- **Drift**: Occurrences that co-activate move closer on S3 (convergent SLERP). This is automatic during every query.
- **Phase coupling**: Kuramoto-style synchronization of phasors for words appearing in both conscious and subconscious.
- **Supersession**: `am_salient` can mark old neighborhoods as superseded by new ones. Superseded neighborhoods are excluded from recall.
- **GC**: Two-phase garbage collection. Phase 1 evicts zero-activation occurrences outside grace window. Phase 2 aggressively targets coldest occurrences to hit size target. Respects epoch grace window and retention days.
- **Session sync**: CLI can parse Claude Code session transcripts (`.jsonl`) and extract episodes, chunked at 5 exchanges per episode.

---

## 2. Observation Extraction Pipeline

### What Honcho Does

Honcho's **Deriver** is a queue-consuming LLM agent that extracts "explicit atomic facts" from every message. Each observation is a natural language string with embedding vector, stored as a `Document` in an observer-observed `Collection`. Observations are deduplicated via embedding similarity before saving.

### What am Has

am does **not** extract atomic facts or observations from conversations. Its ingestion model is:

1. **`am_buffer`**: Accumulates raw user/assistant exchange pairs. After 3 exchanges, concatenates them and passes through `ingest_text()`, which tokenizes and chunks the text into neighborhoods. The raw text is preserved in `source_text` but no semantic extraction occurs.

2. **`am_salient`**: Manual promotion. The AI agent explicitly marks important insights, decisions, or preferences. This is the closest analog to observation extraction, but it is agent-initiated, not automatic.

3. **`am_ingest`**: Document ingestion. Text is chunked into neighborhoods. No extraction of discrete facts.

4. **Session sync**: Parses session transcripts into episodes. Extracts user text, assistant text, and thinking content. No semantic analysis.

### Gap

am stores raw text chunks as neighborhoods. Honcho extracts semantic observations. These are fundamentally different representations:

- am neighborhood: "We discussed using quaternions for geometric memory. The S3 hypersphere gives us nice algebraic properties for composition."
- Honcho observation: "Stuart prefers quaternion-based geometric representations for memory systems."

### What It Would Take

An observation extraction pipeline for am would need to:

1. **LLM extraction layer**: An async process (or tool-time hook) that takes buffered/ingested text and extracts atomic facts. This would be a new module, likely in `am-cli` since `am-core` is pure math with zero I/O.

2. **Observation as typed neighborhood**: Extracted observations could be stored as neighborhoods with `neighborhood_type: Preference | Decision | Insight | Memory`, with `source_text` containing the extracted fact rather than the raw chunk. The geometric position would inherit from the source neighborhood's seed (or its centroid), placing the observation near its origin on S3.

3. **Provenance tracking**: New field on Neighborhood linking back to source neighborhood ID(s). Currently neighborhoods have `superseded_by` but no `derived_from`.

4. **Deduplication**: Before storing an extracted observation, check for existing neighborhoods with high word overlap (the existing `overlap_suppress` logic in scoring could be adapted). The geometric analog: if a new observation's seed is within NEIGHBORHOOD_RADIUS of an existing one with >70% token overlap, skip or merge.

The key design decision: should extraction happen inline (blocking on `am_buffer`/`am_ingest`) or as a background queue? am currently has no async runtime or background workers. A queue approach would require either:
- A separate process (like Honcho's deriver)
- A hook-triggered CLI command
- An async task spawned from the MCP server

The simplest path: a new MCP tool `am_extract` that the agent calls after buffering, or hooking into `am_buffer`'s episode creation to auto-extract.

---

## 3. Offline Consolidation (Dreamer Pattern)

### What Honcho Does

Honcho's **Dreamer** runs during user idle periods and performs two-phase consolidation:
- **Deduction specialist**: Creates deductive observations from explicit facts, deletes duplicates.
- **Induction specialist**: Identifies patterns across all observations, creates generalized inductive observations.
- **Optional surprisal sampling**: Builds spatial index trees from embeddings, computes geometric novelty, feeds high-surprisal observations to specialists.

### What am Has

am has no offline consolidation. Its consolidation is entirely **online**, driven by query-time drift:

1. **Drift-on-query**: Every `am_query` and `am_activate_response` call triggers SLERP drift between co-activated occurrences. Over time, related concepts converge on S3.
2. **GC**: Removes cold occurrences. This is eviction, not consolidation.
3. **Supersession**: Manual via `am_salient` with `supersedes` array. Not automated.

### Gap

No mechanism for:
- Discovering redundant neighborhoods that should be merged
- Generating higher-order insights from accumulated memories
- Identifying under-explored regions of S3
- Cleaning up contradictions between old and new information automatically

### What Geometric Consolidation on S3 Would Look Like

This is where am's architecture offers unique possibilities that Honcho cannot match:

1. **Neighborhood merging via centroid convergence**: Identify pairs of neighborhoods whose seeds have drifted within `NEIGHBORHOOD_RADIUS` of each other and share >N% token overlap. Merge them into a single neighborhood with the weighted centroid as the new seed. This is algebraically clean: `Quaternion::weighted_centroid` already exists.

2. **Manifold density analysis**: Compute the distribution of neighborhood seeds on S3. Dense clusters suggest redundancy (candidates for merging). Sparse regions suggest under-explored territory (candidates for active exploration prompts). The geometric analog of Honcho's surprisal trees, but native to S3 rather than bolted onto embedding space.

3. **Phase coherence consolidation**: Identify neighborhoods where occurrences have high phasor coherence (low phase variance) across multiple query contexts. These are stable associations. Promote them to conscious memory automatically.

4. **Epoch-weighted contradiction resolution**: When two neighborhoods with high word overlap have divergent seeds (angular distance > threshold), the newer one (higher epoch) supersedes the older. This is the geometric equivalent of Honcho's deduction specialist resolving contradictions, but based on manifold geometry rather than LLM reasoning.

5. **Activation decay sweep**: Periodically reduce all activation counts by 1 (saturating at 0), implementing a geometric forgetting curve. This differs from GC (which removes) by making memories more plastic (higher drift rate) rather than deleting them.

Implementation path: A `consolidate` CLI command or scheduled hook that loads the system, runs the consolidation algorithms, and persists the result. No LLM needed for steps 1-5. Step 3 could optionally use an LLM to validate before promoting.

---

## 4. Perspectival Memory (Observer-Observed)

### What Honcho Does

Honcho uses directional `(observer, observed, workspace)` tuples for `Collection` entities. Alice observing Bob and Bob observing Alice produce independent observation sets. This is genuine perspectival memory: the same interaction generates different facts depending on whose perspective is being modeled.

### What am Has

am has a single global manifold per `brain.db`. There is one `DAESystem` per process, identified by `agent_name`. All memories exist in one shared geometric space. There is no concept of:
- Multiple observers
- Directional observation
- Per-entity memory partitions

The `agent_name` field on `DAESystem` identifies whose memory this is (the AI agent), but it does not support modeling the user's perspective or third parties.

### Gap

am cannot answer "What does Alice know about Bob?" vs "What does Bob know about Alice?". All memories occupy a single S3 manifold regardless of source or perspective.

### How This Would Map to S3

Two possible approaches:

**Approach A: Multi-manifold (simplest)**

Separate `DAESystem` instances per observer-observed pair. Each pair gets its own region of storage. This mirrors Honcho's architecture directly. Tradeoff: no cross-perspective geometric operations (cannot compute angular distance between Alice's model of Bob and Bob's model of Alice).

**Approach B: Labeled submanifolds (geometrically rich)**

Single S3 manifold with observer/observed metadata on each neighborhood. Add `observer: String` and `observed: String` fields to `Neighborhood`. Query filters by perspective. Geometric operations naturally cross perspectives: if Alice's observation of Bob and Bob's self-observation are nearby on S3, this signals agreement. If they are distant, this signals divergent perspectives. This enables a unique capability: **perspective alignment as angular distance**.

Approach B is more aligned with am's philosophy of geometric identity and would give am a capability Honcho cannot express: quantifying how aligned two observers' models of the same entity are.

---

## 5. Observation Hierarchy and Lineage

### What Honcho Does

Honcho Documents have:
- `level`: explicit / deductive / inductive
- `source_ids`: JSON array of document IDs forming a DAG
- `times_derived`: Counter for how often an observation has been referenced

This creates a reasoning chain: explicit facts -> deductive conclusions -> inductive generalizations, with full provenance.

### What am Has

am neighborhoods have:
- `neighborhood_type`: Memory / Decision / Preference / Insight / Ingested
- `superseded_by`: Optional UUID pointing to a replacing neighborhood
- `epoch`: Monotonic creation order

There is no:
- Derivation levels (explicit vs inferred)
- Source tracking (which neighborhoods produced this one)
- Derivation chains

`superseded_by` is one-directional replacement, not a DAG. It says "this old memory was replaced by this new one" but cannot express "this conclusion was derived from these three facts."

### Gap

am cannot trace why a memory exists. If a Preference neighborhood was created from insights gathered across multiple conversations, there is no record of that derivation. This makes it impossible to:
- Invalidate derived memories when their sources are proven wrong
- Explain reasoning chains ("I believe X because of Y and Z")
- Weight derived memories by the strength of their sources

### What It Would Take

1. **New field on Neighborhood**: `derived_from: Vec<Uuid>` (optional, empty by default). When `am_salient` or a future extraction pipeline creates a neighborhood from existing ones, it records the source IDs.

2. **Derivation level**: Extend `NeighborhoodType` or add a parallel enum:
   - `Explicit`: Direct from raw input (existing Memory, Ingested types)
   - `Curated`: Agent-promoted (existing Decision, Preference, Insight types)
   - `Inferred`: System-derived through consolidation (new)

3. **Cascade invalidation**: When a source neighborhood is superseded or GC'd, flag its derived neighborhoods for review. The geometric signal: if a derived neighborhood's seed was near its sources' centroid but the sources have moved or been removed, the derived memory may be stale.

4. **Schema migration**: Add `derived_from TEXT` (JSON array of UUIDs) and `derivation_level TEXT DEFAULT 'explicit'` columns to the neighborhoods table. Schema v8.

---

## 6. Peer Cards / Cached Summaries

### What Honcho Does

Honcho maintains 40-fact biographical summaries ("peer cards") in peer `internal_metadata`. These are updated by the Dreamer's specialists with a hard cap on facts and case-insensitive deduplication. They serve as fast-access context: instead of running a full memory search, the peer card gives the AI a quick summary of everything known about an entity.

### What am Has

am has no equivalent. The closest construct is **conscious memory** (neighborhoods in the conscious episode), which are manually curated insights that persist across sessions. But:
- Conscious memories are individual neighborhoods, not a unified summary
- There is no fact cap or deduplication within conscious memory
- There is no automatic summary generation
- Conscious memory is per-agent, not per-entity

The `am_stats` tool returns system-level statistics, not entity summaries.

### Gap

am cannot produce "here are the top 40 facts about this user" without running a full query pipeline. This means every session start requires a query, and the quality of recall depends on the query text matching the right words.

### What It Would Take

Two approaches, depending on whether the summary should be geometric or textual:

**Approach A: Textual peer card (pragmatic)**

A new MCP tool `am_peer_card` that returns a cached, periodically-refreshed summary. Implementation:
- New metadata key in the `metadata` table: `peer_card` storing a JSON summary
- Updated by consolidation or by a new `am_update_peer_card` tool
- Requires LLM to synthesize facts from top-scoring neighborhoods into a coherent summary
- Capped at N facts, deduplicated

**Approach B: Geometric identity vector (native)**

The "peer card" is a quaternion: the weighted centroid of all conscious neighborhoods plus the highest-activation subconscious neighborhoods. This single quaternion represents the entity's current identity orientation on S3. To retrieve a summary, query neighborhoods near this identity centroid.

This is more aligned with am's design. The identity vector can be cheaply maintained (updated incrementally on every `am_salient` and `am_feedback`) and used for:
- Fast nearest-neighbor lookup without full query pipeline
- Cross-session identity continuity (the centroid drifts but never jumps)
- Multi-entity comparison (angular distance between identity vectors)

A hybrid approach: maintain both the geometric identity vector (for fast retrieval and geometric operations) and an LLM-synthesized peer card (for human-readable summaries, refreshed during consolidation).

---

## Summary Matrix

| Capability | Honcho | am Current | Gap Severity | Suggested Approach |
|-----------|--------|-----------|-------------|-------------------|
| Observation extraction | Deriver agent (LLM-powered, automatic) | None. Raw text chunking only. Manual via `am_salient`. | **High** | LLM extraction hook on `am_buffer` episode creation, or new `am_extract` tool |
| Offline consolidation | Dreamer (deduction + induction specialists) | Online drift only. No background processing. | **High** | Geometric consolidation: centroid merging, density analysis, phase coherence promotion |
| Perspectival memory | Observer-observed Collections | Single global manifold | **Medium** | Labeled submanifolds (observer/observed fields on Neighborhood) |
| Derivation hierarchy | explicit/deductive/inductive levels with source_ids DAG | Types exist (Memory/Decision/Preference/Insight) but no derivation tracking | **Medium** | `derived_from: Vec<Uuid>` field, derivation_level enum |
| Peer cards | 40-fact biographical summaries | No equivalent | **Medium** | Geometric identity vector (quaternion centroid) + optional LLM peer card |
| Deduplication | Embedding similarity pre-check | Word overlap suppression in scoring (recall-time only) | **Low** | Adapt overlap_suppress logic to write-time dedup in `am_salient` and extraction |

### Priority Ordering

1. **Observation extraction** and **offline consolidation** are the two highest-value gaps. They are also synergistic: extraction produces the raw material that consolidation refines. Without extraction, am's memory fidelity depends entirely on the AI agent's judgment about what to buffer and what to mark salient. Without consolidation, the manifold grows monotonically and never self-organizes beyond query-time drift.

2. **Derivation hierarchy** enables cascade invalidation and explainable memory, which become critical once extraction and consolidation are producing derived memories automatically.

3. **Perspectival memory** matters for multi-agent scenarios (nancyr, helioy-bus) but is not blocking for single-agent use.

4. **Peer cards** are an optimization. The current query pipeline serves the same purpose, just with higher latency and less consistent results.

### What am Already Does Better Than Honcho

- **Geometric contradiction detection**: Overlap suppression via word overlap threshold + epoch ordering handles contradictions at recall-time without LLM calls. Honcho requires the Dialectic agent to surface contradictions.
- **Continuous identity evolution**: Drift and phase coupling reshape the manifold continuously. Honcho's identity is append-only between Dream cycles.
- **Algebraic composability**: Quaternion multiplication, SLERP, and weighted centroids enable operations on identity that text observations cannot express.
- **Zero LLM dependency on write path**: `am_buffer` and `am_ingest` require no LLM calls. Honcho's Deriver calls an LLM for every message.
- **Cost structure**: am's geometric operations are O(n) or O(n^2) in CPU, not LLM API calls. A full query-drift-compose cycle costs microseconds of compute, not dollars of API usage.
- **Feedback as manifold reshaping**: `am_feedback` physically moves occurrences on S3 (boost) or decays their anchoring (demote). This is reinforcement learning on the geometry itself, something Honcho's text-based observations cannot express.

## Key File References

| File | LOC | Purpose |
|------|-----|---------|
| `crates/am-core/src/system.rs` | 697 | DAESystem: episodes, indexes, activation |
| `crates/am-core/src/quaternion.rs` | 654 | S3 math: SLERP, distance, centroids |
| `crates/am-core/src/query.rs` | 949 | QueryEngine: drift, interference, Kuramoto |
| `crates/am-core/src/compose.rs` | 2,370 | Context composition with budget control |
| `crates/am-core/src/scoring.rs` | 501 | IDF scoring, overlap suppression, vividness |
| `crates/am-core/src/feedback.rs` | 573 | Boost/demote reinforcement signals |
| `crates/am-core/src/neighborhood.rs` | 252 | Neighborhood struct, types, from_tokens |
| `crates/am-core/src/occurrence.rs` | 196 | Occurrence: word on manifold |
| `crates/am-core/src/episode.rs` | 175 | Episode: collection of neighborhoods |
| `crates/am-core/src/surface.rs` | 449 | Surface computation: vivid detection |
| `crates/am-cli/src/server.rs` | 2,169 | MCP server: 12 tool handlers |
| `crates/am-store/src/schema.rs` | 391 | SQLite schema v7 |
| `crates/am-store/src/store/gc.rs` | 274 | Garbage collection |
| `crates/am-store/src/config.rs` | 615 | Configuration with retention policy |
| `crates/am-cli/src/sync.rs` | 1,085 | Session transcript parsing |
