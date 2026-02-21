---
title: React Component Library Ecosystem - State of Play March 2026
type: research
tags: [react, component-libraries, shadcn, radix, base-ui, tailwind, headless, accessibility, icons, charts, tanstack]
summary: Comprehensive landscape analysis of React UI component libraries, icon libraries, chart libraries, and TanStack ecosystem for a monitoring/curation dashboard project in 2026
status: active
source: deep-research
confidence: high
created: 2026-03-19
updated: 2026-03-19
---

## Executive Summary

shadcn/ui with Base UI primitives is the clear default for new React projects in 2026. The copy-paste ownership model, Tailwind v4 integration, dual Radix/Base UI primitive support (added February 2026), and visual builder CLI make it the strongest fit for a monitoring/curation dashboard where you want to own the visual layer. Radix remains stable in production but is effectively in maintenance mode; Base UI (v1.0, December 2025) is the recommended primitive layer going forward. For charts, Tremor (Tailwind-native, shadcn-adjacent copy-paste model) covers dashboard KPIs, while Recharts handles custom visualizations. TanStack Table is the uncontested headless data table solution. Lucide is the default icon library.

## 1. Component Library Landscape

### 1.1 shadcn/ui - The Default Choice

**Architecture**: Copy-paste. `npx shadcn add <component>` copies TypeScript source into `components/ui/`. You own every line. No npm dependency lock-in.

**Stats (March 2026)**: ~110k GitHub stars, ~20M monthly npm downloads (CLI), CLI v4.0.5

**Tailwind integration**: Native. Tailwind v4 supported since early 2026. CSS-first configuration via `@theme` directive. CSS variable theming system with 7 base color palettes (Neutral, Stone, Zinc, Mauve, Olive, Mist, Taupe).

**Dark mode**: Built-in via CSS variables. `:root[class~="dark"]` convention. Updated dark mode colors for improved accessibility in 2026.

**Component breadth**: Accordion, Alert, Alert Dialog, Avatar, Badge, Breadcrumb, Button, Calendar, Card, Carousel, Checkbox, Collapsible, Combobox, Command (command palette via cmdk), Context Menu, Data Table, Date Picker, Dialog, Drawer (via Vaul), Dropdown Menu, Form, Hover Card, Input, Input OTP, Label, Menubar, Navigation Menu, Pagination, Popover, Progress, Radio Group, Resizable, Scroll Area, Select, Separator, Sheet, Skeleton, Slider, Sonner (toasts), Switch, Table, Tabs, Textarea, Toast, Toggle, Tooltip, plus 1398+ premium blocks.

**React 19**: Full support. `forwardRef` deprecated in React 19; ref is now a prop. shadcn components updated accordingly.

**Major 2026 developments**:
- February 2026: Base UI support added as alternative primitive layer (choose at `npx shadcn create` time)
- February 2026: Visual builder at `ui.shadcn.com/create` with framework selection (Next.js, Vite, TanStack Start), theme customization, icon library selection
- February 2026: Five visual styles: Vega (classic), Nova (compact), Maia (soft/rounded), Lyra (boxy/sharp), Mira (dense)
- February 2026: Unified Radix UI package (mono-package migration)
- March 2026: CLI v4 with expanded framework support

**Accessibility**: Inherits from underlying primitive layer (Radix or Base UI). WAI-ARIA compliant. Keyboard navigation. Screen reader support.

