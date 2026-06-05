# PR #307 adversarial review

Verdict: changes requested. The exact range reviewed was `main..171801b9e0a898552d4b69b62631a7a931710614`, with base `e2f2137d70dd14bec02deac70c173e5bdf527cce`.

## Findings

### 1. P1: Launch actuation accepts captures from models outside the target release

Location: [`certification_evidence.py:403`](https://github.com/littleorgans/transport-matters/blob/171801b9e0a898552d4b69b62631a7a931710614/api/src/transport_matters/harnesses/certification_evidence.py#L403-L430)

The resolver check rejects only `release_edge_set(entry) - resolved`. Extra resolver edges pass. The capture check then requires only the expected provider and any nonempty model. It never correlates a captured model, route, or effort with a target release edge.

This is observable in the named real captures. The Claude target is `claude-opus-4-8`, while the Claude capture used `anthropic/claude-fable-5`. The Codex target is `gpt-5-codex`, while the Codex captures used `codex/gpt-5.4-mini` and `codex/gpt-5.6-sol`. All can satisfy the current actuation loop. The emitted digest records the expected release edges beside unrelated `actuated_models`, so facet 3 can certify a target launch that did not occur.

Require exact resolver set equality and bind every captured exchange to an allowed route, model, and effort edge.

### 2. P1: Facet 7 accepts foreign session and transcript evidence

Locations: [`certification_evidence.py:228`](https://github.com/littleorgans/transport-matters/blob/171801b9e0a898552d4b69b62631a7a931710614/api/src/transport_matters/harnesses/certification_evidence.py#L228-L249), [`certification_evidence.py:505`](https://github.com/littleorgans/transport-matters/blob/171801b9e0a898552d4b69b62631a7a931710614/api/src/transport_matters/harnesses/certification_evidence.py#L505-L555)

`_read_session_facts()` checks only that `native_session_id` and `source_descriptor` are nonempty. It does not require `session.run_id == compatibility_facts.run_id`, `session.harness == compatibility_facts.harness_id`, or a descriptor that belongs to that native session. Transcript evaluation then takes the first descriptor's format and scans every `transcripts/*.jsonl` file without correlating snapshots to declared sessions.

Focused probes accepted mismatched run and harness values. A Codex snapshot with a foreign filename and foreign `session_meta.payload.id` also returned a passing transcript digest instead of matching the expected synthesized session ID. A clean snapshot from another session can therefore prove launch ownership for the cited run.

Validate the run and harness fields, decode and validate every descriptor, derive the provider specific snapshot identity, and require a one to one session to snapshot relation.

### 3. P1: The certification validator does not enforce the claimed per facet owner bindings

Locations: [`certification.py:116`](https://github.com/littleorgans/transport-matters/blob/171801b9e0a898552d4b69b62631a7a931710614/api/src/transport_matters/harnesses/certification.py#L116-L126), [`certification.py:430`](https://github.com/littleorgans/transport-matters/blob/171801b9e0a898552d4b69b62631a7a931710614/api/src/transport_matters/harnesses/certification.py#L430-L454), [`certification_evidence.py:181`](https://github.com/littleorgans/transport-matters/blob/171801b9e0a898552d4b69b62631a7a931710614/api/src/transport_matters/harnesses/certification_evidence.py#L181-L204)

`RUN_BOUND_PREDICATE_DIGESTS` binds only three of seven predicates. Installation, version, launch profile, and authentication predicate digests can be replaced in a resealed record and still validate. Facet 7 is also bound to `compatibility_facts_digest`, although its owner artifact is sealed separately as `launch_facts_digest`.

One focused activation probe changed each predicate digest and resealed the record. The four unlisted predicates still validated. A second probe changed `session_ids` and `launch_facts_digest`; facet 7 still validated against the unchanged compatibility digest.

Define and validate the owner digest relationship for all seven facets. Bind `launch_captured_owned_session` to the launch facts that contain the owned session evidence.

### 4. P1: Authentication accepts an unrelated access observation

Location: [`certification_evidence.py:434`](https://github.com/littleorgans/transport-matters/blob/171801b9e0a898552d4b69b62631a7a931710614/api/src/transport_matters/harnesses/certification_evidence.py#L434-L463)

The selection checks only release ID, authenticated status, and age after the store query scopes executor and harness. It does not bind the row's harness version, connection ID and revision, route ID, or probe revision to the observed run, target release route, and captured resolver state.

Focused probes passed rows with `harness_version="0.0.1"`, an unrelated probe revision, a different connection, and an unrelated route. Facet 4 can therefore certify authentication using a fresh row that did not observe the launch path under certification.

Resolve the applicable route and connection from the same stored snapshot, then require the release's authentication probe revision and the run's observed harness version.

### 5. P1: The wire digest omits a detector input

Locations: [`drift_capture.py:80`](https://github.com/littleorgans/transport-matters/blob/171801b9e0a898552d4b69b62631a7a931710614/api/src/transport_matters/drift_capture.py#L80-L130), [`certification_evidence.py:465`](https://github.com/littleorgans/transport-matters/blob/171801b9e0a898552d4b69b62631a7a931710614/api/src/transport_matters/harnesses/certification_evidence.py#L465-L503)

`detect_unknown_shapes()` reads `artifacts.request_ir`, but the wire manifest seals request bytes, response bytes, and the normalized transport model. It omits `request.ir.json`.

A focused probe held the manifest inputs constant and changed only the request IR. One IR was clean and one reported an unknown provider field; both produced the same manifest digest. A substituted or stale IR can change the facet 5 result without changing `wire_evidence_digest`.

Seal every detector input, or derive the IR again from sealed raw bytes inside the evaluator and reject disagreement with persisted IR.

### 6. P1: Two additions violate the hard file size rule

Locations: [`index/tailer.py:227`](https://github.com/littleorgans/transport-matters/blob/171801b9e0a898552d4b69b62631a7a931710614/api/src/transport_matters/index/tailer.py#L227-L251), [`test_drift_capture.py:219`](https://github.com/littleorgans/transport-matters/blob/171801b9e0a898552d4b69b62631a7a931710614/api/src/transport_matters/test_drift_capture.py#L219-L237)

The repository requires refactoring before adding code to any file already over 700 lines. `tailer.py` grew from 748 to 775 lines. `test_drift_capture.py` grew from 702 to 723 lines. Both additions violate an explicit rule with no exception.

The new `certification_evidence.py` is compliant at 658 lines, and no changed function exceeds 150 lines.

### 7. P2: Evidence collection can rewrite or delete evidence before sealing it

Locations: [`certification_evidence.py:153`](https://github.com/littleorgans/transport-matters/blob/171801b9e0a898552d4b69b62631a7a931710614/api/src/transport_matters/harnesses/certification_evidence.py#L153-L175), [`storage/disk.py:41`](https://github.com/littleorgans/transport-matters/blob/171801b9e0a898552d4b69b62631a7a931710614/api/src/transport_matters/storage/disk.py#L41-L53), [`storage/disk.py:99`](https://github.com/littleorgans/transport-matters/blob/171801b9e0a898552d4b69b62631a7a931710614/api/src/transport_matters/storage/disk.py#L99-L150), [`storage/disk.py:406`](https://github.com/littleorgans/transport-matters/blob/171801b9e0a898552d4b69b62631a7a931710614/api/src/transport_matters/storage/disk.py#L406-L412)

The collector uses the active `DiskStorageBackend` as a reader. Construction can remove a legacy root and clean partial writes. `read_index()` can reconcile deletes, recover missing rows, backfill fields, and rewrite `index.jsonl`. `read_exchange()` can redact and rewrite `transport.json`.

Certification can therefore mutate historical evidence before computing its digests. The first and second derivations can differ for the same input directory, and legacy evidence can be removed during evaluation.

Use a dedicated immutable evidence reader. Refuse repairable or legacy state and require repair to happen as a separate, explicit operation before certification.

### 8. P2: Launch facts digest is unstable under an idempotent multi session upsert

Locations: [`certification_evidence.py:181`](https://github.com/littleorgans/transport-matters/blob/171801b9e0a898552d4b69b62631a7a931710614/api/src/transport_matters/harnesses/certification_evidence.py#L181-L190), [`storage/session_facts.py:73`](https://github.com/littleorgans/transport-matters/blob/171801b9e0a898552d4b69b62631a7a931710614/api/src/transport_matters/storage/session_facts.py#L73-L90)

The digest preserves session list order. The existing upsert removes the matching entry and appends it, so rewriting unchanged session `a` changes `[a, b]` to `[b, a]`. A focused probe produced different digests for the same two session facts in opposite orders.

Canonicalize the session set by a stable identity before hashing, or make the durable upsert preserve stable ordering.

### 9. P2: Parsed model digests allow distinct artifact bytes to share one digest

Locations: [`certification_evidence.py:181`](https://github.com/littleorgans/transport-matters/blob/171801b9e0a898552d4b69b62631a7a931710614/api/src/transport_matters/harnesses/certification_evidence.py#L181-L190), [`certification_evidence.py:486`](https://github.com/littleorgans/transport-matters/blob/171801b9e0a898552d4b69b62631a7a931710614/api/src/transport_matters/harnesses/certification_evidence.py#L486-L503), [`storage/session_facts.py:38`](https://github.com/littleorgans/transport-matters/blob/171801b9e0a898552d4b69b62631a7a931710614/api/src/transport_matters/storage/session_facts.py#L38-L59), [`storage/base.py:249`](https://github.com/littleorgans/transport-matters/blob/171801b9e0a898552d4b69b62631a7a931710614/api/src/transport_matters/storage/base.py#L249-L267)

Launch and transport digests hash `model_dump()` output after Pydantic parsing. Both models use the default behavior that ignores unknown fields. Direct probes added well formed extra ownership and transport fields; parsed models and digests remained identical.

This is a semantic collision against the PR's claim to seal exact Tier 1 content. Configure evidence models to forbid extras and fail closed, or hash the exact canonical JSON artifact after validating it.

### 10. P2: Codex meta event admission is global rather than release scoped

Location: [`codex/protocol.py:30`](https://github.com/littleorgans/transport-matters/blob/171801b9e0a898552d4b69b62631a7a931710614/api/src/transport_matters/codex/protocol.py#L30-L71)

The PR admits `codex.rate_limits` and `codex.response.metadata` into one global event type set based on the 0.144.x captures. `unknown_server_event_types()` receives no release or recorded wire revision, and it checks only the type string. Older or later Codex captures now accept these types even if their payload contract differs from the evidence used to certify them.

Scope the wire vocabulary to the recorded wire revision, as transcript adapters already do, or document and prove that these event types are a provider wide invariant. The new fixture legitimately matches captured frames for the selected evidence.

## Real capture verification

The three intended preview captures are legitimate Tier 1 runs:

* `9ac94cde...`: Claude 2.1.214, 5 exchanges, 44 complete transcript records.
* `959a335b...`: Codex 0.144.4, 7 exchanges, 47 complete transcript records.
* `8ffaeec2...`: Codex 0.144.4, 1 exchange, 1 complete transcript record.

Current head's shared `detect_unknown_shapes()` produced no findings for their exchanges. Shared `transcript_drift_spans()` produced no spans for their transcript snapshots. This proves the Tier 1 byte scanners over those captures.

It does not currently prove an end to end seven facet collection. The preview Postgres store has no matching harness observation for the preview executor, so `CapturedRunEvidenceSource.collect()` refuses all three at facet 1. The store may have been reset after capture. The committed happy path test uses synthetic run artifacts and synthetic stored rows.

## Positive checks

* The three shared owner helpers are reused: `detect_unknown_shapes`, `transcript_drift_spans`, and `release_edge_set` each have one production definition.
* Missing bindings, missing run artifacts, no exchanges, missing stored rows, version mismatch, stale authentication, offline drift, and stored drift all refuse rather than skip.
* The Codex `minted:false` deviation is legitimate. Facet 7 must prove synthesized ownership instead of requiring `minted:true`; finding 2 identifies the missing proof.
* All embedded Claude and Codex pointers remain `paused`.
* `COMPATIBILITY_ROLLOUT` remains `advisory`.
* No manifest, certification record, activation file, or mint plan was added.
* `git diff --check main..171801b9` passed.

## Test evidence

The user reported `just check && just test-affected` green and directed the review away from GitHub Actions. A focused local selection of certification tests produced 63 passes and 19 setup errors because the isolated pytest home had no explicit test database URL. The setup errors do not establish a code regression, and the selection is not reported as green.

The repository tree was pristine before review. No repository files were written during review. Final head and tree verification follows the artifact write.
