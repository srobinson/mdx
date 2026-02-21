# attention-matters Code Quality and Security Review

**Date:** 2026-03-13
**Scope:** Full workspace (am-core, am-store, am-cli)
**Lines reviewed:** ~14,769 (source) across 28 Rust files
**Tests:** 58/58 passing, 0 clippy warnings

---

## Executive Summary

The codebase is well structured, cleanly layered, and demonstrates disciplined Rust engineering. The am-core crate maintains its "zero I/O" contract. SQL injection is effectively mitigated through parameterized queries. The MCP server runs over stdio (no network listener). No critical vulnerabilities were found.

The most significant findings are: (1) six `unwrap()` calls in am-core library code on `partial_cmp` that could panic on NaN scores, (2) GC SQL built with string interpolation of validated numeric values that should still use parameterized queries for defense in depth, and (3) a u32 activation counter with no overflow guard that could saturate after ~4B activations.

---

## Findings by Severity

### HIGH (Should fix before next release)

#### H1. `partial_cmp().unwrap()` in compose.rs scoring paths (lines 337, 361, 389, 457, 463, 469, 569)

**File:** `/Users/alphab/Dev/LLM/DEV/helioy/attention-matters/crates/am-core/src/compose.rs`

Seven occurrences of this pattern:

```rust
con.sort_by(|a, b| b.score.partial_cmp(&a.score).unwrap());
```

If any `score` field is `NaN` (which is possible from geometry computations on degenerate input), `partial_cmp` returns `None` and this panics. This is library code in am-core where the convention says panics should never occur. Replace with `unwrap_or(std::cmp::Ordering::Equal)` or `total_cmp()` (available on f64 since Rust 1.62).

**Impact:** Panic in the query pipeline kills the MCP server process. The AI agent loses memory for the rest of the session.

---

### MEDIUM (Should fix in upcoming work)

#### M1. GC SQL uses string formatting instead of parameterized queries

**File:** `/Users/alphab/Dev/LLM/DEV/helioy/attention-matters/crates/am-store/src/store.rs` (lines 686-698, 778-800)

The `gc_pass` and `gc_to_target_size` methods build SQL with `format!()`:

```rust
retention_clauses.push_str(&format!(
    "\n                     AND n.epoch < {epoch_floor}"
));
```

The interpolated values (`epoch_floor`, `retention_secs`, `max_epoch_f`, `recency_weight`) come from validated numeric types (u64, f64) so SQL injection is not realistically exploitable here. However, this violates defense-in-depth principles. If a future refactor introduces user-controlled values into these paths, the injection surface is already open. Use `rusqlite::params!` consistently.

#### M2. `activation_count: u32` has no saturation guard on `activate()`

**File:** `/Users/alphab/Dev/LLM/DEV/helioy/attention-matters/crates/am-core/src/occurrence.rs` (line 41)

```rust
pub fn activate(&mut self) {
    self.activation_count += 1;
}
```

In debug mode this overflows to panic; in release mode it wraps to 0. The `feedback.rs` correctly uses `saturating_add` and `saturating_sub`, but the primary `activate()` path does not. For a long-lived memory system, high-frequency words could theoretically saturate. Use `self.activation_count = self.activation_count.saturating_add(1)`.

#### M3. `token_count()` allocates full Vec unnecessarily

**File:** `/Users/alphab/Dev/LLM/DEV/helioy/attention-matters/crates/am-core/src/tokenizer.rs` (lines 27-29)

```rust
pub fn token_count(text: &str) -> usize {
    tokenize(text).len()
}
```

This tokenizes the entire text into a Vec<String> just to count it. Called in hot paths during context composition (every candidate neighborhood). Could use an iterator-based count or a separate counting function that avoids heap allocation.

#### M4. Server state mutex is held for entire tool handler duration

**File:** `/Users/alphab/Dev/LLM/DEV/helioy/attention-matters/crates/am-cli/src/server.rs`

Every MCP tool handler acquires `self.state.lock().await` and holds it for the full duration including I/O (store save). Since this is a single-connection stdio MCP server, the practical impact is minimal today. If the server ever serves multiple concurrent clients or adds WebSocket transport, this becomes a serialization bottleneck.

#### M5. `SmallRng` is not cryptographically secure

**File:** `/Users/alphab/Dev/LLM/DEV/helioy/attention-matters/crates/am-cli/src/server.rs` (line 51)

`SmallRng` is used for quaternion position generation. This is appropriate for the geometric use case (positions on S3 manifold) and does not require CSPRNG. Noting for completeness: do not use this RNG for any security-sensitive purpose. The current usage is correct.

---

### LOW (Technical debt / improvement opportunities)

#### L1. Clones in query hot path for borrow-conflict avoidance

**File:** `/Users/alphab/Dev/LLM/DEV/helioy/attention-matters/crates/am-core/src/query.rs` (lines 75-94)

```rust
let sub_words: Vec<(OccurrenceRef, String)> = activation
    .subconscious
    .iter()
    .map(|r| (*r, system.get_occurrence(*r).word.clone()))
    .collect();
```

Every word string is cloned to work around the borrow checker (system is borrowed mutably for `get_word_weight`). This is a known pattern in the DAESystem design where `get_word_weight` takes `&mut self` because it calls `ensure_indexes()`. Consider splitting the index-rebuild concern from the weight-lookup concern so the lookup can take `&self`.

#### L2. `session_recalled` is cloned before destructuring state

**File:** `/Users/alphab/Dev/LLM/DEV/helioy/attention-matters/crates/am-cli/src/server.rs` (line 204)

```rust
let session_recalled_snapshot = state.session_recalled.clone();
```

The HashMap is cloned on every `am_query` call to avoid borrow conflicts. For a typical session this map is small (tens of entries), so the cost is negligible. The pattern is correct; just noting the workaround.

