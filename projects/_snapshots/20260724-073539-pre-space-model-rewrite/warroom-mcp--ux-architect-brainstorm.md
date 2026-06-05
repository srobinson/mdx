---
title: Warroom MCP Tools - UX Architect Brainstorm
category: projects
created: 2026-03-17
author: ux-architect
status: brainstorm
tags: [helioy-bus, warroom, mcp, agent-ux, discovery]
---

# Warroom MCP Tools: Agent-Facing Experience Design

The "user" is an orchestrator LLM. Every tool call costs context tokens. Every round-trip costs latency. The design goal: minimize both while maximizing decision quality.

## 1. Discovery Flow

### The Problem

100+ agent types across 5+ namespaces. An orchestrator receives a task description ("review this PR for security and test coverage") and needs to assemble the right team. Three viable discovery strategies, each with distinct tradeoffs.

### Strategy A: Semantic Search (Recommended Primary)

```
warroom_search(query: "security review and test coverage analysis")
→ returns ranked candidates with match scores
```

Why this wins: the orchestrator already has a natural language task description. Forcing it to decompose that into category browsing or exact type names adds cognitive overhead and extra tool calls. A semantic search lets the LLM delegate the matching problem to the server.

Implementation: embed the agent descriptions (already present in the Agent tool definition block) into a lightweight vector index or BM25 keyword index. Agent descriptions are short enough that BM25 with good tokenization works well. No need for a full vector DB.

**Response shape** (critical for LLM consumption):

```json
{
  "results": [
    {
      "agent_type": "pr-review-toolkit:silent-failure-hunter",
      "namespace": "pr-review-toolkit",
      "summary": "Identifies silent failures and inadequate error handling in PRs",
      "match_score": 0.92,
      "tags": ["security", "error-handling", "code-review"]
    }
  ],
  "total_available": 4,
  "query_interpreted_as": "security-focused PR review with test analysis"
}
```

Keep `summary` to one sentence. The orchestrator does not need the full agent description to make a selection decision. If it wants more detail, it can call a separate `warroom_agent_info(agent_type)` tool.

### Strategy B: Category Browse (Secondary, for Exploration)

```
warroom_browse(namespace: "pr-review-toolkit")
→ returns all types in that namespace with one-line summaries
```

Useful when the orchestrator knows the domain ("I need QA agents") but not specific types. Also useful for building presets. Keep this as a secondary tool, not the primary discovery path.

### Strategy C: Direct Specification (No Discovery Needed)

```
warroom_spawn(agents: ["code-reviewer", "silent-failure-hunter", "test-automator"])
→ orchestrator already knows what it wants
```

Many warroom invocations come from experienced orchestrators or preset templates. Discovery is wasted context in these cases. The spawn tool should accept explicit agent types without requiring a search step first.

## 2. The `warroom_recommend` Question

**Yes, but framed correctly.** Call it `warroom_plan` instead, because the output is a proposed team composition the orchestrator can accept, modify, or reject.

```
warroom_plan(
  task: "Review PR #432 for security vulnerabilities, test coverage gaps, and code quality",
  max_agents: 5,
  constraints: ["prefer pr-review-toolkit namespace"]
)
→ {
    "proposed_team": [
      {"agent_type": "pr-review-toolkit:code-reviewer", "rationale": "General code quality"},
      {"agent_type": "pr-review-toolkit:silent-failure-hunter", "rationale": "Error handling audit"},
      {"agent_type": "pr-review-toolkit:pr-test-analyzer", "rationale": "Test coverage analysis"},
      {"agent_type": "voltagent-qa-sec:security-auditor", "rationale": "Security vulnerability scan"}
    ],
    "excluded_with_reason": [
      {"agent_type": "voltagent-qa-sec:penetration-tester", "reason": "Active exploitation not appropriate for PR review"}
    ]
  }
```

