---
title: attention-matters Architecture Alignment Spec
date: 2026-03-18
tags: [attention-matters, architecture, alignment, rust, mcp]
type: spec
status: active
---

# attention-matters Architecture Alignment Spec

Alignment plan between the current attention-matters codebase (v0.1.17) and the Helioy Rust Architecture Proposal.

## 1. Executive Summary

**Today**: attention-matters is a Rust workspace (resolver 3, edition 2024) with three crates: am-core (pure math, zero I/O), am-store (rusqlite persistence), am-cli (CLI + MCP server via rmcp 0.15). The workspace layout, dependency direction, and core/store/cli split already match the reference architecture. The codebase has 379 tests, CI with clippy/fmt/test/audit, benchmark regression gating, and a clean release pipeline.

**Where the proposal wants it to go**: Migrate from rmcp to manual JSON-RPC + tools.toml for MCP server consistency across the helioy ecosystem. Introduce a store trait in am-core for hexagonal architecture. Adopt cargo-nextest. Fix the known issues catalog (N+1 loads, missing indexes, format!-based SQL construction). Standardize justfile recipes and error handling patterns.

**Key insight**: attention-matters is closer to the reference architecture than the proposal suggests. The workspace layout, edition, resolver, dependency inheritance, and release profile are already aligned. The gaps are concentrated in two areas: (1) MCP server implementation (rmcp vs manual JSON-RPC) and (2) absence of a store trait boundary.

## 2. Gap Analysis

### 2.1 MCP Server: rmcp vs Manual JSON-RPC

**Current state**: `server.rs` (2,122 LOC) uses rmcp 0.15's `#[tool_router]` macro. Tool parameter types derive `schemars::JsonSchema` for automatic schema generation. The `AmServer` struct holds a `ToolRouter<Self>` and implements `ServerHandler`. Each tool handler is annotated with `#[tool(description = "...")]`.

**Target state**: Manual JSON-RPC over stdio with `tools.toml` as the single source of truth for tool schemas, descriptions, and parameter definitions. A `build.rs` generates `generated_schema.rs` and `generated_help.rs`.

**Gap severity**: **High**. This is the largest structural change. rmcp provides:
- Automatic JSON schema generation from Rust types
- Protocol routing (initialize, tools/list, tools/call dispatch)
- Transport management (stdio)
- Error type wrappers (`ErrorData`)

All of this must be replaced. The manual approach is approximately 100-150 lines of JSON-RPC routing plus the `tools.toml` + `build.rs` pipeline.

**What changes**:
- Remove `rmcp`, `schemars` dependencies
- Create `tools.toml` with all 12 tool definitions
- Create `build.rs` to generate schema and help text
- Replace `#[tool_router] impl AmServer` with a `match` dispatcher
- Replace `Parameters<T>` extraction with manual `serde_json::Value` parsing
- Replace `McpError` with a local error type
- Replace `CallToolResult` with manual JSON-RPC response construction
- Implement stdio transport loop (read line, parse JSON-RPC, dispatch, write response)

### 2.2 Store Trait Boundary

**Current state**: No store trait exists. `am-store` exports concrete types (`Store`, `BrainStore`). `server.rs` depends directly on `BrainStore`. All store methods are synchronous (rusqlite is inherently sync).

**Target state**: The proposal calls for an async trait in the core crate with `Send + Sync + 'static` bounds, and generic consumers (`McpServer<S: AmStore>`).

**Gap severity**: **Medium**. The proposal's async trait guidance was written primarily for context-matters (which uses sqlx's async API). attention-matters uses rusqlite, which is synchronous. Forcing async signatures on a sync store creates impedance mismatch without benefit for a single-client stdio server.

**Recommended adaptation**: Define a synchronous `AmStore` trait in am-core. rusqlite is sync; the trait is sync. The proposal's async guidance targets sqlx. For a single-client stdio server backed by rusqlite, async signatures create impedance mismatch without benefit. If a future HTTP adapter needs async, `spawn_blocking` wraps at that boundary.

**What changes**:
- Define `AmStore` trait covering the store surface used by server.rs
- Make `AmServer` generic over `S: AmStore`
- Implement `AmStore` for `BrainStore`
- Add an in-memory test implementation for tool handler unit tests

### 2.3 Error Handling

**Current state**: `am-store` uses a manual `StoreError` enum with `Display` and `Error` impls. Not `thiserror`. `am-cli` uses `anyhow`. MCP errors use rmcp's `ErrorData`.

**Target state**: `thiserror` in library crates.

