---
title: multica-ai/multica review through the Helioy lens
type: research
tags: [github-review, agents, orchestration, websocket, helioy-bus, nancyr]
summary: Mature Linear-clone for managed coding agents (Go server + TS workspace + Electron desktop). Strong realtime infrastructure, weak as a borrow source for Helioy because most surface area is product (issues, comments, inbox, web app) rather than primitives. Heartbeat-pong hub with bounded ULID dedup, sharded Redis Stream relay, and unified agent-backend interface are the only orthogonal primitives.
status: active
source: github-researcher
confidence: high
created: 2026-04-28
updated: 2026-04-28
---

# multica-ai/multica review

## 1. Stats

22,348 stars, repo created 2026-01-13 (~3.5 months old), last commit 2026-04-28 (this morning), license is "Apache 2.0 with commercial restriction" (modified, hosted/embedded SaaS forbidden without commercial license — `LICENSE:1-20`). 17 contributors but heavily lopsided: top three accounts (Bohan Jiang 19, devv-eve 8, LinYushen 5) own most of git history; 11 others have a single commit. Cadence is brisk: ~1798 PRs merged in 3.5 months. CI present (`.github/workflows/ci.yml`, `desktop-smoke.yml`, `release.yml`). Stack is Go (Chi, sqlc, gorilla/websocket, Redis Streams, Postgres) + pnpm/Turborepo workspace (Next.js web, Electron desktop, shared `core` / `ui` / `views` packages). ~170k lines source, 42MB on disk. Goreleaser + Homebrew tap distribution. This is a real product with paying-customer pretensions, not a hobby repo.

## 2. Grade

**B−.** Production-grade engineering, but most of the codebase is Linear-clone product surface (issues, comments, inbox, labels, projects, member presence) that is irrelevant to Helioy. The orchestration core is solid but narrow in transferable scope. Sits next to claudex/metaharness on the calibration scale — same level of polish, similar "useful in 2-3 narrow places, skip the rest" verdict.

## 3. Primitives that transfer

1. **Heartbeat-pong WebSocket hub with bounded ULID dedup** (`server/internal/realtime/hub.go:97-100, 122-167, 729-760, 866-892`). 54s ping / 60s pongWait pattern, plus a 128-entry LRU `seenIDs` per client to dedup events that arrived first via local fast path and again via Redis relay. Critical detail captured in `HANDOFF_ARCHITECTURE_AUDIT.md:1-90` — the client must mirror the heartbeat or it gets silently disconnected and never knows. **Lands in: helioy-bus.** The current bus is python+tmux SQLite and lacks any liveness/dedup model; if it ever grows a network transport this is the reference.

2. **`onFirstSubscriber` / `onLastSubscriber` room lifecycle hooks** (`server/internal/realtime/hub.go:179-208, 277-345`). Room transitions 0↔1 fire callbacks so the Redis relay starts/stops `XREADGROUP` loops on demand, capping blocked Redis connections at `pod_count × shard_count` instead of `active_scope_count`. Elegant solution to the fanout-cost problem. **Lands in: helioy-bus.** When warroom.sh grows multi-host fan-out this is the pattern.

3. **Unified `agent.Backend` interface across 11 CLI runtimes** (`server/pkg/agent/agent.go:18-130`, plus per-CLI files `claude.go` / `codex.go` / `copilot.go` / `cursor.go` / `gemini.go` / `hermes.go` / `kimi.go` / `kiro.go` / `openclaw.go` / `opencode.go` / `pi.go`). Single `Execute(ctx, prompt, opts) (*Session, error)` returning a `Messages` channel + `Result` channel; per-backend struct adapts streaming JSON / ACP / app-server flavors into `MessageType` enum (`text`, `thinking`, `tool-use`, `tool-result`, `status`, `error`, `log`). `LaunchHeader` map (`agent.go:131-160`) gives users a one-line preview of *what command* their custom_args extend. **Lands in: nancyr.** Nancyr is the Rust orchestrator; this is exactly the abstraction it needs and the per-CLI files are concrete documentation of every modern agent's stdio contract.

4. **Sharded Redis Stream relay with FNV scope hashing** (`server/internal/realtime/sharded_stream_relay.go:62-200`). 8 fixed Redis Streams (`ws:relay:shard:N`), each pod runs one `XREAD BLOCK` per shard, FNV-1a hash of `scopeType+scopeID` picks the shard. Bounded resource cost, approximate `MAXLEN` retention, no consumer groups required. **Lands in: helioy-bus.** Skip until Helioy needs multi-host bus; then this is the off-the-shelf design.

