# Audioface Near-Term Monetization (1–3 months)

**Builds on:** `audioface-nearterm--brainstorm.md` (npm v0.1 + audioface.dev playground = OSS launch spine).

**Owner direction (locked):**
- Serve humans (tweak) AND agents (auto-generate unique themes)
- Sonic identity from song/movie → materials + theme controls
- Broad UI token coverage + polished high-end SFX, never gimmicky
- **OSS runtime + `AUDIO.md` contract stays free forever**

**Lens:** Fastest ethical dollar that does NOT poison adoption. Revenue in 1–3 months, not "someday."

---

## Free vs paid boundary (non-negotiable)

| Always free | Paid |
|-------------|------|
| `audioface` npm runtime | Theme generation credits |
| `AUDIO.md` contract | Premium curated theme packs |
| 12 core tokens + 4 presets | Private/unlimited saved themes |
| Public playground (audition + tweak) | Song/movie sonic-identity extraction |
| JSON/TS export of *your own* tweaks | Agent API keys + bulk generation |
| React hook (`audioface/react`) | White-label / brand-sound consulting |

Rule: **never paywall `play()` or install.** Paywall *creation at scale* and *premium content*.

---

## Revenue items ranked by (revenue soon / effort)

| # | Item | Effort | Price | Time to $1 | Payment | Metered unit |
|---|------|--------|-------|------------|---------|--------------|
| 1 | **Premium Theme Pack Vol.1** | S | $19–29 one-time | **7–14 days** | LemonSqueezy | 1 pack = 8–12 curated themes (JSON + TS + preview URLs) |
| 2 | **"Sonic Identity" credit demo** (song/movie → theme) | M | $9 / 3 credits · $29 / 15 credits | 14–21 days | LemonSqueezy | 1 credit = 1 reference → full theme JSON + permalink |
| 3 | **audioface.dev Pro** (soft subscription) | M | $12/mo or $99/yr | 21–35 days | Polar or LemonSqueezy | Unlimited private saves + 30 gen credits/mo + export packs |
| 4 | **Design-partner / brand-sound sprint** | S | $2,500–5,000 fixed | **3–14 days** | Stripe Invoice | 1 sprint = custom theme + token audit + 2 revision rounds |
| 5 | **GitHub Sponsors + sponsorware lane** | S | $8 / $25 / $100/mo tiers | 14–30 days | GitHub Sponsors | Tier unlocks: early packs, vote on tokens, name in `THEME_PRESETS` |
| 6 | **Agent Theme API (credit metered)** | L | $0.15/theme gen · $49/mo starter (500 credits) | 30–60 days | Stripe Billing (metered) | 1 API call with `reference_url` or `prompt` → theme JSON |
| 7 | **Special-effects token pack** ("Pro SFX") | M | $39 one-time | 21–28 days | LemonSqueezy | Pack = 6–10 high-end tokens (`panel.dock`, `drag.settle`, etc.) beyond OSS set |
| 8 | **Export/integration packs** | S | $15 add-on or bundled in Pro | 14 days | LemonSqueezy | 1 pack = React + Vue + vanilla snippets + Storybook stories per theme |
| 9 | **Playground soft paywall** (free tier caps) | M | Free: 3 saves, public only · Pro unlocks | 21–35 days | Polar | 1 saved theme slot (free) · unlimited (Pro) |
| 10 | **Workshop / "sonic identity for your product"** | S | $499–799 live session | 14–45 days | Stripe Checkout link | 1 session = 90min + delivered theme pack |

---

## Effort key

- **S** = 1–3 days setup (+ content curation)
- **M** = 1–2 weeks (auth, billing hook, feature gate)
- **L** = 3–6 weeks (API, metering, agent integration)

---

## Deep dives on top 4

### 1. Premium Theme Pack Vol.1 🚩 **Best first-dollar move**

**What ships:** "Product UI Collection" — 10 production-ready themes (e.g. Linear-clean, Bloomberg-dense, Notion-soft, Arc-glass, Console-mechanical). Each theme = JSON + TS + audioface.dev preview link. Sold as zip via LemonSqueezy.

**Why first:**
- Zero new tech — curate from existing composer + a week of sound design
- Launches same week as npm v0.1; link from README ("free runtime, optional packs")
- Proves willingness-to-pay without touching OSS
- LemonSqueezy: embed checkout on audioface.dev in an afternoon

