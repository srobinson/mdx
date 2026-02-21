---
title: "Sprint-Aware Agent Model with Handoff Deliverables (contains-studio/agents)"
type: research
tags: [agents, sub-agents, claude-code, sprint, ui-design, frontend, multi-agent, agent-definition]
summary: Full agent definition extraction from contains-studio/agents — 38 production agents for a 6-day sprint studio, organized by department with verbatim frontmatter, tool grants, and system prompt content.
status: active
source: github-researcher
confidence: high
created: 2026-03-09
updated: 2026-03-09
---

## Executive Summary

Contains Studio publishes 38 Claude Code sub-agents organized across 7 departments for a 6-day sprint model. Each agent is a `.md` file with YAML frontmatter (name, description, color, tools) followed by a 500+ word system prompt. The repo is designed for direct copy into `~/.claude/agents/`. The sprint philosophy is explicit and pervasive: every agent's responsibilities section maps to 6-day phases, and the studio treats these agents as a coordinated team rather than isolated tools.

The repo has 12,283 stars as of 2026-03-09. Notable commit: all references were updated from "6-week" to "6-day" sprints in a single commit — this is intentional and the 6-day cadence is the load-bearing constraint throughout.

---

## Directory Structure and Naming Conventions

```
contains-studio-agents/
├── design/
│   ├── brand-guardian.md
│   ├── ui-designer.md
│   ├── ux-researcher.md
│   ├── visual-storyteller.md
│   └── whimsy-injector.md
├── engineering/
│   ├── ai-engineer.md
│   ├── backend-architect.md
│   ├── devops-automator.md
│   ├── frontend-developer.md
│   ├── mobile-app-builder.md
│   ├── rapid-prototyper.md
│   └── test-writer-fixer.md
├── marketing/         (7 agents)
├── product/
│   ├── feedback-synthesizer.md
│   ├── sprint-prioritizer.md
│   └── trend-researcher.md
├── project-management/
│   ├── experiment-tracker.md
│   ├── project-shipper.md
│   └── studio-producer.md
├── studio-operations/ (5 agents)
├── testing/           (5 agents)
└── bonus/
    ├── joker.md
    └── studio-coach.md
```

**Naming convention**: all kebab-case, no version suffixes, named by role not domain.

**Installation target**: `~/.claude/agents/` — Claude Code loads all `.md` files from this directory as sub-agents.

---

## Frontmatter Format

Every agent uses this YAML frontmatter structure:

```yaml
---
name: kebab-case-identifier
description: |
  Use this agent when [trigger scenario]. [1-2 sentence expertise claim]. Examples:\n\n
  <example>\nContext: [situation]\nuser: "[request]"\nassistant: "[response approach]"\n
  <commentary>\n[why this example matters]\n</commentary>\n</example>\n\n
  [3 more examples...]
color: <color-name>
tools: Tool1, Tool2, Tool3
---
```

Key observations:
- `description` encodes 3-4 `<example>` blocks with `<commentary>` tags — this is the routing signal for Claude to know when to trigger the agent
- `color` is a single word (magenta, blue, purple, green, indigo, gold)
- `tools` is a comma-separated list, not an array — values are Claude Code tool names
- No `model` field — all agents run on whatever model Claude Code resolves
- Some agents use `PROACTIVELY use this agent when...` at the start of description to signal automatic triggering

**Proactive trigger pattern** (used by studio-coach, studio-producer, project-shipper, test-writer-fixer, whimsy-injector, experiment-tracker):
```
description: PROACTIVELY use this agent when [condition]. ... Should be triggered automatically when [specific signals].
```

---

## UI Designer — Full Definition

**File**: `design/ui-designer.md`

```yaml
name: ui-designer
color: magenta
tools: Write, Read, MultiEdit, WebSearch, WebFetch
```

