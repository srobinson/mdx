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
7. codex-cli 0.150.1 binary strings: `chatgpt_base_url` is a `config.toml` key (also per profile) with default `https://chatgpt.com/backend-api/`, and it appears inside the auth manager's `auth_route_config`, so the ChatGPT token route follows the same base. `openai_base_url` and `model_provider`/`wire_api` exist for the API key path. `CODEX_NETWORK_PROXY_ACTIVE` appears in the binary, confirming the strip behavior is the vendor's.
8. An audit of every mitmproxy hook in `api/src` (delegated, verified against code) found a single admission gate at `addon_handlers.py:196` and no consumer of any flow that fails it. Details in "What narrowing loses".
9. The exact successful baseline bundles examined are under `~/.transport-matters-preview/baselines/bundles`: `codex/codex/gpt-5.5/6dac4e5c-4d01-4a7a-b3f4-b9c92d664215.json`, `codex/codex/gpt-5.6-luna/03a87c71-7e42-47fa-9e32-1414a00494cf.json`, `codex/codex/gpt-5.6-sol/3088f516-a8ea-41e6-92c2-7110921c8c14.json`, `codex/codex/gpt-5.6-terra/074c7230-a983-4887-adb3-736e231eefc4.json`, `grok/grok/grok-4.5/9127a6ad-85e7-4e07-8ec7-dc3b31cf985c.json`, and `grok/grok/grok-4.6/34f97a35-b82d-455e-92df-e4fcaad32e95.json`. Their 18 exchange ids resolve in the preview `wire_exchange` store. Each model has three completed exchanges.
10. Codex transport artifacts were retained in the three channel homes. Excluding the current forensic run, all 362 retained codex provider transports have the same tuple: `websocket`, `https`, `chatgpt.com`, `/backend-api/codex/responses`, `101`. The pinned 0.150.1 representative is `~/.transport-matters-dev/workspaces/matters-dev-runtime-access-verification/ba0bdf03/c747fb39-2809-4cc1-bca7-662beb27102c/20260827T201445Z-1636d7c6/transport.json`. The run root's `compatibility.json` records codex-cli 0.150.1, and `logs/mitmdump.log` records the upgrade and WebSocket frames.
11. The retained pinned Grok 1.0.5 representative is `~/.transport-matters-dev/workspaces/matters-dev-runtime-access-verification/ba0bdf03/5f301978-1e56-4025-8a72-3ad1b1879629/20260827T201444Z-61ef87b6/transport.json`; the run root's `compatibility.json` records 1.0.5. All 32 retained grok provider transports have the same tuple: `http`, `POST`, `https`, `cli-chat-proxy.grok.com`, `/v1/responses`, `200`, and the credential header names `authorization`, `x-authenticateresponse`, and `x-xai-token-auth`.
12. The preview event store retains the six exact grok baseline transcript source paths. Every path is rooted at its own `<workspace>/<run-id>/runtime-home/grok/sessions/.../updates.jsonl`. The launch path independently constructs `<run storage>/runtime-home` (`captured/context.py:286-300`), assigns that child home as `GROK_HOME` (`launch/environment.py:124-128`, `cli/explicit_proxy.py:133-140`), and keeps `leader.sock` local to the overlay (`cli/home_overlay.py:280-288`).
13. The bounded current-version fallback run is `~/.transport-matters-dev/workspaces/dev-helioy-transport-matters/ecd9b0df/d0dae092-3067-45f9-8617-fa06edab5e57`, launched on dev ports 8807/8808 with codex-cli 0.150.1, model `gpt-5.5`, and `--force-http-fallback`. `logs/mitmdump.log` records two rejected WebSocket handshakes at `GET https://chatgpt.com/backend-api/codex/responses`, each with status `426`, followed by two `POST https://chatgpt.com/backend-api/codex/responses` HTTP/2 requests with status `200`. The `gpt-5.5` request is flow `1294aa94-2982-41e6-a62c-cd7e6711b70f`; the second request is flow `6207ee98-dd21-49f2-9d9b-7414f1047a37`, model `gpt-5.6-luna`. Both response streams ended with client `CANCEL` resets. The two persisted exchange directories and both `index.jsonl` rows are handshake failures only (`codex/transport-handshake`); no HTTP POST exchange directory or `wire_exchange` row survived in stable, preview, or dev. The transcript `transcripts/fadd1b0b-7726-5676-911f-bade05f28b93.jsonl` records one user message, final `HTTP_FALLBACK_OK`, and `task_complete`. The log ends with clean application shutdown, and post-run checks found no listener on 8807/8808 and no process matching the launch, mitmdump listener, or prompt.
14. Comparator evidence has two different strengths and must remain separate. Captured evidence: the repository already contains a real codex-cli 0.144.0 HTTP fallback fixture at `api/tests/fixtures/codex_http_fallback/`, model `gpt-5.6-sol`; `turn-0/transport.json` records HTTP `POST https://chatgpt.com/backend-api/codex/responses`, status `200`. Re-serializing its preserved turn-0 IR to wire bytes and running `compare_request_schema` plus `assess_support_state` against the pinned codex-cli 0.150.1 `gpt-5.6-sol` WebSocket bundle produced 4 missing properties, 8 additional properties, comparison outcome `breaking`, and support state `degraded`. That result is confounded by the harness-version and capture-context difference. Inference for the current live model: transforming the exact three `gpt-5.5` WebSocket reference bodies from bundle `6dac4e5c-4d01-4a7a-b3f4-b9c92d664215` through the production parser and HTTP serializer produced one missing property, `/type`, zero additional properties, outcome `breaking`, and support state `degraded`. The live 0.150.1 HTTP body was deleted on stream reset, so this inferred one-and-zero result is not an observed comparison of the bounded run.

