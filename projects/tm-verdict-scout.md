# Provider rejection verdict scout

Date: 2026-07-19

Scope: read only scout on `feat/launch-verdict-surface` at `3ae57012824e`. The repository was clean before and after the investigation. No build ran.

## Verdict

The current `PromptReceipt` path proves request submission only. It cannot resolve `failed` from a provider rejection.

`LaunchService._resolve_first_prompt()` delegates directly to `DeliveryProofSubscription.resolve()` (`api/src/transport_matters/controlplane/launch_service.py:423`). Its query returns `submitted` whenever one matching exchange exists (`api/src/transport_matters/controlplane/delivery_proof.py:113`). It discards the existing `WireDeliveryClaim.finalized` fact and never reads response, transcript, or run status. A provisional outbound request can therefore seal `submitted` before the rejection arrives.

The existing drift path is downstream. `ActuationDriftObserver.observe_prompt_receipt()` emits only when another producer supplies a failed receipt with the allowlisted `harness_rejected_prompt` reason (`api/src/transport_matters/harnesses/drift_emitter.py:257`). `prompt_models.py` explicitly says no production path mints that reason (`api/src/transport_matters/controlplane/prompt_models.py:43`). `RUNTIME-SURFACING-S2-PLAN.md:189` records the same gap.

No semantic selected model rejection classifier exists. Searches across `api/src` and `packages` for `model_not_found`, `isApiErrorMessage`, `apiErrorStatus`, and `invalid_request_error` returned no implementation hits. The implementation needs one canonical classifier per native source and one shared verdict producer. The wire and transcript format boundaries, durable live status, Activity projection, roster, Watch, delivery claims, and drift consumer are reusable.

## Governing contract

`LAUNCH-CONTRACT.md:178` says provider access observations never authorize or block launch, and line 179 requires rejection to surface from the live run. Lines 348 to 352 define `submitted`, `unknown`, and `failed`. The feature must preserve process creation and report the observed verdict.

The required behavior is therefore:

1. Spawn the run for every selected target that passes launch resolution.
2. Observe the native first turn.
3. For a prompted launch, return `PromptReceipt(status="failed", reason="harness_rejected_prompt")` when the classified rejection arrives inside the ten second proof deadline.
4. For an interactive launch, retain a durable sticky run verdict and expose it through the existing control plane observation surfaces.

No preflight target rejection or authentication gate belongs in this change.

## Current prompted flow

1. `LaunchService.launch()` creates the run, then calls `_resolve_first_prompt()` (`launch_service.py:286`).
2. `_resolve_first_prompt()` calls `DeliveryProofSubscription.resolve()` with the bounded deadline (`launch_service.py:423`).
3. `DeliveryProofSubscription._query()` calls `wire_delivery_exchanges()` and returns `submitted` for one exchange (`delivery_proof.py:113`).
4. `ControlPlaneReadStore.wire_delivery_exchanges()` maps richer claims back to exchange ids (`controlplane/read_store.py:75`). The richer `wire_delivery_claims()` result already carries `exchange_id` and `finalized` (`read_store.py:84`, `controlplane/delivery_models.py:86`).
5. After the receipt is sealed, `LaunchService` gives it to `ActuationDriftObserver` as best effort evidence (`launch_service.py:291`).

The missing facts are semantic provider outcome and rejection precedence. `PromptReceipt.reason` already carries the required stable code, so its public shape need not grow (`prompt_models.py:58`).

## Native evidence and current reachability

### Claude

The supplied native transcript contains the exact structured rejection at:

`/Users/alphab/.claude/projects/-Users-alphab-Dev-LLM-DEV-helioy-tm-launch-contract/0d832d2b-65b2-488b-bc30-9c6804d331ef.jsonl:20`

The record is an assistant row with:

```json
{
  "error": "model_not_found",
  "isApiErrorMessage": true,
  "apiErrorStatus": 404
}
```

The source is reachable and durable:

* `TranscriptTailer._poll_cursor()` snapshots complete raw bytes before normalization, then submits every complete record (`api/src/transport_matters/index/tailer.py:194`, especially lines 217 to 255).
* `ClaudeAdapter.normalize()` accepts the assistant row and maps the nested message, while ignoring the three top level rejection fields (`api/src/transport_matters/index/adapters/claude.py:141`).
* `session.ingest.build_event()` preserves `raw=dict(record)` in the session event (`api/src/transport_matters/session/ingest.py:118`).
* Activity reads that raw object, but `claudeRow()` only derives message blocks, stop reason, and usage (`packages/activity/src/adapters/transcriptRecords.ts:179`).

Recommended classifier boundary: a pure Claude transcript classifier beside `ClaudeAdapter`, invoked from the one tailer record loop after the Tier 1 snapshot succeeds. Match all three structured fields. Do not infer rejection from the human readable message. Feed its result to the shared verdict producer. Activity then consumes the shared durable state, so TypeScript does not gain a second Claude parser.

### Codex

The supplied run contains the exact server frame in two wire exchanges:

* `/Users/alphab/.transport-matters/workspaces/dev-helioy-transport-matters/ecd9b0df/87ca05c9-db33-469d-8679-c749986e5e4e/20260719T121028Z-70461065/transport.json:2790`
* `/Users/alphab/.transport-matters/workspaces/dev-helioy-transport-matters/ecd9b0df/87ca05c9-db33-469d-8679-c749986e5e4e/20260719T121035Z-924892c4/transport.json:2849`

Each has this structured shape:

```json
{
  "type": "error",
  "status": 400,
  "error": {
    "type": "invalid_request_error",
    "message": "The 'xyz' model is not supported when using Codex with a ChatGPT account."
  }
}
```

The native rollout at `/Users/alphab/.codex/sessions/2026/07/19/rollout-2026-07-19T16-02-31-019f799c-df8b-7c52-82a3-45831526bcf2.jsonl` contains `task_started` at line 2, model `xyz` at line 6, and a misleading `task_complete` at line 11. The rollout cannot own this verdict.

The wire source is reachable and durable:

* `codex.transport._message_artifact()` stores server direction, event type, raw payload text, and parsed payload JSON (`api/src/transport_matters/codex/transport.py:395`).
* `TransportMessageArtifact` and `TransportArtifacts.messages` own that representation (`api/src/transport_matters/storage/base.py:225`, `storage/base.py:249`). This is the object serialized as `transport.json`.
* Codex finalization persists the exchange before `emit_to_index()` fans it to observers (`api/src/transport_matters/codex/exchange.py:263`).
* `WireDriftObserver` already scans post persistence `artifacts.transport.messages` (`api/src/transport_matters/drift_capture.py:80`, `drift_capture.py:174`).

Current behavior is generic drift. `CODEX_KNOWN_SERVER_EVENT_TYPES` omits `error`, so the frame becomes `unknown_response_event` through `unknown_server_event_types()` (`api/src/transport_matters/codex/protocol.py:34`, `protocol.py:69`). The derived `entry.json` and `turn.json` reduce both supplied exchanges to `interrupted`, `websocket_close`, and `ws_close_1006`. No semantic rejection survives there.

Recommended classifier boundary: a pure Codex frame classifier in `codex/protocol.py`, applied by a post persistence verdict observer to `ExchangeArtifacts.transport.messages`. Match server direction, `type=error`, status 400, nested `error.type=invalid_request_error`, and the narrow unsupported model message signature. The persisted `transport.json` remains the authority. Once certified by the supplied capture fixture, add `error` to the known event vocabulary so the semantic verdict and generic unknown event drift do not double report the same frame.

## Shared durable verdict

Use the existing `run_live_status` path. Add a sticky `model_rejected` kind outside `PROVIDER_CONDITIONS`.

That separation is required by the current contracts. `provider_conditions.py:19` owns only authentication and usage conditions, and its module contract keeps those conditions disjoint from harness rejection drift. A selected model rejection is the existing `harness_rejected_prompt` contract fact.