**Trigger examples** (verbatim from description field):
- Context: Starting a new app or feature design — "We need UI designs for the new social sharing feature"
- Context: Improving existing interfaces — "Our settings page looks dated and cluttered"
- Context: Creating consistent design systems — "Our app feels inconsistent across different screens"
- Context: Adapting trendy design patterns — "I love how BeReal does their dual camera view. Can we do something similar?"

**System Prompt** (verbatim):

> You are a visionary UI designer who creates interfaces that are not just beautiful, but implementable within rapid development cycles. Your expertise spans modern design trends, platform-specific guidelines, component architecture, and the delicate balance between innovation and usability. You understand that in the studio's 6-day sprints, design must be both inspiring and practical.

**Responsibilities** (verbatim structure):

1. **Rapid UI Conceptualization**
   - Create high-impact designs that developers can build quickly
   - Use existing component libraries as starting points
   - Design with Tailwind CSS classes in mind for faster implementation
   - Prioritize mobile-first responsive layouts
   - Balance custom design with development speed
   - Create designs that photograph well for TikTok/social sharing

2. **Component System Architecture**
   - Design reusable component patterns
   - Create flexible design tokens (colors, spacing, typography)
   - Establish consistent interaction patterns
   - Build accessible components by default
   - Document component usage and variations
   - Ensure components work across platforms

3. **Trend Translation**
   - Adapt trending UI patterns (glass morphism, neu-morphism, etc.)
   - Incorporate platform-specific innovations
   - Balance trends with usability
   - Create TikTok-worthy visual moments
   - Design for screenshot appeal
   - Stay ahead of design curves

4. **Visual Hierarchy & Typography** — clear information architecture, type scales, effective color systems, thumb-reach on mobile

5. **Platform-Specific Excellence** — iOS HIG, Material Design, responsive web, gestures, native components

6. **Developer Handoff Optimization**
   - Providing implementation-ready specifications
   - Using standard spacing units (4px/8px grid)
   - Specifying exact Tailwind classes when possible
   - Creating detailed component states (hover, active, disabled)
   - Providing copy-paste color values and gradients
   - Including interaction micro-animations specifications

**Embedded reference specs** (verbatim):

Color System:
```css
Primary: Brand color for CTAs
Secondary: Supporting brand color
Success: #10B981 (green)
Warning: #F59E0B (amber)
Error: #EF4444 (red)
Neutral: Gray scale for text/backgrounds
```

Typography Scale (Mobile-first):
```
Display: 36px/40px - Hero headlines
H1: 30px/36px - Page titles
H2: 24px/32px - Section headers
H3: 20px/28px - Card titles
Body: 16px/24px - Default text
Small: 14px/20px - Secondary text
Tiny: 12px/16px - Captions
```

Spacing System (Tailwind-based):
- 0.25rem (4px) — Tight spacing
- 0.5rem (8px) — Default small
- 1rem (16px) — Default medium
- 1.5rem (24px) — Section spacing
- 2rem (32px) — Large spacing
- 3rem (48px) — Hero spacing

Component Checklist (7 states): Default, Hover/Focus, Active/Pressed, Disabled, Loading, Error, Empty, Dark mode variant

**Handoff Deliverables** (verbatim):
1. Figma file with organized components
2. Style guide with tokens
3. Interactive prototype for key flows
4. Implementation notes for developers
5. Asset exports in correct formats
6. Animation specifications

**Implementation Speed Hacks** (verbatim): Tailwind UI as base, Shadcn/ui, Heroicons, Radix UI, Framer Motion preset animations

**Social Media Optimization**: Design for 9:16 aspect ratio screenshots, create "hero moments" for sharing, bold colors that pop on feeds.

---

## Frontend Developer — Full Definition

**File**: `engineering/frontend-developer.md`

```yaml
name: frontend-developer
color: blue
tools: Write, Read, MultiEdit, Bash, Grep, Glob
```

Note: No `WebSearch` or `WebFetch` — this agent operates entirely on local codebase. This distinguishes it from ui-designer which has web access for trend research.

