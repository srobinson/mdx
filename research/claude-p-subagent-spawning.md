---
title: Claude Code `claude -p` / `--print` Mode and Subagent Spawning
type: research
tags: [claude-code, subagents, headless, non-interactive, orchestration, agent-tool]
summary: In `claude -p` mode the Agent tool is fully available and subagents can be spawned; the architectural limit is that spawned subagents cannot themselves re-spawn — one level deep only.
status: active
source: quick-research
confidence: high
created: 2026-03-09
updated: 2026-03-09
---

## Summary

`claude -p` (alias `--print`) is Claude Code's non-interactive / headless / SDK-CLI mode. It does **not** restrict tool availability relative to interactive mode. The Agent tool works normally: a `claude -p` process **can** spawn subagents.

The hard architectural constraint is one level deep: **subagents cannot spawn other subagents**. This applies in all modes — interactive, `-p`, CI, and SDK.

---

## Details

### What `claude -p` actually is

The official docs now call this the "Agent SDK CLI." The old name "headless mode" was retired. The `-p` flag makes Claude run non-interactively, print the result, and exit. Every CLI flag works identically in `-p` mode unless explicitly noted otherwise.

From the CLI reference:

> `--print`, `-p` — Print response without interactive mode (see Agent SDK documentation for programmatic usage details)

Flags that are **`-p` only** (not available in interactive mode):
- `--output-format` (text / json / stream-json)
- `--max-turns`
- `--max-budget-usd`
- `--no-session-persistence`
- `--fallback-model`
- `--json-schema`
- `--include-partial-messages`

None of these restrict tools. They control output format and budget only.

### Does `--print` restrict the Agent tool?

No. The Agent tool (formerly "Task tool," renamed in v2.1.63) is not withheld in `-p` mode. To use it, `Agent` must appear in `--allowedTools`, the same requirement that applies interactively. Example:

```bash
claude -p "Review the auth and payment modules in parallel" \
  --allowedTools "Read,Grep,Glob,Agent"
```

The `--tools` flag can restrict which tools Claude receives. If you pass `--tools "Bash,Edit,Read"` and omit `Agent`, subagent spawning is unavailable — but that is an explicit opt-out by the caller, not a platform-level restriction.

### The one-level depth limit

The single confirmed architectural constraint: **subagents cannot spawn other subagents**.

This is stated explicitly in three separate places in the official docs:

1. Sub-agents page (Plan built-in subagent description):
   > "This prevents infinite nesting (subagents cannot spawn other subagents)"

2. Sub-agents page (note block):
   > "Subagents cannot spawn other subagents. If your workflow requires nested delegation, use Skills or chain subagents from the main conversation."

3. Agent SDK subagents page (note block):
   > "Subagents cannot spawn their own subagents. Don't include `Agent` in a subagent's `tools` array."

4. Sub-agents frontmatter docs:
   > "If `Agent` is omitted from the `tools` list entirely, the agent cannot spawn any subagents. This restriction only applies to agents running as the main thread with `claude --agent`. Subagents cannot spawn other subagents, so `Agent(agent_type)` has no effect in subagent definitions."

GitHub issue [#4182](https://github.com/anthropics/claude-code/issues/4182) ("Sub-Agent Task Tool Not Exposed When Launching Nested Agents") was closed as a duplicate in August 2025. The issue confirmed that the Task/Agent tool is not in a subagent's toolset, and the community explicitly flagged this as an intentional design decision to prevent infinite recursion.

### Implication for orchestrator architecture

The pattern "orchestrator spawns specialist background agents" works cleanly with `claude -p`:

```
claude -p "orchestrate this task" --allowedTools "...,Agent" --agents '{...}'
   └── spawns: frontend-engineer subagent   (reads/edits UI code)
   └── spawns: backend-engineer subagent    (reads/edits API code)
   └── spawns: test-runner subagent         (runs test suite)
```

What does NOT work:
- frontend-engineer subagent trying to spawn a css-specialist sub-subagent
- Any agent spawned as a subagent trying to further delegate via Agent tool

### The `claude -p` workaround for nested spawning

Some users work around the depth limit by having a subagent call `claude -p` through the Bash tool:

```bash
# Inside a subagent's Bash call:
claude -p "Do nested work" --allowedTools "Read,Edit" > /tmp/result.txt
```

The official docs and community (GH #4182) flag this as a poor pattern:
- No visibility from parent process into the nested call
- Errors buried in Bash output, not structured
- No shared context with parent
- Separate process with independent token budget and rate limits
- Data exchange via files/pipes instead of structured tool results

### `--permission-prompt-tool` for non-interactive permission handling

In `-p` mode there is no TTY for permission prompts. Two options:
1. `--dangerously-skip-permissions` — skips all checks (use with caution)
2. `--permission-prompt-tool mcp_tool_name` — delegates permission decisions to an MCP tool that your orchestrator controls

Subagents can also set `permissionMode: bypassPermissions` in their frontmatter to skip checks for that agent specifically.

### Background subagent support

Subagents support `background: true` in frontmatter to run concurrently while the parent continues. In `-p` mode, the process exits after the main agent finishes, so background subagents need to complete before that point. The docs note that `--print` mode had a prior bug where it would hang waiting on long-lived in-process teammate tasks — this was fixed (see changelog).

---

## Architecture recommendation

For an orchestrator spawning specialized agents (frontend-engineer, backend-engineer, etc.) as background processes:

**Option A: Single `claude -p` orchestrator with subagents** (recommended for most cases)
- Launch one `claude -p` with `--allowedTools "...,Agent"` and define specialists via `--agents` JSON or `.claude/agents/` files
- The orchestrator is the main thread; specialists are subagents (one level deep)
- Parallel execution works natively

**Option B: Multiple independent `claude -p` processes** (for true parallelism beyond one level)
- Shell script or external orchestrator launches N separate `claude -p` processes
- Each is a fully capable "main thread" that can itself spawn subagents
- Coordination via files, shared git state, or helioy-bus
- No depth limit; each process has its own agent hierarchy

Option B is the only way to get multi-level hierarchies today, and it is the pattern the helioy-bus and nancyr orchestrators are built for.

---

## Sources

- [Claude Code CLI reference](https://code.claude.com/docs/en/cli-reference) — `-p` flag definition, all flags table
- [Claude Code sub-agents documentation](https://code.claude.com/docs/en/sub-agents) — depth limit, Agent tool restrictions, background support
- [Run Claude Code programmatically (headless docs)](https://code.claude.com/docs/en/headless) — `-p` is now "Agent SDK CLI," tool availability
- [Agent SDK subagents guide](https://platform.claude.com/docs/en/agent-sdk/subagents) — programmatic subagent definition, Agent tool requirement
- [GitHub issue #4182 — Sub-Agent Task Tool Not Exposed When Launching Nested Agents](https://github.com/anthropics/claude-code/issues/4182) — community confirmation, workaround analysis, closed as duplicate Aug 2025
- [GitHub issue #1770 — Enable Parent-Child Agent Communication](https://github.com/anthropics/claude-code/issues/1770)
- [GitHub issue #7475 — Agent mode for forcing Claude Code to spawn subagent](https://github.com/anthropics/claude-code/issues/7475)

---

## Open Questions

- Whether a future release will lift the one-level depth limit with configurable depth guards (GH #4182 proposed depth limits as a safe solution; no public roadmap commitment found)
- Whether `background: true` subagents complete reliably before `claude -p` exits when the orchestrator itself finishes first
- Whether `--dangerously-skip-permissions` propagates automatically to spawned subagents or must be set per subagent via `permissionMode: bypassPermissions`
