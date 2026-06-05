---
title: Manicure Landing Page — UX Architecture Brainstorm
author: design-ux-architect
project: manicure
type: brainstorm
lens: ux-architecture
created: 2026-04-14
---

# Manicure Landing Page — UX Architecture

## Page thesis

The page behaves like the product. Manicure surfaces waste, invites realization, and allows tampering. The landing page should do the same thing to the visitor. The visitor arrives, sees their own assumed-sane agent setup implicated in a payload they cannot defend, starts toggling, and realizes the defaults were never free.

If the page reads like it is selling something, the audience has already left. The page is a diagnostic tool dressed as a landing page.

---

## 1. Structural archetype

**Primary archetype: diagnostic essay.**

A diagnostic essay is built around a single interactive exhibit that carries the argument. Surrounding prose exists to frame the exhibit and to offer depth for readers who want it. The exhibit is load-bearing. If the exhibit is removed, the page collapses into documentation.

Why this archetype over the alternatives:

- **SaaS landing** (hero, features, testimonials, pricing) reads as a pitch. The audience is trained to discount it.
- **Docs index** is inert. It assumes the reader already wants the tool.
- **Playground** is close, but a full playground implies the product lives on the web. Manicure runs locally against a real API key. A playground page would mislead.
- **Essay** alone is inert for a visual medium. Developers respect prose but the visceral argument (tokens wasted) needs to be seen, not asserted.

Diagnostic essay combines the parts that work. One exhibit. Enough prose to steer the reader. A single command at the bottom for anyone who wants to try it locally.

Secondary archetype to borrow from: **CLI tool homepage** in the Warp, Zed, Ghostty lineage. Minimal chrome, dark palette, one big interactive element above the fold, install command as the closer.

---

## 2. Section outline

Proposed top-level sections in scroll order. Heights are approximate in viewport units.

### A. Cold open (≈ 1.0 vh)

**Purpose.** Establish the premise in one visual beat. No heading. No logo sell. A single real-looking payload rendered as a block with token counts, where the majority is dimmed and labelled as untouched. The visitor sees the proportion before reading a word.

**Content.** Static visual with one animated reveal (token counter resolving from 0 to ~40,000 on scroll enter). A very short line of prose underneath: one sentence that names what they are looking at. No CTA here.

**Interaction.** None. Static. The cold open earns the scroll.

**What the visitor should do.** Pause. Scroll.

### B. The diagnostic (≈ 1.5 vh)

**Purpose.** The load-bearing exhibit. An interactive token-budget autopsy on a pre-baked Claude Code payload.

**Content.** A payload panel on the left showing the request structure (system prompt, tools, resources, messages). A control strip on the right with toggles for each MCP server, each tool group, each built-in tool, and the system prompt. A live token count and a "noise ratio" meter at the top. The reader toggles things off. Tokens fall. A small footer line in the panel shows the rendered response quality shifting (this part uses pre-recorded response pairs, not a live Claude call).

**Interaction.** Click to toggle. No paste, no API key, no signup. Every interaction is safe, reversible, and local to the page.

**What the visitor should do.** Tamper. The action IS the realization.

### C. The three pillars as captions (≈ 0.8 vh)

**Purpose.** Name what just happened. The visitor has already experienced Surface, Realize, and Tamper in the diagnostic above. This section labels the experience retroactively.

**Content.** Three compact blocks arranged horizontally on wide viewports, stacked on narrow. Each is one noun, one short line, one illustrative micro-visual tied back to the exhibit above. No bullet points. No "learn more" chevrons.

**Interaction.** None. Prose.

**What the visitor should do.** Finish reading. Continue.

### D. Overlays (≈ 1.2 vh)

**Purpose.** Show that the curation is transferable. The reader is now thinking about their own payload. Overlays turn that impulse into something concrete and shareable.

**Content.** A curated selector with two or three named overlays (for example, "python-trim by @stu", "ts-monorepo-trim", "minimal-mcp"). Applying an overlay to the same diagnostic payload from section B animates the toggles into the overlay's configuration. The payload shrinks. The caption explains what the overlay's author removed and why.

**Interaction.** Click an overlay. The exhibit in section B updates in place (or a pinned mini-preview updates here). Share URL captures the applied overlay.

**What the visitor should do.** Consider the shareable angle. Realize this is how trim knowledge travels.

### E. Install (≈ 0.6 vh)

**Purpose.** Conversion for the convinced. A single command, large, copy-button, terminal-styled.

**Content.** One code block. One line above it naming the shell (pipx, brew, or equivalent). One line below linking to the short getting-started essay for the reader who wants to understand before installing.

**Interaction.** Click-to-copy.

**What the visitor should do.** Copy, or click through to the deeper read.

### F. The deeper read (≈ 0.8 vh)

