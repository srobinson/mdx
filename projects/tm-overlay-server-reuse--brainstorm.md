# TM overlay server fetch — reuse map

Seat: `canvas-overlay-boundary:general:1:2.5` (scout, read-only).  
Warroom topic: `canvas-overlay-delta`.  
Tree: `scout/canvas-overlay-boundary` at `c03edbd96e30d5c2917994897686bd4223f40065`.  
Question: which existing seams would a **remote overlay fetch** bind to?

## Thesis

There is **no product outbound channel** today: no update check, no licensing ping, no telemetry phone-home, no overlay CDN client. The only durable remote-overlay *contract* already on disk is the **signed channel-update validator** (`validate_channel_update` + `RejectAllSignatureVerifier`), still inert and without a fetch writer. Fetch would be greenfield I/O; keying should bind to **harness observation + `match_release`**, not to browser `overlaysStore` or in-memory `OverrideStore`.

---

## Reuse Map

### 1. Outbound HTTP from TM (non-local)

| Class | Owner | Destination | Writer / reader | Precedence |
| --- | --- | --- | --- | --- |
| Anthropic token count | `counting.py:TokenCounter.count` via `addon_runtime.py:_build_capture_primitives` (`httpx.AsyncClient` `base_url="https://api.anthropic.com"`) | `POST /v1/messages/count_tokens` | Addon process; uses captured harness auth headers | Fail-soft → `None` |
| Claude OAuth refresh | `credential_broker.py:HttpxTokenExchanger.exchange` | `CLAUDE_CODE_OAUTH_TOKEN_URL` = `https://platform.claude.com/v1/oauth/token` | Credential broker at managed-home mint | Fail-closed `CredentialBrokerError` |
| Provider reverse proxy | mitmproxy reverse / `Settings.upstream_url` (default Anthropic) | Provider wire, not a TM control plane | Capture plane | Launch override |
| Loopback health / control | `gateway_supervisor.py` (`httpx.AsyncClient`), `desktop_runtime.py` (`urllib.request.urlopen`), `cli/runs_health.py` (`httpx.get/post` on local `/v1/runs`), `api/v1/run_proxy.py` client | Local gateway / local capture API | Process-local | N/A |

**None found: product phone-home.** Searches run:

- `rg 'httpx\.(get|post|AsyncClient)|urllib\.request' api/src/transport_matters --glob '*.py'` (production hits listed above; tests excluded)
- `rg -i 'update_check|check_for_update|license_key|saas|product.?account|telemetry.*http|posthog|sentry' api/src packages www desktop`
- `rg 'github.com/.*/releases|releases/latest|download.*json|fetch.*manifest|overlay.?server' api/src packages www desktop`

Install docs mention `curl …/releases/latest/download/install.sh` (`QUICKSTART.md`); that is human bootstrap, not a runtime client.

**Similar checked and rejected as reuse for overlay fetch:**

- `TokenCounter` / OAuth exchanger: third-party provider endpoints, auth is harness user credential, not TM product identity; wrong trust domain.
- Local `httpx` health clients: loopback only; no remote URL config pattern beyond port env.

---

### 2. How remote or configurable endpoints are expressed

| Mechanism | Owner | What it configures today | Shape |
| --- | --- | --- | --- |
| `settings.toml` | `config.py:TomlSettings` / `DatabaseSettings`; scaffold `settings.example.toml` via `ensure_settings_scaffold` | **Only** `[database] url` and `test_url` | TOML under channel home (`settings_path` → `default_storage_root()`) |
| `TRANSPORT_MATTERS_*` env | `env_keys.py` (`ENV_PREFIX`); readers `config.py:Settings` (`BaseSettings` `env_prefix`), launch `launch/environment.py` | Ports, `DATABASE_URL`, `HOME`, `CHANNEL`, `STORAGE_DIR`, `UPSTREAM_URL`, `GATEWAY_URL`, `CAPTURE_RPC_URL`, run identity fields, desktop smoke, etc. | Process env; env wins over toml for database (`resolve_database_url`) |
| Database URL rewrite | `config.py:resolve_database_url` + `database_url_with_database_name` + `channel.py` channel `database_name` | One operator Postgres server; path rewritten per channel | `[database] url` pattern operators already know |
| Gateway / capture RPC | `packages/gateway/src/main.ts` (`TRANSPORT_MATTERS_DATABASE_URL`, `CAPTURE_RPC_URL`); desktop `gatewayProcess.ts` | Local product plane composition | Loopback origins |
| Upstream provider | `Settings.upstream_url` / `env_keys.UPSTREAM_URL` | Provider reverse target | Not a TM content host |

**None found:** `OVERLAY_*_URL`, remote manifest base URL, CDN host, or settings family for signed channel blobs.

**Existing infra a fetch URL would extend (not invent):**

1. Add a field beside `DatabaseSettings` / `Settings` (env `TRANSPORT_MATTERS_*` + optional toml family) — same load path as `Settings.load` / `get_settings`.
2. Or ride a future channel-update download URL next to `validate_channel_update` (contract exists; download does not).

