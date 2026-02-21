---
title: Claude Code Agent Definitions vs Skills - Community Research
type: research
tags: [claude-code, agents, skills, optimization, tokens]
summary: Agent definitions provide structural enforcement (tool restrictions, model routing, context isolation) that skills cannot; skills provide portable domain knowledge and on-demand loading. The real problem is token bloat from eagerly-loaded agent descriptions.
status: active
source: deep-research
confidence: high
created: 2026-03-17
updated: 2026-03-17
---

## Executive Summary

Agent definitions and skills serve categorically different purposes in Claude Code, though the boundary is blurry for many use cases. Agent definitions provide **structural enforcement** (tool allow/deny lists, model selection, permission modes, context isolation via separate context windows). Skills provide **portable domain knowledge and task workflows** that load on demand. The dominant community pain point in early 2026 is not choosing between the two, but managing the **token overhead** that agent definitions impose on every session. Agent descriptions are eagerly injected into the system prompt's Agent tool definition, consuming tokens even when unused. Anthropic's ToolSearch (deferred tool loading) addresses MCP tools but does not yet apply to agent definitions or skills.

## Detailed Findings

### 1. What Agent Definitions Provide Beyond Skills

Agent definitions in `.claude/agents/` offer capabilities that skills cannot replicate:

**Structurally enforced constraints.** The `tools` and `disallowedTools` fields in agent YAML frontmatter create hard restrictions on what tools a subagent can access. A read-only code reviewer with `tools: Read, Grep, Glob, Bash` physically cannot call Write or Edit. Skills can specify `allowed-tools`, but this only controls permission prompts, and skills run in the parent's context by default rather than an isolated one.

**Model routing.** Agents can specify `model: haiku` or `model: sonnet` to control cost. An Explore agent running on Haiku costs a fraction of Opus. Skills have a `model` field but it applies to the parent context, not a separate execution environment.

**Context isolation.** The primary value proposition. Subagents run in their own context window, preventing exploration noise from polluting the parent session's 200K token limit. When a subagent finishes, only its summary returns to the parent. Skills run inline by default; the `context: fork` option creates isolation but delegates to a built-in agent type rather than a fully custom configuration.

**Permission modes.** Agents support `permissionMode: bypassPermissions`, `acceptEdits`, `dontAsk`, or `plan`. This allows automated workflows without human approval gates. Skills cannot configure permission modes independently.

**Lifecycle hooks.** Agents support `PreToolUse`, `PostToolUse`, and `Stop` hooks scoped to the subagent's execution. This enables per-agent validation logic (e.g., blocking SQL writes for a db-reader agent).

**Background execution.** Agents can run in the background (`background: true`) or be backgrounded with Ctrl+B. Skills with `context: fork` can achieve similar results but with less control.

**Git worktree isolation.** The `isolation: worktree` option gives an agent its own copy of the repository. No skill equivalent exists.

**Persistent memory.** Agents support `memory: user|project|local` for cross-session learning. Skills do not have a memory primitive.

**MCP server scoping.** Agents can have MCP servers that only exist during their execution, avoiding system prompt bloat for the parent session.

