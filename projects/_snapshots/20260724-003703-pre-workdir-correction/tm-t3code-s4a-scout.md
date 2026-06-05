---
title: t3code P1 slice 4a scout — PTY adapter + terminal wire contract
date: 2026-07-07
baseline: main @ f31bf03 (slices 0-3 merged)
spec: /Users/alphab/.mdx/projects/tm-t3code-p1-spec.md
verdict: build-ready
---

# S4a Scout — PTY adapter + terminal wire contract

Slice scope: `PtyPort` seam + `NodePtyAdapter` over node-pty in `packages/runtime`;
single-source the terminal wire contract in `packages/common`. No run lifecycle, no
scrollback/fanout, no capture, no serving.

## 1. Reuse Map

| Capability | Existing owner (reuse/port) | Disposition for 4a |
| --- | --- | --- |
| Spawn PTY (POSIX reference) | `api/src/transport_matters/pty_session.py::spawn_pty_process` + `prepare_terminal_child`, `set_winsize`, `write_all`, `terminate_terminal_pty`, `terminate_process_group`, `close_terminal_master` | Behaviour contract to match (section 4). Deleted in 4e; do not touch now. |
| PTY read → data/exit semantics | `run_manager.py::RunManager._drain_run` / `_handle_pty_readable` (loop `add_reader`, EIO/EBADF = normal exit) and `api/v1/terminal_bridge.py::bridge_websocket_to_pty` | Port the EOF/EIO-as-exit mapping into `NodePtyAdapter.onExit`. Fanout/queueing is 4b, not 4a. |
| Port seam home | `packages/runtime/src/ports.ts` (`CapturePort` precedent: plain interface, promise-based, no Effect) | Add `PtyPort` beside `CapturePort` in the same file. |
| Adapter pattern to mirror | `packages/runtime/src/adapters/CaptureRpcClient.ts` (class implements port; injected impl (`fetchImpl`) for unit tests; typed error class with `code`; `@tm/common` safe* field validation) | `adapters/NodePtyAdapter.ts` sibling, injecting the node-pty module for unit tests. |
| Untrusted-input validation | `packages/common/src/primitives.ts` safe* family (`safeRecord`, `nonEmptyString`, `safeInteger`, `safeBoolean`, `safeIntegerString`) | The wire-contract validators build on these. See section 5 for the zod verdict. |
| Shared-package barrel + boundary | `packages/common/src/index.ts` single barrel; `www/packages/shell/src/testSupport/importGraphBoundary.test.ts` already resolves `@tm/common` from canvas source and enforces single-barrel + no deep imports | Export `terminalContract` through the existing barrel. No new package. |
| xterm renderer contract | `www/packages/canvas/src/viewers/terminal/terminalSession.ts::useTerminalSession` (owns xterm `Terminal` + `FitAddon`, resize → `sendResize`); `infrastructure/runtime/internal/terminalSocket.ts::openTerminalSocket` (binary frames = raw PTY bytes both ways, text frames = JSON control, pre-open outbox); `terminalTransport.ts::browserTerminalTransport` (endpoint → URL) | Unchanged in 4a except frame parsing/serialization moves to the shared contract. |
| xterm round-trip test harness | `terminalSocket.test.ts` `FakeSocket` + `FakeTerm` (implements the injectable `TerminalIO` slice: `onData`/`write`) — protocol round-trip without real xterm or a server | Reuse: extend with shared-contract frames. |
| WS server test harness | `packages/runtime/src/server/runtimeRouter.test.ts` (`fastify.inject()` + `ws` client + tracked `afterEach` close) | Reuse if any 4a test touches the stub router. |
| Cross-platform PTY in TS | **none found** — `rg node-pty` empty (code and lockfile); no other PTY binding anywhere in the JS tree | New dep (section 6). |
| Plain-TS schema validation lib | **none found** — zod is not a dependency of any package; no Effect anywhere | Recommend against introducing it (section 5). |

## 2. Quality Map

**Duplicate terminal-frame definitions (the dup this slice exists to kill).** Every
current definition site of the wire vocabulary:

1. `api/src/transport_matters/api/v1/run_routes.py::run_terminal_ready_frame` — mints
   `run.terminal.ready` (run payload + `terminal{cols,rows}` + `scrollback{replayedBytes,truncated}`);
   `send_run_error_and_close` + `_send_attachment_output` + `bridge_attached_run_terminal`
   mint `run.error` and the inline `run.terminal.scrollback-end` literal.
