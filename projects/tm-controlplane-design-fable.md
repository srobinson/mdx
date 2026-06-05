---
title: Control plane design (fable)
type: projects
tags: [transport-matters, control-plane, design, architecture]
summary: One Python control-plane service owning all verb policy; the gateway grows exactly one net-new resultful runtime primitive (PTY input inject). Watch rides the existing activity SSE plus typed tm_events parsing. Auth is a hashed run-scoped bearer minted inside the capture lease. Launch reaches the canvas through an adoption reconciler triggered by the activity stream the canvas already consumes.
status: active
source: independent design against main 0d88c1081f104cbd3adca771061772be256eb874; inputs CONTROLPLANE.md, tm-controlplane-scout-action.md, tm-controlplane-scout-observe.md, docs/ARCHITECTURE.md
confidence: high
created: 2026-07-11
---

# Control plane: whole-system design

Designed independently against pristine `main` @ `0d88c10`. Every seam is cited
file + symbol. Verbs, principles, and record shapes are CONTROLPLANE.md as
approved; this design resolves the five open tensions and binds each verb to
the scout reuse maps. Nothing the maps list is reinvented.

## Decision summary

| Tension | Decision |
| --- | --- |
| 1 Service placement | **(a)** One Python service (`controlplane/`); gateway grows dumb resultful runtime primitives only. Amend `docs/ARCHITECTURE.md` with a control-plane carve-out; CONTROLPLANE.md stands. |
| 2 Auth | Bearer minted inside the capture lease, SHA-256 stored in `control_plane_grants` (0012), raw token only in the seeded run home. FastAPI dependency resolves token → run_id → grant per request (no cache → instant revoke). MCP binding: thin ASGI auth middleware around the mounted SDK app (SDK `TokenVerifier` as the fallback if the S3 spike favors it). `/mcp` mounts before `mount_frontend_bundles`. |
| 3 Watch | Subscriptions + damping in Python. Triggers: existing activity SSE (`state_changed`, `needs_you`, incl. stalled/exited) + typed `wire_exchange` parsing on the existing tm_events LISTEN (`turn_completed`). Delivery through the prompt inject primitive. Envelope has ONE owner (Python) — no cross-language mirror. |
| 4 Prompt receipt | New resultful `RunManager.deliverInput` + `POST /v1/runs/:runId/input`, distinct from the void `write`. Returns typed outcome per target. Interrupt = harness break byte + settle inside the primitive; policy (envelope, entitlements, fan-out, dispatch_id, audit) in Python. "delivered" = bytes accepted by a live run's PTY, documented as such. |
| 5 Launch → canvas | `launchedBy` lineage threaded through `launchFields` (PR #246 precedent) onto `RunView`; canvas adoption reconciler beside the existing prune reconciliation, triggered by the activity stream the canvas already consumes (`useWorkspaceActivityStream.ts`), adopts controlplane-originated runs into `capturedRunStore` and opens a pane. |

Slice order refined: identity → service+observe → skins → **prompt → watch** →
launch/manage → integration (prompt moves ahead of watch because watch delivery
reuses the prompt primitive).

## Tension 1 — Service placement: (a) one Python service, gateway grows primitives

**Decision.** The control plane is one Python service,
`api/src/transport_matters/controlplane/`, exactly as CONTROLPLANE.md declares.
The Node gateway gains no control-plane policy. It gains one net-new dumb
primitive (resultful PTY input inject, tension 4); every other gateway-side need
is an existing surface: `POST /v1/runs` and `POST /v1/runs/:runId/terminate`
(`packages/runtime/src/server/runtimeRouter.ts` `createRuntimeRouter`),
`GET /v1/workspaces/:id/activity` and `.../activity/stream`
(`packages/activity/src/server/activityRouter.ts` `createActivityRouter`).
Python calls these as a client over `Settings.gateway_url` through a small typed
client module (`controlplane/gateway_client.py`, httpx; the browser-facing
`api/v1/run_proxy.py` `RunProxyMount` is a forwarding seam for downstream
clients and is not reused as the service's client).

**Justification against principle #1 ("twin skins, one service").** This is the
strongest available reading of the principle: all five verbs' policy —
entitlements, envelope, fan-out, receipts, damping, audit, conversation
projection — lives in one module tree, one language, one process, and both
skins are in-process thin adapters over the same service object
(`app.state.controlplane`). The alternative (b), a gateway-hosted action
engine, structurally splits the service: entitlement checks in TypeScript
against grant rows in Postgres, an audit write crossing process per action,
conversation still requiring a Python provider port (reusing
`session/timeline.py` `project_timeline` is mandatory), and the MCP skin — the
primary consumer — degenerating into a forwarding proxy adding a hop per tool
call. (b) also forces the envelope convention into two languages with a
mirror-test burden; (a) dissolves that finding entirely (one Python owner).

**Why the verb-side gravity favors Python.** Four of five verbs' inputs are
Python-native: identity minting and home seeding (`captured_run_context.py`
`build_captured_run_context`, `cli/claude_home.py`, `cli/codex_home.py`), grant
and audit persistence (Alembic via `session/migrate.py` `apply_migrations`,
pool in `main.py` `lifespan`), the conversation projection
(`session/timeline.py` `project_timeline` + `session/async_dao.py`), and
`turn_completed` (the `wire_exchange` flavor already arrives on Python's own
tm_events LISTEN, `session/listen.py` `SessionEventListener`). What the gateway
uniquely owns — run registry, PTY funnel, xstate-derived agent state — is fully
consumable through request/response primitives and one existing SSE stream. No
state derivation is rebuilt in Python: roster state and watch triggers are read
from the activity projection wire surface, never re-derived (the scout-B DRY
verdict holds).

**Degradation.** Gateway absent → observe/conversation still answers (pure
Postgres); action and watch verbs return the structured `busy_gateway`, matching
the `api/v1/runs_unavailable.py` precedent. Under (b) the entire control plane
would die with the gateway.

**Lifecycle.** The gateway is a child of the Python server (`main.py`
`lifespan` owns `app.state.gateway_process`), so Python is already the
composition root of the whole system. In-memory watch subscriptions in Python
share the lifetime of the runs in the child registry: both die with the API,
which is the spec's stated durability contract.

**What amends the doc.** `docs/ARCHITECTURE.md`, not CONTROLPLANE.md:

1. The two-plane rule ("new product contexts do not extend" Python) gains an
   explicit carve-out: *the control plane is not a product context; it is
   policy over both planes (identity, entitlements, audit, projection
   composition) and lives in Python beside the stores it guards. The gateway
   exposes resultful runtime primitives and hosts no control-plane policy.*
2. The Comms charter is disambiguated: the control plane is not Comms. Comms
   (directed agent↔agent messaging as a bounded context) remains a future TS
   context and, when it lands, consumes the same runtime primitives this design
   adds.
3. The origin-flip migration list gains the control plane: when the Gateway
   becomes the front door, `api/v1/controlplane` and `/mcp` join exchanges, run
   meta, run stream, and breakpoint as surfaces reverse-proxied to Python.

## Tension 2 — Auth (greenfield)

**Grant scope identity.** `workspace_id` = the Activity `WorkspaceId`
(`slug/hash`, `packages/activity/src/ids.ts` `asWorkspaceId`, derived in
`run_lifecycle.py` `build_run_lifecycle_event`). Rationale: every read surface
the grant bounds is already keyed by it — the activity routes take it in the
URL, and it is the run-directory identity (`workspaces/{slug}/{hash}/{run}`).
Runtime's UUID `spaceId`/`worktreeId` stay internal partitions; no equivalence
is inferred (scout-A P1 resolved by choosing, not mapping).

**Storage.** Migration `0012_control_plane_grants` (new file under
`api/migrations/versions/`, chain head after `0011_run_live_status_asked`):
`{run_id unique, token_sha256 unique, role IN (observer, director),
workspace_id, created_at}`. Revoke = DELETE the row (spec); resolution is a
per-request SELECT on loopback Postgres with no cache, so the token dies with
the row instantly. Raw tokens never touch Postgres or logs.

**Mint + seed + persist, atomically inside the lease.** All inside the prepare
path so rollback discipline is inherited, ordered:

1. `captured_run_context.py` `build_captured_run_context`: after
   `prepare_launch` mints the run_id and the home overlay materializes, mint
   `secrets.token_urlsafe(32)` and inject the MCP client entry into the
   run-local overlay — before invocation construction, never touching the
   operator source home.
2. Seeding writers: Claude Code `.mcp.json` beside `cli/claude_home.py`
   `apply_claude_proxy_env_settings` (same atomic merge machinery); Codex a
   `[mcp_servers.*]` block via `cli/codex_home.py` `CodexSeeder` — promoting
   the private TOML merge helpers to public names first (api/CLAUDE.md module
   privacy). Entry shape: streamable-HTTP URL `http://127.0.0.1:{port}/mcp`
   plus `Authorization: Bearer` header.
3. Persist the hashed grant row inside `capture_rpc.py`
   `CaptureLeaseRegistry.prepare_capture` after authoritative identity
   resolution (`capture_rpc_routes.py` `_resolved_domain_request`) and before
   the spawn spec returns to Runtime. Persistence failure → release the lease
   (fail closed). Grant-enabled launch rejects the stub capture adapter.
4. Revoke-on-release rides the existing async `release_capture` path (not the
   sync `CapturedRunLease.close`, which must stay sync per scout A).

The grant choice crosses `RunManager.createNew` →
`packages/runtime/src/adapters/CaptureRpcClient.ts` → `capture_rpc_routes.py`
as a typed, non-secret field (`grant: none|observer|director`); the bearer
itself never enters the TypeScript payloads.

**Resolution.** `controlplane/principal.py`: a FastAPI dependency
(`require_control_plane_principal`, modeled on `api/v1/origin.py`
`require_http_origin`) reads the bearer, SHA-256s it, resolves the grant row,
and yields `Principal {actor_run_id, role, workspace_id}`. Service methods take
a `Principal`, never a token and never caller claims (kills the
`runtimeRouter.ownerFromQuery` self-declared-owner pattern at the control-plane
boundary). REST injects `Principal(actor=human)` under the existing loopback
trust (`TrustedHostMiddleware` + origin check).

**MCP SDK binding.** Default: a thin ASGI middleware wrapping the mounted
streamable-HTTP app — resolve bearer → 401 unknown → stash `Principal` in a
contextvar the tool handlers read. The SDK's official `TokenVerifier`/
`AuthSettings` hook is OAuth-resource-server shaped (issuer/resource metadata
ceremony loopback bearers do not need); the S3 spike confirms or flips this,
but the contract is fixed either way: resolution happens before tool dispatch,
handlers receive a resolved principal.

**Mount ordering.** In `main.py` `create_app`: `app.mount("/mcp", mcp_app)`
strictly before `mount_frontend_bundles(app)` (the `/` SPA catch-all is mounted
last and would swallow it — verified constraint). The SDK session manager's
`.run()` context enters in `lifespan` beside the existing
`_close_lifespan_resource` discipline.

## Tension 3 — Watch

**Placement.** Subscriptions and damping live in the Python service
(`controlplane/watch.py`): an in-memory registry
`{watcher_run_id → {targets, events}}` plus a per-watcher damping buffer.
In-memory is correct — the gateway is a child process, so subscriptions and
runs share one lifetime.

**Triggers, two paths into one buffer:**

- `state_changed` / `needs_you` (including timer-derived `stalled`/`exited`,
  which never touch Postgres): an httpx streaming client per watched workspace
  on the existing `GET /v1/workspaces/{id}/activity/stream`
  (`activityRouter.ts` emits a `snapshot` frame then `delta` frames exactly
  when `status`/`needsYou` change — dedup already upstream in
  `packages/activity/src/projections/workspaceActivity.ts`
  `subscribeWorkspaceActivity`; 15s keepalive built in). Reuses the existing
  wire surface; zero new gateway code for triggers.
- `turn_completed`: the `wire_exchange` flavor already arriving on Python's
  tm_events LISTEN. Extend `session/listen.py` `parse_notify_payload` with
  typed parsing for it (today it silently drops three of four flavors — the
  extension is typed models + tests, not a dict passthrough, per the scout-B
  quality note).

**Damping (first-class).** Per-watcher coalesce buffer with a minimum flush
interval of a few seconds (spec): events accumulate, one asyncio flush task per
watcher emits a single coalesced line. Five panes finishing together produce
one wake-up.

**Delivery.** One enveloped line (`[tm watch] researcher (a1b2) finished turn
14; builder (c3d4) → needs_you`) through the prompt inject primitive (tension
4) in nudge mode. A failed watch delivery is dropped and audited, never
retried into a storm.

**Envelope.** Composed only in Python (`controlplane/envelope.py`), consumed by
prompt and watch alike. Because placement (a) keeps all composition in one
language, the cross-language mirror-test burden identified in scouting
disappears.

**Cross-process event path (complete):** gateway activity SSE → Python watch
buffer ← Python tm_events LISTEN; buffer → damped flush → gateway inject
primitive → `PtySession.write`. Both hops are loopback request/response or an
existing SSE; damping's multi-second floor makes the added latency irrelevant.

## Tension 4 — Prompt receipt

**The resultless-PTY fix is a new primitive, not a changed contract.**
`RunManager.write` stays void (the terminal WebSocket path keeps fire-and-
forget). Add `RunManager.deliverInput(runId, owner, {text, interrupt})` in
`packages/runtime/src/service/RunManager.ts`, returning a typed outcome:
`delivered | not_found | ended | write_failed(reason)`. It validates the run
exists and is live, then writes through the same funnel
(`packages/runtime/src/ports.ts` `PtySession.write` →
`adapters/NodePtyAdapter.ts`) — no alternate PTY path. Exposed as
`POST /v1/runs/:runId/input` beside the existing routes in
`runtimeRouter.ts` `createRuntimeRouter`. The programmatic-write precedent is
already in-repo (`RunManager.register`'s OSC color responder).

**Mechanics live with the PTY; policy lives in Python.** The primitive owns
bytes and timing: on `interrupt`, write the harness break byte (Esc `\x1b` for
Claude Code; Codex expected Esc as well — both locked by a recorded-PTY spike
in S4, harness-keyed constants in one module), settle for a fixed per-harness
delay, then deliver. Delivery wraps multi-line text in bracketed paste
(`\x1b[200~ … \x1b[201~`) so embedded newlines cannot submit mid-text, then a
trailing CR submits; the harness queues it and it lands next turn.

**Receipt truth level (documented contract).** `delivered` means the bytes were
accepted by a live run's PTY session — not that the harness consumed them.
That is the strongest claim a PTY can honestly make; the receipt schema says
so.

**Python fan-out** (`controlplane/prompt.py`): director entitlement check →
envelope prefix `[tm from a1b2 «Director»]` → bounded-concurrency fan-out in
stable target order → per-target `{run_id, delivered|failed, reason}` receipts
(partial failure reported, never raised) → one `dispatch_id` per call → one
audit row carrying per-target outcomes. `manage.interrupt(run_id)` is the same
primitive with break-only and no text; `manage.stop` is the existing terminate
route.

## Tension 5 — Launch → canvas pane

**Server side.** `launch(workdir, harness, name?, first_prompt?, grant?)` calls
the gateway `POST /v1/runs` (one idempotency key per launch intent, the
`RunManager.create` single-flight and capture-rollback path — identical to the
UI). Two lineage additions ride `launchFields` (the PR #246 lineage precedent):
`launchedBy {actor_run_id, name}` and `origin: "controlplane"`, surfaced on
`RunView` (`www/packages/core/src/transport.ts`). `first_prompt` delivers
through the inject primitive after spawn (post-readiness nudge), not a new argv
seam.

**Canvas side: adoption is the missing half of reconciliation.** Pane identity
stays browser-minted; the server never fabricates `runKey`s. The existing
reconciliation home (`www/packages/canvas/src/model/capturedRunLifecycle.ts`)
today only prunes (`capturedRunStore.dropRun` when a fresh backend no longer
knows a remembered run). Add the symmetric half:

1. **Trigger:** the workspace activity stream the canvas already consumes
   (`www/packages/canvas/src/infrastructure/stream/useWorkspaceActivityStream.ts`
   feeding `runVitalsStore.ts`). A run appearing in the projection that has no
   `capturedRunStore.runs` mapping fires the reconciler — a live signal, no
   polling.
2. **Qualify:** fetch `listRuns` (`www/packages/core/src/transport.ts`) and
   adopt only runs with `origin === "controlplane"`. Human-spawned runs are
   never unmapped in their own browser; scoping adoption to control-plane
   origin keeps existing semantics untouched (generalizing adoption to any
   unmapped run is a deliberate follow-on, not this slice).
3. **Adopt:** mint `createCapturedRunKey(provider)`, insert the record via a
   new `capturedRunStore.adoptRun(runKey, {provider, runId})` action, create
   the pane record through the existing spawn/pane path
   (`model/spawn.ts` / `paneRecords.ts`), labeled with the launcher's name.
   `ensureRun` then short-circuits on the existing record and the normal
   terminal-WS attach takes over — no new attach machinery.
4. **Persistence:** the adopted record persists like any other, so reload
   re-docks/reattaches. Any record-shape change bumps
   `CAPTURED_RUN_STORAGE_VERSION` with a shape-tolerant migrate (the
   persistence data-loss rule).

## Summary primitive (orchestrator addition, assessed)

**Useful in v1: yes.** It is the pull half of a watch nudge: the watcher learns
`researcher (a1b2) finished turn 14` and needs one cheap situational read —
what is this run for, what just happened — without paying for the default
10-turn conversation window. It instantiates principle #4 for the most common
pull pattern, sitting exactly between `roster()` (state only) and
`conversation()` (full feed). Corroborating product evidence: the activity wire
already carries `initial_prompt` and `last_message`
(`packages/activity/src/server/activityRouter.ts` `runToWire`) — the product
has already identified this pair as the salient situational read.

**Placement: a mode of conversation(), not a new verb.**
`conversation(run_id, shape="summary")`. The summary is purely a selection
policy — first genuine user message plus the last 4 messages — over the
identical projection pipeline; a separate `summary(run_id)` verb would
duplicate the route, tool schema, entitlement check, audit plumbing, and DTO
for zero new projection logic. Seam: the S2 observe service function in
`controlplane/observe.py`, which builds the filtered message list once
(run-scoped DAO query → `session/timeline.py` `project_timeline` →
`MessageItem`-only → IR text-part filter) and then applies one of two selection
policies: the cursor window (`after_turn`/`limit`, default) or the summary
preset. No parallel projection exists in either mode.

**Reuse check.** Rides the same strip-injected logic by construction:
`MessageItem`-only selection already excludes the injected item kinds
(`StateItem`/`ContextItem`/`DiagnosticItem` in `session/timeline_models.py`),
so "initial user prompt" = the first `MessageItem` with `role == user` in turn
order after filtering — the first genuine user turn, post-strip. The tail is
the last 4 `MessageItem`s role-agnostic. One summary-specific rule: when the
run has fewer than 5 messages the head and tail overlap — dedupe by
`turn_index`/sequence, never repeat a message. A pristine run with no genuine
user turn yet returns an empty summary (state belongs to `roster()`).

**Token shape: fits the existing discipline unchanged.** Both selections pass
through the same `max_chars_per_message` tail-truncation and the total hard cap
with the `truncated` marker; the summary preset is strictly smaller than the
default window, so the caps already bound it. One guard: the summary must be
built from the timeline projection (Postgres truth), never from the activity
wire's `initial_prompt`/`last_message` fields — those are a TS-side
convenience pair and using them would fork the conversation truth across
harnesses.

**Slice impact:** lands inside S2 as the second selection policy of the same
observe function; no new slice, no new route, one new tool-schema enum value.

## Slice decomposition (7, dependency order)

- **S1 — Identity + grants + doc amendment.** Migration
  `0012_control_plane_grants`; mint/seed/persist/revoke through the lease as in
  tension 2; `controlplane/principal.py` resolver;
  `docs/ARCHITECTURE.md` carve-out + origin-flip addition landed with the code
  that realizes it. Tests: seeding round-trip both harness homes (source home
  byte-unchanged), resolve, revoke-kills-token, fail-closed lease release.
  Widest blast radius (cross-process spawn path) — review accordingly.
- **S2 — Service + observe + audit table.** `controlplane/` package wired in
  `lifespan`. `conversation()` = new run-scoped DAO query (every existing query
  is session-scoped; `EventRow.run_id` exists) + `project_timeline` +
  `MessageItem`-only + IR text-part filter + `turn_index` cursor + hard caps
  with `truncated`. `roster()`/`workspace_summary()` = activity projection
  read (`gateway_client.py`) joined with `SessionRow` (cwd, title; `model` from
  the latest turn's `EventRow.model`; per-run `last_turn_at` = new run-scoped
  `max(event.ts)` query). Migration `0013_control_plane_actions` + audit
  writer in a new module (never grow `writer.py`/`dao_statements.py`, both
  near the 700 limit). `busy_gateway` degradation from day one.
- **S3 — Twin skins.** `mcp` SDK dependency; REST module
  `api/v1/controlplane_routes.py` under `/v1/controlplane` (thin); MCP
  streamable-HTTP app mounted at `/mcp` before `mount_frontend_bundles`,
  session manager in `lifespan`; auth-binding spike (middleware vs
  `TokenVerifier`). Contract tests: tool schemas, skins-carry-no-logic, `/mcp`
  not swallowed by the SPA catch-all, 401 on unknown/revoked token.
- **S4 — Prompt.** Gateway primitive `RunManager.deliverInput` +
  `POST /v1/runs/:runId/input` (break/settle/bracketed-paste/CR mechanics;
  recorded-PTY spike locks per-harness break + settle constants). Python
  fan-out, receipts, `dispatch_id`, envelope, audit row. Both skins expose it.
- **S5 — Watch.** `controlplane/watch.py` registry + damping; activity-SSE
  trigger client; typed `wire_exchange` parsing in `session/listen.py`;
  delivery via the S4 primitive. Unit tests: damping coalescence, per-watcher
  isolation, drop-and-audit on failed delivery.
- **S6 — Launch + manage + canvas adoption.** `launch()` with grant option,
  `launchedBy`/`origin` lineage through `launchFields` → `RunView`;
  `stop()`/`interrupt()`; entitlement enforcement (observer vs director) across
  all verbs; run `name` lands here as a real spawn-spec field (roster falls
  back to `SessionRow.title` preview when absent); canvas adoption reconciler
  per tension 5 (structural-PR rule: full `pnpm --filter @tm/shell test`).
- **S7 — Integration + error taxonomy.** The spec's end-to-end loop: granted
  spawn → agent `workspace_summary` → prompt a peer → receipt + audit row →
  revoke → denied retry. Taxonomy hardening (`not_found`, `forbidden`,
  `busy_gateway`, `delivery_failed`) across every verb and both skins;
  dispatch-group queryability; packaged-wheel gateway coverage. Gates verbatim:
  `just check`, `just test`.

## Key risks

1. **MCP SDK auth fit** — unproven against loopback bearers; S3 spike is the
   gate, middleware is the safe default.
2. **Interrupt timing** — break byte + settle per harness has zero repo
   precedent; S4's recorded-PTY spike must lock constants empirically before
   receipts can be trusted.
3. **S1 blast radius** — the grant option crosses Python → TS → Python through
   the spawn path; the fail-closed ordering in the lease is the invariant to
   review hardest.
4. **Adoption semantics** — scoping to `origin === "controlplane"` is
   deliberate; widening adoption to any unmapped run changes multi-browser
   behavior and needs its own decision.
5. **Activity SSE as a service dependency** — Python holding streaming clients
   against its child gateway needs reconnect-on-drop handling; run loss and
   stream loss coincide (same process), which bounds the failure mode.
