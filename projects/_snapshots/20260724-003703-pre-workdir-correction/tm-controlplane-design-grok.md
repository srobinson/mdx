---
title: Control plane whole-system architecture (grok)
type: projects
tags: [transport-matters, control-plane, design, grok]
summary: Placement (b) — Gateway @tm/controlplane owns action and watch engines beside RunManager and Activity; Python data plane owns grants, token mint, home MCP seed, conversation projection, and audit; twin skins (MCP+REST) host on the current Python origin as thin auth adapters. Resolves five tensions with concrete seams. Refined 7-slice plan.
status: active
source: independent design against main 0d88c1081f104cbd3adca771061772be256eb874; inputs CONTROLPLANE.md + scout A/B reuse maps
confidence: high
created: 2026-07-11
family: grok
---

# Control plane architecture (grok)

Bound to scout reuse maps on pristine `main` @
`0d88c1081f104cbd3adca771061772be256eb874`. Reinventing any listed anchor is a
defect. This is design only; no repo writes.

## 1. Headline

**Placement = (b): gateway-hosted action engine + Python data plane.**

- **Product plane (TypeScript Gateway):** new context `@tm/controlplane` owns
  prompt delivery, watch registry + damping, launch/manage orchestration, and
  live roster state composition from Activity. It sits in-process with the one
  `RunManager` and Activity projections.
- **Capture / data plane (Python):** grants, token mint, home MCP seed, audit
  table, conversation projection over the normalized timeline, and the twin
  skins (MCP + REST) that resolve identity then call the right plane.
- **One logical service contract, two process homes.** Principle #1 ("twin
  skins, one service") means one verb surface and one principal model, not one
  OS process.

### What amends which doc

| Doc | Amendment |
| --- | --- |
| `CONTROLPLANE.md` §Architecture | Replace "New domain: `api/.../controlplane/` owning the four verbs" with the split: Python `controlplane/` owns identity, observe content, audit, skins; Gateway `@tm/controlplane` owns action and watch engines. Keep principles 2–5 and the verb shapes. |
| `docs/ARCHITECTURE.md` | No structural amend. Control plane action/watch is the first concrete product context under the Comms/orchestration charter. Capture-plane Python tables (grants, actions) are data substrate, not a new product context. |
| Scout A preferred shape | Adopted. |
| Scout B Python-service headline | Partially overruled for action/watch engines; Python remains skins + data plane + observe content. |

### Why not (a) alone

Pure Python service + gateway hop for every prompt byte and every watch nudge
puts latency and failure modes on the hot path, forces a second subscription
registry far from `RunManager`, and invites roster state re-derivation (scout B
DRY trap). PR #242 deleted Python `run_manager`; do not rebuild it.

### Why not pure (b) without Python skins

MCP Python SDK, bearer→Postgres grant resolution, conversation over
`project_timeline`, and home seeding already live in Python. Putting skins only
on Gateway would duplicate auth and force a second MCP host before the origin
flip. Skins stay on the **current origin** (Python) until the Gateway becomes
the front door; then REST migrates, MCP may follow.

---

## 2. System diagram

```text
 Agent (Claude/Codex)                    Human canvas / palette
        |                                         |
        | Authorization: Bearer <token>           | (explicit human principal)
        v                                         v
 ┌────────────────── Python origin (today) ──────────────────┐
 │  /mcp  (MCP streamable HTTP)   /v1/controlplane/* (REST)  │
 │           thin skins → ControlplaneFacade (Python)        │
 │                                                           │
 │  LOCAL:  grants resolve | conversation | audit write      │
 │  REMOTE: typed GatewayControlClient →                     │
 └─────────────────────────────┬─────────────────────────────┘
                               | private HTTP (same trust domain as run_proxy)
                               v
 ┌────────────────── Gateway process ────────────────────────┐
 │  @tm/controlplane router (new ContextMount)               │
 │    prompt / interrupt / watch / unwatch / launch / stop   │
 │    roster live fields                                     │
 │         |                    |                            │
 │         v                    v                            │
 │  RunManager (one)     Activity projections                │
 │  + resultful inject   subscribeWorkspaceActivity          │
 │  + PTY write          sameRunActivityProjection           │
 │                                                           │
 │  CaptureRpcClient ──► Python /v1/capture/*                │
 │    prepare (grant mint + home MCP seed + hash persist)    │
 └───────────────────────────────────────────────────────────┘
                               |
                               v
                    Postgres (Alembic-owned)
                    control_plane_grants
                    control_plane_actions
                    session events / timeline / lifecycle / live_status
```

