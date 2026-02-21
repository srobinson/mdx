# am-core Math Engine Review

**Date:** 2026-03-13
**Scope:** `/Users/alphab/Dev/LLM/DEV/helioy/attention-matters/crates/am-core/`
**Version:** 0.1.15

---

## Summary

am-core is a well-structured pure-math crate implementing the DAE geometric memory system. All 164 unit tests and 7 integration tests pass. The math primitives are correct and convention-compliant. The primary architectural concern is `compose.rs` at 2959 LOC — it has grown into a god-module. Several numeric precision issues and one correctness bug (geodesic distance formula) warrant attention.

---

## 1. constants.rs

**All constants correctly derived. No magic numbers in the constants file itself.**

Verification:
- `PHI = 1.618033988749895` — correct: (1+√5)/2
- `GOLDEN_ANGLE = 2.3999632297286533` — correct: 2π/φ² = 2π/(φ+1) = 2π·(2/(1+√5))
- `NEIGHBORHOOD_RADIUS = 1.9416135460476878` — correct: π/φ
- `THRESHOLD = 0.5` — architectural constant, clearly named
- `SLERP_THRESHOLD = 0.9995` — matches CLAUDE.md convention
- `EPSILON = 1e-10` — appropriate for f64 unit quaternion operations

GC constants (`ACTIVATION_FLOOR`, `DB_SOFT_LIMIT_BYTES`, etc.) are not math constants but belong here as configuration; acceptable.

**One concern:** `ACTIVATION_FLOOR = 0` means all occurrences are GC candidates. This is intentionally the minimum, but the comment is slightly misleading ("at or below this are candidates"). With FLOOR=0, fresh occurrences are immediately eligible for GC unless protected by the grace window.

---

## 2. quaternion.rs

**SLERP implementation: correct.**

- Antipodal flip on `dot < 0.0`: present and correct (takes shorter arc).
- NLERP fallback at `dot > SLERP_THRESHOLD (0.9995)`: correct, normalized after interpolation.
- NLERP fallback uses linear interpolation, not spherical — this is the documented purpose.

**Bug: `angular_distance` formula.**

```rust
pub fn angular_distance(self, other: Self) -> f64 {
    let d = self.dot(other).abs().clamp(-1.0, 1.0);
    2.0 * d.acos()
}
```

The geodesic distance on S³ between two unit quaternions is `2 * acos(|q₁ · q₂|)`, which equals `acos(2(q₁·q₂)² - 1)`. The formula produces a range of [0, π] not [0, 2π].

However, there is a semantic inconsistency: the formula uses `abs(dot)` which means antipodal quaternions (q and -q) have distance 0. This is correct for rotation space (SO(3)) where q and -q represent the same rotation. The SLERP function, by contrast, does NOT use abs(dot) — it flips sign to take the shorter arc but does not collapse the antipodal pair. So `angular_distance(q, -q) == 0` while `q.slerp(-q, 0.5)` produces a midpoint. This is geometrically consistent for rotation semantics but may confuse users who expect S³ manifold distance.

For the neighborhood radius check in tests (`dist <= NEIGHBORHOOD_RADIUS + 0.01`), this works because `NEIGHBORHOOD_RADIUS = π/φ ≈ 1.94 < π`, meaning no antipodal confusion occurs in practice at those distances.

**Hamilton product: correct.** Standard quaternion multiplication formula verified against the reference.

**Shoemake random quaternion generation: correct.**
- Three uniform random numbers s1, t1, t2
- r1 = sqrt(1-s1), r2 = sqrt(s1)
- This is Shoemake's algorithm for uniform distribution on S³

**random_near: correct but has a subtle distribution issue.**
- Uses Gaussian-distributed axis (Box-Muller) + sqrt-corrected angle for uniform spherical cap area distribution.
- The sqrt correction for uniform area is correct for 2-sphere caps. On S³ the exact correction differs, but sqrt is a reasonable approximation.
- Clamping u1 away from zero in `gauss_random` prevents ln(0) — correct defensive coding.

**Test coverage for quaternion.rs: thorough.**
- Identity, normalize, dot, angular distance, SLERP endpoints, SLERP midpoint equidistance, SLERP identity property, SLERP near-parallel NLERP fallback, SLERP antipodal flip, Hamilton product identity and associativity, array roundtrip, random unit property, random_near within radius.
- Missing: test that `random_near` produces uniform distribution (statistical test). Missing: test that Hamilton product is non-commutative.

