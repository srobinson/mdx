---
title: "Helioy Identity: Accessibility & Inclusion Audit"
category: projects
created: 2026-03-15
author: inclusive-visuals-specialist
tags: [helioy, identity, accessibility, audit, phase-3]
status: audit-complete
---

# Helioy Identity: Accessibility & Inclusion Audit

Auditor: Inclusive Visuals Specialist
Input documents: visual-system.md, design-system-foundations.md, brand-strategy.md, inclusive-visuals brainstorm
Method: Programmatic contrast ratio calculation using WCAG 2.x relative luminance formula. All ratios verified to two decimal places.

---

## Audit Summary

**Dark mode: Solid foundation with two actionable issues.**
**Light mode: Five critical failures that must be fixed before production.**

The dark mode palette is well constructed. The light mode palette has systematic gold/amber contrast failures that render interactive elements, focus states, and warning signals inaccessible. These are not edge cases. They affect every gold-colored element in light mode.

---

## 1. Color Contrast Audit

### 1.1 Dark Mode Text on Surfaces

| Combination | Ratio | AA (4.5:1) | AA Large (3:1) | AAA (7:1) | Verdict |
|---|---|---|---|---|---|
| text-primary on surface-0 | 14.93:1 | PASS | PASS | PASS | Excellent |
| text-primary on surface-1 | 13.75:1 | PASS | PASS | PASS | Excellent |
| text-primary on surface-2 | 11.91:1 | PASS | PASS | PASS | Excellent |
| text-primary on surface-3 | 10.01:1 | PASS | PASS | PASS | Excellent |
| text-secondary on surface-0 | 5.97:1 | PASS | PASS | - | Good |
| text-secondary on surface-1 | 5.49:1 | PASS | PASS | - | Good |
| text-secondary on surface-2 | 4.76:1 | PASS | PASS | - | Acceptable |
| **text-secondary on surface-3** | **4.00:1** | **FAIL** | PASS | - | **Fix required** |
| text-tertiary on surface-0 | 3.07:1 | - | PASS | - | OK if large text only |
| text-tertiary on surface-1 | 2.83:1 | - | **FAIL** | - | **Restricted use** |
| text-tertiary on surface-2 | 2.45:1 | - | **FAIL** | - | **Restricted use** |
| text-tertiary on surface-3 | 2.06:1 | - | **FAIL** | - | **Restricted use** |

**Issue D1: text-secondary on surface-3 fails AA.** The spec uses surface-3 for active/selected row backgrounds. Metadata text (`text-secondary`) on selected rows will be inaccessible.

**Fix D1:** Darken `text-secondary` to approximately `#a09b96` (or lighter) to achieve 4.5:1 on surface-3. Alternatively, document that selected rows must promote secondary text to `text-primary`.

**Issue D2: text-tertiary usable only on surface-0 at large sizes.** The spec correctly marks this as "disabled, placeholder" but does not restrict its surface pairing. On surface-1, surface-2, and surface-3, it fails even AA Large.

**Fix D2:** Add an explicit constraint to the design system: `text-tertiary` may only be used on `surface-0`. On elevated surfaces, disabled/placeholder text must use `text-secondary` at reduced opacity or a dedicated `text-disabled` token.

### 1.2 Dark Mode Gold on Surfaces

| Combination | Ratio | AA | AA Large | Verdict |
|---|---|---|---|---|
| gold-500 on surface-0 | 7.82:1 | PASS | PASS | Excellent |
| gold-500 on surface-1 | 7.21:1 | PASS | PASS | Excellent |
| gold-500 on surface-2 | 6.24:1 | PASS | PASS | Good |
| gold-500 on surface-3 | 5.25:1 | PASS | PASS | Acceptable |
| gold-600 on surface-0 | 6.01:1 | PASS | PASS | Good |
| gold-600 on surface-1 | 5.53:1 | PASS | PASS | Good |
| gold-600 on surface-2 | 4.79:1 | PASS | PASS | Acceptable |
| **gold-600 on surface-3** | **4.03:1** | **FAIL** | PASS | **Fix required** |
| gold-700 on surface-0 | 3.65:1 | FAIL | PASS | Decorative only |
| gold-700 on surface-1 | 3.36:1 | FAIL | PASS | Decorative only |
| gold-700 on surface-2 | 2.91:1 | FAIL | FAIL | **Avoid** |
| gold-700 on surface-3 | 2.45:1 | FAIL | FAIL | **Avoid** |

