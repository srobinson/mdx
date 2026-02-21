---
title: CLAUDE_CONFIG_DIR Behavior Research
type: research
tags: [claude-code, config, isolation, nancyr, environment-variables]
summary: Comprehensive research on CLAUDE_CONFIG_DIR — what it controls, known leaks, gotchas, and patterns for agent isolation
status: active
created: 2026-02-20
updated: 2026-02-20
project: helioy
confidence: high
---

# CLAUDE_CONFIG_DIR Behavior

## What It Controls

When set, replaces `~/.claude/` as the user-scope directory. Everything inside moves:

| File/Directory      | Purpose                                          |
| ------------------- | ------------------------------------------------ |
| `.claude.json`      | Prefs, OAuth, MCP servers, project state, caches |
| `.credentials.json` | Stored credentials                               |
| `settings.json`     | User-scope settings                              |
| `CLAUDE.md`         | User-scope instructions                          |
| `agents/`           | Custom subagent definitions                      |
| `projects/`         | Per-project session data                         |
| `plans/`            | Plan files                                       |
| `skills/`           | User-scope skills                                |
| `shell-snapshots/`  | Shell state                                      |
| `statsig/`          | Telemetry                                        |
| `todos/`            | Task persistence                                 |
| `debug/`            | Logs                                             |

## What It Does NOT Control (Known Leaks)

| Item                          | Stays At                | Issue             |
| ----------------------------- | ----------------------- | ----------------- |
| Project-scope config          | `.claude/` in repo root | By design         |
| IDE lock files                | `~/.claude/ide/`        | Bug #4739, #12719 |
| macOS Keychain                | Shared service name     | Bug #20553        |
| `~/.local/state/claude/`      | Hardcoded               | Bug #15670        |
| Default `~/.claude/CLAUDE.md` | May still load          | Bug in v2.1.25    |

## No Inheritance

All-or-nothing replacement. Multi-scope settings still layer:

1. Managed (system paths) — cannot override
2. Command line args
3. Local (`.claude/settings.local.json`)
4. Project (`.claude/settings.json`)
5. User (`$CLAUDE_CONFIG_DIR/settings.json`)

CLAUDE_CONFIG_DIR only changes WHERE #5 lives.

## Empty Directory Behavior

Claude Code bootstraps gracefully. Creates all needed files on demand. User gets prompted to login. No MCP servers, hooks, or settings — clean slate.

## .claude.json Path Asymmetry

Without var: `~/.claude.json` (OUTSIDE `~/.claude/`)
With var: `$CLAUDE_CONFIG_DIR/.claude.json` (INSIDE the config dir)

If `CLAUDE_CONFIG_DIR=$HOME/.claude`, you get `~/.claude/.claude.json` not `~/.claude.json`.

## Multi-Instance Behavior

- Multiple instances CAN share a config dir (timestamped backups protect against contention)
- macOS Keychain collisions with different OAuth accounts
- Agent Teams DON'T inherit CLAUDE_CONFIG_DIR from parent (bug #23676)
- Recommended: per-agent CLAUDE_CONFIG_DIR with symlinks for shared elements

## MCP Server Scopes

| Scope   | Location                          | Affected by CLAUDE_CONFIG_DIR? |
| ------- | --------------------------------- | ------------------------------ |
| User    | `~/.claude.json` global section   | YES — moves with it            |
| Local   | `~/.claude.json` per-project keys | YES — moves with it            |
| Project | `.mcp.json` in repo root          | NO — stays in repo             |
| Managed | System paths                      | NO                             |

## Sources

- Official docs: code.claude.com/docs/en/settings (one sentence only)
- GitHub issues: #3833 (behavior unclear), #15670 (incomplete isolation), #20553 (Keychain collision), #23676 (Agent Teams), #4739 (IDE files)
