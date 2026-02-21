---
title: Claude Code Subagent Skill Invocation and Agent Discovery Capabilities
type: research
tags: [claude-code, subagents, skills, agent-discovery, multi-agent, orchestration]
summary: Subagents cannot invoke skills via the Skill tool or spawn other subagents; no runtime API exists for agent self-discovery; workarounds exist via preloaded skills and CLI enumeration.
status: active
source: deep-research
confidence: high
created: 2026-03-15
updated: 2026-03-15
---

## Executive Summary

Claude Code subagents **cannot** use the Skill tool to invoke slash commands at runtime, and they **cannot** spawn other subagents. These are hard architectural constraints, not bugs. Skills can only be injected into subagents via the `skills:` frontmatter field at startup (content preloading), not discovered or invoked dynamically. There is no runtime API for agents to enumerate available agent types or skills. The `claude agents` CLI command provides static enumeration outside a session, but nothing equivalent exists inside an agent's execution context.

## Detailed Findings

### Q1: Can a subagent use the Skill tool to invoke slash commands?

**No.** Three independent lines of evidence confirm this:

1. **Official documentation** (code.claude.com/docs/en/sub-agents): "Subagents don't inherit skills from the parent conversation; you must list them explicitly" via the `skills:` frontmatter field. The full skill content is **injected at startup**, not made available for runtime invocation. This is static preloading, not dynamic invocation.

2. **Official documentation** (code.claude.com/docs/en/skills): The Skill tool is a tool available to the **main conversation agent**. The docs state: "Built-in commands like `/compact` and `/init` are not available through the Skill tool." The Skill tool's availability is controlled by `allowed-tools` and permission rules, but subagents receive only their declared tools, and the Skill tool is not among the tools subagents can use.

3. **GitHub issue #24072**: Confirms the Skill tool is explicitly excluded from the Plan subagent. The broader pattern is that subagents receive a stripped-down tool set. The Skill tool is a main-session concept.

4. **GitHub issue #18057**: Documents a crash when the Skill tool attempts to invoke a nonexistent skill, suggesting the Skill tool does operate in some agent contexts but is fragile. However, this appears to be a main-session edge case, not subagent behavior.

**The only way to give a subagent skill knowledge is via static preloading:**

```yaml
---
name: api-developer
skills:
  - api-conventions
  - error-handling-patterns
---
```

This injects the full SKILL.md content into the subagent's context window at startup. The subagent cannot discover or load additional skills during execution.

