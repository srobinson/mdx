# attention-matters Architecture Review

**Date:** 2026-03-13
**Scope:** Full workspace architecture review of the DAE (Daemon Attention Engine) geometric memory system.
**Version:** 0.1.15
**Codebase:** 30 files, 16,051 LOC across 3 crates.

---

## 1. Crate Boundaries and Separation of Concerns

### Dependency Direction: Clean

```
am-core  (zero dependencies on other workspace crates)
   ^
am-store (depends on am-core)
   ^
am-cli   (depends on am-core + am-store)
```

This is textbook layered architecture. The dependency DAG is acyclic and flows in the correct direction.

### Zero-I/O Contract of am-core: Upheld (with one minor exception)

A grep for `std::fs`, `std::io`, `std::net`, `std::path`, `File::`, `tokio::`, `async fn` across all of `crates/am-core/src/` returns zero results in production code. The contract holds.

**Minor exception:** `crates/am-core/src/time.rs:8-13` calls `SystemTime::now()`. This is a system clock read, which is technically a side effect. For a "pure math, zero I/O" crate, this is a philosophical impurity. The function returns a `u64` and is used as a timestamp source throughout the system. In practice this is harmless, but a strict interpretation of "zero I/O" would push `now_unix_secs()` and `now_iso8601()` to the caller, passing timestamps as parameters. The pure conversion function `unix_to_iso8601()` is clean.

**Verdict:** The contract is well maintained. The `time.rs` functions are the only place where am-core touches the outside world, and they carry no failure modes beyond `unwrap_or_default`.

### am-store: Well-Bounded Persistence Layer

am-store owns exactly one concern: SQLite persistence of `DAESystem` state. The module breakdown is clean:

| Module | Responsibility |
|--------|---------------|
| `store.rs` (1596 LOC) | Core CRUD operations on SQLite, GC, statistics |
| `project.rs` (349 LOC) | `BrainStore` facade, migration, startup GC |
| `config.rs` (344 LOC) | TOML config loading, defaults, validation |
| `schema.rs` (321 LOC) | DDL, schema versioning, migrations |
| `json_bridge.rs` (252 LOC) | JSON import/export extending `Store` via `impl Store` |
| `error.rs` (26 LOC) | `StoreError` enum, `From<rusqlite::Error>` |

The `json_bridge.rs` pattern of extending `Store` via a separate file using `impl Store` is idiomatic Rust for organizing method groups without splitting the struct definition. Clean.

### am-cli: Application Shell

am-cli bundles three concerns:
1. CLI command dispatch (`main.rs`, 1543 LOC)
2. MCP server (`server.rs`, 1675 LOC)
3. Session transcript sync (`sync.rs`, 1085 LOC)

This is appropriate. All three are application-level entry points that compose am-core and am-store. No architectural concern here.

---

## 2. Module Cohesion within am-core

### Internal Dependency Flow

```
constants -----> quaternion --> phasor --> occurrence --> neighborhood --> episode --> system
                                                              |              |          |
                                                              v              v          v
                                                           query <------  surface  <-- compose
                                                              |                        |
                                                              v                        v
                                                           feedback                  batch
```

The dependency chain follows the domain model naturally: math primitives build up to geometric structures, which build up to query and composition layers. Each module has a clear single responsibility.

### Module Overlap Assessment

No significant overlap detected. Each module owns a distinct concept:

- `query.rs` owns drift, interference, Kuramoto coupling (the retrieval physics)
- `surface.rs` owns vivid neighborhood/episode identification (what is currently "active")
- `compose.rs` owns context assembly (what to show the user)
- `batch.rs` wraps query+compose for amortized IDF across multiple queries

The one area where boundaries blur is between `query.rs` and `compose.rs`. The `compose.rs` module imports `InterferenceResult` from `query.rs` and performs its own scoring/ranking. This creates a scoring pipeline split across two modules: query computes raw interference, compose applies scoring heuristics. This split is defensible because query handles the physics and compose handles the policy, but the 9 private scoring constants in compose (lines 864-908) suggest scoring logic is substantial enough that it could warrant its own module if compose grows further.

### Tokenizer Placement

`crates/am-core/src/tokenizer.rs` (165 LOC) provides regex tokenization and sentence chunking. This is appropriate in am-core because token boundaries affect manifold placement. The tokenizer is a pure function with no I/O.

---

## 3. compose.rs: God Module Assessment

### Size Breakdown

