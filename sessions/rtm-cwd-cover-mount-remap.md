---
title: Runtime Matters cwd cover Docker mount remap
type: sessions
tags: [backend, runtime-matters, docker, mounts, ALP-2784]
summary: Implemented and reviewed Docker cwd cover detection that suppresses cwd auto mount and remaps workdir.
status: active
source: backend-engineer
confidence: high
created: 2026-05-23
updated: 2026-05-23
---

## Summary

Implemented Item 3 of the ALP-2784 Docker road test fix. An explicit Docker mount whose host source equals the spawn cwd, or is an ancestor of the spawn cwd, now suppresses the implicit cwd auto mount and remaps `--workdir` under the explicit mount target.

Key decisions:

- Keep `SpawnRequest.cwd` as a host path.
- Canonicalize and mutate `request.cwd` during Docker mount preflight so argv assembly uses the same canonical cwd that validation used.
- Share cwd mount planning between preflight and argv generation in `crates/rtm-daemon/src/docker_mount_plan.rs`.
- Replace the old symmetric source overlap rejection with directional cover and descendant checks.

## API Contract

No wire schema changed.

CLI behavior contract for Docker isolation:

```text
rtm spawn --isolation docker --cwd <HOST_CWD> --mount <HOST_SOURCE>:<CONTAINER_TARGET>[:ro|:rw]
```

Rules:

- No explicit mount covering cwd: emit existing implicit bind mount `HOST_CWD:HOST_CWD` and set `--workdir HOST_CWD`.
- Explicit source equal to cwd: suppress implicit cwd mount and set `--workdir CONTAINER_TARGET`.
- Explicit source ancestor of cwd: suppress implicit cwd mount and set `--workdir CONTAINER_TARGET/<relative cwd suffix>`.
- Explicit source descendant of cwd: reject as a protocol mismatch.
- Multiple covers: longest source prefix wins when unique. Equal longest matches are rejected.

## Database Changes

None.

## Security Considerations

- Host paths are canonicalized before comparison to avoid symlink based mismatch between validation and argv emission.
- Docker mount targets continue to be normalized as container absolute paths.
- Host isolation remains unchanged and does not apply Docker mount validation.
- Path shaped Claude environment variables still require coverage by an explicit Docker mount target.

## Performance Notes

The planner is pure path processing over the declared mount list. The cost is linear in the number of mounts. No database or Docker CLI calls were added.

Verification completed:

- `cargo test -p rtm-daemon cwd -- --nocapture`
- `cargo test -p rtm-daemon -- --nocapture`
- `cargo test -p rtm-cli --test docker_e2e -- --nocapture`
- `RTM_E2E_DOCKER=1 cargo test -p rtm-cli --test docker_e2e real_docker_spawn_remaps_workdir_when_mount_covers_cwd -- --nocapture`
- `just check && just build && just test`

The final gate passed, including 284 nextest tests.

## Open Items

- Reviewer Phase B signoff received on topic `rtm-cwd-overlap-item3` with exact phrase: `I sign off on the fix as currently filed`.
- ALP-2797 will later redefine `--cwd` as a container path for the k8s shaped model. This implementation intentionally does not preempt that scope.
