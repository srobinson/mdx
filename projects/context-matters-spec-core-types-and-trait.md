---
title: "context-matters: Core Types and ContextStore Trait Specification"
type: project
tags: [context-matters, rust, types, trait, helioy]
status: draft
created: 2026-03-14
updated: 2026-03-14
---

## 1. Overview

This document specifies every Rust type and the `ContextStore` trait for context-matters. All types live in `cm-core` (zero I/O, zero async). The trait uses synchronous method signatures. cm-store's async API wraps these internally.

Foundation documents (approved, not revisited):
- Schema and Storage Layer Specification (DDL, scope paths, hashing, concurrency)
- Project Scaffold and Plugin Integration Spec (crate layout, dependencies)

## 2. File to Type Mapping

| File | Types |
|---|---|
| `cm-core/src/types.rs` | `Entry`, `NewEntry`, `UpdateEntry`, `EntryKind`, `ScopePath`, `ScopeKind`, `Scope`, `NewScope`, `EntryMeta`, `Confidence`, `EntryRelation`, `RelationKind`, `EntryFilter`, `PaginationCursor`, `Pagination`, `PagedResult`, `StoreStats` |
| `cm-core/src/error.rs` | `CmError`, `ScopePathError` |
| `cm-core/src/store.rs` | `ContextStore` trait |
| `cm-core/src/query.rs` | `QueryBuilder`, `FtsQuery` |
| `cm-core/src/lib.rs` | Re-exports all public types |

## 3. Type Definitions

### 3.1 EntryKind

```rust
use serde::{Deserialize, Serialize};

/// Classification of a context entry.
///
/// Each kind carries distinct semantic weight during recall.
/// `Feedback` entries receive highest priority
/// because they represent direct user corrections.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum EntryKind {
    Fact,
    Decision,
    Preference,
    Lesson,
    Reference,
    Feedback,
    Pattern,
    Observation,
}

impl EntryKind {
    /// Return the string representation used in SQL storage.
    pub fn as_str(&self) -> &'static str {
        match self {
            Self::Fact => "fact",
            Self::Decision => "decision",
            Self::Preference => "preference",
            Self::Lesson => "lesson",
            Self::Reference => "reference",
            Self::Feedback => "feedback",
            Self::Pattern => "pattern",
            Self::Observation => "observation",
        }
    }
}

impl std::fmt::Display for EntryKind {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str(self.as_str())
    }
}

impl std::str::FromStr for EntryKind {
    type Err = CmError;

    fn from_str(s: &str) -> Result<Self, Self::Err> {
        match s {
            "fact" => Ok(Self::Fact),
            "decision" => Ok(Self::Decision),
            "preference" => Ok(Self::Preference),
            "lesson" => Ok(Self::Lesson),
            "reference" => Ok(Self::Reference),
            "feedback" => Ok(Self::Feedback),
            "pattern" => Ok(Self::Pattern),
            "observation" => Ok(Self::Observation),
            other => Err(CmError::InvalidEntryKind(other.to_string())),
        }
    }
}
```

### 3.2 ScopeKind

```rust
/// The four levels of the scope hierarchy.
///
/// Ordering is significant: scopes must appear in hierarchical order
/// within a path (global < project < repo < session).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum ScopeKind {
    Global = 0,
    Project = 1,
    Repo = 2,
    Session = 3,
}

impl ScopeKind {
    pub fn as_str(&self) -> &'static str {
        match self {
            Self::Global => "global",
            Self::Project => "project",
            Self::Repo => "repo",
            Self::Session => "session",
        }
    }
}

impl std::fmt::Display for ScopeKind {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str(self.as_str())
    }
}

impl std::str::FromStr for ScopeKind {
    type Err = ScopePathError;

    fn from_str(s: &str) -> Result<Self, Self::Err> {
        match s {
            "global" => Ok(Self::Global),
            "project" => Ok(Self::Project),
            "repo" => Ok(Self::Repo),
            "session" => Ok(Self::Session),
            other => Err(ScopePathError::InvalidKind(other.to_string())),
        }
    }
}
```

### 3.3 ScopePath

```rust
/// A validated, immutable scope path.
///
/// Invariants enforced at construction time:
/// - Starts with "global"
/// - Each segment after global follows `kind:identifier` format
/// - Kinds appear in ascending hierarchical order (global < project < repo < session)
/// - Each kind appears at most once
/// - Intermediate levels may be omitted (e.g., `global/project:x/session:y` is valid)
/// - Identifiers match `[a-z0-9]([a-z0-9-]*[a-z0-9])?`
/// - Total path length <= 256 bytes
///
/// # Examples
///
/// ```
/// use cm_core::ScopePath;
///
/// let path = ScopePath::parse("global/project:helioy/repo:nancyr").unwrap();
/// assert_eq!(path.leaf_kind(), ScopeKind::Repo);
/// assert_eq!(
///     path.ancestors().collect::<Vec<_>>(),
///     vec![
///         "global/project:helioy/repo:nancyr",
///         "global/project:helioy",
///         "global",
///     ]
/// );
/// ```
#[derive(Debug, Clone, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(try_from = "String", into = "String")]
pub struct ScopePath(String);

