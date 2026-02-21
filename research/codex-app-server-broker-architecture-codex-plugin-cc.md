---
title: Codex app-server broker multiplexing architecture (openai/codex-plugin-cc)
type: research
tags: [codex, claude-code-plugin, json-rpc, unix-socket, multi-agent, broker, app-server, nancy, manicure]
summary: OpenAI's Claude Code plugin wraps `codex app-server` (JSON-RPC over stdio) behind a detached broker daemon that multiplexes multiple Claude slash commands onto one Codex process via a Unix socket, returning `BROKER_BUSY` (-32001) on overlap while preserving a single active stream.
status: active
source: github-researcher
confidence: high
created: 2026-04-17
updated: 2026-04-17
---

## Executive Summary

`openai/codex-plugin-cc` is the official Claude Code plugin for the Codex CLI. It ships seven slash commands (`/codex:setup`, `/codex:review`, `/codex:adversarial-review`, `/codex:rescue`, `/codex:status`, `/codex:result`, `/codex:cancel`), a `codex-rescue` subagent, three skills, and three hooks (`SessionStart`, `SessionEnd`, `Stop`). The non-obvious engineering is in how it talks to Codex: it spawns `codex app-server` (a JSON-RPC over stdio server from the Codex CLI) once per workspace, fronts it with a small detached Node broker that listens on a Unix socket (or Windows named pipe), and multiplexes multiple concurrent slash-command invocations onto that single server. The broker enforces a single-writer / single-stream policy with a `BROKER_BUSY` (`-32001`) JSON-RPC error, persists thread IDs so `--resume-last` works across jobs, and delegates auth entirely to `codex login`. The plugin has zero runtime npm dependencies, uses JS + JSDoc with TypeScript types code-generated from `codex app-server generate-ts`, and applies a structured-output JSON schema to every review. The review gate adds an optional Claude `Stop` hook that runs a Codex "stop-gate" review and blocks the stop if the first output line starts with `BLOCK:`.

## Architecture

Three layers, cleanly separated:

1. **Claude-facing surface** (`plugins/codex/commands/*.md`, `plugins/codex/agents/codex-rescue.md`, `plugins/codex/hooks/hooks.json`) — declarative. Markdown frontmatter (`allowed-tools`, `argument-hint`, `disable-model-invocation`) for slash commands; the `codex-rescue` subagent is explicitly instructed to be a "thin forwarding wrapper" with one `Bash` call.
2. **Node orchestrator** (`plugins/codex/scripts/codex-companion.mjs`, 1027 lines, single CLI entrypoint with subcommands: `setup`, `review`, `adversarial-review`, `task`, `task-worker`, `status`, `result`, `task-resume-candidate`, `cancel`). Every slash command ultimately shells to `node ${CLAUDE_PLUGIN_ROOT}/scripts/codex-companion.mjs <subcommand>`.
3. **Codex transport layer** (`plugins/codex/scripts/lib/app-server.mjs`, `app-server-broker.mjs`, `broker-lifecycle.mjs`, `broker-endpoint.mjs`) — the broker + JSON-RPC client pair.

Data flow for a typical `/codex:review`:

```
Claude slash command
  -> node codex-companion.mjs review ...
     -> CodexAppServerClient.connect(cwd)
        -> ensureBrokerSession(cwd)                       [broker-lifecycle.mjs:113]
           -> spawn detached `node app-server-broker.mjs serve --endpoint unix:/tmp/cxc-XXXX/broker.sock`
              -> inside broker: spawn `codex app-server` once, own its stdio
                 -> broker.listen(unix socket)
        -> BrokerCodexAppServerClient connects to socket  [app-server.mjs:274]
        -> JSON-RPC "initialize" + "initialized"
        -> JSON-RPC "thread/start" -> "review/start"      [codex.mjs:914]
        -> streaming notifications routed back through socket
```

Both the broker daemon and each slash-command invocation speak the **same JSON-RPC 2.0 over newline-delimited JSON** protocol. The broker is transparent — it forwards most requests to the real `codex app-server` and proxies notifications back — but it adds admission control and a synthetic `broker/shutdown` method.

State directory: a per-workspace slug plus SHA-256 hash of the canonical workspace path, rooted at `${CLAUDE_PLUGIN_DATA}/state/` or `${tmpdir}/codex-companion/` (`plugins/codex/scripts/lib/state.mjs:29-44`). Jobs are stored as individual JSON files in `jobs/<job-id>.json` with per-job log files; `state.json` holds config (`stopReviewGate`) and the top-50 jobs list. Broker session metadata lives alongside at `broker.json` (`broker-lifecycle.mjs:13`, `:72-93`).

