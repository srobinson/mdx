---
title: Subagent MCP Tool Inheritance — Tested Reality
type: reference
tags: [claude-code, subagents, mcp, tools, claude-p, task-tool]
summary: Hands-on testing (Feb 2026) shows subagents DO inherit MCP tools (foreground AND background). claude -p also gets plugin MCP. Known bugs exist for custom subagents.
status: active
created: 2026-02-21
updated: 2026-02-21
project: helioy
confidence: verified-by-testing
---

# Subagent MCP Tool Inheritance

## Verified by Testing (Feb 2026)

We ran systematic tests across all vectors. Results below are from actual tool calls,
not documentation or GitHub issues.

### Test Results — Helioy Setup

| Vector                                | am                  | fmm     | mdx     | linear              |
| ------------------------------------- | ------------------- | ------- | ------- | ------------------- |
| Subagent foreground (general-purpose) | **YES**             | -       | -       | **YES**             |
| Subagent background (general-purpose) | **YES**             | -       | -       | -                   |
| `claude -p` (plugin MCP)              | **YES** (after fix) | **YES** | **YES** | **YES** (after fix) |

**Key finding: Background subagents DO get MCP tools.** This contradicts some GitHub
issue claims. Our background subagent called `mcp__am__am_stats` successfully in 33ms.

### What the Docs Say

Claude Code docs state subagents inherit all tools including MCP. Our testing confirms
this is true for **built-in subagent types** (general-purpose, Explore, Plan, etc.)
in both foreground and background modes.

### Known Bugs (Not Affecting Us)

These GitHub issues describe real bugs, but they affect custom subagent configurations
we don't use:

| Issue  | What's Broken                                      | Affects Helioy?                 |
| ------ | -------------------------------------------------- | ------------------------------- |
| #7296  | Task-tool agents don't inherit user-scoped MCP     | No — we use plugin MCP          |
| #13605 | Custom plugin subagents don't get MCP              | No — we use built-in types      |
| #13898 | Custom `.claude/agents/` hallucinate MCP calls     | No — we don't use custom agents |
| #14496 | Complex prompts cause non-deterministic MCP access | Maybe — monitor                 |
| #19964 | Docs contradict themselves re: background MCP      | Docs wrong — background works   |

## `claude -p` MCP Access

`claude -p` sessions load plugin MCP servers. Two issues we hit and fixed:

### 1. `am` Binary Collision (FIXED)

The `attention-matters` npm package exposes binary `am`, which collides with the
existing npm package `am` (v1.1.0). Using `npx -y attention-matters serve` fails
silently — npx resolves the wrong binary.

**Fix**: Use the cargo-installed binary directly:

```json
{ "command": "am", "args": ["serve"] }
```

Instead of:

```json
{ "command": "npx", "args": ["-y", "attention-matters", "serve"] }
```

### 2. `linear-server` Missing from Plugin (FIXED)

Linear MCP was configured in `~/.claude.json` (nuked), not in the plugin's `.mcp.json`.
`claude -p` sessions only see plugin-configured MCP servers.

**Fix**: Added to plugin `.mcp.json`:

```json
{ "type": "http", "url": "https://mcp.linear.app/mcp" }
```

Requires one-time OAuth authentication per session.

### 3. Tool Naming in `claude -p`

Plugin MCP tools get a different prefix in `claude -p`:

- This session: `mcp__am__am_stats`, `mcp__linear-server__list_teams`
- `claude -p`: `mcp__plugin_helioy-tools_am__am_stats`, `mcp__plugin_helioy-tools_fmm__fmm_lookup_export`

### 4. Permissions in `claude -p`

MCP tools are **visible** but **permission-blocked** in `claude -p` without
`--dangerously-skip-permissions`. Each tool call needs approval or pre-authorization.

## CLAUDECODE Environment Variable

Claude Code sets `CLAUDECODE=1` at startup. All child processes inherit it.
Since v2.1.41, launching `claude` when this var is set exits with an error:

> Error: Claude Code cannot be launched inside another Claude Code session.

**Technical cause**: Nested sessions share global config (OIDC auth tokens in
`~/.claude/`). Two instances race on token refresh, causing "Request aborted" / 525
errors. Nested `claude -p` hangs ~50-60% when inheriting the env var.

**Workaround for orchestrators**: Strip env vars before spawning workers:

```bash
unset CLAUDECODE CLAUDE_CODE_ENTRYPOINT
```

Workers from clean shells succeed 10/10.

**nancyr**: Spawns independent processes, not nested sessions. Should strip these
vars in the worker launch script.

## Plugin Cache

**Critical**: Changes to plugin source `.mcp.json` do NOT auto-propagate to the cache.
Must manually copy to `~/.claude/plugins/cache/<marketplace>/<plugin>/<version>/`.

## Impact on Helioy Architecture

### nancyr Workers

Independent processes with their own `~/.claude/` dirs. Not affected by subagent bugs.
Must strip `CLAUDECODE` env var when spawning.

### Research Skill (me:research / helioy:research)

Spawns `general-purpose` subagents. MCP tools work in both foreground and background.
No restrictions needed.

### Session Retrospective (ALP-655)

PreCompact hook can use subagents with MCP tools. No foreground-only restriction.
