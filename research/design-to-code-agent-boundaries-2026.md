---
title: Design-to-Code Agent Boundaries 2025-2026
type: research
tags: [design-systems, agents, frontend, ux, mobile, backend, multi-agent, v0, lovable, bolt, figma]
summary: AI design-to-code tools encode three implicit agent layers (UX/intent, visual/brand, implementation); the field is converging on separated frontend+backend agents with a design-awareness layer between Figma and code, while mobile warrants its own specialist agent.
status: active
source: deep-research
confidence: high
created: 2026-03-09
updated: 2026-03-09
---

## Executive Summary

The 2025-2026 landscape shows a clear pattern: monolithic design-to-code tools like v0, Bolt, and Lovable collapse UX, visual design, and implementation into a single pipeline, but the failure modes they surface -- design-blind output, token drift, platform mismatches -- are pushing the field toward explicit agent role separation. Three functional layers are emerging as the natural decomposition: a UX/intent layer (what to build and why), a visual/brand layer (how it looks and feels), and an implementation layer (how the code executes). Mobile is distinct enough to warrant its own agent due to platform-specific build tooling, gesture models, and performance constraints. Backend agents are best understood as contract custodians who own the schema and API surface, with API contract ownership being the primary coordination mechanism between frontend and backend.

---

## Detailed Findings

### 1. v0, Bolt, Lovable, and Figma Make: Implicit Roles in Monolithic Pipelines

Each major tool encodes a different opinion about which design-to-code layers it owns.

**v0 (Vercel)**

v0 positions itself as a UI component specialist. Its Figma integration extracts visual context (colors, spacing, tokens) and structural layout, passing both into React generation with Tailwind CSS and shadcn/ui as the component layer. The implicit agent model is:

- Figma (or the user) acts as the design authority -- v0 does not reason about UX decisions
- v0 translates visual specifications into component code
- Assembly into larger layouts is a second, explicit step

The recommended workflow is incremental composition: generate individual components first, then combine. v0 explicitly learns "style preferences like fonts and spacing" over sessions, meaning it accumulates a visual design memory but not a UX reasoning layer. Backend logic is out of scope for v0's core value proposition, though Vercel is adding it incrementally.

**Bolt (StackBlitz)**

Bolt functions as a full-stack architect operating a WebContainer browser environment. It blurs the UX/visual/implementation boundary through tight integration: real-time debugging feedback loops treat design and implementation as concurrent rather than sequential. The pipeline is: prompt → full-stack generation → integrated debugging → export. UX and visual design are not separated -- the user's prompt is the only UX input.

**Lovable**

Lovable front-loads architectural decisions and integrates Supabase for backend. Its most significant role decomposition experiment was AI personas -- a Product Manager bot, Designer bot, and Developer bot to simulate cross-functional conversation. However, these are prompt-framing aids rather than autonomous agents with separate context windows or toolchains. The role separation is conversational scaffolding, not architectural.

**Figma Make**

Figma Make is the clearest attempt to maintain the UX layer. Because it operates inside Figma, it can consume component libraries, design tokens, and interaction states that already encode UX decisions made by human designers. Key characteristics:

- Native consumption of Figma design system components means the visual layer is pre-established
- Generates functional prototypes using Anthropic's Claude 3.7
- The delta between Figma prototype and production is smaller than v0 because brand fidelity is built in, not retrofitted
- Critical limitation: no persistent design memory -- it overrides prior decisions when new prompts arrive

**Anima**

Anima is the clearest articulation of a standalone design-awareness layer. Its founding premise is that "coding agents ship fast but are design-blind, resulting in inconsistent UI and broken patterns." Anima positions itself as the layer between Figma/visual intent and a downstream coding agent (it launched with Bolt as its first integration partner). The API exposes pixel-perfect component generation that coding agents consume, rather than replacing the coding agent's implementation work. This is the most explicit instantiation of the UX/visual agent vs. implementation agent separation found in production tools.

**Builder.io Fusion 1.0**

Fusion takes the opposite approach: it eliminates handoffs by learning each team's patterns across Slack, Jira, Figma, and GitHub, and produces PRs that update based on design feedback. The coordination mechanism is the tool's internal context engine rather than explicit agent role separation. This is "collapsed roles plus shared memory" rather than specialized agents.

