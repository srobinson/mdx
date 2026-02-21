# AskSLM Technical & SEO Audit

**URL**: https://www.askslm.com/
**Audit date**: 2026-02-22
**Last-Modified header**: Wed, 31 Dec 2025 16:56:44 GMT

---

## Executive Summary

askslm.com is a single-page static HTML site hosted on Cloudflare Pages. It
has no JavaScript framework, no build system, no CMS --- just hand-written
HTML + CSS + a 41-line vanilla JS file. The content is strong but the
technical SEO foundation is severely underdeveloped: no Open Graph tags, no
structured data, no sitemap depth, no separate indexable pages, a single
`<h1>`, duplicate `id` attributes, missing HTTPS redirect from HTTP, and a
contact form that submits to nowhere. The site would benefit enormously from a
rebuild that separates content into distinct pages, adds proper metadata, and
fixes the many HTML quality issues documented below.

**Overall grade: D+** --- good content wrapped in a technically deficient
delivery vehicle.

---

## 1. Technical SEO

### 1.1 Meta Tags

| Tag                         | Present | Value                                                                                                                                                 | Assessment                                                                       |
| --------------------------- | ------- | ----------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------- |
| `<title>`                   | Yes     | `AskSLM \| Private AI for Regulated Enterprises`                                                                                                      | Good. 49 chars --- within 50-60 sweet spot. Pipe separator is fine.              |
| `<meta name="description">` | Yes     | `AskSLM delivers fast, private, domain-specific AI answers using Small Language Models (SLMs), optimized for edge and local AI deployments.`          | 138 chars --- good length (under 155). Could be more action-oriented with a CTA. |
| `<meta name="keywords">`    | Yes     | `AskSLM, edge AI, local AI, SLM, small language models, domain specific AI, private AI, on-device AI, enterprise AI assistant, AI question answering` | Google ignores this tag entirely. Not harmful but not helpful.                   |
| `<meta name="robots">`      | Yes     | `index, follow`                                                                                                                                       | Default behavior --- technically redundant but not harmful.                      |
| `<meta name="viewport">`    | Yes     | `width=device-width, initial-scale=1.0`                                                                                                               | Correct.                                                                         |
| `<meta charset>`            | Yes     | `UTF-8`                                                                                                                                               | **Duplicated on lines 4 and 10.** Remove the duplicate.                          |

**Missing meta tags:**

- `og:title` --- no Open Graph title
- `og:description` --- no Open Graph description
- `og:image` --- no Open Graph image (critical for LinkedIn/Twitter sharing)
- `og:url` --- no Open Graph URL
- `og:type` --- no Open Graph type
- `og:site_name` --- no Open Graph site name
- `twitter:card` --- no Twitter Card markup
- `twitter:title` --- no Twitter title
- `twitter:description` --- no Twitter description
- `twitter:image` --- no Twitter image
- `theme-color` --- no browser theme color for mobile

**Impact**: When anyone shares askslm.com on LinkedIn, Twitter, or Slack, it
will render as a plain text link with no preview image, no title card, and no
description. For a B2B enterprise sales site, this is a significant missed
opportunity.

### 1.2 Heading Structure

```
H1: "Local Private AI. On Your Terms." (line 65) --- ONLY H1 on the page
H2: "The Problem: Why Current AI Fails High-Value Markets" (line 96)
H2: "AskSLM's proprietary value" (line 151)
H2: "Competitive Positioning" (line 181)
H2: "Secure SLM Platform" (line 250)
H2: "AI Inference Engine" (line 291)
H2: "SLM Marketplace" (line 345)
H2: "User-Friendly Training & Knowledge Updates" (line 400)
H2: "On-Premise Deployment, Simplified" (line 450)
H2: "Security & Compliance by Design" (line 500)
H2: "Solutions for Regulated Industries" (line 625)
H2: "Real-World Use Scenarios" (line 720)
H2: "Team" (line 993)
H2: "Development Philosophy" (line 1168)
H2: "Bring the Future of Secure, Local AI Into Your Organization" (line 1213)
H3: (approx 35+ H3 tags for subsections, cards, use cases)
H4: Footer column headings (Platform, Solutions, Resources, Company)
```

**Assessment**: Single H1 is correct. H2/H3 hierarchy is mostly logical. The
sheer volume of H2 sections (15) on a single page dilutes SEO signal --- each
would be stronger as its own indexed page. H4 usage in footer is semantically
appropriate.

### 1.3 Canonical URL

```html
<link rel="canonical" href="https://askslm.com/" />
```

