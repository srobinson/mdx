---
title: SurrealDB through the knowledge-matters lens
type: research
tags: [helioy, knowledge-matters, graph-database, rust, triple-store, surrealdb, property-graph, rdf]
summary: SurrealDB's RELATE model is a typed property graph backed by ordered KV scans; useful as inspiration for knowledge-matters key encoding, but BSL-licensed and far too heavy to embed.
status: active
source: github-researcher
confidence: high
created: 2026-04-28
updated: 2026-04-28
---

## Executive Summary

SurrealDB is a 243k-LoC Rust multi-model database with strong production engineering and a RELATE primitive that is essentially a typed property graph over an ordered key-value store. The RELATE model is closer to property graphs than RDF, and its key encoding (`*ns*db*tb~id<dir><ft><fk>`) is a clean reference design for a triple store backed by a sorted KV. Adopting SurrealDB as a backend (embedded or external) is the wrong call for knowledge-matters: the BSL 1.1 license blocks a "database service" use case at the edges, the surface area dwarfs the requirements, and the dependency cost is enormous. **Use as inspiration only.**

## Repo Health Stats

- **Stars**: 31,961. **Forks**: 1,252. **Open issues**: 592. **Open PRs**: 68. **Merged PRs**: 1,184. (`gh api repos/surrealdb/surrealdb`).
- **Created**: 2021-12-09. **Last push**: 2026-04-27. Active daily commits.
- **Contributors**: 178 (`gh api repos/surrealdb/surrealdb/contributors --paginate`).
- **License**: BSL 1.1, `LICENSE:1`. Single license file at root, all workspace crates inherit via `license-file.workspace = true` (`Cargo.toml:35`, `surrealdb/Cargo.toml`, `surrealdb/core/Cargo.toml`). **Change Date**: 2030-01-01. **Change License**: Apache 2.0. The earlier "BSL with Apache parts" framing is incorrect; the entire workspace is BSL 1.1 today and converts wholesale to Apache 2.0 in 2030. The Additional Use Grant restricts only third-party "Database Service" offerings; embedding inside an internal tool like knowledge-matters is permitted under the grant.
- **Workspace**: 18 crates (`Cargo.toml:1-25`). Key members: `surrealdb` (public client + embedded entry, `publish = true`), `surrealdb-core` (engine, `publish = true`), `surrealdb-server`, `surrealdb-ast`, `surrealdb-parser`, `surrealdb-token`, `surrealdb-types`, `surrealdb-common`. Plus subprojects `surrealml/`, `surrealism/` (a JS-runtime add-on).
- **Test footprint**: 1,622 `.surql` test files. `language-tests/tests/` partitions into `language/`, `parsing/`, `access/`, `api/`, `upgrade/`, `reproductions/`, `self_tests/`, `harness/`, `datasets/`. Plus Rust integration tests in `tests/` (cli, ws, http, graphql, ml, sdk).
- **CI**: 12 GitHub workflows (`ci.yml`, `bench.yml`, `coverage.yml`, `crud-bench.yml`, `fuzzing.yml`, `nix.yml`, `release.yml`, `scorecard.yml`, `supply-chain.yml`, `codeql.yml`, plus PR labeling and automoderator). The `ci.yml` workflow defines ~36 jobs across multi-arch builds, lint, tests, coverage, fuzzing.
- **Toolchain**: Rust 1.91 stable, edition 2024 (`rust-toolchain.toml`, `Cargo.toml:30`). Resolver 3.
- **Honest calibration**: This is a production database. The single author who built graphify or claudex would not have written this in a year. Reviewing it on the same letter scale as those probes is category-error territory.

## Verdict for Knowledge-Matters: Inspiration Only

**Pick: Inspiration only.** Lift the key-encoding pattern, the RELATE syntax shape, and the schemafull/schemaless toggle. Do not embed, do not run as external server.

Defense:

1. **License frames the decision.** BSL 1.1 is fine for embedding inside a personal tool; the Additional Use Grant explicitly permits embedded use that does not provide schemas/tables to third parties. But it prevents knowledge-matters from ever being offered as a Helioy hosted service to external users without a commercial license, and that is a constraint Stuart should not bake in for an early experimental component.

2. **Surface mismatch is enormous.** knowledge-matters wants a triple store. SurrealDB ships a SQL-shaped query language with a parser (`surrealdb/parser/`, `surrealdb/core/src/syn/`), an AST crate (`surrealdb/ast/`), authentication and IAM (`surrealdb/core/src/iam/`), four KV backends (`surrealdb/core/src/kvs/{mem,rocksdb,indxdb,surrealkv,tikv}`), GraphQL (`surrealdb/core/src/gql/`), HTTP and WebSocket servers (`surrealdb/core/src/http/`, `surrealdb/core/src/rpc/`), buckets, change feeds, ML model embedding (`surrealml/`), and a JS scripting runtime (`surrealism/`). Pulling `surrealdb-core` as a dependency drags rocksdb, tokio-tungstenite, reqwest, and the full IAM stack just to get RELATE.