**Gap severity**: **Low**. The current manual `StoreError` is functionally equivalent to a `thiserror` derive. Migration is mechanical: add `#[derive(thiserror::Error)]` and `#[error("...")]` attributes, remove manual `Display` and `Error` impls.

### 2.4 Testing Infrastructure

**Current state**: 379 tests. am-core has 200 unit tests + 7 integration tests + proptest + 8 doctests. am-store has 67 tests. am-cli has 60+ integration tests including process-level shutdown tests. No snapshot testing. No cargo-nextest. No MCP protocol-level subprocess tests (the cli.rs tests exercise tool handlers through the `AmServer` API, not through JSON-RPC).

**Target state**: cargo-nextest, insta snapshot tests for MCP response format, assert_cmd subprocess tests for the JSON-RPC loop.

**Gaps**:
- No `cargo-nextest` in justfile or CI
- No `insta` snapshot tests for tool response structures
- No subprocess-level MCP protocol tests (though the shutdown.rs tests do test at the process level)
- am-core has no benchmarks for the O(n^2) pairwise drift path (only the centroid drift bench exists)

### 2.5 Justfile Recipes

**Current state**: Has `build`, `test`, `fmt`, `clippy`, `check`, `install`, `bench`, `audit`. Missing: `check` does not include test. `test` uses `cargo test` not nextest.

**Target state**: Standardized recipes with nextest.

**Gap severity**: **Low**. Mechanical change.

### 2.6 CI Pipeline

**Current state**: Already has `dtolnay/rust-toolchain@stable`, `Swatinem/rust-cache@v2`, fmt, clippy, test, audit, and benchmark regression gating. Matches the reference architecture closely.

**Gap**: Uses `cargo test` instead of `cargo nextest run`.

**Gap severity**: **Low**.

### 2.7 Known Issues from PROJECT.md

The codebase review identified 7 high-priority, 10 medium-priority, and 13 low-priority issues. These are not architectural alignment items but several overlap with the migration work:

**Overlapping with migration**:
- ~~`compose.rs:337,361,389,457,463,469,569` - `partial_cmp().unwrap()` panics on NaN.~~ **Already fixed.** All production code uses `f64::total_cmp()`. The old `partial_cmp` calls only appear in test comments documenting the prior fix.
- `store.rs` full O(N) serialize on every write. The store trait design must account for the incremental persistence methods (`save_episode`, `save_neighborhood`, `save_occurrence_positions`, `batch_increment_activation`).
- `server.rs` - `am_feedback` and `am_batch_query` have no tests. Adding the store trait enables writing these tests with an in-memory impl.
- `schema.rs:227` and `store.rs:519` use `format!()` to construct SQL strings. Safe in practice (table name from hardcoded list, placeholder construction), but violates the principle of parameterized queries. Should be addressed explicitly.

## 3. Alignment Plan

### Phase 1: Foundation (no behavioral changes)

**Goal**: Prepare the codebase for the MCP migration without changing any user-visible behavior. All existing tests continue to pass.

1. **Migrate StoreError to thiserror** - Add `thiserror` dependency. Replace manual `Display`/`Error` impls with derive macros. Zero behavioral change.

2. **Move `ActivationStats` to am-core** - Currently defined in `am-store/src/store.rs` (6-line plain data struct, no rusqlite dependency). Move to am-core so the trait can reference it without am-core depending on am-store.

