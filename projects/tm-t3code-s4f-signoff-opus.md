---
title: Sign-off findings — t3code P1 Slice 4f (opus 5:2.3)
type: projects
tags: [transport-matters, t3code, p1, slice-4f, sign-off, review, terminal, pty, deletion]
summary: Opus independent sign-off on 4f (move plain /api/terminal onto the gateway + delete pty_session.py). Verdict GO-WITH-FIXES. The crux protocol-identity claim is verified field-for-field (dimension bounds match EXACTLY 80/24/500/200/1 both sides; resize shape identical; pump extraction boundary clean). Deletion genuinely dead. 2 must-fix + 3 confirm-deltas. First-hand on main @ 8be180a.
status: active
source: opus (5:2.3), first-hand on main @ 8be180a
confidence: high
created: 2026-07-08
---

# 4f plan sign-off (opus) — GO-WITH-FIXES

Verified the crux (WS protocol identity) and deletion-dead proof first-hand. The plan is strong;
the protocol claim holds and the deletion is clean. 2 must-fix (both build-completeness/correctness)
+ 3 behavioral deltas to adopt consciously.

## Confirmed sound (independently verified on main @ 8be180a)

- **WS inbound contract is genuinely identical.** Resize frame `{"type":"resize","cols","rows"}` matches
  field-for-field, AND the dimension bounds match EXACTLY: Python `terminal_bridge` DEFAULT_COLS=80/
  DEFAULT_ROWS=24/MAX_COLS=500/MAX_ROWS=200/min=1 vs `@tm/common terminalContract` DEFAULT 80/24 /
  MAX_TERMINAL_COLS=500/MAX_TERMINAL_ROWS=200/MIN=1. So a resize the Python pane accepted is accepted
  identically by `parseTerminalResizeFrameText`/`terminalSizeFromQueryValues` (query `?cols=&rows=`
  clamps the same). The "field-for-field verified" claim is real.
- **Outbound bytes-only preserved.** The plain pane's outbound is raw bytes; the client
  (`terminalSocket.ts` → optional `onTextFrame`) tolerates text frames it doesn't register. The new plain
  handler omits the run-terminal's ready/scrollback/run.error frames.
- **Pump extraction boundary is clean (no run-terminal regression).** In `runTerminalConnection.ts`,
  slow-viewer reason-aware close (`SLOW_VIEWER_CLOSE_CODE`) and bounded-queue backpressure live INSIDE
  `pumpAttachmentOutput`; the `run.terminal.ready` frame + scrollback replay live OUTSIDE it (before the
  pump call). So extracting the pump into a shared helper preserves run-terminal behavior byte-for-byte,
  and the plain handler gets bytes+slow-viewer-close for free by simply not doing the pre-pump ready/replay.
- **Deletion genuinely dead.** pty_session importers = terminal.py (dying) + terminal_bridge PTY-half
  (dying) + test_pty_session (deleted). api/v1/terminal.py importers = router.py include (dropped) +
  test_terminal.py (split). No SURVIVING non-test importer of any deleted PTY-half symbol
  (`bridge_websocket_to_pty`, `parse_control_frame`, size constants, …). The surviving terminal_bridge
  half (origin/close helpers) is imported by origin.py / run_proxy.py / runs_unavailable.py — all live.
  No circular import from the split. (test_runs_unavailable.py's `test_terminal_socket_...` is the RUN WS
  stub's run.error path, not /api/terminal — unaffected.)
- **Plain-shell reaping: no new leak class.** Graceful = `closeGatewayResources` → `plainTerminals.closeAll()`
  (beside `runManager.close()`, under 4e-b ordering). Hard gateway SIGKILL = the node-pty master closes →
  SIGHUP to the shell's foreground group → shell exits — the SAME mechanism the run-terminal agent already
  relies on; 5a (mitmdump addon-import) correctly does not and need not cover bare PTYs.
- **cwd is plain-only.** Captured runs resolve cwd via worktree resolution in the capture RPC (4e-a); the
  plain pane has no worktree and needs `settings.cwd` passed through. Not latent for captured runs.

## Must-fix

### M1 — terminal_bridge.py must drop its pty_session import + the re-export __all__ entries (dangling import)

`terminal_bridge.py` currently does `from transport_matters.pty_session import (TerminalPty, close_terminal_master,
prepare_terminal_child, spawn_pty_process, terminate_process_group, terminate_terminal_pty)` and RE-EXPORTS them
in `__all__`. "Delete the PTY half" must remove that import block AND those `__all__` entries, not just the
bridge functions — pty_session is deleted, so a lingering import fails collection. The plan describes deleting
the bridge functions but the import + re-exports are the actual dangling-import surface; call it out explicitly.

### M2 — cwd passthrough must URL-encode + gateway-side validate (the one behavioral delta the plan flags)

Python spawns at `_workspace_root(settings)` = `(settings.cwd or Path.cwd()).resolve()`. Post-cutover the
gateway process cwd ≠ the workspace, so the Python proxy must forward `settings.cwd` as a query param to
`{gw}/v1/terminal`. Build must: URL-encode the path (spaces/special chars in workspace paths are common);
gateway-side validate it exists + is a directory (+ reject traversal) before `NodePtyAdapter` spawns; and
fall back sanely (or close with a diagnosable reason) if absent/invalid — else the pane opens in the wrong
directory or the shell spawn fails opaquely.

## Confirm-deltas (adopt consciously; not blocking)

- **Invalid resize frame handling diverges.** Python `parse_control_frame` raises → `receive_websocket_input`
  closes 1008 on an invalid/out-of-range resize; TS `parseTerminalResizeFrameText` returns undefined → the
  handler ignores it (run-terminal's existing lenient behavior). Adopt the lenient path consciously (it's
  strictly safer) rather than replicate the Python close; note the tiny delta.
- **Slow-viewer behavior diverges.** The Python plain pane used a blocking read loop (backpressure: a stalled
  viewer pauses the shell). Reusing `TerminalFanout` gives the plain pane a slow-viewer CLOSE
  (`SLOW_VIEWER_CLOSE_CODE`) it never had — a backgrounded tab could now close the pane instead of pausing.
  Acceptable (run-terminal already made this trade), but confirm the client degrades gracefully on that close.
- **Web-mode 1008 stub must be a bare accept+close**, NOT `send_run_error_and_close` (which emits a
  `{"type":"run.error"}` frame the plain client ignores). The plan already specifies a bare close; if the stub
  is DRY-folded into `runs_unavailable.py`, keep it a bare `close(1008, "terminal_unavailable")`.

Scope discipline clean (D-f1 1008 posture consistent with D2/D-d1; supervisor_pty chain untouched). Retires the
last §3 POSIX-only PTY debt; the plain pane becomes Windows-capable. Strong plan — the crux checks out.
