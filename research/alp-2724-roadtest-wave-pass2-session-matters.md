---
title: ALP-2724 Road-Test Wave Pass 2 Review
type: research
tags: [session-matters, linear, moe-review, cli, nancy]
summary: Fresh-eyes pass 2 found PER scope mirroring, verification teardown, shared help-source grounding, and schedule-matters breadcrumb gaps in the ALP-2724 road-test corrective wave.
status: active
source: codebase-analyst
confidence: high
created: 2026-05-22
updated: 2026-05-22
---

## Executive Summary

Pass 2 reviewed the ALP-2724 road-test corrective wave in Linear against the live gate body, worker bodies, dependency graph, and current worktree source. The wave is close, but four substantive issues remain before clean sign-off: the terminal PER is frozen against the original cycle, live-daemon verification lacks teardown discipline, `tools/_shared.toml` is referenced as established but does not exist at HEAD, and ALP-2746 needs breadcrumbs for the future schedule-matters re-scope.

## Project Metadata

- Project: `session-matters`
- Worktree: `/Users/alphab/Dev/LLM/DEV/helioy/littleorgans/session-matters-worktrees/nancy-ALP-2724`
- Language: Rust
- Build system: Cargo plus `just`
- Gate required before completion: `just check && just build && just test`
- fmm status: `.fmm.db` exists, but `fmm_file` tooling reported schema mismatch and `fmm validate` reported 105 files stale. Source checks therefore fell back to shell filesystem inspection for this pass.

## Architecture and Review Surface

- Master parent: `ALP-2724`, status `Worker Done`.
- Gate review issue: `ALP-2726`, status `Worker Done`.
- Execution parent: `ALP-2725`, status `Todo`.
- Road-test corrective wave under review: `ALP-2743`, `ALP-2744`, `ALP-2745`, `ALP-2746`, `ALP-2747`, `ALP-2748`, `ALP-2749`, `ALP-2752`.
- Terminal review issue referenced by the gate: `ALP-2733`.

The gate body's authorization line includes the full road-test wave and `ALP-2747` last. `ALP-2747` has live `blockedBy` relations to `ALP-2743`, `ALP-2744`, `ALP-2745`, `ALP-2746`, `ALP-2748`, `ALP-2749`, and `ALP-2752`, matching the intended final audit order.

## Detailed Findings

### 1. ALP-2733 PER scope mirroring is broken

`ALP-2733` was fetched live and is already `Done`. Its body mirrors the original ALP-2724 cycle only: original shape A CRUD work, help-source decomposition, docs, and original source stubs. It does not cover the road-test wave surfaces:

- `ALP-2743`: `sm get` singular command plus plural alias collapse.
- `ALP-2744`: leaf-help bare invocation, selector grammar source, and vertical layout.
- `ALP-2745`: label metadata model and `sm get session --show-labels`.
- `ALP-2746`: interim alias symmetry between `sm create session` and `sm run`.
- `ALP-2748`: `sm capture <SESSION_ID>` and broad-selector rejection.
- `ALP-2749`: selector argument shape rule.
- `ALP-2752`: removal of `sm link` from CLI and MCP surfaces.
- `ALP-2747`: full final help audit umbrella.

This contradicts `ALP-2726`, which says `ALP-2733 PER replays after the road-test wave lands`. The fix is to reopen and amend `ALP-2733`, or create a new post-road-test PER under `ALP-2725`, then update the gate authorization and order lines so the terminal review blocks on the whole road-test wave and mirrors each new acceptance surface.

### 2. Live-daemon verification lacks preconditions and teardown

Several workers require mutable live state:

- `ALP-2745` needs a running daemon with at least one labeled session.
- `ALP-2746` needs two session creation paths and persisted record comparison.
- `ALP-2748` needs a live captureable session.
- `ALP-2752` needs daemon MCP tool advertisement proof.
- `ALP-2747` audits the integrated help and residual surfaces after all narrow workers land.

The bodies state manual proof commands but not uniform setup and cleanup. `ALP-2746` also uses `tmux:1:3.1` for both `sm create session` and `sm run`; that can collide unless the worker uses distinct targets or tears down between commands. Each affected verification section should require explicit setup and teardown: start or identify the daemon, create temporary sessions, labels, run directories, and targets, record created ids, delete or stop created sessions, close opened panes or use safe targets, and stop any daemon started only for verification.

