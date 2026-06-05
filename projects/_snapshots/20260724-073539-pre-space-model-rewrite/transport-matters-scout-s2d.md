# Scout S2d: VersionBlock persistence, supersession, drift emitters

Baseline `main @ 6d41d5ca` (S2c merged). Scope per RUNTIME-SURFACING-S2-PLAN.md
"S2d. Drift evidence and block store". Tree pristine, no source writes.

## Scope boundary (plan-confirmed)

S2d owns (plan `### S2d`): (1) `VersionBlock` persistence with scope keys, origin,
status, supersession, plus pure enforcement functions and outcome mapping fixtures;
(2) typed drift evidence emitters with run correlation; (3) attribution and threshold
policy; (4) explicit publisher/operator block creation only — automatic block creation
from live evidence activates only after S2f records resolved context on runs.

Not S2d: calling `match_release` at the three launch preparation seams is S2f (plan
Ownership row "Launch gating"; plan `### S2f` item 3). Verified: `match_release` has
zero production callers today — the only non-test reference is the
`harnesses/probes/targets.py` module docstring, which states "uncalled until S2f wires
launch". The compatibility fact artifact and versioned reader dispatch are S2e (plan
`### S2e`). S2d must introduce no launch-path call.

## Reuse Map

Existing owners S2d builds on (file + symbol):

- **Block model**: `harnesses/compatibility.py` `VersionBlock` — frozen pydantic model
  already validating scope keys per scope (`_validate_scope_keys`), supersession
  coherence (`_validate_supersession`: superseded ⇔ `superseded_by` set), and
  `evidence_digest` shape. Do not redeclare; the persisted row adds only `block_id`
  and `executor_id` (see Quality Map).
- **Pure matcher and outcome mapping**: `harnesses/compatibility.py` `match_release` +
  `CompatibilityMatch` — S2b already maps active blocks to
  `harness_version_blocked` / `connection_unavailable` / `target_unavailable` /
  `compatibility_release_unavailable`, filtering `status == "active"` and
  release attribution. The S2d "pure enforcement functions" gap is narrow: a pure
  merge of executor-origin blocks (Postgres) with publisher blocks
  (`CompatibilityChannelState.blocked_versions`) into one block set for matching, and
  the attribution policy. The matcher itself needs no change.
- **Table (DDL-only)**: `api/migrations/versions/0022_harness_executor_tables.py`
  `harness_executor_block` — `block_id` PK, `executor_id`, all `VersionBlock` fields;
  CHECKs mirror the model validators field for field
  (`harness_executor_block_scope_keys_ck`, `harness_executor_block_supersession_ck`);
  index `(executor_id, harness_id, status)`.
- **Recency/write-guard owners (REUSE, do not reinvent)**:
  `harnesses/connections_store.py` `ExecutorEvidenceStore` —
  - `_UPSERT_CONNECTION_SQL`: conditional upsert guarded by
    `revision <= EXCLUDED.revision` with rowcount-0 interpretation in
    `persist_connection` (immutable identity raises, stale revision no-ops);
  - `_UPSERT_OBSERVATION_SQL` / `_UPSERT_ACCESS_OBSERVATION_SQL` /
    `_UPSERT_TARGET_OBSERVATION_SQL`: `observed_at::timestamptz <= EXCLUDED` stale
    rejection;
  - `_ADVANCE_TARGET_SNAPSHOT_SQL`: strict `<` watermark for destructive application
    (the S2c tie fix, `24aec564` — equal-key destructive writes are not idempotent
    retries).
- **Store plumbing**: `session/pool.py` `connect` (sync writes) +
  `create_async_pool` (async reads), the exact store shape
  `ExecutorEvidenceStore` uses; `session/migrate.py` `sql_text_values` for CHECK
  vocabularies in any new migration.
- **Drift vocabulary**: HARNESS-COMPATIBILITY.md "Outcome codes" already defines the
  five drift codes (`launch_contract_drift`, `route_contract_drift`,
  `wire_contract_drift`, `transcript_contract_drift`, `session_contract_drift`) and
  "Runtime drift" defines attribution (version-specific defect → version block;
  provider/route/model behavior spanning versions → route or target block;
  unattributable or capture-unsafe → pause the release). `harnesses/connections.py`
  `ProbeFailureReason` shows the structural-redaction idiom (closed Literal
  vocabulary so raw output cannot ride into Postgres) — reuse for drift reason codes.