After the origin flip (`docs/ARCHITECTURE.md`), the Gateway becomes the front
door and reverse-proxies capture reads; controlplane REST mounts natively on
Gateway; Python keeps grants/audit/conversation RPC and capture prepare.

---

## 3. Tension resolutions

### 3.1 SERVICE PLACEMENT → (b)

| Decision | Gateway `@tm/controlplane` action/watch engine; Python data plane + twin skins facade |
| Rationale | Action verbs need process-local registry, Activity state machine, and resultful PTY write. Observe content, identity, and audit need Postgres and the timeline projector. Twin skins share one Python facade so auth is written once. Matches two-plane rule; reuses every scout A/B anchor without a second RunManager. |
| Seams | Mount: `packages/gateway/src/app.ts` `buildGateway` / `gatewayContexts` / `ContextMount`. Composition: `packages/gateway/src/main.ts` `runGatewayProcess`, `createDefaultRuntimeRouterDeps` (inject the **same** `RunManager`). Runtime: `packages/runtime/src/service/RunManager.ts` `RunManager`. Activity: `packages/activity/src/projections/workspaceActivity.ts` `subscribeWorkspaceActivity`, `runActivityProjection`. Python facade: new `api/src/transport_matters/controlplane/service.py` (package new; do not grow `main.py` past role of lifespan wiring). Gateway hop: extend pattern of `api/src/transport_matters/api/v1/run_proxy.py` `RunRouteProxy` into a **typed** private client (not raw proxy of UI routes). Capture: `packages/runtime/src/adapters/CaptureRpcClient.ts` + `api/.../capture_rpc_routes.py` `prepare_capture`. |

**Principle #1 restated:** skins carry no logic; they resolve a principal and
call `ControlplaneFacade`. The facade is the one service from the skins'
perspective. Internally it routes by capability.

### 3.2 AUTH (greenfield)

| Decision | Run-scoped bearer minted at grant-enabled prepare; store **SHA-256 digest only**; raw token only in seeded home Authorization header; resolve bearer → grant row → principal; delete row = instant revoke. |
| Rationale | Identity is never self-declared (`CONTROLPLANE.md` principle 2). Owner query string is a compatibility partition only (scout A P1). Tool args never establish identity. |
| Seams | Mint site: `api/src/transport_matters/captured_run_context.py` `build_captured_run_context` / `prepare_launch` (run id already minted) + `prepare_captured_run` rollback via `CapturedRunLease`. Thread nonsecret grant choice through `CaptureRpcClient` / `PrepareCaptureRequest` (scout A anchors 11–14). Home inject: `cli/claude_home.py` `apply_claude_proxy_env_settings` sibling for `.mcp.json`; `cli/codex_home.py` `CodexSeeder` + atomic TOML merge for `[mcp_servers.*]`; facade `cli/home_seeders.py` `seed_home_dir` / `cli/runtime_home.py` `prepare_runtime_home`. Persist: new Alembic `0012_control_plane_grants` via `session/migrate.py` `apply_migrations` (never lazy create). Resolve: FastAPI dependency on `app.state` (model on `require_http_origin` and `CaptureLeaseRegistry` shape). MCP: mount official SDK ASGI at `/mcp` in `main.py` `create_app` **before** `mount_frontend_bundles` (SPA catch-all is last). REST human principal: explicit injection, not bearer. |

**Grant record**

```text
control_plane_grants(
  token_digest  bytea PRIMARY KEY,   -- SHA-256 of raw bearer
  run_id        text NOT NULL UNIQUE,
  role          text NOT NULL CHECK (role IN ('observer','director')),
  workspace_id  text NOT NULL,        -- Activity WorkspaceId "slug/hash"
  owner         text NOT NULL,        -- runtime owner partition
  created_at    timestamptz NOT NULL
)
```

