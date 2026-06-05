# Warroom MCP Tools: Backend Architect Brainstorm

## 1. Agent Type Discovery: Sourcing the Registry

### The landscape

Agent types exist in three distinct tiers:

1. **On-disk plugin agents** (`~/.claude/plugins/cache/{org}/{plugin}/{version}/agents/*.md`). These are concrete files with YAML frontmatter (name, description, model, color, mcpServers, hooks). Currently ~33 from `helioy-tools`, ~6 from `pr-review-toolkit`, plus skill-internal agents from `skill-creator`. This is the authoritative, scannable set.

2. **System-prompt-only agents** (`voltagent-*` namespaces). These are injected into the Agent tool description at runtime by Claude Code. There are 100+ of them across `voltagent-biz`, `voltagent-lang`, `voltagent-infra`, `voltagent-qa-sec`, `voltagent-meta`, `voltagent-research`, `voltagent-domains`, `voltagent-dev-exp`, `voltagent-data-ai`, `voltagent-core-dev`. They have no `.md` file on disk. They cannot be discovered by filesystem scan.

3. **The `--agent` flag** used in `warroom.sh` maps to on-disk `.md` files. When `claude --agent backend-engineer` runs, Claude Code resolves the agent definition from the plugin cache. The voltagent agents are only reachable via the `Agent` tool (subagent spawning from within a running session), not via `--agent` CLI flag.

### Recommended approach: hybrid filesystem scan + static catalog

**Primary source: scan on-disk `.md` files.** Walk `~/.claude/plugins/cache/*/*/agents/*.md` (deduplicate across versions by taking the latest). Parse YAML frontmatter to extract `name`, `description`, `model`, `color`. This gives us the set of agents that `--agent` can actually launch in a tmux pane.

**Secondary source: optional static catalog file.** For voltagent and other non-file agents, maintain `~/.helioy/bus/agent_catalog.json` that maps namespace + name to description. This file can be generated once by scraping the system prompt or maintained manually. The MCP tools would merge both sources at query time.

**Why not hardcode?** Agent definitions change as plugins update. A filesystem scan stays current automatically. The static catalog is a fallback for agents that only exist at the system-prompt level and cannot be spawned via `--agent` anyway, so it is lower priority.

### Implementation: `_scan_agent_types()`

```python
import yaml
from pathlib import Path
from functools import lru_cache
import time

PLUGINS_CACHE = Path.home() / ".claude" / "plugins" / "cache"
CATALOG_FILE = BUS_DIR / "agent_catalog.json"

def _scan_agent_types(force: bool = False) -> list[dict]:
    """Scan on-disk agent definitions from Claude Code plugin cache.

    Returns list of dicts: {name, namespace, description, model, color, path}.
    Deduplicates across plugin versions by taking the most recently modified.
    """
    agents = {}  # keyed by (namespace, name) to dedup versions

    for agents_dir in PLUGINS_CACHE.glob("*/*/agents"):
        # Extract namespace from path: cache/{org}/{plugin}/{version}/agents
        parts = agents_dir.relative_to(PLUGINS_CACHE).parts
        if len(parts) < 3:
            continue
        namespace = f"{parts[0]}:{parts[1]}"  # e.g. "helioy:helioy-tools"

        for md_file in agents_dir.glob("*.md"):
            name = md_file.stem
            key = (namespace, name)

            # Dedup: keep most recently modified version
            if key in agents and agents[key]["mtime"] >= md_file.stat().st_mtime:
                continue

            # Parse YAML frontmatter
            meta = _parse_frontmatter(md_file)
            agents[key] = {
                "name": name,
                "namespace": namespace,
                "description": meta.get("description", ""),
                "model": meta.get("model", "sonnet"),
                "color": meta.get("color"),
                "path": str(md_file),
                "mtime": md_file.stat().st_mtime,
            }

    # Merge static catalog if present
    if CATALOG_FILE.exists():
        try:
            catalog = json.loads(CATALOG_FILE.read_text())
            for entry in catalog:
                key = (entry["namespace"], entry["name"])
                if key not in agents:
                    entry["source"] = "catalog"
                    agents[key] = entry
        except (json.JSONDecodeError, KeyError):
            pass

    return sorted(agents.values(), key=lambda a: (a["namespace"], a["name"]))


def _parse_frontmatter(path: Path) -> dict:
    """Extract YAML frontmatter from a markdown file."""
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return {}
    end = text.index("---", 3)
    try:
        return yaml.safe_load(text[3:end]) or {}
    except Exception:
        return {}
```

