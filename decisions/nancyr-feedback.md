⏺ Got the first research back. Here are the findings that reshape
the architecture:

Critical Research Findings

claude -p is strictly one-shot. Each invocation pays full cold
start. No persistent mode.

Agent SDK Streaming Input Mode IS the persistent process. The
SDK keeps a long-lived session, feeds messages via async
generator, near-zero inter-turn latency after first startup.
This is the real "claude server" — it's not a daemon, it's a
never-ending streaming session.

The game-changer: there's a PreCompact hook. It fires before
context compaction. Nancy can intercept this and terminate the
turn before information is lost.

Hooks CANNOT see token usage (open feature request #11008). But
OTel telemetry CAN — claude_code.token.usage and
claude_code.api_request events give per-request token counts in
real-time.

The communication model for token warnings works like this:

Mechanism: OTel events → Nancy
What it does: Nancy watches claude_code.token.usage to track
running totals
────────────────────────────────────────
Mechanism: PostToolUse hook → Claude
What it does: After every tool call, Nancy injects
additionalContext: "70% token budget used, wrap up"
────────────────────────────────────────
Mechanism: PreCompact hook → Nancy
What it does: Nancy detects compaction is imminent, terminates
turn cleanly
────────────────────────────────────────
Mechanism: Stop hook → Claude
What it does: Nancy can block stopping if work is incomplete, or

    allow it

14 hook lifecycle events, not 12. Including PreCompact,
TaskCompleted, TeammateIdle.

Graceful termination via continue: false from any hook, SIGTERM,
or SDK interrupt().

Still waiting on the second research agent (token monitoring
patterns). But here's my big question back to you:

The Two-Process Architecture

If the Agent SDK streaming mode IS the persistent process, then
Nancy's worker looks like:

Nancy (Rust) ──spawns──> Agent SDK process (Node.js/Python)
│ │
├── reads OTel events ◄────┤ emits telemetry
├── injects via hooks ────►│ PostToolUse additionalContext
├── catches PreCompact ◄───┤ about to compact
└── terminates turn ──────►│ continue: false

Nancy is the supervisor. The SDK process is the worker. Nancy
never reimplements the agent loop — it wraps it, monitors it,
and controls its lifecycle.

But you said "CLI, not API." The SDK is technically an API
wrapper. If the economics favor claude CLI subscription, are you
thinking: run the actual claude interactive process as a
pseudo-TTY, parse its output stream, and communicate via hooks +
file IPC? That's a fundamentally different architecture than
the SDK path. Which one are we designing for?

✻ Cooked for 56s

⏺ Agent "Research CLI token monitoring" completed

⏺ Searched for 1 pattern, read 1 file (ctrl+o to expand)

⏺ Second research agent is back. This fills in critical gaps.
Here's the combined picture:

New Intelligence: The Monitoring Stack is Richer Than Expected

StatusLine API (the sleeper hit): Since Claude Code v2.1.6, a
statusline command receives remaining_percentage on every update
cycle. This is the real-time context monitor — not hooks, not
OTel. And crucially: auto-compaction triggers at ~77.5% usage
(there's a 22.5% buffer). So:

remaining_percentage - 22.5 = actual free space before
compaction

Tokentap exists (725 stars) — a working HTTP proxy that
intercepts ANTHROPIC_BASE_URL, counts tokens, shows a fuel
gauge. This is the exact pattern Nancy would implement natively
in Rust. Proven approach.

Stop hook exit code 2 forces Claude to continue. This is the
injection mechanism — when Nancy detects threshold crossing, the
Stop hook fires, reads a flag file Nancy wrote, outputs "You've
used 70% of context. Commit your work and summarize progress."
and exits with code 2. Claude receives that as its next
instruction.

Compaction is three layers:

1. Microcompaction — continuous, offloads large tool outputs to
   disk
2. Auto-compaction — triggers at ~77.5% context used
3. Manual — /compact with optional focus hints

Gemini CLI has native OTel — structured, vendor-neutral, with
gemini_cli.token.usage counters. Totally different format from
Claude's JSONL logs. This validates your "normalize across
providers" requirement.

So the full monitoring architecture for Nancy looks like:

Nancy Supervisor (Rust)
├── HTTP Proxy (hyper/axum)
│ └── Intercepts ANTHROPIC_BASE_URL / OPENAI_BASE_URL traffic
│ └── Parses streaming SSE, counts tokens per request
├── OTel Receiver
│ └── Ingests Gemini CLI telemetry natively
├── StatusLine Hook
│ └── Reads remaining_percentage from Claude continuously
├── JSONL Watcher (notify crate)
│ └── Tails ~/.config/claude/projects/session.jsonl
└── Threshold Engine
└── Writes flag files → Stop hook reads them → injects
directives
└── Catches PreCompact → terminates turn before information
loss

All of this feeds into Nancy's normalized telemetry format — the
data product — regardless of whether the worker is Claude,
Gemini, or Codex.

I've got my questions on the table from my last message (CLI vs
SDK path, data product monetization, process lifecycle). Take
your time — these are the decisions that shape everything.

⏺ am - am_salient (MCP)(text: "Nancy v3 monitoring architecture:
Four data sources for real-time token
monitoring: (1) HTTP proxy via
ANTHROPIC_BASE_URL override (tokentap
pattern, proven), (2) StatusLine API since
Claude v2.1.6 gives remaining_percentage
continuously with 22.5% autocompact buffer,
(3) JSONL session logs at
~/.config/claude/projects/ for
near-real-time tailing, (4) OTel receiver
for Gemini CLI native telemetry.
Communication to running Claude process:
Stop hook exit code 2 forces continuation
with injected message. PreCompact hook
fires before auto-compaction at ~77.5%
context. Three compaction layers:
microcompaction (continuous tool output
offload), auto-compaction (threshold),
manual (/compact). Key architectural
decision: Nancy wraps CLI processes (not
SDK), supervises them with
proxy+hooks+statusline, terminates turns
before compaction to preserve context
fidelity.")
⎿  {
"stats": {
"conscious": 4,
… +5 lines (ctrl+o to expand)

⏺ am - am_buffer (MCP)(user: "Stuart clarified: K8s stays in
vision but not first priority. CLI vs API is
the key abstraction (CLI cheaper via
subscription). Nancy wraps CLI as background
process, captures all telemetry as data
product. Terminate before compaction. Linear
is a plugin not the source of truth.
Enterprise is the target via stepping
stones.", assistant: "Research found:
StatusLine API (remaining_percentage with
22.5% autocompact buffer), tokentap proxy
pattern for ANTHROPIC_BASE_URL interception,
Stop hook exit code 2 for injecting
messages, PreCompact hook for compaction
detection, Gemini CLI native OTel, three
compaction layers. Architecture: Nancy is a
telemetry-rich process supervisor with HTTP
proxy + OTel receiver + StatusLine + JSONL
watcher feeding a normalized data product.")
⎿  {
"buffer_size": 3,
"episode_created": "conversation"
}

⏺ Take your time digesting all that. The three questions that'll
unlock the next layer are still on the table:

1. CLI wrapping vs SDK — subscription economics vs cold start
   tradeoffs
2. What "data product" means concretely — cost attribution?
   quality analytics? compliance?
3. Process lifecycle — one long-lived Claude per task, or Nancy
   starts/stops sessions per iteration?

No rush. These are load-bearing decisions.