**Precedence rule already taught:** env overrides toml for database (`resolve_database_url`); session_store pin wins via `resolve_session_store_url`. A new overlay endpoint should follow env-over-toml, single resolver function, one writer of the resolved string at process start.

---

### 3. Where overlays / overrides persist; identity keys a fetch could use

#### Persistence homes

| Home | Owner | Lifetime | Scope keys | Apply path? |
| --- | --- | --- | --- | --- |
| Browser overlays | `www/packages/inspector/src/stores/overlaysStore.ts:useOverlaysStore` + `persistence.ts:INSPECTOR_STORAGE_KEYS.overlaysStore` (`"transport-matters-overlays"`) via `createFrontendPersistStorage` | Durable in **localStorage** (origin shared with canvas) | `OverlayScope` = `"shared"` \| `{ kind: "project", cwd }` | Docstring: draft model only; **apply-at-intercept not shipped** |
| Live override store | `overrides/state.py:OverrideStore` / `get_store` process singleton | In-memory, addon process | `(run_id, track_id)` via `normalize_scope` (`LEGACY_SCOPE_ID`) | Yes: `overrides/__init__.py:apply_overrides` on request IR; pipeline reads store |
| Shared-proxy override snapshot | `shared_proxy/models.py:OverrideSnapshotPayload` + `SetOverridesRequest`; push `SharedProxyManager.set_overrides` → subprocess `get_store` | Process + rehydrate after restart | `OverrideScopePayload` (run, track) | Live policy carrier product→capture |
| HTTP override routes | `api/v1/overrides.py` (sync after mutation) | Same as store | run/track | Writer of store + shared proxy |
| Disk under channel home | `storage_roots.py:default_storage_root` → `~/.transport-matters` (stable), `settings.toml`, `workspaces/`, observed also `baselines/`, `runtime/`, `executor-id`, … | Operator machine | Channel home; workspace slug/hash/run | **No** recorded-overlay file format or loader found |
| First-frame baselines | `baseline_harvest.py` default output `home / "baselines"` | Operator artifact digests | harness × model digests | Certification / schema parity, not user overlay |
| Compatibility manifest | `compatibility_store.py:embedded_compatibility_manifest` package resource `compatibility_releases_v1.json` | Ship-with-build | channel + harness_id + release_id | Gate at launch; not overlay payload |
| Enablement intent | `enablement_store.py` / `enablement_service.py:gate_harness_enablement` | Postgres, executor-scoped | executor + harness | Launch gate only |

**None found:** disk path for “precomputed recorded overlay per user × harness release”; server-synced overlay cache; IndexedDB overlay store beyond localStorage key above.

#### Identity keys that exist (fetch key candidates)

| Key | Owner | Notes |
| --- | --- | --- |
| `owner` | Session/space default `"local"` (`session/wire_store.py`, gateway activity) | Not a SaaS user id; single-tenant local owner string |
| Channel | `channel.py` / `Settings.channel` / `env_keys.CHANNEL` | `stable` \| `preview` \| `dev` |
| Harness id | Launch `Settings.harness`; `harnesses` descriptors | `claude`, `codex`, … |
| `raw_version` / `normalized_version` | `capabilities.py:probe_binary_version` → `probes/observation.py:build_harness_observation` / `extract_normalized_version` | Doctor prints raw probe line |
| `release_id` | `compatibility.py:match_release`; embedded entries | Per harness release in manifest |
| Wire client UA version | `client_version.py:detect_client_version` | e.g. `claude-cli/2.1.154`; tags unparsed wire shapes |
| TM version | `transport_matters.__version__` | Package metadata |
| `run_id` / `track_id` | Launch + `track_manager` | OverrideStore only; too fine for release overlay |
| Project `cwd` | `Settings.cwd` / meta; overlay project scope | Path leakage if sent server-side |
| Workspace path identity | `workspace.py` slug+hash | Path-derived |
| Model | IR / request | Present; not on `Overlay` type today |
| Provider `account_id` / `device_id` | IR metadata from wire | Provider identity, not TM product account |
| `executor_id` | Connections / inventory observation | Local executor scope for enablement |

**None found:** `org_id`, TM install fingerprint, license seat id, multi-user product account store.

**Precedence / writer rules already present:**

- Override lookup is **exact scope only** (no ancestor walk): `OverrideStore.get_all(scope=…)`.
- Shared-proxy snapshot is the product-plane→capture-plane policy carrier; generation ack exists.
- UI overlay draft and live `OverrideStore` are **two writers with no merge rule** to each other (overlay apply pipeline deferred).

---

### 4. Harness version detection owner (doctor lines)

Doctor output (`cli/diagnose.py:run_doctor`):

```text
for name, capability in detect_harnesses().items():
    _ok(name, capability.version or "version unknown")
```

