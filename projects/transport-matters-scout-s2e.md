# Scout S2e: compatibility fact artifact + versioned reader dispatch

Baseline: main @ 4de2e213 (S2d.1 merged). Scope per RUNTIME-SURFACING-S2-PLAN.md § "S2e. Compatibility facts and historical dispatch" and HARNESS-COMPATIBILITY.md § "Historical read compatibility".

## Scope extracted from the plan

S2e delivers exactly two things:

1. The durable compatibility fact artifact: schema, run directory path, write ordering, owner (the capture boundary), written for every gated launch and mirrored into the control plane audit.
2. A versioned session and transcript reader registry dispatching by recorded revisions. Absent recorded revision returns `historical_contract_unsupported`. The continuation bridge is S3.

Boundaries confirmed: S2f owns the resolver, `launch_options()`, the compatibility application service, and the launch seams that CONSUME the artifact ("Record compatibility facts on every gated run through the S2e artifact" is S2f item 5). S2g owns inventory and first run. S2e produces the artifact writer and reads it back; no launch gating and no production `match_release` call site lands in S2e.

## Reuse Map

### (a) Fact artifact contents and write location

Contents are contract-fixed by HARNESS-COMPATIBILITY.md § "Historical read compatibility" — every run records:

- compatibility release id and digest → `HarnessCompatibilityRelease.release_id` / `release_digest` (harnesses/compatibility.py)
- exact harness version and executable identity → `LocalHarnessObservation.normalized_version` / `executable_identity` / `executable_path` (harnesses/connections.py)
- every adapter and contract revision → the 14 `RELEASE_REVISION_FIELDS` (`RELEASE_FACETS`, harnesses/compatibility.py)
- target catalog and local observation revisions → `target_catalog_revision`, `LocalHarnessObservation.observation_revision`
- schema, fixture, and evidence digests → `HarnessCompatibilityRelease.schema_digests` / `fixture_set_digest` / `evidence_digest`

Placement per plan § "Data placement": run directory launch facts + control plane audit mirror. `sessions.json` is never extended, so the artifact is a NEW sibling file in the run dir. Owner of run-dir filenames: `DiskStorageLayout` (storage/disk_layout.py) — add a `compatibility_facts_path` beside `sessions_facts_path`; do not hand-build paths.

Write-pattern precedent (REUSE, same shape): storage/session_facts.py `write_owned_session_facts` — pydantic frozen model, upsert, tempfile + `Path.replace` atomic write, read side returns `None` when absent. Its writer seam precedent: cli/launch_profile.py `persist_owned_session_facts`, called by the launcher inside the per-run lock, before the retry loop, before any wire frame. The capture boundary composition roots are `prepare_captured_run` / `run_captured_run_on_local_tty` (captured_run.py) — but the production invocation on gated launches is S2f; S2e ships the writer + its unit seam only.

Audit mirror precedent (REUSE): `ControlPlaneAuditSink` / `ControlPlaneAction` (controlplane/audit.py), exactly how `DriftEmitter` (harnesses/drift_emitter.py) mirrors drift evidence with `store + audit` fields. No new audit machinery.

Schema version precedent: `MANIFEST_SCHEMA_VERSION` + schema-gated parse in compatibility_store.py `embedded_compatibility_manifest` / `validate_channel_update`. The artifact must carry its own `fact_schema_version` (name TBD) from day one; validated-read precedent also in runtime_registry.py `read_runtime_template_capabilities` (strict `model_validate`, typed error, never guess).

### (b) Versioned reader dispatch

- Existing reader registry: index/adapters/`__init__.py` `get_adapter(harness)` — harness-keyed, 23 LOC, lazy singleton dict. This is the ONE registry to generalize; do not stand up a second dispatch map elsewhere.
- Historical read consumer: session/backfill.py `_replay_owned` → `get_adapter(owned.harness)` + `decode_source_descriptor` + `DiskStorageLayout.transcript_snapshot_path`. This is where recorded-revision dispatch must thread through.
- Revision vocabulary already exists: `transcript_reader_revision`, `transcript_locator_revision`, `session_bootstrap_revision` on `HarnessCompatibilityRelease`; installed revisions enumerated as `INSTALLED_ADAPTER_REVISIONS` (`{harness}-{facet}-r1`, compatibility_store.py). Today's adapters ARE revision r1; the registry maps (harness, recorded revision) → the existing `ClaudeAdapter` / `CodexAdapter`.
- A revision-keyed reader registry: **none found** (searched `schema_version`, `ADAPTERS_VERSION`, `historical_contract_unsupported`, reader/registry symbols across api/src; `historical_contract_unsupported` appears only in contract docs and the plan). This is the genuinely new piece, but it is a thin keyed layer over `get_adapter`'s existing pattern.

### (c) Forward/backward compat contract

