---
title: Manicure Landing Page, Visual Storyteller Brainstorm
project: manicure
lens: visual-storyteller
author: design-visual-storyteller (helioy-bus)
date: 2026-04-14
status: draft
audience: Stuart (review)
related:
  - ~/.mdx/projects/manicure.md
  - ~/.mdx/projects/manicure-ux-design.md
---

# Manicure Landing Page: Visual Storyteller Brainstorm

Treat the page as an eight frame film. The camera is the scroll. The protagonist is the visitor. Manicure does not appear as a product until after the visitor has been implicated in the problem.

The current page already runs a fluorescent tube flicker motif and an ignition effect on scroll-enter. The existing Hero copy ("You typed 'Hello'. Your agent sent 285,000 tokens to deliver it.") is the right hook and survives this pass unchanged. The brainstorm below extends that foundation.

---

## 1. Story spine

> The visitor arrives curious about a diagnostic tool, sees the grotesque size of a request they thought they understood, recognizes most of it as clutter they personally authorized, and leaves the page less confident about their own setup and more willing to look at what they ship.

The turn lives in the middle: the moment the visitor stops reading about Manicure and starts auditing themselves.

---

## 2. Scene breakdown

Eight scrolls. Each scene names a (a) headline or prompt, (b) what the visitor sees, (c) what the visitor feels, (d) what they now believe.

### Scene 1. Ignition

a. Headline: *See what your coding agent ships.*
b. The page flickers on like a fluorescent tube. A chip reads "Context control plane." Below the flicker, a quiet paragraph: the visitor typed "Hello" and their agent sent 285,000 tokens to deliver it.
c. Mild alarm. A recognition that someone has been paying attention to something they have not.
d. The size of a request is not the size I think.

### Scene 2. The autopsy

a. Headline: *Here is one request. Here is what was in it.*
b. Center of viewport: a single vertical column representing one `/v1/messages` body. Stacked blocks labeled System prompt, Tool definitions, MCP servers, Skills, Conversation, Thinking blocks, User message. Sizes proportional to bytes. A thin sky coloured stripe marks the user message. Everything else is grey.
c. Queasy. The first real look at a thing they had assumed was small.
d. I have never actually seen my own payload.

### Scene 3. The inventory

a. Headline: *Every block has a ledger.*
b. The stack from Scene 2 expands. Each block shows byte count and a "last referenced" tag. Most blocks read "never referenced in this session." Tool definitions show "0 calls." MCP servers show "idle." A small footer tallies the dead weight as a percentage.
c. Embarrassment with a flicker of indignation. Who decided this was ok.
d. Most of what I installed is doing nothing and it is riding along on every turn.

### Scene 4. Noise costs answers

a. Headline: *Same prompt. Same model. Two payloads.*
b. Split screen. Left: the full payload from Scene 3. Right: the same request with eighty percent of the stack removed. Below each: the actual response. The right hand response is tighter, more specific, better. A caption quotes the measured difference in a single line.
c. Incredulous. This is not a caching story.
d. Unused context is not free. It degrades the answer.

### Scene 5. The reveal (emotional center, see §3)

a. Headline: *Turn something off.*
b. The stack becomes interactive. Cursor hovers a tool row. A checkbox appears. Click. The tool's definition greys and slides out of the column. The column shortens visibly. A byte counter drops. The model responds. Nothing else on the visitor's machine changed.
c. A small private thrill. Permission.
d. This thing is editable. I have been allowed to be passive for too long.

### Scene 6. The canvas

a. Headline: *Every token, every turn.*
b. Pull back to show the full Manicure canvas around the stack: tabs for Tool calls, Sub agent contexts, Plans, Thinking blocks. Each panel is a lens on content that used to be hidden inside a black box. Cursor moves through the panels. The stack is always visible on the left as a constant.
c. Orientation. The quiet relief of realizing the tool already knows what you want to look at next.
d. There was always a surface here. I just did not have an instrument.

### Scene 7. Overlays as teaching artifacts

a. Headline: *Curation is a practice. Install someone else's.*
b. A tile grid of published overlays. "Python trim" by Stuart. "React without the dead hooks" by someone. Each tile shows what the overlay strips and why, in plain language. Hover plays a short loop of the overlay running on the stack: blocks greying, column shrinking, response returning.
c. Curiosity tipping toward trust. The same way a good dotfile repo feels.
d. I can learn curation by watching people I respect curate.

### Scene 8. Close

a. Headline: *Care for your cargo.*
b. The stack fades. A single card remains: `manicure start`. Beneath it, the gloss: "mani·cure: manifest and curate." Apache 2.0, Open Source chips. No feature grid. No testimonials.
c. Sobered and equipped. The visitor was not sold anything. They were handed an instrument.
d. I was flying blind. I do not want to be.

---

## 3. The reveal moment

Scene 5 is the emotional center. It earns that status because it is the only scene where the page stops talking and hands the visitor the interaction.

What makes it work:

- **Low stakes.** A single checkbox toggles a single tool. The action is completely reversible and visibly so.
- **Immediate feedback.** The column shortens. The byte counter drops. The response returns. Cause and effect land in the same frame.
- **No product argument.** The headline is an imperative aimed at the visitor, not a claim about Manicure. The page refuses to close the sale in the same beat that it grants agency.
- **Reframes the page.** Everything before Scene 5 is diagnosis. Everything after is workshop. The visitor carries the "I can touch this" feeling through Scenes 6 and 7, which is the only way those scenes read as orientation rather than marketing.

Design detail that matters: the stack on the left of the canvas should stay in viewport across Scenes 5, 6, and 7. It is the receipt that the interaction in Scene 5 was real. If the stack resets or disappears, the reveal loses its load bearing function.

