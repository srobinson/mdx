---
title: rmcp Rust MCP SDK Assessment - Best-in-Class Status March 2026
type: research
tags: [rust, mcp, rmcp, sdk, model-context-protocol, tooling]
summary: rmcp is the official Tier 2 Rust MCP SDK at v1.2.0 with 5.3M downloads and 87.5% server conformance; 0.15 is four versions behind and should be upgraded to 1.2.0
status: active
source: deep-research
confidence: high
created: 2026-03-14
updated: 2026-03-14
---

## Executive Summary

rmcp is the clear best-in-class choice for building MCP servers in Rust. It is the official SDK under `modelcontextprotocol/rust-sdk` (3,165 stars, 5.3M downloads), classified as Tier 2 by the MCP SDK tiering system with 87.5% server conformance. Version 0.15.0 (Feb 10, 2026) is now four releases behind the current 1.2.0 (Mar 11, 2026). The 1.0 release introduced breaking changes to struct construction patterns (non-exhaustive + builder methods) but did NOT change the `#[tool]`/`#[tool_router]` macro API. Upgrading is straightforward and recommended.

## 1. Competitive Landscape

### rmcp (official, dominant)
- **Repo**: `modelcontextprotocol/rust-sdk`
- **Stars**: 3,165 | **Downloads**: 5,300,391 (all time)
- **Version**: 1.2.0 (Mar 11, 2026)
- **Origin**: Started at Block, now maintained by @4t145 and @jokemanfire under the MCP org
- **MCP Tier**: Tier 2 (working toward Tier 1)
- **Conformance**: Server 87.5% (28/32), Client 80.0% (16/20)