2. `api/src/transport_matters/api/v1/terminal_bridge.py::parse_control_frame` +
   `validated_dimension` — consumes the inbound `{type:"resize",cols,rows}` frame with
   bounds `MAX_COLS=500`, `MAX_ROWS=200`.
3. `packages/runtime/src/server/runtimeRouter.ts` — stub WS handler re-mints
   `run.terminal.ready` and `run.error` as inline object literals, and re-declares
   `DEFAULT_TERMINAL_COLS/ROWS=80/24`, `MAX_TERMINAL_COLS/ROWS=500/200`.
4. `www/packages/canvas/src/viewers/terminal/runTerminalFrames.ts::parseRunErrorFrame` +
   `RunErrorFrame` — hand-rolled partial consumer of `run.error`.
5. `www/packages/canvas/src/infrastructure/runtime/internal/terminalSocket.ts::sendResize` —
   inline `{type:"resize",cols,rows}` literal (and `terminalSocketUrl(80, 24)` default).

Constants are consistent everywhere today (80/24 defaults, 500/200 maxima), so
single-sourcing is mechanical, no behaviour reconciliation needed. The Python sites
stay until 4e (route cutover); 4a single-sources the TS side and the Python side then
conforms or dies. Adjacent, out of 4a scope: `www/packages/core/src/transport.ts::RunView`
duplicates the run payload embedded in the ready frame — same magic-string-rule debt,
belongs to the 4c/4e run-view story, flag only.

**Boundary note (new edge).** No browser package imports a `packages/*` package today
(`@tm/common` consumers: runtime, gateway, activity). Canvas → `@tm/common` will be the
first browser→product-plane edge. It is legal by construction: the import-graph boundary
test already resolves `@tm/common` from canvas files and fails closed on deep imports;
`primitives.ts` is pure TS, zero Node APIs, so the vite bundle is clean. The
inspector/canvas dep-lint only forbids inspector↔canvas. Verify with the full shell
suite (structural cross-package change → `pnpm --filter @tm/shell test`, full, not
filtered).

**Near-dup to groom while touching the area.** `CaptureRpcClient.ts` private helpers
`stringField`/`integerField`/`booleanField`/`stringArray`/`stringRecord`/`record` are
generic required-field combinators with zero domain knowledge. Per `packages/AGENTS.md`
("the moment a primitive is needed by a second package it belongs in `@tm/common`"), if
the terminal contract wants the same idiom, promote the combinators to `@tm/common` and
refactor `CaptureRpcClient` to consume them in the same PR. If the contract's parsers
stay pure safe*-based (likely — frames are tiny), leave `CaptureRpcClient` alone.

**Other hygiene findings (no action in 4a).**
- `api/v1/terminal.py` is a 40-name re-export shim (including underscore aliases like
  `_close_fd`) kept for test seams — scheduled for deletion in 4e; do not grow it.
- `runtimeRouter.ts` WS handler is a deliberate slice-1 echo stub; 4a must make its
  frames consume the shared contract so 4c replaces the body, not the vocabulary.
- Sizing: everything in the area is well under thresholds (`pty_session.py` 173,
  `runtimeRouter.ts` 303, `CaptureRpcClient.ts` 254, canvas terminal files ≤165).
  `run_manager.py` at 682 is near the 700 line limit but is 4b-4e port-and-delete
  territory; do not add to it.
- Dead code: none found in the slice area.

## 3. Verified entry points (claimed → actual)

