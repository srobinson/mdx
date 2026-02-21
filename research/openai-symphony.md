---
title: openai/symphony review for Helioy
type: research
tags: [github-review, orchestration, multi-agent, codex, elixir, otp, helioy-bus, nancyr]
summary: OpenAI's Symphony — a Linear-driven Codex orchestrator written in Elixir/OTP — is a substantive reference implementation paired with a 2,169-line language-agnostic SPEC. Worth borrowing concrete primitives for nancyr (orchestrator) and helioy-bus (observability/snapshot pattern), not the whole framework.
status: active
source: github-researcher
confidence: high
created: 2026-05-01
updated: 2026-05-01
---

# openai/symphony — Helioy review

## Stats

- Repo: https://github.com/openai/symphony
- Description: "Symphony turns project work into isolated, autonomous implementation runs, allowing teams to manage work instead of supervising coding agents."
- Stars: 20,406 (rocket-launched on the announcement; not organic compounding)
- Created: 2026-02-26 (~9 weeks old as of this review)
- Last push: 2026-04-27 (active)
- Contributors: 4 OpenAI employees, dominated by `frantic-openai` (9 commits); others 1 commit each. Single-author project for practical purposes.
- License: Apache-2.0
- Primary language: Elixir 95%, with shell, Python, CSS, Dockerfile traces
- Repo size: ~30 MB on disk (mostly the demo MP4 in `.github/media/`)
- Code: 5,517 LOC across `elixir/lib/symphony_elixir/` + 3,485 LOC web/codex/config submodules
- Tests: 8,760 LOC ExUnit; ~1.6:1 test:source ratio. Includes a real Linear+Codex live-e2e harness (`live_e2e_test.exs`, 802 LOC) that creates throwaway Linear projects.
- Docs: Top-level `SPEC.md` is 2,169 lines, RFC-2119-language, complete with reference algorithms in pseudocode (§16). README explicitly says "tell your favorite coding agent to build Symphony from this spec" — i.e. the spec is the deliverable, the Elixir code is just one implementation.
- CI: GitHub Actions, single workflow `make-all` running mise-managed Elixir build + tests on every PR/push. PR description linter as a second job.
- Posture: README labels the implementation a "low-key engineering preview for testing in trusted environments" and "prototype software intended for evaluation only and is presented as-is."
- Releases: zero tags, zero releases.

## Grade

**A−** — substance over marketing, despite the demo-video framing. The SPEC is a serious normative document with reference algorithms, failure model, and security guidance. The Elixir implementation is idiomatic OTP (GenServer + Task.Supervisor + Port + Phoenix LiveView) with solid path-safety, sandbox plumbing, and stall detection. Test depth signals this was actually exercised, not just shipped. Single-author velocity of ~9 commits suggests the author knew the design before starting. Loses against A territory only because (a) it is fundamentally tied to Linear + Codex, the abstraction boundary stops one layer short of multi-agent generality, and (b) the in-memory scheduler with no persistent state is a deliberate ceiling Stuart will outgrow.

## Primitives that transfer

### 1. SPEC-as-deliverable pattern → all of Helioy, especially nancyr

`SPEC.md` is the single most copyable artifact in the repo. 2,169 lines, RFC-2119, with explicit goals/non-goals, normalized domain model, complete reference algorithms in pseudocode (§16), failure-class taxonomy (§14.1), security boundaries (§15), and a test/validation matrix (§17). The README literally says: build your own from this spec. nancyr (Rust orchestrator WIP) should adopt this exact frame — write `SPEC.md` first, treat the Rust impl as one of N possible implementations, and accept community ports. This is the open-source equivalent of "build the ABI, not the binary," and it neutralizes the bus-factor problem of solo-built infrastructure.

Concrete sections worth lifting:
- §3.2 abstraction levels (Policy / Config / Coordination / Execution / Integration / Observability) — clean layering for nancyr.
- §4.1 entity definitions — every entity (Issue, Workspace, RunAttempt, LiveSession, RetryEntry, OrchestratorRuntimeState) has a typed-field list. nancyr should produce equivalents.
- §16 reference algorithms in pseudocode — language-agnostic and disambiguating.