### rust-mcp-sdk (independent alternative)
- **Repo**: `rust-mcp-stack/rust-mcp-sdk`
- **Stars**: 158 | **Downloads**: 88,806 (all time, 60x smaller)
- **Version**: 0.9.0 (Mar 13, 2026)
- **Uses**: `#[mcp_tool]` macro (different API surface)
- **Differentiators**: Multi-client HTTP concurrency, DNS rebinding protection, health check endpoints
- **Status**: SDK merge with rmcp was discussed (issue #320) but did not proceed. The maintainer (@hashemix) is still considering collaboration.

### mcp-sdk-rs (abandoned)
- **Downloads**: 9,713 total
- **Latest**: 0.3.4 (Nov 2025, no updates in 4 months)
- **Verdict**: Dead project. Not viable.

### Assessment
rmcp has 60x the download volume of its nearest competitor. No alternative offers a compelling reason to choose it over rmcp for stdio-based servers launched by Claude Code. rust-mcp-sdk has advantages for HTTP multi-client scenarios, but that is not relevant to subprocess-launched MCP servers.

## 2. Version History: 0.15 to 1.2.0

| Version | Date | Key Changes |
|---------|------|-------------|
| 0.15.0 | Feb 10 | URL elicitation, native-tls backend, SEP-1577 sampling enforcement |
| 0.16.0 | Feb 17 | Custom HTTP headers, OAuth auth method config |
| 0.17.0 | Feb 27 | Streamable HTTP JSON response mode, conformance tests, trait-based tool declaration |
| 1.0.0-alpha | Mar 3 | Breaking: auth token exchange extra fields |
| 1.0.0 | Mar 3 | Auth fixes, API ergonomics, streamable HTTP error handling |
| 1.1.0 | Mar 4 | OAuth 2.0 Client Credentials flow |
| 1.1.1 | Mar 9 | Fix: accept logging/ping before initialization |
| 1.2.0 | Mar 11 | Constructors for non-exhaustive types, ping handling fix |

### Breaking Changes in 1.0

The primary breaking change is structural, not functional. All public model structs became `#[non_exhaustive]` and gained builder-style constructors. Direct struct-literal construction no longer compiles.

**What changed**:
- `ServerInfo { instructions: ..., capabilities: ..., ..Default::default() }` becomes `ServerInfo::new(capabilities).with_instructions("...")`
- Similar patterns for `CallToolRequestParams`, `GetPromptResult`, `Tool`, `ToolAnnotations`, etc.
- Error enums became `#[non_exhaustive]`, requiring `_ => {}` match arms

**What did NOT change**:
- The `#[tool]` macro API
- The `#[tool_router]` macro API
- The `ServerHandler` trait interface
- The schemars integration pattern
- The stdio transport API

For a stdio server using `#[tool]` macros, the migration is primarily updating `get_info()` return values and any manual `ServerInfo` construction. The tool definition code stays the same.

Full migration guide: https://github.com/modelcontextprotocol/rust-sdk/discussions/716

## 3. The `#[tool]` Macro Pattern with schemars

### How It Works
- Struct derives `schemars::JsonSchema` + `serde::Deserialize`
- Field descriptions via `#[schemars(description = "...")]`
- `#[tool_router]` on impl block generates `ToolRouter<Self>`
- `#[tool(description = "...")]` on individual async methods
- Parameters received via `Parameters<T>` wrapper type with destructuring

### Known Limitations

**Issue #135 (Fixed)**: schemars generates `type: ["T", "null"]` for `Option<T>` fields. This broke Cursor and Windsurf clients. Fixed by using `SchemaSettings::openapi3()` to produce `{ "type": "string", "nullable": true }` format. The fix is in the SDK since mid-2025.

**Issue #445 (Fixed)**: Tools with zero parameters generated invalid `inputSchema` (empty object missing `"type": "object"`). Fixed in PR #446 (Sep 2025).

**Ergonomic friction**: Parameter structs require explicit `#[schemars(description = "...")]` annotations on every field for LLMs to understand the schema. This is boilerplate-heavy compared to Python's FastMCP where docstrings suffice. This is a Rust ecosystem constraint, not an rmcp-specific limitation.

**No known open issues** with the `#[tool]` macro as of March 2026.

## 4. stdio Transport

### Implementation
- `transport-io` feature flag enables `stdio()` function
- Server starts with `service.serve(stdio()).await?`
- Lifecycle managed with `.waiting()` or `.cancel()`
- Pluggable transport layer via `Transport` trait

### Known Issues

**Issue #347 (Clean shutdown)**: The MCP spec defines a three-step shutdown sequence (close stdin, wait, SIGTERM, wait, SIGKILL). The rmcp implementation handles this but had edge cases around Windows and tokio interaction with unclosed stdin. This was addressed in earlier versions and is not a practical problem for Unix-based deployments.

**No known buffering issues**. The stdio transport uses tokio's async I/O primitives. Multiple production MCP servers (Roblox Studio, various community servers) use rmcp's stdio transport without reported buffering problems.

## 5. Feature Completeness vs TypeScript/Python SDKs

| Feature | TypeScript (Tier 1) | Python (Tier 1) | Rust/rmcp (Tier 2) |
|---------|:---:|:---:|:---:|
| Tools | Yes | Yes | Yes |
| Resources | Yes | Yes | Yes |
| Prompts | Yes | Yes | Yes |
| Sampling | Yes | Yes | Yes |
| Elicitation | Yes | Yes | Yes |
| Logging | Yes | Yes | Yes |
| Completions | Yes | Yes | Yes |
| Subscriptions | Yes | Yes | Yes |
| OAuth 2.0 | Yes | Yes | Yes |
| Streamable HTTP | Yes | Yes | Yes |
| stdio | Yes | Yes | Yes |
| Conformance | 100% | 100% | 87.5% server / 80% client |

**Gaps preventing Tier 1** (from ROADMAP.md):
- Server: prompt argument substitution, embedded resource content, SEP-1330 enum inference, DNS rebinding protection
- Client: 4 auth-related conformance failures
- Documentation: 14 features undocumented, 7 partially documented
- Missing: VERSIONING.md governance document

For a stdio server exposing tools (no prompts with embedded resources, no client-side auth), rmcp is functionally equivalent to the Tier 1 SDKs.

## 6. ServerHandler Pattern

The pattern used in the spec (get_info returning ServerInfo with instructions) is the canonical rmcp pattern. Post-1.0, the construction changes:

```rust
// Pre-1.0 (0.15 style)
fn get_info(&self) -> ServerInfo {
    ServerInfo {
        instructions: Some("...".into()),
        capabilities: ServerCapabilities::builder().enable_tools().build(),
        ..Default::default()
    }
}

// Post-1.0 (1.2 style)
fn get_info(&self) -> ServerInfo {
    ServerInfo::new(ServerCapabilities::builder().enable_tools().build())
        .with_instructions("...")
}
```

The `#[tool_handler]` macro (older naming) or equivalent handles the ServerHandler trait implementation, routing `ListToolsRequest` and `CallToolRequest` to the tool router automatically.

## 7. Ecosystem Crates

| Crate | Purpose |
|-------|---------|
| `rmcp` | Core SDK |
| `rmcp-macros` | Proc macros (`#[tool]`, `#[prompt]`) |
| `rmcp-actix-web` | Actix-web transport (alternative to Axum) |
| `rmcp-openapi` | Convert OpenAPI specs to MCP tool definitions |
| `rmcp-in-process-transport` | In-process transport for testing |
| `rmcp-server-builder` | Builder pattern for server construction |
| `rmcp-presence` | Presence/discovery |

## Sources Consulted

### Primary Sources
- [rmcp crates.io page](https://crates.io/crates/rmcp) (version history, download counts)
- [modelcontextprotocol/rust-sdk GitHub](https://github.com/modelcontextprotocol/rust-sdk) (releases, issues, roadmap)
- [1.x Migration Guide](https://github.com/modelcontextprotocol/rust-sdk/discussions/716) (breaking changes)
- [ROADMAP.md](https://github.com/modelcontextprotocol/rust-sdk/blob/main/ROADMAP.md) (Tier 1 path)
- [MCP SDK Tiers](https://modelcontextprotocol.io/community/sdk-tiers) (official tiering criteria)
- [MCP SDKs page](https://modelcontextprotocol.io/docs/sdk) (official SDK listing)
- [docs.rs/rmcp](https://docs.rs/rmcp/latest/rmcp/) (API docs, feature flags)

### Issue Tracker
- [Issue #135](https://github.com/modelcontextprotocol/rust-sdk/issues/135): schemars optional field schema incompatibility (fixed)
- [Issue #445](https://github.com/modelcontextprotocol/rust-sdk/issues/445): parameterless tool schema generation (fixed)
- [Issue #347](https://github.com/modelcontextprotocol/rust-sdk/issues/347): stdio clean shutdown
- [Issue #320](https://github.com/modelcontextprotocol/rust-sdk/issues/320): SDK merge discussion with rust-mcp-sdk

### Guides and Articles
- [Complete Guide - rup12.net](https://rup12.net/posts/write-your-mcps-in-rust/) (rmcp 0.11 era patterns)
- [MCPcat Guide](https://mcpcat.io/guides/building-mcp-server-rust/) (current patterns)
- [HackMD Coder's Guide](https://hackmd.io/@Hamze/S1tlKZP0kx) (rmcp 0.1 era, `#[tool_box]` pattern)
- [Shuttle stdio guide](https://www.shuttle.dev/blog/2025/07/18/how-to-build-a-stdio-mcp-server-in-rust)

### Community
- [HN: Writing MCP Servers in Rust](https://news.ycombinator.com/item?id=46236258) (minimal discussion)
- Reddit: No meaningful discussions found for rmcp specifically

## Source Quality Assessment

**Confidence: High.** Primary sources are the official GitHub repository (releases, issues, roadmap, migration guide) and crates.io API data. These are authoritative and current. The download numbers are objective. The conformance scores come from automated testing infrastructure.

The one area of lower confidence is the completeness of the "known issues" section. GitHub issues represent reported problems; unreported friction points (e.g., compile-time macro error messages) would require hands-on testing to surface.

## Open Questions

1. **Macro error diagnostics**: How helpful are rmcp's `#[tool]` macro compile errors when you make a mistake? No source addresses this.
2. **Memory/performance**: No benchmarks comparing rmcp's stdio transport overhead to TypeScript/Python SDKs. Given Rust's baseline, this is unlikely to be a concern.
3. **Tier 1 timeline**: The roadmap lists clear items but no target date. The velocity (0.15 to 1.2 in 32 days) suggests active development.
4. **schemars version**: rmcp uses schemars for JSON Schema 2020-12, but the roadmap notes this as "partial" support. Whether this affects real-world tool schemas with Claude Code is unclear.

## Actionable Takeaways

1. **Upgrade from 0.15 to 1.2.0 immediately.** The `#[tool]` and `#[tool_router]` macros are unchanged. The migration is limited to updating `ServerInfo` construction to use `::new()` + `.with_*()` builder methods, and adding `_ => {}` arms to any exhaustive matches on rmcp error enums.

2. **rmcp is the correct choice.** No competitor offers a compelling alternative for stdio-based MCP servers. The 60x download advantage, official org ownership, and active maintenance (3 releases in 11 days) make the decision clear.

3. **The Arc<CmStore> pattern (no mutex, SQLite pools handle concurrency) is fine.** rmcp's ServerHandler receives `&self`, and tools receive `&self` references. Shared state behind `Arc` with internal concurrency management (like SQLite connection pools) is the standard pattern.

4. **schemars JsonSchema derive is the canonical approach.** Both the official examples and all third-party guides use this pattern. The known schema generation issues (optional fields, parameterless tools) have been fixed.

5. **Watch for Tier 1 promotion.** When rmcp reaches 100% conformance, the API surface may see minor additions but the core patterns will remain stable.
