---
title: ALP-2800 Phase 1 Gate Review Findings for littleorgans
type: research
tags: [littleorgans, linear, gate-review, monorepo, phase-1, moe]
summary: Pass 2 review found four execution risks in the Phase 1 scaffold gate before worker release.
status: active
source: codebase-analyst
confidence: high
created: 2026-05-25
updated: 2026-05-25
---

## Executive Summary

The littleorgans monorepo is a pre-release, clean-slate Rust workspace scaffold that will become the local-first `lilo` product. Pass 2 review of ALP-2800 found four substantive gate risks: W1 is not independently completable as filed, W3 adds an unapproved environment contract, W6 allows a wrong Moon install path, and the PER summarizes acceptance instead of mirroring it.

## Project Metadata

- Repository: `/Users/alphab/Dev/LLM/DEV/helioy/littleorgans/littleorgans`
- Current tracked source: seed repository only, with `README.md:1` and `NOTES/v1-v2-strategy.md:1-103`
- FMM status: `.fmm.db` exists, but `fmm_list_files` returned 0 files and `fmm validate` reported no supported source files from the current root. Structural review therefore used live Linear, current filesystem state, the synthesis, and targeted shell proofs.
- Target language and build system: Rust workspace, Cargo resolver 3, edition 2024, Rust 1.90, Moon orchestration per synthesis `§2` and `§6` at `~/.mdx/projects/littleorgans-monorepo-migration--synthesis.md:283-290` and `369-378`.
- Product version: first monorepo release is `v0.8.0`; all published crates start at `0.8.0` per synthesis `306-326`.

## Architecture

Phase 1 is scaffold only. The synthesis defines a single Cargo workspace with published crates under `crates/`, internal crates under `internal/<substrate>/<role>/`, `tools/xtask`, GitHub Actions, Moon tasks, and reserved app/package/python directories. Relevant source of truth lines:

- Target directory layout: `~/.mdx/projects/littleorgans-monorepo-migration--synthesis.md:239-280`
- Workspace shape: `~/.mdx/projects/littleorgans-monorepo-migration--synthesis.md:283-291`
- Binary surface: `~/.mdx/projects/littleorgans-monorepo-migration--synthesis.md:293-304`
- Data and environment contract: `~/.mdx/projects/littleorgans-monorepo-migration--synthesis.md:328-367`
- Phase 1 mechanics and exit criteria: `~/.mdx/projects/littleorgans-monorepo-migration--synthesis.md:403-472`

Current repo state matches the pre-existing seed assumption in the synthesis: `.git`, `README.md`, `NOTES/v1-v2-strategy.md`, and fmm DB files exist. No Cargo workspace files or crate directories exist yet.

## Detailed Findings

### c1. ALP-2802 cannot complete before the workers it blocks

ALP-2802 excludes `crates/lilo`, `crates/lilo-common`, `crates/lilo-paths`, and `tools/xtask` from scope, but its acceptance requires `cargo metadata`, a package version jq check, `just`, and `moon ci`. With no member manifests present, a Cargo workspace using member globs or explicit missing member paths fails metadata loading.

Proof run in a temporary directory:

```text
members = ["crates/*", "tools/*"]
cargo metadata --no-deps --format-version=1
code=101
failed to load manifest for workspace member .../crates/*
```

Risk: W1 is the first unblocked worker and blocks W2 through W7. As filed, it can stall selector execution before the crate workers have created the manifests required by W1 verification.

Required change: either make W1 create minimal member manifests that W2 through W5 edit, or remove Cargo metadata and Moon gates from W1 and require each crate worker to add its root membership before W8 integration.

### c2. ALP-2804 introduces `LILO_LOG_JSON` outside the locked environment contract

The synthesis gates logging through `LILO_LOG`, output flag or TTY detection. It also says `LILO_SOCKET_PATH` and `LILO_LOG` are the only finer-grained environment overrides. Evidence:

- `LILO_LOG` and output flag or TTY: `~/.mdx/projects/littleorgans-monorepo-migration--synthesis.md:61`
- Only `LILO_SOCKET_PATH` and `LILO_LOG` are finer-grained overrides: `~/.mdx/projects/littleorgans-monorepo-migration--synthesis.md:352`
- Unified standards list `LILO_LOG` only: `~/.mdx/projects/littleorgans-monorepo-migration--synthesis.md:374-375`

