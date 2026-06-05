---
title: "context-matters: Async Migration Spec"
date: 2026-03-18
tags: [rust, context-matters, async, migration, spec]
type: spec
status: active
source: rust-architecture-proposal-helioy-2026
---

# context-matters: Async Migration Spec

## 1. Executive Summary

Migrate the `ContextStore` trait from synchronous signatures to native `async fn` in trait. Add `Send + Sync + 'static` bounds. Make all consumers generic over the trait instead of concrete `CmStore`.

**Why now.** The trait's synchronous design forces `cm-store` to wrap every sqlx call in `tokio::task::block_in_place(|| Handle::current().block_on(async { ... }))`. This creates three problems: (1) it inverts the async runtime's control flow, blocking a tokio worker thread to synchronously re-enter the runtime; (2) it prevents adding a second adapter (in-memory test store, HTTP proxy store) without pulling in tokio as a transitive dependency; (3) it hides the true async boundary from the compiler, defeating borrow checker reasoning about lifetimes across `.await` points.

The migration is mechanical. No business logic changes. No query changes. No schema changes. No new dependencies.

**Driving document.** [`~/.mdx/research/rust-architecture-proposal-helioy-2026.md`](rust-architecture-proposal-helioy-2026.md), sections 2.2, 3.2, and 5.1.

---

## 2. Current State Analysis

### 2.1 Crate Boundaries

```
crates/cm-core/   (1,753 LOC)  Zero I/O. Domain types, ContextStore trait, query builders, error types.
crates/cm-store/  (3,282 LOC)  SQLite adapter. sqlx pools, schema, migrations, dedup.
crates/cm-cli/    (3,339 LOC)  CLI binary + MCP stdio server + 9 tool handlers.
```

### 2.2 The ContextStore Trait (cm-core/src/store.rs)

Synchronous. 17 methods. No `Send`/`Sync`/`'static` bounds. The doc comment explicitly acknowledges the impedance mismatch:

> "The trait uses synchronous signatures because cm-core has zero async dependencies. The adapter crate (cm-store) wraps these in async methods using sqlx's internal thread pool."

```rust
pub trait ContextStore {
    fn create_entry(&self, new_entry: NewEntry) -> Result<Entry, CmError>;
    fn get_entry(&self, id: Uuid) -> Result<Entry, CmError>;
    fn get_entries(&self, ids: &[Uuid]) -> Result<Vec<Entry>, CmError>;
    fn resolve_context(&self, scope_path: &ScopePath, kinds: &[EntryKind], limit: u32) -> Result<Vec<Entry>, CmError>;
    fn search(&self, query: &str, scope_path: Option<&ScopePath>, limit: u32) -> Result<Vec<Entry>, CmError>;
    fn browse(&self, filter: EntryFilter) -> Result<PagedResult<Entry>, CmError>;
    fn update_entry(&self, id: Uuid, update: UpdateEntry) -> Result<Entry, CmError>;
    fn supersede_entry(&self, old_id: Uuid, new_entry: NewEntry) -> Result<Entry, CmError>;
    fn forget_entry(&self, id: Uuid) -> Result<(), CmError>;
    fn create_relation(&self, source_id: Uuid, target_id: Uuid, relation: RelationKind) -> Result<EntryRelation, CmError>;
    fn get_relations_from(&self, source_id: Uuid) -> Result<Vec<EntryRelation>, CmError>;
    fn get_relations_to(&self, target_id: Uuid) -> Result<Vec<EntryRelation>, CmError>;
    fn create_scope(&self, new_scope: NewScope) -> Result<Scope, CmError>;
    fn get_scope(&self, path: &ScopePath) -> Result<Scope, CmError>;
    fn list_scopes(&self, kind: Option<ScopeKind>) -> Result<Vec<Scope>, CmError>;
    fn stats(&self) -> Result<StoreStats, CmError>;
    fn export(&self, scope_path: Option<&ScopePath>) -> Result<Vec<Entry>, CmError>;
}
```

### 2.3 The CmStore Adapter (cm-store/src/sqlite.rs)

`CmStore` holds two `sqlx::SqlitePool` fields (1 writer, 4 readers). Every trait method follows the same pattern:

```rust
fn method_name(&self, ...) -> Result<T, CmError> {
    // validation (pure, no I/O)
    let pool = &self.write_pool; // or read_pool
    tokio::task::block_in_place(|| {
        tokio::runtime::Handle::current().block_on(async {
            // sqlx queries with .await
        })
    })
}
```

There are **17 occurrences** of `block_in_place` in `sqlite.rs`. Zero elsewhere.

One method uses an explicit transaction: `supersede_entry` calls `pool.begin().await` and executes three mutations (INSERT, UPDATE, INSERT) within a `sqlx::Transaction` before `tx.commit().await`.

### 2.4 The MCP Server (cm-cli/src/mcp/mod.rs)

