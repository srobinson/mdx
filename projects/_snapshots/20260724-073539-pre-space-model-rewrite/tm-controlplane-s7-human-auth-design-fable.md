# Design: Human principal for the control plane (S7 human auth)

Independent design, fable, 2026-07-12. Grounded read-only against main `e05373b`
(tree pristine). Companion to `~/.mdx/projects/tm-controlplane-scout-s7-integration.md`.

## Summary

Extend S1's one framework — bearer → resolver → principal — with a second actor kind,
`human`, backed by a per-boot desktop-issued local token whose digest lives in the same
grant table. No new auth middleware, no cookie machinery, no UI-only route: the palette
becomes an ordinary authenticated REST client, and a human with the bearer can equally
drive MCP or curl. The one hard interlock: the moment human auth exists, ambient
grant-minting (`POST /v1/runs` with `controlPlaneGrant`, unauthenticated today) must be
gated, or the design secures the front door beside an open window.

## Threat model (drives everything)

TM is local, single-user, no-sudo. The adversary of interest is not a remote attacker; it
is the **captured agent**: a same-UID process on the same host with loopback network
access. Run-scoped tokens exist precisely to bound agents. Two consequences:

1. **Ambient trust is disqualified.** Loopback trust, same-origin trust, or "the SPA is
   local" would hand every captured agent human powers by dropping its bearer and calling
   unauthenticated. Human identity must be an explicit credential agents do not receive.
2. **Same-UID secrecy is honest defense-in-depth, not a hard boundary.** An agent can read
   any file the user can, including `~/.transport-matters`. Mitigations (0600, per-boot
   rotation, never in run homes/env) raise the bar from "ambient" to "deliberate
   exfiltration", and audit attribution makes abuse detectable. A hard boundary requires
   OS-sandboxing agents — out of scope, roadmap item.

## 1. Human principal identity

Today (`controlplane/models.py`): `ControlPlanePrincipal {run_id, role, workspace_id,
owner}`, minted only by `capture_rpc.py CaptureRegistry.resolve_control_plane_grant`,
which requires a **live capture lease** whose workspace matches the grant row.

Proposal: a small discriminated union sharing the fields every verb actually uses.

- `RunPrincipal` — today's dataclass, unchanged semantics (lease-bound liveness).
- `HumanPrincipal {subject: "local", role: DIRECTOR, workspace_id, owner: "local"}`.

Shared read surface (`role`, `workspace_id`, `owner`, plus a derived `actor` string) keeps
verb signatures untouched; the few places that genuinely need a run identity (watch
self-exclusion, watch registration) narrow on the union and reject humans explicitly.
`owner` composes for free: the gateway's ownership lane already defaults to `"local"`
(`runtimeRouter.ts DEFAULT_RUNTIME_OWNER`), which is the lane canvas runs and the
existing capture facts use, so `terminate_run`/`deliver_input`/`list` calls that take
`owner=principal.owner` work unchanged for a human.

Trust root: **desktop-issued local token, minted by the API at boot**, digest-persisted
(exact S1 discipline: raw exists only outside the DB, `tokens.py digest_run_bearer`).
Why this root and not the alternatives:

- *Same-origin/loopback trust*: disqualified by the threat model above.
- *OS keychain*: the API is a plain Python process launched from the CLI; keychain adds a
  platform dependency for a secret that still ends up readable by same-UID processes via
  the keychain API. No security gain over an 0600 file here, real portability cost.
- *Static bootstrap secret*: unrotated, tends to leak into shell history and configs.
- *Per-boot mint*: matches the process-resident philosophy the control plane already has
  (watch subscriptions, launch ledger die with the API); leakage is bounded by restart;
  revoke = delete row, identical to run grants.

Role is fixed `director` (the local operator owns the machine; a local observer-human is
meaningless). `workspace_id` = the instance's canonical workspace identity, so every
existing visibility check stays uniform. A future cross-workspace human is exactly the
spec's "wider grants over the same model", nothing special.

## 2. Credential on the wire, both skins

Same wire shape as runs: `Authorization: Bearer <token>` on REST and MCP alike.

The middleware change is almost nil, which is S1's design paying off:

- REST: `controlplane_auth.py require_control_plane_principal` is untouched — it already
  delegates to `app.state.control_plane_grant_resolver`.
- MCP: `controlplane_mcp.py ControlPlaneMcpAuthApp` resolves the bearer through the same
  resolver before the SDK hook, and `ControlPlaneTokenVerifier` passes the resolved
  principal through. Only nit: `ControlPlaneAccessToken.client_id/subject` are set from
  `principal.run_id`; they become `principal.actor`.
- The only real change: `grants.py ActiveControlPlaneGrantResolver.resolve` grows a branch
  on the grant row's actor kind — `run` rows keep the live-lease bind through the capture
  registry; `human` rows mint `HumanPrincipal` directly (a human's liveness is the row's
  existence, not a lease).

Storage: extend `control_plane_grant` (migration `0017`; table DDL currently
`0012_control_plane_grants.py`: `run_id text PRIMARY KEY, role, workspace_id,
token_digest bytea UNIQUE`). Rename `run_id` → `subject`, add
`actor_kind text NOT NULL DEFAULT 'run' CHECK (actor_kind IN ('run','human'))`, PK
`(actor_kind, subject)`. One table, one digest-lookup path, revoke-is-delete preserved.
Add a check rejecting `subject LIKE 'human:%'` when `actor_kind='run'` so the audit actor
namespace below cannot be spoofed by a crafted run id.

Lifecycle: `main.py lifespan`, after the grant store is ready — delete any prior human
rows for this workspace, mint, persist digest, hand off raw (below). Rotation per boot.

## 3. Authorization

Human = director: `action_policy.py _require_director` passes; observe/launch/manage/
prompt all work with zero per-verb changes. Two deliberate exceptions:

- **watch/unwatch reject human principals** with structured `invalid_request`
  ("watch delivers to a run PTY"). A human has no PTY; the palette already has a
  strictly better push channel — the workspace activity SSE the canvas consumes. Do not
  bend watch delivery into a second transport; that is UI-only logic by the back door.
- **Launch ledger keying**: `launch_service.py` keys replay entries and frozen audit by
  `principal.owner`. Human and director runs share `owner="local"`, so a director that
  learns or guesses the human's `dispatch_id` could collide with (identical intent:
  fetch the human's terminal receipt; changed intent: spurious rejection) the human's
  ledger entry. Key the ledger by `principal.actor` instead of `owner` — a one-line
  correctness fix that also makes the audit `find(actor, verb, dispatch_id)` and ledger
  agree on identity.

Grant interaction (bootstrap): human `launch(grant=director)` is the missing first-director
mint, through the already-shipped fail-closed path (`captured_run_context.py`). **Hard
interlock**: today the raw gateway spawn (`runtimeRouter.ts controlPlaneGrantFromBody` on
`POST /v1/runs`) accepts a grant with no authentication, so any same-host agent can curl
itself a director run right now. Ship, in the same slice: grant-carrying spawns on the raw
run surface require the human bearer (or arrive only via the principal-gated control-plane
launch verb). Grant-less spawns stay as they are — that surface's exposure predates this
design and is a separate hardening track.

## 4. ⌘K palette flow

The palette is an authenticated REST client, indistinguishable from curl:

1. API mints the token at boot and writes it to the instance run dir beside
   `manifest.json` (the ⌘K instance-discovery seam, `cli/instances.py`), file mode 0600,
   e.g. `human_bearer`. This directory is already the instance handshake surface.
2. The Electron main process (spawned by `transport-matters desktop`,
   `cli/desktop_cmd.py spawn_detached_electron`) reads the file and exposes the token to
   the renderer via a preload bridge — held in memory, never `localStorage`, never a
   cookie, never a query param.
3. `@tm/core transport` attaches `Authorization: Bearer` to `/v1/controlplane/*` requests
   only (scoped injection; the rest of the API keeps its current story).
4. Plain-browser fallback (no Electron): `transport-matters ctl token` prints the bearer
   for explicit paste; palette holds it in memory for the session. Jupyter-style one-time
   handoff URL → session is a later UX slice if paste grates; it adds CSRF/rebinding
   surface and is not needed for v1.

