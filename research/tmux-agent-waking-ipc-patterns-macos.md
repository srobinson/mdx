---
title: Reliable IPC Patterns for Waking Idle TUI Agents in tmux (macOS)
type: research
tags: [tmux, ipc, multi-agent, claude-code, macos, signals, fifo, notify]
summary: Comprehensive analysis of alternatives to tmux send-keys for waking idle Claude Code TUI instances in a multi-agent setup, with reliability rankings and concrete implementation notes.
status: active
source: quick-research
confidence: high
created: 2026-03-14
updated: 2026-03-14
---

## Summary

The current `tmux send-keys "you have mail!" Enter` nudge approach is fundamentally sound but has two fixable bugs: (1) the bus_server call omits the `-l` (literal) flag causing the message text to be parsed as key names rather than literal characters; (2) the tmux target is stored as `session:window.pane` (positional) rather than the stable pane ID (`%N`). These two fixes alone would eliminate most failures.

The "not in a mode" error reported is specific to `send-keys -X`, which requires the pane to be in copy mode. Since the bus_server never uses `-X`, that error is coming from somewhere else in the toolchain (likely the nancy inject module or a manual invocation).

For a more robust long-term architecture, the FIFO + `pipe-pane -I` approach provides the most reliable delivery semantics.

## Details

### How Claude Code Reads Input

Claude (PID observed as 23569) holds fds 0/1/2 on `/dev/ttysXXX` (the pty slave). tmux holds the pty master. When `send-keys` writes text to the master, the kernel routes it to the slave — Claude's `read()` unblocks and receives the text as user input. This is the correct, supported mechanism.

When Claude is generating (busy), the keystrokes are queued by the kernel's pty buffer. Claude reads them the next time it polls its stdin. This is the desired "fire and buffer" behavior.

### Question-by-Question Findings

#### 1. Reliable alternatives to `tmux send-keys`

`send-keys` is the right primitive. The failure modes are:

- **Missing `-l` flag** — Without `-l`, tmux parses the string as key names. Spaces become `Space` keys, which works but is fragile if the message contains tmux key names like `Enter` or `Escape` as words. Always use `send-keys -l "$message"` followed by a separate `send-keys Enter`.
- **Wrong target format** — Storing `session:window.pane` breaks if windows are renamed or panes rearranged. Store and use pane_id (`%N`) directly. `TMUX_PANE` environment variable already provides this; the bus-register.sh converts it away unnecessarily.
- **The "not in a mode" error** — This only occurs with `send-keys -X`. Never use `-X` for injection. If this error is observed without `-X`, the target is resolving to a different pane that is in copy mode.

**Correct pattern:**
```bash
tmux send-keys -t "%85" -l "you have mail!" 2>/dev/null
tmux send-keys -t "%85" Enter 2>/dev/null
```

#### 2. `tmux pipe-pane` and `load-buffer`/`paste-buffer`

**pipe-pane -I**: With the `-I` flag, `pipe-pane` connects a shell command's stdout to the pane's stdin — text the command prints appears "as if typed." This creates a persistent injection channel.

Setup (at agent start, before Claude Code launches):
```bash
PANE_ID="$TMUX_PANE"
FIFO="$HOME/.helioy/bus/wakeup/$PANE_ID"
mkfifo "$FIFO" 2>/dev/null || true
tmux pipe-pane -I -t "$PANE_ID" \
  "while IFS= read -r line; do printf '%s\n' \"\$line\"; done < '$FIFO'"
```

Wake from any other process:
```bash
echo "you have mail!" > "$HOME/.helioy/bus/wakeup/$PANE_ID"
```

Limitations: only one pipe-pane per pane; Claude Code might use pipe-pane itself (unlikely but possible); the `while read` loop must be started before Claude occupies the pane's foreground — so setup must happen at the shell level before launching Claude.

**paste-buffer**: `tmux paste-buffer -t TARGET` pastes clipboard/buffer contents into the pane. Functionally equivalent to `send-keys` but without the literal flag issue. Not clearly better.

**load-buffer**: Loads content into a named buffer from a file. Used with `paste-buffer`. Works but is two commands and doesn't solve timing issues.

#### 3. Filesystem events (fswatch / FSEvents)

`fswatch` is available (`/opt/homebrew/bin/fswatch`). The pattern would be:

```bash
# In a wrapper script started alongside Claude
fswatch -1 "$HOME/.helioy/bus/inbox/$AGENT_ID" | while read event; do
    tmux send-keys -t "$TMUX_PANE" -l "you have mail!"
    tmux send-keys -t "$TMUX_PANE" Enter
done
```

**Assessment**: Viable but requires a sidecar process per agent. The latency is typically sub-100ms on macOS via FSEvents (the backend fswatch uses on macOS). This decouples the sender entirely — no need to know the tmux target, just write to the inbox directory. The sidecar translates filesystem events into tmux keystrokes.

This is actually an elegant architecture: the bus server drops a file, the local sidecar detects it and does the wakeup via tmux. No tmux target stored centrally.

#### 4. Unix signals (SIGUSR1/SIGUSR2)

Claude Code is a Node.js app. Node.js handles `SIGUSR1` by activating the V8 debugger — this is NOT safe to use. `SIGUSR2` is user-defined and Node does not assign a default handler, but Claude Code itself may or may not listen for it. There is no evidence Claude Code handles `SIGUSR2` to wake its TUI input loop.

**Assessment**: Do not use signals to wake Claude Code. The TUI input loop is driven by pty I/O, not signals. Even if Claude received SIGUSR2, it would not inject text into its own stdin.

Signals are useful for *sidecar* processes: you could signal a sidecar watcher script (which does handle SIGUSR2) to trigger a tmux send-keys. But this adds complexity for no benefit over filesystem events.

#### 5. Named pipe (FIFO) approach

A FIFO per agent is the most reliable delivery primitive available. The architecture:

```
sender                   |  per-agent sidecar              | Claude
                         |                                 |
write "msg" to FIFO ---> | while read; do                  |
                         |   tmux send-keys -l ... Enter   | ---> stdin
                         | done                            |
```

The FIFO write blocks until the sidecar reads it — giving backpressure and confirmed-delivery semantics. The sidecar is a long-running `while IFS= read -r line; do ...; done < "$FIFO"` loop.

This is the most robust approach because:
- Delivery is confirmed when the write unblocks
- Multiple senders can write sequentially (the kernel serializes FIFO writes)
- No race conditions with throttling logic
- No central registry of tmux targets needed

The downside: each agent needs a sidecar process. This could be a small bash script or a compiled binary.

#### 6. macOS-specific mechanisms: Darwin notify API and XPC

**Darwin notify (`notifyutil` / `notify_post`)**: Confirmed working. System-wide IPC via `notifyd`. Namespaced by string key (e.g., `com.helioy.agent.fmm`).

```bash
# Sender (any process):
notifyutil -p "com.helioy.agent.fmm"

# Receiver (sidecar listening for wakeup):
notifyutil -w "com.helioy.agent.fmm"
# Blocks until notification posted, then exits — use in a loop:
while notifyutil -1 "com.helioy.agent.fmm"; do
  tmux send-keys -t "$PANE_ID" -l "you have mail!" Enter
done
```

`notifyutil -1` exits after receiving exactly one notification. Loop it for persistent listening. This works across users and processes with no shared filesystem state required.

**Assessment**: Excellent fit for the sender side. Clean, no filesystem artifacts, system-managed. The receiver still needs to translate to a tmux keystroke, so it's a sidecar pattern like FIFO, just without the filesystem.

**TIOCSTI ioctl**: Exists on macOS (`sys/ttycom.h` confirms `#define TIOCSTI`). Injects characters directly into the terminal input queue. Requires the caller to own the terminal. In practice, since all Claude instances run as the same user (`alphab`), this works. But it requires a small C/Rust tool to call the ioctl — no shell-scriptable path.

**XPC**: Apple's structured IPC. Overkill and requires code-signing for production use. Not suitable here.

#### 7. "Fire and confirm delivery" pattern

The most reliable "fire and confirm delivery" pattern combines:

1. **Delivery**: Write message to filesystem inbox (already done — atomic rename)
2. **Wake signal**: Write to a per-agent FIFO or use `notifyutil -p`
3. **Confirm**: The sidecar acknowledges by writing an ack file or updating a timestamp
4. **Fallback**: A slow poll (every 60s) in the sidecar catches any missed wakeups