## Key Patterns

### 1. Broker daemon that multiplexes stdio into a Unix socket

`plugins/codex/scripts/app-server-broker.mjs` is the heart of the plugin. 252 lines. It:

- Spawns one `codex app-server` (via `CodexAppServerClient.connect(cwd, { disableBroker: true })`, `app-server-broker.mjs:68`) and registers a notification handler that routes **all** server-initiated notifications to whichever client socket currently "owns" the turn (`app-server-broker.mjs:84-100`).
- Listens on a Unix socket (non-Windows) or named pipe (Windows) and accepts multiple concurrent clients.
- Tracks two slots: `activeRequestSocket` (who is making a blocking request) and `activeStreamSocket` (who owns an in-flight streaming turn). They are allowed to be the same socket.
- Maintains `activeStreamThreadIds` so notifications for `turn/completed` only close the stream for the right thread (`app-server-broker.mjs:90-99`). This handles the detail that `review/start` creates a sub-thread (`reviewThreadId`) whose `turn/completed` must also release the slot.
- Rejects concurrent attempts with a JSON-RPC error using code `BROKER_BUSY_RPC_CODE = -32001` (`app-server.mjs:23`, sent at `app-server-broker.mjs:179`).
- Allows `turn/interrupt` to bypass the busy check when another socket's stream is active (`app-server-broker.mjs:170-171, 184-195`). Without this exception, you could never cancel a running Codex turn from a second Claude slash command.

The socket life cycle is split: **request socket** (for your `turn/start` reply) and **stream socket** (for the long tail of streaming notifications tied to that thread). The request socket clears on response; the stream socket clears on `turn/completed`. A shutdown path (`app-server-broker.mjs:102-114`, `:160-164`) is wired through a special `broker/shutdown` JSON-RPC method called from the `SessionEnd` hook (`broker-lifecycle.mjs:43-57`).

### 2. Transparent client abstraction

`CodexAppServerClient` (`plugins/codex/scripts/lib/app-server.mjs:331-350`) is a factory. `connect(cwd, options)` returns either a `BrokerCodexAppServerClient` (socket transport, default) or a `SpawnedCodexAppServerClient` (own child process, used inside the broker itself and by `disableBroker: true` callers). Both inherit from `AppServerClientBase` which implements the JSON-RPC framing — newline-delimited JSON over a byte stream, with an id-keyed `pending` map, a line buffer, and a notification handler slot (`app-server.mjs:56-180`). The two subclasses differ only in `initialize()` and `sendMessage()`.

The `transport` field (`"direct"` vs `"broker"`) is exposed on the client for diagnostics and is shown in setup output.

### 3. Opt-out notification capabilities

During initialize, the client tells the app server to stop sending delta notifications it never surfaces (`app-server.mjs:33-41`):

```
optOutNotificationMethods: [
  "item/agentMessage/delta",
  "item/reasoning/summaryTextDelta",
  "item/reasoning/summaryPartAdded",
  "item/reasoning/textDelta"
]
```

This is a bandwidth / noise optimization — the plugin aggregates final messages instead of streaming token-by-token, so it opts out of deltas at the protocol level rather than dropping them locally.

### 4. Thread persistence via Codex-native thread/list

Resume works because Codex itself owns the thread store. `findLatestTaskThread` (`plugins/codex/scripts/lib/codex.mjs:1031-1051`) calls `thread/list` with `searchTerm: TASK_THREAD_PREFIX` ("Codex Companion Task"), filters by name prefix, and returns the most recently updated thread. `runAppServerTurn` then calls `thread/resume` with that id (`codex.mjs:975`). The plugin names persistent threads `Codex Companion Task: <excerpt>` so it can distinguish its own from unrelated Codex threads.

`ephemeral: true` in `buildThreadParams` (`codex.mjs:56-66`) is the opt-out: reviews don't persist, tasks do (`codex.mjs:986-988`).

### 5. Structured review output contract

