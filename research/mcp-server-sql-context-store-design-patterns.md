---
title: MCP Server Design Patterns for SQL-Backed Context/Memory Stores
type: research
tags: [mcp, rust, sql, context-store, tool-design, agent-memory, helioy]
summary: Comprehensive analysis of tool interface design, query/write patterns, naming conventions, and Rust implementation patterns for building a SQL-backed MCP context store server.
status: active
source: deep-research
confidence: high
created: 2026-03-14
updated: 2026-03-14
---

## Executive Summary

Building a high-quality MCP server for a SQL-backed context store requires designing tools for agent ergonomics rather than API fidelity. The research converges on a clear consensus: 5-8 tools per server, outcome-oriented rather than CRUD-atomic, with flat parameter schemas, service-prefixed snake_case naming, and actionable error messages. For a context store specifically, the critical design decision is whether to expose raw SQL, structured query parameters, or semantic/natural-language queries. The evidence strongly favors structured parameters with optional semantic search, avoiding raw SQL exposure entirely. Microsoft's SQL MCP Server team explicitly rejects NL2SQL as nondeterministic and unreliable for production use.

## Detailed Findings

### 1. Tool Granularity: The "5-8 Tools" Consensus

Multiple authoritative sources converge on the same guidance:

**Philschmid (Hugging Face)**: "Maintain 5-8 tools per server. Each tool description, response payload, and error competes for context window space." Design tools around what the agent wants to achieve, not around API endpoints.

**Datadog engineering blog**: "Instead of three atomic tools, give the agent one high-level tool that does the orchestration in your code, not in the LLM's context window."

**Arcade (54 Patterns)**: Start atomic, observe agent behavior in traces, then consolidate when you see repeated tool sequences. Three maturity levels: Atomic (single operation), Composite (bundled workflow), Orchestrated (multi-step coordination).

**MCP official tutorial**: "Instead of implementing `list_users`, `list_events`, and `create_event` tools separately, consider implementing a `schedule_event` tool which finds availability and schedules an event."

The helioy ecosystem already follows this. `am_query` combines recall across conscious, subconscious, and novel connections in one call. `fmm_search` unifies export lookup, path search, import search, and named-import call-site search into one tool with structured filters.

### 2. Naming Conventions

**Established consensus** (SEP-986, Philschmid, Workato, MetaMCP):
- Snake_case universally. GPT-4o tokenization handles it best; over 90% of MCP tools use it.
- Service prefix for namespace isolation: `slack_send_message`, `linear_list_issues`.
- Action-oriented verbs: `search_`, `create_`, `get_`, `list_`, `delete_`, `update_`.
- Never use dots, spaces, or brackets in tool names.

**Helioy convention** uses a different pattern: `{service}_{verb}` with short, memorable verbs.
- `am_query`, `am_ingest`, `am_buffer`, `am_salient`, `am_feedback`, `am_export`
- `fmm_list_files`, `fmm_file_outline`, `fmm_read_symbol`, `fmm_search`, `fmm_glossary`
- `md_search`, `md_context`, `md_index`, `md_keyword_search`

The helioy pattern is tighter than the industry norm. Two-letter prefix + underscore + action. This works well in Claude Code where all tools from the same plugin share a namespace prefix (`mcp__plugin_helioy-tools_{service}__`), so the tool name itself stays compact.

### 3. Query Interface Design: Three Approaches Compared

**Approach A: Raw SQL exposure**
- Used by: mcp-server-sqlite (archived reference), many community SQLite servers
- Pattern: `sqlite_execute(sql: string)` with `sqlite_get_catalog()` for schema discovery
- Pros: Maximum flexibility, agents can write arbitrary queries
- Cons: Security risk (injection), nondeterministic SQL generation, schema drift, agents write incorrect SQL for complex joins
- **Microsoft explicitly rejects this**: "SQL MCP Server intentionally doesn't support NL2SQL. Models aren't deterministic, and complex queries are the most likely to produce subtle errors."