### 2. Workflow-as-config (`WORKFLOW.md` with YAML front matter + Liquid prompt body) — DOES NOT TRANSFER

**Revised 2026-05-02.** Initially flagged as portable, this primitive is redundant with `~/.codex/skills/linear-workflows`, which already encodes Helioy's workflow contract on a stronger substrate. See "Does NOT transfer" §3 below for the full reasoning.

For reference, the Symphony shape: `elixir/WORKFLOW.md` is YAML front matter + Markdown/Liquid body. `workflow.ex:48-83` splits on `---` then parses YAML; `prompt_builder.ex:11-26` renders with `Solid` using `attempt` and `issue.*` variables; `workflow_store.ex:131-148` watches mtime/size/content-hash on a 1s poll and hot-reloads with last-known-good fallback (lines 117-129). Cleanly engineered, but solving a problem Helioy has already solved differently.

### 3. Per-issue workspace lifecycle with hooks + path-safety canonicalization → nancyr workspace manager

`workspace.ex` is the most directly portable concrete code. Lifecycle: `create_for_issue` → `after_create` hook (one-shot, gated on `created?` flag) → `before_run` → agent → `after_run` → eventual `before_remove`. Path safety in `path_safety.ex:1-50` canonicalizes through symlinks segment-by-segment with `File.lstat` and rejects paths that escape `workspace.root` even via symlink (`workspace.ex:358-398`). Hook execution has timeout-with-brutal-kill (`workspace.ex:299-315`). Remote workspaces over SSH use a marker-tagged stdout protocol (`__SYMPHONY_WORKSPACE__\t<created>\t<canonical_path>`) to avoid shell-quoting hell (`workspace.ex:48-79`, `parse_remote_workspace_output:412-433`).

Why this matters for Helioy: nancyr will need workspace isolation per agent task; the symlink-escape check is a real attack surface that a naive `Path.starts_with?` misses. The `after_create`-only-on-fresh-dir gate also matches what Stuart wants for a system that can resume across restarts.

References: `elixir/lib/symphony_elixir/workspace.ex:1-483`, `elixir/lib/symphony_elixir/path_safety.ex`.

### 4. JSON-RPC-over-stdio Codex client with stream demultiplexing → helioy-bus, nancyr

`codex/app_server.ex` (1,096 LOC) is a complete, working JSON-RPC 2.0 client over a stdio Port. Notable details:
- `:line` mode on the Port with `@port_line_bytes 1_048_576` and explicit `:eol`/`:noeol` chunk reassembly (`receive_loop:340-362`) — handles both line-terminated frames and oversized partials correctly.
- Strongly-typed message dispatch by `method` field, with a fallthrough that logs non-JSON stream output at debug or warning depending on whether it matches `(error|warn|warning|failed|fatal|panic|exception)` regex (`log_non_json_stream_line:966-980`).
- Tool-call loop where the client side fulfills a `linear_graphql` dynamic tool synchronously and sends the result back (`dynamic_tool.ex:29-43`, `app_server.ex` tool dispatch).
- Auto-approve answer-injection for non-interactive sessions: when the server asks for human input, reply with a canned string explaining "operator input is unavailable" rather than hanging (`app_server.ex:803-879`).

Helioy applications:
- helioy-bus already has a message protocol; the line-framed stdio stream-demux pattern is directly applicable to any local agent process. The `:eol`/`:noeol` reassembly is non-obvious and worth lifting verbatim into Rust equivalents (`tokio::io::AsyncBufRead` does this for you, but the *pattern* of "log surprising stderr at warn, expected at debug" is the lesson).
- Auto-answer-on-input pattern is a useful policy default for warroom-spawned agents that are running without an attached operator.

References: `elixir/lib/symphony_elixir/codex/app_server.ex:340-440`, `elixir/lib/symphony_elixir/codex/app_server.ex:835-920`, `elixir/lib/symphony_elixir/codex/dynamic_tool.ex`.

### 5. Snapshot/observability triad (GenServer.call snapshot + LiveView + JSON API) → helioy-bus

