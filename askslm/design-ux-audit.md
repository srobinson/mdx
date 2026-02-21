# AskSLM.com Design, UX, and Conversion Audit

**Date**: 2026-02-22
**URL**: <https://www.askslm.com/>
**Type**: Single-page marketing site (all anchor-based navigation)
**Platform**: Custom HTML with Wix-hosted image assets
**Verdict**: The site has real substance but buries it under amateur execution. It reads like a technical spec sheet, not a selling machine.

---

## Executive Summary

AskSLM is building a genuinely compelling product: on-premise AI inference for regulated industries with a marketplace, training pipeline, and hardware-bound encryption. The technology story is strong. The website, however, actively undermines credibility at every turn.

The core problems are:

1. **Massive content overload** -- the single page tries to be a brochure, technical whitepaper, team page, product docs, and contact form all at once
2. **No visual identity** -- generic, template-tier aesthetics with no brand personality
3. **Zero social proof** -- no customer logos, testimonials, case studies, or adoption metrics
4. **Wall-of-text syndrome** -- dense paragraphs that enterprise buyers will never read
5. **Identity confusion** -- the site uses "AskSLM," "Secure SLM," and references both interchangeably, which fractures brand clarity

An enterprise buyer visiting this site for the first time would leave within 10 seconds. A CISO or compliance officer evaluating the tool would find the content useful but the presentation untrustworthy. The site looks like it was built by the engineering team, not a design team -- and enterprise buyers in regulated industries judge credibility by appearance first.

---

## 1. Visual Design Audit

### 1.1 Layout and Spacing

**Problem: Single-page mega-scroll with no breathing room.**

The entire site is one continuous page with approximately 15+ distinct content sections accessed via anchor links. This creates several issues:

- **Cognitive overload**: A visitor scrolling from top to bottom encounters thousands of words of content with no natural stopping points
- **No section separation**: Without clear visual breaks, sections blend into each other
- **Inconsistent density**: Some sections (Problem, Engine) are relatively tight, while Solutions and Use Cases explode into massive lists
- **The "Real-World Use Scenarios" section alone contains 15 detailed scenario boxes** -- this is an entire subsite worth of content crammed into one scroll

**Recommendation**: Break into 5-7 focused pages. The homepage should be 3-4 screens max: hero, problem/solution, proof points, CTA.

### 1.2 Typography

**Problem: No discernible typographic system or hierarchy.**

- No evidence of a professional font stack (no Google Fonts, no custom @font-face detected)
- System fonts or basic web-safe fonts are likely being used -- this screams "template"
- Heading hierarchy exists in HTML (h1 through h4) but without visual differentiation through weight, size, or color, the hierarchy is semantic only, not visual
- Body text appears dense with no variation in paragraph length or formatting to create rhythm

**Recommendation**: Choose one premium sans-serif (e.g., Inter, General Sans, or Satoshi for modern SaaS) paired with a system font for body. Establish a clear type scale with visible differentiation between heading levels.

### 1.3 Color Palette

**Problem: No identifiable brand colors.**

- No hex codes, CSS custom properties, or color system detected in the markup
- The competitive comparison table uses basic checkmarks/X marks with no color coding
- No accent colors for CTAs, no gradient treatments, no brand-color usage visible
- The site appears to rely on default browser styling or minimal custom CSS

**Recommendation**: Establish a 5-color palette: primary brand color (trustworthy -- think dark blue or deep teal for regulated industries), accent for CTAs (high-contrast orange/green), neutral dark for text, neutral light for backgrounds, and a warning/highlight color. Apply consistently.

### 1.4 Visual Hierarchy

**Problem: Everything has equal visual weight.**

- The hero headline "Local Private AI. On Your Terms." is strong copy buried in a page where every section screams for attention
- Feature lists, use cases, team bios, technical specs, and contact forms all compete at the same volume
- No visual anchors (large numbers, icons with weight, colored cards, gradient backgrounds) to guide the eye
- The competitive comparison table is actually a powerful selling tool but gets lost mid-page

**Recommendation**: Ruthlessly prioritize. The hero, problem statement, competitive table, and CTA should dominate. Everything else should be secondary or on subpages.

### 1.5 Whitespace

**Problem: Content-crammed throughout.**

- The 15 "Real-World Use Scenarios" are listed consecutively with no grouping or progressive disclosure
- The Solutions section lists 8 industries with 4 bullet points each, creating a wall of sameness
- Team section shows 8 profiles with bios -- this is fine for an About page but excessive for a homepage
- Feature lists run 4-6 items deep in multiple consecutive sections

