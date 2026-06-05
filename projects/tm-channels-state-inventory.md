# Transport Matters channel state inventory

Verified against repository HEAD `9734986ae5fc2ae7771be5eb890872d4b2e848f0` on 2026-07-28. The machine was inspected in its supplied post reset state. No application, reset, launch, database mutation, or secret read was performed.

This report uses **leak** in the brief's broad sense: state that is shared when channel ownership requires isolation, or persistent state that the current channel reset never removes. The nine numbered findings include reset scope gaps. Deliberate external inputs are inventoried separately and are not counted as leaks.

## Runnable identities today

The committed channel table contains two runnable channels.

| Runtime choice | Home | Logical database | Default ports | Electron identity | Electron user data |
| --- | --- | --- | --- | --- | --- |
| `stable` | `~/.transport-matters` | `transport_matters` | proxy `8787`, web `8788`, gateway `8789` | name `Transport Matters`; app id `io.helioy.transport-matters` | `null` in `ChannelSpec`, so Transport Matters does not set an absolute path |
| `preview` | `~/.transport-matters-preview` | `transport_matters_preview` | proxy `8797`, web `8798`, gateway `8799` | name `Transport Matters Preview`; app id `io.helioy.transport-matters.preview` | `~/.transport-matters-preview/electron-user-data` |

Evidence: `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/api/src/transport_matters/channel-specs.json:stable`, `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/api/src/transport_matters/channel-specs.json:preview`, `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/api/src/transport_matters/channel.py:ChannelSpec`, `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/api/src/transport_matters/channel.py:resolve_channel_spec`.

### What “dev desktop” means

Dev desktop is a launch mode layered onto one of the two channels. `scripts/local-desktop-dev-mode.sh` defaults `TRANSPORT_MATTERS_CHANNEL` to `stable`, validates the selected id against the committed channel table, uses development ports `18787`, `18788`, `18789`, and Vite port `15173`, then passes the selected channel into Electron. Electron resolves the same `ChannelSpec` as packaged desktop and applies its app name, app id, optional explicit user data path, and icon before registering the desktop lifecycle.

The desktop package name is `transport-matters-desktop`. Current startup calls `app.setName()` with the selected channel's Electron name. The live canonical root `~/Library/Application Support/Transport Matters` was modified on 2026-07-28. The live legacy root `~/Library/Application Support/transport-matters-desktop` was last modified on 2026-06-20. Current source contains no writer that explicitly selects the legacy root. These facts identify the legacy root as residue from an earlier development identity, while current stable development uses the stable channel identity.

Evidence: `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/scripts/local-desktop-dev-mode.sh:channel`, `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/desktop/src/env.ts:resolveDesktopChannelSpec`, `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/desktop/src/main.ts:applyChannelIdentity`, `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/desktop/src/main.ts:registerDesktopLifecycleFromEnv`, `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/desktop/package.json:name`.

## Persistent state ownership

### Channel home and Tier 1