The orchestrator exposes runtime state via `Orchestrator.snapshot/0` (`orchestrator.ex:1083-1155`) which is a GenServer.call returning a structured map of running/retrying/totals/polling. `presenter.ex` then projects that snapshot to two surfaces: a Phoenix LiveView dashboard (`dashboard_live.ex`, 330 LOC) and a JSON API at `/api/v1/state`, `/api/v1/<issue_identifier>`, `/api/v1/refresh` (`observability_api_controller.ex`). One in-memory source of truth, two presentations.

Helioy application: helioy-bus needs an observability layer. The GenServer.call-snapshot pattern with timeout fallback to `:timeout` / `:unavailable` (lines 1086-1098) is the right shape — never block a long-running orchestrator on its dashboard's hiccup. Same projector pattern in Rust would be a `tokio::sync::watch` channel feeding both a TUI and an axum endpoint.

References: `elixir/lib/symphony_elixir/orchestrator.ex:1083-1170`, `elixir/lib/symphony_elixir_web/presenter.ex`.

### 6. Stalled-session detection + bounded-power exponential backoff → nancyr retry policy

`reconcile_stalled_running_issues` (`orchestrator.ex:448-487`) compares `now - max(last_codex_timestamp, started_at)` against `codex.stall_timeout_ms` and forces a restart-with-backoff if exceeded. `failure_retry_delay` (`orchestrator.ex:936-939`) caps `2^min(attempt-1, 10)` against `max_retry_backoff_ms` — so backoff is bounded both by attempt-power-cap (no integer overflow at attempt 64) and by configured ceiling. The continuation-vs-failure delay distinction (continuation = 1s for normal completions that should re-poll, failure = exponential) is a small but useful refinement.

References: `elixir/lib/symphony_elixir/orchestrator.ex:448-487`, `elixir/lib/symphony_elixir/orchestrator.ex:928-942`.

### 7. SSH-as-transport with port-shorthand parsing → nancyr distributed worker primitive (low priority)

`ssh.ex` shells out to `ssh -T <host> bash -lc <escaped-cmd>` and parses `host:port` shorthand into `-p` flag (`ssh.ex:67-95`). This is the entire distributed-worker plumbing in 100 lines. nancyr won't need this immediately, but when it does, the lesson is: don't write a custom transport; shell out to ssh, escape carefully, parse `host:port` for ergonomics, and you get free key management.

References: `elixir/lib/symphony_elixir/ssh.ex`.

## Does NOT transfer

### 1. Linear coupling

The whole tracker layer is Linear-shaped: `linear/client.ex` (586 LOC) is a hand-written GraphQL client, `linear_graphql` is the only dynamic tool exposed to Codex, the SPEC §11 is "Linear-Compatible" rather than "tracker-agnostic" (the abstraction promise leaks). Symphony is a Linear-to-Codex pipeline first and a generic orchestrator second. Helioy uses Linear too (the user has a Linear MCP server configured), but nancyr should not replicate Linear-specific GraphQL queries or the `linear_graphql` tool surface; treat it as one tracker behind a clean interface.

### 2. Phoenix LiveView dashboard

The LiveView observability UI (`dashboard_live.ex` 330 LOC, `status_dashboard.ex` 1,952 LOC for a TUI) is high-quality but irrelevant to Helioy. Stuart's surfaces are CLI + Claude Code + cm/am. Borrow the snapshot pattern, skip the rendering layer.

### 3. In-memory scheduler with no persistent state (deliberate)

§14.3 "Partial State Recovery (Restart)" explicitly says retry timers and live-session state do not survive a restart; recovery is via fresh tracker poll + filesystem inspection. This is fine for Symphony's scope but Helioy-bus and nancyr will want durable state (cm-backed, presumably). Do not borrow this constraint.

### 4. Codex app-server protocol coupling

The JSON-RPC method names (`thread/start`, `turn/start`, `turn/completed`, etc.) are Codex-specific. The framing pattern transfers; the methods do not. nancyr should define its own agent protocol and treat Codex as one possible backend.

### 5. The Elixir/OTP runtime story

"Why Elixir? Hot code reload, supervision trees" is real but not sellable to Stuart who is committed to Rust for nancyr. Don't get sucked into a language re-eval.

### 6. WORKFLOW.md format (revised 2026-05-02)

Initially listed under "Primitives that transfer." Reclassified after Stuart pointed at `~/.codex/skills/linear-workflows/`.