| Region | Lines | Purpose |
|--------|-------|---------|
| Types and structs | 1-110 | 11 public types (RecallCategory, BudgetConfig, ContextResult, etc.) |
| `compose_context` | 304-426 | Core context composition (123 lines) |
| `compose_context_budgeted` | 438-686 | Token-budget-aware composition (249 lines) |
| `compose_index` | 716-797 | Index-only query (82 lines) |
| `retrieve_by_ids` | 802-860 | Neighborhood retrieval by UUID (59 lines) |
| Scoring internals | 862-1245 | Private scoring functions and constants (~383 lines) |
| Salience utilities | 1246-1276 | `detect_neighborhood_type`, `extract_salient`, `mark_salient_typed` |
| Tests | 1278-2959 | 48 test functions (1681 lines) |

**Production code: 1276 lines. Tests: 1683 lines.**

### Verdict: Not a god module, but approaching the threshold.

The 1276 lines of production code serve a single cohesive concern: assembling recall context from the geometric memory system. The two primary entry points (`compose_context` and `compose_context_budgeted`) are variations of the same pipeline. The scoring internals (383 lines of private functions) are tightly coupled to the composition logic.

However, two refactoring opportunities exist:

1. **Extract scoring into `crates/am-core/src/scoring.rs`**: The 9 private constants and ~383 lines of scoring functions (aggregate_interference, rank_subconscious, etc.) form a coherent sub-concern. Extracting them would reduce compose.rs to ~890 lines of production code and improve testability of the scoring layer independently.

2. **The salience utilities at lines 1246-1276 are misplaced.** `detect_neighborhood_type` and `mark_salient_typed` deal with neighborhood classification, not context composition. They belong in `neighborhood.rs` or a dedicated `salience.rs` module. They are here because `compose.rs` was the first consumer, but `mark_salient_typed` is also called from `server.rs`.

The test suite at 1683 lines is excellent. 48 tests covering edge cases, budget constraints, and scoring behavior. The test-to-production ratio of 1.3:1 is healthy.

---

## 4. server.rs: MCP Server Scope

### Size Breakdown

| Region | Lines | Purpose |
|--------|-------|---------|
| State and setup | 1-101 | `AmServer`, `ServerState`, constructor, helpers |
| Tool parameter types | 103-192 | 9 request structs with JsonSchema derives |
| Tool implementations | 193-905 | 12 MCP tools (am_query, am_buffer, am_salient, etc.) |
| ServerHandler impl | 907-941 | MCP protocol handler, server info/instructions |
| Tests | 943-1675 | 18 test functions (732 lines) |

**Production code: 941 lines. Tests: 734 lines.**

### Verdict: Appropriate scope, well-structured.

The server.rs file is a thin adapter layer. Each tool method follows the same pattern:
1. Lock the state mutex
2. Delegate to am-core functions
3. Serialize the result to JSON
4. Return as MCP `CallToolResult`

There is minimal business logic in server.rs itself. The `AmServer` struct holds exactly the right state: DAESystem (domain model), BrainStore (persistence), RNG, session tracking, and dedup.

### Concurrency Model

The entire server state is behind a single `Arc<Mutex<ServerState>>`. Every tool handler acquires the lock for its full duration. This is correct for an MCP server on stdio transport (single client, sequential requests) but would become a bottleneck under concurrent access. Given the deployment model (one server per Claude Code session), this is not a concern today. If the server ever moves to HTTP with concurrent clients, the lock should be split (separate locks for system vs. store vs. session_recalled).

### Dedup Window

The `dedup_window` (`HashMap<u64, Instant>`) in `ServerState` prevents duplicate episode creation within 60 seconds. This is cleaned lazily on each `am_buffer` call. The hash is computed via `DefaultHasher`, which is deterministic within a process but not across restarts. This is fine since the window is session-scoped.

---

## 5. main.rs: CLI Design

### Command Surface

```
am serve    # MCP server (primary mode)
am query    # CLI query
am ingest   # Document ingestion
am stats    # Memory statistics
am export   # JSON export
am import   # JSON import
am inspect  # Memory browser (5 sub-modes)
am sync     # Claude Code transcript sync
am gc       # Garbage collection
am forget   # Selective memory removal
am init     # Config generation
```

11 commands. The `Commands` enum spans lines 78-308 (231 lines) because each variant carries detailed `long_about` and `after_help` text. This is verbose but the documentation quality is high. Every command has usage examples and clear explanations.

### main.rs Structure Assessment

**Production code: ~1543 lines (no inline test module).**

