---
title: Transport Matters Unified Endpoint Redirection
type: design
tags: [transport-matters, capture, proxy, grok, codex, claude, trust]
summary: Move codex and grok onto claude's endpoint redirection shape and delete the explicit proxy and its trust machinery
status: active
project: transport-matters
confidence: high
created: 2026-08-29
updated: 2026-08-29
---

# Transport Matters Unified Endpoint Redirection

## Decision

Capture provider traffic for all three harnesses the way claude already does: tell the client where to send provider traffic through its native base URL surface, pointed at a loopback mitmdump listener running in reverse mode toward the real provider origin. Delete `build_explicit_proxy_invocation`, the ten `*_PROXY` child variables, and the entire client trust bundle machinery.

The explicit proxy shape is drift. It sets process tree wide environment on children that inherit it into every descendant, which is how `gh` inside a grok run fails TLS and misreports it as an invalid keyring token. Endpoint redirection scopes capture to the one client that is being captured, and because the client speaks plain HTTP to loopback, no descendant ever needs to trust the mitmproxy CA. The trust problem is deleted rather than solved.

Sequencing: one small shared addon matcher change first, then grok (actively broken), then codex independently, then the deletion pass.

## Pinned evidence

This design targets `main` at `cf66f60c89c115068ee63cafa4e5027bbf630772` with mitmproxy `12.2.3` (the pinned runtime dependency, read from `api/.venv`), Claude Code `2.1.251`, codex-cli `0.150.1`, and Grok `1.0.5 (5115b46bc909)`.

1. Claude launches mitmdump with `--mode reverse:https://api.anthropic.com` (`captured/claude.py:184`, `cli/launch_runtime.py:367`) and hands the child `ANTHROPIC_BASE_URL=http://127.0.0.1:<port>` (`captured/claude.py:208`), also written into the runtime home `settings.json` `env` block (`cli/claude_home.py:111`). No `*_PROXY` variable is set on the claude child.
2. Codex and grok launch mitmdump in `regular` mode through `build_explicit_proxy_invocation` (`cli/explicit_proxy.py:110`), and `build_managed_child_env` sets ten `*_PROXY` variables plus `CODEX_NETWORK_PROXY_ACTIVE` on the child (`launch/environment.py:372-387`).
3. `gh` on macOS verifies TLS through Security.framework and ignores `SSL_CERT_FILE`; the mitmproxy CA is in neither the System nor the login keychain (established upstream of this scout; not re-derived).
4. mitmproxy 12.2.3 reverse mode, verified in the installed source: the listener pins `context.server.address` to the upstream (`proxy/layers/modes.py:65-76`); for an origin form HTTP/1 request `flow.request.host` is parsed from the client's Host header, so it is loopback (`proxy/layers/http/__init__.py:229-241`); with `keep_host_header` at its default of false (Transport Matters never sets it, verified by grep) the Host header is rewritten to the upstream host before any addon hook fires (`proxy/layers/http/__init__.py:264-273`), and `url.hostport` omits the default port, so the header is exactly the bare provider host.
5. The anthropic adapter matches by path alone: `flow.request.path.startswith("/v1/messages")` (`adapters/anthropic.py:191-192`). The grok and codex matchers require an exact `flow.request.host` (`grok/transport.py:7-16`, `codex/transport.py:105-131`).
6. Grok 1.0.5 binary strings: `GROK_CLI_CHAT_PROXY_BASE_URL`, the `--cli-chat-proxy-base-url` flag, and `[endpoints] cli_chat_proxy_base_url` all override the chat proxy base URL, default `https://cli-chat-proxy.grok.com/v1`. The API key auth warning ("uses `Authorization: Bearer` instead of session auth") is attached only to `models_base_url` and `GROK_MODELS_BASE_URL` documentation. A fleet policy passage treats a non xAI `cli_chat_proxy_base_url` as an ordinary deployment configuration.
7. codex-cli 0.150.1 binary strings: `chatgpt_base_url` is a `config.toml` key (also per profile) with default `https://chatgpt.com/backend-api/`, and it appears inside the auth manager's `auth_route_config`. `openai_base_url` is a top-level config key read by `built_in_model_providers()`. `CODEX_NETWORK_PROXY_ACTIVE` appears in the binary, confirming the strip behavior is the vendor's. `OPENAI_BASE_URL` appears once, in a blob beside `GH_TOKEN`, `sk-` and `OPENAI_API_KEY`, which reads as a secret-scanning list rather than a config read: there is no base URL environment variable for codex.

   **Correction, settled by two live probes.** `chatgpt_base_url` is the wrong key. With it set, the override reaches the auth manager and auxiliary `/backend-api/*` traffic goes to loopback, but the Responses WebSocket still goes to `wss://chatgpt.com/backend-api/codex/responses`: it redirects exactly the traffic Transport Matters does not want and misses the only flow that matters. `openai_base_url` is the right key, as a top-level config value with `model_provider` left unset. The active provider stays `openai` and every other built-in field is preserved, source path `cfg.openai_base_url` -> `built_in_model_providers()` -> `create_openai_provider(base_url)`. A substituted provider is not an option: `model_providers.openai` is rejected outright (`reserved built-in provider IDs`), and a custom id inherits nothing and takes type defaults for every omitted field, which an earlier `model_providers.tmprobe` probe paid for by losing the `version` header.
