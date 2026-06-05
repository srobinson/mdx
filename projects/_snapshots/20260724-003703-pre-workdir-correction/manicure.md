---
title: Manicure
type: projects
tags: [manicure, claude-code, codex, mitmproxy, proxy, developer-tools, breakpoint, workbench, helioy, context-engineering, open-source]
summary: Provider-neutral context control plane for coding agents. mitmproxy-resident inspector, rule pipeline, and breakpoint editor for /v1/messages traffic, with an internal IR and pluggable adapters
status: active
project: manicure
confidence: high
created: 2026-04-10
updated: 2026-04-10
---

# Manicure

> **mani**fest + **cur**at**e**. Care for the cargo your coding agent carries.

## TL;DR

A provider-neutral context control plane for coding agents. Sits as a reverse proxy in front of Claude (V1) and Codex (V2), captures every `/v1/messages` exchange to disk, normalizes payloads into an internal representation, runs them through a deterministic curation pipeline, optionally pauses for manual edits in a schema-aware editor, then reserializes and forwards. Burp Repeater meets a context optimizer, with a stable internal schema so adapters can grow without rewriting the core.

## Strategic framing

Three commitments shape every other decision.

1. **Product as a context control plane.** The workbench is not a passive viewer with an editor bolted on. It is a pipeline that subtracts, rewrites, and (later) adds context, with a UI that exposes the pipeline's effects. Manual breakpoint editing is one input to the pipeline among several. Curation rules are first-class from V1.

2. **Workbench as a Helioy integration surface.** The same hook point that strips tools can also retrieve relevant memory from `attention-matters`, inject `markdown-matters` snippets, or call `context-matters` for prior decisions. V1 ships zero Helioy integrations, but the architecture leaves the seam open. V2 wires them in. This is the long-term reason to build the workbench instead of a one-off mitmproxy script.

3. **Provider-neutral from day one.** Anthropic schema details are confined to an adapter. The pipeline, the editor, the persistence layer, and the rule engine all operate on an internal representation. When OpenAI's Codex CLI exposes an equivalent base URL, a second adapter slots in without touching the core. The internal schema is the contract; adapters are the translators.

## Motivation

1. **Visibility**: see exactly what Claude Code (or any client) is sending. The captured payload is the ground truth for debugging context bloat, unexpected tool inclusions, and prompt drift.
2. **Experimentation**: strip tools, shorten system prompts, drop old tool_results, then forward and observe how the model responds with less context. The fastest path to empirical context engineering.
3. **Curation**: persistent rules apply the same edit to every subsequent request. Edit once, never re-edit. The workbench remembers.
4. **Helioy hook**: every request flowing through the workbench is a chance to retrieve, augment, or annotate. The pipeline is the integration seam.
5. **Portability**: one workbench for every coding agent that exposes an HTTPS base URL. Claude today, Codex tomorrow, anything else after that.

## Real-world data

A single capture from a routine Claude Code session produced this breakdown. Every design decision is anchored to these numbers.

| Section | Size | Count | Note |
|---|---|---|---|
| **tools** | **192 KB (67%)** | 147 | Dominates the payload. The `Agent` tool alone is 30 KB of description. |
| system | 28 KB | 3 parts | Part `[2]` alone is 27.5 KB. Parts `[0]` and `[1]` are under 100 chars. |
| messages | 17 KB | 5 turns | `messages[0]` has 5 text blocks, 4 of which are `<system-reminder>` injections. |
| metadata, thinking, output_config, max_tokens, model, stream | < 1 KB combined | | Rarely edited. |
| **total** | **285 KB** | | Approx 71k tokens. |

**Tool prefix distribution** (147 tools):

```
mcp__plugin_helioy-tools_linear-server    37
<bare>                                    29    (Read, Edit, Bash, Agent, ...)
mcp__plugin_helioy-tools_supabase         29
mcp__plugin_helioy-tools_am               12
mcp__plugin_helioy-bus_helioy-warroom      9
mcp__plugin_helioy-tools_cm                9
mcp__plugin_helioy-tools_fmm               8
mcp__plugin_helioy-bus_helioy-bus          7
mcp__plugin_helioy-tools_mdm               7
```

A flat 147-row checkbox list is unusable. Tool grouping by prefix is mandatory. Tools at 67% of the payload explain why `strip_tools` is the headline pipeline action.

## Quick start

Copy, paste, run. No cert install, no sudo, no system proxy settings, no TLS interception.

```bash
# 1. Install
curl -fsSL https://manicure.sh/install.sh | bash
```

```bash
# 2. Start the workbench (blocking, keep this terminal open)
manicure start
```

```bash
# 3. In another terminal, launch Claude Code pointed at the workbench
ANTHROPIC_BASE_URL=http://localhost:8787 claude
```

Open the web UI at `http://localhost:8788`. Every `/v1/messages` request from Claude Code now routes through the workbench, gets normalized to the internal schema, runs through the rule pipeline, and appears in the live log. Arm the breakpoint to pause the next request for manual editing on top of the pipeline output.

### What the install script does

Single-file shell installer, the same pattern as `rustup`, `bun`, `uv`, `ollama`, `fly`, and every other modern dev tool. The script:

1. Detects the host OS and architecture
2. Ensures a Python toolchain is available (uses `uv` if present, otherwise bootstraps it)
3. Installs `manicure` and its dependencies (mitmproxy, fastapi, uvicorn) into an isolated environment
4. Symlinks the `manicure` binary into `~/.local/bin` (or the OS-appropriate location)
5. Prints next-step instructions pointing at `manicure start`

