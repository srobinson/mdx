---
title: CLIProxyAPI Security and Operations Review
type: projects
tags: [backend, security, reliability, operations, cliproxyapi]
summary: Read only review of credential handling, management exposure, proxy behavior, reloads, updates, concurrency, deployment, and engineering risk at the assigned commit.
status: active
source: backend-engineer
confidence: high
created: 2026-08-13
updated: 2026-08-13
---

# CLIProxyAPI Security and Operations Review

## Scope and verification boundary

Reviewed repository: `/Users/alphab/Dev/LLM/DEV/helioy/CLIProxyAPI`

Assigned and verified HEAD: `d757063c967426eaf78a71b1980ebdef5c2299eb`

The repository was pristine at the start of review. The review was read only. Source inspection covered authentication persistence, OAuth lifecycle, management routing and authentication, request logging, server and proxy behavior, retries, cooldowns, session affinity, configuration reload, plugins, remote updates, storage backends, deployment, CI, and tests. An explicit stop instruction ended the review before planned test commands ran. Existing tests cited below were inspected as evidence but were not executed in this review. Findings that depend on runtime proof are identified accordingly.

## Executive summary

The core architecture contains several strong controls. Management routes require a configured secret, OAuth callback state is constrained and short lived, callback files use restrictive permissions, refresh paths use concurrency control, retry waits honor cancellation, TLS verification remains enabled by default, and plugin installation applies archive path checks and hashes.

Six verified defects require attention before exposing the service outside a trusted host:

1. Gin trusts forwarded client IP headers from every peer by default. Management locality and abuse controls rely on that derived address.
2. Default OAuth token persistence creates credential files with process umask permissions and truncates files before encoding completes.
3. Error request logs retain complete prompt and upstream payload data by default, and the resulting log files are created as `0644` in `0755` directories.
4. Home request log forwarding sends the raw `Authorization` header.
5. The HTTP server has no header deadline or header size limit after protocol sniffing, which permits inexpensive connection exhaustion.
6. Session affinity accepts arbitrary client identifiers into a global cache with no capacity bound.

The automatically downloaded management page presents a separate high impact supply chain concern. The fallback page is accepted without digest verification and executes in the management origin. Remote model catalogs are also unsigned, and the main model updater reads an unbounded response.

## Verified defects

### 1. Forwarded IP spoofing weakens management access controls

**Severity:** High

`internal/api/server.go`, `NewServer`, lines 130 to 160, creates a Gin engine without configuring trusted proxies. Gin 1.10.1 enables forwarded client IP processing and trusts all proxy ranges by default. The repository contains no production call to `SetTrustedProxies`.

`internal/api/handlers/management/handler.go`, `Middleware` and `AuthenticateManagementKey`, lines 262 to 397, use `c.ClientIP()` to decide whether the caller is local, enforce `allow-remote`, select the local password path, and key failed attempt bans.

A directly connected client can supply `X-Forwarded-For: 127.0.0.1`. Gin will report the supplied loopback address under its default proxy configuration. The caller still needs a management credential, but the remote access boundary and IP based abuse control no longer provide their documented protection. Attackers can also rotate spoofed values to evade the five attempt ban.

**Recommendation:** Configure an explicit trusted proxy allowlist before serving requests. When no reverse proxy is required, disable forwarded address trust. Base management locality on the socket peer after trusted proxy resolution. Add an integration test with an external `RemoteAddr` and forged forwarded headers.

### 2. OAuth credential files can be broadly readable and partially written

**Severity:** High

`sdk/auth/filestore.go`, `FileTokenStore.Save`, lines 75 to 120, delegates normal token persistence to each provider's `SaveTokenToFile` implementation.

The Claude, Codex, Kimi, xAI, and Vertex implementations create parent directories with `0700`, then open the final credential path with `os.Create`:

* `internal/auth/claude/token.go`, `SaveTokenToFile`, lines 72 to 100
* `internal/auth/codex/token.go`, `SaveTokenToFile`, lines 56 to 80
* `internal/auth/kimi/token.go`, `SaveTokenToFile`, lines 82 to 110
* `internal/auth/xai/token.go`, `SaveTokenToFile`, lines 40 to 68
* `internal/auth/vertex/vertex_credentials.go`, `SaveTokenToFile`, lines 39 to 69

