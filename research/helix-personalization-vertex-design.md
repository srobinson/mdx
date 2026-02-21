---
title: "Helix Personalization Vertex: Architectural Design"
type: research
tags: [helix, attention-matters, personalization, architecture, geometric-memory, observation-lifecycle]
summary: "Design for bridging am's geometric identity with Honcho-style observation capabilities while preserving am's mathematical integrity and owner-write constraint"
status: active
source: software-architect
confidence: high
created: 2026-03-22
updated: 2026-03-22
---

## Design Thesis

The personalization vertex has two distinct concerns that current am conflates into a single entry point: **identity formation** (what is becoming true through dialogue) and **observation capture** (what was said or done). Honcho treats both as text observations. am treats neither as observations. The correct architecture separates them into a pipeline where observations are the *input* and geometric identity is the *output*, with a consolidation process that transforms one into the other.

am should not become Honcho. am's power is its mathematical representation. What am lacks is a *feeder system* that converts raw conversational signal into the geometric operations am already supports. That feeder system belongs at the Helix level, where it can draw from all adapters (cm, mdm, fmm) rather than operating in isolation.

## Architecture Overview

```
Conversations (raw dialogue)
        |
        v
  Observation Extractor          <-- Helix-level capability (new)
  (LLM-powered, async)
        |
        +---> cm: atomic facts    (structured entries, scoped, tagged)
        +---> am: value signals   (geometric encoding on S3)
        |
        v
  Consolidator                   <-- Helix-level scheduled process (new)
  (geometric dreaming)
        |
        +---> am: identity evolution  (manifold reshaping)
        +---> cm: derived insights    (deductive/inductive observations)
```

Three new capabilities. None live inside am-core.

## ADR-001: Observation Extraction as Helix-Level Capability

### Status
Proposed

