# Scout: harness-auth reshape — in-stream login-request detection

Mode 1 read-only scout, 2026-07-17, tree at `main` @ `506e0409`. All citations
are file + symbol. Verdict up front: **the S2d drift seams do not bind directly,
but the surrounding infrastructure binds almost everywhere else.** The genuinely
live wire observation points already exist (`LiveStatusObserver` taps), the live
event channel to the UI already exists (`tm_events` → `SessionEventHub` → SSE)
and is deliberately extensible, and attach-by-run-id already exists as the
resolve affordance. The two real gaps: a PTY-side observation point for
harness-printed login demands (gateway-side, one new hook mirroring an existing
adapter), and any persistence for the per-harness enablement toggle (none
exists, client or server).

---

## Reuse Map

### 1. S2d drift emitter and its four seams — do NOT ride them; mirror the idiom

`harnesses/blocks_store.py :: emit_drift_evidence` + `harnesses/drift_emitter.py
:: DriftEmitter` is a best-effort scheduler (dedup via `drift_evidence_id`
UUIDv5 + `_seen`/`_in_flight`, `submit`/`submit_from_thread`, never blocks the
hot path). The transport idiom is excellent and worth mirroring. The seams
themselves do not bind for login detection, for three structural reasons:

- **Drift-typed end to end.** Every seam terminates in a drift constructor
  (`blocks.py :: wire_parse_drift / transcript_reader_drift /
  session_bootstrap_drift / actuation_drift`); `DriftEvidence` validators
  reject any `detail_code` outside `DRIFT_DETAILS_BY_KIND`, and the store
  writes only `harness_drift_evidence`. Riding them means either widening the
  drift vocabulary with non-drift semantics (wrong: auth demand is not contract
  drift) or a parallel model anyway.
- **Not live.** The wire seam (`drift_capture.py :: WireDriftObserver`) runs
  post-persist over tier-1 `ExchangeArtifacts` — the finalize plane. An
  auth-request surface promised as live must ride a streaming signal
  (established lesson: finalize-driven "live" states are not live).
- **No PTY view.** None of the four seams observes harness terminal/stderr
  output. Seams 3 and 4 are additionally documented gaps with no production
  caller minting their trigger (`capture_rpc.py :: record_session_rejection`
  docstring; `controlplane/prompt_models.py ::
  HARNESS_REJECTION_PROMPT_REASONS` comment).

What DOES bind from this area: the injection idioms. `controlplane/
drift_observer.py :: PromptDriftObserverPort` (Protocol, injected in `main.py`)
and the exchange-sink registration shape are the right patterns for injecting an
auth observer; note every existing port is single-slot, so a second observer on
the same point needs a fan-out wrapper, not a replacement.

### 2. Per-harness signal parsing — mirror `harnesses/probes/` and `live_status.py`

Two proven per-harness classifier shapes exist:

- **Probe adapters** (`harnesses/probes/__init__.py`): frozen
  `AuthenticationProbeAdapter` (command + pure `parse(ProbeCapture) →
  AuthenticationEvidence`), sealed vocabulary with `login_required` already a
  first-class `AuthenticationStatus`, redaction boundary (raw capture never
  leaves the runner; only status enums + fixed reason literals + sanitized
  digest persist). `probes/runner.py :: run_authentication_probe` is complete —
  bounded timeout, per-connection env isolation via `probe_environment` — and
  has **zero production callers**. This is exactly the machinery the
  "opportunistic probe on settings-open" decision needs; it wires, not builds.
- **Live wire classifiers** (`live_status.py :: AnthropicLiveClassifier /
  CodexLiveClassifier` over `_LiveClassifier`): per-run stateful classifiers fed
  streaming payloads, emitting deduped facts. This is the shape for an
  in-stream login-request classifier.

Raw auth-failure signal per harness:

- **codex, local probe**: `Not logged in` + exit 1, status line on **stderr**
  (`probes/codex.py :: _parse` scans both channels; certified against the real
  binary). Authenticated: `Logged in using <method>` + exit 0.
