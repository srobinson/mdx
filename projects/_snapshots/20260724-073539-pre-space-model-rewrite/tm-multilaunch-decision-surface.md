# `launch_batch` decision surface

Date: 2026-07-20  
Inputs: `tm-multilaunch-scout.md`, `LAUNCH-CONTRACT.md`  
Checkout: multi-launch worktree / scout head `8c51797e01ef`

Governing rule: one launch semantic. Batch is fanout over item launch, not a second path.

## REUSE

| Capability batch needs | Existing owner | Disposition | Reason |
| --- | --- | --- | --- |
| Item request and receipt | `run_models.py::LaunchRequest`, `LaunchResult` | Reuse | One request and one receipt per candidate; batch wraps them. |
| Public facade / dispatch mint | `service.py::ControlPlaneService.launch`, `_dispatch_id_factory` | Reuse | Thin `launch_batch` delegation only; keep orchestration out of the 666-line service. |
| Single item authority | `launch_service.py::ControlPlaneLauncher.launch` | Reuse | Every candidate must call this after candidate identity exists. |
| Canonical item intent | `launch_service.py::_NormalizedLaunchRequest`, `_normalize_launch_request`, `_intent_fingerprint` | Reuse | Batch identity must never replace item intent digests. |
| Item claim / replay ledger | `launch_ledger.py::LaunchLedger.claim`, `LaunchLedgerEntry` | Refactor-during | Contract key is `(owner, dispatch_id, candidate_key)`; today it is only `(owner, dispatch_id)`. |
| Per-target failure isolation shape | `service.py::ControlPlaneService.close`, `_close_target` | Reuse | Concurrent gather + per-target outcomes is the isolation precedent. |
| Gateway request projection | `run_models.py::GatewayCreateRunRequest`, `launch_service.py::ControlPlaneLauncher._execute` | Refactor-during | Thread candidate-scoped gateway `idempotency_key`; all other item fields stay. |
| Python→gateway adapter | `run_proxy.py::RunRouteProxy.create_run` | Reuse | Unchanged once each request carries a unique idempotency value. |
| Runtime create idempotency | `RunManager.ts::createWithDisposition`, `runManagerSupport.ts::createRunFingerprint` | Reuse | Proves candidate identity must reach Node; no batch logic inside RunManager. |
| Model / effort / connection resolution | `capture_rpc_routes.py::_resolve_launch_target`, `launch_target.py::resolve_launch_target_advisory`, `resolver_snapshots.py::resolver_snapshots_for_harness` | Reuse | Per candidate through the item path; no batch resolver. |
| REST launch skin | `controlplane_routes.py::launch` | Reuse | Thin `/launch-batch` sibling only. |
| MCP launch skin | `controlplane_mcp.py::_McpControlPlaneAdapter.launch`, `create_control_plane_mcp` | Reuse | Register `launch_batch` + adapter delegation; fanout stays in the batch service. |
| Cmd K command grammar / dispatch | `templateRows.ts::spawnCommand`, `commandTypes.ts::LauncherCommand`, `CanvasCommandDispatcher.ts::useCanvasCommandHandler` | Reuse | Add candidate selection + one commit command on existing grammar. |
| Palette single-run create path | `capturedRunStore.ts::CapturedRunState.ensureRun`, `transport.ts::createCapturedRunView` | Deviate | Direct `POST /v1/runs` bypasses control plane; do not loop N times here. One batch transport into the shared service. |
| Service run adoption | `capturedRunAdoption.ts::CapturedRunAdoptionReconciler`, `canvasActions.ts::adoptCapturedRun` | Reuse | Attach successful service runs; no second adoption mechanism. |

Reuse rows: **15**.

## MISSING-PRIMITIVES

Net-new code the scout marks unavoidable (none exist in runtime today; contract/plan only):

1. **`candidate_key` mint (server-owned)**  
   Deterministic internal UUIDs from batch dispatch + candidate ordinal. Clients never submit them.  
   **Contract mandates:** yes. Ledger key is `(owner, dispatch_id, candidate_key)`; single launch uses a fixed internal key. Without this, equal candidates collapse and unequal ones conflict at Node idempotency.

2. **`launch_batch` verb / batch service**  
   Models (`LaunchBatchRequest` / outcome / result), focused `launch_batch_service.py`, concurrency-bounded fanout, ordered outcomes, REST + MCP skins.  
   **Contract mandates:** yes as the batch entry shape. Must call item authority N times under one dispatch, not invent a second launch semantic.

3. **Sealed workspace snapshot (`WorkspaceSnapshot`)**  
   Seal once; optional isolation of writable candidate workspaces from that seal.  
   **Contract states it on `launch_batch`:** yes (contract: internal candidate key + one sealed workspace snapshot + optional evaluation artifacts). **Repo has zero substrate.** Scout treats real isolation vs live workdir as a human fork (below). Snapshot id without isolation is forbidden (false trust).

4. **Trusted Canvas / operator adapter into control plane** (implementation seam, not a contract primitive)  
   Origin-checked caller context so Cmd K enters the same batch service as MCP without forging agent grants or browser-supplied owner/workspace/candidate keys.  
   **Contract mandates:** not by name; required so palette does not create a second batch semantic under `/v1/runs`.

Evaluation artifacts (rubric, judge, labels, comparative views): **not missing for a foundation cut**; contract marks them optional; scout defers them in both v1 options.

## OPEN DECISIONS

### D1 — v1 scope: sealed snapshot vs thin batch verb (needs Stuart)

Contract sentence (public request / `launch_batch`): batch adds **internal candidate key**, **one sealed workspace snapshot**, and **optional evaluation artifacts**.

| Option | What ships | Contract posture |
| --- | --- | --- |
| **A — Contract-complete snapshot isolation** | Real `WorkspaceSnapshot`, seal once, isolated writable workspace per candidate; defer rubric/judge/labels/comparative views | Matches contract wording for snapshot; adds a 5th PR (seal, Git/non-Git, isolation, cleanup, fail-closed seal). Moves into S4-ish execution layer. |
| **B — Thin batch verb foundation** | Candidate identity, fanout, failure isolation, receipts, MCP, palette over **live workdir**; defer snapshot + all evaluation | Requires **narrow contract clarification** before merge: foundation may omit snapshot until a later slice. |

Scout recommendation alignment: evaluation above snapshot identity stays deferred either way (matches prior design lean of **DEFERRED-eval**). **Conflict is only on snapshot isolation in v1**, not on eval. Scout explicitly rejects a middle state (snapshot id/digest without isolated candidate workspaces).

**Ask:** choose **A** (real snapshot isolation in v1) or **B** (thin foundation + contract clarification that v1 is the batch verb without sealed workspaces).

### D2 — Blast-radius non-negotiables (disposition, not design fork)

Unless you override: candidate keys are **server-owned**; must reach both `LaunchLedger` and gateway `idempotency_key` before any fanout. No client-minted per-candidate `dispatch_id`. No palette `/v1/runs` batch loop.

### D3 — Contract open items touching batch (flag only)

From `LAUNCH-CONTRACT.md` open decisions: whether `brief_id` enters first public version or remains batch-only. Not blocking the D1 call, but do not silently invent brief semantics in the thin path.

---

**Decision requested:** D1 (A or B). Everything else is reuse/extend with server candidate identity as the hard gate.