8. An audit of every mitmproxy hook in `api/src` (delegated, verified against code) found a single admission gate at `addon_handlers.py:196` and no consumer of any flow that fails it. Details in "What narrowing loses".
9. The exact successful baseline bundles examined are under `~/.transport-matters-preview/baselines/bundles`: `codex/codex/gpt-5.5/6dac4e5c-4d01-4a7a-b3f4-b9c92d664215.json`, `codex/codex/gpt-5.6-luna/03a87c71-7e42-47fa-9e32-1414a00494cf.json`, `codex/codex/gpt-5.6-sol/3088f516-a8ea-41e6-92c2-7110921c8c14.json`, `codex/codex/gpt-5.6-terra/074c7230-a983-4887-adb3-736e231eefc4.json`, `grok/grok/grok-4.5/9127a6ad-85e7-4e07-8ec7-dc3b31cf985c.json`, and `grok/grok/grok-4.6/34f97a35-b82d-455e-92df-e4fcaad32e95.json`. Their 18 exchange ids resolve in the preview `wire_exchange` store. Each model has three completed exchanges.
10. Codex transport artifacts were retained in the three channel homes. Excluding the current forensic run, all 362 retained codex provider transports have the same tuple: `websocket`, `https`, `chatgpt.com`, `/backend-api/codex/responses`, `101`. The pinned 0.150.1 representative is `~/.transport-matters-dev/workspaces/matters-dev-runtime-access-verification/ba0bdf03/c747fb39-2809-4cc1-bca7-662beb27102c/20260827T201445Z-1636d7c6/transport.json`. The run root's `compatibility.json` records codex-cli 0.150.1, and `logs/mitmdump.log` records the upgrade and WebSocket frames.
11. The retained pinned Grok 1.0.5 representative is `~/.transport-matters-dev/workspaces/matters-dev-runtime-access-verification/ba0bdf03/5f301978-1e56-4025-8a72-3ad1b1879629/20260827T201444Z-61ef87b6/transport.json`; the run root's `compatibility.json` records 1.0.5. All 32 retained grok provider transports have the same tuple: `http`, `POST`, `https`, `cli-chat-proxy.grok.com`, `/v1/responses`, `200`, and the credential header names `authorization`, `x-authenticateresponse`, and `x-xai-token-auth`.
12. The preview event store retains the six exact grok baseline transcript source paths. Every path is rooted at its own `<workspace>/<run-id>/runtime-home/grok/sessions/.../updates.jsonl`. The launch path independently constructs `<run storage>/runtime-home` (`captured/context.py:286-300`), assigns that child home as `GROK_HOME` (`launch/environment.py:124-128`, `cli/explicit_proxy.py:133-140`), and keeps `leader.sock` local to the overlay (`cli/home_overlay.py:280-288`).
13. The successful bounded fallback rerun is `~/.transport-matters-dev/workspaces/dev-helioy-transport-matters/ecd9b0df/aaeae10b-2bc7-4c37-9712-57c3b5d363eb`, launched on dev ports 8807/8808 with codex-cli 0.150.1, model `gpt-5.5`, and `--force-http-fallback`. `logs/mitmdump.log` records two rejected WebSocket handshakes at `GET https://chatgpt.com/backend-api/codex/responses`, each with status `426`, no `101`, then HTTP/2 `POST https://chatgpt.com/backend-api/codex/responses` requests with status `200` and client `CANCEL` resets. The requested turn is flow `67818b07-94b6-4c6d-88e6-127c7b6c1bfd`; the parser logged `codex/gpt-5.5 system=5 tools=15 msgs=2`, then recognized a complete response in the error hook and finalized provisional exchange `c9af35d5-857f-42ae-b860-fa2f049736bb`. Its directory `20260829T022339Z-c9af35d5/` retains `request.raw`, parsed request and response IR, `response.raw`, 14 HTTP transport messages ending in `response.completed`, and a completed turn whose output is `HTTP_FALLBACK_OK`. The dev `wire_exchange` row survives with `response_complete=true` and a response id. Codex also made a `gpt-5.6-luna` HTTP request during the one user turn; exchange `95a277ff-06b6-40df-92f5-ded86b894eba` survived by the same lifecycle. Its purpose remains unsettled. Ctrl+C shut down the managed run, and post-run checks found no listener on 8807/8808 and no process matching this launch.
14. The observed same-model comparator artifact is `~/.transport-matters-dev/workspaces/dev-helioy-transport-matters/ecd9b0df/aaeae10b-2bc7-4c37-9712-57c3b5d363eb/http-vs-ws-gpt-5.5-comparison.json`. It runs TM's `compare_request_schema` and `assess_support_state` with the pinned codex-cli 0.150.1 WebSocket bundle `~/.transport-matters-preview/baselines/bundles/codex/codex/gpt-5.5/6dac4e5c-4d01-4a7a-b3f4-b9c92d664215.json` as reference and the live HTTP exchange's `request.raw` as candidate. The raw structural result remains one missing property, `/type`, zero additional properties, and comparison outcome `breaking`. The resulting support state is `degraded`, but the determination below establishes that this support verdict compares different transport shapes and does not represent Responses payload loss. The older codex-cli 0.144.0 `gpt-5.6-sol` fixture comparison remains historical evidence only because its 4 missing and 8 additional properties are confounded by version and context.
15. The capture lifecycle regression is pinned by `exchange_recorder/test_codex_http_artifacts.py::test_error_after_terminal_codex_http_response_finalizes_exchange` and `::test_error_during_codex_http_response_retains_incomplete_exchange`. The first failed before the fix because the exchange directory was deleted, then passed after the error hook began recognizing protocol-terminal response bytes. The paired test proves a body without a terminal event remains provisional with no response artifacts. `test_addon_http_error_completion.py` pins the certified terminal events and exact `Content-Length` rule. Both standalone and shared proxy error hooks now use the same handler. The focused 68-test set and the full `just check` gate pass.
16. The raw root-shape determination uses the same pinned `gpt-5.5` bundle and HTTP exchange. All three WebSocket probe bodies have the same 14 root properties and `"type": "response.create"`. The HTTP body has the same other 13 properties, no `/type`, and no property absent from WebSocket. Removing only `/type` from a WebSocket body produces the same parsed semantic IR; the only IR difference is the preserved `provider_extras.type`. The Codex serializer emits that value only when the inbound body carried it and deliberately omits it for HTTP, whose upstream rejects a top-level `type`. This establishes `/type` as a WebSocket envelope discriminator rather than a Responses payload property.
17. `ir_coverage` has no `RESPONSES` profile entry and no declaration for `/type`: `profile_mappings(RESPONSES)` is empty, `mapped_top_level_keys(RESPONSES)` is `None`, and resolution returns `modeled` from `CoverageSource.DEFAULT`. There is no `ir_target`, no `ui_target`, and no inspector read of root `provider_extras.type`. The real code consumers are transport boundary logic: `parse_codex_request` validates absent or `response.create`, and `serialize_codex_request` preserves the discriminator for WebSocket while omitting it for HTTP.
18. The current Claude `sonnet` baseline at `~/.transport-matters-preview/baselines/bundles/claude/anthropic/sonnet/8c97dd33-ede5-4abd-89b4-81cc25d2f10c.json` supplies the reverse-listener control. All three exchanges are HTTP `POST /v1/messages?beta=true` with status `200`; each raw body is a bare Anthropic Messages object with no root `/type`. Anthropic declares its semantic nested discriminators, including `/system/type -> SystemPart.type` and `/messages/content/type -> TextBlock.type`. A root Anthropic `/type` resolves `unmodeled` from its mapped top-level vocabulary.

