---
title: Transport Matters issue 553 delivery claim design
type: design
tags: [transport-matters, issue-553, prompt-delivery, grok, correlation]
summary: One purpose-gated consume path for launch and live prompt delivery claims.
status: active
project: transport-matters
created: 2026-08-31
updated: 2026-08-31
---

## Problem

Grok can send housekeeping and agent-turn requests carrying the same prompt text. Managed launch correlation can persist the same delivery identity on both requests. Live prompt correlation consumes the identity on whichever matching request arrives first. The measured ordering puts housekeeping first, so the launch path reports duplicate requests while the live path silently names the wrong exchange.

The fix must select provider request purpose before consuming delivery state. Launch and live prompts then share one binding record, one claim path, and one receipt contract.

## Usage from the caller

The public launch and prompt APIs remain unchanged.

```python
launch = await launcher.launch(
    principal,
    workdir,
    "grok",
    first_prompt="Review the contracts.",
    dispatch_id=dispatch_id,
)
assert launch.first_prompt is not None
assert launch.first_prompt.status == "submitted"

receipt = await prompt_delivery.deliver(
    principal,
    launch.run_id,
    text="Continue.",
    delivery_id=delivery_id,
    mode="nudge",
    input_surface="composer",
)
assert receipt.status == "submitted"
```

For both calls, a request classified as housekeeping preserves the pending binding. The first eligible request consumes it. Missing purpose evidence remains eligible so protocol drift fails open.

Direct `captured_turn` correlation remains local. Its bounded artifact scan already checks provider purpose before matching the prompt digest.

## Shape

### Launch preparation

`captured.run.prepare_captured_run` arms `LivePromptDeliveryBindings` after `CapturedRunSpawnSpec` establishes the final storage directory and before any caller can spawn the provider client.

```python
def _arm_initial_prompt_delivery(
    request: CapturedRunRequest,
    *,
    storage_dir: Path,
    resource_stack: ExitStack,
) -> None:
    ...
```

The helper requires `initial_prompt` and `delivery_id` as a pair, arms the existing binding, and registers a UUID-scoped discard callback on the captured run resource stack.

### Claim selection

`WireStoreObserver` becomes the sole managed runtime claim owner.

```python
def _claim_bound_delivery_id(
    *,
    entry: IndexEntry,
    artifacts: ExchangeArtifacts,
    binding: ProxyRunBinding | None,
    outbound_request: InternalRequest,
) -> UUID | None:
    ...
```

The helper evaluates `ProviderAdapter.carries_agent_turn` against `outbound_request.metadata`, the same request object passed to `LivePromptDeliveryBindings.claim`. It uses `transport_request_header_lookups(artifacts.transport)`. A definite `False` returns without consuming. `True` and `None` may claim.

`LivePromptDeliveryBindings` remains provider agnostic. Provider names, headers, and request purpose do not enter its interface.

### Duplicate verdicts

The two readers share a reason and keep their own status vocabularies.

```python
# controlplane.delivery_models
DUPLICATE_PROVIDER_REQUESTS_REASON: Final = "duplicate_provider_requests"
```

`DeliveryProofSubscription` returns an in-memory `PromptReceipt(status="unknown")`. Multiple correlated requests cannot prove which request carried the prompt, which follows `docs/LAUNCH-CONTRACT.md`.

`DeliveryWaiter` writes a durable `ControlPlaneDeliveryRow(state="failed")`. `unknown` is not a `DeliveryState`, terminal ledger state, database value, or `WaitForReplyStatus`. A duplicate claim is unreachable after this fix, so the durable branch remains a defensive invariant failure. Leaving the row pending would hide corruption and make waits expire without a terminal explanation.

## Module map

| Module | Responsibility after the change |
| --- | --- |
| `controlplane.launch_service` | Freeze delivery identity and return the receipt. |
| `captured.run` | Arm the launch binding under the final run storage root and attach cleanup. |
| `controlplane.delivery_binding` | Atomically arm, discard, digest-match, and consume one pending delivery. |
| `api.v1.controlplane_gateway_input` | Keep existing live prompt arm and definite failure discard behavior. |
| `wire_store_observer` | Select request purpose and claim the sole managed binding. Both request kind and purpose read metadata from the same curated outbound request that claim consumes. |
| `adapters.base` and provider adapters | Decide whether a request carries the agent turn. |
| `controlplane.delivery_proof` | Interpret durable launch proof and return epistemic `unknown` for duplicate claims. |
| `controlplane.delivery_wait` | Reconcile durable prompt delivery and preserve `failed` for the unreachable duplicate ledger invariant. |
| `captured_turn` | Keep bounded local certification correlation. |

## Lifecycle

- Successful claim unlinks the binding. Later cleanup becomes a UUID-scoped no-op.
- Prepare failure closes the captured resources and discards an armed launch binding.
- Abandoned prepare, registry closure, and duplicate registration close the returned lease.
- Runtime spawn failure releases capture and closes the lease.
- Normal termination and registry shutdown close the lease.
- Definite live delivery failure keeps the existing explicit discard.
- Unknown live delivery outcome keeps the binding armed because the request may have reached the run.

