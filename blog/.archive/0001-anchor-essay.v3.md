---
title: "Watching the wire"
slug: anchor-essay
status: review
account: knowmorecontext
surface: blog
type: deep-dive
created: 2026-04-30
updated: 2026-05-03
post_date:
post_url:
campaign: transport-matters-launch
related: [pinned-anchor, readafile-deepdive]
---

# Watching the wire

A few weeks ago I started watching what my coding agent sends over HTTPS when I asked it to read a file. I expected a small payload. The system message, the user turn, a tool call. What I found was longer. Several segments of it were not in the docs I had read.

The setup was unexceptional. mitmdump in front of the agent, certificate trust in place, one capture per session. Anthropic does document most of these segments. The Claude Code Agent SDK page on modifying system prompts names what gets embedded in the preset. The slash-commands page describes how skill descriptions enter the prompt. The MCP page documents how MCP server tools surface. The composition lives in none of those pages. Reading them in isolation does not show what arrives on the wire.

The first capture was a cold session start. I typed "Hi". The first user message came back with seven content blocks. The actual "Hi" was the seventh.

Block [1] was the one that stopped me: the full text of the `superpowers:using-superpowers` skill, 11,852 characters, appearing twice in the same `<system-reminder>` tag. Not a bug. The plugin was installed from two separate marketplaces — `claude-plugins-official` (April) and `superpowers-dev` (May), both registered as `scope: "user"`, both active. The harness faithfully injected both. 23,704 characters of duplicate instructions on every cold start.

The `/context` command does surface this. In the skills list, `using-superpowers: 47 tokens` appears twice. The signal is visible if you scan for it. What the command does not do is calculate the token cost of the duplication, name the conflicting installs, or suggest which to remove.

The larger finding was the split. Static content arrived in the system field as cached blocks. Dynamic content arrived in the user message stream as system-reminders, injected before "Hi": session hooks, deferred tool references, MCP server instructions, skill descriptors, CLAUDE.md, project memory. The system field the docs describe is half the picture. The user message carries the rest.

That first surprise sent me back to a question I had been avoiding. What do I actually know about how my agents work, and what have I inferred from the surface they show me? The agent's interface is a chat box. The system is whatever ends up in the request body.

## The four layers below the model

The conversation around agent work sits at the top of a stack. Prompt shape, retrieval quality, tool description format, context window squeeze. Real work, all on one floor.

Below it sits the harness. System message segments, tools loaded eagerly or deferred, skill discovery hooks, environment blocks, MCP descriptors. All harness output, on every turn, none of it typed by the user.

Below the harness sits context. Retrieved documents, project notes, tool results from earlier turns, working memory. Loaded by the harness and packed into the request.

Below context sits transport, the bytes on the wire. Envelope, headers, schema, ordering, cache control directives. The plumbing the upper floors assume is correct.

Below transport sits the model. That layer is sealed and not the one this essay is about.

Four conceptual layers below the model, in order from the surface down. They live in the agent's architecture. The API contract that carries them is flat. A `system` field, a `messages` array, a `tools` array, headers. The conceptual layers I just named all collapse into those flat fields by the time the bytes leave the agent process. The wire is where you see the collapse happen.

A note on transport. I am using the word for two things that ride together on a single capture. The API contract is one. What fields exist, what semantics they carry, what `cache_control` means. The encoding is the other. HTTPS framing, JSON serialization, server-sent events for streaming. A reader can split them; mitmdump shows them as one packet. This essay treats them as one floor.

The bottom floor is the one I am going to spend time in.

## The harness

Open a capture of a fresh Claude Code session and the first thing that arrives is a `system` field that runs to thousands of tokens.

Anthropic documents the segments individually. The Agent SDK page on modifying system prompts names what gets embedded in the preset. Working directory, platform and OS version, current date, git status, auto-memory paths. The slash-commands page describes how skill descriptions enter the prompt and how the descriptor budget is sized at 1% of the context window with an 8,000-character fallback. The MCP page documents how server tools surface as `mcp__<server>__<tool>` entries.

