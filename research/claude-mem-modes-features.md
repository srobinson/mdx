---
title: "Claude-Mem Modes, Plugin & Advanced Features Analysis"
category: research
tags: [claude-mem, modes, plugin, endless-mode, ragtime, openclaw]
created: 2026-02-28
---

# Claude-Mem Modes, Plugin & Advanced Features Analysis

Comprehensive competitive intelligence analysis of claude-mem v10.5.2 by Alex Newman (thedotmack). Licensed AGPL-3.0 (core) with PolyForm Noncommercial for ragtime module. Repository: `https://github.com/thedotmack/claude-mem`.

---

## 1. Modes System

### Overview

Modes define how the **observer agent** (a secondary Claude instance) processes and records observations from a primary Claude Code session. There are **34 mode files** in `plugin/modes/`:

- `code.json` -- Base English mode (the canonical definition, ~125 lines)
- `code--chill.json` -- Reduced-verbosity variant
- `email-investigation.json` -- Completely different domain (fraud/email analysis)
- **30 language translations** -- `code--{lang}.json` for ar, bn, cs, da, de, el, es, fi, fr, he, hi, hu, id, it, ja, ko, nl, no, pl, pt-br, ro, ru, sv, th, tr, uk, ur, vi, zh

### Mode Architecture

Each mode is a JSON file with this structure:

```json
{
  "name": "Code Development",
  "description": "Software development and engineering work",
  "version": "1.0.0",
  "observation_types": [...],
  "observation_concepts": [...],
  "prompts": { ... }
}
```

The mode is selected via `CLAUDE_MEM_MODE` setting (default: `code`). The worker loads the mode definition and uses it to construct prompts for the observer agent.

### Base Code Mode: Observation Types (6)

| ID          | Label     | Description                                | Emoji         |
| ----------- | --------- | ------------------------------------------ | ------------- |
| `bugfix`    | Bug Fix   | Something was broken, now fixed            | Red circle    |
| `feature`   | Feature   | New capability or functionality added      | Purple circle |
| `refactor`  | Refactor  | Code restructured, behavior unchanged      | Arrows        |
| `change`    | Change    | Generic modification (docs, config, misc)  | Check         |
| `discovery` | Discovery | Learning about existing system             | Blue circle   |
| `decision`  | Decision  | Architectural/design choice with rationale | Scale         |

### Base Code Mode: Observation Concepts (7)

| ID                 | Label            | Description              |
| ------------------ | ---------------- | ------------------------ |
| `how-it-works`     | How It Works     | Understanding mechanisms |
| `why-it-exists`    | Why It Exists    | Purpose or rationale     |
| `what-changed`     | What Changed     | Modifications made       |
| `problem-solution` | Problem-Solution | Issues and their fixes   |
| `gotcha`           | Gotcha           | Traps or edge cases      |
| `pattern`          | Pattern          | Reusable approach        |
| `trade-off`        | Trade-Off        | Pros/cons of a decision  |

### Prompts Object (Core of Mode Definition)

The `prompts` object contains **~25 named prompt fragments** that are assembled by the worker to construct the observer agent's system prompt. Key fragments:

- **`system_identity`** -- Establishes role: "You are Claude-Mem, a specialized observer tool for creating searchable memory FOR FUTURE SESSIONS."
- **`spatial_awareness`** -- Tells observer about working directories and project context
- **`observer_role`** -- Defines that this is monitoring a DIFFERENT session happening live
- **`recording_focus`** -- What to capture (deliverables, capabilities, technical domains)
- **`skip_guidance`** -- What to skip (empty status checks, package installs, routine file listings)
- **`type_guidance`** -- Constrains observation type selection to the 6 types
- **`concept_guidance`** -- Constrains concept selection to the 7 concepts
- **`field_guidance`** -- How to write facts (concise, no pronouns, include specifics)
- **`output_format_header`** / **`format_examples`** -- XML output format specification
- **`footer`** -- Final instruction reinforcing role boundaries

Summary-specific prompts:

- **`summary_instruction`** -- How to write progress summaries (investigated, learned, completed, next_steps)
- **`summary_context_label`** / **`summary_format_instruction`** / **`summary_footer`**

XML placeholders (templates for the XML structure):

- `xml_title_placeholder`, `xml_subtitle_placeholder`, `xml_fact_placeholder`, `xml_narrative_placeholder`, `xml_concept_placeholder`, `xml_file_placeholder`
- `xml_summary_request_placeholder`, `xml_summary_investigated_placeholder`, `xml_summary_learned_placeholder`, `xml_summary_completed_placeholder`, `xml_summary_next_steps_placeholder`, `xml_summary_notes_placeholder`

Session management headers:

- `header_memory_start`, `header_memory_continued`, `header_summary_checkpoint`
- `continuation_greeting`, `continuation_instruction`

