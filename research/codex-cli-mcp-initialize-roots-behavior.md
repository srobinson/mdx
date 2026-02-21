---
title: Codex CLI does not send MCP roots in initialize; uses cwd inheritance instead
type: research
tags: [mcp, codex, openai, roots, initialize, cwd, fmm]
summary: Codex CLI sets roots to None in its MCP initialize params and does not implement the roots/list handler. MCP servers must discover project root via process cwd or explicit cwd config.
status: active
source: deep-research
confidence: high
created: 2026-03-22
updated: 2026-03-22
---

## Executive Summary

OpenAI Codex CLI does **not** send `roots` in its MCP `initialize` request. The `roots` field in `ClientCapabilities` is explicitly set to `None`. Codex also does not implement the `roots/list` server-to-client request handler. The MCP spec itself does not put roots in the initialize params; roots are a separate capability negotiated at init time, then queried via `roots/list` after initialization. MCP servers running under Codex must discover the project directory through process `cwd` (which Codex sets conditionally) or through the `cwd` field in `config.toml`.

## Detailed Findings

### 1. Codex CLI sends `roots: None` in initialize

Source: [codex-rs/core/src/mcp_connection_manager.rs](https://github.com/openai/codex/blob/main/codex-rs/core/src/mcp_connection_manager.rs)

The `start_server_task` function constructs `InitializeRequestParams` with `roots: None`:

```rust
let params = InitializeRequestParams {
    meta: None,
    capabilities: ClientCapabilities {
        experimental: None,
        extensions: None,
        roots: None,      // <-- explicitly None
        sampling: None,
        elicitation,
        tasks: None,
    },
    client_info: Implementation {
        name: "codex-mcp-client".to_owned(),
        version: env!("CARGO_PKG_VERSION").to_owned(),
        title: Some("Codex".into()),
        ..
    },
    protocol_version: ProtocolVersion::V_2025_06_18,
};
```

This is consistent across all test files (`rmcp-client/tests/resources.rs`, `rmcp-client/tests/streamable_http_recovery.rs`, `mcp-server/tests/common/mcp_process.rs`). Every instance sets `roots: None`.

There is no `roots/list` handler implementation on the Codex client side. A search for `RootsCapability`, `get_roots`, `list_roots`, and `roots_list` across the entire repository returned zero results.

### 2. MCP spec: roots are NOT in initialize params

Source: [MCP Spec 2025-06-18 Lifecycle](https://modelcontextprotocol.io/specification/2025-06-18/basic/lifecycle) and [MCP Spec 2025-06-18 Roots](https://modelcontextprotocol.io/specification/2025-06-18/client/roots)

The MCP specification defines roots as a two-phase protocol:

**Phase 1 (Initialize):** The client declares `capabilities.roots` to signal that it supports the roots feature. This is a boolean capability declaration, not a data payload. The `InitializeRequestParams` schema contains only three fields: `protocolVersion`, `capabilities`, and `clientInfo`. No root URIs are sent in the initialize request.

**Phase 2 (Post-init, server-initiated):** After `initialized` notification, the server sends a `roots/list` request to the client. The client responds with:

```json
{
  "roots": [
    {
      "uri": "file:///home/user/projects/myproject",
      "name": "My Project"
    }
  ]
}
```

The client may also send `notifications/roots/list_changed` if the `listChanged` sub-capability was declared.

Since Codex sets `roots: None` in capabilities, a spec-compliant server would never attempt to call `roots/list` on Codex, because the client has declared it does not support roots.

### 3. Codex MCP server configuration

Source: [Codex MCP docs](https://developers.openai.com/codex/mcp) and [Config Reference](https://developers.openai.com/codex/config-reference)

Codex uses `config.toml` (not `.mcp.json`) for MCP server configuration. Configuration is loaded in this order (highest priority first):

1. CLI flags / `--config` overrides
2. Profile values (`--profile <name>`)
3. Project-scoped `.codex/config.toml` (closest to cwd wins, trusted projects only)
4. User config `~/.codex/config.toml`
5. System config `/etc/codex/config.toml`
6. Built-in defaults

Stdio MCP server config supports these fields:

| Field | Type | Purpose |
|-------|------|---------|
| `command` | string | Required. Server binary/script |
| `args` | array | Arguments |
| `env` | map | Environment variables |
| `env_vars` | array | Env vars to forward from parent |
| `cwd` | string | Working directory for the server process |
| `enabled` | boolean | Enable/disable toggle |
| `startup_timeout_sec` | number | Override 10s default |
| `tool_timeout_sec` | number | Override 60s default |

Codex does **not** read `.mcp.json` files.

### 4. How Codex sets process cwd

Source: [codex-rs/rmcp-client/src/rmcp_client.rs](https://github.com/openai/codex/blob/main/codex-rs/rmcp-client/src/rmcp_client.rs)

The child process spawn is conditional on `cwd`:

```rust
pub async fn new_stdio_client(
    program: OsString,
    args: Vec<OsString>,
    env: Option<HashMap<String, String>>,
    env_vars: &[String],
    cwd: Option<PathBuf>,   // comes from config.toml cwd field
) -> io::Result<Self> {
    // ...
    if let Some(cwd) = cwd {
        command.current_dir(cwd);
    }
    // When None, child inherits parent process cwd
}
```

The `cwd` originates from `McpServerTransportConfig::Stdio { cwd: Option<PathBuf>, .. }` which is deserialized from config.toml. If `cwd` is not specified in config, it defaults to `None`, and the child process inherits the parent Codex process cwd.

**Known issue:** Codex VS Code extension and Codex Desktop may spawn MCP servers with unexpected cwd values (Windows install path instead of workspace root, temporary cache paths under uvx, etc.). This is tracked in [issue #4222](https://github.com/openai/codex/issues/4222) and [issue #7281](https://github.com/openai/codex/issues/7281).

### 5. Claude Code comparison

Claude Code sets the child process `cwd` to the project directory. This is how fmm currently discovers `.fmm.db` via `std::env::current_dir()`. Claude Code's behavior is NOT guaranteed by the MCP spec; it is an implementation detail.

Neither Claude Code nor Codex send root URIs inside the `initialize` request params. The MCP spec does not define such a field.

### 6. Implications for fmm

Given that:
- Codex does not declare `roots` capability (`roots: None`)
- Codex does not implement `roots/list` handler
- Codex may or may not set process cwd depending on config

The fmm server's `initialize` handler cannot rely on receiving roots from Codex through the MCP protocol. The fallback chain should be:

1. **Check `initialize` capabilities for `roots`**: If present, send `roots/list` after init completes (spec-compliant path, works with future clients that support roots)
2. **Check `std::env::current_dir()`**: Works with Claude Code and Codex CLI (when run from project dir or with `cwd` config set)
3. **Search upward for `.fmm.db`**: Defensive fallback for cases where cwd is wrong
4. **Accept explicit `--root` flag or env var**: For edge cases where nothing else works

## Sources Consulted

### Primary (source code, verified)
- [codex-rs/core/src/mcp_connection_manager.rs](https://github.com/openai/codex/blob/main/codex-rs/core/src/mcp_connection_manager.rs) -- InitializeRequestParams construction, `roots: None`
- [codex-rs/rmcp-client/src/rmcp_client.rs](https://github.com/openai/codex/blob/main/codex-rs/rmcp-client/src/rmcp_client.rs) -- child process spawn, conditional cwd
- [codex-rs/core/src/config/types.rs](https://github.com/openai/codex/blob/main/codex-rs/core/src/config/types.rs) -- `McpServerTransportConfig::Stdio` with `cwd: Option<PathBuf>`
- [MCP Spec 2025-06-18 Lifecycle](https://modelcontextprotocol.io/specification/2025-06-18/basic/lifecycle)
- [MCP Spec 2025-06-18 Roots](https://modelcontextprotocol.io/specification/2025-06-18/client/roots)
- [MCP JSON Schema 2025-03-26](https://github.com/modelcontextprotocol/modelcontextprotocol/blob/main/schema/2025-03-26/schema.json)
- [rmcp Rust SDK client handler](https://github.com/modelcontextprotocol/rust-sdk/blob/main/crates/rmcp/src/handler/client.rs)

### Secondary (docs, issues)
- [Codex MCP docs](https://developers.openai.com/codex/mcp)
- [Codex config reference](https://developers.openai.com/codex/config-reference)
- [Codex config basics](https://developers.openai.com/codex/config-basic)
- [Issue #4222: MCP servers not launched in workspace folder](https://github.com/openai/codex/issues/4222)
- [Issue #7281: WSL2 wrong cwd for MCP servers](https://github.com/openai/codex/issues/7281)
- [MCP Python SDK issue #1520: How to access cwd when MCP server launched via uvx](https://github.com/modelcontextprotocol/python-sdk/issues/1520)

### Tertiary (community, low signal)
- X/Twitter discussion: no substantive discussion found on Codex MCP roots
- Reddit: no relevant threads found (Codex MCP community is fragmented)

## Source Quality Assessment

**Confidence: High.** The primary finding (Codex sends `roots: None`) comes directly from the open source code, verified across the production code path (`mcp_connection_manager.rs`) and multiple test files. The MCP spec is unambiguous that roots are a separate request flow, not part of initialize params. The `cwd` behavior is verified from the rmcp_client spawn code.

The one area of uncertainty is whether Codex plans to add roots support in the future. Issue #4222 discusses the workspace directory problem but proposes environment variables and cwd fixes rather than MCP roots adoption. No roadmap signals were found.

## Open Questions

1. **Will Codex add roots support?** Issue #4222 has been open since early 2026 with no maintainer commitment to any specific approach. The suggestions lean toward env vars and cwd fixes, not MCP roots.
2. **Does Claude Code declare roots capability?** Claude Code is closed source. Empirically it sets cwd, but whether it also declares `capabilities.roots` and handles `roots/list` requests is unverified.
3. **Does Cursor or Windsurf send roots?** Untested. Would need similar source code analysis or packet capture.

## Actionable Takeaways

1. **Do not rely on `initialize` roots from Codex.** The capability is explicitly `None`. Any parsing of roots from the initialize request will produce nothing useful when Codex is the client.

2. **`std::env::current_dir()` remains the primary discovery mechanism** for both Claude Code and Codex CLI. Codex users who want their MCP server to see the right project directory should set `cwd` in `.codex/config.toml`:
   ```toml
   [mcp_servers.fmm]
   command = "fmm"
   args = ["serve"]
   cwd = "/path/to/project"
   ```

3. **The `roots/list` handler is still worth implementing** as a future-proof path. If any MCP client declares `capabilities.roots` during init, the server should query `roots/list` and use the result. This is the spec-intended mechanism. Just do not depend on it working today with Codex.

4. **Consider accepting a `--root` CLI arg or `FMM_ROOT` env var** as an explicit override. This covers edge cases where neither cwd nor roots work (uvx sandboxes, VS Code extension bugs, remote MCP over HTTP).
