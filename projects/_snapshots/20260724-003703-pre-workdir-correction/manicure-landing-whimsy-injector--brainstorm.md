---
title: Manicure Landing Page — Whimsy Injector Brainstorm
type: brainstorm
project: manicure
author: design-whimsy-injector (warroom agent)
date: 2026-04-14
status: draft
audience: Stuart + brand/copy/eng leads on the manicure landing warroom
---

# Manicure Landing Page: Whimsy Injector

## Frame

Manicure is a diagnostic tool for skeptical developers. The job here is to find personality without breaking the diagnostic vibe. Whimsy is restraint, not exuberance. Every joke earns its place by paying off in math, surprise, or self-awareness. Nothing winks twice.

The fluorescent flicker on scroll-enter that already ships is the right baseline. It signals "instrument, not advertisement." Build on that aesthetic vocabulary. Add nothing that twirls.

---

## 1. Tone references

Three developer products whose humor I would borrow from, and the single trait that makes each work.

**Linear** — laconic command bar copy. Every microcopy line reads as if the product is slightly tired of being asked. "Add issue. Press C." No persuasion, just instruction. Manicure can borrow the confidence to under-explain.

**Fly.io** — docs and blog voice that admit the awkward parts. Footnoted asides, dry parentheticals, "this is a bit weird and we know" honesty. Manicure should adopt the willingness to point at its own seams. A diagnostic tool that hides its own limits is not credible.

**Val Town** — punchy, declarative headlines that name a thing developers feel but rarely say. "JavaScript without the bullshit." Manicure should let one headline be that blunt. Once. Not the whole site.

Honorable mentions: Warp's command-block philosophy, Tailscale's "it just works" minimalism, Plausible's "Google Analytics for people who hate Google Analytics" positional clarity. Avoid Vercel and Stripe as references. Both are too polished for a tool that asks you to look at your own mess.

---

## 2. Five whimsy moments embedded in the page

Each is tied to the product premise. Each survives the "would Linear ship this" test.

### 2.1 The waste counter that ticks while you read

**What:** The "285,000 tokens" stat in the hero is a live counter. It increments by ~1,200 every second the page is open, with a tiny annotation underneath: *recalculated from public Anthropic SDK telemetry, not your traffic*.

**Where:** Hero subline.

**Reaction:** A blink, then a scroll. The user does the math themselves. "I have been reading this for 40 seconds, that is 48,000 tokens of nothing somewhere."

**Why it doesn't break trust:** The source disclaimer is in the same line. Numbers without sources are marketing. Numbers with sources are reporting. The disclaimer also pre-empts the obvious objection ("how do you know?") before anyone can voice it.

### 2.2 The MCP graveyard footnote

**What:** In the Pillars section, under "Realize," a single italicized line: *Average Claude Code install ships ~6 MCP servers per request and calls 0.4 of them per turn. The rest are pallbearers.*

**Where:** Pillar 2 (Realize), one line under the body copy.

**Reaction:** A wince, possibly a Slack share. The line works because "pallbearers" is unexpected and the number that precedes it is precise.

**Why it doesn't break trust:** No vendor is named. No screenshot of someone's config is shown. The shame is universal, which means it lands without singling anyone out. If the number stops being roughly true, the line gets removed. Nobody knows it was ever there.

### 2.3 The "or: keep wasting tokens" link

**What:** Under the hero CTA "Get started," a low-contrast secondary link: *or: keep wasting tokens.* Clicking it does nothing visible. It writes one line to the browser console: `[manicure] noted. timestamp: 2026-04-14T08:31:12Z`.

**Where:** Below the primary CTA.

**Reaction:** A smirk if seen. Most visitors will not see it. That is fine.

**Why it doesn't break trust:** Nothing harmful happens. No tracking event fires. The console line is only visible to people who open devtools, which is exactly the audience already inclined to like the product. The joke rewards the curious without punishing the polite.

### 2.4 The "your context, but honest" slider

**What:** The interactive payload demo has a slider. As you drag, tools and unused context blocks fade out and the token counter ticks down. The label above the slider has three states: *your context*, *your context, trimmed*, *your context, but honest*. Only the final state is reached at the end of the slider track.

