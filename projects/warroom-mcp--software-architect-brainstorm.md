---
title: Warroom MCP Tools - Software Architect Brainstorm
author: engineering-software-architect
date: 2026-03-17
topic: warroom-mcp-brainstorm
tags: [architecture, agent-discovery, helioy-bus, mcp, warroom]
---

# Warroom MCP Tools: Agent Discovery Architecture

## Current State Analysis

Three distinct sources of agent definitions exist today:

| Source | Count | Location | Format |
|--------|-------|----------|--------|
| voltagent plugins | 141 | `~/.claude/plugins/cache/voltagent-subagents/{namespace}/{version}/{name}.md` | YAML frontmatter (name, description, model) + system prompt |
| helioy-tools agents | 33 | `helioy-plugins/plugins/helioy-tools/agents/{name}.md` | Same format |
| pr-review-toolkit | ~6 | Similar plugin cache structure | Same format |

Total: ~180 agent types across 12+ namespaces. Growing.

The bus server already stores `agent_type` and `profile` (JSON with owns, consumes, capabilities, domain, skills) per registered agent. `send_message` supports `role:` addressing. The warroom script shells out to tmux and passes `--agent {type}` to Claude Code.

## The Discovery Problem, Precisely Stated

An orchestrator agent receives a task (e.g., "build a billing dashboard"). It needs to:
1. Determine which specialist roles would be useful
2. Verify those roles actually exist as spawnable agent types
3. Spawn them via MCP tools instead of shell scripts

Step 1 is an LLM reasoning problem. Steps 2 and 3 are infrastructure problems. The design question is really about step 2: how does an agent go from "I want a backend-engineer" to confirmed knowledge that `helioy-tools:backend-engineer` is a valid, spawnable type with known capabilities?

## Option Analysis

### Option A: Filesystem Scan at Call Time

The simplest approach. A new MCP tool scans the known agent definition directories, parses frontmatter, returns results.

```python
@mcp.tool()
def discover_agents(query: str = "", namespace: str = "", category: str = "") -> list[dict]:
    """Search available agent types by keyword, namespace, or category."""
```

**What you gain**: Zero new infrastructure. Always reflects the actual state of installed agents. No sync problems.

**What you give up**: Scan latency (~180 files per call). No semantic search. Fragile coupling to directory layout conventions across plugin systems.

**Verdict**: Viable MVP. Breaks at 500+ agents due to scan cost and token budget for returning results.

### Option B: Indexed Registry (SQLite)