`plugins/codex/schemas/review-output.schema.json` is a Draft 2020-12 JSON Schema with a fixed shape: `verdict` (`approve` | `needs-attention`), `summary`, `findings[]` (each with severity, title, body, file, `line_start`, `line_end`, confidence 0-1, recommendation), `next_steps[]`. It is passed to Codex as `outputSchema` on `turn/start` (`codex.mjs:1010`, `codex-companion.mjs:412`). The adversarial review prompt (`plugins/codex/prompts/adversarial-review.md`) references this contract explicitly in an `<structured_output_contract>` XML block and instructs: use `needs-attention` for any material risk, every finding must include file + line range + confidence + concrete recommendation. Parsing happens in `parseStructuredOutput` (`codex.mjs:1057-1082`) with graceful fallback to raw text when JSON parse fails.

### 6. First-line protocol for the stop-gate

The review gate uses a tiny text protocol instead of structured output: the Codex task must produce a final answer whose first line starts with exactly `ALLOW:` or `BLOCK:` (`plugins/codex/prompts/stop-review-gate.md:17-19`). The hook parses only that first line (`scripts/stop-review-gate-hook.mjs:69-96`). If `BLOCK:`, the hook emits `{"decision": "block", "reason": ...}` on stdout (`:168-171`) which tells Claude Code to refuse to stop. Everything else (`ALLOW:`, empty output, unexpected text, crash, timeout) fails open to ALLOW or to a non-blocking log note. There's an explicit 15-minute timeout (`:16`), and the README carries a hard warning that the gate "can create a long-running Claude/Codex loop and may drain usage limits quickly" (`README.md:221-223`).

### 7. Adversarial review prompt design

`plugins/codex/prompts/adversarial-review.md` is a reusable masterclass in review prompting. Block structure: `<role>`, `<task>`, `<operating_stance>` (default skepticism), `<attack_surface>` (7 concrete failure classes including auth, data loss, rollback, races, empty-state, schema drift, observability gaps), `<review_method>`, `<finding_bar>` (the 4 questions every finding must answer), `<structured_output_contract>`, `<grounding_rules>` (defensible from context, no invented files/lines), `<calibration_rules>` (prefer one strong finding over many weak). Interpolation uses `{{TARGET_LABEL}}`, `{{USER_FOCUS}}`, `{{REVIEW_COLLECTION_GUIDANCE}}`, `{{REVIEW_INPUT}}` (`codex-companion.mjs:238-247`).

### 8. Subagent as thin forwarder

`plugins/codex/agents/codex-rescue.md` is explicit: "You are a thin forwarding wrapper." One Bash call, return stdout verbatim, no repo inspection, no polling, no summarization (`agents/codex-rescue.md:11-47`). The delegating `/codex:rescue` command (`commands/rescue.md:39-49`) repeats the rule: do not paraphrase, do not ask the subagent to inspect files, do not call `review`/`status`/`result`/`cancel`. This keeps the subagent's context window clean — it is essentially a typed dispatcher, not an agent.

### 9. Claude session partitioning

`SESSION_ID_ENV = "CODEX_COMPANION_SESSION_ID"` is written to the Claude env file at `SessionStart` (`session-lifecycle-hook.mjs:76-79`). All job listing and resume lookups then filter by that session id (`codex-companion.mjs:291-301`, `job-control.mjs:15-25`). At `SessionEnd` the hook terminates any jobs tagged with the current session and fires `broker/shutdown` so the broker process and its Unix socket are cleaned up (`session-lifecycle-hook.mjs:81-112`).

### 10. Background jobs via detached self-re-exec

Background tasks are implemented by detach-spawning the same script (`codex-companion.mjs:641-652`) as `task-worker --cwd <cwd> --job-id <id>`, with `detached: true`, `stdio: "ignore"`, `unref()`. The parent writes the queued job file with the full `request` payload, the worker reads it back (`handleTaskWorker`, `:795-838`), and executes via the exact same `executeTaskRun` path. No job queue library; just filesystem + detached Node processes.

## Detailed Findings

### Repository layout

- `plugins/codex/.claude-plugin/plugin.json` — plugin manifest, name=codex, version=1.0.3 (`.claude-plugin/plugin.json:1-9`).
- `.claude-plugin/marketplace.json` — marketplace manifest exposed at `openai/codex-plugin-cc` (top-level, `marketplace.json:1-22`).
- `plugins/codex/commands/*.md` — 7 slash commands. Each has frontmatter (`description`, `argument-hint`, `allowed-tools`, some with `disable-model-invocation: true`). `review.md` and `rescue.md` include AskUserQuestion flows with a "(Recommended)" suffix for the preferred option.
- `plugins/codex/agents/codex-rescue.md` — one subagent. `model: sonnet`, `tools: Bash`, uses skills `codex-cli-runtime` and `gpt-5-4-prompting`.
- `plugins/codex/skills/` — three user-invocable=false skills: `codex-cli-runtime` (invocation rules), `codex-result-handling` (how to present results; "CRITICAL: After presenting review findings, STOP. Do not make any code changes."), `gpt-5-4-prompting` (XML-block prompt recipe with references/).
- `plugins/codex/hooks/hooks.json` — SessionStart (5s), SessionEnd (5s), Stop (900s = 15 min).
- `plugins/codex/schemas/review-output.schema.json` — structured review output contract.
- `plugins/codex/prompts/{adversarial-review,stop-review-gate}.md` — the two template prompts loaded at runtime.
- No MCP server. Confirmed via grep: no `mcpServers` / `mcp_servers` / `mcp.json` anywhere in the tree.

