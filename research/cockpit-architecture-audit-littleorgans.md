---
title: Cockpit Architecture Audit for littleorgans
type: research
tags: [littleorgans, cockpit, architecture, audit, moe, session, schedule, transport]
summary: Phase A converged on six edits and Phase B clean sign-off was sent after live-doc verification confirmed the remnants were patched.
status: active
source: codebase-analyst
confidence: high
created: 2026-05-31
updated: 2026-05-31
---

## Executive Summary

The cockpit architecture draft passed Phase B after the writer patched the remaining consensus remnants. Live-doc verification confirmed the `lilo run` target-state wording, workflow layering, transport policy ownership, capture persistence boundary, schedule status, and agent-matters wording are now aligned with the MoE consensus.

## Project Metadata

- Primary repo: `/Users/alphab/Dev/LLM/DEV/helioy/littleorgans/littleorgans`
- Language: Rust workspace
- Indexed state: `.fmm.db` present and `fmm validate` passed for 365 files, 48,763 LOC.
- Relevant sibling repos:
  - `/Users/alphab/Dev/LLM/DEV/helioy/agent-matters`, Rust. `.fmm.db` exists but schema is stale for the current fmm binary.
  - `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters`, Python plus TypeScript. `fmm validate` passed for 374 files, 66,896 LOC.
- Artifact audited: `/Users/alphab/.mdx/projects/littleorgans-cockpit-architecture.md`, 429 lines.
- Bus topic: `cockpit-arch-signoff`.

## Architecture Checked

- `lilo` command surface is rooted in `crates/lilo/src/cli/mod.rs` and delegates session verbs to `internal/session/app/src/cli`.
- Session CLI definitions live in `internal/session/app/src/cli/cli_def.rs`.
- `lilo create session` and `lilo run` both dispatch to the same spawn path in `internal/session/app/src/cli/run.rs`.
- Session daemon spawn persists pending intents and session records in `internal/session/daemon/src/handler/spawn.rs`.
- Runtime and session daemon reconciliation exist today through `internal/runtime/daemon/src/reconcile.rs` and `internal/session/daemon/src/reconcile.rs`.
- `schedule-matters` is greenfield. fmm shows no `internal/schedule`, and project instructions reserve schedule without a crate, daemon, or command namespace in v0.8.0.


## Phase B Verification Status

Final live doc reread on 2026-05-31 passed after orchestrator patch `M|apply2`.

Verified against `/Users/alphab/.mdx/projects/littleorgans-cockpit-architecture.md`:

1. Section 6 now separates current code from target state: current `lilo create session` and `lilo run` both route through `spawn_session`, while target `lilo run` is imperative single-agent create-and-place and only the explicit existing-pane variant is exec-shaped.
2. Sole placement wording now says `lilo run` asks schedule-matters to place an agent, not mutate an existing pane.
3. The decisions log now records `lilo run` as create-and-place, with explicit existing-pane variant exec-shaped.
4. The component map now says agent-matters compiler model is decided and littleorgans integration is open.
5. The decisions log now says the settings adapter renders role policy into each CLI config.
6. A stale-phrase sweep found no remaining `imperative single-agent mutation`, `writes into it`, `needs its own design session`, `transport-matters and schedule-matters`, or `scaffold` matches. The only `direct schedule producer` match is the expected decision-log statement that workflow-matters is not a direct schedule producer.

Clean sign-off sent to `helioy:orchestrator` on topic `cockpit-arch-signoff`: `I sign off on the cockpit architecture doc as currently filed`.

## Key Patterns

- Keep workflow above orchestration. Workflow should trigger orchestrator runs, not produce placement requests directly.
- Keep schedule-matters blind. It owns placement mechanics only, not transcript, restart, capture, or orchestration policy.
- Keep agent-matters as the policy compiler. Per CLI adapters render role policy into CLI config. transport-matters may intercept wire traffic, but it should not own security policy.
- Treat transcript persistence as a boundary decision, not an implementation detail. The doc already implies raw artifacts, canonical model, CLI jsonl tailing, and SQL read models.