### Chill Mode Variant

`code--chill.json` overrides only two prompts from the base mode:

1. **`recording_focus`** -- "SELECTIVE MODE" -- Only records work that "would be painful to rediscover". Skips obvious implementations.
2. **`skip_guidance`** -- Much more liberal skipping. "When in doubt, skip it. Less is more."

This is a **partial override pattern** -- the mode only specifies the fields it changes, inheriting the rest from the base `code.json`.

### Language Translation Pattern

Each `code--{lang}.json` overrides these prompt fragments:

- `footer` -- Adds `LANGUAGE REQUIREMENTS: Please write the observation data in {language_name}`
- All `xml_*_placeholder` fields -- Translated to target language
- `continuation_instruction` -- Adds language requirement
- `summary_footer` -- Adds language requirement for summaries

The translation only affects the observer agent's OUTPUT language. The system prompts and structural instructions remain in English.

### Email Investigation Mode (Completely Different Domain)

`email-investigation.json` is a full mode definition (not a partial override) designed for analyzing email fraud. It redefines:

**Observation Types (6, completely different):**

| ID               | Label            | Description                                  |
| ---------------- | ---------------- | -------------------------------------------- |
| `entity`         | Entity Discovery | New person, organization, or email address   |
| `relationship`   | Relationship     | Connection between entities                  |
| `timeline-event` | Timeline Event   | Time-stamped event in communication sequence |
| `evidence`       | Evidence         | Supporting documentation or proof            |
| `anomaly`        | Anomaly          | Suspicious pattern or irregularity           |
| `conclusion`     | Conclusion       | Investigative finding                        |

**Observation Concepts (6, completely different):**

| ID              | Label         | Description                 |
| --------------- | ------------- | --------------------------- |
| `who`           | Who           | People and organizations    |
| `when`          | When          | Timing and sequence         |
| `what-happened` | What Happened | Events and communications   |
| `motive`        | Motive        | Intent or purpose           |
| `red-flag`      | Red Flag      | Warning signs of fraud      |
| `corroboration` | Corroboration | Evidence supporting a claim |

The mode rewrites ALL prompt fragments to investigation-focused language. Key difference: **"Create AT LEAST 1 observation per tool use"** and demands granular, atomic observations (one email = 3-5 observations).

### Key Design Insight

Modes are a **prompt configuration system**, not a code plugin system. They define:

1. The taxonomy (observation types + concepts)
2. The observer agent's behavior (what to record, what to skip)
3. The output language and format
4. The session management headers

The worker dynamically loads modes at runtime and assembles them into agent system prompts.

---

## 2. Plugin Architecture

### Top-Level Structure

```
claude-mem/
  .claude-plugin/         # Top-level plugin manifest (for plugin marketplace)
    plugin.json           # { name, version, description, author, repository, license }
    CLAUDE.md             # Dynamic context (recent observations table)
  plugin/                 # Built plugin (distributed artifact)
    .claude-plugin/       # Inner manifest (installed plugin identity)
      plugin.json         # Same schema as top-level
      CLAUDE.md           # Dynamic context for this scope
    .mcp.json             # MCP server registration
    hooks/                # Hook definitions
      hooks.json          # Claude Code hook mappings
      CLAUDE.md           # Dynamic context
    modes/                # 34 mode JSON files
    skills/               # 4 skill definitions
    scripts/              # Built JS (worker, hooks, CLI, MCP server)
    package.json          # Runtime dependencies (tree-sitter parsers)
    ui/                   # Built viewer UI
    CLAUDE.md             # Dynamic context
  src/                    # TypeScript source
  package.json            # Root package (v10.5.2)
```

### Plugin Manifest (.claude-plugin/plugin.json)

```json
{
  "name": "claude-mem",
  "version": "10.5.2",
  "description": "Persistent memory system for Claude Code",
  "author": { "name": "Alex Newman" },
  "repository": "https://github.com/thedotmack/claude-mem",
  "license": "AGPL-3.0",
  "keywords": ["memory", "context", "persistence", "hooks", "mcp"]
}
```

### MCP Server Registration (plugin/.mcp.json)

```json
{
  "mcpServers": {
    "mcp-search": {
      "type": "stdio",
      "command": "${CLAUDE_PLUGIN_ROOT}/scripts/mcp-server.cjs"
    }
  }
}
```

Uses `${CLAUDE_PLUGIN_ROOT}` variable for path resolution. Single MCP server providing search, timeline, and get_observations tools.

### Hook Definitions (plugin/hooks/hooks.json)

5 lifecycle hooks mapping Claude Code events to worker commands:

| Hook             | Event                     | Command                                                                         | Timeout    |
| ---------------- | ------------------------- | ------------------------------------------------------------------------------- | ---------- |
| Setup            | `*`                       | `setup.sh`                                                                      | 300s       |
| SessionStart     | `startup\|clear\|compact` | `smart-install.js` then `worker-service.cjs start` + `hook claude-code context` | 60s        |
| UserPromptSubmit | `*`                       | `worker-service.cjs hook claude-code session-init`                              | 60s        |
| PostToolUse      | `*`                       | `worker-service.cjs hook claude-code observation`                               | 120s       |
| Stop             | `*`                       | `worker-service.cjs hook claude-code summarize` then `session-complete`         | 120s / 30s |

All hook commands use a pattern: `_R="${CLAUDE_PLUGIN_ROOT}"; [ -z "$_R" ] && _R="$HOME/.claude/plugins/marketplaces/thedotmack/plugin"; node "$_R/scripts/bun-runner.js" "$_R/scripts/worker-service.cjs" <subcommand>`

This uses `bun-runner.js` as an intermediary that handles Bun/Node.js runtime detection and fallback.

### Hook Response Protocol

From `src/hooks/hook-response.ts`:

```typescript
export const STANDARD_HOOK_RESPONSE = JSON.stringify({
  continue: true,
  suppressOutput: true,
});
```

Hooks return JSON with `continue: true` to allow the primary session to proceed. `suppressOutput: true` prevents hook output from appearing in the conversation.

The SessionStart context hook is special -- it constructs a response with `hookSpecificOutput` containing the injected context (recent observations and summaries).

### Exit Code Strategy

- **Exit 0**: Success or graceful shutdown
- **Exit 1**: Non-blocking error (stderr shown to user, continues)
- **Exit 2**: Blocking error (stderr fed to Claude for processing)

Philosophy: Worker/hook errors exit with code 0 to prevent Windows Terminal tab accumulation.

### Built Scripts (plugin/scripts/)

| File                    | Size  | Purpose                             |
| ----------------------- | ----- | ----------------------------------- |
| `claude-mem`            | 63MB  | Compiled binary (native)            |
| `worker-service.cjs`    | 1.9MB | Worker service + CLI (Bun runtime)  |
| `mcp-server.cjs`        | 358KB | MCP server (stdio transport)        |
| `context-generator.cjs` | 73KB  | Context injection builder           |
| `smart-install.js`      | 19KB  | Dependency auto-installer (Bun, uv) |
| `bun-runner.js`         | 6KB   | Bun/Node.js runtime adapter         |
| `worker-cli.js`         | 14KB  | CLI interface                       |
| `worker-wrapper.cjs`    | 2KB   | Worker process wrapper              |
| `statusline-counts.js`  | 2KB   | Status line counter                 |

### Plugin Dependencies (plugin/package.json)

Runtime dependencies are exclusively **tree-sitter parsers** for the smart-explore skill:

- tree-sitter-cli, tree-sitter-c, tree-sitter-cpp, tree-sitter-go, tree-sitter-java, tree-sitter-javascript, tree-sitter-python, tree-sitter-ruby, tree-sitter-rust, tree-sitter-typescript

### Root Package Dependencies

Key dependencies:

- `@anthropic-ai/claude-agent-sdk` -- For spawning observer agents and the Ragtime batch processor
- `@modelcontextprotocol/sdk` -- MCP server implementation
- `express` -- Worker service HTTP server (port 37777)
- `react` + `react-dom` -- Viewer UI
- `handlebars` -- Template engine (for context generation)
- `yaml` -- Configuration parsing
- `zod-to-json-schema` -- Schema generation for MCP tools
- `dompurify` -- HTML sanitization in viewer
- `ansi-to-html` -- Terminal output rendering in viewer

### npm Package Exports

```json
{
  ".": { "types": "./dist/index.d.ts", "import": "./dist/index.js" },
  "./sdk": {
    "types": "./dist/sdk/index.d.ts",
    "import": "./dist/sdk/index.js"
  },
  "./modes/*": "./plugin/modes/*"
}
```

Modes are publicly accessible via npm: `import mode from 'claude-mem/modes/code.json'`.

### Settings Architecture

Settings stored in `~/.claude-mem/settings.json`. Key settings:

| Setting                           | Default                                                             | Purpose                              |
| --------------------------------- | ------------------------------------------------------------------- | ------------------------------------ |
| `CLAUDE_MEM_MODEL`                | `sonnet`                                                            | AI model for observer agent          |
| `CLAUDE_MEM_PROVIDER`             | `claude`                                                            | Provider: claude, gemini, openrouter |
| `CLAUDE_MEM_MODE`                 | `code`                                                              | Active mode profile                  |
| `CLAUDE_MEM_CONTEXT_OBSERVATIONS` | `50`                                                                | Number of observations to inject     |
| `CLAUDE_MEM_WORKER_PORT`          | `37777`                                                             | Worker HTTP port                     |
| `CLAUDE_MEM_SKIP_TOOLS`           | `ListMcpResourcesTool,SlashCommand,Skill,TodoWrite,AskUserQuestion` | Tools excluded from observation      |

