# Transport Matters Control Plane S7

Status: authoritative consolidation specification

Baseline: `transport-matters` main at `e05373b`

Scope: S7 authentication, S7b bootstrap, and S7a integration and audit proof

## 1. Outcome

S7 gives a local human operator the same control plane bearer protocol already used by captured runs. The human principal is workspace bound, has director authority, and reaches both REST and MCP through the existing bearer resolver. The trust root lives in the signed desktop application and the operating system keychain. No operator secret enters an agent process, run directory, renderer, command argument, environment variable, log, or browser storage.

S7 also closes the raw run creation path that currently accepts `controlPlaneGrant` without authorization. A request that creates an observer or director run must carry human authority at the public API boundary and an internal capability at the gateway boundary.

The build order is fixed:

1. S7 auth foundation: principal model, signed keychain issuance, resolver branch, grant migration, typed audit actors, and the `POST /v1/runs` gate.
2. S7b bootstrap: CLI option, Canvas three state setting, and complete plumbing to the gateway.
3. S7a integration and audit proof: both skins exercise the full supported loop, dispatch groups become queryable in tests, and the audit taxonomy is proved.

Each slice lands independently with `just check` and `just test` passing.

## 2. Authority and evidence

This specification consolidates:

- `CONTROLPLANE.md`
- `~/.mdx/projects/tm-controlplane-s7-human-auth-design-gpt.md`
- `~/.mdx/projects/tm-controlplane-s7-human-auth-design-fable.md`
- `~/.mdx/projects/tm-controlplane-s7-human-auth-design-grok.md`
- `~/.mdx/projects/tm-controlplane-scout-s7-integration.md`

Validated repository facts at `e05373b`:

- `api/src/transport_matters/api/v1/controlplane_auth.py:resolve_control_plane_bearer` is the shared REST bearer boundary.
- `api/src/transport_matters/api/v1/controlplane_mcp.py:ControlPlaneTokenVerifier.verify_token` uses the same resolver for MCP.
- `api/src/transport_matters/controlplane/grants.py:ActiveControlPlaneGrantResolver.resolve` resolves only live run grants.
- `api/src/transport_matters/capture_rpc.py:CaptureLeaseRegistry.resolve_control_plane_grant` binds a run grant to its active capture lease.
- `api/src/transport_matters/controlplane/models.py:ControlPlanePrincipal` can represent only a run.
- `api/src/transport_matters/session/migrations/0012_control_plane_grants.py` stores `run_id`, role, workspace, and bearer digest.
- `packages/runtime/src/server/runtimeRouter.ts:registerRunRoutes` accepts `controlPlaneGrant` on `POST /runs` without an authorization gate.
- `api/src/transport_matters/api/v1/run_proxy.py:create_run_proxy_mount` protects the public run route with origin validation only.
- `api/src/transport_matters/controlplane/launch_service.py:ControlPlaneLaunchService` forwards grant selection to the gateway and keys launch idempotency by the actor run.
- `api/src/transport_matters/controlplane/action_builders.py` and `watch_audit.py` write the actor as a plain run id.
- `www/packages/core/src/transport.ts:createCapturedRun` has no control plane grant option.
- `www/packages/canvas/src/model/capturedRunStore.ts:ensureRun` has no persisted grant setting.
- `api/src/transport_matters/cli/launch_options.py` exposes no grant option.
- `api/src/transport_matters/cli/start_cmd.py:run_start` always uses the request default.
- `api/src/transport_matters/captured_run.py:run_captured_run_on_local_tty` passes `control_plane_grants=None`, so the local CLI path cannot persist a selected grant today.
- `desktop/src/window.ts` already isolates the renderer and constrains navigation.
- `desktop/src/preload.cts` exposes no secret or keychain API.
- `desktop/electron-builder.yml` explicitly sets `identity: null`. The current application therefore cannot satisfy the locked code signature ACL.
- No keychain adapter, peer credential check, or reusable actor union exists. Searches covered `keychain`, `keytar`, `safeStorage`, `SO_PEERCRED`, `getpeereid`, `actor_kind`, and `HumanPrincipal`.

