# Research: Claude Code as a Persistent Background Service

> Nancy Research Document 07 -- Claude integration patterns for K8s-native agent orchestration
> Date: 2026-02-14
> Status: Current as of Claude Opus 4.6 / Agent SDK v0.2.39

---

## Executive Summary

Nancy needs Claude (and other LLMs) to function as always-on worker backends within a K8s orchestration layer. This document maps what is **actually shipping today** versus what requires custom engineering.

**The key insight**: Anthropic has converged on the **Claude Agent SDK** as the primary programmatic interface. The CLI (`claude -p`) is now a thin wrapper around the SDK. For Nancy's use case, there are two viable integration paths:

1. **Agent SDK (TypeScript/Python)** -- Full Claude Code capabilities (file ops, bash, MCP, subagents) via a library. Best for replicating what Claude Code does.
2. **Anthropic Messages API (direct HTTP)** -- Raw model access with tool use. Best for multi-model abstraction where Nancy controls the agent loop.

Nancy should pursue **Path 2** (direct API) as the primary integration, with the Agent SDK as an optional "turbo mode" for Claude-specific deep tasks.

---

## 1. Claude Code CLI -- Current Interface (Feb 2026)

### Core Commands

```bash
# Interactive mode
claude

# Non-interactive (headless) -- the "-p" flag
claude -p "Find and fix the bug in auth.py" --allowedTools "Read,Edit,Bash"

# Structured output
claude -p "Summarize this project" --output-format json
claude -p "Extract functions" --output-format json --json-schema '{"type":"object",...}'

# Streaming output (token-by-token)
claude -p "Explain recursion" --output-format stream-json --verbose --include-partial-messages

# Session management
claude -p "Start a review" --output-format json | jq -r '.session_id'  # capture session ID
claude -p "Continue the review" --resume "$session_id"
claude -p "Now focus on DB queries" --continue  # continue most recent

# System prompt customization
gh pr diff "$1" | claude -p --append-system-prompt "You are a security engineer." --output-format json
claude -p "task" --system-prompt "Full replacement prompt"

# Tool permissions (prefix matching with trailing space + *)
claude -p "Create a commit" --allowedTools "Bash(git diff *),Bash(git log *),Bash(git commit *)"
```

### What Headless Mode Provides

- Full tool access: Read, Edit, Write, Bash, Glob, Grep, WebFetch, WebSearch, Task (subagents)
- MCP server integration (same as interactive mode)
- Session persistence with `--resume <session_id>` and `--continue`
- JSON schema-constrained output
- Streaming via `stream-json` format
- Custom system prompts (append or replace)

### What It Does NOT Provide

- No daemon/server mode -- each `claude -p` invocation spawns a fresh Node.js process
- No hot process reuse -- ~12s cold start overhead per invocation
- No built-in session pooling
- No native WebSocket/gRPC interface
- Skills and slash commands are interactive-mode only

### Session Storage

Sessions persist to disk at `~/.claude/sessions/`:

- `metadata.json` -- session metadata
- `messages.jsonl` -- conversation history (JSON Lines)
- `context.json` -- context window state
- `tasks.json` -- background task state

Background tasks started with `run_in_background: true` survive across session resume.

