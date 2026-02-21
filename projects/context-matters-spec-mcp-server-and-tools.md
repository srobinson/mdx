---
title: "context-matters: MCP Server and Tools Specification"
type: project
tags: [context-matters, mcp, rust, tools, helioy]
status: draft
created: 2026-03-14
updated: 2026-03-14
---

## 1. Overview

This document specifies the MCP server struct, all 9 `cx_*` tools, and the server instructions for context-matters. The server lives in `cm-cli/src/mcp/` and uses manual JSON-RPC over stdio (the same pattern as fmm).

All tool documentation is centralized in `tools.toml` at the project root. `build.rs` reads tools.toml at compile time and generates:
- `src/mcp/generated_schema.rs` for the MCP `tools/list` response
- `src/cli/generated_help.rs` for CLI `--help` text
- `templates/SKILL.md` for Claude Code skill documentation

This ensures parity across MCP, CLI, and future web app transports.

Foundation documents (approved, not revisited):
- Schema and Storage Layer Specification (DDL, scope paths, hashing, concurrency)
- Core Types and ContextStore Trait Specification (all Rust types, 17 trait methods)
- Project Scaffold and Plugin Integration Spec (crate layout, dependencies)

## 2. Server Architecture

context-matters uses the same manual JSON-RPC over stdio pattern as fmm. No rmcp dependency. The MCP protocol is simple enough that a library adds more complexity than it removes.

### 2.1 McpServer Struct

```rust
use std::sync::Arc;
use cm_store::CmStore;
use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use std::io::{self, BufRead, Write};

mod schema;
mod tools;

const PROTOCOL_VERSION: &str = "2024-11-05";

/// Maximum input size for text-accepting tool fields (1 MB).
const MAX_INPUT_BYTES: usize = 1_048_576;

/// Maximum number of IDs in a batch request.
const MAX_BATCH_IDS: usize = 100;

/// Default result limit for retrieval tools.
const DEFAULT_LIMIT: u32 = 20;

/// Maximum result limit.
const MAX_LIMIT: u32 = 200;

#[derive(Debug, Deserialize)]
struct JsonRpcRequest {
    #[serde(rename = "jsonrpc")]
    _jsonrpc: String,
    id: Option<Value>,
    method: String,
    #[serde(default)]
    params: Option<Value>,
}

#[derive(Debug, Serialize)]
struct JsonRpcResponse {
    jsonrpc: String,
    id: Value,
    #[serde(skip_serializing_if = "Option::is_none")]
    result: Option<Value>,
    #[serde(skip_serializing_if = "Option::is_none")]
    error: Option<JsonRpcError>,
}

#[derive(Debug, Serialize)]
pub struct JsonRpcError {
    pub code: i32,
    pub message: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub data: Option<Value>,
}

pub struct McpServer {
    store: Arc<CmStore>,
}

impl McpServer {
    pub fn new(store: CmStore) -> Self {
        Self {
            store: Arc::new(store),
        }
    }

    /// Checkpoint the WAL on shutdown.
    pub async fn checkpoint_wal(&self) {
        if let Err(e) = self.store.checkpoint_wal().await {
            tracing::warn!("WAL checkpoint failed: {e}");
        }
        tracing::info!("WAL checkpoint complete");
    }

    /// Run the JSON-RPC stdio loop.
    ///
    /// This uses blocking `stdin.lock().lines()` inside an async fn.
    /// Safe for v1 because: (1) run() is called directly from main(),
    /// not via tokio::spawn(), so Send is not required; (2) the MCP
    /// stdio protocol is single-client sequential request/response;
    /// (3) there is no concurrent work to preempt. If the server
    /// moves to a concurrent transport (HTTP, SSE), this loop must
    /// be replaced with tokio::io::BufReader over tokio::io::stdin().
    pub async fn run(&self) -> anyhow::Result<()> {
        let stdin = io::stdin();
        let mut stdout = io::stdout();

        for line in stdin.lock().lines() {
            let line = line?;
            if line.is_empty() {
                continue;
            }

            let request: JsonRpcRequest = match serde_json::from_str(&line) {
                Ok(req) => req,
                Err(e) => {
                    let error_response = JsonRpcResponse {
                        jsonrpc: "2.0".to_string(),
                        id: Value::Null,
                        result: None,
                        error: Some(JsonRpcError {
                            code: -32700,
                            message: format!("Parse error: {e}"),
                            data: None,
                        }),
                    };
                    writeln!(stdout, "{}", serde_json::to_string(&error_response)?)?;
                    stdout.flush()?;
                    continue;
                }
            };

            let response = self.handle_request(&request).await;

            if let Some(resp) = response {
                let write_result = writeln!(stdout, "{}", serde_json::to_string(&resp)?)
                    .and_then(|_| stdout.flush());
                if let Err(e) = write_result {
                    if e.kind() == std::io::ErrorKind::BrokenPipe {
                        return Ok(());
                    }
                    return Err(e.into());
                }
            }
        }

        Ok(())
    }

    async fn handle_request(&self, request: &JsonRpcRequest) -> Option<JsonRpcResponse> {
        let id = request.id.clone().unwrap_or(Value::Null);

        let result = match request.method.as_str() {
            "initialize" => self.handle_initialize(),
            "notifications/initialized" => return None,
            "tools/list" => Ok(schema::tool_list()),
            "tools/call" => self.handle_tool_call(&request.params).await,
            "ping" => Ok(json!({})),
            _ => Err(JsonRpcError {
                code: -32601,
                message: format!("Method not found: {}", request.method),
                data: None,
            }),
        };

        Some(match result {
            Ok(value) => JsonRpcResponse {
                jsonrpc: "2.0".to_string(),
                id,
                result: Some(value),
                error: None,
            },
            Err(error) => JsonRpcResponse {
                jsonrpc: "2.0".to_string(),
                id,
                result: None,
                error: Some(error),
            },
        })
    }

    fn handle_initialize(&self) -> Result<Value, JsonRpcError> {
        Ok(json!({
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {
                "tools": {}
            },
            "serverInfo": {
                "name": "cm",
                "version": env!("CARGO_PKG_VERSION"),
                "instructions": SERVER_INSTRUCTIONS
            }
        }))
    }

    async fn handle_tool_call(&self, params: &Option<Value>) -> Result<Value, JsonRpcError> {
        let params = params.as_ref().ok_or_else(|| JsonRpcError {
            code: -32602,
            message: "Missing params".to_string(),
            data: None,
        })?;

        let tool_name = params.get("name").and_then(|v| v.as_str())
            .ok_or_else(|| JsonRpcError {
                code: -32602,
                message: "Missing tool name".to_string(),
                data: None,
            })?;

        let arguments = params.get("arguments").cloned().unwrap_or(json!({}));

        let result = match tool_name {
            "cx_recall"  => tools::cx_recall(&self.store, &arguments).await,
            "cx_store"   => tools::cx_store(&self.store, &arguments).await,
            "cx_deposit" => tools::cx_deposit(&self.store, &arguments).await,
            "cx_browse"  => tools::cx_browse(&self.store, &arguments).await,
            "cx_get"     => tools::cx_get(&self.store, &arguments).await,
            "cx_update"  => tools::cx_update(&self.store, &arguments).await,
            "cx_forget"  => tools::cx_forget(&self.store, &arguments).await,
            "cx_stats"   => tools::cx_stats(&self.store, &arguments).await,
            "cx_export"  => tools::cx_export(&self.store, &arguments).await,
            _ => Err(format!("Unknown tool: {tool_name}")),
        };

        match result {
            Ok(value) => Ok(json!({
                "content": [{"type": "text", "text": value}]
            })),
            Err(e) => Ok(json!({
                "content": [{"type": "text", "text": format!("ERROR: {e}")}]
            })),
        }
    }
}
```

