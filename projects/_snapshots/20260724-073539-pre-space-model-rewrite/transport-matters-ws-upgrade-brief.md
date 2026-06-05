---
title: transport-matters — WebSocket upgrade pattern for Helioy daemons (brief)
type: projects
tags: [transport-matters, tm, websocket, http-upgrade, axum, hyper, mcp, session-matters, draft, brief]
summary: Design brief for handling WS upgrades in Helioy's HTTP-serving daemons (smd's user MCP, sm attach, sm logs --follow). Documents the framework-gap pattern, surveys axum/hyper/tower options, contrasts with BerriAI's TCP-proxy workaround, and recommends in-framework axum WebSocketUpgrade for v1 with a TCP-proxy fallback held in reserve.
status: draft
project: transport-matters
confidence: medium
created: 2026-05-18
updated: 2026-05-18
related: [session-matters-foundation-draft, runtime-matters-kubelet-draft, berriai-litellm-agent-platform, kubernetes-sigs-agent-sandbox, helioy-sm-codebase-2026-05, helioy-rtm-codebase-2026-05]
---

# transport-matters — WebSocket upgrade pattern for Helioy daemons (brief)

## Draft caveat

Scoped brief written 2026-05-18 to settle one question for transport-matters and its downstream consumer session-matters: how Helioy's HTTP-serving daemons handle WebSocket upgrades. Not a full transport-matters spec. Triggered by the BerriAI/litellm-agent-platform review (cm `019e34ba-881f-7971-924f-a978599015c2`), which surfaced a 402-LOC TCP-level reverse proxy (`server-proxy.mjs`) as workaround for Next.js App Router's upgrade-handling gap. The same gap is plausible in axum + hyper; this brief settles whether Helioy should preempt it.

## Status (2026-05-18)

session-matters v1 (`0.1.2`, 2026-05-17) ships no HTTP listener and no WebSocket surface. The brief's Option A recommendation remains pending; v1 deferred the HTTP question entirely by routing MCP through stdio-over-unix-socket (`sm mcp` → `McpBridge` RPC → `smd`). The three WS routes the brief specified (`/mcp`, `/attach/:session_id`, `/logs/:session_id?follow=true`) are future passes. The runtime-matters review confirms rtmd has no HTTP listener either, so transport-matters open question 4 (rtmd WS surface) closes as **no**. See `~/.mdx/research/helioy-sm-codebase-2026-05.md` and `~/.mdx/research/helioy-rtm-codebase-2026-05.md`.

## Why this brief now

session-matters v1 ships three WS-shaped surfaces on the same `smd` HTTP listener:

| Surface | Why WS | Status |
|---|---|---|
| `smd` user MCP server | MCP Streamable HTTP transport (current spec, supersedes the legacy stdio + SSE split) | future pass — v1 ships stdio MCP bridge, no HTTP listener |
| `sm attach <session>` | local terminal attaches to a session's TTY over a single duplex channel | future pass — v1 does not ship `/attach` |
| `sm logs --follow <session>` | server-streamed log tail with backpressure | future pass — v1 ships read-only / one-shot logs; `--follow` is CLI-side file tail |

All three need HTTP `Upgrade: websocket` on the same listener that serves non-WS HTTP routes. BerriAI hit this exact case with their framework choice and shipped a TCP proxy in front. Worth confirming Helioy does not need the same workaround before smd code lands.

## The framework gap explained

HTTP frameworks that own the full response lifecycle, writing status + headers + body through their own streams, often cannot cleanly hand the raw TCP socket off for protocol upgrades. The WebSocket handshake requires the server to send `101 Switching Protocols` and then take the socket back from HTTP land so it can speak the WS framing protocol directly.

The gap appears when:

1. Handler returns are abstractly typed (e.g., Next.js `Response`, some axum middleware that wraps responses in opaque streams)
2. A middleware layer buffers the response body before headers are flushed (compression, body-capturing tracing)
3. The framework's runtime serialises the response through its own writer before the upgrade can complete

