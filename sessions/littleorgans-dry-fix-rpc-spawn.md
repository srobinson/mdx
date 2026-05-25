---
title: littleorgans dry-fix rpc-spawn implementation
type: sessions
tags: [backend, littleorgans, rust, mcp, dry]
summary: Consolidated duplicated MCP JSON-RPC plumbing and host-mount policy checks into lilo-rm-core, including clippy-clean boxed parse errors.
status: active
source: backend-engineer
confidence: high
created: 2026-05-28
updated: 2026-05-28
---

## Summary

Implemented the `dry-fix` rpc-spawn lane by moving shared MCP JSON-RPC parsing, serialization, dispatch classification, tool-call argument extraction, tool error payload construction, and host-mount policy checking into `lilo-rm-core`. Follow-up clippy reproduction found `result_large_err` on `parse_json_rpc_line`, fixed by boxing the large parse-error response. Session core now re-exports the shared MCP primitives while preserving the session-specific `sm_tool_error` metadata key.

## API Contract

No HTTP API contract changed. The internal Rust API added these shared functions and types in `lilo_rm_core::mcp`:

```rust
pub enum McpRequest;
pub struct ToolCallRequest;
pub struct HostMountPolicyError;
pub fn parse_json_rpc_line(line: &str) -> Result<JsonRpcRequest, Box<JsonRpcResponse>>;
pub fn serialize_json_rpc_response(response: &JsonRpcResponse) -> String;
pub fn prepare_mcp_request(request: JsonRpcRequest) -> Option<(Value, Result<McpRequest, JsonRpcError>)>;
pub fn json_rpc_response_from_result(id: Value, result: Result<Value, JsonRpcError>) -> JsonRpcResponse;
pub fn tool_call_request(params: Option<Value>) -> Result<ToolCallRequest, JsonRpcError>;
pub fn tool_error_with_meta_key(meta_key: impl Into<String>, message: impl Into<String>) -> Value;
pub fn ensure_mounts_allowed_for_isolation(isolation: &IsolationPolicy, mounts: &[MountSpec]) -> Result<(), HostMountPolicyError>;
```

## Database Changes

None.

## Security Considerations

The shared MCP parsing and dispatch path preserves JSON-RPC error handling for parse errors, unknown methods, missing params, and missing tool names. The shared host-mount guard keeps `--mount` rejected with host isolation across runtime CLI, session CLI, and MCP `agent_run` entry points.

## Performance Notes

No new I/O, database calls, or background work were added. The refactor removes duplicated local branching only.

Verification completed:

```text
cargo check -p lilo-rm-core -p lilo-session-core -p lilo-session-daemon -p lilo-runtime-daemon -p lilo-session-app -p lilo-runtime-app
Finished `dev` profile [unoptimized + debuginfo] target(s) in 8.57s

cargo clippy -p lilo-rm-core --all-targets -- -D warnings
Finished `dev` profile [unoptimized + debuginfo] target(s) in 3.33s

cargo clippy -p lilo-session-daemon -p lilo-runtime-daemon -p lilo-session-core -- -D warnings
Finished `dev` profile [unoptimized + debuginfo] target(s) in 8.26s
```

## Open Items

None for this lane.
## Closeout

Sent bus closeout on topic `dry-fix`: `done rpc-spawn fix: clippy clean`. No git commands were run.
