# Startup screen scout

Repo main `84d2c66d`. Read only. Target: NOW.md Phase 1 startup model (every-startup re-entrant gate: TM operational first including database picker, then harness availability with fix-actions in-app; zero harnesses is valid).

---

## 1. What EXISTS today

### Shell and entry

| Piece | Path / symbol | Role |
|-------|---------------|------|
| Canvas app | `www/packages/canvas/src/App.tsx` → `CanvasApp` → lazy `SessionCanvasRoute` | Product surface on open |
| Shell host | `www/packages/shell/src/rootShell.tsx` | Mounts canvas / inspector |
| Workbench | `www/packages/canvas/src/workbench/SessionCanvasRoute.tsx` | Identity, activity stream, `CanvasWorkbench`; **no startup readiness gate** |
| Command center | `www/packages/canvas/src/launcher/CommandCenter.tsx` | ⌘K palette; zero chrome when closed |

### First-run / harness surface (#353 + #354)

| Piece | Path / symbol | Role |
|-------|---------------|------|
| Hint only when closed | `FirstRunHint` | One-shot localStorage fade of "⌘K to command"; **not** readiness |
| Harness cards UI | `firstrun/FirstRunScreen.tsx` | Renders only when command center is **open**, scope is **settings**, query empty |
| Card model | `firstrun/harnessCards.ts` (`harnessCard`, `inventorySummary`, `installationState`) | Installed / authenticated facts from stored inventory; `none_installed` is a valid summary note |
| Inventory fetch | `firstrun/useHarnessInventory.ts` → `fetchHarnessInventory` → `GET /v1/harnesses` | Polls while installations unobserved |
| Enablement write | `FirstRunScreen` PUT `/v1/harnesses/{id}/enablement` → `api/v1/harness_enablement.set_harness_enablement` | Only in-app fix action on cards |
| Auth remediation | Card text: show `authenticationCommand` as **copyable CLI string** ("Run `…` to sign in") | Diagnosis + terminal handoff, not in-app login driver |
| Inventory API | `api/v1/harnesses.get_harnesses` → `harnesses/inventory.harness_inventory` | Joins detect/enablement/connections/compatibility/launch_options |

### Launch readiness (#354)

| Piece | Path / symbol | Role |
|-------|---------------|------|
| Predicate | `captured/readiness.launch_readiness` | Fresh read-only checks |
| HTTP | `api/v1/launch_readiness.get_launch_readiness` → `GET /v1/launch-readiness` | No materialize |
| TS types + client | `www/packages/core/src/types/launchReadiness.ts`, `transport.fetchLaunchReadiness` | Browser mirror |
| Hook | `firstrun/useLaunchReadiness` (stale forever until explicit retry) | Used by launcher data, not a full-screen gate |
| Launcher use | `launcher/useLauncherData` → `templateRows.buildAgentRows` / `launchBlockedReason` / `launchReadinessRows` | Blocks **agent spawn rows** with failure subtitle; adds "Retry launch readiness" row |
| Infrastructure checks today | `session_store` (`check_session_store`), `mitmdump`, `node`, `gateway` | Subset of doctor |
| Harness checks today | per launch-eligible harness: enablement, client binary (`resolve_client_binary`), credential (`harness_credential_error` / `resolve_harness_credential_source`) | Mixed into same payload |
| Ready semantics | `ready = all(infra) and any(harness binary+credential ready)` | **Zero harnesses ⇒ `ready=false`** |

### Doctor (CLI only)

`cli/diagnose.py::run_doctor`: python, mitmdump, addon, node (warn), gateway, web bundle (warn), `detect_harnesses()`, storage write probe, default ports, session store **schema at migration head**, credential advisory, live runs. Printed to terminal; **not** exposed as HTTP or UI.

### What a user sees on launch

| User | Experience |
|------|------------|
| New or returning, product open | Canvas workbench. Optional fading ⌘K hint once. **No modal, no gate, no doctor surface.** |
| Opens ⌘K → Agents | Launch readiness may disable spawn rows and show retry; templates show `readinessLabel` from catalog |
| Opens ⌘K → Settings (empty query) | `FirstRunScreen` harness cards: install/auth facts, enable toggle, CLI login string |
| Session store down | Backend may run store-less (`main.py` lifespan logs and continues). Inventory errors: "Harness inventory unavailable" + Retry. Launch readiness reports `session_store_unavailable`. No setup picker. |

