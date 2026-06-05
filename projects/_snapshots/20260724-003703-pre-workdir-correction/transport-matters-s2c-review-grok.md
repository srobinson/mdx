# Adversarial review: PR #294 (S2c observations, probes, connections)

| Field | Value |
| --- | --- |
| PR | https://github.com/littleorgans/transport-matters/pull/294 |
| Base | `main` @ `747e0577` |
| Head | `feat/s2c-observations-probes-connections` @ `43ba3ce3` |
| Diff | `gh pr diff 294` (25 files, +2622 / −3) |
| Tree at review | clean, branch matches head SHA |
| Mode | read-only review; no gates run; shared tree untouched |
| Counts | **0 Blocker / 1 Major / 4 Minor** |

## Summary

S2c lands a clean Postgres evidence layer: pure `connections.py`, I/O in `connections_store.py`, migration 0022 additive with symmetric drop, probe runner with home isolation + redaction, three adapters (grok trap-shaped), version extraction owned once and used by `codex_session`, do-not-build-ahead lines held (no block write path, no `match_release` production call, no inventory/REST/startup hook).

The secret/redaction gate is real: adapters sanitize method fields, failure reasons are fixed literals, failure digests use exception type only, and `test_probe_secrets_never_reach_postgres` scans raw access rows. Isolation tests prove ambient harness homes are stripped and connection homes do not cross.

One Major: connection upsert can re-scope a `connection_id` under a different executor/harness while access rows only FK on `connection_id`, so evidence can desync without a constraint failure.

## Gate checklist (focus areas)

| Gate | Verdict |
| --- | --- |
| Secret redaction → Postgres | **Pass** (auth path). Status enums + optional fixed `reason`; no raw stdout/stderr columns; secrets not in evidence dump or access rows. `evidence_digest` is sha256 of capture (or failure type) and is *not* on `LocalHarnessAccessObservation` / access table (matches contract field list). |
| Isolation (ambient credentials) | **Pass for home-dir model**. All `HOME_DIR_ENV_BY_HARNESS` keys stripped; connection home reapplied. Residual: non-home env credentials (see Minor). |
| Migration 0022 | **Pass**. CREATE only; CHECK via `sql_text_values`; symmetric DROP of the five new tables; `reset_to_unmigrated` drops them; head constant bumped; roundtrip present/absent wired. Focused test constraint/cascade coverage is real. Seed-at-prior *shape* is soft (Minor). |
| Pure leaf / store split | **Pass**. `connections.py` has no I/O; store owns SQL/`connect`/pool; private-import shape clean (no `_` private modules). |
| Probe runner | **Pass**. `asyncio.to_thread` + hard timeout; not referenced from lifespan/startup. |
| Store upsert latest | **Pass**. Per executor/harness, per connection, per native model; restart-durable by Postgres; block table DDL-only, supersession columns unexercised. |
| Adapters | **Pass**. Claude/codex both auth states; method allowlists; grok r0 always unknown (`probe_adapter_pending`). |
| Resolution | **Pass**. sole / default / ambiguous / missing + mixed-scope caller bug. |
| Do-not-build-ahead | **Pass**. No executor-block write path; `match_release` uncalled from production S2c code; no inventory/REST/activation; targets attribute via `embedded_channel_state` only. |
| Version fold | **Pass**. `extract_normalized_version` sole interpretation; `resolve_codex_cli_version` delegates; `0.0.0` + mtime cache stay local; unorderable → sentinel test added. |
| Test rigor | **Mostly pass**. Redaction/isolation/migration/store assertions would fail without the impl. Claude redaction assert is weaker than codex/runner (Minor). |

## Issues

### Issue 1 — Severity: Major
- **File:** `api/src/transport_matters/harnesses/connections_store.py:44-51`
- **Description:** `_UPSERT_CONNECTION_SQL` on conflict updates `executor_id` and `harness_id` for an existing `connection_id`. Access observations FK only `connection_id` (`0022` lines 110–113) and carry their own `harness_id` / `route_id` with no composite check. A rescope of the connection row leaves (or accepts) access rows whose harness/route no longer match the parent, still visible under the old harness filter until manually repaired. Latest-per-connection evidence then lies about scope.
- **Suggestion:** On conflict, treat identity as immutable: update only `route_id`, `home_dir`, `is_default`, `revision` (and leave `created_at` write-once). Reject or no-op if `EXCLUDED.executor_id/harness_id` differ. Optionally add a trigger or store-level join assert that access `harness_id`/`route_id` match the parent connection before upsert.
- **Status:** open

