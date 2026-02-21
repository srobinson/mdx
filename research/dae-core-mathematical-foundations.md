---
title: "DAE Core Mathematical Foundations"
type: research
tags: [dae, mathematics, s3-hypersphere, quaternions, attention-matters]
summary: "Deep analysis of the original DAE mathematical engine from source JavaScript"
status: active
created: 2026-02-21
updated: 2026-02-21
project: am
confidence: high
---

# DAE Core Mathematical Foundations

A complete mathematical analysis of the Differential Attention Engine (DAE) v0.7.2, derived from the original JavaScript implementation by @smaxforn. Three source variants were examined: `dae-openclaw/dae-core.mjs`, `DAE-moltbook/dae-moltbook/dae-core.mjs` (identical to openclaw), and `dae-stand-alone/dae_v072.html` (standalone with richer inline documentation and minor structural differences).

This document is the mathematical reference for the Rust reimplementation in `attention-matters`.

---

## 1. The S3 Hypersphere

### Why S3?

The DAE models memory as a **closed manifold** -- specifically the 3-sphere S3, the set of all unit quaternions in R4:

```
S3 = { q in R4 : |q| = 1 }
```

This choice is not arbitrary. S3 has several properties that make it uniquely suited to a memory system:

**Property 1: Closedness (finite volume, no boundaries).** S3 has no edges. Every point is equivalent in topology. There is no "center" and no "periphery." This models the DAE's core axiom from the source comments:

> "The system models memory as a closed manifold (S3) with fixed total mass M=1. Adding content increases resolution/density, not volume. Think: finite universe, increasingly fine-grained."

New memories do not expand the space -- they refine the distribution within it.

**Property 2: Antipodal identification.** In quaternion rotation space, `q` and `-q` represent the same rotation. This means the maximum meaningful angular distance between any two points is pi, not 2\*pi. The code handles this explicitly in `slerp`:

```javascript
// dae-core.mjs lines 101-104
if (dot < 0) {
  o = new Quaternion(-other.w, -other.x, -other.y, -other.z);
  dot = -dot;
}
```

And in `geodesicDistance`:

```javascript
// dae-core.mjs lines 91-94
geodesicDistance(other) {
    const d = Math.min(1, Math.max(-1, Math.abs(this.dot(other))));
    return 2 * Math.acos(d);
}
```

The `Math.abs` on the dot product forces the distance to always measure the shorter arc, respecting antipodal equivalence. The maximum distance is `2 * acos(0) = pi`.

**Property 3: Uniform curvature.** S3 is a space of constant positive curvature. There are no flat patches, no singularities. Distances are well-defined everywhere. SLERP (Spherical Linear intERPolation) provides constant-velocity geodesic interpolation -- essential for the drift mechanics.

**Property 4: Parallelizability.** S3 is one of only four parallelizable spheres (S0, S1, S3, S7). This means you can define a smooth, non-vanishing frame field everywhere -- no "hairy ball" problems. Quaternion multiplication provides natural parallel transport.

**Property 5: Group structure.** S3 is isomorphic to SU(2), the special unitary group. It is simultaneously a manifold AND a Lie group. Quaternion multiplication is the group operation. This means rotations on S3 (used for drift and randomNear) are not ad-hoc -- they are the native group action.

### Point Representation

Every point on S3 is a unit quaternion:

```
q = (w, x, y, z)  where  w^2 + x^2 + y^2 + z^2 = 1
```

The code enforces this invariant via normalization after every operation.

---

## 2. Quaternion Operations

### 2.1 Normalization

```javascript
// dae-core.mjs lines 47-51
normalize() {
    const norm = Math.sqrt(this.w*this.w + this.x*this.x + this.y*this.y + this.z*this.z);
    if (norm < EPSILON) return new Quaternion();  // degenerate -> identity
    return new Quaternion(this.w/norm, this.x/norm, this.y/norm, this.z/norm);
}
```

Standard L2 normalization: `q_hat = q / |q|`. The EPSILON guard prevents division by zero, falling back to the identity quaternion (1, 0, 0, 0). In the openclaw variant, normalization returns a new quaternion (immutable style). The standalone variant normalizes in-place via `_normalize()`.

### 2.2 Dot Product

```javascript
// dae-core.mjs lines 53-55
dot(other) {
    return this.w*other.w + this.x*other.x + this.y*other.y + this.z*other.z;
}
```

The standard inner product in R4. For unit quaternions on S3, `dot(p, q) = cos(theta/2)` where theta is the geodesic distance. The sign of the dot product determines which hemisphere `q` is in relative to `p`, which is critical for SLERP's shortest-path selection.

### 2.3 Quaternion Multiplication

Present explicitly in the standalone variant as `multiply()`:

```javascript
// dae_v072.html lines 530-537
multiply(other) {
    return new Quaternion(
        this.w*other.w - this.x*other.x - this.y*other.y - this.z*other.z,
        this.w*other.x + this.x*other.w + this.y*other.z - this.z*other.y,
        this.w*other.y - this.x*other.z + this.y*other.w + this.z*other.x,
        this.w*other.z + this.x*other.y - this.y*other.x + this.z*other.w
    );
}
```