**Issue**: Canonical points to `https://askslm.com/` (non-www) but the site
lives at `https://www.askslm.com/` (www). The non-www version 301-redirects to
www. The canonical should match the live URL: `https://www.askslm.com/`.

### 1.4 robots.txt

```
User-agent: *
Allow: /

Sitemap: https://askslm.com/sitemap.xml
```

**Issues**:

- Sitemap URL uses non-www (`askslm.com`) while the site is www-canonical.
  Should be `https://www.askslm.com/sitemap.xml`.
- `Allow: /` is implicit --- not needed but not harmful.
- No disallow rules for admin/API paths (if any exist).

### 1.5 sitemap.xml

The sitemap contains exactly **one URL**: `https://askslm.com/`

**Issues**:

- Only the homepage is listed. A proper sitemap should list all indexable pages.
- Uses non-www URL (inconsistent with live site).
- Last modified: 2025-12-12 (over 2 months stale).
- Since this is a single-page site, the sitemap accurately reflects reality ---
  but that reality is the problem.

### 1.6 Structured Data / JSON-LD

**None.** Zero structured data anywhere on the page.

**Missing opportunities**:

- `Organization` schema (company name, logo, location, founders)
- `WebSite` schema with `SearchAction`
- `SoftwareApplication` schema for the platform
- `FAQPage` schema (could be generated from the problem/solution sections)
- `Person` schema for team members
- `LocalBusiness` schema (Austin, TX)

### 1.7 URL Structure

Since the entire site is a single page with anchor links (`#hero`, `#problem`,
`#engine`, etc.), there is no URL structure to evaluate. Every "page" in the
navigation is actually `https://www.askslm.com/#section-name`.

**Footer links for Privacy, Terms, and Security all point to `#` (nowhere).**

```html
<a href="#">Privacy</a>
<a href="#">Terms</a>
<a href="#contact">Security</a>
```

These are dead links. No privacy policy or terms of service exist on the site
despite being linked.

### 1.8 Internal Linking

All navigation links are same-page anchor jumps. There are zero internal links
to separate pages. The footer "Solutions" links all point to `#solutions`
rather than individual solution pages.

**Assessment**: The site has no internal linking strategy because it has no
pages to link between. This is the single biggest structural SEO problem.

### 1.9 Redirect Behavior

| From                     | To                                          | Status  |
| ------------------------ | ------------------------------------------- | ------- |
| `http://askslm.com/`     | Serves content directly (NO HTTPS redirect) | **200** |
| `http://www.askslm.com/` | Serves content directly (NO HTTPS redirect) | **200** |
| `https://askslm.com/`    | `https://www.askslm.com/`                   | **301** |

**Critical issue**: HTTP requests are NOT being redirected to HTTPS. The HTTP
version serves the full page content. This means:

- Duplicate content on HTTP and HTTPS
- Security risk (form submissions over HTTP)
- Google may index the HTTP version

---

## 2. Performance Indicators

### 2.1 Page Weight

| Resource                     | Size    | Notes                                                                      |
| ---------------------------- | ------- | -------------------------------------------------------------------------- |
| HTML                         | 55 KB   | Uncompressed. Very large for a static page --- all content is in one file. |
| styles.css                   | 15.7 KB | Single CSS file, custom-written, no framework.                             |
| script.js                    | 1.3 KB  | 41 lines of vanilla JS (nav toggle + smooth scroll).                       |
| Google Analytics             | ~45 KB  | gtag.js loaded async from googletagmanager.com.                            |
| Cloudflare email obfuscation | ~1 KB   | `/cdn-cgi/scripts/.../email-decode.min.js`                                 |
| Images (team photos)         | Unknown | 2 hosted on wixstatic.com (external), 6+ in `./images/`                    |
| logo.png                     | Unknown | Referenced twice (header + footer).                                        |
| spoke2.png                   | Unknown | Hero section graphic.                                                      |
| favicon assets               | ~4 KB   | favicon.ico (3.2 KB) + PNG variants + apple-touch-icon.                    |

**Estimated total page weight**: ~120-200 KB (excluding images). With team
photos (JPEG, likely 50-100 KB each), total is likely **500-800 KB**.

### 2.2 Render-Blocking Resources

```html
<link rel="stylesheet" href="styles.css" />
```

The CSS file is render-blocking (no `media` attribute, no `preload`). This is
normal for a main stylesheet and acceptable at 15.7 KB. There is no critical
CSS inlining.

### 2.3 Script Loading

