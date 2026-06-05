---
title: Baseline capture SCOUT executability report
type: projects
tags: [transport-matters, baseline-capture, scout, code-review]
summary: Reuse, quality, execution plan, and blocking answers for five confirmed baseline capture defects at main 5591db86
status: active
project: transport-matters
confidence: high
created: 2026-08-18
updated: 2026-08-18
---

## Reuse Map

### Reuse

| Needed capability | Existing owner | Use in the fix |
| --- | --- | --- |
| Cross launch masking | `api/src/transport_matters/session/wire_normalization.py::normalize_request` and `_CROSS_LAUNCH_MASKS` | Make `api/src/transport_matters/baseline_evidence.py::classify_aba` derive the stable fingerprint from each probe's existing `normalized_request`. Add no baseline mask list. |
| Launch delivery marker | `api/src/transport_matters/controlplane/envelope.py::launch_delivery_fields`, `extract_delivery_id`, and `prompt_digest` | Correlate parsed request IR against the probe owned prompt and delivery UUID. Remove prompt substring correlation. |
| Captured request parsing | `api/src/transport_matters/harnesses/certification_run_reader.py::read_captured_exchange` | Supply `InternalRequest` to `extract_delivery_id` for each completed disk candidate. |
| Complete JSONL iteration | `api/src/transport_matters/index/record_ingest.py::iter_complete_records` | Read transcript bytes, ignore a half written tail, and skip malformed complete JSON records. |
| Harness adapter lookup | `api/src/transport_matters/index/adapters/__init__.py::get_adapter` | Map `claude`, `codex`, or `grok` to the current transcript adapter. |
| Provider transcript semantics | `api/src/transport_matters/index/adapters/base.py::TranscriptAdapter.normalize` | Use normalized turn roles instead of literal JSON `role` or `type` checks. |
| Adapter context construction precedent | `api/src/transport_matters/harnesses/certification_evidence.py::CapturedRunEvidenceSource._check_transcripts` | Reuse `SessionBinding`, `FileTailSource`, and snapshot stem conventions. Add no adapter layer or provider switch. |
| Session store preflight | `api/src/transport_matters/captured/dependencies.py::CapturedRunDependencies.check_session_store` | Invoke the injected preflight before source home creation or run preparation. |
| Preflight failure contract | `api/src/transport_matters/capture_rpc.py::CaptureLeaseRegistry.prepare_capture` | Stop when the callable returns an error, before proxy or client launch. |
| Artifact version enforcement | `api/src/transport_matters/baseline_evidence.py::BaselineBundle`, `api/src/transport_matters/baseline_store.py::read_current_baseline`, and `read_baseline_bundle` | Bump the bundle and current pointer contract together. Reject version 1 artifacts and regenerate. |
| Existing local driver | `api/src/transport_matters/baseline_harvest.py::main` | Keep the module command as the only end to end driver. Add no command. |

### Existing infra

`api/src/transport_matters/baseline_harvest.py::main` selects one harness and model, then `api/src/transport_matters/baseline_capture.py::harvest_controlled_baseline` performs three fresh A1, B, A2 captures. `api/src/transport_matters/captured/run.py::prepare_captured_run` starts mitmdump, and `api/src/transport_matters/baseline_capture.py::_capture_probe` starts the prepared client in a detached PTY. The focused fake surfaces are `api/src/transport_matters/test_baseline_harvest.py::test_main_selects_one_requested_cell_and_delegates_capture` and `api/src/transport_matters/test_baseline_capture.py::_install_capture_fakes`. They do not exercise a real proxy, harness, provider, title request, adapter binding, or session store preflight.

Two real version 1 Codex bundles exist at `/Users/alphab/.mdx/TMP/pstack/tm-382/live-codex-2/bundles/codex/codex/gpt-5.6-sol/75f79dfa-a0c0-4fb0-afff-9b33eb10decc.json` and `/Users/alphab/.mdx/TMP/pstack/tm-382/live-codex-2/bundles/codex/codex/gpt-5.6-sol/fe70a6a2-67c0-4cb8-a4bf-734b3677ff54.json`. Their current pointer is beside them under `current/codex/codex/gpt-5.6-sol.json`. The active default output, `/Users/alphab/.transport-matters/baselines`, is absent. Preview and dev baseline directories are also absent.

### Similar checked and rejected