Add an `agent_types` table to the existing bus database. Populated by a build/index step (similar to fmm's `generate` command). Queried via MCP tools.

```sql
CREATE TABLE agent_types (
    qualified_name TEXT PRIMARY KEY,  -- "helioy-tools:backend-engineer"
    namespace      TEXT NOT NULL,     -- "helioy-tools"
    short_name     TEXT NOT NULL,     -- "backend-engineer"
    description    TEXT,
    model          TEXT DEFAULT 'sonnet',
    category       TEXT,              -- "engineering", "design", "research", etc.
    tags           TEXT,              -- JSON array of capability tags
    definition_path TEXT NOT NULL,    -- absolute path to .md file
    indexed_at     TEXT NOT NULL
);
CREATE INDEX idx_agent_types_ns ON agent_types(namespace);
CREATE INDEX idx_agent_types_cat ON agent_types(category);
```

MCP tools:

```python
@mcp.tool()
def search_agent_types(query: str = "", namespace: str = "", category: str = "", limit: int = 20) -> list[dict]:
    """Search the agent type registry. Returns qualified_name, description, model, category."""

@mcp.tool()
def get_agent_type(qualified_name: str) -> dict:
    """Get full metadata for a specific agent type including its system prompt."""

@mcp.tool()
def list_agent_categories() -> list[dict]:
    """List available categories with agent counts."""
```

**What you gain**: O(1) lookups. FTS5 for natural language search across descriptions. Category browsing. Stable interface decoupled from filesystem layout. Scales to 1000+ types.

**What you give up**: Requires an indexing step. Stale data if definitions change without re-indexing. Another table in the bus database (though this fits naturally).

**Verdict**: The right long-term answer. The indexing step is the same pattern fmm already established. Agents on this machine already expect "index then query."

### Option C: Curated Roster

A hand-maintained JSON/TOML file listing "approved" agents for warroom use.

```toml
[engineering]
agents = ["backend-engineer", "frontend-engineer", "rust-engineer", "code-reviewer"]

[design]
agents = ["ux-designer", "visual-designer", "brand-guardian"]
```

**What you gain**: Total control over quality. Small surface area. Predictable behavior.

**What you give up**: Manual maintenance burden. Every new agent requires a roster update. Defeats the purpose of a plugin ecosystem. Doesn't scale.

**Verdict**: Useful as a layer on top of Option B (a "recommended" flag in the registry), but wrong as the primary mechanism.

### Option D: Convention-Based Resolution

Rely on the `namespace:short_name` convention. The orchestrator guesses "I need a backend-engineer," the spawn tool tries to resolve it by walking known namespaces in priority order.

Resolution order: `helioy-tools:{name}` > `voltagent-*:{name}` > fuzzy match.

**What you gain**: Zero configuration. Works today with the existing `--agent` flag.

**What you give up**: Ambiguity when multiple namespaces define the same role name. Silent failures when a guessed name doesn't exist. No way to discover capabilities you don't already know about.

**Verdict**: This is what happens when you don't build discovery. It works until it doesn't, and the failure mode is silent.

## Recommended Architecture: Indexed Registry + Category Browsing

Option B as the foundation, with elements of C layered on top.

### Data Model

```
agent_types table (SQLite, in bus.db)
├── qualified_name   PK    "helioy-tools:backend-engineer"
├── namespace              "helioy-tools"
├── short_name             "backend-engineer"
├── description            first paragraph of .md body
├── model                  "sonnet" | "opus" | "haiku"
├── category               derived from namespace or explicit frontmatter
├── tags                   JSON ["api", "python", "microservices"]
├── priority               integer, lower = preferred (namespace-level)
├── definition_path        absolute path to .md file
└── indexed_at             ISO timestamp
```

Category derivation heuristic (from namespaces):

| Namespace Pattern | Category |
|-------------------|----------|
| `voltagent-lang:*` | language |
| `voltagent-infra:*` | infrastructure |
| `voltagent-qa-sec:*` | quality-security |
| `voltagent-biz:*` | business |
| `voltagent-core-dev:*` | core-development |
| `voltagent-data-ai:*` | data-ai |
| `voltagent-dev-exp:*` | developer-experience |
| `voltagent-domains:*` | domain-specialist |
| `voltagent-meta:*` | meta-orchestration |
| `voltagent-research:*` | research |
| `helioy-tools:*` | helioy (premium, higher priority) |
| `pr-review-toolkit:*` | review |

### MCP Tool Surface

Four tools. Minimal, composable.

**`index_agent_types`** - Rebuild the registry from disk. Called manually or on plugin install. Not called during normal operation.

**`search_agent_types(query, category, namespace, limit)`** - The primary discovery tool. FTS5 across name + description. Filter by category or namespace. Returns compact cards (qualified_name, short_name, description snippet, model, category).

**`get_agent_type(qualified_name)`** - Full detail for a single type. Includes the system prompt body, useful when the orchestrator needs to understand exact capabilities before spawning.

**`list_agent_categories()`** - Returns categories with counts. The "browse" entry point. Useful when the orchestrator doesn't know what's available.

### Warroom Lifecycle Tools

Separate from discovery, these replace warroom.sh:

**`spawn_warroom(name, agents, cwd)`** - Creates a tmux window with one pane per agent. Each pane runs `claude --agent {type}`. Returns the window name and pane map. Idempotent: kills existing window with same name first.

```python
@mcp.tool()
def spawn_warroom(
    name: str,
    agents: list[str],  # qualified or short names
    cwd: str = "",
    initial_prompt: str = "",
) -> dict:
    """Spawn a warroom: a tmux window with one Claude Code pane per agent type."""
```

**`kill_warroom(name)`** - Tears down a named warroom window.

**`warroom_status(name)`** - Returns pane liveness, agent registration status, and bus connectivity for a warroom.

### Resolution Strategy for Agent Names

When `spawn_warroom` receives agent names, it needs to resolve short names to qualified names. The resolution order:

1. If the name contains `:`, treat as qualified. Look up directly.
2. Search `agent_types` for exact `short_name` match.
3. If multiple matches, prefer by priority (helioy-tools > voltagent > others).
4. If zero matches, return an error with suggestions from FTS5.

This gives orchestrators the ergonomic shorthand of "backend-engineer" while maintaining the escape hatch of "voltagent-lang:golang-pro" for disambiguation.

## Key Architectural Boundaries

### What lives in the bus server vs. elsewhere

The bus server owns **runtime state**: which agents are alive, their mailboxes, their tmux targets. The registry is a natural extension: "what agent types could I spawn?" is adjacent to "what agents are running?"

The bus server does NOT own agent definition content. It indexes metadata from files owned by plugins. This is the same relationship fmm has with source code: fmm indexes but never modifies.

### What lives in MCP tools vs. shell scripts

MCP tools should own the full lifecycle: discover, spawn, monitor, kill. The shell script becomes a thin convenience wrapper (or disappears entirely). The failure mode that prompted this work ("agents struggle to execute shell scripts") is eliminated by moving the logic into Python where error handling is explicit and errors are returned as structured data.

### Spawn mechanics: subprocess vs. tmux send-keys

The current warroom.sh uses `tmux send-keys` to type the claude command into a pane. This is fragile (depends on shell state, prompt readiness, etc.) but is the only viable approach given that Claude Code is an interactive TUI. The MCP spawn tool should replicate this exact mechanism, with added guards:

1. Create the pane via `tmux split-window` or `new-window`
2. Set the pane title (identity) BEFORE sending keys
3. Lock `allow-rename` and `allow-set-title`
4. Send the claude command via `send-keys`
5. Return immediately. Do NOT wait for Claude to start. The bus registration (via SessionStart hook) confirms the agent is alive.

### The "available on this machine" vs. "exists in the ecosystem" boundary

Today, the only agents that matter are those with definition files on disk. The registry indexes what's installed. If the ecosystem grows to include remote agent registries or marketplace-style discovery, the `agent_types` table gains a `source` column (local, remote) and the index step learns to fetch from remote catalogs. But that's a future concern. The abstraction boundary (query the registry, not the filesystem) supports this evolution without redesign.

## What I'd Build First

**Phase 1: Registry + Search (standalone value)**
- Add `agent_types` table to bus.db
- Implement `index_agent_types` (scan known directories, parse frontmatter)
- Implement `search_agent_types` and `list_agent_categories`
- Run indexing as part of plugin install or on-demand

**Phase 2: Warroom Spawn (replaces shell script)**
- Implement `spawn_warroom`, `kill_warroom`, `warroom_status`
- Resolution uses the registry from Phase 1
- Identity/title convention preserved exactly as warroom.sh does it

**Phase 3: Enrichment (optional, high leverage)**
- Add `tags` extraction from agent definition bodies (keyword extraction from system prompts)
- Add `recommended` flag for curated subsets
- Add FTS5 index on description + tags for natural language queries like "who can help with database optimization?"

## Open Questions

1. **Should the registry live in bus.db or its own database?** Argument for bus.db: single source of truth, agents table and agent_types table are closely related. Argument against: bus.db is runtime state, registry is build-time state. Different lifecycles. I lean toward bus.db for simplicity, with a clear `indexed_at` timestamp to distinguish build-time data from runtime data.

2. **Who triggers re-indexing?** Plugin install hooks are the natural trigger. But what about when someone manually adds an agent .md file? A watcher is overkill. A simple "index if stale" check (compare directory mtime to indexed_at) on first search per session is cheap enough.

3. **Should spawn_warroom validate agent types against the registry?** Yes. Spawning a nonexistent type wastes a tmux pane and produces a confusing Claude error. Fail fast with "unknown agent type 'foo', did you mean 'frontend-engineer'?"

4. **How does this interact with the `--agent` flag's own resolution?** Claude Code resolves `--agent backend-engineer` by searching plugin agent directories. The bus registry needs to agree with Claude Code's resolution. Indexing the same directories Claude Code searches ensures consistency. But if Claude Code changes its search order, the registry could diverge. Worth documenting this coupling.
