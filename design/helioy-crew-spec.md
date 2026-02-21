---
title: "Helioy Crew: Tmux-based Multi-Agent Orchestration"
type: design
tags: [helioy-crew, orchestration, agents, tmux, claude-code, multi-agent]
summary: Tmux-based orchestration system where an interactive orchestrator manages a dynamic fleet of coordinator agents, each spawning expert subagents to execute Linear issues by role.
status: active
source: project-planner
confidence: high
created: 2026-03-09
updated: 2026-03-09
---

# Helioy Crew

Tmux-based multi-agent orchestration for Claude Code. An interactive orchestrator manages a dynamic fleet of coordinator agents across tmux panes, each spawning expert subagents to execute Linear issues decomposed by role.

Linear project: https://linear.app/alphabio/project/helioy-crew-2eb2d97af131/overview

## Architecture

### Three-Layer Process Model

```
Window 1: Orchestrator (claude --agent helioy.main.orchestrator)
  │         Human-facing. Reads Linear. Manages tmux. Sends mail.
  │         Lifecycle: session-long, interactive
  │
  │  tmux split-window / send-keys / kill-pane
  │  helioy-bus for all coordination
  │
Window 2: Coordinators (claude --agent helioy.main.coordinator --session-id <uuid>)
  │         Task-scoped. Born, works, dies.
  │         Lifecycle: single task, exits on completion or PreCompact
  │
  │  Agent tool (native subagent spawning)
  │
  ├── helioy.sub.frontend-engineer    ← subagent (leaf node)
  ├── helioy.sub.backend-engineer     ← subagent (leaf node)
  ├── helioy.sub.ux-designer          ← subagent (leaf node)
  └── helioy.sub.visual-designer      ← subagent (leaf node)
```

| Layer        | Agent Definition           | Started With                                                 | Lifecycle                         | Can Spawn                          |
| ------------ | -------------------------- | ------------------------------------------------------------ | --------------------------------- | ---------------------------------- |
| Orchestrator | `helioy.main.orchestrator` | Human launches interactively                                 | Session-long                      | Coordinators (via tmux panes)      |
| Coordinator  | `helioy.main.coordinator`  | `claude --agent helioy.main.coordinator --session-id <uuid>` | Task-scoped (single Linear issue) | Expert subagents (via Agent tool)  |
| Expert       | `helioy.sub.*`             | Agent tool from coordinator                                  | Subtask-scoped                    | Nothing (leaf node, no Agent tool) |

### Why This Works

**No subagent nesting limit hit.** Each coordinator is a main `claude` process with full Agent tool access. Experts are one level deep. The Claude Code constraint (subagents cannot spawn subagents) is respected structurally.

**Every agent knows who it is.** The `--agent` flag loads identity, tools, constraints, and collaboration contracts before the first prompt arrives.

**Task-scoped coordinators avoid compaction.** Born with a task, spawns experts, runs review/sign-off, reports completion via bus, exits. Token budget stays bounded. If a task is too large for one coordinator lifecycle, the orchestrator decomposes further.

**Human can intervene at any time.** Switch to window 2, observe any pane, type directly into any coordinator session.

## Communication

### helioy-bus Message Flow

All coordination flows through helioy-bus. The orchestrator never touches a coordinator's stdin after initial launch.

```
Orchestrator (W1)                    Coordinators (W2 panes)
─────────────────                    ──────────────────────
reads ALP-123 from Linear
decomposes by role tags

spawns pane, launches claude  ──→    coordinator-1 starts
sends task via helioy-bus     ──→    checks mail, picks up task
                                     spawns expert subagents
                                     works...
                                     sends "blocked on API contract" ──→  orchestrator reads

spawns another pane           ──→    coordinator-2 starts
sends task via helioy-bus     ──→    checks mail, picks up task
                                     works...
                                     sends "API contract ready" ──→  orchestrator forwards to coordinator-1

                                     coordinator-1 unblocks, continues
                                     sends "complete" ──→  orchestrator marks issue done
orchestrator kills pane
```

### Message Targets

