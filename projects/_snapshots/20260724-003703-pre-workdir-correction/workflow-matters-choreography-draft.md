---
title: workflow-matters choreography draft
type: projects
tags: [workflow-matters, rewrite, choreography, dag, state-machine, nancy, k8s, rust, draft]
summary: Top layer above orchestration-matters. Multi-step, multi-agent process coordination. Nancy bash is today's analog. Future direction, not yet specced for /linear-workflows; deferred until session-matters and runtime-matters land.
status: draft
project: workflow-matters
confidence: low
created: 2026-05-16
updated: 2026-05-17
related: [helioy-bus-rewrite-charter-draft, session-matters-foundation-draft, runtime-matters-kubelet-draft, session-matters-iam-draft, orchestration-matters-controllers-draft]
---

# workflow-matters choreography draft

## Draft caveat

Brainstorm artifact. Future direction marker, not a draft spec for `/linear-workflows`. Linear planning should focus on session-matters and runtime-matters first (the K8s-faithful foundation per the [charter](helioy-bus-rewrite-charter-draft.md)); orchestration-matters layers on top; workflow-matters comes after all three are stable. The deeper, focused dive that produces a v1 draft spec for this product will be a separate session once the lower layers ship.

Naming note: this draft was originally written when the foundation was called `identity-matters`. The foundation is now `session-matters` (control plane) plus `runtime-matters` (per-host kubelet) plus `identity-matters` (IAM stub). All references in this draft have been updated.

## What workflow-matters is

The **choreography layer**. Defines and executes multi-step, multi-agent processes: DAGs, state machines, handoffs, retries, resumability. Sits on top of orchestration-matters (which spawns the agents that workflows coordinate) and session-matters (the substrate).

Today's analog is the nancy bash script at `/Users/alphab/Dev/LLM/DEV/TMP/nancy/nancy` and its supporting modules. The script choreographs PM → Engineering → Reviewer handoffs across Linear-bound agents. workflow-matters formalizes this as a product with declarative workflow definitions, persistent state, and resumable execution.

## Domain

| Concept | Owned by workflow-matters? |
|---|---|
| Workflow definitions (DAGs, state machines) | Yes |
| Workflow execution state (current step, blockers, outputs) | Yes |
| Multi-agent handoffs | Yes |
| Retry policies, error handling, resumability | Yes |
| Workflow-bound supervision (workflow as supervisor for agents it spawns) | Yes |
| Spawning the agents themselves | No, orchestration-matters |
| Identity, channels | No, session-matters |

## Tech stack (assumed)

Rust 2024 edition, Cargo workspace, same patterns as session-matters and orchestration-matters. Mirrors context-matters. Details deferred to the v1 draft spec.

## Examples of workflows in the helioy ecosystem

| Workflow | Today's mechanism |
|---|---|
| Plan → Implement → Review → Ship (Linear-driven) | nancy bash + Linear MCP integration |
| Spawn warroom → dispatch tasks → collect results → kill | warroom + manual coordination |
| Edit plugin source → re-sync caches → nudge live sessions | the script being designed in `helioy-plugins/docs/superpowers/specs/2026-05-16-plugin-resync-script-design.md` |
| Document → review → publish (blog-architect) | blog-architect skill + manual cascade |
| Topic → research → draft → publish | content router + blog-architect |

A formalized workflow-matters would let any of these be declarative, persistent, and resumable.

## Sketch of v1 (high level, not yet spec)

| In scope | Out of scope |
|---|---|
| Declarative workflow definitions (TBD format) | Visual DAG editor |
| Workflow state persistence (sqlx + sqlite) | Cross-machine workflow distribution |
| Workflow as supervisor for spawned agents | Multi-tenant workflow isolation |
| MCP + CLI single binary | Web UI |
| Migration of one nancy bash workflow as a proof-point | Wholesale nancy rewrite |

## Open questions (deferred to v1 spec session)

1. **Workflow definition format.** YAML DAG? Statechart? Code-as-config?
2. **Coordination primitives.** `wait-for(agent)`, `fork-join`, `retry(n, backoff)`, `timeout`, `compensation`, `manual-gate`?
3. **State persistence.** Same store as session-matters? Own store?
4. **Observability.** CLI? Web UI? Both?
5. **Nancy migration.** Rewrite into workflow-matters definitions, or preserve nancy as one specific workflow consumer?
6. **Repository placement.** New project? Inside nancy? Inside helioy umbrella?
7. **Interaction with workflow-bound LLM behavior.** When a workflow spawns an agent with a specific role (PM, Eng), how is that role expressed in the agent's context? System prompt injection? Skill configuration? workflow-matters-owned mechanism? Probably overlaps with runtime-matters.

## Why this draft is not yet a v1 spec

workflow-matters is the most speculative product in the brainstorm and the most dependent on the layers beneath it. Specifying it before session-matters and orchestration-matters land risks designing against a substrate that will change. The right time for a v1 draft spec is after session-matters is in flight and orchestration-matters' shape is concrete.

## Related

- Charter: `helioy-bus-rewrite-charter-draft.md`
- Below (required dependency once specced): `orchestration-matters-controllers-draft.md`
- Below-below (required dependency once specced): `session-matters-foundation-draft.md`
- Today's analog (imperative): nancy bash at `/Users/alphab/Dev/LLM/DEV/TMP/nancy/nancy`
- Likely future overlap: runtime-matters (for role-based context injection)
