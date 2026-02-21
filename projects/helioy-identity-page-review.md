---
title: "Helioy Identity Page: Brand Review"
category: projects
tags: [helioy, identity, brand-review, page-audit]
created: 2026-03-15
author: brand-guardian
status: review-complete
reviewed_file: /Users/alphab/Dev/LLM/DEV/helioy/identity/index.html
---

# Helioy Identity Page: Brand Review

Reviewer: Brand Guardian
Source: `/Users/alphab/Dev/LLM/DEV/helioy/identity/index.html`
Reviewed against: `helioy-identity-brand-guidelines.md` v1.1, `helioy-identity-visual-system.md` v1.1, `helioy-identity-accessibility-audit.md`

---

## Verdict

Strong execution with one critical defect: the page loads Inter instead of General Sans. Every color value, every spacing token, every voice example, every logo variant is correct. The font substitution is the only issue that would be visible to someone comparing this page against the brand spec.

---

## Issues Found

### CRITICAL

**F1. Wrong typeface: Inter instead of General Sans**
The page loads Inter from Google Fonts and declares it as the primary font. The brand spec requires General Sans for all UI, body, marketing, and wordmark usage.

- **Line 10:** `family=Inter:wght@400;500;600;700` loaded from Google Fonts
- **Line 52:** `--font-sans: "Inter", "Noto Sans", system-ui, sans-serif;`
- **Line 1157:** Typography section description reads "Inter as primary face"

**Fix:**
- Line 10: Replace Google Fonts link with a self-hosted General Sans `@font-face` declaration (General Sans is not on Google Fonts; it requires a Fontshare or purchased license embed)
- Line 52: Change to `--font-sans: "General Sans", "Noto Sans", "Noto Sans CJK", system-ui, sans-serif;`
- Line 1157: Change description text from "Inter as primary face" to "General Sans as primary face"

Note: the fallback chain is also missing `"Noto Sans CJK"` per the spec.

---

### HIGH

**F2. Horizontal lockup gap is 48px with a 64px mark (0.75:1 ratio)**
The spec requires the gap between mark and wordmark to equal the mark width (1:1 ratio).

- **Line 1251:** `gap:48px` with a `width="64"` SVG mark

**Fix:**
- Line 1251: Change `gap:48px` to `gap:64px`

---

**F3. scroll-behavior: smooth not disabled under prefers-reduced-motion**
The CSS reduced-motion rule (lines 98-103) sets `animation-duration` and `transition-duration` to 0ms. It does not disable `scroll-behavior: smooth` (line 112). Users with reduced motion preferences will still experience smooth scrolling, which violates the accessibility audit's blanket rule: "All motion must respect prefers-reduced-motion. No exceptions."

- **Line 112:** `scroll-behavior: smooth;`
- **Lines 98-103:** Missing `scroll-behavior: auto;`

**Fix:**
Add to the `@media (prefers-reduced-motion: reduce)` block:
```css
html {
  scroll-behavior: auto !important;
}
```

---

### MODERATE

**F4. Theme toggle focus ring offset is 1px, spec says 2px**

- **Line 209:** `outline-offset: 1px;`
- Pattern control buttons (line 612) correctly use `outline-offset: 2px`

**Fix:**
- Line 209: Change `outline-offset: 1px` to `outline-offset: 2px`

---

**F5. Theme toggle uses 2px spacing values outside the 4px base system**

- **Line 179:** `gap: 2px;`
- **Line 183:** `padding: 2px;`

The spacing scale starts at 4px (`space-1`). 2px is not a defined token.

**Fix:**
- Change `gap: 2px` to `gap: var(--space-1)` (4px)
- Change `padding: 2px` to `padding: var(--space-1)` (4px)
- Alternatively, if the tighter spacing is intentional for this compact control, document 2px as an exception or add a `space-0.5` token

---

**F6. Gold-colored inline code in empty state voice card**
The empty state example applies `style="color:var(--gold-interactive)"` to the `cx_deposit` inline code element. The typography spec defines inline code as `text-primary` color on `surface-1` background. Gold is not specified for inline code in any context.

- **Line 1359:** `<code class="inline-code" style="color:var(--gold-interactive)">cx_deposit</code>`

**Fix:**
- Remove the inline style. Let the inline-code class handle the color (inherits `text-primary`).

---

### LOW

**F7. Missing PNG favicon fallbacks and apple-touch-icon**
The page only includes an SVG favicon (line 7). The visual system spec (Section 8.5) defines PNG fallbacks at 16px and 32px, plus an apple-touch-icon at 180px.

- **Line 7:** Only `<link rel="icon" type="image/svg+xml" href="assets/brand/favicon.svg">`

**Fix:**
Add after line 7:
```html
<link rel="icon" href="assets/brand/favicon-32.png" sizes="32x32" type="image/png">
<link rel="icon" href="assets/brand/favicon-16.png" sizes="16x16" type="image/png">
<link rel="apple-touch-icon" href="assets/brand/apple-touch-icon.png" sizes="180x180">
```

