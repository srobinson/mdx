---
title: "Splitrail by Piebald AI: Token Usage Tracker and Cost Monitor Analysis"
type: research
tags: [frontend, tui, vscode-extension, token-tracking, cost-monitoring, ratatui, webview, dashboard, mcp]
summary: "Splitrail is a real-time token usage tracker/cost monitor for AI coding tools, with a Rust TUI (ratatui), VS Code webview dashboard, and Next.js cloud app. Relevant to Helix frontend as a pattern reference for operational dashboards displaying structured metrics over time."
status: active
source: github-researcher
confidence: high
created: 2026-03-23
updated: 2026-03-23
---

## Executive Summary

Splitrail is a **real-time token usage tracker and cost monitor** for AI coding assistants (Claude Code, Gemini CLI, Codex CLI, Copilot, Cline, Roo Code, etc.). It is *not* an agent memory/context UI. It solves the problem of "how much am I spending on AI coding tools" by parsing local data files from each tool, aggregating token counts and costs, and presenting them across three surfaces: a terminal TUI, a VS Code sidebar, and a web cloud dashboard. Built by Piebald AI (134 stars, actively maintained, v3.3.5 as of March 2026).

While Splitrail targets a different domain than Helix, it provides transferable patterns for building operational dashboards over structured time-series data, multi-source aggregation UIs, and the CLI-to-web progression that Helix will eventually need.

## Architecture Overview

### System Design

```
Local data files (Claude Code, Gemini CLI, Copilot, etc.)
        |
        v
  Analyzer Registry (pluggable trait-based)
        |
        v
  Parser + Deduplication (hash-based, per-message)
        |
        v
  Aggregation (by date, by session, by model)
        |
        v
  Three presentation layers:
    1. TUI (ratatui + crossterm)
    2. VS Code Extension (webview + CLI subprocess)
    3. Cloud (Next.js + API upload)
```

### Data Flow

1. **Discovery**: Each analyzer discovers data files at platform-specific paths (e.g., `~/.claude/projects/`, `~/.gemini/tmp/`, `~/.codex/sessions/`)
2. **Parsing**: JSON/JSONL parsed into normalized `ConversationMessage` structs
3. **Deduplication**: xxhash-based global hash prevents double counting
4. **Aggregation**: Messages grouped by date into `DailyStats`, or by conversation into `SessionAggregate`
5. **Real-time updates**: File watcher (`notify` crate) triggers incremental re-parse of changed files
6. **Display**: Stats pushed via `tokio::sync::watch` channel to TUI; VS Code calls CLI as subprocess

### Key Data Model

```
ConversationMessage {
    application, date, project_hash, conversation_hash,
    global_hash, model, session_name, role,
    stats: Stats {
        input_tokens, output_tokens, cached_tokens,
        reasoning_tokens, cost_cents, tool_calls,
        files_read, files_edited, files_added, files_deleted,
        lines_read/edited/added/deleted,
        bytes_read/edited/added/deleted,
        terminal_commands, file_searches
    }
}

DailyStats { date, user_messages, ai_messages, conversations, models: {name: count}, stats: TuiStats }
SessionAggregate { session_id, first_timestamp, analyzer_name, stats, models, session_name, date }
```

## Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Core runtime | Rust 2024 edition, tokio | Async processing, parallel parsing |
| TUI | ratatui 0.30 + crossterm 0.29 | Terminal dashboard rendering |
| Parsing | simd-json, serde | High-perf JSON/JSONL parsing |
| File watching | notify 8.2 | Real-time filesystem monitoring |
| Parallelism | rayon, dashmap, parking_lot | Parallel parsing, concurrent maps |
| Hashing | xxhash (xxh3) | Fast deduplication hashing |
| Token counting | tiktoken-rs | Token estimation |
| MCP server | rmcp 0.12 | Model Context Protocol integration |
| VS Code extension | TypeScript, VS Code API | Webview sidebar dashboard |
| Cloud | Next.js, React, Tailwind CSS | Web dashboard with dark/light mode |
| Database | rusqlite (bundled) | Local contribution caching |
| Memory allocator | mimalloc v3 | Reduced memory usage with aggressive collection |
| Config | TOML | `~/.splitrail.toml` |

## Frontend Patterns

### 1. TUI Dashboard (ratatui)

The TUI at `src/tui.rs` (2,259 lines) is the primary interface. Key patterns:

**Layout structure:**
- Vertical stack: Header > Update Banner (conditional) > Tabs > Main Table > Summary Stats (toggleable) > Help/Status Bar
- Uses `ratatui::layout::Layout` with `Constraint::Length` for fixed areas and `Constraint::Min` for the data table