Multi-provider support: Claude (default), Gemini (free tier with 1500 req/day), OpenRouter (100+ models including free ones).

---

## 3. Skills System

### 3.1 mem-search

**File:** `plugin/skills/mem-search/SKILL.md`

A 3-layer search workflow for querying past work across sessions:

**Layer 1 -- Search (Index):**

```
search(query="authentication", limit=20, project="my-project")
```

Returns: Table with IDs, timestamps, types, titles (~50-100 tokens/result). Supports filters: `type` (observations/sessions/prompts), `obs_type` (bugfix/feature/decision/discovery/change), `dateStart`, `dateEnd`, `offset`, `orderBy`.

**Layer 2 -- Timeline (Context):**

```
timeline(anchor=11131, depth_before=3, depth_after=3, project="my-project")
```

Returns chronological items around an anchor point. Can auto-find anchor from query.

**Layer 3 -- Fetch (Full Details):**

```
get_observations(ids=[11131, 10942])
```

Returns complete observation objects with title, subtitle, narrative, facts, concepts, files (~500-1000 tokens each).

**Design principle:** "NEVER fetch full details without filtering first. 10x token savings."

### 3.2 make-plan

**File:** `plugin/skills/make-plan/SKILL.md`

Orchestrator skill for creating phased implementation plans. Key elements:

- **Delegation Model:** Subagents gather facts; orchestrator synthesizes
- **Subagent Reporting Contract (MANDATORY):** Each subagent must report sources, findings, snippet locations, confidence + gaps. "Reject and redeploy if conclusions without sources."
- **Phase 0: Documentation Discovery (ALWAYS FIRST):** Deploy subagents to find actual APIs, create "Allowed APIs" list, note anti-patterns
- **Each Phase:** What to implement (frame as COPY from docs), documentation references, verification checklist, anti-pattern guards
- **Final Phase:** Verify all implementations match docs, grep for bad patterns, run tests

### 3.3 do

**File:** `plugin/skills/do/SKILL.md`

Execution orchestrator for running phased plans:

- **Rules:** One objective per subagent, require evidence, don't advance until confirmed
- **Per-Phase:** Deploy Implementation subagent (COPY patterns, cite docs, STOP if API seems missing)
- **Post-Phase:** Deploy 4 separate verification subagents: Verification, Anti-pattern, Code Quality, Commit
- **Between Phases:** Deploy Branch/Sync subagent (push to working branch, prepare handoff)

### 3.4 smart-explore

**File:** `plugin/skills/smart-explore/SKILL.md`

Token-optimized structural code search using tree-sitter AST parsing. **Overrides default exploration behavior** while active.

3-layer workflow:

1. **smart_search(query, path)** -- Discovers files + ranked symbols with signatures across directories (~2-6k tokens)
2. **smart_outline(file_path)** -- Structural skeleton of one file (~1-2k tokens)
3. **smart_unfold(file_path, symbol_name)** -- Full source of one symbol (~400-2,100 tokens)

**Token economics comparison:**

| Approach         | Tokens         |
| ---------------- | -------------- |
| smart_outline    | ~1,000-2,000   |
| smart_unfold     | ~400-2,100     |
| smart_search     | ~2,000-6,000   |
| search + unfold  | ~3,000-8,000   |
| Read (full file) | ~12,000+       |
| Explore agent    | ~39,000-59,000 |

Claims **4-8x savings** on file understanding, **11-18x savings** vs explore agents.

---

## 4. Ragtime (PolyForm Noncommercial)

**Directory:** `ragtime/`
**License:** PolyForm Noncommercial 1.0.0 (distinct from main AGPL-3.0)

### What It Is

An **email investigation batch processor** that feeds email corpus files through Claude using the `email-investigation` mode. It demonstrates claude-mem's architecture being repurposed from code development to investigative analysis.

### Architecture

```typescript
import { query } from "@anthropic-ai/claude-agent-sdk";
```

Uses the **Claude Agent SDK** (`query()` function) to spawn individual sessions. Each email file gets a NEW session -- context is managed by claude-mem's context injection hook, not by conversation continuation.

### Processing Loop

1. Sets `CLAUDE_MEM_MODE=email-investigation`
2. Reads `.md` files from corpus directory, sorted numerically
3. For each file: spawns NEW Claude session via Agent SDK with claude-mem plugin attached
4. Claude reads the file and analyzes entities, relationships, timeline events
5. Claude-mem hooks fire: context injection provides past observations, observer records new ones
6. Waits for worker queue to empty before next file
7. Periodic transcript cleanup (every 10 files) prevents buildup

### Configuration (Environment Variables)

