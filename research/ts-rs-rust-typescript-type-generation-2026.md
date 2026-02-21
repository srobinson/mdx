---
title: "ts-rs: Rust to TypeScript Type Generation Assessment"
type: research
tags: [rust, typescript, ts-rs, code-generation, axum, fullstack]
summary: "ts-rs is a mature, actively maintained crate (1.7k stars, 5.6M downloads) that generates TypeScript interfaces from Rust structs/enums via derive macros. Test-time generation, strong serde compatibility, and good type coverage make it a solid choice for Axum + React/Vite fullstack projects, with a few workspace and enum-related gotchas."
status: active
source: deep-research
confidence: high
created: 2026-03-19
updated: 2026-03-19
---

## Executive Summary

ts-rs is the dominant crate for generating TypeScript type definitions from Rust structs and enums. At 1,733 GitHub stars, 5.6M total downloads, and active maintenance (last push March 8, 2026; v12.0.1 released January 31, 2026), it is a production-grade tool. The derive macro approach with serde attribute compatibility means adding `#[derive(TS)]` to existing serde-annotated types produces correct TypeScript output with near-zero configuration. The main architectural constraint is that generation happens at test time (`cargo test`), not compile time, due to Rust proc macro limitations.

## Detailed Findings

### 1. Current State and Maintenance

| Metric | Value |
|---|---|
| GitHub stars | 1,733 |
| Total downloads | 5,635,471 |
| Recent downloads (90 day) | 2,418,332 |
| Latest version | 12.0.1 (2026-01-31) |
| Open issues | 18 (32 including PRs) |
| MSRV | Rust 1.88.0 |
| License | MIT |
| Versions published | 49 |
| Last push | 2026-03-08 |

Release cadence over the past two years: v8.1.0 (2024-03), v9.0.0 (2024-06), v10.0.0 (2024-09), v10.1.0 (2024-12), v11.0.0 (2025-06), v11.1.0 (2025-10), v12.0.0 (2026-01). Roughly one minor/major release every 3-4 months. The maintainer (NyxCode at Aleph Alpha) is responsive; a collaborator (gustavo-shigueo) handles triage actively.

### 2. How It Works

ts-rs exposes a single trait `TS` with a derive macro. The core mechanism:

1. Add `#[derive(TS)]` and `#[ts(export)]` to a struct or enum.
2. The derive macro generates a hidden test function that writes TypeScript to disk.
3. Running `cargo test` triggers all exports. Files land in `TS_RS_EXPORT_DIR` (default: `./bindings/`).

```rust
#[derive(Serialize, Deserialize, TS)]
#[ts(export)]
struct User {
    user_id: i32,
    first_name: String,
    last_name: String,
}
// Generates: export type User = { user_id: number, first_name: string, last_name: string };
```

**Why test-time?** Rust proc macros evaluate before compilation completes, so file I/O during macro expansion is not possible. The `#[ts(export)]` attribute generates a `#[test]` that calls `TS::export()`. This is a fundamental architectural decision, not a temporary limitation.

**Programmatic alternative:** `TS::export_all()`, `TS::export()`, and `TS::export_to_string()` allow generation outside of tests (e.g., from a dedicated binary or build script that instantiates the types).

### 3. Type Mappings

#### Primitives and Standard Library

| Rust type | TypeScript output |
|---|---|
| `bool` | `boolean` |
| `i8`-`i32`, `u8`-`u32`, `f32`, `f64` | `number` |
| `i64`, `u64`, `i128`, `u128` | `bigint` (configurable via `TS_RS_LARGE_INT`) |
| `String`, `&str` | `string` |
| `()` | `null` |
| `Option<T>` | `T \| null` |
| `Vec<T>`, `[T; N]` | `Array<T>` |
| `HashMap<K, V>`, `BTreeMap<K, V>` | `{ [key in K]?: V }` (v12+) |
| `HashSet<T>`, `BTreeSet<T>` | `Array<T>` |
| `Box<T>`, `Arc<T>`, `Rc<T>`, `Cow<T>` | transparent (unwraps to `T`) |
| `(A, B, C)` | `[A, B, C]` (up to 10-element tuples) |

#### Feature-gated External Types

