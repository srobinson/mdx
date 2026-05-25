---
title: a2aproject/a2a-rs — forensic review for Helioy helioy-bus A2A migration
type: research
tags: [github-review, a2a-rs, a2aproject, agntcy, cisco, linux-foundation, rust, a2a-protocol, agent2agent, json-rpc, grpc, tonic, sse, push-notifications, agent-card, helioy-bus, crates-io, official-sdk, depend-candidate]
summary: Official Linux-Foundation A2A Rust SDK (built by AGNTCY/Cisco, migrated into the canonical a2aproject org). Real, complete, multi-transport (JSON-RPC + REST + gRPC + SLIMRPC + SSE + push), 438 inline tests, all 7 crates published Apache-2.0 on crates.io. Implements A2A protocol v1.0 (not v1.2). Viable dependency for helioy-bus envelope emit/parse via a2a-lf + a2a-pb; vendor only if SLIMRPC/edition-2024 friction bites.
status: active
source: github-researcher
confidence: high
created: 2026-05-31
updated: 2026-05-31
---

# a2aproject/a2a-rs — forensic review

Source: https://github.com/a2aproject/a2a-rs · Artifact: `~/.mdx/research/a2aproject-a2a-rs.md`
Reviewed against local clone at `/tmp/a2a-rs-review`. Lens: is this a viable Rust dependency for the helioy-bus A2A-envelope migration? Default Helioy scope `global/project:helioy`.

## 1. Stats

28 stars, 9 forks, 6 open issues + 2 open PRs (gh API). Created 2026-04-03, last push 2026-05-27. **Real org-driven history, not an AI squash:** 81 commits in the shallow window, authored by 5 humans plus the release bot — Luca Muscariello (50), Mauro Sardara (10), 钊 景 / Linuxdazhao (2), Justin Gross (1), `github-actions[bot]` (18, all `chore: release` from release-plz). Conventional commits throughout (`feat(a2a-server):`, `fix(a2a-client):`, `test(helloworld):`), interop fixes against `a2a-go`/`a2a-java`, and explicit spec-tracking commits ("align error code mappings with upstream spec fix A2A#1627"). **CI is real:** `.github/workflows/{ci,coverage,release-rust}.yml` — build+clippy+fmt+test matrixed across ubuntu/macos/windows, codecov, plus a copyright-header gate. **LICENSE reality: genuine.** `LICENSE.md` is the full Apache-2.0 text (11,357 bytes); `gh api .../license` returns `spdx_id: Apache-2.0, path: LICENSE.md`; every source file carries `// Copyright AGNTCY Contributors` + `SPDX-License-Identifier: Apache-2.0`. The badge matches the grant. **LOC:** Rust 25,112 across 8 crates (a2a-server 5,455, a2a-pb 5,062, a2a-client 3,846, a2a 3,182, a2acli 2,468, examples 1,738, a2a-slimrpc 1,753, a2a-grpc 1,608) + a 796-line `a2a.proto`. **Releases:** per-package tags via release-plz; latest `a2a-server-lf-v0.4.0`, `a2a-grpc-v0.3.0`, `a2a-lf-v0.3.0`, `a2a-slimrpc-v0.1.13`, `a2a-cli-v0.1.5`. **crates.io: all 7 published and downloading** — `a2a-lf 0.3.0` (3654 dl), `a2a-client-lf 0.2.0` (3161), `a2a-server-lf 0.4.0` (2208), `a2a-pb 0.1.8` (3385), `a2a-grpc 0.3.0` (378), `a2a-slimrpc 0.1.13` (207), `a2a-cli 0.1.5` (126). edition 2024, MSRV 1.85. **0 `todo!`/`unimplemented!`.**

## 2. Grade

**B / solid B.** Sits clearly above the B− cluster (claudex, metaharness, revfactory-harness, cozodb, pbakaus/impeccable) and far above the C band (DeepDiagram, jammievae/Qbit). This is the inverse of the Qbit specimen: where Qbit was impressive-on-paper and untested-in-fact, a2a-rs is unglamorous-on-paper and real-in-fact. The trust delta is decisive — **this is an officially-adopted SDK in the canonical A2A org**, Apache-2.0 with a real grant, 438 inline tests, multi-OS CI with a coverage gate, conventional-commit history from named Cisco engineers, and 7 crates genuinely published to crates.io with download traffic. What keeps it off A−/A is maturity, not quality: 28 stars and a thin bus factor (one author, Muscariello, owns ~60% of commits), all crates pre-1.0 with active churn (reqwest 0.12→0.13, tonic→0.14, namespace migration to `-lf` mid-stream), edition-2024 bleeding edge, and a still-evolving upstream spec it tracks rather than freezes. It is the least mature of the official A2A SDKs (Python 1944★, JS 549★, Java 428★, Go 385★, .NET 236★ vs Rust 28★). Real, conformant, young.