---

### 2. Design System Agents: The Maintainer, the UX Designer, and the Visual Designer

Three distinct agent roles are emerging around design systems, each with a different access surface and decision scope.

**Design System Maintainer Agent**

This agent is a governance and consistency enforcer. From production implementations described in the literature:

- Watches Figma via API and triggers documentation updates when components change
- Runs token audit scripts (e.g., `token-audit.js`) that scan CSS for hardcoded visual values and return exit code 1 if violations are found, blocking merges
- Detects when upstream design system packages update and flags affected spec files
- Handles batch operations: token naming, usage analysis, component auditing via Playwright

The maintainer agent operates on code and design artifacts simultaneously. Its primary job is enforcing the boundary between the token layer and hardcoded values. The problem it addresses is well-documented: "LLMs drift, fabricate tokens, and fabricate token names, drift on values within a session, lose all context between sessions."

The three-layer architecture recommended for LLM-compatible design systems is: (1) upstream tokens from the design system, (2) project aliases with fallbacks, and (3) component implementations that only reference aliases, never raw values. The maintainer agent enforces this by catching layer violations before merge.

**UX Designer Agent**

Emerging research (arxiv 2509.20731) describes five roles AI agents can play in the design ideation and inspiration phase: Work Coordinator, Resource Steward, Guardian (context/version history), Reframer (alternative viewpoints), and Creative Catalyst. These are assistance roles within a human-designer workflow, not autonomous agents that generate UX decisions. The boundary is explicit in the research: creative decision-making, final conceptual direction, and cultural context remain exclusively human. The agents handle mundane work: renaming assets, organizing files, retrieving patterns, batch resizing.

