---
title: "cm-store Mutation History: Implementation Spec"
type: projects
tags: [context-matters, cm-store, mutations, audit-trail, spec]
summary: "Implementation spec for store-level mutation history in cm-store. Covers WriteContext, MutationRecord types, ContextStore trait changes, SQLite migration, implementation details, call-site inventory, and test plan."
status: draft
project: helioy
created: 2026-03-19
updated: 2026-03-19
---

# cm-store Mutation History: Implementation Spec

## Overview

Every entry mutation on the context store gets logged at the cm-store layer, regardless of caller. MCP tools, CLI commands, cm-web, and future Helix operations all produce mutation records. This is infrastructure, not a feature of any particular frontend.

**Scope of logging**: Entry lifecycle operations only (`create_entry`, `update_entry`, `supersede_entry`, `forget_entry`). Scope creation and relation creation are not logged. These are structural/relational operations without meaningful before/after state worth auditing at current scale. The `WriteContext` parameter is carried on all mutating methods for consistency, but only entry methods write mutation records.

The goal: a store-level audit trail for entry mutations that records what changed, when, and from what source. Callers pass provenance via a `WriteContext` struct. The store writes a `MutationRecord` in the same transaction as the mutation itself.

## 1. WriteContext Type (cm-core)

File: `crates/cm-core/src/types.rs`

```rust
/// Provenance context passed to every mutating ContextStore method.
///
/// Carries the originating source of a write operation. Extensible
/// for future fields (correlation_id, session_id, actor) without
/// breaking the trait signature.
#[derive(Debug, Clone)]
pub struct WriteContext {
    pub source: MutationSource,
}

impl WriteContext {
    pub fn new(source: MutationSource) -> Self {
        Self { source }
    }
}

/// Identifies where a write operation originated.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum MutationSource {
    /// MCP server tool handler (cx_store, cx_update, cx_forget, cx_deposit).
    Mcp,
    /// Direct CLI command.
    Cli,
    /// cm-web API handler.
    Web,
    /// Helix autonomous operations.
    Helix,
}

impl MutationSource {
    pub fn as_str(&self) -> &'static str {
        match self {
            Self::Mcp => "mcp",
            Self::Cli => "cli",
            Self::Web => "web",
            Self::Helix => "helix",
        }
    }
}

impl std::fmt::Display for MutationSource {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str(self.as_str())
    }
}

impl std::str::FromStr for MutationSource {
    type Err = CmError;

    fn from_str(s: &str) -> Result<Self, Self::Err> {
        match s {
            "mcp" => Ok(Self::Mcp),
            "cli" => Ok(Self::Cli),
            "web" => Ok(Self::Web),
            "helix" => Ok(Self::Helix),
            other => Err(CmError::Validation(
                format!("invalid mutation source: '{other}'"),
            )),
        }
    }
}
```

Re-export from `crates/cm-core/src/lib.rs`:

```rust
pub use types::{
    // ... existing exports ...
    MutationSource, WriteContext,
};
```

## 2. MutationRecord Type (cm-core)

File: `crates/cm-core/src/types.rs`

```rust
/// Classifies the kind of mutation performed on an entry.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum MutationAction {
    /// New entry created.
    Create,
    /// Existing entry fields updated.
    Update,
    /// Entry soft-deleted (superseded_by set to self).
    Forget,
    /// Entry superseded by a replacement entry.
    Supersede,
}

impl MutationAction {
    pub fn as_str(&self) -> &'static str {
        match self {
            Self::Create => "create",
            Self::Update => "update",
            Self::Forget => "forget",
            Self::Supersede => "supersede",
        }
    }
}

impl std::fmt::Display for MutationAction {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str(self.as_str())
    }
}

impl std::str::FromStr for MutationAction {
    type Err = CmError;

    fn from_str(s: &str) -> Result<Self, Self::Err> {
        match s {
            "create" => Ok(Self::Create),
            "update" => Ok(Self::Update),
            "forget" => Ok(Self::Forget),
            "supersede" => Ok(Self::Supersede),
            other => Err(CmError::Validation(
                format!("invalid mutation action: '{other}'"),
            )),
        }
    }
}

/// A recorded mutation on a context entry.
///
/// Written by cm-store in the same transaction as the write operation.
/// Snapshots are full JSON serializations of the `Entry` at that point in time.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MutationRecord {
    /// UUIDv7 identifier for this mutation record.
    pub id: uuid::Uuid,

    /// The entry that was mutated.
    pub entry_id: uuid::Uuid,

    /// What happened.
    pub action: MutationAction,

    /// Where the write originated.
    pub source: MutationSource,

    /// When the mutation occurred.
    pub timestamp: DateTime<Utc>,

    /// Full entry state before the mutation. `None` for `Create` (no prior state).
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub before_snapshot: Option<serde_json::Value>,

    /// Full entry state after the mutation. `None` only if the row was hard-deleted
    /// (which this system does not do). All four actions capture the post-state.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub after_snapshot: Option<serde_json::Value>,
}
```

