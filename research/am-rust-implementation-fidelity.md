---
title: "AM Rust Implementation Fidelity vs DAE JavaScript"
type: research
tags: [dae, attention-matters, rust, javascript, port-analysis]
summary: "Function-by-function comparison of Rust AM port against original DAE JS engine"
status: active
created: 2026-02-21
updated: 2026-02-21
project: am
confidence: high
---

# AM Rust Implementation Fidelity vs DAE JavaScript v0.7.2

Function-by-function comparison of the Rust `am-core` implementation against the original `dae-core.mjs` JavaScript source. Each section shows both implementations side by side and renders a verdict.

---

## 1. Constants

### JS (dae-core.mjs:31-36)

```javascript
const PHI = (1 + Math.sqrt(5)) / 2;
const GOLDEN_ANGLE = (2 * Math.PI) / (PHI * PHI);
const NEIGHBORHOOD_RADIUS = Math.PI / PHI;
const THRESHOLD = 0.5;
const M = 1;
const EPSILON = 1e-10;
```

### Rust (constants.rs:1-17)

```rust
pub const PHI: f64 = 1.618_033_988_749_895;
pub const GOLDEN_ANGLE: f64 = 2.399_963_229_728_653_3;
pub const NEIGHBORHOOD_RADIUS: f64 = 1.941_613_546_047_687_8;
pub const THRESHOLD: f64 = 0.5;
pub const M: f64 = 1.0;
pub const EPSILON: f64 = 1e-10;
pub const SLERP_THRESHOLD: f64 = 0.9995;
```

### Verdict: IDENTICAL

Pre-computed values match the JS formulas exactly (verified numerically). Rust adds `SLERP_THRESHOLD` as a named constant -- in JS this was an inline magic number `0.9995` inside `Quaternion.slerp()`. Rust also adds GC-related constants (`ACTIVATION_FLOOR`, `DB_SOFT_LIMIT_BYTES`, `DB_GC_TARGET_RATIO`) which have no JS equivalent.

---

## 2. Quaternion Representation

### JS (dae-core.mjs:42-126)

```javascript
class Quaternion {
  constructor(w = 1, x = 0, y = 0, z = 0) {
    this.w = w;
    this.x = x;
    this.y = y;
    this.z = z;
  }
  // mutable class, no normalization in constructor
}
```

### Rust (quaternion.rs:13-19, 32-34)

```rust
#[derive(Clone, Copy, Debug, Serialize, Deserialize)]
pub struct Quaternion { pub w: f64, pub x: f64, pub y: f64, pub z: f64 }

pub fn new(w: f64, x: f64, y: f64, z: f64) -> Self {
    Self { w, x, y, z }.normalize()  // auto-normalizes
}
```

### Verdict: ADAPTED (intentionally improved)

- JS: mutable class, no auto-normalization on construction.
- Rust: `Clone + Copy` value type, auto-normalizes in `new()`.
- Mathematical property: Rust guarantees unit quaternion invariant at construction; JS could hold non-unit quaternions until `normalize()` is called explicitly. No mathematical loss -- strictly safer.

---

## 3. Quaternion Operations

### 3a. Normalize

**JS:**

```javascript
normalize() {
    const norm = Math.sqrt(this.w*this.w + this.x*this.x + this.y*this.y + this.z*this.z);
    if (norm < EPSILON) return new Quaternion();  // returns (1,0,0,0)
    return new Quaternion(this.w/norm, this.x/norm, this.y/norm, this.z/norm);
}
```

**Rust:**

```rust
pub fn normalize(self) -> Self {
    let norm = (self.w * self.w + self.x * self.x + self.y * self.y + self.z * self.z).sqrt();
    if norm < EPSILON { return Self::identity(); }
    Self { w: self.w / norm, x: self.x / norm, y: self.y / norm, z: self.z / norm }
}
```

**Verdict: IDENTICAL**

### 3b. Dot Product

**JS:** `return this.w*other.w + this.x*other.x + this.y*other.y + this.z*other.z;`

**Rust:** `self.w * other.w + self.x * other.x + self.y * other.y + self.z * other.z`

**Verdict: IDENTICAL**

### 3c. Geodesic Distance

**JS:**

```javascript
geodesicDistance(other) {
    const d = Math.min(1, Math.max(-1, Math.abs(this.dot(other))));
    return 2 * Math.acos(d);
}
```

**Rust:**

```rust
pub fn angular_distance(self, other: Self) -> f64 {
    let d = self.dot(other).abs().clamp(-1.0, 1.0);
    2.0 * d.acos()
}
```

**Verdict: IDENTICAL** (different method name, same formula)

### 3d. SLERP

**JS (dae-core.mjs:96-119):**

```javascript
slerp(other, t) {
    if (t <= 0) return this;
    if (t >= 1) return other;
    let dot = this.dot(other);
    let o = other;
    if (dot < 0) { o = new Quaternion(-other.w, -other.x, -other.y, -other.z); dot = -dot; }
    if (dot > 0.9995) {
        return new Quaternion(
            this.w + t * (o.w - this.w), this.x + t * (o.x - this.x),
            this.y + t * (o.y - this.y), this.z + t * (o.z - this.z)
        ).normalize();
    }
    const theta = Math.acos(dot);
    const sinTheta = Math.sin(theta);
    const s0 = Math.sin((1 - t) * theta) / sinTheta;
    const s1 = Math.sin(t * theta) / sinTheta;
    return new Quaternion(
        s0 * this.w + s1 * o.w, s0 * this.x + s1 * o.x,
        s0 * this.y + s1 * o.y, s0 * this.z + s1 * o.z
    ).normalize();
}
```

**Rust (quaternion.rs:73-121):**

```rust
pub fn slerp(self, other: Self, t: f64) -> Self {
    if t <= 0.0 { return self; }
    if t >= 1.0 { return other; }
    let mut dot = self.dot(other);
    let o;
    if dot < 0.0 { o = Self { w: -other.w, x: -other.x, y: -other.y, z: -other.z }; dot = -dot; }
    else { o = other; }
    if dot > SLERP_THRESHOLD {
        return Self { w: self.w + t * (o.w - self.w), ... }.normalize();
    }
    let theta = dot.clamp(-1.0, 1.0).acos();
    let sin_theta = theta.sin();
    let s0 = ((1.0 - t) * theta).sin() / sin_theta;
    let s1 = (t * theta).sin() / sin_theta;
    Self { w: s0 * self.w + s1 * o.w, ... }.normalize()
}
```

