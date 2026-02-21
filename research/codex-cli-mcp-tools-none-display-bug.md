---
title: OpenAI Codex CLI shows "Tools: (none)" for functional MCP servers
type: research
tags: [codex, mcp, tool-discovery, schema-conversion, display-bug]
summary: Codex /mcp displays "Tools: (none)" due to a divergence between the display path (which depends on McpServerStatus.tools being populated) and the call path (which routes directly to the MCP server via tools/call). Multiple root causes documented, including schema conversion failures, startup timing, and known display-only bugs.
status: active
source: deep-research
confidence: high
created: 2026-03-21
updated: 2026-03-21
---

## Executive Summary

When Codex CLI's `/mcp` command shows `Tools: (none)` for a server whose tools are still callable, the root cause is a divergence between two independent code paths: the **display path** (which populates `McpServerStatus.tools` from cached/snapshotted tool lists) and the **call path** (which routes `tools/call` directly through the `RmcpClient` to the MCP server). At least five distinct failure modes can produce this symptom. For the helioy-bus server specifically, the most probable cause is **JSON schema conversion failure** on the `register_agent` tool's `profile: dict | None` parameter, which generates an `anyOf` schema node that historically causes Codex's Rust deserializer to fail.

## Detailed Findings

### 1. How Codex discovers and lists MCP tools

Codex CLI uses a Rust MCP client (`rmcp-client`) that follows the standard MCP protocol:

1. **Initialization**: Sends `initialize` JSON-RPC, receives server capabilities.
2. **Tool discovery**: Calls `tools/list` (with optional pagination) to enumerate available tools.
3. **Schema conversion**: Each tool's `inputSchema` is passed through `sanitize_json_schema()` then `serde_json::from_value::<JsonSchema>()` to convert from arbitrary JSON Schema into Codex's internal `JsonSchema` enum (a limited subset).
4. **Aggregation**: `McpConnectionManager.list_all_tools()` collects tools from all servers, prefixing names with `mcp__{server}__{tool}`.
5. **Display**: The TUI's `new_mcp_tools_output_from_statuses()` reads `McpServerStatus.tools` (a map of tool names to Tool definitions) and renders them. If the map is empty, it shows `"Tools: (none)"`.

The `JsonSchema` enum is `#[serde(tag = "type")]`, meaning it dispatches deserialization based on a `type` field. Schema nodes without `type` (like bare `anyOf` wrappers) must have one inferred by the sanitizer.

Source: Codex source code in `codex-rs/core/src/tools/spec.rs`, `codex-rs/core/src/mcp_connection_manager.rs`, `codex-rs/tui_app_server/src/history_cell.rs`.

### 2. Five failure modes that produce "Tools: (none)" while tools remain callable

#### A. JSON Schema conversion failure (most probable for helioy-bus)

When `mcp_tool_to_openai_tool()` fails to deserialize a tool's `inputSchema` into `JsonSchema`, the error propagates and that tool is excluded from the display list. The tool remains callable because `call_tool()` routes the JSON-RPC `tools/call` directly to the MCP server without needing Codex's internal schema representation.

The helioy-bus `register_agent` tool has a `profile: dict | None` parameter. Pydantic/FastMCP generates this schema:

```json
"profile": {
  "anyOf": [
    {"additionalProperties": true, "type": "object"},
    {"type": "null"}
  ],
  "default": null,
  "title": "Profile"
}
```

The `anyOf` wrapper itself has no `type` field. The sanitizer will attempt to infer one from structural keywords (`properties`, `items`, `enum`, etc.), but none are present. It defaults to `"string"`, producing `{"type": "string", "anyOf": [...]}` which may deserialize incorrectly or cause the parent object's properties to be malformed.

Historical precedent: Issue #2204 documented that `["string", "null"]` union types produced `"invalid type: sequence, expected variant identifier"`. Issue #4176 documented that `additionalProperties: {}` (object instead of boolean) produced `"invalid type: map, expected a boolean"`. Both caused tools to be silently excluded.

