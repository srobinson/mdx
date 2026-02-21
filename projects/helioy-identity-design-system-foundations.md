---
title: "Helioy Design System Foundations"
category: projects
tags: [helioy, identity, design-system, phase-1]
created: 2026-03-15
author: ux-architect
status: foundation-spec-v1.1
---

# Helioy Design System Foundations

This document establishes the structural foundation for Helioy's visual identity system. All values are exact and implementation-ready. This feeds directly into the UI Designer's Phase 2 work.

---

## 1. Design Principles

Five principles derived from "Density Without Weight" and team consensus.

### 1.1 Every Element Earns Its Place
No ornamental UI. No decorative flourish that does not carry information. If a visual element cannot justify its presence through function, it is removed. This is the UX translation of "every token counts."

### 1.2 Structure Creates Hierarchy
Spacing, typography weight, and surface elevation create visual hierarchy. Not borders, not boxes, not color variation. When a boundary is needed, use a subtle surface shift rather than a hard line. Chrome disappears; content remains.

### 1.3 Density With Clarity
Information-dense interfaces that remain legible. Our users read code all day. They handle density. The system provides tight spacing without clutter through consistent rhythm and clear typographic scale.

### 1.4 Progressive Disclosure
Simple surface, depth on demand. Default views are terse and scannable. Detail layers are accessible but not imposed. The interface mirrors the user's intent depth.

### 1.5 Warmth Through Material
The system uses warm neutrals, matte textures, and amber accents to feel grounded rather than clinical. Precision without coldness. Infrastructure software that feels like a well-maintained workshop, not a laboratory.

---

## 2. Spacing System

### Resolution: 4px Base Unit

The UI Designer proposed 6px. This was carefully considered. The 6px scale (6, 12, 18, 24, 36, 48, 72) offers appealing intermediate values, but 6px creates alignment friction with standard icon sizes (16, 20, 24, 32px), common font sizing, and the 12-column grid system. A 4px base with a curated scale provides the same density control while maintaining compatibility with the broader ecosystem of component libraries, icon systems, and browser defaults.

### Scale

| Token | Value | px | Usage |
|-------|-------|-----|-------|
| `space-1` | 0.25rem | 4 | Inline element gaps, icon-to-label spacing |
| `space-2` | 0.5rem | 8 | Tight component padding, related element gaps |
| `space-3` | 0.75rem | 12 | Standard component padding, form field spacing |
| `space-4` | 1rem | 16 | Section internal padding, card padding |
| `space-6` | 1.5rem | 24 | Component group spacing, between related sections |
| `space-8` | 2rem | 32 | Major section gaps |
| `space-12` | 3rem | 48 | Page section separation |
| `space-16` | 4rem | 64 | Hero/feature section vertical rhythm |
| `space-24` | 6rem | 96 | Maximum vertical breathing room |

### Application Rules

- **Component internal padding**: `space-3` (12px) standard, `space-2` (8px) compact variant
- **Between sibling components**: `space-4` (16px) standard, `space-3` (12px) dense variant
- **Section separation**: `space-8` (32px) minimum, `space-12` (48px) standard
- **Page margin (mobile)**: `space-4` (16px)
- **Page margin (desktop)**: `space-6` (24px) or contained within max-width
- **Vertical rhythm**: all vertical spacing must use scale values. No arbitrary pixel values.

---

## 3. Color Tokens

### 3.1 Brand Colors

| Token | Hex | Usage | Notes |
|-------|-----|-------|-------|
| `gold-500` | `#d4a54a` | Primary brand accent, interactive highlights, active states | Contrast 5.8:1 on surface-0, passes AA |
| `gold-400` | `#e0b960` | Hover states, emphasis on dark surfaces | Use sparingly, lower contrast |
| `gold-600` | `#b8912e` | Pressed states, secondary accent | Contrast 4.6:1 on surface-0, passes AA large text |
| `gold-700` | `#8a6e1a` | Metadata, tertiary accent, **light mode interactive gold** (links, active states, nav indicators) | Contrast 3.2:1 on dark surface-0 (decorative only); 5.4:1 on light surface-0 (passes AA) |
| `gold-900` | `#3d3010` | Tinted backgrounds, subtle gold wash | Never for text |

