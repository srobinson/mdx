---
title: "Nancyr Objectives"
type: projects
tags: [nancyr, objectives, roadmap, v0.2]
summary: "North star document for nancyr — what it is, what works, what's next, when it's ready"
status: active
created: 2026-02-21
updated: 2026-02-21
project: nancyr
confidence: high
---

# Nancyr Objectives

## What is Nancyr

Nancyr is a process supervisor for Claude Code CLI sessions. It wraps `claude -p` with token budgeting, context injection (FMM codebase maps, AM geometric memory, session continuity), and real-time stream parsing — turning a bare CLI into a managed, observable, resumable autonomous agent.

## Vision

World-class autonomous agent harness. Nancy is not a coding agent — Nancy is a supervisory control system for autonomous coding agents. The agent does the work. Nancy does the orchestration, communication, isolation, and lifecycle management.

## Current State (v0.1.0)

Six-crate Rust workspace. What works today:

| Capability            | Crate         | Status                                                           |
| --------------------- | ------------- | ---------------------------------------------------------------- |
| Token budgeting       | nancy-monitor | Real-time tracking, warn at 70%, deny at 95%                     |
| Stream parsing        | nancy-driver  | Line-delimited JSON from `claude -p --output-format stream-json` |
| FMM context injection | nancy-brain   | Recursive `.fmm` sidecar scan, markdown codebase map             |
| AM memory integration | nancy-brain   | Query, feedback, buffer, salient extraction via brain.db         |
| Session journaling    | nancy-cli     | Append-only JSON, continuity context for prompt injection        |
| Prompt compilation    | nancy-brain   | Multi-context assembly (FMM + AM + journal + budget + task)      |
| Hook server           | nancy-monitor | PreToolUse interception via axum, systemMessage injection        |
| MDX reports           | nancy-brain   | YAML frontmatter + markdown audit trail                          |
| Supervisor loop       | nancy-cli     | End-to-end task execution with cleanup                           |
| CLI                   | nancy-cli     | Clap-based args, tracing, configurable thresholds                |

**Architecture**: CLI adapter pattern. Direct file-based AM access (no IPC daemon). Hook server on random port with automatic settings.local.json management and cleanup.

## Next Milestone (v0.2.0)

### Multi-issue orchestration

Run sequential tasks from Linear. Take a list of issue identifiers, execute them in order, report results back.

### Worker-orchestrator messaging (the Nancy Protocol)

Structured communication between supervisor and worker agent:

- **Directives**: Orchestrator → Worker (course corrections, wrap-up, halt)
- **Progress**: Worker → Orchestrator (status updates, completion reports)
- **Blockers**: Worker → Orchestrator (stuck, needs human input)

### Improved prompt compilation

- SPEC.md integration — generate task specifications from Linear issues
- Better token budget awareness in compiled prompts
- Context priority when budget is tight (task > memory > codebase > journal)

### Session continuity

Resume from journal. Pick up where a previous session left off using journaled state, AM memory feedback, and SPEC.md progress tracking.

## Success Criteria

Nancyr is ready when:

1. **Linear → execution**: Can take a Linear issue, generate a SPEC, execute it autonomously, and report results back to Linear
2. **Course correction**: Can receive directives mid-execution and adjust behavior without restarting
3. **Progress reporting**: Can report progress back to Linear (comments on issues, status updates)
4. **Sequential chaining**: Can chain multiple issues in sequence, carrying context between them
5. **Graceful failure**: Can detect when stuck, report blockers, and pause for human intervention

## Non-Goals (Deferred)

- **Kubernetes orchestration** — CRDs, control plane, worker pods (v0.3+)
- **Multi-provider routing** — LiteLLM-style model gateway, provider adapters
- **API gateway** — OpenAI-compatible proxy, SaaS licensing
- **Multi-worker parallelism** — WorkerPool, concurrent task execution
- **TUI** — Ratatui interface (folded into separate dae project)
- **Extension/plugin system** — Runtime-loadable components
