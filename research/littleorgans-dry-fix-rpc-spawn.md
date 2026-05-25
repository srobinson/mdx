# littleorgans dry-fix rpc-spawn report

## Summary

Refactored duplicated MCP and mount-policy plumbing into `lilo-rm-core` for the rpc-spawn lane. No new dependencies were needed.

## Files changed

- `crates/lilo-rm-core/src/mcp.rs`
- `crates/lilo-rm-core/src/lib.rs`
- `internal/session/core/src/mcp.rs`
- `internal/session/daemon/src/mcp_bridge.rs`
- `internal/runtime/daemon/src/mcp_bridge.rs`
- `internal/session/daemon/src/mcp_tools/agent.rs`
- `internal/session/daemon/src/mcp_tools/control.rs`
- `internal/runtime/app/src/cli/spawn.rs`
- `internal/session/app/src/cli/run.rs`

## Shared API signatures

Module: `lilo_rm_core::mcp`

```rust
pub enum McpRequest {
    Initialize,
    Ping,
    ToolsList,
    ToolsCall(Option<Value>),
}

pub struct ToolCallRequest {
    pub name: String,
    pub arguments: Value,
}

pub struct HostMountPolicyError;

pub fn parse_json_rpc_line(line: &str) -> Result<JsonRpcRequest, Box<JsonRpcResponse>>;
pub fn serialize_json_rpc_response(response: &JsonRpcResponse) -> String;
pub fn prepare_mcp_request(request: JsonRpcRequest) -> Option<(Value, Result<McpRequest, JsonRpcError>)>;
pub fn json_rpc_response_from_result(id: Value, result: Result<Value, JsonRpcError>) -> JsonRpcResponse;
pub fn tool_call_request(params: Option<Value>) -> Result<ToolCallRequest, JsonRpcError>;
pub fn tool_error_with_meta_key(meta_key: impl Into<String>, message: impl Into<String>) -> Value;
pub fn ensure_mounts_allowed_for_isolation(isolation: &IsolationPolicy, mounts: &[MountSpec]) -> Result<(), HostMountPolicyError>;
```

`lilo-session-core::mcp` now re-exports the shared JSON-RPC and MCP helpers from `lilo-rm-core` while preserving the session-specific `sm_tool_error` metadata key through its local `tool_error` wrapper.

## Consolidation notes

- Session and runtime MCP bridges now share JSON-RPC line parsing, response serialization, request dispatch classification, response construction, and MCP `tools/call` argument extraction.
- Runtime and session tool error payload construction now share the same payload builder with substrate-specific metadata keys.
- Runtime CLI, session CLI, and session MCP `agent_run` now call the same host-mount policy guard.
- Session daemon tool RPC error arms in `agent.rs` and `control.rs` now route through one helper instead of repeating the `RpcResponse::Error` and unexpected-response pair at every call site.

## Dependencies

No new dependency was needed.

## Verification

```text
cargo check -p lilo-rm-core -p lilo-session-core -p lilo-session-daemon -p lilo-runtime-daemon -p lilo-session-app -p lilo-runtime-app
Finished `dev` profile [unoptimized + debuginfo] target(s) in 8.57s

cargo clippy -p lilo-rm-core --all-targets -- -D warnings
Finished `dev` profile [unoptimized + debuginfo] target(s) in 3.33s

cargo clippy -p lilo-session-daemon -p lilo-runtime-daemon -p lilo-session-core -- -D warnings
Finished `dev` profile [unoptimized + debuginfo] target(s) in 8.26s
```

## Left open

None for this lane.
