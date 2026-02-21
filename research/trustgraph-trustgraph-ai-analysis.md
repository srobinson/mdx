---
title: "TrustGraph Competitive Analysis vs Helix Architecture"
type: research
tags: [competitive-analysis, knowledge-graph, rag, provenance, context-engineering, helix]
summary: "Deep architectural analysis of TrustGraph (trustgraph-ai/trustgraph) as competitive comparison to Helioy's Helix three-vertex architecture"
status: active
source: github-researcher
confidence: high
created: 2026-03-25
updated: 2026-03-25
---

## Executive Summary

TrustGraph is a self-hosted "context development platform" that combines a knowledge graph, multiple RAG pipelines, LLM-driven extraction, and a PROV-O provenance system into a single deployable stack. It positions itself as "Supabase for context graphs." With 1,497 GitHub stars, 137 forks, 5 contributors, Apache 2.0 license, and active development (v2.1, last push March 23 2026), it represents the most architecturally comparable open-source project to Helix. Its provenance system is surprisingly thorough, but it has zero personalization capabilities and its audit trail, while structured, lacks tamper-evidence guarantees.

## 1. Overview

| Attribute | Value |
|---|---|
| Repository | `trustgraph-ai/trustgraph` |
| Language | Python (~815 .py files), TypeScript (client libs) |
| License | Apache 2.0 |
| Stars | 1,497 |
| Forks | 137 |
| Contributors | 5 |
| Created | July 2024 |
| Latest Version | v2.1 (March 2026) |
| Default Branch | `master` |
| Deploy Model | Docker Compose / Kubernetes (self-hosted) |

**Package structure**: Monorepo with 8+ Python packages: `trustgraph-base` (core types, schema, messaging, provenance), `trustgraph-flow` (all processing services), `trustgraph-cli`, `trustgraph-mcp`, `trustgraph-bedrock`, `trustgraph-vertexai`, `trustgraph-embeddings-hf`, `trustgraph-ocr`.

## 2. Architecture Deep Dive

### 2.1 Core Data Model: RDF Quads

TrustGraph models all knowledge as **RDF quads** (subject, predicate, object, graph). Every triple can optionally carry a named graph identifier, enabling data partitioning within a single collection. Three named graphs are used:

- `""` (default): Core knowledge facts
- `urn:graph:source`: Extraction provenance (document/chunk lineage)
- `urn:graph:retrieval`: Query-time explainability (question/answer chain)

This is a principled design. Named graphs provide clean separation of concerns without requiring separate storage backends.

### 2.2 Storage Layer

**Triple store**: Apache Cassandra with a custom entity-centric schema. The newer implementation (`EntityCentricKnowledgeGraph`) uses 2 tables instead of the original 7-table design:

- `quads_by_entity`: Partitioned by `(collection, entity)`, stores all quads an entity participates in with role metadata (s/p/o)
- `quads_by_collection`: Manifest for collection-level queries and deletion

Each user gets a separate Cassandra **keyspace**, providing hard multi-tenancy at the storage level. Collections live within keyspaces. Schema fields include `otype` (URI/Literal/Triple), `dtype` (datatype), `lang` (language tag), supporting RDF-star via nested triple serialization.

**Vector store**: Qdrant for both graph embeddings (entity vectors) and document embeddings (chunk vectors). Collections are created lazily with dimension suffixes. Supports Milvus and Pinecone as alternatives.

**Document/object store**: Garage (S3-compatible) for chunk content and document storage.

**Message bus**: Apache Pulsar handles all inter-service communication via pub/sub. Every service (chunker, extractor, embeddings writer, RAG service) is an independent consumer/producer wired through Pulsar topics.

### 2.3 Service Architecture

TrustGraph is a **microservice-per-function** architecture where each capability runs as an independent `FlowProcessor` that:

1. Registers consumer/producer specifications against named Pulsar topics
2. Receives configuration from a central config service
3. Processes messages asynchronously
4. Routes results to downstream services

