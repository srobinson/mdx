---
title: Agent Prompt Engineering Patterns for Specialized Engineering Roles (2025-2026)
type: research
tags: [agents, prompt-engineering, system-prompts, tool-gating, multi-agent, UX, frontend, backend, design-handoff]
summary: Comprehensive analysis of how practitioners design agent personas, gate tools, structure output contracts, and handle design-to-code handoffs in 2025-2026, drawing from open-source agent collections, Claude Code docs, MetaGPT internals, and Roo Code's custom mode system.
status: active
source: deep-research
confidence: high
created: 2026-03-09
updated: 2026-03-09
---

## Executive Summary

The craft of writing specialized agent definitions has matured significantly. Three distinct open-source agent collections (msitarzewski/agency-agents, contains-studio/agents, lst97/claude-code-sub-agents) provide concrete public examples of role-differentiated system prompts. The Claude Code subagent spec (code.claude.com/docs/en/sub-agents) and Roo Code's custom modes establish the two dominant tool-gating mechanisms in the ecosystem. MetaGPT remains the canonical reference for document-driven design-to-code handoffs, while the emerging consensus is that the `description` field, not the system prompt body, controls routing and is therefore the highest-leverage single line in any agent definition.

---

## Detailed Findings

### 1. Agent Persona Design Patterns

#### Structure observed across all three open-source collections

Every production-quality agent definition from 2025-2026 follows a consistent internal structure:

1. **YAML frontmatter** (`name`, `description`, `tools`, `model`, `color`)
2. **Role identity block** - one paragraph establishing voice, specialty, and experience frame
3. **Core mission** - 3-6 named responsibilities with sub-bullets
4. **Critical rules** - constraints framed as "what you must always do"
5. **Deliverable templates** - concrete output schemas with real code/markdown examples
6. **Workflow steps** - numbered operational sequence
7. **Communication style** - explicit examples of phrasing ("Be precise: 'Implemented virtualized table reducing render time by 80%'")
8. **Success metrics** - quantitative thresholds (e.g. "Lighthouse scores consistently exceed 90")

Source: msitarzewski/agency-agents (engineering/ and design/ directories), contains-studio/agents, lst97/claude-code-sub-agents

#### How frontend vs. backend vs. UX agents differ

**Frontend Developer** (contains-studio/agents):
- Identity framed around React/Vue/Angular frameworks, pixel-perfect implementation, Core Web Vitals
- Performance metrics embedded in the persona: LCP < 1.8s, TTI < 3.9s, bundle < 200KB gzipped, 60fps
- Strong emphasis on design-system consumption: "Pixel-perfect implementation from Figma/Sketch"
- Tools explicitly listed in frontmatter: `Write, Read, MultiEdit, Bash, Grep, Glob`
- MCP integrations: `magic` (component builder/refiner), `playwright` (browser E2E), `context7` (docs)

**Backend Architect** (msitarzewski/agency-agents):
- Identity framed around scalability, reliability, security-first architecture
- Output templates are system architecture specs, SQL schema definitions, Express.js with rate limiting/helmet
- No browser tools; no visual/screenshot tools
- Explicit "principle of least privilege" constraint built into the persona
- Success metrics: API p95 < 200ms, 99.9% uptime, database queries < 100ms avg, zero critical vulns in audits

**UX Architect** (msitarzewski/agency-agents):
- Identity bridges PM and development -- "translates specs into structure for developers"
- Primary output is a CSS design system (custom properties, spacing scales, typography, theme toggle)
- Explicitly owns: "repository topology, contract definitions, and schema compliance"
- Contains JavaScript class (`ThemeManager`) as deliverable -- UX work crosses into implementation
- Explicitly bridges to other agents: "handoff to LuxuryDeveloper"

**UX Researcher** (msitarzewski/agency-agents):
- Identity is analytical and evidence-based ("Based on 25 user interviews...")
- Outputs are research artifacts: user personas, journey maps, usability test protocols, recommendations
- No tools referencing code execution or file editing
- Output template uses quantitative reporting: task completion rates, NPS, time-on-task targets