Concrete scheme:
```
~/.helioy/bus/
  inbox/
    {agent_id}/
      {message_id}.json     # already atomic via os.rename
  wake/
    {pane_id}               # FIFO per agent
  ack/
    {agent_id}              # timestamp of last wakeup processed
```

The FIFO write is the confirmation primitive: it blocks until the sidecar reads it, proving the sidecar is alive.

#### 8. `tmux wait-for` as a signaling mechanism

`tmux wait-for -S CHANNEL` wakes any client blocking on `tmux wait-for CHANNEL`. This is tmux-internal: the "client" is a tmux process, not Claude.

**Use case**: If a shell script runs `tmux wait-for "agent-B-ready"` before proceeding, another script can unblock it with `tmux wait-for -S "agent-B-ready"`. This works for coordinating shell scripts but cannot wake a running Claude Code TUI.

**Lock/unlock**: `wait-for -L CHANNEL` and `wait-for -U CHANNEL` provide a tmux-internal mutex. Useful for preventing concurrent `send-keys` races from multiple senders.

## Immediate Fixes for bus_server.py

Two bugs in `_tmux_nudge()`:

```python
# Current (buggy):
["tmux", "send-keys", "-t", tmux_target, "you have mail!", "Enter"]

# Fixed:
["tmux", "send-keys", "-t", tmux_target, "-l", "you have mail!"],
["tmux", "send-keys", "-t", tmux_target, "Enter"],
```

Split into two subprocess calls or use tmux `;` chaining:
```python
subprocess.run(["tmux", "send-keys", "-t", tmux_target, "-l", "you have mail!"], ...)
subprocess.run(["tmux", "send-keys", "-t", tmux_target, "Enter"], ...)
```

And in bus-register.sh, store the raw pane_id instead of converting it:
```bash
# Current:
TMUX_TARGET="$(tmux display-message -p -t "$TMUX_PANE" '#{session_name}:#{window_index}.#{pane_index}' ...)"

# Better:
TMUX_TARGET="$TMUX_PANE"  # already the pane_id e.g. %85
```

## Recommended Architecture (Longer Term)

For reliable multi-agent waking, add a per-agent **wakeup sidecar** started by warroom.sh alongside each Claude instance:

```bash
# In warroom.sh, before launching Claude in the pane:
WAKE_FIFO="$HOME/.helioy/bus/wake/$pane_id"
mkfifo "$WAKE_FIFO" 2>/dev/null || true

# Sidecar (runs in a subshell, not visible as a separate pane):
(while IFS= read -r _line; do
    tmux send-keys -t "$pane_id" -l "you have mail!" 2>/dev/null
    tmux send-keys -t "$pane_id" Enter 2>/dev/null
done < "$WAKE_FIFO") &

# Then launch Claude
tmux send-keys -t "$pane_id" "claude ..." Enter
```

The bus server then writes to the FIFO instead of calling send-keys directly:

```python
def _tmux_nudge(tmux_target: str) -> bool:
    fifo_path = Path.home() / ".helioy/bus/wake" / tmux_target.lstrip("%")
    if not fifo_path.exists():
        return _tmux_nudge_direct(tmux_target)  # fallback
    try:
        # Non-blocking open to avoid hanging if sidecar is dead
        fd = os.open(str(fifo_path), os.O_WRONLY | os.O_NONBLOCK)
        os.write(fd, b"wake\n")
        os.close(fd)
        return True
    except OSError:
        return _tmux_nudge_direct(tmux_target)  # fallback to send-keys
```

## Sources

- `tmux 3.6a` man page (locally installed)
- Darwin `notify(3)` man page (locally installed)
- `notifyutil` CLI testing (confirmed working on macOS 26.2)
- Live inspection of Claude Code process (`lsof -p 23569`)
- helioy-bus source: `server/bus_server.py`, `plugin/hooks/bus-register.sh`
- nancy source: `src/notify/inject.sh`

## Open Questions

- Does Claude Code use `pipe-pane` internally? If so, the pipe-pane -I approach conflicts.
- Is there a way to detect if a Claude Code instance is at its input prompt vs. actively generating? The `pane_in_mode` tmux format tells us copy/choice mode but not "generating vs. idle."
- The 30-second throttle prevents rapid nudges. Is there a way to check if the previous nudge was actually processed (i.e., if Claude read its inbox) before deciding to throttle? An ack file approach would enable this.