```html
<script
  async
  src="https://www.googletagmanager.com/gtag/js?id=G-QRJ537RVQF"
></script>
<script>
  /* inline gtag config */
</script>
<!-- ... at end of body: -->
<script src="/cdn-cgi/scripts/.../email-decode.min.js"></script>
<script src="script.js"></script>
```

**Assessment**:

- Google Analytics loaded with `async` --- correct.
- `script.js` loaded at end of `<body>` without `defer` --- acceptable given
  its tiny size, but `defer` would be slightly better.
- Cloudflare email obfuscation script is auto-injected --- acceptable.

### 2.4 Image Optimization

**Team photos**: Two are hosted on `static.wixstatic.com` (Clint House, Zurab
Tutberidze) with query parameters for format and sizing. These are served as
AVIF (good format), but loading them from Wix CDN for just 2 images while the
rest are local (in `./images/`) is inconsistent and adds an extra DNS lookup.

**Local images**: `./images/mariam.jpg`, `./images/georgegoglodze.jpg`,
`./images/thomas.jpg`, `./images/alejandro.jpg`, `./images/saksham.jpg` ---
all JPEG. Query strings like `?auto=compress&cs=tinysrgb&w=400&h=400&fit=crop`
are present but these only work on CDN services (Unsplash, Wix), not on a
static file server. **These query params do nothing on Cloudflare Pages.**

**No `loading="lazy"` on any images.** All 10+ images load eagerly on page
load.

**No `width` / `height` attributes on any `<img>` tags.** This causes layout
shifts (CLS penalty in Core Web Vitals).

**No `<picture>` or `srcset` usage.** No responsive images. No WebP/AVIF
fallbacks for local images.

### 2.5 Third-Party Scripts

| Script                       | Domain                  | Purpose          |
| ---------------------------- | ----------------------- | ---------------- |
| Google Analytics (gtag.js)   | googletagmanager.com    | Analytics        |
| Cloudflare email obfuscation | /cdn-cgi/ (same domain) | Email protection |

**Only two external scripts** --- this is actually excellent. No chat widgets,
no marketing pixel soup, no A/B testing tools. Very clean.

### 2.6 Font Loading

**No custom fonts loaded.** The CSS uses system fonts:

```css
--font-sans:
  system-ui, -apple-system, BlinkMacSystemFont, "SF Pro Text", "Inter",
  sans-serif;
```

**Assessment**: Excellent choice. Zero font loading latency. The `Inter`
reference in the stack will only apply if the user has it installed locally ---
it is not loaded from Google Fonts.

### 2.7 CSS/JS Optimization

- No CSS minification (CSS is hand-formatted with comments).
- No JS minification.
- No bundling or code splitting (not needed at this scale).
- No `preconnect` hints for `googletagmanager.com` or `static.wixstatic.com`.

---

## 3. HTML Quality

### 3.1 Semantic HTML

**Good**:

- Uses `<header>`, `<main>`, `<footer>`, `<nav>`, `<section>`, `<article>` (for team cards).
- Navigation uses `<ul>` / `<li>` structure.
- Content sections use appropriate `<section>` tags with `id` attributes.
- Form uses proper `<label>` elements with `for` attributes.
- Team cards use `<article>` elements.

**Bad**:

- `<center>` tag used twice (lines 486, 979) --- deprecated since HTML4.
- Two `<div>` nesting errors in the hero section (extra closing `</div>` on line 88).
- `<p>` tags nested inside other `<p>` tags (lines 159-170) --- invalid HTML.

### 3.2 Duplicate IDs

**Critical HTML validity issue**: The `id="problem"` is used THREE times:

```html
<section id="problem" class="section section-cta">
  <!-- line 93 -->
  <section id="problem" class="section section-cta">
    <!-- line 148 -->
    <section id="problem" class="section section-alt">
      <!-- line 178 -->
    </section>
  </section>
</section>
```

This is invalid HTML. Only the first `#problem` section will be reachable via
the navigation anchor link. The "AskSLM's proprietary value" and "Competitive
Positioning" sections are effectively unreachable via anchor navigation.

### 3.3 Accessibility

**Good**:

- `aria-label="Main navigation"` on `<nav>`.
- `aria-label="Toggle navigation"` on hamburger button.
- `aria-hidden="true"` on decorative hero graphic.
- All images have `alt` attributes.
- Form inputs have associated `<label>` elements.
- `<html lang="en">` is set.

**Bad**:

- Logo image `alt="Company Logo"` --- should be `alt="AskSLM"` (the brand name).
- Second image `alt="Company Logo"` used on `spoke2.png` which is a decorative
  graphic, not a logo.
- Footer logo `alt="ASKSLM Logo"` --- inconsistent with header (`"Company Logo"`).
- No skip-to-content link.
- No focus styles visible in CSS (no `:focus-visible` rules).
- Contact form has no `action` attribute --- **the form does nothing when submitted**.
- No `required` attributes on form fields.
- No `aria-required` on form fields.
- Hamburger menu `max-height` animation may not work well with screen readers.
- Color contrast likely fine (light text on dark background) but untested.

### 3.4 Valid HTML Issues

1. **Duplicate `<meta charset="UTF-8" />`** on lines 4 and 10.
2. **`<link rel="andoid-chrome-icon">`** on line 17 --- typo. Should be
   `android-chrome`. Also, this is not a standard `rel` value; the correct
   approach is `<link rel="icon" type="image/png" sizes="192x192" ...>`.
3. **Duplicate `id="problem"`** used 3 times.
4. **Nested `<p>` tags** around lines 159-170.
5. **Deprecated `<center>` tags** on lines 486 and 979.
6. **Unescaped `&` in content** (e.g., `Model Integrity & Provenance` on line
   556 --- should be `&amp;`). Some are escaped, some are not.
7. **Inconsistent indentation** --- mix of tabs and spaces throughout.
8. **Missing `action` attribute** on `<form>` element (line 1222).
9. **Footer Privacy/Terms links point to `#`** --- dead links.
10. **Email address obfuscated by Cloudflare** but the protection only works
    with JavaScript enabled.

### 3.5 CSS Methodology

- **Custom CSS** --- no framework (no Tailwind, no Bootstrap).
- CSS custom properties (variables) for theming.
- BEM-lite naming (`.nav-toggle-bar`, `.team-card-header`, `.footer-bottom-inner`).
- Responsive breakpoints at 960px, 768px, 640px, 520px, and 200px.
- Dark theme with gradient backgrounds.
- Good use of `clamp()` for responsive typography.
- **Duplicate CSS rules**: `.nav.open .nav-list` is defined twice (lines 215-219
  and 222-226) with conflicting `max-height` values (600px then 360px). The
  second declaration wins.
- **Duplicate `.nav-list a` rules** defined twice with slightly different values.

---

## 4. Content SEO

### 4.1 Keyword Targeting

**Primary keywords (explicit in meta tags)**:

- AskSLM
- edge AI
- local AI
- SLM / small language models
- domain specific AI
- private AI
- on-device AI
- enterprise AI assistant

**Keywords used heavily in body content**:

- on-premise AI (appears 20+ times)
- regulated industries
- data sovereignty
- secure AI / private AI
- zero cloud
- inference engine
- HIPAA compliance
- enterprise-grade AI

**Keyword gaps** (terms the market searches for but the site does not target):

- "self-hosted AI" / "self-hosted LLM"
- "air-gapped AI"
- "HIPAA compliant AI"
- "SOC 2 AI"
- "on-premises language model" (note: "on-premises" with trailing s is more
  common in enterprise search)
- "private LLM deployment"
- "local LLM server"
- "enterprise AI privacy"

### 4.2 Content Depth

The page is extraordinarily long and detailed for a single page. Approximate
word count: **5,000-6,000 words**. It covers:

- Problem statement with 5 distinct pain points
- Competitive comparison table
- 4 platform components (engine, marketplace, training, deployment)
- 6 security/compliance areas
- 8 industry solutions
- 15 detailed use case scenarios
- 8 team bios
- Development philosophy
- Contact form + CTA

**Assessment**: The content is comprehensive but suffers from the
single-page-app anti-pattern for SEO. All of this content competes for the
same URL. Google cannot rank the "Healthcare" section independently for
healthcare AI queries because it is buried in a 5,000-word page about
everything.

### 4.3 Content Quality Issues

1. **Typo in hero**: "where you data lives" should be "where your data lives"
   (line 68).
2. **Typo**: "competitive most" should be "competitive moat" (line 168).
3. **Branding inconsistency**: The product is called "AskSLM", "Secure SLM",
   "Secure SLM Platform", and "SLM Marketplace" interchangeably. Google will
   struggle to understand the brand entity.
4. **Copyright says 2025** --- should be updated to 2026 or use a range.
5. **"Secure SLM / AskSLM"** in the copyright further muddies the brand.

### 4.4 Blog / Content Strategy

