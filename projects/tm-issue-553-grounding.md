---
title: Transport Matters issue 553 grounding
type: projects
tags: [transport-matters, issue-553, launch, prompt-delivery, grok]
summary: Senior engineer ownership map for unifying launch and live prompt delivery claims in issue 553.
status: active
project: transport-matters
created: 2026-08-31
updated: 2026-08-31
---

## scope

Read only synthesis of `~/.mdx/TMP/pstack/tm553/ground-launch.md` and `~/.mdx/TMP/pstack/tm553/ground-observer.md`, reconciled against the live `transport-matters` tree at commit `1d199d1845666b2d14279d2664edca1598465fca`. No repository files were written. No tests were run by directive.

## ownership verdict

Issue 553 should converge on one consume once binding path.

- `api/src/transport_matters/controlplane/launch_service.py::LaunchService.launch` owns freezing the launch `delivery_id`.
- `api/src/transport_matters/captured/run.py::prepare_captured_run` owns the only safe arming point for launch because it has the final Tier 1 `storage_dir`, the proxy is live, and the provider client still has not spawned.
- `api/src/transport_matters/wire_store_observer.py::WireStoreObserver._submit_exchange` owns claim selection because it is the first common reader that has both the run binding and captured transport headers.
- `api/src/transport_matters/controlplane/delivery_proof.py::DeliveryProofSubscription._query` and `api/src/transport_matters/controlplane/delivery_wait.py::DeliveryWaiter._claim_deliveries` own receipt interpretation and must agree on the duplicate verdict.

## locked facts

- Duplicate correlated provider requests resolve to `unknown`, per `docs/LAUNCH-CONTRACT.md::Result, receipt, and prompt proof`.
- Request purpose gates claims with this rule: `False` skips claim, `True` allows claim, `None` fails open and allows claim. The contract lives in `api/src/transport_matters/adapters/base.py::ProviderAdapter.carries_agent_turn` and `api/src/transport_matters/storage/base.py::transport_request_header_lookups`.
- No migration or backfill belongs in the implementation.
- Preview reset is operator only and out of scope for application code.

## how the ownership splits

The core mistake today is split ownership. Launch first prompt proof starts as a frozen control plane UUID, live prompt proof uses a consume once file binding, and the observer still has a stateless launch fallback that does not know request purpose. Grok exposes the gap because one user turn can fan out into a housekeeping request and an agent turn that share host, path, model, and prompt text.

The clean shape is simple.

1. Launch and live prompt both arm `api/src/transport_matters/controlplane/delivery_binding.py::LivePromptDeliveryBindings`.
2. `WireStoreObserver._submit_exchange` asks the provider whether the request carries the agent turn before it consumes anything.
3. The stateless launch fallback leaves the runtime path and stays only where the reader owns a bounded local scan and already checks purpose first, which is `api/src/transport_matters/captured_turn.py::_wait_for_correlated_exchange`.
4. Receipt readers report the stored claim count consistently. One claim is `submitted`. More than one is `unknown`. Definite native submission failure is `failed`.

## caller first runtime trace: launch first prompt

1. `api/src/transport_matters/controlplane/launch_service.py::LaunchService.launch` normalizes the request, requires launch proof support when `first_prompt` exists, and freezes one `delivery_id` through the launch ledger.
2. `api/src/transport_matters/controlplane/launch_service.py::LaunchService._prepare` refuses a prompt launch without that frozen UUID and returns the paired `initial_prompt` plus `delivery_id`.
3. `api/src/transport_matters/controlplane/launch_service.py::LaunchService._execute` subscribes to delivery proof before run creation, then calls `api/src/transport_matters/api/v1/controlplane_gateway_runs.py::create_run`.
4. `packages/runtime/src/server/runtimeRouter.ts::registerRunRoutes` parses `initialPrompt` and `deliveryId`, applies provider access launch policy, and forwards the pair into `packages/runtime/src/service/RunManager.ts::RunManager.createWithDisposition`.
5. `packages/runtime/src/service/RunManager.ts::RunManager.createNew` calls `capturePort.prepareCapture` before any PTY spawn.
6. `packages/runtime/src/adapters/CaptureRpcClient.ts::prepareCaptureBody` serializes the pair, and `api/src/transport_matters/api/v1/capture_rpc_routes.py::PrepareCaptureRequest.paired_initial_prompt` validates that the pair is whole.
7. `api/src/transport_matters/capture_rpc.py::CaptureLeaseRegistry.prepare_capture` runs preparation, then registers the lease and facts with no await between successful prepare and registration.
8. `api/src/transport_matters/captured/run.py::prepare_captured_run` builds `CapturedRunSpawnSpec`. This is the arming seam. Arm `LivePromptDeliveryBindings` after `spawn_spec` exists and before `_persist_control_plane_grant` returns control to the caller.
9. Only after prepare returns does `packages/runtime/src/service/RunManager.ts::RunManager.createNew` spawn the provider client PTY.
10. When the first outbound request arrives, `api/src/transport_matters/wire_store_observer.py::WireStoreObserver._submit_exchange` should evaluate `get_adapter_for_provider(...).carries_agent_turn(...)` using `transport_request_header_lookups(artifacts.transport)`. `False` preserves the binding. `True` and `None` allow `LivePromptDeliveryBindings.claim`.
11. `api/src/transport_matters/session/writer.py::SessionWriter.submit_wire_exchange` persists the one accepted `delivery_id`, and `api/src/transport_matters/controlplane/delivery_proof.py::DeliveryProofSubscription.resolve` returns the launch receipt.

