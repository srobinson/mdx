---
title: Manicure Landing Refactor — Dev Brief
project: manicure
role: frontend-engineer
orchestrator: manicure.sh:general:3:1.1
reviewer: manicure.sh:helioy-tools:engineering-code-reviewer:3:2.2
created: 2026-04-14
---

# Manicure Landing: Dev Brief

## Project context

Manicure is a reverse proxy between coding agents (Claude Code, Codex) and Anthropic's `/v1/messages` API. It captures, visualizes, and allows tampering with payloads before they reach Claude. Manicure v0.0.1 is live.

The landing page lives at `/Users/alphab/Dev/LLM/DEV/helioy/manicure.sh`. Branch `exp/anim`. Stack: Vite + React + TypeScript + Tailwind.

Audience: skeptical Claude Code users who already run mitmproxy, tcpdump, or read payloads by habit. Register: Burp Suite, Wireshark, Charles, mitmproxy, Observable Framework. The page is a diagnostic tool dressed as a landing page. It argues against the visitor's current setup, not for the product.

## Required reading (in order)

1. `~/.mdx/projects/manicure-landing-synthesis.md` — warroom convergence, 9 open decisions, tensions
2. `~/.mdx/projects/manicure-landing-ux-architect--brainstorm.md` — diagnostic essay archetype, section outline, CTA architecture
3. `~/.mdx/projects/manicure-landing-ui-designer--brainstorm.md` — visual register, color semantics, missing primitives (Appendix B)
4. `~/.mdx/projects/manicure-landing-brand-guardian--brainstorm.md` — voice rules, anchor words, never-say list
5. `~/.mdx/projects/manicure-landing-visual-storyteller--brainstorm.md` — 8-scene arc, "The Stack" running visual thread
6. `~/.mdx/projects/manicure-landing-whimsy-injector--brainstorm.md` — tone references, whimsy moments, footer
7. `~/.mdx/projects/manicure-landing-ux-researcher--brainstorm.md` — personas, 8-second skim test, cut list

Read the source document before writing any code.

## Known drift in the warroom artifacts

All brainstorms and the synthesis reference a fabricated `285,000 tokens` number in the hero copy. That number exceeds Claude Opus 4.x's 200K context ceiling and is impossible for a single `/v1/messages` request. It has been replaced in `src/sections/Hero.tsx` with measured data from Manicure v0.0.1:

- `45,728 tokens` (from `input_tokens` field in a captured opus-4-6 request)
- `28 tool schemas` (from capture metadata)

Treat the updated hero subline as correct. Ignore `285,000` references in the brainstorm files. The synthesis and agent files are frozen records from a point in time — do not rewrite them.

## Decisions already locked (do not revisit)

1. **Hero H1**: keep `See what your coding agent ships.` Unchanged.
2. **Interactive exhibit**: pre-baked JSON payload + scripted response deltas, visibly footnoted as pre-recorded. No paste-your-own. No real-time proxy.
3. **Three pillars** (Surface / Realize / Tamper): retroactive compact captions AFTER the exhibit. Not upfront. No bullets, no "learn more" chevrons.
4. **Overlays section**: CUT in v1 unless 3+ real overlays exist. Do not stage a teaser tile.
5. **Typography**: JetBrains Mono only. Source Serif 4 italic reserved for up to 2 pullquotes — do not introduce unless spec calls for it.
6. **Decorative motifs**: ruler ticks on left edge (quiet measurement cue). No stamp motif. Stamp defers with overlays.
7. **Hero CTA**: remove the "Get started" button. Keep the `$ manicure start` code display and hook line. Install CTA lives in its own section at the bottom.
8. **Shareable diagnostic URL**: toggle state serializes into URL fragment. Teammate opens the URL and sees the same configured exhibit.

## Phased scope

### Phase 1 — Hero tightening

- `src/sections/Hero.tsx`: remove the "Get started" button link. Keep the `$ manicure start` code display and the hook line ("One command. Spawns the proxy, launches Claude, opens the canvas."). Do not change the H1 or subline copy — both are already correct.
- Verify JetBrains Mono is the only font loaded. Strip any sans fallback chain. Confirm the body reads as mono throughout.
- Confirm all numbers use `tabular-nums` and ideally `font-variant-numeric: slashed-zero`. If a number on the page uses proportional digits or has an unslashed zero, fix it.

### Phase 2 — Section restructure