Re-export from `crates/cm-core/src/lib.rs`:

```rust
pub use types::{
    // ... existing exports ...
    MutationAction, MutationRecord, MutationSource, WriteContext,
};
```

### Snapshot design

Full snapshots, not partial diffs. Rationale:

- **Simple**: `serde_json::to_value(&entry)?` at the right moment. No diffing logic in the write path.
- **Self-contained**: each mutation record is interpretable without fetching other records.
- **Client-side diffs**: cm-web computes diffs by comparing before/after JSON. The logic lives in the UI, not the store.
- **Storage cost**: at ~171 active entries and ~30 writes/day, snapshot overhead is negligible. A full entry serializes to ~500 bytes of JSON. Even at 1,000 mutations/month, that is under 500KB.

Snapshot semantics per action:

| Action | `before_snapshot` | `after_snapshot` |
|-----------|-------------------|------------------|
| `Create` | `None` | Full entry after insert |
| `Update` | Full entry before update | Full entry after update |
| `Forget` | Full entry before forget | Full entry after forget (with `superseded_by` = self) |
| `Supersede` | Full entry before supersession | Full entry after supersession (with `superseded_by` = new entry ID) |

Both `Forget` and `Supersede` preserve the post-state because the row still exists and the interesting change is precisely the `superseded_by` field being set. Recording the post-state makes diffs meaningful for all four actions. `after_snapshot` is `None` only if a row were hard-deleted, which this system does not do.

For `supersede_entry`, two mutation records are written:
1. `entry_id=old_id, action=Supersede`: before = entry without `superseded_by`, after = entry with `superseded_by` pointing to replacement.
2. `entry_id=new_id, action=Create`: before = `None`, after = the new replacement entry.

The link between them is explicit in the old entry's `after_snapshot`, which contains the `superseded_by` field pointing to the new entry's ID.

## 3. ContextStore Trait Changes (cm-core)

File: `crates/cm-core/src/store.rs`

Every mutating method gains a `ctx: &WriteContext` parameter. Read-only methods are unchanged.

**Entry methods** (write mutation records):

```rust
// BEFORE                                              // AFTER
async fn create_entry(                                 async fn create_entry(
    &self,                                                 &self,
    new_entry: NewEntry,                                   new_entry: NewEntry,
) -> Result<Entry, CmError>;                               ctx: &WriteContext,
                                                       ) -> Result<Entry, CmError>;

async fn update_entry(                                 async fn update_entry(
    &self,                                                 &self,
    id: Uuid,                                              id: Uuid,
    update: UpdateEntry,                                   update: UpdateEntry,
) -> Result<Entry, CmError>;                               ctx: &WriteContext,
                                                       ) -> Result<Entry, CmError>;

async fn supersede_entry(                              async fn supersede_entry(
    &self,                                                 &self,
    old_id: Uuid,                                          old_id: Uuid,
    new_entry: NewEntry,                                   new_entry: NewEntry,
) -> Result<Entry, CmError>;                               ctx: &WriteContext,
                                                       ) -> Result<Entry, CmError>;

async fn forget_entry(                                 async fn forget_entry(
    &self,                                                 &self,
    id: Uuid,                                              id: Uuid,
) -> Result<(), CmError>;                                  ctx: &WriteContext,
                                                       ) -> Result<(), CmError>;
```

**Scope and relation methods** (no mutation records, but carry provenance for consistency and future extensibility):

```rust
// BEFORE                                              // AFTER
async fn create_scope(                                 async fn create_scope(
    &self,                                                 &self,
    new_scope: NewScope,                                   new_scope: NewScope,
) -> Result<Scope, CmError>;                               ctx: &WriteContext,
                                                       ) -> Result<Scope, CmError>;

async fn create_relation(                              async fn create_relation(
    &self,                                                 &self,
    source_id: Uuid,                                       source_id: Uuid,
    target_id: Uuid,                                       target_id: Uuid,
    relation: RelationKind,                                relation: RelationKind,
) -> Result<EntryRelation, CmError>;                       ctx: &WriteContext,
                                                       ) -> Result<EntryRelation, CmError>;
```

### Full trait signature after changes