**Tab navigation:**
- One tab per analyzer (Claude Code, Gemini CLI, etc.), filtered to only show tools with data
- Tab title includes conversation count: `" Claude Code (44) "`
- Highlighted tab: black text on light green background

**Data table rendering:**
- Columns: Date, Cost, Cached Tokens, Input Tokens, Output Tokens, Reasoning Tokens, Conversations, Tool Calls, Models
- **Peak value highlighting**: Highest value in each column rendered in red, providing instant visual identification of peak usage days
- **Empty row dimming**: Days with zero activity are dimmed (Modifier::DIM)
- **Right-aligned numerics** with `format_number_fit` for overflow handling
- Fixed column width (12 chars for token columns) with graceful fallback to human-readable format when values exceed width

**Two view modes:**
- `StatsViewMode::Daily`: Rows per day with aggregated stats
- `StatsViewMode::Session`: Rows per session with optional day filter (Ctrl+T toggles)

**Date search/jump:**
- Activated with `/`, supports partial matching: month names ("jan"), numeric months ("7"), full dates, M-D, YYYY-MM formats
- Auto-scrolls to first matching date as user types

**Real-time updates:**
- Stats pushed via `tokio::sync::watch` channel
- TUI polls for events at 100ms intervals
- `needs_redraw` flag prevents unnecessary renders
- File watcher events forwarded through `mpsc::UnboundedChannel`

**Upload status display:**
- Animated dots during upload ("Uploading 42/100 messages...")
- Color-coded status: green for success, red for failure, yellow for config issues

**Keyboard interaction model:**
- vim-style navigation: h/l (tabs), j/k (rows)
- Arrow keys as alternatives
- `/` for search, `r` for reverse sort, `s` to toggle summary, `Enter` to drill into day, `q`/`Esc` to quit, `Home`/`End` for jump

### 2. VS Code Extension (Webview Dashboard)

The VS Code extension at `vscode-splitrail/` uses a **webview sidebar** panel in the Activity Bar. Architecture:

**Integration approach:**
- Calls the Splitrail CLI binary as a subprocess: `splitrail stats` produces JSON output
- No direct file parsing in the extension. CLI is the single source of truth.
- Path resolution: checks configured path, then `../target/debug/splitrail`, then PATH

**Dashboard layout (HTML/CSS in `dashboardView.ts`):**
- Card-based grid layout using CSS Grid
- Hero section: large cost number + token/message summary
- 2x2 card grid: By Tool, By Model, Today's Details, Recent Projects
- Time scope selector: Today / This Week / This Month / All Time

**Styling approach:**
- Inline CSS using VS Code theme variables (`--vscode-foreground`, `--vscode-editor-background`, etc.)
- No external CSS framework. All styles defined in template literal.
- Content Security Policy with nonce-based script injection
- Theme-aware: inherits VS Code dark/light mode automatically

**Real-time updates:**
- `vscode.workspace.createFileSystemWatcher` monitors AI tool data directories
- 1500ms debounce on file change events
- Refreshes by re-running CLI subprocess

**Status bar integration:**
- Shows compact summary: `"Splitrail: 1.2m tok . $70.02"`
- Click opens QuickPick popup with today vs. all-time comparison

**Data flow:**
```
CLI subprocess (splitrail stats --json)
    -> JSON parsed in extension.ts
    -> postMessage to webview
    -> JavaScript render() function updates DOM
```

### 3. Cloud Dashboard (Next.js)

The cloud dashboard at `splitrail.dev` is a separate closed-source web app. From the screenshot and CHANGELOG:

**Visible features:**
- Summary cards at top: Tokens (788.96M), Cost ($669.67), Tool Calls (8.8K), Days Tracked (52), Applications (3)
- Tab bar for analyzers: Claude Code (44), Gemini CLI (33), Codex CLI (24)
- Full data table: Date, Cost, Cached Tokens, Input Tokens, Output Tokens, Conversations, Tool Calls, Lines, Models
- Leaderboard feature for competitive usage comparison
- Built with Next.js, Tailwind CSS, dark/light mode

**Upload mechanism:**
- CLI uploads batches of messages (3000 per chunk) to the cloud API
- API token authentication via `~/.splitrail.toml`
- Chunked upload with retry logic, progress tracking
- Timezone-aware date handling for cross-machine aggregation

## Data Visualization Patterns

### Patterns used in Splitrail

