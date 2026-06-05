---
title: Transport Matters Launch
type: projects
tags: [transport-matters, helioy, launch, knowmore-context, helioy-matters, my-voice]
summary: Living launch plan for Transport Matters (manicure rename) and the Helioy editorial brand. Locked decisions, buffer plan, day-by-day schedule, status per post.
status: active
created: 2026-04-28
updated: 2026-04-29
project: transport-matters-launch
confidence: high
related: [my-voice, my-voice-content-strategy, level-up-social-media-engagement-2026]
---

# Transport Matters Launch

Living document. Updates as posts ship and decisions evolve. The launch window is a 7-day editorial warm-up (`@KnowMoreContext` only) followed by Day 7 product reveal (`@HelioyMatters` joins).

## Locked decisions

### Brand and identity

| Decision | Value |
|---|---|
| GitHub org | `littleorgans` (Stuart also owns `littleorgans.com`) |
| Consumer brand surface | Helioy (helioy.com) |
| Editorial brand | Know More Context (knowmorecontext.substack.com) |
| Product (this launch) | Transport Matters (renamed from manicure) |
| License | MIT |
| Repo path | `littleorgans/transport-matters` |
| PyPI package | `transport-matters` (claim defensively before launch) |
| CLI binary | `transport` (e.g. `transport claude`, `transport codex`, `transport doctor`) |

### Distribution

| Decision | Value |
|---|---|
| Install pattern | `curl ... | bash`, existing manicure `install.sh` pattern (uv + uv tool install) |
| Build pipeline | Existing `release.yml`, retag with new package + repo path |
| PyPI trusted publishing | Reconfigure for `transport-matters` project, owner `littleorgans`, repo `transport-matters` |
| Old `manicure` PyPI project | Deprecate with pointer to new, stop publishing after one transition release |

### Web (helioy.com)

| Decision | Value |
|---|---|
| Framework | Astro (migrate from current Vite + custom SSG) |
| Hosting | Vercel (`@astrojs/vercel` adapter) |
| Content model | Products as MDX + blog as MDX, Astro content collections |
| Newsletter | Custom form on `/blog` redirects to `knowmorecontext.substack.com/subscribe?email=...` |
| TM card | Image #2 with current production UI screenshot swapped in (~30-60 min) |
| AM/CM/FMM cards | 1 day each, ship post-launch as micro-moments |

### X strategy

| Decision | Value |
|---|---|
| Editorial account | `@KnowMoreContext` |
| Product account | `@HelioyMatters` |
| Strategy | Brand-first dual-account, editorial warms up Week 1, product joins Day 7 |
| Premium+ | Both accounts from Day 1 (solves off-platform link distribution penalty per research) |
| Cadence | 1 post/day, 5 days/week, 2-3 quote-RTs/day |
| Buffer | 7-10 posts maintained at all times |
| Voice register | The Tinkerer (full doc at `~/.mdx/reference/my-voice.md`) |
| Editorial position | Hierarchy `prompt engineering → context engineering → transport layer` |
| Closing taglines | "Token matters" (singular, editorial close) and "Every token counts" (Helioy ecosystem). Used sparingly. |

## Cross-references

- **Voice source of truth**: `~/.mdx/reference/my-voice.md`
- **Growth research**: `~/.mdx/research/level-up-social-media-engagement-2026.md`
- **Content strategy (older)**: `~/.mdx/projects/my-voice-content-strategy.md`
- **Manicure repo (current)**: `~/Dev/LLM/DEV/helioy/manicure/`
- **helioy.com**: `~/Dev/LLM/DEV/helioy/helioy.com/`

## Buffer plan

Status per post:
- **Locked**: approved, ready to publish
- **Drafted**: written, awaiting review
- **Planned**: anchor noted, no draft yet
- **Pending material**: needs real repo, logs, or screenshots before draft

### Pinned post (`@KnowMoreContext`)

**Status**: Locked

