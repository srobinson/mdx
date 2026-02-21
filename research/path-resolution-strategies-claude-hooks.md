---
title: Path Resolution Strategies for Claude Code Hooks, Agents, and Shell Scripts
type: research
tags: [claude-code, hooks, plugins, agents, paths, helioy, shell-scripts]
summary: Claude Code exposes $CLAUDE_PROJECT_DIR and $CLAUDE_PLUGIN_ROOT for hook path resolution; $HOME is reliable; ~ is NOT expanded in JSON hook command strings; HELIOY_ROOT env var is the right pattern for cross-machine portability.
status: active
source: quick-research
confidence: high
created: 2026-03-09
updated: 2026-03-09
---

## Summary

Claude Code provides two first-party env vars for path resolution in hooks:
- `$CLAUDE_PROJECT_DIR` — the project root (available to all hooks)
- `${CLAUDE_PLUGIN_ROOT}` — the plugin's installation directory (available to plugin hooks/MCP servers only)

`$HOME` is reliable in all hook execution contexts. Tilde (`~`) does NOT expand in JSON command strings because hooks run commands via `sh -c` with no shell expansion of the JSON string before substitution. The correct pattern for helioy-specific paths that live outside a plugin is a user-set `HELIOY_ROOT` environment variable in shell profile.

---

## Details

### 1. Claude Code Runtime Environment Variables