Piebald-AI maintains a third-party extraction of the harness strings from the published Claude Code npm artifact. The current count, against version 2.1.126, is 110+ conditional segments. The set includes tool descriptions, subagent system prompts (Explore and Plan), and utility functions for compaction, CLAUDE.md generation, and session title generation. The harness is a programme. Per session, it composes the system field from these segments.

A capture of the first turn (helioy/helioy-bus, claude-sonnet-4-6, cc 2.1.118) shows the system field arriving as three parts.

`[0]` 81 characters, uncached. A billing header: `x-anthropic-billing-header: cc_version=2.1.118.f05; cc_entrypoint=...`. Anthropic reserves one system block as a session metadata channel, separate from the prompt content.

`[1]` 57 characters, cached. Identity preface: "You are Claude Code, Anthropic's official CLI for Claude." One sentence, independently cached.

`[2]` 27,258 characters, cached. The harness body. Working directory, tool descriptions, affordances, environment block, all conditional segments.

Three parts, two cache breakpoints on the content, one uncacheable metadata block. The billing header's presence as a system block does not appear in the published docs.

A few segments deserve naming. The harness instructions block sits at the top. It carries four affordances Claude is told to accept. Markdown rendering, permission-mode tool execution, system-reminder injection by the harness, automatic compaction. Per Piebald's extraction this block is 195 tokens against cc 2.1.124. Tool descriptions vary in cost. The Status line setup block is 2,120 tokens. The /security-review skill is 2,521. The /schedule skill is 3,130. The Explore subagent prompt is 575. Plan mode is 715. The harness ships these segments before the user types anything.

Skills carry an interesting property. By default, only the description and `when_to_use` text enter the harness. Combined text is capped at 1,536 characters per skill. Full SKILL.md content loads only on invocation. This is the cleanest case in the harness of an already-deployed lazy load. Descriptors at session start, full content on demand.

The env block is harness output. Working directory, git repo flag, platform, shell, OS version, model name, today's date. The git status is a snapshot at session start with an explicit warning that it does not refresh during the session. The env block is documented categorically across multiple pages. The wire shows the assembled set in one place.

The harness is the programme that decides what ships. The user wrote none of it. Reading it requires a proxy.

## Context

The harness composes the request. Context is what the harness packs into it.

The Messages API models alternating user and assistant turns. Each message carries a `role` and a `content` field. The content can be a string for simple cases, or an array of typed blocks (text, image, document, tool_use, tool_result). Consecutive same-role turns are merged.

A read_file call inside a Claude Code session unfolds across two messages. The assistant emits a `tool_use` block carrying an id, a name (`Read`), and an input object. The next user message carries a `tool_result` block carrying the matching `tool_use_id` and the file contents. Multiple parallel tool calls return as multiple `tool_use` blocks in one assistant message; all corresponding `tool_result` blocks must come back in a single user message, and they must come first in the content array.

With `ENABLE_TOOL_SEARCH` active, a deferred tool call unfolds across two round-trips before the assistant can respond. The assistant first emits a `ToolSearch` to resolve the descriptor:

```json
{
  "type": "tool_use",
  "id": "toolu_011UQT9BWgN3r3XEmCujh7xD",
  "name": "ToolSearch",
  "input": { "query": "select:mcp__plugin_helioy-tools_cm__cx_browse", "max_results": 1 }
}
```