```rust
#[allow(async_fn_in_trait)]
pub trait ContextStore: Send + Sync + 'static {
    // ── Entry CRUD ──────────────────────────────────────────────

    async fn create_entry(&self, new_entry: NewEntry, ctx: &WriteContext) -> Result<Entry, CmError>;
    async fn get_entry(&self, id: Uuid) -> Result<Entry, CmError>;                           // unchanged
    async fn get_entries(&self, ids: &[Uuid]) -> Result<Vec<Entry>, CmError>;                 // unchanged
    async fn resolve_context(&self, scope_path: &ScopePath, kinds: &[EntryKind], limit: u32) -> Result<Vec<Entry>, CmError>; // unchanged
    async fn search(&self, query: &str, scope_path: Option<&ScopePath>, limit: u32) -> Result<Vec<Entry>, CmError>; // unchanged
    async fn browse(&self, filter: EntryFilter) -> Result<PagedResult<Entry>, CmError>;       // unchanged
    async fn update_entry(&self, id: Uuid, update: UpdateEntry, ctx: &WriteContext) -> Result<Entry, CmError>;
    async fn supersede_entry(&self, old_id: Uuid, new_entry: NewEntry, ctx: &WriteContext) -> Result<Entry, CmError>;
    async fn forget_entry(&self, id: Uuid, ctx: &WriteContext) -> Result<(), CmError>;

    // ── Relations ───────────────────────────────────────────────

    async fn create_relation(&self, source_id: Uuid, target_id: Uuid, relation: RelationKind, ctx: &WriteContext) -> Result<EntryRelation, CmError>;
    async fn get_relations_from(&self, source_id: Uuid) -> Result<Vec<EntryRelation>, CmError>; // unchanged
    async fn get_relations_to(&self, target_id: Uuid) -> Result<Vec<EntryRelation>, CmError>;   // unchanged

    // ── Scopes ──────────────────────────────────────────────────

    async fn create_scope(&self, new_scope: NewScope, ctx: &WriteContext) -> Result<Scope, CmError>;
    async fn get_scope(&self, path: &ScopePath) -> Result<Scope, CmError>;                     // unchanged
    async fn list_scopes(&self, kind: Option<ScopeKind>) -> Result<Vec<Scope>, CmError>;        // unchanged

    // ── Aggregation ─────────────────────────────────────────────

    async fn stats(&self) -> Result<StoreStats, CmError>;                                       // unchanged
    async fn export(&self, scope_path: Option<&ScopePath>) -> Result<Vec<Entry>, CmError>;      // unchanged

    // ── Mutations ───────────────────────────────────────────────

    /// Query mutation history for a specific entry, with pagination.
    async fn get_mutations(&self, entry_id: Uuid, limit: u32, offset: u32) -> Result<Vec<MutationRecord>, CmError>;

    /// Query mutation history with filters, including timestamp range.
    async fn list_mutations(
        &self,
        entry_id: Option<Uuid>,
        action: Option<MutationAction>,
        source: Option<MutationSource>,
        since: Option<DateTime<Utc>>,
        until: Option<DateTime<Utc>>,
        limit: u32,
    ) -> Result<Vec<MutationRecord>, CmError>;
}
```

Two new read methods are added for querying mutations. `get_mutations` supports per-entry history with pagination. `list_mutations` supports the cm-web `GET /api/mutations` endpoint with filters including timestamp range (`since`/`until`), which aligns with the `idx_mutations_timestamp` index.

## 4. SQLite Migration

File: `crates/cm-store/migrations/005_mutations.sql`

Following the existing naming convention (`001_initial_schema.sql`, `002_fts5_setup.sql`, etc.).

```sql
-- Migration 005: Mutation history table
--
-- Records every entry mutation on the context store.
-- Written by cm-store in the same transaction as the mutation.
-- Snapshots are full JSON serializations of the entry at that point in time.
--
-- No FK on entry_id. Mutation records are self-contained (full snapshots)
-- and must survive even if an entry row is hard-deleted by maintenance,
-- import/reset, or future operations. An audit trail that disappears when
-- its subject is deleted defeats the purpose.

CREATE TABLE mutations (
    id               TEXT PRIMARY KEY,           -- UUID v7
    entry_id         TEXT NOT NULL,              -- Entry that was mutated (no FK, survives deletion)
    action           TEXT NOT NULL CHECK (action IN ('create', 'update', 'forget', 'supersede')),
    source           TEXT NOT NULL CHECK (source IN ('mcp', 'cli', 'web', 'helix')),
    timestamp        TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    before_snapshot  TEXT,                       -- JSON: full entry state before (NULL for create)
    after_snapshot   TEXT                        -- JSON: full entry state after
);

-- Primary access pattern: "show me all mutations for this entry" (per-entry history)
CREATE INDEX idx_mutations_entry ON mutations(entry_id);

-- Secondary: "show me recent mutations across all entries" (activity feed, cm-web dashboard)
CREATE INDEX idx_mutations_timestamp ON mutations(timestamp);

-- Tertiary: "show me all mutations from a specific source" (filter by origin)
CREATE INDEX idx_mutations_source ON mutations(source);
```