#### L3. Dead `_query_words` parameter in `apply_boost`

**File:** `/Users/alphab/Dev/LLM/DEV/helioy/attention-matters/crates/am-core/src/feedback.rs` (line 113)

The parameter `_query_words: &[String]` is unused (prefixed with underscore). Either remove it or document the planned use.

#### L4. Regex `unwrap()` in LazyLock initializers are acceptable

**Files:** `tokenizer.rs` (lines 8-10), `compose.rs` (line 1242)

These are compile-time constant regex patterns that cannot fail. The `unwrap()` is justified. Noting for completeness.

#### L5. No doc-tests

**File:** `/Users/alphab/Dev/LLM/DEV/helioy/attention-matters/crates/am-core/src/lib.rs`

Zero doc-tests across all crates. The public API types (Quaternion, DAESystem, QueryEngine) are well-documented with module-level comments but lack usage examples in doc comments.

#### L6. `PartialEq` on `Quaternion` uses epsilon comparison

**File:** `/Users/alphab/Dev/LLM/DEV/helioy/attention-matters/crates/am-core/src/quaternion.rs` (lines 21-28)

The `PartialEq` impl uses epsilon-based comparison, which means `a == b` and `b == c` does not imply `a == c` (non-transitive). This is fine for the geometric use case but would be incorrect if Quaternion were ever used as a HashMap key. Since it does not implement `Eq` or `Hash`, this is safe.

---

## Security Review

### SQL Injection: LOW RISK

All user-facing SQL uses parameterized queries via `rusqlite::params!`. The GC paths use string formatting but only with validated numeric values (see M1). No user-supplied strings are interpolated into SQL.

### Deserialization: LOW RISK

`import_json` (serde_compat) accepts untrusted JSON and deserializes it into strongly-typed structs. Malformed UUIDs fall through to `unwrap_or_else(|_| Uuid::new_v4())`. Oversized payloads are bounded by serde_json's default recursion limit. No arbitrary code execution surface.

### MCP Server Transport: NO NETWORK EXPOSURE

The server runs over stdio transport only. There is no HTTP listener, no TCP socket, no network binding. The attack surface is limited to whatever process connects to stdin/stdout (Claude Code).

### Path Traversal: MINIMAL RISK

File paths in `sync.rs` resolve Claude Code session directories using `encode_path()` which replaces `/` with `-`. The paths are constructed from `CLAUDE_CONFIG_DIR` (env var or `~/.claude`) and CWD. No user-supplied path components reach the filesystem without sanitization.

### Process Signal Safety

**File:** `/Users/alphab/Dev/LLM/DEV/helioy/attention-matters/crates/am-cli/src/main.rs` (line 437)

The single `unsafe` block calls `libc::kill(pid, 0)` to check if a process is alive. This is a standard POSIX pattern, correctly gated behind `#[cfg(unix)]`, and sends no actual signal (signal 0 is a validity check only). Justified.

### Integer Overflow in Geometry: NEGLIGIBLE

All f64 arithmetic in quaternion/phasor computations uses standard trig functions that produce NaN/Inf on degenerate input rather than UB. The `clamp(-1.0, 1.0)` before `acos()` prevents NaN from domain errors. The `normalize()` fallback to identity on near-zero magnitude prevents division by zero.

---

## Dependency Analysis

All dependencies use semver ranges (e.g., `rand = "0.9"`, `rusqlite = "0.32"`). No pinned versions. `cargo-audit` is not installed but the dependency set is mature and widely audited:

| Dependency | Version | Notes |
|---|---|---|
| rusqlite | 0.32 | bundled SQLite, well-maintained |
| rmcp | 0.15 | MCP protocol library |
| rand | 0.9 | SmallRng for geometry, appropriate |
| serde/serde_json | 1.x | Industry standard |
| tokio | 1.x | Async runtime |
| clap | 4.x | CLI parsing |
| uuid | 1.x | v4 UUIDs |
| pulldown-cmark | 0.13 | Markdown parsing for sync |
| libc | 0.2 | Process signal check only |

**Recommendation:** Install `cargo-audit` and run it in CI.

---

## Architecture Assessment

**SOLID compliance:** Strong. am-core has zero I/O (SRP). Store and CLI have clean separation.

**DRY:** Good. Some minor repetition in the `rng()` and `to_tokens()` test helpers across modules (acceptable for test isolation).

**Code organization:** Clean module hierarchy. Each am-core module has a single responsibility. The system.rs file acts as coordinator. compose.rs is the largest file (~2800 lines including tests) and could benefit from being split into scoring, formatting, and budgeting sub-modules, but is currently coherent.

**Error handling:** am-store uses a proper `StoreError` enum. am-cli uses `anyhow::Result`. am-core returns Option/Result where appropriate. The "refusing to overwrite existing data with empty system" guard in `save_system` is an excellent defensive pattern.

**Test quality:** Tests cover the geometric properties (SLERP endpoints, equidistance, unit quaternion invariant), edge cases (zero input, empty systems, NaN-adjacent), and roundtrip invariants (JSON, SQLite). Good structural coverage.

---

## Top Recommendations (Priority Order)

1. **Fix `partial_cmp().unwrap()` in compose.rs** - Replace with `unwrap_or(Ordering::Equal)` to prevent NaN panics in library code.
2. **Use `saturating_add` in `Occurrence::activate()`** - Prevent u32 overflow on high-frequency activation.
3. **Parameterize GC SQL** - Replace `format!()` with `rusqlite::params!` in gc_pass and gc_to_target_size.
4. **Add `cargo-audit` to CI** - Automated dependency vulnerability scanning.
5. **Optimize `token_count()`** - Avoid full Vec allocation for counting.
