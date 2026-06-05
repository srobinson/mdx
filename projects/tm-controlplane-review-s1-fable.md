---
title: S1 control-plane identity+grants — adversarial review (Fable)
branch: controlplane-s1-identity @ a5b8a26
scope: git diff main...controlplane-s1-identity (36 files, +1437/-26)
date: 2026-07-11
process: code-review high effort (8 finder angles, recall-biased verify) + code-hygiene lens
verdict: no blockers; 9 minors + 1 low; builder trust HIGH
---

# Verdict

No correctness blocker. The six strictness areas of the brief all hold (evidence below).
Nine minor findings and one low, all fixable in one round. Tree verified pristine at
a5b8a26 before and after review; review was read-only.

# Brief strictness areas — evidence

1. **Token security: CLEAN.** Raw bearer flows mint → seed only; it lands exclusively in
   the run home (`.mcp.json` via `write_atomic_json`, `config.toml` via
   `_write_atomic_secret`, both mode 0600, home dir 0700). `PreparedControlPlaneGrant`
   carries only the SHA-256 digest. `capture_spawn_spec_payload` argv/env carry only the
   `--mcp-config` path and `CLAUDE_CONFIG_DIR`; manifests and lifecycle events carry no
   secret. Revoke = DELETE row; resolve is per-request, uncached, against the pool;
   `test_grants.test_resolve_bearer_and_revoke_kills_token` proves revoke kills the token
   and that the digest column does not embed the bearer bytes.
2. **Migration 0012: CORRECT SHAPE, one precedent divergence (F3).** Additive
   `control_plane_grant {run_id PK, role +CHECK, workspace_id, token_digest bytea UNIQUE
   +32-byte CHECK}`, chained 0011→0012, applies on fresh DB. Verified by running
   `test_control_plane_grants_migration` and the full `test_migrate` smoke against
   Postgres: 12 passed.
3. **Fail-closed: HOLDS.** `_persist_control_plane_grant` runs inside
   `prepare_captured_run` before the spawn spec returns; on persist failure it best-effort
   revokes, raises, and the outer teardown rolls back home, manifest, supervisor
   (test asserts source home byte-unchanged, runtime-home gone, supervisor
   terminated+restored). No session store → persist hook None → granted launch raises →
   503 `control_plane_grant_failed`. `StubCaptureAdapter` rejects grants (TS test pins
   `launch_failed`). Restart drops leases → `resolve_control_plane_grant` returns None →
   401.
4. **Home seeding: CLEAN.** Both harnesses covered; source home proven byte-unchanged in
   round-trip tests; Authorization header shape correct in both formats; atomic write
   breaks overlay symlinks so seeding cannot write through to the source home.
5. **Cross-process threading: CLEAN.** `runtimeRouter` normalizes absent → "none" and
   400s unknown values; `RunManager` forwards; `CaptureRpcClient` serializes;
   `PrepareCaptureRequest` defaults NONE. No None-leak path. workspace scope is the
   slug/hash WorkspaceId consistently on mint and resolve (but see F4: two fresh copies
   of the format string).
6. **Resolver: CLEAN.** bearer → digest row → live-lease + workspace binding → principal;
   `require_control_plane_principal` hands skins a resolved principal; no self-declared
   actor input anywhere. 401 body code `forbidden` follows the CONTROLPLANE.md error
   taxonomy verbatim (checked; not a defect).

Gates observed directly: `ruff format --check` (480 files), `ruff check`, `mypy` (no
issues), pytest 35+12 passed (incl. Postgres-backed grant + migration tests), vitest
`@tm/runtime` 158 passed.

# Findings (ranked)

**F1 (minor, correctness edge) `api/src/transport_matters/cli/codex_home.py` `_replace_toml_table`** —
A source Codex config declaring the server as an inline key under a bare table
(`[mcp_servers]` / `transport-matters = { ... }`) is not matched for removal (its table
path is `("mcp_servers",)`, not a prefix match), so the appended
`[mcp_servers.transport-matters]` header redeclares the key. Verified with tomllib:
`Cannot declare ('mcp_servers', 'transport-matters') twice` → seeding raises →
`ControlPlaneGrantPreparationError` → every granted Codex launch for that user 503s
until they hand-edit their config. Fail-closed, but a permanent, hard-to-diagnose
denial on a legal config shape. Handle the inline-key form or produce a targeted error.

**F2 (minor, structural) `api/src/transport_matters/captured_run_context.py` +
`captured_run.py`** — Grant provisioning (mint + seed) lives in the shared
`build_captured_run_context`, but persistence lives only in `prepare_captured_run`. The
other caller, `run_captured_run_on_local_tty`, would seed a bearer that is never
persisted (agent 401s forever, nothing revokes), and the `if write:` gate silently drops
a requested grant instead of failing closed. Latent today (grant is unreachable from the
CLI and write=False is only the print-command dry run), but the invariant "granted
request ⇒ persist hook present ⇒ write=True" is enforced nowhere; make
`build_captured_run_context` reject a granted request it cannot fully provision.

**F3 (minor, migration hygiene) `api/migrations/versions/0012_control_plane_grants.py:31`** —
The CHECK constraint folds in live `ControlPlaneGrantRole` values at import time.
Precedent (0009, 0011) freezes literal tuples inside the migration. When a role is added
later, fresh and old databases get different schemas under the same revision id. Freeze
the literals.