## 3. Locked security model

### 3.1 Principal model

Replace the run only principal with a tagged union. The discriminant is mandatory at every authorization, idempotency, and audit boundary.

```text
ActorKind = run | human

ActorRef
  kind: ActorKind
  subject: nonempty string
  key: "run:<subject>" | "human:<subject>"

RunPrincipal
  actor: ActorRef(kind=run)
  role: observer | director
  workspace_id: canonical workspace identity
  owner: owner scope

HumanPrincipal
  actor: ActorRef(kind=human)
  role: director
  workspace_id: canonical workspace identity
  workspace_root: canonical target path
  owner: owner scope
  display_name: Operator

ControlPlanePrincipal = RunPrincipal | HumanPrincipal
```

The human subject is a stable installation UUID associated with the desktop signing key. Human authority is always bound to one canonical workspace. A human principal cannot request observer authority because the operator needs director operations and a second human role adds no useful security boundary.

All run specific behavior narrows to `RunPrincipal` before reading a run id, active capture, session cwd, or reply target. Shared behavior uses `principal.actor.key`, `workspace_id`, `owner`, and `role`.

### 3.2 Bearer and resolver

Rename the generic token functions to `mint_control_plane_bearer` and `digest_control_plane_bearer`. Delete the run named path after all callers move. The opaque bearer remains `secrets.token_urlsafe(32)` and only its SHA 256 digest is persisted.

`Authorization: Bearer <opaque token>` is the sole application credential on:

- REST under `/v1/controlplane`
- MCP at `/mcp`
- public grant bearing `POST /v1/runs`

`controlplane_auth.py` remains the shared authentication middleware without behavioral changes. The resolver branches after digest lookup:

- `run`: require an active capture lease and preserve the current owner and workspace binding.
- `human`: require an unexpired grant, the requested workspace binding, the registered signing identity, and the active owner scope. No capture lease is required.

MCP uses `principal.actor.key` for client id and subject. REST and MCP receive the same principal object from the same resolver. Neither skin may implement a human special case beyond operation level policy.

Human bearer lifetime is 15 minutes at most. Issuance rotates the prior bearer for that installation and workspace. Desktop close, workspace switch, explicit sign out, and backend shutdown revoke it. Backend startup keeps the current `revoke_all` fail closed behavior.

### 3.3 Keychain issuance protocol

The desktop main process owns a nonexportable signing key held by the operating system keychain. Its ACL or designated requirement binds use to the Transport Matters application code signature. The renderer and preload bridge receive no key material and no bearer.

Issuance uses a one use local bootstrap channel:

1. The backend creates a random Unix domain socket under its private runtime directory. Parent permissions are `0700`; socket permissions are `0600`.
2. The backend emits a challenge containing protocol version, random nonce, backend instance id, owner, canonical workspace id, canonical workspace root, requested client kind, issued time, and expiry. The challenge expires after 30 seconds.
3. The desktop main process connects. Both sides verify the same local UID using platform peer credentials.
4. The desktop signs the complete canonical challenge with the keychain key.
5. The backend verifies the registered public key, application signing identity binding, nonce freshness, expiry, backend instance, owner, and workspace.
6. The backend consumes the nonce, removes the socket, persists the human grant digest and expiry, and returns the raw bearer over that socket once.
7. The desktop main process keeps the bearer only in memory.

Extract the permission, framing, timeout, and cleanup behavior from `api/src/transport_matters/shared_proxy/control.py:SharedProxyControlServer` and `SharedProxyControlClient` into a neutral private socket helper. Add peer credential verification there. This avoids a second local socket protocol implementation.

