---
title: identity-matters v1 draft spec (IAM stub)
type: projects
tags: [identity-matters, im, iam, rbac, authn, authz, audit, stub, k8s, rust, draft]
summary: IAM product for the Helioy platform. v1 is a near-stub establishing the placeholder and intent: Unix peer-cred AuthN, single admin role, audit log via session-matters. v2+ gains teeth (OIDC, RBAC policies, role bindings, capability resolution). Rust library in v1; out-of-process daemon in v2+.
status: draft
project: identity-matters
confidence: medium
created: 2026-05-17
updated: 2026-05-17
related: [helioy-bus-rewrite-charter-draft, session-matters-foundation-draft, runtime-matters-kubelet-draft]
---

# identity-matters v1 draft spec (IAM stub)

## Draft caveat

Brainstorm artifact for `/linear-workflows` consumption. v1 is intentionally a near-stub. The point of shipping it now is to establish the boundary and lock the contract so v2+ can add real teeth without touching session-matters. Linear planning may rescope freely.

The name was previously used for the control plane product (now `session-matters`). It is now reserved for IAM in the strong sense (AuthN + AuthZ + audit).

## Summary

The IAM product. Owns the principal model (who you are), authorization (what you can do), and audit (what was done). v1 is a Rust library compiled into session-matters' daemon; v2+ extracts it into its own out-of-process daemon with real teeth.

v1 contract:
- AuthN: local OS user identified via Unix peer credentials on the session-matters socket
- AuthZ: single role (`admin`) for the local user; everything is allowed
- Audit: every authorized mutation in session-matters writes a row via the identity-matters audit interface

v1 is the smallest skeleton that proves the boundary holds. It's a placeholder with intent: the call site, the audit log, the trait shape, all locked. v2+ swaps the implementation behind the trait without callers changing.

## Why a stub now

Three reasons to ship v1 even though it's a near-no-op:

1. **Establish the call site.** session-matters' code paths must call into identity-matters today, even if the answer is always `yes`. Otherwise we'd retrofit AuthZ later, which is exactly the kind of debt that destroys real systems.
2. **Lock the trait contract.** The Principal / Action / Resource shape that v1 stubs is the same shape v2+ enforces. Designing it once with care is cheaper than designing it twice.
3. **Write to the audit log.** Even with no real AuthZ, an audit log of every mutation is immediately useful for diagnostics and forensics. The audit log is identity-matters' v1 deliverable.

## Goals

1. **Principal model that survives v2+.** v1 has one principal type (`Local(uid)`); the enum is open for extension.
2. **AuthZ trait that survives v2+.** The shape `authorize(principal, action, resource) -> Result<(), AuthzError>` is correct for v1 (always Ok) and for v2+ (real policy evaluation).
3. **Audit log that survives v2+.** A single audit row schema covering principal, action, resource, decision (allow/deny/error), timestamp. Schema is durable.
4. **No teeth, no false security.** v1 is explicit about being a stub. Documentation states clearly that AuthZ is not enforced.
5. **In-process for v1.** No new daemon. Just a Rust crate that session-matters depends on. v2+ extracts as needed.

## Non-goals

- OIDC, mTLS, token-based auth (v2+)
- RBAC policies, Role / RoleBinding model (v2+)
- Capability resolution (v2+; the `capabilities` field on session records remains empty in v1)
- Multi-user identity (v1 is single local user)
- Audit forwarding to external systems (v2+)
- A separate identity-matters daemon (v2+)
- A separate `im` CLI binary beyond an admin sub-tool (v1: CLI is minimal)

## K8s mapping

| K8s concept | identity-matters mapping |
|---|---|
| User / Group (kubeconfig) | Principal (v1: `Local(uid)`; v2+: OIDC-derived, etc.) |
| ServiceAccount | (Future v2+) Principals for non-human callers (controllers, workflows) |
| Role / ClusterRole | (Future v2+) Named collections of allowed actions |
| RoleBinding / ClusterRoleBinding | (Future v2+) Principal-to-Role assignment |
| RBAC admission controller | The `authorize(...)` call from session-matters into identity-matters |
| Audit policy + audit log | identity-matters' v1 audit log |
| TokenReview / SubjectAccessReview | (Future v2+) AuthN and AuthZ APIs at the IAM-product boundary |

## Operating model (v1)

```
session-matters (smd)
    │
    │  fn authorize(principal, action, resource) -> Result<(), AuthzError>
    ▼
identity-matters crate (linked in)
    │
    │  v1 logic:
    │    - if principal == Local(local_uid) → audit + Ok(())
    │    - else → AuthzError::UnknownPrincipal
    │
    └─► writes audit row via session-matters' sm-store
```

