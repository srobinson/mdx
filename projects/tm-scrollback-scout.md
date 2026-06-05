# TM canvas terminal scrollback corruption — scout

Read-only scout on `ml/channels-hardening` at `d986dcde`; `git status --porcelain` was empty before and after the read pass. No runs launched, no panes spawned, no Postgres or channel home touched.

Symptom under investigation: later output spliced over earlier scrollback rows in a canvas terminal pane, progressively eating scrollback, reproduced by the owner at three different pane widths.

## Architecture actually found (differs from the brief's mental model)

There is no raw byte ring. The server (`packages/runtime`) keeps one headless xterm per run and replays attach state by serializing it:

- `RunManager.register` wires `session.onData` into two sinks: `TerminalEmulator.append` (a headless `@xterm/headless` terminal plus `@xterm/addon-serialize`) and `TerminalFanout.append` (per-attachment item queues for live streaming).
- Attach (`RunManager.attach`) returns `emulator.snapshot()` — the SerializeAddon escape-stream reconstruction of the whole buffer — plus a live `TerminalFanout` attachment.
- The wire (`runTerminalConnection.handleRunTerminalConnection`) sends, in order: a `run.terminal.ready` frame carrying the **snapshot's** cols/rows, the snapshot bytes, a `run.terminal.scrollback-end` frame, then live chunks and resize echo frames via `attachmentPump.pumpAttachment`.
- The client (`www/packages/canvas` `terminalSession.useTerminalSession`) resizes its xterm to the snapshot geometry on `ready`, writes the snapshot, and only after `scrollback-end` proposes its own pane size via `sendResize`; geometry changes are applied locally only when the server echoes `run.terminal.resize`, after draining the write queue.

## The five questions

### 1. What the "ring" stores and its bound

Retained state is a headless xterm bounded by **rows**: `TerminalEmulator` with `scrollback: DEFAULT_TERMINAL_SCROLLBACK_LINES` (10,000, `packages/common/src/terminalContract.ts`), identical to the client's xterm `scrollback` in `useTerminalSession`. At the boundary xterm drops oldest rows and the emulator sets a `truncated` flag (`TerminalEmulator.append`). The only byte-shaped buffer is the per-attachment `TerminalQueue` (256 **items**, whole PTY chunks); overflow closes the whole viewer (`TerminalFanout.broadcast` → `SLOW_VIEWER_CLOSE_CODE`), it never drops or truncates individual bytes. **Mid-escape-sequence truncation is ruled out**: nothing in the path can cut a chunk.

### 2. Is the column count known to the writer, and applied before or after replay?

Known: the emulator is created and resized in lockstep with the PTY (`RunManager.register`, `RunManager.resizeRun` — emulator, fanout echo, and `session.resize` together). Applied before replay: the client resizes to the snapshot's geometry on the `ready` frame before writing snapshot bytes (`terminalSession.applyCapturedRunFrame`).

**But the run's geometry is never the pane's at spawn.** `createCapturedRunView` (`www/packages/core/src/transport.ts`) sends no `terminal` field; `runtimeRouter.terminalSizeFromBody` then defaults every canvas run to **80×24**, clamped by `RunManager.managedTerminalSize`. The attach query's cols/rows (`runTerminalSocketUrl` sends the pane's fit size) are stored as attachment metadata only — `RunManager.attach` never resizes the run. So the pane's real size is applied only **after** replay: `scrollback-end` → client `sendResize` → server `resizeRun` → echo → client `term.resize`. Every attach whose pane is not exactly 80×24 therefore performs: replay a serialized buffer at width A, then immediately reflow that deserialized buffer to width B.

### 3. Do live and replay paths differ?

