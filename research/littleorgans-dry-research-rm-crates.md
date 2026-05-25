slice: rm-crates
scope: crates/lilo-rm-core, crates/lilo-rm-client
DUP
crates/lilo-rm-client/tests/typed_helpers.rs:L28-L50 :: crates/lilo-rm-client/tests/integration_event_watcher.rs:L214-L239 | mock runtime socket server | high
crates/lilo-rm-client/tests/typed_helpers.rs:L28-L50 :: crates/lilo-rm-client/tests/integration_event_watcher.rs:L241-L271 | mock runtime socket server | high
crates/lilo-rm-client/tests/integration_event_watcher.rs:L22-L67 :: crates/lilo-rm-client/tests/integration_typed_helpers.rs:L12-L51 | real daemon test harness | med
crates/lilo-rm-client/tests/integration_event_watcher.rs:L70-L86 :: crates/lilo-rm-client/tests/integration_typed_helpers.rs:L54-L70 | wait for daemon socket | high
crates/lilo-rm-client/tests/integration_event_watcher.rs:L273-L277 :: crates/lilo-rm-client/tests/typed_helpers.rs:L22-L26 | temp socket path helper | med
crates/lilo-rm-client/src/lib.rs:L62-L75 :: crates/lilo-rm-client/src/lib.rs:L91-L107 | typed RPC response match | med
crates/lilo-rm-client/src/lib.rs:L78-L88 :: crates/lilo-rm-client/src/lib.rs:L128-L141 | typed RPC response match | med
crates/lilo-rm-core/src/proto.rs:L271-L282 :: crates/lilo-rm-core/src/proto.rs:L295-L306 | nonempty JSON line reader | med
crates/lilo-rm-core/src/launcher.rs:L40-L45 :: crates/lilo-rm-core/src/launcher.rs:L56-L61 | argv command extraction | low
crates/lilo-rm-core/src/cli_output.rs:L362-L364 :: crates/lilo-rm-core/src/cli_output.rs:L366-L368 | optional number display | low
crates/lilo-rm-core/src/version.rs:L122-L140 :: crates/lilo-rm-core/src/types/runtime.rs:L47-L65 | string parsed serde impl | low
crates/lilo-rm-core/src/types/runtime.rs:L47-L65 :: crates/lilo-rm-core/src/types/spawn.rs:L49-L67 | string parsed serde impl | low
crates/lilo-rm-client/tests/typed_helpers.rs:L417-L437 :: crates/lilo-rm-client/tests/typed_helpers.rs:L440-L460 | nudge outcome test body | med
crates/lilo-rm-core/src/types/spawn.rs:L362-L377 :: crates/lilo-rm-core/src/types/spawn.rs:L380-L386 | mount spec parse assertions | low
crates/lilo-rm-core/src/types/spawn.rs:L399-L406 :: crates/lilo-rm-core/src/types/spawn.rs:L409-L416 | tilde expansion assertions | low
crates/lilo-rm-core/tests/serde_snapshots.rs:L336-L349 :: crates/lilo-rm-core/tests/serde_snapshots.rs:L352-L362 | missing field JSON test | low
crates/lilo-rm-core/src/tool_contracts.rs:L143-L152 :: crates/lilo-rm-core/src/tool_contracts.rs:L156-L160 | schema description injection | low