This is the Hamilton product. In the openclaw variant, multiplication is inlined inside `randomNear` (lines 84-88). The formula composes two rotations: `randomNear` constructs a rotation quaternion from a random axis+angle, then left-multiplies it with the center to get a nearby point.

**Mathematical property exploited:** Left-multiplication by a unit quaternion is an isometry of S3. It preserves geodesic distances. This means `randomNear` generates points at exactly the specified angular distance from the center, uniformly distributed on the spherical cap.

### 2.4 SLERP (Spherical Linear Interpolation)

```javascript
// dae-core.mjs lines 96-119
slerp(other, t) {
    if (t <= 0) return this;
    if (t >= 1) return other;
    let dot = this.dot(other);
    let o = other;
    if (dot < 0) {                              // (a) shortest path
        o = new Quaternion(-other.w, -other.x, -other.y, -other.z);
        dot = -dot;
    }
    if (dot > 0.9995) {                          // (b) near-linear fallback
        return new Quaternion(
            this.w + t * (o.w - this.w), this.x + t * (o.x - this.x),
            this.y + t * (o.y - this.y), this.z + t * (o.z - this.z)
        ).normalize();
    }
    const theta = Math.acos(dot);                // (c) full SLERP
    const sinTheta = Math.sin(theta);
    const s0 = Math.sin((1 - t) * theta) / sinTheta;
    const s1 = Math.sin(t * theta) / sinTheta;
    return new Quaternion(
        s0 * this.w + s1 * o.w, s0 * this.x + s1 * o.x,
        s0 * this.y + s1 * o.y, s0 * this.z + s1 * o.z
    ).normalize();
}
```

The SLERP formula:

```
slerp(p, q, t) = p * sin((1-t)*theta) / sin(theta)  +  q * sin(t*theta) / sin(theta)
```

where `theta = acos(|p . q|)`.

Three code paths:

- **(a) Shortest path:** If `dot < 0`, negate `q`. Quaternions `q` and `-q` represent the same rotation, so the negation forces interpolation along the shorter great-circle arc.
- **(b) Near-linear fallback:** When `dot > 0.9995` (theta < ~1.8 degrees), `sin(theta)` is near zero. The code falls back to normalized linear interpolation (NLERP), which is numerically stable and geometrically indistinguishable at this scale.
- **(c) Full SLERP:** The standard formula. Traces a constant-speed path along the great circle connecting `p` and `q`. Parameter `t` in [0,1] controls the fractional distance.

**This is the single most important operation in the DAE.** Drift, phase coupling, and consolidation all operate through SLERP. It is the mechanism by which points move on S3.

### 2.5 Random Quaternion Generation

Two methods exist across variants:

**Openclaw (Hopf-fibration method):**

```javascript
// dae-core.mjs lines 57-69
static random() {
    const s1 = Math.random();
    const s2 = Math.random();
    const t1 = 2 * Math.PI * Math.random();
    const t2 = 2 * Math.PI * Math.random();
    return new Quaternion(
        Math.sqrt(1 - s1) * Math.sin(t1),
        Math.sqrt(1 - s1) * Math.cos(t1),
        Math.sqrt(s1) * Math.sin(t2),
        Math.sqrt(s1) * Math.cos(t2)
    ).normalize();
}
```

This uses the Hopf coordinate parameterization. Two uniform angles `t1, t2` in [0, 2\*pi) and one uniform scalar `s1` in [0, 1) generate points uniformly on S3. Note: `s2` is generated but unused -- this is a vestigial variable (the `sqrtTerm` variable referencing it is also unused). The actual formula uses only `s1`, `t1`, `t2` and produces a uniform distribution without needing `s2`.

