# am-cli Crate Review

Reviewed: 2026-03-13
Codebase: `/Users/alphab/Dev/LLM/DEV/helioy/attention-matters/crates/am-cli`
Version: 0.1.15

---

## File Surface

| File | LOC | Exports | Role |
|------|-----|---------|------|
| `src/main.rs` | 1,543 | 35 | CLI entry point, all command dispatch |
| `src/server.rs` | 1,675 | 1 (AmServer) | MCP stdio server, 12 tools |
| `src/sync.rs` | 1,085 | 9 | Claude Code transcript ingestion |
| `tests/cli.rs` | 619 | 0 | CLI integration tests |
| `tests/shutdown.rs` | 216 | 0 | Server shutdown integration tests |

Total: 5,138 LOC

---

## 1. Command Surface (main.rs, 1,543 LOC)

### Commands defined

| Command | Purpose |
|---------|---------|
| `serve` | Start MCP server on stdio (primary mode for Claude Code integration) |
| `query` | Query geometric memory, print recall |
| `ingest` | Ingest text files as memory episodes |
| `stats` | Show memory statistics |
| `export` | Dump state to v0.7.2-compatible JSON |
| `import` | Load state from JSON |
| `inspect` | Browse memory with five sub-modes (overview, conscious, episodes, neighborhoods, --query) |
| `sync` | Ingest Claude Code session transcripts (hook-triggered or bulk --all) |
| `gc` | Garbage collect cold occurrences, VACUUM SQLite |
| `forget` | Remove memories by term, episode UUID, or conscious UUID |
| `init` | Generate .am.config.toml |

**11 commands total.** The `inspect` command has five sub-modes (an enum `InspectMode`) and the `sync` command has two execution paths.

### LOC justification

The 1,543 LOC is large but not alarming given what it contains:

- ~230 lines of `Commands` enum with rich `long_about` and `after_help` doc strings (inline, terminal-rendered)
- ~200 lines of inspect rendering (`inspect_overview`, `inspect_episodes`, `inspect_neighborhoods`, `inspect_conscious`)
- ~470 lines of sync dispatch (`cmd_sync`, `cmd_sync_single`, `cmd_sync_discover`, `write_sync_log`)
- ~280 lines of gc/forget/init logic
- ~180 lines of process management (pidfile, shutdown, tracing init)

The argument in favor of the current structure: these are all lightweight dispatch and formatting functions with minimal business logic. Splitting into submodules would create indirection without meaningful gain.

The argument against: `cmd_sync_discover` (109 lines) and `inspect_overview` (145 lines) are the densest functions. Neither is complex enough to demand extraction, but if the inspect sub-modes grow they become candidates for an `inspect.rs` module.

**Assessment: acceptable. The density is documentation and terminal formatting, not logic.**

---

## 2. Server Design (server.rs, 1,675 LOC)

### Framework

`rmcp` 0.15 — a Rust MCP (Model Context Protocol) SDK. The server is **not an HTTP server**. It is a JSON-RPC 2.0 server over stdio, using rmcp's `#[tool_router]` and `#[tool_handler]` macros to derive tool dispatch. No network port is opened.

Protocol: MCP (JSON-RPC 2.0 framing, newline-delimited, stdio transport).

### Why only 1 export at 1,675 LOC

`AmServer` is the single public type. Everything else in the file is either:
- Private parameter structs (`QueryRequest`, `BufferRequest`, etc.) — 10 types
- Private state types (`ServerState`)
- Private helper methods on `AmServer` (`content_hash`, `clean_dedup_window`, `stats_json`)
- `#[tool_router]` impl block — the 12 tools (all private to the rmcp macro system)
- `#[tool_handler]` impl of `ServerHandler` (`get_info`)
- 730 lines of `#[cfg(test)]` unit tests (15 tests)

This is a deliberate encapsulation pattern, not a design flaw. The rmcp macro generates the public dispatch surface; callers only need `AmServer::new` and `AmServer::checkpoint_wal`.

### MCP tools exposed

| Tool | Purpose |
|------|---------|
| `am_query` | Primary recall: full context composition (budgeted or fixed) |
| `am_query_index` | Phase-1 two-phase retrieval: compact index, no full content |
| `am_retrieve` | Phase-2: fetch full content for specific neighborhood UUIDs |
| `am_activate_response` | Strengthen manifold connections after response |
| `am_salient` | Mark text as conscious memory; supports `supersedes` list |
| `am_buffer` | Buffer a conversation exchange; creates episode at threshold=3 |
| `am_ingest` | Ingest a document as a memory episode |
| `am_stats` | Memory statistics + DB size + activation distribution |
| `am_export` | Full state export as v0.7.2 JSON |
| `am_import` | Full state import, replaces current state |
| `am_feedback` | Relevance feedback (boost/demote) for recalled neighborhoods |
| `am_batch_query` | Batch queries with amortized IDF computation |

