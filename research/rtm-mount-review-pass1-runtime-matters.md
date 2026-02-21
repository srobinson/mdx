---
title: runtime-matters rtm spawn mount review pass 1
type: research
tags: [runtime-matters, linear, review, docker, mount, preflight]
summary: Final live Linear re-read confirmed all pass 1 blockers were addressed and Codex signed off.
status: active
source: codebase-analyst
confidence: high
created: 2026-05-23
updated: 2026-05-23
---

## Executive Summary

Pass 1 reviewed the live Linear tree for `ALP-2784`, the `rtm spawn --mount` and path-shaped env preflight master. A final live Linear re-read after orchestrator edits confirmed the gate and worker bodies now address the prior blockers. Codex sent `I sign off on the artifact as currently filed` on topic `rtm-mount-review-pass1`.

## Project Metadata

- Language: Rust workspace.
- Build system: Cargo plus `justfile` recipes.
- Verification surface used in this audit: `fmm validate`, `cargo test -p rtm-daemon docker_argv -- --list`, `cargo test -p rtm-daemon preflight -- --list`, and targeted `wc -l` line counts.
- fmm status: `.fmm.db` exists and `fmm validate` reports all 135 indexed files current.

## Architecture

`runtime-matters` is a per host runtime substrate. `rtm-cli` builds typed requests, `rtm-core` owns protocol and public types, and `rtm-daemon` validates and launches runtime processes. Docker isolation currently flows through CLI spawn parsing, `SpawnRequest`, daemon spawn preflight, Docker argv construction, and optional Docker E2E tests.

Relevant current files:

- `crates/rtm-cli/src/cli/spawn.rs`: spawn CLI arguments and request construction, 128 lines.
- `crates/rtm-core/src/types/spawn.rs`: `SpawnRequest` lives at lines 77 to 92, file is 202 lines.
- `crates/rtm-core/src/version.rs`: protocol capability registry is at lines 8 to 20 and `RuntimeCapability` at lines 46 to 69, file is 145 lines.
- `crates/rtm-daemon/src/docker_argv.rs`: Docker argv builder and snapshots, 299 lines.
- `crates/rtm-daemon/src/docker_preflight.rs`: Docker image preflight, 332 lines.
- `crates/rtm-daemon/src/spawn_preflight.rs`: spawn preflight orchestration, 187 lines.
- `crates/rtm-daemon/src/spawn_preflight/tests.rs`: existing preflight tests, 666 lines.
- `crates/rtm-cli/tests/docker_e2e.rs`: opted in Docker E2E harness, 339 lines.

## Key Patterns

- Accepted gate bodies must hold canonical selector lines: `Outcome:`, `Authorized execution parent:`, `Execute:`, and `Required order:`.
- Worker dependencies use Linear `blockedBy` relations. Prose order must mirror the graph.
- PER issues should mirror worker acceptance criteria bullet for bullet when worker coverage is broad.
- Files near 700 lines require extraction before new tests or logic land.

## Detailed Findings

### 1. Container path canonicalization is over specified

`ALP-2790` and the gate design call currently require expanding `~`, resolving relative paths against launch cwd, and resolving symlinks uniformly for mount sources, mount targets, and env values.

That mixes host paths and container paths. Mount sources are host paths. Mount targets and path-shaped env values are container paths. Host filesystem canonicalization of `/home/rtm/.claude` can reject a valid container target when that path does not exist on the host, or compare against the wrong filesystem.

Recommended change: keep host source canonicalization host side. Define target and env coverage as lexical, container path safe comparison, or another explicit container path normalization that does not depend on host filesystem existence.

### 2. PER does not mirror worker acceptance bullet for bullet

`ALP-2793` says each worker outcome must be verified against its acceptance criteria, but it does not enumerate those checks. That leaves quiet skip risk across the broad worker set.

Specific uncovered surfaces include:

- `ALP-2788`: read only default, `:rw` opt in, repeated mount declaration order, host isolation reject before RPC, and help text.
- `ALP-2789`: empty mounts preserve existing argv, read only true emits `readonly`, read write omits it, declaration order, and snapshot coverage.
- `ALP-2790`: unmatched env rejection, same destination acceptance, subtree coverage, duplicate target rejection, host isolation warning and no-op behavior, cwd auto-mount overlap rejection, and curated env list membership.
- `ALP-2787`: serde default and skip behavior, non-empty round trip, explicit snapshot, and workspace build coverage.
- `ALP-2792`: all contradictory `/workspace` references removed and docs avoid implying host env paths are auto-mounted.