There is **no** "new user branch" vs "returning user branch" for readiness. First-run content is buried under Settings, not every-startup.

---

## 2. What is MISSING against the target

### Every-startup re-entrant check

**Missing.** No route-level or app-shell gate on `SessionCanvasRoute` / desktop boot. Failures surface only inside ⌘K (agents/settings) or as partial API errors. Disappearing DB on run fifty does not force a setup surface; it degrades inventory and readiness quietly.

### TM-operational gate (doctor-class)

**Partial machinery, wrong placement and incomplete set.**

| Target check | Today |
|--------------|--------|
| python | doctor only |
| mitmdump | doctor + `launch_readiness` |
| addon | doctor only |
| node | doctor (warn) + readiness |
| gateway | doctor + readiness |
| web bundle | doctor warn only |
| storage | doctor only |
| ports | doctor only |
| session store schema | doctor (revision head); readiness only **reachability** via `check_session_store` (no schema) |

Not shown at product open; not ordered as a dedicated TM-operational stage before harness UI.

### Database as gate's first call + picker

**Missing.**

- No UI for docker / BYO connection string / managed-by-us.
- No API that writes a connection string into channel config.
- Fail-hard / no-DB-mode: process still starts store-less (`main.py` on `MissingDatabaseConfigError`); product does not stop at a setup picker.
- Guidance exists only as CLI/help strings (`session_store_setup_help`, `database_url_guidance`).

### Harness availability (past the gate)

**Mostly exists as Settings cards + inventory**, with gaps:

| Element | Gap |
|---------|-----|
| Installed / auth facts | Present on cards |
| Compatible | Inventory carries compatibility; **cards do not surface it** as a first-run fact |
| Probes non-gating for launch | Contract intent yes; readiness **credential + binary still fold into `ready` and block agent spawn** |
| Zero harnesses valid | Cards/`inventorySummary` agree; **`LaunchReadiness.ready` disagrees** (requires any harness ready) |
| Fix-action per state | Enablement toggle only; install/auth/DB are Retry or "run this CLI" text; **no in-app login driver** (NOW §1.3 still future) |

### Fix-action-per-state (in app, no terminal)

**Largely missing.** Remediation is terminal-oriented (doctor hints, `session_store_setup_help`, card `authenticationCommand`). Enablement is the exception.

---

## 3. REUSE MAP

| Needed capability | Existing owner | Notes |
|-------------------|----------------|-------|
| Doctor check set | `cli/diagnose.py::run_doctor` | Terminal printer; extract/share check functions, do not reimplement |
| Session store reachability | `session_store_preflight.check_session_store` | Used by readiness |
| Session store migrate/prepare | `session_store_preflight.prepare_session_store` | Launch/CLI paths; schema fix without doctor |
| Schema head check | `diagnose.run_doctor` session-store branch (`current_revision` / `migration_head`) | Not in readiness |
| Setup help text | `session_store_setup_help`, `database_url_guidance`, `MissingDatabaseConfigError` | docker compose + ensure-db + settings path |
| Ensure DB exists | `cli/channel_cmd.ensure_channel_database` / `channel ensure-db` | CLI/script only today |
| Connection string config | `config.resolve_database_url`, `Settings.database`, `[database] url` in channel-home `settings.toml`, env `TRANSPORT_MATTERS_DATABASE_URL` | Precedence: env → toml |
| Scaffold settings file | `config.ensure_settings_scaffold` / `Settings.load(materialize=True)` | Creates example toml; **does not set URL from UI** |
| Write settings.toml from product | **none found** | Searched `api/v1` for settings write / database configure routes: no matches |
| Launch readiness HTTP + types | `captured.readiness`, `api/v1/launch_readiness`, `@tm/core` launchReadiness | Reuse; split TM vs harness ready flags |
| Binary / mitmdump / node / gateway resolve | `launch.binaries`, `gateway_supervisor.resolve_*` | Already in readiness infra checks |
| Detect harnesses | `capabilities.detect_harnesses` | Doctor + inventory path |
| Credential predicate | `credential_source.harness_credential_error`, `resolve_harness_credential_source` | Readiness harness checks; NOT probes |
| Login command string | inventory / descriptor `authentication_command`; `credential_source.login_command` (NOW) | Text only until login driver |
| Harness inventory UI | `FirstRunScreen`, `harnessCards`, `useHarnessInventory` | Reuse for post-gate stage |
| Enablement write | `PUT .../enablement` | Keep |
| Template readiness labels | `runtime_registry._catalog_summary` → `RuntimeTemplateReadiness`; `templateRows.readinessLabel` | Launch-time template state, not startup gate |
| Channel home / storage roots | `channel.ChannelSpec`, `storage_roots`, `default_storage_root` | Where settings.toml lives |
| Desktop gateway DB env | `desktop/src/gateway/gatewayProcess.ts` `resolveGatewayDatabaseUrl` | Reads same toml/env; no picker |
| In-app login PTY driver | **none found** as product feature | NOW points at `PtyPort` / gateway sibling; not built |
| Docker-managed / SaaS managed store | **none found** beyond compose + ensure-db docs | |

