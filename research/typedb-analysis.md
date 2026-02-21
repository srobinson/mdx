---
title: TypeDB Architecture Analysis for Helix Context API
type: research
tags: [typedb, database, knowledge-graph, type-system, inference, helix, context-matters]
summary: Deep architectural analysis of TypeDB's type system, inference engine, query language, and data model evaluated against Helix's requirements for intelligent context, personalization, and audit.
status: active
source: github-researcher
confidence: high
created: 2026-03-23
updated: 2026-03-23
---

## Executive Summary

TypeDB is a polymorphic database written in Rust (~11MB source, 4.2k GitHub stars, MPL-2.0) that unifies entity-relationship modeling with a strong type system featuring inheritance and interface polymorphism. It stores data on RocksDB via a custom MVCC storage engine and provides TypeQL, a declarative query language with pattern matching and type inference. TypeDB 3.x introduced user-defined functions, struct types, and a rewritten Rust engine (previously Java). The project positions itself for knowledge representation but fundamentally operates as a typed graph database with compile-time type inference rather than runtime rule-based reasoning. Its architectural patterns offer several lessons for Helix, though the system as a whole is too heavyweight and misaligned to serve as a direct backend.

## Architecture Overview

### Module Layout

TypeDB's Rust workspace is organized into a clean layered architecture:

```
storage/       RocksDB-backed MVCC key-value engine with isolation manager
encoding/      Binary encoding for types, things, values; keyspace layout
concept/       Domain model: TypeAPI, ThingAPI, OwnerAPI, PlayerAPI traits
ir/            Intermediate representation: pattern constraints, pipeline stages
compiler/      Type annotation, inference, query planning, executable generation
executor/      Pipeline execution: match, insert, delete, update, fetch, reduce
function/      User-defined function management and caching
query/         Query manager, cache
database/      Database lifecycle, transactions (Read/Write/Schema)
server/        gRPC + HTTP server, tokio runtime
durability/    WAL, crash recovery
```

### Data Flow

```
TypeQL query string
  -> Parser (typeql crate, pest-based)
  -> IR translation (ir/translation/)
  -> Type annotation/inference (compiler/annotation/)
  -> Query planning (compiler/executable/match_/planner/)
  -> Executable generation (compiler/executable/)
  -> Pipeline execution (executor/pipeline/)
  -> Row/Document results
```

### Storage Engine

The storage layer (`storage/storage.rs`) is a custom MVCC engine wrapping RocksDB:

- **MVCCStorage<Durability>** manages multiple keyspaces optimized for different prefix seek lengths (11, 15, 16, 17, 25 bytes)
- **IsolationManager** provides snapshot isolation with a timeline of sequence-numbered commits
- **Snapshots** are the transaction primitive: `ReadSnapshot`, `WriteSnapshot`, `SchemaSnapshot`
- A WAL-based durability client handles crash recovery
- The isolation manager uses a windowed timeline with reader tracking and watermark advancement

This is significantly more complex than SQLite. The keyspace optimization reveals how seriously they treat prefix-scan performance on their encoding layout.

## Type System and Schema Language

### Three Root Types

TypeDB's type system is built on a conceptual modeling foundation with three root kinds:

1. **Entity** - independent objects (e.g., `user`, `employee`)
2. **Relation** - typed connections with named roles (e.g., `mentorship` with `mentor` and `trainee` roles)
3. **Attribute** - typed values owned by entities or relations (e.g., `full-name value string`)

### Type Hierarchy and Inheritance

Types support single inheritance via `sub`:

```typeql
define
attribute id, value string;
attribute email, sub id;
attribute employee-id, sub id;

entity user, owns full-name, owns email @unique;
entity employee, sub user, owns employee-id @key;
```

Key implementation details from `concept/type_/mod.rs`:
- `TypeAPI` trait provides `get_supertype`, `get_subtypes_transitive`, `is_subtype_of` operations
- `KindAPI` extends `TypeAPI` with annotations and constraint resolution
- Types are encoded as 3-byte `TypeVertex` values (1 byte prefix + 2 byte TypeID), giving a max of 65,536 types per kind

