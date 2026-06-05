# Scout: the real-evaluator slice (replace RealRuntimeEvidencePending)

Scouted 2026-07-18 on main f9f61bc3, read-only. Captures inspected firsthand under
`~/.transport-matters-preview/workspaces/dev-helioy-transport-matters/ecd9b0df/`.

## The central question, answered

**Yes, the evaluators are largely READ + RE-DERIVE + SEAL, not new detection.**
`compatibility.json` is written at capture time by the S2f gate
(`compatibility_service._record` → `compatibility_facts.compatibility_fact_artifact` →
`write_compatibility_facts`), frozen-once, and already seals: release binding
(release_id + release_digest), exact `observed_version`, `executable_path`, all 14
recorded revisions, and the release's schema/fixture/evidence digests. Its digest
function **already exists**: `compatibility_facts.compatibility_fact_digest`.

Caveat that sizes the slice honestly: the digests inside compatibility.json come from
the **release manifest**, not from the captured bytes. So compatibility.json alone
certifies facets 1/2/7's facts; facets 5/6 need re-derivation over the run's tier-1
bytes and transcripts (the artifacts exist; the scan code exists and is pure), and
facets 3/4 read stored Postgres snapshots (state_refresh is the sole producer;
inventory.py is the existing single-join read model).

**The only genuinely NEW detection code is the two bucket-B gap closures** (codex
per-item wire vocabulary, transcript meta allowlist). Everything else is composing
existing pure functions plus defining digest semantics PR1 left open.

What exists vs missing, exactly:

| Evidence | Exists at capture time | Missing |
|---|---|---|
| Release binding, observed version, exec path | compatibility.json (frozen, digest fn exists) | nothing |
| Owned-session binding | sessions.json `minted: true` + native_session_id | nothing |
| Tier-1 wire bytes | `<run>/<ts>-<id>/request.raw`, response bytes, transport.json, request.ir.json, index.jsonl | per-item codex vocab scan (C2) |
| Transcripts | `<run>/transcripts/<native-session>.jsonl` owned copy | meta allowlist (C3) |
| Installed/auth/target snapshots | Postgres rows via state_refresh (auth probe IS wired as default) | nothing |
| Launch profile | resolver.launch_options pure over ResolverSnapshots | evaluator composition only |
| launch_facts / lifecycle digest semantics | — | undefined by PR1; must be defined this slice |

## Reuse map: the 7 facets

Format: facet → owner → deterministic derivation from the captured bundle → status.

1. **harness_installed** → `capabilities.detect_harnesses` (line 173) via
   `state_refresh.refresh_harness_state` writing `LocalHarnessObservation` rows
   (`connections_store.ExecutorEvidenceStore`, table `harness_observation`).
   Evaluator: read the stored row for (executor, harness); require
   `observed, installed, status=="ok"`; cross-check `executable_path` and
   `normalized_version` equal the run's compatibility.json (capture-time truth
   anchors the stored row). Predicate digest = canonical digest of the row.
   **Pure read + cross-check; zero new detection.**

2. **version_in_range** → `compatibility.match_release` (compatibility.py:480), pure.
   Evaluator: re-run match_release over compatibility.json's `observed_version`
   against the embedded release entry. Digest = canonical digest of the match
   outcome + inputs. **Pure recheck.**

3. **launch_profile_resolved** → `resolver.launch_options` (resolver.py:623) over
   `ResolverSnapshots` (explicit pinned inputs, never live) assembled exactly as
   `inventory.harness_inventory` already does from stored snapshots. Evaluator:
   build snapshots → enumerate `LaunchOption`s → derive the facet's
   `CertificationEdgeRef`s; the PR #305 validator already requires this facet to
   own the release edge set exactly. Actuation half of the predicate name
   (`launch_profile_actuated`): corroborate against the capture — index.jsonl
   entries carry the model per exchange (e.g. `anthropic/claude-fable-5` in run
   9ac94cde), proving the resolved profile actually hit the wire. **Pure
   composition; the actuated-edge corroboration is a small new pure check.**