## How claude solves origin matching, and how it generalises

The crux is that under a base URL override the client connects to loopback, so the host the addon sees changes. Claude's answer has two halves.

First, the listener itself carries the origin. Reverse mode serves exactly one upstream, and every captured run owns a dedicated listener (per run mitmdump, or a per run listener registered with the shared proxy, whose `mode_spec` already renders `reverse:{upstream}@127.0.0.1:{port}` per binding, `shared_proxy/models.py:47-55`). One listener, one harness, one provider origin.

Second, the anthropic matcher never reads the host. Path prefix only. That is why nothing had to be solved for claude explicitly.

The mechanism generalises, but the grok and codex matchers must change, because under reverse mode `flow.request.host` is `127.0.0.1` and their exact host checks fail. Two facts make the change small and safe:

- mitmproxy rewrites the Host header to the upstream host before the request hook runs (pinned evidence 4). So `flow.request.host_header` carries the true origin in reverse mode, and the original origin in regular mode. Nothing in `api/src` reads `host_header` today (verified by grep), so claiming it is free.
- The admission gate `addon_handlers.py:194-196` already ORs the three matchers, and the shared proxy demuxes flows by listen port before the gate, so a listener only ever presents one harness's traffic.

The change: `is_grok_responses_flow` and `is_codex_websocket_flow` accept a flow when the provider host matches either `request.host` or the parsed `request.host_header`. Method and path requirements stay exact. This is one matcher edit per harness plus reverse shaped test fixtures (existing tests build flows with `request.host` set, e.g. `test_addon_http_grok.py:22`, and keep passing). No per harness addon fork, no new matching concept.

Path preservation falls out of the base URL shapes. Grok's default base includes `/v1`, so the override is `http://127.0.0.1:<port>/v1` and the addon still sees `/v1/responses`. Codex's default is `https://chatgpt.com/backend-api/`, so the override is `http://127.0.0.1:<port>/backend-api/` and the addon still sees `/backend-api/codex/responses`. The reverse upstream is the bare origin in both cases.

The plumbing already exists: `CapturedRunRequest.upstream` threads to the claude builder today, and `default_upstream_for_harness` (`captured/models.py:58-60`) returns the empty string for codex and grok, which becomes their real origin. `_infer_mode_kind` (`shared_proxy/models.py:188-194`) special cases codex to `regular`; it collapses to "reverse with upstream" for all three.

