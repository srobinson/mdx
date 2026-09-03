---
title: Transport Matters baseline provider deferral
type: design
tags: [transport-matters, baseline, verification, quota, retry]
summary: Recoverable provider refusals must leave baseline capture owed, with durable cooldown and automatic healing on a later launch.
status: draft
created: 2026-09-08
updated: 2026-09-08
project: transport-matters
confidence: medium
---

# Baseline provider deferral

## Status and provenance

Recovered from TM conversation `59c5f67b-6de1-4377-9f10-fb28ca0ef823`. Performance problems interrupted the original effort to save this analysis, first as a document and then as a cx entry. The conversation reader contains 12 messages and ends with a promise to try cx, without a successful persistence receipt.

The original tool evidence survives in that run's captured requests under `~/.transport-matters-preview/workspaces/dev-helioy-transport-matters/ecd9b0df/59c5f67b-6de1-4377-9f10-fb28ca0ef823/`. This document reconstructs the proposal from those findings. It is not a recovered verbatim final report or an approved implementation decision.

On 2026-09-08, the attempt record and central capture, reconciliation, queue, refusal, and resolver paths were read again against checkout HEAD `0c6a57559a1c6cc2487946b9c614517ebbc18fbb`. References below are repository relative. Some consumer references retain the original investigation's line numbers and may move with concurrent work. No production code or persisted attempt was changed.

## Problem and observed evidence

A provider refusing a controlled capture with HTTP 429 leaves a durable failed attempt. Future launches can submit verification work, but reconciliation treats the failed shape as settled. Subscription allowance can reset while the cell remains permanently unanswered.

The exact record remains at `~/.transport-matters-preview/baselines/attempts/claude/anthropic/fable/first-turn/2.1.263.json`:

```json
{
  "artifact_schema_version": 12,
  "harness": "claude",
  "provider": "anthropic",
  "launch_model": "fable",
  "request_shape": "first-turn",
  "effort": "low",
  "harness_version": "2.1.263",
  "status": "failed",
  "attempt_count": 3,
  "started_at": "2026-09-07T19:52:07.742119Z",
  "completed_at": "2026-09-07T19:52:11.132683Z",
  "failure_reason": "CapturedTurnError: the provider refused the turn for claude/fable/a1 with HTTP 429",
  "target_exclusion": null,
  "provenance_gap": null
}
```

The original investigation executed the actual `reconcile_verification_shape` function extracted through Python AST, supplying this real JSON and injected read dependencies. Every write dependency raised if reached. It observed `readiness=settled`, `attempt_count=3`, and no write boundary reached. This is a narrow deterministic reproduction of the reconciliation defect. It does not prove a live launch or provider reset.

The operator identifies this event as subscription usage exhaustion. The stored attempt proves HTTP 429 but contains neither response headers nor reset timing, so it cannot independently establish the exhaustion subtype.

## Current input to output chain

1. Launch admission determines whether the pinned release requires verification. Submission persists a `VerificationRequest`, including owner, executor, route, installed version, binary, release and required shapes. Admission does not start a provider attempt. See `api/src/transport_matters/launch_verification.py:195`.
2. The worker acquires the model's cell lock and reconciles each required shape before consulting the spend gate. Existing attributable evidence can be promoted and assessed without further provider work. See `launch_verification.py:303` and `launch_verification_reconciliation.py:47`.
3. The spend gate reads `VerificationQuotaDecision`, whose values are `unknown` and `usage_limit_reached`. It fails open on lookup errors and is consulted once before the first capture in that verification execution. A known limit ends that queue execution without spending. See `launch_verification.py:248`, `launch_verification.py:346`, and `launch_verification_support.py:30`.
4. `BaselineAttemptRecorder.start` runs on the client spawn callback. It creates the in progress record once per recorder, incrementing the previous count. Multiple probe spawns using the same recorder do not each increment it. The count is capture attempts, not a count of HTTP requests or billed tokens. See `launch_verification.py:397` and `baseline_attempts.py:245`, `baseline_attempts.py:320`.
5. Capture matches the delivery or its tool result request. A refusal on a matched exchange becomes `CapturedTurnError(provider_refusal=...)`. This matching boundary matters: an unrelated quota probe must not defer the controlled capture. See `captured_turn.py:355`.
6. `TransportRefusal` currently carries only status and optional message. HTTP refusal extraction reads the error stop reason; Codex frame extraction can also carry a message. Retry timing and the Anthropic retryability header do not reach this type. See `storage/base.py:305`.
7. Automatic capture catches every exception, records `FAILED` and a bounded diagnostic, and rethrows. It does not classify the structured refusal. Manual harvest already invokes `classify_provider_refusal` and persists a target exclusion when recognized. See `launch_verification.py:452`, `baseline_harvest.py:321`, and `baseline_attempts.py:374`.
8. The queue catches the exception and finishes the request with `failure_reason=capture_failed`. A later launch can enqueue work again, but reconciliation returns `settled` for a failed attempt at the installed version. The failure is therefore at shape eligibility, rather than an absolute inability to enqueue a request. See `launch_verification_queue.py:229` and `launch_verification_reconciliation.py:156`.
9. The resolver sees the failed attempt and projects unknown support with `capture_failed`, unless a recognized target exclusion supplies `provider_refused`. See `harnesses/resolver.py:541`.

