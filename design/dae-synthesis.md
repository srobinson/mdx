# DAE Synthesis — Canonical Algorithm Set for Rust Reimplementation

**Source analysis:** `standalone-analysis.md` + `openclaw-analysis.md` + `moltbook-analysis.md`
**Target:** `attention-matters` (Rust)
**Date:** 2026-02-13

---

## Variant Relationship Map

The three repos share a single canonical engine. dae-core.mjs is **byte-identical** across openclaw and moltbook. The standalone HTML embeds its own copy with WebGPU additions.

```
              dae-core.mjs (984 lines) ← CANONICAL ENGINE
              ┌──────────┼──────────┐
              │          │          │
         standalone   openclaw   moltbook
         (browser)   (server)   (agent)
              │          │          │
         dae_v072.html  dae-server  moltbook-agent
         + WebGPU       + HTTP API  + LLM adapters
         + Chat UI      + REST      + Moltbook API
                        + moltbook- + Seed mode
                          agent     + Echo state
                          (copy)
```

**What each variant adds beyond the core:**

| Variant        | Unique Contribution                                                                                                                                                                                                       |
| -------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Standalone** | WebGPU compute shaders (SLERP + interference), browser chat UI, multi-provider LLM adapters (browser-side), import/export via file picker                                                                                 |
| **OpenClaw**   | HTTP server layer, REST API (query/activate-response/salient/buffer/ingest/import/export/stats), SKILL.md for agent discovery, file-based state persistence                                                               |
| **Moltbook**   | Autonomous agent loop, seed mode (bulk ingest from social platform), conversation history persistence in state files, Echo's consciousness (9.1MB portable identity), response-driven manifold modification feedback loop |

---

## Critical Divergences Between Variants

These are not cosmetic — they represent actual behavioral differences.

### 1. Drift Rate Formula (BREAKING DIFFERENCE)

**Standalone:**

```js
getDriftRate(C) {
    drift = 1 - (2 * activationCount / C);
    return Math.max(0, drift);  // Decreases: 1 at c=0, 0 at c=C/2
}
```

**OpenClaw:**

```js
getDriftRate(C) {
    ratio = activationCount / C;
    if (ratio > THRESHOLD) return 0;
    return ratio / THRESHOLD;  // Increases: 0 at c=0, 1 at c=C/2
}
```

**Impact:** These are _inversely related_. Standalone says "fresh words are loose, drift freely." OpenClaw says "more activated words drift more (until anchored)." In practice, activation happens BEFORE drift, so c >= 1 for any activated word — but the magnitude curves are opposite.

**Recommendation for Rust:** OpenClaw's version makes more physical sense — words that have been activated more in this query session have more "energy" to drift. But the standalone's version has charm too (fresh words are impressionable). **Needs a design decision.**

### 2. Quaternion Random Generation

**Standalone:** Marsaglia's method (rejection sampling on two 2D discs)

```js
do { u1,u2 -> s1 } while s1 >= 1;
do { u3,u4 -> s2 } while s2 >= 1;
sqrtTerm = sqrt((1 - s1) / s2);
return (u1, u2, u3*sqrtTerm, u4*sqrtTerm);
```

**OpenClaw:** Shoemake's method (direct parameterization)

```js
((s1 = random()),
  (s2 = random()),
  (t1 = 2 * pi * random()),
  (t2 = 2 * pi * random()));
return (
  sqrt(1 - s1) * sin(t1),
  sqrt(1 - s1) * cos(t1),
  sqrt(s1) * sin(t2),
  sqrt(s1) * cos(t2)
);
```

**Impact:** Both produce uniform distributions on S³. Marsaglia uses rejection (variable runtime), Shoemake is direct (fixed cost). **Use Shoemake for Rust** — deterministic cost, no branching.

### 3. Quaternion Immutability

**Standalone:** Mutates in place (`this.w /= norm` in constructor)
**OpenClaw:** Returns new quaternions (`normalize()` returns new `Quaternion`)

**Recommendation for Rust:** `#[derive(Clone, Copy)]` with value semantics. All operations return new values. Perfect fit for Rust.

### 4. SLERP Near-Parallel Threshold

**Standalone:** `dot > 1 - EPSILON` (1 - 1e-10, extremely tight)
**OpenClaw:** `dot > 0.9995` (much looser NLERP fallback)