**UX Designer** (lst97/claude-code-sub-agents):
- Tools explicitly include `mcp__playwright__browser_navigate`, `mcp__playwright__browser_snapshot` -- browser access intentional
- Tools also include `mcp__sequential-thinking__sequentialthinking` for complex user journey analysis
- Output artifacts include wireframes, interactive prototypes, and "design specifications & style guides"
- Proactive mandate in description: "Use PROACTIVELY to advocate for the user's needs throughout the entire design process"

**UI Designer** (contains-studio/agents):
- Tools: `Write, Read, MultiEdit, WebSearch, WebFetch` -- no Bash, no code execution
- Oriented toward social media and app store impressions: "Design for 9:16 aspect ratio screenshots", "TikTok-worthy visual moments"
- Developer handoff section explicitly specifies Tailwind class names, 4px/8px grid, Framer Motion preset names
- Sprint-aware: "6-day sprint model" constraint appears in persona

#### Key differentiation principle

Frontend agents need code execution (Bash), browser testing (Playwright), and read/write access. Backend agents need Bash but not browser tools. UX/design agents split: researchers need no execution; designers need browser/screenshot; architects need write but not Bash. Researchers need nothing beyond read tools and web search.

---

### 2. Tool Gating and Context Control

#### Claude Code subagent system (authoritative spec)

The Claude Code docs define a complete tool-gating model via YAML frontmatter:

```yaml
---
name: safe-researcher
description: Research agent with restricted capabilities
tools: Read, Grep, Glob, Bash
disallowedTools: Write, Edit
model: haiku
---
```

**Key mechanisms:**
- `tools` field is an allowlist (only listed tools available)
- `disallowedTools` is a denylist (removed from inherited or specified set)
- `model` selects `haiku`, `sonnet`, `opus`, or `inherit` -- routing expensive tasks to cheaper models is an explicit design goal
- `permissionMode` options: `default`, `acceptEdits`, `dontAsk`, `bypassPermissions`, `plan`
- `isolation: worktree` runs the subagent in a git worktree copy -- filesystem isolation

**Hook-based conditional gating** for finer control than the `tools` field:
```yaml
hooks:
  PreToolUse:
    - matcher: "Bash"
      hooks:
        - type: command
          command: "./scripts/validate-readonly-query.sh"
```
The hook receives tool input as JSON on stdin; exit code 2 blocks the operation. This enables allowing Bash but blocking SQL write operations, for example.

**Spawning restrictions** for orchestrators:
```yaml
tools: Agent(worker, researcher), Read, Bash
```
This allowlists only `worker` and `researcher` subagent types. Attempts to spawn anything else fail. If `Agent` is omitted entirely, the agent cannot spawn subagents at all.

Source: code.claude.com/docs/en/sub-agents

#### Roo Code custom modes (parallel ecosystem)

Roo Code (VS Code extension) uses a different but equivalent model via JSON/YAML config:

```yaml
slug: db-specialist
name: Database Specialist
roleDefinition: |
  You are a database specialist with expertise in schema design,
  query optimization, and data modeling.
groups:
  - read
  - [edit, { fileRegex: "\\.(sql|migration)$", description: "SQL and migration files only" }]
  - command
```

**Four tool groups:** `read`, `edit`, `command`, `mcp`

The `fileRegex` pattern on the `edit` group provides file-type scoped editing -- a backend agent editing only `.sql` files, a frontend agent editing only `.tsx` files. This is Roo's primary mechanism where Claude Code uses `disallowedTools`.

**Typical gating patterns from the docs:**
- Read-only review agent: `groups: [read]`
- Test engineer: `groups: [read, [edit, {fileRegex: "\\.(test|spec)\\.ts$"}], command]`
- Documentation agent: `groups: [read, [edit, {fileRegex: "\\.md$"}]]`
- Full-access developer: all four groups

Source: docs.roocode.com/features/custom-modes

#### Observed tool lists by role type (from collected examples)

| Role | Bash/Command | Write/Edit | Browser/Playwright | WebSearch | MCP tools |
|------|-------------|------------|-------------------|-----------|-----------|
| Frontend Dev | yes | yes | yes (Playwright) | yes | magic, context7 |
| Backend Architect | yes | yes | no | yes | context7 |
| UX Architect | no | yes (CSS/JS files) | no | no | -- |
| UX Researcher | no | no | no | yes | -- |
| UX Designer | no | yes | yes (navigate/snapshot) | yes | context7, sequential-thinking |
| UI Designer | no | yes | no (WebFetch only) | yes | -- |
| Code Reviewer | no | no | no | no | -- |
| Debugger | yes | yes | no | no | -- |
| Agent Organizer | no | yes (CLAUDE.md only) | no | no | -- |