**Recommendation**: Apply the "half the words, twice the impact" rule. Every section should have 40-60% whitespace. Use expandable/accordion patterns for detailed content.

### 1.6 Image Quality and Relevance

**Problem: Minimal imagery, inconsistent sourcing.**

Detected images:

- `logo.png` -- company logo (header/footer)
- `spoke2.png` -- hero visual (vague, likely a generic "network" diagram)
- Team photos: Mix of local files (`./images/clint.jpg`) and Wix-hosted images (`static.wixstatic.com/...`)
- **No product screenshots whatsoever**
- **No diagrams of the architecture they describe in detail**
- **No visual representation of the marketplace, training interface, or deployment flow**

The Wix image URLs with `?auto=compress&cs=tinysrgb&w=400&h=400&fit=crop` parameters suggest some images were pulled from a Wix site builder or stock photo service -- this is extremely visible to anyone who inspects the page.

**Recommendation**: Commission or create: (1) A hero illustration showing on-premise vs. cloud AI visually, (2) Product UI screenshots or mockups, (3) Architecture diagrams for the inference engine, (4) Marketplace interface screenshots, (5) Professional, consistent team photos with uniform background/lighting.

### 1.7 Overall Aesthetic

**Verdict: Dated, generic, and template-tier.**

The site has no visual identity. It could be any B2B startup from 2018. There are no micro-interactions, no animations, no scroll-triggered reveals, no gradient treatments, no custom illustrations, no dark mode sections, no glass-morphism, no anything that signals "we are a serious, well-funded technology company."

Compare to best-in-class AI/enterprise sites (Cohere, Scale AI, Anthropic, Vercel, Linear): those sites use bold typography, generous whitespace, dark themes or sophisticated color, animated product demos, and minimal copy that lets the product speak.

AskSLM looks like the founders wrote everything themselves in HTML and styled it minimally. For a company selling to CISOs and compliance officers at banks and hospitals, this is a credibility killer.

---

## 2. UX Issues

### 2.1 Navigation Clarity and Structure

**Problem: 10-item single-page nav is overwhelming and non-standard.**

Navigation items: Home, The Problem, Engine, Marketplace, Training, Deployment, Solutions, Team, Development Philosophy, Contact.

Issues:

- **10 items is too many** for a top nav. Best practice is 5-7 max
- **"The Problem" as a nav item is unusual** -- this is a content strategy choice, not a navigation pattern enterprise buyers expect
- **"Development Philosophy" does not belong in primary nav** -- this is internal culture content, not a buying-decision page
- **All items are same-page anchors** -- clicking "Solutions" jumps you down a massive page rather than taking you to a focused solutions page. This means the browser back button does not work as expected
- **No dropdown menus** for grouping (e.g., Platform > Engine, Marketplace, Training)

**Recommendation**: Top nav should be: Platform, Solutions, Security, About, Contact/Demo. Subpages handle depth. Team and Philosophy go under About.

### 2.2 Information Architecture

**Problem: Flat structure with no hierarchy.**

Everything is on one page. There is no concept of primary vs. secondary content. A CISO looking for security details must scroll past the team section. A buyer looking for their industry must scroll past the inference engine technical details.

The sitemap.xml confirms this: only one URL exists (`https://askslm.com/`).

**Recommendation**: Minimum viable sitemap:

- **Homepage**: Hero, value prop, 3 key benefits, social proof, CTA
- **/platform**: Engine, Marketplace, Training, Deployment (tabbed or sub-nav)
- **/solutions**: Industry-specific pages (Legal, Healthcare, Finance, Government)
- **/security**: Dedicated security and compliance page (critical for this audience)
- **/about**: Team, philosophy, company story
- **/contact**: Demo request form
- **/use-cases**: Detailed scenario pages (one per industry)

### 2.3 CTA Clarity

**Problem: Weak and repetitive CTAs.**

- Primary CTAs: "Request a Demo" and "Explore the Platform"
- "Explore the Platform" just scrolls down the page -- misleading, as buyers expect this to open a product tour or separate page
- "Talk about models" appears mid-page as a marketplace CTA -- informal and unclear
- The contact form at the bottom is the sole conversion mechanism
- **No secondary conversion paths**: no newsletter signup, no whitepaper download, no product video, no free assessment tool