### 2.2 Error Conversion

```rust
use cm_core::CmError;

/// Convert a CmError to an actionable error string.
///
/// Each error variant produces a human/agent-readable message with
/// recovery guidance. Used by tool handlers.
fn cm_err_to_string(e: CmError) -> String {
    match e {
        CmError::EntryNotFound(id) =>
            format!("Entry '{id}' not found. Verify the ID using cx_browse or cx_recall."),
        CmError::ScopeNotFound(path) =>
            format!("Scope '{path}' does not exist. Use cx_stats to list available scopes, \
                     or create it by storing an entry with a new scope_path."),
        CmError::DuplicateContent(existing_id) =>
            format!("Duplicate content: an active entry with this content already exists \
                     (id: {existing_id}). Use cx_update to modify the existing entry, \
                     or cx_forget it first."),
        CmError::InvalidScopePath(e) =>
            format!("Invalid scope_path: {e}. Format: 'global', 'global/project:<id>', \
                     'global/project:<id>/repo:<id>', or \
                     'global/project:<id>/repo:<id>/session:<id>'. \
                     Identifiers must be lowercase alphanumeric with hyphens."),
        CmError::InvalidEntryKind(s) =>
            format!("Invalid kind '{s}'. Valid values: fact, decision, preference, lesson, \
                     reference, feedback, pattern, observation."),
        CmError::InvalidRelationKind(s) =>
            format!("Invalid relation kind '{s}'. Valid values: supersedes, relates_to, \
                     contradicts, elaborates, depends_on."),
        CmError::Validation(msg) => msg,
        CmError::ConstraintViolation(msg) =>
            format!("Constraint violation: {msg}"),
        CmError::Json(e) => format!("[json] {e}"),
        CmError::Database(msg) => format!("[database] {msg}"),
        CmError::Internal(msg) => format!("[internal] {msg}"),
    }
}

/// Reject input exceeding the per-field byte limit.
fn check_input_size(value: &str, field: &str) -> Result<(), String> {
    if value.len() > MAX_INPUT_BYTES {
        return Err(format!("{field} exceeds {MAX_INPUT_BYTES} byte limit"));
    }
    Ok(())
}

/// Clamp a limit value to the allowed range.
fn clamp_limit(limit: Option<u32>) -> u32 {
    limit.unwrap_or(DEFAULT_LIMIT).min(MAX_LIMIT).max(1)
}
```

### 2.3 Reserved Trait Methods

The `ContextStore` trait includes `get_relations_from` and `get_relations_to` methods that are not exposed through any MCP tool in v1. These are reserved for future expansion (e.g., a `cx_relations` tool for graph exploration). They are used internally by `cx_store` when processing `supersedes` (which creates a `Supersedes` relation via `supersede_entry`).

### 2.4 Concurrency Model

Unlike attention-matters (which uses `Arc<Mutex<ServerState>>` because its in-memory DAESystem requires exclusive access), context-matters delegates concurrency to sqlx's connection pools. The `CmStore` holds a write pool (1 connection) and a read pool (4 connections). No server-level mutex is needed. Multiple read tools can execute concurrently. Write tools serialize through the single-connection write pool.

## 3. Tool Documentation (tools.toml)

All tool descriptions, parameter docs, and help text are defined in `tools.toml` at the project root. `build.rs` reads this file and generates:
- `src/mcp/generated_schema.rs` for the MCP `tools/list` response
- `src/cli/generated_help.rs` for CLI clap help constants
- `templates/SKILL.md` for Claude Code skill documentation

