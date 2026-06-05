---
title: Helioy Rust Architecture Specification
date: 2026-03-18
tags: [rust, architecture, helioy, specification, implementation]
type: specification
status: approved
source: rust-architecture-proposal-helioy-2026.md
---

# Helioy Rust Architecture Specification

Implementation spec derived from the Helioy Rust Architecture Proposal (2026-03-18). Contains exact type definitions, crate boundaries, data flow, error strategy, testing plan, and phased migration ordering.

## 1. Executive Summary

The helioy ecosystem contains four Rust projects at different maturity levels. This spec codifies a reference architecture based on what context-matters already does well (hexagonal core/store/cli split, manual JSON-RPC + tools.toml MCP, thiserror + anyhow error strategy) and prescribes concrete migrations for the three projects that diverge from it.

**Architecture pattern**: Hexagonal (ports and adapters) per workspace. Zero-I/O core crate defines domain types and a port trait. Store crate implements the trait against SQLite. CLI crate wires store to MCP server and CLI commands.

**Key decisions validated against code**:
- context-matters `ContextStore` trait is already async with `Send + Sync + 'static` bounds (confirmed in `cm-core/src/store.rs`).
- attention-matters ALP-1468 branch implements `AmStore` trait with associated error type, removes rmcp/schemars/tokio, adds manual JSON-RPC + tools.toml. Not yet merged to main.
- frontmatter-matters is a 31K LOC monolith (edition 2021). Workspace split is the highest-impact structural change remaining.
- nancyr has cross-workspace path dependencies on `am-core` and `am-store` via relative paths.

## 2. Crate Structure and Dependencies

### 2.1 Per-Project Workspace Layout

```
{project}/
  Cargo.toml              # virtual manifest, [workspace] only
  Cargo.lock
  justfile                 # check, build, test, fmt, clippy, install
  tools.toml               # MCP tool + CLI command definitions
  crates/
    {prefix}-core/         # domain types, port traits, errors. Zero I/O.
    {prefix}-parser/       # (fmm only) tree-sitter grammars + parser registry
    {prefix}-store/        # SQLite adapter (+ InMemoryStore for tests)
    {prefix}-cli/          # binary: CLI + MCP stdio server (build.rs here)
    {prefix}-http/         # binary: HTTP API (when needed)
  .github/
    workflows/
      ci.yml
      release.yml
```

**Note**: The `{prefix}-parser` crate is specific to fmm. Projects without heavy native parsing deps (cm, am) use the standard 3-crate layout.

### 2.2 Naming Convention

| Project            | Prefix  | Current State     | Target State        |
|--------------------|---------|-------------------|---------------------|
| context-matters    | `cm-`   | Workspace (3)     | No structural change |
| attention-matters  | `am-`   | Workspace (3)     | Merge ALP-1468      |
| frontmatter-matters| `fmm-`  | Monolith (1)      | Workspace (3)       |
| nancyr             | `nancy-`| Workspace (6)     | Edition/resolver update |

### 2.3 Workspace Cargo.toml Template

```toml
[workspace]
resolver = "3"
members = [
    "crates/{prefix}-core",
    "crates/{prefix}-store",
    "crates/{prefix}-cli",
]

[workspace.package]
version = "X.Y.Z"
edition = "2024"
license = "MIT"
repository = "https://github.com/srobinson/{project}"

[workspace.dependencies]
{prefix}-core = { path = "crates/{prefix}-core" }
{prefix}-store = { path = "crates/{prefix}-store" }

# Shared deps with pinned versions
serde = { version = "1", features = ["derive"] }
serde_json = "1"
thiserror = "2.0"
uuid = { version = "1", features = ["v7", "serde"] }
# ... project-specific deps

[profile.release]
lto = true
codegen-units = 1
strip = true
opt-level = 3
```

### 2.4 Dependency Direction (Invariant)

```
cli ──depends-on──▶ store ──depends-on──▶ core
cli ──depends-on──▶ core

core: zero I/O dependencies (no sqlx, rusqlite, tokio, fs, network)
store: database deps only (sqlx or rusqlite)
cli: application deps (clap, tokio, tracing-subscriber, anyhow)
```

No reverse dependencies. No circular dependencies. Core never imports store or cli.

## 3. Core Domain Types

### 3.1 context-matters (`cm-core`)

Types as they exist today. These are the reference implementation.

