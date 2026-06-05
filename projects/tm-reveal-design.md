# The First-Run Reveal, at canvas scale

Design for the first thirty seconds after install. Fable seat, 2026-08-05.
Folds in the direction change: we own the canvas, no modal, no pane-squeezed
card. Every number below is read from real captured artifacts, cited by run
and exchange. Reused components are named path+SYMBOL. Both moments of truth
in this document, the headline and the ledger, are server-owned numbers
(`exchange_recorder/stats.py:build_req_stats`, `@tm/core contextTokens`), so
the design adds presentation, never a second accounting.

## Ground truth (the data this design renders)

Claude, run `5f44eeaa`, exchange `20260805T050107Z-e6ca3001`, verified from
`request.raw` and `entry.json`:

| What went over the wire | Chars |
|---|---|
| System, 3 parts (billing header 70, "You are Claude Code" 57, instructions 18,552) | 18,679 |
| 22 tool schemas (largest: Artifact 11,128; ten are cx_* memory tools) | 52,667 |
| A system-reminder carrying CLAUDE.md and project context | 6,858 |
| SessionStart hook output, written by the user themselves | 35,409 |
| **The user's words: "Reply with OK."** | **14** |
| Total request | 114,434 |

Tokens: 41,877 context, of which 41,837 was cache write. The reply: "OK."

Codex, run `5ef9c17e`: the prompt turn (`20260805T050116Z-70107045`) sent
39,752 chars: a 34,991-char Memory briefing (developer), AGENTS.md at 4,467
chars, and the same 14-char prompt, for 20,149 input tokens, reply "OK". Its
tool definitions travelled two seconds earlier in a separate configuration
frame (`20260805T050114Z-3e9a0164`, 48,714 chars) as an `additional_tools`
item inside the conversation stream, which is why `entry.req.tools_chars` is
honestly 0 on the prompt turn: codex ships tools as conversation, not as a
tools block. The design treats that as a fact to reveal, not a gap to hide.

## The one line

Set over both terminals once both harnesses settle, or over the single
terminal when only one runs:

> **You typed 14 characters. Your agents sent 203,000 on your behalf.**

(The number is live: sum of `entry.req.total_chars` over the revealed
exchanges. One harness: "Your agent sent 114,434 on your behalf.")

This is the lean-in line because it is arithmetic the user can check by
counting their own keystrokes. Percentages describe; this indicts, gently,
and every word of it is in the capture.

## The five moments of the canvas

The canvas is the surface. Nothing modal, nothing floats over anything. Panes
are placed by the existing engine (`engine/react/LayoutCanvas.tsx:LayoutCanvas`,
`engine/react/PaneFrame.tsx:PaneFrame`, strategies
`engine/layout/strategies/singleRow.ts:planSingleRow` and
`gridFit.ts:planGridFit`), so every state below is a layout plan, not new
chrome.

### M0 — Before ENABLE (the pre-click state is the lobby, not a leftover)

The ambient backdrop (`workbench/CanvasWorkbench.tsx:AmbientBackdrop`) stays.
On it, centered, one column, generous negative space:

- Kicker, 11px, letterspaced, `--color-txt-3`:
  `TRANSPORT MATTERS · FIRST CAPTURE`
- Title, the one large type moment before the reveal (see scale below):
  `See what your agent sends before you type a word.`
- The harness inventory as canvas objects: the existing cards
  (`firstrun/FirstRunScreen.tsx:FirstRunScreen` harness mode,
  `firstrun/harnessCards.ts:harnessCard`, styled by `firstrun/firstrun.css`)
  laid as a `planSingleRow` band, one card per registered harness, ticking
  Detected → Authenticated live via
  `firstrun/useHarnessInventory.ts:useHarnessInventory`. Not-authed cards show
  their `login_command` fact exactly as the component already renders it.
- Beneath, a single control, the only decision on screen: **ENABLE**, plus
  one line of consent copy, `--color-txt-2`, 12px:
  `Your agents will start in front of you and send one 14-character turn on
  your account. Nothing is changed or filtered; Transport Matters records
  what goes over the wire.`

No modal, no session picker. The session picker is not first-run furniture;
it stays a ⌘K surface (`launcher/CommandCenter.tsx:CommandCenter`).

### M1 — Boot (0–5s after ENABLE)

The card band compacts upward into a status strip and the terminals arrive as
real canvas objects: one `viewers/terminal/CapturedRunPane.tsx:CapturedRunPane`
per authed harness, spawned by the existing
`workbench/SessionCanvasRoute.tsx:launchFirstRunHarnesses` via
`useCanvasStore.addCapturedRun`. Two harnesses: two terminals side by side,
`planGridFit` two columns, each at comfortable terminal proportion. One
harness: a single centered terminal at the same width, flanked by empty
space, which reads as deliberate stage, not absence.

