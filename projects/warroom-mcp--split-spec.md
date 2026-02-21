---
title: "Spec: Split helioy-bus into bus + warroom MCP servers"
author: engineering-software-architect
date: 2026-03-17
topic: bus-warroom-split-spec
tags: [architecture, helioy-bus, mcp, warroom, spec, refactor]
---

# Spec: Split helioy-bus into bus + warroom MCP Servers

## Rationale

My earlier recommendation to keep the servers together was based on deployment complexity and shared database concerns. The research at `~/.mdx/research/mcp-tool-count-impact.md` changes the calculus:

- Anthropic documents tool selection degradation beyond 30-50 tools
- Consensus: 5-8 tools per MCP server, split at 15
- helioy-bus currently has 15 tools in one server, sitting exactly at the split threshold
- Combined with other plugins (cm 8 tools, am 11 tools, fmm 7 tools, linear ~30 tools, mdx 7 tools, supabase ~20 tools), agents see 100+ tools
- Observed `whoami` misrouting to cm/am confirms the namespace collision is real

The split produces two focused servers: **helioy-bus** (7 tools, always loaded) and **helioy-warroom** (8 tools, deferred/lazy loaded for orchestrators only).

## 1. File Structure

### Current

```
server/
  bus_server.py       # 967 LOC — 15 MCP tools (monolith)
  _db.py              # 105 LOC — shared database layer
  _identity.py        #  29 LOC — agent identity resolution
  _tmux.py            # 215 LOC — tmux helpers (nudge, pane alive, spawn)
  _warroom.py         # 141 LOC — agent type scanning/resolution
  proxy.py            # 149 LOC — hot-reload stdio proxy
tests/
  test_bus_server.py  # 1452 LOC — 75 tests
```

### Target

```
server/
  bus_server.py        # messaging/registry MCP server (~450 LOC)
  warroom_server.py    # warroom lifecycle MCP server (~550 LOC)
  _db.py               # shared database layer (unchanged)
  _identity.py         # shared identity resolution (unchanged)
  _tmux.py             # shared tmux helpers (unchanged)
  _warroom.py          # warroom internals (unchanged)
  proxy.py             # proxy for bus_server.py (unchanged)
  warroom_proxy.py     # proxy for warroom_server.py (new, ~20 LOC)
tests/
  test_bus_server.py   # messaging/registry tests (~700 LOC)
  test_warroom_server.py # warroom lifecycle tests (~800 LOC)
  conftest.py          # shared fixtures (isolated_bus, fake_plugins)
```

### What moves where

**bus_server.py retains** (7 tools):
- `whoami`
- `register_agent`
- `unregister_agent`
- `list_agents`
- `heartbeat`
- `send_message`
- `get_messages`

**warroom_server.py receives** (8 tools):
- `warroom_discover`
- `warroom_spawn`
- `warroom_kill`
- `warroom_status`
- `warroom_add`
- `warroom_remove`
- `warroom_presets`
- `warroom_save_preset`

### Shared modules remain unchanged

`_db.py`, `_identity.py`, `_tmux.py`, `_warroom.py` are imported by both servers. No changes needed to these files. Both servers import from the `server` package using existing relative imports.

## 2. Plugin Configuration

### Current hooks.json

The existing hooks.json at `helioy-plugins/plugins/helioy-bus/hooks/hooks.json` declares one MCP server implicitly via the hook structure. The MCP server declaration likely lives in the plugin's `commands/` directory or is configured in the Claude Code plugin registration.

### Target: Two MCP server declarations

The helioy-bus plugin needs to declare two MCP servers. In the Claude Code plugin system, MCP servers are declared in the plugin configuration. The warroom server should be marked for deferred loading.

The plugin directory structure becomes:

```
helioy-plugins/plugins/helioy-bus/
  commands/
    helioy/                 # existing CLI commands
  hooks/
    hooks.json              # hook declarations (unchanged)
  skills/
    mail/                   # existing
    mail-workspace/         # existing
    warroom/                # existing warroom skill
  mcp_servers/
    helioy-bus.json         # bus server declaration
    helioy-warroom.json     # warroom server declaration
```

**helioy-bus.json** (always loaded):
```json
{
  "command": "python",
  "args": ["/Users/alphab/Dev/LLM/DEV/helioy/helioy-bus/server/proxy.py"],
  "description": "Inter-agent message bus for the helioy ecosystem"
}
```

**helioy-warroom.json** (deferred loading):
```json
{
  "command": "python",
  "args": ["/Users/alphab/Dev/LLM/DEV/helioy/helioy-bus/server/warroom_proxy.py"],
  "description": "Warroom lifecycle management: discover, spawn, kill, and manage agent teams",
  "defer_loading": true
}
```