BerriAI hit this with Next.js App Router. They had no escape hatch for the socket handoff after the `Response` was returned, so they put a 402-LOC TCP reverse proxy in front that sniffs the `Upgrade: websocket` header and routes raw socket traffic to a separate WS handler, with normal HTTP forwarded to Next.js.

## axum / hyper / tower survey

axum's `WebSocketUpgrade` extractor (in `axum::extract::ws` since axum 0.6, stable in 0.7) is the modern Rust answer. It handles the handshake + socket handoff cleanly via hyper's `on_upgrade` future. Usage shape:

```rust
async fn ws_handler(ws: WebSocketUpgrade) -> Response {
    ws.on_upgrade(|socket| async move {
        // socket is now a duplex WebSocket stream
    })
}
```

hyper's `on_upgrade` is the underlying primitive: takes a future that resolves to the upgraded `Upgraded` connection. Lower-level, more explicit, useful if axum's extractor abstraction does not fit.

tower-http's middleware ecosystem does NOT generally break upgrades. The upgrade flows through the layered stack via hyper extensions. Two named risks:

- **`tower_http::compression::CompressionLayer`** buffers the response body to compress it; this breaks upgrades because the body is never written. Mitigation: exclude WS routes from the compression layer, or place compression after the WS route is matched.
- **Body-capturing tracing layers** (any custom layer that reads the response body for logging) have the same failure mode. Same mitigation.

The rule that follows: every middleware layer added to smd's axum stack must include a unit test confirming a WS upgrade completes when that layer is in the stack.

## Three options for Helioy

### Option A: In-framework axum `WebSocketUpgrade`

smd uses axum routes for both regular HTTP and WS upgrades on the same listener, single binary, single port externally. Middleware stack must be upgrade-aware (testable in CI).

| Pro | Con |
|---|---|
| Idiomatic Rust + axum pattern | Future middleware additions are a footgun if upgrade-awareness is not tested |
| Single port, single deploy artifact, single TLS termination | All upgrade machinery lives in our code |
| Zero double-hop latency | |
| Smallest deployment YAML | |

### Option B: BerriAI-style TCP-level reverse proxy

Lightweight Rust TCP proxy (`smd-proxy`) sniffs the `Upgrade: websocket` header and forwards WS traffic to a separate handler binary; normal HTTP goes to smd. Two processes, two ports internally, single port externally.

| Pro | Con |
|---|---|
| Framework-agnostic, robust to any middleware addition | Two processes to manage, deploy, restart |
| Hard isolation of WS code path | Double-hop latency for every request |
| Useful if smd later switches HTTP framework | More YAML; more failure modes |

### Option C: Separate listeners on different ports

smd binds two listeners: HTTP on `:8443`, WS on `:8444`. No proxy, no overlap.

| Pro | Con |
|---|---|
| Hard separation, no upgrade machinery needed | Two ports to expose, two URLs for clients |
| Each listener can use the framework that fits best | Breaks the "one user MCP endpoint" narrative |
| Easier to firewall WS vs HTTP independently | LB / Ingress config doubles |

## Recommendation

**Option A (axum `WebSocketUpgrade`) for v1.**

Rationale:

1. axum's upgrade story is mature and well-documented; the extractor handles 99% of cases.
2. Helioy smd is single-product, single-binary; the framework-flexibility argument for Option B does not apply.
3. The upgrade-aware-middleware contract is testable in CI with a small fixture suite. As long as the test exists, the footgun is detected at PR time.
4. Latency budget: Option B adds a TCP proxy hop on every request, including non-WS HTTP. Option C splits the URL surface. Option A is the only one with zero overhead.

Hold Option B as fallback only if a future Helioy requirement forces a body-buffering middleware layer we cannot make upgrade-aware (e.g., transparent compression on all routes, end-to-end body-capturing audit).

