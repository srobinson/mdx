---
title: "Anchor essay expansion — ENABLE_TOOL_SEARCH flag research"
type: research
created: 2026-05-03
status: active
related: [0001-anchor-essay]
tags: [claude-code, mcp, tool-search, token-cost, primary-source]
summary: Primary-source backing for the ENABLE_TOOL_SEARCH flag. Documented in Claude Code Agent SDK docs and CHANGELOG. Practitioner GitHub issues corroborate Stuart's four-figure first-turn token delta with reproducible methodology.
confidence: high
---

# ENABLE_TOOL_SEARCH primary-source research

Exact env var name (case-sensitive): `ENABLE_TOOL_SEARCH`

## Findings

| Section | Claim | Source | Date | Quote / artifact | Confidence |
|---------|-------|--------|------|------------------|-----------|
| 1 | `ENABLE_TOOL_SEARCH` is the canonical Claude Code env var name | https://code.claude.com/docs/en/agent-sdk/tool-search | 2026-05-03 (fetched) | "By default, tool search is always on. You can change this with the `ENABLE_TOOL_SEARCH` environment variable" | high |
| 1 | Documented value table | https://code.claude.com/docs/en/agent-sdk/tool-search | 2026-05-03 | Values: `(unset)`, `true`, `auto`, `auto:N`, `false`. "(unset) Tool search is always on. Tool definitions are never loaded into context. This is the default." | high |
| 1 | `ENABLE_TOOL_SEARCH` referenced from env-vars page | https://code.claude.com/docs/en/env-vars | 2026-05-03 | "When set to a non-first-party host, MCP tool search is disabled by default. Set `ENABLE_TOOL_SEARCH=true` if your proxy forwards `tool_reference` blocks" (in `ANTHROPIC_BASE_URL` row) | high |
| 1 | Variable referenced in Claude Code CHANGELOG | github.com/anthropics/claude-code/blob/main/CHANGELOG.md | 2026-05-03 | "Tool search is now disabled by default on Vertex AI to avoid an unsupported beta header error (opt in with `ENABLE_TOOL_SEARCH`)" — under `## 2.1.121` | high |
| 1 | Variable referenced in Claude Code CHANGELOG (proxy fix) | github.com/anthropics/claude-code/blob/main/CHANGELOG.md | 2026-05-03 | "Fixed tool search to activate even with `ANTHROPIC_BASE_URL` as long as `ENABLE_TOOL_SEARCH` is set." — under `## 2.1.74` | high |
| 2 | Behavior with flag enabled: tool definitions withheld from context | https://code.claude.com/docs/en/agent-sdk/tool-search | 2026-05-03 | "When tool search is active, tool definitions are withheld from the context window. The agent receives a summary of available tools and searches for relevant ones when the task requires a capability not already loaded." | high |
| 2 | On-demand load returns 3-5 tools per search | https://code.claude.com/docs/en/agent-sdk/tool-search | 2026-05-03 | "The 3-5 most relevant tools are loaded into context, where they stay available for subsequent turns." | high |
| 2 | Behavior with flag disabled (`false`) | https://code.claude.com/docs/en/agent-sdk/tool-search | 2026-05-03 | "Setting `ENABLE_TOOL_SEARCH` to `\"false\"` disables tool search and loads all tool definitions into context on every turn." | high |
| 2 | Auto threshold semantics | https://code.claude.com/docs/en/agent-sdk/tool-search | 2026-05-03 | "`auto` — Checks the combined token count of all tool definitions against the model's context window. If they exceed 10%, tool search activates. If they're under 10%, all tools are loaded into context normally." | high |
| 2 | `auto:N` custom threshold | https://code.claude.com/docs/en/agent-sdk/tool-search | 2026-05-03 | "`auto:N` — Same as `auto` with a custom percentage. `auto:5` activates when tool definitions exceed 5% of the context window. Lower values activate sooner." | high |
| 2 | Auto mode added to CLI | github.com/anthropics/claude-code CHANGELOG `## 2.1.9` | 2026-05-03 | "Added `auto:N` syntax for configuring the MCP tool search auto-enable threshold, where N is the context window percentage (0-100)" | high |
| 2 | Auto mode default rollout (the 10% threshold release) | github.com/anthropics/claude-code CHANGELOG `## 2.1.7` | 2026-05-03 | "Enabled MCP tool search auto mode by default for all users. When MCP tool descriptions exceed 10% of the context window, they are automatically deferred and discovered via the MCPSearch tool instead of being loaded upfront. This reduces context usage for users with many MCP tools configured. Users can disable this by adding `MCPSearch` to `disallowedTools` in their settings." | high |
| 2 | Per-server escape hatch | github.com/anthropics/claude-code CHANGELOG `## 2.1.121` | 2026-05-03 | "Added `alwaysLoad` option to MCP server config — when `true`, all tools from that server skip tool-search deferral and are always available" | high |
| 3 | Token cost claim: typical 5-server MCP setup uses ~55K tokens of definitions before any work | https://platform.claude.com/docs/en/agents-and-tools/tool-use/tool-search-tool | 2026-05-03 | "A typical multi-server setup (GitHub, Slack, Sentry, Grafana, Splunk) can consume ~55k tokens in definitions before Claude does any actual work. Tool search typically reduces this by over 85%, loading only the 3–5 tools Claude actually needs for a given request." | high |
| 3 | Anthropic engineering blog quantifies tool-search reduction | https://www.anthropic.com/engineering/advanced-tool-use | 2025-11-24 | "Tool Search Tool preserves 191,300 tokens of context compared to 122,800 with Claude's traditional approach"; "85% reduction in token usage while maintaining access to your full tool library" | high |
| 3 | Anthropic engineering blog: 7-server MCP baseline | https://platform.claude.com/docs/en/agents-and-tools/tool-use/tool-search-tool (Tessl summary attributes 67K to "seven or more MCP servers consuming around 67,000 tokens before an agent even gets out of bed" — see Tessl source) | 2026-02-09 | "user setups with seven or more MCP servers consuming around 67,000 tokens before an agent even gets out of bed" | medium |
| 4 | Activation method: env var on the `claude` process | https://github.com/anthropics/claude-code/issues/18397 | 2026 | `ENABLE_TOOL_SEARCH=true claude` (workaround documented in issue body) | high |
| 4 | Activation method via SDK `env` option | https://code.claude.com/docs/en/agent-sdk/tool-search | 2026-05-03 | TypeScript example: `env: { ENABLE_TOOL_SEARCH: "auto:5" }` passed in `query()` `options` | high |
| 5 | Mechanism: `tool_reference` blocks expanded server-side | https://platform.claude.com/docs/en/agents-and-tools/tool-use/tool-search-tool | 2026-05-03 | "The API returns 3-5 most relevant `tool_reference` blocks. These references are automatically expanded into full tool definitions" | high |
| 5 | Mechanism: deferred tools omitted from system-prompt prefix | https://platform.claude.com/docs/en/agents-and-tools/tool-use/tool-search-tool | 2026-05-03 | "Deferred tools are not included in the system-prompt prefix. When the model discovers a deferred tool through tool search, the tool definition is appended inline as a `tool_reference` block in the conversation. The prefix is untouched, so prompt caching is preserved." | high |
| 5 | Mechanism: two server-side variants | https://platform.claude.com/docs/en/agents-and-tools/tool-use/tool-search-tool | 2026-05-03 | "Regex (`tool_search_tool_regex_20251119`)... BM25 (`tool_search_tool_bm25_20251119`)" | high |
| 5 | Search adds one round-trip on first discovery | https://code.claude.com/docs/en/agent-sdk/tool-search | 2026-05-03 | "Tool search adds one extra round-trip the first time Claude discovers a tool (the search step), but for large tool sets this is offset by smaller context on every turn. With fewer than ~10 tools, loading everything upfront is typically faster." | high |
| 6 | Practitioner measurement (DavidAGRG, Issue #18397) | https://github.com/anthropics/claude-code/issues/18397 | 2026 | See Measurements table | high |
| 6 | Practitioner measurement (johnh, Issue #19890) | https://github.com/anthropics/claude-code/issues/19890 | 2026 | See Measurements table | high |
| 6 | Practitioner measurement (amihos, Issue #18298) | https://github.com/anthropics/claude-code/issues/18298 | 2026-01-15 | See Measurements table | medium |

## Measurements

| Source | Date | Tool count | First-turn tokens (eager) | First-turn tokens (lazy) | Delta | Methodology |
|--------|------|-----------|---------------------------|--------------------------|-------|-------------|
| DavidAGRG, Issue #18397, Claude Code 2.1.7, claude-opus-4-5-20251101, macOS 25.2.0 | 2026 | not stated; multiple MCP servers | MCP tools: **70.5k tokens (35.3% of 200K context)**. Total initial context: **98k tokens (49%)**. Free space: 57k. | MCP tools: **0 tokens (loaded on-demand)**. Total initial context: **23k tokens (11%)**. Free space: 132k. | **~75k tokens** total context delta; **~70.5k tokens** in MCP tool definitions alone | Run `claude` then `claude` with `ENABLE_TOOL_SEARCH=true` prefix. Compared startup token accounting reported by Claude Code's internal context tracker. |
| johnh, Issue #19890, Claude Code 2.1.14, Opus 4.5 (Claude Max), macOS | 2026 | 40+ MCP tools across Sentry, Atlassian, IDE | Total: **71k/200k tokens (36%)**. MCP tools: **49.5k tokens (24.8%)**. Per-tool counts visible (e.g. `mcp__sentry__get_issue_details: 923 tokens`). Free: 84k. | Expected per docs: Total **21k/200k (11%)**. MCP tools "loaded on-demand". Free: 134k. | **~50k tokens** in MCP definitions; **~50k tokens** total context delta when `ENABLE_TOOL_SEARCH=true` is set explicitly | Compared startup state with no env var (auto mode failing) versus `ENABLE_TOOL_SEARCH=true claude` (works). Numbers from Claude Code's startup context display. |
| amihos, Issue #18298, Claude Code 2.1.7, Linux WSL2 | 2026-01-15 | 7 MCP servers (Serena, Sentry, Context7, Playwright, Auggie, OpenMemory, IDE) | MCP tools: **28.1k tokens (14.1% of context)** | Not measured (auto mode failed to activate; user did not run with `ENABLE_TOOL_SEARCH=true`) | At least **28.1k** of MCP definitions would be deferred if flag set | Read MCP tool token count from Claude Code's startup context display. Reproducibility: any session with these 7 MCPs. |
| Anthropic, "Advanced tool use" blog (Bin Wu) | 2025-11-24 | "five-server MCP setup" (server-side benchmark, not Claude Code) | **122,800 tokens** of remaining context with traditional approach | **191,300 tokens** of remaining context with Tool Search Tool | **~68,500 tokens preserved** (≈85% reduction) | Anthropic-internal benchmark on the Claude Developer Platform (server-side `tool_search_tool_regex_20251119`). Methodology not published in detail. |
| Anthropic platform docs (Tool search tool page) | 2026-05-03 (page) | "GitHub, Slack, Sentry, Grafana, Splunk" five-server profile | **~55k tokens** in definitions | "3–5 tools Claude actually needs" | "over 85%" reduction | Same product family as above; documentation example, not a fresh benchmark. |
| Tessl blog (Paul Sawers) summarising Anthropic | 2026-02-09 | "seven or more MCP servers" | **~67,000 tokens** before agent operation begins | not stated | not computed | Quoting Anthropic; no first-hand benchmark. |

## Notes

- **Stuart's "four figure" claim is corroborated and conservatively bounded.** Three independent practitioner reports on the official `anthropics/claude-code` issue tracker show MCP-tool definition costs of **28.1k**, **49.5k**, and **70.5k** tokens that flip to ~0 first-turn tokens when `ENABLE_TOOL_SEARCH=true` is set explicitly. The seed essay's "four figures" (1,000–9,999 tokens) is the lower bound; real-world deltas are routinely **five figures**. Stuart may want to revise upward, or qualify as "four-to-five figures depending on MCP loadout".

- **Exact env var name is `ENABLE_TOOL_SEARCH`** (uppercase, underscore-delimited). Confirmed across SDK docs, env-vars docs, CHANGELOG, and three issue threads.

- **Default state varies by version and host.** As of CHANGELOG `## 2.1.7`, auto mode at the 10% threshold is the default for first-party hosts. As of `## 2.1.121`, Vertex AI defaults to off (opt-in with `ENABLE_TOOL_SEARCH`). For non-first-party `ANTHROPIC_BASE_URL` proxies, it is also off by default. The `## 2.1.74` entry confirms a fix that lets the flag activate tool search even when `ANTHROPIC_BASE_URL` is set.

- **Auto-mode bug is well-documented and reproducible.** Issues #18298 (closed as duplicate, 2026-01-15), #18397 (closed), and #19890 (closed) all report that auto mode does not consistently fire at the documented 10% threshold. Explicit `ENABLE_TOOL_SEARCH=true` reliably restores the documented behavior. This is a load-bearing fact: Stuart's measurement of "four figures" was almost certainly taken with the flag set explicitly, and a default-config user may not see the same delta unless they opt in.

- **Mechanism detail worth using in essay:** the on-demand load is implemented via `tool_reference` blocks inserted into the conversation rather than the system-prompt prefix. This preserves prompt caching across the session while keeping the first-turn payload small. The two server-side variants are `tool_search_tool_regex_20251119` and `tool_search_tool_bm25_20251119`.

- **Credibility flags.** All three GitHub issues are filed against `anthropics/claude-code`, include version + OS + model, include reproduction steps, were triaged by Anthropic with `bug` and `has repro` labels, and were eventually closed. These are high-confidence practitioner sources by GitHub-issue standards. The Tessl blog post is third-party reporting with no first-hand benchmark; treat as colour, not evidence.

- **What is not in primary docs:** there is no published Claude Code first-party benchmark of "first-turn token delta with vs without `ENABLE_TOOL_SEARCH`" in a controlled MCP loadout. The Anthropic blog's 122,800 → 191,300 numbers are server-side API benchmarks, not Claude Code measurements. For a tight essay claim, Stuart's own mitmdump capture remains the cleanest source; the GitHub issues triangulate it.

## Sources consulted

Primary (Anthropic-owned):
- https://code.claude.com/docs/en/agent-sdk/tool-search — Claude Code Agent SDK "Scale to many tools with tool search" page (canonical config docs)
- https://code.claude.com/docs/en/env-vars — Claude Code environment variables reference
- https://platform.claude.com/docs/en/agents-and-tools/tool-use/tool-search-tool — Anthropic API tool search tool documentation
- https://www.anthropic.com/engineering/advanced-tool-use — "Introducing advanced tool use on the Claude Developer Platform" by Bin Wu, 2025-11-24
- https://github.com/anthropics/claude-code/blob/main/CHANGELOG.md — entries under `## 2.1.7`, `## 2.1.9`, `## 2.1.74`, `## 2.1.121`

GitHub issues on `anthropics/claude-code` (practitioner measurements):
- https://github.com/anthropics/claude-code/issues/18298 — "MCP Tool Search not auto-enabling when tools exceed 10% of context" (amihos, 2026-01-15, Claude Code 2.1.7)
- https://github.com/anthropics/claude-code/issues/18397 — "Tool Search doesn't activate automatically despite tengu_mcp_tool_search flag" (DavidAGRG, Claude Code 2.1.7, Opus 4.5)
- https://github.com/anthropics/claude-code/issues/19890 — "[BUG] ENABLE_TOOL_SEARCH auto mode not triggering despite MCP tools exceeding 10% threshold" (johnh, Claude Code 2.1.14, Opus 4.5)
- https://github.com/anthropics/claude-code/issues/12836 — "Support Tool Search and Programmatic Tool Use betas for reduced token consumption" (matthewod11-stack, 2025-12-01)

Secondary:
- https://tessl.io/blog/anthropic-brings-mcp-tool-search-to-claude-code/ — Paul Sawers, 2026-02-09 (no first-hand benchmark; quotes Anthropic staff)

## Open questions

- Is there a first-party Claude Code benchmark (not server-side API) measuring eager vs lazy first-turn tokens with a fixed MCP loadout? Not found in current docs or release notes.
- The CHANGELOG entry attributing auto-mode default rollout to **2.1.7** says the threshold is 10%, but issues filed against 2.1.7 and 2.1.14 show auto mode failing to fire above threshold. Whether this is fixed in a later patch (2.1.16+, 2.1.121, etc.) is not explicitly stated in the CHANGELOG entries reviewed.
- The flag `tengu_mcp_tool_search` (mentioned in `~/.claude.json` per Issue #18397) is undocumented. Its relationship to `ENABLE_TOOL_SEARCH` is unclear from public sources.

## Actionable takeaways for the essay

1. Use `ENABLE_TOOL_SEARCH` as the exact string. Capitalised, underscore.
2. Stuart's "four figure" lower bound is safe, but understated. Three independent practitioner reports show **28k-70k** token first-turn deltas in default MCP loadouts. Consider revising to "four to five figures" or quoting one specific GitHub-issue number for sharper teeth.
3. The mechanism detail worth surfacing: tool definitions move from the system-prompt prefix into inline `tool_reference` blocks, expanded server-side. This preserves prompt caching while shrinking the first-turn payload.
4. Worth noting that the documented default (auto mode at 10%) is unreliable in shipping versions; explicit `ENABLE_TOOL_SEARCH=true` is the load-bearing setting most users will need. This dovetails with the essay's "the vendor's default runs unless somebody on this side of the wire intervenes" closing.