### Files and line counts

```
plugins/codex/scripts/codex-companion.mjs             1027  # CLI entrypoint
plugins/codex/scripts/lib/codex.mjs                   1088  # thread/turn orchestration
plugins/codex/scripts/lib/render.mjs                   465  # output formatters
plugins/codex/scripts/lib/app-server.mjs               350  # JSON-RPC client + broker client
plugins/codex/scripts/lib/git.mjs                      346  # git target resolution
plugins/codex/scripts/lib/job-control.mjs              308  # status/result/cancel helpers
plugins/codex/scripts/app-server-broker.mjs            252  # broker daemon
plugins/codex/scripts/lib/broker-lifecycle.mjs         209  # spawn/teardown broker
plugins/codex/scripts/lib/tracked-jobs.mjs             204  # run + log + update state
plugins/codex/scripts/lib/state.mjs                    191  # workspace-scoped state
plugins/codex/scripts/stop-review-gate-hook.mjs        184
plugins/codex/scripts/lib/process.mjs                  135
plugins/codex/scripts/session-lifecycle-hook.mjs       131
plugins/codex/scripts/lib/args.mjs                     128
plugins/codex/scripts/lib/broker-endpoint.mjs           41
plugins/codex/scripts/lib/fs.mjs                        40
plugins/codex/scripts/lib/prompts.mjs                   13
plugins/codex/scripts/lib/workspace.mjs                  9
```

Total 5121 lines of runtime Node. `codex-companion.mjs` at 1027 lines is past the 700-line threshold Helioy convention favors for refactoring; `codex.mjs` at 1088 is similarly borderline. Both are single-purpose facades though, with behavior broken into small functions.

### JSON-RPC surface (from `app-server-protocol.d.ts:57-66`)

```
initialize            — handshake
thread/start          — create new Codex thread (ephemeral: true for reviews, false for tasks)
thread/resume         — continue a prior thread by id
thread/name/set       — label a persistent thread
thread/list           — enumerate threads (used by findLatestTaskThread)
review/start          — native Codex review, returns reviewThreadId
turn/start            — streaming user turn with optional outputSchema
turn/interrupt        — cancel a running turn (broker allows this during active stream)
```

Plus broker-only synthetic methods: `broker/shutdown` (id-based request → `{}` then `process.exit(0)`) and `initialize` / `initialized` (broker answers `{ userAgent: "codex-companion-broker" }` without forwarding; `app-server-broker.mjs:146-158`).

### Dependencies

- **Runtime**: zero. Only `node:` built-ins (`fs`, `net`, `path`, `os`, `process`, `child_process`, `readline`, `crypto`, `url`).
- **Dev**: `@types/node ^25.5.0`, `typescript ^6.0.2` (`package.json:18-21`).
- **External binaries**: `codex` (installed globally via `npm install -g @openai/codex`), `node` >=18.18, `git`. Auth delegated to `codex login` — the plugin shells to it but never handles tokens (`README.md:56-61`).
- **Type codegen**: `codex app-server generate-ts --out plugins/codex/.generated/app-server-types` at build time (`package.json:14`). The `tsconfig.app-server.json` (`:14-22`) runs `tsc --noEmit` for JSDoc type-checking only. Generated types are imported from `../../.generated/app-server-types/v2/index.js` in `app-server-protocol.d.ts:1-28`.

### Tests

Node's built-in test runner, 10 test files in `tests/`:

```
tests/broker-endpoint.test.mjs      # Unix vs Windows pipe endpoint shape
tests/runtime.test.mjs              # full runtime wiring via fake-codex-fixture.mjs
tests/commands.test.mjs             # command parsing
tests/state.test.mjs                # state/job persistence
tests/git.test.mjs, process.test.mjs, render.test.mjs, bump-version.test.mjs
tests/helpers.mjs, fake-codex-fixture.mjs
```

