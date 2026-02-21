---
title: Sovereign Tech Fellowship Application Draft
type: projects
tags: [sovereign-tech, fellowship, funding, helioy, open-source]
summary: Draft application for the Sovereign Tech Fellowship (deadline April 6, 2026) as maintainer of the Helioy open source MCP infrastructure ecosystem
status: draft
created: 2026-03-26
---

# Sovereign Tech Fellowship Application Draft

## Program Details (Reference)

- **Deadline:** April 6, 2026, 23:59 CET
- **Portal:** https://apply.sovereigntechfund.de
- **Category:** Maintainer (freelance, worldwide)
- **Contract:** 3-12 months, 6-32 hours/week, flexible
- **Start date:** May 1, 2026
- **Compensation:** Negotiated hourly rate (provide fully-loaded rate in application)
- **Interviews:** Starting April 20, decisions by end of April

## Eligibility Checklist

- [x] Maintainer of 3+ FOSS projects (6 public repos on GitHub)
- [x] Merge/release permission on at least one project (sole maintainer on all)
- [x] OSI-approved license (MIT on attention-matters, context-matters, fmm, nancyr; markdown-matters and helioy-bus need LICENSE files added before submission)
- [x] Projects benefit society or critical sectors
- [x] Strong written English
- [ ] **ACTION REQUIRED:** Add LICENSE files to markdown-matters and helioy-bus repos
- [ ] **ACTION REQUIRED:** Add license field to Cargo.toml for markdown-matters and helioy-bus

---

## Application Content

### Statement of Interest (1-2 page PDF)

I maintain six interconnected open source Rust projects that provide memory, context, and orchestration infrastructure for AI agents via the Model Context Protocol (MCP).

MCP was donated to the Linux Foundation's Agentic AI Foundation in December 2025. It has become the connectivity standard for AI agents, with adoption from Anthropic, OpenAI, Google, Microsoft, and others. Monthly SDK downloads exceed 97 million. The protocol defines how AI agents discover and use tools, but the ecosystem of open source tools those agents actually connect to remains underdeveloped. That is the gap my work addresses.

**What I build and maintain:**

The Helioy ecosystem is a suite of MCP servers, each handling a distinct concern that AI agents need:

| Project | Purpose | GitHub |
|---------|---------|--------|
| **context-matters** | Structured context store with hierarchical scoping. Gives agents persistent memory across sessions. | github.com/srobinson/context-matters |
| **attention-matters** | Geometric memory on the S3 hypersphere. Quaternion-based attention with phasor interference for salience-weighted recall. | github.com/srobinson/attention-matters |
| **frontmatter-matters** | Code structural intelligence. Indexes exports, dependencies, and file topology so agents navigate codebases without reading every file. Reduces LLM file reads by 80-90%. | github.com/srobinson/fmm |
| **markdown-matters** | Markdown indexing and semantic search. Structural search with 80% fewer tokens. | github.com/srobinson/markdown-matters |
| **helioy-bus** | Inter-agent message bus. Enables multi-agent coordination through pub/sub messaging and warroom orchestration. | github.com/srobinson/helioy-bus |
| **nancyr** | Process supervisor for AI agent CLIs. Token budgets, lifecycle hooks, and codebase intelligence for multi-agent workflows. | github.com/srobinson/nancyr |

All projects are written in Rust, MIT-licensed, and ship as standalone MCP servers.

**Why this matters for digital sovereignty:**

AI agents are becoming integral to how software is built, maintained, and operated. The infrastructure that manages what these agents remember, what context they operate in, and how they coordinate determines who controls the AI-assisted development stack.

Today, that infrastructure is overwhelmingly proprietary. Agent memory lives in vendor clouds. Context windows are managed by platform providers. Multi-agent orchestration is locked to specific vendors.

Open source MCP servers that handle memory, context, and orchestration locally give developers and organizations sovereignty over their AI tooling. The data stays on their machines. The behavior is auditable. The infrastructure is not subject to vendor pricing changes or terms of service revisions.

This is directly analogous to what projects like Nominatim (geocoding), tcpdump (network analysis), and CycloneDX (SBOM) provide in their respective domains. These were among the projects supported by the 2025 fellowship cohort. The Helioy ecosystem fills the same role for AI agent infrastructure.

**What the fellowship would enable:**

As a solo maintainer, my time splits between development, documentation, issue triage, release engineering, and community support. The fellowship would let me allocate sustained, focused time to:

1. **Reduce technical debt.** Several components need API stabilization and cross-crate consistency improvements before they can support external contributors.
2. **Documentation and onboarding.** Each MCP server needs contributor guides, architecture documentation, and example integrations that lower the barrier for new contributors.
3. **Interoperability testing.** The ecosystem needs CI that validates cross-component integration, particularly as MCP evolves under the Agentic AI Foundation.
4. **Mentoring and community building.** Structured contribution pathways, good-first-issue curation, and mentoring sessions for developers entering the MCP ecosystem.

**About me:**

I am based in New Zealand. I work primarily in Rust and TypeScript. I have been building open source software infrastructure for AI agents since the early days of MCP adoption. Every component I maintain ships as a standalone MCP server, designed to run locally, composable with any MCP client.

I am a solo maintainer across all six projects. The fellowship would be the first external funding for this work.

---

### Project Details (for application form fields)