## 4. Does NOT transfer

1. **Linear-clone product surface** (issues, comments, labels, projects, pins, reactions, inbox). 80% of `server/internal/handler/`, `server/internal/service/`, `apps/web/`, `packages/views/`. Helioy is not building a ticketing system; warroom + cm + nancyr cover task assignment via different abstractions.
2. **Electron desktop shell** (`apps/desktop/`). Helioy lives inside Claude Code and the terminal; no native shell ambition.
3. **Skill-management storage and UI** (`server/internal/daemon/local_skills.go`, `skills-lock.json`, `packages/views/skills/`). Helioy already has the helioy-tools plugin and per-CLI skill directories; multica's centralized skill registry is the wrong shape — it inverts ownership from CLI → server.
4. **Per-runtime skill-root mapping for 8 CLIs** (`server/internal/daemon/local_skills.go:50-95`). Useful as a *reference table* of where each CLI looks for skills, but no Helioy component needs to enumerate them.
5. **Postgres + sqlc + migrations stack** (`server/migrations/`, `server/sqlc.yaml`). Helioy primary memory is cm (SQLite) and fmm (SQLite); migrating to Postgres is a regression for solo-operator deployment.
6. **TanStack Query + Zustand state model.** Strong write-up in `CLAUDE.md` but Helioy has no comparable web frontend that would benefit.
7. **JWT + PAT + workspace membership auth tower** (`server/internal/auth/`, `server/internal/realtime/hub.go:23-32`). Multi-tenant SaaS plumbing; Helioy is single-operator.
8. **Modified-Apache "no SaaS" license.** Cannot copy code under this license without trouble; everything above must be re-implemented from the design, not lifted.
9. **Goreleaser + Homebrew tap distribution.** Helioy components ship via npm/PyPI/cargo and the Claude Code plugin marketplace; binary distribution is not the path.

## 5. Verdict

**Inspiration-only.** The four primitives above are worth studying, none worth copying. License forecloses code-lift; product surface is ~80% irrelevant; the transferable bits are well-documented patterns rather than novel inventions.

## 6. Why

Multica is a serious VC-shaped product attempting to be Linear for AI agents. Most of its value is product polish (presence, inbox, real-time UI, multi-runtime CLI coverage) — surface area Helioy intentionally does not pursue. The pieces that *are* relevant — agent-backend abstraction and the realtime hub — are general distributed-systems patterns that read better in multica's source than in any blog post, but they are not Helioy's bottleneck today. Helioy-bus is python+tmux with SQLite messaging, and that's adequate for the solo-operator warroom use case. Re-implementing multica's hub/relay before Helioy actually has multi-host pressure would be premature. The agent.Backend interface is the closest call: nancyr will need this abstraction eventually, and multica's 11 concrete implementations are a goldmine of "here's what stream-json from CLI X actually looks like." Treat it as the reference manual when nancyr grows beyond Claude Code, not as a vendor lock-in.

## 7. How to apply

- **nancyr:** when adding the second agent runtime (Codex or Cursor), read `server/pkg/agent/agent.go:18-160` and the relevant per-CLI file before designing the trait. Concretely: `agent.Backend.Execute → Session{Messages, Result}` is a clean Rust translation; the `MessageType` enum with `text|thinking|tool-use|tool-result|status|error|log` covers every modern agent's stdio contract. Don't reinvent the streaming parsers from scratch.
- **helioy-bus:** if/when warroom.sh grows past one host, read `server/internal/realtime/hub.go:179-345` for the on-first/on-last subscriber lifecycle pattern, then `sharded_stream_relay.go:62-200` for the bounded Redis relay. Until then, do not introduce Redis or websockets; tmux + SQLite is fine.
- **helioy-bus (smaller win, applicable now):** the heartbeat-pong dedup pattern (`hub.go:97-167`) is worth porting if helioy-bus mail grows network reach. Specifically the bounded `seenIDs` LRU with ULID event IDs prevents duplicate delivery without unbounded memory.
- **Skip:** local skill management (multica centralizes, Helioy distributes; opposite directions), the entire web/desktop layer, the Linear-clone domain model, the auth tower.

## 8. Artifact

`/Users/alphab/.mdx/research/multica-ai-multica.md`
