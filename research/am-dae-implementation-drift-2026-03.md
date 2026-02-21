---
title: "AM vs DAE v0.7.2 — Implementation Drift Audit (March 2026)"
type: research
tags:
  [attention-matters, dae, drift-audit, implementation-fidelity, s3-manifold]
summary: "Systematic comparison of attention-matters Rust implementation against original DAE v0.7.2 JS, focused on behavioral drift in recall/scoring/filtering"
status: active
project: am
confidence: high
related:
  [
    am-rust-implementation-fidelity,
    dae-core-mathematical-foundations,
    dae-design-intent-and-invariants,
    am-conscious-recall-bug-analysis,
  ]
created: 2026-03-04
updated: 2026-03-04
---

# AM vs DAE v0.7.2 — Implementation Drift Audit

Previous audit (`am-rust-implementation-fidelity`) covered function-by-function port accuracy of the math engine. This audit focuses on **behavioral drift** — places where AM's recall/scoring/composition pipeline diverges from the original DAE's intended behavior.

---

## Drift Summary

| Aspect                             | DAE v0.7.2 (JS)                                                      | AM (Rust)                                 | Drift?  | Severity        |
| ---------------------------------- | -------------------------------------------------------------------- | ----------------------------------------- | ------- | --------------- |
| Conscious activation threshold     | None (any word)                                                      | None (any word)                           | No      | —               |
| Base scoring formula               | `sum(IDF * activationCount)`                                         | Same + density bonus + recency decay      | **Yes** | Medium          |
| Type-based score multipliers       | None                                                                 | Decision/Preference: 3x, floor 15.0       | **Yes** | **Critical**    |
| Contradiction handling             | Implicit via phasor interference                                     | Epoch-based Jaccard overlap penalty       | **Yes** | **Significant** |
| Diminishing returns on recall      | None                                                                 | Session-based `1/(1+count)`, D/P exempt   | **Yes** | Low             |
| Interference in composition        | Used (constructive = surface)                                        | **Computed but unused** (`_interference`) | **Yes** | **Critical**    |
| Surface vividness in composition   | Used (threshold gating)                                              | **Computed but unused** (`_surface`)      | **Yes** | **Significant** |
| Novel connection criteria          | 1-2 words, no conscious overlap, `maxWeight * maxPlasticity / count` | Same formula                              | No      | —               |
| Fixed output slots                 | 1 conscious, 2 subconscious, 1 novel                                 | Same                                      | No      | —               |
| Response activation                | Full pipeline (activate + drift + Kuramoto)                          | `am_activate_response` exists             | Verify  | —               |
| Stop-word handling                 | None (IDF handles suppression)                                       | None                                      | No      | —               |
| Mass normalization (M=1)           | Enforced: `mass = count/N * M`                                       | Present in `neighborhood.rs:107`          | No      | —               |
| Episode auto-creation              | Every 5 exchanges                                                    | Every 3 buffered exchanges                | Minor   | Low             |
| Quaternion geometry (SLERP, drift) | Verified identical                                                   | Verified identical                        | No      | —               |
| Kuramoto coupling                  | Verified identical                                                   | Verified identical                        | No      | —               |

---

## Critical Drifts

### 1. Type-Based Score Multipliers (NOT in original DAE)

**DAE v0.7.2**: All neighborhoods scored identically: `sum(IDF * activationCount)`. No concept of neighborhood "types" (Decision, Preference, Insight, Memory). Differentiation was structural (conscious vs subconscious episodes, separate output slots) not numeric.

**AM**: Introduces `NeighborhoodType` enum and applies `DECISION_MULTIPLIER = 3.0` with `DECISION_FLOOR = 15.0` to Decision and Preference types. Also exempts them from session diminishing returns.

**Impact**: This is the direct cause of the "same memory on every query" bug. The floor guarantee overrides IDF-based relevance signal. The exemption from diminishing returns means the problem never self-corrects within a session.

**Assessment**: This extension breaks the original model's philosophy of "pure geometry — all behavior emerges from manifold properties." Score multipliers are a bag-of-words heuristic bolted on top of a geometric system. The original DAE's approach: if something is important, mark it salient (conscious episode) — the structural separation handles the rest.

### 2. Interference Computed but Unused

**DAE v0.7.2**: Phasor interference between conscious and subconscious manifolds is the **primary gate** for cross-manifold recall. Only subconscious occurrences with positive interference (`cos(delta_theta) > 0`, i.e., phases aligned with conscious mean phase) are candidates for surfacing.

