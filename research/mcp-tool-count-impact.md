---
title: "MCP Tool Count Impact on LLM Tool Selection Accuracy"
type: research
tags: [mcp, tool-selection, llm-performance, context-window, claude, tool-search]
summary: "Tool selection accuracy degrades measurably beyond 30-50 tools. Anthropic documents this threshold explicitly. Academic benchmarks show ~10% accuracy drop from 10 to 100 tools, steeper drops beyond 1,000. Multiple mitigation strategies exist (tool search, RAG, lazy loading)."
status: active
source: deep-research
confidence: high
created: 2026-03-17
updated: 2026-03-17
---

## Executive Summary

Tool selection accuracy degrades as available tool count increases. This is documented by Anthropic, confirmed by academic benchmarks, and widely reported by practitioners. Anthropic's own documentation states that Claude's tool selection accuracy "degrades significantly once you exceed 30-50 available tools." Academic benchmarks (HumanMCPBench) show a consistent ~10% accuracy drop from 10 to 100 tools across multiple models, with steeper degradation beyond 1,000 tools. The problem compounds in practice because tool definitions consume 200-850 tokens each, eating context budget before any work begins. Anthropic, OpenAI, and the broader ecosystem have converged on "tool search" / "tool RAG" as the mitigation: load only the 3-5 tools needed per request rather than all tools upfront.

## 1. Anthropic's Official Documentation

### The 30-50 Tool Threshold

Anthropic's Tool Search Tool documentation states directly:

> "Claude's ability to correctly pick the right tool degrades significantly once you exceed 30-50 available tools."

