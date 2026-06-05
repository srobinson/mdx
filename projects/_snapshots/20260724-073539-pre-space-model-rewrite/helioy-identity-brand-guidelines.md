---
title: "Helioy Brand Guidelines"
category: projects
tags: [helioy, identity, brand, guidelines, master]
created: 2026-03-15
author: brand-guardian
status: master-document
version: 1.1
---

# Helioy Brand Guidelines

This is the master brand document. All brand decisions are tested against it. When in doubt, return to the brand essence.

---

## 1. Brand Overview

### Brand Essence

**Helioy crystallizes intelligence so nothing gets wasted.**

### Positioning

For developers building AI agent systems who lose context, repeat work, and burn tokens on structural overhead, Helioy is the infrastructure layer that gives agents persistent memory, structural awareness, and coordinated communication. Unlike generic agent frameworks that treat every interaction as disposable, Helioy crystallizes intelligence so it compounds over time.

### Brand Attributes

| Attribute | Definition |
|-----------|-----------|
| **Accumulative** | Intelligence compounds. Every interaction deposits value that future interactions withdraw. |
| **Precise** | The right context, the right moment, the right cost. Measurable, not vague. |
| **Structural** | Shape over text. Geometric memory, code topology, document architecture. |
| **Adaptive** | Living systems. Choreography over orchestration. Emergent behavior from simple rules. |
| **Crafted** | Handwork from HumanWork. A maker behind every component. Visible intention at every scale. |

### Brand Personality

A senior engineer with 20 years of building systems and undiminished curiosity. Minimal workspace, intentional process. Generous with knowledge, allergic to waste. Warm but not performative. Direct but not harsh. Quiet humor that emerges from competence: observations, not jokes.

The test: if you removed all playful elements, would the product still feel like it was made with care? If yes, the personality is doing its job.

### Central Metaphor: Crystallization

Raw experience compresses into structured, durable knowledge. Crystals form through accumulation. Each molecule joins in a position determined by what came before. The metaphor governs visual language and design decisions. It does not appear in product copy as a literal reference. See the Brand Narrative document for the three-act framework (Waste, Crystallization, Choreography) and the four-level intensity guide.

*Full detail: `helioy-identity-brand-narrative.md`, Sections 1-2, 4*

---

## 2. Logo

### The Facet Mark

An asymmetric crystalline shard viewed from three-quarter angle. Five vertices forming an irregular pentagon with one internal division, creating two visible facets. Not a complete crystal. A fragment implying a larger whole.

**Construction:** Regular pentagon in 96x96px box, rotated 12 degrees clockwise, bottom-left vertex removed, internal line from top vertex to 60% along bottom edge creates two facets (40/60 split). Facets differentiated by fill only, no stroke.

**Fills:**