This follows the fmm pattern exactly. See `~/Dev/LLM/DEV/helioy/fmm/tools.toml` and `~/Dev/LLM/DEV/helioy/fmm/build.rs` for the reference implementation.

The complete tools.toml content for context-matters is authored at `~/.mdx/projects/context-matters-tools.toml`. Copy this file to the workspace root during scaffold setup.

### 3.1 tools.toml Structure

Each tool entry has:
- `mcp_description`: optimized for LLM consumption (concise, action-oriented)
- `cli_about`: optimized for human terminal use (may include formatting, examples)
- Per-parameter entries with both `mcp_description` and `cli_help` variants

```toml
# Single source of truth for all tool documentation.
# build.rs reads this file and generates:
#   src/mcp/generated_schema.rs  — MCP tool list JSON
#   src/cli/generated_help.rs    — CLI help string constants
#   templates/SKILL.md           — Claude Code skill documentation

[skill]
workflow = """
## Context Management Workflow
...
"""

[tools.cx_recall]
cli_name        = "recall"
mcp_description = "Search and retrieve context entries..."
cli_about       = "Search and retrieve context entries from the store..."

[[tools.cx_recall.params]]
name            = "query"
type            = "string"
mcp_description = "Search query text. Supports FTS5 syntax..."
cli_help        = "FTS5 search query (prefix: rust*, phrase: \"scope path\", boolean: AND/OR/NOT)"
cli_flag        = "query"

# ... (full tools.toml content specified in Section 5 tool definitions below)
```

### 3.2 build.rs

Lives at `crates/cm-cli/build.rs`. Clone from `~/Dev/LLM/DEV/helioy/fmm/build.rs` with these changes:
- Read `../../tools.toml` (workspace root, not crate root)
- Tool prefix: `cx_` instead of `fmm_`
- Server name: `cm` instead of `fmm`
- Skill description updated for context-matters
- Output paths: `src/mcp/generated_schema.rs` and `src/cli/generated_help.rs` relative to crate root
- Add `cargo:rerun-if-changed=../../tools.toml` for correct incremental compilation

## 4. Server Instructions

```rust
const SERVER_INSTRUCTIONS: &str = "\
You have a structured context store for persistent project knowledge across sessions.

SESSION LIFECYCLE:
1. RECALL: At session start, call cx_recall with a summary of the user's task or question. \
   This returns relevant context entries (facts, decisions, preferences, lessons) from \
   the current scope and all ancestor scopes. Use returned context silently.
2. STORE: When you discover important facts, decisions, user preferences, lessons learned, \
   or recurring patterns, call cx_store to persist them. Classify entries by kind for \
   effective retrieval later.
3. FEEDBACK: When the user corrects you or clarifies a preference, store it as kind='feedback'. \
   Feedback entries receive highest recall priority.

TOOLS OVERVIEW:
- cx_recall: Search and retrieve context. Primary retrieval tool. Call at session start.
- cx_store: Store a single context entry with structured metadata.
- cx_deposit: Batch-store conversation exchanges for future reference.
- cx_browse: List entries with filters and pagination. For inventory, not search.
- cx_get: Fetch full content for specific entry IDs (two-phase retrieval).
- cx_update: Partially update an existing entry.
- cx_forget: Soft-delete entries that are no longer relevant.
- cx_stats: View store statistics and scope breakdown.
- cx_export: Export entries as JSON for backup.

SCOPE MODEL:
Scopes form a hierarchy: global > project > repo > session. \
Context at broader scopes is visible at narrower scopes. \
When storing entries, use the narrowest appropriate scope. \
Global scope is for cross-project knowledge (user preferences, universal patterns). \
Project scope is for project-level decisions and conventions. \
Repo scope is for codebase-specific facts. \
Session scope is for ephemeral task context.

PRINCIPLES:
- Be selective. Store genuinely reusable knowledge, not routine observations.
- Classify accurately. The kind field drives recall priority and filtering.
- Use specific scope paths. Overly broad scoping pollutes recall for unrelated work.
- Do not mention the context system to the user unless asked.
- If cx_recall returns empty results, that is fine. The scope is new.";
```

## 5. Tool Definitions

### 5.1 cx_recall

Primary retrieval tool. Combines FTS5 keyword search with scope resolution (ancestor walk). Called at session start to load relevant context.

#### Parameters

```rust
#[derive(Debug, Deserialize)]
struct CxRecallParams {
    /// Search query text. Supports FTS5 syntax: prefix queries (rust*),
    /// phrase queries ("scope path"), and boolean operators (AND, OR, NOT).
    /// When omitted, returns all entries at the target scope via scope resolution.
    #[serde(default)]
    query: Option<String>,

    /// Scope path to search within. Retrieves entries from this scope and
    /// all ancestor scopes (e.g., "global/project:helioy/repo:nancyr" also
    /// searches "global/project:helioy" and "global").
    /// Default: "global" (searches everything).
    #[serde(default)]
    scope: Option<String>,

    /// Filter to specific entry kinds. Multiple values combine with OR.
    /// Valid values: fact, decision, preference, lesson, reference, feedback, pattern, observation.
    #[serde(default)]
    kinds: Vec<String>,

    /// Filter to entries with any of these tags.
    #[serde(default)]
    tags: Vec<String>,

    /// Maximum number of entries to return. Default: 20, max: 200.
    #[serde(default)]
    limit: Option<u32>,

    /// Maximum token budget for the response. When set, results are trimmed
    /// to fit within this budget, prioritizing higher-relevance entries.
    /// Follows the am_query budget pattern.
    #[serde(default)]
    max_tokens: Option<u32>,
}
```