**Recommendation**: Primary CTA should be "Request a Demo" everywhere. Add secondary paths: "Download Security Whitepaper" (captures emails from researchers), "Watch 2-Minute Overview" (video for executives), "See Pricing" (for serious buyers).

### 2.4 Content Flow

**Problem: The narrative does not follow a buyer's journey.**

Current flow: Hero > Problem > Technical Specs > Marketplace > Training > Deployment > Security > Solutions > Use Cases > Team > Philosophy > Contact

A B2B enterprise buyer's mental model is:

1. What is this? (5 seconds)
2. Is this for me? (15 seconds)
3. How is it different? (30 seconds)
4. Who else uses it? (trust)
5. How does it work? (detail)
6. What does it cost? (feasibility)
7. How do I get started? (action)

The site skips steps 4 and 6 entirely and front-loads step 5 (technical details) before the buyer even cares.

**Recommendation**: Restructure homepage flow to: Hero (what + who) > Social Proof (logos/quotes) > Problem/Solution (why) > Competitive Advantage (differentiation table) > Industry Solutions (brief, linked) > CTA.

### 2.5 Mobile Responsiveness

**Problem: Unknown but likely poor.**

- No CSS framework (Bootstrap, Tailwind) detected -- responsive behavior depends entirely on custom CSS
- The competitive comparison table (6 columns) will break or be unreadable on mobile
- 10-item navigation will need a hamburger menu that was not detectable
- Dense text blocks will be even harder to read on small screens
- Team photo grid may not stack properly

**Recommendation**: Mobile-first redesign is mandatory. Over 60% of initial visits may come from mobile (LinkedIn links, email clicks from phones).

### 2.6 Performance Concerns

- Google Analytics loaded inline (render-blocking potential)
- No evidence of lazy loading on images
- Mixed image hosting (local files + Wix CDN) suggests ad-hoc development
- No evidence of minification, bundling, or modern build tooling
- The sheer volume of content on one page means large DOM size

### 2.7 Accessibility Red Flags

- No ARIA labels or roles detected beyond basic alt text
- No skip-to-content link
- Form fields may lack proper label associations
- Color contrast unknown but likely problematic given no defined color system
- No focus indicators visible for keyboard navigation

---

## 3. Copywriting Problems

### 3.1 Value Proposition Clarity

**Partial pass.** The hero line "Local Private AI. On Your Terms." is decent -- it communicates the core idea in 6 words. The subheading clarifies the target audience (regulated industries).

**But**: The supporting text immediately dives into feature language: "secure, local inference," "full data sovereignty," "verifiable compliance," "zero cloud risk." These are feature statements, not benefit statements. A hospital administrator does not care about "local inference" -- they care about "keep patient data safe while using AI."

**Also**: There is a typo in the hero: "where you data lives" (should be "your"). On the first line of the site. This is a credibility destroyer for a company selling to enterprise.

### 3.2 Jargon and Unclear Language

**Severe jargon problem throughout.** Examples:

- "C++-optimized inference engine" -- meaningless to a buyer
- "Hardware-bound encrypted execution" -- technical, not benefit-oriented
- "Trusted Execution Environments" -- niche technical term used without explanation
- "Multi-model concurrency" -- developer language
- "RAG" appears without definition (Retrieval-Augmented Generation)
- "Inference stack" -- internal engineering term
- "Hardware-software co-design" -- academic language

The entire site reads like it was written by and for engineers, not for the C-suite buyers who sign 6-figure enterprise contracts.

**Recommendation**: Every technical concept needs a plain-English translation. "Runs AI models locally so your data never leaves your building" instead of "C++-optimized inference engine for on-premise deployment."

### 3.3 Weak Headlines

Many section headlines are functional but uninspiring:

- "The Problem: Why Current AI Fails High-Value Markets" -- decent but long
- "User-Friendly Training & Knowledge Updates" -- generic, could be any product
- "On-Premise Deployment, Simplified" -- cliched "X, Simplified" pattern
- "Security & Compliance by Design" -- overused phrase in enterprise software
- "Solutions for Regulated Industries" -- purely descriptive, no hook
- "Real-World Use Scenarios" -- bland

**Recommendation**: Headlines should create urgency or challenge assumptions. "Your competitors are using AI. Yours stays compliant." or "The AI your legal team will actually approve."

### 3.4 Missing Social Proof

**This is the single biggest credibility gap on the site.**

