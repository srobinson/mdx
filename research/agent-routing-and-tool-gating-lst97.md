---
title: "Description-Driven Routing and MCP Tool Gating Patterns (lst97/claude-code-sub-agents)"
type: research
tags: [claude-code, sub-agents, agent-design, ux, frontend, backend, mobile, mcp, tool-gating]
summary: 33 specialized Claude Code sub-agents with strong description-driven routing patterns, MCP tool integration per agent role, and a shared core philosophy block applied consistently across engineering agents.
status: active
source: github-researcher
confidence: high
created: 2026-03-09
updated: 2026-03-09
---

# lst97 Claude Code Sub-Agents — Design and Engineering Agent Analysis

## Executive Summary

This repository contains 33 specialized Claude Code sub-agents organized into 7 category directories. The agents use a consistent description field pattern with "Use PROACTIVELY" framing to drive automatic routing. Each engineering agent carries a curated MCP tool list, with `context7` near-universal and `sequential-thinking`, `playwright`, and `magic` gated to role-appropriate agents. A shared "Core Development Philosophy" block (Process & Quality, Technical Standards, Decision Making) appears verbatim across all development agents — indicating it was authored once and copy-pasted. The actual differentiation lives in role-specific competencies, guiding principles, and output format sections.

---

## Directory Structure and Naming Conventions

```
agents/
  agent-organizer.md           # Meta-orchestrator — lives at root, not in a category
  business/
    product-manager.md
  data-ai/
    ai-engineer.md
    data-engineer.md
    data-scientist.md
    database-optimizer.md
    graphql-architect.md
    ml-engineer.md
    postgres-pro.md
    prompt-engineer.md
  development/
    backend-architect.md
    dx-optimizer.md
    electorn-pro.md             # Typo in filename (electorn vs electron)
    frontend-developer.md
    full-stack-developer.md
    golang-pro.md
    legacy-modernizer.md
    mobile-developer.md
    nextjs-pro.md
    python-pro.md
    react-pro.md
    typescript-pro.md
    ui-designer.md
    ux-designer.md
  infrastructure/
    cloud-architect.md
    deployment-engineer.md
    devops-incident-responder.md
    incident-responder.md
    performance-engineer.md
  quality-testing/
    architect-review.md
    code-reviewer.md
    debugger.md
    qa-expert.md
    test-automator.md
  security/
    security-auditor.md
  specialization/
    api-documenter.md
    documentation-expert.md
```

Naming: lowercase kebab-case. Language/platform specialists use `-pro` suffix (react-pro, golang-pro, python-pro, nextjs-pro, typescript-pro, postgres-pro). The `electorn-pro.md` typo has persisted.

---

## Frontmatter Format

Every agent file uses the same four fields:

```yaml
---
name: kebab-case-name
description: <routing description — always ends with a "Use PROACTIVELY/when" trigger clause>
tools: Read, Write, Edit, MultiEdit, Grep, Glob, Bash, LS, WebSearch, WebFetch, TodoWrite, Task, [mcp tools...]
model: sonnet | haiku
---
```

No `disallowedTools` field appears anywhere in this collection. Tool gating is done exclusively through the `tools` allowlist — agents receive only the tools they need, nothing is explicitly forbidden.

`model: haiku` is used for `agent-organizer` and `code-reviewer` — the meta/orchestration and review roles. All implementation agents use `model: sonnet`.

---

## Description Field Patterns — Routing Trigger Analysis

The description field is the primary routing signal. Five best examples with verbatim text:

### 1. ux-designer — Empathy framing + lifecycle scope

```
A creative and empathetic professional focused on enhancing user satisfaction by improving the usability, accessibility, and pleasure provided in the interaction between the user and a product. Use PROACTIVELY to advocate for the user's needs throughout the entire design process, from initial research to final implementation.
```

Pattern: persona description + full-lifecycle scope ("entire design process, from initial research to final implementation") + advocacy framing.

### 2. mobile-developer — Scope enumeration as trigger

```
Architects and leads the development of sophisticated, cross-platform mobile applications using React Native and Flutter. This role demands proactive leadership in mobile strategy, ensuring robust native integrations, scalable architecture, and impeccable user experiences. Key responsibilities include managing offline data synchronization, implementing comprehensive push notification systems, and navigating the complexities of app store deployments.
```

Pattern: Enumerates specific technical responsibilities (offline sync, push notifications, app store) as routing triggers. No explicit "Use when" clause — instead lists responsibilities to signal scope.

### 3. performance-engineer — Lifecycle breadth + cultural role

