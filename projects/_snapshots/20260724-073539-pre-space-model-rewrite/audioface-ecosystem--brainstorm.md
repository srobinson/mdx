# Audioface Ecosystem, Moat & 3-Year Bet

**Date:** 2026-07-05  
**Scope:** audioface (procedural Web Audio UI sound system)  
**Lens:** Ecosystem, defensibility, platform expansion. Wide but grounded. Read from AUDIO.md + README.md + source only.

## Current State (Ground Truth)

- Purely procedural synthesis (noise + tone + FM layers). Zero audio assets.
- Semantic token contract (e.g. `button.press`, `panel.dock`, `field.reject`). Tokens describe *interface meaning*.
- Theme model with 7 controls: material (8 profiles), density, politeness, contrast, mechanical, warmth, variation + volume.
- Tiny runtime surface: `createAudioface(config)` returns a frozen resolver; separate engine handles Web Audio scheduling.
- Composer lab (A/B slots, presets, live audition of tokens + canonical sequences, drag/scrub interactions, TS/JSON export).
- Strong invariants: user-gesture start, short decay, no hover, no long tails, no files.
- Package names + audioface.dev now owned across npm/pypi/crates.

The product promise is tactile, low-fatigue, material-aware feedback that feels like part of the interface, not decoration.

## 3-Year Bet

Audioface becomes the standard language and runtime for *declarative, themeable UI sound* the way modern design systems standardized color, typography, and motion tokens.

Success looks like:

- `audioface` (or a thin wrapper) ships as an optional peer in major component libraries and design systems.
- A portable theme file (`.audioface.json` or equivalent) travels between Figma, code, and runtime.
- Teams treat "sound theme" as a first-class design token category alongside visual tokens.
- The runtime is small enough to be a default dependency; the spec is open enough to be implemented anywhere.
- audioface.dev is the registry, reference, and discovery surface.

The bet is expansive because sound is the missing sense in digital interfaces. The defensibility comes from owning the *semantics + the canonical tiny implementation + the distribution surface* at the same time.

## Ranked Ideas by Moat Strength

### 1. Own the Portable Sound Theme Standard + Public Registry (Strongest Moat)

Define and steward an open interchange format for Audioface themes and the semantic token catalog. A versioned JSON schema + reference implementation. Host a public registry (themes, material profiles, curated token extensions) at audioface.dev.

- Designers export from the composer or Figma plugin.
- Design systems declare "audioface" themes the same way they declare color modes or motion prefs.
- Runtimes (web, React Native bridge, desktop, embedded) consume the same theme file.

**Why this moat is strongest:** It turns Audioface into infrastructure. Once the interchange format is adopted inside component libraries and design tokens pipelines, switching requires forking the semantics, the token names, and convincing every downstream consumer to change. We control the default resolver, the test suite, and the evolution of the spec. Package name ownership + domain gives first-mover brand. Weekend clones can copy the synthesis but cannot own the shared language or the registry.

### 2. Figma Plugin as the Source of Truth for Sound

Ship the authoritative Figma plugin that lets designers author, preview (with real Web Audio inside Figma via plugin sandbox tricks or companion), version, and publish Audioface themes directly attached to components or variables.

Two-way sync: Figma theme → code export (TS/JSON) and back-annotation.

**Moat:** Design decisions originate in Figma for most product teams. If the canonical "sound theme" definition lives inside the Figma file and travels with the design system, engineering cannot easily swap it without breaking the design contract. High switching cost.

### 3. "Add Sound" Distribution via Component Primitives (shadcn-style)

Create the equivalent of `npx shadcn@latest add` but for sound:

- `npx audioface add` scaffolds a theme provider, maps existing components to tokens, and wires sequences.
- First-class integrations and recipes for shadcn/ui, Radix, Tailwind, Next.js app router, etc.
- Optional "sound layer" that teams can adopt incrementally.

**Moat:** Captures the modern high-velocity onboarding path. Once teams initialize a new project with sound already present and delightful, the default is set. Distribution compounds through templates, starters, and tutorials.

### 4. Native Experience Inside Daily Dev Tools

- VS Code extension: hover previews, inline token documentation, "play" button that uses the local runtime, sequence debugging.
- Storybook addon with full theme composer panel and sequence runner.
- Vite/Next/Webpack plugins for dev-time sound server and production tree-shaking.
- Tailwind-like config surface or CSS custom property bridge where sensible.

**Moat:** Invisible habit formation. Developers and designers live inside these tools. When auditioning and tweaking sound is as low-friction as changing a Tailwind class, displacement becomes painful.

### 5. Marketplace + Theme Economy on audioface.dev

Curated marketplace for themes (free core set + premium/brand/vertical packs). Creator submissions, remixing, ratings, collections ("Fintech", "Spatial", "High Density Data").

- Free runtime + core tokens.
- Paid or sponsored themes; revenue share.
- Enterprise: private registries, custom materials, audit/compliance exports.

**Moat:** Two-sided network effects. The best themes live here because the audience is here. The audience comes because the best themes are here. Brand ownership of the category name makes this the default discovery surface.

### 6. Accessibility & Non-Visual Interface Layer

Treat Audioface tokens as a first-class affordance system for:

- Enhanced feedback for low-vision / motor-impaired users.
- Sonified data (tables, charts, status changes) without visual reliance.
- Graceful reduced-motion + reduced-sound profiles that still communicate state.
- Reference mappings for ARIA patterns.

**Moat:** Combines technical excellence with a defensible values/standards position. Clones can replicate synthesis but struggle to claim the accessibility leadership or integration with emerging a11y tooling.

### 7. Vertical & Hardware Expansions (Grounded)

Leverage the tiny runtime:

- Notification sound themes (web push + Electron + native bridges).
- Automotive / industrial HMI sound kits (strict latency, material consistency).
- Data sonification primitives for dashboards and monitoring tools.
- Game UI and spatial interface sound vocabulary built on the same semantic base.

**Moat:** Incremental. Core engine + token language travels; each vertical adds surface area and reference customers. Lower standalone moat strength but compounds the platform once the standard exists.

### 8. Certified Runtime + Conformance Suite

Keep the canonical Web runtime extremely small and rock-solid. Publish a conformance test suite + certification program ("Audioface Certified") for alternative implementations (WASM core, native ports, other languages).

**Moat:** Quality bar + compatibility guarantee. Teams trust the reference because it ships with the spec. Alternative runtimes must pass the suite to be credible, creating a de-facto standards body role.

## Single Strongest Moat

**The portable theme interchange format + semantic token registry, backed by the canonical tiny runtime and first-party distribution (npm/pypi/crates + audioface.dev).**

This is the only idea that simultaneously:

- Defines the *shared language* (tokens + theme params) that every other surface must speak.
- Owns the default high-quality, tiny-footprint implementation.
- Captures the package namespace and domain at the category level.
- Creates switching costs at the design-system and component-library layer (the actual point of lock-in in modern frontend).

Everything else (Figma plugin, marketplace, IDE integrations, add commands) becomes a distribution and flywheel mechanism *on top of* the standard. A weekend clone can copy the oscillators. It cannot make the rest of the ecosystem speak its dialect.

## Next Steps (Implied by the Bet)

- Formalize the theme JSON schema + versioning rules.
- Extract a clean public API surface and publish the first 0.1 on the owned package names.
- Build the registry + composer export improvements.
- Prioritize the Figma plugin and the shadcn-style "add" path as the two highest-leverage distribution bets.
- Keep the runtime and token contract ruthlessly minimal and documented in AUDIO.md.

This is the expansive but grounded platform play.