`os.Create` requests mode `0666`, subject to process umask. Existing directories are not tightened by `MkdirAll`. The repository's tracked `auths` directory was observed as `0755`. A conventional `022` umask therefore produces a `0644` bearer token file in a traversable directory.

The same implementations truncate the destination before JSON encoding finishes. Process termination, disk exhaustion, or an encoding failure can leave an empty or partial credential file. The store mutex serializes writers but does not make the write crash safe.

**Recommendation:** Centralize persistence in one atomic helper. Create a `0600` temporary file in the destination directory, encode, flush, close, rename, and fsync the directory. Enforce `0700` on the credential directory and verify existing file permissions at startup. This single helper should replace every provider specific file writer.

### 3. Default error logging persists full prompts and upstream payloads with permissive modes

**Severity:** High

`internal/config/config_load.go`, default initialization, lines 66 to 71, retains ten error logs by default. `config.example.yaml`, request logging settings around lines 121 to 123, documents error retention even when full request logging is disabled.

`internal/api/server.go`, `NewServer`, lines 144 to 158, installs request logging middleware. `internal/api/middleware/request_logging.go`, `RequestLoggingMiddleware`, lines 27 to 68, captures request details in error only mode. `internal/api/middleware/response_writer.go`, response finalization around lines 261 to 372, forces logging for API errors and includes deferred upstream request data.

`internal/logging/request_logger_format.go`, request formatting around lines 117 to 160, masks selected headers but writes the full request body, upstream request, upstream response, and response body. Prompts, tool inputs, attachments encoded in JSON, provider errors, and model output can therefore enter local logs.

`internal/logging/request_logger_writer.go`, log creation around lines 107 to 137 and directory creation around lines 263 to 271, uses file mode `0644` and directory mode `0755`.

`internal/api/middleware/request_logging_test.go`, `TestRequestLoggingMiddlewareCapturesLargeErrorRequestAndDeferredAPIRequest`, is static test evidence that error only mode captures a large request and deferred translated upstream request.

**Recommendation:** Default to metadata only error records. Require an explicit diagnostic setting for prompt and payload capture. Apply structured field allowlists, size bounds, and content redaction before persistence. Create log directories as `0700` and files as `0600`. Document retention, rotation, and secure deletion behavior.

### 4. Home logging forwards the raw authorization credential

**Severity:** High when Home and request logging are enabled

`internal/logging/request_logger_home.go`, Home forwarding around lines 22 to 71, clones the original request headers into the Home payload without applying the text log redactor.

`internal/logging/request_logger_home_test.go`, `TestFileRequestLogger_HomeEnabled_ForwardsWhenRequestLogEnabled`, lines 78 to 151, constructs `Authorization: Bearer secret` and asserts that the value reaches the Home request log payload.

This crosses a service boundary with the credential used to access the proxy. Header masking in `internal/util/provider.go`, around lines 222 to 234, protects textual formatting but does not protect this forwarding path.

**Recommendation:** Use one shared header sanitizer for every log sink. Remove authorization, API key, cookie, proxy authorization, and provider token headers before constructing a Home payload. Add negative tests for every recognized credential header.

### 5. HTTP header acquisition has no effective deadline after protocol sniffing

**Severity:** High for an Internet reachable deployment

`internal/api/server.go`, server construction around lines 248 to 252, sets only `Addr` and `Handler` on `http.Server`. There is no `ReadHeaderTimeout`, `MaxHeaderBytes`, or connection cap.

`internal/api/protocol_multiplexer.go`, `Serve` and connection routing around lines 38 to 123, assigns a ten second deadline while peeking at the first byte, then clears the deadline when the connection is handed to HTTP. A client can send one byte within ten seconds and hold the header open indefinitely. Each accepted connection receives a goroutine.

`config.example.yaml`, lines 1 to 3, binds all IPv4 and IPv6 interfaces by default. No application level rate limiter was found for public API or management routes.

The project rule that protects established upstream streaming does not prevent a bounded inbound header deadline.

**Recommendation:** Set `ReadHeaderTimeout`, a defensible `MaxHeaderBytes`, idle connection limits, and listener level connection caps. Add public request limits and stricter authentication limits. Preserve unbounded upstream response streaming after the upstream connection is established.