Yes, precisely here. Live output is raw PTY bytes applied at matched geometry on both sides, in matched order (fanout queue push order equals emulator write-queue order; the resize echo is ordered within the same queues; the client drains xterm's write queue before applying an echoed resize). The chunk-vs-snapshot boundary is race-free: `fanout.attach` and the snapshot's queue-boundary capture happen in the same synchronous stretch of `RunManager.attach`, so a chunk is either inside the serialized snapshot or delivered after `scrollback-end`, never both.

Replay differs in kind, not just timing: the client's buffer after replay is SerializeAddon's *reconstruction*, not the buffer itself. The addon rebuilds wrapped-line structure heuristically (`SerializeAddon` row-separator logic: natural overflow when its `isValid` checks pass, otherwise a forced-wrap trick of padding dashes plus `ECH`/cursor fixups). It is documented-by-design faithful only at the geometry that produced it. Immediately after replay, both sides reflow to the pane size — the server reflows the **original** buffer with true wrap metadata, the client reflows the **reconstruction**. xterm's resize reflow (rewrap plus cursor adjustment) is only guaranteed to agree if the two buffers are cell-identical, including wrap flags and null-cell tails; Claude's box-drawing, background-colored TUI rows are exactly the rows the addon's heuristics wrestle with.

### 4. Is resize propagated to the PTY, and does it invalidate buffered content?

Propagated: `resizeRun` → `session.resize` (node-pty, TIOCSWINSZ). Buffered content is not invalidated; both terminals reflow. Output produced at the old width but read after the resize is applied at the new width on **both** sides equally — a transient, self-healing artifact identical to any real terminal.

### 5. Does anything write cursor/clear sequences on attach?

No. Attach writes only the ready frame (JSON), snapshot bytes, scrollback-end (JSON). The serialized snapshot itself ends with cursor-restore movements (SerializeAddon tracks and re-establishes the final cursor position) — that is part of the state, applied at matching geometry. OSC 10/11 color queries from the harness are answered by the server emulator into the PTY (`TerminalEmulator` OSC handlers → `onResponse` → input queue) and deliberately swallowed client-side (`useTerminalSession` registers OSC 10/11 no-op handlers for captured runs). Nothing clears or repositions on top of replayed rows.

## Single most likely cause

**Post-replay reflow divergence.** Every canvas run spawns at 80×24 because the spawn body omits geometry, so every attach at any other pane size replays the serialized buffer at the server's width and then immediately reflows that deserialized reconstruction to the pane's width, while the server reflows its original buffer. Any divergence in reconstructed wrap metadata or the reflowed cursor row leaves the client's row grid and viewport-relative cursor offset from the server's. Claude Code repaints its UI with *relative* sequences (cursor-up N, erase, redraw); once the client cursor row disagrees with the PTY's, every subsequent repaint block lands N rows off on the client, overwriting rows that have scrolled above — later output spliced over earlier scrollback, compounding with each repaint.

Width dependence falls out directly: how many lines rewrap, and by how much the cursor shifts, is a function of (server width A, pane width B), so three pane widths produce three distinct splice patterns. It also explains "progressive": each repaint cycle after divergence eats another band.

### Evidence supporting

- `createCapturedRunView` (core `transport.ts`) sends no `terminal`; `runtimeRouter.terminalSizeFromBody` defaults to 80×24 — the risky replay-then-reflow happens on **every** attach of a non-default-size pane, matching "always reproducible".
- `RunManager.attach` ignores the viewer's requested cols/rows for the run itself; geometry sync happens only after `scrollback-end` (`terminalSession`), i.e. after replay.
- SerializeAddon's own source treats wrap reconstruction as heuristic (`isValid` gating, forced-wrap padding with `ECH` cleanup); its stated contract is same-geometry restore.
- Every simpler candidate examined is clean: no byte truncation (Q1), ordered chunk/snapshot boundary (Q3), ordered resize echo with client-side drain, TIOCSWINSZ propagated (Q4), no attach-time clears (Q5).
- No test in `packages/runtime` or `www/packages/canvas` covers replay-into-client-then-resize equivalence (`TerminalEmulator.test.ts` covers serialize-at-current-geometry only).

### Evidence that would falsify

- **Server-side check during a live corruption**: `RunManager.terminalTextSnapshot` (or a fresh reload at the pane's current width, comparing first paint). If the spliced rows are already present in the **server** emulator's buffer, the corruption happened upstream of the client (Claude's own SIGWINCH repaint artifacts recorded faithfully — visible in any terminal) and the reflow-divergence hypothesis is wrong.
- **Unit-level equivalence harness, no live repro needed**: feed an identical Claude-style stream (draw rows, cursor-up-N, erase, redraw; then more output) into (a) a headless xterm resized mid-stream and (b) a serialize→fresh-terminal→replay→resize pipeline at the same sizes, then diff `translateToString` over both buffers. Divergence confirms the mechanism; equality across representative streams falsifies it and points back at the server buffer.

### Smallest change that would fix it

Make replay happen at final geometry instead of reflowing a reconstruction: in `RunManager.attach`, apply the viewer's requested cols/rows via the existing `resizeRun` **before** taking `emulator.snapshot()` (the requested size already arrives in `handleRunTerminalConnection` and is currently dropped). Then the server reflows its true buffer, serializes at the pane's size, and the client replays at that size with no post-replay reflow. Complementarily (one line each side), pass the pane's initial size in the spawn body (`createCapturedRunView` `terminal: {cols, rows}`) so the run never lives at 80×24 at all. Residual risk — mid-attachment user resizes still reflow the deserialized buffer — remains, but the always-on attach-time occurrence disappears; if the harness above shows reflow divergence is unavoidable, the follow-on fix is re-snapshotting on resize instead of echo-and-reflow.

## 2026-07-29 follow-up: harness verdict — reflow theory REFUTED, replay state-loss CONFIRMED

The unit harness named above was built and run (`packages/runtime/src/service/ReflowDivergence.scratch.test.ts` on `ml/terminal-size`, uncommitted). Result:

**Refuted:** serialize → replay → resize is equivalence-preserving against resize-mid-stream for every geometry case tried: widen, narrow, the owner's three-width shape with a replay between each, cursor mid-wrapped-line, replay of already-reflowed scrollback, trimmed-at-cap scrollback, wide chars, BCE/background rows, exact-width wraps, and autowrap-off (SerializeAddon does persist DECAWM). Buffer rows and cursor identical in all cases. The geometry fix (spawn dims + attach-resize-before-snapshot) would therefore NOT fix the corruption.

**Confirmed instead:** SerializeAddon cannot capture the DECSC/DECRC saved-cursor slot (xterm core does not expose it). A `ESC 7` before the snapshot boundary plus `ESC 8` after it restores the true terminal to the saved position but the replayed client to home; the very next output writes over an earlier viewport-top row — exactly "later output spliced over earlier scrollback rows". Harness case "saved cursor (DECSC) across replay" fails with: truth cursor y=23, client cursor y=0, client MARKER overwrote absolute row 13.

Claude Code plausibly emits these: its bundle (`~/.local/share/claude/versions/2.1.220`) contains `cursorSavePosition`/`cursorRestorePosition` (ansi-escapes) ×3, `eraseLines` ×5, and Ink (`ink-box` ×12). Every re-attach (reload, restore-from-dock) crosses the snapshot boundary and drops the saved-cursor state; each post-attach `ESC 8` then anchors Claude's relative repaints wrong. Width shapes the damage pattern (what content sits where), not the trigger — consistent with the three-width screenshots but the width clue pointed at the wrong mechanism.

**Smallest fix implied (not built, per the stop instruction):** shadow the saved-cursor state in `TerminalEmulator` via parser handlers for `ESC 7`/`ESC 8` (observe, return false so xterm still processes), and append a reconstruction suffix to `snapshot()`: position to saved point, `ESC 7`, position back to the true cursor. Contained to `TerminalEmulator`; no ring redesign, no reconciliation layer. Distinguishing check if wanted before building: capture PTY bytes of a live corrupting session and confirm `ESC 7`/`ESC 8` spanning an attach.

## Notes

- `managedTerminalSize` clamps to minimum 80×24; a pane smaller than that renders an 80×24 xterm clipped by the pane DOM. Visually confusable with corruption but not splicing; worth keeping distinct when reading the screenshots.
- Multi-viewer attach: last resize wins for the PTY; other viewers mirror a size their DOM doesn't match. Consistent, not corrupting, but the same replay-then-reflow risk applies to each viewer independently.