## Detailed Findings

### F1. Section 6 needs current state versus target state wording

The draft says `lilo create session` files a declarative multi-agent request and does not create a session. Live code does not match that present tense claim yet.

Evidence:

- Draft lines 121 to 143: `create session` is described as a declarative, multi-agent request, while only `lilo run` is explicitly called interim.
- `internal/session/app/src/cli/run.rs:29-39`: `create_session` calls `spawn_session(args, "headless", false, ...)`.
- `internal/session/app/src/cli/run.rs:41-99`: `spawn_session` sends `SessionRpc::Spawn`.
- `internal/session/daemon/src/handler/spawn.rs:64-90`: daemon completes spawn and persists a session after runtime spawn.
- `cargo run --quiet -p lilo -- create session --help`: help says `Declaratively create a headless session record`, not multi-agent manifest request.

Converged fix:

- Mark section 6 as target state, not current behavior.
- Say both current `create session` and `run` still route through session spawn until schedule-matters lands.
- Add manifest and multi-agent cutover to section 12 open items.
- Fix the analogy table. Target `lilo run` is imperative single-agent create/place, closer to `kubectl run`; only an explicit already-existing pane mode is exec-shaped.

Severity: medium.

### F2. Section 8 lets workflow bypass orchestration into schedule

The draft defines workflow-matters as a thin DAG of orchestrators, then later lists workflow-matters as a direct producer of schedule requests. That makes workflow both the flow layer and a placement producer, which weakens the downward dependency rule and makes orchestration less authoritative.

Evidence:

- Draft lines 253 to 258: workflow-matters is a DAG whose nodes are orchestrators.
- Draft lines 262 to 272: workflow-matters is listed among producers of schedule requests.

Converged fix:

- Remove workflow-matters from direct schedule producers.
- State that workflow triggers orchestrators, and orchestration requests placement.
- Keep `lilo` CLI and orchestration-matters as schedule request producers.

Severity: medium.

### F3. Workflow-matters needs a crisp differentiator from hierarchical orchestration

The draft says an orchestrator can contain sub-orchestrators, and workflow is a DAG of orchestrators. Without a sharper boundary, workflow-matters risks becoming a duplicate orchestration layer.

Evidence:

- Draft lines 242 to 243: an orchestrator can coordinate agents or sub-orchestrators.
- Draft lines 253 to 258: workflow is a DAG of orchestrators.
- Draft lines 274 to 276: workflows and orchestrators may cross-reference while resolved runs must be DAGs.

Converged fix:

- Define orchestration as one live coordinated session with a conductor, shared context, gates, capture, mail, and nudge.
- Define workflow as a DAG of independent orchestrator runs with handoff at edges and no shared live session.
- Define sub-orchestrators as nested conductors inside one live coordinated session.
- Define workflow nodes as independent orchestrator runs.

Severity: medium.

### F4. Transport-matters is two-way, but tool and menu suppression should not route through it

The draft says menus do not arise because littleorgans controls built-in tools through transport-matters. That conflicts with the same section's claim that security is a policy-to-settings compiler rather than runtime interception.

Evidence:

- Draft lines 73 to 80: tool/menu suppression is attributed to transport-matters, then security is declared non-intercepting policy compiled into CLI settings.
- Draft lines 391 to 393: decisions log says agent integration is drive and tail, and security is policy-to-settings.
- transport-matters README lines 5 and 111 to 115: transport-matters proxies traffic and can pause, inspect, edit, and release outbound requests.
- `api/src/transport_matters/breakpoint.py:1-4`: breakpoint state machine pauses mid-flight and allows inspection and edit before forwarding.

Converged fix:

- Attribute menu and tool suppression to compiled CLI settings generated from the agent-matters role policy.
- Describe transport-matters as two-way wire capture and intercept where relevant.
- Do not make transport-matters the owner of security policy or built-in tool control.