**Standalone (Marsaglia's method):**

```javascript
// dae_v072.html lines 488-506
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

Marsaglia's method: rejection-sample two 2D points inside the unit disk, then combine them to project uniformly onto S3. Both methods produce the same distribution; Marsaglia is arguably more numerically robust.

### 2.6 Random Point Near a Seed (randomNear)

```javascript
// dae-core.mjs lines 71-89
static randomNear(center, angularRadius) {
    let ax = gaussRandom(), ay = gaussRandom(), az = gaussRandom();
    const axNorm = Math.sqrt(ax*ax + ay*ay + az*az);
    if (axNorm < EPSILON) return center;
    ax /= axNorm; ay /= axNorm; az /= axNorm;

    const angle = angularRadius * Math.sqrt(Math.random());
    const halfAngle = angle / 2;
    const sinHalf = Math.sin(halfAngle);
    const cosHalf = Math.cos(halfAngle);

    const rotation = new Quaternion(cosHalf, ax*sinHalf, ay*sinHalf, az*sinHalf);
    // Left-multiply rotation * center (Hamilton product inlined)
    return new Quaternion(
        rotation.w*center.w - rotation.x*center.x - rotation.y*center.y - rotation.z*center.z,
        rotation.w*center.x + rotation.x*center.w + rotation.y*center.z - rotation.z*center.y,
        rotation.w*center.y - rotation.x*center.z + rotation.y*center.w + rotation.z*center.x,
        rotation.w*center.z + rotation.x*center.y - rotation.y*center.x + rotation.z*center.w
    ).normalize();
}
```

Algorithm:

1. Generate a random unit axis via 3 Gaussian samples (Box-Muller), normalized. Gaussian components produce a uniform distribution on S2 (the direction sphere).
2. Generate a random angle within the cap: `angle = angularRadius * sqrt(random())`. The `sqrt` ensures **uniform area distribution** on the spherical cap (without sqrt, points would cluster near the pole).
3. Construct a rotation quaternion: `q_rot = (cos(angle/2), axis * sin(angle/2))`.
4. Apply via left-multiplication: `result = q_rot * center`.

This places the new point within geodesic distance `angularRadius` of `center`, uniformly distributed over the spherical cap.

### 2.7 Gaussian Random (Box-Muller Transform)

```javascript
// dae-core.mjs lines 128-132
function gaussRandom() {
  const u1 = Math.random();
  const u2 = Math.random();
  return Math.sqrt(-2 * Math.log(u1)) * Math.cos(2 * Math.PI * u2);
}
```

Standard Box-Muller transform: converts two uniform random variables into a standard normal variable. Used exclusively for generating random rotation axes in `randomNear`.

### 2.8 Geodesic Distance

```javascript
// dae-core.mjs lines 91-94
geodesicDistance(other) {
    const d = Math.min(1, Math.max(-1, Math.abs(this.dot(other))));
    return 2 * Math.acos(d);
}
```

Formula: `d(p, q) = 2 * acos(|p . q|)`

The `abs` handles antipodal identification. The `min/max` clamp prevents `acos` domain errors from floating-point drift. Range: [0, pi].

---

## 3. The Phasor System

### 3.1 DaemonPhasor

Each occurrence carries a phase angle theta in [0, 2\*pi). This is separate from and orthogonal to its S3 position.

```javascript
// dae-core.mjs lines 138-155
class DaemonPhasor {
  constructor(theta = 0) {
    this.theta = theta % (2 * Math.PI);
  }

  static fromIndex(index, baseTheta = 0) {
    return new DaemonPhasor(baseTheta + index * GOLDEN_ANGLE);
  }

  interference(other) {
    return Math.cos(this.theta - other.theta);
  }

  slerp(other, t) {
    let diff = other.theta - this.theta;
    while (diff > Math.PI) diff -= 2 * Math.PI;
    while (diff < -Math.PI) diff += 2 * Math.PI;
    return new DaemonPhasor(this.theta + t * diff);
  }
}
```

**Phase assignment:** When a neighborhood is created from tokens, each token's phasor is assigned via `fromIndex(i)`:

```
theta_i = baseTheta + i * GOLDEN_ANGLE
```

where `GOLDEN_ANGLE = 2*pi / phi^2 ~ 2.3999 rad ~ 137.507 degrees`.

This is the **phyllotaxis pattern** -- the same angle that governs the arrangement of seeds in a sunflower head, scales on a pinecone, and leaves on a stem. It is mathematically proven to maximize the minimum angular distance between successive points on a circle. No two points will be close together until the circle is densely packed.

**Geometric meaning:** Within a neighborhood, each word gets a phase that is maximally separated from all other words' phases. The golden angle ensures this regardless of how many tokens exist.

**Phasor SLERP:** Linear interpolation along the shorter arc of the circle. The `while` loops normalize the difference to [-pi, pi], ensuring shortest-path interpolation.

---

## 4. Drift Mechanics

Drift is the mechanism by which co-activated occurrences move toward each other on S3.

### 4.1 Drift Rate

```javascript
// dae-core.mjs lines 172-177
getDriftRate(containerActivation) {
    if (containerActivation === 0) return 0;
    const ratio = this.activationCount / containerActivation;
    if (ratio > THRESHOLD) return 0;
    return ratio / THRESHOLD;
}
```

Let `c` = occurrence activation count, `C` = container (neighborhood) total activation. The drift rate is:

```
                 0              if C = 0
drift(c, C) =   0              if c/C > 0.5    (anchored)
                 (c/C) / 0.5   if c/C <= 0.5   (mobile)
```

Simplifying: `drift = min(1, 2c/C)` when mobile, `0` when anchored.

**Derivation from the source comments (standalone):**

> drift = 1 - 2c/C, anchors at c = C/2

Setting `drift = 0`: `1 - 2c/C = 0` implies `c = C/2` implies `THRESHOLD = 0.5`.

However, the code uses `ratio / THRESHOLD` which equals `2c/C`, not `1 - 2c/C`. This is the **inverse** of the formula in the comments. The drift rate INCREASES from 0 as activation grows, reaching maximum at the threshold, then dropping to 0 (anchored). This means:

- **Unactivated words (c=0):** drift = 0. They do not move.
- **Lightly activated words (small c/C):** drift is small but positive. They drift slowly.
- **Moderately activated words (c/C approaching 0.5):** drift approaches 1. Maximum mobility.
- **Heavily activated words (c/C > 0.5):** drift = 0. Anchored.

**Interpretation:** Words that have been activated a lot relative to their neighborhood become anchored landmarks. Words that have been activated somewhat are pulled toward co-activated words. Words never activated do not move. This creates a self-organizing structure where frequently co-queried concepts cluster together.

The standalone variant also preserves a legacy solo formula:

```javascript
// dae_v072.html lines 662-665
get driftRate() {
    const c = this.activationCount;
    return c <= 0 ? 0 : (c - 1) / c;
}
```

Legacy formula: `drift = (c-1)/c`. This approaches 1 asymptotically as c grows and uses the occurrence's own count as its reference, not the container. Used only as a backward-compatibility fallback.

### 4.2 Pairwise Drift (O(n^2))

For batches of fewer than 200 mobile occurrences:

```javascript
// dae-core.mjs lines 582-613
_pairwiseDrift(mobile, containerActivations) {
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
}
```

For each pair (occ1, occ2):

1. **Effective drift rate** = `driftRate(c, C) * wordWeight(w)`. IDF weighting means common words ("the") drift negligibly while rare words drift fully.

2. **Meeting point** = `slerp(pos1, pos2, t1/(t1+t2))`. The meeting point is the weighted midpoint on the geodesic between the two positions. The weight `t1/(t1+t2)` means the meeting point is biased toward the occurrence with the higher effective drift rate.

3. **Actual drift**: Each occurrence SLERPs toward the meeting point by `t_i * THRESHOLD` (i.e., `t_i * 0.5`). The THRESHOLD factor dampens the drift to prevent over-correction -- no single drift step moves an occurrence more than halfway.

4. **Phase drift**: Phasors also SLERP toward each other at the same rate.

**Geometric meaning:** Co-activated occurrences converge toward each other on S3, weighted by their relative importance (IDF) and mobility (drift rate). The convergence is mutual but asymmetric -- rarer, more mobile words move more. Over repeated queries, words that frequently co-occur cluster into geometric neighborhoods.

### 4.3 Centroid Drift (O(n))

For batches of 200 or more mobile occurrences:

```javascript
// dae-core.mjs lines 615-648
_centroidDrift(mobile, containerActivations) {
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

    mobile.forEach((occ, i) => {
        const w = weights[i];
        const remWeight = totalWeight - w;
        if (remWeight < EPSILON) return;

        // Leave-one-out centroid
        const tw = (sumW - occ.position.w * w) / remWeight;
        const tx = (sumX - occ.position.x * w) / remWeight;
        const ty = (sumY - occ.position.y * w) / remWeight;
        const tz = (sumZ - occ.position.z * w) / remWeight;

        const n = Math.sqrt(tw*tw + tx*tx + ty*ty + tz*tz);
        if (n < EPSILON) return;

        const target = new Quaternion(tw/n, tx/n, ty/n, tz/n);
        const C = containerActivations.get(occ.neighborhoodId) || 0;
        const factor = occ.getDriftRate(C) * w * 0.5;

        if (factor > 0) {
            occ.position = occ.position.slerp(target, factor);
        }
    });
}
```

Algorithm:

1. Compute the IDF-weighted centroid of all mobile positions in R4: `centroid = sum(w_i * pos_i) / sum(w_i)`.
2. For each occurrence, compute a **leave-one-out centroid** (the centroid of all OTHER occurrences), normalized back onto S3.
3. SLERP toward this centroid by `driftRate * wordWeight * 0.5`.

**Approximation:** This replaces O(n^2) pairwise interactions with O(n) centroid-based attraction. The leave-one-out trick prevents self-attraction. The centroid in R4 projected onto S3 is an approximation of the Frechet mean on S3, but is computationally O(1) per occurrence.

**Note:** Centroid drift only moves positions, not phasors. Phase coupling happens separately through the Kuramoto mechanism.

### 4.4 Neighborhood-Level Drift

```javascript
// dae-core.mjs lines 273-278
driftAll() {
    const C = this.totalActivation;
    this.occurrences.forEach(o => {
        if (o.activationCount > 0) o.driftToward(this.occurrences[0], C);
    });
}
```

A simpler intra-neighborhood drift: all activated occurrences SLERP toward the first occurrence (index 0) in the neighborhood. This consolidates neighborhoods internally. Note: this method exists but is NOT called during query processing -- the query engine uses the more sophisticated pairwise/centroid drift across all activated occurrences.

---

## 5. Interference

Interference determines which subconscious memories constructively reinforce the conscious state (and thus surface) versus which destructively cancel (and are suppressed).

### 5.1 Computing Interference

```javascript
// dae-core.mjs lines 650-693
computeInterference(subconscious, conscious) {
    // Group by word
    const subByWord = new Map();
    const conByWord = new Map();
    // ... grouping code ...

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

        // Per-subOcc interference against conscious mean
        for (const subOcc of subOccs) {
            let diff = Math.abs(subOcc.phasor.theta - meanConPhase);
            if (diff > Math.PI) diff = 2 * Math.PI - diff;
            const interference = Math.cos(diff);
            results.push({ subOcc, conOcc: conOccs[0], interference });
        }

        wordGroups.push({ word, subOccs, conOccs });
    }

    this.applyKuramotoCoupling(wordGroups);
    return results;
}
```

**Only words that appear in BOTH conscious and subconscious manifolds generate interference.** Words exclusive to one manifold bypass interference entirely and are surfaced directly.

For each shared word:

1. **Circular mean** of conscious phasors: Convert to unit vectors on the circle, average, convert back via `atan2`. This correctly handles the circular topology (no wraparound artifacts).

```
mean_theta = atan2( (1/n) * sum(sin(theta_i)),  (1/n) * sum(cos(theta_i)) )
```

2. **Interference value** for each subconscious occurrence:

```
interference = cos(|theta_sub - mean_theta_con|)
```

with the angular difference wrapped to [0, pi].

**Result ranges:**

- `interference = +1`: Perfect constructive interference. Phases aligned. Memory reinforces intent.
- `interference = 0`: Orthogonal phases. Neutral.
- `interference = -1`: Perfect destructive interference. Phases opposed. Memory contradicts intent.

**Geometric meaning:** The same word appearing in a past memory and in the current conscious state can either reinforce or cancel depending on the context in which it was stored (different neighborhoods give different phases). This is the DAE's mechanism for **context-sensitive recall**: the word "bank" in a financial context has a different phase from "bank" in a river context.

---

## 6. Phase Coupling (Kuramoto Model)

### 6.1 The Kuramoto Model

The Kuramoto model describes synchronization of coupled oscillators. In the DAE, the conscious and subconscious manifolds are two populations of oscillators that interact through shared words.

```javascript
// dae-core.mjs lines 695-735
applyKuramotoCoupling(wordGroups) {
    const N_con = this.system.consciousEpisode.count || 1;
    const N_sub = Math.max(1, this.system.N - N_con);
    const N_total = this.system.N || 1;

    const K_CON = N_sub / N_total;    // conscious pulls on subconscious mass
    const K_SUB = N_con / N_total;    // subconscious pulls on conscious mass

    wordGroups.forEach(({ word, subOccs, conOccs }) => {
        const w = this.system.getWordWeight(word);
        const coupling = w * w;        // same word in both -> w_sub === w_con

        // Circular mean phases
        const meanPhaseSub = atan2(mean(sin(theta_sub)), mean(cos(theta_sub)));
        const meanPhaseCon = atan2(mean(sin(theta_con)), mean(cos(theta_con)));

        // Phase difference, wrapped to [-pi, pi]
        let phaseDiff = meanPhaseCon - meanPhaseSub;
        // ... wrapping ...

        const sinDiff = Math.sin(phaseDiff);
        const baseDeltaSub = K_CON * coupling * sinDiff;
        const baseDeltaCon = -K_SUB * coupling * sinDiff;

        // Apply to each occurrence, scaled by individual plasticity
        subOccs.forEach(occ => {
            const plasticity = 1 / (1 + Math.log(1 + occ.activationCount));
            occ.phasor.theta += baseDeltaSub * plasticity;
        });
        conOccs.forEach(occ => {
            const plasticity = 1 / (1 + Math.log(1 + occ.activationCount));
            occ.phasor.theta += baseDeltaCon * plasticity;
        });
    });
}
```

### 6.2 The Coupling Equation

For a shared word `w`, the phase update for each occurrence is:

```
d(theta_sub_i) = K_CON * coupling_w * sin(mean_theta_con - mean_theta_sub) * plasticity_i
d(theta_con_j) = -K_SUB * coupling_w * sin(mean_theta_con - mean_theta_sub) * plasticity_j
```

Where:

- `K_CON = N_sub / N_total` -- strength of conscious-to-subconscious coupling
- `K_SUB = N_con / N_total` -- strength of subconscious-to-conscious coupling
- `coupling_w = (1/|neighborhoods containing w|)^2` -- IDF weight squared
- `plasticity_i = 1 / (1 + ln(1 + activation_count_i))`
- `sin(delta)` provides the Kuramoto restoring force

**Key properties:**

**Conservation:** `K_CON + K_SUB = N_sub/N_total + N_con/N_total = 1`. The total coupling strength is conserved, analogous to `M = 1`.

**Asymmetry by mass:** A large subconscious (many episodes) has `K_CON ~ 1`, meaning conscious memories strongly pull subconscious phases. A large conscious memory has `K_SUB ~ 1`, meaning subconscious memories strongly pull conscious phases. In practice, subconscious typically dominates (many episodes), so `K_CON >> K_SUB` -- the conscious manifold acts as the attractor.

**The sin(delta) coupling:** This is the classic Kuramoto coupling term. When phases are aligned (`delta ~ 0`), `sin(delta) ~ 0` -- no correction needed. When phases differ, the `sin` provides a restoring torque proportional to the misalignment. Maximum torque at `delta = pi/2`.

**Sign convention:** Subconscious phases are pulled TOWARD the conscious mean (positive `sinDiff`). Conscious phases are pulled TOWARD the subconscious mean (negative `sinDiff`). Both populations converge toward mutual synchronization.

**IDF squared coupling:** `coupling = w^2`. Since the same word appears in both manifolds, `w_sub = w_con = w`, and the coupling is their product. Rare words couple strongly; common words barely couple. This prevents "the" from dominating phase dynamics.

### 6.3 Plasticity

```javascript
plasticity = 1 / (1 + Math.log(1 + activationCount));
```

This modulates how much each individual occurrence responds to the Kuramoto coupling:

| activationCount | plasticity |
| --------------- | ---------- |
| 0               | 1.000      |
| 1               | 0.591      |
| 2               | 0.476      |
| 5               | 0.358      |
| 10              | 0.294      |
| 50              | 0.203      |
| 100             | 0.178      |

**Interpretation from source comments:**

> In plain terms: 1/x is how much each new moment teaches you. log(x) is everything you've learned. The more you've experienced, the less you bend.

Fresh occurrences (low activation) are highly plastic -- they move readily in response to coupling. Heavily activated occurrences are crystallized -- they barely move. This provides stability: well-established associations resist perturbation while new associations remain flexible.

**Mathematical foundation:** The marginal contribution of the i-th activation is `1/i`. Cumulative evidence after `c` activations is `sum(1/i, i=1..c) ~ ln(c)` (harmonic series). Plasticity is `1 / (1 + cumulative evidence)`.

---

## 7. Constants

### 7.1 PHI (Golden Ratio)

```javascript
const PHI = (1 + Math.sqrt(5)) / 2; // ~ 1.6180339887
```

The golden ratio. Foundation for both `GOLDEN_ANGLE` and `NEIGHBORHOOD_RADIUS`. Its presence is not decorative -- it provides mathematically optimal spacing (see below).

### 7.2 GOLDEN_ANGLE

```javascript
const GOLDEN_ANGLE = (2 * Math.PI) / (PHI * PHI); // ~ 2.3999 rad ~ 137.507 degrees
```

Derived: `2*pi / phi^2`. Since `phi^2 = phi + 1`, this is equivalently `2*pi / (phi + 1)`.

**Why this value?** The golden angle is the angular complement of the golden ratio's division of the circle. It is the unique angle that, when used to place successive points on a circle, maximizes the minimum separation between any pair of points regardless of how many points are placed. This is the phyllotaxis (leaf arrangement) pattern.

**What breaks if changed?** Using a rational fraction of 2*pi (e.g., 2*pi/3 = 120 degrees) would create periodic patterns -- tokens at indices 0, 3, 6, ... would all land on the same phase. The golden angle is maximally irrational (worst-approximable by rationals), preventing any such periodicity. Changing it would degrade phase separation, potentially causing interference artifacts between unrelated tokens.

### 7.3 NEIGHBORHOOD_RADIUS

```javascript
const NEIGHBORHOOD_RADIUS = Math.PI / PHI; // ~ 1.9416 rad ~ 111.25 degrees
```

The maximum geodesic distance from a neighborhood's seed to any occurrence in it.

**Why pi/phi?** From the source comments:

> In quaternion space, antipodal points (q and -q) represent the same rotation. Maximum meaningful angular distance is pi, not 2pi. pi IS the full range. pi/phi = golden ratio division of the complete space.

This divides the full meaningful angular range (pi) in the golden ratio: `pi = pi/phi + pi/phi^2`. The neighborhood covers `pi/phi ~ 111 degrees` of the `180-degree` full range.

**What breaks if changed?**

- **Too small** (e.g., pi/4 = 45 degrees): Neighborhoods become tiny, occurrences cluster tightly, reducing the manifold's capacity for differentiation.
- **Too large** (approaching pi): Neighborhoods span almost the entire manifold, losing locality. Different neighborhoods would heavily overlap.
- **pi/phi** is the Goldilocks value: large enough for rich internal structure, small enough that distinct neighborhoods occupy distinguishable regions.

### 7.4 THRESHOLD

```javascript
const THRESHOLD = 0.5;
```

Derived from setting drift = 0 in the formula `drift = 1 - 2c/C`:

```
0 = 1 - 2c/C  =>  c/C = 0.5
```

Used for:

1. **Drift anchoring:** An occurrence anchors when its activation exceeds half the container's total activation.
2. **Vivid neighborhood/episode detection:** A neighborhood is "vivid" when more than 50% of its occurrences are surfaced.
3. **Episode vividness:** An episode must have both >50% activation ratio AND mass > 0.5 to be vivid.
4. **Drift damping:** Pairwise drift steps are multiplied by THRESHOLD (0.5), limiting per-step movement.

**What breaks if changed?**

- **Lower** (e.g., 0.3): Words anchor earlier, reducing plasticity. Drift steps are smaller. The system crystallizes faster.
- **Higher** (e.g., 0.8): Words remain mobile longer, the system stays fluid but may fail to stabilize. Vivid recall requires stronger activation.

### 7.5 M (Total Mass)

```javascript
const M = 1;
```

The total mass of the system is always 1, regardless of how many occurrences exist. Individual mass:

```
mass(occurrence) = activationCount / N * M = activationCount / N
mass(neighborhood) = occurrenceCount / N * M = occurrenceCount / N
mass(episode) = occurrenceCount / N * M = occurrenceCount / N
```

This creates a **zero-sum economy**: adding content does not increase total mass, it redistributes it. Each new occurrence dilutes the mass of all existing occurrences. This is the "closed universe" model -- growth adds resolution, not volume.

### 7.6 EPSILON

```javascript
const EPSILON = 1e-10;
```

Numerical stability guard. Used in:

- Quaternion normalization (prevent div-by-zero)
- `randomNear` axis normalization
- SLERP near-linear fallback threshold (standalone uses `1 - EPSILON` instead of `0.9995`)
- Centroid drift (skip when remaining weight is negligible)

---

## 8. Activation and Decay

### 8.1 Activation

Activation is a monotonically increasing counter per occurrence:

```javascript
// dae-core.mjs line 170
activate() { this.activationCount++; }
```

When a query is processed, every occurrence of every query token has its activation incremented. This happens via `DAESystem.activateWord()` which uses the word-occurrence index for O(1) lookup per word.

There is **no decay function** in the DAE. Activation counts only increase. This is a deliberate design choice: the system never forgets. Instead, relative importance shifts through the mass normalization (`mass = c/N`): as N grows, old occurrences' relative mass decreases, even though their absolute activation count remains unchanged.

This is **implicit decay** through dilution, not explicit decay through time-based reduction.

### 8.2 Mass and IDF Weighting

```javascript
// dae-core.mjs lines 428-432
getWordWeight(word) {
    this._rebuildIndexes();
    const nids = this._wordNeighborhoodIndex.get(word.toLowerCase());
    return 1 / (nids ? nids.size : 1);
}
```

Word weight (IDF): `w(word) = 1 / |{neighborhoods containing word}|`

This is a simplified inverse document frequency. Not `log(N/df)` as in classic TF-IDF, but a direct inverse. The effect is more aggressive: a word in 100 neighborhoods gets weight 0.01, not ~0.7 (which log-IDF would give).

**Impact on system behavior:**

- **Drift:** Weight multiplies drift rate. Common words barely move.
- **Kuramoto coupling:** Weight is squared. Common words couple at ~0 strength.
- **Scoring:** Weight multiplied by activation count determines neighborhood ranking.

---

## 9. Context Composition

The composition function (`composeContext`) determines what the LLM actually sees. It runs AFTER activation, drift, and interference.

### 9.1 Neighborhood Scoring

```javascript
// Conscious scoring
entry.score += weight * o.activationCount;

