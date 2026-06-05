# Spec S2g backend: inventory, startup refresh, activation (advisory stays)

Mode 2 spec from the S2g scout
(`~/.mdx/projects/transport-matters-scout-s2g-inventory-enforcing.md`),
written read-only against main (1f9c1317). Plan sources:
RUNTIME-SURFACING-S2-PLAN.md (S2g section, invariants 6 and 7, verification
list), COMPATIBILITY-PUBLISHING.md (Certification), HARNESS-COMPATIBILITY.md.

## Locked decisions (Stuart approved; do not redesign)

- S2g = inventory + non-blocking startup refresh + activation. The build
  remains advisory: `COMPATIBILITY_ROLLOUT` in
  `harnesses/compatibility_service.py` is not touched. The enforcing flip is
  a distinct later release.
- Activation flips the claude/codex channel pointers paused to active, gated
  on that harness's conformance matrix passing.
- Grok stays excluded by construction (`launch=None`) until S2h.
- No new UI; the first-run screen is deferred.

## Reuse map (symbols the build binds to)

- Registry: `harnesses/__init__.py :: list_harness_descriptors`,
  `registered_harness_ids`, `_GROK_DESCRIPTOR` (launch=None).
- Installation: `capabilities.py :: detect_harnesses` (which-walk plus
  bounded 2s `--version` probe), `observe_resolved_binary`.
- Enablement: `harnesses/enablement_store.py :: HarnessEnablementStore
  .list_intents`; the write surface `api/v1/harness_enablement.py ::
  set_harness_enablement` is untouched.
- Channel and release: `channel.py :: resolve_channel_id` (default
  `stable`), `harnesses/compatibility_store.py :: embedded_channel_state`,
  `embedded_release_entry`.
- Blocks: `harnesses/blocks_store.py :: ExecutorBlockStore` (async reads for
  the API side; `active_blocks_sync` stays the launch-gate path),
  `harnesses/blocks.py :: merge_executor_blocks`.
- Evidence: `harnesses/connections_store.py :: ExecutorEvidenceStore`
  (`list_connections`, `latest_harness_observation`,
  `latest_access_observations`, `latest_target_observations`,
  `upsert_harness_observation`, `upsert_access_observation`).
- Judgment and enumeration: `harnesses/compatibility.py :: match_release`;
  `harnesses/resolver.py :: ResolverSnapshots`, `launch_options` (pure,
  already built, zero production callers; inventory is its snapshot
  gatherer per its own docstring).
- Probes: `harnesses/probes/runner.py` (connection scoped, redacting; its
  module docstring reserves the startup hook for S2g),
  `harnesses/probes/observation.py :: build_harness_observation`.
- Lifespan: `main.py :: lifespan` (single startup/shutdown owner; resource
  pattern `_start_session_backed_services` / `_close_lifespan_resource`).
- Certification: net-new `harnesses/certification.py` owns the immutable
  certification record models, canonical digest, and pure validation. Records
  reuse existing fixture files and Tier-1/session evidence. They do not create
  a second capture or test substrate.
- Manifest tooling: `api/scripts/reseal_compatibility_manifest.py`
  (release digests only; channel states are outside
  `release_digest_payload` coverage). Net-new
  `api/scripts/mint_harness_certification_record.py` gathers and validates the
  evidence bundle before writing a record. It delegates release digest
  calculation to the existing reseal tool when a replacement release is
  required.

## Deliverable 1: `harness_inventory()` + `/v1/harnesses` REST + MCP

New application service `harnesses/inventory.py :: harness_inventory()`,
async, executor scoped (`harnesses/executor_identity.py :: local_executor_id`).
Inventory performs no executable or authentication probes. The startup refresh
is the sole producer of local observation rows. The existing live launch gate
continues probing its exact resolved binary without feeding inventory. For
every registered descriptor, one stored snapshot drives every field:

- Read `latest_harness_observation` once. That one object supplies installation
  status, path, raw and normalized version, observation revision, and timestamp.
  It is also the `ResolverSnapshots.observation` and the observed version passed
  to `match_release`. A missing row is explicit `observed=false` with null
  installation facts. It never silently means a known absent executable.
