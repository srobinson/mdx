---
title: PR#236 S4a review — second independent vote (fable)
date: 2026-07-07
pr: 236 (feat/pty-s4a)
reviewed_head: 0c971e2 (per brief)
delta_checked: 4aee094 (codex teardown fix landed mid-review; every finding below re-verified against it)
baseline: main @ f31bf03
verdict: issues — 1 Major, 8 Minor, 1 test note (all survive 4aee094; 2 further candidates already fixed by it)
---

# PR#236 review — fable vote

Method: 8-angle finder pass (line-by-line, removed-behavior, cross-file, parity vs
`pty_session.py`, reuse, simplification, efficiency/altitude, conventions) over
`git diff main...0c971e2`, verified recall-biased against first-hand evidence:
node-pty@1.2.0-beta.14 source (from my scout install), live CI, and `git show` at both
heads. Tree was dirty at review start (codex fix round in the same checkout); all reads
went through `git show`, no repo writes. The brief's teardown cluster (opus Major + 4
Minors) is excluded; overlaps are marked.

## Brief question 1 — is the contract truly single-sourced? YES (verified)

Every duplicate site from my scout catalogue is gone at the reviewed head:
`runtimeRouter.ts` serializes via `serializeRunErrorFrame`/`serializeRunTerminalReadyFrame`
and validates via `terminalSizeFromQueryValues`; canvas `terminalSocket.ts` uses
`serializeTerminalResizeFrame(terminalResizeFrame(...))` and the `DEFAULT_TERMINAL_*`
constants; `runTerminalFrames.ts` delegates to `parseRunErrorFrameText`. Repo-wide grep
at the rev finds no lingering frame literals outside typed serialize arguments, which
are discriminated-union `type` values that `docs/ARCHITECTURE.md`'s magic-string rule
explicitly leaves bare. The removed-behavior audit confirmed the router refactor is
semantically faithful (missing/empty/"0"/negative/non-integer/array query values, 1008
close codes, echo behavior, ready-frame shape all byte-identical). The one residual
constant dup (`MIN_TERMINAL_DIMENSION` in the adapter) was fixed by 4aee094.

## Brief question 3 preface — refuted CI alarm

One finder claimed the `--ignore-scripts` CI installs can never build node-pty, so
runtime+gateway tests would fail. **Refuted empirically**: the pinned 1.2.0-beta.14
ships `prebuilds/{platform}-{arch}/pty.node` inside the tarball and the loader falls
back to them with no build step (verified by scratchpad `pnpm add --ignore-scripts` +
real spawn during scouting), and PR#236's CI is green 7/7 including product-plane.

## Findings (ranked; all verified present at 4aee094)

### 1. MAJOR — adapter is not byte-faithful: PTY output is lossily re-encoded; `encoding: null` is available and unused
`packages/runtime/src/adapters/NodePtyAdapter.ts` (`NodePtyAdapter.spawn`,
`NodePtySession` data path). node-pty is spawned without `encoding: null`, so its
`onData` delivers strings node-pty already decoded as UTF-8 (invalid bytes replaced by
U+FFFD); the session then `TextEncoder.encode`s that string. The Python reference
(`pty_session.py` + `terminal_bridge.py::send_pty_output`) forwards master-fd bytes
verbatim to the WS binary frames. Failure: a child emitting non-UTF-8 output (binary
dump, sixel/image escapes, non-UTF-8 locale) reaches the viewer corrupted and
unrecoverable; the `PtySession.onData(Uint8Array)` contract implies a byte stream it
does not deliver. Input side symmetrical: `write(Uint8Array)` decodes then re-encodes
(4aee094's `{stream: true}` fixed split sequences, but invalid UTF-8 still becomes
U+FFFD). **Fix is directly available in the pinned version**: beta.14 typings declare
`encoding?: string | null` (null → Buffer data events) and `write(data: string |
Buffer)` — spawn with `encoding: null`, pass Buffers both ways, delete the
encoder/decoder pair entirely. Verified against `node-pty/typings/node-pty.d.ts` and
`lib/unixTerminal.js` in the installed 1.2.0-beta.14.