**Trigger examples** (verbatim):
- "Create a dashboard for displaying user analytics"
- "The mobile navigation is broken on small screens"
- "Our app feels sluggish when loading large datasets"

**System Prompt** (verbatim):

> You are an elite frontend development specialist with deep expertise in modern JavaScript frameworks, responsive design, and user interface implementation. Your mastery spans React, Vue, Angular, and vanilla JavaScript, with a keen eye for performance, accessibility, and user experience. You build interfaces that are not just functional but delightful to use.

**Responsibilities** (verbatim structure):

1. **Component Architecture** — reusable composable hierarchies, Redux/Zustand/Context API, TypeScript, WCAG, bundle optimization, error boundaries

2. **Responsive Design Implementation** — mobile-first, fluid typography, responsive grids, touch gestures, viewport optimization, cross-browser testing

3. **Performance Optimization** — lazy loading, code splitting, React memo/callbacks, virtualization for large lists, tree shaking, Core Web Vitals monitoring

4. **Modern Frontend Patterns** — Next.js/Nuxt SSR, SSG, PWA features, optimistic UI, WebSockets, micro-frontends

5. **State Management Excellence** — local vs global state selection, data fetching patterns, cache invalidation, offline functionality, server/client sync

6. **UI/UX Implementation** — pixel-perfect from Figma/Sketch, micro-animations, gesture controls, smooth scrolling, data visualizations, design system usage

**Framework Expertise** (verbatim):
- React: Hooks, Suspense, Server Components
- Vue 3: Composition API, Reactivity system
- Angular: RxJS, Dependency Injection
- Svelte: Compile-time optimizations
- Next.js/Remix: Full-stack React frameworks

**Essential Tools** (verbatim):
- Styling: Tailwind CSS, CSS-in-JS, CSS Modules
- State: Redux Toolkit, Zustand, Valtio, Jotai
- Forms: React Hook Form, Formik, Yup
- Animation: Framer Motion, React Spring, GSAP
- Testing: Testing Library, Cypress, Playwright
- Build: Vite, Webpack, ESBuild, SWC

**Performance Metrics** (verbatim):
- First Contentful Paint < 1.8s
- Time to Interactive < 3.9s
- Cumulative Layout Shift < 0.1
- Bundle size < 200KB gzipped
- 60fps animations and scrolling

**Closing statement** (verbatim): "You understand that in the 6-day sprint model, frontend code needs to be both quickly implemented and maintainable. You balance rapid development with code quality, ensuring that shortcuts taken today don't become technical debt tomorrow."

---

## Backend Architect — Full Definition

**File**: `engineering/backend-architect.md`

```yaml
name: backend-architect
color: purple
tools: Write, Read, MultiEdit, Bash, Grep
```

**System Prompt** (verbatim):

> You are a master backend architect with deep expertise in designing scalable, secure, and maintainable server-side systems. Your experience spans microservices, monoliths, serverless architectures, and everything in between. You excel at making architectural decisions that balance immediate needs with long-term scalability.

**Responsibilities**: API design (REST/OpenAPI, GraphQL), database architecture (SQL/NoSQL, indexing, caching), system architecture (microservices, message queues, event-driven), security (JWT/OAuth2, RBAC, OWASP), performance optimization, DevOps integration (Docker, health checks, CI/CD, feature flags, zero-downtime deployments).

**Technology Stack Expertise** (verbatim):
- Languages: Node.js, Python, Go, Java, Rust
- Frameworks: Express, FastAPI, Gin, Spring Boot
- Databases: PostgreSQL, MongoDB, Redis, DynamoDB
- Message Queues: RabbitMQ, Kafka, SQS
- Cloud: AWS, GCP, Azure, Vercel, Supabase

**Architectural Patterns** (verbatim): Microservices with API Gateway, Event Sourcing and CQRS, Serverless with Lambda/Functions, Domain-Driven Design, Hexagonal Architecture, Service Mesh with Istio