3. **Define AmStore trait** - Create a trait covering the store surface used by server.rs. The trait scope is **MCP server port only**: methods used by tool handlers and server lifecycle. CLI-only operations (`forget_*`, `import_json_file`, `export_json_file`, `mark_salient`) stay on `BrainStore` directly since the CLI wires the concrete type.

   Trait surface (derived from auditing every `store.` and `store.store().` call in server.rs):
   - `load_system() -> Result<DAESystem, Self::Error>`
   - `save_system(&DAESystem) -> Result<(), Self::Error>`
   - `save_episode(&Episode) -> Result<(), Self::Error>`
   - `save_neighborhood(&Episode, &Neighborhood) -> Result<(), Self::Error>`
   - `batch_increment_activation(&[Uuid]) -> Result<(), Self::Error>`
   - `batch_set_activation_counts(&[(Uuid, u32)]) -> Result<(), Self::Error>`
   - `save_occurrence_positions(&[(Uuid, Quaternion, DaemonPhasor)]) -> Result<(), Self::Error>`
   - `mark_superseded(old_id: Uuid, new_id: Uuid) -> Result<(), Self::Error>`
   - `append_buffer(user: &str, assistant: &str) -> Result<usize, Self::Error>`
   - `drain_buffer() -> Result<Vec<(String, String)>, Self::Error>`
   - `buffer_count() -> Result<usize, Self::Error>`
   - `activation_distribution() -> Result<ActivationStats, Self::Error>`
   - `db_size() -> u64`
   - `health_check() -> Result<(), Self::Error>`
   - `checkpoint_truncate() -> Result<(), Self::Error>`

   **Associated error type**: am-core is zero I/O and must not depend on rusqlite. `StoreError` contains `rusqlite::Error`. The trait uses an associated error type:

   ```rust
   pub trait AmStore {
       type Error: std::error::Error + Send + Sync + 'static;
       fn load_system(&self) -> Result<DAESystem, Self::Error>;
       // ...
   }
   ```

   `BrainStore` sets `type Error = StoreError`. `InMemoryStore` can use a lightweight test error or `std::convert::Infallible`. Consumers bound on `S: AmStore` propagate errors with `?` via `From` or `map_err`.

   **Placement**: The trait lives in am-core. am-core owns every type the trait references (`DAESystem`, `Episode`, `Neighborhood`, `Quaternion`, `DaemonPhasor`, `ActivationStats`). This follows the hexagonal pattern: core defines the port, am-store provides the adapter. The `InMemoryStore` test implementation lives in am-store or am-cli dev-dependencies to keep test-only code out of the math crate.

   **Sync, not async**: rusqlite is synchronous. The trait uses sync signatures. This is the correct choice for a single-client stdio server backed by rusqlite.

   **Excluded from trait** (CLI-only, not used by any MCP handler):
   - `forget_episode`, `forget_conscious`, `forget_term` - CLI `am forget` subcommands (main.rs lines 1165-1182)
   - `import_json_file`, `export_json_file` - CLI file-based convenience. The server uses am-core `import_json`/`export_json` free functions on the in-memory `DAESystem` + `save_system`.
   - `mark_salient` - CLI convenience that mutates `DAESystem` + calls `save_system`. The server handler (`am_salient`) uses `save_neighborhood` directly.

4. **Implement AmStore for BrainStore** - Straightforward. Most methods already exist on BrainStore; this formalizes the contract. The two-layer `store.store()` indirection collapses into the trait surface.

5. **Create InMemoryStore for testing** - Implement `AmStore` with `HashMap`-backed storage. `type Error` can be a simple enum or `std::convert::Infallible`. Enables tool handler unit tests without SQLite.

**Dependencies**: Item 1 is independent. Items 2-4 are sequential (move type, define trait, implement). Item 5 depends on item 3 (trait must exist). Item 1 can proceed in parallel with items 2-5.

### Phase 2: MCP Migration

**Goal**: Replace rmcp with manual JSON-RPC + tools.toml. The MCP tool surface remains identical from the agent's perspective.

6. **Create tools.toml** - Define all 12 tools with descriptions, parameter schemas, and CLI help text. Source the descriptions from the current `#[tool(description = "...")]` annotations.

7. **Create build.rs** - Generate `generated_schema.rs` (for MCP `tools/list`) and `generated_help.rs` (for clap help strings). Follow the context-matters pattern.

8. **Implement JSON-RPC stdio loop** - Replace rmcp's transport with a manual readline loop. Parse `JsonRpcRequest`, dispatch to handler, write `JsonRpcResponse`. Approximately 100-150 lines.

9. **Convert tool handlers** - Replace `Parameters<T>` extraction with manual `serde_json::from_value`. Replace `McpError` returns with local error type. Replace `CallToolResult` with `serde_json::Value` response construction. Each handler's business logic stays identical.

10. **Make AmServer generic** - `AmServer<S: AmStore>` instead of concrete `BrainStore`. Wire the generic through main.rs where the concrete type is chosen.

11. **Remove rmcp and schemars dependencies** - Clean up Cargo.toml. This removes proc-macro compile time.

12. **Add MCP protocol subprocess tests** - Use `assert_cmd` to spawn `am serve`, send initialize/tools-list/tools-call JSON-RPC messages, assert on responses.

**Dependencies**: 6 and 7 can proceed in parallel. 8 depends on 7 (needs generated schema). 9 depends on 8 (needs the new dispatch infrastructure). 10 depends on Phase 1 items 2-4 (needs the trait). 11 depends on 9 (all rmcp usage removed). 12 depends on 9 (server works without rmcp).

### Phase 3: Quality and Polish

**Goal**: Bring testing, CI, and tooling to the reference standard.

13. **Switch to cargo-nextest** - Update justfile and CI. Drop-in replacement.

14. **Add insta snapshot tests** - Snapshot the JSON output of each MCP tool handler. Catches unintended format changes.

