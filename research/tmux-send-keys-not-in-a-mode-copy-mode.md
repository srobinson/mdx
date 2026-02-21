---
title: "tmux send-keys: 'not in a mode' error - root cause and fix"
type: research
tags: [tmux, send-keys, copy-mode, TUI, Claude-Code, helioy-bus]
summary: "not in a mode" fires when the target pane is in tmux copy-mode and send-keys is called WITHOUT -X. Fix is to detect pane_in_mode and cancel copy-mode before sending.
status: active
source: quick-research
confidence: high
created: 2026-03-14
updated: 2026-03-14
---

## Summary

`tmux send-keys -t TARGET "you have mail!" Enter` returns rc=1 with `not in a mode` repeated once per key argument when the target pane is in **tmux copy-mode**. This has nothing to do with the TUI application's raw/application mode. It is exclusively a tmux copy-mode state problem.

The fix: detect `#{pane_in_mode}` before sending, and if 1, call `tmux send-keys -t TARGET -X cancel` first.

## Root Cause

### What the error means

In `cmd-send-keys.c`, there are two code paths that emit `"not in a mode"`:

**Path A** (the one we hit): `-X` flag is present but `wme` (window mode entry) is NULL.

**Path B** (the user's actual case, confirmed by testing): pane IS in copy-mode and `-X` is NOT present. When copy-mode is active, tmux routes non-`-X` keys differently -- through the copy-mode key binding dispatch. The error fires because the text strings like `"you"`, `"have"`, etc. are not recognized as valid copy-mode commands.

### Why 7 repetitions

The command `["tmux", "send-keys", "-t", tmux_target, "you have mail!", "Enter"]` passes two key arguments: `"you have mail!"` and `"Enter"`.

- `"you have mail!"` produces **6** errors (tmux processes words/tokens within the string in copy-mode context)
- `"Enter"` produces **1** error
- Total: 7

Verified empirically with tmux 3.6a on macOS.

### Why TUI raw mode is not the issue

A TUI application (like Claude Code, `less`, `vim`, etc.) running in raw/application mode does NOT set `#{pane_in_mode}` to 1. That format variable is exclusively controlled by tmux's own copy-mode/view-mode. A TUI in raw mode receives `send-keys` input fine -- it goes directly to the PTY fd.

### How copy-mode gets activated on idle panes

The most common trigger: mouse scroll events. When Claude Code is idle and someone scrolls the terminal window, tmux interprets the scroll as a request to enter copy-mode. The pane is then stuck in copy-mode until explicitly exited.

## Detection

```bash
IN_MODE=$(tmux display-message -t "$TARGET" -p '#{pane_in_mode}' 2>/dev/null)
# Returns "1" if in copy-mode, "0" if not
```

Additional detail:
```bash
MODE_NAME=$(tmux display-message -t "$TARGET" -p '#{pane_mode}' 2>/dev/null)
# Returns "copy-mode" or ""
```

## Fix

### Shell approach

```bash
_tmux_nudge() {
    local target="$1"
    local text="${2:-you have mail!}"

    # Exit copy-mode if active - it does NOT inject keystrokes into the TUI app
    local in_mode
    in_mode=$(tmux display-message -t "$target" -p '#{pane_in_mode}' 2>/dev/null)
    if [ "$in_mode" = "1" ]; then
        tmux send-keys -t "$target" -X cancel
    fi

    tmux send-keys -t "$target" "$text" Enter
}
```

### Python approach (for bus_server.py `_tmux_nudge`)

```python
def _tmux_nudge(tmux_target: str) -> bool:
    """Send a 'you have mail!' keystroke to wake an idle Claude session."""
    try:
        # Exit copy-mode if active; -X cancel does not inject input into the TUI app
        mode_result = subprocess.run(
            ["tmux", "display-message", "-t", tmux_target, "-p", "#{pane_in_mode}"],
            capture_output=True, timeout=3,
        )
        if mode_result.returncode == 0 and mode_result.stdout.decode().strip() == "1":
            subprocess.run(
                ["tmux", "send-keys", "-t", tmux_target, "-X", "cancel"],
                capture_output=True, timeout=3,
            )

        result = subprocess.run(
            ["tmux", "send-keys", "-t", tmux_target, "you have mail!", "Enter"],
            capture_output=True,
            timeout=3,
        )
        _dbg(f"_tmux_nudge: target={tmux_target!r} rc={result.returncode} stderr={result.stderr.decode().strip()!r}")
        return result.returncode == 0
    except (subprocess.SubprocessError, FileNotFoundError, subprocess.TimeoutExpired) as e:
        _dbg(f"_tmux_nudge: target={tmux_target!r} exception={e!r}")
        return False
```

## Flags that do NOT help

| Flag | Behavior | Helps? |
|------|----------|--------|
| `-l` | Literal UTF-8, skips named-key lookup | No - still errors in copy-mode |
| `-H` | Hex key code | No - different input format, same routing |
| `-X` | Route to copy-mode command handler | No - this is for copy-mode commands (begin-selection, etc.), not text injection |
| `-K` | Route through client key table | No - would send to key bindings, not pane |

## Key Properties of `-X cancel`

- `cancel` is the copy-mode command that exits copy-mode (mapped to `q` in vi, `Escape` in emacs)
- When called via `send-keys -X cancel`, it exits copy-mode without writing any bytes to the underlying PTY
- The TUI application receives no input from this operation (verified empirically)
- Safe to call even if the pane is running Claude Code or any other raw-mode TUI

## What NOT to do

- Do not send literal `q` or `Escape` as a workaround -- these will be received by the TUI app
- Do not use `paste-buffer` as a workaround -- in copy-mode it pastes into the copy-mode buffer, not the app's stdin
- Do not omit the mode check and blindly send `-X cancel` -- if the pane is not in copy-mode, `-X cancel` itself returns `not in a mode`

## Sources

- tmux 3.6a source: `cmd-send-keys.c` (GitHub: tmux/tmux)
- Empirical testing on macOS with tmux 3.6a (Homebrew)
- tmux man page: `send-keys` section, `-X` flag documentation

## Open Questions

- Does Claude Code itself ever programmatically enter copy-mode? (Unlikely -- it's a TUI, not a tmux plugin)
- Could `mouse-scrolling` tmux option be disabled on Claude Code panes to prevent accidental copy-mode entry? (`set -t PANE mouse off` per-pane)
