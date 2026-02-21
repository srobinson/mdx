---
title: "Context Manager Protocol and Agent Collaboration Lists (VoltAgent/awesome-claude-code-subagents)"
type: research
tags: [claude-code, subagents, multi-agent, orchestration, frontend, mobile, design-system]
summary: 127+ curated Claude Code subagent definitions organized into 10 numbered categories, each agent using a YAML frontmatter + markdown system prompt pattern with standardized JSON inter-agent communication routed through a context-manager.
status: active
source: github-researcher
confidence: high
created: 2026-03-09
updated: 2026-03-09
---

## Executive Summary

`VoltAgent/awesome-claude-code-subagents` is a community-curated library of 127+ Claude Code subagent `.md` files. Each agent is a markdown file with YAML frontmatter (`name`, `description`, `tools`, `model`) followed by a free-form system prompt. The defining architectural choice is a **context-manager hub protocol**: every agent begins by sending a typed JSON query to a `context-manager` subagent, then posts JSON status updates during execution, and notifies the context-manager on completion. There is no Expo-specific agent; Expo appears only as a line-item capability inside `mobile-app-developer`.

---

## Architecture

### Repository Layout

```
categories/
  01-core-development/       # backend, frontend, fullstack, mobile, ui-designer, etc.
  02-language-specialists/   # react-specialist, nextjs-developer, swift-expert, etc.
  03-infrastructure/         # devops, kubernetes, terraform, cloud-architect, etc.
  04-quality-security/       # qa-expert, security-auditor, accessibility-tester, etc.
  05-data-ai/                # ml-engineer, llm-architect, postgres-pro, etc.
  06-developer-experience/   # mcp-developer, refactoring-specialist, cli-developer, etc.
  07-specialized-domains/    # mobile-app-developer, fintech-engineer, game-developer, etc.
  08-business-product/       # product-manager, ux-researcher, technical-writer, etc.
  09-meta-orchestration/     # context-manager, agent-organizer, workflow-orchestrator, etc.
  10-research-analysis/      # research-analyst, trend-analyst, competitive-analyst, etc.
tools/subagent-catalog/      # Claude Code skill for browsing/fetching agents
```

Each category directory contains a `plugin.json` (for `claude plugin install`) and a `README.md` with selection guide tables. Plugin names follow the pattern `voltagent-<slug>` (e.g., `voltagent-core-dev`, `voltagent-lang`, `voltagent-meta`).

### Agent File Format

```yaml
---
name: agent-name
description: "Trigger description used by Claude Code for auto-selection"
tools: Read, Write, Edit, Bash, Glob, Grep
model: sonnet   # opus | sonnet | haiku | inherit
---

You are a senior [role]...

[Domain checklists, bullet-point capability lists]

## Communication Protocol
[Mandatory JSON query to context-manager at startup]

## Development Workflow
### 1. [Analysis phase]
### 2. [Implementation phase — includes JSON status update block]
### 3. [Delivery phase — includes completion message string]

[Additional sections: integration with other agents, tool-specific guidance]
```

### Model Routing Convention

| Model | Use case | Example agents |
|-------|----------|----------------|
| `opus` | Deep reasoning — architecture, security audits, financial logic | `security-auditor`, `architect-reviewer`, `fintech-engineer` |
| `sonnet` | Everyday coding — most agents | `frontend-developer`, `backend-developer`, `mobile-developer` |
| `haiku` | Quick tasks — docs, search, dependency checks | `documentation-engineer`, `seo-specialist`, `build-engineer` |

### Tool Assignment Patterns

- **Read-only** (reviewers, auditors): `Read, Grep, Glob`
- **Research** (analysts): `Read, Grep, Glob, WebFetch, WebSearch`
- **Code writers** (developers): `Read, Write, Edit, Bash, Glob, Grep`
- **Documentation**: `Read, Write, Edit, Glob, Grep, WebFetch, WebSearch`

---

## Key Pattern: Context-Manager JSON Protocol

Every agent opens with a mandatory JSON query to the `context-manager`. The JSON shape is consistent across all agents:

```json
{
  "requesting_agent": "<agent-name>",
  "request_type": "get_<domain>_context",
  "payload": {
    "query": "<free-text description of what context is needed>"
  }
}
```