**Grant scope identity (scout A decision 2):** `workspace_id` =
Activity `WorkspaceId` branded `slug/hash`
(`packages/activity/src/ids.ts` `asWorkspaceId`; lifecycle
`api/.../run_lifecycle.py` `build_run_lifecycle_event` +
`workspace.workspace_id`). **Not** UUID `SpaceId` / `WorktreeId`. Runtime space
ids remain placement keys; entitlement visibility is the activity workspace.

**Token lifecycle (atomic with launch)**

1. Capture prepare resolves workdir → authoritative workspace slug/hash + run_id.
2. If grant ∈ {observer, director}: `secrets.token_urlsafe` mint; inject MCP
   entry into **overlay** home only; `INSERT` digest row in same failure domain
   as lease registration.
3. On any failure before spawn spec returns: release lease (`CapturedRunLease.close`
   discipline) and delete grant row.
4. On run release / terminate path: delete grant row (revoke).
5. Mid-run grant change: not supported (launch-time only); revoke is immediate.

**MCP auth hook:** resolve Authorization bearer through the same dependency as
REST agent calls. Spike in S1/S3 against the official MCP Python SDK; if the
SDK hook shape differs, wrap once at the mount adapter without forking resolve
logic.

**Owner string:** never accept caller-supplied owner as identity. Service
methods take `Principal { kind: agent|human, run_id?, owner, workspace_id, role }`.
Runtime `ownerFromQuery` stays for low-level Runtime routes only.

### 3.3 WATCH

| Decision | Subscription map + damping live **in Gateway** `@tm/controlplane`, beside `RunManager` and Activity. Triggers from Activity deltas; delivery is in-process `RunManager` inject with envelope. Python `watch`/`unwatch` verbs proxy registration and write audit rows. |
| Rationale | Spec: "Subscriptions are in-memory beside the run registry." Registry is Gateway process-resident (`RunManager.runs`). Activity already LISTENs `tm_events` (`packages/activity/src/adapters/tmEvents.ts` `TmEventsActivityListener`) and emits status/needsYou deltas (`subscribeWorkspaceActivity` + `sameRunActivityProjection`). Python `SessionEventHub` drops three of four notify flavors; extending it would still lack stalled/exited derivation. |
| Seams | Triggers: `WorkspaceActivityProjections.subscribeWorkspaceActivity` → map status/needsYou changes to `state_changed` / `needs_you`; wire_exchange reconcile path (existing Activity ingestion) → `turn_completed`. Registry: new module under `packages/controlplane/src/service/watchRegistry.ts` (name illustrative; package follows canonical context layout). Delivery: new resultful Runtime inject (see §3.4), **not** terminal WebSocket (`runTerminalConnection` remains viewers only). Damping: per-watcher coalesce buffer + minimum interval (~2–3s); model single-flight of `refreshOwnerWorkspace` and keepalive of `activityRouter`, greenfield otherwise. Envelope: single cross-language constant, mirror-tested (`test_type_mirrors.py` precedent): `[tm watch] …`. Python verbs: facade → `GatewayControlClient.watch|unwatch` + `controlplane/audit.py` append. |

**Event → nudge mapping (references only; content via observe)**

| Event | Source | Nudge payload gist |
| --- | --- | --- |
| `state_changed` | Activity status change | `{run_id, from, to}` names only |
| `needs_you` | `needsYouForStatus` tier | `{run_id, kind}` |
| `turn_completed` | wire_exchange / turn boundary | `{run_id, turn}` |

No content, no transcript text, on the wire (principle 3).

**Cross-process path:** none for delivery. Python only registers interest.
Activity already bridges Postgres NOTIFY → Gateway memory; watch rides that.

### 3.4 PROMPT RECEIPT

