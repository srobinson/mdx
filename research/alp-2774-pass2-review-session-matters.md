---
title: ALP-2774 Pass 2 Review Findings for session-matters
type: research
tags: [session-matters, linear, moe-review, alp-2774, sm-isolation]
summary: Pass 2 found teardown, shell contract, and PER mirror defects in the ALP-2774 issue tree.
status: active
source: codebase-analyst
confidence: high
created: 2026-05-24
updated: 2026-05-24
---

## Executive Summary

The ALP-2774 master tree is selector compatible, with ALP-2782 as the accepted gate and ALP-2775 as the execution parent. Pass 2 found three substantive reviewability defects: the merge gate lacks teardown, the Docker verification shell contract is not explicit, and the PER says it mirrors worker acceptance one for one while adding extra per-worker gating bullets.

## Project Metadata

- Language: Rust workspace.
- Indexed surface: `.fmm.db` present and `fmm validate` reported all 105 files indexed and up to date.
- Current branch state checked from `/Users/alphab/Dev/LLM/DEV/helioy/littleorgans/session-matters`: `main...origin/main`.
- Structural size signal: 105 indexed files, 17,097 LOC. Largest indexed source files are `crates/sm-daemon/src/handler.rs` at 688 LOC and `crates/sm-daemon/src/mcp_tools.rs` at 670 LOC.

## Architecture

The reviewed work plumbs runtime isolation controls from session-matters public surfaces into runtime-matters:

- `ALP-2776` owns the `lilo-rm` 0.7.0 bump and `sm_core::SpawnRequest` wire fields.
- `ALP-2777` forwards `isolation`, `image`, and `mounts` through daemon and driver carriers. The current `spawn_launch` construction site is `crates/sm-daemon/src/handler.rs:609-644`.
- `ALP-2778` owns CLI flags, `tools/run.toml`, generated help, generated MCP schemas, and snapshots.
- `ALP-2779` owns daemon MCP argument reads in `agent_run`, currently `crates/sm-daemon/src/mcp_tools.rs:117-163`.
- `ALP-2780` owns CLI surface regression tests.
- `ALP-2781` is the post execution review issue.
- `ALP-2782` is the accepted gate with `Execute: ALP-2776, ALP-2777, ALP-2778, ALP-2779, ALP-2780, ALP-2781`.

## Key Patterns

- Linear issue descriptions are the reviewed artifact. The codebase was used to validate referenced files, source size pressure, and entry point plausibility.
- Generated public surfaces flow from `tools/run.toml` through `crates/sm-cli/build.rs` into help, MCP schema JSON, docs, and snapshots.
- The MoE review protocol requires compact bus messages with `F`, `A`, `S`, `V`, or `E` lines only.

## Detailed Findings

### F1: ALP-2782 merge gate has no teardown discipline

`ALP-2782` asks the operator to start `rtmd`, start `smd`, build a Docker image, run a Claude TUI into a tmux pane, and verify the spawned Docker container. The gate does not document what to stop or clean after success or failure.

Risk: the operator can leave `rtmd`, `smd`, a Docker container, a tmux TUI target, and possibly runtime-created Docker volumes dirty after the gate. Dirty state also makes the image ancestor container locator less reliable on later attempts.

Required edit sent on bus: add an operator teardown section covering smd/rtmd stop, spawned container cleanup, tmux target cleanup, and Docker volume handling or an explicit no-volume statement.

### F2: ALP-2782 Docker verification shell contract is implicit

The Docker verification snippets use POSIX shell assignment and command substitution. They are safe shape for bash and zsh, but fish cannot paste them as written. The gate does not name the expected shell.

Risk: a fish operator can fail before Docker is exercised, which turns the merge gate into shell-specific tribal knowledge.

Required edit sent on bus: add a POSIX sh/bash/zsh preface or wrap the blocks in an explicit shell.

Notes from shell review:

- `test -n "$CONTAINER"` correctly detects no container after `docker ps --format` returns an empty string.
- `grep -q '^CLAUDE_CODE_OAUTH_TOKEN='` gives a meaningful non-zero exit when the variable is absent under standard grep implementations.
- The missing contract is fish compatibility, not bash or zsh quoting.

### F3: ALP-2781 PER does not strictly mirror the worker acceptance bullets

`ALP-2781` says each worker's bullets mirror filed acceptance criteria one for one. The worker acceptance count is 18 total across ALP-2776 through ALP-2780, but the PER per-worker sections add extra gating bullets.

Examples:

- ALP-2776 PER adds Cargo.toml and `SpawnRequest` carrier criteria beyond the filed acceptance list.
- ALP-2777 PER adds a `SpawnLaunch` carrier and `spawn_launch` copy criterion beyond the filed acceptance list.
- ALP-2778 PER adds `tools/run.toml`, generated JSON, and `spawn_session` helper criteria beyond the five filed acceptance bullets.
- ALP-2779 PER adds an existing optional-reads criterion beyond the two filed acceptance bullets.
- ALP-2780 PER adds a non-assertion criterion beyond the three filed acceptance bullets.

Risk: a reviewer can fail the PER on criteria the worker issue did not authorize as acceptance, or miss that the one-for-one claim is false. This weakens review determinism.

Required edit sent on bus: separate an exact 18-bullet acceptance mirror from optional evidence or cross-cut checks, or mark extras non-gating.

## Dependencies

Critical external dependency in the plan is `lilo-rm-client` and `lilo-rm-core` 0.7.0, which supplies isolation, image, and mount carrier types for the runtime-matters boundary. The pass did not inspect runtime-matters because the review brief constrained file reads to this repo.

## Relevance to Helioy

The findings protect autonomous execution quality. Teardown discipline prevents operator state leakage, explicit shell contracts preserve copy-paste gates across common shells, and exact PER mirroring keeps Nancy review closure deterministic.

## Open Questions

- Does runtime-matters create named or anonymous Docker volumes for this Claude container path? ALP-2782 should either document cleanup or state no volume is created.
- Should the PER keep extra criteria as non-gating evidence hints, or should those criteria be promoted back into worker acceptance bullets?
