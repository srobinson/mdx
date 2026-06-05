---
title: Plan — t3code P1 Slice 4f, plain terminal onto the gateway + delete pty_session.py (D4)
type: projects
tags: [transport-matters, t3code, p1, slice-4f, scout, plan, terminal, pty, deletion]
summary: Move the bare /api/terminal shell pane onto the gateway's NodePtyAdapter and delete pty_session.py + api/v1/terminal.py + terminal_bridge's PTY half. The two WS protocols already share the identical inbound contract (binary bytes + the same {"type":"resize"} frame both sides of the language boundary), and the canvas client tolerates text frames, so the wire contract is preserved with ZERO canvas changes. Recommended shape: a socket-scoped PlainTerminalSessions service on the runtime reusing PtyPort + TerminalFanout backpressure + a pump extracted from runTerminalConnection — no run lifecycle, no capture. Python front door proxies /api/terminal to the gateway (RunProxyMount grows an /api router); web mode gets a terminal_unavailable close (decision D-f1, mirrors D2). Deletes 2 source + 2 test files, reduces terminal_bridge to its surviving origin/close half, and retires the last §3 POSIX-only PTY debt — the plain pane becomes Windows-capable.
status: active
source: scout (fable 5:2.1), first-hand on main @ 8be180a
confidence: high
created: 2026-07-08
---

# Plan — Slice 4f: plain terminal cutover + pty_session deletion

Citations file + symbol, verified on main @ 8be180a.

---

## 1. What /api/terminal actually is (Q1)

`api/v1/terminal.py::terminal_socket` (mounted by `api/v1/router.py` under
`/api`): origin-gate → `accept()` → `spawn_pty_process` (a bare `$SHELL` in
`settings.cwd`, `TERM=xterm-256color`) → `terminal_bridge.bridge_websocket_to_pty`
→ on disconnect `terminate_terminal_pty`. **Socket-scoped**: one socket = one
shell; close kills it. No capture, no lifecycle, no lease, no scrollback, no
multi-viewer.

**Wire protocol**: binary frames = raw PTY bytes both directions; text frames =
`{"type":"resize","cols":N,"rows":N}` (`terminal_bridge.parse_control_frame`).
Initial size via `?cols=&rows=` query.

**Canvas consumer**: `terminalSocket.ts::terminalSocketUrl` (`/api/terminal`) →
`openTerminalSocket` → `TerminalPane.tsx` via `terminalTransport.ts`. The client
treats binary as PTY bytes and routes inbound TEXT frames to an optional
`onTextFrame` (added for the captured-run frames) — the bare pane simply doesn't
register interest, so unexpected text frames are tolerated, not corrupting.

**Protocol comparison with the run terminal** (`runTerminalConnection.ts`):
INBOUND is already identical — binary bytes + the same resize text frame, and
`@tm/common terminalContract.parseTerminalResizeFrameText` parses exactly the
shape Python's `parse_control_frame` accepts (verified field-for-field).
OUTBOUND diverges: the run terminal prepends `run.terminal.ready`, scrollback
replay, `run.terminal.scrollback-end`, and `run.error` text frames; the plain
pane sends raw bytes only. Conclusion: **keep the plain pane's outbound contract
(bytes only) and the canvas needs zero changes.**

## 2. How it lands on the runtime (Q2) — recommended shape: (b), reuse without capture

Not (a): a bare shell is not a run — dragging it through `RunManager` buys
lifecycle/owner/views/capture-release semantics the pane has never had and a
REST surface nobody calls. Recommended:

- **`packages/runtime/src/service/PlainTerminalSessions.ts`** (new, small): a
  socket-scoped session registry over `PtyPort`. `open({cols, rows, cwd?})` →
  spawns via `NodePtyAdapter` (`$SHELL`/`%COMSPEC%` default argv computed here —
  the cross-platform win), wires the session into a **`TerminalFanout`** with
  one attachment and `scrollbackBytes: 0`; `close(sessionId)` disposes;
  `closeAll()` kills every live shell (wired into
  `gateway/src/main.ts::closeGatewayResources` beside `runManager.close()` so
  the 4e-b shutdown ordering also reaps shells — the gateway must not leak its
  children). Reusing the fanout is deliberate DRY: the byte-capped attachment
  queue gives bounded memory + slow-viewer close for free, exactly the
  backpressure the Python bridge got from its blocking read loop.
- **`packages/runtime/src/server/plainTerminalConnection.ts`** (new): the WS
  handler — spawn on connect, binary → `write`, resize text frame →
  `resize` (`parseTerminalResizeFrameText`), pump attachment output → binary
  sends, disconnect → close session. The output pump is **extracted from
  `runTerminalConnection.ts::pumpAttachmentOutput`** into a shared helper
  (it is already protocol-neutral: bytes + close handling); the plain handler
  simply never sends the ready/scrollback frames.
- **Route**: `WS /terminal` on `createRuntimeRouter` (serving at
  `/v1/terminal` under `RUNTIME_CONTEXT_PREFIX`), `RuntimeRouterDeps` grows
  `plainTerminals`.

## 3. How the canvas reaches it (Q3) — same-origin front door, proxied

Keep the front-door model: the canvas keeps calling `/api/terminal` on the
Python origin. `run_proxy.py` grows the forward:

- `RunRouteProxy.forward_terminal` generalizes to take a target path (today it
  hardcodes the run-terminal path); a new public `forward_plain_terminal(ws)`
  targets `{gateway}/v1/terminal` with the query string passed through.
- `RunProxyMount` gains a second router (`api_router`) carrying the
  `WS /terminal` route; `main.py::create_app` includes it under `/api` in the
  gateway branch, replacing `terminal.router` (which `api/v1/router.py` no
  longer includes at all).