### 3. `tools/_shared.toml` is asserted but absent at HEAD

The ALP-2744 body and ALP-2726 help-source layout resolution refer to `tools/_shared.toml` as the shared-content TOML source for selector grammar. Live filesystem check showed no such file at HEAD. Current root `tools/` files are:

- `tools/capture.toml`
- `tools/doctor.toml`
- `tools/label.toml`
- `tools/link.toml`
- `tools/logs.toml`
- `tools/mail.toml`
- `tools/nudge.toml`
- `tools/run.toml`
- `tools/session.toml`
- `tools/wait.toml`

ALP-2744 can create `tools/_shared.toml`, but the current wording implies ALP-2735 already established it. Amend ALP-2744 to state that it introduces or creates the shared source as part of the worker, and adjust gate wording if needed so the dependency chain is grounded in current source.

### 4. ALP-2746 needs future schedule-matters breadcrumbs

ALP-2746 correctly implements the current interim model: `sm create session` and `sm run` are aliases until `schedule-matters` provides reconciliation semantics. The future re-scope will remove or rewrite `--target`, `--detach`, and `--force` from `sm create session`, so the worker should leave explicit breadcrumbs now:

- Named tests for the interim alias-symmetry contract.
- A docs anchor stating the schedule-matters split point.
- A nearby source or help-source note at the shared argument definition identifying which `sm create session` flags are interim pending `schedule-matters`.

Without these breadcrumbs, the future declarative re-scope becomes archaeology across shared argument code, help TOML, tests, and docs.

## Key Patterns

- Terminal PER issues must mirror the final authorized worker set, not just the original cycle before corrective waves were added.
- Manual proof that creates daemon records, labels, panes, or MCP daemon state should always specify teardown.
- Gate prose should distinguish current source from worker-created future source. Calling a missing file “gate-bound” is acceptable only if the worker is clearly responsible for creating it.
- Interim architecture decisions need durable breadcrumbs where future removal will happen.

## Dependencies

- Linear issue bodies and relations fetched live via MCP for `ALP-2724`, `ALP-2725`, `ALP-2726`, `ALP-2733`, and `ALP-2743` through `ALP-2749`, plus `ALP-2752`.
- Local filesystem check of `tools/` and fmm validation in the ALP-2724 worktree.

## Relevance to Helioy

This review protects Nancy's selector flow and Helioy's CLI planning discipline. The main reusable lesson is that corrective waves must re-authorize and re-scope terminal review issues, not merely append workers ahead of an already-completed PER.

## Open Questions

- Whether the orchestrator prefers reopening `ALP-2733` or filing a new post-road-test PER.
- Whether `tools/_shared.toml` should be the canonical shared-content filename or whether ALP-2744 should choose a different schema-compatible shared source name during implementation.

## Final Pass 2 Sign-off Update

After the orchestrator applied the four round-1 consensus items, live Linear re-fetch verified the final state:

- `ALP-2733` is reopened to `Todo`, blocks on `ALP-2732` and `ALP-2747`, and its acceptance now mirrors the union of the original cycle and road-test wave.
- `ALP-2726` describes `ALP-2733` as the single terminal PER, documents the reopen lifecycle, and keeps `ALP-2747` last among workers before PER.
- `ALP-2746` now requires distinct safe tmux targets for `sm create session` and `sm run`, record comparison, teardown of both sessions, and schedule-matters re-scope breadcrumbs.
- `ALP-2745`, `ALP-2748`, and `ALP-2752` now specify daemon setup and cleanup discipline; `ALP-2748` and `ALP-2752` require daemon restart so handler and MCP registry state reflect the build under test.
- `ALP-2747` blocks on the full road-test wave and blocks `ALP-2733`, matching the gate order.
- The local `helioy-tools:linear-workflows` skill files include the new `Re-opening PER on Gate Amendment After Closure` workflow section and late-arrival PER mirroring defect-class sub-pattern.

Final bus sign-off sent: `I sign off on the ALP-2724 road-test wave (ALP-2743..ALP-2749, ALP-2752) as currently filed`.