/// Maximum byte length of a scope path.
const MAX_SCOPE_PATH_LEN: usize = 256;

/// Regex pattern for scope identifiers.
/// Matches: single alphanumeric char, or alphanumeric start/end with hyphens allowed in between.
/// Validated procedurally rather than with regex to avoid the dependency.
fn is_valid_identifier(s: &str) -> bool {
    if s.is_empty() {
        return false;
    }
    let bytes = s.as_bytes();
    // First and last must be alphanumeric
    if !bytes[0].is_ascii_lowercase() && !bytes[0].is_ascii_digit() {
        return false;
    }
    if !bytes[bytes.len() - 1].is_ascii_lowercase() && !bytes[bytes.len() - 1].is_ascii_digit() {
        return false;
    }
    // Interior: lowercase alphanumeric or hyphen
    bytes.iter().all(|b| b.is_ascii_lowercase() || b.is_ascii_digit() || *b == b'-')
}

impl ScopePath {
    /// Parse and validate a scope path string.
    ///
    /// Returns `Err(ScopePathError)` if any invariant is violated.
    pub fn parse(input: &str) -> Result<Self, ScopePathError> {
        if input.is_empty() {
            return Err(ScopePathError::Empty);
        }
        if input.len() > MAX_SCOPE_PATH_LEN {
            return Err(ScopePathError::TooLong {
                len: input.len(),
                max: MAX_SCOPE_PATH_LEN,
            });
        }

        let segments: Vec<&str> = input.split('/').collect();

        if segments[0] != "global" {
            return Err(ScopePathError::MissingGlobalRoot);
        }

        let mut prev_kind = ScopeKind::Global;

        for segment in &segments[1..] {
            let (kind_str, id) = segment
                .split_once(':')
                .ok_or_else(|| ScopePathError::MalformedSegment((*segment).to_string()))?;

            let kind: ScopeKind = kind_str.parse()?;

            if kind <= prev_kind {
                return Err(ScopePathError::OutOfOrder {
                    got: kind.as_str().to_string(),
                    after: prev_kind.as_str().to_string(),
                });
            }

            if !is_valid_identifier(id) {
                return Err(ScopePathError::InvalidIdentifier(id.to_string()));
            }

            prev_kind = kind;
        }

        Ok(Self(input.to_string()))
    }

    /// The root scope. Always valid.
    pub fn global() -> Self {
        Self("global".to_string())
    }

    /// Return the raw path string.
    pub fn as_str(&self) -> &str {
        &self.0
    }

    /// Return all ancestor paths from most specific to least specific.
    ///
    /// The path itself is included as the first element.
    /// The last element is always `"global"`.
    pub fn ancestors(&self) -> impl Iterator<Item = &str> {
        let s = self.0.as_str();
        let mut positions = vec![s.len()];
        for (i, b) in s.bytes().enumerate() {
            if b == b'/' {
                positions.push(i);
            }
        }
        // Reverse so most specific comes first, but we need the slash positions
        // in reverse order after the full length
        let mut result: Vec<&str> = Vec::with_capacity(positions.len());
        // Full path first
        result.push(s);
        // Then progressively shorter prefixes
        // positions contains: [full_len, slash_pos_1, slash_pos_2, ...]
        // We want: s[..slash_pos_last], s[..slash_pos_second_last], ...
        for &pos in positions[1..].iter().rev() {
            result.push(&s[..pos]);
        }
        result.into_iter()
    }

    /// Return the scope kind of the deepest (rightmost) segment.
    pub fn leaf_kind(&self) -> ScopeKind {
        if self.0 == "global" {
            return ScopeKind::Global;
        }
        // The last segment is after the last '/'
        let last_segment = self.0.rsplit('/').next().unwrap();
        let kind_str = last_segment.split(':').next().unwrap();
        kind_str.parse().unwrap() // Safe: validated at construction
    }

    /// Return the depth of the scope path.
    /// `"global"` has depth 1, `"global/project:x"` has depth 2, etc.
    pub fn depth(&self) -> usize {
        self.0.split('/').count()
    }
}

impl std::fmt::Display for ScopePath {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str(&self.0)
    }
}

impl std::str::FromStr for ScopePath {
    type Err = ScopePathError;