Confirmed from official docs (https://code.claude.com/docs/en/settings.md and hooks.md):

| Variable | Scope | Available in hooks? |
|---|---|---|
| `CLAUDE_PROJECT_DIR` | Current session | Yes — project root |
| `CLAUDE_SESSION_ID` | Current session | Yes |
| `CLAUDE_CONFIG_DIR` | User-configurable | Yes — `~/.claude` by default |
| `CLAUDE_CODE_ACCOUNT_UUID` | Authenticated user | Yes |
| `CLAUDE_CODE_USER_EMAIL` | Authenticated user | Yes |
| `CLAUDE_CODE_ORGANIZATION_UUID` | Authenticated user | Yes |
| `CLAUDE_CODE_TEAM_NAME` | Agent teams | Yes |
| `CLAUDE_CODE_TASK_LIST_ID` | Tasks | Yes |
| `CLAUDE_CODE_PLAN_MODE_REQUIRED` | Teammate-specific | Yes |
| `CLAUDE_CODE_REMOTE` | Remote web env | Yes (`"true"` or unset) |
| `CLAUDE_PLUGIN_ROOT` | Plugin hooks only | Yes — plugin install dir |

No `$CLAUDE_AGENT_MEMORY_DIR` or `$CLAUDE_AGENTS_DIR` exists. The memory dir convention (`~/.claude/agent-memory/<agent-name>/`) is baked into the platform, not exposed as a variable.

The docs explicitly state: "Handlers run in the current directory with Claude Code's environment." This means hooks inherit the full shell environment including `$HOME`, `$USER`, and any env vars set in the user's shell profile (`.zshrc`, `.zprofile`, etc.).

### 2. $CLAUDE_PLUGIN_ROOT for Plugin-Relative Paths

For hooks bundled inside a plugin, `${CLAUDE_PLUGIN_ROOT}` resolves to the plugin's installation directory regardless of where the plugin is cached. From the official example:

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "${CLAUDE_PLUGIN_ROOT}/scripts/format-code.sh"
          }
        ]
      }
    ]
  }
}
```

This also works in MCP server configuration within plugins:
```json
{
  "mcpServers": {
    "plugin-database": {
      "command": "${CLAUDE_PLUGIN_ROOT}/servers/db-server",
      "args": ["--config", "${CLAUDE_PLUGIN_ROOT}/config.json"]
    }
  }
}
```

**Critical constraint**: Marketplace-installed plugins are copied to `~/.claude/plugins/cache`. Files outside the plugin directory are not copied. Path traversal (`../shared-utils`) does not work after installation. Symlinks within the plugin directory ARE honored during the copy.

### 3. Tilde Expansion in Hook Command Strings

**Tilde does NOT expand reliably in JSON hook command strings.**

The hooks doc example shows this notation in a comment context:
```json
"command": "echo 'Memory operation initiated' >> ~/mcp-operations.log"
```

However, this only works because the shell interprets the tilde when the hook command string is passed to `sh -c`. The expansion happens at shell invocation time, not at JSON parse time. For paths embedded inside variable assignments or complex expressions, tilde expansion may not occur as expected depending on quoting context.

**Recommendation**: Always prefer `$HOME` over `~` in hook command strings for predictability:
```json
"command": "echo 'data' >> $HOME/mcp-operations.log"
```

The current helioy `crew-precompact.sh` correctly uses `${HOME}` for the bus inbox path:
```bash
BUS_INBOX="${HOME}/.claude/helioy-bus/orchestrator/inbox"
```

This is the right pattern.

### 4. BASH_SOURCE / dirname for Script Self-Location

The standard bash self-location pattern works correctly inside Claude Code hook scripts because hooks run in a real shell process:

```bash
#!/usr/bin/env bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
```

This gives the directory containing the script, regardless of where the script is invoked from. This is reliable because:
- Hook scripts are invoked with their full path (either `${CLAUDE_PLUGIN_ROOT}/scripts/foo.sh` or resolved absolute path)
- `BASH_SOURCE[0]` contains the path used to invoke the script
- The `cd && pwd` pattern resolves symlinks and relative components

**When this works best**: Scripts that live inside the plugin alongside the hooks that call them. The hook references `${CLAUDE_PLUGIN_ROOT}/scripts/foo.sh`, and within `foo.sh`, `BASH_SOURCE[0]` resolves to that same installed path.

**When this is unnecessary**: If the hook command uses `${CLAUDE_PLUGIN_ROOT}` to reference the script, the script already knows where it lives — `BASH_SOURCE[0]` and `${CLAUDE_PLUGIN_ROOT}` will agree.

### 5. helioy-Specific Recommendation: HELIOY_ROOT

The helioy ecosystem has paths that live in the dev directory (`~/Dev/LLM/DEV/helioy/`) that are not inside any plugin. These cannot use `${CLAUDE_PLUGIN_ROOT}`. The right solution is a `HELIOY_ROOT` environment variable set in the user's shell profile.

**Set in `~/.zprofile` or `~/.zshrc`:**
```bash
export HELIOY_ROOT="${HOME}/Dev/LLM/DEV/helioy"
export HELIOY_PLUGINS_DIR="${HELIOY_ROOT}/helioy-plugins/plugins"
```

**Then in hooks.json:**
```json
{
  "hooks": {
    "SessionStart": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "${HELIOY_ROOT}/scripts/preflight.sh"
          }
        ]
      }
    ]
  }
}
```

**Then in shell scripts:**
```bash
#!/usr/bin/env bash
: "${HELIOY_ROOT:?HELIOY_ROOT is not set. Add it to ~/.zprofile}"
CREW_HOOK_DIR="${HELIOY_PLUGINS_DIR}/helioy-tools/hooks"
```

Because hooks run with Claude Code's inherited environment (which sources the user's shell profile), `$HELIOY_ROOT` will be available to all hooks.

**For `~/.mdx` and agent memory paths**, use `$HOME`-relative:
```bash
RESEARCH_DIR="${HOME}/.mdx/research"
AGENT_MEMORY_DIR="${HOME}/.claude/agent-memory"
```

These are already under `$HOME`, so they survive dev directory moves. Only the dev tree paths (`~/Dev/LLM/DEV/helioy/...`) need `HELIOY_ROOT`.

### 6. Current State of helioy Hooks (What's Already Good)

The `crew-precompact.sh` script already uses the correct pattern:
- `${HOME}/.claude/helioy-bus/orchestrator/inbox` — correct, uses `$HOME`
- `${CLAUDE_SESSION_ID:-unknown}` — correct, uses official env var with fallback

The `hooks.json` inline commands use `~/Dev/LLM/DEV/helioy` via the `SessionStart` hook. That specific path needs `$HELIOY_ROOT`.

The agent definition for `helioy.sub.quick-research` uses:
```yaml
command: "cat >> ~/.claude/agent-memory/helioy-sub-quick-research/sessions.jsonl; true"
```
The `~` here is in a YAML string that becomes a shell command. This works because the hook command is run through the shell which expands `~` in simple unquoted contexts. However, `$HOME` is more explicit and correct.

### 7. Convention Table: What to Use Where

| Path Type | Best Variable | Example |
|---|---|---|
| Plugin-bundled scripts | `${CLAUDE_PLUGIN_ROOT}` | `${CLAUDE_PLUGIN_ROOT}/scripts/run.sh` |
| Project-relative scripts | `$CLAUDE_PROJECT_DIR` | `"$CLAUDE_PROJECT_DIR"/.claude/hooks/lint.sh` |
| User home dir | `$HOME` | `$HOME/.mdx/research/` |
| helioy dev tree | `$HELIOY_ROOT` (user-set) | `${HELIOY_ROOT}/helioy-plugins/` |
| Agent memory | `$HOME` | `$HOME/.claude/agent-memory/<agent>/` |
| helioy-bus inbox | `$HOME` | `$HOME/.claude/helioy-bus/orchestrator/inbox` |
| Research output | `$HOME` | `$HOME/.mdx/research/` |

### 8. Agent Definition Files and Path References

Agent definition files (`.md` with YAML frontmatter) do not perform variable expansion in the frontmatter fields themselves. The `command` string in a `hooks` block within frontmatter is passed to the shell for execution, so env vars in that string DO expand at runtime. Tilde in that context is shell-expanded.

The body text of agent definitions (the system prompt) is just a string — no path expansion occurs. If an agent prompt refers to `~/.mdx/research/`, it is a human-readable instruction to the LLM, not an OS path being resolved. This is fine.

---

## Sources

- https://code.claude.com/docs/en/hooks.md — Hook lifecycle, execution context, `$CLAUDE_PROJECT_DIR` and `$CLAUDE_PLUGIN_ROOT` documentation
- https://code.claude.com/docs/en/plugins-reference.md — `${CLAUDE_PLUGIN_ROOT}` variable, plugin caching behavior, path traversal limitations
- https://code.claude.com/docs/en/settings.md — Full list of Claude Code runtime environment variables
- https://code.claude.com/docs/en/sub-agents.md — Agent frontmatter hooks, memory scope paths
- `/Users/alphab/Dev/LLM/DEV/helioy/helioy-plugins/plugins/helioy-tools/hooks/crew-precompact.sh` — Current helioy hook implementation
- `/Users/alphab/Dev/LLM/DEV/helioy/helioy-plugins/plugins/helioy-tools/hooks/hooks.json` — Current helioy hooks configuration

---

## Open Questions

1. **Does `$CLAUDE_CONFIG_DIR` reflect a non-default config dir?** The docs say it is "customizable via environment variable" but do not clarify whether the default `~/.claude` is exposed as this var when not customized. Needs empirical testing.

2. **Tilde in JSON string edge cases**: The official docs show `~/mcp-operations.log` in an example hook command. Does Claude Code pre-process the command string before passing to shell, or does the shell always expand it? The safe answer is to use `$HOME` regardless.

3. **HELIOY_ROOT adoption**: If helioy grows to multiple machines or CI environments, `HELIOY_ROOT` needs to be set in those environments too. A bootstrap script or dotfiles entry would be required.

4. **`$CLAUDE_CONFIG_DIR` for agent memory**: If `CLAUDE_CONFIG_DIR` is reliably set and points to `~/.claude`, it could replace hardcoded `$HOME/.claude` references. Worth testing in a hook script: `echo $CLAUDE_CONFIG_DIR`.
