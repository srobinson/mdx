---
title: "DAE Design Intent and Mathematical Invariants"
type: research
tags: [dae, philosophy, theory, invariants, attention-matters]
summary: "Analysis of load-bearing vs incidental properties in DAE theory — what can be modified safely"
status: active
created: 2026-02-21
updated: 2026-02-21
project: am
confidence: medium
---

# DAE Design Intent and Mathematical Invariants

## 1. Core Thesis: What Problem Does DAE Solve?

DAE's thesis is that memory is not retrieval — it is **emergence on a living geometry**. The system deliberately rejects the dominant paradigm (embed-then-lookup) and replaces it with a dynamical system that changes shape when you use it.

The problem statement, distilled from MANIFOLD.md and the three variant READMEs:

> Vector databases store embeddings in a flat space and retrieve by cosine similarity. That is a lookup table with better math. DAE models memory as a closed manifold that changes shape when you use it. Memories that co-occur drift together. Memories that resonate synchronize. The system does not retrieve memories. It grows them.

This is a genuinely different approach to memory. RAG systems answer "what is most similar to this query?" — DAE answers "what does the current shape of my experience say is relevant right now?" The distinction matters because:

1. **RAG is stateless.** Each query hits the same index. The act of remembering does not change what you will remember next time. DAE is stateful — every query reshapes the manifold, so the same question asked twice produces different results because the first asking changed the geometry.

2. **RAG has no temporal dynamics.** Embeddings are fixed at indexing time. DAE's phases evolve via Kuramoto coupling, so memories that are repeatedly co-activated gradually synchronize, making their co-surfacing increasingly likely. The system develops habits of association.

3. **RAG has no attention budget.** You can add unlimited content to a vector store. DAE enforces M=1 (fixed total mass), meaning importance is a zero-sum game. Making one memory more prominent necessarily makes others less prominent. This mirrors biological attention.

4. **RAG has no novel connections.** Cosine similarity returns the most similar content. DAE's novel connection mechanism explicitly surfaces content with minimal overlap (1-2 shared words, high IDF weight) — lateral bridges that a similarity search would never find.

The contrarian bet (surfaced from memory): DAE bets on human-in-the-loop collaboration rather than full autonomy. The memory system is designed for a hybrid agent — not a fully autonomous system that needs perfect recall, but a collaborative one that benefits from unexpected associations, evolving priorities, and an attention budget that forces triage.

---

## 2. Why S3? Why Not S2 or Euclidean Space?

### The Argument for S3

S3 (the 3-sphere, the surface of the unit ball in R4) is chosen for several interlocking reasons:

**Finite but unbounded.** S3 has no edges, no corners, no privileged center. Every point is geometrically equivalent to every other. This means there is no "center of memory" and no "edge of memory" — no spatial bias in the system. On a flat space (Euclidean), the origin would be privileged. On S2 (a 2-sphere), you get the same unboundedness but in fewer dimensions.

**Closed manifold enables conservation.** The fixed total mass M=1 requires a compact (closed) manifold. On an open manifold like Euclidean space, conservation of mass would require boundary conditions, which would re-introduce spatial privilege. On a closed manifold, conservation is natural — mass is a density function on a finite surface, and integrating it always gives M=1.

**Quaternion algebra.** S3 _is_ the group of unit quaternions. This is not a coincidence — it is the load-bearing design choice. Points on S3 have a natural group structure (quaternion multiplication), which gives you:

- **SLERP** as a geodesic interpolation (the quaternion equivalent of linear interpolation on flat space)
- **Hamilton product** for composing rotations/positions
- **Uniform random sampling** via known algorithms (Shoemake, Marsaglia)
- **Antipodal equivalence** (q and -q represent the same rotation), which bounds the maximum geodesic distance to pi

**Sufficient dimensionality.** S2 (a 2-sphere) is 2-dimensional. S3 is 3-dimensional (it lives in R4, but its intrinsic dimension is 3). The neighborhood radius is pi/phi ~ 111 degrees, which carves out a significant fraction of the manifold. On S2, this would be even more of the total surface, leading to more overlap between neighborhoods. S3 provides more room for neighborhoods to be geometrically distinct.

