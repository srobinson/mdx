# DAE v0.7.2 Standalone Browser — Complete Technical Analysis

Source: `/Users/alphab/Dev/LLM/DEV/DAE/SOURCE/dae-stand-alone/dae_v072.html`
2611 lines, single-file HTML+JS application.

---

## 1. Mathematical Foundations

### 1.1 The S3 Manifold Model

The core insight: memory is modeled as a **closed 3-sphere (S3)** with fixed total mass **M = 1**. Adding content increases resolution/density, not volume. The system is a finite universe that becomes increasingly fine-grained.

```js
const M = 1;  // Total system mass (normalized). Closed universe.
```

Every occurrence's mass is `count / N` where N is total occurrences system-wide. Individual words don't "weigh" a fixed amount; their mass is a proportion of the whole. As N grows, each individual mass shrinks but the total remains 1.

### 1.2 Quaternion Representation

Unit quaternions represent points on S3. Each quaternion `(w, x, y, z)` is always normalized on construction:

```js
class Quaternion {
    constructor(w, x, y, z) {
        this.w = w; this.x = x; this.y = y; this.z = z;
        this._normalize();
    }

    _normalize() {
        const norm = Math.sqrt(this.w*this.w + this.x*this.x + this.y*this.y + this.z*this.z);
        if (norm < EPSILON) {
            this.w = 1; this.x = 0; this.y = 0; this.z = 0;
        } else {
            this.w /= norm; this.x /= norm; this.y /= norm; this.z /= norm;
        }
    }
}
```

Key property: in quaternion space, antipodal points `q` and `-q` represent the same rotation. This means the maximum meaningful angular distance is pi, not 2*pi. This fact drives the neighborhood radius constant.

### 1.3 Quaternion Operations

**Multiplication (Hamilton product):**
```js
multiply(other) {
    return new Quaternion(
        this.w*other.w - this.x*other.x - this.y*other.y - this.z*other.z,
        this.w*other.x + this.x*other.w + this.y*other.z - this.z*other.y,
        this.w*other.y - this.x*other.z + this.y*other.w + this.z*other.x,
        this.w*other.z + this.x*other.y - this.y*other.x + this.z*other.w
    );
}
```

**Dot product:**
```js
dot(other) {
    return this.w*other.w + this.x*other.x + this.y*other.y + this.z*other.z;
}
```

**Angular distance:**
```js
angularDistance(other) {
    const d = Math.min(1, Math.max(-1, Math.abs(this.dot(other))));
    return 2 * Math.acos(d);
}
```
Note the `Math.abs` on the dot product -- this handles the antipodal equivalence. The factor of 2 converts from half-angle (quaternion representation) to full angle.

**SLERP (Spherical Linear Interpolation):**
```js
slerp(other, t) {
    let dot = this.dot(other);
    let ow = other.w, ox = other.x, oy = other.y, oz = other.z;

    // Take shorter path
    if (dot < 0) {
        dot = -dot;
        ow = -ow; ox = -ox; oy = -oy; oz = -oz;
    }
    dot = Math.min(1, dot);

    // Linear interpolation for very close quaternions
    if (dot > 1 - EPSILON) {
        return new Quaternion(
            this.w + t * (ow - this.w),
            this.x + t * (ox - this.x),
            this.y + t * (oy - this.y),
            this.z + t * (oz - this.z)
        );
    }

    const theta = Math.acos(dot);
    const sinTheta = Math.sin(theta);
    const s0 = Math.sin((1 - t) * theta) / sinTheta;
    const s1 = Math.sin(t * theta) / sinTheta;

    return new Quaternion(
        s0 * this.w + s1 * ow,
        s0 * this.x + s1 * ox,
        s0 * this.y + s1 * oy,
        s0 * this.z + s1 * oz
    );
}
```

SLERP is the workhorse operation. It handles:
- Antipodal correction (negate if dot < 0 to take shorter path)
- Degenerate case (dot near 1.0 falls back to linear interpolation)
- Standard formula: `sin((1-t)*theta)/sin(theta) * q1 + sin(t*theta)/sin(theta) * q2`

### 1.4 Uniform Random Quaternion Generation (Marsaglia's Method)

```js
static random() {
    let u1, u2, s1;
    do {
        u1 = Math.random() * 2 - 1;
        u2 = Math.random() * 2 - 1;
        s1 = u1*u1 + u2*u2;
    } while (s1 >= 1);

    let u3, u4, s2;
    do {
        u3 = Math.random() * 2 - 1;
        u4 = Math.random() * 2 - 1;
        s2 = u3*u3 + u4*u4;
    } while (s2 >= 1);

    const sqrtTerm = Math.sqrt((1 - s1) / s2);
    return new Quaternion(u1, u2, u3 * sqrtTerm, u4 * sqrtTerm);
}
```

This produces uniformly distributed points on S3. It uses rejection sampling on two 2D discs, then combines them. The `sqrtTerm = sqrt((1-s1)/s2)` factor ensures the 4D point lies on the unit sphere.

### 1.5 Random Near (Neighborhood Placement)

```js
static randomNear(seed, angularRadius = NEIGHBORHOOD_RADIUS) {
    // Random axis via Gaussian distribution
    let ax = gaussRandom();
    let ay = gaussRandom();
    let az = gaussRandom();
    const axNorm = Math.sqrt(ax*ax + ay*ay + az*az);
    if (axNorm < EPSILON) { ax = 1; ay = 0; az = 0; }
    else { ax /= axNorm; ay /= axNorm; az /= axNorm; }

    // Random angle within cap (sqrt for uniform area distribution)
    const angle = angularRadius * Math.sqrt(Math.random());
    const halfAngle = angle / 2;
    const sinHalf = Math.sin(halfAngle);
    const cosHalf = Math.cos(halfAngle);

    const rotation = new Quaternion(cosHalf, ax * sinHalf, ay * sinHalf, az * sinHalf);
    return rotation.multiply(seed);
}
```