15. **Add missing tool handler tests** - `am_feedback` and `am_batch_query` currently have no tests. The in-memory store from Phase 1 enables these.

16. **Fix format!()-based SQL construction** - `schema.rs:227` interpolates a table name into SQL via `format!()`. `store.rs:519` constructs a DELETE with format-based placeholders. Replace with parameterized queries or const table name validation.

17. **Address remaining known issues** - drain_buffer race window, missing indexes, activation_count overflow, token_count allocation. These are independent bug fixes that can be tackled in any order.

18. **Extract compose.rs god module** - Split into `scoring.rs`, `salient.rs`, `recency.rs` as identified in PROJECT.md. compose.rs is 2,478 LOC; this brings each module under 800 LOC.

**Dependencies**: 13 and 14 are independent. 15 depends on Phase 1 item 4 (in-memory store). 16 and 17 are independent. 18 is independent but should wait until Phase 2 is stable.

## 4. API Surface Changes

### 4.1 New: AmStore Trait

```rust
// crates/am-core/src/store.rs
pub trait AmStore {
    type Error: std::error::Error + Send + Sync + 'static;

    fn load_system(&self) -> Result<DAESystem, Self::Error>;
    fn save_system(&self, system: &DAESystem) -> Result<(), Self::Error>;
    fn save_episode(&self, episode: &Episode) -> Result<(), Self::Error>;
    fn save_neighborhood(&self, episode: &Episode, neighborhood: &Neighborhood) -> Result<(), Self::Error>;
    fn batch_increment_activation(&self, ids: &[Uuid]) -> Result<(), Self::Error>;
    fn batch_set_activation_counts(&self, batch: &[(Uuid, u32)]) -> Result<(), Self::Error>;
    fn save_occurrence_positions(
        &self,
        batch: &[(Uuid, Quaternion, DaemonPhasor)],
    ) -> Result<(), Self::Error>;
    fn mark_superseded(&self, old_id: Uuid, new_id: Uuid) -> Result<(), Self::Error>;
    fn append_buffer(&self, user: &str, assistant: &str) -> Result<usize, Self::Error>;
    fn drain_buffer(&self) -> Result<Vec<(String, String)>, Self::Error>;
    fn buffer_count(&self) -> Result<usize, Self::Error>;
    fn activation_distribution(&self) -> Result<ActivationStats, Self::Error>;
    fn db_size(&self) -> u64;
    fn health_check(&self) -> Result<(), Self::Error>;
    fn checkpoint_truncate(&self) -> Result<(), Self::Error>;
}
```

**Associated error type**: am-core is zero I/O; it cannot depend on rusqlite. The associated `type Error` lets `BrainStore` set `Error = StoreError` (which wraps `rusqlite::Error`), while `InMemoryStore` can use a trivial error type. Consumers bound on `S: AmStore` and use `map_err` or `From` for error propagation.

**Trait scope**: MCP server port only (15 methods). CLI-only operations (`forget_*`, file-based import/export, `mark_salient`) stay on `BrainStore` and are not part of the trait. This keeps `InMemoryStore` minimal and the trait focused on its purpose: enabling generic `AmServer<S>` and test doubles.

### 4.2 Changed: AmServer Becomes Generic

```rust
// Before
pub struct AmServer {
    state: Arc<Mutex<ServerState>>,
    tool_router: ToolRouter<Self>,  // rmcp type
}

// After
pub struct AmServer<S: AmStore> {
    state: Arc<Mutex<ServerState<S>>>,
}
```

### 4.3 Removed: rmcp Types

All `rmcp::*` imports are removed. `schemars::JsonSchema` derives are removed from parameter types. Parameter types become plain `serde::Deserialize` structs.

### 4.4 Added: JSON-RPC Types

Local types (~50 LOC):
- `JsonRpcRequest { jsonrpc, id, method, params }`
- `JsonRpcResponse { jsonrpc, id, result, error }`
- `JsonRpcError { code, message, data }`

### 4.5 Added: tools.toml

Single source of truth for 12 tool definitions. Each tool entry contains:
- `mcp_description` - tool description for MCP tools/list
- `cli_name` - corresponding CLI subcommand name (where applicable)
- `cli_about` - CLI help text
- `[tools.{name}.params.{param}]` - parameter name, type, description, required flag

## 5. Data Model Changes

**None.** The SQLite schema (version 5), wire format (v0.7.2 JSON), and in-memory data structures (`DAESystem`, `Episode`, `Neighborhood`, `Occurrence`) are unchanged. The migration is purely at the transport and API layer.

The store trait formalizes the existing BrainStore interface without adding or removing any persistence operations.