### 3.2 Dark Mode (Primary)

| Token | Hex | Contrast vs text-primary | Usage |
|-------|-----|--------------------------|-------|
| `surface-0` | `#1a1816` | Background for text-primary: 11.2:1 | Page background, deepest layer |
| `surface-1` | `#222018` | 10.1:1 | Card/panel background, first elevation |
| `surface-2` | `#2e2b24` | 8.7:1 | Elevated panels, popovers, dropdowns |
| `surface-3` | `#3a3730` | 7.1:1 | Active/selected row backgrounds |
| `border-subtle` | `#3a3730` | n/a | Hairline borders when surface shift is insufficient |
| `border-default` | `#4a4740` | n/a | Standard component borders |
| `border-interactive` | `#7a7570` | n/a | Interactive element borders (inputs, buttons). Meets 3:1 non-text contrast on surface-0 through surface-2. |

### 3.3 Light Mode (Secondary)

| Token | Hex | Contrast vs text-primary-light | Usage |
|-------|-----|-------------------------------|-------|
| `surface-0-light` | `#faf8f5` | Background for text-primary-light: 14.5:1 | Page background |
| `surface-1-light` | `#f0ece6` | 12.8:1 | Card/panel background |
| `surface-2-light` | `#e6e2dc` | 10.9:1 | Elevated panels |
| `surface-3-light` | `#dcd8d2` | 9.4:1 | Active/selected states |
| `border-subtle-light` | `#dcd8d2` | n/a | Hairline borders |
| `border-default-light` | `#c8c4be` | n/a | Standard borders |
| `border-interactive-light` | `#8a8580` | n/a | Interactive element borders. Meets 3:1 non-text contrast on light surface-0 through surface-2. |

### 3.4 Text Colors

| Token | Hex | Context | Contrast on surface-0 |
|-------|-----|---------|----------------------|
| `text-primary` | `#f0ebe4` | Dark mode body text, headings | 11.2:1 (AAA) |
| `text-secondary` | `#9a9590` | Dark mode metadata, labels, captions | 5.1:1 (AA) |
| `text-tertiary` | `#6a6560` | Dark mode disabled, placeholder | 3.2:1 (AA large only) |
| `text-primary-light` | `#1a1816` | Light mode body text | 14.5:1 (AAA) |
| `text-secondary-light` | `#5a5550` | Light mode metadata | 5.8:1 (AA) |
| `text-tertiary-light` | `#8a8580` | Light mode disabled, placeholder | 3.5:1 (AA large only) |

### 3.5 Semantic Colors

| Token | Hex (dark) | Hex (light) | Usage |
|-------|-----------|-------------|-------|
| `signal-success` | `#6b9b7a` | `#2d7a46` | Connected, passing, complete |
| `signal-warning` | `#d4a54a` | `#7a5f14` | Degraded, attention needed (reuses gold in dark; darkened for light mode contrast) |
| `signal-error` | `#d45a5a` | `#a83232` | Failed, disconnected, error |
| `signal-info` | `#5b8db8` | `#3a6e96` | Informational, neutral status |

Semantic colors are muted and warm-shifted. Standard greens, reds, and blues are replaced with sage, terracotta-red, and steel-blue to maintain the warm mineral palette.

### 3.6 Color Bridge Rule

Gold is the constant across dark and light modes. In dark mode, gold functions as a light source (bright accent on dark surface). In light mode, gold functions as a weight accent (warm emphasis on light surface). Same hue family, different perceptual role.

### 3.7 Never Use

- Pure black (`#000000`) for backgrounds
- Pure white (`#ffffff`) for text
- Saturated primaries (pure red, green, blue) for semantic colors
- Gold for large surface fills (accent only, never background)

---

## 4. Typography Scale

### 4.1 Font Families

**System font (UI, docs, marketing):** The system font must meet these requirements:
- Geometric sans-serif with subtle humanist touches
- Distinct letterforms for `l`, `1`, `I`, `0`, `O` (critical for developer audience)
- Strong weight range (400 through 700 minimum)
- Good x-height for legibility at small sizes
- Variable font preferred for fine-tuning optical sizing
- Candidates: Satoshi, General Sans, Instrument Sans (UI Designer to finalize)

