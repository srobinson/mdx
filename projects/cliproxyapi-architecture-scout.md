---
title: CLIProxyAPI Architecture Scout
type: research
tags: [cliproxyapi, go, proxy, oauth, streaming, websocket, sdk, helioy]
summary: End to end architecture trace of CLIProxyAPI at d757063c967426eaf78a71b1980ebdef5c2299eb, with stable seams and complexity risks.
status: active
source: codebase-analyst
confidence: high
created: 2026-08-13
updated: 2026-08-13
---

# Executive Summary

CLIProxyAPI is a Go 1.26 proxy that exposes OpenAI, Claude, Gemini, Codex, and related client protocols while selecting OAuth or API key credentials across provider executors. The durable architecture is a sequence of narrow seams: Gin routes, protocol handlers, model registry resolution, the auth manager, provider executors, pairwise translators, streaming forwarders, usage plugins, and an embeddable service lifecycle.

The main architectural risk is accumulated matrix complexity. Translation, management routes, Home control plane coordination, storage backends, and WebSocket replay contain substantial policy and state machinery. These areas remain bounded behind useful interfaces, but changes should preserve those owners rather than add parallel paths.

# Project Metadata

| Property | Evidence |
| --- | --- |
| Revision | `d757063c967426eaf78a71b1980ebdef5c2299eb` |
| Working tree | Clean when scouted |
| Module | `github.com/router-for-me/CLIProxyAPI/v7` |
| Language | Go 1.26.0 |
| HTTP stack | Gin |
| Realtime stack | Gorilla WebSocket, Pion WebRTC |
| Configuration | YAML plus environment variables and runtime Home overlays |
| Persistence | File store by default, optional Postgres, Git, and object storage |
| Scale | 1,123 Go files, 490 Go test files, about 370,121 Go lines including tests |

The repository has no `.fmm.db`, so FMM structural queries were unavailable. The scout used bounded source inspection after the FMM failure. The current `docs/sdk-*.md` examples still reference module v6 and Go 1.24, while `go.mod` declares v7 and Go 1.26.0.

# Architecture

## End to end request flow

