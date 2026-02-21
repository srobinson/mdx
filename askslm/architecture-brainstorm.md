# AskSLM Website Rebuild: Information Architecture & Page Strategy

**Date**: 2026-02-22
**Author**: Stuart (product design brainstorm)
**Status**: Draft for founder review
**Context**: Complete rebuild of askslm.com. Current site is a single 5,000+ word HTML page with no multi-page structure, no social proof, no pricing, a broken contact form, and template-tier visual design. The product is strong. The website is not.

---

## 1. Sitemap & Information Architecture

### 1.1 Complete Page Hierarchy

```
askslm.com/
├── / ........................... Homepage (hero, value prop, proof, CTA)
├── /platform/ ................. Platform overview (engine + marketplace + training)
│   ├── /platform/inference-engine/ ... Deep dive on the C++ inference engine
│   ├── /platform/marketplace/ ....... SLM Marketplace explained
│   └── /platform/deployment/ ........ Deployment options (on-prem + appliance)
├── /solutions/ ................ Solutions overview (industry grid)
│   ├── /solutions/legal/ ............ Legal & law firms
│   ├── /solutions/healthcare/ ....... Healthcare & clinical
│   ├── /solutions/financial-services/ Banking, insurance, mortgage
│   └── /solutions/government/ ....... Government & public sector
├── /security/ ................. Security & compliance (standalone — their #1 differentiator)
├── /pricing/ .................. Pricing (does not exist today — must be created)
├── /about/ .................... Company story + team
├── /contact/ .................. Demo request + contact info (replaces broken form)
├── /resources/ ................ Resource hub (blog, whitepapers, case studies)
│   ├── /resources/blog/ ............ Blog index
│   ├── /resources/blog/[slug]/ ..... Individual blog posts
│   ├── /resources/case-studies/ .... Case study index
│   ├── /resources/case-studies/[slug]/ Individual case studies
│   └── /resources/whitepapers/ ..... Gated whitepaper downloads
├── /compare/ .................. Comparison pages (SEO play)
│   ├── /compare/askslm-vs-openai/ .. vs cloud LLMs
│   ├── /compare/askslm-vs-ollama/ .. vs open-source local
│   └── /compare/askslm-vs-huggingface/ vs HF ecosystem
├── /privacy/ .................. Privacy policy (currently a dead link)
├── /terms/ .................... Terms of service (currently a dead link)
└── /sitemap.xml ............... Proper multi-page sitemap
```

**Total: ~25 pages at launch, expandable to 40+ with blog and case study content.**

### 1.2 Navigation Design

#### Primary Navigation (top bar, sticky on scroll)

```
┌─────────────────────────────────────────────────────────┐
│  [Logo]   Platform ▾   Solutions ▾   Security   Pricing │
│                                          [Request Demo] │
└─────────────────────────────────────────────────────────┘
```