    fn from_str(s: &str) -> Result<Self, Self::Err> {
        Self::parse(s)
    }
}

impl TryFrom<String> for ScopePath {
    type Error = ScopePathError;

    fn try_from(s: String) -> Result<Self, Self::Error> {
        Self::parse(&s)
    }
}

impl From<ScopePath> for String {
    fn from(sp: ScopePath) -> Self {
        sp.0
    }
}

impl AsRef<str> for ScopePath {
    fn as_ref(&self) -> &str {
        &self.0
    }
}
```

### 3.4 Confidence

```rust
/// Confidence level for a context entry.
///
/// Stored in the `meta` JSONB column. Affects recall priority:
/// `High` entries surface before `Low` entries at the same scope level.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Confidence {
    High,
    Medium,
    Low,
}
```

### 3.5 EntryMeta

```rust
use std::collections::HashMap;
use serde_json::Value;

/// Structured metadata stored in the JSONB `meta` column.
///
/// The `extra` field captures any additional keys present in the JSON
/// that are not part of the known schema, providing forward-compatible
/// extensibility without schema changes.
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct EntryMeta {
    /// Freeform tags for categorization and filtering.
    #[serde(default, skip_serializing_if = "Vec::is_empty")]
    pub tags: Vec<String>,

    /// Confidence level. Affects recall priority ordering.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub confidence: Option<Confidence>,

    /// Attribution or provenance string (URL, file path, agent name).
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub source: Option<String>,

    /// ISO 8601 timestamp after which this entry is considered stale.
    /// The storage layer stores this value but does not enforce expiry.
    /// Expiry semantics are defined in the MCP tool layer.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub expires_at: Option<chrono::DateTime<chrono::Utc>>,

    /// Numeric priority for manual ordering. Higher values surface first.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub priority: Option<i32>,

    /// Forward-compatible extension fields.
    #[serde(flatten)]
    pub extra: HashMap<String, Value>,
}
```

### 3.6 Entry

```rust
use chrono::{DateTime, Utc};
use uuid::Uuid;

/// A complete context entry as stored in the database.
///
/// This type represents a row from the `entries` table with all columns populated.
/// Construct new entries via `NewEntry`; the store assigns `id`, `content_hash`,
/// `created_at`, `updated_at`, and `superseded_by`.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Entry {
    /// UUIDv7 identifier. Time-sortable, stored as lowercase hex TEXT.
    /// Requires uuid crate ≥1.9.0 for proper v7 monotonicity counters
    /// (earlier versions lack within-millisecond ordering guarantees).
    pub id: Uuid,

    /// Scope this entry belongs to. FK to `scopes.path`.
    pub scope_path: ScopePath,

    /// Classification of the entry.
    pub kind: EntryKind,

    /// Short summary for search results and progressive disclosure.
    pub title: String,

    /// Markdown content body.
    pub body: String,

    /// BLAKE3 hex digest of `scope_path + \0 + kind + \0 + body`.
    /// Used for deduplication. 64 lowercase hex characters.
    pub content_hash: String,

    /// Structured metadata (tags, confidence, source, expiry, priority).
    /// `None` when the database column is NULL.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub meta: Option<EntryMeta>,

    /// Attribution string in `source_type:identifier` format.
    /// Examples: `human:stuart`, `agent:claude-code`, `system:consolidation`.
    pub created_by: String,

    /// Timestamp of entry creation.
    pub created_at: DateTime<Utc>,

    /// Timestamp of last modification. Maintained by database trigger.
    pub updated_at: DateTime<Utc>,

    /// If set, this entry has been superseded by the referenced entry.
    /// A non-null value means this entry is inactive.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub superseded_by: Option<Uuid>,
}
```

### 3.7 NewEntry

```rust
/// Input for creating a new context entry.
///
/// The caller provides scope, kind, title, body, created_by, and optional metadata.
/// The store generates `id` (UUIDv7), `content_hash` (BLAKE3), and timestamps.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NewEntry {
    /// Target scope path. Must reference an existing scope.
    pub scope_path: ScopePath,

    /// Classification.
    pub kind: EntryKind,

    /// Short summary.
    pub title: String,

    /// Markdown content body.
    pub body: String,

    /// Attribution string (`source_type:identifier`).
    pub created_by: String,

    /// Optional structured metadata.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub meta: Option<EntryMeta>,
}

