---
title: "CASS: Coding Agent Session Search - Full Architecture Review"
type: research
tags: [tantivy, session-search, rust, semantic-search, hybrid-search, history-matters]
summary: "Deep code review of CASS (coding_agent_session_search), a 250K-line Rust tool that indexes 19 agent platforms with Tantivy BM25 + MiniLM semantic search, featuring encrypted HTML export. Patterns and anti-patterns for history-matters."
status: active
source: github-researcher
confidence: high
created: 2026-04-24
updated: 2026-04-24
---

## Executive Summary

CASS (Coding Agent Session Search) is a 250K-line Rust CLI/TUI tool by Jeffrey Emanuel that discovers, indexes, and searches coding agent session files from 19 platforms (Claude Code, Codex CLI, Cursor, Aider, etc.). It uses Tantivy for BM25 lexical search, FastEmbed/MiniLM for 384-dim semantic embeddings, and a custom two-tier progressive search architecture. It has 709 GitHub stars (as of April 2026), is actively developed, and has extensive test coverage (98K lines of tests, 10+ benchmarks). The project uses Rust 2024 edition and deploys as a single binary.

## Architecture

### Crate Structure

Single crate with heavy delegation to a constellation of sibling `franken-*` crates:

| Module | LOC | Role |
|---|---|---|
| `src/lib.rs` | 28K | CLI parsing (clap derive), command dispatch, orchestration |
| `src/indexer/mod.rs` | 32K | Core indexing pipeline: scan, parse, normalize, store, index |
| `src/search/query.rs` | 18K | Search execution: lexical, semantic, hybrid, caching, pagination |
| `src/storage/sqlite.rs` | 19K | SQLite schema, migrations, conversation/message CRUD |
| `src/ui/app.rs` | 46K | TUI application (FrankenTUI, their custom fork of Ratatui) |
| `src/connectors/` | Stubs | Re-exports from `franken_agent_detection` crate |
| `src/search/` | ~12 files | Embedder traits, vector index, ANN, reranker, two-tier search |
| `src/html_export/` | 6 files | Self-contained HTML generation with optional AES-GCM encryption |
| `src/encryption.rs` | 630 | AES-256-GCM, Argon2id, HKDF crypto primitives |

### Data Flow

```
Session Files (19 formats)
    |
    v
Connectors (franken_agent_detection)
    | produces NormalizedConversation { messages: [NormalizedMessage] }
    v
Indexer Pipeline (rayon parallel, fs-watch incremental)
    |--- SQLite (FrankenSQLite): conversations, messages, snippets, agents, workspaces
    |--- Tantivy (frankensearch): per-message documents, BM25 index
    |--- Vector Index (FSVI): f16-quantized embeddings, HNSW ANN
    v
SearchClient
    |--- Lexical: Tantivy BM25 with edge n-gram prefix, boolean operators
    |--- Semantic: cosine similarity on MiniLM-384 embeddings
    |--- Hybrid: RRF (Reciprocal Rank Fusion) of lexical + semantic
    v
TUI or JSON/robot output
```

### Key Dependencies

- `frankensearch`: Extracted search library (Tantivy schema, lexical index, vector index, RRF fusion, embedder traits). This is the author's own crate. Contains the Tantivy schema definition, field types, tokenizer registration, and query building.
- `franken_agent_detection`: All 19 connector parsers. Each produces `NormalizedConversation`.
- `frankensqlite`: SQLite wrapper with migration runner. Their own crate wrapping libsqlite3 with a migration system.
- `fastembed`: ONNX Runtime wrapper for MiniLM embedding inference.
- `hnsw_rs`: HNSW approximate nearest neighbor index.
- `asupersync`: Async runtime (their own fork/wrapper).
- `ftui` / `ftui-runtime` / `ftui-extras`: TUI framework (their fork of Ratatui).

## Session Parsing (Connectors)

### Abstraction Layer

All connector logic has been extracted to `franken_agent_detection`. CASS's `src/connectors/` directory contains only one-line re-export stubs:

```rust
// src/connectors/claude_code.rs
pub use franken_agent_detection::connectors::claude_code::ClaudeCodeConnector;
```

The core trait is `Connector`, which produces `NormalizedConversation`:

```rust
pub struct NormalizedConversation {
    pub agent_slug: String,
    pub external_id: Option<String>,
    pub title: Option<String>,
    pub workspace: Option<PathBuf>,
    pub source_path: PathBuf,
    pub started_at: Option<i64>,
    pub ended_at: Option<i64>,
    pub metadata: serde_json::Value,
    pub messages: Vec<NormalizedMessage>,
}

pub struct NormalizedMessage {
    pub idx: i64,
    pub role: String,      // "user", "assistant", "tool", "system"
    pub author: Option<String>,
    pub created_at: Option<i64>,
    pub content: String,
    pub extra: serde_json::Value,
    pub snippets: Vec<NormalizedSnippet>,
    pub invocations: Vec<...>,
}
```

### Supported Platforms (19)

Aider, AMP, ChatGPT, Claude Code, Clawdbot, Cline, Codex CLI, Copilot, Copilot CLI, Crush, Cursor, Factory, Gemini, Kimi, OpenClaw, OpenCode, Pi Agent, Qwen, Vibe.

### ChatGPT Encrypted Conversations

CASS can decrypt ChatGPT's locally encrypted conversation exports using macOS Keychain access (`security-framework` crate) to retrieve the encryption key, then AES-GCM decryption.

## Tantivy Usage (Critical for history-matters)

### Schema Design

The schema is defined in `frankensearch::lexical` (not visible in CASS source). From the CASS wrapper (`src/search/tantivy.rs`), the document model is:

```rust
pub struct CassDocument {
    pub agent: String,
    pub workspace: Option<String>,
    pub workspace_original: Option<String>,
    pub source_path: String,
    pub msg_idx: u64,
    pub created_at: Option<i64>,
    pub title: Option<String>,
    pub content: String,          // The indexed text
    pub conversation_id: Option<i64>,
    pub source_id: String,        // Provenance: "local", "work-laptop", etc.
    pub origin_kind: String,      // "local" or "remote"
    pub origin_host: Option<String>,
}
```

**Key design decision**: Each Tantivy document is a single message, not a conversation. This gives fine-grained search at the message level.

### Schema Versioning

- Schema hash constant `CASS_SCHEMA_HASH` tracked across versions.
- Versioned index directory: `data_dir/index/v7/`.
- `schema_hash.json` written alongside index for compatibility checking.
- On schema mismatch: full rebuild triggered.

### Indexing Strategy

1. **Batch ingestion with backpressure**: Messages are accumulated into batches bounded by both count (`CASS_TANTIVY_ADD_BATCH_MAX_MESSAGES`, default 4096) and character budget (`CASS_TANTIVY_ADD_BATCH_MAX_CHARS`, default 16MB). This prevents memory blowout on large corpora.

2. **Noise filtering**: `is_hard_message_noise()` filters out low-signal messages (empty content, tool acknowledgments) before indexing.

3. **Writer parallelism**: Auto-tuned based on available CPU cores, capped at 26 threads by default (empirically optimized). Governed by a "responsiveness" module that scales down under load.

4. **Bulk load merge policy**: During initial indexing, `configure_bulk_load_merge_policy()` is called to delay segment merging until after the bulk load completes.

5. **Segment management**: `optimize_if_idle()` / `force_merge()` for segment consolidation. `MergeStatus` tracks segment count, last merge timestamp, and cooldown.

6. **Federated search**: Multiple Tantivy index shards can be published as a federated bundle (`federated-search-manifest.json`). On read, all shards are searched in parallel. On write, the bundle is materialized back into a single mutable index.

### Query Building

Queries are built through `frankensearch::lexical::cass_build_tantivy_query()`. CASS adds:

- **NFC normalization**: All queries go through Unicode NFC normalization before Tantivy to match indexed content.
- **Boolean operator detection**: `cass_has_boolean_operators()` checks for AND/OR/NOT syntax.
- **Wildcard fallback**: If exact match returns too few results, automatically retries with prefix wildcard.
- **Edge n-grams**: Pre-computed edge n-grams stored alongside content for prefix matching.
- **Snippet generation**: `try_build_snippet_generator()` / `render_snippet_html()` for highlighting.

### Result Caching

Aggressive LRU caching with:
- **Sharded cache**: Per-agent cache shards with configurable capacity (default 256 per shard, 2048 total).
- **String interning**: Global `StringInterner` (10K capacity) for cache keys to reduce allocation.
- **Byte budget cap**: Optional `CASS_CACHE_BYTE_CAP` limits cache memory.
- **Bloom filter per hit**: 64-bit bloom for fast negative filtering during cache lookups.
- **Background warming**: Dedicated warm thread debounces reload + pre-warms hot queries.

## Semantic Search

### Embedding Pipeline

1. **Text canonicalization** (`src/search/canonicalize.rs`):
   - NFC Unicode normalization
   - Markdown stripping (backticks, headers, links)
   - Code block collapsing (first 20 + last 10 lines kept)
   - Whitespace normalization
   - Low-signal content filtering ("ok", "done", "thanks", etc.)
   - Truncation to 2000 chars max
   - Fast path: Pure ASCII without markdown bypasses the expensive pipeline

2. **Content hashing**: SHA-256 of canonical text for deduplication and memoization.

3. **Embedder trait** (`src/search/embedder.rs`):
   - Re-exports `frankensearch::SyncEmbed` as `Embedder`
   - Two implementations:
     - `HashEmbedder`: FNV-1a feature hashing, 256-dim, deterministic, instant, always available
     - `FastEmbedder`: ONNX MiniLM (all-MiniLM-L6-v2), 384-dim, requires model download

4. **Memoization**: Content-addressed memo cache (`ContentAddressedMemoCache`) avoids re-embedding unchanged messages.

### Vector Index

- **FSVI format** (frankensearch): File-backed vector index with f16 quantization.
- **HNSW ANN**: Optional approximate nearest neighbor via `hnsw_rs` for large corpora.
- **Doc ID encoding**: `SemanticDocId` packs message_id, chunk_idx, agent_id, workspace_id, source_id, role, created_at_ms, and content_hash into a string key using `itoa::Buffer` for zero-allocation integer formatting.

### Two-Tier Progressive Search

The most architecturally interesting piece (`src/search/two_tier_search.rs`):

```
User Query
    |--- Fast Embedder (in-process, ~1ms) ---> Instant results
    |--- Quality Daemon (warm UDS, ~130ms) ---> Refined re-ranking
```

- **Fast tier**: 256-dim hash embedder or small model, runs in-process
- **Quality tier**: 384-dim MiniLM via daemon process (Unix domain socket)
- **Score blending**: Normalized min-max scaling, then weighted blend (default 0.7 quality, 0.3 fast)
- **Progressive display**: Iterator-based API yields `SearchPhase::Initial` then `SearchPhase::Refined`

### Hybrid Search (RRF Fusion)

`rrf_fuse_hits()` merges lexical and semantic results using Reciprocal Rank Fusion:

1. Both result sets are converted to `frankensearch::ScoredResult` / `VectorHit`
2. `fs_rrf_fuse()` (frankensearch) computes fused scores with `RrfConfig::default()`
3. Content-level deduplication by (source_id, source_path, conversation_id, line_number, created_at, content_hash)
4. Lexical hit details preferred (they carry highlighted snippets)

### No-Limit Search Safety

Dynamic memory cap for unbounded queries:
- Reads `/proc/meminfo` for available RAM
- Takes 1/16th of available memory, clamped to [256MB, 16GB]
- Translates to hit count via estimated 80KB per hit
- Hard floor of 1,000 hits, hard ceiling of 1,000,000

## Encrypted HTML Export

### How It Works

`src/html_export/encryption.rs` implements Web Crypto compatible encryption:

1. **Key derivation**: PBKDF2-SHA256 with 600,000 iterations (matching Web Crypto API defaults)
2. **Encryption**: AES-256-GCM with random 16-byte salt + 12-byte IV
3. **Output**: `EncryptedContent { salt, iv, ciphertext, iterations }` as base64-encoded JSON
4. **HTML embedding**: Ciphertext placed in a hidden `<div id="encrypted-content">`, HTML-escaped for XSS safety
5. **Browser decryption**: JavaScript using `window.crypto.subtle` (Web Crypto API) performs the same PBKDF2 + AES-GCM decryption client-side

The exported HTML is fully self-contained: critical CSS/JS inlined, CDN resources optional (progressive enhancement). The file works offline and can be shared securely since the password never leaves the user's machine.

### Crypto Primitives (`src/encryption.rs`)

Clean, well-tested crypto module:
- `aes_gcm_encrypt/decrypt`: Proper length validation, AAD support, separate ciphertext/tag
- `argon2id_hash`: Used for key derivation in other contexts
- `hkdf_extract_expand`: Standard HKDF-SHA256
- `zeroize`: Key material wrapped in `Zeroizing<[u8; 32]>` for memory safety

## Code Quality Assessment

### Strengths

1. **Exhaustive test coverage**: 98K lines of tests including unit, integration, e2e, regression, property-based (proptest), fuzzing, and benchmark tests. Snapshot tests via insta. Real model fixtures for FastEmbed tests.

2. **Well-structured error handling**: `anyhow` for application errors with rich `.context()` chains. `thiserror` for domain-specific error types. Errors carry enough context to be actionable.

3. **Performance engineering**: String interning for cache keys, `itoa::Buffer` for hot-path integer formatting, `smallvec` for stack-allocated collections, `half::f16` for quantized embeddings, `bloomfilter` for probabilistic membership, SIMD via `wide` crate for dot products.

4. **Defensive resource management**: Dynamic memory caps, batch size limits, writer thread caps, retry with exponential backoff for SQLite busy errors.

5. **Schema evolution**: Versioned schemas with hash-based compatibility checks, migration runner in frankensqlite, historical bundle salvage for pre-migration databases.

### Anti-Patterns and Concerns

1. **God files**: `lib.rs` (28K), `indexer/mod.rs` (32K), `query.rs` (18K), `sqlite.rs` (19K), `app.rs` (46K) are all extremely large. These would benefit from decomposition.

2. **Wildcard version pinning**: Almost every dependency in Cargo.toml uses `version = "*"`. This is fragile for reproducibility. They compensate with Cargo.lock, but it is not a recommended practice.

3. **`unsafe impl Send`**: `SendConnection` wraps `frankensqlite::Connection` (which uses `Rc` internally) with `unsafe impl Send`. The safety argument is reasonable (Mutex guarantees exclusive access), but it is a maintenance burden. Two separate wrappers do this (`SendConnection` in query.rs, `SendFrankenConnection` in sqlite.rs).

4. **Over-extraction into sibling crates**: The `franken-*` constellation (`frankensearch`, `frankensqlite`, `franken_agent_detection`, `ftui`, `asupersync`) means the actual core logic is spread across 5+ repos pinned by git rev. Makes the codebase hard to understand as a whole. The sibling crates are all authored by the same person.

5. **Feature flag complexity**: The `encryption` feature flag guards the HTML export encryption, but the underlying crypto deps are already pulled in for ChatGPT decryption. The feature flag adds compile-time complexity without meaningful build-time savings.

6. **Environment variable proliferation**: Dozens of `dotenvy::var()` calls for runtime configuration (`CASS_TANTIVY_MAX_WRITER_THREADS`, `CASS_CACHE_SHARD_CAP`, `CASS_SEMANTIC_BATCH_SIZE`, etc.). No centralized config struct. Hard to discover all configuration options.

## Patterns Worth Adopting for history-matters

### 1. Normalize-Once Conversation Packet

