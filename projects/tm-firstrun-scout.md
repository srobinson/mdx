# tm-firstrun-scout — the first-run screen area (Phase 1.4)

Scouted at main `101287bf` in a read-only worktree. Governing law: NOW.md "Phase 1 — first
run" (the startup model, 1.4, 1.5), docs/ARCHITECTURE.md (two-plane rule, product-plane
gateway, canonical context package), CLAUDE.md WWW section. Lens: reuse, simplification,
efficiency, altitude (the /code-review reuse lens; /code-review itself is user-invocable only
in this session, the `simplify` skill's four angles were loaded instead).

PR#352 (in flight) lands the credential-source predicate; this scout maps main and names the
seam where it plugs in (Reuse Map §A4).

---

## Reuse Map

### A. Backend read surfaces (Python plane)

**A1. `GET /v1/harnesses` — the card API already exists and is card-shaped.**
`api/v1/harnesses.py::get_harnesses` serves `harnesses/inventory.py::harness_inventory`, the
one inventory join ("drives every read surface (REST, MCP, and the deferred first-run
screen)" per its own docstring — the screen is its named consumer). Per harness
(`HarnessInventoryItem`), six groups:

- `descriptor` — `harness_id`, `display_name`, `command_name`, `launch_eligible`.
- `installation` — stored observation with explicit `observed` (absence of a row is
  `observed=false`, never "known absent"); `installed`, `executable_path`,
  `raw_version`/`normalized_version`, `observed_at`; `confirmed_installed` property.
- `enablement` — `configured`, `enabled`, `eligible` (enabled ∧ confirmed_installed).
- `channel` + `compatibility` — pointer state and the advisory `match_release` outcome
  (`CompatibilityOutcome`, `block_reason_code`).
- `connections` — per-connection `authentication_status` / `authentication_method` /
  `access_status` probe evidence with staleness suppression (`access_stale` blanks stale
  statuses so a reader can never mistake old evidence for live).
- `target_observations` + `launch_options` — the enumerated catalog and the resolver's
  eligible options.

Everything a card renders today: installed (with version), enabled, compatible,
authenticated-as-probed, and launchable. **Missing for 1.4:** a credential-predicate field
(§A4), and any reachability signal beyond probe evidence. One failure mode: a single 503
`harness_inventory_unavailable` (`api/v1/harnesses.py::inventory_unavailable`) whenever the
session store is out — which on a fresh install it is (§A5).

Data freshness: rows are written only by the startup refresh
(`harnesses/state_refresh.py::refresh_harness_state`), spawned as a background task when the
session-backed services start (`main.py::_start_session_backed_services`). No store, no
refresh, no rows. `api/v1/capabilities.py` and `api/v1/harness_enablement.py` (GET + PUT
`/harnesses/{id}/enablement`) are thin projections of the same join, so the card surface
cannot disagree with them; the enablement PUT is the card's ready-made enable/disable action.

**A2. `cli/diagnose.py::run_doctor` — the gate list exists, CLI-only, output-shaped.**
Check list at main: python ≥3.12, mitmdump, packaged addon, node (warn), gateway entry
(fail/warn), web bundle (warn), per-harness `detect_harnesses()` (warn), storage dir
write-probe, proxy/web port defaults (warn), session store (configured → reachable →
migration head, via `config.py::resolve_database_url` + `session/migrate.py::current_revision`
vs `migration_head`), claude fleet credential (advisory warn, via
`cli/home_overlay.py::claude_fleet_credential_error`), live-runs report
(`report_runs_health`). Exit non-zero on any fail.

**No API route serves any of this.** `main.py`'s `/health` returns a static
`{"status": "ok"}` and can never carry the gate. The checks are inline in one ~218-line
function printing through `typer` closures (`_ok`/`_fail`); there is no structured check
model to serialize. Moving the list to the UI therefore means refactoring checks into data
first — which the repo's own 150-line function budget already demands (Quality Map §Q1).
Serving it is viable precisely because the backend boots store-less when the DB is absent
(§A5): the API is alive to report its own gate. The only state it cannot self-report is
"backend down", which is Electron main's territory (§C3).

Two checks change meaning over HTTP and should be re-scoped, not blindly ported: the python
version check is trivially true if the API answers, and the port checks describe defaults
the running server already bound past.

**A3. `RuntimeTemplateReadiness` — the card-state vocabulary to reuse, not extend-by-invention.**
`runtime_templates.py`: `state: "ready" | "needs_setup" | "unavailable" | "invalid"` +
typed `reasons` (`"harness_not_installed"`, `"target_unavailable"`). Produced by
`runtime_registry.py::_catalog_summary` from `detect_harnesses()`. Mirrored by hand in
`www/packages/core/src/types/runtimeTemplates.ts` and rendered by
`launcher/templateRows.ts::readinessLabel` (module-private — Quality Map §Q3). 1.5 is one new
reason literal (`credential_unavailable`) fed by the predicate, never by probe output. The
first-run cards should speak this same state/reasons shape rather than mint a parallel enum.

**A4. The credential predicate seam (where PR#352 plugs in).**
At main the predicate is `cli/home_overlay.py::claude_fleet_credential_error` ("shared with
doctor so the diagnostic and the launch path can never disagree"), backed by
`claude_fleet_auth.py::fleet_home_unavailable_reason` +
`credential_broker.py::SecurityOwnerCredentialStore`. Claude-only, macOS-shaped. #352
re-dispatches on credential source and extends this into the one predicate launch, doctor,
and the screen all read (NOW 1.2). The screen-side seam: a per-harness credential field on
`HarnessInventoryItem` (a seventh group beside `connections`), fed by the #352 predicate.
Until it lands, cards render `connections[].authentication_status` as what it is — stored
probe evidence, display-only — because probes must never gate anything
(RUNTIME-SURFACING-S2-PLAN S2g item 4, restated in `ConnectionDiagnosticsInfo`'s docstring).
Wiring #352 in is then one field addition in `_harness_item`, not a card redesign.

**A5. The DB gate — one value, one file, and the failure mode is "refused", not "missing".**
The connection string lives in `[database] url` of `settings.toml` in the canonical channel
home (`config.py::settings_path` → `storage_roots.py::default_storage_root`), env override
`TRANSPORT_MATTERS_DATABASE_URL`; `config.py::resolve_database_url` rewrites the database
path per channel. `ensure_settings_scaffold` materializes the file from the packaged
`settings.example.toml`, **which ships a concrete default**
(`postgresql://tm:tm@localhost:55432/transport_matters`). So a fresh install never raises
`MissingDatabaseConfigError`; it fails at connect with "connection refused" unless the
compose Postgres is up. `cli/diagnose.py::_session_store_failure` already classifies exactly
these causes (refused / auth / no-database / timeout) into one human line — the store
picker's error vocabulary already exists.

When the store is absent the API degrades cleanly: `main.py::_start_session_backed_services`
logs "Session store disabled" and returns, `api/v1/session_store.py::optional_session_pool`
yields `None`, and every inventory-backed read 503s. The welcome picker's whole job is
writing that one `url` value (docker / BYO / managed per NOW), then re-running the gate —
re-entrant, per the startup model. **No settings-write API route exists today**; the picker
needs one (small: read + patch `[database].url` via the existing atomic-write helpers).

### B. Frontend vocabulary (what the screen must reuse)

**B0. The fork is already decided by the constraints.** Canvas and inspector are separate
visual systems with import-boundary tests in both directions
(`shell/src/testSupport/importGraphBoundary.test.ts`, `depLint.test.ts`) and a CI gate that
fails any Tailwind utility class inside canvas (`canvasTailwindFree.test.ts`). The desktop
window only ever loads `/canvas` (`desktop/src/window.ts::rendererUrlForPort`, allowed paths
`/` and `/canvas` only). A new user lands in canvas, so the screen is `@tm/canvas`: BEM CSS
on the `tokens.css` custom properties, Ark UI, co-located `.css` imported by its component
(enforced by `cssColocation.test.ts`), classes like `.canvas-firstrun__*`.

**B1. Card shell:** `viewers/placeholder/paneState.tsx::PaneStateFrame` /
`ResourcePaneStateView` — discriminated status → tone (`default | busy | error`), skeleton
loading body, and a guaranteed actions bar ("errors keep an action so the pane never
collapses into a generic toast" — exactly NOW's "every state carries an action that fixes
it"). CSS `.canvas-resource-pane__*` in `placeholder-pane.css`.

**B2. State→label maps:** `workbench/chrome/RunVitalsStrip.tsx::STATUS_LABELS`
(11 activity states → labels, `data-status` attr, `--needs-you` modifier) and
`viewers/placeholder/provenance.tsx` ("Text, never color alone" — the house a11y rule).
Semantic colors from `tokens.css`: sage=good, rose=error, amber=caution, sky=info.

**B3. Check-list pattern:** no pass/fail check-list component exists anywhere. The
established "N states → list rows" idiom is the launcher's
`commandRows.ts::asyncStatusRows` + `deriveFetchStatus` over
`commandTypes.ts::FetchStatus` (`loading | error | empty | populated`) with a retry row.
The gate list should mirror this row contract rather than invent a checklist widget.

**B4. Data fetching:** TanStack Query over `@tm/core`'s `transport.ts::requestApiJson`
(swappable transport via `createApiTransport`/`setApiTransport` — how the desktop and tests
retarget the base URL). The exact hook template is `launcher/useRuntimeTemplates.ts`: thin
`fetchX` → `useQuery` → collapse to `{ data, FetchStatus, retry }`. Types are hand-written
mirrors under `www/packages/core/src/types/*` with a header naming the Python model
(`exclude_none=True` ⇒ optionals absent, not null; snake_case kept verbatim).
`types/capabilities.ts::fetchCapabilities` exists with no hook; `/v1/harnesses` and any
doctor route need new mirror types + hooks in the same shape.

**B5. Mount point:** `workbench/SessionCanvasRoute.tsx` already owns route-level alerts and
hydration status; the gate branches there, above `CanvasWorkbench`, so `@tm/shell` stays
UI-free and `src/index.ts`'s export surface grows by at most one component. The settings-row
vocabulary for picker rows is `commandRows.ts::buildSettingsRows`' title/subtitle/trailing
triple. Any persisted "seen" flag goes through
`infrastructure/persistence/storageKeys.ts` (asserted by `storageKeys.test.ts`).

### C. Where a new user actually lands today (the gap the screen fills)

**C1.** Electron main (`desktop/src/main.ts::registerDesktopLifecycleFromEnv`) resolves a
backend (bundled standalone / attach-to-live / managed), health-gates `/health` for both
backend and gateway (`desktop/src/backendHealth.ts::waitForBackendHealth`, 15 s), and only
then opens the window on `/canvas`. On failure: a native `dialog.showErrorBox` and
`app.quit()` — the user never sees a window.

**C2.** Inside the window a fresh install renders: ambient backdrop, zero panes (no
zero-pane empty state exists in `CanvasPaneLayer`), the 6.5-second `FirstRunHint` ⌘K chip —
and then the actual first-run experience: with an empty store,
`packages/space/src/domain/actingContext.ts::resolveWorkdirCandidate` returns
`worktree_not_found`, which `SessionCanvasRoute::actingContextErrorMessage` renders as
**"The Worktree for this Canvas no longer exists."** with no retry. A brand-new user is told
a worktree they never had is gone. The escape hatch (⌘K → Workdir → "Create new space") is
undiscoverable; the CLI equivalent (`cli/space_bootstrap.py::bootstrap_cli_space`) is wired
into `start_cmd.py`/`codex_cmd.py` but not the desktop launch.

**C3.** The renderer performs zero health checks; there is no ErrorBoundary anywhere in
`www/packages`. A backend that dies after the window opens degrades to per-domain
"Couldn't load…" rows inside the palette. In-window backend-down UI is out of 1.4's scope
but is the standing boundary to name: the screen can gate everything except "the API is not
answering", which only Electron main (or a future renderer liveness signal) can own.

---

## Quality Map

**Q1. `run_doctor` is wrong-shaped for its next consumer — refactor before adding.**
~218-line function, checks inline, results existing only as terminal output. Already past
the repo's 150-line budget, and CLAUDE.md says refactor before new code. Disposition:
decompose into check functions returning one structured model (id, status ok/warn/fail,
label, detail, structured remedy code per NOW 1.2 "the error carries a structured code, not
a sentence to retype"); CLI renders it, a new route serves it. One list, two renderers —
the same "one predicate, many readers" move the area keeps paying for (slice 1).

**Q2. False first-run error message (C2).** Empty inventory surfaces as
`worktree_not_found` → "no longer exists" phrasing. Disposition: the slice-1 gate mounts
before this path and owns the empty-store state; the misleading copy for the genuinely-empty
case dissolves rather than being patched in place.

**Q3. `readinessLabel` is module-private** in `launcher/templateRows.ts`, consumed only by
`agentSpawnRows`; readiness has no visual treatment anywhere (label folded into a subtitle
string; the only structural signal is `CommandRow.disabled`). Disposition: lift the
state→label map to a shared canvas module when the cards adopt the readiness vocabulary
(slice 1), leaving `templateRows.ts` a consumer.

**Q4. `FirstRunHint.tsx` writes `localStorage` inline** (`"tm.launcher.hintSeen"`),
bypassing the `storageKeys.ts` registry its own test suite asserts against. Disposition:
groom-as-you-touch in slice 1 (the slice is in this exact area); one-line move.

**Q5. Desktop launch skips space bootstrap.** `bootstrap_cli_space` runs for CLI launches
only; the desktop's empty-inventory dead end (C2) is the consequence. Disposition: decision
for the owner in slice 2 — either the gate's "all green" transition bootstraps a default
space (mirroring the CLI) or first-run guides the user through creating one. Do not build
both.

**Q6. Query-key drift:** `core/src/queryKeys.ts` exists but launcher hooks inline literal
keys (`["agents"]`, `["spaces"]`). Disposition: new hooks register their keys in
`queryKeys.ts`; do not chase the existing literals in this slice.

**Q7. Deliberate non-findings** (mapped, correct as-is): doctor probes live
`detect_harnesses()` while inventory reads stored evidence — intentional split; the screen
reads stored inventory only (inventory docstring, invariant 6). `/health` staying a dumb
liveness probe is correct; the gate belongs on its own surface.
`capture_rpc_routes.py::prepare_capture` hardcoding the Claude error code is already named
in NOW 1.2 / PR#352's scope — not re-reported here.

---

## Plan

Three slices, each demoable on the owner's Mac, smallest first. Frontend slices touch
`www/packages`, so per the structural-PR rule the full `pnpm --filter @tm/shell test` suite
runs alongside the repo gates. Gates for every slice, verbatim: `just check` and
`just test-affected` (builder loop), full `just check` + `just test` pre-merge.

### Slice 1 — the screen reads what already exists (smallest demoable)

One vertical slice, two seams, no new machinery:

1. **Backend:** refactor `run_doctor` checks into structured check functions (Q1) returning
   a frozen model; `run_doctor` becomes the CLI renderer (behavior pinned by existing doctor
   tests). New `GET /v1/doctor` in the `api/v1/harnesses.py` registration style serving the
   same list. Store-less boot already makes it serveable on a fresh install (A5). Re-scope
   the python/port checks for the HTTP context (A2).
2. **Frontend (@tm/canvas):** first-run gate component mounted in `SessionCanvasRoute`
   above `CanvasWorkbench` (B5). Renders (a) the doctor check list via the
   `asyncStatusRows`/`FetchStatus` row idiom (B3) and (b) per-harness cards from
   `GET /v1/harnesses` via a new `useHarnessInventory` hook in the `useRuntimeTemplates`
   shape with hand-written mirror types (B4), card shell per `PaneStateFrame` (B1),
   readiness vocabulary per A3, auth shown as probe evidence marked diagnostic until #352
   (A4). All green → straight to the workbench; anything failing → the screen. Re-entrant
   by construction: it is a render branch, not a wizard. Q3 and Q4 land here as
   groom-as-you-touch.

   Demo: fresh channel home + stopped Postgres → open the app → gate list shows the session
   store failing with the classified reason, cards show claude/codex installed state;
   start Postgres, retry, land in the workbench.

   Tests: doctor-model unit tests (each check → structured result), route test (store-less
   app serves the list), hook + gate render tests asserting the user-observable branch
   (screen vs workbench) per the test-observable rule; pin the fresh-install path renders
   the gate, not the `worktree_not_found` alert (Q2).

### Slice 2 — the DB gate acts: store picker

The welcome screen's first check gets its action (NOW: "every state carries an action that
fixes it"). A settings-write surface (read + patch `[database].url` in the channel-home
`settings.toml` via the existing atomic-write helpers, `PUT /v1/settings/database` or
similar), picker UI offering docker / BYO connection string (managed deferred until hosting
exists), validation by attempting the connection and rendering `_session_store_failure`'s
classified reasons (A5), then gate re-run. Owner decision Q5 (auto-bootstrap space vs guided
creation) belongs to this slice's "past the gate" moment. Tests: settings write round-trip
against a temp channel home; picker → gate-green transition after pointing at a live
Postgres; the BYO path never logs or echoes the URL's password (doctor already redacts —
keep the property).

### Slice 3 — fix actions on the cards: login driver + pre-launch readiness

1.3's one driver: spawn the harness's own login against the right home, PTY bridged to the
existing xterm pane machinery, fallback URL surfaced, exit → predicate re-read → card goes
green. Plus 1.5: `credential_unavailable` as a new `RuntimeTemplateReadiness` reason fed by
the #352 predicate, `readinessLabel`'s lifted map (Q3) gaining its label. This slice depends
on #352 being merged; it is the seam consumer, not the seam.

**Sequencing note:** slice 1 has no dependency on #352 and can start immediately; slice 3
is blocked on it; slice 2 is independent of both.