The practical UX designer agent as it exists today is a Figma plugin or conversational tool that generates wireframes and flow diagrams from text prompts (e.g., UX Pilot, Figma's AI wireframe generator). These are prompt-to-wireframe tools, not agents that hold UX reasoning across a session.

**Visual Designer Agent**

This is the most commercially mature role. v0, Anima, and Figma Make all implement versions of a visual designer agent: one that takes structural input (wireframe, component spec, Figma frame) and produces polished, on-brand visual output. The critical input is design tokens and the component library. Without access to these, the output is generic.

The distinction from the UX designer agent: visual design agents know what the brand looks like and can render it consistently; UX designer agents know what users need and can reason about flow and interaction patterns. These are different knowledge bases. A visual designer agent without a design system produces "AI slop"; a UX designer agent without implementation knowledge produces wireframes that violate platform constraints.

---

### 3. UX vs. Visual Design vs. Frontend: Where the Boundary Falls

**The collapsing approach (v0, Bolt, Lovable)**

Tools like v0 and Bolt collapse all three layers into a single prompt → code pipeline. This works well for greenfield prototypes where there is no existing design system or UX research. It fails in contexts where:
- An existing brand must be maintained (requires design tokens as constraints)
- UX research has established interaction patterns that must be preserved
- Accessibility requirements constrain visual choices

The Anthropic 2026 Agentic Coding Trends Report notes that engineers report being able to "fully delegate" only 0-20% of tasks; the remainder requires active supervision and validation. For design-to-code work, the hardest 80% involves design decisions that require context the agent doesn't have.

**The separated approach (Anima + coding agent, v0 + Figma)**

A clearer separation is: human designers (or a design agent with Figma access) establish the visual and UX layer, then a coding agent consumes that as a spec. The mechanism is either Figma MCP (exposing component props, token values, interaction states as structured data) or Anima's API (translating Figma into structured component code for downstream agents).

Key insight from the hvpandya.com analysis: "Source code shows what was built. Specs describe how to build the next thing." The design spec (token structure, component usage rules, interaction patterns) is the contract that prevents context-window drift and session-to-session inconsistency. This points to a role for a spec-keeper agent whose job is maintaining this structured design contract file, distinct from the frontend coding agent that consumes it.

**What works**

The HN discussion on frontend workflows before AI tools found that practitioners who get consistent results from AI coding tools follow a "design system first" discipline: establish the visual system, document it as structured specs, then use AI to generate components that reference the specs. The workflow that fails is ad-hoc prompting without a pre-established design constraint layer.

The Anthropic report highlights that engineers are becoming "more full-stack in capabilities" because AI fills in knowledge gaps -- but this applies to implementation domains (frontend, backend, database), not design reasoning. Design taste and UX judgment remain the human's domain.

---

### 4. Mobile-Specific Considerations

Mobile development requires a dedicated agent specialization for four concrete reasons:

**Performance model is fundamentally different.** Web agents optimize for page load speed and bundle size. Mobile agents must optimize for FPS (frames per second), TTI (time to interactive), and memory footprint across devices with heterogeneous RAM. Callstack's React Native best practices for AI agents explicitly documents this: the optimization target is "FPS and TTI across diverse device capabilities," not network performance.

**Native platform divergence.** iOS and Android require distinct profiling approaches, native module integration patterns, and build-time configurations. Android-specific: R8 code shrinking requires "keep rules for affected packages/classes," particularly with reflection-heavy libraries. iOS-specific: native module integration and profiling workflows differ significantly. A web frontend agent has no knowledge of these; applying web agent outputs to mobile produces build failures and runtime issues.

**Layout system differences.** React Native's Flexbox implementation differs from CSS Flexbox in subtle but consequential ways. Styling approaches (StyleSheet API, not CSS) differ. A web frontend agent applying CSS conventions to React Native produces layout bugs that require mobile-specific debugging knowledge to diagnose.

**App store constraints.** Mobile agents must understand submission requirements, review guidelines, and deployment infrastructure (Expo EAS, Xcode archives, Play Console) that have no web equivalent.

The Vercel agent-skills repository received a formal proposal (Issue #64) to add a React Native skill because "agents currently lack structured guidance for React Native-specific patterns, performance considerations, and mobile UX constraints." Callstack published a reference document explicitly structured for AI agent consumption. This is a community-validated acknowledgment that mobile is a distinct knowledge domain requiring its own agent specialization.

The practical implication: a mobile agent is not a "frontend agent that also knows React Native." It is a platform-specific agent with a different toolset (Xcode, Android Studio, Expo, device simulators, native profilers), a different performance model, and different output artifacts (IPA, APK, OTA update bundles).

---

### 5. Backend Agent Scope and Frontend Boundary

**What belongs to the backend agent**

Based on the FullStack-Agent research (arxiv 2602.03798) and multi-agent architecture literature, the backend agent's natural scope is:

- Database schema design and migration management
- API endpoint definition and implementation (REST, GraphQL)
- Authentication and authorization logic
- Server-side business logic and validation
- Infrastructure configuration (within the project scope)

The FullStack-Agent paper demonstrated that backend specialization produces 38.2% higher accuracy over generalist approaches on backend tasks. The improvement stems from specialized debugging tools (Postman-style API testing built into the agent's toolset) and domain-specific knowledge of ORM patterns, database migration tooling, and RESTful conventions.

**The API contract as boundary mechanism**

The primary mechanism for preventing frontend-backend agent overlap is the API contract established by a planning agent before either implementation agent begins work. The FullStack-Agent architecture makes this explicit: a planning agent creates a JSON spec defining "page layouts, components, data flow, backend entities, and API endpoints with granular type definitions, down to the most granular types (e.g., integer)."

The frontend agent receives a "summary of the APIs the backend agent constructed" before beginning implementation. This sequential handoff prevents the failure mode where the frontend agent generates UI with mock data because no backend contract exists.

In human team practice (documented by Evil Martians), the coordination mechanism is the same: contracts stored separately from backend code (shared monorepo, dedicated contracts repo, or versioned spec directory), with frontend engineers participating in API design rather than passively consuming it. "Contract changes become task zero" for new features.

**The AG-UI protocol**

The emerging AG-UI protocol (CopilotKit) formalizes the frontend-backend agent boundary at the protocol level. Rather than a request-response API contract, AG-UI uses Server-Sent Events to stream structured JSON events from backend agents to frontend agents. "The contract between agents and UIs" -- an explicit formalization of the boundary between the agent reasoning layer (backend) and the rendering layer (frontend).

**Preventing overlap**

The failure mode is when the frontend agent makes backend assumptions (hardcoding data shapes, assuming auth behavior) or the backend agent makes frontend assumptions (designing API responses for backend convenience rather than UI needs). Two mechanisms prevent this:

1. Planning agent produces the explicit typed contract before either implementation agent starts
2. Frontend engineers (or frontend agents) participate in API shape decisions, since "they understand user needs and UI constraints better than anyone"

The second mechanism implies a coordination protocol where the frontend agent must be consulted before the backend agent finalizes endpoint definitions -- a design review gate, not just a technical contract.

---

## Sources Consulted

### Engineering Blogs and Tool Documentation
- [Working with Figma and custom design systems in v0 - Vercel](https://vercel.com/blog/working-with-figma-and-custom-design-systems-in-v0)
- [Anima Skill: AI agents can now design, explore, and publish apps with Anima](https://www.animaapp.com/blog/agentic/ai-agents-can-now-design-explore-and-publish-apps-with-anima/)
- [Anima API: Bringing Figma to coding AI agents](https://www.animaapp.com/blog/api/anima-api-bringing-figma-to-coding-ai-agents/)
- [Builder.io Launches Fusion 1.0 - First AI Agent for Product, Design, and Code](https://www.prnewswire.com/news-releases/builderio-launches-fusion-1-0--the-first-ai-agent-for-product-design-and-code-302615215.html)
- [React Native Best Practices for AI Agents - Callstack](https://www.callstack.com/blog/announcing-react-native-best-practices-for-ai-agents)
- [Expose Your Design System to LLMs - Hardik Pandya](https://hvpandya.com/llm-design-systems)
- [Improve AI code output with AGENTS.md - Builder.io](https://www.builder.io/blog/agents-md)
- [The Architecture Behind Lovable and Bolt - Beam](https://www.beam.cloud/blog/agentic-apps)

### Research Papers
- [FullStack-Agent: Enhancing Agentic Full-Stack Web Coding (arxiv 2602.03798)](https://arxiv.org/html/2602.03798v1)
- [Imagining Design Workflows in Agentic AI Futures (arxiv 2509.20731)](https://arxiv.org/html/2509.20731v1)

### Industry Reports
- [2026 Agentic Coding Trends Report - Anthropic](https://resources.anthropic.com/hubfs/2026%20Agentic%20Coding%20Trends%20Report.pdf)

### Tool Comparisons
- [AI-Driven Prototyping: v0, Bolt, and Lovable Compared - Addyo Substack](https://addyo.substack.com/p/ai-driven-prototyping-v0-bolt-and)
- [Figma Make: New AI Code Generation Tool Review - Banani](https://www.banani.co/blog/figma-make-ai-tool)
- [Day 8: Figma Make vs Vercel v0 - Medium](https://medium.com/design-bootcamp/figma-make-vs-vercel-v0-watching-two-ai-developers-code-my-design-28df4daaa671)

### Community Discussions
- [Ask HN: AI agents and the future of UI/UX design](https://news.ycombinator.com/item?id=44322036)
- [Ask HN: How do you structure front end workflows before using AI tools?](https://news.ycombinator.com/item?id=44192783)
- [Proposal: Add React Native agent skill for mobile - Vercel Labs GitHub](https://github.com/vercel-labs/agent-skills/issues/64)

### Multi-Agent Architecture
- [Design Patterns for a Multi-Agent Future - DEV Community](https://dev.to/rohit_gavali_0c2ad84fe4e0/design-patterns-for-a-multi-agent-future-3jpe)
- [AI Vibe Coding in Multi-Agent Architectures - GoCodeo](https://www.gocodeo.com/post/ai-vibe-coding-in-multi-agent-architectures-how-it-scales-across-teams)
- [API Contracts: A Frontend Survival Guide - Evil Martians](https://evilmartians.com/chronicles/api-contracts-and-everything-i-wish-i-knew-a-frontend-survival-guide)
- [Back-end for Agents Pattern - Medium](https://medium.com/@mdbaraujo/the-back-end-for-agents-pattern-bfa-32e69baf8da3)

### Design Systems
- [How design systems teams are using AI tools](https://learn.thedesignsystem.guide/p/how-design-systems-teams-are-using)
- [Mapping your design system for AI agents - Design Systems Collective](https://www.designsystemscollective.com/codebase-indexing-for-design-systems-agents-c0f6b563a39e)
- [Design Systems in 2026: Predictions, Pitfalls, and Power Moves](https://rydarashid.medium.com/design-systems-in-2026-predictions-pitfalls-and-power-moves-f401317f7563)

---

## Source Quality Assessment

**High confidence findings:**
- FullStack-Agent paper provides empirical benchmarks showing specialization benefits (38.2% backend improvement). This is peer-reviewed quantitative evidence, not anecdote.
- Callstack and Vercel GitHub issue on React Native agent skills are primary sources from practitioners with direct implementation experience.
- hvpandya.com design system article describes a production-tested pattern with specific tooling (token-audit.js, CI integration).
- Anthropic's own Agentic Coding Trends Report is based on their direct customer data.

**Medium confidence findings:**
- Role decomposition patterns from v0/Bolt/Lovable are inferred from tool behavior and comparison articles, not internal architecture documentation (those are not public).
- Lovable's AI persona feature is noted in multiple sources but the implementation depth is unclear.
- The five design agent roles from the arxiv design fiction paper are research proposals, not validated production patterns.

**Gaps:**
- No direct access to Bolt, v0, or Lovable internal architecture documentation. All analysis is external observation.
- Limited Reddit signal on these topics -- site:reddit.com searches returned zero results for technical discussions on agent role boundaries.
- The "look and feel agent" vs "UX agent" separation is not yet a formalized distinction in any production tool -- it remains an analytical frame.

---

## Open Questions

1. Does Figma Make's lack of persistent design memory (it overrides prior decisions on new prompts) represent a fundamental LLM limitation, or is it a product choice that will be fixed?

2. As coding agents become more "full-stack" in capability (Anthropic's trend 1), does the argument for specialized frontend/backend agents weaken? Or does specialization persist because the debugging toolsets differ?

3. How do teams handle the UX research → wireframe → visual design handoff when different agents own different stages? What is the shared artifact format?

4. Is there a viable "visual design agent" that holds brand and component system memory across sessions without collapsing into either a UX agent (too abstract) or a frontend agent (too concrete)?

5. For React Native specifically: as Expo's managed workflow abstracts more platform-specific concerns, does the mobile/web agent distinction narrow?

6. The AG-UI protocol formalizes the backend agent → frontend agent event stream. Does a similar protocol exist or need to exist for the design agent → frontend agent handoff?

---

## Actionable Takeaways

**For building a multi-agent design-to-code system:**

1. Three functional layers are the right decomposition: UX/intent (why and what), visual/brand (look and feel with design system tokens), implementation (code). Do not collapse them without accepting the tradeoffs.

2. Design the API contract as the first artifact, before either frontend or backend implementation agents start. The planning agent that produces this contract is a distinct role from both implementation agents.

3. A design system spec file (structured markdown or JSON documenting token names, component usage rules, interaction patterns) is the mechanism for preventing visual drift across sessions. The spec is the memory layer that survives context window resets. A design system maintainer agent enforces this via CI token audit scripts.

4. Mobile is a distinct platform requiring a separate agent skill context with: Flexbox behavioral differences from web, FPS/TTI performance model, native profiling toolchains, and app store submission knowledge. Do not share a frontend web agent with mobile.

5. Design system token enforcement requires CI integration (exit code 1 on hardcoded values in CSS), not just style guides. Without machine enforcement, agents drift back to hardcoded values within one session.

6. For cross-agent coordination: the frontend agent should have input into API shape before the backend agent finalizes endpoints. The planning agent's contract must capture this negotiation, not just the backend agent's preferences.

**Suggested follow-ups:**
- Investigate Figma MCP server capabilities in depth -- it may be the most practical current mechanism for a design-awareness layer that persists UX and brand decisions across agent sessions
- Evaluate Anima API as the "design-aware layer" for a multi-agent architecture where Bolt or Claude Code handles implementation
- Examine how teams are using AGENTS.md to encode design system constraints for coding agents -- Builder.io's approach may generalize