---

## 3. phasor.rs

**Correct implementation.**

- `rem_euclid(TAU)` for normalization to [0, 2π) — correct.
- Interference as `cos(θ_self - θ_other)` — standard phase interference metric.
- Circular SLERP uses iterative wrap to [-π, π] before interpolation — correct but see note below.

**Minor: circular SLERP uses while loops for wrap-around.**

```rust
while diff > std::f64::consts::PI {
    diff -= std::f64::consts::TAU;
}
while diff < -std::f64::consts::PI {
    diff += std::f64::consts::TAU;
}
```

This is correct but idiomatic Rust would use `rem_euclid` or a single `((diff + PI).rem_euclid(TAU)) - PI` expression. The while loops are technically fine — `diff` is bounded to one TAU wrap due to prior normalization.

**Kuramoto phase_diff wrapping in query.rs also uses while loops** — same pattern throughout the codebase. Consistent but not idiomatic.

**Test coverage for phasor.rs: complete.**
- Normalization, golden-angle spacing, in-phase/anti-phase/orthogonal interference, SLERP endpoints, shortest-arc SLERP, golden-angle separation property.

---

## 4. occurrence.rs

**Data model: clean.**

Fields: `word: String`, `position: Quaternion`, `phasor: DaemonPhasor`, `activation_count: u32`, `id: Uuid`, `neighborhood_id: Uuid`.

Notable: `activation_count` is a `u32` with no overflow protection on `activate()`. At 4 billion activations the counter wraps. For any real-world use case this is fine; adding `saturating_add(1)` would make it bulletproof.

**drift_rate formula: correct per convention.**

```rust
// OpenClaw: ratio / THRESHOLD (2c/C)
pub fn drift_rate(&self, container_activation: u32) -> f64 {
    let ratio = self.activation_count as f64 / container_activation as f64;
    if ratio > THRESHOLD { return 0.0; }
    ratio / THRESHOLD
}
```

CLAUDE.md specifies `ratio / THRESHOLD (2c/C)`. With THRESHOLD=0.5 this gives `(c/C) / 0.5 = 2c/C`. Correct.

**Precision note:** `as f64` cast on `u32` is lossless (u32 max = ~4.3 billion, f64 mantissa has 52 bits = ~4.5 quadrillion integer precision). No precision loss at practical activation counts.

**plasticity formula: correct.**

```
1 / (1 + ln(1 + c))
```

Diminishing returns. At c=0: plasticity=1.0. At c=1: ≈0.591. Consistent with test assertions.

**Test coverage for occurrence.rs: complete.**
- activate, plasticity values, drift_rate edge cases (zero container, below/at/above threshold), is_anchored, mass.

---

## 5. neighborhood.rs

**from_tokens: correct.**

- Random seed quaternion via `Quaternion::random(rng)` or provided.
- Each occurrence placed within NEIGHBORHOOD_RADIUS of seed via `Quaternion::random_near`.
- Phasors assigned via `DaemonPhasor::from_index(i, 0.0)` — golden-angle spacing from base_theta=0.

**is_vivid: uses episode_count as denominator but the parameter name is misleading.**

```rust
pub fn is_vivid(&self, episode_count: usize) -> bool {
    self.count() as f64 > episode_count as f64 * THRESHOLD
}
```

The parameter `episode_count` is actually the total episode occurrence count (as used in `surface.rs`), not the number of episodes. The name should be `total_episode_count` or `episode_occurrence_count`.

**mass formula:** `count / n * M` where n is total system occurrence count. The same `mass()` method signature exists on `Occurrence`, `Neighborhood`, and `Episode` with different interpretations of `n`. The `n` parameter is total system occurrences in some call sites and something else in others — no shared documentation contract.

**Test coverage for neighborhood.rs: good.**

---

## 6. system.rs

**Design: clean lazy-index pattern.**

`OccurrenceRef` uses `usize::MAX` as the sentinel value for conscious episode. This is a sentinel-value anti-pattern — a proper `enum { Conscious, Subconscious(usize) }` would eliminate the sentinel and make the code self-documenting, but the current approach works correctly and is consistent throughout.

**IDF weight formula:**

```rust
1.0 / neighborhoods.len() as f64
```