No separate process. session-matters' smd hosts identity-matters' code in its address space. The trait keeps the boundary semantic; the implementation is colocated for v1 simplicity.

v2+ flips this to an out-of-process daemon (`imd`) called via socket. The trait shape doesn't change; only the implementation behind it.

## Domain model

### Principal

```rust
enum Principal {
    Local(u32),                   // Unix uid from peer creds
    // Future:
    // Oidc(IssuerId, Subject),
    // ServiceAccount(SaId),
    // CrossMachine(MachineId, ...),
}
```

### Action

```rust
enum Action {
    Spawn,            // sm run
    Kill,             // sm delete agent
    List,             // sm get agents
    Read,             // sm get agent X / describe
    Logs,             // sm logs
    MailSend,
    MailRead,
    Nudge,
    Link,             // sm link
    Doctor,
    Daemon,           // sm daemon (start/stop)
}
```

### Resource

```rust
struct ResourceSpec {
    workspace: Option<String>,
    role: Option<String>,
    runtime: Option<RuntimeKind>,
    session_id: Option<Uuid>,
    labels: HashMap<String, String>,
}
```

For v1, the contents of ResourceSpec don't affect the decision. For v2+, RBAC policies can match on workspace, role, labels, etc.

### Decision

```rust
type AuthzResult = Result<Authorized, AuthzError>;

struct Authorized {
    principal: Principal,
    role: String,         // v1: always "admin"
    capabilities: Vec<Capability>,   // v1: empty; v2+: populated from policy
}

enum AuthzError {
    Unauthorized { principal: Principal, action: Action, reason: String },
    UnknownPrincipal,
    InternalError(anyhow::Error),
}
```

### Audit record

```rust
struct AuditRow {
    id: Uuid,                 // UUIDv7
    timestamp: DateTime<Utc>,
    principal: Principal,
    action: Action,
    resource: ResourceSpec,   // serialized as JSON in sqlite
    decision: AuditDecision,  // Allow | Deny(reason) | Error(message)
    session_ref: Option<Uuid>, // session_id touched, if any
    notes: Option<String>,
}
```

Audit rows live in session-matters' sqlite (in the `audit` table inside `sm-store`'s sqlite/ submodule). identity-matters' crate writes them through a trait that session-matters implements.

## v1 scope

| In scope | Out of scope |
|---|---|
| `im-core` crate: Principal, Action, Resource, AuthzResult, AuthzError, AuditRow types | OIDC, JWT, token issuance |
| `im-stub` crate: v1 implementation (always allow local uid, write audit) | RBAC policy model |
| `Authorizer` trait: `fn authorize(...)`. Implemented by im-stub in v1. | Role / RoleBinding storage |
| Audit log schema (in sm-store; im-core defines the row type) | Audit forwarding (syslog, SIEM) |
| Unix peer credential helpers (extract uid from socket connection) | Multi-user support |
| Documentation that v1 has no real teeth | Capability resolution that populates `capabilities` on sessions |

## Tech stack

Same workspace shape as session-matters. v1 may live in the session-matters repo as a sub-crate (`crates/im-core`, `crates/im-stub`) or as a separate workspace; Linear decides. Leaning sub-crate in session-matters' workspace for v1 simplicity, extracted to its own repo in v2+.

### Minimal dependencies

```toml
nix = { version = "0.29", features = ["socket"] }  # for peer cred extraction
uuid = { version = "1.9", features = ["v7", "serde"] }
serde = { version = "1", features = ["derive"] }
chrono = { version = "0.4", features = ["serde"] }
thiserror = "2.0"
async-trait = "0.1"
```

No sqlx in v1 im-* crates (the store is sm-store; im-core defines types only).

## Proposed crate layout (inside session-matters workspace for v1)

```
session-matters/
└── crates/
    ├── im-core/                     types and trait definitions
    │   └── src/
    │       ├── lib.rs
    │       ├── types.rs             Principal, Action, ResourceSpec, AuthzResult
    │       ├── audit.rs             AuditRow type + AuditSink trait (sm-store impls)
    │       ├── error.rs
    │       └── peer_creds.rs        Unix socket peer cred extraction (macOS + Linux)
    ├── im-stub/                     v1 implementation
    │   └── src/
    │       ├── lib.rs               Authorizer impl: always allow local uid + audit
    │       └── tests.rs
    └── ... (sm-core, sm-store, sm-daemon, sm-cli as already specified)
```

`sm-daemon` depends on both `im-core` (trait + types) and `im-stub` (the v1 implementation).

In v2+ extraction:
- `im-core` stays where it is (types and trait are the boundary)
- `im-stub` is replaced by `im-daemon` (its own binary)
- session-matters depends only on `im-core`; the daemon implementation is loaded via socket