impl NewEntry {
    /// Compute the BLAKE3 content hash for deduplication.
    ///
    /// Hash input: `scope_path + \0 + kind + \0 + body`
    /// Returns lowercase hex string (64 chars).
    pub fn content_hash(&self) -> String {
        let mut hasher = blake3::Hasher::new();
        hasher.update(self.scope_path.as_str().as_bytes());
        hasher.update(b"\0");
        hasher.update(self.kind.as_str().as_bytes());
        hasher.update(b"\0");
        hasher.update(self.body.as_bytes());
        hasher.finalize().to_hex().to_string()
    }
}
```

### 3.8 UpdateEntry

```rust
/// Partial update to an existing entry.
///
/// Only fields set to `Some` are applied. `None` fields remain unchanged.
/// The `content_hash` is recomputed by the store if `body` or `kind` changes.
///
/// Scope migration (changing `scope_path`) is intentionally excluded.
/// Moving an entry to a different scope changes its content hash and may
/// violate FK constraints. Use `supersede_entry` to create a replacement
/// at the target scope instead.
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct UpdateEntry {
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub title: Option<String>,

    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub body: Option<String>,

    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub kind: Option<EntryKind>,

    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub meta: Option<EntryMeta>,
}
```

### 3.9 Scope

```rust
/// A row from the `scopes` table.
///
/// Scopes define the hierarchy that entries belong to.
/// They must be created top-down: a scope's `parent_path`
/// must already exist before the scope can be created.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Scope {
    /// The full scope path, which is also the primary key.
    pub path: ScopePath,

    /// The kind of this scope's leaf segment.
    pub kind: ScopeKind,

    /// Human-readable label for this scope.
    pub label: String,

    /// Parent scope path. `None` for the root (`global`).
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub parent_path: Option<ScopePath>,

    /// Optional JSONB metadata.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub meta: Option<serde_json::Value>,

    /// Timestamp of scope creation.
    pub created_at: DateTime<Utc>,
}
```

### 3.10 NewScope

```rust
/// Input for creating a new scope.
///
/// The `path` must be valid per `ScopePath` rules. If `parent_path` is
/// `Some`, the referenced scope must already exist.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NewScope {
    /// Full scope path (becomes the primary key).
    pub path: ScopePath,

    /// Human-readable label.
    pub label: String,

    /// Optional JSONB metadata.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub meta: Option<serde_json::Value>,
}

impl NewScope {
    /// Derive `kind` from the leaf segment of the path.
    pub fn kind(&self) -> ScopeKind {
        self.path.leaf_kind()
    }

    /// Derive `parent_path` by removing the last segment.
    /// Returns `None` for the `global` root scope.
    pub fn parent_path(&self) -> Option<ScopePath> {
        let s = self.path.as_str();
        if s == "global" {
            return None;
        }
        let parent = &s[..s.rfind('/').unwrap()];
        Some(ScopePath::parse(parent).unwrap()) // Safe: parent of a valid path is valid
    }
}
```

### 3.11 RelationKind

```rust
/// The kind of relationship between two entries.
///
/// Relations are directional: `source_id` has this relationship
/// to `target_id`. The composite primary key is
/// `(source_id, target_id, relation)`, allowing multiple
/// distinct relation types between the same pair.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum RelationKind {
    /// Source replaces target (target should have `superseded_by` set).
    Supersedes,
    /// Entries are topically related.
    RelatesTo,
    /// Source contradicts target. Signals a conflict for review.
    Contradicts,
    /// Source provides additional detail for target.
    Elaborates,
    /// Source depends on target being true or present.
    DependsOn,
}

impl RelationKind {
    pub fn as_str(&self) -> &'static str {
        match self {
            Self::Supersedes => "supersedes",
            Self::RelatesTo => "relates_to",
            Self::Contradicts => "contradicts",
            Self::Elaborates => "elaborates",
            Self::DependsOn => "depends_on",
        }
    }
}

impl std::fmt::Display for RelationKind {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str(self.as_str())
    }
}

impl std::str::FromStr for RelationKind {
    type Err = CmError;