This is simplified IDF — proportional to inverse document frequency with constant log factor removed. Mathematically it is `1/df` rather than `log(N/df)`. The absence of the log term means rare words get dramatically higher scores than common words (1/1 vs 1/50 is a 50x difference vs log(N) which would be ~4x for N=50). This is an intentional design choice but could produce unexpected behavior when rare words dominate queries.

**Index rebuild: O(N) where N is total occurrences.** For large systems this could become expensive. No incremental update strategy — any mutation marks the entire index dirty. Acceptable for the current scale.

**`add_episode` only assigns epochs to neighborhoods with epoch=0.** This means if a neighborhood has been explicitly assigned epoch=0 (unlikely but possible), it gets a new epoch. The invariant documentation is clear, but it relies on callers following the protocol correctly.

**Test coverage for system.rs: comprehensive.** Covers IDF, activation partitioning, epoch tracking, conscious pre-activation, neighborhood lookup, serde roundtrip, and sync_next_epoch.

---

## 7. query.rs

**QueryEngine is a zero-size stateless struct** — all methods take `&mut DAESystem`. Good design.

**Drift algorithm: pairwise O(n²) for <200 mobile occurrences, centroid O(n) for >=200.**

The threshold of 200 is a magic number embedded in `drift_and_consolidate`. It should be a named constant.

```rust
if mobile.len() >= 200 {
    Self::centroid_drift(system, &mobile, &container_activations);
} else {
    Self::pairwise_drift(system, &mobile, &container_activations);
}
```

**pairwise_drift uses a snapshot-then-apply pattern** to avoid read-after-write. This means all pairs are drifted toward a meeting point computed from the pre-drift positions. Multiple drift deltas for the same occurrence are applied sequentially (not averaged), which means the final position depends on application order. This produces a slight inconsistency — the last delta has less "resistance" than the first. For small sets this is negligible, but it is not a true simultaneous update.

**centroid_drift uses a leave-one-out centroid** — each occurrence drifts toward the centroid of all other mobile occurrences. This avoids self-attraction. Mathematically correct.

**Large query token optimization (>50 tokens):** filters to occurrences with IDF weight above a floor:

```rust
let weight_floor = 1.0 / (total_nbhd as f64 * 0.1).floor().max(1.0);
```

For `total_nbhd=100`, `floor = 10.0`, so `weight_floor = 0.1`. This keeps only words appearing in at most 10% of neighborhoods. The `.floor().max(1.0)` prevents division by zero but produces unintuitive behavior when `total_nbhd < 10` — floor(0.something) = 0, max(1.0) clamps to 1.0, so weight_floor = 1.0 meaning only words in exactly 1 neighborhood pass. This is an implicit edge-case.

**Kuramoto coupling: correct standard model.**

```
Δθ_sub = K_con * w² * sin(θ_con - θ_sub) * plasticity
Δθ_con = -K_sub * w² * sin(θ_con - θ_sub) * plasticity
```

Where `K_con = n_sub/n_total`, `K_sub = n_con/n_total`. The coupling strengths sum to 1 (verified by test). Using `w²` (IDF weight squared) as coupling strength means rare words couple more strongly — a design decision with sound intuition but no derivation comment.

**Interference computation uses circular mean for conscious reference phase.** `atan2(sin_sum/count, cos_sum/count)` — correct circular statistics.

**Test coverage for query.rs: good.** Covers pairwise drift movement, anchored words don't move, interference computation range, Kuramoto constants sum to 1, Kuramoto pulls phases, full pipeline, IDF-weighted drift.

---

## 8. compose.rs — God Module Analysis

**Size: 2959 LOC. This is the largest single file in the codebase by a factor of ~5x.**

`compose.rs` currently contains:

| Responsibility | LOC estimate |
|---|---|
| Context composition (compose_context) | ~120 |
| Budgeted composition (compose_context_budgeted) | ~250 |
| Index composition (compose_index) | ~80 |
| Direct retrieval (retrieve_by_ids) | ~60 |
| Scoring internals (score_neighborhoods, rank_candidates) | ~300 |
| Overlap suppression (overlap_suppress, idf_weighted_overlap) | ~80 |
| Recency decay (parse_days_ago, days_since_episode) | ~50 |
| Salient extraction (extract_salient, mark_salient_typed, detect_neighborhood_type) | ~30 |
| Constants (7 scoring constants) | ~30 |
| Data types (13 structs/enums) | ~80 |
| Tests | ~1680 |

