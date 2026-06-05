---
title: Manicure Landing — UX Researcher Brainstorm
type: projects
tags: [manicure, landing-page, ux-research, audience, personas, jtbd, objections]
summary: Audience profiling and pressure-test of landing page assumptions. Three personas, top JTBDs, visitor questions, skim test, objections, trust failures, cuts, and a read on the overlays idea.
status: draft
project: manicure
confidence: medium
created: 2026-04-14
updated: 2026-04-14
---

# Manicure Landing — UX Researcher Brainstorm

## Framing premise

This page talks to developers who already bought into Claude Code and who are mid-way through discovering that agents leak quality as context grows. They are not a general dev-tool audience. They have MCP servers installed, settings.json files with opinions, and a bill that has crept upward. The landing's job is to confirm a suspicion they already half-hold, then show them how to look at the evidence.

If the first scroll has to choose between teaching them something about their own setup and telling them something about the product, it should teach.

---

## 1. Audience personas

Three archetypes cover the realistic visitor mix. Each is a synthesis of observable Claude Code community behavior, not a hypothetical.

### A. Malik, the MCP Maximalist

Senior product engineer at a 40-person startup. Runs Claude Code on a daily basis, has installed twelve MCP servers over six months (Linear, Supabase, Playwright, a couple of custom internal ones), and rotates through a dozen skills. His `settings.json` has grown through accretion. Has noticed that long sessions degrade: Claude forgets, loops, fabricates tool results. He has no framework for what is going wrong, only a vague sense that the agent feels dumber the longer he works. Currently "solves" this by starting new sessions more often and clearing context. He skim-reads dev tool posts and clicks through from a Hacker News comment or a peer Slack link.

**Stack**: macOS, Claude Code in a terminal, heavy MCP usage, no custom proxy.
**Skepticism**: medium. Bought-in on Claude, wary of anything that adds middleware.
**What brought them**: a comment saying "your agent is probably shipping way more than you think."

### B. Priya, the Observer

Backend engineer, ten years in, half of them spent in security-adjacent work. Used Burp, Charles, and mitmproxy before LLMs existed. Uses Claude Code but keeps one foot out the door. Does not fully trust a vendor-controlled terminal to tell her what it is doing. She has run `tcpdump` on her own laptop to look at Claude Code traffic once, got put off by TLS, and gave up. Wants the wire-level truth. Clicks through to Manicure because the word "reverse proxy" appears in the description and she wants to see if the tool is serious or cosmetic.

**Stack**: Linux, Claude Code, comfortable with mitmproxy and network tools.
**Skepticism**: high. Will read the GitHub before reading the landing.
**What brought them**: skepticism about agent internals, a desire to audit.

### C. Dev, the Token Accountant

Indie developer or small-team lead. Uses Claude Code as core infrastructure for customer work. Their API spend matters at a line-item level. Has already cut things: fewer thinking tokens, tighter system prompts, a custom CLAUDE.md, careful about model choice. Suspects more savings are possible but does not know where. Reads the Anthropic usage dashboard but finds it coarse. Tried rolling a wrapper script once, abandoned it.

**Stack**: varied, usually macOS or Linux, Claude Code plus a handful of project CLAUDE.md configs.
**Skepticism**: medium-high. Burned out on "save X% on LLM spend" claims.
**What brought them**: a hint that they could see per-request cost attribution at the tool level.

---

## 2. Jobs-to-be-done

Top five JTBDs visitors arrive with, ordered by likely weight. Each lists the status-quo alternatives they already use.

1. **"Tell me what my agent is actually sending so I can stop guessing."**
   Current alternatives: Anthropic dashboard (too coarse), mitmproxy rolled by hand, asking Claude to print its own context (unreliable), giving up.

2. **"Help me figure out why Claude goes off the rails in long sessions."**
   Current alternatives: start fresh sessions frequently, trim CLAUDE.md, disable MCP servers one at a time, read forum threads.