| Claimed (brief/spec) | Actual | Drift |
| --- | --- | --- |
| `pty_session.py::spawn_pty_process` | exists as described | none |
| `runtimeRouter.ts` `run.terminal.ready` + byte frames | exists; WS handler is an echo stub sending `run.terminal.ready` with hardcoded `scrollback:{replayedBytes:0,truncated:false}` | stub, as expected for slice 1 |
| `terminalSocket.ts::runTerminalSocketUrl` | exists at `www/packages/canvas/src/infrastructure/runtime/internal/terminalSocket.ts` | none |
| canvas xterm renderer under `viewers/terminal/` | `TerminalPane.tsx`, `CapturedRunPane.tsx`, `terminalSession.ts`, `runTerminalFrames.ts` | none |
| `packages/runtime/src/ports.ts` with `CapturePort` | exists; `CapturePort` only | spec also lists `LifecycleSink`, `Clock` — not yet present (later slices); `PtyPort` lands beside `CapturePort` |
| `adapters/CaptureRpcClient.ts` pattern | exists as described | none |
| safe* validators promoted to `@tm/common` | `packages/common/src/primitives.ts`, exported via single barrel | none |
| zod available | **not a dependency anywhere** | spec wording is "plain-TS validation (**e.g.** `zod`)" — example, not mandate; see section 5 |
| shared home `packages/contracts` or `@tm/common` | `packages/contracts` does not exist; `@tm/common` does, with the exact charter (`packages/AGENTS.md`) | use `@tm/common`; do not mint a new package |
| "standalone Runtime server" | the runtime router is mounted by `packages/gateway/src/app.ts` (`createGatewayApp` → `createRuntimeRouter` at the runtime prefix) and served by `packages/gateway/src/main.ts` (a plain Node process; Q8 covers its tsx spawn shape) | spec Q6 said Gateway "not built in P1", but the gateway serving root exists and is where node-pty will execute — a plain Node process, **not** Electron |

## 4. Behaviour contract `NodePtyAdapter` must match (from `pty_session.py` + its drivers)

Spawn (`spawn_pty_process`):
- Inputs `argv, env, cwd, cols, rows`; empty argv rejected before any fd is created.
- Winsize is set on the slave **before** exec, so the child sees correct dimensions at
  startup (node-pty: pass `cols`/`rows` in the spawn options — parity by construction).
- Child becomes session leader with the PTY as controlling terminal and foreground
  process group (`prepare_terminal_child`: `setsid`, `TIOCSCTTY`, `tcsetpgrp`), and the
  job-control signals (HUP/INT/QUIT/TERM/TSTP/TTIN/TTOU) are reset to default
  dispositions. node-pty's forkpty + spawn-helper does the session/controlling-tty
  setup; signal-default parity should be asserted behaviourally (Ctrl-C reaches the
  child) in the adapter integration test, not reimplemented.
- All three stdio fds bound to the slave; parent closes the slave after spawn; spawn
  failure closes both fds and propagates.
- Defaults: 80x24 (`DEFAULT_TERMINAL_COLS/ROWS`); read chunk 8192 (`PTY_READ_CHUNK_SIZE`).

Resize (`set_winsize`): `TIOCSWINSZ` on the master at any time → child gets SIGWINCH.
node-pty `resize(cols, rows)` is the direct equivalent (ConPTY resize on Windows).

Write (`write_all`): loop until all bytes written; **EIO/EBADF during write is treated
as "terminal gone" and swallowed**, not raised. Adapter parity: writes after exit must
not throw.

Read / onData / onExit (`_handle_pty_readable`, `bridge_websocket_to_pty::read_ready`):
- **EIO, EBADF, or empty read on the master = normal EOF** (macOS returns EIO when the
  last slave fd closes) → signals exit path, never an error. node-pty maps this to
  `onExit` internally; the adapter must expose exit exactly once with the exit code.
- Data flows as raw bytes today (WS binary frames end to end). **node-pty's `onData`
  delivers UTF-8 decoded `string`s, not bytes** — see open risks.

Terminate (`terminate_terminal_pty` → `terminate_process_group`):
- Grace-then-force on the **process group**: `killpg(SIGTERM)` → wait
  `CHILD_EXIT_TIMEOUT_S = 1.0s` → `killpg(SIGKILL)` → wait 1.0s; ProcessLookupError
  suppressed; PermissionError falls back to single-process terminate/kill.
- Master fd closed exactly once (`closed` flag on `TerminalPty`).
- Exit code read after teardown (`process.poll`).
- node-pty `kill(signal)` signals the **pid, not the group** (the pty child is the
  session leader, so descendants can survive). The grace-then-force group semantics are
  RunManager-level behaviour (4c), but `PtyPort` must expose `pid` and `kill(signal)` so
  it stays implementable; on POSIX `process.kill(-pid, sig)` reaches the group.

## 5. Terminal wire-contract single-source plan

**Home:** `packages/common/src/terminalContract.ts`, exported through the existing
single barrel (`packages/common/src/index.ts`). Name matches the spec's
`terminalContract`. No `packages/contracts` package — `@tm/common`'s charter
(`packages/AGENTS.md`) is exactly this, and a one-file package would violate DRY of
structure.

