# PR #340 review — `ml/terminal-size` (DECSC saved-cursor replay, clamp removal, truncation note)

Read-only review. Base `main`, head `ml/terminal-size` @ `a3cf4fb8`, +401/-28 across 8 files, 9/9 CI green (`[code]smith` skipped).
Working tree pristine at review start and at write time (`git status --porcelain` empty both times).
No edits, no commits, no repo writes. Evidence gathered from the repo's own installed
`@xterm/headless@6.0.0` + `@xterm/addon-serialize@0.14.0` in a scratchpad harness that replicates
`TerminalEmulator`'s shadow logic verbatim; no captured runs, no Postgres, no keychain, no channel homes touched.

**Counts: 1 blocker / 4 major / 6 minor.**

Verdict on the highest-risk change: **the clamp removal is safe** as a wire/robustness matter. Every path into
`RunManager.resizeRun` is bounded `1..MAX` before it arrives (`runtimeRouter.terminalSizeFromBody` for create,
`terminalContract.terminalSizeFromQueryValues` for attach, `terminalContract.terminalSizeFromJsonValues` via
`parseTerminalResizeFrameText` for the live resize frame, and `NodePtyAdapter.terminalDimension` as the last gate,
which throws rather than coerces). Zero, negative, non-integer and absurd values never reach the PTY. It has one real
behavioural cost, finding 5 below.

---

## 1. BLOCKER — the truncation note is painted *over* live terminal rows, hiding output no scrolling can reach

`www/packages/canvas/src/viewers/terminal/terminal-pane.css`, rule `.terminal-pane__truncation`;
`www/packages/canvas/src/viewers/terminal/CapturedRunPane.tsx`, `AttachedRunTerminal`.

The note is `position: absolute; inset: var(--pane-padding) var(--pane-padding) auto; z-index: 1;` with an opaque
`background: var(--color-surface)`. `.terminal-pane` is `position: relative` with `padding: var(--pane-padding)`, so an
absolutely positioned child offset by one padding unit from the padding-box top lands exactly flush with the top of
`.terminal-pane__surface`. The note is a sibling of the surface, not a flex item, so it consumes no layout height and
`FitAddon.proposeDimensions()` still measures the full surface. xterm therefore keeps rendering rows underneath the
opaque box.

**Failure scenario.** A run overflows the 10,000-line cap. The pane reattaches, `run.terminal.ready` carries
`scrollback.truncated: true`, the note renders. From that moment the top ~2 rows of the *live* viewport are covered by
an opaque strip for the rest of the session. Scrolling does not help: xterm scrolls content through the viewport, and
the viewport's top is always under the note. The user loses the first two rows of every Ink repaint frame.