**Approach B: Structured parameter queries**
- Used by: Microsoft SQL MCP Server (DAB), Supabase MCP, Redis Agent Memory Server
- Pattern: `read_records(entity: str, filter: {...}, limit: int, order_by: str)`
- Pros: Deterministic, safe, type-checked, cacheable
- Cons: Limited expressiveness for ad-hoc analysis
- Microsoft's `describe_entities` + `read_records` + `create_record` + `update_record` + `delete_record` + `execute_entity` is the canonical example. Six tools, deterministic SQL generation behind the abstraction.

**Approach C: Semantic/hybrid search**
- Used by: Hindsight, Redis Agent Memory, attention-matters (`am_query`)
- Pattern: `recall(query: str, filters: {...})` with multi-strategy retrieval (semantic + keyword + entity graph + temporal)
- Pros: Natural for agents, handles fuzzy recall, reduces parameter complexity
- Cons: Requires embedding infrastructure, results are probabilistic

**Recommendation for the context store**: Hybrid of B and C. Structured parameters for writes and precise lookups. Semantic search for open-ended recall. The attention-matters pattern (`am_query` accepts text, returns structured recall) is already proven in the ecosystem.

### 4. Write Patterns

**Structured inserts with required fields** (consensus approach):
- Supabase: `mutate(action: "insert", table: str, data: {...})`
- Knowledge Graph Memory: `create_entities([{name, entityType, observations}])`
- Redis Agent Memory: `create_long_term_memories(data: [{type, content, metadata}])`

**Free-form with auto-extraction** (emerging pattern):
- Hindsight's `retain`: accepts raw text, runs background extraction for structured facts, entity resolution, and embedding generation. Writes are async.
- `am_buffer`: accepts user/assistant text pairs, auto-chunks into neighborhoods after 3 exchanges.
- `am_salient`: accepts free text, stores as conscious memory with optional supersession of prior memories.

**Batch operations**:
- Knowledge Graph Memory: All write tools accept arrays (`create_entities([...])`, `create_relations([...])`)
- `am_batch_query`: processes multiple queries with amortized IDF computation
- Datadog: recommends token-budget pagination over record-count pagination

**Recommendation**: Support both structured and free-form writes. Structured for programmatic deposits (agent storing specific facts with metadata). Free-form for conversational context capture (agent summarizing what happened). Batch support for multi-agent scenarios.

### 5. Context Retrieval at Session Start

**The "recall at session start" pattern** is universal across memory MCP servers:
- `am_query` description: "Call this at the START of every session with the user's first message to recall relevant context."
- Redis Agent Memory: `memory_prompt` tool "essential for retrieving relevant context before answering questions."
- Knowledge Graph Memory: "Begin your chat by saying 'Remembering...' and retrieving all relevant information."

**Two-phase retrieval** (proven in helioy):
- Phase 1: `am_query_index` returns compact index (IDs, scores, summaries, token estimates)
- Phase 2: `am_retrieve` fetches full content for selected IDs
- This reduces context pollution and lets the agent be selective about what it loads.

**Multi-strategy retrieval** (Hindsight, recommended for production):
- Semantic search via embeddings
- BM25 keyword matching for exact terminology
- Entity graph traversal
- Temporal filtering with recency boost
- Cross-encoder reranking

### 6. Response Format and Token Efficiency

**Datadog engineering blog** (high signal):
- CSV/TSV uses ~50% fewer tokens than JSON for tabular data
- YAML uses ~20% fewer tokens than JSON for nested data
- Field trimming: remove rarely-used fields from default output; let agents request them
- Token-budget pagination: cut responses at a token threshold, return cursor for continuation

**Helioy pattern**: `am_query` accepts `max_tokens` parameter for budget-aware composition. `md_context` offers compression levels (`full`, `summary`, `brief`). These are proven patterns worth replicating.

### 7. Error Handling

