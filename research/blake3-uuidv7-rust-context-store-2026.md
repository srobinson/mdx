---
title: "BLAKE3 and UUID v7 for a Rust Context Store: Best-in-Class Assessment"
type: research
tags: [blake3, uuid, rust, hashing, deduplication, sqlite, content-addressing]
summary: "BLAKE3 is the correct choice for content dedup hashing in Rust despite small-input overhead; UUID v7 via the uuid crate is best-in-class for sortable IDs; both TEXT storage choices in SQLite are defensible but carry tradeoffs."
status: active
source: deep-research
confidence: high
created: 2026-03-14
updated: 2026-03-14
---

## Executive Summary

BLAKE3 is the right hash for content deduplication in a Rust context store in 2026. It dominates SHA-256 on throughput (3-6x faster single-threaded, 15x+ multi-threaded) while providing 128-bit collision resistance at full 256-bit output. The main caveat is that BLAKE3 underperforms on inputs below ~4 KB compared to BLAKE2s and even SHA-256 with hardware acceleration, but the margin is small in absolute terms (nanoseconds) and irrelevant at the volumes described. UUID v7 via the `uuid` crate (v1.9+) is best-in-class for time-sortable identifiers in Rust, with proper monotonicity counters and RFC 9562 compliance. ULID and TypeID are viable alternatives but offer no advantage for this use case.

---

## Part 1: BLAKE3 for Content Deduplication

### 1.1 Is BLAKE3 the right hash?

**Yes, with nuance.** The decision matrix:

| Hash | Throughput (large) | Throughput (small <4KB) | Collision Resistance | Crypto | Rust Crate Quality |
|---|---|---|---|---|---|
| BLAKE3 | ~6,100 MB/s (x86-64) | Slower than SHA-256 w/ HW accel | 128-bit | Yes | 80M+ downloads, 1.8.x, official impl |
| xxHash3 (128-bit) | ~13,200 MB/s | Fastest | 64-bit (birthday bound) | No | ~10M downloads, well-maintained |
| SHA-256 | ~1,750 MB/s (w/ SHA-NI) | Competitive at <4KB with HW accel | 128-bit | Yes | ring/sha2 crates, mature |
| BLAKE2b | ~1,000 MB/s | Better than BLAKE3 at <100B | 128-bit | Yes | blake2 crate, mature |
| HighwayHash | ~10,000 MB/s | Good | Non-crypto | No | Limited Rust ecosystem |

For the described use case (hash of `scope_path + \0 + kind + \0 + body`, bodies 100-10,000 bytes, stored in SQLite for index lookup):

- **xxHash3 is faster but wrong.** It provides zero preimage or collision resistance against adversarial input. If the context store ever ingests untrusted content, a non-crypto hash allows trivial collision attacks. Even for trusted content, the "insurance" cost of BLAKE3 is measured in nanoseconds per entry.
- **SHA-256 is safe but slow.** 15x slower than BLAKE3 on bulk data. On small inputs with SHA-NI hardware instructions, SHA-256 can match or beat BLAKE3, but this depends on the CPU having SHA-NI (common on recent x86, uncommon on ARM).
- **BLAKE2b is fine but superseded.** BLAKE3 is the same team's successor. BLAKE2b is faster on very short inputs (<100 bytes) but slower on everything else.

**Verdict:** BLAKE3 is the correct default. The small-input overhead is real but irrelevant at context-store volumes (not hashing millions of entries per second). The cryptographic guarantee provides future-proofing at near-zero cost.

### 1.2 Is BLAKE3 overkill for dedup?

No. The framing "overkill" implies significant cost for unnecessary capability. BLAKE3's throughput penalty vs xxHash3 is ~3-4x on large inputs, translating to nanoseconds of difference on 10 KB bodies. The cryptographic guarantee costs almost nothing and provides:

- Protection against accidental collisions in perpetuity (birthday bound at 2^128 operations)
- Protection if the store ever accepts external/untrusted content
- Compatibility with content-addressable storage patterns if the system evolves

The scenario where xxHash3 would be meaningfully better: hashing millions of entries per second in a hot loop where nanoseconds matter. That does not describe a context store writing to SQLite.

### 1.3 The blake3 Rust crate