**None.** There is no blog, no resource library, no case studies, no
whitepapers, no documentation, no changelog. The site is purely a marketing
landing page. For a B2B enterprise play targeting regulated industries, this
represents a massive missed opportunity for:

- Long-tail keyword capture
- Thought leadership
- SEO authority building
- Link earning
- Lead nurturing

---

## 5. Tech Stack Analysis

### 5.1 Framework / Platform

**None.** This is a plain static HTML site with:

- 1 HTML file (index.html)
- 1 CSS file (styles.css, 904 lines, 15.7 KB)
- 1 JS file (script.js, 41 lines, 1.3 KB)

No React, no Next.js, no Astro, no Hugo, no CMS, no static site generator.
The HTML is hand-authored. Evidence includes:

- No `data-*` framework attributes
- No client-side hydration scripts
- No build artifacts or hashed filenames
- HTML comments are hand-written (e.g., `<!-- ================= HERO ================= -->`)
- Inconsistent indentation (mix of tabs/spaces)
- No minification

### 5.2 Hosting

**Cloudflare Pages** (served via Cloudflare CDN):

- Server header: `cloudflare`
- Ray ID: `cf-ray` present
- Email obfuscation: Cloudflare-injected `email-decode.min.js`
- Cookie: `BUI=ui1` (Cloudflare bot management)
- `cf-cache-status: DYNAMIC` (not using Cloudflare cache effectively)

### 5.3 DNS & SSL

- HTTPS is available and valid.
- Non-www redirects to www via 301 (good).
- **HTTP does NOT redirect to HTTPS** (bad).
- No HSTS header detected.
- No Content-Security-Policy header.

### 5.4 Analytics / Tracking

- **Google Analytics 4** (`G-QRJ537RVQF`) via gtag.js.
- No Google Tag Manager container.
- No Facebook Pixel.
- No LinkedIn Insight Tag.
- No HubSpot, Marketo, or other marketing automation.
- No Hotjar, FullStory, or session replay.
- No Google Search Console verification meta tag (may use DNS verification).

### 5.5 Third-Party Integrations

- **Wix Static** (`static.wixstatic.com`) --- 2 team photos are hosted on Wix's CDN,
  suggesting the photos were migrated from a previous Wix-based site.
- **No form backend** --- the contact form has no `action` attribute and no
  JavaScript form handler. **Submissions go nowhere.**
- No CRM integration.
- No calendar/scheduling tool (Calendly, etc.).
- No chat widget.

### 5.6 Security Headers (Missing)

The response headers are minimal:

```
content-type: text/html
cache-control: private
server: cloudflare
```

**Missing security headers**:

- `Strict-Transport-Security` (HSTS)
- `Content-Security-Policy`
- `X-Content-Type-Options`
- `X-Frame-Options`
- `Referrer-Policy`
- `Permissions-Policy`

For a company selling security-focused enterprise AI, the absence of basic
security headers on their own website is a credibility risk.

---

## 6. Prioritized Recommendations

### Critical (Fix immediately)

1. **Fix the contact form.** It submits nowhere. Every demo request is lost.
   Add a form backend (Formspree, Netlify Forms, or a custom endpoint).

2. **Fix HTTP-to-HTTPS redirect.** HTTP serves the full site without redirect.
   Configure Cloudflare to force HTTPS (it is a one-click setting in the
   Cloudflare dashboard under SSL/TLS > Edge Certificates > Always Use HTTPS).

3. **Fix canonical URL.** Change from `https://askslm.com/` to
   `https://www.askslm.com/` to match the live domain.

4. **Fix the "where you data lives" typo** in the hero section.

5. **Fix the "competitive most" typo** (should be "moat").

### High Priority (For the rebuild)

6. **Break the single page into multiple pages.** At minimum:
   - `/` --- homepage (hero + summary cards + CTA)
   - `/platform/` --- engine, marketplace, training, deployment
   - `/solutions/legal/` --- dedicated legal page
   - `/solutions/healthcare/` --- dedicated healthcare page
   - `/solutions/financial-services/` --- dedicated finance page
   - `/solutions/government/` --- dedicated government page
   - `/solutions/` --- solutions overview linking to verticals
   - `/security/` --- security & compliance detail
   - `/about/` --- team + philosophy
   - `/contact/` --- standalone contact page
   - `/use-cases/` --- use case library
   - `/privacy/` --- privacy policy (currently a dead link)
   - `/terms/` --- terms of service (currently a dead link)

