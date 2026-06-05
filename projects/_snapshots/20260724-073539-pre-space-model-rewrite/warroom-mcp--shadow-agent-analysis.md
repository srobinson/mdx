---
title: Shadow Agent Eviction Coordinator - Architect Analysis
author: engineering-software-architect
date: 2026-03-17
topic: token-eviction-shadow-agent
tags: [architecture, helioy-bus, token-management, agent-lifecycle, shadow-agent]
---

# Shadow Agent Eviction Coordinator: Analysis

## Overall Assessment

The shadow agent design is architecturally sound and solves a real problem that my earlier Option C analysis underweighted: the behavioral contamination from any in-band wind-down directive. Even a single "context rotation scheduled" injection changes how the agent allocates its remaining tokens. The shadow agent eliminates that entirely.

The question is whether the complexity is justified. My answer: **yes, but scope it tightly to avoid building a general-purpose agent supervisor.**

## 1. Implementation Viability

### Spawn mechanism: Background tmux pane in a utility window

The shadow agent needs:
- Access to `tmux capture-pane` (requires tmux context)
- Access to the JSONL stream (filesystem read)
- Access to MCP tools (`cx_store`, `cx_deposit`, `warroom_remove`, `warroom_add`)
- No visibility to the target agent

The right vehicle is a **dedicated tmux pane in a hidden utility window**, not a subagent spawned via the Agent tool. Reasons:

1. **Agent tool subagents run inside the parent's context window.** Spawning a shadow agent via the Agent tool would consume the parent's tokens, which defeats the purpose. The parent here is the orchestrator, and its context is the most expensive resource in the system.

2. **A tmux pane with `claude --agent shadow-eviction-coordinator`** runs as an independent process with its own context window. It has access to all MCP servers configured for the project (including helioy-bus, context-matters). It costs haiku-rate tokens in its own budget.

3. **The utility window** should be a fixed, persistent window (e.g., `_eviction` or `_system`) that the orchestrator creates once per session. Shadow agents spawn as panes in this window. One pane per monitored agent.

Spawn flow:

```
orchestrator detects agent at 160k (via PreToolUse hook reporting)
  → calls warroom_add(name="_system", agent="shadow-eviction-coordinator")
     or spawns directly via tmux split-window into the utility window
  → sends bus message to shadow agent: "monitor {target_agent_id}, evict when ready"
  → shadow agent reads terminal buffer, waits for seam, executes eviction
  → shadow agent self-terminates after eviction complete
```

### Alternative: Pure bash script, no LLM

Consider whether the shadow agent needs to be an LLM at all. The two LLM-requiring tasks are:
1. **Seam detection** (is the agent idle or mid-work?)
2. **Handover synthesis** (summarize what the agent was doing)

Seam detection can be done heuristically (see section 2). Handover synthesis genuinely benefits from an LLM. So the LLM is justified, but only for the synthesis step. A hybrid approach:

```
bash script monitors token count via JSONL
  → at 160k, starts polling terminal buffer for seam heuristics
  → when seam detected (or hard ceiling hit), captures terminal buffer
  → spawns haiku agent with buffer as input: "write a handover brief"
  → haiku agent writes brief, calls cx_store, exits
  → bash script kills target pane, triggers respawn
```

