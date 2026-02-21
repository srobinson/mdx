# DAE OpenClaw Server — Complete Technical Analysis

**Source:** `/Users/alphab/Dev/LLM/DEV/DAE/SOURCE/dae-openclaw/`
**Version:** 0.7.2
**Author:** smaxforn
**Analyzed:** 2026-02-13
**Purpose:** Full extraction of every algorithm, constant, data structure, and technique for Rust reimplementation.

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Constants and Mathematical Foundations](#2-constants-and-mathematical-foundations)
3. [Quaternion Implementation](#3-quaternion-implementation)
4. [DaemonPhasor](#4-daemonphasor)
5. [Occurrence](#5-occurrence)
6. [Neighborhood](#6-neighborhood)
7. [Episode](#7-episode)
8. [DAESystem](#8-daesystem)
9. [Tokenization](#9-tokenization)
10. [Ingestion](#10-ingestion)
11. [QueryEngine — Activation Pipeline](#11-queryengine--activation-pipeline)
12. [SLERP Drift with IDF Weighting](#12-slerp-drift-with-idf-weighting)
13. [Phasor Interference](#13-phasor-interference)
14. [Kuramoto Model](#14-kuramoto-model)
15. [Surface Computation](#15-surface-computation)
16. [Context Composition](#16-context-composition)
17. [Salient Extraction](#17-salient-extraction)
18. [System Prompt](#18-system-prompt)
19. [Server API Layer](#19-server-api-layer)
20. [Agent Integration (moltbook-agent)](#20-agent-integration-moltbook-agent)
21. [State Serialization](#21-state-serialization)
22. [Complete Export List](#22-complete-export-list)
23. [Differences from Browser Standalone](#23-differences-from-browser-standalone)
24. [Rust Module Mapping](#24-rust-module-mapping)

---

## 1. Architecture Overview

```
OpenClaw Agent  ──HTTP──  dae-server.mjs   (I/O, persistence, HTTP routing)
                              |
                         dae-core.mjs      (Pure computation, zero dependencies)
                              |
                        .dae-state/        (JSON on disk)

moltbook-agent.mjs   (Standalone alternative: embeds dae-core + LLM + Moltbook polling)
import-state.mjs     (CLI utility: imports browser exports into .dae-state/)
```

**Module boundaries:**

- `dae-core.mjs` (984 lines) — Pure math + memory. No I/O, no browser, no Node APIs (except `crypto.randomUUID()`). All classes and functions are exported.
- `dae-server.mjs` (359 lines) — HTTP wrapper. Reads/writes state to disk. Manages conversation buffer. Depends on `dae-core.mjs` + Node `http`, `fs`, `path`.
- `moltbook-agent.mjs` (625 lines) — Autonomous agent. Embeds the full DAE pipeline. Polls Moltbook API, calls LLM providers, manages state. Alternative to server mode.
- `import-state.mjs` (73 lines) — CLI tool. Validates and writes a browser/agent export into `.dae-state/`.

**Data flow for a single turn (server mode):**

1. `POST /query` with user text -> tokenize -> activate words -> drift -> interference -> surface -> compose context -> return
2. Agent uses context in its LLM call
3. `POST /activate-response` with agent response -> activate words -> weight-filtered drift -> Kuramoto coupling -> save state
4. `POST /salient` with insight text (optional) -> extract salient tags -> add to conscious episode -> save state
5. `POST /buffer` with {user, assistant} -> append to buffer -> if buffer >= threshold, create episode -> save state

---

## 2. Constants and Mathematical Foundations

**File:** `dae-core.mjs` lines 1-36

The system models memory as a closed manifold S^3 (the 3-sphere, the surface of a 4D hypersphere) with fixed total mass M=1. Adding content increases resolution/density, not volume.

```js
const PHI = (1 + Math.sqrt(5)) / 2; // 1.6180339887...
const GOLDEN_ANGLE = (2 * Math.PI) / (PHI * PHI); // 2*pi/phi^2 ~ 2.39996... rad ~ 137.508 degrees
const NEIGHBORHOOD_RADIUS = Math.PI / PHI; // pi/phi ~ 1.94161... rad ~ 111.246 degrees
const THRESHOLD = 0.5; // Universal threshold for anchoring, vividness, mass
const M = 1; // Fixed total mass of the closed universe
const EPSILON = 1e-10; // Numerical stability guard
```

**Mathematical foundations described in the header comment:**

| Concept              | Formula                                                                    | Description                                                           |
| -------------------- | -------------------------------------------------------------------------- | --------------------------------------------------------------------- |
| Closed universe      | S^3, M=1                                                                   | Fixed mass, growth adds density not volume                            |
| N                    | Total occurrences across all episodes                                      | System size                                                           |
| Anchoring            | `drift = 1 - 2c/C` when `c/C <= 0.5`, else `drift = 0`                     | Words anchor when activation count exceeds half the container's total |
| Anchor threshold     | `c/C > 0.5`                                                                | Occurrence is anchored (won't drift)                                  |
| Golden angle         | `2*pi/phi^2 ~ 137.5 deg`                                                   | Phyllotaxis distribution for phasors                                  |
| Neighborhood radius  | `pi/phi ~ 111 deg`                                                         | Angular radius within which word positions are scattered              |
| Interference         | `cos(delta_theta)`                                                         | Constructive (+1) or destructive (-1)                                 |
| IDF weighting        | `1 / (number of neighborhoods word appears in)`                            | Inverse document frequency analog                                     |
| Kuramoto coupling    | `K_CON + K_SUB = 1` where `K_CON = N_sub/N_total`, `K_SUB = N_con/N_total` | Cross-manifold phase synchronization                                  |
| Plasticity           | `1 / (1 + log(1 + activationCount))`                                       | Diminishing returns on phase updates                                  |
| Mass of occurrence   | `(c / N) * M` where c=activationCount, N=total occurrences                 | Proportional mass in closed universe                                  |
| Mass of neighborhood | `(count / N) * M`                                                          | Proportional by occurrence count                                      |
| Mass of episode      | `(count / N) * M`                                                          | Same proportional scheme                                              |

---

## 3. Quaternion Implementation

**File:** `dae-core.mjs` lines 42-132

Quaternions represent points on S^3. They are always normalized (unit quaternions).

### Constructor

```js
class Quaternion {
  constructor(w = 1, x = 0, y = 0, z = 0) {
    this.w = w;
    this.x = x;
    this.y = y;
    this.z = z;
  }
}
```

Default is the identity quaternion (1, 0, 0, 0).

### Normalize

```js
normalize() {
    const norm = Math.sqrt(this.w*this.w + this.x*this.x + this.y*this.y + this.z*this.z);
    if (norm < EPSILON) return new Quaternion();  // Degenerate -> identity
    return new Quaternion(this.w/norm, this.x/norm, this.y/norm, this.z/norm);
}
```

Returns a NEW quaternion (immutable pattern). Falls back to identity if norm is near zero.

### Dot Product

```js
dot(other) {
    return this.w*other.w + this.x*other.x + this.y*other.y + this.z*other.z;
}
```

Standard 4D dot product. Used for geodesic distance and SLERP.

### Random (Uniform on S^3)

```js
static random() {
    const s1 = Math.random();
    const s2 = Math.random();
    const t1 = 2 * Math.PI * Math.random();
    const t2 = 2 * Math.PI * Math.random();
    const sqrtTerm = Math.sqrt((1 - s1) / s2);  // NOTE: unused variable
    return new Quaternion(
        Math.sqrt(1 - s1) * Math.sin(t1),
        Math.sqrt(1 - s1) * Math.cos(t1),
        Math.sqrt(s1) * Math.sin(t2),
        Math.sqrt(s1) * Math.cos(t2)
    ).normalize();
}
```

This is the Shoemake algorithm for uniform random quaternions on S^3. Note `sqrtTerm` is computed but never used — the actual components use `sqrt(1-s1)` and `sqrt(s1)` directly. The `.normalize()` at the end is technically redundant for this parameterization but acts as a safety net.

### Random Near (Neighborhood Placement)

```js
static randomNear(center, angularRadius) {
    // Generate random axis via Gaussian samples (uniform on sphere)
    let ax = gaussRandom(), ay = gaussRandom(), az = gaussRandom();
    const axNorm = Math.sqrt(ax*ax + ay*ay + az*az);
    if (axNorm < EPSILON) return center;
    ax /= axNorm; ay /= axNorm; az /= axNorm;

    // Random angle within radius (sqrt for uniform area distribution)
    const angle = angularRadius * Math.sqrt(Math.random());
    const halfAngle = angle / 2;
    const sinHalf = Math.sin(halfAngle);
    const cosHalf = Math.cos(halfAngle);

    // Build rotation quaternion and multiply with center
    const rotation = new Quaternion(cosHalf, ax * sinHalf, ay * sinHalf, az * sinHalf);
    return new Quaternion(
        rotation.w * center.w - rotation.x * center.x - rotation.y * center.y - rotation.z * center.z,
        rotation.w * center.x + rotation.x * center.w + rotation.y * center.z - rotation.z * center.y,
        rotation.w * center.y - rotation.x * center.z + rotation.y * center.w + rotation.z * center.x,
        rotation.w * center.z + rotation.x * center.y - rotation.y * center.x + rotation.z * center.w
    ).normalize();
}
```

**Algorithm:**

1. Generate a random rotation axis from 3 Gaussian random numbers (Box-Muller), normalize to unit vector.
2. Pick a random angle within `angularRadius` using `sqrt(random)` for uniform distribution within the cap area.
3. Build a rotation quaternion from half-angle and axis.
4. Multiply rotation \* center (this IS the quaternion multiplication, written out inline — Hamilton product).
5. Normalize the result.

This places the new point within an angular distance of `angularRadius` from `center` on S^3.

**The quaternion multiplication formula (Hamilton product) used inline:**

```
(a, b) -> result where:
  result.w = a.w*b.w - a.x*b.x - a.y*b.y - a.z*b.z
  result.x = a.w*b.x + a.x*b.w + a.y*b.z - a.z*b.y
  result.y = a.w*b.y - a.x*b.z + a.y*b.w + a.z*b.x
  result.z = a.w*b.z + a.x*b.y - a.y*b.x + a.z*b.w
```

Note: There is no standalone `multiply()` method. The Hamilton product is only ever written inline in `randomNear()`.

### Geodesic Distance

```js
geodesicDistance(other) {
    const d = Math.min(1, Math.max(-1, Math.abs(this.dot(other))));
    return 2 * Math.acos(d);
}
```

Geodesic (great-circle) distance on S^3. The `abs(dot)` treats antipodal quaternions as the same point (they represent the same rotation). Clamped to [-1, 1] for numerical safety. Returns radians in [0, pi].

**Note:** This method exists but is never called in the codebase. It's available for external use.

### SLERP (Spherical Linear Interpolation)

```js
slerp(other, t) {
    if (t <= 0) return this;
    if (t >= 1) return other;
    let dot = this.dot(other);
    let o = other;

    // Flip to shorter arc if needed
    if (dot < 0) {
        o = new Quaternion(-other.w, -other.x, -other.y, -other.z);
        dot = -dot;
    }

    // Near-parallel: use linear interpolation (avoid division by near-zero sin)
    if (dot > 0.9995) {
        return new Quaternion(
            this.w + t * (o.w - this.w), this.x + t * (o.x - this.x),
            this.y + t * (o.y - this.y), this.z + t * (o.z - this.z)
        ).normalize();
    }

    // Standard SLERP
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

**Algorithm:**

1. Boundary checks (t=0 returns `this`, t=1 returns `other`).
2. If dot product is negative, negate `other` to take the shorter arc.
3. If nearly parallel (dot > 0.9995), use normalized linear interpolation (NLERP) to avoid numerical instability.
4. Otherwise, compute standard SLERP: `q(t) = sin((1-t)*theta)/sin(theta) * q0 + sin(t*theta)/sin(theta) * q1`.
5. Always normalize the result.

### Serialization

```js
toArray() { return [this.w, this.x, this.y, this.z]; }
static fromArray(arr) { return new Quaternion(arr[0], arr[1], arr[2], arr[3]); }
```

Wire format: `[w, x, y, z]` — 4-element array.

### Gaussian Random Helper

```js
function gaussRandom() {
  const u1 = Math.random();
  const u2 = Math.random();
  return Math.sqrt(-2 * Math.log(u1)) * Math.cos(2 * Math.PI * u2);
}
```

Box-Muller transform. Returns a single standard normal sample. Used by `Quaternion.randomNear()` to generate a uniform random axis on the 2-sphere.

---

## 4. DaemonPhasor

**File:** `dae-core.mjs` lines 138-155

A phasor is a phase angle on the golden-angle lattice. It lives on the circle (S^1), not on S^3.

```js
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

**Key details:**

- `fromIndex(i)`: Assigns phase = `baseTheta + i * GOLDEN_ANGLE`. Each successive word in a neighborhood gets a phase offset by the golden angle (~137.5 degrees). This creates a phyllotaxis-like spiral that maximally spreads phases.
- `interference(other)`: Returns `cos(theta1 - theta2)`. Range: [-1, +1]. +1 = constructive (in phase), -1 = destructive (out of phase).
- `slerp(other, t)`: Circular SLERP. Wraps the difference to [-pi, pi] for shortest-arc interpolation, then linearly interpolates the angle.

**Serialization:** Only `theta` (a float) is stored. Reconstructed via `new DaemonPhasor(theta)`.

---

## 5. Occurrence

**File:** `dae-core.mjs` lines 161-221

An Occurrence is a single word instance placed on S^3 with an associated phasor.

```js
class Occurrence {
  constructor(word, position, phasor, neighborhoodId = null) {
    this.word = word; // string, the token
    this.position = position; // Quaternion on S^3
    this.phasor = phasor; // DaemonPhasor (phase angle)
    this.activationCount = 0; // int, how many times activated
    this.neighborhoodId = neighborhoodId; // UUID of parent neighborhood
  }
}
```

### Activate

```js
activate() { this.activationCount++; }
```

Simply increments the counter.

### Drift Rate

```js
getDriftRate(containerActivation) {
    if (containerActivation === 0) return 0;
    const ratio = this.activationCount / containerActivation;
    if (ratio > THRESHOLD) return 0;    // Anchored — won't move
    return ratio / THRESHOLD;            // Linear ramp: 0 at ratio=0, 1 at ratio=THRESHOLD
}
```

**Drift formula:**

- `ratio = activationCount / containerTotalActivation`
- If `ratio > 0.5` (THRESHOLD): the occurrence is **anchored** — drift rate = 0.
- Otherwise: `driftRate = ratio / 0.5 = 2 * ratio`. Linearly increases from 0 to 1 as the ratio approaches the threshold.

**Interpretation:** Words that are activated proportionally more relative to their container are more anchored. Words that are barely activated drift more freely. Once a word reaches half the container's total activation, it locks in place.

### Plasticity

```js
get plasticity() {
    const c = this.activationCount;
    return 1 / (1 + Math.log(1 + c));
}
```

**Values:**

- c=0: plasticity = 1/(1 + log(1)) = 1/(1+0) = 1.0
- c=1: plasticity = 1/(1 + log(2)) = 1/1.693 = 0.591
- c=10: plasticity = 1/(1 + log(11)) = 1/3.398 = 0.294
- c=100: plasticity = 1/(1 + log(101)) = 1/5.620 = 0.178
- c=1000: plasticity = 1/(1 + log(1001)) = 1/7.909 = 0.126

Logarithmic decay — initially responsive, gradually hardening. Used in Kuramoto coupling to modulate phase updates.

### isAnchored

```js
isAnchored(containerActivation) {
    const ratio = this.activationCount / containerActivation;
    return ratio > THRESHOLD;
}
```

Boolean check. Not called internally (drift rate handles the logic). Available for external queries.

### Mass

```js
mass(N) {
    const c = this.activationCount;
    return N > 0 ? (c / N) * M : 0;
}
```

Proportional mass in the closed universe: `activationCount / totalSystemOccurrences * 1.0`.

### Drift Toward

```js
driftToward(target, containerActivation) {
    const t = this.getDriftRate(containerActivation);
    if (t <= 0) return;
    this.position = this.position.slerp(target.position, t);
    this.phasor = this.phasor.slerp(target.phasor, t);
}
```

Moves this occurrence toward a target by SLERP-ing both position (on S^3) and phasor (on S^1). Only moves if drift rate > 0. This is used by `Neighborhood.driftAll()`.

### Serialization

```js
toJSON() {
    return {
        word: this.word,
        position: this.position.toArray(),    // [w, x, y, z]
        phasor: this.phasor.theta,            // float
        activationCount: this.activationCount, // int
        neighborhoodId: this.neighborhoodId    // UUID string
    };
}

static fromJSON(data) {
    const occ = new Occurrence(
        data.word,
        Quaternion.fromArray(data.position),
        new DaemonPhasor(data.phasor ?? data.theta ?? 0),  // backward compat: "theta" field
        data.neighborhoodId
    );
    occ.activationCount = data.activationCount || 0;
    return occ;
}
```

---

## 6. Neighborhood

**File:** `dae-core.mjs` lines 227-299

A Neighborhood is a chunk of text (e.g., 3 sentences) containing a collection of Occurrences, anchored around a seed quaternion.

```js
class Neighborhood {
  constructor(seed, id = null, sourceText = "") {
    this.seed = seed; // Quaternion — center point on S^3
    this.id = id || crypto.randomUUID(); // UUID
    this.occurrences = []; // Array<Occurrence>
    this.text = sourceText; // Original source text (for display)
  }
}
```

### Factory: fromTokens

```js
static fromTokens(tokens, seed = null, sourceText = '') {
    const neighborhood = new Neighborhood(seed || Quaternion.random(), null, sourceText);
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

**Word positioning algorithm:**

1. If no seed provided, pick a random point on S^3.
2. For each token at index `i`:
   a. Position: `randomNear(seed, pi/phi)` — random point within ~111 degrees of the seed.
   b. Phasor: `fromIndex(i)` — phase = `i * GOLDEN_ANGLE` (i.e., `i * 2*pi/phi^2`).
   c. Create Occurrence, link to this neighborhood.

**Important:** Every word in the same neighborhood is clustered around the same seed on S^3, but each gets an independent random offset within the neighborhood radius. The phasor gives each word a distinct phase based on its position in the text.

### Computed Properties

```js
get count() { return this.occurrences.length; }

get totalActivation() {
    return this.occurrences.reduce((sum, o) => sum + o.activationCount, 0);
}

mass(N) {
    return N > 0 ? (this.count / N) * M : 0;
}
```

### activateWord

```js
activateWord(word) {
    const activated = [];
    const wordLower = word.toLowerCase();
    this.occurrences.forEach(o => {
        if (o.word.toLowerCase() === wordLower) {
            o.activate();
            activated.push(o);
        }
    });
    return activated;
}
```

Case-insensitive activation. Increments `activationCount` on every matching occurrence and returns the list.

### isVivid

```js
isVivid(episodeCount) {
    return this.count > episodeCount * THRESHOLD;
}
```

A neighborhood is "vivid" if its occurrence count exceeds half of the episode's total count.

### driftAll

```js
driftAll() {
    const C = this.totalActivation;
    this.occurrences.forEach(o => {
        if (o.activationCount > 0) o.driftToward(this.occurrences[0], C);
    });
}
```

Drifts all activated occurrences toward the FIRST occurrence in the neighborhood. Uses the neighborhood's total activation as the container activation. Note: this is a simpler intra-neighborhood drift, distinct from the cross-neighborhood drift in QueryEngine.

### Serialization

```js
toJSON() {
    const C = this.totalActivation;  // computed but not stored (recalculated from occurrences)
    return {
        seed: this.seed.toArray(),         // [w, x, y, z]
        id: this.id,                       // UUID string
        sourceText: this.text,             // string
        occurrences: this.occurrences.map(o => {
            const base = o.toJSON();
            base.neighborhoodId = this.id; // ensure consistent
            return base;
        })
    };
}

static fromJSON(data) {
    const n = new Neighborhood(Quaternion.fromArray(data.seed), data.id, data.sourceText);
    n.occurrences = (data.occurrences || []).map(o => Occurrence.fromJSON(o));
    return n;
}
```

---

## 7. Episode

**File:** `dae-core.mjs` lines 305-367

An Episode is a collection of Neighborhoods representing one conversation or document.

```js
class Episode {
  constructor(
    name = "Untitled",
    isConscious = false,
    id = null,
    timestamp = null,
  ) {
    this.name = name;
    this.isConscious = isConscious; // true only for the conscious episode
    this.id = id || crypto.randomUUID();
    this.timestamp = timestamp || new Date().toISOString();
    this.neighborhoods = []; // Array<Neighborhood>
  }
}
```

### displayName

```js
get displayName() {
    if (this.isConscious) return 'Conscious';
    const date = new Date(this.timestamp);
    const dateStr = date.toLocaleDateString('en-US', { month: 'numeric', day: 'numeric', year: '2-digit' });
    const timeStr = date.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' });
    return `${this.name} (${dateStr} ${timeStr})`;
}
```

Formats as e.g. "Conversation 3 (2/13/26 4:30 PM)".

### Computed Properties

```js
get count() {
    return this.neighborhoods.reduce((sum, n) => sum + n.count, 0);
}

get totalActivation() {
    return this.neighborhoods.reduce((sum, n) => sum + n.totalActivation, 0);
}

mass(N) {
    return N > 0 ? (this.count / N) * M : 0;
}
```

### Generator: allOccurrences

```js
*allOccurrences() {
    for (const n of this.neighborhoods) {
        yield* n.occurrences;
    }
}
```

Yields every occurrence across all neighborhoods in this episode.

### activateWord, isVivid, serialization

Delegates to child neighborhoods. `isVivid` checks `count > systemCount * THRESHOLD`.

---

## 8. DAESystem

**File:** `dae-core.mjs` lines 373-496

The top-level container. Holds all episodes plus the special conscious episode, and maintains indexes for fast lookup.

```js
class DAESystem {
  constructor() {
    this.episodes = []; // Array<Episode> — subconscious episodes
    this.consciousEpisode = new Episode("conscious", true); // The single conscious episode
    this._indexDirty = true; // Lazy rebuild flag
    this._wordNeighborhoodIndex = new Map(); // word -> Set<neighborhoodId>
    this._wordOccurrenceIndex = new Map(); // word -> Array<Occurrence>
    this._neighborhoodIndex = new Map(); // neighborhoodId -> Neighborhood
    this._neighborhoodEpisodeIndex = new Map(); // neighborhoodId -> Episode
    this.agentName = "DAE";
  }
}
```

### Index Rebuild

```js
_rebuildIndexes() {
    if (!this._indexDirty) return;
    this._wordNeighborhoodIndex.clear();
    this._wordOccurrenceIndex.clear();
    this._neighborhoodIndex.clear();
    this._neighborhoodEpisodeIndex.clear();

    const allEpisodes = [...this.episodes, this.consciousEpisode];
    for (const ep of allEpisodes) {
        for (const n of ep.neighborhoods) {
            this._neighborhoodIndex.set(n.id, n);
            this._neighborhoodEpisodeIndex.set(n.id, ep);
            for (const occ of n.occurrences) {
                const w = occ.word.toLowerCase();
                if (!this._wordNeighborhoodIndex.has(w)) {
                    this._wordNeighborhoodIndex.set(w, new Set());
                }
                this._wordNeighborhoodIndex.get(w).add(n.id);
                if (!this._wordOccurrenceIndex.has(w)) {
                    this._wordOccurrenceIndex.set(w, []);
                }
                this._wordOccurrenceIndex.get(w).push(occ);
            }
        }
    }
    this._indexDirty = false;
}
```

**Four indexes, lazily rebuilt:**

1. `_wordNeighborhoodIndex`: word (lowercase) -> Set of neighborhood IDs containing that word. Used for IDF weight computation.
2. `_wordOccurrenceIndex`: word (lowercase) -> all Occurrence objects for that word across the entire system. Used for fast activation.
3. `_neighborhoodIndex`: neighborhood ID -> Neighborhood object.
4. `_neighborhoodEpisodeIndex`: neighborhood ID -> Episode object that contains it.

The dirty flag is set when episodes are added or conscious neighborhoods are created. Rebuild runs on first access.

### N (Total Occurrence Count)

```js
get N() {
    return this.episodes.reduce((sum, e) => sum + e.count, 0) + this.consciousEpisode.count;
}
```

### IDF Weight (getWordWeight)

```js
getWordWeight(word) {
    this._rebuildIndexes();
    const nids = this._wordNeighborhoodIndex.get(word.toLowerCase());
    return 1 / (nids ? nids.size : 1);
}
```

**IDF formula:** `weight = 1 / (number of neighborhoods this word appears in)`.

- Word in 1 neighborhood: weight = 1.0 (unique/rare)
- Word in 5 neighborhoods: weight = 0.2 (common)
- Word in 100 neighborhoods: weight = 0.01 (very common, like stop words)

This is the core importance signal. It's used in drift magnitude, Kuramoto coupling strength, and context scoring.

### activateWord

```js
activateWord(word) {
    this._rebuildIndexes();
    const subconscious = [];
    const conscious = [];
    const wordLower = word.toLowerCase();

    const occs = this._wordOccurrenceIndex.get(wordLower);
    if (!occs) return { subconscious, conscious };

    for (const occ of occs) {
        occ.activate();  // increment activationCount
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

Activates ALL occurrences of a word across the entire system, partitioned into conscious vs subconscious.

### addToConscious

```js
addToConscious(text) {
    const tokens = tokenize(text);
    const neighborhood = Neighborhood.fromTokens(tokens, null, text);
    neighborhood.occurrences.forEach(o => o.activate());  // Pre-activate all occurrences
    this.consciousEpisode.addNeighborhood(neighborhood);
    this._indexDirty = true;
    return neighborhood;
}
```

Creates a new neighborhood from text, pre-activates all its occurrences (activationCount = 1), and adds it to the conscious episode. This is called when salient content is extracted.

---

## 9. Tokenization

**File:** `dae-core.mjs` lines 502-509

```js
function tokenize(text) {
  return text
    .replace(/[^\w\s']/g, " ") // Replace non-word, non-space, non-apostrophe with space
    .toLowerCase() // Lowercase everything
    .split(/\s+/) // Split on whitespace
    .map((t) => t.replace(/^'+|'+$/g, "")) // Strip leading/trailing apostrophes
    .filter((t) => t.length > 0); // Remove empty strings
}
```

**Notable:** No stop-word removal. No stemming. No lemmatization. The IDF weighting naturally down-weights common words. Apostrophes are preserved inside words (e.g., "don't" stays as "don't").

---

## 10. Ingestion

**File:** `dae-core.mjs` lines 515-529

```js
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

**Algorithm:**

1. Split text into sentences using lookbehind regex `(?<=[.!?])\s+`.
2. Group into chunks of 3 sentences each.
3. Each chunk becomes one Neighborhood (tokenized, positioned on S^3).
4. All neighborhoods go into a new Episode.

**No activation happens during ingestion.** Occurrences start with activationCount=0. They are "dormant" until queried.

---

## 11. QueryEngine -- Activation Pipeline

**File:** `dae-core.mjs` lines 535-819

The QueryEngine is a stateless processor that operates on a DAESystem.

### Constructor

```js
class QueryEngine {
  constructor(system) {
    this.system = system;
  }
}
```

### activate(query)

```js
activate(query) {
    const tokens = tokenize(query);
    const uniqueTokens = [...new Set(tokens.map(t => t.toLowerCase()))];
    const result = { subconscious: [], conscious: [] };

    uniqueTokens.forEach(token => {
        const { subconscious, conscious } = this.system.activateWord(token);
        result.subconscious.push(...subconscious);
        result.conscious.push(...conscious);
    });

    return result;
}
```

**Steps:**

1. Tokenize query.
2. Deduplicate tokens (case-insensitive).
3. For each unique token, activate ALL matching occurrences across the entire system.
4. Partition results into subconscious and conscious lists.

### processQuery(query) — The Full Pipeline

```js
processQuery(query) {
    // Step 1: Activate all matching words
    const activation = this.activate(query);

    // Step 2: Compute weight floor for large queries
    const totalNbhd = this.system.episodes.reduce((s, ep) => s + ep.neighborhoods.length, 0)
        + (this.system.consciousEpisode ? this.system.consciousEpisode.neighborhoods.length : 0);
    const queryTokenCount = tokenize(query).length;

    // Step 3: Drift — with pre-filter for large queries
    if (queryTokenCount > 50) {
        const weightFloor = 1 / Math.max(1, Math.floor(totalNbhd * 0.1));
        const driftSub = activation.subconscious.filter(occ =>
            this.system.getWordWeight(occ.word) >= weightFloor
        );
        const driftCon = activation.conscious.filter(occ =>
            this.system.getWordWeight(occ.word) >= weightFloor
        );
        this.driftAndConsolidate(driftSub);
        this.driftAndConsolidate(driftCon);
    } else {
        this.driftAndConsolidate(activation.subconscious);
        this.driftAndConsolidate(activation.conscious);
    }

    // Step 4: Phasor interference
    const interference = this.computeInterference(activation.subconscious, activation.conscious);

    // Step 5: Surface computation
    const surface = this.computeSurface(activation, interference);

    return { activation, interference, surface };
}
```

**Weight floor for large queries (>50 tokens):**

- `weightFloor = 1 / floor(totalNeighborhoods * 0.1)`
- Only words appearing in fewer than 10% of neighborhoods are included in drift.
- Example: 100 neighborhoods -> weightFloor = 1/10 = 0.1 -> words must appear in <= 10 neighborhoods.
- This is a performance optimization: long text activates many common words; filtering them speeds up drift without losing meaningful signal.

---

## 12. SLERP Drift with IDF Weighting

**File:** `dae-core.mjs` lines 554-648

### driftAndConsolidate

```js
driftAndConsolidate(activated) {
    if (activated.length < 2) return;

    // Cache container activations for each neighborhood
    const containerActivations = new Map();
    activated.forEach(occ => {
        if (!containerActivations.has(occ.neighborhoodId)) {
            const neighborhood = this.system.getNeighborhoodForOccurrence(occ);
            containerActivations.set(occ.neighborhoodId, neighborhood ? neighborhood.totalActivation : 0);
        }
    });

    // Layer 1: Pre-filter anchored occurrences (drift rate > 0 means mobile)
    const mobile = activated.filter(occ => {
        const C = containerActivations.get(occ.neighborhoodId) || 0;
        return occ.getDriftRate(C) > 0;
    });

    if (mobile.length < 2) return;

    // Branching: O(n) centroid for large sets, O(n^2) pairwise for small
    if (mobile.length >= 200) {
        this._centroidDrift(mobile, containerActivations);
    } else {
        this._pairwiseDrift(mobile, containerActivations);
    }
}
```

**Pre-filter logic:** Only occurrences with positive drift rate are included. Anchored words (activationCount/containerActivation > 0.5) are excluded entirely.

**Branching threshold:** 200 mobile occurrences. Below that, use precise O(n^2) pairwise. Above, use approximate O(n) centroid.

### Pairwise Drift (O(n^2)) — for small batches < 200

```js
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
                    const weight = t1 / total;  // Meeting point weighted by drift rates
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

**Pairwise drift algorithm, for each pair (occ1, occ2):**

1. Compute effective drift: `t_i = driftRate(C_i) * IDF_weight(word_i)`.
2. Compute meeting point: SLERP from occ1 to occ2 with parameter `weight = t1 / (t1 + t2)`. If occ1 drifts more, the meeting point is closer to occ1.
3. Move each occurrence toward the meeting point by `t_i * 0.5` (THRESHOLD).
4. Also SLERP phasors toward each other by the same factor.

**Key insight:** The IDF weight modulates drift magnitude. Rare words drift more; common words barely move. The THRESHOLD (0.5) halves the drift step — this damps the movement to prevent overshooting.

### Centroid Drift (O(n)) — for large batches >= 200

```js
_centroidDrift(mobile, containerActivations) {
    // Step 1: Compute weighted centroid
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

    // Step 2: For each occurrence, compute leave-one-out centroid and drift toward it
    mobile.forEach((occ, i) => {
        const w = weights[i];
        const remWeight = totalWeight - w;
        if (remWeight < EPSILON) return;

        // Leave-one-out centroid (exclude current occ)
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

**Centroid drift algorithm:**

1. Compute IDF-weighted centroid of all mobile occurrences in R^4.
2. For each occurrence, compute a **leave-one-out** centroid (exclude self from the sum).
3. Normalize the leave-one-out centroid to project it back onto S^3.
4. SLERP the occurrence toward this centroid by `driftRate * IDF_weight * 0.5`.

**Important difference from pairwise:** Centroid drift only moves positions, not phasors. Phasor drift is omitted in the O(n) path.

---

## 13. Phasor Interference

**File:** `dae-core.mjs` lines 650-693

```js
computeInterference(subconscious, conscious) {
    // Group by word
    const subByWord = new Map();
    subconscious.forEach(occ => {
        const w = occ.word.toLowerCase();
        if (!subByWord.has(w)) subByWord.set(w, []);
        subByWord.get(w).push(occ);
    });

    const conByWord = new Map();
    conscious.forEach(occ => {
        const w = occ.word.toLowerCase();
        if (!conByWord.has(w)) conByWord.set(w, []);
        conByWord.get(w).push(occ);
    });

    const results = [];
    const wordGroups = [];

    for (const [word, subOccs] of subByWord) {
        const conOccs = conByWord.get(word);
        if (!conOccs) continue;  // Skip words not in both manifolds

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

    // Apply Kuramoto coupling
    this.applyKuramotoCoupling(wordGroups);
    return results;
}
```

**Interference algorithm (per word that exists in BOTH conscious and subconscious):**

1. Compute the **circular mean** phase of all conscious occurrences of this word: `meanPhase = atan2(mean(sin(theta)), mean(cos(theta)))`.
2. For each subconscious occurrence, compute phase difference from conscious mean (wrapped to [0, pi]).
3. Interference = `cos(diff)`. Range [-1, +1].
   - +1: in phase (constructive) — subconscious memory reinforces conscious attention
   - -1: out of phase (destructive) — contradicts or is irrelevant
   - 0: orthogonal
4. After computing interference, apply Kuramoto coupling to synchronize phases.

**Key:** Interference is only computed for words present in BOTH conscious and subconscious. Words unique to subconscious are treated differently in surface computation (they're "novel").

---

## 14. Kuramoto Model

**File:** `dae-core.mjs` lines 695-735

```js
applyKuramotoCoupling(wordGroups) {
    if (wordGroups.length === 0) return;

    // Coupling constants based on manifold sizes
    const N_con = this.system.consciousEpisode.count || 1;
    const N_sub = Math.max(1, this.system.N - N_con);
    const N_total = this.system.N || 1;

    const K_CON = N_sub / N_total;    // Conscious coupling strength
    const K_SUB = N_con / N_total;    // Subconscious coupling strength
    const TWO_PI = 2 * Math.PI;

    wordGroups.forEach(({ word, subOccs, conOccs }) => {
        const w = this.system.getWordWeight(word);
        const coupling = w * w;  // IDF weight SQUARED

        // Circular mean phases for each manifold
        let sinSumSub = 0, cosSumSub = 0;
        subOccs.forEach(occ => {
            sinSumSub += Math.sin(occ.phasor.theta);
            cosSumSub += Math.cos(occ.phasor.theta);
        });
        const meanPhaseSub = Math.atan2(sinSumSub / subOccs.length, cosSumSub / subOccs.length);

        let sinSumCon = 0, cosSumCon = 0;
        conOccs.forEach(occ => {
            sinSumCon += Math.sin(occ.phasor.theta);
            cosSumCon += Math.cos(occ.phasor.theta);
        });
        const meanPhaseCon = Math.atan2(sinSumCon / conOccs.length, cosSumCon / conOccs.length);

        // Phase difference (wrapped to [-pi, pi])
        let phaseDiff = meanPhaseCon - meanPhaseSub;
        while (phaseDiff > Math.PI) phaseDiff -= TWO_PI;
        while (phaseDiff < -Math.PI) phaseDiff += TWO_PI;

        // Kuramoto phase update
        const sinDiff = Math.sin(phaseDiff);
        const baseDeltaSub = K_CON * coupling * sinDiff;      // Subconscious pulled toward conscious
        const baseDeltaCon = -K_SUB * coupling * sinDiff;     // Conscious pulled toward subconscious (weaker)

        // Apply with plasticity modulation
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

**Kuramoto model — the full equations:**

Given a word `w` present in both manifolds:

```
N_con = total occurrences in conscious episode
N_sub = N_total - N_con
K_CON = N_sub / N_total     (larger manifold couples more strongly TO conscious)
K_SUB = N_con / N_total     (smaller manifold couples more weakly TO subconscious)
coupling = IDF_weight(w)^2   (squared! rare words couple much more strongly)

mean_phase_sub = circular_mean(theta for all subconscious occurrences of w)
mean_phase_con = circular_mean(theta for all conscious occurrences of w)
phaseDiff = wrap_to_pi(mean_phase_con - mean_phase_sub)

delta_sub = +K_CON * coupling * sin(phaseDiff)   (subconscious pulled toward conscious)
delta_con = -K_SUB * coupling * sin(phaseDiff)    (conscious pulled toward subconscious, opposite sign)

For each subconscious occurrence:
    plasticity = 1 / (1 + log(1 + activationCount))
    theta_new = (theta + delta_sub * plasticity) mod 2*pi

For each conscious occurrence:
    plasticity = 1 / (1 + log(1 + activationCount))
    theta_new = (theta + delta_con * plasticity) mod 2*pi
```

**Key properties:**

1. **Asymmetric coupling:** K_CON + K_SUB = 1 always. When conscious is small relative to subconscious, subconscious is pulled MORE toward conscious (K_CON is large). Conscious is pulled LESS toward subconscious (K_SUB is small). This makes conscious attention the "attractor."
2. **IDF squared:** Rare words get coupling proportional to `(1/n)^2`. A word in 2 neighborhoods gets 0.25 coupling. A word in 10 gets 0.01. Common words barely couple.
3. **Plasticity modulation:** Newly activated occurrences (low count) respond strongly. Heavily activated ones barely move. This prevents over-consolidation.
4. **sin(phaseDiff):** Classic Kuramoto — pulls phases together when `|diff| < pi`, pushes apart when `|diff| > pi`. Maximum coupling at pi/2 phase difference. Zero coupling when perfectly in-phase or anti-phase.
5. **Word-aggregated:** Coupling is computed per-word across the two manifolds, not per individual occurrence pair. Mean phases are used.

---

## 15. Surface Computation

**File:** `dae-core.mjs` lines 737-795

```js
computeSurface(activation, interference) {
    const N = this.system.N;
    const fragments = [];
    const vividNeighborhoods = [];
    const vividEpisodes = [];

    // Step 1: Collect subconscious occs with positive interference
    const surfacedOccs = new Set();
    interference.forEach(({ subOcc, interference: intVal }) => {
        if (intVal > 0) surfacedOccs.add(subOcc);
    });

    // Step 2: Also add subconscious occs whose words are NOT in conscious (novel)
    const consciousWords = new Set(activation.conscious.map(o => o.word.toLowerCase()));
    activation.subconscious.forEach(occ => {
        if (!consciousWords.has(occ.word.toLowerCase())) surfacedOccs.add(occ);
    });

    // Step 3: Group by neighborhood
    const neighborhoodActivations = new Map();
    surfacedOccs.forEach(occ => {
        const nid = occ.neighborhoodId;
        if (!neighborhoodActivations.has(nid)) neighborhoodActivations.set(nid, []);
        neighborhoodActivations.get(nid).push(occ);
    });

    // Step 4: Identify vivid neighborhoods and episodes
    const vividNeighborhoodIds = new Set();
    const vividEpisodeIds = new Set();

    this.system.episodes.forEach(episode => {
        let episodeActivated = 0;
        episode.neighborhoods.forEach(neighborhood => {
            const nActivated = (neighborhoodActivations.get(neighborhood.id) || []).length;
            episodeActivated += nActivated;
            if (neighborhood.count > 0) {
                const nRatio = nActivated / neighborhood.count;
                if (nRatio > THRESHOLD) {      // >50% of neighborhood's words surfaced
                    vividNeighborhoods.push(neighborhood);
                    vividNeighborhoodIds.add(neighborhood.id);
                }
            }
        });
        if (episode.count > 0 && N > 0) {
            const eRatio = episodeActivated / episode.count;
            if (eRatio > THRESHOLD && episode.mass(N) > THRESHOLD) {
                vividEpisodes.push(episode);    // >50% activated AND >50% mass
                vividEpisodeIds.add(episode.id);
            }
        }
    });

    // Step 5: Remaining surfaced occs (not in vivid neighborhoods/episodes) are fragments
    surfacedOccs.forEach(occ => {
        if (!vividNeighborhoodIds.has(occ.neighborhoodId)) {
            const ep = this.system.getEpisodeForOccurrence(occ);
            if (!ep || !vividEpisodeIds.has(ep.id)) {
                fragments.push(occ);
            }
        }
    });

    return { fragments, vividNeighborhoods, vividEpisodes };
}
```

**Surface computation — what "surfaces" from subconscious to conscious attention:**

1. **Positive interference:** Subconscious occurrences whose phasors are constructively interfering (cos > 0) with the conscious mean phase for the same word.
2. **Novel words:** Subconscious occurrences of words NOT present in conscious at all. These represent novel connections.
3. **Vivid neighborhoods:** Neighborhoods where >50% of occurrences surfaced. These represent coherent chunks of memory.
4. **Vivid episodes:** Episodes where >50% of occurrences surfaced AND the episode has >50% of system mass. (This is very hard to achieve — only for massive, highly relevant episodes.)
5. **Fragments:** Surfaced occurrences not in any vivid neighborhood or episode. Isolated memories.

---

## 16. Context Composition

**File:** `dae-core.mjs` lines 826-934

This is the function that builds the text context injected into the LLM prompt.

```js
function composeContext(system, surface, activation, interference) {
    const parts = [];
    let metrics = { conscious: 0, subconscious: 0, novel: 0 };
    const consciousWords = new Set(activation.conscious.map(o => o.word.toLowerCase()));
```

### Step 1: Score Conscious Neighborhoods

```js
const conNeighborhoods = new Map();
activation.conscious.forEach((o) => {
  const w = o.word.toLowerCase();
  const weight = system.getWordWeight(w);
  if (!conNeighborhoods.has(o.neighborhoodId)) {
    const neighborhood = system.getNeighborhoodForOccurrence(o);
    if (neighborhood) {
      conNeighborhoods.set(o.neighborhoodId, {
        neighborhood,
        score: 0,
        words: new Set(),
        activatedCount: 0,
      });
    }
  }
  if (conNeighborhoods.has(o.neighborhoodId)) {
    const entry = conNeighborhoods.get(o.neighborhoodId);
    entry.score += weight * o.activationCount;
    entry.words.add(w);
    entry.activatedCount++;
  }
});
```

**Scoring:** `score = sum(IDF_weight * activationCount)` for each activated occurrence in the neighborhood.

### Step 2: Score Subconscious Neighborhoods

```js
const subNeighborhoods = new Map();
activation.subconscious.forEach((o) => {
  const w = o.word.toLowerCase();
  const weight = system.getWordWeight(w);
  const ep = system.getEpisodeForOccurrence(o);
  if (!subNeighborhoods.has(o.neighborhoodId)) {
    const neighborhood = system.getNeighborhoodForOccurrence(o);
    if (neighborhood && ep) {
      subNeighborhoods.set(o.neighborhoodId, {
        neighborhood,
        episode: ep,
        score: 0,
        words: new Set(),
        activatedCount: 0,
        maxWordWeight: 0,
        maxPlasticity: 0,
      });
    }
  }
  if (subNeighborhoods.has(o.neighborhoodId)) {
    const entry = subNeighborhoods.get(o.neighborhoodId);
    entry.score += weight * o.activationCount;
    entry.words.add(w);
    entry.activatedCount++;
    const plasticity = 1 / (1 + Math.log(1 + o.activationCount));
    if (weight > entry.maxWordWeight) entry.maxWordWeight = weight;
    if (plasticity > entry.maxPlasticity) entry.maxPlasticity = plasticity;
  }
});
```

Additionally tracks `maxWordWeight` and `maxPlasticity` for novelty scoring.

### Step 3: Select and Format

**CONSCIOUS RECALL:** Top-1 conscious neighborhood by score.

```js
const conRanked = [...conNeighborhoods.values()].sort(
  (a, b) => b.score - a.score,
);
if (conRanked.length > 0) {
  const best = conRanked[0];
  selectedIds.add(best.neighborhood.id);
  const text =
    best.neighborhood.text ||
    best.neighborhood.occurrences.map((o) => o.word).join(" ");
  parts.push("CONSCIOUS RECALL:");
  parts.push("[Source: Previously marked salient]");
  parts.push(`"${text}"`);
  metrics.conscious = 1;
}
```

**SUBCONSCIOUS RECALL:** Top-2 subconscious neighborhoods by score (excluding already-selected).

```js
const subRanked = [...subNeighborhoods.values()]
  .filter((entry) => !selectedIds.has(entry.neighborhood.id))
  .sort((a, b) => b.score - a.score);
subRanked.slice(0, 2).forEach((entry, i) => {
  selectedIds.add(entry.neighborhood.id);
  const text =
    entry.neighborhood.text ||
    entry.neighborhood.occurrences.map((o) => o.word).join(" ");
  const epName = entry.episode.displayName || entry.episode.name || "Memory";
  parts.push(`\nSUBCONSCIOUS RECALL ${i + 1}:`);
  parts.push(`[Source: ${epName}]`);
  parts.push(`"${text}"`);
  metrics.subconscious++;
});
```

**NOVEL CONNECTION:** Top-1 from remaining subconscious neighborhoods with special criteria.

```js
const novelCandidates = [...subNeighborhoods.values()]
  .filter((entry) => {
    if (selectedIds.has(entry.neighborhood.id)) return false;
    if (entry.activatedCount > 2) return false; // Max 2 activated words
    const hasConsciousMatch = [...entry.words].some((w) =>
      consciousWords.has(w),
    );
    if (hasConsciousMatch) return false; // NO words in common with conscious
    return true;
  })
  .map((entry) => ({
    ...entry,
    novelty:
      entry.maxWordWeight * entry.maxPlasticity * (1 / entry.activatedCount),
  }))
  .sort((a, b) => b.novelty - a.novelty);
```

**Novel connection criteria:**

1. Not already selected.
2. At most 2 activated words in the neighborhood (thin connection).
3. NONE of its activated words appear in conscious memory (truly novel bridge).

**Novelty score:** `maxWordWeight * maxPlasticity * (1 / activatedCount)`

- High IDF weight (rare bridging word) increases novelty.
- High plasticity (recently created, few activations) increases novelty.
- Fewer activated words increases novelty (single-word bridges score higher).

### Output Format

The composed context looks like:

```
CONSCIOUS RECALL:
[Source: Previously marked salient]
"<text>"

SUBCONSCIOUS RECALL 1:
[Source: Conversation 3 (2/13/26 4:30 PM)]
"<text>"

SUBCONSCIOUS RECALL 2:
[Source: Document X]
"<text>"

NOVEL CONNECTION:
[Source: Seed: general]
"<text>"

[Activated: 4 neighborhoods | conscious:1 subconscious:2 novel:1]
```

Return value: `{ context: string, metrics: { conscious: number, subconscious: number, novel: number } }`

---

## 17. Salient Extraction

**File:** `dae-core.mjs` lines 965-969

```js
function extractSalient(system, text) {
  const m = text.match(/<salient>(.*?)<\/salient>/gs);
  if (m)
    m.forEach((s) => system.addToConscious(s.replace(/<\/?salient>/g, "")));
  return m ? m.length : 0;
}
```

Regex extracts all `<salient>...</salient>` blocks (supports dotall via `s` flag — content can span lines). Each extracted block is stripped of tags and added to the conscious episode via `addToConscious()`. Returns the count of salient blocks found.

---

## 18. System Prompt

**File:** `dae-core.mjs` lines 940-959

```js
const DAE_SYSTEM_PROMPT = (
  context,
) => `You have a persistent memory system called DAE...

WHAT YOU'LL SEE:
CONSCIOUS RECALL — Text you previously marked as important...
SUBCONSCIOUS RECALL — Text from past conversations...
NOVEL CONNECTION — Text surfaced through a single unexpected word bridge...

HOW TO USE MEMORIES:
- Reference and build on surfaced content naturally...
- Absence of a recall type means nothing matched...

MARKING MEMORIES:
When you produce a genuine insight... wrap it in <salient>content</salient> tags...

CRITICAL: If any recall section... is absent from your context below, it does not exist...

${context}`;
```

A template function that takes the composed context string and wraps it in instructions for the LLM.

---

## 19. Server API Layer

**File:** `dae-server.mjs`

### Configuration (Environment Variables)

| Variable            | Default        | Description                                    |
| ------------------- | -------------- | ---------------------------------------------- |
| `DAE_PORT`          | `7777`         | HTTP port                                      |
| `DAE_BIND`          | `0.0.0.0`      | Bind address (0.0.0.0 for Docker reachability) |
| `DAE_STATE_DIR`     | `./.dae-state` | Directory for state persistence                |
| `EPISODE_THRESHOLD` | `5`            | Exchanges before creating a new episode        |
| `DAE_AGENT_NAME`    | `dae-agent`    | Agent name stored in metadata                  |

### Endpoints

#### POST /query

**Input:** `{ "text": "user message" }`
**Processing:** `queryEngine.processQuery(text)` -> `composeContext(...)` -> returns context
**Output:** `{ "context": string, "metrics": {...}, "stats": {...} }`
**Side effects:** Activates words (increments activation counts), applies drift and interference. Does NOT save state.

**Important detail:** `/query` does NOT save state to disk. The activation and drift happen in memory only. State is saved on `/activate-response`, `/salient`, `/buffer`, and `/ingest`.

#### POST /activate-response

**Input:** `{ "text": "agent response" }`
**Processing:**

1. Activate all words in the response text against the system.
2. Weight-filtered drift: compute `weightFloor = 1 / floor(totalNeighborhoods * 0.1)`, only drift words with IDF weight >= floor.
3. Drift subconscious and conscious separately.
4. Compute interference (Kuramoto coupling).
5. Save state.
   **Output:** `{ "activated": {sub, con}, "drifted": {sub, con}, "stats": {...} }`

#### POST /salient

**Input:** `{ "text": "insight text" }`
**Processing:** Wraps in `<salient>` tags if not already wrapped, extracts, adds to conscious episode. Saves state.
**Output:** `{ "stored": count, "conscious": neighborhood_count, "stats": {...} }`

#### POST /buffer

**Input:** `{ "user": "...", "assistant": "..." }`
**Processing:**

1. Appends `[user, assistant]` pair to `conversationBuffer` array.
2. Increments `meta.totalExchanges`.
3. If buffer length >= `EPISODE_THRESHOLD`:
   - Creates new Episode named `"Conversation N"`.
   - Each buffered exchange becomes one Neighborhood (user + assistant combined).
   - Adds episode to system.
   - Clears buffer.
4. Saves state.
   **Output:** `{ "bufferSize": number, "episodeCreated": name|null, "stats": {...} }`

#### POST /ingest

**Input:** `{ "text": "document content", "name": "optional name" }`
**Processing:** Calls `ingestText(text, name)` which splits into 3-sentence chunks. Adds episode. Saves state.
**Output:** `{ "episode": name, "neighborhoods": count, "occurrences": count, "stats": {...} }`

#### POST /import

**Input:** Full DAE state JSON with `system` field.
**Processing:** Deserializes via `DAESystem.fromJSON()`, replaces in-memory state. Saves.
**Output:** `{ "imported": true, "stats": {...} }`

#### GET /export

**Output:** Full state JSON: `{ "version": "0.7.2", "timestamp": ..., "system": {...}, "conversationBuffer": [...], "meta": {...} }`

#### GET /stats

**Output:** `{ "N": number, "episodes": number, "conscious": number, "agentName": string, "totalExchanges": number, "bufferSize": number }`

### State Persistence Strategy

- State is saved to `STATE_DIR/dae-state.json` (the full system) and `STATE_DIR/meta.json` (exchange count).
- State is saved after every mutating operation (activate-response, salient, buffer, ingest, import).
- State is NOT saved after `/query` (read-only in terms of disk, but mutates in-memory activation counts and positions via drift).
- On startup, loads from disk if exists, otherwise initializes fresh.
- On SIGINT/SIGTERM, saves state before exiting.

**Observation:** There is an asymmetry here. `/query` mutates in-memory state (activations, drift, interference) but doesn't persist. If the server crashes after a `/query` but before `/activate-response` or `/buffer`, those activations are lost. This seems intentional — the query-phase mutations are "tentative" until the response cycle completes.

### Server Infrastructure

- Pure Node.js `http.createServer` — zero dependencies.
- CORS enabled for all origins.
- Route matching: `"METHOD /path"` string lookup.
- JSON request body parsing via manual chunk collection.
- Graceful shutdown on SIGINT/SIGTERM.

---

## 20. Agent Integration (moltbook-agent.mjs)

### Purpose

A standalone autonomous agent that:

1. Polls a Moltbook instance for new posts/replies.
2. Queries DAE for memory context.
3. Calls an LLM to generate a response.
4. Posts the response back to Moltbook.
5. Processes the response through DAE (activation, drift, Kuramoto, salient extraction).
6. Manages episode creation from conversation buffer.

### Two Modes

1. **Seed mode** (`--seed`): Read-only ingestion of existing Moltbook posts. No LLM calls. Fetches posts + comments from configured submolts and ingests them as episodes.
2. **Agent mode** (default): Full read-respond loop with LLM calls.

### Configuration (Additional to Server)

| Variable              | Default                           | Description                          |
| --------------------- | --------------------------------- | ------------------------------------ |
| `MOLTBOOK_API_URL`    | `https://www.moltbook.com/api/v1` | Moltbook API base                    |
| `MOLTBOOK_API_KEY`    | required                          | Moltbook auth                        |
| `LLM_PROVIDER`        | `claude`                          | One of: claude, openai, grok, gemini |
| `LLM_API_KEY`         | required (agent mode)             | LLM auth                             |
| `LLM_MODEL`           | per-provider default              | Model override                       |
| `POLL_INTERVAL_MS`    | `30000`                           | Poll interval (30s)                  |
| `HEARTBEAT_EVERY`     | `50`                              | Heartbeat log every N polls          |
| `CONVERSATION_WINDOW` | `5`                               | Number of exchanges in LLM context   |
| `MAX_RESPONSE_LEN`    | `2000`                            | Max tokens in LLM response           |
| `MOLTBOOK_SUBMOLT`    | `general`                         | Default submolt to monitor           |

### Default LLM Models

```js
const DEFAULT_MODELS = {
  claude: "claude-sonnet-4-20250514",
  openai: "gpt-4o",
  grok: "grok-3",
  gemini: "gemini-2.0-flash",
};
```

### LLM Adapters

Four adapters with identical interface: `{ endpoint, headers(), body(messages, systemPrompt), parse(data) }`.

- **Claude:** Uses `x-api-key` header, `anthropic-version: 2023-06-01`, separate `system` field.
- **OpenAI:** Uses `Authorization: Bearer`, prepends system message to messages array.
- **Grok:** Same as OpenAI but different endpoint (api.x.ai).
- **Gemini:** Uses API key in URL (!), maps roles (`assistant` -> `model`), uses `system_instruction` field.

All adapters redact API keys from error messages.

### Turn Flow (Agent Mode)

```
1. Poll Moltbook for new posts + notifications
2. For each interaction:
   a. processExchange(system, queryEngine, query, conversationHistory)
      - queryEngine.processQuery(query)        // activate, drift, interfere
      - composeContext(...)                      // build memory context string
      - DAE_SYSTEM_PROMPT(context)             // wrap in system prompt
      - Slice conversationHistory to window     // last N*2 messages
   b. callLLM(messages, systemPrompt)           // get response
   c. processResponse(system, queryEngine, reply)
      - extractSalient(system, reply)           // <salient> tags -> conscious
      - queryEngine.activate(reply)             // activate response words
      - Weight-filtered drift                   // IDF floor filter
      - queryEngine.computeInterference(...)    // Kuramoto coupling
   d. Update conversationHistory
   e. Append to conversationBuffer
   f. If buffer >= threshold: create episode
   g. Post reply to Moltbook
   h. Save state
3. Update meta.lastPollTime
4. Wait POLL_INTERVAL_MS, repeat
```

### Seed Mode

```
1. For each submolt in --seed-submolts (or CONFIG.submolt):
   a. Create Episode("Seed: submoltName")
   b. For each page (up to --seed-pages, default 5):
      - Fetch posts
      - For each post: tokenize(title + body) -> Neighborhood -> add to episode
      - For each post's comments: tokenize(comment) -> Neighborhood -> add to episode
   c. Add episode to system
2. Save state
3. Exit (no agent loop)
```

### Additional Logic Beyond dae-core

1. **Conversation window management:** Slices `conversationHistory` to last `CONVERSATION_WINDOW * 2` messages for LLM context.
2. **Salient tag stripping from Moltbook posts:** `cleanReply()` removes `<salient>` tags before posting to Moltbook (they're internal DAE markers, not for display).
3. **Heartbeat logging:** Every N polls, logs system stats.
4. **Deduplication:** Filters out interactions from the agent's own name.
5. **Graceful shutdown:** Saves state on SIGINT/SIGTERM.

---

## 21. State Serialization

### Wire Format (dae-state.json)

```json
{
    "version": "0.7.2",
    "timestamp": "2026-02-13T...",
    "system": {
        "episodes": [
            {
                "name": "Conversation 1",
                "isConscious": false,
                "id": "uuid",
                "timestamp": "iso-8601",
                "neighborhoods": [
                    {
                        "seed": [w, x, y, z],
                        "id": "uuid",
                        "sourceText": "original text",
                        "occurrences": [
                            {
                                "word": "token",
                                "position": [w, x, y, z],
                                "phasor": 1.234,
                                "activationCount": 5,
                                "neighborhoodId": "uuid"
                            }
                        ]
                    }
                ]
            }
        ],
        "consciousEpisode": { /* same structure, isConscious: true */ },
        "N": 27669,
        "totalActivation": 12345,
        "agentName": "dae-agent"
    },
    "conversationBuffer": [["user msg", "assistant msg"], ...],
    "conversationHistory": [{"role": "user", "content": "..."}, ...]
}
```

### Deserialization Chain

```
JSON -> DAESystem.fromJSON(data.system)
  -> data.episodes.map(Episode.fromJSON)
    -> data.neighborhoods.map(Neighborhood.fromJSON)
      -> data.occurrences.map(Occurrence.fromJSON)
        -> Quaternion.fromArray(data.position)
        -> new DaemonPhasor(data.phasor ?? data.theta ?? 0)  // backward compat
```

**Backward compatibility:** `Occurrence.fromJSON` accepts both `phasor` and `theta` field names for the phasor angle.

### import-state.mjs

CLI utility that:

1. Reads a JSON file (browser export or another agent's export).
2. Validates structure (must have `system.episodes` or `system.consciousEpisode`).
3. Test-deserializes via `DAESystem.fromJSON()`.
4. Writes to `STATE_DIR/dae-state.json` and `STATE_DIR/meta.json` (with reset meta).

---

## 22. Complete Export List

From `dae-core.mjs`:

```js
export {
  // Constants
  PHI,
  GOLDEN_ANGLE,
  NEIGHBORHOOD_RADIUS,
  THRESHOLD,
  M,
  EPSILON,
  // Classes
  Quaternion,
  DaemonPhasor,
  Occurrence,
  Neighborhood,
  Episode,
  DAESystem,
  QueryEngine,
  // Functions
  tokenize,
  ingestText,
  composeContext,
  extractSalient,
  DAE_SYSTEM_PROMPT,
};
```

**Not exported:** `gaussRandom()` (internal helper).

---

## 23. Differences from Browser Standalone

Based on code structure and comments:

1. **No WebGPU / GPU acceleration.** All computation is CPU-only JavaScript. The browser standalone likely has (or planned) WebGPU compute shaders for parallel drift/interference.

2. **No visualization.** No 3D rendering of the S^3 manifold. The browser version likely renders quaternion positions as a point cloud.

3. **No `crypto.randomUUID` polyfill needed.** Node 18+ has it natively. Browser version may have needed a polyfill or used a different UUID strategy.

4. **State persistence is file-based.** Browser version likely uses localStorage or IndexedDB. Server uses `writeFileSync` to `.dae-state/`.

5. **HTTP API layer.** Browser version was a single HTML file with embedded JavaScript. Server version separates concerns into HTTP endpoints.

6. **Conversation buffer and episode threshold.** The server version has a `conversationBuffer` that accumulates exchanges and creates episodes at a threshold (default 5). The browser version may have managed this differently (e.g., per-session, per-page-refresh).

7. **No `Neighborhood.driftAll()` usage.** This method exists on the Neighborhood class (drifts all occurrences toward the first occurrence) but is never called in the server pipeline. The server only uses `QueryEngine.driftAndConsolidate()` for cross-neighborhood drift. `driftAll()` may have been used in the browser version for intra-neighborhood consolidation.

8. **No `Occurrence.isAnchored()` direct usage.** The method exists but anchoring is handled implicitly via `getDriftRate()` returning 0.

9. **No `Quaternion.geodesicDistance()` usage.** The method exists but is never called. May have been used in the browser version for distance-based filtering or visualization.

10. **Agent name stored on DAESystem.** Server version stores `agentName` on the system object and in metadata. Browser version likely did not need this.

11. **Backward compatibility in deserialization.** `Occurrence.fromJSON` accepts `data.phasor ?? data.theta ?? 0` — suggesting an older format used `theta` as the field name. The server version handles both.

---

## 24. Rust Module Mapping

Suggested Rust module structure based on the JavaScript architecture:

```
dae-core/
  src/
    lib.rs              // Re-exports
    constants.rs        // PHI, GOLDEN_ANGLE, NEIGHBORHOOD_RADIUS, THRESHOLD, M, EPSILON
    quaternion.rs       // Quaternion struct + impl (normalize, dot, random, randomNear, geodesicDistance, slerp)
    phasor.rs           // DaemonPhasor struct + impl (fromIndex, interference, slerp)
    occurrence.rs       // Occurrence struct + impl (activate, driftRate, plasticity, isAnchored, mass, driftToward)
    neighborhood.rs     // Neighborhood struct + impl (fromTokens, activateWord, isVivid, driftAll, mass)
    episode.rs          // Episode struct + impl (addNeighborhood, activateWord, isVivid, mass, allOccurrences)
    system.rs           // DAESystem struct + impl (indexes, activateWord, getWordWeight, addToConscious)
    tokenizer.rs        // tokenize()
    ingest.rs           // ingestText()
    query_engine.rs     // QueryEngine (activate, driftAndConsolidate, computeInterference, applyKuramotoCoupling, computeSurface, processQuery)
    context.rs          // composeContext()
    salient.rs          // extractSalient()
    serde.rs            // Serialization/deserialization (JSON wire format)

dae-server/
  src/
    main.rs             // HTTP server (axum/actix-web)
    routes.rs           // Endpoint handlers
    state.rs            // File-based persistence
    config.rs           // Environment configuration
```

### Rust-Specific Considerations

1. **Quaternion** should be `#[derive(Clone, Copy)]` — small struct, passed by value. Consider using `f64` (JS `Number` is f64). Alternatively `f32` if memory/SIMD matters.

2. **Random number generation:** Replace `Math.random()` with `rand` crate. `gaussRandom()` can use `rand_distr::StandardNormal`.

3. **UUID generation:** Use `uuid` crate.

4. **Indexes:** The `_wordNeighborhoodIndex` (word -> Set<ID>) and `_wordOccurrenceIndex` (word -> Vec<&Occurrence>) should be `HashMap<String, HashSet<Uuid>>` and `HashMap<String, Vec<usize>>` (with occurrence indices rather than references to avoid borrow checker issues).

5. **Occurrence graph:** Occurrences are mutated in place during drift and Kuramoto. Consider using a flat `Vec<Occurrence>` with index-based references rather than object references. An ECS-like approach (separate arrays for positions, phasors, activation counts) would enable SIMD.

6. **SLERP:** Can leverage `glam` crate's quaternion SLERP, but verify it handles the antipodal flip and near-parallel NLERP fallback.

7. **Phasor SLERP:** Trivial — just angle interpolation with wrapping. No external dependency needed.

8. **Serialization:** `serde` + `serde_json` for the wire format. Ensure backward compatibility with `theta` field name via `#[serde(alias)]`.

9. **The centroid drift** computes in R^4 then projects back to S^3 — straightforward numerics, no special Rust considerations.

10. **Performance hot path:** `driftAndConsolidate` (especially pairwise O(n^2)) and `applyKuramotoCoupling` are the most compute-intensive. These are excellent candidates for SIMD (packed quaternion operations) and parallelization (rayon for the pairwise loop).

11. **Circular mean:** `atan2(mean(sin), mean(cos))` — standard trig, no special handling needed.

12. **Regex for salient extraction:** Use `regex` crate with `(?s)` flag for dotall.

13. **The `processQuery` pipeline is inherently sequential:** activate -> drift -> interfere -> surface -> compose. No parallelism opportunity between stages, but each stage can be internally parallelized.

---

## Appendix: All Mathematical Formulas in One Place

### Constants

```
PHI = (1 + sqrt(5)) / 2 = 1.618033988749895
GOLDEN_ANGLE = 2*pi / PHI^2 = 2.3999632297286533 rad = 137.50776405003785 deg
NEIGHBORHOOD_RADIUS = pi / PHI = 1.9416135460476878 rad = 111.24611797498106 deg
THRESHOLD = 0.5
M = 1
EPSILON = 1e-10
```

### Quaternion Operations

```
normalize(q) = q / |q|   where |q| = sqrt(w^2 + x^2 + y^2 + z^2)
dot(a, b) = a.w*b.w + a.x*b.x + a.y*b.y + a.z*b.z
geodesicDistance(a, b) = 2 * acos(clamp(|dot(a, b)|, -1, 1))
slerp(a, b, t):
    if dot < 0: negate b, dot = -dot
    if dot > 0.9995: NLERP (linear + normalize)
    else: theta = acos(dot), result = sin((1-t)*theta)/sin(theta) * a + sin(t*theta)/sin(theta) * b
Hamilton product (a*b):
    w = a.w*b.w - a.x*b.x - a.y*b.y - a.z*b.z
    x = a.w*b.x + a.x*b.w + a.y*b.z - a.z*b.y
    y = a.w*b.y - a.x*b.z + a.y*b.w + a.z*b.x
    z = a.w*b.z + a.x*b.y - a.y*b.x + a.z*b.w
```

### Phasor Operations

```
fromIndex(i) = i * GOLDEN_ANGLE
interference(a, b) = cos(a.theta - b.theta)
slerp(a, b, t) = a.theta + t * wrap_to_pi(b.theta - a.theta)
circular_mean(thetas) = atan2(mean(sin(thetas)), mean(cos(thetas)))
```

### Occurrence Dynamics

```
plasticity(c) = 1 / (1 + log(1 + c))
driftRate(c, C) = if c/C > 0.5 then 0 else (c/C) / 0.5
mass(c, N) = (c / N) * M
isAnchored(c, C) = c/C > 0.5
```

### IDF Weight

```
weight(word) = 1 / |{neighborhoods containing word}|
```

### Pairwise Drift

```
For mobile occurrences i, j:
    t_i = driftRate(c_i, C_i) * weight(word_i)
    t_j = driftRate(c_j, C_j) * weight(word_j)
    meeting_point = slerp(pos_i, pos_j, t_i / (t_i + t_j))
    pos_i = slerp(pos_i, meeting_point, t_i * 0.5)
    pos_j = slerp(pos_j, meeting_point, t_j * 0.5)
    phasor_i = slerp(phasor_i, phasor_j, t_i * 0.5)
    phasor_j = slerp(phasor_j, phasor_i, t_j * 0.5)
```

### Centroid Drift

```
For each mobile occurrence i:
    centroid = IDF-weighted mean of all other mobile positions (in R^4)
    target = normalize(centroid) (project back to S^3)
    factor = driftRate(c_i, C_i) * weight(word_i) * 0.5
    pos_i = slerp(pos_i, target, factor)
    (no phasor drift in centroid mode)
```

### Kuramoto Phase Coupling

```
For each word w in both manifolds:
    K_CON = N_sub / N_total
    K_SUB = N_con / N_total
    coupling = weight(w)^2
    phaseDiff = wrap_to_pi(mean_phase_con - mean_phase_sub)
    delta_sub = +K_CON * coupling * sin(phaseDiff)
    delta_con = -K_SUB * coupling * sin(phaseDiff)
    For each sub occurrence: theta += delta_sub * plasticity(c)
    For each con occurrence: theta += delta_con * plasticity(c)
```

### Surface Criteria

```
Surfaced occurrence: interference > 0 OR word not in conscious
Vivid neighborhood: activated_count / total_count > 0.5
Vivid episode: activated_count / total_count > 0.5 AND mass > 0.5
Fragment: surfaced but not in any vivid neighborhood or episode
```

### Context Scoring

```
neighborhood_score = sum(weight(word) * activationCount) for activated occurrences
novelty = maxWordWeight * maxPlasticity * (1 / activatedCount)
```

### Selection Limits

```
CONSCIOUS RECALL: top 1 by score
SUBCONSCIOUS RECALL: top 2 by score
NOVEL CONNECTION: top 1 by novelty (max 2 activated words, no conscious word overlap)
```