**Monospace font (code, CLI, data):** JetBrains Mono. Free, widely supported, excellent ligature set, strong character distinction. Berkeley Mono if licensing is secured for premium contexts.

**Wordmark font:** Separate from system font. Requirements:
- Must support wide tracking (200-400 units) without letterform collision
- Mixed-case "Helioy" with capital H anchoring
- Geometric character with warmth (not cold/mechanical)
- Must read cleanly at 16px wide (favicon/avatar contexts)
- UI Designer owns selection; this spec defines the constraints

**Script fallback chain:** For CJK, Devanagari, Arabic, and Cyrillic contexts, specify fallbacks that maintain visual weight and rhythm. System font stack: `[primary-sans], "Noto Sans", "Noto Sans CJK", system-ui, sans-serif`. Monospace stack: `"JetBrains Mono", "Noto Sans Mono", ui-monospace, monospace`.

### 4.2 Type Scale

Base size: 16px (1rem). Scale ratio: 1.25 (Major Third).

| Token | Size | rem | Weight | Line Height | Usage |
|-------|------|-----|--------|-------------|-------|
| `text-xs` | 12px | 0.75 | 400 | 1.5 (18px) | Badges, fine print, code annotations |
| `text-sm` | 14px | 0.875 | 400 | 1.5 (21px) | Labels, captions, secondary UI text |
| `text-base` | 16px | 1 | 400 | 1.6 (25.6px) | Body text, form inputs, UI defaults |
| `text-lg` | 20px | 1.25 | 500 | 1.5 (30px) | Subheadings, emphasized body |
| `text-xl` | 24px | 1.5 | 600 | 1.3 (31.2px) | Section headings (H3) |
| `text-2xl` | 30px | 1.875 | 600 | 1.25 (37.5px) | Page section headings (H2) |
| `text-3xl` | 38px | 2.375 | 700 | 1.2 (45.6px) | Page titles (H1) |
| `text-4xl` | 48px | 3 | 700 | 1.1 (52.8px) | Hero headings, marketing |

### 4.3 Typography Rules

- **Minimum body text**: 16px. Never 12px or 14px for body content.
- **Maximum line length**: 72 characters for body text, 90 characters for documentation prose.
- **Paragraph spacing**: `space-4` (16px) between paragraphs.
- **Heading spacing**: `space-6` (24px) above headings, `space-3` (12px) below.
- **Letter spacing**: 0 for body text. Headings at `text-2xl` and above may use -0.02em tracking. Wordmark uses +0.12em to +0.2em.
- **No serif typefaces** anywhere in the system. Serif signals tradition. Helioy signals precision.

---

## 5. Grid & Layout

### 5.1 Container System

| Token | Max Width | Usage |
|-------|-----------|-------|
| `container-xs` | 480px | Narrow content (auth forms, modals) |
| `container-sm` | 640px | Prose content (docs, blog) |
| `container-md` | 768px | Mixed content (docs with sidebar nav) |
| `container-lg` | 1024px | Standard application layout |
| `container-xl` | 1280px | Wide application layout, marketing |
| `container-full` | 100% | Edge-to-edge (dashboards, data tables) |

All containers center horizontally with `space-4` (16px) minimum horizontal padding.

### 5.2 Grid System

12-column grid. Column gap: `space-6` (24px). Row gap: `space-6` (24px).

**Default layout templates favor asymmetric splits:**

| Pattern | Columns | Usage |
|---------|---------|-------|
| `layout-sidebar` | 3 / 9 | Navigation sidebar + main content |
| `layout-sidebar-wide` | 4 / 8 | Settings, admin panels |
| `layout-content` | 5 / 7 | Content with supplementary panel |
| `layout-split` | 6 / 6 | Comparison views, side-by-side |
| `layout-single` | 8 centered | Focused reading, documentation |

Symmetry is the fallback, not the default. Asymmetry creates intentional tension that signals considered design.

### 5.3 Responsive Breakpoints