Recommended change: amend `ALP-2793` with grouped per-worker review bullets that mirror each worker acceptance criterion.

### 3. Preflight tests are already within 34 lines of the hard cap

`crates/rtm-daemon/src/spawn_preflight/tests.rs` is 666 lines. `ALP-2790` will need several new preflight tests for unmatched envs, same destination coverage, subtree coverage, duplicate targets, host isolation no-op warnings, cwd overlap rejection, and env policy list membership.

Recommended change: require extraction or test module splitting before `ALP-2790` adds tests. This keeps the repo compliant with the 700 line cap.

### 4. E2E image acceptance contradicts the existing harness, severity delegated

`ALP-2791` and `ALP-2793` reference `--image runtime-matters-claude:local`, while `ALP-2791` also says the test should match the convention of existing Docker E2E tests. The live harness does not use that tag. `crates/rtm-cli/tests/docker_e2e.rs` builds dynamic per-session tags from `examples/dockerfiles/claude.Dockerfile`: `runtime-matters-claude:e2e-{session_id}-base` and `runtime-matters-claude:e2e-{session_id}`.

Recommended change: replace `runtime-matters-claude:local` in `ALP-2791` and `ALP-2793` with the existing dynamic image harness pattern, add an explicit prerequisite worker that builds the `:local` tag, or document the manual build command. Both panes agree on the fix shape. Severity label is the orchestrator's call.

### Probe Results

- Required order vs blockers: clean. The gate order matches live `blockedBy` relations for `ALP-2786` through `ALP-2793`.
- Execute set: clean. Backlog children under `ALP-2785` are exactly `ALP-2786` through `ALP-2793`, and all appear in the gate `Execute:` line.
- Verification command realism: clean. `cargo test -p rtm-daemon docker_argv -- --list` resolves 5 tests. `cargo test -p rtm-daemon preflight -- --list` resolves 27 tests.
- Implementation prescription level: acceptable aside from the canonicalization bug. `MountSpec`, `SpawnRequest.mounts`, CLI `--mount`, and Docker argv strings are public or observable surfaces for this work.
- E2E image precondition: agreed defect with severity delegated. `ALP-2791` names `runtime-matters-claude:local` but also says to match the convention of existing Docker E2E tests. Existing `crates/rtm-cli/tests/docker_e2e.rs` builds session-scoped images from `examples/dockerfiles/claude.Dockerfile` at lines 69 to 93 and uses them at lines 24 to 35.

## Dependencies

Critical dependencies surfaced by the audit:

- Docker CLI and daemon availability for E2E tests.
- `examples/dockerfiles/claude.Dockerfile` as the in-repo Docker verification target.
- `cargo nextest` via the `just test` recipe for normal workspace test runs.
- fmm index for structural navigation and line count validation.

## Relevance to Helioy

This review protects Nancy execution reliability. The main risks are selector safe review coverage, avoiding host and container path confusion, and staying inside the repo line count policy before autonomous workers start.

## Consensus Message Status

After peer discussion and crossed messages, definitive close converged on three unambiguous substantive blockers: host versus container path canonicalization, PER bullet mirroring, and preflight test location plus file-size pressure. The E2E image acceptance versus harness mismatch is an agreed defect with the severity label delegated to the orchestrator because both panes flipped framing and agree on the same fix. The `MountSpec` naming concern was treated as soft and not a blocker.


## Final Live Re-read Sign-off

After the orchestrator applied the review changes, Codex re-read live Linear state for `ALP-2790`, `ALP-2791`, `ALP-2793`, `ALP-2794`, `ALP-2795`, and the full `ALP-2785` Backlog child set. The final check confirmed:

- `ALP-2794` splits host-source canonicalization from container-path normalization.
- `ALP-2790` mirrors that split and requires container target / env comparisons without host filesystem calls.
- `ALP-2795` is in the Execute set and structurally blocks `ALP-2790` and `ALP-2793` before new mount tests land.
- `ALP-2791` uses the existing dynamic-tag Docker E2E harness pattern and removes the hardcoded `runtime-matters-claude:local` reference from automated test acceptance.
- `ALP-2793` mirrors each worker's acceptance bullets, including `ALP-2795` and the updated `ALP-2791` criteria.
- The gate `Execute:` line matches the live Backlog children under `ALP-2785`.

Final bus sign-off sent to `runtime-matters:general:3:2.1`: `I sign off on the artifact as currently filed`.

## Open Questions

- Should path-shaped env normalization reject relative container env values, or should it define lexical resolution relative to the container workdir?
