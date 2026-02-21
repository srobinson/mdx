---
title: Token Eviction Strategy - Architect Feedback
author: engineering-software-architect
date: 2026-03-17
topic: token-eviction-strategy
tags: [architecture, helioy-bus, token-management, agent-lifecycle, warroom]
---

# Token Eviction Strategy: Architect Feedback

## Recommendation: Option B with a structured wind-down phase

Neither option as described is complete. Option A has the right intuition (agents should be aware of limits) but the wrong mechanism (continuous display creates noise and behavioral drift). Option B has the right default (agents work uncontaminated) but the wrong endgame (abrupt eviction loses in-flight work).

The third option combines both: silent operation with a single, structured wind-down prompt at threshold.

## Why Option A Fails

Continuous token display creates a category of problem I'd call **resource anxiety**. LLMs trained on RLHF optimize for perceived helpfulness. When an agent sees its fuel gauge climbing, it will:

1. Start compressing responses (lower quality)
2. Skip validation steps it would normally perform
3. Attempt to "finish everything" rather than checkpoint cleanly
4. Mention the token count in its outputs ("I'm running low on context, so let me quickly...")

This behavior is well-documented in human psychology (deadline pressure) and transfers to LLM behavioral patterns. The continuous display doesn't give the agent "situational awareness" in a useful sense. It gives it a countdown timer that degrades its work.

The context cost is also non-trivial. One line per tool call across a 165k context window means hundreds of injected lines. Each one is a few tokens, but they accumulate, and worse, they anchor the model's attention on resource management rather than the task.

## Why Option B Almost Works

Option B's key insight is correct: the best work comes from agents that don't know they're being watched. An agent at 160k tokens that doesn't know its count will produce the same quality work as one at 50k tokens (modulo actual context rot, which is a model limitation, not a behavioral one).

The failure mode is the abrupt cut. Consider: the agent is halfway through implementing a function. It calls a tool. The PreToolUse hook fires, sees 165k, triggers session-logger, and kills the pane. The session-logger captures whatever the agent's last message was, but that message wasn't a summary of remaining work. It was "let me read this file to check the return type." The handover to the replacement agent is incomplete because the evicted agent never had a chance to describe what it was doing and what remains.

## Option C: Silent Operation + Structured Wind-Down

### How it works

1. **0 to 150k tokens**: The agent operates with zero awareness of its token budget. No fuel gauge. No hints. Full quality work.

2. **At 150k tokens** (the wind-down trigger): A single system-level injection via the PreToolUse hook delivers a structured wind-down directive. Not a warning. A directive.

```
[SYSTEM] Context rotation scheduled. Before your next tool call, write a handover
brief: (1) what task you were working on, (2) what you've completed, (3) what
remains, (4) any decisions or context the next agent needs. Use session-logger
to persist it. You have approximately 15k tokens remaining.
```

3. **The agent writes its handover brief.** This is a natural LLM behavior. Given a clear instruction with structure, the agent will produce a thorough summary. It's not panicking because it just learned about the limit. It's executing a well-defined sub-task.

4. **At 165k tokens** (the hard eviction): Kill the pane regardless. If the agent completed its handover, great. If not (because it ignored the directive or got stuck), the session-logger captures whatever state exists. The hard limit is a safety net, not the primary mechanism.

5. **The replacement agent** receives the handover brief as part of its initial prompt. The orchestrator doesn't need to synthesize anything. The evicted agent wrote its own handover.

### Why this is better

| Concern | Option A | Option B | Option C |
|---------|----------|----------|----------|
| Work quality 0-150k | Degraded by fuel gauge awareness | Full quality | Full quality |
| Work quality 150-165k | Further degraded by urgency | Full quality until abrupt cut | Intentionally redirected to handover |
| Handover completeness | Incidental (whatever session-logger captures) | Incidental | Structured (agent writes its own brief) |
| Behavioral contamination | High (every tool call) | Zero | Minimal (single injection at 150k) |
| Orchestrator burden | Low (agent self-manages, poorly) | High (must synthesize handover from raw session log) | Low (handover brief is agent-authored) |
| Implementation complexity | Medium (hook on every call, threshold logic) | Low (single threshold check) | Medium (two thresholds, one injection) |

### The key insight

The 15k buffer between 150k and 165k isn't wasted "warning space." It's a work phase with a different objective. The agent transitions from "execute the task" to "document your state for your successor." That's a legitimate, useful use of those tokens.

## Implementation Notes

### The wind-down injection

The PreToolUse hook already has access to `additionalContext`. The injection should fire exactly once. Use a flag file or bus state to track whether the wind-down directive has been delivered for this session.

```python
# In the PreToolUse hook
if token_count >= 150_000 and not wind_down_delivered(session_id):
    mark_wind_down_delivered(session_id)
    return {"additionalContext": WIND_DOWN_DIRECTIVE}
```

The directive should NOT say "you're running out of tokens." It should say "context rotation is scheduled." The framing matters. "Running out" triggers scarcity behavior. "Scheduled rotation" triggers orderly handover behavior.

### What the handover brief should contain

Structure it as a template the agent fills in:

```markdown
## Handover Brief
### Task: [what was assigned]
### Completed: [what's done, with file paths]
### In Progress: [what was mid-flight]
### Remaining: [what hasn't been started]
### Decisions Made: [any choices that affect remaining work]
### Blockers: [anything the next agent should know about]
```

### The replacement agent's initial prompt

The orchestrator composes the new agent's prompt:

```
You are continuing work started by a previous agent in this warroom.

[Handover brief from evicted agent]

Pick up from where they left off. Start with the "In Progress" items.
```

### Failure mode: agent ignores the wind-down directive

Possible, but unlikely. LLMs are instruction-followers by training. The directive is clear, structured, and doesn't conflict with the current task. If the agent does ignore it (perhaps deep in a multi-step tool call chain), the 165k hard eviction catches it, and the session-logger provides a fallback (less complete, but present).

### Failure mode: agent uses all 15k tokens on the handover

Also unlikely, but guard against it. The directive should say "concise handover brief (500 words max)." If the agent's handover takes more than 2-3k tokens, the remaining buffer is still adequate for session-logger to fire at 165k.

## One More Consideration: Eviction Notification to Peers

When an agent is evicted, the orchestrator should be notified (you already have this). But consider also: should the evicted agent's warroom peers be notified? If agent A was working with agent B on a shared task, agent B needs to know that A was replaced and that A's successor may ask for context.

A bus message from the orchestrator to the warroom topic would handle this:

```
[orchestrator -> topic:warroom-{name}] Agent {qualified_name} rotated at {timestamp}.
Replacement spawned. Handover brief available at {path}.
```

This is a low-cost addition that prevents peers from sending messages to a dead agent and waiting for responses that never come.