Services are grouped into **flows** (runtime configurations). A flow defines which services are active, which topics they use, and what parameters they run with. Flows can be created, started, and stopped at runtime via the config API.

Key services in `trustgraph-flow/`:

| Service | Path | Purpose |
|---|---|---|
| `chunking/recursive` | Text chunking (recursive splitting) |
| `chunking/token` | Token-based chunking |
| `extract/kg/definitions` | LLM-driven entity/definition extraction |
| `extract/kg/ontology` | Ontology-conformant triple extraction (OntoRAG) |
| `embeddings/fastembed` | Local embedding generation |
| `embeddings/ollama` | Ollama-based embeddings |
| `retrieval/graph_rag` | GraphRAG pipeline |
| `retrieval/document_rag` | DocumentRAG pipeline |
| `retrieval/nlp_query` | Natural language query service |
| `storage/triples/cassandra` | Cassandra triple writer |
| `storage/graph_embeddings/qdrant` | Qdrant graph embedding writer |
| `agent/react` | ReAct agent with tool calling |
| `cores/` | Knowledge Core management |

### 2.4 API Layer

A REST + WebSocket API gateway (`api-gateway`, port 8088) provides:

- **Global services**: config, flow management, knowledge cores, library, collection management
- **Flow-hosted services**: RAG, text completion, embeddings, triples query, agent
- Authentication via bearer token (optional `GATEWAY_SECRET`)
- OpenAPI 3.1 spec (v2.1)

MCP server (`trustgraph-mcp`) exposes TrustGraph capabilities as MCP tools via WebSocket connections to the API gateway.

## 3. Knowledge Graph and Retrieval Patterns

### 3.1 Three RAG Pipelines

**DocumentRAG**: Standard vector retrieval.
1. Extract concepts from query via LLM
2. Embed concepts
3. Query Qdrant for matching document chunks
4. Fetch chunk content from Garage (S3)
5. Synthesize answer via LLM

**GraphRAG** (the flagship): A 4-stage pipeline.
1. **Grounding**: LLM extracts concepts from query, embeds them, finds seed entities in Qdrant
2. **Exploration**: Batched graph traversal from seed entities (configurable depth, default 2 hops, max 1000 edges), querying Cassandra for all triples involving each entity
3. **Focus**: LLM scores edges for relevance (`kg-edge-scoring` prompt), selects top N, then generates per-edge reasoning (`kg-edge-reasoning` prompt). Concurrently traces source documents via provenance chain
4. **Synthesis**: Selected edges plus source document metadata fed to LLM for final answer generation (`kg-synthesis` prompt)

**OntologyRAG**: An ontology-constrained extraction variant.
1. Loads user-defined ontology (classes, properties)
2. Embeds ontology elements into a local vector store
3. For each text chunk, selects relevant ontology subset via vector similarity
4. LLM extracts triples conforming to the selected ontology subset
5. Validates and normalizes extracted entities

### 3.2 Knowledge Extraction Pipeline

Ingest flow: Document upload -> PDF/OCR decoding -> Chunking -> KG extraction (parallel: definitions + relationships) -> Triple storage + Embedding storage.

The extraction uses LLM prompts to produce structured triples from text chunks. Entity normalization maps extracted entities to canonical URIs under `http://trustgraph.ai/e/`. Schema.org and SKOS vocabularies are used for standard predicates.

### 3.3 Context Cores

TrustGraph's "Context Core" concept is a portable, versioned bundle of knowledge:
- Ontology definitions and mappings
- Context graph (entities, relationships, evidence)
- Embeddings/vector indexes
- Source manifests and provenance
- Retrieval policies

Cores can be exported, imported, and loaded into different flows. This is their unit of knowledge packaging.

## 4. Trust/Provenance Mechanisms

This is where TrustGraph is most relevant to Helix. The provenance system is substantial and well-designed.

