---
title: caam (coding_agent_account_manager) evaluated against Transport Matters credential handling
type: research
tags: [credentials, auth, claude-code, codex, account-switching, home-isolation, transport-matters]
summary: caam is a multi-account auth-file switcher for AI CLIs; partial overlap with TM, strong patterns to borrow (credential drift watching, error classification, expiry-driven readiness), but its license rider makes direct code lifting unattractive and it has no macOS keychain story.
status: active
source: github-researcher
confidence: high
created: 2026-08-01
updated: 2026-08-01
---

# caam — Coding Agent Account Manager

Repo: https://github.com/Dicklesworthstone/coding_agent_account_manager (Jeffrey Emanuel / Dicklesworthstone). Go CLI, ~154 stars, created 2025-12-17, last commit 2026-07-23, active weekly release cadence via goreleaser. Verdict up front: **borrow patterns, do not lift code.** The license rider makes derivative-work distribution restrictions viral, and the two strongest things TM needs from this space (keychain-aware brokering, wire-level failure classification) are things caam does not have and TM already does better. What is worth taking is the drift-watching design, the auth-relevant-field hashing trick, the error taxonomy, and one operational landmine (Claude Agent View) they documented the hard way.

## What it is

caam solves a different primary problem than TM: one person paying for multiple fixed-cost subscriptions (Claude Max, GPT Pro, Gemini Ultra, Grok) who hits rate limits mid-flow and wants to switch accounts in ~50ms instead of a 30-60s OAuth dance. The core insight it is built on: every AI CLI stores OAuth bearer tokens in plain files, and possession equals access, so account switching is file copying.

Three operating modes:

1. **Vault profiles** (`internal/authfile`: `Vault`, `GetAuthFileSet`): backup/restore auth-file sets in place. One account active per tool. The vault lives at `~/.local/share/caam/vault/<tool>/<profile>/`.
2. **Isolated profiles** (`internal/profile`, `internal/exec`): full per-profile `$HOME` with symlinks to real `.ssh`, `.gitconfig`. Parallel sessions, but blank shell history and blank conversation history.
3. **Shallow profiles** (`internal/shallow`: `Manager.Create`, `providerLayout`, `SpawnEnv`): the interesting one. A per-identity `$HOME` where **only the auth-bearing files are real and everything else symlinks back to the real `~/`**. Designed for orchestrators fanning N concurrent Claude/Codex sessions across N accounts. Per provider, the real-file set is tiny: for claude it is `.claude/.credentials.json`, `.claude/.credentials.lock`, and `.claude.json`; `.claude/projects/`, `.claude/todos/` etc. symlink through so all sessions share conversation history.

Around that core: a rate-limit-detecting exec wrapper with automatic profile rotation (`internal/wrap`, `internal/ratelimit`, `internal/rotation`), profile health scoring (`internal/health`), credential drift watching (`internal/authwatch`), PTY-driven re-login (`internal/handoff`, `internal/pty`), an optional daemon for scheduled vault backups and pool refresh (`internal/daemon`), plus a TUI and a Next.js dashboard.

## Mechanism, at the level TM cares about

**Credential storage and switching.** Everything is file copying with atomic write discipline (temp file, fsync, rename; see `internal/refresh/refresh.go: writeAuthFile` and `internal/authwatch: SaveState`). Provider auth-file sets are declared data (`internal/authfile/authfile.go: AuthFileSet` with per-file `Required`/`Optional` specs), and all backup/restore/detect logic iterates the declaration. That is the same shape as TM's dispatch-on-credential-location principle (`cli/credential_source.py: resolve_harness_credential_source`), just organized per file rather than per source kind.

**Active-profile detection is content hashing, not state files.** `caam status` SHA-256 hashes the live auth files and compares against every vault profile (`internal/authwatch: Tracker.FindMatchingProfile`). No hidden state to desync; works after manual switches and reboots. The refinement that matters: for Claude they hash **auth-relevant fields only**, not whole files. `.credentials.json` hashes `accessToken`+`refreshToken`; `.claude.json` hashes only the `oauthAccount` field (`internal/authfile/authfile.go`, around the `hashAuthRelevantContent` dispatch near the `.credentials.json` / `.claude.json` case switch), because Claude Code rewrites `.claude.json` on every run and whole-file hashing would report constant false drift.

**Drift watching.** `internal/authwatch` is a small, clean design: `Tracker.Capture` snapshots per-provider `AuthState` (combined hash, per-file hashes, mtimes), `DetectChange` classifies transitions into `ChangeNew | ChangeModified | ChangeRemoved`, `Watcher.Start` polls every 5s (they deliberately chose polling over fsnotify for cross-platform auth files), and state persists to `auth_state.json` so drift detection survives restarts. `CheckUnsavedAuth` warns when live credentials match no saved profile.