## How claude solves origin matching, and how it generalises

The crux is that under a base URL override the client connects to loopback, so the host the addon sees changes. Claude's answer has two halves.

First, the listener itself carries the origin. Reverse mode serves exactly one upstream, and every captured run owns a dedicated listener (per run mitmdump, or a per run listener registered with the shared proxy, whose `mode_spec` already renders `reverse:{upstream}@127.0.0.1:{port}` per binding, `shared_proxy/models.py:47-55`). One listener, one harness, one provider origin.

Second, the anthropic matcher never reads the host. Path prefix only. That is why nothing had to be solved for claude explicitly.

The mechanism generalises, but the grok and codex matchers must change, because under reverse mode `flow.request.host` is `127.0.0.1` and their exact host checks fail. Two facts make the change small and safe:

- mitmproxy rewrites the Host header to the upstream host before the request hook runs (pinned evidence 4). So `flow.request.host_header` carries the true origin in reverse mode, and the original origin in regular mode. Nothing in `api/src` reads `host_header` today (verified by grep), so claiming it is free.
- The admission gate `addon_handlers.py:194-196` already ORs the three matchers, and the shared proxy demuxes flows by listen port before the gate, so a listener only ever presents one harness's traffic.

The change: `is_grok_responses_flow` and `is_codex_websocket_flow` accept a flow when the provider host matches either `request.host` or the parsed `request.host_header`. Method and path requirements stay exact. This is one matcher edit per harness plus reverse shaped test fixtures (existing tests build flows with `request.host` set, e.g. `test_addon_http_grok.py:22`, and keep passing). No per harness addon fork, no new matching concept.

