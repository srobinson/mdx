---
title: Warroom MCP Tools Specification
category: projects
created: 2026-03-17
author: orchestrator
status: spec
tags: [helioy-bus, warroom, mcp, agent-discovery]
sources:
  - warroom-mcp--software-architect-brainstorm.md
  - warroom-mcp--backend-architect-brainstorm.md
  - warroom-mcp--ux-architect-brainstorm.md
---

# Warroom MCP Tools: Specification

Synthesized from three-architect brainstorm session (2026-03-17).

## Problem

Agents struggle to execute `warroom.sh` (bash): shell quoting, tmux context requirements, opaque `set -euo pipefail` failures. 100+ agent types across namespaces with no programmatic discovery.

## Design Decisions

1. **All warroom tools live in `bus_server.py`.** The bus already owns agent runtime state, tmux integration, and messaging. Warroom lifecycle is a natural extension.
2. **Agent type discovery uses filesystem scan with in-memory TTL cache.** No SQLite table for agent types in v1. Scan `~/.claude/plugins/cache/*/*/agents/*.md`, parse frontmatter, cache for 60 seconds.
3. **No pyyaml dependency.** Use regex-based frontmatter parser for scalar fields (name, description, model).
4. **Registration stays in the SessionStart hook.** `warroom_spawn` records spawn intent. The hook backfills `agent_id` on boot. `warroom_status` cross-references via `tmux_target`.
5. **Warroom state tracked in SQLite.** New `warrooms` and `warroom_members` tables in `registry.db`.
6. **Short name resolution with namespace priority.** `backend-engineer` resolves to `helioy-tools:backend-engineer` over `voltagent-core-dev:backend-developer`. Priority: helioy-tools > pr-review-toolkit > voltagent-*.

## Schema

```sql
CREATE TABLE IF NOT EXISTS warrooms (
    warroom_id   TEXT PRIMARY KEY,
    tmux_session TEXT NOT NULL,
    tmux_window  TEXT NOT NULL,
    cwd          TEXT NOT NULL,
    created_at   TEXT NOT NULL,
    status       TEXT NOT NULL DEFAULT 'active'
);

CREATE TABLE IF NOT EXISTS warroom_members (
    warroom_id   TEXT NOT NULL REFERENCES warrooms(warroom_id) ON DELETE CASCADE,
    agent_type   TEXT NOT NULL,
    tmux_target  TEXT NOT NULL,
    pane_id      TEXT NOT NULL,
    agent_id     TEXT,
    spawned_at   TEXT NOT NULL,
    PRIMARY KEY (warroom_id, agent_type)
);
```

## MCP Tools (6 total)

### 1. `warroom_discover`

Search available agent types that can be spawned.

```python
@mcp.tool()
def warroom_discover(
    query: str = "",
    namespace: str = "",
    limit: int = 20,
) -> dict:
```

**Parameters:**

- `query`: substring match against name and description. Empty = all.
- `namespace`: filter to a plugin namespace (e.g. `helioy-tools`). Empty = all.
- `limit`: max results (default 20).

**Returns:**

```json
{
  "agents": [
    {
      "qualified_name": "helioy-tools:backend-engineer",
      "name": "backend-engineer",
      "namespace": "helioy-tools",
      "summary": "Use this agent when building server-side APIs...",
      "model": "opus"
    }
  ],
  "total": 33,
  "namespaces": ["helioy-tools", "pr-review-toolkit", "voltagent-lang", "..."]
}
```

**Errors:** None fatal. Empty results if no matches.

### 2. `warroom_spawn`

Create a warroom: tmux window with one Claude Code pane per agent type.

```python
@mcp.tool()
def warroom_spawn(
    name: str,
    agents: list[str],
    cwd: str = "",
    layout: str = "tiled",
) -> dict:
```

**Parameters:**

- `name`: warroom identifier, becomes tmux window name. Alphanumeric + hyphens, 1-30 chars.
- `agents`: list of agent type names (qualified or short). Max 8.
- `cwd`: working directory. Defaults to caller's cwd.
- `layout`: tmux layout (tiled, even-horizontal, even-vertical, main-horizontal, main-vertical).

**Behavior:**

