---
title: RTM Docker tmux direct run fix
type: sessions
tags: [backend, runtime-matters, docker, tmux, ALP-2784]
summary: Replaced detached Docker attach wrapper for tmux spawns with direct interactive docker run.
status: active
source: backend-engineer
confidence: high
created: 2026-05-23
updated: 2026-05-23
---

## Summary

Implemented the Item 2 fix for `rtm spawn --target tmux:... --isolation docker` blank pane behavior. The Docker tmux launch path now runs the container directly in the shim process with interactive TTY flags instead of spawning a detached container and then attaching through a shell wrapper.

Commit: `c2d8d26 nancy[ALP-2784]: Run Docker tmux sessions directly`

Reviewer sign-off received on 2026-05-23: `I sign off on the fix as currently filed.`

## API Contract

No public API request or response schema changes.

Behavioral launch contract for Docker tmux targets changed from:

- `/bin/sh -c "docker run -d -i -t ...; docker attach ..."`

To:

- `docker run --rm ... -i -t --sig-proxy=false <image> <runtime>`

The CLI surface remains unchanged.

## Database Changes

None.

## Security Considerations

The change removes a shell interpolation layer from the tmux Docker path, eliminating shell quoting risk for runtime args, environment values, and mount paths in that path. Existing Docker preflight, image selection, mount validation, env forwarding, container naming, and session labels remain unchanged.

`--sig-proxy=false` is retained on the direct run path so pane close or pane signal behavior does not kill the container unexpectedly. Runtime termination still uses the existing Docker kill path by session container name.

## Performance Notes

The tmux Docker path now avoids the extra `docker attach` process and shell wrapper. Runtime lifecycle tracking still records the host Docker CLI child PID and Docker kill still targets the session named container.

## Verification

Automated gates passed before commit:

- `cargo test -p rtm-daemon docker_argv -- --nocapture`
- `cargo test -p rtm-daemon docker_tmux_policy_uses_direct_docker_run_for_host_shim -- --nocapture`
- `cargo test -p rtm-cli docker_tmux_pattern_a_container_survives_pane_close -- --nocapture`
- `just check && just build && just test`

`just test` ran 274 tests with 274 passed.

Reviewer independently verified:

- `cargo test -p rtm-daemon docker_argv`
- `cargo test -p rtm-daemon docker_tmux_policy_uses_direct_docker_run_for_host_shim`
- `cargo test -p rtm-cli --test integration_pass5 docker_tmux_pattern_a_container_survives_pane_close`
- `cargo test -p rtm-daemon`
- `cargo test -p rtm-cli --test integration_pass5`

Manual local image verification using Stuart's workflow showed `rtm --version` as `runtime-matters 0.2.4+c2d8d26`; `rtm spawn --target tmux:3:5.1 --isolation docker ...` followed by `rtm capture` displayed the Claude Code UI in the target pane.

## Open Items

The manual capture showed an unrelated Claude image/install metadata warning: `Auto-update failed` and `installMethod is native, but claude command not found`. This is not part of the blank pane transport bug.
