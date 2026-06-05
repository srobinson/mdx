# PR#236 review — t3code P1 slice 4a (PTY adapter + terminal wire contract)

- **Branch:** `feat/pty-s4a` · **Head:** `0c971e2` (tree pristine at review time)
- **Baseline:** `main` (`f31bf03`) · **Diff:** `git diff main...HEAD` (17 files, +968/-77)
- **Reviewer:** `transport-matters:general:5:2.2` · adversarial pass, xhigh effort
- **Verdict:** `issue` — **1 Major, 4 Minor**. No Blocker. The slice's headline objective (single-sourcing the terminal wire contract) is **fully met**; findings cluster in `NodePtySession` teardown/guard semantics.

Node-pty behaviour cited below was verified against the installed `node-pty@1.2.0-beta.14`
(`node_modules/.../node-pty/lib/unixTerminal.js`), not from memory.

---

## Findings

### Major

**M1 — `NodePtySession` has no teardown; `dataListeners` and the node-pty subscriptions are never released on exit.**
`packages/runtime/src/adapters/NodePtyAdapter.ts:160` (`emitExit`), constructor `:113`/`:117`, field `:103`; contract gap at `packages/runtime/src/ports.ts:87` (`PtySession` has no `dispose`).

- `emitExit` clears `exitListeners` (`:164`) but leaves `dataListeners` populated, and the `NodePtyDisposable`s returned by `process.onData(...)`/`process.onExit(...)` in the constructor are discarded (never stored, never disposed). `PtySession` exposes no `dispose()`/teardown at all.
- The constructor's `onData` arrow captures `this`, so the session ↔ IPty ↔ closure form a retained set. GC reclaims it **only if nothing holds the session after exit**. The reference contract (`pty_session.py::terminate_terminal_pty` / `close_terminal_master`) explicitly kills the group and closes the master fd on teardown.
- **Impact:** latent today (4a has no post-exit retainer), but the brief's focus #1 makes "the pty is disposed on exit; no dangling listeners/handles" an acceptance criterion for *this* slice, and it fails. It will bite in 4b the moment `RunManager` keeps a session past exit for status/scrollback/attach: every `onData` handler (and whatever it closes over, e.g. a scrollback buffer) plus the live `IPty` stays reachable with no API to free it. The clear-`exitListeners`-but-not-`dataListeners` asymmetry is an oversight regardless of the dispose-API question.
- **Fix:** clear `dataListeners` in `emitExit`, capture and dispose the two constructor subscriptions on exit, and add a `dispose()` (or make `kill()` release listeners) to `PtySession` so a retaining owner can free the handle.

### Minor

**m2 — `resize()` does not bounds-check its arguments; a non-positive value throws an uncaught raw node-pty error.**
`packages/runtime/src/adapters/NodePtyAdapter.ts:130-138` (`:133` calls `this.process.resize`).

- `spawn` validates dimensions via `terminalDimension` (`:51-52`), but `resize` forwards `cols`/`rows` straight to node-pty. Verified: `UnixTerminal.resize` throws `Error('resizing must be done using positive cols and rows')` for `cols<=0 || rows<=0 || isNaN || Infinity`. `isTerminalGoneError` matches only `EIO`/`EBADF`/`closed`, so that error is **not** swallowed — it propagates uncaught, and it is not wrapped as `NodePtyAdapterError` the way spawn errors are.
- **Impact:** reachable via the public `PtySession.resize` (e.g. a collapsed 0-width pane emitting `resize(0, n)`). The current wire path is guarded upstream — `terminalSizeFromQueryValues` / `parseTerminalResizeFrameText` reject `<1` — so this is a robustness/consistency gap, not a live crash on the 4a runtime path. **Fix:** clamp/validate in `resize` the same way `spawn` does (reuse `terminalDimension`).

**m3 — `write(Uint8Array)` corrupts non-UTF-8 and split-multibyte bytes.**
`packages/runtime/src/adapters/NodePtyAdapter.ts:123`.

- `this.decoder.decode(data)` runs a stateless (`stream:false`) `TextDecoder`, then node-pty re-encodes the string to UTF-8. Invalid bytes become U+FFFD and a multibyte sequence split across two `write` calls is flushed as U+FFFD. The reference `pty_session.py::write_all` writes raw bytes byte-accurately.
- **Impact:** low — terminal input is ~always whole-message UTF-8 (xterm `onData` is a string; the WS binary frame is one `TextEncoder` output), so split-multibyte is unlikely on the real path, but a single-frame non-UTF-8 paste (e.g. `0xFF`) is silently mangled. Partly inherent to node-pty's string-only `write`. **Fix:** at minimum use a persistent streaming decoder (`{stream:true}`) so split-multibyte survives, or constrain `PtySession.write` to `string` so the byte-fidelity promise is not made.

**m4 — the pre-exit `EIO`/`EBADF` race branch in `write`/`resize` is never exercised by a test.**
`packages/runtime/src/adapters/NodePtyAdapter.test.ts:484-499` ("emits exit exactly once…"), guards under test at adapter `:124-127` / `:135-137`.

