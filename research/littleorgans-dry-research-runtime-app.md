slice: runtime-app
scope: internal/runtime/app
DUP
internal/runtime/app/tests/docker_e2e.rs:L309-L353 :: internal/runtime/app/tests/common/harness.rs:L351-L423 | daemon lifecycle harness | high
internal/runtime/app/tests/cli_flags.rs:L182-L193 :: internal/runtime/app/tests/spawn_target.rs:L520-L531 | spawn command builder | med
internal/runtime/app/tests/docker_e2e.rs:L292-L306 :: internal/runtime/app/tests/common/harness.rs:L271-L277 | command env builder | med
internal/runtime/app/tests/critical_scenarios.rs:L16-L33 :: internal/runtime/app/tests/integration_pass2.rs:L78-L95 | sigkill exited scenario | med
internal/runtime/app/tests/critical_scenarios.rs:L36-L55 :: internal/runtime/app/tests/integration_pass2.rs:L98-L115 | shim lost scenario | med
internal/runtime/app/tests/integration_events_cursor.rs:L317-L330 :: internal/runtime/app/tests/integration_events_cursor.rs:L332-L345 | event count wait helper | med
internal/runtime/app/tests/critical_scenarios.rs:L191-L198 :: internal/runtime/app/tests/integration_pass5.rs:L313-L320 | json status wait helper | med
internal/runtime/app/tests/spawn_target.rs:L98-L114 :: internal/runtime/app/benches/spawn_latency.rs:L26-L44 | headless spawn request literal | med
internal/runtime/app/tests/spawn_target.rs:L506-L518 :: internal/runtime/app/tests/common/wait.rs:L70-L85 | log wait polling helper | low
internal/runtime/app/tests/docker_e2e.rs:L369-L382 :: internal/runtime/app/tests/common/harness.rs:L439-L449 | child exit wait helper | low
internal/runtime/app/tests/integration_events_cursor.rs:L389-L394 :: internal/runtime/app/tests/integration_events_cursor.rs:L396-L401 | watcher count wait helper | low
internal/runtime/app/tests/integration_pass4.rs:L65-L72 :: internal/runtime/app/tests/common/wait.rs:L31-L38 | events polling helper | low
internal/runtime/app/benches/spawn_latency.rs:L55-L61 :: internal/runtime/app/benches/status_query.rs:L40-L46 | bench sample count helper | low
internal/runtime/app/src/cli/version.rs:L5-L14 :: internal/runtime/app/src/cli/doctor.rs:L6-L13 | simple rpc emit handler | low