**Note**: The exact mechanism for declaring MCP servers depends on how Claude Code plugins register them. If the plugin system uses a `plugin.toml` with an `[mcp_servers]` section, that's where both servers are declared. If MCP servers are registered via the `commands/` directory, each gets its own command entry. Verify the plugin system's MCP registration mechanism before implementing.

## 3. Shared Database Access

### Database: `~/.helioy/bus/registry.db`

Both servers read from and write to the same SQLite database via `_db.py`.

### WAL mode concurrency

The database already uses `PRAGMA journal_mode=WAL` (set in `_init_db`). WAL mode supports concurrent readers with a single writer. This is sufficient for our access pattern:

- **bus_server**: frequent reads (list_agents, get_messages), frequent writes (register, heartbeat, send_message)
- **warroom_server**: infrequent reads (warroom_status cross-references agents table), infrequent writes (spawn, kill, add, remove)

WAL mode handles this without contention. The warroom server's writes are low-frequency (spawning a warroom is a rare event). SQLite's write serialization (one writer at a time) will not cause observable latency.

### Table ownership

| Table | Primary Owner | Secondary Reader |
|-------|--------------|-----------------|
| `agents` | bus_server (register, unregister, heartbeat, list) | warroom_server (cross-reference in warroom_status) |
| `nudge_log` | bus_server (nudge throttling) | none |
| `warrooms` | warroom_server | none |
| `warroom_members` | warroom_server | none |
| `token_usage` | bus_server (token tracking) | warroom_server (warroom_status includes token data) |

### Schema initialization

Both servers call `_init_db()` when opening a database connection. `_init_db` uses `CREATE TABLE IF NOT EXISTS` and migration `ALTER TABLE` wrapped in `contextlib.suppress(OperationalError)`. This is idempotent and safe for concurrent initialization by both servers. Whichever server connects first creates all tables. The second server's `CREATE TABLE IF NOT EXISTS` statements are no-ops.

No schema changes required for the split.

## 4. Deferred Loading

Claude Code supports deferred tool loading. When a server is marked `defer_loading: true`, its tools appear in the `<available-deferred-tools>` system reminder by name only (no schema). The agent must call `ToolSearch` to fetch the full schema before invoking a deferred tool.

### Which tools get deferred

All 8 warroom tools. The warroom server is entirely deferred.

### Why this works

- Orchestrator agents (the primary warroom consumers) know they need warroom tools and will search for them explicitly
- Worker agents (backend-engineer, frontend-engineer, etc.) never need warroom tools and never pay the context cost
- The tool names (`warroom_spawn`, `warroom_kill`, etc.) are distinctive enough for ToolSearch to match reliably

### What stays eagerly loaded

All 7 bus tools. Every agent needs `register_agent` (called by SessionStart hook), `send_message`, and `get_messages`. These must be available immediately without a ToolSearch roundtrip.

## 5. Hook Ownership

All hooks belong to the **bus** plugin. None need to change.

| Hook | Script | Server Dependency | Notes |
|------|--------|-------------------|-------|
| SessionStart | `bus-register.sh` | bus_server (register_agent) | Calls register_agent MCP tool |
| PreToolUse | `check-mail.sh` | bus_server (get_messages) | Checks inbox for pending messages |
| PreToolUse | `token-capture.sh` | bus_server (token tracking) | Writes token usage to bus DB |
| UserPromptSubmit | `check-mail.sh` | bus_server (get_messages) | Same as above |
| Stop | echo message | none | Static message, no MCP call |
| SessionEnd | `bus-unregister.sh` | bus_server (unregister_agent) | Calls unregister_agent MCP tool |

No hooks depend on warroom_server. The warroom is orchestrator-initiated via MCP tool calls, not hook-triggered. If future features require warroom hooks (e.g., auto-eviction at token threshold), those hooks would still interact via bus_server tools (send_message to orchestrator) rather than calling warroom_server directly.

## 6. Import Paths

### Current imports in bus_server.py

```python
from server._db import db, BUS_DIR, INBOX_DIR, REGISTRY_DB, PLUGINS_CACHE, PRESETS_DIR, LOG_FILE
from server._identity import _self_agent_id
from server._tmux import (
    _tmux_pane_alive, _tmux_nudge, _nudge_allowed, _record_nudge,
    _inbox_has_unread, _tmux_check, _spawn_pane, NUDGE_THROTTLE_SECONDS,
)
from server._warroom import _scan_agent_types, _resolve_agent_type, _parse_frontmatter
```