| Variable                     | Default                   | Purpose                         |
| ---------------------------- | ------------------------- | ------------------------------- |
| `RAGTIME_CORPUS_PATH`        | `./datasets/epstein-mode` | Path to email markdown files    |
| `RAGTIME_PLUGIN_PATH`        | `./plugin`                | Path to claude-mem plugin       |
| `CLAUDE_MEM_WORKER_PORT`     | `37777`                   | Worker port                     |
| `RAGTIME_TRANSCRIPT_MAX_AGE` | `24`                      | Hours before transcript cleanup |
| `RAGTIME_PROJECT_NAME`       | `ragtime-investigation`   | Project name for grouping       |
| `RAGTIME_FILE_LIMIT`         | `0`                       | Max files to process (0=all)    |
| `RAGTIME_SESSION_DELAY`      | `2000`                    | Delay between sessions (ms)     |

### Significance

Ragtime proves claude-mem's mode system is general-purpose -- the same observation/memory infrastructure supports completely different domains by swapping the mode configuration. The "epstein-mode" dataset reference suggests it was designed for analyzing the Epstein document corpus.

---

## 5. Endless Mode (Beta)

### Concept

A **biomimetic memory architecture** solving Claude's context window exhaustion problem. Transforms O(N^2) context scaling into O(N) linear complexity.

### The Problem

In standard Claude Code sessions:

- Tool outputs accumulate in context window (1-10k+ tokens each)
- After ~50 tool uses, context fills (~200k tokens)
- Claude re-synthesizes ALL previous outputs on every response (O(N^2))

### How It Works

**Two-Tier Memory System:**

```
Working Memory (Context Window):
  -> Compressed observations only (~500 tokens each)
  -> Fast, efficient, manageable

Archive Memory (Transcript File):
  -> Full tool outputs preserved on disk
  -> Perfect recall, searchable
```

After each tool use:

1. Pre-Tool-Use hook tracks tool execution start (sends `tool_use_id`)
2. Tool completes, PostToolUse hook **BLOCKS** (up to 110s timeout)
3. Worker processes tool output via SDK agent, generates compressed observation
4. Event-driven wait mechanism (no polling) -- `SessionManager.waitForNextObservation()`
5. Compressed observation injected back into context
6. Transcript on disk is transformed -- full tool output replaced with compressed version
7. Context window usage reduced

### Configuration

```json
{
  "CLAUDE_MEM_ENDLESS_MODE": "false",
  "CLAUDE_MEM_ENDLESS_WAIT_TIMEOUT_MS": "90000"
}
```

### Implementation Status

- **Branch:** `beta/endless-mode` (not in stable)
- **Status:** Architecturally complete, functional but experimental
- **Key Components:** Pre-Tool-Use Hook, Save Hook (blocking), SessionManager.waitForNextObservation(), SDKAgent, `tool_use_id` database column
- **Known Issues:** Slower than standard mode (blocking adds latency), no production validation, no benchmarks, no comprehensive tests

### Token Economics Calculator

`scripts/endless-mode-token-calculator.js` simulates savings using real observation data. Key math:

- **Without Endless Mode:** Each continuation carries ALL previous full tool outputs. Cumulative context grows by `originalToolSize` per tool use. Continuation cost = sum of all previous outputs.
- **With Endless Mode:** Each continuation carries compressed observations. Cumulative context grows by `compressedSize` per tool use. Discovery cost is identical (still need to create observations).

The calculator uses a 2x multiplier heuristic: original content = 2x discovery tokens. Characters to tokens: 1 token ~ 4 characters.

### Anthropic Scale Projection

The calculator projects impact at 100k active users, 10 sessions/week:

- Significant weekly token savings
- Claims potential to serve more users with same infrastructure

---

## 6. Conductor System

**File:** `conductor.json`

Minimal configuration:

```json
{
  "scripts": {
    "setup": "cp ../settings.local.json .claude/settings.local.json && npm install",
    "run": "npm run build-and-sync"
  }
}
```

The conductor is a **development automation** system. It defines two scripts:

- `setup` -- Copies local settings and installs dependencies
- `run` -- Triggers `build-and-sync` which builds hooks, syncs to marketplace directory, and restarts the worker

This appears to be a lightweight task runner for the development workflow, not a production orchestration system.

---

## 7. OpenClaw Gateway Integration

**Directory:** `openclaw/`

### What OpenClaw Is

OpenClaw is a **multi-channel messaging gateway** that runs AI agents and connects them to messaging platforms (Telegram, Discord, Slack, Signal, WhatsApp, LINE, iMessage).

### Plugin Manifest (openclaw.plugin.json)

```json
{
  "id": "claude-mem",
  "name": "Claude-Mem (Persistent Memory)",
  "kind": "memory",
  "version": "10.4.1",
  "skills": ["skills/make-plan", "skills/do"],
  "configSchema": { ... }
}
```