---

## 4. The running visual thread

**The Stack.**

A single vertical column representing one request payload. Every scene references it, modifies it, or is framed around it. Scene by scene:

| Scene | What the Stack does |
| --- | --- |
| 1 | Implied by the 285,000 token number. Not rendered. |
| 2 | Introduced. Blocks labeled. User message highlighted. |
| 3 | Annotated. Each block shows bytes and last reference. |
| 4 | Duplicated side by side. Shortened right hand column. |
| 5 | Becomes interactive. Shortens in response to a click. |
| 6 | Shifts left, becomes part of the Manicure canvas. |
| 7 | Appears inside overlay preview loops. Pre curated. |
| 8 | Fades. The visitor no longer needs to see it. |

Why this motif earns primacy over the fluorescent flicker:

The flicker already carries the page as a connective device for text arrival. It should keep doing that. The Stack carries the content. One is how the page turns on. The other is what the page is about. Keeping them separate keeps the flicker from becoming a gimmick and gives the Stack room to accrue meaning across scroll.

The Stack works because it behaves like a real diagnostic instrument. It starts opaque. It becomes annotated. It becomes editable. It becomes redundant. That arc mirrors the visitor's own trajectory from ignorance to agency, which is the point of the page.

Small craft notes:

- Block sizes should be proportional to real byte counts in a real recorded request. Faking the proportions would insult the audience.
- The user message stripe should be the sky colour already in the palette. No new hues.
- The "last referenced" labels should read like git blame annotations, not marketing captions.
- Block removal in Scene 5 should use a physical motion (slide out, then the stack recompacts) rather than a fade. The visitor needs to feel mass leaving.

---

## 5. Three alternative arcs

### A. Autopsy (detective mystery)

The page opens on a crime scene: a single request went out, and the visitor is invited to investigate what was in it. Tension builds as more of the payload is revealed. The reveal is that the visitor is the perpetrator: they installed the bloat.

- Strength: emotional charge, makes the visitor the subject.
- Risk: too clever. The audience smells staging.

### B. Before / after (diagnostic comparison)

Every scroll is a side by side. Left column shows what the agent sends today. Right column shows what the agent would send after Manicure curation. The scrolls accumulate a running delta counter.

- Strength: crisp. Easy to grasp.
- Risk: reads like a product comparison page. Sells rather than teaches. Violates the positioning constraint.

### C. Tour of the lab (workshop)

The visitor is given a guided walk through the Manicure canvas. Each scroll demonstrates one panel: tool calls, sub agent contexts, plans, thinking blocks. The reveal is that a manipulator has always sat between the keyboard and the model, and the visitor can step into it.

- Strength: lands the product's actual shape. Educational by default.
- Risk: competence without stakes. No emotional punch. The visitor learns what Manicure does but never feels their own waste.

### Recommendation: hybrid A → C

Autopsy framing through Scene 4. Workshop framing from Scene 6 onward. Scene 5 is the pivot.

Rationale: Autopsy carries the emotional charge that makes the visitor pay attention. Workshop carries the competence that makes them stay. The scene order above already implements this hybrid. Scenes 1 through 4 implicate the visitor. Scene 5 hands them the instrument. Scenes 6 through 8 orient them inside it.

A pure autopsy page would end with shame and no instrument. A pure workshop page would never earn the right to talk about the instrument. The hybrid respects the diagnostic tone the product requires.

---

## 6. Copy cues (Stuart's voice)

On voice rules: no em dashes, no hyphen as pause, no "X, not Y" or "not X, is Y" constructions, no AI slop, every token counts. All three drafts below pass those filters.

### Scene 1 (hook)

The existing live copy holds. Keep it.

> **See what your coding agent ships.**
>
> You typed "Hello". Your agent sent 285,000 tokens to deliver it. Your five characters were 0.002% of the request. The rest is noise competing for the model's attention.

One tightening option for the subline if Stuart wants to compress further:

> You typed "Hello". Your agent shipped 285,000 tokens to say it. Five characters. 0.002% of the payload. The rest competed with you for the model's attention.

### Scene 5 (reveal)

> **Turn something off.**
>
> Uncheck a tool you never use. Watch the request collapse. Resend the prompt. Read what Claude says when it has less to think about.

Micro caption under the interactive stack:

> Nothing on your machine changed. You just stopped shipping it.

### Scene 8 (close)

> **Care for your cargo.**
>
> mani·cure: manifest and curate. Install once. Inspect every request. Decide what travels with you.

Button: `manicure start`

Footer chip row (already live, keep): Apache 2.0, Open Source. No testimonials. No logos.

---

## 7. Decisions for Stuart

Not prescriptive. These are the three forks where a decision unlocks the rest of the work.

1. **Stack vs Fluorescent as dominant motif.** Recommend Stack for content, Fluorescent for connective tissue. Approve or redirect.
2. **Scene 5 interactivity.** The reveal depends on the visitor actually clicking. Do we ship a scripted animation that looks interactive, a real embedded payload editor, or a recorded pointer replay? Each has a different build cost and a different honesty cost.
3. **Scene 7 overlays.** Do we include overlays in the v1 page, or hold them until the feature ships? If held, Scene 7 becomes a single teaser tile with "more soon" and the page drops to seven scrolls.

---

## 8. Open questions

- The 285,000 number is specific. Is it the right calibration? A lower number (50k, 100k) might be more relatable and still shocking for anyone running a fresh Claude Code session.
- Scene 4's side by side requires real measurements. Does Manicure already have a benchmark pair we can quote, or does the launch gate on producing one?
- Do we want a Scene 0 above the Hero: a single animated token counter that counts up to 285,000 before the page flickers on? Strong but potentially theatrical. Flagging as optional.