The desktop installs a request header hook scoped to the Transport Matters web contents id, exact application origin, and exact paths `/v1/controlplane`, `/v1/controlplane/*`, `/v1/runs`, and `/mcp`. It injects the in memory bearer and strips any renderer supplied `Authorization` value. Other origins and paths receive no credential. Navigation restrictions in `desktop/src/window.ts` remain active.

The public key and installation UUID are public identity material. Their registry may be stored under the private Transport Matters home. The signing key never leaves the OS keychain.

### 3.4 Accepted residual threat

Same UID process compromise can steal an in memory bearer, connect to a private local socket, or tamper with the local public identity registry. S7 accepts this residual risk. The design limits exposure with signature bound key use, one use challenges, peer UID checks, workspace binding, short bearer expiry, rotation, narrow header injection, and revocation.

### 3.5 Human operation policy

Human principals may call summary, roster, conversation, prompt, launch, stop, and interrupt subject to the current role and workspace checks.

`watch` and `unwatch` require a captured run because delivery needs a run reply path. `ControlPlaneService.watch` and `ControlPlaneService.unwatch` reject a human principal with the existing `invalid_request` error before entering the watch engine. Both skins expose the same error. This policy keeps `api/src/transport_matters/controlplane/watch.py`, already near the file limit, unchanged.

## 4. Persistence migration

Add one migration after `0016_action_dispatch_idempotency`.

### 4.1 Grant table

Transform `control_plane_grants` to:

```text
actor_kind   text        not null check actor_kind in ('run', 'human')
subject      text        not null check subject <> ''
role         text        not null check role in ('observer', 'director')
workspace_id text        not null
workspace_root text      null
owner        text        null
token_digest bytea       not null unique
expires_at   timestamptz null
primary key (actor_kind, subject, workspace_id)
check (actor_kind = 'run'
       and workspace_root is null and owner is null and expires_at is null)
   or (actor_kind = 'human'
       and role = 'director'
       and workspace_root is not null
       and owner is not null and owner <> ''
       and expires_at is not null)
```

Existing S1 rows are preserved exactly:

- set `actor_kind = 'run'`
- rename `run_id` to `subject`
- retain role, workspace id, and token digest
- set `workspace_root = null` and `owner = null`; the live capture continues to supply both for a run
- set `expires_at = null`

The store API changes from run keyed methods to actor keyed methods. `PreparedControlPlaneGrant` and `ResolvedControlPlaneGrant` carry `ActorRef`. Run preparation still mints a run grant before the launch boundary. Human issuance persists the canonical workspace root and owner with the same store, token digest, resolution, rotation, and revocation code. Service validation rejects a noncanonical root before persistence.

### 4.2 Audit table

Keep the existing `actor` text column and make its value the canonical typed actor key. Backfill every existing S1 through S6b action row from `<run_id>` to `run:<run_id>`. New rows use `run:<subject>` or `human:<subject>`.

The existing `(actor, verb, dispatch_id)` uniqueness constraint remains valid after the backfill. `LaunchLedger` and any in memory idempotency key use the same typed actor key. Gateway ownership remains the owner scope and does not become an actor key.

Downgrade removes the `run:` prefix and restores `run_id`. A downgrade must reject or delete human grants and human audit rows because the old schema cannot represent them. Upgrade and normal operation preserve all existing run data.

Migration tests must cover a fresh upgrade, seeded old run rows, seeded action rows, exact transformed values, uniqueness behavior, and upgrade then downgrade round trip.

## 5. Closing the grant self mint path

Authorization must survive to the final boundary that can mint a director run.

### 5.1 Public boundary

In `api/src/transport_matters/api/v1/run_proxy.py:create_run_proxy_mount`:

- `controlPlaneGrant = none` keeps current behavior.
- `observer` or `director` requires the normal bearer resolver.
- the resolved principal must be `HumanPrincipal`, director, and bound to the requested canonical workspace.
- derive that workspace with `captured_run_context.py:validated_workspace`; reject a body `workspaceId` that does not match the canonical `workspaceRoot` and `cwd`.
- origin validation remains defense in depth.
- client supplied internal capability headers are always stripped.