### Caching strategy

Agent definitions change rarely (only on plugin install/update). Use a time-based cache with 60-second TTL:

```python
_agent_type_cache: list[dict] | None = None
_agent_type_cache_time: float = 0
CACHE_TTL = 60.0

def _get_agent_types() -> list[dict]:
    global _agent_type_cache, _agent_type_cache_time
    now = time.time()
    if _agent_type_cache is None or (now - _agent_type_cache_time) > CACHE_TTL:
        _agent_type_cache = _scan_agent_types()
        _agent_type_cache_time = now
    return _agent_type_cache
```

No SQLite table for the type catalog. The registry DB tracks *running* agents. The type catalog is a read-only derived view of what *could* run. Mixing them conflates two concerns.


## 2. Data Structures and Storage

### Running warrooms: new SQLite table

Add a `warrooms` table to the existing registry DB alongside `agents` and `nudge_log`:

```sql
CREATE TABLE IF NOT EXISTS warrooms (
    warroom_id   TEXT PRIMARY KEY,          -- user-chosen name, e.g. "design", "review"
    tmux_session TEXT NOT NULL,             -- tmux session name
    tmux_window  TEXT NOT NULL,             -- tmux window name (usually == warroom_id)
    cwd          TEXT NOT NULL,             -- working directory for all panes
    created_at   TEXT NOT NULL,
    status       TEXT NOT NULL DEFAULT 'active'  -- active | killed
);

CREATE TABLE IF NOT EXISTS warroom_members (
    warroom_id   TEXT NOT NULL REFERENCES warrooms(warroom_id) ON DELETE CASCADE,
    agent_type   TEXT NOT NULL,             -- e.g. "backend-engineer"
    tmux_target  TEXT NOT NULL,             -- e.g. "main:3.0"
    pane_id      TEXT NOT NULL,             -- tmux pane ID, e.g. "%7"
    agent_id     TEXT,                      -- populated once agent registers on bus
    spawned_at   TEXT NOT NULL,
    PRIMARY KEY (warroom_id, agent_type)
);
```

### Why a separate table instead of a column on `agents`?

The `agents` table tracks registration state driven by the SessionStart hook. Registration happens *after* spawn, asynchronously. The warroom tables track spawn intent and tmux topology, which exist before any agent registers. They answer different questions:

- `warrooms` + `warroom_members`: "What did the orchestrator ask for?" (spawn intent)
- `agents`: "What is actually running and reachable?" (registration state)

The `agent_id` column in `warroom_members` gets backfilled when the spawned agent's SessionStart hook fires and calls `register_agent`. The join key is `tmux_target`.

### In-memory representation for return values

```python
@dataclass
class WarroomMember:
    agent_type: str
    tmux_target: str
    pane_id: str
    agent_id: str | None  # None until registered
    status: str           # "spawning" | "registered" | "dead"

@dataclass
class Warroom:
    warroom_id: str
    tmux_session: str
    tmux_window: str
    cwd: str
    members: list[WarroomMember]
    created_at: str
    status: str  # "active" | "killed" | "degraded"
```


## 3. MCP Tool Signatures

### `warroom_discover`

```python
@mcp.tool()
def warroom_discover(
    query: str = "",
    namespace: str = "",
    limit: int = 50,
) -> list[dict]:
    """Search available agent types that can be spawned in a warroom.

    Scans on-disk agent definitions from installed Claude Code plugins.
    Supports substring matching on name and description.

    Args:
        query: Substring to match against agent name or description.
               Empty string returns all available types.
        namespace: Filter to a specific plugin namespace
                   (e.g. "helioy:helioy-tools"). Empty = all.
        limit: Maximum results to return.

    Returns:
        List of {name, namespace, description, model, color} dicts.
    """
```