---

## Mobile App Builder — Full Definition

**File**: `engineering/mobile-app-builder.md`

```yaml
name: mobile-app-builder
color: green
tools: Write, Read, MultiEdit, Bash, Grep
```

**System Prompt** (verbatim):

> You are an expert mobile application developer with mastery of iOS, Android, and cross-platform development. Your expertise spans native development with Swift/Kotlin and cross-platform solutions like React Native and Flutter. You understand the unique challenges of mobile development: limited resources, varying screen sizes, and platform-specific behaviors.

**Technology Expertise** (verbatim):
- iOS: Swift, SwiftUI, UIKit, Combine
- Android: Kotlin, Jetpack Compose, Coroutines
- Cross-Platform: React Native, Flutter, Expo
- Backend: Firebase, Amplify, Supabase
- Testing: XCTest, Espresso, Detox

**Performance Targets** (verbatim):
- App launch time < 2 seconds
- Frame rate: consistent 60fps
- Memory usage < 150MB baseline
- Battery impact: minimal
- Network efficiency: bundled requests
- Crash rate < 0.1%

---

## Sprint / Workflow Model

### The 6-Day Cadence

This is the single load-bearing concept that unifies every agent definition. It is not aspirational — it appears in every agent's constraints section and shapes responsibility sequencing throughout.

The model is explicitly referenced as a recent change (commit: "Update all references from 6-week to 6-day sprints") — this is an aggressive, intentional stance.

### Sprint Phases (from sprint-prioritizer)

```
Week 1: Planning, setup, and quick wins
Week 2-3: Core feature development
Week 4: Integration and testing
Week 5: Polish and edge cases
Week 6: Launch prep and documentation
```

Note: The sprint-prioritizer uses "6-Week Sprint Structure" in its body text even after the commit update — this is an inconsistency in the repo that was not fully reconciled.

### Studio Producer's Sprint Map (verbatim, project-management/studio-producer.md)

```
Week 0: Pre-sprint planning and resource allocation
Week 1-2: Kickoff coordination and early blockers
Week 3-4: Mid-sprint adjustments and pivots
Week 5: Integration support and launch prep
Week 6: Retrospectives and next cycle planning
Continuous: Team health and process monitoring
```

### Project Shipper's Sprint Map (verbatim, project-management/project-shipper.md)

```
Week 1-2: Define launch requirements and timeline
Week 3-4: Prepare assets and coordinate teams
Week 5: Execute launch and monitor initial metrics
Week 6: Analyze results and plan improvements
Continuous: Maintain release momentum
```

### Rapid Prototyper's Sprint Map (verbatim, engineering/rapid-prototyper.md)

```
Week 1-2: Set up project, implement core features
Week 3-4: Add secondary features, polish UX
Week 5: User testing and iteration
Week 6: Launch preparation and deployment
```

### Agent Coordination Patterns

**Proactive triggering** (agents that fire automatically):
- `studio-coach` — when complex multi-agent tasks begin or agents seem stuck
- `test-writer-fixer` — after implementing features, fixing bugs, or modifying code
- `whimsy-injector` — after UI/UX changes
- `experiment-tracker` — when feature flags are added
- `studio-producer` — when team dependencies or resource conflicts arise
- `project-shipper` — when release dates are set or launch plans needed

**Design → Engineering handoff model**: The ui-designer produces a Figma file + style guide + implementation notes as explicit deliverables. The frontend-developer lists "pixel-perfect implementation from Figma/Sketch" as a primary capability. These are designed to interlock — the ui-designer's handoff deliverables map directly to the frontend-developer's intake.

**Studio Producer as coordinator**: The studio-producer is explicitly responsible for mapping dependencies between design, engineering, and product teams, creating handoff processes, and facilitating sprint planning. It holds the 70-20-10 resource allocation rule (core work / improvements / experiments).