**Keychain: they punt.** caam never reads or writes the macOS keychain for Claude OAuth. It assumes file-based `~/.claude/.credentials.json` exists (`docs/CLAUDE_AUTH_INVENTORY.md` CLAUDE-003 lists file paths only). For Codex it goes further and **forces** file storage: `internal/provider/codex/codex.go: EnsureFileCredentialStore` writes `cli_auth_credentials_store = "file"` into `config.toml`, replacing any keychain setting. The only keychain code in the tree is an API-key convenience script for `security find-generic-password` (`internal/provider/claude/claude.go`, launcher script template). TM's broker (`credential_broker.py: SecurityOwnerCredentialStore` reading the keychain owner credential, `CredentialBroker` minting access-only copies into `runtime-access/`) is strictly stronger on macOS: caam's answer to the keychain is to opt out of it.

**Expiry and refresh.** `internal/health/expiry.go: ParseClaudeExpiry / ParseCodexExpiry / ParseGeminiExpiry` parse per-provider expiry (Claude: `claudeAiOauth.expiresAt` as Unix millis). `internal/authpool: Monitor` + a `Refresher` interface implement refresh-before-expiry with a configurable threshold (default 5 min) and bounded concurrency; `internal/daemon/pool_refresher.go` runs it in the background. Critically, **Claude refresh is disabled**: `internal/refresh/claude.go` carries `ClaudeRefreshDisabled = true` and marks the endpoint (`api.anthropic.com/oauth/token`, client id `claude-code-cli`) as SPECULATIVE, with `refreshClaude()` returning `UnsupportedError` immediately. Their documented reasoning (CLAUDE-006): the endpoint is undocumented, refresh is handled internally by Claude Code, and external refresh risks auth corruption. Codex and Gemini refresh are implemented and enabled. Note the asymmetry with TM: TM's `HttpxTokenExchanger.exchange` does perform a working token exchange, so TM knows something caam does not; their disable decision validates TM's broker-owns-refresh posture rather than contradicting it.

**Detecting a bad credential.** Two layers, both output-based rather than wire-based. `internal/ratelimit/detector.go: Detector` regex-scans wrapped CLI stdout/stderr for provider-specific patterns (`rate.?limit`, `\b429\b`, `RESOURCE_EXHAUSTED`, ...). `internal/health/penalty.go: PenaltyForError` classifies error strings into auth / rate-limit / server / timeout buckets with different penalty weights, feeding `ProfileHealth` scores with time decay (`DecayPenalty`) and cooldowns, which `internal/rotation: Select` (smart / round_robin / random) consumes to pick the next profile. The taxonomy is right; the sensor is weak. TM sits on the wire and can classify from actual HTTP status and error bodies instead of regexing rendered terminal output.

**Re-authentication without restart.** `internal/handoff/claude.go: ClaudeLoginHandler` injects `/login` into a live PTY (`pty.Controller.InjectCommand`) and watches output for hardcoded English phrases ("opening browser", "device code", "waiting for authentication") to track login-in-progress/complete. It exists and reportedly works, but it is string matching against UI text that Anthropic can change in any release.

**Concurrent sessions on one account** are handled only in the sense that shallow profiles give each session its own `.credentials.lock` flock target so sessions do not serialize on a shared lock. There is no coordination of refresh between concurrent processes sharing one credential file; they sidestep the problem by giving each session its own account.

