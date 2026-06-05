# S7 Human Control Plane Authentication Design

Status: proposed

Evidence base: repository head `e05373b6a4f5a101f1f4da95d499682e6bc8ee11`, inspected with a clean working tree on 2026-07-12.

## Decision

Add a first class `human` principal beside the shipped `run` principal. The initial human identity is a local operator installation, authenticated by a desktop key held in the OS keychain. The desktop proves possession of that key to the Python service over a private local bootstrap channel. The service then issues a short lived, workspace scoped, opaque bearer. REST and MCP carry both human and run credentials in the standard `Authorization: Bearer` header and resolve them through one authentication boundary.

Loopback, same origin, Electron, and possession of the rendered page provide transport context only. None establishes identity. No HTTP route may mint a human credential based on origin, Host, a cookie, or an unauthenticated bootstrap secret.

The first human role is `operator`. It has the four control plane verbs within one canonical workspace. Run grants retain `observer` and `director`. A human session never becomes a synthetic run and never receives a fake `run_id`.

## Current constraints

S1 through S6b already have the right shared boundary but assume one actor shape:

* `controlplane_auth.py` resolves every REST bearer through `app.state.control_plane_grant_resolver`.
* `controlplane_mcp.py` calls the same resolver before the MCP SDK verifier runs.
* `ControlPlanePrincipal` contains `run_id`, grant role, workspace, and owner.
* Authorization checks `observer` versus `director`.
* Action builders persist `principal.run_id` as `control_plane_action.actor`.
* Prompt envelopes, launch preparation, launch replay identity, and watch delivery all treat the actor as a run.
* The watch registry keys subscriptions by watcher run ID and delivers notifications to that run's PTY.

The auth middleware can be extended cleanly. The service layer needs an explicit actor model because an optional or invented human `run_id` would spread confused deputy bugs through every downstream assumption.

## Threat model

S7 should protect against:

* a remote web origin reaching the loopback API;
* DNS rebinding to the loopback listener;
* cross origin browser requests;
* an agent run attempting to acquire human authority;
* one principal selecting another principal, workspace, or role in request data;
* bearer disclosure through URLs, cookies, local storage, logs, error bodies, or agent homes;
* accidental credential reuse across backend instances or workspaces;
* replay of a desktop bootstrap proof;
* code paths that authenticate a human bearer and later treat it as a run bearer.

A process with full control of the same OS account can inspect application memory, replace user owned files, or drive the desktop. That is equivalent to control of the local operator for this single user phase. Team seats and remotely verified people will require an account or organization identity provider. The initial `human_id` therefore means local operator installation, rather than proof of a real world person.

## Principal model

Use a tagged union. Keep the common scope fields on both variants and keep run only fields on the run variant.

```python
ActorType = Literal["run", "human"]

@dataclass(frozen=True, slots=True)
class ActorRef:
    type: ActorType
    id: str

@dataclass(frozen=True, slots=True)
class RunPrincipal:
    actor: ActorRef              # {type: "run", id: run_id}
    grant: Literal["observer", "director"]
    workspace_id: str
    owner: str
    credential_id: str

@dataclass(frozen=True, slots=True)
class HumanPrincipal:
    actor: ActorRef              # {type: "human", id: human_id}
    role: Literal["operator"]
    workspace_id: str
    workspace_root: str
    owner: str
    desktop_instance_id: str
    credential_id: str
```

`ControlPlanePrincipal` becomes `RunPrincipal | HumanPrincipal`. Shared helpers own actor serialization, scope checks, display labels, and capability checks. Code that needs a watcher PTY or actor session must narrow to `RunPrincipal` first.

The canonical audit key is `run:<run_id>` or `human:<human_id>`, produced by one helper. The tagged fields remain separate in durable storage. The string form is for logs, SDK subjects, and in memory keys.

The human ID is a random installation UUID created once by the desktop and associated with its keychain key. The display label is mutable presentation data, such as `Local operator`, and carries no authority. Future seat identity can replace the installation subject while preserving the `human` principal type and audit schema.

## Trust root and bootstrap

Name: keychain backed desktop operator handshake.

On first desktop setup, Electron main creates an operator signing key. The private key is stored in the platform credential store with application access control. The public key and human ID are registered in the Transport Matters home. Production must fail closed when the keychain key is unavailable. Development can have an explicit development identity, stored under a separate profile and visibly marked. Production must never fall back to the development path.