```
Context is a web that compounds.

System messages, tool descriptions, env-driven instructions, "do this", "do not do that"... all stacked together, all sent over the wire on every turn.

I have been watching my own. Sharing what I find here.
```
Characters: 244/280

Note: closing line uses "Sharing what I find here" which is a verbal commitment to the account's purpose, not a per-post anticipation closer. Acceptable as a permanent pinned anchor; would be rejected on a regular post.

### Day 1 — Read-a-file teaser

**Status**: Locked

```
What does Claude Code send to Anthropic when you ask it to read a file?

I started watching mine and what I witnessed changed how I think about agents.
```
Characters: 155/280

### Day 2 — 50k LOC review teardown (Claude vs Codex)

**Status**: Pending material

Anchor: "What happens when you ask Claude to review your 50k LOC project? How does Codex do it?" Real repo, real logs, side-by-side breakdown. Long thread, probably 6-10 posts. Needs the actual repo and the actual intercepted logs to draft against.

### Day 3 — Hidden prompts deep dive

**Status**: Planned

Anchor: layered reveal of what is actually inside the system message Claude Code sends. Multiple screenshots, walkthrough of unexpected sections. Long thread.

### Day 4 — mitmdump tutorial

**Status**: Planned

Anchor: "you can do this in 5 minutes today." Tutorial-style thread, low-stakes, high-share. Demonstrates that anyone can replicate Stuart's vantage point with off-the-shelf tooling. Bridges the editorial account to a wider audience.

### Day 5 — Managed vs ephemeral runtimes

**Status**: Planned

Anchor: educational thread on session lifecycle. Why some sessions persist, why others are ephemeral, what that means for context cost.

### Day 6 — Claude/Codex transport contrast

**Status**: Planned, possibly redundant with Day 2

If Day 2 lands the concrete contrast, Day 6 zooms out to abstract transport-model differences (reverse proxy vs explicit HTTPS proxy, what each implies for control). If Day 6 stays redundant with Day 2, drop and replace with a Reserve slot promotion.

### Day 7 — Synthesis + launch reveal

**Status**: Planned

Anchor: short post on `@KnowMoreContext` synthesizing the week. `@HelioyMatters` posts the product reveal thread (drafted closer to date). Editorial account quote-RTs with framing. Blog post live on helioy.com/blog, dev.to cross-post with `canonical_url`, Substack email goes out.

### Reserve A — (elevated to Pinned)

The "tokens matter" anchor became the pinned post. Reserve A slot is now empty.

### Reserve B — Enhance-prompt observation

**Status**: Planned (sequencing decision pending)

Anchor: general observation on how to ask the agent to tease out what you actually want. The `enhance-prompt` skill (not yet built in `helioy-tools/skills/`) becomes a follow-up post when it ships.

Open question: post first as general observation with skill follow-up, or build skill first and post is the demo?

### Reserve C — Context management controls

**Status**: Planned

Anchor: trimming, compacting, summarization. The control surface most users do not know exists. Lead-in to the Transport Matters override system if timed near launch.

## Day-by-day schedule (warm-up week)

| Day | Date | Account | Action |
|---|---|---|---|
| Day 0 | (T-1) | `@KnowMoreContext` | Premium+ subscription active, profile set up, pinned post published |
| Day 0 | (T-1) | `@HelioyMatters` | Premium+ subscription active, profile set up, no posts yet |
| Day 1 | Launch+0 | `@KnowMoreContext` | Day 1 post + 3-5 quote-RTs of high-signal accounts |
| Day 2 | Launch+1 | `@KnowMoreContext` | Day 2 thread (50k LOC review) + replies + reply-of-reply on big accounts |
| Day 3 | Launch+2 | `@KnowMoreContext` | Day 3 thread (hidden prompts) |
| Day 4 | Launch+3 | `@KnowMoreContext` | Day 4 thread (mitmdump tutorial) |
| Day 5 | Launch+4 | `@KnowMoreContext` | Day 5 thread (runtimes) |
| Day 6 | Launch+5 | `@KnowMoreContext` | Day 6 post (synthesis or contrast, TBD) |
| Day 7 | Launch+6 | Both | `@HelioyMatters` reveal, `@KnowMoreContext` quote-RTs, blog + dev.to + Substack go live |