**Known bug (issue #29441):** When agent teams spawn teammates, the `skills:` frontmatter is not honored. The startup sequence never reads `agent.skills` and performs no skill resolution or injection. This means even the static preloading path is broken for team-spawned agents.

**Known bug (issue #27736):** The main session's Agent tool description does not render the `skills:` field from subagent frontmatter. The main agent cannot see what skills a subagent has preloaded, degrading orchestration quality. One user reported 4 failed attempts before successfully prompting the right agent because skill visibility was missing.

### Q2: Is there a programmatic way to list available agent types?

**Partially, but only outside the agent's runtime context.**

1. **CLI command `claude agents`**: Lists all configured subagents grouped by source (built-in, user, project, plugin) and indicates override priority. This runs outside an interactive session and is the closest thing to an enumeration API.

2. **`/agents` interactive command**: Inside a session, the `/agents` slash command opens an interactive interface to view, create, edit, and delete subagents. This is user-facing, not programmatically accessible to the agent itself.

3. **`--agents` CLI flag**: Accepts JSON agent definitions at session launch. This is a configuration mechanism, not a discovery mechanism.

4. **Agent SDK (`agents` parameter)**: In the TypeScript/Python SDK, subagents are defined programmatically in the `agents` dict passed to `query()`. Claude sees the descriptions of all defined agents and selects among them. But this is static configuration provided by the developer, not runtime discovery by the agent.

**There is no runtime introspection API.** An agent executing inside Claude Code cannot call a function or tool to enumerate what other agents or skills exist. The agent's knowledge of available agents comes entirely from:
- The Agent tool's system prompt, which lists available subagent types and their descriptions
- For the main session: skill descriptions loaded into context (up to 2% of context window budget)

**Feature requests exist but are unresolved:**
- Issue #12612: Request for `claude model list` CLI command (no agent list equivalent)
- Issue #6574: Request for CLI command to list available MCP tools and servers
- Issue #25771: Request for `claude skills list` / `claude skills deploy` CLI commands

### Q3: Can agents discover what other agents exist at runtime?

**No, with important nuances.**

The main session agent knows about available subagents because the Agent tool's description includes a list of available agent types with their descriptions. This is injected into the system prompt at session startup. So the main agent can "see" what subagents are available, but:

1. **This is static.** The list is frozen at session startup. Creating a new agent file mid-session requires a restart or `/agents` reload.

2. **Subagents cannot see sibling agents.** A subagent has no Agent tool (confirmed: "Subagents cannot spawn other subagents"). Therefore a subagent has zero visibility into what other agents exist.

3. **Skills field is invisible to the main agent** (issue #27736). Even when the main agent can see subagent names and descriptions, it cannot see what skills each subagent has preloaded, limiting informed delegation.

4. **Agent Teams** (experimental, `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`): Agent teams coordinate multiple Claude Code instances with shared tasks and inter-agent messaging. Teammates work independently in their own context windows and can communicate directly. However, this is a separate paradigm from subagents. Agent teams are described in natural language and the team lead coordinates work. This is the closest thing to agent-to-agent discovery, but it operates at the session level (each teammate is a full Claude Code instance), not at the tool level.

### Architectural Constraints Summary

| Capability | Main Agent | Subagent | Agent Team Member |
|---|---|---|---|
| Invoke Skill tool | Yes | No | Unknown (likely yes, as full CC instance) |
| Spawn subagents | Yes | No | Yes (full CC instance) |
| See available agents | Yes (via Agent tool desc) | No | Yes (via team messaging) |
| Preload skills | N/A (loads from context) | Yes (via `skills:` field) | Broken (issue #29441) |
| Discover skills at runtime | Yes (Skill tool) | No | Unknown |
| `Agent(type)` tool restriction | Yes | No effect (cannot spawn) | Yes |

### Workarounds for Multi-Agent Orchestration

1. **Preload skills into subagent frontmatter.** This is the official pattern. List all skills a subagent needs in its `skills:` field. The content is injected at startup.

2. **Use the main agent as orchestrator.** The main agent has both the Skill tool and the Agent tool. It can load a skill, extract information, then pass that information to a subagent via the Agent tool's prompt string.

3. **Embed knowledge directly in subagent markdown.** For small amounts of domain knowledge, put it directly in the subagent's system prompt rather than referencing skills.

4. **Use Agent Teams for peer-to-peer discovery.** If agents need to discover and communicate with each other at runtime, Agent Teams is the intended mechanism. Each teammate is a full Claude Code instance with access to skills and tools.

5. **External orchestration via the Agent SDK.** Build a controlling process that enumerates agents/skills from the filesystem, then passes the relevant configuration to `query()` calls. This moves discovery outside Claude Code into your own code.

6. **MCP-based communication.** Use an MCP server (like helioy-bus) as a shared message bus. Agents can read/write to the bus to discover each other and exchange information. This requires each agent to have the MCP server configured.

## Sources Consulted

### Official Documentation
- [Create custom subagents](https://code.claude.com/docs/en/sub-agents) -- primary reference for subagent capabilities, tool access, skill preloading
- [Extend Claude with skills](https://code.claude.com/docs/en/skills) -- skill invocation, discovery, Skill tool mechanics
- [Subagents in the SDK](https://platform.claude.com/docs/en/agent-sdk/subagents) -- Agent SDK programmatic subagent definition
- [Agent Teams](https://code.claude.com/docs/en/agent-teams) -- inter-agent communication at the session level

### GitHub Issues (anthropics/claude-code)
- [#17283](https://github.com/anthropics/claude-code/issues/17283) -- Skill tool ignoring `context: fork` and `agent:` frontmatter (CLOSED as completed)
- [#27736](https://github.com/anthropics/claude-code/issues/27736) -- Agent skills field not rendered in Agent tool description
- [#12633](https://github.com/anthropics/claude-code/issues/12633) -- Feature request for subagent-exclusive skills (hide from main agent)
- [#24072](https://github.com/anthropics/claude-code/issues/24072) -- Skill tool not available in Plan mode
- [#18057](https://github.com/anthropics/claude-code/issues/18057) -- Subagent crash on Skill tool invoking nonexistent skill
- [#29441](https://github.com/anthropics/claude-code/issues/29441) -- Agent `skills:` frontmatter not preloaded for team-spawned teammates
- [#25771](https://github.com/anthropics/claude-code/issues/25771) -- Feature request for programmatic skill deployment via CLI/API
- [#20931](https://github.com/anthropics/claude-code/issues/20931) -- Custom agents not loaded as subagent types
- [#11205](https://github.com/anthropics/claude-code/issues/11205) -- Custom subagents not discovered
- [#4623](https://github.com/anthropics/claude-code/issues/4623) -- Sub-agents not detected in CLI list
- [#11028](https://github.com/anthropics/claude-code/issues/11028) -- Tool name duplication error when spawning subagents

### X/Twitter
- [@claude_code](https://x.com/claude_code/status/1948622899604050063) -- Official tips on subagent selection via description fields
- [@omarsar0](https://x.com/omarsar0/status/1981798842866557281) -- Skills vs subagents mental model
- [@omarsar0](https://x.com/omarsar0/status/1949204315350216789) -- Multi-agent deep research with subagents
- [@sethlazar](https://x.com/sethlazar/status/2006214936603844668) -- Lessons on multi-agent orchestration compute costs

### Blog Posts
- [Claude Code Customization Guide](https://alexop.dev/posts/claude-code-customization-guide-claudemd-skills-subagents/) -- alexop.dev
- [Claude Code Skills vs Subagents](https://dev.to/nunc/claude-code-skills-vs-subagents-when-to-use-what-4d12) -- DEV Community
- [Mental Model for Claude Code](https://levelup.gitconnected.com/a-mental-model-for-claude-code-skills-subagents-and-plugins-3dea9924bf05) -- Level Up Coding / Medium

## Source Quality Assessment

**Confidence: High.** The official documentation at code.claude.com is comprehensive and recently updated. GitHub issues provide ground-truth behavioral observations from users hitting actual limitations. The X/Twitter discussions are from practitioners building real systems. The architectural constraints (no subagent-to-subagent spawning, no Skill tool in subagents) are stated explicitly in official docs, not inferred.

**Gap:** The Agent Teams feature is experimental and documentation is thinner. The interaction between Agent Teams and skills/subagents is poorly documented. Issue #29441 suggests the integration is incomplete.

## Open Questions

1. **Agent Teams + Skills:** Do agent team members (full CC instances) have access to the Skill tool? The docs do not explicitly confirm this.
2. **Plugin-provided agent enumeration:** Could a plugin expose a tool that reads `~/.claude/agents/` and `.claude/agents/` at runtime, giving agents filesystem-based discovery?
3. **MCP-based skill injection:** Could an MCP server dynamically provide skill-like content to subagents mid-execution, bypassing the static preloading limitation?
4. **`context: fork` resolution:** Issue #17283 was closed as completed. Does the Skill tool now honor `context: fork` and `agent:` fields? If so, this partially addresses the gap by letting skills run in subagent contexts.

## Actionable Takeaways

For the helioy multi-agent orchestration system:

1. **Do not rely on subagents invoking skills dynamically.** Design the system so that all required knowledge is either preloaded via `skills:` frontmatter or passed through the Agent tool's prompt string.

2. **Use MCP (helioy-bus) for inter-agent discovery.** Since Claude Code provides no native runtime discovery, an MCP-based registry where agents announce themselves and query for peers is the correct architectural choice.

3. **The main agent must serve as the skill-aware orchestrator.** Only the main session has access to the Skill tool. If a workflow requires loading a skill and then delegating based on its content, the main agent must do the skill loading and content extraction before delegating to subagents.

4. **Consider Agent Teams for peer-to-peer workflows.** If the orchestration pattern requires agents to discover and communicate with each other (rather than hub-and-spoke through a main agent), Agent Teams is the intended mechanism, despite being experimental.

5. **Build external enumeration into nancyr.** Since no runtime introspection API exists, the Rust orchestrator should read agent definitions from `~/.claude/agents/` and `.claude/agents/` at startup and maintain its own registry. This is more reliable than depending on Claude Code's internal mechanisms.