The substrate difference is the disqualifier:

| | Symphony WORKFLOW.md | Helioy linear-workflows |
|---|---|---|
| Substrate | YAML + Liquid file in repo | Linear issue graph (descriptions, statuses, relations) |
| Durable state | File-as-state, hot-reload, last-known-good | Linear-as-state; HANDOVER.md is coord only |
| Shape | Single per-repo policy file driving one Codex worker | Three explicit gates (planning / issue review / post-exec) with two-agent author/review loop |
| Outcomes | Implicit | Three named outcomes per gate (Ready / Blockers / Needs human) |

Symphony's WORKFLOW.md is one thin slice of what Helioy's linear-workflows already encodes, on a weaker substrate. Importing it would create a parallel mechanism — the ACE memorize → CLAUDE.md anti-pattern in different clothes. Skip.

## Verdict

**Borrow primitives.**

Specifically:
1. Adopt the SPEC.md-as-deliverable pattern for nancyr (highest-leverage move; biggest behavioral change for the project).
2. Port the workspace lifecycle + path-safety canonicalization into nancyr's workspace manager when it gets one. Symlink-escape rejection in particular is non-trivial and Symphony solved it cleanly.
3. Use the snapshot/projector pattern for helioy-bus observability when that becomes a need.

**Skip:** the WORKFLOW.md format. Redundant with `~/.codex/skills/linear-workflows`, which encodes Helioy's workflow contract on a stronger substrate (Linear-as-state vs file-as-state).

Do not adopt the whole framework. nancyr is not a Linear-to-Codex pipeline; it's a multi-agent orchestrator with a different problem shape (coordinating heterogeneous agents, not running Codex against issues).

## Why

This is substance, not marketing — but a specific kind of substance. OpenAI shipped:
- A normative spec good enough to reimplement from
- A working reference implementation with real test depth
- A clear "we are not maintaining this for production" disclaimer

That last item is the tell. They are not building a product; they are seeding a pattern. Read in context with the "harness engineering" blog post linked from the README, this is OpenAI's recommended shape for "agents-as-employees" pipelines in 2026 — repo-owned WORKFLOW.md, isolated workspace per task, idempotent reconciliation against a tracker, dispatcher with backoff. Helioy's nancyr is solving a partially-overlapping problem; the parts that overlap (workflow contract, workspace isolation, retry/reconcile loop) should reuse Symphony's vocabulary.

The 20K stars are the OpenAI announcement effect, not signal about quality. Discount them. Judge on the SPEC and the test ratio — both excellent.

## How to apply

In priority order:

1. **nancyr**: Open a SPEC.md draft this month modeled on Symphony's structure. Goals/Non-Goals → Domain Model → State Machine → Reference Algorithms → Failure Model → Security. Write it in nancyr's repo before writing more Rust. This unblocks community contribution and forces clarity on what nancyr is and is not. **Estimated effort**: 2-3 days of focused writing.

2. **Workflow contract**: keep `~/.codex/skills/linear-workflows` as the canonical mechanism. Do NOT port Symphony's WORKFLOW.md format; it would dilute a stronger substrate (Linear-as-state) with a weaker one (file-as-state).

3. **nancyr workspace manager**: When implementing isolation, port `path_safety.ex`'s symlink-aware canonicalization into Rust (it's ~50 lines; the algorithm — segment-by-segment lstat + readlink + recurse — is the part to copy, not the syntax). Reject workspaces whose canonical form escapes `workspace.root` even when the literal path is under it.

4. **helioy-bus**: When observability becomes a priority, use the GenServer.call-snapshot-with-timeout pattern. In Rust: a `tokio::sync::watch::Sender` owned by the orchestrator, with consumers (TUI, HTTP, future MCP exporter) on the `Receiver` side. Never block the orchestrator on a presentation-layer hiccup.

5. **helioy-plugins**: Consider whether skill SKILL.md files could adopt the front-matter + Liquid body shape (they nearly already do). Symphony's `.codex/skills/` directory is exactly the same shape as helioy-plugins skills. The convergence is interesting and probably worth aligning to.

## Architecture deep-dive (for future reference)

### Module layout