**Verdict: IDENTICAL** -- Rust adds a `.clamp(-1.0, 1.0)` before `acos()` for numerical safety. This prevents NaN from floating-point rounding. Mathematically equivalent, numerically more robust.

### 3e. Random (Shoemake's method)

**JS (dae-core.mjs:57-69):**

```javascript
static random() {
    const s1 = Math.random();
    const s2 = Math.random();
    const t1 = 2 * Math.PI * Math.random();
    const t2 = 2 * Math.PI * Math.random();
    const sqrtTerm = Math.sqrt((1 - s1) / s2);  // UNUSED variable
    return new Quaternion(
        Math.sqrt(1 - s1) * Math.sin(t1),
        Math.sqrt(1 - s1) * Math.cos(t1),
        Math.sqrt(s1) * Math.sin(t2),
        Math.sqrt(s1) * Math.cos(t2)
    ).normalize();
}
```

**Rust (quaternion.rs:124-139):**

```rust
pub fn random(rng: &mut impl Rng) -> Self {
    let s1: f64 = rng.random();
    let t1 = std::f64::consts::TAU * rng.random::<f64>();
    let t2 = std::f64::consts::TAU * rng.random::<f64>();
    let r1 = (1.0 - s1).sqrt();
    let r2 = s1.sqrt();
    Self { w: r1 * t1.sin(), x: r1 * t1.cos(), y: r2 * t2.sin(), z: r2 * t2.cos() }.normalize()
}
```

**Verdict: IDENTICAL** (with a JS bug cleaned up)

The JS version generates an extra random `s2` and computes `sqrtTerm = Math.sqrt((1 - s1) / s2)` which is never used. This is dead code -- likely a leftover from an earlier formula. The Rust version correctly eliminates it. The actual quaternion formula is the same standard Shoemake method.

### 3f. Random Near

**JS (dae-core.mjs:71-89):**

```javascript
static randomNear(center, angularRadius) {
    let ax = gaussRandom(), ay = gaussRandom(), az = gaussRandom();
    const axNorm = Math.sqrt(ax*ax + ay*ay + az*az);
    if (axNorm < EPSILON) return center;
    ax /= axNorm; ay /= axNorm; az /= axNorm;
    const angle = angularRadius * Math.sqrt(Math.random());
    const halfAngle = angle / 2;
    // rotation quaternion, then Hamilton product inline
    const rotation = new Quaternion(cosHalf, ax*sinHalf, ay*sinHalf, az*sinHalf);
    return new Quaternion(
        rotation.w*center.w - rotation.x*center.x - rotation.y*center.y - rotation.z*center.z,
        rotation.w*center.x + rotation.x*center.w + rotation.y*center.z - rotation.z*center.y,
        rotation.w*center.y - rotation.x*center.z + rotation.y*center.w + rotation.z*center.x,
        rotation.w*center.z + rotation.x*center.y - rotation.y*center.x + rotation.z*center.w
    ).normalize();
}
```

**Rust (quaternion.rs:144-175):**

```rust
pub fn random_near(center: Self, angular_radius: f64, rng: &mut impl Rng) -> Self {
    let ax = gauss_random(rng); let ay = gauss_random(rng); let az = gauss_random(rng);
    let ax_norm = (ax*ax + ay*ay + az*az).sqrt();
    if ax_norm < EPSILON { return center; }
    let ax = ax / ax_norm; let ay = ay / ax_norm; let az = az / ax_norm;
    let angle = angular_radius * rng.random::<f64>().sqrt();
    let half_angle = angle / 2.0;
    let rotation = Self { w: cos_half, x: ax*sin_half, y: ay*sin_half, z: az*sin_half };
    (rotation * center).normalize()
}
```

**Verdict: IDENTICAL** -- The inline Hamilton product in JS is replaced by the `Mul` trait impl (`rotation * center`) in Rust. The Hamilton product formula is identical (verified against quaternion.rs lines 205-213). Rust uses explicit RNG injection instead of `Math.random()`.

### 3g. Hamilton Product

**JS:** Inline in `randomNear` only; no standalone Hamilton product.

**Rust:** Standalone `Mul` trait implementation (quaternion.rs:202-213).

```rust
impl Mul for Quaternion {
    type Output = Self;
    fn mul(self, rhs: Self) -> Self {
        Self {
            w: self.w*rhs.w - self.x*rhs.x - self.y*rhs.y - self.z*rhs.z,
            x: self.w*rhs.x + self.x*rhs.w + self.y*rhs.z - self.z*rhs.y,
            y: self.w*rhs.y - self.x*rhs.z + self.y*rhs.w + self.z*rhs.x,
            z: self.w*rhs.z + self.x*rhs.y - self.y*rhs.x + self.z*rhs.w,
        }
    }
}
```

**Verdict: ADAPTED** -- Rust factors out what JS inlines. Same math. Also adds `Neg` trait for antipodal negation.

---

## 4. Gauss Random (Box-Muller)

**JS (dae-core.mjs:128-132):**

```javascript
function gaussRandom() {
  const u1 = Math.random();
  const u2 = Math.random();
  return Math.sqrt(-2 * Math.log(u1)) * Math.cos(2 * Math.PI * u2);
}
```

**Rust (quaternion.rs:216-221):**

```rust
fn gauss_random(rng: &mut impl Rng) -> f64 {
    let u1: f64 = rng.random::<f64>().max(f64::MIN_POSITIVE);
    let u2: f64 = rng.random();
    (-2.0 * u1.ln()).sqrt() * (std::f64::consts::TAU * u2).cos()
}
```

**Verdict: ADAPTED (safety improvement)**

Rust clamps `u1` away from zero with `.max(f64::MIN_POSITIVE)` to avoid `ln(0) = -inf`. JS can technically produce `-Infinity` if `Math.random()` returns exactly 0 (probability ~0 but not impossible). No mathematical property change.

---

## 5. DaemonPhasor

### JS (dae-core.mjs:138-155)

```javascript
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

### Rust (phasor.rs:8-44)

```rust
pub struct DaemonPhasor { pub theta: f64 }

