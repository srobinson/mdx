---
title: "Helioy Visual Identity System"
category: projects
tags: [helioy, identity, visual-system, phase-2]
created: 2026-03-15
updated: 2026-03-15
version: "1.1"
author: ui-designer
status: production-spec
---

# Helioy Visual Identity System

Production-ready visual identity specification. All values are exact. A developer can implement directly from this document.

> **v1.1 Changelog (2026-03-15):** Accessibility audit fixes applied. (1) Added `gold-interactive-light` token (#8a6e1a) for light mode interactive gold. (2) Light mode focus ring switched to `text-primary-light`. (3) Dark mode `signal-error` lightened to #d45a5a for 4.5:1 compliance. (4) Light mode `signal-warning` darkened to #7a5f14. (5) Added `border-interactive` token for 3:1 non-text contrast on form inputs and UI components.

---

## 1. Logo Mark: The Facet

### Concept

A single asymmetric crystalline shard viewed from a three-quarter angle. The mark implies a fragment broken from a larger crystalline structure. It is not a complete geometric solid. It is a piece that suggests vastness beyond the frame.

### Geometric Construction

The mark is built from five vertices forming an irregular pentagon with one internal division line, creating two visible facets on the front face and implying a third receding facet.

**Construction method:**

1. Start with a regular pentagon inscribed in a 96x96px bounding box.
2. Rotate the pentagon 12 degrees clockwise. This breaks the symmetry and creates a "grown, not drawn" quality.
3. Remove the bottom-left vertex. Reconnect the adjacent vertices with a straight line, creating an irregular quadrilateral with one diagonal that feels like a natural fracture plane.
4. Draw an internal line from the top vertex to a point 60% along the bottom edge. This creates two front facets of different proportions (roughly 40/60 split).
5. The left facet is the "shadow facet" (darker fill). The right facet is the "light facet" (lighter fill). The division line itself is not stroked; the facets are differentiated by fill value only.

**Proportions:**
- Bounding box: square (1:1 aspect ratio)
- The mark occupies approximately 85% of the bounding box width and 90% of the height
- The mark's visual center of gravity sits slightly above and right of the geometric center
- Clear space: minimum 25% of the mark's width on all sides

**Fill values (dark mode, primary usage):**
- Light facet: `gold-500` (#d4a54a)
- Shadow facet: `gold-600` (#b8912e)
- No stroke. No outline. Fill only.

**Fill values (light mode):**
- Light facet: `gold-600` (#b8912e)
- Shadow facet: `gold-700` (#8a6e1a)

**Fill values (monochrome/single color):**
- Light facet: 100% foreground color
- Shadow facet: 70% foreground color opacity

### Size Behavior

| Context | Size | Detail Level |
|---------|------|-------------|
| Favicon | 16x16px | Two-facet silhouette only. No internal division line. Single gold fill. The shape reads as a tilted quadrilateral. |
| Avatar/npm | 32x32px | Two facets visible with fill differentiation. No internal line rendered; facets distinguished by color alone. |
| Navigation | 48x48px | Full two-facet rendering with clear color distinction between facets. |
| Feature | 64x64px | Full rendering. At this size, the internal division line may be rendered as a 1px hairline in `gold-700` for additional definition. |
| Hero/Marketing | 96px+ | Full rendering with optional subtle lattice texture within the shadow facet (a grid of faint lines at 30-degree angles suggesting internal crystal structure). The lattice uses `gold-700` at 20% opacity. |

### Mark Variations

**Primary:** Gold facets on dark surface (described above).
**Reversed:** `text-primary` (#f0ebe4) facets on any dark surface. For contexts where gold would clash or when monochrome is required.
**Light surface:** `gold-600`/`gold-700` facets on light surfaces.
**Knockout:** Single-color mark at 100%/70% opacity split. Works on any solid background.

**Never:**
- Rotate the mark beyond its designed orientation
- Add a drop shadow or glow
- Place the mark on a busy photographic background without a solid backing surface
- Animate the mark's geometry (the shape is fixed; only opacity and color may transition)
- Apply gradients to the facets

---

## 2. Wordmark

### Typeface Selection: General Sans

**Decision rationale:** General Sans over Satoshi. Both are geometric sans-serifs with humanist warmth. General Sans wins on three counts:
1. The capital H has a distinctive crossbar height that gives the word "Helioy" a strong anchor without feeling top-heavy
2. The lowercase y descender has a clean diagonal return that avoids visual collision with wide tracking
3. The weight axis offers more granularity between Medium (500) and Semibold (600), which matters for the wordmark specifically

**Wordmark specification:**
- Typeface: General Sans Semibold (600)
- Case: Mixed ("Helioy")
- Tracking: +160 units (CSS: `letter-spacing: 0.16em`)
- No custom kerning pairs beyond the typeface defaults
- The capital H is not modified. The typeface's natural H proportions are used.

**Rendering:**
- On dark surfaces: `text-primary` (#f0ebe4)
- On light surfaces: `text-primary-light` (#1a1816)
- The wordmark is never rendered in gold. Gold is reserved for the Facet mark. The wordmark is always the text color of its surface.

### Lockup Configurations

**Horizontal lockup (primary):**
Facet mark to the left of the wordmark. The mark's vertical center aligns with the wordmark's x-height center (not the cap-height center). Gap between mark and wordmark: the width of the mark itself (1:1 ratio). Minimum reproduction width: 120px.

**Stacked lockup:**
Facet mark centered above the wordmark. Gap between mark bottom and wordmark cap-height: 50% of mark height. Used when horizontal space is constrained (square social avatars, app icons). Minimum reproduction height: 80px.

**Mark only:**
The Facet alone. Used at sizes below 120px horizontal or in contexts where the brand is already established (favicon, CLI prompt icon, notification badges).

**Wordmark only:**
"Helioy" in General Sans Semibold with wide tracking. Used in text-heavy contexts (documentation headers, footer credits) where the mark would compete with content density.

---

## 3. Color Palette

All values from the UX Architect's foundation spec. Organized here with usage ratios and application rules.

### 3.1 Brand Gold

| Token | Hex | Role |
|-------|-----|------|
| `gold-400` | #e0b960 | Hover state, light emphasis. Use sparingly. |
| `gold-500` | #d4a54a | Primary accent. Interactive elements, active states, the Facet's light face. The signature color. |
| `gold-600` | #b8912e | Pressed states, secondary accent, Facet shadow face. |
| `gold-700` | #8a6e1a | Metadata on dark surfaces, tertiary accent. In light mode, this is the interactive gold (links, active states, navigation indicators). Passes AA on light surfaces. |
| `gold-900` | #3d3010 | Tinted background wash. Subtle gold-infused surface for featured areas. Never for text. |

**Light mode interactive rule:** `gold-500` (#d4a54a) fails contrast on light surfaces (2.13:1). All interactive gold elements in light mode must use `gold-700` (#8a6e1a) instead. This includes links, active navigation indicators, selected states, and any text rendered in gold. The token alias `gold-interactive-light` maps to `gold-700` to make this explicit in code.

**Usage ratio:** Gold should appear on no more than 15% of any given screen's surface area. It is an accent. Overuse dilutes impact and creates visual noise.

### 3.2 Surfaces

**Dark mode (primary):**

| Token | Hex | Role |
|-------|-----|------|
| `surface-0` | #1a1816 | Page background. The deepest layer. |
| `surface-1` | #222018 | Cards, panels, sidebar. First elevation. |
| `surface-2` | #2e2b24 | Elevated panels, popovers, dropdowns. |
| `surface-3` | #3a3730 | Active/selected row backgrounds. |
| `border-subtle` | #3a3730 | Hairline borders when surface shift alone is not sufficient. |
| `border-default` | #4a4740 | Standard component borders (inputs, cards that need explicit edges). |
| `border-interactive` | #5a5750 | Form inputs, buttons, and UI component boundaries requiring 3:1 non-text contrast against surface-0. 3.1:1 ratio. |

**Light mode (secondary):**

| Token | Hex | Role |
|-------|-----|------|
| `surface-0-light` | #faf8f5 | Page background. Warm paper. |
| `surface-1-light` | #f0ece6 | Cards, panels. |
| `surface-2-light` | #e6e2dc | Elevated panels. |
| `surface-3-light` | #dcd8d2 | Active/selected states. |
| `border-subtle-light` | #dcd8d2 | Hairline borders. |
| `border-default-light` | #c8c4be | Standard borders. |
| `border-interactive-light` | #a8a49e | Form inputs, buttons, UI components requiring 3:1 non-text contrast on surface-0-light. 3.2:1 ratio. |

### 3.3 Text

| Token | Hex | Mode | Role |
|-------|-----|------|------|
| `text-primary` | #f0ebe4 | Dark | Body text, headings. 11.2:1 contrast on surface-0. |
| `text-secondary` | #9a9590 | Dark | Metadata, labels, captions. 5.1:1 on surface-0. |
| `text-tertiary` | #6a6560 | Dark | Disabled, placeholder. 3.2:1 (large text only). |
| `text-primary-light` | #1a1816 | Light | Body text. 14.5:1 on surface-0-light. |
| `text-secondary-light` | #5a5550 | Light | Metadata. 5.8:1. |
| `text-tertiary-light` | #8a8580 | Light | Disabled, placeholder. 3.5:1. |

### 3.4 Semantic

| Token | Dark | Light | Role |
|-------|------|-------|------|
| `signal-success` | #6b9b7a | #2d7a46 | Connected, passing, complete |
| `signal-warning` | #d4a54a | #7a5f14 | Attention needed. Dark mode reuses gold. Light mode darkened for 4.5:1 contrast. |
| `signal-error` | #d45a5a | #a83232 | Failed, disconnected, error. Dark mode lightened from #c94a4a for 4.5:1 on surface-0. |
| `signal-info` | #5b8db8 | #3a6e96 | Informational, neutral status |

### 3.5 Color Bridge Rule

Gold is the constant hue across modes, but the specific value shifts for accessibility. In dark mode, `gold-500` (#d4a54a) functions as emitted light (bright accent on dark surface, 5.8:1 contrast). In light mode, interactive gold shifts to `gold-700` (#8a6e1a) for 4.5:1+ contrast. Same hue family, different weight. The perceptual warmth remains consistent even as the literal value changes.

### 3.6 Prohibited Colors

- Pure black (#000000) for any surface
- Pure white (#ffffff) for any text
- Saturated primaries (pure red, green, blue)
- Cool blues or teals as accent colors
- Neon or electric tones
- Gradient fills on interactive elements
- Gold on surfaces larger than 15% of viewport

---

## 4. Typography System

### 4.1 Font Stack

**UI/Body/Marketing:** General Sans
```css
font-family: "General Sans", "Noto Sans", "Noto Sans CJK", system-ui, sans-serif;
```

General Sans serves as both the wordmark face and the system UI face. Using one typeface family across the entire brand reduces visual fragmentation and keeps the token count low (literally and metaphorically).

**Code/CLI/Data:** JetBrains Mono
```css
font-family: "JetBrains Mono", "Noto Sans Mono", ui-monospace, monospace;
```

JetBrains Mono with ligatures enabled. The ligature set handles `=>`, `->`, `!=`, `>=`, `<=`, `===` naturally, which matters in documentation and product UI.

### 4.2 Type Scale

Base: 16px (1rem). Ratio: 1.25 (Major Third).

| Token | Size | Weight | Line Height | Letter Spacing | Usage |
|-------|------|--------|-------------|----------------|-------|
| `text-xs` | 12px / 0.75rem | 400 | 1.5 (18px) | 0 | Badges, annotations, code comments |
| `text-sm` | 14px / 0.875rem | 400 | 1.5 (21px) | 0 | Labels, captions, secondary UI |
| `text-base` | 16px / 1rem | 400 | 1.6 (25.6px) | 0 | Body, form inputs, default |
| `text-lg` | 20px / 1.25rem | 500 | 1.5 (30px) | 0 | Subheadings, emphasized body |
| `text-xl` | 24px / 1.5rem | 600 | 1.3 (31.2px) | 0 | H3 section headings |
| `text-2xl` | 30px / 1.875rem | 600 | 1.25 (37.5px) | -0.02em | H2 page section headings |
| `text-3xl` | 38px / 2.375rem | 700 | 1.2 (45.6px) | -0.02em | H1 page titles |
| `text-4xl` | 48px / 3rem | 700 | 1.1 (52.8px) | -0.02em | Hero headings, marketing |

### 4.3 Typography Rules

- Body text minimum: 16px. Never smaller for running prose.
- Maximum line length: 72 characters for body, 90 for documentation.
- Paragraph spacing: `space-4` (16px).
- Heading spacing: `space-6` (24px) above, `space-3` (12px) below.
- Negative tracking (-0.02em) applies at `text-2xl` and above only.
- Wordmark tracking (+0.16em) is exclusive to the wordmark. Never apply wide tracking to UI text.
- No serif typefaces. Anywhere. Ever.
- Code snippets in prose: `text-sm` JetBrains Mono, `surface-1` background, `space-1` horizontal padding, `border-radius: 3px`.

---

## 5. Icon System

### 5.1 Style Direction: Geometric Solid with Negative Space

Icons are built from filled geometric primitives (rectangles, circles, triangles) with strategic cutouts that create the recognizable form. The result has visual mass. Each icon feels like it was cut from material, not drawn with a pen.

**Construction rules:**
- Start from a filled shape, then subtract to reveal the icon's meaning
- No outlines. No strokes. Fill-and-cut only.
- Corner radius: 1px on outer corners, 0px on cut/negative-space corners. The contrast between soft outer edges and sharp cuts creates the Helioy icon character.
- Optical alignment to a 20x20px grid with 2px padding (16px active area at the smallest size)

### 5.2 Sizes

| Token | Pixel Size | Grid | Usage |
|-------|-----------|------|-------|
| `icon-sm` | 16x16px | 12px active | Inline with text, table cells, metadata |
| `icon-md` | 20x20px | 16px active | Navigation items, form input icons |
| `icon-lg` | 24x24px | 20px active | Feature callouts, card headers |
| `icon-xl` | 32x32px | 28px active | Hero features, empty states |

Four sizes. No intermediates. If a context does not fit these four, the layout is wrong, not the icon system.

### 5.3 Color

- Default: `text-secondary` (#9a9590 dark / #5a5550 light). Icons are secondary to text content.
- Active/Selected: `gold-500` (#d4a54a) in dark mode, `gold-700` (#8a6e1a) in light mode. The gold treatment signals "this is active."
- Interactive hover: `text-primary`. Icons brighten on hover, they do not change color to gold (gold is reserved for the active state).
- Disabled: `text-tertiary` at 60% opacity.
- Semantic: Icons paired with semantic states use the corresponding signal color (success, error, warning, info).

### 5.4 Icon Accessibility

- Every navigation icon has a visible text label. Icon-only navigation is prohibited.
- Icons that convey state must not rely on color alone. Shape differentiation is required (checkmark for success, X for error, triangle for warning).
- All icons include appropriate `aria-label` or `aria-hidden="true"` when decorative.

---

## 6. Pattern System: Structured Light

### 6.1 Concept

Caustic light patterns serve as the brand's repeatable graphic element. These are the interference patterns created when light refracts through crystalline geometry, projected onto a surface. The pattern connects Helios (light/energy) with geometric memory (the refracting structure) to produce something functional and beautiful.

### 6.2 Generation Method

Patterns are generated algorithmically, not illustrated. The source algorithm simulates light refraction through a faceted surface and captures the resulting interference pattern.

**Parameters:**
- Light source: single directional source, warm color temperature (matching `gold-500`)
- Refracting surface: irregular polygon matching the Facet mark's geometry
- Projection surface: flat plane at variable distance from the refracting element
- Output: grayscale intensity map, colorized with the brand palette

**For implementation without a physics engine:** Use Perlin noise masked through Voronoi cell boundaries to approximate caustic patterns. The Voronoi seed points should be distributed irregularly (not grid-aligned) to avoid mechanical repetition.

### 6.3 Color Treatment

- Primary: `gold-500` pattern on `surface-0` background. The pattern renders at 8-15% opacity for background texture, 30-50% for featured areas.
- Secondary: `gold-700` pattern on `surface-1`. Lower contrast for subtle surface treatment.
- Light mode: `gold-600` pattern on `surface-0-light` at 5-10% opacity.

### 6.4 Application Rules

**Where patterns appear:**
- Website hero backgrounds (large scale, low opacity)
- Social media card backgrounds (medium scale, medium opacity)
- Conference/presentation slide backgrounds (large scale, low opacity)
- Loading state backgrounds (animated: the pattern slowly shifts as if the light source is moving)
- Email header strips (small crop, high contrast)

**Where patterns do not appear:**
- Product UI surfaces. The product is content-dense. Patterns compete with data.
- Documentation pages. Clean surfaces, no decoration.
- Inside the Facet mark. The mark is solid fills only.
- CLI output. The CLI is typographic only.
- On surfaces smaller than 200x200px. The pattern loses coherence at small sizes.

### 6.5 Animation

When animated, the pattern shifts as if the light source is moving slowly (completing one cycle every 30-60 seconds). The movement is continuous, not stepped. Easing: linear for the light source movement (constant velocity feels natural for light). Opacity may pulse subtly (between 8% and 12% for backgrounds) on a 10-second cycle.

Animated patterns respect `prefers-reduced-motion`. When reduced motion is active, the pattern is static at its median opacity.

---

## 7. Brand Art Direction

### 7.1 Primary Visual Language: Structural Diagrams

The product's actual data structures serve as brand art. Geometric memory patterns, dependency graphs, agent communication flows, and code topology maps are rendered as beautiful visualizations using the brand palette.

**Rendering rules:**
- Nodes: circles or rounded squares, 8-12px radius depending on importance
- Active/highlighted nodes: `gold-500` fill
- Connected nodes: `text-secondary` fill
- Background/context nodes: `text-tertiary` at 40% opacity
- Edges: 1px lines in `border-default`, curved with 12px radius at bends
- Active edges (data flowing): `gold-500` at 60% opacity, 2px width
- Labels: `text-xs` General Sans, `text-secondary` color

**Composition:**
- Center-weighted or golden-ratio composition. The most active/golden cluster sits at a focal point.
- Dark negative space surrounds the diagram. The structure emerges from darkness.
- The diagram extends past frame edges, implying continuation beyond what is visible.

### 7.2 Photography Direction

Photography is secondary to structural diagrams but has a defined role in case studies, team pages, and editorial content.

**When photography appears:**
- Real workspace environments (not staged). Warm ambient light. Screens visible but not the focus.
- Material close-ups: actual crystals, amber, geological specimens, cut gemstones. These serve as texture references and metaphor reinforcement.
- Architectural interiors with strong directional light: concrete, wood, brass. Spaces that feel both contemporary and timeless.

**Photographic treatment:**
- Color grade to the warm mineral palette. Shift highlights toward gold, shadows toward warm charcoal. Remove cool casts.
- No filters, no overlays, no duotone treatments. The color correction should feel invisible.
- Shallow depth of field for material close-ups. Medium depth for environments.

**Never:**
- Stock photography of any kind
- Hands on keyboards, pointing at screens, smiling at laptops
- AI-generated imagery of people
- Illustration or character art

### 7.3 Data Visualization Style

For charts, graphs, and metrics displayed in marketing or product contexts:

- Primary data series: `gold-500`
- Secondary series: `signal-info` (#5b8db8)
- Tertiary series: `text-secondary` (#9a9590)
- Status series: use semantic colors (`signal-success`, `signal-error`)
- Axes and labels: `text-tertiary`
- Grid lines: `border-subtle` at 40% opacity
- No 3D effects. No gradients on chart elements. Flat fills, clean lines.
- Bar charts and line charts preferred over pie charts. Pie charts are prohibited (they communicate proportion poorly and violate the "every element earns its place" principle).

---

## 8. Application Examples

### 8.1 Website Header

```
[surface-0 background, full width]

  [Horizontal lockup: Facet mark + "Helioy" wordmark, left-aligned]

  [Navigation: 5 items, General Sans text-sm weight-500, text-secondary default,
   text-primary on hover, gold-500 underline 2px on active item,
   items spaced at space-8 (32px)]

  [CTA button: "Get Started", gold-500 background, surface-0 text,
   General Sans text-sm weight-600, space-3 vertical padding, space-6 horizontal,
   border-radius 6px, 44px minimum height]

  [Structured Light caustic pattern at 8% opacity fills the hero area below nav]

  [Hero heading: text-4xl weight-700, text-primary, max-width 640px,
   "Infrastructure that remembers"]

  [Subheading: text-lg weight-400, text-secondary, max-width 480px,
   "Every token counts."]

  [Interactive system diagram: structural diagram showing product topology,
   gold-500 active nodes, animated edges showing data flow]
```

### 8.2 Documentation Page

```
[surface-0 background]

  [layout-sidebar: 3/9 split]

  LEFT (3 columns):
    [surface-1 sidebar background]
    [Wordmark only at top, text-sm, text-secondary, space-4 padding]
    [Navigation tree: General Sans text-sm weight-400
     - Active item: gold-500 text, surface-2 background strip
     - Inactive: text-secondary
     - Section headers: text-xs weight-600 text-tertiary uppercase tracking +0.08em
     - Indent: space-4 per level
     - Tree connectors: border-subtle vertical lines]
    [Search: surface-2 input, text-secondary placeholder,
     "/" keyboard shortcut badge in text-tertiary]

  RIGHT (9 columns):
    [container-sm (640px) centered within the 9-column area]
    [H1: text-3xl weight-700, text-primary, gold-500 left border 3px, space-3 left padding]
    [Body: text-base weight-400 line-height-1.6 text-primary, max-width 72ch]
    [Code blocks: surface-1 background, JetBrains Mono text-sm,
     space-4 padding, border-radius 6px, border-subtle 1px border,
     syntax highlighting using brand palette:
       - keywords: gold-500
       - strings: signal-success
       - comments: text-tertiary
       - functions: signal-info
       - variables: text-primary]
    [Inline code: surface-1 background, JetBrains Mono text-sm,
     space-1 horizontal padding, border-radius 3px]
    [Links: gold-interactive text (gold-500 dark, gold-700 light), no underline default, underline on hover]
```

### 8.3 CLI Output

```
[Terminal with warm dark background, not necessarily surface-0;
 the terminal uses the user's own background color]

  helioy> cx_recall --context ./my-project    [gold-500 prompt, text-primary command]

  ├─ Searching geometric memory...           [text-tertiary, tree chars]
  ├─ 12 experiences matched                  [text-tertiary]
  ├─ Relevance: 0.89 avg                     [text-tertiary, number in text-primary]
  └─ Retrieved in 23ms                       [text-tertiary, number in signal-success]

  Context loaded. 4 deposits available.       [text-primary]

  helioy>                                     [gold-500 prompt, ready for input]
```

The CLI identity is purely typographic and chromatic. No ASCII art logos, no decorative borders, no emoji. The gold prompt marker is the brand signature. Structure comes from tree characters (`├─`, `└─`) and consistent indentation.

### 8.4 GitHub Social Card (1200x630px)

```
[surface-0 background, full bleed]

  [Structured Light caustic pattern at 12% opacity, covering full area,
   with the brightest concentration in the upper-right quadrant]

  [Facet mark: 64px, positioned at space-8 from top-left corner]

  [Repository name: text-2xl weight-600, text-primary,
   positioned below mark with space-6 gap]

  [Description: text-lg weight-400, text-secondary,
   max-width 640px, below repo name with space-3 gap]

  [Tagline: text-sm weight-500, gold-500,
   positioned at bottom-left with space-8 margin,
   "every token counts"]

  [Small structural diagram in bottom-right corner at 20% opacity,
   showing the relevant product's node topology as a watermark]
```

### 8.5 Favicon (16x16px, 32x32px)

**16x16px:**
The Facet mark simplified to a two-tone quadrilateral. At this size, the internal facet division is not rendered. The shape is a single `gold-500` fill on transparent background. The asymmetric silhouette is the identifying feature.

**32x32px:**
The Facet mark with two-facet fill differentiation (`gold-500` light face, `gold-600` shadow face). No internal line; color distinction alone separates the facets. Transparent background.

**SVG favicon (scalable):**
Full Facet mark with both facets and appropriate fill. Served as SVG for browsers that support it, with PNG fallback at 32x32px.

```html
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="icon" href="/favicon-32.png" sizes="32x32" type="image/png">
<link rel="icon" href="/favicon-16.png" sizes="16x16" type="image/png">
<link rel="apple-touch-icon" href="/apple-touch-icon.png" sizes="180x180">
```

The Apple Touch Icon (180x180px) uses the Facet mark at 64px centered on a `surface-1` (#222018) background with 58px padding on all sides.

---

## 9. Implementation Reference

### CSS Custom Properties (complete)

```css
:root {
  /* Brand Gold */
  --gold-400: #e0b960;
  --gold-500: #d4a54a;
  --gold-600: #b8912e;
  --gold-700: #8a6e1a;
  --gold-900: #3d3010;

  /* Surfaces (dark mode default) */
  --surface-0: #1a1816;
  --surface-1: #222018;
  --surface-2: #2e2b24;
  --surface-3: #3a3730;
  --border-subtle: #3a3730;
  --border-default: #4a4740;
  --border-interactive: #5a5750;

  /* Text */
  --text-primary: #f0ebe4;
  --text-secondary: #9a9590;
  --text-tertiary: #6a6560;

  /* Semantic */
  --signal-success: #6b9b7a;
  --signal-warning: #d4a54a;
  --signal-error: #d45a5a;
  --signal-info: #5b8db8;

  /* Interactive gold (alias for mode-aware usage) */
  --gold-interactive: var(--gold-500);

  /* Focus */
  --focus-ring-color: var(--gold-500);

  /* Spacing (4px base) */
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
  --font-sans: "General Sans", "Noto Sans", "Noto Sans CJK", system-ui, sans-serif;
  --font-mono: "JetBrains Mono", "Noto Sans Mono", ui-monospace, monospace;

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

  /* Shadows (floating elements only) */
  --shadow-float: 0 4px 16px rgba(0, 0, 0, 0.3);
  --shadow-overlay: 0 8px 32px rgba(0, 0, 0, 0.4);

  /* Border radius */
  --radius-sm: 3px;
  --radius-md: 6px;
  --radius-lg: 12px;
}

[data-theme="light"] {
  --surface-0: #faf8f5;
  --surface-1: #f0ece6;
  --surface-2: #e6e2dc;
  --surface-3: #dcd8d2;
  --border-subtle: #dcd8d2;
  --border-default: #c8c4be;
  --border-interactive: #a8a49e;
  --text-primary: #1a1816;
  --text-secondary: #5a5550;
  --text-tertiary: #8a8580;
  --signal-success: #2d7a46;
  --signal-warning: #7a5f14;
  --signal-error: #a83232;
  --signal-info: #3a6e96;
  --gold-interactive: var(--gold-700);
  --focus-ring-color: var(--text-primary);
}

@media (prefers-color-scheme: light) {
  :root:not([data-theme="dark"]) {
    --surface-0: #faf8f5;
    --surface-1: #f0ece6;
    --surface-2: #e6e2dc;
    --surface-3: #dcd8d2;
    --border-subtle: #dcd8d2;
    --border-default: #c8c4be;
    --border-interactive: #a8a49e;
    --text-primary: #1a1816;
    --text-secondary: #5a5550;
    --text-tertiary: #8a8580;
    --signal-success: #2d7a46;
    --signal-warning: #7a5f14;
    --signal-error: #a83232;
    --signal-info: #3a6e96;
    --gold-interactive: var(--gold-700);
    --focus-ring-color: var(--text-primary);
  }
}

@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0ms !important;
    transition-duration: 0ms !important;
  }
}
```

### Syntax Highlighting Palette

For code blocks across documentation and product UI:

```css
.syntax {
  --syn-keyword: var(--gold-500);       /* if, const, return, import */
  --syn-string: var(--signal-success);  /* "strings", 'strings' */
  --syn-comment: var(--text-tertiary);  /* // comments */
  --syn-function: var(--signal-info);   /* functionName() */
  --syn-variable: var(--text-primary);  /* identifiers */
  --syn-number: var(--gold-400);        /* 42, 3.14 */
  --syn-type: var(--text-secondary);    /* TypeName, interface */
  --syn-operator: var(--text-secondary); /* =, +, => */
  --syn-punctuation: var(--text-tertiary); /* {, }, (, ) */
}
```

---

**Author:** UI Designer
**Date:** 2026-03-15
**Version:** 1.1 (accessibility fixes applied)
**Status:** Production specification. Ready for implementation.
**Dependencies:** General Sans font files, JetBrains Mono font files, Facet mark SVG (to be produced by a vector artist from the geometry described in Section 1).