**The test section alone is 1680 lines (56% of the file).**

The tests are excellent — extensive coverage of scoring, budgeting, decisions/preferences, overlap suppression, recency decay, session diminishing returns, two-phase retrieval. But their volume inflates the file size significantly.

**Extraction candidates:**

1. `scoring.rs` — `score_neighborhoods`, `rank_candidates`, `aggregate_interference`, `idf_weighted_overlap`, `overlap_suppress`, `ScoredNeighborhood`, `RankedCandidate`, and the 7 scoring constants. This is a coherent computation unit.

2. `salient.rs` — `extract_salient`, `mark_salient_typed`, `detect_neighborhood_type`, and the `SALIENT_RE` static. These are ingestion-side concerns, not composition concerns.

3. `recency.rs` — `parse_days_ago`, `days_since_episode`, `RECENCY_DECAY_RATE`. Independent utility.

After extraction, `compose.rs` would contain only the public composition functions, data types, and their tests — approximately 700 LOC.

**Is compose.rs a god module?** Yes, in the sense that it mixes scoring logic, content extraction, context formatting, recency computation, and overlap detection. However, all these concerns exist exclusively in service of composition — there is no inappropriate mixing of I/O or state. The extraction above would improve navigability without changing any behavior.

---

## 9. batch.rs

**Amortization strategy: correct.**

The batch engine activates the union of all tokens once, drifts once, then partitions results per query. This is correct because:

1. IDF weights are a read-only property of the `word_neighborhood_index` (which counts neighborhoods, not activations).
2. Activation bumps `activation_count` on occurrences but does NOT modify neighborhood membership.
3. Therefore IDF weights are stable within a batch.

**One correctness concern:** The batch activates the union, meaning an occurrence gets bumped for every query that includes its word, even if a query only partially benefits from it. For a batch of N queries that all share word W, occurrences of W get bumped N times instead of once. This inflates `activation_count` beyond what a single-query call would produce. The comment in the code acknowledges this ("batch of 1 should match direct query fragment count") but does not document the activation inflation behavior.

This could affect `drift_rate` computation — higher `activation_count` may push words across the anchoring threshold sooner than intended. Mitigation: batch queries should be considered writes to the manifold, and callers should not run large batches repeatedly on the same system without understanding this effect.

**`_word_groups` variable naming:** The word groups from the global interference computation are stored in `_word_groups` — the leading underscore indicates the caller intended to suppress the unused-variable warning. The global interference is applied via `apply_kuramoto_coupling`, but the per-query re-computation in step 5 computes interference again per query. So the global interference is computed and then discarded except for the Kuramoto coupling. This is intentional (global coupling, per-query scoring) but could use a comment.

**Test coverage for batch.rs: good.** Covers empty requests, per-query results, correct activation subsets, per-query budget, overlapping query sharing, single-query equivalence.

---

## 10. feedback.rs

**Boost mechanic: correct.** SLERP toward IDF-weighted centroid with factor `BOOST_DRIFT_FACTOR * idf_weight * plasticity`. High-IDF (rare, specific) words get pulled harder. Plasticity provides diminishing returns — heavily-activated occurrences are harder to move. Geometrically sound.

**Demote mechanic:** `activation_count.saturating_sub(DEMOTE_DECAY)` where `DEMOTE_DECAY = 2`. Simple activation decay. Floor at 0 via `saturating_sub`. `DEMOTE_DECAY = 2` is a magic number embedded as a module-level constant — fine, but no derivation rationale documented.

**`BOOST_DRIFT_FACTOR = 0.15`** — no derivation rationale. This is a tuning parameter that controls how aggressively helpful memories converge toward query regions. Should be documented.

**centroid computation in feedback.rs vs centroid_drift in query.rs** — duplicate code. Both compute a weighted centroid in R⁴ and project to S³. The logic is identical (sum wx/total_weight, normalize). This should be extracted to a shared utility function on `Quaternion` or in a `geometry.rs` module.

**Test coverage for feedback.rs: good.** Covers boost moves closer to centroid, boost increases activation, demote decreases activation, demote floors at zero, nonexistent neighborhood, empty query.

---

## 11. Numeric Stability

**f64 throughout: consistent with CLAUDE.md convention.**