Why this is not a backdoor: same-origin gives the palette nothing — authorization comes
from presenting the same credential class every other client presents, resolved by the
same resolver, audited by the same writer. Anything the palette can do, `curl -H` can do.

## 5. Audit actor

`control_plane_action.actor` is already a plain text column designed for both actor kinds
(spec § Attribution: "actor (run_id via MCP, human via REST)"). Runs keep `actor =
run_id`; humans write `actor = "human:local"`. No audit migration: the
`(actor, verb, dispatch_id)` uniqueness constraint and `action_builders.py` (4 sites,
`actor=principal.run_id` → `principal.actor`) carry over. The `human:` prefix is reserved
by the grant-table check in §2, so no run can ever mint an id that collides with the
human namespace. Prompt envelopes: `envelope.py format_prompt_envelope` gets sender ref
`"human"` and a display name (default `Operator`), so a prompted agent sees
`[tm from human «Operator» #…]` and knows replies cannot be prompted back to a run id.

## 6. Blast radius on S1–S6b

| Surface | Change |
|---|---|
| `controlplane/models.py` | principal union + shared `actor` property |
| `controlplane/grants.py` | resolver actor-kind branch; human mint/revoke store fns |
| Migration `0017` | grant table: `subject` rename, `actor_kind`, namespace check |
| `main.py lifespan` | boot mint + handoff file write/cleanup |
| `controlplane_auth.py` | none (interface holds) |
| `controlplane_mcp.py` | `client_id/subject` from `principal.actor`; else none |
| REST routes | none |
| `action_builders.py` | `actor=principal.actor` (4 sites) |
| `service.py` | watch/unwatch human rejection; `_resolve_actor_name` human branch; envelope sender |
| `launch_service.py` | ledger key `owner` → `actor` |
| `runtimeRouter.ts` / run spawn RPC | gate `controlPlaneGrant` behind the human bearer |
| Desktop (`desktop_cmd`/Electron main/preload) + `@tm/core transport` | token handoff + scoped header injection |
| Capture/home seeding, watch engine internals, S6b reconciler | untouched |

Test surface: extend `test_controlplane_skins.py` parity tests with a human principal;
seeding round-trip equivalent = mint-at-boot + resolve + revoke-kills-token; integration:
human REST launch(grant=director) → director MCP prompt → two audit rows with distinct
actors — which is exactly the S7a loop test with the bootstrap made real instead of
SQL-minted.

## 7. Security risks

- **Confused deputy / self-mint (the live one)**: unauthenticated `POST /v1/runs` +
  `controlPlaneGrant` lets any local agent mint a director today. Gated in this slice
  (§3). Without this, human auth is theater.
- **Same-UID token theft**: irreducible without agent sandboxing (roadmap). Mitigated:
  0600 handoff file, per-boot rotation, digest-only persistence, raw never in run homes,
  run env, logs, or the DB; audit rows make human-actor actions attributable and
  anomalies (human actions while the operator is away) detectable.
- **Renderer exposure**: preload-held in memory; no `localStorage`/cookie; a SPA XSS
  could still exfiltrate — CSP and the no-cookie choice keep the exposure to active
  compromise rather than persistent ambient credential.
- **DNS rebinding / CSRF**: neutralized structurally — there is no ambient auth to ride;
  a cross-site page cannot attach the bearer. Keep loopback binding + Host hygiene anyway.
- **Prompt-chain escalation** (human token drives a director which drives specialists):
  inherent to the product's delegation model; the controls are the always-on envelope
  attribution and per-action audit, unchanged from the spec.
- **Revocation gap**: delete row or restart; a runtime `revoke` verb stays in the spec's
  deferred list. Per-boot rotation bounds the exposure window meanwhile.

## Recommendation

One PR-sized slice, buildable independently of S7a: migration + resolver branch + models
union + audit/envelope actor + lifespan mint + handoff + spawn-grant gate, with the
palette header injection landing alongside (the palette UI verbs themselves are the
separate UI track). This unblocks S7b's canvas grant option (the option needs an
authenticated carrier) and turns the S7a loop test's SQL-minted director into a real
bootstrap.
