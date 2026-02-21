---
title: ALP-2724 Pass 6 Issue Review for session-matters
type: research
tags: [session-matters, linear, cli, issue-review, alp-2724]
summary: Pass 6 found one substantive release notes coverage gap in the ALP-2724 execution tree.
status: active
source: codebase-analyst
confidence: high
created: 2026-05-22
updated: 2026-05-22
---

## Executive Summary

Pass 6 of the ALP-2724 MoE issue review found one substantive gap: the tree updates project docs and generated docs, but does not explicitly cover `CHANGELOG.md` or release notes for breaking CLI noun changes and post ALP-2673 namespace lifecycle cleanup.

## Project Metadata

- Project: `session-matters`
- Language: Rust
- Build system: Cargo with `just` verification
- Indexed with fmm: yes, fmm reported 100 indexed files and 15,034 LOC under `crates/`
- Relevant Linear tree: ALP-2724, ALP-2725, ALP-2726, ALP-2727, ALP-2728, ALP-2729, ALP-2730, ALP-2735, ALP-2731, ALP-2732, ALP-2733

## Architecture

The reviewed work targets the `sm` CLI surface:

- CLI grammar lives in `crates/sm-cli/src/cli/cli_def.rs`.
- Read and delete behavior live in `crates/sm-cli/src/cli/get.rs` and `crates/sm-cli/src/cli/delete.rs`.
- Help generation is currently rooted in `tools.toml`, consumed by `crates/sm-cli/build.rs` and `crates/sm-core/src/tool_contracts.rs`.
- Generated documentation surfaces include `crates/sm-cli/src/tool_docs.rs` and `crates/sm-cli/templates/SKILL.md`.

## Key Patterns

- The Linear gate uses a selector compatible master, gate, execution parent, worker, and PER shape.
- Worker issues encode dependencies structurally through Linear relations and prose through the gate Required order.
- Tests use `crates/sm-cli/tests/common/mod.rs` helpers, including `DaemonFixture`, `sm_bin`, and `assert_cmd::cargo::cargo_bin("sm")`.

## Detailed Findings

### Finding 1: CHANGELOG or release notes coverage is missing

`CHANGELOG.md` exists and has an `Unreleased` section, but current lines 7 to 16 still document `.sm/namespace` marker discovery and marker based selector precedence. ALP-2724 removes user visible CRUD forms such as `sm get agent`, `sm get agents`, and `sm delete agent`; ALP-2673 removed marker reader behavior. The execution tree should make the release notes surface explicit.

Recommended change:

- Add `CHANGELOG.md` to ALP-2732 stable entry points and acceptance, plus ALP-2733 manual review criteria, or add a dedicated release notes worker if changelog edits should be separated from project docs.

### Non-findings from pass 6 probes

- Cross repo consumer docs: no documented `sm get` or `sm delete` invocations were found in sibling `../identity-matters` or `../runtime-matters` README, PROJECT, or CLAUDE files. `../transport-matters` was not present in this checkout.
- Tests outside `crates/sm-cli/tests`: no `sm` binary shell out references found in other `crates/*/tests` directories.
- Justfile, scripts, workflows: no hardcoded `sm` command references found.
- Worker test convention: the existing test harness makes worker prose adequate. No added convention text appears necessary.
- Wave atomicity: W2 can rename the clap noun while leaving `AGENT_*` constant cleanup to W5 without forcing an intermediate compile break.

## Dependencies

Critical dependencies and surfaces:

- `clap` for CLI grammar.
- `assert_cmd` through `crates/sm-cli/tests/common/mod.rs` for binary testing.
- fmm for structural outlines.
- Linear issue tree as planning source of truth.
- helioy-bus for peer consensus review coordination.

## Relevance to Helioy

This review protects the cross littleorgans CLI control plane from stale user facing surfaces. The same release notes gap pattern can recur in sibling repo work when breaking changes are treated as pre release implementation details but still appear in published `CHANGELOG.md` or generated docs.

## Open Questions

- Whether the orchestrator prefers to amend ALP-2732 directly or create a separate release notes worker.
- Whether `CHANGELOG.md` should be treated as a standard W6 docs entry point for future session-matters CLI surface changes.