impl DaemonPhasor {
    pub fn new(theta: f64) -> Self {
        Self { theta: theta.rem_euclid(std::f64::consts::TAU) }
    }
    pub fn from_index(index: usize, base_theta: f64) -> Self {
        Self::new(base_theta + index as f64 * GOLDEN_ANGLE)
    }
    pub fn interference(self, other: Self) -> f64 {
        (self.theta - other.theta).cos()
    }
    pub fn slerp(self, other: Self, t: f64) -> Self {
        let mut diff = other.theta - self.theta;
        while diff > PI { diff -= TAU; }
        while diff < -PI { diff += TAU; }
        Self::new(self.theta + t * diff)
    }
}
```

### Verdict: ADAPTED (normalization improvement)

**Key difference:** JS uses `theta % (2 * Math.PI)` which preserves negative values (JS `%` is remainder, not modulo). Rust uses `.rem_euclid(TAU)` which always produces `[0, TAU)`. This means the Rust phasor always normalizes to a positive range, while JS can store negative theta values.

**Mathematical impact:** None for interference (cosine is even in the difference) and slerp (wrapping handles it). But Rust prevents phase accumulation drift from producing arbitrarily large theta values. Strictly better.

---

## 6. Occurrence

### JS (dae-core.mjs:161-221)

```javascript
class Occurrence {
    constructor(word, position, phasor, neighborhoodId = null) {
        this.word = word;
        this.position = position;
        this.phasor = phasor;
        this.activationCount = 0;
        this.neighborhoodId = neighborhoodId;
    }
    activate() { this.activationCount++; }
    getDriftRate(containerActivation) {
        if (containerActivation === 0) return 0;
        const ratio = this.activationCount / containerActivation;
        if (ratio > THRESHOLD) return 0;
        return ratio / THRESHOLD;
    }
    get plasticity() { return 1 / (1 + Math.log(1 + c)); }
    isAnchored(containerActivation) {
        return (this.activationCount / containerActivation) > THRESHOLD;
    }
    mass(N) { return N > 0 ? (c / N) * M : 0; }
    driftToward(target, containerActivation) { ... }
}
```

### Rust (occurrence.rs:13-79)

```rust
pub struct Occurrence {
    pub word: String,
    pub position: Quaternion,
    pub phasor: DaemonPhasor,
    pub activation_count: u32,
    pub id: Uuid,            // NEW: per-occurrence UUID
    pub neighborhood_id: Uuid,
}
// drift_rate, plasticity, is_anchored, mass: identical formulas
```

### Verdict: ADAPTED

**Preserved exactly:**

- `activate()`: `self.activation_count += 1`
- `drift_rate()`: `ratio / THRESHOLD`, returns 0 when `container_activation == 0` or `ratio > THRESHOLD`
- `plasticity()`: `1.0 / (1.0 + (1.0 + c as f64).ln())`
- `is_anchored()`: `ratio > THRESHOLD`
- `mass()`: `(c / N) * M`

**Differences:**

- Rust adds `id: Uuid` per occurrence (JS has no per-occurrence UUID).
- Rust uses `u32` for `activation_count` (JS uses Number/f64 via increment). No practical difference for counts < 2^32.
- Rust's `is_anchored()` adds a guard: returns `true` when `container_activation == 0` (JS would divide by zero, returning `NaN > THRESHOLD` which is `false`). This is a **bug fix**.

**JS `driftToward()` method is MISSING from Rust `Occurrence`:**

```javascript
driftToward(target, containerActivation) {
    const t = this.getDriftRate(containerActivation);
    if (t <= 0) return;
    this.position = this.position.slerp(target.position, t);
    this.phasor = this.phasor.slerp(target.phasor, t);
}
```

This method existed in JS for the `Neighborhood.driftAll()` function (intra-neighborhood drift). In Rust, drift is handled entirely in `QueryEngine` via `pairwise_drift` and `centroid_drift`. The `driftToward` method on `Occurrence` was not ported because it was only used by `Neighborhood.driftAll()`, which itself was never called in the JS query pipeline (see Section 8).

---

## 7. Neighborhood

### JS (dae-core.mjs:227-299)

```javascript
class Neighborhood {
    constructor(seed, id = null, sourceText = '') { ... }
    static fromTokens(tokens, seed = null, sourceText = '') {
        tokens.forEach((token, i) => {
            const position = Quaternion.randomNear(neighborhood.seed, NEIGHBORHOOD_RADIUS);
            const phasor = DaemonPhasor.fromIndex(i);
            ...
        });
    }
    get count() { return this.occurrences.length; }
    get totalActivation() { return this.occurrences.reduce((sum, o) => sum + o.activationCount, 0); }
    mass(N) { return N > 0 ? (this.count / N) * M : 0; }
    activateWord(word) { ... }
    isVivid(episodeCount) { return this.count > episodeCount * THRESHOLD; }
    driftAll() {
        const C = this.totalActivation;
        this.occurrences.forEach(o => {
            if (o.activationCount > 0) o.driftToward(this.occurrences[0], C);
        });
    }
}
```

### Rust (neighborhood.rs:48-125)

```rust
pub struct Neighborhood {
    pub id: Uuid,
    pub seed: Quaternion,
    pub occurrences: Vec<Occurrence>,
    pub source_text: String,
    pub neighborhood_type: NeighborhoodType,  // NEW
}
// from_tokens, count, total_activation, mass, is_vivid, activate_word: identical
```

### Verdict: ADAPTED

**Preserved exactly:**

- `from_tokens`: random position within `NEIGHBORHOOD_RADIUS`, golden-angle phasor spacing. Identical logic.
- `count`, `total_activation`, `mass`, `is_vivid`, `activate_word`: identical formulas.

**Differences:**

- Rust adds `NeighborhoodType` enum: `Memory | Decision | Preference | Insight`. JS has no concept of typed neighborhoods.
- Rust's `from_tokens` takes `&mut impl Rng` (deterministic testing). JS uses `Math.random()`.
- JS `driftAll()` is **NOT PORTED** to Rust. This method drifted all activated occurrences toward `occurrences[0]` (the first word). This was never called in the JS `QueryEngine.processQuery()` pipeline -- it appears to be dead code or a vestigial API. **No mathematical loss.**

---

## 8. Drift Function

### JS Pairwise Drift (dae-core.mjs:582-613)

```javascript
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

### Rust Pairwise Drift (query.rs:151-226)