- Read enablement through `HarnessEnablementStore.list_intents`. Absent intent
  means enabled, preserving the existing rule. `{configured, enabled,
  eligible}` is a projection of that intent plus the same stored installation
  observation.
- Read channel state and release through `resolve_channel_id`,
  `embedded_channel_state`, and `embedded_release_entry`; both are null when no
  pointer exists, including grok.
- Read active executor blocks through `ExecutorBlockStore.active_blocks`, merge
  them with `merge_executor_blocks`, and report the pure `match_release`
  outcome as advisory data.
- Read `list_connections`, `latest_access_observations`, and
  `latest_target_observations` together. Each connection response includes its
  latest authentication status, method, access status, probe revision,
  connection revision, observed time, and fixed reason. A connection with no
  access row reports null diagnostics. The inventory also projects target
  observation summaries so diagnostics remain readable independently of
  picker eligibility.
- Assemble one `ResolverSnapshots` from those same objects and call
  `resolver.launch_options`. No field is re-read or re-probed during assembly.
  This is the resolver's first production caller.

The per-harness response has six explicit groups: descriptor, installation
observation, enablement, channel and compatibility, connection and target
diagnostics, and launch options. Every group carries its source revision or
observation time where one exists. A refresh racing an inventory request may
become visible on the next request, while a single response never mixes live
detection with older stored installation evidence.

Surface decision (per scout findings): `/v1/harnesses` is a new read surface
owned by `api/v1/harnesses.py`. `main.py :: create_app` registers that router
directly with `prefix="/v1"`, matching the other public `/v1` surfaces. It is
deliberately absent from `api/v1/router.py`, because `main.py` mounts that
aggregate at `/api` and would otherwise expose `/api/harnesses`. The new
surface does not extend `GET /api/harnesses/enablement`. The two existing GET
reads are strict subsets and become thin projections delegating to
`harness_inventory()` in this slice, so exactly one join implementation
exists: `api/v1/capabilities.py :: get_capabilities` (the UI consumes it
firsthand: `www/packages/core/src/transport.ts :: fetchCapabilities`, so it
cannot be retired without UI change, which is out of scope) and
`api/v1/harness_enablement.py :: get_harness_enablement`. Endpoint
retirement lands with the control-plane UI redesign, not here.

MCP projection: one read tool in `api/v1/controlplane_mcp.py` (478 lines,
fits under the 700 threshold) delegating to the same service and projecting
the same response model.

Route and coherence tests pin all three boundaries: `/v1/harnesses` resolves,
`/api/harnesses` does not, and both legacy `/api` GET reads are projections of
the service. An inventory test seeds a stored observation that contradicts an
injected live detector, asserts the detector is never called, and proves the
same stored revision drives installation, compatibility, and launch options.
Another test persists access rows for two connections and proves REST and MCP
surface the corresponding authentication and access diagnostics.

Store-down posture: identical to `get_harness_enablement`, one 503 with a
stable error code when the session pool is absent or store reads fail
(`optional_session_pool`). No partial-degrade machinery in this slice.

## Deliverable 2: non-blocking startup refresh

Hook point: `main.py :: lifespan`, after services construction, one
`asyncio.create_task` held on `app.state` and cancelled in the existing
`finally` chain. A small async close wrapper cancels the task, awaits it while
suppressing `asyncio.CancelledError`, and is itself passed to
`_close_lifespan_resource`. The task is created only when the session pool is
available. It processes each harness and connection independently, so one
failed probe or write cannot prevent later observations from refreshing.

The task:

1. Runs `detect_harnesses` off-loop and upserts fresh installation evidence
   through `build_harness_observation` +
   `ExecutorEvidenceStore.upsert_harness_observation`. Both the detector and
   every synchronous Postgres upsert run through `asyncio.to_thread`; no sync
   store call executes on the event loop. Inventory then serves last-known
   observations without probing per request.
