---
title: helioy-bus vs multica realtime primitives — gap analysis
type: research
tags: [helioy-bus, multica, gap-analysis, realtime, websocket, redis-streams]
summary: Helioy-bus is single-host SQLite+tmux today. All three multica primitives (heartbeat-pong hub, room lifecycle hooks, sharded Redis relay) are network-transport patterns. None are needed-now; two are needed-when-multi-host, one is conditional on adopting websockets.
status: active
source: codebase-analyst
confidence: high
created: 2026-04-28
updated: 2026-04-28
---

# helioy-bus vs multica realtime primitives

## 1. Current state

**Heartbeat-pong WebSocket hub with bounded ULID dedup.** Helioy-bus has no websocket layer. The closest analogues are `agent_registry.heartbeat()` (`server/bus_server.py:127-136`) which refreshes `agents.last_seen` on demand, and lazy pruning via `reconciliation.prune_dead_agents()` driven by tmux pane existence (`server/bus_server.py:109`). There is no liveness ping cadence, no pong wait, no event-id dedup. Message identity is a UUID written into the JSON payload (`server/services/message.py:162`), but no consumer dedups on it because each message is delivered to exactly one inbox file under one recipient. The dedup-on-relay problem multica solves does not exist yet because there is no relay.

**`onFirstSubscriber` / `onLastSubscriber` room lifecycle hooks.** Helioy-bus has no room or subscription concept. The shape closest to a "room" is a warroom (`warroom_server.py`, `services/warroom.py`), but warroom membership is a control-plane spawn record, not a messaging subscription. Addressing is direct, role-based, or `*` broadcast resolved per-send by `_resolve_recipients` (`server/services/message.py:99-136`). There is no per-scope reader process to start or stop, so the multica capping argument (`pods × shards` vs `active_scopes`) does not apply.

**Sharded Redis Stream relay with FNV scope hashing.** Helioy-bus has no Redis, no streams, no cross-host fanout. Inbox delivery is `os.rename` into a per-recipient directory under `~/.helioy/bus/inbox/{to}/` (`server/services/message.py:182-194`), and the wakeup channel is `tmux send-keys` (`server/_tmux.py:111-146`). Both assume a single shared filesystem and a single tmux server. `_NUDGEABLE_RUNTIMES = {"claude", "codex"}` (`server/services/message.py:29`) is the only routing knob. Multi-host is not just unsupported, the design forecloses it.

## 2. Need-to-have-now vs defer

| Primitive | Verdict | Trigger |
|---|---|---|
| Heartbeat-pong + ULID dedup | **needed-when** helioy-bus grows a network transport (websocket or QUIC) AND has more than one delivery path per message | Today, single-path file delivery is exactly-once by `os.rename` atomicity. The dedup pattern is only load-bearing once a message can arrive twice. |
| `onFirstSubscriber` / `onLastSubscriber` | **needed-when** helioy-bus introduces per-scope reader loops with non-zero idle cost | Today, recipient lookup is a SQL query at send time, cost zero when no one sends. There is no idle-cost problem to solve. |
| Sharded Redis Stream relay | **skip-until** Helioy crosses a single host AND tmux ceases to be the wake channel | This is a multi-pod fanout pattern. Solo-operator deployment never crosses a host. Cross-host need has not surfaced in any active workstream. |

All three grade defer. None are bugs in the current bus.

## 3. Adoption order

Only one ordering constraint exists when the triggers fire:

1. Heartbeat-pong + dedup ships first, because it is transport-layer hygiene that any network bus needs regardless of fanout shape.
2. Room lifecycle hooks ship second, because they are a fanout optimization that presupposes a per-scope reader, which only exists once you have a relay or stream consumer.
3. Sharded Redis relay ships third, because it presupposes both bounded liveness (1) and per-scope start/stop (2) to avoid the unbounded-XREADGROUP problem multica avoids.

Without (1), (3) leaks duplicates. Without (2), (3) wastes connections. (2) without (3) is dead weight.

## 4. Effort sketch (Rust reimplementation, when triggered)