* `api/src/transport_matters/request_inventory.py::request_contains_text` parses request bytes correctly, but substring matching cannot distinguish the title request. Replacing correlation leaves it with no production caller, so delete it and its focused assertions.
* The deleted `api/src/transport_matters/baseline_harvest.py::_capture_cell` selected requests with tool schemas. This is useful history and fixture material, but delivery identity is the stronger existing contract.
* Calling `api/src/transport_matters/controlplane/envelope.py::extract_delivery_id` with request IR alone always returns `None`. The launch fields are required.
* `api/src/transport_matters/index/subagents.py` contains Claude specific assistant record checks. Its subagent discovery contract does not provide provider neutral reply completion.
* `api/src/transport_matters/index/record_ingest.py::iter_complete_records` owns byte safety only. It does not infer roles.
* `api/src/transport_matters/harnesses/certification_evidence.py::CapturedRunEvidenceSource._check_transcripts` validates snapshots and adapter drift. It does not return normalized turns, so baseline cannot call it as a reply predicate.
* `api/src/transport_matters/capture_rpc.py::CaptureLeaseRegistry.prepare_capture` rejects the external web runtime used by baseline capture. It is the preflight precedent, not a replacement launch path.
* `api/src/transport_matters/captured/run.py::run_captured_run_on_local_tty` owns an interactive client lifecycle and cannot poll capture artifacts concurrently.

### None found with searches run

No production fake, fixture, recorded, replay, or offline mode drives `baseline_harvest` end to end. No provider neutral `transcript_has_reply` predicate exists outside baseline capture. No public function accepts a whole `CapturedRunDependencies` value, runs its preflight, and prepares the external runtime. No migration, fallback, or regeneration path handles a baseline schema mismatch. No repository fixture contains both Claude title request bytes and the owned first turn request.

Searches run:

```text
rg -i 'offline|fixture|recorded|replay' api/src/transport_matters/baseline_*.py api/src/transport_matters/test_baseline_*.py api/tests/fixtures
git log -G 'offline|fixture|recorded|replay' -- api/src/transport_matters/baseline_*.py api/src/transport_matters/test_baseline_*.py
git log -S titletra --all
git log -S has_tool_schemas --all
rg 'transcript.*reply|has_reply|assistant.*role|role.*assistant|NormalizedTurn' api/src/transport_matters
rg 'iter_complete_records\(' api/src/transport_matters
rg 'check_session_store|CapturedRunDependencies|prepare_captured_run\(' api/src/transport_matters --glob '*.py'
rg -l --hidden --no-ignore '"static_fingerprint"' /Users/alphab --glob '*.json'
```

## Quality Map

### Duplication

`api/src/transport_matters/baseline_capture.py::_capture_probe` and `api/src/transport_matters/capture_rpc.py::CaptureLeaseRegistry._prepare_with_dependencies` hand forward the same eight launch dependencies. The capture RPC performs the separate preflight; baseline omits it. `api/src/transport_matters/baseline_capture.py::_transcript_has_reply` also reimplements JSONL iteration and provider role inference. `api/src/transport_matters/baseline_capture.py::_build_probe_evidence` and `api/src/transport_matters/baseline_evidence.py::BaselineBundle.validate_probe_contract` reimplement `api/src/transport_matters/controlplane/envelope.py::prompt_digest`. The five defect pass should remove the correlation and transcript duplication. Prompt digest consolidation fits the same edit if it reduces lines.

### Boundary

Cross launch volatility belongs to wire normalization. Delivery identity belongs to the control plane envelope. Complete transcript record parsing belongs to record ingest. Harness semantics belong to transcript adapters. Session store readiness belongs to the injected capture dependency and is checked before lower level run preparation. Artifact compatibility belongs to `BaselineBundle` and `baseline_store`. Keeping these owners prevents another baseline specific mask, JSONL reader, provider switch, preflight, or schema loader.

### Dead code

After delivery based correlation, `api/src/transport_matters/request_inventory.py::request_contains_text` has no production caller and should be deleted with its test assertions. After adapter based reply detection, `api/src/transport_matters/baseline_capture.py::_json_has_assistant_role` should be deleted. Keep `_json_contains_text`; it consumes decoded transcript records and has a different boundary. `ProbeEvidence.normalized_request` is currently write only after validation and serialization. The fingerprint fix should make it an input to `classify_aba`. The literal `ProbeEvidence.correlation_method="unique-prompt"` becomes false after delivery correlation and must change with the artifact version.

