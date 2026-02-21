---
title: identity-matters v0.1.1 codebase review (draft-vs-shipping audit)
type: research
tags: [codebase-review, identity-matters, im, iam, rust, audit, peer-creds, sqlite, lilo, helioy, draft-vs-shipping]
summary: identity-matters shipped at v0.1.1 as three published crates (lilo-im-core, lilo-im-stub, lilo-im-store). The Authorizer trait, audit pipeline, peer-cred extraction, and reserved schema fields all match the draft. Vault, CaSource, HMAC, and Capability enrichment are entirely absent. Audit storage moved into its own crate instead of sm-store, which is a principled improvement the draft did not predict.
status: active
source: codebase-analyst
confidence: high
created: 2026-05-18
updated: 2026-05-18
---

# identity-matters v0.1.1 codebase review

## 1. Snapshot

**Repo.** `github.com/littleorgans/identity-matters`, MIT, branch `main`, reviewed at v0.1.1 (tag `6a88edd`, 2026-05-17; HEAD `e01affa` is a CI fix). Repo is one week old: first real commit `62fee96` (`nancy[ALP-2456]: Establish IAM tracer crates`) and v0.1.1 cut a day later. Eighteen commits, nine prefixed `nancy[ALP-…]:` — Nancy did the engineering work against Linear issues `ALP-2456` through `ALP-2480`.

**Workspace shape.** Cargo workspace, resolver 3, edition 2024, MSRV `1.90`, stable toolchain (`rust-toolchain.toml:2`). Three member crates under `crates/`, all v0.1.1:

| Published name  | Path               | LOC (src+tests) | One-liner                                                                              |
| --------------- | ------------------ | --------------- | -------------------------------------------------------------------------------------- |
| `lilo-im-core`  | `crates/im-core/`  | 407             | `Authorizer` trait, `Principal`/`Action`/`ResourceSpec`, `AuditRow`, peer-cred extract |
| `lilo-im-stub`  | `crates/im-stub/`  | 182             | `StubAuthorizer` that allows the configured local uid and audits both decisions        |
| `lilo-im-store` | `crates/im-store/` | 613             | `SqliteAuditSink`, schema/migrations, filtered `query_audit` API                       |