2. Runs the authentication/access probes through
   `harnesses/probes/runner.py` for each registered connection, recording
   results with `build_access_observation` and
   `ExecutorEvidenceStore.upsert_access_observation`. The runner already moves
   its subprocess off-loop; the synchronous upsert also runs through
   `asyncio.to_thread`. Probes run only when the observation has an installed,
   normalized version and an embedded release exists to attribute the access
   row. Grok has no release in S2g, so it receives installation evidence only.
   Probe outcomes remain diagnostics and never authorize or block launch.
3. Logs and swallows every failure; a failed refresh leaves last-known
   evidence in place. Failure isolation is per harness or connection, followed
   by one outer guard for unexpected task failures.

Non-blocking guarantee: startup never awaits the task; launch paths are
untouched (they keep probing live at `cli/launch_runtime.py ::
prepare_launch`). Tests colocated in `test_main.py` prove the real boundary:

1. Inject a refresh callable that never resolves and assert the lifespan enters
   and the health route serves without waiting.
2. Use the real test Postgres and real `ExecutorEvidenceStore` persistence.
   Wrap each synchronous upsert with a worker-thread barrier that waits before
   delegating to the real method. While the worker is held, assert the lifespan
   has entered, a health request completes, and `/v1/prepare` completes through
   the existing injected `CaptureLeaseRegistry.prepare_run` seam within short
   deadlines. Release the barrier, await refresh, then read Postgres and assert
   both harness and access observations landed. This test fails if either
   upsert runs on the event loop and proves actual persistence rather than an
   injected no-op.
3. Assert one connection write failure is logged while a later connection is
   still persisted.
4. Assert an unexpected raising refresh is logged and startup remains live.
5. Assert shutdown cancels and awaits the task without leaking
   `CancelledError`.

## Deliverable 3: activation (paused to active), still advisory

Data change in `harnesses/compatibility_releases_v1.json`: the four channel
states (stable/preview x claude/codex) flip from `paused` to `active` only
after the certification record gate below passes. Each state bumps `sequence`
to 2, refreshes `activated_at`, and keeps its stub signature. Embedded data
remains trusted through package integrity, while `RejectAllSignatureVerifier`
continues rejecting every mutable update. `COMPATIBILITY_ROLLOUT` remains
`advisory`.

Activation points at the immutable release whose certification record passed.
The existing `r1` release may be used only when the newly minted record and
fixture bundle reproduce its existing `evidence_digest` and
`fixture_set_digest`. A mismatch never rewrites `r1`. It leaves `r1`
unactivated, then mints `r2` with the same certified baseline and
adapter/catalog payload,
the actual certification and fixture digests, updated target
`compatibility_release_id` values, and a release digest recomputed through
`api/scripts/reseal_compatibility_manifest.py`. The sequence-2 pointers then
reference `r2`. This preserves release immutability while making evidence
provenance enforceable.

### Immutable certification record gate

`harness_compatibility_gate outcome=compatible` and the run-dir compatibility
facts remain useful launch telemetry. They are written during
`prepare_launch`, before the harness starts, and therefore cannot certify
startup, turns, parsing, transcripts, resume/fork, or shutdown. Pointer
activation uses the certification record below instead.

#### Owner, storage, and immutability

`harnesses/certification.py` owns `CertificationRecordV1`, the 13 closed facet
identifiers, canonical digest calculation, and pure validation against one
`CompatibilityReleaseEntry`. Package-embedded records live at
`api/src/transport_matters/harnesses/certification_records_v1/<release_id>.json`.
There is exactly one record per release id and exactly one entry for each of
the 13 facets. The mint command refuses to overwrite a record; changed
evidence requires a new release id.

Raw wire bytes, owned transcripts, and session rows remain in their existing
Tier-1 and Postgres owners. The record stores stable run/session identities,
artifact digests, normalized assertions, and repo-relative fixture hashes. It
contains no raw provider payload, transcript text, terminal output, credential,
or absolute home path.

#### Record schema