## 6. Migration Strategy

### Principle: No Flag Day

Each phase produces a working, testable system. The MCP tool surface is identical before and after migration. Agents calling am_query, am_ingest, etc. see no behavioral difference.

### Phase 1 Execution (estimated: 2-3 focused sessions)

1. Create a feature branch from main
2. Land thiserror migration as a standalone commit (purely mechanical)
3. Land AmStore trait + BrainStore impl + InMemoryStore in one commit
4. Verify all 379 existing tests pass
5. PR and merge

### Phase 2 Execution (estimated: 3-4 focused sessions)

1. Branch from Phase 1
2. Create tools.toml by extracting descriptions from current server.rs annotations
3. Create build.rs and verify generated code matches current rmcp-generated schemas
4. Build the JSON-RPC stdio loop alongside the existing rmcp server (temporary dual-path)
5. Port one tool handler (am_stats, the simplest) to the new path and verify
6. Port remaining 11 handlers
7. Make AmServer generic over AmStore
8. Remove rmcp and schemars from Cargo.toml
9. Add subprocess MCP protocol tests
10. Verify all existing tests pass, then the new subprocess tests
11. PR and merge

### Phase 3 Execution (estimated: 2 sessions)

1. Branch from Phase 2
2. Add nextest, insta snapshots, missing handler tests
3. Fix remaining known issues from PROJECT.md
4. Extract compose.rs sub-modules
5. PR and merge

### Rollback

Each phase is independently revertable. If Phase 2 encounters problems, Phase 1 changes remain valid. The feature branch strategy ensures main stays stable.

## 7. Risk Assessment

### High Risk

| Risk | Mitigation |
|------|------------|
| MCP protocol incompatibility after rmcp removal | Subprocess tests (Phase 2, item 9) verify the full JSON-RPC handshake. Run against Claude Code before merging. |
| Tool schema drift between rmcp-generated and tools.toml-generated schemas | Compare generated schemas byte-for-byte during migration. Write a test that asserts schema equality. |

### Medium Risk

| Risk | Mitigation |
|------|------------|
| AmStore trait surface is wrong (missing methods) | Audit every `store.` call in server.rs and main.rs before defining the trait. The list in section 4.1 is derived from this audit. |
| Performance regression from removing rmcp's optimized routing | The routing is a single `match` on method name. No measurable overhead. Existing benchmark gate catches regressions. |
| compose.rs extraction introduces bugs | Extract only after Phase 2 is stable and merged. Each extraction is a pure refactor with existing test coverage. |

### Low Risk

| Risk | Mitigation |
|------|------------|
| tools.toml format diverges from context-matters | Copy the exact TOML schema from context-matters. Both use the same build.rs template. |
| InMemoryStore behavior diverges from SQLite store | Keep the in-memory impl minimal. Use it for tool handler tests, not for integration tests. Integration tests keep using real SQLite. |

## 8. Success Criteria

### Phase 1
- [ ] `StoreError` uses `thiserror` derive
- [x] All `partial_cmp().unwrap()` in compose.rs replaced with `total_cmp()` (already done)
- [ ] `ActivationStats` moved from am-store to am-core
- [ ] `AmStore` trait defined in am-core with associated error type (15 methods)
- [ ] `BrainStore` implements `AmStore`
- [ ] `InMemoryStore` implements `AmStore` with basic functionality
- [ ] All 379 existing tests pass
- [ ] `just check` passes

### Phase 2
- [ ] `tools.toml` defines all 12 MCP tools
- [ ] `build.rs` generates schema and help text from tools.toml
- [ ] Manual JSON-RPC stdio loop replaces rmcp transport
- [ ] All tool handlers ported to manual dispatch
- [ ] `AmServer<S: AmStore>` is generic over the store trait
- [ ] `rmcp` and `schemars` removed from Cargo.toml
- [ ] Subprocess MCP protocol tests pass (initialize, tools/list, tools/call)
- [ ] Claude Code integration test: `claude mcp add am -- am serve` works, all tools callable
- [ ] No change in MCP tool names, parameter schemas, or response formats

### Phase 3
- [ ] `just test` uses `cargo nextest run --workspace`
- [ ] CI uses nextest
- [ ] insta snapshot tests cover all 12 tool response formats
- [ ] `am_feedback` and `am_batch_query` have dedicated tests
- [ ] `format!()`-based SQL in `schema.rs:227` and `store.rs:519` replaced with parameterized queries
- [ ] compose.rs split into sub-modules (each under 800 LOC)
- [ ] Missing indexes added (episodes.is_conscious, occurrences.activation_count, neighborhoods.episode_id+epoch)
