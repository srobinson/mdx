---
title: Claude Code Hooks - All Supported Event Types and Matchers
type: research
tags: [claude-code, hooks, events, automation, lifecycle]
summary: Claude Code supports 19 hook events including UserPromptSubmit (user message) and Stop (assistant response). No hook fires on raw assistant content mid-stream; Stop fires after Claude finishes with last_assistant_message available.
status: active
source: quick-research
confidence: high
created: 2026-03-08
updated: 2026-03-14
---

## Summary

Claude Code hooks **do** support a user message hook (`UserPromptSubmit`) and an assistant response hook (`Stop`). There is no mid-stream assistant content hook. As of March 2026, there are **19 named hook events** covering the full session lifecycle.

---

## All Supported Hook Events

| Event                | When it fires                                                           |
| -------------------- | ----------------------------------------------------------------------- |
| `SessionStart`       | Session begins or resumes                                               |
| `UserPromptSubmit`   | **User submits a prompt, before Claude processes it**                   |
| `PreToolUse`         | Before a tool call executes (can block)                                 |
| `PermissionRequest`  | When a permission dialog appears                                        |
| `PostToolUse`        | After a tool call succeeds                                              |
| `PostToolUseFailure` | After a tool call fails                                                 |
| `Notification`       | When Claude Code sends a notification                                   |
| `SubagentStart`      | When a subagent is spawned                                              |
| `SubagentStop`       | When a subagent finishes                                                |
| `Stop`               | **When Claude finishes responding** (includes `last_assistant_message`) |
| `TeammateIdle`       | When an agent team teammate is about to go idle                         |
| `TaskCompleted`      | When a task is being marked as completed                                |
| `InstructionsLoaded` | When a CLAUDE.md or `.claude/rules/*.md` file is loaded                 |
| `ConfigChange`       | When a configuration file changes during a session                      |
| `WorktreeCreate`     | When a worktree is being created                                        |
| `WorktreeRemove`     | When a worktree is being removed                                        |
| `PreCompact`         | Before context compaction                                               |
| `SessionEnd`         | When a session terminates                                               |

---

## User Message and Assistant Response Hooks

### UserPromptSubmit

Fires **before** Claude processes the user's message. The hook receives `prompt` (the raw text submitted). You can:

- Inject additional context into Claude's context via stdout (exit 0)
- Use `additionalContext` field in JSON output
- Block the prompt (exit 2)

No matcher support -- fires on every prompt submission.

### Stop

Fires **after** Claude finishes responding. Receives:

- `stop_hook_active` (bool) -- true if a Stop hook already triggered a continuation, use this to prevent infinite loops
- `last_assistant_message` -- the text content of Claude's final response, so you do not need to parse transcript files

No matcher support -- fires on every response completion. Does not fire on user interrupts.

**There is no mid-stream or content-streaming hook.** If you need to inspect assistant response content, use `Stop` with `last_assistant_message`.

---

## Matcher Support by Event

Matchers are regex patterns that filter when a hook fires within its event type.

| Events                                                                                                                | Matcher filters on        | Example values                                                                     |
| --------------------------------------------------------------------------------------------------------------------- | ------------------------- | ---------------------------------------------------------------------------------- |
| `PreToolUse`, `PostToolUse`, `PostToolUseFailure`, `PermissionRequest`                                                | tool name                 | `Bash`, `Edit\|Write`, `mcp__.*`                                                   |
| `SessionStart`                                                                                                        | how session started       | `startup`, `resume`, `clear`, `compact`                                            |
| `SessionEnd`                                                                                                          | why session ended         | `clear`, `logout`, `prompt_input_exit`, `bypass_permissions_disabled`, `other`     |
| `Notification`                                                                                                        | notification type         | `permission_prompt`, `idle_prompt`, `auth_success`, `elicitation_dialog`           |
| `SubagentStart`, `SubagentStop`                                                                                       | agent type                | `Bash`, `Explore`, `Plan`, custom agent names                                      |
| `PreCompact`                                                                                                          | what triggered compaction | `manual`, `auto`                                                                   |
| `ConfigChange`                                                                                                        | configuration source      | `user_settings`, `project_settings`, `local_settings`, `policy_settings`, `skills` |
| `UserPromptSubmit`, `Stop`, `TeammateIdle`, `TaskCompleted`, `WorktreeCreate`, `WorktreeRemove`, `InstructionsLoaded` | **no matcher support**    | always fires on every occurrence                                                   |

---

## Hook Types

Four handler types are available:

| Type      | Mechanism                                                                                             |
| --------- | ----------------------------------------------------------------------------------------------------- |
| `command` | Shell command; stdin = JSON event data; stdout/stderr/exit code = output                              |
| `http`    | POST JSON to a URL; response body = output                                                            |
| `prompt`  | Single-turn LLM call (Haiku by default); returns `{"ok": true/false, "reason": "..."}`                |
| `agent`   | Multi-turn subagent with tool access; same ok/reason format; up to 50 tool turns, 60s default timeout |

---

## Exit Code / Output Contract

| Exit code      | Meaning                                                                  |
| -------------- | ------------------------------------------------------------------------ |
| `0`            | Allow; stdout added to Claude's context (SessionStart, UserPromptSubmit) |
| `2`            | Block; stderr shown to Claude as feedback                                |
| Other non-zero | Allow; stderr logged but not shown to Claude                             |

For structured control, exit 0 and write JSON to stdout using `hookSpecificOutput` with `permissionDecision` (PreToolUse) or `decision: "block"` (PostToolUse, Stop).

---

## Key Notes

- `PermissionRequest` hooks do not fire in non-interactive / headless mode (`-p`). Use `PreToolUse` instead for automated permission decisions.
- `PostToolUse` cannot undo actions already executed.
- Default hook timeout is 10 minutes (configurable per hook via `timeout` field in seconds).
- Stop hooks must check `stop_hook_active` to prevent infinite loops.
- Shell profile `echo` statements in `~/.zshrc` / `~/.bashrc` will corrupt JSON output from command hooks; guard them with `if [[ $- == *i* ]]; then`.

---

## Sources

- [Hooks reference](https://code.claude.com/docs/en/hooks) -- full event schemas, JSON formats, async/HTTP/prompt hooks
- [Automate workflows with hooks (guide)](https://code.claude.com/docs/en/hooks-guide) -- quickstart, examples, matcher table
- Web search results, March 2026

## Related Research

- `claude-code-external-notification-wakeup-mechanisms.md` -- multi-agent bus wakeup patterns, tmux send-keys reliability, Stop vs UserPromptSubmit for inbox polling