### What Would Break on S2

- **No natural group structure.** S2 is not a Lie group. You cannot multiply two points on S2 to get another point on S2 in a way that forms a group. This means SLERP would still work (geodesics exist on S2), but the `randomNear()` operation (which uses quaternion multiplication to place a point near a seed) would need a different implementation. The Hamilton product trick — build a rotation quaternion and multiply it by the seed — only works because S3 _is_ the quaternion group.
- **Phasor interference still works.** The phasor system is on S1 (the circle), not on the spatial manifold. S2 vs S3 wouldn't affect interference.
- **Kuramoto coupling still works.** It operates on phases, not positions.
- **Drift still works.** SLERP exists on any sphere. But the meeting-point calculation in pairwise drift uses quaternion interpolation properties that assume S3.

### What Would Break in Euclidean Space

- **No conservation of mass.** The manifold is open — mass can spread infinitely. You lose the M=1 constraint and the finite attention budget.
- **No natural angular metric.** Geodesic distance on S3 gives you an angle in [0, pi]. In Euclidean space, distances are unbounded, and there is no natural notion of "how far apart" that saturates.
- **SLERP becomes LERP.** Linear interpolation in flat space doesn't have the same properties — it doesn't preserve unit length, and the "meeting point" concept loses its geometric elegance.
- **No phyllotaxis analogy.** The golden-angle distribution on a circle (phasors) and the neighborhood cap on a sphere both rely on the compact, bounded nature of the manifold.

### Verdict: S3 is Load-Bearing

S3 is not a convenient choice — it is the _only_ manifold that simultaneously provides: a natural group structure (quaternion algebra), a compact topology (conservation of mass), sufficient dimension (neighborhood separation), and a rich set of tools (SLERP, Hamilton product, uniform sampling). Changing the manifold would require rederiving most of the system.

---

## 3. Why Quaternions? What Properties Are Being Exploited?

Quaternions are the native coordinate system for S3 — a unit quaternion _is_ a point on S3. But DAE exploits several quaternion properties beyond mere representation:

### 3.1 SLERP as Geodesic Interpolation

SLERP (Spherical Linear Interpolation) traces the shortest path between two points on S3. This is geometrically meaningful: when two memories drift toward each other, they move along the great circle connecting them — the most natural path on the manifold. SLERP preserves unit length (stays on S3) and has constant angular velocity (moves at uniform speed along the geodesic).

**Load-bearing:** The drift mechanism depends on SLERP producing geometrically meaningful interpolated positions. Any replacement would need to produce geodesic paths on a compact manifold.

### 3.2 Antipodal Equivalence

For unit quaternions, q and -q represent the same rotation. SLERP handles this by checking `dot < 0` and negating to take the shorter arc. This means the maximum meaningful distance is pi, not 2\*pi. The neighborhood radius (pi/phi) is defined relative to this maximum.

**Load-bearing for distance metrics; incidental for memory semantics.** The specific value pi as the maximum distance is a consequence of quaternion representation. The ratio (pi/phi for neighborhoods) is the load-bearing constant.

### 3.3 Hamilton Product for Composition

The `randomNear()` function builds a rotation quaternion from a random axis and angle, then multiplies it by the seed to place a new point. This uses the Hamilton product (quaternion multiplication) as a composition of rotations. The result is a uniform distribution within a spherical cap — exactly what is needed for neighborhood placement.

**Load-bearing for placement.** The uniform-within-cap distribution is essential for neighborhood structure. The Hamilton product is the mechanism, but the property (uniform cap distribution) is what matters.

### 3.4 Four-Component Representation Enables R4 Centroid

The centroid drift algorithm computes an IDF-weighted mean in R4 (treating quaternions as 4-vectors), then normalizes back to S3. This "project to R4, average, project back" trick works because quaternions have 4 components and the embedding space is Euclidean. The leave-one-out centroid is an O(1) operation per occurrence because you can subtract the individual contribution from the precomputed sum.

**Load-bearing for performance; the math is correct for any sphere.** The same centroid-projection trick works for S2 (3D vectors normalized to unit length). But the 4-component structure of quaternions makes the implementation natural.

