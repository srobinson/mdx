---
title: identity-matters v1 draft spec (IAM stub)
type: projects
tags: [identity-matters, im, iam, rbac, authn, authz, audit, stub, k8s, rust, draft]
summary: IAM product for the Helioy platform. v0.1.1 shipped 2026-05-17 as a standalone repo with three published crates (lilo-im-core, lilo-im-stub, lilo-im-store). Authorizer trait + Unix peer-cred AuthN + always-allow stub + im-owned SQLite audit. v2+ gains teeth (OIDC, RBAC policies, role bindings, capability resolution).
status: draft
project: identity-matters
confidence: medium
created: 2026-05-17
updated: 2026-05-18
related: [helioy-bus-rewrite-charter-draft, session-matters-foundation-draft, runtime-matters-kubelet-draft, berriai-litellm-agent-platform, helioy-im-codebase-2026-05, kubernetes-sigs-agent-sandbox, helioy-controller-conventions]
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

Audit rows live in identity-matters' own SQLite, owned by the `lilo-im-store` crate (default path `~/.im/audit.sqlite`). `SqliteAuditSink` is the built-in `AuditSink` implementation. session-matters consumes it by holding an `SqliteAuditSink` and passing it as `dyn AuditSink` to whatever `Authorizer` it wires. The identity store is sovereign over its data shape; consumers do not host identity rows. Supersedes the earlier sm-store-hosted plan; resolves open question 2.

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

v0.1.1 ships as a standalone repo at `github.com/littleorgans/identity-matters` with three published crates: `lilo-im-core` (types + traits), `lilo-im-stub` (v1 always-allow Authorizer), `lilo-im-store` (SQLite audit). The `lilo-` prefix is the crates.io publishable form; in-repo directory names stay short (`crates/im-core`, `crates/im-stub`, `crates/im-store`) with `[lib] name = "lilo_im_core"` smoothing the import path. Resolves open question 1.

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

## Crate layout (v0.1.1, standalone repo)

```
identity-matters/
└── crates/
    ├── im-core/                     [lib.name = "lilo_im_core"]
    │   └── src/
    │       ├── lib.rs
    │       ├── types.rs             Principal, Action, ResourceSpec, AuthzResult
    │       ├── audit.rs             AuditRow + AuditSink trait + AuditDecision
    │       ├── error.rs             AuthzError (5 variants incl. Audit { message })
    │       └── peer_creds.rs        Unix peer cred extraction (macOS + Linux)
    ├── im-stub/                     [lib.name = "lilo_im_stub"]
    │   └── src/
    │       ├── lib.rs               StubAuthorizer: allow local uid + record
    │       └── tests.rs
    └── im-store/                    [lib.name = "lilo_im_store"]
        └── src/
            ├── lib.rs
            ├── sqlite/
            │   ├── mod.rs
            │   └── audit.rs         SqliteAuditSink + _schema_version migrations
            └── migrations/
                └── 0001_audit.sql
```

Consumers (session-matters) depend on `lilo-im-core` (trait + types) and `lilo-im-stub` (v1 Authorizer) and `lilo-im-store` (SqliteAuditSink). All three publish to crates.io.

In v2+ extraction:
- `lilo-im-core` stays as the boundary (types + traits)
- `lilo-im-stub` is replaced by `lilo-im-daemon` (its own binary)
- session-matters depends only on `lilo-im-core`; the daemon implementation is loaded via socket

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

1. **Repo placement.** [RESOLVED 2026-05-18] Standalone repo from day one (`github.com/littleorgans/identity-matters`); v0.1.1 published.
2. **Audit storage location.** [RESOLVED 2026-05-18] Identity-owned SQLite via `lilo-im-store::SqliteAuditSink`. Sm-store does not host identity rows.
3. **Peer cred portability.** macOS uses `LOCAL_PEERCRED` / `getpeereid`; Linux uses `SO_PEERCRED`. Wrap in `im-core::peer_creds` with cfg-gated impls.
4. **Audit row schema stability.** v1 schema must accommodate v2+ richness (policy id, evaluation trace, denial reason). Reserve fields now.
5. **Principal extensibility.** [RESOLVED 2026-05-18] `Principal::Unknown { kind, raw }` with hand-rolled serde (`types.rs:28-122`) preserves unknown variants on round-trip. Test in `tests/principal_forward_compat.rs`.
6. **What `sm doctor` shows.** Stub status surface: principal, role, capabilities (empty), "v1 stub: no real AuthZ enforced" warning. Specify the exact wording.
7. **Action enumeration.** [RESOLVED 2026-05-18] Closed enum with exported `Action::ALL: [Self; 11]` (`types.rs:141-153`) for exhaustive iteration.

## External validation: BerriAI/litellm-agent-platform (2026-05-18)

The platform `BerriAI/litellm-agent-platform` (10 days old, MIT, 135 stars, A− grade) reviewed in `~/.mdx/research/berriai-litellm-agent-platform.md` (cm `019e34ba-881f-7971-924f-a978599015c2`) surfaces three identity-adjacent primitives Helioy v1 does not currently spec. Worth absorbing the v2+ seams now, even though v1 stays a stub, so v1 trait shapes accommodate v2+ without rework.

### Vault MITM as v2+ primitive (seam in v1)

The pattern: agents run with `bypass-permissions: on` but never see real credentials. Stub credentials in the env (`LITELLM_API_KEY=stub_xxx`), MITM on all egress via `HTTPS_PROXY=http://127.0.0.1:14322` (vault sidecar), vault swaps stubs for real keys on outbound TLS. The trap they ship into AGENTS.md: env merge order can silently leak real keys; explicit `delete merged["LITELLM_API_KEY"]` defence-in-depth is required after merging passthrough env into harness env.