### Grooming recommendation

Keep the implementation inside the existing files. Add no production file, helper, type, adapter, or command. Delete the displaced prompt and literal role paths in the same change. Use artifact schema version 2 and require fresh bundles because the product is pre release and the default store is empty. The only line growth that needs scrutiny is adapter context construction. Follow the compact `SessionBinding` precedent in `CapturedRunEvidenceSource._check_transcripts`; if real run facts cannot supply that context cleanly, stop and revise the plan before adding an adapter facade.

## Plan

### Decision needed

1. Approve a version 2 bundle and current pointer contract with deliberate version 1 invalidation. A migration would preserve fingerprints whose meaning changed.
2. Use the control plane delivery marker for request correlation. `_capture_probe` owns the exact prompt and UUID, so it can pass `launch_delivery_fields(prompt, delivery_id)` beside each parsed `InternalRequest`. Current disk artifacts cannot recover the UUID on their own.
3. Use a real `SessionBinding` and `TurnContext` for transcript normalization, following certification evidence. Do not add a provider switch or a new adapter method. This is the one step that may exceed near neutral lines; the deletion of `_json_has_assistant_role` and the raw line reader should offset it.
4. Match `CaptureLeaseRegistry.prepare_capture` by calling the injected `check_session_store` callable. Keep database materialization and migration outside this five defect pass.

### Proposed steps bound to the reuse map

1. Change request correlation in `api/src/transport_matters/baseline_capture.py::_wait_for_correlated_exchange` to parse completed exchanges with `read_captured_exchange` and resolve their delivery marker with `extract_delivery_id` plus probe owned launch fields. Thread the UUID into the poller, update the correlation method contract, delete `request_contains_text`, and restore a title side request fixture.
2. Change `api/src/transport_matters/baseline_evidence.py::classify_aba` so stable fingerprint records use the already stored cross launch normalized request. Reuse canonicalization and request observation code already in the module area. Add no masks or pointer walker.
3. Bump `api/src/transport_matters/baseline_evidence.py::BaselineBundle.artifact_schema_version` and the current pointer version written and checked by `api/src/transport_matters/baseline_store.py`. Keep hard rejection for version 1, with a clear error. Regenerate rather than migrate.
4. Replace transcript `read_text`, `splitlines`, and literal assistant checks in `api/src/transport_matters/baseline_capture.py::_transcript_has_reply` with `Path.read_bytes`, `iter_complete_records`, `get_adapter`, and `TranscriptAdapter.normalize`. Construct the existing binding and turn context from the run and owned snapshot facts. Delete `_json_has_assistant_role`.
5. Call `capture_dependencies.check_session_store()` at the start of `api/src/transport_matters/baseline_capture.py::_capture_probe`, before `source_home.mkdir` and `prepare_captured_run`. Stop on a returned error. Add the callable to the focused dependency fixture.
6. Inspect the final diff for net line count. Any new helper, type, adapter facade, command, mask, parser, or parallel compatibility path fails this plan.

### Tests and gates

Add focused regressions in `api/src/transport_matters/test_baseline_capture.py` for a Claude title request that wraps the controlled prompt, a Grok user and assistant update sequence, a malformed complete transcript record, a half written multibyte tail, a raw U+2028 inside a complete record, and a failing session store preflight that proves no source home, proxy, or client starts. Extend `api/src/transport_matters/test_baseline_evidence.py` with date and cwd only changes that remain exact after cross launch masking, plus version 1 load rejection and version 2 round trip coverage. Remove the obsolete substring assertions from `api/src/transport_matters/test_request_inventory.py` if `request_contains_text` is deleted.

Implementation gates are `cd api && just check` and `cd api && just test`. Behavioral proof still requires two live Claude runs through `cd api && uv run python -m transport_matters.baseline_harvest --harness claude`: the first writes version 2, the second reports an exact comparison, and the captured title side request does not become the selected exchange. Recheck a clean tree and the same HEAD before and after the live proof. The SCOUT pass ran no tests, builds, or harness processes.

## Blocking Questions

### Q1. Surface

