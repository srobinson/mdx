---
title: What does a workflow contract treat as state?
slug: workflow-contract-state
status: review
account: knowmorecontext
surface: blog
type: teardown
created: 2026-05-02
updated: 2026-05-02
post_date:
post_url:
campaign:
related: []
---

# What does a workflow contract treat as state?

OpenAI shipped Symphony in late February. About 5,500 lines of Elixir, a 2,169-line normative spec, and a working orchestrator that points Codex at Linear issues. I read it because I have my own answer to the same problem and wanted to see how somebody else solved it.

My answer lives at `~/.codex/skills/linear-workflows`. Three short markdown files describing how Codex and Claude take turns on a Linear graph.

Reading Symphony with that comparison in mind, one question kept dragging the whole architecture behind it. The question is what each design treats as durable state.

## Where the contract lives

Symphony's contract for agent behaviour is a single file. The repo it manages contains `WORKFLOW.md`, with YAML front matter for runtime settings and a Liquid body that renders into the agent's prompt. There is real engineering around it. `workflow_store.ex` polls the file's modification time on a one-second tick. When the file changes, the store reloads it. If the new version fails to parse, the store falls back to the last good version. Hot reload with a safety net.

The orchestrator treats that file as the source of authority for what agents do.

Helioy's contract for agent behaviour lives in the Linear issue graph. Issue descriptions, statuses, parent-child relations, blocking relations. The skill that defines how agents read and write that graph is short. Three markdown files in `~/.codex/skills/linear-workflows/workflows/`, plus a one-page `SKILL.md` routing them.

The opening line of that `SKILL.md` reads: "Linear is the durable planning substrate. HANDOVER.md and other local files are coordination state only."

The choice underneath both designs is whether durable state lives in a file or in a graph. Symphony picks the file. Helioy picks the graph. Everything downstream follows from that.

## Loop shape

Symphony's loop has one role. The orchestrator pulls Linear issues, renders the WORKFLOW.md prompt with issue context, hands the result to Codex, watches the run, and writes results back. One agent does the work. The orchestrator schedules and supervises.

Helioy's loop has two roles, asymmetric on purpose. Codex authors. Claude reviews. The planning gate file describes a pattern where Codex creates or updates one focused planning issue at a time, and Claude reviews each one before any execution starts. Every review turn ends with one explicit action recorded in Linear, drawn from a small set the workflow names.

The issue rules are stable across all three workflow files. An issue should be completable by one autonomous agent in one session. References point to files, modules, or symbols rather than line numbers. Dependencies are encoded as Linear relations when order matters. The reviewer marks the source planning issue Worker Done when accepted; Backlog issues stay Todo until the gate review authorizes them.

## Outcomes

Symphony's run-time outcomes are implicit. The orchestrator reconciles against Linear, retries with bounded exponential backoff, and runs until issues complete or fail. There is no formal "outcome of this gate" in the spec. The gate is the orchestrator state.

Helioy names its outcomes. Every planning gate ends in exactly one of three:

- Ready For Execution. The Backlog contains a reviewed executable set, no prerequisite blockers required. The outcome carries authorized issue identifiers and required order.
- Pre Execution Blockers Required. Prerequisite work must land before downstream planning is reliable. The outcome names the blocker issues.
- Needs Human Direction. The two agents cannot reach a defensible shared position. The outcome records the unresolved question, both positions, the consequences, and the smallest decision the human must make.

Named outcomes are only legible because the substrate already encodes them. The Linear graph holds the next-action state across sessions and across agents. A new outcome value at gate close becomes a queryable property of the graph. On a file substrate, the same names would require inventing a state machine the file cannot enforce.

## What is surprising

The choice between a file and a graph as durable state cascades through everything else.

Symphony has to invent hot reload with last-known-good because `WORKFLOW.md` is mutable state under a running orchestrator. Saving the file mid-run could leave the system inconsistent, so the store catches parse failures and rolls back. The graph substrate handles concurrency at the storage layer. HANDOVER.md does not need to be durable because Linear already is.

Symphony has one role driving an issue because a file does not naturally support two writers. Two roles writing to the same file at once is a merge conflict waiting to happen. The graph substrate makes a two-role loop natural. The author writes one issue, the reviewer reads it and writes a state change back, and the storage layer keeps them consistent.

The named outcomes only become legible when the substrate already encodes "this gate is in state X with these dependencies." Inventing that on top of a file means inventing a state machine the file does not support. Symphony does not name its outcomes the way Helioy does, and reading the spec, I cannot tell whether the team chose not to or simply could not without changing the substrate.

Two paragraphs deep into the SPEC.md, the file-as-state choice was already locked. Everything described above is downstream of that one decision.

## Implication

Reading Symphony with Helioy in mind, the lesson is that when reading someone else's design, the substrate question goes first. What does this treat as durable state? The rest follows.

Symphony's spec is excellent at what it scopes. The Linear coupling at the tracker layer is called out explicitly. The in-memory scheduler with no persistent state across restarts is called out as a deliberate ceiling. The team documented their choices in normative language, in a 2,169-line file written specifically so somebody else can reimplement from it.

Sitting next to that, the linear-workflows skill is the cheaper design. Three short markdown files plus the Linear graph carry what Symphony's `WORKFLOW.md` plus `workflow.ex` plus `workflow_store.ex` plus `prompt_builder.ex` carry. The skill picks up replay, multi-agent review, and named outcomes as a side effect of the substrate choice.

Now I am wondering which other subsystems quietly chose file-as-state when graph-as-state was already available. Configuration files, agent prompt templates, plan documents, run journals. The cost of that choice stays invisible until somebody holds one design next to another and notices what each one had to invent to get back what the other got for free.

I publish teardowns at knowmorecontext.substack.com. Token matters.