12 tools total. The `get_info` server instructions encode a full session lifecycle protocol for the AI agent consuming the server.

### Concurrency model

Single `Arc<Mutex<ServerState>>` wrapping the entire mutable state. All tool handlers acquire the same lock for their full execution. This is appropriate: the engine is compute-bound CPU work (no awaits within the critical section except for `store.save_system`). No deadlock risk since there is only one lock and handlers do not re-enter.

The Tokio runtime is `rt-multi-thread`, but the mutex ensures sequential tool execution, which is correct — the DAE state is not safe for concurrent mutation.

### Orphaned buffer flush

Both `am_query` and `am_query_index` flush any incomplete conversation buffer from a previous session at the start of the call. This is a deliberate "lazy consolidation" pattern: buffer exchanges during a session, and on the next session's first query, flush any leftovers into an episode. Duplicated logic between the two handlers is a minor maintenance risk but low priority.

### State architecture

`ServerState` holds:
- `system: DAESystem` — the in-memory geometric manifold (full state)
- `store: BrainStore` — SQLite persistence handle
- `rng: SmallRng` — deterministic random for quaternion placement
- `session_recalled: HashMap<Uuid, u32>` — per-session recall counts for diminishing returns
- `dedup_window: HashMap<u64, Instant>` — 60-second content hash window for buffer dedup

`DefaultHasher` is used for the dedup content hash. This is intentional (comment says "16 hex chars - sufficient for dedup within a 60-second window"), but `DefaultHasher` is not stable across Rust releases per the stdlib docs. A hash collision within the 60-second window would silently drop a buffered exchange. For a dedup window this is acceptable, but it is worth noting.

---

## 3. Sync (sync.rs, 1,085 LOC)

### What it syncs

Claude Code session transcripts. When Claude Code invokes the `PreCompact` or `Stop` hooks, it writes a JSON payload to stdin with `session_id` and `transcript_path`. The `am sync` command reads this payload, parses the JSONL transcript at the given path, extracts text content, and ingests it into the geometric memory system as named episodes.

### Two execution modes

**Hook-triggered (default):** stdin is not a terminal → read `HookInput` JSON → parse single session file → ingest episodes with replace semantics.

**Bulk discovery (`--all`):** walks `~/.claude/projects/<encoded-cwd>/` for `.jsonl` files → ingests all sessions using the simpler `extract_session_text` path (no episode chunking, just flat text per session).

The hook-triggered path uses `extract_episodes` (chunked, with sidechain support). The bulk path uses `extract_session_text` (flat). This is an intentional trade-off: single-session sync produces better episodic structure, bulk re-sync values simplicity and speed.

### External integrations

No network calls. All access is local filesystem reads. The only external process invoked is `git rev-parse --show-toplevel` (via `std::process::Command`) when looking up the Claude project directory — to handle git worktrees. No Claude API calls.

### Content filtering

- Skips tool_use and tool_result blocks
- Skips system prompts (detected by prefix heuristic)
- Skips file-history-snapshot entries
- Minimum 20-character length filter on text fragments
- Strips markdown via `pulldown-cmark`

### Sidechain handling

Sub-agent work (identified by `isSidechain: true` + `slug`/`agentId`) is grouped into separate named episodes per agent. This is architecturally correct for the DAE model.

---

## 4. Protocol Design

No REST API. No HTTP. The server is pure MCP over stdio JSON-RPC 2.0.

This is the correct choice for a Claude Code MCP server:
- Zero port management
- No auth surface (local process only)
- Claude Code spawns/owns the process lifetime
- rmcp handles all framing and dispatch

The CLI commands (query, ingest, stats, etc.) bypass the server entirely and talk directly to `am-store` + `am-core`. No duplication of the transport layer.

---

## 5. Error Handling

### Server handlers

All tool handlers return `Result<CallToolResult, McpError>`. Error paths use `McpError::internal_error(e.to_string(), None)` for storage failures and `McpError::invalid_params` for bad input (e.g., unknown feedback signal, empty UUID list). This is correct MCP error semantics.

Persistence failures (`store.save_system`) are logged as errors but do not abort the handler — callers get a successful tool result even if the persist failed. This is a deliberate leniency: a transient write failure should not terminate the AI agent's session. The trade-off is that state might not be persisted, but the in-memory state remains consistent.

### CLI commands

All commands use `anyhow::Result<()>` propagated to `main`. Errors print via anyhow's display chain. No structured error format for CLI output — appropriate for a terminal tool.

### Missing coverage

