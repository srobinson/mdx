---
title: "Watching the wire"
slug: anchor-essay
status: review
account: knowmorecontext
surface: blog
type: deep-dive
created: 2026-04-30
updated: 2026-05-04
post_date:
post_url:
campaign: transport-matters-launch
related: [pinned-anchor, readafile-deepdive]
---

# Watching the wire

I started watching what my coding agent sends over HTTPS a few weeks ago. The setup was minimal. [`mitmdump`](https://docs.mitmproxy.org/stable/) in front of the agent, certificate trust in place, one capture per session.

The first capture was a cold session start. I typed `Hi`. The first user message came back with six content blocks. The actual `Hi` was the sixth.

![User message blocks: five system-reminders precede "Hi"](images/0001-anchor-essay/user-blocks.png)

Five `<system-reminder>` blocks arrived before my message did. Session-start hook output, deferred tool references, MCP server instructions, skill descriptors, a behavioural rule block. None of it written by me, all of it injected into the user channel before the first byte I had authored. One of the five earns its keep: the deferred tool references list ~137 tool names in around 6k chars. Paired with the `ToolSearch` tool's own calling directive, that contract stands in for what would otherwise be a hundred-plus full tool schemas in the request. The other four are runtime state the harness wants the model to read as if I had typed it.

The system field on the same capture was also long, and it did not match any documented static string. Anthropic publishes pages on the segments. The [Agent SDK page on system prompts](https://code.claude.com/docs/en/agent-sdk/modifying-system-prompts) names what gets embedded in the preset. The [slash-commands page](https://code.claude.com/docs/en/slash-commands) describes how skill descriptions enter the prompt. The [MCP page](https://code.claude.com/docs/en/mcp) documents how MCP server tools surface. The composition lives in none of those pages. [Piebald-AI's extraction](https://github.com/Piebald-AI/claude-code-system-prompts) of the harness from the published npm artifact counts 110+ conditional segments composed per session by the harness programme.

Two surprises in one capture. The user channel was not just what I typed. The system field was not what the docs assembled. The agent's interface is a chat box. The system is whatever ends up in the request body.

That sent me to a question I had been avoiding. What do I actually know about how my agents work, and what have I inferred from the surface they show me?

## The four layers below the model

The conversation around agent work sits at the top of a stack. Prompt shape, retrieval quality, tool description format, context window squeeze. Real work, all on one floor.

Below it sits the harness. System message segments, tools loaded eagerly or deferred, skill discovery hooks, environment blocks, MCP descriptors. All harness output, on every turn, none of it typed by the user.

Below the harness sits context. Retrieved documents, project notes, tool results from earlier turns, working memory, system-reminders injected into the user-content stream. Loaded by the harness and packed into the request.

Below context sits transport, the bytes on the wire. Envelope, headers, schema, ordering, cache control directives. The plumbing the upper floors assume is correct.

Below transport sits the model. That layer is sealed and not the one this piece is about.

The agent's mental model has layers. The API contract that carries them is flat. A `system` field, a `messages` array, a `tools` array, headers. The conceptual layers all collapse into those flat fields by the time the bytes leave the agent process. The wire is where you see the collapse happen.

The bottom three floors are what this piece spends time in.

## The harness

Open a capture of a fresh Claude Code session and the first thing that arrives is a `system` field that runs to thousands of tokens.

Anthropic documents the segments individually. The Agent SDK page names what gets embedded in the preset: working directory, platform and OS version, current date, git status, auto-memory paths. The slash-commands page describes how skill descriptions enter the prompt and how the descriptor budget is sized at 1% of the context window with an 8,000-character fallback. The MCP page documents how server tools surface as `mcp__<server>__<tool>` entries.

[Piebald-AI's extraction](https://github.com/Piebald-AI/claude-code-system-prompts) is mechanical. It parses the published Claude Code npm artifact and emits the strings the binary will substitute. Against version 2.1.126 the count is 110+ conditional segments. Tool descriptions, subagent system prompts (Explore and Plan), and utility functions for compaction, CLAUDE.md generation, and session title generation. The `ToolSearch` directive shown later in this piece is one of these conditional segments, composed only when `ENABLE_TOOL_SEARCH` is active. The harness is a programme. Per session, it composes the system field from these segments.

A capture of the first turn (helioy/helioy-bus, claude-sonnet-4-6, cc 2.1.118) shows the system field arriving as three parts.

| Block | Cached | Contents |
|---|---|---|
| `[0]` | no | Billing header (`x-anthropic-billing-header: cc_version=...; cc_entrypoint=...`) |
| `[1]` | yes | Identity preface (`You are Claude Code, Anthropic's official CLI for Claude.`) |
| `[2]` | yes | Harness body. Working directory, tool descriptions, affordances, environment block, conditional segments. |

Three parts, two cache breakpoints on the content, one uncacheable metadata block. The billing header's presence as a system block does not appear in the published docs.

A few segments inside `[2]` deserve naming. The harness instructions block sits at the top. It carries four affordances Claude is told to accept: markdown rendering, permission-mode tool execution, system-reminder injection by the harness, automatic compaction.

Per Piebald's extraction (cc 2.1.124), the published costs of named segments:

| Segment | Kind | Tokens |
|---|---|---|
| Harness instructions | Top-level rules | 195 |
| Status line setup | Setup tool | 2,120 |
| `/security-review` | Skill | 2,521 |
| `/schedule` | Skill | 3,130 |
| Explore subagent prompt | Subagent | 575 |
| Plan mode prompt | Subagent | 715 |

The harness ships these segments before the user types anything.

Skills carry an interesting property. By default, only the description and `when_to_use` text enter the harness. The combined text is [capped at 1,536 characters per skill](https://code.claude.com/docs/en/slash-commands). Full SKILL.md content loads only on invocation. This is the cleanest case in the harness of an already-deployed lazy load. Descriptors at session start, full content on demand.

The env block is harness output. Working directory, git repo flag, platform, shell, OS version, model name, today's date. The git status is a snapshot at session start with an explicit warning that it does not refresh during the session. The env block is documented categorically across multiple pages. The wire shows the assembled set in one place.

The harness is the programme that decides what ships in the system field. The user wrote none of it. Reading it requires a proxy.

## The user channel

The user channel ships more than what the user typed.

The [Messages API](https://platform.claude.com/docs/en/api/messages) models alternating user and assistant turns. Each message carries a `role` and a `content` field. The content can be a string for simple cases, or an array of typed blocks (`text`, `image`, `document`, `tool_use`, `tool_result`). Consecutive same-role turns are merged.

A `read_file` call inside a Claude Code session unfolds across two messages. The assistant emits a `tool_use` block carrying an `id`, a `name` (`Read`), and an `input` object. The next user message carries a [`tool_result`](https://platform.claude.com/docs/en/agents-and-tools/tool-use/handle-tool-calls) block carrying the matching `tool_use_id` and the file contents. Multiple parallel tool calls return as multiple `tool_use` blocks in one assistant message; all corresponding `tool_result` blocks must come back in a single user message, and they must come first in the content array.

System-reminders are harness injection in the user-content stream. The harness prompt instructs the model directly: "User messages include a `<system-reminder>` appended by this harness. These reminders are not from the user, so treat them as an instruction to you, and do not mention them." Harness directives ride the user-content stream and reach only the model. The chat surface does not render them. The screenshot at the top of this piece is the receipt: five reminder blocks, then `Hi`.

The block content is heterogeneous. Session-start hook output, skill descriptors, MCP server instructions, behavioural rule blocks. The lack of visibility makes it possible for instructions to compound without the user noticing. On my own system, the `using-superpowers` skill was injecting twice on every cold start because two marketplaces had registered the plugin: `claude-plugins-official` (April) and `superpowers-dev` (May), both at `scope: "user"`, both active. The harness faithfully injected both. The `/context` command does surface the duplication; in the skills list, `using-superpowers: 47 tokens` appears twice. What the command does not do is calculate the token cost of the duplication, name the conflicting installs, or suggest which to remove.

## Deferral on the wire

The deferral contract has another half: the directive that teaches the model what `ToolSearch` does and how to query it. It ships as the description on the `ToolSearch` tool itself, inside the `tools` array of the request.

```
Fetches full schema definitions for deferred tools so they can be called.

Deferred tools appear by name in <system-reminder> messages. Until fetched, only the name is known — there is no parameter schema, so the tool cannot be invoked. This tool takes a query, matches it against the deferred tool list, and returns the matched tools' complete JSONSchema definitions inside a <functions> block. Once a tool's schema appears in that result, it is callable exactly like any tool defined at the top of the prompt.

Result format: each matched tool appears as one <function>{"description": "...", "name": "...", "parameters": {...}}</function> line inside the <functions> block — the same encoding as the tool list at the top of this prompt.

Query forms:
- "select:Read,Edit,Grep" — fetch these exact tools by name
- "notebook jupyter" — keyword search, up to max_results best matches
- "+slack send" — require "slack" in the name, rank by remaining terms
```

Names in the user channel, calling instructions on the tool itself. With [`ENABLE_TOOL_SEARCH`](https://code.claude.com/docs/en/agent-sdk/tool-search) active, a deferred tool call unfolds across two round-trips before the assistant can respond. The assistant first emits a `ToolSearch` to resolve the descriptor:

```json
{
  "type": "tool_use",
  "id": "toolu_011UQT9BWgN3r3XEmCujh7xD",
  "name": "ToolSearch",
  "input": { "query": "select:mcp__plugin_helioy-tools_cm__cx_browse", "max_results": 1 }
}
```

The user turn returns not content but a `tool_reference`, the resolved descriptor injected inline:

```
{'type': 'tool_reference', 'tool_name': 'mcp__plugin_helioy-tools_cm__cx_browse'}
```

With the schema now loaded, the assistant emits the real call:

```json
{
  "type": "tool_use",
  "id": "toolu_01JFHncdmxUzEXo2NhMxJ9uw",
  "name": "mcp__plugin_helioy-tools_cm__cx_browse",
  "input": { "limit": 3 }
}
```

The tool result returns a structured payload:

```json
{
  "advisory": "no scope specified, using scope='cwd_inferred' to infer the local scope. run `cm stats` to list all scopes.",
  "entries": [
    {
      "age": "19h",
      "id": "019deace-dcb4-7ea3-a574-3a56c6893aa7",
      "snippet": "Branch status check: `codex/list-agents-cwd-basename` committed tip is merged into origin/main at a6fab7e, but there are uncommitted local changes in five files that are not merged.",
      "tags": [
        "conversation",
        "summary"
      ],
      "title": "Session summary"
    },
    {
      "age": "19h",
      "id": "019deace-dcb3-7e83-b3e9-462bc1f18fd0",
      "snippet": "did we merge this branch? --- Checked current branch `codex/list-agents-cwd-basename` after `git fetch --all --prune`. `HEAD`, `main`, and `origin/main` all resolve to `a6fab7e`, and both...",
      "tags": [
        "conversation"
      ],
      "title": "did we merge this branch?"
    }
  ],
  "has_more": true,
  "header": {
    "created_by": "agent:claude-code",
    "kind": "observation",
    "kinds_histogram": {
      "observation": 2
    },
    "returned": 2,
    "scope": "global/project:helioy/repo:helioy-bus",
    "sort_used": "updated_at desc",
    "tags_histogram": {
      "conversation": 2,
      "summary": 1
    },
    "total": 41
  },
  "next_cursor": "eyJzb3J0IjoicmVjZW50IiwidHMiOiIyMDI2LTA1LTAyVDIyOjI4OjM4LjcwN1oiLCJpZCI6IjAxOWRlYWNlLWRjYjMtN2U4My1iM2U5LTQ2MmJjMWYxOGZkMCJ9",
  "resolution": {
    "candidates": [
      {
        "matched": [
          "repo",
          "project_parent",
          "specificity"
        ],
        "scope": "global/project:helioy/repo:helioy-bus",
        "score": 330
      },
      {
        "matched": [
          "project_parent",
          "project"
        ],
        "scope": "global/project:helioy",
        "score": 110
      },
      {
        "matched": [
          "fallback"
        ],
        "scope": "global",
        "score": 0
      }
    ],
    "confidence": "high",
    "requested_scope": "cwd_inferred",
    "resolved_scope": "global/project:helioy/repo:helioy-bus",
    "scope_mode": "resolved",
    "signals": [
      "cwd basename matched repo scope segment: helioy-bus",
      "cwd parent basename matched project scope segment: helioy"
    ]
  }
}
```

The model received a full briefing on the repo's recent session history before composing a reply to "Hi." It knew the branch, the merge state, the last conversation. No user instruction initiated any of this. The `resolution.candidates` block shows how the page resolved: three candidate scopes scored by match specificity (`repo:helioy-bus` at 330, `project:helioy` at 110, `global` fallback at 0), the highest-scoring one chosen. The page returned 2 entries out of 41 in scope, sorted by `updated_at desc`, with a `next_cursor` for the rest.

The assistant text response followed: "Hi. The last session implemented `list_agents` cwd_basename filtering on this branch, and there were uncommitted local changes in five files. What are you working on today?"

Two round-trips to accomplish what eager loading handles in one. The cost is latency. The gain is that the full tool descriptor surface stayed off the wire.

Working memory accumulates as turns. The Messages API has no separate state. Whatever the agent wants the model to remember has to ride in the request, in the messages array, on every subsequent turn.

## The ENABLE_TOOL_SEARCH measurement

There is one knob in this stack with quantified before-and-after numbers.

[`ENABLE_TOOL_SEARCH`](https://code.claude.com/docs/en/agent-sdk/tool-search) is documented on the Claude Code Agent SDK page. The valid values: unset (default; all tool definitions load eagerly on every turn), `true`, `auto` (loads everything if tool definitions are under 10% of the context window; defers them otherwise), `auto:N` (custom percentage threshold), `false` (loads all on every turn).

The mechanism is documented [at the API layer too](https://platform.claude.com/docs/en/agents-and-tools/tool-use/tool-search-tool). Tools marked `defer_loading: true` are not included in the system-prompt prefix. When the model discovers a deferred tool through tool search, the tool definition is appended inline as a `tool_reference` block in the conversation. Search returns 3 to 5 most relevant tools per query. Two server-side variants are documented: regex (`tool_search_tool_regex_20251119`) and BM25 (`tool_search_tool_bm25_20251119`). The cached prefix is preserved.

Anthropic publishes numbers for the cost.

| Frame | Without tool search | With tool search | Source |
|---|---|---|---|
| MCP definitions for a GitHub + Slack + Sentry + Grafana + Splunk loadout | ~55,000 tokens | reduced by 85%+ | [tool search docs](https://platform.claude.com/docs/en/agents-and-tools/tool-use/tool-search-tool) |
| Working context remaining on the same loadout | 122,800 tokens | 191,300 tokens | [advanced tool use post](https://www.anthropic.com/engineering/advanced-tool-use) |

Three independent practitioner measurements posted as GitHub issues against `anthropics/claude-code` triangulate this against real Claude Code installations. Percentages reference the 200,000-token context window.

| Issue | Loadout | MCP definition cost | With `ENABLE_TOOL_SEARCH=true` |
|---|---|---|---|
| [#18298](https://github.com/anthropics/claude-code/issues/18298) | 7 MCP servers | 28,100 tokens (14.1% of context) | reported drop |
| [#18397](https://github.com/anthropics/claude-code/issues/18397) | multi-server | 70,500 tokens (35.3% of context) | drops to ~0 on first turn |
| [#19890](https://github.com/anthropics/claude-code/issues/19890) | 40+ MCP tools | 49,500 tokens (24.8% of context) | expected drop to ~0 |

I ran the same measurement on my own setup. Same session (helioy/helioy-bus, claude-sonnet-4-6), same first turn, same MCP loadout, three cold starts.

| Configuration | Input tokens | Saved vs default | Tools on the wire |
|---|---|---|---|
| default (unset) | 67,504 | n/a | 149 |
| `ENABLE_TOOL_SEARCH=true` | 28,073 | 39,431 | 8 |
| `ENABLE_TOOL_SEARCH=auto:0` | 27,991 | 39,513 | 8 |

39,431 tokens off a single first turn. The four-figure floor in the published examples understates a real-world Helioy loadout by an order of magnitude.

That saving stacks two policies. `ENABLE_TOOL_SEARCH` defers user-installed tools, the documented behaviour. It also triggers an internal policy on Claude Code's own built-ins.

| | Default | With `ENABLE_TOOL_SEARCH` active |
|---|---|---|
| Built-ins eagerly loaded | 29 | 8 |
| Schema bytes shipped | 79,420 chars | 36,972 chars |
| Hot set | all 29 | Read, Edit, Write, Bash, Agent, Skill, ScheduleWakeup, ToolSearch |

Seven of the eight carry over from the default loadout. `ToolSearch` is added when deferral activates. The other 22 default tools become deferrable in Anthropic's own judgment: the Task* to-do suite the runtime uses for progress tracking, Monitor, the Web* family, the Notebook* family, the Cron* family, plan-mode and worktree controls, PushNotification, RemoteTrigger, MCP resource tools, and AskUserQuestion.

The seven that stay hot read as essential: file ops, shell, subagent dispatch, skill activation, the deferral mechanism itself. `ScheduleWakeup` is the surprise. Its presence in the hot set says scheduled work has joined the operating floor.

The default loadout ships all 29 anyway.

`auto:0` sets the deferral threshold at 0%: defer always, regardless of tool surface size. The result is identical to `true` in tools loaded. The 82-token difference between the two captures is the startup hook success message, absent in the `auto:0` run.

A second observation worth making about this knob. [Release v2.1.7](https://github.com/anthropics/claude-code/releases/tag/v2.1.7) made auto mode the shipped default: "Enabled MCP tool search auto mode by default for all users. When MCP tool descriptions exceed 10% of the context window, they are automatically deferred." The three issues above all report that auto mode does not consistently fire above the documented threshold. Explicit `ENABLE_TOOL_SEARCH=true` reliably restores the documented behavior. The default that ships and the default that works can diverge.

If one knob saves five figures of tokens per turn, what else is shipping by default?

## Token pollution

Tokens that ride along on every turn without earning their place consume the context window the user wanted for the work itself.

Concrete numbers exist:

- 50 tools = 10,000 to 20,000 tokens for a moderate MCP loadout (tool search documentation).
- GitHub + Slack + Sentry + Grafana + Splunk = ~55,000 tokens (Anthropic's published example).
- Real-world MCP loadouts captured against Claude Code = 28,000 to 70,000 tokens (the three practitioner issues cited above).
- The harness itself before any MCP = thousands of tokens of segment text (Piebald's extraction).

[Caching](https://platform.claude.com/docs/en/build-with-claude/prompt-caching) offsets the per-turn cost. Anthropic's [engineering post on Claude Code's caching strategy](https://claude.com/blog/lessons-from-building-claude-code-prompt-caching-is-everything) describes a tiered layout. Static system prompt and tools are globally cached; CLAUDE.md is cached within a project; session context is cached within a session; conversation messages cache per session. The cache control mechanism supports up to four breakpoints per request, with TTLs of 5 minutes (default) or 1 hour. 5-minute writes cost 1.25x base input tokens, 1-hour writes 2x, cache reads 0.1x. With a 90% cache hit rate, a $100 session falls to about $19.

Four turns of one session (helioy/helioy-bus, `ENABLE_TOOL_SEARCH=auto:0`, no hooks), prompt: `Hi`.

| Turn | Input total | Cache read | Fresh tokens | What the cache shows |
|---|---|---|---|---|
| 1 | 27,991 | 9,599 | 12,125 | Cross-session warm cache hits the static prefix. `ToolSearch` resolves `cx_browse` and `am_query`; the two new descriptors arrive as fresh tokens. |
| 2 | 28,369 | 15,866 | 195 | The turn-1 reminders and tool descriptors now cache. Fresh input collapses to 195. Both tools fire. |
| 3 | 29,252 | 15,866 | 1,078 | `cx_browse` returns; `am_query` errors. Cache read holds steady because nothing committed between turn 2 and turn 3. |
| 4 | 31,218 | 28,281 | 2,739 | Cache read jumps as turn-2 and turn-3 conversation content commits to cache. `am_query` retries successfully. The assistant emits the greeting. |

The pattern: cache read climbs as conversation accumulates, fresh tokens collapse once descriptors and reminders cache, and input total stays flat near 28k-31k because deferral keeps the tool surface small. The 67,504-token default ships the same prefix on every turn whether the user typed `Hi` or a paragraph.

The am_query error on turn 3 is the lazy-load failure mode. The descriptor resolved correctly through ToolSearch, but the tool call itself failed at runtime. The model retried without user input and recovered on turn 4.

Four round-trips to answer "Hi". The token cost on each turn stayed near 28,000 to 31,000, flat relative to the 67,504 default, because deferral kept the tool surface at 10 descriptors rather than 149. The 10 is the 8 hot built-ins plus the 2 user-installed tools (`cx_browse` and `am_query`) that `ToolSearch` resolved during this session. The latency trade is real and measurable.

Cache offsets cost. It does not eliminate composition. Whatever ships in the prefix has to ship the first time. Anthropic's own engineering account names the constraint: "Because tools are part of the cached prefix, adding or removing a tool invalidates the cache for the entire conversation." Cache breaks are treated as incidents. The first-turn cost is the floor. Every operation that mutates the prefix pays the floor again.

Token pollution is one consequence of composition the user does not author. Control is the other.

## Control

To change agent behaviour, you have to change what it sends. The wire is where it sends from. The vendor's default runs unless somebody on this side of the wire intervenes.

The skills mechanism is one example of intervention already in production. Skill descriptions enter the harness; full SKILL.md content loads only on invocation. The lazy-load pattern is documented and shipped. The harness already does this for one segment.

The tools mechanism is a second. `ENABLE_TOOL_SEARCH` defers tool definitions out of the system-prompt prefix into inline `tool_reference` blocks expanded server-side. The shape is the same: a discovery surface in the user channel (names in reminders), a calling directive on the tool itself (the `ToolSearch` description), and the full schema returned on demand. Two of the obvious lazy-load mechanisms have shipped.

A small experiment on a third class of intervention: session-start hooks. Same loadout, same first turn. Hook active versus hook removed.

| | Hook active | Hook removed |
|---|---|---|
| Request tokens | 67,504 | 67,422 |
| User blocks | 6 | 5 |
| Missing block | none | `SessionStart:startup hook success` |
| Response shape | silent → `cx_browse` only | "Starting session checks per memory instructions." then `cx_browse` and `am_query` in parallel |

The token delta is 82. The behavioural delta is larger. With the hook, the model called one tool, silently, with the exact parameters the hook specified. Without it, the model produced a text preamble, then dispatched two memory tools in parallel: `cx_browse` and `am_query`. It drew its own inference from the `EXTREMELY_IMPORTANT` block that was still present in both sessions.

When asked why it called am_query, the model identified two separate sources. The `helioy-tools_am` MCP server instruction (one line in the MCP server instructions block) says "Query geometric memory at the START of every session with am_query." The cx_browse call came from a different source: a project-specific feedback memory entry, `feedback_cx_browse_on_start.md`, told the model to call cx_browse at session start in this repo.

Two instructions from two injection layers, both firing simultaneously, neither aware of the other.

A third experiment clarifies the weight of each. With `autoMemoryEnabled: false` set in `.claude/settings.json`, the file-memory entries do not inject. The harness body shrinks substantially, the auto-memory configuration removed. The AM MCP server instruction remains in its block unchanged. The model responded to "Hi" with "Hi! What are you working on?" in one turn, zero tool calls.

The AM instruction alone was not enough. The model read "Query geometric memory at the START of every session" and skipped it. The model treats MCP server instructions as advisory text and weighs them against all other context. Combined with a file-memory entry reinforcing the same behaviour, the instruction fired. Alone, it did not.

The hook collapses this entire weighting problem into a single authoritative instruction. The 82 tokens it saves are incidental. With the hook, the model called one tool, silently, precisely. Without it, two competing instructions from different injection layers both fired. One routed correctly. One returned noise from unrelated projects. Strip the file-memory entries and the MCP instruction is no longer sufficient to drive any call at all.

A fourth target is the env block, the working-memory block, and the harness instructions themselves. The Agent SDK ships an `excludeDynamicSections` option that moves per-session context out of the system field into the first user message, holding the prefix stable for cross-session cache reuse. The default behavior remains the dynamic preset. [Issue #44536](https://github.com/anthropics/claude-code/issues/44536) on `anthropics/claude-code` is filed under the title "Lazy context loading: extend the ToolSearch pattern to all context components."

The cost of composition is paid by the user, on every turn, in tokens that consume the window the user wanted for the work itself. Knowing what is on the wire is what makes intervention possible. Every other lever sits downstream of that.

The proxy can do more than watch. I have been intercepting requests before they hit the wire and stripping the system prompts and system-reminder bloat. One exchange collapses from 124,200 tokens to 57,300.

![Pipeline panel: 124.2K → 57.3K, -54%, three toggle dimensions](images/0001-anchor-essay/strip-system-prompt-and-reminders.png)

I publish the teardowns at [knowmorecontext.substack.com](https://knowmorecontext.substack.com).

Two vendors, two deployment contracts. Anthropic introduced the Tool Search API primitive in November 2025. The type names embed the date: `tool_search_tool_bm25_20251119`. [Codex issue #9266](https://github.com/openai/codex/issues/9266) (January 15, 2026) proposed an equivalent for OpenAI's CLI and cited the Anthropic spec by URL as the reference implementation. [PR #17854](https://github.com/openai/codex/pull/17854) landed it stable on April 16, 2026 and flipped the default on. Codex manages this via a TOML feature flag (`codex features enable tool_search`). No `ENABLE_TOOL_SEARCH` env var exists in [Codex's config surface](https://developers.openai.com/codex/cli/features). The deployment contracts diverged. Claude Code gates deferral behind explicit opt-in. Codex ships with it on and requires deliberate opt-out.

If you enjoyed this, let me know what you want torn down next. Reply on Substack or find me at @KnowMoreContext on X.

Token matters.