| Context | Light Facet | Shadow Facet |
|---------|------------|--------------|
| Dark surfaces (primary) | `gold-500` (#d4a54a) | `gold-600` (#b8912e) |
| Light surfaces | `gold-600` (#b8912e) | `gold-700` (#8a6e1a) |
| Monochrome | 100% foreground | 70% foreground opacity |

### Size Behavior

| Size | Rendering |
|------|-----------|
| 16px (favicon) | Single gold fill silhouette. No internal division. |
| 32px (avatar) | Two facets by color, no internal line. |
| 48px (navigation) | Full two-facet rendering. |
| 64px (feature) | Full rendering, optional 1px hairline division in `gold-700`. |
| 96px+ (hero) | Full rendering, optional internal lattice texture at 20% opacity. |

### Wordmark

**Typeface:** General Sans Semibold (600)
**Case:** Mixed ("Helioy")
**Tracking:** +160 units (CSS: `letter-spacing: 0.16em`)
**Color:** Always the text color of its surface (`text-primary` on dark, `text-primary-light` on light). The wordmark is never rendered in gold. Gold is reserved for the Facet mark.

### Lockups

| Configuration | Spec | Min Size |
|--------------|------|----------|
| **Horizontal (primary)** | Mark left of wordmark. Mark vertical center aligns to wordmark x-height center. Gap equals mark width. | 120px wide |
| **Stacked** | Mark centered above wordmark. Gap is 50% of mark height. | 80px tall |
| **Mark only** | The Facet alone. For sizes below 120px or established brand contexts. | 16px |
| **Wordmark only** | Text-heavy contexts (doc headers, footer credits). | n/a |

### Clear Space

Minimum 25% of mark width on all sides.

### Misuse

- Do not rotate beyond designed orientation
- Do not add drop shadow or glow
- Do not place on busy photographic backgrounds without solid backing
- Do not animate the mark's geometry (only opacity and color may transition)
- Do not apply gradients to the facets

*Full detail: `helioy-identity-visual-system.md`, Sections 1-2*

---

## 3. Color

### Brand Gold

| Token | Hex | Usage |
|-------|-----|-------|
| `gold-400` | #e0b960 | Hover state, light emphasis. Use sparingly. |
| `gold-500` | #d4a54a | **Primary accent.** Interactive elements, active states, Facet light face. 5.8:1 on surface-0. |
| `gold-600` | #b8912e | Pressed states, secondary accent, Facet shadow face. |
| `gold-700` | #8a6e1a | **Interactive gold in light mode.** Decorative borders/lattice only on dark. Never for text on dark surfaces. |
| `gold-900` | #3d3010 | Tinted background wash. Never for text. |

**Usage ratio:** Gold on no more than 15% of any screen surface area.

### Surfaces

**Dark mode (primary):**

| Token | Hex | Role |
|-------|-----|------|
| `surface-0` | #1a1816 | Page background |
| `surface-1` | #222018 | Cards, panels, sidebar |
| `surface-2` | #2e2b24 | Elevated panels, popovers |
| `surface-3` | #3a3730 | Active/selected rows |

**Light mode:**

| Token | Hex | Role |
|-------|-----|------|
| `surface-0-light` | #faf8f5 | Page background (warm paper) |
| `surface-1-light` | #f0ece6 | Cards, panels |
| `surface-2-light` | #e6e2dc | Elevated panels |
| `surface-3-light` | #dcd8d2 | Active/selected |

### Text

| Token | Hex | Mode | Contrast on surface-0 |
|-------|-----|------|-----------------------|
| `text-primary` | #f0ebe4 | Dark | 11.2:1 (AAA) |
| `text-secondary` | #9a9590 | Dark | 5.1:1 (AA) |
| `text-tertiary` | #6a6560 | Dark | 3.2:1 (large only) |
| `text-primary-light` | #1a1816 | Light | 14.5:1 (AAA) |
| `text-secondary-light` | #5a5550 | Light | 5.8:1 (AA) |
| `text-tertiary-light` | #8a8580 | Light | 3.5:1 (large only) |

### Semantic Colors

| Token | Dark | Light | Purpose |
|-------|------|-------|---------|
| `signal-success` | #6b9b7a | #2d7a46 | Connected, passing |
| `signal-warning` | #d4a54a | #7a5f14 | Attention needed (reuses gold in dark; darkened for light mode contrast) |
| `signal-error` | #d45a5a | #a83232 | Failed, error |
| `signal-info` | #5b8db8 | #3a6e96 | Informational |

All semantic colors are muted and warm-shifted. No saturated primaries.

### Borders

| Token | Dark | Light | Usage |
|-------|------|-------|-------|
| `border-subtle` | #3a3730 | #dcd8d2 | Decorative/supplementary hairlines |
| `border-default` | #4a4740 | #c8c4be | Standard component borders |
| `border-interactive` | #5a5750 | #a8a49e | **Form inputs, checkboxes, toggles.** Any border serving as the sole component boundary indicator. 3:1+ on surfaces. |

### Color Bridge Rule

Gold is constant across modes but shifts role. In dark mode, `gold-500` is the interactive accent. In light mode, `gold-700` serves this role (4.58:1 on surface-0-light, passing AA). Focus rings use `text-primary-light` (#1a1816) in light mode for guaranteed visibility (16.70:1).

### Prohibited

Pure black (#000), pure white (#fff), saturated primaries, cool blues/teals as accents, neon, gradient fills on interactive elements, gold on surfaces larger than 15% of viewport.

*Full detail: `helioy-identity-design-system-foundations.md`, Section 3*

---

## 4. Typography

### Font Families

| Role | Font | Stack |
|------|------|-------|
| **UI / Body / Marketing / Wordmark** | General Sans | `"General Sans", "Noto Sans", "Noto Sans CJK", system-ui, sans-serif` |
| **Code / CLI / Data** | JetBrains Mono | `"JetBrains Mono", "Noto Sans Mono", ui-monospace, monospace` |

No serif typefaces. Anywhere.

### Type Scale

Base: 16px (1rem). Ratio: 1.25 (Major Third).

| Token | Size | Weight | Line Height | Usage |
|-------|------|--------|-------------|-------|
| `text-xs` | 12px | 400 | 1.5 | Badges, annotations |
| `text-sm` | 14px | 400 | 1.5 | Labels, captions, secondary UI |
| `text-base` | 16px | 400 | 1.6 | Body text, form inputs |
| `text-lg` | 20px | 500 | 1.5 | Subheadings |
| `text-xl` | 24px | 600 | 1.3 | H3 headings |
| `text-2xl` | 30px | 600 | 1.25 | H2 headings |
| `text-3xl` | 38px | 700 | 1.2 | H1 page titles |
| `text-4xl` | 48px | 700 | 1.1 | Hero headings |

### Rules

- Minimum body text: 16px
- Maximum line length: 72 characters (body), 90 characters (docs)
- Negative tracking (-0.02em) at `text-2xl` and above only
- Wordmark tracking (+0.16em) is exclusive to the wordmark
- Paragraph spacing: 16px. Heading spacing: 24px above, 12px below.

*Full detail: `helioy-identity-design-system-foundations.md`, Section 4; `helioy-identity-visual-system.md`, Section 4*

---

## 5. Voice and Tone

### Five Principles

**Say less, mean more.** Every word earns its place.
- *This:* "Agents remember. Tokens drop. Work compounds."
- *Not this:* "Our revolutionary AI-powered platform enables your intelligent agents to leverage persistent memory solutions."

**Show the mechanism.** How things work, not just that they work.
- *This:* "Context-matters stores experience as geometric shapes. Retrieval searches by resonance, not keywords."
- *Not this:* "Our advanced memory system uses cutting-edge technology to supercharge your AI agents."

**Respect the reader's time.** Value proposition before explanation.
- *This:* "fmm answers structural questions in O(1). Here's how."
- *Not this:* "In today's complex software landscape, understanding code structure is more important than ever..."

**Be specific, never vague.** Numbers over adjectives.
- *This:* "5 fmm calls replace 30+ file reads."
- *Not this:* "Dramatically improve your development workflow."

**Warm authority.** Knowledgeable without condescending. Occasionally wry, never performative.
- *This:* "This function remembers so you don't have to."
- *Not this:* "Say goodbye to forgetting forever with our amazing memory tool!"

### Tone by Context

| Context | Register | Example |
|---------|----------|---------|
| **Website hero** | Terse, high-impact | "Agents that remember. Every token counts." |
| **Documentation** | Technical precision, no marketing language | "Prerequisites: Node.js 18+, an MCP-compatible client, 10 minutes." |
| **Error messages** | Honest, actionable, no apology | "Context not found. Run `cx_stats` to check." |
| **Changelog** | Specific, measurable, migration path for breaking changes | "Token cost for recall dropped 40% through smarter scope pruning." |
| **Social** | Specific pain + specific solution | "Your AI rebuilt your project context 47 times this week. Mine remembered it from Monday." |
| **Empty states** | State the fact, provide next action, quiet encouragement | "No context stored yet. Stores grow more useful over time. Start small." |

*Full detail: `helioy-identity-brand-narrative.md`, Section 5*

---

## 6. Visual Language

### Structured Light Patterns

Caustic light patterns serve as the brand's repeatable graphic element: interference patterns created when light refracts through crystalline geometry. Generated algorithmically (simulated refraction or Perlin noise through Voronoi boundaries), not illustrated.

**Color treatment:**
- Primary: `gold-500` at 8-15% opacity on `surface-0` for backgrounds, 30-50% for featured areas
- Secondary: `gold-700` on `surface-1` for subtle surface treatment
- Light mode: `gold-600` at 5-10% opacity on `surface-0-light`

**Where patterns appear:** Website hero backgrounds, social cards, conference slides, loading states, email headers.
**Where patterns do not appear:** Product UI surfaces, documentation pages, inside the Facet mark, CLI output, surfaces smaller than 200x200px.

**Animation:** Light source drift at 30-60 second cycle, linear easing. Respects `prefers-reduced-motion` (static at median opacity).

### Brand Art: Structural Diagrams

The product's actual data structures rendered as visualizations. Gold highlights on active nodes, `text-secondary` for connected nodes, `text-tertiary` for context. Edges are 1px curved lines. Diagrams extend past frame edges, implying continuation. Center-weighted composition against dark negative space.

### Photography Direction

Material close-ups (crystals, amber, geological specimens), architectural interiors with directional warm light, real workspaces. Color graded to the warm mineral palette. No stock photography, no staged desks, no AI-generated people, no illustration.

### Data Visualization

Gold for primary series. No pie charts. No 3D effects. No gradients on chart elements. Flat fills, clean lines.

### Syntax Highlighting

| Element | Token |
|---------|-------|
| Keywords | `gold-500` |
| Strings | `signal-success` |
| Comments | `text-tertiary` |
| Functions | `signal-info` |
| Variables | `text-primary` |
| Numbers | `gold-400` |

*Full detail: `helioy-identity-visual-system.md`, Sections 6-7; `helioy-identity-mood-board.md`*

---

## 7. Design System Summary

### Spacing

4px base unit. Scale: 4, 8, 12, 16, 24, 32, 48, 64, 96px.

| Token | Value | Primary Usage |
|-------|-------|---------------|
| `space-1` | 4px | Inline gaps, icon-label spacing |
| `space-2` | 8px | Tight component padding |
| `space-3` | 12px | Standard component padding |
| `space-4` | 16px | Section padding, card padding |
| `space-6` | 24px | Component group spacing |
| `space-8` | 32px | Major section gaps |
| `space-12` | 48px | Page section separation |
| `space-16` | 64px | Hero vertical rhythm |

### Grid

12-column grid, 24px gap. Asymmetric defaults: 3/9 sidebar, 4/8 settings, 5/7 content, 8 centered for reading. Mobile-first responsive breakpoints at 480, 768, 1024, 1280px.

### Surface Elevation

Expressed through background warmth shift, not shadow. Each level uses the next `surface-N` token. Shadows reserved for floating elements only (popovers: `0 4px 16px rgba(0,0,0,0.3)`, modals: `0 8px 32px rgba(0,0,0,0.4)`).

### Motion

| Parameter | Value |
|-----------|-------|
| Easing | `cubic-bezier(0.16, 1, 0.3, 1)` (sharp attack, long settle) |
| Duration | 120ms (fast), 200ms (normal), 400ms (slow) |
| Stagger | 0ms, 60ms, 100ms, 120ms (decreasing increments) |
| Reduced motion | All transitions instant (0ms). Opacity at 150ms max. |

No bounce. No overshoot. No animation slower than 400ms unless page-level transition.

### Icons

Geometric solid with negative space cuts. Fill-and-cut only, no outlines. Four sizes: 16, 20, 24, 32px. Default color `text-secondary`, active `gold-500`, hover `text-primary`. Every navigation icon requires a visible text label.

### Border Radius

`radius-sm` (3px) for inline code, badges. `radius-md` (6px) for buttons, cards, inputs. `radius-lg` (12px) for modals, large containers.

*Full detail: `helioy-identity-design-system-foundations.md`, Sections 2, 5-7; `helioy-identity-visual-system.md`, Section 5*

---

## 8. Accessibility

A post-production audit identified five corrective fixes. All have been applied to the color values in this document.

### Corrective Fixes Applied (v1.1)

| Fix | Issue | Resolution |
|-----|-------|------------|
| **C1** | gold-500 invisible in light mode (2.13:1) | Light mode interactive gold uses `gold-700` (#8a6e1a, 4.58:1 on surface-0-light) |
| **C2** | Focus ring invisible in light mode | Light mode focus ring uses `text-primary-light` (#1a1816, 16.70:1) |
| **C3** | signal-error failed AA in dark mode (3.85:1) | Lightened from #c94a4a to `#d45a5a` (4.5:1+ on surface-0) |
| **C4** | signal-warning invisible in light mode | Darkened light value from #b8912e to `#7a5f14` (4.5:1+ on surface-0-light) |
| **C5** | All border tokens failed 3:1 for UI components | New `border-interactive` token (#5a5750 dark, #a8a49e light) for form controls |

### Standing Requirements

- **Contrast floors:** Body text 4.5:1 AA minimum (7:1 AAA target). Large text 3:1. UI components 3:1.
- **Color independence:** Never rely on color alone to convey state. Shape/pattern differentiation required for icons and data visualizations.
- **Text-tertiary restriction:** `text-tertiary` permitted only on `surface-0`. On elevated surfaces, use `text-secondary` for disabled states.
- **text-xs restriction:** `text-xs` (12px) for badges and labels only. Any content requiring comprehension uses `text-sm` (14px) minimum.
- **Motion:** All motion (CSS, JS, SVG, video autoplay) must respect `prefers-reduced-motion`. No exceptions. No strobing or rapid flashing at any preference level.
- **Data visualization:** All chart types must use shape or pattern differentiation in addition to color. Solid, dashed, dotted for lines. Solid, hatched, stippled for bars. Direct labels on series, not legend-only.
- **High-contrast mode:** Available via `[data-theme="high-contrast"]`. 10:1 text contrast, visible borders, 3px focus rings.

*Full detail: `helioy-identity-accessibility-audit.md`*

---

## 9. Personality and Micro-Interactions

Personality is a byproduct of craft. It emerges from how things are built, not from what is added afterward.

### Five Personality Principles

1. **Personality is a byproduct of craft.** A well-structured error message has more character than a witty loading screen. If a playful element could be removed and the product would feel worse, it has earned its place. If the product would feel the same, it is decoration.

2. **Discovery over announcement.** The best personality details are found, not shown. Reward sustained attention, not first impressions.

3. **Information is the personality.** Showing a user their token savings is more delightful than a celebratory animation. The product's capability is the personality.

4. **Variation without randomness.** Output varies slightly to feel alive. "Done. 4 files indexed." vs. "Indexed 4 files in 0.3s." Same information, different cadence. Variation follows rules, not a random number generator.

5. **Warmth has a budget.** No more than one personality moment per interaction. Gold accent rules apply: present but never dominant.

### CLI Voice

The CLI is the primary personality surface. Key patterns:

- **Status output:** Terse, factual. Growth deltas in parentheses when notable. Always terminates with "ready."
- **Success messages:** Start lowercase. One sentence maximum. Metrics in parentheses.
- **Error messages:** Three components in order: what happened, why it probably happened, what to do. Never "Oops" or any interjection. Always end with an actionable command.
- **Loading states:** Minimal cycling dot animation. Loading verb matches operation ("searching", "indexing", "connecting"). Duration shown only when >2 seconds.
- **Help text:** Opening line is a lowercase sentence fragment describing the mechanism. Realistic examples, not `foo` and `bar`.
- **Geometric fingerprints:** Unicode shapes (`◇ △ ○ ▽ ◁ ▷ □ ⬡`) after context storage indicate geometric cluster assignment. Undocumented. Rewards attention.

### Web Micro-Interactions

- **Page load:** Staggered formation sequence with decreasing delay increments. Elements "find position" faster as the page takes shape.
- **Code block warmup:** Syntax highlighting transitions from monochrome to full brand palette on scroll intersection (marketing site only, not docs).
- **Hover states:** Warm glow via box-shadow, not underline. CTA buttons: lighter on hover (energy gathering), darker on press (energy released).
- **Copy button:** "Copy" to "Copied" to "Remembered" (1.5s delay). The only wordplay in the documentation UI.
- **Empty states:** No illustrations, no sad-face icons. State the fact, provide the action, optionally one line of factual encouragement.

### Easter Eggs

Five discoverable details. Each rewards attention without demanding it:

1. **`--about` flag:** Hidden on all CLI tools. Returns a one-sentence reason the tool exists.
2. **Geometric fingerprints:** Cluster shapes after context storage. Pattern becomes self-evident through use.
3. **Anniversary milestone:** On the store's exact birthday, a one-time status line shows the user's first-ever deposit.
4. **Efficiency marker:** One-time note when cumulative token savings cross round thresholds (100K, 1M, 10M).
5. **Version codenames:** Mineral/geological terms in verbose version output. Alphabetical progression. Never announced.

### Personality Anti-Patterns

Prohibited: performative errors ("Oops!"), eager greetings ("Welcome back!"), loading screen jokes, celebration cascades (confetti, achievements), anthropomorphized tools ("I noticed..."), forced personality moments ("We hope you love it!").

*Full detail: `helioy-identity-personality-spec.md`*

---

## 10. Brand Guardrails

These are non-negotiable across all touchpoints, all audiences, all scales.

### Technical accuracy above all
Every claim must be verifiable. The brand's credibility depends on the code being as good as the copy.

### The tagline is a constraint
"Every token counts" governs internal behavior as much as external messaging. If a feature wastes tokens, it violates the brand. If documentation is bloated, it violates the brand. The tagline is an operational principle.

### No anthropomorphization of AI
The tools process, store, retrieve, coordinate. They do not "think," "feel," or "understand." Precision in language protects the brand from the hype cycle.

### Maker identity stays visible
The brand must feel like something a person built with intention. Not generated. Not corporate. Stuart's fingerprints detectable in the craft at every scale.

### Voice does not change with audience
From vibe coders to enterprise, the character stays the same. Depth of documentation increases. Surface area expands. The precision and respect for the reader are fixed.

### Accessibility is structural
WCAG 2.2 AA minimum across all color combinations. Never rely on color alone for information. Minimum 16px body text. `prefers-reduced-motion` compliance mandatory. High-contrast mode variant available.

### Protect the naming convention
Lowercase. Descriptive. Human. Product names feel like tools a person named (context-matters, fmm, nancy, helioy-bus), not products a committee branded.

### No visual trend-chasing
No gradient meshes, glassmorphism, neon-on-dark, AI sparkle effects. The identity is built from product philosophy. It ages with the product, not against it.

### Anti-patterns summary

| Category | Prohibited |
|----------|-----------|
| Color | Pure black/white, saturated primaries, cool accents, neon, polished metallic gold |
| Typography | Serif typefaces, body text below 16px, lines longer than 72 characters |
| Imagery | Stock photography, AI-generated people, illustration/character art, "hero developer" compositions |
| Copy | "Revolutionary," "AI-powered," "cutting-edge," "leverage," AI anthropomorphization, exclamation marks in product voice |
| Visual | Gradient fills on UI elements, drop shadows on the logo, pie charts, icon-only navigation, bounce/overshoot animations |
| Territory | "AI platform," "autonomous agents," "enterprise AI," "no-code/low-code" |

---

## Source Documents

This guidelines document synthesizes and references these detailed specifications:

| Document | Content | Author |
|----------|---------|--------|
| `helioy-identity-brand-strategy.md` | Brand essence, positioning, attributes, personality, voice, metaphor, guardrails | Brand Guardian |
| `helioy-identity-design-system-foundations.md` | Spacing, color tokens, type scale, grid, accessibility, touchpoints, CSS variables | UX Architect |
| `helioy-identity-visual-system.md` | Logo spec, wordmark, color application, icons, patterns, brand art, application examples, full CSS | UI Designer |
| `helioy-identity-brand-narrative.md` | Origin story, three-act framework, visual language principles, metaphor usage guide, tone examples | Visual Storyteller |
| `helioy-identity-mood-board.md` | Image generation prompts, style lock, material studies, atmospheric references, abstraction guide | Image Prompt Engineer |
| `helioy-identity-accessibility-audit.md` | WCAG contrast audit, corrective fixes, color blindness assessment, motion accessibility | Inclusive Visuals Specialist |
| `helioy-identity-personality-spec.md` | Personality principles, CLI voice patterns, web micro-interactions, Easter eggs, anti-patterns | Whimsy Injector |

For implementation: start with the CSS custom properties in `helioy-identity-visual-system.md`, Section 9. Apply the corrective color fixes from the accessibility audit (Section 8 of this document) to those values.

---

## Changelog

**v1.1 (2026-03-15):** Incorporated accessibility audit fixes (corrected signal-error dark, signal-warning light, gold-700 as light mode interactive gold, border-interactive token, focus ring light mode). Added Accessibility section (8). Added Personality and Micro-Interactions section (9). Added mood board, accessibility audit, and personality spec to source documents. Renumbered Brand Guardrails to section 10.

**v1.0 (2026-03-15):** Initial master document consolidating Phases 0-2.

---

*Helioy Brand Guidelines v1.1. 2026-03-15.*
*Brand Guardian: consolidated from 8-agent design team output across Phases 0-3.*
*Source of truth for all brand decisions.*
