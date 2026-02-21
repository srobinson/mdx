# Voice: Product Brainstorm

## Executive Summary

**Voice** is a CLI tool and runtime library that solves a critical problem at the intersection of AI generation and personal expression: how to eliminate AI's homogeneous writing patterns while preserving each user's authentic voice.

The product bridges a gap: LLMs generate fast but generic. Users want the speed without sacrificing their identity. Voice detects what makes text "sound like an AI" and applies user-defined voice profiles to transform generic output into personalized, authentic-sounding text.

---

## 1. User Personas

### Primary Persona: Dev-to-Docs Engineer
- **Profile**: Software engineer who writes documentation, blog posts, or content-heavy code comments
- **Pain point**: AI-generated documentation violates team style guides. Needs rapid iteration (AI speed) with consistent voice (engineering rigor)
- **Context**: Writes 5-20 pages of AI-assisted content per week. Tired of manual rewrites
- **Motivation**: Autonomy + trust in output quality

### Secondary Persona: Technical Content Creator
- **Profile**: Technical writer, developer advocate, or productmarketing engineer with a distinct voice
- **Pain point**: Inconsistency across AI-assisted pieces destroys personal brand. Each draft requires heavy editing
- **Context**: Produces 10-50 pieces per month (docs, blogs, social content, video scripts)
- **Motivation**: Scale output without diluting brand; maintain authenticity

### Tertiary Persona: Enterprise Content Team
- **Profile**: Small team (3-10 people) managing brand voice across multiple output channels
- **Pain point**: Scaling content creation (social, landing pages, help docs) while maintaining brand consistency. Current solution: extensive style guides that writers ignore
- **Context**: Uses AI for drafting, spends 40% of time on revisions and style corrections
- **Motivation**: Velocity + compliance; enforce brand without micromanaging

### Emerging Persona: Individual AI Users
- **Profile**: Everyday person using ChatGPT, Claude, Copilot to write emails, cover letters, proposals
- **Pain point**: Output is useful but doesn't sound like them. Feels inauthentic
- **Context**: 1-5 pieces per day; low technical literacy but high willingness to learn
- **Motivation**: Utility without artificiality; delegation without loss of self

---

## 2. User Stories & Jobs to Be Done

### Core Job: "Transform generic AI output into authentic, personalized text"

**Story 1: Developer documentation**
- As a developer writing API docs with AI assistance, I want my generated documentation to match my team's voice (concise, example-heavy, light on jargon) so that users recognize our docs by tone alone

**Story 2: Brand consistency at scale**
- As a content team lead, I want all AI-generated content (blogs, social, landing pages) to sound like our brand, not like ChatGPT, so that we can 10x output without hiring 10x writers

**Story 3: Personal authenticity in professional writing**
- As a technical writer, I want my voice profile to capture my style (conversational, precise, no corporate fluff) so that my AI-assisted work feels like me, not a bot pretending to be me

**Story 4: Composable profiles**
- As a developer, I want to combine multiple voice profiles (my personal style + company style + domain conventions) so that my output respects all three constraints simultaneously

**Story 5: Non-technical user**
- As a student writing essays with AI assistance, I want my voice profile to reflect my natural writing so that my professor doesn't flag AI-generated text while I benefit from AI's organizing and editing help

### Jobs to Be Done (JTBD):
1. **Detect what is "AI slop"** — Identify patterns that flag text as machine-generated (em dashes, hedging, repetitive transitions, etc.)
2. **Define personal voice** — Capture what makes a user's writing unique (vocabulary, sentence structure, tone, perspective)
3. **Apply voice at scale** — Transform bulk AI output instantly without manual revision
4. **Iterate on voice** — Update voice profiles as taste evolves; test variations
5. **Share voice professionally** — Distribute team/brand voice profiles without sharing sensitive content

---

## 3. Product Boundaries

### Voice IS:
- A post-generation text transformation layer
- AI slop detection and filtering engine
- User voice profile management and application
- A portable, composable representation of writing style
- A CLI-first tool (integrable into any workflow)
- An open standard for voice profiles

