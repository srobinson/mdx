---
title: ALP-2724 Road-Test Wave Pass 3 Review
type: research
tags: [helioy, session-matters, linear, moe-review, sm-cli]
summary: Fresh-eyes review found five substantive integration risks in the ALP-2724 road-test corrective wave.
status: active
source: codebase-analyst
confidence: high
created: 2026-05-22
updated: 2026-05-22
---

## Executive Summary

Pass 3 reviewed the ALP-2724 road-test corrective wave across Linear gate ALP-2726, PER ALP-2733, and worker issues ALP-2743 through ALP-2749 plus ALP-2752. The review sent a conditional sign-off on the bus with five changes: constrain MCP capture scope, sequence ALP-2748 and ALP-2744 before ALP-2749, clarify docs source ownership, and assign CHANGELOG ownership.

## Project Metadata

- Project: `session-matters`
- Working tree: `/Users/alphab/Dev/LLM/DEV/helioy/littleorgans/session-matters-worktrees/nancy-ALP-2724`
- Language: Rust
- Build gate named by issues: `just check && just build && just test`
- fmm status: `.fmm.db` exists, but MCP structural read failed because index schema version 6 did not match available fmm schema version 5. Review fell back to shell structural checks and live Linear reads.

## Architecture

Relevant surfaces in the wave:

- CLI command tree and argument shape: `crates/sm-cli/src/cli/cli_def.rs`
- CLI dispatch and behavior: `crates/sm-cli/src/cli/get.rs`, `crates/sm-cli/src/cli/capture.rs`, `crates/sm-cli/src/cli/run.rs`, `crates/sm-cli/src/cli/namespace.rs`
- Generated help and MCP schema: `crates/sm-cli/src/cli/generated_help.rs`, `crates/sm-cli/src/mcp/generated_schema.rs`, `crates/sm-cli/src/mcp/generated_schema/*.json`, `crates/sm-cli/src/mcp/generated_instructions.rs`
- Help source: `tools/*.toml`, with planned shared selector content in `tools/_shared.toml`
- Daemon and MCP runtime surface: `crates/sm-daemon/src/handler.rs`, `crates/sm-daemon/src/mcp_tools.rs`
- Protocol and registry: `crates/sm-core/src/tool_contracts.rs`
- Docs: `README.md`, `PROJECT.md`, `CHANGELOG.md`

Current size checks showed the main surfaces under the 700 LOC cap, with `crates/sm-daemon/src/handler.rs` at 682 LOC and `crates/sm-daemon/src/mcp_tools.rs` at 622 LOC. Any road-test worker touching `handler.rs` should watch cap pressure.

## Key Patterns

- Linear gate ALP-2726 is the authorization source. Its `Execute:` list includes original workers, PER correctives, and road-test correctives.
- PER ALP-2733 is reopened and now mirrors both original-cycle and road-test surfaces.
- ALP-2747 is the terminal road-test audit worker before PER and is the best owner for cross-wave documentation and CHANGELOG reconciliation.
- Shared CLI selector semantics cross multiple workers. ALP-2744 introduces shared selector metadata; ALP-2749 audits selector command shape; ALP-2748 changes capture from selector to session id. These are not safely independent.

## Detailed Findings

### 1. ALP-2748 allows too much MCP surface change

ALP-2748 is scoped around `sm capture` becoming a single-session CLI command. Its acceptance allows the MCP `session_capture` tool to keep a selector-shaped field or be renamed/reframed. That grants the worker permission to rename or extend the MCP tool surface while ALP-2747 and PER mainly audit existing generated schema names. Recommended change: preserve `session_capture` and any existing compatibility alias, and require schema plus daemon handling to enforce one exact session id or explicit zero/multi-match errors.

### 2. ALP-2749 depends on ALP-2748

ALP-2726 says ALP-2745, ALP-2746, ALP-2748, ALP-2749, and ALP-2752 can run in parallel. ALP-2749's selector-rule contract includes single-session commands taking positional session ids, with `sm capture <SESSION_ID>` named via ALP-2748. Recommended change: Required order and dependency edges should place ALP-2749 after ALP-2748.

### 3. ALP-2744 and ALP-2749 share selector-help infrastructure

ALP-2744 introduces `tools/_shared.toml`, machine-readable selector semantics, and build-renderer changes. ALP-2749 classifies selector-consuming commands and verifies help and near-miss forms. Both touch `tools/*.toml`, `crates/sm-cli/build.rs`, and `crates/sm-cli/tests/cli_help_surface_test.rs`. Recommended change: sequence ALP-2744 before ALP-2749, or state that ALP-2749 consumes ALP-2744's shared selector metadata and does not create a parallel classification path.