Severity: medium.

### F5. Transcript service ownership and persistence split need an explicit open item

The draft implies a CLI jsonl tailer, SQL persistence, a canonical model, and dual HTTP-over-wire plus CLI-jsonl capture, but section 12 only says capture-and-sync placement is open. It also names the wrong neighbor, schedule-matters. Capture is a session-matters primitive keyed by session-id; schedule-matters is placement-only.

Evidence:

- Draft lines 82 to 85: tail CLI session files, normalize them, write SQL, sync UI.
- Draft lines 220 to 225: session-matters owns capture as a primitive.
- Draft lines 338 to 347: open item says capture-and-sync service placement is between transport-matters and schedule-matters.
- Draft lines 360 to 375: dual capture path, HTTP over wire via transport-matters plus CLI jsonl via transcript service, then asks where canonical transcript store lives.
- `transport-matters` README lines 92 to 99: current implementation persists run-scoped artifact bundles, original outbound request, parsed IR, curated outbound request, audit metadata, and transport diagnostics.
- `api/src/transport_matters/storage/base.py:151-165`: `ExchangeArtifacts` stores raw request, parsed request IR, curated raw and IR, response raw and IR, transport artifacts, events, and turn summary.
- fmm for littleorgans shows session store is SQLite under `internal/session/store/src/sqlite`.

Converged fix:

- Rename open item 2 to `Transcript service owner and persistence model`.
- Replace `between transport-matters and schedule-matters` with transport-matters to session-matters.
- Include session identity, transport canonical model, CLI jsonl tailing, Postgres raw/canonical storage, and local SQLite read model.
- Do not mark the storage split decided until those boundaries are written.

Severity: medium.

### F6. Component map overstates schedule-matters status

The component map says schedule-matters is a scaffold. That is too strong for current repo state.

Evidence:

- Draft line 326: schedule-matters status is `scaffold`.
- fmm `internal/` topology shows only `db`, `identity`, `port`, `runtime`, `session`, and `wire`.
- `/Users/alphab/Dev/LLM/DEV/helioy/littleorgans/schedule-matters` exists but is empty.
- Project instructions say schedule is reserved only and has no crate, daemon, or command namespace in v0.8.0.

Converged fix:

- Change schedule-matters status to `reserved / greenfield (no crate yet)`.

Severity: medium.

### F7. Minor wording and consistency edits

These are low severity but should be included in the writer patch.

Evidence and fixes:

- Draft line 89 says the settings adapter writes into agent-matters, while lines 213 to 215 say agent-matters renders into each engine config. Reword to `renders the role's policy into each CLI config`.
- Draft lines 340 to 342 say agent-matters needs its own design session, but lines 425 to 429 already decide resolve/compile/use and content-addressed runtime home activation. Sibling `agent-matters` PROJECT.md lines 17 to 42 confirm resolve, compile, and use workflows. Narrow the open item to littleorgans integration specifics.
- Section 2 uses upward arrows while section 8 uses produces-down arrows. Use one convention.

Severity: low.

## Dependencies

- `fmm` provided structural validation for the littleorgans repo and transport-matters.
- Cargo was used to render current CLI help for `lilo --help`, `lilo create session --help`, and `lilo run --help`.
- Direct shell inspection was used for sibling `agent-matters` because its `.fmm.db` schema is stale for the current fmm binary.
- helioy-bus carried Phase A peer debate and convergence.

## Relevance to Helioy

The audit protects the cockpit stack from ambiguous control-plane ownership. The critical corrections keep workflow out of direct placement, keep schedule-matters blind and mechanical, keep security policy in agent-matters rather than transport-matters, and make transcript persistence ownership explicit before multiple substrates start writing overlapping capture state.

## Open Questions

- None for the Phase B sign-off.
- Future work remains only in the architecture doc's own open questions.