```text
CertificationRecordV1 {
  schema_version: 1
  release_id: str
  harness_id: HarnessId
  baseline_version: str
  transport_matters_revision: full git SHA
  certified_at: RFC3339 UTC

  fixture_set_digest: sha256
  fixture_files: [{path: repo-relative path, sha256: sha256}]
  suite_results: [{suite_id: str, selectors: [pytest/vitest selectors],
                   outcome: "passed"}]

  runtime_runs: [{
    scenario_id: str
    run_id: str
    session_ids: [str]
    observed_harness_version: str
    compatibility_facts_digest: sha256
    launch_facts_digest: sha256
    wire_evidence_digest: sha256 | null
    transcript_evidence_digest: sha256 | null
    lifecycle_evidence_digest: sha256
    predicate_results: [{predicate_id: CertificationPredicateId,
                         outcome: "passed", evidence_digest: sha256}]
  }]

  facets: [{
    facet_id: CertificationFacetId
    outcome: "passed"
    applicability: "required" | "declared_unsupported"
    fixture_refs: [{suite_id: str, fixture_paths: [repo-relative path]}]
    runtime_refs: [{scenario_id: str,
                    predicate_id: CertificationPredicateId}]
    edge_refs: [{route_id: str, model_id: str, effort: str | null}]
  }]
}
```

The record carries no self-declared digest. Its certification digest is
`canonical_digest(record.model_dump(mode="json"))`. Fixture set digest is the
canonical digest of the sorted `{path, sha256}` pairs in `fixture_files`.
Normalized suite results exclude time, duration, host paths, and log text so
the same passing evidence has a stable digest.

#### Evidence gathering for all 13 facets

`api/scripts/mint_harness_certification_record.py` runs the pinned selectors,
hashes the cited fixture files, and inspects the supplied run ids through the
existing Tier-1 and session read boundaries. It derives pass status from those
results and predicates. It accepts no `--passed` flag and no free-form facet
status. `CertificationPredicateId` is also closed, and the validator owns the
allowed predicate set for each facet. Every tested route, model, and accepted
effort in the release must appear in `edge_refs`; fixture evidence may cover
equivalent effort shapes, while each harness still needs the bounded runtime
scenario set.

| Facet id | Required fixture suites and digests | Required durable runtime evidence |
|---|---|---|
| `exact_harness_version` | `test_capabilities.py`, `harnesses/probes/test_observation.py`, `harnesses/test_compatibility.py` | Compatibility facts and launch facts agree on executable path, exact normalized version, release id, and adapter revisions. |
| `prompt_free_interactive_startup` | `cli/test_captured_run.py`, `cli/test_start_acceptance.py`, `test_supervisor.py`, `test_supervisor_spawn.py` | A prompt-free run reaches ready, creates no submitted turn, and exits cleanly. |
| `startup_prompt_first_turn` | `cli/test_prompt.py`, `api/v1/test_capture_rpc_routes.py`, `packages/runtime/src/service/RunManagerInitialPrompt.test.ts` | A native startup-prompt run has one correlated user turn, wire request, response, and transcript record. |
| `model_effort_actuation` | `cli/test_launch_profile.py`, `test_request_pipeline.py`, Codex request parser/serializer tests | Recorded wire provider/model and launch facts equal requested model/effort; fixture edges cover every accepted effort. |
| `provider_request_parsing` | `adapters/test_anthropic.py`, `adapters/test_codex.py`, `codex/test_request_parser_metadata.py`; hashes under `api/tests/fixtures/claude_messages/**`, `codex_response_*.json`, and `codex_http_fallback/**` | First and later-turn wire requests parse, retain raw evidence digests, and correlate to the expected run/session. |
| `streaming_response_terminal` | `test_response_stream.py`, `test_response_stream_capture.py`, `codex/test_response_parser_content.py`, `packages/common/src/terminalContract.test.ts`, `packages/runtime/src/service/TerminalEmulator.test.ts` | Each prompted scenario reaches a completed response and terminal state with durable response evidence. |
| `tool_usage_provider_errors` | `adapters/test_anthropic.py`, `adapters/test_codex.py`, `test_exchange_stats.py`, `test_provider_conditions.py`, `packages/activity/src/adapters/transcriptRecords.test.ts`; hashes of tool, usage, and provider-error fixtures | A bounded tool-using scenario proves correlated tool/result and usage records; deterministic fixtures cover provider-error branches. |
| `approval_structured_input` | `test_live_status*.py`, `test_breakpoint.py`, `controlplane/test_prompt.py`, `controlplane/test_prompt_delivery.py` | A bounded approval or structured-question scenario is correlated where the harness supports it. A declared unsupported result needs a fixture proving the capability declaration. |
| `second_turn_correlation` | Claude multi-turn message fixtures and Codex continuity/derivation suites | The prompted scenario submits a second turn and links both wire exchanges and transcript records to one session in order. |
| `transcript_wire_correlation` | `index/adapters/test_claude.py`, `index/adapters/test_codex.py`, `session/test_wire_normalization.py`, `session/test_conversation_parity.py`, `storage/test_transcript_snapshot.py` | Owned transcript digest, normalized session rows, and wire rows agree for both turns. |
| `session_bootstrap_resume_fork` | `cli/test_codex_session.py`, `storage/test_session_facts.py`, index adapter, and captured-run suites | The bounded scenario bundle proves bootstrap plus resume and fork where supported, with parent/session identities and continued correlation. |
| `project_layout_runtime_home` | `cli/test_runtime_home*.py`, `cli/test_home_seed*.py`, `cli/test_secure_captured_workdir.py` | Launch facts and Tier-1 facts prove canonical project identity, managed home materialization, and the selected connection context. |
| `clean_shutdown_durable_capture` | `test_supervisor_terminate.py`, `test_run_lifecycle_emission.py`, `storage/test_disk_persist.py`, `storage/test_transcript_snapshot.py` | Every scenario reaches an ended lifecycle state; final wire, transcript, session, and facts digests remain readable after process exit. |