1. **Time-series table** (primary): Daily rows with numeric columns, peak highlighting, sortable, filterable
2. **Summary cards**: Hero number (total cost) with supporting metrics (token count, message count)
3. **Breakdown cards**: By Tool and By Model with percentage badges
4. **Detail cards**: Input/Output/Cache token breakdown, file operation counts
5. **Tab-based segmentation**: One tab per data source/analyzer
6. **Scope selector**: Time range filtering (today/week/month/all)

### Patterns NOT used (gaps relevant to Helix)

- No line/bar/area charts. All visualization is tabular and card-based.
- No graph/network visualization
- No timeline/history view for individual items
- No search across content (only date filtering)
- No relationship visualization between entities
- No tree/hierarchical views beyond the two-level table drill-down

## Integration and API Patterns

### MCP Server

Splitrail exposes its data via MCP (Model Context Protocol), allowing AI assistants to query usage stats programmatically. Implemented in `src/mcp/` using the `rmcp` crate.

**Tools exposed:**
- `get_daily_stats`: Query with date/analyzer/limit filters
- `get_model_usage`: Model distribution breakdown
- `get_cost_breakdown`: Cost over date range with daily granularity
- `get_file_operations`: File read/write/edit statistics
- `compare_tools`: Cross-tool comparison
- `list_analyzers`: Available analyzer enumeration

**Resources:**
- `splitrail://summary`: Latest daily summary as text
- `splitrail://models`: Model usage breakdown as text

**Pattern for Helix**: The MCP server pattern is directly applicable. Helix could expose cm entries, am values, and audit records via MCP tools, making its data accessible to agent toolchains.

### JSON API

The `splitrail stats` CLI command outputs structured JSON matching `JsonStatsResponse`:
```typescript
interface JsonStatsResponse {
  analyzer_stats: {
    analyzer_name: string;
    num_conversations: number;
    daily_stats: { [date: string]: {
      date: string;
      user_messages: number;
      ai_messages: number;
      conversations: number;
      models: { [model: string]: number };
      stats: { inputTokens, outputTokens, cost, ... };
    }};
    messages?: ConversationMessage[];
  }[];
}
```

### Cloud Upload API

- REST endpoint at configurable server URL
- Bearer token authentication
- Chunked uploads (3000 messages per batch)
- Deduplication via global hash
- Retry logic with configurable attempt count
- Progress callbacks for TUI/extension integration

## What a Helix Frontend Can Learn

### Directly transferable patterns

1. **Progressive disclosure across surfaces**: Splitrail's three-tier approach (TUI for power users, VS Code sidebar for at-a-glance, web for full analytics) maps directly to Helix's eventual needs. Start with a CLI/TUI for developer use, add an editor sidebar, then build a full web dashboard.

2. **CLI-as-backend for editor extensions**: The VS Code extension calls the CLI as a subprocess rather than reimplementing parsing logic. For a Helix VS Code extension, this means: build `helix stats` or `helix query` CLI commands that output JSON, then render that JSON in a webview. Single source of truth, zero code duplication.

3. **Card-based summary + table drill-down**: The hero card (total cost) + breakdown cards (by tool, by model) + detailed table pattern works well for Helix. Translate to: hero card (total context entries / active attention values) + breakdown by scope/tag + detailed entry table.

4. **Time scope selector**: Today/Week/Month/All is a universal pattern. For Helix audit trails, this maps directly.

5. **Tab-based source segmentation**: Splitrail's one-tab-per-analyzer maps to one-tab-per-scope or one-tab-per-vertex (cm, am, audit) in Helix.

6. **Real-time file watching + debounced refresh**: The pattern of watching data files, debouncing changes, and pushing updates via channels applies to watching cm/am data stores.

7. **Peak value highlighting**: Coloring extreme values in tabular data draws attention to anomalies. Useful for audit anomaly detection in Helix.

8. **VS Code theme variable integration**: Using `--vscode-*` CSS custom properties for automatic dark/light mode adaptation is the correct approach for any VS Code webview.

### Patterns Helix needs that Splitrail does not provide

1. **Graph/network visualization**: Helix's derivation DAGs, cm entry relationships, and am geometric surfaces need d3.js, three.js, or similar. Splitrail has no graph visualization.

2. **Content search and preview**: Helix stores rich text context entries. A frontend needs full-text search with snippet preview, faceted filtering by tags/scopes/types. Splitrail only filters by date.

3. **3D/geometric visualization**: am's quaternion-based S3 hypersphere representation needs specialized visualization. This is entirely outside Splitrail's domain.

4. **Audit trail timeline**: CRITIC mutation records and provenance chains need a timeline view with expand/collapse for individual records. Splitrail's daily granularity is too coarse.

