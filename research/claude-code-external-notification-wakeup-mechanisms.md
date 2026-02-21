---
title: Claude Code External Notification and Wakeup Mechanisms for Multi-Agent Systems
type: research
tags: [claude-code, hooks, multi-agent, tmux, notifications, inter-agent, helioy-bus]
summary: Claude Code has no built-in idle polling or signal-based wakeup. The best hook-based approach for bus-style messaging is UserPromptSubmit (check inbox on every user turn) or Stop (check inbox after every response). tmux send-keys works but requires the TUI to be in input-ready state. TeammateIdle is the native mechanism for agent teams but requires the experimental agent-teams feature.
status: active
source: quick-research
confidence: high
created: 2026-03-14
updated: 2026-03-14
---

## Summary

Claude Code has **no built-in idle polling, periodic hooks, or signal handler for external wakeup**. The architecture is entirely event-driven around user/tool lifecycle points. For a helioy-bus style multi-agent system, the practical options rank as:

1. **`UserPromptSubmit` hook** -- inject inbox content on every user turn (lowest friction)
2. **`Stop` hook** -- check inbox after every response (catches both directions)
3. **`tmux send-keys` with `Enter`** -- injects simulated user input; works when TUI is idle at the prompt, unreliable if Claude is mid-response
4. **Native agent teams (`TeammateIdle`)** -- built-in wakeup mechanism, but requires experimental flag and fixed architecture

---

## Details

### 1. Built-in notification / idle mechanisms

**None exist for arbitrary external processes.** Claude Code does not expose:
- A signal handler (SIGUSR1, etc.) for "check external state"
- A named pipe or UNIX socket to accept messages
- A file watcher that triggers re-evaluation
- Any periodic/timer hook

The `Notification` event fires when *Claude Code itself* sends a notification to the user (e.g., idle prompt, permission prompt). It is outbound-only from Claude Code's perspective; you cannot trigger it externally.

The `TeammateIdle` hook fires when a teammate in an **agent team** is about to go idle. This is the closest thing to a built-in wakeup mechanism, but it only exists within the native agent-teams feature (experimental, requires `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`). In that model, the lead automatically delivers messages to idle teammates without needing tmux injection.

### 2. Hook events available -- full list

| Event | Fires | Blockable |
|---|---|---|
| `SessionStart` | Session begin/resume | No |
| `UserPromptSubmit` | User submits prompt, before Claude | Yes |
| `PreToolUse` | Before any tool call | Yes |
| `PermissionRequest` | Permission dialog appears | Yes |
| `PostToolUse` | After tool call succeeds | No |
| `PostToolUseFailure` | After tool call fails | No |
| `Notification` | Claude Code sends notification | No |
| `SubagentStart` | Subagent spawned | No |
| `SubagentStop` | Subagent finishes | Yes |
| `Stop` | Claude finishes responding | Yes |
| `TeammateIdle` | Agent team teammate about to idle | Yes |
| `TaskCompleted` | Task marked complete | Yes |
| `InstructionsLoaded` | CLAUDE.md loaded | No |
| `ConfigChange` | Config file changed mid-session | Yes |
| `WorktreeCreate` | Worktree being created | Yes |
| `WorktreeRemove` | Worktree being removed | No |
| `PreCompact` | Before context compaction | No |
| `SessionEnd` | Session terminates | No |

**No hook fires periodically or on idle.** Every hook is tied to a discrete lifecycle event.

### 3. UserPromptSubmit for inbox checking

`UserPromptSubmit` fires before Claude processes any user-submitted prompt. A hook registered here can:
- Read a message bus / mailbox file
- Inject unread messages as `additionalContext` into Claude's context
- Return exit 0 with JSON `{"hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext": "..."}}`

This is the most natural fit for helioy-bus: every time the human operator (or an automated prompt) fires a turn, pending bus messages are automatically injected. Claude sees them as part of its context and can respond.

**Limitation:** it only fires when the user submits a prompt. If agent B is sitting idle waiting for a message from agent A and no human turn happens, this hook never fires.

Example hook configuration:
```json
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "/path/to/check-bus-inbox.sh"
          }
        ]
      }
    ]
  }
}
```

```bash
#!/bin/bash
# check-bus-inbox.sh
INPUT=$(cat)
SESSION=$(echo "$INPUT" | jq -r '.session_id')
MESSAGES=$(bus-cli poll --session "$SESSION" --format json 2>/dev/null)
if [ -n "$MESSAGES" ]; then
  jq -n --argjson msgs "$MESSAGES" '{
    hookSpecificOutput: {
      hookEventName: "UserPromptSubmit",
      additionalContext: ("Pending bus messages:\n" + ($msgs | tostring))
    }
  }'
fi
exit 0
```