The Python service exposes a local bootstrap channel in its runtime directory. Prefer a Unix domain socket with mode `0600` and peer credential checks. On platforms where the service is a direct child and the socket is unavailable, an inherited anonymous pipe can carry the same protocol. A loopback HTTP endpoint is excluded.

Handshake:

1. The backend creates a random backend instance ID and a one use nonce.
2. It sends a challenge containing the nonce, backend instance ID, canonical workspace ID, owner, requested client kind, and expiry.
3. Electron main signs the complete challenge with the keychain key.
4. The backend verifies the signature, authorized public key, peer OS user, nonce freshness, workspace, and backend instance.
5. The backend mints a 256 bit opaque bearer with a `tmh_` prefix, stores only its SHA 256 digest in memory, and returns the raw bearer over the private channel.
6. The nonce is consumed. The bearer expires at desktop close, backend shutdown, workspace switch, or a bounded maximum lifetime. Renewal repeats the signed challenge.

The private key proves the approved desktop installation. The private local channel prevents the bootstrap credential or issued bearer from appearing in HTTP logs, URLs, renderer state, or process arguments. Peer user verification and file mode are defense in depth. The signature remains the authority.

The human credential store is process resident. Its record contains digest, credential ID, human ID, role, workspace ID, workspace root, owner, desktop instance ID, issued time, and expiry. Backend restart clears all human sessions. Audit rows remain durable.

Run grant persistence and active capture checks remain as shipped. A generic credential resolver sits above the two mechanisms:

```text
opaque bearer
  -> parse type prefix
  -> hash once
  -> run grant plus active capture, or human session plus expiry
  -> tagged ControlPlanePrincipal
```

The prefix accelerates routing and makes mistakes visible. The server record remains authoritative. Both credential classes need 256 bits of entropy and constant time digest comparisons where an in memory comparison occurs. Rename `digest_run_bearer` to the generic `digest_control_plane_bearer`.

## Credential on the wire

Both skins use exactly:

```http
Authorization: Bearer <opaque credential>
```

Run credentials can adopt a `tmr_` prefix during this pre release migration. Human credentials use `tmh_`. There is no cookie, query parameter, alternate human header, implicit desktop flag, or body field that selects principal type.

`require_control_plane_principal` becomes a generic dependency. The MCP authentication wrapper uses the same resolver. The MCP SDK access token receives:

* `subject` and `client_id`: the canonical typed actor key;
* scopes derived from the resolved principal capabilities;
* the resolved tagged principal as private server context.

The current MCP verifier uses `principal.run_id` for subject and client ID. That must change before a human token reaches MCP. REST and MCP contract tests must prove that the same human credential resolves to the same principal and authorization result on both skins.

The hidden palette credential should remain dedicated to the desktop session. If a human later needs an external MCP client, the desktop can explicitly issue a second short lived credential for the same human principal after another keychain handshake. The browser credential should never be copied into an MCP configuration, and no human credential may be seeded into an agent home. Agents continue to receive only their run scoped credentials.

## Authorization

Replace `require_director` with a central capability decision over principal type, authority, verb, and target workspace.

| Principal | Observe | Launch | Manage | Prompt | Watch |
|---|---:|---:|---:|---:|---:|
| Run observer | yes | no | no | no | yes |
| Run director | yes | yes | yes | yes | yes |
| Human operator | yes | yes | yes | yes | no in S7 |

The human operator is broad across verbs and narrow across scope. Its workspace ID, canonical root, and gateway owner are fixed during the desktop handshake. Request bodies cannot widen them. Target runs must still be visible in that workspace and owner. Launch workdirs must remain descendants of the trusted canonical root at the final actuation boundary.

An operator may choose `none`, `observer`, or `director` when launching a child because that delegates run authority already available to a director. A human token cannot mint another human token. Human credential issuance remains solely behind the desktop trust root.

`watch` remains limited to run principals for S7. Its shipped meaning is a process resident subscription whose notification is delivered into the authenticated watcher's PTY, with self exclusion by watcher run ID. A human has no PTY and no run ID. Faking either would violate the principal model. The canvas already consumes activity as a UI client. A later browser subscription transport can reuse the event facts but needs its own delivery and lifecycle contract.

Authorization failures use the existing structured `forbidden` response. Authentication failures remain `401` with `WWW-Authenticate: Bearer`. Resolver outages remain `503`. Expired or revoked credentials are indistinguishable from unknown credentials to the caller.

## Command palette flow

Electron main owns the bearer in memory. It must not expose the value through preload or renderer JavaScript.