### Plugin Config Schema

| Field                      | Type    | Default      | Purpose                                                    |
| -------------------------- | ------- | ------------ | ---------------------------------------------------------- |
| `syncMemoryFile`           | boolean | `true`       | Write MEMORY.md to agent workspaces                        |
| `workerPort`               | number  | `37777`      | Worker service port                                        |
| `project`                  | string  | `"openclaw"` | Project name for scoping observations                      |
| `observationFeed.enabled`  | boolean | `false`      | Stream observations to messaging channel                   |
| `observationFeed.channel`  | string  | --           | Channel type (telegram/discord/slack/signal/whatsapp/line) |
| `observationFeed.to`       | string  | --           | Target chat/channel/user ID                                |
| `observationFeed.botToken` | string  | --           | Optional dedicated Telegram bot token                      |
| `observationFeed.emojis`   | object  | --           | Per-agent emoji customization                              |

### Plugin Architecture (src/index.ts -- 1016 lines)

The OpenClaw plugin registers:

**Event Handlers:**

| Event                 | Behavior                                                 |
| --------------------- | -------------------------------------------------------- |
| `session_start`       | Initialize claude-mem session                            |
| `message_received`    | Capture inbound user prompts from channels               |
| `after_compaction`    | Re-init session after context compaction                 |
| `before_agent_start`  | Init session + sync MEMORY.md + track workspace          |
| `tool_result_persist` | Record observation (fire-and-forget) + re-sync MEMORY.md |
| `agent_end`           | Summarize session + complete                             |
| `session_end`         | Clean up session tracking                                |
| `gateway_start`       | Reset all session tracking                               |

**Registered Commands:**

| Command                | Purpose                        |
| ---------------------- | ------------------------------ |
| `/claude_mem_status`   | Worker health check            |
| `/claude_mem_feed`     | Observation feed status/toggle |
| `/claude-mem-search`   | Search observations by query   |
| `/claude-mem-recent`   | Show recent context snapshot   |
| `/claude-mem-timeline` | Timeline around best match     |

**SSE Observation Feed Service:**

Connects to worker's `/stream` SSE endpoint and forwards `new_observation` events to configured messaging channels. Features:

- Auto-reconnect with exponential backoff (1s to 30s max)
- 1MB SSE buffer limit
- Per-agent emoji assignment (deterministic hash of agentId)
- Multi-channel support via `CHANNEL_SEND_MAP` (7 channels)
- Direct Telegram bot token bypass option

**MEMORY.md Live Sync:**

The plugin writes `MEMORY.md` to each agent's workspace directory, updated:

- Before each agent run (provides context)
- After every tool use (keeps context current)
- Updates are fire-and-forget (non-blocking)

### Install Script

`openclaw/install.sh` (63KB) -- Full automated installer handling:

- Dependency checks (Bun, uv)
- Plugin installation
- Memory slot configuration
- AI provider setup (Claude Max Plan, Gemini, OpenRouter)
- Worker startup
- Optional observation feed configuration
- Supports `--non-interactive`, `--upgrade`, `--provider=`, `--api-key=` flags

---

## 8. Cursor IDE Integration

**Directory:** `cursor-hooks/`

### Architecture

Bridges Cursor's hook system to claude-mem's worker API using shell scripts.

### Hook Mappings (hooks.json)

```json
{
  "beforeSubmitPrompt": ["session-init.sh", "context-inject.sh"],
  "afterMCPExecution": ["save-observation.sh"],
  "afterShellExecution": ["save-observation.sh"],
  "afterFileEdit": ["save-file-edit.sh"],
  "stop": ["session-summary.sh"]
}
```

### Context Injection Strategy

Context is injected via Cursor's **Rules** system, not via hook output:

1. Install creates initial context file at `.cursor/rules/claude-mem-context.mdc`
2. File has `alwaysApply: true` frontmatter -- included in ALL chat sessions
3. Context refreshed at **3 points**: before prompt, after summary (worker auto-update), after session ends

```markdown
---
alwaysApply: true
description: "Claude-mem context from past sessions (auto-updated)"
---

# Memory Context from Past Sessions

[context from claude-mem]
```

### Project Registry

`~/.claude-mem/cursor-projects.json` -- Registered projects get automatic context file updates from the worker, even when observations come from Claude Code or other IDEs.

### Comparison with Claude Code

| Feature             | Claude Code                        | Cursor                                                  |
| ------------------- | ---------------------------------- | ------------------------------------------------------- |
| Context injection   | `additionalContext` in hook output | Auto-updated rules file                                 |
| Injection timing    | Immediate (same prompt)            | Before prompt + after summary + after session           |
| Session Summary     | Stop hook with transcript          | Stop hook (no transcript)                               |
| Observation Capture | PostToolUse hook                   | afterMCPExecution + afterShellExecution + afterFileEdit |