`fake-codex-fixture.mjs` is notable: it impersonates `codex app-server` so tests run without the real Codex binary.

### Broker endpoint format

From `plugins/codex/scripts/lib/broker-endpoint.mjs:10-17` and `:19-41`:

- Non-Windows: `unix:/tmp/cxc-XXXXXX/broker.sock` (temp dir created via `fs.mkdtempSync`).
- Windows: `pipe:\\.\pipe\cxc-XXXXXX-codex-app-server`, sanitized to `[A-Za-z0-9._-]`.
- Env var `CODEX_COMPANION_APP_SERVER_ENDPOINT` (`app-server.mjs:22`) lets external tooling or tests plug in a pre-existing broker.

## Dependencies

- **`codex` CLI** — provides the `app-server` subcommand (JSON-RPC server over stdio) and `app-server generate-ts` for type codegen.
- **Node ≥ 18.18** — uses `node:test`, `fs.mkdtempSync`, native fetch is not used.
- **git** — review target resolution in `plugins/codex/scripts/lib/git.mjs` (working-tree vs base-branch modes).
- **Claude Code plugin runtime** — exposes `${CLAUDE_PLUGIN_ROOT}`, `${CLAUDE_PLUGIN_DATA}`, `${CLAUDE_PROJECT_DIR}`, `${CLAUDE_ENV_FILE}`, hook event names, `AskUserQuestion` tool.

## Relevance to Helioy

### Nancy (`~/Dev/LLM/DEV/TMP/nancy`)

Commit `7e744fe` (`Add Codex live-path support to Nancy`) recently added Codex as a first-class live path. This plugin's transport pattern is directly applicable:

- **Adopt the broker + app-server JSON-RPC pattern for Nancy's Codex worker.** Instead of re-spawning `codex app-server` per sidecar, spawn once per workspace behind a Unix socket and multiplex. That gives Nancy: concurrent Claude worker requests, thread resume across workers, a single auth-ready Codex process per repo, and a clean `broker/shutdown` for teardown. `plugins/codex/scripts/app-server-broker.mjs:48-246` is a self-contained 200-line reference implementation.
- **Steal the `BROKER_BUSY` (-32001) policy.** When two Nancy workers race on the same Codex, the loser should get a structured busy error, not a blocking wait. Pairs well with Nancy's existing sidecar rotation (see commit `afed38e`).
- **Steal the request/stream socket split.** Request socket clears on response; stream socket clears on `turn/completed` for a matching thread id. This is the minimal state you need to correctly route streaming notifications back to the right worker (`app-server-broker.mjs:74-100`).
- **Steal the session-scoped state directory layout** (`state.mjs:29-44`). Per-workspace SHA-256 hash avoids cross-project collisions; plug it into Nancy's plugin-data conventions.
- **Steal the thread naming convention for resume** (`codex.mjs:1031-1051`). Prefix-based `thread/list` filter avoids Nancy needing its own thread registry.
- **Steal the detached self-re-exec pattern for background workers** (`codex-companion.mjs:641-680`). No job-queue dependency.
- **Adversarial review prompt** (`plugins/codex/prompts/adversarial-review.md`) is a ready-made prompt template for Nancy's review phase. XML-block structure is the same one used in Helioy's `gpt-5-4-prompting` skill references.

### manicure (Codex traffic inspector)

Key transport fact: **this plugin's Codex transport is newline-delimited JSON-RPC 2.0 over stdio and Unix sockets, not HTTP.** Implications:

- `codex app-server` reads/writes JSONL on stdin/stdout (`app-server.mjs:189-226`). An HTTP proxy is useless here.
- The broker re-frames that same JSONL over a Unix socket (`app-server-broker.mjs:118-223`). Each line is one complete JSON-RPC message.
- manicure must hook at one of two boundaries to observe traffic:
  1. **Stdio boundary** — inject between the broker and `codex app-server` by intercepting `codex app-server`'s stdin/stdout. Simplest: set `PATH` so a manicure shim replaces `codex`, then shell out to the real binary and tee every JSONL line.
  2. **Below the app-server process** — not feasible without Codex source changes; the app server itself is the JSON-RPC producer.