The `ConversationPacket` contract (`src/model/conversation_packet.rs`) normalizes once, then feeds multiple sinks (SQLite, Tantivy, analytics, semantic). Each sink gets indices/hashes rather than re-processing raw text. This is a clean separation worth adopting.

### 2. Message-Level Tantivy Documents

Indexing individual messages rather than entire conversations gives precise search results. The doc carries enough metadata (agent, workspace, source_path, conversation_id) to reconstruct context. This is the right granularity for coding session search.

### 3. Batched Tantivy Writes with Backpressure

The dual-bounded batch system (max messages AND max chars) prevents both memory blowout on large messages and excessive commit overhead on many small messages. The governing system that scales writer threads under load is also worth studying.

### 4. Canonicalization Pipeline for Embeddings

The fast-path / slow-path canonicalization with content hashing for memoization is well-designed:
- Pure ASCII without markdown discriminators takes the cheap path
- Content hash prevents re-embedding unchanged messages
- Low-signal filtering removes noise before embedding

### 5. Two-Tier Progressive Search

The iterator-based progressive search API is elegant. Fast results display immediately while quality refinement runs asynchronously. The score normalization and weighted blending is clean. For history-matters, this pattern could enable instant hash-based results refined by ML embeddings.

### 6. Federated Index Shards

The federated search manifest system allows distributing Tantivy indexes across multiple files/machines while presenting a unified search interface. The materialize-on-write pattern (shards assembled into a mutable index when writes are needed) is clever.

### 7. Secret Redaction

`src/indexer/redact_secrets.rs` sanitizes API keys, tokens, and credentials before indexing. Essential for any tool that indexes coding sessions.

### 8. Schema Hash Versioning

Using a hash of the schema definition to detect incompatible index versions is more robust than simple version numbers. Forces a full rebuild only when the schema actually changes.

## What Not to Adopt

1. **The god-file pattern**: Keep files under 700 lines (per Stuart's rule).
2. **Wildcard dependency versions**: Pin versions properly.
3. **Environment variable sprawl**: Use a typed config struct with builder pattern.
4. **Sibling crate constellation**: Keep core logic in-repo unless genuinely reusable by other projects.
5. **Unsafe Send wrappers**: If your SQLite connection is `!Send`, design around it rather than overriding the safety guarantee.

## Sources Consulted

- `Cargo.toml`: Dependency graph, features, build config
- `src/connectors/mod.rs`, `src/connectors/claude_code.rs`: Connector architecture
- `src/model/types.rs`: Domain model (Message, Conversation, Snippet, Agent)
- `src/model/conversation_packet.rs`: Normalize-once packet contract
- `src/search/tantivy.rs`: Tantivy wrapper, schema, indexing, federated search
- `src/search/query.rs`: Search execution, caching, RRF fusion, hybrid search
- `src/search/two_tier_search.rs`: Progressive search architecture
- `src/search/embedder.rs`, `hash_embedder.rs`, `fastembed_embedder.rs`: Embedding pipeline
- `src/search/canonicalize.rs`: Text preprocessing
- `src/search/vector_index.rs`: Vector index facade, doc ID encoding
- `src/encryption.rs`: Crypto primitives
- `src/html_export/encryption.rs`, `mod.rs`: Encrypted HTML export
- `src/indexer/mod.rs`, `semantic.rs`: Indexing pipeline
- `src/storage/sqlite.rs`: SQLite backend
- `src/main.rs`, `src/lib.rs`: CLI entry point and command dispatch

## Open Questions

1. The actual Tantivy schema (field types, stored vs. indexed, tokenizer config) is in `frankensearch::lexical`, not in the CASS repo. A deeper review would require cloning frankensearch.
2. The connector parsing logic (how each of the 19 formats is actually parsed) is in `franken_agent_detection`. Only the abstraction boundary is visible here.
3. How the daemon process for quality embeddings is managed/started is in `src/daemon/`, which was not deeply reviewed.
4. The reranker pipeline (cross-encoder ms-marco-MiniLM-L-6-v2) was referenced but not deeply analyzed.
