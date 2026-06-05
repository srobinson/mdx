---
title: Transport Matters first contact, the felt experience of overlay world
type: design
tags: [ux-design, transport-matters, first-run, overlay, onboarding]
summary: Ten interaction concepts for the first-run flow and the moment a user first sees and shapes what their harness sends
status: active
source: ux-designer
confidence: medium
created: 2026-08-03
updated: 2026-08-03
---

# TM first contact: interaction brainstorm (Mode 6)

Angle: interaction design and felt experience. What the user sees, in what
order, the moment of revelation, and the smallest overlay edit that makes the
value land inside ninety seconds.

## Grounding (read against code, not the plan)

`docs/plans/RUNTIME-SURFACING-PLAN.md` governs catalog/launch/eval, not first
run. The operative source for this moment is NOW.md Phase 1 plus what is
already on `feat/startup-gate`:

- **The two bands exist.** `FirstRunScreen.tsx` already renders either the
  blocking infrastructure gate (`InfrastructureGateProps`, server-owned
  remediation from `infrastructure_guidance.py`) or the non-blocking harness
  cards. The gate blocks; harness cards offer. Do not redesign that split.
- **The harness card voice is established.** `harnessCards.ts`: facts are
  text-first, evidence is dated ("Signed in · via Claude.ai · probed 2m ago"),
  unknown never renders as negative, and the footnote "It reports; it never
  gates" is already the product's tone. The overlay flow should inherit this
  voice, not invent one.
- **The overlay substrate exists but is session-resident.** `overrides/state.py`
  (`OverrideStore`, "lives in the addon process") with targets
  `tool:{name}`, `system:{index}`, `sampling:{field}`, `toolresult:{id}`,
  `msg:{m}:blk:{b}` (`overrides/targets.py`). Persistence and versioning are
  the new work; the edit vocabulary is not.
- **Token truth exists.** `breakpoint.py::PausedFlow.tokens_before` and the
  count_tokens re-audit give an authoritative before/after count. This is the
  currency of the whole reveal.
