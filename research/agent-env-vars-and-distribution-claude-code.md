---
title: Claude Code Agent Hook Environment Variables and Agent Distribution
type: research
tags: [claude-code, agents, hooks, environment-variables, plugins, distribution]
summary: Documents which env vars work in agent-level hook commands, how hook commands are executed, and all mechanisms for distributing agent definitions across machines and teams.
status: active
source: quick-research
confidence: high
created: 2026-03-09
updated: 2026-03-09
---

## Summary

**Question 1 (Env vars in agent hooks):** Only two env vars are officially documented for hook command strings: `$CLAUDE_PROJECT_DIR` and `${CLAUDE_PLUGIN_ROOT}`. `$CLAUDE_SESSION_ID` does NOT exist as an env var — the session ID is only available via stdin JSON (`session_id` field). `$HOME` works because hooks inherit the full shell environment. Hook commands run with "Claude Code's environment" (no explicit sh -c documentation, but stdin JSON piping implies a shell invocation).

**Question 2 (Agent distribution):** Plugins CAN bundle agent definitions in their `agents/` directory. This is fully supported in the plugin system. However, a known bug (issue #17524, still open as of 2026-03-09) prevented plugin agents from loading in some versions. The fix landed around v2.1.37. The canonical distribution mechanism is `claude plugin install <plugin>@<marketplace>`. Community collections like VoltAgent, lst97, and contains-studio all distribute via plugin marketplaces (`claude plugin install` or `/plugin install`).

---

## Details

### Question 1: Environment Variables in Agent Hook Commands

#### What is documented

The official hooks reference at `https://code.claude.com/docs/en/hooks` says:

> "Handlers run in the current directory with Claude Code's environment."

And specifically, under "Reference scripts by path":

> - `$CLAUDE_PROJECT_DIR`: the project root. Wrap in quotes to handle paths with spaces.
> - `${CLAUDE_PLUGIN_ROOT}`: the plugin's root directory, for scripts bundled with a plugin.

These are the **only two env vars explicitly documented** for use in hook command strings.

#### Variable-by-variable answers

| Variable | Available in agent hooks? | Notes |
|---|---|---|
| `$CLAUDE_PROJECT_DIR` | Yes | Documented. Points to project root. |
| `${CLAUDE_PLUGIN_ROOT}` | Plugin hooks only | Documented for plugin `hooks/hooks.json`. Not defined if the hook is in an agent frontmatter that is NOT inside a plugin. |
| `$CLAUDE_SESSION_ID` | No | Does not exist as an env var. This is a feature request (issue #17188, open). Session ID is only available in hook stdin JSON as `session_id`. |
| `$CLAUDE_CONFIG_DIR` | Not documented | `CLAUDE_CONFIG_DIR` exists as a user-configurable env var to override where Claude stores its config, but it is not injected into hooks. |
| `$HOME` | Yes | Hooks inherit the full shell environment, so standard variables like `HOME`, `PATH`, `USER` are available. |
| `$CLAUDE_CODE_REMOTE` | Yes | Set to `"true"` in remote web environments, not set locally. Documented as available to hooks. |

#### `${CLAUDE_PLUGIN_ROOT}` in agent-level hooks

`${CLAUDE_PLUGIN_ROOT}` resolves to the plugin directory. In agent frontmatter hooks, it is only defined when the agent itself is bundled inside a plugin. If the agent lives in `~/.claude/agents/` or `.claude/agents/` (standalone, not in a plugin), `${CLAUDE_PLUGIN_ROOT}` is undefined in the hook command.

Example from an agent inside a plugin's `agents/` directory — valid:

```yaml
---
name: db-reader
description: Execute read-only database queries
tools: Bash
hooks:
  PreToolUse:
    - matcher: "Bash"
      hooks:
        - type: command
          command: "${CLAUDE_PLUGIN_ROOT}/scripts/validate-readonly-query.sh"
---
```

This works because `${CLAUDE_PLUGIN_ROOT}` is set when the plugin is loaded. For a standalone agent in `~/.claude/agents/`, use `$HOME` or `$CLAUDE_PROJECT_DIR` instead.

#### How hook commands are executed

The docs do not explicitly state `sh -c` but demonstrate hook scripts with `#!/bin/bash` shebangs and pipe JSON via stdin. The statement "Handlers run in the current directory with Claude Code's environment" implies the command string is passed to a shell. Standard shell variable expansion (`$VAR` and `${VAR}`) works in command strings, consistent with `sh -c` invocation.

Key behavior:
- JSON context arrives via **stdin** for `type: command` hooks
- The shell environment includes Claude Code's own inherited env
- Hooks have access to all env vars the Claude Code process itself has

#### Getting session ID in hooks (workaround)

Since `$CLAUDE_SESSION_ID` does not exist, the workaround (from community issue #17188) is to extract it from the SessionStart hook's stdin JSON:

```bash
#!/usr/bin/env bash
INPUT=$(cat)
SESSION_ID=$(echo "$INPUT" | jq -r '.session_id // empty')
# Use SESSION_ID for downstream logic
```

The `session_id` field is present in all hook stdin JSON payloads.

---

### Question 2: Agent Distribution and Deployment

#### Plugin-bundled agents: fully supported

Yes, plugins CAN bundle agent definitions. The `agents/` directory at the plugin root is an officially supported plugin component. From the plugins reference:

> **Location**: `agents/` directory in plugin root
> **File format**: Markdown files describing agent capabilities

The priority chain is:
1. `--agents` CLI flag (session-only)
2. `.claude/agents/` (project-scoped)
3. `~/.claude/agents/` (user-scoped)
4. Plugin's `agents/` directory (lowest priority, where plugin is enabled)

Plugin agents appear in `/agents` alongside custom agents and are namespaced as `plugin-name:agent-name`.

#### Known bug with plugin agent loading (fixed ~v2.1.37)

Issue #17524 (filed 2026-01-11, still open but with community confirmation of fix): in versions around 2.1.4, plugin agents and skills were NOT discovered — only MCP servers loaded from plugins. The fix appeared around v2.1.37 based on a commenter's confirmation.

Symptom: `/agents` showed empty list even with agents in plugin `agents/` directory.

Workaround (if on older version): symlink the plugin agents directory:

```bash
ln -s ~/.claude/plugins/my-plugin/agents ~/.claude/agents
```

A secondary symptom (also confirmed): plugin agents DO load but are only reachable by their namespaced name `plugin-name:agent-name`, not the bare name. When invoked by bare name, Claude gets an error showing the namespaced form is available.

#### Distribution mechanisms

| Mechanism | What it installs | Use case |
|---|---|---|
| `claude plugin install <name>@<marketplace>` | Skills, agents, hooks, MCP servers, LSP servers — the full plugin | Primary distribution method |
| `/plugin install` (in-app) | Same as above, interactive | User-facing install |
| `--plugin-dir ./my-plugin` | Same, for the current session only | Development/testing |
| Manual: copy `.md` files to `~/.claude/agents/` | Only agent files | Quick personal use, no marketplace needed |
| Checked into `.claude/agents/` in a repo | Agent files only, scoped to project | Team sharing via version control |

#### Community collections distribution

The major community agent collections all use the **plugin marketplace system**:

- **VoltAgent** (`contains-studio`, `lst97`): distributed via GitHub-hosted marketplaces, installed with `claude plugin install plugin-name@marketplace-url`
- Anthropic's official marketplace is at `claude.ai/settings/plugins` and `platform.claude.com/plugins`
- Community marketplaces are plain JSON files (`marketplace.json`) hosted anywhere (GitHub repos, web servers)

#### Is there a simpler "copy-paste" path?

Yes, for agent-only distribution without building a full plugin:
- Drop `.md` files into `~/.claude/agents/` (user-scoped, all projects)
- Drop `.md` files into `.claude/agents/` (project-scoped, commit to repo)
- No CLI command needed; agents are discovered from these directories at session start

#### Plugin manifest agent path configuration

The `plugin.json` manifest supports an `agents` field to specify non-default agent file locations:

```json
{
  "name": "my-plugin",
  "agents": "./custom-agents/"
}
```

Custom paths supplement the default `agents/` directory rather than replacing it.

#### Are there proposals for plugin-bundled agents?

The plugin-bundled agent support is already shipped and documented. The main open discussion threads are:
- Issue #17524: bug about agents not loading from plugins (partially resolved)
- Issue #30727: request for an official verified marketplace for agents (community wants curated discovery)
- Issue #15439: request for `ref` and `path` params in plugin source schema (version pinning for plugin installs)

---

## Sources

- `https://code.claude.com/docs/en/hooks` — hooks reference (env vars, execution context)
- `https://code.claude.com/docs/en/sub-agents` — subagent docs (frontmatter hooks, distribution)
- `https://code.claude.com/docs/en/plugins-reference` — plugin component specs (agents directory, CLAUDE_PLUGIN_ROOT)
- `https://code.claude.com/docs/en/plugins` — plugin authoring guide
- `https://code.claude.com/docs/en/settings` — env var reference (CLAUDE_PROJECT_DIR, CLAUDE_CONFIG_DIR)
- GitHub issue #17524 (anthropics/claude-code): plugin agents not discovered
- GitHub issue #17188 (anthropics/claude-code): feature request for CLAUDE_SESSION_ID env var

---

## Open Questions

1. **Does `${CLAUDE_PLUGIN_ROOT}` expand in agent frontmatter hooks for plugin-bundled agents?** Documented behavior says yes (it's defined when the plugin is loaded), but not explicitly tested for the frontmatter-in-agent case vs. the hooks.json case.

2. **Is `$CLAUDE_CONFIG_DIR` injected into the hook subprocess environment?** It is a documented Claude Code env var but not confirmed as injected. If the user has set it in their shell, it will be present; if only set in `settings.json` under `env`, it may not be.

3. **Plugin agent namespacing when invoked by Claude.** Does Claude reliably invoke `plugin-name:agent-name` by description match, or does the user need to specify the full namespaced name? Issue comments suggest bare-name invocation fails in some versions.