```rust
fn pairwise_drift(system: &mut DAESystem, mobile: &[OccurrenceRef], ...) {
    // Snapshot current state to avoid read-after-write issues
    let states: Vec<(Quaternion, DaemonPhasor, f64, String)> = ...;
    let weights: Vec<f64> = ...;
    // Collect all deltas
    for i in 0..n {
        for j in (i + 1)..n {
            let t1 = dr1 * weights[i];
            let t2 = dr2 * weights[j];
            // ... same meeting point formula ...
            // Instead of mutating in-place, accumulate deltas
            position_deltas[i].push((meeting, factor));
            phasor_deltas[i].push((*phasor2, factor));
        }
    }
    // Apply all deltas at once
    for (idx, r) in mobile.iter().enumerate() {
        let (mut pos, mut phasor, _, _) = states[idx];
        for (target, factor) in &position_deltas[idx] { pos = pos.slerp(*target, *factor); }
        for (target, factor) in &phasor_deltas[idx] { phasor = phasor.slerp(*target, *factor); }
        let occ = system.get_occurrence_mut(*r);
        occ.position = pos; occ.phasor = phasor;
    }
}
```

### Verdict: DIVERGED (intentional -- snapshot semantics)

**Formulas preserved:**

- `t = drift_rate * IDF_weight` -- identical.
- Meeting point: `weight = t1 / (t1 + t2); meeting = pos1.slerp(pos2, weight)` -- identical.
- Drift factor: `t * THRESHOLD` -- identical.
- Both position and phasor SLERP -- preserved.

**Semantic divergence:**
JS mutates positions **in-place during iteration**, meaning later pairs see the already-drifted positions of earlier pairs. The order of iteration affects the final result.

Rust **snapshots all positions first**, computes all deltas against the original state, then applies them. This eliminates iteration-order dependence and prevents compounding drift within a single pass.

**Mathematical impact:** Slightly different final positions after drift. The Rust behavior is more principled (commutative across pairs) but produces different numerical results for the same input. **Intentional improvement.** The accumulated SLERP in the delta application (applying multiple SLERP operations sequentially from the snapshot) is a reasonable approximation.

### JS Centroid Drift (dae-core.mjs:615-648)

```javascript
_centroidDrift(mobile, containerActivations) {
    // IDF-weighted centroid in R4, leave-one-out
    // factor = occ.getDriftRate(C) * w * 0.5
    // occ.position = occ.position.slerp(target, factor);
}
```

### Rust Centroid Drift (query.rs:230-294)

```rust
fn centroid_drift(system: &mut DAESystem, mobile: &[OccurrenceRef], ...) {
    // Same IDF-weighted centroid, leave-one-out, project to S3
    // factor = dr * w * 0.5
    // occ.position = occ.position.slerp(target, factor);
}
```

### Verdict: IDENTICAL

Same algorithm: IDF-weighted sum in R^4, leave-one-out centroid, project to S^3 via normalization, SLERP with factor = drift_rate _ IDF _ 0.5. Neither phasor-drifts in centroid mode (JS and Rust both skip it).

### Drift Threshold (pairwise vs centroid selection)

**JS:** `mobile.length >= 200` triggers centroid.
**Rust:** `mobile.len() >= 200` triggers centroid.

**Verdict: IDENTICAL**

---

## 9. Interference Calculation

### JS (dae-core.mjs:650-693)

```javascript
computeInterference(subconscious, conscious) {
    // Group by word
    // Circular mean phase of conscious occurrences
    let sinSum = 0, cosSum = 0;
    conOccs.forEach(occ => {
        sinSum += Math.sin(occ.phasor.theta);
        cosSum += Math.cos(occ.phasor.theta);
    });
    const meanConPhase = Math.atan2(sinSum / conOccs.length, cosSum / conOccs.length);
    // Per-subOcc interference against conscious mean
    let diff = Math.abs(subOcc.phasor.theta - meanConPhase);
    if (diff > Math.PI) diff = 2 * Math.PI - diff;
    const interference = Math.cos(diff);
}
```

### Rust (query.rs:298-360)

```rust
pub fn compute_interference(system: &DAESystem, subconscious: &[OccurrenceRef], conscious: &[OccurrenceRef])
    -> (Vec<InterferenceResult>, Vec<WordGroup>) {
    // Same: group by word, circular mean phase, cos(wrapped_diff)
    let mean_con_phase = (sin_sum / count).atan2(cos_sum / count);
    let mut diff = (sub_theta - mean_con_phase).abs();
    if diff > PI { diff = TAU - diff; }
    let interference = diff.cos();
}
```

### Verdict: IDENTICAL

Same algorithm: circular mean of conscious phases via atan2(mean_sin, mean_cos), wrapped angular difference, cosine interference. The only surface difference is that Rust returns both the interference results and word groups as a tuple; JS stores word groups as a side effect for Kuramoto.

---

## 10. Phase Coupling / Kuramoto Model

### JS (dae-core.mjs:695-735)

```javascript
applyKuramotoCoupling(wordGroups) {
    const N_con = this.system.consciousEpisode.count || 1;
    const N_sub = Math.max(1, this.system.N - N_con);
    const N_total = this.system.N || 1;
    const K_CON = N_sub / N_total;
    const K_SUB = N_con / N_total;

    wordGroups.forEach(({ word, subOccs, conOccs }) => {
        const w = this.system.getWordWeight(word);
        const coupling = w * w;
        // Circular mean phases for both manifolds
        let phaseDiff = meanPhaseCon - meanPhaseSub;
        // wrap to [-pi, pi]
        const sinDiff = Math.sin(phaseDiff);
        const baseDeltaSub = K_CON * coupling * sinDiff;
        const baseDeltaCon = -K_SUB * coupling * sinDiff;
        // Apply with plasticity
        subOccs.forEach(occ => {
            const plasticity = 1 / (1 + Math.log(1 + occ.activationCount));
            occ.phasor.theta = ((occ.phasor.theta + baseDeltaSub * plasticity) % TWO_PI + TWO_PI) % TWO_PI;
        });
        conOccs.forEach(occ => {
            const plasticity = 1 / (1 + Math.log(1 + occ.activationCount));
            occ.phasor.theta = ((occ.phasor.theta + baseDeltaCon * plasticity) % TWO_PI + TWO_PI) % TWO_PI;
        });
    });
}
```