The file follows a standard pattern: CLI definition at top, `main()` as dispatcher in the middle, command implementations as functions below. The `cmd_*` functions range from 13 lines (`cmd_export`) to 145 lines (`inspect_overview`).

**Concern:** main.rs has 0 unit tests. All testing for CLI commands comes through `crates/am-cli/tests/cli.rs` (20 integration tests using `assert_cmd`). This is acceptable for a CLI binary, but the larger functions (`cmd_sync_discover` at 109 lines, `inspect_overview` at 145 lines) would benefit from unit-testable extraction.

**Concern:** The sync-related functions in main.rs (`cmd_sync`, `cmd_sync_single`, `cmd_sync_discover`, `write_sync_log`) total ~340 lines and represent a distinct subsystem. They call into `sync.rs` for parsing but handle all orchestration inline. This could be extracted to reduce main.rs to ~1200 lines.

---

## 6. sync.rs: Session Transcript Ingestion

### Purpose

sync.rs parses Claude Code JSONL session transcripts and extracts conversation episodes for ingestion into the memory system.

### Size Breakdown

| Region | Lines | Purpose |
|--------|-------|---------|
| Types | 34-68 | `HookInput`, `SessionInfo`, `ExtractedEpisode` |
| JSONL parsing | 100-142 | `extract_episodes`: parse transcript, split into episodes |
| Text extraction | 402-442 | `extract_session_text`: role-tagged plaintext from JSONL |
| File discovery | 450-539 | `resolve_claude_dir`, `find_project_dir`, `discover_sessions` |
| Tests | 541-1085 | 27 test functions (544 lines) |

**Production code: ~540 lines. Tests: ~545 lines.**

### Verdict: Well-bounded.

sync.rs owns a single concern: Claude Code transcript parsing. It has no dependency on am-core or am-store. It imports only `anyhow`, `pulldown_cmark`, `serde`, and `std`. The boundary is clean: it produces `ExtractedEpisode` structs that main.rs then feeds to am-core for ingestion.

The test suite is thorough, covering JSONL parsing edge cases, sidechain filtering, markdown stripping, role headers, and filesystem discovery.

---

## 7. Dependency Direction Verification

### Cargo.toml Dependency Matrix

| Crate | am-core | am-store | External |
|-------|---------|----------|----------|
| am-core | - | - | rand, uuid, regex, serde, serde_json |
| am-store | yes | - | rusqlite, serde, toml, tracing, uuid, rand |
| am-cli | yes | yes | rmcp, tokio, clap, schemars, serde, serde_json, anyhow, rand, tracing, tracing-subscriber, uuid, pulldown-cmark, libc |

**am-core never depends on am-store or am-cli.** Verified both in Cargo.toml and by code inspection.

### External Dependency Assessment

- **serde_json in am-core:** Required for `serde_compat.rs` JSON serialization. This is appropriate since the wire format is a core domain concern.
- **regex in am-core:** Required for the tokenizer. Appropriate.
- **rand in am-core:** Required for quaternion random placement and golden-angle distribution. Appropriate.
- **rmcp in am-cli:** MCP protocol library. Single point of protocol dependency in the right layer.
- **pulldown-cmark in am-cli:** Markdown stripping for sync transcripts. Light dependency, correctly isolated.

No dependency concerns.

---

## 8. Public API Surface of am-core

### 74 Exports from lib.rs

The lib.rs file is a pure re-export facade (53 lines, all `pub use` statements). The 74 exports break down as:

| Category | Count | Examples |
|----------|-------|---------|
| Constants | 12 | PHI, GOLDEN_ANGLE, THRESHOLD, EPSILON, NEIGHBORHOOD_RADIUS, etc. |
| Core types | 8 | Quaternion, DaemonPhasor, Occurrence, Neighborhood, Episode, DAESystem, etc. |
| Reference types | 3 | OccurrenceRef, NeighborhoodRef, NeighborhoodType |
| Query types | 4 | QueryEngine, QueryResult, BatchQueryEngine, BatchQueryRequest, BatchQueryResult |
| Compose types | 10 | ContextResult, BudgetConfig, BudgetedContextResult, CategorizedIds, etc. |
| Surface/Feedback types | 4 | SurfaceResult, FeedbackSignal, FeedbackResult |
| Free functions | 15 | compose_context, compute_surface, apply_feedback, ingest_text, tokenize, etc. |
| Serde | 3 | CURRENT_VERSION, import_json, export_json |
| Time | 3 | now_unix_secs, now_iso8601, unix_to_iso8601 |
| Module re-exports | 15 | mod batch, mod compose, mod constants, etc. |