| Feature flag | Rust type | TypeScript output |
|---|---|---|
| `chrono-impl` | `DateTime<Utc>`, `NaiveDateTime`, `NaiveDate`, etc. | `string` |
| `uuid-impl` | `uuid::Uuid` | `string` |
| `url-impl` | `url::Url` | `string` |
| `bigdecimal-impl` | `BigDecimal` | `string` |
| `semver-impl` | `semver::Version` | `string` |
| `indexmap-impl` | `IndexMap<K,V>` / `IndexSet<T>` | `Record<K,V>` / `Array<T>` |
| `bytes-impl` | `Bytes` | `Array<number>` |
| `ordered-float-impl` | `OrderedFloat<f64>` | `number` |

### 4. Serde Compatibility

With the `serde-compat` feature (enabled by default), serde attributes are automatically recognized. Supported attributes:

- `rename`, `rename_all` (all inflection patterns: `camelCase`, `snake_case`, `kebab-case`, `PascalCase`, `SCREAMING_SNAKE_CASE`, `lowercase`, `UPPERCASE`)
- `rename_all_fields` (applies field renaming across all enum variants)
- `tag`, `content` (internally tagged, adjacently tagged enums)
- `untagged`
- `skip`, `skip_serializing`, `skip_serializing_if` (caveat: `skip_serializing` requires paired `#[serde(default)]`)
- `flatten`
- `default`
- `try_from`, `into` (for newtype patterns like `ScopePath`)

### 5. Enum Handling

#### Simple C-like enums with `rename_all`

```rust
#[derive(Serialize, Deserialize, TS)]
#[serde(rename_all = "snake_case")]
#[ts(export)]
pub enum EntryKind {
    Fact,
    Decision,
    Preference,
    Lesson,
}
// Generates: export type EntryKind = "fact" | "decision" | "preference" | "lesson";
```

This is the default output. The `serde(rename_all)` attribute is respected automatically.

#### TypeScript enum output (optional)

If you prefer `export enum` instead of a string union, use `#[ts(repr(enum))]`:

```rust
#[derive(TS)]
#[ts(export, repr(enum))]
#[serde(rename_all = "snake_case")]
pub enum EntryKind { Fact, Decision, ... }
// Generates: export enum EntryKind { Fact = "fact", Decision = "decision", ... }
```

**Note:** There is an open race condition bug (#479, March 2026) when multiple `export enum` types target the same output file. The sorting logic assumed `export type` prefix, breaking ordering for `export enum`. Workaround: export to separate files per type.

#### Tagged enums

```rust
#[derive(TS)]
#[serde(tag = "type")]
enum Message {
    Request { id: String, method: String },
    Response { id: String, status: u8 },
}
// Generates: { "type": "Request", id: string, method: string } | { "type": "Response", id: string, status: number }
```

Adjacently tagged (`tag` + `content`) and `untagged` enums are also supported. Per-variant `#[ts(untagged)]` is supported for mixed tagging.

### 6. Nested Types and Imports

ts-rs automatically resolves dependencies. When `Entry` contains `EntryMeta`, and both derive `TS` with `#[ts(export)]`, the generated `Entry.ts` file includes:

```typescript
import type { EntryMeta } from "./EntryMeta";
```

The `dependencies()` trait method recursively walks all referenced types. All transitive dependencies are exported alongside the root type.

The `#[ts(inline)]` attribute expands a nested type inline instead of importing it. The `#[ts(flatten)]` attribute merges a nested struct's fields into the parent (equivalent to serde's `flatten`).

