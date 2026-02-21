---
title: "mdcontext — Linear Project Status"
type: projects
tags: [mdcontext, linear, status, helioy]
summary: "Current Linear issues, milestones, and project status for mdcontext"
status: active
created: 2026-02-21
updated: 2026-02-21
project: mdcontext
---

# mdcontext -- Linear Project Status

Last synced from Linear: 2026-02-21

## Project Overview

**mdcontext** is a CLI tool that generates AI-optimized context from markdown codebases.

- **Linear Project URL:** https://linear.app/alphabio/project/mdcontext-33a6d607392c
- **Project Status:** Canceled (standalone project superseded by Helioy ecosystem integration)
- **Team:** Alphabio
- **Created:** 2026-01-21
- **Last Updated:** 2026-02-18

### Core Features

- Structural indexing -- parse and index markdown documents with sections, headings, and links
- Semantic search -- BM25 keyword + vector embeddings with RRF fusion
- Tree output -- visualize document structure for AI consumption
- Watch mode -- real-time index updates on file changes

### Tech Stack

- TypeScript + Effect (functional error handling, dependency injection)
- @effect/cli for command parsing
- OpenAI embeddings (text-embedding-3-small) with HNSW vector store
- Vitest for testing

---

## Milestones

| Milestone                | Progress | Target Date |
| ------------------------ | -------- | ----------- |
| Errors as Values         | 0%       | None set    |
| Better Config Management | 0%       | None set    |

---

## Project Documents