5. **Entity detail views**: Clicking a cm entry should show its full content, metadata, relationships, derivation history. Splitrail's drill-down stops at session-level aggregates.

6. **Multi-backend data composition**: Helix combines cm + am + audit data from different backends. The frontend needs a unified query layer that composes results, which is more complex than Splitrail's single-backend model.

### Recommended tech stack for Helix frontend

Based on Splitrail's approach and Helix's requirements:

- **Web framework**: Next.js (validated by Splitrail Cloud, SSR/SSG for performance)
- **Styling**: Tailwind CSS + VS Code theme variables for editor integration
- **Data tables**: TanStack Table for sortable/filterable tables with virtual scrolling
- **Charts**: Recharts or Nivo for time-series cost/usage charts
- **Graph visualization**: Cytoscape.js or react-flow for derivation DAGs
- **3D visualization**: Three.js with React Three Fiber for am hypersphere rendering
- **State management**: Zustand or Jotai (lightweight, avoids Redux boilerplate)
- **Real-time**: WebSocket or SSE for live updates from Helix API
- **VS Code extension**: Webview panel calling Helix CLI (follow Splitrail's pattern)

## Assessment

### Strengths

- Clean separation between data layer (analyzers) and presentation (TUI/extension/cloud)
- Performance-conscious: mimalloc, simd-json, rayon parallelism, xxhash, TinyVec for small collections
- Pluggable analyzer architecture via trait-based registry
- MCP server integration is forward-thinking
- VS Code extension uses webview with proper CSP and theme integration

### Limitations

- No data visualization beyond tables and cards (no charts, graphs, or timelines)
- Cloud is closed-source, so its full patterns are not inspectable
- VS Code extension uses inline HTML templates rather than a component framework
- No mobile or responsive design in the VS Code sidebar

### Relevance to Helix: Medium

Splitrail is a usage tracker, not a memory/context UI. The architectural patterns (CLI-as-backend, progressive surface expansion, card+table dashboard layout, real-time file watching) transfer cleanly. The specific UI challenge of visualizing context entries, geometric attention values, and audit provenance chains requires visualization capabilities beyond what Splitrail demonstrates. Consider researching tools like Neo4j Bloom (graph visualization), Grafana (time-series dashboards), or Obsidian (knowledge graph UI) for those specific needs.

## Sources Consulted

- `README.md`: Project overview, feature list, supported tools
- `Cargo.toml`: Full dependency graph
- `AGENTS.md`: Architecture documentation
- `CHANGELOG.md`: Version history (v1.0.0 through v3.3.5)
- `src/main.rs`: Entry point, CLI args, analyzer registration, startup flow
- `src/tui.rs` (2,259 lines): Full TUI implementation (layout, rendering, input handling)
- `src/tui/logic.rs`: TUI business logic (aggregation, date matching)
- `src/types.rs` (1,070 lines): Core data model (CompactDate, ModelCounts, Stats, etc.)
- `src/models.rs` (1,394 lines): Model pricing database
- `src/analyzer.rs` (1,267 lines): Pluggable analyzer trait and registry
- `src/watcher.rs` (563 lines): File watching and real-time stats management
- `src/mcp/server.rs`: MCP server implementation with 6 tools + 2 resources
- `src/mcp/types.rs`: MCP request/response types
- `src/upload.rs`: Cloud upload with chunking and retry
- `vscode-splitrail/package.json`: Extension manifest and configuration
- `vscode-splitrail/src/extension.ts`: Extension activation, status bar, file watching
- `vscode-splitrail/src/dashboardView.ts`: Webview HTML/CSS/JS dashboard
- `vscode-splitrail/src/usageView.ts`: Data types and tree view provider
- `screenshots/cloud.png`: Cloud dashboard UI (visual inspection)
- `screenshots/extension.png`: VS Code extension UI (visual inspection)
- `splitrail.dev`: Cloud web app (WebFetch analysis)

## Open Questions

1. **Splitrail Cloud internals**: The cloud dashboard is closed-source. Its full component architecture, charting library choices, and real-time update mechanism are not inspectable from this repo.
2. **Leaderboard implementation**: The cloud has a leaderboard feature visible in the UI. The data model and ranking algorithm are not in the open-source repo.
3. **Authentication flow**: How the cloud handles user accounts and API token provisioning is not documented in the OSS repo.
4. **Future roadmap**: The "Recent Projects" card in the VS Code extension says "coming in a future update." Whether Splitrail plans to add project-level analytics or richer visualizations is unknown.
