---
title: Roadtest run detach removal
type: sessions
tags: [backend, cli, roadtest, session]
summary: Removed the dead lilo run --detach flag after proving run is already fire and forget.
status: active
source: backend-engineer
confidence: high
created: 2026-05-30
updated: 2026-05-30
---

## Summary

Implemented ROADTEST MoE item 5 on `fix/roadtest`.

The item began as a request to implement `lilo run --detach`, but Phase A proved the premise was false. `lilo run` already returns after the session reaches Running and never attaches, streams, or waits for runtime exit. The reviewed decision was Option A: remove the misleading flag instead of inventing a foreground mode.

Commit: `2f7408e fix(session): remove no-op run detach flag`.

## API Contract

No HTTP API changed.

CLI contract changed:

```text
sm run <RUNTIME> --role <ROLE> [--dir <DIR>] [--namespace <NAMESPACE>] [--label <LABEL>] [--agent-config <AGENT_CONFIG>] [--isolation <ISOLATION>] [--image <IMAGE>] [--mount <HOST:CONTAINER[:ro|:rw]>] [--target <TARGET>] [--force]
```

Removed:

```text
sm run ... --detach
```

`--detach` now fails at clap parsing as an unexpected argument. Default run behavior remains unchanged: spawn, register, print the session, and return.

## Database Changes

None.

The session spawn records and spawn intent rows remain unchanged. Existing tests still prove `sm run` resolves the spawn intent and persists the session without the removed flag.

## Security Considerations

No authorization path changed.

The removal reduces misleading surface area. Operators no longer receive a false claim that `sm run` can wait on or attach to a runtime.

## Performance Notes

No runtime path changed. The removal is behaviorally inert.

Gates run:

- `cargo test -p lilo-session-app --test cli_get_test run_detach_is_rejected_by_clap -- --nocapture`, PASS
- `cargo test -p lilo-session-app --test cli_help_surface_test run_help_describes_every_flag -- --nocapture`, PASS
- `just codegen --check`, PASS
- `just check`, PASS
- `just build`, PASS
- `just test`, PASS, 558 of 558
- `fmm generate && fmm validate`, PASS
- `rg -- '--detach'`, only rejection and absence tests plus out of scope docker and git fixture hits

## Open Items

Foreground or attach behavior remains deferred. This item intentionally did not add a stream, attach, or wait mode.

Phase B reviewer signoff was received, and `2f7408e` was pushed to `origin/fix/roadtest`.
