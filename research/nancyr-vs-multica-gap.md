---
title: nancyr vs multica agent.Backend gap analysis
type: research
tags: [nancyr, multica, agent-backend, runtime-trait, gap-analysis]
summary: nancyr already has Claude-shaped Driver+DriverEvent abstractions adequate for today's single-runtime supervisor. Multica's agent.Backend interface is the right reference when nancyr adds a second CLI, not before. Verdict defer.
status: active
source: codebase-analyst
confidence: high
created: 2026-04-28
updated: 2026-04-28
---

# nancyr vs multica agent.Backend gap analysis

## 1. Current state

nancyr's runtime contracts live in two places:

- `crates/nancy-core/src/traits.rs:5-14` — `Driver` trait. Three methods: `spawn(&TaskSpec) -> WorkerSpec`, `send(&WorkerSpec, &Message)`, `stop(&WorkerSpec)`. Sync, no streaming.
- `crates/nancy-core/src/traits.rs:20-29` — `Runtime` trait. Process-level `exec/kill/is_alive`. One impl: `ProcessRuntime` at `crates/nancy-runtime/src/process.rs:22-61`.
- `crates/nancy-driver/src/cli.rs:9-77` — `CliDriver<R: Runtime>`. The only `Driver` impl. Hardcodes `"claude"` binary at line 18 and stream-json args at line 29.
- `crates/nancy-driver/src/stream.rs:13-50` — `StreamEvent` enum. Claude-Code-specific tag set: `system|assistant|user|result`.
- `crates/nancy-driver/src/stream.rs:95-123` — `DriverEvent` enum. Higher-level: `SessionStarted | Text | ToolUse | TokenUsage | Completed | ParseError`. mpsc::Sender delivery via `stream_events()` at `stream.rs:127`.

The gap vs a multi-runtime contract is real but contained:

- `Driver::spawn` returns synchronously without surfacing the event stream. Today the supervisor presumably wires `stream_events` separately. There is no per-driver `Session` type that bundles stdout channel + result future.
- `CliDriver` is parameterized only over `Runtime`, not over a `Backend` trait. `claude_bin` is a string field, not a discriminator.
- `StreamEvent` and `ContentBlock` are baked into the Claude stream-json schema. No abstraction layer between raw stream and `DriverEvent`.
- No `LaunchHeader` equivalent. There is no way to render "what command will I actually run" before spawn for user inspection.

This is the correct shape for a single-runtime supervisor. It is not a portable contract.

## 2. What multica's interface gives us

From the review artifact (`~/.mdx/research/multica-ai-multica.md:29` and section 7), the load-bearing pieces of `agent.Backend`:

1. **`Execute(ctx, prompt, opts) -> Session`** with `Session{Messages chan, Result chan}`. Single async entrypoint that returns both the streaming and terminal channels. Replaces nancyr's split between `Driver::spawn` and external `stream_events()`.
2. **`MessageType` enum**: `text | thinking | tool-use | tool-result | status | error | log`. Covers every modern agent's stdio contract, including the Codex-flavored streaming JSON, Cursor's ACP, and Gemini's app-server flavor.
3. **`LaunchHeader` map**: previews the resolved command line (binary + flags + custom_args) before exec. UX win for nancyr's `--dry-run` and `init` paths.
4. **Per-CLI files as a stdio reference manual**: each `claude.go`, `codex.go`, `cursor.go` etc. is a worked example of how that runtime frames its stream.

The noise to ignore: multica's auth tower, skill registry, presence model, anything tied to Linear-clone surface.

## 3. Need-to-have-now vs defer

| Element | Bucket | Reason |
|---|---|---|
| Backend trait with Execute → Session | needed-when nancyr spawns a second CLI | Today `CliDriver` is the only impl. A trait split with one impl is dead weight. |
| MessageType enum (text/thinking/tool-use/tool-result/status/error/log) | needed-when streaming Codex or Cursor | nancyr's `DriverEvent` already covers Text/ToolUse/Completed for Claude. `thinking` and `status` are the next obvious additions for Codex; revisit then. |
| LaunchHeader preview | nice-to-have, low cost | One method on `CliDriver` returning `Vec<String>`. Useful for `nancyr orient` / dry-run. Land independently. |
| Session{Messages, Result} bundling | needed-when async lifecycle exits CLI driver internals | Trade off: tightening the trait now forces the supervisor refactor without payoff. Defer until second runtime arrives. |
| Per-CLI cheat-sheet | needed-when adding that specific CLI | Read on demand, not now. |

The dominant signal: nancyr is single-runtime by design (`PROJECT.md:14`, "Wraps the Claude Code CLI subscription"). Stuart already runs Codex separately via `codex:codex-cli-runtime`. nancyr is not the place that needs an 11-CLI matrix.

**Verdict: defer.** Adopt the contract shape when adding the second runtime, not earlier. Do the LaunchHeader preview opportunistically.

## 4. Per-CLI cheat sheet inventory

If/when nancyr grows a second runtime, these are the multica per-CLI files worth pulling up first, ranked by likely transfer value:

1. **`server/pkg/agent/codex.go`** — Codex is the most likely second runtime given Stuart's existing usage. Concrete reference for Codex stream framing.
2. **`server/pkg/agent/claude.go`** — Cross-check against nancyr's existing `StreamEvent` parsing. If multica handles edge cases (interrupted streams, partial JSON, retry semantics) that nancyr does not, lift the patterns.
3. **`server/pkg/agent/cursor.go`** — Cursor uses ACP (Agent Communication Protocol), a different shape from stream-json. The translation layer to a unified MessageType is the interesting bit.
4. `server/pkg/agent/gemini.go` — App-server flavor. Useful only if Gemini CLI ever enters scope.
5. `server/pkg/agent/copilot.go` — GitHub Copilot CLI. Lowest priority; surface area Helioy does not pursue.

Skip Hermes, Kimi, Kiro, OpenClaw, OpenCode, Pi unless directly relevant.

## 5. Effort sketch

A defensible adoption when the second runtime arrives:

- Promote `Driver` trait to `Backend` with `execute(&self, task: TaskSpec) -> BackendSession` returning `{events: mpsc::Receiver<DriverEvent>, result: oneshot::Receiver<TaskResult>}`. ~30 LoC in `nancy-core/src/traits.rs`.
- Extend `DriverEvent` with `Thinking`, `Status`, `Error` variants. ~20 LoC in `nancy-driver/src/stream.rs` plus serde tests.
- Split `nancy-driver` into `nancy-driver/src/claude/` and `nancy-driver/src/codex/`. Roughly mirror `cli.rs` + `stream.rs` per backend. ~200 LoC for Codex parser plus tests.
- Add `Backend::launch_header() -> Vec<String>` returning the resolved argv. ~10 LoC per impl.
- Wire selection in `nancy-cli` via `--backend claude|codex` flag. ~30 LoC in CLI parsing + dispatch.

Total: ~300-400 LoC, 5-7 files touched, plus a per-backend integration test fixture (record real stream-json transcripts to `tests/fixtures/codex/*.jsonl`).

## 6. Risks and non-obvious traps

- **Async boundary:** multica's `Execute` returns channels; nancyr's `spawn` is sync. Bridging that means `Backend::execute` needs to be `async fn` or return a future. `async_trait` macro on a public trait pulls a heavy dependency; alternative is hand-rolled `Pin<Box<dyn Future>>` returning `BackendSession` whose internals are themselves channels. Pick now and avoid churn later.
- **Stream framing differences:** Codex emits OpenAI-style SSE inside a custom envelope, not newline-delimited JSON. nancyr's `BufReader::lines()` loop in `stream_events()` (`stream.rs:127`) will not work for Codex without a framer abstraction. Multica handles this per-CLI; nancyr will need a `Framer` trait or per-driver loop.
- **Tool-use vs tool-result asymmetry:** nancyr currently drops `ToolResult` content blocks (`stream.rs:171-173`). Multica preserves both as `tool-use` and `tool-result` MessageTypes. If nancyr's hook server ever needs to reason about results (it currently does not — token budget is tracked from `usage` only), this becomes load-bearing.
- **Send + Sync constraints:** `Driver: Send + Sync` is fine for `CliDriver<ProcessRuntime>` because both are unit-stateless. A future Codex backend that holds a long-lived HTTP client (connection pool) needs to be Send+Sync also; pick reqwest::Client (Arc-shared) over hyper raw.
- **License hygiene:** modified-Apache forecloses copying multica source. Read for design, type from scratch. Do not paste even small helpers.

## 7. Punch list

Defer until second runtime is on the roadmap. When that day arrives, in order:

1. `crates/nancy-core/src/traits.rs` — rename `Driver` to `Backend`. Add `async fn execute()` returning `BackendSession`. Add `fn launch_header() -> Vec<String>`. Mark `send/stop` for deprecation.
2. `crates/nancy-core/src/types.rs` — add `BackendSession { events: mpsc::Receiver<DriverEvent>, result: oneshot::Receiver<TaskResult> }`. Extend `DriverEvent` with `Thinking { text: String }`, `Status { phase: String }`, `Error { message: String }`.
3. `crates/nancy-driver/src/lib.rs` — split into `mod claude; mod codex;`. Move existing `cli.rs` + `stream.rs` under `claude/`.
4. `crates/nancy-driver/src/codex/mod.rs` — new. Reference multica's `server/pkg/agent/codex.go` for stream framing.
5. `crates/nancy-driver/src/codex/stream.rs` — Codex parser. Fixtures at `crates/nancy-driver/tests/fixtures/codex/*.jsonl`.
6. `crates/nancy-cli/src/main.rs` — add `--backend claude|codex` flag, dispatch via boxed `Backend`.
7. `crates/nancy-monitor/src/budget.rs` — verify token accounting still wires through `DriverEvent::TokenUsage` for both backends. Codex token reporting may differ.

For now, the only opportunistic change worth doing today: add `CliDriver::launch_header() -> Vec<String>` returning the resolved argv. Useful for `nancyr orient` and zero-risk.

## 8. Artifact

`/Users/alphab/.mdx/research/nancyr-vs-multica-gap.md`
