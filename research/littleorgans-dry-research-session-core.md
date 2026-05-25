slice: session-core
scope: internal/session/core, internal/session/driver, internal/session/store
DUP
internal/session/store/src/sqlite/labels.rs:66-77 :: internal/session/store/src/sqlite/labels.rs:90-106 | label upsert SQL helper | high
internal/session/driver/src/conv.rs:89-96 :: internal/session/store/src/sqlite/spawn_intents.rs:307-314 | lifecycle transcript path extraction | high
internal/session/store/src/sqlite/events.rs:370-392 :: internal/session/store/src/sqlite/namespaces.rs:230-252 | test Session fixture builder | med
internal/session/driver/tests/rtmd_nudge.rs:49-81 :: internal/session/driver/tests/rtmd_spawn.rs:30-75 | Unix socket RPC mock setup | med
internal/session/core/src/tool_contracts/registry.rs:22-32 :: internal/session/core/src/tool_sources.rs:24-36 | tool source newline aggregation | med
internal/session/store/src/sqlite/spawn_intents.rs:250-269 :: internal/session/store/src/sqlite/spawn_intents.rs:271-291 | spawn intent status update plumbing | med
internal/session/store/src/sqlite/mail.rs:106-108 :: internal/session/store/src/sqlite/sessions.rs:382-384 | row error range helper | low
internal/session/core/src/proto/tests.rs:103-106 :: internal/session/core/src/proto/tests.rs:123-126 | RPC JSON round trip assertions | low