The capture follow-up resolves which codex transport is active. Each baseline model has three completed wire exchanges, and every exchange carries `request_metadata.provider_metadata.x-codex-ws-stream-request-start-ms`: `gpt-5.5` 3 of 3, `gpt-5.6-luna` 3 of 3, `gpt-5.6-sol` 3 of 3, and `gpt-5.6-terra` 3 of 3. None has `request_wire_bytes`, the field populated by ordinary HTTP requests. The retained transport bytes remove any ambiguity in that marker: all 362 pre-existing codex transports are WebSocket upgrades to `https://chatgpt.com/backend-api/codex/responses`, with `Connection: Upgrade`, `Upgrade: websocket`, status `101`, and a first client frame whose event type is `response.create`. HTTP fallback appeared zero times in the retained provider transports.

The captured WebSocket URL has the same origin and base path as the pinned default `chatgpt_base_url`, with `codex/responses` appended. No retained capture or config artifact records a different `chatgpt_base_url`. This is evidence of consistency with derivation from the base. It does not prove derivation because the observed effective value never differs from the default. In particular, recorded bytes cannot establish that an `http://` base produces a `ws://` URL.

Still unproven: no retained codex capture used a mitmproxy reverse listener, so the bytes do not establish that mitmproxy 12.2.3 bridges a plaintext loopback WebSocket upgrade to the TLS upstream. The smallest test settles both remaining facts at once: run one codex-cli 0.150.1 turn with `chatgpt_base_url = "http://127.0.0.1:<port>/backend-api/"` against `--mode reverse:https://chatgpt.com@127.0.0.1:<port>`. Require an inbound loopback `GET /backend-api/codex/responses` with `Connection: Upgrade` and `Upgrade: websocket`, an upstream `101`, one client `response.create` frame, and terminal `response.completed`. The inbound connection proves the `http` to `ws` derivation; the upstream `101` and completed response prove the reverse bridge.

### HTTP fallback contingency: transport succeeds, capture does not

The bounded dev run settles the transport half of the contingency for codex-cli 0.150.1. The fallback addon returned `426` to each WebSocket upgrade, no `101` occurred, Codex immediately sent ordinary HTTP/2 `POST` requests to the same `/backend-api/codex/responses` path, the provider returned `200`, and the requested `gpt-5.5` turn completed as `HTTP_FALLBACK_OK`. These are captured facts from the run log and transcript.

The same run fails the capture acceptance criterion. The production addon parsed the `gpt-5.5` request far enough to log `system=6 tools=15 msgs=2`, then mitmproxy observed `200 OK (content missing)` followed by a client `CANCEL` reset. The error lifecycle deleted the provisional HTTP exchange. Only the two injected handshake failures remain on disk, and the session store contains no row for the HTTP request. The second HTTP request, model `gpt-5.6-luna`, followed the same lifecycle. Its purpose is unsettled; the transcript proves there was only one user turn.

The observed current-version request schema therefore cannot be compared with the same-model WebSocket reference. The closest captured comparison uses the older 0.144.0 `gpt-5.6-sol` fallback fixture and produces 4 missing and 8 additional properties, with a `degraded` support verdict. The version and context mismatch prevent attributing that full delta to transport. The current `gpt-5.5` transport-only inference produces one missing property, `/type`, no additions, and the same `degraded` verdict. That inference is consistent with the serializer contract and the older captured fixture, both of which omit the WebSocket envelope's top-level `type` on HTTP.

Decision: the fallback is proven as a provider transport and remains unusable as the capture contingency. A usable contingency requires the HTTP response lifecycle to retain and finalize the exchange when Codex resets the HTTP/2 stream after consuming the terminal response, followed by one bounded current-version rerun whose persisted request body can be compared directly. The primary WebSocket risk remains open, and its reverse-listener test above is unchanged.

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

Codex has the same question with a different answer already visible: `chatgpt_base_url` sits inside the auth route configuration itself (pinned evidence 7), so the token route follows the redirect. That traffic already transits the proxy today under explicit mode, and the reverse upstream is the same `chatgpt.com` origin, so nothing new is exposed. The codex unit's bounded test is the same shape: one turn, credential headers compared, both transports exercised.

## Grok's leader process model