The user turn returns not content but a `tool_reference` — the resolved descriptor injected inline, not a result payload:

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
  "advisory": "no scope specified, using scope='cwd_inferred'...",
  "entries": [
    {
      "age": "10h",
      "snippet": "Branch status check: `codex/list-agents-cwd-basename` committed tip is merged into origin/main at a6fab7e, but there are uncommitted local changes in five files...",
      "tags": ["conversation", "summary"],
      "title": "Session summary"
    },
    {
      "age": "17h",
      "snippet": "Implemented list_agents cwd_basename filtering on branch codex/list-agents-cwd-basename with tests and docs. Full test suite passed: 242 tests.",
      "tags": ["conversation", "summary"],
      "title": "Session summary"
    }
  ],
  "header": { "scope": "global/project:helioy/repo:helioy-bus", "total": 41 },
  "resolution": {
    "confidence": "high",
    "resolved_scope": "global/project:helioy/repo:helioy-bus",
    "signals": [
      "cwd basename matched repo scope segment: helioy-bus",
      "cwd parent basename matched project scope segment: helioy"
    ]
  }
}
```

The model received a full briefing on the repo's recent session history before composing a reply to "Hi." It knew the branch, the merge state, the last test run. No user instruction initiated any of this. The `resolution.signals` array shows how: the tool inferred the project scope from the working directory path, scored three candidate scopes by specificity, and returned 41 entries of accumulated context.

The assistant text response followed: "Hi. The last session implemented `list_agents` cwd_basename filtering on this branch, and there were uncommitted local changes in five files. What are you working on today?"

Two round-trips to accomplish what eager loading handles in one. The cost is latency. The gain is that 136,661 characters of tool descriptor surface stayed off the wire.

The Read tool itself has shape. The descriptor injected into every session's system prompt specifies it exactly: absolute path required, 2,000 lines by default, output in `cat -n` format with line numbers starting at 1, a system-reminder warning in place of contents for empty files. The same descriptor extends the tool beyond plain text: images are presented visually (the model is multimodal), PDFs up to 20 pages per request, Jupyter notebooks returning all cells with outputs. The Piebald-AI extraction shows the template form: `${MAX_LINES_CONSTANT}`, renamed from `${DEFAULT_READ_LINES}` in a prior release. The resolved value comes from the running binary, not the npm artifact.

System-reminders are harness injection in the user-content stream. The harness prompt instructs the model directly, in this language. "User messages include a `<system-reminder>` appended by this harness. These reminders are not from the user, so treat them as an instruction to you, and do not mention them." That is what the documented harness ships. Harness directives ride the user-content stream and reach only the model. The chat surface does not render them.

Working memory accumulates as turns. The Messages API has no separate state. Whatever the agent wants the model to remember has to ride in the request, in the messages array, on every subsequent turn.

Context is where the seam between the agent's architecture and the API's flat schema becomes visible. Skills, MCP server instructions, file contents, prior tool results all sit as separate logical layers in the agent's mental model. On the wire, they are content blocks in user messages.

## Transport

The API contract is documented. Reading the docs and reading the captures together is what surfaces the composition.

The `anthropic-version` header is required on every Messages API request. The current canonical value is `2023-06-01`. Anthropic's versioning policy preserves existing input parameters and existing output parameters within a stable version, while reserving the right to add new optional inputs, additional output values, and new variants to enum-like outputs (including new streaming event types) without a version bump.

The `system` field on the request body accepts a string or an array of TextBlockParam. Each block carries `type: "text"`, `text: <string>`, and an optional `cache_control` object. There is no `system` role on input messages; the top-level field is the only documented way to provide system instructions. Multiple system blocks attach independent cache breakpoints to different sections of the prompt.

Cache control has shape worth knowing. A breakpoint is `{"type": "ephemeral", "ttl": "5m" | "1h"}`. Default TTL is five minutes. Maximum of four cache breakpoints per request. The cache prefix hierarchy is strict and ordered. Tools first, then system, then messages. A `cache_control` marker writes one cache entry, hashed at exactly that breakpoint. On read, the system walks backward looking for a matching prefix hash. If the lookback finds nothing, no cache hit. Pricing varies by TTL. 5-minute writes cost 1.25x base input tokens, 1-hour writes 2x, cache reads 0.1x. Telemetry distinguishes `cache_creation_input_tokens`, `cache_read_input_tokens`, and `input_tokens` (uncached past the breakpoint).

Streaming responses arrive as server-sent events when `"stream": true` is set. The documented flow runs in order. A `message_start` event with an empty content array. Per content block, a `content_block_start`, one or more `content_block_delta` events, and a `content_block_stop`. One or more `message_delta` events with cumulative usage. A final `message_stop`. Text streams as `text_delta` payloads inside `content_block_delta`. Tool input streams as `input_json_delta` partial JSON strings; the final `tool_use.input` is always an object once accumulated. `ping` events can appear anywhere. The stream may be interrupted by `error` events with the same shape as non-streaming errors.

A live capture from the same session (ENABLE_TOOL_SEARCH=true, first response turn):

```
event: message_start
data: {"type":"message_start","message":{"model":"claude-sonnet-4-6","id":"msg_018X...","usage":{"input_tokens":12207,"cache_creation_input_tokens":15866,"cache_read_input_tokens":0,"cache_creation":{"ephemeral_5m_input_tokens":0,"ephemeral_1h_input_tokens":15866},"output_tokens":1,"service_tier":"standard","inference_geo":"not_available"}}}

