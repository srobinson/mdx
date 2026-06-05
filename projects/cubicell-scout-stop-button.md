# Scout: STOP stays armed after transition card (state motion timeline)

Pin: origin/main motion/transport (worktree spike only differs in shape-shader; `git diff origin/main -- src/panels/motion src/transport src/evaluation/pieceAt.ts` empty).

## Trace

1. **STOP disabled** — `TransportRow` in `PieceMotionPanel.tsx`: `disabled={!timeAttached}` where `timeAttached = editor.transport.timeMs !== null`. Stop click → `createTransportScrubCommand(null)` → `setTransportTime(null)` detaches clock.

2. **Transition card click** — `PieceStateStrip` `onClick` → `onFocusGap(index)` → `PieceMotionPanel.focusSegment({ kind:"gap", index })`: `setFocus` + **deliberate scrub** `createTransportScrubCommand(segment.startMs)`. Intent (PR #91 `333c3980`): *"Land the playhead on the segment so Play previews it immediately."* Arms transport possession (timeMs set); not play, not loop by itself. Loop window also set via `setTransportLoopWindow(focusWindow)`.

3. **State card click** — `onSelectState`: if new id → `selectActiveState(id)` + `setFocus({ kind:"state" })`; if same id → inspector cube/state toggle only. **Never** scrubs `null`. Leaves `transport.timeMs` attached → STOP stays enabled, playhead parked at prior scrub.

4. **Cube selection blocked** — Armed `timeMs` → `resolveAttachedPieceSource` → stage `source.kind === "piece"` → `samplePieceAt` / `PieceFrame.interactive: false` (comment: *"Piece playback locks canvas interaction"*, B2 `b31bce72`). `EditorStudio`: `canvasInteractive = !previewing && staged.interactive`; `gateStageMutationHandlers` strips `onSelectionChange` etc. Intentional for any attached piece clock (play **or** parked scrub), not only `playing`.

5. **Dual highlight** — Separate axes, same root incompleteness: State tile `aria-selected={id === activeStateId}` (store); transition `aria-pressed={focus.kind==="gap"}` (motion focus). `focusSegment` does not clear `activeStateId`, so prior State + Transition both lit. State click fixes highlight (`setFocus state`) but not the clock.

## Minimal fix

Matches archaeology: arm-on-transition is intentional; lock-while-piece-staged is intentional; **state-card should exit preview mode** (Stuart) by detaching the clock the way Stop does.

| Option | Verdict |
|--------|---------|
| **(a)** state-card clears armed mode | **Yes** — one-liner in `onSelectState` / shared helper: `dispatch(createTransportScrubCommand(null))` (also clears loop window via existing focus→window effect when focus leaves gap). Symbols: `PieceMotionPanel` `onSelectState`, `focusSegment` (optional: only arm gap, not leave stale on state). |
| (b) lock only while `playing` | Fights `PieceFrame.interactive: false` contract; parked scrub would edit a non-authored staged scene. |
| (c) both | Overkill if (a) lands. |

**Recommend (a).** Optional polish: clear `activeStateId` highlight coupling or leave as dual-axis UI (out of STOP bug).
