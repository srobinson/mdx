# Scout: Control plane S7 (integration) — scope map + plan

Scouted main at `e05373b` (S1–S6b merged), tree pristine throughout, read-only.
Author: fable. Date: 2026-07-12.

## 1. What the docs scope as S7

CONTROLPLANE.md never names "S7". The slice numbering lives in the original scout plan
(`~/.mdx/projects/tm-controlplane-scout-observe.md`, ## Plan):

> "S7 integration + audit proof. The spec's end-to-end test: spawn with grant, agent calls
> `workspace_summary`, prompts a peer, receipt and audit row verified. Error taxonomy
> hardening (`not_found`, `forbidden`, `busy_gateway`, `delivery_failed`) across all verbs;
> dispatch-group queryability check."

The authoritative post-lock contract is CONTROLPLANE.md § Testing, Integration bullet:

> "Integration: the shipped prompt test covers director-grant → prompt → receipt plus audit
> row → revoke-denied retry against real grant SQL and a migrated Postgres, with the gateway
> behind the proxy hop stubbed. The full actuation-boundary test (real spawn,
> `workspace_summary`, prompt landing on a real gateway PTY) defers to slice #22 with durable
> causal damping."

Two other spec sentences turn out to define S7's real remaining work (see §2):

- § Identity: "UI surface: a three-state spawn option, off / observer / director." (unshipped)
- § Architecture, Skins: "REST under `/v1/controlplane`, consumed by the canvas UI and the
  palette." and § Attribution: "actor (run_id via MCP, human via REST)". (no human REST path
  exists)

**Parking-lot pull check (brief question):** CONTROLPLANE.md's integration scope explicitly
does NOT demand the parking-lot items. The actuation-boundary test is deferred to slice #22
by the spec itself; wire-store integrity and durable launch-exactly-once are unrelated to a
stubbed-gateway integration proof. Nothing needs pulling in.

## 2. End-to-end reality: wired vs unwired

### Wired (verified firsthand at e05373b)

- **Service, all verbs.** `controlplane/service.py` `ControlPlaneService` exposes
  `workspace_summary`, `roster`, `conversation`, `prompt`, `launch`, `stop`, `interrupt`,
  `watch`, `unwatch`; wired in `main.py lifespan` with grant resolver
  (`ActiveControlPlaneGrantResolver`), `ControlPlaneAuditWriter`, `ControlPlaneReadStore`,
  `ControlPlaneWatchEngine`, and the gateway via `run_proxy_mount.control_plane_gateway`.
- **Both skins, all nine operations.** REST `api/v1/controlplane_routes.py` (9 routes under
  `/v1/controlplane`) and MCP `api/v1/controlplane_mcp.py` (9 tools, streamable HTTP at
  `/mcp`, SDK auth with server-resolved principal). Not observe-only: prompt/launch/stop/
  interrupt/watch/unwatch all present on both skins.
- **Error taxonomy, largely enforced already.** `test_controlplane_skins.py` has
  `test_rest_status_map_exhausts_the_control_plane_error_vocabulary`, structured-envelope
  parity across skins, opaque unexpected errors, fail-closed auth, 503 identity-outage
  parity, and `test_route_and_tool_entrypoints_are_branch_free_delegators` (skins carry no
  logic — spec principle 1 enforced by test).
- **Identity chain.** Token minted inside the capture lease, `.mcp.json`/`config.toml`
  seeding (`controlplane/provisioning.py` + `cli/home_seeders.py`), per-request uncached
  resolve, revoke-kills-token (all S1, tested). Grant persistence is fail-closed in
  `captured_run_context.py`.
- **Grant spawn plumbing to the gateway boundary.** Gateway `POST /v1/runs` accepts
  `controlPlaneGrant` (`runtimeRouter.ts controlPlaneGrantFromBody`,
  `ports.ts CONTROL_PLANE_GRANT_OPTIONS`); `capture_rpc.py` binds and persists the grant;
  S6a threads frozen workspace identity end to end.
- **Launch loop closure.** Launch ledger idempotency + `first_prompt` delivery
  (`launch_service.py`, `launch_delivery.py`, `launch_ledger.py`) and the S6b canvas
  adoption reconciler (merged, all review findings resolved at `b32f570`).
