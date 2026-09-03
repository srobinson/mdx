---
title: Transport Matters manual baseline retry through harness refresh
type: design
tags: [transport-matters, baseline, verification, manual-retry, harness-refresh]
summary: Explicit harness refresh permits one normal verification retry of earlier 429 failures and preserves provider explanations.
status: draft
created: 2026-09-08
updated: 2026-09-08
project: transport-matters
issue: https://github.com/littleorgans/transport-matters/issues/653
---

# Retry refused baseline captures through explicit harness refresh

A captured provider 429 currently leaves a baseline shape permanently settled. An operator who knows their subscription allowance has reset should be able to run the existing harness refresh command, then launch the model again to retry verification. Refresh must preserve the failure evidence and use the existing verification queue.

This specification selects manual recovery. It replaces the earlier draft's automatic deferral, reset parsing and cooldown design. No implementation has been made.

## Product contract

1. A baseline capture receives a matched provider HTTP 429. TM retains its failed attempt and the provider's explanation. Ordinary launches do not repeatedly retry that failure.
2. After allowance resets, the operator invokes **Refresh harnesses** through Cmd+K, the harness screen, MCP `harnesses(refresh=true)`, or `transport-matters harnesses refresh preview` for the preview channel.
3. The shared manual refresh operation refreshes catalogs and authentication, and records permission to retry eligible failed captures that existed when the operation began. Refresh itself creates no provider capture jobs.
4. The next ordinary verification execution for the model may spend one verification attempt using that permission. Usually this follows the next launch. Work already queued by an earlier launch may also use the permission when it reaches the verifier; refresh does not interrupt or replace it.
5. Successful verification produces the normal bundle and support verdict. Another refusal records the new failed attempt and requires another explicit refresh. A failed retry cannot reuse the old permission.

The operator decides when to retry. Authentication refresh is not proof of restored allowance. Support continues to mean what the captured evidence proves.

## Verified defect and existing entry points

The preview attempt `baselines/attempts/claude/anthropic/fable/first-turn/2.1.263.json` has artifact version 12, status `failed`, count 3, and completion `2026-09-07T19:52:11.132683Z`. Its diagnostic is:

```text
CapturedTurnError: the provider refused the turn for claude/fable/a1 with HTTP 429
```

Both `target_exclusion` and `provenance_gap` are explicitly null. The original investigation ran the real reconciliation function with this JSON and read dependencies, made every write dependency fail if reached, and observed `settled` without reaching a write boundary. The file and central code paths were read again on 2026-09-08.

References below use repository HEAD `0c6a57559a1c6cc2487946b9c614517ebbc18fbb` as inspected. Recheck the symbols before implementation in this shared checkout.