    fn from_str(s: &str) -> Result<Self, Self::Err> {
        match s {
            "supersedes" => Ok(Self::Supersedes),
            "relates_to" => Ok(Self::RelatesTo),
            "contradicts" => Ok(Self::Contradicts),
            "elaborates" => Ok(Self::Elaborates),
            "depends_on" => Ok(Self::DependsOn),
            other => Err(CmError::InvalidRelationKind(other.to_string())),
        }
    }
}
```

### 3.12 EntryRelation

```rust
/// A directional relationship between two entries.
///
/// Corresponds to a row in the `entry_relations` table.
/// Relations cascade-delete when either entry is removed.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EntryRelation {
    pub source_id: Uuid,
    pub target_id: Uuid,
    pub relation: RelationKind,
    pub created_at: DateTime<Utc>,
}
```

### 3.13 EntryFilter

```rust
/// Query parameters for browsing and filtering entries.
///
/// All fields are optional. When multiple fields are set,
/// they combine with AND semantics. An empty filter returns
/// all active entries (where `superseded_by IS NULL`).
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct EntryFilter {
    /// Filter to a specific scope path (exact match, no ancestor walk).
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub scope_path: Option<ScopePath>,

    /// Filter by entry kind.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub kind: Option<EntryKind>,

    /// Filter by tag (entry must have at least one matching tag).
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub tag: Option<String>,

    /// Filter by created_by attribution.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub created_by: Option<String>,

    /// If true, include superseded (inactive) entries. Default: false.
    #[serde(default)]
    pub include_superseded: bool,

    /// Pagination parameters.
    #[serde(default)]
    pub pagination: Pagination,
}
```

### 3.14 PaginationCursor

```rust
/// Composite cursor for deterministic pagination.
///
/// Uses `(updated_at, id)` to avoid skipping entries when multiple
/// entries share the same `updated_at` timestamp (e.g., batch imports
/// or trigger-driven updates within a single transaction).
///
/// SQLite supports tuple comparison: `WHERE (updated_at, id) < (?, ?)`.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PaginationCursor {
    pub updated_at: DateTime<Utc>,
    pub id: Uuid,
}
```

### 3.15 Pagination

```rust
/// Cursor-based pagination using `(updated_at, id)` ordering.
///
/// Results are ordered by `updated_at DESC, id DESC` (most recently
/// modified first, with UUID tiebreaker for deterministic ordering).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Pagination {
    /// Maximum number of entries to return.
    pub limit: u32,

    /// Cursor for the next page.
    /// Entries with `(updated_at, id) < (cursor.updated_at, cursor.id)` are returned.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub cursor: Option<PaginationCursor>,
}

impl Default for Pagination {
    fn default() -> Self {
        Self {
            limit: 50,
            cursor: None,
        }
    }
}
```

### 3.16 PagedResult

```rust
/// A paginated result set.
///
/// If `next_cursor` is `Some`, more results are available.
/// Pass it as `pagination.cursor` on the next request.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PagedResult<T> {
    /// The items on this page.
    pub items: Vec<T>,

    /// Total count of matching entries (across all pages).
    pub total: u64,

    /// Cursor for the next page, if more results exist.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub next_cursor: Option<PaginationCursor>,
}
```

### 3.17 StoreStats

```rust
/// Aggregate statistics about the context store.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct StoreStats {
    /// Total number of active entries (superseded_by IS NULL).
    pub active_entries: u64,

    /// Total number of superseded entries.
    pub superseded_entries: u64,

    /// Number of scopes.
    pub scopes: u64,

    /// Number of relations.
    pub relations: u64,

    /// Breakdown of active entries by kind.
    pub entries_by_kind: HashMap<EntryKind, u64>,

    /// Breakdown of active entries by scope path.
    pub entries_by_scope: HashMap<String, u64>,

    /// Database file size in bytes (0 for in-memory databases).
    pub db_size_bytes: u64,
}

use std::collections::HashMap;
```

## 4. Error Types

### 4.1 CmError

```rust
use thiserror::Error;
use uuid::Uuid;

/// Top-level error type for context-matters operations.
///
/// All `ContextStore` methods return `Result<T, CmError>`.
/// Each variant maps to a distinct failure mode with enough
/// context for the caller to construct a meaningful error response.
#[derive(Debug, Error)]
pub enum CmError {
    /// The requested entry does not exist.
    #[error("entry not found: {0}")]
    EntryNotFound(Uuid),

    /// The requested scope does not exist.
    #[error("scope not found: {0}")]
    ScopeNotFound(String),

    /// An entry with the same content hash already exists (active, not superseded).
    /// The `Uuid` is the ID of the existing duplicate.
    #[error("duplicate content: existing entry {0}")]
    DuplicateContent(Uuid),