### 4.1 Extraction-Time Provenance (PROV-O)

Every extracted fact records its full lineage using W3C PROV-O ontology:

```
Document -> Page -> Chunk -> Subgraph -> (individual triples)
```

Each link is a `prov:wasDerivedFrom` triple. Each transformation records:
- `prov:Activity` (what extraction step ran)
- `prov:Agent` (which component, its version)
- `prov:startedAtTime` (when it ran)
- TG-specific metadata: LLM model used, ontology applied, chunk parameters

**Containment model**: Instead of per-triple reification (expensive), a `tg:Subgraph` entity uses `tg:contains` with RDF-star quoted triples. One subgraph per chunk extraction, shared across all triples from that chunk.

Provenance triples are stored in the `urn:graph:source` named graph, colocated with the knowledge facts in the same Cassandra collection but logically separated.

### 4.2 Query-Time Provenance (Explainability)

Every RAG query generates a full explainability trace stored in `urn:graph:retrieval`:

**GraphRAG trace chain**:
```
Question -> Grounding -> Exploration -> Focus -> Synthesis
```

- **Question**: Query text, timestamp, question type (GraphRAG/DocRAG/Agent)
- **Grounding**: Extracted concepts
- **Exploration**: Seed entities, edge count
- **Focus**: Selected edges (as RDF-star quoted triples) with per-edge reasoning
- **Synthesis**: Final answer, linked to stored document in librarian

**Agent trace chain**:
```
Question -> Analysis(1..N) -> Conclusion
```

Each Analysis records: action taken, arguments, thought process, observation.

### 4.3 Explainability Client

A dedicated `ExplainabilityClient` fetches provenance traces with **quiescence detection** for eventual consistency handling: fetch, wait, fetch again; if results match, data is stable.

The trace can be walked backward from any answer to its source documents, through every intermediate reasoning step.

### 4.4 What Is Missing from TrustGraph's Provenance

**No tamper-evidence**: Provenance triples are stored as regular data in Cassandra. They can be modified or deleted without detection. There is no hash chaining, Merkle tree, or append-only log.

**No cryptographic integrity**: No signing of provenance records. Nothing prevents a compromised system from rewriting history.

**No formal audit log**: The provenance system tracks knowledge lineage, not operational events (who accessed what, when, permission changes, configuration mutations).

**No immutability guarantees**: Named graphs can be overwritten. Collections can be deleted wholesale.

## 5. Vertex Coverage Assessment

### Vertex 1: Intelligent Context

**TrustGraph coverage: Strong (8/10)**

- LLM-curated knowledge extraction (definitions, relationships, ontology-constrained)
- Three distinct retrieval pipelines (Document, Graph, Ontology RAG)
- 4-stage GraphRAG with concept extraction, subgraph traversal, LLM-scored edge selection, and synthesis
- Portable Context Cores for knowledge packaging
- Multi-model storage (graph, vector, document, tabular)
- Ontology-driven structuring for precision retrieval

**Gap vs Helix**: TrustGraph treats context as static knowledge that gets ingested and queried. There is no concept of context evolution, decay, contradiction detection, or intelligent curation over time. Context Cores are versioned artifacts, not living knowledge that adapts.

### Vertex 2: Personalization

**TrustGraph coverage: None (0/10)**

- No user preference modeling
- No geometric identity modeling
- No adaptive behavior based on user history
- Multi-tenancy exists (per-user keyspaces) but only for data isolation
- The `user` parameter flows through every query for access control, not personalization
- No attention weighting, no relevance scoring based on user profile

**Gap**: This is TrustGraph's most significant blind spot. Every user gets the same retrieval behavior. No equivalent to Helix's S3 hypersphere modeling.

### Vertex 3: Audit

**TrustGraph coverage: Partial (5/10)**