Path preservation falls out of the base URL shapes. Grok's default base includes `/v1`, so the override is `http://127.0.0.1:<port>/v1` and the addon still sees `/v1/responses`. Codex appends `responses` to `openai_base_url`, so the override is `http://127.0.0.1:<port>/backend-api/codex` and the addon still sees `/backend-api/codex/responses`. The reverse upstream is the bare origin in both cases. `openai_base_url` also redirects the model catalog request, so the reverse listener serves `/backend-api/codex/models` as well as the Responses path. That pair defines Codex capture scope. Other ChatGPT service calls retain their own routes and go direct. A live codex-cli 0.150.1 probe observed `https://chatgpt.com/backend-api/ps/mcp` taking that direct path. This is deliberate: the admission gate drops non-provider flows before state exists, and every capture consumer is fed only by provider-gated persist sinks.

The plumbing already exists: `CapturedRunRequest.upstream` threads to the claude builder today, and `default_upstream_for_harness` (`captured/models.py:58-60`) returns the empty string for codex and grok, which becomes their real origin. `_infer_mode_kind` (`shared_proxy/models.py:188-194`) special cases codex to `regular`; with all three reverse it collapses entirely, and `ProxyModeKind` along with it.

The capture follow-up resolves which codex transport is active. Each baseline model has three completed wire exchanges, and every exchange carries `request_metadata.provider_metadata.x-codex-ws-stream-request-start-ms`: `gpt-5.5` 3 of 3, `gpt-5.6-luna` 3 of 3, `gpt-5.6-sol` 3 of 3, and `gpt-5.6-terra` 3 of 3. None has `request_wire_bytes`, the field populated by ordinary HTTP requests. The retained transport bytes remove any ambiguity in that marker: all 362 pre-existing codex transports are WebSocket upgrades to `https://chatgpt.com/backend-api/codex/responses`, with `Connection: Upgrade`, `Upgrade: websocket`, status `101`, and a first client frame whose event type is `response.create`. HTTP fallback appeared zero times in the retained provider transports.

The captured WebSocket URL has the same origin and base path as the pinned defaults, with `codex/responses` appended. No retained capture or config artifact records a different base. That was evidence of consistency, not of derivation, because the observed effective value never differed from the default, and recorded bytes could not establish that an `http://` base produces a `ws://` URL.

**Both remaining unknowns are now settled by live runs.** Bounded dev-channel codex-cli 0.150.1 turns with `-c openai_base_url="http://127.0.0.1:<port>/backend-api/codex"` against `--mode reverse:https://chatgpt.com` produced, in every run, an inbound loopback `GET /backend-api/codex/responses` with `Connection: Upgrade` and `Upgrade: websocket`, an upstream `101`, one client `response.create` frame, and a completed response persisted with `protocol: websocket`. So the `http` base does derive a `ws` URL, and mitmproxy 12.2.3 does bridge a plaintext loopback WebSocket upgrade to the TLS upstream. The upgrade also retained `version: 0.150.1`, proving the built-in provider's `http_headers` were inherited. The model catalog request arrived on the same listener rather than escaping to `chatgpt.com`. A like-for-like `gpt-5.5` first-turn request, captured in the pinned baseline's own cell, compares `exact` / `blessed` against reference bundle `6dac4e5c-4d01-4a7a-b3f4-b9c92d664215` with zero missing and zero additional properties.

The persisted `gpt-5.6-sol` verdict records candidate effort `xhigh`. The release plan names effort `low`, and `read_reusable_baseline_for_version` deliberately accepts evidence from any recorded effort for a planned low structural reference because effort changes content without changing request structure. Calling the persisted candidate low effort is inaccurate; calling its structural comparison matched is accurate. A separate default-cell run showed one `/input` discriminator difference on its prewarm request. Without a default-cell reference captured under the same coordinates before and after this migration, that observation cannot be attributed to endpoint redirection. It remains unresolved evidence rather than a migration finding.

### HTTP fallback contingency: usable as a transport-distinct capture floor