## caller first runtime trace: live prompt

1. `api/src/transport_matters/controlplane/prompt_delivery.py::VerifiedPromptDelivery.deliver` serializes delivery per owner and run, subscribes to proof, and calls `_deliver_untracked`.
2. `_deliver_untracked` sends the request through `api/src/transport_matters/api/v1/run_proxy.py::RunRouteProxy.deliver_input`, which reaches `api/src/transport_matters/api/v1/controlplane_gateway_input.py::deliver_input`.
3. `deliver_input` arms `LivePromptDeliveryBindings` through `api/src/transport_matters/capture_rpc.py::CaptureLeaseRegistry.arm_prompt_delivery` before it POSTs to the Gateway route.
4. If the Gateway returns a definite non 200 or a typed failed outcome, `deliver_input` discards the matching binding. If the POST result is transport unknown or the success payload is malformed, the binding stays armed because the input may have reached the run.
5. `WireStoreObserver._submit_exchange` should use the same purpose gate as launch before it claims the binding.
6. The writer persists the claim, and `DeliveryProofSubscription.resolve` or `DeliveryWaiter._claim_deliveries` reports the receipt from stored claims. No reader should recompute launch matching from prompt text after the write.

## why prepare_captured_run is the seam

`prepare_captured_run` is the first place where all of these are true at once.

- `CapturedRunSpawnSpec.storage_dir` is final.
- The capture proxy is already running and can observe the first request.
- Runtime has not called `RunManager.createNew -> ptyPort.spawn` yet.
- Direct headless capture has not called `run_captured_turn -> ProcessSupervisor.spawn` yet.
- The same prepared lease lifecycle already owns cleanup through `CapturedRunLease.close` and `CapturedRunResources.close`.

`CaptureLeaseRegistry.prepare_capture` is too narrow because direct `run_captured_turn` preparation bypasses it. `LaunchService` is too early because it does not own the resolved run storage. `_build_provider_invocation` is also too early and currently owns the carrier that needs to disappear.

## reuse map

| need | reuse | why this is the right owner |
| --- | --- | --- |
| Consume once correlation record | `api/src/transport_matters/controlplane/delivery_binding.py::LivePromptDeliveryBindings` | Already provides atomic arm, claim, UUID scoped discard, invalid payload cleanup, and prompt digest matching. |
| Launch arming seam | `api/src/transport_matters/captured/run.py::prepare_captured_run` | Owns final `storage_dir` and still precedes all provider client spawn paths. |
| Purpose discrimination | `api/src/transport_matters/adapters/base.py::ProviderAdapter.carries_agent_turn` | Existing provider contract. `None` already means fail open. |
| Header access | `api/src/transport_matters/storage/base.py::transport_request_header_lookups` | The observer already has transport artifacts and already uses this helper for Codex request kind. |
| Grok specific purpose signal | `api/src/transport_matters/grok/request_purpose.py::grok_carries_agent_turn` | Uses `x-grok-turn-idx`, which is the measured separator between housekeeping and numbered turns. |
| Local certification correlation | `api/src/transport_matters/captured_turn.py::_wait_for_correlated_exchange` | Already proves the desired ordering: purpose first, digest match second. |
| Duplicate receipt semantics | `api/src/transport_matters/controlplane/delivery_proof.py::DeliveryProofSubscription._query` | Already matches the launch contract for duplicate claims. |
| Cleanup hook | `api/src/transport_matters/captured/models.py::CapturedRunLease.close` via the existing resource stack in `prepare_captured_run` | The lease already closes on prepare failure, runtime spawn failure, run termination, direct turn cancellation, and registry shutdown. |

## quality map

