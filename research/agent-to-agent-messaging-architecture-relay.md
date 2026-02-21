---
title: Agent Relay — real-time agent-to-agent messaging architecture
type: research
tags: [multi-agent, message-bus, mcp, pty, rust, typescript, orchestration, competitive-landscape]
summary: Commercial-grade multi-agent comms layer (Rust broker + TS/Python SDKs) routing messages through a hosted WebSocket cloud and injecting them into terminal-native agent PTYs via MCP tools; overlaps heavily in scope with helioy-bus but takes an opposite architectural bet (cloud-routed + PTY injection vs local MCP mailbox).
status: active
source: github-researcher
confidence: high
created: 2026-04-20
updated: 2026-04-20
---

## Executive Summary

Agent Relay (github.com/AgentWorkforce/relay) is a well-funded, actively shipped multi-agent communication product from Agent Workforce Inc. Apache-2.0, 621 stars, TypeScript + Rust hybrid, v4.0.30 released today. It spawns terminal-native CLIs (Claude Code, Codex, Gemini CLI, OpenCode, Aider, Goose) inside Rust-managed PTYs, exposes an `mcp__relaycast__*` tool surface so agents can DM each other / post to channels / spawn workers, and routes everything through a hosted Relaycast cloud WebSocket. It is the nearest commercial competitor to helioy-bus in scope, but its architecture is the opposite bet: cloud-routed, PTY-injected, CLI-agnostic.

## 1. What it is

"Slack for agents." Real-time communication infrastructure, not a framework or harness. Agents keep running however they already run; Agent Relay sits beside them providing channels, DMs, inbox, reactions, presence, and workflow orchestration. Sold via npm (`@agent-relay/sdk`), pip (`agent-relay-sdk`), a curl installer, a Claude Code plugin, and a hosted cloud with a Next.js dashboard. Active and commercial: daily releases, 34 open issues, mature CI/release automation, Fly.io deployment config, OpenAPI spec, Swift package, Docker images.

Status: **active production product**, not a prototype. Backed by a company.

## 2. Architecture

**Languages:** Rust (broker, ~29k LOC), TypeScript (SDK + dashboard), Python SDK, Swift SDK. Monorepo with turbo + 18 workspace packages.

**Core abstractions:**
- **Broker** (`src/main.rs`, 6655 lines — monolith warning) — Rust binary `agent-relay-broker` with subcommands `init | pty | headless | wrap`. Single-binary install.
- **PTY Session** (`src/pty.rs`, `src/pty_worker.rs`) — wraps each agent CLI in a native PTY via `portable-pty` (cross-platform, replaced tmux).
- **MCP tool layer** — agents call `mcp__relaycast__message_dm_send(to, text)`, `post_message(channel, text)`, `agent_add(name, cli, task)`, `agent_remove`, `agent_list`, `message_inbox_check`.
- **Relaycast client** (`src/relaycast_ws.rs`) — WebSocket to hosted cloud; the broker is effectively a thin edge.
- **Injector** (`src/inject.rs`) — waits for agent idle (default 30s threshold), then writes `Relay message from X [id]: ...\n` into the agent's PTY stdin.
- **SDK** (`packages/sdk/`) — TS client driving the broker over stdio JSON-RPC. High-level `AgentRelay` wrapper with `spawn`, `waitForAgentReady`, `waitForIdle`, event hooks.
- **Workflow engine** (`packages/sdk/src/workflows/`) — DAG runner with YAML templates (`code-review`, `bug-fix`, `feature-dev`), `{{steps.X.output}}` chaining, builder API. Separate from the messaging layer.

**Transport:** stdio (SDK↔broker) + WebSocket over TLS (broker↔Relaycast cloud) + PTY (broker↔agent). No local socket option; message delivery is cloud-mediated by design.

**State model:** workspace-scoped (API key = workspace), presence tracked by Relaycast cloud. Local broker keeps `state.json`, `pending/` (in-flight deliveries), `credentials/`, plus a dedup cache (`src/dedup.rs` — bounded LRU with TTL, clean impl).

**Persistence:** JSONL message log via pluggable `StorageAdapter` (`packages/storage`). Adapters: JSONL, Memory, DLQ. Long-term history lives in Relaycast cloud.