### Issue 2 — Severity: Minor
- **File:** `api/src/transport_matters/session/test_harness_executor_tables_migration.py:118-211`
- **Description:** Scout mandated shape is seed at prior revision → upgrade → constraint-check → downgrade. This focused test starts at head (fixture-migrated), inserts, checks, then downgrade/upgrade. Upgrade path and constraints are exercised, but the file does not seed under `0021_wire_response_completion` before applying 0022. Fine for pure CREATE TABLE today; weaker template if 0022 later gains backfill.
- **Suggestion:** Mirror `test_wire_response_completion_migration.py`: downgrade to 0021, assert tables absent, upgrade to head, then insert and check constraints, then downgrade again.
- **Status:** open

### Issue 3 — Severity: Minor
- **File:** `api/src/transport_matters/harnesses/probes/test_claude.py:66`
- **Description:** Redaction assert is `stdout not in model_dump(...).values()`, which only catches full-string equality of a field to the entire stdout. Substring leakage into a field would pass. Codex/runner tests use `_SECRET not in str(dump)` and are stronger.
- **Suggestion:** Align with runner: inject a secret token into malformed JSON fixtures and assert `secret not in str(evidence.model_dump(mode="json"))`.
- **Status:** open

### Issue 4 — Severity: Minor
- **File:** `api/src/transport_matters/harnesses/probes/runner.py:57-65`
- **Description:** Isolation strips only `HOME_DIR_ENV_BY_HARNESS` values. Ambient provider credential env vars (`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, and similar) still flow from `base_env` into every probe. Correct for the contract’s home-dir credential model and matching tests; incomplete if any harness honors env API keys when the selected home is empty or login_required.
- **Suggestion:** Document the home-only isolation contract next to `probe_environment`, or strip a shared denylist of provider credential env keys when assembling probe env (single owner, no second harness map).
- **Status:** open

### Issue 5 — Severity: Minor
- **File:** `api/src/transport_matters/harnesses/connections_store.py:44-51` (also `214-216`)
- **Description:** (a) Upsert rewrites `created_at` from the payload, so “created” is not durable. (b) `upsert_access_observation` does not verify the parent connection’s harness/route before insert; only FK existence is enforced. Related to Issue 1 but caller-level rather than identity mutation.
- **Suggestion:** `created_at = COALESCE(harness_connection.created_at, EXCLUDED.created_at)` or omit it from DO UPDATE; load parent connection and reject harness/route mismatch on access upsert.
- **Status:** open

## Code hygiene (scoped to the 25 changed files only)

| Check | Result |
| --- | --- |
| New file LOC | All under 700 (largest new source: store 262, connections 228, migration 200, test_runner 211, migration test 324) |
| `test_migrate.py` growth | +drops only; 638 LOC, under 700; focused tests correctly live in `test_harness_executor_tables_migration.py` |
| Duplication | Table names duplicated migration-local vs `connections.py` (normal for Alembic). Fixture builders centralized in `connections_test_support.py`. HOME env map reused, not redeclared. |
| Boundaries | Pure leaf vs store is the right seam; probes package vocabulary vs per-harness adapters is clear; runner is the only subprocess owner. |
| Dead / ahead | No executor-block store methods; no REST; no startup probe registration. |
| Naming / craft | Outcome vocabulary and comments match the contract (`connection_missing` vs `connection_unavailable` called out explicitly). |

No hygiene-driven refactors recommended before merge beyond Issue 1’s store identity fix.

## Craftsmanship verdict

Tight S2c evidence slice: correct ownership, real redaction/isolation tests, migration and do-not-build-ahead discipline; fix connection upsert identity mutability before this store grows production writers.