1. **Process bootstrap.** `cmd/server/main.go:main` parses modes and flags, bootstraps plugins, loads `.env`, selects storage, installs the global token store, applies plugin configuration, and starts the service. Home JWT configuration can replace local runtime configuration before startup. See `cmd/server/main.go:72`, `cmd/server/main.go:140`, `cmd/server/main.go:274`, `cmd/server/main.go:377`, and `cmd/server/main.go:602`.
2. **SDK lifecycle.** `internal/cmd/run.go:StartServiceWithPluginHost` builds and runs `sdk/cliproxy.Service`. `sdk/cliproxy/service_lifecycle.go:Service.Run` starts usage collection, loads credentials, registers executors, constructs the API server, attaches relay services, starts HTTP, and starts either local watchers or Home subscription machinery. See `internal/cmd/run.go:33` and `sdk/cliproxy/service_lifecycle.go:32`.
3. **HTTP ingress.** `internal/api/server.go:NewServer` installs recovery, tracing, request logging, CORS, access control, retry settings, management handling, Home middleware, and routes. Its `http.Server` has `Addr` and `Handler` only, consistent with the project rule that established upstream connections must not receive general timeouts. See `internal/api/server.go:118`.
4. **Route selection.** `internal/api/server_routes.go:setupRoutes` exposes OpenAI chat, completions, Responses, images, video, Claude messages and token count, Gemini generate and interactions, realtime endpoints, and compatibility aliases. `internal/api/server_routes.go:unifiedModelsHandler` distinguishes model list shapes using path, headers, query data, Home mode, and client identity. See `internal/api/server_routes.go:42` and `internal/api/server_routes.go:575`.
5. **Protocol handling.** Handlers under `sdk/api/handlers/openai`, `sdk/api/handlers/claude`, and `sdk/api/handlers/gemini` parse the client contract and choose streaming or nonstreaming execution. Representative entry points are `OpenAIResponsesAPIHandler.Responses`, `ClaudeAPIHandler.ClaudeMessages`, and `GeminiAPIHandler.GeminiHandler`.
6. **Model and provider resolution.** `sdk/api/handlers/handlers_execution.go:executeWithAuthManagerFormats` invokes an optional plugin model router, resolves the route through `getRequestDetailsWithOptions`, assembles immutable request metadata, then delegates to the auth manager. Unknown models fail before upstream dispatch. See `sdk/api/handlers/handlers_execution.go:42` and `sdk/api/handlers/handlers_routing.go:159`.
7. **Credential selection.** `sdk/cliproxy/auth.Manager` owns credential state, selectors, schedulers, executors, retry configuration, aliases, cooldowns, and Home dispatch state. `Manager.executeMixedOnce` chooses the next provider and credential, prepares or refreshes auth, invokes interceptors, dispatches the executor, records the result, and rotates on eligible failure. See `sdk/cliproxy/auth/conductor.go:103` and `sdk/cliproxy/auth/conductor_execution.go:275`.
8. **Provider translation and dispatch.** The selected executor translates request bytes from the source format into its provider format, applies payload and thinking configuration, calls the upstream, reports usage, and translates response bytes back to the requested response format. Examples are `CodexExecutor.Execute` at `internal/runtime/executor/codex_executor_execute.go:21`, `GeminiExecutor.Execute` at `internal/runtime/executor/gemini_executor.go:125`, and `ClaudeExecutor.Execute` at `internal/runtime/executor/claude_executor_execute.go:19`.
9. **Response delivery.** Nonstream responses return translated bytes and headers. Streaming responses pass through `BaseAPIHandler.executeStreamWithAuthManagerFormats`, which obtains the first deliverable chunk before committing downstream headers. It may redispatch only before the first downstream byte, then `BaseAPIHandler.ForwardStream` owns cancellation, chunk forwarding, terminal errors, flushing, and keepalive behavior. See `sdk/api/handlers/handlers_stream.go:267` and `sdk/api/handlers/stream_forwarder.go:59`.
10. **Accounting and logs.** Executors use `helps.ExecutorUsageReporter`, which guarantees one usage publication, including zero token outcomes. `sdk/cliproxy/usage.Manager` dispatches records to plugins. Request logging separately captures request, response, streaming timeline, and error spool data. See `internal/runtime/executor/helps/usage_helpers.go:51`, `sdk/cliproxy/usage/manager.go:223`, and `internal/api/middleware/request_logging.go:31`.

## Translation architecture

The general protocol pipeline uses a pairwise byte translation registry rather than a single canonical request representation. `internal/translator/translator/translator.go:Register` indexes translators by source and target format; request, stream response, nonstream response, and token count operations dispatch through that registry. `internal/translator/init.go` imports protocol pairs so their `init` functions register implementations.

`sdk/cliproxy/executor.Request` deliberately carries provider shaped JSON bytes plus a `Format`; `executor.Options` retains source format, response format, and original request bytes. Provider executors perform translation immediately before upstream payload policy. The thinking subsystem is a narrower exception: it normalizes reasoning settings to a canonical `ThinkingConfig`, validates them centrally, then applies provider output.

This design keeps handlers and executors independently extensible. Its cost is an approximately 59,348 line translator area, including tests, with many pair specific implementations. New protocol work should extend the registry and shared translator helpers. A second translation pipeline would increase divergence.

## Model registry

`sdk/cliproxy/service_models.go:registerModelsForAuth` converts each active credential into registry model registrations, applying provider catalogs, configured exclusions, prefixes, aliases, plan tiers, and plugin models. `internal/registry/model_registry.go:ModelRegistry` tracks registrations per auth ID and exposes available models and sorted provider candidates. `internal/util/provider.go:GetProviderName` consults this registry, so availability derives from current registrations rather than static provider guessing.

`internal/registry/model_updater.go:StartModelsUpdater` refreshes remote catalogs every three hours, validates fetched data, and retains the last valid snapshot on failure. `--local-model` disables remote updates. Home mode disables the general models updater while retaining the distinct Codex client template updater. This split is intentional and visible in `cmd/server/main.go:modelCatalogUpdaterPlan`.

## Credential selection, retry, and cooldown