### 3.5 What Quaternion Properties Are NOT Exploited

- **Non-commutativity of multiplication.** DAE never uses q1*q2 where order matters. The Hamilton product is used only in randomNear (rotation * seed), where commutativity is not relevant because the rotation is random.
- **Quaternion conjugate.** Not used.
- **Quaternion inverse.** Not used.
- **Rotation representation.** DAE treats quaternions as points on S3, not as rotations of 3D space. The fact that quaternions can represent 3D rotations is coincidental — DAE never applies a quaternion to a 3D vector.

### Verdict: Quaternions Are Load-Bearing as S3 Coordinates

Quaternions are load-bearing because they ARE S3. You cannot represent S3 without quaternions (or an equivalent 4-component parameterization). The specific quaternion operations used (SLERP, dot product, Hamilton product for placement) are the natural operations on S3. Replacing quaternions would mean replacing S3.

---

## 4. The Role of Drift

Drift is the mechanism by which the manifold changes shape through use. It is **fundamental to the theory, not an optimization**.

### What Drift Does

When a query activates words across the manifold, activated words SLERP toward each other. The magnitude of drift is controlled by:

- **IDF weight:** Rare words drift more (they carry more signal)
- **Drift rate:** Determined by the ratio of individual activation to container activation (words activated proportionally more are more anchored)
- **THRESHOLD (0.5):** Serves as a damping factor, halving the drift step

### Why Drift Is Fundamental

1. **Drift creates associative structure.** Words that are frequently co-activated end up spatially close on S3. This is not just a side effect — it IS the learning mechanism. The manifold develops topological structure that reflects patterns of use. Without drift, words would remain at their initial random positions, and the spatial structure would carry no information.

2. **Drift implements competitive learning.** Because the manifold is closed (M=1), drift is a zero-sum game. When words cluster in one region, they effectively "push out" other words (by making those other regions less dense). This creates a competitive dynamic where the most frequently activated associations dominate the geometry.

3. **Drift creates anchoring.** The anchoring threshold (c/C > 0.5) means that heavily activated words stop drifting. They become fixed points on the manifold — landmarks that other words drift toward but that do not themselves move. This is the mechanism by which the manifold crystallizes around its most important structures.

4. **Drift is irreversible.** Once a word has drifted, it stays at its new position. There is no "un-drift" operation. This gives the system a genuine history — the current shape of the manifold is the cumulative result of every query that ever activated it.

### The Plasticity Curve

The plasticity function `1 / (1 + ln(1 + c))` modulates how much a word's phase changes under Kuramoto coupling. It has the property of diminishing returns:

- c=0: plasticity = 1.0 (fully responsive)
- c=10: plasticity = 0.294
- c=100: plasticity = 0.178
- c=1000: plasticity = 0.126

This is logarithmic "forgetting of the ability to forget." Early activations change the memory substantially. Later activations barely move it. The manifold has a memory of its own learning history encoded in its rigidity.

### Verdict: Drift Is Load-Bearing

Drift is not an optimization step — it is the core learning mechanism. Without drift, the manifold would be static, and the system would degenerate to a fancy keyword index. The specific drift formula (pairwise vs centroid) is an implementation choice, but the existence of spatial drift driven by IDF-weighted co-activation is a fundamental property of the theory.

---

## 5. Oscillator Model and Attention: Why Kuramoto?

### The Analogy

The Kuramoto model describes how coupled oscillators synchronize. In physics, it explains firefly synchronization, cardiac pacemaker cells, power grid frequency locking, and neural oscillation patterns. DAE applies it to memory:

- Each word occurrence has a phase angle (phasor theta)
- Words shared between conscious and subconscious manifolds are coupled oscillators
- Over repeated activations, their phases synchronize

### Why Oscillators Model Attention

The insight is that **attention is not a static property — it is a dynamical process**. When you attend to something, you are not just "pointing" at it — you are synchronizing your internal state with it. The Kuramoto model captures this:

1. **Phase coherence = relevance.** When conscious and subconscious copies of a word are in phase (theta_con ~ theta_sub), interference is constructive (cos(diff) > 0), and the subconscious memory surfaces. When they are out of phase, interference is destructive, and the memory is suppressed. Synchronization literally creates relevance.

