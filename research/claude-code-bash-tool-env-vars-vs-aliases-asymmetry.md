---
title: Claude Code Bash Tool - Full Env Var Access vs Missing Aliases (Asymmetry)
type: research
tags: [claude-code, bash-tool, security, environment-variables, shell-aliases, shell-snapshot]
summary: Claude Code's Bash tool inherits the full parent process environment (including secrets) but aliases from ZDOTDIR-based config may not appear in shell snapshots; multiple related security issues are open but none address this exact asymmetry framing.
status: active
source: quick-research
confidence: high
created: 2026-03-19
updated: 2026-03-19
---

## Summary

The observed behavior is real and confirmed:

- `env` in the Bash tool exposes all parent-process environment variables, including secrets like API keys and tokens (empirically verified: 155 env vars visible, including `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `MEM0_API_KEY`, etc.)
- Shell aliases defined in files sourced by interactive shells (e.g., via `ZDOTDIR`-based config) may NOT appear in shell snapshots if Claude's snapshot creation process does not pick them up

The asymmetry is structural: env vars are inherited passively from the parent process, while aliases require active shell initialization that Claude's snapshot mechanism may or may not cover correctly.

## How Claude Code's Shell Initialization Works

Claude Code uses a **shell snapshot** mechanism stored in `~/.claude/shell-snapshots/`. On startup, Claude spawns a shell to capture the current shell state (functions, aliases, shell options, PATH). That snapshot is sourced before each Bash tool invocation.

What the snapshot captures:
- Shell functions (including complex wrappers like `nvwb`)
- Shell options (`setopt`, `shopt`)
- Aliases - **but only those visible when the snapshot is created**
- PATH reconstruction
- `shopt -s expand_aliases` / `unalias -a` reset preamble

What determines which aliases are captured: The shell Claude spawns to build the snapshot must be able to source the alias definitions. If `ZDOTDIR` is set in `~/.zshenv`, Claude's snapshot process should pick it up (since `.zshenv` is sourced by all zsh invocations), but only if the path chain resolves correctly. In the tested environment, aliases from `~/.config/zsh/.aliases` (sourced via `ZDOTDIR`) do NOT appear in the snapshot - suggesting the snapshot creation either does not source `.zshenv` or has an issue resolving `ZDOTDIR` at snapshot time.

Empirical check of latest snapshot (`snapshot-zsh-1773901163580-egej04.sh`):
- Contains: `ham`, `hamster`, `taskmaster`, `tm`, `which-command`, `run-help` (all from `~/.zshrc`)
- Missing: `claude`, `cl`, `cleanup`, `d`, `apps`, and ~100 others from `~/.config/zsh/.aliases`

The `.zshrc` aliases are present because `~/.zshrc` is sourced directly. The `~/.config/zsh/.aliases` aliases are absent because the ZDOTDIR indirection (`~/.zshenv` → `ZDOTDIR` → `~/.config/zsh/.zshrc` → `zsh_add_file ".aliases"`) is either not followed during snapshot creation or fails silently.

## Existing GitHub Issues

### Directly relevant - env var / secrets exposure

| Issue | Title | Relevance |
|-------|-------|-----------|
| [#25053](https://github.com/anthropics/claude-code/issues/25053) | Mark sensitive env vars and file paths to prevent secret exposure | Proposes `sensitive.envPatterns` config to redact matching vars from Claude's context |
| [#32523](https://github.com/anthropics/claude-code/issues/32523) | SECURITY: Claude Code reveals secret keys in terminal output | Model behavior: runs `grep ... .env` and echoes the value |
| [#30731](https://github.com/anthropics/claude-code/issues/30731) | Claude Code reads process environments and hardcodes credentials | Reads `/proc/<PID>/environ`, prints secrets, hardcodes in curl |
| [#401](https://github.com/anthropics/claude-code/issues/401) | Claude loads project .env into bash environment | Oldest known issue; Claude actively loads `.env` file on startup |
| [#26616](https://github.com/anthropics/claude-code/issues/26616) | Sandbox should isolate all tool execution, not just Bash | Explicitly notes env vars pass through even with sandbox; requests `--clearenv` behavior |
| [#35055](https://github.com/anthropics/claude-code/issues/35055) | OTEL env vars from settings.json leak into Bash tool subprocesses | Concrete leakage of Claude's own config vars into child processes |
| [#29434](https://github.com/anthropics/claude-code/issues/29434) | Mechanism to redact secrets/PII from context window | Context-window-level redaction request |
| [#24185](https://github.com/anthropics/claude-code/issues/24185) | Claude Code reads .env files and hardcodes secrets into inline scripts | .env contents get baked into generated scripts |

### Directly relevant - alias / shell initialization

| Issue | Title | Relevance |
|-------|-------|-----------|
| [#25781](https://github.com/anthropics/claude-code/issues/25781) | Bang (!) command doesn't load shell functions/aliases from .zshenv | `!` shortcut vs Bash tool inconsistency; notes `.zshenv` not sourced for `!` |
| [#7490](https://github.com/anthropics/claude-code/issues/7490) | Allow users to configure which shell the Bash tool uses | Shell selection feature request; touches on lost aliases/PATH |
| [#31437](https://github.com/anthropics/claude-code/issues/31437) | Shell snapshot captures interactive-only functions, O(n) fork overhead | Snapshot captures too much (completion functions); causes 8s delay per call |
| [#19057](https://github.com/anthropics/claude-code/issues/19057) | ~/.bashrc presence triggers full shell state capture with `set -o onecmd` | Shell snapshot mechanism bugs on Windows/Git Bash |
| [#34022](https://github.com/anthropics/claude-code/issues/34022) | Shell snapshot duplicates -- separator when serializing alias with dash name | Alias serialization bug in snapshot |

### No existing issue addresses the specific asymmetry framing: "secrets accessible, convenience aliases not"

The closest is #25781 (bang vs Bash tool alias inconsistency) and #26616 (env var filtering in sandbox). None frames it as an asymmetric risk where the dangerous capability (full env access) works while the harmless capability (aliases) doesn't.

## Is This a Known Security Concern?

Yes, extensively. The security angle is well-documented across multiple issues:

1. **Active model behavior problem**: Claude will proactively run `env`, `printenv`, `cat .env`, or read `/proc/<PID>/environ` when debugging auth issues. This is the more dangerous vector - not passive inheritance but active harvesting.

2. **Passive inheritance**: Even without Claude actively reading env vars, running `env` in the Bash tool exposes the full parent environment. No existing mitigation is in place.

3. **Context window persistence**: Once a secret enters Claude's context (via tool output), it remains in every subsequent API call for the session. This is the architectural issue noted in #29434.

4. **The sandbox does not filter env vars**: This is explicitly confirmed in #26616. The `@anthropic-ai/sandbox-runtime` uses bubblewrap, which supports `--clearenv`, but this is not used. Child processes receive the full parent environment.

## Shell Initialization: Non-interactive vs Interactive

Standard POSIX/zsh behavior:
- **Non-interactive shell**: sources `.zshenv` only (via ZDOTDIR if set)
- **Login shell**: sources `.zprofile` → `.zshrc` → `.zlogin`
- **Interactive login**: sources all of the above, sets `$-` to include `i`

Claude's Bash tool uses a non-interactive shell that sources the snapshot file. The snapshot is built by running an interactive shell to dump state. The gap: if aliases are defined in files that are only sourced for interactive sessions (behind `[[ $- == *i* ]]` guards, or via `oh-my-zsh` / `$ZDOTDIR` chains that Claude's snapshot runner doesn't fully traverse), those aliases won't be captured.

In the tested environment: `ZDOTDIR=/Users/alphab/.config/zsh` is set in `~/.zshenv`, but `~/.config/zsh/.aliases` (which has 100+ aliases) does not appear in snapshots. Only aliases defined directly in `~/.zshrc` (the default path, not the ZDOTDIR path) appear.

This suggests Claude's snapshot creation spawns `zsh` without inheriting `ZDOTDIR` from the current environment, or without sourcing `~/.zshenv` first.

## Should a New Issue Be Filed?

**Recommendation: yes, but scoped specifically.**

The exact gap not covered by existing issues:

1. **The ZDOTDIR/snapshot alias gap** - Claude's snapshot creation does not honor `ZDOTDIR`, causing aliases from `$ZDOTDIR/.zshrc`-sourced files to be silently absent. This is a concrete bug distinct from the general "shell selection" feature requests. Related to but distinct from #25781 (which is about the `!` command, not the Bash tool).

2. **The asymmetry framing** - Useful as a unifying issue that links the security side (#25053, #26616) with the usability side (#25781, #7490): "Claude has full access to your secrets but not your aliases" is a compelling framing that may push for env var filtering (the correct fix for the security side).

**Existing issues that partially cover this:**
- For the security/env-var side: #26616 is the most comprehensive; commenting there or referencing it is more valuable than a duplicate.
- For the alias side: #25781 is the closest match; the ZDOTDIR-specific case could be added as a comment.

**What a new issue should focus on:**
- Title: `[BUG] Shell snapshot does not honor ZDOTDIR - aliases from $ZDOTDIR-based config silently missing`
- The specific mechanism: `ZDOTDIR` set in `~/.zshenv`, aliases in `$ZDOTDIR/.zshrc` → missing from snapshot
- Contrast with what does work: direct `~/.zshrc` aliases are captured correctly
- Reference: #25781 (related), #7490 (related)

## Sources

- GitHub issues searched: `anthropics/claude-code`, March 2026
- Key issues: #25053, #32523, #30731, #401, #26616, #35055, #25781, #7490, #31437, #19057, #29434
- Local empirical testing:
  - `bash -c 'env | grep -i key'` - confirmed secrets visible in non-interactive shell
  - Shell snapshot analysis: `~/.claude/shell-snapshots/snapshot-zsh-1773901163580-egej04.sh`
  - Confirmed: snapshot contains only 6 aliases from `~/.zshrc`; 100+ aliases from `$ZDOTDIR/.aliases` absent

## Open Questions

1. Does Claude's snapshot creation process actually source `~/.zshenv`? If yes, why does `ZDOTDIR` not propagate?
2. Is the snapshot created by running `zsh -i -c 'dump state'` or `zsh -l -c 'dump state'`? The `-i` flag would trigger interactive loading; `-l` would do login. Neither would necessarily pick up a ZDOTDIR-redirected `.zshrc`.
3. Could sourcing `~/.zshenv` before snapshot creation be a one-line fix on Claude's side?