Mid-execution status updates follow this shape:

```json
{
  "agent": "<agent-name>",
  "update_type": "progress",   // or "status": "developing"
  "current_task": "<task label>",
  "completed_items": ["item1", "item2"],
  "next_steps": ["step1", "step2"]
}
```

The context-manager itself sends a self-assessment query on startup:

```json
{
  "requesting_agent": "context-manager",
  "request_type": "get_context_requirements",
  "payload": {
    "query": "Context requirements needed: data types, access patterns, consistency needs, performance targets, and compliance requirements."
  }
}
```

And reports its own progress:

```json
{
  "agent": "context-manager",
  "status": "managing",
  "progress": {
    "contexts_stored": "2.3M",
    "avg_retrieval_time": "47ms",
    "cache_hit_rate": "89%",
    "consistency_score": "100%"
  }
}
```

**Important clarification**: This JSON "protocol" is defined entirely within agent system prompts. There is no runtime message bus, no actual JSON RPC, and no inter-process communication infrastructure in this repository. The JSON blocks are instructional patterns that tell the agent what to output as text, simulating structured communication. The actual routing between subagents is handled by Claude Code's native subagent invocation mechanism.

---

## Detailed Findings

### 1. frontend-developer (categories/01-core-development/frontend-developer.md)

**Frontmatter:**
```yaml
name: frontend-developer
description: "Use when building complete frontend applications across React, Vue, and Angular frameworks requiring multi-framework expertise and full-stack integration."
tools: Read, Write, Edit, Bash, Glob, Grep
model: sonnet
```

**Identity:** Senior frontend developer, React 18+, Vue 3+, Angular 15+.

**Initial context-manager query (verbatim):**
```json
{
  "requesting_agent": "frontend-developer",
  "request_type": "get_project_context",
  "payload": {
    "query": "Frontend development context needed: current UI architecture, component ecosystem, design language, established patterns, and frontend infrastructure."
  }
}
```

**Execution flow:**
1. Context Discovery — query context-manager for component architecture, design tokens, state management patterns, testing strategy, build pipeline
2. Development Execution — scaffold components with TypeScript interfaces, implement layouts/interactions, integrate state management, write tests, ensure accessibility
3. Handoff and Documentation — notify context-manager of all created/modified files, document component API, highlight architectural decisions

**Status update format (verbatim):**
```json
{
  "agent": "frontend-developer",
  "update_type": "progress",
  "current_task": "Component implementation",
  "completed_items": ["Layout structure", "Base styling", "Event handlers"],
  "next_steps": ["State integration", "Test coverage"]
}
```

**Completion message format:**
> "UI components delivered successfully. Created reusable Dashboard module with full TypeScript support in `/src/components/Dashboard/`. Includes responsive design, WCAG compliance, and 90% test coverage. Ready for integration with backend APIs."

**TypeScript requirements:** strict mode, no implicit any, strict null checks, no unchecked indexed access, exact optional property types, ES2022 target, path aliases, declaration files.

**Collaboration partners (Integration with other agents):**
- Receive designs from `ui-designer`
- Get API contracts from `backend-developer`
- Provide test IDs to `qa-expert`
- Share metrics with `performance-engineer`
- Coordinate with `websocket-engineer` for real-time features
- Work with `deployment-engineer` on build configs
- Collaborate with `security-auditor` on CSP policies
- Sync with `database-optimizer` on data fetching

**Deliverables:** component files with TypeScript definitions, test files (>85% coverage), Storybook documentation, performance metrics report, accessibility audit results, bundle analysis output, build configuration files, documentation updates.

---

### 2. ui-designer (categories/01-core-development/ui-designer.md)

**Frontmatter:**
```yaml
name: ui-designer
description: "Use this agent when designing visual interfaces, creating design systems, building component libraries, or refining user-facing aesthetics requiring expert visual design, interaction patterns, and accessibility considerations."
tools: Read, Write, Edit, Bash, Glob, Grep
model: sonnet
```

**Identity:** Senior UI designer, visual design + interaction design + design systems.

**Initial context-manager query (verbatim):**
```json
{
  "requesting_agent": "ui-designer",
  "request_type": "get_design_context",
  "payload": {
    "query": "Design context needed: brand guidelines, existing design system, component libraries, visual patterns, accessibility requirements, and target user demographics."
  }
}
```

