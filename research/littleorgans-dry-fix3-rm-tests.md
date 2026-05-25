# littleorgans dry fix 3: rm tests

## Files changed

- `crates/lilo-rm-client/tests/common/mock_socket.rs`
- `crates/lilo-rm-client/tests/common/daemon.rs`
- `crates/lilo-rm-client/tests/typed_helpers.rs`
- `crates/lilo-rm-client/tests/integration_event_watcher.rs`
- `crates/lilo-rm-client/tests/integration_typed_helpers.rs`
- `crates/lilo-rm-core/src/types/spawn.rs` test module only
- `crates/lilo-rm-core/tests/serde_snapshots.rs`

## Helpers consolidated

- Moved repeated mock runtime socket setup into `tests/common/mock_socket.rs` with `mock_runtime_response`, `mock_runtime_exchange`, and `temp_socket_path`.
- Moved real daemon startup, stop, and socket readiness polling into `tests/common/daemon.rs`.
- Reused the shared daemon harness from both rm client integration tests.
- Consolidated nudge outcome assertions in `typed_helpers.rs` with `assert_nudge_helper_preserves_outcome`.
- Consolidated mount spec parse assertions and tilde expansion assertions inside the `#[cfg(test)]` module of `lilo-rm-core/src/types/spawn.rs`.
- Consolidated spawn request JSON error assertions and serde round trip assertions in `serde_snapshots.rs`.

## Verification

- `cargo clippy -p lilo-rm-client -p lilo-rm-core --all-targets -- -D warnings` passed.
- `cargo test -p lilo-rm-client -p lilo-rm-core` passed.

## Left

- Production duplicate candidates from the research file were intentionally left untouched.
- No `Cargo.toml` files were edited.
