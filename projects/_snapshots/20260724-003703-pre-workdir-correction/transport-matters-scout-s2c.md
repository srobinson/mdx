# Scout: S2c observations, probes, connections (executor tables; the S2b seam's first production consumer)

Baseline: main @ 747e0577 (S2b merged). Tree pristine, no source writes.
Governing docs: RUNTIME-SURFACING-S2-PLAN.md (section "S2c. Observations, probes, and
connections", "Decisions folded into this plan", "Data placement", "Ownership");
HARNESS-COMPATIBILITY.md (sections "Version enforcement", "Local target observation",
"Channel state", "Outcome codes"); COMPATIBILITY-PUBLISHING.md ("Detection",
"Publication"); api/CLAUDE.md (import DAG, async boundary, module privacy).

## Scope reconciliation (brief vs plan)

The brief names S2c "executor tables + activation service". The plan's S2c section is
"Observations, probes, and connections" with five items: (1) Postgres tables for
observations, connections, and executor blocks; (2) a connection-scoped probe runner
with isolation and redaction gates; (3) the three probe adapters with both auth-state
fixtures; (4) target observation adapters (grok native catalog; codex and claude
declare honest completeness); (5) connection records, sole-connection resolution,
explicit default selection, `connection_ambiguous` on violation.

There is no "activation service" in plan-S2c, and nothing called activation writes to
the executor tables. Channel-pointer activation is package-embedded publisher data
(S2b store); the conformance-gated flip to `active` plus enforcement is S2g. The
executor tables hold *evidence* (observations, connections, executor-origin blocks).
What the brief's phrase maps to in wire reality: S2c builds the first production
consumer of the S2b compatibility store. Today `match_release`,
`embedded_channel_state`, `embedded_release_entry`, and
`embedded_compatibility_manifest` have zero production callers (grep across `api/src`
excluding tests: none) — the S2b seam is dormant until S2c's observation service reads
the active release and its certified routes to stamp `compatibility_release_id` and
`route_id` onto access observations.

Lines against later slices (do not build ahead):
- **S2c/S2d:** plan-S2c item 1 names the executor-blocks *table*; plan-S2d owns
  VersionBlock persistence *logic* (write paths, supersession, enforcement wiring,
  drift emitters). Recommend: S2c ships the table DDL with no write path; S2d fills it.
- **S2e:** no compatibility fact artifact, no reader registry.
- **S2f:** no resolver, no launch gating, no setup actions (the user-confirmed "test
  access" action is `setup_adapter_revision` territory, S2f item 4 — S2c access
  evidence comes only from nonconsuming probes; where none exists, access stays
  `unknown`).
- **S2g:** no inventory service, no REST/MCP surface, no startup refresh, no pointer
  activation. All four embedded channel pointers are `paused`
  (`compatibility_releases_v1.json`: stable/preview × claude/codex, `expires_at` null).
- **Nuance for the builder:** with pointers paused, `match_release` returns
  `compatibility_release_unavailable` — that gates *authorization*, not evidence.
  Observations are still recordable against the pointer's `active_release_id`;
  the contract ("Local target observation") makes `compatibility_release_id` null only
  when the observed version is outside every certified range.
- `sessions.json` is never extended (plan "Decisions" block).

## Reuse Map

| S2c capability | Existing owner | Verdict |
| --- | --- | --- |
| Contract vocabulary (outcomes, `normalize_version`, `compare_versions`, `is_expired`, `match_release`) | `harnesses/compatibility.py` (pure leaf, S2b) | reuse as-is; do not re-declare outcome literals |
| Active release + routes for a channel/harness | `harnesses/compatibility_store.py` `embedded_channel_state`, `embedded_release_entry` | reuse as-is; S2c is their first production caller. Route ids in embedded data: `claude.anthropic.oauth`, `codex.chatgpt.oauth` |
| Channel id | `channel.py` `resolve_channel_spec().id` | reuse; never a second channel enum (S2b Quality Map rule holds) |
| Harness identity + descriptors | `harnesses/__init__.py` `HarnessDescriptor`, `list_harness_descriptors`, `HarnessId` | reuse; grok registered, launch-ineligible (`launch=None`) |
| Installation + raw version probe | `capabilities.py` `detect_harness_descriptor`, `_probe_harness_version` (2s timeout, raw first line, None on failure) | reuse as the `LocalHarnessObservation` input; add normalization at the write path via `normalize_version` |
| Postgres store shape | `controlplane/grants.py` `ControlPlaneGrantStore`: frozen dataclass, module-level SQL f-strings over table constants from the domain's models module, sync `connect(database_url)` writes + async pool reads. `controlplane/models.py` owns `CONTROL_PLANE_GRANT_TABLE` | mirror exactly. Table constants belong to the owning domain module (harnesses side), not scattered strings |
| Pool/connect | `session/pool.py` `connect`, `create_async_pool` | reuse; no session→harnesses import exists today, so `harnesses/connections.py` importing `session.pool` creates no cycle (verified by grep) |
| Migration machinery | `session/migrate.py` (`apply_migrations` advisory-locked, `sql_text_values` for CHECK enums), `migrations/env.py` | reuse; authoring convention below |
| Enum → CHECK constraint | `migrations/versions/0012_control_plane_grants.py` pattern: raw SQL `op.execute`, `sql_text_values(...)`, named constraints, full `downgrade()` | mirror |
| Row models | `session/models.py` (`SessionRow` et al., pydantic frozen) or domain-side frozen models per `controlplane` precedent | follow controlplane precedent: rows live with the domain store |
| Probe subprocess idiom | `capabilities.py` `_probe_harness_version` (capture_output, check=False, timeout, exception → None) | mirror for `codex login status` / `claude auth status --json`; grok is S2h |
| Per-harness home env for connection-scoped context | `launch_environment.py` `HOME_DIR_ENV_BY_HARNESS` (`CLAUDE_CONFIG_DIR`, `CODEX_HOME`) | reuse; do NOT mint a second harness→env map in probes (see Quality Map H2) |
| Secret redaction for probe evidence | none fits. `transport_redaction.py` is transport-header scoped (`redact_transport_artifacts`); probe output is a different shape | new: store status enums + sanitized `canonical_digest` evidence only; raw probe output and secrets never reach Postgres (plan-S2c item 2 gate) |
| Evidence digest | `canonicalization.py` `canonical_digest` (S2b promotion) | reuse as-is |
| Connection records (`HarnessConnection`), observation rows, sole/default resolution, `connection_ambiguous` | none found. Searched `HarnessConnection`, `LocalHarnessObservation`, `LocalHarnessAccessObservation`, `LocalTargetObservation` across `api/src` and `www`: docs only | new, per plan Ownership: `harnesses/connections.py` + Postgres tables; probes under `harnesses/probes/` per-harness modules |
| Test DB harness | `session/testing.py` `TestDb` (template-clone per worker), `test_db` fixture | reuse for store + migration tests |
| Probe fixtures both auth states | precedent: `harnesses/compatibility_test_support.py`, parametrize matrices in `harnesses/test_compatibility.py` | mirror; captured-output fixtures per adapter |

## Quality Map

Scope swept (analysis only): `harnesses/*` (compatibility, store, registry, tests),
`capabilities.py`, `cli/codex_session.py`, `session/{migrate,testing,test_migrate,
test_migration_roundtrip,backfill,models,pool,writer,wire_store}.py`,
`controlplane/grants.py`, `launch_environment.py`, `transport_redaction.py`.

Sizing: green. Largest scoped source `writer.py` 680 LOC (S2c should not touch it —
observations are a new domain store, not a SessionWriter concern); `compatibility.py`
550 (pure models only; persistence must NOT land there); `test_migrate.py` 626 —
**watch, nearing the 700 hard limit**: S2c migration tests must go in a new focused
file (`test_..._migration.py` per the 0012/0013/0019 convention), never grow
`test_migrate.py` beyond the required `reset_to_unmigrated` additions.

- **H1 duplication, now due (carried from S2b D1):** two `--version` interpretations
  persist. `capabilities.py` `_probe_harness_version` (raw first line, None on
  failure) vs `cli/codex_session.py` `_run_codex_cli_version` (trailing token, 5s,
  `0.0.0` sentinel, mtime-keyed cache; sole caller `cli/launch_profile.py` for rollout
  metadata). `compatibility.py` `normalize_version` deliberately excludes extraction:
  "Extraction from raw --version output belongs to the observation adapter". S2c
  creates that adapter owner when it writes `LocalHarnessObservation.normalized_version`.
- **H2 hardcoded harness seam adjacent to the probe runner:**
  `launch_environment.py` `HOME_DIR_ENV_BY_HARNESS` is keyed by
  `HARNESS_NAME_CLAUDE/CODEX` constants, not descriptors (an S2a leftover: "no
  production code path names a harness outside descriptor registration" is an S2
  completion criterion). The probe runner needs exactly this fact ("connection's exact
  environment and credential context"). Building a fourth map would be a regression;
  consuming this one keeps a single owner. Generalizing it onto `HarnessDescriptor`
  is the elegant fix but touches launch paths — acceptable to defer with a named
  pointer if the slice is heavy.
- **H3 boundary character change:** `harnesses/` is today a pure-ish leaf (only
  `importlib.resources` reads). Plan Ownership puts `connections.py` + Postgres there,
  which imports `session.pool` (psycopg). Precedent exists (`controlplane/grants.py`
  does exactly this) and no cycle results, but the split must stay clean: pure models
  and resolution logic (sole/default/`connection_ambiguous`) separate from store I/O,
  matching `compatibility.py` (pure) vs `compatibility_store.py` (I/O). The
  private-import boundary test (`test_private_import_boundary.py`) applies.
- **H4 migration gate shape:** `just migration-smoke` runs ONLY
  `session/test_migrate.py`. The roundtrip (`test_migration_roundtrip.py`) and the
  per-migration focused tests run under full `just test`. A builder who greens
  migration-smoke alone has not proven the new DDL. Also: `reset_to_unmigrated` in
  `test_migrate.py` must drop the new tables (else re-upgrade collides on CREATE
  TABLE), `EXPECTED_MIGRATION_HEAD_REVISION` in `session/testing.py` must be bumped,
  and `test_migration_roundtrip.py` must gain the new present/absent assertions at the
  right revisions.
- **Dead code:** none found in scope. S2b's flagged `detect_harness` (singular) is
  already gone from `capabilities.py`.
- **Async boundary note:** api/CLAUDE.md wants I/O async; the grants precedent mixes
  sync writes with async reads. Probe subprocess execution is blocking — run it off
  the event loop (`asyncio.to_thread`, the `main._start_session_store` idiom) and keep
  it out of startup (nonblocking refresh is S2g; S2c should expose the runner, not
  hook it into boot).

## Persistence and migration facts (mandated by the brief)

**(a) Alembic convention.** `api/migrations/versions/NNNN_name.py`, sequential
zero-padded ids, `revision`/`down_revision` strings, raw SQL via `op.execute`
(no SQLAlchemy metadata; `env.py` has `target_metadata = None`), CHECK enums via
`session/migrate.py` `sql_text_values`, named constraints, symmetric `downgrade()`
mandatory (every existing migration has one; roundtrip walks head→0002 and back).
Runtime auto-migrates in `main.lifespan` → `_start_session_store` →
`apply_migrations` (fast-path head check, `pg_advisory_lock` serialized). Testing:
`just migration-smoke` = `pytest src/transport_matters/session/test_migrate.py`;
focused per-migration test file with data seeded at the prior revision, upgraded,
constraint-checked, downgraded (0012/0019 pattern); roundtrip assertions; head
constant in `session/testing.py`.

**(b) Storage-version bumps and the rehydrate contract.** The Postgres store has no
separate storage-version: the alembic revision IS the schema version (plus
`manifest_schema_version` for embedded compatibility data — unchanged by S2c since
executor evidence is Postgres, not signed data). Rehydrate/backfill contract is
SKIP, never wipe: `session/backfill.py` `backfill_session_spaces` marks unresolvable
rows (`legacy_unassigned`, `seen_unresolved`) and moves on; transcript replay
(`replay_transcript_run`) returns early on missing facts/snapshots rather than
deleting. S2c's tables are greenfield evidence tables — no backfill of existing data
is needed and none should be written; freshness is contract-owned
(`observation_stale`), so old rows age out logically, not destructively.

**(c) The activation seam.** Producers: publisher-signed data → embedded manifest
(`compatibility_store.embedded_compatibility_manifest`, validated at first read) or a
future verified cached update (`validate_channel_update`, currently rejected wholesale
by `RejectAllSignatureVerifier`). Consumers: none in production today. "Activation"
writes nothing to executor tables — it is the channel pointer (`active_release_id`,
`status`) inside signed data; executor tables receive only local evidence rows keyed
by release/route ids read from that pointer. The S2c seam: observation/connection
service reads `embedded_channel_state` + `embedded_release_entry` for route identity;
`match_release` stays uncalled until S2f wires the gate at the three launch
preparation seams (plan Ownership row "Launch gating").

**(d) codex_session version fold.** Belongs in S2c: the plan defers it as "S2c/S2f",
and S2c is where the extraction owner is born (H1). Concretely: one public extraction
helper in the observation adapter that turns raw `--version` output into a
`normalize_version` input; `LocalHarnessObservation` writes normalized (retaining
`raw_version` per contract); `cli/codex_session.py` `resolve_codex_cli_version` keeps
its never-fail semantics (its `0.0.0` sentinel and mtime cache stay at that call site
— session bootstrap metadata must not gate a launch) but delegates extraction to the
shared owner. Single caller (`cli/launch_profile.py`), so blast radius is one file
plus tests. If the slice runs heavy, the delegation (not the owner) may slip to S2f;
creating a third interpretation may not.

## Plan

Suggested build order, one migration, no changes to existing tables:

1. **Contracts + models (pure):** `harnesses/connections.py` — `HarnessConnection`,
   `LocalHarnessObservation`, `LocalHarnessAccessObservation`,
   `LocalTargetObservation` frozen pydantic models field-for-field from
   HARNESS-COMPATIBILITY.md ("Version enforcement", "Local target observation");
   table-name constants beside them (controlplane precedent); pure sole/default
   resolution returning `connection_ambiguous` on violation.
2. **Migration `0022_harness_executor_tables`:** three tables (observations,
   connections, executor blocks), CHECK enums via `sql_text_values` (auth status,
   access status, completeness, block scope/origin/status), named constraints,
   symmetric downgrade. Update `reset_to_unmigrated`, bump
   `EXPECTED_MIGRATION_HEAD_REVISION`, add focused
   `session/test_harness_executor_tables_migration.py` + roundtrip assertions.
   Executor-block table ships DDL-only; write paths are S2d.
3. **Store (I/O):** mirror `ControlPlaneGrantStore` — frozen dataclass, SQL constants
   over the table names, upsert semantics for observations (latest per
   executor/harness/connection), reads for the future inventory join. Survives
   restart by construction; supersession columns present, unexercised until S2d.
4. **Probe runner:** connection-scoped env assembly reusing `HOME_DIR_ENV_BY_HARNESS`
   (H2 — no new map); subprocess off-loop with hard timeout; isolation tests (ambient
   credentials cannot bleed across connections) and redaction tests (raw output and
   secrets never reach Postgres; sanitized `canonical_digest` evidence only) gate the
   boundary per plan-S2c item 2.
5. **Probe adapters:** `harnesses/probes/` per-harness modules. codex `codex login
   status` (text + exit code), claude `claude auth status --json` (structured; exit
   encodes state), both with logged-in and logged-out captured fixtures. Grok adapter
   module registers the exit-code trap shape but the real catalog probe is S2h.
6. **Target observation adapters:** codex/claude declare honest completeness
   (`complete`/`partial`/`failed` absence semantics per contract); observation rows
   carry `compatibility_release_id` from the embedded pointer when in range, null
   otherwise.
7. **Version fold (H1/d):** extraction helper in the observation adapter;
   `resolve_codex_cli_version` delegates, sentinel stays local.

Gates, verbatim: `just check`, `just test`, and `cd api && just migration-smoke` —
judged by output content, not pipe exit codes. Full `just test` is the authoritative
migration proof (H4).

**Migration-risk verdict:** low for data loss — purely additive DDL, no ALTER on
existing tables, no backfill, downgrade drops only the new tables. The concentrated
risks are instead (1) secret leakage into Postgres via probe evidence — the redaction
gate is the real blocker-class test; (2) `reset_to_unmigrated`/roundtrip drift
breaking `just test` for every later PR; (3) scope creep into S2d block logic or S2f
gating through the dormant `match_release` seam.

**Reuse verdict:** the evidence tables, connection records, probe runner, and probe
adapters are genuinely greenfield (no prior art anywhere in `api/src`), but every
supporting mechanism has one existing owner to reuse — S2b vocabulary and store,
grants-store shape, migration machinery, subprocess probe idiom, home-dir env map,
canonical digest — and the two active duplication traps are the version-extraction
fork (fold it, H1) and a second harness→env map (don't, H2).