- **Canvas owns config-time overlay editing by charter** (canvas CLAUDE.md:
  "config-time, proactive overlay editing ahead of the request. No
  breakpoint."), but no overlay editor is shipped there yet. The inspector owns
  the interactive breakpoint. First contact happens in canvas.

Owner's rule, restated as the structural constraint: **first-run is a guided
pass over surfaces Settings owns permanently.** Every screen below must be
addressable from Settings on day 400, with first-run adding only sequence and
spotlight, never logic.

---

## The ninety-second script

The spine the concepts hang off. Times are targets, not promises.

| t | Beat | Surface |
|---|------|---------|
| 0:00 | Gate: store picker or all-green pass-through | InfrastructureSection (shipped) |
| 0:15 | Offer: "Claude Code found. Signed in via Claude.ai." Enable toggle | Harness card (shipped) |
| 0:25 | Doorway: "Want to see what Claude Code sends on your behalf?" | New affordance on the card (Concept 4) |
| 0:30 | Theater: sealed capture runs, progress narrated | Concept 5 |
| 0:50 | **The reveal: the Receipt** | Concept 1 |
| 1:10 | First edit: toggle one tool off, watch the count drop | Concept 3 |
| 1:30 | Landing: "Every future request carries this shape. Change it any time in Settings → Claude Code." | Concept 6 |

Everything after 0:25 is skippable, resumable, and reachable later from
Settings. The user who declines the doorway has a fully working product.

---

## Concept 1: The Receipt (the moment of revelation)

The first thing shown is never JSON. It is one proportional bar: the anatomy
of the first frame, segmented by provenance, measured in real tokens
(`tokens_before` machinery, not estimates).

```
Your first message to Claude Code was 12 words.
The wire carried 18,431 tokens.

█ you (41 tok)
████████████████████ tool schemas (11,204 tok · 18 tools)
████████ system prompt (5,890 tok · 9 sections)
██ injected reminders (1,296 tok)

                                  [ See what's inside ]
```

The headline is the product thesis in one sentence: *your words are a sliver
of what travels.* The user's own text is the smallest segment, rendered
first and in the accent color, because the emotional beat is recognition
("that's mine") followed by scale ("and that's everything else").

Copy rules for this screen:

- Numbers are real and dated, in the harness-card voice: "captured just now
  from Claude Code 2.1.7."
- No judgment words. Not "bloat", not "waste". The provider's payload is
  presented as fact. The user forms the opinion; the product supplies the
  measurement. This keeps the reveal trustworthy instead of salesy.
- Segment labels use the provenance vocabulary (Concept 7).

Why a bar and not a table or tree: the insight is proportional, and a bar is
the only form where proportion is pre-attentive. The table is one click away.

## Concept 2: Four altitudes, one surface

Progressive disclosure as a fixed ladder. Each altitude is a zoom on the same
receipt, never a different page:

1. **Bar** (Concept 1): proportion only.
2. **Category cards**: one card per segment. "Tool schemas · 11,204 tok · 18
   tools · largest: `str_replace_based_edit_tool` (2,890 tok)."
3. **Item list**: every tool, every system section, every reminder as a row
   with its own token cost, sorted descending. Each row carries its overlay
   affordance inline (Concept 3).
4. **Raw text**: the actual bytes, syntax-lit, reached only by explicit "view
   raw" on a single item, never as a page of everything.

The ladder maps one-to-one onto the override target grammar that already
exists: category ≈ kind, item ≈ `tool:{name}` / `system:{index}`. The UI
altitude at which the user acts is exactly the granularity at which the
overlay is stored. No translation layer, no invented model.

Rule: the first session starts at altitude 1 and can reach 4; Settings
remembers the altitude the user last used per harness.

## Concept 3: The first edit is a switch, not a text field

The smallest overlay edit that makes value land immediately: **turn off one
tool schema.** At altitude 3, every tool row is:

```
◉  WebSearch                    412 tok    [on]
◉  NotebookEdit               1,108 tok    [on]   ← never used in your sessions
```

One toggle. The moment it flips:

- The receipt bar animates: the segment shrinks, the total re-counts via the
  real count_tokens path, and the delta is stated in future tense:
  **"Next request: 17,323 tokens (−1,108)."**
- A revert affordance appears in place, not in a toast.

Why a tool toggle and not a system-prompt edit as the first act:

- **Reversible and legible.** On/off is auditable at a glance; a text edit
  requires reading comprehension to trust.
- **Zero authorship burden.** Ninety seconds in, nobody wants to write prose
  into a system prompt. Flipping a switch is a decision, not a composition.
- **Already representable.** `tool:{name}` is a shipped override target.

System prompt editing stays fully available at altitude 3/4 but is the second
lesson, not the first. The first-run pass may highlight one candidate toggle
(a tool with a large schema) as a suggestion chip, phrased as an offer:
"NotebookEdit costs 1,108 tokens per request. Turn it off? You can bring it
back any time." Suggested, never pre-flipped.

## Concept 4: Offer, then doorway (the second yes)

The harness card already carries the first yes (Enable). The doorway to
overlay world is a second, visually subordinate affordance that appears only
on an enabled, installed harness:

```
┌──────────────────────────────────────────────┐
│ Claude Code                        [Enabled] │
│ Detected      Installed · 2.1.7              │
│ Authenticated Signed in · via Claude.ai      │
│               · probed just now              │
│ ────────────────────────────────────────────│
│ Manage what Claude Code sends →              │
│ System prompt, tools, and reminders travel   │
│ with every request. See them, shape them.    │
└──────────────────────────────────────────────┘
```

Design intent: the doorway is discovered, not modal. It never interrupts the
gate flow, never counts as an onboarding "step", and renders identically in
Settings forever. Declining is not an event; there is nothing to dismiss.

The two-line subcopy is the entire pitch and must stay under twenty words.
It names the invisible layer in plain nouns before the user has seen it, so
the reveal (Concept 1) confirms an expectation instead of ambushing.

## Concept 5: Capture as theater

Stage 2 captures the first-frame baseline under `--yolo` in a sealed run with
no walk. That mechanism is the product's core trick, so narrate it instead of
hiding it behind a spinner:

```
Recording a baseline …
  ✓ Launched Claude Code 2.1.7 in a sealed, throwaway home
  ✓ Captured its first outbound request before it left
  ◌ Counting tokens
Nothing was sent to Anthropic on your behalf yet.
```

Three checklist lines, each stated as a fact when done, in the dated-evidence
voice. The last line matters most: this is the moment the user learns TM sits
*in front of* the wire, and the trust claim ("nothing left yet") is checkable
against the product's own architecture. Fifteen to twenty seconds of honest
process beats an instant screen the user cannot account for.

This screen doubles as the returning-user re-baseline surface unchanged,
which keeps the settings-owns-it rule intact.

## Concept 6: A guide rail, not a wizard

Concrete shape for the owner's rule. First-run renders the ordinary Settings
sections (Store, Harnesses, per-harness Wire) with a slim rail:

```
● Store          ready
● Harnesses      Claude Code enabled
○ Wire           baseline captured, no overlays yet
```

Every rail state is **derived from stored facts** (readiness checks, harness
enablement, baseline existence, overlay count), never from a step counter.
Consequences that fall out for free:

- Re-entrant: DB gone on run fifty lands you on the same rail with Store
  regressed to attention state, exactly the shipped gate behavior.
- Skippable: the rail is a report, so there is no "exit wizard" state to
  design.
- Idempotent copy: each section's copy describes present state ("baseline
  captured 3d ago") and never "step 2 of 4".

The rail is the *only* first-run-specific chrome. It can persist quietly in
Settings as a health summary, which means even the rail obeys the rule.

## Concept 7: Provenance vocabulary (three voices on the wire)

To make the invisible legible, name the layers once and use the names
everywhere: receipt segments, item rows, raw view gutters, diff briefings.

| Voice | Label | Meaning |
|-------|-------|---------|
| You | "You wrote" | Prompt text the human typed |
| Harness | "Claude Code adds" | System prompt, tool schemas, injected reminders |
| History | "Carried forward" | Replayed context, tool results, prior turns |

Each voice gets one hue used only for provenance (house rule from
`harnessCards.ts` holds: text carries meaning, color decorates). In the raw
view the gutter is striped by voice, so even altitude 4 reads as annotated
evidence rather than a JSON dump.

This vocabulary is also the future contract for wire-versus-transcript diff:
"Claude Code adds" is precisely the wire-only content the CLI hides, so the
first-run naming seeds the mental model the diff product will cash in later.

## Concept 8: The drift briefing (returning users)

Returning user, stored baseline, current first frame differs: lead with a
briefing, not a diff view.

```
Claude Code updated what it sends
2.1.7 → 2.2.0 since your baseline (11d ago)

  System prompt   3 sections changed   +412 tok
  Tools           1 added (Glob)       +388 tok
  Reminders       unchanged

Your overlays still apply cleanly.        [ Review changes ]  [ Accept new baseline ]
```

The last line is the critical one. Overlays are edits against a harness
version (NOW.md: "an overlay is an edit to what a specific harness version
sends"), so the briefing must always state whether each overlay still binds:
**applies cleanly / target moved / target gone.** A `tool:NotebookEdit`
toggle survives a version bump trivially; a `system:{index}` edit may not.
Surfacing that verdict here, in plain state words, is what makes persistent
overlays trustworthy across updates. "Review changes" opens the receipt in
diff mode with the three-voice gutter.

## Concept 9: Plan currency (headroom framing)

The brief's "here is your plan headroom" beat. Token counts are honest but
abstract; plans are the unit users actually feel. Once the user states their
plan (optional, layered on top per NOW.md), savings render twice:

> Next request: 17,323 tokens (−1,108, about 6% of every request)

and on the harness Wire settings page, cumulative and dated:

> Overlays trimmed ~412k tokens across 372 requests this week.

Never project money or exact rate-limit math (TM cannot verify provider
accounting; a wrong promise poisons the trust the receipt earned). Percent-of-
request and measured cumulative counts are claims TM can back with its own
captures. If no plan is stated, the percent line stands alone and nothing
nags.

## Concept 10: Trust grammar for a layer that edits the wire

The overlay is the first feature that *changes* what leaves the machine, so
the interaction grammar must telegraph safety:

- **Tense split.** Overlays speak in future tense about the next request
  ("Next request will carry…"); audits and receipts speak in past tense with
  dates ("Sent 14:03, 17,323 tok"). The tense alone tells the user whether
  they are shaping or reviewing.
- **Original always adjacent.** Every edited item renders original and
  effective side by side or via one hover; revert is per-item, in place.
- **One master switch.** `OverrideStore.set_enabled` already models it:
  "Send everything unmodified" as a single prominent toggle per harness.
  The escape hatch is the reason people dare to experiment.
- **Nothing silent.** Any turn where overlays changed the outbound request is
  badged in run history with the delta, tying config-time edits to run-time
  evidence via the shipped `request_diff.request_unchanged` seam.

---

## Open questions for the owner

1. **Where does the doorway live on macOS Claude first-run before login?**
   The card can show "Not signed in"; the sealed capture needs a credential.
   Proposed: doorway renders disabled with the same dated-evidence copy
   ("Sign in to record a baseline"), wired to the login driver seam.
2. **Suggestion chips (Concept 3): does TM ever rank tools by observed usage**
   ("never used in your sessions"), which needs session history, or only by
   schema cost on a fresh install? Fresh install has no usage evidence, so
   day-one chips can only rank by size.
3. **Does the first-run reveal show reminders (`msg` blocks / injected
   content) as editable, or read-only in v1?** Recommend read-only at first
   contact; toggling tools and viewing everything is enough for the first
   session, and reminder edits have the highest surprise risk.

## What I would cut first

Concept 9 (plan currency) and the suggestion chip in Concept 3. The receipt,
the tool toggle with a live recount, and the guide rail are the irreducible
core; they alone deliver the revelation and the first edit inside the script.