This is simpler than a persistent shadow agent because the LLM portion is a single-shot synthesis task, not a monitoring loop. LLMs are poor monitors (they can't poll, they respond to prompts). A bash script with `tmux capture-pane` in a loop is a natural monitor.

**My recommendation: hybrid approach.** Bash for monitoring and seam detection. Haiku for handover synthesis. No persistent shadow LLM agent.

## 2. Seam Detection Heuristics

The terminal buffer reveals agent state through predictable patterns. Here's what to look for:

### High-confidence seams (safe to evict)

| Signal | How to detect | Confidence |
|--------|---------------|------------|
| Agent is idle at prompt | Last line matches the Claude Code prompt pattern (`❯` or similar). No tool call in progress. | Very high |
| Agent just committed | Recent output contains `git commit` success message or commit hash | High |
| Agent completed a tool call | Output contains tool result, followed by agent text, followed by prompt | High |
| Agent finished writing a file | Output contains "File written" or "File created" confirmation | High |

### Low-confidence seams (risky to evict)

| Signal | How to detect | Risk |
|--------|---------------|------|
| Agent is mid-edit | Output shows Edit tool invocation without completion confirmation | Data loss |
| Agent is mid-multi-step | Output contains "Now let me..." or "Next, I'll..." patterns | Incomplete work |
| Agent is waiting for tool response | Spinner visible, no output for N seconds but tool is running | Interrupted operation |

### Implementation

```bash
capture_buffer() {
    tmux capture-pane -t "$target" -p -S -500  # last 500 lines
}

is_idle() {
    local buffer="$1"
    local last_line=$(echo "$buffer" | tail -1)
    # Claude Code shows a prompt character when idle
    [[ "$last_line" =~ ^[[:space:]]*❯ ]] || [[ "$last_line" =~ ^[[:space:]]*\$ ]]
}

recently_committed() {
    local buffer="$1"
    echo "$buffer" | tail -20 | grep -qE '^\[.*[0-9a-f]{7}\]|^commit [0-9a-f]'
}

mid_tool_call() {
    local buffer="$1"
    # Look for tool invocation without completion
    local last_tool=$(echo "$buffer" | grep -n 'Tool:' | tail -1 | cut -d: -f1)
    local last_result=$(echo "$buffer" | grep -n 'Result:' | tail -1 | cut -d: -f1)
    [[ -n "$last_tool" && ( -z "$last_result" || "$last_tool" -gt "$last_result" ) ]]
}
```

The polling loop:

```bash
while true; do
    buffer=$(capture_buffer)
    if is_idle "$buffer" || recently_committed "$buffer"; then
        if ! mid_tool_call "$buffer"; then
            trigger_eviction "$buffer"
            break
        fi
    fi
    sleep 5  # poll every 5 seconds
done
```

### The JSONL stream as a structured signal

The terminal buffer is a rendering of what the user sees. The JSONL stream (if available via `HELIOY_SESSION_ID`) is the structured record of tool calls and responses. Parsing the last few JSONL entries gives a more reliable signal:

- Last entry is an `assistant` message with no pending tool call = idle
- Last entry is a `tool_result` = just finished a tool call, good seam
- Last entry is a `tool_use` = mid-tool-call, do not evict

If the JSONL stream is accessible, prefer it over terminal buffer parsing for seam detection. Use the terminal buffer for the handover synthesis (it has the full narrative).

## 3. Race Conditions

The window between "shadow decides to evict" and "pane killed" is small (milliseconds for a `tmux kill-pane`). But the concern is valid.

### Scenario: agent starts new tool call between decision and kill

The agent sends a tool call. The MCP server begins processing. The shadow kills the pane. The MCP server's stdio pipe breaks. In the bus server (Python), this manifests as a broken pipe exception on stdout. FastMCP should handle this gracefully (the connection drops, the server continues for other clients).

**Risk: low.** The broken pipe is a normal disconnection event. No data corruption. The tool call's side effects (file writes, git commits) may or may not have completed. This is the same risk as killing any process mid-operation.

### Do we need a lock?

No. A distributed lock between the shadow agent and the target agent would require the target agent to participate (check a lock before each action), which reintroduces behavioral contamination. The entire point of the shadow agent is that the target doesn't know it exists.

The pragmatic mitigation: the shadow agent checks seam status twice with a 2-second gap. If the agent is idle at both checks, evict. This reduces the probability of catching a transition from idle to active.

```bash
if is_idle "$buffer1"; then
    sleep 2
    buffer2=$(capture_buffer)
    if is_idle "$buffer2"; then
        trigger_eviction "$buffer2"
    fi
fi
```

### Scenario: target agent writes to a file, shadow kills mid-write

The Edit and Write tools in Claude Code are atomic from the agent's perspective (single tool call). If the tool call completed (file written), the work is saved. If the tool call was interrupted (kill arrived during execution), the file may be partially written. This is an existing risk with any process kill and isn't unique to the shadow agent.

Mitigation: the handover brief should note "last observed action was [X]" so the replacement agent can verify file state.

## 4. Hard Ceiling

**Yes, absolutely.** 170k hard kill-switch, no exceptions.

The shadow agent is a haiku-class process that could itself fail: crash, hang, enter a loop, produce bad seam detection, or simply take too long to synthesize a handover. The hard ceiling is the safety net for shadow agent failure.

The hierarchy:

| Threshold | Actor | Action |
|-----------|-------|--------|
| 160k | PreToolUse hook | Spawns shadow monitor (bash script) |
| 160k-170k | Shadow monitor | Polls for seam, triggers eviction when safe |
| 170k | PreToolUse hook | Hard kill regardless of shadow state. Also kills shadow if still running. |

The PreToolUse hook at 170k should:
1. Kill the target agent's pane
2. Kill the shadow monitor's pane (if still alive)
3. Trigger a fallback handover (mechanical JSONL parse, no LLM synthesis)
4. Respawn fresh agent with whatever handover data is available

This means the system degrades gracefully:
- Best case: shadow finds a seam, produces rich handover at ~162k
- Degraded case: shadow can't find a seam, hard ceiling fires at 170k, mechanical handover
- Worst case: shadow crashes, hard ceiling fires at 170k, mechanical handover

## 5. Scope Creep Risk Assessment

### What this is
A token-budget lifecycle manager that ensures clean agent rotation. Specific, bounded, solves one problem.

### What this must not become
- A general-purpose agent supervisor (monitoring health, performance, correctness)
- A quality gate (reviewing the agent's work before eviction)
- A task scheduler (deciding what the replacement agent should do next)

### Complexity budget

| Component | Complexity | Justification |
|-----------|------------|---------------|
| Token tracking via JSONL | Low | Already available, just needs a line counter |
| Bash seam detection | Low | ~50 lines of bash, grep patterns on terminal buffer |
| Haiku handover synthesis | Low | Single-shot prompt, no conversation, no tools beyond cx_store |
| PreToolUse hook integration | Medium | Two thresholds (160k spawn, 170k hard kill), flag tracking |
| Respawn coordination | Medium | warroom_remove + warroom_add + orchestrator notification |

Total: ~200 lines of bash, ~50 lines of Python hook changes, one agent definition for the handover synthesizer. This is proportionate to the problem.

### The simpler alternative you mentioned

> At 165k, parse JSONL mechanically, kill, respawn. No shadow agent.

This works. The handover quality is lower (structured data without narrative synthesis), and the eviction timing is dumb (may cut mid-work). But it's 80% of the value at 20% of the complexity.

**My recommendation: build the simple version first (mechanical JSONL parse at 165k). Measure handover quality. If replacement agents consistently struggle to pick up context, add the shadow agent as a v2 enhancement.**

The shadow agent design is sound. It doesn't need to ship in v1. The architecture supports adding it later without changing the eviction interface (the output is the same: a handover brief at a known path, a bus notification to the orchestrator).