Concrete dates fill in once Day 0 is set.

## Open items

### Pre-launch build work

- [ ] Manicure → Transport Matters rename audit (full sweep, test gate, smoke test)
- [ ] Repo rename + transfer to `littleorgans/transport-matters`
- [ ] PyPI: claim `transport-matters` defensively, reconfigure trusted publishing
- [ ] helioy.com Astro migration (port 9 product pages, blog scaffold, RSS, sitemap)
- [ ] TM card screenshot swap (latest production UI)
- [ ] Anchor blog essay drafted and scheduled
- [ ] dev.to account creation, canonical URL setup
- [ ] knowmorecontext.substack.com publishing flow verified

### Buffer drafting

- [ ] Day 2 thread (pending real repo + logs)
- [ ] Day 3 thread (hidden prompts)
- [ ] Day 4 thread (mitmdump tutorial)
- [ ] Day 5 thread (runtimes)
- [ ] Day 6 post (synthesis or transport contrast, decide after Day 2 lands)
- [ ] Day 7 reveal post for `@HelioyMatters`
- [ ] Reserve B (enhance-prompt) sequencing decision
- [ ] Reserve C (context management controls) draft

### Post-launch drip

- [ ] AM card (1 day)
- [ ] CM card (1 day)
- [ ] FMM card (1 day)
- [ ] Follow-up blog posts (drip every 3-4 days)

## Decision log

Brief record of when each decision locked, with conversation context.

### 2026-04-28
- Org: `littleorgans` locked. Stuart owns `littleorgans.com`. One sarcastic friend reaction surfaced ("little organs of little humans is a horror movie"); single data point, weak signal, kept.
- Brand handles: brand-first dual-account locked. `@HelioyMatters` (product) + `@KnowMoreContext` (editorial). Personal `@srobinson` (1,624 following / 68 followers / 0 tweets) parked.
- License: MIT. No IP in this package per Stuart.
- Distribution: keep manicure's existing `install.sh` (curl + uv). Path A (rename in place) chosen over Path B (rewrite for npm-style binary distribution) because of 7-day window.
- CLI binary: `transport` (over `transport-matters` literal or `tm` short alias).
- helioy.com migration: Astro on Vercel, products + blog as MDX, custom newsletter form redirects to Substack.
- Voice persona: The Tinkerer. Full doc rewritten from scratch at `~/.mdx/reference/my-voice.md`.
- Editorial hierarchy: prompt engineering → context engineering → transport layer. The argument is shown through evidence, never asserted.
- Cadence: Steady (1 post/day, 5 days/week, 2-3 quote-RTs/day). Buffer-first.
- Pinned post: option B locked.
- Voice corrections this session: Tinkerer register established, "we" usage narrowed (no discourse-participation), "Token matters" singular, conversational precision (not informal grammar), density principle (not absolute brevity), no unverified claims (foundation rule), no anticipation closers ("either share or shut up").

### 2026-04-29
- Premium+ on both accounts from Day 1 (after research surfaced off-platform link distribution penalty for non-Premium accounts since March 2025).
- Day 1 post locked: "What does Claude Code send to Anthropic when you ask it to read a file? I started watching mine and what I witnessed changed how I think about agents."
- Day 2 anchor changed from `ENABLE_TOOL_SEARCH` token-diff to "50k LOC review: Claude vs Codex teardown." Pending real repo + logs.
- Deep research delivered: `~/.mdx/research/level-up-social-media-engagement-2026.md`. Six load-bearing findings: Grok-powered ranker, reply-of-reply ~75x weight, external link suppression without Premium, Buffer 18M-post analysis, engagement bait suppression, Stuart's voice = slower curve / higher quality followers.

## How this document evolves

Update on every decision lock, every post draft, every status change. When the launch ships, archive this file under `~/.mdx/projects/archive/` and start a fresh launch plan for the next product.