Key details:
- Random axis: three independent Gaussian samples, normalized. This gives a uniform direction on S2.
- `Math.sqrt(Math.random())` for the angle: this corrects for the fact that spherical cap area increases with angle. Without sqrt, points would cluster near the pole.
- The rotation quaternion is `cos(halfAngle) + sin(halfAngle) * axis`, then multiplied by the seed to position the result near the seed.

### 1.6 Golden-Angle Distribution

```js
const PHI = (1 + Math.sqrt(5)) / 2;                    // 1.618033988749895
const GOLDEN_ANGLE = (2 * Math.PI) / (PHI * PHI);       // 2.399963229728653 rad = 137.508 deg
const NEIGHBORHOOD_RADIUS = Math.PI / PHI;               // 1.941611400220653 rad = 111.246 deg
```

The golden angle (2*pi/phi^2) is the same angle found in phyllotaxis (sunflower seed spirals, pinecones). It is mathematically proven to maximize the minimum distance between successive points on a circle.

The neighborhood radius (pi/phi) is the golden ratio division of the complete angular space. Since antipodal quaternions are equivalent, pi (not 2*pi) is the full meaningful range. Dividing by phi gives the largest "neighborhood" that maintains golden-ratio proportions.

### 1.7 Box-Muller Transform (Gaussian Random)

```js
function gaussRandom() {
    const u1 = Math.random();
    const u2 = Math.random();
    return Math.sqrt(-2 * Math.log(u1)) * Math.cos(2 * Math.PI * u2);
}
```

Standard Box-Muller transform producing normally distributed values from uniform random inputs. Used for generating random rotation axes.

---

## 2. Core Algorithms

### 2.1 Phasor System

Each occurrence carries a phase angle theta (a "DaemonPhasor"):

```js
class DaemonPhasor {
    constructor(theta) {
        this.theta = ((theta % (2 * Math.PI)) + 2 * Math.PI) % (2 * Math.PI);
    }

    static fromIndex(index, baseTheta = 0) {
        return new DaemonPhasor(baseTheta + index * GOLDEN_ANGLE);
    }

    phaseDifference(other) {
        let diff = Math.abs(this.theta - other.theta);
        if (diff > Math.PI) diff = 2 * Math.PI - diff;
        return diff;
    }

    interference(other) {
        return Math.cos(this.phaseDifference(other));
    }

    slerp(other, t) {
        let diff = other.theta - this.theta;
        while (diff > Math.PI) diff -= 2 * Math.PI;
        while (diff < -Math.PI) diff += 2 * Math.PI;
        return new DaemonPhasor(this.theta + t * diff);
    }
}
```

Key properties:
- Phase is always normalized to `[0, 2*pi)`.
- Successive words in a neighborhood get phases at golden-angle increments: `baseTheta + index * GOLDEN_ANGLE`. This maximizes phase separation within a neighborhood.
- **Interference is `cos(phase_difference)`**: aligned phases (+1, constructive), opposed phases (-1, destructive). Same word in different contexts gets different phases and can reinforce or cancel.
- Phasor SLERP wraps around the circle correctly (shortest path via [-pi, pi] normalization).

### 2.2 Word Positioning on the Manifold

When text is ingested, it becomes a **Neighborhood** -- a cluster of occurrences positioned near a random seed quaternion:

```js
static fromTokens(tokens, seed = null, sourceText = null) {
    const neighborhood = new Neighborhood(seed, null, sourceText);
    tokens.forEach((token, i) => {
        const position = Quaternion.randomNear(neighborhood.seed, NEIGHBORHOOD_RADIUS);
        const phasor = DaemonPhasor.fromIndex(i);
        const occ = new Occurrence(token, position, phasor);
        occ.neighborhoodId = neighborhood.id;
        neighborhood.occurrences.push(occ);
    });
    return neighborhood;
}
```

Algorithm:
1. A random seed quaternion is generated (uniform on S3).
2. Each word gets a position within `NEIGHBORHOOD_RADIUS` (pi/phi ~ 111 deg) of the seed.
3. Each word gets a phase at golden-angle spacing from index 0.
4. Each occurrence starts with `activationCount = 0`.

### 2.3 Tokenization

```js
function tokenize(text) {
    return text
        .replace(/[^\w\s']/g, ' ')    // Strip non-word chars except apostrophes
        .toLowerCase()
        .split(/\s+/)
        .map(t => t.replace(/^'+|'+$/g, ''))  // Trim leading/trailing apostrophes
        .filter(t => t.length > 0);
}
```

Preserves contractions (don't, it's) as single tokens. No stemming, no stop-word removal. The IDF weighting handles common words naturally.

### 2.4 Activation

When a query arrives, every word in the query activates all matching occurrences across the system:

```js
activateWord(word) {
    this._rebuildIndexes();
    const subconscious = [];
    const conscious = [];
    const wordLower = word.toLowerCase();

    const occs = this._wordOccurrenceIndex.get(wordLower);
    if (!occs) return { subconscious, conscious };

    for (const occ of occs) {
        occ.activate();  // activationCount++
        const ep = this._neighborhoodEpisodeIndex.get(occ.neighborhoodId);
        if (ep && ep.isConscious) {
            conscious.push(occ);
        } else {
            subconscious.push(occ);
        }
    }
    return { subconscious, conscious };
}
```