The orchestrator can send messages to:

- **Individual coordinator**: targeted by pane/session ID
- **All coordinators**: broadcast via `*`
- **Role groups**: target by agent type (e.g., all frontend coordinators)

### Pane Startup Sequence

```bash
# Orchestrator creates pane
tmux split-window -t crew-agents

# Orchestrator launches coordinator with controlled session ID
session_id=$(uuidgen)
tmux send-keys -t crew-agents.1 \
  "claude --agent helioy.main.coordinator --session-id $session_id" Enter

# Task is already waiting on the bus
# Coordinator picks it up via check-directives on startup
```

## Token Lifecycle

Compaction is death, not recovery. A coordinator never compacts. It dies cleanly and a fresh one can be spawned with geometric memory providing continuity.

### External Token Watcher

A separate process (not inside any agent) tails the coordinator's session JSONL and monitors burn rate. The orchestrator owns the session ID, so the JSONL path is always known:

```
~/.claude/projects/<encoded-project>/<session-id>.jsonl
```

Token tracking reuses nancy's proven approach:

- Parse `.message.usage` from assistant messages in the stream
- High-water-mark tracking (context usage only increases)
- Progressive threshold alerts sent via helioy-bus:

```
  0%  ──── working ────────────────────────────────
 65%  ──── warning: "start wrapping up" ───────────  ← token watcher via bus
 75%  ──── critical: "wind down NOW" ──────────────  ← token watcher via bus
 85%  ──── danger: "STOP" ─────────────────────────  ← token watcher via bus
  ~%  ──── PreCompact fires ───────────────────────  ← last resort safety net
           1. am sync (persist geometric memory)
           2. bus message to orchestrator (status report)
           3. kill process
```

### PreCompact Hook

The safety net. Fires if the coordinator ignored all warnings or the task was genuinely too large.

```yaml
hooks:
  PreCompact:
    - hooks:
        - type: command
          command: "~/Dev/LLM/DEV/helioy/helioy-plugins/plugins/helioy-tools/hooks/crew-precompact.sh"
```

The hook:

1. Calls `am sync` to persist geometric memory (same as SessionEnd)
2. Sends a status report to the orchestrator via helioy-bus (what's done, what's not, any uncommitted work)
3. Kills the process

### Orchestrator Response to Coordinator Death

When the orchestrator receives a death/completion message:

- **Task complete**: mark Linear issue done, kill pane, move on
- **Task incomplete (PreCompact death)**: spawn a fresh coordinator for the remaining work. The new coordinator calls `am_query` on startup, recalls where the previous one left off. No compaction, no context loss. Clean handoff through geometric memory.

## Session ID Ownership

The orchestrator always creates and owns session IDs. This is foundational.

- Orchestrator generates UUID before launching a coordinator
- Passes it via `--session-id <uuid>`
- Token watcher uses the same UUID to locate the JSONL file
- Session ID maps 1:1 to a Linear issue for traceability

```
session_id → coordinator pane → Linear issue → JSONL file → token watcher
```

All five are linked by the session ID the orchestrator controls.

## Linear Integration

### Issue Organization

Linear issues are organized/tagged by role:

```
ALP-123: "Billing System" (parent)
  ├── ALP-124 [backend]  "Create billing API endpoints"
  ├── ALP-125 [frontend] "Implement billing dashboard"  (blocked by ALP-124)
  └── ALP-126 [design]   "Design billing components"    (blocks ALP-125)
```

### Dependency-Aware Sequencing

The orchestrator reads the issue dependency graph and sequences coordinator launches:

1. Spawn ALP-126 (design) and ALP-124 (backend) in parallel (no dependency)
2. Wait for both to signal completion via bus
3. Spawn ALP-125 (frontend) which consumes outputs from both

### Issue Lifecycle

```
Backlog → Todo → In Progress (coordinator spawned) → Done (coordinator exits)
```

The orchestrator updates Linear status as coordinators report via bus.

## Agent Definitions Required

### New Agents

