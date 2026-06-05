---
title: "Helix Three Vertices: Concrete Plan of Action"
type: project
tags: [helix, architecture, roadmap, personalization, audit, context, honcho, ahp]
summary: "Actionable plan for completing Helix's three required vertices: intelligent context (solid), personalization (gaps in am), and audit (missing entirely). Synthesized from competitive analysis of Honcho and AHP plus three architectural design studies."
status: active
confidence: high
created: 2026-03-22
updated: 2026-03-22
---

## The Thesis

Helix is not one vertex of a competitive triangle. It IS the triangle. Three capabilities are required for completeness:

| Vertex | Question it answers | Current state |
|--------|-------------------|---------------|
| Intelligent Context | "What does this agent know?" | Solid (cm + mdm + LLM curation) |
| Personalization | "What matters and to whom?" | Partial (am has the representation, lacks the pipeline) |
| Audit | "What happened, who caused it, can we trust it?" | Missing entirely |

CRITIC (the system evolver) needs all three: audit trail proving what changed, entity models informing what "better" means, intelligent context as the substrate being evolved.

## Research Base

Five documents inform this plan:

1. `~/.mdx/research/honcho-plastic-labs-analysis.md` -- Honcho competitive analysis
2. `~/.mdx/research/agent-history-protocol-analysis.md` -- AHP competitive analysis
3. `~/.mdx/research/attention-matters-gap-analysis.md` -- am current state vs Honcho capabilities
4. `~/.mdx/research/helix-audit-vertex-design.md` -- Audit vertex architecture
5. `~/.mdx/research/helix-personalization-vertex-design.md` -- Personalization vertex architecture

## Architectural Decisions (Settled)

These emerged consistently across all three design studies:

### AD-1: Audit is cross-cutting infrastructure, not a fourth adapter
Adapters transform context into representations. Audit records what happened to context. Different contract. Audit lives at the Helix proxy level, observing every adapter interaction.

### AD-2: Observer and Consolidator live at Helix level, not inside am-core
am-core is pure math with zero I/O. Observation extraction and consolidation are LLM-powered processes that route results TO am through existing APIs (am_buffer, am_salient, am_ingest). am-core stays clean.

### AD-3: cm stores what IS, am stores what MATTERS
Honcho conflates facts and values in a single observation store. Helix separates them. The Observer classifies and routes: facts to cm, value signals to am. When an observation carries both, it writes to both.

### AD-4: Perspectives are reference frame rotations, not data copies
Multiple observers see the same S3 manifold from different orientations via Hamilton product rotation. Zero data duplication. Agent perspectives form naturally from query history centroids with decreasing plasticity.

### AD-5: Derivation lineage lives in cm
am's representation is continuous (neighborhoods drift and interfere). Explicit derivation DAGs suit cm's structured entries. am gets a new NeighborhoodType::Synthesized variant for consolidation output.

### AD-6: Three graduated audit levels
L1 (operation log): content hashing, gap records, mutation table extensions. L2 (provenance trail): centralized store, read-path audit, CRITIC records. L3 (verifiable audit): signed checkpoints, AHP-compatible export, OTLP.

---

## Implementation Plan

### Phase 1: Foundation (Observer + cm schema)

**Goal**: Automated observation extraction from conversations, routed to cm (facts) and am (values).

**Deliverables**:

1. **Observer component** at Helix level
   - LLM-powered classification prompt: fact vs value vs structural (discard)
   - Batch processing (5 turns per batch, matching am's episode chunking)
   - Facts route to cm with `derivation_level: explicit`, `source: observer`
   - Value signals route to am via `am_buffer` (subconscious only)
   - Opt-in per workspace configuration
   - Start with conservative classifier (ambiguous observations default to cm)

2. **cm schema extensions**
   - Add `derivation_level` field: explicit | deductive | inductive
   - Add `derived_from` field: array of source entry IDs
   - Add `agent_id` field to mutations table
   - Add `session_id` field to mutations table
   - Migration for existing entries (default: explicit, empty derived_from)

3. **Context gaps table**
   - `context_gaps` table with structured reason codes
   - `payload_hint` field (approximate description of lost content)
   - `resolved` / `resolved_by` fields for gap filling
   - Recall responses include `gaps` field so agents know what they don't know

**Dependencies**: None. Can start immediately.
**Risk**: Observer classification quality determines pipeline value. The fact/value boundary needs iteration.

### Phase 2: Geometric Consolidation (The Dreamer on S3)

**Goal**: Offline consolidation that transforms accumulated geometry into higher-order structure.

**Deliverables**:

1. **Consolidator: Phase 1 -- Geometric Deduction (cluster analysis)**
   - Identify neighborhood clusters that have drifted close on S3 via geodesic distance
   - Generate synthesis neighborhoods (LLM distillation of cluster content)
   - Write via `am_salient` for owner review
   - Add `NeighborhoodType::Synthesized` variant to am-core

2. **Consolidator: Phase 2 -- Geometric Induction (tension detection)**
   - Find near-antipodal high-activation neighborhood pairs (angular distance > 0.7*pi)
   - Generate tension records (LLM synthesis of what the tension is)
   - Route tensions to cm as structured entries with kind: tension
   - Surface to owner via CRITIC for resolution

3. **Consolidator: Phase 3 -- Manifold Pruning (pre-GC consolidation)**
   - Before GC runs, extract unique content from GC candidates
   - Migrate to nearest active neighborhood or create new one
   - Prevents information loss during eviction

4. **Scheduling and fingerprinting**
   - Consolidation triggered by idle detection or daily cron
   - Consolidation fingerprints (hash of participating neighborhood IDs) prevent reprocessing

**Dependencies**: Phase 1 (Observer populates the raw material Consolidator refines).
**Risk**: Consolidator needs read access to am's full state. Direct store access vs MCP export tradeoff (131MB brain.db). Recommend direct read-only SQLite connection.

### Phase 3: Audit Infrastructure

**Goal**: Provenance tracking, gap documentation, and the foundation for CRITIC accountability.

**Deliverables**:

1. **L1 audit capabilities**
   - Extend cm mutations table: `auth_type`, `auth_id`, `derived_from`, `proxy_rationale`
   - BLAKE3 content hashing on provenance records
   - Lightweight `prev_record_hash` chain within adapter scope
   - Context gaps integration (from Phase 1 deliverable 3)

2. **Helix proxy RequestContext**
   - Per-request UUID, agent_id, session_id, operation, adapter_calls
   - The spine that makes cross-adapter correlation possible
   - Flows through the entire operation lifecycle

3. **L2 centralized provenance store** (when proxy exists)
   - Single provenance table across all adapters
   - Write-path audit: what was stored, who routed it, why
   - Read-path audit: candidate set, what was filtered, curation reasoning
   - Optional read receipts

4. **Fail-open discipline**
   - Audit failures never block context operations
   - Gap records for audit failures (gap of a gap)
   - All Helix MCP tools handle errors gracefully

**Dependencies**: Phase 1 (cm schema extensions). The Helix proxy itself must exist for L2.
**Risk**: Proxy rationale storage cost. Recommend storing rationale only for write operations initially, sample for reads.

### Phase 4: Perspectival Memory

**Goal**: Multiple observers see the same manifold from different orientations.

**Deliverables**:

1. **Agent perspective tracking**
   - Record query centroids during am queries
   - Compute perspective quaternion via SLERP-weighted average of query centroids
   - Plasticity decreases with query count: `1 / (1 + ln(1 + count))`
   - Store in cm as structured entry: {agent_id, perspective quaternion, query_count, last_updated}

2. **Perspective-biased recall**
   - Compose scoring adds angular proximity bonus relative to agent's perspective
   - Owner perspective is identity quaternion (unbiased, default behavior)
   - CRITIC perspective computed from mission/evaluation criteria

3. **Perspective alignment metric**
   - Angular distance between observers' perspectives quantifies alignment
   - Novel capability neither Honcho nor AHP can express

**Dependencies**: Phase 2 (Consolidator must exist so perspectives have meaningful structure to view).
**Risk**: Low. Pure math additions. Zero changes to am-core's data model. Sub-millisecond compute cost.

### Phase 5: CRITIC Integration

**Goal**: Close the loop. CRITIC evolves the system using am as fitness function, with full audit trail.

**Deliverables**:

1. **CRITIC mutation records**
   - Genome unit, mutation type, hypothesis, before/after state hashes
   - Baseline and mutated metrics
   - `am_alignment` field: how mutation aligns with am's value landscape
   - Approved_by, phase (1-4 evolution stages), confidence, review_after
   - Reverts are new records, not deletions

2. **Promotion recommendation pipeline**
   - Consolidator output -> CRITIC evaluation -> owner notification
   - Suggested promotion thresholds (recall count, feedback history)
   - Workspace-level policy for CRITIC delegation authority

3. **Genome versioning**
   - Monotonic version increments on adopted mutations
   - Version history as audit trail
   - Revert creates new version, links to original

**Dependencies**: Phases 1-4 (all vertices must be operational).
**Risk**: CRITIC is the highest-risk component. Mutations change system behavior. Start at Phase 1 of CRITIC evolution (owner IS the critic) and progress through the four phases documented in docs.llm/1010.THE_CRITIC.

---

## Patterns Adopted from Research

| Pattern | Source | Where it lands | Phase |
|---------|--------|---------------|-------|
| Observation extraction (Deriver) | Honcho | Observer at Helix level | 1 |
| Offline consolidation (Dreamer) | Honcho | Consolidator with geometric operations | 2 |
| Configurable reasoning depth | Honcho | `helix recall --depth` (5 levels) | 1 |
| Observation lineage DAG | Honcho | cm `derived_from` + `derivation_level` | 1 |
| RRF hybrid search | Honcho | Tantivy BM25 + vector similarity fusion | 1 |
| Content-addressed dedup | AHP | BLAKE3 pre-check on cm writes | 1 |
| Gap documentation | AHP | `context_gaps` table + recall response field | 1 |
| Fail-open discipline | AHP | All Helix MCP tools | 3 |
| Conformance levels | AHP | L1/L2/L3 graduated audit | 3 |
| OTLP export | AHP | Context operations as OpenTelemetry spans | 3 (L3) |
| Per-agent config overrides | AHP | Workspace-level Observer/audit configuration | 1 |
| W3C Trace Context | AHP | Cross-agent context propagation via helioy-bus | 3 (L3) |
| Perspectival memory | Honcho | Reference frame rotations on S3 | 4 |
| Peer cards / cached summaries | Honcho | Geometric identity vector (weighted centroid) | 2 |

## Patterns NOT Adopted (and why)

| Pattern | Source | Why not |
|---------|--------|---------|
| Text-only observations | Honcho | am's geometric representation is strictly more expressive |
| No write-path quality gating | Honcho | Helix's curation-on-write is fundamentally superior |
| Full hash chain protocol | AHP | Operational weight not justified for single-owner deployment. L1 lightweight chain suffices; L3 AHP-compatible export available when needed |
| Postgres-as-queue | Honcho | Helix is Rust/SQLite-native. No need for PG coupling |
| LLM dependency on every write | Honcho | am's geometric operations are O(n) CPU, not API calls |
| Embedding-based dedup | Honcho | am uses geometric position on S3. No embedding API needed |
| Separate Dialectic agent | Honcho | `helix recall` already queries all adapters. Redundant |

## Open Questions (Requiring Decision)

1. **Observer model selection**: Same model as Helix write-path LLM, or cheaper (Haiku/Flash) for high-volume extraction? The fact/value classification task is simpler than full observation extraction.

2. **Consolidator access pattern**: Direct SQLite read on brain.db (fast, schema-coupled) vs MCP export (clean, slow for 131MB)? Recommend direct read-only connection.

3. **Consolidation frequency**: Daily cron vs idle detection? Idle detection is more aligned with Honcho's Dreamer but harder in multi-agent environments.

4. **Tension resolution UX**: How does the owner interact with surfaced tensions? New CLI command? Notification? cm-web dashboard?

5. **Perspective inheritance**: When Agent A is replaced by Agent B in the same role, does B inherit A's perspective quaternion? Ties into nancy's agent lifecycle.

6. **Provenance retention policy**: How long are provenance records kept? Should they inherit entry lifecycle or have independent retention?

7. **CRITIC audit storage**: Git-tracked files (versioned alongside genome) or provenance database (queryable)?

## Success Criteria

Helix covers all three vertices when:

1. **Personalization**: An agent can query `helix recall` and receive context shaped by both structured facts (cm) and geometric identity (am), with observations automatically extracted from conversations and consolidated offline. The owner's values influence recall without the owner manually tagging every interaction.

2. **Audit**: Every context operation has provenance. Failed writes are documented as gaps. Agents know what they don't know. CRITIC mutations are auditable with am alignment justification. The system can answer "why does this agent believe X?" by tracing the derivation chain.

3. **CRITIC closure**: The system evolves toward the owner's vision, not just toward efficiency. Mutations are justified against am's value landscape. The audit trail proves alignment. The owner can verify at any point that evolution is on track.

The competitive moat: no other system combines LLM-curated intelligent context, geometric identity, and provenance-tracked audit in a single agent-facing API. Honcho has personalization without quality gating. AHP has audit without intelligence. Helix has all three.
