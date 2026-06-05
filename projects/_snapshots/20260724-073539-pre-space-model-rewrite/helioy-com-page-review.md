---
title: "Helioy Landing Page (helioy.com): Brand Review"
category: projects
tags: [helioy, identity, brand-review, landing-page]
created: 2026-03-15
author: brand-guardian
status: review-complete
reviewed_file: /Users/alphab/Dev/LLM/DEV/helioy/identity/helioy.com.html
---

# Helioy Landing Page: Brand Review

Reviewer: Brand Guardian
Source: `/Users/alphab/Dev/LLM/DEV/helioy/identity/helioy.com.html`
Reviewed against: `helioy-identity-brand-guidelines.md` v1.1

---

## Verdict

This is strong work. The voice is precise, the structure is clean, and the page communicates Helioy's value in the brand's register without any marketing bloat. Two structural issues need attention: missing focus-visible styles (accessibility) and lockup gap ratios. The rest is polish.

---

## Issues Found

### CRITICAL

**L1. No focus-visible styles anywhere on the page**
No `:focus-visible` or focus outline is defined for any interactive element. Links, buttons, the nav CTA, and the hero CTAs are all invisible to keyboard users. The `--focus-ring-color` custom property is not defined in the CSS.

**Fix:** Add to CSS:
```css
:root {
  --focus-ring-color: var(--gold-500);
}

a:focus-visible, button:focus-visible {
  outline: 2px solid var(--focus-ring-color);
  outline-offset: 2px;
}
```

---

### HIGH

**L2. Hero lockup gap violates 1:1 ratio**
The hero lockup uses `gap: var(--space-6)` (24px) with a 56px mark. The brand spec requires the gap to equal the mark width. Expected: 56px.

- **Line 138:** `gap: var(--space-6);`

**Fix:** Change to a value matching the mark width. Since 56px is not a spacing token, either:
- Use a 48px mark with `gap: var(--space-12)` (48px)
- Or use a 64px mark with `gap: var(--space-16)` (64px)
- Or keep 56px and set `gap: 56px` as a one-off (lockup gaps are component-specific, not general spacing)

**L3. Nav lockup gap is 12px with a 24px mark (0.5:1)**

- **Line 90:** `gap: var(--space-3);`

**Fix:** Change to `gap: var(--space-6)` (24px) for 1:1 ratio with the 24px mark.

---

### MODERATE

**L4. Three font sizes fall outside the type scale**

| Element | Size Used | Nearest Token |
|---------|-----------|---------------|
| Nav wordmark (line 95) | 1.125rem (18px) | text-base (16px) or text-lg (20px) |
| Hero wordmark (line 144) | 2.5rem (40px) | text-3xl (38px) or text-4xl (48px) |
| What-diagram (line 257) | 0.8125rem (13px) | text-xs (12px) or text-sm (14px) |

The type scale exists to prevent exactly this kind of drift. Every custom size is a future inconsistency.

**Fix:**
- Nav wordmark: Use `text-lg` (1.25rem / 20px). The extra tracking compensates for the size increase.
- Hero wordmark: Use `text-3xl` (2.375rem / 38px) or `text-4xl` (3rem / 48px).
- What-diagram: Use `text-sm` (0.875rem / 14px) for readability, or `text-xs` (0.75rem / 12px) if treating as annotation.

---

**L5. Nav CTA min-height is 40px, spec says 44px**

- **Line 111:** `min-height: 40px;`

The brand spec application example defines CTAs as "44px minimum height." 44px is also the WCAG 2.2 recommended minimum touch target.

**Fix:** Change to `min-height: 44px;`

---

**L6. Link hover uses underline-style box-shadow**

- **Line 73:** `a:hover { box-shadow: 0 1px 0 0 var(--gold-500); }`

The brand spec says "Warm glow via box-shadow, not underline." A 1px bottom box-shadow reads as an underline. The personality spec describes hover states as "warm glow."

**Fix:** Use a diffused glow instead:
```css
a:hover { box-shadow: 0 0 0 1px var(--gold-700); }
```
Or simply rely on the color shift (gold on hover is already a sufficient signal).

---

### LOW

**L7. Nav missing aria-label**