```
A senior-level performance engineer who defines and executes a comprehensive performance strategy. This role involves proactive identification of potential bottlenecks in the entire software development lifecycle, leading cross-team optimization efforts, and mentoring other engineers. Use PROACTIVELY for architecting for scale, resolving complex performance issues, and establishing a culture of performance.
```

Pattern: Three-part "Use PROACTIVELY for" list covering architectural (scale), reactive (issues), and organizational (culture) triggers. Broadest trigger scope in the collection.

### 4. security-auditor — Compliance keyword saturation

```
A senior application security auditor and ethical hacker, specializing in identifying, evaluating, and mitigating security vulnerabilities throughout the entire software development lifecycle. Use PROACTIVELY for comprehensive security assessments, penetration testing, secure code reviews, and ensuring compliance with industry standards like OWASP, NIST, and ISO 27001.
```

Pattern: Lists specific methodologies (penetration testing, SAST/DAST) and named standards (OWASP, NIST, ISO 27001) as routing keywords. Standards are load-bearing for routing.

### 5. agent-organizer — Anti-pattern: orchestration routing

```
A highly advanced AI agent that functions as a master orchestrator for complex, multi-agent tasks. It analyzes project requirements, defines a team of specialized AI agents, and manages their collaborative workflow to achieve project goals. Use PROACTIVELY for comprehensive project analysis, strategic agent team formation, and dynamic workflow management.
```

Pattern: Explicitly frames the agent as a meta-layer. "Use PROACTIVELY for" targets abstract workflow concepts (project analysis, team formation, workflow management) rather than technical tasks.

---

## UX Designer — Full Agent Definition

**File**: `agents/development/ux-designer.md`

**Frontmatter** (verbatim):
```yaml
---
name: ux-designer
description: A creative and empathetic professional focused on enhancing user satisfaction by improving the usability, accessibility, and pleasure provided in the interaction between the user and a product. Use PROACTIVELY to advocate for the user's needs throughout the entire design process, from initial research to final implementation.
tools: Read, Write, Edit, MultiEdit, Grep, Glob, Bash, LS, WebSearch, WebFetch, TodoWrite, Task, mcp__context7__resolve-library-id, mcp__context7__get-library-docs, mcp__sequential-thinking__sequentialthinking, mcp__playwright__browser_navigate, mcp__playwright__browser_snapshot
model: sonnet
---
```

**MCP tools**: `context7` (resolve-library-id, get-library-docs), `sequential-thinking` (sequentialthinking), `playwright` (browser_navigate, browser_snapshot — read-only; no click/fill/evaluate).

**MCP Integration section** (verbatim):
```
- context7: Research UX methodologies, accessibility standards, design pattern libraries
- sequential-thinking: Complex user journey analysis, systematic usability evaluation
```

Note: playwright is declared in tools but not mentioned in the MCP Integration section. The UX agent has read-only playwright access (navigate + snapshot) without interaction capabilities. This is intentional differentiation from frontend-developer and performance-engineer which get fuller playwright access.

**Body structure**:
- Role, Expertise, Key Capabilities header block
- MCP Integration section
- Core Competencies (user research, IA, wireframing, interaction design, usability testing, visual design, collaboration)
- Guiding Principles (7 numbered principles: user-centricity, empathy, clarity, consistency, hierarchy, accessibility, user control)
- Expected Output (Research artifacts, Design artifacts, Handoff artifacts — organized in three groups)
- Constraints & Assumptions (technical constraints, business requirements, scope creep, regulatory, time/budget)

---

## UI Designer — Full Agent Definition

**File**: `agents/development/ui-designer.md`

**Frontmatter** (verbatim):
```yaml
---
name: ui-designer
description: A creative and detail-oriented AI UI Designer focused on creating visually appealing, intuitive, and user-friendly interfaces for digital products. Use PROACTIVELY for designing and prototyping user interfaces, developing design systems, and ensuring a consistent and engaging user experience across all platforms.
tools: Read, Write, Edit, MultiEdit, Grep, Glob, Bash, LS, WebSearch, WebFetch, TodoWrite, Task, mcp__magic__21st_magic_component_builder, mcp__magic__21st_magic_component_refiner, mcp__context7__resolve-library-id, mcp__context7__get-library-docs
model: sonnet
---
```

**MCP tools**: `magic` (component_builder, component_refiner), `context7` (resolve-library-id, get-library-docs). No playwright, no sequential-thinking.

**Key distinction from ux-designer**: UI designer gets `magic` for generative component work; UX designer gets `sequential-thinking` + `playwright` for research and journey analysis. The split cleanly separates visual production (magic) from research/evaluation (sequential-thinking + playwright).