| Decision | Add resultful Runtime action `inject(runId, owner, bytes, mode)` returning typed outcome; controlplane prompt fans out with `dispatch_id` and per-target receipts; envelope composed once in the action engine. |
| Rationale | `RunManager.write` returns `void` and silent-no-ops missing/ended/wrong-owner/empty writes (scout A P1). Terminal WS creates viewer state and is wrong channel. `terminate` is process kill, not interrupt. |
| Seams | New method on `packages/runtime/src/service/RunManager.ts` (or narrow `PromptPort` implemented by RunManager) — keep `write` for terminal path unchanged. Endpoint: `@tm/controlplane` router, not a second attachment on `/terminal`. Bytes end at `packages/runtime/src/adapters/NodePtyAdapter.ts` `NodePtySession.write` / `ports.ts` `PtySession`. Fan-out + receipt + audit: Python facade after Gateway returns per-target results (or Gateway accepts multi-target in one RPC to cut N hops — prefer **one Gateway call with targets[]** for a single dispatch). Envelope prefix always on: `[tm from {run_id8} «{label}»]`. |

**Modes**

| Mode | Behavior | Notes |
| --- | --- | --- |
| `nudge` | inject envelope+text + newline now | Harness queues for next turn |
| `interrupt` | harness break → settle → inject | Claude: Esc (`\x1b`) first; settle timer TBD by capture test; Codex: capture real PTY break in S5 fixture work before locking bytes |

**Receipt shape (never raises on partial failure)**

```text
{ dispatch_id, results: [{ run_id, status: delivered|failed, reason? }] }
```

Reasons: `not_found`, `forbidden`, `ended`, `busy_gateway`, `delivery_failed`.

**Interrupt ≠ stop.** `interrupt(run_id)` reuses inject break-only.
`stop(run_id)` → `RunManager.terminate`.

### 3.5 LAUNCH → CANVAS PANE

| Decision | Server launch reuses `RunManager.create` → capture prepare (grant path). Canvas adopts via activity stream + new `adoptRun` store path that binds `runKey→runId` **without** `POST /v1/runs`. |
| Rationale | Today pane identity is browser-local (`www/packages/canvas/src/model/capturedRunStore.ts`); `ensureRun` always creates. `useCapturedRunBinding` only knows spawn-then-attach. Server-side `RunManager` entry alone never creates a pane (scout A P1). Activity SSE already reaches canvas (`useWorkspaceActivityStream` → `/v1/workspaces/{id}/activity/stream`). |
| Seams | Launch verb: facade → Gateway controlplane launch → `RunManager.create` (anchors 4–5) with stable idempotency key per launch intent; grant option through capture RPC. **LaunchKind:** extend `packages/activity/src/domain/runActivityEvent.ts` `launchKinds` from `canvas\|detached` with `controlplane` (pg contract mirror). Canvas reconciler: on activity snapshot/delta for `launch_kind=controlplane` runs not present in `capturedRunStore.runs` values, call new `adoptRun(runKey, {provider, runId})` + `canvasActions` spawn pane ref with that `runKey` (mirror `addCapturedRun` / `createCapturedRunRef` but skip create). Binding: `useCapturedRunBinding` short-circuits when `persistedRunId` exists (already does); adopt must populate the store first. Drop path remains `dropRun` when process-resident run vanishes. |

**Not in scope for v1:** full server-persisted pane layout. Adoption is
best-effort for open canvas clients in the workspace; reload re-lists activity
and re-adopts live controlplane runs.

**first_prompt:** after create readiness, one resultful inject (nudge) with the
text; not argv. Keeps harness spawn contracts stable.

**name:** pass optional display name through spawn/lifecycle metadata
(`launchFields` lineage or new optional field on lifecycle); roster synthesizes
`name || SessionRow.title || run_id` until a dedicated column exists. Prefer
threading `name` into lifecycle payload in S6 rather than a migration if
possible; if a column is required, new focused migration module (do not grow
`session/test_migrate.py` past 700).

---

## 4. Verb ownership matrix