| State | Path and ownership | Creator or dependency | Normal removal | Channel reset |
| --- | --- | --- | --- | --- |
| Channel home | Stable `~/.transport-matters`; preview `~/.transport-matters-preview` | `default_storage_root()` resolves the active channel | No whole home removal exists | Preserved |
| Home override | `$TRANSPORT_MATTERS_HOME` | `default_storage_root()` gives this value precedence over the selected channel | Operator managed | Reset operates inside the resolved override |
| Settings | `<home>/settings.toml` | `ensure_settings_scaffold()` creates the packaged example on first setup | Operator managed | Preserved |
| Executor identity | `<home>/executor-id` | `local_executor_id()` mints one UUID per resolved home | No runtime remover | Preserved |
| Transcript denylist | `<home>/transcript_denylist.json` | Runtime reads an optional operator file | Operator managed | Preserved |
| Channel template catalog | `<home>/runtimes/**` | Runtime registry reads templates after the shared catalog | Operator managed | Preserved |
| Detached desktop record | `<home>/runtime/desktop.json` | Detached desktop launch records process identity and ports | Stop and stale discovery unlink the record | Preserved if present |
| Detached desktop log | `<home>/runtime/desktop.log` | Detached desktop launch appends output | No runtime remover | Preserved |
| Shared proxy state | `<home>/runtime/shared-proxy/shared-proxy.pid`, socket, and `logs/shared-mitmdump.log` | Backend lifespan owns `SharedProxyManager` | Normal termination removes PID and socket; log and directories remain | Preserved |
| Workspace root | `<home>/workspaces` | `default_workspaces_root()` | Reset can sweep immediate workspace identity children | Swept unless `--skip-tier1` |
| Workspace identity | `<home>/workspaces/{slug}/{hash}` | Canonical workspace identity | Reset removes each immediate child recursively | Swept unless skipped |
| Run root | `<workspace>/{run_id}` | Captured launch | Durable by design | Swept with workspace identity |
| Run lock | `<workspace>/lock` | `WorkspaceLock` opens and locks the file | Kernel lock releases; file remains | Swept with workspace identity |
| Run liveness manifest | `<run>/manifest.json` | Captured launch writes launch facts | Normal launch cleanup unlinks it | Swept with Tier 1 |
| Tier 1 artifacts | `<run>/index.jsonl`, `sessions.json`, `compatibility.json`, `transcripts/**`, exchange request, response, transport, event, audit, and turn files | Proxy and transcript capture | Durable by design | Swept with Tier 1 |
| Proxy log | `<run>/logs/mitmdump.log` | Per run proxy process | Durable with run | Swept with Tier 1 |
| Managed agent overlay | `<run>/runtime-home/claude` or `<run>/runtime-home/codex` | Captured launch copies or links source content and provides local writable agent state | Clean launch exit removes it; a crash can retain it inside Tier 1 | Swept with Tier 1 |
| Live prompt delivery | `<run>/.live-prompt-delivery.json` and `.live-prompt-delivery.lock` | Delivery binding writes request state and an advisory lock file | Claim or discard removes JSON; lock file persists | Swept with Tier 1 |

Evidence: `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/api/src/transport_matters/storage_roots.py:default_storage_root`, `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/api/src/transport_matters/storage_roots.py:default_workspaces_root`, `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/api/src/transport_matters/config.py:ensure_settings_scaffold`, `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/api/src/transport_matters/harnesses/executor_identity.py:local_executor_id`, `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/api/src/transport_matters/transcript_denylist.py:read_transcript_denylist`, `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/api/src/transport_matters/runtime_registry.py:runtime_template_roots`, `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/api/src/transport_matters/desktop_runtime.py:desktop_record_path`, `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/api/src/transport_matters/desktop_runtime.py:desktop_log_path`, `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/api/src/transport_matters/shared_proxy/manager.py:SharedProxyManager`, `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/api/src/transport_matters/lock.py:WorkspaceLock`, `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/api/src/transport_matters/storage/disk_layout.py:DiskStorageLayout`, `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/api/src/transport_matters/captured_run.py:prepare_captured_run`, `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/api/src/transport_matters/controlplane/delivery_binding.py:LivePromptDeliveryBindings`.

### Electron and web storage

| State | Path and ownership | Creator or dependency | Normal removal | Channel reset |
| --- | --- | --- | --- | --- |
| Stable Electron profile | Observed `~/Library/Application Support/Transport Matters`, 608632 KB | Stable desktop identity; Chromium owns the profile layout | No application remover | Preserved |
| Preview Electron profile | `~/.transport-matters-preview/electron-user-data` | Preview `ChannelSpec` gives Electron an explicit path | No application remover | Preserved because reset only sweeps `<home>/workspaces` |
| Legacy development profile | Observed `~/Library/Application Support/transport-matters-desktop`, 554076 KB | Surviving package name identity from earlier development startup | No current writer or remover found | Preserved |
| Inspector browser state | Local Storage keys `transport-matters-ui`, `transport-matters-overlays`, and `transport-matters.panel.dismissed.*` | Zustand persistence through `localStorage` | User profile deletion or explicit browser storage clear | Preserved inside profile |
| Canvas browser state | Local Storage keys `transport-matters-theme`, `transport-matters-captured-run`, `transport-matters-canvas:{canvasId}`, `transport-matters-keymap`; Session Storage key `transport-matters-acting-context-locator` | Canvas persistence adapters | User profile deletion or explicit browser storage clear | Preserved inside profile |
| Launcher hint | Local Storage key `tm.launcher.hintSeen` | First run hint | Explicit browser storage clear | Preserved inside profile |
| macOS preferences | Observed `~/Library/Preferences/io.helioy.transport-matters.plist`, `com.electron.transport-matters.plist`, and `com.electron.transport-matters.helper.plist` | Electron and macOS preference domains | No application remover found | Preserved |