| Path | Current behavior |
| --- | --- |
| [launch_verification_reconciliation.py:86](https://github.com/littleorgans/transport-matters/blob/0c6a57559a1c6cc2487946b9c614517ebbc18fbb/api/src/transport_matters/launch_verification_reconciliation.py#L86) | Reads the shape attempt; the final branch at line 156 logs manual retry required and returns settled for failed attempts. |
| [launch_verification.py:303](https://github.com/littleorgans/transport-matters/blob/0c6a57559a1c6cc2487946b9c614517ebbc18fbb/api/src/transport_matters/launch_verification.py#L303) | Owns the model lock, reconciliation before spending, and sequential required shapes. The exception path at line 452 writes every automatic failure without classifying provider refusal. |
| [baseline_harvest.py:321](https://github.com/littleorgans/transport-matters/blob/0c6a57559a1c6cc2487946b9c614517ebbc18fbb/api/src/transport_matters/baseline_harvest.py#L321) | Manual capture classifies the structured provider refusal before writing the attempt. |
| [baseline_attempts.py:320](https://github.com/littleorgans/transport-matters/blob/0c6a57559a1c6cc2487946b9c614517ebbc18fbb/api/src/transport_matters/baseline_attempts.py#L320) | Shared recorder starts once on client spawn, keeps attempt counts, and finishes through the atomic attempt writer. |
| [api/v1/harnesses.py:71](https://github.com/littleorgans/transport-matters/blob/0c6a57559a1c6cc2487946b9c614517ebbc18fbb/api/src/transport_matters/api/v1/harnesses.py#L71) | `run_harness_refresh` is the explicit refresh owner, shared by HTTP and MCP. It invokes `refresh(force=True)`. |
| [api/v1/controlplane_mcp.py:224](https://github.com/littleorgans/transport-matters/blob/0c6a57559a1c6cc2487946b9c614517ebbc18fbb/api/src/transport_matters/api/v1/controlplane_mcp.py#L224) | MCP `harnesses(refresh=true)` invokes that owner before projecting inventory. There is no separate callable MCP auth verify tool in the inspected contract. |
| [cli/harnesses_cmd.py:44](https://github.com/littleorgans/transport-matters/blob/0c6a57559a1c6cc2487946b9c614517ebbc18fbb/api/src/transport_matters/cli/harnesses_cmd.py#L44) | CLI refresh posts to the resolved channel's `/v1/harnesses/refresh`. |
| [FirstRunScreen.tsx:282](https://github.com/littleorgans/transport-matters/blob/0c6a57559a1c6cc2487946b9c614517ebbc18fbb/www/packages/canvas/src/firstrun/FirstRunScreen.tsx#L282) | Harness screen already posts to that route. Its separate access test creates a diagnostic captured run. |
| [templateRows.ts:153](https://github.com/littleorgans/transport-matters/blob/0c6a57559a1c6cc2487946b9c614517ebbc18fbb/www/packages/canvas/src/launcher/templateRows.ts#L153) | Cmd+K's existing Retry launch readiness effect only refetches readiness through `useLaunchReadiness`. It does not perform harness refresh. |

Background refresh also uses `force=True`, including version triggered enumeration. Therefore the retry side effect belongs in `run_harness_refresh`, never in `refresh_harness_state(force=True)` or the authentication observation writer. Startup verification and ordinary inventory reads must not issue retry permission.

## Preserve the provider explanation

Anthropic documents JSON errors with `error.type` and `error.message`. 429 can mean request or token rate limits, acceleration limits, a monthly API tier spend cap, or certain Claude Code workspace limits. The monthly spend cap response additionally documents `error.details.error_code = enforced_spend_limit_reached` and a reset date in the message. Claude Code also distinguishes subscription exhaustion from temporary throttling. Sources: [error format](https://platform.claude.com/docs/en/api/errors), [rate and spend limits](https://platform.claude.com/docs/en/api/rate-limits), [Claude Code errors](https://code.claude.com/docs/en/errors).

TM currently persists raw HTTP response bytes but `transport_refusal` extracts only the HTTP status from `ResStats.stop_reason`. Codex's recognized server refusal already preserves a message. See [storage/base.py:305](https://github.com/littleorgans/transport-matters/blob/0c6a57559a1c6cc2487946b9c614517ebbc18fbb/api/src/transport_matters/storage/base.py#L305), `exchange_recorder/__init__.py:279`, and `exchange_recorder/artifacts.py:108`.

Extend the existing HTTP refusal boundary to receive the matched recorded response body and populate the existing `TransportRefusal.message` from a valid Anthropic `error.message`. Keep the status when the body is absent, malformed, non JSON, or contains a non string message. Use the existing bounded diagnostic formatting and render message text as text. Do not copy a whole response body into an operator label or log. Read response bytes only on the refusal path; do not add another body read to every healthy exchange.

`captured_turn.py:_classify_run_exchanges` must continue establishing that the exchange belongs to the delivery or its tool result before classifying refusal. Claude's unrelated healthy quota probe returning 429 must never become a baseline failure. The current classifier's `x-should-retry` handling stays unchanged. This issue does not infer account exhaustion or reset timing from the header or message.

New and historical attempts keep their existing diagnostic representation. Add one strict reader for the controlled provider refusal diagnostic beside the existing attempt refusal logic. Match the known `CapturedTurnError: the provider refused the turn for <scenario> with HTTP <status>` grammar, validate its scenario against the attempt's harness and launch model, and permit the existing optional quoted provider message suffix. An unrelated exception or message merely containing 429 never qualifies. Reuse the parsed refusal with the existing permanent exclusion classifier; remove its separate broad status extraction path after migrating its supported historical fixtures.

Both automatic and manual capture must finish exceptions through one shared recorder operation. This repairs the current classifier divergence while preserving the existing Codex HTTP 400 entitlement exclusion. The live structured error and historical diagnostic must produce the same retry eligibility.

## Scope of manual retry

Only a completed failed controlled capture whose parsed provider refusal is HTTP 429 and has no target exclusion qualifies. The policy applies to the harnesses for which the recorded refusal actually proves 429; it does not guess in band statuses that current parsers do not recognize.

| Existing evidence | Explicit refresh result |
| --- | --- |
| Completed failed provider 429, including old fable v12 JSON | Eligible for manual retry permission. |
| Recognized permanent target exclusion, including Codex HTTP 400 entitlement | Preserved; refresh does not undo it. |
| Other 4xx, 5xx, local setup errors, timeouts, malformed diagnostics | No new retry permission in this issue. |
| In progress attempt or held model lock | Preserve running work; do not arm or interrupt it. |
| Successful evidence or a captured provenance gap | Preserve normal reuse and settlement. |
| Failure completed after the refresh's candidate snapshot | Requires a later explicit refresh. |

Refresh covers the answering channel and local executor, across installed harnesses and their observed current versions. It uses the same baseline root as the coordinator, including the existing fallback in `baseline_output(app)`. The storage root and local executor must be resolved once from the same channel; never combine preview storage with stable's executor ID.

Select failed models from retained attempt evidence, not catalog membership, so a missing picker row does not cause evidence deletion. A permission never restores a retired target or overrides launchability. Installed version changes are fenced by the version in the permission. Attempt records do not carry account identity; this feature grants a local operator retry at the existing verification cell scope and makes no account health claim.

## Selected durable shape

Use a small separate **manual retry permit** in the baseline store. Preserve the current attempt JSON, status enum, baseline artifact version and count. A permit is an instruction about future work; the attempt remains evidence of past work.

Compare the alternatives:

- Deleting or resetting the failed attempt makes it due but discards count and evidence, and cannot express an explicit override of a stale quota advisory.
- Adding a retry field to the attempt changes the strict durable schema, which currently shares its version with bundles. A new attempt status also expands every inventory discriminator.
- A permit tied to exact failure identities leaves those artifacts readable by old versions, survives restart and becomes stale when the underlying attempts change. Select this shape. It introduces no timer, reset calculation or scheduled retry worker.

Proposed owner: `launch_verification_retry.py`, using the existing attempt reader, `VerificationCell`, canonical digest helper, path escaping, atomic JSON writer, and model lock. If a current equivalent is found during implementation, extend it instead of introducing another store.

Conceptual contract:

```text
ManualVerificationRetry
  schema_version: 1
  executor_id
  harness, provider, model, installed_version
  failed_attempts: nonempty tuple of {request_shape, fingerprint}
  requested_at: timezone aware timestamp
  consumed_at: timezone aware timestamp or absent
```

Address one permit per executor, harness, provider, model and version under `baselines/verification-retries/`. All required shapes share the existing model lock. Do not put sidecar JSON inside the `attempts` directory, whose reader enumerates JSON as attempts.

A failure fingerprint uses stable parsed attempt facts: full attempt address including shape and version, count, start and completion times, and a digest of the bounded failure diagnostic. It excludes parser filled optional defaults and the artifact schema version so parsing a legacy record does not invalidate its identity. Reuse existing coordinate types rather than redeclaring them. A permit must not match a later failure just because it has the same HTTP status.

One reader determines whether an unconsumed permit still matches the current failed attempts. Missing, malformed, unsupported or mismatched permits authorize nothing and produce a bounded diagnostic when malformed. Eligibility never depends on elapsed time. Obsolete versions can be pruned when replaced through the same owner; consumed records may remain as the last manual retry receipt.

Conceptual public operations, with concrete types settled against the existing owners:

```text
snapshot_retry_candidates(output, executor, installed_versions)
arm_manual_retry(candidate_snapshot, requested_at)
read_matching_manual_retry(cell, current_attempts)
consume_manual_retry(permit, started_at)
```

Keep candidate selection and grant matching pure where possible. Arm and consume run under the existing model lock. This module owns permission only; it does not enqueue, harvest, parse transport bodies, or decide support verdicts.

## Explicit refresh transaction

1. Resolve channel, executor, baseline output and installed version observations. At entry to the serialized manual operation, snapshot exact completed 429 failure identities. Do this before waiting for the forced probe pass. A queued refresh must not retroactively select failures that happen after its own candidate snapshot.
2. Run the existing forced catalog and authentication refresh. Probe outcomes remain authoritative for what they actually observed. Per harness probe failures are already isolated and may be recorded without raising; do not claim a successful refresh means every probe authenticated successfully.
3. If the top level refresh operation raises, issue no new permits and return its existing typed error. Existing permits remain intact.
4. For each candidate model, acquire its existing lock without waiting for a long running capture. Reread attempts and the installed version. Arm only the exact failures still present and in scope. A held lock, changed version, changed failure, success or in progress record is skipped.
5. Write one permit per model atomically. Repeating refresh against the same unchanged failures and an outstanding permit converges without stacking permissions. A consumed permit may be replaced only by a new explicit refresh and a fresh candidate snapshot.
6. Persisting a permit can fail after the ordinary refresh updated some observations. Surface that failure through the existing refresh error mapping rather than reporting complete success. Per model atomic writes make repeating the command safe; partial permits do not authorize more than their own recorded failures.

Use off loop file operations for scans and locks. Do not hold a model lock while running authentication or enumeration probes. Multiple backends share the model file lock; the existing in process refresh mutex alone is insufficient for permit writes.

The HTTP response may retain its existing `{refreshed: true}` contract. MCP retains its inventory projection and CLI its normal exit behavior. Update descriptions and success text to state that earlier 429 captures can retry during normal verification. Log bounded counts for armed, already armed, busy and changed candidates. A busy candidate is not advertised as having received a permit.

## Verification execution and permit consumption

Read and validate the permit under the existing model lock. Reconcile all available local evidence first. Existing bundle promotion, support comparison and provenance gap settlement retain precedence and do not consume permission.

For required shapes named by a valid permit, the exact failed 429 becomes due. Failed shapes without permission keep their existing settled behavior. Shapes with no evidence remain normally due. Permanent exclusions are checked before manual permission. Do not weaken the generic failed branch for every failure.

The permit is one authorization for a model's next physical verification execution. It can cover its matching failed shapes and any normally due required shapes handled by that same sequential execution. It is not authorization to verify other models, reinterpret non 429 failures, or replace successful evidence.

Consume it once at the existing provider start boundary, alongside `BaselineAttemptRecorder.start`, when the first capture using that authorization reports client spawn. Keep the already validated set of authorized failure fingerprints in the running verifier for the remaining sequential shapes. This allows both required shapes to finish under one operator action while preventing another execution from reusing the durable permission. The first refusal or capture exception aborts the remaining shapes through existing behavior.

Before the callback, recheck that the permit is unconsumed and still matches under the held lock. Atomically persist its consumed time before recording the new attempt. If the permit write fails, abort the authorized verification before proceeding with further probe work. The client spawn callback is the existing accounting boundary, not proof that the provider received zero bytes before it; the integration test must respect that boundary. A new permit must never be inferred from an orphaned attempt.

Pre spawn preparation failure, lock contention, quota denial without permission, or local evidence reuse does not consume a permit. A crash after consuming but before the attempt write can conservatively require another explicit refresh. This is acceptable for manual recovery: preserve the consumed receipt, never invent a successful capture or silently retry indefinitely. A crash after attempt start follows existing orphan reconciliation policy; this issue does not redesign orphan recovery.

After the first spawn, attempt counts and completion continue through the existing recorder. `start_baseline_attempt` creates the new in progress record and naturally replaces the prior failure state. A second 429 has a new fingerprint and the consumed permit cannot authorize it. If some shapes succeeded before a later shape failed, retain their evidence; another refresh selects only the remaining qualifying failure.

Manual CLI harvest remains an explicit direct capture path. A later manual harvest that replaces one of the recorded failures invalidates that failure's permission. Grant validation must never let a stale permit override the new outcome. Do not add a second harvester or a second queue for refresh retries.

## Stale quota advisory

The existing quota query considers active, open `usage_limit_reached` run rows, with matching harness and owner, and excludes standing run exits. It has no reset timestamp. A live row can therefore remain a refusal advisory after the real subscription resets. See [controlplane_statements.py:131](https://github.com/littleorgans/transport-matters/blob/0c6a57559a1c6cc2487946b9c614517ebbc18fbb/api/src/transport_matters/session/controlplane_statements.py#L131) and [launch_verification.py:248](https://github.com/littleorgans/transport-matters/blob/0c6a57559a1c6cc2487946b9c614517ebbc18fbb/api/src/transport_matters/launch_verification.py#L248).

A valid manual retry permit allows that one model verification execution to proceed despite this advisory. Record that the operator override was used. Preserve ordinary quota checks for executions with no permit. Keep the existing `VerificationQuotaDecision` typed through the spend decision so the override can target `USAGE_LIMIT_REACHED` specifically; the current boolean boundary must not become a generic bypass for future denial reasons. Preserve its current fail open behavior for unavailable quota evidence. Do not clear or fabricate live status rows, change provider access observations, or claim quota is available. Installation, enablement, authentication, launch admission, route attribution, publisher reference selection, locks, concurrency slots and capture deadlines still apply.

The verifier must establish that at least one exact authorized failure remains among its required shapes before using this override. An orphan permit or a permit for a shape absent from the pinned release must not clear the spend gate. A current release with full attributable evidence consumes nothing. This avoids a permission for old work authorizing unrelated future work.

## UI, MCP and CLI

- Add an always discoverable **Refresh harnesses** command in Cmd+K's Agents scope, with search terms including auth, authentication, refresh and retry. Subtitle: **Refresh model and sign in status; allow another attempt for captures refused with 429.** The row must remain accessible when launch readiness is failing.
- Use the existing asynchronous command dispatch path so pending state and errors remain visible. Prevent duplicate submissions while pending. Refresh inventory and readiness queries after it completes.
- Extract the existing harness screen POST into one shared client operation and migrate the screen plus Cmd+K to it. Do not duplicate the request, error mapping or query invalidation in both callers.
- Keep **Retry launch readiness** as a read action; its current label promises prerequisite reevaluation and should not silently gain mutation semantics. Name the harness screen refresh consistently, replacing the vague **Safe Refresh** label where present.
- Use the existing `/v1/harnesses/refresh`, MCP `harnesses(refresh=true)`, and CLI refresh entry points. Update their documentation to include retry permission and lazy provider spending. Do not add a separate MCP retry tool or new HTTP route.
- Until verification actually runs, keep the failed attempt and `support_state=unknown`, `support_reason=capture_failed`. Refresh success text explains that a model launch can retry an earlier 429. Do not show queued or running merely because a permit exists.
- Display the bounded provider explanation where baseline failure detail is shown. This change does not add an operator supplied reset timestamp or new support reason vocabulary.

## Migration and compatibility

Existing failed 429 attempts become selectable by the shared strict diagnostic reader when explicit refresh is invoked. The exact fable v12 record with null exclusion must work without edits, deletion, archive moves or a backfill command. No automatic migration launches provider work.

Attempts, bundles, queue requests, reference artifacts and support reason vocabulary retain their schemas. The permit has its own small versioned JSON contract. Old backends ignore it and retain today's terminal behavior; they cannot corrupt an attempt by trying to parse a newly added field. A newer backend checks permit identity against current attempts every time, so an older writer replacing an attempt invalidates stale permission. A launch handled only by an old backend may still need another launch on an upgraded backend to recover. Do not claim uniform new behavior across mixed versions.

The existing attempt parser's supported versions and shape defaults stay intact. Refactor its historical refusal extraction into the one diagnostic reader and retain its existing recognized entitlement fixture behavior. In particular, `test_account_scoped_model_refusal_is_upgraded_from_the_current_attempt_schema` uses the older `CapturedTurnError: provider refused with HTTP 400: ...` diagnostic without a scenario. Support that exact legacy form for permanent exclusion reconstruction; require the scenario bound form for new manual 429 permission. Do not broaden 429 eligibility to every legacy diagnostic that happens to contain a status. Delete the duplicated manual failure classification branch once the shared recorder handles both entry points.

## Module and caller inventory

| Owner | Required change |
| --- | --- |
| `storage/base.py`, `captured_turn.py`, `storage/test_transport_refusal.py` | Preserve bounded Anthropic message on the matched HTTP refusal path; inventory every caller before extending the function signature. |
| `baseline_attempts.py`, `baseline_harvest.py`, `launch_verification.py` | One strict diagnostic reader and shared recorder failure operation for automatic/manual capture and historical records. |
| Proposed `launch_verification_retry.py` | Versioned manual permit, exact failure identity, candidate snapshot, atomic arm and consume under existing locks. |
| `api/v1/harnesses.py`, application wiring | Put permit issuance in the shared explicit refresh operation; resolve the answering channel and executor once. |
| `launch_verification_reconciliation.py`, `launch_verification.py` | Return due for matching authorized failures, keep a per execution authorization, consume once at provider start and scope quota override. |
| `api/v1/controlplane_mcp.py`, `cli/harnesses_cmd.py` | Retain shared route semantics; update descriptions, error behavior and documentation. |
| Shared frontend harness refresh client, `FirstRunScreen.tsx`, launcher rows/types/dispatcher | One refresh operation with observable progress and error, distinct from readiness reads. |
| `docs/HARNESS-COMPATIBILITY.md` and affected tests | Document manual recovery and preserve lazy verification, immutable evidence and accounting rules. |

No change is required to `UnknownSupportReason`, the baseline status discriminator, publication cohort rules, or the queue scheduling algorithm. Add no second transport refusal type. Keep mutations out of the resolver and inventory readers.

As inspected, the main touched production files are below 700 lines, but several are close: `FirstRunScreen.tsx` 640, inventory 617, attempts 588, resolver 566 and verifier 550. Measure again before editing. Refactor any file already over the hard limit before adding code and keep functions under approximately 150 lines.

## Acceptance tests

Write the narrow failing test before production edits. The first regression should prove the actual old fable failure stays settled today even after the current manual refresh, then prove a permit makes precisely that failure eligible.

| Check | What it must prove |
| --- | --- |
| Refusal extraction | Valid Anthropic JSON preserves its message; malformed, empty, absent and non string bodies preserve status without throwing; Codex server message behavior remains intact; unrelated quota probe is ignored. |
| Diagnostic compatibility | Exact fable v12 with explicit null exclusion qualifies; optional quoted messages qualify; wrong scenario, unrelated 429 text and other statuses do not. Existing legacy Codex entitlement fixtures retain their result. |
| Shared failure recorder | Identical automatic/manual exceptions yield identical diagnostics and exclusions. The 400 entitlement case still settles and stays excluded from publication cohorts. |
| Manual refresh surfaces | HTTP, MCP, CLI and both UI callers reach one owner. Explicit refresh arms the candidates; startup, version change, inventory reads and Cmd+K readiness rereads do not. |
| Snapshot boundary | Failure during the probe pass is not included. Changed version, changed attempt, in progress work and held lock are skipped. Top level refresh failure arms nothing new. |
| Permit persistence | Unconsumed permission survives process restart. Repeated refresh against unchanged outstanding permission does not stack retries. Malformed, mismatched and unsupported permit data grants nothing. |
| Physical execution | First provider spawn consumes once; multiple probe spawns do not increment the capture count repeatedly. Both required shapes can finish in one authorized execution. Failure aborts later shapes. |
| No premature spending | Refresh calls neither capture nor queue submission. Permission alone changes no support phase. Preparation failure and evidence reuse do not consume it. Existing queued work can use permission only through normal verifier entry. |
| Quota advisory | An active stale usage limit row cannot veto a valid manual retry; an execution without permission remains gated. No quota or access row is cleared or made available. |
| Stale grant fencing | New failure, manual harvest replacement, unrelated version, executor, model, shape or missing publisher shape cannot reuse old permission. |
| Concurrency and crash | Two backends compete under the existing model lock and at most one physical execution consumes a permit. Crash windows preserve evidence and consumed receipt; no extra retry is inferred. Existing orphan and cancellation tests still pass. |
| UI | Cmd+K refresh is discoverable when readiness fails, calls the shared mutation once, shows pending/failure, and invalidates inventory/readiness. Existing readiness retry remains read only. |

The decisive integration test uses the existing captured turn dependencies and a controlled provider responder: produce a matched 429 with a message; inspect the actual failed JSON and launch view; invoke refresh over HTTP or MCP; prove zero new provider requests from refresh; restart the backend; launch the model; keep a stale live usage row present; answer the authorized capture successfully; inspect the consumed permit, incremented attempt count, persisted bundle and resulting support verdict. Repeat with another 429 and prove ordinary launches cannot retry until another refresh. Run a second backend in the lock test.

Run focused owning suites, then the repository required full `just test` gate, whose package suites run serially, and `just --working-directory api ci`. Verify affected TypeScript with package owned `pnpm --filter @tm/core typecheck` and `pnpm --filter @tm/canvas typecheck`, plus the Canvas build. Use the shell package owning Vitest for the core and Canvas suites; do not invent an ad hoc TypeScript command. Rerun the existing queue, economics, provider access, vocabulary, publication exclusion and stale attempt recovery tests. The spec does not claim these implementation checks have passed.

## Boundaries and related work

The exact fable response message and reset headers have not been recovered; only its status diagnostic was verified. The extraction fix covers future captures and already retained raw responses when read, without pretending to reconstruct missing historic text.

Unattended recovery, provider reset parsers, cooldown/backoff policy, generalized 5xx retries, account wide quota state, permanent entitlement recovery and auth credential renewal are outside this issue. They are not prerequisites for this operator initiated recovery path.

Related contracts: [#633, lazy support verification](https://github.com/littleorgans/transport-matters/issues/633), [#399, provider access verification](https://github.com/littleorgans/transport-matters/issues/399), and [#470, retaining entitlement exclusions](https://github.com/littleorgans/transport-matters/issues/470).
