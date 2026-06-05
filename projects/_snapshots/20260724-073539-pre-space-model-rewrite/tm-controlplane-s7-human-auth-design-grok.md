---
title: S7 human REST auth model for the control plane (grok)
type: projects
tags: [transport-matters, control-plane, s7, auth, human-principal, design, grok]
summary: >
  Human is a first-class principal kind beside run in the same uncached bearer→digest→grant
  framework. Trust roots in a desktop/process-local operator root (never agent-visible);
  workspace-bound human director sessions share Authorization Bearer across REST and MCP.
  Origin/loopback alone is defense in depth, not identity. Biggest risk: confused deputy via
  human-token leakage to a loopback-capable agent.
status: active
source: >
  Independent design against pristine main e05373b6a4f5a101f1f4da95d499682e6bc8ee11;
  CONTROLPLANE.md; S1 tokens/grants/principal; controlplane_auth + MCP TokenVerifier;
  owners.py DEFAULT_OWNER; origin/trusted_hosts; scout s7 human REST gap; prior design notes
  (codex operator capability, fable loopback inject, grok explicit human principal).
confidence: high
created: 2026-07-12
family: grok
topic: tm-s7-authdesign
---

# S7 — Human principal auth for the control plane

Design only. Repo was read-only at `e05373b6a4f5a101f1f4da95d499682e6bc8ee11` (clean
`main`). This file lives outside the repo.

## 0. Problem and non-goals

**Problem.** S1 ships run-scoped identity only: bearer → SHA-256 digest →
`control_plane_grant` → live capture → `ControlPlanePrincipal{run_id, role,
workspace_id, owner}`. Both skins (`/v1/controlplane` REST and `/mcp`) resolve
that path only. A human driving the North Star ⌘K palette (twin client of the
director agent) has no legitimate principal. Same-origin UI access without a
principal would be a UI-only backdoor and violates principle 1 (twin skins, one
service) and principle 2 (identity is never self-declared).

**Spec debt.** CONTROLPLANE.md § Attribution already says audit actor is
`run_id via MCP, human via REST`, but shipped code always audits
`principal.run_id` and REST rejects missing run bearers.

**Non-goals for this design:** multi-tenant cloud IdP, OAuth, OS keychain UX,
junior human seats, cross-workspace director grants (already deferred), CLI
`ctl` skin details beyond “third client of the same credential model”, changing
grant roles beyond observer/director.

## 1. Principal identity

### 1.1 Types

Extend the identity vocabulary; keep one principal object at the service boundary.

```text
PrincipalKind = run | human

ControlPlanePrincipal:
  kind:         PrincipalKind
  actor_id:     str          # run: run_id; human: "human:{owner}" (stable)
  role:         observer | director
  workspace_id: str          # canonical workspace key (same as S1 grants)
  owner:        str          # today always DEFAULT_OWNER "local"
```

Compatibility for S1–S6b call sites during migration:

- `run_id` property: for `kind=run` returns `actor_id`; for `kind=human` is
  absent or raises in typed accessors (prefer explicit `actor_id` in new code).
- Service methods keep taking one `ControlPlanePrincipal`; they never see a raw
  token (principle 2 unchanged).

### 1.2 How a human is identified (extends S1)

| Step | Run (S1, unchanged) | Human (S7) |
| --- | --- | --- |
| Mint | At grant-enabled capture prepare | Desktop/operator mint of a **workspace-bound human session** |
| Persist digest | `control_plane_grant.token_digest` + run_id | Human grant row (see §1.3); digest only |
| Raw bearer location | Run home MCP seed only | Desktop main / HttpOnly session only; **never** run homes or agent env |
| Resolve | digest → grant → live capture lease | digest → human grant → owner+workspace still valid (no capture required) |
| Principal | kind=run, actor_id=run_id, role, workspace, owner | kind=human, actor_id=`human:{owner}`, role=director, workspace, owner |
| Revoke | delete grant row | delete human grant row / expire session |

Humans are **not** fake runs. They do not require a capture lease. They **do**
use the same digest lookup, uncached per-request resolve, and role/workspace
fields so authorization and audit stay one framework.

### 1.3 Storage shape

Prefer one grant surface with a kind discriminator over a parallel half-auth.

Option A (recommended): extend grant persistence

```text
control_plane_grant  (evolve)
  principal_kind  text NOT NULL  -- 'run' | 'human'
  actor_id        text NOT NULL  -- run_id or human:{owner}
  role            text NOT NULL
  workspace_id    text NOT NULL
  owner           text NOT NULL  -- denormalize; today always local
  token_digest    bytea NOT NULL UNIQUE
  expires_at      timestamptz NULL  -- optional for human sessions; NULL for run
  -- run-only: capture liveness still checked via CaptureLeaseRegistry
```