`sdk/cliproxy/auth/conductor.go:ProviderExecutor` is the central upstream seam. Built in selectors include round robin, weighted round robin, fill first, and session affinity. Scheduler state preindexes ready and cooling credentials to avoid repeatedly scanning the full set.

`Manager.Execute`, `Manager.ExecuteCount`, and `Manager.ExecuteStream` share selection and retry policy. Cross credential retry limits are distinct from per request retries. A single unauthorized response can trigger credential refresh and one immediate retry. `MarkResult` updates credential and model state, including transient cooldown, quota exhaustion, disable cooling behavior, and model scoped penalties. `conductor_selection.go:retryAllowed`, `shouldRetryAfterError`, and `closestCooldownWait` keep that policy in one owner.

Handler streaming adds one extra guard: bootstrap failures can redispatch before the first byte only. Home streaming explicitly avoids this handler level redispatch because Home owns credential scope and concurrency accounting.

## Streaming and WebSocket flow

The standard stream path delays downstream commitment until it has a valid first chunk. After commitment, errors are encoded into the active client protocol and the same upstream attempt remains authoritative. This prevents duplicate visible output.

OpenAI Responses WebSocket is a stateful facade. `sdk/api/handlers/openai/openai_responses_websocket.go:OpenAIResponsesAPIHandler.ResponsesWebsocket` upgrades the connection, reconstructs incremental request state, manages pinned credentials, supports local prewarm behavior, and invokes `forwardResponsesWebsocket`. The forwarder restores completion output, reconciles tool calls, emits terminal protocol errors, and records pending tool call IDs. See `sdk/api/handlers/openai/openai_responses_websocket.go:254` and `sdk/api/handlers/openai/openai_responses_websocket_forward.go:28`.

Codex can use HTTP or a persistent upstream WebSocket. `internal/runtime/executor/codex_websockets_executor.go:CodexAutoExecutor` chooses the transport per credential. `CodexWebsocketsExecutor` binds upstream connections to execution sessions and enforces the permitted WebSocket liveness read deadline in `internal/runtime/executor/codex_websockets_session.go:547`. Session teardown and auth changes invalidate the connection centrally.

`internal/wsrelay` is a separate relay facility attached during `Service.Run`. It should remain distinct from the OpenAI Responses WebSocket facade because it owns relay sessions rather than request protocol adaptation.

## Hot reload

Local mode uses `internal/watcher.Watcher` for configuration and credential file changes. It debounces events, creates complete snapshots, and dispatches coalesced auth updates. `sdk/cliproxy/service_config.go:commitConfigUpdate` validates and sequences configuration commits; `applyConfigRuntime` serializes runtime effects and rejects stale commits. `internal/api/server_reload.go:Server.UpdateClientsContext` updates retry settings, caches, live services, WebSocket handling, auth, access, protocol handlers, and management state.

Home mode does not start the file watcher. Its subscription feeds the same runtime application boundary through a staged commit process.

## Storage

`sdk/cliproxy/auth/store.go:Store` defines the durable credential seam with `List`, `Save`, and `Delete`. `sdk/auth/filestore.go:FileTokenStore` is the default. Postgres, Git, and object store implementations live under `internal/store` and also persist or mirror configuration where needed. Startup installs one selected store into the SDK registry at `cmd/server/main.go:602`.

Postgres has precedence when configured. Object storage and Git are selected when Postgres is absent; otherwise file storage remains active. Cooldown persistence is a separate optional seam with file and Postgres implementations. Home disables local stores because credential acquisition belongs to its control plane.

## Plugins

`internal/pluginhost/host.go:Host` publishes an immutable atomic `Snapshot` of loaded capabilities. `Host.ApplyConfig` loads platform artifacts, resolves priorities, registers capabilities, and atomically swaps the snapshot. Adapters bridge plugin executors, translators, normalizers, interceptors, usage plugins, access and auth providers, schedulers, model routers, models, routes, flags, and frontend auth into core interfaces.

The stable extension boundary is `sdk/pluginapi` plus `pluginhost.Host.Snapshot`. Dynamic library loading, RPC bridges, panic fuses, hot reload, artifact synchronization, and migration cleanup are implementation complexity behind that boundary.

