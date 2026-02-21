---
title: "Session Lifecycle — Startup & Shutdown Workflows"
type: design
tags:
  [helioy, session, lifecycle, startup, shutdown, am, fmm, mdcontext, nancyr]
summary: "Two entry points (interactive claude, programmatic nancy -p), optimized startup discovery, and shutdown memory extraction"
status: active
created: 2026-02-21
updated: 2026-02-21
project: helioy
confidence: high
---

# Session Lifecycle

## Two Entry Points

### 1. Interactive: Stuart types `claude`

The agent starts cold. It doesn't know where it is, what the project is, or what the task is. First operation is always: **"Where am I? What is my task?"**

Discovery sequence:

```
SessionStart hook fires
  └── just preflight (plugin sync, mdx index, am sync)

Agent receives system-reminder
  └── "Call am_query with first user message"

Agent discovers context:
  1. git log — recent commits tell the story
  2. am_query — geometric memory recalls prior sessions, decisions, patterns
  3. mdcontext — structured knowledge base (design docs, objectives, research)
  4. fmm — codebase structure (exports, imports, dependencies, LOC)
  5. CLAUDE.md — project conventions and navigation priority
```

The agent assembles its own context from these sources. The human provides the task.

### 2. Programmatic: nancyr spawns `claude -p`

Nancyr owns the entire `.claude` dir via `CLAUDE_CONFIG_DIR`. We own the prompt. We can be smart and feed the agent everything it needs:

```
nancyr compiles prompt:
  1. Working directory
  2. FMM codebase map (pre-scanned)
  3. AM memory context (pre-queried)
  4. Session continuity (journal of prior runs)
  5. Token budget awareness
  6. The actual task (from Linear issue → SPEC.md)

nancyr spawns: claude -p --output-format stream-json
  └── Agent starts with full context, no discovery needed
```

**Key difference**: Interactive mode discovers. Programmatic mode is pre-compiled.

## Startup: Git Context

Recent git history is extremely informative. Should be part of every startup:

```bash
git log -n 10 --pretty=format:"Commit: %h%nDate: %ad%nMessage: %B%n--End--" --date=short
```

This tells the agent:

- What was worked on recently
- The pace and pattern of changes
- Co-authored commits (which agent sessions produced what)
- What branch we're on and how far ahead/behind

For interactive mode: agent runs this as part of discovery.
For programmatic mode: nancyr includes it in the compiled prompt.

## Startup: Tool Synergy

Four tools available at startup, each with a distinct role:

| Tool          | What it provides                                               | Token cost    | Speed   |
| ------------- | -------------------------------------------------------------- | ------------- | ------- |
| **git log**   | Recent commit history, branch state                            | ~500 tokens   | Instant |
| **am**        | Prior session context, decisions, patterns, debugging insights | ~1-3k tokens  | ~100ms  |
| **mdcontext** | Structured knowledge (design docs, research, objectives)       | ~1-5k tokens  | ~200ms  |
| **fmm**       | Codebase structure (every export, import, dependency, LOC)     | ~2-10k tokens | ~100ms  |

### AM ↔ mdcontext Overlap

AM and mdcontext serve different purposes but have overlap:

- **AM**: Conversational memory. Episodes from sessions. Geometric manifold. Good at "what did we decide about X?" and "what happened last time I tried Y?"
- **mdcontext**: Structured documents. Authored knowledge. Good at "what's the architecture?" and "what are the objectives?"

The overlap: both contain knowledge about the project. A design decision might exist as an AM salient memory AND as a `~/.mdx/decisions/` document.

**Resolution**: They complement, don't compete:

- AM is the **fast recall** layer — geometric query finds relevant context in ~100ms
- mdcontext is the **deep reference** layer — structured docs with full detail
- AM can surface "there's a design doc about X" which leads to mdcontext lookup
- Session logs feed AM automatically; design docs feed mdcontext manually

**Future opportunity**: AM could index mdcontext documents as episodes, creating a unified query surface. Query AM → get pointers to both prior conversations AND structured docs.

## Shutdown: Memory Extraction

When a Claude session ends, valuable context exists in the session transcript that should become AM memories.

### Current State

`am sync` runs at session start (via preflight) and ingests prior session transcripts. This is reactive — memories from session N are available starting in session N+2 (synced at start of N+1, but N+1 has already started).

### Desired State

On session close/exit:

1. Deconstruct the session transcript
2. Extract substantive exchanges (skip tool calls, file reads, boilerplate)
3. Create AM episodes from the meaningful content
4. Mark any architecture decisions or insights as salient
5. Memories available immediately in session N+1

### Implementation Options

1. **SessionEnd hook** — if Claude Code supports it, run `am sync` on exit
2. **nancyr post-processing** — nancyr already has the stream, can extract and ingest
3. **am sync improvements** — make sync smarter about what it extracts from transcripts
4. **Hybrid** — hook for interactive, nancyr for programmatic

### What to Extract

From a session transcript, these are high-value:

- Architecture decisions made
- Bugs found and fixed (root cause + solution)
- User corrections ("no, do it this way")
- Code patterns established
- Things that didn't work (negative knowledge)

Low-value (skip):

- File reads and tool outputs
- Boilerplate code generation
- Permission prompts and confirmations

## Open Questions

1. Should FMM be part of the SessionStart hook? (Pre-scan codebase on startup)
2. Can we make `am sync` run on session exit instead of next session start?
3. Should mdcontext documents be automatically ingested into AM for unified querying?
4. How much startup context is too much? Token budget for discovery vs actual work.
5. Should the interactive startup sequence be codified as a skill?
