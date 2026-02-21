---
title: Structured Agent Memory Systems - SQL/SQLite-Backed Memory Layers for LLM Agents
type: research
tags: [agent-memory, sqlite, sql, local-first, llm-agents, memory-architecture, schema-design]
summary: Comprehensive landscape analysis of SQL-backed structured memory systems for LLM agents, covering 12+ projects, schema patterns, query strategies, human-in-the-loop, and practitioner experience.
status: active
source: deep-research
confidence: high
created: 2026-03-14
updated: 2026-03-14
---

## Executive Summary

The structured agent memory landscape in early 2026 has bifurcated into two camps: **cloud-hosted memory services** (Mem0, Zep, Letta Cloud) that combine vector stores with knowledge graphs, and **local-first SQLite-backed systems** (engram, agent-recall, OpenMemory, Google's Always-On Memory Agent, sqlite-memory) designed for single-developer or on-device use. The most technically mature local-first projects converge on a common pattern: a single SQLite file with FTS5 full-text search, structured observation records with type/scope/project metadata, and an MCP server exposing memory tools to the agent. Letta's benchmark finding that a filesystem-based agent scored 74% on LoCoMo (beating Mem0's 68.5%) has catalyzed a broader debate about whether structured retrieval provides enough advantage over simple file search to justify the complexity. The emerging consensus: the agent-facing interface (what the agent "sees") matters more than the storage backend, and the most effective systems decouple these layers.

## 1. Project Landscape

### 1.1 Cloud/Hosted Memory Services

**Letta (formerly MemGPT)** | 37.8k GitHub stars | YC S23
- Three-tier memory: core blocks (always in context, 2000 chars/block), recall (conversation history), archival (persistent searchable store)
- Self-editing: agents use `memory_replace`, `memory_insert`, `memory_rethink` tools to modify their own core blocks
- Storage: SQLite by default via pip, PostgreSQL recommended for production (42 tables)
- V1 architecture shift (2026): dropped heartbeat/send_message tool-based control in favor of native model reasoning
- Key insight: agents manage their own context window, deciding what stays visible vs. what goes to archival
- Letta Code extends this with filesystem-based memory, scoring 74% on LoCoMo benchmark
- Source: [Letta GitHub](https://github.com/letta-ai/letta), [Letta v1 blog](https://www.letta.com/blog/letta-v1-agent)

**Mem0** | 24.6k GitHub stars | YC W24
- Two-phase processing: extracts facts from message pairs, then compares against existing memories via vector search, deciding add/update/delete/ignore
- Triple storage: key-value (facts), graph store (relationships via Mem0g), vector store (semantic similarity)
- Scoping: organization -> project -> user -> session hierarchy with role-based access (READER, OWNER)
- Weakness: stores facts but does not learn behavioral patterns (confirmed by HN discussion, user fliellerjulian)
- 26% improvement over OpenAI baseline, 91% lower p95 latency vs full-context, 90%+ token savings
- Source: [Mem0 GitHub](https://github.com/mem0ai/mem0), [Mem0 paper](https://arxiv.org/abs/2504.19413)

**Zep** | Cloud + community edition
- Temporal knowledge graph: G = (N, E, phi) with three subgraph tiers (episode, semantic entity, community)
- Bitemporal: tracks both event time (when fact was true) and ingestion time (when fact was recorded)
- Powered by Graphiti engine; requires Neo4j for graph storage
- 94.8% on DMR benchmark (vs MemGPT's 93.4%), 18.5% accuracy improvement, 90% latency reduction
- Weakness: advanced features cloud-exclusive; local deployment substantially less capable
- Source: [Zep paper](https://arxiv.org/abs/2501.13956), [Graphiti GitHub](https://github.com/getzep/graphiti)

**Memori (MemoriLabs)** | SQL-native
- Database-agnostic: SQLite, PostgreSQL, MySQL, MongoDB via PEP 249 drivers
- Schema: third normal form with semantic triples (subject, predicate, object) for knowledge graph
- Memory attribution: facts attributed to entity (person/place/thing) + process (agent/program)
- Session management groups multi-step agent interactions
- FAISS for vector similarity on extracted fact embeddings (768-dim sentence transformer)
- Source: [Memori GitHub](https://github.com/MemoriLabs/Memori), [InfoQ coverage](https://www.infoq.com/news/2025/12/memori/)

### 1.2 Local-First SQLite Systems

**engram (Gentleman-Programming)** | Go binary + SQLite + FTS5
- Single binary, zero runtime dependencies (pure Go SQLite via modernc.org/sqlite)
- Data model: observations with title, type, content, project, scope, topic_key, metadata (created_at, updated_at, revision_count, duplicate_count)
- 13 MCP tools: mem_save, mem_update, mem_delete, mem_search, mem_context, mem_timeline, mem_session_summary, mem_get_observation, etc.
- Three-layer progressive disclosure: compact search results -> timeline context -> full untruncated content
- Deduplication: hash of project+scope+type+title in rolling window; duplicates increment counter
- Topic upsert: same project+scope+topic_key updates existing row rather than creating duplicates
- Scoping: project + scope ("project" or "personal")
- Session lifecycle: session_start -> proactive mem_save during work -> session_end with structured summary
- Database: `~/.engram/engram.db`
- Source: [engram GitHub](https://github.com/Gentleman-Programming/engram)

**agent-recall (mnardit)** | SQLite knowledge graph + MCP
- Entity-relation-slot-observation model (knowledge graph in SQLite)
- Entities: named things (person, client, project) with type
- Slots: key-value pairs on entities, scoped and bitemporal (valid_from/valid_to, archived not deleted)
- Observations: free-text facts attached to entities
- Relations: directed links between entities
- Scope chains with inheritance: `global -> acme-agency -> client-a`; local overrides parent for same slot
- 9 MCP tools including create_entities, add_observations, search_nodes
- LLM-generated briefings at session start (summarize all entities/slots/observations in scope chain)
- Token budget constraints for truncating lower-priority briefing content
- Database: `~/.agent-recall/frames.db`
- Source: [agent-recall GitHub](https://github.com/mnardit/agent-recall), [HN discussion](https://news.ycombinator.com/item?id=47165499)

**Google Always-On Memory Agent** | SQLite + ADK + Gemini
- Continuous background process ingesting files/API data, storing structured memories in SQLite
- Scheduled consolidation every 30 minutes: LLM re-reads stored memories, merges duplicates, drops noise
- No vector DB, no embeddings: pure LLM-driven memory read/write/consolidate
- Memory fields: summary, entities, topics, importance score (0-1), source attribution
- Single-instance, no user isolation or scoping
- Built with Google ADK + Gemini 3.1 Flash-Lite
- Source: [GitHub](https://github.com/GoogleCloudPlatform/generative-ai/tree/main/gemini/agents/always-on-memory-agent), [VentureBeat](https://venturebeat.com/orchestration/google-pm-open-sources-always-on-memory-agent-ditching-vector-databases-for)

**OpenMemory (CaviraOSS)** | SQLite/PostgreSQL + MCP
- Hierarchical Memory Decomposition (HMD): episodic, semantic, procedural, emotional, reflective sectors
- Composite scoring: salience + recency + coactivation (not just cosine distance)
- Adaptive forgetting: decay engine per sector, not hard TTLs
- Zero-config MCP endpoint for Claude Desktop, VS Code, etc.
- Integrations: LangChain, CrewAI, AutoGen, Streamlit
- Source: [OpenMemory GitHub](https://github.com/CaviraOSS/OpenMemory)

**sqlite-memory (sqliteai)** | SQLite extension
- SQLite extension (not a separate process): vector similarity + FTS5 hybrid search
- Markdown-aware chunking preserving semantic boundaries
- Local embedding via llama.cpp (no cloud calls)
- Transactional safety via SAVEPOINT
- Part of broader sqliteai ecosystem: sqlite-vector, sqlite-agent, sqlite-mcp
- Source: [sqlite-memory GitHub](https://github.com/sqliteai/sqlite-memory)

**MemOS (MemTensor)** | SQLite + FTS5 + vector
- Memory operating system metaphor: scheduling, layering, API abstraction, permissions
- OpenClaw Local Plugin (v1.0.0, March 2026): 100% on-device, persistent SQLite
- Hybrid search (FTS5 + vector), task summarization, skill evolution (skills self-upgrade)
- Multi-agent collaboration support
- Memory Viewer dashboard for inspection
- Unified Memory API: add, retrieve, edit, delete; graph-structured, inspectable, editable
- Source: [MemOS GitHub](https://github.com/MemTensor/MemOS), [MemOS paper](https://arxiv.org/html/2505.22101v1)

### 1.3 Framework-Integrated Memory

**LangMem (LangChain)** | Storage-agnostic
- Two-layer: stateless Core API (create_memory_manager, create_prompt_optimizer) + stateful integration with LangGraph BaseStore
- Namespace scoping: template variables populated at runtime (e.g., user_id, project_id)
- Memory tools: create_manage_memory_tool, create_search_memory_tool
- Supports both embedding-based recall and separate query model for search
- Source: [LangMem GitHub](https://github.com/langchain-ai/langmem)

**Claude Code Memory** | File-based
- Hierarchical .md files: project CLAUDE.md -> user CLAUDE.md -> .claude/rules/*.md -> auto-memory
- 92% rule application rate under 200 lines; 71% beyond 400 lines
- Specificity-based conflict resolution (more specific rules override general)
- No database, no structured query; pure prompt injection
- Source: [Claude Code docs](https://code.claude.com/docs/en/memory)

## 2. Schema Patterns

### 2.1 Common Entity Models

Across all surveyed systems, five recurring entity types emerge:

| Entity | Description | Found In |
|--------|-------------|----------|
| **Observation/Memory** | Core unit: a fact, decision, or learned pattern | engram, agent-recall, OpenMemory, Letta archival |
| **Entity** | Named thing (person, project, concept) | agent-recall, Zep, Mem0g, Memori |
| **Relation** | Directed link between entities | agent-recall, Zep Graphiti, Mem0g |
| **Session** | Grouping of interactions with lifecycle | engram, Memori, Letta recall |
| **Scope/Namespace** | Isolation boundary (project, user, global) | agent-recall, engram, LangMem, Mem0 |

### 2.2 Scoping Models

Three patterns for scoping memory:

1. **Flat namespace** (engram): project + scope ("project" | "personal"). Simple but limited.
2. **Hierarchical scope chain** (agent-recall): `global -> org -> project` with inheritance and local override. Most expressive for multi-project use.
3. **Template-variable namespace** (LangMem): runtime-populated path like `("user", "{user_id}", "memories")`. Flexible but requires framework integration.

### 2.3 Temporal Models

- **No history** (engram, Google AOMA): overwrite or deduplicate; latest value wins
- **Bitemporal** (agent-recall, Zep): track both event time and ingestion time; old values archived with valid_from/valid_to
- **Revision counting** (engram topic_key): increment revision_count on upsert; no full history but track evolution

### 2.4 Minimum Viable Schema for Local-First SQLite

Synthesizing the strongest patterns from the surveyed projects:

```sql
-- Core memory unit
CREATE TABLE memories (
    id INTEGER PRIMARY KEY,
    type TEXT NOT NULL,          -- 'fact', 'decision', 'pattern', 'feedback', 'observation'
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    scope TEXT NOT NULL,         -- 'global', 'user', 'project', 'session'
    scope_id TEXT,               -- project name, user id, etc.
    confidence REAL DEFAULT 1.0,
    importance REAL DEFAULT 0.5,
    source TEXT,                 -- where this memory came from
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    valid_from TEXT,             -- bitemporal: when fact became true
    valid_to TEXT,               -- bitemporal: when fact stopped being true
    revision INTEGER DEFAULT 1,
    content_hash TEXT            -- deduplication
);

-- Full-text search
CREATE VIRTUAL TABLE memories_fts USING fts5(
    title, content, type, scope_id,
    content=memories, content_rowid=id
);

-- Entity graph (optional, for relational memory)
CREATE TABLE entities (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    type TEXT NOT NULL,          -- 'person', 'project', 'concept', 'tool'
    scope TEXT NOT NULL,
    scope_id TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE entity_relations (
    id INTEGER PRIMARY KEY,
    source_id INTEGER REFERENCES entities(id),
    target_id INTEGER REFERENCES entities(id),
    relation_type TEXT NOT NULL, -- 'works_on', 'depends_on', 'knows_about'
    created_at TEXT NOT NULL
);

CREATE TABLE entity_facts (
    id INTEGER PRIMARY KEY,
    entity_id INTEGER REFERENCES entities(id),
    key TEXT NOT NULL,
    value TEXT NOT NULL,
    scope TEXT NOT NULL,
    scope_id TEXT,
    valid_from TEXT,
    valid_to TEXT,
    created_at TEXT NOT NULL
);

-- Session tracking
CREATE TABLE sessions (
    id INTEGER PRIMARY KEY,
    started_at TEXT NOT NULL,
    ended_at TEXT,
    summary TEXT,
    scope_id TEXT
);
```

## 3. Query Patterns

### 3.1 Pure FTS5 (engram pattern)
- Agent calls `mem_search(query)` which maps to FTS5 MATCH
- Progressive disclosure: compact results -> timeline -> full content
- Token-efficient: avoids loading full content until needed
- Limitation: no semantic similarity, only keyword matching

### 3.2 Hybrid FTS5 + Vector (sqlite-memory, MemOS pattern)
- Combine BM25 ranking from FTS5 with cosine similarity from sqlite-vec or llama.cpp embeddings
- Weighted merge: `score = alpha * bm25_score + (1 - alpha) * cosine_sim`
- Best retrieval quality but requires embedding infrastructure

### 3.3 LLM-Driven (Google AOMA pattern)
- No vector search, no FTS5: the LLM reads stored memories and decides relevance
- Consolidation loop replaces indexing: periodic LLM pass merges/deduplicates
- Simplest stack but highest per-query cost and latency

### 3.4 Scope-Chain Resolution (agent-recall pattern)
- Load all entities/slots/observations within scope chain at session start
- LLM summarizes into structured briefing
- No per-query retrieval; entire relevant context loaded upfront
- Works well when total memory fits within briefing token budget

### 3.5 Agent-As-Retriever (Letta pattern)
- Agent uses search tools (grep, search_files, archival_search) iteratively
- Self-directed query reformulation: agent refines searches based on initial results
- Letta's 74% LoCoMo score demonstrates this approach works surprisingly well
- Key finding: LLMs are better at using familiar tools (filesystem ops) than specialized memory APIs

## 4. Human-in-the-Loop

### 4.1 CHI 2025 Research Findings (Jones et al.)

The most rigorous user study on agent memory expectations comes from CHI EA '25 (6 interviews + 54 Reddit threads). Key findings:

**Memory Hierarchy**: Users conceptualize five layers:
1. Factual memories (general knowledge, training data)
2. User-related memories (preferences, identity, interaction style)
3. Domain-related memories (specialized knowledge for current role)
4. Project-related memories (higher-level project context)
5. Task-related memories (specific current-task details)

**User Desires**:
- Transparent memory: "I don't really know how it decides what is important to remember" (P3)
- Scoped access: 5/6 participants wanted memories disjoint across projects/domains
- Controllable overlap: ability to define how much memory crosses project boundaries
- On/off toggles: Reddit users want to selectively enable/disable specific memories
- Hierarchical organization: "like folders and subfolders in file systems" or "global vs. local variables"

**Current Workarounds**: Users create separate chat threads per project, use custom GPTs/personas, switch between accounts, and copy-paste context between sessions.

**Design Recommendation**: Memory systems should organize and control access to memories via hierarchical structures based on users' task-based needs, supporting both explicit user curation and implicit agent-driven organization.

### 4.2 Production Implementations

| System | Human Control | Mechanism |
|--------|--------------|-----------|
| Letta ADE | Visual memory editor | Web UI for inspecting/editing core memory blocks, archival entries |
| MemOS | Memory Viewer dashboard | Visual inspection of stored memories |
| OpenMemory | MCP-based | Agent-mediated; no direct UI for humans |
| engram | CLI + TUI | `engram search`, `engram timeline` commands; interactive TUI |
| agent-recall | CLI | `agent-recall history Alice role` for temporal lineage |
| ChatGPT | Settings page | List of memories with delete button; no editing |
| Claude | Settings page | List of memories with delete button; no editing |

### 4.3 Gap Analysis

No local-first system provides a good human curation experience. The best available is engram's TUI, which is read-only search. The pattern that emerges from the CHI research is clear: users want folder-like organization with drag-and-drop, on/off toggles per memory, and the ability to see exactly which memories influenced a response. No system delivers this today.

## 5. What Works and What Does Not

### 5.1 Confirmed Working Patterns

**Proactive agent saving** (engram, agent-recall): instructing the agent to call `mem_save` after significant work produces better memory than passive extraction. The agent decides what matters.

**Structured observations with type tags** (engram): categorizing memories as "decision", "pattern", "bugfix", "architecture" enables filtered retrieval.

**Scope chains with inheritance** (agent-recall): the `global -> org -> project` model with local override maps cleanly to real-world developer contexts.

**Deduplication with counters** (engram): hashing content to prevent duplicate entries while tracking frequency provides signal about importance.

**Progressive disclosure** (engram): returning compact search results first, then full content on demand, conserves tokens effectively.

**Periodic consolidation** (Google AOMA): scheduled LLM passes to merge/deduplicate/prune keeps memory stores clean over time.

### 5.2 Known Failure Modes

**Flat file degradation** (Glen Rhodes, dev.to): production agent memory files grow to 6000+ tokens with duplicates, stale context, and contradictions. System appears functional in dev but fails gradually over weeks.

**"Give me everything" retrieval** (Rhodes): even well-structured databases fail when agents query without filtering. Intelligent retrieval is the bottleneck, not storage.

**Behavioral pattern blindness** (HN, fliellerjulian): Mem0 and similar systems store explicit facts ("user prefers Python") but cannot learn implicit patterns from behavior over time. The solution proposed: capture structured events (agent output, user corrections, accepted changes) and run periodic LLM analysis to build confidence-weighted preference profiles.

**Benchmark gaming** (multiple sources): Mem0, Letta, and Zep have each published benchmarks claiming superiority. Independent evaluation is essential. Letta's finding that a filesystem scores 74% on LoCoMo while Mem0 reports 68.5% suggests current benchmarks may not measure what matters.

**User corrections as highest-signal data** (HN, solarkraft): "I have to re-tell my LLM a piece of info I have already told it a few weeks ago." No system automatically treats corrections as the most important memory signal.

**Token bloat from always-in-context memory** (Letta): core memory blocks are limited to 2000 chars each because they consume tokens on every call. The tradeoff between always-available and token-efficient is fundamental.

### 5.3 The Filesystem vs. Database Debate (March 2026)

Letta's benchmark showing filesystem-based agents outperform specialized memory tools has generated substantial discourse. The emerging synthesis:

- **Interface layer**: what the agent "sees" (filesystem ops, SQL queries, MCP tools) matters more than storage
- **Storage layer**: what actually persists (SQLite, files, PostgreSQL) is an implementation detail
- **The winning pattern**: a "virtual filesystem" where agents interact with familiar file-like primitives backed by structured storage underneath
- **When databases win**: multi-project scoping, temporal queries, deduplication, consolidation. When memory exceeds what fits in a single context window.
- **When files win**: simplicity, zero setup, familiar LLM tooling, works out of the box

## 6. Sources Consulted

### GitHub Repositories
- [Letta](https://github.com/letta-ai/letta) - 37.8k stars
- [Mem0](https://github.com/mem0ai/mem0) - 24.6k stars
- [engram](https://github.com/Gentleman-Programming/engram) - Go binary + SQLite
- [agent-recall](https://github.com/mnardit/agent-recall) - SQLite knowledge graph
- [OpenMemory](https://github.com/CaviraOSS/OpenMemory) - HMD architecture
- [sqlite-memory](https://github.com/sqliteai/sqlite-memory) - SQLite extension
- [MemOS](https://github.com/MemTensor/MemOS) - Memory OS
- [Memori](https://github.com/MemoriLabs/Memori) - SQL-native
- [LangMem](https://github.com/langchain-ai/langmem) - LangChain memory
- [Google AOMA](https://github.com/GoogleCloudPlatform/generative-ai/tree/main/gemini/agents/always-on-memory-agent)

### Research Papers
- [Zep: A Temporal Knowledge Graph Architecture for Agent Memory](https://arxiv.org/abs/2501.13956) - Rasmussen 2025
- [Mem0: Building Production-Ready AI Agents with Scalable Long-Term Memory](https://arxiv.org/abs/2504.19413) - 2025
- [Users' Expectations and Practices with Agent Memory](https://doi.org/10.1145/3706599.3720158) - Jones et al., CHI EA '25
- [Memory in the Age of AI Agents: A Survey](https://arxiv.org/abs/2512.13564) - Dec 2025
- [A-Mem: Agentic Memory for LLM Agents](https://arxiv.org/html/2502.12110v11) - Zettelkasten approach
- [MemOS: An Operating System for Memory-Augmented Generation](https://arxiv.org/html/2505.22101v1) - 2025
- ICLR 2026 Workshop: [MemAgents](https://openreview.net/forum?id=U51WxL382H)

### HackerNews Discussions
- [Agent Recall Show HN](https://news.ycombinator.com/item?id=47165499) - architecture discussion
- [Knowledge graphs for agent memory](https://news.ycombinator.com/item?id=43940654) - practitioner experience
- [Mem0 limitations](https://news.ycombinator.com/item?id=46891715) - behavioral pattern blindness
- [Google AOMA](https://news.ycombinator.com/item?id=47290892)

### Blog Posts and Articles
- [Graphlit Survey of AI Agent Memory Frameworks](https://www.graphlit.com/blog/survey-of-ai-agent-memory-frameworks) - Oct 2025
- [Letta Benchmarking: Is a Filesystem All You Need?](https://www.letta.com/blog/benchmarking-ai-agent-memory) - Mar 2026
- [Glen Rhodes: Why agents need a database](https://glenrhodes.com/why-ai-agents-need-a-database-for-memory-not-just-a-flat-file-like-skill-md/)
- [Letta v1 Agent Loop](https://www.letta.com/blog/letta-v1-agent) - architecture decisions

## 7. Source Quality Assessment

**High confidence**: engram, agent-recall, and Letta architectures are well-documented with inspectable source code. The CHI '25 paper provides the only rigorous user study on memory expectations. Letta's LoCoMo benchmark is reproducible.

**Medium confidence**: Mem0 and Zep benchmark claims conflict with each other. Each vendor publishes favorable results. Google AOMA is a reference implementation, not production-hardened. OpenMemory documentation is marketing-heavy.

**Low confidence**: Behavioral pattern learning remains theoretical. No production system demonstrates it. The "virtual filesystem" pattern is described in commentary but lacks reference implementations.

**Gap**: No research compares local-first SQLite memory systems head-to-head. All benchmarks test cloud-scale systems. Developer experience reports for local memory systems are sparse.

## 8. Open Questions

1. **Consolidation scheduling**: Google AOMA uses a 30-minute timer. What is the right cadence for local-first systems where usage is bursty (coding sessions)?
2. **Memory decay**: OpenMemory's per-sector adaptive forgetting is the most sophisticated decay model but untested at scale. When should memories expire?
3. **Cross-project memory sharing**: agent-recall's scope chains are the only implementation. How should memories from Project A inform work on Project B when projects overlap?
4. **Correction-as-signal**: No system treats user corrections as the highest-priority memory signal, despite HN consensus that they should be.
5. **Human curation UI**: The CHI research establishes clear user needs (folder-like organization, on/off toggles, transparency about which memories influence responses). No local-first system addresses these.
6. **Hybrid interface**: Can a SQLite-backed system expose a filesystem-like interface to agents while maintaining structured query capabilities underneath?

## 9. Actionable Takeaways

For building a local-first SQLite memory system:

1. **Start with engram's data model** as the baseline: observations with type/scope/project/topic_key, FTS5 search, deduplication via content hash, progressive disclosure for token efficiency.

2. **Add agent-recall's scope chains** for multi-project isolation with inheritance. The `global -> user -> project` hierarchy maps directly to real developer workflows.

3. **Add bitemporal history** from agent-recall for slots/facts that change over time. Archive old values rather than deleting.

4. **Implement periodic consolidation** from Google AOMA: a scheduled LLM pass that merges duplicates, resolves contradictions, and prunes stale entries.

5. **Expose MCP tools** following engram's 13-tool pattern: save, update, delete, search, context, timeline, session lifecycle.

6. **Build a human curation interface** addressing CHI findings: hierarchical memory browser, per-memory on/off toggles, scope visualization, and transparency about which memories were used in the last response.

7. **Capture corrections explicitly**: when a user corrects agent behavior, store the correction with highest confidence/importance. This is the gap every system misses.

8. **Decouple interface from storage**: let agents interact via familiar filesystem-like or search primitives, backed by SQLite with proper indexing underneath. The Letta benchmark proves agents perform better with familiar tools.
