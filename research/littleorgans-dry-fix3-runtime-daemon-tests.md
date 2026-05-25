# littleorgans dry fix3 runtime daemon tests

## Summary

Consolidated repeated test fixtures and assertions across the runtime daemon, runtime store, and runtime launcher test lane. All changes stayed in test code or `#[cfg(test)]` helper surface inside allowed runtime files.

## Files changed

1. `internal/runtime/daemon/src/docker_argv.rs`
2. `internal/runtime/daemon/src/spawn_preflight/tests/mounts.rs`
3. `internal/runtime/daemon/src/server/tests.rs`
4. `internal/runtime/daemon/src/service.rs`
5. `internal/runtime/daemon/src/backend.rs`
6. `internal/runtime/daemon/src/shim_socket.rs`
7. `internal/runtime/daemon/src/server/config.rs`
8. `internal/runtime/launchers/tests/conformance.rs`
9. `internal/runtime/store/src/sqlite/lifecycle/tests.rs`

## Work completed

`docker_argv.rs` now uses one test image constant and a shared headless Docker launch helper for repeated default launch setup.

`spawn_preflight/tests/mounts.rs` now uses one async helper for accepted Docker preflight paths, plus one assertion helper for no conflict responses.

`server/tests.rs` now shares the terminal tmux nudge failure setup and assertion for exited and lost lifecycle states.

`service.rs` now uses a `ServiceFixture` that owns the temp directory, config, and database handle for both service tests.

`backend.rs` and `shim_socket.rs` now share `DaemonConfig` test fixture construction through `#[cfg(test)]` methods on `DaemonConfig`.

`launchers/tests/conformance.rs` now uses one `probe_request` helper for the integration test request literal. The production `warm_registry` literal in `internal/runtime/launchers/src/lib.rs` was left unchanged by the lane rule.

`store/src/sqlite/lifecycle/tests.rs` now uses one `lifecycle_store` helper for repeated temp database setup.

The `tmux.rs` finding was not changed because it is production code and was outside this lane.

## Verification

Clean:

```bash
cargo clippy -p lilo-runtime-daemon -p lilo-runtime-store -p lilo-runtime-launchers --all-targets -- -D warnings
```

Clean:

```bash
cargo test -p lilo-runtime-daemon -p lilo-runtime-store -p lilo-runtime-launchers
```

Test result highlights:

1. `lilo-runtime-daemon`: 88 passed.
2. `lilo-runtime-launchers`: 2 integration tests passed, 0 unit tests.
3. `lilo-runtime-store`: 6 passed.
4. Doc tests for all three crates passed.

## Line limit check

All edited source files remain under 700 lines. Largest edited file is `internal/runtime/daemon/src/docker_argv.rs` at 488 lines.