---

### 3. Output Format Contracts

#### Design agent outputs

Design agents in 2025-2026 produce primarily **prose-structured markdown documents** with embedded code artifacts. Common outputs:

**UX Architect** produces:
- CSS design system file (`design-system.css`) with custom properties for colors, typography, spacing
- Layout framework file (`layout.css`) with grid/container patterns
- JavaScript `ThemeManager` class
- Deliverable template: `# [Project] Technical Architecture & UX Foundation` with sections for CSS Architecture, UX Structure, Responsive Strategy, Accessibility Foundation, Developer Implementation Guide

**UI Designer** produces:
- Figma file reference + organized components
- Style guide with tokens (explicit Tailwind classes and hex values)
- Interactive prototype
- Implementation notes including: exact Tailwind utility class names, Framer Motion preset names, Radix UI component references, Heroicons naming
- Component checklist covering all states (default, hover, active, disabled, loading, error, empty, dark mode variant)

**UX Researcher** produces:
- Research study plan (objectives, methodology, participant criteria, protocol)
- User persona template (demographics, behavioral patterns, goals, quotes with evidence counts)
- Usability testing protocol (session structure, data collection)
- Findings report with high/medium/long-term prioritized recommendations

#### Engineering agent outputs

Engineering agents produce code with structured commentary:

**Frontend Developer** deliverable template:
```markdown
# [Project Name] Frontend Implementation
## UI Implementation
**Framework**: [React/Vue/Angular with version and reasoning]
**State Management**: [Redux/Zustand/Context API]
## Performance Optimization
**Core Web Vitals**: [LCP < 2.5s, FID < 100ms, CLS < 0.1]
## Accessibility Implementation
**WCAG Compliance**: [AA compliance specifics]
```

**Backend Architect** deliverable is a system architecture specification document:
```markdown
# System Architecture Specification
## High-Level Architecture
**Architecture Pattern**: [Microservices/Monolith/Serverless]
**Communication Pattern**: [REST/GraphQL/gRPC/Event-driven]
## Service Decomposition
[per-service: database, cache, APIs, events]
```

The key distinction: design agents output **specifications** (what to build), engineering agents output **implementations** (built code + explanatory structure). The UX Architect is a bridge -- it outputs specifications expressed as working CSS/JS starter code.

---

### 4. Agent Collaboration and Design-to-Code Handoffs

#### MetaGPT pipeline (document-driven)

MetaGPT is the canonical multi-agent pipeline for design-to-code handoff. The pipeline is strictly sequential and document-mediated:

1. **Product Manager** (`Alice`) ingests user requirement, outputs **PRD** containing: user stories, requirement pool, competitive analysis, feature priorities. Tools: `Browser`, `Editor`, `SearchEnhancedQA`.
2. **Architect** subscribes to PRD, outputs **System Design** document: tech stack, file list, data structures, interface definitions. No browser access.
3. **Project Manager** reads System Design, outputs **Task List**: specific coding assignments per file/function.
4. **Engineer(s)** pick up tasks, write code guided by architecture document.
5. **QA Engineer** reviews and tests.

Critical design choice: agents communicate through documents and diagrams, not dialogue. This prevents context pollution and makes intermediate outputs auditable. The PRD is the handoff format between PM and Architect; the System Design is the handoff between Architect and Engineer.

Source: MetaGPT ICLR 2024 paper, arxiv.org/html/2308.00352v6; FoundationAgents/MetaGPT GitHub

#### Claude Code's agent chaining pattern

The Claude Code docs recommend chaining subagents via the main conversation:
```
Use the code-reviewer subagent to find performance issues,
then use the optimizer subagent to fix them
```
Each subagent completes its task and returns a summary to the main conversation, which then passes relevant context to the next. The handoff format is whatever the first subagent returns as its final output -- typically a structured markdown report.