**Limitations**:
- Component count is smaller than MUI or Ant Design. Some practitioners on HN note "missing half the components I need" for complex apps.
- You must maintain your own components (no automatic upstream patches). This is by design.
- cmdk and Vaul still use Radix even with Base UI selected (as of March 2026, per GitHub issue #9191).

**Community sentiment**: HackerNews split between "it's the idea, not the library" advocates and "I need a complete component set" critics. Reddit discussions fragmented. Practitioner consensus: best for teams that want control and are building design systems, not for teams that want "batteries included."

### 1.2 Primitive Layer: Radix UI vs Base UI

#### Radix UI (Maintenance Mode)

**Stats**: ~18.7k GitHub stars, ~130M monthly npm downloads (across all packages)

**Architecture**: Installed dependency. Unstyled headless primitives. `asChild` composition pattern.

**Current status**: Effectively in maintenance mode. WorkOS acquired Modulz (the company behind Radix). Many original maintainers left. Co-creator Colem publicly called Radix a "liability" and the "last option" for serious projects. Known bugs like aggressive `setState` causing "update depth exceeded" errors closed without fixes.

**React 19**: Most packages updated by late 2025, but required workarounds for new ref handling.

**Recommendation**: Safe for existing production apps. Do not start new projects on Radix primitives alone. Use via shadcn/ui where the abstraction layer insulates you.

#### Base UI (The New Default Primitive)

**Stats**: ~8.9k GitHub stars, ~5M monthly npm downloads, v1.3.0 (March 2026)

**Architecture**: Installed dependency. Unstyled headless primitives. Render prop pattern (vs Radix's `asChild`). Single consolidated package (`@base-ui/react`).

**Origin**: Created by the same developers who built Radix, Material UI, and Floating UI. Joint venture with full-time engineering backing from MUI.

**Key advantages over Radix**:
- Native multi-select in Select component
- Dedicated Combobox component (Radix requires cmdk workaround)
- Autocomplete without dialog patterns
- More intuitive render prop API
- Consolidated single package (vs Radix's many scoped packages)
- Built for React 19 from inception
- Smaller bundle (Dialog: ~6KB vs Radix ~9KB)
- Active full-time maintenance team

**Component count**: 35 accessible components at v1 launch.

**Recommendation**: Use for new projects, either directly or via shadcn/ui's Base UI primitive option.

### 1.3 React Aria (Adobe)

**Stats**: react-aria: ~1.8M weekly downloads, react-aria-components: ~1.2M weekly downloads. Monorepo (adobe/react-spectrum) has 13k+ stars.

**Architecture**: Installed dependency. Two APIs: low-level hooks (`react-aria`) and higher-level unstyled components (`react-aria-components`). Part of Adobe's React Spectrum ecosystem.

**Tailwind integration**: First-class. Official `tailwindcss-react-aria-components` plugin. Data attribute modifiers (`data-[selected]:bg-blue-400`). Render prop API for state-based class application.

**Accessibility**: The gold standard. Adobe's dedicated accessibility research team. Most thoroughly tested accessibility primitives in the React ecosystem. Full WAI-ARIA compliance, keyboard interactions, screen reader announcements, touch support, focus management.

**Component breadth**: Comprehensive. Buttons, calendars, checkboxes, color pickers, combo boxes, date pickers, dialogs, drag-and-drop, grids, list boxes, menus, meters, number fields, popovers, progress bars, radio groups, search fields, select, sliders, switches, tables, tabs, tag groups, text fields, toggles, tooltips, tree views.

**React 19**: Compatible.

**Limitations**: Steeper learning curve than Radix. API is "quite different" from Radix/Base UI/Ariakit. Adobe enterprise backing is both strength (resources) and concern (corporate priorities could shift).

**Notable derivative**: JollyUI takes React Aria components and applies shadcn/ui's design language and Tailwind styling. Copy-paste model like shadcn but using React Aria instead of Radix.

**Recommendation**: Best choice for projects with strict accessibility compliance requirements (government, enterprise, healthcare). Consider JollyUI if you want shadcn-style DX with React Aria accessibility.

### 1.4 HeroUI (formerly NextUI)

**Stats**: 27k+ GitHub stars, 120k+ weekly npm downloads

**Architecture**: Installed dependency. Pre-styled but customizable. Built on React Aria + Tailwind CSS.

**Tailwind integration**: Native. Built with Tailwind CSS. Zero runtime CSS.

**Key value**: Beautiful defaults out of the box with React Aria's accessibility. Individual package imports for bundle optimization.

**Limitations**: Less control than shadcn (installed dependency model). React-only (no Vue/Svelte). Rebranded January 2025 from NextUI, so some documentation/community resources still reference old name.

**Recommendation**: Good for teams that want beautiful defaults immediately without building a design system from scratch. Less relevant for your use case since you want to own the visual layer.

### 1.5 Headless UI (Tailwind Labs)

**Stats**: Latest v2.2.9, published ~6 months ago

**Architecture**: Installed dependency. Unstyled, accessible components. By Tailwind Labs.

**Tailwind integration**: Perfect (same team). `@headlessui/tailwindcss` plugin for state variants.

**Component breadth**: Limited. Menu, Dialog, Combobox, Listbox, Transition, Portal, and a few others. Deliberately small scope.

**Limitations**: Small component count. No tables, no command palette, no toast, no drawer. More of a supplement than a foundation.

**Recommendation**: Not sufficient as a primary library. Use shadcn/ui or React Aria instead. Headless UI fills specific gaps if needed.

### 1.6 Ark UI / Park UI (Chakra team)

**Architecture**: Ark UI is headless primitives (installed dependency). Park UI is the styled layer on top (copy-paste, like shadcn). Multi-framework: React, Vue, Solid, Svelte.

**Stats**: Ark UI has 45+ components, latest v5.34.1. Performance: 1.5x-4x better than v4 in stress tests (10k components).

**Tailwind integration**: Park UI supports Tailwind CSS and Panda CSS. Ark UI is styling-agnostic.

**Limitations**: Park UI rated 2.5/5 by users, citing poor documentation and limited component selection. Panda CSS dependency for Park UI adds learning curve. Smaller community than shadcn ecosystem.

**Recommendation**: Worth watching for multi-framework projects. Not recommended over shadcn/ui + Base UI for React-only projects.

### 1.7 Melt UI

**Framework**: Svelte only. No React support.

**Note**: Included in your question but not applicable to a React project. Melt UI is the equivalent of Radix for Svelte, with Bits UI as the styled layer on top.

### 1.8 Ariakit

**Architecture**: Installed dependency. Hooks-based. State-driven approach separating state management from rendering. Formerly Reakit.

**Tailwind integration**: Styling-agnostic. Works with any approach.

**API similarity**: Close to Radix and Base UI (unlike React Aria's different API paradigm).

**Limitations**: Significant learning curve. No pre-styled components at all. Small community.

**Recommendation**: Niche. Use if you need maximum composition flexibility and are building everything from scratch.

### 1.9 Emerging: Basecoat (Non-React)

Show HN project: "All of the shadcn/ui magic, none of the React." For teams wanting shadcn patterns outside React. Not relevant for your project but signals the influence of the copy-paste model.

## 2. Decision Matrix for Your Requirements

| Requirement | shadcn/ui + Base UI | React Aria / JollyUI | Headless UI | Ark UI + Park UI |
|---|---|---|---|---|
| Copy-paste ownership | Yes (core feature) | JollyUI: Yes | No (npm dep) | Park UI: Yes |
| Tailwind CSS compatibility | Native (v4) | First-class plugin | Native | Park UI: Yes |
| Headless / unstyled | Base UI layer is headless; shadcn adds Tailwind styling you control | Fully headless | Fully headless | Ark: headless |
| Dark mode built-in | Yes, CSS variables | You implement | You implement | Park UI: Yes |
| Accessibility | Excellent (Base UI) | Gold standard | Excellent | Good (WAI-ARIA) |
| Active maintenance | Very active (CLI v4, Mar 2026) | Active (Adobe team) | Slower cadence | Active (v5.34) |
| TypeScript first | Yes | Yes | Yes | Yes |
| Component breadth | Broad (50+) | Broad (40+) | Narrow (~10) | Broad (45+) |

**Recommendation**: shadcn/ui with Base UI primitives. It satisfies all seven requirements.

## 3. Icon Libraries

| Library | Icons | Weekly Downloads | Bundle (50 icons) | Bundle (200 icons) | Weights/Styles |
|---|---|---|---|---|---|
| **Lucide** | 1,500+ | ~29.4M | 5.16 KB | 15.72 KB | 1 (stroke) |
| **Heroicons** | 290+ | ~2.0M | 3.49 KB | 19.09 KB | 2 (outline, solid) |
| **Phosphor** | 1,200+ | ~100K | 33.91 KB | 102.27 KB | 6 (thin, light, regular, bold, fill, duotone) |
| **Tabler** | 5,900+ | N/A | Tree-shakable | Tree-shakable | 2 (outline, filled) |

**Analysis**:
- Lucide is the default for shadcn/ui projects. Best bundle efficiency at scale. 1,500+ icons. shadcn's visual builder offers Lucide as the default icon library selection.
- Heroicons is the smallest at low icon counts but scales worse. Only 290 icons limits breadth. Natural fit with Tailwind (same team).
- Phosphor offers unmatched design versatility with 6 weights for visual hierarchy, but 16-18x bundle overhead makes it unsuitable for performance-sensitive apps.
- Tabler has the largest icon count (5,900+) with tree-shaking. Good for projects needing breadth. There was a shadcn/ui community discussion about switching to Tabler.

**Recommendation**: Lucide. It is the ecosystem default, has the best bundle characteristics at scale, 1,500+ icons covers dashboard needs, and shadcn/ui integration is zero-config.

## 4. Chart / Visualization Libraries

| Library | Stars | Weekly Downloads | Rendering | Tailwind-native | Copy-paste |
|---|---|---|---|---|---|
| **Recharts** | 26.8k | ~16.7M | SVG | No (className) | No |
| **Tremor** | 16.5k | ~1.1M (total) | SVG (via Recharts) | Yes | Yes |
| **Nivo** | 14k | ~2.5K | SVG/Canvas/HTML | No | No |
| **Victory** | 11.1k | ~272K | SVG | No | No |
| **ECharts (echarts-for-react)** | N/A | N/A | Canvas/WebGL | No | No |

**Analysis**:

- **Tremor**: Purpose-built for dashboards. 35+ components including KPI cards, sparklines, line/bar/area/donut charts, data tables. Built on Recharts + Tailwind CSS + Radix UI. Copy-paste model. Acquired by Vercel. Supports Tailwind v4. "Show the data, hide the chrome" philosophy. Best fit for a monitoring dashboard.

- **Recharts**: The workhorse. 16.7M weekly downloads. Simple declarative API. SVG-based. Handles small-to-medium datasets well. Performance degrades with 10k+ data points (SVG node overhead). shadcn/ui's built-in chart components use Recharts under the hood.

- **Nivo**: Most visually polished. Supports SVG, Canvas, and HTML rendering. Better for large datasets via Canvas mode. Steeper learning curve. D3-based.

- **Victory**: Best cross-platform story (React Native compatible). Accessibility-focused. Good for teams with a shared design system. Modular.

- **ECharts**: Enterprise-grade. Handles 100k+ data points. GPU-accelerated Canvas/WebGL. Maps, 3D, drill-down. Overkill for most dashboards but necessary for massive datasets.

**Recommendation for monitoring dashboard**: Tremor as the primary chart layer (KPI cards, standard charts, Tailwind-native). If Tremor's high-level API is too constrained for a specific visualization, drop to Recharts directly. Consider Nivo's Canvas mode only if you hit SVG performance limits with large datasets.

## 5. TanStack Ecosystem (March 2026)

### TanStack Query
- Retained #1 position in the React library ecosystem (overtook Next.js)
- 42% of users rate it positively
- Full RSC (React Server Components) support via hydration pattern and `ReactQueryStreamedHydration`
- Works with Next.js App Router, TanStack Start, Vite
- The standard for server state management

### TanStack Table
- Headless. You bring your own UI.
- 10-15KB tree-shaken
- Sorting, multi-sort, global/column filters, pagination, row grouping, aggregation, row selection/expansion, column ordering/visibility/resizing, virtualization
- Pairs with shadcn/ui's Data Table component (which wraps TanStack Table)
- Server-side data support
- The uncontested solution for complex data tables in React

### TanStack Router
- Type-safe routing with inferred params and search params
- Route-first data loading, integrated with TanStack Query
- Autocomplete and compile-time type checks for route params
- Significantly ahead of React Router v7 in type safety (React Router v7's advanced features only work in framework mode)
- TanStack Start (full-stack framework) reached 1.0

### TanStack Form
- Type-safe form handling, framework-agnostic
- Newer addition to the ecosystem

### Ecosystem Direction
- Philosophy: headless, framework-agnostic, fully type-safe
- New tools in development: TanStack DB, TanStack AI
- The ecosystem is increasingly cohesive: Router + Query + Table + Form + Start

**Recommendation**: Use TanStack Query for data fetching, TanStack Table for data grids (via shadcn's Data Table wrapper), and evaluate TanStack Router if building a SPA outside Next.js.

## 6. Recommended Stack for Monitoring/Curation Dashboard

```
Primitives:     shadcn/ui + Base UI (copy-paste, own everything)
Styling:        Tailwind CSS v4 (CSS-first config)
Dark mode:      shadcn CSS variable system
Icons:          Lucide
Charts:         Tremor (KPIs, standard charts) + Recharts (custom)
Data tables:    TanStack Table (via shadcn Data Table component)
Data fetching:  TanStack Query
Routing:        TanStack Router (SPA) or Next.js App Router
Forms:          TanStack Form or React Hook Form
```

**Initialization**: `npx shadcn create` with Base UI primitive selection, Tailwind v4, Lucide icons.

## Sources Consulted

### Primary Documentation
- [shadcn/ui Changelog](https://ui.shadcn.com/docs/changelog) - February/March 2026 releases
- [shadcn/ui Theming](https://ui.shadcn.com/docs/theming) - CSS variable system
- [shadcn/ui Dark Mode](https://ui.shadcn.com/docs/dark-mode) - Dark mode setup
- [Base UI](https://base-ui.com/) - v1.0 docs
- [React Aria Styling](https://react-aria.adobe.com/styling) - Tailwind integration
- [TanStack Docs](https://tanstack.com/) - Query, Table, Router
- [Tremor](https://www.tremor.so/) - Dashboard components

### Analysis Articles
- [PkgPulse: shadcn/ui vs Base UI vs Radix 2026](https://www.pkgpulse.com/blog/shadcn-ui-vs-base-ui-vs-radix-components-2026) - Detailed metrics comparison
- [Builder.io: 15 Best React UI Libraries 2026](https://www.builder.io/blog/react-component-libraries-2026) - Ranked review
- [Makers Den: React UI Libraries 2025](https://makersden.io/blog/react-ui-libs-2025-comparing-shadcn-radix-mantine-mui-chakra)
- [InfoQ: Base UI 1 Release](https://www.infoq.com/news/2026/02/baseui-v1-accessible/) - v1 analysis
- [InfoQ: shadcn Visual Builder](https://www.infoq.com/news/2026/02/shadcn-ui-builder/)
- [LogRocket: Headless UI Alternatives](https://blog.logrocket.com/headless-ui-alternatives/) - Radix vs React Aria vs Ark UI vs Base UI
- [CodeWithSeb: TanStack 2026 Guide](https://www.codewithseb.com/blog/tanstack-ecosystem-complete-guide-2026)

### Social / Practitioner Sentiment
- [shadcn on X: Thoughts on Radix](https://x.com/shadcn/status/1936082723904565435) - June 2025 thread on Radix maintenance and strategy
- [HN: shadcn criticism thread](https://news.ycombinator.com/item?id=40465533) - "Missing essential components"
- [HN: Base UI recommendation](https://news.ycombinator.com/item?id=46956364) - Radix developers moved to Base UI
- [DEV.to: Radix Future Deep Dive](https://dev.to/mashuktamim/is-your-shadcn-ui-project-at-risk-a-deep-dive-into-radixs-future-45ei)
- [GitHub: shadcn Base UI Migration Discussion](https://github.com/shadcn-ui/ui/discussions/9562)

### Icon Library Benchmarks
- [Lucide Comparison](https://lucide.dev/guide/comparison) - Official comparison page
- [Medium: React Icons Bundle Cost Benchmark](https://medium.com/codetodeploy/the-hidden-bundle-cost-of-react-icons-why-lucide-wins-in-2026-1ddb74c1a86c) - Next.js 16 Turbopack benchmarks
- [shadcndesign: Best Icon Libraries for shadcn](https://www.shadcndesign.com/blog/5-best-icon-libraries-for-shadcn-ui)

### Chart Library Analysis
- [Querio: Top React Chart Libraries 2026](https://querio.ai/articles/top-react-chart-libraries-data-visualization)
- [LogRocket: Best React Chart Libraries 2025](https://blog.logrocket.com/best-react-chart-libraries-2025/)
- [Kyle Gill: React Chart Libraries](https://www.kylegill.com/essays/react-chart-libraries)

## Source Quality Assessment

**High confidence**: shadcn/ui features and timeline (verified against official changelog), Base UI v1 release facts, TanStack ecosystem status, icon bundle benchmarks (multiple independent sources agree), npm download numbers (cross-referenced npmtrends and npm).

**Medium confidence**: Radix maintenance status claims (sourced from community reports and the co-creator's public statements, but WorkOS has not made an official deprecation announcement). Tremor acquisition by Vercel (single source). HeroUI download numbers (single source from Jan 2026 article).

**Low confidence**: Specific practitioner percentage preferences (Reddit searches returned almost no results for this topic; the React community is fragmented across Discord, X, and private Slacks).

## Open Questions

1. **Base UI component parity with Radix**: As of March 2026, cmdk (Command) and Vaul (Drawer) in shadcn still depend on Radix even when Base UI is selected. Timeline for full Base UI equivalents is unclear.
2. **Tremor v4**: Tremor's copy-paste model is relatively new. Long-term maintenance trajectory post-Vercel acquisition is unknown.
3. **TanStack Start maturity**: 1.0 released but real-world production reports are sparse.
4. **React Aria adoption trajectory**: Despite Adobe backing and superior accessibility, React Aria's market share growth appears slower than Base UI's. Whether JollyUI gains traction as the "shadcn for React Aria" remains to be seen.

## Actionable Takeaways

1. **Initialize with**: `npx shadcn create`, select Base UI primitives, Tailwind v4, Lucide icons, Nova or Mira style for a dashboard.
2. **Add Tremor** for dashboard-specific chart components and KPI cards.
3. **Use TanStack Table** via shadcn's Data Table wrapper for all data grid needs.
4. **Use TanStack Query** for server state management.
5. **Do not migrate** existing Radix-based projects. The abstraction layer in shadcn insulates you from Radix maintenance concerns.
6. **Monitor Base UI** component expansion, particularly for Command palette and Drawer replacements for cmdk/Vaul.
7. **Consider JollyUI** as an alternative only if accessibility compliance is a hard regulatory requirement.
