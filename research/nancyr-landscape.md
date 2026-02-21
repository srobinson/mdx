# AI Coding Agent Orchestration Landscape -- February 2026

**Date:** 2026-02-14
**Purpose:** Strategic research for the Nancy Rust rewrite. Understand where the market is, where it's heading, and where Nancy fits.
**Status:** Current as of mid-February 2026

---

## Executive Summary

The AI coding agent market has undergone a fundamental shift in the past 12 months. The transition from "AI pair programmer" (single-agent, interactive) to "AI workforce manager" (multi-agent, asynchronous) is now the defining trend. Addy Osmani (O'Reilly, Feb 13 2026) frames this as the move from **Conductor** (guiding one agent interactively) to **Orchestrator** (managing a fleet of agents in parallel).

Key data points:

- 57% of companies now run AI agents in production (Jan 2026)
- Google's 2025 DORA Report: 90% AI adoption increase correlates with 9% climb in bug rates, 91% increase in code review time, 154% increase in PR size
- ~90% of Claude Code is written by Claude Code itself (Anthropic internal)
- 72% of developers say vibe coding is NOT part of their professional work (Stack Overflow 2025)
- 67.3% of AI-generated PRs get rejected vs 15.6% for manual code (LinearB)
- METR study: experienced developers were 19% slower with AI tools while believing they were 20% faster

The consensus is crystallizing: **parallelism is the productivity multiplier, but quality requires human oversight**. The tools winning are those that enable parallel agent execution with rigorous verification loops. This is exactly Nancy's thesis.

---

## 1. Tool-by-Tool Analysis

### 1.1 Claude Code (Anthropic)

**What it is:** Terminal-based AI coding agent, now the de facto standard for serious AI-assisted development. Started as a CLI tool, now available in 9+ access modes (CLI, VS Code extension, web, mobile, GitHub Actions, SDK).

**Architecture (as of Feb 2026):**

- **Sub-agents / Task tool:** Claude Code can spawn isolated sub-agents via the `Task` tool. Each sub-agent gets its own context window, works independently, and reports results back. This is Claude Code's built-in orchestration primitive.
- **Agent Teams (Feb 2026):** The newest feature. A lead agent coordinates multiple teammate agents that can message each other directly, claim tasks from a shared list, and work in parallel. Each teammate has its own context window. This is a significant upgrade from sub-agents which reported back in isolation.
- **Hooks (14 event types):** Event-driven lifecycle hooks that fire deterministically at specific points (PreToolUse, PostToolUse, SessionStart, Stop, etc.). Not LLM-dependent -- they execute regardless. Enables auto-formatting, security guardrails, audit logging, permission gating.
- **Skills:** Reusable markdown-based instruction sets that Claude Code can invoke. Community ecosystem growing (37+ skills in popular public repos).
- **Background agents:** Cloud-based execution. Point at a GitHub repo, give it a task, and it works asynchronously in a sandboxed container. Pushes branches and opens PRs when done.
- **Compaction:** When nearing context limits, Claude Code summarizes conversations while preserving architectural decisions and unresolved bugs.
- **Claude Code SDK / Agent SDK:** The same agent loop, tools, and context management powering Claude Code, exposed as a programmable SDK. Available in TypeScript and Python. Enables building custom agents with the same capabilities. Supports headless mode for programmatic control.

**Key insight for Nancy:** Claude Code is building orchestration INTO the agent. Agent Teams and the Task tool mean Claude Code itself is becoming an orchestrator. Nancy needs to work WITH these primitives, not replicate them. The SDK is particularly relevant -- Nancy could use it as a worker backend.

**What Claude Code lacks:** It orchestrates at the agent level but has no concept of issue trackers, project management, iterative self-correction across sessions, or human-gated review workflows. It's a powerful executor but not a project coordinator.

### 1.2 Devin (Cognition)

**What it is:** The first "autonomous software engineer" -- a fully autonomous coding agent that operates in its own cloud environment.

**Architecture:**

- Devin 2.0 launched April 2025 at $20/month (down from $500). Core accessibility move.
- Operates in a full cloud VM with its own shell, browser, and code editor.
- Takes a task description, formulates a plan, and executes autonomously.
- Uses "Interactive Planning" where it presents its plan for human approval before executing.
- Can run parallel agents (multiple Devins on different tasks).
- Integrates with GitHub for PR creation and Slack for task assignment.
- 83% more productive than v1 per internal benchmarks.
- SWE-bench: 13.86% end-to-end resolution rate.

**Key insight for Nancy:** Devin proves the market for autonomous task execution from issue descriptions. Nubank achieved 12x efficiency improvement using Devin for ETL migration. But Devin is a closed platform -- you hand it a task and hope for the best. There's no transparency into its orchestration. Nancy's value is being the orchestration layer that can dispatch to Devin OR Claude Code OR any other agent, with human oversight at every stage.

**What Devin lacks:** Open architecture, self-hosting, tool-agnosticism. It's a walled garden. Thoughtworks' Birgitta Boeckeler: "I haven't seen them [autonomous agents like Devin] actually work a single time yet."

### 1.3 OpenHands (formerly OpenDevin)

**What it is:** Open-source autonomous coding agent platform. The open-source answer to Devin.

**Architecture:**

- Sandboxed Docker execution environment for safety.
- Web UI + VSCode integration.
- Multi-agent delegation support.
- Enterprise features: RBAC, audit logging.
- 72% SWE-bench Verified (as of early 2026).
- $18.8M Series A funding.
- Supports multiple LLM backends (not locked to one provider).

**Key patterns:**

- Event-driven architecture with an event stream connecting agent, runtime, and UI.
- Agent-Controller-Runtime separation: Agent decides actions, Controller manages execution loop, Runtime executes in sandbox.
- Hierarchical delegation: agents can spawn sub-agents for specialized tasks.
- Built-in browsing, code execution, and file management capabilities.

**Key insight for Nancy:** OpenHands validates the "open-source orchestration" thesis. Its event-driven architecture and multi-agent delegation are architecturally similar to what Nancy needs. The key difference: OpenHands IS the agent. Nancy orchestrates agents. OpenHands could be one of Nancy's workers.

### 1.4 Cursor Agent Mode

**What it is:** IDE-integrated AI coding agent. Cursor 2.0 (Oct 2025) introduced "Composer," its first agentic coding model, marking the shift from assistant to agent.

**Architecture:**

- **Planner/Worker/Judge hierarchy** (documented in their browser-building experiment). Planners explore codebase and create tasks, Workers execute without coordinating with each other, Judge agents evaluate progress at cycle end.
- **Parallel agents:** Run up to 8 agents simultaneously using git worktree isolation.
- **Background agents:** Cloud-based async execution. Clone repo, spin up ephemeral environment, work end-to-end, open PR with summary.
- **Real-time dashboard** accessible from desktop or mobile for monitoring.
- **MCP integration** for tool extensibility.
- **Context engine:** Indexes entire codebase for semantic search.

**Browser experiment findings (Jan 2026):**

- Cursor agents built a browser (FastRender) in a week: 1M+ lines of code, 1,000 files.
- Equal-status agents with locking failed (agents held locks too long, 20 agents slowed to 2-3 throughput).
- Optimistic concurrency control failed (agents became risk-averse).
- Hierarchical Planner/Worker/Judge was the architecture that worked.
- But: code didn't compile at announcement, pages loaded in "a literal minute," CEO's own assessment: "It _kind of_ works!"

**Key insight for Nancy:** Cursor's experiment is the strongest evidence that multi-agent orchestration WORKS for scale but FAILS for quality without human oversight. The Planner/Worker/Judge pattern is sound. The missing piece -- which Nancy provides -- is the human in the review loop and the iterative correction cycle.

### 1.5 Aider

**What it is:** Open-source terminal-based AI pair programming tool. 40,000+ GitHub stars. Consistently tops coding benchmarks.

**Architecture:**

- Works directly inside git repositories. Every change is a git commit.
- **Repository Map:** Uses tree-sitter to parse code into AST, extracts function signatures and class definitions, builds dependency graph using PageRank to rank symbol importance. Dynamically fits content within token budgets. This pattern is now widely adopted across the industry.
- Supports virtually every major LLM provider.
- "Architect mode" uses powerful model for planning, fast model for execution.
- Self-improving: 80% of Aider's own code is written by Aider.
- Conversational interface in terminal with multi-file editing.

**Key insight for Nancy:** Aider pioneered two patterns Nancy should learn from: (1) the repository map for intelligent context selection, and (2) git-native operation where every change is committed. Aider is a single-agent tool though -- no multi-agent orchestration. Nancy could use Aider as a worker alongside Claude Code.

### 1.6 SWE-agent (Princeton/Stanford)

**What it is:** Research-oriented autonomous agent for fixing GitHub issues. NeurIPS 2024 paper. 18,400+ GitHub stars.

**Architecture:**

- **Agent-Computer Interface (ACI):** Custom interface designed specifically for LLM agents to interact with computers. The core insight: just as IDEs help human developers, LLM agents benefit from specially-built interfaces.
- Takes a GitHub issue URL and attempts to fix it autonomously.
- Configurable via single YAML file.
- Docker-based execution isolation.
- Mini-SWE-Agent: 100 lines of Python achieving 65% on SWE-bench Verified.
- EnIGMA mode for cybersecurity vulnerability detection.
- State of the art on SWE-bench among open-source projects (>74% on SWE-bench Mini).

**Key insight for Nancy:** SWE-agent's "issue in, fix out" paradigm is almost exactly Nancy's workflow. The ACI concept -- that agents need purpose-built interfaces, not human interfaces -- is a design principle Nancy should internalize. Nancy's worker prompt and sidecar navigation system are essentially a custom ACI.

### 1.7 Goose (Block)

**What it is:** Open-source AI developer agent from Block (Square, Cash App). 30,000+ GitHub stars. Free.

**Architecture:**

- **MCP-native:** Built around Model Context Protocol from the ground up. Connects to 3,000+ tools via MCP servers.
- Runs locally on developer's machine.
- BYO model -- works with any LLM provider.
- **Recipes:** Reusable workflow automation scripts.
- Rewritten from Python CLI to Rust + Electron in late 2025 (used Goose itself to help with the migration).
- OSS Roadmap (Feb-Apr 2026) includes enhanced multi-agent capabilities.

**Key insight for Nancy:** Goose's MCP-native architecture validates the direction of building on open protocols rather than proprietary integrations. Its Rust rewrite is directly relevant -- they went through the same Python-to-Rust journey Nancy is undertaking. Their experience: "goose helped us make that transition" using the old version to build the new version.

### 1.8 Claude Code SDK / Agent SDK

**What it is:** Anthropic's framework for building custom agents with the same capabilities as Claude Code.

**Architecture:**

- Available in TypeScript (`@anthropic-ai/claude-code`) and Python.
- Same agent loop, tool framework, and context management as Claude Code.
- Supports headless mode for programmatic automation.
- Can be embedded in CI/CD pipelines, custom tools, and orchestration systems.
- Fits in ~10 lines of code for basic usage.
- Supports MCP servers for tool extensibility.

**Key insight for Nancy:** This is potentially the most important tool for Nancy's Rust rewrite. Instead of shelling out to `claude` CLI and parsing stdout, Nancy could use the Agent SDK as a library to programmatically control Claude Code workers. The SDK gives structured input/output, proper error handling, and event streams. The question: does Nancy want to depend on Anthropic's SDK, or stay CLI-agnostic?

---

## 2. Architecture Patterns Emerging

### 2.1 Human-in-the-Loop vs Fully Autonomous

The market has bifurcated:

| Approach                     | Tools                                            | Evidence                                                                    |
| ---------------------------- | ------------------------------------------------ | --------------------------------------------------------------------------- |
| **Fully autonomous**         | Devin, background agents                         | Nubank 12x efficiency on migrations. But: 67.3% PR rejection rate (LinearB) |
| **Human-in-the-loop**        | Conductor, Claude Squad, Claude Code interactive | UC San Diego/Cornell: "Professional developers don't vibe, they control"    |
| **Hybrid (emerging winner)** | Cursor background + review, GitHub Copilot agent | Human defines scope, agent executes, human reviews PR                       |

The hybrid model is winning. Addy Osmani: "Human effort is front-loaded (writing a good task description) and back-loaded (reviewing the final code), but not much is needed in the middle."

**Nancy's position:** Nancy IS the hybrid model, architected from first principles. Issue tracker defines scope (front-loaded), agent executes (middle), human reviews via git (back-loaded).

### 2.2 Single Agent vs Multi-Agent Coordination

Three patterns have emerged:

**Pattern 1: Hierarchical (Planner/Worker/Judge)**

- Cursor's browser experiment proved this works at scale.
- Planners explore and decompose, Workers execute independently, Judges evaluate.
- Claude Code's Agent Teams follow this with lead + teammate roles.

**Pattern 2: Parallel Independent (Git Worktree Isolation)**

- Each agent gets its own worktree, works independently, results merged.
- Tools: Claude Squad, Conductor (Melty Labs), Parallel Worktrees skill.
- Standard isolation mechanism across the industry now.

**Pattern 3: Sequential Pipeline**

- Plan -> Code -> Test -> Review -> Merge, each potentially a different agent.
- Factory.ai "Droids" automate entire pipeline.
- More reliable than parallel for interdependent changes.

**Steve Yegge's Gas Town** combines all three: The Mayor (planner), Polecats (parallel workers on worktrees), The Refinery (merge queue manager). Built 130,000+ lines of Go in 6 days. But described as "extremely alpha" and "riding a wild stallion."

### 2.3 File-Based vs Socket-Based IPC

| Mechanism              | Used By                                                | Tradeoffs                                                        |
| ---------------------- | ------------------------------------------------------ | ---------------------------------------------------------------- |
| **Git-backed files**   | Nancy (sessions), Beads (.beads/beads.jsonl), Gas Town | Persistent, auditable, survives crashes, merge-friendly. Slower. |
| **Filesystem signals** | Nancy (directives), Claude Code (hooks)                | Simple, reliable, no daemon needed. Race conditions possible.    |
| **Stdin/stdout pipes** | Claude Code CLI, Aider                                 | Direct, low latency. Requires process management.                |
| **SDK/API**            | Claude Code SDK, OpenHands event stream                | Structured, typed, proper error handling. Adds dependency.       |
| **tmux panes**         | Nancy (orchestrator), Claude Squad                     | Visual, human-observable. Fragile, terminal-dependent.           |

**Trend:** The industry is moving from file-based to SDK-based IPC for agent-to-agent communication, while keeping file-based (git) for human-visible state and audit trails. Nancy should consider a dual approach: SDK-based for real-time agent control, git-based for persistent state.

### 2.4 Session Management and Context Windowing

The "50 First Dates" problem (Yegge's term) is universal: agents have no memory between sessions.

**Solutions emerging:**

- **Aider's Repository Map:** Tree-sitter AST + PageRank for intelligent context selection. Now industry standard.
- **Claude Code's Compaction:** Summarize conversations when nearing limits, preserving key decisions.
- **Beads (Yegge):** Issues stored as JSONL in git, cached in SQLite. Hash-based IDs to prevent merge conflicts. "Land the plane" pattern where agents clean up state at session end.
- **Nancy's approach:** Session history files in `.nancy/tasks/<task>/sessions/`. Agent reads previous sessions + git log at start of each iteration.
- **CLAUDE.md accumulation:** "Every mistake becomes a rule" -- Anthropic's pattern of accumulating learnings in project-level instruction files.

**Key insight:** The winning pattern combines ephemeral context (current conversation) with persistent context (project rules, session history, git log). Nancy already does this. The Rust rewrite should make it faster and more structured.

### 2.5 Git Worktree Isolation

Git worktrees have become THE standard for multi-agent parallel development:

- Share a single `.git` directory (lightweight, synchronized).
- Each agent gets its own working directory and branch.
- No merge conflicts during execution.
- Easy cleanup for failed experiments.
- Supported by: Cursor (up to 8 parallel agents), Claude Squad, Conductor, Gas Town, Parallel Worktrees skill.

**Article from Upsun Developer Center (Feb 11, 2026):** "Git worktrees started as a way to handle emergency hotfixes without stashing your work. Now they're how developers run multiple AI coding agents at the same time."

**Nancy already uses worktrees** (there's a `worktrees/` directory in the project). The Rust rewrite should make worktree management a first-class primitive.

### 2.6 Tool Use and MCP (Model Context Protocol)

MCP has achieved critical mass:

- **Introduced** by Anthropic late 2024 as open standard.
- **Adoption by Feb 2026:** Claude Code, Cursor, Goose (3,000+ tools), OpenAI ChatGPT, VS Code, and dozens of others.
- **MCP Apps (Jan 26, 2026):** First official MCP extension. Tools can now return interactive UI components that render in conversations. Developed jointly by Anthropic and OpenAI.
- **Ecosystem:** Described as "USB-C for AI" -- universal connector between AI models and external tools/data.
- **Architecture:** Client-server model. MCP servers expose tools (functions), resources (data), and prompts. MCP clients (the AI apps) discover and invoke them.

**Key insight for Nancy:** MCP is the integration standard. Nancy should expose its capabilities (task management, status, directives) as an MCP server that any AI client can consume. Nancy should also be an MCP client that can discover and use tools from the ecosystem.

### 2.7 Planning -> Execution -> Review Loops

The most effective workflow pattern, described consistently across sources:

1. **Explore:** Agent reads relevant files (explicitly told NOT to code yet)
2. **Plan:** Use extended thinking / "think hard" mode. Document plan in markdown.
3. **Execute:** Implement the plan. For parallel work, dispatch to multiple agents.
4. **Verify:** Run tests, lint, type check. Agent self-validates.
5. **Review:** Human reviews diff/PR. Optionally, a separate AI reviewer.
6. **Iterate:** If issues found, loop back with corrections.

Anthropic's engineering guidance: "Planning is essential. Agents should plan, then act. This goes a long way towards maintaining coherence."

One practitioner calls it "waterfall in 15 minutes."

**Nancy's loop** (read sessions -> check git -> work -> export -> repeat) IS this pattern, implemented as an autonomous iteration cycle. The Rust rewrite should make each phase explicit and hookable.

---

## 3. What's Changed Since January 2026

### 3.1 Claude Code Evolution (Jan-Feb 2026)

**Agent Teams (Feb 2026):** The biggest shift. A lead agent can create teammate agents that work in parallel, message each other, and claim tasks from a shared list. This moves Claude Code from "single agent with sub-agents" to "multi-agent team."

**Hooks system matured:** Now 14 event types. The community has built security guardrails, auto-formatting pipelines, and workflow automations on top. No longer experimental -- production-ready.

**Skills ecosystem:** Community-contributed skill repositories have proliferated. Skills are reusable markdown instruction sets that Claude Code invokes contextually. This pattern validates Nancy's own skill-based architecture.

**Claude Code for Web:** Hosted version with sandboxed execution. Mobile access. Async task queuing. "Teleport" feature to transfer sessions to local environment.

**Code Kit v4.6:** Released for Claude Code's new Task System, indicating continued investment in orchestration primitives.

### 3.2 MCP Ecosystem Growth

**MCP Apps (Jan 26, 2026):** Tools can return interactive UIs. Joint Anthropic/OpenAI standard. This is a massive expansion of what MCP can do.

**Adoption velocity:** Every major AI coding tool now supports MCP. It's becoming the de facto standard, not just an Anthropic thing.

**Registry & publishing:** MCP now has a registry for discovering servers, CLI tools for publishing, and automated publishing pipelines.

### 3.3 New Orchestration Patterns

**Ralph Wiggum loops -> Task tool:** The pattern Nancy is named after (autonomous loops that re-feed prompts until success criteria are met) was pioneered by Geoffrey Huntley mid-2025. Claude Code's Task system now provides some of this natively, reducing the need for external loops. But the external orchestrator (Nancy's approach) still provides: issue tracker integration, cross-session memory, human review gates, and multi-CLI support.

**Conductor (Melty Labs):** Orchestration tool that deploys multiple Claude Code agents with git worktree isolation. Dashboard for monitoring. GitHub integration shows tasks as "Merged" with archive buttons. Staff SWE at LinkedIn: "I found Conductor to make the most sense to me."

**Claude Squad:** Open-source terminal multiplexer for parallel Claude instances. Spawns multiple Claude Code sessions in tmux panes.

**myclaude:** Multi-backend orchestration. Routes tasks to Claude, Codex, or Gemini based on task type. Manages context across backends.

**Gas Town (Steve Yegge):** Most ambitious orchestrator. 20-30 parallel agents, git worktrees, Mayor/Polecat/Refinery hierarchy. But "extremely alpha."

---

## 4. Nancy's Positioning

### 4.1 The Gap in the Market

Every tool analyzed above falls into one of two categories:

**Category A: AI Agents (the executors)**

- Claude Code, Devin, OpenHands, Cursor, Aider, SWE-agent, Goose
- They DO the coding work
- Increasingly sophisticated at single-task execution
- Adding their own orchestration features (Agent Teams, background agents)

**Category B: Agent Orchestrators (the coordinators)**

- Claude Squad, Conductor, Gas Town, myclaude
- They coordinate MULTIPLE agents
- Focused on parallel execution and worktree isolation
- Mostly thin wrappers around Claude Code

**The gap:** Neither category connects to the WHY of the work. No tool bridges from "what does the team need built" (issue tracker) through "coordinate agents to build it" (orchestration) to "verify it was built correctly" (review loop) with the human as the quality gate.

This is where Nancy sits.

### 4.2 Nancy's Unique Value Proposition

Nancy is not another AI coding tool. It's not another orchestrator wrapper. Nancy is the **project coordination layer** that connects:

```
Issue Tracker (Linear)     Nancy Orchestrator        AI Agents (any CLI)

  "What to build"    -->   "How to build it"    -->  "Build it"
  (human intent)           (decomposition,           (execution)
                            dispatching,         <--
                            verification)        "Review it"
                                                (git-based verification)
```

**Differentiators:**

1. **Issue tracker as source of truth.** No other orchestrator starts from Linear/GitHub Issues. They start from human prompts or markdown files. Nancy makes the issue tracker the canonical interface for both humans and agents.

2. **CLI-agnostic.** Gas Town is Claude-only. Conductor is Claude-only. Claude Squad is Claude-only. Nancy works with any AI CLI -- Claude Code, Copilot, Aider, future tools. This is future-proof.

3. **Human-in-the-loop by design, not as an afterthought.** Nancy's loop (issue -> spec -> execute -> review -> iterate) has the human at every gate. Not "fire and forget with a PR at the end" but "iterative self-correction with human verification at each cycle."

4. **Git history as memory.** Most agents have "50 First Dates" amnesia between sessions. Nancy's agents read previous session history AND git log to understand what happened. Mistakes become learnings. This is closer to Yegge's Beads pattern but simpler and built-in.

5. **Experiment infrastructure.** Nancy's `experiment` command enables reproducible A/B testing of agent approaches from GitHub issues. No other tool has this.

6. **Directive system.** Nancy can redirect workers mid-task via file-based directives. This is the human-in-the-loop knob -- from fully autonomous (no directives) to tightly guided (frequent redirects).

### 4.3 Strategic Risks

**Risk 1: Claude Code subsumes orchestration.**
Agent Teams + Task tool + background agents + hooks mean Claude Code is building its own orchestration. If Anthropic ships "Claude Code Projects" with issue tracker integration, Nancy's differentiation narrows.

**Mitigation:** Nancy is CLI-agnostic. As long as multiple AI CLIs exist (and they will -- Cursor, Copilot, Codex, Aider, Goose), there's value in a tool that coordinates across them. Also, Nancy's iteration loop and self-correction via git history is architecturally different from Agent Teams.

**Risk 2: MCP makes orchestration commoditized.**
If every tool speaks MCP, maybe any tool can orchestrate any other tool, and the orchestration layer becomes trivial.

**Mitigation:** MCP is a communication protocol, not an orchestration strategy. Having a USB-C port doesn't mean you don't need a computer to plug it into. Nancy's value is the workflow intelligence (decomposition, dispatching, verification, iteration), not the communication channel.

**Risk 3: Fully autonomous agents get good enough.**
If Devin-class agents achieve 90%+ success rates, the human-in-the-loop becomes overhead rather than value-add.

**Mitigation:** Google's DORA Report data (9% bug rate increase, 91% review time increase) suggests we're far from this. The METR study (19% slower despite feeling 20% faster) suggests the quality gap is persistent. Nancy's bet on human oversight is the right bet for the next 2-3 years at minimum.

### 4.4 Architecture Recommendations for Rust Rewrite

Based on this landscape analysis:

1. **Make git worktree management a first-class primitive.** Every serious orchestrator uses worktrees. Nancy should make creating, managing, and merging worktrees trivial.

2. **Expose Nancy as an MCP server.** Let any MCP-capable client (Claude Code, Cursor, etc.) discover Nancy's capabilities: task listing, status checking, directive sending, session history reading.

3. **Support multiple worker backends.** Start with Claude Code CLI (via stdout/stdin). Add Agent SDK support. Design the interface so Aider, Copilot CLI, and future tools can be plugged in.

4. **Implement the Plan/Execute/Review loop explicitly.** Make each phase a distinct state in the task state machine. Allow hooks at each transition. This aligns with industry best practice.

5. **Keep file-based state for persistence, add structured APIs for real-time.** Git-backed state (sessions, specs, directives) for durability and auditability. gRPC or local socket for real-time agent control and status.

6. **Build repository map capability.** Aider's tree-sitter + PageRank pattern is now industry standard for context selection. Nancy should provide this to workers, not leave it to each agent's own implementation.

7. **Design for the Conductor -> Orchestrator spectrum.** Some tasks need a human conductor (interactive, single agent). Others need autonomous orchestration (parallel agents on worktrees). Nancy should support both modes fluidly.

---

## 5. Competitive Landscape Matrix

| Tool         | Type               | Multi-Agent        | Issue Tracker         | Human-in-Loop     | CLI-Agnostic     | Git-Native   | Open Source |
| ------------ | ------------------ | ------------------ | --------------------- | ----------------- | ---------------- | ------------ | ----------- |
| **Nancy**    | Orchestrator       | Planned            | Linear (core)         | By design         | Yes              | Yes          | Yes         |
| Claude Code  | Agent              | Agent Teams        | No                    | Optional          | No (Claude only) | Via tools    | No          |
| Devin        | Agent              | Parallel instances | Slack/GitHub          | Plan approval     | No (Devin only)  | Via agent    | No          |
| OpenHands    | Agent              | Delegation         | No                    | Optional          | Multi-LLM        | Via agent    | Yes         |
| Cursor       | Agent+Orchestrator | 8 parallel         | No                    | Background+review | No (Cursor only) | Worktrees    | No          |
| Aider        | Agent              | No                 | No                    | Interactive only  | Multi-LLM        | Core feature | Yes         |
| SWE-agent    | Agent              | No                 | GitHub Issues (input) | No                | Multi-LLM        | Via Docker   | Yes         |
| Goose        | Agent              | Roadmap            | No                    | Interactive       | Multi-LLM + MCP  | Via tools    | Yes         |
| Gas Town     | Orchestrator       | 20-30 agents       | Beads (custom)        | Mayor pattern     | No (Claude)      | Worktrees    | Yes         |
| Conductor    | Orchestrator       | Multi-session      | No                    | Dashboard         | No (Claude)      | Worktrees    | Yes         |
| Claude Squad | Orchestrator       | Multi-session      | No                    | tmux visual       | No (Claude)      | No           | Yes         |

**Nancy's unique combination:** Issue tracker integration + CLI-agnostic + human-in-the-loop by design + git-native iteration. No other tool has all four.

---

## 6. Key Quotes and Data Points

**On the shift to orchestration:**

> "The role of the software engineer is evolving from implementer to manager, or in other words, from coder to conductor and ultimately orchestrator." -- Addy Osmani, O'Reilly Radar, Feb 2026

**On quality vs speed:**

> "GenAI amplifies indiscriminately. When you ask it to generate code, it doesn't distinguish between good and bad." -- Birgitta Boeckeler, Global Lead for AI-assisted Software Delivery, Thoughtworks

**On realistic productivity:**

> ~40% of time spent coding, ~60% of that time the assistant is useful, ~55% faster when useful. Net cycle time impact: 8-13%, not the 50% marketing claims suggest. -- Boeckeler's calculation

**On professional developers:**

> "Professional Software Developers Don't Vibe, They Control." -- UC San Diego/Cornell study, Dec 2025

**On planning:**

> "Planning is essential. Agents should plan, then act. This goes a long way towards maintaining coherence." -- Anthropic engineering guidance

**On the memory problem:**

> "The 50 First Dates problem -- agents have no memory between sessions and create conflicting swamps of markdown files." -- Steve Yegge

**On parallelism:**

> "The emerging consensus is that parallelism is the key productivity multiplier -- multiple agents on separate git worktrees, with human oversight as orchestrator rather than implementer." -- Mike Mason

**On Git worktrees:**

> "Git worktrees started as a way to handle emergency hotfixes without stashing your work. Now they're how developers run multiple AI coding agents at the same time." -- Upsun Developer Center, Feb 2026

---

## 7. Sources

### Primary Analysis

- Mike Mason, "AI Coding Agents in 2026: Coherence Through Orchestration, Not Autonomy" (Jan 22, 2026) -- https://mikemason.ca/writing/ai-coding-agents-jan-2026/
- Addy Osmani, "Conductors to Orchestrators: The Future of Agentic Coding" (Feb 13, 2026) -- O'Reilly Radar

### Tool-Specific

- Claude Code Agent Teams documentation -- https://claudefa.st/blog/guide/agents/agent-teams
- Claude Code Sub-Agent design -- https://claudefa.st/blog/guide/agents/sub-agent-design
- Claude Agent SDK guide -- https://dev.to/rajeshroyal/claude-agent-sdk-build-agents-that-work-like-claude-code-50ln
- Agent Teams with Claude Code and Agent SDK -- https://kargarisaac.medium.com/agent-teams-with-claude-code-and-claude-agent-sdk
- Task Tool deep dive -- https://dev.to/bhaidar/the-task-tool-claude-codes-agent-orchestration-system-4bf2
- Devin AI guide -- https://www.digitalapplied.com/blog/devin-ai-autonomous-coding-complete-guide
- OpenHands analysis -- https://atoms.dev/insights/a-comprehensive-analysis-of-opendevin-openhands-architecture-development-use-cases-and-challenges
- Cursor 2.0 architecture -- https://www.digitalapplied.com/blog/cursor-2-0-agent-first-architecture-guide
- Cursor agent internals -- https://blog.bytebytego.com/p/how-cursor-shipped-its-coding-agent
- Aider overview -- https://hypereal.tech/a/aider-ai
- SWE-agent -- https://swe-agent.com/latest/
- Goose review -- https://venturebeat.com/infrastructure/claude-code-costs-up-to-usd200-a-month-goose-does-the-same-thing-for-free
- Goose roadmap -- https://github.com/block/goose/discussions/6973
- Goose self-maintenance -- https://block.github.io/goose/blog/2025/12/28/goose-maintains-goose

### Patterns and Ecosystem

- MCP Apps announcement -- https://blog.modelcontextprotocol.io/posts/2026-01-26-mcp-apps/
- MCP ecosystem analysis -- https://bytebridge.medium.com/mcp-today-and-tomorrow-composability-context-and-the-road-ahead
- Git worktrees for parallel agents -- https://devcenter.upsun.com/posts/git-worktrees-for-parallel-ai-coding-agents/
- Parallel Worktrees skill -- https://github.com/spillwavesolutions/parallel-worktrees
- Claude Code hooks guide -- https://claudefa.st/blog/tools/hooks/hooks-guide
- Multi-agent orchestration patterns -- https://developertoolkit.ai/en/codex/productivity-patterns/multi-agent-workflows/
- AI coding trends 2026 -- https://beyond.addy.ie/2026-trends/
- Orchestrator alternatives discussion -- https://www.reddit.com/r/ClaudeAI/comments/1qs2d4g/orchestrators_that_are_less_bloated_than_gas_town/