## CLI surface (v1 minimal)

No standalone `im` binary in v1. identity-matters' surface is exposed through `sm doctor` (shows IAM stub status: principal model, current uid, "no real AuthZ enforced") and through `sm` audit query commands.

Future `im` CLI surface (v2+):

```
im
├── whoami                          show your current principal + role + capabilities
├── audit query [--principal P] [--action A] [--since T]
├── role list / get / create / delete (v2+)
├── role bind / unbind (v2+)
├── policy list / get / apply / delete (v2+)
└── completions <shell>
```

## Boundary contracts

### session-matters → identity-matters

```rust
// im-core
#[async_trait]
pub trait Authorizer: Send + Sync {
    async fn authorize(
        &self,
        principal: &Principal,
        action: Action,
        resource: &ResourceSpec,
    ) -> AuthzResult;
}

#[async_trait]
pub trait AuditSink: Send + Sync {
    async fn record(&self, row: AuditRow) -> Result<(), AuditError>;
}
```

`im-stub::StubAuthorizer` implements `Authorizer` for v1 (always allow local uid; record via AuditSink).

`sm-store::SqliteAuditSink` implements `AuditSink` (writes to the audit table).

`sm-daemon` wires these together at startup.

## Migration from helioy-bus

helioy-bus has no IAM. There's nothing to migrate. identity-matters v1 is greenfield.

## Dependencies

External: minimal (nix, uuid, serde, chrono, thiserror, async-trait).

Internal: none in v1. sm-store provides the audit table; im-core defines the row shape. The relationship is "im-core types are stored in sm-store" not "im-core depends on sm-store."

## Open questions for Linear planning

1. **Repo placement.** Sub-crate in session-matters workspace for v1, separate repo in v2+? Or separate repo from day one to signal product boundary?
2. **Audit storage location.** sm-store sqlite (v1) — easy. Separate sqlite under im-store (v2+) — cleaner. Migration path?
3. **Peer cred portability.** macOS uses `LOCAL_PEERCRED` / `getpeereid`; Linux uses `SO_PEERCRED`. Wrap in `im-core::peer_creds` with cfg-gated impls.
4. **Audit row schema stability.** v1 schema must accommodate v2+ richness (policy id, evaluation trace, denial reason). Reserve fields now.
5. **Principal extensibility.** Tagged enum is the obvious choice; v2+ adds variants. Ensure serialization is forward-compatible.
6. **What `sm doctor` shows.** Stub status surface: principal, role, capabilities (empty), "v1 stub: no real AuthZ enforced" warning. Specify the exact wording.
7. **Action enumeration.** Is `Action` an open enum (free-form strings) or closed? Leaning closed for v1; open enables v2+ custom actions without recompile but loses compile-time checking.

## Success criteria

1. session-matters' smd cannot perform any mutating operation without calling `Authorizer::authorize(...)` and writing an audit row.
2. `sm doctor` clearly states "v1 identity-matters is a stub; no AuthZ enforced".
3. The audit table contains a row for every spawn, kill, mail send, nudge, link operation.
4. The trait surface is stable enough that v2+ swaps `im-stub` for `im-daemon` without changing call sites.
5. Audit row schema accommodates v2+ richness without migration (reserved nullable columns).
6. macOS and Linux both extract peer creds correctly on the session-matters socket.

## Parent + sub-issue shape (for /linear-workflows)

**Parent:** "identity-matters v1: IAM stub establishing boundary + audit log"

**Sub-issues (4 workers):**

1. **im-core types + trait.** Principal, Action, ResourceSpec, AuthzResult, AuthzError, AuditRow, Authorizer trait, AuditSink trait. Peer cred extraction (macOS + Linux). Tests for serialization stability.
2. **Audit table + AuditSink impl in sm-store.** Schema + migration + `SqliteAuditSink`. Includes reserved fields for v2+ (policy id, evaluation notes, denial detail).
3. **im-stub.** `StubAuthorizer` always allows `Local(uid)` matching the daemon's effective uid; rejects everything else. Records to AuditSink. Tests covering all Action variants.
4. **Wire into sm-daemon + doctor surface.** smd integration: every mutating handler calls authorize before acting. `sm doctor` shows stub status. Integration test: a spawn ends up in the audit table.

Optional Phase-2 worker:

5. **Documentation: when to enforce.** Clear callout in the v1 README and `sm doctor` output that AuthZ is NOT enforced. Roadmap for v2+ (OIDC, RBAC, policy DSL).

## Related

- Charter: `helioy-bus-rewrite-charter-draft.md`
- Peer (consumer): `session-matters-foundation-draft.md`
- Peer (substrate): `runtime-matters-kubelet-draft.md`
