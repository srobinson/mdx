---
title: Warrooms Primitive Review
type: reviews
tags: [architecture, multi-agent, orchestration, helioy-bus, helioy-warroom]
summary: Architectural review of the warroom primitive in helioy-bus. Three-layer factoring (window, bus, lifecycle) cleanly separates concerns most agent frameworks collapse. The interactive tmux window is the load-bearing novelty.
status: active
source: claude-opus-4-7
confidence: high
created: 2026-05-15
updated: 2026-05-15
---

## Verdict

**Accept as foundation.** The warroom primitive is one of the cleanest factorings of multi-agent orchestration in the field. Three distinct layers each answer a different question without leaking into the others, and the interactive tmux window collapses the autonomy vs supervision tradeoff that most agent frameworks force as a binary choice.

## What it is

A warroom is a tmux window that hosts one runtime pane per agent type, registered against `helioy-bus` for structured message passing. Three coordinated primitives:

- `warroom_spawn` creates the tmux window and pane layout, validates agent types, registers each pane on the bus.
- `helioy-bus` carries durable, machine-readable messages between agents via per-recipient inboxes.
- Each tmux pane is a live, interactive agent runtime that the human can switch to at any time.

The factoring matters because each layer handles a distinct concern:

```text
Window  ── live workbench       (human ↔ agent, bidirectional)
Bus     ── structured handoff   (agent ↔ agent, durable artifact)
Warroom ── lifecycle scaffold   (spawn, register, layout, teardown)
```

Most agent frameworks collapse these into a single API surface. Spawn, drive, monitor, and collect become facets of one runtime call. That makes the simple case look small, but every non-trivial workflow ends up reinventing the missing primitives ad hoc.

## What is novel

### 1. The interactive window

The load-bearing property. The tmux pane is not a read-only console; it is the agent's actual TTY. The human can switch to the window, interrupt mid-thought, redirect, type instructions, or kill the process. The agent has no idea whether a human is watching or not, so its behavior does not bifurcate based on supervision mode.

Most agent runtimes force a choice at spawn time: full auto (and pray) or supervised (and babysit). The warroom collapses this. Autonomy is the default; intervention is one keystroke away; neither mode taints the structured output that lands on the bus. That property only emerges when the primitive is right.

### 2. Structured handoff decoupled from observation

`helioy-bus` carries machine-readable messages: agent A produces a structured artifact, sends to agent B, B receives via `get_messages`. The window is for humans; the bus is for machines. This separation means that an agent's tactical chatter in its pane never pollutes the artifacts it hands off, and humans can observe progress without parsing structured payloads.

The inverse is also true. Bus traffic stays clean even when a human jumps into a pane mid-execution to redirect.

### 3. Composability across N agents

Single-agent invocation is the degenerate case of an N-pane warroom. Same primitives at N=1 and N=8, no API churn. That uniform abstraction is a strong signal the design matches the problem shape rather than a particular use case.

## Where it will be tested

Two things to watch as warrooms scale beyond a single-investigator session.

### Pane density above ~8

Tmux layouts (`tiled`, `main-vertical`, etc.) lose readability fast past 8 panes. Past ~6, the cognitive load of "which window has the thing I care about" rises sharply. The warroom contract caps at 8 agents per warroom which is sensible, but a session-level routing or focus layer might be needed once orchestrators spawn multiple warrooms in parallel. Candidate: a "promoted pane" pattern where the warroom can hoist one pane to a larger split on demand.

### Cross-pane wait-and-feedback

When agent A's output is input to agent B, the bus is the right channel. But the affordance for "wait for B's result, then feed back into A" is currently coordinator-script territory. First-class support for typed message dependencies, or a `bus_wait_for` primitive that blocks until a structured response arrives, would lower the cost of common patterns and prevent ad hoc coordinator code from accumulating.

### Auth and runtime broker fragility

Observed during this session: codex's shared runtime broker socket (`/var/folders/.../cxc-*/broker.sock`) refusing connections silently broke subagent invocations via the codex bridge, without any user-facing diagnostic. Warroom spawn worked because it does not depend on the shared broker, but the failure mode for the broker case is worth a health check or surfaced error. Adjacent to warroom proper but in the same blast radius.

## Why the factoring matters

Every multi-agent system eventually has to answer the same four questions:

1. How does a human know what an agent is doing right now?
2. How does an agent hand a structured result to another agent?
3. How does the system manage spawn, lifecycle, and cleanup?
4. How does the human intervene without bringing the whole thing down?

Most frameworks answer one or two well and bolt the rest on later. Warrooms answer all four with three primitives, and each primitive is independently useful. The window alone is valuable for any long-running agent. The bus alone is valuable for any structured handoff. The warroom alone is valuable for any team composition. Putting them together is a force multiplier, not a coupling cost.

## Recommendation

**Default pattern for multi-agent work.** When the task involves more than one agent, parallel investigation, or human oversight of autonomous execution, reach for a warroom rather than a single-agent subprocess. The setup cost is one tool call; the observability dividend is structural.

For single-investigator deep-dive tasks where the agent runtime is already known and stable, direct subagent invocation remains lighter weight. But the warroom should be the second tool reached for, not the last.