The shared flow should be:

```text
Claude Tier 1 transcript record      Codex Tier 1 transport.json frame
               \                      /
             native pure classifiers
                       |
             one verdict observer
                       |
        run_live_status kind=model_rejected
                       |
       @tm/activity needs-you-model-rejected
                       |
             roster and Watch
```

Reuse details:

* `LiveStatusObserver` already serializes latest wins writes and preserves sticky conditions until a genuine later successful turn (`api/src/transport_matters/live_status_observer.py:74`, `live_status_observer.py:228`, `live_status_observer.py:396`). Reuse this behavior through a dedicated model rejection offer method.
* `SessionWriter.submit_run_live_status()` persists and sends a run event notification (`api/src/transport_matters/session/writer.py:152`).
* `SessionEventHub.subscribe_run_events()` supplies durable catch up semantics for that notification (`api/src/transport_matters/session/listen.py:219`).
* `@tm/activity` already reads the current row from Postgres (`packages/activity/src/adapters/postgresRecords.ts:508`) and projects run status plus structured `needs_you` (`packages/activity/src/projections/workspaceActivity.ts:55`).
* The Activity contract owns all needs you tiers and payloads in one place (`packages/contract/src/activity/wire.ts:7`, `wire.ts:38`, `wire.ts:74`).

This needs a database migration after `0026_harness_enablement` because the `run_live_status_kind_check` constraint is closed (`api/migrations/versions/0025_provider_condition_kinds.py:22`). The same addition crosses the Python literal and enum, TypeScript port, Activity event and machine, wire contract, Python mirrors, and migration head.

The verdict should remain sticky until a later genuine successful turn or run exit. That lets an interactive caller observe it after the failed user turn and recover naturally after choosing a supported model.

## Interactive control plane seam

The existing Activity read model is the correct public seam.

`GatewayActivityRun` already carries `status`, `tier`, and `needs_you` (`api/src/transport_matters/controlplane/activity.py:90`). `ControlPlaneService._roster_snapshot()` reads workspace Activity and creates `RosterItem` values (`api/src/transport_matters/controlplane/service.py:603`). The public roster currently keeps `state` but drops `needs_you` (`service.py:620`, `controlplane/observe_models.py:37`). Extend `RosterItem` with the structured payload and document it.

Agent query:

1. Call `whoami()` to get the authenticated `run_id` (`controlplane/service.py:206`, `api/v1/controlplane_mcp.py:223`).
2. Call `roster()` and match that `run_id` (`controlplane/service.py:173`, `api/v1/controlplane_mcp.py:226`).
3. Read `state="needs-you-model-rejected"` and `needs_you={"kind":"model_rejected"}`.

A director can query `roster()` directly for any managed run. Existing Watch delivers the prompt push when a run enters the needs you tier, plus `state_changed` (`api/src/transport_matters/controlplane/watch.py:511`). Its `status` should be `needs-you-model-rejected`. The roster remains the structured pull authority, consistent with the current push references and pull content design.

`GET /v1/runs/{id}` is a process resident gateway lifecycle view. It should not gain a second semantic verdict representation. `ControlPlaneReadStore` remains the delivery proof and session evidence adapter. No new run verdict endpoint or MCP verb is needed.

## Prompt proof changes

Extend the existing proof subscription and read store. Do not create a parallel launch proof service.

Recommended resolution order:

1. Query the existing delivery claims. More than one claim returns `unknown` with `duplicate_provider_requests`.
2. Query the durable current run live status. A matching `model_rejected` verdict returns `failed`, reason `harness_rejected_prompt`, and the available exchange id.
3. Return `submitted` only after positive response evidence or one finalized claim has settled without a rejection.
4. Continue until either wire delivery or run event notification wakes the query. At the deadline, return `unknown` with `proof_deadline`.