- **codex, in-stream**: ChatGPT rejects the websocket upgrade with 401/403 —
  already classified as `chatgpt_auth_rejected` in `codex/diagnostics.py ::
  build_codex_transport_diagnostics`, but from persisted artifacts (post-hoc).
  The live-plane equivalent of that signal is the upgrade response status the
  transport already records (`codex/transport.py`, `response_status_code`).
- **claude, local probe**: `claude auth status --json`, authoritative
  `loggedIn: false` (`probes/claude.py :: _parse`).
- **claude, in-stream**: HTTP 401 from `api.anthropic.com`. No classifier
  exists today; the only handling is generic `http_{status}` stop-reason
  tagging at finalize (`exchange_recorder_artifacts.py ::
  tag_http_error_status`). The live signal is `flow.response.status_code` at
  response-header time in `addon_handlers.py :: handle_response_headers` —
  available before any body bytes, genuinely live.
- **grok**: probe adapter is an r0 stub always returning `unknown`
  (`probes/grok.py`; real parser is S2h). The exit-code trap is encoded (`grok
  models` exits 0 in both auth states — parse output, never trust exit code).
  No grok wire capture exists yet (adapters registry is anthropic + codex
  only), so in-stream grok detection has no substrate until S2h.

### 3. RunManager and non-visible panes — capture runs detached; one clean hook point

`RunManager` is **gateway-side TypeScript** (`packages/runtime/src/service/
RunManager.ts`), not Python; Python fronts it via `api/v1/run_proxy.py`. The
PTY pump is the `session.onData` callback installed unconditionally in
`RunManager.register`: every chunk goes to (1) `run.inputAdapter.observe(data)`
(readiness classification), (2) `run.emulator.append` (bounded scrollback,
`TerminalEmulator`), (3) `run.fanout.append` (`TerminalFanout`, a no-op
broadcast over an empty attachment map when detached). **Output is consumed and
classified for the run's whole life regardless of viewers** — the hidden-pane
requirement is already satisfied at the capture layer.

The existing PTY classification hook to mirror is
`packages/runtime/src/service/HarnessPromptInputAdapter.ts` (per-harness
output inspection → `run.readyAt` + `subscribeReadiness` listeners). A
login-demand matcher is the same shape: per-harness pattern over PTY output,
firing a run-scoped event. One genuine design point: the gateway has no path to
the Python event plane today (readiness events are gateway-internal; durable run
lifecycle records are emitted Python-side). A PTY-detected auth demand needs a
gateway → API bridge (small REST callback, or piggyback on the existing
lifecycle write path) — flagged in the Plan.

### 4. Live event streaming — binds cleanly; one new payload type, no new channel

The channel exists and is built to extend: writer publishes `SELECT pg_notify`
on `tm_events` (`session/writer.py :: _notify` and the typed payload builders);
`session/listen.py :: SessionEventListener` LISTENs on one long-lived
connection and forwards into `session/listen.py :: SessionEventHub`; SSE
handlers in `api/v1/session_routes.py` (`stream_session_events`,
`stream_session_timeline`) and `api/v1/stream.py :: stream_run` replay durable
rows by seq then live-tail, with catch-up doorbells on reconnect. Adding an
auth-request event = one payload-type constant + one pydantic `*Signal` in
`session/notify_payloads.py` + a `parse_notify_payload` branch + a hub
subscriber set — the exact recipe `RUN_LIVE_STATUS_PAYLOAD_TYPE` and
`CONTROL_PLANE_DELIVERY_PAYLOAD_TYPE` already followed. Do not invent a second
channel; none is needed.

The wire-side write path to mirror is `live_status_observer.py ::
LiveStatusObserver`: installed once in `addon_runtime.py`, fed from exactly two
seams in `addon_handlers.py` (`handle_response_headers` chunk tap for Anthropic
HTTP; `handle_codex_websocket_message` for Codex WS payloads), latest-wins rows
via `SessionWriter.submit_run_live_status`, best-effort, never blocks the
proxy. An auth observer is a sibling of this observer at the same two call
sites — or, simpler for Anthropic, a status-code check at header time that
never needs the chunk tap at all.