An agent run bearer cannot authorize raw grant bearing `POST /v1/runs`. Agent initiated delegated launch continues through the control plane `launch` operation, where current director and workspace policy applies.

### 5.2 Gateway boundary

Generate one random internal capability per supervised backend and gateway pair. Pass it only to the Python service and gateway process. Keep it out of renderer state, captured agent environments, run facts, and logs.

`api/src/transport_matters/api/v1/run_proxy.py:RunRouteProxy` injects the capability only after public human authorization. Its internal `create_run` method also injects it for a director launch already authorized by `ControlPlaneLaunchService`.

`packages/runtime/src/server/runtimeRouter.ts:registerRunRoutes` requires a constant time match of the internal capability whenever `controlPlaneGrant` is observer or director. Direct access to the gateway port therefore fails closed. External gateway mode must configure the capability explicitly or reject grant bearing spawns.

Capability ownership belongs in:

- `api/src/transport_matters/gateway_supervisor.py:GatewayPlan` and `plan_gateway_supervision`
- `desktop/src/gateway/gatewayProcess.ts:buildGatewayLaunch`
- `packages/gateway/src/main.ts:createDefaultRuntimeRouterDeps`
- `packages/runtime/src/server/runtimeRouter.ts:RuntimeRouterDeps`

The internal capability follows the accepted same UID residual threat. It supplies boundary continuity, not a new user credential.

## 6. S7 auth foundation

### 6.1 Reuse map

| Need | Reuse | Search result |
| --- | --- | --- |
| Shared bearer boundary | `controlplane_auth.py:resolve_control_plane_bearer` and `require_control_plane_principal` | Existing REST path found |
| MCP bearer resolution | `controlplane_mcp.py:ControlPlaneTokenVerifier` | Existing shared resolver found |
| Grant persistence | `controlplane/grants.py:ControlPlaneGrantStore` | Existing run store found; generalize it |
| Run liveness | `capture_rpc.py:CaptureLeaseRegistry.resolve_control_plane_grant` | Existing run branch found |
| Opaque bearer | `controlplane/tokens.py` | Existing mint and digest found; rename generically |
| Private local socket | `shared_proxy/control.py:SharedProxyControlServer` and `SharedProxyControlClient` | Existing permissions and framing found; extract neutral helper |
| Peer UID validation | none | Searches for `SO_PEERCRED` and `getpeereid` found no implementation |
| OS keychain signing | none | Searches for keychain adapters found no implementation |
| Desktop header scoping | `desktop/src/window.ts:createWindow` security policy | Existing web contents and navigation boundary found |
| Typed actor | none | Searches for `actor_kind`, `ActorRef`, and `HumanPrincipal` found no implementation |
| Final grant gate | `run_proxy.py:create_run_proxy_mount` and `runtimeRouter.ts:registerRunRoutes` | Both current boundaries found |

### 6.2 Exact changes

1. Add `ActorKind`, `ActorRef`, `RunPrincipal`, `HumanPrincipal`, and union helpers in `controlplane/models.py`. Replace direct `principal.run_id` reads with exhaustive narrowing.
2. Generalize `ControlPlaneGrantStore`, token names, prepared grants, and active resolution. Retain capture lease validation only in the run branch.
3. Add the migration in section 4 and update grant plus audit persistence tests.
4. Add `controlplane/operator_auth.py` with an `OperatorBootstrapService`, verifier port, challenge creation, one use nonce consumption, signature verification, human grant rotation, expiry, and revocation. Wire it in `main.py` beside the existing grant store and resolver.
5. Extract the private socket helper from `shared_proxy/control.py`; add peer UID checks and deterministic cleanup tests.
6. Add desktop main process modules under `desktop/src/operator/` for the keychain signer, bootstrap client, and in memory credential lifecycle. Keep the preload surface unchanged unless a status only value is required.
7. Add exact origin and path header injection from `desktop/src/window.ts` through one operator credential hook owned by the main process.
8. Update action builders, watch audit, launch idempotency, MCP subject identity, prompt actor labels, and logging to use `ActorRef.key`.
9. Reject human watch and unwatch in `ControlPlaneService` before the watch engine.
10. Implement both layers of the grant self mint gate from section 5. The public layer reuses `captured_run_context.py:validated_workspace` and never trusts a body workspace id by itself.
11. Update `CONTROLPLANE.md` with the principal union, human policy, credential flow, public and gateway gates, and accepted same UID risk.