**Return shape:**
```json
[
  {
    "name": "backend-engineer",
    "namespace": "helioy:helioy-tools",
    "description": "Use this agent when building server-side APIs...",
    "model": "opus",
    "color": "green"
  }
]
```

**Error cases:** None fatal. Empty results if no matches. Filesystem scan failures logged but swallowed (return empty list with a warning field).


### `warroom_spawn`

```python
@mcp.tool()
def warroom_spawn(
    name: str,
    agent_types: list[str],
    cwd: str = "",
    prompt: str = "",
    layout: str = "tiled",
) -> dict:
    """Spawn a warroom: a tmux window with one pane per agent type.

    Creates a new tmux window, splits it into panes (one per agent type),
    sets canonical pane titles for identity resolution, and launches
    Claude Code with --agent in each pane.

    Idempotent: if a warroom with this name exists, it is killed first.

    Args:
        name: Warroom identifier (becomes the tmux window name).
              Must be alphanumeric + hyphens, 1-30 chars.
        agent_types: List of agent type names to spawn.
                     Each must exist in the agent type registry.
                     Max 8 agents per warroom (tmux pane limit).
        cwd: Working directory for all agents. Defaults to the
             caller's cwd if omitted.
        prompt: Optional initial prompt to send to all agents after
                spawn. Useful for briefing the warroom.
        layout: tmux layout algorithm. One of: tiled, even-horizontal,
                even-vertical, main-horizontal, main-vertical.

    Returns:
        {warroom_id, tmux_window, members: [{agent_type, tmux_target, pane_id}],
         spawned_at}
    """
```

**Return shape:**
```json
{
  "warroom_id": "design",
  "tmux_window": "design",
  "members": [
    {"agent_type": "brand-guardian", "tmux_target": "main:3.0", "pane_id": "%12"},
    {"agent_type": "ui-designer", "tmux_target": "main:3.1", "pane_id": "%13"}
  ],
  "spawned_at": "2026-03-17T10:00:00+00:00"
}
```

**Error cases:**
- `ValueError`: invalid name format, empty agent_types, >8 agents, unknown agent type
- `RuntimeError`: not inside tmux (`$TMUX` unset)
- `RuntimeError`: tmux new-window or split-window fails (resource exhaustion, dead session)
- Partial failure: if pane 3 of 5 fails to split, return partial result with error field listing which agents failed. Do not roll back successful panes.


### `warroom_kill`

```python
@mcp.tool()
def warroom_kill(
    name: str = "",
    kill_all: bool = False,
) -> dict:
    """Kill a warroom or all warrooms.

    Kills the tmux window and removes warroom records from the registry.
    Agents in killed panes are pruned from the agent registry on the
    next list_agents call (existing lazy-prune behavior).

    Args:
        name: Warroom to kill. Required unless kill_all is True.
        kill_all: Kill every tracked warroom. Overrides name.

    Returns:
        {killed: [warroom_id, ...], errors: [str, ...]}
    """
```

**Error cases:**
- `ValueError`: neither name nor kill_all provided
- Partial success: some windows may already be dead. Report per-warroom success/failure.


### `warroom_status`

```python
@mcp.tool()
def warroom_status(
    name: str = "",
) -> list[dict]:
    """Get status of warrooms and their member agents.

    Cross-references warroom_members with the agents table and tmux
    pane liveness to report per-member status.

    Args:
        name: Specific warroom to query. Empty = all warrooms.

    Returns:
        List of warroom dicts, each with members annotated with
        registration status and pane liveness.
    """
```

**Return shape:**
```json
[
  {
    "warroom_id": "design",
    "status": "active",
    "created_at": "2026-03-17T10:00:00+00:00",
    "members": [
      {
        "agent_type": "brand-guardian",
        "tmux_target": "main:3.0",
        "agent_id": "helioy-bus:brand-guardian:main:3.0",
        "registered": true,
        "pane_alive": true,
        "last_seen": "2026-03-17T10:05:00+00:00"
      },
      {
        "agent_type": "ui-designer",
        "tmux_target": "main:3.1",
        "agent_id": null,
        "registered": false,
        "pane_alive": true,
        "last_seen": null
      }
    ]
  }
]
```


## 4. tmux Subprocess Lifecycle Management

### The race condition problem