### 4. Stop hook for inbox checking

`Stop` fires every time Claude finishes a response. This catches both:
- Turns initiated by a human
- Continuation turns triggered by other hooks

A `Stop` hook can check the inbox and, if there are messages, return `{"decision": "block", "reason": "...messages here..."}` to prevent Claude from stopping and continue the conversation. This effectively wakes Claude on the next polling cycle.

**Caution:** `Stop` hooks must guard against infinite loops using the `stop_hook_active` field:
```bash
INPUT=$(cat)
if [ "$(echo "$INPUT" | jq -r '.stop_hook_active')" = "true" ]; then
  exit 0
fi
```

### 5. tmux send-keys behavior

Claude Code's TUI uses raw terminal mode (readline-style input). `tmux send-keys` does work to inject text, **but only when the TUI is sitting at the input prompt**. Specifically:

- When Claude is idle at the `>` prompt: `tmux send-keys -t <pane> "check your inbox" Enter` works reliably
- When Claude is mid-response (streaming): the keystrokes queue or get dropped, depending on terminal buffering
- When Claude is waiting for a permission prompt: the keys may interact with the permission UI, not the main input

The unreliability you experience is most likely from race conditions between Claude's response completion and the send-keys call. A safer approach is to wait for the idle state before injecting:

```bash
# Poll until the pane shows the input prompt (heuristic: look for "> " at end of pane)
until tmux capture-pane -pt "$PANE" | tail -1 | grep -q '^> '; do sleep 0.5; done
tmux send-keys -t "$PANE" "you have mail" Enter
```

This is still fragile because the prompt detection is heuristic. The hook-based approaches are more robust.

### 6. Alternative external wakeup approaches

| Approach | Reliability | Notes |
|---|---|---|
| `UserPromptSubmit` hook | High | Only fires on user turns; good for "check on next interaction" |
| `Stop` hook with block | High | Fires every response; can self-continue; must guard `stop_hook_active` |
| `tmux send-keys` | Medium | Works when idle; race-prone; needs pane-state detection |
| Named pipes / UNIX sockets | Not supported | Claude Code does not expose any socket |
| SIGUSR1 / signals | Not supported | No documented signal handling in Claude Code |
| File watcher triggering `tmux` | Medium | Wrapper: inotifywait on a mailbox file, then send-keys |
| HTTP hook endpoint | High | Run an HTTP server that Claude polls via a `Stop` hook |
| Native agent teams | High | Built-in mailbox + `TeammateIdle` hook; experimental; requires fixed architecture |

**Most practical pattern for helioy-bus without agent teams:**

Combine `Stop` hook (polls inbox after each response, self-continues if mail found) with `UserPromptSubmit` hook (injects mail into context on each human turn). This gives:
- Automatic wakeup within one turn cycle after mail arrives
- No tmux dependency
- Clean JSON context injection instead of raw text injection

### 7. Native agent teams architecture

If you can adopt the native agent teams feature (`CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`), the architecture already solves this problem:

- Each teammate has a **mailbox**
- Messages sent to a teammate are **delivered automatically**
- `TeammateIdle` hook fires when a teammate is about to go idle; returning exit 2 keeps them active
- No tmux required; communication is built into the Claude Code runtime

The limitation is that agent teams require a fixed lead/teammate topology created within Claude Code itself, and the feature is experimental with known limitations (no session resumption for in-process teammates, task status lag, no nested teams).

---

## Sources

- [Claude Code Hooks Reference](https://code.claude.com/docs/en/hooks) -- full event schemas, exit codes, JSON I/O
- [Automate workflows with hooks](https://code.claude.com/docs/en/hooks-guide) -- lifecycle table, UserPromptSubmit and Stop examples
- [Agent teams documentation](https://code.claude.com/docs/en/agent-teams) -- mailbox, TeammateIdle, architecture

---

## Open Questions

- Does Claude Code process `tmux send-keys` differently in headless (`-p`) vs interactive mode?
- Can the `Stop` hook's `additionalContext` field (if it exists; only confirmed for SessionStart and UserPromptSubmit) inject bus messages without blocking?
- Does the `TeammateIdle` hook fire reliably if the teammate is sitting idle between tasks in a long-running session, or only at the moment of going idle after completing assigned work?
- Is there a way to use HTTP hooks to receive a push from the bus (i.e., the bus POSTs to a local hook endpoint that Claude is polling)? This would invert the polling model.
