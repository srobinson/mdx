---
title: cozodb/cozo through the Helioy lens for knowledge-matters
type: research
tags: [helioy, knowledge-matters, datalog, embedded-database, graph-database, cozodb, surrealdb-comparison]
summary: Cozo is MPL-2.0 and clean but effectively abandoned (last commit 2024-12, community fork also dead, open issue "Is cozo still being maintained?" with mourning emoji). Inspiration only. Build the edge layer.
status: active
source: github-researcher
confidence: high
created: 2026-04-28
updated: 2026-04-28
---

# cozodb/cozo, Helioy lens for knowledge-matters

## Verdict

**Inspiration only. Grade: B-. Skip as a dependency.**

Cozo clears the licensing bar that SurrealDB failed (MPL 2.0, no BSL drag). The crate boundary is clean, the storage trait is small, the sqlite backend matches the Helioy sidecar convention. On any other day this would be a serious embedded-backend candidate.

It is not. The project is effectively abandoned. Last commit on `main` is 2024-12-04. Last commit on the community fork (`cozo-community/cozo`) is 2024-12-12. An open issue from 2026-04-10 titled "Is cozo still being maintained?" has nine comments, all 🕯️ emoji, no maintainer reply. Multiple unmerged PRs sit waiting. A `cargo update` regression has been open since 2025-09. Adopting a 73k-LoC graph engine that nobody is maintaining is worse than the BSL drag, because at least SurrealDB has a company shipping releases.

The right move is to lift two or three primitives, build the edge layer on sqlite using the SurrealDB shapes already chosen, and skip Datalog entirely.

## Repo health stats

- **Stars / age**: 3,975 stars, created 2022-10-14, primary author Ziyang Hu (60 of ~85 commits, 70%). Single-author production database. ([Cargo.toml authors line], `git shortlog -sn`)
- **License**: MPL-2.0 across the workspace. Confirmed in `cozo-core/Cargo.toml:9` and the per-file headers (every `.rs` file in `cozo-core/src/` carries the MPL block, e.g. `cozo-core/src/storage/mod.rs:1-7`). No surprise dual-licensing.
- **Workspace layout**: 10 crates in `Cargo.toml:3-15`. `cozo-core` is the engine; `cozo-bin` is the standalone server; `cozo-lib-{c,java,wasm,swift,python,nodejs}` are FFI shims; `cozorocks` is the RocksDB C++ bridge.
- **Core LoC**: 73,780 lines across 104 `.rs` files. `cozo-core` alone is ~50k. Storage trait is 165 lines (`cozo-core/src/storage/mod.rs`). HNSW is 1,035 lines (`cozo-core/src/runtime/hnsw.rs`). Tests in `cozo-core/src/runtime/tests.rs` total 1,614 lines with 72 `#[test]` functions.
- **CI**: single workflow `.github/workflows/build.yml`. Build/test, no fuzz, no benchmark gating.
- **Liveliness**: **dead**. Last commit on `cozodb/cozo` main: 2024-12-04. Last commit on `cozo-community/cozo` fork: 2024-12-12. Issue #301 (2026-04-10) "Is cozo still being maintained?" is unanswered; commenters Madd0g, chuanqisun, xpe, iron-apeiron, tompassarelli all left only 🕯️. Issue #298 (2025-09) reports `cargo update` breaks the build, unfixed.
- **Dependency depth**: 311 transitive crates with `--no-default-features --features storage-sqlite`, 410 with default features. The minimal cut still pulls `pest`, `pest_derive`, `miette`, `ndarray`, `jieba-rs`, `aho-corasick`, `rust-stemmers`, `rmp-serde`. Cozo cannot be built without the Datalog parser and the FTS tokenizers, even when knowledge-matters would use neither.

## Architectural fit for knowledge-matters

**Verdict: inspiration only.** The reasoning, ordered by what kills the candidacy first:

1. **Abandonment risk dominates.** The whole point of preferring an embedded engine over building one is to inherit a maintained transactional KV layer with an MVCC story. Cozo's MVCC trait and stratified Datalog evaluator are real engineering, but if the upstream is dead, Helioy inherits the maintenance burden anyway. SurrealDB had a worse license; Cozo has a worse pulse.
2. **Datalog is a query surface knowledge-matters does not want.** Cozo deliberately rejects the property-graph model in `README.md:~95`: "Most existing graph databases start by requiring you to shoehorn your data into the labelled-property graph model. We don't go this route." Helioy already decided property-graph wins (this session's surrealdb review). Embedding Cozo means writing CozoScript queries that operate on relations, then doing the property-graph projection on top in Rust. The query layer fights us.
3. **Internal relation API is `pub(crate)`.** `RelationHandle` (`cozo-core/src/runtime/relation.rs:75`), `InputRelationHandle` (`:321`), `create_relation` (`:586`), `encode_key_for_store` (`:247`) are all `pub(crate)`. The only public surface is `Db::run_script` (`cozo-core/src/runtime/db.rs:403`) returning `NamedRows` (`:130`). To embed Cozo, knowledge-matters serializes facts into CozoScript strings, runs them, parses the JSON-shaped `NamedRows` back. That is an external-database integration with extra steps, just in-process.
4. **Surface area is too large for what we want.** 50k LoC of `cozo-core` includes a Datalog parser, stratified evaluator, magic-set rewriter, 17 graph algorithms (`cozo-core/src/fixed_rule/algos/*.rs`), HNSW, MinHash LSH, FTS with three tokenizers (jieba, aho-corasick, rust-stemmers, fast2s for Chinese-traditional-to-simplified). knowledge-matters needs none of these except possibly transitive closure, which is a 30-line recursive SQL CTE.

The bar for "embedded backend" was: clean crate boundary, minimal transitive deps, swappable sqlite, confidence/scope/provenance expressible without ceremony, license clean. Cozo passes license, half-passes clean boundary (the Storage trait is good but the public API is not), fails minimal deps (310+ transitive even on minimal feature set), and the schema model fights provenance bodies (more below).

## Datalog vs property-graph traversal

Datalog earns its keep when:
- Recursive reachability and transitive closure are pervasive across queries.
- Multiple consumers benefit from a declarative composable query layer.
- Negation-as-failure and stratified aggregation are load-bearing.

knowledge-matters has one consumer (Helix), Helix can write any query language, and the workload is "fetch entities related to entity X with confidence above threshold". Two-hop and three-hop traversals are a parameterized recursive CTE in sqlite or a hand-written loop over the edge index. Datalog's recursion advantage is real but irrelevant when the queries are 1-3 hops with predicate filtering, not graph-algorithmic.

The cost side is concrete: a CozoScript dialect with its own pest grammar (`cozo-core/src/cozoscript.pest`), its own error model (miette), its own validity-time arithmetic. Helix prompts that emit CozoScript are harder to make robust than prompts emitting parameterized SQL or a structured edge-traversal API. Datalog buys recursive convenience and costs a learning surface and a dependency on a dead project. It does not earn its keep here.

## Primitives worth lifting

Three. Cited file:line. Crate intentionally absent because we are not depending on Cozo, just borrowing shapes.

### 1. Storage trait, exactly as written

`cozo-core/src/storage/mod.rs:31-52` defines `Storage` and `:56-165` defines `StoreTx`. The shape is:

```rust
pub trait Storage<'s>: Send + Sync + Clone {
    type Tx: StoreTx<'s>;
    fn storage_kind(&self) -> &'static str;
    fn transact(&'s self, write: bool) -> Result<Self::Tx>;
    fn batch_put<'a>(...) -> Result<()>;
    fn range_compact(&'s self, lower: &[u8], upper: &[u8]) -> Result<()>;
}
```

This is the right interface for a knowledge-matters storage layer that wants to swap sqlite for in-memory testing or a future rocksdb. `for_update: bool` on `get` and `multi_get` (`:60`, `:65`) is the clean MVCC lock-on-read primitive. Key-value byte slices, range scans bounded inclusive/exclusive, explicit `commit()` returning `Err` on conflict (`:104`). Cozo's sqlite implementation in `cozo-core/src/storage/sqlite.rs:25-115` is a 90-line proof that the trait fits sqlite cleanly: a single `cozo(k BLOB primary key, v BLOB)` table, seven prepared statements (`:122-130`), a sharded reader-writer lock for the single-writer constraint (`:28`).

This shape transfers directly to knowledge-matters' edge store. Compose this with the SurrealDB composite-key encoding already lifted, and you have a sqlite-backed edge index in 200 lines.

### 2. Validity column type as a first-class schema citizen

`cozo-core/src/data/relation.rs:88-104` defines `ColType` with `Validity` as a peer of `Int`, `String`, `Json`. Cozo's `:create` syntax pins time-travel per relation, not globally: `:create vld {a, v: Validity => d}` (test fixture in `cozo-core/src/data/tests/validity.rs:24`). The semantics in `cozo-core/src/storage/mod.rs:139-144` are: validity sits at the last slot of the key, and `range_skip_scan_tuple` returns only the most-recent-as-of-`valid_at` assertive row.

Map this to knowledge-matters: a confidence update is an assertion at `valid_at = now`, with optional retraction. The "as-of" query becomes `WHERE valid_at <= ?` with a `DISTINCT ON (subject, predicate, object)` ordered by `valid_at DESC`. This is a borrowed shape, not a borrowed implementation. The sqlite cost is one extra `valid_at` column on the edge table and a covering index. Get snapshot semantics for confidence updates without touching MVCC.

### 3. Triggers as schema-attached side-effect rules

`cozo-core/src/cozoscript.pest:40-45` exposes `set_triggers` with `on put`, `on rm`, `on replace` clauses that run a query when a relation mutates. The C++/Rust scaffolding is in `cozo-core/src/runtime/relation.rs:166` (`has_triggers`) and `cozo-core/src/runtime/callback.rs` (`EventCallbackRegistry`).

For knowledge-matters this maps to "when an edge is asserted, append to provenance log" or "when confidence drops below threshold, mark for review". The lift is the *shape*: triggers are declared per-relation at schema time, not as application-side observers. Implementation in knowledge-matters can be a 30-line dispatch table keyed on `(relation, op)`, but the API ergonomics come from Cozo.

### Primitives explicitly NOT worth lifting

- **HNSW** (`cozo-core/src/runtime/hnsw.rs`, 1,035 lines). knowledge-matters defers vectors. graphify provides graph-as-similarity. Confirms the deferral was right: integrating vector indexes into a graph store is non-trivial (1k LoC just for the manifest and search loop in `:594`), and the data-quality story is unclear. Skip.
- **Stratified Datalog evaluation** (`cozo-core/src/query/stratify.rs:224-280`). Beautiful code: SCC reduction, generalized Kahn topological sort over the rule graph, cycle verification for negation safety. Irrelevant unless we adopt Datalog. We are not.
- **17 graph algorithms** (`cozo-core/src/fixed_rule/algos/*.rs`: PageRank, Louvain, Yen's k-shortest-paths, A*, BFS, DFS, top-sort, Kruskal, Prim, label propagation, random walk, triangles, all-pairs-shortest-paths, Dijkstra, BFS shortest path, degree centrality, strongly connected components). knowledge-matters does not run graph algorithms. If it ever does, copy the one needed. Do not pay the surface tax up front.
- **FTS with jieba/aho-corasick/rust-stemmers/fast2s** (`cozo-core/src/fts/`). markdown-matters owns full-text search.
- **MinHash LSH** (`cozo-core/src/runtime/minhash_lsh.rs`, 389 lines). Out of scope.
- **Imperative DSL** (`cozo-core/src/runtime/imperative.rs`, 399 lines, plus `parse/imperative.rs`). Cozo grew procedural extensions. We do not need them.
- **TiKV / Sled / RocksDB backends**. We want sqlite, optionally in-memory for tests. Sled is marked experimental in `cozo-core/Cargo.toml:43`. TiKV is for distributed deployment. RocksDB is a 50MB build dependency. Skip all three.
- **CozoScript parser** (`cozo-core/src/cozoscript.pest`, plus `parse/*.rs`). Pest grammar with custom error reporting. Avoid; we are not adopting the query language.

## Head-to-head: cozo vs surrealdb

| Axis | SurrealDB | CozoDB | Winner |
|------|-----------|--------|--------|
| License clean for embedded internal use | BSL 1.1 | MPL 2.0 | **cozo** |
| Surface area / link cost | 243k LoC, four KV backends, ML, JS, GraphQL | 73k LoC, four KV backends, FTS, HNSW, 17 algos | cozo |
| Storage backend matches sqlite-sidecar convention | yes, `surrealkv` or rocksdb | yes, sqlite as default minimal feature | tie |
| Confidence/scope/provenance expressible | property graph fits cleanly | relational with Json column, awkward fit for triple bodies | surrealdb |
| Project health: maintainer | company, full-time team | abandoned 17 months, no maintainer reply | **surrealdb** |
| Project health: breaking-change risk | regular releases, semver loose | frozen at 0.7.6 forever | inverted |
| Query surface fit (property-graph traversal) | SurrealQL has graph traversal | Datalog rejects property-graph explicitly | **surrealdb** |
| Public API permits direct manipulation | yes, RPC and embedded | no, only `run_script` returning `NamedRows` | surrealdb |

Cozo wins license. SurrealDB wins everything else, including project health which is the variable that flipped between the two reviews. Both fail as embedded backends for knowledge-matters, for different reasons. The inspiration-only verdict is symmetric: lift shapes, build the edge layer.

## Recommended action

1. **Build the edge layer in knowledge-matters from scratch on sqlite.** Use the three SurrealDB shapes already lifted (composite-key edge encoding, schemafull/schemaless toggle per predicate, per-operation permissions struct).
2. **Lift the three Cozo shapes above into the same component**: the `Storage`/`StoreTx` trait pair as the storage abstraction, the `Validity` column type for confidence-update snapshots, the schema-attached triggers for provenance-log writes.
3. **Skip Datalog.** Use parameterized SQL for fetches, recursive CTEs for the rare transitive-closure case, hand-written Rust for any traversal hot path.
4. **Re-evaluate in 12-18 months** if a fork picks up Cozo with a credible maintainer commitment. The engine internals are good; only the upstream is dead.

## Grade calibration: B-

Anchors from prior reviews:
- C: DeepDiagram (narrow, mostly demo).
- B-: claudex / metaharness / revfactory-harness (single-author, useful primitives, limited scope).
- B: graphify (cleaner pipeline, real tests).
- B+: superpowers / impeccable (real CI, real tests, broad surface).
- A-: notebooklm-py / mngr (production-quality, well-architected).

Cozo lands at **B-**. As a database it is A-quality engineering: stratified Datalog, MVCC, multiple storage backends, HNSW, time travel. As a borrow target it is B- because the public API is too narrow (only `run_script`), the surface is too large for the three primitives we want, and the project is dead. It sits structurally where claudex does: useful shapes, single author, frozen, lift narrowly. The license advantage over SurrealDB is real but does not save the candidacy when the maintenance signal is mourning emoji.

If Cozo had shipped a release in 2026, this would be B+ and the embedded-backend verdict would be a coin flip with SurrealDB. It did not, and it is not.

## Sources consulted

- `Cargo.toml:3-15` (workspace members)
- `cozo-core/Cargo.toml:1-15, 17-67, 80-146` (license, features, dependencies)
- `cozo-core/src/storage/mod.rs:1-165` (Storage and StoreTx traits)
- `cozo-core/src/storage/sqlite.rs:1-150` (sqlite backend implementation)
- `cozo-core/src/data/relation.rs:1-120` (ColType, Validity, schema model)
- `cozo-core/src/runtime/db.rs:97-130, 262-440` (Db struct, NamedRows, run_script)
- `cozo-core/src/runtime/relation.rs:75-321, 586` (RelationHandle, InputRelationHandle)
- `cozo-core/src/runtime/hnsw.rs:1-80` (HnswIndexManifest)
- `cozo-core/src/runtime/callback.rs` (EventCallbackRegistry)
- `cozo-core/src/cozoscript.pest:14-50, 144` (grammar, triggers, relation ops)
- `cozo-core/src/data/tests/validity.rs:1-60` (validity test fixture)
- `cozo-core/src/query/stratify.rs:165-280` (stratification)
- `README.md:~80-200` (embedded vs server, anti-property-graph stance, time-travel rationale, perf)
- `git log` (last commit 2024-12-04), `git shortlog -sn` (Ziyang Hu 60/85 commits)
- `gh issue list` (#301 maintenance question with 🕯️ comments, #298 broken cargo update, #306 sled del bug)
- `gh repo view cozo-community/cozo` (community fork, last push 2024-12-12, dead too)

## Open questions

- Is anyone forking cozo with a credible commitment? `cozo-community` was the obvious candidate; it died at the same time as upstream. Worth a 30-minute search if the embed verdict ever needs to be revisited.
- Does the SurrealDB shape lift actually compose with Cozo's Storage trait without friction? Likely yes (both are MVCC byte-slice KV), but worth a 50-line spike if the edge layer goes that direction.
- Is there a maintained MPL/Apache embedded property-graph engine? If one exists with a current pulse, it dominates both candidates here. Not aware of one as of 2026-04.