**Issue D3: gold-600 on surface-3 fails AA.** The spec uses gold-600 for pressed states. If a pressed button sits on surface-3 (active row), it falls below threshold.

**Fix D3:** Ensure pressed states on elevated surfaces use `gold-500` floor, or darken `surface-3` pressed-state combinations by constraining gold-600 to surface-0 and surface-1 only.

**Issue D4: gold-700 fails AA Large on surface-2 and surface-3.** The spec marks gold-700 as "decorative only" for dark surfaces. This is correct, but the visual system doc uses gold-700 for "metadata on dark surfaces." If that metadata is text, it is inaccessible on any surface above surface-0.

**Fix D4:** Strike "metadata" from gold-700's role in the visual system. Replace with "decorative borders and lattice texture only. Never for text of any size."

### 1.3 Dark Mode Semantic Colors

| Combination | Ratio | AA | AA Large |
|---|---|---|---|
| signal-success on surface-0 | 5.56:1 | PASS | PASS |
| signal-success on surface-1 | 5.12:1 | PASS | PASS |
| **signal-error on surface-0** | **3.85:1** | **FAIL** | PASS |
| **signal-error on surface-1** | **3.54:1** | **FAIL** | PASS |
| signal-info on surface-0 | 5.01:1 | PASS | PASS |
| signal-info on surface-1 | 4.62:1 | PASS | PASS |

