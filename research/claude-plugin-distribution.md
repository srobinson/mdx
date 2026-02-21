---
title: Claude Code Plugin & Skill Distribution Patterns
type: research
tags: [claude-code, plugins, skills, mcp, distribution, marketplace]
summary: How skills, MCP servers, and plugins are distributed — marketplace system, npm, project config, and open-source patterns
status: active
created: 2026-02-20
updated: 2026-02-20
project: helioy
confidence: high
---

# Plugin & Skill Distribution Patterns

## Plugin System (shipped Jan 2026)

Plugins bundle skills + MCP servers + hooks + commands + agents into one installable unit.

```
my-plugin/
  .claude-plugin/
    plugin.json              # Manifest
  skills/
    review/SKILL.md          # Skills
  commands/
    deploy.md                # Slash commands
  agents/
    security-reviewer.md     # Subagents
  servers/
    db-server                # Bundled MCP server
```

### Marketplace System

Decentralized. Anyone hosts `marketplace.json` in a Git repo.

```bash
/plugin marketplace add owner/repo
/plugin install plugin-name@marketplace
/plugin marketplace update
```

Plugin sources: relative paths, GitHub repos, Git URLs, npm packages, pip packages.

### Team Distribution

```json
// .claude/settings.json (committed)
{
  "extraKnownMarketplaces": {
    "company-tools": {
      "source": { "source": "github", "repo": "your-org/claude-plugins" }
    }
  },
  "enabledPlugins": {
    "code-formatter@company-tools": true
  }
}
```

### Key Variable

`${CLAUDE_PLUGIN_ROOT}` — references installed plugin directory. Plugins copied to `~/.claude/plugins/cache`.

## Skill Distribution Methods

1. **Plugin marketplace** (official, recommended) — bundled in plugins
2. **npm package** — `@your-org/skill-name`, installs to `~/.claude/skills/` or `.claude/skills/`
3. **Git repo** — clone and copy SKILL.md
4. **Manual / symlinks** — direct file copy

### Skill Priority Order

1. Plugin (highest)
2. Project (`.claude/skills/`)
3. Personal (`~/.claude/skills/`)
4. Enterprise (managed settings)

## MCP Server Distribution

1. **npx one-liners** (most common): `claude mcp add server -- npx -y @package/name`
2. **Remote HTTP**: `claude mcp add --transport http name https://url/mcp`
3. **Docker** (enterprise): containerized with signatures and SBOMs
4. **Plugin-bundled**: `.mcp.json` or inline in `plugin.json`
5. **Project .mcp.json**: committed to git, shared with team

### MCP Server Scopes

| Scope           | Storage                      | Visibility                  |
| --------------- | ---------------------------- | --------------------------- |
| Local (default) | `~/.claude.json` per-project | You, current project        |
| Project         | `.mcp.json` in repo          | Team (committed)            |
| User            | `~/.claude.json` global      | You, all projects           |
| Managed         | System paths                 | All users, admin-controlled |

## Community Ecosystem

| Resource                            | Description                          |
| ----------------------------------- | ------------------------------------ |
| claude-plugins.dev                  | Community CLI + browse               |
| claudecodeplugins.io                | 313 plugins, 1336 skills             |
| skillsmp.com                        | 239k+ skills, open SKILL.md standard |
| anthropics/claude-code-plugins      | Official: 65k stars                  |
| jeremylongshore/claude-code-plugins | Community: 1.4k stars, 270+ plugins  |

## Key Insight

**Plugins are the answer for Helioy distribution.** A single `helioy/claude-plugins` repo with marketplace.json can distribute all Helioy skills + MCP server configs + hooks as one installable unit. Users run one command, get everything.