### 6. Session affinity cache has no global capacity bound

**Severity:** Medium

`sdk/cliproxy/auth/session_cache.go`, `sessionCache`, `SetAliases`, and cleanup, lines 18 to 38, 101 to 180, and 280 to 301, maintain a synchronized map with TTL cleanup. `maxStableSessionAliases` limits aliases per group to 64 but does not limit total groups or entries.

`sdk/cliproxy/session/identity.go`, `NormalizeExplicitID`, lines 43 to 55, limits each explicit value to 256 bytes. `sdk/cliproxy/auth/selector.go`, session selection around lines 655 to 690, admits client supplied explicit identifiers into the cache. The documented default TTL is one hour.

An authenticated client can generate distinct identifiers and retain an unbounded number of entries until expiry. Mutex protection prevents data races but does not constrain memory growth.

**Recommendation:** Add a global entry budget with LRU eviction, per principal quotas, metrics, and rejection or degradation behavior. Rate limiting reduces the growth rate but should not replace the capacity bound.

## Remote update and supply chain risks

### Management control panel

**Severity:** High design risk, with a verified unsafe fallback

`internal/managementasset/updater.go`, `StartAutoUpdater` and `EnsureLatestManagementHTML`, lines 59 to 117 and 191 to 291, fetch the control panel at startup and every three hours unless disabled. The normal GitHub release path compares the downloaded SHA 256 value with the release asset digest when the digest is present.

`ensureFallbackManagementHTML`, lines 293 to 310, downloads `https://cpamc.router-for.me/` when the local page is missing and release discovery fails. The function explicitly accepts and persists the page without digest verification. `atomicWriteFile`, lines 410 to 439, makes replacement crash safe but cannot establish publisher authenticity.

`internal/api/server_management.go`, `serveManagementControlPanel`, lines 284 to 311, serves the downloaded page from the proxy origin. The page is expected to handle a high privilege management key. A compromised release account, fallback host, DNS path paired with certificate compromise, or configured panel repository can deliver script with management origin privileges and exfiltrate that key.

**Recommendation:** Remove the unsigned fallback. Embed a known safe panel in the binary or require a signature verified against pinned release keys. Pin an expected publisher identity and version policy. Prefer a separate origin with a narrow, short lived management session.

### Model catalogs

**Severity:** Medium

`internal/registry/model_updater.go`, `StartModelsUpdater` and `fetchModelsFromRemote`, lines 74 to 181, fetch unsigned catalogs from a GitHub branch and a project host at startup and every three hours. Validation requires unique nonempty model identifiers but does not verify provenance or semantic bounds. The response is read using unbounded `io.ReadAll`.

`internal/registry/codex_client_models_updater.go`, `fetchCodexClientModelsFromRemote`, lines 66 to 119, uses an 8 MiB bound and validates the document, which is stronger. The `--local-model` flag disables both remote catalogs, and embedded data provides a fallback.

Remote catalog content affects model availability and per provider registration through `sdk/cliproxy/service_models.go` and the callback registered in `sdk/cliproxy/service_plugins.go`.

**Recommendation:** Apply a response bound to the main catalog. Sign catalogs or pin a release digest. Add strict field sizes, numeric ranges, model count limits, and an operator visible revision. Consider local catalogs as the production default.

## Verified strengths

### Management authentication

* `internal/api/server.go`, management route registration around lines 233 to 240, enables management routes only when a configured or environment supplied secret exists.
* `internal/api/server_management.go`, `registerManagementRoutes`, lines 27 to 29, applies availability and authentication middleware to the management group.
* `internal/api/handlers/management/handler.go`, `AuthenticateManagementKey`, lines 300 to 397, uses constant time comparisons for environment and local passwords, bcrypt for the configured secret, and a five failure, thirty minute ban.
* `internal/config/config_load.go`, secret normalization around lines 104 to 113, hashes plaintext management secrets before persistence.

These controls remain valuable after the forwarded IP defect is corrected.

### OAuth lifecycle

