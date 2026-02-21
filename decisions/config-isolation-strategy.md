---
title: Configuration Isolation Strategy
type: decisions
tags: [nancyr, claude-config, mcp, skills, isolation, open-source, plugin]
summary: CLAUDE_CONFIG_DIR per agent with Helioy plugin installed per agent space — universal plugin, per-agent isolation
status: active
created: 2026-02-20
updated: 2026-02-20
project: helioy
confidence: high
---

# Configuration Isolation Strategy

## Decision

**CLAUDE_CONFIG_DIR per agent.** Each nancyr agent gets its own config space. The Helioy plugin is the universal distribution mechanism — installed into each agent's config dir. Same plugin, same capabilities, per-agent isolation.

```
CLAUDE_CONFIG_DIR={agent_space_dir} claude -p "..."
```

For local dev (outside nancyr): same plugin, installed into user's `~/.claude/`.

### Why per-agent config dirs

- Each agent has its own CLAUDE.md optimized for its role/profile
- Hooks, permissions, model selection are per-agent
- Plugin installed per agent allows future customization (KISS for now)
- Clean isolation — agents don't see each other's state
- Logs, session data, todos all scoped to the agent

### The Helioy plugin

One plugin, universal. Installed into each agent's `CLAUDE_CONFIG_DIR` and into user's `~/.claude/` for local dev. Contains all Helioy capabilities:

**MCP Servers:**

- `am` — attention-matters memory engine (`npx attention-matters serve`)
- `fmm` — code structural intelligence (`npx frontmatter-matters serve`)
- `mdcontext` — markdown hybrid search (`npx mdcontext serve`)

**Skills:**

- `memory` — session lifecycle, AM integration
- `fmm` / `fmm-navigate` — sidecar navigation
- `helioy:knowledge-base` — ~/.mdx management
- `linear-workflow` — Linear issue conventions
- `nancy/*` — orchestrator, send-message, update-spec, session-history
- `check-directives` — Nancy inbox protocol
- `create-spec` — requirements elicitation

**Hooks:**

- SessionStart — am_query memory recall
- Stop — am_buffer session persistence check

### npm packaging for Rust projects

All open source Rust projects MUST be packaged via npm for easy distribution. This is critical when MCP is involved — `npx` one-liners are the standard distribution pattern for MCP servers.

| Rust project      | npm package           | MCP command                     |
| ----------------- | --------------------- | ------------------------------- |
| attention-matters | `attention-matters`   | `npx attention-matters serve`   |
| fmm               | `frontmatter-matters` | `npx frontmatter-matters serve` |

mdcontext is already TypeScript/npm native.

Pattern: Rust binary compiled per platform, published to npm with postinstall download from GitHub Releases. Same mechanism used by both projects — JS wrapper at `bin/`, native binary downloaded to `scripts/` by postinstall. Release-please automates versioning + CI builds for 4 targets (macOS arm64/x64, Linux arm64/x64). fmm also supports Windows x64.

### nancyr agent lifecycle

```
1. nancyr creates agent space dir
2. nancyr installs Helioy plugin into agent's CLAUDE_CONFIG_DIR
3. nancyr writes compiled CLAUDE.md (6-layer, role-optimized)
4. nancyr writes settings.json (permissions, hooks, model)
5. nancyr spawns: CLAUDE_CONFIG_DIR={dir} claude -p "task"
6. Agent runs with full Helioy capabilities, scoped isolation
7. On completion: nancyr archives agent space (logs, session, output)
```

### Local dev (outside nancyr)

Same plugin, installed once via marketplace:

```bash
/plugin marketplace add helioy/claude-plugins
/plugin install helioy-tools@helioy
```

User gets all Helioy skills + MCP servers. Their `~/.claude.json` stays untouched — plugin MCP servers merge alongside existing user servers.

## Migration Plan

### Phase 1: Cleanup existing config

1. Remove duplicate SessionStart hook (in both settings.json AND .claude.json)
2. Remove duplicate PreToolUse check-directives hook
3. Consolidate linear-server (currently registered twice)
4. Remove fmm-navigate copies from 3 individual repo `.claude/` dirs

### Phase 2: npm packaging

1. ~~Publish `attention-matters` to npm~~ — DONE (v0.1.3, postinstall download bug fixed)
2. ~~Publish `frontmatter-matters` to npm~~ — DONE (v0.1.2, working)
3. Verify `mdcontext` npm package has MCP serve command

### Phase 3: Build plugin

1. Create `helioy/claude-plugins` repo with `marketplace.json`
2. Expand WIP `am-memory` plugin to full Helioy plugin
3. Bundle all skills, MCP configs, hooks

### Phase 4: Install and verify

1. Install Helioy plugin in local dev
2. Remove all manual Helioy config from `~/.claude/skills/`, `~/.claude.json`, `settings.json`
3. Verify local dev works
4. Test nancyr agent spawn with plugin in CLAUDE_CONFIG_DIR
5. Verify agent isolation

## Version History

- v1: Two modes, two mechanisms (CLAUDE_CONFIG_DIR + user plugin)
- v2: One plugin globally, worktree constraints (WRONG — removed CLAUDE_CONFIG_DIR)
- v3: (current) CLAUDE_CONFIG_DIR per agent + universal plugin installed per agent space
