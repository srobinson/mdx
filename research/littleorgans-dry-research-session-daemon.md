slice: session-daemon
scope: internal/session/daemon
DUP
internal/session/daemon/src/handler/spawn.rs:L106-L142 :: internal/session/daemon/src/handler/spawn.rs:L202-L226 | 3x immediate tx scaffold | high
internal/session/daemon/src/handler/sessions.rs:L59-L77 :: internal/session/daemon/src/handler/sessions.rs:L79-L96 | selector fanout error loop | med
internal/session/daemon/src/handler/messaging.rs:L80-L86 :: internal/session/daemon/src/handler/messaging.rs:L88-L97 | mail count response wrapper | med
internal/session/daemon/src/mcp_tools/mail.rs:L75-L91 :: internal/session/daemon/src/mcp_tools/mail.rs:L93-L109 | mail count selector wrapper | med
internal/session/daemon/src/mcp_tools/args.rs:L77-L92 :: internal/session/daemon/src/mcp_tools/args.rs:L111-L127 | optional string array parser | med
internal/session/daemon/src/mcp_tools/agent.rs:L106-L107 :: internal/session/daemon/src/mcp_tools/control.rs:L117-L118 | 15x RPC error match arms | med
internal/session/daemon/src/service.rs:L131-L141 :: internal/session/daemon/src/service.rs:L151-L161 | runtime service test setup | med
internal/session/daemon/src/events.rs:L310-L332 :: internal/session/daemon/src/service.rs:L213-L235 | session fixture builder | low
internal/session/daemon/src/handler/spawn/tests.rs:L196-L213 :: internal/session/daemon/tests/namespace_rpc.rs:L276-L293 | spawn request builder | med
internal/session/daemon/tests/common/mod.rs:L189-L223 :: internal/session/daemon/tests/capture_target.rs:L115-L143 | spawn test helper | med
internal/session/daemon/tests/handler/spawn_namespace.rs:L9-L46 :: internal/session/daemon/tests/handler/spawn_namespace.rs:L49-L87 | namespace spawn test body | med
internal/session/daemon/tests/capture_target.rs:L58-L70 :: internal/session/daemon/tests/capture_target.rs:L73-L85 | target rejection test body | low
internal/session/daemon/src/events.rs:L16-L35 :: internal/session/daemon/src/lifecycle.rs:L13-L35 | background task guard wrapper | low
internal/session/daemon/src/mcp_bridge.rs:L99-L106 :: internal/session/daemon/src/mcp_bridge.rs:L108-L115 | JSON RPC response constructor | low
