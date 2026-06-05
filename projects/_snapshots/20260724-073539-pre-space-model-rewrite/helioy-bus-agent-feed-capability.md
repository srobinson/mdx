---
title: "Agent Feed Consumption: Package session transcript access as a bus-level MCP tool"
type: project
tags: [helioy-bus, agent-feed, session-transcript, mcp, tooling]
status: idea
project: helioy-bus
created: 2026-03-14
---

## Problem

During the context-matters warroom, the orchestrator was blind to architect-engineer review conversations. Could only see CC'd bus message summaries, not the actual reasoning, tool calls, or code the agents examined. Any agent should be able to consume another agent's full session feed.

## Existing Infrastructure

The plumbing already exists in multiple places:

- **Nancy** reads worker session transcripts to monitor progress and send course corrections
- **AM** ingests session data for geometric memory
- **Session transcripts** are files on disk (Claude Code writes them)

None of this is packaged as a shared capability. Each system reimplements its own transcript reading.

## Proposed Capability

Package as helioy-bus MCP tools. Any registered agent can call against any other registered agent's session.

### Operations

| Operation | Description |
|-----------|-------------|
| `bus_feed_tail` | Last N turns of an agent's session |
| `bus_feed_search` | Grep an agent's transcript for a term |
| `bus_feed_page` | Page through full session (less/more style, offset + limit) |

### Interface sketch

```
bus_feed_tail(agent_id: "helioy:general:5:2.4", lines: 50)
bus_feed_search(agent_id: "helioy:general:5:2.4", query: "scope path validation")
bus_feed_page(agent_id: "helioy:general:5:2.4", offset: 0, limit: 100)
```

Or a single tool with mode parameter:

```
bus_feed(agent_id: "...", mode: "tail" | "search" | "page", query?: "...", offset?: 0, limit?: 50)
```

### Implementation Path

1. Identify where Claude Code stores session transcripts (path convention by tmux pane)
2. Map bus agent_id → transcript file path
3. Expose read operations as MCP tools on helioy-bus
4. No new storage, no new indexing. Just file access through a consistent interface.

## Origin

Discovered during context-matters warroom planning (2026-03-14). Four agents (3 rust-engineers, 1 architect-reviewer) collaborated via helioy-bus. The orchestrator could monitor bus messages but had no visibility into the agents' actual work sessions.
