---
title: "AM Recall Quality — Implementation Plan"
type: design
tags:
  [
    am,
    attention-matters,
    contradiction,
    relevance,
    scoring,
    composition,
    epoch,
    supersession,
  ]
summary: "Three-phase plan to fix AM's contradiction gap and relevance problem — epoch + overlap detection, decision relevance scoring, scoring refinements"
status: active
created: 2026-03-03
updated: 2026-03-03
project: am
confidence: high
related:
  [
    am-contradiction-gap-analysis,
    am-contradiction-handling-design,
    am-relevance-and-contradiction-research,
  ]
---

# AM Recall Quality — Implementation Plan

## Context

Attention-matters has two structural problems that must be solved before it's a credible public offering:

1. **Contradiction gap** — When newer information contradicts older information, both surface equally. The system has no way to prefer the current one. Demoting doesn't work on Decision-type memories (flat 100.0 overrides activation count). Demoted memories can be revived by any future query.

2. **Relevance problem** — Decision memories surface on every query because they get flat 100.0 regardless of query relevance. Token-level activation means shared domain vocabulary pulls irrelevant memories. Signal-to-noise degrades as the manifold grows.

These are engineering gaps, not vision gaps. The core thesis (memory as emergence on a living geometry) is sound and differentiated. Validated by external research: Zep/Graphiti (bi-temporal invalidation), Adaptive Hopfield Networks (context-dependent similarity), neuroscience (RIF, reconsolidation). Full research at `am-relevance-and-contradiction-research.md`.

## Phase 1: Structural Contradiction Handling (~10 hours)

### 1a. Epoch counter

- Add `epoch: u64` to `Neighborhood` struct
- Add `next_epoch: u64` to `DAESystem`, increment on every neighborhood creation
- Wire format: `#[serde(default)]` on `WireNeighborhood`
- SQLite: `epoch INTEGER DEFAULT 0` on neighborhoods table
- Files: `neighborhood.rs`, `system.rs`, `serde_compat.rs`, `schema.rs`, `store.rs`

### 1b. Superseded_by field

- Add `superseded_by: Option<Uuid>` to `Neighborhood`
- Wire format + SQLite: nullable, default None/NULL
- Composition: hard-exclude superseded neighborhoods before scoring
- Files: `neighborhood.rs`, `serde_compat.rs`, `schema.rs`, `store.rs`, `compose.rs`

### 1c. Overlap detection at composition time

- After scoring top-N candidates, compute pairwise IDF-weighted word overlap
- Overlap formula: `Σ IDF(w) for intersection / Σ IDF(w) for union`
- Group candidates with overlap > 0.3 threshold
- Within each group, suppress all but highest-epoch to 0.1x score
- Re-rank. Only runs on top candidates — bounded cost.
- Files: `compose.rs`

### 1d. Wire supersession into am_salient

- Extend `SalientRequest` with optional `supersedes: Vec<String>`
- Mark referenced neighborhoods with `superseded_by = new_id`
- Files: `server.rs`

### 1e. Tests

- Epoch assignment, overlap computation, supersession filtering
- Integration: contradicting memories → only newest surfaces
- Integration: supersede a Decision → no longer surfaces
- Wire format round-trip with new fields

## Phase 2: Decision Relevance (~4 hours)

### 2a. Competitive scoring with floor

Replace flat 100.0:

```
Decision score = max(normal_score × DECISION_MULTIPLIER, DECISION_FLOOR)
```

- DECISION_MULTIPLIER: 3.0 (genuinely matching Decisions score 3x)
- DECISION_FLOOR: 15.0 (minimum visibility, doesn't dominate unrelated queries)
- Same treatment for Preference type
- Files: `compose.rs`, `constants.rs`

### 2b. Tests

- Decision with high query overlap scores > floor
- Decision with no query overlap scores = floor
- Acceptance test: "social media voice" query does NOT return AM architecture Decision as top result

## Phase 3: Scoring Refinements (~6 hours)

### 3a. Co-occurrence density bonus

```
density_bonus = activated_count / total_query_tokens
score *= (1.0 + density_bonus)
```

Rewards memories matching the query's gestalt, not just its vocabulary.

### 3b. Softer session dedup

Replace hard exclusion with diminishing returns:

```
recall_penalty = 1.0 / (1.0 + times_recalled)
```

Change `session_recalled` from `HashSet<Uuid>` to `HashMap<Uuid, u32>`.

### 3c. Flexible top-N

Add minimum score threshold. Stop padding context with weak matches.

## Sequencing

Phase 1 → Phase 2 → Phase 3. Each independently shippable and testable.

## Wire Format

All additive. `#[serde(default)]` on new fields. Old files deserialize cleanly. Non-breaking.