Both observed Electron profiles contain Chromium profile state, including Local Storage, Session Storage, Cookies, Preferences, WebStorage, caches, network state, and trust state. Local Storage and Session Storage under the canonical profile were modified on 2026-07-28. The equivalent legacy files remain present from the earlier profile.

Evidence: `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/www/packages/core/src/persistence.ts:createFrontendPersistStorage`, `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/www/packages/inspector/src/stores/persistence.ts:INSPECTOR_STORAGE_KEYS`, `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/www/packages/canvas/src/infrastructure/persistence/storageKeys.ts:CANVAS_STORAGE_KEYS`, `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/www/packages/canvas/src/infrastructure/persistence/canvasCacheStorage.ts:canvasCacheKey`, `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/www/packages/canvas/src/launcher/FirstRunHint.tsx:HINT_SEEN_KEY`, `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/desktop/src/main.ts:applyChannelIdentity`.

### Agent homes, credentials, trust, and temporary files

| State | Path and ownership | Creator or dependency | Normal removal | Channel reset |
| --- | --- | --- | --- | --- |
| Native source homes | `~/.claude`, `~/.codex`, environment selected home, or explicit agent home | Overlay materialization reads configuration and links approved content | Agent or operator managed | Preserved |
| Shared runtime catalog | `~/.agent-runtimes/runtimes/**`, or `$AGENT_RUNTIMES_ROOT` | Runtime registry reads this first | External runtime manager or operator managed | Preserved |
| Claude fleet auth home | `~/.claude-auth` | Dedicated `CLAUDE_CONFIG_DIR` for fleet login and broker lock | Operator managed | Preserved |
| Broker lock | `<Claude auth source>/broker.lock` | Credential broker advisory lock | Lock releases; file remains | Preserved |
| Fleet Keychain credential | macOS Keychain service `Claude Code-credentials-{hash(~/.claude-auth)}` | Claude login and credential broker read | Keychain deletion | Preserved |
| Per run Claude Keychain credential | macOS Keychain service `Claude Code-credentials-{hash(runtime overlay)}` | Claude Code can import the access only credential seeded into a runtime overlay | Keychain deletion | Preserved after overlay cleanup |
| Mitmproxy CA | `~/.mitmproxy/mitmproxy-ca-cert.pem` and sibling mitmproxy state | Mitmproxy generates its global CA home | Manual mitmproxy state removal | Preserved and shared by both channels |
| Generated Codex trust bundle | `${TMPDIR}/transport-matters-codex-ca-*/codex-ca-bundle.pem` | Codex launcher merges system roots with the mitmproxy CA | Registered process exit handler removes directories | Reset does not remove crash residue |
| Long socket fallback | `/tmp/tm-sp-{pid}-{digest}/s.sock` and its parent | Shared proxy control server uses this when the channel home socket path is too long | Socket close unlinks the socket; parent cleanup is absent | Reset does not remove parent or crash residue |

The supplied fixture states that `~/.claude-auth` is absent and all namespaced Keychain records were deleted. Live inspection found `~/.mitmproxy` present at 28 KB and `~/.agent-runtimes` present at 11940 KB. No `transport-matters-codex-ca-*` or `tm-sp-*` directory was present in the current temporary root.

The shared runtime catalog and native source homes are intentional external dependencies. They affect launch behavior after a product reset, but Transport Matters does not own their lifecycle. They are excluded from the nine leak count.