### Coherence Assessment

The API surface is coherent. All exports relate to the geometric memory domain. The naming is consistent: types are PascalCase, functions are snake_case, constants are SCREAMING_SNAKE.

**Concern: Both modules and their contents are re-exported.** For example, `pub mod compose;` and `pub use compose::{compose_context, ...};` both exist. This means consumers can write either `am_core::compose_context(...)` or `am_core::compose::compose_context(...)`. This dual-path access is not harmful but creates API surface ambiguity. The flat re-exports suggest the intended API is `am_core::TypeName`, and the module re-exports exist for consumers that want to import from a specific sub-module.

**Concern: 12 constants are exported at the top level.** Constants like `PHI`, `GOLDEN_ANGLE`, `M`, `EPSILON` are generic names. Exporting them at the crate root risks name collisions for consumers. Keeping them behind `am_core::constants::PHI` would be cleaner, though in practice am-cli is the only consumer and uses them sparingly.

---

## 9. Error Handling Strategy

### am-store: Custom StoreError

```rust
pub enum StoreError {
    Sqlite(rusqlite::Error),
    InvalidData(String),
}
```

Implements `Display`, `Error`, and `From<rusqlite::Error>`. Clean and minimal.

### am-cli: anyhow

All CLI commands return `anyhow::Result<()>`. The `StoreError` from am-store is converted via `.context("...")` calls, which wrap the underlying error with a human-readable message. This produces good error traces for CLI users.

### Error Propagation Chain

```
rusqlite::Error --> StoreError::Sqlite --> anyhow::Error (with context string)
```

This is clean. The `.context()` pattern is used consistently throughout main.rs (30+ call sites), providing descriptive error messages at each layer.

### server.rs Error Handling

MCP tool handlers return `Result<CallToolResult, McpError>`. Internal errors are converted to MCP error responses. The pattern is:

```rust
let mut state = self.state.lock().await;
// ... operations that can fail ...
Ok(CallToolResult::success(vec![Content::text(json)]))
```

Store errors within tool handlers are handled by converting to MCP error text. This is appropriate for the MCP protocol.

**One concern:** In `server.rs:451`, the `AmServer::new` error is mapped with `.map_err(|e| anyhow::anyhow!("{e}"))`. This loses the typed error. The `AmServer::new` returns `Result<Self, String>`, so the error is already stringly-typed before this conversion. The `new()` method itself maps `StoreError` to `String` via `format!()`. A better pattern would be to return `Result<Self, StoreError>` from `new()` and let the caller decide on conversion.

---

## 10. Architectural Risks and Refactoring Opportunities

### Risk 1: Single Mutex Serializes All Server Operations (Low, but watch)

`ServerState` holds the entire in-memory `DAESystem`, `BrainStore`, and `SmallRng` behind one `tokio::sync::Mutex`. Every MCP tool call acquires this lock for its full duration, including I/O (SQLite writes). For the current single-client MCP stdio model, this is correct. If the server ever serves multiple concurrent clients (e.g., over HTTP), this becomes a throughput bottleneck.

**Recommendation:** Document this as an intentional constraint. If multi-client support arrives, split into read-write lock or per-concern locks.

### Risk 2: Full System Load/Save Granularity (Medium)

`store.rs` `save_system` serializes the entire `DAESystem` to SQLite on every write operation. `load_system` deserializes the entire state on startup. For a growing memory system with thousands of episodes, this becomes O(N) per save. The current implementation uses a dirty flag (`system.dirty`) to avoid unnecessary saves, which is good.

**Recommendation:** Consider incremental persistence (append-only episode writes, batch occurrence updates) as data volumes grow. The current full-system save is acceptable for current scale but will not scale to millions of occurrences.

### Risk 3: compose.rs Scoring Constants are Hardcoded (Low)

Nine scoring constants (`DECISION_MULTIPLIER`, `CONSCIOUS_MIN_OVERLAP`, `INTERFERENCE_WEIGHT`, `VIVIDNESS_BOOST`, `RECENCY_DECAY_RATE`, etc.) are compile-time constants in compose.rs. These control recall quality and ranking behavior. Tuning them requires recompilation.

**Recommendation:** Consider making scoring parameters configurable via the existing `Config` system if tuning becomes frequent. The current approach is fine for a system where the developer controls all parameters.

### Risk 4: No Structured Logging in am-core (Low)

