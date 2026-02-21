---
title: Linear MCP Daily Re-authentication Root Cause and Fix
type: research
tags: [linear, mcp, claude-code, oauth, api-key, authentication]
summary: The helioy-tools linear-server uses OAuth 2.1 with no credentials in config; OAuth tokens expire (typically ~24h), causing daily reauth. Fix is to switch to a personal API key via Authorization header in .mcp.json.
status: active
source: quick-research
confidence: high
created: 2026-03-11
updated: 2026-03-11
---

## Summary

The daily re-authentication is caused by Linear's OAuth 2.1 token expiration. The `linear-server` entry in `plugins/helioy-tools/.mcp.json` uses `"type": "http"` with no credentials, forcing Claude Code to perform an interactive OAuth flow every session. OAuth access tokens issued by `mcp.linear.app` are short-lived (typically 24 hours). Personal API keys do not expire. Switching to a personal API key eliminates the daily prompt.

## Root Cause

### Current configuration

`/Users/alphab/Dev/LLM/DEV/helioy/helioy-plugins/plugins/helioy-tools/.mcp.json`:

```json
"linear-server": {
  "type": "http",
  "url": "https://mcp.linear.app/mcp"
}
```

No `headers` field. No stored credentials. Claude Code initiates an OAuth 2.1 flow on every new session once the previous token expires.

### Why it expires daily

Linear's hosted MCP server (`mcp.linear.app`) implements OAuth 2.1 with dynamic client registration. The access tokens it issues are short-lived — standard OAuth practice puts them at 1 hour to 24 hours. There is no persistent refresh token stored by the plugin config itself; Claude Code stores OAuth tokens in `~/.claude.json`, but the token TTL governs when they become invalid. Starting a new Claude Code session the following day hits an expired token, triggering re-auth.

### What Linear actually supports for persistent auth

Linear's MCP server explicitly supports bypassing the OAuth flow by accepting a personal API key (or any valid OAuth access token) directly in the `Authorization: Bearer` header. Personal API keys are non-expiring credentials tied to the user account.

From Linear's MCP documentation:
> "authenticate with your own API keys or OAuth access tokens by passing them directly in the `Authorization: Bearer <yourtoken>` header instead of using the interactive authentication flow"

## Fix

### Step 1: Generate a personal API key in Linear

Linear settings path: **Settings → Account → Security & Access → API keys**

Copy the generated key. It does not expire.

### Step 2: Update `.mcp.json` to pass the key as a header

```json
{
  "mcpServers": {
    ...
    "linear-server": {
      "type": "http",
      "url": "https://mcp.linear.app/mcp",
      "headers": {
        "Authorization": "Bearer ${LINEAR_API_KEY}"
      }
    }
  }
}
```

Claude Code supports environment variable expansion in `.mcp.json` using `${VAR}` syntax. Set `LINEAR_API_KEY` in your shell environment (e.g. in `~/.zshrc` or via a secrets manager) so the key never appears in the committed file.

### Step 3: Set the environment variable

```bash
# Add to ~/.zshrc or equivalent
export LINEAR_API_KEY="lin_api_xxxxxxxxxxxxxxxxxxxx"
```

### Step 4: Clear the stale OAuth token (optional cleanup)

```
/mcp
```

Select `linear-server` → "Clear authentication" to remove the stored OAuth token from `~/.claude.json`. This is optional but avoids any confusion between old OAuth state and the new header-based auth.

## Tradeoffs

| Method | Expiry | Interactive | Scopes |
|---|---|---|---|
| OAuth 2.1 (current) | ~24h access token | Yes, each session after expiry | Per-consent |
| Personal API key | Never | No | Full account access |

The personal API key grants full access to the account. If a narrower scope is needed (e.g. read-only), Linear's OAuth app system is the correct mechanism, but that requires setting up a registered OAuth app with pre-configured credentials using `--client-id` and `--client-secret` flags in Claude Code — more setup, but with proper token refresh behavior that would eliminate the daily prompt as well.

For a single-user personal workflow (Stuart's case), the personal API key is the straightforward fix.

## Sources

- `plugins/helioy-tools/.mcp.json` in helioy-plugins repo (inspected directly)
- Linear MCP docs: https://linear.app/docs/mcp
- Claude Code MCP docs: https://code.claude.com/docs/en/mcp (HTTP server config, headers, env var expansion)
- MCP transport spec: https://modelcontextprotocol.io/docs/concepts/transports

## Open Questions

- Linear does not publish the exact TTL of OAuth tokens issued by `mcp.linear.app`. "Daily" expiry aligns with common 24h access token lifetimes, but it could be shorter.
- Claude Code's OAuth token refresh behavior (whether it attempts a refresh_token grant automatically) is not fully documented. If it did, a properly registered OAuth app with refresh tokens would also solve this without an API key.
