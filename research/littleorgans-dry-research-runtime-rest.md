slice: runtime-rest
scope: internal/runtime/{launchers,platform,store}, internal/{db,identity,wire}
DUP
internal/runtime/launchers/src/claude.rs:L5-L20 :: internal/runtime/launchers/src/codex.rs:L5-L20 | launcher impl differs only binary and kind | med
internal/runtime/launchers/src/lib.rs:L39-L50 :: internal/runtime/launchers/tests/conformance.rs:L28-L39 | SpawnRequest probe literal repeated | med
internal/runtime/store/src/sqlite/lifecycle.rs:L86-L88 :: internal/runtime/store/src/sqlite/lifecycle.rs:L103-L105 | lifecycle SELECT columns repeated four times | high
internal/runtime/store/src/sqlite/lifecycle.rs:L324-L336 :: internal/runtime/store/src/sqlite/lifecycle.rs:L365-L376 | encoded lifecycle bind order repeated | high
internal/runtime/store/src/sqlite/lifecycle/codec.rs:L123-L143 :: internal/runtime/store/src/sqlite/lifecycle.rs:L198-L203 | lifecycle state string arms repeated | med
internal/runtime/store/src/sqlite/lifecycle/tests.rs:L13-L16 :: internal/runtime/store/src/sqlite/lifecycle/tests.rs:L34-L37 | LifecycleStore temp setup repeated five times | low
internal/runtime/platform/src/tmux.rs:L63-L69 :: internal/runtime/platform/src/tmux.rs:L71-L77 | capture status error handling repeated | low