**Strengths**:
- Full PROV-O extraction provenance (document to triple lineage)
- Query-time explainability traces (question to answer chain)
- RDF-star containment model for efficient provenance storage
- Source document tracing from selected edges back through subgraph -> chunk -> page -> document
- Named graph separation of concerns (knowledge vs provenance vs explainability)

**Gaps**:
- No tamper-evidence (no hash chains, no Merkle trees)
- No cryptographic signing of provenance records
- No operational audit log (access events, config changes, data mutations)
- No append-only guarantee; provenance can be overwritten
- No formal compliance features (retention policies, access logging)

## 6. Transferable Patterns

These are concrete architectural ideas from TrustGraph that could inform Helix:

### 6.1 Named Graph Separation (high value)

Using named graph URIs within the same collection to logically separate knowledge facts (`""`), extraction provenance (`urn:graph:source`), and query provenance (`urn:graph:retrieval`) is elegant. Helix could adopt this for separating core knowledge, audit records, and personalization data within a unified storage layer.

### 6.2 Subgraph Containment Model (high value)

Instead of reifying every triple (3x storage overhead), TrustGraph uses a containment model where a subgraph entity `tg:contains` quoted triples via RDF-star. This is O(n) provenance instead of O(3n). Helix's audit vertex could use a similar approach for batch provenance.

### 6.3 4-Stage GraphRAG Pipeline (medium value)

The Grounding -> Exploration -> Focus -> Synthesis pipeline with LLM-scored edge selection is well-designed. The separation of concept extraction, graph traversal, relevance scoring, and synthesis into distinct stages with provenance at each step is a pattern worth studying for Helix's intelligent context vertex.

### 6.4 Quiescence Detection for Eventual Consistency (medium value)

The `ExplainabilityClient` pattern of fetch-wait-fetch-compare for detecting data stability under eventual consistency is clever. Relevant if Helix uses eventually consistent stores.

### 6.5 Context Cores as Portable Artifacts (medium value)

The idea of packaging knowledge as a versioned, exportable, loadable bundle (ontology + graph + embeddings + provenance + policies) is strong. Helix could adopt a similar concept for its context packaging, with the addition of personalization state.

### 6.6 Entity-Centric Storage Design (low value for Helix)

The 2-table Cassandra schema where every entity has a partition containing all quads it participates in is efficient for graph traversal. However, this is Cassandra-specific and Helix's storage choices may differ.

## 7. Where Helix Wins

### 7.1 Personalization is Helix's Unfair Advantage

TrustGraph serves the same knowledge to every user. Helix's geometric identity modeling on S3 provides a fundamentally different value proposition: context that understands who is asking, adapts retrieval to user preferences, and evolves the identity model through interaction. No amount of graph structure substitutes for this.

### 7.2 Tamper-Evident Audit Trail

TrustGraph's provenance is honest record-keeping. Helix's audit vertex, with hash chaining and tamper-evidence, provides verifiable record-keeping. In regulated environments (healthcare, finance, legal), this is a hard requirement that TrustGraph cannot satisfy.

### 7.3 Unified Architecture vs. Infrastructure Sprawl

TrustGraph requires: Cassandra + Qdrant + Garage (S3) + Apache Pulsar + an LLM provider + Docker/Kubernetes. That is a significant operational footprint. Helix's unified API approach, where three vertices are accessible through a single interface, offers dramatically simpler deployment and operation.

### 7.4 Intelligent Curation vs. Static Ingestion

TrustGraph's model is: ingest documents, extract knowledge, query it. Knowledge does not evolve, contradict itself, or decay. Helix's intelligent context vertex promises LLM-curated storage where knowledge is actively managed, contradictions are detected, and relevance changes over time. This is a generation ahead of static RAG.

### 7.5 Mathematical Foundations

Helix's use of geometric modeling (S3 hypersphere for identity, attention-matters for memory) provides a principled mathematical framework. TrustGraph's intelligence is entirely in LLM prompts. When the prompts change, the behavior changes unpredictably. Geometric models provide stable, interpretable behavior.