2. **Coupling strength encodes importance.** The coupling constant is IDF_weight^2. Rare words couple much more strongly than common words. "Mycelial" in both manifolds creates a strong coupling; "the" creates almost none. This is information-theoretic: rare shared terms carry more mutual information.

3. **Asymmetric coupling models attentional hierarchy.** K_CON = N_sub/N_total, K_SUB = N_con/N_total. When the conscious manifold is small (as it typically is), K_CON is large and K_SUB is small. This means the subconscious is pulled strongly toward conscious phase alignment, but conscious is barely affected by the subconscious. Conscious attention is the attractor — it shapes the subconscious, not the other way around. This is a direct model of top-down attentional modulation.

4. **The sin(phaseDiff) coupling function has natural dynamics.** Maximum coupling at pi/2 phase difference (furthest from both alignment and anti-alignment). Zero coupling at perfect alignment (already synchronized) and perfect opposition (unstable equilibrium). This creates a self-limiting system: once phases align, coupling stops pulling them. No runaway synchronization.

5. **Plasticity-modulated coupling prevents over-consolidation.** Heavily activated occurrences (high c) have low plasticity, so their phases barely change even under strong coupling. This protects established memories from being overwritten by new associations.

### What the Phasor Represents

The phasor theta is assigned sequentially within a neighborhood using golden-angle spacing: `theta_i = i * GOLDEN_ANGLE`. This means:

- Words early in a text chunk have different phases than words late in it
- The golden angle ensures maximum phase separation (no two words perfectly align)
- Phase carries positional/temporal information within a context

Interference between conscious and subconscious copies of a word is therefore comparing when/where that word appeared in different contexts. Constructive interference means the word appeared in analogous positions within analogous contexts. Destructive means the contexts are phase-misaligned — the word plays different roles.

### Verdict: Kuramoto Is Load-Bearing with Caveats

The oscillator model is load-bearing for the interference and phase-coupling mechanisms. Without it, there is no way to determine which subconscious memories are "in phase" with current conscious attention. The specific use of `sin(phaseDiff)` for coupling (rather than, say, a linear function of phase difference) is standard Kuramoto and has desirable stability properties that other functions would not have.

However, the initial phase assignment (golden angle from positional index) is more **incidental** than load-bearing. The golden angle guarantees maximal separation, which is elegant, but other irrational-angle distributions would also work. What matters is that phases are distributed non-commensurately so that interference is meaningful.

---

## 6. Load-Bearing Properties (Cannot Change Without Breaking Theory)

### 6.1 The Closed Manifold (M=1)

The fixed total mass is what creates the finite attention budget. Every occurrence's mass is c/N, and sum(c/N) = M = 1. This is a conservation law. Removing it would make the system open-ended — everything could become important simultaneously, eliminating the competitive dynamics that make triage meaningful.

**Cannot change:** The total mass must be conserved. The specific value (M=1) is a normalization convention that could be any positive constant, but the conservation property itself is essential.

### 6.2 S3 as the Spatial Manifold

As argued in Section 2, S3 provides the unique combination of compactness (conservation), group structure (SLERP, Hamilton product), sufficient dimension, and no privileged center. Changing the manifold requires rederiving the entire system.

**Cannot change:** The manifold must be S3 or something isomorphic to it.

### 6.3 Drift as a Learning Mechanism

Drift is what makes the manifold "alive." Without it, the system is a static index with fancy scoring. The manifold must change shape through use, with co-activated words moving closer together.

**Cannot change:** There must be a spatial drift mechanism driven by co-activation. The specific drift formula (pairwise vs centroid, IDF weighting, THRESHOLD damping) can be tuned, but drift itself cannot be removed.

### 6.4 The Two-Manifold Architecture (Conscious/Subconscious)

The separation between conscious (agent-marked salient content) and subconscious (all ingested content) is essential for:

- Interference computation (requires two manifolds with different phase distributions)
- Kuramoto coupling (cross-manifold synchronization requires two distinct manifolds)
- The three-tier recall model (conscious recall, subconscious recall, novel connections)
- Attentional hierarchy (K_CON + K_SUB = 1, with conscious as attractor)

