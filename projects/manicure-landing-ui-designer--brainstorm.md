---
title: "Manicure Landing Page: UI Designer Brainstorm"
project: manicure
lens: ui-designer
author: design-ui-designer (helioy-bus)
date: 2026-04-14
status: draft
audience: Stuart (review)
related:
  - ~/.mdx/projects/manicure-landing-visual-storyteller--brainstorm.md
  - ~/.mdx/projects/manicure.md
---

# Manicure Landing Page: UI Designer Brainstorm

The storyteller pass defined the arc (eight scenes, the Stack as protagonist, the Scene 5 reveal as pivot). This pass defines the register: the visual language, type stack, color semantics, density, and motion that carry the story.

The existing codebase already commits to a specific aesthetic: mono-only JetBrains Mono, near-black canvas, desaturated accents, zero radii, noise grain, and a fluorescent ignition motif. That is not an accident. It is already inside the register this brief asks for. My work below names that register, tightens it, and extends it into the scenes the storyteller scoped.

---

## 1. Reference board

Six products to study. One line each on the exact artifact to borrow.

**Warp.dev.** Mono-confident landing where the terminal carries the hero beat. Borrow: the willingness to let a mono typeface carry 60px display headlines without an editorial sans propping it up. Reject: their high-saturation glow; the Manicure page is calmer.

**Val Town.** Code blocks treated as editorial content. Borrow: inline rendered JSON and payload snippets typeset with the same care as body copy, ranged-left. The payload is the argument.

**Linear (pre-2024 and current quiet sections).** Patience with one idea per scroll, whitespace as punctuation, muted type hierarchy. Borrow: the permission to let a single paragraph fill a viewport. Reject: their marketing chrome (feature tiles, gradient halos).

**Panic.com and Nova landing.** Craft detail in every vertical pixel; hand-set type; obsessive pixel care. Borrow: the respect-the-reader tone and the willingness to ship a single illustration where others ship twelve.

**Observable Framework docs.** Notebook-as-page, inline data visualizations as the content. Borrow: charts and measurements typeset at body-text register, carrying the prose forward rather than decorating it. This is the mental model for the Stack.

**iA Writer.** Editorial commitment, serif accents used surgically, confidence to be mostly text. Borrow: the footnote and epigraph register for optional editorial pullquotes later in the scroll. This unlocks a single serif accent without softening the mono backbone.

---

## 2. Visual register: Diagnostic Instrument

**Committed pick: Diagnostic Instrument.**

The landing reads as a field manual for an instrument that happens to be running on the same page. The instrument is the content. The page is its frame. Every surface, type choice, and color decision earns its place by referencing measurement, inspection, or calibration.

Why this survives the education-not-sales constraint:

- Instruments do not sell themselves. They are picked up by practitioners who already suspect a problem. The register invites suspicion instead of excitement.
- Field manuals are written for people who know their domain. The voice is precise, the illustrations are technical, the numbers are real. The audience recognizes this tone because they already read manuals daily (man pages, Anthropic API docs, observability dashboards).
- Instruments render evidence. The product's job is to render a payload. The page can show the instrument rendering the payload as its primary content without staging a demo. The surface is the argument.

What Diagnostic Instrument rules out by construction:
- Lifestyle imagery.
- Hero photography of developers.
- Testimonial cards.
- Feature grids with icons.
- Gradient hero backgrounds.
- Faux-3D product mockups.