event: content_block_start
data: {"type":"content_block_start","index":0,"content_block":{"type":"thinking","thinking":"","signature":""}}

event: ping
data: {"type": "ping"}

event: content_block_delta
data: {"type":"content_block_delta","index":0,"delta":{"type":"signature_delta","signature":"EoYDClsIDRgCKk..."}}

event: content_block_stop
data: {"type":"content_block_stop","index":0}

event: content_block_start
data: {"type":"content_block_start","index":1,"content_block":{"type":"tool_use","id":"toolu_011UQT9BWgN3r3XEmCujh7xD","name":"ToolSearch","input":{},"caller":{"type":"direct"}}}

event: content_block_delta
data: {"type":"content_block_delta","index":1,"delta":{"type":"input_json_delta","partial_json":"{\"query\""}}

event: content_block_delta
data: {"type":"content_block_delta","index":1,"delta":{"type":"input_json_delta","partial_json":": \"select:mcp__plugin_helioy-tools_cm__cx_browse\", \"max_results\": 1}"}}}

event: content_block_stop
data: {"type":"content_block_stop","index":1}

event: message_delta
data: {"type":"message_delta","delta":{"stop_reason":"tool_use"},"usage":{"output_tokens":157},"context_management":{"applied_edits":[]}}

event: message_stop
data: {"type":"message_stop"}
```

The documented event sequence matches. Four fields in this capture are not described in the current streaming reference. `inference_geo` and `service_tier` appear in `message_start` usage. The thinking block emits a `signature_delta` carrying an opaque verification signature rather than a `thinking_delta` with reasoning text. The `tool_use` content block carries a `caller` object (`{"type":"direct"}`). `context_management` appears on `message_delta` with an `applied_edits` array. The `input_json_delta` events stream the tool input as partial JSON strings, accumulating into the final `input` object once the block closes.

The absent reasoning text is intentional. On Claude 4 models, extended thinking is summarized or omitted by default; full thinking output over the wire requires sales-tier access. The `signature_delta` token is a cryptographic verification handle: the server encrypts the reasoning, sends the signature, and decrypts it on the next turn for multi-turn continuity. The client never holds the plaintext. Anthropic's stated rationale is jailbreak resistance — a visible thought process gives adversaries a roadmap — and a faithfulness caveat that streaming reasoning may not accurately represent what is happening in the model. In a separate disclosure from February 2026, Anthropic documented a coordinated chain-of-thought extraction campaign: roughly 24,000 fraudulent accounts prompted Claude to articulate reasoning chains, generating training data at scale for third-party model distillation. Anthropic's docs do not explicitly connect that threat model to the summarization design, but the encrypted signature mechanism makes the same data unavailable at the wire level regardless of intent.

The sample stream the docs publish carries an initial `message_start` with `usage: {"input_tokens": 25, "output_tokens": 1}`, then text deltas, then a `message_delta` with `stop_reason: "end_turn"` and cumulative `output_tokens: 15`, then `message_stop`. The shape on a real Claude Code response matches.

The transport floor is observable from one capture per session. The schema is published. The composition the agent decides on per turn is what the docs do not assemble in one place.

## The ENABLE_TOOL_SEARCH measurement

There is one knob in this stack with quantified before-and-after numbers.

`ENABLE_TOOL_SEARCH` is documented on the Claude Code Agent SDK page on tool search. The valid values include unset (default; all tool definitions load eagerly on every turn), `true`, `auto` (loads everything if tool definitions are under 10% of the context window; defers them otherwise), `auto:N` (custom percentage threshold), and `false` (loads all tool definitions on every turn).

The mechanism is documented at the API layer too. Tools marked `defer_loading: true` are not included in the system-prompt prefix. When the model discovers a deferred tool through tool search, the tool definition is appended inline as a `tool_reference` block in the conversation. Search returns 3 to 5 most relevant tools per query. Two server-side variants are documented. Regex (`tool_search_tool_regex_20251119`) and BM25 (`tool_search_tool_bm25_20251119`). The cached prefix is preserved.

Anthropic publishes numbers for the cost. A typical multi-server MCP setup of GitHub, Slack, Sentry, Grafana, Splunk consumes about 55,000 tokens of tool definitions before the agent does any work. Tool search reduces this by over 85%. Anthropic's engineering blog post on advanced tool use frames it numerically. 191,300 tokens of context preserved with tool search active, against 122,800 with the traditional approach.

Three independent practitioner measurements posted as GitHub issues against `anthropics/claude-code` triangulate this against real Claude Code installations. Issue #18298 reported 7 MCP servers totaling 28,100 tokens of MCP definitions (14.1% of context). Issue #18397 reported a multi-server setup at 70,500 tokens of MCP definitions (35.3% of context), dropping to roughly zero on first turn with `ENABLE_TOOL_SEARCH=true` set explicitly. Issue #19890 reported 40+ MCP tools across Sentry, Atlassian, and an IDE server at 49,500 tokens (24.8%) without the flag, expected to drop to roughly zero with it.

Same session (helioy/helioy-bus, claude-sonnet-4-6), same first turn, same MCP loadout. Three cold starts.

| | Default | `ENABLE_TOOL_SEARCH=true` | `ENABLE_TOOL_SEARCH=auto:0` |
|---|---|---|---|
| Input tokens | 67,504 | 28,073 | 27,991 |
| Tools in wire | 149 | 8 | 8 |
| Tool descriptor chars | 173,633 | 36,972 | 36,972 |
| Cache read (turn 1) | 0 | 0 | 9,599 |

39,431 tokens on a first turn. The four-figure floor understated this by an order of magnitude.

`auto:0` sets the deferral threshold at 0% — defer always, regardless of tool surface size. The result is identical to `true`: 8 tools in wire, same descriptor surface. The 82-token difference between the two captures is the startup hook success message (363 chars), absent in the `auto:0` run. The 9,599 cache read on the `auto:0` turn reflects the static system prompt blocks hitting from a prior session — the identity preface and harness body caching across session boundaries when the prefix is unchanged.

A second observation worth making about this knob. A CHANGELOG entry documents `auto` mode at the 10% threshold as the default. Issues #18298, #18397, and #19890 report that auto mode does not consistently fire above the documented threshold. Explicit `ENABLE_TOOL_SEARCH=true` reliably restores the documented behavior. The default that ships and the default that works can diverge.

If one knob saves five figures of tokens per turn, what else is shipping by default?

## Token pollution

Tokens that ride along on every turn without earning their place consume the context window the user wanted for the work itself.

Concrete numbers exist. Anthropic's tool search documentation publishes the "50 tools = 10,000 to 20,000 tokens" range for a moderate MCP loadout. The "GitHub, Slack, Sentry, Grafana, Splunk" example lands at ~55,000 tokens. Practitioner captures of typical real-world MCP loadouts land in the 28,000 to 70,000 range as cited above. The harness itself, before any MCP, runs to thousands of tokens of segment text per Piebald's extraction.

Caching offsets the per-turn cost. Anthropic's engineering blog on Claude Code's caching strategy describes a tiered layout. Static system prompt and tools are globally cached; CLAUDE.md is cached within a project; session context is cached within a session; conversation messages cache per session. Cache reads cost 0.1x base input tokens. With a 90% cache hit rate, a $100 session falls to about $19. Four turns of one session (helioy/helioy-bus, `ENABLE_TOOL_SEARCH=auto:0`, no hooks). The prompt was "Hi".

| Turn | Request | Cache read | Cache write | Fresh input | Tools | Event |
|---|---|---|---|---|---|---|
| 1 | 27,991 | 9,599 | 6,267 | 12,125 | 8 | ToolSearch (cx_browse + am_query) |
| 2 | 28,369 | 15,866 | 12,308 | 195 | 10 | cx_browse ✓, am_query ✓ (descriptors loaded) |
| 3 | 29,252 | 15,866 | 12,308 | 1,078 | 10 | cx_browse ✓, am_query ERROR → retry queued |
| 4 | 31,218 | 28,281 | 198 | 2,739 | 10 | am_query ✓ → END_TURN, greeting text |

Turn 1 had a partial warm cache (9,599) from a prior session — the static system prompt blocks hit cross-session. Turn 2 collapsed fresh input to 195 tokens once the session-start reminders cached. Cache read grew from 9,599 to 28,281 across four turns as accumulated conversation content moved from fresh to cached.

The am_query error on turn 3 is the lazy-load failure mode: the descriptor resolved correctly through ToolSearch, but the tool call itself failed at runtime. The model retried without user input and recovered on turn 4.

Four round-trips to answer "Hi". The token cost on each turn stayed near 28,000 to 31,000 — flat relative to the 67,504 default — because deferral kept the tool surface at 10 descriptors (36,972 + 896 + 1,720 chars) rather than 149 (173,633 chars). The latency trade is real and measurable.

Cache offsets cost; it does not eliminate composition. Whatever ships in the prefix has to ship the first time. Anthropic's own engineering account names the constraint. "Because tools are part of the cached prefix, adding or removing a tool invalidates the cache for the entire conversation." Cache breaks are treated as incidents. The first-turn cost is the floor. Every operation that mutates the prefix pays the floor again.

Token pollution is one consequence of composition the user does not author. Control is the other.

## Control

To change agent behaviour, you have to change what it sends. The wire is where it sends from. The vendor's default runs unless somebody on this side of the wire intervenes.

The skills mechanism is one example of intervention already in production. Skill descriptions enter the harness; full SKILL.md content loads only on invocation. The lazy-load pattern is documented and shipped. The harness already does this for one segment.

The tools mechanism is a second. `ENABLE_TOOL_SEARCH` defers tool definitions out of the system-prompt prefix into inline `tool_reference` blocks expanded server-side. The pattern is the same one. Descriptor surface for discovery, full content on demand. Two of the obvious lazy-load mechanisms have shipped.

Same loadout, same first turn. Hook active versus hook removed.

| | Hook active | Hook removed |
|---|---|---|
| Request tokens | 67,504 | 67,422 |
| User blocks | 6 | 5 |
| Missing block | none | `SessionStart:startup hook success` (363 chars) |
| Response shape | silent → `cx_browse` only | "Starting session checks per memory instructions." + `cx_browse` + `am_query` in parallel |

The token delta is 82. The behavioural delta is larger. With the hook, the model called one tool, silently, with the exact parameters the hook specified. Without it, the model produced a text preamble, then dispatched two memory tools in parallel — cx_browse and am_query — drawing its own inference from the 11,852-char `EXTREMELY_IMPORTANT` block that was still present in both sessions.

Turn 2 without the hook: cache read 57,828 (the full cold-start write now warm), fresh input 2,836 (both tool results: 2,143 chars from cx_browse, 5,862 from am_query), END_TURN with a text greeting summarising the branch state. The model got there. The hook collapses the interpretation step, not the outcome.

When asked why it called am_query, the model identified two separate sources. The `helioy-tools_am` MCP server instruction — one line in the 3,954-char MCP server instructions block — says "Query geometric memory at the START of every session with am_query." The cx_browse call came from a different source: a project-specific feedback memory entry, `feedback_cx_browse_on_start.md`, which told the model to call cx_browse at session start in this repo.

Two instructions from two injection layers, both firing simultaneously, neither aware of the other.

A third experiment clarifies the weight of each. With `autoMemoryEnabled: false` set in `.claude/settings.json`, the file-memory entries do not inject. The harness body shrinks from 27,258 to 14,712 characters — the auto-memory configuration removed. The AM MCP server instruction remains in the 3,954-char block unchanged. The model responded to "Hi" with "Hi! What are you working on?" in one turn, zero tool calls.

The AM instruction alone was not enough. The model read "Query geometric memory at the START of every session" and skipped it. MCP server instructions are advisory text, not commands. The model weighs them against all other context. Combined with a file-memory entry reinforcing the same behaviour, the instruction fired. Alone, it did not.

The hook's value is not the 363 characters it saves. It is that it collapses this entire weighting problem into a single authoritative instruction. With the hook, the model called one tool, silently, precisely. Without it, two competing instructions from different injection layers both fired — one routing correctly, one returning noise from unrelated projects. Strip the file-memory entries and the MCP instruction is no longer sufficient to drive any call at all.

The third obvious target is the env block, the working-memory block, and the harness instructions themselves. The Agent SDK ships an `excludeDynamicSections` option that moves per-session context out of the system field into the first user message, holding the prefix stable for cross-session cache reuse. The default behavior remains the dynamic preset. Issue #44536 on `anthropics/claude-code` is filed under the title "Lazy context loading: extend the ToolSearch pattern to all context components."

The cost of composition is paid by the user, on every turn, in tokens that consume the window the user wanted for the work itself. Knowing what is on the wire is what makes intervention possible. Every other lever sits downstream of that.

I publish the teardowns at [knowmorecontext.substack.com](https://knowmorecontext.substack.com).

Anthropic introduced the Tool Search API primitive in November 2025. The type names embed the date: `tool_search_tool_bm25_20251119`. Codex issue #9266 (January 15, 2026) proposed an equivalent for OpenAI's CLI and cited the Anthropic spec by URL as the reference implementation. PR #17854 landed it stable on April 16, 2026 and flipped the default on. Codex manages this via a TOML feature flag (`codex features enable tool_search`). No `ENABLE_TOOL_SEARCH` env var exists in Codex's config surface. The deployment contracts diverged: Claude Code gates deferral behind explicit opt-in; Codex ships with it on and requires deliberate opt-out.

If you enjoyed this, let me know what you want torn down next. Reply on Substack or find me at @KnowMoreContext on X.

Token matters.

## Sources

Primary references for the claims in this piece.

Anthropic Messages API:
- [Messages API reference](https://platform.claude.com/docs/en/api/messages)
- [Versioning](https://platform.claude.com/docs/en/api/versioning)
- [Streaming Messages](https://platform.claude.com/docs/en/api/messages-streaming)
- [Prompt caching](https://platform.claude.com/docs/en/docs/build-with-claude/prompt-caching)
- [Define tools](https://platform.claude.com/docs/en/agents-and-tools/tool-use/define-tools)
- [Handle tool calls](https://platform.claude.com/docs/en/agents-and-tools/tool-use/handle-tool-calls)
- [Tool search tool](https://platform.claude.com/docs/en/agents-and-tools/tool-use/tool-search-tool)

Claude Code internals:
- [Modifying system prompts](https://code.claude.com/docs/en/agent-sdk/modifying-system-prompts)
- [Tool search](https://code.claude.com/docs/en/agent-sdk/tool-search)
- [Slash commands and skills](https://code.claude.com/docs/en/slash-commands)
- [MCP](https://code.claude.com/docs/en/mcp)
- [Environment variables](https://code.claude.com/docs/en/env-vars)
- [Lessons from building Claude Code: prompt caching is everything](https://claude.com/blog/lessons-from-building-claude-code-prompt-caching-is-everything)
- [Introducing advanced tool use](https://www.anthropic.com/engineering/advanced-tool-use)

OpenAI Codex lineage:
- [Codex issue #9266](https://github.com/openai/codex/issues/9266): Jan 15, 2026. Proposes tool deferral, links Anthropic spec as reference.
- [Codex PR #17854](https://github.com/openai/codex/pull/17854): Apr 16, 2026. Flips `Feature::ToolSearch` to stable and default-on.
- [Codex features config](https://developers.openai.com/codex/cli/features): `tool_search` toggled via `codex features enable`, not an env var.

Third-party with reproducible methodology:
- [Piebald-AI/claude-code-system-prompts](https://github.com/Piebald-AI/claude-code-system-prompts): mechanical extraction from the published npm artifact.

Practitioner measurements (filed against `anthropics/claude-code`):
- Issue #18298 — 7 MCP servers, 28,100 tokens of MCP definitions
- Issue #18397 — multi-server setup, 70,500 tokens of MCP definitions
- Issue #19890 — 40+ MCP tools, 49,500 tokens of MCP definitions
- Issue #44536 — open feature request for "lazy context loading: extend the ToolSearch pattern to all context components"