Total 1,382 LOC of Rust (`wc -l`). Largest file `crates/im-store/src/sqlite/audit.rs` at 335 LOC, under the local hard limit of 700 enforced by `scripts/check-loc-limit.sh:4` (matches Stuart's CLAUDE.md ceiling).

**Dependency stack** (`Cargo.toml:23-33`). `async-trait` 0.1, `chrono` 0.4 with serde, `nix` 0.30 with `socket,user` for peer creds (draft asked 0.29; bumped one minor without a recorded reason), `serde` 1, `serde_json` 1, `thiserror` 2.0, `tokio` 1 with `macros,net,rt` only, `uuid` 1.9 with `serde,v7`. Storage: `rusqlite` 0.37 `bundled` (commit `339b18b nancy[ALP-2474]: Replace im-store sqlx audit sink with rusqlite` swapped sqlx out before v0.1 cut). Dev: `insta` 1, `tempfile` 3.

**Crate naming.** Published prefix is `lilo-` (`Cargo.toml:19`); in-repo dirs stay short and `[lib].name = "lilo_im_core"` smooths the import path. Renaming landed in `57c9542 nancy[ALP-2479]: Rename identity crates for publication` as the publication blocker. Draft did not predict the prefix.

**CI and release.** `ci.yml`: just-check + build + test + nextest + a conditional `cargo-semver-checks` on source-only changes (`ci.yml:53-63`). `publish.yml`: OIDC via `rust-lang/crates-io-auth-action@v1.0.4` + `actions/attest-build-provenance@v3`, repackages after publish so attestation finds the `.crate` files. `release-plz.yml`: per-crate tags (`e01affa`). No static `CARGO_REGISTRY_TOKEN` anywhere. `justfile:28` runs `fmt + clippy --fix -D warnings + loc`.

## 2. Grade

**A−**. The v1 boundary is locked as the draft intended: callers depend only on `lilo-im-core`, the stub is swappable, the audit schema reserves v2+ fields, and forward-compat principal deserialization is in place. Test discipline is high for a one-week-old repo: integration tests cover all 11 Action variants against a real SQLite (`crates/im-store/tests/audit.rs:42-67`), forward-compat principal round-trips an `Unknown` kind (`crates/im-core/tests/principal_forward_compat.rs:1-29`), peer-cred extraction runs over a real `UnixListener` (`crates/im-core/tests/peer_creds.rs:11-29`), and four `insta` snapshots pin the wire shapes of `AuditDecision`, `AuthzError`, the SQLite column layout, and the stub audit summary. Deductions from a full A: (1) the draft's `Capability` design names `CredentialAccess(CredentialId)` as the v1 placeholder variant; shipped `Capability` is a degenerate `{ name: String }` newtype (`crates/im-core/src/types.rs:173-176`), so the v2-vault seam is weaker than intended. (2) The `credential_resolution` nullable column the draft mandates is missing from `0001_audit.sql`, making v2 vault integration a migration rather than a column-fill. (3) The HMAC primitive the draft leaned toward shipping is absent. (4) No consumer wires `Authorizer` yet: session-matters does not exist in this repo, so the "every mutating handler calls authorize" success criterion is unverifiable from inside identity-matters.

## 3. What actually shipped vs the draft

| Draft feature                                                | Status            | Evidence                                                                                                                                                                                                |
| ------------------------------------------------------------ | ----------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `im-core` types crate                                        | shipped           | `crates/im-core/src/lib.rs:5-26`                                                                                                                                                                        |
| `Authorizer` trait, async                                    | shipped, verbatim | `crates/im-core/src/lib.rs:19-26` matches draft signature byte-for-byte                                                                                                                                 |
| `AuditSink` trait                                            | shipped, verbatim | `crates/im-core/src/audit.rs:61-64`                                                                                                                                                                     |
| `Principal::Local(u32)`                                      | shipped           | `crates/im-core/src/types.rs:13-19`                                                                                                                                                                     |
| Open principal enum for forward compat                       | shipped, expanded | `Principal::Unknown { kind, raw }` (`types.rs:15-19`) with hand-rolled serde so unknown kinds round-trip; tested at `tests/principal_forward_compat.rs:5-29`                                            |
| `Action` enum closed at 11 variants                          | shipped, verbatim | `crates/im-core/src/types.rs:124-138`; `Action::ALL` exported for exhaustive iteration (`types.rs:141-153`)                                                                                             |
| `ResourceSpec` with workspace/role/runtime/session_id/labels | shipped, verbatim | `crates/im-core/src/types.rs:164-171`                                                                                                                                                                   |
| `AuthzError` taxonomy                                        | shipped, expanded | `crates/im-core/src/error.rs:5-19` adds an `Audit { message }` variant the draft didn't name, plus `AuthzError::audit(AuditError)` constructor (`error.rs:21-28`) so sink failures propagate cleanly    |
| `AuditRow` with reserved v2 fields                           | shipped, expanded | `crates/im-core/src/audit.rs:17-30`; reserved: `policy_id`, `evaluation_trace`, `denial_reason`. **Missing**: `credential_resolution`                                                                   |
| `AuditDecision::{Allow,Deny,Error}`                          | shipped, verbatim | `crates/im-core/src/audit.rs:9-15`, serde tag `kind` snake_case                                                                                                                                         |
| Peer-cred extraction, macOS + Linux                          | shipped, verbatim | `crates/im-core/src/peer_creds.rs:11-32`; `getpeereid` via `BorrowedFd` on macOS, `SO_PEERCRED` on Linux; other unix returns `AuthzError::Internal` (`peer_creds.rs:34-37`)                             |
| `StubAuthorizer` always-allow local uid                      | shipped, verbatim | `crates/im-stub/src/lib.rs:42-73`                                                                                                                                                                       |
| StubAuthorizer audits every decision                         | shipped, verbatim | `crates/im-stub/src/lib.rs:49-50` (allow), `:62-70` (deny); sink failure escalates to `AuthzError::Audit`                                                                                               |
| Audit table in sm-store's sqlite                             | **different**     | Audit lives in its own crate `lilo-im-store` (`crates/im-store/src/lib.rs:1-35`), not embedded in sm-store. See §7                                                                                      |
| Single audit schema with reserved fields                     | shipped           | `crates/im-store/migrations/0001_audit.sql:1-13`; column layout snapshot-pinned at `tests/snapshots/audit__audit_table_columns.snap:5-15`                                                               |
| Migration runner                                             | shipped, expanded | `_schema_version` table, transactional batch apply, idempotent re-runs (`crates/im-store/src/sqlite/audit.rs:193-214`)                                                                                  |
| Filtered audit query API                                     | shipped, expanded | `AuditFilters { principal, action, since, limit }` (`im-store/src/sqlite/audit.rs:35-41`), `query_audit` free function (`im-store/src/lib.rs:17-25`); landed in `0b433e7 nancy[ALP-2459]`               |
| Single admin role                                            | shipped, verbatim | `crates/im-stub/src/lib.rs:53`                                                                                                                                                                          |
| Empty capabilities in v1                                     | shipped           | `crates/im-stub/src/lib.rs:54`; but `Capability` itself is `{ name: String }` (`types.rs:173-176`), not the discriminated enum the draft prescribed                                                     |
| `Capability::CredentialAccess(CredentialId)`                 | **missing**       | Draft `identity-matters-iam-draft.md:300` asked for at least one variant. Shipped type is a name-only struct, so the v2 vault seam exists only nominally                                                |
| HMAC-derived per-pod tokens (`im-core::hmac`)                | **missing**       | No `hmac` module                                                                                                                                                                                        |
| `im-vault::CaSource` trait                                   | **missing**       | No `im-vault` crate exists                                                                                                                                                                              |
| `credential_resolution` audit column                         | **missing**       | `0001_audit.sql:1-13`; reserved columns are `policy_id`, `evaluation_trace`, `denial_reason` only                                                                                                       |
| Sub-crate in session-matters workspace                       | **different**     | identity-matters is a standalone repo and standalone workspace published to crates.io. Resolves draft open question 1                                                                                   |
| `sm doctor` IAM status surface                               | not in this repo  | session-matters is not in this workspace                                                                                                                                                                |
| `im` CLI binary                                              | not in v1         | Three `[lib]` only, no bin targets                                                                                                                                                                      |

**Surprises not in the draft.**

- `AuthzError::Audit` with `AuthzError::audit(AuditError)` constructor for sink-failure plumbing (`crates/im-core/src/error.rs:5-28`). Without it the stub would have had to swallow audit failures or surface them via a misleading variant.
- `Principal::Unknown { kind, raw }` with hand-rolled serde (`types.rs:28-122`) preserving all unknown fields under their original keys. Draft only said "open enum"; shipped design handles the actual v2-producer-to-v1-reader case.
- `_schema_version` table with idempotent apply (`im-store/src/sqlite/audit.rs:193-214`). Draft did not specify migration discipline; this is the right one.
- `AuditRow::new` synthesizes `id = Uuid::now_v7()`, `timestamp = Utc::now()`, mirrors `resource.session_id` into `session_ref`, and auto-populates `denial_reason` from `Deny { reason }` (`im-core/src/audit.rs:32-58`). Four derivations bundled into one constructor.
- Four `.snap` files pin the SQLite column layout, `AuditDecision` JSON, `AuthzError` Display strings, and stub audit summary. Wire shapes will not drift silently.
- `cargo-semver-checks` gated on whether `crates/*/src/` files changed in the PR (`ci.yml:53-63`). Saves CI on doc-only PRs.

## 4. Primitives that landed

Subset of BerriAI + agent-sandbox primitives identity-matters-relevant.

1. **Unix peer-cred AuthN with cfg-gated platform impls.** `crates/im-core/src/peer_creds.rs:11-37`. Maps to the draft's K8s `User/Group` row. macOS uses `getpeereid(BorrowedFd::borrow_raw(fd))` inside `tokio::task::spawn_blocking` so the blocking syscall does not stall the reactor (`peer_creds.rs:14-22`). Linux uses `getsockopt(stream, sockopt::PeerCredentials)` which is non-blocking. Live integration test against a real `UnixListener` (`tests/peer_creds.rs:11-29`).
2. **Audit-everything pattern (BerriAI).** Every authorize call writes a row before returning on both branches (`crates/im-stub/src/lib.rs:49-70`). Sink failure escalates to `AuthzError::Audit` (`stub/src/lib.rs:33`) rather than being swallowed. Integration test exercises 11 allows + 1 deny across `Action::ALL` (`im-store/tests/audit.rs:42-89`).
3. **Pinned wire shape via snapshot tests (BerriAI).** `Principal::Local` JSON locked to `{"kind":"Local","uid":501}` (`types.rs:192-196`); `AuditDecision` JSON, `AuthzError` Display, SQLite column layout all `.snap`-pinned. Four snapshot files total.
4. **Forward-compatible principal deserialization (agent-sandbox).** `Principal::Unknown { kind, raw }` plus round-trip test (`tests/principal_forward_compat.rs:5-29`). A v1 reader deserializes a v2 principal kind and reserializes it without dropping fields. Same discipline agent-sandbox applies to v1alpha1↔v1beta1, applied at the wire layer.
5. **Reserved nullable columns for future enrichment.** `migrations/0001_audit.sql:10-12` declares `policy_id`, `evaluation_trace`, `denial_reason` as `TEXT NULL`. `assert_reserved_columns_are_nullable` enforces it (`tests/audit.rs:208-213`). Adds v2 policy evaluation without a migration.
6. **Transactional, idempotent migrations with a version table.** `_schema_version` + `schema_version_applied` predicate + transaction-wrapped batch (`im-store/src/sqlite/audit.rs:193-214`). Re-running is a no-op; integration test calls `run_migrations` twice and asserts the column layout is identical (`tests/audit.rs:21-32`).
7. **OIDC publish + build provenance attestation.** `publish.yml:14-43`: OIDC-derived token via `rust-lang/crates-io-auth-action@v1.0.4`, `actions/attest-build-provenance@v3` signs each `.crate`. Stricter than BerriAI's static-token model.
8. **Blast-radius-scoped CI gate.** `cargo-semver-checks` runs only when source files change (`ci.yml:53-63`). Same spirit as agent-sandbox's label-selector watches: do not waste cycles on irrelevant work.

## 5. Primitives missing

1. **Vault MITM credential sidecar (BerriAI #1).** No `im-vault` crate. Status: **deliberately deferred to v2+** per `identity-matters-iam-draft.md:295`. The seam (`Authorized.capabilities`) exists but the enrichment plumbing is degenerate, so deferment is honest.
2. **HMAC-derived per-pod tokens (BerriAI #2).** No `im-core::hmac`. The draft itself was undecided (`identity-matters-iam-draft.md:309`); shipping decision is "defer." Consistent with not having an rtmd↔shim handshake to authenticate yet; the primitive has no consumer.
3. **CA bundle distribution + `CaSource` trait (BerriAI #3).** No `im-vault` crate, no trait. **Deliberately deferred to v2+** per `identity-matters-iam-draft.md:316-319`. The operational rule (no CA private key in repo) has no executable owner, but nothing to violate yet.
4. **`Capability::CredentialAccess(CredentialId)` placeholder variant.** **Oversight or simplification**, depending on lens. Draft unambiguous (`identity-matters-iam-draft.md:300`: "Reserve `Capability` as an enum in `im-core` v1 with at least one variant defined"). Shipped is `struct Capability { name: String }` (`types.rs:173-176`). Net effect: v2 vault landing is a wider change to `im-core` than predicted because `Capability` shape itself shifts. See §8 for draft update.
5. **`credential_resolution` audit column.** **Oversight**. Draft explicit (`identity-matters-iam-draft.md:301`: "Adding this column at v2 is migration work; defining it at v1 is one column declaration."). Shipped schema has three reserved columns, not four. Lowest-effort to fix pre-1.0.
6. **K8s mapping artifacts (CRDs, controllers).** **Out of scope for v1** by design. Draft's K8s mapping table is forward-looking; v1 ships in-process. Not a miss, just a not-yet.
7. **`sm doctor` integration.** **Out of this repo.** Lives in session-matters. The identity-matters boundary ends at the `Authorizer` trait; the doctor surface is downstream.

## 6. Fit against helioy-controller-conventions

identity-matters ships no CRDs and no controllers. Five of the six conventions do not apply. The two that touch:

- **Convention 3 (`Option<bool>` three-state).** `ResourceSpec` uses `Option<String>` / `Option<RuntimeKind>` / `Option<Uuid>` (`types.rs:164-171`); `AuditFilters` likewise (`im-store/src/sqlite/audit.rs:35-41`). None is a `bool` so the convention does not apply directly, but the spirit (None = preserve / do not constrain) is followed.
- **Convention 6 (non-destructive defaults).** No user-visible destructive operation in v1. Closest parallel: the stub returns `AuthzError::UnknownPrincipal` for an unrecognized principal — deny-by-default, the right posture for IAM (`crates/im-stub/src/lib.rs:72`).

Conventions 1, 2, 4, 5 are k8s controller patterns with no surface here. Re-check when the first identity-matters CRD lands (probably v2+ with `im-daemon`).

## 7. Surprises

**Cleaner than planned.**

- **Audit storage owns its own crate.** Draft (`identity-matters-iam-draft.md:170`) said audit rows live in `sm-store`'s sqlite submodule. Shipped reality reverses that: `lilo-im-store` owns its own SQLite (default `~/.im/audit.sqlite`), its own schema, its own migration runner. README (`im-store/README.md:5`) is explicit: "Consumers query it through `SqliteAuditSink` and `query_audit` rather than hosting identity data in their own stores." Identity-matters now owns the identity data end-to-end. Cleanly resolves draft open question 2. Most important architectural deviation in the repo and it is for the better.
- **`AuditError` + `AuthzError::Audit { message }` for sink-failure plumbing.** Draft left this path unstated. Shipped design lets callers distinguish "policy denied" from "we could not record the decision," the right separation for IAM.
- **Test discipline.** Per-Action exhaustive integration test, real-socket peer-cred test, real-SQLite audit test, forward-compat principal test, four snapshot tests, all in 1.4k LOC. Test-to-source file ratio roughly 2:1. Unusually disciplined for a one-week-old crate.
- **Crate-rename-before-publish discipline.** `lilo-` prefix introduced in a dedicated commit (`57c9542`) with `[lib].name` smoothing the import path. Saves docs.rs URLs and namespace claims; avoids the `im-core` name-squatting problem.
- **OIDC publish + attestation + per-crate release tagging.** Stronger supply-chain story than BerriAI itself.

**Concerning.**

- **`Capability` is a name-only struct, not a discriminated enum.** `types.rs:173-176` is the entire definition. Draft asked for at least one real variant. Shipping the degenerate version means: (a) v2 vault is a breaking change to `im-core` rather than additive; (b) `capabilities: Vec::new()` (`im-stub/src/lib.rs:54`) reads like a seam but is semantically empty; (c) downstream callers can misuse it without knowing it is a placeholder. Worth a doc-comment marking it v1-placeholder while the type stays in 0.x.
- **No `credential_resolution` column.** v2 vault is migration work, not a column-fill. Cheap to fix pre-1.0.
- **Audit pipeline blocks on the sink.** `im-stub/src/lib.rs:49-50` awaits `record(...)` before returning. Under SQLite this is fast, but a slow or hung sink throws back-pressure into the authorize path. Bounded queue / fire-and-forget-with-bound is the usual mitigation. Not necessarily wrong for a stub; worth noting before the same code becomes a v2 hot path.
- **`audit_db_parent` returns `Option<&Path>` and `connect` skips `mkdir` on `None` (`im-store/src/sqlite/audit.rs:63-65`).** A bare filename gets no parent dir created. Current default (`~/.im/audit.sqlite`) always has a parent so this is dormant, but a caller passing a raw filename gets a less helpful error from `Connection::open`. Minor.
- **Empty top-level `README.md` and `CHANGELOG.md`.** Root README is one line; root CHANGELOG is the release-plz header only. Per-crate files are populated. Cosmetic but visible on the GitHub landing page.
- **`lilo-` prefix is undocumented in-repo.** No README mention of why crates publish as `lilo-im-core` rather than `im-core`. One sentence in the top-level README would close this.

## 8. Recommended draft updates

Concrete revisions to `~/.mdx/projects/identity-matters-iam-draft.md` to match shipping reality. Quoted draft text first, suggested replacement second.

1. **Crate naming and repo placement** (supersedes §"Proposed crate layout"). Draft: "v1 may live in the session-matters repo as a sub-crate ... or as a separate workspace; Linear decides. Leaning sub-crate ... extracted to its own repo in v2+." Replace with: "v1 ships as a standalone repo (`github.com/littleorgans/identity-matters`) with three published crates: `lilo-im-core`, `lilo-im-stub`, `lilo-im-store`. The `lilo-` prefix is the publishable form; in-repo dirs stay short with `[lib].name = \"lilo_im_core\"` smoothing the import path. Resolves open question 1."
2. **Audit storage location** (supersedes §"Domain model > Audit record" closing paragraph and open question 2). Draft: "Audit rows live in session-matters' sqlite (in the `audit` table inside `sm-store`'s sqlite/ submodule). identity-matters' crate writes them through a trait that session-matters implements." Replace with: "Audit rows live in identity-matters' own SQLite, owned by the `lilo-im-store` crate (default `~/.im/audit.sqlite`). `SqliteAuditSink` is the built-in `AuditSink`. session-matters consumes it by holding an `SqliteAuditSink` and passing it as `AuditSink` to whatever `Authorizer` it wires. Identity store is sovereign over its data shape; consumers do not host identity rows. Resolves open question 2 and tightens the v1 boundary beyond the draft."
3. **`Capability` shape** (revises §"External validation > Vault MITM" provision 1). Draft: "Reserve `Capability` as an enum in `im-core` v1 with at least one variant defined (`CredentialAccess(CredentialId)`)." Replace with: "v1 ships `Capability { name: String }` as a placeholder; the discriminated-enum shape is **not** in v1. v2 vault landing is therefore a breaking change to `im-core`. Lowest-cost fix: bump `Capability` to an enum with at least `Name(String)` and `CredentialAccess(CredentialId)` variants in a 0.2 release before any external consumer pins `im-core`." Open a follow-up Linear issue.
4. **`credential_resolution` audit column** (revises §"External validation > Vault MITM" provision 2). Draft: "`AuditRow` schema must include a `credential_resolution` nullable column from v1." Replace with: "v0.1.1 reserves `policy_id`, `evaluation_trace`, `denial_reason` but **not** `credential_resolution`. Known gap. Land it in 0.2 (`migrations/0002_credential_resolution.sql`) alongside the `Capability` enum bump." Open a follow-up Linear issue.
5. **HMAC primitive** (revises §"External validation > HMAC-derived per-pod tokens"). Draft: "Lean: ship in v1." Replace with: "**Did not ship in v0.1.1.** Deferred because rtmd↔shim handshake has no implementation yet, so the primitive has no consumer. Revisit when runtime-matters lands its shim model. Reserve `lilo-im-core::hmac` as the future module path."
6. **Error taxonomy** (additive). Add: "`AuthzError::Audit { message }` is the sink-failure variant v0.1.1 added on top of the draft's four. `AuthzError::audit(AuditError)` (`error.rs:21-28`) is the canonical lift. An authorization decision that was not recorded is an integrity violation, not a recoverable error."
7. **Principal forward compatibility** (additive). Add: "v0.1.1 ships `Principal::Unknown { kind, raw }` with hand-rolled serde (`types.rs:28-122`) so a v1 reader can deserialize and reserialize a v2-producer's principal without dropping fields. Tested in `tests/principal_forward_compat.rs`. Resolves draft open question 5."
8. **Action enum ALL** (additive). Add: "`Action::ALL: [Self; 11]` is exported (`types.rs:141-153`) for exhaustive iteration. Resolves draft open question 7 in favor of closed-enum + exported `ALL` array."
9. **Audit schema migration discipline** (additive). Add: "v0.1.1 introduces a `_schema_version` table with idempotent transactional apply (`im-store/src/sqlite/audit.rs:193-214`). Each future migration adds a row keyed by integer version. `0001_audit.sql` is the v1 schema; the runner only applies versions not yet recorded."
10. **Crates.io publish + provenance** (additive). Add: "v0.1.1 publishes via OIDC (`rust-lang/crates-io-auth-action@v1.0.4`) with `actions/attest-build-provenance@v3` signing each `.crate`. No static publish token. Per-crate release tags via `release-plz`. Workflow at `.github/workflows/publish.yml`."

## 9. Provenance

- **Version reviewed.** v0.1.1.
- **HEAD SHA.** `e01affa2a6400f3194e1ae236aee04019c1dd3e6` (branch `main`).
- **Release tag.** `chore: release v0.1.1` at `6a88edd0e0c315a0247a695c7039149dfb8fd290` (2026-05-17).
- **Date reviewed.** 2026-05-18.
- **License.** MIT.
- **Reviewer.** Stuart Robinson via codebase-analyst.
- **Sources inspected.** All 16 Rust files (1,382 LOC) under `crates/`, all 3 crate Cargo.tomls plus workspace `Cargo.toml`, all 4 `.snap` files, all 3 GitHub workflows, `release-plz.toml`, `rust-toolchain.toml`, `justfile`, `scripts/check-loc-limit.sh`, `.fmmrc.toml`, `migrations/0001_audit.sql`, per-crate READMEs and CHANGELOGs, root README and CHANGELOG, git log of 18 commits since inception.
- **Sources not inspected.** No `.nancy/` content (gitignored scratch). No Linear issue state for `ALP-2456`..`ALP-2480` beyond commit messages.
- **Related cm.** `019e34ba-881f-7971-924f-a978599015c2` (BerriAI review), `019e3784-2194-7b91-87ae-84e3b3545767` (agent-sandbox review), `019e327f-111b-7382-a760-12e4e410e701` (seven-product invariants).
- **Related drafts.** `~/.mdx/projects/identity-matters-iam-draft.md`, `~/.mdx/projects/helioy-controller-conventions.md`.