---

## 4. DATABASE picker specifically

### Where the connection string lives

1. Env: `TRANSPORT_MATTERS_DATABASE_URL` (`env_keys.DATABASE_URL`) on `Settings.database_url`
2. File: channel home `settings.toml` → `[database] url` (`config.settings_path` → `default_storage_root()` / channel home)
3. Runtime pin: `Settings.with_session_store_url` / `resolve_session_store_url` for process-local override

Channel database **name** is rewritten from the URL path via `database_url_with_database_name` + `ChannelSpec.database_name`.

Example defaults: packaged `settings.example.toml` → `postgresql://tm:tm@localhost:55432/transport_matters` (docker-compose oriented).

### What writes it today

| Writer | What it does |
|--------|----------------|
| Operator / env | Manual |
| `ensure_settings_scaffold` | Copies example toml if missing (includes a default URL string) |
| `channel ensure-db` | Creates DB on server using resolved URL; does not invent a picker UX |
| Scripts (`local-desktop-dev-mode.sh`, reset) | Resolve/print/bootstrap; not product UI |
| **No product API or canvas form** | — |

### When store is absent or schema missing

| Situation | Behavior |
|-----------|----------|
| Not configured (`MissingDatabaseConfigError`) | Backend lifespan: session store disabled, continues without pool. Desktop gateway may omit `DATABASE_URL`. |
| Unreachable URL | `check_session_store` error string; readiness check fails; inventory 503; FirstRun error + Retry |
| Schema missing / behind | Doctor fails with `db upgrade` hint. `prepare_session_store` migrates on launch paths. Readiness **does not** assert migration head. Auto-migrate is not an in-app button. |

No degraded "use product without DB" product mode is designed; process degradation exists, which fights the "store is precondition" rule.

---

## 5. Smallest first slice

**Split and gate on existing launch-readiness infrastructure only: every canvas startup must consume `GET /v1/launch-readiness`, treat infrastructure checks (session_store first) as a re-entrant blocking surface before workbench use, and change `LaunchReadiness.ready` so green infrastructure with zero ready harnesses is success.**

Why this slice, not a plan:

- Reuses `launch_readiness`, HTTP, core types, `useLaunchReadiness`, `check_session_store`, failure codes, and FirstRun error/retry patterns.
- Fixes the false coupling that marks zero harnesses as not ready (blocks Phase 1 validity).
- Creates the every-startup re-entrant shell the target requires, without yet building docker/BYO/managed picker or login PTY.
- Surfaces DB absence as the first failed infra check with existing help text (`session_store_setup_help` / detail strings); a later slice can replace "Retry + CLI" with a picker that writes `[database] url`.

Out of slice (next, not this): settings write API + three-option DB picker; full doctor parity (addon, storage, ports, schema); in-app login driver; moving harness cards from Settings-only to post-gate stage.

---

## Bottom line

#353/#354 gave harness evidence cards under Settings and a launch-readiness predicate that gates agent spawn, not product entry. Missing is the every-startup TM-operational gate (DB first, picker that writes one connection string), doctor-class checks in the open surface, fix-actions without the terminal, and readiness semantics that treat zero harnesses as operational success.
