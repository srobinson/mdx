---
title: Helioy Ecosystem Architecture
type: design
tags: [helioy, architecture, nancyr, am, fmm, mdcontext, ecosystem]
summary: Complete architecture vision for the Helioy ecosystem — libraries, products, agent model, and infrastructure
status: active
created: 2026-02-20
updated: 2026-02-20
project: helioy
confidence: high
---

# Helioy Ecosystem Architecture

## Overview

**Helioy** (helioy.com) is an umbrella brand for AI developer tooling. The ecosystem comprises three individually-releasable libraries, two products (one folding into the other), and shared infrastructure for knowledge management and skill composition.

The thesis: LLM context windows are the bottleneck. Every token should be high-value. Navigation tokens are waste. Helioy tools maximize signal-to-noise in AI-assisted development.

## Ecosystem Map

```
┌─────────────────────────────────────────────────────────┐
│  HELIOY ECOSYSTEM                                       │
│                                                         │
│  ┌─────────────── LIBRARIES ──────────────────┐         │
│  │                                            │         │
│  │  attention-matters (am)                    │         │
│  │    Geometric memory engine                 │         │
│  │    S3 manifold, SLERP drift, Kuramoto      │         │
│  │                                            │         │
│  │  fmm (Frontmatter Matters)                 │         │
│  │    Code structural intelligence            │         │
│  │    Auto-generated metadata for navigation  │         │
│  │                                            │         │
│  │  mdcontext                                 │         │
│  │    Token-efficient markdown analysis        │         │
│  │    BM25 + semantic hybrid search           │         │
│  └────────────────────────────────────────────┘         │
│                                                         │
│  ┌─────────────── PRODUCTS ───────────────────┐         │
│  │                                            │         │
│  │  nancyr                                    │         │
│  │    Rust orchestrator wrapping Claude Code   │         │
│  │    Hub-and-spoke multi-agent coordination  │         │
│  │    Adaptive TUI (chat + agent dashboard)   │         │
│  │                                            │         │
│  │  dae-app → folds INTO nancyr               │         │
│  │    Chat TUI + daemon + memory integration  │         │
│  └────────────────────────────────────────────┘         │
│                                                         │
│  ┌─────────────── INFRASTRUCTURE ─────────────┐         │
│  │  ~/.mdx          Knowledge base            │         │
│  │  helioy:* skills  Claude Code skills       │         │
│  │  fmm-bench       Benchmark harness         │         │
│  └────────────────────────────────────────────┘         │
└─────────────────────────────────────────────────────────┘
```

## Libraries

### attention-matters (am)

Pure Rust geometric memory engine. Zero I/O in the core. Models recall as activation on a closed S3 manifold.

- **am-core**: Quaternions, phasors, drift, interference, Kuramoto coupling, context composition
- **am-store**: SQLite persistence (brain.db per developer, not per project)
- **am-cli**: CLI for ingestion, querying, import/export

All constants derive from phi (golden ratio) and pi. No magic numbers. The math decides what matters.

Key concept: **One Brain** — single brain.db per developer. Episodes tagged with project_id for filtering, but IDF calculates across the entire corpus. Words common across many projects get correctly lower weight.

### fmm (Frontmatter Matters)

Rust CLI + npm wrapper. Generates structural metadata for source code files so LLMs can understand "what does this file do?" without scanning entire files. 90%+ token savings on navigation.

### mdcontext

TypeScript + Effect. Token-efficient markdown analysis for LLM consumption. 7 MCP tools, hybrid search (BM25 + HNSW semantic), 5 embedding providers, section-level indexing, 80%+ token compression.

**Strategy**: mdcontext stays general-purpose open source. Works on any markdown, zero conventions required. Helioy-specific features (frontmatter filtering, tag search, \_versions/ handling) live in a separate adapter layer.

## Products

### nancyr — The Orchestrator

Rust process supervisor that wraps Claude Code CLI (`claude -p`). Never a Claude Code session itself. Hub-and-spoke multi-agent coordination with adaptive TUI.

**6 crates**: nancy-core, nancy-brain, nancy-driver, nancy-monitor, nancy-runtime, nancy-cli.

**Key principle**: CLI wrapping is the default, not direct API calls. Provider subscriptions are heavily subsidized — users pay $20/month for Max, not per-token. Adapter pattern allows API as an optional backend.

#### Product Flow