- The test sets `process.writeError` **after** `emitExit` has set `exitEvent`, so `session.write("late")` returns at the `exitEvent !== null` guard (`:121`) and never enters the `try`. The `isTerminalGoneError(error)` catch — the exact race the code exists to handle (pty gone, `write`/`resize` throws before `onExit` lands) — is untested for both methods.
- **Impact:** a regression changing `:126`/`:136` back to `throw error` passes the whole suite green while production would throw an uncaught `EIO` during the exit race. **Fix:** add a case where the fake throws `{ code: "EIO" }` while `exitEvent` is still `null` and assert `write`/`resize` swallow it.

**m5 — `MIN_TERMINAL_DIMENSION` is duplicated across the package boundary; the adapter re-implements the contract's bounds check.**
`packages/runtime/src/adapters/NodePtyAdapter.ts:10` duplicates `packages/common/src/terminalContract.ts:14`; `terminalDimension` (`NodePtyAdapter.ts:174-181`) re-derives the `[MIN, max]` check that `dimensionFromJsonValue`/`dimensionFromQueryValue` own.

- The PR correctly single-sources `DEFAULT_/MAX_TERMINAL_COLS/ROWS` from `@tm/common`, but `MIN_TERMINAL_DIMENSION = 1` is re-declared privately in both files because the contract never exports it. Per `packages/AGENTS.md` ("@tm/common is the single home… Duplication across packages is a defect").
- **Impact:** low (trivial literal), but if the shared floor ever changes the adapter's bound drifts from the wire contract's. **Fix:** export `MIN_TERMINAL_DIMENSION` from `@tm/common` and import it in the adapter.

---

## Verified clean (no findings)

- **Single-source (focus #2) — complete.** `terminalContract.ts` is the sole definer of every frame shape (`TerminalResizeFrame`, `RunTerminalReadyFrame`, `RunTerminalScrollbackEndFrame`, `RunErrorFrame`, `RunTerminalServerTextFrame`, `TerminalSize`, `RunTerminalScrollback`). The old local `RunErrorFrame` in `runTerminalFrames.ts` is gone (now a re-export from `@tm/common`, consumed by `CapturedRunPane.tsx`). `runtimeRouter.ts` dropped its `DEFAULT_/MAX_TERMINAL_*` consts and inline `JSON.stringify` frames for the `serialize*` helpers; `terminalSocket.ts` builds resize frames via `serializeTerminalResizeFrame(terminalResizeFrame(...))`. `git grep` confirms **no** remaining local frame type/interface, **no** stray frame `JSON.parse`, and **no** leftover `80/24/500/200` dimension literals in the TS tree. (Python `pty_session.py` constants are a separate process boundary, not a duplicate.)
- **Placement / shape (focus #3) — correct.** `PtyPort` sits in `ports.ts` beside `CapturePort`; `NodePtyAdapter` sits in `adapters/` mirroring `CaptureRpcClient`; boundary validation uses `@tm/common` `safe*` (`safeRecord`/`safeInteger`/`safeIntegerString`/`safeBoolean`/`nonEmptyString`); no zod. The only `JSON.parse` is wrapped in `recordFromJson`'s try/catch, so malformed wire input returns `undefined` rather than throwing.
- **Boundary parity (focus #4).** `terminalSizeFromQueryValues`/`dimensionFromQueryValue` reproduce the deleted `terminalSizeFromQuery`/`boundedIntegerFromQueryValue` exactly: absent/empty → default; non-integer string → reject; `<1`/`>max` → reject; the null-vs-undefined (absent-vs-malformed) distinction is preserved.
- **Contract spawn/write/resize/onData/onExit vs `pty_session.py`.** spawn passes command/args/env/cwd/cols/rows; argv-empty and out-of-bounds dims are rejected *before* the spawn `try` (no error mislabeling as `pty_spawn_failed`); exit is emitted exactly once (idempotent `exitEvent` guard) with a single `queueMicrotask` replay for late `onExit` subscribers.
- **Tests genuine (focus #4).** `terminalContract.test.ts` asserts real malformed/out-of-bounds rejection (`"not json"`, bare `"42"`, string-typed cols, `MAX+1`, `"0"`, `rows:0`, `replayedBytes:-1`, empty `code`), not just happy paths. `NodePtyAdapter.test.ts` spawns a **real** `/bin/sh` and round-trips write→data→resize→exit; the `shellSpec()` platform branch **runs on the host** (it is not an `it.skip` masquerading as green). Windows ConPTY is auto-selected by node-pty by default and is exercised by the win32 branch on the desktop CI job.
- **kill() race — REFUTED.** node-pty's `UnixTerminal.kill` already wraps `process.kill` in `try { } catch { /* swallow */ }`, so the adapter's unguarded `kill()` cannot throw on a dead pid. Not a defect.

---

## Method note
10-angle xhigh methodology, scoped to the brief: line-by-line + two independent adversarial finder agents (adapter correctness/leak; single-source/test-genuineness), candidates verified against source and the installed node-pty, node-pty-dependent claims (resize throw, kill swallow) confirmed against `node_modules`. No repo writes; `git rev-parse HEAD` == `0c971e2`, working tree clean throughout.