### Installation

```bash
# Interactive setup
bun run cursor:setup

# Or manual
claude-mem cursor install user    # Global
claude-mem cursor install         # Per-project
```

---

## 9. Transcript Watching

**File:** `transcript-watch.example.json`

### What It Is

A system for watching **external AI tool transcript files** (JSONL) and feeding them into claude-mem's observation pipeline. This extends claude-mem beyond Claude Code to any tool that writes structured transcripts.

### Configuration

```json
{
  "version": 1,
  "schemas": { "codex": { ... } },
  "watches": [{ "name": "codex", "path": "~/.codex/sessions/**/*.jsonl", ... }],
  "stateFile": "~/.claude-mem/transcript-watch-state.json"
}
```

### Schema Definition (Codex Example)

Schemas define how to parse JSONL events. Each event has:

- **name** -- Event identifier
- **match** -- JSON path matching rule (field path + equals/in condition)
- **action** -- What to do: `session_context`, `session_init`, `assistant_message`, `tool_use`, `tool_result`, `session_end`
- **fields** -- Field mappings from JSONL paths to claude-mem fields

**Event types defined for Codex:**

| Event             | Match                                                                | Action            | Fields                      |
| ----------------- | -------------------------------------------------------------------- | ----------------- | --------------------------- |
| session-meta      | `type == "session_meta"`                                             | session_context   | sessionId, cwd              |
| turn-context      | `type == "turn_context"`                                             | session_context   | cwd                         |
| user-message      | `payload.type == "user_message"`                                     | session_init      | prompt                      |
| assistant-message | `payload.type == "agent_message"`                                    | assistant_message | message                     |
| tool-use          | `payload.type in [function_call, custom_tool_call, web_search_call]` | tool_use          | toolId, toolName, toolInput |
| tool-result       | `payload.type in [function_call_output, custom_tool_call_output]`    | tool_result       | toolId, toolResponse        |
| session-end       | `payload.type == "turn_aborted"`                                     | session_end       | --                          |

### Field Resolution

Supports advanced field resolution:

- Direct path: `"payload.message"`
- Coalesce (first non-null): `{ "coalesce": ["payload.arguments", "payload.input", "payload.action"] }`
- Static value: `{ "value": "web_search" }`

### Watch Configuration

```json
{
  "name": "codex",
  "path": "~/.codex/sessions/**/*.jsonl",
  "schema": "codex",
  "startAtEnd": true,
  "context": {
    "mode": "agents",
    "path": "~/.codex/AGENTS.md",
    "updateOn": ["session_start", "session_end"]
  }
}
```

- `startAtEnd: true` -- Only process new events, don't replay history
- `context` -- Optional context injection back into the watched tool's config file
- `stateFile` -- Persists watch position across restarts

### Significance

This is a **universal adapter** -- any AI tool that writes structured JSONL transcripts can be observed by claude-mem. The schema system is declarative and extensible, making it straightforward to add support for new tools beyond Codex.

---

## 10. Viewer UI

**Directory:** `src/ui/viewer/`

### Architecture

React 18 single-page application served from `http://localhost:37777`. Built to `plugin/ui/viewer.html` (single-file template).

### Components

| Component                  | Purpose                                                          |
| -------------------------- | ---------------------------------------------------------------- |
| `App.tsx`                  | Root component, state management, SSE + pagination merge         |
| `Header.tsx`               | Connection status, project filter, theme toggle, context preview |
| `Feed.tsx`                 | Chronological feed of observations/summaries/prompts             |
| `ObservationCard.tsx`      | Individual observation display                                   |
| `SummaryCard.tsx`          | Session summary display                                          |
| `PromptCard.tsx`           | User prompt display                                              |
| `ContextSettingsModal.tsx` | Settings editor (21KB -- largest component)                      |
| `LogsModal.tsx`            | Console/logs drawer (16KB)                                       |
| `ErrorBoundary.tsx`        | Error boundary wrapper                                           |
| `GitHubStarsButton.tsx`    | GitHub stars social proof                                        |
| `TerminalPreview.tsx`      | Terminal output renderer (ANSI to HTML)                          |
| `ScrollToTop.tsx`          | Scroll-to-top button                                             |
| `ThemeToggle.tsx`          | Light/dark theme toggle                                          |

### Custom Hooks

| Hook                 | Purpose                                                                                                                   |
| -------------------- | ------------------------------------------------------------------------------------------------------------------------- |
| `useSSE`             | EventSource connection to `/stream`, handles initial_load/new_observation/new_summary/new_prompt/processing_status events |
| `useSettings`        | Settings CRUD via worker API                                                                                              |
| `useStats`           | Worker and database statistics                                                                                            |
| `usePagination`      | Paginated data loading with project filter                                                                                |
| `useTheme`           | System/manual theme preference with CSS class toggling                                                                    |
| `useContextPreview`  | Context preview modal state                                                                                               |
| `useGitHubStars`     | GitHub API star count fetcher                                                                                             |
| `useSpinningFavicon` | Animated favicon during processing                                                                                        |