**Source**: [Claude Code Headless Docs](https://code.claude.com/docs/en/headless)

---

## 2. Claude Agent SDK (the real API)

The CLI was previously called "headless mode." Anthropic has since shipped proper SDKs that expose the same engine as a library.

### Packages

- **TypeScript**: `@anthropic-ai/claude-agent-sdk` (npm, v0.2.39, 1.9M weekly downloads)
- **Python**: `claude-agent-sdk` (PyPI)
- **Source**: [TS repo](https://github.com/anthropics/claude-agent-sdk-typescript), [Python repo](https://github.com/anthropics/claude-agent-sdk-python)

### Core API

```typescript
import { query } from "@anthropic-ai/claude-agent-sdk";

for await (const message of query({
  prompt: "Find and fix the bug in auth.py",
  options: {
    model: "claude-opus-4-6",
    allowedTools: ["Read", "Edit", "Bash"],
    // Session resumption
    resume: "session-xyz",
    // Fork instead of continuing original
    forkSession: true,
  },
})) {
  if (message.type === "system" && message.subtype === "init") {
    const sessionId = message.session_id; // capture for later resume
  }
  if ("result" in message) console.log(message.result);
}
```

```python
from claude_agent_sdk import query, ClaudeAgentOptions

async for message in query(
    prompt="Find and fix the bug in auth.py",
    options=ClaudeAgentOptions(
        model="claude-opus-4-6",
        allowed_tools=["Read", "Edit", "Bash"],
        resume="session-xyz",
    ),
):
    print(message)
```

### Subagents (Programmatic)

```python
from claude_agent_sdk import query, ClaudeAgentOptions, AgentDefinition

async for message in query(
    prompt="Review the auth module for security issues",
    options=ClaudeAgentOptions(
        allowed_tools=["Read", "Grep", "Glob", "Task"],
        agents={
            "code-reviewer": AgentDefinition(
                description="Expert code review. Use for quality and security reviews.",
                prompt="You are a code review specialist...",
                tools=["Read", "Grep", "Glob"],  # read-only
                model="sonnet",  # cheaper model for this subagent
            ),
            "test-runner": AgentDefinition(
                description="Runs and analyzes test suites.",
                prompt="You are a test execution specialist...",
                tools=["Bash", "Read", "Grep"],
            ),
        },
    ),
):
    pass
```

Key constraints:

- Subagents cannot spawn their own subagents (no infinite nesting)
- Up to 10 concurrent tasks with intelligent queuing
- Each subagent maintains separate context (isolation)
- Subagent transcripts persist independently of main conversation
- Subagents can be resumed by capturing `agentId` from Task tool results

### Session Management

| Feature                 | Details                                                              |
| ----------------------- | -------------------------------------------------------------------- |
| Auto-created session ID | Returned in first `system/init` message                              |
| Resume                  | `resume: "session-id"` in options                                    |
| Fork                    | `forkSession: true` creates new branch from resume point             |
| Storage                 | `~/.claude/sessions/` on disk                                        |
| Compaction              | Main conversation can compact without affecting subagent transcripts |
| Cleanup                 | Auto-cleanup via `cleanupPeriodDays` (default: 30)                   |
| No timeout              | Sessions do not timeout, but use `maxTurns` to prevent loops         |

### Hooks System (14 Lifecycle Events)

Hooks are deterministic triggers that run shell commands, LLM prompts, or subagents at specific lifecycle points.

| Event                | When                      | Can Block?           |
| -------------------- | ------------------------- | -------------------- |
| `SessionStart`       | Session begins or resumes | No                   |
| `UserPromptSubmit`   | User submits prompt       | Yes                  |
| `PreToolUse`         | Before tool executes      | Yes (allow/deny/ask) |
| `PermissionRequest`  | Permission dialog shown   | Yes                  |
| `PostToolUse`        | After tool succeeds       | No (feedback only)   |
| `PostToolUseFailure` | After tool fails          | No (feedback only)   |
| `Notification`       | Notification sent         | No                   |
| `SubagentStart`      | Subagent spawned          | No (inject context)  |
| `SubagentStop`       | Subagent finishes         | Yes                  |
| `Stop`               | Main agent done           | Yes (force continue) |
| `TeammateIdle`       | Team member about to idle | Yes                  |
| `TaskCompleted`      | Task marked complete      | Yes                  |
| `PreCompact`         | Before context compaction | No                   |
| `SessionEnd`         | Session terminates        | No                   |

Hook types:

- `command` -- shell script, receives JSON on stdin, returns JSON on stdout
- `prompt` -- single-turn LLM evaluation (default: Haiku for speed)
- `agent` -- multi-turn subagent with tool access (up to 50 turns)

Hooks can run async (`"async": true`) for non-blocking background work.

Configuration locations (in priority order):

1. Managed policy (org-wide)
2. `~/.claude/settings.json` (user global)
3. `.claude/settings.json` (project, committable)
4. `.claude/settings.local.json` (project, gitignored)
5. Plugin `hooks/hooks.json`
6. Skill/agent frontmatter

**Source**: [Hooks Reference](https://code.claude.com/docs/en/hooks), [SDK Hooks](https://platform.claude.com/docs/en/agent-sdk/hooks)

### The ~12s Cold Start Problem

Each `query()` call spawns a new process. Measured performance:

| Metric                  | Time |
| ----------------------- | ---- |
| 1st query               | ~13s |
| 2nd query (new process) | ~12s |
| 3rd query (new process) | ~12s |
| Direct Messages API     | 1-3s |

**Official solution**: Streaming input mode keeps the subprocess alive between turns. Results:

- Cold start (first message): ~12s
- Warm messages (subsequent): ~2-3s (77% faster)
- Sessions auto-expire after 10 minutes of inactivity

**Source**: [Agent SDK TS Issue #34](https://github.com/anthropics/claude-agent-sdk-typescript/issues/34)

---

## 3. Anthropic Messages API (Direct HTTP)

This is the raw model API -- no agent loop, no file tools, no shell access. You bring your own agent loop.

### Core Request

```bash
curl https://api.anthropic.com/v1/messages \
  -H "x-api-key: $ANTHROPIC_API_KEY" \
  -H "anthropic-version: 2023-06-01" \
  -H "content-type: application/json" \
  -d '{
    "model": "claude-opus-4-6",
    "max_tokens": 4096,
    "messages": [{"role": "user", "content": "Hello"}]
  }'
```

### Key Capabilities

| Feature                     | Status | Notes                                                              |
| --------------------------- | ------ | ------------------------------------------------------------------ |
| Tool use / function calling | GA     | Define tools as JSON schema, Claude returns `tool_use` blocks      |
| Extended thinking           | GA     | `thinking: { type: "enabled", budget_tokens: N }`                  |
| Streaming                   | GA     | SSE with `stream: true`, required for >21,333 max_tokens           |
| Token counting              | GA     | `/v1/messages/count_tokens` endpoint                               |
| Prompt caching              | GA     | Cache prefixes for repeated context, up to 90% cost reduction      |
| Batch processing            | GA     | 50% discount for async batch jobs                                  |
| Vision                      | GA     | Images in message content                                          |
| PDF support                 | GA     | Direct PDF processing                                              |
| Structured outputs          | GA     | JSON schema constraints                                            |
| Code execution              | Beta   | Sandboxed bash/code execution (`code-execution-2025-08-25` header) |
| Programmatic tool calling   | Beta   | Claude writes code to call tools, reducing round trips             |
| Computer use                | GA     | Screen interaction via screenshots + coordinate actions            |

### Models and Pricing (Feb 2026)

| Model             | Input ($/1M tokens) | Output ($/1M tokens) | Context Window           | Max Output |
| ----------------- | ------------------- | -------------------- | ------------------------ | ---------- |
| Claude Opus 4.6   | $15                 | $75                  | 200K                     | 32K        |
| Claude Opus 4.5   | $5                  | $25                  | 200K                     | 32K        |
| Claude Sonnet 4.5 | $3                  | $15                  | 1M (long-ctx: $6/$22.50) | 64K        |
| Claude Sonnet 4   | $3                  | $15                  | 1M                       | 64K        |
| Claude Haiku 4.5  | $1                  | $5                   | 200K                     | 8K         |

Long-context pricing: Requests with >200K input tokens cost ~2x on input and ~1.5x on output.

### Agent SDK vs Direct API -- Decision Matrix

| Dimension              | Agent SDK                            | Direct API                 |
| ---------------------- | ------------------------------------ | -------------------------- |
| Latency (first call)   | ~12s                                 | 1-3s                       |
| Latency (warm)         | ~2-3s                                | 1-3s                       |
| File operations        | Built-in (Read/Edit/Write/Glob/Grep) | DIY                        |
| Shell execution        | Built-in (Bash tool)                 | DIY or Code Execution beta |
| MCP integration        | Built-in                             | DIY                        |
| Subagent orchestration | Built-in (Task tool)                 | DIY                        |
| Multi-model support    | Claude-only                          | Any provider               |
| Context management     | Automatic compaction                 | Manual                     |
| Session persistence    | Built-in                             | Manual                     |
| Hooks/lifecycle        | 14 events                            | None (you own the loop)    |
| Token overhead         | High (reads files, plans, iterates)  | You control exactly        |
| Language binding       | TypeScript, Python                   | Any (HTTP)                 |

**Nancy's sweet spot**: Use the direct API for the agent loop (Rust controls everything), but invoke the Agent SDK for specific "deep work" tasks where Claude Code's file tools and context management earn their overhead.

---

## 4. Running as a Background Service

### Anthropic's Official Hosting Patterns

From the [Hosting Guide](https://platform.claude.com/docs/en/agent-sdk/hosting):

#### Pattern 1: Ephemeral Sessions

New container per task, destroyed on completion. Best for one-off tasks.

#### Pattern 2: Long-Running Sessions

Persistent container instances running multiple Agent SDK processes. Best for proactive agents, content servers, high-frequency chat bots.

#### Pattern 3: Hybrid Sessions (Nancy's best fit)

Ephemeral containers hydrated with history/state from a database or SDK session resumption. Best for intermittent interaction -- kick off work, spin down, resume later.

#### Pattern 4: Single Container Multi-Agent

Multiple SDK processes in one container. Best for agent collaboration/simulation.

### Resource Requirements (per SDK instance)

| Resource | Recommendation                                               |
| -------- | ------------------------------------------------------------ |
| RAM      | 1 GiB minimum                                                |
| Disk     | 5 GiB                                                        |
| CPU      | 1 core                                                       |
| Network  | Outbound HTTPS to `api.anthropic.com` + optional MCP servers |
| Runtime  | Node.js 18+ (required by Claude Code CLI)                    |

Cost estimate: ~$0.05/hour for container alone. **Token costs dominate** -- a single complex task can consume $1-10+ in API calls.

### Session Pooling (Not Yet Official)

There is no official session pooling API. Community proposals include:

```typescript
// PROPOSED (not shipping) -- Process pooling
const sdk = await createAgentSDK({
  poolSize: 3, // keep 3 processes warm
  processReuseLimit: 100, // recycle after N queries
});

// PROPOSED -- Persistent session API
const session = await createSession({ model: "claude-sonnet-4-5-20250929" });
await session.query({ prompt: "Query 1" }); // 12s cold
await session.query({ prompt: "Query 2" }); // <1s warm
```

**Current workaround**: Streaming input mode keeps subprocess alive between turns. Sessions auto-expire after 10 minutes idle.

### What Nancy Should Build

Nancy's Rust orchestrator should implement its own session pool:

```
┌─────────────────────────────────────────────────┐
│  Nancy Controller (Rust / K8s Operator)         │
│                                                  │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐        │
│  │ Worker 1 │ │ Worker 2 │ │ Worker N │        │
│  │ (Pod)    │ │ (Pod)    │ │ (Pod)    │        │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘        │
│       │             │             │              │
│  ┌────▼─────────────▼─────────────▼─────┐       │
│  │      Session State Store             │       │
│  │  (SQLite / Redis / etcd)             │       │
│  └──────────────────────────────────────┘       │
└─────────────────────────────────────────────────┘
         │              │              │
    ┌────▼────┐    ┌────▼────┐   ┌────▼────┐
    │Anthropic│    │ OpenAI  │   │  Ollama  │
    │   API   │    │   API   │   │  Local   │
    └─────────┘    └─────────┘   └──────────┘
```

Each worker pod:

1. Calls the LLM API directly (HTTP)
2. Maintains conversation state in the shared store
3. Implements the agent loop in Rust (tool execution, context management)
4. Can resume any session by loading state from store

This approach avoids the 12s cold start entirely because Nancy IS the agent loop.

---

## 5. Containerized Claude Code

### Official DevContainer Support

Anthropic provides a reference devcontainer configuration. Key components:

- **Base**: Ubuntu with dev tools (Docker CLI, GitHub CLI, Node.js, Go, Python 3, Git, ripgrep, jq)
- **User**: Non-root `agent` user with sudo
- **Auth**: `ANTHROPIC_API_KEY` environment variable (must be set globally, not shell-session-inherited, since Docker daemon doesn't inherit shell env)
- **Permissions**: `--dangerously-skip-permissions` flag for unattended operation

### Docker Sandbox (Official)

```bash
# Docker's official sandbox support
docker sandbox run <sandbox-name> -- [claude-options]
```

Docker Sandboxes provide disposable, isolated environments. Each agent runs in its own sandbox with process isolation, resource limits, network control, and ephemeral filesystems.

### Community Docker Images

Several maintained projects:

- [claudebox](https://github.com/RchGrav/claudebox) -- "Ultimate Claude Code Docker Development Environment"
- [claude-code-container](https://github.com/tintinweb/claude-code-container) -- Focused on `--dangerously-skip-permissions` mode
- [claude-container](https://github.com/nezhar/claude-container) -- Complete isolation with persistent credentials

### Sandbox Providers (Production)

| Provider                                                                    | Type                  | Notes                                      |
| --------------------------------------------------------------------------- | --------------------- | ------------------------------------------ |
| [Modal Sandbox](https://modal.com/docs/guide/sandbox)                       | Serverless containers | Demo: Claude Slack GIF creator             |
| [Cloudflare Sandboxes](https://github.com/cloudflare/sandbox-sdk)           | Edge containers       |                                            |
| [Daytona](https://www.daytona.io/)                                          | Dev environments      |                                            |
| [E2B](https://e2b.dev/)                                                     | Code execution        |                                            |
| [Fly Machines](https://fly.io/docs/machines/)                               | Micro-VMs             |                                            |
| [Vercel Sandbox](https://vercel.com/docs/functions/sandbox)                 | Serverless            |                                            |
| [Depot](https://depot.dev/blog/now-available-claude-code-sessions-in-depot) | Claude Code sessions  | Managed hosting specifically for Agent SDK |

### Security Considerations

- API keys must be injected as env vars or secrets, never baked into images
- `--dangerously-skip-permissions` bypasses ALL safety prompts -- required for unattended operation but grants full system access
- Network policy should restrict outbound to `api.anthropic.com` + required MCP servers only
- File access scoped via volume mounts to project directory
- Consider gVisor or Firecracker for stronger isolation than Docker's default

**Sources**: [Docker Docs - Claude Code](https://docs.docker.com/ai/sandboxes/claude-code/), [Claude Code DevContainer](https://code.claude.com/docs/en/devcontainer), [Docker Sandboxes Blog](https://www.docker.com/blog/docker-sandboxes-run-claude-code-and-other-coding-agents-unsupervised-but-safely/)

---

## 6. Multi-Model Support

Nancy must support Claude, OpenAI, local models, and potentially others. The key challenge is abstracting the differences in tool calling formats, context limits, and capabilities.

### Rust Crates for Multi-Provider LLM Access

| Crate                                                     | Providers                                                           | Tool Calling      | Status         |
| --------------------------------------------------------- | ------------------------------------------------------------------- | ----------------- | -------------- |
| [`genai`](https://crates.io/crates/genai)                 | OpenAI, Anthropic, Gemini, Ollama, Groq, DeepSeek, xAI, Cohere, 14+ | Planned (not yet) | Active, v0.5.x |
| [`llm`](https://github.com/graniet/llm)                   | OpenAI, Anthropic, Gemini, Ollama, ElevenLabs                       | Yes (unified API) | Active         |
| [`llm-connector`](https://crates.io/crates/llm-connector) | OpenAI, Anthropic                                                   | Basic             | Newer          |
| [`multi-llm`](https://crates.io/crates/multi-llm)         | Multiple                                                            | Unknown           | Early          |

**Reality check**: None of these crates are production-grade for Nancy's needs. The `genai` crate is the most mature but lacks tool calling. The `llm` crate has tool calling but is newer.

### Recommended Approach: Nancy's Own Abstraction

Nancy should build a thin provider trait in Rust:

```rust
#[async_trait]
pub trait LLMProvider: Send + Sync {
    async fn chat(
        &self,
        messages: &[Message],
        tools: &[ToolDefinition],
        config: &ModelConfig,
    ) -> Result<Response>;

    async fn stream_chat(
        &self,
        messages: &[Message],
        tools: &[ToolDefinition],
        config: &ModelConfig,
    ) -> Result<Pin<Box<dyn Stream<Item = Result<StreamEvent>>>>>;

    fn capabilities(&self) -> ProviderCapabilities;
    fn context_window(&self) -> usize;
    fn name(&self) -> &str;
}

pub struct ProviderCapabilities {
    pub tool_calling: bool,
    pub vision: bool,
    pub extended_thinking: bool,
    pub streaming: bool,
    pub structured_output: bool,
    pub max_output_tokens: usize,
}
```

Implementation per provider:

- **AnthropicProvider** -- Direct HTTP to `api.anthropic.com/v1/messages`, Anthropic tool format
- **OpenAIProvider** -- Direct HTTP to `api.openai.com/v1/chat/completions`, OpenAI function calling format
- **OllamaProvider** -- Local HTTP to Ollama's OpenAI-compatible endpoint (now also supports Anthropic Messages API format)
- **GeminiProvider** -- Google's Vertex AI or Gemini API

### Tool Calling Format Differences

The main divergence is how tool calls are structured:

**Anthropic**:

```json
{
  "type": "tool_use",
  "id": "toolu_123",
  "name": "get_weather",
  "input": { "location": "San Francisco" }
}
```

**OpenAI**:

```json
{
  "type": "function",
  "id": "call_123",
  "function": {
    "name": "get_weather",
    "arguments": "{\"location\":\"San Francisco\"}"
  }
}
```

Key differences:

- OpenAI stringifies arguments; Anthropic uses native JSON
- OpenAI supports parallel function calls natively; Anthropic does too but differently
- Tool result format differs (Anthropic: `tool_result` content block; OpenAI: `tool` role message)
- Anthropic has `computer_use` tool type; OpenAI does not

Nancy's abstraction layer must normalize these into a common `ToolCall` / `ToolResult` type.

### Ollama as Local Claude Code Backend

Ollama now implements the Anthropic Messages API, meaning Claude Code CLI can point at local models:

```bash
ANTHROPIC_BASE_URL=http://localhost:11434 claude -p "Review this code"
```

This is significant -- it means Nancy could potentially use Claude Code's Agent SDK with local models, though capability gaps (tool calling quality, context window) are real.

**Sources**: [Ollama Claude Code Integration](https://docs.ollama.com/integrations/claude-code), [Claude Code Router](https://atalupadhyay.wordpress.com/2025/10/03/claude-code-router-complete-guide-with-hands-on-lab/)

---

## 7. Agent Patterns -- What Actually Works

### The Agent Loop (Context -> Thought -> Action -> Observation)

Every agent (Claude Code, custom, etc.) runs the same loop:

```
1. CONTEXT:  Assemble system prompt + conversation history + tool results
2. THOUGHT:  Send to LLM, get response (may include tool_use blocks)
3. ACTION:   Execute tool calls (file read, bash, API call, etc.)
4. OBSERVE:  Collect tool results, append to conversation
5. REPEAT:   Until LLM returns end_turn without tool calls
```

Claude Code's innovation is doing this well at scale with good context management (auto-compaction, subagent isolation, session persistence). But the loop itself is simple -- Nancy can implement it in Rust.

### Context Engineering (the hard part)

What makes Claude Code effective isn't the loop -- it's the context engineering:

- **CLAUDE.md** files inject project-specific knowledge at session start
- **Auto-compaction** summarizes conversation when context window fills
- **Subagent isolation** prevents context pollution from exploratory work
- **File checkpointing** enables rollback without losing context
- **Session resumption** preserves full conversation history across restarts

Nancy needs to replicate these patterns:

1. **Project context injection** -- Nancy already has this via template-based prompt assembly
2. **Context window tracking** -- Track token counts, trigger compaction before overflow
3. **Worker isolation** -- Git worktrees per worker (already planned)
4. **State persistence** -- Conversation history in SQLite/files (already planned via file-based IPC)

### Long-Running Agent Sessions

Anthropic's recommended pattern for complex tasks:

**Initializer + Coder pattern**:

1. Initializer Agent runs once to set up environment and create a detailed plan
2. Coder Agent is invoked repeatedly to execute plan steps

For Nancy, this maps to:

1. **Planner worker** -- Reads the Linear issue, explores the codebase, produces an implementation plan
2. **Coder worker** -- Executes each plan step in its own session, with focused context

### Agent Teams (Multi-Agent)

Claude Code now supports agent teams where multiple agents collaborate:

- Agents have named roles (researcher, implementer, reviewer)
- `TeammateIdle` and `TaskCompleted` hooks enforce quality gates
- Agents share a task board for coordination

Nancy's multi-worker architecture maps naturally to this -- each worker is essentially a teammate with a specialized role.

---

## 8. Pricing and Cost Model

### Per-Request Costs (Anthropic API)

For a typical coding task (~10K input tokens, ~2K output tokens, 5 turns):

- **Sonnet 4.5**: ~$0.015 input + ~$0.15 output = ~$0.17/task
- **Opus 4.6**: ~$0.75 input + ~$3.75 output = ~$4.50/task

With prompt caching (50-90% reduction on cached prefixes):

- **Sonnet 4.5 with caching**: ~$0.05-0.10/task

### Always-On vs Per-Request

There is no "always-on subscription" for the API. You pay per token, period.

Cost optimization strategies:

1. **Prompt caching** -- Cache system prompts and project context (up to 90% savings)
2. **Batch API** -- 50% discount for non-urgent async work
3. **Model routing** -- Use Haiku ($1/$5) for simple tasks, Sonnet for most work, Opus for hard problems
4. **Context management** -- Aggressive compaction to avoid paying for stale context
5. **Subagent model selection** -- Run exploration/review subagents on cheaper models

### Container Hosting Costs

~$0.05/hour per container (~$36/month). Negligible compared to token costs.

---

## 9. Recommendations for Nancy

### Architecture Decision: Nancy Owns the Agent Loop

Nancy should implement the agent loop in Rust, calling LLM APIs directly via HTTP. This gives:

- **Multi-model support** from day one (not locked to Claude Code's Node.js runtime)
- **Sub-second latency** (no 12s cold start)
- **Full control** over context management, tool execution, and session state
- **K8s-native** resource management (no Node.js process management overhead)

### Use Agent SDK Selectively

For specific use cases where Claude Code's built-in tools are worth the overhead:

- Complex multi-file refactoring tasks where Edit/Write tool semantics matter
- Tasks requiring MCP server integration
- Initial prototyping before Nancy's own tools are mature

Invoke via CLI from Rust worker pods:

```rust
let output = Command::new("claude")
    .args(&["-p", &prompt, "--output-format", "json", "--allowedTools", "Read,Edit,Bash"])
    .env("ANTHROPIC_API_KEY", &api_key)
    .output()
    .await?;
```

### Nancy's LLM Integration Layers

```
┌─────────────────────────────────────────────┐
│            Nancy Agent Loop (Rust)           │
│  Context Mgmt | Tool Dispatch | State Store │
├─────────────────────────────────────────────┤
│         Provider Abstraction Trait           │
│  AnthropicProvider | OpenAIProvider | ...    │
├─────────────────────────────────────────────┤
│          HTTP Client (reqwest)               │
│    + Token counting + Rate limiting          │
│    + Retry logic + Stream parsing            │
└─────────────────────────────────────────────┘
```

### Implementation Priority

1. **Phase 1**: `AnthropicProvider` with tool calling via Messages API
2. **Phase 2**: Agent loop in Rust (context tracking, tool execution, session state)
3. **Phase 3**: `OpenAIProvider` + `OllamaProvider`
4. **Phase 4**: Advanced features (prompt caching, extended thinking, model routing)
5. **Optional**: Agent SDK integration for "turbo mode" deep tasks

### Key Technical Decisions

| Decision            | Choice                             | Rationale                                         |
| ------------------- | ---------------------------------- | ------------------------------------------------- |
| Primary integration | Direct HTTP API                    | Multi-model, low latency, full control            |
| Agent loop          | Rust-native                        | No Node.js dependency, K8s-native                 |
| Session state       | File-based IPC (existing) + SQLite | Debuggable, auditable, git-friendly               |
| Tool execution      | Rust async (tokio)                 | Concurrent tool calls without subprocess overhead |
| Context management  | Token counting + manual compaction | Must work across providers                        |
| Model routing       | Configurable per task/role         | Cost optimization via model selection             |

---

## 10. What's on the Horizon

### Shipping / Recently Shipped

- Agent SDK streaming input mode (warm sessions, ~2-3s latency)
- Agent teams with `TeammateIdle` and `TaskCompleted` hooks
- Docker Sandbox official support
- Programmatic tool calling (Claude writes code to batch tool calls)
- Tool Search Tool (dynamic tool discovery, 85% context savings)
- Plugins system (hooks + MCP + agents in one package)
- Ollama Anthropic API compatibility

### Likely Coming (based on community requests and Anthropic signals)

- Official session pooling / daemon mode for Agent SDK
- Process reuse across `query()` calls (addressing the 12s cold start)
- Rust SDK (currently TypeScript and Python only)
- Improved batch/async agent execution
- Native K8s operator for Agent SDK hosting

### Not Coming (would require architecture changes)

- Hot-swappable models mid-session (session state is model-specific)
- Cross-provider session portability
- Sub-second cold start for Agent SDK (inherent to spawning Node.js)

---

## Sources

- [Claude Code Headless/Programmatic Docs](https://code.claude.com/docs/en/headless)
- [Agent SDK Overview](https://platform.claude.com/docs/en/agent-sdk/overview)
- [Agent SDK Hosting Guide](https://platform.claude.com/docs/en/agent-sdk/hosting)
- [Agent SDK Sessions](https://platform.claude.com/docs/en/agent-sdk/sessions)
- [Agent SDK Subagents](https://platform.claude.com/docs/en/agent-sdk/subagents)
- [Hooks Reference](https://code.claude.com/docs/en/hooks)
- [Agent SDK TS Issue #34 - 12s Overhead](https://github.com/anthropics/claude-agent-sdk-typescript/issues/34)
- [Building Agents with the Claude Agent SDK](https://www.anthropic.com/engineering/building-agents-with-the-claude-agent-sdk)
- [Claude Agent SDK npm](https://www.npmjs.com/package/@anthropic-ai/claude-agent-sdk)
- [Docker Docs - Claude Code](https://docs.docker.com/ai/sandboxes/claude-code/)
- [Docker Sandboxes Blog](https://www.docker.com/blog/docker-sandboxes-run-claude-code-and-other-coding-agents-unsupervised-but-safely/)
- [Claude Code DevContainer](https://code.claude.com/docs/en/devcontainer)
- [Advanced Tool Use](https://www.anthropic.com/engineering/advanced-tool-use)
- [Anthropic API Pricing](https://platform.claude.com/docs/en/about-claude/pricing)
- [Context Windows](https://platform.claude.com/docs/en/build-with-claude/context-windows)
- [Extended Thinking](https://platform.claude.com/docs/en/build-with-claude/extended-thinking)
- [rust-genai crate](https://github.com/jeremychone/rust-genai)
- [graniet/llm crate](https://github.com/graniet/llm)
- [Ollama Claude Code Integration](https://docs.ollama.com/integrations/claude-code)
- [Depot - Claude Code Sessions](https://depot.dev/blog/now-available-claude-code-sessions-in-depot)