Hold Option C as a pure-isolation fallback if a security review later requires WS traffic to terminate on a different listener.

## Concrete v1 work items if Option A holds

These items remain the prescription for the pass that introduces smd's HTTP listener. They were not done in v1 (v0.1.2) because no HTTP listener was added; MCP runs over the stdio bridge instead. Track for the pass that ships `/mcp`, `/attach`, or `/logs --follow` as a real HTTP route.

1. Add dependencies to smd workspace: `axum = "0.7"`, `tokio-tungstenite = "0.21"`, `futures-util = "0.3"`. Pin minor versions.
2. Spec smd's HTTP listener as a single axum router carrying regular HTTP routes + 3 WS routes: `/mcp` (Streamable HTTP transport), `/attach/:session_id`, `/logs/:session_id?follow=true`.
3. Build the upgrade-aware-middleware fixture: a route that returns a `WsUpgradeSucceeded(bool)` after a layered round-trip; CI runs the fixture against the full middleware stack on every PR.
4. Document the "no body-buffering middleware on WS routes" rule in smd's AGENTS.md.
5. Add a contract test that every WS route survives a synthetic LB shape that strips and re-injects the `Upgrade: websocket` header (mirrors BerriAI's ALB-subprotocol-token workaround need, in case Helioy ever runs behind an AWS ALB).

### Substrate already in place for a future `/attach`

v1 session-matters chose `forkpty` rather than plain `fork` for spawn (`sm-driver/src/inprocess.rs:23-26`). The pty master fd is held in `SpawnHandle`. When `/attach/:session_id` lands as a real WS route, the duplex side already has a fd to bridge; no second pty open needed, no re-parenting tricks. The v2 attach work consumes this substrate; the v1 driver choice was forward-looking.

## Open questions for `/linear-workflows`

1. **MCP Streamable HTTP transport: full-duplex WS or SSE?** The protocol spec went through revisions; check what current SDK clients expect before locking the smd `/mcp` route shape. Still open: v1 sidestepped by shipping the stdio bridge (`sm-cli/src/mcp/server.rs:7-36` ↔ `sm-daemon/src/mcp_bridge.rs:16-31`), so no HTTP transport shape is locked yet.
2. **`sm attach` framing: binary WS frames or JSON-RPC envelopes?** Binary is lower overhead; JSON-RPC is more inspectable. Decide before the shim socket protocol locks.
3. **Auth on WS routes: subprotocol or cookie/bearer?** Subprotocol is the most LB-portable (ALBs strip Authorization on upgrade per BerriAI's finding). Lean: subprotocol with a derived token (HMAC of session_id; see identity-matters v1 spec).
4. **Listener sharing between smd and rtmd.** Does rtmd's admin HTTP listener (for /diagnose, /healthz) also need WS for /attach forwarding from smd? Or does smd handle /attach end-to-end and rtmd never speaks WS?
5. **TLS strategy.** smd listener uses `rustls`. Does the WS upgrade preserve TLS termination cleanly through axum + hyper? Confirm in the fixture suite.

## Related

- Companion review: `berriai-litellm-agent-platform` (cm `019e34ba-881f-7971-924f-a978599015c2`) for the original TCP-proxy workaround context
- Peer (caller): `session-matters-foundation-draft` (smd's HTTP/WS surface lives here; this brief settles the upgrade pattern, smd's draft consumes the recommendation)
- Substrate (consideration): `runtime-matters-kubelet-draft` (rtmd may have its own WS needs for /attach pass-through; open question 4 above)
- Architectural anchor: `kubernetes-sigs/agent-sandbox` review (cm `019e3784-2194-7b91-87ae-84e3b3545767`) for the broader k8s endgame context — once runtime-matters consumes SandboxClaim, /attach traffic may need to flow through a Sandbox.status.ServiceFQDN target rather than direct to a local rtmd