- Absent artifact / absent recorded revision (every pre-S2e run dir) → `historical_contract_unsupported` per plan S2e item 2.
- Unknown recorded revision (artifact from a newer build naming a reader this build lacks) → `historical_contract_unsupported` with the missing revision, per HARNESS-COMPATIBILITY.md: "never a guessed parse through the current adapter".
- Unknown artifact schema version (newer `fact_schema_version`) → same outcome; the read must be schema-version-gated like `validate_channel_update` gates `manifest_schema_version`.
- Reader removal is contract-bound: only after a deterministic migration produced an equivalent supported artifact (HARNESS-COMPATIBILITY.md § Historical read compatibility). Not an S2e concern beyond not blocking it.

### (d) Migration need

None. The artifact is a run-dir file; the audit mirror writes rows into the existing `control_plane_action` table via `ControlPlaneAuditSink`. Executor evidence tables (harness_observation etc., harnesses/connections.py) already exist from S2c/S2d (api/migrations/versions through 0017). No DDL, `just migration-smoke` unaffected — unless review decides the audit mirror needs its own table, which the plan does not ask for.

### (e) S2e/S2f boundary

S2e ships: artifact model + schema version, `DiskStorageLayout` path, writer (atomic, idempotent), audit mirror call, reader registry + revision dispatch, `historical_contract_unsupported` outcome plumbing, fixtures. S2e does NOT ship: any call from `prepare_captured_run` / `run_captured_run_on_local_tty` / `run_codex` into the writer (S2f), any `match_release` production call (S2f), any inventory join (S2g). The writer takes already-resolved facts as input; it never resolves a release or runs a probe.

## Quality Map

Scoped hygiene pass (report-only; measurements via `wc -l`, outlines via fmm):

- File sizes: compatibility.py 553, launch_profile.py 300, backfill.py 287, compatibility_store.py 258, connections.py 242, disk_layout.py 177, audit.py 148, session_facts.py 98, adapters/__init__.py 23. All under the 700 hard limit, but compatibility.py at 553 has no room for a new model family → the artifact model belongs in a NEW module (e.g. `harnesses/compatibility_facts.py`), importing the release vocabulary, not extending compatibility.py.
- Duplication already in scope: session_facts.py hand-rolls tempfile+replace while storage/disk_helpers.py `DiskStorageFileOpsMixin._atomic_write_model_json` implements the same atomic JSON write as a private mixin method. A third copy for the fact artifact would triple it. Recommend the builder promote one public atomic-write-JSON helper (disk_helpers.py is the natural owner; note the private-import boundary test forbids importing the private mixin method) and have session_facts + the new writer share it. Small, in-slice, DRY-mandated.
- Hardcoded harness seams in scope: `INSTALLED_ADAPTER_REVISIONS` builds from a literal `("claude", "codex")` (compatibility_store.py) and `HARNESSES` maps literal names (cli/launch_profile.py). Both are S2-completion-criterion-2 targets but owned by other slices; S2e must not add a NEW hardcoded harness list — key the registry off descriptors/`HarnessId`.
- Clean: audit.py, disk_layout.py, adapters/__init__.py are tight single-owner modules; extend, don't fork.

## Plan

1. `harnesses/compatibility_facts.py` (new): frozen pydantic artifact model carrying `fact_schema_version`, release id + digest, observed version + executable identity, the 14 revision fields (reuse `RELEASE_REVISION_FIELDS`), observation revisions, digests. Fixture-backed round-trip tests.
2. `DiskStorageLayout.compatibility_facts_path` + writer module beside session_facts.py (or in it if cohesion holds and LOC stays sane): atomic, idempotent, read side returns typed absent. Shared atomic-write helper promoted per Quality Map.
3. Audit mirror: compose a `ControlPlaneAction` (new verb) and write through the injected `ControlPlaneAuditSink`, mirroring the `DriftEmitter` wiring shape.
4. Versioned reader registry: generalize index/adapters/`__init__.py` `get_adapter` to revision-aware lookup (harness + recorded transcript_reader/session_bootstrap revision → adapter), registering today's adapters at their r1 revisions; unknown/absent → `historical_contract_unsupported` (typed error or outcome, matching contract outcome codes).
5. Thread recorded-revision dispatch through session/backfill.py `_replay_owned` reading the artifact beside `sessions.json`; absent artifact → `historical_contract_unsupported` for that run's historical read path.
6. Fixtures per plan § Verification: "Recorded compatibility revisions round trip from launch facts to historical reader dispatch" — write artifact, read back, dispatch selects the right reader; unknown revision and absent artifact both surface the outcome code.
7. Gates: `just check` + `just test-affected` (builder loop); grok runs full `just check` + `just test` + migration-smoke pre-merge.

Versioning-risk verdict: the artifact needs its schema version and the unsupported-outcome path from the first commit; the main design risk is inventing a second dispatch/atomic-write path instead of generalizing `get_adapter` and the existing atomic-write pattern. Blast-radius note: once dispatch is revision-gated, ALL pre-S2e run dirs read as `historical_contract_unsupported` — plan-sanctioned, and this repo carries no backward-compat obligation, but the builder brief should state it explicitly so the replay/backfill behavior change is deliberate.