### Rust (query.rs:363-430)

```rust
pub fn apply_kuramoto_coupling(system: &mut DAESystem, word_groups: &[WordGroup]) {
    let n_con = system.conscious_episode.count().max(1);
    let n_total = system.n().max(1);
    let n_sub = n_total.saturating_sub(n_con).max(1);
    let k_con = n_sub as f64 / n_total as f64;
    let k_sub = n_con as f64 / n_total as f64;

    for group in word_groups {
        let w = system.get_word_weight(&group.word);
        let coupling = w * w;
        // Circular mean phases -- identical
        // Phase diff wrapping -- identical
        let base_delta_sub = k_con * coupling * sin_diff;
        let base_delta_con = -k_sub * coupling * sin_diff;
        // Apply with plasticity
        for r in &group.sub_refs {
            let occ = system.get_occurrence_mut(*r);
            let plasticity = occ.plasticity();
            occ.phasor = DaemonPhasor::new(occ.phasor.theta + base_delta_sub * plasticity);
        }
    }
}
```

### Verdict: IDENTICAL

All formulas preserved:

- `K_CON = N_sub / N_total`, `K_SUB = N_con / N_total` (guaranteeing K_CON + K_SUB = 1)
- `coupling = IDF_weight^2`
- `baseDelta = K * coupling * sin(phaseDiff)`
- Plasticity modulation: `1 / (1 + ln(1 + activationCount))`
- Phase normalization: JS uses `((theta + delta) % TAU + TAU) % TAU`; Rust uses `DaemonPhasor::new()` which calls `.rem_euclid(TAU)`. Mathematically equivalent.

---

## 11. Activation and Decay Mechanics

### JS (dae-core.mjs:449-468)

```javascript
activateWord(word) {
    const occs = this._wordOccurrenceIndex.get(wordLower);
    for (const occ of occs) {
        occ.activate();
        if (ep.isConscious) conscious.push(occ);
        else subconscious.push(occ);
    }
    return { subconscious, conscious };
}
```

### Rust (system.rs:177-210)

```rust
pub fn activate_word(&mut self, word: &str) -> ActivationResult {
    self.ensure_indexes();
    let refs = self.word_occurrence_index.get(&word_lower).cloned();
    for occ_ref in refs {
        let occ = self.get_occurrence_mut(occ_ref);
        occ.activate();
        if occ_ref.is_conscious() { conscious.push(occ_ref); }
        else { subconscious.push(occ_ref); }
    }
    ActivationResult { subconscious, conscious }
}
```

### Verdict: IDENTICAL

Same semantics: iterate index, increment activation, partition into conscious/subconscious.

---

## 12. IDF Weighting

### JS (dae-core.mjs:428-432)

```javascript
getWordWeight(word) {
    const nids = this._wordNeighborhoodIndex.get(word.toLowerCase());
    return 1 / (nids ? nids.size : 1);
}
```

### Rust (system.rs:167-174)

```rust
pub fn get_word_weight(&mut self, word: &str) -> f64 {
    self.ensure_indexes();
    match self.word_neighborhood_index.get(&word_lower) {
        Some(neighborhoods) if !neighborhoods.is_empty() => 1.0 / neighborhoods.len() as f64,
        _ => 1.0,
    }
}
```

### Verdict: IDENTICAL

`1 / (number of neighborhoods containing word)`. Default weight = 1.0 for unknown words.

---

## 13. Surface Computation

### JS (dae-core.mjs:737-795)

```javascript
computeSurface(activation, interference) {
    // Step 1: Positive interference → surface
    interference.forEach(({ subOcc, interference: intVal }) => {
        if (intVal > 0) surfacedOccs.add(subOcc);
    });
    // Step 2: Novel words (subconscious only, not in conscious vocabulary)
    activation.subconscious.forEach(occ => {
        if (!consciousWords.has(occ.word.toLowerCase())) surfacedOccs.add(occ);
    });
    // Step 3: Vivid neighborhoods (>50% activated)
    // Step 4: Vivid episodes (>50% activated AND >50% mass)
    // Step 5: Fragments (surfaced but not in vivid structures)
}
```

### Rust (surface.rs:24-108)

```rust
pub fn compute_surface(system: &DAESystem, query_result: &QueryResult) -> SurfaceResult {
    // Step 1: Positive interference → surface -- identical
    // Step 2: Novel words -- identical
    // Step 3: Vivid neighborhoods -- identical threshold (> THRESHOLD)
    // Step 4: Vivid episodes -- identical (e_ratio > THRESHOLD && mass > THRESHOLD)
    // Step 5: Fragments -- identical exclusion logic
}
```

### Verdict: IDENTICAL

All five steps are preserved with the same thresholds and logic. The Rust version returns richer output (`SurfaceResult` with `neighborhood_surfaced_counts` HashMap), but the core algorithm is unchanged.

---

## 14. Context Composition and Scoring

### JS (dae-core.mjs:826-934)

```javascript
function composeContext(system, surface, activation, interference) {
  // Score conscious neighborhoods: weight * activationCount
  // Score subconscious neighborhoods: weight * activationCount
  // Conscious: top 1
  // Subconscious: top 2 (excluding selected)
  // Novel: top 1, filtered by:
  //   - activatedCount <= 2
  //   - no words overlap with conscious
  //   - scored by maxWordWeight * maxPlasticity * (1/activatedCount)
}
```

### Rust (compose.rs:107-186, 685-829)

```rust
fn rank_candidates(system: &mut DAESystem, query_result: &QueryResult, project_id: Option<&str>)
    -> Vec<RankedCandidate> {
    // Score conscious: weight * activation_count * affinity
    // Score subconscious: weight * activation_count * affinity
    // Novel: activated_count <= 2, no conscious overlap
    //   scored by max_word_weight * max_plasticity / activated_count
}
// compose_context: conscious top 1, subconscious top 2, novel top 1
```

### Verdict: DIVERGED (intentional enhancements)

**Preserved from JS:**

- Scoring formula base: `IDF_weight * activation_count`
- Selection limits: 1 conscious, 2 subconscious, 1 novel
- Novel filtering: `activated_count <= 2`, no conscious word overlap
- Novel scoring: `max_word_weight * max_plasticity / activated_count` (JS uses `* (1/activatedCount)`, equivalent)
- Output format: `CONSCIOUS RECALL:`, `SUBCONSCIOUS RECALL N:`, `NOVEL CONNECTION:`