### Data Types

```typescript
interface Observation {
  id: number;
  memory_session_id: string;
  project: string;
  type: string; // bugfix, feature, refactor, change, discovery, decision
  title: string | null;
  subtitle: string | null;
  narrative: string | null;
  text: string | null;
  facts: string | null;
  concepts: string | null;
  files_read: string | null;
  files_modified: string | null;
  prompt_number: number | null;
  created_at: string;
  created_at_epoch: number;
}

interface Summary {
  id: number;
  session_id: string;
  project: string;
  request?: string;
  investigated?: string;
  learned?: string;
  completed?: string;
  next_steps?: string;
  created_at_epoch: number;
}

interface Settings {
  CLAUDE_MEM_MODEL: string;
  CLAUDE_MEM_PROVIDER?: string;
  CLAUDE_MEM_CONTEXT_OBSERVATIONS: string;
  CLAUDE_MEM_WORKER_PORT: string;
  // ... Gemini, OpenRouter, token economics, display settings
}
```

### SSE Stream Events

| Event Type          | Payload                                            |
| ------------------- | -------------------------------------------------- |
| `initial_load`      | observations[], summaries[], prompts[], projects[] |
| `new_observation`   | Single observation                                 |
| `new_summary`       | Single summary                                     |
| `new_prompt`        | Single prompt                                      |
| `processing_status` | isProcessing, queueDepth                           |

### Data Merge Strategy

When no project filter: merge SSE live data with paginated API data, deduplicate by ID. When filtered: only use paginated data (API handles filtering).

---

## 11. Competitive Intelligence Summary for Helioy-Plugins

### What Claude-Mem Does Well

1. **Mode system is elegant** -- JSON configuration for observer behavior, supports completely different domains (code vs email investigation), language translations are partial overrides
2. **Multi-integration** -- Same worker serves Claude Code (hooks), Cursor (shell scripts + rules files), OpenClaw (plugin API + SSE + messaging), and any JSONL-writing tool (transcript watcher)
3. **Token-aware design** -- 3-layer search workflow (index -> timeline -> fetch), smart-explore with tree-sitter AST parsing, explicit token budgets documented
4. **Observation taxonomy** -- Types + concepts as orthogonal dimensions, constrained to known values
5. **Viewer UI** -- Real-time SSE feed, project filtering, settings management, theme toggle
6. **Multi-provider AI** -- Claude (default), Gemini (free tier), OpenRouter (100+ models)
7. **Make-plan/do orchestration** -- Subagent delegation with mandatory reporting contracts

### Architectural Differences from Helioy

| Aspect        | Claude-Mem                           | Helioy (attention-matters)               |
| ------------- | ------------------------------------ | ---------------------------------------- |
| Memory model  | SQLite + Chroma vectors              | Geometric quaternion memory              |
| Recall        | FTS5 search + vector similarity      | Compose scoring with geometric distance  |
| Observer      | Secondary Claude instance            | am_buffer/am_salient (explicit API)      |
| Cross-project | Project-scoped (separate namespaces) | Unified brain.db (no project boundaries) |
| Mode system   | JSON prompt configuration            | No equivalent (single-purpose)           |
| Protocol      | HTTP API (localhost:37777)           | MCP server (stdio)                       |
| Taxonomy      | Fixed 6 types + 7 concepts           | Free-form (no taxonomy constraints)      |

### Lessons for Helioy-Plugins

1. **Skills as SKILL.md files** -- Simple, effective convention. Our skills directory follows the same pattern.
2. **Hook lifecycle is critical** -- 5 hooks (Setup, SessionStart, UserPromptSubmit, PostToolUse, Stop) cover the full session. Our hooks system should match this coverage.
3. **Context injection timing matters** -- Claude-mem injects at session start + compacts. The Cursor integration shows the challenge of getting fresh context into non-Claude Code editors.
4. **Modes could be valuable** -- Our `.mdx` system serves a similar purpose but modes are more structured. Consider if helioy-plugins needs domain-specific observer configurations.
5. **Transcript watching is powerful** -- The schema-based JSONL adapter pattern could let our tools observe sessions from any AI tool.
6. **OpenClaw integration pattern** -- The SSE observation feed streaming to messaging channels is a compelling feature for visibility into agent work.
7. **Smart-explore's tree-sitter integration** -- 4-8x token savings via AST-based code navigation is a strong value prop. FMM serves a similar purpose but via sidecar metadata rather than runtime parsing.
8. **Endless Mode's blocking hook pattern** -- The concept of synchronous observation injection is architecturally significant but their implementation is still experimental.