**The Agent View landmine (issue #49, worth the whole read).** Claude Code's `--bg` Agent View supervisor is a long-lived, cross-session daemon **not bound to the profile's `$HOME`**. A shallow session resuming would reconnect to a supervisor bound to a different identity, silently bypassing per-identity auth isolation. caam cannot control that daemon's lifecycle, so `shallow-spawn` injects `CLAUDE_CODE_DISABLE_AGENT_VIEW=1` by default (`internal/shallow/shallow.go: SpawnEnv`, which also scrubs `CLAUDE_CONFIG_DIR` and pins `CODEX_HOME`/`GEMINI_HOME` so a stray inherited value cannot pull the real identity back in). Any product that launches Claude Code under a substitute home has this failure mode.

**The assumption inventory as a process artifact.** `docs/CLAUDE_AUTH_INVENTORY.md` catalogs every undocumented Anthropic surface caam touches (CLAUDE-001 through CLAUDE-010), each with file+symbol, the assumption, observed reality, a classification (Correct / Fixable / Remove-Disable), and resolution status. Findings worth knowing regardless of caam: current `claudeAiOauth` no longer carries `email` or `accountId` (identity extraction returns empty, `internal/identity/claude.go: ExtractFromClaudeCredentials`); Claude access tokens are opaque, not JWTs (their JWT decoding was removed); an undocumented usage API exists at `api.anthropic.com/api/oauth/usage` with header `anthropic-beta: oauth-2025-04-20` returning `five_hour`/`seven_day`/`opus` utilization windows (`internal/usage/claude.go: ClaudeFetcher.Fetch`, marked experimental).

## Comparison against Transport Matters

Overlap is real but partial. caam's center of gravity is many accounts, one machine, quota juggling. TM's is one owned fleet identity, wire capture, and operational readiness. The shared subproblems:

| Problem | caam | TM today |
|---|---|---|
| Home isolation | Shallow symlink-through `$HOME`, declared per-provider real-file sets | Fleet home at `~/.claude-auth` separate from user `~/.claude`, linked `runtime-access/` |
| Keychain credential | Not handled; forced to file where possible | `SecurityOwnerCredentialStore` + `CredentialBroker` minting access-only copies |
| Refresh | Disabled for Claude (speculative endpoint); enabled Codex/Gemini | `HttpxTokenExchanger` performs real exchange |
| Credential drift | `authwatch.Tracker` hash-based watcher, poll + persisted state | Nothing watches the credential home (known gap) |
| Bad-credential detection | Regex on CLI stdout + error-string taxonomy | Unclassified output on expiry (known gap); but TM sees the wire |
| Re-auth in product | PTY `/login` injection with output pattern matching | Being designed (operational readiness) |
| Concurrent agents, one account | Avoided (one account per session) | Actual TM problem; caam offers nothing |

Where caam is cleaner than TM: nothing structural. The shallow-profile declared-layout approach (`providerLayout` as data, one generic `Manager.Create` consuming it) is a tidy shape, but TM's per-harness dispatch in `resolve_harness_credential_source` already encodes the same principle at the source level, and TM's isolation requirement (capture, not identity multiplexing) does not need symlink-through homes.

Where TM is ahead and should not regress: the keychain broker. caam's whole design assumes bearer-token files it can copy, including refresh tokens, into vault directories and per-profile homes. TM's access-only minting into `runtime-access/` (`CredentialBroker._write_shared_credential`) deliberately keeps the refresh token out of agent-reachable homes. Do not import vault-style whole-credential copying.

## What to adopt

Ranked. All as patterns reimplemented in TM's Python, not lifted Go (see license section).

1. **A credential drift watcher, authwatch-shaped.** This is the direct fill for TM's named gap ("nothing today watches the credential home; deleted mid-session, agents fail at expiry as unclassified output"). The design to copy: snapshot per-source `AuthState` (content hash, per-file hashes, checked-at), classify transitions as new/modified/removed, poll on a coarse interval, persist state across restarts, and surface removed/foreign states into readiness. In TM this sits next to `CredentialBroker` and feeds the operational-readiness surface; the symbols it touches are `CredentialBroker` (or a new sibling module the broker and doctor both consume), `shared_access_credential_error`, and the readiness checks under design. Classification matters more than detection: "removed" and "replaced by a credential we did not mint" are different operator messages.
2. **Auth-relevant-field hashing.** When watching Claude files, hash only the token-bearing fields, never whole files; `.claude.json` is rewritten every run and whole-file hashing produces permanent false drift. caam learned this the hard way. Applies to whatever the TM watcher hashes in the fleet home and `runtime-access/`.
3. **Error taxonomy for credential failure, applied at the wire.** Keep caam's four-way classification (auth / rate-limit / server / timeout, `PenaltyForError`) but drive it from what the proxy actually sees (HTTP 401/403 vs 429 vs 5xx on the outbound turn) instead of regexing CLI output. This converts TM's "fails as unclassified output" into a typed readiness event at the layer where TM is uniquely positioned. Touches the proxy's response classification and whatever readiness event stream the operational-readiness design lands on.
4. **Refresh-before-expiry as a monitor loop.** caam's `authpool.Monitor` shape (check interval, refresh threshold before expiry, bounded concurrency, per-profile state machine) maps cleanly onto TM re-minting via `CredentialBroker`/`HttpxTokenExchanger` before the shared access credential expires, rather than reacting to failure. TM already owns a working exchange; it just lacks the proactive loop.
5. **Audit the Agent View / background-supervisor risk now.** If any Claude Code build ships a cross-session background supervisor, a TM-launched captured run could reconnect to a supervisor bound to the user's own identity, bypassing both the fleet credential and, worse for TM, the capture proxy. Verify whether TM's launch env (the `prepare_captured_run()` seam and the claude launch path) needs to set `CLAUDE_CODE_DISABLE_AGENT_VIEW=1` and scrub `CLAUDE_CONFIG_DIR` the way `shallow.SpawnEnv` does. This is a capture-integrity question, not just an identity one.
6. **The assumption-inventory doc pattern.** TM depends on undocumented surfaces too (keychain item shape, `claudeAiOauth` schema, the token exchange endpoint, Codex auth.json). A CLAUDE_AUTH_INVENTORY-style doc with assumption / observed reality / classification / verification date per surface is cheap and pays out exactly when Anthropic or OpenAI changes something. Their concrete findings (no email/accountId in current credentials, opaque non-JWT tokens, the `api/oauth/usage` endpoint with `anthropic-beta: oauth-2025-04-20`) are immediately reusable facts.

## What to avoid

- **Do not adopt file-forcing as a keychain answer.** `EnsureFileCredentialStore` is caam's workaround for not having a broker. TM has a broker. Forcing file storage would move the refresh token onto disk in agent-reachable homes and regress TM's main security property.
- **Do not adopt stdout/stderr regex as the failure sensor.** It is the best caam can do from outside the process; TM sees the bytes and should never rank a regex over an HTTP status.
- **Do not lift their Claude refresh code.** They marked it speculative and disabled it. TM's exchanger is the working implementation; theirs is a stub around a guessed endpoint.
- **Do not copy the PTY login pattern matching wholesale.** Hardcoded English UI strings ("opening browser", "enter the code") are a fragility TM's re-auth design should improve on; TM can observe the OAuth callback traffic on the wire instead of guessing from terminal text.
- **Do not import whole-credential vault copies.** Their vault stores full credentials, refresh tokens included, per profile directory. Contradicts TM's access-only minting.

## Licence and maintenance

**Licence: MIT with an "OpenAI/Anthropic Rider"** (GitHub reports NOASSERTION because of it). The rider denies all rights to OpenAI, Anthropic, their affiliates, and anyone acting on their behalf; forbids providing the software or any derivative work to those parties; requires the rider be included unmodified in all distributions of derivatives; and terminates the licence automatically on breach. Practical read for Helioy: Helioy is not a restricted party, so use and modification are permitted. But lifting code makes TM (or the touched module) a derivative work carrying a viral restriction: TM could then never be provided to, hosted for, or made accessible to Anthropic or OpenAI, which is a real strategic constraint for a product in this space (a demo to either company would arguably breach). Patterns and ideas are not copyrightable; reimplementation from this research is clean. Recommendation: **pattern adoption only, no code lifting.**

**Maintenance:** healthy. Created 2025-12-17, last commit 2026-07-23 (a week before this review), 154 stars, 2 open issues, signed releases via goreleaser with cosign verification, extensive test suite (unit + e2e per package), CHANGELOG maintained, active fix cadence referencing real user issues (#49 Agent View, #55 plugin enablement, #56 skills sharing, #57 Grok provider). Repo carries heavy AI-assisted-development exhaust (35KB AGENTS.md, improvement-prompt files, large images) but the Go code itself is disciplined: atomic writes everywhere, per-package tests, documented assumptions.

## Sources consulted

README.md; LICENSE; docs/CLAUDE_AUTH_INVENTORY.md; internal/authwatch/authwatch.go; internal/authfile/authfile.go; internal/shallow/shallow.go; internal/refresh/{refresh,claude}.go; internal/health/{expiry,penalty}.go; internal/identity/claude.go; internal/ratelimit/detector.go; internal/wrap/wrap.go; internal/handoff/claude.go; internal/authpool/monitor.go; internal/rotation/rotation.go; internal/provider/codex/codex.go; internal/provider/claude/claude.go; git log; GitHub API metadata. TM side: api/src/transport_matters/credential_broker.py, api/src/transport_matters/cli/credential_source.py (read-only, symbol confirmation).

## Open questions

- Whether the current Claude Code release actually ships Agent View / a background supervisor in the builds TM launches, and whether TM's launch env already scrubs `CLAUDE_CONFIG_DIR`. Ten-minute check against the TM launch path.
- Whether the undocumented `api/oauth/usage` endpoint still works and whether TM wants it as a readiness signal (quota headroom) or should stay away from undocumented surfaces on principle.
- caam offers nothing for TM's real concurrency problem (N agents sharing one minted credential and its refresh cycle); that remains TM's own design work.