- **Line 385:** `<nav class="nav">` has no `aria-label`

**Fix:** Add `aria-label="Primary"` for disambiguation.

---

**L8. Footer mark at 20px uses two-facet rendering**
The spec says 16px gets single-fill silhouette, 32px gets two-facet. 20px falls between. At this size on standard displays, the gold-600/gold-500 distinction is imperceptible.

- **Line 560:** `width="20" height="20"`

**Fix:** Either increase to 24px (closer to 32px behavior) or use single-fill silhouette:
```html
<svg width="20" height="20" viewBox="0 0 96 96" aria-hidden="true">
  <path d="M36 12 L12 52 L48 88 L78 78 L88 32 Z" fill="#d4a54a"/>
</svg>
```

---

**L9. Missing og:image meta tag**
Social sharing will show no image preview. The brand spec defines a GitHub social card format (1200x630px).

**Fix:** Add `<meta property="og:image" content="[url-to-social-card]">` once the asset is produced.

---

## Passed Checks

### Color Values
All CSS custom properties match the brand spec. Gold scale (400-900), surfaces (0-3), text hierarchy (primary/secondary/tertiary), borders (subtle/default), and semantic colors (success, info) are correct. The `--gold-interactive` alias correctly points to `var(--gold-500)`.

Note: This page operates in dark mode only. No light mode overrides are present. This is acceptable for a v1 landing page if light mode is not yet supported.

### Typography
General Sans loaded via Fontshare CDN. JetBrains Mono via Google Fonts. Font fallback chains include Noto Sans CJK. Type scale sizes, weights, line heights, and letter-spacing values match the spec at all standard scale stops. Negative tracking correctly applied at text-2xl and above. Wordmark tracking at 0.16em.

### Logo Usage
Facet mark uses correct production paths (`M36 12 L12 52 L48 88 Z` / `M36 12 L88 32 L78 78 L48 88 Z`) and correct fills (gold-600 shadow, gold-500 light). Wordmark rendered in text-primary, never gold. Favicon SVG linked correctly.

### Voice & Tone
Outstanding. Every section follows the brand voice principles:

- **"Agents that remember."** Terse, high-impact. Three words. The approved hero register.
- **"5 calls replace 30 file reads."** Specific, measurable. Numbers over adjectives.
- **"Context compounds instead of evaporating."** Shows the mechanism.
- **Product card questions** ("What does the agent already know?") frame each tool from the user's perspective. Effective.
- **Philosophy tenets** are direct, structural, free of marketing language. "Tokens are a strict budget" is excellent brand voice.
- **No prohibited copy:** No "revolutionary," "AI-powered," "cutting-edge," "leverage," no exclamation marks, no anthropomorphization beyond approved functional descriptions.

### Brand Guardrails
- No pure black/white. No saturated primaries. No cool accents. No neon.
- No gradients on interactive elements. No bounce/overshoot in motion.
- No serif typefaces. Body text at 16px minimum.
- Product names are lowercase, descriptive, human.
- No "AI platform" or "autonomous agents" territory language.
- No stock imagery, AI people, or illustrations.
- Maker identity visible through craft quality.

### Accessibility (partial)
- `lang="en"` on html element.
- `prefers-reduced-motion` CSS rule with scroll-behavior auto. Correct.
- Caustic canvas: adaptive step, throttled RAF, single render under reduced motion. Correct.
- Decorative SVGs use `aria-hidden="true"`. Hero mark has `aria-label`.
- CTA buttons have sufficient color contrast (dark on gold-500: 7.82:1).

---

## Summary

| Severity | Count | Key Issue |
|----------|-------|-----------|
| Critical | 1 | No focus-visible styles (keyboard users cannot navigate) |
| High | 2 | Lockup gap ratios (hero and nav) |
| Moderate | 3 | Off-scale font sizes, nav CTA height, link hover style |
| Low | 3 | Nav aria-label, footer mark size, missing og:image |

The voice and visual execution are the best implementation of the brand I have reviewed. The landing page communicates with the precision the brand promises. The focus-visible omission is the only item that requires immediate attention.

---

*Brand Guardian. 2026-03-15.*
*Review method: Line-by-line audit against brand guidelines v1.1.*