- Audit `src/sections/` for current inventory. Report back what exists.
- Kill the problem-to-solution funnel shape: Problem / Revelation / Comparison / HowItWorks / TokenEconomics should collapse into a single interactive diagnostic section (implemented in Phase 4).
- Move the Pillars section to AFTER the (future) exhibit and reduce to compact retroactive captions: one noun + one short line + one micro-visual per pillar. No bullets, no chevrons.
- Replace `BottomCTA.tsx` with a plain install block: one `card-flush` code block with copy-button, one line above naming the install surface (e.g. `pipx install manicure` or whatever the current channel is — check the README at the repo root), one line below linking to the deeper read.

### Phase 3 — Primitives (UI designer's Appendix B)

Build these as standalone components in `src/components/`:

- `Stack.tsx` — vertical block inventory of a captured payload. Each block has: type, token count, preview snippet, state (active / dimmed / struck). Rose strikethrough + 40% opacity on disabled blocks.
- `PayloadStrip.tsx` — horizontal live telemetry strip (optional; see UI designer doc before committing to it — HUD + strip may be redundant).
- `Counter.tsx` — mechanical token counter. Tabular-nums. Animates between values. Amber accent.
- `ManifestCard.tsx` — overlay card layout. Build the primitive, do not surface — overlays are cut in v1.
- `TamperToggle.tsx` — toggle with rose accent when active, `txt-2` gray when inactive.
- HUD slot in `src/App.tsx` — top-right persistent `session N / turn N / tokens N` element. Reflects Stack state.

Each component ≤700 lines. Most will be far smaller.

### Phase 4 — Exhibit

- `src/sections/Diagnostic.tsx` — load-bearing exhibit. Three-column layout: Block Inventory / Expanded Block JSON / Tamper Panel. Pre-baked payload loaded as static JSON from `public/payloads/` or `src/data/`.
- Scripted response deltas keyed on a small set of salient toggle combinations (e.g. ~10 curated deltas). Store as JSON.
- Visible footnote: `responses are pre-recorded examples.`
- Toggle state → URL fragment serialization. Reload restores state. Share URL = teammate sees the same exhibit.

### Phase 5 — Polish

- Ruler ticks on left edge as subtle measurement motif. Static SVG or CSS, not animated.
- Accent economy (max 2 per viewport): sky = intent, sage = kept, amber = mass, rose = tamper, lavender = annotation, teal = dormant (overlays).
- Motion: only fluorescent ignition (existing) + mechanical counter (new). No parallax. No ambient fade-in-on-scroll.

## Voice and copy rules (non-negotiable)

From `brand-guardian` + `whimsy-injector`:

- No em dashes anywhere. No en dashes. Hyphens only where punctuation demands it.
- No "It is X, not Y" or "not X, it is Y" patterns.
- No exclamation marks.
- Anchor words: Forensic, Meticulous, Candid, Dry, Spare.
- Forbidden phrases: `supercharge`, `10x`, `save on API costs`, `the future of AI development`, `trusted by engineers at [logos]`, `AI magic`, `intelligently`, `powered by`, `coming soon`, `Phase 2`, `learn more` (as a CTA).
- No exclamation marks in microcopy, error states, or the install confirmation.
- Every claim with a measurement. Measurements from Manicure captures only — no fabricated numbers.

## Workflow

1. Start with Phase 1. Work on branch `exp/anim` (do not create a new branch). Do not commit unless the user explicitly tells you to — run `git status` at the end and let the user decide.
2. When Phase 1 is done and `pnpm build` + `pnpm typecheck` both pass, notify the reviewer (`manicure.sh:helioy-tools:engineering-code-reviewer:3:2.2`) with a single-line message asking for review. CC the orchestrator (`manicure.sh:general:3:1.1`).
3. Apply reviewer feedback. Re-notify reviewer, CC orchestrator.
4. Iterate until reviewer approves.
5. When reviewer approves a phase, notify the orchestrator: `Phase N complete. Ready for Phase N+1.` — wait for orchestrator to greenlight before starting the next phase.

## Hard rules

- Never skip `pnpm typecheck` and `pnpm build` before marking a phase done. If tests exist, run them too.
- Never introduce new dependencies without orchestrator approval. Work with what's installed.
- Never overwrite the warroom artifacts in `~/.mdx/projects/`.
- Files ≤700 lines. Refactor before adding.
- If any decision above conflicts with something you find in the codebase or the references, send a single-line question to the orchestrator and pause. Do not invent.
- Validate before you act. Read the file, grep the symbol, open the bundler config. Never assume.

## Reply convention

- One line per notification: `Done. <one-sentence delta>. Ready for review.` or `Applied feedback. Re-ready.`
- Do not summarize your work — the diff speaks.
- If you hit a wall, escalate in one line: `Blocked on <specific question>. Need input from <agent_id>.`

Acknowledge this brief with a single line, then begin Phase 1.
