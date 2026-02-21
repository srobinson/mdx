---
title: Nancy Codex Support V1 Specification
type: projects
tags: [nancy, codex, claude, runtime, spec, cli]
summary: V1 plan for adding Codex as a first class Nancy harness on the live `./nancy` and `./nancy go <issue>` paths.
status: active
created: 2026-04-17
updated: 2026-04-17
project: nancy
confidence: high
related: [nancyr-objectives]
---

# Nancy Codex Support V1 Specification

## Purpose

Add Codex support to `nancy` without dragging Claude specific assumptions through the entire execution path.

The target is narrow and operational:

- `./nancy`
- `./nancy go <linear issue ref>`

Those are the only paths that matter for V1.

## Problem

Nancy already has the beginnings of a driver abstraction, but the real execution path still assumes Claude semantics in several places.

Observed coupling on the live path:

- `start.sh` assumes Claude specific review configuration and behavior
- sidecar behavior is designed around Claude terminal UI markers and slash commands
- role handling assumes Claude subagent semantics
- driver loading is nominally generic, but the worker lifecycle is still shaped around the incumbent harness

That means Codex support cannot be delivered safely by only adding `src/cli/drivers/codex.sh`. The execution path must ask the selected harness what it supports.

## Goals

- support Codex on `./nancy`
- support Codex on `./nancy go <issue>`
- preserve the existing Claude path
- keep harness specific behavior inside drivers or harness scoped modules
- define a clear V1 capability contract for harnesses
- produce a work breakdown that maps cleanly into Linear issues

## Non Goals

- dead code cleanup outside the live path
- watcher and inbox modernization
- Codex sidecar parity in V1
- reworking unrelated orchestration panes
- broad architecture rewrite

## Scope Boundary

This specification applies only to the direct `nancy` entrypoints below.

### Included

- `./nancy`
- `./nancy go <issue>`
- CLI detection and setup for Codex
- worker prompt execution via the active harness
- review execution via the active harness, if the driver declares support

### Excluded

- legacy or redundant code paths outside the two entrypoints above
- watcher injection and notification dead code
- Codex specific pane automation beyond what is required for the live path

## Current State

The current branch already contains part of the baseline:

- Codex CLI detection can be added to dependency checks
- a `src/cli/drivers/codex.sh` driver can implement `run_interactive` and `run_prompt`
- token parsing can be extended to understand Codex usage events

That baseline is useful, but it is not sufficient.

The main remaining problem is execution ownership. `start.sh` still knows too much about Claude.

## Design Principles

1. Harness boundary must be explicit.
2. `start.sh` should orchestrate workflow, not encode Claude policy.
3. Driver capabilities should be queried, not assumed.
4. V1 should prefer correct execution over feature parity.
5. Sidecar support should be harness scoped.

## Target Design

## 1. Harness Contract

Nancy should treat each harness as a driver with a required execution surface and an explicit capability surface.

### Required driver functions

- `detect`
- `version`
- `name`
- `init_session`
- `run_interactive`
- `run_prompt`

### Required capability functions

- `supports_sidecar`
- `supports_review_agent`
- `supports_agent_role`
- `supports_resume`
- `supports_export`

Optional capability helpers may be added later, but V1 should not add more than needed.

## 2. Start Flow Ownership

`src/cmd/start.sh` should own workflow sequencing only:

- render prompt
- initialize session
- decide whether sidecar is allowed
- execute worker prompt
- decide whether review is allowed
- advance loop or stop

It should not own harness specific configuration such as Claude config directories or Claude print mode flags.

Those choices belong to the driver.

## 3. Review Execution

Review should become a generic driver mode.

The workflow requirement is simple:

- run review prompt
- stream output if supported
- exit cleanly when review is complete

Implementation can differ by harness.

For Claude, that may still map to stream JSON print mode.
For Codex, that may map to `codex exec --json`.

The important invariant is that `start.sh` requests review behavior generically and the driver implements it.

## 4. Sidecar Policy

Sidecar behavior must be declared by the active harness.

### Claude

- supports sidecar in V1
- current sidecar behavior remains enabled

### Codex

- sidecar is disabled in V1
- worker execution still proceeds
- loop progression depends on process exit rather than pane automation

Codex specific sidecar support can be a later phase once the base harness path is stable.

## 5. Agent Role Policy

Agent role handling must also be capability gated.

### Claude

- can consume role aware flags or agent mappings

### Codex

- V1 should assume no role specific runtime flag unless proven necessary
- role may remain part of prompt content without becoming a CLI flag

This prevents `start.sh` from assuming that every harness has a Claude style subagent model.

## 6. Acceptance Criteria

Codex support is complete for V1 when all of the following are true:

1. `nancy setup` can detect and report Codex as an available CLI.
2. `./nancy` can launch using Codex as the selected harness.
3. `./nancy go <issue>` can run the worker through Codex without falling back to Claude specific logic.
4. The worker loop does not attempt to start the sidecar when the active harness does not support it.
5. Review execution is controlled by driver capability and exits cleanly.
6. Token usage parsing does not break when Codex emits usage records.
7. Claude behavior on the same paths still works.

## Implementation Plan

## Phase 1. Freeze the harness capability contract

Change:

- define the minimal capability functions in the driver layer
- document expected return values

Result:

- `start.sh` can branch on harness support instead of harness name

## Phase 2. Refactor `start.sh` onto capabilities

Change:

- remove direct Claude review wiring from `start.sh`
- gate sidecar startup on `supports_sidecar`
- gate role flags on `supports_agent_role`
- gate review execution on `supports_review_agent`

Result:

- the worker loop becomes harness aware without embedding Claude assumptions

## Phase 3. Complete the Codex driver

Change:

- implement the full required function surface in `src/cli/drivers/codex.sh`
- ensure prompt execution, export behavior, and streaming review behavior work through the driver contract

Result:

- Codex becomes a supported harness on the live path

## Phase 4. Validate the two real entrypoints

Change:

- test `./nancy`
- test `./nancy go <issue>`
- confirm Claude regression coverage on the same path

Result:

- V1 can ship with confidence

## Linear Breakdown

This work should be split into the following issues.

### 1. Define Nancy harness capability contract

Deliverables:

- required driver capability functions
- short driver contract doc in code comments or adjacent docs
- call sites updated to use the contract entrypoints

### 2. Refactor worker loop to consume harness capabilities

Deliverables:

- `start.sh` no longer hardcodes Claude review semantics
- sidecar startup capability gated
- role handling capability gated

### 3. Complete Codex driver for Nancy V1

Deliverables:

- Codex interactive execution
- Codex prompt execution
- Codex review mode support
- export and token handling aligned with the contract

### 4. Validate live path behavior for Claude and Codex

Deliverables:

- smoke coverage for `./nancy`
- smoke coverage for `./nancy go <issue>`
- confirmation that Claude still works on the same path

## Open Questions

These should be resolved during implementation, not before starting.

1. Does Codex need any session persistence behavior beyond what V1 requires for the worker loop?
2. Should review output formatting be normalized at the driver layer or in shared CLI formatting code?
3. Does Codex need a dedicated export fallback when `--output-last-message` is insufficient for Nancy session persistence?

## Recommendation

Ship Codex support in two stages.

Stage one is a clean harness contract plus operational support for `./nancy` and `./nancy go <issue>` without Codex sidecar automation.

Stage two, if needed, is Codex specific sidecar behavior once there is evidence that autonomous looping under Codex needs the same pane level intervention Claude currently uses.