**New in Rust (not in JS):**

1. **Project affinity scoring**: `score *= affinity` where affinity is 2.0 (same project), 1.0 (no project), 0.3 (different project). JS has no project scoping.
2. **Recency decay**: `score *= 1.0 / (1.0 + days_old * 0.01)`. JS has no time-based decay.
3. **Decision/Preference flat scoring**: Decisions get `DECISION_FLAT_SCORE = 100.0` regardless of activation. JS has no concept of neighborhood types.
4. **Session deduplication**: `session_recalled` set prevents returning the same neighborhood twice in one session (except Decisions/Preferences). JS has no session tracking.
5. **Conscious recency boost**: Newer conscious neighborhoods get higher multiplier (up to 2.0x). JS treats all conscious neighborhoods equally.
6. **Budget-constrained composition** (`compose_context_budgeted`): Fills minimums per category, then greedily fills remaining token budget. Entirely new capability.
7. **`[DECIDED]` and `[PREFERENCE]` prefix in output**: Typed neighborhoods get semantic markers. JS has no equivalent.

**Mathematical impact:** The base scoring formula is preserved, but the Rust score can differ significantly due to project affinity, recency decay, and type-based flat scoring. These are all multiplicative modifiers on top of the original IDF \* activation formula. The original mathematical properties (IDF weighting, activation-proportional scoring) are preserved as the foundation; the additions are additive dimensions of relevance.

---

## 15. Tokenization

### JS (dae-core.mjs:502-509)

```javascript
function tokenize(text) {
  return text
    .replace(/[^\w\s']/g, " ")
    .toLowerCase()
    .split(/\s+/)
    .map((t) => t.replace(/^'+|'+$/g, ""))
    .filter((t) => t.length > 0);
}
```

### Rust (tokenizer.rs:15-23)

```rust
pub fn tokenize(text: &str) -> Vec<String> {
    let cleaned = NON_WORD.replace_all(text, " ");  // same regex: [^\w\s']
    cleaned.to_lowercase()
        .split_whitespace()
        .map(|t| APOSTROPHE_TRIM.replace_all(t, "").to_string())
        .filter(|t| !t.is_empty())
        .collect()
}
```

### Verdict: IDENTICAL

Same regex patterns, same processing order: strip non-word (keeping apostrophes), lowercase, split whitespace, trim leading/trailing apostrophes, filter empties. Rust uses compiled `LazyLock<Regex>` for performance.

---

## 16. Ingestion

### JS (dae-core.mjs:515-529)

```javascript
function ingestText(text, name = null) {
  const episode = new Episode(name);
  const sentences = text.split(/(?<=[.!?])\s+/).filter((s) => s.trim());
  const chunkSize = 3;
  for (let i = 0; i < sentences.length; i += chunkSize) {
    const chunk = sentences.slice(i, i + chunkSize).join(" ");
    const tokens = tokenize(chunk);
    if (tokens.length > 0) {
      const neighborhood = Neighborhood.fromTokens(tokens, null, chunk);
      episode.addNeighborhood(neighborhood);
    }
  }
  return episode;
}
```

### Rust (tokenizer.rs:56-71)

```rust
pub fn ingest_text(text: &str, name: Option<&str>, rng: &mut impl Rng) -> Episode {
    let mut episode = Episode::new(name.unwrap_or(""));
    let sentences = split_sentences(text);
    let chunk_size = 3;
    for chunk in sentences.chunks(chunk_size) {
        let combined = chunk.join(" ");
        let tokens = tokenize(&combined);
        if !tokens.is_empty() {
            let neighborhood = Neighborhood::from_tokens(&tokens, None, &combined, rng);
            episode.add_neighborhood(neighborhood);
        }
    }
    episode
}
```

### Verdict: IDENTICAL

3-sentence chunking, same tokenization, same neighborhood creation.

**Minor difference in sentence splitting regex:**

- JS: `text.split(/(?<=[.!?])\s+/)` (lookbehind, splits after punctuation)
- Rust: Custom `split_sentences()` using `Regex::new(r"[.!?]\s+")` with manual boundary tracking

Both produce the same splits for standard text. The Rust version manually handles the remainder after the last match.

---

## 17. Episode

### JS (dae-core.mjs:305-367)

```javascript
class Episode {
    constructor(name = 'Untitled', isConscious = false, id = null, timestamp = null) { ... }
    get displayName() { ... }  // formatted with date/time
    get count() { ... }
    get totalActivation() { ... }
    mass(N) { ... }
    *allOccurrences() { ... }
    activateWord(word) { ... }
    isVivid(systemCount) { return this.count > systemCount * THRESHOLD; }
}
```

### Rust (episode.rs:10-90)

```rust
pub struct Episode {
    pub id: Uuid,
    pub name: String,
    pub is_conscious: bool,
    pub timestamp: String,
    pub project_id: String,  // NEW
    pub neighborhoods: Vec<Neighborhood>,
}
// count, total_activation, mass: identical
// display_name: simplified (just name or "Memory")
// all_occurrences, all_occurrences_mut: equivalent
```

### Verdict: ADAPTED

**Preserved:** `count`, `total_activation`, `mass`, `add_neighborhood`.

**Differences:**

- Rust adds `project_id: String` for project-scoped recall. JS has no project concept.
- JS `displayName` formats with locale date/time; Rust `display_name()` just returns name or "Memory". The formatted display is handled at the MCP/CLI layer.
- JS `activateWord()` is on Episode; Rust moves it to `DAESystem.activate_word()` via the index.
- JS `isVivid()` is on Episode; Rust's surface computation checks vividness directly without this method.

---

## 18. DAESystem / Indexes

### JS (dae-core.mjs:373-496)

```javascript
class DAESystem {
    constructor() {
        this.episodes = [];
        this.consciousEpisode = new Episode('conscious', true);
        this._indexDirty = true;
        this._wordNeighborhoodIndex = new Map();
        this._wordOccurrenceIndex = new Map();
        this._neighborhoodIndex = new Map();
        this._neighborhoodEpisodeIndex = new Map();
        this.agentName = 'DAE';
    }
    get N() { ... }
    get totalActivation() { ... }
    getWordWeight(word) { ... }
    activateWord(word) { ... }
    addToConscious(text) { ... }
}
```