7. **Add Open Graph and Twitter Card meta tags** to every page.

8. **Add JSON-LD structured data** (Organization, WebSite, SoftwareApplication).

9. **Add a real sitemap** listing all pages with accurate lastmod dates.

10. **Add security headers** via Cloudflare (HSTS, CSP, X-Content-Type-Options).

### Medium Priority

11. **Add `loading="lazy"`** to all images below the fold.

12. **Add `width` and `height`** attributes to all `<img>` tags.

13. **Consolidate team photos** --- move Wix-hosted images to own domain.

14. **Add `<link rel="preconnect">` hint** for `googletagmanager.com`.

15. **Remove duplicate `<meta charset>`** tag.

16. **Fix duplicate `id="problem"`** (use unique IDs).

17. **Remove deprecated `<center>` tags.**

18. **Fix nested `<p>` tags** (invalid HTML).

19. **Fix the `rel="andoid-chrome-icon"` typo.**

20. **Add a skip-to-content link** for accessibility.

21. **Add `:focus-visible` styles** for keyboard navigation.

### Lower Priority (Content strategy)

22. **Start a blog/resources section** targeting long-tail keywords:
    - "HIPAA compliant AI solutions"
    - "on-premises AI deployment guide"
    - "small language models vs large language models"
    - "private AI for law firms"
    - Industry-specific thought leadership

23. **Create dedicated landing pages** for each industry vertical to capture
    search traffic from buyers researching AI for their specific sector.

24. **Add case studies** or proof points (even anonymized) to build trust.

25. **Consolidate brand naming** --- pick either "AskSLM" or "Secure SLM" and
    use it consistently. Google associates one brand entity per domain.

26. **Update copyright year** to 2026.

27. **Add LinkedIn Insight Tag** --- for a B2B enterprise play, LinkedIn
    retargeting is likely more valuable than any other pixel.

---

## 7. Competitive Context

The site positions against OpenAI/Anthropic (cloud), Hugging Face (open
source), and Ollama (local). The competitive table is a strong differentiator
but lives on a page no one can find via search because it is buried in a
single-page site.

Key search terms like "private AI for enterprises", "on-premise LLM",
"HIPAA AI", and "air-gapped AI deployment" have growing search volume. The
site has zero organic visibility for any of these because there are no
individual pages optimized for them.

---

## Appendix A: Complete File Inventory

| File                         | Size                       | Notes                                  |
| ---------------------------- | -------------------------- | -------------------------------------- |
| `index.html`                 | 55,012 bytes (1,348 lines) | Single page, unminified                |
| `styles.css`                 | 15,662 bytes (904 lines)   | Custom CSS, unminified                 |
| `script.js`                  | 1,281 bytes (41 lines)     | Vanilla JS, unminified                 |
| `favicon.ico`                | 3,249 bytes                | Standard favicon                       |
| `favicon-32x32.png`          | Present                    | PNG favicon                            |
| `favicon-16x16.png`          | Present                    | PNG favicon                            |
| `apple-touch-icon.png`       | Present                    | Apple touch icon                       |
| `android-chrome-192x192.png` | Present                    | Android icon                           |
| `logo.png`                   | Present                    | Company logo (used in header + footer) |
| `spoke2.png`                 | Present                    | Hero section graphic                   |
| `images/mariam.jpg`          | Present                    | Team photo                             |
| `images/georgegoglodze.jpg`  | Present                    | Team photo                             |
| `images/thomas.jpg`          | Present                    | Team photo                             |
| `images/alejandro.jpg`       | Present                    | Team photo                             |
| `images/saksham.jpg`         | Present                    | Team photo                             |
| `robots.txt`                 | Small                      | 3-line file                            |
| `sitemap.xml`                | Small                      | Single URL entry                       |

## Appendix B: External Dependencies

| Resource            | Domain                 | Purpose              |
| ------------------- | ---------------------- | -------------------- |
| gtag.js             | googletagmanager.com   | Google Analytics 4   |
| email-decode.min.js | /cdn-cgi/ (Cloudflare) | Email obfuscation    |
| 2 team photos       | static.wixstatic.com   | Legacy photo hosting |

## Appendix C: CSS Breakpoints

| Breakpoint         | Target                           |
| ------------------ | -------------------------------- |
| `max-width: 960px` | Tablet landscape                 |
| `max-width: 768px` | Tablet portrait                  |
| `max-width: 640px` | Large phone                      |
| `max-width: 520px` | Small phone                      |
| `max-width: 200px` | Unusably small (unclear purpose) |