**Project 1: context-matters**
- **Role:** Sole maintainer
- **Repository:** https://github.com/srobinson/context-matters
- **License:** MIT
- **Criticality reasoning:** AI agents operating across sessions need persistent, structured context. Without open source options, this function defaults to proprietary vendor solutions, creating data lock-in for every organization using AI agents.
- **Target users:** Developers building MCP-based AI agent workflows; organizations deploying AI coding assistants that need auditable, local memory.
- **Current challenges:** API stabilization needed for v1.0; hierarchical scope model needs documentation for contributors; no integration test suite against upstream MCP spec changes.
- **Governance:** Solo maintainer. The fellowship goal is to establish contributor pathways.

**Project 2: frontmatter-matters (fmm)**
- **Role:** Sole maintainer
- **Repository:** https://github.com/srobinson/fmm
- **License:** MIT
- **Criticality reasoning:** LLM agents consume tokens proportional to the files they read. fmm provides precomputed structural metadata that eliminates 80-90% of file reads. For any organization running AI agents against large codebases, this directly reduces cost and latency.
- **Target users:** AI agent developers; teams using Claude Code, Cursor, or similar tools against large codebases; IDE plugin developers.
- **Current challenges:** Multi-language support (currently strongest in TypeScript/Rust) needs expansion; workspace discovery logic needs refactoring for monorepo patterns.
- **Governance:** Solo maintainer.

**Project 3: attention-matters**
- **Role:** Sole maintainer
- **Repository:** https://github.com/srobinson/attention-matters
- **License:** MIT
- **Criticality reasoning:** Geometric memory using quaternion representations on the S3 hypersphere provides salience-weighted recall that degrades gracefully. This approach to agent memory is novel in the open source space and provides an alternative to vector-database-dependent solutions.
- **Target users:** Researchers exploring geometric approaches to memory; AI agent developers needing attention-weighted recall; organizations wanting local, auditable agent memory.
- **Current challenges:** Mathematical documentation needs improvement for contributors unfamiliar with quaternion geometry; benchmark suite incomplete.
- **Governance:** Solo maintainer.

**Project 4: helioy-bus**
- **Role:** Sole maintainer
- **Repository:** https://github.com/srobinson/helioy-bus
- **License:** MIT (needs LICENSE file)
- **Criticality reasoning:** Multi-agent AI systems need coordination infrastructure. Without open source options, organizations depend on vendor-specific orchestration platforms that dictate agent communication patterns.
- **Target users:** Developers building multi-agent systems; teams coordinating multiple AI coding agents on shared codebases.
- **Current challenges:** Protocol documentation; stress testing for concurrent agent scenarios; warroom orchestration patterns need formalization.
- **Governance:** Solo maintainer.

**Project 5: nancyr**
- **Role:** Sole maintainer
- **Repository:** https://github.com/srobinson/nancyr
- **License:** MIT
- **Criticality reasoning:** AI agent process supervision (token budgets, lifecycle management, crash recovery) is essential for production multi-agent deployments. No mature open source option exists.
- **Target users:** Teams running multi-agent AI workflows in production; developers needing resource governance for AI agent processes.
- **Current challenges:** WIP status; needs stabilization of supervisor API and hook system.
- **Governance:** Solo maintainer.

**Project 6: markdown-matters**
- **Role:** Sole maintainer
- **Repository:** https://github.com/srobinson/markdown-matters
- **License:** MIT (needs LICENSE file)
- **Criticality reasoning:** Markdown is the universal interchange format for AI agent context. Structural indexing and search reduces token consumption by 80%, directly impacting the cost and feasibility of AI agent deployments.
- **Target users:** AI agent developers; documentation systems; knowledge management platforms.
- **Current challenges:** Summarization pipeline needs architectural work; search ranking needs tuning.
- **Governance:** Solo maintainer.

---

### Evaluation Criteria Alignment

**Prevalence:** MCP is used by every major AI platform (97M+ monthly SDK downloads). Open source MCP servers are foundational infrastructure for the ecosystem.

**Relevance:** AI agents are being deployed across education (coding tutors), healthcare (clinical documentation), energy (infrastructure monitoring), and industry (software development). The infrastructure layer that manages agent memory, context, and coordination affects all of these sectors.

**Vulnerability:** This work is unfunded. As a solo maintainer, a single burnout event removes the maintainer from six interconnected projects. This is the exact failure mode the fellowship was designed to address.

**Sustainability plan:**
- API stabilization to reduce maintainer-dependent knowledge
- Contributor documentation and onboarding materials
- Good-first-issue program
- Architecture Decision Records for all design choices
- CI/CD that validates cross-component integration

**Active engagement:** Willing to participate in conferences, events, evaluation reporting, and interviews. Available for the Sovereign Tech Agency's communication activities.

---

### Logistics

- **Preferred arrangement:** Freelance contractor (based in New Zealand, worldwide option)
- **Preferred hours:** 20-32 hours/week
- **Preferred duration:** 12 months
- **Hourly rate:** [TO BE DETERMINED - research NZ/EU market rates for senior Rust infrastructure developers]

---

## Pre-Submission Checklist

- [ ] Add MIT LICENSE file to `markdown-matters` repo
- [ ] Add MIT LICENSE file to `helioy-bus` repo
- [ ] Add `license = "MIT"` to Cargo.toml for markdown-matters
- [ ] Add `license = "MIT"` to Cargo.toml for helioy-bus
- [ ] Format statement of interest as PDF (1-2 pages)
- [ ] Verify all GitHub repos are public and have descriptions
- [ ] Add description to context-matters GitHub repo
- [ ] Add description to helioy-bus GitHub repo
- [ ] Determine fully-loaded hourly rate
- [ ] Submit via https://apply.sovereigntechfund.de before April 6, 23:59 CET
