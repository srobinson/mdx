---
title: OpenAI Codex CLI - Internals and Extension Points
type: research
tags: [codex, openai, cli, hooks, mcp, agent, config]
summary: Codex CLI (Rust) has a hooks system with 3 events, MCP server support, agent roles, profiles, and TOML config at ~/.codex/config.toml. No tmux integration or PreToolUse/PostToolUse equivalents.
status: active
source: quick-research
confidence: high
created: 2026-03-19
updated: 2026-03-19
---

## Summary

OpenAI Codex CLI (github.com/openai/codex) is a Rust-based coding agent. It has a hooks system with 3 lifecycle events (not equivalent to Claude Code's PreToolUse/PostToolUse), native MCP server support, a profile/agent-role system, and TOML-based config layered across global/project scopes. No tmux integration exists.

## Details

### 1. Hooks / Lifecycle System

**Yes, hooks exist -- but with 3 events only, not per-tool granularity.**

Hook configs live in `hooks.json` files discovered from each config layer (see config locations below). They are **not** in `config.toml`.

**Three hook events:**

| Event | Trigger | Equivalent in Claude Code |
|---|---|---|
| `SessionStart` | Session initialization or resume | `SessionStart` |
| `UserPromptSubmit` | User submits a prompt | No direct equivalent |
| `Stop` | Session/turn ends | `Stop` |

**No** `PreToolUse`, `PostToolUse`, or per-tool hook equivalents exist.

**hooks.json structure:**

```json
{
  "hooks": {
    "SessionStart": [
      {
        "matcher": "optional_regex",
        "hooks": [
          {
            "type": "command",
            "command": "/path/to/script",
            "timeout_sec": 30,
            "async": false,
            "statusMessage": "Running hook..."
          }
        ]
      }
    ],
    "UserPromptSubmit": [],
    "Stop": []
  }
}
```

Handler types: `command` (external process), `prompt` (inject into model context), `agent` (autonomous agent).

Handlers run **concurrently** via `join_all()`. Exit code 0 = success (parse JSON stdout), exit code 2 = block (read reason from stderr).

**SessionStart hook input payload (JSON via stdin):**

```json
{
  "hook_event_name": "SessionStart",
  "session_id": "<uuid>",
  "transcript_path": "/path/or/null",
  "cwd": "/current/dir",
  "model": "gpt-5.1",
  "permission_mode": "default|acceptEdits|plan|dontAsk|bypassPermissions",
  "source": "startup|resume|clear"
}
```

**Stop hook input payload adds:**
- `stop_hook_active`: boolean
- `last_assistant_message`: string or null

**UserPromptSubmit hook input payload adds:**
- `prompt`: the user's submitted text

**Hook output fields hooks can return:**
- `continue`: boolean (false = halt)
- `stopReason`: string
- `decision`: `"block"` (requires `reason`)
- `reason`: blocking rationale or continuation prompt
- `additionalContext`: text injected into model context (SessionStart only)
- `systemMessage`: warning to display
- `suppress_output`: boolean (Stop only)

### 2. Environment Variables

Codex sets/reads these environment variables:

| Variable | Direction | Purpose |
|---|---|---|
| `CODEX_HOME` | Read | Override default `~/.codex` home dir |
| `CODEX_SANDBOX` | Set | Set to `"seatbelt"` when spawning under macOS Seatbelt sandbox |
| `CODEX_SANDBOX_NETWORK_DISABLED` | Set | Set to `1` inside sandbox shell sessions to signal network is blocked |
| `RUST_LOG` | Read | Controls logging verbosity (TUI default: `codex_core=info,codex_tui=info,codex_rmcp_client=info`; exec mode defaults to `error`) |
| `SHELL` / `COMSPEC` | Read | Determines which shell to invoke for hook commands |

**No equivalents to `CLAUDE_PROJECT_DIR` or `CLAUDE_SESSION_ID` are passed to hook commands.** Hook data is delivered via JSON on stdin, not environment variables.

### 3. tmux Integration

**None.** Codex has no tmux awareness, pane title setting, or session detection. The TUI runs directly in the terminal without tmux management.

### 4. Agent Roles / --agent Flag

**No `--agent` CLI flag exists at the top level.** Agent roles are an internal orchestration concept, not a user-facing CLI flag.

Three built-in roles:
- `default` - general agent
- `explorer` - codebase questions, fast and authoritative
- `worker` - execution work (features, bugs)
- `awaiter` - monitors task completion (background polling, `model_reasoning_effort = "low"`)

Roles are defined as TOML files under `agents/` dirs in config layers, or inline in `config.toml` under `[agents.roles.<name>]`. The multi-agent tool handler owns role selection when spawning sub-agents.

Custom roles support:
- `description` (required)
- `config_file`: path to external TOML with role settings
- `nickname_candidates`: alternative names list
- `developer_instructions`: system prompt override

**Related CLI flag:** `--profile <PROFILE>` selects a named configuration profile (model, provider, sandbox, approval policy).

### 5. MCP Server Support

**Yes, full MCP support via the `codex mcp` subcommand.**

**CLI management:**
```bash
# stdio transport
codex mcp add <NAME> -- <COMMAND> [ARGS...] --env KEY=VALUE

# HTTP transport
codex mcp add <NAME> --url <URL> --bearer-token-env-var MY_TOKEN_VAR

codex mcp list [--json]
codex mcp get <NAME> [--json]
codex mcp remove <NAME>
codex mcp login <NAME>   # OAuth
codex mcp logout <NAME>
```

**config.toml format:**
```toml
[mcp_servers.<name>]
# stdio transport
command = "/path/to/server"
args = ["--flag"]
env = { KEY = "value" }
cwd = "/optional/cwd"

# or HTTP transport
url = "https://server/endpoint"
bearer_token_env_var = "MY_TOKEN_VAR"

# common options
startup_timeout_sec = 30
tool_timeout_sec = 60
# tool filtering
enabled_tools = ["tool1", "tool2"]
disabled_tools = ["tool3"]
```

MCP servers are stored in `~/.codex/config.toml`. Per-project MCP servers can be added via `.codex/config.toml` in the project tree.

Codex also exposes itself as an MCP server: `codex mcp-server` runs a stdio MCP interface with lifecycle notifications (`thread/started`, `turn/completed`, `account/login/completed`) and approval requests (`applyPatchApproval`, `execCommandApproval`).

### 6. Config File Format and Location

**Format:** TOML

**Config layer stack (lowest to highest precedence):**

1. Built-in defaults
2. Cloud managed requirements
3. Admin managed preferences (macOS MDM)
4. System: `/etc/codex/requirements.toml` (Unix) or `%ProgramData%\OpenAI\Codex\requirements.toml` (Windows)
5. User: `~/.codex/config.toml` (or `$CODEX_HOME/config.toml`)
6. Project tree: parent dirs searched for `.codex/config.toml` (disabled if untrusted)
7. Repository root: `$(git rev-parse --show-toplevel)/.codex/config.toml`
8. Runtime: CLI flags via `-c KEY=VALUE` dotted-path overrides

**Hook configs:** `hooks.json` in the same config folder as each layer's `config.toml`.

**Key config.toml fields:**

```toml
model = "gpt-5.1"
model_reasoning_effort = "high"  # high | medium | low
web_search_mode = "disabled"     # live | cached | disabled

[permissions]
sandbox_policy = "read_only"  # danger_full_access | read_only | workspace_write

[tui]
theme = "dracula"
animations = true

[memories]
generate_memories = false
use_memories = false

[history]
persistence = "save_all"  # save_all | none

[mcp_servers.my-server]
command = "/usr/local/bin/my-mcp-server"
args = []

[agents.roles.my-role]
description = "My custom agent role"
# developer_instructions = "..."

[profiles.fast]
model = "gpt-4o-mini"
sandbox_policy = "workspace_write"
```

**Codex home directory contents:**
- `config.toml` - user config
- `hooks.json` - user-level hooks
- `log/codex-tui.log` - TUI log file
- SQLite database (session history)
- OAuth credentials

**Schema:** `codex-rs/core/config.schema.json` (for IDE autocompletion)

## Sources

- `codex-rs/hooks/src/events/` - hook event structs
- `codex-rs/hooks/schema/generated/` - JSON schemas for hook I/O
- `codex-rs/hooks/src/engine/` - hook dispatch, config, command runner
- `codex-rs/cli/src/main.rs` - CLI flags and subcommands
- `codex-rs/core/src/config_loader/` - layer stack, file paths
- `codex-rs/core/src/config/` - ConfigToml, profiles, agent roles
- `codex-rs/core/src/agent/role.rs` - built-in roles (default, explorer, worker, awaiter)
- `codex-rs/cli/src/mcp_cmd.rs` - MCP subcommand
- `codex-rs/docs/codex_mcp_interface.md` - MCP server interface docs
- `.github/codex/home/config.toml` - example config in repo

## Open Questions

- Exact env vars passed to hook command processes (code showed no explicit env injection beyond shell detection -- data goes via stdin JSON only)
- Whether `--role` or `--agent-type` flags exist at CLI level for user-facing role selection (currently appears to be internal/sub-agent only)
- Full list of `features` flag names for `codex features list`
