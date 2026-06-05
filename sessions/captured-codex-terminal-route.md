---
title: Captured Codex Terminal Route
type: sessions
tags: [backend, captured-run, codex, websocket, security]
summary: Added backend captured Codex terminal support through one provider-parametric captured run route.
status: active
source: backend-engineer
confidence: high
created: 2026-06-09
updated: 2026-06-09
---

## Summary

Implemented backend PR-a for captured Codex panes on `feat/captured-codex`.

Key decisions:

- Preserved the existing Claude route, `/api/captured-runs/claude/terminal`, and kept it registered before the parameterized route.
- Added `/api/captured-runs/{cli}/terminal` with a strict `claude | codex` allowlist before any captured run preparation or spawn.
- Generalized captured terminal preparation by provider while reusing `prepare_captured_run`, `terminal_bridge`, and the nested `web_runtime=external` path.
- Collapsed the redundant Claude wrapper and provider dispatch helper. `_captured_terminal_socket` now calls the one provider-parametric `_prepare_captured_agent_run` path for Claude and Codex.
- Codex uses the existing Codex launch profile and explicit HTTPS proxy environment. It launches the real Codex CLI and relies on native ChatGPT subscription auth, not API keys.
- Added `captured_codex.py` as a small shared helper so captured run Codex launch reuses public Codex command helpers without copying invocation logic.
- Folded the two deferred #65 minors: `close_runtime` now closes web before capture, and Codex uses `require_web_port` rather than a cast for embedded web launches.

## API Contract

```typescript
type CapturedRunCli = "claude" | "codex";

// Existing route, preserved.
// WS /api/captured-runs/claude/terminal?cols=80&rows=24&cwd=/absolute/path

// Provider route.
// WS /api/captured-runs/{cli}/terminal?cols=80&rows=24&cwd=/absolute/path

interface CapturedRunTerminalQuery {
  cols?: number;
  rows?: number;
  cwd?: string;
}

interface CapturedRunReadyFrame {
  type: "captured-run.ready";
  cli: CapturedRunCli;
  runId: string;
  cwd: string;
  storageDir: string;
  proxyPort: number;
  webPort?: number;
  nativeSessionId?: string;
}

interface CapturedRunErrorFrame {
  type: "captured-run.error";
  code:
    | "origin_not_allowed"
    | "invalid_terminal_control_frame"
    | "session_store_unavailable"
    | "launch_failed"
    | "bind_conflict";
  message: string;
}
```

Unknown `cli` values are rejected with WebSocket policy violation code 1008 before spawn.

## Database Changes

No schema or migration changes.

Codex captured panes still write through the existing run directory and session store paths used by `prepare_captured_run` and the Codex launch profile.

## Security Considerations

The provider path parameter is a strict allowlist. It never selects an arbitrary binary or launch profile.

Codex panes use the real Codex CLI and native ChatGPT subscription authentication. No API credential flow was added. The child environment uses the existing managed child proxy sanitizer, explicit HTTP and HTTPS proxy variables, and `CODEX_CA_CERTIFICATE` handling.

Nested panes remain capture only with `web_runtime=external`, so no nested web sidecar or breakpoint control plane is exposed.

## Performance Notes

No nested web process is started for captured Codex panes. The new code reuses the existing Codex invocation and proxy setup instead of copying terminal or launch plumbing.

Line count limits held:

- `api/src/transport_matters/captured_run.py`: 684 lines
- `api/src/transport_matters/cli/launch_runtime.py`: 700 lines
- `api/src/transport_matters/cli/runner.py`: 700 lines
- `api/src/transport_matters/cli/codex_cmd.py`: 461 lines
- `api/src/transport_matters/api/v1/captured_terminal.py`: 302 lines after DRY cleanup
- `api/src/transport_matters/captured_codex.py`: 64 lines

## Verification

- `cd api && just ci`: exit 0, 1274 passed in 21.24s after cleanup commit `3e594fd`.
- `uv run mypy src/`: green inside `just ci`, `Success: no issues found in 319 source files`.
- `uv run ruff format --check src/`: green inside `just ci`, `319 files already formatted`.
- `uv run ruff check src/`: green inside `just ci`, `All checks passed!`.
- Focused captured terminal route tests: exit 0, 5 passed.
- `rg -n "_prepare_captured_run_for_cli|_prepare_captured_claude_run" api/src/transport_matters`: no matches after cleanup.
- `git diff --check`: exit 0.
- Existing CLI tests were not edited.
- Wire capture files were not edited.

PR: https://github.com/littleorgans/transport-matters/pull/66
Commits: `f3ba653`, `3e594fd`
Latest bus reply: `done: 3e594fd`

## Open Items

Frontend Codex pane UI and button wiring are intentionally left for the separate frontend slice.

Live local smoke was not run in this pane after backend PR-a because this slice adds the backend Codex route contract and DRY cleanup only.