Above each terminal, its pane title carries the existing progress copy from
`launchFirstRunHarnesses` verbatim: `Starting Claude Code. Answer any sign in
or trust prompt in its pane.` The harness's own dialogs (Claude's trust
prompt) happen inside the terminal, where a terminal is the one place a
terminal prompt looks intentional.

No skeletons, no spinners beyond the pane's own existing loading chrome
(`viewers/registry.tsx:PaneShell`). The terminal output IS the loading state,
and it is the most honest one we own.

### M2 — The turn lands (pacing: land at once, per harness)

The turn takes one to two seconds. That is too fast to narrate and too slow
to pretend is instant, so the rule is: **no element renders until its number
is real, and each harness reveals the moment its own turn settles.** Claude
will usually land first; its reveal composing while codex still streams is
the pacing, free, truthful, and staggered by reality rather than by
animation. Nothing delays information; information arrives when it exists.

As each harness's substantive turn settles, a reveal panel composes BESIDE
its terminal (terminal shifts left within its cell, reveal takes the right
half; the pair now reads as one object). The panel is the existing
`provider-exchange` pane (`viewers/registry.tsx` viewer →
`viewers/resource/ArkExchangeViewer.tsx:ArkExchangeViewer` with
`initialView: "first-run"`), whose `FirstRunReveal` section is restyled to
canvas scale (same component, same data, new CSS in
`viewers/resource/exchange-viewer.css` under the existing
`canvas-exchange__reveal-*` block).

### M3 — Both settled: the comparison is the arrangement

When the second harness settles, the one line (above) sets in the band
between the two terminal+reveal pairs. The spatial argument:

```
   You typed 14 characters. Your agents sent 203,000 on your behalf.

  ┌─ CLAUDE CODE ─────────┐┌─ reveal ──────┐  ┌─ CODEX ───────────────┐┌─ reveal ──────┐
  │ $ claude              ││ 114,434 chars │  │ $ codex               ││ 88,466 chars  │
  │ > Reply with OK.      ││ one payload,  │  │ > Reply with OK.      ││ two frames,   │
  │ OK                    ││ every turn    │  │ OK                    ││ resent as the │
  │                       ││ 41,837 cached │  │                       ││ chat grows    │
  └───────────────────────┘└───────────────┘  └───────────────────────┘└───────────────┘
```

Identical prompt, identical two-letter answer, two different economies. What
the contrast teaches that neither alone can: **the payload is a property of
the harness, not of the model or the task.** Claude ships everything every
turn and pays once into cache (41,837 tokens of cache write on turn one).
Codex spreads itself across frames and resends conversation incrementally.
Same user, same day, same "OK".

### M4 — At rest

The reveals stay. Under the one line, one quiet sentence, `--color-txt-3`:

`Transport Matters recorded this; it changed nothing. Every turn from now on
is captured the same way.`

And one action per pair, the existing pane affordance, not a new button:
`Open the full wire record` → the exchange's inspect tab that
`ArkExchangeViewer` already owns (its `ExchangeBody` tabs). Depth lives
there, not here. The ⌘K registry remains the way everything else is reached.

## The reveal panel, at canvas scale

Content hierarchy inside each panel, top to bottom. All figures from
`entry.req` + `contextTokens(entry.res)` + `fetchTurnContent` — the owners
the Inspector uses.

1. **Kicker** (11px, letterspaced, `--color-sage`): `WHAT YOUR AGENT SENT`
2. **The number** (the one large glyph moment; see scale): `114,434`
   with unit line under it (12px, `--color-txt-2`): `characters in one turn ·
   41,877 provider-billed tokens`
3. **The ledger** — four rows, each the existing left-rail row idiom
   (`canvas-exchange__reveal-part`, 2px left border), color-coded by rail,
   value in mono, one plain-language clause each. Concrete copy, Claude
   panel:

   - `--color-sky` · **System instructions** · `18,679 chars · 3 parts` ·
     `Who your agent believes it is. You wrote none of it.`
   - `--color-lavender` · **Tool catalog** · `52,667 chars · 22 schemas` ·
     `Every tool it could use, sent in full. This turn used none of them.`
   - `--color-amber` · **Context you brought** · `42,267 chars` ·
     `Your CLAUDE.md and reminder (6,858) plus your SessionStart hook
     (35,409), attached to every single turn.`
   - `--color-sage` · **Your words** · `14 chars` · `"Reply with OK."`

   The sage row is the anchor; it renders the actual prompt text from
   `get_turn_content` (`stats.py:extract_user_prompt_text`), truncated to one
   line. Fourteen characters against a hundred thousand needs no chart.

4. **Footnote** (11px, `--color-txt-3`), the honesty line:
   `Recorded as sent. Nothing was optimised, trimmed, or blocked.`