### Target imports

**bus_server.py** (messaging only):
```python
from server._db import db, BUS_DIR, INBOX_DIR, REGISTRY_DB, LOG_FILE
from server._identity import _self_agent_id
from server._tmux import (
    _tmux_pane_alive, _tmux_nudge, _nudge_allowed, _record_nudge,
    _inbox_has_unread, NUDGE_THROTTLE_SECONDS,
)
```

Removes: `PLUGINS_CACHE`, `PRESETS_DIR`, `_tmux_check`, `_spawn_pane`, all `_warroom` imports.

**warroom_server.py** (warroom only):
```python
from server._db import db, BUS_DIR, PRESETS_DIR, PLUGINS_CACHE
from server._identity import _self_agent_id
from server._tmux import _tmux_pane_alive, _tmux_check, _spawn_pane
from server._warroom import _scan_agent_types, _resolve_agent_type
```

### Package initialization

`server/__init__.py` exists (assumed, for the `server.` package imports to work). No changes needed.

### Running as standalone scripts

Both servers must be runnable as `python server/bus_server.py` and `python server/warroom_server.py`. The `server` package imports require that the parent directory is on `sys.path`. The proxy scripts handle this by spawning from the correct working directory. The `warroom_proxy.py` must do the same.

## 7. Test Organization

### Split tests into two files + shared conftest

**tests/conftest.py** (new, ~80 LOC):
Extract shared fixtures currently in `test_bus_server.py`:
- `isolated_bus` fixture (creates temp dirs, patches DB paths)
- `fake_plugins` fixture (creates mock agent definition files)
- Any helper functions used by both test files

**tests/test_bus_server.py** (~700 LOC):
Retains tests for messaging/registry tools:
- `test_register_*` (6 tests)
- `test_list_agents_*` (7 tests)
- `test_heartbeat_*` (1 test)
- `test_unregister_*` (1 test)
- `test_send_message_*` (11 tests)
- `test_get_messages_*` (3 tests)
- `test_whoami_*` (1 test)
- `test_adhoc_session_fallback_identity` (1 test)
- `test_profile_migration_*` (1 test)
- `test_coexistence_of_both_modes` (1 test)
- `test_token_usage_*` (3 tests)

Total: ~35 tests

**tests/test_warroom_server.py** (new, ~800 LOC):
Receives all warroom tests:
- `test_parse_frontmatter_*` (4 tests)
- `test_scan_agent_types_*` (3 tests)
- `test_resolve_*` (4 tests)
- `test_warroom_schema_*` (1 test)
- `test_warroom_discover_*` (4 tests)
- `test_warroom_presets_*` (2 tests)
- `test_warroom_save_preset_*` (1 test)
- `test_warroom_spawn_*` (6 tests)
- `test_warroom_kill_*` (2 tests)
- `test_warroom_status_*` (2 tests)
- `test_warroom_add_*` (4 tests)
- `test_warroom_remove_*` (3 tests)
- `test_repo_mode_lifecycle` (1 test)
- `test_role_mode_lifecycle` (1 test)

Total: ~38 tests

**tests/test_resolve_identity.sh** (unchanged)

### Import changes in tests

Tests currently import from `server.bus_server`:
```python
from server.bus_server import warroom_spawn, warroom_kill, ...
```

After split, warroom tests import from `server.warroom_server`:
```python
from server.warroom_server import warroom_spawn, warroom_kill, ...
```

Bus tests continue importing from `server.bus_server`.

## 8. Proxy Configuration

### Existing proxy.py

`proxy.py` watches `server/` for `.py` changes and restarts `bus_server.py`. After the split, it should only restart when bus-relevant files change.

**Option A**: proxy.py watches specific files (`bus_server.py`, `_db.py`, `_identity.py`, `_tmux.py`) rather than the entire directory. This prevents a bus restart when `_warroom.py` changes.

**Option B**: proxy.py continues watching all `.py` files. A change to `_db.py` affects both servers, so restarting both is correct. Changes to `_warroom.py` cause an unnecessary bus restart, but the restart is fast (sub-second) and harmless.

**Recommendation**: Option B. The simplicity is worth the occasional unnecessary restart.

### warroom_proxy.py (new)

A minimal proxy for the warroom server. Can be a near-copy of proxy.py with `SERVER_SCRIPT` pointing to `warroom_server.py`.