3. **The dependency tax dominates.** `Cargo.lock` is 237kB. Compile time on a fresh build is well into minutes even with `kv-mem` only. For a primary-memory layer that will be queried inside Helix at every retrieval, that startup and link cost is wrong-shaped.

4. **External-server is the wrong fit for Helioy.** The other matters components (markdown-matters, context-matters, attention-matters, frontmatter-matters) are in-process libraries or sqlite-backed sidecars. Adding a long-running daemon with auth and TLS for the relationship store breaks the deploy story.

## RDF vs Lighter Triples: Evidence

SurrealDB's RELATE is **typed labelled edges with arbitrary record bodies** plus directional traversal (`->`, `<-`, `<->`). The Rust types in `surrealdb/core/src/expr/dir.rs:18-26` define `Dir::{In, Out, Both}` exactly mirroring the SurrealQL operators. The `RelateStatement` (`surrealdb/core/src/expr/statements/relate.rs:17-31`) takes a `from`, a `to`, and a `through` table, plus arbitrary `data` attached to the edge. Edges are first-class records (the `knows:[person:tobie, person:jaime]` composite ID in `language-tests/tests/language/graph/upsert_relate_complex_array_traversal.surql`) and can themselves be queried, indexed, and have permissions. `TableType::Relation` (`surrealdb/core/src/catalog/table.rs:151-156`) lets you constrain `RELATION IN person OUT person ENFORCED`, with `enforced` toggling referential integrity (`relation.surql:18-21`).

This is property graph semantics, not RDF. RDF triples are `<s, p, o>` with predicates as URIs in a global namespace and no native edge bodies; SPARQL traversal is pattern-matching, not directional walks. SurrealDB's edges carry record IDs, structured data, schemafull constraints, and permissions; that is Neo4j/TigerGraph territory.

**Implication for knowledge-matters**: if Stuart adopts the SurrealDB-shaped data model (even without depending on the crate), he is implicitly choosing property graph over RDF. Given the existing primitives already on the day-one list (confidence-tagged edges with `EXTRACTED`/`INFERRED`/`AMBIGUOUS`, scope hierarchy, edge bodies for provenance), property graph is the right answer. Confidence tags and scope are edge properties, which is awkward in RDF (requires reification or RDF-star) and natural in property graphs. The case for RDF/SPARQL would have been: (1) federation across external knowledge graphs (Wikidata, DBpedia), or (2) reasoning over OWL ontologies. Neither is on the knowledge-matters roadmap. **Drop RDF/SPARQL. Build a typed-predicate property graph with confidence and scope as edge attributes.**

## Three Primitives That Transfer

### 1. Composite key encoding for graph edges

`surrealdb/core/src/key/graph/mod.rs:122-145` defines the on-disk edge layout:

```rust
pub(crate) struct Graph<'a> {
    __: u8, _a: u8,
    pub ns: NamespaceId,    // namespace
    _b: u8,
    pub db: DatabaseId,     // database
    _c: u8,
    pub tb: Cow<'a, TableName>,  // source table
    _d: u8,
    pub id: RecordIdKey,    // source record id
    pub eg: Dir,            // direction (In/Out/Both)
    pub ft: Cow<'a, TableName>,  // edge predicate (the "through" table)
    pub fk: Cow<'a, RecordIdKey>,  // target record id
}
```

Encoded with `storekey` (a sort-preserving binary encoder, `surrealdb/core/src/key/graph/mod.rs:3`), this gives prefix-scannable layers: by source record (`Prefix`, lines 16-43), by source+direction (`PrefixEg`, 45-77), by source+direction+predicate (`PrefixFt`, 79-120). For knowledge-matters on top of SQLite or a sled/redb backend, this layout is directly transferable: scope becomes the namespace prefix, predicate-typed edges scan in O(log n) with predicate filtering for free, and confidence can be a prefix between predicate and target if you want range scans by confidence band. Cite this layout in the knowledge-matters design doc.

### 2. Schemafull/schemaless flag at table granularity

`surrealdb/core/src/catalog/table.rs:51` `pub(crate) schemafull: bool` plus `surrealdb/core/src/expr/statements/define/table.rs:42` `pub full: bool` and `pub permissions: Permissions`. SurrealDB lets you mark some tables as schemafull (every field declared, type-checked) and others schemaless (free-form). For knowledge-matters this maps cleanly onto the confidence-tag axis: predicate types extracted from deterministic sources (e.g., AST imports from frontmatter-matters) are `EXTRACTED` and live in schemafull predicate tables with declared subject/object types. LLM-inferred predicates are `INFERRED`/`AMBIGUOUS` and live in schemaless predicate tables with free-form arguments. The schemafull/less choice is per-predicate, not per-store. Worth lifting.

### 3. Permissions/Access at table+operation granularity

`surrealdb/core/src/catalog/schema/mod.rs:91-96`:

```rust
pub struct Permissions {
    pub(crate) select: Permission,
    pub(crate) create: Permission,
    pub(crate) update: Permission,
    pub(crate) delete: Permission,
}
```

