---
title: "Codex CLI: Header Identity Audit for Transport-Matters Flow Discrimination"
type: research
tags: [codex, headers, transport-matters, websocket, http-fallback, session-id, thread-id, mitmproxy]
summary: Header-by-header inventory of what Codex CLI sends on the WS upgrade and HTTP fallback POST, with per-header lifetime. Three discrimination cases (WS-fail-retry, next-turn, separate session) resolve cleanly when Transport Matters parses `x-codex-turn-metadata.turn_id`; without that header-value parsing, Case 1 and Case 2 require HTTP transport-pair correlation.
status: active
confidence: high
created: 2026-05-14
updated: 2026-05-14
---

# Codex CLI: Header Identity Audit for Transport-Matters Flow Discrimination

Source tree inspected: `openai/codex` at `main` (local clone `/tmp/codex-clone`, commit `12bfb57`, 2026-05-14). All file:line citations are against that snapshot. The prior research doc (`codex-cli-ws-http-fallback-mechanism.md`) cites the same files; nontrivial divergences are flagged explicitly in Section A and the Verdict.

## Correction to the prior research doc

The prior doc (`codex-cli-ws-http-fallback-mechanism.md` line 158, 230, 235) attributes `x-client-request-id` to the **HTTP path only**. That is wrong on current `main`. The WebSocket upgrade also carries `x-client-request-id = thread_id` (`codex-rs/core/src/client.rs:903-904`), and the WS integration test asserts this (`codex-rs/core/tests/suite/client_websockets.rs:130-133`). The value is identical on both transports. The HTTP-only framing of `x-client-request-id` in the prior doc led to its mention as a stitching key on lines 163, 235; that recommendation still works, but the header is not a transport discriminator and never was.

Also worth noting against the prior doc:

- The prior doc lists `session_id` and `thread_id` as headers on both transports (line 76, 85, 235). The actual emitted header names are kebab-case only: `session-id` and `thread-id` (`codex-rs/codex-api/src/requests/headers.rs:8,11`). The underscore-cased forms do not appear on the wire as Codex-emitted headers. HTTP header names are case-insensitive on the wire, but a literal `session_id`/`thread_id` (with underscores) is not what Codex sends.
- `x-codex-installation-id` is NOT sent as a header on the regular `/responses` WS or HTTP turn requests. It only appears as a **JSON body** field inside `client_metadata` (`codex-rs/core/src/client.rs:760-763`). The only request path where `x-codex-installation-id` is a real HTTP header is the `/responses/compact` endpoint (`codex-rs/core/src/client.rs:489-490`). Transport-matters cannot read it from headers alone for the turn flows.

## Section A: Exact header inventory

Every Codex-emitted header on the request side. Lower-case names below are the on-wire forms; original casing in the source is preserved in parentheses where it differs.

### A.1 WebSocket upgrade (`GET wss://chatgpt.com/backend-api/codex/responses`)

Headers attached by `ResponsesWebsocketClient::connect` (`codex-rs/codex-api/src/endpoint/responses_websocket.rs:369-394`) via `merge_request_headers(provider.headers, extra_headers, default_headers)`. The three layers:

1. **`provider.headers`**: config-time provider headers. Empty for the built-in `openai` provider (`codex-rs/codex-api/src/provider.rs:47`).
2. **`extra_headers`**: produced by `ModelClient::build_websocket_headers` (`codex-rs/core/src/client.rs:890-922`):
   - `openai-beta` (`OpenAI-Beta`) = `responses_websockets=2026-02-06` (`client.rs:912-914`; constant at `client.rs:146`).
   - `x-client-request-id` = `thread_id` (`client.rs:903-904`). **New finding vs. prior doc.**
   - `session-id` = `session_id` (`requests/headers.rs:8`, via `build_session_headers` at `client.rs:906`).
   - `thread-id` = `thread_id` (`requests/headers.rs:11`).
   - `x-codex-window-id` = `"{thread_id}:{window_generation}"` (`client.rs:620-621`, via `build_responses_identity_headers` at `client.rs:907`; format at `client.rs:382-386`).
   - `x-openai-subagent` = subagent label, only when session is a sub-agent (`client.rs:599`, via `build_subagent_headers` invoked from `build_responses_identity_headers` at `client.rs:614`). Absent for normal root CLI invocations.
   - `x-codex-parent-thread-id` = parent thread, sub-agent `ThreadSpawn` only (`client.rs:618`). Absent for normal CLI.
   - `x-openai-memgen-request` = `"true"` for memory consolidation sub-agent only (`client.rs:606-607`). Absent for normal CLI.
   - `x-codex-beta-features` = comma-separated beta feature keys when set (`client.rs:1661`, via `build_responses_headers`).
   - `x-codex-turn-state` = sticky-routing token, **only after** the first WS upgrade response of the turn populates it (`client.rs:1663-1668`; populated at `responses_websocket.rs:525-532`). Absent on the first attempt of a turn.
   - `x-codex-turn-metadata` = JSON-encoded turn metadata when present (`client.rs:1669-1671`).
   - `x-oai-attestation` (`X_OAI_ATTESTATION_HEADER`) when attestation is enabled (`client.rs:908-910`).
   - `x-responsesapi-include-timing-metrics` = `"true"` when timing metrics feature is enabled (`client.rs:915-920`).
3. **`default_headers`**: process-wide defaults from `codex_login::default_client::default_headers()` (`codex-rs/login/src/auth/default_client.rs:232-248`):
   - `originator` = `codex_cli_rs` (configurable via `CODEX_INTERNAL_ORIGINATOR_OVERRIDE`, `default_client.rs:36-37`).
   - `user-agent` (`User-Agent`) = `codex_cli_rs/<crate-version> (<OS> <OS-version>; <arch>) <user_agent_suffix>` (`default_client.rs:133-157`).
   - `x-openai-internal-codex-residency` = `"us"` for residency-pinned builds (`default_client.rs:38, 238-246`). Absent in default builds.
4. **Auth layer**: `self.auth.add_auth_headers(&mut headers)` after the merge (`responses_websocket.rs:383`):
   - `authorization` (`Authorization`) = `Bearer <access-token>` for ChatGPT bearer auth (`bearer_auth_provider.rs:33-36`), or signed ed25519 header for agent identity (`model-provider/src/auth.rs:36-40`).
   - `chatgpt-account-id` (`ChatGPT-Account-ID`) = ChatGPT account id (`bearer_auth_provider.rs:38-41` and `model-provider/src/auth.rs:42-44`). Note literal casing has `ID` uppercase.
   - `x-openai-fedramp` = `"true"` for fedramp accounts only (`bearer_auth_provider.rs:43-44`).
5. **Tungstenite-added RFC 6455 handshake headers** (added by `into_client_request` at `responses_websocket.rs:481`):
   - `connection: Upgrade`
   - `upgrade: websocket`
   - `host: chatgpt.com`
   - `sec-websocket-key`: fresh random per attempt
   - `sec-websocket-version: 13`

`x-codex-inference-call-id` is NOT added on the WS upgrade (only HTTP path calls `inference_trace_attempt.add_request_headers`; see Section A.2 below).

### A.2 HTTP fallback POST (`POST https://chatgpt.com/backend-api/codex/responses`)

Headers attached by `ResponsesClient::stream_request` (`codex-rs/codex-api/src/endpoint/responses.rs:70-100`). Construction order:

1. **`extra_headers`**: produced by `ModelClientSession::build_responses_options` (`codex-rs/core/src/client.rs:959-986`):
   - Same `build_responses_headers` contribution as WS: `x-codex-beta-features`, `x-codex-turn-state`, `x-codex-turn-metadata`.
   - Same `build_responses_identity_headers` contribution: `x-codex-window-id`, optional sub-agent set.
   - `x-oai-attestation` when enabled.
2. **`inference_trace_attempt.add_request_headers`** (`client.rs:1254`, → `rollout-trace/src/inference.rs:155-167`):
   - `x-codex-inference-call-id` = fresh UUID v4 per **attempt** (`rollout-trace/src/inference.rs:343-345`). **HTTP-only**; not present on WS.
3. **In `stream_request`** itself (`responses.rs:91-97`):
   - `x-client-request-id` = `thread_id` (`responses.rs:91-92`).
   - `session-id` = `session_id` (`responses.rs:94`, via `build_session_headers`).
   - `thread-id` = `thread_id`.
   - `x-openai-subagent` = subagent label when present (`responses.rs:95-97`). Note: this is set in the inner client too via `build_subagent_headers`, so it appears once.