### Context
am requires explicit writes via `am_salient`, `am_buffer`, or `am_ingest`. Agents must decide what to write and when. This creates two problems: agents write too little (missing observations they don't recognize as important), and the owner must manually curate through DECISION/PREFERENCE/insight prefixes.

Honcho's Deriver solves this by extracting "explicit atomic facts" from every message. But Honcho conflates facts (cm's domain) with values (am's domain). Helix should separate them.

### Decision
Observation extraction lives at the Helix level as a new component: the **Observer**. It runs on the write path when conversations are saved, operating as a background processor similar to am's existing `am sync` hook. The Observer is LLM-powered and produces two output types:

1. **Factual observations** routed to cm as structured entries with `derivation_level: explicit` and `source: observer` metadata.
2. **Value signals** routed to am as typed geometric writes (decisions, preferences, insights, tensions).

The Observer does not write raw text to am. It translates observations into am's existing vocabulary: `am_salient` with DECISION/PREFERENCE prefix, or `am_buffer` for conversational context. am's tokenizer, neighborhood placement, and golden-angle phasor spacing handle the geometric encoding. The Observer's job is *classification and routing*, not geometric math.

### Consequences
- am-core remains pure math with zero LLM dependency. No observation extraction logic enters the Rust codebase.
- The Observer can be swapped, tuned, or disabled without touching am.
- Factual observations go where facts belong (cm), preserving the am/cm boundary.
- The owner retains ultimate authority: Observer-generated value signals enter the subconscious manifold, not the conscious manifold. Only the owner (via explicit `am_salient`) promotes to conscious. This preserves write-only-for-owner on the conscious manifold while allowing automated population of the subconscious.
- Cost: every conversation now incurs an LLM call on the write path. Mitigated by batching (process N turns at once, matching am's existing 5-turn episode chunking) and by making the Observer optional per workspace configuration.

## ADR-002: The Boundary Between am and cm

### Status
Proposed

### Context
Honcho stores everything as text observations in collections. This conflates "Alice is 25 years old" (fact) with "Alice values simplicity over completeness" (identity). When you query Honcho, facts and values compete for the same retrieval surface. Helix must maintain clean separation.

### Decision
The boundary rule: **cm stores what IS. am stores what MATTERS.**

| Signal | Goes to | Rationale |
|--------|---------|-----------|
| "We use PostgreSQL" | cm | Fact. Structured, queryable, can become stale. |
| "We chose PostgreSQL because operational simplicity matters more than performance ceilings" | Both | The fact goes to cm. The value judgment ("simplicity > performance ceilings") goes to am. |
| "Stuart prefers terse responses" | am | Preference. Identity-level. Should influence all future agent behavior. |
| "The auth service is at /src/auth" | Neither (fmm) | Structural fact derivable from the codebase. |
| "We considered Redis but rejected it due to operational complexity" | cm | Decision record. Factual, with rationale. The underlying value ("operational complexity aversion") may separately go to am if it represents a pattern. |

The Observer classifies each extracted observation against this matrix. When an observation carries both fact and value, it writes to both systems. cm gets the full observation text. am gets the distilled value signal.

### Consequences
- Queries about "what do we use" hit cm. Queries about "how do we think" hit am. Clean separation.
- The Observer needs a classification prompt that reliably distinguishes facts from values. This is the hardest prompt engineering problem in the design. Start with a conservative classifier that routes ambiguous observations to cm only (facts are cheaper to store incorrectly than values).
- Duplicate detection spans two systems. The Observer should check cm for existing factual coverage before writing, using cm's BLAKE3 content hashing and Tantivy search. For am, deduplication happens geometrically (similar observations cluster into nearby regions of S3 and interfere naturally).

## ADR-003: Geometric Consolidation (The Dreamer Pattern on S3)

### Status
Proposed

### Context
Honcho's Dreamer runs deduction and induction specialists during idle periods. Deduction draws logical conclusions from explicit facts. Induction identifies patterns across many observations. Both produce new text observations stored alongside the originals.

am has no equivalent. Its manifold reshapes continuously through queries (drift, interference, Kuramoto coupling), but there is no offline process that synthesizes higher-order structure from accumulated geometry.

### Decision
The **Consolidator** is a Helix-level scheduled process that performs three geometric operations on am's manifold during idle periods.

**Phase 1: Geometric Deduction (Cluster Analysis)**

Identify neighborhood clusters that have drifted close together on S3 through repeated co-activation. When neighborhoods from different episodes have seed quaternions within a threshold angular distance (e.g., NEIGHBORHOOD_RADIUS / 2), and their constituent words overlap significantly, they represent converging insights.

The Consolidator:
1. Reads the current manifold state via `am_export` or direct store access.
2. Identifies convergent clusters using geodesic distance between neighborhood seeds.
3. For each cluster, generates a *synthesis neighborhood*: a new conscious-level neighborhood whose source text is an LLM-generated distillation of the cluster's combined source texts.
4. Writes the synthesis via `am_salient`, which the owner can then review and accept or reject.

This is geometric deduction: the manifold's topology reveals what concepts have converged, and the Consolidator makes that convergence explicit.

**Phase 2: Geometric Induction (Tension Detection)**

Identify regions of S3 where high-activation neighborhoods from different episodes are near-antipodal (angular distance approaching pi). Near-antipodal positions on S3 represent maximal geometric separation. When two strongly activated concepts occupy opposite poles, that is a *tension*: two things the system considers important but that point in contradictory directions.

The Consolidator:
1. Finds neighborhood pairs with high activation and angular distance > pi * 0.7.
2. Generates a *tension record*: an LLM-synthesized description of what the tension is and why it exists.
3. Routes the tension to cm as a structured entry with `kind: tension` and references to both source neighborhoods.
4. Optionally surfaces the tension to the owner via CRITIC for resolution.

This is geometric induction: the manifold's global structure reveals contradictions that no single query would surface. Honcho's induction specialist does this via text pattern matching. am does it through angular measurement. The geometric approach is more precise because angular distance on S3 is a continuous metric, unlike text similarity which is threshold-dependent.

**Phase 3: Manifold Pruning (GC-Aware Consolidation)**

Before am's existing GC runs, the Consolidator identifies neighborhoods that are GC candidates (low activation, old epoch) but whose *content* is partially represented in higher-activation neighborhoods. Rather than losing the information entirely through GC, the Consolidator:
1. Extracts unique content from GC-candidate neighborhoods that has no nearby representative in the active manifold.
2. Appends that content to the closest active neighborhood's source text (or creates a new neighborhood if no close candidate exists).
3. Allows GC to proceed normally.

This prevents information loss during GC by ensuring that the manifold's representational coverage is maintained even as specific neighborhoods are evicted.

### Consequences
- The Consolidator requires read access to am's full state (export or store query). This is compatible with am's read-only-for-agents constraint since the Consolidator reads am but writes through the existing `am_salient` and `am_buffer` APIs.
- Phase 1 and Phase 3 are safe (additive). Phase 2 produces tension records that require human judgment. The system should never auto-resolve tensions.
- Cost: periodic LLM calls for synthesis and tension description. Controlled by consolidation frequency (daily, or triggered by idle detection) and batch size (process top-N clusters/tensions per cycle).
- The Consolidator needs a concept of "already consolidated" to avoid re-processing. Track consolidated cluster fingerprints (hash of participating neighborhood IDs) in cm or a dedicated consolidation log.

## ADR-004: Perspectival Memory on S3

### Status
Proposed

### Context
Honcho tracks observer-observed directional observations. Alice observing Bob produces different observations than Bob observing Alice. Each direction is a separate Collection with independent Documents.

am currently has one manifold per brain (one global brain at `~/.attention-matters/brain.db`). There is no concept of "who is observing" or "from whose perspective."

### Decision
Perspectival memory maps to **reference frames on S3**. Each observer has a rotation (quaternion) that transforms the manifold into their frame of reference. The same underlying manifold is viewed from different orientations.

Implementation: am already supports this mathematically through Hamilton products. A perspective is a unit quaternion P. To view the manifold from P's perspective, every neighborhood seed is rotated by P's conjugate: `seed_in_P = P* . seed . P`. This rotates the entire manifold so that P's "forward direction" aligns with the identity quaternion (1,0,0,0).

Concretely:
- The owner's perspective is the identity quaternion. The manifold as stored is the owner's view. This is the default and current behavior.
- An agent's perspective is a quaternion computed from the agent's interaction history with am. An agent that primarily queries about "code quality" develops a perspective quaternion oriented toward the region of S3 where code-quality neighborhoods cluster. Its view of the manifold emphasizes concepts near its orientation and attenuates distant ones.
- CRITIC's perspective is computed from the mission statement and evaluation criteria, placing it in a frame where mission-aligned concepts are foregrounded.

This gives each observer a *natural filter* on the manifold without duplicating any data. The same neighborhoods exist once. Different observers see different relative importances based on their angular proximity to each neighborhood in their rotated frame.

**How agent perspectives form:**
1. Each time an agent queries am, the query centroid (IDF-weighted average of activated occurrence positions) is recorded.
2. Over multiple queries, the agent's perspective quaternion converges toward the SLERP-weighted average of its query centroids. Early queries have high plasticity (perspective shifts easily). Later queries have low plasticity (perspective stabilizes). This mirrors am's existing occurrence plasticity curve: `1 / (1 + ln(1 + c))`.
3. The perspective quaternion is stored in cm as a structured entry: `{agent_id, perspective: [w,x,y,z], query_count, last_updated}`.

**How perspective affects recall:**
When an agent queries am, compose adds a perspective bias to the scoring function. Neighborhoods whose seeds are closer to the agent's perspective quaternion (smaller angular distance after perspective rotation) receive a scoring bonus. This means each agent naturally surfaces the parts of the manifold most relevant to its interaction history, without any explicit filtering.

### Consequences
- Zero changes to am-core's data model. Perspectives are pure read-time transformations stored externally in cm.
- The owner's perspective is always identity (no rotation). This preserves the owner's unbiased view of the full manifold.
- Agent perspectives are ephemeral metadata. Losing them means agents start with a fresh perspective, which is acceptable for ephemeral agents.
- This approach cannot represent "Agent A's observations about Agent B" in the Honcho sense, because am stores values, not observations about entities. That use case belongs in cm (structured entries about entities). Perspectival memory in am answers a different question: "how does this observer relate to the identity manifold?" rather than "what does this observer know about that entity?"
- Computational cost is negligible. One Hamilton product per neighborhood seed per query. For a system with 41,017 occurrences across ~15 episodes, the rotation pass is sub-millisecond.

## ADR-005: Observation Lifecycle

### Status
Proposed

### Context
The full path from raw conversation to identity evolution needs a defined lifecycle with clear stages, ownership transitions, and quality gates.

### Decision

```
Stage 1: CAPTURE
  Input:  Raw conversation turns (user + assistant text)
  Actor:  am sync hook / helix save
  Output: Conversation buffer entries
  Gate:   None (capture everything)

Stage 2: EXTRACTION
  Input:  Buffered conversation turns (batched, 5 turns per batch)
  Actor:  Observer (Helix-level, LLM-powered)
  Output: Classified observations
           -> facts -> cm (derivation_level: explicit, source: observer)
           -> values -> am subconscious (via am_buffer/am_ingest)
           -> structural -> discarded (fmm handles this)
  Gate:   Observer classification prompt + cm dedup check (BLAKE3)
  Timing: Async, post-conversation. Triggered by am sync hook
          or helix save completion.

Stage 3: GEOMETRIC ENCODING
  Input:  Value signals arriving at am via am_buffer/am_ingest
  Actor:  am-core (tokenizer, neighborhood placement, phasor spacing)
  Output: Neighborhoods on S3 subconscious manifold
  Gate:   am's existing input size check (1MB cap)
  Timing: Synchronous with the write.

Stage 4: GEOMETRIC EVOLUTION
  Input:  Agent queries against the manifold
  Actor:  am-core QueryEngine (activate, drift, interfere, couple)
  Output: Reshaped manifold (positions, phases, activations updated)
  Gate:   None (every query reshapes the manifold)
  Timing: Synchronous with each query.

Stage 5: CONSOLIDATION
  Input:  Full manifold state (post-query accumulated changes)
  Actor:  Consolidator (Helix-level, scheduled)
  Output: Synthesis neighborhoods (deduction), tension records (induction),
          content migration (pre-GC pruning)
  Gate:   Owner review for conscious promotion.
          Consolidation fingerprint check to prevent reprocessing.
  Timing: Scheduled (daily or idle-triggered).

Stage 6: CONSCIOUS PROMOTION
  Input:  Synthesis neighborhoods from consolidation OR direct am_salient
  Actor:  Owner (explicit) or CRITIC (via owner delegation)
  Output: Conscious-manifold neighborhoods
  Gate:   Owner approval. This is the hard gate. Only the owner
          (or CRITIC acting with owner authority) promotes to conscious.
  Timing: Manual / on-demand.
```

### Ownership at each stage

| Stage | Who writes | Who reads | Constraint |
|-------|-----------|-----------|------------|
| Capture | Agents (via hooks) | Observer | Automatic |
| Extraction | Observer | cm, am | Observer classifies; am receives only value signals |
| Encoding | am-core | Nobody (internal) | Pure math, no external dependency |
| Evolution | am-core (triggered by agent queries) | Agents (via am_query) | Agents read results; queries reshape manifold |
| Consolidation | Consolidator | cm (tensions), am (synthesis candidates) | Consolidator reads am, writes to cm and am subconscious |
| Promotion | Owner / CRITIC | All agents | Owner-only gate to conscious manifold |

### Consequences
- Agents never write directly to am's conscious manifold. The constraint is preserved.
- Agents write to am's subconscious manifold indirectly, through the Observer's classification and am_buffer/am_ingest. They do not choose what goes to am. The Observer does.
- The owner sees consolidation outputs as candidates (subconscious or cm entries). Promotion to conscious requires explicit action.
- CRITIC uses am as its fitness function by reading the conscious manifold and comparing agent behavior against it. CRITIC can *recommend* promotions to the owner but cannot execute them unilaterally. (Unless the owner configures CRITIC with promotion authority, which is a workspace-level policy decision.)

## ADR-006: Observation Hierarchy and Derivation Tracking

### Status
Proposed

### Context
Honcho tracks explicit/deductive/inductive levels with source_ids forming a DAG. am has no derivation tracking. cm has no derivation tracking.

### Decision
Derivation tracking lives in cm, where observations are structured entries with metadata. am does not track derivation because its representation is continuous, and the concept of "this neighborhood was derived from those neighborhoods" is poorly suited to geometric memory where neighborhoods drift, merge, and interfere continuously.

cm entries gain two new fields:
- `derivation_level`: `explicit | deductive | inductive` (default: explicit)
- `derived_from`: array of cm entry IDs (default: empty)

The Observer writes at `explicit` level. The Consolidator writes at `deductive` (cluster synthesis) and `inductive` (tension detection) levels, with `derived_from` referencing the source entries or am neighborhood IDs that triggered the consolidation.

For am, lineage is encoded geometrically rather than explicitly. Neighborhoods that were created by the Consolidator carry a `neighborhood_type` of a new variant: `Synthesized`. This lets the scoring and composition logic treat synthesized neighborhoods differently (e.g., higher baseline activation, since they represent consolidated insight rather than raw observation).

### Consequences
- cm becomes the lineage authority. Queries about "why do we believe X" trace through cm's `derived_from` DAG.
- am's lineage is topological rather than explicit: neighborhoods that share ancestry will be geometrically close (because the Consolidator creates synthesis neighborhoods near the centroids of their source clusters).
- Adding `Synthesized` to `NeighborhoodType` is a one-variant enum extension in am-core. Minimal code change. The main impact is in `compose.rs` scoring, where Synthesized neighborhoods should receive a scoring bonus similar to Decision/Preference types.

## Component Interaction Summary

```
                     OWNER
                       |
                  [am_salient]
                  [CRITIC delegation]
                       |
                       v
              +--------+--------+
              |   am (conscious) |   <-- WRITE-ONLY for owner
              |   S3 manifold    |   <-- READ-ONLY for agents + Consolidator
              +---------+-------+
                        ^
                        | promote
                        |
              +---------+-------+
              | am (subconscious)|  <-- Observer writes value signals here
              |   S3 manifold    |  <-- Queries reshape through drift/coupling
              +--------+--------+
                       ^  |
              writes   |  | reads (query, export)
                       |  v
              +--------+--------+
              |    Observer      |  <-- Helix-level, LLM-powered
              |  (extraction +  |      Runs post-conversation
              |   classification)|
              +--------+--------+
                       |  ^
              facts    |  | reads existing entries for dedup
                       v  |
              +--------+--------+
              |       cm        |  <-- Facts, tensions, derivation DAG
              |  (context-      |
              |   matters)      |
              +--------+--------+
                       ^
                       | writes tensions, synthesis records
                       |
              +--------+--------+
              |  Consolidator   |  <-- Helix-level, scheduled
              |  (geometric     |      Runs during idle
              |   dreaming)     |
              +--------+--------+
                       |
              reads am state via export
```

## Implementation Sequence

### Phase 1: Observer (weeks 1-3)
1. Define the classification prompt for fact-vs-value separation.
2. Build the Observer as a Helix-level service that consumes conversation buffers.
3. Route facts to cm with `derivation_level: explicit, source: observer`.
4. Route value signals to am via `am_buffer` / `am_ingest`.
5. Wire into am's existing sync hook or as a separate post-conversation trigger.
6. Make the Observer opt-in per workspace configuration.

### Phase 2: Derivation Tracking in cm (week 4)
1. Add `derivation_level` and `derived_from` fields to cm's entry schema.
2. Migration for existing entries (default to `explicit`, empty `derived_from`).
3. Update cm's query and display to surface derivation chains.

### Phase 3: Consolidator (weeks 5-8)
1. Build cluster detection (geodesic distance between neighborhood seeds).
2. Build tension detection (near-antipodal high-activation pairs).
3. Build LLM synthesis for cluster distillation and tension description.
4. Add `Synthesized` variant to `NeighborhoodType` in am-core.
5. Wire into a scheduler (cron, or idle-detection via conversation gap analysis).
6. Build the consolidation fingerprint log to prevent reprocessing.

### Phase 4: Perspectival Memory (weeks 9-10)
1. Define the agent perspective data model in cm.
2. Record query centroids during am queries.
3. Compute and update agent perspective quaternions.
4. Add perspective bias to compose scoring.

### Phase 5: CRITIC Integration (weeks 11-12)
1. Define CRITIC's perspective quaternion from mission/evaluation criteria.
2. Build the promotion recommendation pipeline (Consolidator output -> CRITIC evaluation -> owner notification).
3. Define workspace-level policy for CRITIC delegation authority.

## Open Questions

1. **Observer model selection**: The Observer's classification quality determines the entire pipeline's value. Should it use the same model as Helix's write-path LLM, or a cheaper model (Gemini Flash, Haiku) for high-volume extraction? Honcho defaults to Gemini Flash Lite for its Deriver. The classification task (fact vs value) is simpler than Honcho's "extract atomic facts" task, so a smaller model may suffice.

2. **Consolidation frequency**: How often should the Consolidator run? Daily is a reasonable starting point. But "idle detection" is more aligned with Honcho's Dreamer pattern. What counts as idle in a multi-agent environment where different agents may be active at different times?

3. **Tension resolution workflow**: When the Consolidator surfaces a tension, how does the owner interact with it? A cm entry is queryable, but the owner needs a dedicated interface (CLI command, notification) to review and resolve tensions. This may require a new am_tensions or helix_tensions command.

4. **Perspective persistence across agent lifetimes**: Ephemeral agents die and new ones spin up. Should perspectives transfer? If Agent A was a "code quality specialist" and Agent B replaces it in the same role, should B inherit A's perspective? This ties into nancy's agent lifecycle management.

5. **Conscious promotion criteria**: Can the system suggest promotion thresholds? For example, "this synthesis neighborhood has been recalled 10+ times and boosted 5+ times from the subconscious; consider promoting to conscious." This would require tracking recall/feedback history per subconscious neighborhood, which am already partially does through activation counts.

6. **Consolidator access pattern**: Reading am's full state via `am_export` produces a JSON snapshot. For a system with 41K occurrences (current brain.db is 131MB), this export may be large. Direct SQLite read access (read-only connection to brain.db) would be more efficient. Does the Consolidator get direct store access, or does it go through the MCP API? Direct access couples it to am-store's schema. MCP access is cleaner but slower.

## What This Design Does Not Do

- **It does not make am an observation store.** am remains a geometric memory system. Observations flow through it as value signals that become geometric structure. The observations themselves (as text) live in cm.
- **It does not give agents write access to conscious memory.** The owner-write constraint is preserved. The Observer populates subconscious. Promotion requires owner action.
- **It does not replicate Honcho's Dialectic.** Honcho's query agent is a tool-calling LLM that searches observations. Helix already has `helix recall` which queries all adapters including am. Adding another query agent would be redundant.
- **It does not require embeddings.** Honcho's entire pipeline depends on text-embedding-3-small for dedup and search. am uses geometric position on S3, which is more expressive and does not require an embedding API call per observation.
