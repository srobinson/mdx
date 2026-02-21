---
title: Token Usage Tracking for helioy-bus
category: projects
created: 2026-03-17
author: orchestrator
status: spec
tags: [helioy-bus, token-tracking, warroom, context-window]
---

# Token Usage Tracking for helioy-bus

## Problem

An orchestrator managing a warroom has no visibility into how much context each agent has consumed. An agent at 85% context is about to hit compression or lose coherence. The orchestrator needs this signal to:
- Route new work away from hot agents
- Preemptively wind down agents before they degrade
- Report burn rate in `warroom_status`

## How Claude Code Exposes Token Data

Claude Code writes JSONL to `~/.claude/projects/<encoded-project>/<uuid>.jsonl`. Each assistant turn emits:

```json
{
  "type": "assistant",
  "message": {
    "usage": {
      "input_tokens": 28000,
      "cache_creation_input_tokens": 5000,
      "cache_read_input_tokens": 12000,
      "output_tokens": 450
    }
  }
}
```

Total context consumed per turn: `input_tokens + cache_creation_input_tokens + cache_read_input_tokens`

Context is a high-water mark (it only grows within a session). Output tokens accumulate across turns.

There is no live API or status bar export. The JSONL file is the only programmatic source, and it updates after each assistant message completes (not during streaming).

## Design Options

### Option A: JSONL Watcher (nancy's approach)

A `tail -F` process per agent watches the JSONL file and updates a tracking file.

**Problem for the bus:** The JSONL path contains an encoded project path and a session UUID. The bus doesn't know either value because agents are spawned via `tmux send-keys`, not by capturing Claude's stdout. Discovering the JSONL file requires scanning `~/.claude/projects/` by mtime, which is fragile and race-prone.

**Verdict:** Wrong fit. Nancy controls Claude's lifecycle (stdin/stdout pipes). The bus does not.

### Option B: Hook-based reporting (recommended)

A Claude Code hook fires on each assistant turn and writes token usage to the bus registry. The hook runs inside the agent's process, so it has access to the JSONL via the Claude Code environment.

**Two sub-options:**

**B1: PostToolUse hook on every MCP call.** Too noisy. Fires on every tool call, not just assistant turns. Would need filtering.

**B2: Custom hook that tails the JSONL.** A SessionStart hook spawns a lightweight background watcher that:
1. Finds the active JSONL file for this session
2. Tails it with `tail -F`
3. On each assistant message, writes token usage to the bus SQLite (same pattern as `bus-register.sh`)

The watcher is a shell script that runs alongside Claude. It writes directly to `registry.db` (no MCP round-trip). A SessionEnd hook kills the watcher.

### Option C: Agent self-reports via MCP tool

Add a `report_token_usage()` MCP tool. Agents call it periodically or a hook triggers it.

**Problem:** The agent itself doesn't know its own token counts. Token data is in the JSONL output stream, not available to MCP tools or hooks as an environment variable. The agent would need to find and parse its own JSONL file.

**Verdict:** Circular. The agent can't read its own usage without the same file-discovery problem.

### Option D: Tmux status bar scraping

Claude Code shows token count in the status bar. Scrape it via `tmux capture-pane`.

**Problem:** The status bar format is not stable. Parsing it requires regex against a UI that changes across versions. Also requires knowing which line of the terminal contains the status bar.

**Verdict:** Fragile. Last resort.

## Recommended: Option B2 (Background JSONL Watcher via Hook)

### Architecture

```
SessionStart hook
  ├── bus-register.sh (existing: registers agent on bus)
  └── token-watcher.sh (new: spawns background tail -F)
        ↓
    tail -F ~/.claude/projects/{project}/{session}.jsonl
        ↓
    Filter: .type == "assistant" → .message.usage
        ↓
    Write to registry.db: agents.token_usage (JSON column)
        ↓
SessionEnd hook
  └── token-watcher-stop.sh (kills the background process)
```

### Schema Change

Add a `token_usage` column to the `agents` table:

```sql
ALTER TABLE agents ADD COLUMN token_usage TEXT NOT NULL DEFAULT '{}';
```

The column stores a JSON object:

```json
{
  "total_input": 85000,
  "total_output": 12000,
  "limit": 200000,
  "percent": 42.5,
  "updated": "2026-03-17T10:05:00Z"
}
```

### JSONL File Discovery (RESOLVED)

The JSONL path is fully deterministic from two values the bus already has:

```
~/.claude/projects/-{cwd.replace("/", "-")}/{session_id}.jsonl
```

The encoding is trivial: replace `/` with `-`, prepend `-`. Both `cwd` and `session_id` are stored in the `agents` table at registration time. No scanning, no lsof, no guessing. O(1) discovery.

### Hook: `token-watcher.sh`

