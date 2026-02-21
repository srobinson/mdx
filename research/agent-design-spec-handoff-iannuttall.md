---
title: "Design Spec Handoff Contract and Frontend Designer Pattern (iannuttall/claude-agents)"
type: research
tags: [agents, claude-code, frontend-design, agent-definitions, handoff, design-spec, frontmatter]
summary: Seven Claude Code subagent definitions with full verbatim content, covering the frontend-designer's frontend-design-spec.md handoff contract, all frontmatter fields, and design-to-code workflow patterns.
status: active
source: github-researcher
confidence: high
created: 2026-03-09
updated: 2026-03-09
---

## Executive Summary

`iannuttall/claude-agents` is a collection of seven Claude Code subagent definitions (2,023 stars as of 2026-03-08) stored as `.md` files under `agents/`. Each file uses YAML frontmatter to declare the agent's name, description (with inline examples), optional tool allowlist, and color. The `frontend-designer` agent is the most complex: it drives a full design-analysis workflow and produces a `frontend-design-spec.md` handoff artifact for developers. There is no paired frontend-developer agent in this repo — the handoff is one-directional, from designer to human developer.

---

## Architecture

### Directory Structure

```
claude-agents/
├── README.md
├── LICENSE
└── agents/
    ├── code-refactorer.md
    ├── content-writer.md
    ├── frontend-designer.md
    ├── prd-writer.md
    ├── project-task-planner.md
    ├── security-auditor.md
    └── vibe-coding-coach.md
```

### Installation Paths

- Project-scoped: `.claude/agents/*.md`
- Global (all projects): `~/.claude/agents/*.md`

Claude Code auto-discovers agents from either location.

---

## Frontmatter Contract

All agents share this frontmatter schema:

```yaml
---
name: <kebab-case-slug>
description: <prose trigger description with inline XML examples>
tools: <comma-separated tool allowlist>   # optional
color: <named color>
---
```

**Mandatory fields**: `name`, `description`, `color`

**Optional fields**: `tools` — when omitted, the agent has access to all tools (as seen in `frontend-designer` and `content-writer`). When present, it restricts the agent to a named subset.

**Description format**: The description field doubles as the routing trigger. It includes a prose explanation followed by one to three `<example>` blocks with `Context:`, `user:`, `assistant:`, and `<commentary>` sub-fields, all inlined as a single string value. This is the mechanism by which Claude Code decides which agent to invoke.

**Color values observed**: `orange`, `blue`, `green`, `red`, `purple`, `cyan`, `pink`

---

## Key Patterns

### Pattern 1: Description-as-Router

The `description` field is not documentation — it is the invocation trigger. It must contain enough signal for Claude to recognize when to route to this agent. The inline `<example>` blocks are training-style examples showing the user utterance, the assistant's routing decision, and a commentary explaining the reasoning. This mirrors few-shot prompting inside a YAML string.

### Pattern 2: Named Output Artifact

Every agent that produces documentation names its output file explicitly in the system prompt body:
- `frontend-designer` → `frontend-design-spec.md`
- `prd-writer` → `prd.md`
- `project-task-planner` → `plan.md`
- `security-auditor` → `security-report.md`

The agent asks the user to confirm output location and suggests a default if none is provided (e.g., `/docs/design/`, project root, `/docs/security/`).

### Pattern 3: Bounded Scope

Agents explicitly state what they will NOT do. `prd-writer`: "You are not responsible or allowed to create tasks or actions." `code-refactorer` lists explicit prohibitions against adding features or changing external behavior. This prevents scope creep within a subagent's turn.

### Pattern 4: Tool Allowlisting

When a tool list is present, it acts as a capability fence:
- `code-refactorer`: `Edit, MultiEdit, Write, NotebookEdit, Grep, LS, Read`
- `prd-writer`: `Task, Bash, Grep, LS, Read, Write, WebSearch, Glob`
- `project-task-planner`: `Task, Bash, Edit, MultiEdit, Write, NotebookEdit, Grep, LS, Read, ExitPlanMode, TodoWrite, WebSearch`
- `security-auditor`: `Task, Bash, Edit, MultiEdit, Write, NotebookEdit`

`frontend-designer` has no `tools` field — it relies on the full tool suite including image analysis for mockup processing.

---

## Detailed Findings

### 1. frontend-designer — Full Definition Analysis

**Frontmatter**:
```yaml
name: frontend-designer
description: Use this agent when you need to convert design mockups, wireframes, or
  visual concepts into detailed technical specifications and implementation guides
  for frontend development. [+ 3 inline examples]
color: orange
```
No `tools` restriction — full tool access intended.

