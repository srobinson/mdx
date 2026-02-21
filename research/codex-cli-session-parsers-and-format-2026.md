---
title: Codex CLI Session Log Parsers, Viewers, and Format Documentation
type: research
tags: [codex-cli, openai, session-logs, jsonl, devtools, agent-observability]
summary: Rich ecosystem of open source tools parse Codex CLI rollout JSONL files; OpenAI themselves ship Euphony as an official viewer. Format stored at ~/.codex/sessions/YYYY/MM/DD/rollout-*.jsonl.
status: active
source: deep-research
confidence: high
created: 2026-04-24
updated: 2026-04-24
---

## Executive Summary

A substantial ecosystem of open source tools exists for parsing OpenAI Codex CLI session logs. This ranges from OpenAI's own official viewer (Euphony, 213 stars) to multi-agent session browsers (agentsview at 827 stars, cass at 709 stars, Agent Sessions at 491 stars) down to Codex-specific utilities (codex-sessions, codex-history-list). The Codex CLI stores sessions as JSONL "rollout" files at `~/.codex/sessions/YYYY/MM/DD/rollout-<timestamp>-<uuid>.jsonl`. The format uses a `RolloutLine` envelope with `type`/`payload` fields wrapping `SessionMeta`, `ResponseItem`, and `EventMsg` variants. No official JSON Schema is published, but `codex app-server generate-json-schema` can dump a version-specific schema.

## Codex CLI Session Storage Format

### Directory Structure
- **Location**: `~/.codex/sessions/` (or `$CODEX_HOME/sessions/` if `CODEX_HOME` is set)
- **Hierarchy**: `YYYY/MM/DD/rollout-<timestamp>-<uuid>.jsonl`
- **Config**: `~/.codex/config.toml`
- **TUI logs**: `~/.codex/logs/codex-tui.log`

### JSONL Schema (post-PR #3380, merged Sept 2025)
Each line is a `RolloutLine` with `type` and `payload` fields. The `RolloutItem` enum has three variants:
1. **SessionMeta** - metadata with conversation `id`
2. **ResponseItem** - agent/assistant responses
3. **EventMsg** - events including `UserMessage` variants

Additional fields observed in the wild:
- `record_type` (value `"state"` for state records, filtered during parsing)
- `role` (user/assistant)
- `content` (string or array of `{type, text}` objects)
- `timestamp` at file level for sorting
- Tool calls, errors, and token usage data

### Format Evolution
Pre-PR #3380 files contain bare `SessionMeta`/`ResponseItem` JSON without the `RolloutLine` envelope. Parsers must handle both formats. The `--json` streaming output uses event types: `thread.started`, `turn.started`, `turn.completed`, `turn.failed`, `item.*`, and `error`.

### Schema Generation
Run `codex app-server generate-json-schema` to dump a version-specific JSON Schema bundle.

## Tools That Parse Codex CLI Sessions

### Official: OpenAI Euphony
- **Repo**: https://github.com/openai/euphony
- **Stars**: 213
- **What**: Browser-based viewer for Harmony chat data AND Codex session JSONL logs
- **Stack**: TypeScript (79%), CSS, Python/FastAPI backend, Web Components
- **Features**: Auto-detects Codex JSONL, renders as conversation timeline, JMESPath filtering, metadata inspection, token rendering, markdown support, embeddable web components
- **License**: Apache 2.0
- **Announced**: April 21, 2026 by @OpenAIDevs on X

### Multi-Agent Session Browsers

**agentsview** (wesm/agentsview)
- **Stars**: 827
- **What**: Local-first session intelligence for 16 agents including Codex CLI
- **Stack**: Go (71%), TypeScript/Svelte frontend, Tauri, SQLite with FTS5
- **Features**: Full-text search, cost tracking, activity heatmaps, HTML/Gist export, live updates via SSE, prompt-caching-aware cost calculation
- **Note**: Bills itself as "100x faster replacement for ccusage"

**cass** (Dicklesworthstone/coding_agent_session_search)
- **Stars**: 709
- **What**: Unified TUI/CLI indexing 19 agent platforms into searchable timeline
- **Stack**: Rust, Tantivy (BM25), SQLite, optional MiniLM embeddings
- **Features**: Sub-60ms search, hybrid lexical+semantic, wildcard patterns, analytics dashboard, HTML export with AES-256-GCM encryption, SSH/rsync multi-machine sync, robot mode for AI agent integration
- **Codex path**: `~/.codex/sessions` (Rollout JSONL)