**MCP Integration section** (verbatim):
```
- magic: Generate modern UI components, refine design systems, create interactive elements
- context7: Research design patterns, accessibility guidelines, UI framework documentation
```

---

## Frontend Developer

**File**: `agents/development/frontend-developer.md`

**Frontmatter** (verbatim):
```yaml
---
name: frontend-developer
description: Acts as a senior frontend engineer and AI pair programmer. Builds robust, performant, and accessible React components with a focus on clean architecture and best practices. Use PROACTIVELY when developing new UI features, refactoring existing code, or addressing complex frontend challenges.
tools: Read, Write, Edit, MultiEdit, Grep, Glob, Bash, LS, WebSearch, WebFetch, TodoWrite, Task, mcp__magic__21st_magic_component_builder, mcp__magic__21st_magic_component_refiner, mcp__context7__resolve-library-id, mcp__context7__get-library-docs, mcp__playwright__browser_snapshot, mcp__playwright__browser_click, mcp__magic__21st_magic_component_builder
model: sonnet
```

Note: `mcp__magic__21st_magic_component_builder` appears twice in the tools list — a copy-paste artifact.

**MCP tools**: `magic` (component_builder, component_refiner — duplicated), `context7`, `playwright` (browser_snapshot, browser_click — limited interaction, no evaluate/fill).

**Description pattern**: "Acts as" + "pair programmer" framing. Trigger clause lists three distinct situations (new features, refactoring, complex challenges).

---

## Backend Architect

**File**: `agents/development/backend-architect.md`

**Frontmatter** (verbatim):
```yaml
---
name: backend-architect
description: Acts as a consultative architect to design robust, scalable, and maintainable backend systems. Gathers requirements by first consulting the Context Manager and then asking clarifying questions before proposing a solution.
tools: Read, Write, Edit, MultiEdit, Grep, Glob, Bash, LS, WebSearch, WebFetch, TodoWrite, mcp__context7__resolve-library-id, mcp__context7__get-library-docs, Task, mcp__sequential-thinking__sequentialthinking
model: sonnet
---
```

**MCP tools**: `context7`, `sequential-thinking`. No magic, no playwright.

**Description pattern**: "Acts as a consultative architect" — positions the agent as a consultant who asks clarifying questions before proposing solutions. The description mentions "consulting the Context Manager" which is likely a reference to the project CLAUDE.md or another agent.

**MCP Integration section** (verbatim):
```
- context7: Research framework patterns, API best practices, database design patterns
- sequential-thinking: Complex architectural analysis, requirement gathering, trade-off evaluation
```

---

## Mobile Developer

**File**: `agents/development/mobile-developer.md`

**Frontmatter** (verbatim):
```yaml
---
name: mobile-developer
description: Architects and leads the development of sophisticated, cross-platform mobile applications using React Native and Flutter. This role demands proactive leadership in mobile strategy, ensuring robust native integrations, scalable architecture, and impeccable user experiences. Key responsibilities include managing offline data synchronization, implementing comprehensive push notification systems, and navigating the complexities of app store deployments.
tools: Read, Write, Edit, MultiEdit, Grep, Glob, Bash, LS, WebSearch, WebFetch, TodoWrite, Task, mcp__context7__resolve-library-id, mcp__context7__get-library-docs, mcp__sequential-thinking__sequentialthinking
model: sonnet
---
```

**MCP tools**: `context7`, `sequential-thinking`. No magic (mobile is not web component generation), no playwright (no browser).

**Description pattern**: No "Use PROACTIVELY" clause. Instead the description is written entirely as role definition with implicit routing through technology keyword enumeration (React Native, Flutter, offline data synchronization, push notifications, app store deployments).

---

## Full Stack Developer

**File**: `agents/development/full-stack-developer.md`

**Frontmatter** (verbatim):
```yaml
---
name: full-stack-developer
description: A versatile AI Full Stack Developer proficient in designing, building, and maintaining all aspects of web applications, from the user interface to the server-side logic and database management. Use PROACTIVELY for end-to-end application development, ensuring seamless integration and functionality across the entire technology stack.
tools: Read, Write, Edit, MultiEdit, Grep, Glob, Bash, LS, WebSearch, WebFetch, TodoWrite, Task, mcp__context7__resolve-library-id, mcp__context7__get-library-docs, mcp__sequential-thinking__sequentialthinking, mcp__magic__21st_magic_component_builder
model: sonnet
---
```

**MCP tools**: `context7`, `sequential-thinking`, `magic` (component_builder only — not refiner). Gets both frontend (magic) and backend (sequential-thinking) MCP tools.