### 6.3 Migration blast radius

The blast radius covers `0012` model assumptions, grant store queries, capture lease resolution, prepared launch data, action actor values, MCP subject ids, launch ledger keys, tests that assert raw run actor strings, and any fixtures that insert grants directly. Existing S1 rows and audit history are transformed in place as specified in section 4.

### 6.4 Tests and gates

Add focused proof for:

- migration preservation and round trip
- run bearer behavior unchanged after union conversion
- human issuance accepts one valid challenge exactly once
- expired, replayed, wrong workspace, wrong owner, wrong backend instance, wrong UID, unknown key, and invalid signature cases
- bearer rotation and every revocation trigger
- renderer cannot read the key or bearer
- header injection only for the allowed web contents, origin, and paths
- REST and MCP accept the same human bearer and resolve the same typed principal
- REST and MCP return the same `invalid_request` for human watch and unwatch
- audit and idempotency distinguish `run:x` from `human:x`
- public grant bearing run creation rejects no bearer, run bearer, wrong workspace human bearer, and expired human bearer
- gateway rejects grant bearing direct calls without the internal capability
- control plane director launch and authorized public human spawn cross the final gateway gate
- ordinary `controlPlaneGrant = none` run creation remains unchanged

Required slice gates:

```text
just check
just test
```

The signed application acceptance test must also prove the keychain ACL against the release signature. Unit mocks cannot satisfy this release gate.

### 6.5 REST and MCP symmetry

Both skins keep the existing authentication middleware and service delegation. The same human bearer, principal union, role rules, workspace rules, error enum, status mapping, and opaque error text apply. New auth tests extend the current branch free REST and MCP parity tests instead of creating a second human test harness.

## 7. S7b bootstrap

### 7.1 Reuse map

| Need | Reuse | Search result |
| --- | --- | --- |
| Grant option vocabulary | `packages/runtime/src/ports.ts:CONTROL_PLANE_GRANT_OPTIONS` | Existing type found; move to neutral contract package |
| Captured request model | `api/src/transport_matters/captured_run_models.py:CapturedRunRequest` | Existing field found |
| Gateway request parser | `runtimeRouter.ts:controlPlaneGrantFromBody` | Existing parser found |
| Canvas run creation | `www/packages/core/src/transport.ts:createCapturedRun` | Existing request owner found; option absent |
| Canvas run defaults | `www/packages/canvas/src/model/capturedRunStore.ts:ensureRun` | Existing state owner found; setting absent |
| Canvas setting interaction | `launcher/commandTypes.ts`, command row builders, and `CanvasCommandDispatcher` | Existing setting command pattern found |
| CLI launch option | `api/src/transport_matters/cli/launch_options.py` | Existing option owner found; grant option absent |
| CLI grant persistence | none | `run_captured_run_on_local_tty` explicitly passes `control_plane_grants=None` |
| CLI keychain access | none | Python CLI has no code signature bound key access |

### 7.2 Exact changes