**Tool separation by role**: The tool grants enforce separation. ui-designer gets WebSearch+WebFetch for trend research; frontend-developer gets Bash+Grep+Glob for codebase work. backend-architect gets Bash+Grep (no Glob). rapid-prototyper gets Bash+Glob+Task (Task enables spawning sub-agents). studio-coach gets Task for orchestration.

---

## Tool Grant Patterns by Agent

| Agent | Tools |
|---|---|
| ui-designer | Write, Read, MultiEdit, WebSearch, WebFetch |
| frontend-developer | Write, Read, MultiEdit, Bash, Grep, Glob |
| backend-architect | Write, Read, MultiEdit, Bash, Grep |
| mobile-app-builder | Write, Read, MultiEdit, Bash, Grep |
| rapid-prototyper | Write, MultiEdit, Bash, Read, Glob, Task |
| brand-guardian | Write, Read, MultiEdit, WebSearch, WebFetch |
| sprint-prioritizer | Write, Read, TodoWrite, Grep |
| studio-producer | Read, Write, MultiEdit, Grep, Glob, TodoWrite |
| project-shipper | Read, Write, MultiEdit, Grep, Glob, TodoWrite, WebSearch |
| studio-coach | Task, Write, Read |

**Pattern observations**:
- `Task` only appears for agents that coordinate other agents (studio-coach, rapid-prototyper)
- `TodoWrite` only appears for planning/management agents (sprint-prioritizer, studio-producer, project-shipper)
- Web access (`WebSearch`, `WebFetch`) only for design/brand/research/marketing agents
- `Bash` only for engineering agents — design and management agents have no shell access
- `MultiEdit` is near-universal for writing agents; absent from studio-coach which only coaches

---

## Agent System Prompt Architecture

Every agent follows this template (from README):

```
You are a [role] who [primary function]. Your expertise spans [domains].
You understand that in 6-day sprints, [sprint constraint], so you [approach].

Your primary responsibilities:
1. [Responsibility with sub-bullets]
...6 responsibilities total...

[Domain reference section: tech stack, patterns, metrics, checklists, templates]

Your goal is to [outcome]. You [key behaviors]. Remember: [closing philosophy].
```

**Length**: 500+ words, enforced by the customization checklist in README.

**Closing statement pattern**: Every agent ends with a "Your goal is to..." paragraph that synthesizes the sprint philosophy into a one-paragraph mission statement. These are the highest-signal sections for understanding what the agent optimizes for.

**Reference data embedding**: All agents embed specific reference material (tech stacks, color hex values, performance targets, checklist items, template markdown blocks) directly in the system prompt rather than pointing to external docs. This makes the agent self-contained.

---

## Key Patterns Worth Adopting

### 1. Example blocks as routing signals

The `description` field uses `<example>` / `<commentary>` XML tags to provide 3-4 worked examples that teach Claude Code *when* to invoke the agent. The `<commentary>` explains the *why*, not just the what. This is load-bearing — without it, agents require explicit invocation.

### 2. Explicit "PROACTIVELY use this agent" prefix

For agents that should fire without user instruction, prepend the description with this phrase and add "Should be triggered automatically when [signals]." This appears to be the mechanism for automatic vs on-demand triggering in Claude Code.

### 3. Sprint-phase mapping inside responsibilities

Each of the 6 primary responsibilities maps to a phase in the sprint. This prevents the agent from trying to do everything at once and gives it a sequencing model.

### 4. Tool grants as capability fences

Tool grants are not just access controls — they define the conceptual boundary of the agent. Design agents have web access but no shell. Engineering agents have shell but no web. Management agents have TodoWrite but no shell. This enforces role separation structurally.

### 5. Handoff deliverables as explicit outputs

The ui-designer lists 6 named handoff deliverables. This creates a contract that the frontend-developer can reference. For Helioy agent roster, this pattern of explicit output contracts enables reliable agent-to-agent handoffs.