**Execution flow:**
1. Context Discovery — brand guidelines, existing design system, patterns, accessibility requirements, performance constraints
2. Design Execution — visual concepts and variations, component systems, interaction patterns, design decisions, developer handoff preparation
3. Handoff and Documentation — notify context-manager of all design deliverables, document component specifications, provide implementation guidelines, accessibility annotations, design tokens and assets

**Status update format (verbatim):**
```json
{
  "agent": "ui-designer",
  "update_type": "progress",
  "current_task": "Component design",
  "completed_items": ["Visual exploration", "Component structure", "State variations"],
  "next_steps": ["Motion design", "Documentation"]
}
```

**Completion message format:**
> "UI design completed successfully. Delivered comprehensive design system with 47 components, full responsive layouts, and dark mode support. Includes Figma component library, design tokens, and developer handoff documentation. Accessibility validated at WCAG 2.1 AA level."

**Collaboration partners:**
- Collaborate with `ux-researcher` on user insights
- Provide specs to `frontend-developer`
- Work with `accessibility-tester` on compliance
- Support `product-manager` on feature design
- Guide `backend-developer` on data visualization
- Partner with `content-marketer` on visual content
- Assist `qa-expert` with visual testing
- Coordinate with `performance-engineer` on optimization

**Capability areas:** motion design, dark mode design, cross-platform consistency (Web/iOS/Android/Desktop), design documentation, quality assurance.

**Deliverables:** design files with component libraries, style guide documentation, design token exports, asset packages, prototype links, specification documents, handoff annotations, implementation notes.

---

### 3. ux-researcher (categories/08-business-product/ux-researcher.md)

**Frontmatter:**
```yaml
name: ux-researcher
description: "Use this agent when you need to conduct user research, analyze user behavior, or generate actionable insights to validate design decisions and uncover user needs. Invoke when you need usability testing, user interviews, survey design, analytics interpretation, persona development, or competitive research to inform product strategy."
tools: Read, Grep, Glob, WebFetch, WebSearch
model: sonnet
```

Note: `ux-researcher` is a **read-only + web research** agent — no `Write`, `Edit`, or `Bash` tools.

**Initial context-manager query (verbatim):**
```json
{
  "requesting_agent": "ux-researcher",
  "request_type": "get_research_context",
  "payload": {
    "query": "Research context needed: product stage, user segments, business goals, existing insights, design challenges, and success metrics."
  }
}
```

**Progress tracking format (verbatim):**
```json
{
  "agent": "ux-researcher",
  "status": "analyzing",
  "progress": {
    "studies_completed": 12,
    "participants": 247,
    "insights_generated": 89,
    "design_impact": "high"
  }
}
```

**Collaboration partners:**
- Collaborate with `product-manager` on priorities
- Work with `ux-designer` on solutions (note: references `ux-designer`, not `ui-designer` — this appears to be a naming inconsistency; no `ux-designer` agent exists in this repo)
- Support `frontend-developer` on implementation
- Guide `content-marketer` on messaging
- Help `customer-success-manager` on feedback
- Assist `business-analyst` on metrics
- Partner with `data-analyst` on analytics
- Coordinate with `scrum-master` on sprints

**Capability areas:** user interview planning, usability testing, survey design, analytics interpretation, persona development, journey mapping, A/B test analysis, accessibility research, competitive analysis, research synthesis.

---

### 4. backend-developer (categories/01-core-development/backend-developer.md)

**Frontmatter:**
```yaml
name: backend-developer
description: "Use this agent when building server-side APIs, microservices, and backend systems that require robust architecture, scalability planning, and production-ready implementation."
tools: Read, Write, Edit, Bash, Glob, Grep
model: sonnet
```

**Identity:** Senior backend developer, Node.js 18+, Python 3.11+, Go 1.21+.

**Initial context-manager query (verbatim):**
```json
{
  "requesting_agent": "backend-developer",
  "request_type": "get_backend_context",
  "payload": {
    "query": "Require backend system overview: service architecture, data stores, API gateway config, auth providers, message brokers, and deployment patterns."
  }
}
```

