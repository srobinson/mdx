# Transport Matters cold first run journey

Scope: packaged product launch at `e1ca17d6`, starting with no channel home, no configured database, and no harness authentication. Static reads were pinned to that commit with `git show`. Another agent advanced the shared HEAD during the scout. Evidence is static source plus existing unit tests. No captured run, Postgres, Keychain, macOS Library, or channel home was touched.

## Gate order

There are eight ordered product gates from app launch to a usable captured agent.

1. **Channel configuration and session store**

   The packaged Electron app starts its bundled Python backend. `serve_desktop_backend()` immediately calls `preflight_session_store_or_exit()` before Uvicorn starts. `Settings.load(materialize=True)` creates the starter `settings.toml` when the channel home is absent. The starter has no database URL. The preflight then checks configuration, connectivity, and migration head in that order.

   A fully cold launch stops here on the configuration check. Python writes `error: session store is not configured` plus Docker and external Postgres setup instructions to stderr, then exits with code 2. The normal Electron child uses piped stdio and only forwards it during standalone smoke. The product user therefore sees the modal title `Transport Matters failed to start` and body `Transport Matters backend exited before readiness with code 2.` No BrowserWindow opens.

   Sources: `desktop/src/main.ts:startBundledStandalone`, `desktop/src/main.ts:startBackendAndCreateWindow`, `desktop/src/backendProcess.ts:launchBackendProcess`, `desktop/src/backendProcess.ts:forwardSmokeOutput`, `api/src/transport_matters/cli/desktop_cmd.py:serve_desktop_backend`, `api/src/transport_matters/cli/launch_runtime.py:preflight_session_store_or_exit`, `api/src/transport_matters/session_store_preflight.py:prepare_session_store`, `api/src/transport_matters/config.py:Settings.load`.

2. **Backend and Gateway readiness**

   After a database is configured, reachable, and migrated, Electron requires both the Python health endpoint and Gateway health endpoint to succeed. It creates the window only after both promises settle successfully. Either failure stops both children, shows the startup failure modal, and quits.

   Sources: `desktop/src/main.ts:startBackendAndCreateWindow`, `desktop/src/main.ts:showBackendStartupFailure`.

3. **Space, Workdir, and Canvas context**

   A new database has no Space inventory. The unscoped packaged launch tries to resolve the app home directory against owned Workdirs. An empty inventory returns `worktree_not_found`. Canvas renders `The Worktree for this Canvas no longer exists.` The launcher offers `Create new space` and `Create new Workdir`; there is no automatic first run creation.

   Sources: `www/packages/canvas/src/model/canvasIdentityOwner.ts:resolveWorkdir`, `packages/space/src/service/SpaceContextService.ts:resolveWorkdirContext`, `packages/space/src/domain/actingContext.ts:resolveWorkdirCandidate`, `www/packages/canvas/src/workbench/SessionCanvasRoute.tsx:actingContextErrorMessage`, `www/packages/canvas/src/launcher/workdirRows.ts:buildSpaceRows`.

4. **Harness executable and enablement**

   The native launcher always renders Claude and Codex as enabled `Native` rows. A pane click reaches `prepare_launch()`, which first resolves the executable. A normal missing binary prints an actionable PATH error inside the Python backend and raises `typer.Exit(2)`. The capture route has no translation for that exception, so the current wire result is an unstructured HTTP 500. Runtime falls back to `capture RPC failed with HTTP 500`, and the pane renders `<Harness> captured run failed to start: capture RPC failed with HTTP 500`.

   When the binary resolves, `gate_harness_enablement()` checks the exact executable with `--version` and reads the enabled intent from Postgres. A typed `harness_not_installed` or `harness_disabled` rejection becomes HTTP 409 and its message reaches the same pane alert.

   Sources: `www/packages/canvas/src/launcher/templateRows.ts:agentSpawnRows`, `api/src/transport_matters/cli/launch_runtime.py:prepare_launch`, `api/src/transport_matters/cli/launch_runtime.py:resolve_client_binary`, `api/src/transport_matters/harnesses/enablement_service.py:gate_harness_enablement`, `packages/runtime/src/adapters/CaptureRpcClient.ts:responseError`, `packages/runtime/src/service/RunManager.ts:createNew`, `www/packages/canvas/src/infrastructure/runtime/useCapturedRunBinding.ts:spawnErrorMessage`.