```rust
// ── Scope hierarchy ──

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum ScopeKind {
    Global = 0,
    Project = 1,
    Repo = 2,
    Session = 3,
}

/// Validated, immutable scope path. Invariants enforced at construction.
/// Starts with "global", segments follow kind:identifier format,
/// kinds in ascending order, identifiers match [a-z0-9][a-z0-9-]*[a-z0-9].
#[derive(Debug, Clone, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(try_from = "String", into = "String")]
pub struct ScopePath(String);

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Scope {
    pub path: ScopePath,
    pub kind: ScopeKind,
    pub label: String,
    pub parent_path: Option<ScopePath>,
    pub meta: Option<serde_json::Value>,
    pub created_at: DateTime<Utc>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NewScope {
    pub path: ScopePath,
    pub label: String,
    pub meta: Option<serde_json::Value>,
}

// ── Entry types ──

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum EntryKind {
    Fact, Decision, Preference, Lesson, Reference, Feedback, Pattern, Observation,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Confidence { High, Medium, Low }

#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct EntryMeta {
    pub tags: Vec<String>,
    pub confidence: Option<Confidence>,
    pub source: Option<String>,
    pub expires_at: Option<DateTime<Utc>>,
    pub priority: Option<i32>,
    #[serde(flatten)]
    pub extra: HashMap<String, serde_json::Value>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Entry {
    pub id: Uuid,              // UUIDv7, time-sortable
    pub scope_path: ScopePath,
    pub kind: EntryKind,
    pub title: String,
    pub body: String,
    pub content_hash: String,  // BLAKE3 hex (64 chars)
    pub meta: Option<EntryMeta>,
    pub created_by: String,
    pub created_at: DateTime<Utc>,
    pub updated_at: DateTime<Utc>,
    pub superseded_by: Option<Uuid>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NewEntry {
    pub scope_path: ScopePath,
    pub kind: EntryKind,
    pub title: String,
    pub body: String,
    pub created_by: String,
    pub meta: Option<EntryMeta>,
}

#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct UpdateEntry {
    pub title: Option<String>,
    pub body: Option<String>,
    pub kind: Option<EntryKind>,
    pub meta: Option<EntryMeta>,
}

// ── Relations ──

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum RelationKind {
    Supersedes, RelatesTo, Contradicts, Elaborates, DependsOn,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EntryRelation {
    pub source_id: Uuid,
    pub target_id: Uuid,
    pub relation: RelationKind,
    pub created_at: DateTime<Utc>,
}

// ── Pagination ──

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PaginationCursor {
    pub updated_at: DateTime<Utc>,
    pub id: Uuid,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Pagination {
    pub limit: u32,           // default: 50
    pub cursor: Option<PaginationCursor>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PagedResult<T> {
    pub items: Vec<T>,
    pub total: u64,
    pub next_cursor: Option<PaginationCursor>,
}

// ── Filtering ──

#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct EntryFilter {
    pub scope_path: Option<ScopePath>,
    pub kind: Option<EntryKind>,
    pub tag: Option<String>,
    pub created_by: Option<String>,
    pub include_superseded: bool,
    pub pagination: Pagination,
}

// ── Stats ──

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TagCount { pub tag: String, pub count: u64 }

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct StoreStats {
    pub active_entries: u64,
    pub superseded_entries: u64,
    pub scopes: u64,
    pub relations: u64,
    pub entries_by_kind: HashMap<String, u64>,
    pub entries_by_scope: HashMap<String, u64>,
    pub entries_by_tag: Vec<TagCount>,
    pub db_size_bytes: u64,
}
```

### 3.2 attention-matters (`am-core`)

Types as they exist on main. These are stable and should not change.

```rust
// ── Geometric primitives ──

#[derive(Clone, Copy, Debug, Serialize, Deserialize)]
pub struct Quaternion {
    pub w: f64,
    pub x: f64,
    pub y: f64,
    pub z: f64,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct DaemonPhasor {
    pub phase: f64,
    pub frequency: f64,
    pub amplitude: f64,
}

// ── Core domain types ──

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize, Default)]
#[serde(rename_all = "lowercase")]
pub enum NeighborhoodType {
    #[default] Memory,
    Decision,
    Preference,
    Insight,
    Ingested,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct Occurrence {
    pub id: Uuid,
    pub word: String,
    pub position: Quaternion,
    pub phasor: DaemonPhasor,
    pub activation_count: u32,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct Neighborhood {
    pub id: Uuid,
    pub seed: Quaternion,
    pub occurrences: Vec<Occurrence>,
    pub source_text: String,
    pub neighborhood_type: NeighborhoodType,
    pub epoch: u64,
    pub superseded_by: Option<Uuid>,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct Episode {
    pub id: Uuid,
    pub name: String,
    pub neighborhoods: Vec<Neighborhood>,
    pub is_conscious: bool,
    pub timestamp: String,
}

// ── System container ──

#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash)]
pub enum EpisodeRef {
    Conscious,
    Subconscious(usize),
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash)]
pub struct OccurrenceRef {
    pub episode_ref: EpisodeRef,
    pub neighborhood_idx: usize,
    pub occurrence_idx: usize,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct NeighborhoodRef {
    pub episode_ref: EpisodeRef,
    pub neighborhood_idx: usize,
}

/// Top-level container. Episodes + conscious_episode + lazy-rebuilt indexes.
/// 20 public methods, near decomposition threshold.
#[derive(Serialize, Deserialize)]
pub struct DAESystem {
    pub episodes: Vec<Episode>,
    pub conscious_episode: Episode,
    pub agent_name: String,
    pub next_epoch: u64,
    // serde(skip): 4 index HashMaps + index_dirty flag
}

// ── Query/composition types ──

pub struct QueryManifest {
    pub drifted: Vec<Uuid>,
    pub activated: Vec<Uuid>,
    pub demoted_activations: Vec<(Uuid, u32)>,
}

pub struct QueryResult {
    pub activation: ActivationResult,
    pub interference: Vec<InterferenceResult>,
    pub word_groups: Vec<WordGroup>,
    pub query_token_count: usize,
    pub manifest: QueryManifest,
}

// ── Store support types (am-store) ──

#[derive(Debug)]
pub struct ActivationStats {
    pub total: u64,
    pub zero_activation: u64,
    pub max_activation: u32,
    pub mean_activation: f64,
}

#[derive(Debug)]
pub struct GcResult {
    pub evicted_occurrences: u64,
    pub removed_neighborhoods: u64,
    pub removed_episodes: u64,
    pub before_occurrences: u64,
    pub before_size: u64,
    pub after_size: u64,
}

#[derive(Debug)]
pub struct EpisodeInfo {
    pub id: String,
    pub name: String,
    pub is_conscious: bool,
    pub timestamp: String,
    pub neighborhood_count: u64,
    pub occurrence_count: u64,
    pub total_activation: u64,
}

#[derive(Debug)]
pub struct NeighborhoodDetail {
    pub id: String,
    pub source_text: String,
    pub episode_name: String,
    pub is_conscious: bool,
    pub occurrence_count: u64,
    pub total_activation: u64,
    pub max_activation: u32,
}
```