The warroom script reveals the core timing issue: pane title must be set *before* `send-keys` launches Claude, because the SessionStart hook reads the pane title to derive agent identity. The current bash script handles this with sequential execution within a single shell process. Translating to Python requires the same ordering guarantee.

### Proposed implementation pattern

```python
def _spawn_pane(
    window: str,
    cwd: str,
    agent_type: str,
    repo: str,
    is_first: bool = False,
) -> dict:
    """Spawn a single tmux pane with proper identity setup.

    Returns {pane_id, tmux_target} or raises on failure.

    Ordering contract:
    1. Create pane (new-window or split-window)
    2. Set pane title (select-pane -T) -- identity must be stable
    3. Lock window title options (allow-rename off)
    4. Send keys to launch Claude -- SessionStart hook reads title
    """
    # Step 1: create pane
    if is_first:
        result = subprocess.run(
            ["tmux", "new-window", "-n", window, "-c", cwd,
             "-P", "-F", "#{pane_id}"],
            capture_output=True, timeout=5,
        )
    else:
        result = subprocess.run(
            ["tmux", "split-window", "-t", window, "-c", cwd,
             "-P", "-F", "#{pane_id}"],
            capture_output=True, timeout=5,
        )

    if result.returncode != 0:
        raise RuntimeError(f"tmux pane creation failed: {result.stderr.decode().strip()}")

    pane_id = result.stdout.decode().strip()  # e.g. "%7"

    # Step 2: resolve tmux_target from pane_id
    target_result = subprocess.run(
        ["tmux", "display-message", "-p", "-t", pane_id,
         "#{session_name}:#{window_index}.#{pane_index}"],
        capture_output=True, timeout=3,
    )
    tmux_target = target_result.stdout.decode().strip()

    # Step 3: set canonical pane title BEFORE launching Claude
    title = f"{repo}:{agent_type}:{tmux_target}"
    subprocess.run(
        ["tmux", "select-pane", "-t", pane_id, "-T", title],
        capture_output=True, timeout=3,
    )

    # Step 4: lock window titles (idempotent, first pane sets it)
    if is_first:
        subprocess.run(
            ["tmux", "set-option", "-wt", window, "allow-rename", "off"],
            capture_output=True, timeout=3,
        )
        subprocess.run(
            ["tmux", "set-option", "-wt", window, "allow-set-title", "off"],
            capture_output=True, timeout=3,
        )

    # Step 5: launch Claude
    claude_cmd = f"claude --verbose --dangerously-skip-permissions --agent {agent_type}"
    subprocess.run(
        ["tmux", "send-keys", "-t", pane_id, claude_cmd, "Enter"],
        capture_output=True, timeout=3,
    )

    return {"pane_id": pane_id, "tmux_target": tmux_target}
```

### Race condition mitigations

1. **Title before launch:** The sequential subprocess calls within `_spawn_pane` guarantee title is set before `send-keys`. Python's `subprocess.run` is synchronous. No race.

2. **Registration lag:** After `send-keys`, Claude Code takes 2-5 seconds to boot and fire the SessionStart hook. The warroom_spawn return value includes `tmux_target` but `agent_id` is `None`. The orchestrator should poll `warroom_status` or `list_agents` to confirm registration. This is an inherent async gap. Do not try to paper over it with sleep/polling in the spawn tool itself.

3. **Pane index stability:** `split-window` can shift pane indices. Always use pane_id (`%N`) for targeting, never computed indices. The tmux_target (session:window.pane) is resolved immediately after creation and recorded. If tmux reflows panes, the pane_id remains stable.

4. **Layout after each split:** Call `tmux select-layout -t {window} {layout}` after each split to prevent pane-too-small failures on subsequent splits.

### Error handling for subprocess calls

Wrap all tmux subprocess calls in a helper:

```python
def _tmux(*args: str, timeout: int = 5) -> subprocess.CompletedProcess:
    """Run a tmux command with consistent error handling."""
    result = subprocess.run(
        ["tmux", *args],
        capture_output=True,
        timeout=timeout,
    )
    return result

def _tmux_check(*args: str, timeout: int = 5) -> str:
    """Run a tmux command, raise on failure, return stdout."""
    result = _tmux(*args, timeout=timeout)
    if result.returncode != 0:
        raise RuntimeError(
            f"tmux {args[0]} failed (rc={result.returncode}): "
            f"{result.stderr.decode().strip()}"
        )
    return result.stdout.decode().strip()
```