**Cannot change:** There must be two distinct manifolds with cross-manifold coupling. The conscious/subconscious framing could be renamed, but the structural duality is essential.

### 6.5 Phasor Interference as a Surfacing Criterion

The decision of whether a subconscious memory surfaces depends on cos(phase_difference) between its phasor and the conscious mean phase. Positive interference = surfaces. This is the core mechanism by which the system decides what is relevant.

**Cannot change:** Surfacing must depend on phase coherence between manifolds. The cosine function is standard wave physics and should not be replaced.

### 6.6 IDF Weighting

Inverse neighborhood frequency is the importance signal that pervades the system: it modulates drift magnitude, Kuramoto coupling strength (squared!), and context scoring. Without it, common words ("the", "is") would dominate every operation, drowning out meaningful signal.

**Cannot change:** There must be an inverse-frequency weighting scheme. The specific formula (1/count) could use log-smoothed IDF or other variants, but the principle of down-weighting common words is essential.

### 6.7 Anchoring

The anchoring threshold (c/C > THRESHOLD) prevents heavily activated words from drifting. This is the mechanism by which the manifold crystallizes. Without anchoring, the manifold would be perpetually plastic — no stable structure would ever form.

**Cannot change:** There must be an anchoring mechanism that freezes words after sufficient activation. The specific threshold (0.5) and formula could vary.

### 6.8 The K_CON + K_SUB = 1 Constraint

This ensures the total coupling strength across manifolds is conserved, just like total mass M=1. It also creates the asymmetric coupling where conscious attention dominates (when N_con << N_sub, K_CON is large).

**Cannot change:** Coupling constants must sum to a fixed value and be inversely proportional to manifold size.

---

## 7. Incidental Properties (Can Be Changed Safely)

### 7.1 The Specific Value of THRESHOLD (0.5)

THRESHOLD appears in multiple roles: anchoring (c/C > 0.5), vivid recall (ratio > 0.5), drift damping (factor \* 0.5). The value 0.5 is convenient (halfway) but not mathematically derived from phi or pi. It could be tuned without breaking the theory, though all its uses would need to be considered together.

**Can change:** But must remain a single universal constant used consistently across all roles. Splitting it into multiple independent thresholds would be a design decision, not a theoretical requirement.

### 7.2 The Drift Rate Formula

The two variants (standalone: `1 - 2c/C`, openclaw: `(c/C)/0.5`) produce inversely related drift profiles. The synthesis document notes this is a design decision. Either formula satisfies the core requirements (drift exists, anchoring occurs at threshold, IDF modulates magnitude). Other monotonic functions with the same boundary conditions would also work.

**Can change:** The drift rate curve is tunable. What matters is: zero drift when anchored, non-zero drift when mobile, IDF modulation.

### 7.3 Number of Sentences per Neighborhood Chunk (3)

Text is split into 3-sentence chunks for neighborhood creation. This is a tuning parameter — 2 or 5 sentences would also work. The number affects neighborhood granularity but not the theory.

**Can change freely.**

### 7.4 Episode Threshold (5 exchanges)

Conversation episodes are created every 5 buffered exchanges. This is a tuning parameter.

**Can change freely.**

### 7.5 Context Composition Limits (1 conscious, 2 subconscious, 1 novel)

The number of neighborhoods surfaced in each category is a practical limit, not a theoretical one. You could surface more or fewer.

**Can change freely.** Though the distinction between the three categories (conscious/subconscious/novel) is load-bearing, the count limits are not.

### 7.6 Novelty Score Formula

`novelty = maxWordWeight * maxPlasticity * (1/activatedCount)` is one reasonable way to score novel connections. Other formulas combining rarity, freshness, and thin connection would also work.

**Can change.** The criteria for novelty (few activated words, no conscious overlap, high IDF bridge word) are more important than the exact scoring formula.

### 7.7 Quaternion Random Generation Algorithm

Shoemake vs Marsaglia — both produce uniform distributions on S3. The algorithm is an implementation detail.