This is the same defect commit 2 removes the `managedTerminalSize` floor to fix ("a grid larger than the pane would put
viewport rows behind the pane's DOM edge where no scrolling reaches them"), reintroduced by commit 3 in miniature. The
existing `.terminal-pane__status` precedent does not cover it: that banner sits at the *bottom* and appears when the
terminal is dead or still loading, while this one sits at the top over a live, scrolling terminal.

The fix is layout, not overlay: make the note a flex row above `.terminal-pane__surface` so the surface (and the fit
computation) shrinks by its height.

## 2. MAJOR — truncation is reported only at attach, so a run that overflows while you are watching stays silent

`packages/runtime/src/server/runTerminalConnection.ts`, `handleRunTerminalConnection`;
`www/packages/canvas/src/viewers/terminal/CapturedRunPane.tsx`, `AttachedRunTerminal.onTextFrame`.

`snapshot.truncated` is carried only on the one-shot `run.terminal.ready` frame, and the pane sets
`scrollbackTruncated` only from that frame. `TerminalEmulator.append` keeps updating `this.truncated`, but nothing
pushes the change to an already-attached viewer.

**Failure scenario.** Spawn a Claude pane and leave it open. The run emits more than 10,000 lines during the session.
The server's emulator has discarded the head, the client's own xterm (`scrollback: DEFAULT_TERMINAL_SCROLLBACK_LINES`)
has discarded it too, and the pane shows no note for as long as the pane stays attached. The note appears only after a
reload or a dock restore. Commit 3's stated ruling ("stop hiding truncation") is met across a reattach and not during
the session where the loss actually happens.

## 3. MAJOR — the shadow tracks only `ESC 7`; three other writers of xterm's saved-cursor slot leave it stale, and a stale shadow injects a *wrong* saved cursor

`packages/runtime/src/service/TerminalEmulator.ts`, constructor `registerEscHandler({ final: "7" })` and
`savedCursorRestoration`.

In `@xterm/headless@6.0.0` the saved-cursor slot (`buffer.savedX` / `buffer.savedY`) is written by four paths, all
routed to `InputHandler.saveCursor`: `ESC 7`, `CSI s`, `CSI ?1048h`, and `CSI ?1049h` (which saves *then* switches to
the alternate buffer). It is cleared by RIS (`ESC c`), which rebuilds the buffers with `savedX = savedY = 0`. The
shadow observes only the first. Because `savedCursorRestoration()` emits an unconditional `ESC 7` whenever the shadow
is non-null, a stale shadow does not merely fail to help: it manufactures a saved cursor the truth terminal does not
have, at a row the truth terminal never saved.

Reproduced against the installed xterm with the shadow logic copied verbatim (truth = one terminal fed the raw stream;
client = fresh terminal fed `serialize() + suffix`, then both fed the post-boundary bytes):

| scenario | pre-boundary | post-boundary | result |
|---|---|---|---|
| PR's own case | `…ESC 7 ESC[5;10H` | `ESC 8 MARKER` | cursor and rows **match** (the fix works for its target) |
| SCOSC/SCORC | `…ESC[s ESC[5;10H` | `ESC[u MARKER` | client y=0 vs truth y=12; `MARKER` splices over row 0 |
| stale shadow | `…ESC 7 …ESC[s ESC[3;3H` | `ESC 8 MARKER` | client y=12 vs truth y=14; `MARKER` lands on the wrong content row |
| RIS after save | `…ESC 7 ESC c …` | `ESC 8 MARKER` | truth restores home (slot cleared), client restores stale row 12 |
| alt buffer after save | `…ESC 7 ESC[?1049h alt content` | `ESC 8 MARKER` | client writes into the alt row: `" alt content"` becomes `"MARKERontent"` |

The `CSI s` and RIS rows are the load-bearing ones: there the PR's mechanism makes replay *worse* than the pre-PR
behaviour, which was a restore to home. The alt-buffer row matters for `codex`, a supported harness on this same
`TerminalEmulator` whose ratatui TUI lives on the alternate screen; note also that the shadow is a single field while
xterm keeps the slot **per buffer**, so a normal-buffer save is replayed into the alternate buffer's slot.

Claude Code on macOS emits `ESC 7` (ansi-escapes uses `CSI s` only on Windows), so today's stable-channel path is the
row that passes. This is a contract gap in a generic component, not a live user break.

Smallest correct shape: register the same handler on `CSI s`, `CSI ?1048h`, `CSI ?1049h`, invalidate on RIS/DECSTR and
on buffer switch, and key the shadow by active buffer.

## 4. MAJOR — the reconstruction restores position only; DECRC also restores SGR and the charset

`packages/runtime/src/service/TerminalEmulator.ts`, `savedCursorRestoration`.

`InputHandler.saveCursor` stores `savedCurAttrData` and `savedCharset` alongside the coordinates, and
`restoreCursor` puts both back. The suffix is `CUP; ESC 7; CUP`, so the `ESC 7` executed on the replaying client
captures whatever SGR state `serialize()` left active at the end of the snapshot, not the SGR state that was live at
the original save.

**Failure scenario, reproduced.** Stream `ESC[31m ESC 7 ESC[0m` then more output, snapshot, replay, then `ESC 8` +
`COLORED`. Truth renders `COLORED` with `fg = palette 1` (red); the replayed client renders it with the default
foreground (`isFgDefault() === true`). Any harness that saves the cursor inside a colored region and restores after the
attach boundary repaints in the wrong colors. The `savedCursorRestoration` doc comment discloses the pending-wrap gap
but not this one.

## 5. MAJOR — removing the floor shrinks the control plane's only view of a blocked run, for alternate-screen harnesses

`packages/runtime/src/service/TerminalEmulator.ts`, `textSnapshot` / `renderedText`;
`packages/runtime/src/server/runtimeRouter.ts`, `/runs/:runId/terminal-snapshot`;
`api/src/transport_matters/controlplane/delivery_wait.py`, `_result`.

The deleted `managedTerminalSize` comment named this consumer explicitly ("Claude renders question options from the PTY
geometry"). On a `needs_you` delivery the control plane calls `read_terminal_snapshot` and returns it as `pane` — the
only thing an MCP caller has to see what the run is asking. `renderedText` walks `buffer.active`, and the alternate
buffer has **no scrollback**: `buffer.active.length === rows`, verified at rows=24 → 24 and rows=8 → 8 after writing 60
lines behind `ESC[?1049h`.

**Failure scenario.** A `codex` run sits in a canvas pane sized to 8 rows and blocks on a question. An agent calls the
control plane's wait-for-reply; `pane` now carries 8 rows instead of the 24 the floor used to guarantee, and the
question's options are simply not in the payload. Nothing in the diff replaces the guarantee and no test exercises the
control-plane read at a sub-floor geometry.

For the normal buffer (Claude) the loss is bounded — `renderedText` reads the full scrollback and only the 32,000-char
tail cap applies — so this is a codex/alt-screen exposure, not a Claude one. Flagging it as the unpriced half of the
owner's ruling: the ruling was about the canvas viewport, and it silently repriced a control-plane contract.

## 6. MINOR — `truncated` flips one line before anything is actually lost

`packages/runtime/src/service/TerminalEmulator.ts`, `append`:
`this.truncated ||= this.terminal.buffer.normal.baseY >= this.scrollbackLines`.

xterm's normal buffer holds `scrollback + rows` lines; `baseY` saturates at `scrollback` when the buffer becomes *full*,
one line before the first eviction. Verified with `scrollback: 10, rows: 5`: after 14 lines `baseY = 10` and the flag is
`true` while the oldest retained line is still `L1`; the first real loss happens at 15 lines.

Pre-existing arithmetic, but this PR is what puts it in front of the user — the pane now asserts "Earliest output is no
longer available" at the exact moment it still is. Sticky is the right choice; the boundary is off by one
(`baseY > scrollbackLines`, or compare against a first-retained marker).

## 7. MINOR — pending-wrap loss at the final cell overwrites a character

`packages/runtime/src/service/TerminalEmulator.ts`, `savedCursorRestoration` (disclosed in its doc comment, untested).

**Reproduced.** Save, then fill the row to exactly column 80, snapshot, replay, then write `W`. Truth wraps `W` onto the
next row; the client overwrites the last `z` of row 12 with `W`. The trailing `CUP` discards `serialize()`'s
pending-wrap reconstruction. The comment argues this is narrower than losing the slot entirely, which is fair, but the
new `TerminalEmulator.replayFidelity.test.ts` has a mid-wrapped-line case *without* a save (so no suffix is emitted) and
a saved-cursor case *without* a wrap — the acknowledged gap has no pin.

## 8. MINOR — the same text frame is JSON-parsed twice, through two functions where one suffices

`www/packages/canvas/src/viewers/terminal/CapturedRunPane.tsx`, `AttachedRunTerminal.onTextFrame`.

`parseRunTerminalServerTextFrame` already returns `run.error` as a `RunErrorFrame`, so the added call makes
`parseRunErrorFrameText` redundant: every inbound text frame now runs `JSON.parse` twice and is validated twice. One
parse plus a `switch` on `frame.type` covers both. Also `const errorText = parseRunErrorFrameText(text)` names a
`RunErrorFrame | undefined` "text".

## 9. MINOR — at `cols: 1` the server grid and the PTY geometry diverge permanently

`packages/runtime/src/service/RunManager.ts`, `resizeRun`; `packages/runtime/src/service/TerminalEmulator.ts`, `resize`.

The wire floor is `MIN_TERMINAL_DIMENSION = 1`, but xterm clamps to `MINIMUM_COLS = 2` / `MINIMUM_ROWS = 1` in both its
constructor and `resize`. A client sending `{"type":"resize","cols":1,"rows":1}` leaves the PTY at 1 column,
`run.terminalSize` recording 1, and the emulator at 2 — so the `run.terminal.ready` frame reports `cols: 2` and the
server renders 1-column PTY output into a 2-column grid. No wedge and no exhaustion (the ceiling is untouched at
500×200, and `FitAddon.proposeDimensions` never proposes below the same minimums), so this is a fidelity wart reachable
only by a hand-crafted frame. Worth one line: reject below 2 columns at the contract, or record the clamped value.

## 10. MINOR — the terminal viewer reaches into the resource viewers' primitives

`www/packages/canvas/src/viewers/terminal/CapturedRunPane.tsx` imports `../resource/primitives/TruncationNote`, whose
own doc says "Shared 'partial content' note **for the resource viewers**". Reusing it is the right call over a copy;
either move it to a viewer-neutral primitives home or widen the doc so the next viewer knows it may.

## 11. MINOR — the note is not announced

`TruncationNote` renders a bare `<p>`; the sibling `.terminal-pane__status` carries `role="alert"`. A note that appears
asynchronously mid-session (and, per finding 2, only should) is invisible to assistive tech. `role="status"` would match
the pane's existing vocabulary.

---

## Item 2 — the replaced legacy test

The replacement in `RunManagerTerminal.test.ts` ("treats the viewport as authoritative at any size") is **strictly
stronger** than what it replaced. The old test asserted `spawnInputs[0]` was `{cols:80, rows:24}` for a 35×7 create and
`session.resizes` stayed `[]` after a 35→resize; the replacement asserts spawn at `{cols:35, rows:7}` and
`session.resizes === [{cols:33, rows:5}]`, plus the text snapshot at 33×5. Every assertion is the negation of the old
one and none is weaker. `RunManager.test.ts`'s new "viewport-authoritative geometry" case adds the end-to-end
consequence (resize → attach → snapshot 40×10 with the pre-shrink prompt still reachable in the replay).

Sweep for surviving old assumptions: no other test asserts a swallowed resize, and no test asserts 80×24 as a *clamped
output*. The remaining `80`/`24` hits across `packages/` are fixture inputs (`TerminalFanout.test.ts`,
`TerminalEmulator.test.ts`, `NodePtyAdapter.test.ts`, the new replay-fidelity scenarios). One informational case:
`packages/runtime/src/server/runtimeRouter.test.ts` opens the terminal socket with `cols=132&rows=43` and asserts the
ready frame carries `terminal: { cols: 80, rows: 24 }`. That still passes for the right reason — `RunManager.attach`
deliberately does not resize the run, and the fixture created it at the 80×24 default — but it now reads like an 80×24
guarantee. A comment naming "attach does not resize; 80×24 is the fixture's create size" would keep the next reader
from mis-reading it as the floor coming back.

## Item 5 — scope

Clean. The diff contains the three stated changes and nothing else: the `@tm/common` import in `RunManager.ts` narrows
to a type-only import purely because the two constants are no longer referenced, and the CSS addition is the note's own
rule. No unrelated refactors, no drive-by renames, no dependency changes.

---

# Re-verification of `360383a9`

Delta-only review of `360383a9` on top of `a3cf4fb8` (+963/-85, 25 files, 9/9 green). Read-only; tree pristine at
start and at write time (`git status --porcelain` empty both times, HEAD `360383a9`). No edits, no commits, no gates
run (the tree is shared). Evidence again from the repo's own `@xterm/headless@6.0.0` + `@xterm/addon-serialize@0.14.0`
in a scratchpad harness replicating the new `TerminalEmulator` logic verbatim; no captured runs, no Postgres, no
keychain, no `~/Library`, no channel homes.

**All 11 original findings are addressed. Two of the fixes introduce new defects in the very property they were meant
to restore.** New: **1 blocker / 2 major / 4 minor**. Fail-safe verdict: **unsound** — see NEW-2.

## Closure of the original 11

| # | original | closed by | verdict |
|---|---|---|---|
| 1 | note overlays live rows | `.terminal-pane { flex-direction: column }`, note now `flex: none` in flow, DOM-ordered above the surface | closed |
| 2 | truncation only at attach | `RunTerminalTruncatedFrame` + `TerminalFanout.notifyTruncated` + `attachmentPump` branch + `TerminalEmulator.onTruncated` | closed (mechanism); trigger now wrong, see NEW-1 |
| 3 | shadow tracked only `ESC 7` | `registerSavedCursorShadow` mirrors `ESC 7`, `CSI s`, `CSI ?1048h`, `CSI ?1049h`, clears on RIS/DECSTR, keys by `bufferType` | closed for position; four pinning tests added |
| 4 | DECRC also restores SGR/charset | `SavedCursorShadow.pen` + `sgrReset`, charset fail-safe | closed for the tested path; pen mirror holed, see NEW-2 / NEW-3 |
| 5 | control-plane read shrinks | converted to an explicit owner invariant on `RunManager.terminalTextSnapshot` + 40×8 alt-screen test | closed as a decision |
| 6 | `truncated` off-by-one | `registerMarker(0)` + `firstLine.isDisposed` | narrow defect closed (test pins L1 retained at 14 lines); replaced by a larger one, see NEW-1 |
| 7 | pending-wrap overwrite | `cursorX >= cols - 1` omission + test | closed |
| 8 | double parse / `errorText` | single `parseRunTerminalServerTextFrame` + `switch` | closed |
| 9 | `cols: 1` divergence | `MIN_TERMINAL_DIMENSION` split into `MIN_TERMINAL_COLS = 2` / `MIN_TERMINAL_ROWS = 1`, threaded through the contract and `NodePtyAdapter` | closed; no stale `MIN_TERMINAL_DIMENSION` reference remains |
| 10 | cross-viewer import | `TruncationNote` moved to `viewers/primitives/`, all four callers updated, doc widened | closed; no stale `resource/primitives/TruncationNote` reference remains |
| 11 | not announced | `role?: "status"` prop, passed by the terminal pane, asserted in the test | closed |

Verified independently, both clean: `CSI s` is unconditionally `saveCursor` in xterm (no DECSLRM / mode-69 branch), so
mirroring it is faithful; `softReset` does reset `_curAttrData` and the active buffer's `savedX/savedY`, so
`shadowClear` matches DECSTR.

## NEW-1 (BLOCKER) — the new truncation detector fires on a screen clear, with zero scrollback overflow

`packages/runtime/src/service/TerminalEmulator.ts`, constructor `this.firstLine = this.terminal.registerMarker(0)` and
`append`.

xterm disposes a line's markers whenever that **line is erased**, not only when it is evicted: `eraseInDisplay` calls
`clearMarkers(ybase + y)` per reset line. While the run is still inside its first screenful (`baseY === 0`), line 0 is
a viewport line, so any full-screen erase kills the marker.

**Reproduced** at `cols: 80, rows: 24, scrollback: 10000` after writing three lines — no overflow is even possible:

| stream | `firstLine.isDisposed` (⇒ `truncated`) | `baseY` |
|---|---|---|
| plain output | false | 0 |
| `CSI 2J` (clear screen) | **true** | 0 |
| `CSI 2J CSI 3J CUP` (the standard clear-terminal triple) | **true** | 0 |
| `CSI 1J` (erase above) from row 10 | **true** | 0 |
| `CSI 3J` alone, `CSI 2K`, `CSI 0J`, RIS, alt enter/leave | false | 0 |

Resizes are clean (checked rows 24→8, 24→2, 8→24 and cols 80→20 with 3 and 20 lines: marker survives, `L1` retained).

**Failure scenario.** Open a fresh captured Claude pane. Within the first 24 rows of output the harness clears the
screen (Ctrl+L, `/clear`, or any TUI that starts with a clear). `firstLine.isDisposed` flips, `append` sets
`truncated = true` and fires `onTruncated()`, `TerminalFanout.notifyTruncated()` pushes `run.terminal.truncated` to
every attached viewer, and the pane renders *"Earliest output is no longer available: this run outgrew the 10,000 lines
of scrollback the terminal keeps."* The run produced perhaps twenty lines. The flag is sticky, so the false claim
persists for the life of the run and is repeated on every subsequent attach's ready frame.

This is worse than the finding-6 defect it replaces: that one over-claimed by exactly one line at the 10,000-line
boundary; this one over-claims by the entire run at line ~20, on the owner's live stable-channel path, and it now also
pushes a live frame rather than only colouring an attach.

The requirement is "a line was evicted from the retained scrollback", which is a scroll event, not a content marker.
The exact signal is available without a marker: `truncated` becomes true on the first scroll that occurs while
`buffer.normal.baseY` is already at `scrollbackLines` (subscribe to `terminal.onScroll`, or keep the old arithmetic and
require one further scroll after saturation). Keeping the marker *and* requiring `baseY >= scrollbackLines` would also
close it.

## NEW-2 (MAJOR) — the fail-safe is unsound: the pen mirror desynchronises across `?1049h`/`?1049l` and no omission condition fires

`packages/runtime/src/service/TerminalEmulator.ts`, `shadowRestorePen` and `savedCursorRestoration`.

This is the inverse the brief asked for, and it exists. The five omission conditions all guard the **position**
shadow; none observes the **pen**. Root cause: xterm keeps one saved slot *per buffer* and `?1049h`/`?1049l` implicitly
save/restore across the buffer switch, while the shadow keeps a single slot tagged with a `bufferType`.
`shadowRestorePen` runs *before* xterm performs the switch, so on `?1049l` it compares the shadow's `"normal"` against
the still-active `"alternate"`, decides the slot is foreign, and clears the pen — while xterm, having switched first,
restores the normal buffer's saved attributes.

**Reproduced.** Stream `history\r\n` `ESC[31m` `ESC[?1049h` `alt frame` `ESC[0m` `ESC[?1049l`, snapshot, replay, then
write `LIVE-TEXT`:

- suffix omitted? **no** — shadow non-null, `bufferType` matches the now-active normal buffer, `charsetDirty` and
  `penDirty` false, cursor not at the last column. Every fail-safe passes.
- truth `LIVE-TEXT`: `fgDefault: false, fg: 1` (red, restored from the normal buffer's slot).
- client `LIVE-TEXT`: `fgDefault: true, fg: -1` (default).

The blast radius is wider than the old suffix's. `savedCursorRestoration` now ends with `sgrReset(this.pen)`, which
**overwrites the live SGR that `serialize()` correctly restored**. So a wrong pen no longer costs a wrong colour after
a post-attach DECRC; it costs the wrong colour for *all* output after the attach. Where the mechanism is wrong it is
now worse than emitting nothing.

The same desync reaches the position shadow by chaining: `ESC 7` (normal) → `?1049h` → `ESC 7` (alt) → `?1049l` leaves
the shadow tagged `"alternate"` while the active buffer is normal (suffix omitted, safe), but the pen is now the alt
buffer's; a subsequent `ESC 7` in the normal buffer captures that wrong pen into a shadow that *is* emitted.

Smallest correct shape: keep two shadows, one per buffer type, and have the `?h`/`?l` handlers act on the buffer the
sequence targets rather than the one that happens to be active when the custom handler runs. Failing that, treat any
`?1048`/`?1049` restore as unprovable and set a `penDirty`-style flag.

## NEW-3 (MAJOR) — `sgrSequence` reserializes xterm sub-parameters into a sequence that parses to no colour

`packages/runtime/src/service/TerminalEmulator.ts`, `sgrSequence`.

xterm's `params.toArray()` represents colon sub-parameters as a nested array *following* the parent value, and uses
`-1` for an omitted sub-parameter. `sgrSequence` joins the outer list with `;` and the nested list with `:`, which
detaches the sub-parameters from their parent and re-emits the `-1` sentinel literally.

**Reproduced.** `ESC[38:2::255:0:0m` (the ITU/ISO colon form of 24-bit colour) yields
`params.toArray() = [38, [2, -1, 255, 0, 0]]` and `sgrSequence` produces `ESC[38;2:-1:255:0:0m`. Replayed into a fresh
terminal:

- original: cell `fg = 16711680`, `isFgRGB() = true`
- round-trip: cell `fg = -1`, `isFgRGB() = false`

The text still prints, so there is no visible garbage, but the colour is silently dropped — from both the saved-slot
pen and the live pen, on every snapshot the suffix is emitted for. Reachability is low for chalk/Ink (semicolon form)
and higher for anything emitting the standard colon form. `sgrSequence` should join a nested group to its parent with
`:` and drop or re-encode `-1` as an empty sub-parameter.

## NEW-4 (MINOR) — the charset fail-safe covers four designations out of about fifteen

`packages/runtime/src/service/TerminalEmulator.ts`, `registerSavedCursorShadow` charset loop.

The loop registers `ESC ( 0`, `ESC ( A`, `ESC ) 0`, `ESC ) A`. xterm's `CHARSETS` map carries roughly fifteen finals
(`0 A B 4 C 5 R Q K Y E 6 Z H 7 =`) and xterm also designates G2/G3 via `ESC *` and `ESC +`. A stream designating, say,
`ESC ( K` changes the charset that DECSC saves while leaving `charsetDirty` false, so the suffix is emitted with a
charset the reconstruction does not model. Narrow (national replacement charsets are effectively dead in modern TUIs),
but a fail-safe that enumerates a subset reads as if it enumerates the set. Register the intermediates
(`( ) * +`) and treat *any* final as dirty, rather than listing finals.

## NEW-5 (MINOR) — the overlay regression is pinned by grepping the stylesheet, not by an observable

`www/packages/canvas/src/viewers/terminal/CapturedRunPane.test.tsx`, "lays the note out as a flex row above the
terminal surface, never over it".

The test reads `terminal-pane.css` off disk and asserts the `.terminal-pane` rule contains `flex-direction: column`
and the `.terminal-pane__truncation` rule does not contain `position: absolute`. The jsdom constraint is real and the
compromise is defensible, but the assertion is on the intermediate config rather than the end state: it passes if the
note is given `position: fixed`, if it is overlaid by a negative margin or a transform, or if the JSX is reordered to
put the note after the surface. Asserting DOM order (the note precedes `.terminal-pane__surface`) alongside the CSS
strings would cover the reordering case cheaply. (The `resolve(process.cwd(), "../canvas/src/...")` path happens to
resolve correctly from both the shell and the canvas package roots; worth a word in the comment so nobody "fixes" it.)

## NEW-6 (MINOR) — the 40×8 invariant test only has teeth in its geometry assertion

`packages/runtime/src/service/RunManager.test.ts`, "the control plane observes exactly what the human sees, with no
hidden floor".

It would fail if a row floor were restored — `toMatchObject({ cols: 40, rows: 8 })` catches that, which is the stated
purpose. But the two `toContain` assertions carry no weight: three lines of alt-screen content fit in an 8-row buffer
and would fit in a 24-row floored one too, so they pass in both worlds and pass equally if `textSnapshot` were reading
the normal buffer. To pin "exactly what the human sees", emit more than 8 rows into the alternate buffer and assert
the overflowed rows are **absent** from the snapshot — that is the invariant, and it is currently unpinned.

## NEW-7 (MINOR) — dead branch in `sgrSequence`

`sgrSequence` returns `null` for `params.length === 0` and the `m` handler treats that as "bare reset". xterm never
yields an empty parameter list for `CSI m`: verified that a bare `ESC[m` arrives as `[0]`, which the `startsWithReset`
branch already handles correctly. The `null` path and its `this.pen = []` branch are unreachable.

## Regression surface

Everything in `360383a9` traces to one of the 11. The only additions not directly named by a finding are
`RunManagerOptions.terminalScrollbackLines` (a test seam on a production type, documented as such, required to
exercise overflow) and the `TerminalFanout.test.ts` `resizeFrom` guard plus the `runtimeRouter.test.ts` comment, both
of which follow mechanically from the new queue-item variant and my item-2 note. `AttachmentClosed` carries no `kind`
field, so `attachmentPump`'s `"kind" in item` discriminant remains correct with the third variant. No unrelated
refactors, no dependency changes, no scope creep.

---

# Final delta `cfb79886`

Delta-only review of `cfb79886` (3 files, +221/-57) against `## Re-verification of 360383a9`. Read-only; tree pristine
at start and at write time, HEAD `cfb79886`. The intermediate `8a3bed15` (round-2 minors) was outside this pass per the
brief. Evidence from the shipped `@xterm/headless@6.0.0` bundle and a scratchpad harness replicating the new
`TerminalEmulator` verbatim; no captured runs, no Postgres, no keychain, no `~/Library`, no channel homes.

**NEW-2, NEW-3, NEW-7: all three closed.** Invariant: **sound**. Closure test: **load-bearing, with one named gap.**
New: **0 blocker / 0 major / 3 minor**.

## Closure of NEW-2, NEW-3, NEW-7

Re-ran every previously reproduced defect against the new model plus twenty-two fresh scenarios. Truth versus
replayed-client comparison over cursor (x/y/baseY/buffer type), full buffer rows, and the foreground attribute at the
post-boundary marker.

- **NEW-2 (pen desync across `?1049h`/`?1049l`)** — closed. The exact reproduction (`ESC[31m` → `?1049h` → alt work →
  `?1049l` → snapshot → replay → write) is now equivalent, suffix **emitted**. Also equivalent: `?1048h`/`?1048l` in
  place; the nested `ESC 7` normal → `?1049h` → `ESC 7` alt → `?1049l` case that was the chained variant; `?47h`/`?47l`
  (no implicit save/restore); alt re-entry with a surviving alt slot; DECSTR inside alt then leave; RIS inside alt;
  `?1048;1049l` and `?1049;1048l` multi-parameter exits.
- **NEW-3 (colon sub-parameter reserialization)** — closed. `ESC[38:2::255:0:0m` now round-trips: the client's marker
  cell matches truth's RGB foreground. Also equivalent for `38:5:196` mixed with semicolon-form attributes, plain
  semicolon truecolor, and a bare `ESC[m` used as a reset anchor.
- **NEW-7 (dead `params.length === 0` branch)** — closed the right way: `sgrSequence` is now total and
  `startsWithReset` treats an empty list as a reset, so the handler is total without carrying an unreachable branch.

The round-1 and round-2 cases all still hold: `ESC 7`/`ESC 8`, `CSI s`/`CSI u`, `CSI s` superseding an earlier `ESC 7`,
RIS and DECSTR after a save (suffix correctly withheld), a normal-buffer save while the alternate buffer is active
(withheld), DECRC restoring the save-time SGR, and a save resting at the last column (withheld).

## 1. The ordering invariant — sound, and the exception is the only one

Verified from the bundle, not the summary. Exhaustive scan of `@xterm/headless@6.0.0`
(`lib-headless/xterm-headless.js`, which is what `require.resolve` returns) finds exactly five occurrences each of
`saveCursor(` and `restoreCursor(` — four call sites plus the method definition on each side:

| slot operation | site in the bundle | buffer xterm executes it on | shadow observes |
|---|---|---|---|
| `ESC 7` | `registerEscHandler({final:"7"},()=>this.saveCursor())` | active, in place | active ✓ |
| `CSI s` | `registerCsiHandler({final:"s"},e=>this.saveCursor(e))` | active, in place | active ✓ |
| `CSI ?1048h` | `case 1048:this.saveCursor();break;` | active, in place | active ✓ |
| `CSI ?1049h` | `case 1049:this.saveCursor();case 47:case 1047:…activateAltBuffer(…)` — **saves, then falls through to the switch** | active *before* the switch | active ✓ |
| `ESC 8` | `registerEscHandler({final:"8"},()=>this.restoreCursor())` | active, in place | active ✓ |
| `CSI u` | `registerCsiHandler({final:"u"},e=>this.restoreCursor(e))` | active, in place | active ✓ |
| `CSI ?1048l` | `case 1048:this.restoreCursor();break;` | active, in place | active ✓ |
| `CSI ?1049l` | `case 1049:case 47:case 1047:…activateNormalBuffer(),1049===e.params[t]&&this.restoreCursor()` — **switches, then restores** | normal, *after* the switch | forced `"normal"` ✓ |

Eight sites, seven in place, one exception, and the code's handler mapping matches all eight. **No second ordering
exception exists.** The `?1049h` half is the one that could plausibly have been a second exception and is not: the
fall-through puts the save strictly before `activateAltBuffer`.

## 2. The two omission conditions that disappeared

Both are accounted for; neither was dropped.

- **"the save belongs to the inactive buffer"** is now *impossible* rather than guarded. `savedCursorRestoration`
  reads `this.shadows[buffer.type]`, so a slot is either the active buffer's or absent; a foreign slot cannot be
  reached. This collapses into "no slot for the active buffer", and it is a strict improvement: the old condition
  discarded a *valid* alternate-buffer slot whenever the pane snapshotted in the alternate buffer, so the shadow now
  covers cases it previously refused. Confirmed by the "alt re-entry" scenario, which emits a correct alternate-buffer
  suffix where the old model would have withheld it.
- **"RIS/DECSTR nulled the slot"** also collapses into "no slot", via `shadowReset` (both slots) and `shadowSoftReset`
  (active slot only). Equivalence confirmed empirically for both.

**The attack, repeated.** One state survives where the shadow is wrong and none of the three conditions fire — see
minor 1 below. Everything else I tried is either equivalent or correctly withheld. What I tried and could not break:
every pairing of the four writers with the two restores across both buffers; `?47h`/`?47l` (which take no slot action
in xterm and correctly take none in the shadow); alt re-entry after `activateNormalBuffer()` calls `_alt.clear()` —
verified from the bundle that `Buffer.clear()` resets `ydisp/ybase/x/y/lines/scroll region/tab stops` and **not**
`savedX/savedY/savedCurAttrData`, so xterm's alternate slot survives the exit and the persisting shadow is right;
DECSTR in either buffer; RIS in either buffer; a spurious restore with no prior save; and the pen across every one of
those.

## 3. The two unreported fixes — both correct against the bundle

- **DECSTR clears only the active buffer's slot.** `softReset` reads
  `…this._activeBuffer.savedX=0,this._activeBuffer.savedY=this._activeBuffer.ybase,this._activeBuffer.savedCurAttrData.fg=…,this._activeBuffer.savedCharset=…`
  — `_activeBuffer` throughout, never both buffers. The old `shadowClear` over-cleared. Note the shadow *nulls* where
  xterm *resets to (0, ybase) with default attributes*; those are behaviourally identical for the reconstruction,
  since a null shadow withholds the suffix and the replaying client's own default slot is (0,0) with default
  attributes, i.e. the same relative row and pen. Confirmed equivalent.
- **A spurious `?1049l` with no prior save resets the pen to default on both sides.** The `Buffer` constructor
  initializes `savedCurAttrData = DEFAULT_ATTR_DATA.clone()` and `restoreCursor` copies it into `_curAttrData`
  unconditionally, so restoring an untouched slot *does* reset the live pen in xterm. `shadowRestore`'s
  `this.shadows[type]?.pen ?? []` mirrors exactly that. Confirmed equivalent for both `?1049l` and `?1048l` with no
  prior save.

## 4. The closure test — load-bearing, with one gap

`TerminalEmulator.slotClosure.test.ts` is genuinely load-bearing, not decorative. Verified first-hand:
`require.resolve("@xterm/headless")` resolves to `lib-headless/xterm-headless.js`, the bundle I audited;
`/saveCursor/gu` counts 5, `/restoreCursor(?!Color)/gu` counts 5, and the `?1049l` ordering regex matches. It tracks
the installed artifact rather than a transcribed claim, and the most likely future change — xterm adding a fifth
writer, e.g. a new DECSET that saves — moves the count and fails the test. Its failure modes under minification or
identifier changes are all *loud* (count drops to 0, regex stops matching), never silently green.

The gap: **the counts are position-blind, and only one half of the ordering invariant is pinned.**

- A future xterm that *swaps* a site — drops `CSI s` handling and adds a save under some other mode — keeps the count
  at 5 and passes while the mirrored writer set is wrong. The property is "the set is {`ESC 7`, `CSI s`, `?1048h`,
  `?1049h`}"; the assertion is only "the set has four members".
- Nothing pins the `?1049h` half. If xterm ever moved its save after `activateAltBuffer`, both assertions still pass
  and `shadowSave` would silently record the wrong buffer — the same class of defect as NEW-2. The bundle form is
  regex-able today: `/case 1049:this\.saveCursor\(\);case 47:case 1047:/u` matches (verified), and asserting it would
  close the gap for the cost of one line. Matching each of the four save sites and four restore sites by its own
  context rather than by a total count would close the first.

## 5. Regression surface

Everything in `cfb79886` traces to NEW-2, NEW-3, NEW-7 or the two named extras. `SavedCursorShadow` losing its
`bufferType` field and the `BufferType` alias are mechanical consequences of the per-buffer split;
`charsetDirty` + `penDirty` merging into `shadowUnfaithful` is the omission-condition collapse the split enabled, not
new scope. No behaviour outside the shadow is touched: `onScroll` truncation, the snapshot surface, and every other
member are byte-identical to `8a3bed15`.

## New findings

### 1. MINOR — a multi-parameter `?h` performs two saves in xterm and one in the shadow

`packages/runtime/src/service/TerminalEmulator.ts`, the `{ prefix: "?", final: "h" }` handler.

xterm's `setModePrivate` loops over parameters and acts on each; the shadow's handler calls `shadowSave()` at most
once, against the buffer active when the handler runs. For every real sequence this is identical, because 1048 and
1049 are alternatives that no emitter combines. `CSI ?1049;1048h` is the exception: xterm saves the normal slot
(param 1049, pre-switch), activates the alternate buffer, then saves the *alternate* slot (param 1048, post-switch).
The shadow records only the normal one. `CSI ?1049;1049h` behaves the same way.

**Reproduced.** `ESC[31m` `CSI ?1049;1048h` ` alt-frame` `ESC 8` `ESC 7` `CSI[10;1H` → snapshot → replay → `ESC 8`
`MARKER`. The suffix **is emitted**, and it is wrong: truth renders `MARKER` at `fg` palette 1, the client at default.
The chain is that the `ESC 8` restores xterm's alternate slot (red pen) while the shadow, having no alternate slot,
resets its pen to default; the following `ESC 7` then writes that wrong pen into an alternate shadow which passes all
three omission conditions. Stopping right after the `?h` instead only *withholds* the suffix — the fail-safe holds
there and the cost is the pre-shadow restore-to-home.

Not reachable from any emitter I know of — ansi-escapes, Ink, crossterm and termios reset strings all emit 1048 and
1049 separately — which is why this is a minor and not a repeat of NEW-2. The fix is one line: act per matching
parameter in sequence order rather than once per sequence.

### 2. MINOR — the closure test's gap (see section 4)

Position-blind counts plus an unpinned `?1049h` ordering half. Concrete, cheap fix stated above.

### 3. MINOR — `shadowUnfaithful` is sticky past the point where xterm has restored the modelled state

`shadowReset` (RIS) clears it; `shadowSoftReset` (DECSTR) does not. But the bundle's `softReset` calls
`this._charsetService.reset()` and `this._curAttrData = DEFAULT_ATTR_DATA.clone()`, so after DECSTR both unmodelled
states *are* back to their defaults and the shadow is provably faithful again. The conservative choice is safe, but it
costs coverage: one `ESC ( 0` anywhere in a run disables reconstruction for the rest of that run, and "fail safe" here
means the original symptom returns — the client restores to home and splices output over row 0, which I confirmed is
exactly what the charset scenarios now produce. Worth knowing as a coverage figure rather than a defect: the mechanism
is off for any run that designates a charset, permanently, even after a soft reset that would make it valid again.