**OSS-safe:** Runtime plays all themes; pack is convenience + curation + naming.

---

### 2. Sonic Identity credits (song/movie → theme)

**What ships:** audioface.dev page: paste Spotify/YouTube URL or pick "Blade Runner" / "Daft Punk" movie-mood presets → pay → receive theme JSON + shareable permalink.

**v1 architecture (ship fast, don't fake AI):**
1. Client-side or server-side audio feature extraction (tempo, spectral centroid, brightness, percussiveness) — Web Audio + essentia.js or lightweight Python microservice
2. Map features → `material`, `density`, `politeness`, `contrast`, `mechanical`, `warmth` via deterministic rules
3. Human QA queue for first 50 generations (owner spot-checks outliers)
4. Agent path: same endpoint, API key later

**Meter:** 1 credit = 1 reference source → 1 complete theme (all 12 tokens resolved).

**Price psychology:** $9/3 feels like "coffee money try-it"; $29/15 hooks designers doing client work.

---

### 3. audioface.dev Pro

**Free tier:** Playground, tweak sliders, 3 saved themes (localStorage), public permalinks, export current theme.

**Pro ($12/mo):** Unlimited cloud saves, private themes, 30 sonic-identity credits/mo, all premium packs included, priority new tokens.

**Payment:** Polar (cleanest for indie SaaS + license keys) or LemonSqueezy (if staying one vendor).

**Gate:** Supabase auth (already in stack) + `pro` flag on user row. No runtime license check — web-only entitlements.

---

### 4. Design-partner sprint (parallel cash lane)

Not scalable, but **fastest cash if outreach starts now.** Offer 3 slots: "We tune your app's sonic identity in one week." Deliverable = custom theme JSON + `AUDIO.md` snippet for their repo + 15min Loom walkthrough.

**Does not compete with OSS** — consulting sells expertise, not the runtime.

Pitch to: indie SaaS founders, design agencies, devtools startups. Post npm launch + demo video.

---

## Payment surface recommendation

| Use case | Vendor | Why |
|----------|--------|-----|
| One-time packs + credit bundles | **LemonSqueezy** | MoR, EU VAT, digital delivery, embed checkout, fast setup |
| Pro subscription | **Polar** or LemonSqueezy | Recurring + customer portal |
| Consulting / workshops | **Stripe Payment Link** | Invoices, custom amounts, no platform cut on high-ticket |
| Agent API (later) | **Stripe Billing** | Metered usage native |
| Community / early access | **GitHub Sponsors** | Zero friction for dev audience |

**Do not** split across 4 vendors at launch. Week 1–4 stack: **LemonSqueezy only** (packs + credits). Add Polar when Pro ships. Stripe for consulting.

---

## Sequenced revenue plan

### Month 1 (parallel with OSS launch)

| Week | Ship | Revenue target |
|------|------|----------------|
| 1 | npm v0.1 + LemonSqueezy "Theme Pack Vol.1" checkout link on audioface.dev | $0 → first sale |
| 2 | audioface.dev playground live; "Buy Pack" CTA; GitHub Sponsors page | $200–500 |
| 3 | Sonic Identity v1 (rule-based extraction + credit checkout) | $500–1k |
| 4 | Outreach: 5 design-partner conversations → close 1 sprint | $2.5k+ |

### Month 2

- audioface.dev Pro beta (invite sponsors first)
- Pro SFX token pack
- Export/integration pack bundled into Pro

### Month 3

- Agent Theme API private beta (metered Stripe)
- 2nd theme pack (genre/mood collections)
- Workshop offering for teams

---

## What NOT to monetize early

- npm install or `play()` calls
- `AUDIO.md` or agent contract access
- Basic presets (Studio, Console, etc.)
- Permalink sharing (viral loop must stay free)
- Open-source repo / GitHub issues

---

## Success metrics (90 days)

- First dollar within 14 days of npm publish
- $1k cumulative by day 45 (packs + credits + 0–1 sprint)
- $5k MRR path visible (Pro + credits + API beta)
- npm downloads unaffected (no license key in runtime)
- ≥1 paying customer who is NOT a friend

---

## First-dollar move 🚩

**Ship Premium Theme Pack Vol.1 on LemonSqueezy ($19–29) the same week as npm v0.1** — curated JSON/TS themes with preview links, checkout embedded on audioface.dev. No new infrastructure, no OSS friction, revenue within days of launch.