**Status update format (verbatim):**
```json
{
  "agent": "backend-developer",
  "status": "developing",
  "phase": "Service implementation",
  "completed": ["Data models", "Business logic", "Auth layer"],
  "pending": ["Cache integration", "Queue setup", "Performance tuning"]
}
```

**Completion message format:**
> "Backend implementation complete. Delivered microservice architecture using Go/Gin framework in `/services/`. Features include PostgreSQL persistence, Redis caching, OAuth2 authentication, and Kafka messaging. Achieved 88% test coverage with sub-100ms p95 latency."

**Performance target:** response time under 100ms p95.

**Collaboration partners:**
- Receive API specifications from `api-designer`
- Provide endpoints to `frontend-developer`
- Share schemas with `database-optimizer`
- Coordinate with `microservices-architect`
- Work with `devops-engineer` on deployment
- Support `mobile-developer` with API needs
- Collaborate with `security-auditor` on vulnerabilities
- Sync with `performance-engineer` on optimization

---

### 5. mobile-developer (categories/01-core-development/mobile-developer.md)

**Frontmatter:**
```yaml
name: mobile-developer
description: "Use this agent when building cross-platform mobile applications requiring native performance optimization, platform-specific features, and offline-first architecture. Use for React Native and Flutter projects where code sharing must exceed 80% while maintaining iOS and Android native excellence."
tools: Read, Write, Edit, Bash, Glob, Grep
model: sonnet
```

**Identity:** Senior mobile developer, React Native 0.82+, cross-platform specialist. (Flutter mentioned in description but body focuses on React Native.)

**Initial context-manager query (verbatim):**
```json
{
  "requesting_agent": "mobile-developer",
  "request_type": "get_mobile_context",
  "payload": {
    "query": "Mobile app context required: target platforms (iOS 18+, Android 15+), minimum OS versions, existing native modules, performance benchmarks, and deployment configuration."
  }
}
```

**Progress tracking format (verbatim):**
```json
{
  "agent": "mobile-developer",
  "status": "developing",
  "platform_progress": {
    "shared": ["Core logic", "API client", "State management", "Type definitions"],
    "ios": ["Native navigation", "Face ID integration", "HealthKit sync"],
    "android": ["Material 3 components", "Biometric auth", "WorkManager tasks"],
    "testing": ["Unit tests", "Integration tests", "E2E tests"]
  }
}
```

**Performance targets:**
- Cold start under 1.5 seconds
- Memory usage below 120MB baseline
- Battery under 4% per hour
- 120 FPS for ProMotion displays
- Touch interactions <16ms
- App size under 40MB initial download
- Crash rate below 0.1%

**Target versions:** iOS 18+, Android 15+, Xcode 16+, Android Studio Hedgehog+.

**Modern architecture:** React Native New Architecture (Fabric, TurboModules), Hermes engine, RAM bundles.

**Collaboration partners:**
- Coordinate with `backend-developer` for API optimization and GraphQL/REST design
- Work with `ui-designer` for platform-specific designs following HIG/Material Design 3
- Collaborate with `qa-expert` on device testing matrix and automation
- Partner with `devops-engineer` on build automation and CI/CD pipelines
- Consult `security-auditor` on mobile vulnerabilities and OWASP compliance
- Sync with `performance-engineer` on optimization and profiling
- Engage `api-designer` for mobile-specific endpoints and real-time features
- Align with `fullstack-developer` on data sync strategies and offline support

---

### 6. mobile-app-developer (categories/07-specialized-domains/mobile-app-developer.md)

A second, more generic mobile agent in the Specialized Domains category (as distinct from `mobile-developer` in Core Development).

**Frontmatter:**
```yaml
name: mobile-app-developer
description: "Use this agent when developing iOS and Android mobile applications with focus on native or native or cross-platform implementation, performance optimization, and platform-specific user experience."
tools: Read, Write, Edit, Bash, Glob, Grep
model: sonnet
```

**Cross-platform frameworks listed (verbatim):** React Native optimization, Flutter performance, **Expo capabilities**, NativeScript features, Xamarin.Forms, Ionic framework, platform channels, native modules.

This is the **only place "Expo" appears** in the entire repository. There is no dedicated Expo-specific agent.