5. **Harness compatibility**

   Launch preparation reuses the exact executable observation and compares its normalized live `--version` result with the embedded channel release and minimum version. The build constant is `advisory`. Unknown, old, blocked, and unavailable compatibility outcomes are recorded but do not stop the pane spawn and are not rendered.

   The live enumerated catalog is a separate model and effort probe. Claude executes `claude -p /model` and `claude -p /effort`; Codex executes `codex debug models --bundled`. These results populate stored target observations. They do not supply the compatibility minimum or turn compatibility into a product gate.

   Sources: `api/src/transport_matters/harnesses/compatibility_service.py:gate_launch_preparation`, `api/src/transport_matters/harnesses/compatibility_service.py:COMPATIBILITY_ROLLOUT`, `api/src/transport_matters/harnesses/probes/claude.py:MODEL_ENUMERATION_PROBE`, `api/src/transport_matters/harnesses/probes/codex.py:MODEL_ENUMERATION_PROBE`, `api/src/transport_matters/harnesses/state_refresh.py:_refresh_target_snapshot`.

6. **Runtime home and credentials**

   Claude requires the managed fleet credential. The fleet owner credential lives under `~/.claude-auth` and is read through Keychain. Launch mints the shared access credential, links it into the per run home, and verifies the link identity. Missing fleet home, unreadable owner credential, or mint failure raises `CredentialBrokerError`. The capture route translates it to HTTP 503 with code `claude_fleet_credential_unavailable` and the message includes `CLAUDE_CONFIG_DIR=~/.claude-auth claude auth login`. Runtime preserves that message and the pane renders it.

   Codex has no credential broker. Its native auth source is `CODEX_HOME`, defaulting to `~/.codex`. Runtime home materialization symlinks native `auth.json` when it exists. `_symlink_file_if_exists()` silently returns when it does not, so absent Codex authentication does not stop pane spawn.

   Sources: `api/src/transport_matters/claude_fleet_auth.py:CLAUDE_FLEET_BOOTSTRAP_COMMAND`, `api/src/transport_matters/cli/home_overlay.py:claude_fleet_credential_error`, `api/src/transport_matters/cli/home_overlay.py:_mint_claude_credential`, `api/src/transport_matters/api/v1/capture_rpc_routes.py:prepare_capture`, `api/src/transport_matters/cli/runtime_home.py:plan_runtime_home`, `api/src/transport_matters/cli/codex_home.py:default_codex_home`, `api/src/transport_matters/cli/home_overlay.py:_link_overlay_credential_files`.

7. **Capture proxy and PTY**

   Python must prepare the capture lease and proxy before returning a spawn spec. Runtime then spawns the harness in a PTY. Typed capture failures retain their upstream status and code. Remaining preparation failures collapse to the generic HTTP fallback. PTY spawn failures retain their exception message. All are rendered in the captured run pane alert.

   Sources: `api/src/transport_matters/capture_rpc.py:CaptureLeaseRegistry.prepare_capture`, `packages/runtime/src/service/RunManager.ts:createNew`, `packages/runtime/src/server/runtimeRouter.ts:replyRunManagerError`, `www/packages/canvas/src/viewers/terminal/CapturedRunPane.tsx:CapturedRunPane`.

8. **Provider authentication**

   Authentication probe results do not participate in pane spawn. Startup refresh runs them as nonblocking diagnostics after the session store is live. An unauthenticated Codex pane can therefore open. If its ChatGPT websocket upgrade later returns 401 or 403, the wire observer emits sticky `auth_required`. Anthropic 401 produces the same condition. Canvas activity renders that later runtime fact as `Login needed`.

   This live label is derived from an actual provider response. It is independent of the stored `codex login status` or `claude auth status --json` probe result and does not make the six preflight checks visible.

   Sources: `api/src/transport_matters/harnesses/state_refresh.py:run_startup_refresh`, `api/src/transport_matters/harnesses/state_refresh.py:_refresh_connection_access`, `api/src/transport_matters/provider_conditions.py:classify_provider_response_status`, `api/src/transport_matters/live_status_observer.py:observe_codex_handshake_rejection`, `www/packages/canvas/src/workbench/chrome/RunVitalsStrip.tsx:STATUS_LABELS`.

## Six logical harness checks

The named six checks exist as a distributed read model. Only authentication adapters live in `harnesses/probes/claude.py` and `harnesses/probes/codex.py`. Installation comes from `capabilities.detect_harnesses()`. Compatibility comes from `compatibility.match_release()`.