The two bounded dev runs establish the defect and its repair for codex-cli 0.150.1. The fallback addon returned `426` to each WebSocket upgrade, no `101` occurred, Codex immediately sent ordinary HTTP/2 `POST` requests to the same `/backend-api/codex/responses` path, the provider returned `200`, and the requested `gpt-5.5` turn completed as `HTTP_FALLBACK_OK`. In the first run the subsequent client `CANCEL` routed through an unconditional error cleanup and deleted the provisional exchange. In the rerun the same reset routed through completion-aware cleanup and the exchange survived on disk and in `wire_exchange`.

The separating signal is in the captured response body at the error hook. Responses streams are complete only after TM's existing protocol parser recognizes `response.completed` or `response.failed`; Anthropic's corresponding terminal event is `message_stop`. A length-delimited response is also complete when the retained raw body exactly satisfies its single valid `Content-Length`. A stream reset before those signals remains a provisional outbound request, represented by the existing `response_complete=false` state, and is not finalized with partial response data. This preserves failure evidence without allowing truncated bodies into reference schemas or drift comparisons.

The direct current-version comparison is now observed. Against the same-model WebSocket reference, the HTTP request loses only the WebSocket envelope's top-level `/type` property and adds nothing. TM grades the raw structural comparison `breaking` and the support verdict `degraded` because the Responses profile has no coverage declaration and defaults every position to modeled.

The raw difference is real. `/type` equals `response.create` in every pinned WebSocket probe, is the sole root property absent from the HTTP body, and controls WebSocket round-trip framing. The HTTP transport sends the Responses payload bare and the serializer deliberately omits `/type`. No semantic IR field or inspector reader loses content on the HTTP path. The current `degraded` support verdict is therefore an artifact of comparing unlike transports on an axis intended to measure version drift. It remains an honest raw-schema finding and would be a real regression if a WebSocket candidate lost the discriminator.

Decision: the fallback is usable in practice as a transport-distinct capture floor if the primary WebSocket route cannot bridge. It must not be treated as a WebSocket-fidelity substitute or used to mint a WebSocket reference. The primary WebSocket risk remains open, and its reverse-listener test above is unchanged.

### Comparator follow-up: make transport a reference coordinate

The current reference model has no transport coordinate. `BaselineCell`, `RequestCaptureProvenance`, `ProbeEvidence`, `ReleaseRequestSchemaReference`, and `SupportVerdictArtifact` identify harness, provider, model, effort, and version while omitting HTTP versus WebSocket. A bundle stores raw request bytes, and the exchange stores `TransportArtifacts.protocol`, but `_build_probe_evidence` discards that protocol before the bundle is minted. `request_shape` is fixed to `first-turn` and should not be overloaded with a second axis.

The recommended shape is a transport-aware reference identity. Add `http` or `websocket` to the baseline cell and release request schema reference, carry the observed protocol from the captured exchange, and compare a candidate only with a reference for the same transport. WebSocket `/type` then remains modeled by its transport contract and a WebSocket loss still fails honestly. HTTP compares against a bare HTTP reference and receives no charge for absent WebSocket framing. A launch that tries WebSocket and falls back must bind its verdict to the protocol of the exchange that actually survived, which is known after capture.

The cost is material and bounded. The baseline artifact schema and current-pointer compatibility need a migration; release references, reference keys, verdict keys and paths, projection cohort coordinates, and operator support surfaces need the new coordinate. Existing bundles require a protocol backfill from their exact retained exchange artifact or a recapture. Certifying the HTTP contingency requires one controlled three-probe bundle per supported Codex model and version, adding provider work and signed reference data. An installed version can then have separate support results per transport, so any aggregate display needs an explicit rule.

Two cheaper shapes lose important evidence. Marking `/type` unmodeled in `ir_coverage` would bless this HTTP comparison, but it would also hide a WebSocket framing loss that the serializer genuinely consumes. Stripping known envelope keys before comparison avoids duplicate references, but then the raw-schema comparator stops checking the full request body and a separate, versioned transport-envelope contract must detect missing or changed WebSocket framing. That split may be worthwhile if more transports acquire only mechanical wrappers; for the current system, transport-aware references preserve the strongest evidence and keep the version comparator's inputs homogeneous.

## What narrowing loses: nothing load bearing

Shape B sees settings, storage, trace, and telemetry traffic. Shape A sees only provider calls. The audit verdict: no code consumes non provider traffic.

