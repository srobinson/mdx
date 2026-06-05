# Audioface — Product Positioning, Category & Developer Adoption

Lens: what IS Audioface as a product, who is it for, and what wedge gets to 1000 real users.

## The one-sentence pitch

**Audioface is the sound contract for AI-built interfaces: one Markdown file (`AUDIO.md`) and a tiny procedural runtime that give any app a coherent, tasteful sonic identity, with zero audio files.**

Human-facing tagline: **a typeface for your interface's sound.** A typeface is a chosen, coherent visual identity for text. An audioface is a chosen, coherent sonic identity for interaction. The name already carries the category.

## The core framing problem

The real competitor is not another UI-sound library. It is **silence**, and silence is winning by default. Almost no web app has sound, and most developers actively distrust UI sound because they associate it with annoyance. So the pitch cannot be "add sound to your app." That loses to silence every time.

The two things that flip it:

1. **Silence-respecting by design.** Semantic feedback only at interaction edges, quiet by default, one-tap mute. Audioface is the difference between a cheap keyboard and a premium one: you do not notice until you feel it, and you cannot go back.
2. **A distribution channel that does not require a human to decide they want sound.** That channel is AI coding agents, and it is the whole game.

## Why NOW

AI agents are building UIs at scale and they already read contract files (`DESIGN.md`, component conventions) to match a project's system. There is a visual identity contract but no sonic one. `AUDIO.md` is deliberately the audio equivalent of `DESIGN.md`. The moment an agent building a UI can read one file and give the app a coherent sound, sonic identity becomes a default, not a specialist task. We own `audioface.dev` + npm + pypi + crates, so we can be the name of that standard before anyone else claims it.

## Ideas, ranked by impact

### 1. SHARPEST BET — `AUDIO.md` as the sonic half of the agent contract pair
Position Audioface not as a library but as **a standard**: `DESIGN.md` gave agents your visual system; `AUDIO.md` gives them your sound. The wedge to 1000 users is distribution through AI coding tools (Claude Code, Cursor, v0, Lovable, bolt), not convincing humans they want sound. Agents install what is easy to install and contract-shaped. This rides an existing, growing behavior instead of creating a new one. Everything else below serves this bet.

### 2. `audioface init` + agent skill/MCP — make the contract an install *action*
The mechanism behind bet #1. One command drops `AUDIO.md`, wires the tiny runtime, and picks a starting theme. Ship it as a Claude Code skill / MCP and a CLI so an agent can add sonic identity in one step, unprompted, the same way it adds a UI library. If the agent can *do* it, the developer never has to *want* it first.

### 3. audioface.dev as a "hear-it-first" playground, not docs
Sound is the only product that literally cannot be screenshotted. The landing page must be one click to feel it (respecting the user-gesture constraint). Hero = a live interaction flow (command confirm, toggle snap, toast arrive) that feels physical and premium, then reveals it is procedural, zero files, one config object. Token gallery + live theme composer + export are the conversion engine. This page is where the "aha" happens.

### 4. Shareable sonic themes as the growth loop
Every theme composed on audioface.dev gets a URL and an exportable `AUDIO.md`. Sharing "here is the sound identity I made" is the marketing. Themes are the shareable artifact that spreads the category, the way a shared color palette or font pairing does. Presets (Studio, Console, Soft Office, Instrument Panel) are named starting points people remix and pass around.

### 5. Narrow the ICP to taste-forward builders, not design-system committees
Do NOT lead with enterprise design-system teams: slow, committee-driven, sound is always deprioritized. The ideal first human is the builder of dev tools and productivity apps who already chases "feel" (Linear/Superhuman/command-palette aesthetic), plus the agents building those apps. These people already believe premium interaction is worth it, so sound is an easy yes. Land there, then let design systems follow.

### 6. The category name does the positioning work — commit to "typeface for sound"
Lean hard on the audioface/typeface analogy in every surface. It makes an abstract idea instantly legible, frames sonic identity as a *designed, selectable, brandable* asset (you choose it like a font), and answers "what is this" in three words. This is the strongest human-facing frame; bet #1 is the strongest agent-facing frame. Run both, targeted at each audience.

### 7. Cross-language story: the contract is portable, renderers are per-platform
Explains why we hold npm + pypi + crates. `AUDIO.md` is a language-neutral spec; Web Audio is simply the *first* renderer. Positions Audioface as a durable standard with implementations (JS today, native later) rather than a JS toy. Lower near-term impact, high credibility for the "this is a standard" thesis.

### 8. Accessibility/feedback as a credibility pillar, not the headline
Semantic-first sound (confirmation, rejection, non-visual and reduced-motion feedback) is a genuine, defensible value. Keep it as the answer to "isn't UI sound annoying?" not as the pitch. It proves the taste and restraint that make the whole thing trustworthy.

## Positioning vs the field
- **vs silence:** win by restraint, not volume. Quiet by default, semantic only, trivially mutable.
- **vs Tone.js / Howler:** those are music/game audio, asset-heavy, no semantic token model, not themeable as identity, not agent-readable. Our moat is the **semantic token + theme-control model + the contract format**, not the synthesis.
- **vs Material sound guidelines:** guidelines are prose; Audioface is a runnable contract plus a runtime.

## The "aha" moment
Hearing one coherent interaction flow that feels physical and premium, then realizing it is procedural (no files) and one config object away from being in your own app in 30 seconds.

## Sharpest positioning bet (one line)
**Be the `AUDIO.md` standard: the agent-readable sound contract that pairs with `DESIGN.md`, distributed through AI coding tools so any app gets a coherent sonic identity with zero audio files.**