#### Response Format

Returns a JSON object with a `results` array. Each result includes metadata for two-phase retrieval (title and snippet only, not full body). Use `cx_get` with the returned IDs to fetch full content.

```json
{
  "results": [
    {
      "id": "019503a1-...",
      "scope_path": "global/project:helioy",
      "kind": "decision",
      "title": "Use sqlx over diesel for context-matters",
      "snippet": "First 200 chars of body...",
      "confidence": "high",
      "tags": ["architecture", "database"],
      "created_by": "agent:claude-code",
      "updated_at": "2026-03-14T00:15:00.000Z"
    }
  ],
  "returned": 12,
  "scope_chain": ["global/project:helioy/repo:nancyr", "global/project:helioy", "global"],
  "token_estimate": 1250
}
```

#### Trait Methods Called

- When `query` is set: `ContextStore::search(query, scope_path, limit)` for FTS5 search with optional scope filtering.
- When `query` is omitted: `ContextStore::resolve_context(scope_path, kinds, limit)` for scope-resolution-based retrieval.
- In both cases, results are post-filtered by `kinds` and `tags` if specified.
- When combining `query` with `kinds`/`tags` filters, the result count may be lower than `limit` because filtering is applied after FTS5 ranking. For example, requesting `limit: 20` with a tag filter may return fewer than 20 entries if most FTS5 matches lack the requested tag. This is acceptable for v1. In v2, tag and kind filters will be pushed into the SQL query.

#### Error Cases

| Condition | Error Message |
|-----------|--------------|
| Invalid `scope` | `"Invalid scope_path: ... Format: 'global', 'global/project:<id>', ..."` |
| Invalid `kinds` entry | `"Invalid kind 'xxx'. Valid values: fact, decision, preference, ..."` |
| Query too long | `"query exceeds 1048576 byte limit"` |

#### Example

```
cx_recall(query: "sqlx migration", scope: "global/project:helioy")
```

### 5.2 cx_store

Store a single context entry with structured metadata.

#### Parameters

```rust
#[derive(Debug, Deserialize)]
struct CxStoreParams {
    /// Short summary of the entry. Displayed in search results.
    title: String,

    /// Full content body in markdown.
    body: String,

    /// Entry classification. Determines recall priority.
    /// Valid values: fact, decision, preference, lesson, reference, feedback, pattern, observation.
    kind: String,

    /// Target scope path. The scope is auto-created if it does not exist.
    /// Default: "global".
    #[serde(default = "default_scope")]
    scope_path: String,

    /// Attribution. Format: "source_type:identifier".
    /// Default: "agent:claude-code".
    #[serde(default = "default_created_by")]
    created_by: String,

    /// Freeform tags for categorization.
    #[serde(default)]
    tags: Vec<String>,

    /// Confidence level: "high", "medium", or "low".
    #[serde(default)]
    confidence: Option<String>,

    /// Source URL or path for reference entries.
    #[serde(default)]
    source: Option<String>,

    /// ISO 8601 expiry timestamp. After this time the entry is considered stale.
    #[serde(default)]
    expires_at: Option<String>,

    /// Numeric priority for manual ordering. Higher values surface first.
    #[serde(default)]
    priority: Option<i32>,

    /// ID of an existing entry that this new entry supersedes.
    /// The old entry is soft-deleted and linked via a 'supersedes' relation.
    #[serde(default)]
    supersedes: Option<String>,
}

fn default_scope() -> String { "global".to_string() }
fn default_created_by() -> String { "agent:claude-code".to_string() }
```

#### Behavior

1. Parse and validate `scope_path` as a `ScopePath`.
2. Parse and validate `kind` as an `EntryKind`.
3. If the scope does not exist, auto-create it (and any missing ancestor scopes). This enables agents to store entries without a separate scope creation step.
4. Build `EntryMeta` from `tags`, `confidence`, `source`, `expires_at`, `priority`.
5. If `supersedes` is set, call `ContextStore::supersede_entry(old_id, new_entry)`. Otherwise call `ContextStore::create_entry(new_entry)`.

#### Response Format

```json
{
  "id": "019503a1-...",
  "scope_path": "global/project:helioy",
  "kind": "decision",
  "title": "Use sqlx over diesel",
  "content_hash": "a1b2c3d4...",
  "created_at": "2026-03-14T00:15:00.000Z",
  "superseded": null,
  "message": "Entry stored."
}
```

When `supersedes` is set:
```json
{
  "id": "019503a2-...",
  "scope_path": "global/project:helioy",
  "kind": "decision",
  "title": "Use sqlx over diesel (updated rationale)",
  "content_hash": "e5f6a7b8...",
  "created_at": "2026-03-14T00:20:00.000Z",
  "superseded": "019503a1-...",
  "message": "Entry stored. Superseded entry 019503a1-..."
}
```

#### Error Cases

| Condition | Error Message |
|-----------|--------------|
| Empty title | `"Validation error: title cannot be empty"` |
| Empty body | `"Validation error: body cannot be empty"` |
| Invalid kind | `"Invalid kind 'xxx'. Valid values: fact, decision, ..."` |
| Invalid scope_path | `"Invalid scope_path: ..."` |
| Duplicate content | `"Duplicate content: an active entry with this content already exists (id: ...)"` |
| Invalid supersedes ID | `"Entry '<id>' not found. Verify the ID using cx_browse or cx_recall."` |
| Body too large | `"body exceeds 1048576 byte limit"` |
| Invalid confidence | `"Invalid confidence 'xxx'. Valid values: high, medium, low."` |

