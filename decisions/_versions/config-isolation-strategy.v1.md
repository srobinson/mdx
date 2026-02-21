---
title: Configuration Isolation Strategy
type: decisions
tags: [nancyr, claude-config, mcp, skills, isolation, open-source, plugin]
summary: CLAUDE_CONFIG_DIR for nancyr agent isolation, Helioy plugin for user-local — two modes, one ecosystem
status: active
created: 2026-02-20
updated: 2026-02-20
project: helioy
confidence: high
---

# Configuration Isolation Strategy

## Decision

Two modes, two mechanisms:

| Mode | Mechanism | Who controls config |
|------|-----------|-------------------|
| **nancyr runtime** | `CLAUDE_CONFIG_DIR` per agent | nancyr compiles and owns it |
| **user-local** | Helioy plugin via marketplace | User installs once, transparent |

## Research Findings

### CLAUDE_CONFIG_DIR

- **All-or-nothing** — replaces `~/.claude/` entirely. NO inheritance.
- Multi-scope settings still layer: managed > local > project > user. CLAUDE_CONFIG_DIR only moves WHERE the user scope lives.
- Empty dir = clean slate. Claude bootstraps gracefully.
- `.claude.json` path asymmetry: without the var it lives at `~/.claude.json` (outside `~/.claude/`). With it, moves INSIDE the config dir.
- **Known leaks**: IDE lock files hardcoded to `~/.claude/ide/`, macOS Keychain not namespaced, `~/.local/state/claude/` not redirected.
- **Agent Teams DON'T inherit** CLAUDE_CONFIG_DIR from parent (bug #23676). nancyr spawns via `claude -p`, not Agent Teams, so this doesn't affect us.

### Plugin System (shipped Jan 2026)

Plugins bundle skills + MCP servers + hooks + commands + agents into one installable unit.

```
helioy-plugin/
  .claude-plugin/
    plugin.json           # Manifest
  skills/
    helioy:knowledge-base/
      SKILL.md
    helioy:research/
      SKILL.md
  servers/
    mdcontext-server      # Bundled MCP server
```

- Marketplace is decentralized — Git repo with `marketplace.json`
- Team distribution via `.claude/settings.json` `extraKnownMarketplaces`
- `${CLAUDE_PLUGIN_ROOT}` for path references inside installed plugins
- Precedence: Plugin > Project > Personal for skills

## Mode 1: nancyr Runtime

```
CLAUDE_CONFIG_DIR=/tmp/nancyr/agents/<agent-id>/ claude -p "task"
```

nancyr compiles a complete config directory per agent:

```
/tmp/nancyr/agents/<agent-id>/
├── .claude.json          # MCP servers for this agent's needs
├── settings.json         # Model, permissions, allowed tools
├── CLAUDE.md             # 6-layer compiled prompt
├── skills/               # Agent archetype skills only
│   └── researcher/SKILL.md
└── hooks/                # Nancy's nervous system
```

No inheritance needed. nancyr has a config template per archetype (researcher, coder, reviewer) and stamps out per-agent dirs. Fast — just file copies + CLAUDE.md compilation.

### What nancyr controls per agent

| Component | How nancyr configures it |
|-----------|------------------------|
| Model | `settings.json` — cheap model for researchers, capable model for coders |
| Permissions | `settings.json` — restrict destructive commands per archetype |
| MCP servers | `.claude.json` — only servers this agent needs (am, mdcontext, fmm) |
| Skills | `skills/` — archetype-specific skills |
| Hooks | `settings.json` hooks — inbox check on PreToolUse, heartbeat on PostToolUse |
| Prompt | `CLAUDE.md` — compiled 6-layer prompt (role, task, context, state, constraints, comms) |
| Logs | Captured from stdout/stderr, owned by nancyr |

## Mode 2: User-Local (Helioy Plugin)

For personal dev use outside nancyr. Single install:

```bash
/plugin marketplace add helioy/claude-plugins
/plugin install helioy-tools@helioy
```

The plugin provides:
- **Skills**: helioy:knowledge-base, helioy:research, helioy:skill-creator
- **MCP servers**: mdcontext (pointing at ~/.mdx), optionally am
- **Hooks**: Session-start memory recall, session-end buffer flush

User's existing `~/.claude.json` stays untouched. Plugin MCP servers merge alongside user's existing servers.

## Answered Questions

1. **Composability**: No inheritance — nancyr compiles self-contained config dirs. This is simpler and more reliable than trying to layer.

2. **Skill distribution**: Helioy plugin for user-local. Direct file copy into CLAUDE_CONFIG_DIR for nancyr agents.

3. **MCP server lifecycle**: In nancyr mode, each `claude -p` process starts its own MCP servers (stdio). In user-local mode, Claude Code manages them. No sharing needed — stdio servers are per-process.

4. **Config layering**: All-or-nothing. nancyr builds complete configs. No layering.

5. **mdcontext for ~/.mdx**: Bundled in Helioy plugin for user-local. Compiled into agent .claude.json for nancyr mode.

## Known Gotchas

- `.claude.json` path moves inside CLAUDE_CONFIG_DIR (asymmetry with default behavior)
- macOS Keychain collisions if multiple instances use different OAuth accounts
- Plugin cache copied to `~/.claude/plugins/cache` — plugins don't install into CLAUDE_CONFIG_DIR
- `${CLAUDE_PLUGIN_ROOT}` needed for all path references in plugin configs

## Next Steps

- Create `helioy/claude-plugins` repo with marketplace.json
- Build Helioy plugin packaging (skills + mdcontext MCP server)
- Build nancyr config template compiler (per-archetype dirs)
- Add mdcontext as MCP server to user-local setup (immediate, unblocks knowledge-base skill)