---

## Tool Gating Patterns

Tool assignment is strictly additive via allowlist. No agent uses `disallowedTools`. The pattern is: start with a common base set, then add MCP tools appropriate to the agent's domain.

### Base tool set (nearly universal across dev agents)
```
Read, Write, Edit, MultiEdit, Grep, Glob, Bash, LS, WebSearch, WebFetch, TodoWrite, Task
```

### MCP tool assignments by role

| Agent | context7 | sequential-thinking | magic | playwright |
|---|---|---|---|---|
| ux-designer | resolve+docs | sequentialthinking | — | navigate+snapshot |
| ui-designer | resolve+docs | — | builder+refiner | — |
| frontend-developer | resolve+docs | — | builder+refiner | snapshot+click |
| react-pro | resolve+docs | — | builder+inspiration+refiner | — |
| backend-architect | resolve+docs | sequentialthinking | — | — |
| full-stack-developer | resolve+docs | sequentialthinking | builder | — |
| mobile-developer | resolve+docs | sequentialthinking | — | — |
| performance-engineer | resolve+docs | sequentialthinking | — | navigate+screenshot+evaluate |
| security-auditor | resolve+docs | sequentialthinking | — | navigate+snapshot+evaluate |
| code-reviewer | resolve+docs | sequentialthinking | — | — |
| debugger | resolve+docs | sequentialthinking | — | — |
| agent-organizer | — | — | — | — |

**Key observations**:

1. `context7` is present on every agent except `agent-organizer`. It is the universal documentation lookup tool.

2. `sequential-thinking` is assigned to agents that need structured multi-step reasoning: architects, engineers, auditors, reviewers. It is absent from pure frontend/UI agents (ux-designer gets it as an exception because user journey analysis is complex sequential reasoning).

3. `magic` (21st-dev component generator) is frontend-only: ui-designer, frontend-developer, react-pro, full-stack-developer. It is absent from backend, mobile, infrastructure, and quality agents.

4. `playwright` is split by intent:
   - **Read-only** (navigate + snapshot): ux-designer — for visual research only
   - **Limited interaction** (snapshot + click): frontend-developer — for E2E testing
   - **Full evaluation** (navigate + screenshot + evaluate): performance-engineer, security-auditor — for measurement and exploitation simulation

5. `agent-organizer` runs on `haiku` with a minimal tool set (Read, Write, Edit, Grep, Glob, Bash, TodoWrite) — no MCP tools at all. It is a planning agent, not an execution agent.

6. `code-reviewer` also runs on `haiku` — despite having sequential-thinking and context7. Review is a reasoning task, not a generation task.

---

## Shared Core Development Philosophy Block

Every development agent contains this identical section verbatim. It is the shared engineering contract:

```markdown
## Core Development Philosophy

### 1. Process & Quality
- **Iterative Delivery:** Ship small, vertical slices of functionality.
- **Understand First:** Analyze existing patterns before coding.
- **Test-Driven:** Write tests before or alongside implementation. All code must be tested.
- **Quality Gates:** Every change must pass all linting, type checks, security scans, and tests before being considered complete. Failing builds must never be merged.

### 2. Technical Standards
- **Simplicity & Readability:** Write clear, simple code. Avoid clever hacks. Each module should have a single responsibility.
- **Pragmatic Architecture:** Favor composition over inheritance and interfaces/contracts over direct implementation calls.
- **Explicit Error Handling:** Implement robust error handling. Fail fast with descriptive errors and log meaningful information.
- **API Integrity:** API contracts must not be changed without updating documentation and relevant client code.

### 3. Decision Making
When multiple solutions exist, prioritize in this order:
1. **Testability:** How easily can the solution be tested in isolation?
2. **Readability:** How easily will another developer understand this?
3. **Consistency:** Does it match existing patterns in the codebase?
4. **Simplicity:** Is it the least complex solution?
5. **Reversibility:** How easily can it be changed or replaced later?
```

This block appears unchanged in: frontend-developer, backend-architect, full-stack-developer, mobile-developer, react-pro, debugger, performance-engineer, and others. The UX and UI designers do not include it — they have alternative "Guiding Principles" sections instead.

---

## Agent Organizer Architecture

The `agent-organizer` is architecturally distinct from all other agents:

- Runs on `haiku` (cost/speed optimized for planning work)
- No MCP tools
- Minimal tool set (Read, Write, Edit, Grep, Glob, Bash, TodoWrite — notably no WebSearch, WebFetch, Task)
- Explicitly prohibited from writing code or modifying files
- Outputs structured delegation reports, not implementations
- Contains a full directory of all 33 agents with descriptions for intelligent selection