- **Integration tests shipped.** `api/tests/integration/test_controlplane_prompt.py::
  test_director_prompt_persists_receipt_and_audit_row_and_revoke_denies_retry` (drives REST
  `/v1/controlplane/prompt` against migrated Postgres, real grant SQL, stubbed gateway
  behind `RunRouteProxy`) and `test_controlplane_launch.py::
  test_director_launch_is_scoped_idempotent_delivered_and_audited`.

### Unwired / missing glue

1. **Human grant bootstrap — the only real product gap.** No shipped surface lets the human
   mint the first director grant. `www/packages` contains zero references to
   grant or controlplane (no three-state spawn option; the canvas spawn call
   `@tm/core transport.ts createCapturedRun` sends no `controlPlaneGrant`), and the CLI
   (`cli/launch_options.py`, command modules) exposes no flag — only the internal
   `cli/_helpers.py` parameter (default `NONE`) exists. Today the first director can only be
   minted by hand-crafting `POST /v1/runs` with `controlPlaneGrant`. Until this ships, the
   north-star loop is not human-drivable; after it ships, everything downstream (director
   launches specialists with grants via `launch(grant=…)`) already works.
2. **Human REST auth story — decision needed.** The REST skin requires a run-scoped bearer
   (`controlplane_auth.py require_control_plane_principal`; there is no human principal
   type). The spec's "human via REST" audit actor and "consumed by the canvas UI and the
   palette" are therefore unimplementable as specced without a decision: implicit
   local/same-origin human principal vs a minted human token. Palette adoption of the
   control plane is a UI track of its own; the decision is the S7-blocking part only if S7
   is defined to include the palette (I recommend it is not — see Plan).
3. **Loop integration test.** No single test chains launch → observe (`workspace_summary`/
   `roster`/`conversation`) → prompt → stop, and no integration test drives the MCP skin
   over HTTP with real grant SQL (MCP coverage is colocated contract-level). Watch has unit
   coverage only (`test_watch.py`, `test_watch_corrections.py`); its PTY actuation is
   #22-deferred by the spec.