- The single admission gate (`addon_handlers.py:196`) returns before any state is created for a non matching flow. `get_request_flow_state` is then `None` forever, and every response, error, and streaming path exits on that. Not stored, not counted, not classified, not indexed.
- `provider-outcome-classifier-r1` (`harnesses/connections.py:80`, consumed at `harnesses/provider_access_recorder.py:244-248`) is fed exclusively from call sites behind the gate, and its classifiers parse only Anthropic SSE and Responses protocol shapes. Access elevation cannot involve auxiliary traffic.
- The grok activity discrimination among several `/v1/responses` requests happens inside provider traffic: `grok/request_purpose.py` reads the request's own `x-grok-turn-idx` header and body shape. Same host, same path, discriminated by content. Provider only capture preserves it exactly.
- Everything feeding `support_state`, baseline capture, drift capture, live status, and the wire store hangs off exchange sinks fired only from the provider gated persist functions. No sink has another producer.
- No host allowlist, telemetry, statsig, or auxiliary request concept exists anywhere in `api/src` (grep swept).
- One consumer runs before the gate: `refresh_expired_claude_credential` (`addon_handlers.py:516`). It is active only when `binding.harness == "claude"`, and claude already sees provider traffic only. Unaffected.
- One behavior is removed and it is an improvement: the shared proxy today injects a 502 into auxiliary requests it cannot map to a run (`shared_proxy/addon.py:308`). Under redirection those requests never transit the proxy, so the harness stops receiving synthetic failures on its telemetry.

The auxiliary traffic was never evidence. It was only ever exposure.

## Whether the override moves the auth path

The retained explicit proxy evidence settles what the normal Grok chat proxy request carries. Real requests were `POST https://cli-chat-proxy.grok.com/v1/responses`, returned `200`, and carried all three of these credential headers:

- `Authorization: Bearer [redacted]`
- `x-xai-token-auth: [redacted opaque token]`
- `x-authenticateresponse: [redacted opaque marker]`

All 32 retained grok provider transports have that same header-name set. The exact `grok-4.5` and `grok-4.6` baseline bundles preserve request bodies and wire rows, but their original header artifacts were cleaned. The retained control is the same pinned Grok 1.0.5 build and explicit proxy path.

This evidence corrects the earlier test criterion. A Bearer authorization header already accompanies the session-shaped `x-xai-token-auth` and `x-authenticateresponse` headers on the default chat proxy route. Bearer presence alone cannot identify the `models_base_url` API key path.

Still unproven: none of the retained requests used `cli_chat_proxy_base_url`, and no capture retains the originating config key. Recorded bytes therefore do not tie auth mode to that key. Grok's warning about switching auth remains documented only against `models_base_url` (pinned evidence 6), so neutrality of `cli_chat_proxy_base_url` remains a source-backed inference.

The bounded launch test before deletion is now:

1. Start a reverse listener at `reverse:https://cli-chat-proxy.grok.com` with the production addon.
2. Launch grok once with `GROK_CLI_CHAT_PROXY_BASE_URL=http://127.0.0.1:<port>/v1`, native credentials, one prompt, no `XAI_API_KEY` in the environment.
3. Compare the captured `/v1/responses` credential header names and schemes against an explicit proxy control from the same account, and require a terminal `response.completed`.

The redirected request must retain `Authorization: Bearer [redacted]`, `x-xai-token-auth`, and `x-authenticateresponse`, then complete successfully. A missing session-shaped header, a changed credential scheme, or a 401 refutes neutrality and stops the migration at the matcher unit, which is harmless standalone.

Codex answers it differently now that `openai_base_url` is the carrier. `chatgpt_base_url` stays at its default, so the auth manager's token route is untouched and keeps going to `chatgpt.com` directly. What the redirect moves is the provider traffic and the model catalog, both to the same `chatgpt.com` origin through the listener, so nothing new is exposed. Live runs confirm the credential headers on the upgrade are unchanged, `authorization` and `chatgpt-account-id` included.

## Grok's leader process model

The escape risk from a pre-existing native leader is resolved. Each of the six exact grok baseline runs wrote its transcript beneath its own `<run-id>/runtime-home/grok/sessions/...` path. The launch path creates that run-owned home, passes it to the child as `GROK_HOME`, makes `leader.sock` local rather than linking the native home's socket, and removes the runtime home when the run exits (pinned evidence 12). With Grok's default socket at `~/.grok/leader.sock`, the managed child resolves a different socket path for every run. A leader already running under the native `~/.grok/leader.sock` cannot be reused by a managed run.

The captures do not retain a leader PID, argv, environment, or socket connection. Reuse of an already running leader at the same run-scoped socket is therefore inferred from Grok's documented socket model. Under the normal launch sequence that leader was created inside the same managed environment and inherited the endpoint override. A wrong-environment leader would require another process to start first against the exact newly allocated transient `GROK_HOME`.

The smallest process observation, if direct proof is required, does not need provider traffic: hold one managed run open, record the Grok process tree and Unix socket endpoints, and require the client to connect to `<run storage>/runtime-home/grok/leader.sock` with no connection to the native `~/.grok/leader.sock`. Start a second client in that same run and require reuse of the same run-scoped leader PID.