**Initial context-manager query (verbatim):**
```json
{
  "requesting_agent": "mobile-app-developer",
  "request_type": "get_mobile_context",
  "payload": {
    "query": "Mobile app context needed: target platforms, user demographics, feature requirements, performance goals, offline needs, and monetization strategy."
  }
}
```

**Performance targets:** App size < 50MB, startup time < 2 seconds, crash rate < 0.1%.

---

### 7. context-manager (categories/09-meta-orchestration/context-manager.md)

**Frontmatter:**
```yaml
name: context-manager
description: "Use for managing shared state, information retrieval, and data synchronization when multiple agents need coordinated access to context and metadata."
tools: Read, Write, Edit, Glob, Grep
model: sonnet
```

Note: `context-manager` has **no `Bash` tool** — it is not an executor.

**Identity:** Senior context manager, shared knowledge and state across distributed agent systems. Focus: information architecture, retrieval optimization, synchronization protocols, data governance.

**Self-initialization query (verbatim):**
```json
{
  "requesting_agent": "context-manager",
  "request_type": "get_context_requirements",
  "payload": {
    "query": "Context requirements needed: data types, access patterns, consistency needs, performance targets, and compliance requirements."
  }
}
```

**Progress tracking format (verbatim):**
```json
{
  "agent": "context-manager",
  "status": "managing",
  "progress": {
    "contexts_stored": "2.3M",
    "avg_retrieval_time": "47ms",
    "cache_hit_rate": "89%",
    "consistency_score": "100%"
  }
}
```

**Performance targets it tracks:** retrieval time < 100ms, data consistency 100%, availability > 99.9%.

**Context types managed:** project metadata, agent interactions, task history, decision logs, performance metrics, resource usage, error patterns, knowledge base.

**Storage patterns:** hierarchical organization, tag-based retrieval, time-series data, graph relationships, vector embeddings, full-text search, metadata indexing, compression strategies.

**Collaboration partners (Integration with other agents):**
- Support `agent-organizer` with context access
- Collaborate with `multi-agent-coordinator` on state
- Work with `workflow-orchestrator` on process context
- Guide `task-distributor` on workload data
- Help `performance-monitor` on metrics storage
- Assist `error-coordinator` on error context
- Partner with `knowledge-synthesizer` on insights
- Coordinate with all agents on information needs

**Delivery notification (verbatim):**
> "Context management system completed. Managing 2.3M contexts with 47ms average retrieval time. Cache hit rate 89% with 100% consistency score. Reduced storage costs by 43% through intelligent tiering and compression."

**What context-manager actually does (implementation reality):** The agent uses its Read/Write/Edit/Glob/Grep tools to read and write files on disk. It is, effectively, a file-system-backed shared state store. The "context" is presumably stored in files that other agents can read. There is no database or in-memory store — the tools available are purely file I/O.

---

## Taxonomy — Full Category Structure

| # | Category | Plugin name | Agent count (approx) | Focus |
|---|----------|-------------|----------------------|-------|
| 01 | Core Development | `voltagent-core-dev` | 10 | Backend, frontend, fullstack, mobile, UI, WebSocket |
| 02 | Language Specialists | `voltagent-lang` | 25+ | Per-language/framework experts |
| 03 | Infrastructure | `voltagent-infra` | 16 | DevOps, cloud, Kubernetes, Terraform |
| 04 | Quality & Security | `voltagent-qa-sec` | 14 | QA, security auditing, testing, compliance |
| 05 | Data & AI | `voltagent-data-ai` | 12 | ML, data engineering, LLM, PostgreSQL |
| 06 | Developer Experience | `voltagent-dev-exp` | 13 | Tooling, docs, DX, refactoring, MCP |
| 07 | Specialized Domains | `voltagent-domains` | 12 | Blockchain, IoT, fintech, game dev, mobile-app |
| 08 | Business & Product | `voltagent-biz` | 11 | PM, UX research, technical writing, business analysis |
| 09 | Meta & Orchestration | `voltagent-meta` | 9 | context-manager, agent-organizer, workflow-orchestrator |
| 10 | Research & Analysis | `voltagent-research` | 7 | Research analyst, trend analyst, competitive analysis |

---

## Key Patterns Worth Adopting