### Interface System (Capabilities)

TypeDB's "interface" system is its capability mechanism:

- **owns** - entity/relation owns an attribute type (with ordering, cardinality, uniqueness constraints)
- **plays** - entity/relation plays a role in a relation type
- **relates** - relation type declares roles it relates

The `Capability` trait (`concept/type_/mod.rs:799`) is generic over `ObjectType` and `InterfaceType`, with annotation types for constraints. This is the polymorphism mechanism: queries match types that satisfy interface requirements rather than requiring exact type matches.

### Annotations and Constraints

TypeDB supports schema-level annotations that become constraints:

- `@abstract` - type cannot be instantiated directly
- `@key` - attribute is unique and required (implies `@unique` + cardinality(1,1))
- `@unique` - attribute value is unique across instances
- `@cardinality(min, max)` - bounds on ownership count
- `@distinct` - ordered collection elements must be distinct
- `@regex("...")` - string attribute must match pattern
- `@range(min..max)` - value must fall within range
- `@values(v1, v2, ...)` - value must be from enumerated set
- `@cascade` - cascade deletes
- `@independent` - relation can exist without all role players

These are enforced at the type system level, compiled into constraint sets that the executor validates on writes. This constraint system is architecturally interesting for Helix.

### Struct Types

TypeDB 3.x added struct types for composite values:

```typeql
define
struct address:
  street value string,
  city value string,
  zip value string?,
;
```

`StructDefinition` (in `encoding/graph/definition/struct.rs`) stores fields as a `HashMap<StructFieldIDUInt, StructDefinitionField>` with name-to-ID mapping. Fields can be optional. This is relevant for cm's need to store structured metadata.

### Value Types

Built-in value types: `Boolean`, `Integer`, `Double`, `Decimal`, `Date`, `DateTime`, `DateTimeTZ`, `Duration`, `String`, `Struct(DefinitionKey)`. The type system supports implicit casting (Integer -> Double/Decimal, Date -> DateTime) for comparisons.

## Inference Engine

**This is the most important finding for Helix evaluation.**

TypeDB's "inference" is primarily **compile-time type inference**, not runtime rule-based reasoning. Here is what actually happens:

### Type Inference (What Exists)

The compiler's annotation module (`compiler/annotation/`) performs:

1. **Type Seeding** (`type_seeder.rs`): Seeds the type inference graph with possible types for each variable based on schema
2. **Type Inference Graph** (`match_inference.rs`): Builds a constraint propagation graph using `VertexAnnotations` (mapping variables to sets of possible types)
3. **Constraint Propagation**: Intersects type sets across constraints until reaching a fixed point (`add_or_intersect` on `VertexAnnotations`)
4. **Pruning**: Removes impossible type combinations from the inference graph

This is closer to Hindley-Milner style type inference than to a Prolog-like rule engine. The inference resolves *which concrete types* a polymorphic variable could take, then generates specialized execution plans per type combination.

### Functions (TypeDB 3.x)

TypeDB 3.x replaced the older rule-based inference with user-defined functions:

```typeql
with fun fn_test() -> animal:
  match $called_animal isa cat, has $called_name;
  return { $called_animal };
```

Functions are:
- Parsed from TypeQL, stored as `FunctionDefinition` in the schema
- Type-checked at definition time against the schema
- Called from queries with `$result = fn_test()`
- Support stream returns (multiple results) and single returns (with selectors like `first`, `last`)
- Checked for stratification violations (recursive cycles through negation or reduction)

**This is important**: TypeDB 3.x removed implicit backward-chaining rule inference (which existed in TypeDB 2.x) and replaced it with explicit function calls. The inference is now forward, explicit, and deterministic. There is no automatic materialization or backward chaining.

### What TypeDB Does NOT Have