Other reconciliation outcomes must retain their meaning: attributable evidence settles after local reuse; absent evidence with no attempt is due; a recent in progress attempt is pending; stale in progress work is recovered under the lock; a captured provenance gap settles because another paid capture would reproduce the attribution problem. See `launch_verification_reconciliation.py:47`, `:94`, `:105`, and `:107`.

## Consumers and change surface

### Attempt status and failure disposition

| Consumer | Responsibility and consequence |
| --- | --- |
| `baseline_attempts.py:32`, `:59`, `:83` | Closed status enum, durable JSON shape and lifecycle validation. A new field or status changes the persisted contract. |
| `baseline_attempts.py:245`, `:279`, `:320` | Start, finish and shared recorder. Own counting and atomic persistence. |
| `baseline_attempts.py:395`, `:426` | Permanent refusal classifier and account entitlement exclusion projection. Only recognized failed exclusions remove account targets. |
| `baseline_attempts.py:532` | One parser for legacy and current attempts. Already upgrades artifact versions, defaults request shape and reconstructs historical exclusions from diagnostics. |
| `launch_verification.py:452` | Automatic failure writer, currently missing refusal classification. |
| `baseline_harvest.py:321` | Manual failure writer, currently classifies permanent refusal. |
| `launch_verification_reconciliation.py:132`, `:156` | Orphan failure writer and terminal retry decision. |
| `harnesses/resolver_snapshots.py:135` | Loads attempts per cell and derives account exclusions for the resolver. |
| `harnesses/resolver.py:541` | Projects failed attempts into unknown support reasons. |
| `harnesses/inventory.py:231`, `:399`, `:553` | Discriminated baseline inventory states, serialization and attempt reads. The fallback branch currently assumes failed. |
| `baseline_publish_plan.py:123`, `baseline_publish.py:178` | Consume account exclusions when constructing publication cohorts. Temporary refusal must never remove a target from a cohort. |
| `www/packages/core/src/types/harnessInventory.ts:238` | TypeScript baseline inventory union, with in progress, failed and succeeded variants. |

Queue request failure is a separate contract. `launch_verification_queue_models.py` and `launch_verification_queue.py` carry their own `capture_failed` field; changing attempt interpretation alone does not remove a stale queue failure from resolver fallback. Unrelated run, delivery and exchange statuses named `failed` are outside this migration.

### Unknown support reason

The vocabulary owner is `support_state.py:85`, with a second closed validation set near `:126`. Consumers include `harnesses/resolver_models.py:240`, `harnesses/resolver.py:554`, `api/v1/harness_launch_view.py:71`, `:134`, `:164`, and `api/v1/harness_support_view.py:71`.

Cross language contracts include `shared/harness_inventory_vocabulary_v1.json:107` and `www/packages/core/src/types/harnessInventory.ts:73`. Canvas maps reasons to operator text in `www/packages/canvas/src/firstrun/harnessCards.ts:344`. Vocabulary tests live in `harnesses/test_inventory_vocabulary.py` and `www/packages/core/src/types/harnessInventory.test.ts`; Canvas fixtures and card tests must follow the changed contract.

Resolver precedence matters. Existing support evidence is resolved before missing evidence diagnostics. For missing shapes, active queue work currently wins, followed by derivation failure, in progress attempts, permanent refusal, capture failure, provenance gap, assessment missing, and queue failure fallback. A deferred shape must be handled explicitly before generic capture failure while genuine failures on other required shapes remain visible. See `harnesses/resolver.py:516`.

