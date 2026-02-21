---
title: "My Voice Content Strategy"
type: projects
tags: [my-voice, x, twitter, content, strategy]
summary: "Content strategy for X/Twitter presence — revenue model, content pillars, first 30 days, minimum viable start"
status: active
created: 2026-02-21
updated: 2026-02-22
related: [my-voice]
project: my-voice
confidence: medium
---

# My Voice — Content Strategy

## Revenue Model

**Phase 1 (Months 1-3)**: Build audience. No monetization. Pure value creation.

**Phase 2 (Months 3-6)**: Creator revenue sharing (X ads). Requires 500+ followers and consistent posting history.

**Phase 3 (Months 6+)**: Premium content or subscriptions if audience justifies it. Newsletter tie-in potential.

**Cost**: ~$15/mo for X API access via third-party provider (TwitterAPI.io or similar).

## Content Pillars

### 1. AI Tools & Workflow

What I'm building. How I use Claude Code. Autonomous agent patterns. Real outputs, not theory.

### 2. Building in Public

Progress on Helioy ecosystem. Wins, failures, decisions. Numbers when possible (tokens, costs, time saved).

### 3. Autonomous Agents

Where the industry is going. Commentary on new releases, frameworks, approaches. Grounded in hands-on experience.

### 4. Developer Productivity

Practical tips. Things that actually work vs things that sound good. Anti-hype where warranted.

## First 30 Days

### Engagement Target

- **Week 1**: 3-5 replies/day to people I already follow. No original posts yet. Build reply muscle.
- **Week 2**: 5 replies/day + 1 original post every other day.
- **Week 3-4**: 5 replies/day + 1 original post/day.

### Content Types

| Type         | Frequency   | Purpose                                            |
| ------------ | ----------- | -------------------------------------------------- |
| Replies      | Daily (3-5) | Build relationships, show expertise                |
| Observations | 2-3/week    | Short takes on AI news/releases                    |
| Build logs   | 1-2/week    | What I shipped this week with Helioy               |
| Threads      | 1/week      | Deep dive on a topic (agent patterns, tool design) |

### Tone

See `~/.mdx/reference/my-voice.md` for the full voice specification. Summary:

- Direct, technical, no fluff
- Personal experience over theory
- Show work (screenshots, metrics, code snippets)
- Opinions welcome but grounded
- Technical precision with poetry — don't dumb down, don't over-academicize
- Anti-hype: numbers over adjectives, shipped work over speculation

### Tooling

- **Voice reference**: `~/.mdx/reference/my-voice.md` — the voice source of truth
- **Skill**: `helioy-tools:my-voice` — drafts content in Stuart's voice
- **Content strategy**: this document

## Tech Stack

```
Claude Code (primary interface)
    ↓
My Voice MCP Server (v0.1)
    ├── Feed fetching (TwitterAPI.io)
    ├── SQLite local storage
    ├── Reply drafting tools
    └── Post composition tools
    ↓
X API (posting, reading)
```

The MCP server is the interface — no separate app. Everything happens inside Claude Code conversations.

## Minimum Viable Start

What's needed to start posting (v0.1 — ALP-112):

1. **MCP server scaffold** (ALP-113) — basic server Claude Code can connect to
2. **X API provider** (ALP-114) — sign up, get credentials, verify access
3. **X API auth** (ALP-115) — authenticate, make calls work
4. **Feed fetching** (ALP-117) — pull timeline into SQLite
5. **MCP tools** (ALP-118) — expose feed data to Claude

**Skip for now**: Follow graph archaeology (v0.2 / ALP-119). Voice profiling. Draft management. Start posting manually first using feed context, build the voice profile tools after establishing a posting habit.

## What Success Looks Like (30 Days)

- Posting daily with AI-assisted drafting
- 50+ meaningful replies sent
- 10+ original posts published
- At least 1 thread that gets engagement
- Feed monitor running, surfacing relevant content
- Clear sense of what topics resonate