## Capture audit against the plan

No captured provider behavior contradicts endpoint redirection. Codex is more dependent on the WebSocket leg than the first note implied because all retained provider transports use it. Grok's provider path and HTTP transport match the proposed override path. The explicit proxy logs also contain the auxiliary settings, telemetry, storage, update, and MCP traffic that the provider-only redirect intentionally removes, with no evidence that Transport Matters persisted those flows.

The live fallback rerun closes the separate capture-persistence risk. Endpoint redirection remains unaffected. A current codex-cli 0.150.1 HTTP fallback exchange now survives the observed terminal HTTP/2 `CANCEL` lifecycle, is parsed, and reaches the wire store. Its sole schema difference is the expected WebSocket envelope discriminator, so the contingency is usable as an HTTP capture floor while remaining transport-distinct from the still-primary WebSocket path. The current `degraded` support result is a cross-transport comparison artifact. The repository's older real fallback fixture continues to correct the claim that the fallback had never been exercised anywhere; it was absent from the retained channel-home transport census.

One captured fact contradicts an earlier proof criterion in this note: `Authorization: Bearer` is already present on Grok's ordinary chat proxy route alongside the session-shaped headers. The migration decision survives, but its auth test must compare the complete credential header set and successful response rather than treating Bearer presence as evidence of an auth-path switch.

## Deletion path

Callers of `build_explicit_proxy_invocation`, verified by grep: `captured/grok.py:59` and `cli/codex_cmd.py:124` (`build_codex_invocation`, reached from `run_codex` and from `captured/codex.py:62` for canvas). Both move onto a shared endpoint redirect builder generalised from `_build_claude_captured_invocation` (`captured/claude.py:120`), parameterised by harness, upstream origin, and the extra env or config that carries the base URL. One builder, three harnesses, per DRY.

Deleted once both harnesses move:

- `cli/explicit_proxy.py`, whole file.
- The `proxy_url` branch of `build_managed_child_env` (`launch/environment.py:372-387`): the ten `*_PROXY` assignments and the `CODEX_NETWORK_PROXY_ACTIVE` marker, plus the `proxy_url` and `codex_ca_certificate` parameters.
- `cli/trust.py` and `cli/codex_trust.py`, whole files: `resolve_codex_ca_certificate`, `resolve_tls_ca_certificate`, bundle construction, the error taxonomy, the process lifetime cache, and `resolve_proxy_only_codex_ca_hint`. With no client side TLS, the mitmproxy CA is unused by Transport Matters entirely.
- `captured/grok.py:49-58`: the `SSL_CERT_FILE` resolution and `child_extra_env`, and the `grok-trust` bundle directory under run storage.
- The CA half of `resolve_codex_addons_and_ca` (`cli/codex_cmd.py:205-231`) and its threading through `cli/__init__.py:93,340`; `CODEX_CA_BUNDLE_DIR_PREFIX` in `temporary_paths.py`; `raise_trust_cli_error` (`cli/launch_runtime.py:257`).
- Operator prose that describes the explicit shape: `_build_proxy_only_codex_hint` (`cli/codex_cmd.py:73-88`), the codex banner's `explicit HTTPS proxy` target and the grok banner's `SSL_CERT_FILE` hint (`cli/banner.py:48,73`), the codex and grok "Proxy environment" help sections (`cli/help.py:140-200`), and the `CODEX_CA_CERTIFICATE` and explicit mode hints in `codex/diagnostics.py:52,85`.
- The codex special case in `_infer_mode_kind` (`shared_proxy/models.py:188-194`).

Kept, deliberately:

- `_MANAGED_CHILD_PROXY_ENV_KEYS`, `_MANAGED_CHILD_PROXY_INTERNAL_ENV_KEYS`, and `_MANAGED_CHILD_TRUST_ENV_KEYS` as removal sets (`launch/environment.py:41-99`), and `managed_child_shell_env_excludes`. Stripping an operator's ambient proxy and trust variables is bypass prevention and deterministic capture, correct on its own merits and independent of how Transport Matters routes its own traffic. `CODEX_NETWORK_PROXY_ACTIVE` stays in the strip set as an inherited variable to remove, even though nothing sets it any more.
- The `NO_PROXY=127.0.0.1,localhost` assignment (`launch/environment.py:386-387`), defensive: it guarantees the loopback route survives any proxy variable that reaches the child by another path.
- `--force-http-fallback` and its addon: `force_http_fallback_addon.py` matches by path suffix (`:31`) and works unchanged under reverse mode.
- `desktop/src/app/bundledResources.ts` `SSL_CERT_FILE`: that is the certifi bundle for the bundled Python backend's own SSL context, unrelated to harness trust.