**Protocol envelope** (`src/protocol.rs:PROTOCOL_VERSION = 1`): versioned, tagged enums for `SdkToBroker` / `BrokerToSdk`, structured `RelayDelivery`, `AgentSpec` with `runtime: Pty | Headless`, `HeadlessProvider: Claude | Opencode`, priority u8, thread_id, injection_mode `Wait | Steer`.

## 3. Comparison to helioy-bus / nancy

| Axis | Agent Relay | helioy-bus | Verdict |
|---|---|---|---|
| Transport | Hosted WebSocket cloud (Relaycast) | Local MCP tool calls | Opposite bets |
| Delivery | PTY stdin injection after idle | Mailbox polled by agent | Opposite bets |
| Agent lifecycle | Broker owns PTY, spawns/kills | External (warroom, user) | Relay is more opinionated |
| Cross-machine | First class | No | Relay wins |
| Offline / airgap | Requires internet | Works offline | helioy-bus wins |
| Multi-tenant | Workspace isolation via API key | Single user | Relay wins |
| Mental model | Slack for agents | Inbox for agents | Both valid |
| Lock-in | Relaycast SaaS | None | helioy-bus wins |
| Workflow DAG | Built-in (`WorkflowRunner`) | Delegated to nancy | Separate concern |

**Direct overlap:** DMs, broadcast (`to: "*"`), inbox check, agent list, presence. `mcp__relaycast__message_dm_send` vs helioy-bus `send_message`. `mcp__relaycast__agent_list` vs `list_agents`. `mcp__relaycast__message_inbox_check` vs `get_messages`. The warroom concept also appears as relay's `spawn`/`release` on channels.

**Things Relay does that Helioy does not:**
1. **Cross-machine / remote agents** via cloud routing. Helioy is strictly local.
2. **PTY-injection delivery** — shoves messages into the running agent's stdin when idle, rather than waiting for a polled `get_messages`. Solves the "agent never checks its inbox" problem directly at the transport layer. This is the most interesting divergence.
3. **Idle detection as a first-class primitive** (`onAgentIdle`, `waitForIdle`, configurable `idleThresholdSecs`) exposed in the SDK.
4. **Message injection modes** — `Wait` (queue until idle) vs `Steer` (interrupt immediately). Encodes a policy helioy-bus currently leaves implicit.
5. **Headless + PTY dual runtime** — same protocol supports both interactive CLIs and headless API-driven providers.
6. **Built-in dedup cache** with TTL + bounded size (`src/dedup.rs`) — worth copying verbatim.
7. **Priority queue with overflow policy** (`src/queue.rs:BoundedPriorityQueue`) — 5 priority buckets, drop-on-overflow semantics.
8. **ACP bridge** (`packages/acp-bridge`) — editors like Zed talk to relay via Agent Client Protocol.
9. **A2A server/transport** (`packages/sdk/src/communicate/a2a-*`) — implements Google's A2A protocol as a transport.
10. **Trajectory system** (`trail` CLI + `.trajectories/` tracked in git) — structured record of decisions/reflections for future agents. Orthogonal to messaging but complementary to Helioy's am/cm.

**Things Helioy does that Relay does not:**
- Geometric memory (am), structured context store (cm), ubiquitous language — Relay has zero semantic memory layer.
- Plugin-scoped MCP tool namespacing that composes with the user's existing Claude Code setup.
- No SaaS dependency.

## 4. Patterns worth stealing / avoiding

**Steal:**
- `src/dedup.rs` — bounded TTL dedup cache, ~100 lines, clean tests. Drop straight into helioy-bus if dedup becomes an issue.
- `src/redact.rs` — LazyLock regex array for api_key/token/bearer redaction before logs. Three lines, ships real value.
- `src/protocol.rs` — `PROTOCOL_VERSION: u32` + `ProtocolEnvelope<T>` with `v`, `type`, `request_id`, `payload`. Clean versioned envelope. Worth copying if helioy-bus versions its wire format.
- `MessageInjectionMode { Wait, Steer }` — formalizes the "do I wait for you to be idle or interrupt you now" policy. helioy-bus could adopt this as a message metadata field.
- `BoundedPriorityQueue` with `push_with_overflow_policy` returning the dropped item — cleaner than silent drops.
- The idle-threshold-before-inject pattern. Even if Helioy keeps its polled-mailbox model, surfacing `idleThresholdSecs` on warroom spawns would help.
- Self-echo filter (`src/routing.rs:is_self_echo`) — guards against dashboard-originated messages looping back to their sender while allowing legitimate local-target messages. Small but load-bearing.