`McpServer` holds `Arc<CmStore>` (concrete type). The `run()` method uses blocking `stdin.lock().lines()` inside an `async fn`. Tool dispatch calls 9 synchronous handler functions:

```rust
let result = match tool_name {
    "cx_recall" => tools::cx_recall(&self.store, &arguments),
    "cx_store" => tools::cx_store(&self.store, &arguments),
    // ... 7 more
};
```

Handlers are `pub fn cx_*(store: &CmStore, args: &Value) -> Result<String, String>`.

### 2.5 Consumer Coupling

Every consumer references `CmStore` by concrete type, not through the `ContextStore` trait:

| File | Reference |
|------|-----------|
| `mcp/mod.rs` | `store: Arc<CmStore>`, `fn new(store: CmStore)`, `fn store() -> &CmStore` |
| `mcp/tools/*.rs` (9 files) | `fn cx_*(store: &CmStore, ...)` |
| `mcp/mod.rs` | `fn ensure_scope_chain(store: &CmStore, ...)` |
| `cli/mod.rs` | `fn cmd_stats(store: &CmStore)` |
| `main.rs` | `open_store() -> CmStore` (concrete; this one stays) |

### 2.6 Threading Model

- `#[tokio::main]` uses the multi-thread runtime (default).
- `McpServer::run()` is called via `runtime.block_on()`, not `tokio::spawn()`. This means the future does NOT need to be `Send`.
- `StdinLock<'_>` is `!Send`. It is held across `.await` points inside the loop. This compiles because `block_on` does not require `Send`. This is a documented design constraint (see section 10, Risk R3).
- Tool calls are sequential. The MCP stdio protocol is single-client request/response. There is no concurrent work.

### 2.7 SQLite Async Reality

sqlx's SQLite backend is not truly async. Each pool connection runs on a dedicated OS thread. The "async" API is a channel-dispatch wrapper: the caller sends a query to the connection thread via a channel, the connection thread executes it synchronously, and the result comes back on the channel. The `.await` suspends the caller while waiting for the channel response.

This means removing `block_in_place` does not change the actual execution model. The same work happens on the same threads. What changes is the control flow: instead of blocking a tokio worker to synchronously pump the runtime, the trait method yields properly and lets tokio schedule other work (if any exists).

For a single-client stdio MCP server, this distinction is academic. The value is architectural: the trait becomes composable with async callers, enabling future HTTP adapters and concurrent tool execution without further signature changes.

---

## 3. Target State Architecture

### 3.1 Trait Definition

```rust
/// Async storage interface for context entries.
///
/// All methods are async and return `Result<T, CmError>`. Uses native
/// async fn in trait (stable since Rust 1.75). Consumers use generics
/// (`&impl ContextStore`) rather than `dyn ContextStore` because native
/// async traits do not support dynamic dispatch without boxing.
///
/// ## Bounds
///
/// `Send + Sync + 'static` enables:
/// - Wrapping in `Arc<S>` for shared ownership across async tasks
/// - Using `S` as a type parameter in structs stored in `Arc`
/// - Future compatibility with `tokio::spawn` if concurrency is added
///
/// ## Conventions
///
/// - Methods that query entries exclude superseded entries by default
///   unless the caller explicitly opts in via `EntryFilter::include_superseded`.
/// - Write methods use the write pool (1 connection). Read methods use the read pool.
/// - All IDs are UUIDv7, generated by the store on creation.
pub trait ContextStore: Send + Sync + 'static {
    async fn create_entry(&self, new_entry: NewEntry) -> Result<Entry, CmError>;
    async fn get_entry(&self, id: Uuid) -> Result<Entry, CmError>;
    async fn get_entries(&self, ids: &[Uuid]) -> Result<Vec<Entry>, CmError>;
    async fn resolve_context(&self, scope_path: &ScopePath, kinds: &[EntryKind], limit: u32) -> Result<Vec<Entry>, CmError>;
    async fn search(&self, query: &str, scope_path: Option<&ScopePath>, limit: u32) -> Result<Vec<Entry>, CmError>;
    async fn browse(&self, filter: EntryFilter) -> Result<PagedResult<Entry>, CmError>;
    async fn update_entry(&self, id: Uuid, update: UpdateEntry) -> Result<Entry, CmError>;
    async fn supersede_entry(&self, old_id: Uuid, new_entry: NewEntry) -> Result<Entry, CmError>;
    async fn forget_entry(&self, id: Uuid) -> Result<(), CmError>;
    async fn create_relation(&self, source_id: Uuid, target_id: Uuid, relation: RelationKind) -> Result<EntryRelation, CmError>;
    async fn get_relations_from(&self, source_id: Uuid) -> Result<Vec<EntryRelation>, CmError>;
    async fn get_relations_to(&self, target_id: Uuid) -> Result<Vec<EntryRelation>, CmError>;
    async fn create_scope(&self, new_scope: NewScope) -> Result<Scope, CmError>;
    async fn get_scope(&self, path: &ScopePath) -> Result<Scope, CmError>;
    async fn list_scopes(&self, kind: Option<ScopeKind>) -> Result<Vec<Scope>, CmError>;
    async fn stats(&self) -> Result<StoreStats, CmError>;
    async fn export(&self, scope_path: Option<&ScopePath>) -> Result<Vec<Entry>, CmError>;
}
```

### 3.2 Consumer Pattern

All consumers become generic over the trait. The concrete type is chosen only in `main.rs`.

```rust
// McpServer becomes generic
pub struct McpServer<S: ContextStore> {
    store: Arc<S>,
}

