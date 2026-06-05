# CLI Config Home Resolution: Claude Code (`.claude`) vs Codex (`.codex`)

> Deep-research synthesis, 2026-06-01. 18 sources, 85 claims extracted, 25 adversarially verified (3-vote panel), 23 confirmed, 2 killed. Question: how does each tool determine its actual home/config directory at runtime, and how does a script reliably resolve it.

## Foundation

Both CLIs build their config home from two layers: an **OS home-directory base** plus a **single environment-variable override** layered on top. Neither consults `XDG_CONFIG_HOME`. Neither has a `CLAUDE_HOME`-style alias. The override is the only seam.

## Resolution algorithm, side by side

| | Claude Code (`.claude`) | Codex CLI (`.codex`) |
|---|---|---|
| Default path | `~/.claude` | `~/.codex` |
| Home base | Node `os.homedir()` → `HOME` (POSIX), `%USERPROFILE%` (Windows) | Rust `dirs::home_dir()` → `$HOME` / `%USERPROFILE%` |
| Override var | `CLAUDE_CONFIG_DIR` | `CODEX_HOME` |
| Override semantics | Used **verbatim**; relocates the whole tree. Empty/arbitrary path is the documented "clean session" trick | Used **only if set and non-empty** (`.filter(\|v\| !v.is_empty())`); path is canonicalized |
| Override + missing dir | Tolerated (docs point the example at an empty dir) | **Fatal error** — target must already exist; Codex does not create it |
| XDG support | None | None |
| Separate `*_HOME` alias | None | None |

### Script logic each tool actually runs

```sh
# Claude Code  — verbatim if set; Windows default: %USERPROFILE%\.claude
config_dir="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"

# Codex CLI  — empty string counts as unset; when set, the dir must already exist
if [ -n "${CODEX_HOME:-}" ]; then config_dir="$CODEX_HOME"; else config_dir="$HOME/.codex"; fi
```

```js
// Node equivalent (Claude Code's own logic)
const os = require("node:os");
const path = require("node:path");
const claudeDir = process.env.CLAUDE_CONFIG_DIR || path.join(os.homedir(), ".claude");
```

## Claude Code detail

### What `CLAUDE_CONFIG_DIR` relocates

The **entire tree** moves under the override path: `settings.json`, `settings.local.json`, `projects/`, `todos/`, `statsig/`, `logs/`, `shell-snapshots/`, `backups/`, `plugins/`, `history.jsonl`, and the sibling dotfile `~/.claude.json`.

- **Linux / Windows**: `.credentials.json` also moves under the override → forces re-login.
- **macOS**: credentials live in the Keychain and are **not** relocated.

### Managed / enterprise settings never move

`managed-settings.json` lives at fixed system paths **outside** `~/.claude`, so the override never touches it and it always wins:

- macOS: `/Library/Application Support/ClaudeCode/managed-settings.json`
- Linux / WSL: `/etc/claude-code/managed-settings.json`
- Windows: `C:\Program Files\ClaudeCode\managed-settings.json` (moved from `C:\ProgramData\ClaudeCode\` as of **v2.1.75**)

### Settings precedence (highest → lowest)

1. **Managed** (cannot be overridden by config)
2. **Command-line args** (`--permission-mode`, `--settings`, session-scoped)
3. **Local** — `.claude/settings.local.json`
4. **Project** — `.claude/settings.json`
5. **User** — `~/.claude/settings.json`

The managed source itself resolves **first-found** across four tiers: server-managed (admin console) → plist/registry policy (macOS `com.anthropic.claudecode`; Windows `HKLM\SOFTWARE\Policies\ClaudeCode`) → file `managed-settings.json` → Windows user registry `HKCU\SOFTWARE\Policies\ClaudeCode`. `/status` reports exactly one active source: `(remote)`, `(plist)`, `(HKLM)`, `(HKCU)`, or `(file)`.

## Codex CLI detail

### What lives under `CODEX_HOME` (default `~/.codex`)

`config.toml` (primary user config), `auth.json` (or OS keychain/keyring), `history.jsonl` (when persistence enabled), `log/` (default `$CODEX_HOME/log`), `sessions`, `skills`, plus SQLite state and per-user caches.

- **Profiles**: per-file as `$CODEX_HOME/<name>.config.toml`, selected with `--profile <name>` (changed from in-config `[profiles.name]` sections in **0.134.0**, ~2026-05-27).
- **Project overrides**: `.codex/config.toml` within a repo (trusted projects only; closest file to cwd wins; a key blocklist cannot be overridden by project config).
- **Sub-override**: `CODEX_SQLITE_HOME` (defaults to `CODEX_HOME`) relocates only SQLite state.

### Source of truth

`fn find_codex_home()` in `codex-rs/utils/home-dir/src/lib.rs`:
- Reads `std::env::var("CODEX_HOME").ok().filter(|val| !val.is_empty())` → set only when present **and** non-empty.
- When set: `fs::metadata` check; `NotFound` → fatal `"CODEX_HOME points to ..., but that path does not exist"`; non-directory → `InvalidInput`; then `path.canonicalize()`. No `create_dir`.
- When unset: `home_dir().join(".codex")`. Existence is **not** verified at resolution time.

The OpenAI env-vars doc page documents `CODEX_HOME` (default `~/.codex`) but contains **no** per-platform path resolution and no XDG/HOME/USERPROFILE reference. The expansion lives in source, not docs.

## Caveats (what the verifier killed or qualified)

1. **Codex per-platform home branch — REFUTED 0-3.** The claim that Codex's `home_dir()` reads `$HOME` on POSIX and `USERPROFILE` on Windows was not substantiated by the cited source line. It is the general behavior of the `dirs`/`home` crate, but if exact Windows/WSL behavior is load-bearing (e.g. `USERPROFILE` unset, WSL with both present), verify against the crate docs.
2. **"Claude settings docs omit `CLAUDE_CONFIG_DIR`" — REFUTED 1-2.** The var is real and documented across `claude-directory`, `env-vars`, and `debug-your-config`.
3. **Time-sensitivity.** Windows `managed-settings.json` moved `ProgramData` → `Program Files` at v2.1.75. Codex profile layout changed at 0.134.0. Findings reflect state as of 2026-06-01.
4. **"Cannot be overridden"** for Claude managed settings is a config-hierarchy guarantee, not OS tamper resistance (re-syncs from server-managed on next fetch).
5. **Permission rules MERGE** across scopes rather than scalar-replace; "managed always wins" describes binding direction, not wholesale array replacement.

## Open questions

- Exact precedence between CLI flags and Managed settings at a managed deny boundary (Claude issue #19369).
- `dirs::home_dir` behavior on Windows/WSL edge cases when `USERPROFILE` is unset.
- Whether Codex sub-overrides beyond `CODEX_SQLITE_HOME` exist for `log/`, `sessions/`, `skills/`.
- Whether `CLAUDE_CONFIG_DIR` relocates plugin marketplace caches and OAuth refresh state identically across platforms.

## Primary sources

**Claude Code:** [settings](https://code.claude.com/docs/en/settings) · [.claude directory](https://code.claude.com/docs/en/claude-directory) · [debug-your-config](https://code.claude.com/docs/en/debug-your-config) · [admin-setup](https://code.claude.com/docs/en/admin-setup) · [server-managed-settings](https://code.claude.com/docs/en/server-managed-settings) · [env-vars](https://code.claude.com/docs/en/env-vars) · GitHub issues [#3833](https://github.com/anthropics/claude-code/issues/3833), [#14313](https://github.com/anthropics/claude-code/issues/14313)

**Codex:** [config-advanced](https://developers.openai.com/codex/config-advanced) · [config-reference](https://developers.openai.com/codex/config-reference) · [config-basic](https://developers.openai.com/codex/config-basic) · [environment-variables](https://developers.openai.com/codex/environment-variables) · [`find_codex_home` source](https://github.com/openai/codex/blob/main/codex-rs/utils/home-dir/src/lib.rs) · [docs/config.md](https://github.com/openai/codex/blob/main/docs/config.md) · [`home::home_dir`](https://docs.rs/home/latest/home/fn.home_dir.html)