## Home control plane

Home mode starts from JWT certificate claims in `internal/home/certificate.go:ConfigFromJWT`. `internal/home.Client` speaks Redis compatible commands over mTLS for configuration, models, credential acquisition and refresh, usage, logs, plugin tasks, cluster membership, and failover.

`sdk/cliproxy/service_home.go` stages Home overlays, syncs plugins, commits configuration, manages the subscriber lifetime, replaces execution registries, and publishes a new dispatch bundle only after successful runtime application. `sdk/cliproxy/auth/conductor_home.go:HomeDispatchBundle` atomically couples the active Home client and execution registry. `sdk/cliproxy/auth/home_selection.go:HomeDispatchSelection` owns one selected credential, its execution scope, cancellation resources, retention, and release ticket.

This transaction boundary prevents requests from observing a new configuration with an old credential registry. The Redis protocol client, cluster failover, release acknowledgements, plugin synchronization, and retained WebSocket concurrency make Home the largest state coordination surface.

## SDK embedding

`sdk/cliproxy.Builder` is the primary embedder entry point. `Builder.Build` accepts config, credential client providers, watcher factory, lifecycle hooks, core auth manager, access manager, cooldown store, plugin host, server options, management password, and post auth hooks. The resulting `Service` owns startup and graceful shutdown.

The useful public seams are:

* `cliproxy.Builder` and `cliproxy.Service`
* `auth.Store`
* `auth.ProviderExecutor`
* translator registration by format pair
* model registry registration
* usage plugins
* server options and lifecycle hooks

The SDK documentation should be refreshed before external use because its module and Go version examples lag the current code.

# Stable Seams

| Seam | Why it is stable |
| --- | --- |
| `cliproxy.Builder` to `Service` | One construction and lifecycle boundary for CLI and embedding |
| Gin route to protocol handler | Client protocol concerns stay outside auth and provider execution |
| `auth.Manager` and `ProviderExecutor` | Central owner for credentials, selection, retry, cooldown, refresh, and dispatch |
| `auth.Store` | Storage implementations share a minimal credential contract |
| Model registry per auth ID | Model availability follows live credentials and provider registrations |
| Translator format registry | Protocol pair implementations are discoverable without handler branching |
| Stream bootstrap to forwarder | Retry is bounded before downstream commitment |
| Usage manager to plugins | Executors publish one common accounting record |
| Plugin host atomic snapshot | Requests see one coherent capability set |
| Home dispatch bundle | Home client and execution registry change atomically |
| Config commit sequence | Local watcher and Home updates share ordered runtime application |

# Incidental Complexity and Change Guidance

1. **Pairwise translation matrix.** High file and line count is inherent to protocol coverage, but shared JSON surgery, event framing, and usage parsing should be factored before adding another pair.
2. **Management API routing.** `internal/api/server_management.go:registerManagementRoutes` and related handlers form a broad administrative surface. Keep management policy outside provider handlers.
3. **Home coordination.** Preserve staged configuration, atomic dispatch publication, execution scope release, and ordering tests. Direct mutation of auth maps or execution registries would weaken consistency.
4. **Responses WebSocket replay.** Incremental state, pinning, tool cache, prewarm, replay, and fallback HTTP are coupled. Changes need session level tests, not only payload unit tests.
5. **Git storage.** Repository reconciliation and recovery are large backend specific concerns. They should remain behind `auth.Store` and config persistence interfaces.
6. **Plugin runtime.** Dynamic loading and RPC are failure prone. Preserve priority ordering, snapshot publication, panic fusing, and stale capability pruning.
7. **Global registries.** The token store, model registry, translator registry, and usage manager use process global access in places. Embedders should construct one service per process unless isolation behavior is explicitly tested.

# Targeted Test Evidence

The source tree contains focused guards for the principal seams:

* Credential limits and cooldown: `sdk/cliproxy/auth/conductor_overrides_test.go:TestManager_MaxRetryCredentials_LimitsCrossCredentialRetries`, `TestManager_MarkResult_TransientErrorCooldownDefault`, and `TestManager_Execute_DisableCooling_DoesNotBlackoutAfter403`.
* Credential rotation: `sdk/cliproxy/auth/conductor_overrides_test.go:TestManager_DeepSeekCredentialFailuresRotateCredential` and `TestManager_UnknownUpstreamErrorRotatesAndPenalizesModelOnly`.
* Stream commitment: `sdk/api/handlers/handlers_stream_bootstrap_test.go:TestExecuteStreamWithAuthManager_RetriesBeforeFirstByte`, `TestExecuteStreamWithAuthManager_DoesNotRetryAfterFirstByte`, and `TestExecuteStreamWithAuthManager_HomeBootstrapFailureDoesNotRedispatch`.
* Stream framing: `sdk/api/handlers/handlers_stream_bootstrap_test.go:TestExecuteStreamWithAuthManager_ValidatesOpenAIResponsesStreamDataJSON` and `TestExecuteStreamWithAuthManager_AllowsSplitOpenAIResponsesSSEEventLines`.
* Model snapshots: `internal/registry/model_registry_test.go:TestGetAvailableModelsInvalidatesCacheOnRegistryChanges` plus Codex updater tests `TestFetchCodexClientModelsFallsBackToNextURL` and `TestRefreshCodexClientModelsKeepsLastValidSnapshot`.
* Hot reload ordering: `sdk/cliproxy/service_executionregistry_test.go:TestServiceSkipsStaleLocalConfigRuntimeApply`, `TestServiceConfigWorkerFinalizesRapidUpdatesInOrder`, and `TestServiceSerializesHomeAndWatcherConfigRuntimeApply`.
* Usage: `test/usage_logging_test.go:TestGeminiExecutorRecordsSuccessfulZeroUsageInQueue` and the stable serialization tests in `internal/redisqueue/plugin_test.go`.
* Plugins: plugin host tests cover priority chains, panic fuses, highest priority routing, stale executor pruning, and streaming callback lifetime.
* Protocol multiplexing: `internal/api/protocol_multiplexer_test.go:TestAcceptMuxNotBlockedByIdleConnection` protects HTTP and Redis coexistence on one listener.

# Critical Dependencies

| Dependency | Role |
| --- | --- |
| Gin | HTTP routing and middleware |
| Gorilla WebSocket | Downstream and upstream WebSocket transport |
| Pion WebRTC | Realtime transport |
| fsnotify | Local configuration and credential watching |
| logrus | Structured logging |
| gjson and sjson | Protocol payload inspection and mutation |
| pgx | Postgres configuration, credential, and cooldown persistence |
| go-git | Git backed storage |
| MinIO client | Object storage backend |
| go-redis | Redis integrations |
| Bubble Tea | Terminal UI |

# Relevance to Helioy

CLIProxyAPI already exposes the seams Helioy needs for embedding and orchestration: builder based lifecycle, model registry resolution, credential scheduling, plugin interception, usage publication, live configuration, and Home controlled execution scopes. Helioy integrations should call these owners directly. Parallel credential caches, retry loops, model maps, usage queues, or configuration clocks would duplicate policy and weaken the tested ordering guarantees.

The Home dispatch bundle and configuration sequence are especially relevant to control plane work. They provide an existing transaction boundary for changing remote configuration and credential ownership while requests remain active.

# Verification and Confidence

* Source revision verified with `git rev-parse HEAD`: `d757063c967426eaf78a71b1980ebdef5c2299eb`.
* Working tree verified clean with `git status --short` before the scout.
* File counts and line counts were measured from the pinned checkout.
* Symbols and tests above were inspected or located in the pinned checkout.
* No build or test command was run after the explicit stop instruction. Test references are source evidence, not a claim of execution in this scout.
* Confidence is high for module boundaries, ownership, and request flow; medium for rarely exercised Home failover behavior because it was source traced without a live Home environment.

# Open Questions

1. Which translator pairs account for current production traffic, and which can be retired before the next protocol expansion?
2. Should SDK globals become service scoped before multiple embedded instances are supported?
3. Which Home failover and release acknowledgement paths have environment level coverage beyond unit tests?
4. Should SDK documentation updates be made a release gate for v7?