- **Drift emission seams (where evidence originates)**:
  wire parse → `adapters/base.py` `ProviderAdapter` implementations; transcript
  reader → `index/tailer.py` with `session/quarantine.py` `classify` already
  separating storage failures (poison/transient SQLSTATE classes) from record-shape
  problems — the exact "reader drift vs storage failure" boundary the plan demands;
  session bootstrap → `session/` run lifecycle contracts; actuation →
  `controlplane/prompt_delivery.py`.
- **Test infra**: `session/testing.py` `TestDb` fixture + the
  `test_connections_store.py` store-fixture pattern;
  `harnesses/connections_test_support.py` builders (`make_connection`, …) — add a
  `make_executor_block` beside them; `harnesses/compatibility_test_support.py` for
  release/channel fixtures;
  `session/test_harness_executor_tables_migration.py` round-trip to extend for block
  rows.
- **None found** (net-new, as planned): no `harnesses/blocks.py`, no block write path
  (`connections_store.py` docstring: "The executor block table has no write path
  here; VersionBlock persistence is S2d"), no drift evidence record type, no
  supersession write path, no executor/publisher block merge helper.

## Supersession contract (a)

Per HARNESS-COMPATIBILITY.md "Channel state": a block clears **only** by
supersession, recorded in `status` and `superseded_by`, through a later signed
channel update or a new release covering the change. Executor-origin blocks are
durable local records that survive restart and act before publication; publisher
blocks enter signed channel state. Blocks apply to new launches only and never
rewrite frozen run facts. A superseded block therefore: stays in the table (durable,
auditable — GC is an explicit open decision in the contract), is excluded from
matching (`match_release` filters `status == "active"`), and never returns to
active. `revision` is the block's monotonic record revision; `created_at` orders
lineage. Note `superseded_by` carries no FK — correct, because a publisher
supersession can reference a block id that lives in signed channel state, not in
this table.

## Write-path recency hazard (b)

The two failure modes to design out:

1. **Resurrection**: any upsert that writes `status` from the incoming payload lets a
   replayed stale `active` record overwrite a stored `superseded` row. Guard: the
   status transition is one-way (`active → superseded`) and must be its own
   conditional statement — supersede via
   `UPDATE … SET status='superseded', superseded_by=%s WHERE block_id=%s AND
   status='active'`, interpreting rowcount 0 as already-superseded (idempotent) —
   never a whole-row upsert keyed on `block_id`. This is the
   `persist_connection` rowcount-interpretation idiom, not a new mechanism.
2. **Stale supersession / duplicate active blocks**: creation should be
   `INSERT … ON CONFLICT (block_id) DO NOTHING` (a block is immutable once created;
   there is nothing newer to accept), with `revision`-guarded update only if the
   design allows block record revision at all. The recency key is `revision`
   (integer, `>= 1` CHECK) per block lineage, matching the connection pattern —
   `observed_at`-style timestamp recency is wrong here because blocks are events,
   not latest-state observations. No destructive retirement exists on this table, so
   the strict-`<` watermark owner is not needed; cite it only to show why ties
   matter when a write is destructive.

Data-integrity risk to surface explicitly: **0022 has no uniqueness on the natural
scope key** — two `active` blocks for the same
`(executor_id, harness_id, release_id, scope, normalized_version/route_id/model_id)`
can coexist. The contract does not forbid it (different `reason_code`s, and
`match_release` returns the first match), but if the build wants
one-active-block-per-scope-key it needs a partial unique index → a new migration.
Decision for the plan review, not silently either way.

## Drift emitters (c)

"Drift" (HARNESS-COMPATIBILITY.md "Runtime drift") = observed runtime behavior
leaving the certified contract while the binary stays installed and capture remains
safe; raw wire bytes and the owned transcript stay durable when normalization
degrades; degraded runs may continue but cannot count as conformance evidence. S2d
ships **typed evidence emitters, not automatic blocks**: wire parse drift separated
from generic parse failure (adapter seam), transcript reader drift separated from
storage failure (the `quarantine.classify` boundary), session bootstrap rejection,
actuation rejection — each with run correlation. Attribution policy (plan S2d item
3): evidence without resolved release, route, and model context **cannot create a
block**; unattributable or capture-unsafe evidence pauses the release instead.
Automatic creation activates only after S2f records resolved context; until then
blocks are created by explicit publisher or operator action against recorded
evidence. Open design point: 0022 has no drift-evidence table; blocks carry only
`evidence_digest`. Plan "Data placement" puts executor evidence in Postgres but
names only observations, connections, and executor blocks — the evidence record
itself likely lands in the control plane audit + run directory (raw), digest in the
block. If the build needs durable queryable pre-block evidence, that is a new table
and a conscious scope call.

## S2d/S2f boundary (d)

Confirmed clean: `match_release` uncalled in production; no launch preparation seam
touches compatibility today. S2d adds the pure merge + store + emitters; the first
production call of `match_release` (over merged publisher + executor blocks) is
S2f's application service. Any S2d change that imports launch/CLI modules is a leak.

## Migration need (e)

The 0022 DDL is **sufficient** for the core S2d write path: every `VersionBlock`
field plus `block_id`/`executor_id` is present, and both CHECK constraints already
enforce the model's scope-key and supersession invariants at the storage layer. A
new migration is needed only if (i) one-active-per-scope-key partial unique index is
adopted, or (ii) a durable drift-evidence table is scoped in. Default: no migration.

## Quality Map (scoped hygiene, assessment only)

Measurements: `compatibility.py` 550, `connections_store.py` 408,
`compatibility_store.py` 258, `connections.py` 242, tests 206–430, support 85/185,
migration 213. All under the 700 hard limit; no function near 150.

- **Headroom**: `compatibility.py` at 550 is the file to protect — S2d's pure
  additions (merge, attribution policy, evidence types) belong in the planned new
  `harnesses/blocks.py` (plan Ownership: "Version blocks and drift intake |
  harnesses/blocks.py plus Postgres tables"), keeping `compatibility.py` flat.
- **Store placement**: `connections_store.py` at 408 plus an estimated 150–200 lines
  of block SQL/store lands near 600 — legal but crowds the next slice. Recommend a
  sibling `blocks_store.py` mirroring the established pure-module/store split
  (`connections.py`/`connections_store.py`), same `connect` + pool shape.
- **Duplication watch**: the conditional-upsert guard idiom
  (`WHERE stored.<key> <= EXCLUDED.<key>`) already appears four times as SQL
  constants in `connections_store.py`. Block SQL should reuse the idiom verbatim in
  its store module; flag in review any hand-rolled alternative recency mechanism
  (SELECT-then-write, app-side clock comparison) as a REJECT-level deviation.
- **Model DRY hazard**: the persisted row is `VersionBlock` + `block_id` +
  `executor_id`. The build must compose (subclass `VersionBlock` adding two fields)
  — a 14-field redeclaration is the S2d duplication trap.
- **Boundaries**: pure-model/store split and the import DAG are clean and enforced
  (`test_private_import_boundary.py`); `blocks.py` must stay I/O-free per
  api/CLAUDE.md (sync pure computation, async I/O in the store).
- **Tests**: colocated pattern with shared builders is healthy; extend
  `connections_test_support.py` and the migration round-trip rather than forking
  new fixture files.

## Plan

1. `harnesses/blocks.py` (pure, new): `ExecutorVersionBlock` (composes
   `VersionBlock` + `block_id`, `executor_id`), pure merge of executor + publisher
   blocks for matching, attribution policy (evidence → version/route/target block or
   release pause), typed drift evidence records with closed reason-code vocabulary
   and run correlation fields.
2. `harnesses/blocks_store.py` (new): `create_block` (insert-immutable, ON CONFLICT
   DO NOTHING), `supersede_block` (conditional one-way UPDATE, rowcount
   interpretation), `active_blocks` / `list_blocks` reads; `TestDb` round-trip tests
   including restart survival and supersession across every scope (verification gate
   "Executor blocks survive restart and supersession is proven across every scope").
3. Emitters: typed evidence constructors at the four seams recording into the
   control plane audit with run correlation; explicit operator/publisher creation
   path only — no automatic block creation, no `match_release` call.
4. Fixtures: outcome-mapping matrix (drift fixtures land attributed blocks, preserve
   raw capture, surface contract outcome codes), stale/replayed-write and
   resurrection-attempt cases mirroring `test_connections_store.py`.
5. Gates: `just check` + `just test-affected` in the build loop; grok runs full
   `just check` + `just test` + `cd api && just migration-smoke` pre-merge.
6. Decisions to settle before build: partial unique index for one-active-per-scope-key
   (migration y/n); drift evidence persistence home (audit-only vs new table);
   confirm `superseded_by` stays FK-less.

Verdict: high reuse (model, matcher, recency idioms, store plumbing, and test infra
all exist); the supersession risk concentrates in two write statements — keep block
creation immutable and supersession a one-way conditional UPDATE, and the S2c
hazard class cannot recur; no migration needed unless the uniqueness decision says
otherwise.