**Avoid:**
- `src/main.rs` at 6655 lines and `src/helpers.rs` at 2026 lines are monoliths; `src/snippets.rs` at 3169 lines is a text blob. Violates Stuart's 700-line rule. If adopting ideas, reimplement smaller.
- The "agent bootstrap task" convention (`packages/sdk/src/relay-adapter.ts:26-36`) string-appends a protocol contract to every spawned agent's task prompt: "Send `ACK:` on receive, `DONE:` on complete." This is a load-bearing semi-formal protocol hidden in a prompt suffix. Fragile. Document the contract in an MCP resource instead.
- PTY injection after idle solves one problem (agents not checking inbox) by creating another: delivery timing depends on idle detection heuristics, and "idle" is ill-defined for streaming agents. Known limitation the docs acknowledge ("Messages can be lost if agent is busy").
- Cloud dependency. The broker without Relaycast is a paperweight. Open issue #748 proposes E2EE as a *future* feature. Payloads currently traverse Agent Workforce's servers in plaintext (TLS to their endpoint, but they can read it).

## 5. Red flags

| Item | Severity | Notes |
|---|---|---|
| Hosted-cloud dependency | Medium | Relaycast is a paid SaaS. Self-hosting path is not first-class. Stuart would not integrate this. |
| Test suite currently broken | Medium | Open issue #672 "Test Suite: 346 failures (cron detected)" is still open. Daily releases shipping anyway. |
| Telemetry / PostHog | Low | `src/telemetry.rs` + `TELEMETRY.md`; PostHog v5 upgrade shipped today. Opt-out present, but default is on. |
| Monolithic Rust files | Low | `main.rs` 6655 LOC, `listen_api.rs` 2200, `swarm.rs` 1709. Refactor debt, not a bug. |
| License | None | Apache-2.0, clean. Ideas portable. |
| Security | Low | TLS + API-key workspaces; redaction regex is three patterns only (easy to defeat); rate limiting is "server-side via Relaycast" i.e. outsourced. Not self-hostable. |
| Maintenance | Positive | 30+ releases in recent weeks, active issue triage, paid team. |
| Supply chain | Low | `prpm` (their own package manager) adds novelty; install.sh is 35KB of shell. |

## 6. Verdict

**Borrow ideas. Do not integrate. Do not collaborate.**

Reasoning:
- **Integrating** is off the table: hosted-SaaS dependency, prompt-injection delivery model, and the fact that Stuart already has helioy-bus and warroom in-tree. Adopting Relay means rewriting his orchestration layer around someone else's cloud.
- **Collaborating** is off the table: this is a funded commercial product with a team shipping daily. Any contribution gets absorbed into their roadmap, not yours.
- **Borrowing ideas** is the right play. Specifically lift: `MessageInjectionMode { Wait, Steer }` as a message metadata field, `dedup.rs` as-is, `redact.rs` pattern, versioned protocol envelope, and the `idleThresholdSecs` concept surfaced in warroom spawns. The PTY-injection trick is clever but not worth copying — helioy-bus's MCP-mailbox model is cleaner and aligns with Claude Code's native tool-calling loop.

One strategic note: Agent Relay has validated that there is commercial demand for this exact shape of product. That is useful market signal for Helioy positioning, even if the architectures diverge.

## Sources consulted

- `README.md`, `ARCHITECTURE.md` (690 lines — unusually thorough)
- `src/main.rs`, `src/protocol.rs`, `src/inject.rs`, `src/dedup.rs`, `src/redact.rs`, `src/routing.rs`, `src/queue.rs`, `src/message_bridge.rs`
- `Cargo.toml`, `package.json`
- `packages/sdk/src/relay-adapter.ts`, SDK layout
- `git log` (v4.0.2x–v4.0.30 release cadence)
- `gh api repos/AgentWorkforce/relay` (stars, forks, issues)
- Open issues #672 (test suite), #748 (E2EE proposal)

## Open questions

- How does Relaycast cloud handle message ordering across multiple broker instances? Not answered in ARCHITECTURE.md.
- What is the exact MCP server surface — is it a real MCP server the agent connects to, or is it simulated via PTY output parsing with structured-call conventions? Mixed signals in the docs.
- License of the Relaycast cloud SDK dep (`relaycast = "=1.0.0"` in Cargo.toml) — is that also Apache-2.0 or is the cloud client closed-source?