### 3.3 frontmatter-matters (existing types, moved as-is during split)

The fmm codebase has stable, well-tested types. The workspace split moves them into `fmm-core` without renaming or restructuring. Inventing new types during a structural migration adds unnecessary risk.

**Authoritative source**: The exact field definitions, signatures, and generic parameters are the source code in `parser/mod.rs` and `manifest/mod.rs`. The listings below are illustrative to show the shape and relationships of the types. The split will mechanically move the actual types from source.

**Types from `parser/mod.rs` → `fmm-core`:**

```rust
/// A single exported symbol from a source file.
pub struct ExportEntry {
    pub name: String,
    pub start_line: usize,
    pub end_line: usize,
    pub parent_class: Option<String>,  // distinguishes top-level from class methods
    pub kind: Option<String>,           // "nested-fn", "closure-state", or None
}

/// Parser output metadata for a single file.
pub struct Metadata {
    pub imports: Vec<String>,           // raw import paths
    pub exports: Vec<String>,           // exported symbol names
    pub default_export: Option<String>,
    pub named_imports: HashMap<String, Vec<String>>,  // source → imported names
    pub namespace_imports: Vec<String>,                // wildcard imports
    // additional fields per parser
}

/// Full result from parsing a single file.
pub struct ParseResult {
    pub metadata: Metadata,
    pub entries: Vec<ExportEntry>,
}

/// Static descriptor for a language module.
pub struct RegisteredLanguage {
    pub language_id: &'static str,
    pub extensions: &'static [&'static str],
    pub reexport_filenames: &'static [&'static str],
    pub test_patterns: LanguageTestPatterns,
}

/// Patterns used to detect test files per language.
pub struct LanguageTestPatterns {
    // path segments and filename suffixes
}

/// Port trait for language parsers.
pub trait Parser: Send + Sync {
    fn parse(&self, source: &str, path: &str) -> ParseResult;
    // ...
}
```

**Types from `manifest/mod.rs` → `fmm-core`:**

```rust
/// A complete file entry in the in-memory manifest.
pub struct FileEntry {
    pub path: String,
    pub language: String,             // language_id string, not an enum
    pub loc: u32,
    pub exports: Vec<String>,
    pub imports: Vec<String>,
    pub dependencies: Vec<String>,    // resolved dependencies
    pub named_imports: HashMap<String, Vec<String>>,
    pub namespace_imports: Vec<String>,
    pub export_lines: Option<Vec<ExportLines>>,
    pub methods: Option<HashMap<String, ExportLines>>,
    pub function_names: Vec<String>,
    pub nested_fns: Vec<String>,      // ALP-922 nested symbols
    pub closure_state: Vec<String>,   // ALP-922 closure captures
    pub modified_at: String,
}

/// Line range for an export or method.
pub struct ExportLines {
    pub start: usize,
    pub end: usize,
}

/// Resolved export location with source file.
pub struct ExportLocation {
    pub file: String,
    pub export: ExportEntry,
}

/// Central in-memory read model. Built from SQLite, queried by MCP tools.
pub struct Manifest {
    pub files: HashMap<String, FileEntry>,
    pub export_index: HashMap<String, Vec<ExportLocation>>,
    pub export_locations: HashMap<String, Vec<ExportLocation>>,
    pub export_all: HashMap<String, Vec<String>>,
    pub function_index: HashMap<String, Vec<ExportLocation>>,
    pub method_index: HashMap<String, Vec<ExportLocation>>,
    pub reverse_deps: HashMap<String, Vec<String>>,
    pub workspace_packages: HashMap<String, PathBuf>,
    pub workspace_roots: Vec<PathBuf>,
}
```

**Note on languages**: Languages are identified by string IDs and extension mappings on `RegisteredLanguage`, not by an enum. The dynamic `ParserRegistry` registration pattern (via `register_language!` macro) requires this flexibility. Creating a `Language` enum would conflict with the macro-based registration.

## 4. Port Traits (Store Interfaces)

### 4.1 context-matters: `ContextStore`

```rust
// cm-core/src/store.rs (current, on main)

/// Async storage interface for context entries.
/// Native async fn in trait (stable since Rust 1.75).
/// Consumers use generics, not dyn, because native async traits
/// do not support dynamic dispatch without boxing.
#[allow(async_fn_in_trait)]
pub trait ContextStore: Send + Sync + 'static {
    // Entry CRUD
    async fn create_entry(&self, new_entry: NewEntry) -> Result<Entry, CmError>;
    async fn get_entry(&self, id: Uuid) -> Result<Entry, CmError>;
    async fn get_entries(&self, ids: &[Uuid]) -> Result<Vec<Entry>, CmError>;
    async fn resolve_context(
        &self, scope_path: &ScopePath, kinds: &[EntryKind], limit: u32,
    ) -> Result<Vec<Entry>, CmError>;
    async fn search(
        &self, query: &str, scope_path: Option<&ScopePath>, limit: u32,
    ) -> Result<Vec<Entry>, CmError>;
    async fn browse(&self, filter: EntryFilter) -> Result<PagedResult<Entry>, CmError>;
    async fn update_entry(&self, id: Uuid, update: UpdateEntry) -> Result<Entry, CmError>;
    async fn supersede_entry(&self, old_id: Uuid, new_entry: NewEntry) -> Result<Entry, CmError>;
    async fn forget_entry(&self, id: Uuid) -> Result<(), CmError>;

    // Relations
    async fn create_relation(
        &self, source_id: Uuid, target_id: Uuid, relation: RelationKind,
    ) -> Result<EntryRelation, CmError>;
    async fn get_relations_from(&self, source_id: Uuid) -> Result<Vec<EntryRelation>, CmError>;
    async fn get_relations_to(&self, target_id: Uuid) -> Result<Vec<EntryRelation>, CmError>;

    // Scopes
    async fn create_scope(&self, new_scope: NewScope) -> Result<Scope, CmError>;
    async fn get_scope(&self, path: &ScopePath) -> Result<Scope, CmError>;
    async fn list_scopes(&self, kind: Option<ScopeKind>) -> Result<Vec<Scope>, CmError>;

    // Aggregation
    async fn stats(&self) -> Result<StoreStats, CmError>;
    async fn export(&self, scope_path: Option<&ScopePath>) -> Result<Vec<Entry>, CmError>;
}
```