**1. Typed JSON context request at startup.** Every agent declares what context it needs using a consistent `{requesting_agent, request_type, payload.query}` shape. This makes agent dependencies explicit and readable.

**2. Three-phase execution model.** Analysis → Implementation → Delivery. Each phase is documented in the system prompt with named checkpoints. The delivery phase always includes a templated completion string with concrete metrics.

**3. Agent-specific `request_type` values.** Each agent uses a semantically distinct `request_type` (`get_frontend_context`, `get_backend_context`, `get_mobile_context`, `get_design_context`, etc.), allowing the context-manager to route or filter by domain.

**4. Integration lists as explicit collaboration contracts.** Every agent ends with an "Integration with other agents" bullet list that names specific partner agents and the direction of data flow. This is the closest thing to an inter-agent interface contract in the repository.

**5. Minimal tool permissions.** Agents request only the tools they need. Read-only agents (`ux-researcher`, `code-reviewer`) never get `Bash` or `Write`. This enforces role boundaries.

**6. Model field in frontmatter.** `model: opus|sonnet|haiku|inherit` routes each agent to the appropriate tier automatically. `inherit` passes through the parent conversation's model.

---

## Dependencies

- Claude Code (Anthropic) — subagent runtime, `/agents` UI, plugin system
- No external runtime dependencies in agent files themselves
- The `subagent-catalog` tool uses `curl`, `bash`, and a local file cache

---

## Relevance to Helioy

The context-manager pattern is directly relevant to Helioy's attention-matters and helioy-bus components. Key observations:

- The VoltAgent context-manager is file-system backed (Read/Write/Edit only). Helioy's attention-matters provides a more sophisticated geometric memory engine that could serve the same role with semantic retrieval rather than text search.
- The JSON inter-agent communication protocol (the `{requesting_agent, request_type, payload}` shape) is a clean convention that helioy-bus could adopt as a message envelope format.
- The "integration with other agents" section in each agent definition is essentially a static dependency declaration. Helioy's nancyr orchestrator could use these lists to automatically construct agent collaboration graphs.
- The `model` frontmatter field maps cleanly onto Helioy's agent definition system. Worth adopting for Helioy sub-agents.

---

## Sources Consulted

- `README.md` — full taxonomy, plugin names, subagent structure documentation
- `CLAUDE.md` — repo-level instructions, tool assignment philosophy
- `categories/01-core-development/frontend-developer.md` — verbatim
- `categories/01-core-development/ui-designer.md` — verbatim
- `categories/01-core-development/backend-developer.md` — verbatim
- `categories/01-core-development/mobile-developer.md` — verbatim
- `categories/07-specialized-domains/mobile-app-developer.md` — verbatim (Expo reference)
- `categories/08-business-product/ux-researcher.md` — verbatim
- `categories/09-meta-orchestration/context-manager.md` — verbatim
- `categories/09-meta-orchestration/README.md` — orchestration patterns
- `categories/01-core-development/README.md` — core dev selection guide
- `categories/01-core-development/.claude-plugin/plugin.json` — plugin format
- `categories/02-language-specialists/react-specialist.md` — partial read

---

## Open Questions

1. **Context-manager implementation gap.** The system prompt instructs the agent to "manage" contexts, but with only file I/O tools, the actual persistence mechanism is entirely implicit. How do agents know *where* to write/read context? No shared path convention is defined in any agent file.

2. **No actual message bus.** The JSON "communication protocol" exists only as instructional text. Agents cannot actually send messages to each other at runtime — they can only invoke each other as subagents. The context-manager works only if agents are explicitly invoked in sequence by the parent.

3. **No Expo-specific agent.** If Helioy needs Expo expertise, the best fit is `mobile-app-developer` from category 07 (which lists "Expo capabilities" as a line item) or a custom agent derived from `mobile-developer` with Expo-specific constraints added.

4. **`ux-researcher` references a non-existent `ux-designer` agent** in its collaboration list. The actual design agent is `ui-designer`. This may reflect a naming inconsistency introduced during renaming.

5. **`react-specialist` vs `frontend-developer`.** The repository maintains two React-capable agents with different scopes: `frontend-developer` (multi-framework, full implementation) vs `react-specialist` (React-only, optimization/advanced patterns). The division criterion is "building new" vs "optimizing existing."