## Implementation units

### Unit 1: origin aware matchers

Extend `is_grok_responses_flow` and `is_codex_websocket_flow` to accept the provider host from `request.host_header` as well as `request.host`. Add reverse shaped fixtures (loopback host, rewritten header) beside the existing regular shaped tests. Behavior preserving for every live path; lands first and stands alone.

### Unit 2: grok to endpoint redirection

Give grok a real origin in `default_upstream_for_harness`, move `build_grok_captured_invocation` onto the shared redirect builder with `GROK_CLI_CHAT_PROXY_BASE_URL=http://127.0.0.1:<port>/v1` as the child's extra env, reverse mode argv, no `SSL_CERT_FILE`, no proxy variables. Run the bounded auth test above. Checkpoints: a genuine captured `/v1/responses` exchange with unchanged schema against the shipped reference; credential headers identical to an explicit proxy capture; `gh` succeeding in a shell inside the run, which is the reported failure; activity and access classification unchanged.

The native leader escape risk is already resolved by the run-scoped `GROK_HOME` and local `leader.sock` evidence above. Retain the process observation as a diagnostic checkpoint if the endpoint launch test shows any traffic bypass.

### Unit 3: codex to endpoint redirection

Independent of unit 2; requires only unit 1. Carry `openai_base_url = "http://127.0.0.1:<port>/backend-api/codex"` to the child and drop `CODEX_CA_CERTIFICATE` and the proxy variables.

The carrier is argv, `-c openai_base_url="<url>"`, not a config file write. A `config.toml` write is unavailable on the plain CLI path: `_prepare_codex_launch_parts` plans the runtime home with `use_runtime_overlay=False`, so an ordinary `transport-matters codex` in `NATIVE` mode has `child_home is None` and the codex child inherits the operator's real `~/.codex`. Writing the redirect there would mutate operator config and outlive the run. Argv works identically on every launch path and writes nothing. Codex applies the last repeated `-c` value, so the capture-critical endpoint override follows user passthrough and is inserted immediately before a literal `--` when one is present. The shell exclusion, model, effort, permission and session arguments keep their existing positions. It is also the honest thing to render in `--print-command` and the proxy-only banner hint.

The 0.150.1 `--force-http-fallback` checkpoint has now passed after the capture lifecycle repair. One bounded current-version user turn produced a persisted HTTP POST exchange, parsed request and response, a completed `wire_exchange` row, and a direct same-model comparator verdict. The observed transport cost is the absence of the WebSocket-only `/type: response.create` envelope discriminator, with zero Responses payload losses and zero additions. Keep the fallback as a transport-distinct contingency. The unit's first checkpoint remains the primary WebSocket reverse-listener test above; this rerun does not answer either WebSocket unknown.

### Unit 4: deletion

Everything in the deletion path, in one change, with the kept list untouched. Checkpoints: grep gates prove no `*_PROXY` assignment survives outside the removal sets and `cli/trust.py` and `cli/explicit_proxy.py` are gone; the full suite is green; one live canvas run per harness. `cli/explicit_proxy.py` becomes `cli/redirected_client.py` with `redirect` required, since it is the shared builder codex and grok both use and only its explicit branch is dead.

## Required proof

The end state proves one property three times: launch harness X, capture a genuine provider exchange, and observe that no process in the run's tree beyond the harness client had its network environment or trust surface altered. Concretely per harness: the captured exchange lands with schema, activity, and access outcomes matching an explicit proxy capture of the same account; `env | grep -i proxy` inside a run shell shows only `NO_PROXY`; and `gh api user` succeeds inside a grok run.

## Explicit exclusions

This endpoint-redirection design does not implement the transport-aware reference follow-up above. That work changes baseline and support evidence contracts and should remain independently reviewable. The endpoint change does not add certificate installation of any kind, keychain writes included. It does not migrate the shared proxy's ownership model; the per binding reverse mode it already supports is reused as is. The Tier 2 shared proxy load harness now gives both its Claude and Codex bindings an upstream and drives both as reverse listeners. Restoring regular mode would preserve an unsupported launch shape solely for a synthetic harness; migrating the harness keeps its concurrency, capture isolation and process saturation purpose aligned with every real caller.

Visual verification on this machine fails the same 14 specs at `bc651e00` and on the endpoint-redirection worktree because the local font or renderer differs from the checked-in image set. One of those already failing specs, `exchange-detail-transport-diagnostics.png`, also has a legitimate branch-specific copy change from the removed client CA guidance to the upstream TLS leg guidance. Its snapshot is stale. It was not regenerated alone because doing so with this renderer would make one image inconsistent with its 13 siblings; the visual suite needs a coherent rebaseline in its reference renderer.