---

**F8. Caustic animation loop runs continuously under reduced motion**
The `requestAnimationFrame` loop (lines 1562-1567) runs every frame regardless of motion preference. When reduced motion is active, the animation is functionally static (time does not increment), but the render function still executes every frame. This wastes CPU/GPU cycles.

**Fix:**
When `reducedMotion` is true, render once and skip the RAF loop:
```js
if (reducedMotion) {
  pAnim = false; pTime = 1.5;
  render(heroC, 0.10, pTime);
  render(demoC, pOpacity, pTime * 1.2);
} else {
  (function loop() { /* existing loop */ })();
}
```

---

## Passed Checks

### 1. Color Values
All 28 CSS custom property values match the brand guidelines exactly. Dark mode, light mode, gold scale, surfaces, text hierarchy, borders, semantic colors, interactive aliases, and focus ring colors are all correct. The v1.1 accessibility fixes (corrected signal-error #d45a5a, light mode focus ring using text-primary, gold-interactive aliasing to gold-700 in light mode) are properly implemented.

### 2. Typography (except font family)
Type scale sizes, weights, line heights, and letter-spacing values all match. Negative tracking (-0.02em) correctly applied at text-2xl and above only. Wordmark tracking (+0.16em) used exclusively on the wordmark. Minimum body text is 16px. JetBrains Mono correctly specified for code with the proper fallback chain.

### 3. Logo Usage
- Facet mark SVG geometry is consistent across all instances
- Dark variant: gold-500 light facet, gold-600 shadow facet. Correct.
- Light variant: gold-600 light facet, gold-700 shadow facet. Correct.
- Monochrome: 100%/70% opacity split. Correct.
- Size behavior: 16px uses single fill, 32px uses two-tone fills without internal line. Correct.
- Wordmark never rendered in gold. Correct.
- No prohibited treatments (rotation, shadow, glow, gradient, geometry animation). Correct.
- Mark SVGs include proper aria-label or aria-hidden attributes.

### 4. Spacing System
All spacing values use the 4px base scale tokens correctly (with the exception of the theme toggle noted in F5). Section padding, component gaps, and card padding all use the defined token scale. 12-column grid uses 24px gap (space-6). Layout demos show the specified asymmetric splits (3/9, 5/7).

### 5. Voice/Tone Examples
All six voice context examples match the brand narrative spec:
- Website hero: Terse, high-impact, no adjectives. Correct.
- CLI status: Factual, growth deltas in parentheses, terminates with "ready." Correct.
- Error message: Three-part structure (what, why, what to do), no apology. Correct.
- Changelog: Specific, measurable, migration path for breaking changes. Correct.
- Social: Specific pain, specific solution. Correct.
- Empty state: State fact, provide action, quiet encouragement. Correct.
- Copy button sequence: Copy, Copied, Remembered (1.5s delay). Matches personality spec.

### 6. Brand Guardrails
- No anthropomorphization of AI. Correct.
- No prohibited copy words ("revolutionary," "AI-powered," "cutting-edge," etc.). Correct.
- No exclamation marks in product voice. Correct.
- No visual trend-chasing (no gradient meshes, glassmorphism, neon). Correct.
- No pure black (#000) or pure white (#fff). Correct.
- No serif typefaces. Correct.
- No bounce or overshoot in motion curves. Correct.
- No icon-only navigation. Correct.
- Maker identity visible (version credit, consistent craft). Correct.
- Tagline used as constraint, not decoration. Correct.

### 7. Accessibility
- `prefers-reduced-motion` CSS rule with !important override. Correct.
- JS reduced-motion detection stops caustic animation. Correct.
- Theme toggle uses `role="radiogroup"` and `role="radio"` with `aria-checked`. Correct.
- Nav has `role="navigation"` and `aria-label="Primary"`. Correct.
- Decorative SVGs and canvases use `aria-hidden="true"`. Correct.
- Meaningful SVGs have `aria-label`. Correct.
- `lang="en"` on html element. Correct.
- Focus-visible styles defined on interactive elements. Correct.
- Light mode overrides: gold-interactive uses gold-700, focus-ring uses text-primary. Correct.

---

## Summary

| Severity | Count | Key Issue |
|----------|-------|-----------|
| Critical | 1 | Wrong font (Inter vs General Sans) |
| High | 2 | Lockup gap ratio, smooth scroll under reduced motion |
| Moderate | 3 | Focus offset, 2px spacing, gold inline code |
| Low | 2 | Favicon fallbacks, RAF loop optimization |

The page is a precise implementation of the brand system with one substitution error in the typeface. Fixing the font and the lockup gap brings it to full compliance. The remaining issues are polish items.

---

*Brand Guardian. 2026-03-15.*
*Review method: Line-by-line audit against brand guidelines v1.1, visual system v1.1, and accessibility audit.*