// Subconscious scoring (same formula)
entry.score += weight * o.activationCount;
```

Score formula per neighborhood:

```
score(neighborhood) = sum over activated occurrences: IDF(word_i) * activationCount_i
```

This is essentially a weighted term frequency: each occurrence contributes its IDF weight times how many times it has been activated overall (not just this query). High scores go to neighborhoods with many rare, frequently-activated words.

### 9.2 Selection Pipeline

The composition selects up to 4 neighborhoods in a fixed priority:

**1. CONSCIOUS RECALL (1 neighborhood):** Highest-scoring neighborhood from the conscious episode (user's previously marked `<salient>` content). Scored by `sum(IDF * activationCount)`.

**2. SUBCONSCIOUS RECALL (up to 2 neighborhoods):** Top 2 highest-scoring neighborhoods from subconscious episodes, excluding any already selected. Same scoring formula.

**3. NOVEL CONNECTION (1 neighborhood):** A special selection designed to surface lateral associations:

```javascript
// Filters:
if (entry.activatedCount > 2) return false; // max 2 matching words
const hasConsciousMatch = [...entry.words].some((w) => consciousWords.has(w));
if (hasConsciousMatch) return false; // no overlap with conscious

// Score:
novelty = maxWordWeight * maxPlasticity * (1 / activatedCount);
```

Novel connection requirements:

- At most 2 activated words in the neighborhood (thin connection)
- None of those words appear in conscious memory (truly unexpected bridge)
- Scored by: `max(IDF) * max(plasticity) * (1/activatedCount)`

This formula favors: rare bridge words (high IDF), fresh occurrences (high plasticity), and minimal overlap (1/count penalty). It is specifically designed to surface "one unexpected word" connections -- the kind of lateral association that might reframe a problem.

### 9.3 Surface Computation

Before composition, `computeSurface` determines which occurrences are "surfaced" (eligible for scoring):

```javascript
// 1. Constructively interfering occurrences
interference.forEach(({ subOcc, interference: intVal }) => {
  if (intVal > 0) surfacedOccs.add(subOcc);
});