4. **`stream` callback** (`responses.rs:136-142`):
   - `accept` (`Accept`) = `text/event-stream`.
   - Request compression header (`content-encoding: zstd`) is added by the underlying `ReqwestTransport` when `RequestCompression::Zstd` is selected (`responses.rs:124-128`).
5. **Process-wide reqwest defaults**: same `originator`, `user-agent`, optional residency header as the WS path (`default_client.rs:232-248`), applied via `Client::default_headers` (`default_client.rs:223`).
6. **Auth layer**: `self.auth.add_auth_headers(&mut headers)` in `EndpointSession::stream_with` (verify at `codex-api/src/auth.rs:57`, `codex-api/src/endpoint/session.rs`). Same `authorization`, `chatgpt-account-id`, optional `x-openai-fedramp` as WS.

### A.3 `response.processed` WS client-to-server ack

This is a JSON frame **inside an already-open WS connection** (`codex-rs/core/src/client.rs:942-952`, → `responses_websocket.rs:220`). Not a new HTTP request, so no headers. A mitmproxy capture sees it as a binary/text WS data frame on the WS flow, not as a separate flow with its own header set.

## Section B: Identity lifetime for every candidate header

For each header, "session" means one `codex` CLI invocation (one `ModelClient` instantiation at `session/session.rs:872`). "Turn" means one user prompt = one `TurnContext` (`turn_context.rs:494`) = one `ModelClientSession` from `client.new_session()` (`client.rs:358`, called per turn at `session/turn.rs:156`). "Attempt" means one iteration of the retry loop inside `try_run_sampling_request` (`session/turn.rs:1055`).