Precision concerns:

1. **`activation_count as f64` casts throughout.** u32 to f64 is exact up to 2^24 ≈ 16 million, but f64 mantissa is 52 bits so u32 is lossless (u32 max ≈ 4.3 billion < 2^53). No issue in practice.

2. **`usize as f64` for occurrence counts.** On 64-bit systems, usize = u64. For total occurrence counts above 2^53 (~9 quadrillion), precision is lost. Not a practical concern.

3. **Clippy reports 29 `usize as f64` precision warnings and 3 `u64 as i64` wrap warnings.** The u64-to-i64 cast occurs in `parse_days_ago`:
   ```rust
   let now_days = (crate::time::now_unix_secs() / 86400) as i64;
   ```
   `now_unix_secs()` returns `u64`. The division produces a day count (~19,000 for current dates). Converting to i64 is safe for the next ~292 billion years. The clippy warning is a false positive here, but adding a comment would suppress it cleanly.

4. **SLERP clamp in `slerp`:** `dot.clamp(-1.0, 1.0)` before `acos` prevents NaN from dot products that slip outside [-1, 1] due to floating-point rounding. Present and correct.

5. **`angular_distance` uses `.abs().clamp(-1.0, 1.0)`.** The `abs()` ensures the value is non-negative, so `clamp(-1.0, 1.0)` effectively clamps to [0.0, 1.0]. The lower bound of -1.0 is redundant after abs(). Not a bug, just dead code.

6. **`parse_days_ago` Julian Day computation** has hardcoded constants (719468, 146097, etc.) without numeric separators. These are standard proleptic Gregorian calendar constants and are correct; clippy pedantic flags the readability issue.

7. **`compute_weighted_centroid` in feedback.rs vs centroid_drift in query.rs** — both normalize the result after computing the R⁴ sum. Both guard against norm < EPSILON before dividing. Numerically stable.

---

## 12. Test Coverage

**Total: 164 unit tests across all modules + 7 integration tests = 171 tests.**

Module-by-module test count:
- `quaternion.rs`: 13 tests
- `phasor.rs`: 8 tests
- `occurrence.rs`: 8 tests
- `neighborhood.rs`: 6 tests
- `episode.rs`: 7 tests
- `system.rs`: 11 tests
- `query.rs`: 9 tests
- `surface.rs`: 10 tests
- `compose.rs`: 59 tests
- `batch.rs`: 6 tests
- `feedback.rs`: 7 tests
- `tokenizer.rs`: 12 tests
- `time.rs`: 2 tests
- `serde_compat.rs`: (not read, not counted)

**Well covered areas:**
- Drift mechanics (pairwise and centroid paths)
- Scoring pipeline (density bonus, recency decay, interference weighting)
- Decision/Preference type semantics (DECIDED prefix, 3x multiplier, softer diminishing returns)
- Superseded neighborhood exclusion
- Overlap suppression (contradiction detection)
- Budget constraints and greedy fill
- Session diminishing returns
- Feedback (boost/demote mechanics)
- Full pipeline integration (ingest → query → surface → compose → serde roundtrip)

**Coverage gaps:**

1. **No property-based tests (proptest/quickcheck).** The geometric properties (SLERP geodesic monotonicity, angular distance triangle inequality, centroid convergence) would benefit from randomized testing.

2. **No fuzz tests** for tokenizer or serde_compat (injection vectors for external input).

3. **No tests for `random_near` distribution uniformity.** The sqrt-corrected angle is claimed to produce uniform area distribution — this is untested statistically.

4. **No test for batch activation inflation.** The fact that batch queries bump activations N times is undocumented and untested.

5. **No benchmark tests.** `query.rs` has an O(n²) pairwise drift path. Performance regression detection requires criterion benchmarks.

6. **Large query path (>50 tokens) has minimal test coverage.** The weight_floor filtering logic is exercised by no explicit test.

7. **`parse_days_ago` has no unit test.** The Julian day computation is complex and brittle.

8. **`time.rs` has only 2 tests** (known date, Unix epoch). ISO8601 formatting edge cases are not tested.

---

## 13. Idiomatic Rust

**Strengths:**