- **Crate:** `blake3` on crates.io
- **Version:** 1.8.3 (as of March 2026)
- **Downloads:** 80M+ total, 15M+ recent
- **Maintainer:** Official BLAKE3 team (Jack O'Connor et al.)
- **SIMD:** Auto-detects SSE2, SSE4.1, AVX2, AVX-512, NEON, WASM at runtime on x86
- **Optional features:** `rayon` for multi-threaded hashing of large inputs
- **Quality:** This is the reference implementation. Battle-tested in production by Wasmer, numerous backup tools, and the Rust compiler's incremental compilation explored it (rust-lang/rust#41215).

### 1.4 Output size: 256-bit (64 hex chars) vs truncated

The current approach stores 256 bits as 64 lowercase hex characters. Assessment:

**256-bit (64 hex chars) is the right choice.** Here is why:

- BLAKE3 provides 128-bit collision resistance at 256-bit output. Truncating to 128 bits (32 hex chars) drops collision resistance to 64 bits (birthday bound = n/2). At 64 bits, a collection of ~2^32 (~4 billion) entries has a non-negligible collision probability.
- BLAKE3 maintainers confirm: "truncating the regular 256-bit output is equivalent to getting a shorter output from the XOF" (GitHub issue #168). This means truncation is safe from a cryptographic perspective, but the birthday bound still applies.
- Storage cost: 64 bytes per row in SQLite TEXT. For a context store with thousands to millions of entries, this is negligible.
- Index performance: SQLite indexes TEXT columns efficiently. The 64-char hex string is fixed-length, which helps B-tree comparisons.

**Could you truncate to 128 bits (32 hex chars)?** Yes, if the store will never exceed ~1 million entries and you accept 64-bit collision resistance. The space savings (32 bytes per row) are unlikely to matter.

**Could you use BLOB(32) instead of TEXT(64)?** Yes, saving 50% storage. But you lose debuggability (can't read hashes in `sqlite3` shell) and gain conversion overhead in Rust. For a context store, TEXT is the pragmatic choice.

---

## Part 2: UUID v7 for Entry IDs

### 2.1 Is UUID v7 best-in-class for sortable IDs?

**Yes for this use case.** Comparison:

| ID Format | Bits | Sortable | Standardized | Rust Crate | Format |
|---|---|---|---|---|---|
| UUID v7 | 128 | Yes (ms precision) | RFC 9562 (published) | `uuid` (300M+ downloads) | `550e8400-e29b-...` (36 chars) |
| ULID | 128 | Yes (ms precision) | Informal spec | `ulid` (~5M downloads) | `01ARZ3NDEKTSV4RRFFQ69G5FAV` (26 chars) |
| TypeID | 128 + prefix | Yes | Jetify spec v0.3 | `mti` (~50K downloads) | `user_01h455vb4p...` (variable) |
| KSUID | 160 | Yes (s precision) | Informal | `ksuid` (~1M downloads) | Base62 (27 chars) |
| nanoid | variable | No | No | `nanoid` | Custom alphabet |
| Snowflake | 64 | Yes | No | Various | Integer |

**UUID v7 wins because:**
- RFC 9562 is now a published standard (finalized 2024). ULID predates it and is functionally equivalent but lacks formal standardization.
- The `uuid` crate is the Rust ecosystem's canonical UUID library with 300M+ downloads. It supports v7 with proper monotonicity counters since v1.9.0.
- PostgreSQL 18 adds native `uuidv7()`. SQLite has no native UUID type, but the ecosystem is converging on UUID v7.
- ULID's 26-char Crockford Base32 encoding is more compact, but the advantage is marginal and comes with less tooling support.
- TypeID adds a type prefix (`user_`, `entry_`) which is useful for multi-entity systems but adds complexity for a single-entity context store.
- Snowflake IDs are 64-bit and require a coordinating authority for worker IDs. Wrong fit for a local context store.

### 2.2 SQLite TEXT vs BLOB for UUIDs

The current approach stores UUIDs as TEXT. Assessment:

| Aspect | TEXT (36 chars) | BLOB (16 bytes) |
|---|---|---|
| Storage per row | 36-38 bytes | 16 bytes |
| Index size | ~2.2x larger | Baseline |
| Insert speed | Comparable | Comparable |
| Select speed | <10% slower | Baseline |
| Debuggability | Direct `SELECT` | Requires `hex()` |
| Rust conversion | `Uuid::to_string()` / `Uuid::parse_str()` | `Uuid::as_bytes()` / `Uuid::from_bytes()` |

**TEXT is defensible for a context store.** The 2x storage overhead on the ID column is dwarfed by the body column (markdown text, 100-10,000 bytes). The debuggability advantage is significant during development. If the store grows to millions of rows and query performance on the ID index becomes measurable, switching to BLOB is a straightforward migration.

### 2.3 UUID text format: hyphens vs raw hex

The description says "lowercase hex TEXT." This could mean:

- **Standard hyphenated:** `550e8400-e29b-41d4-a716-446655440000` (36 chars) -- this is the canonical RFC 9562 format
- **Raw hex:** `550e8400e29b41d4a716446655440000` (32 chars)

**Use the standard hyphenated format.** Reasons:

- The `uuid` crate's `Display` impl produces hyphenated lowercase by default (`Uuid::to_string()`). Raw hex requires explicit `Uuid::simple()`.
- Every UUID tool, library, and debugger expects the hyphenated format. Raw hex requires mental parsing.
- The 4-byte overhead (36 vs 32 chars) is negligible.
- SQLite string comparison on fixed-format strings is efficient regardless of hyphens.
- Hyphens make the version nibble visually obvious (the `7` in `e29b-7...`), aiding debugging.

### 2.4 UUID v7 monotonicity within the same millisecond

The `uuid` crate (v1.9+) handles this correctly:

1. **Counter mechanism:** 42-bit counter (12 bits in `rand_a` field + 30 bits in `rand_b`), with 32 remaining bits filled with random data.
2. **Within a millisecond:** Counter increments, ensuring strict monotonicity. The counter is initialized to a random value (with high bit unset) when a new millisecond is observed.
3. **Counter overflow:** If the counter exhausts all 42 bits within a single millisecond (practically impossible), the timestamp is artificially incremented until the real clock catches up.
4. **Thread safety:** `Uuid::now_v7()` uses a static `Mutex<ContextV7>` internally, so concurrent callers within the same process get monotonic IDs.
5. **Cross-process:** No monotonicity guarantee across processes. Two separate processes generating v7 UUIDs in the same millisecond will interleave, but each process's IDs will be internally monotonic. For a single-writer context store, this is not a concern.

**Pitfall to watch:** If using custom `ContextV7` instances (not the static default), you must ensure the context is shared across all generation sites. Using `Uuid::now_v7()` avoids this.

---

## Part 3: Combined Recommendations

### Current design assessment

| Design Choice | Assessment | Change Needed? |
|---|---|---|
| BLAKE3 for content hash | Correct | No |
| 256-bit / 64 hex chars | Correct | No |
| Stored as TEXT in SQLite | Defensible | No |
| UUID v7 for entry IDs | Correct | No |
| `uuid` crate v1 with v7 feature | Correct (ensure v1.9+) | Verify version |
| UUID stored as TEXT | Defensible | No |
| UUID format (hex vs hyphenated) | Clarify: use hyphenated | Maybe |

### Potential optimizations (not recommended now, but available)

1. **Truncate BLAKE3 to 192 bits (48 hex chars):** Saves 16 bytes per row, still provides 96-bit collision resistance. Only worthwhile at millions of rows.
2. **Store UUID as BLOB(16):** Saves ~20 bytes per row on the ID column. Worthwhile only if storage or index performance becomes measurable.
3. **Replace BLAKE3 with xxHash3-128 for pure speed:** Only if profiling shows hashing is a bottleneck, which it will not be for markdown bodies written to SQLite.

---

## Sources Consulted

### Technical Articles
- [Joey Lynch: Use Fast Data Algorithms](https://jolynch.github.io/posts/use_fast_data_algorithms/) -- throughput benchmarks: xxHash64 13,232 MB/s, BLAKE3 3,675 MB/s, SHA-256 240 MB/s
- [Sylvain Kerkour: Choosing a hash function for 2030 and beyond](https://kerkour.com/fast-secure-hash-function-sha256-sha512-sha3-blake3) -- BLAKE3 6,121 MB/s on x86-64, recommends BLAKE3 as "function to rule them all"
- [Joseph Szymborski: Maybe don't use Blake3 on Short Inputs](https://jszym.com/blog/short_input_hash/) -- BLAKE3 underperforms on <4KB inputs; BLAKE2s wins for very short inputs
- [KodrAus: uuid now properly supports version 7 counters](https://kodraus.github.io/rust/2024/06/24/uuid-v7-counters.html) -- detailed explanation of uuid crate v1.9 counter mechanism
- [Brandur: Postgres UUIDv7 + per-backend monotonicity](https://brandur.org/fragments/uuid-v7-monotonicity)
- [Vespa: Efficiency, UUIDs and SQLite](https://vespa-mrs.github.io/vespa.io/development/project_dev/database/DatabaseUuidEfficiency.html) -- TEXT 94MB vs BLOB 51MB for 1M UUIDs
- [Droidcon: Optimizing UUID Storage in SQLDelight](https://www.droidcon.com/2024/12/09/optimizing-uuid-storage-in-sqldelight-text-vs-two-longs-and-a-look-ahead-at-uuid-v7/)

### GitHub Issues and Discussions
- [BLAKE3 #168: Collision-resistance properties with less than 256 bits](https://github.com/BLAKE3-team/BLAKE3/issues/168) -- maintainer confirms truncation safety, birthday bound applies
- [BLAKE3 #194: Collision resistance](https://github.com/BLAKE3-team/BLAKE3/issues/194)
- [rust-lang/rust #41215: Hash algorithm for incremental compilation](https://github.com/rust-lang/rust/issues/41215) -- Rust compiler team evaluated BLAKE3 and others

### HackerNews
- [Choosing a hash function for 2030 and beyond (HN)](https://news.ycombinator.com/item?id=46047409) -- consensus: BLAKE3 for speed+security, SHA-2 for compliance
- [BLAKE3 dedup concern (HN)](https://news.ycombinator.com/item?id=38250398) -- chunk counter concern applies only to Bao tree mode, not single-call `blake3::hash()`
- [UUIDv7 looks interesting, but how is it different from ULID](https://news.ycombinator.com/item?id=31716140)

### Crate Pages
- [blake3 on crates.io](https://crates.io/crates/blake3) -- v1.8.3, 80M+ total downloads
- [uuid on crates.io](https://crates.io/crates/uuid) -- 300M+ total downloads, v7 counters since v1.9.0
- [uuid docs.rs](https://docs.rs/uuid)

### Standards
- [BLAKE3 IETF Draft](https://www.ietf.org/archive/id/draft-aumasson-blake3-00.html)
- [RFC 9562: UUIDs](https://www.rfc-editor.org/rfc/rfc9562) -- published standard for UUID v7

---

## Source Quality Assessment

**Confidence: High.** The core claims are supported by:
- Official maintainer statements (BLAKE3 team on truncation, uuid crate author on counters)
- Published benchmarks from multiple independent sources converging on the same throughput ratios
- RFC 9562 as a published standard for UUID v7
- Production usage data (crate download counts, Wasmer adoption, Rust compiler evaluation)

**Gaps:**
- No Rust-specific micro-benchmarks comparing BLAKE3 vs xxHash3 on 1-10KB inputs. The Szymborski blog used C implementations. Actual Rust crate performance may differ slightly due to SIMD dispatch implementation.
- Reddit and HackerNews had minimal discussion of BLAKE3-for-dedup specifically in 2025-2026. The topic is settled enough that it does not generate debate.

---

## Open Questions

1. **ARM performance:** BLAKE3 drops to 1,338 MB/s on ARM64 (Graviton 4) vs 6,121 MB/s on x86-64. If the context store runs on Apple Silicon or ARM servers, BLAKE3 is still fast but the gap vs SHA-256 (with hardware crypto extensions) narrows. Worth benchmarking if ARM is the target.
2. **BLAKE3 IETF standardization timeline:** The IETF draft exists but is not yet an RFC. For systems requiring formal standardization, this is a gap. For a local context store, irrelevant.
3. **uuid crate v2 migration:** The `uuid` crate is on v1.x. A v2 release could change APIs. No indication this is imminent.

---

## Actionable Takeaways

1. **Keep BLAKE3 with 256-bit output stored as 64-char lowercase hex.** This is the correct design.
2. **Keep UUID v7 via the `uuid` crate.** Ensure the crate version is 1.9.0 or later to get proper monotonicity counters. Use `Uuid::now_v7()` for the simplest correct behavior.
3. **Use hyphenated format for UUID TEXT storage** (`550e8400-e29b-71d4-...`), matching `Uuid::to_string()` output. This is the canonical format and costs only 4 bytes over raw hex.
4. **Do not switch to xxHash3.** The throughput advantage is irrelevant at context-store volumes, and losing cryptographic collision resistance removes future optionality.
5. **Do not switch to BLOB storage** unless profiling shows the TEXT overhead matters, which it will not for a store with markdown bodies dominating row size.
6. **Do not switch to ULID or TypeID.** UUID v7 is now RFC-standardized with superior ecosystem support in Rust.
