# runtime-app-tests DRY fix3 report

## Files changed

1. `internal/runtime/app/tests/common/mod.rs`
2. `internal/runtime/app/tests/common/harness.rs`
3. `internal/runtime/app/tests/common/process.rs`
4. `internal/runtime/app/tests/common/wait.rs`
5. `internal/runtime/app/tests/cli_flags.rs`
6. `internal/runtime/app/tests/spawn_target.rs`
7. `internal/runtime/app/tests/critical_scenarios.rs`
8. `internal/runtime/app/tests/integration_pass2.rs`
9. `internal/runtime/app/tests/integration_pass4.rs`
10. `internal/runtime/app/tests/integration_pass5.rs`
11. `internal/runtime/app/tests/integration_events_cursor.rs`
12. `internal/runtime/app/tests/docker_e2e.rs`
13. `internal/runtime/app/benches/spawn_latency.rs`
14. `internal/runtime/app/benches/status_query.rs`

## Helpers consolidated

- Centralized headless spawn command construction in `tests/common/mod.rs` and reused it from CLI flag and spawn target tests.
- Centralized headless `SpawnRequest` construction in `tests/common/harness.rs` and reused it from spawn target tests and spawn latency bench.
- Promoted `RtmHarness::rtm_command` for shared command/env setup and reused it from Docker E2E and kill format helpers.
- Centralized child exit polling in `tests/common/process.rs` and reused the harness daemon shutdown path.
- Centralized JSON status, events since cursor, RPC event polling, watcher count polling, log contains polling, and SIGKILL scenario setup in `tests/common/wait.rs`.
- Removed local duplicate wait helpers from critical scenario, pass4, pass5, and event cursor tests.
- Replaced duplicated benchmark sample count parsing with `common::bench_sample_count`.
- Reworked Docker E2E daemon setup to use `RtmHarness::start_with_docker_image`, removing the local `RtmEnv` and `RtmDaemon` harness.

## Verification

- `cargo clippy -p lilo-runtime-app --all-targets -- -D warnings` passed.
- `cargo test -p lilo-runtime-app` passed.

## Anything left

- The production duplicate listed in the research file, `internal/runtime/app/src/cli/version.rs` and `internal/runtime/app/src/cli/doctor.rs`, was intentionally not touched because this lane was limited to test and bench code.