**Design notes**:
- Concrete error type (`CmError`) instead of associated type. Justified because cm has a single store backend (sqlx SQLite) and the error variants are domain-semantic (EntryNotFound, DuplicateContent), not adapter-specific.
- Async signatures match the sqlx backend. Single-client stdio model means the async is a convenience wrapper, not a concurrency enabler.
- 17 methods. Below the decomposition threshold.

### 4.2 attention-matters: `AmStore`

```rust
// am-core/src/store_trait.rs (ALP-1468 branch, not yet on main)

/// Hexagonal port for DAE persistence.
/// Sync signatures: rusqlite is synchronous and a single-client stdio
/// server gains nothing from async wrappers.
pub trait AmStore {
    type Error: std::error::Error + Send + Sync + 'static;

    // System lifecycle
    fn load_system(&self) -> Result<DAESystem, Self::Error>;
    fn save_system(&self, system: &DAESystem) -> Result<(), Self::Error>;

    // Incremental persistence
    fn save_episode(&self, episode: &Episode) -> Result<(), Self::Error>;
    fn save_neighborhood(
        &self, episode: &Episode, neighborhood: &Neighborhood,
    ) -> Result<(), Self::Error>;
    fn batch_increment_activation(&self, ids: &[Uuid]) -> Result<(), Self::Error>;
    fn batch_set_activation_counts(&self, batch: &[(Uuid, u32)]) -> Result<(), Self::Error>;
    fn save_occurrence_positions(
        &self, batch: &[(Uuid, Quaternion, DaemonPhasor)],
    ) -> Result<(), Self::Error>;
    fn mark_superseded(&self, old_id: Uuid, new_id: Uuid) -> Result<(), Self::Error>;

    // Conversation buffer
    fn append_buffer(&self, user: &str, assistant: &str) -> Result<usize, Self::Error>;
    fn drain_buffer(&self) -> Result<Vec<(String, String)>, Self::Error>;
    fn buffer_count(&self) -> Result<usize, Self::Error>;

    // Stats and health
    fn activation_distribution(&self) -> Result<ActivationStats, Self::Error>;
    fn db_size(&self) -> u64;
    fn health_check(&self) -> Result<(), Self::Error>;
    fn checkpoint_truncate(&self) -> Result<(), Self::Error>;

    // CLI-facing (forget, import/export)
    fn forget_episode(&self, episode_id: &str) -> Result<u64, Self::Error>;
    fn forget_conscious(&self, neighborhood_id: &str) -> Result<u64, Self::Error>;
    fn forget_term(&self, term: &str) -> Result<(u64, u64, u64), Self::Error>;
    fn import_json_str(&self, json: &str) -> Result<(), Self::Error>;
    fn export_json_string(&self) -> Result<String, Self::Error>;
}
```

**Design notes**:
- Associated error type (`type Error`) because am has two store implementations: `BrainStore` (rusqlite, `StoreError`) and `InMemoryStore` (test double, `MemoryStoreError`).
- Sync signatures. Correct for rusqlite backend.
- 20 methods. At the decomposition threshold noted in DAESystem. If more methods are needed, consider splitting read-only queries from mutations.
- Full persistence port: includes CLI-only operations (forget, import/export), not just MCP surface.
- **Naming nit** (from implementation review): `import_json_str` / `export_json_string` asymmetry. Consider `import_json` / `export_json`. Not a blocker.
- **Infallibility note**: `db_size(&self) -> u64` is intentionally infallible. Returns 0 for in-memory stores or missing database files. Document this explicitly in the trait.

### 4.3 frontmatter-matters: `FmmStore` (target)

fmm uses a **batch-write + in-memory-read** pattern, not per-entry CRUD. The indexer writes in bulk transactions. The MCP server loads the entire `Manifest` into memory on startup and queries it via HashMap lookups. No SQL runs at MCP query time.

The trait surface reflects these actual semantics:

```rust
// fmm-core/src/store.rs (to be created during workspace split)

/// Batch-oriented storage interface for code metadata.
///
/// Write path: indexer calls begin_batch → upsert_file (×N) → commit_batch
/// in a single SQLite transaction. CPU-bound parsing happens outside the
/// transaction via rayon parallelism.
///
/// Read path: load_manifest() builds the entire in-memory Manifest from
/// SQLite in one pass. MCP tools query the Manifest, not the database.
pub trait FmmStore {
    type Error: std::error::Error + Send + Sync + 'static;

    // Lifecycle
    fn initialize(&self) -> Result<(), Self::Error>;

    // Batch write (indexer path)
    fn begin_batch(&mut self) -> Result<(), Self::Error>;
    fn upsert_file(&mut self, row: &PreserializedRow) -> Result<(), Self::Error>;
    fn delete_all_files(&mut self) -> Result<(), Self::Error>;
    fn commit_batch(&mut self) -> Result<(), Self::Error>;
    fn write_reverse_deps(
        &mut self, deps: &HashMap<String, Vec<String>>,
    ) -> Result<(), Self::Error>;
    fn write_workspace_packages(
        &mut self, pkgs: &HashMap<String, PathBuf>,
    ) -> Result<(), Self::Error>;
    fn write_meta(&mut self, key: &str, value: &str) -> Result<(), Self::Error>;

    // Bulk read (MCP server startup)
    fn load_manifest(&self) -> Result<Manifest, Self::Error>;

    // Staleness checks (incremental indexer)
    fn load_indexed_mtimes(&self) -> Result<HashMap<String, String>, Self::Error>;
}
```