This matches the DDL from the web curation spec with two refinements:
- explicit `CHECK` constraints on `action` and `source` to catch bad data at the database layer, consistent with how the `scopes.kind` and `entry_relations.relation` columns use CHECK constraints in `001_initial_schema.sql`
- no foreign key on `entry_id`, so mutation history remains durable even if an entry row is later hard-deleted outside the normal soft-delete path

**Note on CHECK constraint evolution**: Adding a future `MutationSource` variant (e.g., `Api`) requires a new migration to ALTER the CHECK constraint on the `source` column. Same for `MutationAction`. The CHECK constraint is intentionally coupled to the enum. This is the same pattern used for `scopes.kind` and `entry_relations.relation`.

## 5. CmStore Implementation Changes (cm-store)

File: `crates/cm-store/src/sqlite.rs`

### Helper: entry snapshot serialization

Add a private helper near the existing `parse_entry` function:

```rust
/// Serialize an Entry to a JSON Value for mutation snapshots.
fn entry_snapshot(entry: &Entry) -> Result<serde_json::Value, CmError> {
    Ok(serde_json::to_value(entry)?)
}
```

### Helper: insert mutation record

Add a private helper to reduce repetition across the four mutating methods:

```rust
/// Insert a mutation record within an existing transaction.
async fn insert_mutation(
    executor: impl sqlx::Executor<'_, Database = sqlx::Sqlite>,
    entry_id: &str,
    action: MutationAction,
    source: MutationSource,
    before: Option<&serde_json::Value>,
    after: Option<&serde_json::Value>,
) -> Result<(), CmError> {
    let id = Uuid::now_v7().to_string();
    let action_str = action.as_str();
    let source_str = source.as_str();
    let before_json = before.map(|v| v.to_string());
    let after_json = after.map(|v| v.to_string());
    let now = Utc::now().format("%Y-%m-%dT%H:%M:%S%.3fZ").to_string();

    sqlx::query(
        "INSERT INTO mutations (id, entry_id, action, source, timestamp, before_snapshot, after_snapshot) \
         VALUES (?, ?, ?, ?, ?, ?, ?)",
    )
    .bind(&id)
    .bind(entry_id)
    .bind(action_str)
    .bind(source_str)
    .bind(&now)
    .bind(&before_json)
    .bind(&after_json)
    .execute(executor)
    .await
    .map_err(map_db_err)?;

    Ok(())
}
```

### Method-by-method changes

#### `create_entry`

Current state: no transaction (single INSERT + fetch). Must wrap in a transaction.

```rust
async fn create_entry(&self, new_entry: NewEntry, ctx: &WriteContext) -> Result<Entry, CmError> {
    // ... validation unchanged ...

    let pool = &self.write_pool;
    dedup::check_duplicate(pool, &content_hash, None).await?;

    let now = Utc::now().format("%Y-%m-%dT%H:%M:%S%.3fZ").to_string();

    let mut tx = pool.begin().await.map_err(|e| CmError::Database(e.to_string()))?;

    // INSERT entry (same query as before, but against &mut *tx)
    sqlx::query("INSERT INTO entries ...")
        .bind(/* same binds */)
        .execute(&mut *tx)
        .await
        .map_err(/* same error handling */)?;

    // Fetch the created entry within the transaction
    let row = sqlx::query("SELECT * FROM entries WHERE id = ?")
        .bind(&id_str)
        .fetch_one(&mut *tx)
        .await
        .map_err(map_db_err)?;

    let entry = parse_entry(&row)?;
    let after = entry_snapshot(&entry)?;

    // Write mutation record
    insert_mutation(&mut *tx, &id_str, MutationAction::Create, ctx.source, None, Some(&after)).await?;

    tx.commit().await.map_err(|e| CmError::Database(e.to_string()))?;

    Ok(entry)
}
```

#### `update_entry`

Current state: no explicit transaction (SELECT + dynamic UPDATE + fetch). Must wrap in a single transaction that encompasses the before-read, the write, and the mutation record.