1. Move `ControlPlaneGrantOption` and its value tuple to a browser safe `@tm/contract/controlplane` module. Runtime imports and reexports that definition. Core and Canvas import it from the contract package. Delete the runtime declaration.
2. Extend `www/packages/core/src/transport.ts:createCapturedRun` with `controlPlaneGrant` and serialize it with the exact wire field already consumed by the runtime router.
3. Add a persisted Canvas default with three values: `none`, `observer`, and `director`. A command center settings row cycles the value and announces the selected state. Each spawn captures the current value into its immutable request.
4. Thread the selection through `canvasActions`, `capturedRunStore.ensureRun`, core transport, Python proxy, and gateway request parsing. No layer may infer or silently upgrade the value.
5. Add `--control-plane-grant none|observer|director` to the shared CLI launch options and to both Claude and Codex captured launch entry points. Default is `none`.
6. Consolidate local CLI launch onto the captured run preparation seam so selected grants use the same persistence and final gateway authorization as Canvas. Remove the explicit `control_plane_grants=None` path.
7. For `observer` or `director`, the CLI requests one spawn authorization from the running signed desktop broker. The broker presents operator confirmation for an external CLI request, signs the backend one use challenge, and returns an ephemeral human bearer to the CLI over a private local channel.
8. The CLI holds that bearer only in memory for the spawn request, then discards it before the agent child starts. It never places the bearer in argv, environment, shell history, run facts, transcript, or logs.
9. If the signed desktop broker is absent, locked, unsigned, or declines confirmation, grant bearing CLI launch fails closed. `none` remains available.
10. Update help text and `CONTROLPLANE.md` so both launch surfaces explain that the setting controls the new run's authority.

### 7.3 Migration blast radius

S7b adds no database migration. It consumes the actor keyed grant table from S7 auth. Fixtures and tests that construct `CapturedRunRequest`, `EnsureRunOptions`, or core create options must include the new default or rely on a single shared `none` default. The contract move requires runtime, core, gateway, and Canvas import updates with no duplicate union declarations.

### 7.4 Tests and gates

Add focused proof for:

- contract package value and exhaustive parser agreement
- core serializes all three values and omits no explicit choice
- Canvas persists and cycles all three states
- each Canvas spawn captures the chosen value
- CLI parsing and help for both providers
- default `none` causes no auth bootstrap
- observer and director request broker confirmation and use the returned bearer once
- absent or rejected broker fails closed without starting a run
- no bearer reaches captured child argv, environment, facts, logs, renderer, or persistent storage
- public API and final gateway gates receive the same value
- both direct human spawn and control plane launch grant paths persist a resolvable run bearer

Required slice gates:

```text
just check
just test
```

### 7.5 REST and MCP symmetry

S7b changes launch inputs and leaves control plane verb semantics shared. REST and MCP `launch(grant=...)` continue to delegate to the same `ControlPlaneLaunchService`. Canvas and CLI use the public spawn boundary with the same human bearer scheme. Tests compare the resulting prepared grant and launched principal rather than only request JSON.

## 8. S7a integration and audit proof

### 8.1 Reuse map

| Need | Reuse | Search result |
| --- | --- | --- |
| Prompt integration | `api/tests/integration/test_controlplane_prompt.py` | Existing director prompt, receipt, audit, and revoke proof found |
| Launch integration | `api/tests/integration/test_controlplane_launch.py` | Existing scoped idempotent launch and audit proof found |
| REST skin | `api/v1/controlplane_routes.py` and current REST delegation tests | All nine operations found |
| MCP skin | `api/v1/controlplane_mcp.py` and current MCP delegation tests | All nine operations found |
| Dispatch identity | `controlplane/audit.py` and migration `0016_action_dispatch_idempotency` | Existing dispatch index and uniqueness found |
| Action construction | `action_builders.py` and `watch_audit.py` | Existing audit builders found |
| Full two skin loop | none | Existing integrations cover prompt and launch separately |
| Dispatch group query proof | none | No grouped query helper or full fanout assertion found |

### 8.2 Exact changes