### What `manicure start` runs

```bash
mitmdump \
  --mode reverse:https://api.anthropic.com \
  --listen-port 8787 \
  -s <bundled addon>
```

`--mode reverse` means no cert install. mitmproxy accepts plain HTTP on localhost and handles TLS only on the outbound leg to Anthropic. The bundled addon starts the FastAPI web UI on port 8788 as a background task on the same event loop.

## Scope (V1, locked)

**In scope**
- Capture every `/v1/messages` request and response to disk
- Internal representation (IR) with a single Anthropic adapter, lossless round-trip invariant
- Deterministic rule pipeline with six curation actions
- Persistent rule storage scoped by `session_id`, `device_id`, `account_id`, `model`, or global
- Persistent on-disk log viewable via a web UI
- Live-updating log list via Server-Sent Events
- Request-only breakpoint: pause after pipeline, edit, release
- Schema-aware editor over the IR (not the raw Anthropic schema)
- Rules UI: list, create, enable/disable, delete, view audit trail
- Global toggle + armed-once mode for the breakpoint
- Token and character accounting, visible live during edits

**Explicit non-goals (V1)**
- A second adapter (Codex/OpenAI ships in V2)
- Any Helioy integration (V2)
- Response breakpoints
- Conditional pause rules
- Drop and canned-response button
- Retention policy or log rotation
- Diff view against the original
- Replay of historical exchanges
- JSON Schema validation
- Auth (localhost bind is the only guard)

## V2 and beyond

- **OpenAI / Codex adapter**: slot in alongside `AnthropicAdapter`, reuse the entire pipeline and editor unchanged
- **Helioy integration hooks**: additive pipeline actions calling `attention-matters`, `markdown-matters`, `context-matters` for retrieval and augmentation
- **Response breakpoints** with careful client-timeout handling
- **Response-side rules** (rewrite tool_use args, inject memory hits)
- **Filter rules** for conditional pausing (pause-when-model-equals, pause-when-tool-present)
- **Drop button** with canned response
- **Log rotation and retention**
- **Diff view** against the original payload inside the editor
- **Replay**: re-send a historical exchange, optionally with edits
- **Cross-exchange search** across `index.jsonl`
- **Template substitution**: parameterized rules (e.g. inject the current git branch into a system part)
- **Parsed `<system-reminder>` handling** with per-reminder toggles
- **Saved mutation recipes** beyond simple rules: multi-step workflows applied with one click

## Distribution and licensing

### License

Apache 2.0.

### Repository

Public on GitHub at V2 (when the Codex adapter ships). Repo name: `manicure`. Standard OSS metadata files: `LICENSE`, `README.md`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `SECURITY.md`. Distribution channels: pypi (`pip install manicure`), the curl-pipe install script at `manicure.sh`, and Homebrew tap once stable. CI runs the lossless round-trip test against a fixture corpus of real captured payloads.

### Maintenance stance

Maintain conditional on traction. The bar is whether the project crosses a meaningful adoption threshold: GitHub stars, install counts, organic issue/PR flow, and most importantly whether anyone is using it as critical infrastructure. Below the threshold, archive with a clear note that forks are welcome. Above the threshold, treat as a long-running project with proper release cadence and roadmap.

### Launch

Launch coordinated with V2 release:

- Demo gif, 60 seconds, showing the live log fill, the editor stripping 100 KB of MCP tools, and the post-strip request succeeding
- Blog post explaining the motivation, the IR, and the curation pipeline
- Hacker News submission timed to a weekday morning Pacific time
- X / Reddit (`r/LocalLLaMA`, `r/ClaudeAI`) cross-posts pointing to the blog post
- Direct outreach to a small number of practitioners building on Claude Code

## Naming

**Manicure.** Five reinforcing layers, every reading points at the product:

1. **Portmanteau**: **mani**fest + **cur**at**e**. The two words that describe what the pipeline does, contracted into one.
2. **Wordplay**: contains *cure*. The workbench is the cure for context bloat.
3. **Etymology**: Latin *manus + cura* = hand + care. Literally "hand-care", which is exactly what the breakpoint editor is.
4. **Surface metaphor**: a manicure trims back overgrowth while preserving and shaping what remains. Loss-explicit, never destructive.
5. **Distinctiveness**: zero collision in the dev-tool space. Searchable, ownable, screenshot-friendly.

**Identity surfaces**:

| Surface | Slug | Notes |
|---|---|---|
| pypi | `manicure` | Clean, no prior package |
| crates.io | `manicure` | Reserved for any future Rust port |
| Domain | `manicure.sh` | Available (RDAP-verified); `.sh` TLD reads as "shell" |
| GitHub | `<owner>/manicure` | |
| CLI binary | `manicure` | Installed by the curl-pipe script |

**Backup domains**: `manicure.tools`, `manicure.app`, `manicure.run`. Note: `manicure.dev` is taken.

**Tagline candidates**:
- "Manicure your prompts."
- "Care for the cargo your coding agent carries."
- "Manifest curate."

## Related

- `/Users/alphab/.claude/scripts/capture_claude_request.py` (current addon, pre-workbench)
- `~/.mdx/projects/manicure-spec.md` (technical spec)
- `~/.mdx/projects/_versions/manicure.v3.md` (pre-split combined doc)