## Three structural choices

| Shape | Benefits | Costs and reset behavior |
| --- | --- | --- |
| A. Typed `provider_deferral` beside `target_exclusion`, retaining failed attempt lifecycle | Smallest status migration; keeps the fact that this attempt failed and makes future eligibility explicit; shares existing parser and recorder. | Every consumer equating failed with terminal must use the typed disposition. Strict old readers reject new fields unless the artifact version transition is handled. Reset eligibility comes from persisted timing, rather than failure status. |
| B. New `DEFERRED` attempt status | Retryable outcome is explicit in every status switch; avoids displaying ordinary capture failure for deferral. | Expands Python lifecycle validation, inventory discriminators, TypeScript unions and fixtures. Old enum readers reject it. Still requires reason, timing and migration, so the new status alone does not solve retries. |
| C. Route refusal exclusively onto the quota axis, with no failed capture record | A single account signal could prevent sibling models from spending against an exhausted subscription. | The existing quota axis is a projection of active run status, lacks reset timing and cannot represent generic 429 or 5xx. A physical attempt already began and needs an honest completed record. Hiding that failure loses accounting or leaves an orphan. A durable account quota store requires a broader identity and lifecycle design. |

Recommended starting shape: A, with one typed deferral and one shared classification path for manual and automatic capture. The completed attempt can remain historically failed while its retry disposition stays owed. The important invariant is that this failure never settles future capture eligibility. The UI reports deferral explicitly.

This is a proposed decision, not a conclusion recovered verbatim from the interrupted run. Choose B instead if the product requires deferred to be a first class baseline inventory status everywhere; carry its complete migration cost in the same change. C is unsuitable as the sole repair. Reuse the existing provider condition classifier for recognized exhaustion, and consider a durable account gate separately when ownership is established.

## Caller first implementation sketch

Conceptual data shape, subject to the existing module conventions:

```text
BaselineProviderDeferral
  reason: usage_limit_reached | rate_limited | provider_unavailable
  provider_status: integer
  retry_not_before: timezone aware timestamp
  timing_source: provider | fallback
  consecutive_deferrals: positive integer

BaselineCaptureAttempt
  provider_deferral: BaselineProviderDeferral | None
```

Use `rate_limited` for an unclassified 429; it must not assert a known subscription reset. Validate that deferral belongs only to a completed failed attempt, cannot coexist with target exclusion or provenance gap, and has coherent timing. Preserve the bounded diagnostic for troubleshooting.

Extend the existing `TransportRefusal` boundary to carry the selected response evidence needed for classification and timing. Do not create a second refusal type in each caller. Parse selected headers once at this boundary and reuse `classify_provider_response_status` for the known Anthropic condition. Do not persist entire response headers or introduce another provider pattern list for the same decision.

Both capture entry points should call a shared recorder failure operation with the exception and completion time. That operation classifies permanent exclusion or temporary deferral and writes the existing attempt. Put durable types and validation with the attempt model; put pure classification and retry timing in a cohesive module if adding it to the attempt module would exceed the 700 line ceiling. Search current helpers before adding any function.

Reconciliation needs to distinguish waiting for a provider cooldown from pending physical work. Introduce a typed cooldown readiness outcome if the current literal cannot express it clearly. The caller stops the current request without setting queue `capture_failed`; a later launch reconsiders eligibility. Existing lock contention and physical in progress work retain their queued behavior. No worker should sleep until a quota reset while holding a capture slot.

The operator reason should be `capture_deferred`, with the typed cause available as detail if the API exposes it. `quota_exhausted` alone overstates what generic 429 evidence proves. Only genuinely queued or running work receives `verification_pending` and a phase. A cooldown is not a running verification.

## Retry policy

Returning `due` on every launch without a time gate is insufficient. It can spend repeatedly while a subscription remains exhausted. Returning `False` from the worker is also insufficient: it places the request back on a queue scanned every 100 ms. See `launch_verification_queue.py:160`, `:185`, `:229`.

Proposed policy:

1. Persist a fixed `retry_not_before` when the refusal is observed. Repeated reads never move it forward.
2. Prefer validated provider timing from the matched response. Treat malformed timing as absent. Parse HTTP date and delay forms at one boundary with an injected clock; reject invalid or past values in favor of a short future fallback.
3. When timing is absent, use bounded exponential cooldown across consecutive deferrals: propose 60 seconds initially, doubling to a 15 minute ceiling. These are design defaults requiring product acceptance, not measured reset intervals. Persist the streak independently of lifetime attempt count, and reset it after successful capture.
4. Before the deadline, a launch performs local reconciliation and ends its verification request without another capture. At or after the deadline, the next eligible launch may retry under the existing cell lock and spend gate.
5. A repeated provider refusal completes the new attempt, advances its deferral streak and sets the next deadline. It does not enter an immediate retry loop. Successful capture writes the normal bundle and verdict and clears deferral through the normal replacement attempt.
6. Stop the remaining shapes in the current execution after a provider deferral. A later launch can resume the owed shapes. Attempt counts advance only when the existing client spawn boundary is crossed.

For this scope, automatic healing means healing on a later launch after cooldown. It does not promise a background capture exactly at reset time. If unattended recovery is required, add durable scheduled eligibility to the queue explicitly rather than abusing the current queued boolean.

For 5xx, propose deferral for recognized temporary service failures such as 500, 502, 503 and 504 with the same timing machinery. Do not classify every exception or every 5xx as temporary: protocol or implementation errors such as 501 need separate evidence. Keep timeouts and local setup failures outside this change unless separately specified and tested.

No HTTP 429 should permanently settle a verification cell solely because of its status or repeated occurrence. A provider's instruction not to retry immediately, including Anthropic's `x-should-retry: false`, does not prove a model will remain unavailable after an account allowance reset. Permanent exclusion requires independently recognized entitlement evidence.

## Existing quota signal and its limits

`GET_ACTIVE_USAGE_LIMIT_FOR_OWNER_SQL` requires an open live status generation, matching run start owner and harness, and no standing run exit. A closed or exited run's usage limit no longer answers the gate. `read_known_quota_decision` returns only an enum, with no reset timestamp. See `session/controlplane_statements.py:131` and `launch_verification_support.py:64`.

The shared provider classifier intentionally recognizes Anthropic 429 as `usage_limit_reached` only when `x-should-retry` is explicitly false. Its comments document a healthy Claude quota probe returning 429 with true, and explicitly acknowledge that the exhaustion marker lacks a certified real capture. Markerless or retryable 429 must therefore never synthesize account exhaustion. See `provider_conditions.py:32` and `:39`.

A capture should reuse that classification, but should not manufacture an unrelated active run status row to keep the gate closed. The capture's typed deferral can safely gate its own cell. Cross model account suppression requires a durable observation owned by the actual quota identity, with expiry and supersession rules, consumed by the same quota decision service.

That broader design must establish channel, executor or connection identity, route, authentication family and owner semantics from the real account model. The current harness plus owner query is not proof that every connection shares one subscription. A shared gate must not let one account's refusal suppress another account, or preserve a closed generation's limit forever. This remains an explicitly unverified boundary.

## Durable compatibility and migration

The attempt is strict Pydantic JSON (`extra=forbid`) and shares the baseline artifact version vocabulary. Adding an optional field is not automatically compatible with an old reader. The existing parser already supports historical versions and removes an obsolete top level `retry_after` field. Reintroducing that name without understanding the old migration would be unsafe. See `baseline_attempts.py:59`, `:111`, `:532`.

Use one parser migration path. Recognize a legacy failed provider refusal diagnostic only when it matches the known `CapturedTurnError: the provider refused the turn for ... with HTTP 429` grammar. An arbitrary exception merely mentioning 429 must remain unchanged. Prefer structured evidence whenever available. Preserve the recorded completion time, count and diagnostic; infer generic rate limiting without inventing a reset time or subscription subtype.

Derive legacy fallback eligibility from its original completion time, so every read does not restart the cooldown. The old fable failure is already well beyond the proposed fallback ceiling and becomes due on its next eligible launch. If the record explicitly contains `target_exclusion: null`, that must not disable deferral migration. Existing exclusion backfill has a missing key check that must not be copied blindly.

Read normalization can be pure. Persist the current format through the existing atomic writer on the next ordinary transition under the cell lock. Choose and test the artifact version increment through the central version owner; account for its effect on bundles and other consumers before implementation. Unsupported artifacts must not silently disappear in a way that triggers duplicate paid capture.

Do not delete fable's attempt or reset its count as the ordinary fix. Manual deletion loses evidence and accounting. A narrowly targeted backfill can be an operational alternative only if pure parser migration cannot represent the historical evidence, with dry run, atomic writes and idempotent selection. No such backfill or deletion was performed here.

