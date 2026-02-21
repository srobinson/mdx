---
title: Nancy CLI Worker Spawn — No MCP Config Passed
type: research
tags: [nancy, claude-cli, mcp, worker-spawn, linear-server]
summary: Nancy spawns claude workers with bare flags only — no --mcp-config, no --allowedTools, no MCP server spec. Workers inherit MCP solely from whatever .claude/settings.json exists in their cwd (the git worktree).
status: active
source: quick-research
confidence: high
created: 2026-03-09
updated: 2026-03-09
---

## Summary

Nancy does not pass any MCP configuration when spawning a worker agent. The `claude` binary is invoked with only these flags:

```
claude \
  --dangerously-skip-permissions \
  --session-id <uuid> \
  [--agent helioy-tools:<role>] \
  [--model <model>] \
  --include-partial-messages \
  --output-format stream-json \
  --verbose --debug \
  -p "<prompt>"
```

No `--mcp-config`, `--allowedTools`, or any equivalent flag is passed. MCP server availability is therefore entirely determined by what `.claude/settings.json` (or `settings.local.json`) Claude discovers in the working directory at the time it is invoked.

## Details

### The spawn path

`cmd::start` (in `src/cmd/start.sh`) calls `cli::run_prompt` (dispatched in `src/cli/dispatch.sh`) which resolves to `cli::claude::run_prompt` in `src/cli/drivers/claude.sh`.

The entire argument construction in `cli::claude::run_prompt` (lines 136–153):

```bash
local args=("--dangerously-skip-permissions")
args+=("--session-id" "$uuid")

if [[ -n "$agent_role" ]]; then
    args+=("--agent" "helioy-tools:${agent_role}")
fi

if [[ -n "$model" ]]; then
    args+=("--model" "$model")
fi

args+=("--include-partial-messages" "--output-format" "stream-json" "--verbose" "--debug")
args+=("-p" "$prompt_text")
```

That is the complete set. No MCP flags anywhere in the codebase (confirmed by a grep for `mcp|allowedTools|--config` across `src/**/*.sh` — zero hits).

### Working directory at spawn time

`_start_setup_worktree` runs `cd "$worktree_dir"` before the iteration loop, so claude is launched from inside the git worktree (`<parent>/<repo>-worktrees/nancy-<task>`). Claude will look for `.claude/` settings in that directory tree.

If the worktree does not have a `.claude/` directory with MCP config, or if the project's `.claude/settings.json` does not list `linear-server`, the worker will not have it.

### Why linear-server is missing

The nancy project root had a `.claude.bk/` backup but no active `.claude/` directory at the time of inspection. The worktree directories are fresh checkouts — they would inherit only whatever `.claude/` config was committed to the repo (none is) or what Claude discovers via its own project-path lookup (`~/.claude/projects/<encoded-path>/`).

Claude's MCP server config lives in `~/.claude/settings.json` at the user level, OR in a per-project `.claude/settings.json`. If `linear-server` is configured only in one project's `.claude/settings.json` and the worktree path does not match that project, the server is invisible to the worker.

## The Root Cause

Claude resolves MCP servers by project path. When nancy creates a worktree at a new path like `../echoecho-worktrees/nancy-ALP-123/`, that path has no `.claude/` settings file and does not match any pre-existing Claude project config. The user-level `~/.claude/settings.json` is checked, but `linear-server` may only be configured at the project level for the main checkout.

## Fix Options

1. **Add `.claude/settings.json` to the repo root** listing all required MCP servers. Git worktrees share the parent repo's `.claude/` via `git worktree add`, so the settings file will be present in the worktree automatically.

2. **Commit a `.claude/settings.json`** in the project that includes `linear-server` in `mcpServers`. Workers spawned in any worktree of that repo will pick it up.

3. **Move `linear-server` to `~/.claude/settings.json`** (user-global level) so it is available regardless of project path.

4. **Patch `cli::claude::run_prompt`** to accept and pass `--mcp-config <path>` once the Claude CLI exposes that flag stably.

## Sources

- `/Users/alphab/Dev/LLM/DEV/TMP/nancy/src/cli/drivers/claude.sh` — lines 125–196 (`cli::claude::run_prompt`)
- `/Users/alphab/Dev/LLM/DEV/TMP/nancy/src/cmd/start.sh` — lines 136–164 (worktree setup + invocation)
- `/Users/alphab/Dev/LLM/DEV/TMP/nancy/src/cli/dispatch.sh` — routing layer
- `/Users/alphab/Dev/LLM/DEV/TMP/nancy/.nancy/config.json` — project config (cli, model, token_threshold only)
- `/Users/alphab/Dev/LLM/DEV/TMP/nancy/.claude.bk/settings.local.json` — backed-up settings (permissions + hooks, no MCP config)

## Open Questions

- Does `claude --dangerously-skip-permissions` bypass project-level settings lookup? Worth verifying.
- Does `--agent helioy-tools:<role>` load an agent profile that could inject MCP servers? Undocumented behavior worth checking.
