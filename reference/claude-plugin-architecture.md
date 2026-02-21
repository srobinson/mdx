---
title: Claude Code Plugin Architecture — Install, Registration, Lifecycle
type: reference
tags: [claude-code, plugins, architecture, marketplace, helioy-plugins]
summary: Complete plugin lifecycle from marketplace registration through install, caching, and runtime loading. Hard-won from hands-on debugging Feb 2026.
status: active
created: 2026-02-21
updated: 2026-02-21
project: helioy
confidence: high
---

# Claude Code Plugin Architecture

## File System Layout

### Registration (survives ~/.claude.json deletion)

| File                                                        | Purpose                                             |
| ----------------------------------------------------------- | --------------------------------------------------- |
| `~/.claude/settings.json`                                   | User policies, permissions, **plugin registration** |
| `~/.claude/plugins/installed_plugins.json`                  | Version, scope, install timestamp                   |
| `~/.claude/plugins/known_marketplaces.json`                 | Marketplace sources (GitHub, local dir)             |
| `~/.claude/plugins/cache/<marketplace>/<plugin>/<version>/` | Cached plugin artifacts                             |

### Runtime State (regenerated on delete)

| File             | Purpose                                                  |
| ---------------- | -------------------------------------------------------- |
| `~/.claude.json` | OAuth, MCP server configs, per-project data, preferences |

**Critical insight**: Deleting `~/.claude.json` does NOT lose plugin registration. Plugins
live in `~/.claude/settings.json`. The `.json` file is runtime state that regenerates.

## Plugin Directory Structure

```
my-plugin/
  .claude-plugin/
    plugin.json            # Manifest: name, version, description
  skills/
    my-skill/SKILL.md      # Skills (frontmatter + body)
  hooks/
    hook-config.json        # Lifecycle hooks
  .mcp.json                # MCP server definitions
  commands/
    my-command.md           # Slash commands
  agents/
    my-agent.md             # Custom subagents
```

### plugin.json Manifest

```json
{
  "name": "helioy-tools",
  "version": "0.1.0",
  "description": "Helioy ecosystem tools"
}
```

## Install Flow

### 1. Add Marketplace

```bash
# From GitHub repo
/plugin marketplace add srobinson/helioy-plugins

# From local directory (dev mode)
claude --plugin-dir /path/to/helioy-plugins   # session-only
```

Marketplace registration stored in `~/.claude/plugins/known_marketplaces.json`:

```json
{
  "helioy": {
    "source": {
      "source": "local_directory",
      "path": "/Users/alphab/Dev/LLM/DEV/helioy-plugins"
    }
  }
}
```

### 2. Install Plugin

```bash
/plugin install helioy-tools@helioy
```

This copies the plugin to the cache directory and registers it:

- Cache: `~/.claude/plugins/cache/helioy/helioy-tools/0.1.0/`
- Registration: `~/.claude/settings.json` → `enabledPlugins.helioy-tools@helioy: true`
- Metadata: `~/.claude/plugins/installed_plugins.json` → version, scope, timestamp

### 3. Runtime Loading

On session start, Claude Code:

1. Reads `~/.claude/settings.json` for enabled plugins
2. Loads each plugin from its cache directory
3. Discovers skills/, hooks/, .mcp.json, commands/, agents/
4. Skills appear as available `/skill-name` commands
5. MCP servers from `.mcp.json` are started
6. Hooks are registered for their lifecycle events

## Skill Loading — Progressive Disclosure

Skills use a two-phase loading model:

1. **Always in context** (~100 words each): Frontmatter `name` + `description` from every
   installed skill. This is the "menu" Claude sees for skill matching.
2. **Loaded on trigger** (<5k words): Full SKILL.md body loaded only when the skill is
   invoked. Contains detailed instructions, tool references, workflows.

This means 11 skills cost ~1,100 tokens in permanent context — negligible.

### SKILL.md Frontmatter Pattern

```yaml
---
name: linear-workflow
description: Create and manage Linear issues following Helioy ways of working.
---
```

**Only `name` and `description` in frontmatter.** Everything else goes in the body.
Tools are woven naturally into workflow instructions, not listed in a dedicated section.

## MCP Servers in Plugins

Plugin `.mcp.json` defines MCP servers that start with the session:

```json
{
  "mcpServers": {
    "am": {
      "command": "npx",
      "args": ["-y", "attention-matters", "serve"]
    },
    "fmm": {
      "command": "npx",
      "args": ["-y", "frontmatter-matters", "serve"]
    },
    "mdx": {
      "command": "npx",
      "args": ["-y", "--package", "mdcontext", "mdcontext-mcp"]
    }
  }
}
```

**Note**: `mdcontext-mcp` is a separate binary from the `mdcontext` CLI. The npm package
exposes both. Use `--package mdcontext` with the binary name `mdcontext-mcp`.

## Hooks in Plugins

Hooks are JSON config files that fire shell commands on lifecycle events:

| Event                    | When                             |
| ------------------------ | -------------------------------- |
| SessionStart             | Session begins                   |
| SessionEnd / Stop        | Session ends                     |
| PreCompact               | Before context window compaction |
| PreToolUse / PostToolUse | Before/after tool execution      |
| Notification             | On notification events           |

## Dev vs Production

| Scenario                 | How Plugins Load                                      |
| ------------------------ | ----------------------------------------------------- |
| Local dev                | `claude --plugin-dir ./helioy-plugins` (session flag) |
| Installed                | `/plugin install helioy-tools@helioy` (persistent)    |
| Isolated agents (nancyr) | nancyr stamps `~/.claude/settings.json` per worker    |
| K8s / containers         | Mount plugin cache + settings.json into container     |

## Helioy Plugin — Current State

```
helioy-plugins/
  plugins/
    helioy-tools/
      .claude-plugin/plugin.json
      .mcp.json                    # am, fmm, mdx
      hooks/SessionStart.json      # am_query reminder
      skills/                      # 11 skills
        memory/SKILL.md
        linear-workflow/SKILL.md
        fmm/SKILL.md
        fmm-navigate/SKILL.md
        knowledge-base/SKILL.md
        create-spec/SKILL.md
        nancy-orchestrator/SKILL.md
        nancy-send-message/SKILL.md
        nancy-update-spec/SKILL.md
        nancy-session-history/SKILL.md
        check-directives/SKILL.md
```

Git repo: `srobinson/helioy-plugins` — 3 commits pushed.