These specific issues were fixed in v0.21.0 (PR #1975) and v0.42+ (PR #4305), but the `anyOf` with `null` type pattern continues to surface edge cases in newer versions. The `tool_search.rs` path uses `?` propagation that fails the entire operation if any single tool conversion fails.

Sources: [Issue #2204](https://github.com/openai/codex/issues/2204), [Issue #4176](https://github.com/openai/codex/issues/4176), [Issue #4300](https://github.com/openai/codex/issues/4300), [Issue #3152](https://github.com/openai/codex/issues/3152).

#### B. Startup timing / snapshot staleness

`McpConnectionManager` maintains `AsyncManagedClient` instances that can return a "startup snapshot" (from disk cache or previous session) while the actual client is still initializing. If the inner server takes longer than `startup_timeout_sec` (default: 10s) to respond to `tools/list`, the display shows cached results (possibly empty) while the client eventually connects and tools become callable.

Python MCP servers are slower to start than Node.js ones due to interpreter startup and module import time. The proxy.py wrapper adds another layer of startup latency.

Source: `mcp_connection_manager.rs` startup snapshot logic. [Issue #5770](https://github.com/openai/codex/issues/5770).

#### C. Display-only bug (confirmed in Codex Desktop, plausible in CLI)

Issue #14189 documents the exact symptom: "MCP tools in TRUSTED project are not shown in Codex Desktop, but they still work." The tools function when invoked but do not appear in `/mcp`. This was confirmed as a display-only bug affecting how `McpServerStatus` is populated from the app-server layer, not a tool discovery failure.

Source: [Issue #14189](https://github.com/openai/codex/issues/14189).

#### D. resources/list dependency (fixed but worth noting)

Issue #8565 documented that Codex CLI was using `resources/list` as the availability check for MCP servers. Servers that only exposed tools (no resources) were treated as unavailable. The FastMCP Python server does not expose resources by default.

This was fixed, but if running an older Codex version, this could be the cause.

Source: [Issue #8565](https://github.com/openai/codex/issues/8565).

#### E. Cascading disconnection from -32601 errors

Issue #14454 documents that if any MCP server returns `-32601 (Method not found)` for `resources/templates/list`, Codex disconnects ALL MCP servers. FastMCP servers that don't implement resource templates could trigger this. The result is all servers showing no tools.

Source: [Issue #14454](https://github.com/openai/codex/issues/14454).

### 3. Codex vs Claude Code MCP implementation differences

Claude Code uses the `@anthropic-ai/sdk` TypeScript MCP client. Key differences:

| Aspect | Codex CLI | Claude Code |
|--------|-----------|-------------|
| MCP client | Rust (`rmcp-client`) | TypeScript |
| Schema handling | Must convert to internal `JsonSchema` enum (limited subset) | Passes schemas through with minimal transformation |
| `anyOf` support | Recursive sanitization, but `JsonSchema` enum cannot natively represent `anyOf` | Full JSON Schema support |
| `null` types | Stripped during type inference | Supported natively |
| Error handling | Schema failure excludes tool from display (silent in some paths) | Tolerant of schema variations |
| `resources/list` | Historically required for availability check | Not required |
| Startup timeout | 10s default | More lenient |

### 4. The proxy pattern and its interaction with tool discovery

The helioy-bus proxy.py is a passthrough stdio proxy that hot-reloads the inner server. During normal operation, it transparently forwards all JSON-RPC messages including `tools/list` requests and responses. However:

- During a hot-reload cycle, the proxy buffers incoming messages and replays `initialize` to the new inner server. The `tools/list` response from the new server may differ if code changed.
- The proxy does NOT send `notifications/tools/list_changed` after a hot-reload. Codex caches the tool list from the initial `tools/list` call and does not re-query unless it receives this notification or reconnects.

This means: after a hot-reload, Codex's cached tool list may be stale. But this does not explain the initial "none" state since the first `tools/list` should succeed.

### 5. FastMCP Python library MCP spec compliance

The `mcp` Python package (which includes `FastMCP`) supports the full MCP specification for `tools/list` and `tools/call`. It correctly implements:

- `initialize` / `notifications/initialized` handshake
- `tools/list` with pagination
- `tools/call` with proper JSON-RPC responses
- stdio transport

The schema generation uses Pydantic v2, which produces standard JSON Schema including `anyOf`, `$ref`, `$defs`, and `additionalProperties` as objects. These are all valid JSON Schema but may not be compatible with Codex's limited `JsonSchema` enum.

## Diagnostic Steps

1. **Check Codex logs**: `~/.codex/log/codex-tui.log` will show schema conversion errors like "Failed to convert" or "invalid type".

2. **Test tool schema directly**: Send a raw `tools/list` JSON-RPC request to the server and inspect the response schemas for `anyOf`, `$ref`, `additionalProperties` as objects, or missing `type` fields.

3. **Increase startup timeout**: In `~/.codex/config.toml`:
   ```toml
   [mcp_servers.helioy-bus]
   startup_timeout_sec = 30
   ```

4. **Simplify problematic schemas**: Change `profile: dict | None = None` to `profile: str = ""` (serialize dict as JSON string) to eliminate the `anyOf` union type.

5. **Check Codex version**: Run `codex --version`. Versions < 0.42.0 have the most schema conversion issues. Versions < 0.77.0 have the `resources/list` dependency bug.

## Sources Consulted

### GitHub Issues (openai/codex)
- [#14189 - MCP tools not shown in Desktop but still work](https://github.com/openai/codex/issues/14189) - Exact symptom match, confirmed display-only bug
- [#8565 - CLI only checking resources/list for availability](https://github.com/openai/codex/issues/8565) - Historical root cause
- [#11821 - MCP tool discovery InOp](https://github.com/openai/codex/issues/11821) - Regression in tool discovery
- [#5770 - MCP not listing tools, timeout 10 seconds](https://github.com/openai/codex/issues/5770) - SSE naming / timeout
- [#14454 - Cascading disconnection from -32601](https://github.com/openai/codex/issues/14454) - resources/templates/list failure
- [#4176 - MCP tools silently excluded due to errors](https://github.com/openai/codex/issues/4176) - Schema conversion silent failure
- [#2204 - JSON Schema parsing failures](https://github.com/openai/codex/issues/2204) - integer, union types, missing type
- [#4300 - firecrawl_extract conversion error](https://github.com/openai/codex/issues/4300) - additionalProperties as object
- [#3152 - $ref schema references degraded](https://github.com/openai/codex/issues/3152) - FastMCP/Pydantic specific

### Source Code (openai/codex)
- `codex-rs/core/src/tools/spec.rs` - Schema sanitization and conversion pipeline
- `codex-rs/core/src/mcp_connection_manager.rs` - Tool aggregation and caching
- `codex-rs/tui_app_server/src/history_cell.rs` - Display logic for /mcp command
- `codex-rs/rmcp-client/src/rmcp_client.rs` - Rust MCP client implementation
- `codex-rs/core/src/tools/handlers/tool_search.rs` - Tool search with error propagation

### Official Documentation
- [Codex MCP Documentation](https://developers.openai.com/codex/mcp)
- [Codex CLI Changelog](https://developers.openai.com/codex/changelog)
- [Codex Configuration Reference](https://developers.openai.com/codex/config-reference)

### Community Reports
- [OpenAI Developer Community - stdio bug](https://community.openai.com/t/mcp-servers-all-time-out-narrowed-it-down-to-stdio-bug/1363658)
- [badlogic/pi-mono #1635 - object schemas missing properties](https://github.com/badlogic/pi-mono/discussions/1635)

### MCP Python SDK
- [Python SDK Issue #423 - initialization timing](https://github.com/modelcontextprotocol/python-sdk/issues/423)
- [Python SDK Issue #265 - stdio_client timeout](https://github.com/modelcontextprotocol/python-sdk/issues/265)

## Source Quality Assessment

**Confidence: High.** The findings are triangulated across Codex source code analysis, multiple independent GitHub issues with confirmed fixes, and official documentation. The specific schema patterns from helioy-bus were directly inspected and matched against known failure modes.

The weakest link is determining which exact failure mode applies without access to Codex's debug logs for this specific server connection. The `anyOf` schema theory is the most probable based on the evidence, but the display-only bug (#14189) is also a strong candidate.

## Open Questions

1. What Codex CLI version is being used? This determines which schema bugs have been fixed.
2. Does `~/.codex/log/codex-tui.log` contain schema conversion errors for helioy-bus tools?
3. Does the problem occur on first connection, or only after a hot-reload cycle?
4. Does removing the `profile: dict | None` parameter from `register_agent` cause tools to appear?

## Actionable Takeaways

1. **Immediate fix**: Change `profile: dict | None = None` to `profile: str = ""` in `register_agent` and serialize the dict as a JSON string. This eliminates the `anyOf` schema that is the most probable trigger.

2. **Check logs**: Read `~/.codex/log/codex-tui.log` after starting a session with the MCP server configured. Search for "Failed to convert" or "serde" errors referencing helioy-bus tool names.

3. **Increase timeout**: Add `startup_timeout_sec = 30` to the helioy-bus MCP config in case the proxy adds startup latency.

4. **Update Codex**: Ensure running >= 0.116.0 (latest as of 2026-03-19) which has the most recent schema normalization fixes.

5. **Send `notifications/tools/list_changed`**: After the proxy hot-reloads the inner server, have it send this MCP notification to Codex so tools are re-enumerated. This addresses stale cache after reload.

6. **File a Codex issue**: If the problem persists after fixing the schema, file an issue referencing #14189 with the specific `anyOf`/`null` schema pattern from FastMCP. The display-only bug path suggests a gap between the status-reporting layer and the actual tool registry.