| Harness check | Computed | Machine surface outside doctor | What the cold product user sees |
| --- | --- | --- | --- |
| Claude installed | Startup refresh resolves `claude`, checks runnability, and executes `claude --version`; launch repeats this over the resolved path | `GET /api/capabilities`, `GET /v1/harnesses`, `GET /v1/harnesses/enablement`, MCP `harnesses`; stored observation | Native Claude stays enabled and shows `Native`. Missing executable becomes the generic pane HTTP 500 fallback. A conditional specialist row can say `Install the required harness`, but it uses a separate live catalog call and requires a specialist template to exist. |
| Claude in version | Normalized live `--version` is matched against the embedded active release, minimum version, expiry, and blocks | `GET /v1/harnesses`, MCP `harnesses`, launch audit and per run compatibility facts | No native launcher state and no warning. Current rollout is advisory, so an old version proceeds. |
| Claude authed | Startup refresh runs `claude auth status --json` for the native connection; `loggedIn` maps to `authenticated` or `login_required` | `GET /v1/harnesses`, MCP `harnesses` | No probe result. Managed launch readiness instead comes from the fleet credential helper. A missing fleet credential produces the typed pane error with the bootstrap command. |
| Codex installed | Startup refresh resolves `codex`, checks runnability, and executes `codex --version`; launch repeats this over the resolved path | `GET /api/capabilities`, `GET /v1/harnesses`, `GET /v1/harnesses/enablement`, MCP `harnesses`; stored observation | Native Codex stays enabled and shows `Native`. Missing executable becomes the generic pane HTTP 500 fallback. The conditional specialist behavior matches Claude. |
| Codex in version | Normalized live `--version` is matched against the embedded active release, minimum version, expiry, and blocks | `GET /v1/harnesses`, MCP `harnesses`, launch audit and per run compatibility facts | No native launcher state and no warning. Current rollout is advisory, so an old version proceeds. |
| Codex authed | Startup refresh runs `codex login status`; exit 0 plus `Logged in using ChatGPT` or `Logged in using an API key` means authenticated, exit 1 plus `Not logged in` means login required, and contradictions mean unknown | `GET /v1/harnesses`, MCP `harnesses` | No probe result. Missing `auth.json` does not stop spawn. A later provider rejection can produce the separate `Login needed` runtime status. |

**Rendered outside doctor: 0/6.** This count is the six stored checks on the native first run launcher. The browser has no caller of `fetchCapabilities()` and no caller of `/v1/harnesses`. The two native rows ignore inventory. Conditional specialist installation text and provider derived `Login needed` are separate computations.

Sources: `api/src/transport_matters/capabilities.py:detect_harnesses`, `api/src/transport_matters/harnesses/state_refresh.py:refresh_harness_state`, `api/src/transport_matters/harnesses/inventory.py:harness_inventory`, `api/src/transport_matters/api/v1/capabilities.py:get_capabilities`, `api/src/transport_matters/api/v1/harnesses.py:get_harnesses`, `api/src/transport_matters/api/v1/harness_enablement.py:get_harness_enablement`, `api/src/transport_matters/api/v1/controlplane_mcp.py:harnesses`, `www/packages/core/src/transport.ts:fetchCapabilities`, `www/packages/canvas/src/launcher/templateRows.ts:agentSpawnRows`.

## Doctor reachability

`doctor` is not a first install journey. It directly calls `detect_harnesses()` and prints installed plus raw version for each harness. It does not read the stored harness inventory, run either authentication probe, or compute compatibility. It separately calls `claude_fleet_credential_error()` and prints the Claude bootstrap command when needed. It has no equivalent Codex native auth check.

Source: `api/src/transport_matters/cli/diagnose.py:run_doctor`.

## Authentication definitions

- **Claude launch ready:** `claude_fleet_credential_error()` can read the owner credential and, when required, the shared access credential. Launch then mints or refreshes the shared access credential and proves the per run credential resolves to it.
- **Claude probe authenticated:** `claude auth status --json` reports `loggedIn: true` in the probed native connection. This is diagnostic state and does not authorize the managed fleet launch.
- **Codex probe authenticated:** `codex login status` exits 0 with a recognized logged in line.
- **Codex launch credential present:** native `CODEX_HOME` contains `auth.json`, usually created by a prior native Codex login, and the per run overlay links that file. File presence is the materialization condition; the startup probe is the semantic authentication check.

## Pane error classification

The reported `capture RPC failed with HTTP 500` text is general. `CaptureRpcClient.responseError()` uses it only when a non successful response lacks a supported message in JSON. It does not classify authentication. At this revision:

- Missing Claude fleet authentication has a specific typed 503 and readable bootstrap message.
- Missing Codex `auth.json` does not fail capture preparation.
- Missing harness executable follows an unhandled `typer.Exit` path and can produce the generic HTTP 500 fallback.
- Other unhandled Python preparation exceptions can produce the same fallback.

## Test evidence

The existing harness was run without pytest bytecode or cache writes:

- API: 36 passed, covering the Claude and Codex probe parsers plus typed Claude credential translation.
- Runtime: 12 passed, covering capture RPC error body and fallback behavior.
- Canvas: 27 passed, covering captured pane spawn error rendering and the `Login needed` vitals label.

Another agent had advanced the shared HEAD before these executions. The targeted tests are unchanged from `e1ca17d6`. The only relevant source delta adds an unrelated terminal copy fallback to `CapturedRunPane`.