| area | current state | required end state |
| --- | --- | --- |
| Duplicate receipt contract | `DeliveryProofSubscription` returns `unknown` for terminal duplicates, but `DeliveryWaiter` still finishes duplicates as `failed`. | Both readers return `unknown` with reason `duplicate_provider_requests`. |
| Launch versus live symmetry | Live prompt uses `LivePromptDeliveryBindings`. Launch still depends on runtime `launch_fields` plus `extract_delivery_id`. | Both launch and live prompt arm the same binding and claim through the same observer path. |
| Purpose before consume | `captured_turn` already does purpose first. `WireStoreObserver` still consumes before it knows whether the request is housekeeping. | `WireStoreObserver` mirrors `captured_turn`: skip on `False`, claim on `True` or `None`. |
| Cleanup coverage | Binding cleanup exists for successful claim, explicit discard, invalid payload, and replacement arm. There is no lease lifecycle cleanup for an unclaimed launch binding. | A lease owned discard callback removes stale launch bindings on every unconsumed exit path. |
| Runtime payload discipline | The delivery UUID is only correlation state. Launch profiles validate pairing and pass the prompt, not the UUID, into provider argv. | Keep the UUID out of provider argv. Keep it in the consume once binding only. |
| Storage compatibility | The issue concerns preview evidence rows, not a persisted contract readers depend on. | No migration, no backfill, no compatibility branch. |
| Operational cleanup | Old preview rows may still exist. | Reset or cleanup stays an operator action outside application code. |

## forward deletion map

| delete or change | forward reason | keep instead |
| --- | --- | --- |
| `api/src/transport_matters/captured/context.py::_build_provider_invocation` update that adds `launch_delivery_fields(request.initial_prompt, request.delivery_id)` into runtime `launch_fields` | Keeping it would let a later matching request reclaim after the binding is consumed. | Arm one binding in `prepare_captured_run`. |
| `api/src/transport_matters/wire_store_observer.py::WireStoreObserver._submit_exchange` fallback to `extract_delivery_id(..., launch_fields=binding.launch_fields)` for managed runtime launches | The fallback has no request purpose signal and is the direct path to the Grok duplicate. | Purpose gated `LivePromptDeliveryBindings.claim`. |
| `api/src/transport_matters/controlplane/delivery_wait.py::DeliveryWaiter._claim_deliveries` duplicate terminal result of `failed` | It contradicts `docs/LAUNCH-CONTRACT.md` and `DeliveryProofSubscription`. | `unknown` with reason `duplicate_provider_requests`. |
| Test expectations that pin launch fallback behavior, especially `api/src/transport_matters/test_wire_store_observer.py` launch field correlation coverage | Those tests defend the path that issue 553 needs removed from managed runtime launches. | Replace them with launch binding and housekeeping first regressions. |
| Any migration, backfill, or compatibility reader for preview rows | No live contract requires it. It adds risk to the wrong layer. | Operator reset only if cleanup is needed. |
| Any preview reset path in application code | Out of scope for the fix. | Operational reset outside the app. |

Keep `api/src/transport_matters/controlplane/envelope.py::launch_delivery_fields` and `::extract_delivery_id` for `captured_turn` and its bounded local scan. The helper is still useful when the reader owns a private artifact set and checks purpose first.

## focused test and gate commands

These are the narrow commands the implementation should drive first.

| purpose | exact command |
| --- | --- |
| Python regressions around binding, duplicate semantics, observer claim order, direct captured turn, and live prompt routing | `cd api && just test src/transport_matters/controlplane/test_delivery_binding.py src/transport_matters/controlplane/test_delivery_proof.py src/transport_matters/test_wire_store_observer.py src/transport_matters/test_captured_turn.py src/transport_matters/api/v1/test_run_proxy_controlplane.py api/tests/integration/test_controlplane_prompt.py api/tests/integration/test_controlplane_launch.py` |
| Runtime route and capture ordering regressions | `pnpm --filter @tm/runtime test -- src/server/runtimeRouter.test.ts src/service/RunManagerInitialPrompt.test.ts src/service/captureRpcLifecycle.test.ts src/service/RunManager.test.ts` |
| Focused Python quality gate after the code change | `cd api && just ci` |
| Focused TypeScript quality gate after the code change | `pnpm --filter @tm/runtime typecheck` |
| Final repository gate before merge | `just check` |
| Final repository test gate before merge | `just test` |

## recommended implementation shape

1. Arm launch bindings in `prepare_captured_run` immediately after `CapturedRunSpawnSpec` construction and register a matching UUID discard callback on the existing resource stack.
2. Remove launch delivery field carriage from managed runtime launch fields.
3. Teach `WireStoreObserver._submit_exchange` to evaluate provider purpose before claim and stop falling back to stateless launch field extraction for managed runtime launches.
4. Converge `DeliveryWaiter` duplicate semantics with `DeliveryProofSubscription` and the launch contract.
5. Keep `captured_turn` on its current local correlation path.

That shape reuses existing owners, deletes the duplicate path instead of layering over it, and keeps the fix inside the real boundary that has both transport evidence and final run storage.