| Verb | Authz | Compute owner | Persistence | Skin entry |
| --- | --- | --- | --- | --- |
| `workspace_summary` | observer+ | Python join: Activity roster via gateway client + session cwd/title + last_turn_at query | audit optional (read) | both |
| `roster` | observer+ | same | — | both |
| `conversation` | observer+; target in workspace | Python: run-scoped DAO + `project_timeline` + MessageItem + text parts only; `shape=feed\|summary` | — | both |
| `watch` / `unwatch` | observer+ | Gateway watch registry | `control_plane_actions` | both |
| `prompt` | director | Gateway multi-target inject | actions + dispatch_id | both |
| `launch` | director | Gateway create + Python grant prepare | grant row + actions; canvas adopt | both |
| `stop` | director | `RunManager.terminate` | actions + grant revoke | both |
| `interrupt` | director | Gateway inject break-only | actions | both |

Observe text filtering IR: `part["type"] == "text"` on
`session/timeline.py` `project_timeline` / `MessageItem.parts` (scout B).

Degrade: gateway down → structured `busy_gateway` (mirror
`runs_unavailable` / `RunRouteProxy` 503 `gateway_unavailable`).

### Summary observe primitive (v1)

**Useful: yes.** Roster is state-only; full `conversation` feed is the right tool
for deep catch-up but too heavy for "what is this pane and where did it land?"
after a watch nudge. A fixed-window per-run summary is the missing middle rung
for director MoA loops and keeps token spend structural (principle 4).

**Placement: conversation-mode**, not a parallel verb.

```text
conversation(run_id, shape="feed" | "summary", ...)
# defaults: shape="feed" with existing after_turn / limit / max_chars_per_message
# shape="summary": ignore after_turn/limit windowing; fixed extract below
```

Rationale: one entitlement path, one projection pipeline, one cap/truncate
policy. A separate `summary(run_id)` tool would look like a second projector to
callers and to future skins. MCP may expose a thin alias tool that only sets
`shape="summary"` (skin sugar, zero domain logic).

**Reuse (same seam as feed — no parallel projection):**

1. Run-scoped event load (new DAO query; scout B gap).
2. `session/timeline.py` `project_timeline` → full timeline items.
3. Keep `MessageItem` only (`session/timeline_models.py` `MessageItem`) — drops
   `ContextItem` / `StateItem` / diagnostics (injected system reminders and hook
   context never become MessageItems).
4. Text-only parts: `part["type"] == "text"` (IR vocabulary once).
5. Keep roles `user` and `assistant` only (drop `system` / `tool` MessageItems if
   any survive).
6. Then branch on `shape`:
   - **feed:** existing cursor (`after_turn` via `MessageItem.turn_index`),
     default last 10, per-message and total caps + `truncated`.
   - **summary:** from that same filtered list:
     - `initial` = text of the **first** remaining item with `role == "user"`
       (first genuine user turn post strip-injected; not Activity
       `initialPrompt`, which is live-machine only and wrong for finished runs).
     - `recent` = last **4** filtered messages, role-agnostic among
       user/assistant.
     - If the initial user message also falls inside the last-4 window, still
       emit it once under `initial` and keep the window as-is (agents need the
       task framing even when the run is short).

Module home: `controlplane/conversation.py` (single function
`project_conversation_feed(..., shape=...)`). Do not read
`RunActivityProjection.initialPrompt` for this path.

**Token shape:** yes, fits hard-cap discipline cleanly.

| Field | Bound |
| --- | --- |
| `initial` | one message; same per-message `max_chars` tail-truncate + marker |
| `recent` | at most 4 messages; same per-message cap |
| response total | hard server cap; if over, shrink `recent` from the oldest edge first, never drop `initial` before recent tails; `truncated: true` when any trim applied |

Fixed cardinality (1 + ≤4) is cheaper and more predictable than feed defaults.
Response shape example:

```text
{
  shape: "summary",
  run_id,
  initial: { turn, role: "user", text } | null,
  recent: [{ turn, role: "user"|"assistant", text }, ...],  // ≤4
  truncated: bool
}
```

`initial: null` only when no genuine user MessageItem exists yet (pre-first-turn
or empty run).

**S2:** implement `shape` in the same slice as feed; unit-test both harnesses'
timeline fixtures for summary extract and cap behavior.

