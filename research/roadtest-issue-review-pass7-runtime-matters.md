---
title: rtm Docker Road Test Issue Review Pass 7
type: research
tags: [runtime-matters, linear, docker, road-test, issue-review]
summary: Pass 7 found one remaining issue quality gap: the manual Docker road test starts rtmd but does not bind teardown evidence.
status: active
source: codebase-analyst
confidence: high
created: 2026-05-21
updated: 2026-05-21
---

## Executive Summary

Reviewed ALP-2684 through ALP-2692 and ALP-2650 for the runtime-matters Docker road-test corrective wave. The issue graph and cited source paths are consistent, but ALP-2689's binding manual verification starts `rtm daemon start` and never binds daemon teardown, leaving operator state dirty after the required host proof.

## Project Metadata

- Language: Rust workspace.
- Branch: `nancy/ALP-2643`.
- fmm index: `.fmm.db` present and usable.
- Indexed size: 106 Rust files, 17,322 LOC.
- File cap status from fmm: largest indexed file is `crates/rtm-core/src/types.rs` at 693 LOC; second is `crates/rtm-cli/tests/common/mod.rs` at 682 LOC. Generated files under `crates/rtm-cli/src/generated/` are indexed and small.

## Architecture

The reviewed work lives in the runtime-matters Docker sandboxing execution chain under master `ALP-2643`, execution parent `ALP-2649`, and accepted gate `ALP-2650`. The corrective wave covers Docker command resolution, reference image validity, arm64 local-image preflight, per-spawn image selection, public terminology cleanup, real-Docker E2E coverage, environment passthrough, a precondition refactor for `rtm-core/src/types.rs`, and post execution review.

## Detailed Findings

### Finding 1: ALP-2689 manual verification lacks rtmd teardown

- Severity: substantive issue-quality gap.
- Affected issues: `ALP-2689`, mirrored review criteria in `ALP-2691`.
- Evidence:
  - `ALP-2689` Binding manual verification starts `rtm daemon start` in the foreground, then runs `rtm spawn`, container presence checks, `docker top`, `rtm kill`, and a container absence check.
  - Its expected end state proves the container is gone but does not stop the daemon or assert daemon shutdown.
  - The CLI has a daemon stop surface: `DaemonCommand` includes `Stop` in `crates/rtm-cli/src/cli/daemon.rs:8-13`; `DaemonCommand.run` routes `Self::Stop` to `stop().await` in `crates/rtm-cli/src/cli/daemon.rs:16-29`; `stop` sends `RuntimeRpc::Stop` and waits for socket removal in `crates/rtm-cli/src/cli/daemon.rs:32-42`.
- Required change: add an explicit teardown step to ALP-2689, either `rtm daemon stop` from the second shell or an explicit interrupt of the foreground daemon, with an observable clean shutdown check. Mirror that expectation in ALP-2691's review criteria.

### Clean checks

- Linear fetches: ALP-2684, ALP-2685, ALP-2686, ALP-2687, ALP-2688, ALP-2689, ALP-2690, ALP-2691, ALP-2692, and ALP-2650 fetched with relations. Comments were checked; only ALP-2650 had comments.
- Path verification: cited paths exist on `nancy/ALP-2643`, including README, CHANGELOG, the Dockerfile, CLI tests, daemon modules, core modules, snapshots, and common test harness files.
- Ordering: structural `blockedBy` relations match the claimed order for the reviewed corrective wave:
  - ALP-2692 blocks ALP-2687 and ALP-2690.
  - ALP-2684, ALP-2685, ALP-2686, ALP-2687, and ALP-2690 block ALP-2689.
  - ALP-2688, ALP-2689, and ALP-2692 block ALP-2691.
- File-cap coverage: fmm covers generated Rust files under `crates/rtm-cli/src/generated/`; no current indexed Rust file is at or above 700 LOC.

## Dependencies

Critical reviewed surfaces:

- Linear MCP for live issue descriptions, relations, and comments.
- fmm for indexed Rust file topology and LOC checks.
- Git tracked-file checks for non-Rust paths and directories not represented by fmm symbols.

## Relevance to Helioy

This review reinforces the Nancy issue-quality rule that manual verification sequences must leave host state clean, especially for long-running daemons. A successful road test should prove both product behavior and test harness teardown.

## Open Questions

- After ALP-2689 is amended, a follow-up pass should verify ALP-2691 mirrors the teardown criterion exactly enough for PER to enforce it.