For design-to-code specifically, the pattern would be:
1. UX Designer subagent: produces component spec + wireframe description in markdown
2. Main conversation passes the spec to Frontend Developer subagent
3. Frontend Developer implements against the spec

The intermediate format is unstructured markdown in current practice -- no formal schema between design and implementation subagents.

#### contains-studio's sprint model

The contains-studio/agents collection is built around 6-day sprints with explicit cross-agent collaboration. The UI Designer's `whenToUse` description mentions "implementation-ready specifications" and lists handoff deliverables including "implementation notes for developers" and "Figma file with organized components". The Frontend Developer's identity includes "Pixel-perfect implementation from Figma/Sketch" as a core responsibility. The handoff is implicit -- the UI Designer produces a Figma link + annotated spec, the Frontend Developer consumes it.

#### agency-agents' explicit bridging role

The UX Architect agent in msitarzewski/agency-agents explicitly names its bridging function: "Take ProjectManager task lists and add technical foundation layer" and "Provide clear handoff specifications for LuxuryDeveloper." This is the clearest example of a dedicated bridge agent whose primary function is translation between design intent and implementable code structure. Its output (CSS design system + layout framework + theme toggle) is directly consumable code, not a specification requiring further translation.

---

### 5. Real-World Agent Prompt Examples

#### The `description` field as primary routing mechanism

The most important single insight from 2025-2026 practice: Claude Code uses the `description` field (not the system prompt body) to decide when to delegate to a subagent. High-quality descriptions follow the pattern:

```
Use this agent when [specific trigger condition]. This agent excels at [capability]. Examples:
<example>
Context: [situation]
user: "[request]"
assistant: "[how orchestrator decides to delegate]"
<commentary>[why this is the right agent]</commentary>
</example>
```

The lst97 collection includes 2-3 concrete `<example>` blocks per agent definition. This is the pattern that produces reliable automatic delegation.

#### Model routing by role

From observed frontmatter across the collections:
- **Agent Organizer** (orchestrator): `model: haiku` -- deliberate choice to use cheapest model for routing/delegation decisions which don't require reasoning depth
- **Frontend Developer**: `model: sonnet` -- mid-tier for implementation
- **UX Designer**: `model: sonnet`
- **Data Scientist**: `model: sonnet` (explicit in Claude Code examples)
- Heavy reasoning roles default to `inherit` (main conversation model)

#### Persistent memory per agent

Claude Code supports `memory: user|project|local` in subagent frontmatter. The memory directory (`~/.claude/agent-memory/<name-of-agent>/`) persists across conversations. The first 200 lines of `MEMORY.md` are auto-injected. This enables a code-reviewer agent that builds up codebase-specific patterns over time, or a UX researcher agent that maintains institutional knowledge about user segments.

#### Constraint framing patterns

Effective agent constraints are framed as positive imperatives, not prohibitions:
- "Security-First Architecture: Implement defense in depth across all system layers"
- "Foundation-First Approach: Create scalable CSS architecture before implementation begins"
- "Research Methodology First: Establish clear research questions before selecting methods"

This is distinct from "do not..." framing. The Augment Code blog notes: "Avoid Overfitting to Examples... Telling models what not to do is safer [than examples]." The combination is: positive imperatives for stance, negative constraints for specific behaviors to avoid.

---

## Sources Consulted