**Recommendation for Rust:** Use `0.9995` (OpenClaw). The standalone's threshold is numerically aggressive. Standard practice in game engines and graphics libraries is ~0.9995.

### 5. Hamilton Product

**Standalone:** Explicit `multiply()` method on Quaternion
**OpenClaw:** Inline in `randomNear()` only, no standalone method

**Recommendation for Rust:** Implement `impl Mul<Quaternion> for Quaternion` trait. Clean operator overloading.

### 6. Phasor Interference

**Standalone DaemonPhasor:**

```js
interference(other) {
    let diff = Math.abs(this.theta - other.theta);
    if (diff > Math.PI) diff = 2 * Math.PI - diff;
    return Math.cos(diff);
}
```

**OpenClaw DaemonPhasor:**

```js
interference(other) {
    return Math.cos(this.theta - other.theta);
}
```

**Impact:** OpenClaw's version doesn't wrap — but `cos()` is symmetric and periodic, so `cos(a-b)` = `cos(|a-b|)` = `cos(2π - |a-b|)` when |a-b| > π. Mathematically equivalent! The standalone's wrapping is defensive but unnecessary.

**Recommendation for Rust:** Use the simple `cos(a - b)`. Math handles it.

### 7. WebGPU (Standalone Only)

Two WGSL compute shaders:

- **Batch SLERP:** 4 storage buffers, workgroup 64
- **Batch Interference:** 3 storage buffers, workgroup 64