Globs in this table are authoring shorthand. The minted record expands them to
sorted exact paths and stores one SHA-256 per file. The fixture bundle includes
the applicable files under `api/tests/fixtures/claude_messages/**`,
`api/tests/fixtures/claude_transcript.jsonl`,
`api/tests/fixtures/codex_40_live_turn.jsonl`,
`api/tests/fixtures/codex_response_*.json`,
`api/tests/fixtures/codex_rollout*.jsonl`,
`api/tests/fixtures/codex_http_fallback/**`, and
`packages/activity/fixtures/{claude,codex}/**`. The mint command fails when a
selector has no matching fixture or when a file changes after its suite ran.

The runtime bundle therefore contains more than a single launch when the
contract requires it: one prompt-free run, one prompted two-turn run, and the
resume/fork plus approval or structured-input scenarios supported by that
harness. All runs are bounded and execute while rollout is advisory, so a
paused pointer cannot block certification traffic.

#### Exact activation check

The mint command validates the record, writes it once, and prints its canonical
digest. Before a channel state can become active,
`compatibility_store` applies the same pure validation for the pointed release:

1. A package-embedded record exists for `active_release_id` and its release,
   harness id, baseline version, and full facet set match.
2. The facet ids equal the closed 13-value set exactly, every outcome is
   `passed`, every evidence reference resolves inside the record, and route,
   model, and effort coverage equals the release catalog. Every runtime
   predicate is permitted for its facet and has a passing result in the
   referenced scenario.
3. During minting, hashes of the repo files match every `fixture_files` entry.
   At package load, the canonical digest of those sorted entries produces
   `record.fixture_set_digest`; it equals `release.fixture_set_digest`.
4. `canonical_digest(record)` equals `release.evidence_digest`.

Missing records, incomplete facets, non-passing outcomes, unresolved evidence,
catalog coverage gaps, or either digest mismatch raise
`CompatibilityDataError` while loading embedded data. The mint tool exposes a
`--verify-activation <release_id>` mode that runs the same validator and must
succeed immediately before the pointer edit. This makes the record a build and
runtime data-integrity gate. A passing prepare-launch audit cannot satisfy or
bypass it.

### Activation tests

New `harnesses/test_certification.py` covers the record boundary:

- exact 13-facet completeness, unique facet ids, `passed` outcomes, resolved
  fixture/runtime references, and complete route/model/effort coverage;