**Can change freely.** What matters is uniformity of the distribution.

### 7.8 SLERP Near-Parallel Threshold (0.9995 vs 1-epsilon)

The threshold at which SLERP falls back to linear interpolation is a numerical detail. 0.9995 is standard practice in graphics.

**Can change freely.**

### 7.9 The Plasticity Curve Shape

`1/(1 + ln(1+c))` is one function with diminishing returns. Other sublinear monotonically decreasing functions (e.g., `1/(1+c)^alpha` for small alpha, or `exp(-c/k)`) would serve the same purpose.

**Can change** as long as the replacement function satisfies: plasticity(0) ~ 1, monotonically decreasing, approaching 0 slowly. The logarithmic shape has a nice information-theoretic justification (harmonic series ~ log), but it is not the only valid choice.

### 7.10 Golden Angle for Phasor Spacing

The golden angle (2\*pi/phi^2 ~ 137.5 deg) maximizes minimum spacing on the circle. This is elegant and well-motivated, but other irrational multiples of pi would also produce non-commensurate phase distributions. The key requirement is that phases never perfectly align.

**Can change** but the golden angle is optimal for the stated purpose (maximizing minimum distance), so there is little reason to change it.

### 7.11 Neighborhood Radius (pi/phi)

The angular cap radius for word placement within a neighborhood. This affects how tightly words cluster and how much neighborhoods can overlap. Pi/phi is derived from the golden ratio division of the meaningful angular range [0, pi], which is aesthetically pleasing and produces good separation. Other values in the range [0.5*pi, pi] would work differently but not break the theory.

**Can change** but would affect the degree of neighborhood overlap and the effective number of distinct regions on the manifold.

---

## 8. Epoch-Based Jaccard Overlap Penalty: Impact Assessment

### What the Proposed Change Does

The proposed modification adds **contradiction handling** via epoch-based Jaccard overlap. The idea: when new content has high token overlap with existing content but different semantic intent (e.g., correcting a previous statement), the system should recognize this as a contradiction/update rather than reinforcement.

### Does It Violate Load-Bearing Properties?

**M=1 Conservation:** No violation. Adding a penalty/score modifier does not change total mass. The penalty would affect surfacing decisions, not mass distribution.

**S3 Manifold:** No violation. The penalty operates on token sets (Jaccard similarity), not on manifold geometry. It does not modify quaternion positions, phasor phases, or the spatial structure.

**Drift:** No violation. Drift operates on activated occurrences, and a Jaccard penalty would affect _which_ content surfaces, not _how_ words move on the manifold.

**Two-Manifold Architecture:** No violation. The penalty could be applied during surface computation or context composition, which are downstream of the manifold mechanics.

**Phasor Interference:** Potential interaction, but not violation. If a Jaccard penalty suppresses a neighborhood that would otherwise surface via positive interference, this is a scoring modification layered on top of the interference signal. The interference itself (cos(phase_difference)) is unchanged.

**IDF Weighting:** No violation. Jaccard similarity uses token overlap, which is related to but independent of IDF scoring. They could interact (high-IDF overlapping tokens would be more significant), which is actually desirable.

**Anchoring:** No violation. Anchoring is a drift-rate mechanism, not a surfacing mechanism.

**K_CON + K_SUB = 1:** No violation. Kuramoto coupling is unchanged.

### Where It Operates

The Jaccard overlap penalty would most naturally operate in one of two places:

1. **Surface computation** (Section 15 of the openclaw analysis): After determining which occurrences surface via interference, apply a penalty to neighborhoods whose Jaccard overlap with recently ingested content exceeds a threshold. This would filter contradicted content before context composition.

2. **Context composition** (Section 16): After scoring neighborhoods but before selecting the top-1/top-2/top-1, apply a Jaccard penalty to the score. Neighborhoods with high overlap to more recent content (same epoch or later epoch) would have their scores reduced.

### The Theory Gap It Fills

DAE v0.7.2 has no mechanism for handling contradiction or supersession. If you ingest "the API uses port 8080" and later ingest "the API uses port 9090", both memories persist with equal standing. The system has no way to know the second supersedes the first. Co-activation of "API" and "port" would actually drift them together and strengthen the association — making the contradiction worse, not better.