**Where:** Mid-page, in the Surface or Tamper section.

**Reaction:** A satisfied exhale. The third label is the punchline and you have to drag the slider all the way to find it.

**Why it doesn't break trust:** The transformation shown is real (the tools dropped were genuinely unused in the demo trace), and the third label is honest about its own framing. It is not "your context, optimized." The product is not promising magic, it is promising candor.

### 2.5 Devtools easter egg

**What:** Open the browser console on the landing page. One line is logged on load:

```
// you opened devtools. that is exactly the instinct manicure rewards.
```

Followed by a JSON.parse of a fake payload that approximates what the page would look like if it were a coding agent request: 47 unused tools, a 12,000 token system prompt, and a 4 character user input (`npm `).

**Where:** Console only.

**Reaction:** A nod. Maybe a screenshot.

**Why it doesn't break trust:** It is invisible to non-developers and respectful of developers. The fake payload is labeled fake. There is no marketing copy. The medium is the message.

---

## 3. The name itself

**Read: lean in. Ration the puns.**

"Manicure" is already doing most of the work. It signals attention to detail, surgical precision, and a faint comic absurdity (you do not normally manicure software). The wordmark `mani·cure` with the interpunct, paired with the etymology gloss `manifest + curate`, gives you a built-in payoff that justifies the choice without belaboring it.

The risk is that puns multiply. If "trim," "groom," "file," "buff," and "polish" all show up as section headers, the page becomes a hairdresser's homepage. Resist.

**Two ways to weaponize the name:**

### 3.1 The interpunct as the canvas cursor

Make the dot in `mani·cure` the same dot that blinks as the cursor in any product screenshot or canvas demo. Visually, the dot becomes "the agent's attention." Trimming context trims that dot's blast radius. The wordmark is now a diagram. No copy required to explain it.

### 3.2 One paid-off pun, deep in the diagnostic copy

Use the word "manicure" as a verb exactly once in the page body, and only when it follows a hard number. Example:

> Your last 100 requests carried 4.2M tokens. Of those, 1.1M never reached an attention head. Your context could use a manicure.

This works because the pun is the conclusion of an arithmetic statement. The reader has already accepted the math, so they accept the verb. Anywhere else on the page, the same line would be cute. Here it is the diagnosis.

Do not use "manicure" as a verb in headlines. Headlines are too prominent for puns.

---

## 4. A micro-interaction that rewards curiosity

**The chip in the hero that admits it has been renamed.**

Currently the chip says `Context control plane`. On hover, it morphs (subtle slide, not a tooltip) to: *(formerly: 'context laundering proxy')*. Hover off, it returns.

**Why this works:**

- It rewards a curious mouse, not a curious click. No interaction state to trap users in.
- It signals self-awareness about positioning. A team confident enough to name the bad option they rejected reads as a team that has thought hard about positioning.
- It is briefly funny ("laundering" is a slightly menacing word for what the proxy does, which is exactly why it was rejected) and then gone.
- It is one line of copy and three CSS rules. Cheap to ship, cheap to remove.

If the team prefers a different rejected name, swap the copy. The mechanic is the value.

---

## 5. Three hero headlines with edge

### Candidate A: "Your prompt is 0.002% of the request."

Number-led. Specific. Visceral. Bypasses the "another AI tool" filter because it does not mention the product. Forces a scroll because the implied question ("then what is the other 99.998%?") is the whole pitch.

### Candidate B: "Read your agent's mail."

Three words. Concrete metaphor. Implies surveillance with consent (it is your mail). Ties cleanly to the proxy concept without using the word "proxy." Slightly old-fashioned word "mail" gives it dryness.

### Candidate C: "See what your coding agent ships."

The current headline. Direct, diagnostic, low-risk. Strong baseline. Less personality than the other two but no false notes.

### Ranking and defense

**#1: Candidate A** — *"Your prompt is 0.002% of the request."*

Defense: The audience is developers. Numbers beat copy at this audience by an order of magnitude. The number is precise enough to feel real and small enough to feel violating. It does not mention manicure. It does not mention Claude. It states a fact the reader did not know about their own behavior, which is the best possible opening for a diagnostic tool. The reader supplies the curiosity. The product supplies the answer.