| Header | Source (file:line) | Lifetime | Changes on new CLI invocation | Changes on WS-fail→HTTP flip | Changes on new turn | Changes on retry within turn | Changes between WS frames in a turn |
|---|---|---|---|---|---|---|---|
| `session-id` | `state.session_id` set once at `session/session.rs:808-812` (= `thread_id` for root CLI); read at `client.rs:896, 906, 499`; emitted by `requests/headers.rs:8` | Per CLI invocation | YES (fresh UUID v7 at startup) | NO | NO | NO | NO |
| `thread-id` | `state.thread_id` set once at session start; read at `client.rs:897, 906, 500, 743`; emitted by `requests/headers.rs:11` | Per CLI invocation (= `session-id` for root) | YES | NO | NO | NO | NO |
| `x-client-request-id` | `thread_id` value; emitted by `responses.rs:91-92` (HTTP) and `client.rs:903-904` (WS upgrade) | Per CLI invocation (= `thread-id`) | YES | NO | NO | NO | NO |
| `x-codex-window-id` | `"{thread_id}:{window_generation}"` (`client.rs:382-386, 620-621`); `window_generation` is `AtomicU64` (`client.rs:168`) bumped only by `advance_window_generation` (`client.rs:377`), called only on compaction (`session/mod.rs:2584`) | Per CLI invocation, unless conversation compaction fires | YES | NO | NO | NO | NO |
| `x-codex-installation-id` (header) | `state.installation_id` from `~/.codex/installation_id` (`installation_id.rs:19-64`); emitted as **header** only on `/responses/compact` (`client.rs:489-490`) | Per machine (persisted to disk) | NO (stable across invocations on same machine) | n/a (not on `/responses`) | NO | NO | NO |
| `x-codex-installation-id` (body) | Same source; embedded in `client_metadata` JSON (`client.rs:760-763`) | Per machine | NO | NO | NO | NO | NO |
| `x-codex-turn-metadata` | JSON-encoded `TurnMetadataState` built per turn at `turn_context.rs:575-584`; embeds `session_id`, `thread_id`, `turn_id` (= `sub_id`), sandbox; emitted by `client.rs:1669-1671` | Per turn | YES | NO | YES | NO | NO |
| `x-codex-turn-state` | Server-issued sticky token captured at `responses_websocket.rs:525-532` (WS upgrade response); stored in `Arc<OnceLock<String>>` on `ModelClientSession.turn_state` (`client.rs:246`); replayed on subsequent same-turn requests by `client.rs:1663-1668` | Per turn (server-issued) | YES | n/a (HTTP fallback may not receive it; OnceLock from WS attempt is still held but may be empty if WS never responded) | YES (`OnceLock` recreated per `new_session` at `client.rs:362`) | NO (replayed unchanged within turn) | NO |
| `x-codex-inference-call-id` | Fresh `Uuid::new_v4()` per attempt (`rollout-trace/src/inference.rs:130, 343-345`); added only on HTTP path (`client.rs:1254`) | Per HTTP attempt (HTTP-only) | YES | YES (fresh attempt) | YES | YES (fresh per retry) | n/a (HTTP) |
| `x-openai-subagent` | `state.session_source` set at session start (`client.rs:341`); emitted by `client.rs:599` and `responses.rs:95-97` | Per CLI invocation (per sub-agent invocation) | YES if source differs | NO | NO | NO | NO |
| `x-codex-parent-thread-id` | `session_source` (`client.rs:618`); only for `SubAgentSource::ThreadSpawn` | Per CLI invocation | YES if applicable | NO | NO | NO | NO |
| `x-codex-beta-features` | `state.beta_features_header` set at session start (`client.rs:345`); emitted by `client.rs:1659-1662` | Per CLI invocation | Possibly (config-dependent) | NO | NO | NO | NO |
| `openai-beta` (`OpenAI-Beta`) | Static constant `responses_websockets=2026-02-06` (`client.rs:146`); WS-only (`client.rs:911-914`) | Build-time constant (WS only) | NO | n/a (not on HTTP) | NO | NO | NO |
| `accept` | Static `text/event-stream` (`responses.rs:138-139`); HTTP-only | Build-time constant (HTTP only) | NO | n/a | NO | NO | n/a |
| `authorization` (Bearer) | Auth manager token (`bearer_auth_provider.rs:33-36`); may rotate on 401 recovery (`client.rs:1283-1290`) | Per CLI invocation; may change on unauthorized refresh | YES (re-login) | NO | NO | Possibly (on 401 refresh) | NO |
| `chatgpt-account-id` (`ChatGPT-Account-ID`) | Auth manager account id (`bearer_auth_provider.rs:38-41`) | Per logged-in account | NO (same account) | NO | NO | NO | NO |
| `x-openai-fedramp` | Constant per-account flag (`bearer_auth_provider.rs:43-44`) | Per account | NO | NO | NO | NO | NO |
| `originator` | Process-static (`default_client.rs:101-119`); first read latches via `LazyLock<RwLock<Option<...>>>` (`default_client.rs:47`) | Per CLI invocation (latched) | NO (same `codex_cli_rs` value) | NO | NO | NO | NO |
| `user-agent` | Process-static; includes crate version + OS info (`default_client.rs:133-157`) | Per CLI invocation; build-stable | NO (same Codex binary) | NO | NO | NO | NO |
| `x-openai-internal-codex-residency` | Process-static when residency requirement set (`default_client.rs:238-246`) | Per CLI invocation | NO | NO | NO | NO | NO |
| `x-oai-attestation` | `attestation_provider.header_for_request` (`client.rs:659-670`); attestation provider may sign per-request | Per request (provider-dependent) | YES | YES | YES | YES (signed per attempt) | NO |
| `x-responsesapi-include-timing-metrics` | `state.include_timing_metrics` (`client.rs:175`); WS-only (`client.rs:915-920`) | Per CLI invocation | NO (config-dependent) | n/a | NO | NO | NO |
| `host` | URL host; always `chatgpt.com` for default openai provider | Per provider | NO | NO | NO | NO | NO |
| `sec-websocket-key` | Tungstenite-generated per WS upgrade attempt | Per WS attempt | YES | n/a (not on HTTP) | YES (new WS = new key) | YES (each reconnect) | n/a |

Key reads:

- **`session-id`, `thread-id`, `x-client-request-id` are the same value**, set once at session start (`session/session.rs:811`: `SessionId::from(thread_id)`), and never change during the session. They flip together on a new CLI invocation. (Sub-agents are an exception: `session_id` and `thread_id` can diverge there, see `session/session.rs:808-812`.)
- **`x-codex-turn-metadata`** is the only emitted header that changes per turn but stays constant across attempts/retries within a turn. It embeds the turn_id (`sub_id`) in its JSON payload.
- **`x-codex-inference-call-id`** is the only emitted header that changes per attempt (per retry), but it is HTTP-only.
- **`x-codex-window-id`** changes only when the session compacts; for the typical "early in conversation" capture window it equals `{thread_id}:0` and behaves as session-stable.

## Section C: Discrimination matrix

Column meanings:
- **Case 1**: turn N attempted over WS, WS fails, same turn N retried over HTTP after `force_http_fallback` (`client.rs:405`).
- **Case 2**: turn N completed over WS, then turn N+1 starts (over WS or HTTP).
- **Case 3**: two separate `codex` CLI invocations captured by the same mitmproxy run.

Comparison is "is the header value on the second request the same as on the first?"

| Header | Case 1 (WS-fail → HTTP-retry, same turn) | Case 2 (WS-done → next turn) | Case 3 (separate Codex session) |
|---|---|---|---|
| `session-id` | same value | same value | different value |
| `thread-id` | same value | same value | different value |
| `x-client-request-id` | same value (= `thread-id`) | same value (= `thread-id`) | different value |
| `x-codex-window-id` | same value (no compaction between attempts) | same value (changes only on compaction, not on prompt boundary) | different value |
| `x-codex-installation-id` (body) | same value | same value | **same value if both invocations on the same machine** |
| `x-codex-turn-metadata` | same value (turn_id stable across attempts in a turn) | **different value** (new turn_id) | different value |
| `x-codex-turn-state` | not present on the HTTP retry (HTTP fallback typically does not carry it; WS-issued token is per-turn anyway) | not present on first request of new turn (server re-issues) | not present on first request of new session |
| `x-codex-inference-call-id` | not present on WS attempt; fresh value on HTTP retry | not present on WS; HTTP path emits a fresh value per attempt | n/a unless both requests are HTTP, then different |
| `openai-beta` | present on WS, absent on HTTP | present on WS, absent on HTTP | same presence pattern per transport |
| `accept: text/event-stream` | absent on WS upgrade, present on HTTP | absent on WS, present on HTTP | same presence pattern per transport |
| `authorization` | same value | same value | same if same logged-in account; otherwise different |
| `chatgpt-account-id` | same value | same value | same if same account |
| `originator`, `user-agent` | same value | same value | same value if same Codex binary |
| `sec-websocket-key` | present on WS (initial), absent on HTTP retry | new value if turn N+1 reopens WS, otherwise n/a | n/a comparison cross-transport |

Reasoning grounded in Section B: every header in the top group (`session-id` family + `x-codex-window-id`) has a **per-CLI-invocation lifetime**, so it cannot distinguish events inside one session. The only header with a **per-turn** lifetime that survives transport flip is `x-codex-turn-metadata`. Its discriminating bit (`turn_id`) sits inside an opaque JSON value, not as a separate header.

## Section D: Verdict

**The three cases cannot be fully distinguished from request headers alone.** Specifically:

- **Case 1 vs. Case 2 collapse to a single header-name signature.** Both produce two requests with identical `session-id`, `thread-id`, `x-client-request-id`, `x-codex-window-id`, `originator`, `user-agent`, `authorization`, `chatgpt-account-id`. The only header value that differs between Case 1 and Case 2 is `x-codex-turn-metadata`, which is JSON-encoded, not a discrete header name change. If Transport Matters treats that header value as opaque, Case 1 and Case 2 are header-indistinguishable. If Transport Matters parses the header value as JSON, `x-codex-turn-metadata` resolves the ambiguity: parse it as JSON, extract `turn_id`, compare across requests. Same `turn_id` → Case 1; different `turn_id` → Case 2.

- **Case 3 is cleanly distinguishable.** A new CLI invocation produces a new `thread_id` (UUID v7 generated at startup, `session_id.rs:20-23`), which changes `session-id`, `thread-id`, `x-client-request-id`, and `x-codex-window-id` all together. Any one of those four headers differing across requests is a sufficient indicator. **Caveat**: if you only watch `x-codex-installation-id` you will be fooled: it is stable across invocations on the same machine (`installation_id.rs:19-64`, persisted to `~/.codex/installation_id`). And in any case it is body data, not a header on the turn endpoint.