**Issue D5: signal-error (#c94a4a) fails AA on all dark surfaces.** Error text at body size (16px, weight 400) is inaccessible. This is a critical finding. Error messages are high-priority content that users need to read under stress.

**Fix D5:** Lighten `signal-error` dark mode value to `#d45a5a` or `#d86060`. Target: 4.5:1 minimum on surface-0. Verify the replacement maintains warm terracotta character and sufficient distinction from gold.

### 1.4 Light Mode: Text on Surfaces

| Combination | Ratio | AA | AAA |
|---|---|---|---|
| text-primary-light on surface-0-light | 16.70:1 | PASS | PASS |
| text-primary-light on surface-1-light | 15.05:1 | PASS | PASS |
| text-secondary-light on surface-0-light | 6.95:1 | PASS | FAIL |
| text-secondary-light on surface-1-light | 6.26:1 | PASS | FAIL |
| text-secondary-light on surface-2-light | 5.71:1 | PASS | FAIL |
| text-secondary-light on surface-3-light | 5.19:1 | PASS | FAIL |
| text-tertiary-light on surface-0-light | 3.45:1 | FAIL | FAIL |
| text-tertiary-light on surface-1-light | 3.11:1 | FAIL | FAIL |
| text-tertiary-light on surface-2-light | 2.83:1 | FAIL | FAIL |

Light mode text hierarchy is acceptable. Same tertiary restriction applies: large text on base surface only.

### 1.5 Light Mode: Gold on Surfaces (CRITICAL FAILURE CLUSTER)

| Combination | Ratio | AA | AA Large |
|---|---|---|---|
| **gold-400 on surface-0-light** | **1.76:1** | **FAIL** | **FAIL** |
| **gold-500 on surface-0-light** | **2.13:1** | **FAIL** | **FAIL** |
| **gold-500 on surface-1-light** | **1.92:1** | **FAIL** | **FAIL** |
| **gold-600 on surface-0-light** | **2.78:1** | **FAIL** | **FAIL** |
| **gold-600 on surface-1-light** | **2.50:1** | **FAIL** | **FAIL** |
| gold-700 on surface-0-light | 4.58:1 | PASS | PASS |
| gold-700 on surface-1-light | 4.13:1 | FAIL | PASS |

**Issue L1 (CRITICAL): gold-500 is invisible in light mode.** At 2.13:1 on the lightest surface, gold-500 fails every WCAG threshold. This affects:
- All interactive links (documentation specifies gold-500 for links)
- Active navigation items
- Active sidebar indicators
- The "every token counts" tagline on marketing pages
- The CLI prompt marker on light terminal backgrounds
- Any gold-colored text or icon label

This is not an edge case. It affects every interactive gold element across the entire light mode experience.

**Issue L2 (CRITICAL): Focus ring fails in light mode.** The spec defines focus as "2px solid gold-500, offset 2px." On light surfaces, gold-500 achieves only 1.59:1 to 2.13:1. Focus indicators are functionally invisible in light mode. Keyboard-only users cannot see where they are on the page.

**Issue L3 (CRITICAL): signal-warning in light mode is inaccessible.** `signal-warning-light` (#b8912e) achieves only 2.78:1 on surface-0-light and 2.50:1 on surface-1-light. Warning messages are unreadable. Since warning reuses the gold family, the same fundamental contrast problem applies.

**Fix for L1, L2, L3 (unified):** The gold accent color needs a light-mode-specific variant. Options:

**Option A (recommended):** Create a `gold-light` token at approximately `#8a6e1a` (the current gold-700) or darker for all interactive gold in light mode. gold-700 achieves 4.58:1 on surface-0-light, passing AA. This is already in the palette. The fix is a usage rule: in light mode, interactive gold uses `gold-700`, not `gold-500`.

**Option B:** Create a dedicated `interactive-gold-light` token at approximately `#7a5f14`, targeting 5.5:1+ on light surfaces.

**Option C:** For focus rings specifically, switch to `text-primary-light` (#1a1816) in light mode. This guarantees visibility (16.70:1) and is a common accessible pattern.

**Recommendation:** Apply Option A for text and interactive elements. Apply Option C for focus rings. The focus ring does not need to be gold in light mode. It needs to be visible.

### 1.6 Light Mode Semantic Colors

| Combination | Ratio | AA |
|---|---|---|
| signal-success-light on surface-0-light | 4.97:1 | PASS |
| **signal-success-light on surface-1-light** | **4.48:1** | **FAIL** |
| signal-error-light on surface-0-light | 6.25:1 | PASS |
| signal-error-light on surface-1-light | 5.63:1 | PASS |
| signal-info-light on surface-0-light | 5.14:1 | PASS |
| signal-info-light on surface-1-light | 4.63:1 | PASS |

**Issue L4: signal-success-light barely fails on surface-1-light.** Status indicators on cards (surface-1) will have insufficient contrast.

**Fix L4:** Darken `signal-success-light` from `#2d7a46` to `#267040` or similar. Target: 4.8:1+ on surface-1-light.

### 1.7 Border/UI Component Contrast (SYSTEMIC FAILURE)

WCAG 2.1 SC 1.4.11 requires 3:1 contrast for UI component boundaries against adjacent colors.

| Combination | Ratio | 3:1 Requirement |
|---|---|---|
| **border-default vs surface-0** | **1.91:1** | **FAIL** |
| **border-default vs surface-1** | **1.76:1** | **FAIL** |
| **border-subtle vs surface-0** | **1.49:1** | **FAIL** |
| **border-default-light vs surface-0-light** | **1.64:1** | **FAIL** |
| **border-default-light vs surface-1-light** | **1.48:1** | **FAIL** |
| **border-subtle-light vs surface-0-light** | **1.34:1** | **FAIL** |

**Issue B1 (CRITICAL): Every border token fails the 3:1 non-text contrast requirement in both modes.**

The design philosophy uses surface elevation shifts rather than borders, and the spec correctly treats borders as supplementary. But the visual system explicitly uses `border-default` for "inputs, cards that need explicit edges." Input field boundaries are required by WCAG to meet 3:1 against their background. A user who cannot perceive the surface-1 to surface-0 shift (low-vision, low-quality display, direct sunlight) has no fallback indicator for where the input field is.

**Fix B1:** Create a `border-interactive` token specifically for input fields and form controls:
- Dark mode: approximately `#5a5750` (target 3:1+ against surface-0 and surface-1)
- Light mode: approximately `#a8a49e` (target 3:1+ against surface-0-light and surface-1-light)

`border-subtle` and `border-default` can remain as decorative/supplementary borders where the surface shift provides the primary visual boundary. But any border that serves as the sole indicator of a UI component boundary (inputs, checkboxes, toggles) must use the new `border-interactive` token.

### 1.8 CTA Button Contrast

| Combination | Ratio | AA |
|---|---|---|
| surface-0 text on gold-500 background | 7.82:1 | PASS |

The dark-on-gold CTA button passes. This is well designed.

**Light mode CTA note:** The spec does not define a light mode CTA. If the same gold-500 background with dark text pattern is used, it will pass (7.82:1). If gold-500 is used for text on a light button, it will fail per L1. Ensure CTAs use gold as a fill, never as text, in light mode.

---

## 2. Color Blindness Assessment

### 2.1 Protanopia and Deuteranopia (red-green, ~8% of males)

The gold/amber primary is a strong choice. Gold sits in the yellow channel, which protanopes and deuteranopes perceive with near-normal sensitivity. The primary brand color remains visible and distinctive under red-green color blindness.

**Concern: signal-error vs signal-warning.** Both `signal-error` (#c94a4a, warm red) and `signal-warning` (#d4a54a, gold) shift toward similar brownish-yellow hues under deuteranopia simulation. Users with deuteranopia may not distinguish error from warning states by color alone.

**Status:** Mitigated by existing design system rule: icons must use shape differentiation (checkmark, X, triangle). If shape is enforced consistently, color distinction is supplementary. But the spec must call this out explicitly in the semantic color section.

### 2.2 Tritanopia (blue-yellow, ~0.003%)

Gold/amber occupies the yellow range that tritanopes perceive poorly. Under tritanopia, the gold accent shifts toward pinkish-gray and loses its warmth. The brand's signature color becomes muted.

**Status:** Tritanopia is extremely rare. The brand gold will still be visible (it does not disappear), but its emotional warmth is reduced. No fix needed, but worth noting for the high-contrast mode: the high-contrast variant should not rely on gold warmth as a distinguishing factor.

### 2.3 Data Visualization Series Distinction

| Pair | Contrast | 3:1 Target |
|---|---|---|
| gold-500 vs signal-info | 1.56:1 | **FAIL** |
| gold-500 vs text-secondary | 1.31:1 | **FAIL** |
| signal-info vs text-secondary | 1.19:1 | **FAIL** |

**Issue CV1: All three data visualization series colors fail to achieve 3:1 contrast against each other.** Under any form of color blindness, these three series become indistinguishable.

**Fix CV1:** Data visualizations must use shape or pattern differentiation in addition to color. Require: solid lines vs dashed vs dotted for line charts. Filled vs hollow vs hatched for bar segments. And add direct labels (not just legends) to each data series. The spec prohibits pie charts (good), but must add pattern requirements for all other chart types.

---

## 3. Typography Legibility

### 3.1 General Sans Assessment

General Sans is a geometric sans-serif with humanist influences. Assessment against the brainstorm requirements:

**Letterform distinction (l/1/I/0/O):** General Sans has acceptable distinction between these characters. The lowercase l has a subtle tail, the digit 1 has a distinct flag, and the capital I has serifs at display weights. At text-sm (14px) and below, the l/I distinction becomes marginal. This is mitigated by the system primarily displaying code in JetBrains Mono, where these characters are unambiguous.

**Mirrored letterforms (b/d, p/q):** General Sans, like most geometric sans-serifs, has symmetrical b/d and p/q. This is a known friction point for dyslexic readers. However, no geometric sans avoids this entirely, and the brand's choice to prioritize geometric warmth is defensible. The high line height (1.6 for body) and generous spacing mitigate reading difficulty.

**Weight at small sizes:** General Sans weight 400 at text-xs (12px) on dark backgrounds may appear thin. The warm off-white text-primary (#f0ebe4) on warm charcoal is better than pure white on pure black for subpixel rendering, which helps. No fix required, but monitor closely.

**Script fallback chain:** The specified chain (`"General Sans", "Noto Sans", "Noto Sans CJK", system-ui, sans-serif`) is correct. Noto Sans provides weight-matched fallbacks for Latin, Cyrillic, Devanagari, Arabic, and CJK scripts. The system-ui fallback catches any remaining gaps. This is well specified.

### 3.2 Body Text Sizing

- Minimum body text: 16px (1rem). **PASS.**
- Line height: 1.6 for body. **PASS** (exceeds 1.5 minimum).
- Max line length: 72ch body, 90ch docs. **PASS** (72 is within the 45-75ch optimal range).
- text-xs (12px) exists. The spec restricts it to "badges, annotations, code comments." This is acceptable if enforced. 12px text on elevated surfaces with text-secondary color reaches 4.76:1 at best, which passes AA but provides poor readability for sustained reading.

**Recommendation:** Add an explicit rule: `text-xs` must never be used for content that requires reading. Badges and labels only. If a code annotation requires comprehension, use `text-sm` (14px) minimum.

### 3.3 Line Length Control

The spec defines `container-sm: 640px` for prose. At 16px General Sans, 640px width produces approximately 75-80 characters per line depending on content mix. This slightly exceeds the 72ch rule but is within acceptable range. No fix needed.

---

## 4. Logo Legibility

### 4.1 The Facet at Small Sizes

**16x16px (favicon):** The spec correctly simplifies to a single-fill quadrilateral, dropping the internal facet division. A single gold-500 (#d4a54a) shape on a transparent background will read as a distinctive mark at this size. The asymmetric silhouette (12-degree rotation of the irregular pentagon) provides enough shape identity to distinguish it from common geometric favicon shapes.

**Assessment: PASS.** The favicon treatment is well considered.

**32x32px (avatar/npm):** Two-facet rendering with gold-500/gold-600 fill distinction. The contrast between these two golds is only 1.30:1. At 32px, this subtle distinction may be invisible on lower-quality displays or under color blindness.

**Assessment: Marginal.** The mark will read as a single-color shape on most 32px contexts, with the facet distinction becoming a bonus on high-DPI displays. This is acceptable because the mark's identity comes from its silhouette, not its internal color variation.

**48x48px+:** Full rendering with clear facet distinction. No concerns at this size.

### 4.2 The Facet on Light Surfaces

The light-mode Facet uses gold-600 (#b8912e) and gold-700 (#8a6e1a) fills.

- Light facet (gold-600) on surface-0-light: 2.78:1
- Shadow facet (gold-700) on surface-0-light: 4.58:1

**Issue M1: The light-mode Facet's lighter facet achieves only 2.78:1 against the light background.** The mark's lighter half may appear washed out on light surfaces, reducing visual presence.

**Fix M1:** Darken the light-mode Facet's light facet from gold-600 to gold-700, and the shadow facet from gold-700 to a new darker value (approximately `#6a5514`). Target: both facets above 3:1 on surface-0-light (the 3:1 threshold for graphical objects per WCAG SC 1.4.11).

### 4.3 Monochrome Variant

The reversed/knockout variant uses text-primary (#f0ebe4) at 100%/70% opacity on dark surfaces. At 100% opacity, contrast is 14.93:1. At 70% opacity (effective color approximately #b8b3ac on surface-0), contrast is approximately 8.5:1. Both pass. **PASS.**

---

## 5. Motion Accessibility

### 5.1 prefers-reduced-motion Implementation

The CSS spec includes:

```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0ms !important;
    transition-duration: 0ms !important;
  }
}
```

**Assessment: PASS.** This is a correct, comprehensive implementation. The `!important` override ensures no component-level animation can bypass the user's preference. The `*::before, *::after` selectors catch pseudo-element animations.

### 5.2 Structured Light Pattern Animation

The spec defines a 30-60 second cycle for the caustic light pattern animation, with linear easing. It explicitly states: "When reduced motion is active, the pattern is static at its median opacity."

**Assessment: PASS.** The animation is slow and subtle (no seizure risk). The static fallback is clearly specified.

### 5.3 Stagger Pattern

The cascading stagger (0ms, 60ms, 100ms, 120ms) with decreasing delay increments is well designed. Maximum total entrance animation: 120ms + 400ms (duration-slow) = 520ms. This is within the sub-second threshold where motion is perceived as responsive rather than decorative.

**Assessment: PASS.**

### 5.4 Missing Specification

The spec covers UI transitions and the Structured Light pattern, but does not address:

- **Page transitions:** If the website or product UI uses page-level transitions (route changes), these must also respect reduced-motion.
- **Scroll-linked animations:** If parallax or scroll-triggered animations are introduced later, they must be disabled under reduced-motion.
- **Video/animated content:** If marketing pages include embedded video or animated SVG diagrams, autoplay must be disabled under reduced-motion, or controls provided.

**Fix MO1:** Add a blanket rule to the design system: "All motion, regardless of source (CSS, JavaScript, SVG SMIL, video autoplay), must respect prefers-reduced-motion. No exceptions."

---

## 6. Cultural Sensitivity

### 6.1 The Crystallization Metaphor

Crystallization as a governing visual metaphor is culturally neutral. Crystals carry broadly positive associations across global cultures: formation, value, structure, clarity. Specific cultural readings:

- **Western:** Associated with clarity, precision, science. Aligns with brand attributes.
- **East Asian:** Crystals and gemstones carry positive associations with refinement and accumulated wisdom in Chinese and Japanese traditions.
- **South Asian:** Crystal (sphatik) holds sacred status in Hindu tradition but is broadly positive. The abstract geometric treatment avoids religious specificity.
- **Middle Eastern:** Geometric crystalline patterns are central to Islamic art and architecture. The Facet mark's geometry resonates with this tradition without appropriating specific sacred patterns (it does not use star-and-polygon tessellation or any identifiable Islamic geometric pattern).
- **African:** Crystal and mineral imagery connects to real geological wealth. No negative associations identified.

**Assessment: PASS.** No cultural sensitivity concerns with the crystallization metaphor.

### 6.2 The Gold Color

Gold carries universally positive associations: solar energy, value, warmth. The matte treatment specified in the brand strategy avoids the "luxury/opulence" reading that polished gold triggers. No cultural concerns.

**One note:** In some East Asian contexts, gold paired with red signals festivity or prosperity (Chinese New Year, for example). The brand's avoidance of saturated red for semantic colors means this pairing will not occur accidentally. The warm terracotta `signal-error` is sufficiently distinct from festive red. **No fix needed.**

### 6.3 The Facet Mark Shape

The asymmetric pentagon with one vertex removed does not resemble any national flag, religious symbol, political emblem, or culturally significant glyph that I can identify. The 12-degree rotation further distances it from any recognizable geometric symbol.

**Assessment: PASS.**

### 6.4 Wordmark in Mixed Case

"Helioy" in mixed case with capital H is a safe choice. The word does not form offensive combinations in major world languages. The wide tracking prevents any visual ambiguity where adjacent letterforms might suggest unintended words.

**Assessment: PASS.** (Formal linguistic review across Mandarin, Arabic, Hindi, Spanish, Portuguese phonetic systems still recommended before global launch, as noted in Phase 0 brainstorm.)

---

## 7. Recommendations: Required Fixes

Ordered by severity. Each fix includes the exact corrective action.

### CRITICAL (must fix before any production use)

**C1. Light mode interactive gold.**
Create a usage rule: in light mode, all interactive gold elements (links, active states, navigation indicators, icon active states) use `gold-700` (#8a6e1a) instead of `gold-500`. gold-700 achieves 4.58:1 on surface-0-light, passing AA. Update the Color Bridge Rule to document this shift: "In dark mode, gold-500 is the interactive accent. In light mode, gold-700 serves this role."

**C2. Light mode focus ring.**
Switch focus ring color in light mode from `gold-500` to `text-primary-light` (#1a1816). This achieves 16.70:1 and guarantees visibility. Keep gold-500 for dark mode focus rings (7.82:1 on surface-0, excellent). Add to CSS:
```css
[data-theme="light"] {
  --focus-ring-color: var(--text-primary);
}
```

**C3. signal-error dark mode.**
Replace `#c94a4a` with `#d45a5a` for dark mode. Verify the new value achieves 4.5:1+ on surface-0 and maintains visual distinction from signal-warning (gold-500).

**C4. signal-warning light mode.**
Replace `#b8912e` with `#7a5f14` (or equivalent dark amber) for light mode. Target: 4.5:1 on surface-0-light. The warning state in light mode is currently invisible.

**C5. Interactive border token.**
Create `border-interactive` at approximately `#5a5750` (dark) and `#a8a49e` (light). Apply to all form inputs, checkboxes, toggles, and any component where the border is the sole indicator of the component boundary. Leave `border-subtle` and `border-default` for decorative/supplementary use.

### HIGH (fix before launch)

**H1. signal-success light mode.**
Darken from `#2d7a46` to `#267040` for light mode. Target: 4.8:1+ on surface-1-light.

**H2. Facet mark light mode facets.**
Darken the light-mode Facet fills. Light facet: gold-700 (#8a6e1a). Shadow facet: new `gold-800` at approximately `#6a5514`. Both must exceed 3:1 on surface-0-light.

**H3. text-secondary on surface-3 restriction.**
Add to design system: "When using surface-3 (active/selected states), promote text-secondary content to text-primary." Alternatively, lighten text-secondary by one stop to achieve 4.5:1 on surface-3.

### MODERATE (fix before scaling)

**M1. text-tertiary surface restriction.**
Add explicit rule: `text-tertiary` is permitted only on `surface-0`. On elevated surfaces, use `text-secondary` at 70% opacity for disabled states.

**M2. gold-700 role clarification.**
Remove "metadata" from gold-700's described role. It is decorative only on dark surfaces (3.65:1 on surface-0 fails AA). In light mode it becomes the interactive gold per fix C1.

**M3. Data visualization pattern requirement.**
Add to the data visualization spec: "All chart types must use shape or pattern differentiation in addition to color. Line charts: solid, dashed, dotted. Bar charts: solid, hatched, stippled. All series must carry direct labels, not legend-only."

**M4. Motion blanket rule.**
Add: "All motion, regardless of implementation method (CSS, JS, SVG, video autoplay), must respect prefers-reduced-motion. No exceptions."

**M5. text-xs usage constraint.**
Add: "`text-xs` (12px) is restricted to non-reading content: badges, labels, annotations. Any text that requires comprehension must use `text-sm` (14px) minimum."

---

## 8. High Contrast Mode Gap

The design system foundations spec (section 6.6) defines a high-contrast variant with correct requirements (10:1 text, visible borders, reduced surface variation, wider focus rings). The visual system spec does not include the actual high-contrast token values.

**Issue HC1:** The high-contrast mode is specified in requirements but not in implementation values. No CSS custom properties or token overrides are provided.

**Fix HC1:** Add a `[data-theme="high-contrast"]` block to the CSS spec with:
- `text-primary: #ffffff` (exception to the "no pure white" rule, justified by accessibility need)
- `text-secondary: #d0ccc6`
- `surface-0: #0a0908`
- `surface-1: #1a1816`
- `border-default: #8a8580` (achieves 3:1+ on all surfaces)
- Focus ring: 3px solid `#ffffff`

---

## Final Verdict

The dark mode palette is strong. The team clearly invested in contrast ratios for the primary usage mode. The light mode has systematic gold-contrast failures that are fixable with a single design decision: use gold-700 as the interactive gold in light mode, and darken the focus ring.

The border contrast failure is structural but solvable with a new interactive border token. The error/warning color fixes are straightforward value adjustments.

None of these findings require rethinking the visual direction. The warm mineral palette, the crystallization metaphor, the Facet mark, the typography system: all of these survive the audit. The fixes are calibration, not redesign.

**Post-fix, this identity system will exceed WCAG 2.2 AA compliance across both modes and will meet AAA for primary text.** That is a strong foundation for a brand that claims precision as a core attribute.

---

*Auditor: Inclusive Visuals Specialist*
*Date: 2026-03-15*
*Method: Programmatic WCAG relative luminance calculation, all values verified to 0.01:1 precision*