4. **authentication_checkable** → `probes.runner.run_authentication_probe`
   (runner.py:87), wired since PR2 as the default probe of
   `state_refresh.refresh_harness_state` (state_refresh.py:184), writing
   `LocalHarnessAccessObservation` rows (table `harness_access_observation`).
   Evaluator: read the stored access row for the run's connection + release;
   require a typed `authentication_status` recorded by the probe revision. No
   live auth at mint. Predicate is `authentication_evidence_current` — a
   freshness window against `observed_at` is required (staleness is derived at
   read time by design, never stored). **Pure read; window constant is the only
   new decision.**

5. **wire_payload_zero_drift** → the S2d scanners. `drift_capture._detect_unknown_shapes`
   is already a pure function over `ExchangeArtifacts` split by evidence
   provenance (anthropic: `adapters/anthropic.unknown_request_fields` +
   `unknown_response_event_types`; codex: `request_parser.unknown_request_fields`,
   `protocol.unknown_server_event_types`, `response_parser.parse_sse_event_payloads`).
   Evaluator: for each index.jsonl entry, rebuild `ExchangeArtifacts` via the
   disk storage `read_exchange` surface and re-run the scan offline; zero
   findings AND zero stored `wire_contract_drift` blocks for the run
   (`ExecutorBlockStore` query) = pass. Promote `_detect_unknown_shapes` to a
   public name (module-privacy rule) rather than duplicating the composition.
   **BLOCKED by criterion C2** (below) until the codex per-item vocabulary closes.

6. **transcript_zero_drift** → the index adapters (`index/adapters/claude.py`,
   `codex.py`) + `index/tailer_drift.emit_transcript_drift`. Evaluator: re-drive
   the adapters over the run's owned `transcripts/*.jsonl`; zero drift AND zero
   stored `transcript_contract_drift` blocks for the run = pass.
   **BLOCKED by criterion C3** until the meta allowlist closes.

7. **launch_capture_proven** → `read_compatibility_facts` (present + valid),
   sessions.json `minted: true` binding the native session id (the record's
   `session_ids`), and ≥1 captured exchange in index.jsonl.
   `compatibility_facts_digest` = the existing `compatibility_fact_digest()`.
   **Pure read + validate; zero new code beyond composition.**

## Bucket-B criteria: where each binds, and what blocks minting

- **C1 predicate-to-owner deterministic derivation** — this IS the slice. Each
  evaluator computes `CertificationPredicateResult.evidence_digest` from the
  owner evidence it actually read (stored row / artifact / bytes manifest), and
  `validate_certification_for_release` gains per-facet structural bindings: the
  wire predicate's evidence digest must equal the run's `wire_evidence_digest`,
  the capture predicate's must equal `compatibility_facts_digest`, etc. Today
  `_resolve_facet_references` (certification.py:395) only vocabulary-checks.
- **C2 codex per-item wire vocabulary** — `request_parser.unknown_request_fields`
  (request_parser.py:82) scans only top-level `provider_extras`; unknown item
  keys merely set `keep_raw` in `_parse_message_item` (line 158/218) and never
  reach the drift predicate. Verified live on main. **Blocks facet 5.**
- **C3 transcript meta allowlist** — adapters return `None` for unknown record
  types (claude.py:115/118, codex.py: many) and the tailer advances them as
  ordinary meta skips. Verified live on main. **Blocks facet 6.**