```rust
async fn update_entry(&self, id: Uuid, update: UpdateEntry, ctx: &WriteContext) -> Result<Entry, CmError> {
    // ... validation unchanged ...

    let pool = &self.write_pool;

    let mut tx = pool.begin().await.map_err(|e| CmError::Database(e.to_string()))?;

    // Fetch current entry inside the transaction (before snapshot).
    let current_row = sqlx::query("SELECT * FROM entries WHERE id = ?")
        .bind(&id_str)
        .fetch_optional(&mut *tx)
        .await
        .map_err(map_db_err)?
        .ok_or(CmError::EntryNotFound(id))?;

    let current = parse_entry(&current_row)?;

    // ... dedup check against &mut *tx, build dynamic UPDATE (unchanged) ...

    if sets.is_empty() {
        // No-op: no mutation record, roll back the read-only tx.
        return Ok(current);
    }

    let before = entry_snapshot(&current)?;

    // Execute dynamic UPDATE against tx
    let sql = format!("UPDATE entries SET {} WHERE id = ?", sets.join(", "));
    let mut q = sqlx::query(&sql);
    for v in &values {
        q = q.bind(v);
    }
    q = q.bind(&id_str);
    q.execute(&mut *tx).await.map_err(map_db_err)?;

    // Fetch updated entry (after snapshot)
    let row = sqlx::query("SELECT * FROM entries WHERE id = ?")
        .bind(&id_str)
        .fetch_one(&mut *tx)
        .await
        .map_err(map_db_err)?;

    let entry = parse_entry(&row)?;
    let after = entry_snapshot(&entry)?;

    // Write mutation record
    insert_mutation(&mut *tx, &id_str, MutationAction::Update, ctx.source, Some(&before), Some(&after)).await?;

    tx.commit().await.map_err(|e| CmError::Database(e.to_string()))?;

    Ok(entry)
}
```

#### `supersede_entry`

Current state: already uses a transaction. Move old-entry fetch inside the transaction, add two mutation record INSERTs with full post-state snapshots.

```rust
async fn supersede_entry(&self, old_id: Uuid, new_entry: NewEntry, ctx: &WriteContext) -> Result<Entry, CmError> {
    // ... validation, dedup check unchanged ...

    let pool = &self.write_pool;

    let mut tx = pool.begin().await.map_err(|e| CmError::Database(e.to_string()))?;

    // Fetch old entry inside the transaction (before snapshot).
    let old_row = sqlx::query("SELECT * FROM entries WHERE id = ?")
        .bind(&old_id_str)
        .fetch_optional(&mut *tx)
        .await
        .map_err(map_db_err)?
        .ok_or(CmError::EntryNotFound(old_id))?;

    let old_entry = parse_entry(&old_row)?;
    let old_before = entry_snapshot(&old_entry)?;

    // INSERT new entry (unchanged, against &mut *tx)
    // UPDATE old entry superseded_by (unchanged)
    // INSERT supersedes relation (unchanged)

    // Fetch old entry again for after snapshot (now has superseded_by set)
    let old_after_row = sqlx::query("SELECT * FROM entries WHERE id = ?")
        .bind(&old_id_str)
        .fetch_one(&mut *tx)
        .await
        .map_err(map_db_err)?;

    let old_after_entry = parse_entry(&old_after_row)?;
    let old_after = entry_snapshot(&old_after_entry)?;

    // Fetch new entry for after snapshot
    let new_row = sqlx::query("SELECT * FROM entries WHERE id = ?")
        .bind(&new_id_str)
        .fetch_one(&mut *tx)
        .await
        .map_err(map_db_err)?;

    let new_entry_result = parse_entry(&new_row)?;
    let new_after = entry_snapshot(&new_entry_result)?;

    // Mutation 1: old entry superseded (before: without superseded_by, after: with superseded_by)
    insert_mutation(&mut *tx, &old_id_str, MutationAction::Supersede, ctx.source, Some(&old_before), Some(&old_after)).await?;

    // Mutation 2: new entry created
    insert_mutation(&mut *tx, &new_id_str, MutationAction::Create, ctx.source, None, Some(&new_after)).await?;

    tx.commit().await.map_err(|e| CmError::Database(e.to_string()))?;

    Ok(new_entry_result)
}
```

#### `forget_entry`

Current state: no transaction (single UPDATE + optional existence check). Must wrap everything in a single transaction: read before-state, perform the update, read after-state, write mutation record.