Evidence: `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/api/src/transport_matters/cli/home_seeders.py:resolve_source_home_dir`, `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/api/src/transport_matters/cli/home_overlay.py:materialize_runtime_home_overlay`, `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/api/src/transport_matters/cli/home_overlay.py:CLAUDE_FLEET_AUTH_HOME`, `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/api/src/transport_matters/credential_broker.py:SecurityOwnerCredentialStore`, `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/api/src/transport_matters/runtime_registry.py:runtime_template_roots`, `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/api/src/transport_matters/cli/trust.py:mitmproxy_ca_cert_path`, `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/api/src/transport_matters/cli/codex_trust.py:_resolve_generated_codex_ca_certificate`, `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/api/src/transport_matters/cli/codex_trust.py:_cleanup_codex_ca_cache_for_process_exit`, `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/api/src/transport_matters/shared_proxy/manager.py:_control_socket_path`, `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/api/src/transport_matters/shared_proxy/control.py:SharedProxyControlServer`.

## PostgreSQL lifecycle

Transport Matters manages logical databases inside an existing PostgreSQL server. `channel ensure-db` creates the selected channel database if absent and applies migrations. Normal application startup requires a reachable configured database and applies migrations under an advisory migration lock. No application code starts PostgreSQL, stops PostgreSQL, creates a cluster, deletes a server data directory, or removes a Docker volume.

The source checkout offers optional PostgreSQL 17 through Docker Compose. That service binds `127.0.0.1:55432`, initializes database `transport_matters`, and persists its cluster in Docker volume `tm-postgres`. `README.md` tells the operator to run `docker compose up -d`. The setup failure message gives the same operator action.

The repository's default development endpoint was reachable during this inventory. Read only catalog inspection returned exactly:

1. `postgres`
2. `template0`
3. `template1`
4. `transport_matters`
5. `transport_matters_preview`

No `tm_test_*` database was present. The test harness creates per test databases named `tm_test_{pid}_{uuid}` and session templates named `tm_test_template_*`. Fixture finalizers drop normal test databases; the stale sweep targets template databases. A killed test process can therefore leave a non template `tm_test_*` database. The channel reset ignores all test databases.

Post reset meaning:

1. A channel reset drops the selected logical database with `WITH (FORCE)`, recreates it, and migrates it.
2. The other channel database remains.
3. Test databases remain.
4. The PostgreSQL server, cluster, Docker container, and `tm-postgres` volume remain outside application lifecycle.
5. A machine with no running server still fails setup. Reset cannot produce a self starting first launch because no embedded database exists.

Evidence: `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/api/src/transport_matters/cli/channel_cmd.py:ensure_channel_database`, `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/api/src/transport_matters/session/migrate.py:apply_migrations`, `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/api/src/transport_matters/session/testing.py:TestDb`, `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/api/conftest.py:test_db`, `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/docker-compose.yml:postgres`, `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/docker-compose.yml:tm-postgres`, `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/api/src/transport_matters/session_store_preflight.py:session_store_setup_help`.

## Existing reset script audit

`scripts/reset-channel-store.sh`:

1. Defaults to channel `stable`.
2. Resolves settings, the channel database URL, and the workspace root through application code after exporting `TRANSPORT_MATTERS_CHANNEL`.
3. Refuses to proceed when PostgreSQL reports active sessions for the target database or `pgrep` finds a matching detached desktop backend, unless `--force` is supplied.
4. Requires the operator to type the channel id unless `--yes` is supplied.
5. Drops only the target logical database with `WITH (FORCE)`, recreates it, and runs migrations.
6. Removes every immediate child under the resolved `<home>/workspaces`, unless `--skip-tier1` is supplied.
7. Runs schema and data count checks after migration.
8. Supports `--dry-run`.

Safety conclusion:

1. The channel id and logical database mapping are sound when the normal channel homes are used.
2. The default target is destructive stable. Typed confirmation protects interactive use. `--yes` removes that confirmation. `--force` bypasses the liveness gate, after which `DROP DATABASE ... WITH (FORCE)` can disconnect active clients.
3. An ambient `TRANSPORT_MATTERS_HOME` collapses stable and preview storage roots. The database name still follows the selected channel, while the Tier 1 sweep uses the shared override. Resetting either channel can therefore delete captures belonging to the other channel.
4. The liveness process match covers detached desktop backend commands containing the selected channel. It does not prove the absence of every process using the target home or database.
5. Reset preserves the home root and all non workspace children. It also preserves Electron profiles, plist preferences, Keychain credentials, the global mitmproxy home, temporary crash residue, test databases, PostgreSQL server state, and Docker state.

