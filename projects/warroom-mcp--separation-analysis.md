---
title: Warroom MCP - Separation Analysis
author: engineering-software-architect
date: 2026-03-17
topic: warroom-mcp-architecture
tags: [architecture, helioy-bus, mcp, warroom, separation-of-concerns]
---

# Should Warroom Be a Separate MCP Server?

## The Coupling Inventory

Before answering, let's map the actual dependencies between the two concern groups.

### Messaging/Registry (original bus)
Tools: `register_agent`, `unregister_agent`, `list_agents`, `heartbeat`, `send_message`, `get_messages`, `whoami`
Internals: `_init_db`, `_self_agent_id`, `_tmux_pane_alive`, `_tmux_nudge`, `_nudge_allowed`, `_record_nudge`, `_inbox_has_unread`
Tables: `agents`, `nudge_log`

### Warroom Lifecycle (new)
Tools: `warroom_discover`, `warroom_spawn`, `warroom_kill`, `warroom_status`, `warroom_presets`, `warroom_save_preset`
Internals: `_parse_frontmatter`, `_scan_agent_types`, `_resolve_agent_type`, `_tmux_check`, `_spawn_pane`
Tables: `warrooms`, `warroom_members`

### Shared Dependencies
| Resource | Used By Messaging | Used By Warroom |
|----------|:-:|:-:|
| `db()` / bus.db | Yes | Yes |
| `agents` table | Yes (read/write) | Yes (read, for cross-reference in `warroom_status`) |
| `_tmux_pane_alive` | Yes (liveness pruning in `list_agents`, nudge gating) | Yes (liveness check in `warroom_status`) |
| `_tmux_check` | No | Yes |
| `_now` | Yes | Yes |
| `_dbg` | Yes | Yes |

The cross-reference is real but narrow: `warroom_status` reads from `agents` to determine which spawned panes have registered. That's a single SELECT query.

## Decision: Keep Them Together

**Do not separate.** The cost of separation exceeds its benefit at this scale.

### Arguments for keeping together

**1. Shared database is the primary integration point.** Both concerns write to the same SQLite file. Splitting into two servers means either: (a) two processes sharing one SQLite file with WAL mode contention, or (b) duplicating the `agents` table across two databases and keeping them in sync. Both options add complexity that solves no user problem.

**2. MCP server count is a deployment cost.** Each MCP server is a separate stdio subprocess with its own lifecycle. The plugin's `mcp_servers` map in `plugin.toml` must declare each one. The Claude Code host process manages each connection independently. More servers means more reconnection surface, more TOML configuration, and more debugging surface when things go wrong.

**3. Tool namespace "pollution" is a non-problem.** Claude Code agents see all MCP tools regardless. The `warroom_` prefix already creates a clean namespace. An agent that only needs messaging will never accidentally call `warroom_spawn` because the tool descriptions make intent clear. LLMs are good at tool selection from large sets; the MCP protocol does not benefit from smaller tool surfaces the way REST APIs benefit from smaller endpoints.

**4. 1200 LOC is moderate, not alarming.** The file is well-organized with clear internal boundaries (messaging helpers, warroom helpers, DB layer). Python files become problematic around 3000-5000 LOC. At 1200 LOC with ~20 functions, the file is readable. Adding `warroom_add` and `warroom_remove` will push it to ~1400 LOC. Still manageable.

### When separation would be justified

If any of these conditions emerge, revisit this decision:
- The server exceeds 2500 LOC and the two concern groups develop independent release cadences
- A second consumer needs warroom lifecycle without messaging (e.g., a web dashboard)
- SQLite contention becomes measurable under concurrent warroom spawns
- The team needs to deploy messaging and warroom independently (different stability tiers)

None of these conditions exist today.

### The middle path: internal module extraction

If the single-file size becomes uncomfortable before full separation is justified, extract internal modules without splitting the MCP server:

```
server/
  bus_server.py        # MCP tool definitions only (~400 LOC)
  _messaging.py        # messaging internals
  _warroom.py          # warroom internals
  _db.py               # shared database layer
  _tmux.py             # shared tmux utilities
```

Same MCP server, same process, same database connection. Just file-level organization. This is a refactor, not an architecture change, and can happen at any time without breaking the MCP interface.

---

# warroom_add and warroom_remove Design

## warroom_add

Adds individual agents to a running warroom without tearing it down.

### Mechanics

1. Validate the warroom exists and is active.
2. Resolve the agent type (same `_resolve_agent_type` path).
3. Check for duplicates: if the warroom already has an agent of this type, return an error (or allow a `force` flag that kills the existing pane first).
4. Split a new pane in the warroom's tmux window via `_spawn_pane(is_first=False)`.
5. Insert a row into `warroom_members`.
6. Reflow the layout.

### Schema consideration

The current `warroom_members` primary key is `(warroom_id, agent_type)`. This prevents having two agents of the same type in one warroom. That's a reasonable constraint for now, but worth noting. If you want two `code-reviewer` agents in a warroom, the PK would need to change to `(warroom_id, agent_type, tmux_target)` or introduce a surrogate key.

For now, keep the existing PK and document that each agent type can appear at most once per warroom.

### Tool signature

```python
@mcp.tool()
def warroom_add(
    name: str,
    agent: str,
    cwd: str = "",
) -> dict:
    """Add an agent to an existing warroom.

    Splits a new pane in the warroom's tmux window and launches Claude Code
    with the specified agent type. The warroom must already exist.

    Args:
        name: Warroom identifier.
        agent: Agent type name (qualified or short).
        cwd: Working directory for the new pane. Defaults to the warroom's
             original cwd.

    Returns:
        {warroom_id, added: {agent_type, tmux_target, pane_id}, member_count}
    """
```

### Implementation sketch

```python
def warroom_add(name: str, agent: str, cwd: str = "") -> dict:
    with db() as conn:
        wr = conn.execute(
            "SELECT * FROM warrooms WHERE warroom_id = ? AND status = 'active'",
            (name,),
        ).fetchone()
        if not wr:
            return {"error": f"No active warroom '{name}'."}

        # Check for duplicate
        existing = conn.execute(
            "SELECT 1 FROM warroom_members WHERE warroom_id = ? AND agent_type = ?",
            (name, agent),  # needs resolved qualified_name here
        ).fetchone()

    agent_def = _resolve_agent_type(agent)
    if not agent_def:
        all_types = _scan_agent_types()
        q = agent.lower()
        suggestions = [a["qualified_name"] for a in all_types if q in a["name"].lower()][:5]
        return {"error": "Unknown agent type", "suggestions": suggestions}

    qn = agent_def["qualified_name"]

    with db() as conn:
        existing = conn.execute(
            "SELECT 1 FROM warroom_members WHERE warroom_id = ? AND agent_type = ?",
            (name, qn),
        ).fetchone()
        if existing:
            return {"error": f"Agent type '{qn}' already in warroom '{name}'. Kill it first with warroom_remove."}

    use_cwd = cwd or wr["cwd"]
    try:
        pane_info = _spawn_pane(
            session=wr["tmux_session"],
            window=wr["tmux_window"],
            cwd=use_cwd,
            agent_type=agent_def["name"],
            qualified_name=qn,
            is_first=False,
            layout="tiled",  # reflow with default layout
        )
    except RuntimeError as e:
        return {"error": f"Spawn failed: {e}"}

    now = _now()
    with db() as conn:
        conn.execute(
            """INSERT INTO warroom_members
               (warroom_id, agent_type, tmux_target, pane_id, agent_id, spawned_at)
               VALUES (?, ?, ?, ?, NULL, ?)""",
            (name, qn, pane_info["tmux_target"], pane_info["pane_id"], now),
        )
        count = conn.execute(
            "SELECT COUNT(*) FROM warroom_members WHERE warroom_id = ?", (name,)
        ).fetchone()[0]

    return {
        "warroom_id": name,
        "added": pane_info,
        "member_count": count,
    }
```