### Minimal discrimination logic

If `x-codex-turn-metadata` parsing is allowed (it is a single header value, not body content):

```
Given two captured requests R1 and R2 on path /backend-api/codex/responses:

1. If R1.thread-id != R2.thread-id:
   → Case 3 (separate Codex CLI invocations).

2. Else (same thread-id):
   Parse R1.x-codex-turn-metadata and R2.x-codex-turn-metadata as JSON.
   Extract turn_id from each.
   - If both turn_ids equal: Case 1 (same turn, retry).
   - If turn_ids differ:    Case 2 (next turn).
```

Minimal header set required: `thread-id` (or equivalently `session-id` or `x-client-request-id`) + `x-codex-turn-metadata`.

### If `x-codex-turn-metadata` cannot be parsed

If the rule is strictly "header name presence/absence and unparsed value equality, no JSON parsing of any header value either", then Case 1 vs. Case 2 cannot be resolved. The two surviving paths:

1. **Body inspection.** The `ResponsesApiRequest` body contains `client_metadata` with the turn metadata too, and the WS frame envelope's `ResponseCreateWsRequest.client_metadata` carries the same `x-codex-turn-metadata` value (`client.rs:1364`). Same problem in a different field. Body parsing is mandatory if header values must stay opaque.

2. **Flow correlation in mitmproxy.** Treat the WS flow and the HTTP POST as a stitched pair when the HTTP POST arrives within a small time window after a same-`thread-id` WS flow closes with a stream error or 426. This is reliable because `force_http_fallback` is a one-way switch (`client.rs:412`); after it flips, the HTTP request follows immediately (`turn.rs:1118-1119` resets retries and re-enters the loop). The proxy can carry state: "I saw thread T close WS uncleanly at time t0; the next HTTP POST on thread T before t0 + N seconds is Case 1; later POSTs on thread T are Case 2." This requires client-side proxy state, not just per-request header inspection.

### Practical recommendation

Treating `x-codex-turn-metadata` as a parseable header value is the cleanest path and is consistent with how Codex itself uses it. It is a single HTTP header, sent as JSON-stringified `application/json` content inside the header value (`turn_metadata.rs:222-223`). Parsing one header value to extract one field is qualitatively different from buffering and parsing the SSE response body or the WS request frames. If transport-matters is willing to do that, the three-case discrimination is exact and stateless.

If that is off the table, fall back to flow correlation: on every closed WS flow with `thread-id = T`, remember `T` and the close timestamp; on the next HTTP POST with `thread-id = T` within, say, 30 seconds, label it Case 1; otherwise Case 2. The `force_http_fallback` is one-way per session (`client.rs:411-412`) so once you label a `thread-id` as "fallen back", every subsequent HTTP POST on that `thread-id` is also post-fallback (not necessarily the *same* turn, just same session): to discriminate Case 1 from Case 2 within the post-fallback HTTP stream you still need turn-level info, which only `x-codex-turn-metadata` exposes header-side.

## Sources consulted