**F4 (minor, DRY) `api/src/transport_matters/controlplane/provisioning.py:57` +
`capture_rpc.py:119`** — Two new hand-rolled copies of the workspace identity string
`f"{slug}/{hash}"`, one writing the grant, one recomputing for the resolve equality
check; they must agree byte-for-byte or every bearer resolves to None. A third copy
already exists at `api/v1/run_storage.py run_workspace_id`. Promote one helper onto
`workspace.py` and use it at all three sites.

**F5 (minor, dead complexity) `api/src/transport_matters/capture_rpc.py`
`_prepare_with_dependencies`** — The two-arm conditional (call with or without the
grant kwargs) guards nothing: the `PrepareCapture` Protocol declares both kwargs with
defaults and every fake accepts `**kwargs`. It also encodes an implicit both-or-neither
invariant across two independent optional callables; collapsing persist+revoke into one
small port object (or always passing both) removes the branch and makes the coupling
type-level.

**F6 (minor, hygiene) `api/src/transport_matters/controlplane/grants.py`** — No
reconciliation for orphaned grant rows: SIGKILL/crash (revoke callback never runs) or a
failed revoke DELETE during release leaks rows forever. Fail-closed regardless (resolve
requires a live lease), but digests accumulate unbounded with no cleanup path; a startup
sweep or launch-time upsert-over-stale would close it.

**F7 (minor, DRY) `api/src/transport_matters/api/v1/controlplane_auth.py`** — Bypasses
the existing `raise_api_error` helper and writes the identical 503
`control_plane_unavailable` HTTPException twice in one function; collapse both branches.

**F8 (minor, DRY) `api/src/transport_matters/cli/codex_home.py`** —
`_replace_toml_table` re-implements table-boundary scanning beside the existing
`_find_table_end`; both walk `_TOML_TABLE_RE` (`^\s*\[`), which also false-matches
lines inside multi-line arrays (inherited weakness, now in two copies). Share one
boundary helper.

**F9 (minor, test hygiene) `api/src/transport_matters/cli/test_control_plane_grant_capture.py`** —
Both tests copy the ~18-field `CapturedRunRequest` literal and the full dependency-lambda
wall instead of extending the `_request`/`_prepare` builders already in
`cli/test_captured_run.py`.

**F10 (low, placement) `packages/runtime/src/adapters/StubCaptureAdapter.ts` +
`api/v1/capture_rpc_routes.py:260`** — The grant rejection is per-adapter (a future
third CapturePort that forgets the guard fails open), and `control_plane_url` derives
from the inbound Host header rather than server-owned config (correct on the loopback
deploy; fragile behind any proxy/host change). Both are one-line hardenings at the
shared seam.

# Noted, not findings

- `require_control_plane_principal` has zero callers and `/mcp` is not mounted — correct
  S1 scope (skins are a later slice), but granted runs spawned during the S1→S3 window
  carry an MCP client pointing at the SPA catch-all; expect visible MCP connect failures
  in agents until the skin lands.
- `release_capture` now emits RUN_EXITED even when lease cleanup fails — deliberate,
  test-pinned, and better than the old permanently-live zombie; the lifecycle event now
  matches registry state.
- `CapturedRunLease.close` ExceptionGroup change: all production callers use broad
  `except Exception`, no break; `run_captured_run_on_local_tty` predates and is
  unaffected.
- Conventions pass clean: module-privacy attribute access is the pre-existing idiom in
  those files and outside the boundary test's definition; import DAG unbroken
  (`controlplane/models` is a pure leaf; `run_lifecycle_contracts` imports nothing);
  singular table name matches every existing table; all files ≤438 LOC.

# Builder quality assessment (Stuart's standing request)

**Craftsmanship: strong.** Clean module shape (pure vocabulary in `models.py`, tokens
isolated, provisioning separate from persistence), conventions followed without being
told (frozen slotted dataclasses, chained exceptions, colocated tests, keyword-only
seams), and one genuinely thoughtful hardening beyond the letter of the spec: making
`CapturedRunLease.close` attempt every cleanup so the revoke callback cannot be skipped
by an earlier teardown failure, with a test pinning the order.

**Test rigor: real, not tautological.** The red paths are the ones that matter and they
assert observable end-state: persist-failure rollback checks the source home
byte-for-byte, runtime-home removal, manifest absence, and supervisor
terminate/restore counts; revoke-kills-token runs against real Postgres and additionally
asserts the digest column does not contain the bearer bytes; the migration test
round-trips upgrade/downgrade and provokes the CHECK violation; the TS side pins the
stub fail-closed contract. No test in the diff merely re-asserts its own setup.

**Spec + reuse fidelity: high.** Every locked identity decision is implemented as
specified (mint inside the capture lease, digest-only persistence, persist-before-return,
fail-closed, per-request uncached resolve, live-lease binding, slug/hash scope, both
harness home formats, stub rejection). Reuse map respected: seeder registry extended
rather than forked, `home_io` atomics reused, existing `connect`/pool infra reused, no
parallel implementations introduced.

**Shortcuts/gaps: the minors above.** The pattern in the misses is consistent: local
copies where a shared helper was one search away (F4, F7, F9), a defensive branch instead
of a firmed-up contract (F5), and precedent not checked for the migration idiom (F3). No
overreach; scope is tight to S1.

**TRUST VERDICT: HIGH.** Zero correctness defects in an identity/persistence slice with
real adversarial surface, pervasive fail-closed instincts, and failure-path tests that
would have caught its own bugs. Suitable for sizeable delegated scope. The watch-item for
future briefs: DRY and repo-precedent checks trail this repo's zero-tolerance bar, so
briefs should keep naming "search before writing" explicitly and reviews should keep a
duplication pass.
