---
title: Token Eviction Strategy - Agent UX Analysis
category: projects
created: 2026-03-17
author: ux-architect
status: brainstorm
tags: [helioy-bus, warroom, token-management, agent-ux, eviction]
---

# Token Eviction: What Produces the Best Agent Behavior?

## The Behavioral Answer

Option (d) is the real risk, and it dominates. LLMs are trained on human text where "running out of time/space" triggers summarization, hedging, and meta-commentary. An agent at 158k/165k that sees a fuel gauge will almost certainly start producing output like "Given my remaining context, let me quickly summarize..." That is pure waste. It consumes the very tokens it is trying to conserve, and the summarization is worse than what a fresh agent would produce with proper handoff state.

Option (b) also occurs. Rushed output from an LLM under perceived pressure tends toward shallower reasoning, skipped validation steps, and shorter tool call descriptions. The agent "knows" it should finish fast and trades quality for speed. This is the opposite of what we want in the final stretch of a session.

Option (a) is theoretically possible but requires specific training or prompting to achieve. Current foundation models do not have a reliable "wrap up gracefully" behavior when shown resource limits. They either ignore the signal or overreact.

Option (c) would be ideal but is unlikely. LLMs attend to injected context. A `[context: 158k/165k]` annotation in every tool response is high-salience text that will influence generation.

## Recommendation: Option B (Silence) with Orchestrator Visibility

### For agents: total silence

The agent should never see its own token count. Its job is to produce the best possible output on the current task. Resource management is an infrastructure concern, not an agent concern. Mixing the two degrades both.

This follows a well-established UX principle: do not surface system constraints that the user cannot meaningfully act on. An agent cannot "decide to use fewer tokens." It can only degrade its output quality in an attempt to be shorter. That is strictly worse than letting it run at full quality until eviction.

### For the orchestrator: full visibility

The orchestrator is the resource manager. It needs token counts to make scheduling decisions:

```
warroom_status()
→ {
    "agents": [
      {"agent_id": "...", "token_usage": 142000, "budget": 165000, "utilization": 0.86},
      {"agent_id": "...", "token_usage": 98000, "budget": 165000, "utilization": 0.59}
    ]
  }
```

The orchestrator can then decide:
- Pre-stage a replacement agent before eviction
- Route new work to lower-utilization agents
- Trigger early handoff if the remaining budget is insufficient for the next task

This is the correct separation of concerns. The orchestrator manages resources. Agents produce work.

### The eviction handoff

The critical UX moment is not the eviction itself but the continuity gap. When agent A is evicted and agent B takes over, what state transfers?

Two options:

**Minimal handoff (recommended):** The session-logger fires before eviction and persists a structured work log. The replacement agent receives this log as part of its initial prompt. The orchestrator manages the routing.

**Rich handoff:** Agent A is prompted to produce a structured handoff document before eviction. This requires the agent to know eviction is coming, which brings us back to the fuel gauge problem.

Minimal handoff wins because it does not require agent cooperation. The session logger already captures tool calls, file modifications, and key decisions. A fresh agent with that context plus the original task description can resume effectively.

## The Exception: Long-Running Deliberate Tasks

There is one scenario where agent-visible token awareness might help: tasks that are inherently multi-phase and where the agent is choosing how to allocate effort across phases (e.g., "research, then design, then implement"). Knowing it has 40% budget remaining could help the agent decide to skip the implementation phase and hand off a design document instead.

But this is better solved by task decomposition at the orchestrator level. Break "research + design + implement" into three separate tasks assigned to three agents. Each agent gets full budget for one phase. The orchestrator sequences them.

Do not solve orchestration problems inside the agent.

## Summary

| Audience | Sees token count? | Rationale |
|----------|-------------------|-----------|
| Agent | No | Prevents behavioral degradation. Agent focuses on quality. |
| Orchestrator | Yes, via `warroom_status` | Enables proactive scheduling and replacement staging. |
| Human operator | Yes, via `warroom status` CLI | Operational visibility for debugging and capacity planning. |

The eviction should be silent from the agent's perspective. The orchestrator fires `session-logger`, tears down the pane, spawns a replacement, and injects the work log. The replacement agent does not know it is a replacement. It just receives a task with prior context.