- Idempotent: kills existing warroom with same name first.
- Validates all agent types against the registry before spawning any panes.
- Creates panes sequentially: create pane, set title, lock rename, send-keys, select-layout.
- Records spawn intent in `warrooms` + `warroom_members`.
- Returns immediately. Does NOT wait for agents to register.

**Returns:**

```json
{
  "warroom_id": "design",
  "tmux_window": "design",
  "members": [
    {"agent_type": "backend-engineer", "qualified_name": "helioy-tools:backend-engineer", "tmux_target": "3:4.0", "pane_id": "%12"},
    {"agent_type": "ui-designer", "qualified_name": "helioy-tools:ui-designer", "tmux_target": "3:4.1", "pane_id": "%13"}
  ],
  "spawned_at": "2026-03-17T10:00:00+00:00"
}
```

**Errors:**

- Unknown agent type: return suggestions via fuzzy match.
- Not inside tmux: clear error.
- Partial failure: return spawned + failed lists.

### 3. `warroom_kill`

Tear down a warroom or all warrooms.

```python
@mcp.tool()
def warroom_kill(
    name: str = "",
    kill_all: bool = False,
) -> dict:
```

**Returns:** `{"killed": ["design"], "errors": []}`

### 4. `warroom_status`

Get status of warrooms with live cross-referencing.

```python
@mcp.tool()
def warroom_status(
    name: str = "",
) -> list[dict]:
```

Cross-references `warroom_members.tmux_target` with `agents.tmux_target` to report:

- `registered`: agent has called `register_agent` via SessionStart hook
- `pane_alive`: tmux pane still exists
- `agent_id`: populated once registered, null while spawning

### 5. `warroom_presets`

List available preset team compositions.

```python
@mcp.tool()
def warroom_presets() -> dict:
```

Reads from `~/.helioy/bus/presets/*.json`. Each preset: `{name, description, agents[], tags[]}`.

### 6. `warroom_save_preset`

Save a warroom composition as a reusable preset.

```python
@mcp.tool()
def warroom_save_preset(
    name: str,
    agents: list[str],
    description: str = "",
    tags: list[str] = [],
) -> dict:
```

## Internal Functions

### `_scan_agent_types() -> list[dict]`

Walk `~/.claude/plugins/cache/*/*/agents/*.md`. Parse YAML frontmatter via regex. Deduplicate across plugin versions (keep latest mtime). Cache in-memory with 60s TTL.

### `_resolve_agent_type(name: str) -> dict | None`

1. If contains `:`, exact qualified lookup.
2. Exact `short_name` match across all namespaces.
3. Priority ordering: helioy-tools > pr-review-toolkit > voltagent-*.
4. If zero matches, return None (caller provides fuzzy suggestions).

### `_spawn_pane(window, cwd, agent_type, repo, is_first) -> dict`

Sequential tmux subprocess calls:

1. `new-window` or `split-window` (capture pane_id)
2. `display-message` (resolve tmux_target)
3. `select-pane -T` (set identity title BEFORE claude starts)
4. `set-option allow-rename off` (lock titles, first pane only)
5. `send-keys` (launch `claude --verbose --dangerously-skip-permissions --agent {type}`)
6. `select-layout` (reflow after each split)

### `_tmux_check(*args) -> str`

Wrapper for tmux subprocess calls with timeout and error handling.

### `_parse_frontmatter(path) -> dict`

Regex-based YAML frontmatter extraction for scalar fields. No pyyaml.

## Ordering Contract

Pane title MUST be set before `send-keys`. This is the invariant that makes identity resolution work. Python's synchronous `subprocess.run` guarantees this naturally.

## Phase 2 (Deferred)

- FTS5 index on agent type descriptions for natural language search.
- `warroom_plan(task, max_agents, constraints)`: task-to-team recommendation tool.
- `warroom_id` environment variable set in pane for explicit join (vs tmux_target matching).
- Multi-cwd warrooms (different working directory per agent).
- `from_agent` validation in `send_message` to prevent reply-routing bugs.

---

Transcript for [What If Intelligence Didn't Evolve? It "Was There" From the Start! - Blaise Agüera y Arcas](https://www.youtube.com/watch?v=M2iX6HQOoLg) by [Merlin AI](https://merlin.foyer.work/)