Each operation gets its own predicate expression (`Permission::Specific(expr)` or `None`/`Full`). For knowledge-matters' scope hierarchy (global > project > repo > session), this is the right shape: the scope check is a predicate on the row, not a separate table per scope, and the four CRUD axes let you mark, say, INFERRED edges as creatable by Helix at session scope but not promotable to global without an explicit confirmation. SurrealDB also has `DEFINE SCOPE` (now superseded by `DEFINE ACCESS ... TYPE RECORD` per `surrealdb/core/src/expr/statements/define/access.rs`) but that is for user/auth scopes, not for the data hierarchy Helioy needs. Lift the operation-keyed `Permissions` shape, skip the access-token machinery.

## What Does NOT Transfer

Itemized skip list:

- **Parser, AST, lexer**: 4 crates totalling tens of thousands of lines for a SurrealQL surface knowledge-matters does not need (`surrealdb/{ast,parser,token}/`, `surrealdb/core/src/syn/`, `surrealdb/core/src/sql/`).
- **HTTP and WebSocket servers**: `surrealdb/core/src/http/`, `surrealdb/core/src/rpc/`. Knowledge-matters is in-process.
- **IAM, JWT, JWKS, bearer access**: `surrealdb/core/src/iam/`, `surrealdb/core/src/expr/statements/define/access.rs`. Helioy auth is "Stuart's laptop".
- **Cluster mode, distributed timestamps, HLC**: `surrealdb/core/src/dbs/node.rs`, `surrealdb/core/src/kvs/clock.rs`, `surrealdb/core/src/kvs/timestamp.rs`. Single-node knowledge-matters has no need.
- **Multiple KV backends**: `surrealdb/core/src/kvs/{rocksdb,tikv,indxdb,surrealkv,mem}`. Pick one (sqlite or redb) and commit.
- **Live queries (change subscriptions)**: `surrealdb/core/src/expr/statements/live.rs:15-28`. Tempting because Helix could in principle react to graph mutations, but Helioy doesn't have that loop wired yet and the subscription machinery (`SubscriptionDefinition`, `Notification` channel, capture-by-parameter walking via `Variables`) is heavy. Defer.
- **GraphQL endpoint**: `surrealdb/core/src/gql/`. No use case.
- **Buckets and BLOB storage**: `surrealdb/core/src/buc/`. No use case.
- **Change feeds**: per-table CDC. No consumer.
- **SurrealML and Surrealism (JS scripting)**: entire `surrealml/` and `surrealism/` subprojects. No.
- **Fuzz infrastructure, supply-chain audit, codecov, scorecard CI**: SurrealDB's CI shape is right for a database serving paying customers, not for a Helioy component. Use it as a north star for what mature Helioy CI would look like, do not copy.

## Grade

**Off the Helioy review scale.** SurrealDB is a different artifact class from graphify, claudex, notebooklm-py, and the other reviewed repos. It is a production multi-tenant database with 178 contributors, a commercial entity, and a 4-year build history. The right calibration is "this is what mature Rust database engineering looks like" rather than a letter grade.

If forced onto the scale: the engineering quality, test footprint, and ergonomics of the embedded API (`surrealdb/src/lib.rs`, `surrealdb/src/engine/local/native.rs`) are A or A+. The relevance to knowledge-matters as a borrowable artifact is C, because the dependency cost and license drag make borrowing more code than the three primitives above a bad trade. So grade is **A for what it is, C as a Helioy borrow-target**, and the latter is what matters here.

## Sources Consulted

- `README.md`, `LICENSE`, `Cargo.toml`, `rust-toolchain.toml`, `CLAUDE.md`, `CONTRIBUTING.md`.
- `surrealdb/core/src/expr/statements/relate.rs`, `surrealdb/core/src/expr/dir.rs`.
- `surrealdb/core/src/key/graph/mod.rs`.
- `surrealdb/core/src/catalog/table.rs`, `surrealdb/core/src/catalog/schema/mod.rs`.
- `surrealdb/core/src/expr/statements/define/{table,access,live}.rs`.
- `surrealdb/core/src/kvs/{api.rs,ds.rs,mod.rs}`.
- `surrealdb/src/{lib.rs,engine/local/mod.rs,engine/local/native.rs,method/mod.rs}`.
- `language-tests/tests/language/graph/upsert_relate_complex_array_traversal.surql`, `language-tests/tests/language/statements/define/table/relation.surql`.
- `.github/workflows/ci.yml`.
- `gh api repos/surrealdb/surrealdb` for stars, forks, issues, PRs, contributors.

## Open Questions

- Is there a permissive-licensed Rust property-graph crate worth comparing? `cozodb` (MPL 2.0, embedded, Datalog-shaped) is the closest peer worth a separate review before committing.
- Does the SurrealDB key encoding survive concurrent writes cleanly under sqlite, or does the prefix layout assume an LSM-style range scanner? Worth a 1-day spike if knowledge-matters adopts the layout.
- Is the schemafull/less-per-table dichotomy the right abstraction for confidence tags, or should confidence be modelled as a single edge attribute with a denormalized index? Bench both before committing.
