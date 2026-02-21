---
title: "AM Contradiction Handling — Design Options"
type: design
tags:
  [
    am,
    attention-matters,
    contradiction,
    epoch,
    overlap,
    supersession,
    composition,
  ]
summary: "Three design options for structural contradiction handling in AM, with trade-off analysis"
status: draft
created: 2026-03-03
updated: 2026-03-03
project: am
confidence: medium
related:
  [
    am-contradiction-gap-analysis,
    dae-design-intent-and-invariants,
    dae-core-mathematical-foundations,
  ]
---

# AM Contradiction Handling — Design Options

## Context

AM models association, not truth. Contradictory memories coexist with equal standing. See [gap analysis](am-contradiction-gap-analysis.md) for the full audit.

## Design Constraint

Attention-matters is the initial public offering of the DAE engine. Changes must be mathematically sound, backwards-compatible with wire format v0.7.2, and preserve the core invariants documented in [DAE Design Intent](../research/dae-design-intent-and-invariants.md).

## Rejected Approaches

**Antipodal placement** — Push contradicted memories to the geometric opposite of the manifold. Rejected: tangles on reversal (if you change your mind back, the geometry becomes inconsistent).

**Phase-shift marking** — Use phasor phase to mark superseded content. Useful only as supplement. Phase already encodes temporal ordering via golden-angle spacing; overloading it conflates two signals.

**Aggressive recency decay** — Increase RECENCY_DECAY_RATE to make old memories fade faster. Rejected: penalises all old memories equally, including good ones. Indiscriminate.

## Option A: Epoch + Overlap Detection at Composition Time

Two additions:

### 1. Monotonic Epoch Counter

Add `epoch: u64` to Neighborhood. Add `next_epoch: u64` to DAESystem (starting at 1). Each new neighborhood gets the current epoch and increments the counter.

```rust
// neighborhood.rs
pub struct Neighborhood {
    pub id: Uuid,
    pub seed: Quaternion,
    pub occurrences: Vec<Occurrence>,
    pub source_text: String,
    pub neighborhood_type: NeighborhoodType,
    pub epoch: u64,  // NEW — monotonic creation order
}
```

Wire format: add `epoch` to `WireNeighborhood` with `#[serde(default)]`. Old files deserialize with epoch 0.

### 2. IDF-Weighted Overlap Detection

During composition, after scoring and ranking the top-N candidates:

1. Compute pairwise IDF-weighted word overlap between top candidates
2. Group candidates with overlap > threshold into "topic clusters"
3. Within each cluster, suppress all but highest-epoch to 0.1x score
4. Re-rank

IDF-weighting means rare word matches count more than common ones. Two neighborhoods sharing "the", "is", "a" won't cluster. Two sharing "epoch", "contradiction", "neighborhood" will.

```
overlap(A, B) = Σ IDF(w) for w in (words_A ∩ words_B)
             / Σ IDF(w) for w in (words_A ∪ words_B)
```

Threshold TBD. Starting point: 0.3 (IDF-weighted overlap is lower than raw Jaccard because common words contribute less).

### Trade-offs

| +                                                      | -                                                                                     |
| ------------------------------------------------------ | ------------------------------------------------------------------------------------- |
| Structural — no LLM cooperation needed                 | Token-level overlap isn't semantic similarity                                         |
| Reverse-a-reverse works naturally (highest epoch wins) | May suppress related-but-compatible memories                                          |
| Uses existing IDF infrastructure                       | Threshold tuning affects false positives/negatives                                    |
| Only runs on top-N candidates, not full manifold       | Adds O(k²) pairwise comparison on top candidates                                      |
| Non-breaking schema change                             | Epoch 0 default means pre-existing neighborhoods are unordered relative to each other |

### Scope

- `neighborhood.rs`: Add epoch field
- `system.rs`: Add next_epoch counter, assign on neighborhood creation
- `compose.rs`: Add overlap detection after scoring, before final ranking
- `serde_compat.rs`: Add epoch to wire format with default

Estimated: ~8 hours for core implementation + tests.

## Option B: Geometric Drift Convergence

Instead of token overlap, use the manifold's own dynamics. When a query activates two neighborhoods about the same topic, drift pulls their occurrences toward each other. Track cumulative drift convergence between neighborhoods over multiple queries.

### Mechanism

Add `drift_affinity: HashMap<Uuid, f64>` to Neighborhood. During drift, when occurrences from two neighborhoods converge, increment their mutual affinity. During composition, high-affinity neighborhoods are treated as a topic cluster (same suppression logic as Option A).

### Trade-offs

| +                                                       | -                                                                                         |
| ------------------------------------------------------- | ----------------------------------------------------------------------------------------- |
| Uses native geometry — this is what the manifold is for | Cold-start: new contradictions haven't had queries to reveal their relationship           |
| Emerges from actual usage patterns                      | Requires new tracking infrastructure (drift history)                                      |
| More semantically meaningful over time                  | HashMap per neighborhood is memory-heavy at scale                                         |
| No threshold tuning for overlap detection               | Affinity grows for related AND contradictory content equally — need epoch to disambiguate |

### Verdict

Elegant but requires Option A's epoch anyway to distinguish which member of a converging pair is current. Better as a v2 evolution layered on top of A.

## Option C: Explicit Supersession

Add `superseded_by: Option<Uuid>` to Neighborhood. When content contradicts an existing memory, the caller provides the ID of what it supersedes. During composition, superseded neighborhoods are excluded entirely.

### Mechanism

Extend `am_salient` to accept an optional `supersedes: Vec<Uuid>` parameter. The `recalled_ids` in query responses provide the IDs needed to reference what's being superseded.

```rust
// neighborhood.rs
pub struct Neighborhood {
    // ... existing fields ...
    pub superseded_by: Option<Uuid>,  // NEW — explicit contradiction link
}
```

### Trade-offs

| +                                      | -                                                                   |
| -------------------------------------- | ------------------------------------------------------------------- |
| Precise — no false positives           | Depends on LLM detecting contradictions (same weakness as feedback) |
| Clean semantics ("this replaces that") | Requires recalled_ids to be surfaced (already shipped)              |
| Simple implementation                  | Doesn't handle cases where LLM misses a contradiction               |
| No threshold tuning                    | One-directional — can't easily un-supersede                         |

### Scope

- `neighborhood.rs`: Add superseded_by field
- `compose.rs`: Filter out superseded neighborhoods before scoring
- `serde_compat.rs`: Add to wire format with default None
- MCP tools: Extend am_salient to accept supersedes parameter

Estimated: ~4 hours.

## Recommended Approach: A + C

They solve different failure modes:

- **C** handles the explicit case — the LLM knows it's contradicting something and says so. Clean, precise, zero false positives.
- **A** handles the implicit case — the LLM didn't notice the contradiction, but the system catches it structurally at composition time.

Together they provide defence in depth. Neither alone is sufficient.

**B** is the most mathematically elegant but is a bigger bet, requires A anyway, and has the cold-start problem. Candidate for v2.

## Open Questions

1. What IDF-weighted overlap threshold for Option A? Needs empirical tuning against real AM data.
2. Should epoch 0 (pre-existing neighborhoods) be treated specially? E.g., all epoch-0 neighborhoods are considered same-epoch and never suppress each other.
3. Should superseded neighborhoods be excluded entirely or just heavily penalized (0.01x)?
4. Wire format version bump to 0.8.0 or keep 0.7.2 with additive fields?

## Status

**Draft** — awaiting Stuart's review and decision before implementation.