Activation is O(1) per word via pre-built indexes. Results are split into conscious (from the LLM's own salient markings) and subconscious (from ingested documents and past conversations).

### 2.5 IDF Word Weighting

```js
getWordWeight(word) {
    this._rebuildIndexes();
    const nids = this._wordNeighborhoodIndex.get(word.toLowerCase());
    return 1 / (nids ? nids.size : 1);
}
```

Weight = 1 / (number of neighborhoods the word appears in). Not classic TF-IDF -- this is pure inverse neighborhood frequency.

- "the" in 150 neighborhoods: weight = 0.0067
- "mycelial" in 2 neighborhoods: weight = 0.5

### 2.6 SLERP Drift (Spatial Consolidation)

Activated words drift toward each other on the manifold. This is the spatial learning mechanism -- co-activated words cluster together over time.

**Drift rate formula (container-relative):**
```js
getDriftRate(containerActivation) {
    if (containerActivation <= 0) return 0;
    const drift = 1 - (2 * this.activationCount / containerActivation);
    return Math.max(0, drift);  // Clamp to 0 when anchored
}
```

Where:
- `containerActivation` = total activation across all occurrences in the neighborhood
- `drift = 1 - 2c/C`
- When `c > C/2`, drift = 0 (anchored)
- When `c = 0`, drift = 1 (fully mobile)

**Anchoring threshold derivation:**
Setting drift = 0: `1 - 2c/C = 0` => `c = C/2` => threshold ratio = 0.5.

**Legacy solo drift rate** (when container unavailable):
```js
get driftRate() {
    const c = this.activationCount;
    return c <= 0 ? 0 : (c - 1) / c;
}
```
This approaches 1 asymptotically (opposite direction -- high activation = high drift in legacy mode).

**Pairwise drift algorithm (CPU, small batches < 200 mobile):**
```js
for (let i = 0; i < mobile.length; i++) {
    const occ1 = mobile[i];
    const C1 = containerActivations.get(occ1.neighborhoodId) || 0;
    const w1 = this.system.getWordWeight(occ1.word);

    for (let j = i + 1; j < mobile.length; j++) {
        const occ2 = mobile[j];
        const C2 = containerActivations.get(occ2.neighborhoodId) || 0;
        const w2 = this.system.getWordWeight(occ2.word);

        const t1 = occ1.getDriftRate(C1) * w1;
        const t2 = occ2.getDriftRate(C2) * w2;

        if (t1 > 0 || t2 > 0) {
            const total = t1 + t2;
            if (total > 0) {
                const weight = t1 / total;
                const meeting = occ1.position.slerp(occ2.position, weight);

                if (t1 > 0) {
                    occ1.position = occ1.position.slerp(meeting, t1 * THRESHOLD);
                    occ1.phasor = occ1.phasor.slerp(occ2.phasor, t1 * THRESHOLD);
                }
                if (t2 > 0) {
                    occ2.position = occ2.position.slerp(meeting, t2 * THRESHOLD);
                    occ2.phasor = occ2.phasor.slerp(occ1.phasor, t2 * THRESHOLD);
                }
            }
        }
    }
}
```

Algorithm:
1. Pre-filter: skip anchored occurrences (getDriftRate === 0).
2. For each pair of mobile occurrences:
   - Compute weighted drift rates: `t = getDriftRate(C) * wordWeight`
   - Find meeting point: SLERP between positions, weighted by `t1 / (t1 + t2)`
   - Each occurrence SLERPs toward the meeting point by `t * THRESHOLD` (0.5)
   - Phasors also SLERP toward each other at the same rate

The meeting point calculation ensures heavier (rarer) words pull more. The final SLERP factor is `driftRate * wordWeight * 0.5` -- the THRESHOLD serves as a damping factor.

**Weight floor for large queries:**
When query or response has > 50 tokens, a weight floor is applied to prevent the O(n^2) drift from exploding:
```js
const weightFloor = 1 / Math.max(1, Math.floor(totalNbhd * 0.1));
```
Words must appear in < 10% of neighborhoods to enter drift. This filters "the", "a", etc. but passes "don't" (~0.033 weight).

### 2.7 Centroid Drift (CPU large batch >= 200, or GPU >= 50)

For large batches, pairwise O(n^2) is replaced with O(n) centroid computation:

```js
// Compute IDF-weighted centroid
let sumW = 0, sumX = 0, sumY = 0, sumZ = 0, totalWeight = 0;
const weights = mobile.map(occ => {
    const w = this.system.getWordWeight(occ.word);
    sumW += occ.position.w * w;
    sumX += occ.position.x * w;
    sumY += occ.position.y * w;
    sumZ += occ.position.z * w;
    totalWeight += w;
    return w;
});

// Per-occurrence target: centroid excluding self
mobile.forEach((occ, i) => {
    const w = weights[i];
    const remWeight = totalWeight - w;
    if (remWeight < 1e-10) return;

    const tw = (sumW - occ.position.w * w) / remWeight;
    const tx = (sumX - occ.position.x * w) / remWeight;
    const ty = (sumY - occ.position.y * w) / remWeight;
    const tz = (sumZ - occ.position.z * w) / remWeight;

    // Normalize and SLERP
    const n = Math.sqrt(tw*tw + tx*tx + ty*ty + tz*tz);
    const target = new Quaternion(tw/n, tx/n, ty/n, tz/n);
    const C = containerActivations.get(occ.neighborhoodId) || 0;
    const factor = occ.getDriftRate(C) * w * 0.5;

    if (factor > 0) {
        occ.position = occ.position.slerp(target, factor);
    }
});
```

The "exclude self from centroid" step (`(sum - occ * w) / (totalWeight - w)`) is an O(1) operation per occurrence because the global sum is precomputed.

### 2.8 Phasor Interference

Cross-manifold interference determines which subconscious memories surface:

```js
computeInterference(subconscious, conscious) {
    // Group by word
    const subByWord = new Map();
    const conByWord = new Map();
    // ... grouping ...

    // Per word: circular mean of conscious phases, then per-subOcc interference
    for (const [word, subOccs] of subByWord) {
        const conOccs = conByWord.get(word);
        if (!conOccs) continue;

        // Circular mean phase of conscious occurrences
        let sinSum = 0, cosSum = 0;
        conOccs.forEach(occ => {
            sinSum += Math.sin(occ.phasor.theta);
            cosSum += Math.cos(occ.phasor.theta);
        });
        const meanConPhase = Math.atan2(sinSum / conOccs.length, cosSum / conOccs.length);

        // Each subOcc interferes with the aggregate conscious state
        for (const subOcc of subOccs) {
            let diff = Math.abs(subOcc.phasor.theta - meanConPhase);
            if (diff > Math.PI) diff = 2 * Math.PI - diff;
            const interference = Math.cos(diff);
            results.push({ subOcc, conOcc: conOccs[0], interference });
        }
    }
}
```

Optimization: instead of O(sub * con) pair-wise interference, uses circular mean phase aggregation. "the" with 500 sub and 50 con goes from 25,000 pairs to 500 cos() evaluations.

Positive interference (> 0) means the memory surfaces. Negative means suppressed.

### 2.9 Kuramoto Phase Coupling

Cross-manifold phase synchronization. When conscious and subconscious share a word, their phasors couple -- pulling toward alignment over time.

```js
applyKuramotoCoupling(wordGroups) {
    const N_con = this.system.consciousEpisode.count || 1;
    const N_sub = Math.max(1, this.system.N - N_con);
    const N_total = this.system.N || 1;

    // Coupling constants from manifold proportions
    const K_CON = N_sub / N_total;   // conscious pulls on subconscious mass
    const K_SUB = N_con / N_total;   // subconscious pulls on conscious mass
    // K_CON + K_SUB = 1 always (conserved like M=1)

    wordGroups.forEach(({ word, subOccs, conOccs }) => {
        const w = this.system.getWordWeight(word);
        const coupling = w * w;  // same word in both manifolds

        // Circular mean phases for each manifold
        const meanPhaseSub = Math.atan2(sinSumSub/subOccs.length, cosSumSub/subOccs.length);
        const meanPhaseCon = Math.atan2(sinSumCon/conOccs.length, cosSumCon/conOccs.length);

        // Phase difference normalized to [-pi, pi]
        let phaseDiff = meanPhaseCon - meanPhaseSub;
        // ... normalization ...
        const sinDiff = Math.sin(phaseDiff);

        // Base deltas
        const baseDeltaSub = K_CON * coupling * sinDiff;
        const baseDeltaCon = -K_SUB * coupling * sinDiff;

        // Distribute to each occurrence, scaled by individual plasticity
        subOccs.forEach(occ => {
            const plasticity = 1 / (1 + Math.log(1 + occ.activationCount));
            const delta = baseDeltaSub * plasticity;
            occ.phasor.theta = ((occ.phasor.theta + delta) % TWO_PI + TWO_PI) % TWO_PI;
        });

        conOccs.forEach(occ => {
            const plasticity = 1 / (1 + Math.log(1 + occ.activationCount));
            const delta = baseDeltaCon * plasticity;
            occ.phasor.theta = ((occ.phasor.theta + delta) % TWO_PI + TWO_PI) % TWO_PI;
        });
    });
}
```

**The Kuramoto coupling equation (per word):**
```
d_theta/dt = K * plasticity_i * weight^2 * sin(theta_bar_other - theta_bar_self)
```

Key design:
- **K_CON = N_sub / N_total**: conscious pulls proportional to subconscious mass
- **K_SUB = N_con / N_total**: subconscious pulls proportional to conscious mass
- **K_CON + K_SUB = 1**: total coupling conserved
- **coupling = weight^2**: rare word in both manifolds = strong coupling; common word = noise
- **sin(phase_diff)**: standard Kuramoto -- pull toward alignment, push away from anti-alignment
- **Opposite signs**: baseDeltaCon = -baseDeltaSub (Newton's third law -- equal and opposite)
- **Per-occurrence plasticity**: high activation = barely moves; low activation = moves readily

### 2.10 Plasticity

```js
const plasticity = 1 / (1 + Math.log(1 + occ.activationCount));
```

Mathematical derivation from the source comments:
- Each activation's marginal contribution = `1/i` (diminishing returns)
- Cumulative evidence = sum(1/i) = harmonic series ~ log(c)
- So plasticity = 1 / (1 + log(1 + c))
- At c=0: plasticity = 1 / (1 + 0) = 1.0 (fully plastic)
- At c=1: plasticity = 1 / (1 + log(2)) = ~0.591
- At c=10: plasticity = 1 / (1 + log(11)) = ~0.294
- At c=100: plasticity = 1 / (1 + log(101)) = ~0.178

"The more you've experienced, the less you bend."

### 2.11 Consolidation Rate

```js
getConsolidationRate(containerActivation) {
    if (containerActivation <= 0) return 0;
    const ratio = this.activationCount / containerActivation;
    if (ratio > THRESHOLD) return 0;  // Anchored, don't consolidate
    return ratio / THRESHOLD;  // Scales 0 -> 1 as we approach threshold
}
```

Linear ramp from 0 to 1 as `c/C` approaches 0.5. Once anchored (c/C > 0.5), consolidation stops.

Legacy solo consolidation: `c / (c + 1)` -- approaches 1 asymptotically.

---

## 3. Memory Architecture

### 3.1 Two-Manifold Model: Conscious vs Subconscious

The system maintains two separate S3 manifolds:

- **Subconscious**: All ingested documents and past conversation episodes. Multiple episodes, each containing multiple neighborhoods.
- **Conscious**: A single episode containing content the LLM has marked with `<salient>` tags. This is the LLM's own judgment about what matters.

Cross-manifold interaction happens ONLY through:
1. Phasor interference (activation matching)
2. Kuramoto phase coupling

Spatial drift (SLERP) happens ONLY within each manifold, never across.

### 3.2 How Queries Surface Memories

The full pipeline in `processQuery()`:

1. **Activate**: Each unique query token activates all matching occurrences across both manifolds. Each match increments its `activationCount`.

2. **Drift**: Activated mobile (non-anchored) occurrences within each manifold SLERP toward each other. Rare words drift more. Anchored words don't move.

3. **Interference**: For each word present in both manifolds, compute cos(phase_difference) between subconscious occurrences and the circular mean of conscious phases.

4. **Surface**: Three categories of results are composed:
   - **Conscious Recall**: Best-scoring neighborhood from conscious manifold (LLM's own prior salient markings)
   - **Subconscious Recall** (top 2): Best-scoring neighborhoods from subconscious manifold
   - **Novel Connection** (1): A neighborhood with low overlap (1-2 words activated), high word weight, high plasticity, and NO conscious match for the bridge word

### 3.3 Surfacing Scoring

Neighborhoods are scored by aggregating activated occurrences:

```js
entry.score += weight * o.activationCount;
```

Score = sum of (IDF weight * activation count) for each activated occurrence in the neighborhood.

### 3.4 Novel Connection Detection

```js
const novelCandidates = [...subNeighborhoods.values()]
    .filter(entry => {
        if (selectedIds.has(entry.neighborhood.id)) return false;
        if (entry.activatedCount > 2) return false;               // Must have low overlap
        const hasConsciousMatch = [...entry.words].some(w => consciousWords.has(w));
        if (hasConsciousMatch) return false;                       // Bridge word must be truly unexpected
        return true;
    })
    .map(entry => ({
        ...entry,
        novelty: entry.maxWordWeight * entry.maxPlasticity * (1 / entry.activatedCount)
    }))
    .sort((a, b) => b.novelty - a.novelty);
```

Novelty score = `maxWordWeight * maxPlasticity * (1 / activatedCount)`. Favors rare, recently-encountered, single-word bridges into unexpected content.

### 3.5 Vivid Recall

A threshold-based mechanism for detecting strong memories:

```js
// Vivid neighborhood: activated ratio > THRESHOLD (50%)
const nRatio = nActivated / neighborhood.count;
if (nRatio > THRESHOLD) {
    vividNeighborhoods.push(neighborhood);
}

// Vivid episode: activated ratio > THRESHOLD AND mass > THRESHOLD
const eRatio = episodeActivated / episode.count;
if (eRatio > THRESHOLD && episode.mass(N) > THRESHOLD) {
    vividEpisodes.push(episode);
}
```

### 3.6 How Responses Strengthen Connections

After the LLM responds:

1. **Response activation**: The response text activates matching occurrences in both manifolds (same as query activation, incrementing counts).
2. **Response drift**: Weight-filtered drift within each manifold.
3. **Response interference + Kuramoto**: Cross-manifold phase coupling on the response's activation.
4. **Salient extraction**: `<salient>` tags in the response are extracted and added to the conscious manifold.

```js
const responseActivation = queryEngine.activate(reply);
// ... weight floor filtering ...
queryEngine.driftAndConsolidate(driftSub);
queryEngine.driftAndConsolidate(driftCon);
const responseInterference = queryEngine.computeInterference(
    responseActivation.subconscious, responseActivation.conscious
);
```

### 3.7 Salient Marking System

```js
function extractSalient(text) {
    const m = text.match(/<salient>(.*?)<\/salient>/gs);
    if (m) m.forEach(s => daeSystem.addToConscious(s.replace(/<\/?salient>/g, '')));
    return m ? m.length : 0;
}
```

The LLM is instructed to wrap important insights in `<salient>` tags. These are:
- Extracted from the response
- Added to the conscious episode as new neighborhoods
- Each occurrence in the new neighborhood is activated once on creation
- Displayed in gold in the UI

---

## 4. Data Structures

### 4.1 Occurrence

The atomic unit. One word instance with position and phase.

```js
{
    word: string,                    // The token (lowercase)
    position: Quaternion,            // Position on S3 manifold [w, x, y, z]
    phasor: DaemonPhasor,           // Phase angle theta in [0, 2*pi)
    activationCount: number,         // Times this occurrence has been activated
    id: string,                      // UUID
    neighborhoodId: string           // Parent neighborhood UUID
}
```

Serialized form (toJSON):
```js
{
    word: "string",
    position: [w, x, y, z],         // Array of 4 floats
    phasor: 1.234,                   // theta as single float
    activationCount: 5,
    id: "uuid",
    neighborhoodId: "uuid",
    // Computed fields (in serialization only):
    containerActivation: 42,
    driftRate: 0.35,
    isAnchored: false
}
```

### 4.2 Neighborhood

A group of co-occurring words from a text chunk.

```js
{
    seed: Quaternion,                // Center point on S3
    occurrences: Occurrence[],       // All word instances in this chunk
    id: string,                      // UUID
    episodeId: string,               // Parent episode UUID
    sourceText: string               // Original text (for display/export)
}
```

Computed properties:
- `count`: number of occurrences
- `totalActivation`: sum of all occurrence activation counts
- `mass(N)`: count / N (fraction of total system)

### 4.3 Episode

A collection of neighborhoods (a document or conversation segment).

```js
{
    name: string,                    // Display name
    isConscious: boolean,            // true for the conscious episode, false for subconscious
    neighborhoods: Neighborhood[],
    id: string,                      // UUID
    timestamp: string                // ISO 8601
}
```

Computed properties:
- `count`: total occurrences across all neighborhoods
- `totalActivation`: sum across all neighborhoods
- `mass(N)`: count / N
- `displayName`: formatted with date/time

### 4.4 DAESystem

Top-level container.

```js
{
    episodes: Episode[],             // Subconscious episodes
    consciousEpisode: Episode,       // Single conscious episode (isConscious=true)
    agentName: string,               // Display name for the agent

    // Indexes (rebuilt lazily):
    _wordNeighborhoodIndex: Map<string, Set<string>>,    // word -> Set<neighborhoodId>
    _wordOccurrenceIndex: Map<string, Occurrence[]>,     // word -> [Occurrence]
    _neighborhoodIndex: Map<string, Neighborhood>,       // neighborhoodId -> Neighborhood
    _neighborhoodEpisodeIndex: Map<string, Episode>      // neighborhoodId -> Episode
}
```

### 4.5 State Export Format

```js
{
    version: '0.7.2',
    timestamp: "ISO 8601 string",
    system: {
        episodes: [...],            // Full serialized episode array
        consciousEpisode: {...},    // Full serialized conscious episode
        N: number,                  // Total occurrence count
        totalActivation: number,
        agentName: string
    },
    conversationHistory: [          // Array of {role, content} pairs
        { role: 'user', content: '...' },
        { role: 'assistant', content: '...' }
    ],
    conversationBuffer: [           // Pending conversation pairs not yet episodized
        ['user msg', 'assistant reply'],
        ...
    ]
}
```

---

## 5. Ingestion Pipeline

### 5.1 Document Ingestion

```js
function ingestText(text, name = null) {
    const episode = new Episode(name);

    // Split into sentence chunks (3 sentences per chunk)
    const sentences = text.split(/(?<=[.!?])\s+/).filter(s => s.trim());
    const chunkSize = 3;

    for (let i = 0; i < sentences.length; i += chunkSize) {
        const chunk = sentences.slice(i, i + chunkSize).join(' ');
        const tokens = tokenize(chunk);
        if (tokens.length > 0) {
            const neighborhood = Neighborhood.fromTokens(tokens, null, chunk);
            episode.addNeighborhood(neighborhood);
        }
    }

    return episode;
}
```

Chunking: 3 sentences per neighborhood. Split on `(?<=[.!?])\s+` (lookbehind for sentence-ending punctuation followed by whitespace).

### 5.2 Conversation Episode Creation

Conversations are buffered and episodized every 5 exchanges:

```js
conversationBuffer.push([q, reply]);
if (conversationBuffer.length >= 5) {
    const ep = new Episode(`Conversation ${daeSystem.episodes.length + 1}`);
    conversationBuffer.forEach(([userMsg, asstMsg]) => {
        const combined = userMsg + ' ' + asstMsg;
        const tokens = tokenize(combined);
        const neighborhood = Neighborhood.fromTokens(tokens, null, combined);
        ep.addNeighborhood(neighborhood);
    });
    daeSystem.addEpisode(ep);
    conversationBuffer = [];
}
```

Each exchange (user message + assistant reply) becomes one neighborhood. Five neighborhoods form an episode.

### 5.3 Conscious Ingestion

```js
addToConscious(text) {
    const tokens = tokenize(text);
    const neighborhood = Neighborhood.fromTokens(tokens, null, text);
    neighborhood.occurrences.forEach(o => o.activate());  // Pre-activate once
    this.consciousEpisode.addNeighborhood(neighborhood);
    this._indexDirty = true;
    return neighborhood;
}
```

Conscious content gets one initial activation (the LLM "noticed" it). This gives it a non-zero activation count from the start.

---

## 6. WebGPU Acceleration

### 6.1 Architecture

The `GPUCompute` class wraps WebGPU initialization and two compute pipelines. The `GPUQueryEngine` extends the base `QueryEngine` and overrides `driftAndConsolidate` to route through GPU or CPU based on batch size.

```
Batch size thresholds:
  < 2 mobile:    skip entirely
  < 50 mobile:   CPU pairwise O(n^2)
  >= 50 + GPU:   GPU centroid O(n) parallel
  >= 200 no GPU: CPU centroid O(n)
```

For interference: the base class's word-aggregated Kuramoto is already O(uniqueWords) + O(n+m), so GPU acceleration is not needed.

### 6.2 SLERP Compute Shader (WGSL)

```wgsl
struct Quat { w: f32, x: f32, y: f32, z: f32 }

@group(0) @binding(0) var<storage, read> src: array<Quat>;
@group(0) @binding(1) var<storage, read> dst: array<Quat>;
@group(0) @binding(2) var<storage, read> factors: array<f32>;
@group(0) @binding(3) var<storage, read_write> out: array<Quat>;

fn quat_dot(a: Quat, b: Quat) -> f32 {
    return a.w * b.w + a.x * b.x + a.y * b.y + a.z * b.z;
}

fn quat_normalize(q: Quat) -> Quat {
    let n = sqrt(q.w*q.w + q.x*q.x + q.y*q.y + q.z*q.z);
    if (n < 1e-10) { return Quat(1.0, 0.0, 0.0, 0.0); }
    return Quat(q.w/n, q.x/n, q.y/n, q.z/n);
}

@compute @workgroup_size(64)
fn main(@builtin(global_invocation_id) gid: vec3u) {
    let i = gid.x;
    if (i >= arrayLength(&src)) { return; }

    let q1 = src[i];
    var q2 = dst[i];
    let t = factors[i];

    var d = quat_dot(q1, q2);
    if (d < 0.0) {
        q2 = Quat(-q2.w, -q2.x, -q2.y, -q2.z);
        d = -d;
    }
    d = clamp(d, -1.0, 1.0);

    if (d > 0.9999) {
        out[i] = quat_normalize(Quat(
            q1.w + t * (q2.w - q1.w),
            q1.x + t * (q2.x - q1.x),
            q1.y + t * (q2.y - q1.y),
            q1.z + t * (q2.z - q1.z)
        ));
        return;
    }

    let theta = acos(d);
    let sin_theta = sin(theta);
    let s0 = sin((1.0 - t) * theta) / sin_theta;
    let s1 = sin(t * theta) / sin_theta;

    out[i] = quat_normalize(Quat(
        s0 * q1.w + s1 * q2.w,
        s0 * q1.x + s1 * q2.x,
        s0 * q1.y + s1 * q2.y,
        s0 * q1.z + s1 * q2.z
    ));
}
```

Workgroup size: 64. Dispatch: `ceil(count / 64)` workgroups.

Data layout: 4 storage buffers (src quaternions, dst quaternions, per-element factors, output quaternions). Quaternions packed as 4x f32 = 16 bytes each.

### 6.3 Interference Compute Shader (WGSL)

```wgsl
@group(0) @binding(0) var<storage, read> phases1: array<f32>;
@group(0) @binding(1) var<storage, read> phases2: array<f32>;
@group(0) @binding(2) var<storage, read_write> out: array<f32>;

const PI: f32 = 3.14159265359;

@compute @workgroup_size(64)
fn main(@builtin(global_invocation_id) gid: vec3u) {
    let i = gid.x;
    if (i >= arrayLength(&phases1)) { return; }

    var diff = abs(phases1[i] - phases2[i]);
    if (diff > PI) { diff = 2.0 * PI - diff; }
    out[i] = cos(diff);
}
```

Simple: phase difference -> cos. 3 storage buffers (phases1, phases2, output).

### 6.4 GPU Buffer Management

```js
_createBuffer(data, usage) {
    const buffer = this.device.createBuffer({
        size: data.byteLength,
        usage: usage,
        mappedAtCreation: true
    });
    new data.constructor(buffer.getMappedRange()).set(data);
    buffer.unmap();
    return buffer;
}
```

Pattern: create buffer mapped, copy data, unmap. For readback, a staging buffer with MAP_READ | COPY_DST is used. All buffers are explicitly destroyed after use.

### 6.5 CPU Fallback Strategy

Both `batchSlerp` and `batchInterference` have threshold checks:

```js
async batchSlerp(occurrences, targets, factors) {
    if (!this.available || occurrences.length < 100) {
        return this._cpuBatchSlerp(occurrences, targets, factors);
    }
    // ... GPU path ...
}

async batchInterference(phases1, phases2) {
    if (!this.available || phases1.length < 100) {
        return this._cpuBatchInterference(phases1, phases2);
    }
    // ... GPU path ...
}
```

Threshold: 100 elements minimum for GPU dispatch. Below that, CPU is faster due to GPU dispatch overhead.

### 6.6 GPU Drift Path

The GPU drift uses the centroid approach:
1. CPU: compute IDF-weighted centroid (O(n) -- cheap)
2. CPU: compute per-occurrence target (centroid minus self, O(n))
3. CPU: compute drift factors
4. GPU: batch SLERP all occurrences toward their targets in parallel
5. CPU: phasor SLERP (cheap, scalar)

Note: `batchSlerp` is called fire-and-forget (`this.gpu.batchSlerp(mobile, targets, factors)` with no `await`). The comment says "GPU slerp is async but drift doesn't need to block." This is a deliberate design choice -- the next operation (interference computation) reads phasors, not positions.

---

## 7. Constants and Tuning Parameters

| Constant | Value | Derivation | Controls |
|----------|-------|-----------|----------|
| `PHI` | 1.618033988749895 | `(1 + sqrt(5)) / 2` | Golden ratio, foundation for other constants |
| `GOLDEN_ANGLE` | 2.399963229728653 rad (137.508 deg) | `2*pi / phi^2` | Phasor spacing between successive words in a neighborhood |
| `NEIGHBORHOOD_RADIUS` | 1.941611400220653 rad (111.246 deg) | `pi / phi` | Angular cap radius for positioning words near seed |
| `THRESHOLD` | 0.5 | `drift = 1 - 2c/C = 0` => `c/C = 0.5` | Anchoring threshold; vivid recall threshold; drift damping factor |
| `M` | 1 | Axiomatic | Total system mass (closed universe normalization) |
| `EPSILON` | 1e-10 | Numerical safety | Zero-guard for normalization, SLERP degeneracy |
| `CONVERSATION_WINDOW_SIZE` | 5 | Tuning | Number of recent exchange pairs sent to LLM |
| Conversation buffer size | 5 | Tuning | Exchanges before creating a new episode |
| Chunk size (ingestion) | 3 sentences | Tuning | Sentences per neighborhood when ingesting documents |
| Weight floor factor | 0.1 | Tuning | Words must appear in < 10% of neighborhoods for drift |
| GPU SLERP threshold | 100 elements | Performance | Minimum batch for GPU dispatch |
| GPU drift threshold | 50 mobile | Performance | Minimum mobile set for GPU centroid path |
| CPU centroid threshold | 200 mobile | Performance | Minimum for CPU centroid (vs pairwise) |
| Workgroup size | 64 | GPU standard | WGSL compute workgroup size |
| SLERP degenerate threshold | 0.9999 (GPU) / `1 - EPSILON` (CPU) | Numerical | Dot product threshold for linear interpolation fallback |
| Claude model | `claude-sonnet-4-20250514` | Provider config | |
| GPT model | `gpt-4o` | Provider config | |
| Grok model | `grok-beta` | Provider config | |
| Gemini model | `gemini-1.5-flash` | Provider config | |
| Max tokens (Claude) | 4096 | Provider config | |
| Sidebar width range | 150-500px | UI | |
| Input height range | 50-300px | UI | |

---

## 8. Index System

The system maintains four lazy-rebuilt indexes for O(1) lookups:

```js
_wordNeighborhoodIndex: Map<string, Set<string>>     // "mycelial" -> Set{"nbhd-uuid-1", "nbhd-uuid-2"}
_wordOccurrenceIndex: Map<string, Occurrence[]>       // "mycelial" -> [Occurrence, Occurrence]
_neighborhoodIndex: Map<string, Neighborhood>         // "nbhd-uuid-1" -> Neighborhood
_neighborhoodEpisodeIndex: Map<string, Episode>       // "nbhd-uuid-1" -> Episode
```

Dirty flag pattern: `_indexDirty` is set true whenever episodes are added or neighborhoods change. `_rebuildIndexes()` is called before any indexed operation and skips if not dirty.

Rebuild scans all episodes (including conscious) and all their neighborhoods and occurrences.

---

## 9. Query-Response Pipeline (Complete Flow)

### 9.1 User sends message

1. Tokenize query, deduplicate tokens
2. Activate all matching occurrences (subconscious + conscious)
3. If query > 50 tokens: apply weight floor to drift input
4. Drift/consolidate within subconscious manifold
5. Drift/consolidate within conscious manifold
6. Compute interference between manifolds (+ Kuramoto coupling)
7. Surface: fragments, vivid neighborhoods, vivid episodes
8. Compose context: conscious recall (1) + subconscious recall (top 2) + novel connection (1)
9. Build conversation window (last 5 exchanges)
10. Send to LLM with system prompt + context + conversation window

### 9.2 LLM responds

11. Extract `<salient>` tags -> add to conscious manifold
12. Activate response text across both manifolds
13. Weight-floor-filtered drift within each manifold
14. Compute interference + Kuramoto coupling on response activation
15. Buffer the exchange (user msg + reply)
16. If buffer reaches 5: create new subconscious episode

### 9.3 Key insight: double activation

Every exchange triggers TWO activation passes:
- Query activation (step 2): user's words activate memories
- Response activation (step 12): LLM's words activate memories

This means each exchange contributes two rounds of drift and coupling. The response activation is what creates the "learning from thinking" effect -- the LLM's own output strengthens the associations it referenced.

---

## 10. LLM Integration

### 10.1 System Prompt Structure

The system prompt tells the LLM about three memory types:
- **CONSCIOUS RECALL**: Previously `<salient>`-marked content
- **SUBCONSCIOUS RECALL**: Past conversations/documents matching current query
- **NOVEL CONNECTION**: Single-word bridge to unexpected content

The LLM is instructed to use `<salient>content</salient>` tags for insights worth remembering.

### 10.2 Multi-Provider Adapter Pattern

```js
const LLMAdapters = {
    claude: {
        endpoint: 'https://api.anthropic.com/v1/messages',
        headers: (apiKey) => ({...}),
        buildBody: (messages, context) => ({...}),
        parseResponse: (data) => data.content[0].text
    },
    gpt: { ... },
    grok: { ... },
    gemini: { ... }
};
```

Each adapter defines: endpoint (string or function for Gemini), headers builder, request body builder, response parser. The Gemini adapter is notably different -- it puts everything in a single user message rather than using system/user/assistant roles.

### 10.3 Conversation Window

```js
const CONVERSATION_WINDOW_SIZE = 5;

function getConversationWindow(history, n) {
    const max = n * 2;  // 5 exchanges = 10 messages
    return history.length <= max ? [...history] : history.slice(-max);
}
```

Last 10 messages (5 user + 5 assistant) are sent to the LLM. Older messages are dropped but their effects persist in the manifold through activation counts and positional drift.

---

## 11. UI/UX Patterns (Brief)

### 11.1 Layout

Single-page app: header (API controls, GPU status, import/export) -> main area (chat + sidebar). Sidebar shows N (total occurrences), Ep (episode count), Con (conscious count), and an episode list.

### 11.2 Resizable Panels

Both the input area height and sidebar width are resizable via drag handles. Mouse event handling with bounds clamping.

### 11.3 Message Display

- User messages: blue-tinted background with left border
- Assistant messages: neutral background, labeled with agent name
- System messages: centered, muted
- Salient content: rendered in gold via regex replacement of `<salient>` tags
- Meta line shows: `con:X sub:Y novel:Z` counts, plus salient extraction count

### 11.4 Import/Export

- Export: full system state as JSON (version, timestamp, system, conversation history, buffer)
- Import: JSON file via drag-and-drop or file picker. Recreates DAESystem from JSON, reinitializes GPUQueryEngine.
- Upload: raw text files (.txt, .md, .html) ingested as new subconscious episodes.

### 11.5 API Key Management

Keys stored in sessionStorage (per-provider). Not persisted across browser sessions. The `anthropic-dangerous-direct-browser-access` header is set for Claude to allow direct browser API calls.

---

## 12. Performance Architecture

### 12.1 Three-Tier Drift Strategy

| Tier | Condition | Algorithm | Complexity |
|------|-----------|-----------|------------|
| Skip | < 2 mobile | No drift | O(1) |
| CPU Pairwise | < 200 mobile (no GPU) or < 50 mobile (with GPU) | Full pairwise SLERP | O(n^2) |
| CPU Centroid | >= 200 mobile, no GPU | Weighted centroid + sequential SLERP | O(n) |
| GPU Centroid | >= 50 mobile, GPU available | Weighted centroid + parallel SLERP | O(n) |

### 12.2 Word-Aggregated Kuramoto Optimization

Before: 500 sub x 50 con occurrences of "the" = 25,000 coupling computations.
After: 1 circular mean per manifold, 1 coupling delta, 550 plasticity-scaled distributions.

### 12.3 Circular Mean Phase Optimization

Instead of O(sub * con) interference pairs, compute one circular mean phase for each word in the conscious manifold, then O(sub) interference values against that mean.

### 12.4 Index-Based Activation

Word activation is O(1) lookup via `_wordOccurrenceIndex` instead of scanning all episodes/neighborhoods/occurrences.

### 12.5 Anchored Pre-Filter

Before entering the O(n^2) or O(n) drift loop, anchored occurrences (drift rate = 0) are filtered out. This can dramatically reduce the working set.

---

## 13. Reimplementation Notes for Rust

### 13.1 Core Types

```
Quaternion: [f32; 4] or struct { w: f32, x: f32, y: f32, z: f32 }
DaemonPhasor: f32 (just theta)
Occurrence: struct with word (String or interned), position, phasor, activation_count, id, neighborhood_id
Neighborhood: struct with seed, occurrences (Vec), id, episode_id, source_text
Episode: struct with name, is_conscious, neighborhoods (Vec), id, timestamp
DAESystem: struct with episodes (Vec), conscious_episode, indexes
```

### 13.2 Critical Algorithms to Port

1. Marsaglia uniform quaternion sampling
2. Box-Muller Gaussian random
3. SLERP (quaternion + phasor variants)
4. Pairwise drift with IDF weighting
5. O(n) centroid drift
6. Circular mean phase computation (atan2 of averaged sin/cos)
7. Kuramoto coupling with plasticity
8. Tokenization (regex-based, preserving apostrophes)
9. Index maintenance (word -> occurrences, word -> neighborhoods, etc.)

### 13.3 GPU Considerations

The WGSL shaders can likely be ported to wgpu (Rust WebGPU). The buffer layout is straightforward:
- SLERP: 4 bindings (src quats, dst quats, factors, output quats)
- Interference: 3 bindings (phases1, phases2, output)
- Workgroup size: 64

### 13.4 Numerical Constants

All constants are derived from phi, pi, and the relationships between them. No magic numbers that need empirical tuning -- except the performance thresholds (50, 100, 200) which are platform-dependent and should be re-benchmarked for Rust.

### 13.5 Serialization

The JSON format is simple and flat. Quaternions are `[f32; 4]`, phasors are single `f32`, UUIDs are strings. Serde should handle this directly.