#### Trait Methods Called

- `ContextStore::create_scope` (if scope auto-creation needed, called for each missing ancestor)
- `ContextStore::create_entry` or `ContextStore::supersede_entry`

### 5.3 cx_deposit

Batch deposit of conversation exchanges for future context. Designed for capturing session content that might be useful in future sessions, similar to `am_buffer` but with structured storage rather than geometric embedding.

#### Parameters

```rust
#[derive(Debug, Deserialize)]
struct CxDepositParams {
    /// Conversation exchanges to store. Each exchange is a user/assistant pair.
    exchanges: Vec<Exchange>,

    /// Optional summary of the conversation. If provided, stored as a separate
    /// 'observation' entry linked to the individual exchange entries via
    /// 'elaborates' relations.
    #[serde(default)]
    summary: Option<String>,

    /// Target scope path. Default: "global".
    #[serde(default = "default_scope")]
    scope_path: String,

    /// Attribution. Default: "agent:claude-code".
    #[serde(default = "default_created_by")]
    created_by: String,
}

#[derive(Debug, Deserialize)]
struct Exchange {
    /// User's message.
    user: String,
    /// Assistant's response.
    assistant: String,
}
```

#### Behavior

1. Validate `scope_path`. Auto-create scope if missing.
2. For each exchange, create an entry with:
   - `kind`: `observation`
   - `title`: first 80 characters of the user message, truncated at a word boundary
   - `body`: full `user` + `\n\n---\n\n` + `assistant` content
   - `meta.tags`: `["conversation"]`
3. If `summary` is provided, create a separate entry with:
   - `kind`: `observation`
   - `title`: `"Session summary"`
   - `body`: the summary text
   - `meta.tags`: `["conversation", "summary"]`
   - Create `elaborates` relations from the summary entry to each exchange entry.
4. All entries are created in a single transaction.

#### Response Format

```json
{
  "deposited": 3,
  "entry_ids": ["019503a1-...", "019503a2-...", "019503a3-..."],
  "summary_id": "019503a4-...",
  "message": "Deposited 3 exchanges with summary."
}
```

#### Error Cases

| Condition | Error Message |
|-----------|--------------|
| Empty exchanges array | `"Validation error: exchanges cannot be empty"` |
| Exchange content too large | `"exchanges[N].user exceeds 1048576 byte limit"` |
| More than 50 exchanges | `"Validation error: maximum 50 exchanges per deposit"` |

#### Trait Methods Called

- `ContextStore::create_scope` (if needed)
- `ContextStore::create_entry` (once per exchange, once for summary)
- `ContextStore::create_relation` (summary to each exchange)

### 5.4 cx_browse

Filtered listing with cursor-based pagination. For inventory and exploration, not semantic search. Returns metadata without full body content (two-phase retrieval).

#### Parameters

```rust
#[derive(Debug, Deserialize)]
struct CxBrowseParams {
    /// Filter to entries at this exact scope path (no ancestor walk).
    /// Omit to browse across all scopes.
    #[serde(default)]
    scope_path: Option<String>,

    /// Filter by entry kind.
    /// Valid values: fact, decision, preference, lesson, reference, feedback, pattern, observation.
    #[serde(default)]
    kind: Option<String>,

    /// Filter by tag (entries must have at least one matching tag).
    #[serde(default)]
    tag: Option<String>,

    /// Filter by creator attribution string.
    #[serde(default)]
    created_by: Option<String>,

    /// Include superseded (inactive) entries. Default: false.
    #[serde(default)]
    include_superseded: bool,

    /// Maximum entries per page. Default: 20, max: 200.
    #[serde(default)]
    limit: Option<u32>,

    /// Pagination cursor from a previous cx_browse response.
    /// Pass this value to fetch the next page.
    #[serde(default)]
    cursor: Option<String>,
}
```

#### Cursor Encoding

The `PaginationCursor` (composite of `updated_at` + `id`) is serialized to a URL-safe base64 JSON string for the MCP interface. The agent treats it as an opaque string.

```rust
fn encode_cursor(cursor: &PaginationCursor) -> String {
    use base64::{Engine, engine::general_purpose::URL_SAFE_NO_PAD};
    let json = serde_json::to_string(cursor).unwrap();
    URL_SAFE_NO_PAD.encode(json.as_bytes())
}

fn decode_cursor(encoded: &str) -> Result<PaginationCursor, String> {
    use base64::{Engine, engine::general_purpose::URL_SAFE_NO_PAD};
    let bytes = URL_SAFE_NO_PAD.decode(encoded)
        .map_err(|_| "Invalid cursor format".to_string())?;
    serde_json::from_slice(&bytes)
        .map_err(|_| "Invalid cursor format".to_string())
}
```

#### Response Format

```json
{
  "entries": [
    {
      "id": "019503a1-...",
      "scope_path": "global/project:helioy",
      "kind": "decision",
      "title": "Use sqlx over diesel",
      "snippet": "First 200 chars of body...",
      "tags": ["architecture"],
      "created_by": "agent:claude-code",
      "created_at": "2026-03-14T00:10:00.000Z",
      "updated_at": "2026-03-14T00:15:00.000Z",
      "superseded_by": null
    }
  ],
  "total": 42,
  "next_cursor": "eyJ1cGRhdGVkX2F0Ij...",
  "has_more": true
}
```

#### Trait Methods Called

- `ContextStore::browse(filter)` with `EntryFilter` constructed from parameters.

#### Error Cases

