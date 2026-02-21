---
title: "Relevance-Gated Recall on Geometric Manifolds — Literature Review"
type: research
tags:
  [
    attention-matters,
    relevance-gating,
    hopfield-networks,
    sdm,
    bm25,
    act-r,
    hubness,
    geometric-memory,
  ]
summary: "Survey of mathematical approaches to relevance-gated memory recall, applied to AM's S3 hypersphere manifold"
status: active
project: am
confidence: high
related:
  [
    am-conscious-recall-bug-analysis,
    am-dae-implementation-drift-2026-03,
    dae-core-mathematical-foundations,
  ]
created: 2026-03-04
updated: 2026-03-04
---

# Relevance-Gated Recall on Geometric Manifolds — Literature Review

Survey of approaches to the "everything activates" problem in associative memory systems, with application to AM's S3 hypersphere manifold.

---

## 1. Modern Hopfield Networks — Temperature as Selectivity

**Source**: Ramsauer et al. 2020, "Hopfield Networks is All You Need" (https://ar5iv.labs.arxiv.org/html/2008.02217)

Energy function: `E = -lse(beta, X^T xi) + (1/2) xi^T xi + beta^{-1} log N + (1/2) M^2`

Update rule (equivalent to transformer attention): `xi_new = X * softmax(beta * X^T xi)`

The inverse temperature **beta** controls selectivity:

- **High beta**: Single-pattern fixed points (clean recall of individual memories)
- **Low beta**: Metastable states (averages over subsets)
- **Very low beta**: Global fixed point averaging ALL patterns — the "everything activates" failure mode

Storage capacity with exponential separation: `C ~ 2^{d/2}` — exponential in dimension.

**AM application**: AM currently operates in the "very low beta" regime — any overlap activates. Introducing a temperature parameter on the scoring function would create winner-take-all dynamics where the strongest match suppresses weaker ones.

## 2. Kernelized Hopfield on Spheres — The Separation Parameter

**Source**: Hu et al. NeurIPS 2024, "Provably Optimal Memory Capacity for Modern Hopfield Models" (https://arxiv.org/abs/2410.23126)

Key insight: optimal memory capacity on a hypersphere requires memories to form an **optimal spherical code** — maximizing the minimum angular distance between any two patterns.

The separation parameter Delta: `Delta_mu = K(xi_mu, xi_mu) - max_{nu != mu} K(xi_nu, xi_mu)`

Retrieval error decreases **exponentially** with Delta. This gives a theoretical bound on how many memories can be stored at a given separation level.

**AM application**: The geodesic distance on S3 between a query point and each memory IS a natural relevance gate. Rather than activating on word overlap, compute angular distance from query centroid to memory seed. Only memories within a separation threshold activate.

## 3. Curved Neural Networks — Explosive Phase Transitions

**Source**: Muolo et al. Nature Communications 2025 (https://www.nature.com/articles/s41467-025-61475-w)

State-dependent temperature: `beta'(x) = beta / [1 - gamma * beta * E(x)]`

With negative gamma, approaching a memory pattern **increases** the effective inverse temperature — making the attractor sharper and the transition explosive (discontinuous). Creates:

- Self-regulating annealing — system sharpens focus as it nears a memory
- Hysteresis — recalled memory resists displacement
- Winner-take-all without external scheduling

**AM application**: The gamma parameter could control how aggressively the manifold funnels toward the nearest relevant memory. Below a critical distance: explosive recall. Above it: nothing happens. This is a geometric ignition threshold.

## 4. Kanerva's Sparse Distributed Memory — Hard Activation Radius

**Source**: Kanerva, Sparse Distributed Memory (https://grokipedia.com/page/Sparse_distributed_memory)

Core mechanism: `y_m = 1 if d(x, h_m) <= H, else 0`

The **1/1000 rule**: activation radius H is set to activate ~1/1000th of all locations. For 10,000 stored items, activate ~10.

Critical distance for convergent retrieval: queries closer than this converge; farther ones fail. Signal reinforces (`k` nearby memories), noise cancels (`1/sqrt(k)`).

**AM application**: Implement a hard activation radius on S3. Memories beyond a geodesic threshold simply do not participate. The 1/1000 ratio is a validated starting point.

## 5. BM25 — Three-Mechanism Relevance Control

**Source**: BM25 (https://en.wikipedia.org/wiki/Okapi_BM25)

```
score(D,Q) = SUM_i IDF(q_i) * [f(q_i,D) * (k1+1)] / [f(q_i,D) + k1 * (1 - b + b * |D|/avgdl)]
```

Three mechanisms AM is missing:

1. **IDF weighting** — AM has this, but the DECISION_FLOOR bypasses it
2. **Term frequency saturation** (k1 = 1.2-2.0) — after ~3 occurrences of a term, diminishing returns. AM's `activation_count` grows without bound
3. **Length normalization** (b = 0.75) — penalizes longer documents. AM has no equivalent — a 200-word conscious memory containing many common words has more activation surface than a 20-word one

**AM application**: Add TF saturation to prevent `activation_count` from growing linearly with queries. Add length normalization so verbose memories don't dominate.

## 6. ACT-R — Activation Equation with Fan Effect

**Source**: Anderson, ACT-R cognitive architecture (http://act-r.psy.cmu.edu/wordpress/wp-content/themes/ACT-R/tutorials/unit4.htm)

Total activation: `A_i = B_i + SUM_j(W_j * S_ji) + PM + noise`

**Base-level activation** (power-law decay): `B_i = ln(SUM_j(t_j^{-d}))` where d ~ 0.5

**Fan effect** (anti-hubness): `S_ji = S_max - ln(fan_j)` — if a word connects to 100 memories, each connection is weakened by ln(100) ~ 4.6. A word connecting to 2 memories has strength S_max - 0.7.

**Retrieval threshold (tau)**: `if max(A_i) < tau: retrieval FAILS (returns nothing)`. Default tau = -2.0.

**Retrieval probability**: `P(recall_i) = 1 / (1 + exp(-(A_i - tau) / s))` — sigmoid gating centered at threshold.

**Spreading activation budget**: Total W divided among context elements. More context words → each word has less individual power → prevents single-word matches from overwhelming multi-word relevance.

**AM application**: The fan effect is directly applicable. AM's IDF weight (`1 / neighborhood_count`) IS a fan effect, but the DECISION_FLOOR overrides it. The retrieval threshold concept is critical — when nothing is relevant enough, return nothing. The spreading activation budget would prevent single common words from activating memories.

## 7. The Hubness Problem

**Source**: Radovanovic et al. JMLR 2010 (https://www.jmlr.org/papers/volume11/radovanovic10a/radovanovic10a.pdf); Hubness reduction comparison PMC 2020 (https://pmc.ncbi.nlm.nih.gov/articles/PMC7327987/)

**Problem**: In high-dimensional spaces, certain points naturally become nearest neighbors of disproportionately many other points (hubs). This is intrinsic to the geometry.

**Best correction methods**:

- **Mutual Proximity**: `MP(d_x,y) = P(d(x,*) > d(x,y)) * P(d(y,*) > d(y,x))` — two points are "close" only if mutually among each other's nearest neighbors
- **Local Scaling**: `LS(d_x,y) = 1 - exp(-d^2 / (sigma_x * sigma_y))` — normalize by local density
- **NICDM**: `NICDM(d_x,y) = d_x,y / (mu_x * mu_y)` — normalize by mean k-NN distance

Key finding: scaling methods consistently outperform centering methods. k = 5-10 for neighborhood size.

**AM application**: Hub memories (high connectivity, many shared words) should have their proximity inflated. Local scaling on geodesic distances would naturally suppress memories that are "close to everything."

## 8. Global Workspace Theory — Ignition Threshold

**Source**: Baars, Global Workspace Theory (https://pmc.ncbi.nlm.nih.gov/articles/PMC8770991/)

- Unconscious processors operate in parallel, each computing local activations
- Information **competes** for access to the global workspace (consciousness)
- **Ignition threshold**: minimum activity required before information enters consciousness
- When ignition occurs: sudden, coherent, exclusive — winner suppresses all competitors
- Below threshold: "progressively decaying wave" that never becomes conscious
- Pre-stimulus state (context, goals) biases which processors win

**AM application**: Maps directly to conscious vs subconscious memory tiers. Conscious recall should require crossing a non-linear ignition threshold — not a smooth gradient. Below threshold: return nothing for conscious, let subconscious fill the gap. Above: explosive winner-take-all recall.

---

## Synthesis: Proposed Gating Architecture for AM

Six layers, ordered from cheapest to most expensive:

### Layer 1: IDF Activation Gate

Don't activate occurrences whose IDF weight is below a threshold (e.g., `< 0.05`). Prevents common words from triggering anything. **Cheapest possible fix.**

### Layer 2: Fan Effect / TF Saturation

Cap the contribution of any single word: `contribution = IDF * min(activation_count, k1+1) / (activation_count + k1)` with k1 ~ 1.5. Prevents runaway activation counts.

### Layer 3: Minimum Overlap Threshold

Require `activated_count / total_count > 0.15` for a neighborhood to qualify. Ensures non-trivial overlap with the query.

### Layer 4: Phasor Interference Gate (RESTORE FROM EXISTING CODE)

Only include conscious memories where aggregate interference is positive. This is the original DAE's gate — already implemented, just needs wiring.

### Layer 5: Vividness Gate (RESTORE FROM EXISTING CODE)

Only include neighborhoods where `activated_count / total_count > THRESHOLD (0.5)`. Already implemented in surface.rs, just needs wiring.

### Layer 6: Ignition Threshold

After all scoring, require `max_score > tau` for conscious recall. If nothing crosses the threshold, return empty conscious recall rather than the "best" garbage.

### Remove

- `DECISION_FLOOR = 15.0` — this is the primary cause of the current bug
- Decision/Preference exemption from diminishing returns — no type should be immune to session-level suppression

### Keep (as safety net)

- `DECISION_MULTIPLIER = 3.0` — reasonable importance signal as long as the floor is removed
- Epoch-based Jaccard overlap — useful safety net even with interference active

---

## Key References

- Ramsauer et al. 2020 — Modern Hopfield / attention equivalence: https://ar5iv.labs.arxiv.org/html/2008.02217
- Hu et al. NeurIPS 2024 — Spherical codes for optimal memory capacity: https://arxiv.org/abs/2410.23126
- Muolo et al. 2025 — Curved neural networks, explosive transitions: https://www.nature.com/articles/s41467-025-61475-w
- Kanerva — Sparse Distributed Memory: https://grokipedia.com/page/Sparse_distributed_memory
- Plate — Holographic Reduced Representations: https://www.semanticscholar.org/paper/0c4d193b4e8520dbc583cc7ee59c8417869f67ce
- ACT-R Unit 4 (activation): http://act-r.psy.cmu.edu/wordpress/wp-content/themes/ACT-R/tutorials/unit4.htm
- ACT-R Unit 5 (retrieval probability): http://act-r.psy.cmu.edu/wordpress/wp-content/themes/ACT-R/tutorials/unit5.htm
- Radovanovic et al. 2010 — Hubness in high dimensions: https://www.jmlr.org/papers/volume11/radovanovic10a/radovanovic10a.pdf
- Hubness reduction comparison 2020: https://pmc.ncbi.nlm.nih.gov/articles/PMC7327987/
- Baars — Global Workspace Theory: https://pmc.ncbi.nlm.nih.gov/articles/PMC8770991/
- BM25: https://en.wikipedia.org/wiki/Okapi_BM25
- Bricken — SDM and Hopfield connection: https://www.trentonbricken.com/SDM-And-Hopfield-Networks/