* `internal/api/handlers/management/oauth_sessions.go` defines a thirty minute pending session lifetime and a one minute completed lifetime.
* State validation around lines 334 to 359 constrains length and character set and rejects path traversal.
* Callback writes around lines 422 to 462 use a `0700` directory and `0600` file and require a matching pending provider and state.
* The cancellation guard around lines 302 to 310 runs immediately before credential save.
* Claude and Codex refresh implementations use single flight coordination. Claude tests named `TestRefreshTokens_UsesIndependentTimeout`, `TestRefreshTokensWithRetry_429BlocksImmediateReplay`, and `TestRefreshTokens_DeduplicatesConcurrentRefresh` provide static coverage evidence.

### Retry, cooldown, and concurrency

`sdk/cliproxy/auth/conductor_execution.go`, execution methods around lines 36 to 169, apply the same retry policy to standard, counted, and streaming operations and stop on context cancellation. `sdk/cliproxy/auth/conductor_selection.go`, retry selection around lines 675 to 862, honors retry after, cooldown state, maximum wait, jitter, and cancellable waits. State is guarded by mutexes and atomics. Session cache tests and cooldown store concurrency tests exist.

### Proxy and TLS behavior

`sdk/proxyutil/proxy.go` clones the Go default transport, supports HTTP, HTTPS, and SOCKS proxies, preserves certificate verification, and redacts proxy credentials from displayed URLs. The server TLS path in `internal/api/server.go`, around lines 273 to 300, loads the configured certificate and supports HTTP/2 and HTTP/1.1. No general `InsecureSkipVerify` behavior was found outside an explicit Home option and tests.

### Plugin installation

`internal/pluginstore/install.go` verifies supplied SHA 256 values, rejects archive traversal and nonregular target entries, and writes installed libraries through a temporary file and rename. Dynamic loading is disabled unless configured.

## Design tradeoffs and operational risks

### Plugin trust

`config.example.yaml`, plugin store comments around lines 80 to 101, states that dynamic libraries are trusted in process code. `internal/pluginhost/loader_unix.go`, load path around lines 111 to 162, uses native dynamic loading. A plugin therefore receives the service account's file, network, memory, and credential access. Archive hashes protect integrity against accidental corruption but do not create independent publisher authenticity when artifact and checksum share a release authority.

This is a documented trust model. Production use should restrict registries, pin versions and publisher keys, record provenance, and disable dynamic plugins by default. Untrusted third party plugins require process isolation and a capability based RPC boundary.

### Generic management API call

`internal/api/handlers/management/api_tools.go`, `APICall`, lines 99 to 215, lets an authenticated management caller send arbitrary URL, method, headers, body, host override, and selected credential substitutions. The operation is consistent with a high privilege administrator, but it is also an SSRF primitive. The response uses unbounded `io.ReadAll` around line 204. The sixty second client timeout is an intentional project exception.

Keep this endpoint behind the strongest management role, bound the response body, restrict schemes, block link local and private destinations unless explicitly enabled, and audit every call without logging secrets.

### Retry amplification

`config.example.yaml`, retry settings around lines 144 to 154, defaults request retries to three and permits trying every credential when `max-retry-credentials` is zero. Large credential pools can amplify latency and upstream spend during incidents. The present retry logic is careful and cancellable. A finite production default, idempotency classification, retry budget metrics, and per request attempt cap would make failure behavior easier to bound.

### Configuration reload consistency

`internal/watcher/config_reload.go`, `reloadConfig`, lines 88 to 143, validates the new file and preserves the prior hash when loading fails. It then publishes watcher configuration before invoking the client reload callback.

`sdk/cliproxy/service_config.go`, `commitConfigUpdate` and `applyConfigRuntime`, lines 84 to 192, serializes runtime updates and rejects stale commits. The config pointer and sequence are committed before manager, profiling, server, plugin, model, and auth work completes. Cancellation or a later runtime failure returns false without rollback. Tests in `sdk/cliproxy/service_executionregistry_test.go`, including `TestConfigCommitDoesNotHoldCommitMutexDuringCooldownPersistence` and Home worker cancellation cases, codify partial commit behavior.

This avoids long critical sections but does not provide transactional reload. Expose desired and applied revisions separately, keep the prior applied runtime until staging succeeds, and publish one immutable runtime snapshot after all fallible preparation completes.

### Storage backends

