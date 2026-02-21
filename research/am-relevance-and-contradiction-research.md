---
title: "AM Relevance & Contradiction — External Research"
type: research
tags:
  [
    am,
    attention-matters,
    relevance,
    contradiction,
    scoring,
    neuroscience,
    competitors,
  ]
summary: "External validation of AM's contradiction and relevance problems — competitor patterns, academic literature, neuroscience analogies"
status: active
created: 2026-03-03
updated: 2026-03-03
project: am
confidence: high
related:
  [
    am-contradiction-gap-analysis,
    am-contradiction-handling-design,
    dae-design-intent-and-invariants,
  ]
---

# AM Relevance & Contradiction — External Research

## Competitor Analysis

### Zep/Graphiti — Temporal Knowledge Graph with Edge Invalidation

Most directly relevant system. Paper: https://arxiv.org/html/2501.13956v1

- **Bi-temporal modeling**: Every edge (fact) carries four timestamps — t_created, t_expired (system time), t_valid, t_invalid (world time). Separates "when the system learned it" from "when it was true."
- **Contradiction detection**: Uses semantic search, keyword search, and graph traversal to find existing edges that might conflict. LLM compares new edges against candidates.
- **Edge invalidation, not deletion**: Old edge's t_invalid is set to t_valid of new edge. Preserved for audit/reasoning but no longer surfaces as current truth.
- **Key insight**: Don't delete contradicted memories, mark them as superseded.

Maps to our epoch + overlap approach. The overlap detection is their candidate finding. The epoch is their system time. The superseded_by field is their edge invalidation.

### MemGPT/Letta — Agent-Managed Memory

Paper: https://arxiv.org/abs/2310.08560

Agent itself manages memory via tool calls. Less applicable because DAE operates below the LLM layer. But validates the two-tier memory concept (archival + recall) analogous to different activation thresholds.

### MemOS — Memory Operating System

Paper: https://arxiv.org/abs/2507.03724

Task-aligned routing: decomposes queries into topic-concept-fact hierarchy before retrieval. Relevant for decision relevance — queries could be classified ("what did we decide about X?" vs "what do you know about X?") and routed to different memory types.

## Academic Literature

### Adaptive Hopfield Networks (A-Hop, November 2025)

Paper: https://arxiv.org/abs/2511.20609

Core argument: Fixed similarity measures (like IDF × activation_count) cannot guarantee that the retrieved pattern has the strongest association with the query. Develops "adaptive similarity" — a mechanism that learns to approximate the likelihood of each stored pattern generating the query.

**DAE relevance**: Within S³, query-memory affinity could be modeled not as static token overlap, but as the probability that the query originated from a given memory's semantic neighborhood. In practice: the weight of a shared token should depend on how many other query tokens also appear in that memory (co-occurrence density).

### Predictive Associative Memory (PAM, February 2026)

Paper: https://arxiv.org/abs/2602.11322

Biological memory associates through temporal co-occurrence, not similarity. PAM achieves cross-boundary recall where cosine similarity scores zero. Validates enhancement to DAE's activation model: memories ingested/activated in the same session should get co-activation boost beyond token overlap.

### Curved Neural Networks (Nature Communications, 2025)

Coverage: https://techxplore.com/news/2025-07/neural-networks-enable-ai-memory.html

Geometric curvature in processing space creates "explosive memory recall." A single curvature parameter balances memory power and accuracy. Validates DAE's S³ approach. Suggests query-dependent curvature modulation could sharpen/broaden recall basins.

## Neuroscience Analogies

### Retrieval-Induced Forgetting (RIF)

Paper: https://pmc.ncbi.nlm.nih.gov/articles/PMC4394359/

When the brain retrieves a specific memory, it actively suppresses competing memories sharing the same category cue. Suppression is temporary, not permanent. Maps directly to overlap-based suppression during composition — highest-scoring memories should inhibit lower-scoring ones with overlapping tokens.

### Memory Reconsolidation

Paper: https://pmc.ncbi.nlm.nih.gov/articles/PMC4588064/

Retrieved memories become temporarily labile (susceptible to modification). In a contradicting context, the old memory can be updated or weakened. Validates: retrieval in the presence of contradiction should weaken the old memory's score.

### Event Boundaries and Memory Segmentation

Sessions/epochs function as event boundaries. Recall across event boundaries is naturally lower. Memories from different events should have attenuated cross-activation. The epoch boundary itself should act as an attenuation factor.

### Temporal Context Model (TCM)

Paper: https://pmc.ncbi.nlm.nih.gov/articles/PMC3432313/

Items encoded close in time share similar temporal context and are more likely to be co-retrieved. Rather than treating activation_count as flat, recent activations should contribute more.

## Key Insights for AM

### For Contradiction Handling

1. **Mark, don't delete** (Zep) — superseded_by field, not removal
2. **Epoch-based inhibition** (RIF) — newer overlapping memory suppresses older one per-query
3. **Retrieval-triggered weakening** (reconsolidation) — retrieval in contradicting context should weaken old memory

### For Relevance

1. **Co-occurrence density** (A-Hop) — weight tokens by how many other query tokens co-occur in the same memory
2. **Query-type routing** (MemOS) — decision queries vs knowledge queries activate different memory types
3. **Competitive scoring** — replace flat Decision 100.0 with multiplied score + floor
4. **Event boundary attenuation** — cross-epoch activation penalised