The escape risk from a pre-existing native leader is resolved. Each of the six exact grok baseline runs wrote its transcript beneath its own `<run-id>/runtime-home/grok/sessions/...` path. The launch path creates that run-owned home, passes it to the child as `GROK_HOME`, makes `leader.sock` local rather than linking the native home's socket, and removes the runtime home when the run exits (pinned evidence 12). With Grok's default socket at `~/.grok/leader.sock`, the managed child resolves a different socket path for every run. A leader already running under the native `~/.grok/leader.sock` cannot be reused by a managed run.

The captures do not retain a leader PID, argv, environment, or socket connection. Reuse of an already running leader at the same run-scoped socket is therefore inferred from Grok's documented socket model. Under the normal launch sequence that leader was created inside the same managed environment and inherited the endpoint override. A wrong-environment leader would require another process to start first against the exact newly allocated transient `GROK_HOME`.

The smallest process observation, if direct proof is required, does not need provider traffic: hold one managed run open, record the Grok process tree and Unix socket endpoints, and require the client to connect to `<run storage>/runtime-home/grok/leader.sock` with no connection to the native `~/.grok/leader.sock`. Start a second client in that same run and require reuse of the same run-scoped leader PID.

## Capture audit against the plan

No captured provider behavior contradicts endpoint redirection. Codex is more dependent on the WebSocket leg than the first note implied because all retained provider transports use it. Grok's provider path and HTTP transport match the proposed override path. The explicit proxy logs also contain the auxiliary settings, telemetry, storage, update, and MCP traffic that the provider-only redirect intentionally removes, with no evidence that Transport Matters persisted those flows.

The live fallback run adds a separate capture-persistence risk. Endpoint redirection remains unaffected. The proposed HTTP contingency cannot preserve a current codex-cli 0.150.1 exchange through the observed HTTP/2 `CANCEL` lifecycle, so it cannot substitute for the primary WebSocket path today. The repository's older real fallback fixture proves that HTTP capture has worked for codex-cli 0.144.0 and corrects the claim that the fallback had never been exercised anywhere; it was absent from the retained channel-home transport census.

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

Independent of unit 2; requires only unit 1. Carry `chatgpt_base_url = "http://127.0.0.1:<port>/backend-api/"` into the run scoped `CODEX_HOME` config (the runtime home is already materialised per run, and `cli/toml_edit.py` exists for exactly this kind of write). Drop `CODEX_CA_CERTIFICATE` and the proxy variables. First checkpoint, before anything else: the bounded WebSocket test above, which now targets only the two remaining unknowns, URL scheme derivation and the reverse listener bridge.

The 0.150.1 `--force-http-fallback` checkpoint has now run once. Provider transport and turn completion passed; exchange retention, parsed persistence, and direct schema comparison failed because both HTTP/2 streams ended in client `CANCEL` and the provisional rows were deleted. Do not repeat the live checkpoint until the response lifecycle has a deterministic proof that this terminal reset retains the completed exchange. Then run one bounded current-version turn and require a persisted HTTP POST exchange, parsed request and response, a `wire_exchange` row, classifier and continuity outcomes, and a direct same-model comparator verdict. Until that passes, HTTP fallback is unavailable as the migration contingency.

### Unit 4: deletion

Everything in the deletion path, in one change, with the kept list untouched. Checkpoints: grep gates prove no `*_PROXY` assignment survives outside the removal sets and `cli/trust.py` and `cli/explicit_proxy.py` are gone; the full suite is green; one live canvas run per harness.

## Required proof

The end state proves one property three times: launch harness X, capture a genuine provider exchange, and observe that no process in the run's tree beyond the harness client had its network environment or trust surface altered. Concretely per harness: the captured exchange lands with schema, activity, and access outcomes matching an explicit proxy capture of the same account; `env | grep -i proxy` inside a run shell shows only `NO_PROXY`; and `gh api user` succeeds inside a grok run.

## Explicit exclusions

This design does not touch overlay coverage, the comparison pipeline, blessing ranges, or reference schema content; capture transport changes none of those inputs. It does not add certificate installation of any kind, keychain writes included. It does not migrate the shared proxy's ownership model; the per binding reverse mode it already supports is reused as is.