## 5. Integration with `register_agent` Flow

### Should `warroom_spawn` auto-register?

**No.** Registration should remain in the SessionStart hook, for three reasons:

1. **Single source of truth.** The SessionStart hook sets the PID file, resolves identity from the pane title, and calls `register_agent` with accurate process state (ppid, session_id). If `warroom_spawn` pre-registers, the hook would then `INSERT OR REPLACE` over it, making the pre-registration wasted work.

2. **Identity resolution accuracy.** The pane title format (`{repo}:{agent_type}:{session}:{window}.{pane}`) is read by the running agent's hook, which knows its own PID and session_id. The spawner does not have these values at spawn time because Claude Code has not started yet.

3. **Lifecycle consistency.** Non-warroom agents (manually started Claude sessions) use the same SessionStart hook path. Keeping warroom agents on the same path means `list_agents`, `send_message`, and liveness pruning all work identically regardless of how the agent was started.

### What `warroom_spawn` should do instead

1. Record spawn intent in `warrooms` + `warroom_members` tables (tmux_target, agent_type, pane_id).
2. Leave `agent_id` NULL in `warroom_members`.
3. `warroom_status` cross-references `warroom_members.tmux_target` with `agents.tmux_target` to backfill the join and report registration state.

### Backfill query

```sql
SELECT
    wm.agent_type,
    wm.tmux_target,
    wm.pane_id,
    a.agent_id,
    a.last_seen,
    CASE
        WHEN a.agent_id IS NOT NULL THEN 'registered'
        ELSE 'spawning'
    END AS status
FROM warroom_members wm
LEFT JOIN agents a ON wm.tmux_target = a.tmux_target
WHERE wm.warroom_id = ?
```

### Optional enhancement: warroom_id tag on registration

Add an optional `warroom_id` parameter to `register_agent`. The SessionStart hook could pass this if it detects it was launched in a warroom context (e.g., by inspecting the pane title format or an environment variable set by `warroom_spawn`). This would make the join explicit rather than relying on tmux_target matching.

Implementation: set `HELIOY_WARROOM_ID={name}` as an environment variable in the tmux pane before launching Claude:

```python
# In _spawn_pane, before send-keys:
subprocess.run(
    ["tmux", "send-keys", "-t", pane_id,
     f"export HELIOY_WARROOM_ID={warroom_id}", "Enter"],
    capture_output=True, timeout=3,
)
```

Then `register_agent` picks it up from `os.environ` and stores it.


## 6. Open Questions

1. **Max panes per warroom.** tmux has a practical limit around 8-12 panes before they become unusably small. Should we enforce a hard cap at 8, or let the user decide and accept tiny panes?

2. **Initial prompt delivery.** The `prompt` parameter on `warroom_spawn` could send a briefing to each agent. But the agent has not registered yet when spawn returns. Options: (a) use `tmux send-keys` to type the prompt into the pane after a brief delay, (b) pre-stage a message in the agent's inbox so it is waiting when SessionStart fires, (c) let the orchestrator use `send_message` after confirming registration via `warroom_status`. Option (b) is cleanest because it leverages existing infrastructure.

3. **`--dangerously-skip-permissions` flag.** The current warroom.sh hardcodes it. The MCP tool should probably accept a `permissions: str` parameter ("skip" | "normal") with "skip" as default for warroom agents, since they are supervised by an orchestrator.

4. **Multi-repo warrooms.** Current role-mode uses a single cwd. The repo-mode uses different cwds per pane. Should `warroom_spawn` support a `cwd_per_agent: dict[str, str]` override? Adds complexity. Could be a v2 feature.

5. **Dependency on `pyyaml`.** The frontmatter parser needs a YAML library. The bus server currently has no `pyyaml` dependency. Options: (a) add it, (b) use a regex-based frontmatter parser for the simple cases we need (name, description, model, color are all scalar values), (c) use `tomllib` if we switch frontmatter format. Option (b) is pragmatic for v1.