The lifecycle regression must prove that preparation creates the binding and `lease.close()` removes an unclaimed binding.

## Forward deletion map

- Delete launch delivery fields from `captured.context._build_provider_invocation`.
- Delete the managed observer fallback to `extract_delivery_id(..., launch_fields=...)`.
- Replace duplicated reason literals with `delivery_models.DUPLICATE_PROVIDER_REQUESTS_REASON`; preserve each reader's domain status.
- Replace tests that defend managed launch field correlation with purpose-gated binding tests.
- Rewrite `codex.test_exchange_finalize_sink.test_codex_cold_launch_commits_delivery_before_prompt_response` against the binding so it still proves the outbound sink commits the claim before a response exists.
- Move delivery claim tests out of `test_wire_store_observer.py`, currently 673 lines, into a focused `test_wire_store_delivery_claim.py`; remove the migrated tests from the old file.
- Keep `launch_delivery_fields` and `extract_delivery_id` for `captured_turn` local correlation.
- Add no migration, backfill, compatibility reader, or preview reset code.

## Test contract

1. Launch ordering: housekeeping first, agent turn second. The binding survives housekeeping, one exchange claims the delivery, and `wire_exchange_id` names the agent turn.
2. Live prompt ordering: the same ordering and assertions.
3. Purpose boundary: `False` preserves, `True` consumes, and `None` consumes.
4. Retry: a later matching request cannot claim after successful consumption.
5. Lifecycle: paired launch preparation arms under `spawn_spec.storage_dir`; lease close discards.
6. Carrier deletion: managed launch fields retain workspace, affinity, lifecycle, provider access, and continuation facts while dropping delivery proof fields.
7. Contract: proof returns `unknown` and durable wait returns `failed`, both with `duplicate_provider_requests`.
8. Ordering: the Codex outbound sink still commits the delivery claim before the provider response exists.
9. Existing TypeScript pairing and prepare-before-spawn tests remain green. No Runtime contract changes are expected.

## Synthesis decision

Design B is the base. It evaluates purpose against the same curated outbound request that it may consume, keeps the public surface unchanged, and centralizes the duplicate reason while preserving each domain's status.

Grafts from design A:

- The complete cleanup matrix across prepare, cancellation, registration, spawn, termination, shutdown, live failure, unknown outcome, and successful claim.
- The focused lifecycle test under `captured/test_shared_lifecycle.py`.
- The managed launch field deletion assertion.
- Explicit `False`, `True`, and `None` observer tests.
- The rule that binding storage remains provider agnostic.

Partner correction round:

- Rejected the original shared status constant. Receipt proof and the durable delivery ledger use different closed vocabularies. They share only the reason.
- Added the Codex outbound sink ordering regression that also depended on the deleted fallback.
- Split new claim tests away from the 673-line `test_wire_store_observer.py`.
- Required `_request_kind` and claim purpose to read the same curated outbound metadata object.
- Added sanitized captured Grok header fixtures from client version 1.0.13 so the positive discriminator is grounded in measured traffic.

Rejected shapes:

- Provider purpose inside `LivePromptDeliveryBindings`, because it leaks transport evidence into the storage primitive.
- Launch-specific binding state, because it duplicates the existing record and lifecycle.
- Managed runtime fallback through launch fields, because it reintroduces repeated claims after consumption.
- Purpose repair in receipt readers, because the wrong exchange would already be persisted.
- Migration or compatibility code, because affected preview rows are development evidence and no reader contract depends on them.

## Tradeoffs accepted

- Missing purpose evidence remains eligible in exchange for preserving fail-open protocol behavior.
- One pending binding per run remains the internal shape in exchange for the existing serialized live prompt and single launch prompt contracts.
- `captured_turn` keeps local digest correlation in exchange for its bounded, purpose-first certification scan.
- An explicitly armed live prompt may replace an unresolved launch binding. Launch normally resolves proof before returning, and this slice does not add cross-service serialization for that unmeasured overlap.
- Proof and durable wait keep different statuses for duplicate claims in exchange for preserving both closed domain contracts without a migration.

## Open risks

- Observer fixtures must preserve the measured Grok header and ordering without timing dependence. Use sanitized fixture data grounded in tier-1 captures from Grok client 1.0.13 rather than reading an operator home during tests.
- The paired launch invariant should fail at capture preparation if a direct caller bypasses the RPC validator.
- New helpers must keep `captured/run.py`, `wire_store_observer.py`, and `delivery_wait.py` below repository file limits. New observer regressions belong in a separate focused test file because `test_wire_store_observer.py` is already 673 lines.

## Next implementation step

Write the housekeeping-first observer regressions for live and launch delivery, run them against the current implementation, and record the intended failures before changing production code.