The CLAUDE.md (project-level, not global) defines a dispatch protocol: the orchestrator (main Claude instance) routes all non-trivial requests through agent-organizer, which returns a delegation plan, then the orchestrator executes that plan by invoking the recommended agents sequentially or in parallel.

This creates a two-level hierarchy: main process (dispatcher) → agent-organizer (planner) → specialist agents (executors).

---

## Key Architectural Patterns Worth Noting

**Description as routing contract**: The description field is treated as a formal routing specification. Each description combines persona identity, scope declaration, and trigger conditions. The "Use PROACTIVELY" clause appears in most but not all — mobile-developer demonstrates that pure scope/responsibility enumeration can route without an explicit trigger phrase.

**Role-scoped tool lists over monolithic access**: Rather than giving all agents all tools, each agent receives only what its role requires. This prevents agents from misusing capabilities (a UX agent cannot fill forms or evaluate JS in playwright; a code reviewer cannot make web requests or spawn tasks).

**Shared philosophy, differentiated competencies**: The core engineering philosophy is centralized as a copy-pasted block, then agent value comes entirely from the role-specific sections. This trades consistency for maintainability — if the core philosophy changes, 10+ files need updates.

**MCP Integration section as documentation**: Every agent with MCP tools includes an explicit "MCP Integration" section explaining what each MCP server is used for in that agent's context. This documents intent rather than just listing tools.

**Model selection as cost signal**: `haiku` for orchestration/review, `sonnet` for all implementation work. No agent uses `opus`.

---

## Dependencies

MCP servers required for full functionality:
- `@modelcontextprotocol/server-sequential-thinking` — multi-step reasoning
- `@upstash/context7-mcp` — up-to-date library documentation lookup
- `@21st-dev/magic` — UI component generation (requires paid API key)
- `@playwright/mcp` — browser automation

All four are configured as stdio-type MCP servers in `~/.claude.json`. Context7 and sequential-thinking are free; magic requires a 21st.dev API key.

---

## Relevance to Helioy

**For agent definition design**: The description field pattern here is the most systematic example of routing-by-description encountered so far. The "Use PROACTIVELY when/for X, Y, Z" structure combined with persona framing is directly adoptable for Helioy agent definitions.

**For tool gating**: The allowlist-only approach (no disallowedTools) with role-scoped MCP tools is a clean pattern. Helioy agents that use helioy-bus, fmm, mdcontext, or attention-matters MCP tools should similarly scope them per agent role rather than granting universal access.

**For model selection**: The haiku/sonnet split for planner vs. executor roles maps well to nancyr's orchestration model. Planning/routing agents should run cheaper/faster models; execution agents run higher-capability models.

**For shared philosophy blocks**: The copy-paste approach works at this scale (33 agents) but would become a maintenance burden at larger scale. A template or include mechanism would be preferable for Helioy agent definitions if the collection grows beyond ~20 agents.

---

## Sources Consulted

- `README.md` — full agent catalog, installation, and orchestration pattern documentation
- `CLAUDE.md` — project-level development philosophy and agent dispatch protocol
- `agents/development/ux-designer.md` — full content
- `agents/development/ui-designer.md` — full content
- `agents/development/frontend-developer.md` — full content
- `agents/development/backend-architect.md` — full content
- `agents/development/mobile-developer.md` — full content
- `agents/development/full-stack-developer.md` — full content
- `agents/development/react-pro.md` — full content
- `agents/quality-testing/code-reviewer.md` — full content
- `agents/quality-testing/debugger.md` — full content
- `agents/infrastructure/performance-engineer.md` — full content
- `agents/security/security-auditor.md` — full content
- `agents/agent-organizer.md` — full content (includes full agent directory)

---

## Open Questions

1. The `agent-organizer`'s agent directory lists descriptions that differ slightly from the actual frontmatter descriptions in each agent file. Which is authoritative for routing — the frontmatter or the organizer's internal catalog?

2. The CLAUDE.md dispatch protocol mandates routing all non-trivial work through agent-organizer, but the agent-organizer itself has no Task tool. How does it invoke sub-agents in practice — does the main Claude instance do it, or does the organizer use Bash to call the Claude CLI?

3. `code-reviewer.md` has `name: code-reviewer-pro` in the frontmatter but the filename is `code-reviewer.md`. The README lists it as `code-reviewer`. This inconsistency may cause routing failures.

4. No agent uses `disallowedTools`. Would explicitly blocking dangerous tools (Bash for read-only agents like ux-designer) provide meaningful safety improvements, or is the allowlist sufficient?