- No probabilistic reasoning
- No learned embeddings or similarity search
- No LLM-powered curation
- No continuous/geometric representations (cf. am's S3 hypersphere)
- No temporal reasoning beyond storing timestamps
- No uncertainty quantification

## Query Language (TypeQL)

### Pattern Matching

TypeQL's core is declarative pattern matching. The IR constraint types (from `ir/pattern/constraint.rs`) reveal the full vocabulary:

| Constraint | Purpose |
|---|---|
| `Isa` | Instance-of check (with `isa` exact or `isa!` no-inheritance) |
| `Sub` | Subtype relationship |
| `Has` | Attribute ownership |
| `Links` | Relation role-player binding |
| `Is` | Variable identity |
| `Owns` | Schema: type owns attribute type |
| `Relates` | Schema: relation type declares role |
| `Plays` | Schema: type plays role |
| `Label` | Type label constraint |
| `Kind` | Kind constraint (entity/relation/attribute/role) |
| `Comparison` | Value comparison (==, !=, <, >, <=, >=) |
| `ExpressionBinding` | Computed value binding |
| `FunctionCallBinding` | Function invocation with result binding |
| `Iid` | Internal ID lookup |
| `Value` | Value type constraint |

### Polymorphic Queries

TypeQL's key differentiator is transparent polymorphism:

```typeql
match $user isa user, has email $email;
```

This returns `user` instances AND instances of any subtype (e.g., `employee`). The type inference engine resolves all valid type combinations at compile time and generates union execution plans.

### Pipeline Model

Queries are pipelines of stages:
- `match` - pattern matching (read)
- `insert` - create instances
- `delete` - remove instances
- `update` - modify attributes/links
- `put` - upsert (match-or-insert)
- `fetch` - transform results into documents
- Modifiers: `select`, `sort`, `offset`, `limit`, `distinct`, `require`, `reduce`

### Negation, Disjunction, Optional

TypeQL supports:
- **Negation** (`not { ... }`): Variables bound inside negation are locally scoped; parent-scoped variables filter results
- **Disjunction** (`{ ... } or { ... }`): Variables bound in all branches are available outside; branch-local variables are locally scoped
- **Optional** (`try { ... }`): Variables bound inside are optional (nullable) in the output

These scoping semantics are carefully implemented in the IR pattern module with `VariableBindingMode` tracking (always-binding, optionally-binding, locally-binding-in-child, require-prebound).

## Data Model

### Encoding

TypeDB encodes data into RocksDB with a prefix-based layout optimized for scan patterns:

- **Type vertices**: 3 bytes (prefix + type ID)
- **Object vertices**: 11 bytes (prefix + type ID + object ID)
- **Short attribute vertices**: 12 bytes (prefix + type ID + inline value)
- **Long attribute vertices**: 21 bytes (prefix + type ID + hashed value + category)

Keyspaces are split by prefix length to optimize bloom filters. This is a serious performance engineering choice.

### Relations

Relations in TypeDB are first-class objects with their own vertices, linking to role players via edge encodings. The `Links` constraint connects a relation to a player via a role type. This three-way binding (relation, player, role) is richer than a simple edge in a property graph.

### Statistics

`thing/statistics.rs` tracks instance counts per type, used by the query planner for cost estimation. This is how TypeDB optimizes join orders.

## Comparison to Helix

### Structural Parallels

| Aspect | TypeDB | Helix |
|---|---|---|
| Schema | TypeQL `define` with inheritance + interfaces | cm schema with types, tags, scopes, derivation levels |
| Storage | RocksDB + MVCC + custom encoding | SQLite + Tantivy (cm), Quaternion store (am) |
| Query | TypeQL pattern matching | cm API (structured) + mdm (full-text) + LLM synthesis |
| Inference | Compile-time type inference | LLM-powered curation (read/write paths) |
| Functions | TypeQL user-defined functions | Observer/Consolidator agents |
| Types | Entity/Relation/Attribute + inheritance | Context entries with derivation DAGs + am neighborhoods |
| Constraints | Schema annotations (@unique, @cardinality, etc.) | CRITIC mutation rules + am alignment |

### Where TypeDB's Model Maps to cm

TypeDB's entity-relation-attribute triple maps cleanly to cm's domain:

- **Entity** -> Context entry (fact, observation, decision, etc.)
- **Relation** -> Derivation links, semantic relationships between entries
- **Attribute** -> Metadata (tags, scopes, confidence, timestamps)
- **Inheritance** -> Derivation levels (explicit > deductive > inductive)

The `owns` interface could model which entry types can carry which metadata attributes, with constraints enforcing consistency (e.g., `@cardinality(1,1)` for required fields).

### Where TypeDB Cannot Model am

TypeDB's type system is fundamentally discrete and symbolic. am's geometric memory operates in continuous space (S3 hypersphere with quaternions). There is no way to represent:
- Continuous orientation as identity
- Geometric neighborhoods
- Angular distance as similarity
- Quaternion rotation as value evolution

These are inherently numerical/geometric operations that require a different computational substrate.

## What Helix Can Learn

### 1. Schema-Level Constraint Enforcement

TypeDB's annotation system (`@unique`, `@cardinality`, `@range`, `@values`, `@regex`) enforces data quality at the schema level rather than in application code. Helix could adopt this pattern for cm entries:

- `@cardinality` on tag types (e.g., "each context entry has exactly one primary scope")
- `@values` for enumerated fields (derivation_level must be explicit|deductive|inductive)
- Schema-level validation for entry type compliance before LLM curation

This would give the CRITIC a formal constraint language to express mutation rules, rather than encoding them in prompts.

### 2. Polymorphic Querying

TypeDB's transparent type polymorphism is directly applicable. A Helix query like "find all context entries about authentication" should transparently return entries of any subtype (facts, decisions, observations) that match, without the caller specifying each type. cm's current tag-based system approximates this but lacks formal inheritance semantics.

### 3. Capability-Based Interfaces

The `owns`/`plays`/`relates` capability system is a clean way to model what operations are valid on what types. Helix could use this pattern for:
- Defining which agents can read/write which context scopes
- Expressing which entry types support which metadata fields
- Modeling role-based access (am is WRITE-ONLY for owner, READ-ONLY for agents)

### 4. Negation and Optional Semantics

TypeDB's careful handling of negation and optional patterns in query scoping is relevant for gap detection in Helix. "Find topics where we have observations but no corresponding decisions" is a natural negation query. The variable binding mode tracking (always-binding vs. optionally-binding vs. locally-scoped) is a mature approach to handling uncertainty in query results.

### 5. Pipeline Composition

TypeDB's query pipeline model (match -> transform -> write) maps well to Helix's read/write path architecture. A "match entries, synthesize with LLM, store derived entry" flow is essentially a TypeDB-style pipeline with an LLM stage injected between match and insert.

### 6. Type Inference as Query Optimization

TypeDB's compile-time type inference narrows the search space before execution. Helix could use a similar approach: before sending context to an LLM for synthesis, use type/tag/scope constraints to prune the candidate set. This is exactly what Tantivy already does for text, but formalizing it as type inference over the context graph would make the pruning composable and verifiable.

## Where Helix Diverges

### 1. LLM Curation vs. Schema Inference

TypeDB's inference is schema-driven and deterministic. A query always produces the same results given the same data. Helix's LLM-powered curation is fundamentally non-deterministic: the same context may yield different syntheses depending on the model, prompt, and conversation state. This is by design, because Helix serves agents that need interpretive, context-sensitive answers rather than exact pattern matches.

TypeDB answers: "What entities match this pattern?" Helix answers: "What does this context *mean* for this agent in this situation?"

### 2. Continuous vs. Discrete Representations

TypeDB operates entirely in the discrete/symbolic domain. am's quaternion-based identity representation occupies continuous geometric space. These are categorically different computational paradigms. TypeDB cannot represent "this value is 73% aligned with the owner's orientation" because alignment is a continuous measure derived from geometric operations, not a discrete type relationship.

### 3. Write-Path Intelligence

TypeDB validates writes against schema constraints (deterministic, fast). Helix's write path involves LLM-powered routing, overlap detection, and contradiction resolution (non-deterministic, expensive). TypeDB ensures data *consistency*. Helix ensures data *quality and coherence*.

### 4. Temporal and Provenance Models

TypeDB stores data as current state with MVCC for transaction isolation. It does not natively model temporal evolution, provenance chains, or audit trails. Helix requires graduated audit levels (L1 operation log, L2 provenance trail, L3 verifiable audit) and derivation DAGs that TypeDB would have to model as application-level relations rather than system-level features.

### 5. Agent-Facing vs. Developer-Facing

TypeDB is a general-purpose database with a developer-facing API. Helix is an agent-facing context API where consumers (Claude, other LLMs) interact without knowing about underlying backends. The abstraction level is different: TypeDB expects callers to write TypeQL queries; Helix expects callers to express intent ("what context do I need for this task?") and receives curated responses.

## TypeDB as Potential Backend for cm (Evaluation)

### Arguments For

1. **Richer schema**: TypeDB's type system with inheritance and interfaces could express cm's entry type hierarchy more formally than SQLite schemas
2. **Relation modeling**: First-class relations would naturally represent derivation DAGs and entry relationships
3. **Constraint enforcement**: Schema-level annotations would replace application-level validation code
4. **Polymorphic queries**: Transparent subtype matching would simplify query construction for agents

### Arguments Against

1. **Operational complexity**: TypeDB requires its own server process, RocksDB management, and custom WAL. cm currently runs embedded SQLite with zero operational overhead. This is a significant regression in deployment simplicity.

2. **No full-text search**: TypeDB has no built-in full-text search. cm uses Tantivy for fast candidate retrieval. You would still need Tantivy or a similar system alongside TypeDB, creating a two-engine architecture.

3. **No vector/embedding support**: If Helix ever adds semantic similarity search (likely for am observation extraction), TypeDB offers nothing here. SQLite-vec or a dedicated vector store would still be needed.

4. **Performance mismatch**: TypeDB is optimized for complex pattern matching across large type hierarchies. cm's primary access patterns are key-value lookups, tag filters, and full-text search. These are well-served by SQLite + Tantivy with much lower overhead.

5. **Dependency weight**: TypeDB is a 4k+ file Rust project with RocksDB, gRPC, tokio, and numerous dependencies. Embedding it would be a substantial dependency. Running it as a separate server adds operational complexity that works against Helix's "everything embedded" philosophy.

6. **LLM integration point**: The value of Helix is not in the storage layer but in the LLM curation layer. Swapping SQLite for TypeDB does not improve the read-path synthesis or write-path quality gating. The intelligence lives above the storage.

7. **Lock-in risk**: TypeDB is MPL-2.0 with a commercial cloud offering. The community edition is open source, but the project's trajectory favors the cloud product. Depending on TypeDB for a core storage layer introduces a dependency on Vaticle's product direction.

### Verdict

**TypeDB is not a good fit as a direct backend for cm or Helix.** The operational complexity is too high, the missing full-text search is a dealbreaker, and the core value proposition (polymorphic type system + compile-time inference) addresses problems that Helix solves differently (with LLM curation rather than schema inference).

However, several TypeDB patterns should be adopted at the schema design level within cm's existing SQLite store:

- Formal constraint definitions for entry type validation
- Inheritance-aware type hierarchies for context entries
- Capability-based interface declarations for agent access control
- Pipeline-oriented query composition

These can be implemented as application-layer abstractions over SQLite + Tantivy without taking on TypeDB as a dependency.

## Assessment and Recommendations

### For Helix Development

1. **Adopt TypeDB's constraint annotation pattern** for cm entry validation. Define `@cardinality`, `@values`, and `@range` style constraints in cm's schema that the CRITIC can reference when evaluating mutations. This formalizes what is currently implicit in prompts.

2. **Consider TypeDB's capability model** for modeling agent permissions in the Helix proxy layer. The `owns`/`plays`/`relates` abstraction cleanly separates "what this type can do" from "what this type is."

3. **Do not adopt TypeDB as a storage backend.** The complexity/benefit ratio is wrong. SQLite + Tantivy covers cm's access patterns with far less operational overhead. If richer graph querying becomes necessary, evaluate lighter alternatives (e.g., SQLite recursive CTEs for DAG traversal, or a purpose-built in-memory graph for derivation chains).

4. **TypeDB's pipeline model validates Helix's read/write path design.** The match-transform-write pipeline with typed intermediate results is the same architecture Helix uses (match context -> LLM synthesis -> store derived entry). This convergence suggests the pipeline abstraction is correct.

### For am (Attention Matters)

TypeDB offers nothing for am's geometric memory domain. The S3 hypersphere, quaternion operations, and continuous identity representation are outside TypeDB's computational model. am should continue with its specialized geometric storage.

### For Audit Vertex

TypeDB's MVCC and transaction model provide snapshot isolation but not the graduated audit trail Helix needs. The L1/L2/L3 audit levels require purpose-built provenance tracking that is orthogonal to TypeDB's transaction model. TypeDB could *store* audit records but provides no special support for generating or querying them.

## Sources Consulted

- `README.md` - project overview, schema examples, TypeQL syntax
- `Cargo.toml` (workspace) - full dependency graph, module structure
- `RELEASE_NOTES_LATEST.md` - v3.8.1 release, performance focus
- `concept/type_/mod.rs` - TypeAPI, KindAPI, OwnerAPI, PlayerAPI, Capability traits
- `concept/thing/mod.rs` - ThingAPI trait, encoding helpers
- `concept/type_/constraint.rs` - ConstraintDescription, ConstraintCategory enums
- `encoding/encoding.rs` - EncodingKeyspace layout, RocksDB configuration
- `encoding/graph/type_/mod.rs` - Kind enum (Entity, Attribute, Relation, Role)
- `encoding/graph/type_/vertex.rs` - TypeVertex encoding (3 bytes)
- `encoding/graph/definition/struct.rs` - StructDefinition for composite types
- `encoding/value/value_type.rs` - ValueType enum, casting rules
- `ir/lib.rs` - RepresentationError, IR error types
- `ir/pattern/mod.rs` - Pattern trait, Vertex enum, ScopeId, IrID trait
- `ir/pattern/constraint.rs` - Constraint enum (18 variants), ConstraintsBuilder
- `ir/pattern/negation.rs` - Negation scoping semantics
- `ir/pattern/disjunction.rs` - Disjunction with branch variable binding
- `ir/pattern/optional.rs` - Optional with optionally-binding variables
- `ir/pipeline/mod.rs` - VariableRegistry, FunctionReadError, FunctionRepresentationError
- `compiler/lib.rs` - ExecutorVariable, VariablePosition
- `compiler/annotation/mod.rs` - AnnotationError, type inference entry point
- `compiler/annotation/type_inference.rs` - resolve_value_types, type inference tests
- `compiler/annotation/match_inference.rs` - VertexAnnotations, TypeInferenceGraph
- `compiler/query_structure.rs` - QueryStructure, PipelineStructure
- `executor/lib.rs` - ExecutionInterrupt, Provenance, pipeline module
- `executor/pipeline/pipeline.rs` - Pipeline struct, read/write pipeline construction
- `executor/pipeline/match_.rs` - MatchStageExecutor, lazy pattern iterator
- `function/lib.rs` - FunctionError, stratification violation detection
- `function/function.rs` - Function struct, SchemaFunction
- `storage/storage.rs` - MVCCStorage, keyspace management
- `storage/isolation_manager.rs` - IsolationManager, Timeline, snapshot isolation
- `database/lib.rs` - Database, DatabaseManager modules
- `database/transaction.rs` - TransactionRead, TransactionWrite with snapshot isolation

## Open Questions

1. **TypeDB 3.x rule migration**: TypeDB 2.x had backward-chaining rules that were removed in 3.x. The function replacement has different semantics (explicit vs. implicit). How do existing TypeDB users handle the migration? Are there patterns from the old rule system worth studying for Helix's Observer design?

2. **Query planning cost model**: TypeDB uses thing statistics for join order optimization. How does this compare to Helix's approach of using Tantivy scores + LLM relevance ranking for candidate selection?

3. **Struct type evolution**: TypeDB's struct types are still maturing (optional/list types marked as unimplemented). How will nested struct support affect the data model? Could a similar evolution path inform cm's entry metadata structure?