Option B: sibling table `control_plane_human_grant` with identical resolve
contract. Acceptable if migration risk on the live run-grant table is too high;
resolve still fans in through one `ControlPlaneIdentity.resolve(bearer)`.

**Workspace binding.** Mirror run grants: one human session bearer is bound to
one `workspace_id`. The canvas already opens per workspace; mint or select the
session when the canvas/palette binds that workspace. Avoids rewiring every
service method to take a free-floating workspace override (blast radius).

**Human role.** For S7 single-user: human sessions are always `director`.
Observer-class human seats are a later product (NORTHSTAR junior seat), not this
slice.

### 1.4 Trust root (mechanism and why)

| Candidate | Verdict |
| --- | --- |
| Pure same-origin / loopback trust as identity | **Reject as primary.** Local agents can forge Origin/Host-looking traffic to the loopback server; CORS does not apply on same-origin rebinding paths. `trusted_hosts` and `require_http_origin` stay as **defense in depth**, not principals. |
| OS keychain as sole root | Defer. Good for multi-device later; overkill and asymmetric for REST+MCP mint paths on single-user loopback. |
| UI-only unauthenticated REST | **Forbidden.** UI-only backdoor; director cannot share the path. |
| **Desktop-issued local operator root → human session bearer** | **Adopt.** |

**Root of trust: process-local operator root.**

1. On API lifespan (or first desktop attach), ensure a high-entropy **operator
   root** exists under the TM home (e.g. `~/.transport-matters/operator/root`
   mode 0600) or is generated into process memory and handed only to the desktop
   parent via the existing `backend_started` / desktop IPC channel.
2. The operator root is **never** injected into capture `launchEnv`, harness
   client env, nested shells, manifests, or logs (same discipline as the codex
   design’s `TRANSPORT_MATTERS_GATEWAY_CONTROL_TOKEN` strip list).
3. Desktop **main** (not renderer) proves possession of the operator root to a
   mint endpoint and receives a **human session bearer** (workspace-bound).
4. Renderer / palette never sees the operator root. It receives only the session
   bearer via host injection (preload interceptor or HttpOnly cookie exchange).

Why this root:

- Matches product reality: single-user local desktop, loopback API, owner
  `local` already shared by spaces/sessions/runs.
- Mirrors S1: server mints, server stores digest only, skins resolve, clients
  never self-declare identity.
- Gives agents no path to “be human” unless they steal a human session secret
  that is never placed in their environment (see §7).

Browser-only dev (no Electron): developer sets an explicit env-held operator
root; the vite/shell proxy injects mint capability. No silent anonymous human.

## 2. Credential on the wire (both skins)

### 2.1 Wire format

One credential scheme for REST and MCP:

```http
Authorization: Bearer <token>
```

Token entropy: same class as `mint_run_bearer()` (`secrets.token_urlsafe(32)`).
Digest: existing `digest_run_bearer` (SHA-256) shared for both kinds (rename to
`digest_control_plane_bearer` if hygiene wants a neutral name; behavior
unchanged).

No second header for human. No “human means no Authorization”. Optional later:
HttpOnly cookie that the server turns into the same bearer resolve path for
browser convenience; the resolved principal is identical. Cookie is a transport
adapter, not a second identity system.

### 2.2 Auth middleware change

**Single resolve boundary** (today `resolve_control_plane_bearer` /
`ActiveControlPlaneGrantResolver`):

```text
bearer
  → digest
  → lookup grant by token_digest
  → if kind=run: require live capture + workspace match (S1)
  → if kind=human: require row present (and not expired); no capture
  → ControlPlanePrincipal
  → skins never see the token again
```

Concrete touch points:

| Surface | Change |
| --- | --- |
| `api/v1/controlplane_auth.py` | `require_control_plane_principal` stays; resolver returns dual-kind principal. 401 wording becomes “invalid or revoked control plane bearer” (already generic). |
| `api/v1/controlplane_mcp.py` | `ControlPlaneTokenVerifier.verify_token` uses the same resolve; `client_id`/`subject` = `principal.actor_id` (not always `run_id`). Human-via-MCP is allowed for twin-skin parity (CLI/director tools over MCP with a human session is legitimate; rare). |
| `ControlPlaneGrantStore.resolve` | Discriminate kind; or dual store behind one protocol. |
| `capture_rpc.resolve_control_plane_grant` | Run path only; human path never enters capture registry. |

Per-request, uncached (principle 2). Revoke still means delete/expire row → next
request dies.

### 2.3 Mint surface (trusted, not a skin verb)

Not one of the four product verbs. Small auth bootstrap owned by the identity
module:

```text
POST /v1/controlplane/auth/session
  proof: operator root (Authorization: Bearer <operator-root> OR private desktop channel)
  body: { workspace_id, owner? }
  → { bearer, principal_kind: "human", actor_id, role, workspace_id, owner, expires_at? }
```

Fail closed if operator root missing/mismatch. Rate-limit per owner. Audit the
mint itself (`verb=auth.session`, actor=`human:{owner}` or `system:operator`).

Desktop flow never exposes this to the renderer as a free-form “type any
workspace” without main-process workspace binding from the open canvas.

## 3. Authorization: human vs run

| Capability | Run observer | Run director | Human director (S7) |
| --- | --- | --- | --- |
| observe (summary/roster/conversation) | yes, grant workspace | yes | yes, session workspace |
| watch / unwatch | yes | yes | yes for subscribe registry; **delivery** see below |
| prompt / launch / manage | no | yes | yes |
| mint human session | no | no | no (operator root only) |
| grant on launch (`grant=observer\|director`) | no | yes | yes (human launches the first director cell) |

Rules:

1. **Same role gates.** `require_director` stays role-based, not kind-based.
2. **Same workspace bounds.** All existing `principal.workspace_id` /
   `principal.owner` filters in `read_store`, launch, manage, watch keys stay.
3. **No privilege escalation via kind.** A run bearer cannot become human by
   header tricks; kind is server-assigned at mint. A human session cannot claim
   another owner’s workspace without a mint for that binding.
4. **Watch delivery.** Today watch flushes via PTY nudge to the watcher run.
   For `kind=human`, subscribe may succeed for future push channels, but PTY
   delivery is a no-op or returns a structured “no agent delivery surface”
   (human already has canvas activity SSE). Do not invent a fake run_id to
   write a PTY. Prefer fail-soft: accept watch for API symmetry, skip PTY
   flush, audit `delivery=skipped_human`.
5. **Envelope sender.** Prompt envelope today uses `principal.run_id` and a
   resolved pane name. For human: `sender_run_id` becomes a stable ref
   (`human` or short actor token) and display name `"You"` / owner label —
   still terminal-safe via existing `_terminal_safe_text`.

S1 grants for agents are unchanged. Human is how the first director grant gets
launched from the palette (closes the scout “human grant bootstrap” gap once
the spawn option is wired; bootstrap is a product surface that **uses** this
auth, not a second auth system).

## 4. ⌘K palette flow (same-origin without backdoor)

```text
Desktop main
  |  holds operator root (from backend_started / file 0600)
  |  on canvas open for workspace W:
  |     POST /v1/controlplane/auth/session {workspace_id:W}
  |  receives human session bearer
  v
Preload / host request interceptor
  |  attaches Authorization: Bearer <human-session>
  |  renderer JS never reads operator root
  |  prefer HttpOnly cookie exchange so page JS cannot exfiltrate raw bearer
  v
Palette / canvas (same origin as API)
  |  calls /v1/controlplane/* exactly as a director agent would
  v
require_control_plane_principal → kind=human director principal
  → ControlPlaneService verbs
```

Why this is not a backdoor:

- Identity is still server-resolved from a minted digest-backed credential.
- A director agent with a run director bearer performs the same verbs over MCP
  or REST; capability parity holds.
- Origin/Host checks remain for CSRF/rebinding; they do not substitute for the
  bearer.
- Agents cannot mint human sessions without the operator root, which is stripped
  from their environment.

Dev-without-desktop: env operator root + explicit inject. Documented, not
implicit anonymous.

## 5. Audit actor

`control_plane_action.actor` stays `text NOT NULL` (migration 0013). No hard
requirement to add columns for S7; encode kind in the actor string.

| Principal | `actor` value |
| --- | --- |
| run | `run_id` (unchanged; existing rows stay valid) |
| human | `human:{owner}` e.g. `human:local` |

Optional later (eval nicety, not S7-blocking): `actor_kind` column or JSON
details. Idempotency unique on `(actor, verb, dispatch_id)` continues to work:
human and run cannot collide if human actors always use the `human:` prefix and
run_ids never take that prefix (enforce at mint).

Action builders switch from `actor=principal.run_id` to
`actor=principal.actor_id`.

Envelope text and audit text remain the delivered terminal-safe body (existing
S5 contract).

## 6. Blast radius on S1–S6b