---

## 5. Package and module map (new)

### TypeScript (product plane)

```text
packages/controlplane/          # @tm/controlplane
  src/index.ts
  src/domain/                   # pure: receipt types, damping policy, envelope
  src/service/                  # promptFanout, watchRegistry, launchOrchestrator
  src/ports.ts                  # RunActionPort, ActivityReadPort, ...
  src/adapters/                 # RunManagerActionAdapter, ...
  src/server/controlplaneRouter.ts
  fixtures/
```

Mount via `ContextMount` in `buildGateway`. Import only `@tm/controlplane` barrel
from gateway.

### Python (data plane + skins)

```text
api/src/transport_matters/controlplane/
  __init__.py
  service.py          # facade: principal in, verbs out
  grants.py           # mint, digest, resolve, revoke
  audit.py            # control_plane_actions writer
  conversation.py     # timeline filter + caps
  gateway_client.py   # typed private HTTP client
  principal.py        # Principal types
  errors.py           # not_found, forbidden, busy_gateway, delivery_failed

api/src/transport_matters/api/v1/controlplane_routes.py   # thin REST
# MCP app factory module colocated; mounted in main.create_app

api/migrations/versions/0012_control_plane_grants.py
api/migrations/versions/0013_control_plane_actions.py
# focused test modules; do NOT extend session/test_migrate.py (693 LOC)
```

Home MCP writers: public functions on seeder facade; no private Codex TOML
cross-imports (`api/CLAUDE.md`).

---

## 6. Envelope contract (single source)

Cross-plane string constants, mirrored TS/Python with conformance test:

```text
PROMPT_ENVELOPE = "[tm from {actor_short} «{label}»] {body}"
WATCH_ENVELOPE  = "[tm watch] {summary_line}"
```

Actor short = first 8 of run_id (or `human`). Label from grant/roster name.
Always on for delivered prompts and watch nudges.

---

## 7. Seven-slice plan (refined)

Order preserved from scout B with placement baked in. Dependency: identity
before skins; observe before agents can act usefully; watch before prompt
value; launch last among verbs; integration proves the loop.

| Slice | Name | Deliverables | Depends | Proof |
| --- | --- | --- | --- | --- |
| **S1** | Identity + grants | `0012_control_plane_grants`; mint in prepare path; home MCP seed both harnesses; resolve dependency; revoke on release; grant option on capture RPC | — | seed round-trip Claude+Codex; source home byte-unchanged; resolve; revoke kills token; granted launch fails closed without capture RPC / no StubCaptureAdapter |
| **S2** | Observe + audit substrate | Python `controlplane/` package; `conversation` with `shape=feed|summary`; `roster`/`workspace_summary` via gateway activity + DAO; `0013_control_plane_actions` + audit writer | S1 (principal types) | timeline fixtures both harnesses (feed + summary extract); busy_gateway; caps/truncated; migration focused tests |
| **S3** | Twin skins | MCP SDK dep; `/mcp` mount order; REST `controlplane_routes`; bearer on agent paths; human principal on REST | S1, S2 | contract tests: schemas, skins logic-free, SPA does not swallow `/mcp` |
| **S4** | Watch engine | `@tm/controlplane` package + router; watch registry; Activity triggers; damping; PTY inject port (resultful, used for watch lines); Python watch/unwatch proxy + audit | S1–S3, Runtime inject base | unit damping; delta→nudge; unsubscribe; process death clears subs |
| **S5** | Prompt | multi-target inject; nudge vs interrupt (harness fixtures for break+settle); dispatch_id; receipts; envelope; audit | S4 inject port | partial fan-out receipt; interrupt≠terminate; envelope always present |
| **S6** | Launch + manage + canvas adopt | launch with grant; stop; interrupt; `launch_kind=controlplane`; canvas `adoptRun` + activity reconciler; optional name/first_prompt | S1, S5 | director launches observer peer; pane appears without browser POST create; stop revokes grant |
| **S7** | Integration + taxonomy | end-to-end: granted spawn → `workspace_summary` → prompt peer → receipt + audit row; error taxonomy hardening; packaged gateway wheel | S1–S6 | CONTROLPLANE.md testing §; `just check` + `just test` |

