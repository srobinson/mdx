---
title: Manicure Landing Page — Warroom Synthesis
project: manicure
date: 2026-04-14
type: synthesis
lenses: [brand-guardian, visual-storyteller, whimsy-injector, ux-researcher, ux-architect, ui-designer]
related:
  - ~/.mdx/projects/manicure-landing-brand-guardian--brainstorm.md
  - ~/.mdx/projects/manicure-landing-visual-storyteller--brainstorm.md
  - ~/.mdx/projects/manicure-landing-whimsy-injector--brainstorm.md
  - ~/.mdx/projects/manicure-landing-ux-researcher--brainstorm.md
  - ~/.mdx/projects/manicure-landing-ux-architect--brainstorm.md
  - ~/.mdx/projects/manicure-landing-ui-designer--brainstorm.md
---

# Manicure Landing Page: Warroom Synthesis

Six specialist agents delivered independent brainstorms on the Manicure landing page. This document surfaces convergence, sharpest individual contributions, tensions, and decisions that need Stuart's call.

## The thesis (all six converged here)

> Most dev tool landing pages argue for the product. Manicure argues against the visitor's current setup.

This sentence from brand-guardian is the cleanest distillation of what every agent proposed. Every other recommendation in this synthesis either supports or operationalizes it.

## Strong convergence (6 of 6 agree)

| Area | Consensus |
| --- | --- |
| Register | Diagnostic tool, not SaaS pitch. Patterns match to Burp Suite, Wireshark, Charles, mitmproxy, Observable Framework. |
| Visual protagonist | A single vertical representation of a real `/v1/messages` payload ("The Stack"). It is annotated, then editable, then absorbed into the Manicure canvas. |
| Strongest artifact | The existing "You typed 'Hello'. Your agent sent 285,000 tokens" hook. Survives the pass unchanged. Build outward from it. |
| Overlays | Real idea with real pull. Late scroll, not hero. Only ship on v1 if three real overlays exist. |
| Feature framing | No bento grid. No icons. Features appear only as resolutions of problems the visitor has already seen demonstrated. |
| Social proof | No logo walls, no testimonials, no "trusted by." Replace with real screenshots of real before/after payloads. |
| CTA in hero | No install button in hero. Install belongs at the bottom, after the diagnostic has earned it. |
| Chrome | No macOS window chrome on screenshots. No browser frames. The instrument bleeds full viewport. |

## The sharpest individual contributions

### Brand Guardian
- **Brand promise (narrow by design):** Manicure intercepts every request, shows the payload, lets you edit before forwarding. Does NOT promise productivity, better code, or cost savings.
- **Anchor words:** Forensic, Meticulous, Candid, Dry, Spare. Each justified in the source document.
- **Voice sample:** *"Your coding agent ships twenty tools with every request. You used two. Manicure shows you the eighteen you didn't."*
- **Never-say list (with reasoning):** "supercharge," "10x," "save on API costs," "the future of AI development," "trusted by engineers at [logos]."

### Visual Storyteller
- **Story spine:** The visitor arrives curious, sees the grotesque size of a request they thought they understood, recognizes most of it as clutter they personally authorized, leaves less confident about their own setup and more willing to look.
- **8-scene arc (autopsy → workshop hybrid):** Ignition → Autopsy → Inventory → Noise costs answers → **Reveal (pivot, Scene 5)** → Canvas → Overlays → Close.
- **Running visual thread:** The Stack. Scene 1 implied, Scene 2 introduced, Scene 3 annotated, Scene 4 duplicated side-by-side, Scene 5 interactive, Scene 6 absorbed into canvas, Scene 7 pre-curated overlay previews, Scene 8 fades.
- **Reveal moment (Scene 5):** The one scene where the page stops talking and hands the visitor the interaction. Toggle a tool, watch the column shorten, watch the counter drop, watch the response return. Low stakes, immediate feedback, reframes the page from diagnosis to workshop.

### UX Architect
- **Structural archetype:** Diagnostic essay. One load-bearing interactive exhibit carries the argument. Prose exists to frame the exhibit.
- **Section collapse:** Problem / Revelation / Comparison / HowItWorks / TokenEconomics → ONE interactive diagnostic (~1.5 viewport heights). Pillars reduced to retroactive captions. Total page ~6 viewport heights.
- **Shareable diagnostic URL:** toggle five things off, copy the URL, send to a teammate. The teammate opens and sees the same configured exhibit. Marketing loop without marketing.
- **Fidelity honesty rule:** Real token deltas (arithmetic). Pre-recorded response deltas (illustrative, footnoted as such). A skeptical developer is not insulted by a well-labeled demo. They are insulted by a live-looking demo that is actually scripted.
- **CTA architecture:** One install command. At the bottom. Never in the hero.