```
elixir/lib/symphony_elixir/
├── orchestrator.ex          1655 LOC  — GenServer poll loop, dispatch, retry, reconcile
├── codex/
│   ├── app_server.ex        1096 LOC  — JSON-RPC client over stdio Port
│   └── dynamic_tool.ex       209 LOC  — linear_graphql client-side tool impl
├── linear/
│   ├── adapter.ex             91 LOC  — Tracker behaviour impl
│   ├── client.ex             586 LOC  — Linear GraphQL client
│   └── issue.ex               43 LOC  — Issue struct
├── status_dashboard.ex      1952 LOC  — TUI rendering (skip)
├── config/schema.ex          557 LOC  — Ecto-based typed config
├── workspace.ex              483 LOC  — per-issue workspace lifecycle
├── agent_runner.ex           203 LOC  — single-issue execution loop
├── cli.ex                    191 LOC  — CLI entrypoint
├── specs_check.ex            175 LOC  — repo health checks
├── workflow_store.ex         153 LOC  — hot-reload watcher
├── config.ex                 154 LOC  — typed accessors
├── workflow.ex               123 LOC  — YAML front matter + body parser
├── ssh.ex                    100 LOC  — ssh shell-out
├── http_server.ex             88 LOC
├── log_file.ex                80 LOC
├── prompt_builder.ex          64 LOC  — Liquid render
├── path_safety.ex             50 LOC  — symlink-safe canonicalization
├── tracker.ex                 46 LOC  — Tracker behaviour
└── tracker/memory.ex          72 LOC  — in-memory tracker for tests
```

### Concurrency model

- One supervised `Orchestrator` GenServer (`use GenServer`).
- `Task.Supervisor.SymphonyElixir.TaskSupervisor` owns per-issue agent worker tasks, monitored by ref so the orchestrator gets `{:DOWN, ref, :process, _, reason}` on exit (`orchestrator.ex:119-164`).
- `WorkflowStore` GenServer polls `WORKFLOW.md` mtime every 1s; orchestrator pulls latest from store at each tick.
- Optional Phoenix endpoint runs Bandit + LiveView for dashboard.

### Test posture

`make all` → format check + Credo + Dialyzer + ExUnit. Live e2e (`make e2e`) creates real Linear projects, optionally spins up Docker SSH workers, mounts host `~/.codex/auth.json`, and runs the full pipeline including issue-comment writes. This level of integration testing is unusual for a "preview" — it's prototype-quality only in the README disclaimer, not in the code.

## Sources consulted

- `README.md`, `SPEC.md`, `elixir/README.md`, `elixir/WORKFLOW.md`
- `elixir/lib/symphony_elixir/orchestrator.ex` (~1200 LOC read)
- `elixir/lib/symphony_elixir/codex/app_server.ex` (full)
- `elixir/lib/symphony_elixir/codex/dynamic_tool.ex` (full)
- `elixir/lib/symphony_elixir/workspace.ex` (full)
- `elixir/lib/symphony_elixir/path_safety.ex` (full)
- `elixir/lib/symphony_elixir/workflow.ex` and `workflow_store.ex` (full)
- `elixir/lib/symphony_elixir/agent_runner.ex` (full)
- `elixir/lib/symphony_elixir/prompt_builder.ex` (full)
- `elixir/lib/symphony_elixir/ssh.ex` (full)
- `elixir/lib/symphony_elixir/linear/adapter.ex` (full)
- `elixir/lib/symphony_elixir/config/schema.ex` (partial)
- `elixir/lib/symphony_elixir_web/presenter.ex` (full)
- `.codex/skills/land/SKILL.md` (full)
- `.github/workflows/make-all.yml`
- `gh repo view openai/symphony` metadata; `gh api repos/openai/symphony/contributors`

## Open questions

- How does the SPEC handle multi-tracker (e.g. Linear + GitHub Issues simultaneously) at scale? §11 sketches the Tracker contract but every concrete reference is Linear-shaped.
- Is `frantic-openai` a known author? (Likely "Stas" / Stanislav, based on prior OpenAI repos.) If yes, is there a Twitter/blog post pairing that explains the design choices?
- Does the `harness engineering` blog post linked from README describe the policy layer in more detail than `WORKFLOW.md` shows?