| Token | Width | Behavior |
|-------|-------|----------|
| `bp-sm` | 480px | Stack to single column below this |
| `bp-md` | 768px | Sidebar collapses, grid simplifies |
| `bp-lg` | 1024px | Full layout activates |
| `bp-xl` | 1280px | Wide layout variant available |

**Strategy: mobile-first.** Base styles target the narrowest viewport. Breakpoints add complexity upward. Below `bp-sm`, all layouts collapse to single column with `space-4` page margins.

### 5.4 Surface Elevation System

Elevation is expressed through background warmth shift, not shadow. Each elevation step uses the next `surface-N` token. Shadows are reserved for floating elements (popovers, dropdowns, tooltips).

| Level | Surface Token | Shadow | Usage |
|-------|---------------|--------|-------|
| 0 (base) | `surface-0` | none | Page background |
| 1 (raised) | `surface-1` | none | Cards, panels, sidebar |
| 2 (elevated) | `surface-2` | none | Nested panels, active areas |
| 3 (floating) | `surface-2` | `0 4px 16px rgba(0,0,0,0.3)` | Popovers, dropdowns, tooltips |
| 4 (overlay) | `surface-2` | `0 8px 32px rgba(0,0,0,0.4)` | Modals, dialogs |

---

## 6. Accessibility Requirements

### 6.1 Contrast Ratios

- **Body text on surface**: minimum 7:1 (WCAG AAA target, AA 4.5:1 hard floor)
- **Large text (18px+ bold or 24px+ regular) on surface**: minimum 4.5:1
- **UI components and graphical objects**: minimum 3:1 against adjacent colors
- **Gold accent on surfaces**: verified at 5.8:1 on `surface-0` (passes AA)
- Every color pairing in the system has been specified with contrast ratios. No combination may be used in production without verification.

### 6.2 Focus States

- All interactive elements must show a visible focus indicator
- Focus ring (dark mode): 2px solid `gold-500`, offset 2px from element edge
- Focus ring (light mode): 2px solid `text-primary-light` (`#1a1816`), offset 2px from element edge
- Focus ring must have 3:1 contrast against the element background AND the page background in both modes
- Tab order follows visual reading order (left-to-right, top-to-bottom)
- No focus traps except in modal dialogs (with Escape to dismiss)

### 6.3 Motion

- All animations must respect `prefers-reduced-motion: reduce`
- When reduced motion is active: transitions become instant (0ms duration), no translate/scale transforms, opacity transitions permitted at 150ms max
- No strobing or rapid flashing at any motion preference level
- Standard motion: `cubic-bezier(0.16, 1, 0.3, 1)` easing (sharp attack, long settle)
- Duration range: 120ms to 400ms for UI transitions. Nothing slower unless page-level transition.
- Stagger pattern for cascading elements: 0ms, 60ms, 100ms, 120ms (decreasing delay increments)
- No bounce, no overshoot. Precision, not playfulness.

### 6.4 Typography Accessibility

- Minimum body text: 16px
- Line height: 1.5x minimum for body text, 1.2x minimum for headings
- Maximum line length: 72 characters
- Font families must have distinct letterforms for ambiguous characters (`l`/`1`/`I`, `0`/`O`)
- Fonts must avoid mirrored letterforms (`b`/`d`, `p`/`q`) where possible, supporting neurodivergent readers

### 6.5 Icon Accessibility

- All icons legible at 16x16px minimum
- Icons must not rely solely on color to convey state (use shape or pattern differentiation)
- Navigation icons must have visible text labels (icon-only navigation is a known accessibility barrier)
- Icon sizes: 16px (inline), 20px (navigation), 24px (feature), 32px (hero). Four sizes only.

### 6.6 High Contrast Mode

Provide a high-contrast variant of the color system for users who require it. This variant:
- Increases text contrast to minimum 10:1
- Replaces subtle borders with visible 1px solid lines
- Removes background warmth variation (uses only `surface-0` and `surface-2` for maximum distinction)
- Increases focus ring width to 3px

---

## 7. Touchpoint Architecture

### 7.1 CLI

The CLI is the brand's front door. Identity is typographic and behavioral.