This is not over-engineering. It is the highest-leverage tool in the set. An orchestrator calling `warroom_plan` once replaces what would otherwise be: search, read results, evaluate candidates, search again, compare, decide. That is 3-5 tool calls collapsed into one.

The `excluded_with_reason` field is important. It teaches the orchestrator about agent boundaries, reducing future misselections.

### Implementation Note

`warroom_plan` can be implemented entirely server-side using the same BM25/keyword matching that powers `warroom_search`, plus a set of composition rules (e.g., "never include penetration-tester for review-only tasks", "always include code-reviewer as baseline for any code-focused warroom"). No LLM inference required on the server side.

## 3. Information Density

### The Golden Rule: One Tool Call, One Decision

Each tool response should contain exactly enough information for the orchestrator to make its next decision without a follow-up call.

**Too sparse** (forces round-trips):
```json
{"agent_types": ["code-reviewer", "silent-failure-hunter", "test-automator"]}
```
The orchestrator has to call another tool to learn what these agents do before deciding.

**Too dense** (wastes context):
```json
{"agents": [{"type": "code-reviewer", "full_description": "800 words...", "tools_available": [...], "example_prompts": [...]}]}
```
The orchestrator does not need the full tool list to decide whether to include an agent in a warroom.

**Right density**:
```json
{
  "agent_type": "code-reviewer",
  "summary": "Reviews code for quality, security, and best practices",
  "namespace": "pr-review-toolkit",
  "tags": ["code-quality", "security", "best-practices"]
}
```

One sentence summary + tags. That is the decision surface an LLM needs.

### Pagination: Do Not Paginate

With 100+ agents, there is a temptation to paginate browse results. Resist it. Pagination means multiple round-trips. Instead:

- `warroom_search` returns top N results (default 10, configurable via `limit`)
- `warroom_browse` returns all agents in a namespace (namespaces are small, 5-15 agents each)
- If the orchestrator wants everything, `warroom_browse(namespace: "all")` returns all 100+ agents with one-line summaries. At ~50 tokens per agent, that is ~5000 tokens. Expensive but cheaper than 10 paginated calls.

## 4. Presets and Templates

### Discovery Model

Presets are named team compositions maintained as configuration, not code. An orchestrator discovers them via:

```
warroom_presets()
→ {
    "presets": [
      {
        "name": "pr-review",
        "description": "Standard pull request review team",
        "agents": ["code-reviewer", "silent-failure-hunter", "pr-test-analyzer"],
        "tags": ["review", "quality"]
      },
      {
        "name": "design-team",
        "description": "Full design review and implementation team",
        "agents": ["brand-guardian", "ui-designer", "visual-storyteller", "ux-researcher"],
        "tags": ["design", "brand", "ux"]
      }
    ]
  }
```

### Spawning from Presets

```
warroom_spawn(preset: "pr-review", name: "review-432")
```

Presets can be extended inline:

```
warroom_spawn(
  preset: "pr-review",
  add: ["security-auditor"],
  remove: ["pr-test-analyzer"],
  name: "security-review-432"
)
```

### Where Presets Live

A TOML or JSON file in `~/.helioy/bus/presets/`. Not hardcoded. Users and orchestrators should be able to create presets from successful warroom compositions:

```
warroom_save_preset(
  name: "security-review",
  agents: ["code-reviewer", "silent-failure-hunter", "security-auditor"],
  description: "Security-focused code review team"
)
```

## 5. Error Communication

### Principle: Errors Must Be Actionable

Every error response should tell the orchestrator what to do next, not just what went wrong.

```json
{
  "error": "agent_type_not_found",
  "agent_type": "backend-dev",
  "message": "No agent type 'backend-dev' found",
  "suggestions": ["backend-developer", "backend-engineer"],
  "action": "Retry with a corrected agent_type"
}
```

### Error Categories