Source: [Tool search tool - Claude API Docs](https://platform.claude.com/docs/en/agents-and-tools/tool-use/tool-search-tool)

### Internal Benchmark Numbers

Anthropic's engineering blog ("Advanced Tool Use") provides internal evaluation data showing tool search improves accuracy on MCP benchmarks:

| Model | Without Tool Search | With Tool Search |
|-------|-------------------|-----------------|
| Opus 4 | 49% | 74% |
| Opus 4.5 | 79.5% | 88.1% |

The baseline numbers (49% for Opus 4, 79.5% for Opus 4.5) represent performance when all tools are loaded into context simultaneously. The improvements come from surfacing only relevant tools.

Source: [Anthropic Engineering - Advanced Tool Use](https://www.anthropic.com/engineering/advanced-tool-use)

### When Anthropic Recommends Tool Search

Anthropic recommends enabling tool search when:
- Tool definitions consume more than 10K tokens
- You experience tool selection accuracy issues
- Building MCP-powered systems with multiple servers
- You have 10+ tools available

Tool search is "less beneficial" with fewer than 10 tools or when all tools are used frequently in every session.

### Claude Code's Automatic Threshold

Claude Code automatically enables tool search when MCP tool descriptions would consume more than 10% of the context window. This is enabled by default for all users.

## 2. Academic Benchmarks: Quantified Degradation

### HumanMCPBench (2026): Accuracy vs. Tool Count

The HumanMCPBench paper tested three models across context configurations of 10, 50, and 100 tools using 500 queries:

| Model | 10 tools | 50 tools | 100 tools | Drop (10 to 100) |
|-------|----------|----------|-----------|-------------------|
| GPT-4o-mini | 98.2% | 92.4% | 88.2% | -10.0 pts |
| Claude 3.5 Haiku | 97.8% | 91.9% | 88.6% | -9.2 pts |
| Gemini 2.0 Flash | 98.4% | 93.6% | 88.2% | -10.2 pts |

At extreme scale (Gemini 2.0 Flash only):
- 500 tools: 87.4%
- 2,000 tools: 65.0%

The sharpest drop occurs between 1,000 and 2,000 tools, suggesting long-context interference becomes significant beyond ~1,000 candidates.

Source: [HumanMCPBench - arXiv:2602.23367](https://arxiv.org/html/2602.23367)

### LiveMCPBench (2025-2026): 527 Tools, 70 Servers

LiveMCPBench evaluates agents against 527 tools across 70 MCP servers on 95 real-world tasks:

| Model | Success Rate | Avg Tools Used |
|-------|-------------|---------------|
| Claude Sonnet 4 | 78.95% | 2.71 |
| Claude Opus 4 | 70.53% | 3.40 |
| DeepSeek-R1-0528 | 48.42% | ~1.0 |
| Qwen3-235B-A22B | 48.42% | ~1.0 |
| GPT-4.1-Mini | 44.21% | ~1.0 |
| Gemini 2.5 Pro | 41.05% | ~1.0 |
| GPT-4.1 | 38.95% | ~1.0 |

The most common error (~50% of failures) is inability to find the correct tool. Most models severely underutilize available tools, averaging close to just one tool per task despite 527 being available.

Source: [LiveMCPBench - arXiv:2508.01780](https://arxiv.org/html/2508.01780v1)

### RAG-MCP (2025): Retrieval-Augmented Tool Selection

RAG-MCP demonstrated that pre-selecting tools via semantic retrieval triples tool selection accuracy:
- Baseline (all tools in context): 13.62%
- With RAG-MCP: 43.13%
- Prompt token reduction: over 50%

Source: [RAG-MCP - arXiv:2505.03275](https://arxiv.org/abs/2505.03275)

### MCP-Zero (2025): Active Tool Discovery at Scale

MCP-Zero tested against 2,797 tools across 308 MCP servers:
- 98% reduction in token consumption versus full-schema injection
- Maintained strong multi-turn consistency (~3% accuracy drop vs >20% in baselines)
- Outperformed retrieval-only baselines (~65-72% accuracy)

Source: [MCP-Zero - arXiv:2506.01056](https://arxiv.org/abs/2506.01056)

## 3. Platform Hard Limits

| Platform | Hard Limit | Notes |
|----------|-----------|-------|
| OpenAI Assistants API | 128 tools | Per run; tools can be swapped between runs |
| Claude Desktop | ~100 tools visible | Observed cap; not officially documented |
| Cursor | 40 tools | Enforced ceiling |
| GitHub Copilot | 128 tools | Per chat request |
| Claude API | 120 tools | Reported maximum |

Sources: [Lunar.dev](https://www.lunar.dev/post/why-is-there-mcp-tool-overload-and-how-to-solve-it-for-your-ai-agents), [Demiliani blog](https://demiliani.com/2025/09/04/model-context-protocol-and-the-too-many-tools-problem/), [MCP Discussion #537](https://github.com/orgs/modelcontextprotocol/discussions/537)

## 4. Token Cost of Tools in Practice

### Per-Tool Token Overhead

- Average tool description: 200-500 tokens (simple tools)
- Measured average in practice: 550-850 tokens per tool
- GitHub MCP server: 27 tools consuming ~18K tokens (~667 tokens/tool)
- Playwright MCP: 21 tools consuming ~13.6K tokens (~649 tokens/tool)

### Real-World Context Consumption

Documented Claude Code setups:

| Configuration | MCP Token Cost | % of 200K Window |
|--------------|---------------|-------------------|
| 7 MCP servers active | 67,300 tokens | 33.7% |
| 3 core servers only | 42,600 tokens | 21.3% |
| 5 servers, 30 tools each (150 total) | 30,000-60,000 tokens | 15-30% |
| Typical multi-server (GitHub, Slack, Sentry, Grafana, Splunk) | ~55,000 tokens | 27.5% |

One user documented 73 MCP tools + 56 agents consuming 108K tokens (54% of 200K window) before any conversation started.

Sources: [GitHub Issue #11364](https://github.com/anthropics/claude-code/issues/11364), [GitHub Issue #7336](https://github.com/anthropics/claude-code/issues/7336), [Scott Spence blog](https://scottspence.com/posts/optimising-mcp-server-context-usage-in-claude-code)

## 5. MCP Server Design Recommendations: Tool Count

### Workato (Enterprise MCP Platform)

- Start with 3-5 core tools
- Limit to 5-8 tools per server
- 8-12 tools is "reasonable"
- Split into separate domains if >15 tools
- Tool name prefixes signal too-broad scope

Source: [Workato MCP Server Design](https://docs.workato.com/mcp/mcp-server-design.html)

### Philipp Schmid (Hugging Face)

- 5-15 tools per server
- "One server, one job"
- Use service-prefixed naming: `{service}_{action}_{resource}`

Source: [philschmid.de/mcp-best-practices](https://www.philschmid.de/mcp-best-practices)

### Block Engineering

- Consolidated their Linear MCP from 30+ tools (v1) to 2 primary tools (v3)
- Workflow-driven consolidation over tool count limits
- Bundle related read-only actions into single tools with category parameters

Source: [Block Engineering Blog](https://engineering.block.xyz/blog/blocks-playbook-for-designing-mcp-servers)

### Datadog Engineering

- Core set of tools by default, opt-in toolsets for specialized needs
- Explored two-call patterns (ask "how do I do X?" then do it) to reduce upfront tool count
- Tradeoff: fewer tools in context but higher latency from chaining

Source: [Datadog Engineering Blog](https://www.datadoghq.com/blog/engineering/mcp-server-agent-tools/)

### Practitioner Rule of Thumb (Claude Code Community)

- 20-30 MCPs configured globally
- Under 10 enabled per project
- Under 80 tools active total

## 6. Claude Code Plugin System: Cross-Plugin Tool Accumulation

The total tool count across all plugins affects selection accuracy. This is confirmed by multiple GitHub issues:

- **Issue #29157**: With many MCP servers connected (Grafana, Linear, Sentry, Slack, Notion, Discord, etc.), tool definitions exhaust the subagent context budget entirely.
- **Issue #7328**: Feature request for selective enable/disable of individual tools from MCP servers, because large servers (20+ tools each) overwhelm the interface.
- **Issue #12241**: Bug report about excessive context usage warnings from MCP tools.
- **Issue #6762**: MCP tools taking up too much space in context.

Claude Code's mitigation (automatic tool search when >10% of context consumed by tool definitions) applies across all plugins. Tools from all connected MCP servers are pooled together for the purpose of this threshold.

Sources: GitHub issues [#29157](https://github.com/anthropics/claude-code/issues/29157), [#7328](https://github.com/anthropics/claude-code/issues/7328), [#12241](https://github.com/anthropics/claude-code/issues/12241), [#7336](https://github.com/anthropics/claude-code/issues/7336)

## 7. Mitigation Strategies

### 1. Tool Search / Deferred Loading (Anthropic's approach)
- Mark tools with `defer_loading: true`
- Claude searches tool catalog on-demand (regex or BM25)
- Returns 3-5 most relevant tools per query
- Reduces context by 85-95%
- Claude Code enables this automatically when tools exceed 10% of context

### 2. Tool RAG (RAG-MCP, community approach)
- Embed tool descriptions in vector store
- Retrieve semantically relevant tools per query
- Triples accuracy (13.62% to 43.13% in RAG-MCP benchmark)

### 3. Active Tool Discovery (MCP-Zero)
- Agent autonomously identifies capability gaps
- Hierarchical semantic routing: match to server, then to tool
- 98% token reduction with maintained accuracy

### 4. Progressive Disclosure (Klavis Strata)
- Agent navigates tool catalog through logical discovery steps
- +13-15% success rate improvement on benchmarks
- 83%+ accuracy on human eval

### 5. Tool Consolidation (Block pattern)
- Merge granular CRUD tools into broader workflow tools
- Reduce 30+ tools to 2-3 well-designed interfaces
- Tradeoff: more complex individual tools, fewer selection errors

## Sources Consulted

### Anthropic Official Documentation
- [Tool Search Tool - Claude API Docs](https://platform.claude.com/docs/en/agents-and-tools/tool-use/tool-search-tool)
- [Advanced Tool Use - Anthropic Engineering](https://www.anthropic.com/engineering/advanced-tool-use)
- [Tool Use Overview - Claude API Docs](https://platform.claude.com/docs/en/agents-and-tools/tool-use/overview)

### Academic Papers
- [RAG-MCP: Mitigating Prompt Bloat in LLM Tool Selection (arXiv:2505.03275)](https://arxiv.org/abs/2505.03275)
- [MCP-Zero: Active Tool Discovery (arXiv:2506.01056)](https://arxiv.org/abs/2506.01056)
- [LiveMCPBench: Can Agents Navigate an Ocean of MCP Tools? (arXiv:2508.01780)](https://arxiv.org/abs/2508.01780)
- [HumanMCPBench: Human-Like Query Dataset for MCP Tool Retrieval (arXiv:2602.23367)](https://arxiv.org/html/2602.23367)

### GitHub Issues (Claude Code)
- [#7336: Lazy Loading for MCP Servers (95% context reduction)](https://github.com/anthropics/claude-code/issues/7336)
- [#11364: Lazy-load MCP Tool Definitions](https://github.com/anthropics/claude-code/issues/11364)
- [#7328: MCP Tool Filtering](https://github.com/anthropics/claude-code/issues/7328)
- [#29157: Disable MCP Tools for Subagents](https://github.com/anthropics/claude-code/issues/29157)
- [#12241: Large MCP Tools Context Warning](https://github.com/anthropics/claude-code/issues/12241)

### MCP Protocol Discussions
- [Discussion #537: Maximum number of tools per MCP server](https://github.com/orgs/modelcontextprotocol/discussions/537)

### Developer Blogs
- [Scott Spence: Optimising MCP Server Context Usage](https://scottspence.com/posts/optimising-mcp-server-context-usage-in-claude-code)
- [Demiliani: MCP and the "Too Many Tools" Problem](https://demiliani.com/2025/09/04/model-context-protocol-and-the-too-many-tools-problem/)
- [Lunar.dev: How to Prevent MCP Tool Overload](https://www.lunar.dev/post/why-is-there-mcp-tool-overload-and-how-to-solve-it-for-your-ai-agents)
- [Block Engineering: Playbook for Designing MCP Servers](https://engineering.block.xyz/blog/blocks-playbook-for-designing-mcp-servers)
- [Datadog Engineering: Designing MCP Tools for Agents](https://www.datadoghq.com/blog/engineering/mcp-server-agent-tools/)
- [Philipp Schmid: MCP Best Practices](https://www.philschmid.de/mcp-best-practices)
- [Workato: MCP Server Design Best Practices](https://docs.workato.com/mcp/mcp-server-design.html)

### X/Twitter
- [Klavis AI: Strata launch with +13% benchmark improvement](https://x.com/Klavis_AI/status/1970140203575861611)
- [Arnav Gupta: "Too many tools saturate the context"](https://x.com/championswimmer/status/1940437170445312294)
- [Jeffrey Emanuel: "MCP tool overload is real... paradox of choice"](https://x.com/doodlestein/status/1940527120746484142)
- [Philipp Schmid: LiveMCPBench results](https://x.com/_philschmid/status/1955601309966447074)

## Source Quality Assessment

**High confidence** findings:
- The 30-50 tool threshold comes directly from Anthropic's documentation
- HumanMCPBench provides clean quantitative degradation curves with reproducible methodology
- LiveMCPBench provides real-world tool-at-scale evaluation data
- Claude Code GitHub issues provide first-hand developer experience with specific token measurements

**Medium confidence** findings:
- Platform hard limits (120 for Claude, 128 for OpenAI, 40 for Cursor) are reported by third parties but not always in official docs
- Token-per-tool estimates vary widely (200-850) depending on tool complexity

**Gap**: No Reddit discussions were found on this specific topic. The community discussion happens primarily on GitHub issues, X/Twitter, and engineering blogs.

## Open Questions

1. **Does the degradation curve differ between Claude model sizes?** The HumanMCPBench data covers only Haiku-class models. Anthropic's internal data shows Opus 4 at 49% baseline (much lower than Haiku's 88-98%), but this may reflect a different benchmark methodology rather than a direct comparison.

2. **What is the interaction between tool count and tool description quality?** Well-named, well-described tools may degrade more gracefully than ambiguously named ones, but no benchmark isolates this variable.

3. **Does tool search introduce its own failure mode?** If the search step fails to surface the correct tool, the model never gets a chance to select it. LiveMCPBench shows retrieval errors account for ~50% of all failures.

4. **How does extended thinking interact with tool selection at scale?** No data exists on whether enabling extended thinking improves tool selection accuracy with large tool sets.

## Actionable Takeaways

1. **Keep active tools under 30 per context.** This is Anthropic's documented threshold for reliable selection. Under 15 is better.

2. **Design MCP servers with 5-8 tools each.** This is the consensus across Workato, Philipp Schmid, and the broader community. Split at 15.

3. **Enable tool search / deferred loading for any setup with >10 tools.** This is Anthropic's own recommendation and is automatic in Claude Code.

4. **Name tools with service prefixes** (`github_create_issue`, not `create_issue`) to reduce ambiguity across multiple MCP servers.

5. **Consolidate where possible.** Block's pattern of collapsing 30+ tools into 2-3 well-designed interfaces is the most aggressive and effective approach.

6. **Budget 500-800 tokens per tool for context planning.** With a 200K window, that means 250-400 tools would consume the entire context. Practical ceiling is much lower because you need context for actual work.

7. **For Claude Code with multiple plugins**: the total tool count across all plugins is what matters. Claude Code's automatic tool search (triggered at >10% context consumption) mitigates this, but poorly described deferred tools may still fail at the retrieval step.