The current theory addresses **recency** only through plasticity (new content is more plastic) and **importance** through IDF/activation (frequently activated content scores higher). It does not address **conflict between content with overlapping topics but different claims**.

An epoch-based Jaccard overlap penalty fills this gap without disturbing the manifold mechanics. It operates at the scoring/surfacing layer, not at the geometric layer. This is the right layer for such a feature — the manifold should model ALL memories (including superseded ones), but the surfacing logic should prefer the most recent version when multiple contradictory memories exist.

### Recommendation

**The proposed change is safe.** It operates in a space the original theory does not address (content contradiction/supersession) and does not modify any load-bearing properties. It is best implemented as a scoring modifier in the context composition phase, applied after interference-based surfacing but before final neighborhood selection.

Specific design considerations:

- **Epoch must be well-defined.** Each neighborhood or episode needs a timestamp or epoch number for recency comparison. Episodes already have timestamps.
- **Jaccard threshold needs tuning.** Too low and unrelated content is penalized; too high and only exact duplicates are caught. A threshold around 0.3-0.5 Jaccard similarity (on IDF-weighted tokens, not raw tokens) would likely work.
- **The penalty should suppress, not delete.** Superseded content should remain on the manifold (it may become relevant in historical context) — it should just score lower in surfacing.
- **Consider IDF-weighted Jaccard.** Raw Jaccard would be dominated by common words. Weighting tokens by their IDF score before computing overlap would make the penalty sensitive to meaningful overlap, not stopword overlap.

---

## Summary Table

| Property                    | Classification       | Rationale                                                               |
| --------------------------- | -------------------- | ----------------------------------------------------------------------- |
| S3 manifold                 | LOAD-BEARING         | Only manifold with group structure + compactness + sufficient dimension |
| M=1 conservation            | LOAD-BEARING         | Creates finite attention budget; defines competitive dynamics           |
| Quaternion representation   | LOAD-BEARING         | Native coordinates for S3; enables SLERP, Hamilton product              |
| Two-manifold architecture   | LOAD-BEARING         | Required for interference, Kuramoto, and attentional hierarchy          |
| Drift via SLERP             | LOAD-BEARING         | Core learning mechanism; makes manifold stateful                        |
| Anchoring                   | LOAD-BEARING         | Crystallization mechanism; prevents perpetual plasticity                |
| Phasor interference (cos)   | LOAD-BEARING         | Surfacing criterion; determines relevance via phase coherence           |
| IDF weighting               | LOAD-BEARING         | Information-theoretic importance signal; pervades all operations        |
| Kuramoto coupling           | LOAD-BEARING         | Cross-manifold synchronization; creates attentional dynamics            |
| K_CON + K_SUB = 1           | LOAD-BEARING         | Conservation of coupling; asymmetric attentional hierarchy              |
| Plasticity (1/(1+ln(1+c)))  | INCIDENTAL (shape)   | Diminishing returns required; specific curve is tunable                 |
| THRESHOLD = 0.5             | INCIDENTAL (value)   | Convenient but not derived from phi/pi; tunable                         |
| Golden angle phasors        | INCIDENTAL (optimal) | Optimal spacing but other irrationals would work                        |
| Neighborhood radius pi/phi  | INCIDENTAL (tunable) | Affects clustering density; derived from phi but adjustable             |
| Drift rate formula          | INCIDENTAL (curve)   | Two variants exist; boundary conditions matter, not curve shape         |
| Chunk size (3 sentences)    | INCIDENTAL (tuning)  | Practical parameter; no theoretical significance                        |
| Context limits (1/2/1)      | INCIDENTAL (tuning)  | Practical parameter; category distinction is load-bearing               |
| Novelty score formula       | INCIDENTAL (scoring) | Criteria matter more than exact formula                                 |
| Quaternion RNG algorithm    | INCIDENTAL (impl)    | Uniformity matters, not the specific algorithm                          |
| Epoch-based Jaccard penalty | COMPATIBLE           | Fills a theory gap; operates at scoring layer, not manifold layer       |