File, Postgres, Git, and object storage backends persist OAuth material in application readable form. Backend TLS, access policy, filesystem permissions, repository visibility, bucket policy, and encryption at rest carry the confidentiality boundary. Git storage has especially durable history semantics. Production guidance should prefer envelope encryption with a KMS managed key and avoid committing bearer tokens to version history.

### CORS and network defaults

`internal/api/server_middleware.go`, CORS middleware around lines 127 to 146, returns wildcard origin and headers. `config.example.yaml` binds every interface and disables TLS by default. Explicit API credentials prevent ordinary ambient credential CSRF, but wildcard CORS expands browser reach to local deployments and allows any origin to read responses when it obtains a key.

Provide a secure production profile: loopback binding unless deliberately overridden, TLS or documented trusted reverse proxy termination, an origin allowlist for management, trusted proxy configuration, public rate limits, and separate management listener support.

## Deployment, observability, CI, and maintenance

### Health and graceful operation

`internal/api/server_routes.go`, health route around lines 42 to 52, always returns `{"status":"ok"}`. It is useful as liveness only. It does not report auth store, Postgres, Redis, object store, Git mirror, Home, plugin, or remote dependency readiness.

Add distinct liveness and readiness endpoints. Readiness should use bounded, nonsecret dependency probes and report component states. Metrics should include active connections, header acquisition failures, request attempts, cooldown counts, session cache size and eviction, config desired versus applied revision, auth persistence failures, updater revision, and request log bytes.

### CI and test posture

The repository contains broad unit and integration coverage for OAuth state, refresh single flight, retry and cooldown behavior, session affinity concurrency, request logging, model validation, plugin installation, watcher reload, and service replacement behavior. The most important missing regression cases are:

1. Forged forwarded headers cannot obtain local management treatment.
2. Every credential file is exactly `0600`, its directory is `0700`, and interrupted writes preserve the prior file.
3. No log sink retains authorization or API key headers.
4. Error logging redacts prompt bodies unless diagnostic capture is enabled.
5. Partial HTTP headers are closed within the configured deadline.
6. Session affinity remains within a fixed memory budget under high cardinality input.
7. Unsigned management panel content is rejected.
8. Configuration reload either applies one complete runtime revision or leaves the prior revision active.

Add race testing for auth selection, session affinity, watcher reload, WebSocket lifecycle, plugin replacement, and shutdown. Add static analysis and vulnerability scanning to CI, with pinned tool versions and a documented exception process.

### Maintenance concentration

Several source files exceed the repository's stated 700 line limit, including `internal/store/gitstore.go`, `sdk/cliproxy/auth/conductor_cooldown.go`, `sdk/cliproxy/auth/conductor_selection.go`, `internal/registry/model_registry.go`, `internal/api/server_routes.go`, and management handler files. This concentration increases review cost and makes security invariants difficult to prove. Refactor around explicit owners for retry state, cooldown persistence, route groups, storage synchronization, and management resources before extending those files.

The Go module also includes a prerelease pseudo version of go-git v6. Treat prerelease dependencies as explicit operational risk, pin reproducible versions, record upgrade cadence, and scan the complete module graph before release.

## Prioritized remediation

### Before any remote deployment

1. Configure trusted proxies and add the forged forwarded header regression test.
2. Replace provider file writes with one atomic `0600` credential writer and enforce `0700` directories.
3. Sanitize every log sink, disable prompt capture by default, and restrict log permissions.
4. Add inbound header deadlines, header size limits, connection limits, and public rate limits.
5. Remove unsigned management page fallback and establish signed update provenance.

### Before production readiness

1. Bound the session cache and remote model downloads.
2. Separate desired and applied config revisions and stage reloads transactionally.
3. Restrict CORS and management network exposure.
4. Bound and audit the management API call endpoint.
5. Add readiness checks, security metrics, race testing, and dependency scanning.
6. Define encryption and retention requirements for every auth storage backend.

## Verdict

The service should remain limited to a trusted host or trusted private network until the forwarded IP, credential persistence, secret logging, HTTP header exhaustion, and management asset provenance issues are resolved. The current concurrency and OAuth structures provide a strong base. The remaining work is concentrated in boundary hardening, secret lifecycle controls, bounded resource use, and transactional operations.