**Contents** (shapes verified against the live Python producer and canvas consumer):
- Server→client text frames: `RunTerminalReadyFrame` (`run.terminal.ready` with `run`,
  `terminal{cols,rows}`, `scrollback{replayedBytes,truncated}`),
  `RunTerminalScrollbackEndFrame` (`run.terminal.scrollback-end`),
  `RunErrorFrame` (`run.error` with `code`, `message`).
- Client→server text frame: `TerminalResizeFrame` (`resize` with `cols`, `rows`).
- Binary frames remain raw PTY bytes in both directions — explicitly outside the JSON
  contract, documented as such.
- Constants: `DEFAULT_TERMINAL_COLS=80`, `DEFAULT_TERMINAL_ROWS=24`,
  `MAX_TERMINAL_COLS=500`, `MAX_TERMINAL_ROWS=200` (identical today in
  `terminal_bridge.py`, `runtimeRouter.ts`, and `pty_session.py`).
- Parse + serialize pairs (`parse*Frame`/`serialize*Frame` or equivalent) built on the
  `primitives.ts` safe* family: never throw on wire input, return typed frame or
  `undefined`, enforce the dimension bounds where the Python `validated_dimension` does.

**Consumers migrated in 4a:** `runtimeRouter.ts` (stub ready/error frames +
`terminalSizeFromQuery` bounds), canvas `runTerminalFrames.ts::parseRunErrorFrame`
(delegate to the shared parser; keep the exported name if the call sites prefer it),
canvas `terminalSocket.ts::sendResize` (serialize via the contract). Canvas
`package.json` gains `"@tm/common": "workspace:*"` — the first browser→`packages/*`
edge (see Quality Map for why that is safe).

**Python:** `run_routes.py`/`terminal_bridge.py` keep their literals until 4e deletes
them. Cross-language conformance is the `docs/ARCHITECTURE.md` "single source cross
plane constants + conformance test" pattern; if wanted early, a Python test asserting
the frame literals against a small JSON fixture exported from `@tm/common` is cheap —
optional, 4e-adjacent.