Evidence: `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/scripts/reset-channel-store.sh:usage`, `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/scripts/reset-channel-store.sh:gate`, `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/api/src/transport_matters/storage_roots.py:default_storage_root`, `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/api/src/transport_matters/config.py:resolve_database_url`.

## Post reset machine evidence

| State | Observed result |
| --- | --- |
| `~/.transport-matters` | Present, empty, 0 KB |
| `~/.transport-matters-preview` | Present, empty, 0 KB |
| `~/.claude-auth` | Absent |
| Namespaced Claude Keychain records | Deleted according to the supplied fixture |
| `~/.mitmproxy` | Present, 28 KB |
| `~/.agent-runtimes` | Present, 11940 KB |
| Canonical Electron profile | Present, 608632 KB, modified 2026-07-28 |
| Legacy Electron profile | Present, 554076 KB, modified 2026-06-20 |
| macOS preference plists | Three present: current stable app id, legacy Electron app, legacy helper |
| Temporary Codex CA cache | None found |
| Temporary shared proxy socket directory | None found |
| Development PostgreSQL catalog | Stable and preview databases present; no test database present |

Under current source, an empty stable home loads no database URL. `doctor` therefore records a session store failure even when the source checkout's PostgreSQL endpoint is reachable. The existing databases do not supply application configuration.

Evidence: `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/api/src/transport_matters/config.py:Settings.load`, `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/api/src/transport_matters/config.py:resolve_database_url`, `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/api/src/transport_matters/config.py:ensure_settings_scaffold`.

## Nine reset leaks or scope gaps

1. **Stable Electron path is implicit, with two surviving profiles.** Stable `ChannelSpec` supplies no absolute user data directory. The canonical `Transport Matters` profile and legacy `transport-matters-desktop` profile both retain complete Chromium and product storage. The reset knows neither path. This counts as one leak, as directed.
2. **Preference identities survive separately.** Three product related plist files remain outside channel homes. The reset has no preference domain inventory or cleanup.
3. **Claude Keychain records outlive homes.** Fleet and per run services are keyed by hashed Claude config paths. Removing an overlay or channel home does not delete their Keychain records.
4. **Mitmproxy trust is global.** Both channels depend on `~/.mitmproxy`; the current reset neither inventories nor removes this shared CA state.
5. **The channel home reset is partial.** Only `<home>/workspaces/*` is swept. Settings, executor identity, desktop record and log, shared proxy log and directories, transcript denylist, channel templates, and preview Electron user data can remain under the selected home.
6. **The home override defeats storage isolation.** One ambient `TRANSPORT_MATTERS_HOME` collapses both channel roots. A channel reset then sweeps a shared workspaces tree while dropping only the selected channel database.
7. **Crashed test databases can survive.** Test finalizers drop per test databases only when they run. The stale sweep handles templates. Channel reset ignores all `tm_test_*` databases.
8. **Server and volume lifecycle are outside reset.** Logical database recreation leaves the PostgreSQL cluster, container, and Docker volume intact. On a serverless machine, first launch still fails because Transport Matters does not start its database prerequisite.
9. **Temporary cleanup depends on clean process exit.** Generated Codex CA directories use an exit handler. Shared proxy long path socket cleanup unlinks the socket but leaves its parent. Crashes can retain both classes, and channel reset never inspects them.

## Boundary for a future true fresh start

A complete design needs an explicit ownership policy before deletion:

1. Channel owned: selected home, selected logical database, selected Electron profile, selected preference domain, and channel attributable credential records.
2. Product global: legacy Electron identities, shared CA state, and product temporary directories.
3. External dependency: native agent homes, shared agent runtime catalog, system trust roots, PostgreSQL server or cluster, Docker installation, and operator selected homes.
4. Safe reset must resolve every target from committed channel data, reject a shared `TRANSPORT_MATTERS_HOME` unless the operator explicitly chooses a global reset, prove relevant processes are stopped, and report external prerequisites it intentionally preserves.

The present script is suitable for rebuilding one channel's logical database and deleting its Tier 1 captures under normal homes. Its name and confirmation should not imply whole product or machine state removal.