**Role definition** (verbatim opening):
> You are an expert frontend designer and UI/UX engineer specializing in converting design concepts into production-ready component architectures and design systems.
> Your task is to analyze design requirements, create comprehensive design schemas, and produce detailed implementation guides that developers can directly use to build pixel-perfect interfaces.

**Workflow phases**:

1. **Initial Discovery** — Asks about tech stack (framework, CSS approach, component libraries, state management, build tools, existing design tokens) and collects design assets (mockups, Figma links, brand guidelines, reference sites).

2. **Visual Decomposition** — When images are provided, systematically analyzes visual elements using atomic design (atoms/molecules/organisms), extracts color palettes, typography scales, spacing, component hierarchy, interaction patterns, responsive indicators.

3. **JSON Schema Generation** — Produces a structured design schema before writing the spec:
```json
{
  "designSystem": {
    "colors": {},
    "typography": {},
    "spacing": {},
    "breakpoints": {},
    "shadows": {},
    "borderRadius": {},
    "animations": {}
  },
  "components": {
    "[ComponentName]": {
      "variants": [],
      "states": [],
      "props": {},
      "accessibility": {},
      "responsive": {},
      "interactions": {}
    }
  },
  "layouts": {},
  "patterns": {}
}
```

4. **Tool Usage** — Actively searches for best practices, accessibility standards, performance techniques, and component library docs.

5. **Iterative Feedback Loop** — After initial output, gathers feedback on specific components, missing patterns, vision alignment, and accessibility priorities before refining.

### 2. frontend-design-spec.md Output Contract

The agent writes to a user-confirmed location (suggests `/docs/design/` as default). The full document template (verbatim from agent definition):

```markdown
# Frontend Design Specification

## Project Overview
[Brief description of the design goals and user needs]

## Technology Stack
- Framework: [User's framework]
- Styling: [CSS approach]
- Components: [Component libraries]

## Design System Foundation

### Color Palette
[Extracted colors with semantic naming and use cases]

### Typography Scale
[Font families, sizes, weights, line heights]

### Spacing System
[Consistent spacing values and their applications]

### Component Architecture

#### [Component Name]
**Purpose**: [What this component does]
**Variants**: [List of variants with use cases]

**Props Interface**:
```typescript
interface [ComponentName]Props {
  // Detailed prop definitions
}
```

**Visual Specifications**:
- [ ] Base styles and dimensions
- [ ] Hover/Active/Focus states
- [ ] Dark mode considerations
- [ ] Responsive breakpoints
- [ ] Animation details

**Implementation Example**:
```jsx
// Complete component code example
```

**Accessibility Requirements**:
- [ ] ARIA labels and roles
- [ ] Keyboard navigation
- [ ] Screen reader compatibility
- [ ] Color contrast compliance

### Layout Patterns
[Grid systems, flex patterns, common layouts]

### Interaction Patterns
[Modals, tooltips, navigation patterns, form behaviors]

## Implementation Roadmap
1. [ ] Set up design tokens
2. [ ] Create base components
3. [ ] Build composite components
4. [ ] Implement layouts
5. [ ] Add interactions
6. [ ] Accessibility testing
7. [ ] Performance optimization

## Feedback & Iteration Notes
[Space for user feedback and design iterations]
```

**What the spec contains**:
- Project overview and tech stack declaration
- Design tokens: colors (semantic), typography scale, spacing system
- Per-component: purpose, variants, TypeScript props interface, visual states, implementation example in JSX, accessibility checklist (ARIA, keyboard nav, screen reader, WCAG contrast)
- Layout patterns and interaction patterns
- Implementation roadmap as a checkbox sequence
- A dedicated feedback section for iteration

**What it does NOT contain**: No dark mode tokens block, no animation keyframes section, no icon system, no z-index scale. These are notable gaps compared to production design systems.

### 3. Design-to-Code Handoff Model

There is no `frontend-developer` agent in this repo. The handoff is from `frontend-designer` (subagent) to the human developer or the main Claude Code session. The `frontend-design-spec.md` is the artifact that bridges the two. The developer reads the spec and implements from it — there is no automated agent-to-agent handoff mechanism.

The workflow chain that does exist is:
```
prd-writer → plan.md
project-task-planner (reads prd.md) → plan.md
frontend-designer (reads mockups/briefs) → frontend-design-spec.md
```

These agents are designed to be invoked sequentially by a human, not automatically chained.

### 4. Other Agent Definitions Summary

**code-refactorer** (`color: blue`)
- Improves code structure/readability/maintainability without changing functionality
- Restricted tool set: `Edit, MultiEdit, Write, NotebookEdit, Grep, LS, Read`
- Explicit prohibitions: no new features, no API changes, no suggestions without code examples
- Process: initial assessment → clarify goals → systematic analysis (duplication, naming, complexity, function size, patterns, organization, performance) → explain what/why/fix for each issue