```rust
async fn forget_entry(&self, id: Uuid, ctx: &WriteContext) -> Result<(), CmError> {
    let id_str = id.to_string();
    let pool = &self.write_pool;

    let mut tx = pool.begin().await.map_err(|e| CmError::Database(e.to_string()))?;

    // Fetch current entry inside transaction (before snapshot).
    let row = sqlx::query("SELECT * FROM entries WHERE id = ?")
        .bind(&id_str)
        .fetch_optional(&mut *tx)
        .await
        .map_err(map_db_err)?;

    match row {
        None => return Err(CmError::EntryNotFound(id)),
        Some(ref r) => {
            let entry = parse_entry(r)?;
            if entry.superseded_by.is_some() {
                // Already superseded/forgotten, no-op. No mutation record.
                return Ok(());
            }

            let before = entry_snapshot(&entry)?;

            sqlx::query(
                "UPDATE entries SET superseded_by = ? WHERE id = ? AND superseded_by IS NULL",
            )
            .bind(&id_str)
            .bind(&id_str)
            .execute(&mut *tx)
            .await
            .map_err(map_db_err)?;

            // Fetch after-state (now has superseded_by = self)
            let after_row = sqlx::query("SELECT * FROM entries WHERE id = ?")
                .bind(&id_str)
                .fetch_one(&mut *tx)
                .await
                .map_err(map_db_err)?;

            let after_entry = parse_entry(&after_row)?;
            let after = entry_snapshot(&after_entry)?;

            insert_mutation(&mut *tx, &id_str, MutationAction::Forget, ctx.source, Some(&before), Some(&after)).await?;

            tx.commit().await.map_err(|e| CmError::Database(e.to_string()))?;
        }
    }

    Ok(())
}
```

#### `create_scope`

Signature change only. No mutation record. Implementation is the same, just adds the unused `_ctx` parameter.

```rust
async fn create_scope(&self, new_scope: NewScope, _ctx: &WriteContext) -> Result<Scope, CmError> {
    // ... body unchanged ...
}
```

#### `create_relation`

Signature change only. No mutation record.

```rust
async fn create_relation(&self, source_id: Uuid, target_id: Uuid, relation: RelationKind, _ctx: &WriteContext) -> Result<EntryRelation, CmError> {
    // ... body unchanged ...
}
```

#### `get_mutations` (new)

```rust
async fn get_mutations(&self, entry_id: Uuid, limit: u32, offset: u32) -> Result<Vec<MutationRecord>, CmError> {
    let id_str = entry_id.to_string();
    let clamped_limit = limit.min(200).max(1);

    let rows = sqlx::query(
        "SELECT id, entry_id, action, source, timestamp, before_snapshot, after_snapshot \
         FROM mutations WHERE entry_id = ? ORDER BY timestamp DESC LIMIT ? OFFSET ?",
    )
    .bind(&id_str)
    .bind(clamped_limit)
    .bind(offset)
    .fetch_all(&self.read_pool)
    .await
    .map_err(map_db_err)?;

    rows.iter().map(parse_mutation).collect()
}
```

#### `list_mutations` (new)

```rust
async fn list_mutations(
    &self,
    entry_id: Option<Uuid>,
    action: Option<MutationAction>,
    source: Option<MutationSource>,
    since: Option<DateTime<Utc>>,
    until: Option<DateTime<Utc>>,
    limit: u32,
) -> Result<Vec<MutationRecord>, CmError> {
    let mut sql = String::from(
        "SELECT id, entry_id, action, source, timestamp, before_snapshot, after_snapshot FROM mutations WHERE 1=1"
    );
    let mut binds: Vec<String> = Vec::new();

    if let Some(eid) = entry_id {
        sql.push_str(" AND entry_id = ?");
        binds.push(eid.to_string());
    }
    if let Some(a) = action {
        sql.push_str(" AND action = ?");
        binds.push(a.as_str().to_owned());
    }
    if let Some(s) = source {
        sql.push_str(" AND source = ?");
        binds.push(s.as_str().to_owned());
    }
    if let Some(s) = since {
        sql.push_str(" AND timestamp >= ?");
        binds.push(s.to_rfc3339());
    }
    if let Some(u) = until {
        sql.push_str(" AND timestamp <= ?");
        binds.push(u.to_rfc3339());
    }

    sql.push_str(" ORDER BY timestamp DESC LIMIT ?");
    // Floor at 1, cap at 200. Matches clamp_limit() convention: 0 becomes 1, not empty.
    let clamped_limit = limit.min(200).max(1);

    let mut q = sqlx::query(&sql);
    for b in &binds {
        q = q.bind(b);
    }
    q = q.bind(clamped_limit);

    let rows = q.fetch_all(&self.read_pool).await.map_err(map_db_err)?;
    rows.iter().map(parse_mutation).collect()
}
```

#### Row parser (new helper)

Add alongside existing `parse_entry`, `parse_scope`, `parse_relation`:

```rust
fn parse_mutation(row: &SqliteRow) -> Result<MutationRecord, CmError> {
    use sqlx::Row;

    let id_str: String = row.try_get("id").map_err(map_db_err)?;
    let entry_id_str: String = row.try_get("entry_id").map_err(map_db_err)?;
    let action_str: String = row.try_get("action").map_err(map_db_err)?;
    let source_str: String = row.try_get("source").map_err(map_db_err)?;
    let timestamp_str: String = row.try_get("timestamp").map_err(map_db_err)?;
    let before_str: Option<String> = row.try_get("before_snapshot").map_err(map_db_err)?;
    let after_str: Option<String> = row.try_get("after_snapshot").map_err(map_db_err)?;

    Ok(MutationRecord {
        id: Uuid::parse_str(&id_str)
            .map_err(|e| CmError::Internal(format!("invalid mutation id: {e}")))?,
        entry_id: Uuid::parse_str(&entry_id_str)
            .map_err(|e| CmError::Internal(format!("invalid entry_id: {e}")))?,
        action: action_str.parse()?,
        source: source_str.parse()?,
        timestamp: parse_datetime(&timestamp_str)?,
        before_snapshot: before_str
            .map(|s| serde_json::from_str(&s))
            .transpose()?,
        after_snapshot: after_str
            .map(|s| serde_json::from_str(&s))
            .transpose()?,
    })
}
```

## 6. Call-site Update Inventory

Every file and function that calls a mutating trait method, with the exact change required.

### MCP tool handlers (all get `MutationSource::Mcp`)

| File | Function | Calls | Change |
|------|----------|-------|--------|
| `crates/cm-cli/src/mcp/tools/store.rs` | `cx_store` | `store.create_entry(new_entry)` (line 129) | Add `&WriteContext::new(MutationSource::Mcp)` |
| `crates/cm-cli/src/mcp/tools/store.rs` | `cx_store` | `store.supersede_entry(old_id, new_entry)` (line 122) | Add `&WriteContext::new(MutationSource::Mcp)` |
| `crates/cm-cli/src/mcp/tools/update.rs` | `cx_update` | `store.update_entry(id, update)` (line 114) | Add `&WriteContext::new(MutationSource::Mcp)` |
| `crates/cm-cli/src/mcp/tools/forget.rs` | `cx_forget` | `store.forget_entry(id)` (line 48) | Add `&WriteContext::new(MutationSource::Mcp)`. Note: `cx_forget` calls `get_entry` (line 42) before `forget_entry` for response messaging (already_inactive vs forgotten classification). `forget_entry` now also fetches the entry inside its transaction for before/after snapshots. This is a double-read, acceptable at current scale. The tool handler read is for response classification; the store-layer read is for audit correctness. |
| `crates/cm-cli/src/mcp/tools/deposit.rs` | `cx_deposit` | `store.create_entry(new_entry)` (line 98) | Add `&WriteContext::new(MutationSource::Mcp)` |
| `crates/cm-cli/src/mcp/tools/deposit.rs` | `cx_deposit` | `store.create_entry(summary_entry)` (line 121) | Add `&WriteContext::new(MutationSource::Mcp)` |
| `crates/cm-cli/src/mcp/tools/deposit.rs` | `cx_deposit` | `store.create_relation(sid, exchange_id, ...)` (line 129) | Add `&WriteContext::new(MutationSource::Mcp)` |

### Helpers

| File | Function | Calls | Change |
|------|----------|-------|--------|
| `crates/cm-cli/src/mcp/mod.rs` | `ensure_scope_chain` | `store.create_scope(new_scope)` (line 415) | Add `ctx: &WriteContext` parameter to `ensure_scope_chain` signature. Forward `ctx` to `store.create_scope(new_scope, ctx)`. |

`ensure_scope_chain` callers must also pass the WriteContext:

| File | Function | Calls | Change |
|------|----------|-------|--------|
| `crates/cm-cli/src/mcp/tools/store.rs` | `cx_store` | `ensure_scope_chain(store, &scope_path)` (line 86) | Add `&WriteContext::new(MutationSource::Mcp)` |
| `crates/cm-cli/src/mcp/tools/deposit.rs` | `cx_deposit` | `ensure_scope_chain(store, &scope_path)` (line 73) | Add `&WriteContext::new(MutationSource::Mcp)` |

### Practical note on MCP tools

Each tool handler should construct the `WriteContext` once at the top:

```rust
pub async fn cx_store(store: &impl ContextStore, args: &Value) -> Result<String, String> {
    let ctx = WriteContext::new(MutationSource::Mcp);
    // ... rest of function uses &ctx everywhere ...
}
```

### Tests

