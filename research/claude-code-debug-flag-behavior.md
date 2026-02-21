---
title: Claude Code --debug Flag Behavior Reference
type: research
tags: [claude-code, cli, debug, logging, api]
summary: Complete reference for --debug, --debug-file, CLAUDE_DEBUG, and debug output format in Claude Code CLI
status: active
source: quick-research
confidence: high
created: 2026-03-17
updated: 2026-03-17
---

## Summary

`--debug` in Claude Code always writes to a file at `~/.claude/debug/<session-uuid>.txt`, not to stdout or stderr. The flag accepts an optional comma-separated filter string. There is no `CLAUDE_DEBUG` environment variable in the official API; the generic `DEBUG` env var was historically problematic and has since been addressed. API calls log client creation and auth steps but do not log token counts, system prompt size, or tool definitions in the Claude Code debug output.

## Details

### 1. Where does debug output go?

**To a file, not to stdout or stderr.**

Default path: `~/.claude/debug/<session-uuid>.txt`

A `latest` symlink is maintained: `~/.claude/debug/latest -> ~/.claude/debug/<uuid>.txt`

On startup, Claude Code prints two lines to the terminal (stdout/stderr, not the debug file):
```
Debug mode enabled
Logging to: ~/.claude/debug/<session-id>.txt
```

Everything after that goes to the file only. Confirmed by:
- GitHub issue #27746: crash report showing `appendFileSync` writing to `~/.claude/debug/<uuid>.txt`
- GitHub issue #11015: bug report shows the "Logging to:" message on activation
- Live debug files on this machine at `~/.claude/debug/`

### 2. What does `--debug "api"` filter to?

The filter is a comma-separated list of category strings matched case-insensitively against bracketed tags in log lines. The format is:

```
<timestamp> [DEBUG] [CATEGORY:subcategory] message
```

`--debug "api"` matches entries tagged `[API:auth]` and `[API:request]`.

The docs example `"api,mcp"` matches both API and MCP categories.

**Negation syntax**: prefix with `!` to exclude. Example: `"!statsig,!file"` logs everything except statsig and file-related entries.

**Known categories observed in real debug files** (from `~/.claude/debug/` files on this machine):

| Category tag | What it covers |
|---|---|
| `[API:auth]` | OAuth token checks before each API call |
| `[API:request]` | Client creation, auth header presence |
| `[MCP]` | MCP server connection events |
| `[STARTUP]` | Initialization sequence |
| `[init]` | Global config init (mTLS, agents, CA certs) |
| `[LSP MANAGER]` | Language server protocol manager |
| `[LSP SERVER MANAGER]` | LSP server lifecycle |
| `[LSP PROTOCOL ...]` | Per-server protocol messages |
| `[keybindings]` | Keybinding setup |
| `[Reconnection]` | Agent reconnection logic |
| `[REPL:mount]` / `[REPL:unmount]` | REPL lifecycle |
| `[3P telemetry]` | Third-party telemetry (Statsig) |
| `[claudeai-mcp]` | Claude.ai MCP server gate checks |
| `[ToolSearch:optimistic]` | Optimistic tool search polling |
| `[TeammateMailbox]` | Multi-agent inbox polling (mentioned in issues) |
| `[useDeferredValue]` | React deferred rendering |
| `[Perfetto]` | Performance tracing |
| `[Claude in Chrome]` | Chrome integration |
| `[lspRecommendation]` | LSP setup recommendations |
| `[onCancel]` / `[onSubmit]` | User action handlers |
| `[PASSIVE DIAGNOSTICS]` | Background diagnostic checks |

The docs also mention `statsig` and `1p` (first-party) as filterable categories, used in the `"!statsig,!file"` negation example. These tags must exist in code but were absent from the debug files examined (likely only emitted in specific code paths).

### 3. What does `--debug-file` do? What is the default path?

`--debug-file <path>` redirects debug output to a specific file instead of the auto-generated UUID path. It also **implicitly enables debug mode** without needing `--debug`.