| Condition | Error Message |
|-----------|--------------|
| Invalid scope_path | `"Invalid scope_path: ..."` |
| Invalid kind | `"Invalid kind 'xxx'. Valid values: ..."` |
| Invalid cursor | `"Invalid cursor format"` |

### 5.5 cx_get

Fetch full content for specific entry IDs. Phase 2 of two-phase retrieval. Also used after `cx_browse` or `cx_recall` to load full body content.

#### Parameters

```rust
#[derive(Debug, Deserialize)]
struct CxGetParams {
    /// Entry IDs to retrieve. Maximum 100 per request.
    /// IDs that do not exist are silently omitted from results.
    ids: Vec<String>,
}
```

#### Response Format

Returns full entries including body content, ordered to match the input ID order.

```json
{
  "entries": [
    {
      "id": "019503a1-...",
      "scope_path": "global/project:helioy",
      "kind": "decision",
      "title": "Use sqlx over diesel",
      "body": "Full markdown content...",
      "content_hash": "a1b2c3d4...",
      "meta": {
        "tags": ["architecture"],
        "confidence": "high",
        "source": "https://github.com/..."
      },
      "created_by": "agent:claude-code",
      "created_at": "2026-03-14T00:10:00.000Z",
      "updated_at": "2026-03-14T00:15:00.000Z",
      "superseded_by": null
    }
  ],
  "found": 1,
  "missing": 0
}
```

#### Trait Methods Called

- `ContextStore::get_entries(ids)`

#### Error Cases

| Condition | Error Message |
|-----------|--------------|
| Empty ids array | `"Validation error: ids cannot be empty"` |
| Too many IDs | `"Validation error: maximum 100 IDs per request"` |
| Invalid UUID format | `"Invalid UUID format: 'xxx'"` |

### 5.6 cx_update

Partially update an existing entry. Only provided fields are modified.

#### Parameters

```rust
#[derive(Debug, Deserialize)]
struct CxUpdateParams {
    /// ID of the entry to update.
    id: String,

    /// New title. Omit to keep existing.
    #[serde(default)]
    title: Option<String>,

    /// New body content. Omit to keep existing.
    /// Changing body recomputes content_hash and checks for duplicates.
    #[serde(default)]
    body: Option<String>,

    /// New kind classification. Omit to keep existing.
    /// Valid values: fact, decision, preference, lesson, reference, feedback, pattern, observation.
    #[serde(default)]
    kind: Option<String>,

    /// Replace metadata entirely. Omit to keep existing.
    /// To update tags while keeping other meta fields, provide the complete
    /// desired meta object.
    #[serde(default)]
    meta: Option<CxMetaInput>,
}

#[derive(Debug, Deserialize)]
struct CxMetaInput {
    #[serde(default)]
    tags: Vec<String>,
    #[serde(default)]
    confidence: Option<String>,
    #[serde(default)]
    source: Option<String>,
    #[serde(default)]
    expires_at: Option<String>,
    #[serde(default)]
    priority: Option<i32>,
}
```

#### Behavior

Scope migration (changing `scope_path`) is intentionally excluded. Moving an entry to a different scope changes its content hash and violates the dedup model. Use `cx_store` with `supersedes` to create a replacement at the target scope.

The `superseded_by` field is not directly settable via `cx_update`. Supersession is managed through `cx_store(supersedes: ...)` and `cx_forget`.

#### Response Format

```json
{
  "entry": {
    "id": "019503a1-...",
    "scope_path": "global/project:helioy",
    "kind": "decision",
    "title": "Updated title",
    "content_hash": "new-hash-if-body-changed...",
    "updated_at": "2026-03-14T00:20:00.000Z"
  },
  "message": "Entry updated."
}
```

#### Trait Methods Called

- `ContextStore::update_entry(id, update)`

#### Error Cases

| Condition | Error Message |
|-----------|--------------|
| Entry not found | `"Entry '<id>' not found. ..."` |
| Invalid UUID | `"Invalid UUID format: 'xxx'"` |
| Duplicate content after update | `"Duplicate content: ..."` |
| Invalid kind | `"Invalid kind 'xxx'. Valid values: ..."` |
| No fields to update | `"Validation error: at least one field must be provided"` |

### 5.7 cx_forget

Soft-delete entries. Marks entries as forgotten by setting `superseded_by` to their own ID.

#### Parameters

```rust
#[derive(Debug, Deserialize)]
struct CxForgetParams {
    /// Entry IDs to forget. Maximum 100 per request.
    ids: Vec<String>,
}
```

#### Behavior

Each ID is processed independently. If an entry is already forgotten (superseded_by is set), it is silently skipped. Partial success is reported: some entries may be forgotten while others fail.

#### Response Format

```json
{
  "forgotten": 2,
  "already_inactive": 1,
  "not_found": 0,
  "details": [
    {"id": "019503a1-...", "status": "forgotten"},
    {"id": "019503a2-...", "status": "forgotten"},
    {"id": "019503a3-...", "status": "already_inactive"}
  ],
  "message": "Forgot 2 entries. 1 already inactive."
}
```

#### Trait Methods Called

- `ContextStore::get_entry(id)` (to check current state)
- `ContextStore::forget_entry(id)` (for each active entry)

#### Error Cases

| Condition | Error Message |
|-----------|--------------|
| Empty ids array | `"Validation error: ids cannot be empty"` |
| Too many IDs | `"Validation error: maximum 100 IDs per request"` |
| Invalid UUID format | `"Invalid UUID format: 'xxx'"` |

### 5.8 cx_stats

Aggregate statistics about the context store. Diagnostic tool for understanding what context exists.

#### Parameters

```rust
#[derive(Debug, Deserialize)]
struct CxStatsParams {}
```