## 3. Primitives that transfer

1. **The complete A2A v1.0 wire type model** — `a2a/src/types.rs` (1,065 lines). `Task`, `TaskStatus`, `TaskState`, `Message`, `Part`/`PartContent`, `Artifact`, `SendMessageRequest`/`Response`, `TaskPushNotificationConfig`, plus the full request/response set for get/list/cancel/subscribe. This is the canonical Rust rendering of the A2A envelope. For helioy-bus this is the directly-reusable core: depend on `a2a-lf` and your envelopes serialize wire-compatibly with the Go/Java/Python/.NET SDKs for free. **Landing target: helioy-bus** envelope layer.

2. **AgentCard discovery + protocol negotiation** — `a2a/src/agent_card.rs` (886 lines: `AgentCard`, `AgentInterface`, `AgentCapabilities`, `AgentSkill`, `AgentExtension`, the full `SecurityScheme` family — ApiKey/HttpAuth/OAuth2/OpenIdConnect/MutualTls — and `AgentCardSignature`) paired with `a2a-client/src/agent_card.rs` (`AgentCardResolver`) and `factory.rs` (`A2AClientFactory` picks a transport from the card's advertised interfaces). This is the discovery-then-negotiate pattern Helioy will want if bus peers ever advertise capabilities. **Landing target: identity-matters / session-matters** (capability descriptor) feeding the bus transport selection.

3. **Transport trait + factory abstraction** — `a2a-client/src/transport.rs` (`Transport` and `TransportFactory` traits) with four concrete impls behind one interface: `JsonRpcTransport`, `RestTransport`, gRPC (`a2a-grpc`), SLIMRPC (`a2a-slimrpc`). `A2AClient<T: Transport>` is generic for zero-cost static dispatch. Clean separation of envelope from carrier — exactly the shape helioy-bus needs to keep its custom JSON path while adding A2A. **Landing target: helioy-bus** transport seam.

4. **Server executor / handler model** — `a2a-server/src/executor.rs` (`AgentExecutor` trait), `handler.rs` (`RequestHandler`), `agent_card.rs` (`AgentCardProducer`), with REST + JSON-RPC bindings on axum, `sse.rs` for streaming, and a `push/` module (`push/sender.rs`, `push/store.rs`) implementing real push-notification delivery. The `task_store/` trait + in-memory impl is the pluggable persistence seam where Helioy would drop its SQLite outbox. **Landing target: helioy-bus** server side.

5. **Protobuf interop layer** — `a2a-pb` (5,062 LOC + 796-line `a2a.proto` + generated `lf.a2a.v1.rs`) provides native↔protobuf conversion (`pbconv.rs`) and ProtoJSON via pbjson. This is the cross-SDK interop guarantee: the same task can move as JSON-RPC, ProtoJSON, or gRPC and round-trip. Even if Helioy only ever speaks JSON, this crate is the proof that the type model is canonical. **Landing target: reference** for envelope fidelity.

## 4. Does NOT transfer

1. **A2A is v1.0, not v1.2 — correct the helioy-bus decision.** The repo pins `pub const VERSION = "1.0"` (`a2a/src/lib.rs:20`), `protocolVersion: "1.0"` in agent cards, and `TaskPushNotificationConfig v1.0.0`. The Helioy locked decision ("wrap custom JSON envelopes in A2A v1.2") names a version that does not exist in the current A2A protocol line. A2A uses semver and is at 1.0; there is no public v1.2. Before building, reconcile the decision text with the actual spec version, or the conformance target is fiction.

2. **SLIMRPC is Cisco-experimental, not core A2A — do not adopt it.** `a2a-slimrpc` depends on `agntcy-slim-bindings` (Cisco's experimental transport, repo `experimental-cpb-slimrpc`). It is an optional, isolated crate: verified that `a2a`/`a2a-client`/`a2a-server`/`a2a-pb` do **not** depend on it. Take the standard transports (JSON-RPC/REST/gRPC/SSE) and leave SLIMRPC on the shelf. Pulling it in would chain Helioy to a non-standard Cisco runtime.

3. **No idempotency / outbox / dedup layer exists here — that stays Helioy's job.** Grep for `idempoten|outbox|dedup|at-least-once` returns zero. The SDK gives you the envelope and the transport; the SQLite outbox and idempotency keys from the helioy-bus decision are Helioy-owned reliability machinery layered *on top*. a2a-rs is correctly scoped to protocol, not delivery semantics. Do not expect it to solve exactly-once.

4. **Pre-1.0 churn + edition 2024 + thin bus factor = pin hard, watch upstream.** All crates are pre-1.0 and visibly churning (mid-stream namespace migration to `-lf`, reqwest 0.12→0.13, tonic 0.13→0.14, prost→0.14). edition 2024 / MSRV 1.85 is aggressive. ~60% of commits are one author. None of this disqualifies it, but it means a Helioy dependency must pin exact versions and budget for breaking minor bumps — this is not a frozen 1.0 you set and forget.

5. **The full client/server framework is more than helioy-bus needs.** Helioy already owns its bus, control plane (session-matters), and runtime. Importing `a2a-server` (axum executor framework, 5,455 LOC) would duplicate transport ownership Helioy already has. The depend-worthy slice is narrow: `a2a-lf` (types) and `a2a-pb` (interop), not the whole stack.

## 5. Verdict

**Depend — narrowly.** Take `a2a-lf` (envelope types) and, if cross-SDK protobuf interop matters, `a2a-pb`, as real crates.io dependencies for helioy-bus envelope emit/parse. Skip `a2a-server`/`a2a-slimrpc` (framework + Cisco transport Helioy does not need). Vendor the type module only if edition-2024/MSRV-1.85 or pre-1.0 churn becomes intolerable — but the Apache-2.0 grant and live crate make depend the default, vendor the fallback, and clean-room reimplementation unnecessary.

## 6. Why

This is the official Rust SDK for the Agent2Agent protocol, and provenance is the whole story. The `a2aproject` org is the canonical home of A2A (the 24,069-star `A2A` spec repo, org description "Donated to the Linux Foundation by Google"). The Rust implementation was authored by AGNTCY (Cisco's open agent project — Muscariello and Sardara are Cisco engineers; every file says `Copyright AGNTCY`, the crate suffix `-lf` reads Linux Foundation, and pre-migration tags were `agntcy-a2a-*`) and migrated into the official org alongside the Python/JS/Java/Go/.NET SDKs. So the trust question the lens demands — official or community fork — resolves cleanly to **official, but the youngest sibling.** The implementation is substantively real: complete task/message/artifact/part/agent-card type model, four transports behind one trait, SSE streaming, working push notifications, ProtoJSON interop tested against the Go and Java SDKs, 438 inline tests, multi-OS CI with a coverage gate, all published Apache-2.0. For helioy-bus the practical consequence is that the hard, boring, conformance-critical work — getting the envelope bytes exactly right so they interoperate with every other A2A agent — is already done, tested, and on crates.io. Helioy should not reinvent it. The one correction the lens forces: the protocol is v1.0, not the v1.2 the locked decision assumes.

## 7. How to apply

- **helioy-bus**: add `a2a-lf = "0.3"` (pinned) as a dependency; map Helioy's custom JSON inter-agent envelope onto `a2a::types::{Message, Task, Part, Artifact}`. Emit/parse through these types so bus traffic is wire-compatible with the broader A2A ecosystem. Keep the SQLite outbox + idempotency layer entirely Helioy-side; the SDK does not and should not provide it.
- **Decision hygiene**: update the locked "helioy-bus migration path — A2A envelopes" decision to say **A2A v1.0**, not v1.2. Verify against `a2a-protocol.org` before committing the version to spec text. This is a factual correction, not a scope change.
- **Transport**: if the bus grows beyond JSON, reuse the `Transport`/`TransportFactory` shape from `a2a-client/src/transport.rs` as the seam, but write Helioy's own impls — do not import `a2a-server`'s axum framework (Helioy already owns transport via session-matters/runtime-matters). Explicitly exclude `a2a-slimrpc`.
- **Risk control**: pin exact minor versions; subscribe to release-plz tags; budget for pre-1.0 breaking bumps. If MSRV 1.85 / edition 2024 collides with Helioy's toolchain floor, vendor `a2a/src/types.rs` + `agent_card.rs` under Apache-2.0 attribution rather than forking the workspace.
- **No clean-room needed.** Unlike the no-license/no-test repos in prior reviews, this one is legally and technically safe to depend on or copy with attribution. The deliverable is this teardown plus the v1.0-vs-v1.2 correction.

## 8. Artifact

`~/.mdx/research/a2aproject-a2a-rs.md` (this file). Source line: `a2a/src/lib.rs:20` — `pub const VERSION: &str = "1.0";` (the load-bearing spec-version fact).
