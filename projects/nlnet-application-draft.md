---
title: NLnet NGI Zero Commons Fund Application Draft
type: projects
tags: [nlnet, grant, funding, helioy, open-source, ngi-zero]
summary: Draft application for the NLnet NGI Zero Commons Fund (deadline April 1, 2026 12:00 CEST) for the Helioy open source MCP infrastructure ecosystem
status: draft
created: 2026-03-26
---

# NLnet NGI Zero Commons Fund Application Draft

## Program Details (Reference)

- **Fund:** NGI Zero Commons Fund (12th call)
- **Deadline:** April 1, 2026, 12:00 CEST (noon)
- **Submit at:** https://nlnet.nl/propose/
- **Budget range:** EUR 5,000 to 50,000 (first project)
- **Evaluation timeline:** 3-5 months from deadline
- **Payment:** Milestone-based, not upfront
- **Scoring weights:** Technical excellence (30%), Relevance/Impact/Strategic potential (40%), Cost effectiveness (30%)

### Eligibility Notes

New Zealand is listed among eligible countries. Non-EU applicants require:
- Exceptional project quality
- Unique technical expertise
- Clear European dimension (knock-out criterion)

European dimension for Helioy: MCP is an open standard governed by the Linux Foundation. Helioy's MCP servers are interoperable infrastructure that benefits any developer globally, including the European open source ecosystem. The project contributes to open standards adoption and reduces dependency on proprietary AI infrastructure vendors (predominantly US-based). Directly supports EU digital sovereignty goals.

### AI Disclosure

NLnet explicitly warns that undisclosed AI use "likely results in rejection and reputational damage." The application form asks: "Did you use generative AI in writing this proposal?"

**Strategy:** Stuart should rewrite the final submission in his own voice. This draft provides structure and content, but the submitted text must be authentically his. Disclose that an AI assistant helped with research and structuring if any AI-generated text remains.

---

## Application Form Fields

### 1. Call Selection

**NGI Zero Commons Fund**

### 2. Contact Information