- Web mode (`gateway_url` unset): the `/api` side mounts a stub route that
  accepts and closes 1008 `terminal_unavailable` (the plain client shows a
  disconnected pane) — mirror of the D2 runs stub. **D-f1 for Stuart**: accept
  plain-pane-unavailable in web mode (recommended — consistent with the locked
  D-d1/D2 posture; the alternative keeps pty_session alive and defeats D4).

## 4. Deletion set + importer evidence (Q4)

Fresh greps on main @ 8be180a:

| Symbol / file | Non-test importers | Disposition |
| --- | --- | --- |
| `pty_session.py` (whole file: `spawn_pty_process`, `TerminalPty`, `prepare_terminal_child`, `set_winsize`, `terminate_terminal_pty`, `terminate_process_group`, `write_all`, `close_fd`, `close_terminal_master`, `CHILD_EXIT_TIMEOUT_S` — the §3 POSIX-only debt: `setsid`/`TIOCSCTTY`/`killpg`) | `api/v1/terminal.py` (dying), `api/v1/terminal_bridge.py` (its dying PTY half) | DELETE |
| `api/v1/terminal.py` (whole file) | `api/v1/router.py` (the mount — drop the include) | DELETE |
| `terminal_bridge.py` PTY half: `bridge_websocket_to_pty`, `receive_websocket_input`, `send_pty_output`, `parse_control_frame`, `validated_dimension`, `TerminalControlError`, `DEFAULT_COLS/ROWS`, `MAX_COLS/ROWS`, `PTY_READ_CHUNK_SIZE` | only `terminal.py` (dying) — size constants have zero other importers (run-route users died in 4e-d) | DELETE the half; file survives reduced |
| `terminal_bridge.py` surviving half: `origin_allowed`, `origin_allowed_for_request`, `origin_allowed_from_headers`, `normalize_origin`, `request_origin_from_*`, `trusted_loopback_host`, `close_websocket_if_connected`, `send_run_error_and_close` | `api/v1/origin.py`, `api/v1/run_proxy.py`, `api/v1/runs_unavailable.py` | KEEP; reword module docstring (no longer a PTY bridge) |
| `test_pty_session.py` | its subprocess module-import check also covers `captured_run_models` | DELETE; fold the `captured_run_models` entry into `cli/test_captured_run.py::test_captured_run_modules_are_standalone_importable`'s existing parametrize |
| `api/v1/test_terminal.py` | mixes plain-pane tests (dying) with origin-helper tests (surviving symbols) | DELETE the pane tests; RELOCATE surviving origin/close-helper cases to a `test_terminal_bridge.py` (or keep the file reduced under a truthful name) |

`supervisor_pty*.py` is untouched (the CLI supervisor chain, unrelated to
pty_session — same distinction 4e-d preserved).

## 5. Touch list + test plan (Q6)

**TS (5):** `service/PlainTerminalSessions.ts` + test (new);
`server/plainTerminalConnection.ts` + test (new); `runTerminalConnection.ts`
(extract the shared pump); `runtimeRouter.ts` (+`/terminal` route, deps);
`index.ts` barrel; `gateway/src/main.ts` + `app.ts` (deps + close chain) +
gateway tests.

**Python (5):** `run_proxy.py` (generalized WS forward + `forward_plain_terminal`
+ `RunProxyMount.api_router`); `main.py::create_app` (mount proxy-or-stub under
`/api`, drop `terminal.router` from `api/v1/router.py`); new
`api/v1/terminal_unavailable.py` (or fold the stub into `runs_unavailable.py`
as a sibling route — DRY-preferred); `terminal_bridge.py` reduction; deletions
per §4.

**Tests:**
1. TS: spawn/echo/resize/close round-trip over the new route with `FakePtyPort`
   (router-level, mirrors the run-terminal suite); `closeAll` kills sessions on
   gateway close; slow-viewer overload closes (fanout reuse proof).
2. Python proxy: `/api/terminal` WS forwards bytes+resize to a stub gateway
   (extend `test_run_proxy.py`'s real-socket harness — the s1 pattern); dead
   gateway → clean 1011 (existing hardening path reused).
3. Web-mode stub: `gateway_url` unset → `/api/terminal` accepts then closes
   1008 `terminal_unavailable`; runs stub untouched.
4. Deletion safety: import-boundary + collection green with the files gone;
   `captured_run_models` import check preserved in its new home.
5. Manual (mac): desktop → open plain terminal pane → shell echoes; quit →
   no orphaned shell (`closeAll` + 4e-b ordering); note Windows pane now
   POSSIBLE (verification deferred to a Windows environment, 5b-adjacent).

## 6. Blast radius / parity / decisions

- **Zero canvas changes** (protocol preserved; client already text-frame
  tolerant). The one behavioral delta: the shell's cwd. Today Python spawns at
  `settings.cwd` (the workspace); the gateway process's cwd is NOT the
  workspace — the proxy must pass the workspace dir (query param `cwd` added by
  the Python proxy from `settings.cwd`, validated gateway-side) or the pane
  silently opens in the wrong directory. Called out as a build requirement,
  not a decision.
- **Parity**: `$SHELL` fallback (`/bin/bash`) moves to the TS session service
  with a Windows-aware default (`%COMSPEC%`); TERM env preserved.
- **D-f1 (Stuart)**: web-mode plain pane unavailable (1008 close) — recommended
  accept, consistent with D2/D-d1; rejecting it means keeping pty_session.
- **Risk**: the extracted pump must not change run-terminal behavior — the
  extraction is covered by the existing run-terminal suite staying green.
- Retires the last §3 POSIX-only PTY debt; after 4f the only POSIX-only
  surface left in the tree is the CLI supervisor chain (out of P1 scope).
