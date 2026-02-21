---
title: Monitoring Claude Code HTTP Requests
category: research
tags: [claude-code, debugging, tokens, macos]
created: 2026-03-17
---

# Monitoring Claude Code HTTP Requests

## Executive Summary

Claude Code provides multiple layers of request visibility, from built-in CLI flags (`--verbose`, `--debug "api"`) and environment variables (`CLAUDE_DEBUG=1`) through purpose-built proxy tools that leverage the `ANTHROPIC_BASE_URL` redirect mechanism. The simplest full-payload inspection path is `claude-code-logger` (zero-config npm proxy), while `mitmproxy` in reverse mode offers the most flexibility for advanced analysis. All approaches exploit the same architectural fact: Claude Code is a Node.js application that respects `ANTHROPIC_BASE_URL`, `HTTPS_PROXY`, and `NODE_EXTRA_CA_CERTS` environment variables.

## 1. Built-in Claude Code Debug Capabilities

### CLI Flags

| Flag | Behavior |
|------|----------|
| `--verbose` | Full turn-by-turn output including JSON payloads, system prompts, tool calls |
| `--debug` | Debug mode with optional category filtering: `claude --debug "api,mcp"` |
| `--debug "api"` | Filters debug output to API-related events only |

The `--verbose` flag produces unstructured JSON dumps that are difficult to read for large payloads. The `--debug` flag with category filtering (added in later versions) is more practical for targeted inspection.

### Environment Variables (Debugging and Observability)

