---
title: Claude Code --agents CLI Flag Behavior and Agent Priority Model
type: research
tags: [claude-code, cli, agents, subagents, plugins]
summary: --agents defines session-scoped agents with highest priority (1); plugin agents have lowest priority (4); all sources are ADDITIVE with per-name overrides, not wholesale replacement
status: active
source: quick-research
confidence: high
created: 2026-03-17
updated: 2026-03-17
---

## Summary

`--agents` does NOT replace plugin-defined or filesystem-defined agents. It sits at the **top of a priority stack**, and all sources are loaded additively. When two sources define an agent with the same name, the higher-priority source wins for that name only. Every other uniquely-named agent from every source is still available.

## Details

### Priority Stack (highest to lowest)

| Priority | Source | Scope |
|----------|--------|-------|
| 1 (highest) | `--agents` CLI flag | Current session only |
| 2 | `.claude/agents/` | Current project |
| 3 | `~/.claude/agents/` | All projects (user-level) |
| 4 (lowest) | Plugin's `agents/` directory | Where plugin is enabled |

Source: [Sub-agents docs](https://code.claude.com/docs/en/sub-agents#choose-the-subagent-scope)

### Answers to the specific questions

**1. Does `--agents` override/bypass plugin-defined agent files?**

No. It does not bypass or suppress plugin agents. Plugin agents remain loaded. If `--agents` defines an agent with the same name as a plugin agent, the `--agents` version wins for that name. All other plugin agents remain available.

**2. Does `--agents` ADD to existing agents, or REPLACE them entirely?**

ADD. All sources are loaded. The priority only matters for name collisions. There is no mechanism to wholesale replace the entire agent set with `--agents`.

**3. If plugins define agents and you also pass `--agents`, what happens?**

Both sets are loaded. CLI-defined agents shadow same-name plugin agents. All other agents from all sources remain active. The `/agents` command (interactive) and `claude agents` (CLI listing) show all agents grouped by source and mark which are overridden.

**4. Can `--agents` be used to have ZERO filesystem-based agents but still define session-scoped ones?**

Not directly via `--agents` alone. The flag adds agents; it does not suppress others. To suppress filesystem agents you would need an orthogonal mechanism (e.g., `--disallowedTools "Agent(agent-name)"` per agent, or `permissions.deny` in settings). There is no single flag to load only CLI-defined agents and ignore all file/plugin sources.

### `--agents` JSON format

```bash
claude --agents '{
  "code-reviewer": {
    "description": "Expert code reviewer. Use proactively after code changes.",
    "prompt": "You are a senior code reviewer.",
    "tools": ["Read", "Grep", "Glob", "Bash"],
    "model": "sonnet"
  }
}'
```

The `prompt` field is the equivalent of the markdown body in file-based agents. All frontmatter fields are supported: `description`, `prompt`, `tools`, `disallowedTools`, `model`, `permissionMode`, `mcpServers`, `hooks`, `maxTurns`, `skills`, `memory`.

### Relevant constraint: plugin agent security restrictions

Plugin agents (priority 4) cannot use `hooks`, `mcpServers`, or `permissionMode` frontmatter fields. These are silently ignored for security. CLI-defined agents (`--agents`) do NOT have this restriction -- they support all fields including `hooks`, `mcpServers`, and `permissionMode`.

### Known bug (as of 2026-03-17)

GitHub issue #35253: Plugin-namespaced agents (`plugin-name:agent-name`) do not inject their definition when spawned as **teammates** (agent teams). They work correctly as subagents. Affects Claude Code v2.1.69+. Non-plugin `.claude/agents/` definitions work for teammates.

## Sources

- CLI reference: https://code.claude.com/docs/en/cli-reference (--agents flag definition)
- Sub-agents full docs: https://code.claude.com/docs/en/sub-agents (priority table, format, all fields)
- GitHub issue #35253: https://github.com/anthropics/claude-code/issues/35253 (plugin teammate bug)

## Open Questions

- Is there a supported way to disable ALL filesystem and plugin agents for a session while still using `--agents`? The docs do not describe such a flag. `--strict-mcp-config` has an analogue for MCP servers but nothing equivalent exists for agents.
- Does `--plugin-dir` interact with the agent priority stack (does it push a new priority level or merge into priority 4)?