**Design notes**:
- `&mut self` on write methods: SQLite single-writer model. Batch callers hold exclusive access.
- No per-entry lookup methods. All MCP queries go through the in-memory `Manifest`.
- `PreserializedRow` encapsulates the file data serialized by the indexer (CPU-bound work happens in rayon, serialization before the write lock).
- `InMemoryFmmStore` test double: holds a `Manifest` and a `Vec<PreserializedRow>`. Batch write populates them. `load_manifest` returns accumulated state.

## 5. Module Boundaries and Public API Surface

### 5.1 context-matters

```
cm-core (lib crate)
├── pub mod types      → ScopeKind, ScopePath, Scope, NewScope, EntryKind,
│                        Confidence, EntryMeta, Entry, NewEntry, UpdateEntry,
│                        RelationKind, EntryRelation, PaginationCursor,
│                        Pagination, PagedResult, EntryFilter, TagCount, StoreStats
├── pub mod error      → ScopePathError, CmError
├── pub mod store      → ContextStore trait
└── pub mod query      → (query builder helpers, internal)

cm-store (lib crate)
├── pub struct CmStore → impl ContextStore for CmStore
├── pub fn open_store() → CmStore constructor (pool setup, migrations)
└── (internal: SQL queries, migration files, pool config)

cm-cli (bin crate)
├── pub mod mcp        → McpServer<S: ContextStore>, tool handlers, JSON-RPC loop
├── pub mod cli        → CLI-only commands (stats)
└── main.rs            → Cli struct, Commands enum, main()
```

### 5.2 attention-matters (post-ALP-1468)

```
am-core (lib crate)
├── pub types          → Quaternion, DaemonPhasor, Occurrence, Neighborhood,
│                        NeighborhoodType, Episode, DAESystem, EpisodeRef,
│                        OccurrenceRef, NeighborhoodRef, ActivationStats
├── pub store_trait    → AmStore trait
├── pub query          → QueryEngine, QueryResult, QueryManifest
├── pub compose        → compose_context, compose_index, BudgetConfig, etc.
├── pub batch          → BatchQueryEngine
├── pub feedback       → apply_feedback, FeedbackSignal
├── pub salient        → extract_salient, mark_salient_typed
├── pub serde_compat   → import_json, export_json (v0.7.2 wire format)
└── pub tokenizer      → tokenize, ingest_text, token_count

am-store (lib crate)
├── pub struct BrainStore    → impl AmStore for BrainStore
├── pub struct InMemoryStore → impl AmStore for InMemoryStore (test double)
├── pub config               → Config, RetentionPolicy
├── pub error                → StoreError, MemoryStoreError
└── (internal: schema, json_bridge, project dir management)

am-cli (bin crate)
├── pub server         → AmServer<S: AmStore>, tool handlers
├── pub jsonrpc        → JSON-RPC types, stdio loop
├── pub sync           → Claude Code sync (conversation ingest)
├── pub sync_dispatch  → sync format dispatch
└── main.rs            → Cli, Commands, main()
```

### 5.3 frontmatter-matters (target, post-split, 4 crates)

```
fmm-core (lib crate) — zero I/O, zero tree-sitter
├── pub types          → ExportEntry, Metadata, ParseResult, FileEntry,
│                        ExportLines, ExportLocation, RegisteredLanguage,
│                        LanguageTestPatterns, PreserializedRow
├── pub manifest       → Manifest (in-memory read model), rebuild_reverse_deps()
├── pub error          → FmmError
├── pub store          → FmmStore trait, Parser trait
└── (no tree-sitter deps, no rusqlite, no clap)

fmm-parser (lib crate) — tree-sitter grammars live here
├── pub registry       → ParserRegistry, ParserFactory, register_language! macro
├── pub builtin        → 18 language parser implementations
│   ├── typescript, javascript, python, rust, go, java, ...
│   └── (each module provides a DESCRIPTOR const + Parser impl)
└── depends on: fmm-core (for Parser trait, ExportEntry, Metadata, ParseResult)

fmm-store (lib crate) — SQLite persistence
├── pub struct FmmSqliteStore → impl FmmStore
├── pub reader         → load_manifest_from_db(), load_exports()
├── pub writer         → serialize_file_data(), upsert_preserialized()
├── pub schema         → table definitions, migrations
└── depends on: fmm-core (for FmmStore trait, Manifest, FileEntry, etc.)

fmm-cli (bin crate) — wiring + application logic
├── pub mcp            → MCP server + tool handlers (query Manifest, not DB)
├── pub cli            → CLI commands (init, index, validate, watch, etc.)
├── pub config         → .fmmrc.toml handling
├── pub format         → output formatters (json, text, table)
├── pub search         → search/FTS utilities
├── pub extractor      → glossary_builder (562 LOC), dependency_matcher (616 LOC),
│                        call_site_finder, private_members
├── pub resolver       → cross-package import resolution (oxc_resolver)
└── main.rs            → ParserRegistry::with_builtins(), store construction,
                         Manifest load, command dispatch
    depends on: fmm-core, fmm-parser, fmm-store
```

