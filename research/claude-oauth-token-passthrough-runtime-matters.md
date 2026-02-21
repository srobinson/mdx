---
title: Claude OAuth token passthrough in runtime-matters
type: research
tags: [runtime-matters, claude, oauth, docker, env, helioy]
summary: Explicit CLAUDE_CODE_OAUTH_TOKEN env reaches spawned Claude, including Docker, but Claude expects a raw access token rather than the macOS Keychain credentials JSON blob.
status: active
source: codebase-analyst
confidence: high
created: 2026-05-23
updated: 2026-05-23
---

## Executive Summary

`runtime-matters` forwards explicit spawn env correctly. `CLAUDE_CODE_OAUTH_TOKEN` is lost only when callers rely on implicit host env inheritance, because `CLAUDE_CODE_` is denied during host env capture; explicit `--env` bypasses that filter. The login failure is therefore most likely a value problem: the macOS Keychain item is a JSON credentials blob, while Claude Code consumes `CLAUDE_CODE_OAUTH_TOKEN` as a raw bearer access token.

Full task deliverable: `~/.mdx/projects/auth-token-debug--codex.md`.

## Project Metadata

- Language: Rust 2024 workspace.
- Relevant crates: `rtm-cli`, `rtm-core`, `rtm-launchers`, `rtm-daemon`, `rtm-platform`.
- Local Claude binary: `/Users/alphab/.local/bin/claude` symlinked to `/Users/alphab/.local/share/claude/versions/2.1.149`.
- fmm status: `.fmm.db` exists and `fmm validate` passed for all 135 files.

## Architecture

The CLI parses env flags into `SpawnRequest.env` (crates/rtm-cli/src/cli/spawn.rs:38-83). The Claude launcher starts from that request env and upserts Helioy and RTM session metadata (crates/rtm-launchers/src/lib.rs:55-74, crates/rtm-launchers/src/claude.rs:14-20). The daemon stores the resulting `LaunchSpec` for the shim, which later retrieves it by session id (crates/rtm-daemon/src/server/spawn.rs:39-45, crates/rtm-daemon/src/server/spawn.rs:112-122).

For host runtime execution, the shim clears inherited process env and writes exactly `LaunchSpec.env` to the runtime process (crates/rtm-cli/src/cli/shim.rs:92-98, crates/rtm-cli/src/cli/shim.rs:125-131). For Docker execution, the daemon converts every `LaunchSpec.env` entry into a Docker `--env KEY=value` pair before the image argument (crates/rtm-daemon/src/docker_argv.rs:48-64, crates/rtm-daemon/src/docker_argv.rs:128-133).

## Key Patterns

- Implicit host env capture denies the `CLAUDE_CODE_` prefix (crates/rtm-core/src/spawn_context.rs:25-25, crates/rtm-core/src/spawn_context.rs:69-80).
- Explicit `--env` is applied after that denylist and is not filtered by key name (crates/rtm-cli/src/cli/spawn.rs:79-83, crates/rtm-cli/src/cli/spawn.rs:85-106).
- Docker isolation inherits no caller env by default; explicit env is the only path (crates/rtm-cli/src/cli/spawn.rs:74-83).
- Docker `--env` emission has no allowlist and no auth scrub (crates/rtm-daemon/src/docker_argv.rs:128-133).

## Detailed Findings

### Host env passthrough

A host spawn will not inherit `CLAUDE_CODE_OAUTH_TOKEN` just because it exists in the caller environment. The `CLAUDE_CODE_` prefix is denied during implicit host capture (crates/rtm-core/src/spawn_context.rs:25-25). If the caller passes `--env CLAUDE_CODE_OAUTH_TOKEN` or `--env CLAUDE_CODE_OAUTH_TOKEN=...`, the explicit override is inserted after capture and reaches `LaunchSpec.env` (crates/rtm-cli/src/cli/spawn.rs:74-83, crates/rtm-cli/src/cli/spawn.rs:85-106).

### Docker env passthrough

Docker isolation starts from an empty env vector and takes explicit overrides only (crates/rtm-cli/src/cli/spawn.rs:74-83). The Docker argv builder writes each launch env as `--env KEY=value` (crates/rtm-daemon/src/docker_argv.rs:128-133). A live sentinel run confirmed that `CLAUDE_CODE_OAUTH_TOKEN=sentinel-marker-12345` appeared in both Docker config and the running `claude` process environment.

### Claude token consumption

The local Claude Code binary is a Mach-O executable, not unpacked JS. `strings` on `/Users/alphab/.local/share/claude/versions/2.1.149` shows `CLAUDE_CODE_OAUTH_TOKEN`, `CLAUDE_CODE_OAUTH_TOKEN_FILE_DESCRIPTOR`, `ANTHROPIC_AUTH_TOKEN`, `CCR_OAUTH_TOKEN_FILE`, `tokenSource`, and OAuth profile validation messages. A temp config run with `CLAUDE_CODE_OAUTH_TOKEN=sentinel-marker-12345` returned `401 Invalid bearer token`, proving that Claude reads the env var and treats it as a bearer credential.

### Keychain shape

`security find-generic-password -s 'Claude Code-credentials' -a alphab` reports a generic password item in the login keychain with service `Claude Code-credentials` and account `alphab`. A redacted local parser printed only structure: the password value is an 831 byte JSON object with top level keys `claudeAiOauth` and `mcpOAuth`. `claudeAiOauth` contains `accessToken`, `refreshToken`, `expiresAt`, `scopes`, `subscriptionType`, and `rateLimitTier`. No secret values were printed or written.

## Dependencies

- `clap` parses `--env` and spawn options in `rtm-cli`.
- `serde` carries `SpawnRequest.env` and `LaunchSpec.env` across the daemon protocol.
- Docker CLI receives env via generated `docker run --env` argv.
- macOS Keychain stores the local Claude credentials blob outside `.claude`.

## Relevance to Helioy

Helioy agents can use explicit env passthrough safely, but credential bridges should parse and inject the minimum credential. Passing or mounting the whole Claude Keychain JSON is the wrong contract for `CLAUDE_CODE_OAUTH_TOKEN`, and mounting `~/.claude` into Docker cannot provide macOS Keychain secrets.

## Open Questions

1. Should Helioy add a secure token helper that reads Keychain, extracts `claudeAiOauth.accessToken`, checks `expiresAt`, and injects only at spawn time?
2. Should long running spawned Claude sessions use a refresh capable credential path rather than a static access token env?
3. Should docs make the implicit host env denylist explicit for `CLAUDE_CODE_*` variables so users know to use `--env`?