3. **"Give me a way to strip the noise without breaking my setup."**
   Current alternatives: manually toggle MCP servers in settings.json, comment out skills, maintain separate profiles.

4. **"Let me experiment on the payload before I commit to a config change."**
   Current alternatives: edit settings, restart, observe, repeat. Slow and error-prone.

5. **"Prove to me that context bloat is a real quality problem, not just a bill problem."**
   Current alternatives: anecdotal evidence from Twitter, blog posts, their own hunches.

Note the shape. Items 1, 2, and 5 are diagnostic. Items 3 and 4 are curative. The landing must open on diagnosis. Cure comes second.

---

## 3. Top five silent visitor questions

The page should answer these in roughly this order as the scroll unfolds.

1. **"What am I looking at?"** (3 seconds)
2. **"Why is this a problem I haven't already noticed?"** (the gut-punch moment)
3. **"Show me it is real. What do I actually ship every request?"** (data, not claims)
4. **"What does this do, concretely? Is it safe?"** (mechanism, installation stakes)
5. **"Why should I trust this instead of writing my own?"** (positioning against the DIY impulse)

If the page answers these in the wrong order, it reads as a sales pitch. If it answers them in this order, it reads as a diagnostic.

---

## 4. Eight-second skim test

If a visitor leaves after eight seconds, three beats must have landed:

1. **Your agent ships a lot more than you think.** A concrete token or kilobyte number in the first viewport. The 285 KB figure with the 67% tools breakdown is the single strongest artifact the landing has. Put it near the top.

2. **This is a tool for looking, not a tool that sells a fix.** The visual and copy register as Burp Suite, Wireshark, or Charles, not as a SaaS product page. Terminal font, live payload rendering, no hero illustration of a smiling developer.

3. **It is one command to install and it does not touch your system.** No cert install, no sudo, localhost only. Visible in the first scroll. Removes the "this will mess with my machine" reflex.

Nothing else matters at eight seconds. Personas A and C especially will bounce if a product pitch runs before the data does.

---

## 5. Five objections and their counters

1. **"I can do this myself with a small proxy script."**
   *Counter*: Yes, and also: the IR normalization, the round-trip invariant, the rule scoping by session/model/account, and the audit trail are the parts that a weekend script never grows into. A one-line hook in the landing: "You could write this in a weekend. It will stay a weekend project."

2. **"Another middleware between my agent and the model, slowing my loop."**
   *Counter*: Honest performance number. Latency overhead stays under the noise floor of the Anthropic API itself. Put the actual measured latency delta on the landing, not hand-wavy "negligible" wording.

3. **"I trust Anthropic and Claude Code to ship a clean request."**
   *Counter*: Not an argument about trust. Show the real request. The payload is what it is, regardless of whether anyone is to blame for its shape. The data does the work.

4. **"mitmproxy already exists. Why a wrapper?"**
   *Counter*: mitmproxy is the transport. Manicure is the schema. A rules UI over typed IR is the thing mitmproxy does not give you. A single line acknowledging that the product is a thin layer on mitmproxy buys credibility with Persona B specifically.

5. **"Premature optimization. Prompt caching already handles repeated payloads."**
   *Counter*: This is the most important one to answer well because it is technically informed and half-right. Caching handles the cost side. It does not change what the model attends to. Every token in the context competes for attention whether or not it was a cache read. Noise is noise. Anchor this with the Confident Narrator finding. Show that the model hallucinates tool execution when the shape of the payload is inconsistent, and point out that no cache solves that.

---

## 6. What the landing cannot make believable on first contact

Claims to push later in the funnel (docs, demo video, blog, follow-up post):