| Area | Impact |
| --- | --- |
| `controlplane/models.py` | Principal gains `kind` + `actor_id`; tests/fixtures update. |
| `controlplane/tokens.py` | Shared mint/digest; maybe neutral names. |
| `controlplane/grants.py` + migration | Kind discriminator or sibling table; resolve dual path. |
| `capture_rpc.resolve_control_plane_grant` | Run-only; unchanged liveness semantics. |
| `api/v1/controlplane_auth.py` | Same Depends; richer resolver. |
| `api/v1/controlplane_mcp.py` | subject/client_id from `actor_id`; verifier unchanged shape. |
| `api/v1/controlplane_routes.py` | No per-route auth fork; optional auth.session route. |
| `action_builders.py` / audit | `actor_id`. |
| `service.py` envelope + actor name | Human display path; no run timeline lookup required. |
| `watch.py` delivery | Human skip-PTY branch; registry key stays (workspace, owner) + actor. |
| `read_store` / launch / manage | No ownership change; still principal.owner + workspace_id. |
| Home seed (Claude/Codex) | Unchanged; still run bearers only. |
| Canvas non-controlplane routes | Still owner query param world for sessions/activity; **out of scope** to retrofit all UI APIs in S7, but control plane palette path is bearer-first. |
| Gateway private tokens | Orthogonal; keep stripping discipline for operator root. |

**Tests to add (design-level list):**

- Resolve human bearer → principal kind=human; revoke kills next request.
- Run bearer never resolves as human; human never requires capture lease.
- REST + MCP both accept human bearer for observe and a director verb.
- Operator root missing/wrong → mint 401; agent env cannot read root (strip
  test).
- Audit row actor `human:local` for palette prompt; envelope not a run_id.
- Confused-deputy regression: forged Origin without bearer still 401 on
  controlplane routes.

## 7. Security risks

### 7.1 Biggest risk: confused deputy via human-token leakage

A loopback-capable agent process that obtains a **human session bearer** acts
with full director power and audits as human. That is worse than stealing a peer
run’s observer token.

Mitigations (required):

1. Never place human session or operator root in capture/launch/agent env,
   run homes, MCP seeds, or logs.
2. Prefer HttpOnly + SameSite cookie (or main-process header inject) so renderer
   XSS / agent-influenced page content cannot `fetch` the raw secret out of JS
   memory as easily.
3. Workspace-bind sessions; short TTL + refresh via operator root for human
   sessions (runs stay lifetime-of-capture).
4. Revoke-all human sessions on operator root rotation.
5. Constant-time digest compare (already hash equality on stored digest).

### 7.2 Privilege escalation

- Forging `kind` in a request body: impossible if kind is only set at mint.
- Using a run director bearer to mint human sessions: mint requires operator
  root, not director role.
- Cross-workspace: blocked by workspace_id on the grant row.

### 7.3 Same-origin / loopback assumptions

- Remain necessary but insufficient. Document explicitly in CONTROLPLANE.md
  § Identity when this lands: “Origin and Host are CSRF/rebinding defenses;
  control plane identity is always a resolved bearer.”
- Binding beyond loopback requires operator-conscious trusted_hosts **and**
  still bearer auth; never “open LAN = open human.”

### 7.4 Token leakage channels

- `backend_started` JSON must not log the operator root or human bearer at info
  level; desktop consumes then discards root from any renderer-visible payload.
- Transcript/wire capture of control plane HTTP should redact Authorization
  (existing redaction patterns for provider tokens).
- Palette network panel in devtools: cookie-httpOnly preferred over
  Authorization set from JS.

### 7.5 Watch / PTY confused paths

Do not deliver human watches to an arbitrary run’s PTY. That would be a
confused-deputy write channel.

## 8. Decision summary (lock candidates)

1. **Principal kinds:** `run | human` in one principal type; service sees only
   resolved principals.
2. **Credential:** same `Authorization: Bearer` on REST and MCP; digest store;
   uncached resolve.
3. **Trust root:** desktop/process-local operator root → workspace-bound human
   director session; not pure same-origin identity.
4. **Authz:** human S7 sessions are director in their workspace; role gates
   unchanged.
5. **Audit actor:** `human:{owner}` vs run_id; prefix non-collision.
6. **Palette:** host-injected session credential; twin client of director, not a
   backdoor.
7. **Biggest residual risk:** human session exfiltration to a local agent;
   mitigated by env strip, HttpOnly/host inject, TTL, revoke.

## 9. Suggested CONTROLPLANE.md amendment (when implementing)

Replace the implicit “human via REST” audit line with:

> Identity principals are `run` or `human`. Both authenticate with a
> server-minted bearer resolved per request to a principal. Run bearers are
> minted into grant-enabled capture homes. Human bearers are minted from a
> desktop-held operator root into workspace-bound director sessions. Origin and
> Host checks defend the loopback browser surface; they do not establish
> control-plane identity. Audit `actor` is `run_id` or `human:{owner}`.

## 10. Out of scope follow-ons

- Three-state spawn option in canvas UI (product glue on top of this auth).
- Junior human seats / observer humans.
- Cross-workspace human directors.
- Full retrofit of non-controlplane owner-query APIs to bearer auth.
- Cloud multi-user IdP.