Source: [Claude Code Subagents Documentation](https://code.claude.com/docs/en/sub-agents)

**Bottom line:** If you need tool restrictions, model routing, context isolation, or permission overrides, agent definitions are the correct mechanism. Skills cannot provide these. If you need domain knowledge, step-by-step workflows, or reference material, skills are correct and lighter weight.

### 2. Community Granularity Patterns

Three distinct camps have emerged:

**Fine-grained maximalists (50-127+ agents).** The [VoltAgent awesome-claude-code-subagents](https://github.com/VoltAgent/awesome-claude-code-subagents) collection offers 127+ agents across 10 categories. Multiple forks exist (0xfurai, rahulvrane, supatest-ai). These are designed as a menu to pick from, not to install wholesale. No repository warns about token overhead from loading all 127 definitions.

**Moderate specialists (5-15 agents).** Power users in GitHub issues report setups with 5-13 custom agents. A typical "GSD" (Get Stuff Done) setup described in [Issue #22613](https://github.com/anthropics/claude-code/issues/22613) uses 13 agents consuming ~5,000 tokens in descriptions plus 27 skill entries at ~800 tokens. This level already causes 20%+ context usage before typing.

**Minimalists (0-3 agents, rely on built-in + skills).** The approach recommended by practitioners who have measured token costs. Multiple sources converge on "2-3 focused agents for parallel research, with the main session synthesizing outputs" as the practical sweet spot for solo developers. Source: [ksred.com](https://www.ksred.com/claude-code-agents-and-subagents-what-they-actually-unlock/).

Daniel Miessler's framework (77+ skills, 20+ agents) represents the maximalist architect approach, but he treats skills as the primary organizational unit and agents as parallel workers that invoke skills. Source: [danielmiessler.com](https://danielmiessler.com/blog/when-to-use-skills-vs-commands-vs-agents).

### 3. `--system-prompt` and `--append-system-prompt` Usage

Claude Code provides four system prompt modification flags:

- `--system-prompt`: Replaces the entire system prompt (nuclear option; removes all built-in capabilities)
- `--append-system-prompt`: Appends to the end of the base system prompt (recommended for most uses)
- `--prepend-system-prompt`: Prepends to the start
- `--agents` (JSON): Injects session-scoped agent definitions without creating files

No community evidence exists of anyone using `--system-prompt` to reduce startup costs. The replacement removes Claude Code's built-in tooling and agent infrastructure, making it counterproductive. `--append-system-prompt` is used in CI/CD pipelines and headless automation to inject task-specific instructions.

The `--agents` flag is the most relevant for reducing startup costs: it allows defining session-scoped agents as JSON, avoiding the filesystem-based eager loading that causes permanent token overhead.

Source: [Claude Code CLI Reference](https://code.claude.com/docs/en/cli-reference), [GitHub Issue #2692](https://github.com/anthropics/claude-code/issues/2692)

### 4. Token Cost of Agent Definitions

**How injection works.** All agent `.md` files from `~/.claude/agents/` and `.claude/agents/` are loaded at session start. Their descriptions are injected into the Agent tool (formerly Task tool) definition in the system prompt. Every session pays this cost regardless of whether agents are used.

**Measured overhead:**

| Setup | Token Cost | Source |
|---|---|---|
| 13 GSD agents + 27 skills | ~7,000 tokens | [Issue #22613](https://github.com/anthropics/claude-code/issues/22613) |
| 29 agents (user report) | ~3,000-8,700 tokens (100-300 per agent) | [Issue #4973](https://github.com/anthropics/claude-code/issues/4973) |
| 16.2k tokens measured | Exceeded 15k recommendation | [Issue #8997](https://github.com/anthropics/claude-code/issues/8997) |
| 100+ agent types | ~10,000 tokens | [Issue #19445](https://github.com/anthropics/claude-code/issues/19445) |
| Full power-user setup (agents + skills + MCP + memory) | ~108k tokens (54% of 200k) | [Issue #7336](https://github.com/anthropics/claude-code/issues/7336) |

**Per-agent cost:** Each agent definition consumes approximately 100-300 tokens in the Agent tool description, depending on description length.

**Skill descriptions:** Budget is 2% of context window (fallback: 16,000 characters). Each skill uses ~109 characters of overhead plus description length. Skills load descriptions eagerly but full content on demand.

**Subagent execution cost:** When a subagent is spawned, it starts a fresh context window. Reported costs range from 30K-160K tokens per subagent invocation, depending on task complexity. The 15-77x multiplier vs. doing the same work inline (reported in [Issue #4911](https://github.com/anthropics/claude-code/issues/4911)) is partly explained by subagents inheriting system prompts, user memory, project memory, and MCP tool definitions.

**ToolSearch mitigation.** Anthropic shipped ToolSearch for MCP tools (activates automatically when tool descriptions exceed 10% of context). This reduces MCP overhead by ~85%. However, ToolSearch does **not** apply to agent definitions or skill descriptions. [Issue #19445](https://github.com/anthropics/claude-code/issues/19445) requested AgentSearch and SkillSearch equivalents but was closed as "not planned."

### 5. Anthropic's Published Guidance

Anthropic's official best practices page ([code.claude.com/docs/en/best-practices](https://code.claude.com/docs/en/best-practices)) provides the following guidance on agents:

- "Define specialized assistants in `.claude/agents/` that Claude can delegate to for isolated tasks."
- "Subagents run in their own context with their own set of allowed tools. They're useful for tasks that read many files or need specialized focus without cluttering your main conversation."
- "Use subagents for investigation: Delegate research with 'use subagents to investigate X'."

The subagents documentation offers four design best practices:
1. Design focused subagents: each should excel at one specific task
2. Write detailed descriptions: Claude uses the description to decide when to delegate
3. Limit tool access: grant only necessary permissions
4. Check into version control: share project subagents with your team

**What Anthropic does NOT provide:**
- No guidance on optimal number of agents
- No guidance on token budgets for agent descriptions
- No warning about agent definition bloat
- No recommendation to prefer skills over agents or vice versa for specific patterns
- No measurement guidance for agent overhead

The "Extend Claude Code" feature overview page mentions using skills for "domain knowledge and reusable workflows" and agents for "isolated tasks," but does not provide a decision framework.

### 6. Community Discussions About Agent Definition Bloat

This is the most active area of community concern. Key issues filed against anthropics/claude-code:

**Bloat from eager loading:**
- [#8997](https://github.com/anthropics/claude-code/issues/8997): Dynamic/Lazy Agent Loading (closed, not planned)
- [#22613](https://github.com/anthropics/claude-code/issues/22613): Lazy-load agent descriptions (closed, duplicate of #7336)
- [#4973](https://github.com/anthropics/claude-code/issues/4973): Deleted agents still consuming tokens (closed, not planned)
- [#19445](https://github.com/anthropics/claude-code/issues/19445): AgentSearch/SkillSearch like ToolSearch (closed, not planned)
- [#17022](https://github.com/anthropics/claude-code/issues/17022): /context doesn't display tokens from .claude/agents/ files

**Subagent execution overhead:**
- [#4911](https://github.com/anthropics/claude-code/issues/4911): Subagents 15-77x more tokens than inline work
- [#6825](https://github.com/anthropics/claude-code/issues/6825): Configurable inheritance of system prompt/memory for subagents
- [#4908](https://github.com/anthropics/claude-code/issues/4908): Scoped context passing for subagents
- [#10164](https://github.com/anthropics/claude-code/issues/10164): Show sub-agent token usage in /context
- [#22625](https://github.com/anthropics/claude-code/issues/22625): Per-subagent token usage tracking

**Operational issues:**
- [#7406](https://github.com/anthropics/claude-code/issues/7406): Claude thinks it spawns agents in parallel but doesn't
- [#13326](https://github.com/anthropics/claude-code/issues/13326): Background agents consuming tokens without returning results
- [#25200](https://github.com/anthropics/claude-code/issues/25200): Custom agents cannot use deferred MCP tools

The pattern is clear: Anthropic has closed most lazy-loading requests as "not planned" while shipping ToolSearch only for MCP tools. Agent and skill definition overhead remains unaddressed as of March 2026.

### 7. Opus Over-delegation Problem

Multiple sources confirm that Opus models over-delegate to subagents. Anthropic's own documentation flags this: "Opus will delegate to agents in situations where a direct approach would be faster and cheaper." If you run Opus as your main model and have many agent definitions loaded, Opus reads those descriptions and is more likely to spawn subagents unnecessarily, compounding the token cost. This is a documented behavioral tendency, not a bug.

## Sources Consulted

### Official Documentation
- [Claude Code Subagents](https://code.claude.com/docs/en/sub-agents)
- [Claude Code Skills](https://code.claude.com/docs/en/skills)
- [Claude Code Best Practices](https://code.claude.com/docs/en/best-practices)
- [Claude Code Cost Management](https://code.claude.com/docs/en/costs)
- [Claude Code CLI Reference](https://code.claude.com/docs/en/cli-reference)

### GitHub Issues (anthropics/claude-code)
- [#4911](https://github.com/anthropics/claude-code/issues/4911) - Subagents too slow and cost more tokens
- [#4908](https://github.com/anthropics/claude-code/issues/4908) - Scoped context passing for subagents
- [#4973](https://github.com/anthropics/claude-code/issues/4973) - Deleted agents still consume tokens
- [#6825](https://github.com/anthropics/claude-code/issues/6825) - Configurable inheritance for subagents
- [#7336](https://github.com/anthropics/claude-code/issues/7336) - Lazy loading for MCP servers and tools
- [#8997](https://github.com/anthropics/claude-code/issues/8997) - Dynamic/Lazy agent loading
- [#10164](https://github.com/anthropics/claude-code/issues/10164) - Show sub-agent token usage
- [#13627](https://github.com/anthropics/claude-code/issues/13627) - Agent body content not injected
- [#17022](https://github.com/anthropics/claude-code/issues/17022) - /context doesn't show agent tokens
- [#19445](https://github.com/anthropics/claude-code/issues/19445) - Deferred loading for agents/skills
- [#22613](https://github.com/anthropics/claude-code/issues/22613) - Lazy-load agent descriptions
- [#22625](https://github.com/anthropics/claude-code/issues/22625) - Per-subagent token tracking

### Community Articles and Blogs
- [Daniel Miessler - When to Use Skills vs Commands vs Agents](https://danielmiessler.com/blog/when-to-use-skills-vs-commands-vs-agents)
- [ksred - Claude Code Agents: What They Actually Unlock](https://www.ksred.com/claude-code-agents-and-subagents-what-they-actually-unlock/)
- [alexop.dev - Claude Code Customization Guide](https://alexop.dev/posts/claude-code-customization-guide-claudemd-skills-subagents/)
- [Colin McNamara - Understanding Skills, Agents, and MCP](https://colinmcnamara.com/blog/understanding-skills-agents-and-mcp-in-claude-code)
- [DEV Community - Claude Code Sub Agents Burn Out Your Tokens](https://dev.to/onlineeric/claude-code-sub-agents-burn-out-your-tokens-4cd8)
- [Gigi Sayfan - Claude Code Deep Dive: Subagents in Action](https://medium.com/@the.gigi/claude-code-deep-dive-subagents-in-action-703cd8745769)
- [Piebald-AI/claude-code-system-prompts](https://github.com/Piebald-AI/claude-code-system-prompts) - Extracted system prompt structure

### Curated Collections
- [VoltAgent/awesome-claude-code-subagents](https://github.com/VoltAgent/awesome-claude-code-subagents) - 127+ agent definitions

## Source Quality Assessment

**Confidence: High.** Findings triangulate across official documentation, GitHub issues with measured token counts, and multiple independent community reports. The official docs are comprehensive and current (updated for v2.1.63+ Agent tool rename). GitHub issues provide the most reliable token measurements since they include reproduction steps and exact numbers.

**Gaps:**
- No Reddit threads found on this topic. The Claude Code community discussion happens primarily on GitHub issues and Medium/dev.to.
- X/Twitter searches returned no direct results. Claude Code power user discussions may be happening in private Discords or Slack groups.
- Anthropic has not published a guide specifically comparing skills vs agents or providing token budget recommendations.
- No data exists on how prompt caching interacts with agent definition overhead (definitions would benefit from caching since they are identical across turns).

## Open Questions

1. **Will Anthropic extend ToolSearch to agent definitions?** Issue #19445 was closed "not planned" but the underlying need is real. #31002 suggests built-in system tools are now deferred, which may indicate incremental progress.

2. **What is the interaction between prompt caching and agent description overhead?** If agent descriptions are cached (likely, since they repeat in every turn's system prompt), the marginal token cost after the first turn may be significantly lower than the headline numbers suggest. No one has measured this.

3. **Does Opus over-delegation worsen with more agent definitions?** Anecdotal evidence says yes, but no controlled measurement exists.

4. **What is the optimal agent count before description overhead outweighs benefits?** Given ~200 tokens per agent average, 10 agents costs ~2,000 tokens (~1% of 200K). 50 agents costs ~10,000 tokens (~5%). The breakpoint depends on how often each agent is used.

## Actionable Takeaways

1. **Use agent definitions only when you need their structural enforcement.** Tool restrictions, model routing, permission modes, context isolation, and MCP server scoping are the capabilities skills cannot replicate. For everything else (domain knowledge, workflows, conventions), prefer skills.

2. **Keep agent count low (3-10) for daily work.** Each agent definition costs 100-300 tokens in every session. The community sweet spot is 2-3 focused agents for solo work. Daniel Miessler's 20+ agent setup is an outlier that works because his agents invoke skills rather than carrying heavy descriptions.

3. **Write short agent descriptions.** The `description` field is what Claude uses to decide when to delegate. It is also what gets injected into every session's system prompt. Keep it to one sentence.

4. **Put domain knowledge in skills, not agent system prompts.** Use the `skills` frontmatter field to inject skill content into subagents at spawn time. This avoids loading that content into every session.

5. **Scope MCP servers to agents via `mcpServers` frontmatter.** This prevents MCP tool definitions from bloating the parent session's context.

6. **Use `--agents` JSON for session-scoped definitions.** If you need different agent configurations for different workflows, define them as JSON flags instead of files that load in every session.

7. **Monitor overhead with `/context`.** Note that /context may not currently display agent definition tokens separately (Issue #17022). Watch the "Tools" percentage.

8. **Be aware of Opus over-delegation.** If using Opus as your main model, consider denying Agent access for specific agents you don't want auto-delegated: `permissions.deny: ["Agent(my-expensive-agent)"]`.
