---
title: RTM Mount Linear Tree Pass 4 Review
type: research
tags: [runtime-matters, linear-review, moe-review, docker, rtm-mount]
summary: Pass 4 found five substantive readiness gaps; round 2 live Linear re-read verified all five fixes and signed off.
status: active
source: codebase-analyst
confidence: high
created: 2026-05-23
updated: 2026-05-23
---

## Executive Summary

A pass 4 cold read of the Linear tree for ALP-2784 found the ALP-2796 amendment structurally included and the probed file sizes below the 700 line cap. Five substantive gaps were identified: cross repo evidence ownership, missing acceptance coverage for cwd auto mount overlap conflicts, a canonicalized source data flow gap, unresolved policy drift for relative path shaped env values, and ambiguous tilde expansion ownership. Round 2 re-read of live Linear after orchestrator edits verified all five were resolved, and Codex signed off with `I sign off on the artifact as currently filed`.

## Project Metadata

- Language: Rust workspace.
- Tooling: fmm indexed, `.fmm.db` present and `fmm validate` reported all 135 files up to date on 2026-05-23.
- Build system: Cargo plus repo gate commands in `PROJECT.md`: `just check`, `just build`, `just test`.
- Public crates: `lilo-rm-core` and `lilo-rm-client` per `PROJECT.md`.
- Current branch during review: `main`.

## Architecture

The current spawn path is important to the canonicalization finding:

1. `handler.rs` runs `spawn_preflight::check(&state, &request)` before launcher dispatch and backend preparation, then calls launcher dispatch and `backends.prepare_launch(&request, launch)` (`crates/rtm-daemon/src/handler.rs:103-110`).
2. `spawn_preflight::check` takes an immutable `&SpawnRequest` and returns `Result<Option<RuntimeResponse>>`, so the current API can reject or allow but cannot return normalized mount data (`crates/rtm-daemon/src/spawn_preflight.rs:15-20`).
3. `LaunchSpec` carries `argv`, `env`, `cwd`, and optional `shell_resume`; it has no mount field today (`crates/rtm-core/src/launcher.rs:31-37`).
4. Docker argv currently emits the cwd self mount and workdir directly from `launch.cwd` (`crates/rtm-daemon/src/docker_argv.rs:80-83`).

## Key Patterns

- Linear is the planning source of truth. Gate `Execute:` and structural relations must agree before execution.
- Worker bodies must be self sufficient. Binding design call resolutions need mirrored acceptance and PER coverage where they affect behavior.
- Data flow matters for planning review. A worker that says validation canonicalizes data must also specify how canonicalized data reaches the consumer that emits Docker argv.

## Detailed Findings

### Round 2 re-verification outcome

On 2026-05-23, after the orchestrator reported all five pass 4 consensus changes applied, Codex re-read live Linear state via MCP for ALP-2794, ALP-2788, ALP-2789, ALP-2790, ALP-2793, ALP-2796, parent children, Backlog children, and gate/PER comments. No remaining substantive concerns were found.

Verified fixes:

- F1: ALP-2796 now owns filing or updating the `session-matters` tracking issue, release notes include the ID, and PER treats absence as an action item rather than terminal master failure.
- F2: ALP-2790 acceptance and ALP-2793 PER mirror now include duplicate target, cwd source overlap, and cwd target overlap rejection.
- F3: Gate, ALP-2790, ALP-2789, and PER now bind canonicalized source data flow to Docker argv emission and prohibit re-canonicalization in argv emission.
- F4: Gate, ALP-2790, and PER now reject relative path shaped env values with a clear preflight error.
- F5: Gate, ALP-2788, ALP-2790, and PER now split CLI tilde expansion from daemon canonicalization. CLI expands `~` with launching user's `$HOME`; daemon handles relative paths and symlinks only.

Bus signoff sent to orchestrator: `I sign off on the artifact as currently filed`.

### 1. Cross repo coordination evidence has no assigned producer

Evidence:

- ALP-2793 requires PER to cite a concrete `session-matters` issue ID or concrete consuming commit/check evidence. Absence fails cross worker acceptance.
- ALP-2796 says the `session-matters` consumption update is out of scope and coordination is tracked by the PER cross worker bullet.

Impact: PER can block on evidence nobody is assigned to produce.

Required change: Make ALP-2796 own filing or citing the `session-matters` tracking issue before Worker Done, or explicitly authorize PER to file the missing issue and re run the acceptance check.

### 2. Cwd auto mount overlap conflict is not mirrored in acceptance

Evidence:

- Gate conflict policy says duplicate mount targets are rejected and mount sources or targets that overlap the cwd auto mount are rejected.
- ALP-2790 prose mentions source or target overlap rejection.
- ALP-2790 acceptance and ALP-2793 PER mirror include duplicate target rejection, but no explicit source overlap or target overlap tests.

Impact: The binding conflict rule can be missed while the worker and PER still pass their bullet lists.

Required change: Add acceptance and PER bullets for source overlap with cwd auto mount and target overlap with cwd auto mount.

### 3. Canonicalized source emission lacks an explicit data path

Evidence:

- Gate and ALP-2790 require host mount sources to be canonicalized before comparison and emitted into Docker `--mount source=...` argv.
- Current source calls preflight before backend prepare launch and Docker argv emission (`crates/rtm-daemon/src/handler.rs:103-110`).
- Current preflight API cannot return normalized mount values (`crates/rtm-daemon/src/spawn_preflight.rs:15-20`).
- Current `LaunchSpec` has no mount field (`crates/rtm-core/src/launcher.rs:31-37`).

Impact: An implementation can validate canonicalized values and still emit raw user typed mount sources into Docker argv, especially for `~`, relative paths, and symlinks.

Required change: Amend ALP-2789 or ALP-2790 acceptance to prove Docker argv uses canonicalized source paths, and authorize the data shape change needed to carry normalized mounts from validation to emission.

### 4. Relative path shaped env policy is unresolved

Evidence:

- The gate describes mount targets and path shaped env values as container paths and binds lexical normalization for comparison.
- ALP-2790 narrows validation to path shaped keys whose values are absolute paths.

Impact: Relative path shaped env values have no bound behavior. They may bypass mount coverage validation and preserve a silent hang class for that input shape.

Required change: Bind one policy. Either reject relative path shaped env values for docker isolation with a clear error, or mark them exempt with rationale and coverage.

### 5. Tilde expansion does not specify which HOME is authoritative

Evidence:

- ALP-2790 requires mount sources to expand `~`.
- ALP-2788 says the CLI passes host source values through unchanged.
- `SpawnRequest` has no caller home field (`crates/rtm-core/src/types/spawn.rs:77-92`).
- fmm source search found existing `HOME` handling only in `rtm-paths` path policy and tests, with no existing tilde expansion helper.

Impact: A daemon implementation can reasonably use its own `HOME`. That works for single user local dev, but can canonicalize against the wrong user under systemd, alternate user daemons, or future deployment shapes.

Required change: Bind one authority. Either add caller home to the request shape, state that daemon home is authoritative with an explicit deployment assumption, or move tilde expansion to the caller and amend ALP-2788.

### Positive Checks

- ALP-2796 appears in gate `Execute`, gate `Required order`, ALP-2793 PER per worker mirror, PER `blockedBy`, and structural relations.
- Master ALP-2784 has only the gate and Backlog as direct children.
- Backlog ALP-2785 has the expected workers plus PER.
- File size probes were below cap:
  - `crates/rtm-daemon/src/docker_argv.rs`: 299 LOC.
  - `crates/rtm-cli/src/cli/spawn.rs`: 128 LOC.
  - `crates/rtm-core/src/types/spawn.rs`: 202 LOC. This is where `SpawnRequest` lives.
  - `crates/rtm-core/src/version.rs`: 145 LOC.
  - Existing `crates/rtm-daemon/src/spawn_preflight/tests.rs`: 666 LOC, already covered by ALP-2795.

## Dependencies

Critical local surfaces:

- `crates/rtm-core/src/types/spawn.rs`: public `SpawnRequest`.
- `crates/rtm-core/src/version.rs`: public runtime protocol capability list.
- `crates/rtm-daemon/src/spawn_preflight.rs`: preflight validation entry point.
- `crates/rtm-daemon/src/docker_argv.rs`: Docker run argv construction.
- `crates/rtm-daemon/src/handler.rs`: spawn request orchestration.
- `crates/rtm-core/src/launcher.rs`: `LaunchSpec` handoff shape.

## Relevance to Helioy

This tree sits on the runtime contract between `session-matters` and `runtime-matters`. The cross repo evidence gap is especially relevant because `session-matters` consumes `lilo-rm-core` and must eventually expose mounts end to end.

## Open Questions

- Should relative path shaped env values be rejected or explicitly exempt?
- Should canonicalized mounts live on `SpawnRequest`, a normalized daemon side request wrapper, or `LaunchSpec`?
- Should ALP-2796 file the `session-matters` tracking issue, or should PER own that action when the evidence is absent?
- Whose home directory owns `~` expansion: caller, daemon, or CLI pre expansion?