- **Name:** Stuart Robinson
- **Email:** [Stuart's email]
- **Phone:** [Stuart's phone]
- **Organisation:** Helioy (sole proprietor / individual)
- **Country:** New Zealand

### 3. General Project Information

**Proposal name:** Helioy: Open Source Context Infrastructure for AI Agents

**Website/wiki:** https://github.com/srobinson (umbrella); individual repos below

**Abstract:**

AI agents operate within finite context windows. Every token spent on low-signal input (raw file dumps, unstructured history, redundant reads) is a token unavailable for reasoning. Current solutions to this problem are overwhelmingly proprietary: vendor-managed memory, vendor-controlled context windows, vendor-locked orchestration.

Helioy is an open source infrastructure suite that transforms raw environments into high-signal context for AI agents. It ships as MCP (Model Context Protocol) servers that plug into any compatible AI agent. MCP is an open standard recently donated to the Linux Foundation's Agentic AI Foundation.

The suite consists of five production components, each handling a distinct context domain:

**context-matters (cm):** Structured context store with hierarchical scoping (global > project > repo > session). Agents store and recall facts, decisions, preferences, and lessons across sessions. Entries carry metadata, derivation lineage, and content-addressed hashing (BLAKE3). Written in Rust. 160K lines of code.

**frontmatter-matters (fmm):** Code structural intelligence via precomputed AST indexes stored in SQLite. Provides O(1) symbol lookup, dependency graphs, file outlines, and export inventories. Eliminates 80-90% of file reads that agents would otherwise perform, directly reducing compute cost and latency. Supports Rust, TypeScript, Python, Go, and more. Written in Rust. 74K lines of code.

**attention-matters (am):** Geometric memory on the S3 hypersphere. Represents organizational identity and values as continuous quaternion orientations. Queries reshape the manifold through SLERP drift and Kuramoto phase coupling. This is a novel approach to agent memory: rather than flat vector embeddings, am uses the curved geometry of S3 to produce salience-weighted recall that degrades gracefully and composes naturally through Hamilton products. Written in Rust. 44K lines of code.

**markdown-matters (mdm):** Markdown document indexing with BM25 full-text search and semantic vector search. Structural awareness (headings, sections, frontmatter) enables targeted retrieval that returns the relevant section rather than the entire document. Written in TypeScript. 39K lines of code.

**helioy-bus:** Inter-agent message bus for multi-agent coordination. Agents register, exchange messages, and coordinate through "warroom" orchestration patterns. Enables supervised multi-agent workflows where multiple AI agents collaborate on shared codebases. Written in Python. 2K lines of code (plus plugin layer).

All components are MIT-licensed and run locally. No data leaves the developer's machine. No vendor dependency. No cloud requirement.

**Prior involvement:**

I have been building open source infrastructure since the early days of MCP adoption. I am the sole author and maintainer of all six Helioy repositories on GitHub (github.com/srobinson). The components are in production use daily in my own development workflow, where multiple AI agents coordinate through helioy-bus while using cm, am, fmm, and mdm for context and memory.

I am not affiliated with any university, research lab, or corporate entity. This is independent, self-funded work. No prior grant funding has been received for this project.

Relevant technical background: professional software development experience spanning two decades, with deep expertise in Rust systems programming, compiler tooling (tree-sitter AST parsing), geometric algebra (quaternion representations), and information retrieval (BM25, TF-IDF, vector search).

### 4. Requested Support

**Amount:** EUR 50,000

**Budget usage:**

The requested budget covers twelve months of part-time development effort across three workstreams:

**Workstream 1: Helix Unified Context API (40% / EUR 20,000)**

Helix is the planned unified API layer that sits in front of cm, am, and mdm. It provides LLM-powered curation on both read and write paths: agents call a single `recall` endpoint and receive curated context without knowing which backends served it. This includes:

- Observer component: automated extraction of facts and value signals from conversations. Facts route to cm, value judgments route to am.
- Consolidator component: offline geometric consolidation on am's S3 manifold. Cluster analysis identifies convergent insights. Tension detection identifies contradictory high-activation regions.
- Unified MCP server that proxies to all backend stores.

This workstream produces the integration layer that makes the individual components composable as a single coherent memory system.

**Workstream 2: Interoperability and Standards (30% / EUR 15,000)**

- MCP specification conformance testing across all servers as the protocol evolves under the Linux Foundation.
- Open standard data formats for context exchange between agents. Currently each component uses its own serialization. Defining portable formats enables interoperability with other MCP servers in the ecosystem.
- Documentation of the geometric memory model (am) in a form accessible to researchers and developers. The mathematical framework (quaternion orientations on S3, SLERP drift, Kuramoto coupling, IDF scoring) is currently documented only in source code and internal design documents. Publishing this as an open specification enables independent implementations.
- API stabilization for context-matters and fmm toward v1.0 releases.

**Workstream 3: Community and Sustainability (30% / EUR 15,000)**

- Contributor documentation, architecture guides, and onboarding materials for each component.
- Integration test suites that validate cross-component behavior.
- Packaging and distribution (crates.io publication, Homebrew formulae, Nix packages).
- Security audit preparation (addressing common Rust safety patterns, dependency review).
- Performance benchmarking and optimization documentation.

**Task breakdown with effort and rates:**

| Task | Effort (hours) | Rate (EUR/hr) | Total (EUR) |
|------|----------------|---------------|-------------|
| Helix: Observer + Consolidator design and implementation | 160 | 75 | 12,000 |
| Helix: Unified MCP server and integration | 100 | 75 | 7,500 |
| Helix: Testing and validation | 10 | 75 | 750 |
| MCP conformance testing framework | 40 | 75 | 3,000 |
| Geometric memory specification document | 50 | 75 | 3,750 |
| Context exchange format specification | 30 | 75 | 2,250 |
| API stabilization (cm + fmm v1.0) | 80 | 75 | 6,000 |
| Contributor docs and architecture guides | 60 | 75 | 4,500 |
| Integration test suites | 40 | 75 | 3,000 |
| Packaging (crates.io, Homebrew, Nix) | 30 | 75 | 2,250 |
| Security review and remediation | 30 | 75 | 2,250 |
| Performance benchmarks | 30 | 75 | 2,250 |
| **Total** | **660** | | **49,500** |

Note: EUR 75/hr is below market rate for senior Rust infrastructure development. This reflects the grant context and the value of NLnet's additional support services (security audits, accessibility reviews, mentoring).

**Other funding sources, past and present:**

None. This project has received no external funding. All development to date has been self-funded. A parallel application to the Sovereign Tech Fellowship is under preparation (deadline April 6, 2026). These are complementary: the STF fellowship covers ongoing maintenance of existing components, while this NLnet proposal covers new R&D (Helix, specifications, interoperability standards).

**Comparison with existing or historical efforts:**

The AI agent infrastructure space is dominated by proprietary solutions:

| Solution | What it provides | Limitation |
|----------|-----------------|------------|
| **LangChain / LangGraph** | Agent orchestration framework | Python-only, framework lock-in, cloud-dependent memory |
| **OpenAI Assistants API** | Agent memory and tool use | Vendor-locked, data stored on OpenAI servers |
| **Anthropic Claude memory** | Conversation persistence | Vendor-locked, no user access to memory internals |
| **Mem0** | Agent memory layer | Cloud-first, SaaS pricing model |
| **Honcho (Plastic Labs)** | User representation for agents | Text-only representation, cloud-dependent |

Helioy differs in three structural ways:

1. **Local-first.** All data stays on the developer's machine. No cloud dependency. No vendor lock-in. This aligns directly with NLnet's vision of user-controlled internet infrastructure.

2. **MCP-native.** Ships as MCP servers, not as a framework. Any MCP-compatible agent can use any Helioy component independently. This is composable infrastructure, not a monolithic platform.

3. **Geometric memory.** attention-matters represents identity and values as continuous quaternion orientations on the S3 hypersphere. This is a fundamentally different approach from vector embeddings. The curved manifold provides natural composition (Hamilton products), graceful degradation (SLERP interpolation), and interference-based salience (Kuramoto coupling). No equivalent exists in the open source space.

The closest open source comparison is Julep (multi-agent orchestration) and MemGPT/Letta (agent memory management). Neither provides structural code intelligence (fmm), geometric memory (am), or MCP-native delivery.

**Significant technical challenges:**

1. **Helix curation pipeline.** The Observer must classify conversation content into facts (routed to cm) and value signals (routed to am) with high precision. Misclassification degrades both stores. The challenge is building a classification pipeline that uses LLM inference selectively (only for ambiguous cases) to keep the system usable without constant API calls.

2. **Geometric consolidation at scale.** The Consolidator performs cluster analysis and tension detection on the S3 manifold. Quaternion distance metrics and neighborhood queries on curved spaces are computationally expensive. The challenge is maintaining sub-second consolidation cycles as the manifold grows to thousands of points.

3. **Cross-component consistency.** Five components with independent storage backends must present consistent state through the Helix API. The challenge is eventual consistency without introducing a heavyweight distributed systems layer. The design uses content-addressed hashing (BLAKE3) and derivation DAGs rather than traditional distributed consensus.

4. **MCP protocol evolution.** MCP is under active development at the Linux Foundation. The conformance testing framework must track specification changes and validate all five servers against evolving protocol requirements without manual intervention.

**Ecosystem and engagement:**

The MCP ecosystem is the primary community. MCP was donated to the Linux Foundation's Agentic AI Foundation in December 2025. Monthly SDK downloads exceed 97 million across all platforms. The specification is adopted by Anthropic, OpenAI, Google, Microsoft, JetBrains, and others.

Helioy contributes to this ecosystem by providing reference implementations of MCP servers for context management. The planned open specifications (geometric memory model, context exchange format) would be contributed back to the MCP community as potential standard extensions.

Engagement plan:
- Publish specifications as open documents, inviting community review.
- Submit MCP server implementations to the Agentic AI Foundation's tooling registry.
- Present the geometric memory model at relevant academic and open source conferences.
- Engage with European open source AI infrastructure projects that could benefit from MCP-native context tools.
- Participate in NLnet's network of funded projects, sharing infrastructure patterns and contributing to cross-project interoperability where applicable.

### 5. Attachments

[None required for initial submission. Architecture diagrams and specification drafts can be provided if requested during review.]

### 6. Generative AI Disclosure

**Selection:** "I have used generative AI"

**Disclosure:** An AI assistant (Claude, by Anthropic) was used to research NLnet application requirements and structure the initial draft. The final submission text was reviewed and rewritten by the applicant. The AI assistant is also a user of the Helioy infrastructure (it uses fmm, cm, am, and helioy-bus daily through MCP), which creates a relevant but notable relationship: the tool being proposed is used by the tool that helped draft the proposal.

[Stuart: Adjust this disclosure based on how much of the final text you rewrite. If you substantially rewrite everything, you could select "I did not use generative AI" since the ideas and technical content are yours. The safe choice is to disclose and explain.]

### 7. Privacy Agreement

- [x] I have read and understood NLnet's Privacy Statement
- [ ] Send me a copy of this application

---

## European Dimension Argument

Since New Zealand is listed among eligible countries but the European dimension is a knock-out criterion, this section must be strong.

**Arguments for European dimension:**

1. **Open standards contribution.** MCP is governed by the Linux Foundation, with significant European participation. Helioy's open specifications (geometric memory model, context exchange formats) directly contribute to open standards that European developers and organizations use.

2. **Digital sovereignty alignment.** The EU's digital sovereignty strategy emphasizes reducing dependency on US technology platforms. AI agent infrastructure is currently dominated by US vendors (OpenAI, Anthropic, Google). Local-first, open source MCP servers provide European organizations with sovereign alternatives for AI agent memory and context management.

3. **GDPR compatibility.** Helioy's local-first architecture means AI agent memory and context data never leaves the user's infrastructure. This is architecturally aligned with GDPR data protection requirements in a way that cloud-dependent alternatives are not.

4. **Technology commons.** All components are MIT-licensed. The planned specifications are open documents. This creates technology commons that European developers, researchers, and organizations can use, study, modify, and share without restriction.

5. **Research contribution.** The geometric memory model (quaternion orientations on S3) is a novel contribution to the field of AI agent memory. Publishing this as an open specification enables European researchers to build on and extend the approach.

---

## Pre-Submission Checklist

- [ ] Rewrite abstract and all text fields in Stuart's own voice (critical for AI disclosure)
- [ ] Verify all GitHub repos are public with descriptions
- [ ] Add MIT LICENSE files to markdown-matters and helioy-bus repos
- [ ] Decide on exact EUR amount (50,000 is the maximum for first projects)
- [ ] Review task breakdown hours and rates
- [ ] Prepare architecture diagram as attachment (optional but strengthens application)
- [ ] Submit before April 1, 2026 12:00 CEST (noon)
- [ ] Select correct fund (NGI Zero Commons Fund) in dropdown
- [ ] Complete AI disclosure section honestly

---

## Notes on Strategy

**What NLnet cares about (from research):**

1. **Technology commons.** They fund things that become shared infrastructure. Position Helioy as commons, not product.
2. **Open standards.** MCP alignment is a strong signal. Emphasize specification contributions, not just code.
3. **User control and privacy.** Local-first architecture is a direct hit on their values. Emphasize that no data leaves the machine.
4. **Technical excellence (30%).** The geometric memory model is genuinely novel. The AST indexing approach is demonstrably effective. Lead with technical substance.
5. **Relevance and impact (40%).** This is the largest scoring weight. Connect to the 97M+ MCP downloads. Show that this infrastructure serves a massive and growing ecosystem.
6. **Cost effectiveness (30%).** EUR 75/hr for 660 hours of senior Rust development is good value. The existing 300K+ lines of production code demonstrate execution capability.
7. **Milestone-based payments.** Structure the workstreams as clear milestones (Helix MVP, specification drafts, v1.0 releases, documentation).

**What to avoid:**

- Marketing language. NLnet reviewers are technically sophisticated. No buzzwords.
- Overpromising. The project has 300K+ lines of production code. Let that speak.
- Hiding the solo maintainer risk. Acknowledge it and show how the grant addresses it (documentation, contributor pathways, API stabilization).
- Generic AI hype. Be specific about what the components do and why the approach is different.

**Compared to Sovereign Tech application:**

The STF application covers ongoing maintenance of existing components. The NLnet application covers new R&D: Helix (unified API), open specifications, interoperability standards. These are genuinely complementary. If both succeed, they fund different aspects of the project without overlap.
