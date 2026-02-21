---
title: mcpServers YAML Frontmatter Syntax in Claude Code Agent Definition Files
type: research
tags: [claude-code, agents, subagents, mcp, yaml, frontmatter]
summary: mcpServers in agent .md frontmatter takes a YAML sequence of server name strings (referencing already-configured servers) or inline map entries. The list-of-strings syntax is valid and correct.
status: active
source: quick-research
confidence: high
created: 2026-03-09
updated: 2026-03-09
---

## Summary

The `mcpServers:` YAML frontmatter syntax used in agent definition files is **valid and correct** per the official Claude Code documentation. A list of strings where each string is a server name referencing an already-configured MCP server is the documented pattern.

```yaml
mcpServers:
  - linear-server
```

This is correct YAML. The issue with a worker agent not seeing `linear-server` tools is **not** a syntax problem. It is a runtime availability problem.

---

## Details

### What the docs say

From `https://code.claude.com/docs/en/sub-agents` (the authoritative reference, accessed 2026-03-09):

> `mcpServers` — MCP servers available to this subagent. Each entry is either **a server name referencing an already-configured server** (e.g., `"slack"`) or an inline definition with the server name as key and a full MCP server config as value.

The field accepts two forms:

**Form 1: Reference to a pre-configured server (name as string)**
```yaml
mcpServers:
  - linear-server
  - github
```

**Form 2: Inline server definition (name as key, full config object as value)**
```yaml
mcpServers:
  my-server:
    type: http
    url: https://api.example.com/mcp
```

Both forms are supported. Mixing them in one list is documented as valid.

### The actual agent files in helioy-tools

The `mobile-engineer.md` and `frontend-engineer.md` agents at `/Users/alphab/Dev/LLM/DEV/helioy/helioy-plugins/plugins/helioy-tools/agents/` both use:

```yaml
mcpServers:
  - linear-server
```

This is syntactically correct.

### Why the worker agent might not see linear-server tools

The `mcpServers` field in agent frontmatter restricts or selects which of the **already-configured** servers are available to the subagent. If `linear-server` is not configured at the session level (i.e., not present in `~/.claude.json` or `.mcp.json`), the string reference resolves to nothing.

Possible root causes:

1. **`linear-server` is not configured in the active session's MCP settings.** The name must match exactly a server configured via `claude mcp add` or in `.mcp.json`. Run `claude mcp list` to verify.

2. **The plugin's `.mcp.json` does not define `linear-server`.** Plugin-bundled MCP servers are defined in the plugin's own `.mcp.json`. If `linear-server` is defined at user scope in `~/.claude.json` but the agent runs in a context where that config is not loaded (e.g., a headless or CI session), it won't be present.

3. **Subagents do not inherit MCP tools by default when `mcpServers` is specified.** When you list any `mcpServers` entries, you are creating an **explicit allowlist**. If the name does not resolve to a running server, no tools from that server appear. Without the `mcpServers` field, subagents inherit all tools from the parent conversation including MCP tools.

4. **Session start timing.** The docs note: "Subagents are loaded at session start. If you create a subagent by manually adding a file, restart your session." The same applies to MCP server availability — if the server was added after session start, it may not be visible.

### Verification steps

```bash
# Confirm linear-server is registered
claude mcp list

# Check which scope it's in
claude mcp get linear-server
```

If `linear-server` is not in the output, the agent will never see its tools regardless of correct frontmatter syntax.

### Alternative: let subagents inherit MCP tools

If you remove `mcpServers:` from the frontmatter entirely, the subagent inherits **all** tools available to the parent conversation, including all MCP tools. This is the zero-config path and works as long as the parent session has `linear-server` connected.

---

## Sources

- `https://code.claude.com/docs/en/sub-agents` — Supported frontmatter fields table and mcpServers description
- `https://code.claude.com/docs/en/mcp` — MCP server configuration format and scopes
- `/Users/alphab/Dev/LLM/DEV/helioy/helioy-plugins/plugins/helioy-tools/agents/mobile-engineer.md` — Actual agent file inspected
- `/Users/alphab/Dev/LLM/DEV/helioy/helioy-plugins/plugins/helioy-tools/agents/frontend-engineer.md` — Actual agent file inspected

---

## Open Questions

- Does the helioy-tools plugin's `.mcp.json` define `linear-server`, or does it rely on it being present at user scope? If the latter, headless/worker sessions may not have it unless they inherit from the same `~/.claude.json`.
- Is the worker agent being launched via `claude --agent` in a new shell that doesn't have the user's MCP config loaded?
