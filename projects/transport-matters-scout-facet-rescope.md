# Scout: certification facet re-scope (behavioral 13 → observability ~7)

Mode 1 read-only survey, 2026-07-18, tree at 8947628a (feat/s2g-mint-activation, PR #305).
Scope: map Stuart's 7 observability facets onto existing owners, bind facets 5/6 to the
S2d drift machinery, answer the auth-gated capture question firsthand, state the PR1/PR3 delta.

## Headline answers

**Auth-gated question: NO new authenticated capture is required.** Tier-1 already owns
real wire payloads AND owned transcripts for both harnesses:

- **codex 0.144.4 (exact embedded baseline match):** run `dev-helioy-transport-matters-s2/69983fa3/ffbd7e9d-...`
  has 1 real exchange (request.raw 48 KB, request.ir.json 101 KB, transport.json 306 KB of
  websocket frames — codex responses ride the transport, no response.raw by design) plus an
  owned transcript. `compatibility.json` binds it to `codex-0.144.4-r1`, observed_version `0.144.4`.
- **claude 2.1.212 / 2.1.214 (in-range, NOT the 2.1.211 baseline):** runs under
  `dev-helioy-transport-matters-s2/69983fa3/` (2.1.212: 5 exchanges across 2 runs, transcripts
  incl. a 64 KB jsonl) and `dev-helioy-transport-matters/ecd9b0df/` (2.1.214: 2 runs with
  exchanges). All facts artifacts bind to `claude-2.1.211-r1` (minimum 2.1.211 admits them).
  No capture at exactly 2.1.211 exists.

Consequence: facets 5/6 can be certified offline from owned bytes today. The only decision is
the claude version identity: either (a) the in-version facet accepts observed >= minimum under
the release (the launch gate already matched these runs to `claude-2.1.211-r1`), or (b) mint the
claude successor at baseline 2.1.212/2.1.214 from owned evidence — still no new auth capture.
Caveat for Stuart: codex evidence is thin (one exchange, 311-byte transcript); richer capture
would strengthen the record but is a quality choice, not a gate.

Second correction to the brief: `run_authentication_probe` is **no longer unwired**. PR2 wired it
as the default `probe` of `state_refresh.refresh_harness_state`, running at startup refresh and
persisting access evidence via `connections_store.ExecutorEvidenceStore`. Facet 4 reads that
stored evidence; nothing new to build there.

## Facet map (owner → evidence → predicate)

| # | Facet | Existing owner (file + symbol) | Evidence certified against | Predicate |
|---|-------|-------------------------------|---------------------------|-----------|
| 1 | INSTALLED | `capabilities.py` `detect_harnesses` / `resolve_harness_binary` / `_probe_harness_version`; persisted by `harnesses/state_refresh.py` `refresh_harness_state` through `EvidenceWriter` → `connections_store.ExecutorEvidenceStore`; read as `latest_harness_observation` (`harnesses/connections.py` `LocalHarnessObservation`), surfaced by `harnesses/inventory.py` `HarnessInstallationInfo.confirmed_installed` | Stored harness observation (executable path + `--version` string) | Observation exists for the harness with a runnable path and a parsed version string |
| 2 | IN-VERSION | `harnesses/compatibility.py` `match_release` + `CompatibilityMatch` (`normalize_version`, `compare_versions`); applied by `harnesses/resolver.py` `_compatibility_disposition`; per-run binding recorded by `harnesses/compatibility_facts.py` `CompatibilityFactArtifact` (`observed_version`, `release_id`) | Stored observation version vs the release under certification | `match_release(observed)` yields compatible for this release; the cited tier-1 runs' facts artifacts record the same release_id |
| 3 | MODELS/EFFORTS launch profile | `harnesses/resolver.py` `launch_options`, `_resolve_effort`, `_verify_native_effort`, `_select_edge`, target catalog via the release's `target_catalog_revision`/`route_catalog_revision` | Resolver output over the stored snapshot + the release's catalogs; per-turn actuation record (`turn.json` in the exchange dir) | The release's catalogs resolve a launch option for the harness, and captured turns show requested model/effort actuated (the existing `actuation_matches_request` predicate survives here) |
| 4 | AUTH checkable | `harnesses/probes/runner.py` `run_authentication_probe` + per-harness adapters `probes/claude.py`, `probes/codex.py`, `probes/grok.py` (via `probes/targets.py`); persisted by `state_refresh._refresh_connection_access` → `connections_store.upsert_access_observation`; surfaced by `inventory.ConnectionDiagnosticsInfo` (incl. staleness suppression) | Stored access observation at the current connection revision | Latest access evidence is an authenticated status, not stale (revision matches the connection) |
| 5 | REQ/RES PAYLOAD zero drift | Live seam: `drift_capture.py` `WireDriftObserver` (post-persist exchange sink) → `_detect_unknown_shapes` → pure detectors `adapters/anthropic.py` `unknown_request_fields` / `unknown_response_event_types`, `codex/request_parser.py` `unknown_request_fields`, `codex/protocol.py` `unknown_server_event_types`, `codex/response_parser.py` `parse_sse_event_payloads`; emission via `harnesses/drift_emitter.py` `DriftEmitter` → `blocks_store.emit_drift_evidence` (`wire_contract_drift`) | Owned tier-1 exchange bytes (request.raw / request.ir.json / response.raw / transport.json) of the cited runs | Re-run the pure detectors over every cited exchange: all unknown-field/unknown-event sets empty; zero stored `wire_contract_drift` blocks for those runs |
| 6 | TRANSCRIPT zero drift | Live seam: `index/tailer_drift.py` `emit_transcript_drift` (`TranscriptDriftHook`) ← injected by `drift_capture.py` `make_tailer_drift_hook`, gated by `blocks_store.transcript_failure_is_drift`, emitted as `transcript_contract_drift`/`transcript_reader_drift` (`harnesses/blocks.py`) | Owned transcript copies under `<run>/transcripts/*.jsonl`, re-read through `index/adapters/claude.py` / `index/adapters/codex.py` | Drive the transcript adapter over each owned transcript: full parse, zero commit failures / locator divergence; zero stored transcript drift blocks for those runs |
| 7 | CAN LAUNCH + CAPTURE | Launch: `run_lifecycle.py` `prepare_captured_run` seam + `controlplane/launch_service.py`; facts: `compatibility_facts.CompatibilityFactArtifact` (compatibility.json); session-id injection: `sessions.json` `minted: true` + `native_session_id`; launch/session drift kinds `launch_contract_drift` (`drift_emitter.ActuationDriftObserver`) and `session_contract_drift` (`capture_rpc.py`) | The cited tier-1 run dirs themselves | Run has a valid facts artifact for the release, ≥1 captured exchange (index.jsonl + exchange dir), a minted owned session binding, and zero launch/session contract drift blocks |

Facets 1–4 certify against the SAME stored snapshots the inventory plane already reads
(PR2's `harness_inventory` join) — no new probes, no live calls at mint time. Facets 5–7
certify against owned tier-1 bytes re-driven through the exact production parsers — the
"zero drift" predicate is literally "the S2d detectors find nothing", not a new parser.

## Reuse contract for facets 5/6 (do-not-reinvent map)

The mint-time evidence source should call the pure detector layer directly, NOT the emitter:
`_detect_unknown_shapes` is the exact composition needed but is private to `drift_capture.py`;
the module-privacy rule means the re-scope either promotes it to a public name
(`detect_unknown_shapes`) or the mint source composes the same public per-provider functions
itself. Promotion is the DRY move: one composition, two callers (live sink + mint).
The emitter/store half (`DriftEmitter`, `emit_drift_evidence`) stays live-plane-only; the mint
additionally QUERIES stored drift blocks for the cited runs (read via `blocks_store.ExecutorBlockStore`)
so live-time detections and mint-time re-scan must both be clean.

For transcripts, the reusable unit is the `index/adapters/{claude,codex}.py` reader plus the
`transcript_failure_is_drift` gate; the mint drives the reader over the owned copy and treats
any hook-worthy failure as facet failure.

## Delta: PR1 vocabulary + PR3 tooling

PR1 (`harnesses/certification.py`), all mechanical, contained in the closed vocabularies:
- `CertificationFacetId` Literal: 13 behavioral ids → ~7 observability ids (suggested:
  `harness_installed`, `version_in_range`, `launch_profile_resolved`, `authentication_checkable`,
  `wire_payload_zero_drift`, `transcript_zero_drift`, `launch_capture_proven`).
- `CERTIFICATION_FACETS` tuple, `CertificationPredicateId` Literal, `FACET_PREDICATES` map: 1:1 rewrite.
- `DECLARABLE_FACETS`: `approval_structured_input` disappears with its facet. Open decision:
  does anything stay declarable? Candidate: none — every observability facet is required for a
  certifiable harness (grok stays excluded via `launch=None`, it never reaches certification).
- COMPATIBILITY-PUBLISHING.md certification list must be rewritten in lockstep (the 1:1
  vocabulary test pins doc ↔ code).
- Record/evidence models (`FixtureEvidence`, runtime evidence, digests, activation gate in
  `compatibility_store._require_certified_active_pointers`) are UNTOUCHED — the substrate keeps.

PR3 (`certification_minting.py` + script + fixtures):
- `MintPlan`/`PlannedFacet` shapes unchanged; plan fixtures and `certification_test_support.py`
  facet constants re-keyed to the new ids; all test digests regenerate.
- `RealRuntimeEvidencePending` is replaced by a real runtime evidence source that takes cited
  tier-1 run paths, re-runs the pure detectors/readers (facets 5–7) and reads stored snapshots
  (facets 1–4). This becomes implementable NOW because the evidence already exists on disk —
  the fail-closed placeholder existed only because behavioral facets needed new authenticated
  scenario captures.
- Suite/junit/clean-tree/atomic-write mechanics: unchanged.

## Decision points for Stuart

1. Claude version identity: accept in-range 2.1.212/2.1.214 evidence for `claude-2.1.211-r1`,
   or mint the successor at the observed baseline (recommended: successor at 2.1.214 — the
   facts artifacts already bind those runs, and `exact_harness_version` semantics stay honest).
2. Codex evidence depth: certify from the single owned 0.144.4 exchange now, or take one richer
   unattended capture first (quality, not a blocker).
3. Any declarable facets in the new vocabulary, or all-required (scout recommends all-required).
