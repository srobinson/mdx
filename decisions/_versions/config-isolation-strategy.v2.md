---
title: Configuration Isolation Strategy
type: decisions
tags: [nancyr, claude-config, mcp, skills, isolation, open-source, plugin]
summary: Single Helioy plugin serves both local dev and nancyr — plugin = capabilities, worktree = constraints, prompt = instructions
status: active
created: 2026-02-20
updated: 2026-02-20
project: helioy
confidence: high
supersedes: config-isolation-strategy.v1
---

# Configuration Isolation Strategy

## Decision

One plugin, both modes. The Helioy plugin installs globally and serves local dev AND nancyr agents.

```
Plugin (global)     = WHAT tools exist     (skills + MCP servers)
Worktree config     = WHAT agent is allowed (permissions, hooks, model)
Compiled CLAUDE.md  = WHAT agent should do  (prompt)
```

`CLAUDE_CONFIG_DIR` is an optional security boundary for true sandboxing — NOT the default mechanism.

## Why One Plugin Works

When nancyr spawns `claude -p` in a git worktree, the agent sees:
- **Global config** — user's installed plugins, MCP servers, skills
- **Project config** — `.claude/settings.json` and `.mcp.json` in the worktree
- **Prompt** — compiled via `-p` flag or worktree's `CLAUDE.md`

nancyr controls agents by writing project-level config INTO each worktree:

| What nancyr controls | How |
|---------------------|-----|
| Permissions | `.claude/settings.json` in worktree |
| Hooks (inbox check, heartbeat) | `.claude/settings.json` hooks |
| Model selection | `.claude/settings.json` model |
| Extra MCP servers | `.mcp.json` in worktree |
| Instructions | `.claude/CLAUDE.md` (compiled 6-layer prompt) |

The plugin provides capabilities. The worktree provides constraints. No config duplication needed.

### When CLAUDE_CONFIG_DIR IS needed

Only for true sandboxing: agent must NOT see the user's other tools (e.g., preventing a research agent from accessing Linear, or running untrusted agent code). This is an opt-in security boundary, not the default.

## The Helioy Plugin

### What it bundles

**MCP Servers:**
- `am` — attention-matters memory engine (`npx attention-matters serve`)
- `fmm` — code structural intelligence (`fmm mcp`)
- `mdcontext` — markdown hybrid search (pointing at `~/.mdx`)

**Skills:**
- `memory` — session lifecycle, AM integration
- `fmm` — sidecar navigation protocol
- `fmm-navigate` — MCP-first code navigation (currently duplicated in 3 repos)
- `helioy:knowledge-base` — ~/.mdx management
- `linear-workflow` — Linear issue conventions
- `nancy/orchestrator` — worker supervision
- `nancy/send-message` — orchestrator comms
- `nancy/update-spec` — spec tracking
- `nancy/session-history` — git log access
- `check-directives` — Nancy inbox protocol
- `create-spec` — requirements elicitation

**Hooks:**
- SessionStart — am_query memory recall
- Stop — am_buffer session persistence check

### What stays in user config (NOT in plugin)

- `context7` — third-party
- `exa` — third-party
- `linear-server` — third-party (though linear-workflow skill references it)
- `mcp-files` — third-party
- Symlinked skills from `~/.agents/skills/` — third-party

## Migration Plan

### Phase 1: Audit cleanup (before plugin)

1. Remove duplicate SessionStart hook (exists in BOTH settings.json AND .claude.json)
2. Remove duplicate PreToolUse check-directives hook
3. Consolidate linear-server registration (currently npx mcp-remote AND native HTTP)
4. Remove fmm-navigate copies from individual repo `.claude/` dirs (plugin will provide it)

### Phase 2: Build plugin

1. Create `helioy/claude-plugins` repo with `marketplace.json`
2. Package all Helioy skills + MCP configs + hooks into plugin structure
3. WIP `am-memory` plugin at `attention-matters/plugin/` is the starting point
4. Expand to include fmm, mdcontext, all skills

### Phase 3: Install and verify

1. Install Helioy plugin via marketplace
2. Remove manual skill copies from `~/.claude/skills/`
3. Remove manual MCP configs from `~/.claude.json`
4. Remove manual hooks from `~/.claude.json` and `settings.json`
5. Verify: local dev works, nancyr agents work

### Phase 4: nancyr worktree templates

1. Build per-archetype worktree config templates (researcher, coder, reviewer)
2. Each template = `.claude/settings.json` + `.claude/CLAUDE.md` + optional `.mcp.json`
3. nancyr stamps these into worktrees before spawning agents

## Known Issues

- `am` MCP server currently uses local binary path — needs npm publish of `attention-matters`
- Plugin cache lives at `~/.claude/plugins/cache` — may not follow CLAUDE_CONFIG_DIR (needs verification)
- macOS Keychain not namespaced per config dir (relevant only if using CLAUDE_CONFIG_DIR)
- `.claude.json` path asymmetry when CLAUDE_CONFIG_DIR is set