### Whimsy Injector
- **Tone references:** Linear (laconic command copy), Fly.io (admits the awkward parts), Val Town (punchy, declarative, willing to be blunt once). Reject Vercel/Stripe (too polished for a tool that asks you to look at your own mess).
- **MCP graveyard line** (under Realize): *"Average Claude Code install ships ~6 MCP servers per request and calls 0.4 of them per turn. The rest are pallbearers."*
- **Hero headline candidate #1:** *"Your prompt is 0.002% of the request."* Numbers beat copy by an order of magnitude at this audience.
- **Mani·cure interpunct as the cursor:** the dot in the wordmark becomes the blinking cursor on the canvas. The wordmark is now a diagram.
- **Footer (not a link grid):**
  ```
  this landing page: 47KB gzipped.
  your last claude request: ~600KB of payload.
  we are not above noticing.
  ```
- **Chip hover reveal:** `Context control plane` morphs on hover to `(formerly: 'context laundering proxy')`. One line of copy, three CSS rules.
- **Devtools easter egg:** opening devtools logs a fake Claude Code payload shaped like a landing page request. 47 unused tools, 12k-token system prompt, 4-character user input (`npm `).

### UX Researcher
- **Three personas:** Malik the MCP Maximalist (medium skepticism, came from a "your agent ships way more than you think" comment). Priya the Observer (high skepticism, security background, ran tcpdump, reads GitHub before landing). Dev the Token Accountant (medium-high skepticism, per-line-item spend, wants per-tool cost attribution).
- **Eight-second skim test — three beats that must land:**
  1. Your agent ships a lot more than you think (concrete number in first viewport).
  2. This is a tool for looking, not a tool that sells a fix (Burp/Wireshark register).
  3. One command to install, does not touch your system (no sudo, no certs).
- **Top objections with counters:** "I can build this myself" / "middleware latency" / "I trust Anthropic" / "mitmproxy exists" / "prompt caching handles this."
- **Cut list (usually appears on dev tool landings, cut here):** hero video with smiling developer, "trusted by" logos, feature checklist grid, FAQ accordion, email capture above the fold.
- **What the landing CANNOT make believable on first contact:** quality improvement claims, percentage token reduction, "no risk," ecosystem integration hype, the three-pillar abstraction itself. Defer each to a deeper read.

### UI Designer
- **Committed visual register:** Diagnostic Instrument. The page is the field manual of the instrument running on the same page.
- **Typography:** JetBrains Mono only (no sans). 48-72px display. 16-18px body. All numbers tabular-nums + slashed zero. Optional Source Serif 4 italic for two surgical pullquotes.
- **Color semantics (accent economy: max two accents per viewport):**
  - **Sky** = visitor's intent (the "Hello", user message stripe)
  - **Sage** = kept state (install command, "keep" badges)
  - **Amber** = token density / mass (all numeric displays)
  - **Rose** = tamper / edit
  - **Lavender** = annotation / metadata
  - **Teal** = overlays / second-party provenance
- **Hero enhancements (keep existing copy):**
  - Persistent HUD top-right: `session 0 / turn 0 / tokens 0` that animates as you scroll.
  - Full-width live payload strip below fold with a scanline sweep.
  - Replace "Get started" button with muted text link `read the payload →`.
- **Canvas hero illustration spec (§6 of source document):** three-column grid (Block Inventory / Expanded Block JSON / Tamper Panel). Toggling in column 3 drives row state in column 1 (rose strikethrough, 40% opacity, counter decrements).
- **Density arc:** editorial (Scenes 1-2) → diagnostic (Scenes 3-5) → reference (Scenes 6-8).
- **Motion:** two earned cues — fluorescent ignition for text arrival (already shipping), mechanical token counter for Scene 5 (new, load-bearing). Two anti-patterns: no parallax, no fade-in-on-scroll as ambient motion.
- **Single decorative flourish allowed:** rubber-stamp ink motif behind overlay manifest titles in teal at 12% opacity. Used once, used carefully.
- **Anti-look:** neon phosphor-green (Matrix aesthetic), glassmorphism / aurora gradients, screenshot-in-browser-frame, AI-generated hero illustrations, testimonial cards, feature-tile grids.
- **Missing primitives to build:** `Stack`, `PayloadStrip`, `Counter`, `ManifestCard`, `TamperToggle` components, plus a HUD slot in `App.tsx`.

## Tensions that need reconciliation

### 1. Hero headline (three candidates)