| Error | Response Pattern |
|-------|-----------------|
| Agent type not found | Fuzzy-match suggestions + "retry with corrected type" |
| tmux not available | `{"error": "tmux_unavailable", "action": "Warroom requires tmux. Start a tmux session first."}` |
| Pane limit reached | `{"error": "pane_limit", "current": 8, "max": 8, "action": "Kill existing warroom or increase limit"}` |
| Window name collision | `{"error": "window_exists", "name": "review", "action": "Use force=true to replace, or choose a different name"}` |
| Agent spawn failed | `{"error": "spawn_failed", "agent_type": "code-reviewer", "pane_id": "%12", "reason": "claude process exited", "action": "Check logs at ~/.helioy/bus/logs/"}` |

### Partial Success

Warroom spawns are multi-agent operations. Some agents may succeed while others fail. Always return a manifest:

```json
{
  "warroom": "review-432",
  "spawned": [
    {"agent_type": "code-reviewer", "agent_id": "helioy-bus:code-reviewer:3:4.0", "status": "running"},
    {"agent_type": "silent-failure-hunter", "agent_id": "helioy-bus:silent-failure-hunter:3:4.1", "status": "running"}
  ],
  "failed": [
    {"agent_type": "security-auditor", "error": "spawn_failed", "reason": "agent definition not found"}
  ]
}
```

The orchestrator can decide whether partial success is acceptable or whether to abort the entire warroom.

## 6. Complete Tool Surface (Proposed)

Minimal viable set, ordered by expected call frequency:

| Tool | Purpose | When |
|------|---------|------|
| `warroom_spawn` | Create a warroom from explicit types or preset | Every warroom creation |
| `warroom_status` | List active warrooms and their agents | Monitoring, health checks |
| `warroom_kill` | Tear down a warroom by name | Cleanup |
| `warroom_plan` | Get team composition recommendation for a task | Complex or unfamiliar tasks |
| `warroom_search` | Find agent types by capability description | Discovery when plan is not enough |
| `warroom_presets` | List available preset compositions | Exploration, learning |
| `warroom_browse` | List all agents in a namespace | Exploration |
| `warroom_save_preset` | Save a warroom composition as a reusable preset | After successful warroom |

Eight tools. The first three handle 80% of usage. The rest are progressive disclosure for complex scenarios.

## 7. Interaction Flow: Happy Path

```
Orchestrator receives task: "Review PR #432 for security issues"

1. warroom_plan(task: "Review PR #432 for security issues", max_agents: 4)
   → proposed_team: [code-reviewer, silent-failure-hunter, security-auditor]

2. warroom_spawn(agents: ["code-reviewer", "silent-failure-hunter", "security-auditor"], name: "pr-432")
   → warroom created, 3 agents running, all agent_ids returned

3. send_message(to: "*", content: "Review PR #432...", topic: "pr-432-review")
   → messages delivered to all warroom agents

Done. Three tool calls from task to running warroom.
```

## 8. Architecture Note: Server-Side vs Client-Side Logic

The current warroom.sh handles tmux operations (split-window, send-keys, pane identity). Moving this to MCP tools means the bus_server.py needs to shell out to tmux. This is already established pattern (see `_tmux_pane_alive` and `_tmux_nudge`).

Key constraint: the MCP server runs as a stdio subprocess of Claude Code. It has access to tmux commands if the parent session is in tmux. The `warroom_spawn` tool should validate tmux availability before attempting any pane operations and return a clear error if tmux is not present.

## 9. What I Would Not Build

- **Agent capability negotiation at runtime.** Agent types are static definitions. Runtime discovery of "what can you do?" is a different problem and adds protocol complexity without clear value.
- **Warroom chat channels.** The bus already provides messaging. Adding warroom-scoped channels creates a parallel communication system. Use topics on existing `send_message` instead.
- **Agent health monitoring within warrooms.** The bus `list_agents` already prunes dead panes. Warroom status can delegate to the registry rather than maintaining separate state.
- **Dynamic agent scaling.** "Add another code-reviewer because the first one is slow" is orchestrator-level logic, not warroom infrastructure. Keep the warroom tools focused on lifecycle (create, status, kill).