- canonical fixture and certification digest stability;
- rejection of missing, duplicate, unsupported, or free-form facets, missing
  evidence, a failed suite, and a catalog edge without evidence;
- minting refuses to overwrite an existing release record; changed evidence
  requires a new release id.

In `harnesses/test_compatibility_store.py`:

- `test_every_embedded_pointer_starts_paused` is superseded by a test
  asserting the claude and codex pointers are `active` on both channels
  (and only those four states exist).
- `test_embedded_paused_pointer_fails_closed_until_activation` is
  superseded by its mirror: every active pointer has a complete matching
  certification record, and the stable/claude pointer at baseline version
  matches `compatible`.
- Active pointers with a missing record, missing facet, non-passing outcome,
  unresolved evidence reference, incomplete edge coverage, fixture digest
  mismatch, or certification digest mismatch each raise
  `CompatibilityDataError`.
- A paused pointer may carry no certification record. It still matches
  `compatibility_release_unavailable`, preserving the pre-activation state.
- `test_no_grok_release_ships_before_its_conformance_matrix` stays
  unchanged (grok exclusion pin).

New advisory-not-blocking proofs:

- A rollout pin test asserting
  `compatibility_service.COMPATIBILITY_ROLLOUT == "advisory"`, so the
  enforcing flip cannot ride into this slice unnoticed; the later flip
  release deletes this pin deliberately.
- A gate-level test in `harnesses/test_compatibility_service.py`: active
  pointer, baseline-or-newer observed version, decision records
  `outcome="compatible"` and nothing raises; and the existing
  non-compatible advisory cases still record without raising.
- A certification test proves that this compatible gate action and its
  compatibility facts cannot substitute for any missing certification facet.
- The S2f per-seam acceptance tests
  (`cli/test_launch_compatibility_gate.py`) stay green unmodified; they run
  under the advisory constant.

## Deliverable 4: grok (no work, two confirmations)

Excluded by construction: `_GROK_DESCRIPTOR` has `launch=None`, so no
launch path reaches either gate, and the manifest contains no grok release
or pointer (pinned by `test_no_grok_release_ships_before_its_conformance_matrix`).
Inventory lists grok as installation/enablement only with null channel
state and no launch options (matches plan S2a: "grok appears as installed,
path, and version only"). One inventory test asserts that shape.

## Tests and gates

- Inventory: colocated `harnesses/test_inventory.py` covering zero, one,
  and several ready harnesses and every failed check without cross-harness
  blocking (plan verification line); REST tests beside
  `api/v1/test_harness_enablement.py`; MCP projection test beside the
  existing controlplane MCP tests; an explicit `/v1` mount test; stored
  observation coherence and access-diagnostic tests; delegation tests proving
  the two legacy GET reads serve the same data as the service.
- Startup refresh: the five `test_main.py` cases above, including real
  Postgres persistence held behind a worker-thread barrier.
- Activation: certification model, minting, immutable record, digest gate,
  manifest, rollout pin, and advisory launch tests above.
- Gate for the build: `just check` + `just test-affected`. No migration is
  expected (inventory reads existing tables only); if one appears,
  `cd api && just migration-smoke` joins the gate.
- Release gate for the activation PR: run the pinned fixture suites and the
  bounded runtime scenario bundle on Stuart's machine, mint one immutable
  record for each activated release, and run the exact record/release digest
  validator before editing channel state. The PR records the certification
  record paths and runtime run ids.

## Completion line

S2g backend is complete when `GET /v1/harnesses` and the MCP tool serve the
joined per-harness state from the one `harness_inventory()` service (legacy
GET reads delegating, PUT untouched), each response uses one stored
installation observation and includes connection-scoped authentication/access
diagnostics, the startup refresh keeps all synchronous detection and
persistence off the event loop with the real-persistence test proving it, and
each activated claude/codex release has an immutable complete 13-facet record
whose fixture and certification digests match the release. All four pointers
are active while `COMPATIBILITY_ROLLOUT` stays advisory with the pin test
proving it, grok remains pointer-less and unlaunchable, and `just check` plus
`just test-affected` pass on the final tree.