**GitHub repositories (primary sources with direct file access)**
- [msitarzewski/agency-agents](https://github.com/msitarzewski/agency-agents) -- complete agent collection with engineering/, design/, product/ directories
- [contains-studio/agents](https://github.com/contains-studio/agents) -- 6-day sprint model, engineering/ and design/ agents
- [lst97/claude-code-sub-agents](https://github.com/lst97/claude-code-sub-agents) -- 54+ agents across domains with explicit MCP tool lists
- [FoundationAgents/MetaGPT](https://github.com/FoundationAgents/MetaGPT) -- metagpt/roles/ Python implementations

**Documentation (authoritative specs)**
- [Claude Code Sub-Agents Documentation](https://code.claude.com/docs/en/sub-agents) -- complete frontmatter schema, tool gating, permission modes, hooks, memory
- [Roo Code Custom Modes](https://docs.roocode.com/features/custom-modes) -- fileRegex tool gating, role definition schema

**Research / papers**
- [MetaGPT ICLR 2024](https://arxiv.org/html/2308.00352v6) -- document-driven handoff architecture
- [VoltAgent/awesome-agent-skills](https://github.com/VoltAgent/awesome-agent-skills) -- community agent skill collection

**Blog posts / HN**
- [Augment Code: 11 Prompting Techniques for Agents](https://www.augmentcode.com/blog/how-to-build-your-agent-11-prompting-techniques-for-better-ai-agents)
- [Cursor Agent System Prompt leak discussion](https://news.ycombinator.com/item?id=43305622)
- [IBM: MetaGPT multi-agent PRD automation](https://www.ibm.com/think/tutorials/multi-agent-prd-ai-automation-metagpt-ollama-deepseek)

---

## Source Quality Assessment

**High confidence:**
- Claude Code subagent spec: official Anthropic documentation, current as of early 2026
- msitarzewski/agency-agents, contains-studio/agents, lst97 collections: actual working agent definitions, directly inspected via GitHub API
- MetaGPT role implementations: source code directly read

**Medium confidence:**
- MetaGPT handoff architecture: paper from 2023/2024, some evolution since then; MGX (MetaGPT X) launched Feb 2025 with updated architecture not fully examined
- Roo Code custom modes: docs are current but the fileRegex behavior details were from docs page summary, not direct testing

**Gaps:**
- No direct examination of Cursor's internal agent role system prompts (HN discussion referenced them but gist content was not accessible)
- ChatDev's specific inception prompting templates not directly retrieved
- No Reddit community discussion retrieved (site:reddit.com queries returned no results for technical specifics; community discourse on agent prompt craft may exist on Discord servers not indexed)

---

## Open Questions

1. **Design-to-code intermediate format**: There is no established standard format for the output a UX Designer agent passes to a Frontend Developer agent. Current practice is informal markdown. Is there a structured component spec format (JSON Schema? MDX? Storybook story format?) that would make this handoff more reliable?

2. **Model selection for design agents**: The observed pattern assigns haiku to orchestrators and sonnet to implementation agents. What is the right model tier for UX Researcher agents whose primary output is qualitative synthesis? None of the reviewed collections document this decision.

3. **Tool access for browser-based design review**: The lst97 UX Designer includes `mcp__playwright__browser_snapshot` for visual inspection. No collection was found using screenshot diffing between design spec and implemented component. This gap is likely a significant source of design drift.

4. **Long-running agent memory for UX research**: The Claude Code memory system is designed for per-agent persistence. No example was found of a UX Researcher agent actually maintaining cross-session persona libraries or research findings in its memory directory.

5. **MetaGPT X architecture**: MGX launched Feb 2025 as the production evolution. Its agent role definitions and handoff schemas were not examined in this research pass.

---

## Actionable Takeaways

**For Nancy/nancyr agent design:**

1. The `description` field drives routing -- write it as a triggering condition with `<example>` blocks, not a summary of capabilities. This is the single highest-ROI line in any agent definition.

2. Model tier routing is a first-class concern: use haiku for orchestration/delegation, sonnet for implementation, opus for architecture design. Encode this in the frontmatter, not in the orchestrator's system prompt logic.

3. Separate UX Architect from UX Designer from UX Researcher into three distinct agents. Each has a different tool profile and output format. Merging them into "UX agent" creates an incoherent tool set.

4. For design-to-code handoffs, the MetaGPT pattern is the proven approach: document-mediated, sequential, with explicit artifact schemas at each stage. The UX Architect → Frontend Developer handoff should produce a CSS design system + component inventory document, not a verbal description.

5. Roo Code's `fileRegex` mechanism on the edit group is a cleaner constraint than blanket tool allowlists for cases where you want an agent to edit its domain files but not touch infrastructure. Claude Code's `disallowedTools` is coarser but simpler.

6. Build persistent memory (`memory: project`) into any UX Researcher or Architecture Review agent. These roles accumulate knowledge that degrades without continuity.

**Follow-up research suggested:**
- Examine MGX (MetaGPT X) role specs and handoff contracts
- Search for component spec formats used in AI-assisted design-to-code tools (v0, Lovable, Bolt.new)
- Retrieve contains-studio/agents README for sprint model documentation and explicit agent collaboration graph