- **Platform** dropdown: Overview, Inference Engine, Marketplace, Deployment
- **Solutions** dropdown: Overview, Legal, Healthcare, Financial Services, Government
- **Security**: No dropdown — direct link to /security/ (this deserves top-level prominence because it is the #1 buyer concern for regulated industries)
- **Pricing**: Direct link
- **Request Demo**: Button (high-contrast accent color), always visible, sticky

5 items. Clean. Every item maps to a buying decision.

**What got cut from current nav**: "The Problem" (merged into homepage), "Training" (merged into Platform), "Team" (moved to About), "Development Philosophy" (moved to About or removed entirely), "Engine" (nested under Platform). The current 10-item nav is cut to 5.

#### Utility Navigation (top-right, above primary nav or inline)

```
Resources   About   Contact   [Search icon]
```

These are secondary navigation items. Important but not buying-decision pages. They live in a utility bar or are accessible via the footer.

#### Footer Navigation

```
┌───────────────────────────────────────────────────────────┐
│  [Logo]                                                   │
│  Private, on-premise AI for regulated enterprises.        │
│                                                           │
│  Platform          Solutions        Resources    Company  │
│  ─────────         ─────────        ─────────    ─────── │
│  Overview          Legal            Blog         About    │
│  Inference Engine  Healthcare       Case Studies Contact  │
│  Marketplace       Financial Svc    Whitepapers  Careers  │
│  Deployment        Government       Comparisons  Press    │
│                                                           │
│  Security          Legal                                  │
│  ─────────         ─────                                  │
│  Overview          Privacy Policy                         │
│  Compliance        Terms of Service                       │
│                                                           │
│  ──────────────────────────────────────────────────────── │
│  © 2026 AskSLM. All rights reserved.     Austin, TX      │
│  contact@askslm.com                                       │
└───────────────────────────────────────────────────────────┘
```

#### Key IA Decisions

1. **Brand consolidation**: Use "AskSLM" everywhere. Kill "Secure SLM" as a product name. The current site uses both interchangeably, which fractures brand identity and confuses Google's entity recognition. "AskSLM" is the domain, the brand, and the product. Period.

2. **Security gets its own top-level page**: In every other B2B SaaS site, security is buried under a footer link. For AskSLM, security IS the product. It belongs in the primary nav right next to Platform and Solutions. A CISO evaluating this product should be able to reach the security page in one click from anywhere on the site.

3. **Solutions are separate pages, not a single scroll**: The current site lists 8 industries in one scroll section. Each industry deserves its own page for three reasons: (a) SEO -- "private AI for law firms" can rank independently, (b) buyer relevance -- a hospital CISO does not want to scroll past legal and banking content, (c) depth -- each industry page can have tailored use cases, pain points, and (eventually) case studies.

4. **Comparison pages are an SEO power play**: People searching "AskSLM vs Ollama" or "private AI vs OpenAI" are high-intent buyers. Dedicated comparison pages capture this traffic and control the narrative. These are standard in enterprise SaaS (see: Notion vs Confluence, Linear vs Jira).

5. **Resources hub from day one**: Even if it launches with only 2-3 blog posts and 1 whitepaper, the structure needs to exist. It signals maturity and gives the team a place to publish content that drives organic traffic over time.

### 1.3 URL Structure (SEO-Optimized)

| URL                              | Target Keywords                                            |
| -------------------------------- | ---------------------------------------------------------- |
| `/`                              | AskSLM, private AI, on-premise AI                          |
| `/platform/`                     | AskSLM platform, on-premise AI platform                    |
| `/platform/inference-engine/`    | AI inference engine, local AI engine, on-premise inference |
| `/platform/marketplace/`         | SLM marketplace, AI model marketplace                      |
| `/platform/deployment/`          | on-premise AI deployment, AI appliance                     |
| `/solutions/legal/`              | AI for law firms, private AI legal, legal document AI      |
| `/solutions/healthcare/`         | HIPAA compliant AI, healthcare AI, clinical AI             |
| `/solutions/financial-services/` | AI for banking, financial services AI, KYC AI              |
| `/solutions/government/`         | government AI, air-gapped AI, FedRAMP AI                   |
| `/security/`                     | AI security, AI compliance, on-premise AI security         |
| `/pricing/`                      | AskSLM pricing, on-premise AI cost                         |
| `/compare/askslm-vs-openai/`     | AskSLM vs OpenAI, private AI vs cloud AI                   |
| `/compare/askslm-vs-ollama/`     | AskSLM vs Ollama, enterprise local AI                      |
| `/resources/blog/`               | (long-tail keywords per article)                           |

Trailing slashes on all URLs for consistency. Lowercase, hyphenated, no underscores.

### 1.4 Content Migration Map

Where current content goes in the new structure:

| Current Section          | New Location                      | Action                                 |
| ------------------------ | --------------------------------- | -------------------------------------- |
| Hero                     | Homepage hero                     | Rewrite (fix typos, sharpen copy)      |
| The Problem              | Homepage (condensed to 3 bullets) | Rewrite heavily                        |
| Proprietary Value        | Homepage value prop section       | Rewrite (kill jargon)                  |
| Competitive Table        | Homepage + /compare/ pages        | Keep and expand                        |
| Platform Overview        | /platform/                        | Rewrite for clarity                    |
| Inference Engine         | /platform/inference-engine/       | Rewrite (less jargon, add diagrams)    |
| Marketplace              | /platform/marketplace/            | Rewrite (add screenshots/mockups)      |
| Training & RAG           | /platform/ (subsection)           | Condense and rewrite                   |
| Deployment               | /platform/deployment/             | Rewrite (add pricing hints)            |
| Security & Compliance    | /security/                        | Rewrite and expand significantly       |
| Solutions (8 industries) | /solutions/[industry]/ (4 pages)  | Rewrite + expand top 4, archive rest   |
| Use Scenarios (15)       | Distribute across solution pages  | Pick best 1-2 per industry             |
| Team                     | /about/                           | Keep bios, rewrite for consistency     |
| Development Philosophy   | /about/ (brief mention) or remove | Condense to 2 sentences max            |
| Contact / Demo Form      | /contact/                         | Rebuild entirely (form actually works) |

**What to cut entirely:**

- 11 of 15 "Real-World Use Scenarios" (keep 4 strongest, one per industry vertical)
- "Development Philosophy" as a standalone section (nobody buying enterprise AI cares about your sprint methodology)
- The long "Application Examples" bullet list from Training section (generic and unfocused)
- Redundant feature repetition across sections (the same "zero cloud" claim appears in 6+ places)

**Industries to keep as standalone pages (top 4):**

1. Legal -- large addressable market, clear pain points, high willingness to pay
2. Healthcare -- HIPAA is a forcing function, massive market
3. Financial Services -- merge Banking + Mortgage + Insurance into one page
4. Government / Public Sector -- air-gapped requirements, long sales cycles but large contracts

**Industries to mention on the Solutions overview but NOT give standalone pages yet:**

- Architecture & Engineering
- Education & Research
- Manufacturing
- Energy, Telecom, Retail, etc.

These can get standalone pages later when there is customer evidence or content to fill them. Empty pages are worse than no pages.

---

## 2. Homepage Blueprint

### 2.1 Design Philosophy

The homepage must do three things in this order:

1. **Explain what AskSLM is** (in under 10 seconds)
2. **Prove it is credible** (in under 30 seconds)
3. **Get the visitor to the right next page** (in under 60 seconds)

Target word count: **400-600 words** on the entire homepage (down from 5,000+). Every word earns its place. Depth lives on subpages.

### 2.2 Section-by-Section Layout

#### Section 1: Hero (above the fold)

```
┌──────────────────────────────────────────────────────────┐
│  [Sticky Nav]                                            │
│                                                          │
│                                                          │
│     AI that stays inside your building.                  │
│                                                          │
│     Run advanced language models on your own             │
│     infrastructure. No cloud. No data leaks.             │
│     Built for healthcare, legal, finance,                │
│     and government.                                      │
│                                                          │
│     [Request a Demo]     [See How It Works →]            │
│                                                          │
│                                                          │
│  ┌──────┐ ┌──────┐ ┌──────┐                             │
│  │100%  │ │Zero  │ │Runs  │                              │
│  │On-   │ │Cloud │ │on    │                              │
│  │Prem  │ │Usage │ │Your  │                              │
│  └──────┘ └──────┘ │HW   │                              │
│                     └──────┘                              │
└──────────────────────────────────────────────────────────┘
```

**Headline options** (pick one, test the others):

- "AI that stays inside your building." (benefit-first, plain English)
- "Private AI. On your infrastructure. Under your control." (three-beat rhythm)
- "The AI your compliance team will actually approve." (audience-aware, provocative)

**Subheadline**: 2 sentences max. Name the target industries. State the core benefit in non-technical language. No jargon. No "inference engine." No "data sovereignty." Just: your data never leaves. You own everything. It works on hardware you already have.

**CTAs**:

- Primary: "Request a Demo" (high-contrast button, accent color)
- Secondary: "See How It Works" (ghost button or text link, goes to /platform/)

**Trust badges below CTAs**: Three pills/badges -- "100% On-Premise", "Zero Cloud Usage", "Standard Hardware". These are the three most memorable claims. Keep them visual and scannable.

**Visual**: NOT a generic network diagram. Options:

- An animated diagram showing data flowing WITHIN a building perimeter (never leaving)
- A product screenshot or mockup of the inference engine dashboard
- A split visual: left side shows data leaving to a cloud (red, crossed out), right side shows data staying local (green, checkmark)

**What NOT to put above the fold**: Technical specifications, team photos, feature lists, the word "C++", anything about sprints or agile methodology.

#### Section 2: Social Proof Bar (immediately below hero)

```
┌──────────────────────────────────────────────────────────┐
│  Trusted by teams in healthcare, legal, and finance      │
│                                                          │
│  [Logo] [Logo] [Logo] [Logo] [Logo] [Logo]              │
│                                                          │
│  "AskSLM let us deploy AI without ever sending           │
│   patient data outside our network."                     │
│   — CISO, Regional Health System                         │
└──────────────────────────────────────────────────────────┘
```

**If no customer logos exist yet**, use alternatives:

- Compliance framework logos: SOC 2, HIPAA, ISO 27001 (only if certifications are in progress or achieved)
- Technology partner logos: Intel (if using SGX for TEEs), AMD (if using SEV), NVIDIA
- "In pilot with organizations across 4 regulated industries" (if true)
- Advisor or investor names/logos (if applicable)

**This section is non-negotiable.** Even a single quote from a pilot customer is better than nothing. The current site has ZERO social proof. That is a dealbreaker for enterprise buyers. If there are truly no customers, advisors, or partners to reference, this section becomes "Built for the most demanding compliance requirements" with framework logos and a brief trust statement.

#### Section 3: The Problem / Solution (2 screens)

```
┌──────────────────────────────────────────────────────────┐
│                                                          │
│  The AI problem nobody talks about                       │
│                                                          │
│  ┌─────────────────┐  ┌─────────────────┐               │
│  │ Cloud AI sends   │  │ Generic models  │               │
│  │ your data to     │  │ hallucinate on  │               │
│  │ someone else's   │  │ domain-specific │               │
│  │ servers          │  │ questions       │               │
│  └─────────────────┘  └─────────────────┘               │
│  ┌─────────────────┐  ┌─────────────────┐               │
│  │ No vendor stands │  │ API costs scale │               │
│  │ behind the       │  │ linearly with   │               │
│  │ answers          │  │ usage           │               │
│  └─────────────────┘  └─────────────────┘               │
│                                                          │
│  AskSLM solves all four.                                 │
│                                                          │
│  Your data stays on your hardware. Models are trained    │
│  on your domain. Vendors certify accuracy. Costs are     │
│  fixed and predictable.                                  │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

The current site has 5 problem statements with dense paragraphs. Cut to 4, presented as cards with 1-sentence descriptions. Then immediately pivot to the solution in 2-3 sentences. No jargon. No "C++ inference engine." Just outcomes.

**Keep the competitive comparison table** -- but simplified. The existing table (AskSLM vs OpenAI vs HuggingFace vs Ollama) is genuinely powerful. Put it here or directly below this section. Use checkmarks and X marks with green/red color coding. Link to the full /compare/ pages for detail.

#### Section 4: Platform Overview (1 screen)

```
┌──────────────────────────────────────────────────────────┐
│                                                          │
│  One platform. Three capabilities.                       │
│                                                          │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐    │
│  │  [icon]       │ │  [icon]       │ │  [icon]       │  │
│  │  Inference    │ │  Model        │ │  One-Click   │   │
│  │  Engine       │ │  Marketplace  │ │  Deployment  │   │
│  │              │ │              │ │              │     │
│  │  Run multiple │ │  Curated,     │ │  Your servers│   │
│  │  AI models    │ │  domain-      │ │  or our      │   │
│  │  locally, in  │ │  specific     │ │  plug-and-   │   │
│  │  real time,   │ │  models from  │ │  play AI     │   │
│  │  on standard  │ │  trusted      │ │  appliance   │   │
│  │  hardware.    │ │  vendors.     │ │              │   │
│  │              │ │              │ │              │     │
│  │  [Learn more] │ │  [Learn more] │ │  [Learn more]│   │
│  └──────────────┘ └──────────────┘ └──────────────┘    │
│                                                          │
│           [Explore the Platform →]                       │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

Three cards. One sentence each. Link to the deep-dive subpages. This replaces the 4 separate detailed sections currently on the homepage. The depth lives on /platform/ and its children.

#### Section 5: Industry Solutions (1 screen)

```
┌──────────────────────────────────────────────────────────┐
│                                                          │
│  Built for industries where AI compliance is mandatory   │
│                                                          │
│  ┌────────────────────────┐ ┌────────────────────────┐  │
│  │ ⚖ Legal                │ │ 🏥 Healthcare           │  │
│  │                        │ │                        │  │
│  │ Document review,       │ │ Patient summaries,     │  │
│  │ e-discovery, and case  │ │ diagnostic support,    │  │
│  │ research — with full   │ │ and coding — fully     │  │
│  │ attorney-client        │ │ HIPAA compliant.       │  │
│  │ privilege protection.  │ │                        │  │
│  │                        │ │                        │  │
│  │ [Learn more →]         │ │ [Learn more →]         │  │
│  └────────────────────────┘ └────────────────────────┘  │
│  ┌────────────────────────┐ ┌────────────────────────┐  │
│  │ 🏦 Financial Services  │ │ 🏛 Government           │  │
│  │                        │ │                        │  │
│  │ KYC/AML automation,    │ │ Case processing,       │  │
│  │ risk analysis, and     │ │ policy interpretation,  │  │
│  │ compliance — all data  │ │ and citizen services — │  │
│  │ stays in your vault.   │ │ air-gapped ready.      │  │
│  │                        │ │                        │  │
│  │ [Learn more →]         │ │ [Learn more →]         │  │
│  └────────────────────────┘ └────────────────────────┘  │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

4 cards, not 8. Each links to its dedicated /solutions/ page. Short, benefit-oriented copy. Industry-specific language (HIPAA, attorney-client privilege, KYC/AML, air-gapped). No generic "AI for your industry" fluff.

#### Section 6: How It Works (1 screen, optional)

```
┌──────────────────────────────────────────────────────────┐
│                                                          │
│  From evaluation to production in weeks, not months      │
│                                                          │
│  1. Assess ──→ 2. Deploy ──→ 3. Customize ──→ 4. Scale  │
│                                                          │
│  We evaluate    Install on     Train models    Add users,│
│  your infra     your servers   on your         models,   │
│  and security   or ship an     domain data     and use   │
│  requirements   appliance      with no-code    cases     │
│                                tools           over time │
│                                                          │
│  [Request a Demo to Start →]                             │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

This section addresses a critical objection the current site ignores: "How do I actually get this thing running?" A simple 4-step flow demystifies the process and makes the buyer feel like this is achievable.

#### Section 7: Final CTA (1 screen)

```
┌──────────────────────────────────────────────────────────┐
│                                                          │
│  [Dark or gradient background, visually distinct]        │
│                                                          │
│  Ready to run AI on your terms?                          │
│                                                          │
│  See AskSLM in action. We will walk you through a       │
│  live deployment tailored to your industry and           │
│  compliance requirements.                                │
│                                                          │
│  [Request a Demo]    [Download Security Whitepaper]      │
│                                                          │
│  No commitment. No data shared. 30-minute call.          │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

Two CTAs: primary (demo) and secondary (whitepaper download for people not ready to talk to sales). The reassurance line ("No commitment. No data shared. 30-minute call.") reduces friction.

### 2.3 Above-the-Fold Priorities (in order)

1. What this is (headline + subheadline)
2. Who it is for (regulated industries named explicitly)
3. What to do next (CTA button)
4. Why to trust it (trust badges or social proof)

That is it. Everything else is below the fold.

---

## 3. Key Page Concepts

### 3.1 Platform Page (/platform/)

**Purpose**: The technical deep-dive for IT evaluators and technical champions on the buying committee. This is where the jargon lives -- but organized and contextualized, not dumped.

**Structure**:

```
Hero: "The complete on-premise AI platform"
  - 1-paragraph overview
  - Architecture diagram (visual, not text)
  - Animated or interactive diagram showing data flow

Tab 1: Inference Engine
  - What it is (plain English first, then technical detail)
  - "Like an operating system for AI" (keep this metaphor -- it works)
  - Performance benchmarks (if available)
  - Hardware requirements
  - Screenshot or mockup of the engine dashboard

Tab 2: Model Marketplace
  - What it is (app store for AI models)
  - How trust brokering works (diagram)
  - Example models available
  - Vendor onboarding process (brief)

Tab 3: Training & RAG
  - No-code training for domain experts
  - RAG integration with internal knowledge bases
  - How customization works without ML engineers

Tab 4: Deployment Options
  - Option A: Your existing hardware (specs, requirements)
  - Option B: SLM Appliance (the "AI in a Box")
  - Comparison table of both options
  - Implementation timeline
```

**Key copy principle**: Lead with the benefit in plain English. Follow with the technical detail. The CTO reads the first paragraph. The infrastructure engineer reads the rest.

**Critical missing asset**: The current site has NO product screenshots, NO architecture diagrams, NO visual representation of the product whatsoever. The platform page requires visuals. If the product UI is not ready for screenshots, commission professional mockups or create detailed architecture diagrams. A platform page with no visuals is a whitepaper, not a product page.

### 3.2 Solutions Pages (/solutions/[industry]/)

**Should these be separate pages?** Yes. Absolutely. For three reasons:

1. **SEO**: "HIPAA compliant AI" and "AI for law firms" are separate search queries. They need separate pages to rank.
2. **Buyer experience**: A hospital CISO arriving on the site wants to see healthcare content immediately, not scroll past legal and banking content to find it.
3. **Sales enablement**: The sales team can send a prospect a direct link to their industry page instead of saying "scroll down to the Healthcare section."

**How many?** 4 at launch. Expand later with evidence.

**Template structure (same for all 4):**

```
Hero:
  - Industry-specific headline
  - 1-sentence value prop tailored to that industry
  - Industry-relevant trust badge (HIPAA for healthcare, etc.)

Pain Points (3 cards):
  - Industry-specific problems that current AI cannot solve
  - Written in the language of that industry (not generic AI language)

How AskSLM Solves It:
  - 4-5 use cases specific to this industry
  - Each use case is 2-3 sentences max
  - Pull the BEST scenarios from the current "Real-World Use Scenarios" section

Architecture / Deployment for This Industry:
  - Brief note on how deployment typically works for this sector
  - Compliance frameworks relevant to this industry
  - Link to /security/ for full details

Case Study (when available):
  - Placeholder section: "See how [industry type] organizations use AskSLM"
  - Initially: a detailed hypothetical scenario (clearly labeled)
  - Later: replace with real customer stories

CTA:
  - "See AskSLM for [Industry]" / "Request a [Industry] Demo"
  - Pre-select the industry in the demo request form
```

**Example: /solutions/healthcare/**

- Headline: "HIPAA-compliant AI that never leaves your hospital network"
- Pain points: Patient data in the cloud, AI hallucinations in clinical settings, no audit trail for AI-assisted decisions
- Use cases: Patient history summarization, diagnostic support, medical coding, clinical decision support
- Compliance: HIPAA, HITECH, hospital IT policies
- CTA: "Request a Healthcare Demo"

### 3.3 Security Page (/security/)

**This is AskSLM's most important page after the homepage.** Security is not a feature -- it is the entire product thesis. The buyers (CISOs, compliance officers, legal counsel) will spend more time on this page than any other.

**Structure**:

```
Hero:
  "Security is not a feature we added. It is the architecture."

Section 1: Security Architecture Overview
  - Visual diagram of the security layers
  - Data flow diagram showing what stays local vs. what (if anything) crosses a network
  - Hardware-bound encryption explained visually (TEE diagram)

Section 2: Data Protection
  - Zero cloud usage (explain exactly what this means)
  - On-site processing (what data paths exist)
  - Encryption at rest and in transit
  - Role-based access controls
  - Segregated model/data storage

Section 3: Compliance Frameworks
  - Grid of compliance logos/badges with status
  - HIPAA, SOC 2, ISO 27001, FedRAMP (if applicable)
  - For each: what AskSLM does to support that framework
  - Link to downloadable compliance documentation (PDF)

Section 4: Model Integrity & Provenance
  - How models are verified before execution
  - Cryptographic signing
  - Version tracking and lineage
  - Training data provenance and documentation

Section 5: Audit & Governance
  - Audit trail capabilities
  - Logging and monitoring
  - Policy enforcement mechanisms
  - Incident response readiness

Section 6: Penetration Testing & Certifications
  - Third-party audit results (when available)
  - Bug bounty program (if applicable)
  - Security contact (security@askslm.com)

Downloadable Assets:
  - Security whitepaper (PDF, gated — email required)
  - SOC 2 report (if available, gated for prospects)
  - Architecture diagram (downloadable)

CTA:
  "Have security questions? Talk to our team."
  [Schedule a Security Review]
```

**Critical note**: This page must be factual and specific. No hand-waving. No "we take security seriously" filler. CISOs will probe every claim. If a certification is in progress, say "in progress." If it does not exist yet, do not claim it. Credibility is built through specificity and honesty, not through listing every buzzword.

### 3.4 Pricing Page (/pricing/)

**The current site has NO pricing information.** This is a problem. Even enterprise products benefit from a pricing page because it:

- Qualifies prospects (people who cannot afford it self-select out)
- Reduces sales cycle friction (buyers have budget conversations internally before the demo call)
- Signals maturity and transparency

**Recommended approach: Tiered with "Contact for pricing" on Enterprise**

```
┌──────────────────────────────────────────────────────────┐
│                                                          │
│  Transparent pricing for secure AI                       │
│                                                          │
│  ┌───────────┐  ┌───────────┐  ┌───────────┐           │
│  │ Starter    │  │ Business   │  │ Enterprise │           │
│  │            │  │            │  │            │           │
│  │ For small  │  │ For mid-   │  │ For large  │           │
│  │ teams      │  │ sized orgs │  │ orgs with  │           │
│  │ evaluating │  │ deploying  │  │ complex    │           │
│  │ on-prem AI │  │ across     │  │ compliance │           │
│  │            │  │ departments│  │ needs      │           │
│  │            │  │            │  │            │           │
│  │ From       │  │ From       │  │ Custom     │           │
│  │ $X,XXX/mo  │  │ $XX,XXX/mo │  │            │           │
│  │            │  │            │  │            │           │
│  │ • Up to N  │  │ • Up to N  │  │ • Unlimited│           │
│  │   models   │  │   models   │  │   models   │           │
│  │ • X users  │  │ • X users  │  │ • Unlimited│           │
│  │ • Email    │  │ • Priority │  │   users    │           │
│  │   support  │  │   support  │  │ • Dedicated│           │
│  │ • Deploy   │  │ • Deploy   │  │   CSM      │           │
│  │   on your  │  │   on your  │  │ • SLM      │           │
│  │   hardware │  │   hardware │  │   Appliance│           │
│  │            │  │ • Custom   │  │ • Custom   │           │
│  │            │  │   training │  │   training │           │
│  │            │  │            │  │ • SLA      │           │
│  │            │  │            │  │ • On-site  │           │
│  │            │  │            │  │   deploy   │           │
│  │            │  │            │  │            │           │
│  │ [Start     │  │ [Request   │  │ [Contact   │           │
│  │  Trial]    │  │  Demo]     │  │  Sales]    │           │
│  └───────────┘  └───────────┘  └───────────┘           │
│                                                          │
│  All plans include: zero cloud usage, encryption,        │
│  audit logging, software updates                         │
│                                                          │
│  ──────────────────────────────────────────────────────  │
│                                                          │
│  FAQ:                                                    │
│  • What hardware do I need?                              │
│  • How does marketplace model pricing work?              │
│  • Is there an annual discount?                          │
│  • What is the implementation timeline?                  │
│  • Do you offer proof-of-concept deployments?            │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

**If the team is not ready to publish specific prices**, an alternative format works:

```
  How AskSLM pricing works
  ─────────────────────────
  Platform license: Annual subscription based on deployment size
  Marketplace models: Usage-based or per-seat, varies by vendor
  SLM Appliance: One-time hardware cost + annual software license
  Implementation: Included in first-year license for qualifying orgs

  [Get a Custom Quote]

  Typical deployment costs 5-20x less than cloud AI API fees
  for equivalent workloads.
```

Either way, the page should exist. "Contact us" with zero context is a conversion killer.

### 3.5 About / Team Page (/about/)

**Structure**:

```
Section 1: Company Story
  - 2-3 paragraphs: Why AskSLM exists, what problem the founders saw, where it is going
  - NOT the "Development Philosophy" section (that is internal process, not a story)
  - Tone: Authoritative and confident, not startup-bro

Section 2: Leadership
  - Clint House (CEO) — professional headshot, 3-sentence bio, LinkedIn link
  - Zurab Tutberidze (CTO) — professional headshot, 3-sentence bio, LinkedIn link
  - Emphasis on their combined 40+ years, previous exits, regulated-industry experience

Section 3: Engineering Team
  - Grid of 6 team members
  - Professional headshots (MUST be consistent — same background, same lighting, same crop)
  - Name, title, 1-sentence description
  - No LinkedIn links for non-leadership (optional)

Section 4: Company Facts
  - Founded: [year]
  - HQ: Austin, TX
  - Team size: 8 (and growing)
  - Core technology: Built in-house in C++
  - Backed by: [investors, if applicable]

Section 5: Careers (optional, link out)
  - "We're hiring" banner with link to careers page or job board
```

**Key change from current site**: The team section currently has 8 full bios on the homepage. Move all of this to /about/. On the homepage, the team does not appear at all. Buyers do not care about your team until they care about your product.

**Photo quality matters enormously.** The current site has inconsistent photo hosting (some local, some on Wix CDN) and likely inconsistent photo quality. For the rebuild, every team member needs a professional headshot with the same background, lighting, and crop. This signals "we are a real company" more than any amount of copy.

### 3.6 Contact / Demo Request Page (/contact/)

**The current form is broken.** It has no `action` attribute. Submissions go nowhere. This is the most critical fix in the entire rebuild.

**Structure**:

```
┌──────────────────────────────────────────────────────────┐
│                                                          │
│  See AskSLM in your environment                         │
│                                                          │
│  ┌─── Left Column (60%) ──────────────────────────────┐ │
│  │                                                     │ │
│  │  Request a personalized demo                        │ │
│  │                                                     │ │
│  │  We will walk you through a live deployment          │ │
│  │  tailored to your industry, infrastructure,         │ │
│  │  and compliance requirements.                       │ │
│  │                                                     │ │
│  │  Full Name*           [________________]            │ │
│  │  Work Email*          [________________]            │ │
│  │  Company*             [________________]            │ │
│  │  Job Title            [________________]            │ │
│  │  Industry*            [▼ Select ______]             │ │
│  │    Legal, Healthcare, Financial Services,           │ │
│  │    Government, Insurance, Education,                │ │
│  │    Architecture/Engineering, Other                  │ │
│  │  Company Size         [▼ Select ______]             │ │
│  │    1-50, 51-200, 201-1000, 1000+                   │ │
│  │  How can we help?     [________________]            │ │
│  │                       [________________]            │ │
│  │                                                     │ │
│  │  [Request Your Demo]                                │ │
│  │                                                     │ │
│  │  We respond within 1 business day.                  │ │
│  │  Your data is never shared.                         │ │
│  │                                                     │ │
│  └─────────────────────────────────────────────────────┘ │
│                                                          │
│  ┌─── Right Column (40%) ─────────────────────────────┐ │
│  │                                                     │ │
│  │  What to expect:                                    │ │
│  │                                                     │ │
│  │  1. 30-minute live demo                             │ │
│  │  2. Tailored to your industry                       │ │
│  │  3. Technical deep-dive available                   │ │
│  │  4. No commitment required                          │ │
│  │                                                     │ │
│  │  ──────────────────────────────────                 │ │
│  │                                                     │ │
│  │  Prefer email?                                      │ │
│  │  contact@askslm.com                                 │ │
│  │                                                     │ │
│  │  Location                                           │ │
│  │  Austin, TX                                         │ │
│  │                                                     │ │
│  └─────────────────────────────────────────────────────┘ │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

**Key improvements over current form**:

1. **It actually works.** Form submissions go to a real backend (HubSpot, Formspree, or custom API).
2. **More fields for qualification**: Job title and company size help the sales team prioritize. Industry dropdown expanded from 5 to 8+ options (matching all industries mentioned on the site).
3. **Expectation setting**: Right column tells the visitor exactly what happens next. This reduces anxiety and increases form completions.
4. **Confirmation page**: After submission, redirect to a thank-you page with: (a) "We will be in touch within 1 business day", (b) a Calendly embed so they can self-schedule immediately, (c) a link to the security whitepaper or resources.

---

## 4. Conversion Architecture

### 4.1 Primary Conversion Path: Visitor to Demo Request

```
Discovery (SEO, LinkedIn, referral)
  │
  ▼
Homepage (10 seconds: understand what + who)
  │
  ├──→ Solutions page (self-identify by industry)
  │       │
  │       ▼
  │     Industry-specific value + use cases
  │       │
  │       ▼
  │     "Request a [Industry] Demo" ──→ /contact/ (pre-filled industry)
  │
  ├──→ Platform page (technical evaluation)
  │       │
  │       ▼
  │     Technical deep-dive on engine, marketplace, deployment
  │       │
  │       ▼
  │     "Request a Demo" ──→ /contact/
  │
  ├──→ Security page (compliance evaluation)
  │       │
  │       ▼
  │     Security architecture, compliance frameworks, audit capabilities
  │       │
  │       ▼
  │     "Schedule a Security Review" ──→ /contact/
  │
  └──→ Pricing page (budget evaluation)
          │
          ▼
        Tier comparison + FAQ
          │
          ▼
        "Get a Custom Quote" ──→ /contact/
```

**Every page has at most 2 clicks to the demo request form.** The CTA appears:

- In the sticky header (always visible)
- At the bottom of every page
- Contextually within each page (after key selling points)

### 4.2 Secondary Conversions

| Conversion                   | Mechanism                  | Location                              | Purpose                                                             |
| ---------------------------- | -------------------------- | ------------------------------------- | ------------------------------------------------------------------- |
| Security whitepaper download | Gated PDF (email required) | /security/, homepage CTA, exit intent | Capture CISO/compliance officer emails who are not ready for a demo |
| Blog newsletter              | Email signup               | /resources/blog/ sidebar              | Nurture leads with ongoing content                                  |
| ROI calculator               | Interactive tool (future)  | /pricing/ or standalone               | Self-serve qualification; generates a custom savings estimate       |
| Product video                | Embedded video (ungated)   | Homepage, /platform/                  | Let executives see the product without committing to a call         |
| Comparison page CTAs         | "See how AskSLM compares"  | /compare/ pages                       | Capture high-intent comparison shoppers                             |

**Priority order for building these**:

1. Security whitepaper (requires writing, not coding)
2. Product video (even a 2-minute screen recording is better than nothing)
3. Blog newsletter (comes free with a CMS)
4. ROI calculator (development effort, do later)

### 4.3 CTA Strategy

| CTA Text                       | Context                        | Button Style                            |
| ------------------------------ | ------------------------------ | --------------------------------------- |
| "Request a Demo"               | Primary action everywhere      | Solid accent color (high contrast)      |
| "See How It Works"             | Homepage hero secondary        | Ghost button / text link                |
| "Download Security Whitepaper" | Security page, homepage footer | Secondary style                         |
| "Get a Custom Quote"           | Pricing page                   | Solid accent color                      |
| "Schedule a Security Review"   | Security page                  | Solid accent color                      |
| "Request a [Industry] Demo"    | Solution pages                 | Solid accent color (pre-fills industry) |
| "Watch the 2-Minute Overview"  | Homepage, platform page        | Play button / video embed               |
| "Subscribe"                    | Blog sidebar                   | Small inline form                       |

**CTA rules**:

- Never use more than 2 CTAs per section (one primary, one secondary)
- Primary CTAs are always above AND below the fold
- The sticky header CTA is always "Request a Demo"
- CTAs should use action verbs ("Request", "Download", "Schedule", "Watch") not passive phrases ("Learn more", "Click here")
- Exception: "Learn more" is acceptable on homepage cards that link to subpages, but style it as a text link, not a button

### 4.4 Trust-Building Sequence

The buyer journey through the site should build trust incrementally:

```
Page 1 — Homepage:
  Trust signal: Social proof bar (logos or compliance badges)
  Trust signal: "100% On-Premise / Zero Cloud" badges
  Trust signal: Competitive comparison table
  Buyer thinks: "This looks legitimate and different."

Page 2 — Solutions or Platform:
  Trust signal: Industry-specific language shows domain expertise
  Trust signal: Technical depth shows real product (not vaporware)
  Trust signal: Architecture diagrams show engineering maturity
  Buyer thinks: "They understand my industry and have a real product."

Page 3 — Security:
  Trust signal: Compliance framework detail
  Trust signal: Audit and governance capabilities
  Trust signal: Downloadable security documentation
  Buyer thinks: "This could actually pass our compliance review."

Page 4 — Pricing:
  Trust signal: Transparent pricing shows business maturity
  Trust signal: Clear implementation timeline
  Buyer thinks: "I can build a business case for this."

Page 5 — About:
  Trust signal: Experienced leadership with relevant backgrounds
  Trust signal: Dedicated engineering team (not 2 people in a garage)
  Buyer thinks: "This company will be around in 2 years."

Page 6 — Contact:
  Trust signal: Professional form with clear expectations
  Trust signal: Fast response time commitment
  Trust signal: No-pressure framing
  Buyer thinks: "I am ready to have a conversation."
```

---

## 5. Content Strategy

### 5.1 Content That Needs to Be Written from Scratch

| Content               | Priority | Est. Length            | Notes                                                                   |
| --------------------- | -------- | ---------------------- | ----------------------------------------------------------------------- |
| Homepage (new)        | P0       | 400-600 words          | Completely new. None of the current homepage copy is usable as-is.      |
| Security page         | P0       | 1,500-2,000 words      | Detailed, factual, no fluff. Include downloadable PDF.                  |
| Pricing page          | P0       | 500-800 words          | Tier descriptions + FAQ                                                 |
| 4 Solutions pages     | P0       | 800-1,200 words each   | Industry-specific. Pull from current scenarios but rewrite entirely.    |
| Security whitepaper   | P1       | 3,000-5,000 words      | Gated PDF. Deep technical security architecture detail.                 |
| Privacy policy        | P1       | Legal document         | Hire a lawyer or use a generator. The current dead link is a liability. |
| Terms of service      | P1       | Legal document         | Same.                                                                   |
| 3 Comparison pages    | P1       | 1,000-1,500 words each | vs OpenAI, vs Ollama, vs HuggingFace                                    |
| About / company story | P2       | 500-800 words          | New narrative, not the current "Development Philosophy"                 |
| 3-5 launch blog posts | P2       | 800-1,500 words each   | Thought leadership + SEO capture                                        |
| Platform page         | P0       | 1,200-1,800 words      | Technical but accessible                                                |
| Platform subpages (3) | P1       | 800-1,200 words each   | Engine, Marketplace, Deployment deep dives                              |

**Total new content needed: approximately 20,000-30,000 words across all pages.**

### 5.2 Content That Can Be Salvaged and Rewritten

| Current Content                                    | Salvage Value | What to Keep                                          | What to Kill                                                   |
| -------------------------------------------------- | ------------- | ----------------------------------------------------- | -------------------------------------------------------------- |
| Hero headline ("Local Private AI. On Your Terms.") | Medium        | The general idea. Rewrite for more impact.            | The typo. The jargon-heavy subheading.                         |
| Problem section (5 pain points)                    | High          | The insights are correct. Condense from 5 to 3-4.     | The dense paragraph format. The academic tone.                 |
| Competitive table                                  | Very High     | The structure and data points. This is gold.          | Nothing — expand it.                                           |
| Platform overview                                  | Medium        | The "OS for AI" metaphor. The three-pillar structure. | The jargon. The walls of text.                                 |
| Inference engine detail                            | Medium        | Technical specs (C++, standard hardware, multi-model) | "C++-optimized inference engine" as a headline.                |
| Marketplace description                            | Medium        | Trust broker concept. Two-way protection.             | "Talk about models" CTA.                                       |
| Security & compliance lists                        | High          | The actual security capabilities listed. All of them. | The list format. Needs narrative + visuals.                    |
| Solutions (8 industries)                           | Medium        | Top 4 industries' bullet points.                      | Bottom 4 industries (for now). Expand top 4 into pages.        |
| Use scenarios (15)                                 | Low-Medium    | Best 4 (one per target industry)                      | The other 11. Too many dilutes impact.                         |
| Team bios                                          | Medium        | Founder bios (strong).                                | The paragraph format for non-founders. Shorten to 1 line each. |
| Development philosophy                             | Zero          | Nothing.                                              | Everything. Replace with a company story.                      |

### 5.3 Missing Content Types

| Content Type                  | Status                     | Priority | Rationale                                                                |
| ----------------------------- | -------------------------- | -------- | ------------------------------------------------------------------------ |
| Case studies                  | Does not exist             | P1       | Enterprise buyers need proof. Even 1 anonymized case study helps.        |
| Whitepapers                   | Does not exist             | P1       | Gated content for lead capture. Security whitepaper first.               |
| Product screenshots / demos   | Does not exist             | P0       | A product with no visuals looks like vaporware.                          |
| Architecture diagrams         | Does not exist             | P0       | Technical buyers need to understand the system visually.                 |
| Blog / articles               | Does not exist             | P2       | SEO + thought leadership. 3-5 posts at launch.                           |
| Video (product overview)      | Does not exist             | P1       | 2-minute overview for executives who will not read 5 pages.              |
| ROI calculator                | Does not exist             | P3       | Interactive tool. "Your current AI API spend is $X. With AskSLM: $Y."    |
| Comparison pages              | Does not exist             | P1       | High-intent SEO capture. "AskSLM vs [competitor]"                        |
| Documentation / API reference | Does not exist (public)    | P3       | For technical evaluators. Can be a separate subdomain (docs.askslm.com). |
| Changelog / release notes     | Does not exist             | P3       | Signals active development.                                              |
| Customer logos                | Does not exist             | P0       | Even "in pilot with organizations in healthcare and legal" is something. |
| Compliance certifications     | Does not exist (displayed) | P0       | If SOC 2, HIPAA BAA, or any cert is in progress, say so.                 |

### 5.4 Blog / Resource Center Strategy

**Launch with 3-5 articles that target high-intent keywords:**

1. "Why On-Premise AI Is the Future for Regulated Industries" (pillar content, targets "on-premise AI")
2. "HIPAA-Compliant AI: What Healthcare Organizations Need to Know" (targets "HIPAA AI", "HIPAA compliant AI")
3. "Small Language Models vs. Large Language Models: Why Smaller Is Better for Enterprise" (targets "SLM vs LLM", educational)
4. "The Hidden Costs of Cloud AI APIs: Why Per-Token Pricing Fails at Scale" (targets cost-conscious buyers, supports the 5-20x claim)
5. "Air-Gapped AI Deployment: A Technical Guide for Government IT Teams" (targets government vertical)

**Ongoing cadence**: 2-4 posts per month. Mix of:

- Thought leadership (industry trends, AI governance, compliance)
- Technical deep dives (how the engine works, TEE architecture, benchmark results)
- Industry spotlights (how AI transforms legal, healthcare, etc.)
- Product updates (new models in marketplace, new features)

**Resource center structure**:

```
/resources/
├── /blog/ .............. All articles (filterable by tag)
├── /case-studies/ ...... Customer stories (when available)
└── /whitepapers/ ....... Gated PDFs (security, compliance, ROI)
```

---

## 6. Technical Recommendations

### 6.1 Framework Recommendation

**Recommended: Astro with React islands.**

| Option               | Pros                                                                                                        | Cons                                                                | Verdict                     |
| -------------------- | ----------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------- | --------------------------- |
| **Astro**            | Zero JS by default, excellent Core Web Vitals, MDX for blog, partial hydration, image optimization built in | Smaller ecosystem than Next.js                                      | **Winner**                  |
| Next.js (App Router) | Massive ecosystem, RSC, ISR, Vercel integration                                                             | Over-engineered for a marketing site, JS-heavy, slower than needed  | Runner-up                   |
| Framer / Webflow     | Designer-friendly, fast to ship, built-in CMS                                                               | Limited customization, vendor lock-in, poor for custom interactions | Good for MVP if no dev time |
| 11ty / Hugo          | Fast static builds, markdown-native                                                                         | No component model, limited interactivity, dated DX                 | Not recommended             |
| Plain HTML (current) | Simple                                                                                                      | Unmaintainable, no CMS, no templating, no image optimization        | Absolutely not              |

**Why Astro wins for AskSLM**:

1. **Performance**: Ships zero JavaScript by default. For a marketing site targeting enterprise buyers who judge credibility by page speed, this matters. Perfect Lighthouse scores out of the box.
2. **Content-first**: Built for content sites. MDX support means the blog and resource center are trivial to build.
3. **Partial hydration**: Interactive elements (pricing calculator, comparison tables, form validation) use React "islands" — the rest is static HTML.
4. **Image optimization**: Built-in `<Image>` component handles WebP/AVIF, srcset, lazy loading, and width/height attributes automatically. Solves every image issue in the current audit.
5. **SEO-native**: Generates proper HTML pages with full meta tags, sitemap.xml, robots.txt, structured data. Solves the entire "single-page site" problem.
6. **Tailwind CSS**: First-class support. Clean, consistent styling with no custom CSS chaos.

**Stack**:

```
Framework:   Astro 5.x
Styling:     Tailwind CSS 4.x
Components:  React (for interactive islands only)
Content:     MDX (blog posts, case studies)
Deployment:  Cloudflare Pages (already their host) or Vercel
Forms:       See section 6.3
Analytics:   See section 6.4
```

### 6.2 CMS Needs

**Does AskSLM need a CMS?** Not immediately. Here is the decision tree:

**If the marketing team is technical (comfortable editing MDX files in GitHub)**:

- Use Astro's built-in Content Collections with MDX files
- Blog posts are `.mdx` files in a `/content/blog/` directory
- Merging a PR publishes a post
- Cost: $0
- This is what Astro is designed for

**If the marketing team needs a visual editor**:

- Add a headless CMS: **Keystatic** (free, Git-based, built for Astro) or **Sanity** (free tier, more powerful, hosted)
- Keystatic is the lighter option — it stores content as files in the repo, provides a visual editor, and requires zero infrastructure
- Sanity is better if they need collaboration features, scheduled publishing, or rich asset management

**Recommendation**: Start with MDX files in the repo. Add Keystatic later if non-technical team members need to publish content. Do NOT add a CMS before there is someone publishing regularly.

### 6.3 Form Handling

**The current form submits to nowhere.** This is not an exaggeration — the `<form>` tag has no `action` attribute, and there is no JavaScript form handler. Every demo request since the site launched has been lost.

**Recommended solution: Formspree (starter) or HubSpot (growth)**

| Option               | Cost                        | CRM                | Email Notification | Spam Protection     | Verdict               |
| -------------------- | --------------------------- | ------------------ | ------------------ | ------------------- | --------------------- |
| **Formspree**        | Free (50 subs/mo) to $10/mo | Zapier integration | Yes                | reCAPTCHA, honeypot | Good for launch       |
| **HubSpot Free CRM** | Free                        | Built-in CRM       | Yes                | Built-in            | Best for growth       |
| Netlify Forms        | Free (100 subs/mo)          | Zapier             | Yes                | Honeypot            | Only if using Netlify |
| Custom API           | Dev time                    | Custom             | Custom             | Custom              | Overkill              |

**Recommendation**: Use **HubSpot Free CRM** as the form backend. Reasons:

1. The form submission goes directly into a CRM where the sales team can track leads
2. Automatic email notifications to the team
3. Lead scoring and pipeline management as the company grows
4. Free tier is generous (up to 1,000 contacts)
5. Integrates with email marketing when they start nurturing leads

**Form implementation**:

- Use HubSpot's embedded form (they generate a form embed code) or submit via HubSpot's API from a custom-styled form
- Add honeypot field for spam protection
- Add client-side validation (required fields, email format)
- Redirect to a /contact/thank-you/ page after submission
- On the thank-you page: embed a Calendly widget so the lead can self-schedule immediately

### 6.4 Analytics & Tracking

**Current state**: Google Analytics 4 (G-QRJ537RVQF) via gtag.js. That is it.

**Recommended stack**:

| Tool                          | Purpose                                               | Priority              |
| ----------------------------- | ----------------------------------------------------- | --------------------- |
| **Google Analytics 4** (keep) | Baseline traffic and acquisition data                 | P0                    |
| **Google Search Console**     | Organic search performance, indexing, Core Web Vitals | P0                    |
| **LinkedIn Insight Tag**      | LinkedIn ad retargeting, website demographics         | P0                    |
| **PostHog** or **Plausible**  | Privacy-friendly product analytics, event tracking    | P1                    |
| **Microsoft Clarity**         | Session replay, heatmaps (free)                       | P1                    |
| **HubSpot tracking code**     | Lead attribution, form analytics                      | P0 (if using HubSpot) |

**Event tracking plan (minimum viable)**:

| Event                 | Trigger                         | Parameters                            |
| --------------------- | ------------------------------- | ------------------------------------- |
| `cta_click`           | Any CTA button clicked          | `cta_text`, `page`, `section`         |
| `form_start`          | First form field focused        | `form_id`, `page`                     |
| `form_submit`         | Form successfully submitted     | `form_id`, `industry`, `company_size` |
| `form_abandon`        | Form started but page exited    | `form_id`, `last_field_filled`        |
| `whitepaper_download` | Whitepaper PDF downloaded       | `document_name`                       |
| `video_play`          | Product video played            | `video_name`, `page`                  |
| `scroll_depth`        | 25%, 50%, 75%, 100% page scroll | `page`, `depth`                       |
| `comparison_view`     | Comparison table viewed         | `page`                                |
| `pricing_view`        | Pricing page visited            | —                                     |

**LinkedIn Insight Tag is critical.** AskSLM's buyers are on LinkedIn. The Insight Tag enables: (a) retargeting website visitors with LinkedIn ads, (b) understanding visitor demographics (company, title, industry) without form fills, (c) conversion tracking for LinkedIn ad campaigns. For a B2B enterprise play, this is more valuable than Facebook Pixel or any other tracking pixel.

### 6.5 Security Headers (for their own site)

The technical SEO audit found that askslm.com — a company selling security — has zero security headers on its own website. This is embarrassing and fixable in 5 minutes via Cloudflare.

**Add these headers via Cloudflare Workers or Transform Rules:**

```
Strict-Transport-Security: max-age=31536000; includeSubDomains
Content-Security-Policy: default-src 'self'; script-src 'self' https://www.googletagmanager.com https://snap.licdn.com; img-src 'self' data:; style-src 'self' 'unsafe-inline';
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
Referrer-Policy: strict-origin-when-cross-origin
Permissions-Policy: camera=(), microphone=(), geolocation=()
```

Also: force HTTPS redirect (one-click in Cloudflare dashboard).

### 6.6 Infrastructure Summary

```
Domain:        askslm.com (Cloudflare DNS — keep)
Hosting:       Cloudflare Pages (keep) or Vercel (if using Astro)
CDN:           Cloudflare (keep)
SSL:           Cloudflare (fix HTTP→HTTPS redirect)
Forms:         HubSpot Free CRM
Analytics:     GA4 + GSC + LinkedIn Insight + PostHog
Email:         Existing (contact@askslm.com)
Images:        Self-hosted (move off Wix CDN)
Blog content:  MDX files in repo (or Keystatic if needed)
CI/CD:         GitHub Actions → Cloudflare Pages (or Vercel auto-deploy)
```

---

## 7. Launch Prioritization

### Phase 1: Foundation (Weeks 1-3)

- [ ] Brand identity: Finalize name (AskSLM), color palette, typography, logo refresh
- [ ] Homepage: Write, design, build
- [ ] Security page: Write, design, build
- [ ] Contact page: Build with working form (HubSpot)
- [ ] Platform overview page: Write, design, build
- [ ] Privacy policy and Terms of Service: Get written
- [ ] Fix HTTPS redirect and add security headers
- [ ] Set up Google Search Console
- [ ] Deploy Astro site to Cloudflare Pages (or Vercel)

### Phase 2: Depth (Weeks 3-5)

- [ ] 4 Solutions pages (Legal, Healthcare, Financial Services, Government)
- [ ] Pricing page
- [ ] About / Team page (with new consistent headshots)
- [ ] 3 Platform subpages (Engine, Marketplace, Deployment)
- [ ] Proper sitemap.xml with all pages
- [ ] Open Graph and Twitter Card meta tags on all pages
- [ ] JSON-LD structured data (Organization, WebSite)
- [ ] LinkedIn Insight Tag
- [ ] Product screenshots or mockups commissioned

### Phase 3: Growth (Weeks 5-8)

- [ ] Security whitepaper (written + gated PDF)
- [ ] 3 Comparison pages (vs OpenAI, vs Ollama, vs HuggingFace)
- [ ] Blog infrastructure + 3 launch posts
- [ ] Product overview video (2 minutes)
- [ ] Event tracking implementation
- [ ] Session replay tool (Clarity)

### Phase 4: Optimization (Ongoing)

- [ ] A/B test hero headlines
- [ ] Add case studies as customers come online
- [ ] Expand blog to 2-4 posts/month
- [ ] Build ROI calculator
- [ ] Add Calendly scheduling embed
- [ ] WCAG 2.1 AA accessibility audit
- [ ] Consider docs.askslm.com for technical documentation

---

## 8. Open Questions for the Founder

These decisions affect the architecture and should be resolved before build begins:

1. **Brand name**: Is it "AskSLM" or "Secure SLM"? The site currently uses both. Pick one. I recommend AskSLM (it is the domain, it is more memorable, and "Ask" implies interaction).

2. **Pricing transparency**: Are you willing to publish starting prices on the website? Even ballpark ranges help conversion. If not, the pricing page becomes a "How Pricing Works" explainer.

3. **Customer evidence**: Do you have ANY pilot customers, design partners, or paid users? Even 1 logo or quote transforms the social proof situation. If not, can you name industries you are piloting in, even without company names?

4. **Compliance certifications**: Is SOC 2, HIPAA BAA, ISO 27001, or FedRAMP in progress? If so, we can show "in progress" badges. If not, what is the timeline?

5. **Product visuals**: Is the product UI far enough along to screenshot? If not, are you open to commissioning professional mockups or architecture illustrations?

6. **Who publishes content?** Does the team have someone who will write blog posts and case studies, or does content creation need to be outsourced? This affects CMS decisions.

7. **Target launch date**: This roadmap assumes 6-8 weeks. Is that realistic given team bandwidth?

8. **Budget for design**: Is there budget for a professional brand identity (logo, color system, illustration style, icon set) or is this being done in-house?