### Voice IS NOT:
- A writing assistant (that's Claude, GPT, etc.)
- A grammar checker (that's Grammarly)
- A content generator (that's an LLM)
- A spell checker or punctuation tool
- A fact-checker or plagiarism detector
- A style guide authoring tool (Hemingway Editor)
- A collaborative writing platform
- An LLM fine-tuning service

### Intentional Boundaries:
- **Voice doesn't generate**; it filters and transforms. If you have no AI output to start with, Voice doesn't help. (Implication: complementary to LLMs, not a replacement)
- **Voice doesn't teach writing**; it enforces style. It won't make you a better writer, but it will make your AI output sound like you
- **Voice doesn't replace editing**; it accelerates it. A human still reviews the output; Voice just removes the tedious slop layer first

---

## 4. Differentiation

### Vs. Prompt Engineering
- **Limitation**: Prompt engineering is fragile (works with one model, breaks with another) and non-portable (baked into system prompts)
- **Voice advantage**: Works post-generation (model-agnostic). Profiles are shareable, versioned, inspectable. A voice profile works with Claude, GPT, Copilot, or custom models

### Vs. Custom GPTs / Fine-Tuning
- **Limitation**: Expensive, slow, model-dependent, creates vendor lock-in
- **Voice advantage**: Lightweight, instant, works with any model, portable across tools and platforms

### Vs. Style Guides + Manual Enforcement
- **Limitation**: Teams write 50-page style guides that get ignored. Expensive to enforce through code review
- **Voice advantage**: Style guides become executable, composable code. Enforcement is instant and objective

### Vs. Grammarly, Hemingway, etc.
- **Limitation**: These tools optimize for readability, correctness, or formality—not for preserving authentic voice
- **Voice advantage**: Focuses on voice authenticity and AI slop removal. Doesn't prescribe "better writing"; lets users define their own standard

### Unique Value:
Voice is the only tool that directly solves "my AI output doesn't sound like me." It's purpose-built for a gap that emerges only in the post-LLM era.

---

## 5. Distribution Model

### Tier 1: Open Source CLI (Foundation)
- **What**: CLI tool that takes text + voice profile.json, outputs transformed text
- **Why**: Builds trust, enables developer adoption, creates network effects as profiles proliferate
- **License**: MIT or Apache 2.0
- **Hosting**: GitHub
- **Target audience**: Developers, early adopters, self-sufficient users

### Tier 2: Freemium Cloud + Profile Management (Monetization)
- **Free tier**: Upload/test profiles, transform up to 10k words/month
- **Paid ($9-29/month)**: Unlimited transformation, advanced profile analytics, version history, team sharing
- **Target**: Individual content creators, small teams
- **Revenue model**: Simple, transparent, usage-based optionality

### Tier 3: Marketplace (Network Effects)
- **What**: GitHub-like repository of shared voice profiles ("Voice Profiles" by domain, industry, persona)
- **Mechanics**: Users upload profiles, others fork/remix/rate. Top profiles bubble up
- **Revenue**: Promoted/premium profiles (optional; free baseline exists)
- **Target**: Teams discovering best practices; individuals finding profiles they resonate with

### Tier 4: Enterprise (Future)
- **What**: Self-hosted Voice runtime + team management console
- **Features**: SAML/SSO integration, audit logs, profile governance, on-premise processing
- **Pricing**: $5k-50k/year + implementation
- **Target**: Enterprises with sensitive content (healthcare, legal, finance) or regulatory requirements

### Strategy:
Start with **CLI + cloud freemium** (Tier 1+2). Marketplace emerges organically as users share profiles. Enterprise tier becomes viable once a strong community exists.

---

## 6. MVP Scope

### Minimum Viable Product: Slop Filter + Voice Application
Ship a focused product that proves the core concept: transform generic AI text into personalized output.

**Core Features:**
1. **AI Slop Detection Module**
   - Pattern-based detection of common AI markers:
     - Em dashes, hedging phrases ("It is important to note that"), repetitive transitions
     - Passive voice clustering, superlatives, hollow corporate jargon
     - Formulaic openings/closings ("In this guide, we explore...")
   - Output: JSON report listing flagged phrases and suggestions
   - No ML/ML required initially; pure regex/pattern matching

2. **Voice Profile Format**
   - JSON schema defining:
     - Forbidden patterns (things your voice never says)
     - Preferred patterns (things your voice favors)
     - Vocabulary constraints (jargon whitelist/blacklist)
     - Tone indicators (formal, casual, technical, etc.)
     - Sentence structure preferences (avg length, subordination patterns)
   - Human-readable, git-friendly, composable (profiles can inherit from other profiles)

3. **Transformation Engine**
   - Takes flagged text + voice profile
   - Applies replacements/rewrites using profile rules
   - Falls back to LLM micro-service for context-aware rewrites (optional, paid tier)
   - Output: cleaned text ready for human review

4. **CLI Tool**
   - `voice init` — Create voice profile from sample writing
   - `voice detect [file]` — Scan for AI slop
   - `voice apply [file] [profile]` — Transform text using profile
   - `voice profiles list` — Show available/installed profiles
   - JSON in/out for integration with other tools

5. **Simple Web UI** (optional for MVP, but valuable)
   - Paste text → see slop detection with inline highlights
   - Paste voice profile → apply to sample text
   - Download results (text + JSON report)

**MVP Non-Scope:**
- LLM-powered rewrites (Tier 2+)
- Profile learning from samples (Tier 2+)
- Marketplace (Tier 3)
- Team/collaboration features
- IDE plugins
- Advanced analytics

**MVP Success Criteria:**
- Developers can build voice profiles in 15 minutes
- Slop detection catches 70%+ of recognizable AI patterns
- Transformation produces readable output without requiring fallback LLM
- Users report: "I got AI help without sounding like an AI"

---

## 7. Growth Vectors

### Near-term (0-3 months post-MVP)
1. **Community Profiles**
   - Users share profiles on GitHub. "Best for technical writing," "startup voice," "academic," "conversational"
   - Top profiles get pinned/featured; network effects compound
   - Low friction: profiles are just JSON; no vendor dependency

2. **Integrations (Partnerships)**
   - VS Code extension: lint AI-generated comments
   - GitHub Actions: scan generated docs for slop on PR
   - Slack bot: apply voice profiles to AI-drafted messages
   - Writing tools (Obsidian, Notion, etc.): native Voice support
   - Goal: make Voice the "linter for AI writing"

3. **Usage Growth**
   - Content creators (Twitter, Substack, blogs) discovering Voice through dev communities
   - Advocates shipping profiles for their own voice
   - Word-of-mouth: "this made my AI output sound like me"

### Mid-term (3-12 months)
4. **Marketplace + Reputation**
   - Profiles become discoverable, rated, forked
   - Users trust community profiles; adoption accelerates
   - Premium profiles (with LLM-assisted rewrites) generate revenue

5. **Voice Profile Learning**
   - Analyze user writing samples → auto-generate initial voice profile
   - Users tweak; model improves
   - AI-assisted profile generation (not available in MVP)

6. **Team/Enterprise Adoption**
   - Teams want shared brand voice profiles
   - Managers use Voice to enforce style without micromanaging
   - Enterprise tier becomes relevant

### Long-term (12+ months)
7. **Ecosystem Play**
   - Voice profiles become a currency: teams share/sell profiles as IP
   - "Certified Voice Profiles" (for brands, publications, industries)
   - Voice as a service: Teams offer Voice consulting to implement brand profiles

8. **Vertical-Specific Profiles**
   - Healthcare: profiles that enforce medical writing standards
   - Legal: profiles for contract language, briefs, terms
   - Marketing: profiles capturing brand voice across global teams
   - Each vertical is a TAM expansion

9. **Network Effects**
   - As community grows, profile diversity increases
   - Discovery becomes harder; curation becomes valuable
   - Marketplace becomes destination for "finding your voice"

10. **Monetization Scaling**
    - Usage-based cloud (pay for transformations)
    - Premium profiles (creators charge for specialized profiles)
    - Enterprise licenses (on-premise, team management)
    - Consulting/implementation services

### Key Assumption to Validate:
Is the desire to "sound like myself in AI-assisted writing" strong enough to generate adoption and network effects?

**Validation approach**:
- Ship MVP, get 1000 developers to try Voice
- Measure: % who create profiles, % who re-use profiles, NPS
- Target: 30%+ retention after 30 days, 50%+ NPS
- If validation succeeds, community + marketplace become viable

---

## Summary: What Voice Becomes

**Phase 1 (MVP)**: Voice is a CLI tool that removes AI slop and applies personal voice profiles. Target: developers, content creators. Revenue: free with optional cloud tier.

**Phase 2 (Growth)**: Voice is the standard for portable voice profiles. Community discovers, shares, and refines profiles. Marketplace emerges. Vertical-specific profiles grow. Revenue: Freemium SaaS + premium profiles.

**Phase 3 (Scale)**: Voice is the infrastructure layer for authenticated AI writing. Teams, enterprises, and publications rely on Voice profiles for consistency and compliance. Ecosystem of integrations (IDEs, writing tools, CI/CD) makes Voice invisible but essential. Revenue: Enterprise + SaaS + consulting.

---

## Open Questions for Next Phase

1. **Voice Profile Format**: Should profiles be JSON? YAML? Code? (Recommend: JSON for simplicity, but extensible to code later)
2. **LLM Dependency**: Is pattern-matching slop detection sufficient, or do we need an LLM in the loop? (MVP: no LLM. Tier 2: optional LLM for context-aware rewrites)
3. **Learning**: How do we help users discover and articulate their voice? Auto-generation from samples or manual profile building? (MVP: manual. Tier 2: auto-generation)
4. **Distribution**: Do we lead with CLI or web UI? (Recommend: CLI first for credibility with developers, add web UI for accessibility)
5. **Monetization Timing**: Free-only launch or freemium from day 1? (Recommend: free only. Freemium after validation and usage growth)