From a comprehensive environment variable audit (source: [GitHub Gist by unkn0wncode](https://gist.github.com/unkn0wncode/f87295d055dd0f0e8082358a0b5cc467)):

| Variable | Purpose |
|----------|---------|
| `CLAUDE_DEBUG=1` | Enable debug logging for internal warnings and diagnostics |
| `CLAUDE_CODE_DEBUG_LOGS_DIR` | Custom directory for debug logs (default: `~/.claude/debug/{sessionId}.txt`) |
| `CLAUDE_CODE_DIAGNOSTICS_FILE` | Write diagnostics to a specific file |
| `CLAUDE_CODE_ENABLE_TOKEN_USAGE_ATTACHMENT` | Attach token usage info (used/total/remaining) to messages |
| `CLAUDE_CODE_EXTRA_BODY` | Additional JSON merged into API request bodies |
| `ANTHROPIC_LOG` | Anthropic SDK internal logging level |
| `OTEL_LOG_USER_PROMPTS` | Include user prompts in OpenTelemetry logs |
| `OTEL_LOG_TOOL_CONTENT` | Include tool input/output content in telemetry |
| `OTEL_LOG_TOOL_DETAILS` | Include detailed tool execution info in telemetry |
| `DEBUG_SDK` | Activate SDK debug logging |
| `SESSION_LOGS_UNGROUP_REASONING_TEXT` | Controls reasoning text visibility in session logs |

### Built-in Commands

| Command | What it shows |
|---------|---------------|
| `/cost` | Session token usage: total cost, API duration, wall duration, lines changed (API key users only) |
| `/stats` | Usage patterns for Max/Pro subscribers |
| `/context` | Current context window consumption breakdown |
| `/debug` | Built-in skill (v2.1.30+) that reads session debug logs and troubleshoots |

### Debug Log Location

Debug logs are stored at `~/.claude/debug/<session-id>.txt`. Session transcripts (JSONL format) are stored at `~/.claude/projects/<encoded-path>/` and contain per-request token usage breakdowns, tool calls, and conversation history. Compaction events appear in transcript metadata but the actual compaction API calls are not logged in the JSONL.

### The Full Debug Incantation

```bash
CLAUDE_DEBUG=1 claude --debug --verbose 2>&1 | tee debug-$(date +%Y%m%d).log
```

This produces everything, but the output is overwhelming. For targeted API inspection, `claude --debug "api"` is more practical.

## 2. Proxy-Based Request Interception

All proxy approaches exploit the same mechanism: Claude Code respects `ANTHROPIC_BASE_URL` to redirect API traffic through a local proxy.

### 2a. claude-code-logger (Simplest Option)

**Repository**: [dreampulse/claude-code-logger](https://github.com/dreampulse/claude-code-logger)

Zero-install proxy that intercepts Claude Code traffic and displays system prompts, tools, token metrics, and conversation flow.

```bash
# Start the logger
npx claude-code-logger start

# In another terminal, launch Claude Code through it
ANTHROPIC_BASE_URL=http://localhost:8000/ claude
```

**Key flags**:
- `--log-body`: Enable full request/response body logging
- `-v, --verbose`: Show untruncated system prompts
- `--chat-mode`: Display conversation only (default on)
- `--debug`: Troubleshooting messages
- `-p, --port`: Local port (default 8000)

**What you see**: System prompts, tool definitions, token metrics, full message exchanges. Handles gzip, deflate, brotli compression and SSE streaming. The default chat mode filters to user/assistant conversation only; use `--verbose` to see system-level detail.

### 2b. mitmproxy (Most Flexible)

**Setup on macOS**:

```bash
# Install
brew install mitmproxy

# Start as reverse proxy targeting Anthropic
mitmweb --mode reverse:https://api.anthropic.com --listen-port 8000

# Launch Claude Code through it
ANTHROPIC_BASE_URL=http://localhost:8000 claude
```

`mitmweb` provides a browser UI at `localhost:8081` for inspecting flows. `mitmproxy` provides a terminal UI. `mitmdump` is headless for scripting.

**Certificate trust** (required for some configurations):
```bash
# mitmproxy generates certs at first run
# macOS: import into Keychain Access, set Always Trust for SSL
open ~/.mitmproxy/mitmproxy-ca-cert.pem
```

For the reverse proxy mode pointing at `ANTHROPIC_BASE_URL=http://localhost:8000`, certificate trust is typically not required because the local connection uses HTTP, and mitmproxy handles TLS to the upstream Anthropic endpoint.

**Ready-to-use Python addons** exist for extracting system prompts, tool definitions, and full request/response capture. A comprehensive set of three addons is documented at [nerdleveltech.com](https://www.nerdleveltech.com/Capture-Claude-Code-with-mitmproxy-step-by-step-guide-with-addons-analysis-scripts):

1. `dump_claude_prompts.py`: Extracts system prompts only
2. `dump_claude_prompts_and_tools.py`: Extracts system prompts and tool schemas
3. `dump_claude_full.py`: Full timestamped request/response capture with message history

Run with: `mitmdump -s addon.py --mode reverse:https://api.anthropic.com --listen-port 8000`

**Visualization**: Use `mitmproxy-llm-better-view` addon with `mitmweb` for readable formatting of the large JSON payloads Claude Code sends.

**macOS Network Extension**: mitmproxy now supports transparent interception of macOS applications via a Network Extension (no proxy env vars needed), though the `ANTHROPIC_BASE_URL` approach is simpler for Claude Code specifically.

### 2c. llm-interceptor (Cross-Platform MITM)

**Repository**: [chouzz/llm-interceptor](https://github.com/chouzz/llm-interceptor)

Purpose-built for intercepting AI coding assistant traffic. Supports Claude Code, Cursor, and others.

```bash
# Configure
HTTP_PROXY=http://127.0.0.1:9090
HTTPS_PROXY=http://127.0.0.1:9090
NODE_EXTRA_CA_CERTS=~/.mitmproxy/mitmproxy-ca-cert.pem
```

Features session-based recording (start/stop via keyboard), automatic API key masking, pre-configured for Anthropic/OpenAI/Google/Groq APIs. Outputs JSONL and split JSON files per session.

### 2d. claude-code-proxy (Web Dashboard)

**Repository**: [seifghazi/claude-code-proxy](https://github.com/seifghazi/claude-code-proxy)

Go + React application providing a web dashboard with SQLite-backed persistent logging, searchable request history, conversation threading, and performance metrics.

```bash
# Setup
make install && make dev
# Dashboard at localhost:5173, proxy at localhost:3001
ANTHROPIC_BASE_URL=http://localhost:3001 claude
```

### 2e. cc-trace (Claude Code Skill)

**Repository**: [alexfazio/cc-trace](https://github.com/alexfazio/cc-trace)

A Claude Code skill (not a standalone tool) that turns Claude into an interactive assistant for configuring and using mitmproxy. It guides setup, filter application, payload explanation, and addon writing. Useful if you want Claude to help you analyze its own traffic.

## 3. Proxy Comparison for This Use Case

| Tool | Setup Effort | Payload Visibility | Token Tracking | Best For |
|------|-------------|-------------------|----------------|----------|
| `claude-code-logger` | One command | Full (with `--log-body`) | Yes | Quick inspection, minimal setup |
| `mitmproxy` (reverse) | 5 min | Full | Manual (via addons) | Scriptable analysis, custom addons |
| `Proxyman` | 10 min | Full (GUI) | Manual | macOS-native GUI, visual inspection |
| `Charles Proxy` | 15 min | Full (GUI) | Manual | Cross-platform GUI, familiar to mobile devs |
| `llm-interceptor` | 10 min + cert | Full | Yes (auto-parsed) | Multi-tool comparison (Cursor vs Claude) |
| `claude-code-proxy` | 15 min (Go+Node) | Full + DB storage | Dashboard metrics | Persistent logging, team use |

**Recommendation**: For quick one-off inspection, `claude-code-logger` via npx is the fastest path. For ongoing analysis with custom extraction, `mitmproxy` in reverse mode with Python addons is the most powerful. Proxyman is the best option if you prefer a polished macOS GUI.

### Proxyman Setup for Claude Code

Proxyman requires a license for HTTPS decryption. Configure via the Proxyman helper script for your terminal, then:

1. Enable "All Domains" for the Node.js process in the bottom-right panel
2. Filter to `api.anthropic.com` to remove analytics noise
3. Set `HTTPS_PROXY` environment variable to route Claude Code traffic

Proxyman also offers an MCP server that lets Claude Code query Proxyman's captured data, creating a self-referential debugging loop.

### Charles Proxy

Works but requires more manual configuration: install root certificate, enable SSL proxying for `api.anthropic.com`, and configure Claude Code's proxy settings. Less ergonomic than the alternatives for CLI application interception.

## 4. What Request Payloads Contain

Based on multiple reverse-engineering analyses (Kir Shatrov, api2o.com, ClaudeTUI research):

**System prompt** (~14,328 tokens constant overhead):
- Claude Code identity and behavioral instructions
- Tool definitions (11+ tools: Bash, Edit, Read, Write, GlobTool, GrepTool, LS, etc.)
- Security constraints and safety guidelines
- CLAUDE.md contents from project and user configs
- Environment context: working directory, git status, platform, date, model version

**Request types** (distinguished by tool availability):
1. Title generation (Haiku model): topic detection for new conversations
2. Conversation (Sonnet model): includes Task tool for spawning subagents
3. Task execution (Sonnet model): excludes Task tool to prevent recursion

**Token distribution** (from ClaudeTUI analysis of real sessions):
- System prompt: ~14k tokens per request
- Compaction summaries: 11-19k tokens per compaction event
- Effective conversation window: ~167k of 200k available
- Cache read ratio: up to 98% in long sessions
- Compaction triggers at ~83% capacity
- Average efficiency: ~76% (24% overhead from compaction + buffer)
- Subagents: ~50k tokens per subprocess call

## 5. Session-Level Token Usage Tracking

### Built-in Options

- `/cost`: Real-time session cost (API key users)
- `/stats`: Usage patterns (subscription users)
- `/context`: Context window consumption breakdown
- `--verbose`: Includes per-turn token counts in output

### Third-Party Tools

**ccusage** ([ryoppippi/ccusage](https://github.com/ryoppippi/ccusage)): Parses local JSONL session transcripts for daily, monthly, session-level, and 5-hour billing block reports. `npx ccusage@latest daily` for a quick daily breakdown. Tracks cache creation vs. cache read tokens separately.

**Claude-Code-Usage-Monitor** ([Maciek-roboblog](https://github.com/Maciek-roboblog/Claude-Code-Usage-Monitor)): Real-time CLI chart of token consumption with cost estimates and limit predictions.

**ccusage.com**: Web-based analysis tool for Claude Code JSONL files.

**ClaudeTUI**: Research tool that analyzed thousands of API calls to produce the token distribution statistics cited above.

### Token Counting API

Anthropic offers a free token counting endpoint that accepts the same structured input as the Messages API (system prompts, tools, images, PDFs) and returns token counts without consuming quota. Useful for estimating request sizes before sending.

## 6. Network Configuration Reference

For all proxy approaches, these environment variables control Claude Code's network behavior:

```bash
# Redirect API traffic to local proxy
export ANTHROPIC_BASE_URL=http://localhost:8000

# Or use standard proxy vars (for forward proxy setups)
export HTTPS_PROXY=http://localhost:8080
export HTTP_PROXY=http://localhost:8080
export NODE_EXTRA_CA_CERTS=~/.mitmproxy/mitmproxy-ca-cert.pem

# Bypass proxy for specific domains
export NO_PROXY=localhost,127.0.0.1
```

These can also be set in `~/.claude/settings.json`:
```json
{
  "env": {
    "HTTPS_PROXY": "http://localhost:8080",
    "NODE_EXTRA_CA_CERTS": "/path/to/ca-cert.pem"
  }
}
```

**Known issues**: `HTTPS_PROXY` in settings.json may not apply to Anthropic API POST requests (GitHub issue #11660). Setting via shell export is more reliable. `NODE_EXTRA_CA_CERTS` in settings.json has also had intermittent issues; shell export is preferred.

## Sources Consulted

### GitHub Repositories and Issues
- [dreampulse/claude-code-logger](https://github.com/dreampulse/claude-code-logger) (proxy logger)
- [chouzz/llm-interceptor](https://github.com/chouzz/llm-interceptor) (MITM proxy)
- [seifghazi/claude-code-proxy](https://github.com/seifghazi/claude-code-proxy) (web dashboard proxy)
- [alexfazio/cc-trace](https://github.com/alexfazio/cc-trace) (Claude Code skill for mitmproxy)
- [ryoppippi/ccusage](https://github.com/ryoppippi/ccusage) (JSONL usage analyzer)
- [anthropics/claude-code#6308](https://github.com/anthropics/claude-code/issues/6308) (timing/token display without verbose)
- [anthropics/claude-code#10388](https://github.com/anthropics/claude-code/issues/10388) (agent token usage API)
- [anthropics/claude-code#4859](https://github.com/anthropics/claude-code/issues/4859) (debug/verbose stderr bug)
- [Claude Code CLI Environment Variables Gist](https://gist.github.com/unkn0wncode/f87295d055dd0f0e8082358a0b5cc467)

### Articles and Tutorials
- [Reverse engineering Claude Code (Kir Shatrov)](https://kirshatrov.com/posts/claude-code-internals) -- mitmproxy reverse engineering methodology
- [Claude Code Implementation Dive (api2o.com)](https://blog.api2o.com/en/blog/claude-code-prompts-tools-structure) -- request payload structure analysis
- [Capture Claude Code with mitmproxy (nerdleveltech.com)](https://www.nerdleveltech.com/Capture-Claude-Code-with-mitmproxy-step-by-step-guide-with-addons-analysis-scripts) -- step-by-step guide with Python addons
- [Where Do Your Claude Code Tokens Actually Go? (dev.to)](https://dev.to/slima4/where-do-your-claude-code-tokens-actually-go-we-traced-every-single-one-423e) -- ClaudeTUI token tracing research
- [Tutorial: Intercept Claude Code Requests (ai.moda)](https://www.ai.moda/en/blog/tutorial-intercepting-claude-code-requests) -- David Manouchehri tutorial (content not extractable via fetch)

### Official Documentation
- [Claude Code CLI Reference](https://code.claude.com/docs/en/cli-reference)
- [Claude Code Cost Management](https://code.claude.com/docs/en/costs)
- [Claude Code Enterprise Network Configuration](https://code.claude.com/docs/en/network-config)

### X/Twitter
- [@dani_avila7](https://x.com/dani_avila7/status/2019413280851132525): /debug command in Claude Code v2.1.30 for skill/subagent/hook troubleshooting
- [@burkov](https://x.com/burkov/status/2012036165512184178): ~$0.80 per code update request on API key billing; ~$80/day for heavy use vs $100/month Max subscription

## Source Quality Assessment

**High confidence**: Environment variables, CLI flags, and proxy setup methods are verified across multiple independent sources (official docs, GitHub repos, reverse-engineering articles). The `ANTHROPIC_BASE_URL` redirect mechanism is documented by Anthropic and confirmed by multiple third-party tools.

**Medium confidence**: Token distribution numbers (14k system prompt, 98% cache reads, 76% efficiency) come from one detailed analysis (ClaudeTUI/dev.to article). The methodology appears sound but has not been independently replicated with published data.

**Low confidence**: Reddit yielded zero results across multiple query variations. Community discussion of these techniques appears fragmented across GitHub issues, dev.to, and individual blog posts rather than concentrated in any single forum.

## Open Questions

1. **OpenTelemetry integration**: The OTEL environment variables suggest Claude Code supports OpenTelemetry export. The exact collector setup and what spans/metrics are emitted is undocumented publicly.
2. **Per-request token breakdown in verbose mode**: Whether `--debug "api"` shows the full `usage` block from API responses (input_tokens, output_tokens, cache_creation_input_tokens, cache_read_input_tokens) or a summary.
3. **Compaction API calls**: These are "hidden" and not logged in JSONL transcripts. Whether they are visible via proxy interception is not confirmed.
4. **LiteLLM as a monitoring proxy**: Several enterprises use LiteLLM for spend tracking on Bedrock/Vertex. Whether this works cleanly with `ANTHROPIC_BASE_URL` for direct API users is unverified.

## Actionable Takeaways

**For quick payload inspection**: `npx claude-code-logger start --log-body -v` in one terminal, `ANTHROPIC_BASE_URL=http://localhost:8000/ claude` in another. Zero install, immediate visibility.

**For ongoing monitoring**: Set up mitmproxy with the `dump_claude_full.py` addon for persistent capture, then use the extraction scripts to analyze system prompt evolution and token patterns over time.

**For token cost tracking**: `npx ccusage@latest daily` parses local JSONL files without any proxy setup. For real-time session tracking, configure the status line via `/config` or use `/cost` periodically.

**For macOS GUI**: Proxyman with a filter on `api.anthropic.com` provides the most polished visual experience, but requires a license for HTTPS decryption.
