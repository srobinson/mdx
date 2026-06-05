---
title: lilo-moon SQL-first persistence research
type: projects
tags: [lilo-moon-template, persistence, drizzle, atlas, sqlx, supabase, workos, clerk, rls]
summary: August 2026 fact check of drizzle-kit pull, SQL migration runners, sqlx, non-JS Supabase clients, auth JWKS, and RLS with third-party JWTs.
status: active
project: lilo-moon-template
confidence: high
---

# SQL-first persistence and provider adapter seams

Verified 2026-08-20. npm dist-tags and GitHub/crates.io release dates, plus official docs. Not a design. Owner preferences that the evidence contradicts are in [Recommendation](#recommendation).

## 1. Drizzle introspection (`drizzle-kit pull`)

**Current versions (npm, 2026-08-20)**

| Channel | drizzle-orm | drizzle-kit | Date |
|---|---|---|---|
| `latest` (stable) | **0.45.2** | **0.31.10** | 2026-03-27 (orm; kit paired) |
| `rc` | **1.0.0-rc.4** | **1.0.0-rc.4** | 2026-06-27 |
| `beta` | 1.0.0-beta.22 | 1.0.0-beta.22 | 2026-04-16 |

Sources: `https://registry.npmjs.org/drizzle-orm`, `https://registry.npmjs.org/drizzle-kit`, `https://github.com/drizzle-team/drizzle-orm/releases`. Docs still banner `v1.0.0-beta.2` even though rc.4 shipped. Roadmap widget says v1.0 at 98%. Do not treat 1.0 as stable.

**What `pull` is for.** Official database-first path: introspect live DDL, write `schema.ts`. Docs: `https://orm.drizzle.team/docs/drizzle-kit-pull` and Option 1 on `https://orm.drizzle.team/docs/migrations`. v1 added `drizzle-kit pull --init` (marks the pulled snapshot applied so later `generate` diffs from it): `https://orm.drizzle.team/docs/v0-v1-changes`. Kit rewrite (DDL snapshots, introspection 10s → &lt;1s, `pull+generate` as a kit test scenario) is in 1.0, not in 0.31.10.

**What pull loses or mangles (Postgres, verified against 0.31.10 / 0.45.2 unless noted)**

| Object | Status | Evidence |
|---|---|---|
| Tables, PKs, FKs, unique, basic indexes | Usually recovered | Official pull docs |
| CHECK constraints | Round-trip broken: mid-expression casts survive (`(vertical)::text`), next `generate` emits DROP/ADD | [#6093](https://github.com/drizzle-team/drizzle-orm/issues/6093) opened **2026-08-04**, still open |
| `numeric` defaults | Pulled as string `.default('1')`; generate wants a numeric default | same issue; SQLite sibling [#5661](https://github.com/drizzle-team/drizzle-orm/issues/5661) |
| Partitioned parents (`relkind = 'p'`) | Dropped from introspection on 0.31.10. rc.4 query includes `'p'`; Drizzle DSL still has no partition concept | #6093 |
| Index opclasses | Mis-assigned or dropped (`uuid_ops`, `text_ops`, `timestamptz_ops`) | #6093 |
| RLS policies | Drizzle can *author* `pgPolicy` / `pgTable.withRLS` (`https://orm.drizzle.team/docs/rls`). Pull docs never claim policy round-trip. Treat policies as SQL, not as pull output. | RLS docs + pull docs |
| Postgres functions / custom types | Historical: functions pulled as TS methods ([#4916](https://github.com/drizzle-team/drizzle-orm/issues/4916)); custom types / citext mangled ([#4806](https://github.com/drizzle-team/drizzle-orm/issues/4806), [#3446](https://github.com/drizzle-team/drizzle-orm/issues/3446)). Listed as fixed in the 1.0-beta.2 kit rewrite notes, not proven on stable 0.31.10. | beta.2 release notes |
| Generated columns | First-class in the TS API (`https://orm.drizzle.team/docs/generated-columns`). Not in the pull command surface. Do not assume expressions survive pull. | generated-columns docs |
| Partial indexes | Not documented on the pull page. Expression indexes have crashed kit historically ([PR 3888](https://github.com/drizzle-team/drizzle-orm/pull/3888)). | kit history |
| `schemaFilter` | 0.x: `public` only. 1.0: all schemas, globs. A 0.31 pull of a multi-schema DB is a different product than a 1.0 pull. | v0→v1 changes |

**Round-trip.** On **stable 0.31.10**, `pull` then `generate` is not a no-op. #6093 (four days before this write) is explicit: “`pull` → `generate` on an unchanged database should report `No schema changes`. Today it emits DROP/ADD pairs.” The reporter removed `db:pull` from their scripts. 1.0-rc rewrote snapshots and lists `pull+generate` as a test scenario; it is still a pre-release (`rc.4`, plus unpublished `rc.5-*` dist-tags).

**Verdict: PARTIAL.** `pull` is the documented database-first command and is much faster in 1.0, but on the current stable pair it is not generate-clean. It must not own migrations. Use it as a generated TS artifact after SQL is applied.

## 2. Language-agnostic SQL migration runners

Compared 2026-08-20. Owner constraint: plain `.sql` as source of truth, moon monorepo, Drizzle for TS only.

| | Atlas (ariga) | dbmate | golang-migrate | sqlx migrate |
|---|---|---|---|---|
| Version | **v1.3.0** (2026-08-02) `https://github.com/ariga/atlas/releases/tag/v1.3.0` | **v2.35.0** (2026-08-07) `https://github.com/amacneil/dbmate/releases/tag/v2.35.0` | **v4.19.1** (2025-11-29) `https://github.com/golang-migrate/migrate/releases/tag/v4.19.1` | **sqlx-cli 0.9.0** (2026-05-21) crates.io |
| SQL as SOT | Yes. `file://schema.sql` or a SQL directory is a first-class desired state (`https://atlasgo.io/atlas-schema/sql`). Versioned SQL migrations too. RLS `ENABLE` / `CREATE POLICY` are ordinary SQL. | Yes. Timestamped `.sql` with `-- migrate:up` / `-- migrate:down` in one file. Auto-dumps `db/schema.sql` via `pg_dump`. | Yes. Paired `N.up.sql` / `N.down.sql`. | Yes. `sqlx migrate add` writes `migrations/<ts>-<name>.sql`; `-r` adds `.up.sql`/`.down.sql`. |
| Up/down | Declarative apply *or* versioned up. Down is not the product; drift/lint is. | Up + rollback (`dbmate down`). Down required in the file even if empty. | Versioned up/down. Dirty-state halt on mid-run failure (`force` to unstick). | Optional reversible (`-r`). `sqlx migrate revert`. |
| CI | `atlas migrate lint` / `migrate apply`. Ephemeral `docker://postgres/16/dev` as `--dev-url`. Agent JSON output on drizzle-kit is unrelated; Atlas has its own CI story. | `dbmate --wait up`. Single Go binary. No SQL lint. | CLI in CI. Dirty flag is the failure mode. Last release **9 months** before this write. | `sqlx migrate run`. Tied to a Rust toolchain. |
| Postgres coverage | High: policies, functions, triggers, composite/domain types, partial indexes as SQL. Atlas exists specifically to cover objects ORMs omit (`https://atlasgo.io/guides/orms/drizzle`). | Whatever you write; dump is `pg_dump`. No planner. Enum `ADD VALUE` needs `transaction:false`. | Whatever you write. Driver breadth (Cassandra, Mongo, …) is irrelevant here. | Whatever you write. No planner. |
| Drizzle interop | **Yes, first-class.** `drizzle-kit export` → Atlas (`https://orm.drizzle.team/docs/migrations` Option 6, `https://atlasgo.io/guides/orms/drizzle`). Inverse of SQL-first, but the loader exists. | None. | Atlas can *plan for* golang-migrate (`https://atlasgo.io/guides/migration-tools/golang-migrate`). The migrate binary itself has no Drizzle knowledge. | None. |

**Why the others lose**

- **dbmate** is the smallest honest SQL runner (language-agnostic binary, schema dump in git, up/down). It will not plan diffs, lint destructive SQL, or talk to Drizzle. Fine as a fallback; thin for a baseline that also wants RLS, functions, and a TS schema derived from SQL.
- **golang-migrate** is the popular Go CLI, but v4.19.1 is stale relative to Atlas/dbmate (last tag 2025-11-29), the dirty-state workflow is a known production footgun (Bytebase 2026-08-04 roundup: `https://www.bytebase.com/blog/top-database-schema-change-tool-evolution/`), and there is no Drizzle story except “use Atlas to write golang-migrate files.”
- **sqlx migrate** is a Rust crate feature, not a monorepo tool. Using it as the shared runner forces every CI job and every TS/Python app through `cargo`. Compile-time `query!` (question 3) is a different product from the migrator.

**Recommend Atlas.** One Go binary, SQL schema files as desired state, versioned migrations generated by `atlas migrate diff`, lint in CI, Postgres objects including RLS, and a documented Drizzle export path if a TS-first experiment is ever needed.

**Verdict: Atlas.** dbmate is the only other language-agnostic SQL tool that is still shipping; it loses planning, lint, and Drizzle. golang-migrate is stale. sqlx migrate is Rust-only.

## 3. Rust `sqlx` compile-time SQL and offline CI

**Version:** sqlx **0.9.0**, sqlx-cli **0.9.0**, released **2026-05-21** (crates.io `max_stable_version`). Repo moved: docs.rs still links launchbadge; README lives at `https://github.com/transact-rs/sqlx`. 0.8.6 (2025-05-19) is the previous stable line.

**Still the strongest Postgres compile-time-checked raw SQL choice in Rust.** Diesel 2.x is a query builder/ORM with its own DSL. SeaORM is an ORM on top of sqlx. Neither gives “the SQL you wrote, checked by the live catalog.” That remains sqlx `query!` / `query_as!` (`https://docs.rs/crate/sqlx/0.9.0`).

**Offline / CI without a live DB: yes.** 0.9 crate docs: “Offline mode is now always enabled.” Workflow, from `sqlx-cli/README.md`:

1. `cargo sqlx prepare` (or `--workspace`) writes `.sqlx/` query metadata. Commit it.
2. CI: `SQLX_OFFLINE=true cargo build` so a stray `DATABASE_URL` cannot reach a database.
3. CI freshness gate: `cargo sqlx prepare --check` (nonzero if `.sqlx` is stale).

Prepare still needs a live DB *once*, when queries or schema change. CI builds do not. FAQ: `https://github.com/transact-rs/sqlx/blob/main/FAQ.md`.

**Do not use sqlx as the monorepo migrator** (question 2). Use sqlx as the Rust query layer against the same Postgres Atlas migrates.

**Verdict: YES.** sqlx 0.9.0 is still the compile-time raw-SQL pick; offline CI works via committed `.sqlx` + `SQLX_OFFLINE=true` + `prepare --check`.

## 4. Supabase clients outside JS

### Python `supabase` (PyPI)

**Real.** Official client, documented at `https://supabase.com/docs/reference/python/installing`, repo `https://github.com/supabase/supabase-py`. Promoted to first-party 2024-08-16 (`https://supabase.com/blog/python-support`).

- Latest stable: **2.31.0**, uploaded **2026-06-04** (`https://pypi.org/project/supabase/`).
- Pre-release: **3.0.0a1**, 2026-04-09.
- Surface: `create_client`, Auth (`sign_up` / `sign_in_with_password` / `sign_out`), PostgREST table CRUD, Storage, Edge Functions. This is the Data API client, not a Postgres driver.

If Python needs RLS-aware SQL against the wire protocol, that is `psycopg` / `asyncpg`, not this package.

### Rust `supabase-lib-rs`

**Nominal.** Community crate, **not** a Supabase product.

- crates.io **0.5.3**, last publish **2025-10-16** (~10 months before this write): `https://crates.io/crates/supabase-lib-rs`
- Repo: `https://github.com/nizovtsevnv/supabase-lib-rs` (44 commits). README advertises `0.5.4`; that version is not on crates.io.
- Claims auth (MFA, OAuth, magic link), PostgREST, Storage, Realtime, WASM. 113 tests per README. Unofficial, thin history, stale relative to supabase-js and supabase-py.

Sibling community crate `supabase_rs` **0.7.0** (2026-03-05, `https://github.com/floris-xlx/supabase_rs`) is also unofficial (“Lightweight Rust client for Supabase REST and GraphQL”).

There is no official Supabase Rust SDK as of this write. A Rust service that needs the database should use **sqlx (or equivalent) on Postgres**. Use a REST crate only if the app must call Storage/Realtime/Functions, and treat it as a vendor adapter with an explicit escape hatch.

**Verdict: Python real (2.31.0, official). Rust `supabase-lib-rs` nominal (0.5.3, community, stale).**

## 5. Auth portability (WorkOS AuthKit, Clerk, Supabase Auth)

All three issue **asymmetric JWTs** verifiable with a stock JWKS library (`jose`, `jsonwebtoken`, Rust `jsonwebtoken` + JWKS fetch). None require the vendor SDK for verification. Algorithms: pin from the JWKS `alg` (RS256 or ES256). Never trust `alg: none`. Never use HS256 for the portable seam.

| | WorkOS AuthKit | Clerk (session token v2) | Supabase Auth |
|---|---|---|---|
| JWKS URL | `https://api.workos.com/sso/jwks/<clientId>` ([session tokens](https://workos.com/docs/reference/authkit/session-tokens), [sessions](https://workos.com/docs/authkit/sessions)). OIDC issuer is different: `https://api.workos.com/user_management/<clientId>`. `jwks_uri` from discovery points at the `/sso/jwks/` URL. Docs sometimes write `http://`; use HTTPS. | Frontend API `https://<fapi>/.well-known/jwks.json`, or Backend API `https://api.clerk.com/v1/jwks` ([manual verification](https://clerk.com/docs/guides/sessions/manual-jwt-verification)). | `https://<project>.supabase.co/auth/v1/.well-known/jwks.json` ([JWTs](https://supabase.com/docs/guides/auth/jwts)). Empty if the project is still on the legacy HS256 shared secret. Asymmetric JWT Signing Keys: 2025-07-14 (`https://supabase.com/blog/jwt-signing-keys`). |
| Alg | RSA / **RS256** in the wild (issue reports + WorkOS JWKS blog 2026-03-10: WorkOS manages RSA keys). | Example code pins **RS256**. | Header `alg` is `HS256 \| ES256 \| RS256`. New projects should be on asymmetric keys. |
| User id | `sub` (WorkOS user id, `user_…`) | `sub` (`user_…`) | `sub` (auth user UUID) |
| Org / tenant | `org_id` (selected org, may be absent) | Compact object **`o.id`**, `o.slg`, `o.rol`, `o.per` (v2). v1 `org_id` / `org_role` / `org_permissions` **deprecated 2025-04-14**. | No first-class org claim. Put tenancy in `app_metadata` and read via `auth.jwt()`. |
| Role | **`role`** = org membership (`member`, `admin`, …), plus `roles: string[]`. **Collides with Postgres `role`.** | `o.rol` (no `org:` prefix). Not a Postgres role. | **`role`** = Postgres role: `authenticated` / `anon` / `service_role`. This is the claim PostgREST uses to `SET ROLE`. |
| Permissions | `permissions: string[]` (from the org role) | `o.per` (compact names) + `o.fpm` bitmask. Intentionally hard to decode by hand; Clerk tells you to use an SDK for `o.fpm`. | None first-class. Custom via access-token hook or `app_metadata`. |
| Extra that an adapter must absorb | `sid` (session, required for logout), `client_id`, `entitlements`, `feature_flags`, `act` (impersonation). JWT templates can add claims but **cannot** override `iss`/`sub`/`exp`/`iat`/`nbf`/`jti` ([JWT templates](https://workos.com/docs/authkit/jwt-templates)). | `sid`, `azp` (CSRF: validate against known origins), `sts: pending` when orgs are required and the user has none, `pla`/`fea` billing claims, `v: 2`. | `aal`, `session_id`, `email`, `phone`, `is_anonymous`, `amr`, `app_metadata`, `user_metadata`. `user_metadata` is user-writable; do not put authz there ([claims reference](https://supabase.com/docs/guides/auth/jwt-fields)). |

**Adapter must normalize at least:** user id (`sub` is safe), tenant (`org_id` vs `o.id` vs `app_metadata`), role (WorkOS org role vs Clerk `o.rol` vs Supabase Postgres `role`), permissions (array vs compact `o.per`), and a Postgres `role` claim of `authenticated` if anything talks to PostgREST.

**Verdict: YES.** All three expose JWKS and RS256/ES256 JWTs verifiable with a stock library. Claim models differ on tenant, role, and permissions; that difference is the adapter.

## 6. RLS vs third-party JWTs

Postgres RLS does **not** require a Supabase-issued JWT. It requires a Postgres role plus session GUCs that `auth.uid()` / `auth.jwt()` read.

**How Supabase wires it.** PostgREST verifies `Authorization: Bearer`, then sets `request.jwt.claims` and `request.jwt.claim.sub` and `SET ROLE` from the `role` claim. Helpers (`https://supabase.com/docs/guides/database/postgres/row-level-security`):

```sql
auth.uid()   -- request.jwt.claim.sub
auth.jwt()   -- request.jwt.claims::json
```

Supabase’s own pgTAP tests impersonate without minting a JWT:

```sql
set local role authenticated;
set local request.jwt.claim.sub = '<uuid>';
```

Drizzle’s documented Supabase wrapper does the same from a decoded token (`https://orm.drizzle.team/docs/rls`, `createDrizzle`): `set_config('request.jwt.claims', …, true)`, `set_config('request.jwt.claim.sub', …, true)`, `set local role`.

**Third-party JWT into PostgREST (the Data API path).** Official as of this write: Third-Party Auth (`https://supabase.com/docs/guides/auth/third-party/overview`). First-class providers include **Clerk, WorkOS, Auth0, Cognito, Firebase**. Requirements: **asymmetric** JWTs, `kid` in the header, OIDC issuer. Symmetric (HS256) is explicitly not supported. Keys are cached in the project and re-fetched on a ~30 minute cycle. Pricing: third-party MAU.

WorkOS-specific: you **must** JWT-template `role` to `"authenticated"` because WorkOS already uses `role` for org membership (`https://supabase.com/docs/guides/auth/third-party/workos`):

```json
{ "role": "authenticated", "user_role": {{organization_membership.role}} }
```

**This path is currently buggy for WorkOS.** [supabase/auth#2476](https://github.com/supabase/auth/issues/2476) opened **2026-04-08**, still **open**, label `bug`: hosted PostgREST returns `PGRST301 JWSInvalidSignature` because WorkOS JWKS lives at `/sso/jwks/<clientId>` while GoTrue appears to guess `{issuer}/.well-known/jwks.json` (404) instead of OIDC `jwks_uri`. Reporter followed the official WorkOS TPA doc. Workaround they used: service role, which **bypasses RLS**.

Clerk is listed as first-class TPA; confirm JWKS discovery before betting the Data API on it (same class of path mismatch is cited on that issue).

**Imported JWT signing keys** (`https://supabase.com/docs/guides/auth/signing-keys`): you can mint ES256 tokens with `sub` + `role: authenticated` using a key the project already trusts. That is not “WorkOS JWT in, RLS out”; it is a re-sign.

**What actually holds for a language-agnostic baseline**

1. Apps connect to **Postgres directly** (Drizzle, sqlx, psycopg). Verify the IdP JWT with JWKS in process. In a transaction: `set local role authenticated` + `set_config('request.jwt.claims', …)` / `request.jwt.claim.sub`. RLS policies keep using `auth.uid()`. No PostgREST, no Supabase JWT, no TPA. This is how you swap WorkOS / Clerk / Supabase Auth.
2. Apps that must use PostgREST/Realtime/Storage need TPA + a Postgres `role` claim. Treat WorkOS-via-PostgREST as **not proven** until #2476 closes.

**Verdict: YES** for RLS driven by a third-party JWT, via session GUCs (and via TPA when JWKS discovery works). **No**, RLS does not require a Supabase-issued JWT. **Do not** ship WorkOS → PostgREST as the adapter until the open JWSInvalidSignature bug is dead.

## Recommendation

**Migration runner:** Atlas v1.3.0. Desired state in SQL (`schema.sql` / SQL directory, including `ENABLE ROW LEVEL SECURITY` and `CREATE POLICY`). `atlas migrate diff` writes versioned SQL. CI runs `atlas migrate lint` then `atlas migrate apply`. dbmate is the only other living language-agnostic SQL runner; keep it off the baseline.

**TS client flow:** SQL is the source of truth. After Atlas apply, `drizzle-kit pull` (prefer 1.0-rc.4 if you accept pre-release kit; otherwise 0.31.10) writes `schema.ts` as a **generated** file. Do **not** `pull` then `generate` as the migration loop. Stable 0.31.10 is not round-trip clean (#6093, 2026-08-04). Keep `drizzle-orm` **0.45.2** + `drizzle-kit` **0.31.10** on the baseline until 1.0 is `latest`. `drizzle-kit generate` is TS-first; that contradicts SQL-first.

**Rust access:** sqlx **0.9.0** `query!` against Postgres. Commit `.sqlx/`. CI: `SQLX_OFFLINE=true` and `cargo sqlx prepare --check`. Do not put a Supabase REST crate on the hot path.

**Python access:** official `supabase` **2.31.0** only for Data API / Auth / Storage. For SQL and RLS, `psycopg` (or async equivalent) on the same Postgres URL, same `set_config` pattern as Drizzle.

**Auth adapter seam (exact):**

```
IdP access JWT
  → stock JWKS verify (iss, aud, exp, alg pinned, kid)
  → ClaimMapper: { userId, tenantId, orgRole, permissions, pgRole }
  → either
       (a) Postgres transaction: set local role <pgRole>;
           set_config('request.jwt.claims', claims_json, true);
           set_config('request.jwt.claim.sub', userId, true);
       (b) PostgREST: Authorization: Bearer <jwt> only if TPA JWKS discovery is proven for that IdP
```

Mapper inputs: WorkOS `sub` / `org_id` / `role`+`permissions`; Clerk `sub` / `o.id` / `o.rol`+`o.per` (v2); Supabase Auth `sub` / `app_metadata` / Postgres `role`. Output `pgRole` is always `authenticated` or `anon`. WorkOS org `role` must not leak into `SET ROLE`.

**Disagreements with the stated preference (3)**

1. **`drizzle-kit pull` as the primary workflow instead of `generate`.** Pull is the right *derivation* step. It is not a stable migration engine on current stable kit. SQL + Atlas is the workflow; pull is codegen.
2. **`supabase-lib-rs` as a real client.** It is a 10-month-stale community crate. Python `supabase` is real. Rust should speak Postgres via sqlx.
3. **“Supabase reduced to a swappable adapter” via the Data API.** That only holds if PostgREST trusts the IdP JWKS. WorkOS TPA is documented and currently fails signature verification (#2476, open). The adapter that actually swaps is (a) above: JWKS verify in process, then session GUCs on a Postgres connection. Hosted Supabase Postgres is fine; PostgREST is optional.

SQL-as-SOT, Drizzle for TS ergonomics, and a swappable auth provider are all right. The pull-as-migrator, the Rust Supabase SDK, and PostgREST-as-the-seam are the parts that do not survive contact with August 2026 evidence.