For Helioy v1 identity-matters: leave a seam so v2+ can add an `im-vault` crate without changing session-matters call sites. Two concrete provisions:

1. `Authorizer::authorize` already returns `Authorized { principal, role, capabilities }`. The `capabilities: Vec<Capability>` field is empty in v1 but defined. v2+ vault uses capabilities to decide which credentials to swap on outbound TLS. The shape is right; the implementation is the v2+ work. **v0.1.1 ships `Capability { name: String }` as a placeholder; the discriminated-enum shape is NOT in v1.** v2 vault landing is therefore a breaking change to `lilo-im-core`. Lowest-cost fix before any external consumer pins: bump `Capability` to an enum with at least `Name(String)` and `CredentialAccess(CredentialId)` variants in a 0.2 release. Open a follow-up Linear issue.
2. `AuditRow` schema should include a `credential_resolution` nullable column from v1. v1 always writes NULL; v2+ writes the resolution decision (which stub was swapped, which real key was used, audit trail of the credential lifetime). **v0.1.1 reserves `policy_id`, `evaluation_trace`, `denial_reason` but NOT `credential_resolution`.** Known gap; land it in 0.2 alongside the `Capability` enum bump (`migrations/0002_credential_resolution.sql`). Open a follow-up Linear issue.

### HMAC-derived per-pod tokens (could be v1)

BerriAI's pattern: server holds a master secret; each pod gets a token derived via HMAC bound to `session_id`. The pod uses this token when calling back into the server; the server validates by recomputing the HMAC. No token storage on the server; no token transit secrets.

For Helioy: this is a simpler primitive than full vault MITM and applies directly to the rtmd↔shim auth that v1 currently doesn't have. Shim presents a derived token when reporting back to rtmd (ShimReady, ShimExit); rtmd validates against `session_id`. Prevents a rogue shim from forging exit reports for another session.

Decision pending: ship in v1 (small addition to rtmd↔shim handshake; identity-matters provides the HMAC primitive via `im-core::hmac` module), or defer to v2 (v1 trusts the local socket as the authentication boundary)?

**Did not ship in v0.1.1.** Deferred because the rtmd↔shim handshake has no implementation yet, so the primitive has no consumer. Revisit when runtime-matters lands its shim model. Reserve `lilo-im-core::hmac` as the future module path.

### CA bundle distribution (operational rule for v2+)

BerriAI ships the vault CA private key in their repo (`vault/ca.crt`). This is fine for a reference impl. Helioy's v2+ vault must NOT do this. Operational rule to spec now even though it's a v2 concern:

- Spec `im-vault::CaSource` trait at v1 (stub-only impl returning None) so v2+ pluggable backends (HSM, KMS, file with restricted permissions, env-var-pointer) implement the same trait without restructuring.
- CA private key never lives in the runtime-matters or session-matters repo, ever.
- CA cert (public) bundling into harness images via runtime-matters' Dockerfile is acceptable; private key never.

### Why this matters for v1

v1 identity-matters is a stub by design. The point of locking these v2+ seams now is that trait shapes propagate to call sites in session-matters. Retrofitting `capabilities` into the AuthzResult later means touching every call site; defining it now (even with empty default) costs nothing and prevents the retrofit. Same logic for AuditRow columns and the CaSource trait.

## v0.1.1 shipping additions (2026-05-18)

Five primitives shipped in v0.1.1 that the draft does not name. They land as facts of the public API; document them so future readers don't propose redoing what already exists. Source: `~/.mdx/research/helioy-im-codebase-2026-05.md`.

### Error taxonomy: `AuthzError::Audit { message }`

v0.1.1 ships a fifth variant on top of the draft's four: `AuthzError::Audit { message }`, the sink-failure variant. `AuthzError::audit(AuditError)` (`error.rs:21-28`) is the canonical lift from a store-side failure into the authorization error type. An authorization decision that was not recorded is an integrity violation, not a recoverable error; lifting it into `AuthzError` forces the caller to handle it as one.

### Principal forward compatibility

v0.1.1 ships `Principal::Unknown { kind, raw }` with hand-rolled serde (`types.rs:28-122`) so a v1 reader can deserialize and reserialize a v2-producer's principal without dropping fields. Tested in `tests/principal_forward_compat.rs`. Resolves open question 5.

### `Action::ALL` exhaustive iterator

`Action::ALL: [Self; 11]` is exported (`types.rs:141-153`) for exhaustive iteration. Closed-enum + exported `ALL` array is the v1 shape; resolves open question 7 in favour of closed enum.

### Audit schema migration discipline

v0.1.1 introduces a `_schema_version` table with idempotent transactional apply (`im-store/src/sqlite/audit.rs:193-214`). Each future migration adds a row keyed by integer version. `0001_audit.sql` is the v1 schema; the runner only applies versions not yet recorded. Future migrations (Capability enum, credential_resolution column) extend this pattern.

### Crates.io publish + provenance

v0.1.1 publishes via OIDC (`rust-lang/crates-io-auth-action@v1.0.4`) with `actions/attest-build-provenance@v3` signing each `.crate`. No static publish token. Per-crate release tags via `release-plz`. Workflow at `.github/workflows/publish.yml`. Sets the publishing pattern for `lilo-rm-*`, `lilo-sm-*`, and any future lilo-prefixed crate.

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