- Hooking at the Unix socket boundary works too: connect a second socket to the broker's endpoint as an observer, but the broker doesn't broadcast — it routes to the active owner — so passive observation requires broker modification. The stdio boundary is the right place.
- The env var `CODEX_COMPANION_APP_SERVER_ENDPOINT` (`app-server.mjs:22`) gives manicure a clean injection point: spawn manicure as the broker, have it expose its own socket and proxy to a real broker. Client code discovers it via env.
- JSONL framing is trivial to parse (read until `\n`, `JSON.parse`). Message kinds: request (`id` + `method` + `params`), response (`id` + `result` | `error`), notification (no `id`, has `method`).

### helioy-plugins / helioy-bus

- The declarative plugin surface (`plugins/codex/commands/*.md` with structured frontmatter including `argument-hint`, `allowed-tools`, `disable-model-invocation`) is the same shape Helioy plugins already use.
- The subagent-as-thin-forwarder pattern (`codex-rescue.md`) is a cleaner template than most Helioy agents. One-Bash-call contract keeps subagent context cheap.
- The `SESSION_ID_ENV` + `CLAUDE_ENV_FILE` pattern for passing session identity through hooks (`session-lifecycle-hook.mjs:34-39, 76-79`) is reusable for any Helioy plugin that wants per-Claude-session state.

## Sources Consulted

- `README.md` (306 lines)
- `package.json`, `tsconfig.app-server.json`, `.claude-plugin/marketplace.json`
- `plugins/codex/.claude-plugin/plugin.json`
- `plugins/codex/hooks/hooks.json`
- `plugins/codex/scripts/app-server-broker.mjs` (entire file)
- `plugins/codex/scripts/codex-companion.mjs` (entire file)
- `plugins/codex/scripts/stop-review-gate-hook.mjs` (entire file)
- `plugins/codex/scripts/session-lifecycle-hook.mjs` (entire file)
- `plugins/codex/scripts/lib/app-server.mjs` (entire file)
- `plugins/codex/scripts/lib/broker-lifecycle.mjs` (entire file)
- `plugins/codex/scripts/lib/broker-endpoint.mjs` (entire file)
- `plugins/codex/scripts/lib/app-server-protocol.d.ts`
- `plugins/codex/scripts/lib/state.mjs`, `job-control.mjs` (partial), `codex.mjs` (partial)
- `plugins/codex/commands/rescue.md`, `review.md`
- `plugins/codex/agents/codex-rescue.md`
- `plugins/codex/skills/codex-cli-runtime/SKILL.md`, `codex-result-handling/SKILL.md`, `gpt-5-4-prompting/SKILL.md`
- `plugins/codex/prompts/adversarial-review.md`, `stop-review-gate.md`
- `plugins/codex/schemas/review-output.schema.json`
- `tests/broker-endpoint.test.mjs` (sample)
- Clone commit: current `main` HEAD as of 2026-04-17 (shallow depth 50).

## Open Questions

- **Broker crash recovery.** If the detached broker dies mid-stream, `BrokerCodexAppServerClient.handleExit` rejects all pending requests (`app-server.mjs:162-175`). What is the user-visible behavior on the next slash command? Does `ensureBrokerSession` silently respawn, or does the stale `broker.json` need manual cleanup? `isBrokerEndpointReady` does a 150ms probe (`broker-lifecycle.mjs:102-111`) then tears down and respawns if unreachable, so the path looks self-healing, but I did not exercise a mid-stream kill.
- **Concurrency ceiling.** Only one active request + one active stream at a time. For Nancy, where many workers want Codex concurrently, is one-broker-per-workspace the right granularity or should Nancy run one broker per worker? Running one broker per worker would lose the thread-resume benefit but avoid head-of-line blocking.
- **Stream ownership when `review/start` creates a subthread.** `buildStreamThreadIds` (`app-server-broker.mjs:14-23`) tracks both `params.threadId` and `result.reviewThreadId`. I did not verify what happens when `turn/completed` fires for the parent thread before the review thread — which threadId wins the close check at `:90-99`? The code accepts either match, which seems correct but is worth a concrete test.
- **Stop-gate interaction with parallel background tasks.** The hook at `stop-review-gate-hook.mjs:105-110` runs `codex-companion.mjs task` which itself goes through the broker. If a background `task` is already running and holding the stream, the gate will hit `BROKER_BUSY`. Not clearly handled — likely a real loop-risk footgun that the README warning hints at.
- **Windows named-pipe permissions.** The sanitization at `broker-endpoint.mjs:4-8` strips anything non-alphanumeric from the pipe name but relies on default pipe ACLs. Multi-user Windows hosts might see cross-user access issues — not observed, just noted.