4. **Dispatch-group queryability check.** The only SELECT on `control_plane_action` is the
   audit writer's replay read (`audit.py`, keyed actor+verb+dispatch_id). Nothing proves a
   dispatch group is queryable as a group (spec § Attribution: "dispatch groups are
   queryable state"). A test-level SELECT-by-dispatch_id assertion is missing; no product
   query surface is required (judge/eval verbs are in "Deferred, not dropped").

## 3. Review deferrals: S7 vs parking lot

| Item | Origin | Disposition |
|---|---|---|
| Actuation-boundary e2e (real spawn/PTY) + durable causal damping (B1) | spec § Testing / S4–S5 reviews | **#22 parking** (spec-mandated) |
| Wire-store integrity (2 pre-S4 defects) | S4 max review, NOW.md | **#22 parking** (already recorded) |
| Durable launch-exactly-once (ledger survives API restart) | S6a review | **#22 parking** (already recorded) |
| 4-char run-ref collision in envelopes (L4) | S4 adjudication | **S7 doc pass** — a CONTROLPLANE.md wording call, zero code; settle it while S7 updates the doc |
| Audit awaits under global registry lock (N5), dual-source watch coupling (L3), bindingless-finalize catch-up (L8) | S4 adjudication | Parking (hardening, explicitly adjudicated defer) |
| `RunManager.write` hot-path cost | S5 max review | **Resolved** — verified queue-idle fast path in `RunManager.write` |
| S6a nits (fingerprint incl. presentation fields → resize 409; getattr typing; replay-tail re-derivation) | S6a review | Groom-as-you-touch |
| S6b residuals (candidates map never evicts terminal entries; persistent-404 re-burst per reconnect snapshot) | S6b review | Groom-as-you-touch (bounded, canvas-internal) |
| `service.py` at 697/700 | S6a review | **Resolved** — split landed; now 546 with `launch_service.py` 412 |

## Reuse Map

| S7 capability | Existing owner |
|---|---|
| Integration harness (migrated PG, real grant SQL, app lifespan, stubbed gateway behind proxy hop) | `api/tests/integration/test_controlplane_prompt.py` (fixtures: `TestDb` via `session/testing`, `create_app`, `RunRouteProxy`, `mint_run_bearer`/`digest_run_bearer`) |
| Launch stubbing for the loop test | `test_controlplane_launch.py` + `controlplane/launch_test_support.py` |
| MCP-over-HTTP driving | `api/v1/test_controlplane_skins.py test_mcp_observe_tools_delegate_principal_and_arguments` (transport helper pattern) |
| Watch registration in tests | `controlplane/watch_test_support.py` |
| Dispatch-group SELECT base | `controlplane/audit.py` (existing replay-read statement) |
| Error vocabulary exhaustiveness | `test_controlplane_skins.py test_rest_status_map_exhausts_the_control_plane_error_vocabulary` — extend, don't duplicate |
| CLI grant flag home | `cli/launch_options.py` (options owner) → `cli/_helpers.py control_plane_grant` (already accepts it) |
| Canvas spawn grant field | `www/packages/core/src/transport.ts createCapturedRun` body → gateway `runtimeRouter.ts controlPlaneGrantFromBody` (already parses it); UI option beside the existing spawn affordance in canvas actions |
| Grant option vocabulary (TS) | `packages/runtime/src/ports.ts CONTROL_PLANE_GRANT_OPTIONS` — browser side must get it via `@tm/contract`, never import `@tm/runtime` (packages/AGENTS.md boundary) |

None found: human REST principal (greenfield, decision-gated); dispatch-group product query
surface (correctly absent — deferred verbs).

## Quality Map

- LOC (all green): `watch.py` 670 — **30 lines under the hard cap; any S7 change touching it
  must split first**. `service.py` 546, `main.py` 508, `launch_service.py` 412,
  `controlplane_mcp.py` 393. Largest test file 575.
- Boundary: skins proven logic-free by test; MCP adapter's delegation mirroring of REST is
  inherent twin-skin shape, not duplication (shared errors/envelope modules already own the
  common parts).
- Dead code: S4's `needs_you` unconsumed-field note is moot — `watch.py` consumes it.
- Duplication watch item: the browser must not re-declare the grant option union when the
  UI option ships; it belongs on a `@tm/contract` subpath (see Reuse Map).

## Plan

**Decision needed (Stuart/orchestrator):** does S7 include the human-side surfaces? The
spec demands them ("UI surface: a three-state spawn option"; "human via REST") but the scout
slice definition is test/hardening only. Recommendation below assumes: bootstrap yes,
palette no.

**Split: two PRs.**

**S7a — integration + audit proof** (the scout-defined scope, stubbed gateway):
1. Full-loop integration test, both skins: mint director grant (SQL) → `launch` →
   `workspace_summary`/`roster`/`conversation` → `prompt` peer → `stop`, receipts + audit
   rows asserted after each action verb; REST via the existing httpx harness, MCP via the
   streamable-HTTP client pattern from the skins test. Watch/unwatch registration + audit
   asserted in-loop (delivery actuation stays #22).
2. Dispatch-group queryability test: SELECT by `dispatch_id` returns the fan-out group with
   per-target outcomes.
3. Error-taxonomy audit: sweep each verb's `not_found`/`forbidden` semantics (esp.
   cross-workspace run_id) into integration assertions where the loop test doesn't already
   cover them; the vocabulary/status-map exhaustiveness tests already exist — extend in
   place.
4. Doc pass: CONTROLPLANE.md status update + settle L4 (run-ref length in envelopes) as a
   wording decision.
   Gate: `just check` + full `just test` (integration tests need the migrated-PG fixture).
5. No production code expected except what the taxonomy sweep surfaces; if `watch.py` needs
   edits, split it first (700 rule).

**S7b — human grant bootstrap** (mechanical; plumbing exists to the gateway boundary):
1. CLI: three-state `--control-plane-grant` on the claude/codex launch commands
   (`launch_options.py` → `_helpers.py`, already parameterized).
2. Canvas: grant option in the spawn affordance → `createCapturedRun` body field →
   gateway (already parses). Grant union via `@tm/contract`.
   Gate: `just check`, `just test`, `pnpm --filter @tm/shell test` (full suite — UI/contract
   change).

**Not S7:** palette-on-REST + human REST principal (own slice after the auth decision); CLI
skin, cross-workspace grants, rename/breakpoint/spend verbs, judge/eval (spec "Deferred,
not dropped"); all #22 parking items.
