slice: xcontext-dup
scope: cross-crate / cross-context
DUP
internal/runtime/app/src/cli/spawn.rs:L84-L89 :: internal/session/app/src/cli/run.rs:L101-L106 | host mount policy guard | high
internal/runtime/app/src/cli/spawn.rs:L84-L89 :: internal/session/daemon/src/mcp_tools/agent.rs:L39-L48 | host mount policy guard | high
internal/runtime/daemon/src/mcp_bridge.rs:L34-L55 :: internal/session/daemon/src/mcp_bridge.rs:L40-L62 | JSON RPC request dispatch | high
internal/runtime/daemon/src/mcp_bridge.rs:L70-L88 :: internal/session/daemon/src/mcp_bridge.rs:L76-L97 | MCP tool call argument extraction | high
crates/lilo-rm-core/src/mcp.rs:L43-L67 :: internal/session/daemon/src/mcp_bridge.rs:L99-L123 | JSON RPC response constructors | high
crates/lilo-rm-core/src/mcp.rs:L80-L91 :: internal/session/core/src/mcp.rs:L56-L67 | MCP tool error payload | med
crates/lilo-im-store/src/sqlite/audit.rs:L224-L231 :: internal/runtime/store/src/sqlite/lifecycle.rs:L386-L393 | SQL WHERE AND builder | high
internal/runtime/daemon/src/identity.rs:L127-L132 :: internal/session/daemon/src/identity_client.rs:L42-L47 | session ResourceSpec builder | med
internal/runtime/app/build.rs:L96-L105 :: internal/session/app/build.rs:L106-L115 | explicit git SHA lookup | med
internal/runtime/app/build.rs:L74-L83 :: internal/session/app/build.rs:L84-L93 | git path lookup helper | med
internal/runtime/app/build.rs:L107-L115 :: internal/session/app/build.rs:L117-L125 | HEAD short SHA command | med
crates/lilo/build.rs:L78-L82 :: internal/runtime/app/build.rs:L68-L72 | cargo rerun path guard | med
crates/lilo/build.rs:L40-L46 :: internal/session/app/build.rs:L127-L133 | short SHA truncation helper | med
internal/session/driver/src/conv.rs:L89-L96 :: internal/session/store/src/sqlite/spawn_intents.rs:L307-L314 | transcript path extraction | med
internal/runtime/app/build.rs:L232-L243 :: internal/session/core/src/tool_contracts/render.rs:L18-L29 | rust const name rendering | med
internal/session/core/src/agent_config.rs:L32-L43 :: internal/session/daemon/src/agent_config.rs:L66-L78 | tilde home expansion | med