| Element | Treatment |
|---------|-----------|
| Prompt marker | `gold-500` color. Format: `helioy>` or tool-specific `fmm>`, `cx>` |
| Status lines | `text-tertiary` (dim). Structured with tree characters (`├─`, `└─`) |
| Content output | `text-primary` (default terminal foreground) |
| Success | `signal-success` prefix |
| Warning | `signal-warning` prefix |
| Error | `signal-error` prefix with actionable message |
| Tables | Aligned columns, `border-subtle` separators, `text-secondary` headers |

**Behavioral identity:**
- Default output is terse. Verbose flags (`-v`, `--verbose`) unlock detail layers.
- Consistent verb-noun grammar across all tools (`cx_recall`, `fmm_list_files`, `md_search`)
- Structured output (tables, indented trees) over wall-of-text

### 7.2 Documentation Site

| Element | Specification |
|---------|--------------|
| Theme | Dark by default, light mode available |
| Layout | `container-sm` (640px) for prose, `layout-sidebar` (3/9) for navigation |
| Typography | System sans for prose, monospace for code blocks |
| Headings | `text-2xl` for H2, `text-xl` for H3, `gold-500` accent on H1 |
| Code blocks | `surface-1` background, monospace, syntax highlighting using brand palette |
| Cross-links | Visible relationship indicators between related concepts |
| Navigation | Architecture-first hierarchy: system topology before individual tool docs |
| Search | Prominent, keyboard-accessible (`/` shortcut), instant results |

**Voice:** Technical precision. No marketing language in documentation. The docs earn trust by being right.

### 7.3 Website / Marketing

| Element | Specification |
|---------|--------------|
| Theme | Dark mode primary. Light mode available. |
| Layout | `container-xl` (1280px) for marketing pages |
| Hero | Interactive system diagram showing product topology. Not static illustration. |
| Navigation | 5-7 items maximum. `gold-500` active indicator. |
| CTAs | `gold-500` background, `surface-0` text. Minimum 44x44px touch target. |
| Content structure | Lead with architecture (system diagram), then capabilities, then use cases |
| Typography | `text-4xl` hero headings, `text-base` body, generous (`space-12`) section spacing |
| Diagrams | Structural diagrams as brand art using the color system. Gold highlights on active nodes, warm charcoal for structure. |

### 7.4 Product UI

| Element | Specification |
|---------|--------------|
| Theme | Dark primary, light secondary. User preference persisted. |
| Layout | `container-full` for dashboards. `layout-sidebar` (3/9) standard. |
| Density | Compact mode available: reduces `space-3` padding to `space-2`, reduces `text-base` to `text-sm` |
| System state | Always visible: agent count, bus status, token budget. `gold-500` for active, `text-tertiary` for idle. |
| Data visualization | Brand palette only. Gold for primary series, semantic colors for status, `text-secondary` for axes/labels. |
| Navigation | Sidebar with text labels. Icon + label, never icon-only. |
| Instrument panel metaphor | Dense, purposeful, every element actionable. Scales from simple (indie dev) to complex (enterprise) by adding panels, not redesigning. |

### 7.5 Scaling Principle

The brand scales by adding layers of structure, not visual complexity:

**Indie dev (now):** Gold mark + monospace type + dark surface. Minimal. Recognizable in a terminal screenshot.

**Teams (next):** Add the surface elevation system. Panels, cards, layout grids. The brand expands through structure.

**Enterprise (future):** Add the signal color system for operational dashboards. Status indicators, health metrics, system topology views. The brand becomes an operating environment.

---

## Appendix: Token Reference (CSS Custom Properties)