No parameters. Stats are a global diagnostic view. Per-scope entry counts are included in the `entries_by_scope` breakdown and `scope_tree` fields.

#### Response Format

```json
{
  "active_entries": 156,
  "superseded_entries": 23,
  "scopes": 8,
  "relations": 12,
  "entries_by_kind": {
    "fact": 42,
    "decision": 28,
    "preference": 15,
    "lesson": 18,
    "reference": 22,
    "feedback": 8,
    "pattern": 12,
    "observation": 11
  },
  "entries_by_scope": {
    "global": 30,
    "global/project:helioy": 65,
    "global/project:helioy/repo:nancyr": 38,
    "global/project:helioy/repo:fmm": 23
  },
  "db_size_bytes": 524288,
  "scope_tree": [
    {"path": "global", "kind": "global", "label": "Global", "entry_count": 30},
    {"path": "global/project:helioy", "kind": "project", "label": "Helioy", "entry_count": 65}
  ]
}
```

#### Trait Methods Called

- `ContextStore::stats()`
- `ContextStore::list_scopes(None)` (for the scope_tree)

#### Error Cases

None. This tool always succeeds.

### 5.9 cx_export

Export entries as JSON for backup or migration.

#### Parameters

```rust
#[derive(Debug, Deserialize)]
struct CxExportParams {
    /// Filter export to a specific scope path and its descendants.
    /// Omit to export everything.
    #[serde(default)]
    scope_path: Option<String>,

    /// Export format. Currently only "json" is supported.
    /// Default: "json".
    #[serde(default = "default_format")]
    format: String,
}

fn default_format() -> String { "json".to_string() }
```

#### Response Format

```json
{
  "entries": [ /* full Entry objects */ ],
  "scopes": [ /* full Scope objects */ ],
  "exported_at": "2026-03-14T00:30:00.000Z",
  "count": 156
}
```

Relations are excluded from export in v1. The trait provides per-entry relation lookups (`get_relations_from`, `get_relations_to`) but no bulk export method. A `list_relations` method and corresponding export support can be added in v2.

#### Trait Methods Called

- `ContextStore::export(scope_path)`
- `ContextStore::list_scopes(None)` (filtered by scope_path prefix if specified)

#### Error Cases

| Condition | Error Message |
|-----------|--------------|
| Invalid scope_path | `"Invalid scope_path: ..."` |
| Unsupported format | `"Unsupported export format 'xxx'. Currently only 'json' is supported."` |

## 6. Tool Dispatch

Tool dispatch uses a match statement in `handle_tool_call` (Section 2.1). Each tool handler is a standalone async function in `src/mcp/tools/`:

```rust
// src/mcp/tools/mod.rs
pub mod recall;
pub mod store;
pub mod deposit;
pub mod browse;
pub mod get;
pub mod update;
pub mod forget;
pub mod stats;
pub mod export;

pub use recall::cx_recall;
pub use store::cx_store;
pub use deposit::cx_deposit;
pub use browse::cx_browse;
pub use get::cx_get;
pub use update::cx_update;
pub use forget::cx_forget;
pub use stats::cx_stats;
pub use export::cx_export;
```

Each tool handler has the signature:

```rust
pub async fn cx_recall(store: &CmStore, arguments: &Value) -> Result<String, String>
```

Tool descriptions are NOT in the Rust source. They live in `tools.toml` and are compiled into `generated_schema.rs` by `build.rs`. The `tools/list` response loads this generated schema:

```rust
// src/mcp/schema.rs
#[path = "generated_schema.rs"]
mod generated_schema;

pub(super) fn tool_list() -> serde_json::Value {
    generated_schema::generated_tool_list()
}
```

## 7. Response Construction Pattern

All tool handlers return `Result<String, String>`. The `String` on success is the JSON-serialized response body. The McpServer wraps it in the MCP content envelope (Section 2.1).

```rust
/// Serialize a JSON value to a pretty-printed string for the response.
fn json_response(value: serde_json::Value) -> Result<String, String> {
    Ok(serde_json::to_string_pretty(&value).unwrap())
}
```

### 7.1 Snippet Generation

For two-phase retrieval responses (`cx_recall`, `cx_browse`), the body is truncated to a snippet:

```rust
/// Truncate body to a snippet, safe for multi-byte UTF-8.
///
/// Uses `floor_char_boundary` (stable since Rust 1.82) to avoid
/// panicking on multi-byte character boundaries.
fn snippet(body: &str, max_chars: usize) -> String {
    if body.len() <= max_chars {
        return body.to_string();
    }
    let end = body.floor_char_boundary(max_chars);
    match body[..end].rfind(' ') {
        Some(pos) => format!("{}...", &body[..pos]),
        None => format!("{}...", &body[..end]),
    }
}

const SNIPPET_LENGTH: usize = 200;
```

### 7.2 Token Estimation

For `max_tokens` budget support in `cx_recall`:

```rust
/// Rough token estimate: ~4 characters per token for English text.
fn estimate_tokens(text: &str) -> u32 {
    (text.len() as u32 + 3) / 4
}
```

When `max_tokens` is set, results are accumulated until the budget is exhausted, prioritizing entries with higher relevance scores.

## 8. Scope Auto-Creation

When `cx_store` or `cx_deposit` receives a scope path that does not exist, the server creates the full scope chain automatically. This prevents agents from needing to manage scope creation as a separate step.