**Strong consensus** across all sources:
- Errors must be actionable, not generic
- Good: `"unknown field 'stauts' -- did you mean 'status'?"` (Datadog, Arcade, Philschmid)
- Good: `"User not found. Please try searching by email address instead."` (Philschmid)
- Bad: `"invalid query"`, `"internal error"`
- Agents recover surprisingly well from errors given specific guidance
- Include suggestions for correct input formats, fuzzy-matched field names, valid enum values

### 8. Security Patterns

**Microsoft SQL MCP Server** sets the bar:
- Entity abstraction layer prevents internal schema exposure
- RBAC at every tool invocation
- Read-only mode as a configuration option
- No DDL (data definition language) support; DML only
- Deterministic query generation (no NL2SQL)

**Supabase MCP**:
- Three safety tiers: safe (always allowed), write (requires write mode), destructive (requires 2-step confirmation)
- Automatic migration script generation for write operations

**Arcade patterns**:
- Context injection: user identity and permissions passed server-side, never through the LLM
- Idempotent operations for graceful agent retry handling

### 9. Existing Reference Implementations

| Server | Language | Storage | Tool Count | Key Pattern |
|--------|----------|---------|------------|-------------|
| Knowledge Graph Memory (Anthropic) | TypeScript | JSON file | 9 | Entity/Relation/Observation model |
| memory-mcp-rs | Rust | SQLite + FTS5 | 9 | Rust port of above, indexed queries |
| Redis Agent Memory | Python | Redis | 7 | Working memory + long-term with semantic search |
| Hindsight | Python | PostgreSQL + pgvector | 3 | retain/recall/reflect with multi-strategy retrieval |
| Microsoft SQL MCP Server | C# | SQL Server/PostgreSQL | 6 | RBAC + entity abstraction, no NL2SQL |
| Supabase MCP | TypeScript | PostgreSQL | 4 | Safety tiers, migration generation |
| attention-matters (helioy) | Rust | Custom manifold | 11 | Geometric memory, two-phase retrieval |

### 10. Rust Implementation Patterns (rmcp SDK)

**Server struct**: `#[derive(Clone)]` with state fields. Database connection pool as `Arc<Pool<Sqlite>>` or similar.

**Tool definition**: `#[tool(description = "...")]` macro on async methods. Parameters via `#[derive(Deserialize, schemars::JsonSchema)]` structs with `#[schemars(description = "...")]` on each field.

**Handler**: `#[tool_handler]` macro implements `ServerHandler` trait. `get_info()` returns capabilities and instructions.

**Transport**: `server.serve(stdio()).await` for Claude Code integration. Streamable HTTP also supported.

**Error pattern**: `McpError::internal_error(format!("..."), None)` with descriptive messages.

**Dependencies**: `rmcp` (with `server`, `transport-io`, `macros` features), `tokio`, `serde`, `schemars`, `anyhow`.

## Concrete Tool Interface Proposal

Based on helioy naming conventions, the research findings, and the `cx_` prefix (for "context"):

### Core Tools (7 tools)

```
cx_recall(query: str, max_tokens?: uint, scope?: str, tags?: [str])
```
Primary retrieval tool. Semantic + keyword hybrid search. Called at session start with the user's first message. Returns ranked context fragments with relevance scores. `scope` filters by project/agent/global. `tags` for categorical filtering.