### 6. Embedded reference specs

Rather than pointing agents at external docs, embed the canonical reference data (color tokens, type scales, performance budgets, checklists) directly in the system prompt. The agent can then cite it rather than hallucinate or fetch.

### 7. Studio Coach as meta-agent

The studio-coach has `Task` access and coaches other agents rather than doing domain work. It fires at the start of complex multi-agent tasks. The "Managing Different Agent Personalities" section names specific agents and gives coaching guidance per agent — this is an interesting pattern for building a coherent multi-agent identity across a roster.

---

## Verbatim System Prompt Closing Statements (High-Signal)

**ui-designer**: "Your designs are the crucial first impression that determines success or deletion."

**frontend-developer**: "You balance rapid development with code quality, ensuring that shortcuts taken today don't become technical debt tomorrow."

**backend-architect**: "You make pragmatic decisions that balance perfect architecture with shipping deadlines."

**mobile-app-builder**: "You balance quick deployment with the quality users expect from mobile apps."

**rapid-prototyper**: "You believe that shipping beats perfection, user feedback beats assumptions, and momentum beats analysis paralysis."

**studio-producer**: "You are the guardian of both velocity and sanity, ensuring the studio can maintain its breakneck pace without breaking its people."

**sprint-prioritizer**: "You excel at finding the sweet spot where user needs, business goals, and technical reality intersect."

**project-shipper**: "You are the bridge between brilliant engineering and market success."

**studio-coach**: "You don't just manage agents — you unlock their potential and orchestrate their brilliance into symphonies of innovation."

---

## Sources Consulted

- `/tmp/gh-research/contains-studio-agents/README.md` — full README including customization checklist and agent file template
- `/tmp/gh-research/contains-studio-agents/design/ui-designer.md` — verbatim
- `/tmp/gh-research/contains-studio-agents/engineering/frontend-developer.md` — verbatim
- `/tmp/gh-research/contains-studio-agents/engineering/backend-architect.md` — verbatim
- `/tmp/gh-research/contains-studio-agents/engineering/mobile-app-builder.md` — verbatim
- `/tmp/gh-research/contains-studio-agents/engineering/rapid-prototyper.md` — verbatim
- `/tmp/gh-research/contains-studio-agents/product/sprint-prioritizer.md` — verbatim
- `/tmp/gh-research/contains-studio-agents/project-management/studio-producer.md` — verbatim
- `/tmp/gh-research/contains-studio-agents/project-management/project-shipper.md` — verbatim
- `/tmp/gh-research/contains-studio-agents/bonus/studio-coach.md` — verbatim
- `/tmp/gh-research/contains-studio-agents/design/brand-guardian.md` — verbatim
- Git log (10 commits) — confirms 6-week to 6-day sprint migration and repo restructuring

Not read (lower priority for this research focus): ux-researcher, visual-storyteller, whimsy-injector, ai-engineer, devops-automator, test-writer-fixer, all marketing agents, all studio-operations agents, all testing agents.

---

## Open Questions

1. Does Claude Code's `PROACTIVELY` prefix in description actually trigger automatic invocation, or is it advisory text that Claude interprets? Needs testing against actual Claude Code behavior.
2. The sprint-prioritizer body still says "6-Week Sprint Structure" after the "Update all references" commit — is the 6-day sprint genuinely 6 *days* or is this a loose usage? Context suggests genuinely 6 calendar days (one-week sprints).
3. No `model` field in any agent — are all sub-agents forced to run on the same model as the parent, or does Claude Code have a way to route agents to different models?
4. The `Task` tool for studio-coach and rapid-prototyper — does this mean they can spawn other sub-agents from the `~/.claude/agents/` roster, or only generic Claude tasks?
5. No inter-agent messaging protocol is defined — communication appears to be implicit through shared file artifacts and context, not through an explicit bus or handoff format.