1. Desktop main completes the keychain handshake after backend health and workspace identity are established.
2. It installs a request header hook on the dedicated Electron session.
3. The hook adds the human bearer only when all conditions match: the request belongs to the Transport Matters window, the scheme and exact origin match the backend, and the path is `/v1/controlplane` or `/mcp` and descendants.
4. The palette uses ordinary same origin fetch calls. The request reaches the existing authentication middleware with an explicit bearer.
5. The hook never injects the bearer into navigation, external URLs, run terminal traffic, generic `/v1` traffic, or responses.
6. Closing the window revokes the credential and removes the hook. A reload can reuse the same live desktop session. A workspace switch requires a new scoped credential.

This keeps the UI a normal authenticated client. The backend grants no authority because a request came from Electron or from the same origin. A browser page opened outside the authenticated desktop session receives `401`.

Header injection limits token exfiltration but cannot prevent a compromised renderer from exercising the operator's authority. The renderer therefore remains part of the trusted computing base for action integrity. Maintain the existing sandbox, context isolation, disabled Node integration, exact navigation origin, and external window denial. Add a strict Content Security Policy, prohibit remote scripts and unsafe evaluation, keep untrusted transcript or artifact HTML out of the application origin, and restrict the header hook to the main web contents ID.

Host allowlisting and CORS remain required. State changing REST calls from a browser should also validate an exact allowed Origin when the header is present. Authorization bearer semantics protect nonbrowser clients. No policy should treat a missing Origin as human identity.

## Audit actor

Migrate `control_plane_action` from one untyped `actor` field to explicit identity:

```text
actor_type          run | human
actor_id            run_id | human_id
actor_credential_id issuance/session identifier
actor_label         optional presentation snapshot
```

The dispatch uniqueness constraint becomes `(actor_type, actor_id, verb, dispatch_id)`. Existing rows migrate as `actor_type = 'run'` and retain the prior actor value as `actor_id`. The migration must use frozen literals.

Audit builders accept `ActorRef` or the complete principal and never read `principal.run_id` generically. Prompt envelopes distinguish senders, for example `[tm from human «Local operator» #abcd1234]` and `[tm from run a1b2 «Director» #abcd1234]`. A human envelope contains no reply run handle.

The credential ID gives incident response a revocable session boundary without storing a bearer digest in the action row. It also distinguishes two desktop sessions belonging to the same local operator. The audit label is explanatory only. Actor type and ID carry attribution.

## Blast radius through S1 to S6b

### Identity and persistence

* Add the tagged principal union and actor helpers in the identity model.
* Generalize bearer minting and digest naming.
* Keep the S1 run grant store and active capture resolver.
* Add a process resident human credential store and the desktop handshake service.
* Replace `control_plane_grant_resolver` with a generic credential resolver used by both skins.
* Revoke human credentials on desktop, workspace, and backend lifecycle transitions.

### Service policy

* Replace role only director checks with capability checks.
* Use `actor_key` for launch replay ownership. A shared gateway owner is insufficient once human and run callers coexist.
* Change normalized launch intent from `actor_run_id` to typed actor identity.
* Resolve a run launch root from its captured session and a human launch root from its authenticated workspace scope.
* Generalize prompt sender labels and envelopes.
* Narrow watch and PTY delivery paths to `RunPrincipal` at their public boundary.
* Preserve all workspace and owner filters in reads and gateway calls.

### Audit

* Migrate actor fields and the dispatch uniqueness constraint.
* Update prompt, launch, manage, watch, and watch delivery builders.
* Include credential ID for mutable action verbs.
* Keep observe calls free of action rows.

### REST and MCP skins

* Both accept the generic bearer and receive a resolved tagged principal.
* MCP SDK subjects and clients use typed actor keys.
* Both return identical authorization outcomes for each principal class.
* No skin contains human specific action policy.

### Desktop and Canvas

* Add keychain identity management and signed bootstrap in Electron main.
* Add exact request header injection without exposing the token in preload.
* Bind the token to the actual web contents, backend instance, origin, workspace, and lifecycle.
* Palette API calls move to `/v1/controlplane` as ordinary authenticated calls.

S6b canvas adoption remains service driven. A human launched run and a director launched run continue to produce the same launch activity and adoption behavior. The audit actor and ownership marker identify who initiated the action.

## Security analysis

### Confused deputy