**Gotcha:** Flattening a zero-field struct panics with "cannot be flattened" (open bug #473, v12.0.1). Flattening externally tagged enums with unit variants produces nonsensical output like `{ biz: number } & 'Foo'`.

### 7. Output Path Configuration

**Environment variable (recommended for workspaces):**

In `.cargo/config.toml` at the workspace root:

```toml
[env]
TS_RS_EXPORT_DIR = { value = "crates/cm-web/frontend/src/api/generated/", relative = true }
```

The `relative = true` makes the path relative to the directory containing `.cargo/config.toml` (the workspace root).

**Per-type override:**

```rust
#[ts(export, export_to = "models/")]   // subdirectory within TS_RS_EXPORT_DIR
#[ts(export, export_to = "Entry.ts")]  // explicit filename within TS_RS_EXPORT_DIR
```

Path behavior: trailing `/` = directory (type name becomes filename), no trailing `/` = treat as filename.

**Additional env vars:**

- `TS_RS_IMPORT_EXTENSION`: file extension for import statements (e.g., `.js` for ESM)
- `TS_RS_LARGE_INT`: mapping for `i64`/`u64`/`i128`/`u128` (default: `bigint`, alternative: `number`)

### 8. Workspace Integration

**The workspace path problem (issue #71, closed):** In a Cargo workspace, each crate's `CARGO_MANIFEST_DIR` differs. Without a shared `TS_RS_EXPORT_DIR`, types from different crates export to different `./bindings/` directories relative to each crate, breaking cross-crate import paths.

**Solution:** Set `TS_RS_EXPORT_DIR` in the workspace-level `.cargo/config.toml` with `relative = true`. All crates in the workspace then export to the same directory, and import paths resolve correctly.

**For the context-matters project specifically:** The `cm-core` crate defines domain types. A workspace-level config pointing to `crates/cm-web/frontend/src/api/generated/` would centralize all exports. Run `cargo test --workspace` to generate all bindings.

### 9. Build Integration Patterns

**Pattern A: cargo test as a generation step (standard)**

```bash
# In Justfile or Makefile
generate-types:
    cargo test --workspace  # generates .ts files as side effect
    # optionally: npx prettier --write crates/cm-web/frontend/src/api/generated/
```

**Pattern B: Dedicated binary**

```rust
// crates/cm-web/src/bin/generate_types.rs
fn main() {
    Entry::export_all().unwrap();
    // ... other types
}
```

**Pattern C: cargo watch for dev**

```bash
cargo watch -w crates/cm-core/src -s "cargo test --workspace && echo 'Types regenerated'"
```

**CI integration:** Run `cargo test`, then `git diff --exit-code crates/cm-web/frontend/src/api/generated/` to catch uncommitted type changes. This is a common CI gate pattern.

### 10. Specific Compatibility Assessment for context-matters Types

| Type | ts-rs compatibility | Notes |
|---|---|---|
| `ScopeKind` (enum, `serde(rename_all = "snake_case")`) | Full | Generates `"global" \| "project" \| "repo" \| "session"` |
| `EntryKind` (enum, `serde(rename_all = "snake_case")`) | Full | Generates `"fact" \| "decision" \| ...` |
| `Confidence` (enum, `serde(rename_all = "snake_case")`) | Full | Generates `"high" \| "medium" \| "low"` |
| `ScopePath` (newtype, `serde(try_from = "String", into = "String")`) | Needs `#[ts(as = "String")]` or `#[ts(type = "string")]` | Serde serializes as string, but ts-rs does not auto-detect `try_from`/`into` for newtype transparency |
| `Entry` (struct with `Uuid`, `DateTime<Utc>`, nested types) | Full with feature flags | Requires `chrono-impl` and `uuid-impl` features |
| `EntryMeta` (struct with `flatten`, `skip_serializing_if`, `HashMap<String, Value>`) | Partial concern | `serde_json::Value` needs `serde-json-impl` feature. The `#[serde(flatten)]` on `extra: HashMap<String, Value>` will add `& { [key: string]: ... }` intersection |
| `NewEntry`, `UpdateEntry` | Full | Standard structs with `Option` fields |
| `PagedResult<T>` (generic struct) | Full | ts-rs handles generics |
| `MutationAction`, `MutationSource`, `RelationKind` (enums) | Full | Same pattern as EntryKind |

**Key consideration for `EntryMeta.extra`:** The `#[serde(flatten)]` on `extra: HashMap<String, serde_json::Value>` will generate an intersection type. Since `serde_json::Value` maps to `JsonValue` (with the `serde-json-impl` feature), this produces `{ tags: Array<string>, confidence: ... } & { [key: string]: JsonValue }`. This is semantically correct but may surprise frontend consumers. Consider using `#[ts(skip)]` on `extra` if the frontend does not need arbitrary extension fields.

### 11. Known Limitations and Gotchas

1. **Test-time generation only.** Cannot generate at compile time. You must run `cargo test` (or use the programmatic API) to produce `.ts` files.

2. **HashMap representation changed in v12.** `HashMap<K, V>` now generates `{ [key in K]?: V }` (optional values). This can cause `Object.values()` to return `T | undefined` in TypeScript. A compat flag `TS_RS_USE_V11_HASHMAP` exists temporarily.

3. **Race condition with `export enum` in shared files** (issue #479, open). Multiple enum types exported to the same `.ts` file may appear in nondeterministic order. The sorting logic assumes `export type` prefix.

4. **Flatten panics on zero-field structs** (issue #473, open). `#[serde(flatten)]` on an empty struct causes a runtime panic during export.

5. **`optional_fields` does not compile with generic parameters** (issue #476, open). Using `#[ts(optional_fields)]` on a generic struct fails to compile.

6. **`skip_serializing` without `default` is a silent correctness issue.** The field is omitted from TypeScript, but without `#[serde(default)]`, deserialization will fail if the field is missing. ts-rs mirrors serde's behavior here.

7. **Newtype wrappers with custom serde (`try_from`/`into`) need manual annotation.** ts-rs does not auto-detect `serde(try_from = "String")` on newtypes. Use `#[ts(as = "String")]` or `#[ts(type = "string")]`.

8. **No compile-time type safety guarantee.** ts-rs generates types that *should* match serde output, but there is no formal verification. If you use `#[ts(type = "...")]` overrides, you can introduce drift.

9. **MSRV 1.88.0.** Requires a recent Rust toolchain.

### 12. Community Sentiment

Direct Reddit discussions about ts-rs proved difficult to find (no results from `site:reddit.com` queries). The community signal comes from:

- **GitHub issues:** Active, responsive maintenance. Issues are triaged within days. The maintainers engage substantively with bug reports and feature requests.
- **Download trajectory:** 2.4M recent downloads (90-day) on a crate with 5.6M lifetime suggests accelerating adoption, not plateau.
- **Blog coverage:** Multiple independent engineering blogs (Hoeser.dev, cetra3, imfeld.dev, valand.dev) discuss ts-rs as the go-to solution for Rust-to-TypeScript type sharing. The Hoeser.dev post specifically describes using ts-rs with an Axum backend.
- **Ecosystem position:** ts-rs is consistently mentioned alongside `specta` as the two main derive-macro approaches. `specta` (from the Tauri ecosystem) offers more features (multi-file export, namespace support, branded types) but is still pre-2.0 with a more complex API. For straightforward "generate .ts files from Rust structs," ts-rs is the simpler, more established choice.

### 13. Alternatives Considered

| Crate | Stars | Approach | Tradeoff vs ts-rs |
|---|---|---|---|
| **specta** | ~2k | Derive macro, multi-language export | More powerful (namespaces, branded types, dependent type export), but pre-2.0 alpha, more complex setup |
| **schemars** + json-schema-to-typescript | ~1.2k | JSON Schema intermediate | Two-step pipeline, handles arbitrary JSON Schema consumers, but requires Node tooling |
| **typeshare** (1Password) | ~2.4k | Static analysis of Rust files | No derive macro needed, but cannot handle types from external crates, less accurate |
| **ts-bind** | small | Derive macro, compile-time | Less mature, smaller community |

## Sources Consulted

### GitHub
- [Aleph-Alpha/ts-rs repository](https://github.com/Aleph-Alpha/ts-rs) (1,733 stars)
- [ts-rs Wiki: Deriving the TS trait](https://github.com/Aleph-Alpha/ts-rs/wiki/Deriving-the-TS-trait) (comprehensive attribute reference)
- [ts-rs Wiki: Feature flags](https://github.com/Aleph-Alpha/ts-rs/wiki/Feature-flags) (type mapping tables)
- [Issue #479: Race condition with enum export to same file](https://github.com/Aleph-Alpha/ts-rs/issues/479) (open, March 2026)
- [Issue #473: Flatten panics on zero-field struct](https://github.com/Aleph-Alpha/ts-rs/issues/473) (open, Feb 2026)
- [Issue #476: optional_fields with generics](https://github.com/Aleph-Alpha/ts-rs/issues/476) (open, Feb 2026)
- [Issue #442: HashMap representation change](https://github.com/Aleph-Alpha/ts-rs/issues/442) (closed, v12 migration)
- [Issue #71: Workspace import path resolution](https://github.com/Aleph-Alpha/ts-rs/issues/71) (closed, solved via TS_RS_EXPORT_DIR)
- [Issue #23: C-like enum as TypeScript enum](https://github.com/Aleph-Alpha/ts-rs/issues/23) (closed, implemented via `repr(enum)`)
- [ts-rs example/src/lib.rs](https://github.com/Aleph-Alpha/ts-rs/blob/main/example/src/lib.rs) (usage patterns)
- [ts-rs releases](https://github.com/Aleph-Alpha/ts-rs/releases) (version history)

### Documentation
- [docs.rs/ts-rs](https://docs.rs/ts-rs/latest/ts_rs/) (API reference)
- [docs.rs TS trait](https://docs.rs/ts-rs/latest/ts_rs/trait.TS.html) (blanket implementations, trait methods)
- [crates.io/crates/ts-rs](https://crates.io/crates/ts-rs) (download statistics)

### Blog Posts and Articles
- [Hoeser.dev: Using ts-rs bindings in TypeScript](https://www.hoeser.dev/blog/2024-05-18-using-ts-rs-bindings/) (Axum + Lit frontend, Rollup bundling of generated types)
- [cetra3: Publishing Rust types to a TypeScript frontend](https://cetra3.github.io/blog/sharing-types-with-the-frontend/) (survey of approaches: ts-rs, schemars, OpenAPI, GraphQL)
- [imfeld.dev: Synchronizing Rust Types with Typescript](https://imfeld.dev/writing/generating_typescript_types_from_rust) (schemars-based approach, useful for comparison)
- [Rustfinity: Generate TypeScript Bindings for Rust](https://www.rustfinity.com/blog/generate-typescript-bindings-for-rust) (ts-bind guide)

### Alternatives
- [specta-rs/specta](https://github.com/specta-rs/specta) (pre-2.0, multi-language export)

## Source Quality Assessment

**Confidence: High.** Primary sources (GitHub repo, docs.rs, crates.io API) provide authoritative data on maintenance status, API surface, and known bugs. The wiki documentation is detailed and current. Blog posts from independent authors provide corroboration of real-world usage patterns. The main gap is Reddit community discussion, which yielded zero results across multiple query formulations; this likely reflects fragmentation of the Rust web-dev community across Discord and GitHub rather than negative sentiment.

## Open Questions

1. **`serde_json::Value` with flatten in ts-rs v12.** The exact TypeScript output for `EntryMeta.extra` (a flattened `HashMap<String, serde_json::Value>`) needs hands-on verification. The `serde-json-impl` feature should handle `Value`, but the intersection type with optional HashMap keys may produce unwieldy TypeScript.

2. **ESM import extensions.** If the Vite frontend uses ESM imports, the `import-esm` feature (or `TS_RS_IMPORT_EXTENSION` env var) may be needed to append `.js` to generated import paths. Depends on the tsconfig/Vite resolution strategy.

3. **Specta comparison depth.** Specta's 2.0 release (in progress) may offer advantages for namespace-based export and branded newtypes. Worth revisiting if ts-rs limitations become blocking.

## Actionable Takeaways

### Recommended setup for context-matters

1. **Add ts-rs dependency to `cm-core`:**
   ```toml
   [dependencies]
   ts-rs = { version = "12.0", features = ["chrono-impl", "uuid-impl", "serde-json-impl"] }
   ```

2. **Configure workspace export path** in `.cargo/config.toml`:
   ```toml
   [env]
   TS_RS_EXPORT_DIR = { value = "crates/cm-web/frontend/src/api/generated/", relative = true }
   ```

3. **Annotate domain types** in `cm-core/src/types.rs`:
   ```rust
   #[derive(Debug, Clone, Serialize, Deserialize, TS)]
   #[serde(rename_all = "snake_case")]
   #[ts(export)]
   pub enum EntryKind { ... }

   #[derive(Debug, Clone, Serialize, Deserialize, TS)]
   #[ts(export)]
   pub struct Entry { ... }

   // For ScopePath newtype:
   #[derive(Debug, Clone, Serialize, Deserialize, TS)]
   #[serde(try_from = "String", into = "String")]
   #[ts(export, as = "String")]  // <-- manual override needed
   pub struct ScopePath(String);
   ```

4. **Add a just recipe:**
   ```
   generate-types:
       cargo test --workspace
   ```

5. **CI gate:** After `cargo test`, run `git diff --exit-code crates/cm-web/frontend/src/api/generated/` to catch stale types.

6. **Consider `#[ts(skip)]` on `EntryMeta.extra`** if the frontend does not consume arbitrary extension fields, to avoid the flattened HashMap intersection type.