**Key boundary decision**: `Manifest` definition lives in `fmm-core` (it's a domain type). `load_manifest_from_db()` lives in `fmm-store` (it knows how to build a Manifest from SQLite). Domain logic on Manifest (like `rebuild_reverse_deps`) stays with it in `fmm-core`. `ParserRegistry` lives in `fmm-parser` (it holds factory closures that construct concrete parser instances). `fmm-cli` constructs `ParserRegistry::with_builtins()` in `main.rs` and passes it down.

## 6. Data Flow Diagrams

### 6.1 MCP Tool Call (context-matters, representative)

```
Claude Code (stdio)
    │
    │  JSON-RPC: {"method":"tools/call","params":{"name":"cx_recall",...}}
    ▼
cm-cli: JSON-RPC loop (stdin reader)
    │
    │  parse JsonRpcRequest, route by tool name
    ▼
cm-cli: tool handler fn cx_recall(store: &impl ContextStore, args: &Value)
    │
    │  validate args, parse scope_path
    │  call store.resolve_context(scope_path, kinds, limit)
    ▼
cm-store: CmStore::resolve_context()
    │
    │  SQL: SELECT from entries JOIN scopes, FTS5 ranking
    │  ancestor walk via scope_path.ancestors()
    ▼
cm-cli: tool handler formats response
    │
    │  Entry → JSON with snippet (body truncated to 200 chars)
    │  CmError → actionable string with recovery guidance
    ▼
cm-cli: JSON-RPC response (stdout)
    │
    │  {"result":{"content":[{"type":"text","text":"..."}]}}
    ▼
Claude Code
```

### 6.2 DAE Query Cycle (attention-matters)

```
Claude Code (stdio)
    │
    │  JSON-RPC: tools/call "am_query"
    ▼
am-cli: AmServer<S>.handle_tool("am_query", args)
    │
    │  lock state mutex (serialized access)
    ▼
am-core: QueryEngine::process_query(&mut system, query)
    │
    │  1. tokenize(query)
    │  2. activate_word() for each token (updates activation_count)
    │  3. compute phasor interference (sub × con manifolds)
    │  4. SLERP drift (IDF-weighted position updates)
    │  5. Kuramoto coupling (phase synchronization)
    │  ──▶ returns QueryResult + QueryManifest
    ▼
am-core: compose_context(&system, &query_result, limit)
    │
    │  score neighborhoods by activation + interference + recency
    │  sort, deduplicate, truncate to token budget
    ▼
am-cli: persist mutations via AmStore
    │
    │  store.batch_increment_activation(manifest.activated)
    │  store.save_occurrence_positions(manifest.drifted)
    ▼
am-cli: format response → JSON-RPC → stdout
```

### 6.3 Indexing Pipeline (frontmatter-matters)

```
$ fmm index [path]
    │
    │  walk directory tree (ignore crate, respects .gitignore)
    ▼
fmm: detect language per file (extension + shebang)
    │
    │  parallel via rayon (thread pool)
    ▼
fmm: tree-sitter parse → AST
    │
    │  per-language extractor (exports, imports, line ranges)
    ▼
fmm: resolve imports (oxc_resolver for JS/TS, path resolution for others)
    │
    │  build FileManifest per file
    ▼
fmm: upsert into SQLite (rusqlite, single writer)
    │
    │  files table, exports table, imports table, FTS5 index
    ▼
fmm: .fmm.db ready for MCP queries
```

## 7. Error Handling Strategy

### 7.1 Error Enum Definitions

**cm-core errors** (current, reference implementation):

```rust
#[derive(Debug, Error)]
pub enum ScopePathError {
    #[error("scope path cannot be empty")]
    Empty,
    #[error("scope path too long: {len} bytes (max {max})")]
    TooLong { len: usize, max: usize },
    #[error("scope path must start with 'global'")]
    MissingGlobalRoot,
    #[error("malformed segment: '{0}' (expected 'kind:identifier')")]
    MalformedSegment(String),
    #[error("invalid scope kind: '{0}' (expected global, project, repo, or session)")]
    InvalidKind(String),
    #[error("scope kind '{got}' cannot appear after '{after}'")]
    OutOfOrder { got: String, after: String },
    #[error("invalid identifier: '{0}' (must match [a-z0-9][a-z0-9-]*[a-z0-9])")]
    InvalidIdentifier(String),
}

#[derive(Debug, Error)]
pub enum CmError {
    #[error("entry not found: {0}")]
    EntryNotFound(Uuid),
    #[error("scope not found: {0}")]
    ScopeNotFound(String),
    #[error("duplicate content: existing entry {0}")]
    DuplicateContent(Uuid),
    #[error("invalid scope path: {0}")]
    InvalidScopePath(#[from] ScopePathError),
    #[error("invalid entry kind: {0}")]
    InvalidEntryKind(String),
    #[error("invalid relation kind: {0}")]
    InvalidRelationKind(String),
    #[error("validation error: {0}")]
    Validation(String),
    #[error("constraint violation: {0}")]
    ConstraintViolation(String),
    #[error("json error: {0}")]
    Json(#[from] serde_json::Error),
    #[error("database error: {0}")]
    Database(String),
    #[error("internal error: {0}")]
    Internal(String),
}
```

**am-store errors** (current, on main):

```rust
#[derive(Debug)]
pub enum StoreError {
    Sqlite(rusqlite::Error),
    Io(std::io::Error),
    InvalidData(String),
}

// Manual Display + Error impls (no thiserror)
// Manual From<rusqlite::Error> and From<std::io::Error>
```

**Target for am-store**: Migrate to `thiserror` for consistency. Low priority since the current manual impls are correct and complete.

**fmm errors** (target):

```rust
// fmm-core/src/error.rs

#[derive(Debug, Error)]
pub enum FmmError {
    #[error("file not found: {0}")]
    FileNotFound(String),
    #[error("unsupported language: {0}")]
    UnsupportedLanguage(String),
    #[error("parse error in {path}: {detail}")]
    Parse { path: String, detail: String },
    #[error("index not found: run `fmm init` first")]
    NoIndex,
    #[error("index version mismatch: expected {expected}, found {found}")]
    VersionMismatch { expected: String, found: String },
    #[error("database error: {0}")]
    Database(String),
    #[error("io error: {0}")]
    Io(#[from] std::io::Error),
    #[error("config error: {0}")]
    Config(String),
}
```

### 7.2 Error Handling Rules

| Layer | Strategy | Crate |
|-------|----------|-------|
| Domain types | `thiserror` with descriptive variants | `*-core` |
| Store adapter | `thiserror` wrapping database errors | `*-store` |
| CLI boundary | `anyhow` for top-level `Result<()>` | `*-cli/main.rs` |
| MCP tool handlers | Operational errors → successful response with recovery guidance. Protocol errors → JSON-RPC error. | `*-cli/mcp/` |

**MCP error-as-UI pattern** (from context-matters, to be adopted by all):

```rust
// Operational errors: return as tool result with isError: true
fn cm_err_to_string(err: CmError) -> String {
    match err {
        CmError::EntryNotFound(id) =>
            format!("Entry not found: {id}. Verify the ID using cx_browse or cx_recall."),
        CmError::DuplicateContent(id) =>
            format!("Duplicate content detected. Existing entry: {id}. Use cx_update to modify."),
        // ... actionable messages for every variant
    }
}

// Protocol errors: JSON-RPC error response
// Reserved for: method not found, invalid params, internal server crash
```

## 8. Testing Strategy

### 8.1 Test Layers Per Crate

| Layer | Location | What | How | Runner |
|-------|----------|------|-----|--------|
| Unit | `*-core/src/` `#[cfg(test)]` | Pure logic, type validation, error formatting | Inline `#[test]` | nextest |
| Store integration | `*-store/tests/` | All trait methods against real SQLite | In-memory DB per test | nextest |
| Tool handler | `*-cli/tests/` | MCP tool handlers against InMemoryStore | Function-level, `insta` snapshots | nextest |
| Subprocess MCP | `*-cli/tests/` | Full JSON-RPC protocol over stdio | `assert_cmd`, spawn binary | nextest |
| Property | `*-core/tests/` | Serialization round-trips, parsing invariants | `proptest` | nextest |

### 8.2 Test Infrastructure Per Project

**context-matters** (current gaps to fill):
- [ ] Switch `just test` from `cargo test` to `cargo nextest run`
- [ ] Add `insta` snapshot tests for MCP tool response format
- [ ] Add subprocess MCP protocol tests via `assert_cmd`
- [ ] Property tests for cursor encode/decode and scope path parsing

**attention-matters** (ALP-1468 branch already includes):
- [x] InMemoryStore test double with `std::sync::Mutex` (Send-compatible)
- [x] `insta` snapshot tests for all 12 tool responses
- [x] Subprocess MCP protocol tests
- [x] `cargo nextest` in justfile and CI

**frontmatter-matters** (after workspace split):
- [ ] Extract unit tests into `fmm-core/src/` inline tests
- [ ] Create `InMemoryFmmStore` (holds a `Manifest` + `Vec<PreserializedRow>`)
- [ ] Add `insta` snapshots for MCP tool output format
- [ ] Property tests for language detection and export extraction
- [ ] Parser tests remain in `fmm-parser` (each builtin language module has inline tests)

### 8.3 InMemoryStore Contract

Every project with a store trait must provide an `InMemoryStore` in the store crate:

```rust
// Pattern: std::sync::Mutex for interior mutability (Send-safe)
pub struct InMemoryStore {
    state: std::sync::Mutex<InMemoryState>,
}

// Must impl the same trait as the real store
impl AmStore for InMemoryStore {
    type Error = MemoryStoreError;
    // ...
}
```

**Requirement**: `InMemoryStore` must be `Send`. Use `std::sync::Mutex`, not `RefCell`. This was a concrete bug in attention-matters ALP-1468 where `RefCell` broke `AmServer` construction.

## 9. Migration Phasing

### Phase 0: Merge ALP-1468 (attention-matters) — Immediate

**Status**: Code complete on `nancy/ALP-1468` branch. 19 commits. Not merged.

**What it does**:
1. Defines `AmStore` trait in `am-core/src/store_trait.rs` (20 methods, associated error type)
2. Implements `BrainStore: AmStore` and `InMemoryStore: AmStore`
3. Removes rmcp, schemars, tokio dependencies
4. Implements manual JSON-RPC stdio loop + `tools.toml` + `build.rs`
5. Makes `AmServer` generic over `S: AmStore`
6. Adds `insta` snapshot tests, subprocess MCP protocol tests, nextest

**Risk**: Low. The branch has been through clinical review and multiple iterations.

**Ordering**: Independent. No blockers.

### Phase 1: context-matters Testing Hardening — High Priority

**What to do**:
1. Switch `just test` recipe to `cargo nextest run --workspace`
2. Add `insta` snapshot tests for all MCP tool response formats (cx_store, cx_recall, cx_browse, cx_get, cx_update, cx_forget, cx_deposit, cx_stats, cx_export)
3. Add subprocess MCP tests via `assert_cmd` (initialize, tools/list, one tools/call round-trip)
4. Add `proptest` tests for `PaginationCursor` encode/decode and `ScopePath::parse`

**Risk**: Low. Additive only. No behavioral changes.

**Ordering**: Independent. No blockers.

### Phase 2: frontmatter-matters Workspace Split — Medium Priority

**What to do**: Split the 31K LOC monolith into 4 crates: `fmm-core`, `fmm-parser`, `fmm-store`, `fmm-cli`.

**Risk**: Medium. The primary risk is hidden coupling between parser types and manifest types. Mitigated by moving both into `fmm-core` together and keeping consumer logic (glossary_builder, dependency_matcher) in `fmm-cli`.

**Ordering**: Independent. Benefits from Phase 0 and Phase 1 as reference implementations.

**5-step incremental approach** (tests must pass at each step):

**Step 2a**: Create workspace structure. Virtual manifest with `fmm-core`, `fmm-parser`, `fmm-store`, `fmm-cli`. Workspace inheritance for version/edition/deps. Update to edition 2024, resolver 3.

**Step 2b**: Move pure types into `fmm-core`. From `parser/mod.rs`: `ExportEntry`, `Metadata`, `ParseResult`, `RegisteredLanguage`, `LanguageTestPatterns`, `Parser` trait. From `manifest/mod.rs`: `FileEntry`, `ExportLines`, `ExportLocation`, `Manifest` (including `rebuild_reverse_deps()`). Error types. No tree-sitter deps, no rusqlite. `Manifest`'s `impl From<Metadata> for FileEntry` moves with both types since they co-locate in core.

**Step 2c**: Move parser implementations into `fmm-parser`. All `builtin::*` modules (18 languages), `ParserRegistry`, `ParserFactory`, `register_language!` macro. This crate holds all 15 tree-sitter native deps. Depends on `fmm-core` for the `Parser` trait and output types.

**Step 2d**: Move `db/` into `fmm-store`. `reader.rs`, `writer.rs`, `mod.rs`. Define `FmmStore` trait in `fmm-core` (batch semantics), implement in `fmm-store`. Depends on `fmm-core` for types and trait.

**Step 2e**: Everything else becomes `fmm-cli`. cli, mcp, config, format, search, extractor (glossary_builder, dependency_matcher, call_site_finder, private_members), resolver. `main.rs` constructs `ParserRegistry::with_builtins()`, opens the store, loads the Manifest, dispatches commands. Depends on all three crates.

### Phase 3: nancyr Modernization — Lower Priority

**What to do**:
1. Update to edition 2024, resolver 3
2. Resolve `am-core`/`am-store` path dependency (publish to crates.io or document layout requirement)
3. Standardize justfile recipes

**Risk**: Low for edition/resolver. Medium for the dependency resolution (publishing requires stable API surface in am).

**Ordering**: Phase 0 must complete first (am API needs to be stable before nancyr depends on it).

### Phase 4: Ecosystem Standardization — Ongoing

1. Standardize justfile recipes across all projects: `check`, `build`, `test`, `fmt`, `clippy`, `install`
2. Extract CI templates into `helioy/github-actions` repo
3. Ensure all projects have `[profile.release]` with lto, codegen-units=1, strip, opt-level=3

## 10. Open Questions and Risks

### 10.1 Open Questions

**Q1: Should `ContextStore` use an associated error type?**
Currently uses concrete `CmError`. This works because cm has a single store backend. If a second backend (HTTP proxy, in-memory test) is added, an associated error type would be cleaner. The proposal recommends keeping concrete for now and switching only if a second adapter materializes.
**Recommendation**: Keep concrete. The trait already has `CmError::Database(String)` as an escape hatch for adapter-specific errors.

**Q2: When should nancyr's am-core/am-store dependency go through crates.io?**
Option 1 (crates.io) requires stable am API and publish discipline. Option 3 (documented path dep) is acceptable during active development.
**Recommendation**: Path dependency with documentation until am hits 1.0 or nancyr goes public.

**Q3: Should fmm-core's tree-sitter parsers live in core or a separate `fmm-parser` crate?** — **Resolved.**
Tree-sitter grammars are large native dependencies (~15 crates). Architect and rust engineer agree: `fmm-parser` crate. Core holds the `Parser` trait and output types (zero tree-sitter deps). Parser crate holds `ParserRegistry`, all `builtin::*` implementations, and the `register_language!` macro. `ParserRegistry` cannot be in core because it holds `ParserFactory` closures that construct concrete parser instances.

**Q4: markdown-matters Rust migration timing?**
The proposal outlines a phased migration. The TypeScript version works. Migration should be demand-driven (performance bottleneck or feature that benefits from Rust), not architecture-driven.
**Recommendation**: Defer. Revisit when indexing performance becomes a bottleneck.

### 10.2 Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| fmm workspace split surfaces hidden coupling | Medium | Medium | Incremental approach (Phase 2 steps a-d). Keep tests passing at each step. |
| ALP-1468 merge conflicts with main | Low | Low | Branch is 19 commits ahead, main has 0 divergent commits since fork point. |
| tree-sitter grammar version churn during fmm split | Low | Medium | Pin exact versions in workspace deps. Test with `cargo update --dry-run` before bumping. |
| nancyr am-store path dependency breaks on am API changes | High | Low | nancyr is lower priority. Path dep is documented. Breaking changes require manual nancyr update. |

### 10.3 Decisions Not Yet Made

- **Shared CI workflow extraction**: The proposal recommends `helioy/github-actions`. Not specified whether to use reusable workflows or composite actions. Decision deferred to Phase 4.
- **Binary distribution**: cargo-dist vs npm wrappers vs manual GitHub releases. Deferred until projects are ready for public distribution.
- **Observability**: Tracing spans and metrics for MCP tool handlers. Not covered in this spec. Each project currently logs to stderr via `tracing-subscriber`.