- **Zero customer logos**
- **Zero testimonials or quotes**
- **Zero case studies**
- **Zero usage statistics** ("X models deployed," "Y organizations," etc.)
- **Zero third-party validation** (awards, analyst mentions, certifications)
- **Zero press mentions**
- **Zero partnership logos** (hardware vendors, compliance frameworks)

The only implied credibility is the team bios (founder with "multiple exits," CTO with "20+ year career"). This is necessary but nowhere near sufficient for enterprise buyers who need organizational proof, not individual proof.

**Recommendation**: Even pre-revenue, you can show: pilot customer logos (with permission), advisor/investor logos, compliance framework logos (SOC 2, HIPAA, etc.), hardware partner logos (if using Intel SGX or AMD SEV for TEEs), and "in use by X organizations across Y industries" even if numbers are small.

### 3.5 Tone/Voice Consistency

The tone oscillates between:

- **Marketing speak**: "Bring the Future of Secure, Local AI Into Your Organization"
- **Technical documentation**: "C++-optimized inference engine, transparent and auditable training pipeline"
- **Startup pitch deck**: "battle-tested founding team," "high-velocity engineering group"
- **Sales copy**: "consistently outperform the market"

There is no unified brand voice. For a regulated-industry enterprise product, the voice should be: **authoritative, clear, measured, and trustworthy** -- like a senior partner at a law firm, not like a startup pitch deck.

### 3.6 CTA Text Quality

- "Request a Demo" -- standard, acceptable
- "Explore the Platform" -- misleading (just scrolls down the page)
- "Talk about models" -- too casual and vague for enterprise buyers
- Submit button on form -- should say "Request Your Demo" or "Get Started"

---

## 4. Conversion Optimization

### 4.1 Conversion Path

**Problem: Single, weak conversion path.**

The only conversion mechanism is a contact form at the bottom of a very long page. To reach it, a visitor must scroll through approximately 15 sections of content or know to click "Contact" in the nav.

There is no:

- Sticky header CTA that follows the user
- Mid-page conversion opportunities
- Exit-intent popup
- Chat widget
- Calendly/scheduling embed
- Phone number
- Secondary lead magnets (whitepapers, assessments, ROI calculators)

**Recommendation**: Add a sticky "Request Demo" button in the header. Add mid-page CTAs after the Problem and Competitive Table sections. Add a "Download Security Whitepaper" as a secondary lead capture. Consider a Calendly embed for direct scheduling.

### 4.2 Trust Signals

**Almost entirely absent.**

Missing:

- Security certifications (SOC 2, ISO 27001, HIPAA BAA)
- Compliance framework logos
- Customer testimonials
- Case study links
- "As seen in" press logos
- Partnership badges
- Uptime/reliability statistics
- Data handling certifications

Present:

- Team bios with experience claims (weak trust signal)
- Technical claims about encryption and on-premise deployment (unverified)
- Austin, TX location (minor trust signal)

For a company selling to **regulated industries** (healthcare, finance, legal, government), the absence of compliance certifications and third-party validation is a dealbreaker.

### 4.3 Objection Handling

The site does address some objections implicitly:

- "Runs on standard hardware" (addresses cost/infrastructure concerns)
- "No ML engineers needed" (addresses talent concerns)
- Competitive comparison table (addresses "why not OpenAI/HuggingFace")

**Missing objection handling:**

- "Is this actually production-ready?" (no deployment metrics, no uptime claims)
- "Can we try before we buy?" (no free trial, no sandbox)
- "What does implementation look like?" (no timeline or process description)
- "What happens if it breaks?" (no SLA or support guarantees mentioned)
- "What does it cost?" (pricing completely absent)

### 4.4 Pricing Clarity

**Pricing is completely absent.** The site mentions "5-20x cost reduction" and "subscription and usage-based plans" but provides zero actual pricing information.

For enterprise sales, this is not unusual (custom pricing is common), but the site should at least have:

- Starting price or "plans from $X/month"
- A pricing page with tier names and feature comparisons
- Or at minimum, "Contact us for pricing" as an explicit statement

---

## 5. Competitive Context

### 5.1 What Kind of Business Is This?

AskSLM (also branded "Secure SLM") is an **on-premise AI inference platform** targeting regulated industries. Their value proposition is:

- Run Small Language Models locally (no cloud dependency)
- A marketplace for pre-trained, domain-specific models
- Training tools for fine-tuning with proprietary data
- Hardware-bound encryption for compliance
- A C++ inference engine optimized for standard (non-GPU) hardware

This positions them in the intersection of:

- **Edge AI / On-Premise AI** (competitors: Ollama, LM Studio, Jan.ai for consumer; NVIDIA AI Enterprise, HPE, Dell for enterprise)
- **AI for Regulated Industries** (competitors: Microsoft Azure with compliance features, AWS GovCloud, Palantir AIP)
- **SLM/LLM Marketplaces** (competitors: Hugging Face, Replicate, Together AI)

### 5.2 Target Audience

Based on the site content, they are targeting:

- **Primary**: CISOs, CTOs, and compliance officers at mid-to-large enterprises in legal, healthcare, finance, and government
- **Secondary**: IT directors evaluating AI deployment options
- **Tertiary**: Domain experts (lawyers, doctors, financial analysts) who would use the models

The buying committee for this product is 3-5 people: a technical evaluator, a compliance officer, an executive sponsor, and possibly procurement. The site needs to serve all of them, currently it only speaks to the technical evaluator.

### 5.3 What Best-in-Class Looks Like

**Direct competitors' sites to study:**

- **Ollama** (ollama.com) -- clean, developer-focused, "just works" messaging
- **Palantir AIP** (palantir.com) -- dark, authoritative, enterprise gravitas, video-first
- **Scale AI** (scale.com) -- bold design, motion graphics, customer logos everywhere
- **Anthropic** (anthropic.com) -- clean, minimal, trust-building through restraint
- **Cohere** (cohere.com) -- enterprise AI with clear use cases, product demos front and center

**What these sites have in common:**

1. Minimal text on the homepage (under 500 words above the fold)
2. Strong visual identity (custom illustrations, consistent color, premium typography)
3. Customer logos prominently displayed
4. Product screenshots or interactive demos
5. Clear navigation to focused subpages (not mega-scroll)
6. One primary CTA repeated consistently
7. Fast load times, smooth animations
8. Mobile-first responsive design

---

## 6. Priority Recommendations (Rebuild Roadmap)

### Tier 1: Critical (Do First)

| #   | Issue                                  | Action                                                                                                   |
| --- | -------------------------------------- | -------------------------------------------------------------------------------------------------------- |
| 1   | Single-page structure                  | Break into 5-7 focused pages with clear IA                                                               |
| 2   | No visual identity                     | Commission brand identity: logo refresh, color palette, type system, illustration style                  |
| 3   | Zero social proof                      | Get 3-5 pilot customer quotes/logos. If none exist, use advisor quotes, partner logos, compliance badges |
| 4   | Hero typo ("you" vs "your")            | Fix immediately -- this is visible in the first sentence                                                 |
| 5   | Content overload                       | Cut homepage to 4 sections: Hero, Problem/Solution, Proof, CTA. Move everything else to subpages         |
| 6   | Brand confusion (AskSLM vs Secure SLM) | Pick one name. Use it everywhere. Kill the other                                                         |

### Tier 2: Important (Do Next)

| #   | Issue                  | Action                                                                                    |
| --- | ---------------------- | ----------------------------------------------------------------------------------------- |
| 7   | No product visuals     | Create UI screenshots/mockups, architecture diagrams, deployment flow visuals             |
| 8   | Jargon-heavy copy      | Rewrite all copy for C-suite audience. Technical details go on a dedicated /platform page |
| 9   | Weak CTAs              | Sticky header CTA, mid-page CTAs, secondary lead magnets (whitepaper, video)              |
| 10  | No pricing information | Add pricing page or at least "Plans starting from..."                                     |
| 11  | Missing security page  | Dedicated /security page with compliance frameworks, certifications, architecture diagram |
| 12  | Navigation overhaul    | 5-item top nav with dropdowns. Platform, Solutions, Security, About, Contact              |

### Tier 3: Polish (Do After Rebuild)

| #   | Issue                      | Action                                                             |
| --- | -------------------------- | ------------------------------------------------------------------ |
| 13  | No animations/interactions | Add subtle scroll animations, hover states, micro-interactions     |
| 14  | Accessibility              | Full WCAG 2.1 AA compliance (critical for government clients)      |
| 15  | Performance optimization   | Lazy loading, image optimization, code splitting, CDN              |
| 16  | SEO                        | Proper meta tags, structured data, industry-specific landing pages |
| 17  | Analytics/tracking         | Event tracking on CTAs, scroll depth, form abandonment             |
| 18  | Competitive comparison     | Make the comparison table interactive and more prominent           |