```rust
/// Ensure the full scope chain exists, creating missing scopes top-down.
async fn ensure_scope_chain(store: &CmStore, path: &ScopePath) -> Result<(), String> {
    let ancestors: Vec<&str> = path.ancestors().collect();

    // Walk from root (last) to leaf (first)
    for ancestor_str in ancestors.into_iter().rev() {
        let ancestor = ScopePath::parse(ancestor_str).map_err(|e| cm_err_to_string(e.into()))?;
        match store.get_scope(&ancestor).await {
            Ok(_) => continue, // Already exists
            Err(CmError::ScopeNotFound(_)) => {
                // Derive label from the last segment
                let label = ancestor_str
                    .rsplit('/')
                    .next()
                    .and_then(|s| s.split(':').nth(1))
                    .unwrap_or(ancestor_str)
                    .to_string();

                let new_scope = NewScope {
                    path: ancestor,
                    label,
                    meta: None,
                };
                store.create_scope(new_scope).await.map_err(cm_err_to_string)?;
            }
            Err(e) => return Err(cm_err_to_string(e)),
        }
    }
    Ok(())
}
```

### 8.1 Orphan Scope Behavior

Scope auto-creation and entry creation are separate operations, not wrapped in a single transaction. If scope creation succeeds but entry creation fails (e.g., duplicate content), the newly created scopes remain in the database. This is harmless: empty scopes are valid containers and will be used by subsequent stores. This is a known behavior, not a bug.

## 9. Acceptance Criteria

### 9.1 Server Lifecycle

1. `McpServer::new(store)` constructs successfully with an in-memory `CmStore`.
2. The `initialize` response includes non-empty `serverInfo.instructions` and `capabilities.tools`.
3. The `tools/list` response exposes exactly 9 tools: `cx_recall`, `cx_store`, `cx_deposit`, `cx_browse`, `cx_get`, `cx_update`, `cx_forget`, `cx_stats`, `cx_export`.

### 9.2 cx_recall

4. `cx_recall(query: "sqlx")` returns entries matching the FTS5 query.
5. `cx_recall(scope: "global/project:helioy/repo:nancyr")` with no query returns entries from the repo scope, the project scope, and the global scope.
6. `cx_recall(query: "sqlx", kinds: ["decision"])` returns only decision entries matching the query.
7. `cx_recall(query: "sqlx", max_tokens: 500)` returns results trimmed to fit within 500 tokens.
8. `cx_recall()` with no parameters returns entries from the global scope.
9. Results include `snippet` (truncated body) but not `body` (two-phase retrieval).

### 9.3 cx_store

10. `cx_store(title: "T", body: "B", kind: "fact")` creates an entry and returns its ID.
11. `cx_store(... scope_path: "global/project:new-project")` auto-creates the scope chain.
12. `cx_store(... supersedes: "<old-id>")` soft-deletes the old entry and creates a new one.
13. Storing the same content twice returns a `DuplicateContent` error with the existing entry's ID.
14. `cx_store(kind: "invalid")` returns an error listing valid kind values.
15. `cx_store(title: "", ...)` returns a validation error.

### 9.4 cx_deposit

16. `cx_deposit(exchanges: [{user: "U", assistant: "A"}])` creates one observation entry.
17. `cx_deposit(exchanges: [...], summary: "S")` creates exchange entries plus a summary entry linked via `elaborates` relations.
18. Depositing an empty exchanges array returns a validation error.

### 9.5 cx_browse

19. `cx_browse()` with no filters returns the first page of active entries.
20. `cx_browse(kind: "decision")` returns only decision entries.
21. `cx_browse(include_superseded: true)` includes forgotten and superseded entries.
22. Passing `next_cursor` from a previous response returns the next page with no duplicates.
23. When no more results exist, `next_cursor` is null and `has_more` is false.

### 9.6 cx_get

24. `cx_get(ids: ["<valid-id>"])` returns the full entry including `body`.
25. `cx_get(ids: ["<valid-id>", "<invalid-id>"])` returns only the valid entry with `found: 1, missing: 1`.
26. `cx_get(ids: [])` returns a validation error.
27. `cx_get` with more than 100 IDs returns a validation error.

### 9.7 cx_update

28. `cx_update(id: "<id>", title: "New title")` updates only the title, preserving body and kind.
29. `cx_update(id: "<id>", body: "New body")` recomputes `content_hash`.
30. `cx_update(id: "<id>")` with no update fields returns a validation error.
31. `cx_update(id: "<nonexistent>", ...)` returns an EntryNotFound error.

### 9.8 cx_forget

32. `cx_forget(ids: ["<id>"])` sets `superseded_by` to the entry's own ID.
33. After forgetting, `cx_browse()` no longer returns the entry (unless `include_superseded: true`).
34. Forgetting an already-forgotten entry reports `already_inactive` status.

### 9.9 cx_stats

35. `cx_stats()` with no parameters returns counts matching the actual database state.
36. `entries_by_kind` sums equal `active_entries`.

### 9.10 cx_export

37. `cx_export()` returns all active entries and scopes as JSON (no relations in v1).
38. `cx_export(scope_path: "global/project:helioy")` returns only entries and scopes within that scope subtree.
39. `cx_export(format: "csv")` returns an unsupported format error.

### 9.11 Error Messages

40. Every error response includes guidance on how to resolve the issue (valid values, alternative tools, or next steps).
41. Invalid enum values list all valid options in the error message.

### 9.12 Scope Auto-Creation

42. Storing an entry at `global/project:new/repo:new-repo` auto-creates `global`, `global/project:new`, and `global/project:new/repo:new-repo` scopes.
43. Auto-created scopes have their label derived from the identifier segment.

### 9.13 Input Validation

44. Any text field exceeding 1 MB is rejected with a byte limit error.
45. Batch operations (cx_get, cx_forget) exceeding 100 IDs are rejected.
