slice: SYNTHESIS
scope: littleorgans production Rust (crates/ + internal/ + tools/), ~44k LOC
method: 10 codex codebase-analyst agents, warroom dry-sweep, 2026-05-28
totals: 101 duplicate findings + 13 dead-code findings
raw: ~/.mdx/research/littleorgans-dry-research-<slice>.md (10 files)

# TIER 1 — cross-cutting production consolidations (highest value)

## T1.1 MCP / JSON-RPC plumbing reimplemented in 3+ contexts  [HIGH]
internal/session/daemon/src/mcp_bridge.rs:L34-55 :: internal/runtime/daemon/src/mcp_bridge.rs:L34-55 | JSON-RPC request dispatch
internal/session/daemon/src/mcp_bridge.rs:L70-97 :: internal/runtime/daemon/src/mcp_bridge.rs:L70-88 | tool-call arg extraction
internal/session/daemon/src/mcp_bridge.rs:L99-123 :: crates/lilo-rm-core/src/mcp.rs:L43-67 | JSON-RPC response constructors
internal/session/core/src/mcp.rs:L56-67 :: crates/lilo-rm-core/src/mcp.rs:L80-91 | tool error payload [MED]
internal/session/daemon/src/mcp_tools/agent.rs:L106 :: internal/session/daemon/src/mcp_tools/control.rs:L117 | 15x RPC error match arms [MED]
=> extract one JSON-RPC/MCP bridge into lilo-rm-core (or lilo-common); both daemons speak the same wire.

## T1.2 build.rs git-SHA logic copied across build scripts  [MED]
internal/runtime/app/build.rs:L74-125 :: internal/session/app/build.rs:L84-133 | git path/SHA/short-SHA helpers
crates/lilo/build.rs:L40-82 :: internal/runtime/app/build.rs:L68-72 | rerun guard + SHA truncation
=> shared build-support module (tools/ or a build-deps crate).

## T1.3 store-layer SQL patterns repeated within and across stores  [HIGH]
internal/runtime/store/src/sqlite/lifecycle.rs:L86-105 | lifecycle SELECT column list repeated 4x
internal/runtime/store/src/sqlite/lifecycle.rs:L324-376 | encoded bind order repeated
crates/lilo-im-store/src/sqlite/audit.rs:L94-222 | audit row column order + codecs repeated
crates/lilo-im-store/src/sqlite/audit.rs:L224-231 :: internal/runtime/store/src/sqlite/lifecycle.rs:L386-393 | SQL WHERE-AND builder (cross-context)
internal/session/store/src/sqlite/labels.rs:L66-106 | label upsert SQL helper
=> store helpers: column constants, bind helper, shared WHERE/AND builder.

## T1.4 host-mount policy guard triplicated  [HIGH]
internal/runtime/app/src/cli/spawn.rs:L84-89 :: internal/session/app/src/cli/run.rs:L101-106 :: internal/session/daemon/src/mcp_tools/agent.rs:L39-48 | host mount policy guard
=> single policy fn (likely lilo-rm-core or lilo-common).

## T1.5 misc cross-context  [MED]
internal/session/core/src/agent_config.rs:L32-43 :: internal/session/daemon/src/agent_config.rs:L66-78 | tilde/home expansion (lilo-paths should own this)
internal/runtime/daemon/src/identity.rs:L127-132 :: internal/session/daemon/src/identity_client.rs:L42-47 | session ResourceSpec builder

# TIER 2 — intra-module production dups (medium value)

internal/session/daemon/src/handler/spawn.rs:L106-226 | 3x immediate-tx scaffold [HIGH]
internal/runtime/daemon/src/event_log.rs:L126-235 | event-append persistence path 2x [HIGH]
internal/runtime/daemon/src/service.rs:L56-82 :: internal/runtime/daemon/src/server/runner.rs:L18-40 | daemon bootstrap+reconcile setup [HIGH]
internal/runtime/launchers/src/claude.rs:L5-20 :: internal/runtime/launchers/src/codex.rs:L5-20 | launchers differ only by binary+kind; parameterize [MED]
internal/runtime/daemon/src/docker_preflight.rs:L94-175 | docker image-inspect flow 2x [MED]
internal/runtime/daemon/src/docker_runtime.rs:L52-86 | docker running-probe async-blocking 2x [MED]
internal/session/store/src/sqlite/spawn_intents.rs:L250-291 | spawn-intent status update plumbing [MED]
internal/session/driver/src/conv.rs:L89-96 :: internal/session/store/src/sqlite/spawn_intents.rs:L307-314 | transcript path extraction [HIGH] (also flagged xcontext)
crates/lilo-im-core/src/types.rs:L126-155 | action variants repeated [MED]
crates/lilo/src/cli/mod.rs:L12-151 | command names+categories repeated [MED]
crates/lilo-rm-client/src/lib.rs:L62-141 | typed RPC response match 2x [MED]
crates/lilo-rm-core/src/types/{runtime,spawn}.rs:L47-67 | string-parsed serde impl repeated [LOW]

# TIER 3 — dead code (13, all med/low; cargo flagged none, all via fmm zero-use-site)

read_tool_sources @ internal/session/core/src/tool_sources.rs:24 | no use-sites [MED]
install @ internal/session/app/src/mcp/panic_guard.rs:1 | empty stub unused [MED]
TOOL_NAMES @ internal/session/app/src/mcp/tools.rs:1 | no use-sites [MED]
protocol, response @ internal/session/app/src/mcp.rs:3-4 | unused reexport modules [LOW]
Rtm{KillByPid,Status,Version,Watchers}{Args,Response} @ internal/runtime/app/src/generated/contracts.rs:3-15 | 8 generated aliases unused [LOW]
=> generator over-emits contract aliases; trim generator or accept as generated surface.

# TIER 4 — test-infrastructure duplication (large bucket, lowest priority)
~50 of the 101 findings are test helpers: mock Unix-socket servers, daemon lifecycle harnesses,
fixture builders, wait/poll helpers, CLI assert helpers. Recurring in rm-crates (17), runtime-app (14),
session-daemon, session-core, session-app.
=> per-crate tests/common shared helpers; not blocking, but cheap wins.