```
cx_store(content: str, kind: "fact" | "decision" | "preference" | "pattern" | "reference", tags?: [str], scope?: str, supersedes?: [str])
```
Store a context entry. Structured insert with required `kind` classification. `supersedes` array for replacing outdated entries (mirrors `am_salient`'s pattern). Auto-extracts entities and generates embeddings in background.

```
cx_deposit(exchanges: [{role: str, content: str}], summary?: str)
```
Batch deposit of conversation exchanges. Like `am_buffer` but accepts arbitrary exchange counts. Optional agent-provided summary. Auto-chunks and indexes.

```
cx_browse(kind?: str, scope?: str, tags?: [str], since?: str, limit?: uint, offset?: uint)
```
Structured browsing with filters. Returns paginated list of entries with metadata (id, kind, tags, created, summary snippet). For when the agent needs to inventory what context exists rather than search by meaning.

```
cx_get(ids: [str])
```
Fetch full content for specific entry IDs. Phase 2 of two-phase retrieval (mirrors `am_retrieve`). Also used after `cx_browse` to load specific entries.

```
cx_update(id: str, content?: str, tags?: [str], kind?: str)
```
Partial update of an existing entry. For correcting or enriching existing context.

```
cx_forget(ids: [str])
```
Soft-delete entries. Marks as forgotten rather than hard-deleting, preserving audit trail.

### Optional Diagnostic Tools (2 tools)

```
cx_stats(scope?: str)
```
Memory system statistics. Entry count by kind, tag distribution, storage size. For diagnostics only.

```
cx_export(scope?: str, format?: "json" | "csv")
```
Export context entries for backup or migration.

### Why This Surface

**7 core tools** fits the 5-8 consensus. The split between `cx_recall` (semantic) and `cx_browse` (structured) gives agents two distinct retrieval modes. `cx_store` (single structured entry) and `cx_deposit` (batch conversation capture) serve the two primary write use cases. `cx_get` enables two-phase retrieval without forcing full content in list/search results. `cx_update` and `cx_forget` round out the lifecycle.

**No raw SQL**. The structured parameters are deterministic and safe. The server translates them to SQL internally.

**Scope isolation** enables multi-project and multi-agent use without separate databases.

**Tag-based taxonomy** is more flexible than rigid entity-type hierarchies and lets conventions emerge organically.

## Sources Consulted

### Engineering Blog Posts (High Signal)
- [Datadog: Designing MCP tools for agents](https://www.datadoghq.com/blog/engineering/mcp-server-agent-tools/) - Detailed guidance on tool granularity, output format optimization, token-budget pagination
- [Philschmid: MCP is Not the Problem, It's your Server](https://www.philschmid.de/mcp-best-practices) - Six core principles including "Outcomes Over Operations"
- [MCP Official: Writing Effective Tools](https://modelcontextprotocol.info/docs/tutorials/writing-effective-tools/) - Consolidation over 1:1 mapping, response format flexibility
- [Workato: MCP server tool design](https://docs.workato.com/mcp/mcp-server-tool-design.html) - Naming clarity, description components, parameter constraints
- [Arcade: 54 Patterns for Building Better MCP Tools](https://arcade.dev/blog/mcp-tool-patterns) - Maturity progression, context injection, idempotent operations

### Reference Implementations
- [Microsoft SQL MCP Server](https://learn.microsoft.com/en-us/azure/data-api-builder/mcp/overview) - Entity abstraction, RBAC, deterministic query generation, explicit rejection of NL2SQL
- [Anthropic Knowledge Graph Memory Server](https://glama.ai/mcp/servers/@modelcontextprotocol/knowledge-graph-memory-server) - 9-tool interface for entity/relation/observation management
- [Redis Agent Memory Server](https://redis.github.io/agent-memory-server/mcp/) - 7-tool interface with working memory + long-term, semantic search
- [Hindsight MCP Memory](https://hindsight.vectorize.io/blog/2026/03/04/mcp-agent-memory) - retain/recall/reflect with multi-strategy retrieval and cross-encoder reranking
- [memory-mcp-rs](https://crates.io/crates/memory-mcp-rs) - Rust port of Knowledge Graph Memory with SQLite + FTS5
- [mcp-memory-libsql](https://github.com/joleyline/mcp-memory-libsql) - Rust, libSQL vector search
- [Supabase MCP](https://supabase.com/docs/guides/getting-started/mcp) - 4 tools, safety tiers, migration generation

### Rust MCP SDK
- [rmcp official SDK](https://github.com/modelcontextprotocol/rust-sdk) - v0.12.0, macro-based tool definition
- [MCPcat: Build MCP Servers in Rust](https://mcpcat.io/guides/building-mcp-server-rust/) - Complete code patterns with state management
- [Shuttle: How to Build a stdio MCP Server in Rust](https://www.shuttle.dev/blog/2025/07/18/how-to-build-a-stdio-mcp-server-in-rust)
- [rup12.net: Building MCP Servers in Rust with rmcp](https://rup12.net/posts/write-your-mcps-in-rust/)

### Naming and Standards
- [MCP Server Naming Conventions](https://zazencodes.com/blog/mcp-server-naming-conventions) - Snake_case consensus, 90%+ adoption
- [SEP-986: Specify Format for Tool Names](https://github.com/modelcontextprotocol/modelcontextprotocol/issues/986) - Standardization proposal
- [MetaMCP Namespaces](https://docs.metamcp.com/en/concepts/namespaces) - Prefix collision avoidance

### HackerNews Discussions
- [An in-depth guide to MCP tool design](https://news.ycombinator.com/item?id=44299718)
- [Show HN: Open-Source MCP Server for Context and AI Tools](https://news.ycombinator.com/item?id=43368327)

## Source Quality Assessment

**High confidence**: Tool granularity consensus (5-8 tools), naming conventions (snake_case), structured parameters over raw SQL, actionable error messages. These findings are triangulated across 5+ independent authoritative sources.

**Medium confidence**: The specific tool interface proposal. While grounded in proven patterns from both the broader ecosystem and helioy's own conventions, real-world agent usage will surface adjustments. The Arcade patterns guide wisely advises "start atomic, watch how agents actually use your tools."

**Low confidence**: Optimal retrieval strategy (pure semantic vs hybrid). The Hindsight multi-strategy approach is theoretically superior but adds complexity. Whether the context store needs BM25 + vector + entity graph or just FTS5 + vector depends on data volume and query patterns that can only be determined empirically.

## Open Questions

1. **FTS5 vs pgvector vs both?** SQLite with FTS5 is simpler and proven in memory-mcp-rs. pgvector enables true semantic search but requires embedding generation. The helioy ecosystem already uses embeddings in attention-matters. Should the context store share that embedding infrastructure or be self-contained?

2. **Scope model**: Should scope be project-level (directory-based like helioy plugins), agent-level (per-agent instance), user-level, or hierarchical? The `am_query` system is brain-wide; the context store might need finer isolation.

3. **Consistency with am_***: How much overlap is acceptable between `cx_*` and `am_*`? If attention-matters already provides recall, what does a context store add? The likely answer: structured, typed, queryable facts vs. geometric manifold neighborhoods. But the boundary needs explicit definition.

4. **Write latency**: Hindsight's async write path (extraction + entity resolution + embedding happen in background) is the right pattern for production but adds complexity. Should writes block until indexed, or return immediately and index asynchronously?

5. **Schema evolution**: How to handle adding new `kind` values or tag taxonomies over time without breaking existing entries?

## Actionable Takeaways

1. **Use the `cx_` prefix** with 7 core tools: `recall`, `store`, `deposit`, `browse`, `get`, `update`, `forget`.

2. **Build on rmcp** (v0.12.0+) with `#[tool]` macros, `schemars` for parameter schemas, and `tokio` async runtime.

3. **SQLite + FTS5 for the first iteration**. Add vector search later if needed. FTS5 handles keyword recall, and the structured `kind`/`tags` filters handle categorical queries.

4. **Two-phase retrieval** (`cx_browse`/`cx_recall` returns summaries, `cx_get` returns full content) is proven in helioy and reduces context pollution.

5. **Never expose raw SQL**. Translate structured parameters to SQL server-side.

6. **Flat parameter schemas** with `schemars` descriptions on every field. Use enums for `kind` and constrained types wherever possible.

7. **Actionable error messages** with field suggestions, valid enum values, and recovery guidance.

8. **Token budget parameter** on retrieval tools (following `am_query`'s `max_tokens` pattern).