**AM**: The interference computation exists in `query.rs:306-370`. `compute_interference` correctly calculates per-word interference values between manifolds. But `compose_context` (compose.rs:268) receives `_interference` as an unused parameter. The composition pipeline relies entirely on IDF-weighted activation scores — the geometric gate is disconnected.

**Impact**: The entire phasor-based relevance filtering system exists but does nothing. This means the manifold evolves (Kuramoto coupling synchronizes phases, drift moves positions) but the output selection ignores all of it. The system is doing expensive geometric computation whose results are thrown away.

**Assessment**: This is likely the most significant drift. The interference mechanism IS the DAE's answer to relevance gating. Without it, the system degrades to a bag-of-words retrieval engine with geometric overhead.

### 3. Epoch-Based Jaccard Overlap (NOT in original DAE)

**DAE v0.7.2**: No explicit contradiction handling. Contradictions are handled implicitly through phasor interference — contradictory content sharing the same words develops opposed phases through Kuramoto coupling, producing destructive interference that suppresses co-activation.

**AM**: Introduces `overlap_suppress` (compose.rs:1076-1130) using IDF-weighted Jaccard coefficient with `OVERLAP_THRESHOLD = 0.3`. When two neighborhoods have > 30% IDF-weighted word overlap, the older one (lower epoch) gets score multiplied by `OVERLAP_SUPPRESSION = 0.1`.

**Impact**: Works as intended for explicit contradictions. But it's a heuristic layered on top of a system designed to handle this geometrically. If interference were wired in, Jaccard overlap would be redundant for most cases.

**Assessment**: Reasonable pragmatic extension, but architecturally foreign. With interference restored, this could be kept as a safety net for edge cases where Kuramoto coupling hasn't had enough queries to develop opposed phases.

### 4. Surface/Vividness Computed but Unused

**DAE v0.7.2**: Surface analysis (`composeContext`) uses vivid neighborhoods — requiring `activatedCount / totalCount > THRESHOLD (0.5)` and `mass > THRESHOLD`. This filters out neighborhoods where only a small fraction of words were activated.

**AM**: `SurfaceResult` is computed in `surface.rs` but `_surface` is unused in the composition pipeline. Comment says "reserved for future use."

**Impact**: Without vividness filtering, neighborhoods activated by a single word in a 50-word neighborhood can still surface. The original DAE would require at least 50% of words to be activated.

---

## Drifts That Are Reasonable Extensions

### Density Bonus (compose.rs)

```
density_bonus = activated_count / query_token_count
score *= (1 + density_bonus)
```

Not in original DAE. But directionally correct — neighborhoods matching more query tokens should score higher. This is compatible with the geometric philosophy as a scoring refinement.

### Recency Decay (compose.rs)

```
decay = 1.0 / (1.0 + days_old * 0.01)
```

Not in original DAE (which had no notion of real-world time). Reasonable extension for a persistent system where memories can be months old. Previous audit (`am-recall-layer-issues`) noted the decay rate is too weak — a 365-day-old memory still retains 27% of score.

### Session Diminishing Returns (compose.rs)

```
score *= 1.0 / (1.0 + recall_count)  // for non-Decision/Preference types
```

Not in original DAE. Reasonable for session UX — prevents the same subconscious memory from dominating an entire session. The Decision/Preference exemption is the problematic part.

### Budgeted Composition (compose.rs:403)

Not in original DAE (which had fixed 1+2+1 slots). Useful for Nancy prompt compiler integration where token budgets matter. Extends rather than contradicts the original model.

---

## Recommendations

### Priority 1: Wire in interference

Connect `compute_interference` output to `compose_context` scoring. Only conscious memories with positive aggregate interference should surface. This restores the original DAE's primary relevance gate and is the most principled fix.

### Priority 2: Remove DECISION_FLOOR

Let IDF weighting do its job. If a Preference matches only by common words, it should score low. The 3x multiplier can stay (it's a reasonable "importance" signal), but the floor of 15.0 creates a relevance bypass.

### Priority 3: Wire in vividness

Use `SurfaceResult.vivid_neighborhoods` to filter candidates before scoring. This restores the "must activate a meaningful fraction of the neighborhood" gate from the original DAE.

### Priority 4: Evaluate Jaccard overlap with interference active

Once interference is wired in, test whether Jaccard overlap suppression is still needed. If Kuramoto coupling + interference handles contradictions geometrically, the explicit heuristic may be redundant. Keep it as a safety net initially.
