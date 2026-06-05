# tm-firstrun-scout-1b — the doctor gate (slice 1b)

Scouted at main `329e3ef0`, read-only. Governing: NOW.md Phase 1 (startup model, 1.4),
docs/ARCHITECTURE.md (boundary enforcement standard, two plane rule), prior scout
`~/.mdx/projects/tm-firstrun-scout.md` (slice boundaries kept, not redone), grok's flag sweep
`~/.mdx/projects/tm-1b-firstrun-refs.md` (reconciled, §E). Quality lens: `code-hygiene`
inspection mode over the doctor/credential files; `/code-review` remains user-invocable only in
this session (same as the prior scout's session), so its reuse lens was applied by hand.
Citations are file plus symbol throughout.

---

## Q1 — the launch gate does NOT precede the mint; the diagnostic is what lies

**Answer: No. The Claude launch path never evaluates `harness_credential_error` before the
mint, and a fresh fleet home CAN launch.** The doctor's warn is a diagnostic-only false
positive whose message misattributes a not-yet-minted artifact to a mint failure.

**The launch path, owner by owner.** `cli/start_cmd.py` builds a `CapturedRunRequest`;
`captured/context.py::_prepare_home_and_grant` calls `cli/runtime_home.py::plan_runtime_home`
with `use_runtime_overlay = write and prepared.client_path is not None`, so every writing
Claude launch takes the overlay. `cli/runtime_home.py::prepare_runtime_home` then dispatches to
`cli/home_overlay.py::materialize_runtime_home_overlay` (or the template variant), which calls
`cli/credential_source.py::resolve_credential_path`. For a `KeychainCredentialSource` that is
`_mint_claude_credential`: it checks only `claude_fleet_auth.py::fleet_home_unavailable_reason`
(darwin plus `~/.claude-auth` exists), then `credential_broker.py::CredentialBroker.mint`, whose
`_write_shared_credential` creates `runtime-access/` itself
(`mkdir(mode=0o700, parents=True, exist_ok=True)`). The only launch-path appearance of
`harness_credential_error` is `prepare_runtime_home`'s NATIVE-mode-no-child-home branch, which
a writing Claude captured launch cannot reach (overlay always on); Codex reaches it via
`cli/codex_cmd.py` (`use_runtime_overlay=False`) with a `NativeCredentialSource`, where the
predicate is a correct file-existence check. The spawn boundary check
`cli/runner.py::assert_claude_client_credential_identity` runs after materialization, so it sees
the freshly minted artifact.

**Where the false warn comes from.** `cli/diagnose.py::_report_credential_readiness` calls
`harness_credential_error(source)` with the default `require_shared=True`, which for a keychain
source ends at `credential_broker.py::shared_access_credential_error` — a predicate over the
**mint's output artifact** (`runtime-access/.credentials.json`, its permissions, its contents).
On a bootstrapped-but-never-launched fleet home that returns "shared access credential directory
is missing", and `cli/credential_source.py::_keychain_credential_failure` wraps it as "could not
mint a Claude credential (…); launch aborted" — no mint was attempted and no launch was aborted.
Verified first-hand: `~/.claude-auth` holds only `.claude.json` and `backups/`.

**The fix seam already exists and is dark.** `harness_credential_error(require_shared=False)`
skips exactly the artifact demand (fleet home present, keychain owner credential readable —
the true pre-mint readiness). Zero callers pass it today (verified by sweep). Wiring the
diagnostic/readiness readers to `require_shared=False` for keychain sources, or introducing a
distinct "not yet minted" advisory state, resolves Q1 without touching the launch path.

## Q2 — run_doctor's inventory, and what the /v1/harnesses emitter already owns

**Nothing in `run_doctor` is a structured value.** Every check renders inline through the
`_ok`/`_fail` closures or bare `typer.secho`; the only structure is `failures: list[str]`
(labels appended by `_fail`). Check inventory at main, with HTTP re-scope notes:

| Check | Today | Over HTTP |
|---|---|---|
| python ≥3.12 | `_ok`/`_fail` | trivially true if the API answers; serve as info/version |
| mitmdump (`cli/launch_runtime.py::resolve_mitmdump_executable`) | `_ok`/`_fail` | gate check |
| packaged addon | `_ok`/`_fail` | gate check |
| node (`gateway_supervisor.resolve_node_binary`) | `_ok` / inline warn | gate check (warn) |
| gateway entry (`gateway_supervisor.resolve_gateway_entry`) | `_ok`/`_fail`/inline warn | gate check |
| web bundle | `_ok` / inline warn | gate check (warn) |
| harnesses (`capabilities.detect_harnesses` live loop) | `_ok` / inline warn | **omit** — stage 2 per NOW; the screen already reads stored evidence from `GET /v1/harnesses` |
| storage write probe | `_ok`/`_fail` | gate check |
| proxy/web default ports (`cli/net.port_in_use`) | `_ok` / inline warn | re-scope: describes defaults the running server already bound past |
| session store (`config.resolve_database_url` → `session/migrate.current_revision` vs `migration_head`) | `_ok`/`_fail` ×3 shapes | **the gate's first call**; `_session_store_failure`'s classifier and `config.database_url_guidance` are the reusable detail/remedy strings |
| credential readiness (`_report_credential_readiness`) | `_ok` / inline warn | **omit from the gate** — harness availability, stage 2; see Q4 |
| runs health (`report_runs_health`) | echo lines, interactive reap | CLI-only: interactive, and self-referential over HTTP |

To become serializable values, each check needs extraction into a function returning one frozen
model (id, severity, label, detail, structured remedy code — `CredentialErrorCode` in
`credential_broker.py` is the precedent for code-shaped remedies), with `run_doctor` reduced to
a renderer. The repo already demands this: `run_doctor` is ~205 lines against the 150 budget
(Quality Map §Q-1).

**What the inventory emitter owns that a doctor emitter must reuse, not parallel:** harness
installed/version/auth evidence is already served by `api/v1/harnesses.py::get_harnesses` over
`harnesses/inventory.py::harness_inventory` (installation group from
`probes/observation.py::build_harness_observation` rows, connections group), consumed by
`firstrun/useHarnessInventory.ts` and `firstrun/harnessCards.ts`. NOW's startup model makes the
split explicit: the gate is "is TM operational", harness availability is a separate concern past
the gate. So `GET /v1/doctor` should carry **no harness rows at all** — which also keeps its
dependency set free of `cli/` and of the session pool. Registration style to copy:
`api/v1/harnesses.py` (router registered directly at `/v1` by `main.create_app`; the doctor route
must serve store-less, unlike inventory's one 503 `inventory_unavailable`). Frontend patterns to
copy verbatim: mirror types under `www/packages/core/src/types/` with the Python-model header,
fetcher in `core/src/transport.ts`, key in `core/src/queryKeys.ts`, hook in the
`useHarnessInventory` shape collapsing to `fetchStatus.ts::FetchStatus`. Vocabulary pinned from
both planes like `shared/harness_inventory_vocabulary_v1.json`
(`harnesses/test_inventory_vocabulary.py` + `core/src/types/harnessInventory.test.ts`).

## Q3 — severity has no owner; the shape that makes the bug unrepresentable

**Owner today: the callsite's choice of closure.** `_fail` is the only writer of `failures`;
warn is six independent bare `typer.secho(fg=YELLOW)` sites (node, gateway, web bundle, missing
harness, ports, credential) with no accumulator, no shared helper, and no trace in the final
verdict. `run_doctor`'s tail reads only `failures`, so "all checks passed" prints over any
number of outstanding warns — structural, confirmed in source, observed live today. Even
`_report_credential_readiness` is half-injected: it receives the `_ok` closure but calls
`typer.secho` directly for its warn path.

**Shape a structured result needs:** severity (`ok | warn | fail`) as a field on each returned
check value, with the aggregate verdict a worst-of fold over the returned list — never a
side-effect accumulator a check can bypass. CLI maps fail→exit 1 (current contract, pinned by
existing doctor tests); the first-run gate maps fail→hold, warn→surface-with-action. This is the
ARCHITECTURE.md boundary standard applied to severity: enforced once where the values are
produced, inherited by every renderer nobody has written yet.

## Q4 — the Authenticated row and the 1.2 predicate: projection or own surface, not a field on the stored join

**Owners.** The row: `firstrun/harnessCards.ts::authenticatedFact`, today rendering
`ConnectionDiagnosticsInfo` probe evidence, its docstring already naming "the credential
predicate that will feed this fact directly" as the successor. The predicate:
`cli/credential_source.py::resolve_harness_credential_source` + `harness_credential_error`.

**Direct binding into `HarnessInventoryItem` is blocked by three facts.** (1)
`harnesses/inventory.py::harness_inventory`'s own invariant: one stored snapshot, no live
detection mixed in — the predicate is a live filesystem/keychain check. (2) The API plane
imports no `cli/` module today (verified sweep); the predicate lives under `cli/` and pulls
`cli/home_seeders.resolve_source_home_dir` and `cli/home_constants`. (3) The keychain arm shells
`security(1)` (`credential_broker.py::SecurityOwnerCredentialStore.read`, 2s timeout) — a sync
subprocess that `firstrun/useHarnessInventory.ts`'s 3-second poll would re-run per tick if it
lived on the polled route. Plus the Q1 trap: any binding using `require_shared=True` reports a
fresh fleet home as unavailable.

**The two viable bindings, owner named:** (a) **own live surface** — the predicate evaluated
(off-thread, `require_shared=False` for keychain) on the gate's plane, e.g. beside `/v1/doctor`;
freshness is per-request, which is what 1.3's "login exits → predicate re-read → card goes
green" needs. (b) **projection** — `harnesses/state_refresh.py::refresh_harness_state` writes a
credential observation row the inventory serves like any stored evidence; keeps the join's
invariant but couples freshness to refresh triggers. Either way the frontend change is a
field-source swap inside `authenticatedFact`, not a card redesign (prior scout §A4 holds).
NOW sequences this after 1b ("then the Authenticated row reads 1.2's predicate"), so 1b only
needs the decision recorded, not the build (§Plan D2).

## Q5 — `?firstrun=1` blast radius: reconciled with grok, one cut

Grok's enumeration (`~/.mdx/projects/tm-1b-firstrun-refs.md`) is confirmed by my independent
sweep; no conflicts, nothing missed on either side. Strict flag machinery is 11 rows in three
files: `route.ts::isFirstRunCanvas` (+ shared `hasCanvasFlag`), `SessionCanvasRoute.tsx` (the
import, the `firstRun` memo, four effect guards — activity stream, adoption reconciler,
transcript spawn, captured-run prune — and the render branch), and the single producer test in
`SessionCanvasRoute.test.tsx`. No production producer, no persistence, no e2e path, no backend
reader. Retirement is one cut: the gate verdict replaces `firstRun` as the branch condition, the
four effect guards keep their containment semantics under the new condition (the containment
comment in `SessionCanvasRoute.tsx` says 1b inherits it), the flag test is replaced by
gate-vs-workbench branch tests. `route.test.ts` never covered `isFirstRunCanvas` (grok's find) —
moot once deleted. `FirstRunHint` and its storage keys are a name collision, untouched.

---

## Quality Map

- **Q-1 (groom first, in-slice).** `cli/diagnose.py::run_doctor` ~205 LOC against the 150
  budget, checks inline, results print-only. The 1b refactor IS the groom: model + per-check
  functions + renderer. Existing doctor tests pin the CLI rendering behavior.
- **Q-2 (dissolves with Q-1).** Warn rendering duplicated across six hand-rolled `typer.secho`
  sites with inconsistent hint shapes; no `_warn` counterpart to `_ok`/`_fail` — that asymmetry
  is the Q3 bug's mechanism.
- **Q-3 (fix in-slice, one line of dispatch).** `_keychain_credential_failure` wording claims
  "could not mint … launch aborted" for a state where no mint ran; paired with
  `require_shared=True` it turns "not yet minted" into a false failure (Q1).
- **Q-4 (decision, deferrable).** `cli/credential_source.py` is ARCHITECTURE.md's named
  credential-isolation boundary but is `cli/`-homed while 1.4/1.5 want it read from the API
  plane. Promote to a top-level leaf vs import `cli` from the api plane. Not needed for 1b if
  the gate excludes credential rows (D1); record, defer to the Authenticated-row slice.
- **Q-5 (watch).** `credential_broker.py` at 666 LOC nearing the 700 hard limit. 1b should add
  nothing there; next writer refactors first.
- **Q-6 (dark seam, wire not delete).** `require_shared=False` has zero callers.
- **Non-findings upheld:** doctor probing live while inventory reads stored is the intentional
  split (inventory invariant 6); `/health` staying a dumb liveness probe is correct; prior
  scout's Q2/Q4 frontend grooms (worktree_not_found copy, FirstRunHint storage key) remain
  valid targets inside this slice's area.

## Plan

**Decisions needed (surface-and-decide before build):**

- **D1 — gate scope over HTTP.** `GET /v1/doctor` carries TM-operational checks only
  (version-info, mitmdump, addon, node, gateway, web bundle, storage, session store); harness
  and credential rows stay on their own surfaces. Recommended: yes — it matches NOW's two-stage
  order and keeps the doctor emitter free of `cli/` imports and the session pool.
- **D2 — predicate home** (Quality Map Q-4). Record now, build with the Authenticated-row
  slice.
- **D3 — fix the false fleet-credential warn in-slice.** Keychain readiness reads
  `require_shared=False` (or a distinct "not yet minted" advisory). Recommended: in-slice — it
  is Q1's product truth, one dispatch change plus one test, in the exact files 1b touches.

**Ordered steps, bound to the reuse map:**

1. Extract the structured check model and per-check functions into a new non-`cli` module
   (imports today are already all non-`cli`: `config`, `gateway_supervisor`,
   `session.migrate`, `capabilities`), severity per Q3's worst-of shape;
   `cli/diagnose.py::run_doctor` becomes the CLI renderer (exit-1-on-fail pinned by existing
   tests; warn summary line replaces silent swallow). Credential readiness stays CLI-side
   (D1) with D3's dispatch fix.
2. `GET /v1/doctor` in the `api/v1/harnesses.py` registration style, store-less serve; status
   vocabulary pinned two-plane per `shared/harness_inventory_vocabulary_v1.json` precedent.
3. Frontend: mirror types + fetcher + `queryKeys.ts` entry + hook in the
   `useHarnessInventory` shape; gate list rendered in `FirstRunScreen` above the harness
   cards via the `FetchStatus` row idiom.
4. Retire `?firstrun=1` per Q5's one cut: gate verdict replaces `firstRun` in
   `SessionCanvasRoute.tsx`, effect-guard containment preserved under the new condition.

**Tests and gates.** Per-check unit tests (each check returns a value); the Q3 pin written to
fail before the fix: an aggregate over `[ok, warn]` must not report all-passed (test-observable
rule). Route test: store-less app serves the gate list while inventory 503s. D3 regression: a
fleet home with an owner credential and no `runtime-access/` reports ready (or "not yet
minted"), never failure. Frontend: gate-vs-workbench branch tests replacing the flag test;
fresh-install path renders the gate, not the `worktree_not_found` alert (prior scout Q2).
Structural rule applies (route composition changes): full `pnpm --filter @tm/shell test`.
Gates verbatim: `just check` + `just test-affected` inner loop; full `just check` + `just test`
pre-merge; CI is the verdict.

---

# Operational readiness, live

Appended at main `0913b3bf` (after `d2635ec1` wrote the cli-adapter rule and ratchet into
docs/ARCHITECTURE.md). Reframe under diagnosis: "is desktop/canvas operational, live, on launch
and continuously; nuked `~/.claude-auth` is detected and offered re-auth." Diagnosis only.

**Verdict on the doctor-gate hypothesis: wrong-shaped as the mechanism, half-right as a
surface.** A GET snapshot can carry the launch-time repair menu (the session store, the
bundles, the binaries) but cannot satisfy "continuously" by construction, and the restated
requirement's hard case — credential death after launch — is invisible to any snapshot the
user is not currently looking at. What replaces it is not new machinery: every spawn failure
already reaches the canvas as a typed error with a structured code (Q2), a per-run liveness
poll already exists (`CaptureHealthMonitor`), and a live SSE spine canvas already subscribes
to exists with a runtime-readiness event seam already flowing through it (Q4). The shape the
requirement forces is a readiness snapshot plus change events on that existing spine; the
run_doctor check list is an input to the snapshot, not the mechanism. (Payloads and routes
deliberately not designed here.)

## Q1 — what "canvas is operational" decomposes into

Conditions for a canvas run to spawn, owner by owner (the real path:
`POST /runs` → `RunManager.createNew` → `capturePort.prepareCapture` →
`api/v1/capture_rpc_routes.py::prepare_capture` → `captured/context.py::prepare_captured_run`):

| # | Condition | Owning symbols |
|---|---|---|
| S1 | Python backend answering (the plane itself) | `desktop/src/backendHealth.ts::waitForBackendHealth` gates `/health` at desktop launch; nothing re-checks after |
| S2 | Node + gateway present and running (the `/runs` surface) | `gateway_supervisor.resolve_node_binary` / `resolve_gateway_entry`; run routes 503 without it |
| S3 | Session store configured, reachable, migrated | `CaptureSessionStoreUnavailable` at the RPC; CLI twin `cli/launch_runtime.py::preflight_session_store_or_exit` |
| S4 | Harness installed + enabled (gates) | `HarnessEnablementRejected` (`gate_enablement=write` in `captured/context.py`) |
| S5 | Client binary resolvable | `cli/launch_runtime.py::resolve_client_binary` |
| S6 | mitmdump resolvable | `cli/launch_runtime.py::resolve_mitmdump_executable` |
| S7 | Port pair allocatable, proxy binds | `cli/ports.py::allocate_port_pair`, retry policy `cli/bind_failure.py`, `CapturedRunBindConflict` |
| S8 | Proxy spawns and reaches readiness | `cli/runner.py::start_prepared_proxy`, `CapturedRunProxyStartTimeout` |
| S9 | Credential resolvable or mintable | `cli/credential_source.py::resolve_credential_path` → `CredentialBrokerError` with `CredentialErrorCode` |
| S10 | Workspace/canvas identity resolves | `capture_rpc_routes.py::_resolved_domain_request` (`canvas_affinity_required`, `workspace_identity_mismatch`) |
| S11 | Control-plane grant prepared | `ControlPlaneGrantPreparationError` |
| S12 | Per-run storage root writable, PTY spawnable | run-root creation in `captured/context.py`; `ptyPort.spawn` (node-pty) via `RunManager` |

Conditions for it to KEEP running: python backend stays up (runs are process-resident; an API
restart orphans capture), the proxy sidecar stays alive (polled — see Q2), the node gateway
process stays up (it owns the PTYs), the session store stays up (history stops, run survives),
and the credential artifact stays valid (nothing watches it — Q3).

**Divergence from run_doctor, the valuable part.** Doctor checks irrelevant to canvas
operability: the python version (moot if the API answers), the default proxy/web port checks
(canvas launches allocate dynamically via `allocate_port_pair`; the defaults are CLI-launch
concerns), and the runs sweep (hygiene, not operability). Real conditions run_doctor never
checks: **the canvas bundle** — doctor probes `files("transport_matters")/"www"/index.html`,
which is the *inspector* bundle; the bundle the desktop actually loads
(`api/src/transport_matters/canvas/`, per the WWW section of CLAUDE.md) is checked nowhere —
plus enablement intent (S4), proxy actual bind/readiness (S7/S8; doctor checks binary presence
only), workspace identity rows (S10), control-plane grant (S11), PTY spawnability (S12), its
credential check exists but is wrong (`require_shared=True`, §Q1 above), and the entire
keep-running dimension.

## Q2 — what is verified at spawn, and how failures surface

Everything in S3–S11 is verified at spawn today and surfaces **typed**:
`prepare_capture` maps each to an HTTP status plus structured code — enablement 409
(`harness_not_installed`, `harness_disabled`) or 503, `CredentialBrokerError` 503 carrying
`exc.code` (`claude_fleet_credential_unavailable` / `claude_credential_unavailable` /
`codex_credential_unavailable`), `session_store_unavailable` 503, `bind_conflict` 409,
`proxy_start_timeout` 503, `workspace_identity_mismatch` 409, `control_plane_grant_failed`
503. `RunManager.createNew` wraps any of these as
`RunManagerError("launch_failed", …, {upstreamStatus, upstreamCode})`, so the canvas spawn
caller receives the harness-correct code in the spawn response. **A spawn failure is a typed
response, not an event**; nothing re-broadcasts it on a stream.

After spawn, exactly one failure class is watched: `CaptureHealthMonitor` (3s sequential poll
per run, `DEFAULT_CAPTURE_HEALTH_POLL_MS`, threshold 3) degrades the run on a dead proxy
(`alive: false`) or gone lease → `settleRun(capture-lost)` → run view `FAILED` and every
terminal WebSocket closes with typed reason `capture_lost`. Every other post-spawn failure —
including the harness's own auth errors — reaches the pane only as **terminal bytes** the
harness happens to print. The wire plane observes provider 401s but nothing classifies them
(searched `401|unauthorized|auth_fail` across `addon.py`, `wire_store_observer.py`,
`session/` — one comment in `session/dao_statements.py`, zero classifiers).

## Q3 — the nuke, concretely

**Already-running run:** the overlay's `.credentials.json` symlink
(`cli/home_overlay.py::_link_overlay_credential_file` → `CredentialBroker.shared_credential_path`)
now dangles. TM does not react: nothing watches the fleet home, the artifact, or the keychain
— **none found**; searches: `watchfiles|watchdog|inotify|fsevents|chokidar|fs\.watch|watchFile`
across `api/src`, `packages`, `www/packages`, `desktop/src` (hits only the poll-driven
transcript tailer `index/tailer.py` and `self_reap.py`, neither touching credentials), plus the
Q2 sweep showing `CaptureHealthMonitor` polls proxy liveness only. The harness keeps working on
its in-memory access token (minted with a ≥1h validity floor, `_MINTED_CREDENTIAL_MIN_TTL`)
until expiry; what happens then is the harness's own behaviour (it watches the credential
file's mtime per NOW §1.1), surfacing as terminal bytes and unclassified wire 401s. TM's first
structured knowledge of the nuke is the **next spawn**: `_mint_claude_credential` →
`fleet_home_unavailable_reason` returns "~/.claude-auth does not exist" → `CredentialBrokerError`
code `claude_fleet_credential_unavailable` → `prepare_capture` 503 → `launch_failed` with that
upstreamCode in the canvas spawn response.

One load-bearing fact for re-auth costing: the keychain entry survives the nuke.
`SecurityOwnerCredentialStore` derives its service name from the sha256 of the config-dir
*path*, which is unchanged, so after the directory marker is restored the broker can mint again
without a browser login; the deleted directory (and its `.claude.json`) is the only lost
precondition the broker itself checks.

## Q4 — live signal machinery that already exists

| Channel | Producer | Canvas subscriber today? |
|---|---|---|
| Workspace activity SSE | `packages/activity/src/server/activityRouter.ts`, fed by runtime lifecycle facts and session records off the Postgres NOTIFY backbone | **Yes** — `useWorkspaceActivityStream.ts` (snapshot-on-connect, 1s auto-reconnect); note it is workspace-scoped and deliberately disabled on the first-run branch of `SessionCanvasRoute` |
| Runtime readiness events | `RunManager.subscribeReadiness` → `activityRouter.ts::subscribeReadiness` (`ActivityRuntimeReadinessEvent`) | Indirectly, via the activity stream — an existing runtime→activity readiness event path |
| Terminal WebSocket | `packages/runtime/src/server/runTerminalConnection.ts`, `TerminalFanout` (typed close reasons incl. `capture_lost`) | **Yes** — every xterm pane |
| Session event SSE | `api/v1/stream.py` / `session_routes.py` | Yes — `useSessionEventStream.ts` |
| Postgres NOTIFY `tm_events` | `session/listen.py::NOTIFY_CHANNEL`; writers `session/writer.py` (pg_notify) and `controlplane/delivery_store.py` | Not directly; it is the backbone under the SSE surfaces |
| `state_refresh` | `harnesses/state_refresh.py::refresh_harness_state`, fire-and-forget at startup | No live signal; frontend compensates with the 3s inventory poll |

So the Q4 answer is **yes**: a live spine canvas already subscribes to exists (activity SSE),
and a readiness-shaped event path through it already exists. The ARCHITECTURE ratchet's
reuse-if-one-exists therefore applies; "live" here does not need a new spine. (Memory rule
also applies: the signal must be genuinely streaming — this one is; the inventory poll is not.)

## Q5 — detection mechanism comparison, with recommendation

- **Event-driven on the operation that fails**: exact, zero idle cost, and mostly built —
  spawn failures are already typed with the credential code (Q2); the per-run health monitor is
  the precedent for the one post-spawn watch that exists. What is missing is only propagation:
  a spawn-time credential failure dies in one spawn response instead of updating any readiness
  state others can see.
- **Filesystem watcher on the fleet home**: no watcher machinery exists anywhere in the repo
  (Q3 searches); the tailer is deliberately poll-driven. A watcher would be new machinery
  guarding state that only launch actually consumes, and it cannot see keychain death anyway —
  the artifact can be intact while the keychain entry is gone.
- **Polling a health surface**: precedents exist (capture health 3s, inventory poll 3s,
  `waitForBackendHealth`), but the keychain arm of the credential predicate shells
  `security(1)` per evaluation, so an idle-time poll pays a subprocess forever to detect an
  event that almost never happens.

**Recommendation: event-driven on the failing operation, delivered over the existing activity
spine, with the snapshot evaluated once at startup.** The startup evaluation rides the same
place `state_refresh` already runs (`main.py::_start_session_backed_services`' background
task), so desktop launch gains no felt latency — the desktop already waits only on `/health`.

## Q6 — the re-auth seam

Nothing drives a login from inside the product today — searches `auth login|login_command|
bootstrap_command` across `api/`, `packages/`, `www/packages` return zero non-cli hits; 1.3 is
unbuilt. What exists is exactly the seam detection would hand it: the structured
`CredentialErrorCode`, plus `NativeCredentialSource.login_command` and
`KeychainCredentialSource.bootstrap_command` (`CLAUDE_FLEET_BOOTSTRAP_COMMAND` =
`CLAUDE_CONFIG_DIR=~/.claude-auth claude auth login`) with the target home on the same object.
The execution substrate is the run machinery itself: `RunManager` spawns arbitrary argv+env on
a PTY with terminal fanout to an xterm pane — the exact shape 1.3's driver needs. Detection
hands re-auth `(harness, error code, command, home)`; everything is already on one dataclass.

## Prior dispositions invalidated or amended by this reframe

- Disposition 1 (gate scope): stands for the snapshot's content, but the snapshot alone no
  longer defines the slice; the live delivery path is the center.
- Disposition 4 ("the refactor is the slice"): amended — the run_doctor extraction is now an
  input to the readiness snapshot, not the slice's definition.
- My earlier "lift or import in place" for `resolve_mitmdump_executable` and `port_in_use`:
  invalidated by `d2635ec1` — the ratchet forbids binding a new consumer to a displaced cli
  module, so anything this slice reads from `cli/` moves out, paid for by this slice.
- Disposition 7 (CLI warn count): unaffected but no longer 1b-critical.