---

## 7. Specific Content Issues Log

| Location                  | Issue                                                                            | Severity |
| ------------------------- | -------------------------------------------------------------------------------- | -------- |
| Hero subheading           | Typo: "where you data lives" should be "where your data lives"                   | Critical |
| Hero                      | "spoke2.png" as hero image -- unclear, likely a generic network graphic          | High     |
| Team photos               | Mixed hosting (local + Wix CDN) with visible Wix URL parameters                  | Medium   |
| Copyright                 | "2025" -- outdated, should be "2025-2026" or current year                        | Low      |
| Proprietary value section | Single run-on sentence describing the entire value proposition                   | High     |
| Marketplace section       | "Talk about models" CTA is too informal                                          | Medium   |
| Use Scenarios             | 15 scenarios is excessive for a homepage -- belongs on subpages                  | High     |
| Solutions                 | 8 industries listed with equal weight -- should prioritize top 3-4               | Medium   |
| Team section              | 8 full bios on homepage is excessive                                             | Medium   |
| Development Philosophy    | Entire section is internal culture, not buyer-relevant                           | High     |
| Footer                    | References "Privacy," "Terms," "Security" links but unclear if these pages exist | Medium   |

---

## 8. Technology/Platform Recommendation

The current site appears to be hand-rolled HTML with Wix image hosting. For the rebuild:

**Recommended stack:**

- **Webflow** or **Framer** for the marketing site (designer-friendly, fast iteration, built-in CMS for blog/case studies)
- **Alternatively**: Next.js + Tailwind if the team prefers code-based (better for custom interactions and performance)
- **Hosting**: Vercel or Netlify (fast global CDN, perfect Lighthouse scores)
- **Forms**: Formspree or HubSpot (CRM integration for lead tracking)
- **Analytics**: PostHog or Mixpanel (product-aware analytics, not just pageviews)

**Not recommended:**

- Wix (looks cheap, limited customization, poor performance)
- WordPress (overkill for a marketing site, security overhead)
- Squarespace (limited for B2B enterprise design)

---

## 9. Competitive Benchmarking Summary

| Dimension         | AskSLM (Current)                        | Industry Standard       | Best-in-Class                     |
| ----------------- | --------------------------------------- | ----------------------- | --------------------------------- |
| First impression  | Template/amateur                        | Clean and professional  | Striking and memorable            |
| Load time         | Unknown (likely slow, single huge page) | Under 3 seconds         | Under 1 second                    |
| Social proof      | None                                    | 3-5 logos + 2 quotes    | Logo bar + case studies + metrics |
| Product visuals   | Zero screenshots                        | 2-3 key screenshots     | Interactive demo or video         |
| Mobile experience | Likely broken                           | Functional              | Designed mobile-first             |
| Content density   | Extreme overload                        | Focused, scannable      | Minimal, high-impact              |
| Brand identity    | None                                    | Consistent colors/fonts | Distinctive visual language       |
| Navigation        | 10-item single-page                     | 5-7 items, multi-page   | Contextual, role-based            |
| CTAs              | 1 form at bottom                        | Multiple touchpoints    | Sticky + contextual + secondary   |
| SEO readiness     | Minimal (1 URL in sitemap)              | Basic on-page SEO       | Full technical + content SEO      |

---

## 10. Bottom Line

AskSLM has a **strong product story** trapped inside a **weak website**. The technology positioning (on-premise AI for regulated industries) is genuinely differentiated and timely -- the market is moving toward inference optimization and data sovereignty. But the site actively undermines the product's credibility through:

1. Amateur visual design that signals "early-stage startup" to enterprise buyers who need "established, trustworthy vendor"
2. Content overload that buries the value proposition under technical minutiae
3. Complete absence of social proof in a market where trust is everything
4. A single-page structure that prevents focused, role-specific buyer journeys
5. Jargon-heavy copy written for engineers, not for the executives who write checks

The rebuild should prioritize **trust signals, visual credibility, and content focus** above all else. The product speaks for itself -- the website just needs to get out of the way and let the right people find the right information quickly.

A well-executed rebuild could turn this from a site that "sucks" into a genuine competitive advantage. The content raw material is there; it just needs professional design, strategic restructuring, and buyer-centric copywriting.