impl<S: ContextStore> McpServer<S> {
    pub fn new(store: S) -> Self { Self { store: Arc::new(store) } }
    pub fn store(&self) -> &S { &self.store }
}

// Tool handlers use impl trait
pub async fn cx_store(store: &impl ContextStore, args: &Value) -> Result<String, String> { ... }

// Helper functions use impl trait
pub(crate) async fn ensure_scope_chain(store: &impl ContextStore, path: &ScopePath) -> Result<(), String> { ... }

// CLI commands use impl trait
pub async fn cmd_stats(store: &impl ContextStore) { ... }
```

### 3.3 main.rs (Unchanged Structurally)

```rust
#[tokio::main]
async fn main() -> Result<()> {
    // ... argument parsing, tracing init ...
    match &cli_args.command {
        Commands::Serve => cmd_serve().await,
        Commands::Stats => {
            let store = open_store().await?;   // CmStore: concrete type chosen here
            cli::cmd_stats(&store).await?;     // Inferred as &CmStore via impl ContextStore
            // ...
        }
    }
}
```

The concrete `CmStore` type appears only in `main.rs` (via `open_store()`) and in test setup functions. All other code is generic.

---

## 4. Migration Strategy

Single atomic commit. The trait, impl, all consumers, and all tests must change together. Async fn in trait is not additive; you cannot have both sync and async versions of the same method on the same trait without a shim trait.

### Phase Ordering

```
Phase 0:  Validate baseline         (just check && just test)
Phase 1:  Trait + bounds            (cm-core/src/store.rs)
Phase 2:  Store impl                (cm-store/src/sqlite.rs)
Phase 3:  MCP server + handlers     (cm-cli/src/mcp/**)
Phase 4:  CLI commands              (cm-cli/src/cli/mod.rs)
Phase 5:  Store integration tests   (cm-store/tests/sqlite_integration.rs)
Phase 6:  CLI integration tests     (cm-cli/tests/tools_integration.rs)
Phase 7:  Validate result           (just check && just test)
```

**Entry criteria:** `just check && just test` passes on main.

**Exit criteria:**
- `just check && just test` passes
- `grep -r "block_in_place" crates/` returns zero results
- `grep -r "CmStore" crates/cm-cli/src/mcp/` returns zero results (concrete type only in main.rs and test setup)
- `grep -r "use cm_store::CmStore" crates/cm-cli/src/mcp/tools/` returns zero results

All phases happen in the same commit. The phases are logical ordering for the implementor, not separate PRs.

---

## 5. ContextStore Trait Migration

### 5.1 Trait Definition Changes

**File:** `crates/cm-core/src/store.rs`

Two changes:

1. Line 23: Add `Send + Sync + 'static` bounds.
2. All 17 method signatures: prepend `async`.

The doc comment (lines 8-22) must be updated. Replace "Synchronous storage interface" with the async doc comment shown in section 3.1. Remove the paragraph about "wraps these in async methods" since the trait itself is now async.

**cm-core Cargo.toml:** No changes. Native async fn in trait requires no dependencies. The trait compiles without tokio, without futures, without async-trait. This preserves cm-core's zero-I/O guarantee.

### 5.2 Why Native Async Fn (Not #[async_trait])

Native `async fn` in trait is stable since Rust 1.75. The project targets edition 2024, so this is available. Advantages over the `#[async_trait]` proc macro:

- No heap allocation per call (no `Box::pin(async move { ... })`)
- No proc macro dependency or compile-time cost
- The compiler sees the real types, enabling better error messages
- No hidden `Send` bound injection (`#[async_trait]` adds `Send` by default unless `?Send` is specified)

**Trade-off 1: No dyn dispatch.** Native async fn in trait does not support `dyn ContextStore`. The returned futures have unnameable types, so they cannot be erased behind a trait object. This forces all consumers to use generics (`impl ContextStore`, `<S: ContextStore>`). For context-matters, this is the correct trade-off: there is one implementor (`CmStore`), and generics are zero-cost (monomorphized at compile time).

**Trade-off 2: Future Send-ness is not constrained.** With `async fn` syntax, the trait does not guarantee that returned futures are `Send`. The `Send + Sync + 'static` bound constrains the *implementing type*, not the *futures its methods produce*. In the current architecture (single-client MCP stdio, `block_on` in main), this is irrelevant because the futures never need to be `Send`.

If a future HTTP adapter calls trait methods from `tokio::spawn`'ed axum handlers, the futures *would* need to be `Send`. At that point, switch from `async fn` syntax to RPITIT with an explicit `Send` bound:

```rust
// Future form (when HTTP adapter is added):
fn create_entry(&self, new_entry: NewEntry) -> impl Future<Output = Result<Entry, CmError>> + Send + '_;
```

This is a one-line-per-method change with no impact on `CmStore` (its futures are already `Send` because `SqlitePool` and `sqlx::Transaction` are `Send`). The migration from `async fn` to RPITIT is additive and can be deferred until the HTTP adapter materializes.

**Decision: use `async fn` now, defer RPITIT `+ Send` until needed.** This follows the reversibility principle: the simpler syntax is easier to read and sufficient for current requirements.

### 5.3 Send + Sync + 'static Justification

`CmStore` holds two `SqlitePool` fields. `SqlitePool` implements `Send + Sync` (it is an `Arc<PoolInner>` internally). Therefore `CmStore` auto-derives `Send + Sync + 'static`.

Adding these bounds to the trait is forward-compatible:
- Required for `Arc<S>` (used in `McpServer`)
- Required for `tokio::spawn()` if concurrent tool handling is added later
- Required if a future HTTP adapter wraps the store in `axum::State<Arc<S>>`

No implementor will fail these bounds unless it holds non-Send/Sync state, which would be a design error for a database adapter.

---

## 6. SQLite / sqlx Migration

### 6.1 Removing block_in_place

Each of the 17 `block_in_place` occurrences follows the same transformation:

**Before:**
```rust
fn method_name(&self, ...) -> Result<T, CmError> {
    // validation (unchanged)
    let pool = &self.write_pool;
    tokio::task::block_in_place(|| {
        tokio::runtime::Handle::current().block_on(async {
            sqlx::query("...").execute(pool).await.map_err(map_db_err)?;
            // ...
        })
    })
}
```

**After:**
```rust
async fn method_name(&self, ...) -> Result<T, CmError> {
    // validation (unchanged)
    let pool = &self.write_pool;
    sqlx::query("...").execute(pool).await.map_err(map_db_err)?;
    // ...
}
```

The inner async block's body moves directly into the method body. All `.await` calls remain. No query logic changes.

### 6.2 Pool Configuration (Unchanged)

The dual-pool architecture stays as-is:

- **Write pool:** `max_connections(1)`. Serializes writes, avoids `SQLITE_BUSY`.
- **Read pool:** `max_connections(4)`, `read_only(true)`. Concurrent reads via WAL.
- **Pragmas:** WAL mode, `synchronous=NORMAL`, `busy_timeout=5000ms`, `cache_size=-64000` (64MB), `mmap_size=268435456` (256MB), `foreign_keys=ON`.

No pool configuration changes are needed. The pools are already async (`create_pools` is already `async fn`). The migration only affects how the trait methods interact with the pools.

### 6.3 Transaction Patterns

`supersede_entry` is the only method using an explicit `sqlx::Transaction`. The transaction code is already async inside the `block_in_place` wrapper. After migration, it moves to the method body:

```rust
async fn supersede_entry(&self, old_id: Uuid, new_entry: NewEntry) -> Result<Entry, CmError> {
    // validation, dedup check...
    let mut tx = pool.begin().await.map_err(|e| CmError::Database(e.to_string()))?;

    // INSERT new entry
    sqlx::query("INSERT INTO entries ...").execute(&mut *tx).await.map_err(map_db_err)?;

    // UPDATE old entry
    sqlx::query("UPDATE entries SET superseded_by = ? WHERE id = ?")
        .bind(&new_id_str).bind(&old_id_str)
        .execute(&mut *tx).await.map_err(map_db_err)?;

    // INSERT relation
    sqlx::query("INSERT INTO entry_relations ...")
        .bind(&new_id_str).bind(&old_id_str)
        .execute(&mut *tx).await.map_err(map_db_err)?;

    tx.commit().await.map_err(|e| CmError::Database(e.to_string()))?;

    // Fetch result (post-commit, from pool)
    let row = sqlx::query("SELECT * FROM entries WHERE id = ?")
        .bind(&new_id_str).fetch_one(pool).await.map_err(map_db_err)?;
    parse_entry(&row)
}
```

`sqlx::Transaction<'_, Sqlite>` is `Send`. Holding it across `.await` points is safe. In the current architecture, `Send` is not required (see section 7.2), but this remains correct even if `Send` becomes required in the future.

### 6.4 Import Cleanup

After removing all `block_in_place` wrappers, the `tokio` import in `sqlite.rs` is no longer needed. Remove:

```rust
// These are no longer used:
// tokio::task::block_in_place
// tokio::runtime::Handle
```

Check whether `tokio` is used elsewhere in `sqlite.rs` (it is not). The `tokio` dependency remains in `cm-store/Cargo.toml` for `#[tokio::test]` in tests.

### 6.5 dedup Module (No Changes)

`dedup::check_duplicate` is already `pub async fn`. It takes `&SqlitePool` directly and uses `.await` internally. No changes needed. The function is called from within the trait impl methods, and after migration those methods are async, so the `.await` on `check_duplicate` works naturally.

`dedup::recompute_hash_for_update` is synchronous (pure computation). No changes.

---

## 7. MCP Server Migration

### 7.1 McpServer Struct

**File:** `crates/cm-cli/src/mcp/mod.rs`

**Before (line 114):**
```rust
pub struct McpServer {
    store: Arc<CmStore>,
}

impl McpServer {
    pub fn new(store: CmStore) -> Self {
        Self { store: Arc::new(store) }
    }
    pub fn store(&self) -> &CmStore {
        &self.store
    }
}
```

**After:**
```rust
pub struct McpServer<S: ContextStore> {
    store: Arc<S>,
}

impl<S: ContextStore> McpServer<S> {
    pub fn new(store: S) -> Self {
        Self { store: Arc::new(store) }
    }
    pub fn store(&self) -> &S {
        &self.store
    }
}
```

Remove `use cm_store::CmStore;` (line 14). The `use cm_core::{CmError, ScopePath};` import already exists (line 13). Add `ContextStore` to that import if not already present.

### 7.2 The Blocking Stdin Loop

`McpServer::run()` uses `stdin.lock().lines()`, which returns a `StdinLock<'_>`. This type is `!Send`. The lock is held across the `.await` on `self.handle_request(&request).await`.

This compiles because `run()` is called from `main()` via `runtime.block_on()`, which executes the future on the current thread without requiring `Send`. If someone were to call `tokio::spawn(server.run())`, the compiler would reject it with a "`StdinLock` is not Send" error.

**This is correct behavior, not a bug.** The MCP stdio protocol is inherently single-client. There is no reason to spawn the server future onto a separate task. The constraint is self-documenting: the type system prevents misuse.

No changes to the stdio loop structure. The only change is adding `.await` to the tool handler calls inside `handle_tool_call`.

### 7.3 Tool Dispatch

**Before (lines 248-258):**
```rust
let result = match tool_name {
    "cx_recall" => tools::cx_recall(&self.store, &arguments),
    "cx_store" => tools::cx_store(&self.store, &arguments),
    // ... 7 more
    _ => Err(format!("Unknown tool: {tool_name}")),
};
```

**After:**
```rust
let result = match tool_name {
    "cx_recall" => tools::cx_recall(&self.store, &arguments).await,
    "cx_store" => tools::cx_store(&self.store, &arguments).await,
    "cx_deposit" => tools::cx_deposit(&self.store, &arguments).await,
    "cx_browse" => tools::cx_browse(&self.store, &arguments).await,
    "cx_get" => tools::cx_get(&self.store, &arguments).await,
    "cx_update" => tools::cx_update(&self.store, &arguments).await,
    "cx_forget" => tools::cx_forget(&self.store, &arguments).await,
    "cx_stats" => tools::cx_stats(&self.store, &arguments).await,
    "cx_export" => tools::cx_export(&self.store, &arguments).await,
    _ => Err(format!("Unknown tool: {tool_name}")),
};
```

Since `self.store` is `Arc<S>`, and `Arc<S>` derefs to `S`, passing `&self.store` gives `&Arc<S>`. The tool handlers take `&impl ContextStore`. `Arc<S>` implements `Deref<Target = S>`, but `&Arc<S>` is not `&S`. We need `&*self.store` or the handlers should accept `&Arc<S>`.

Actually, since the handlers take `store: &impl ContextStore`, and we pass `&self.store` where `self.store: Arc<S>`, Rust will auto-deref: `&Arc<S>` dereferences to `&S`, and `S: ContextStore`, so `&S` satisfies `&impl ContextStore`. This works transparently.

Correction: `&self.store` gives `&Arc<S>`, not `&S`. For `&impl ContextStore` to accept this, `Arc<S>` itself would need to implement `ContextStore`. It does not. We need `&*self.store` to get `&S`.

Check the current code: `tools::cx_recall(&self.store, &arguments)` where `self.store: Arc<CmStore>`. The handler takes `store: &CmStore`. `&self.store` gives `&Arc<CmStore>`. `Arc<CmStore>` derefs to `CmStore`. Rust auto-derefs `&Arc<CmStore>` to `&CmStore` at the call site.

After migration: handler takes `store: &impl ContextStore`. `&self.store` gives `&Arc<S>`. Auto-deref gives `&S`. `S: ContextStore`. The `impl ContextStore` is resolved to `S`. This works.

### 7.4 ensure_scope_chain

**Before (line 388):**
```rust
pub(crate) fn ensure_scope_chain(store: &CmStore, path: &ScopePath) -> Result<(), String> {
    use cm_core::{ContextStore, NewScope};
    // ...
    match store.get_scope(&ancestor) {
        Ok(_) => continue,
        Err(CmError::ScopeNotFound(_)) => {
            store.create_scope(new_scope).map_err(cm_err_to_string)?;
        }
        Err(e) => return Err(cm_err_to_string(e)),
    }
}
```

**After:**
```rust
pub(crate) async fn ensure_scope_chain(store: &impl ContextStore, path: &ScopePath) -> Result<(), String> {
    use cm_core::NewScope;
    // ...
    match store.get_scope(&ancestor).await {
        Ok(_) => continue,
        Err(CmError::ScopeNotFound(_)) => {
            store.create_scope(new_scope).await.map_err(cm_err_to_string)?;
        }
        Err(e) => return Err(cm_err_to_string(e)),
    }
}
```

Remove the `use cm_core::ContextStore` inside the function body (line 389). `ContextStore` is already in scope from the function signature's `impl ContextStore` bound.

### 7.5 Tool Handler Transformation Pattern

All 9 handlers follow the same transformation:

1. `pub fn cx_*(store: &CmStore, args: &Value)` becomes `pub async fn cx_*(store: &impl ContextStore, args: &Value)`
2. Remove `use cm_store::CmStore;` import
3. Add `.await` after every `store.*()` call
4. Add `.await` after `ensure_scope_chain()` calls (affects `store.rs` and `deposit.rs`)

**Complete call-site inventory:**

| File | store calls | ensure_scope_chain calls |
|------|-------------|-------------------------|
| `tools/browse.rs` | 1 (`store.browse`) | 0 |
| `tools/deposit.rs` | 3 (`create_entry` x2, `create_relation`) | 1 |
| `tools/export.rs` | 2 (`store.export`, `store.list_scopes`) | 0 |
| `tools/forget.rs` | 2 (`store.get_entry`, `store.forget_entry`) | 0 |
| `tools/get.rs` | 1 (`store.get_entries`) | 0 |
| `tools/recall.rs` | 3 (`store.search`, `store.resolve_context`, `store.browse`) | 0 |
| `tools/stats.rs` | 2 (`store.stats`, `store.list_scopes`) | 0 |
| `tools/store.rs` | 2 (`store.supersede_entry`, `store.create_entry`) | 1 |
| `tools/update.rs` | 1 (`store.update_entry`) | 0 |

**Total:** 17 store calls + 2 ensure_scope_chain calls = 19 `.await` additions across 9 files.

### 7.6 CLI Command Handler

**File:** `crates/cm-cli/src/cli/mod.rs`

```rust
// Before (line 11)
pub async fn cmd_stats(store: &CmStore) {
    let stats = store.stats();
    // ...
}

// After
pub async fn cmd_stats(store: &impl ContextStore) {
    let stats = store.stats().await;
    // ...
}
```

Remove `use cm_store::CmStore;`. The function is already `async fn` (it was async before, calling sync store methods).

### 7.7 main.rs

No signature changes. `main.rs` is where the concrete type lives. `open_store()` returns `CmStore`. `McpServer::new(store)` infers `McpServer<CmStore>`. Type inference handles everything.

The `server.store().write_pool()` call on line 84 continues to work because `store()` returns `&S` where `S = CmStore`, and `CmStore` has a `write_pool()` method.

Wait: `store()` returns `&S` where `S: ContextStore`. The `write_pool()` method is on `CmStore`, not on `ContextStore`. Since `S` is inferred as `CmStore` in `main.rs`, `server.store()` returns `&CmStore`, and `write_pool()` resolves. This works because Rust monomorphizes the generic.

---

## 8. Error Handling

### 8.1 No Changes to Error Types

`CmError` (cm-core/src/error.rs) is unchanged. It uses `thiserror` with 11 variants. All variants are `Send + Sync` (they contain `Uuid`, `String`, `ScopePathError`, and `serde_json::Error`, all of which are `Send + Sync`).

### 8.2 No Changes to Error Propagation

The `Result<T, CmError>` return type on all trait methods stays the same. The `?` operator works identically in async methods. No new error variants needed.

### 8.3 No Changes to Error-as-UI Pattern

`cm_err_to_string()` converts domain errors to actionable messages. The tool handlers call this via `.map_err(cm_err_to_string)`. The `isError:true` workaround remains. None of this is affected by async.

### 8.4 sqlx Error Mapping

`map_db_err()` converts `sqlx::Error` to `CmError`. No changes. The function is synchronous and is called inline after `.await.map_err(map_db_err)?`.

---

## 9. Testing Strategy

### 9.1 Existing Tests (Modify)

**Store integration tests** (`cm-store/tests/sqlite_integration.rs`, 1,288 LOC):

- Helper functions `create_global()` and `create_project_scope()`: change `fn` to `async fn`, add `.await` to store calls.
- All test bodies: add `.await` after every `store.*()` call.
- Tests already use `#[tokio::test(flavor = "multi_thread")]`. No annotation changes.

**CLI tool integration tests** (`cm-cli/tests/tools_integration.rs`, 744 LOC):

- Helper function `create_global()`: change `fn` to `async fn`, add `.await`.
- All test bodies: add `.await` after every `tools::cx_*()` call and every direct `store.*()` call.
- Tests already use `#[tokio::test(flavor = "multi_thread")]`. No annotation changes.

### 9.2 New Tests: Insta Snapshots (Item 4)

**Depends on:** Async migration complete (items 1+2).

Snapshot tests for MCP tool response format stability. Each test calls a tool handler and snapshots the JSON response with dynamic fields redacted.

**Cargo.toml changes:**

Workspace root `[workspace.dependencies]`:
```toml
insta = { version = "1", features = ["json", "redactions"] }
```

`crates/cm-cli/Cargo.toml` `[dev-dependencies]`:
```toml
insta = { workspace = true }
```

**New file:** `crates/cm-cli/tests/snapshot_tests.rs`

Coverage: one test per tool (9 tests). Redact `id`, `created_at`, `updated_at`, `content_hash`, `db_size_bytes`, and `exported_at` fields.

**Workflow:**
```sh
cargo insta test -p cm-cli          # Run tests, generate pending snapshots
cargo insta review                  # Review and approve each snapshot
# Commit snapshot files in crates/cm-cli/tests/snapshots/
```

### 9.3 New Tests: Subprocess MCP Protocol (Item 5)

**Depends on:** Async migration complete (items 1+2).

Spawn the compiled `cm serve` binary, pipe JSON-RPC messages to stdin, assert on stdout responses.

**No new dependencies.** `assert_cmd` (2.x), `predicates` (3.x), and `tempfile` (3.x) are already in cm-cli dev-dependencies. The subprocess tests use `std::process::Command` directly for stdin/stdout piping.

**New file:** `crates/cm-cli/tests/mcp_protocol_test.rs`

Tests:
1. `protocol_initialize_handshake` - Verify initialize response shape, serverInfo, instructions.
2. `protocol_tools_list` - Verify 9 tools returned with name, description, inputSchema.
3. `protocol_tools_call_cx_stats` - Call cx_stats, verify response content structure.
4. `protocol_unknown_method` - Verify -32601 error for bogus method.
5. `protocol_store_and_recall_roundtrip` - Store an entry, recall it, verify it appears.

Each test spawns an isolated server with `CM_DATA_DIR` set to a tempdir. `CM_DATA_DIR` is already supported by the config system (`cm-store/src/config.rs` line 66).

### 9.4 Independent Item: cargo-nextest (Item 3)

**Independent of async migration. Can be done first or in a separate commit.**

`justfile` line 8: replace `cargo test --workspace` with `cargo nextest run --workspace`.

New file `.config/nextest.toml`:
```toml
[profile.default]
retries = 0
slow-timeout = { period = "60s" }

[profile.ci]
retries = 2
fail-fast = true
```

---

## 10. Risk Assessment

### R1: All-or-Nothing Commit

**Risk:** The async migration touches 16 files and must be a single atomic commit. A partial migration does not compile.

**Mitigation:** The transformation is mechanical: add `async`, remove wrapper, add `.await`. Each file's changes are independent once the trait and impl are done. The blast radius is documented exhaustively in this spec. A competent implementor can complete all changes in one pass.

**Severity:** Low. The changes are syntactic, not semantic.

### R2: SQLite Single-Writer Constraint

**Risk:** Making the trait async might invite future callers to issue concurrent writes, which SQLite cannot handle.

**Mitigation:** The write pool is already capped at `max_connections(1)`. Concurrent write attempts queue at the pool level, serialized by sqlx. The 5-second `busy_timeout` handles any contention at the SQLite level. This constraint exists today and is unchanged by the migration.

**Severity:** None (pre-existing, already mitigated).

### R3: StdinLock !Send Constraint

**Risk:** `McpServer::run()` holds `StdinLock<'_>` across `.await` points. `StdinLock` is `!Send` (and `!` `'static`). If someone calls `tokio::spawn(server.run())`, it will fail to compile with errors on both `Send` and `'static`.

**Mitigation:** The MCP stdio protocol is single-client. Spawning the server on a separate task is architecturally wrong. The constraint is self-documenting via the type system. The existing code has a comment (lines 132-137) documenting why blocking stdin is safe. Update this comment to mention the `!Send` constraint explicitly.

**Validated:** Rust engineer confirmed this analysis. No action required beyond updating the doc comment.

**Severity:** Low. The compiler prevents misuse.

### R4: Test Helper Async Cascade

**Risk:** Making `create_global()` and `create_project_scope()` async cascades `.await` to every test that calls them.

**Mitigation:** Tests already use `#[tokio::test(flavor = "multi_thread")]`. Adding `.await` to helper calls is the same mechanical transformation as the main code. The total number of test files affected is 2.

**Severity:** Low. Mechanical.

### R5: Snapshot Test Fragility

**Risk:** Insta snapshot tests lock down JSON response format. Legitimate format changes require re-approving snapshots.

**Mitigation:** This is the point. Format stability is a feature, not a bug. Use `cargo insta review` to approve intentional changes. Redact dynamic fields (IDs, timestamps, hashes) so only structural changes trigger failures.

**Severity:** Not a risk; it is the desired behavior.

### R6: Subprocess Test Reliability

**Risk:** Subprocess tests spawn a real binary. They depend on the binary being compiled, the server starting quickly, and stdin/stdout being correctly piped.

**Mitigation:** `env!("CARGO_BIN_EXE_cm")` resolves the binary path at compile time. Each test creates an isolated tempdir for the database. The server starts in under 100ms (SQLite in-memory migration on an empty database). Stdin/stdout piping is straightforward with `std::process::Command`.

**Severity:** Low. Standard `assert_cmd` patterns.

---

## 11. Success Criteria

### 11.1 Core Migration (Items 1+2)

- [ ] `ContextStore` trait has `async` on all 17 methods
- [ ] `ContextStore` trait has `Send + Sync + 'static` bounds
- [ ] `ContextStore` doc comment reflects async design
- [ ] `CmStore` impl has zero `block_in_place` calls
- [ ] `CmStore` impl has zero `Handle::current().block_on()` calls
- [ ] `McpServer` is generic: `McpServer<S: ContextStore>`
- [ ] All 9 tool handlers accept `&impl ContextStore`
- [ ] `ensure_scope_chain` accepts `&impl ContextStore`
- [ ] `cmd_stats` accepts `&impl ContextStore`
- [ ] `main.rs` is the only file that references `CmStore` directly (plus test setup)
- [ ] `just check` passes (fmt + clippy with -D warnings)
- [ ] `just test` passes (all existing tests)
- [ ] No new dependencies added

### 11.2 cargo-nextest (Item 3)

- [ ] `just test` uses `cargo nextest run --workspace`
- [ ] `.config/nextest.toml` exists with default and ci profiles
- [ ] All tests pass under nextest

### 11.3 Snapshot Tests (Item 4)

- [ ] `insta` added to workspace dependencies with `json` and `redactions` features
- [ ] Snapshot test file covers all 9 tools
- [ ] Dynamic fields are redacted (IDs, timestamps, hashes, db_size_bytes)
- [ ] Snapshots committed in `crates/cm-cli/tests/snapshots/`
- [ ] `cargo insta test -p cm-cli` passes with no pending reviews

### 11.4 Subprocess MCP Protocol Tests (Item 5)

- [ ] 5 protocol tests: initialize, tools/list, tools/call, unknown method, store+recall roundtrip
- [ ] Each test uses an isolated tempdir via `CM_DATA_DIR`
- [ ] Tests run without manual server setup
- [ ] `just test` includes these tests and they pass

### 11.5 Final Verification

```sh
just check                                          # fmt + clippy clean
just test                                           # all tests pass
grep -r "block_in_place" crates/                    # zero results
grep -r "CmStore" crates/cm-cli/src/mcp/tools/      # zero results
grep -r "use cm_store::CmStore" crates/cm-cli/src/mcp/  # zero results (except possibly mod.rs test setup)
cargo insta test -p cm-cli                          # snapshot tests pass, no pending reviews
```

---

## Appendix A: Blast Radius Summary

| Crate | Files Changed | Nature of Changes |
|-------|--------------|-------------------|
| cm-core | 1 | Trait: add `async`, add `Send + Sync + 'static`, update doc comment |
| cm-store | 2 | Impl: remove 17x `block_in_place`, flatten async blocks. Tests: add `.await` |
| cm-cli | 13 | 9 handlers: `&CmStore` to `&impl ContextStore` + `.await`. McpServer: generic `<S>`. ensure_scope_chain: generic + async. cli/mod.rs: generic. Tests: `.await` |
| **Total** | **16** | No logic changes. No new dependencies. No Cargo.toml changes (for items 1+2). |

## Appendix B: Dependency Graph

```
cm-core  (no async deps, no I/O deps)
   |
   v
cm-store (sqlx, tokio in Cargo.toml for test, uses sqlx's async API directly)
   |
   v
cm-cli   (tokio runtime, clap, tracing; wires concrete CmStore to generic McpServer)
```

The migration does not change this dependency graph. cm-core remains zero-I/O. cm-store remains the only crate that touches sqlx. cm-cli remains the only crate that references the concrete `CmStore` type (in main.rs and tests).