**Agent Sessions** (jazzyalex/agent-sessions)
- **Stars**: 491
- **What**: Native macOS app for 8 agents including Codex CLI
- **Stack**: Swift (87%), Python, Shell
- **Features**: Agent Cockpit (live HUD for iTerm2), unified search with image browsing, session resume via right-click, read-only access to agent directories

**agtrace** (lanegrid/agtrace)
- **Stars**: 39
- **What**: Real-time observability dashboard for Claude Code, Codex, Gemini
- **Stack**: Rust (98.7%), distributed as npm package and Rust crate
- **Features**: Context window monitoring, token consumption tracking, MCP integration, session browsing

### Codex-Specific Tools

**codex-sessions** (Uri2001/codex-sessions)
- **Stars**: 3
- **What**: Cross-platform TUI for browsing/searching/managing Codex CLI session logs
- **Stack**: Go 1.25, tview, tcell
- **Features**: Fuzzy search across session metadata, keyboard-first navigation, quick resume via `codex resume <session-id>`, safe deletion
- **Latest release**: v0.2.2 (Nov 2025)

**codex-history-list** (shinshin86/codex-history-list)
- **Stars**: 9
- **What**: CLI that lists Codex sessions with cwd and first user ask
- **Stack**: TypeScript
- **Features**: Extracts cwd from `<environment_context>` tags, identifies first user query, concurrent file processing, date range filtering, JSON output

### Usage Analytics

**ccusage** (ryoppippi/ccusage)
- **Stars**: not captured (actively maintained, v17+)
- **What**: CLI for analyzing Claude Code AND Codex CLI usage from local JSONL files
- **Stack**: TypeScript, npm
- **Features**: Daily/monthly/session/5-hour-block reports, multi-instance support, timezone/locale configuration

**CodexBar** (steipete/CodexBar)
- **What**: macOS menu bar app showing usage stats for Codex and Claude Code

**CodeBurn** (getagentseal/codeburn)
- **What**: Interactive TUI dashboard for cost observability across Claude Code, Codex, Cursor

### Session Format Converters

**SpecStory CLI** (specstoryai/getspecstory)
- **What**: Converts Codex CLI sessions to structured Markdown in `.specstory/history/`
- **Commands**: `specstory run codex` (auto-capture), `specstory sync codex` (batch convert)
- **Source**: Reads from `~/.codex/history`

**AI Sessions MCP** (HN: "Share sessions between Codex and Claude Code")
- **What**: MCP server letting any client search/read local CLI sessions across agents
- **Purpose**: Start in one agent, resume in another

## Sources Consulted

### GitHub Repositories
- https://github.com/openai/codex (official repo)
- https://github.com/openai/euphony (official viewer)
- https://github.com/openai/codex/pull/3380 (rollout format PR)
- https://github.com/openai/codex/discussions/3827 (rollout file discussion)
- https://github.com/openai/codex/issues/2765 (session transcripts issue)
- https://github.com/openai/codex/issues/5781 (chat export issue)
- https://github.com/Dicklesworthstone/coding_agent_session_search
- https://github.com/jazzyalex/agent-sessions
- https://github.com/wesm/agentsview
- https://github.com/Uri2001/codex-sessions
- https://github.com/shinshin86/codex-history-list
- https://github.com/ryoppippi/ccusage
- https://github.com/lanegrid/agtrace

### Official Documentation
- https://developers.openai.com/codex/cli/features
- https://developers.openai.com/codex/cli/reference

### X/Twitter
- https://x.com/OpenAIDevs/status/2046620363568890230 (Euphony announcement)
- https://x.com/specstoryai/status/1975204317700509776 (SpecStory Codex support)
- https://x.com/tomsiwik/status/1953558364665131159 (session resume tip)

### Hacker News
- https://news.ycombinator.com/item?id=45474749 (AI Sessions MCP)
- https://news.ycombinator.com/item?id=46425670 (agtrace)

### Reddit
- No relevant results found for Codex CLI session parsing topics

## Source Quality Assessment

**Confidence: High.** Multiple independent tools confirm the same storage format and directory structure. The official OpenAI Euphony tool validates that the JSONL format is stable enough for third-party consumption. The PR #3380 in the official repo documents the format evolution. The ecosystem is active (most tools updated within the last 2 months as of April 2026).

**Gap**: No official JSON Schema documentation is published. The format is reverse-engineered from the source code and observation. The `codex app-server generate-json-schema` command exists but produces version-specific output.

## Open Questions

1. Is there a stable, versioned schema contract for rollout JSONL files, or can OpenAI break parsers with any release?
2. Does the `--json` streaming output format match the persisted rollout format exactly, or are they different schemas?
3. How do multi-turn tool call chains (MCP, shell, file edits) serialize in the rollout format? The PR mentions `ResponseItem` but details are sparse.