1. Add a focused integration module for one migrated Postgres service graph, a controlled gateway boundary, the real bearer resolver, and both protocol skins.
2. Bootstrap a human director through the real backend issuance service with a deterministic signing verifier adapter. Keep OS keychain mechanics covered by desktop acceptance tests.
3. Use the same human bearer through REST and MCP to exercise summary, roster, conversation, launch, prompt, stop, and interrupt across both skins.
4. Launch a captured director with the requested grant, resolve its run bearer through a live test capture lease, and use that run principal for watch and unwatch across both skins.
5. Assert human watch and unwatch produce the same `invalid_request` through REST and MCP.
6. Query actions by `dispatch_id` and assert one dispatch group, one row per target, typed actor, verb, request envelope, target identity, terminal outcome, and error taxonomy. Keep this as an audit query and test helper unless a product caller requires a public API.
7. Add an audit taxonomy sweep for every mutating builder, including watch delivery. Observe operations remain unaudited under the current policy.
8. Extend the existing response parity matrix so every supported verb and every attainable control plane error has identical REST and MCP semantics.
9. Prove revocation on the next request for human and run bearers through both skins.
10. Update `CONTROLPLANE.md` status and evidence links after the full gates pass.

The full loop proves current control plane semantics. Real PTY actuation, durable causal damping, wire integrity, and durable exactly once launch remain parking lot item 22 and are outside S7.

### 8.3 Migration blast radius

S7a adds no database migration. It proves the S7 auth migration against the existing session, grant, action, dispatch, prompt, launch, and watch tables. Fixtures that previously asserted a raw actor run id must assert the typed actor key. Existing S1 through S6b rows remain available through the migration behavior in section 4.

### 8.4 Tests and gates

The full loop must prove:

- one human credential authenticates both skins
- both skins observe the same workspace scoped data
- both skins launch the same grant semantics
- prompt, stop, and interrupt produce equivalent receipts and audit rows
- a launched run bearer resolves only while its capture is active
- watch and unwatch work for a run director through both skins
- human watch and unwatch fail identically
- dispatch groups are complete and queryable by dispatch id
- actor taxonomy distinguishes human and run actions
- role, workspace, owner, expiry, outage, invalid bearer, revoked bearer, and service errors retain parity
- action uniqueness still prevents duplicate dispatch execution for both actor kinds
- audit envelopes contain safe metadata and no bearer, signing material, raw transcript bytes, or provider payload

Required slice gates:

```text
just check
just test
```

Record the exact commands and outputs in the implementation handoff. Passing focused tests alone does not complete S7a.

### 8.5 REST and MCP symmetry

The parity assertion is behavioral. For every operation, the test invokes the same service graph once through REST and once through MCP, then compares normalized success data, error code, terminal result, audit classification, and authorization decision. Transport framing may differ. Authority and product semantics may not.

## 9. Completion criteria

S7 is complete when all of the following are true:

- The tagged principal union is exhaustive and raw run id assumptions are removed from shared paths.
- Existing run grants and audit actions migrate without data loss.
- A signed desktop can obtain a short lived human bearer through a one use, peer verified bootstrap channel.
- The renderer and captured agents cannot receive operator signing material or bearer state through supported interfaces.
- REST and MCP use the same bearer resolver and demonstrate operation and error parity.
- Raw public grant bearing run creation requires a workspace bound human director.
- The gateway rejects grant bearing creation without its internal capability.
- Canvas and CLI expose `none`, `observer`, and `director`, default to `none`, and preserve the exact choice to the gateway.
- Human and run audit actors are unambiguous.
- The full loop and dispatch group proofs pass.
- `just check` and `just test` pass for every sub slice.
- `CONTROLPLANE.md` reflects the shipped behavior and leaves parking lot item 22 unchanged.

## 10. Owner decision

Choose the signed platform rollout before S7 auth implementation begins. The current Electron package is unsigned, and Linux has no direct equivalent of the macOS designated requirement assumed by the locked keychain ACL.

Recommendation: ship S7 human authority on a signed macOS build first and fail closed on unsigned development builds and unsupported platforms. Add other platforms only after each has an equivalent application identity bound key store and acceptance test. Code signing is a release dependency for S7 auth; notarization may follow the product distribution policy.
