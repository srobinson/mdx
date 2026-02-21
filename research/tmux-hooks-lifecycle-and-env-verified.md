---
title: tmux Hooks for Pane/Session Lifecycle and Environment Variables
type: research
tags: [tmux, hooks, lifecycle, environment, helioy-bus, cleanup]
summary: Verified behavior of tmux lifecycle hooks (pane-exited, window-unlinked, session-closed) including format specifier expansion, scoping, and working directory. Tested on tmux 3.6a.
status: active
source: quick-research
confidence: high
created: 2026-03-20
updated: 2026-03-20
---

## Summary

Verified on **tmux 3.6a** via live testing. For the helioy-bus cleanup use case (catching `kill-window` / `kill-session`), the reliable approach is:

- **`session-closed`** — fires on `kill-session` and when the last window in a session is killed
- **`window-unlinked`** — fires on `kill-window` (every window unlinked, including all windows on `kill-session`)
- `#{hook_session_name}` and `#{hook_window}` give the correct dying entity's identity

**Critical: `pane-exited` does NOT fire for `kill-window` or `kill-pane`.** It only fires when the process inside the pane exits naturally.

---

## Details

### Hook Firing Matrix

| Trigger | `pane-exited` | `window-unlinked` | `session-closed` | Order |
|---|---|---|---|---|
| `kill-pane` (not last) | No | No | No | — |
| `kill-window` (not last window) | No | Yes | No | unlinked |
| `kill-window` (last window) | No | Yes | Yes | session-closed → unlinked |
| `kill-session` | No | Yes (per window) | Yes | session-closed → unlinked (×N) |
| Natural process exit | Yes | Yes (if last pane) | Yes (if only window) | exited → unlinked → closed |

Key observation: `session-closed` fires **before** `window-unlinked` when killing a session.

### After-Hooks that Exist (and Don't)

Valid `after-` hooks include: `after-kill-pane`, `after-split-window`, `after-new-session`, `after-new-window`, `after-select-window`, `after-send-keys`, etc.

**`after-kill-window` and `after-kill-session` do NOT exist.** Setting them returns `invalid option`.

### Format Specifiers in Hooks: The `hook_*` Variables

When a hook fires, the "current" pane/window/session context is **not the dying entity** — it resolves to the currently active session. Use `hook_*` variables instead:

| Variable | What it gives |
|---|---|
| `#{hook_session}` | Session ID of the entity that triggered the hook (e.g. `$93`) |
| `#{hook_session_name}` | Session name of the triggering entity (reliable) |
| `#{hook_window}` | Window ID of the window being unlinked (e.g. `@242`) |
| `#{hook_pane}` | Pane ID in `pane-exited` (gives dying pane ID) |
| `#{hook_client}` | Client name, if relevant |
| `#{hook_window_name}` | Window name of trigger |

**`#{pane_id}`, `#{session_name}`, `#{window_index}` in hook commands resolve to the current active context, NOT the dying entity.** This is a critical gotcha.

### pane-exited: PID Availability

`pane-exited` fires when the process exits naturally. By the time the hook runs, the pane is gone and `#{pane_pid}` gives the **currently active pane's PID**, not the dying one. `#{hook_pane}` gives the correct pane ID but the pane is already gone.

**Exception**: with `remain-on-exit on`, `pane-died` fires instead and the pane is still accessible — `#{pane_id}`, `#{pane_pid}`, and `#{pane_dead_status}` all resolve correctly. This is not practical for global use.

### Programmatic Hook Installation

No `~/.tmux.conf` modification required. Hooks live in server memory:

```sh
# Install
tmux set-hook -g session-closed "run-shell \"/path/cleanup.sh '#{hook_session_name}' '#{hook_session}'\""
tmux set-hook -g window-unlinked "run-shell \"/path/cleanup.sh '#{hook_window}' '#{hook_session_name}'\""

# Remove
tmux set-hook -g -u session-closed
tmux set-hook -g -u window-unlinked
```

Hooks survive as long as the tmux **server** is running. They are lost on server restart (all sessions killed).

### Hook Scoping

- `-g` = global, fires for all sessions
- Without `-g` / with `-t session` = session-scoped, fires only for that session
- Session-scoped hooks on the dying session **do not fire** for `session-closed` — the session options are gone. Only global hooks fire reliably.
- New sessions created after `set-hook -g` automatically have the global hooks apply.

### Array Hooks (Multiple Commands per Hook)

Hooks are stored as arrays. Setting without index clears and sets `[0]`. Use explicit indices to append:

```sh
tmux set-hook -g session-closed "run-shell 'first'"
tmux set-hook -g 'session-closed[1]' "run-shell 'second'"  # Note: quote brackets in zsh
```

Array entries fire in ascending index order. Setting without index (`set-hook -g session-closed ...`) **clears all existing entries** and sets `[0]`. Use explicit indices to preserve existing hooks.

`show-hooks -g` lists all array entries. An empty entry (no command) is a no-op placeholder.

### Environment in run-shell Hook Commands

The hook command runs with:
- **Environment**: the tmux **global server environment** (captured at server start). NOT the pane's environment.
- **Working directory**: the CWD of the tmux server process (wherever `tmux` was started). NOT the session's `session-path`.
- Custom vars set via `tmux set-environment -g VAR value` ARE accessible as `$VAR` in run-shell.

The `-c start-directory` flag on `run-shell` can override the working directory.

### Format Specifier Expansion

Format specifiers in hook commands ARE expanded by tmux before the shell command runs:

```sh
tmux set-hook -g session-closed \
  "run-shell \"/path/cleanup.sh '#{hook_session_name}' '#{hook_session}'\""
```

When `kill-session -t my-agent` runs, the script receives `my-agent` and `$93` as positional args. Verified working.

---

## Practical Recipe for helioy-bus

To catch both `kill-window` and `kill-session` for all sessions:

```sh
# Install hooks (from plugin init code, no tmux.conf required)
tmux set-hook -g session-closed \
  "run-shell \"/path/to/bus-cleanup.sh session '#{hook_session_name}' '#{hook_session}'\""
tmux set-hook -g window-unlinked \
  "run-shell \"/path/to/bus-cleanup.sh window '#{hook_window}' '#{hook_session_name}'\""

# Uninstall (from plugin teardown)
tmux set-hook -g -u session-closed
tmux set-hook -g -u window-unlinked
```

Caveat: using `session-closed` + `window-unlinked` together means **both will fire** when killing a session (session-closed first, then one window-unlinked per window). The cleanup script should be idempotent or use session-closed exclusively if window-level granularity isn't needed.

For `kill-pane` (non-last-pane): no lifecycle hook fires. This is acceptable since the session/window remains alive and the agent process continues in the window.

---

## Sources

- `man tmux` (tmux 3.6a, Darwin 25.2.0)
- Live testing via `tmux set-hook -g` + `run-shell` + log file observation
- Tested hooks: `pane-exited`, `pane-died`, `window-unlinked`, `session-closed`, `after-kill-pane`

## Open Questions

1. Does `window-unlinked` fire for windows unlinked via `unlink-window` (multi-session window sharing)? Not tested — likely yes based on the hook name.
2. Is there a hook equivalent to `after-kill-session`? No — confirmed invalid. The closest is `session-closed`.
3. If multiple plugins install hooks, is there a safe append pattern? Yes — use explicit array indices and a unique index range or check `show-hooks -g` before installing.
4. Hook persistence across tmux server restart: hooks are NOT persisted. If the server restarts (e.g., all sessions killed and `exit-empty on`), hooks must be re-installed. For helioy-bus this likely means installing on session creation or via a client-attached hook.