| Document                    | URL                                                                                     | Created    |
| --------------------------- | --------------------------------------------------------------------------------------- | ---------- |
| Search & Embeddings Roadmap | [View](https://linear.app/alphabio/document/search-and-embeddings-roadmap-392e021cacd4) | 2026-01-21 |

### Search & Embeddings Roadmap Summary

Four-phase plan for improving search capabilities:

1. **Phase 1 (Quick Wins):** Fix dimension mismatch, dynamic efSearch, query preprocessing, heading match boost
2. **Phase 2 (Hybrid Search):** BM25 integration, RRF fusion, `--mode hybrid` CLI flag (15-30% recall improvement target)
3. **Phase 3 (Local/Offline):** Ollama provider, provider selection CLI, nomic-embed-text testing (zero-cost offline search)
4. **Phase 4 (Advanced):** Cross-encoder re-ranking, HyDE query expansion, alternative API providers (Voyage AI)

---

## Issues Directly in mdcontext Project (50 total)

### Completion Summary

- **Done:** 48 issues
- **In Progress:** 1 issue (ALP-263: User Feedback & Feature Requests Tracking)
- **Backlog/Todo:** 1 issue

The standalone mdcontext project is largely complete. Nearly all 50 issues have been marked Done, covering:

- Multi-provider embedding support (OpenAI, Ollama, LM Studio, OpenRouter)
- Semantic search threshold tuning and multi-word search fixes
- Fuzzy/stemmed search, progressive refinement, cross-file operations
- Section exclusion, duplicate detection, relevance ranking improvements
- Progress indicators, CLI timeout flags, error handling
- Effect Redacted for API key safety
- Contributing docs and CI

---

## mdcontext Issues in Other Projects

mdcontext plays a significant role across two other Linear projects: **meta** and **Helioy**.

### In the "meta" Project

#### ALP-241: Knowledge Graph Validation System for mdcontext (In Progress)

- **Priority:** Urgent | **Assignee:** Stuart Robinson
- **URL:** https://linear.app/alphabio/issue/ALP-241/knowledge-graph-validation-system-for-mdcontext
- **Objective:** Build knowledge graph from 2,066 agentic-flow markdown files to validate mdcontext capabilities
- **Assertion:** Worker only needs mdcontext CLI -- no custom parsing/extraction code
- **Working dir:** `/Users/alphab/Dev/LLM/DEV/meta/kg-validation/`
- **Success criteria:** 18K+ nodes, 80K+ edges in Neo4j, all from mdcontext CLI output

Sub-issues (all Backlog, all Urgent priority):

| ID      | Title                                              | Status  |
| ------- | -------------------------------------------------- | ------- |
| ALP-247 | Install mdcontext globally or as dependency        | Backlog |
| ALP-248 | Run mdcontext index on agentic-flow corpus         | Backlog |
| ALP-249 | Examine mdcontext output structure                 | Backlog |
| ALP-251 | Load document nodes from mdcontext JSON into Neo4j | Backlog |
| ALP-252 | Load section nodes from mdcontext JSON into Neo4j  | Backlog |
| ALP-253 | Create LINKS_TO edges from mdcontext links.json    | Backlog |
| ALP-254 | Use mdcontext search to find similar documents     | Backlog |
| ALP-255 | Extract concepts from section headings             | Backlog |
| ALP-261 | Verify graph meets success criteria                | Backlog |
| ALP-262 | Remove custom extraction code and dependencies     | Backlog |
| ALP-242 | KG-001: Infrastructure & Extraction Pipeline       | Todo    |

#### ALP-340: Vision: LLM-Native Code Infrastructure (Backlog)

- **Priority:** Urgent
- **URL:** https://linear.app/alphabio/issue/ALP-340/vision-llm-native-code-infrastructure
- Frames mdcontext as "Layer 1" in a 5-layer evolution:
  1. **mdcontext** -- semantic search + embeddings for markdown
  2. **fmm** -- apply mdcontext concept to code (structured metadata per file)
  3. **The Problem** -- LLMs skip comments/frontmatter
  4. **The Solution** -- MCP tools make frontmatter executable
  5. **Agent Memory (Nancy)** -- episodic memory extraction

Sub-issues:

| ID      | Title                                                  | Status  | Priority |
| ------- | ------------------------------------------------------ | ------- | -------- |
| ALP-344 | Document mdcontext capabilities and integration points | Backlog | Medium   |
| ALP-342 | Nancy: Agent memory extraction from session logs       | Backlog | High     |

### In the "Helioy" Project

mdcontext is one of three individually releasable libraries in the Helioy ecosystem (alongside `attention-matters` and `frontmatter-matters`).

#### ALP-630: Helioy Architecture & Infrastructure Bootstrap (In Progress)

- **Priority:** High
- **URL:** https://linear.app/alphabio/issue/ALP-630/helioy-architecture-and-infrastructure-bootstrap
- Key decisions: Helioy umbrella brand, three libraries (am, fmm, mdcontext), CLI wrapping as default, ~/.mdx centralized knowledge base

Completed sub-issues:

- ALP-631: Bootstrap ~/.mdx knowledge base directory structure (Done)
- ALP-632: Write helioy-architecture.md design document (Done)
- ALP-633: Build helioy:knowledge-base skill (Done)

#### ALP-637: mdcontext Helioy adapter layer (Backlog)

- **Priority:** Medium
- **URL:** https://linear.app/alphabio/issue/ALP-637/mdcontext-helioy-adapter-layer
- **Parent:** ALP-630
- Creates a Helioy-specific adapter for mdcontext with:
  - Frontmatter-aware search filtering (tags, type, status, project)
  - Tag-based search/aggregation
  - Document type classification from frontmatter
  - `_versions/` directory handling
  - Integration with attention-matters (ingest indexed docs into AM)
- Depends on mdcontext npm package having MCP serve command
- Partly folds into the Helioy plugin (ALP-639)

#### ALP-654: Create foundational reference docs in ~/.mdx (Backlog)

- **Priority:** Urgent
- Includes creating `~/.mdx/reference/npm-package-names.md` covering mdcontext naming

---

## Cross-Project References

mdcontext is referenced in several additional issues by pattern or comparison:

| ID      | Title                                                  | Context                                                                          | Status |
| ------- | ------------------------------------------------------ | -------------------------------------------------------------------------------- | ------ |
| ALP-535 | World-class CLI help system for fmm                    | mdcontext cited as reference implementation for help systems                     | Done   |
| ALP-536 | Custom main help renderer with MCP tools and workflows | References mdcontext help patterns                                               | Done   |
| ALP-537 | Rich per-command help with examples and notes          | References mdcontext's approach                                                  | Done   |
| ALP-538 | Error messages with typo suggestions                   | References mdcontext's error-handler.ts (655 LOC)                                | Done   |
| ALP-561 | `am inspect` -- browse memories                        | Example shows correcting "fmm repo is github.com/srobinson/fmm -- NOT mdcontext" | Done   |

---

## Current State Summary

1. **Standalone mdcontext project:** Canceled as a separate Linear project (48/50 issues Done). The tool itself is functional and feature-complete for its core use case.

2. **Active integration work (Helioy):** mdcontext is being integrated as one of three core libraries in the Helioy ecosystem. The adapter layer (ALP-637) is in Backlog, pending the npm package having MCP serve capability.

3. **Validation work (meta):** The Knowledge Graph validation system (ALP-241) is In Progress but all sub-issues remain in Backlog/Todo. This work validates mdcontext by building a Neo4j graph from 2,066 markdown files using only the CLI.

4. **Vision alignment:** mdcontext is positioned as "Layer 1" in the LLM-Native Code Infrastructure vision, providing the foundation that fmm and Nancy build upon.

5. **Key blockers/next steps:**
   - mdcontext npm package needs MCP serve command (for ALP-637)
   - KG validation sub-issues need to progress (ALP-247 through ALP-262)
   - Documentation of mdcontext capabilities (ALP-344) is pending
   - Search & Embeddings Roadmap phases are defined but milestones show 0% progress