No offline end to end path exists. The local entry point is `api/src/transport_matters/baseline_harvest.py::main`, invoked exactly as `cd api && uv run python -m transport_matters.baseline_harvest --harness claude`. The command is unattended, but it is live: `api/src/transport_matters/harnesses/probes/runner.py::run_model_enumeration_probe` runs Claude model and effort subprocesses, then `api/src/transport_matters/baseline_capture.py::harvest_controlled_baseline` starts three real A1, B, A2 captured clients. `api/src/transport_matters/captured/run.py::prepare_captured_run` starts mitmdump for each probe, and `api/src/transport_matters/baseline_capture.py::_capture_probe` starts the client in a detached PTY. Unit fakes exist in `api/src/transport_matters/test_baseline_harvest.py` and `test_baseline_capture.py`, but no fixture harness or recorded mode exists. A live harness and provider launch is unavoidable; the closest offline surface is `_install_capture_fakes`, which does not prove the launch seam.

### Q2. Artifact compat

`artifact_schema_version` exists as `Literal[1]` in `api/src/transport_matters/baseline_evidence.py::BaselineBundle`. `api/src/transport_matters/baseline_store.py::read_baseline_bundle` enforces it through Pydantic model validation, while `read_current_baseline` separately rejects a current pointer version other than 1. A disagreement raises before comparison and before any new launch because `api/src/transport_matters/baseline_capture.py::harvest_controlled_baseline` loads the current bundle first; no migration, fallback, or automatic regeneration exists. Keeping version 1 while changing fingerprint meaning would load the old bundle and report breaking drift instead. Two real version 1 Codex bundles exist under `/Users/alphab/.mdx/TMP/pstack/tm-382/live-codex-2`; the current default store is `/Users/alphab/.transport-matters/baselines`, and it is not populated.

### Q3. Delivery ID

No. The delivery UUID is not recoverable from Claude request bytes. `api/src/transport_matters/controlplane/envelope.py::launch_delivery_fields` stores the UUID and exact prompt digest in transport owned launch fields, while `extract_delivery_id` uses the request only to prove that digest against a first user text block. `api/src/transport_matters/wire_store_observer.py::WireStoreObserver._resolve_run` obtains a `ProxyRunBinding`, and `_submit_exchange` passes `binding.launch_fields` to the extractor. `api/src/transport_matters/baseline_capture.py::_wait_for_correlated_exchange` receives only storage directory, run ID, scenario, prompt, and timeout; `IndexEntry` and `CapturedExchange` carry no delivery ID. Its caller still owns the original prompt and UUID, and `CapturedRunSpawnSpec.launch_env` contains serialized launch fields, but the current correlator has no access to the structured binding fields. `extract_delivery_id` therefore is not a drop in call on captured bytes; the plan must thread or reconstruct the launch fields.

### Q4. Transcript seam

`api/src/transport_matters/index/record_ingest.py::iter_complete_records` can be called directly after `Path.read_bytes`; it needs no registry or cursor and returns complete records plus the consumed byte count. `api/src/transport_matters/index/adapters/base.py::TranscriptAdapter.normalize` needs an adapter instance and a `TurnContext`, which in turn needs a `SessionBinding`, source path, and sequence. `api/src/transport_matters/index/adapters/__init__.py::get_adapter` is the live registry from harness name to `ClaudeAdapter`, `CodexAdapter`, or `GrokAdapter`. Baseline capture does not currently construct a binding or turn context. `api/src/transport_matters/harnesses/certification_evidence.py::CapturedRunEvidenceSource._check_transcripts` is the closest production precedent: it builds a lightweight binding from the snapshot stem, adapter provider, run ID, harness, and recorded time, then uses the same record seam. There is no shared reply predicate, so adapter normalization needs this existing context setup before baseline can call it.

### Q5. Preflight

At this commit the method is `api/src/transport_matters/capture_rpc.py::CaptureLeaseRegistry.prepare_capture`; no `register_capture` symbol exists. It calls `CapturedRunDependencies.check_session_store`, raises `CaptureSessionStoreUnavailable` on a returned error, and only then calls `_prepare_with_dependencies`. `api/src/transport_matters/baseline_capture.py::_capture_probe` must call `capture_dependencies.check_session_store()` before source home creation and `prepare_captured_run`, then stop if the result is not `None`. The same eight remaining dependency fields are hand unpacked by `CaptureLeaseRegistry._prepare_with_dependencies`; no public whole bundle preparation helper exists. The search covered `CapturedRunDependencies`, `default_claude_run_dependencies`, `check_session_store`, and every production `prepare_captured_run` call.
