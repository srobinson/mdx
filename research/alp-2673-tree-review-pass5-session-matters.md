---
title: ALP-2673 Tree Review Pass 5 Findings for session-matters
type: research
tags: [session-matters, linear, moe-review, alp-2673, namespace-lifecycle]
summary: Pass 5 found two remaining issue-contract defects around retry idempotency and partial-failure test feasibility.
status: active
source: codebase-analyst
confidence: high
created: 2026-05-22
updated: 2026-05-22
---

## Executive Summary

Fresh pass 5 review of the ALP-2673 namespace-lifecycle Linear tree found two substantive remaining defects. ALP-2714 promises idempotent retry after partial delete without defining observable behavior for partial states, and ALP-2716 relies on a chmod-based partial-failure probe that is not implementation independent.

## Project Metadata

- Project: `session-matters`
- Language: Rust
- Linear project: `session-matters`
- Repo path: `/Users/alphab/Dev/LLM/DEV/helioy/littleorgans/session-matters`
- fmm index: available. `fmm_list_files` reported 98 indexed files and 14,137 LOC under `crates/`.
- Relevant tree:
  - Master: ALP-2673
  - Gate: ALP-2711
  - Execution parent: ALP-2710 Backlog
  - Workers: ALP-2712, ALP-2713, ALP-2714
  - Post execution review: ALP-2716
  - Canceled docs worker: ALP-2715

## Architecture

The reviewed tree is selector-compatible:

- ALP-2673 has direct children ALP-2711 gate and ALP-2710 Backlog.
- ALP-2710 contains ALP-2712, ALP-2713, ALP-2714, and ALP-2716.
- ALP-2711 `Execute:` line names exactly ALP-2712, ALP-2713, ALP-2714, and ALP-2716.
- ALP-2712 blocks ALP-2713, ALP-2714, and ALP-2716.
- ALP-2713 and ALP-2714 block ALP-2716.
- ALP-2716 is labeled `Post Execution Review` and blocked by the three workers.
- ALP-2715 is canceled, parentless, and outside the gate Execute set.

Relevant source structure surfaced by fmm:

- `crates/sm-cli/src/cli/delete.rs`: current delete dispatch is small, 46 LOC, with exported `run` and private `delete_agent`.
- `crates/sm-paths/src/lib.rs`: current `SmPaths` exposes `dir`, `pidfile`, `database`, and `log`; binding path accessor is not yet implemented because ALP-2712 owns it.
- Test files exist under `crates/sm-cli/tests/` and `crates/sm-daemon/tests/`, including namespace and selector coverage.

## Key Patterns

- Multi-step mutating operations need explicit transaction or recovery semantics. `sm delete namespace` is not one operation; it sequences cascade termination, catalog removal, and binding clear.
- Test acceptance criteria must name the risk they cover. `just test` alone does not prove new edge cases are tested.
- Permission-based failure probes should not assume a specific implementation strategy. On Unix, file write bits do not reliably make unlink or rename fail because those operations are controlled by the parent directory permissions.

## Detailed Findings

### Finding 1: ALP-2714 retry idempotency is underspecified after partial delete

ALP-2714 defines a Partial-failure contract with two paths: atomic rollback across cascade, catalog removal, and binding clear, or best-effort completion with operator-visible state. It also states that failed deletes surface the failed sub-operation and that retry is idempotent.

The observable behavior is incomplete for best-effort states. If cascade and catalog removal complete, then binding clear fails, a retry of `sm delete namespace foo` may see `foo` as nonexistent. ALP-2714 observable behavior #5 says deleting a nonexistent namespace returns a clear error with no mutation. That conflicts with the retry promise because the stale binding may remain unrepaired.

Recommended change:

- Add explicit retry outcomes for each partial state in ALP-2714, especially catalog absent plus binding still pointing at the deleted namespace.
- Preserve the normal `nonexistent` behavior for a genuinely unknown namespace, but define how a retry detects or repairs a stale binding caused by the previous failed delete.
- Mirror this in ALP-2716 partial-failure review criteria.

Bus sign-off sent:

> I sign off conditional on the following changes: item 1, ALP-2714 must define retry observables for partial deletes.

### Finding 2: ALP-2716 chmod-based partial-failure probe is not implementation independent

ALP-2716 partial-failure probe says to revoke write permission on `$SM_HOME/namespace` with `chmod -w $SM_HOME/namespace`, then invoke `sm delete namespace foo`.

That probe only fails reliably if binding clear opens and writes that existing file. If the implementation clears by unlinking, renaming a temp file over it, or replacing parent-directory entries, the file's write bit is not the controlling permission on Unix. Parent directory permissions control unlink and rename. Therefore the probe is not implementation independent and may pass or fail for reasons unrelated to the contract.

Recommended change:

- Reframe chmod as an example or manual smoke probe only.
- For ALP-2714 AC #9, require deterministic fault injection or harness-controlled failure for at least one partial-failure path, where feasible.
- If deterministic injection is out of scope for this worker, adjust ALP-2714 AC #9 and ALP-2716 to require manual PER evidence for partial-failure behavior instead of mandatory automated chmod coverage.

Bus sign-off sent:

> I sign off conditional on the following changes: item 2, PER ALP-2716 partial-failure probes should not depend on `chmod -w $SM_HOME/namespace` as the test mechanism.

### Clean probes

The following checks were clean against live Linear and cm state:

- Universal issue shape and selector-compatible hierarchy.
- Gate Execute set and Backlog children match.
- Gate required order matches Linear `blocks` / `blockedBy` relations.
- ALP-2715 cancellation cleanup is intact.
- ALP-2711 design-call resolutions are restated in the active workers after pass 4.
- cm references exist and characterize the decisions accurately:
  - `019e4bef-5516-7581-8796-2ade42965aff`: body ratify outcome.
  - `019e4c03-7c45-7533-8143-d7ca48658efd`: tree review pass 1.
  - `019e4c11-8c68-76a1-8c44-652355dd6ed1`: tree review pass 2.
  - `019e4c1e-ef40-7130-8722-b8d2703a11c0`: tree review pass 3.
  - `019e4c2d-a0d6-7ba0-bd36-7c524cb7fbf8`: tree review pass 4.
- Master ALP-2673 binding storage and gate ALP-2712 daemon-side lookup framing match.
- PER master close-out language points to the selector closure rule; no separate owner ambiguity was material enough to block pass 5.

## Dependencies

- Linear is the source of truth for the issue tree and dependency relations.
- `helioy-tools:linear-workflows` defines selector-compatible shape, gate Execute semantics, corrective issue authorization, and selector closure.
- cm stores pass history and decision records.
- fmm provides structural source checks for Rust file topology and symbols.

## Relevance to Helioy

This pass reinforces two reusable planning checks for Helioy Linear gates:

1. Any issue that says "retry is idempotent" should enumerate retry-visible states after each partial mutation.
2. Any PER probe that uses chmod or filesystem permissions should state whether it is a manual example, an automated acceptance requirement, or only one acceptable fault-injection mechanism.

## Open Questions

- Should ALP-2714 prefer a durable delete operation journal for retry repair, or should retry repair be limited to observable stale binding cleanup?
- Should ALP-2716 require automated fault injection for partial-failure coverage, or explicitly allow manual PER evidence for that one path?

## Peer Consensus Update

Peer pane `session-matters:helioy-tools:codebase-analyst:1:2.1` independently ratified both pass 5 findings. Consensus summary was relayed to the orchestrator on topic `2673-tree-review-pass5`.

Consensus conditions:

1. ALP-2714 must define retry observables for partial-delete states. The peer sharpened the finding: path B best-effort recovery guidance conflicts with the blanket `retry is idempotent` statement unless the retry either recognizes orphan binding state or the contract says partial-state cleanup is operator-driven.
2. ALP-2716 / ALP-2714 AC #9 must replace or qualify the chmod probe. The peer confirmed the distinction between chmod-based read failure coverage and binding-clear failure, where unlink and rename depend on parent directory permissions. Acceptable repairs include parent-directory permission revocation, deterministic fault injection, or demoting chmod to a manual example.

Both panes agreed the remaining probes were clean: selector shape, gate Execute, blockedBy chain, ALP-2715 cancellation cleanup, cm references, master/gate storage framing, corrective state machine, and PER close-out semantics.

## Closure Update

The orchestrator applied both pass 5 consensus changes and requested a live re-read of ALP-2714 and ALP-2716. Re-fetch confirmed both defects are resolved.

- ALP-2714 now defines operation-idempotent retry with three explicit cases: catalog present, catalog absent plus binding points at the name, and true nonexistent. The observable behavior and acceptance criteria now distinguish retry cleanup from normal nonexistent behavior.
- ALP-2716 now treats chmod as example-only, rejects chmod-based automated proof for binding-clear failure, and requires deterministic harness-controlled fault injection in ALP-2714 AC #10 and PER test-coverage verification.

Clean sign-off sent to orchestrator: `I sign off on ALP-2673 tree as currently filed.`

## Peer Clean Sign-off Update

Peer pane `session-matters:helioy-tools:codebase-analyst:1:2.1` also re-read live ALP-2714 and ALP-2716 after the orchestrator edits and emitted the exact clean sign-off: `I sign off on ALP-2673 tree as currently filed.`

Pass 5 therefore closed with round-2 clean consensus from both panes. Per the MoE workflow, this is not the exit condition because exit requires round-1 zero findings. Pass 6 follows.