**Validation approach — recommendation: safe* primitives, not zod.**
- zod is a dependency of nothing in this repo; introducing it creates a second
  validation vocabulary beside the safe* family that `packages/AGENTS.md` mandates
  reusing ("never re-derive a coercion or validation helper... duplication across
  packages is a defect"), and adds a runtime dep to the canvas browser bundle.
- The contract is four tiny frame shapes; safe*-based parsers are ~60 lines and match
  the proven `CaptureRpcClient` idiom.
- The spec's own wording is "plain-TS validation (**e.g.** `zod`)" — the locked part is
  "not Effect Schema", not "must be zod".
If the orchestrator wants zod anyway, it is a one-file swap inside `terminalContract.ts`
and does not change the plan shape.

## 6. node-pty native-module risk assessment (empirically verified on this machine)

**New dep confirmed:** node-pty appears nowhere in code or `pnpm-lock.yaml`.

**Pin: `node-pty@1.2.0-beta.14` exact (no caret), in the pnpm catalog.**

Evidence, all verified by real installs in the scratchpad today:
- **1.1.0 (npm `latest`, published 2025-12-22) is broken on macOS out of the box.** Its
  tarball ships full prebuilds, but packs `prebuilds/darwin-*/spawn-helper` **without
  the executable bit** (`-rw-r--r--`). Install succeeds (the prebuild check passes, so
  node-gyp never runs), `require` succeeds, and `pty.spawn` then fails with
  `posix_spawnp failed.`. `chmod +x spawn-helper` fixes it — proving the diagnosis —
  but the fix would need a repo postinstall hack that script-suppressed installs skip.
- **1.2.0-beta.14 (published 2026-06-26) works prebuilt with scripts disabled.** Ships
  `pty.node` for darwin-arm64/x64 + linux-arm64/x64 and ConPTY binaries
  (`conpty.node`, `conpty.dll`, `OpenConsole.exe`) plus winpty fallback for
  win32-arm64/x64, spawn-helper packed `+x`. Verified: `npm i --ignore-scripts` and
  `pnpm add --ignore-scripts` both give a working spawn/write/onData/onExit round-trip
  with no compile step (tested on Node 25; N-API via `node-addon-api`, loader checks
  `build/Release` → `prebuilds/{platform}-{arch}`).

**CI implications: none required.** Every JS job and the root `just js-install` recipe
run `pnpm install --frozen-lockfile --ignore-scripts`, and pnpm's
`onlyBuiltDependencies` allowlist (currently `electron`) stays untouched — beta.14
needs no install script at all. The product-plane job (ubuntu, linux-x64 prebuild) can
run real PTY spawn integration tests. No native toolchain enters CI.

**Electron implications: none in P1.** node-pty executes in the Runtime/Gateway
standalone Node process (`packages/gateway/src/main.ts`), which the desktop does not
even spawn today (desktop spawns the Python `_desktop-backend`). Even at the target,
the addon is N-API, so it is Electron-ABI independent — no `electron-rebuild`, no
`@electron/packager` change.

**Residual risks:** (i) it is a beta tag — mitigated by the exact pin, the adapter
integration test in CI, and this being the actively maintained line (1.1.0 stable is
the demonstrably broken alternative); (ii) no Windows CI job exists, so the ConPTY path
rests on prebuild presence until the teardown-matrix slice adds Windows coverage;
(iii) prebuilds cover x64/arm64 only — fine for our targets.

## 7. Plan (ordered, bound to the reuse map)

1. **Contract:** add `packages/common/src/terminalContract.ts` + colocated test
   (parse/serialize round-trips, bounds enforcement mirroring `validated_dimension`
   cases, unknown/malformed frame rejection). Export via the barrel.
2. **Consume in runtime stub:** `runtimeRouter.ts` ready/error frames and
   `terminalSizeFromQuery` bounds from the contract; delete its local constants.
3. **Consume in canvas:** `runTerminalFrames.ts` delegates to the shared parser;
   `terminalSocket.ts::sendResize` serializes via the contract; add the `@tm/common`
   workspace dep. Update `runTerminalFrames.test.ts` / `terminalSocket.test.ts` to
   import shared constants.
4. **Port:** add `PtyPort` to `packages/runtime/src/ports.ts` — `spawn({argv, env, cwd,
   cols, rows})` returning a session handle with `write(data)`, `resize(cols, rows)`,
   `kill(signal?)`, `onData`, `onExit({exitCode, signal})`, `pid`. Shape mirrors
   `CapturePort`'s plainness; section 4 is the semantic contract.
5. **Adapter:** `packages/runtime/src/adapters/NodePtyAdapter.ts` over node-pty
   (catalog-pinned `1.2.0-beta.14`, dep of `@tm/runtime` only). Unit tests with an
   injected fake pty module (CaptureRpcClient's `fetchImpl` idiom); one real
   integration test: spawn a plain shell, write an echo marker, assert onData carries
   it, resize, exit, assert single `onExit` with code, assert post-exit `write` does
   not throw.
6. **xterm round-trip:** extend the canvas `FakeTerm`/`FakeSocket` round-trip test to
   drive shared-contract frames end to end (resize serialize → parse on the runtime
   side; `run.error` mint on the runtime side → parse in canvas). A literal headless
   xterm in `packages/runtime` would need `@xterm/headless` (not in the catalog) and
   buys little before 4c serving exists — recommend the harness route.

**Gates (verbatim, per slice):** `just check` and `just test`. The canvas consumer step
is a cross-package structural change: run the full `pnpm --filter @tm/shell test`
suite, not targeted filters. CI needs zero workflow changes.

## 8. Open risks

- **Bytes vs strings at the node-pty boundary.** Python today is byte-faithful end to
  end (raw `os.read` bytes → WS binary). node-pty `onData` yields UTF-8 decoded
  strings. For xterm rendering this is lossless in practice, but the adapter must
  define its encoding boundary explicitly (encode `onData` strings to `Uint8Array`
  UTF-8 for the binary wire) and the parity suite in 4b should include a multibyte /
  split-sequence case. This is the sharpest semantic difference from
  `spawn_pty_process`, worth a decision-record line in the PR.
- **Group kill semantics** live above the adapter (section 4): `PtyPort` exposing
  `pid` + `kill` keeps 4c's grace-then-force implementable; do not let the adapter
  swallow that.
- **Beta pin governance** and **no Windows CI** (section 6).
- **First browser→packages/* import edge** — expected clean, but prove with the full
  shell suite + both product builds (`pnpm --filter @tm/canvas build`).

## 9. Recommended build order

Contract (1) → consumers (2, 3) → port (4) → adapter (5) → round-trip (6). Steps 4-5
are independent of 2-3 and can be built in parallel inside one branch; one PR for the
slice, gated once on `just check` + `just test`.