### 2. Minor — output emitted before the first `onData` subscriber is silently dropped
`NodePtyAdapter.ts::NodePtySession` constructor subscribes `process.onData` immediately
(node-pty's socket is flowing from construction via its internal `_forwardEvents`) and
fans out to an empty listener set; there is no buffer and no `pause()`. Python parity:
the kernel buffers PTY output until `add_reader` installs, so nothing is lost
regardless of consumer timing. A caller that awaits anything between `await spawn()`
and `session.onData(...)` loses the child's first output (shell banner, fast `echo`)
non-deterministically; the exit path got replay treatment, the data path did not, and
nothing documents the "subscribe synchronously" requirement. 4aee094 tightened this
further: `onData` after exit returns a no-op subscription, so a fast-exiting child's
output can be wholly unobservable. Fix: buffer chunks until the first subscriber (cap
it), or `pause()` until first subscribe, or document the synchronous-subscribe
contract on `PtyPort` and assert it in 4c.

### 3. Minor — hardcoded `name: "xterm-256color"` clobbers caller-provided TERM, breaking env replace semantics
`NodePtyAdapter.spawn` always passes `name: "xterm-256color"`. Verified in beta.14
`lib/unixTerminal.js`: `name = opt.name || env.TERM || DEFAULT_NAME; env.TERM = name;`
— `opt.name` wins and overwrites `env.TERM`. The documented contract (scout doc §4,
from `spawn_pty_process`) is REPLACE semantics: caller env used verbatim; only the
local-terminal driver adds TERM. When 4c ports `RunManager._start_run_terminal`, a
captured-run spawn spec whose env carries its own TERM (harness template, `TERM=dumb`
test env) is silently overridden. Fix: pass `name` from `input.env?.TERM ??
"xterm-256color"` (and note `cwd` defaulting to `process.cwd()` is also softer than
Python's required+validated cwd — fine for 4a, do not let 4c rely on it).

### 4. Minor — `isTerminalGoneError` is calibrated to errors node-pty never throws, and misses the ones it does
Verified against beta.14 source: on POSIX, write-after-death cannot reach the adapter's
catch — `Terminal._close()` replaces `write` with a no-op and fd errors surface on the
socket's `'error'` event, absorbed internally (EAGAIN/EIO). So the EIO/EBADF matching
guards a path that effectively cannot throw on unix. Meanwhile the throws that DO exist
are unmatched: Windows `windowsPtyAgent` throws `"Cannot resize a pty that has already
exited"` — no EIO/EBADF/"closed" in the message — so a resize racing exit delivery (the
`exitEvent === null` window) rethrows on ConPTY, where Python semantics say benign
no-op. And the `/\b(?:EIO|EBADF|closed)\b/i` word-match over-swallows: any genuine
error whose message contains "closed" is silently dropped from `write`/`resize` (and
now `dispose`'s kill path in 4aee094). Fix: match the actual node-pty failure modes
(the Windows already-exited messages) and drop the generic "closed" word-match; treat
the unix try/catch as belt-and-suspenders, not the safety mechanism.

### 5. Minor — node-pty rethrows unusual master-fd errors as process-crashing uncaught exceptions; adapter attaches no error listener
Beta.14 `unixTerminal.js` socket `'error'` handler: non-EAGAIN, non-EIO errors (e.g.
EBADF from an externally closed fd) hit `if (this.listeners('error').length < 2) throw
err;` — an uncaught throw from an event handler, crashing the Runtime server process.
Python's equivalent path logs and treats it as exit
(`terminal_bridge.py::bridge_websocket_to_pty` read error handling). The `IPty` typed
surface doesn't expose `on("error")`, but the Terminal instance is an EventEmitter
delegate at runtime. Options: attach a defensive error listener via the runtime
surface, or accept + document the risk for 4c and add it to the teardown matrix.
Rare-but-real; PLAUSIBLE.

### 6. Minor — `@tm/runtime` barrel eagerly loads the native module for router-only consumers
`packages/runtime/src/index.ts` re-exports `NodePtyAdapter`, whose module does
top-level `import * as nodePty from "node-pty"`; node-pty loads `pty.node` at module
scope (`unixTerminal.js` `loadNativeModule` at import). `@tm/gateway` (`app.ts`,
`main.ts`) and every router-only test now pull the native binary into their module
graph without touching a PTY. CI is green because prebuilds cover linux/darwin
x64+arm64 — but any consumer on a non-prebuilt platform (musl/Alpine containers, other
arches) fails at import before a line of gateway code runs. Fix: lazy `await
import("node-pty")` inside `spawn()` (the injectable `nodePtyModule` seam already
exists, so the change is contained and the single-barrel rule stays intact).

### 7. Minor — consolidated parser silently narrows `run.error` acceptance: empty `code` now drops the banner
Old `runTerminalFrames.ts::parseRunErrorFrame` accepted `typeof code === "string"`
(empty string included); the shared `parseRunErrorFrameText` uses `nonEmptyString`, so
`{"type":"run.error","code":""}` now parses to nothing and `CapturedRunPane` shows no
failure banner (silent fallback to progress/closed state). Low severity — the backend
only emits non-empty codes today — but it is an untested, undocumented narrowing on an
error-surfacing path. Fix: bless non-empty-code as the contract with a test in
`terminalContract.test.ts`, or preserve the old acceptance.

### 8. Minor — `runTerminalFrames.ts` is now a two-line shim with a duplicate test suite
Its whole substance is `parseRunErrorFrameText(text) ?? null`; the sole consumer is
`CapturedRunPane.tsx`, and `runTerminalFrames.test.ts` re-tests parse behavior owned by
`terminalContract.test.ts`. Delete the shim, import from `@tm/common` at the call site
(it already null-checks), and drop the redundant tests — otherwise the file becomes a
magnet that re-fragments the contract this PR just consolidated.

### 9. Minor (test) — ready-frame routing assertion lost in the rewrite
The old `terminalSocket.test.ts` asserted a `run.terminal.ready` text frame routes to
`onTextFrame` with `term.written` staying empty; the rewritten test exercises that path
only with `run.error`. A future router regression that writes ready-frame JSON into the
xterm buffer would pass CI. Restore one ready-frame case.

### 10. Note — late-`onExit` replay dispose is uncancellable (overlaps the teardown cluster; re-verify post-round)
`onExit` on an exited session queues `queueMicrotask(() => handler(event))` and returns
`{ dispose: () => undefined }` — a subscriber that disposes before the microtask runs
still gets called against torn-down state. 4aee094 added `disposed` guards elsewhere
but left this path. Listed as a note, not counted, since it sits in the codex round's
neighborhood; verify it is covered there.

## Already fixed by 4aee094 (found independently, no action)
- `MIN_TERMINAL_DIMENSION` duplicated in the adapter → now exported from
  `terminalContract` and imported.
- `write(Uint8Array)` non-streaming decode splitting multibyte sequences → now
  `decode(data, { stream: true })` (residual invalid-UTF-8 case folded into finding 1).

## Refuted candidates (for the record)
- "CI cannot build node-pty under `--ignore-scripts`" → prebuilds ship in-tarball;
  loader uses them; CI 7/7 green on this PR.
- serialize wrappers / consumer-less `parseRunTerminalServerTextFrame` as dead code →
  deliberate contract surface for 4c per the locked slice plan.
- `NodePtyExitEvent` vs `PtyExitEvent` duplication → deliberate external-module seam
  typing for the injectable fake.
- Router query-parsing regressions → audited case-by-case, faithful.
- `@tm/common` domain-knowledge charter tension → spec-directed home (locked in the
  scout round); noted, not charged.

## Process note
The working tree was dirty at review start (codex applying the fix round in the same
checkout) — brief required pristine; review proceeded entirely via `git show` at
0c971e2, then delta-verified against the committed 4aee094. Tree is clean at 4aee094
now. Recommend future concurrent rounds use a separate worktree.
