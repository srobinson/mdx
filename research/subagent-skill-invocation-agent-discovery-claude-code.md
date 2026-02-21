---
title: Subagent Skill Invocation and Agent Type Discovery in Claude Code
type: research
tags: [claude-code, subagents, skills, agent-discovery, warroom, helioy]
summary: Subagents spawned via the Agent tool cannot invoke the Skill tool. There is no programmatic API for listing agent types. The correct runtime discovery approach is to read the filesystem directly from ~/.claude/plugins/installed_plugins.json and the agents/ directories in each plugin's installPath.
status: active
source: quick-research
confidence: high
created: 2026-03-15
updated: 2026-03-15
---

## Summary

1. **Subagents cannot invoke the Skill tool** — it is a top-level UI construct, unavailable inside Agent-spawned subagents.
2. **No programmatic API for listing agent types** — there is no MCP endpoint, no Claude Code CLI flag, and no settings key that enumerates registered agents. The `/agents` dialog is purely UI-side.
3. **Agent discovery is filesystem-based** — two files give you everything needed to enumerate all registered agents at runtime: `~/.claude/plugins/installed_plugins.json` and the `agents/*.md` files under each plugin's `installPath`.
4. **Agents can read their own definition files** — nothing prevents a Bash tool call from reading `~/.claude/plugins/cache/{plugin}/{name}/{version}/agents/*.md`.

---

## Details

### Q1: Can a subagent invoke the Skill tool?

No. The Skill tool (`GD` in the minified Claude Code bundle, version 2.1.76) is a conversational construct that expands a slash command into a prompt and re-enters the main conversation loop. Subagents run in isolated contexts via `lL()` / `nL()` (the internal agent executor) and do not have access to the main loop's slash command dispatch. The bundle includes `--disable-slash-commands` as a recognized flag and the Skill tool's `isEnabled()` check specifically gates it out of non-interactive and agent sessions.

Evidence from the bundle: the Agent tool's call path explicitly builds a tool list via `D_ = C__(z_, W.mcp.tools)` which filters tools through permission rules — and skills are prompt-type tools that are never included in the subagent tool list.

### Q2: Is there a programmatic way to list available agent types?

No. The `/agents` dialog is purely client-side UI. There is no MCP endpoint, API route, or CLI command that returns the agent registry.

What Claude Code does internally (from `V2` module in the bundle):
1. Reads `CLAUDE.md`-adjacent settings files for `agents:` keys (`userSettings`, `projectSettings`, `localSettings`, `flagSettings`, `policySettings`)
2. Calls `cd_()` (lazy-cached) which reads all enabled plugins' `agents/` directories
3. Merges them via `oh()` (getActiveAgentsFromList), with later-priority sources overriding earlier ones

The merge priority order is: `built-in` < `plugin` < `userSettings` < `projectSettings` < `flagSettings` < `policySettings`

The Agent tool's error message when an unknown `subagent_type` is passed reads:
```
Agent type '{X}' not found. Available agents: {s.map(i => i.agentType).join(", ")}
```
This list is derived from `activeAgents` on the live `agentDefinitions` object — but it is never exposed as a tool result.

### Q3: How to enumerate agents at runtime (the correct approach)

Two steps:

**Step 1 — get all plugin install paths:**
```bash
cat ~/.claude/plugins/installed_plugins.json | python3 -c "
import json, sys
data = json.load(sys.stdin)
for name, versions in data.get('plugins', {}).items():
    for v in versions:
        print(v.get('installPath', ''))
"
```

**Step 2 — collect all agent .md files from those paths:**
```bash
find <installPath>/agents -name "*.md" 2>/dev/null
```

Each `.md` file has YAML frontmatter with these fields:
```yaml
name: <agent-type-slug>          # used as subagent_type value
description: <whenToUse text>    # shown in /agents dialog
model: sonnet|opus|haiku|inherit
color: <optional>
memory: user|project|local
mcpServers: [list]
hooks: { SubagentStop: [...] }
```

The `name` field in frontmatter is exactly the string passed to `subagent_type` in the Agent tool.

**Complete one-liner to enumerate all registered agent types:**
```bash
python3 -c "
import json, os, subprocess
with open(os.path.expanduser('~/.claude/plugins/installed_plugins.json')) as f:
    data = json.load(f)
import re
for name, versions in data.get('plugins', {}).items():
    for v in versions:
        agents_dir = v.get('installPath', '') + '/agents'
        if os.path.isdir(agents_dir):
            for fname in os.listdir(agents_dir):
                if fname.endswith('.md'):
                    fpath = os.path.join(agents_dir, fname)
                    with open(fpath) as af:
                        content = af.read()
                    m = re.search(r'^name:\s*(.+)$', content, re.MULTILINE)
                    d = re.search(r'^description:\s*[\">\|]?\s*(.+?)[\"\n]', content, re.MULTILINE)
                    if m:
                        print(f'{m.group(1).strip()}: {d.group(1).strip() if d else \"\"}')
"
```

### Q4: Can agents read their own definition files?

Yes — straightforwardly. The Bash tool has no restriction on reading `~/.claude/plugins/cache/`. A subagent (or the warroom skill running as the main agent) can issue:
```bash
cat ~/.claude/plugins/cache/helioy/helioy-tools/0.1.0/agents/rust-engineer.md
```

This is not a workaround — it is the intended mechanism since there is no higher-level API.

---

## Application to the Warroom Skill

The current warroom skill hardcodes agent roles (engineer, architect, reviewer). To make it runtime-discoverable:

1. At warroom invocation, run the enumeration script above via Bash.
2. Parse each agent's `name` and `description` fields.
3. Present the list to the user or use the descriptions to match roles to the task at hand.

The warroom skill already has access to Bash (it runs via the main conversation, not inside a subagent), so this is straightforward to add.

A lightweight version — just list what's available from the helioy plugin:
```bash
ls ~/.claude/plugins/cache/helioy/helioy-tools/0.1.0/agents/ | sed 's/\.md$//'
```

Current helioy agents: `codebase-analyst`, `code-reviewer`, `orchestrator`, `research-synthesizer`, `ux-designer`, `github-researcher`, `ux-researcher`, `project-planner`, `deep-research`, `frontend-engineer`, `visual-designer`, `coordinator`, `clinical-reviewer`, `rust-engineer`, `quick-research`, `backend-engineer`, `mobile-engineer`.

---

## Sources

- Claude Code binary `~/.local/share/claude/versions/2.1.76` (minified JS, inspected via `strings`)
- `~/.claude/plugins/installed_plugins.json`
- `~/.claude/plugins/cache/helioy/helioy-tools/0.1.0/agents/*.md`
- `~/.claude/plugins/cache/helioy/helioy-bus/0.1.0/skills/warroom/SKILL.md`

Key bundle symbols identified:
- `cd_` — lazy-cached async function that loads all plugin agents from `agents/` directories
- `oh` (`getActiveAgentsFromList`) — deduplicates agents by agentType with priority ordering
- `NW_` — the Agent tool definition with its `prompt()` method that builds the subagent_type listing
- `P47` — generates the agent listing text for the Agent tool's system prompt
- `GD` — the Skill tool constant name

---

## Open Questions

- Is there a settings-layer mechanism (e.g., `agents:` in `~/.claude/settings.json`) that would allow injecting agent definitions without a plugin? The bundle parses `userSettings` and `projectSettings` agent definitions via `LoR` (a zod record schema). This warrants further investigation for lightweight agent registration.
- The `allowedAgentTypes` field on `agentDefinitions` can restrict which agents are spawnable in a given context. Its source and configurability are unclear.