```python
#!/usr/bin/env python3
"""helioy-warroom hot-reload stdio proxy.

Same architecture as proxy.py but for the warroom MCP server.
"""
from pathlib import Path
import sys

# Re-use the proxy implementation, just change the target script
WATCH_DIR = Path(__file__).parent
SERVER_SCRIPT = WATCH_DIR / "warroom_server.py"

# Import and run the same proxy class
from server.proxy import HotReloadProxy
import asyncio

if __name__ == "__main__":
    # Patch the server script path
    import server.proxy as p
    p.SERVER_SCRIPT = SERVER_SCRIPT
    asyncio.run(HotReloadProxy().run())
```

**Better approach**: Refactor `proxy.py` to accept the target script as a command-line argument:

```python
# proxy.py
if __name__ == "__main__":
    import sys
    target = sys.argv[1] if len(sys.argv) > 1 else "bus_server.py"
    SERVER_SCRIPT = WATCH_DIR / target
    asyncio.run(HotReloadProxy().run())
```

Then both MCP server declarations use the same proxy:
- Bus: `python server/proxy.py bus_server.py`
- Warroom: `python server/proxy.py warroom_server.py`

This eliminates `warroom_proxy.py` entirely.

## 9. Migration Path

Step-by-step refactor that preserves all 75 tests at every step.

### Step 1: Extract conftest.py

Move `isolated_bus` and `fake_plugins` fixtures from `test_bus_server.py` to `tests/conftest.py`. Pytest discovers conftest.py automatically.

**Verify**: `just test` passes. All 75 tests green.

### Step 2: Create warroom_server.py with MCP tool definitions

Create `server/warroom_server.py`:
- New `FastMCP` instance: `mcp = FastMCP("helioy-warroom")`
- Copy the 8 warroom tool functions from `bus_server.py`
- Add imports from shared modules
- Add `if __name__ == "__main__": mcp.run()`

Do NOT remove the tools from `bus_server.py` yet. Both files define the same tools temporarily.

**Verify**: `python -c "from server.warroom_server import mcp; print(mcp.name)"` succeeds.

### Step 3: Create test_warroom_server.py

Copy warroom-related tests from `test_bus_server.py` to `test_warroom_server.py`. Update imports to point to `server.warroom_server`.

**Verify**: `just test` passes. Test count increases (now ~113 tests, some duplicated temporarily).

### Step 4: Remove warroom tools from bus_server.py

Delete the 8 warroom tool functions from `bus_server.py`. Remove unused imports (`PLUGINS_CACHE`, `PRESETS_DIR`, `_tmux_check`, `_spawn_pane`, `_scan_agent_types`, `_resolve_agent_type`).

**Verify**: `just test` passes. Some tests in `test_bus_server.py` will fail (those that import warroom functions from bus_server). Delete those tests from `test_bus_server.py` (they now live in `test_warroom_server.py`).

**Verify**: `just test` passes. Test count returns to 75 (split across two files).

### Step 5: Update proxy.py to accept target argument

Modify proxy.py to accept a command-line argument for the target server script. Default to `bus_server.py` for backward compatibility.

**Verify**: `python server/proxy.py` starts bus server. `python server/proxy.py warroom_server.py` starts warroom server.

### Step 6: Update plugin MCP server declarations

Add the warroom server declaration to the helioy-bus plugin configuration. Mark it as deferred.

**Verify**: Claude Code sees both servers. Bus tools load eagerly. Warroom tools appear in `<available-deferred-tools>`.

### Step 7: Verify end-to-end

- Start a Claude Code session. Confirm bus tools work (register, send, get).
- Call `ToolSearch` for warroom tools. Confirm they load.
- Spawn a warroom. Confirm it works.
- Kill the warroom. Confirm cleanup.

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| SQLite WAL contention between two processes | Low | Low | WAL mode handles concurrent readers. Warroom writes are rare. |
| Import path breakage during migration | Medium | Low | Step-by-step migration with test verification at each step. |
| Deferred loading prevents hooks from reaching warroom tools | None | N/A | No hooks call warroom tools. Verified in section 5. |
| Proxy restart behavior changes | Low | Low | Option B (watch all .py files) preserves current behavior. |
| Plugin configuration format uncertainty | Medium | Medium | Verify Claude Code plugin MCP registration mechanism before step 6. |

## Success Criteria

1. Two separate MCP server processes, each with its own stdio connection
2. Bus server: 7 tools, always loaded, <4000 tokens of tool definitions
3. Warroom server: 8 tools, deferred loaded, zero context cost for non-orchestrator agents
4. All 75 existing tests pass, split across two test files
5. Shared database access works without contention
6. Hot-reload proxy works for both servers
7. No behavioral change for existing agents (bus tools work exactly as before)