am-core has zero tracing/logging. am-store uses `tracing` sparingly. am-cli uses `tracing` for server lifecycle. For a pure math library, silence is appropriate. However, debugging recall quality issues (why did this neighborhood rank higher?) requires adding temporary logging and recompiling.

**Recommendation:** Consider adding `tracing` as an optional feature in am-core for diagnostic builds. Alternatively, return scoring metadata in `ContextResult` for downstream debugging.

### Risk 5: DAESystem Is a Monolithic In-Memory State (Medium)

`DAESystem` (system.rs:52-71) holds all episodes, the conscious episode, occurrence/neighborhood indexes, IDF weights, and dirty tracking in a single struct with 20 public methods. This is the central domain object that all query, compose, surface, and feedback operations operate on.

The design is appropriate for the current scale (single-brain, single-process). The risk is that as the system grows, DAESystem becomes a god object that everything depends on. The current 20-method interface is manageable but approaching the threshold where decomposition would improve testability.

**Recommendation:** Monitor method count. If DAESystem grows beyond ~25 public methods, consider extracting read-only query operations into a separate `SystemView` or splitting indexes into their own type.

### Refactoring Opportunity 1: Extract Scoring from compose.rs

Move the ~383 lines of private scoring functions and constants from compose.rs into a `scoring.rs` module. This improves:
- Testability: scoring functions can be unit tested independently
- Readability: compose.rs focuses on assembly, scoring.rs on ranking
- Reusability: batch.rs could use scoring directly

### Refactoring Opportunity 2: Move Salience Utilities

`detect_neighborhood_type`, `extract_salient`, `mark_salient_typed` (compose.rs:1246-1276) are neighborhood classification functions, not composition functions. Move to `neighborhood.rs` or a dedicated `salience.rs`.

### Refactoring Opportunity 3: Extract Sync Orchestration from main.rs

The sync-related functions in main.rs (`cmd_sync`, `cmd_sync_single`, `cmd_sync_discover`, `write_sync_log`, ~340 lines) could move to a `sync_cmd.rs` or become methods on a `SyncRunner` struct in sync.rs. This would reduce main.rs from 1543 to ~1200 lines and keep sync logic co-located.

---

## 11. Strengths

1. **Clean crate boundaries.** The three-layer architecture with am-core as a pure domain library is well executed. The zero-I/O contract is enforced by dependency absence, which is the strongest guarantee Rust offers.

2. **Excellent test coverage.** 282+ test functions across the workspace. The compose.rs test suite (48 tests, 1683 lines) is particularly strong. Test-to-production ratios are healthy across all modules.

3. **Consistent error handling.** The `StoreError -> anyhow::Error` chain with `.context()` annotations produces clear error messages. The pattern is applied uniformly.

4. **Well-chosen dependencies.** No unnecessary dependencies. Each external crate serves a clear purpose. The dependency count is minimal for a system of this complexity.

5. **Domain model fidelity.** The module structure mirrors the mathematical domain: quaternions, phasors, occurrences, neighborhoods, episodes, system. Each module owns its domain concept without leaking into adjacent concerns.

6. **Comprehensive CLI documentation.** Every command has `long_about` text, usage examples, and clear parameter descriptions. The CLI is self-documenting.

7. **Thoughtful operational features.** Dedup window for buffer, dirty flag for save optimization, WAL checkpoint on shutdown, GC with configurable retention, schema versioning with migrations.

---

## 12. Summary Scores

| Dimension | Score | Notes |
|-----------|-------|-------|
| Crate boundaries | 9/10 | Clean layering, minor time.rs impurity |
| Module cohesion | 8/10 | Compose is approaching threshold, salience misplaced |
| API surface | 8/10 | Coherent, dual-path re-exports are minor issue |
| Error handling | 8/10 | Consistent pattern, server.rs loses type info in one spot |
| Scalability readiness | 6/10 | Full-system save/load, single mutex, in-memory state |
| Test coverage | 9/10 | 282+ tests, main.rs is the gap |
| Dependency hygiene | 10/10 | Minimal, justified, well-layered |
| Documentation | 8/10 | CLI excellent, code comments good, no architecture docs |
| Technical debt | Low | No obsolete patterns, no dead code observed |
| Evolution potential | 7/10 | DAESystem approaching god-object threshold |

**Overall assessment: Strong architecture for a 0.x project.** The foundation is sound, the crate boundaries are well-drawn, and the code quality is high. The primary scaling concern is the full-system-in-memory model, which works today but will need incremental persistence for production-scale data. The refactoring opportunities are minor improvements, not urgent fixes.