No validation of text input size in MCP tools. A caller could pass a very large string to `am_ingest` or `am_buffer` with no size limit enforced before the work begins. This is a local-only server so the attack surface is the AI agent itself, but it is worth noting for robustness.

---

## 6. Process Management

### PID file

Written to `<AM_DATA_DIR>/am-serve.pid` on startup. Uses the `AM_DATA_DIR` env var for the path, falling back to `am_store::default_base_dir`. On startup:
- If a stale pidfile exists (process dead), it is removed.
- If an alive pidfile exists, the server logs a warning but proceeds (coexisting with SQLite `busy_timeout`). This allows multiple serve instances against the same store, relying on SQLite WAL mode for serialization.

### Shutdown

`cmd_serve` races `service.waiting()` (stdin EOF) against `shutdown_signal()` (SIGINT, SIGTERM, SIGHUP). On shutdown:
- Calls `AmServer::checkpoint_wal()` — explicit WAL TRUNCATE checkpoint
- Removes pidfile
- Hard timeout of 5 seconds: if cleanup exceeds this, exits with code 1

Pre-handshake stdin EOF is handled gracefully (exits 0, no panic).

### No daemon mode

The server is always foreground, always stdio-attached. Claude Code manages its process lifecycle. This is the correct model for an MCP server.

---

## 7. CLI UX

- **Argument parser:** `clap` 4 with `derive` feature. All commands use `#[derive(Parser)]`.
- **Help text:** Rich `long_about` and `after_help` strings on every command, with ANSI bold formatting. Examples are inline and copy-pasteable.
- **Verbose flag:** Global `--verbose` that switches tracing from WARN to DEBUG, directed to stderr (correct for an MCP server — stdout is the JSON-RPC channel).
- **JSON output:** `inspect` command supports `--json` for machine-readable output.
- **Dry run:** `sync` and `gc` both support `--dry-run`.
- **Naming:** Consistent, lowercase, verb-noun. No inconsistencies.