- Quaternion is `#[derive(Clone, Copy)]` as specified — lightweight value type, no heap allocation.
- `DaemonPhasor` is also `Clone, Copy` — consistent.
- `OccurrenceRef` is `#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash)]` — appropriate for an index type.
- `LazyLock<Regex>` for compiled regexes — idiomatic.
- `floor_char_boundary` for UTF-8 safe string slicing in compose.rs — correct.
- Snapshot-before-mutate pattern in pairwise_drift — correct borrow management.

**Issues:**

1. **Unnecessary clones.** `get_word_occurrences` returns a `Vec<OccurrenceRef>` cloned from the index:
   ```rust
   .cloned().unwrap_or_default()
   ```
   The caller in feedback.rs immediately uses it to iterate — a borrowed slice would suffice if the API allowed it, but the borrow checker requires the clone due to subsequent `&mut DAESystem` borrows. Acceptable, documented by the snapshot pattern.

2. **`retrieve_by_ids` is O(n * m)** where n = IDs requested, m = total neighborhoods. It linear-scans conscious then all episodes for each ID. With a large system this is inefficient. The `neighborhood_index` on `DAESystem` already provides O(1) lookup — `retrieve_by_ids` should use it rather than scanning. The current implementation does NOT call `ensure_indexes`, so it bypasses the index entirely.

3. **`get_neighborhood_text` also scans linearly** within an episode. With `episode_idx` available as a parameter, it could use direct array access:
   ```rust
   // current:
   for nbhd in &episode.neighborhoods { if nbhd.id == neighborhood_id { ... } }
   // could be:
   let nref = self.neighborhood_index.get(&neighborhood_id)?;
   &episode.neighborhoods[nref.neighborhood_idx]
   ```

4. **Clippy pedantic:** 163 warnings total. Dominant categories:
   - 41 missing `#[must_use]` on methods
   - 35 documentation items missing backticks
   - 29 `usize as f64` precision casts
   - 9 `u32` to `f64` via `as` instead of `f64::from`
   None are correctness issues, but `clippy::pedantic` compliance is explicitly listed in the development checklist.

5. **`NeighborhoodType::from_str_lossy`** — the `_lossy` naming implies potential data loss, which is accurate (unknown strings map to Memory). Could implement `FromStr` with a proper error type for a cleaner API.

6. **`try_add` is a closure inside `compose_context_budgeted`** that borrows `system` immutably but takes `system: &DAESystem`. The closure captures nothing from the outer scope except via parameter — it could be a standalone private function. Its current form as a closure inside a 200-line function adds complexity.

---

## Top Findings Summary

### Critical (correctness risk)

None — all tests pass and the core math is correct.

### High (design/correctness concern)

1. **`angular_distance` antipodal collapse:** `q.angular_distance(-q) == 0` while these are distinct manifold points. The code works for the intended use case (rotation semantics) but documents this in the comment. Should be called `rotation_distance` or the comment should be clearer about the semantic choice.

2. **`retrieve_by_ids` bypasses the O(1) index** and performs O(n*m) linear scan. For large systems this is a performance regression path.

3. **Batch activation inflation:** batch queries bump `activation_count` once per query per token, not once per batch. A system that processes 100 batch queries on the same manifold will have occurrences with 100x the activation counts compared to 100 sequential single queries. This affects drift rate, anchoring, and plasticity. Undocumented.

### Medium (maintainability)

4. **compose.rs is a 2959-line god module.** Extract `scoring.rs`, `salient.rs`, and `recency.rs`. The tests alone are 1680 lines.

5. **Duplicate centroid computation** between `feedback.rs::compute_weighted_centroid` and `query.rs::centroid_drift`. Extract to a shared utility.

6. **Magic number 200** (pairwise/centroid drift threshold). Should be a named constant `PAIRWISE_DRIFT_MAX_MOBILE`.

7. **`is_vivid` parameter named `episode_count`** but means "total occurrence count of the episode". Misleading.

### Low (polish)

8. **163 clippy::pedantic warnings.** Predominantly `#[must_use]`, doc backticks, `as f64` casts. None are bugs but the development checklist requires pedantic compliance.

9. **No criterion benchmarks** for the O(n²) pairwise drift path.

10. **`BOOST_DRIFT_FACTOR` and `DEMOTE_DECAY` have no derivation rationale** in documentation.

11. **`usize::MAX` sentinel for conscious episode** — works correctly but a proper enum would be self-documenting.

12. **No property-based tests** for geometric invariants.
