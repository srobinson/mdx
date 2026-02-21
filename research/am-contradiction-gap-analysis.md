---
title: "AM Contradiction Handling — Gap Analysis"
type: research
tags:
  [am, attention-matters, contradiction, epoch, jaccard, scoring, composition]
summary: "Audit of AM's contradiction handling: what was decided, what shipped, what didn't, and how scoring actually works today"
status: active
created: 2026-03-03
updated: 2026-03-03
project: am
confidence: high
related:
  [
    dae-synthesis,
    dae-core-mathematical-foundations,
    dae-design-intent-and-invariants,
    am-contradiction-handling-design,
  ]
---

# AM Contradiction Handling — Gap Analysis

Audited 2026-03-03 against attention-matters codebase at `~/Dev/LLM/DEV/helioy/attention-matters/`.

## The Problem

AM's geometry models **association**, not **truth**. When contradictory memories exist ("use approach A" then later "don't use A, use B"), both get recalled. The system has no structural mechanism to prefer the current one.

## What Was Decided (But Never Implemented)

A conscious recall from AM itself surfaces this decision:

> [DECIDED] AM contradiction handling strategy — epoch-based Jaccard overlap penalty. Add monotonic epoch counter to DAESystem and Neighborhood. During composition, group candidate neighborhoods by Jaccard token similarity (>0.6), suppress all but highest-epoch in each group (0.1x score). Handles reverse-a-reverse naturally. Optional superseded_by field for explicit LLM-driven correction. Antipodal placement rejected (tangles on reversal). Phase-shift marking useful only as supplement. ~8 hours minimum viable implementation.

**None of this shipped.** Verified by codebase grep — zero hits for "epoch", "jaccard", "superseded" in the Rust source.

## What Actually Exists Today

### Scoring Pipeline (compose.rs)

The current scoring formula for each neighborhood:

```
score = Σ(IDF(word) × activation_count)  for each activated occurrence
```

Where IDF = `1.0 / number_of_neighborhoods_containing_word`.

### Post-Processing by Type

| Neighborhood Type | Treatment                            |
| ----------------- | ------------------------------------ |
| Decision          | Flat score = 100.0 (always surfaces) |
| Preference        | Flat score = 100.0 (always surfaces) |
| Insight           | Normal scoring with recency decay    |
| Memory            | Normal scoring with recency decay    |

### Recency Decay

Applied to non-Decision/Preference neighborhoods:

```
decay = 1.0 / (1.0 + days_since_episode × 0.01)
```

- 7 days old: 0.93x
- 30 days old: 0.77x
- 90 days old: 0.53x
- 365 days old: 0.21x

**Key detail:** Timestamps live on **Episodes**, not Neighborhoods. All neighborhoods in an episode share the same timestamp. This provides episode-level granularity only.

### Conscious Recency Boost

Conscious neighborhoods get position-based boost:

```
recency_boost = 1.0 + (index / count)
```

Newest conscious neighborhood gets ~2.0x, oldest gets 1.0x.

### Feedback (Boost/Demote)

- **Boost:** SLERP occurrences toward query centroid, increase activation_count by 1. Drift factor: `0.15 × IDF × plasticity`.
- **Demote:** Decrease activation_count by 2, floor at 0. Makes occurrences drift away in future queries.

The CORRECT protocol (demote old + salient new) is documented in the memory skill but depends entirely on the LLM detecting contradictions and calling am_feedback. Not structural.

### Composition Output

Default (non-budgeted): top 1 conscious + top 2 subconscious + top 1 novel.
Budgeted: fills guaranteed minimums then greedily fills by score within token budget.

Session dedup prevents the same non-Decision neighborhood from appearing twice in a session.

## What Doesn't Exist

1. **No epoch counter** on Neighborhood or DAESystem
2. **No Jaccard similarity** calculation anywhere
3. **No overlap detection** between candidate neighborhoods
4. **No superseded_by field** or explicit contradiction links
5. **No mechanism** to distinguish "two memories about the same topic" from "two unrelated memories"

## Consequence

Both sides of a contradiction surface with equal standing. If both are Decision type, both get flat 100.0. The only mitigation is manual feedback (demote old), which is unreliable.

## Wire Format Considerations

Current version: **0.7.2**. Wire format uses `#[serde(default)]` extensively. Adding new fields to `WireNeighborhood` is non-breaking — old files deserialize with defaults, new files include the field. No migration needed for additive changes.

## Related Codebase Locations

- Scoring: `am-core/src/compose.rs` lines 668-784
- Neighborhood struct: `am-core/src/neighborhood.rs` lines 48-56
- DAESystem struct: `am-core/src/system.rs` lines 52-67
- Episode struct: `am-core/src/episode.rs` lines 11-17
- Wire format: `am-core/src/serde_compat.rs` (CURRENT_VERSION = "0.7.2")
- Feedback: `am-core/src/feedback.rs` lines 107-238
- Recency: `am-core/src/compose.rs` lines 618-666