| Agent                      | Type | Purpose                                                                                                                                                |
| -------------------------- | ---- | ------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `helioy.main.orchestrator` | main | Human-facing. Reads Linear, manages tmux panes, routes bus messages, tracks token budgets, handles dependency sequencing.                              |
| `helioy.main.coordinator`  | main | Task-scoped team lead. Receives a Linear issue via bus, spawns the right expert subagents, collects results, runs review/sign-off, reports completion. |

### Existing Agents (Expert Fleet)

| Agent                          | Role                                                           |
| ------------------------------ | -------------------------------------------------------------- |
| `helioy.sub.ux-researcher`     | User research, personas, journey maps, usability protocols     |
| `helioy.sub.ux-designer`       | Interaction design, component specs, design system foundations |
| `helioy.sub.visual-designer`   | Brand tokens, themes, visual polish, motion design             |
| `helioy.sub.frontend-engineer` | React/Next.js implementation, CSS, performance, accessibility  |
| `helioy.sub.mobile-engineer`   | React Native/Expo, platform APIs, EAS builds, app store        |
| `helioy.sub.backend-engineer`  | API endpoints, DB schema, auth, infrastructure                 |

### Coordination Contracts

**API contract as coordination primitive.** The backend coordinator produces a typed API contract document. The frontend coordinator receives it via bus before starting implementation. Contract negotiation is bidirectional.

**Design spec as handoff artifact.** The design coordinator produces a design specification to `~/.mdx/design/`. The frontend/mobile coordinator reads it as input. The spec is the contract.

**Review/sign-off process.** Each coordinator runs a review cycle before reporting completion. Options: spawn a code-reviewer subagent, self-review against acceptance criteria, or request orchestrator review.

## Infrastructure Dependencies

| Component              | Status      | Role in Crew                                                            |
| ---------------------- | ----------- | ----------------------------------------------------------------------- |
| helioy-bus             | Exists      | All inter-agent communication                                           |
| attention-matters (am) | Exists      | Geometric memory persistence, PreCompact sync, cross-session continuity |
| fmm                    | Exists      | Code structural intelligence for all engineering agents                 |
| mdcontext              | Exists      | Knowledge base indexing for research and design artifacts               |
| tmux                   | System tool | Process lifecycle management                                            |
| Linear MCP             | Exists      | Issue reading, status updates                                           |

## Git Isolation

Open question: do coordinators work in separate worktrees or a single working tree?

**Separate worktrees (safer)**:

- Each coordinator gets its own `git worktree`
- No file conflicts between parallel coordinators
- Orchestrator merges branches on completion
- Nancy already implements this pattern (`_start_setup_worktree`)

**Single working tree (simpler)**:

- All coordinators share the same working directory
- Works if coordinators touch different files (design + backend = safe)
- Fails if two coordinators modify the same files (two frontend tasks = conflict)

Recommendation: worktrees by default, single tree only when the orchestrator confirms non-overlapping file sets.

## Open Questions

1. **Coordinator priming**: How does the coordinator know which expert subagents to spawn for a given task? Options: (a) role tags on the Linear issue map to agent types, (b) the coordinator reads the issue and decides, (c) the orchestrator specifies agents in the bus message.

2. **Expert agent model selection**: All experts currently run sonnet. Should the coordinator be able to override this for complex tasks (promote to opus)?

3. **Parallel vs sequential experts**: When a coordinator needs both backend and frontend work within a single issue, does it spawn both as parallel subagents or sequence them?

4. **Review process**: Self-review, peer-review (spawn a reviewer subagent), or orchestrator-review? Different issues may warrant different review depth.

5. **Token budget per coordinator**: Hard ceiling via `--max-budget-usd`? Or purely threshold-based soft limits via the watcher?

6. **Failure handling**: When an expert subagent fails, does the coordinator retry (up to N times with progressively specific instructions, per msitarzewski pattern), escalate to orchestrator, or abort the task?

7. **Nancy coexistence**: Helioy Crew and Nancy serve different use cases (interactive vs headless). Can the orchestrator delegate to nancy for background tasks while managing interactive coordinators for foreground work?