**REST cutover (scout A decision 9):** low-level `/v1/runs` remains Runtime.
Canvas human launch may keep using Runtime create in v1; controlplane REST is
additive. Entitled human actions that need audit (palette prompt/stop) should
call `/v1/controlplane/*` so humans and agents share the audit shape. Full
canvas migration of spawn buttons is optional follow-up, not S6 blocker, as long
as **agent** launch adopts panes.

**Audit durability:** fail closed on audit insert **before** side effect for
mutating verbs when the pool is available; if insert fails after successful
delivery, log + metric (do not roll back PTY bytes). Prefer pre-insert
`accepted` row then update outcomes when that stays simple; otherwise one
completed row after fan-out with best-effort write and S7 metric assertion.

---

## 8. Explicit non-goals (v1)

- Second `RunManager` or resurrected Python run manager.
- Python re-derivation of Activity status / stalled / exited.
- Using terminal WebSocket as agent command channel.
- Durable watch subscriptions across API/Gateway restart.
- Cross-workspace director grants.
- Runtime mid-run grant toggle (revoke-only).
- CLI skin (`transport-matters ctl`).
- Server-authoritative full canvas layout graph.

---

## 9. Risks and spikes

| Risk | Mitigation |
| --- | --- |
| MCP SDK auth hook fit | S3 short spike; wrap at mount if needed |
| Codex interrupt bytes unknown | S5 capture fixtures before locking settle timers |
| Grant path blast radius across capture RPC | S1 only; typed non-metadata carrier; integration tests for rollback |
| `writer.py` / `dao_statements.py` near 700 | new modules only |
| Origin flip later moves REST | facade + client keep skins thin; document mount move |
| Canvas multi-client adopt races | adopt idempotent by runId; runKey deterministic `controlplane:{runId}` |

---

## 10. Decision log (summary)

1. **Placement (b):** Gateway action/watch engine + Python data plane + Python twin skins facade. Amends `CONTROLPLANE.md` architecture section; honors `docs/ARCHITECTURE.md`.
2. **Grant scope:** Activity `WorkspaceId` (`slug/hash`).
3. **Token storage:** SHA-256 digest in Postgres; raw only in overlay home; delete = revoke.
4. **Watch:** Gateway registry + Activity triggers + in-process PTY inject.
5. **Prompt:** resultful Runtime inject; multi-target receipts; interrupt ≠ terminate.
6. **Canvas:** `launch_kind=controlplane` + `adoptRun` via activity stream; no browser create POST for agent launches.
7. **Slices:** S1→S7 as table above; observe and identity before push/action.
8. **Summary primitive:** v1 yes; `conversation(run_id, shape="summary")` over the same `project_timeline` → MessageItem → text filter as feed; initial = first genuine user MessageItem; recent = last 4; not a parallel projector and not Activity `initialPrompt`.

---

## 11. Anchors reused (checklist)

| # | Anchor | Role in this design |
| --- | --- | --- |
| A1 | `buildGateway` / `ContextMount` | Mount `@tm/controlplane` |
| A2 | `runGatewayProcess` one RunManager | Inject same instance |
| A3 | `RunRouteProxy` | Pattern for typed gateway client + degrade |
| A4–8 | `RunManager`, runtimeRouter, PtySession | create/terminate/inject |
| A9–10 | canvas transport + terminal socket | human path only; adopt separate |
| A11–17 | Capture RPC, prepare_captured_run, home seeders | grant mint + MCP seed |
| A18 | run id / lifecycle workspace | grant.workspace_id source |
| A19–20 | Alembic, DAO conventions | grants + actions tables |
| B | `project_timeline`, MessageItem, turn_index | conversation feed + summary shapes |
| B | Activity projection + tmEvents | roster state + watch triggers |
| B | `main.create_app` mount order | `/mcp` before SPA |
| B | launchKinds | extend with controlplane |

No alternate PTY, no second activity machine, no parallel home preparation.