The implementation must close the race between an exchange finalization doorbell and the verdict write. A finalized claim cannot immediately win over a concurrently scheduled semantic rejection. The clean proof is a single outcome query whose result encodes one of `rejected`, `accepted`, `pending`, or `ambiguous`, with rejection taking precedence. If the existing stores cannot provide that ordering atomically, positive response evidence should seal `submitted`; a bare outbound request should remain pending.

Once the failed receipt exists, `ActuationDriftObserver` already emits `startup_prompt_rejected`. This is direct reuse.

## Reuse map

| Capability | Owner | Verdict |
| --- | --- | --- |
| Prompted launch receipt orchestration | `controlplane/launch_service.py::LaunchService._resolve_first_prompt` | Reuse unchanged public seam. |
| Bounded delivery proof and delivery notification | `controlplane/delivery_proof.py::DeliveryProofSubscription` | Extend with verdict reads and run event wakeups. |
| Correlated claim identity and finalization | `controlplane/read_store.py::wire_delivery_claims`, `delivery_models.py::WireDeliveryClaim` | Reuse richer claim. Stop collapsing it to exchange ids for proof. |
| Failed receipt drift | `harnesses/drift_emitter.py::ActuationDriftObserver` | Reuse directly once the producer mints `harness_rejected_prompt`. |
| Claude durable native record | `index/tailer.py::TranscriptTailer._poll_cursor`, `index/adapters/claude.py::ClaudeAdapter`, `session/ingest.py::build_event` | Reuse Tier 1 record loop and raw event. Add one pure classifier. |
| Codex durable wire frame | `codex/transport.py::_message_artifact`, `storage/base.py::TransportArtifacts`, `storage/exchange_sink.py::emit_to_index` | Reuse `transport.json` representation and post persistence sink. Add one pure classifier. |
| Current run condition persistence | `live_status_observer.py::LiveStatusObserver`, `session/writer.py::submit_run_live_status` | Reuse sticky serialization with a distinct `model_rejected` kind. |
| Agent and director observation | `@tm/activity::runActivityProjection`, `ControlPlaneService.roster`, `WatchRuntime._record_activity_delta` | Extend existing state, structured payload, pull, and push surfaces. |
| Semantic selected model rejection detector | none found after searches for the four native signature fields across `api/src` and `packages` | Missing. Create one canonical classifier per native format and share the verdict producer. |

Count: 9 entries, 8 reusable capabilities, 1 missing semantic detector.

## Slice plan

### Slice 1: classify and persist one run verdict

* Add a shared internal model rejection result and stable `model_rejected` live kind.
* Add the pure Claude transcript classifier and one tailer hook after Tier 1 snapshot.
* Add the pure Codex wire classifier over post persistence transport messages.
* Add the observer method that writes one sticky live status row.
* Certify Codex `error` in the known event vocabulary with the supplied fixture.
* Add migration `0027`, Python and TypeScript vocabulary mirrors, and focused classifier, observer, migration, and drift tests.
* Construct the live verdict observer before starting `TranscriptTailer`. Current runtime order starts the tailer at `addon_runtime.py:512` and creates `LiveStatusObserver` at line 528.

### Slice 2: resolve prompted rejection

* Extend `ControlPlaneReadPort` with the narrow verdict read needed by proof.
* Preserve `WireDeliveryClaim.finalized` and add run event wakeups to the existing subscription.
* Make classified rejection win before success, while preserving duplicate and deadline outcomes.
* Return the existing stable `harness_rejected_prompt` reason. Let `ActuationDriftObserver` emit the existing launch contract drift.
* Add unit tests for early request, late rejection, accepted response, duplicate claims, deadline, unavailable reads, and replay stability.

### Slice 3: expose interactive verdict and reconcile contracts

* Add `needs-you-model-rejected` and `{kind: "model_rejected"}` to Activity.
* Extend the Activity machine, projections, fixtures, status tiers, Python mirrors, SSE payloads, roster `needs_you`, Watch, and MCP schema tests.
* Keep `whoami()` plus `roster()` as the agent query.
* Update the governing and runtime documents listed below.
* Run the four acceptance scenarios through the real launch and run read surfaces.