```
User types "nancyr"
        │
        ▼
┌─── INIT ────────────────────────────────────────────┐
│  • Detect context (pwd, git state, Linear project)  │
│  • Query AM for relevant memories                    │
│  • Load project config if exists                     │
└──────────────────────┬──────────────────────────────┘
                       ▼
┌─── CHAT (full screen) ──────────────────────────────┐
│  • ratatui TUI, streaming conversation              │
│  • Requirements gathering, clarification            │
│  • User describes what they want                    │
│  • System proposes plan                             │
└──────────────────────┬──────────────────────────────┘
                       ▼
┌─── PLAN ────────────────────────────────────────────┐
│  • Decompose into tasks (Linear sub-issues)         │
│  • Assign agent archetypes (researcher, coder, etc) │
│  • Define dependencies, quality gates               │
│  • Human approves plan                              │
└──────────────────────┬──────────────────────────────┘
                       ▼
┌─── ORCHESTRATE ─────────────────────────────────────┐
│  • Spawn agents (each in own git worktree)          │
│  • TUI animates: full screen → 50/50 split          │
│  •   Left: chat continues                           │
│  •   Right: agent dashboard (status, progress)      │
│  • Hub-and-spoke comms (file-based IPC)             │
└──────────────────────┬──────────────────────────────┘
                       ▼
┌─── RESEARCH ────────────────────────────────────────┐
│  • Research agents explore, persist to ~/.mdx       │
│  • Findings surface to orchestrator                 │
│  • Orchestrator distributes context to workers      │
└──────────────────────┬──────────────────────────────┘
                       ▼
┌─── REVIEW ──────────────────────────────────────────┐
│  • Agents push + gh pr create                       │
│  • Claude reviews PR (automated)                    │
│  • Optional human review (flag-controlled)          │
│  • Conflicts resolved by human or orchestrator      │
└──────────────────────┬──────────────────────────────┘
                       ▼
┌─── EXECUTE ─────────────────────────────────────────┐
│  • Approved changes merged                          │
│  • Retrospective generated                          │
│  • Learnings feed back into AM and skills           │
└─────────────────────────────────────────────────────┘
```

#### Adaptive TUI UX

State-driven layout with animated transitions (ratatui):

1. **Chat mode**: Full screen. User types requirements, system responds.
2. **Orchestration mode**: Chat animates to 50% left column. Agent dashboard appears in 50% right column showing: agent status, progress bars, message feed, resource usage.
3. **Focus mode**: User can expand any panel to full screen, collapse back.

This is the world-class UX target. The transition itself is part of the experience.

#### CLAUDE.md Prompt Compiler — 6 Layers

Nancy compiles a CLAUDE.md for each worker agent:

1. **Role Template** — static per archetype (researcher, coder, reviewer)
2. **Task Specification** — decomposed from reasoning engine
3. **DAE Context** — geometric memory query, curated per worker
4. **Project State** — live git status, modified files, test results (FMM fits here)
5. **Constraints and Budget** — token budget, scope, quality gates
6. **Comms Protocol** — inbox/outbox, output format, escalation triggers

Nancy talks THROUGH config, not TO Claude during execution.

#### Nancy's Supervision Loop

```
receive → assess → plan → dispatch → monitor → coordinate → evaluate → deliver
```