**Purpose.** Serve the reader who wants prose before code. Three to four linked essays or doc pages, each with a one-line hook.

**Content.** Plain links with descriptive titles. No cards, no thumbnails, no reading time estimates, no tags.

**Interaction.** Navigation out.

### G. Footer (≈ 0.3 vh)

**Purpose.** Signal that a real person built this. Repo link, license (Apache-2.0), one-line bio, way to reach the author.

**Interaction.** Minimal.

**Total scroll depth.** Roughly 6 to 6.5 viewport heights. Short for a landing page. The diagnostic absorbs the time budget that a typical page spends on bullet features.

---

## 3. The interactive diagnostic

This is the exhibit. Its design is the single biggest decision on the page.

### Interaction envelope

Recommended primary shape: **browser-only toggle-a-pre-baked-payload.** No API keys. No paste. No Claude call at runtime.

The payload is a real Claude Code request captured by Manicure itself, anonymized, frozen as JSON, and shipped as a static asset. Response quality shifts are demonstrated via a small table of pre-recorded response pairs keyed on a handful of salient toggle combinations. The reader cannot produce an arbitrary response; they can produce one of ten or so curated deltas. This is a conscious design lie the same way a product demo is a design lie: it is honest about what it is, it illustrates a true principle, and it sidesteps the infrastructure tax of making it real.

### Why not paste-your-own

The paste-your-own interaction is tempting. It collapses the distance between the page and the reader's situation. It is also wrong as the primary interaction on a landing page:

- Payloads contain project code and proprietary context. Asking the reader to paste that into a web page is a trust ask that should come later, after the local install.
- Paste-your-own implies full-fidelity response simulation, which requires API calls. Either the visitor supplies a key (friction) or the site proxies (cost, abuse surface).
- The paste interaction is a better fit for the installed tool. The landing page's job is to make the reader want to install the tool. The paste moment lives at `manicure start`.

Leave paste as a later affordance, possibly a `/playground` route for the curious, not the primary.

### Why not a scripted walkthrough

A scripted walkthrough (play button, auto-advance) is the third tempting shape. It removes reader agency. The product's core loop is Tamper. A walkthrough shows Tamper without letting the visitor perform it. That is a betrayal of the thesis. Scripted walkthroughs belong in product-tour videos, not on this page.

### Fidelity of the "response quality shifts" panel

Be honest about this piece. The diagnostic shows real token deltas (arithmetic, not simulation) and pre-recorded response deltas (illustrative, not live). A tiny footnote on the panel saying "responses are pre-recorded examples" is enough to preserve trust with a skeptical audience. A skeptical developer is not insulted by a well-labeled demo. They are insulted by a live-looking demo that is actually scripted.

---

## 4. CTA architecture

### Primary CTA

**One install command.** Large, monospace, copy-button. Appears once, at the install section, not repeated in the hero. The exhibit earns the install, so the install does not need to preempt the exhibit.

Possible exact form (design to verify with the release channel): `pipx install manicure` or `brew install helioy/tap/manicure`. The command must be honest about the installed surface. If `manicure start` spawns Claude Code, the command and the expected first-use line should be within the same block.

### Secondary CTA

**Read the thesis.** A link to the long-form essay where Stuart argues context curation over cache optimization. Developers who need to reason about a tool before using it go here.

### Tertiary CTA

**View on GitHub.** In the nav (if there is one) and the footer. Always available, never the highlighted action.

### What is not a CTA

No "book a demo." No "sign up for updates." No "join the waitlist." No "request early access." No "get in touch." Any of these breaks the diagnostic tool vibe instantly.

### CTA placement rule

The page has one primary moment of conversion. It sits after the diagnostic, after the overlay example, after the reader has had enough contact with the idea to want the thing. Placing the install command in the hero is the most common landing page mistake and it is wrong here because the reader does not yet know what they would be installing.

---

## 5. Progressive disclosure pattern

The staircase, in order of reader patience:

1. **Three seconds.** Cold open token visual. The reader has seen the proportion.
2. **Thirty seconds.** First few toggles in the diagnostic. The reader has produced a smaller payload with their own hand.
3. **Two minutes.** The three pillars retroactively label what the reader just did. The overlay section shows that the curation is portable.
4. **Five minutes.** The install command and the thesis essay. The reader who wants prose has prose. The reader who wants code has code.
5. **Twenty minutes.** The essays linked from section F. Deeper arguments about context quality, the history of cache optimization being the wrong target, overlays as a social artifact.

Each rung should make sense as a stopping point. A reader who leaves at step 2 should have taken away the realization even if they never install. A reader who leaves at step 4 has the tool. The page rewards any depth of attention.

---

## 6. Navigation