## warroom_remove

Removes a single agent from a running warroom by killing its pane.

### Mechanics

1. Look up the member in `warroom_members` by warroom name + agent type.
2. Kill the tmux pane (not the window).
3. Delete the `warroom_members` row.
4. If the warroom now has zero members, mark the warroom as 'killed' and remove the (now empty) tmux window.
5. Reflow the remaining panes.

### Edge case: removing the last pane

Killing the last pane in a tmux window automatically destroys the window. The tool should handle this gracefully by marking the warroom as killed in the database.

### Tool signature

```python
@mcp.tool()
def warroom_remove(
    name: str,
    agent: str,
) -> dict:
    """Remove an agent from a warroom by killing its tmux pane.

    If this is the last agent in the warroom, the warroom itself is
    torn down.

    Args:
        name: Warroom identifier.
        agent: Agent type to remove (qualified or short name).

    Returns:
        {warroom_id, removed: str, remaining_members: int, warroom_killed: bool}
    """
```

### Implementation sketch

```python
def warroom_remove(name: str, agent: str) -> dict:
    agent_def = _resolve_agent_type(agent)
    qn = agent_def["qualified_name"] if agent_def else agent

    with db() as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        member = conn.execute(
            "SELECT * FROM warroom_members WHERE warroom_id = ? AND agent_type = ?",
            (name, qn),
        ).fetchone()
        if not member:
            return {"error": f"No agent '{qn}' in warroom '{name}'."}

        pane_id = member["pane_id"]

        # Kill the tmux pane
        try:
            subprocess.run(
                ["tmux", "kill-pane", "-t", pane_id],
                capture_output=True, timeout=5,
            )
        except (subprocess.SubprocessError, FileNotFoundError):
            pass  # Pane may already be dead

        # Remove the member record
        conn.execute(
            "DELETE FROM warroom_members WHERE warroom_id = ? AND agent_type = ?",
            (name, qn),
        )

        # Check remaining members
        remaining = conn.execute(
            "SELECT COUNT(*) FROM warroom_members WHERE warroom_id = ?", (name,)
        ).fetchone()[0]

        warroom_killed = False
        if remaining == 0:
            conn.execute(
                "UPDATE warrooms SET status = 'killed' WHERE warroom_id = ?",
                (name,),
            )
            warroom_killed = True
        else:
            # Reflow remaining panes
            wr = conn.execute(
                "SELECT tmux_session, tmux_window FROM warrooms WHERE warroom_id = ?",
                (name,),
            ).fetchone()
            if wr:
                try:
                    subprocess.run(
                        ["tmux", "select-layout", "-t",
                         f"{wr['tmux_session']}:{wr['tmux_window']}", "tiled"],
                        capture_output=True, timeout=5,
                    )
                except (subprocess.SubprocessError, FileNotFoundError):
                    pass

    return {
        "warroom_id": name,
        "removed": qn,
        "remaining_members": remaining,
        "warroom_killed": warroom_killed,
    }
```

## Interaction with warroom_kill

`warroom_kill` remains the bulk operation (tear down entire warroom). `warroom_remove` is the surgical operation (remove one member). They share no code path beyond the database, which is fine. `warroom_kill` deletes the window; `warroom_remove` deletes a pane.

## Summary of Recommendations

| Question | Answer |
|----------|--------|
| Separate MCP server? | No. Keep together. Cost of separation exceeds benefit. |
| When to revisit? | At 2500+ LOC, or if independent deployment/consumers emerge. |
| Middle path? | Module extraction into `_messaging.py`, `_warroom.py`, `_db.py`, `_tmux.py`. |
| warroom_add? | Split new pane in existing window, insert member, reflow. |
| warroom_remove? | Kill pane, delete member, auto-kill warroom if last member removed. |
| PK constraint? | Keep `(warroom_id, agent_type)` for now. One instance per type per warroom. |