### 5. Canvas attach-by-run-id — exists; it is the resolve affordance as-is

No "reattach" endpoint exists because reattach is the ordinary attach path
against a live run id: persisted `capturedRunStore.runs[runKey].runId`
(`www/packages/canvas/src/model/capturedRunStore.ts`, persisted precisely so
reload re-attaches instead of re-spawning) → `useCapturedRunBinding` →
`useTerminalSession` opens WS `/v1/runs/{runId}/terminal`
(`terminalSocket.ts :: runTerminalSocketUrl`, proxied by `api/v1/run_proxy.py`,
handled by `packages/runtime/src/server/runTerminalConnection.ts ::
handleRunTerminalConnection`) → `RunManager.attach` replays the emulator
snapshot (`run.terminal.ready` → snapshot bytes → `run.terminal.scrollback-end`)
then live-tails. `capturedRunStore.adoptRun` binds an externally-known runId to
a pane — the exact affordance an auth-request inbox needs for "attach this
hidden run".

One gap on this surface: **no toast/notification/inbox component or store
exists anywhere in `www/packages`** (searches: toast/Toaster/notification/
NotificationCenter/inbox/banner across canvas, inspector, shell, core, host).
The only precedents are inline `role="alert"` pane banners, and existing pane
states carry deliberate comments rejecting generic toasts
(`viewers/placeholder/paneState.tsx`, `viewers/resource/resourceState.ts`). A
global auth-request surface is greenfield UI and should be specced as a
distinct global surface so it does not erode that per-pane precedent.

### 6. Enablement — facts exist and are clean; the toggle has no home anywhere

- **exists**: `capabilities.py :: detect_harnesses` over the registry
  (`harnesses/__init__.py :: list_harness_descriptors`, `HarnessId`,
  `HarnessDescriptor`; grok has `launch=None`). REST: `api/v1/capabilities.py
  :: get_capabilities`. Single-path variant `observe_resolved_binary` is what
  the S2f gate reuses.
- **version-compatible**: `harnesses/compatibility.py :: match_release` (pure),
  consumed by `harnesses/resolver.py :: resolve_target / launch_options` and by
  the advisory gate `harnesses/compatibility_service.py ::
  gate_launch_preparation` at the single `prepare_launch` choke point.
- **user toggle**: none found, client or server. Backend `config.py ::
  TomlSettings` holds only `[database]`; no settings-like Postgres table in
  migrations 0001–0024; no preferences store. Frontend precedent for a user
  toggle is zustand-persist over localStorage
  (`www/packages/core/src/persistence.ts :: createFrontendPersistStorage`;
  `bypassPermissions` / `controlPlaneGrant` rows in
  `canvas/src/launcher/commandRows.ts :: buildSettingsRows`). Decision needed
  (Plan): a client-only localStorage toggle cannot gate backend launch
  eligibility for CLI/MCP launches, so the toggle likely needs a small
  server-side home; nothing exists to reuse.

---

## Quality Map

Findings from the /code-review lens over the scouted areas (read-only; none
block the spec, two shape it):

1. **Shipped code the fixed decisions retire**: `harnesses/resolver.py ::
   _access_evidence` rejects launches with `authentication_required` /
   `authentication_expired` / `authentication_probe_failed` /
   `access_unavailable` / `access_probe_failed` — auth gates launch today,
   directly contradicting "auth is never a hard pre-launch gate". The spec must
   reshape these `ResolutionRejectionCode` values (and `launch_options`
   exclusion reasons) into advisory surfacing, not leave a dead gating branch.