**Recommendation: minimal top nav, right-aligned, three items.**

- `manicure` wordmark, left-aligned, linking to the top of the page.
- `docs` (or `read`), `github`, `install` right-aligned. `install` is a text link that jumps to section E, not a button.

**What not to include.** No "features," no "pricing," no "about," no "blog" (unless there is a live blog with recent posts), no "login," no dropdowns, no mega-menu.

**Fixed vs. unfixed.** Lightly sticky with background blur on scroll, not fully pinned chrome. The page is short enough that the nav does not need to survive 8 viewport heights of scrolling.

**Alternative.** No nav at all. Warp's homepage used to do this well. The tradeoff is discoverability of the GitHub link, which the skeptical audience reaches for within ten seconds. Keep the nav for that reason alone.

---

## 7. Page state

### What the page should remember

- **Diagnostic state.** The reader's toggle configuration in section B survives a reload. Stored in localStorage keyed by payload id.
- **Applied overlay.** If an overlay has been applied, remember which one.
- **Visit count, lightly.** On return, the cold open can say "you were here before" only if that language is honest; if not, skip it. Do not use it as a nudge.

### What the page should not remember

- No analytics-driven personalization. The page does not change its argument based on referrer or prior visits. Doing so would break the diagnostic tool vibe.

### Boldest useful interactive state

**Shareable diagnostic URL.** A reader toggles off four tools and an MCP server, copies a URL, sends it to a teammate. The teammate opens the URL and sees the same configured exhibit. This is the teaching artifact angle from the brief, applied to the exhibit itself. It is cheap (serialize the toggle state into the fragment), and it lets the page be a vehicle for one developer convincing another.

This is the single interactive affordance that would lift the page above other dev-tool landings. It doubles as a marketing loop without being marketing.

### Stretch: paste-your-own, `/playground`

If there is appetite later, a `/playground` route takes a user-supplied payload (in-browser, client-only, no server send) and runs the same diagnostic. Launched as a separate route so the landing page stays focused. Ship after the install funnel is stable.

---

## 8. Failure modes

Three common dev-tool landing page patterns that would actively undermine the positioning:

### 1. Feature bento grid

Six boxes. Icon, title, two-line description. "Inspect" / "Modify" / "Share" / "Analyze" / "Integrate" / "Deploy." This pattern is load-bearing in a lot of SaaS landings. It would be actively harmful here. The bento grid asserts; it does not demonstrate. Because the product's claim is that asserted context curation is cheap and demonstrated context curation is valuable, a bento grid contradicts the thesis in its own structure. A developer reading it would feel the mismatch without being able to name it.

### 2. Big hero headline with gradient and action verbs

"Ship better agents faster. Now with real-time introspection." Giant type, gradient, rocket-adjacent copy. The skeptical developer audience exits on sight. This pattern is the bullshit smell the brief warned about. It is disqualifying. It also makes the voice constraints (no em dashes, professional, concise) impossible to honor without looking like the page cannot decide who it is for.

### 3. Testimonials from unknown companies

"Manicure saved us 40% on our token bill. — CTO, AcmeCorp." The audience does not care. Social proof for dev tools is code snippets, named respected engineers, public GitHub stars, and actual usage numbers. Generic testimonial cards are worse than no testimonials because they signal that the tool is trying to borrow authority it has not yet earned.

### Honorable mentions (also harmful)

- **A pricing table.** Manicure is open source under Apache-2.0. A pricing table would betray that.
- **A floating chat widget in the bottom-right.** Every chat widget reads as pitch-oriented support theater.
- **A "trusted by" logo row with brands the reader does not recognize.** Same failure mode as testimonials, louder.
- **Cookie banner and GDPR modal as the first interaction.** Kills the cold open entirely. If analytics is needed, use server-side or privacy-respecting tooling that does not require a banner.

---

## Summary of the architecture

One exhibit carries the argument. A short cold open earns the scroll into the exhibit. Three pillars retroactively label what the visitor has already experienced. Overlays demonstrate portability. One install command converts. A small set of essays serves the readers who want prose. The nav is three links. The page remembers the visitor's configuration and serializes it into a shareable URL.

The page is short. The exhibit is deep. The conversion is quiet.

This shape is deliberately at odds with the existing section inventory (Problem / Revelation / Comparison / Pillars / HowItWorks / TokenEconomics / BottomCTA). The existing inventory reads as a problem-to-solution funnel, which is what the brief is trying to reject. The architecture proposed here collapses Problem, Revelation, Comparison, HowItWorks, and TokenEconomics into a single interactive exhibit (section B), keeps Pillars in a reduced retroactive role (section C), and replaces the traditional BottomCTA with a plain install block (section E). The boldest change is the diagnostic taking over the middle of the page, displacing roughly five sections of prose.