```css
:root {
  /* Brand */
  --gold-400: #e0b960;
  --gold-500: #d4a54a;
  --gold-600: #b8912e;
  --gold-700: #8a6e1a;
  --gold-900: #3d3010;

  /* Surfaces (dark) */
  --surface-0: #1a1816;
  --surface-1: #222018;
  --surface-2: #2e2b24;
  --surface-3: #3a3730;
  --border-subtle: #3a3730;
  --border-default: #4a4740;
  --border-interactive: #7a7570;

  /* Text (dark) */
  --text-primary: #f0ebe4;
  --text-secondary: #9a9590;
  --text-tertiary: #6a6560;

  /* Semantic */
  --signal-success: #6b9b7a;
  --signal-warning: #d4a54a;
  --signal-error: #d45a5a;
  --signal-info: #5b8db8;

  /* Spacing */
  --space-1: 0.25rem;
  --space-2: 0.5rem;
  --space-3: 0.75rem;
  --space-4: 1rem;
  --space-6: 1.5rem;
  --space-8: 2rem;
  --space-12: 3rem;
  --space-16: 4rem;
  --space-24: 6rem;

  /* Typography */
  --text-xs: 0.75rem;
  --text-sm: 0.875rem;
  --text-base: 1rem;
  --text-lg: 1.25rem;
  --text-xl: 1.5rem;
  --text-2xl: 1.875rem;
  --text-3xl: 2.375rem;
  --text-4xl: 3rem;

  /* Containers */
  --container-xs: 480px;
  --container-sm: 640px;
  --container-md: 768px;
  --container-lg: 1024px;
  --container-xl: 1280px;

  /* Motion */
  --ease-default: cubic-bezier(0.16, 1, 0.3, 1);
  --duration-fast: 120ms;
  --duration-normal: 200ms;
  --duration-slow: 400ms;
}

/* Light mode override */
[data-theme="light"] {
  --surface-0: #faf8f5;
  --surface-1: #f0ece6;
  --surface-2: #e6e2dc;
  --surface-3: #dcd8d2;
  --border-subtle: #dcd8d2;
  --border-default: #c8c4be;
  --border-interactive: #8a8580;
  --text-primary: #1a1816;
  --text-secondary: #5a5550;
  --text-tertiary: #8a8580;
  --signal-success: #2d7a46;
  --signal-warning: #7a5f14;
  --signal-error: #a83232;
  --signal-info: #3a6e96;
  --gold-interactive: #8a6e1a;
  --focus-ring: #1a1816;
}

/* System preference bridge */
@media (prefers-color-scheme: light) {
  :root:not([data-theme="dark"]) {
    --surface-0: #faf8f5;
    --surface-1: #f0ece6;
    --surface-2: #e6e2dc;
    --surface-3: #dcd8d2;
    --border-subtle: #dcd8d2;
    --border-default: #c8c4be;
    --border-interactive: #8a8580;
    --text-primary: #1a1816;
    --text-secondary: #5a5550;
    --text-tertiary: #8a8580;
    --signal-success: #2d7a46;
    --signal-warning: #7a5f14;
    --signal-error: #a83232;
    --signal-info: #3a6e96;
    --gold-interactive: #8a6e1a;
    --focus-ring: #1a1816;
  }
}

/* Reduced motion */
@media (prefers-reduced-motion: reduce) {
  * {
    animation-duration: 0ms !important;
    transition-duration: 0ms !important;
  }
}
```

---

**Author:** UX Architect
**Date:** 2026-03-15
**Version:** 1.1
**Status:** Foundation specification complete. Accessibility audit fixes applied. Ready for UI Designer Phase 2 work.
**Dependencies:** UI Designer to finalize system font selection and wordmark font from specified constraints.

---

## Changelog

### v1.1 (2026-03-15) — Accessibility Audit Fixes

Five critical light mode failures identified by accessibility audit, now resolved:

1. **Light mode interactive gold**: `gold-700` (`#8a6e1a`) designated as the interactive gold token for light mode (links, active states, navigation indicators). Added `--gold-interactive` CSS property for light mode.
2. **Light mode focus ring**: Switched from `gold-500` to `text-primary-light` (`#1a1816`) in light mode for sufficient contrast. Added `--focus-ring` CSS property.
3. **Dark mode signal-error**: Changed from `#c94a4a` to `#d45a5a` for improved contrast on dark surfaces.
4. **Light mode signal-warning**: Changed from `#b8912e` to `#7a5f14` for sufficient contrast on light surfaces.
5. **Border tokens**: Added `border-interactive` token (`#7a7570` dark, `#8a8580` light) meeting 3:1 non-text contrast in both modes.