- **"Improves response quality."** Quality claims without a user's own session to compare against will read as vendor puffery. Defer to a blog post with captured before/after traces.
- **Any percentage number for token reduction.** "Cut 60% of your tokens" will be read as marketing regardless of whether it is true. Let the user measure their own savings; show one honest raw capture instead.
- **"No risk to your setup."** Developers will decide this themselves by reading the install script. Do not argue for it. Let the curl command be auditable and short.
- **"Helioy ecosystem integration."** On the V1 landing, this is future-facing and dilutes the core pitch. Mention it only in a footer "Roadmap" link.
- **The three-pillar abstraction itself** (Surface, Realize, Tamper). These are internal framing. Naming them to the user is abstraction for abstraction's sake. Show, do not categorize.

---

## 7. Five things to cut that usually appear on dev-tool landings

1. **Hero video with a smiling developer at a laptop.** Replace with a live terminal or a static rendering of a real payload.
2. **"Trusted by teams at" with logos.** Manicure has no such teams yet, and the audience smells this from orbit.
3. **Feature checklist grid with icons.** Every checkbox feature lands as filler. The product has six rule actions and a breakpoint. Describe them in plain prose or omit them from the landing.
4. **FAQ accordion.** An FAQ is where honest copy goes to die. Fold every question worth answering into the main scroll as part of the argument.
5. **Email capture above the fold.** Developers bounce on anything that demands an address before showing a screenshot.

Each of these cuts raises the diagnostic-tool register and lowers the product-pitch register. That trade is the entire point.

---

## 8. The shareable overlays idea

From a UX research angle, this has real pull but it is not the hero of V1.

**What is attractive**: overlays as teaching artifacts is a genuinely strong frame. "Install Stuart's Python trim and watch it fire" is a form of pedagogy that dev tools rarely get right. Persona A (the Maximalist) responds to this most: he has no mental model for what to strip, so adopting someone else's curated view is useful and socially acceptable. It also creates a growth loop: the best overlays become content, content drives installs.

**Why it stays a footnote in V1**: The landing's job is to move the visitor from "my agent is fine" to "my agent is loud." Overlays are the answer to a question the visitor has not asked yet. Leading with a shareable overlays gallery skips the diagnostic step and lands as a marketplace feature, which is exactly the product-pitch register to avoid.

**Where it belongs**: one paragraph on the landing, late in the scroll, framed as "what this shape of tool unlocks." A separate sub-page when overlays land as a V2 feature. The paragraph copy should describe overlays as readable documents rather than as a feature, because the teaching-artifact angle is stronger than the convenience angle. Example framing: "A published overlay is someone else's curation made legible. You install it, watch it run, and read what they chose to cut and why."

**Signal this is working**: if overlay installs become a common way people first try Manicure (via a peer sharing one), the frame was correct. If they sit unused, the feature was a distraction.

---

## Cross-cutting note on tone

The landing copy currently sitting in `src/sections/Hero.tsx` already holds the right register. "You typed 'Hello'. Your agent sent 285,000 tokens to deliver it." That sentence is the strongest line on the current page because it is diagnostic, not promotional. Every other section on the landing should be measured against that sentence. If a paragraph reads as promotional next to it, the paragraph is wrong.

The second strongest artifact the product has is the Confident Narrator finding: strip tools from the payload, and the model fabricates tool execution with total confidence. Put this somewhere on the landing. It is the single clearest demonstration that "more is less" is a structural claim about how LLMs work, not a product talking point. Persona B (the Observer) will bookmark it. Persona C (the Accountant) will share it.

## Open questions worth pressure-testing with users

- Does the 285 KB number land as shocking, or as "sure, tools are big"? Test on three Claude Code users who do not already know the tool.
- Is the `ANTHROPIC_BASE_URL` step a stopper? Some users will read "set an env var to route through a proxy" and worry about enterprise policy or auth.
- Does "no cert install" register as a differentiator, or is it invisible to anyone who has not tried to run mitmproxy with TLS before?

These three are the cheapest things to validate before the landing ships. Even one fifteen-minute call per persona would de-risk the first-scroll claims.