| Role | Symbol | Responsibility |
| --- | --- | --- |
| **One home for `--version` probe** | `capabilities.py:probe_binary_version` | Spawn `[path, "--version"]`, first non-empty line; never raises; shared by doctor, certified observation, codex rollout metadata |
| Aggregate install map | `capabilities.py:detect_harnesses` → `detect_harness_descriptor` → `observe_resolved_binary` | PATH/`which` + probe |
| Normalize probe line | `harnesses/probes/observation.py:extract_normalized_version` | First token `normalize_version` accepts (`compatibility.py:normalize_version`) |
| Observation record | `probes/observation.py:build_harness_observation` → `LocalHarnessObservation` | `raw_version`, `normalized_version`, `probe_failed` / `harness_version_unknown` |
| Release match | `compatibility.py:match_release` | Advisories / gate from normalized version + channel state |
| Production gate caller | `compatibility_service.py` (launch gate) | First production `match_release` caller |
| Wire-time UA tag | `client_version.py:detect_client_version` | Distinct from binary probe; header-derived |

Doctor does **not** invent a second version path; it prints `HarnessCapability.version` from `detect_harnesses`.

---

### 5. Auth / account / licensing scaffolding

| Area | What exists | Owner |
| --- | --- | --- |
| Harness authentication methods | `harnesses/connections.py:AuthenticationMethod` (`claudeai`, `console`, `oauth_token`, `chatgpt`, `api_key`) | Probe / access evidence for harnesses |
| Credential location policy | Managed home link vs macOS Claude keychain broker | `cli/home_overlay.py`, `credential_broker.py` |
| Token exchange | OAuth refresh to Claude platform (above) | Broker only |
| CORS / Host allowlist | `Settings.cors_*`, `trusted_hosts` | Loopback product UI defense |
| Space owner | String `"local"` | Multi-tenant *shape* with one local owner |
| Package license | Apache-2.0 in `pyproject.toml` | Legal license of source, not product entitlement |

**None found:** TM product login, license key validation, seat metering, billing webhook, account registry, signed client certificate for overlay CDN, or any “TM account” table.

---

### 6. Closest existing infra for a remote overlay channel (reuse, not invent)

| Piece | Status | Bind how |
| --- | --- | --- |
| `validate_channel_update` + signature fields | **Built, tests, inert** (`RejectAllSignatureVerifier.verify` → always `False`) | Accept/verify a downloaded manifest or overlay bundle before activation |
| `embedded_compatibility_manifest` | Active fallback | Offline default when remote fail/reject |
| `match_release` / observation versions | Active at launch | **Fetch key:** `(channel, harness_id, normalized_version)` → `release_id` |
| `enablement_store` + launch gate | Durable Postgres intent | Pattern for “resolved before traffic”, not the overlay body |
| `SharedProxyManager.set_overrides` | Live flat `Override[]` install | **Install seam after fetch compile** (product/capture already speaks snapshots) |
| `apply_overrides` | Hot path | Consumer of installed list only |
| `overlaysStore` | UI draft/localStorage | Recording UX / local personal overlays; **not** release distribution home |
| Certification privacy rule | `certification.py` docstring: no raw bytes, credentials, absolute paths | Server overlay must not ship project `cwd` scopes |

---

## Searches run (none-found evidence)

1. Production HTTP: `rg 'httpx\.(get|post|AsyncClient)|urllib\.request' api/src/transport_matters` (exclude tests).  
2. Phone-home / license: `rg -i 'update_check|check_for_update|license_key|saas|telemetry|posthog|sentry|product.?account'`.  
3. Overlay server / remote manifest fetch: `rg 'overlay.?server|fetch.*manifest|releases/latest|download.*json'`.  
4. Settings families: read `config.py`, `env_keys.py`, `settings.example.toml` (database only).  
5. Overlay persist: `rg 'overlaysStore|OverrideStore|saveAsOverlay|INSPECTOR_STORAGE_KEYS'`.  
6. Version owners: `rg 'probe_binary_version|detect_harnesses|extract_normalized_version|detect_client_version'`.  
7. Auth/product: `rg -i 'license|billing|subscription|account' api/src packages` (hits are harness/SSE/activity subscriptions, not TM SaaS).

---

## Implications for “TM must call out to a server for the overlay”

| Decision facet | Constraint from this map |
| --- | --- |
| HTTP client | New code; do not overload count_tokens or OAuth clients |
| Config | New `TRANSPORT_MATTERS_*` (+ optional toml) following `Settings` / `env_keys` |
| Cache on disk | New under channel home; no existing overlay blob tree |
| Activation trust | **Reuse** `validate_channel_update` contract or same verifier/digest rules |
| Key | Prefer `normalized_version` + harness + channel (and `release_id`); not localStorage overlay id |
| Apply | After fetch, install via existing override snapshot path into `OverrideStore` |
| Auth for fetch | Greenfield product auth **or** public signed artifacts; no TM account stack to hang a private per-user pull on |
| Per-user personal overlays | Stay local (`overlaysStore` / future disk); do not key the release server on `cwd` or path |

## One-line thesis (for orchestrator)

**done:** `~/.mdx/projects/tm-overlay-server-reuse--brainstorm.md` — no product outbound fetch exists; bind remote release overlays to inert `validate_channel_update` + `match_release` keys and install via override snapshot, not localStorage `overlaysStore`.
