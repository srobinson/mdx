---
title: Session Continuity — Context Retrieval at Session Start
type: design
tags: [helioy, nancyr, memory, continuity, session, architecture]
status: draft
created: 2026-02-21
updated: 2026-02-21
---

# Session Continuity

How context flows into a Claude session, and what we expect to happen.

## The Problem

Every new Claude session starts cold. Context from the previous session — what was accomplished, what's in flight, what decisions were made — must be reconstructed. Today this happens through a mix of memory recall and filesystem exploration, but the result is inconsistent: sessions often "explore as if for the first time" even when the knowledge exists in retrievable form.

## Two Modes, Same Need

There are two execution modes. Both need **continuity**. Both need **full retrieval access**.

|                               | Local Dev (Interactive)        | nancyr Worker (Background)      |
| ----------------------------- | ------------------------------ | ------------------------------- |
| **Who starts it**             | Stuart launches `claude`       | Nancy spawns `claude -p`        |
| **Session lifetime**          | Minutes to hours, open-ended   | Single task iteration, bounded  |
| **Cold start**                | Retrieval discovers continuity | Nancy pre-compiles a head start |
| **Config ownership**          | User's `~/.claude/`            | Nancy's `CLAUDE_CONFIG_DIR`     |
| **Runtime access to context** | Full — AM, mdx, FMM via MCP    | Full — same tools, same access  |

### The key insight

Nancy pre-compiles a **head start**, not a **ceiling**. The compiled prompt gives the worker a running start, but the worker retains full access to AM, mdx, FMM, and Linear via MCP tools. Workers must be able to break out of compiled context when they encounter something unexpected, need deeper context, or discover the pre-compiled view was incomplete.

For local dev, continuity is not inherently unknown — it's **discoverable**. With the right retrieval tools and session handoff artifacts, a local session should reconstruct continuity as effectively as a pre-compiled prompt. The current experience of "exploring as if for the first time" is a tooling gap, not a fundamental limitation.

**What's common is retrieval.** Both modes query the same sources with the same tools. The difference is that Nancy front-loads retrieval at spawn time. But front-loading doesn't replace runtime access — it supplements it.

## Three Context Sources

### 1. attention-matters (Geometric Memory)

**What it holds:** Past session exchanges, conscious insights (architecture decisions, user preferences, debugging patterns), cross-project knowledge.

**Retrieval:** `am_query` with task-relevant terms. Returns conscious recall (explicitly marked important), subconscious recall (relevant past conversations), and novel connections (lateral associations).

**Current gap:** Generic queries ("what are we working on") return generic results. Query quality determines recall quality. Recent work may not surface if the session ended before enough exchanges were buffered (needs 3 for an episode) or if the salient markers don't match the query terms.

### 2. mdx/mdcontext (Structured Documents)

**What it holds:** Design docs, architecture decisions, research notes, session summaries, project status, retrospectives. All in `~/.mdx/` with frontmatter metadata.

**Retrieval:** `md_keyword_search` for structural queries, `md_search` for semantic (requires embeddings). Path-based filtering by category (`design/`, `sessions/`, `decisions/`).

**Current gap:** No semantic search until embeddings are built (`mdcontext index --embed`). No MCP tool for building embeddings autonomously. No session summary documents being written yet (ALP-655).

### 3. fmm/frontmatter-matters (Code Structure)

**What it holds:** Export maps, import graphs, dependency trees, LOC — structural intelligence for every source file via `.fmm` sidecars.

**Retrieval:** `fmm_lookup_export` for O(1) symbol lookup, `fmm_file_info` for file profiles, `fmm_dependency_graph` for impact analysis. No reading source needed for navigation.

**Current gap:** FMM sidecars must exist (generated via `fmm generate`). The MCP server needs `.fmmrc.json` in the project root to know which directory to index.

## What We Expect at Session Start

### Local Dev (Interactive)

**Goal:** The session knows where we left off. No full-repo surveys. No rediscovering what was just done.

Expected sequence:

1. **SessionStart hook fires** — triggers memory recall automatically
2. **AM query with first user message** — returns relevant conscious + subconscious recall
3. **If user asks "where are we?"** — answer from memory + mdx session docs, NOT from `git log` across all repos
4. **Code navigation** — use FMM for structure, not grep. Read source only when needed.
5. **During session** — buffer exchanges, mark insights salient, strengthen connections
6. **Before session ends** — write session summary to `~/.mdx/sessions/` (ALP-655)