// 2. Subconscious occurrences with NO conscious match (bypass interference)
activation.subconscious.forEach((occ) => {
  if (!consciousWords.has(occ.word.toLowerCase())) surfacedOccs.add(occ);
});
```

Two paths to surfacing:

1. **Constructive interference** (interference > 0): The word exists in both manifolds and phases align.
2. **No conscious match**: The word is only in subconscious. Since there is no conscious reference to interfere with, it passes through.

Destructively interfering occurrences (interference < 0) are the ONLY ones that get suppressed. This is important: negative interference is an active suppression signal, not a default.

After surfacing, neighborhoods are classified:

- **Vivid neighborhoods**: >50% of occurrences surfaced
- **Vivid episodes**: >50% of occurrences surfaced AND mass > 50%
- **Fragments**: Surfaced occurrences not in vivid neighborhoods/episodes

---

## 10. The Complete Query Pipeline

Putting it all together, a query flows through:

```
Query text
    |
    v
[1] Tokenize -> unique tokens
    |
    v
[2] Activate -> increment activation count for all matching occurrences
    |          -> partition into {subconscious, conscious}
    v
[3] Drift -> co-activated mobile occurrences SLERP toward each other
    |       -> weighted by IDF, damped by THRESHOLD
    |       -> pairwise (n<200) or centroid (n>=200)
    |       -> conscious and subconscious drift SEPARATELY (no cross-manifold spatial drift)
    v