| Primitive | LoC est. | Files touched | Test surface |
|---|---|---|---|
| Heartbeat-pong + ULID dedup | 250 to 400 | new `transport/ws.rs`, new `dedup.rs` (LRU, 128 entries per peer), wire into a future Rust `bus_core` | unit tests for LRU eviction, integration test for ping/pong drop, fuzz dedup under reorder |
| Room lifecycle hooks | 150 to 250 | extend `transport/ws.rs` with `Room` map, callbacks `on_first` / `on_last` | unit tests for 0↔1 transitions under concurrent join/leave, leak test for reader-task cleanup |
| Sharded Redis relay | 400 to 600 | new `relay/redis_shards.rs`, new `hash/fnv.rs`, config for shard count, retention | integration tests with embedded `redis-server`, hash-distribution stats, MAXLEN behavior under burst |

These are floor estimates assuming you reuse `tokio-tungstenite`, `redis-rs`, and `fnv` crates. Doubling for ops + observability is realistic.

## 5. Risks / non-obvious traps

- **Heartbeat asymmetry.** Multica's `HANDOFF_ARCHITECTURE_AUDIT.md` notes the client must mirror heartbeats or be silently disconnected. A naive Rust port that only implements server-side ping will repeat the same trap. The MCP plugin layer would need explicit pong logic, and Claude Code is not a websocket client today, so this primitive is dead weight unless the MCP transport itself moves to websockets.
- **Dedup window sizing.** 128-entry LRU is multica's empirical pick. With higher fanout or chattier topics it underflows. Make the size configurable from the start; do not bake the constant.
- **Room callback reentrancy.** `on_first` / `on_last` fire from inside the subscriber map's lock in many naive implementations. Spawning the reader task synchronously from the callback deadlocks under concurrent join. Use a channel: callback enqueues a request, supervisor task acts on it.
- **FNV is not stable across reseeds.** Multica uses FNV-1a unsalted, which is fine. If you ever add a salt for tenant isolation, shard ownership shifts and in-flight messages route to the wrong reader. Pick salted-or-not at design time and never change it.
- **Redis Streams retention is approximate.** `MAXLEN ~` is fast but lossy under burst. Helioy-bus today has perfect message archival to disk; users will notice if relay-mode silently drops events. Either keep the inbox-archive promise on the receive side or document the new semantics loudly.
- **Tmux nudge does not survive multi-host.** The wakeup channel is `send-keys`. Cross-host bus needs a different wake mechanism (push notification, MCP server-sent event, or websocket peer). Adopting Redis relay without solving wake means messages arrive but recipients sit idle.
- **License pollution.** Multica's modified-Apache forbids SaaS hosting derivations. Re-implement from the design, never copy file-shapes or constants. Cite the patterns by behavior in commit messages, not by source path.

## 6. Punch list

When the triggers fire, in order:

1. Decide whether the network bus is a separate Rust crate or an extension to the Python server. If Rust, name it `helioy-bus-net` and house it next to `nancyr`.
2. Implement `transport/ws.rs` with `tokio-tungstenite`. Server pings on a 54s interval, drops peers that miss 60s pong wait. Mirror the multica timer values.
3. Implement `dedup.rs` with a 128-entry-default LRU keyed on `(peer_id, ulid)`. Insert on receive, query before deliver. Configurable size.
4. Add a behavioral test: peer joins, sender publishes, peer receives once even when message arrives via two paths. Use `tokio::test` with simulated dual-delivery.
5. Introduce `Room` keyed on scope-id. `on_first` and `on_last` hooks queued through a supervisor channel. No callback runs under the room map lock.
6. When multi-host pressure arrives, add `relay/redis_shards.rs`. Eight shards default, FNV-1a hash on `scope_type:scope_id`. One `XREAD BLOCK` task per shard per pod, started by the room supervisor's first-subscriber path.
7. Document the new semantics in `helioy-bus/SPEC.md` under a new "network transport" section. Mark the python file-inbox path as the local-host fast path; the relay is for cross-host only.
8. Until any of step 1's trigger is real, leave `helioy-bus/server/` alone. The current shape covers the solo-operator warroom case.

## 7. Artifact

`/Users/alphab/.mdx/research/helioy-bus-vs-multica-gap.md`