What should NOT happen:

- Running `git log` across all 5+ repos to survey state
- Re-exploring directory structures already mapped by FMM
- Presenting generic architecture summaries instead of recent-work-specific context
- Missing work done in the immediately previous session

### nancyr Worker (Background)

**Goal:** Fast start with deep context, plus full autonomy to discover more.

Nancy's prompt compiler assembles 6 layers into CLAUDE.md before spawning the worker:

1. **Role Template** — static blueprint per worker archetype (researcher, coder, reviewer)
2. **Task Specification** — decomposed subtask from Nancy's reasoning engine
3. **DAE Context** — AM query results, curated and budget-packed for this specific task
4. **Project State** — live git status, modified files, FMM code map, test results
5. **Constraints & Budget** — token budget, scope boundaries, quality gates, iteration limits
6. **Comms Protocol** — inbox/outbox paths, output format, escalation triggers

But the worker is NOT confined to this compiled context. It has full MCP access to:

- **AM** — query for deeper context, buffer its own exchanges, mark its own insights
- **mdx** — search design docs, reference material, past session summaries
- **FMM** — navigate code structure beyond what was pre-compiled
- **Linear** — read issue details, comments, related issues

The compiled prompt is a **warm cache**. The MCP tools are the **full database**. Nancy gives you the 80% you'll need. The tools let you get the other 20% when you need it.

After the worker completes, Nancy:

- Ingests the session into AM (feedback loop)
- Writes outcome to `.nancy/sessions/` (journal)
- Boosts/demotes memories based on whether they led to success (relevance feedback)

## The Retrieval Layer

Both modes perform the same retrieval operations. Nancy front-loads them; local dev triggers them on demand. But both have continuous access throughout the session.

| Retrieval     | At Start                                               | During Session         |
| ------------- | ------------------------------------------------------ | ---------------------- |
| AM query      | SessionStart hook (local) / Nancy pre-compile (worker) | On-demand — both modes |
| mdx search    | On-demand (local) / excerpted into prompt (worker)     | On-demand — both modes |
| FMM lookup    | On-demand (local) / code map in prompt (worker)        | On-demand — both modes |
| Linear issues | On-demand (local) / task spec injected (worker)        | On-demand — both modes |

The "During Session" column is identical. That's the point. Pre-compilation is an optimization for cold start, not a constraint on runtime capability.

## Gaps to Close

### Immediate (ALP-655: Session Retrospective)

Write a structured session summary before context is lost. Two mechanisms:

- **SessionEnd/Stop hook** — fires when Claude session ends, writes `~/.mdx/sessions/YYYY-MM-DD-summary.md` with what was accomplished, decisions made, open threads
- **PreCompact hook** — fires before context compression, captures key context before it's lost
- **AM buffer flush** — ensure all buffered exchanges become episodes before exit

This is the single highest-leverage fix. Without it, the geometric memory captures vibes but not specifics.

### Near-term

- **Smarter session-start queries** — query AM with project-specific terms, not generic "what are we working on". Query with the names of recently-touched repos/issues.
- **mdcontext embeddings bootstrap** — add MCP tool or hook that builds embeddings on first index, so semantic search works without manual CLI invocation.
- **Session history tool** — expose `~/.mdx/sessions/` as queryable context so sessions can find "what did the last session do?"

### Architecture (nancyr Phase 2+)

- **Budget-aware retrieval** — AM's `am_query` with `max_tokens` already works. Extend to mdcontext and FMM so the prompt compiler can say "give me the best context that fits in N tokens."
- **Relevance feedback loop** — after each worker session, tell AM what helped (boost) and what didn't (demote). The manifold learns from outcomes.
- **Cross-worker context sharing** — when multiple workers run in parallel, share relevant discoveries through the inbox system, backed by AM batch queries.
- **Worker self-extension** — workers that discover their compiled context is insufficient should be able to request richer context from Nancy mid-session, not just query tools directly.

## Design Principles

> **Continuity is the default experience.** Every session should feel like resuming, not restarting.

> **Pre-compilation is a head start, not a ceiling.** Workers always retain full retrieval access. The compiled prompt is a warm cache. The tools are the full database.

> **Retrieval is the common foundation.** Both modes use the same AM/mdx/FMM queries. The difference is timing (pre-session vs on-demand), not capability.

> **Context confinement is an anti-pattern.** An agent that can only see what was compiled into its prompt will fail on any task that deviates from the predicted path. Full tool access is non-negotiable.