### 4. Docs ownership is ambiguous

ALP-2745, ALP-2746, and ALP-2749 use `PROJECT.md and/or README` or `PROJECT.md or README`. PER reads both and can catch stale docs later, but workers can satisfy their own acceptance while fragmenting documentation. Recommended change: each docs-owning worker should name exact surfaces. Preferred rule: user-visible command-model changes update both `PROJECT.md` and README CLI section, or update the named source plus generated output if one surface is generated.

### 5. CHANGELOG ownership is missing

PER ALP-2733 acceptance 5g requires `CHANGELOG.md` Unreleased to include the road-test user-visible CLI changes. No executable road-test worker owns the CHANGELOG update. Recommended change: assign this to ALP-2747 because it runs last and already audits docs, help, MCP, README, and PROJECT. Required coverage should include `sm get` aliased single-subcommand shape, label metadata and `--show-labels`, alias-pending-schedule-matters interim, selector argument shape rule, `sm capture <SESSION_ID>`, and `sm link` removal.

## Dependencies

- Linear MCP provided live issue bodies and relations.
- helioy-bus carried the review brief and conditional sign-off.
- fmm MCP was attempted first for structural analysis but failed due schema mismatch.

## Relevance to Helioy

The findings reinforce three Helioy planning rules: parallel execution must match actual shared-file dependencies, late wave additions need explicit PER and CHANGELOG ownership, and MCP surface changes must be constrained to the worker's authorized scope.

## Open Questions

- Whether the peer pane agrees all five findings are substantive, or wants to collapse items 2 and 3 into one Required order correction.
- Whether ALP-2747 should own all road-test docs finalization, or each worker should own its own CHANGELOG bullet with ALP-2747 auditing only.

## Peer Consensus Update

Peer pane `nancy-ALP-2724:helioy-tools:codebase-analyst:1:3.1` replied on topic `2724-roadtest-review-pass3` and independently found the same substantive set. Items 1 and 2 in their reply map to this document's CHANGELOG ownership and docs source-of-truth findings; they explicitly concurred with the MCP capture scope and ALP-2748/ALP-2744 sequencing findings. I replied with consensus confirmation and CCed the orchestrator.

## Final Pass 3 Sign-off

The orchestrator reported all five consensus findings applied. I re-fetched live Linear state for ALP-2726, ALP-2733, ALP-2743 through ALP-2749, and ALP-2752. Confirmed: ALP-2747 owns CHANGELOG.md, docs source-of-truth rule is codified and reflected in ALP-2745/2746/2749, ALP-2748 preserves `session_capture` and `agent_capture` identities while tightening schema and handler behavior, ALP-2749 is structurally blocked by ALP-2748 and ALP-2744, and the gate Required order reflects the new sequencing. Also checked local commit `8d673e8`, which added `TLDR.md` and symlinked `CLAUDE.md` / `AGENTS.md` to it. Sent the clean sign-off phrase on the bus: `I sign off on the ALP-2724 road-test wave (ALP-2743..ALP-2749, ALP-2752) as currently filed`.

## Round 2 Regression Note

Peer pane found one missed application after the clean sign-off: ALP-2752 still retained the pre-pass-3 docs hedge `PROJECT.md (or the closest equivalent surface)` in acceptance bullet 5, while ALP-2726 now claims ALP-2752 uses the docs source-of-truth rule. I re-read ALP-2752 live and confirmed the contradiction. Sent a new conditional sign-off requiring ALP-2752 to name `PROJECT.md` as the canonical unmanaged-session adoption deferral rationale surface, with README and other docs only stripping `sm link` references.

## Round 2 Fix Verified

Orchestrator reported the ALP-2752 docs ownership defect fixed. I re-fetched ALP-2752 and ALP-2726 live. ALP-2752 now has a Docs ownership section matching the wave rule, acceptance 5 names `PROJECT.md` as the rationale surface and limits README / other docs to removing `sm link` references. ALP-2726 now lists ALP-2745, ALP-2746, ALP-2749, and ALP-2752 as docs-rule users, with ALP-2748 excluded because it does not author user-facing docs. No further action was needed.

## Final Peer Convergence

Peer pane sent final clean sign-off after live Linear re-read confirmed the ALP-2752 round-2 fix. I acknowledged and CCed the orchestrator with matching final position: `I sign off on the ALP-2724 road-test wave (ALP-2743..ALP-2749, ALP-2752) as currently filed`.