[4] Interference -> for shared words, compute cos(phase_diff)
    |             -> constructive (>0) surfaces, destructive (<=0) suppresses
    v
[5] Kuramoto Coupling -> shared words pull phases toward alignment
    |                  -> K_CON + K_SUB = 1, scaled by IDF^2 and plasticity
    v
[6] Surface -> determine which occurrences are eligible
    |        -> classify into vivid neighborhoods, vivid episodes, fragments
    v
[7] Compose -> score neighborhoods by sum(IDF * activation)
    |        -> select: 1 conscious, 2 subconscious, 1 novel
    v
Context string -> injected into LLM system prompt
```

---

## 11. Variant Differences

Comparing the three source files:

| Feature                  | openclaw/moltbook (dae-core.mjs)             | standalone (dae_v072.html)      |
| ------------------------ | -------------------------------------------- | ------------------------------- |
| Random quaternion        | Hopf-fibration (unused s2 variable)          | Marsaglia's method              |
| Normalization            | Returns new quaternion (immutable)           | Mutates in place                |
| multiply()               | Inlined in randomNear                        | Explicit method                 |
| Legacy driftRate         | Not present                                  | Present as compatibility getter |
| Legacy consolidationRate | Not present                                  | Present as compatibility getter |
| Occurrence.id            | Not stored                                   | Stored (UUID)                   |
| Centroid drift           | Present (n >= 200 fallback)                  | Not present (pairwise only)     |
| Large query optimization | Present (weight floor for >50 token queries) | Present                         |
| composeContext           | Module-level function, takes system param    | Closure over global daeSystem   |
| Console logging          | Removed                                      | Extensive debug logging         |

The core mathematics are identical. The openclaw variant is a cleaned extraction with the centroid drift optimization added. The standalone is the original with richer inline documentation.

---

## 12. Summary of Mathematical Architecture

The DAE is a **dual-manifold oscillator-coupled memory system**:

1. **Geometry**: Unit quaternions on S3, providing a closed, bounded, uniformly-curved space with no singularities.
2. **Topology**: Two separate manifolds (conscious, subconscious) that interact only through shared-word phase coupling -- never through spatial drift.
3. **Dynamics**: Three forces shape the manifold over time:
   - **Drift** (spatial, intra-manifold): Co-activated words converge via SLERP, weighted by IDF.
   - **Kuramoto coupling** (phase, cross-manifold): Shared words' phases synchronize, governed by manifold-mass-proportional coupling constants.
   - **Anchoring** (stabilization): Heavily-activated words crystallize in place, providing stable landmarks.
4. **Selection**: Interference (cos of phase difference) gates which memories surface. Composition ranks by IDF-weighted activation and selects diverse recall types (conscious, subconscious, novel).
5. **Conservation**: Total mass M=1, total coupling K=1. The system is a closed economy where new content redistributes rather than inflates.

The golden ratio phi appears at three structural levels: phase spacing (golden angle), spatial extent (neighborhood radius), and the threshold derivation -- making it a true architectural constant, not a mystical decoration.