ALP-2804 requires `LILO_LOG_JSON`. That creates a new public environment contract during Phase 1 without a synthesis or gate amendment.

Required change: remove `LILO_LOG_JSON` from W3, or explicitly amend the synthesis and gate before authorizing it.

### c3. ALP-2807 permits `cargo install moon`, which is not the moonrepo tool

Official Moon installation docs list proto, the Bash installer, npm package, and manual release downloads. Current `cargo search moon` resolves `moon = "0.0.0"` as “Moon UI”, not moonrepo’s task runner.

Risk: GitHub Actions can install the wrong crate or fail before `moon ci`, defeating the Phase 1 CI gate.

Required change: pin CI installation to moonrepo’s official setup path, such as `moonrepo/setup-toolchain` or the official installer, and delete `cargo install moon` from ALP-2807.

Sources used: <https://moonrepo.dev/docs/install> and local `cargo search moon --limit 5`.

### c4. ALP-2810 summarizes worker acceptance instead of mirroring it

ALP-2810 has one generic “All Acceptance bullets” line plus summary focus rows. It does not mirror each worker Acceptance list bullet by bullet. ALP-2802 alone includes acceptance checks for `cargo metadata`, jq version uniqueness, a `just --show` loop, `git check-ignore .fmm.db`, root file presence, and no `0.8.0` CHANGELOG heading. Several of those are not repeated in the ALP-2810 row.

Risk: the PER can close on a summary review and miss worker acceptance bullets that should be falsifiable at review time.

Required change: expand ALP-2810 rows into per-worker bullet mirrors, or require pasted pass/fail evidence for every acceptance bullet by worker ID.

## Dependencies

Critical Phase 1 dependencies from the reviewed gate:

- Cargo and Rust toolchain 1.90 for workspace build, test, fmt, clippy, and docs.
- Moon for orchestration. Current host did not have `moon` on PATH during review, which confirms the preflight path is operationally relevant.
- `jq`, `just`, `gh`, `fmm`, and optional linters `yamllint`, `actionlint`, `markdownlint`.
- GitHub CLI access to `littleorgans/littleorgans`; `gh repo view` confirmed the private repo exists with default branch `main`.

## Relevance to Helioy

The review protects the first littleorgans monorepo scaffold from selector stalls and contract drift. The findings are mostly reusable for Helioy planning gates: each autonomous worker must verify against artifacts it creates itself, environment variables need an explicit source of truth, CI install methods must be pinned to canonical tools, and PER issues should mirror acceptance rather than summarize.

## Open Questions

- Should W1 own minimal placeholder crate manifests, or should W2 through W5 each update root membership as they create crates?
- Should Moon be installed via Homebrew locally and `moonrepo/setup-toolchain` in CI, or should the repo adopt proto from day one?
- Should PER mirroring be hand-authored in Linear, or generated from worker Acceptance sections to prevent drift?

## Verification After Orchestrator Edits

Re-read live Linear on 2026-05-25 for ALP-2802 through ALP-2810 after the pass 2 VERIFY nudge. All seven conditional items were applied:

- c1: ALP-2802 now creates per-crate stub manifests and source files for `crates/lilo`, `crates/lilo-common`, `crates/lilo-paths`, and `tools/xtask`; W2 through W5 now expand those stubs.
- c2: ALP-2804 now locks logging to `LILO_LOG` only and adds a negative `LILO_LOG_JSON=1` no-effect test.
- c3: ALP-2807 now forbids `cargo install moon` and requires an official moonrepo installer or maintained moonrepo action.
- c4: ALP-2810 now mirrors worker acceptance bullets under per-worker H3 sections.
- S1: ALP-2806 now verifies `codegen`, `dist-check`, and `mirror-publish` exit code 2 behavior.
- S2: ALP-2808 now adds a `CLAUDE.md` line-count check and ALP-2810 checks Rust, Markdown, TOML, YAML, and YML files against the 700 LOC cap.
- S3: ALP-2809 now asserts `gh repo view littleorgans/littleorgans` before any local commit and leaves the final step as push only.

Bus response sent on topic `alp2800-review-pass2`:

```text
V|I sign off on ALP-2800 Phase 1 gate as currently filed
```