**prd-writer** (`color: green`)
- Produces `prd.md` from a feature or project description
- Tools: `Task, Bash, Grep, LS, Read, Write, WebSearch, Glob`
- Output: 10-section PRD (product overview, goals, personas, functional requirements, UX, narrative, success metrics, technical considerations, milestones, user stories)
- User stories require unique IDs (e.g., `US-001`), acceptance criteria, and must cover edge cases
- Explicit scope: "You are not responsible or allowed to create tasks or actions."

**project-task-planner** (`color: purple`)
- Requires a PRD as input — will refuse and request one if not provided
- Produces `plan.md` with 10 development phases as checkboxes
- Tools include `ExitPlanMode` and `TodoWrite` — this agent operates in plan mode
- Phases: Setup → Backend Foundation → Feature Backend → Frontend Foundation → Feature Frontend → Integration → Testing → Documentation → Deployment → Maintenance

**security-auditor** (`color: red`)
- Produces `security-report.md` with findings by severity (Critical/High/Medium/Low)
- Tools: `Task, Bash, Edit, MultiEdit, Write, NotebookEdit`
- Covers 8 vulnerability categories: Auth/Authz, Input Validation, Data Protection, API Security, Web App Security, Infrastructure, Dependency Management, Mobile, DevOps/CI-CD
- Uses OWASP/CWE terminology; each finding includes location, description, impact, remediation checklist, and references

**content-writer** (`color: cyan`)
- Two operating modes: OUTLINE and WRITE
- No tools restriction — uses web search for fact-checking
- Explicit word blocklist (delve, tapestry, vibrant, etc.) and forbidden phrase patterns
- Outline: max 5 H2 sections, saved to `.content/{slug}.md`
- Write: max 300 words per section, work section-by-section

**vibe-coding-coach** (`color: pink`)
- No tools restriction; no named output artifact
- Targets non-technical users building apps through conversation
- Implements professional security practices (parameterized queries, CSRF tokens, encryption) while hiding technical complexity from the user
- Success metric: how well the app matches the user's stated "vibe", not code elegance

---

## Dependencies

No external dependencies. These are pure Markdown/YAML files read by Claude Code's native subagent loader. The only runtime requirement is Claude Code itself and any tools declared in the frontmatter (all standard Claude Code built-ins).

---

## Relevance to Helioy

This repo confirms the frontmatter contract for Claude Code agents deployed to `~/.claude/agents/` or `.claude/agents/`. Key adoption signals:

1. **Frontmatter fields**: `name`, `description` (with `<example>` blocks), `color`, and optionally `tools` are sufficient for a working agent definition. No other fields are required.

2. **The description-as-router pattern** is the correct mechanism for automatic invocation. The inline `<example>` blocks with `<commentary>` tags are specifically structured to teach Claude Code when to route to the agent.

3. **Named output artifacts** (`.md` files) are the standard handoff mechanism. There is no agent-to-agent message passing in this pattern — a file written by one agent is read by the next.

4. **The frontend-design-spec.md schema** provides a concrete template for what a design handoff document should contain. For Helioy's own frontend agents, this is worth extending with: design token variables (CSS custom properties), dark mode token overrides, animation token system, and icon/asset inventory.

5. **The missing frontend-developer agent** is notable. A complete Helioy agent pair would include both a designer agent (produces spec) and a developer agent (consumes spec and writes code), linked by the shared artifact path.

---

## Sources Consulted

- `README.md`
- `agents/frontend-designer.md` (full content)
- `agents/code-refactorer.md` (full content)
- `agents/prd-writer.md` (full content)
- `agents/project-task-planner.md` (full content)
- `agents/security-auditor.md` (full content)
- `agents/content-writer.md` (full content)
- `agents/vibe-coding-coach.md` (full content)
- `gh repo view` metadata (2,023 stars, updated 2026-03-08)
- `git log` (single initial commit)
- Open issues and PRs (3 open issues, 2 open PRs — repo is lightly maintained)

---

## Open Questions

1. Does Claude Code parse `<example>` blocks inside the description string, or does it treat the entire description as unstructured text? The examples suggest it has semantic significance, but the mechanism is not documented here.
2. What is the exact behavior when `tools` is omitted versus explicitly listing all tools? Is there a security difference?
3. The `project-task-planner` uses `ExitPlanMode` — this implies agents can be invoked while Claude Code is in plan mode. How does that interact with the agent lifecycle?
4. There is no `frontend-developer` agent here. Worth building one that explicitly reads `frontend-design-spec.md` as its required input artifact — mirroring how `project-task-planner` requires a PRD.
