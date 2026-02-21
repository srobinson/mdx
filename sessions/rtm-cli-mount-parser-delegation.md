---
title: rtm-cli Mount Parser Delegation
type: sessions
tags: [backend, runtime-matters, rtm-cli, parser]
summary: Delegated rtm-cli --mount parsing to rtm-core MountSpec FromStr and removed duplicate CLI helpers.
status: active
source: backend-engineer
confidence: high
created: 2026-05-24
updated: 2026-05-24
---

## Summary

Implemented `i2-cli-delegation` on branch `refactor/expose-mount-parser`.

Commit: `ba0642bfa4bc`.

`crates/rtm-cli/src/cli/spawn.rs` now wires clap `--mount` parsing through `|s: &str| s.parse::<MountSpec>()`, delegating to `rtm_core::MountSpec::from_str`. The duplicate private `parse_mount_spec` and `expand_mount_source` helpers were deleted from rtm-cli. `reject_host_mounts` remains in rtm-cli so the public CLI still rejects `--mount` with `--isolation host`.

## API Contract

No HTTP API changes.

CLI contract preserved:

```text
rtm spawn --mount HOST:CONTAINER[:ro|:rw]
```

Behavior remains aligned with existing CLI tests, including default read only mode, explicit read write mode, leading tilde expansion, malformed value rejection, and host isolation rejection.

## Database Changes

None.

## Security Considerations

The CLI still rejects Docker only mount flags under host isolation before sending a daemon request. Core parsing remains independent of clap and only normalizes the caller supplied mount source and target fields.

## Performance Notes

No runtime performance impact expected. The change removes duplicate parser code and uses the shared `FromStr` implementation already present in rtm-core.

## Verification

Passed:

```text
cargo test -p lilo-rm-core
cargo test -p rtm-cli
cargo test -p rtm-daemon
fmm generate && fmm validate
git diff --check
rg confirmed no private rtm-cli mount parser symbols remain
```

## Open Items

None for this slice. Branch is ahead of origin by one commit and has not been pushed, pending orchestrator push authorization.