```bash
#!/usr/bin/env bash
# Spawned by SessionStart. Runs in background.
# Finds the active JSONL file, tails it, writes token usage to registry.db.

AGENT_ID="$HELIOY_AGENT_ID"
DB_PATH="$HOME/.helioy/bus/registry.db"
CONTEXT_LIMIT="${TOKEN_CONTEXT_LIMIT:-200000}"

# Deterministic JSONL path from cwd + session_id
PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$PWD}"
ENCODED_DIR="-${PROJECT_DIR//\//-}"
SESSION_ID="${HELIOY_SESSION_ID}"
JSONL_FILE="$HOME/.claude/projects/${ENCODED_DIR}/${SESSION_ID}.jsonl"

# Background watcher
tail -n 0 -F "$JSONL_FILE" 2>/dev/null | while IFS= read -r line; do
    usage=$(echo "$line" | jq -c 'select(.type == "assistant") | .message.usage // empty' 2>/dev/null)
    [[ -z "$usage" ]] && continue

    input=$(echo "$usage" | jq -r '.input_tokens // 0')
    cache_creation=$(echo "$usage" | jq -r '.cache_creation_input_tokens // 0')
    cache_read=$(echo "$usage" | jq -r '.cache_read_input_tokens // 0')
    output=$(echo "$usage" | jq -r '.output_tokens // 0')

    turn_input=$((input + cache_creation + cache_read))

    # Update registry.db directly
    sqlite3 "$DB_PATH" "
        UPDATE agents SET token_usage = json_object(
            'total_input', MAX(json_extract(COALESCE(NULLIF(token_usage,'{}'),'{}'), '$.total_input'), $turn_input),
            'total_output', COALESCE(json_extract(token_usage, '$.total_output'), 0) + $output,
            'limit', $CONTEXT_LIMIT,
            'percent', ROUND(CAST(MAX(json_extract(COALESCE(NULLIF(token_usage,'{}'),'{}'), '$.total_input'), $turn_input) AS REAL) / $CONTEXT_LIMIT * 100, 1),
            'updated', datetime('now')
        ), last_seen = datetime('now')
        WHERE agent_id = '$AGENT_ID';
    "
done &

echo $! > "$HOME/.helioy/bus/pids/${AGENT_ID}.token_watcher"
```

### MCP Tool: `agent_token_usage`

Exposes token data in the bus API:

```python
@mcp.tool()
def agent_token_usage(agent_id: str = "") -> dict:
    """Get token usage for an agent or all agents.

    Args:
        agent_id: Specific agent. Empty = all registered agents.

    Returns:
        List of {agent_id, agent_type, token_usage: {total_input, total_output, limit, percent, updated}}
    """
```

### Integration with `warroom_status`

`warroom_status` already cross-references `warroom_members` with `agents`. Adding token_usage is a single column addition to the SELECT:

```python
# In warroom_status, the member dict gains:
{
    "agent_type": "backend-engineer",
    "agent_id": "helioy-bus:backend-engineer:3:4.0",
    "registered": true,
    "pane_alive": true,
    "token_usage": {"total_input": 85000, "percent": 42.5, ...}
}
```

### Integration with `list_agents`

`list_agents` already returns full agent cards. `token_usage` appears as a parsed JSON field (same pattern as `profile`).

## Open Questions

1. ~~**JSONL file discovery.**~~ RESOLVED. Path is `-{cwd.replace("/", "-")}` + `/{session_id}.jsonl`. Both values in the agents table.

2. **Watcher cleanup.** If Claude crashes without firing SessionEnd, the watcher process becomes orphaned. Mitigation: the watcher checks if its parent PID is still alive every 30 seconds and exits if not.

3. **Multiple sessions.** If an agent is restarted (new Claude session in the same pane), the watcher from the old session may still be running. SessionStart should kill any existing watcher for this agent_id before spawning a new one.

4. **Performance.** `tail -F` + `jq` per line is cheap. SQLite write per assistant turn is negligible. No concerns at the scale of 1-20 warroom agents.

## Context Rot Thresholds

Context rot degrades agent quality well before the advertised context window is full. Research shows degradation starts around 150k tokens regardless of model (Sonnet 200k, Opus 1M). The thresholds are absolute token counts, not percentages of the window.

| Threshold | Total Input | Action |
|-----------|-------------|--------|
| **warning** | 150k | Bus message to orchestrator: agent approaching context limit. Orchestrator should avoid sending new complex tasks. |
| **final-warning** | 160k | Bus message to orchestrator: agent at critical context. Orchestrator should wrap up current work. |
| **evict** | 170k | Automated sequence: (1) trigger `session-logger` skill to persist work log, (2) kill the agent pane, (3) respawn a fresh agent of the same type in the same warroom slot. The orchestrator receives a bus message with the old agent's work summary so it can brief the replacement. |

### Eviction Flow

```
Watcher detects total_input >= 170k
  ↓
1. Send bus message to agent: "Run /session-logger now. You are being rotated."
  ↓
2. Wait for session-logger completion (poll JSONL for result event, timeout 30s)
  ↓
3. Kill the tmux pane
  ↓
4. warroom_remove(name, agent_type) -- cleans up DB
  ↓
5. warroom_add(name, agent_type) -- spawns fresh replacement
  ↓
6. Send bus message to orchestrator:
   "Agent {agent_id} evicted at {total_input} tokens.
    Replacement spawned as {new_agent_id}.
    Work log: {session_log_path}"
```

The orchestrator can then brief the new agent with relevant context from the old session log.

### Why Not Percentage-Based

A percentage of the context window is misleading. Opus advertises 1M tokens, but an agent at 150k is already degrading. Using absolute thresholds grounded in observed context rot is more reliable than `percent_of_limit`.

The `token_usage` JSON still stores `percent` for display purposes, but threshold logic uses absolute `total_input` values.

## Implementation Phases

~~**Phase 1: JSONL discovery research.**~~ RESOLVED.

**Phase 1: Watcher hook.** `token-watcher.sh` (SessionStart) and `token-watcher-stop.sh` (SessionEnd). Direct SQLite writes. Deterministic JSONL path from `cwd` + `session_id`.

**Phase 2: MCP integration.** `agent_token_usage` tool. `token_usage` in `warroom_status` and `list_agents`.

**Phase 3: Threshold alerts + eviction.** Watcher sends bus messages at 150k/160k. At 170k, triggers session-logger then rotates the agent via warroom_remove + warroom_add.