| Candidate | Author | Strength | Risk |
| --- | --- | --- | --- |
| "See what your coding agent ships." | Current (kept by storyteller) | Safe, diagnostic, low-risk | Less personality than the others |
| "Your prompt is 0.002% of the request." | Whimsy (ranked #1) | Number-led, violates silently, forces scroll | Number requires justification in subline |
| "Your agent sends more than you think." | Brand Guardian | Six words, close to accusation, respectful | Less visceral than the number |

**Suggested stack:** keep the current hero line as the title. Use whimsy's "0.002%" as the first line of the subline (replacing or preceding the 285,000 line). The abstract claim leads, the number validates it in the next beat.

### 2. The three pillars (Surface / Realize / Tamper)

- **UX researcher:** Cut entirely from visible copy. Internal framing only.
- **UX architect:** Keep, but retroactively as compact captions AFTER the diagnostic exhibit. The visitor has already experienced them; the section just labels the experience.
- **UI designer:** Doesn't directly address but the existing `context control plane` chip stays.

**Recommendation: UX architect wins.** Retroactive labeling preserves the internal frame without asserting it upfront. Compact block, no bullet points, no "learn more" chevrons.

### 3. Interactive diagnostic fidelity

All three structural agents flagged this. Shared recommendation:

- Real token deltas (arithmetic, not simulation).
- Pre-recorded response deltas (illustrative, footnoted as such).
- No paste-your-own on the landing (trust ask should come after local install).
- No scripted auto-advance walkthrough (betrays the Tamper thesis).
- Browser-only, no API key, no signup.

### 4. Accent economy vs Canvas complexity

UI designer flagged this as an open question. "Max two accents per viewport" is the rule. The Canvas (Scene 6) needs sky + amber + rose in one frame (visitor's intent + token counter + tamper panel). Three hues in one frame.

**Proposed fix (UI designer):** Rose on the tamper panel degrades to `txt-2` gray until hovered. Active tamper state lights up rose. This keeps the resting frame at two accents and uses rose as reactive rather than ambient.

### 5. Overlays in v1 or v2

- UX architect: ship in v1 if 3+ real overlays exist, else teaser tile.
- Visual storyteller: same.
- UI designer: "Gallery layout presumes at least three real overlays. Without them, the scene is weaker than the rest of the page and should be cut rather than staged."
- Brand guardian: overlays fit the brand cleanly as teaching artifacts. No marketplace.
- Whimsy: registry should look like a typewritten zine, not npm.

**Recommendation:** Cut overlays from v1 unless 3+ real ones exist at ship. Replace Scene 7 with a single paragraph about what this shape of tool unlocks, framed as future-facing.

### 6. HUD top-right vs Live Payload strip redundancy

UI designer's own flagged question. Both are telemetry. One is sufficient.

**Recommendation:** Keep the HUD top-right as connective tissue across the whole scroll. Drop the full-width payload strip once the Scene 2 Stack is in viewport. The HUD is ambient; the strip is a redundant intro card.

## Decisions for Stuart (forks that unlock downstream work)

1. **Hero copy.** Stack the three candidates as proposed above, or pick one outright?
2. **Interactive diagnostic.** Browser-only pre-baked payload with scripted response deltas (consensus), or invest in real-time simulation?
3. **Three pillars treatment.** Retroactive captions (architect recommendation) or cut entirely (researcher recommendation)?
4. **Overlays in v1.** Cut until 3+ real overlays ship, or stage the scene with a teaser tile?
5. **Typography budget.** JetBrains Mono only (default), Berkeley Mono upgrade, Source Serif 4 accent, or both?
6. **Decorative motifs.** Stamp motif on overlay cards (single flourish), ruler ticks on left edge (quiet measurement cue). Ship both, one, or neither?
7. **Hero button replacement.** Keep "Get started" button, or replace with muted text link `read the payload →` per UI designer?
8. **285,000 token number.** Keep as-is, or tighten to a more relatable 50k-100k (visual storyteller asks)?
9. **Shareable diagnostic URL.** Ship this v1 as the marketing loop without marketing, or defer?

## Recommended next steps

1. **Stuart reviews this synthesis and settles the 9 decisions above.** Most can be answered in a single word.
2. **One more round for convergence:** spin up a smaller warroom (2 agents, e.g. UX architect + visual storyteller) and feed them the resolved decisions. Ask them to produce a concrete scroll-by-scroll spec.
3. **Build brief:** UI designer's Appendix B names the 5 missing primitives. Once the spec is locked, those become tickets.

The warroom convergence is unusually tight. Every agent arrived at the same thesis through their own lens, which is the strongest possible signal that the thesis is the right one. The work now is to operationalize it without softening it.
