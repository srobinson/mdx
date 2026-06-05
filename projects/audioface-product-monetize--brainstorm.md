# Audioface — Monetization: Business Model & Who Pays

Lens: where the money lives without breaking the free-to-win-the-standard thesis from round 1 (`AUDIO.md` as the agent-readable sound contract, distributed through AI coding tools).

## The one line that governs everything

**Authoring and shipping a sound identity is free forever. You pay to *generate* one (the AI magic), to *govern* many (brand registry/conformance), or to consume it *at programmatic scale* (agent API).**

You can always hand-build and ship an audioface for $0. Money attaches only to things that are (a) marginal-cost-bearing, (b) genuinely magic, or (c) organizational governance. None of those gate the standard, so none poison OSS.

## What MUST stay free (the standard is a public good)
- The runtime / Web Audio renderer.
- The `AUDIO.md` contract format and token vocabulary (the spec itself).
- `audioface init`, base presets, hand-tweaking in the composer, self-serve export, self-hosting.

If the contract or the ability to author/ship costs money, agents and design systems will not standardize on it. The free tier is the moat, not a loss leader.

## Pricing psychology — the anchor is BRAND, not a dev tool

Anchor a generated, brand-derived audioface against a **typeface license, a sound logo, or a brand system** (agency work priced from thousands to tens of thousands), NOT against a $12/mo dev-tool subscription. "Sonic brand identity" already has a budget line at design orgs and agencies. Publicly pricing a "brand audioface" at brand-asset levels resets willingness-to-pay across the whole ladder and makes Pro credits and the API feel cheap by contrast. The generative tech (song/movie -> audioface) is the magic that justifies premium and creates metered consumption.

## Ideas, ranked by revenue potential vs adoption risk

### 1. SHARPEST BET — Meter the *generation*, never the runtime
One pricing primitive: **the generated audioface is the paid unit.** Sold as credits to humans (Pro) and as a metered API to agents (Cursor, v0, Lovable, Claude Code auto-generating a unique theme per app). It structurally cannot poison OSS because you never charge to author or ship, only to have the machine *derive* a bespoke identity for you. It monetizes exactly the thing that is both delightful and carries real compute cost, and it scales linearly with the standard: every agent that adopts the free contract becomes a potential metered generator. This is the flywheel where free adoption directly produces revenue.

### 2. Song/Movie -> Audioface as the flagship generator (the demand engine behind #1)
The paid magic that people actually open a wallet for: point at a favorite song or film, extract a sonic identity (timbre, brightness, density, attack, warmth), and map it onto materials + theme controls. Novel, high-want, deeply shareable ("I made my app sound like Blade Runner"). This is what converts free users to Pro credits and what agents burn API calls on. Give 1-2 free generations to deliver the aha, then meter.

### 3. Human Pro subscription (the prosumer on-ramp / recurring base)
~$12-20/mo or annual: composer pro features, unlimited and private themes, saved library, high-end effect palettes, and a monthly allotment of generation credits (rolls into #1). Low friction, predictable MRR, and the natural home for individual builders and freelancers. Freemium boundary = generation credits, not features that would cripple adoption.

### 4. Team/Enterprise: private theme registry + branded identity kits + conformance
Highest ACV, anchored to brand budgets. Host an org's sonic identity as a **private, versioned registry** (the private-font/design-token analogue), sell branded sonic identity kits, SSO, seats, and **conformance/audit** ("does this app's sound conform to our `AUDIO.md`?"). This is a brand-governance product sold to design orgs and agencies, where recurring ACV genuinely lives. Adoption risk is timing: the category must mature first, so this is where the money *ends up*, not the fastest path in.

### 5. Agency / done-for-you "sonic identity" service tier
A managed "brand audioface" engagement priced like agency brand work (thousands+). Highest per-deal revenue, low volume, and it funds category education and reference logos. Risk: services can distract from product leverage, so keep it thin, productized, and used mainly to seed lighthouse brands and set the pricing anchor.

### 6. Premium theme / effect marketplace (creator ecosystem)
Creators sell high-end, polished effect packs and signature themes; we take a cut. Grows the free ecosystem, modest revenue, low risk, and reinforces "audioface = a chosen identity you can license." Must never gate the core semantic tokens behind it.

### 7. Conformance/audit as a standalone paid CI check
"Sound conformance" as a CI/PR gate against the org's `AUDIO.md`. Sticky, governance-budget-funded, expands enterprise ACV. Depends on registry adoption, so it trails #4.

## Where the money actually lives
- **Generation** (marginal cost + magic): credits + agent API. The engine.
- **Governance** (registry, conformance, brand kits, SSO): enterprise recurring ACV.
- **Scale** (agent API metering): grows automatically as the free standard wins.

## Sharpest monetization bet (one line)
**Meter the generation, not the runtime: the AI-derived audioface (flagship: song/movie -> sonic identity) is the paid unit, sold as Pro credits to humans and a metered API to agents, while the runtime and `AUDIO.md` contract stay free forever — so revenue scales with adoption instead of fighting it.**