### Rust (system.rs:52-328)

```rust
pub struct DAESystem {
    pub episodes: Vec<Episode>,
    pub conscious_episode: Episode,
    pub agent_name: String,
    word_neighborhood_index: HashMap<String, HashSet<Uuid>>,
    word_occurrence_index: HashMap<String, Vec<OccurrenceRef>>,
    neighborhood_index: HashMap<Uuid, NeighborhoodRef>,
    neighborhood_episode_index: HashMap<Uuid, usize>,
    index_dirty: bool,
}
```

### Verdict: ADAPTED

**Preserved:**

- Same 4 indexes with same semantics
- Lazy rebuild on dirty flag
- N, totalActivation, getWordWeight, activateWord, addToConscious: identical behavior

**Differences:**

- Rust uses `OccurrenceRef` (episode_idx, neighborhood_idx, occurrence_idx) instead of direct object references. This is a structural adaptation required by Rust's ownership model.
- `usize::MAX` sentinel for conscious episode index (JS just checks `ep.isConscious`).
- Rust adds `get_occurrence()`, `get_occurrence_mut()`, `get_neighborhood_for_occurrence()`, `get_episode_for_occurrence()` for safe access through the hierarchy.

---

## 19. Query Engine Pipeline

### JS (dae-core.mjs:797-819)

```javascript
processQuery(query) {
    const activation = this.activate(query);
    // Weight floor for large queries (>50 tokens)
    if (queryTokenCount > 50) { ... filter by weightFloor ... }
    this.driftAndConsolidate(activation.subconscious);
    this.driftAndConsolidate(activation.conscious);
    const interference = this.computeInterference(activation.subconscious, activation.conscious);
    const surface = this.computeSurface(activation, interference);
    return { activation, interference, surface };
}
```

### Rust (query.rs:58-109)

```rust
pub fn process_query(system: &mut DAESystem, query: &str) -> QueryResult {
    let activation = Self::activate(system, query);
    // Weight floor for large queries (>50 tokens) -- identical logic
    Self::drift_and_consolidate(system, &drift_sub);
    Self::drift_and_consolidate(system, &drift_con);
    let (interference, word_groups) = Self::compute_interference(system, ...);
    Self::apply_kuramoto_coupling(system, &word_groups);
    QueryResult { activation, interference, word_groups }
}
```

### Verdict: ADAPTED

**Same pipeline order:** activate -> weight floor filter -> drift sub + con -> interference -> Kuramoto.

**Key difference:** In JS, `computeInterference()` calls `this.applyKuramotoCoupling(wordGroups)` internally. In Rust, Kuramoto is called as a separate step in `process_query`. Same result, cleaner separation.

**Note:** In JS, `processQuery` calls `computeSurface` as part of the pipeline. In Rust, surface computation is separated out -- the caller (MCP server / compose layer) calls `compute_surface()` after `process_query()`. This is an architectural improvement (separation of concerns) with no mathematical difference.

---

## 20. Feedback System

### JS: **NO EQUIVALENT**

The JS `dae-core.mjs` has no feedback mechanism. There is no way to boost or demote recalled memories based on whether they were helpful.

### Rust (feedback.rs:58-201)

```rust
pub fn apply_feedback(system: &mut DAESystem, query: &str,
    neighborhood_ids: &[Uuid], signal: FeedbackSignal) -> FeedbackResult {
    // Boost: SLERP target occurrences toward IDF-weighted query centroid
    //   factor = BOOST_DRIFT_FACTOR * IDF_weight * plasticity
    //   also increments activation_count
    // Demote: decrement activation_count by DEMOTE_DECAY (saturating at 0)
}
```

**Verdict: NEW IN RUST**

Entirely new capability. Constants: `BOOST_DRIFT_FACTOR = 0.15`, `DEMOTE_DECAY = 2`. Uses the same geometric primitives (SLERP, IDF weighting, plasticity) as the rest of the engine. Mathematically consistent with the manifold model -- boost drifts occurrences closer to where they were needed, demote makes them less anchored.

---

## 21. Salient Extraction

### JS (dae-core.mjs:966-969)

```javascript
function extractSalient(system, text) {
  const m = text.match(/<salient>(.*?)<\/salient>/gs);
  if (m)
    m.forEach((s) => system.addToConscious(s.replace(/<\/?salient>/g, "")));
  return m ? m.length : 0;
}
```

### Rust (compose.rs:868-905)

```rust
static SALIENT_RE: LazyLock<Regex> = LazyLock::new(|| Regex::new(r"(?s)<salient>(.*?)</salient>").unwrap());

pub fn extract_salient(system: &mut DAESystem, text: &str, rng: &mut impl Rng) -> u32 {
    for cap in SALIENT_RE.captures_iter(text) {
        if let Some(content) = cap.get(1) {
            let (nbhd_type, clean_text) = detect_neighborhood_type(content.as_str());
            system.add_to_conscious_typed(clean_text, nbhd_type, rng);
        }
    }
}
```

### Verdict: ADAPTED

Same regex extraction of `<salient>` tags. Rust adds **type detection**: `DECISION:` and `PREFERENCE:` prefixes in the salient text are stripped and used to set the `NeighborhoodType`. Rust also adds `mark_salient_typed()` for programmatic (non-tag) salient marking.

---

## 22. Serde Compatibility (Wire Format)

### JS: Inline `toJSON()` / `fromJSON()` methods on every class.

### Rust (serde_compat.rs): Dedicated module with `WireExport`, `WireSystem`, `WireEpisode`, `WireNeighborhood`, `WireOccurrence` types.

### Verdict: ADAPTED

- Wire format matches v0.7.2 JSON exactly (camelCase fields, `[w,x,y,z]` quaternion arrays, bare theta floats).
- Supports `theta` alias for `phasor` field (backward compatibility with older exports).
- Supports `projectId` and `neighborhoodType` fields (gracefully ignored by JS if present).
- Round-trip tested: export from Rust -> import back preserves all quaternion positions, phasor angles, activation counts, and structure.

---

## Summary Table