This is the highest implementation risk. The shipped code equates authenticated principal with run. Adding nullable human fields would allow audit, prompt envelopes, watch delivery, launch roots, or replay ledgers to borrow a run identity accidentally. A tagged union, exhaustive narrowing, and one actor helper prevent that class. A bearer is always resolved before policy. Tool arguments and REST data never declare actor type.

Tests must send a run bearer through REST and a human bearer through MCP, then prove each keeps its original authority and audit actor. A token prefix that disagrees with its stored credential class must fail authentication.

### Renderer compromise and token leakage

This has the largest operational consequence because an operator can launch, stop, interrupt, and prompt every visible run. Keeping the bearer outside renderer JavaScript reduces theft but leaves action misuse possible after XSS. The primary defenses are a strict CSP, no remote code, sandboxed Electron, exact navigation, output encoding, path limited header injection, short credential lifetime, server side workspace checks, rate limits, and durable audit.

Never log Authorization, bootstrap challenges with signatures, or raw credentials. Error envelopes stay opaque. The bearer must not enter local storage, IndexedDB, cookies, crash metadata, analytics, clipboard, agent homes, or persisted Canvas state.

### Loopback and origin assumptions

Loopback only reduces network reach. Any local process can connect. Same origin only describes browser routing. Trusted Host middleware remains the DNS rebinding boundary, CORS controls cross origin browser reads, and the bearer authenticates the principal. The private signed handshake establishes the human credential.

HTTP on loopback leaves the bearer visible to sufficiently privileged local inspection. The single OS user threat model accepts this for S7. Remote binding, LAN access, team seats, or a reverse proxy require TLS and an account backed identity provider before human credentials are enabled.

### Privilege escalation

An observer cannot call launch, manage, or prompt. A director cannot request a human credential. An operator cannot widen workspace scope through a target or workdir argument. Human credential minting is absent from REST and MCP. Grant delegation at launch remains bounded to the existing run grant roles.

### Replay and lifecycle

Bootstrap nonces are single use and bound to backend instance, workspace, and expiry. Human bearers are also bound to that instance and workspace. Restart, close, expiry, revocation, or workspace switch kills them. A stale bearer returns the same `401` as an unknown bearer. Renewal issues a new credential ID and digest.

## Verification plan

Required security tests:

* REST and MCP accept valid human and run bearers through the shared resolver.
* Unknown, revoked, expired, wrong workspace, wrong backend instance, and prefix mismatched bearers fail closed.
* No cookie, query, body, Origin, Host, or Electron marker authenticates a caller.
* Run observer, run director, and human operator capability matrices are identical across skins.
* Human `watch` fails before registry access or PTY lookup.
* Human launch derives its root from authenticated scope and still passes the final filesystem confinement check.
* Run and human prompts produce correctly typed, terminal safe envelopes and audit rows.
* Dispatch IDs do not collide across actor types or actor IDs.
* Bootstrap proofs reject reuse, modification, expiry, wrong workspace, wrong backend instance, wrong key, and wrong peer user.
* Electron injects the header only for the intended web contents, exact origin, and control plane paths.
* Renderer code cannot read the credential through preload, storage, API responses, or injected globals.
* DNS rebinding Host tests, CORS tests, navigation policy tests, and credential redaction tests remain green.
* Closing the window and switching workspace revoke the credential immediately.

One integration test should launch the desktop trust boundary, call a REST action from the palette origin, call the equivalent MCP action with a human client credential, and assert one typed human actor in durable audit. A parallel run bearer test should prove the same operation remains attributed to the run.

## Rejected alternatives

### Same origin or loopback trust

These signals do not identify a human and remain vulnerable to local processes, renderer compromise, and configuration mistakes. They stay as transport defenses.

### Authentication cookie

A cookie would add CSRF and ambient authority to a service already standardized on bearer authentication. It would also diverge REST from MCP.

### Human as a synthetic director run

This would forge a session, create a fake watcher PTY, corrupt audit meaning, and let run specific service assumptions survive invisibly.

### Long lived bearer in local storage or settings

This creates an easy exfiltration path and survives beyond the desktop or backend session. The keychain key should be long lived. Bearers should be ephemeral.

### Unauthenticated HTTP bootstrap secret

A loopback mint route becomes the UI only backdoor the North Star excludes. The bootstrap belongs on a private channel and requires proof rooted in the desktop key.

## Ship criteria

S7 is ready when every control plane request resolves to a tagged principal, both skins use the same resolver and policy, the palette presents an ephemeral human bearer without renderer access, action audit carries explicit actor type and ID, run grants retain their current scope, and no HTTP or UI condition can mint or imply human authority.