| File | Impact |
|------|--------|
| `crates/cm-store/tests/sqlite_integration.rs` | Every call to `create_entry`, `update_entry`, `supersede_entry`, `forget_entry`, `create_scope`, `create_relation` needs `&ctx`. Add `fn test_ctx() -> WriteContext { WriteContext::new(MutationSource::Mcp) }` helper. |
| `crates/cm-cli/tests/tools_integration.rs` | `create_scope` call in `create_global()` helper (line 28) needs `&ctx`. Tool handler calls (`cx_store`, `cx_update`, etc.) do NOT change because they construct WriteContext internally. |
| `crates/cm-cli/tests/snapshot_tests.rs` | Same as tools_integration: only `create_scope` calls in test setup need `&ctx`. Snapshot content may change if tool responses include mutation-related data (unlikely for v1). |
| `crates/cm-cli/tests/mcp_protocol_test.rs` | Review for any direct trait method calls. Likely only setup helpers. |

## 7. Test Plan

### New tests in `crates/cm-store/tests/sqlite_integration.rs`

| Test | Description |
|------|-------------|
| `create_entry_writes_mutation` | Create an entry, call `get_mutations(entry_id, 50, 0)`. Assert: one record, action=Create, source=Mcp, before=None, after contains entry JSON with matching id/title/body. |
| `update_entry_writes_mutation` | Create then update an entry. Assert: two mutation records (Create + Update). Update record has before (old title) and after (new title). |
| `forget_entry_writes_mutation` | Create then forget. Assert: two records (Create + Forget). Forget record has before snapshot (without superseded_by) and after snapshot (with superseded_by = self). |
| `supersede_entry_writes_two_mutations` | Create entry A, supersede with entry B. Assert: three records total. Entry A has Create + Supersede. Entry B has Create. Supersede record for A has before snapshot (without superseded_by) and after snapshot (with superseded_by = B's ID). |
| `forget_already_superseded_no_mutation` | Forget an already-superseded entry. Assert: no new mutation record written (no-op). |
| `noop_update_no_mutation` | Call `update_entry` with no actual changes (all fields None after validation). Assert: no mutation record written. |
| `list_mutations_filters` | Create several entries with different actions. Test `list_mutations` with action filter, source filter, entry_id filter, since/until timestamp range, and limit. |
| `get_mutations_pagination` | Create an entry, perform multiple updates. Test `get_mutations` with limit and offset. Assert correct page sizes and ordering. |
| `mutation_source_roundtrip` | Verify `MutationSource` as_str/FromStr roundtrip for all variants. |
| `mutation_action_roundtrip` | Verify `MutationAction` as_str/FromStr roundtrip for all variants. |

### New tests in `crates/cm-core/tests/types_test.rs`

| Test | Description |
|------|-------------|
| `write_context_construction` | Verify `WriteContext::new` sets source correctly for all variants. |
| `mutation_source_serde` | Verify JSON serialization/deserialization of `MutationSource` enum. |
| `mutation_action_serde` | Verify JSON serialization/deserialization of `MutationAction` enum. |

### Existing test updates

All existing tests in `sqlite_integration.rs` and `tools_integration.rs` that call mutating trait methods must be updated to pass `&WriteContext`. Use a shared `test_ctx()` helper. This is a mechanical change: add one argument to each call site.

Snapshot tests in `snapshot_tests.rs` may need snapshot updates if the test output format changes. Since mutation history is written silently (same tool response format), snapshots should remain stable. Verify by running `cargo test` and checking for snapshot mismatches.

## 8. Migration Path

**Existing data**: No mutation records exist for historical entries. This is acceptable and expected. The mutations table starts empty. All writes after the migration is applied will be logged.

**Deployment sequence**:
1. Add migration file `005_mutations.sql`
2. `run_migrations()` (via `sqlx::migrate!`) applies it automatically on next startup
3. No backfill. No data conversion. The migration is purely additive (new table + indexes).

**Rollback**: Drop the `mutations` table. No other tables are affected. The `WriteContext` parameter is a code-level change that compiles regardless of whether the table exists, but removing the table would cause INSERT failures. In practice, rollback means reverting the code change and the migration together.

**Performance considerations**:
- Each entry write adds one INSERT to the `mutations` table (two for supersede). At ~30 writes/day, this is negligible.
- All before-snapshot reads happen inside the same transaction as the write, so there is no extra connection acquisition. The added cost is one indexed primary key lookup per mutating call.
- `supersede_entry` and `forget_entry` now re-fetch the entry after the UPDATE to capture the post-state. This adds one more SELECT per call, also inside the transaction.
- `create_entry` already fetched the created row. The snapshot serialization (`serde_json::to_value`) adds microseconds.