## 8. Key Takeaway

TrustGraph is the strongest open-source competitor to Helix's intelligent context vertex. Its PROV-O provenance system and 4-stage GraphRAG pipeline are well-engineered and provide real explainability. Its Context Core concept for portable knowledge bundles is compelling.

However, TrustGraph occupies a different category than Helix. It is infrastructure for knowledge graphs with RAG bolted on. Helix is a unified intelligent context API built around three required vertices. TrustGraph competes on one vertex (intelligent context, where it is strong), has zero coverage on a second (personalization), and partial coverage on the third (audit/provenance without tamper-evidence).

The competitive risk from TrustGraph is that teams who only need knowledge graph + RAG will choose it because it exists today and is open source. Helix's response should be to emphasize the three-vertex differentiation: the ability to serve personalized, auditable context is what separates a context platform from a knowledge graph with RAG.

**Specific threat level**: Medium. TrustGraph is well-positioned for enterprise knowledge management use cases but fundamentally cannot compete on personalization or verifiable audit.

## Sources Consulted

- `README.md`: Project overview and feature matrix
- `DEVELOPER_GUIDE.md`: Release and build process
- `schema.ttl`: RDF schema definitions
- `trustgraph-base/trustgraph/provenance/`: Full provenance system (`triples.py`, `namespaces.py`, `vocabulary.py`, `uris.py`)
- `trustgraph-base/trustgraph/api/explainability.py`: Explainability client and entity models
- `trustgraph-base/trustgraph/base/flow_processor.py`: Flow processing architecture
- `trustgraph-base/trustgraph/base/pubsub.py`: Pulsar messaging layer
- `trustgraph-flow/trustgraph/retrieval/graph_rag/graph_rag.py`: GraphRAG implementation
- `trustgraph-flow/trustgraph/retrieval/graph_rag/rag.py`: GraphRAG service wrapper
- `trustgraph-flow/trustgraph/retrieval/document_rag/document_rag.py`: DocumentRAG implementation
- `trustgraph-flow/trustgraph/extract/kg/ontology/extract.py`: Ontology-based extraction
- `trustgraph-flow/trustgraph/extract/kg/ontology/ontology_selector.py`: Ontology selection algorithm
- `trustgraph-flow/trustgraph/storage/triples/cassandra/write.py`: Cassandra triple writer
- `trustgraph-flow/trustgraph/storage/graph_embeddings/qdrant/write.py`: Qdrant embedding writer
- `trustgraph-flow/trustgraph/direct/cassandra_kg.py`: Entity-centric Cassandra schema
- `trustgraph-flow/trustgraph/cores/knowledge.py`: Knowledge Core management
- `trustgraph-flow/trustgraph/agent/react/agent_manager.py`: ReAct agent implementation
- `trustgraph-mcp/trustgraph/mcp_server/mcp.py`: MCP server integration
- `specs/api/openapi.yaml`: REST API specification
- GitHub Issues: Open issues listing (10 open, including PostgreSQL/AGE integration request)

## Open Questions

1. **Performance at scale**: No benchmarks found. How does the 2-table Cassandra schema perform with millions of triples? The entity-centric partitioning could create hotspots for highly-connected entities.

2. **Context Core lifecycle**: The `unload_kg_core` method returns "not implemented". How mature is the knowledge lifecycle management?

3. **Ontology RAG maturity**: Recent PRs (`#691`) suggest OntoRAG pipeline was recently fixed. May still have stability issues.

4. **Entity deduplication**: Open issue `#430` notes duplicate entities in Qdrant. This is a fundamental knowledge graph problem they have not solved.

5. **PostgreSQL/AGE integration**: Issue `#675` (March 24, 2026) requests PostgreSQL with AGE graph extension as an alternative to Cassandra. This would significantly simplify deployment if implemented.