One PR can carry these three reviewable commits. Each slice has a closed test gate and deletes no active path.

## Failing test design

These four acceptance tests should fail on current `3ae57012824e` and pass after the slices:

1. Prompted Claude rejection. Launch with `first_prompt`, feed the supplied structured transcript record inside the proof deadline, assert the run was created and `first_prompt.status == "failed"`, reason `harness_rejected_prompt`.
2. Prompted Codex rejection from wire. Launch with `first_prompt`, feed the supplied `transport.json` server frame through the Codex transport finalization path, assert failed receipt and exchange identity. Also feed the misleading rollout `task_complete` and prove it cannot change the verdict.
3. Interactive rejection. Launch without `first_prompt`, assert launch returns with a live run, then parameterize the Claude and Codex native sources. Query `whoami()` plus `roster()` and assert `needs-you-model-rejected` with structured `model_rejected`. Assert Watch emits the matching needs you transition.
4. Surface and still spawn. For both harnesses, assert gateway creation and run identity occur before the rejection, no target preflight rejects the model, and a later supported turn clears the sticky verdict under the defined recovery rule.

Focused unit tests should cover exact positive signatures, near miss negatives, Codex transcript exclusion, Codex generic drift deduplication, proof ordering, notification catch up, database constraint round trip, Activity exhaustive transitions, roster serialization, and launch ledger replay.

Count: 4 acceptance scenarios plus focused unit coverage.

## Documentation changes

Required:

* `LAUNCH-CONTRACT.md`: define `harness_rejected_prompt`, rejection precedence within the proof deadline, and the post launch run observation for launches without `first_prompt`.
* `CONTROLPLANE.md`: change submission proof from a bare matching exchange, add `needs_you` to roster, and document `needs-you-model-rejected` for roster and Watch.
* `CONTROLPLANE-OBSERVATION-PLAN.md`: add model rejection to the needs you reason and run state tables.
* `RUNTIME-SURFACING-S2-PLAN.md`: close follow up item 3 with production classifier and receipt evidence. Keep session bootstrap item 2 open.
* `RUNTIME-SURFACING-PLAN.md`: add prompted and interactive provider rejection acceptance evidence to the runtime surfacing gate.

Review choice:

* `HARNESS-COMPATIBILITY.md` needs an update only if the two error shapes become revision certified compatibility promises. The recommended implementation certifies them beside the existing transcript and wire adapter revisions, so recording those signatures there would make drift review explicit.

## Risk and open decisions

The biggest blast radius is the closed run state vocabulary. One new kind crosses a database check constraint, Python literal and enum, TypeScript port, Activity event union and machine, public activity contract, Python mirror, roster, Watch, and migration head. Missing one member can reject the durable write or silently erase the public signal. Exhaustive mirror, migration, machine graph, and end to end tests are required.

The highest correctness risk inside that slice is premature `submitted`. Current proof seals on the outbound request before either supplied rejection source can arrive. The proof state machine must encode rejection precedence and test both event orders.

Recommended decisions for review:

1. Use `harness_rejected_prompt` for the receipt reason, `model_rejected` for the durable live kind and structured needs you kind, and `needs-you-model-rejected` for the Activity state.
2. Keep model rejection outside `PROVIDER_CONDITIONS` so authentication and usage remain runtime edge conditions and launch contract drift stays distinct.
3. Expose structured `needs_you` on roster. The unique state remains useful for filters and Watch.
4. Clear the sticky verdict only on a later genuine successful turn or run exit.
5. Treat the certified Codex `error` frame as known protocol vocabulary after semantic classification, preventing duplicate generic drift.

## Counts

* Reuse map: 9 entries, 8 reusable, 1 missing classifier.
* Slices: 3.
* Acceptance scenarios: 4.
* Primary blast radius risk: 1 closed vocabulary expansion, with premature receipt sealing as its critical ordering hazard.