    /// Scope path validation failed.
    #[error("invalid scope path: {0}")]
    InvalidScopePath(#[from] ScopePathError),

    /// An invalid entry kind string was provided.
    #[error("invalid entry kind: {0}")]
    InvalidEntryKind(String),

    /// An invalid relation kind string was provided.
    #[error("invalid relation kind: {0}")]
    InvalidRelationKind(String),

    /// A field validation check failed.
    #[error("validation error: {0}")]
    Validation(String),

    /// Foreign key constraint violation (e.g., scope has entries, cannot delete).
    #[error("constraint violation: {0}")]
    ConstraintViolation(String),

    /// JSON serialization or deserialization failed.
    #[error("json error: {0}")]
    Json(#[from] serde_json::Error),

    /// Database error from the storage backend.
    #[error("database error: {0}")]
    Database(String),

    /// An internal error that should not occur during normal operation.
    #[error("internal error: {0}")]
    Internal(String),
}
```

### 4.2 ScopePathError

```rust
/// Errors specific to scope path parsing and validation.
///
/// Separated from `CmError` because scope path validation is a pure
/// operation (no I/O) and can be tested independently of the store.
#[derive(Debug, Error)]
pub enum ScopePathError {
    /// The input string is empty.
    #[error("scope path cannot be empty")]
    Empty,

    /// The path exceeds the maximum length.
    #[error("scope path too long: {len} bytes (max {max})")]
    TooLong { len: usize, max: usize },

    /// The path does not start with "global".
    #[error("scope path must start with 'global'")]
    MissingGlobalRoot,

    /// A segment does not follow the `kind:identifier` format.
    #[error("malformed segment: '{0}' (expected 'kind:identifier')")]
    MalformedSegment(String),

    /// A scope kind is not recognized.
    #[error("invalid scope kind: '{0}' (expected global, project, repo, or session)")]
    InvalidKind(String),

    /// Scope kinds are not in ascending hierarchical order.
    #[error("scope kind '{got}' cannot appear after '{after}'")]
    OutOfOrder { got: String, after: String },

    /// An identifier contains invalid characters.
    #[error("invalid identifier: '{0}' (must match [a-z0-9][a-z0-9-]*[a-z0-9])")]
    InvalidIdentifier(String),
}
```

## 5. ContextStore Trait

```rust
use uuid::Uuid;

/// Synchronous storage interface for context entries.
///
/// All methods return `Result<T, CmError>`. The trait uses synchronous
/// signatures because cm-core has zero async dependencies. The adapter
/// crate (cm-store) wraps these in async methods using sqlx's internal
/// thread pool. A future rusqlite adapter would use
/// `tokio::task::spawn_blocking`.
///
/// ## Conventions
///
/// - Methods that query entries exclude superseded entries by default
///   unless the caller explicitly opts in via `EntryFilter::include_superseded`.
/// - Write methods (`create_entry`, `update_entry`, `supersede_entry`, `forget_entry`)
///   use the write pool (1 connection). Read methods use the read pool (4 connections).
/// - All IDs are UUIDv7, generated by the store on creation.
pub trait ContextStore {
    // ── Entry CRUD ──────────────────────────────────────────────

    /// Create a new entry.
    ///
    /// Generates a UUIDv7 `id`, computes the BLAKE3 `content_hash`,
    /// and sets `created_at` and `updated_at` to the current timestamp.
    ///
    /// # Errors
    ///
    /// - `CmError::ScopeNotFound` if `new_entry.scope_path` does not exist in `scopes`.
    /// - `CmError::DuplicateContent` if an active entry with the same content hash exists.
    /// - `CmError::Validation` if title or body is empty.
    fn create_entry(&self, new_entry: NewEntry) -> Result<Entry, CmError>;

    /// Retrieve a single entry by ID.
    ///
    /// Returns the entry regardless of superseded status.
    ///
    /// # Errors
    ///
    /// - `CmError::EntryNotFound` if no entry with this ID exists.
    fn get_entry(&self, id: Uuid) -> Result<Entry, CmError>;

    /// Retrieve multiple entries by IDs.
    ///
    /// Returns entries in the same order as the input IDs.
    /// Missing IDs are silently omitted from the result (no error).
    /// Returns entries regardless of superseded status.
    fn get_entries(&self, ids: &[Uuid]) -> Result<Vec<Entry>, CmError>;

    /// Resolve context for a scope by walking up the hierarchy.
    ///
    /// Returns all active entries from the target scope and every
    /// ancestor scope, ordered by:
    /// 1. Scope depth (most specific first)
    /// 2. `updated_at` DESC within each scope level
    ///
    /// This is the primary recall method. MCP tools call this to gather
    /// all relevant context for a given working scope.
    ///
    /// # Arguments
    ///
    /// - `scope_path`: The target scope to resolve from.
    /// - `kinds`: Optional filter to specific entry kinds. If empty, all kinds are included.
    /// - `limit`: Maximum total entries to return across all scope levels.
    fn resolve_context(
        &self,
        scope_path: &ScopePath,
        kinds: &[EntryKind],
        limit: u32,
    ) -> Result<Vec<Entry>, CmError>;

    /// Full-text search using FTS5.
    ///
    /// Searches `title` and `body` fields using SQLite FTS5 `MATCH` syntax.
    /// Results are ranked by FTS5 relevance score.
    ///
    /// # Arguments
    ///
    /// - `query`: FTS5 query string. Supports prefix queries (`rust*`),
    ///   phrase queries (`"scope path"`), and boolean operators (`AND`, `OR`, `NOT`).
    /// - `scope_path`: Optional scope filter. When set, only entries at this
    ///   exact scope or its ancestors are included. This follows the scope
    ///   resolution pattern: context from broader scopes is always visible
    ///   at narrower scopes. This is not a descendant search.
    /// - `limit`: Maximum number of results.
    fn search(
        &self,
        query: &str,
        scope_path: Option<&ScopePath>,
        limit: u32,
    ) -> Result<Vec<Entry>, CmError>;

    /// Browse entries with filtering and pagination.
    ///
    /// Applies all filter criteria with AND semantics.
    /// Returns a paginated result set ordered by `updated_at DESC`.
    fn browse(&self, filter: EntryFilter) -> Result<PagedResult<Entry>, CmError>;

    /// Partially update an existing entry.
    ///
    /// Only fields set to `Some` in `update` are modified.
    /// If `body` or `kind` changes, the `content_hash` is recomputed
    /// and checked for duplicates.
    /// `updated_at` is refreshed by the database trigger.
    ///
    /// # Errors
    ///
    /// - `CmError::EntryNotFound` if the entry does not exist.
    /// - `CmError::DuplicateContent` if the updated content hash matches another active entry.
    fn update_entry(&self, id: Uuid, update: UpdateEntry) -> Result<Entry, CmError>;

    /// Supersede an entry: soft-delete the old entry and create a replacement.
    ///
    /// Sets `superseded_by` on `old_id` to the new entry's ID.
    /// Creates a `Supersedes` relation from the new entry to the old entry.
    /// Executed as a single transaction.
    ///
    /// # Errors
    ///
    /// - `CmError::EntryNotFound` if `old_id` does not exist.
    /// - `CmError::DuplicateContent` if the new entry's content hash matches another active entry.
    fn supersede_entry(&self, old_id: Uuid, new_entry: NewEntry) -> Result<Entry, CmError>;

    /// Soft-delete an entry by marking it as forgotten.
    ///
    /// Sets `superseded_by` to the entry's own ID (self-referential),
    /// distinguishing a "forgotten" entry from one superseded by a replacement.
    ///
    /// # Errors
    ///
    /// - `CmError::EntryNotFound` if the entry does not exist.
    fn forget_entry(&self, id: Uuid) -> Result<(), CmError>;

    // ── Relations ───────────────────────────────────────────────

    /// Create a relation between two entries.
    ///
    /// # Errors
    ///
    /// - `CmError::EntryNotFound` if either `source_id` or `target_id` does not exist.
    /// - `CmError::ConstraintViolation` if the relation already exists.
    fn create_relation(
        &self,
        source_id: Uuid,
        target_id: Uuid,
        relation: RelationKind,
    ) -> Result<EntryRelation, CmError>;

    /// Get all relations where the given entry is the source.
    fn get_relations_from(&self, source_id: Uuid) -> Result<Vec<EntryRelation>, CmError>;

    /// Get all relations where the given entry is the target.
    fn get_relations_to(&self, target_id: Uuid) -> Result<Vec<EntryRelation>, CmError>;

    // ── Scopes ──────────────────────────────────────────────────

    /// Create a new scope.
    ///
    /// Derives `kind` and `parent_path` from the scope path.
    /// The parent scope must already exist (except for `global`).
    ///
    /// # Errors
    ///
    /// - `CmError::ScopeNotFound` if the parent scope does not exist.
    /// - `CmError::ConstraintViolation` if the scope already exists.
    fn create_scope(&self, new_scope: NewScope) -> Result<Scope, CmError>;

    /// Retrieve a scope by its path.
    ///
    /// # Errors
    ///
    /// - `CmError::ScopeNotFound` if no scope with this path exists.
    fn get_scope(&self, path: &ScopePath) -> Result<Scope, CmError>;

    /// List all scopes, optionally filtered by kind.
    fn list_scopes(&self, kind: Option<ScopeKind>) -> Result<Vec<Scope>, CmError>;

    // ── Aggregation ─────────────────────────────────────────────

    /// Return aggregate statistics about the store.
    fn stats(&self) -> Result<StoreStats, CmError>;

    /// Export all active entries, optionally filtered by scope.
    ///
    /// Returns entries ordered by `scope_path ASC`, `created_at ASC`.
    /// Superseded entries are excluded.
    fn export(&self, scope_path: Option<&ScopePath>) -> Result<Vec<Entry>, CmError>;
}
```

## 6. Content Hash Implementation

The `NewEntry::content_hash()` method (Section 3.7) is the single source of truth for hash computation. The store calls this method during `create_entry` and `supersede_entry`, and recomputes it during `update_entry` when any of the three hash inputs change.

Hash input format:
```
BLAKE3(scope_path_string + \0 + kind_string + \0 + body_string)
```

The title is excluded. Two entries with the same scope, kind, and body but different titles are considered duplicates.

The resulting hash is a 64-character lowercase hexadecimal string stored in the `content_hash` TEXT column.

## 7. lib.rs Re-exports

```rust
//! Domain types and traits for the context-matters store.
//!
//! This crate defines the core abstractions with zero I/O dependencies.
//! The `ContextStore` trait uses synchronous method signatures.
//! Storage adapters (cm-store) wrap these in async where needed.

mod error;
mod query;
mod store;
mod types;

pub use error::{CmError, ScopePathError};
pub use store::ContextStore;
pub use types::{
    Confidence, Entry, EntryFilter, EntryKind, EntryMeta, EntryRelation,
    NewEntry, NewScope, PagedResult, Pagination, PaginationCursor,
    RelationKind, Scope, ScopeKind, ScopePath, StoreStats, UpdateEntry,
};
```

## 8. Acceptance Criteria

### 8.1 Type Construction and Validation

1. `ScopePath::parse("global")` returns `Ok` with `leaf_kind() == ScopeKind::Global` and `depth() == 1`.
2. `ScopePath::parse("global/project:helioy/repo:nancyr")` returns `Ok` with `leaf_kind() == ScopeKind::Repo`.
3. `ScopePath::parse("global/project:helioy/session:deploy-review")` returns `Ok` (skipped hierarchy level is valid).
4. `ScopePath::parse("project:helioy")` returns `Err(ScopePathError::MissingGlobalRoot)`.
5. `ScopePath::parse("global/workspace:foo")` returns `Err(ScopePathError::InvalidKind(_))`.
6. `ScopePath::parse("")` returns `Err(ScopePathError::Empty)`.
7. `ScopePath::parse("global/repo:x/project:y")` returns `Err(ScopePathError::OutOfOrder { .. })` (repo before project).
8. `ScopePath::parse("global/project:UPPER")` returns `Err(ScopePathError::InvalidIdentifier(_))`.
9. `ScopePath::parse(&"x".repeat(257))` returns `Err(ScopePathError::TooLong { .. })`.

### 8.2 Ancestor Traversal

10. `ScopePath::parse("global/project:helioy/repo:nancyr").unwrap().ancestors()` yields `["global/project:helioy/repo:nancyr", "global/project:helioy", "global"]`.
11. `ScopePath::global().ancestors()` yields `["global"]`.

### 8.3 Content Hashing

12. Two `NewEntry` values with the same `scope_path`, `kind`, and `body` but different `title` produce identical `content_hash()` output.
13. Changing the `body` produces a different hash.
14. Changing the `scope_path` produces a different hash.
15. Changing the `kind` produces a different hash.
16. The hash output is exactly 64 lowercase hex characters.

### 8.4 NewScope Derivation

17. `NewScope { path: "global/project:helioy", .. }.kind()` returns `ScopeKind::Project`.
18. `NewScope { path: "global/project:helioy", .. }.parent_path()` returns `Some(ScopePath("global"))`.
19. `NewScope { path: "global", .. }.parent_path()` returns `None`.

### 8.5 Serde Round-Trip

20. `EntryKind` serializes to/from lowercase snake_case strings.
21. `EntryMeta` with `extra` fields round-trips through JSON: unknown keys are preserved.
22. `ScopePath` serializes as a plain JSON string and deserializes via `TryFrom<String>`.
23. `Entry` with `meta: None` serializes without the `meta` key (via `skip_serializing_if`).

### 8.6 Error Formatting

24. `CmError::EntryNotFound(some_uuid).to_string()` produces `"entry not found: <uuid>"`.
25. `ScopePathError::OutOfOrder { got: "project", after: "repo" }.to_string()` produces `"scope kind 'project' cannot appear after 'repo'"`.

### 8.7 Trait Method Contracts

26. `create_entry` rejects empty title (returns `CmError::Validation`).
27. `create_entry` rejects empty body (returns `CmError::Validation`).
28. `create_entry` returns `CmError::DuplicateContent(existing_id)` when content hash matches an active entry.
29. `get_entries` with a mix of valid and invalid IDs returns only the valid entries, in input order.
30. `resolve_context` returns entries ordered by scope depth DESC, then `updated_at` DESC.
31. `supersede_entry` atomically sets `superseded_by` on the old entry and creates the new entry with a `Supersedes` relation.
32. `forget_entry` sets `superseded_by` to the entry's own ID.
33. `browse` with default `EntryFilter` excludes superseded entries.
34. `browse` with `include_superseded: true` includes superseded entries.
35. `export` excludes superseded entries and orders by scope_path ASC, created_at ASC.
