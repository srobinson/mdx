---
title: Helioy Bus Audit
type: projects
tags: [helioy, helioy-bus, architecture, audit, testing, runtime]
summary: Audit of helioy-bus covering architecture, code quality, test surface, and structural risks.
status: active
created: 2026-04-17
updated: 2026-04-17
project: helioy-bus
confidence: high
related: [helioy-bus-proposal]
---

# Helioy Bus Audit

## Scope

This audit reviews `helioy-bus` as it exists today across four concerns:

- architecture and boundaries
- code quality and maintainability
- test surface and operational confidence
- readiness for a broader runtime model beyond Claude

The codebase is small and functional, but it still carries clear proof of concept characteristics. The main issue is not that the code is failing. The main issue is that core concepts are implicit, spread across multiple mechanisms, and encoded directly in handlers and hooks rather than in stable domain boundaries.

## Current Product Shape

`helioy-bus` already exposes a meaningful product surface:

- agent registration and presence
- direct, role based, and broadcast messaging
- tmux based wakeup and liveness checks
- warroom orchestration
- plugin agent discovery
- token capture and session metadata

That is already larger than a narrow message bus. In practice this repo is becoming a local multi agent control plane.

## Current Architecture

The system is implemented through two main MCP entrypoints:

- `server/bus_server.py`
- `server/warroom_server.py`

Shared state and behavior are split across:

- SQLite tables in `server/_db.py`
- file based inboxes under `~/.helioy/bus/inbox/`
- tmux subprocess control in `server/_tmux.py`
- hook scripts in `plugin/hooks/`
- identity logic spread across Bash and Python

The dominant pattern is inline orchestration. MCP handlers perform validation, persistence, filesystem writes, identity lookup, tmux interaction, and response formatting directly.

## Main Findings

### 1. Warroom membership is modeled incorrectly

This is the clearest concrete bug in the current design.

`warroom_members` is keyed by `(warroom_id, agent_type)`. That means:

- repo mode panes all compete for the same `"general"` key
- duplicate specialist roles cannot be represented correctly
- add and remove semantics are forced to target by type rather than stable membership identity

This is too weak for the current feature set and completely insufficient for a robust control plane.

## 2. Identity is not canonical

There are multiple identity derivation paths:

- hook based resolution from pane title
- `register_agent()` auto derived ids
- `_self_agent_id()` via PID files or shell fallback
- basename fallback when nothing else is available

These can disagree. That creates a system where registration identity, runtime identity, and messaging identity are not guaranteed to be the same thing.

This is the most important architectural blocker for future Codex support.

## 3. Core handlers mix too many concerns

The main MCP handlers combine:

- transport layer concerns
- domain behavior
- persistence
- filesystem delivery
- tmux side effects
- liveness and reconciliation

This makes the code harder to evolve, harder to test in isolation, and harder to reason about when failures happen mid flow.

## 4. Reads mutate state

Several read style tools also perform cleanup or backfill work:

- `list_agents()` prunes registry rows
- `get_messages()` archives and TTL cleans messages
- `warroom_status()` backfills member identity

This makes query behavior non deterministic and obscures where reconciliation actually lives.

## 5. Hook logic is duplicated

Important behavior exists twice:

- registration logic in both Python and hook embedded Python
- unregister behavior in both server and hook paths
- mailbox scan and identity fallback duplicated across mail scripts

This raises the risk of contract drift between runtime behavior and the MCP layer.

## 6. Test coverage is good in process, weaker at the operational boundary

The Python test suite is healthy for in process behavior. It covers core registry, routing, and many warroom operations well.

The weak spots are:

- production hook execution
- shell to Python contract behavior
- tmux subprocess behavior
- partial failure semantics
- end to end operational flow

The identity shell tests exist, but they are not part of the default test path.

## 7. The architecture is runtime specific in practice

Even where the code looks generic, many assumptions are Claude specific:

- hook lifecycle model
- pane title conventions
- launch commands
- token capture path
- runtime identity assumptions

That does not make the system wrong. It does mean the current abstraction boundary is at the wrong level for multi runtime support.

## What Is Working Well

The audit is not a verdict that the code is bad. Several things are working well:

- the repo is still small enough to restructure without heroic effort
- the current tests catch many regressions in core Python behavior
- the product surface is coherent enough to extract a real model from it
- the shared filesystem plus SQLite approach is still viable for the current deployment model

The project has enough shape to justify methodical architecture work rather than a rewrite from scratch.

## Dead Code And Hack Assessment

I did not find large amounts of obvious dead code. The issue is not unused modules. The issue is prototype style coupling:

- hot reload proxy and CLI entrypoints are thin wrappers with little or no coverage
- shell scripts carry core behavior that should eventually move behind shared interfaces
- tmux coordinates function as domain keys in places where they should only be infrastructure details
- documentation around `reply_to` suggests semantics that the implementation does not actually enforce

This is a codebase with active paths that are modeled too loosely, not a codebase bloated with abandoned subsystems.

## Architectural Conclusion

`helioy-bus` should be understood as a local agent control plane with these domain concerns:

- agent identity
- presence and liveness
- message delivery
- runtime capability and type
- warroom desired state
- infrastructure reconciliation

The current implementation is effective enough for a POC, but the model is still implicit. That implicitness is the root cause behind the main audit findings.

## Recommended Priorities

1. Fix the warroom membership model.
2. Define canonical agent identity.
3. Separate application logic from MCP and hook adapters.
4. Isolate tmux and runtime specific behavior behind narrow interfaces.
5. Add contract tests for hook and process boundaries.

## Bottom Line

The codebase does not need a rewrite.

It does need a deliberate extraction of domain boundaries so the next phase of work, especially Claude plus Codex support, is building on an explicit model rather than on conventions hidden in pane titles, hooks, and inline handler code.
