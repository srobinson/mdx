# 574: pane capture verb: an agent cannot see a blocked run's screen, and the snapshot route already returns it

URL: https://github.com/littleorgans/transport-matters/issues/574
State: open
Labels: enhancement
Updated: 2026-09-04T14:32:02Z

## Summary

An agent driving the control plane cannot see what a pane is showing. When a run misbehaves in a
way the conversation and roster do not capture, there is no verb that answers "what is on the
screen". Something equivalent to `tmux capture-pane`, with a scrollback bound.

The capture path itself is built and correct. Verified end to end on 2026-09-02 against a live
blocked run: the snapshot route returns the exact screen. Only the verb is missing.

## Verified reproduction (2026-09-02, preview, main at `8a55fb41`)

Codex released `0.152.1` while `0.152.0` was installed, which arms the interactive update gate.
Three launches, three outcomes:

| launch | result |
| --- | --- |
| MCP `launch` with agent + `first_prompt` | ran normally, replied, 4 exchanges captured |
| MCP `launch` NATIVE (no agent) + `first_prompt` | ran normally, captured |
| launch with no initial prompt (⌘K, terminal, MCP) | parked on the update gate, never takes a turn |

The discriminator is the initial prompt, not the version cache. Every MCP launch passes a prompt
in argv (`_initial_prompt_argv`), so codex goes straight into the turn and never renders the gate.
⌘K and a bare terminal start the TUI with nothing to do, which is where it renders. Ruled out:
a NATIVE run's child home receives a copy of `~/.codex/version.json` already showing `0.152.1`
available at startup and still does not gate, so a populated version cache is not the trigger.

What the blocked run (`ef008927`) looked like on each surface:

- `roster`: `state: "starting"`, `needs_you: null`, `last_turn_at: null`. Indefinitely.
- The run's own supervised gateway (`:61063`): healthy, `GET /v1/runs` returns `{"items":[]}`,
  and `terminal-snapshot` returns `run_not_found`.
- The canvas gateway (`:58244`): holds the run, and `terminal-snapshot` returns it exactly.

```
GET /v1/runs/ef008927-8a12-47cf-9fcf-939a15ecb813/terminal-snapshot?owner=local
{"cols":107,"rows":49,"truncated":false,"text":
"  ✨  Update available! 0.152.0 -> 0.152.1

  Release notes: https://github.com/openai/codex/releases/latest

› 1. Update now (runs `npm install -g @openai/codex`)
  2. Skip
  3. Skip until next version

  Press enter to continue"}
```

Finding it required scanning every listening port for a gateway that knew the run id. Each run
supervises its own gateway, but the one that holds the terminal is the canvas gateway. No agent
should have to discover that.

## Why

Three things this reproduction makes concrete, beyond the original 2026-09-01 defects (#572, a
codex launch dying on an interactive update prompt; and a pane still displaying a run the control
plane considered gone):

1. **The one existing path to a snapshot is unsafe on exactly this run.** `wait_for_reply`
   populates `pane`, but only alongside a delivery. Prompting a run parked on the update gate
   types into the gate, where enter selects **1. Update now**, running `npm install -g
   @openai/codex` unattended and swapping the harness binary under TM mid-session. So the agent
   must either stay blind or risk an unattended global install.
2. **`needs_you` is null on a run that literally needs you.** A blocked run is indistinguishable
   from a slow-starting one. Whatever populates that field should read the same signal the verb
   exposes.
3. **This is the release-day failure mode.** Capture survived the codex release intact; both
   prompted runs captured normally. What broke was a run that never starts and cannot say why.
   That makes the verb the thing standing between an operator and a silent stall on the day a
   harness ships. See #519, which predicted a release-day capture failure and did not get one.

Neither the conversation projection nor the activity stream carries harness UI: modals, update
prompts, auth challenges, and errors printed outside the transcript. That is exactly the class of
failure where an agent gets stuck and cannot report why.

## Most of this already exists

- `TerminalEmulator.textSnapshot(maxChars)` (`packages/runtime/src/service/TerminalEmulator.ts:323`)
  returns `{ text, cols, rows, truncated }` and already takes a character bound.
- Gateway serves it at `GET /runs/:runId/terminal-snapshot`
  (`packages/runtime/src/server/runtimeRouter.ts:197`).
- The control plane already consumes it: `read_terminal_snapshot`
  (`api/src/transport_matters/api/v1/controlplane_gateway_reads.py:128`), called from
  `delivery_wait.py:531` to populate the `pane` field on a wait result.

So the work is a service verb plus the two skins, not new capture machinery.

## Shape

- `pane(run_id, max_chars?)` returning the snapshot as it already exists, with the server cap
  applied the way observe responses are capped.
- Observer grant is sufficient: it is a read.
- The verb must resolve the gateway that owns the terminal. The reproduction above shows a run
  registered on the canvas gateway and absent from its own supervised gateway, so a caller
  guessing wrong gets `run_not_found` on a live run.
- Worth deciding whether it should also be reachable for a run that has exited, since that is the
  case that motivated it. The emulator is disposed on exit
  (`TerminalEmulator.ts:341`), so the last screen may need to be retained at teardown for the
  post-mortem case to work at all.


## Comment by srobinson at 2026-09-04T14:32:02Z (updated 2026-09-04T14:32:02Z)

https://github.com/littleorgans/transport-matters/issues/574#issuecomment-5541946941

## Consider an `isPromptBufferDirty` predicate on the same capture

A second consumer for this capture, from the #616 investigation.

#616 is fusion: text left in a composer joins the next prompt. The remedy being taken is a blind
unconditional clear written immediately before every prompt, in the same PTY write as the
bracketed paste. It needs no proof, because an unobserved clear degrades to today's behaviour
rather than to something worse. It is deliberately the KISS answer.

What it cannot do is answer the question the fix actually wants asked: **is there anything in the
composer right now?** Three separate research agents converged on the same wall. From the
runtime's current PTY boundary, proving a composer is empty means either a harness supplied
semantic event, which none of the three provides reliably, or reconstructing the rendered screen
and identifying the composer region. The first does not exist. The second is what this issue is
already building.

The signals that look like acknowledgements are not. Claude's `render_acknowledged` proves a
render cycle happened, not what it drew. Grok's `Input cleared · ctrl+z to undo` is an ephemeral
tip, capped at three displays per session and suppressed for small collapses. Codex's empty
placeholder is the strongest of the three and still requires a completed differential redraw plus
confidence that the ordinary composer is the visible surface.

So the predicate belongs here rather than in the runtime's escape stream parsing. The snapshot
route already returns the exact screen, as this issue's reproduction demonstrates.

**What it would take beyond the verb.** The verb returns a screen. A dirty predicate needs the
composer's location and extent within that screen, per harness, plus the cursor position. That is
per harness UI knowledge, which is real work and is why this is a follow on rather than a
prerequisite. `TerminalEmulator` already performs robust ANSI parsing, but its public snapshots do
not expose cursor or region state, so the parsing is not the missing part.

**What it would buy.**

- #616 could verify its clear rather than assume it, and could skip the write entirely when the
  composer is already empty.
- Rollback on failure becomes possible at all. It is rejected today specifically because a
  rollback that cannot confirm its own effect is a blind write into a possibly running harness.
- The `needs_you` gap this issue already names has the same shape: a predicate over the captured
  screen rather than over the transcript.

Not a dependency for #616, which ships without it. Recorded here so the verb's design leaves room
for a predicate over the same capture rather than only a text blob for a human to read.


## Sub issues
[]