Default path (when using `--debug` without `--debug-file`): `~/.claude/debug/<session-uuid>.txt`

On Windows: `C:\Users\<name>\.claude\debug\<session-uuid>.txt` (Windows bug #27746 confirms this path pattern).

The directory must exist. Claude Code does not create it on Windows (bug #27746, still open as of March 2026). On macOS/Linux it is created automatically.

### 4. Does `CLAUDE_DEBUG=1` differ from `--debug`?

**`CLAUDE_DEBUG` is not a documented environment variable** as of March 2026. It does not appear in the official env vars reference at `code.claude.com/docs/en/env-vars`.

Historical context:
- The generic `DEBUG=true` (from `.env` files) used to trigger debug mode (bug #346, fixed in v0.2.54, regressed in v2.0.32 as issue #11015)
- Issue #24 proposed renaming to `CLAUDE_DEBUG` or `CLAUDE_CODE_DEBUG` -- this was closed without being implemented as a documented env var
- The fix was to stop reading the generic `DEBUG` variable from `.env` files

The correct way to enable debug mode non-interactively is `claude --debug` or `claude --debug-file /path/to/log`.

### 5. What does the debug output format look like for API calls?

All entries follow: `<ISO-8601 timestamp> [DEBUG] [optional-category] <message>`

For API calls specifically, the debug file shows:
```
2026-03-04T23:41:35.392Z [DEBUG] [API:request] Creating client, ANTHROPIC_CUSTOM_HEADERS present: false, has Authorization header: false
2026-03-04T23:41:35.392Z [DEBUG] [API:auth] OAuth token check starting
2026-03-04T23:41:35.407Z [DEBUG] [API:auth] OAuth token check complete
```

**What it does NOT show:**
- Token counts (input/output)
- System prompt size or content
- Tool definitions sent to the model
- Response body or streaming content
- Cost or billing data

Token counts, headers (including rate limit headers), and streaming body are visible when the **underlying Anthropic SDK** emits its own `DEBUG` namespace logging. This is a different system -- the SDK uses `debug` npm package format:
```
Anthropic:DEBUG:response 200 https://api.anthropic.com/v1/messages GZ [Headers] {
  'anthropic-ratelimit-input-tokens-limit': ['300000'],
  'anthropic-ratelimit-input-tokens-remaining': ['222000'],
  ...
}
```
This was the original bug in issue #24 -- it leaked to console when `DEBUG=*` or `DEBUG=Anthropic:*` was set. This is not the same as `--debug`.

To see token counts, use Claude's built-in `/cost` command or enable OpenTelemetry via `CLAUDE_CODE_ENABLE_TELEMETRY=1`.

## Sources

- `claude --help` output (local, March 2026)
- `code.claude.com/docs/en/cli-reference` - official CLI flag docs
- `code.claude.com/docs/en/env-vars` - complete env var reference (no CLAUDE_DEBUG listed)
- GitHub anthropics/claude-code issue #24 - "Rename DEBUG env option to CLAUDE_DEBUG"
- GitHub anthropics/claude-code issue #346 - "Unintended Debug Logging Triggered by .env File"
- GitHub anthropics/claude-code issue #11015 - "DEBUG mode auto-enabled from .env (regression)"
- GitHub anthropics/claude-code issue #27746 - "Crashes when debug directory missing (Windows)"
- GitHub anthropics/claude-code issue #25139 - "TeammateMailbox polling generates debug log volume"
- Live debug files at `~/.claude/debug/` (examined March 2026)

## Open Questions

- Are `statsig` and `1p` tag names actually used as filter strings, or just category labels? The docs show `"!statsig,!file"` but these tags do not appear in observed debug output.
- Does the filter match partial strings (substring) or require exact case-insensitive match? The docs example `"api,mcp"` suggests lowercase partial matching against full tag strings like `[API:request]`.
- What does `--debug "hooks"` match exactly? Hooks-related messages in observed files don't use a bracketed tag, they appear without a category prefix.