| Component                   | Verdict   | Notes                                         |
| --------------------------- | --------- | --------------------------------------------- |
| Constants                   | IDENTICAL | Pre-computed, numerically exact match         |
| Quaternion struct           | ADAPTED   | Auto-normalize, Clone+Copy. Safer.            |
| Quaternion.normalize        | IDENTICAL |                                               |
| Quaternion.dot              | IDENTICAL |                                               |
| Quaternion.geodesicDistance | IDENTICAL |                                               |
| Quaternion.slerp            | IDENTICAL | +clamp for numerical safety                   |
| Quaternion.random           | IDENTICAL | Removed dead `sqrtTerm` variable              |
| Quaternion.randomNear       | IDENTICAL | Hamilton product factored into Mul trait      |
| Hamilton product            | ADAPTED   | Standalone Mul impl vs inline                 |
| gaussRandom                 | ADAPTED   | Clamped u1 away from zero                     |
| DaemonPhasor                | ADAPTED   | rem_euclid vs remainder modulo                |
| Occurrence fields           | ADAPTED   | Added per-occurrence UUID, u32 activation     |
| Occurrence.driftRate        | IDENTICAL |                                               |
| Occurrence.plasticity       | IDENTICAL |                                               |
| Occurrence.isAnchored       | ADAPTED   | Bug fix: division-by-zero guard               |
| Occurrence.mass             | IDENTICAL |                                               |
| Occurrence.driftToward      | MISSING   | Dead code in JS, drift handled by QueryEngine |
| Neighborhood.fromTokens     | IDENTICAL |                                               |
| Neighborhood.driftAll       | MISSING   | Dead code in JS, never called in pipeline     |
| Neighborhood type system    | NEW       | Decision/Preference/Insight/Memory            |
| Pairwise drift formula      | IDENTICAL |                                               |
| Pairwise drift semantics    | DIVERGED  | Snapshot vs in-place (intentional)            |
| Centroid drift              | IDENTICAL |                                               |
| Interference calculation    | IDENTICAL |                                               |
| Kuramoto coupling           | IDENTICAL | All formulas preserved                        |
| Activation mechanics        | IDENTICAL |                                               |
| IDF weighting               | IDENTICAL |                                               |
| Surface computation         | IDENTICAL |                                               |
| Composition scoring base    | IDENTICAL | IDF \* activation                             |
| Project affinity scoring    | NEW       | 2.0x / 1.0x / 0.3x multiplier                 |
| Recency decay scoring       | NEW       | 1/(1 + days \* 0.01)                          |
| Decision flat scoring       | NEW       | DECISION_FLAT_SCORE = 100.0                   |
| Session deduplication       | NEW       | Skip already-recalled non-decisions           |
| Budget composition          | NEW       | Token-budget-constrained output               |
| Conscious recency boost     | NEW       | Newer conscious neighborhoods score higher    |
| Feedback (boost/demote)     | NEW       | SLERP toward query centroid / decay           |
| Salient type detection      | NEW       | DECISION:/PREFERENCE: prefix parsing          |
| Tokenization                | IDENTICAL | Same regex, same pipeline                     |
| Ingestion (3-sentence)      | IDENTICAL |                                               |
| Episode                     | ADAPTED   | Added project_id, simplified display          |
| DAESystem indexes           | ADAPTED   | OccurrenceRef architecture for ownership      |
| Query pipeline order        | IDENTICAL | activate->drift->interference->Kuramoto       |
| Serde wire format           | ADAPTED   | v0.7.2 compatible with extensions             |

---

## Mathematical Properties Assessment

### Fully Preserved

1. **S^3 manifold model** -- closed, unit quaternion, finite mass M=1
2. **Golden angle phase distribution** -- 2pi/phi^2, maximally irrational spacing
3. **Neighborhood radius** -- pi/phi geodesic cap on S^3
4. **SLERP interpolation** -- shortest arc, antipodal flip, NLERP fallback at 0.9995
5. **Drift rate** -- ratio/THRESHOLD, anchoring at ratio > THRESHOLD
6. **Plasticity curve** -- 1/(1 + ln(1 + c)), logarithmic diminishing returns
7. **IDF weighting** -- 1/(number of neighborhoods containing word)
8. **Mass conservation** -- activation/N \* M, total mass = 1
9. **Interference** -- cos(phase_difference), constructive/destructive
10. **Kuramoto coupling** -- K_CON + K_SUB = 1, coupling = IDF^2, plasticity-modulated sin(phaseDiff)
11. **Vivid threshold** -- 0.5 for neighborhoods, episodes, and drift anchoring

### Intentionally Changed

1. **Pairwise drift semantics** -- snapshot-then-apply instead of in-place mutation. Eliminates iteration-order dependence. Different numerical results but more principled.
2. **Phasor normalization** -- always [0, TAU) via rem_euclid instead of potentially negative. Prevents phase accumulation.
3. **Occurrence.isAnchored** -- returns true for zero container activation instead of NaN comparison. Bug fix.

### Newly Added (no JS equivalent)

1. Project-scoped recall with affinity scoring
2. Recency decay on non-decision memories
3. Decision/Preference neighborhood types with flat scoring
4. Session deduplication preventing repeated recall
5. Budget-constrained context composition
6. Feedback system (boost/demote with geometric SLERP)
7. Conscious recency boost (newer salient memories rank higher)
8. Garbage collection infrastructure (constants defined, implementation in am-store)

### Absent from Rust (present in JS but unused)

1. `Occurrence.driftToward()` -- only used by `Neighborhood.driftAll()` which was never called in the query pipeline
2. `Neighborhood.driftAll()` -- appears to be vestigial; all drift is handled by QueryEngine
3. `Episode.isVivid()` -- vividness is checked inline in surface computation
4. `DAE_SYSTEM_PROMPT` constant -- prompt template lives in the MCP server layer, not in core
5. `Episode.displayName` with locale-formatted timestamp -- display formatting is at the API layer

---

## Conclusion

The Rust port is a **high-fidelity mathematical port** of the JS engine. Every core formula -- quaternion operations, drift mechanics, interference, Kuramoto coupling, IDF weighting, plasticity, mass conservation -- is preserved exactly. The three intentional divergences (snapshot drift, phasor normalization, isAnchored guard) are all improvements that do not break any mathematical invariant.

The substantial new capabilities (feedback, project scoping, recency decay, typed neighborhoods, budget composition, session dedup) are all built on top of the original mathematical foundations, using the same primitives (SLERP, IDF, plasticity). They extend the model without contradicting it.

No mathematical properties were lost or accidentally changed.