Single loop. Nancy manages its own fleet (not Claude's subagent API — provider-agnostic). Nancy's brain = cheap model (Haiku/Flash) for reasoning, separate from worker models.

### dae-app → Folds Into nancyr

dae-app (1,196 LOC) has working code that nancyr needs:

- ratatui TUI with streaming chat (460 LOC)
- Unix socket daemon with lifecycle management (350 LOC)
- Memory integration wrapping am-core/am-store (386 LOC)

The direct Anthropic API driver needs refactoring to CLI wrapping (adapter pattern).

## Agent Model

### Core Properties

**Idempotent agent runs** — FUNDAMENTAL constraint:

- Human can pause or terminate all agents at any time
- Agents checkpoint incrementally
- Agents are resumable from any checkpoint
- Agents don't corrupt shared state on termination
- Each agent runs in its own git worktree (isolation)

**Human-in-the-loop** — always available:

- Orchestrator doesn't need human by default
- Human retains override control at all times
- Configurable via flag (e.g., `--human-in-the-loop`)
- Human can pause all work — agents immediately paused or terminated

### Communication Model

Hub-and-spoke through orchestrator. No peer-to-peer agent communication.

**File-based IPC** (proven by bash nancy):

```
.nancy/tasks/<task>/comms/
├── orchestrator/
│   ├── inbox/
│   ├── outbox/
│   └── archive/
└── worker/
    ├── inbox/
    ├── outbox/
    └── archive/
```

Markdown message files with typed headers (Type/From/Priority/Time). fswatch for real-time detection. Pre-tool-use hooks force agents to check inbox. Prompt injection via tmux send-keys.

**Agent → Orchestrator messages:**

| Type           | Purpose                                     |
| -------------- | ------------------------------------------- |
| blocker        | Agent is stuck, needs guidance              |
| progress       | Status update, percentage, current activity |
| finding        | Discovery worth sharing with other agents   |
| review-request | Work ready for review                       |
| done           | Task completed                              |

**Orchestrator → Agent messages:**

| Type      | Purpose                               |
| --------- | ------------------------------------- |
| directive | New instruction or task adjustment    |
| guidance  | Context from another agent's findings |
| context   | Additional information for the task   |
| stop      | Terminate immediately                 |
| pause     | Suspend work, checkpoint state        |

### Execution Phase

1. Orchestrator creates **git worktree per agent** (branch isolation)
2. On completion: agent runs `push` + `gh pr create`
3. Claude reviews PR (automated review agent)
4. Optional human review (env var / flag controlled)
5. Merge conflicts resolved by human or orchestrator

## The Learning Loop (THE USP)

Skills, hooks, and prompts are **first-class artifacts** that the system can reason about and improve.

### Three Feedback Loops

**Loop 1 — Per-task** (immediate):
Retrospective generator evaluates outcome vs. CLAUDE.md prompt. What worked? What didn't? Adjustments for next task.

**Loop 2 — Pattern crystallizer** (days/weeks):
Detect meta-patterns across retrospectives. Evolve role templates. Update skill definitions. Surface recurring blockers.

**Loop 3 — Continuous geometric drift**:
DAE manifold drift, IDF reweighting, phasor interference. The memory system itself adapts — frequently co-activated concepts drift closer together on the manifold.

The system's own configuration (skills, hooks, prompts, templates) is a thing it can inspect, version, experiment with, and improve. This is the differentiator.

## Infrastructure

### ~/.mdx Knowledge Base

Centralized markdown document store. Shallow hierarchy by document type.

```
~/.mdx/
├── research/        # Research findings
├── decisions/       # ADRs
├── design/          # Architecture docs, RFCs
├── sessions/        # Session summaries
├── projects/        # Per-project context
├── retrospectives/  # Post-mortems
├── reference/       # Stable reference material
└── _schema.md       # Frontmatter contract
```

Per-category `_versions/` subdirectories for document history. Filenames are kebab-case slugs, no dates. Frontmatter dates auto-managed by the helioy:knowledge-base skill.

### Skills System

All Helioy skills prefixed with `helioy:`:

- **helioy:knowledge-base** — Manages ~/.mdx (CRUD, versioning, search)
- **helioy:research** — Spawns parallel subagents, persists findings to ~/.mdx
- **helioy:skill-creator** — Creates new skills following Helioy conventions

Skills follow progressive disclosure: metadata always in context, body on trigger, resources as needed.

### Documentation Approach

Hybrid of three patterns:

1. **ARCHITECTURE.md** per repo — high-level map, updated on structural changes
2. **ADRs** per repo — decision log in `decisions/` within ~/.mdx
3. **Lightweight Design Docs** — RFC-lite template for cross-cutting concerns:
   - Problem, Appetite, Proposed Solution, Alternatives, Rabbit Holes, Open Questions

## Terminology

| Term      | Definition                                                    |
| --------- | ------------------------------------------------------------- |
| Project   | Body of work (Linear project or git repo)                     |
| Task      | Discrete unit within a project (Linear issue)                 |
| Agent     | Autonomous process working on a task (researcher, coder, etc) |
| Session   | One agent's lifecycle (spawn → work → complete/fail)          |
| Worker    | Synonym for agent when emphasizing execution                  |
| Directive | Message from orchestrator to agent                            |

## Repositories

| Repo              | Type    | Status  | Location                            |
| ----------------- | ------- | ------- | ----------------------------------- |
| attention-matters | Library | Active  | ~/Dev/LLM/DEV/DAE/attention-matters |
| fmm               | Library | Active  | ~/Dev/LLM/DEV/fmm                   |
| mdcontext         | Library | Active  | ~/Dev/LLM/DEV/mdcontext             |
| nancyr            | Product | Active  | ~/Dev/LLM/DEV/TMP/nancyr            |
| fmm-bench         | DevTool | Active  | ~/Dev/LLM/DEV/fmm-bench             |
| dae-app           | Product | Folding | ~/Dev/LLM/DEV/dae/dae-app           |

Future: all repos under `~/Dev/LLM/DEV/helioy/` (ALP-636).

## Milestones

### M0: Foundation (current)

- Bootstrap ~/.mdx knowledge base (ALP-631)
- Write this architecture document (ALP-632)
- Build helioy:knowledge-base skill (ALP-633)

### M1: Skills & Research

- Build helioy:research skill (ALP-634)
- Build helioy:skill-creator skill (ALP-635)
- Reorganize filesystem under helioy/ (ALP-636)

### M2: Integration

- mdcontext Helioy adapter layer (ALP-637)
- Integrate dae-app TUI/daemon into nancyr (ALP-638)

### M3: Multi-Agent Orchestration

- nancyr multi-agent spawn and coordination
- Adaptive TUI (full screen → 50/50 split)
- File-based IPC comms system
- Git worktree isolation per agent

### M4: Learning Loop

- Per-task retrospective generation
- Pattern crystallizer across sessions
- Skill/hook/prompt versioning and experimentation