The sentence also has a structural elegance. It reads as a fragment of a measurement, not a slogan. That is the right register.

**#2: Candidate B** — Memorable, but more abstract. Better as a section header or a tweet than as the hero.

**#3: Candidate C** — The safe pick. Will not get in the way. Will not sell you on its own.

Recommendation: Ship A. Hold B in reserve for the OG image, the homepage `<title>`, or a section header lower on the page.

---

## 6. The footer

A footer that is not just links.

**Proposal:** A single line of microcopy above the link grid, in the same monospace as the install command.

```
this landing page: 47KB gzipped.
your last claude request: ~600KB of payload.
we are not above noticing.
```

Three lines. No periods on the first two (deliberate, they read as data). Period on the third (deliberate, the line lands).

**Why this closes with a smile:**

- It is a flex (we are light) and a self-effacement (we are looking at our own page weight, which is a slightly silly thing to compare) at the same time. That tension is the joke.
- It restates the product premise one more time without saying the product name. Repetition through metaphor, not through copy.
- "We are not above noticing" is the sentence I most want to live in the reader's head. It is the entire posture of the company in seven words.
- It is renderable as static text. No counter, no live update, no JS. The whimsy is in the writing, which means it never breaks.

Numbers can be updated when the page weight changes. The Claude payload number can be footnoted to a public source if needed.

---

## 7. Five things NOT to do

Anti-patterns specific to skeptical Claude Code users.

### 7.1 No "AI magic," "intelligently," or "powered by"

These are the three highest-bounce phrases for this audience. Developers who write prompts daily read "intelligently filters" as "we have not thought hard about what we filter." If the page describes mechanism, mechanism wins. If it describes magic, the audience leaves.

### 7.2 No exclamation marks. Anywhere.

Including in microcopy. Including in error states. Including in the install confirmation. The voice is laconic and slightly tired. The closest the page gets to enthusiasm is a colon. A single exclamation mark on the page is enough to suggest the product was made by people who type the way they post on LinkedIn.

### 7.3 No animated rockets, sparkles, gradients with eight stops, or floating particles

Visual whimsy at this audience reads as Webflow templates and Y Combinator graveyard. The fluorescent flicker on scroll-enter is enough motion. If anything else moves on the page, it is data (the waste counter, a token tally on a slider). Decoration that moves is decoration that lies.

### 7.4 No fake testimonials and no "Senior Engineer at Stealth Startup"

If social proof appears, it is a real screenshot of a real payload going from large to small, with a real handle attached and a caption that names the project. Receipts, not quotes. A blockquote with a smiling avatar is the single fastest way to lose this audience.

### 7.5 No "Coming soon," roadmap teasers, or "Phase 2" hints

The page describes what works today. Future-tense kills credibility for a diagnostic tool, because the implicit promise of a diagnostic tool is "the truth, now." If overlays are not shareable yet, the page does not mention overlays. When they are shareable, the page mentions them.

Bonus 7.6 (worth flagging): Do not name competitors on the landing. Naming LangSmith, LangFuse, Helicone, or Helicone-likes validates them and frames manicure as a direct-comparison play, which it is not. The lane is "look at your payload before you ship it." That lane has no incumbent yet. Do not invent one.

---

## Bonus: shareable overlays as teaching artifacts

The brief flagged this as exploratory. Quick read from the whimsy lens.

If overlays become shareable, the registry should not look like an npm or Marketplace page. It should look like a small, hand-curated zine. Each overlay's listing is a typewritten card with three fields: who made it, what it strips, why. Example card:

```
python-trim
@stuart
strips numpy from MCP unless your turn imports it.
because numpy ships 14k tokens of types you almost never need.
```

The whimsy is in the precision of human taste. A registry of overlays is a registry of opinions about what is noise. That is a much better story than "browse community plugins."

If shareable overlays ship, the registry deserves a separate brainstorm. It is its own surface.

---

## Closing note

The page should feel like it was made by someone who is mildly annoyed on the user's behalf. Not angry. Not preachy. Just a peer who has done the math, has seen the receipts, and is offering you the receipts so you can do your own math. Whimsy in this register is not jokes. It is the audacity of being specific.