One UX note: `ingest` requires at least one positional `files` argument even when `--dir` is provided (by clap's `required = true`). This is documented but slightly awkward — passing a file that also gets scanned by `--dir` creates a duplicate episode. The test explicitly documents this behavior ("3 episodes: first.md twice + second.md").

---

## 8. Authentication and Authorization

None. The MCP server operates on localhost stdio only. The Claude Code host process owns the pipe. There is no network exposure, no API key, no token. This is appropriate — the threat model is the local machine only.

The `BrainStore` is a SQLite file at a well-known path (`~/.attention-matters/brain.db` by default). Any local process with filesystem access can read or write it directly, bypassing the MCP layer. This is a property of the design (developer tool, not a multi-tenant service) rather than a vulnerability.

---

## 9. Test Coverage

### server.rs unit tests (15 tests, ~730 LOC within file)

Tests call tool methods directly on an in-memory `AmServer` (backed by `BrainStore::open_in_memory()`). Coverage includes:

- `am_stats` on empty store
- `am_ingest` creates episode and updates N
- `am_query` response structure (all required JSON fields)
- `am_salient` stores conscious neighborhoods
- `am_salient` with `<salient>` tag extraction
- `am_activate_response` activates occurrences
- `am_buffer` threshold behavior (episode creation at 3 exchanges)
- `am_buffer` dedup (identical content within window)
- `am_export` / `am_import` roundtrip
- Stats after multiple operations
- Orphaned buffer flush on `am_query`
- `am_salient` supersedes old memory
- `am_query_index` compact entry structure
- `am_retrieve` full content fetch
- `am_query` includes index field

Strong coverage of the tool behavior contracts. `am_feedback` and `am_batch_query` are not unit-tested here.

### tests/cli.rs integration tests (619 LOC, ~24 tests)

End-to-end process invocation via `assert_cmd`. Coverage:

- `stats` on fresh DB
- `ingest` file → `stats` reflects data
- `query` after ingest (non-empty output)
- `export` / `import` roundtrip (N and episode count match)
- `ingest --dir` directory scan
- Missing required arguments produce failures
- `inspect` all sub-modes + JSON output
- `sync --all --dry-run` finds sessions, no ingest
- `sync --all` ingests sessions, idempotent on re-run
- `sync` (hook stdin mode) ingests session, idempotent
- `sync` with no project directory
- `gc` on fresh DB, `gc --dry-run`, `gc` evicts with high floor
- `forget` term, not-found term, missing argument

### tests/shutdown.rs (216 LOC, 5 tests)

Process-level shutdown tests:
- Early stdin EOF (before MCP handshake) exits 0 quickly
- Post-handshake stdin EOF exits 0 quickly
- SIGTERM exits 0 quickly (unix only)
- Pidfile created on start, removed on clean shutdown
- WAL checkpoint on exit (WAL file is empty/absent after shutdown)

These tests drive an actual `am serve` process and verify the MCP handshake over JSON-RPC. This is excellent: the shutdown contract is tested at the OS level.

### Gaps

- `am_feedback` and `am_batch_query` have no dedicated tests (neither unit nor integration)
- `am_retrieve` error path (invalid UUID list) has a unit test but no CLI-level test
- Concurrent serve instances are not tested
- Large-input behavior (no size limit) is not tested

---

## 10. Dependencies

| Crate | Version | Purpose |
|-------|---------|---------|
| `rmcp` | 0.15 | MCP stdio server framework (the only heavy external dep specific to CLI) |
| `tokio` | 1 | Async runtime (multi-thread, io-std, signal, time) |
| `clap` | 4 | Argument parsing |
| `schemars` | 1 | JSON Schema derivation for MCP tool parameter types |
| `serde` + `serde_json` | 1 | Serialization |
| `anyhow` | 1 | Error handling |
| `rand` | 0.9 | SmallRng for quaternion placement |
| `tracing` + `tracing-subscriber` | 0.1 / 0.3 | Structured logging |
| `uuid` | 1 | UUIDs for neighborhoods |
| `pulldown-cmark` | 0.13.1 | Markdown stripping in sync (no default features) |
| `libc` | 0.2 | Unix signal sending in shutdown tests |
| `am-core` + `am-store` | workspace | Internal crates |

Dev dependencies: `assert_cmd`, `predicates`, `tempfile` — standard integration test utilities.

**Assessment:** Clean. No heavyweight or risky dependencies. `pulldown-cmark` with `default-features = false` is well-scoped. `rmcp` 0.15 is the MCP SDK — the expected choice.

---

## 11. Summary of Issues and Observations

### Strengths

1. **Protocol clarity.** No HTTP, no ports, no auth surface. Pure MCP stdio. The design is exactly right for Claude Code integration.
2. **Shutdown contract is production-quality.** 5-second timeout, explicit WAL checkpoint, pidfile lifecycle, pre-handshake EOF handling — all tested end-to-end.
3. **Test coverage is strong.** Unit tests in server.rs cover the tool contracts directly. CLI integration tests cover the full process lifecycle. Shutdown tests cover OS-level behavior.
4. **Help text quality.** The Commands enum carries detailed `long_about` and `after_help` with working examples. This is the kind of documentation that stays current because it is code.
5. **Replace semantics on sync.** Idempotent re-sync by episode name prevents duplicate episodes without requiring a tracking database.
6. **Two-phase retrieval design.** `am_query_index` + `am_retrieve` is a thoughtful optimization for large manifolds — lets the AI agent see a compact manifest before pulling full content.

### Issues

1. **`DefaultHasher` instability for dedup.** `DefaultHasher` is not guaranteed to be stable across Rust versions or even across process invocations (it is randomized in some configurations). For in-process, same-run dedup within a 60-second window, this is unlikely to cause problems in practice, but it should be `FxHasher` or a fixed-output hash if correctness of dedup matters.

2. **Orphaned buffer flush duplicated.** The flush-orphaned-buffer block (lines 210-224 in server.rs) appears in both `am_query` and `am_query_index`. This is 15 lines of identical logic. Extract to a helper method on `AmServer` or `ServerState`.

3. **No input size limits on MCP tools.** `am_ingest`, `am_buffer`, and `am_salient` accept unbounded text. A runaway caller (or a Claude session with a very large context) could cause memory pressure. Add a max byte limit with a descriptive error.

4. **`am_feedback` and `am_batch_query` have no tests.** These are non-trivial tools. `am_batch_query` especially — amortized IDF across multiple queries — merits unit test coverage of its output structure.

5. **`ingest --dir` + positional file creates duplicate episodes.** Documented in tests, but the UX is confusing. If `--dir` is provided, the positional `files` argument should be made optional (or `--dir` should implicitly satisfy the required constraint). Currently requires a workaround.

6. **ANSI escape codes unconditionally in `Commands` docs.** The `after_help` strings use `\x1b[1m` for bold. These display correctly in a terminal but produce garbage in CI logs or when help text is captured programmatically. Clap has `ColorChoice` support that could be used instead.

7. **`cmd_sync_discover` loads store after determining dry-run.** In the dry-run path, `open_store` is called at the top of `cmd_sync_discover` unconditionally (line 1253), but the store is only written in the real path. Minor: a `--dry-run` pass creates the store file unnecessarily. Low impact.

8. **No test for `am_gc` command via the CLI with `--target-mb` flag.** The size-based GC mode is untested at the integration level.