**Can facets 1/2/3/4/7 mint while 5/6 gate?** No. All seven facets are required
and `DECLARABLE_FACETS` is empty (deliberately, PR #305), so no record can mint
until C2 and C3 close. The gap closures are on the critical path; build them
first with fixtures cut from the real captures.

## Design decisions for Stuart

1. **Is compatibility.json the sealed evidence artifact?** Mostly yes: it is the
   run's identity anchor and `compatibility_facts_digest` is already its digest.
   But it cannot carry facets 5/6 (its digests are manifest-side), so the
   evaluators collapse to read+validate for facets 1/2/7, pure recompute for
   2/3/5/6, stored-snapshot reads for 1/3/4. Recommend: seal compatibility.json
   as-is via the existing digest; do NOT extend the frozen artifact.
2. **launch_facts_digest and lifecycle_evidence_digest semantics** (PR1 fields,
   never defined anywhere else in the repo — verified by grep). Proposal:
   launch_facts_digest = canonical digest of sessions.json content (the run
   dir's launch facts per CLAUDE.md); lifecycle_evidence_digest = canonical
   digest of index.jsonl (the bounded exchange sequence is the run's lifecycle).
   Alternative: collapse both into one and drop a field — but that churns the
   sealed record schema; defining semantics is cheaper.
3. **Version identity for evidence runs**: claude captures bind to release
   claude-2.1.211-r1 with observed 2.1.214 (in-range, not exact baseline);
   codex is exact 0.144.4. Nothing in `validate_certification_for_release`
   requires `observed_harness_version == baseline_version`. Accept in-range
   evidence, or require exact baseline (then claude needs the 2.1.214 successor
   path)? Recommend: accept in-range; the record already carries the observed
   version honestly and reproduction/successor mechanics handle drift.
4. **authentication_checkable strength**: require `authentication_status ==
   "authenticated"`, or any typed probe outcome (proving checkability, not
   login)? Facet name says checkable; recommend requiring a successful probe
   with `authenticated` for the minted connection, since Stuart's machine is
   the only minter and it is authenticated anyway.
5. **Scenario plumbing**: `MintPlan` carries `scenario_ids` only; the evidence
   source needs run-dir paths + DB scope. Extend the plan JSON with a
   per-scenario `{run_dir, executor_id}` map (declarative, no outcomes — keeps
   the plan-cannot-declare-a-pass invariant) rather than a sidecar file.

## Quality map

Strengths to lean on: every scanner is already pure and post-hoc by design
(detection deliberately runs off the hot path over persisted bytes — exactly an
offline evaluator's contract); the fact artifact is frozen-once with idempotent
retry; the mint pipeline is fail-closed end to end (suites must prove executed
tests, fixtures hash-bracketed, clean-worktree double-checked).

Risks/watch items:
- `_detect_unknown_shapes` is module-private; promote, don't duplicate.
- Facets 1/3/4 read Postgres rows keyed by executor_id; the preview-home
  captures ran under the same executor and DB, but the evaluator must fail
  closed (not skip) when a row is absent.
- Run 0252ea34 (claude) captured NO exchanges (transcript only) — scenario
  selection must cite the exchange-bearing runs: claude 9ac94cde (5 exchanges,
  tool use), codex 959a335b (7 exchanges, tool use), codex 8ffaeec2 (1).
- Codex responses ride transport.json frames (no response.raw by design);
  the wire evaluator must use the transport-frame path of the existing scan and
  keep its capture-unsafe digest rule.
- Auth freshness window: pick one constant, document it in the facet comment.

## Plan (3 PRs, ordered by the critical path)

- **PR-A: close the detection gaps (C2, C3), fixtures from the real captures.**
  Codex per-item closed key vocabulary in `request_parser` surfacing through
  `unknown_request_fields`; transcript meta allowlist in the two adapters with
  unknown types classified as transcript drift through the existing tailer hook.
  Red-before tests: a synthetic unknown item key / unknown record type must
  surface as drift; real capture bytes must scan clean. This PR alone improves
  the live drift plane regardless of certification.
- **PR-B: the evaluators + digest semantics + validator bindings (C1).**
  New `certification_evidence.py` (or similar) housing a
  `CapturedRunEvidenceSource` implementing `RuntimeEvidenceSource.collect`:
  per scenario, read compatibility.json + sessions.json + index.jsonl +
  exchanges + transcripts + stored snapshots, run the 7 derivations, emit
  `CertificationRuntimeRun` with the 5 digests per the agreed semantics.
  Extend `validate_certification_for_release` with per-facet owner bindings.
  Wire the CLI: replace `RealRuntimeEvidencePending()` with the real source
  when the plan supplies scenario bindings (keep fail-closed when absent).
- **PR-C: mint for real.** Plan JSONs for claude-2.1.211-r1 and codex-0.144.4-r1
  citing the preview-home runs; Stuart drives the mint on a clean tree; expect
  claude to derive a successor or reproduce per decision 3; pointers stay
  paused until Stuart flips them deliberately — this slice still does NOT
  activate anything.

Estimated shape: PR-A small (two focused vocab closures + fixtures), PR-B the
core (one new module ~300-400 lines + validator additions + tests), PR-C mostly
operational. No file approaches 700 lines.
