---
title: RTM Docker Road Test Issue Review Pass 2
type: research
tags: [runtime-matters, linear, docker, issue-review, alp-2643]
summary: Fresh-eyes pass-2 review of ALP-2684 through ALP-2690 and gate ALP-2650 found two sequencing and manual verification precision gaps.
status: active
source: codebase-analyst
confidence: high
created: 2026-05-21
updated: 2026-05-21
---

## Executive Summary

Current Linear state for the Docker road-test corrective set is mostly executable. The pass-2 review found two substantive gaps: ALP-2686 is incorrectly treated as independent even though ALP-2689's local-image real Docker verification can require it on arm64 hosts, and ALP-2689's manual verification command does not preserve the generated session id used later by `rtm kill`.

## Project Metadata

- Project: runtime-matters
- Repository branch verified: `nancy/ALP-2643`
- Commit verified: `b43dbf5`
- Language: Rust
- Build system: Cargo with `just` tasks
- Gate reviewed: ALP-2650
- Worker issues reviewed: ALP-2684, ALP-2685, ALP-2686, ALP-2687, ALP-2688, ALP-2689, ALP-2690

## Architecture Context

fmm indexed 106 source files under `crates/` with 17,322 LOC. Relevant surfaces verified through fmm and tracked path checks:

- Docker runtime placement: `crates/rtm-daemon/src/docker_runtime.rs`
- Docker preflight and typed errors: `crates/rtm-daemon/src/docker_preflight.rs`, `crates/rtm-daemon/src/spawn_preflight.rs`, `crates/rtm-daemon/src/error.rs`
- Spawn request public contract: `crates/rtm-core/src/types.rs`
- Daemon env default: `crates/rtm-daemon/src/server.rs`
- CLI spawn entry point: `crates/rtm-cli/src/cli/`
- Documentation assertions: `crates/rtm-cli/tests/docker_documentation.rs`
- Example image: `examples/dockerfiles/claude.Dockerfile`

## Detailed Findings

### Finding 1: ALP-2686 must block ALP-2689 on arm64 hosts

ALP-2689 builds and uses `runtime-matters-claude:local` from `examples/dockerfiles`. ALP-2686 exists because local-only images are rejected by the current arm64 preflight when registry manifest inspection fails. On an arm64 operator host, ALP-2689's real-Docker E2E and binding manual verification can fail before lifecycle insert unless ALP-2686 has landed.

Current Linear state marks ALP-2686 independent:

- ALP-2686 relations: no blockers and no blocked issues.
- ALP-2689 blockedBy: ALP-2684, ALP-2685, ALP-2687, ALP-2690.
- ALP-2650 Required order: `ALP-2686 and ALP-2688 are independent`.

Recommended change:

- Add ALP-2686 as blocking ALP-2689.
- Amend ALP-2689 Notes to include ALP-2686 in the blocking list.
- Amend ALP-2650 Required order to include `ALP-2686 before ALP-2689` and remove ALP-2686 from the independent clause.

### Finding 2: ALP-2689 manual verification should preserve the session id

ALP-2689's binding command uses `--session-id "$(uuidgen)"`, then the expected end state requires `rtm kill <session_id>`. The generated UUID is not assigned to a variable in the command block, and `<session_id>` is not defined as a substitutable placeholder alongside `<TMUX_TARGET>` and `<HOST_CWD>`.

This makes the one-shot manual evidence less precise than the rest of the block. Recommended change:

```text
SESSION_ID="$(uuidgen)"
rtm spawn \
  --runtime claude \
  --session-id "$SESSION_ID" \
  ...
rtm kill "$SESSION_ID"
```

Also update the prose to state that `SESSION_ID` is operator-generated and reused for kill verification.

## Dependencies

The reviewed batch depends on Docker, a working example image, tmux, `rtmd`, and operator supplied credentials passed via `--env`. ALP-2689 is the integration point consuming contracts introduced by ALP-2684, ALP-2685, ALP-2686, ALP-2687, and ALP-2690.

## Relevance to Helioy

The findings protect the Nancy selector and PER gate from false readiness. The first prevents architecture dependent failure on Apple Silicon hosts. The second ensures operator-host evidence is reproducible enough for ALP-2654 to treat as terminal gate evidence.

## Open Questions

- Should ALP-2689 require the same host architecture in the manual evidence comment, or is linking ALP-2686 as a blocker sufficient?
- Should ALP-2690 verification avoid exposing the raw credential value in `docker inspect` evidence, for example by checking key presence or a redacted capture?