Remove the duplicated manual failure classifier branch when both capture paths use the shared operation. Remove the blanket failed means settled interpretation for retryable provider evidence. Retain version adapters only as the single durable reader compatibility boundary, with documented ownership and the supported artifact versions as their removal condition. Do not keep a second legacy retry engine.

Mixed old and new backends writing the same channel need an explicit deployment compatibility decision. An old writer can replace a new attempt with the old schema and an old reader can reject new data. This proposal does not claim that concurrent mixed versions are safe.

## Verification plan

No implementation tests have been run for the proposed change because no implementation exists. The recovered AST reproduction proves only today's settled outcome. Implement in verifiable units, first showing the intended failure and then the passing behavior.

| Test home | Exact proof required |
| --- | --- |
| `test_baseline_attempts.py` | New deferral lifecycle validation; exclusion and deferral mutually exclusive; timezone checks; atomic round trip; fixed timing across repeated reads; count preserved across legacy normalization and incremented once at spawn. |
| `test_baseline_attempts.py` | Exact fable v12 fixture with explicit null exclusion becomes eligible after cooldown; unrelated text containing 429 does not migrate; known Codex HTTP 400 entitlement remains excluded and terminal; malformed and unsupported artifacts follow the declared compatibility policy. |
| `test_provider_conditions.py` | Preserve healthy Anthropic 429 true and missing marker negative cases; reuse explicit false classification; never translate bare status into proven account exhaustion. |
| Storage refusal tests and `test_captured_turn.py` | Matched refusal carries selected timing and condition evidence through transport extraction to `CapturedTurnError`; unrelated probe is ignored; delay/date timing parsing and invalid header behavior are deterministic. |
| `test_baseline_harvest.py` and `test_launch_verification.py` | Manual and automatic writers produce the same structured deferral or exclusion for the same exception; 429 aborts further probes and shapes; pre spawn failure never invents an attempt; successful retry writes normal evidence. |
| Reconciliation tests in `test_launch_verification.py` or a focused module | Frozen clock before, at and after deadline; no spend before eligibility; failed 429 becomes due after it; terminal 400 settles; evidence reuse and provenance gaps retain precedence. |
| `test_launch_verification_queue.py` | Deferral ends the request without `capture_failed`; many scan ticks do not call the provider again; a later launch after cooldown can enqueue and execute; restart retains persisted eligibility; two backends cannot capture the same cell concurrently. |
| `test_launch_verification_economics.py` and boundary tests | Reconciliation happens before quota; known active quota prevents spend; no count increment for admission, lock contention or cooldown; one physical worker retains its slot until exit on cancellation. |
| Resolver and inventory tests | Deferred missing shape reports unknown with `capture_deferred`; active work still has phase; generic queue failure does not mask deferral; true failure in another required shape remains visible; deferred models stay in picker and publication cohorts. |
| Python vocabulary, core TypeScript and Canvas tests | New reason agrees across JSON, Python and TypeScript; serialization parses; operator copy displays deferral; recognized permanent refusal retains its existing behavior. |

The strongest affordable integration proof is a deterministic controlled provider path: first return a matched 429 with known timing, inspect the exact durable attempt and launch view, relaunch before deadline and prove zero extra provider requests, advance the injected clock, return a valid capture, and inspect the persisted bundle plus derived support verdict. Include process restart and a sibling shape. Use the existing capture test dependencies and a controlled responder rather than spending a real exhausted subscription for the regression.

After focused checks pass, run the repository's required full Python gate from `api/justfile` and package owned TypeScript `typecheck` scripts for affected packages. Use the actual current command definitions when implementing. The original investigation noted several oversized implementation and test files; measure again and refactor before adding code to any file above 700 lines. Split functions over approximately 150 lines and keep new files under the file limit.

## Open boundaries

- The real fable response headers and the provider's reset timestamp were not verified. Its diagnostic alone cannot prove the quota subtype.
- Healthy quota probe handling is evidenced in the classifier; the classifier itself records uncertainty about the exhaustion header shape.
- No live post reset capture was attempted, and no current quota lookup was executed against Postgres during this recovery.
- Account scoped cross model suppression needs identity and expiry design beyond the cell retry repair.
- Backoff defaults, the new public reason and the selected durable shape remain proposed choices.
- Consumer searches should be rerun before implementation because this checkout is shared and code can move.