**Recommendation for Rust:** Use `wgpu` crate. Port WGSL shaders directly (they're already in WGSL). But also consider: Rust's SIMD + rayon may make GPU unnecessary for typical workloads. Benchmark first.

---

## Canonical Algorithm Set

These are identical or near-identical across both variants. This is the ground truth.

### Constants (derived from φ and π)

```
PHI             = (1 + √5) / 2                     = 1.618033988749895
GOLDEN_ANGLE    = 2π / φ²                           = 2.3999632297... rad (137.508°)
NEIGHBORHOOD_RADIUS = π / φ                          = 1.9416135460... rad (111.246°)
THRESHOLD       = 0.5
M               = 1                                  (total system mass)
EPSILON         = 1e-10
```

### Data Hierarchy

```
DAESystem
├── episodes: Vec<Episode>              (subconscious)
│   └── Episode
│       ├── neighborhoods: Vec<Neighborhood>
│       │   └── Neighborhood
│       │       ├── seed: Quaternion
│       │       ├── occurrences: Vec<Occurrence>
│       │       │   └── Occurrence { word, position: Quaternion, phasor: f32, activation_count: u32 }
│       │       └── source_text: String
│       ├── name: String
│       └── is_conscious: false
├── conscious_episode: Episode          (conscious, is_conscious=true)
└── indexes (lazy rebuilt):
    ├── word → Set<NeighborhoodId>      (for IDF weight)
    ├── word → Vec<OccurrenceRef>       (for activation)
    ├── NeighborhoodId → Neighborhood   (for lookup)
    └── NeighborhoodId → Episode        (for conscious/subconscious classification)
```

### Core Pipeline (both variants identical)

```
Query arrives
  │
  ├─ 1. TOKENIZE: lowercase, strip punctuation (keep apostrophes), split whitespace
  │     No stemming. No stop words. IDF handles it.
  │
  ├─ 2. ACTIVATE: For each unique token, increment activationCount on all matching occurrences
  │     O(1) per word via index. Split results into {subconscious, conscious}.
  │
  ├─ 3. DRIFT: Activated mobile occurrences SLERP toward each other within each manifold
  │     ├─ Pre-filter: skip anchored (driftRate == 0)
  │     ├─ Weight floor for large queries (>50 tokens): 1/floor(totalNbhd * 0.1)
  │     ├─ < 200 mobile: PAIRWISE O(n²)
  │     │   ├─ t_i = driftRate(c_i, C_i) * IDF(word_i)
  │     │   ├─ meeting = slerp(pos_i, pos_j, t_i / (t_i + t_j))
  │     │   ├─ pos_i = slerp(pos_i, meeting, t_i * 0.5)
  │     │   └─ phasor_i = slerp(phasor_i, phasor_j, t_i * 0.5)
  │     └─ >= 200 mobile: CENTROID O(n)
  │         ├─ centroid = IDF-weighted mean in R⁴
  │         ├─ target_i = normalize((centroid - self_i*w_i) / (totalW - w_i))
  │         ├─ pos_i = slerp(pos_i, target_i, driftRate * w_i * 0.5)
  │         └─ NO phasor drift in centroid mode
  │
  ├─ 4. INTERFERENCE: For words in BOTH manifolds
  │     ├─ Circular mean of conscious phases: atan2(mean(sin), mean(cos))
  │     ├─ Per sub-occurrence: interference = cos(theta_sub - meanConPhase)
  │     └─ Positive = surfaces, Negative = suppressed
  │
  ├─ 5. KURAMOTO COUPLING: Cross-manifold phase synchronization
  │     ├─ K_CON = N_sub / N_total (subconscious pulled toward conscious)
  │     ├─ K_SUB = N_con / N_total (conscious pulled toward subconscious)
  │     ├─ K_CON + K_SUB = 1 always
  │     ├─ coupling = IDF(word)²
  │     ├─ delta_sub = +K_CON * coupling * sin(phaseDiff)
  │     ├─ delta_con = -K_SUB * coupling * sin(phaseDiff)
  │     └─ Per occurrence: theta += delta * plasticity(activationCount)
  │
  ├─ 6. SURFACE: Determine what "surfaces" from subconscious
  │     ├─ Positive interference → surfaced
  │     ├─ Novel words (not in conscious) → surfaced
  │     ├─ Vivid neighborhood: >50% occurrences surfaced
  │     ├─ Vivid episode: >50% activated AND >50% mass (very rare)
  │     └─ Fragments: surfaced but not vivid
  │
  └─ 7. COMPOSE CONTEXT:
        ├─ Score neighborhoods: sum(IDF * activationCount) per activated occurrence
        ├─ CONSCIOUS RECALL: top 1 conscious by score
        ├─ SUBCONSCIOUS RECALL: top 2 subconscious by score
        └─ NOVEL CONNECTION: top 1 by novelty score
            ├─ novelty = maxWordWeight * maxPlasticity * (1/activatedCount)
            ├─ max 2 activated words
            └─ NO conscious word overlap
```

### Response Pipeline (after LLM responds)

```
Response arrives
  │
  ├─ 1. EXTRACT SALIENT: regex /<salient>(.*?)<\/salient>/gs
  │     → Add to conscious episode, pre-activate once
  │
  ├─ 2. ACTIVATE response text (same as query activation)
  │
  ├─ 3. WEIGHT-FILTERED DRIFT (same weight floor logic)
  │
  ├─ 4. INTERFERENCE + KURAMOTO on response activation
  │
  ├─ 5. BUFFER exchange {user, assistant}
  │     → Every N exchanges (default 5), create new subconscious episode
  │
  └─ 6. PERSIST state
```

### Key Formulas (Canonical)

```
Plasticity:     1 / (1 + ln(1 + c))
IDF Weight:     1 / |{neighborhoods containing word}|
Mass:           count / N  (N = total system occurrences)
Neighborhood score: Σ(IDF(word) × activationCount) for activated occurrences
Novelty:        maxWordWeight × maxPlasticity × (1 / activatedCount)
```

---

## Rust Architecture Proposal

### Crate Structure

```
attention-matters/
├── Cargo.toml                 (workspace)
├── crates/
│   ├── am-core/               (pure math, zero deps except rand/uuid)
│   │   ├── constants.rs
│   │   ├── quaternion.rs      (#[derive(Clone, Copy)], impl Mul, SLERP, random)
│   │   ├── phasor.rs          (newtype over f64, golden-angle spacing)
│   │   ├── occurrence.rs      (word + position + phasor + activation)
│   │   ├── neighborhood.rs    (seed + occurrences, fromTokens factory)
│   │   ├── episode.rs         (conscious/subconscious container)
│   │   ├── system.rs          (DAESystem + indexes)
│   │   ├── tokenizer.rs       (regex-based, preserve apostrophes)
│   │   ├── engine.rs          (activate, drift, interfere, kuramoto, surface)
│   │   ├── context.rs         (compose context string)
│   │   └── serde.rs           (JSON wire format, backward compat with v0.7.2)
│   │
│   ├── am-server/             (HTTP API — replaces dae-server.mjs)
│   │   ├── main.rs
│   │   ├── routes.rs          (query, activate-response, salient, buffer, ingest, export, import, stats)
│   │   ├── state.rs           (file persistence + conversation history)
│   │   └── config.rs          (env vars)
│   │
│   ├── am-agent/              (autonomous agent — replaces moltbook-agent.mjs)
│   │   ├── main.rs            (CLI: run / seed subcommands)
│   │   ├── agent.rs           (poll → query DAE → LLM → process response loop)
│   │   ├── llm/
│   │   │   ├── mod.rs         (LlmProvider trait)
│   │   │   ├── claude.rs
│   │   │   ├── openai.rs
│   │   │   ├── grok.rs
│   │   │   └── gemini.rs
│   │   ├── platform/
│   │   │   ├── mod.rs         (SocialPlatform trait)
│   │   │   └── moltbook.rs
│   │   ├── seed.rs            (bulk ingest from platform)
│   │   └── config.rs
│   │
│   └── am-gpu/                (optional, wgpu acceleration)
│       ├── shaders/
│       │   ├── slerp.wgsl
│       │   └── interference.wgsl
│       ├── compute.rs
│       └── lib.rs
│
├── tests/                     (integration tests)
│   ├── golden_tests.rs        (verify against JS reference outputs)
│   └── property_tests.rs      (quaternion invariants, SLERP properties)
│
└── benches/                   (criterion benchmarks)
    ├── drift.rs
    ├── slerp.rs
    └── kuramoto.rs
```

### Key Rust Design Decisions

| Decision           | Choice                                      | Why                                                                  |
| ------------------ | ------------------------------------------- | -------------------------------------------------------------------- |
| Float type         | `f64`                                       | JS Number is f64; preserves numerical compatibility for golden tests |
| Quaternion         | `#[derive(Clone, Copy)]` struct             | Small (32 bytes), passed by value, no allocations                    |
| Occurrence storage | Flat `Vec<Occurrence>` + index refs         | Avoids Rc/RefCell, borrow-checker friendly                           |
| Indexes            | `HashMap<String, Vec<usize>>`               | Index into occurrence vec, not references                            |
| Random             | `rand` crate + `rand_distr::StandardNormal` | Replaces Box-Muller and Marsaglia                                    |
| UUID               | `uuid` crate v1                             | Standard                                                             |
| JSON               | `serde` + `serde_json`                      | With `#[serde(alias = "theta")]` for backward compat                 |
| HTTP               | `axum`                                      | Modern, tokio-native, good ergonomics                                |
| Regex              | `regex` crate                               | For tokenizer and salient extraction                                 |
| SIMD potential     | SoA layout for hot paths                    | Positions as `[f64; 4]` arrays, batch SLERP with packed ops          |
| Parallelism        | `rayon` for pairwise drift                  | The O(n²) loop is embarrassingly parallel                            |

### Numerical Compatibility Strategy

To validate the Rust port against the JS reference:

1. Export a DAE state JSON from the JS version
2. Import into Rust
3. Run identical query
4. Compare: activation counts, drift positions (within ε), interference values, surfaced neighborhoods, composed context

The deterministic parts (activation, interference, Kuramoto, scoring) should match exactly.
The non-deterministic parts (random positioning, initial quaternions) won't match — but properties should hold.

---

## Open Questions for Stuart

1. **Drift rate formula:** Standalone (1 - 2c/C) vs OpenClaw (2c/C). Which behavior? Or new formula?
2. **GPU support:** Include `am-gpu` crate from the start, or defer? SIMD + rayon may suffice.
3. **API compatibility:** Match the OpenClaw HTTP API exactly, or redesign?
4. **State format:** Full backward compatibility with v0.7.2 JSON, or fresh format? Echo's 9.1MB state is a real-world stress test.
5. **Scope:** Core + server + agent? Or start with core only and layer up?
6. **Agent generalization:** The moltbook agent is Moltbook-specific. Do we want `SocialPlatform` trait from the start for pluggable backends, or just port moltbook and generalize later?
7. **Seed mode:** First-class CLI subcommand (`am-agent seed --platform moltbook --pages 5`)? Or keep it a runtime flag?
8. **Conversation history:** Always persist in state files (moltbook approach) or let the caller manage it (openclaw approach)?