2. **Plan residue to retire**: `RUNTIME-SURFACING-S2-PLAN.md` S2f item 4
   ("Land the backend setup actions (sign in, test access) with a REST action
   surface and a CLI fallback") was never built. The "test access"
   exactly-once provider call, the pre-launch "sign in" action, and the S2
   probe-contract rule "access remains `unknown` and cannot authorize launch"
   are all superseded by the reshape. Retirement is deleting planned text, not
   shipped code; S2f part 1 (resolver, gate, facts) does not depend on item 4.
3. **Dead read surface**: `blocks_store.py :: ExecutorBlockStore.
   list_drift_evidence` has zero consumers outside its own tests — drift
   evidence is store-only with no REST/MCP/UI reader. Not auth work, but if the
   auth-request event ships a read surface, drift should eventually follow the
   same pattern rather than accrete a second bespoke one.
4. **DRY risk on codex auth classification**: `codex/diagnostics.py`
   (`chatgpt_auth_rejected`, 401/403 on upgrade) is finalize-plane; a live
   classifier will re-recognize the same signal. Share the recognition
   vocabulary (status-set + code literals) in one owner so the live event and
   the post-hoc diagnostic cannot drift apart.
5. **Single-slot observer ports**: `TranscriptDriftHook`,
   `PromptDriftObserverPort`, and `TranscriptTailer.on_drift` each carry one
   observer. Any design adding a second classifier at the same point needs an
   explicit fan-out, or the second consumer silently displaces the first.
6. **Known debt, unchanged**: `probes/runner.py` TODO to generalize
   `HOME_DIR_ENV_BY_HARNESS` onto `HarnessDescriptor` (acknowledged S2
   completion item; the settings-menu probe wiring will touch this seam and
   could carry the fix).
7. **Documented-gap seams**: drift seams 3 (session bootstrap rejection) and 4
   (`harness_rejected_prompt`) have no production producer. Worth knowing
   because a harness that loses auth and exits looks today like an
   "undifferentiated client exit" — exactly the blind spot the PTY/wire login
   classifier closes from the other side.

---

## Plan

> Superseded in part by the **Delta** section below (launcher agent reframed as
> the primary consumer; slices recut there). The bounded-context split and
> items 1, 5, 6, 7 stand.

Shape for the spec, in dependency order. Bounded contexts stay separate
throughout: **Enablement** (settings-time, request/response, owns the toggle +
capabilities + resolver) and **Auth Signal** (runtime, volatile, event-driven,
never gates).

1. **Wire-side login-request detection (Python, addon process).** A sibling of
   `LiveStatusObserver` installed at the same two `addon_handlers.py` seams:
   Anthropic — classify `flow.response.status_code == 401` at
   `handle_response_headers` (header-time; no chunk tap needed); Codex — WS
   upgrade 401/403 where the transport records `response_status_code`, sharing
   one recognition vocabulary with `codex/diagnostics.py` (Quality 4). Emits a
   control-plane auth-request event, best-effort, mirroring the `DriftEmitter`
   dedup idiom (one event per run per auth episode, not per 401).
2. **Event plane (Python, API process).** New `tm_events` payload type
   (`auth_request` signal model + `parse_notify_payload` branch + hub
   subscriber set), surfaced on the existing session/run SSE streams. No new
   channel. Durable row optional but recommended (an inbox needs replay for
   requests raised while the UI was closed).
3. **PTY-side detection (gateway, TypeScript) — the one new observation
   point.** Per-harness login-demand matcher mirroring
   `HarnessPromptInputAdapter`, fed from the existing `session.onData` pump
   (already runs detached). Needs the gateway → API bridge decision: a small
   authenticated callback from gateway to the control plane, or reuse of the
   existing run-lifecycle write path. This is supplementary to (1): wire 401s
   cover mid-run loss for claude/codex; PTY covers demands that never reach the
   wire (harness refuses to send, prints "run /login").
4. **Surface (www).** Greenfield global toast + auth-request inbox subscribing
   to the SSE event; resolve action = `adoptRun` + ordinary attach by run id
   (all existing). Keep it a distinct global surface; pane-internal errors keep
   their inline-alert precedent.
5. **Enablement.** Per-harness toggle: recommend a minimal server-side home
   (single-row settings table or a `[harnesses]` section in `settings.toml`)
   because CLI/MCP launch eligibility is computed backend-side; localStorage
   cannot reach it. Toggle feeds `launch_options` / `resolve_target` snapshots
   as a third enablement fact beside exists + version. Reshape the resolver's
   auth rejection codes (Quality 1) in the same slice so "enablement gates,
   auth surfaces" is true in code, not just in the contract.
6. **Opportunistic probes (settings-open).** Wire the existing, complete
   `run_authentication_probe` behind a settings-scoped endpoint: codex + claude
   cheap local probes on menu open; grok on-demand only (network, and its
   parser is an S2h stub — display `unknown` honestly until then).
7. **Retire residue.** Update `RUNTIME-SURFACING-S2-PLAN.md` S2f item 4 and the
   probe-contract "cannot authorize launch" language to the reshaped posture.

Binding verdict, one line: the seams that matter bind — live wire taps,
`tm_events` hub, attach-by-run-id, probe adapters all reuse cleanly; the drift
seams themselves do not (drift-typed, single-slot, no PTY view, post-persist),
and the only genuinely new infrastructure is the gateway PTY hook + bridge and
the enablement toggle store.

---

## Delta: launcher agent is the primary consumer

Reframe: the main consumer of "prompt not accepted" is the DIRECTOR AGENT that
launched the captured run, in real time, with a reason enum (at least
`auth_required` and `usage_limit_reached`). The human toast/inbox is a
secondary rendering of the same control-plane signal.

### 1. Launcher-notification path — BUILT, missing only the producer

The agent-facing real-time path exists end to end in the control plane:

- **Verbs**: `api/v1/controlplane_mcp.py` exposes `prompt`, `wait_for_reply`,
  `watch` / `unwatch` (plus `roster`, `workspace_summary`, `conversation`,
  `launch`, `interrupt`, `close`) over `controlplane/service.py ::
  ControlPlaneService`.
- **Synchronous receipts**: `prompt` returns `prompt_models.py :: PromptResult`
  with per-target `PromptReceipt` (`status: submitted|failed|unknown`,
  open-string `reason`, `wire_exchange_id` correlation).
- **Correlated wait**: `delivery_models.py` delivery ledger
  (`DeliveryState` includes `needs_you` and `failed`;
  `WaitForReplyStatus` mirrors it) + `delivery_wait.py ::
  ControlPlaneDeliveryWait.wait`, resolved in real time by
  `SessionEventHub.subscribe_control_plane_delivery` doorbells
  (`session/listen.py`) fed from `delivery_store.py` pg_notify on `tm_events`.
- **Standing subscription with push**: `watch.py :: ControlPlaneWatchEngine`
  mints `WatchFact` on tier transitions (`turn_completed`, `state_changed`,
  `needs_you`) and `watch_delivery.py :: WatchDeliveryLoop` delivers the
  formatted envelope **into the watching agent's own PTY** via
  `PromptDeliveryCoordinatorPort` — genuine real-time push to an agent.

The gap is purely the **producer**: nothing classifies an auth or usage-limit
failure into this plane. Today a 401/429-failed turn produces no turn-boundary
completion and no `needs_you` tier change (`needs_you` currently derives only
from the live-status `asked` kind — `controlplane/service.py` checks
`target.needs_you.get("kind") == "asked"`), so `wait_for_reply` times out as
`pending` and `watch` stays silent. The launcher is blind not because the pipe
is missing but because nothing puts the fact into the pipe.

### 2. Prompt-delivery seam re-evaluated — yes, one seam covers both consumers

Wiring the failed-prompt classifier into the receipt/delivery plane gives the
launcher receipt, the watch push, the human overview, and (optionally) drift
evidence from ONE classification point:

- The wire failure observer (Anthropic 401/429 at `addon_handlers.py ::
  handle_response_headers` header time; codex WS upgrade 401/403 + in-band
  frames at `handle_codex_websocket_message`) correlates by run_id/flow state
  and (a) resolves the run's open deliveries to a terminal state with the
  classified reason, and (b) drives a `needs_you` condition with a new kind on
  the activity plane. `wait_for_reply` then resolves in real time (doorbell),
  `watch` fires `needs_you` into the launcher's PTY, and the same signals feed
  the human status overview and SSE streams. No new channel, no new verb.
- **Vocabulary placement caution**: `HARNESS_REJECTION_PROMPT_REASONS` is
  defined as harness CONTRACT evidence — its sole purpose is feeding the S2d
  drift seam (`ActuationDriftObserver`), and it is a documented gap by design.
  `auth_required` / `usage_limit_reached` are provider/runtime conditions, not
  contract drift; putting them in that set would mint drift evidence on every
  expired login. Recommend a THIRD reason set in `prompt_models.py` (e.g.
  provider-condition reasons: `auth_required`, `usage_limit_reached`) beside
  `OPERATIONAL_PROMPT_FAILURE_REASONS` and `HARNESS_REJECTION_PROMPT_REASONS`.
  `PromptReceipt.reason` is an open string, and the sets are frozensets used
  for classification, so this is additive.
- The earlier gateway PTY hook becomes SUPPLEMENTARY: it covers demands that
  never reach the wire (harness refuses to send, prints "run /login" at
  startup), feeding the same receipt/needs_you plane through the bridge.

### 3. Usage-limit detection per harness — none exists; same seams as 401

No wire-level usage-limit classification anywhere (the only 429 handling is
`counting.py`'s own count_tokens sidecar skip and the generic
`tag_http_error_status` `http_429` stop-reason at finalize). Detection points:

- **Anthropic**: HTTP 429 at `handle_response_headers` (status alone suffices
  for the enum; the error body distinguishes rate-limit vs usage-limit if a
  finer split is wanted — that needs the chunk tap since the body follows).
- **codex**: no limit-frame constant exists in `codex/protocol.py`; in-band
  usage-limit frames need a protocol check against a real capture (same lesson
  as the stderr probe: certify against the real binary). Upgrade-level 429
  would surface at the same transport point as the 401/403.
- **grok**: no wire substrate yet (no adapter registered); out of scope until
  S2h.
- Share one recognition vocabulary owner with `codex/diagnostics.py ::
  chatgpt_auth_rejected` as already flagged (Quality 4).

### 4. Control-plane naming and substrate

The realtime all-agent-status overview is the **controlplane activity plane**:
`controlplane/activity.py :: GatewayActivitySnapshot / GatewayActivityRun /
ActivityStatusTier` (`active | needs_you | idle | stalled | terminal`),
assembled by `ControlPlaneService` into `workspace_summary` / `roster` and
watched by `ControlPlaneWatchEngine`. Substrate: `tm_events` pg_notify →
`SessionEventHub`. Agent-facing consumption is BUILT (MCP verbs above);
UI-facing SSE streams exist (`session_routes.py`, `stream.py`); only the human
toast/inbox rendering is unbuilt.

### 5. Revised slices (launcher path first)

- **S1 (priority): wire failure classifier + receipt/delivery integration.**
  Python-only. Observer at the two addon seams classifying 401 →
  `auth_required` and 429 → `usage_limit_reached`; new provider-condition
  reason set in `prompt_models.py`; resolve open deliveries + drive the
  `needs_you` activity condition. Deliverable: a director agent's
  `wait_for_reply` / `watch` reports the rejection in real time. Includes the
  shared recognition vocabulary with `codex/diagnostics.py`.
- **S2: enablement** (unchanged, independent, can run parallel to S1): toggle
  store + third enablement fact in resolver/`launch_options` + retire the
  auth-gating rejection codes.
- **S3: human surface**: toast/inbox UI over the existing SSE signals S1
  produces, attach-by-run-id action, settings rows + opportunistic
  `run_authentication_probe` wiring. Needs S1; settings rows pair with S2.
- **S4: gateway PTY matcher + bridge** (now last): supplementary detection for
  never-hits-the-wire demands, feeding the same S1 plane.