Register adjacents considered and rejected:
- **Editorial terminal** (close, but gives up density; the page has a job heavier than a longform essay).
- **Forensic lab** (close, leans into spectacle; "crime scene" stages the visitor as detective rather than practitioner).
- **Broadcasting console** (real-time dashboards as hero; too noisy for Scene 1's patience).
- **Plain documentation** (too neutral; gives up the emotional charge the storyteller built).

Diagnostic Instrument sits between editorial terminal and forensic lab with the calibration of plain documentation. That sweet spot is already implied by the current codebase.

---

## 3. Typography stack

Current state: JetBrains Mono is the single font family for everything, sans and mono both aliased to it. Radii are zero. Font features `ss01` and `zero` are active.

This is a bold choice. Keep it.

### Stack

**Primary (headlines, body, UI, code):** JetBrains Mono 400 and 500.

Keep the single-family commitment. A mono-only landing is the clearest possible signal to a developer audience that the page was built by someone who respects their register. The minute a sans shows up as primary body, the page reads as a dev-tool marketing site. Mono-only keeps it an instrument manual.

**Upgrade path (optional, Stuart's call):** Berkeley Mono.

Berkeley has more editorial character than JetBrains, slightly warmer, better optical sizing at 14-20px body, and distinguishes the page from every other dev tool reaching for JetBrains by default. It ships as a paid license. If the budget is not right for v1, JetBrains is the correct default.

**Editorial accent (optional, used surgically):** Source Serif 4, italic, at pullquotes and epigraphs only.

A single serif voice at 14-16px italic, reserved for margin notes and in-line epigraphs that stand outside the instrument's telemetry voice. The contrast signals "this is the author speaking" without breaking the mono frame. If introduced, it appears at most twice across the entire page (Scene 4 caption, Scene 8 close-quote). Any third use erodes the distinction.

If Stuart prefers zero serif, that is also correct. The page does not need it. The decision is a taste call.

### Rules

| Role | Face | Size (desktop) | Weight | Leading | Tracking |
| --- | --- | --- | --- | --- | --- |
| Display (Scene titles, Hero) | JetBrains Mono | 48 to 72px | 500 | 1.05 | -0.015em |
| Section headlines | JetBrains Mono | 28 to 36px | 500 | 1.12 | -0.01em |
| Body | JetBrains Mono | 16 to 18px | 400 | 1.55 | 0 |
| Payload code blocks | JetBrains Mono | 13 to 14px | 400 | 1.45 | 0, tabular-nums on |
| Byte and token counters | JetBrains Mono | 13 to 16px | 500 | 1 | 0, tabular-nums, slashed zero |
| Labels and chips | JetBrains Mono | 11px | 500 | 1 | 0.14em, uppercase |
| Annotations (margin notes) | JetBrains Mono | 12px | 400 | 1.4 | 0, italic optional |
| Editorial pullquote (rare) | Source Serif 4 | 16px italic | 400 | 1.6 | 0 |

**Maximum measure:** 72ch for body. Payload views break out to full viewport width.

**Numeric display rule:** all numbers on the page route through tabular-nums and slashed-zero, even inline. Numbers are protagonists. They must align across turns and across decrements in Scene 5.

---

## 4. Color palette

Current tokens (keep all, retain names):

**Neutrals (structure):**
- `well` #040408. Deep backing behind raised panels, rarely visible.
- `canvas` #08080c. Primary background.
- `surface` #0e0e14. Cards, Stack blocks.
- `raised` #16161e. Tamper panel, elevated.
- `hover` #1e1e2a. Interaction feedback.

**Edges:**
- `edge` #23232f. Panel borders.
- `edge-strong` #2c2c3a. Emphasized divisions.
- `edge-subtle` #16161e. Hairlines that read as structure.

**Text:**
- `txt` #dcdce4. Primary.
- `txt-2` #9292a8. Secondary, labels inside prose.
- `txt-3` #6e6e82. Annotations, byline metadata.
- `label` #7a7a92. Uppercase chip text.

### Accent semantics (new rigor, same hues)

The palette already ships six accents. Each gets an assigned job. Overlap is forbidden.

| Hue | Token | Job | Where it appears |
| --- | --- | --- | --- |
| Sky | `sky` #7ab3d4 | The visitor's intent. What you typed. The sliver of payload that is you. | "Hello" in Hero subline. User message stripe in the Stack. Primary install CTA. |
| Sage | `sage` #7ec9a0 | The kept state. Anything that survives curation. | Code block syntax, `manicure start`, overlay-active badges, bottom CTA. |
| Amber | `amber` #d4b07e | Token density. Mass. Quantity. Never emotional, always numeric. | Byte counters, token bars, the live payload pilot light. |
| Rose | `rose` #d4879c | Tamper and edit. "You are about to mutate this." | Scene 5 toggle strikethrough, delete affordances, strip-tool button. |
| Lavender | `lavender` #a88bda | Annotation. Margin notes. "Last referenced." | Scene 3 metadata tags, overlay descriptions, author bylines. |
| Teal | `teal` #6ebcb0 | Overlays. Shareable curation. Second-party provenance. | Scene 7 overlay cards, active-overlay edge bar. |

### Accent economy

**Maximum two accent hues per viewport.** This is the load-bearing rule. If a scroll features sky and amber, sage stays off. If Scene 5 is rose and amber (tamper plus counter), everything else is neutral.

Reason: six accents at once reads as a brand guideline spread. Two accents at once reads as an instrument highlighting signal. The page needs the latter.

### Backgrounds

Keep the near-black canvas. Do not lighten to gray. The current `#08080c` with 1.5% SVG noise overlay is exactly the correct baseline. Lighter backgrounds push the register toward "dev tool SaaS." Darker (pure black) kills the warmth that mono-on-dark needs.

### Selection and focus

Keep sky-tinted selection (`rgba(122,179,212,0.25)`). Add one detail: focus rings on interactive elements (Scene 5 toggles, overlay install buttons) should be 2px sage outline, 2px offset, sharp corners. Accessibility and instrument-panel feel in the same motion.

---

## 5. Hero treatment (first 100vh)

The current Hero already lands the right hook. Keep the copy, keep the flicker, and layer one additional diagnostic element that persists across the rest of the page.

### Layout (desktop 1440px)

Centered content column, max-width 900px, sitting 40% down the viewport.

**Top:** chip reads `context control plane` in uppercase 11px, sky border. No change.

**Headline:** "See what your coding agent ships." JetBrains Mono 48px/56px responsive, 500 weight, tight leading. Delivered via FlickerText with `segmentSize={3}`. No change.

**Subline:** the existing 285,000 token paragraph. Keep. The `"Hello"` in sky is correct by the accent rule above (visitor's intent).

**Primary action group:**
- Left: `card-flush` with `$ manicure start` in sage mono. Keep.
- Right: replace the current "Get started" button with a muted text link: `read the payload →` in sky, 14px, underline-on-hover.

Rationale for the button change: "Get started" is sales register. The page's Scene 1 job is to invite reading before installing. The install CTA lives at Scene 8. A text link in place of a solid button keeps Scene 1 in diagnostic voice and defers the commit to the end of the scroll.

**Hook line:** "One command. Spawns the proxy, launches Claude, opens the canvas." Keep.

### Persistent telemetry (new)

**Fixed HUD, top-right of viewport, 11px mono, always visible:**

```
session 0 / turn 0 / tokens 0
```

On page load, all three read blank dashes. As the visitor scrolls into Scene 2, the HUD animates to:

```
session demo / turn 1 / tokens 47,388
```

Tokens count up mechanically (tabular-nums, one frame per 1000 tokens) to match the rendered Stack's total. By Scene 5, when the visitor toggles a block, the HUD counter decrements in sync with the Stack change.

This HUD is the page's pilot light. It signals that a diagnostic instrument is running throughout the whole scroll. It stays non-interactive and always muted (txt-3 with amber number accent).

**Fixed measurement rule, left edge of content, desktop only:**

A 1px edge-color vertical rule at the left content edge with tiny ruler ticks every 100px of scroll distance and numeric labels (100, 200, 300). The page is measured. This is a quiet visual that rewards close reading and codes the whole experience as "page-as-instrument."

Do not add this on mobile. It dies at narrow widths.

### Live payload strip (new)

Below the Hero fold, spanning full viewport width, 32px tall, a diagnostic strip reads:

```
LIVE PAYLOAD    [■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■□□□□]  47,388 tokens / 200k window
```

The strip uses label styling on the left, a monospaced block-character bar in the center (amber for used tokens, edge-subtle for remaining), and the counter on the right in amber tabular-nums.

A scanline sweeps across the strip every 6 seconds using the existing `@keyframes scanline`. The sweep is clinical. No easing.

This strip is the connective tissue between Hero (Scene 1) and Scene 2. It says: the instrument is already running. What you are about to read is what it sees.

### Ambient elements

Keep the subtle radial sky glow at 4% opacity behind the headline. Keep the noise texture. Drop nothing. The existing Hero is close to correct; it needs the HUD, the ruler ticks, and the payload strip to connect to the rest of the page.

---

## 6. The "surface" view: single hero illustration specification

A single canvas mock that could stand in for the whole brand. Designer-ready description below. Render at 1440x900.

### Canvas

- Background: `canvas` #08080c with noise texture at 1.5% opacity.
- Full-bleed. No macOS window chrome. No rounded corners. No drop shadows around the canvas. The instrument presents as a real panel. Faux device chrome breaks the illusion.

### Top bar: 48px, border-bottom 1px `edge`

- Left (16px padding): `manicure` wordmark, JetBrains Mono 14px 500, `txt`.
- Center (centered): breadcrumb in 12px mono, `txt-3`: `claude-code / agent-session-3847 / turn 12/∞`.
- Right (16px padding): token counter in two parts. Small label `tokens` in 11px uppercase `label`. Number `47,388 / 200,000` in JetBrains Mono 14px 500, amber on the used value, `txt-3` on the denominator. Below, a 3px-high mini-bar shows 23.7% amber fill.

### Body: three-column grid

- **Column widths:** 30% / 40% / 30%.
- **Gutters:** 1px `edge` vertical dividers between columns. No other gutter padding.

**Column 1: Block inventory (30%)**

A vertical scroll of payload blocks, top to bottom in order of ship:

1. `SYSTEM PROMPT`: 11px uppercase `label`, 4.8k tokens right-aligned mono amber. Two preview lines of `txt-2` 12px. Green dot left of title (kept).
2. `TOOL DEFINITIONS (47)`: 11.2k tokens. Preview: "read, write, glob, grep, edit…" Gray dot (kept, unused).
3. `MCP SERVER: postgres`: 2.8k tokens. Gray dot.
4. `MCP SERVER: linear`: 1.9k tokens. Gray dot.
5. `MCP SERVER: supabase`: 3.4k tokens. Gray dot.
6. `SKILLS (12)`: 6.1k tokens. Gray dot.
7. `CONVERSATION`: 8.9k tokens. Green dot.
8. `CURRENT USER MESSAGE`: 184 tokens. Sky left-stripe, 2px wide, extending full block height.

Each block is a 72px card with 8px padding, separated by 1px `edge-subtle` hairlines. Selected block (#2 in this mock) has a 1px `sky` left border instead of the usual edge.

Scrollbar: 6px, `edge-strong` thumb, no track. Already defined.

**Column 2: Expanded block (40%)**

The selected block from Column 1 rendered as raw JSON with syntax highlighting:

```
{
  "tools": [
    { "name": "read",  "description": "Read a file…",  "tokens": 248 },
    { "name": "write", "description": "Write a file…", "tokens": 264 },
    { "name": "glob",  "description": "Find files by pattern…", "tokens": 198 },
    …
  ]
}
```

- Gutter with line numbers at `txt-3` 11px, tabular.
- Keys: `sky` 13px 400.
- Strings: `txt` 13px 400.
- Numbers: `amber` 13px 500 tabular.
- Punctuation: `txt-3`.
- On hover over a tool row, the row gets `hover` background and a right-side annotation fades in: `last call: never this session`, lavender 11px italic.

Header of column 2: 11px `label` reads `EXPANDED BLOCK ·  47 TOOL DEFINITIONS · 11,172 TOKENS`. Right of the header, a tiny toggle row: `[strip]  [keep]  [rewrite]` with the current state (`keep`) in sage.

**Column 3: Tamper panel (30%, `raised` background)**

Elevated panel. Subtle inset highlights top and bottom.

Top: 11px `label` reads `TAMPER · TURN 12`.

Three groups, each with a 1px `edge-subtle` hairline above:

1. **Strip unused tools.** Row of 47 tiny toggles as a single horizontal strip, 4px per toggle, shown as small `sage` fills for kept and `edge` for stripped. Below, a summary: `12 of 47 kept · saves 8,842 tokens`.
2. **Rewrite system prompt.** Single row with an editor affordance. `rose` accent on the pencil icon.
3. **Skip this block.** Three rows corresponding to the three MCP servers above. Checkboxes on the left, block name in the middle, token savings on the right in `amber`.

Bottom of panel: two buttons side-by-side, full width of column.
- Primary: `forward (edited)`. 1px `sage` border, transparent fill, `sage` text, JetBrains Mono 13px 500. 40px tall.
- Ghost: `send as-is`. 1px `edge-strong` border, transparent fill, `txt-2` text.

Above the buttons, a live delta line: `pending edits: strip 35 tools · strip 2 MCP servers · saves 14,227 tokens`, `rose` 12px tabular.

### Accent behavior (the key payoff)

The toggle state in column 3 drives visible state in column 1. When the viewer toggles off a tool set, the corresponding row in column 1 gets:

- Left dot flips from gray to `rose`.
- Text across the row drops to 40% opacity.
- A 1px `rose` strikethrough traverses the token number.
- The top-bar token counter decrements by the delta.

This is the instrument working. A designer mocking the still frame should capture it at the moment of a toggle mid-decrement, showing one row already struck through, another fading.

---

## 7. Density rules

The page moves through three density modes in a deliberate arc:

**Editorial (Scenes 1 and 2).** 72ch body, 60 to 70% whitespace on desktop, one idea per 100vh. The visitor is reading. The page is patient. Type does not compete with figures.

**Diagnostic (Scenes 3 through 5).** The Stack occupies 40 to 50% of viewport width centered, annotated with measurements in the right margin, `lavender` metadata tags. Whitespace drops to 30 to 40%. The visitor is auditing. The page is an inspection.

**Reference (Scenes 6 through 8).** The Canvas from §6 breaks out full-bleed. Multi-column tabular data acceptable. Whitespace drops to 20 to 30%. The visitor is orienting. The page is a manual.

Why the ramp: the storyteller's spine goes from ignorance to agency to orientation. Density should echo that journey. A page that opens at reference density is a product pitch. A page that never reaches reference density is a magazine article. The Manicure page needs to be both, in order.

**Column rule:** never more than three columns simultaneously. Three is the Stack / JSON / tamper grid of the Canvas and it is the ceiling. Four-column grids read as marketing tiles.

**Whitespace rule:** vertical rhythm is an 8px grid. Section spacing is 128px on desktop (16 units), 96px on tablet, 64px on mobile.

---

## 8. Motion

### Two motion cues (earn their presence)

**1. Fluorescent ignition** (already shipping).

Text flickers on like a sodium lamp catching. Three or four false starts before it holds, a brief overshoot in brightness, then settles. The `useFluorescent` hook in `src/animations/useFluorescent.ts` is already correctly tuned. Subtle profile for all scene-entry titles. Normal profile reserved for the Hero headline only.

Keep the reduced-motion path that forces `opacity: 1` for `prefers-reduced-motion`. Already implemented.

**Constraint:** once a text element ignites, it stays lit. Do not re-ignite on subsequent scroll passes. Ignition is a one-time event per element.

**2. Mechanical token counter** (new, load-bearing for Scene 5).

When the visitor toggles a block in the Scene 5 Stack, the token counter decrements mechanically, one frame per roughly 200 tokens, linear easing, no overshoot. Total duration for a 12,000-token decrement is 600ms. The counter feels like a flip-clock or a graduated cylinder draining.

This is the one moment of physical feedback on the entire page. It must land hard. Do not soften it with easing. Do not add a number-morphing tween. The decrement should look like an instrument settling.

Apply to: top-bar token counter in the Canvas, the Hero HUD, the live payload strip. All three update together.

### Two anti-patterns (explicitly rejected)

**1. No parallax scroll.** The Stack is the page's anchor. Layering it at a different scroll velocity breaks the illusion that it is a real payload inspection. Everything scrolls at content speed.

**2. No fade-in-on-scroll as ambient motion.** If body paragraphs fade in when they cross the viewport, the ignition cue loses its function. The fluorescent flicker is reserved for titles and scene-entry elements. Body text is visible as it arrives.

### Additional motion craft

- **Scanline** (already defined) sweeps across the Live Payload strip every 6 seconds and across the Stack whenever a new sample ingests (Scene 2 intro, Scene 5 after a toggle). Nowhere else.
- **Glow-pulse** (already defined) applies to exactly one element: the amber pilot light on the Live Payload strip. Nothing else pulses.
- **Hover** on payload rows uses a 100ms linear fill from `surface` to `hover`. No transform, no scale.
- **Toggle click** in Scene 5 fires a 120ms `opacity` and `transform: translateX(-4px)` on the block as it slides out, then a 200ms `height` collapse on the container. Two-stage motion. Physical.

---

## 9. Anti-look

Three aesthetic tropes explicitly rejected. Each undermines the register by construction.

**1. Neon phosphor-green terminal cliche.**

Any saturated green-on-black (`#00ff66`, the Matrix palette) reads as "hacker aesthetic," which is sales cosplay for the audience we want. Developers who have been using Claude Code for months recognize that palette as someone cosplaying their lifestyle. The existing `sage` at #7ec9a0 is correct because it is desaturated and warm; the rejection is for anything brighter.

**2. Glassmorphism, blur backgrounds, aurora gradients.**

The product's entire premise is seeing clearly. Atmospheric blur is a semiotic contradiction. The page should have zero `backdrop-filter: blur`. No layered translucent cards. No bokeh. No aurora hero backgrounds. The visual field is in focus or it is in shadow. There is no middle state.

**3. Screenshot-in-a-browser-frame hero imagery.**

The cliche macOS window chrome or Chrome browser frame surrounding a product screenshot is sales register. The Manicure Canvas should bleed full viewport width with no faux device chrome. The instrument sits inside the page; it does not claim to be a separate app displayed through a window.

### Bonus rejections specific to this audience

**4. AI-generated hero illustrations.** Neural net renderings, robot mascots, glowing synapse diagrams, "intelligent pipeline" metaphor art. The audience will sneer. The Canvas illustration from §6 is the entire visual argument.

**5. Testimonial cards and logo walls.** No "as seen on," no "trusted by," no carousel of developer headshots. The instrument sells the instrument.

**6. Feature-tile grids.** Rows of three or four tiles with icons and two-line blurbs. This is the cheapest SaaS pattern and it collapses the education register into a sales register in one component.

---

## 10. Overlays as UI pattern

The brief invites engagement with shareable overlays. Here is the UI for Scene 7 and the sustained affordance.

### The manifest card

An overlay is a manifest. Each overlay card is a stamped document:

```
┌────────────────────────────────────────────────┐
│ PYTHON TRIM                     by @srobinson │
│ ──────────────────────────────                │
│ Strips unused Python tooling from Claude      │
│ Code sessions. Targets ide-intellisense,      │
│ jupyter-kernel, and the stdlib docs block.    │
│                                                │
│ -34 tools · -9,200 tokens avg · 12 installs   │
│                                                │
│ [ install overlay ]          [ inspect diff ] │
└────────────────────────────────────────────────┘
```

Layout:
- Card: `surface` background, 1px `edge` border, 0 radius, 24px padding.
- Title: JetBrains Mono 16px 500 uppercase, `txt`.
- Byline: JetBrains Mono 12px 400, `lavender`. Right-aligned.
- Hairline rule below title: 1px `edge-subtle`, gradient fade on both ends.
- Description: JetBrains Mono 14px 400, `txt-2`, max 3 lines.
- Signature delta: JetBrains Mono 13px 500, `amber` numbers, `txt-3` separators. Always in tabular-nums.
- Primary action: `install overlay`, 1px `teal` border, transparent fill, `teal` text, 36px tall.
- Secondary action: `inspect diff`, 1px `edge-strong` border, `txt-2` text.

### Stamp flourish (once, used once)

Behind each overlay title, a faint rubber-stamp ink motif in `teal` at 12% opacity, slightly rotated 3 to 5 degrees. This is the single decorative flourish on the page. It signals "manifest" as a printed artifact. Use at 80% of card width, clipped to card bounds, on the title area only.

Do not repeat this motif anywhere else. It is the one non-functional mark on the page.

### Active-overlay provenance

When an overlay is active inside the Canvas (relevant to Scene 6), a 2px `teal` bar runs down the left edge of every block affected. Above the Stack, a thin overlay-status strip reads: `overlay: python-trim · 34 blocks stripped · saves 9,184 tokens this turn`.

Provenance is visible. The visitor can see which choices came from them and which came from the overlay they installed.

### Gallery layout (Scene 7)

A 2-column grid of overlay manifest cards on desktop, single column on mobile. Cards do not hover-zoom. They respond to cursor with a 1px border color shift from `edge` to `teal`. That is all.

Below the grid, a single line of editorial pullquote text (the one surgical use of Source Serif 4 italic):

> *You do not need to write your own curation. You can subscribe to someone else's and learn theirs.*

One pullquote. One serif voice. Both earn their presence by landing the teaching argument about overlays.

---

## 11. Decisions for Stuart

Forks where a call unlocks the rest of the work.

**1. Typography budget.** Berkeley Mono license, Source Serif 4 accent, both, or neither. Default: neither; ship JetBrains Mono only. Upgrade path is honest; zero rework to retrofit.

**2. Live demo fidelity on the Hero strip.** Real payload ticker pulling from a recorded session vs. pre-baked animation. Real data is the instrument being honest; baked data is cheaper. The honesty cost of baked data in the Hero strip is meaningful because it contradicts the Scene 2 framing.

**3. Ruler ticks on the left edge.** A quiet flourish that codes the page as measured. Some will love it; some will find it fussy. Default: ship it on desktop only, at very low contrast. Remove if it reads as decoration during review.

**4. Stamp motif on overlays.** A single decorative flourish in an otherwise purely functional palette. It sells the "manifest" metaphor for overlays. Remove if it feels ornamental during review.

**5. Button replacement in Hero.** Replacing the primary "Get started" button with a muted text link `read the payload →`. This commits the page to invite-reading-before-installing. If Stuart wants the install action available in Scene 1, the button stays.

---

## 12. Open questions

- The Hero HUD in the top-right is a second always-on instrument. Does it feel useful or fussy when viewed alongside the live payload strip below? The instinct says one of the two is redundant. Recommendation: keep the HUD, drop the full-width strip once the Scene 2 Stack is visible. The HUD is the connective tissue; the strip is an intro card.

- The Scene 6 Canvas occupies full viewport. Does the three-column grid hold on a 1280px viewport, or does column 3 (tamper) collapse to a drawer? The answer depends on whether tamper is observable at rest (needed for the Canvas to tell its full story) or revealable on demand.

- Overlays are open exploration. If Stuart holds overlays until post-v1 ship, Scene 7 reduces to a single manifest card labeled "coming" with a waitlist affordance. The gallery layout above presumes at least three real overlays exist. Without them, the scene is weaker than the rest of the page and should be cut rather than staged.

- Accent economy: this brief argues for max two accent hues per viewport. Scene 5 uses rose (tamper) and amber (counter). Scene 7 uses teal and lavender. Scene 6 uses sky (user message) and amber (counter) plus rose on the tamper panel. Three hues in one frame might be unavoidable in the Canvas. Review whether rose in the Canvas can move to a `txt-2` gray until the viewer hovers the tamper panel.

---

## 13. Summary of commitments

One sentence each. This is the register the implementation should hold to.

- **Register:** Diagnostic Instrument. The page is the field manual of the instrument running on the same page.
- **Type:** JetBrains Mono only, 48 to 72px display, 16 to 18px body, tabular-nums for all numbers. One optional serif accent at pullquotes.
- **Color:** near-black canvas, six desaturated accents each with a single assigned job, max two accents per viewport.
- **Surface:** the Stack is the content. The Canvas from §6 is the hero illustration. No faux chrome, no device frames.
- **Density:** editorial to diagnostic to reference, in that order.
- **Motion:** fluorescent ignition for text arrival, mechanical counter for Scene 5 tamper. Nothing else.
- **Rejection:** no neon green, no glassmorphism, no AI-stock hero art, no feature tiles, no testimonial carousels, no browser-frame screenshots.
- **One flourish:** the rubber-stamp ink behind overlay manifest titles. Used once, used carefully.

---

## Appendix A: Token mapping

For the implementation designer. Existing Tailwind theme tokens map to the register above as follows.

| Role in register | Existing token | Notes |
| --- | --- | --- |
| Canvas | `bg-canvas` | No change |
| Panel / block background | `bg-surface` | Stack blocks, Canvas panels |
| Elevated panel | `bg-raised` | Tamper column, overlay cards |
| Hairline | `border-edge-subtle` | Between Stack blocks |
| Panel border | `border-edge` | Cards, column dividers |
| Emphasized border | `border-edge-strong` | Scene rules, ghost-button borders |
| Primary ink | `text-txt` | Headlines, body |
| Secondary ink | `text-txt-2` | Labels inside prose, ghost-button text |
| Annotation ink | `text-txt-3` | Metadata, HUD numerators |
| Label ink | `text-label` | Uppercase chips and strip labels |
| Visitor intent | `text-sky`, `border-sky` | "Hello", user message stripe |
| Kept / alive | `text-sage`, `border-sage` | Install command, primary CTAs |
| Token density | `text-amber` | All numeric displays |
| Tamper / edit | `text-rose`, `border-rose` | Scene 5 strip indicators |
| Annotation / metadata | `text-lavender` | "last referenced" tags, bylines |
| Overlay / second-party | `text-teal`, `border-teal` | Manifest cards, active-overlay edge bar |

## Appendix B: Missing primitives

What the current codebase does not yet provide and the register asks for:

- A `Stack` component: vertical stack of payload blocks, each block receives `label`, `tokens`, `status` (kept, unused, stripped), `preview` props, and a `stripe` accent slot.
- A `PayloadStrip` component for the live payload HUD and the in-viewport block bar.
- A `Counter` component that decrements mechanically, accepting `from` and `to` numeric props, fires a single animation, honors `prefers-reduced-motion`.
- A `ManifestCard` component for overlays with title, byline, description, signature line, and two actions.
- A `TamperToggle` primitive, the 4px-wide binary fill used in the 47-tool strip.
- A HUD slot in `App.tsx` that fixes the top-right telemetry line.

These five components plus the HUD slot cover every surface described above.