Codex panel, same skeleton, rows that tell its true shape:

   - `--color-sky` · **System instructions** · `34,991 chars` ·
     `Includes a Memory briefing the harness writes for itself.`
   - `--color-lavender` · **Tool catalog** · `sent inside the conversation` ·
     `31,118 chars delivered as a stream frame two seconds earlier.`
   - `--color-amber` · **Context you brought** · `4,467 chars` ·
     `Your AGENTS.md, attached to every turn.`
   - `--color-sage` · **Your words** · `14 chars` · `"Reply with OK."`

   The lavender row proves degradation is designed: when `tools_chars` is 0
   because the harness ships tools as conversation, the row states that fact
   instead of printing `0 chars 0.00%`. A smaller payload produces shorter
   rows, never empty ones; any row whose value is genuinely absent renders
   its clause in `--color-txt-3` with an em-free plain sentence
   (`Not observed on this turn.`).

## Visual treatment

**Of a piece with what exists.** One family: JetBrains Mono
(`styles/tokens.css --font-sans/--font-mono`, with `ss01` and slashed zero
already set). The canvas is charcoal (`--color-well` through
`--color-raised`), light comes from type, and the five muted pastels are the
entire accent vocabulary. The reveal introduces zero new colors and zero new
fonts; at canvas scale it earns exactly one new type size.

**Scale.** Existing canvas type runs 11–15px, which is card scale. The
reveal's number is the single permitted large moment:
`clamp(40px, 5vw, 72px)`, weight 600, `--color-accent` (so an active theme
recolors it: the theme system owns `--color-accent` by locked decision, and
the reveal inherits light/dark/tinted treatment from tokens alone, no
hardcoded hexes). The one line at M3 sets at `clamp(20px, 2.2vw, 32px)` in
`--color-txt`. Kickers, ledger, footnotes stay at the product's 11–13px so
the big number has something to be big against. Hierarchy: number, one line,
ledger rows, everything else quiet.

**Color roles, fixed:** sky = the harness's own instructions, lavender =
tool catalog, amber = what the user brought (hooks, CLAUDE.md, AGENTS.md),
sage = the user's words, rose = reserved for failure states only (a harness
whose turn errors renders its panel frame in `--color-rose` with the error
line, exactly like `canvas-exchange__error`). These mirror the rail
vocabulary the canvas already uses (`--color-agent-rail-*`), so the reveal
reads as native.

**Motion.** None that delays information. Panes arrive with whatever
`LayoutCanvas` already does on spawn; ledger rows may fade 120ms on mount,
and nothing else moves. The real animation is the terminal streaming next to
the panel.

## Deliberately not shown, and where it lives

- Block-level itemization, per-part char counts, previews: Inspector
  `SystemSection` / `ToolsSection` / `BlockRow`, reachable through the
  panel's `Open the full wire record` tab.
- Cache economics over time, pipeline before/after, overrides:
  `CharsLedger` and the breakpoint editor, Inspector origin. First-run makes
  no before/after claim because nothing was changed; there is no "saved"
  number anywhere in this design by construction.
- Raw bytes and transport diagnostics: `ExchangeDetail` tabs.
- Harness enablement and login remediation after first-run: the same
  `FirstRunScreen` where it already lives, ⌘K settings scope.

## Build notes (for the eventual brief; nothing here is new machinery)

- Reused as-is: `FirstRunScreen`, `harnessCard`, `useHarnessInventory`,
  `useLaunchReadiness`, `CapturedRunPane`, `ArkExchangeViewer` +
  `ExchangeBody` + `FirstRunReveal`, `PaneShell`, `LayoutCanvas`, `PaneFrame`,
  `planSingleRow`, `planGridFit`, `useCanvasStore.spawnPane/addCapturedRun`,
  `useCapturedRunStore.ensureRun`, `launchFirstRunHarnesses`,
  `fetchTurnContent`/`turnContentKey`, `contextTokens`, server owners
  `build_req_stats`, `build_res_stats`, `extract_user_prompt_text`,
  `get_turn_content`. Fourteen client components/symbols, zero duplicated.
- New: (1) the M0 lobby composition (a layout state over existing cards and
  copy, replacing the modal), (2) canvas-scale CSS for the existing
  `canvas-exchange__reveal-*` block plus the M3 one-line band, (3) the
  amber "context you brought" attribution, which needs the reminder and
  hook blocks distinguishable from the user's words; today `build_req_stats`
  folds all three into `messages_chars`, so this is one server-side stat
  extension on the existing owner, not a client-side parser. Three new
  things, each an extension of a named owner.
- Selection correctness is prerequisite and already diagnosed separately:
  the reveal must render the substantive turn
  (`extract_user_prompt_text` equals the delivered prompt), or every number
  above is the quota probe's.