- `codex-rs/codex-api/src/requests/headers.rs:5-14`: `build_session_headers` emitter.
- `codex-rs/codex-api/src/endpoint/responses.rs:70-150`: HTTP request header construction.
- `codex-rs/codex-api/src/endpoint/responses_websocket.rs:357-540`: WS connect, handshake, response header parsing.
- `codex-rs/core/src/client.rs:134-148`: header name constants.
- `codex-rs/core/src/client.rs:160-181`: `ModelClientState` (session-scoped identity fields).
- `codex-rs/core/src/client.rs:312-352`: `ModelClient::new` (session_id, thread_id, installation_id wiring).
- `codex-rs/core/src/client.rs:358-364`: `ModelClient::new_session` (fresh per-turn session).
- `codex-rs/core/src/client.rs:370-386`: window_generation, `current_window_id`.
- `codex-rs/core/src/client.rs:405-424`: `force_http_fallback`.
- `codex-rs/core/src/client.rs:487-503`: compact endpoint header insertion (installation-id header).
- `codex-rs/core/src/client.rs:594-624`: `build_subagent_headers`, `build_responses_identity_headers`.
- `codex-rs/core/src/client.rs:626-657`: `build_ws_client_metadata` (body, not header).
- `codex-rs/core/src/client.rs:740-766`: `build_responses_request` (installation-id placed in `client_metadata` body).
- `codex-rs/core/src/client.rs:890-922`: `build_websocket_headers` (WS upgrade headers).
- `codex-rs/core/src/client.rs:959-986`: `build_responses_options` (HTTP path extra headers).
- `codex-rs/core/src/client.rs:1220-1305`: HTTP `stream_responses_api` retry loop.
- `codex-rs/core/src/client.rs:1308-1448`: WS `stream_responses_websocket` retry loop.
- `codex-rs/core/src/client.rs:1547-1616`: `stream` (transport dispatch, fallback trigger).
- `codex-rs/core/src/client.rs:1651-1673`: `build_responses_headers` (turn_state, turn_metadata, beta features).
- `codex-rs/core/src/installation_id.rs:19-64`: disk-persisted installation id.
- `codex-rs/core/src/session/session.rs:808-812, 872-884`: session_id derived from thread_id; ModelClient instantiation.
- `codex-rs/core/src/session/turn.rs:140-156`: per-turn `ModelClientSession` creation.
- `codex-rs/core/src/session/turn.rs:1055-1153`: retry loop, fallback gate, retry reset.
- `codex-rs/core/src/turn_metadata.rs:181-264`: `TurnMetadataState` definition and header serialization.
- `codex-rs/core/src/session/turn_context.rs:575-587`: per-turn `TurnMetadataState` construction with `sub_id` (turn_id).
- `codex-rs/login/src/auth/default_client.rs:36-249`: originator, user-agent, default_headers.
- `codex-rs/model-provider/src/auth.rs:21-50`: agent-identity auth headers (Authorization + ChatGPT-Account-ID).
- `codex-rs/model-provider/src/bearer_auth_provider.rs:31-47`: bearer auth headers.
- `codex-rs/protocol/src/session_id.rs:19-66`: SessionId UUID v7, ThreadId→SessionId conversion.
- `codex-rs/protocol/src/thread_id.rs:17-29`: ThreadId UUID v7.
- `codex-rs/rollout-trace/src/inference.rs:28, 122-167, 343-345`: `x-codex-inference-call-id` definition, lifetime, HTTP-only attachment.
- `codex-rs/codex-api/tests/clients.rs:441-486`: HTTP-side header assertion (confirms `session-id`, `thread-id`, `x-client-request-id`, `x-openai-subagent`).
- `codex-rs/core/tests/suite/client_websockets.rs:120-156`: WS-upgrade header assertion (confirms `OpenAI-Beta`, `x-client-request-id` = thread_id, `session-id`, `thread-id`, `user-agent`, `client_metadata.x-codex-installation-id` in body).

## Open questions

1. **Sub-agent root sessions.** For sub-agents (review, compact, memory consolidation), `session_id` is inherited from the controlling agent (`session.rs:809`), but `thread_id` is fresh. So `session-id != thread-id` for sub-agents, and `x-client-request-id = thread_id` will not equal `session-id`. transport-matters may see this in capture if Codex spawns a sub-agent mid-session. The three-case matrix in Section C assumes root-CLI sessions; sub-agent flows are an additional axis worth a separate capture run.
2. **`x-codex-installation-id` in headers via shared device.** If multiple users log in to the same machine, the installation_id stays the same. Combined with two separate `codex` invocations on the same login, Case 3 still works (different `thread-id`). But the installation_id is not a *user* identifier and should not be relied on as one.
3. **`x-codex-turn-state` propagation across WS→HTTP.** Source shows the `OnceLock<String>` is per-`ModelClientSession`, and that session is per-turn. The HTTP fallback path inside the same turn reuses the same `ModelClientSession.turn_state` (`client.rs:974`). So if the WS upgrade did populate `x-codex-turn-state` before failing mid-stream, the HTTP retry **will** include it. If the WS attempt failed before the upgrade response (e.g., 426, connect timeout), `x-codex-turn-state` is never populated and the HTTP retry omits it. So this header's presence pattern can co-discriminate Case 1 sub-types, but only for the "WS got partway then died" variant.
