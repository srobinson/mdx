# launch_batch v1 implementation spec — architect review (opus)

Reviewer: `multi-launch:general:1:2.2` (opus). Read-only; verify build-readiness, no redesign.
Baseline: feat/multi-launch @ `8c51797e01ef`, tree pristine before and after.
Spec: `~/.mdx/projects/tm-multilaunch-spec-v1.md`. Authority: `LAUNCH-CONTRACT.md`.

## Verdict line

**review: clean.** No blocking issue. Reuse map is faithful, both weighted concerns are
real, locked decisions honored, migration safety internalizes the prior wipe burn. Three
non-blocking polish notes below. **I sign off on the v1 spec as build-ready.**

## 1. Reuse-map fidelity — PASS (49/49 verified against real code)

Every `file:symbol` in §7 and §8 binds to a real existing owner. No reinvention of an
existing helper/type/table/runner. Notable exact matches:

- `service.py` = 666 lines, `RunManager.ts` = 664 lines — matches §10 verbatim; the
  700-line-first-extract discipline is correctly pre-flagged.
- `CAPTURED_RUN_STORAGE_VERSION` = 7 (bump→8 correct); `CAPTURED_RUN_SPAWN_CONCURRENCY` = 5
  (matches §4.6 `concurrency=5`); `CANVAS_STORE_STORAGE_VERSION` = 1 (correctly NOT bumped).
- Latest migration = `0029_native_connection_origin`; `0030` slot free, 20 chars < 32.
- `createCanvasPersistOptions.migrate` = `() => emptyPersistedCanvasState()` — the
  blanket-reset hazard §6.2 warns against is REAL and correctly quarantined.

Three benign nuances (do not affect the spec's claims): `scoped_launch_workdir` is defined
in `launch_policy.py` and imported by `launch_service.py` (spec only says the launcher
*calls* it — correct); `ControlPlaneErrorCode` is a PEP695 `type` alias, so adding
`dispatch_conflict` is a literal-union edit, not an enum member; `CAPTURED_RUN_STORAGE_VERSION`
is a file-local const (bump in place, no export needed).

Independent ground-truth read of `run_models.py::LaunchRequest`: current fields are exactly
`workdir, harness(Literal["claude","codex"]), model?, effort?, agent?, name?, first_prompt?,
grant, dispatch_id?`. The §4.1 decomposition (`LaunchTargetIntent`→`LaunchItemIntent`→
`LaunchRequest`) **preserves every field with no drop and no type narrowing**; harness was
already a required `"claude"|"codex"` literal. The contract's larger `LaunchRequest`
(connection/brief_id/allow_unverified_target) is aspirational and not in the implemented
launcher, so mirroring the real surface is correct, not a regression.

## 2. Locked decisions — all three HONORED

- **(a) placement-free durable profile:** `LaunchProfileDefinition` (§4.3) carries no canvas
  field and validation explicitly forbids `canvas_id`/`canvas_ref`/`dispatch_id`/
  `candidate_key`/owner/workspace in the profile; `placements` is a separate invocation-time
  tuple on `LaunchBatchRequest` (§4.4). ✓
- **(b) hybrid canvas, not full B:** `canvas_id` threads create→`createWithDisposition`→
  `RuntimeRunView` (§4.7); §3.4 explicitly refuses `ManagedRunFilters.canvasId` in v1. ✓
- **(c) server candidate identity before fanout:** deterministic UUIDv5 keys computed for all
  candidates before the first task (§4.5), reaching the durable item key `(owner, dispatch_id,
  candidate_key)` and the gateway `idempotency_key` (§4.6 steps 7-9); browser posts one batch
  request, never loops `/v1/runs` (§2.4, §6/S6). ✓ Note: the process-resident `LaunchLedger`
  is *replaced* by Postgres `DurableLaunchStore` (reuse-map honestly labels this "Deviate"),
  which is the mechanism for the restart-replay fix — consistent with (c)'s intent.

## 3. Weighted concerns

### Restart-replay for process-resident RunManager runs — REAL, not hand-waved

The resolution is a genuine state machine, not a wish:
- Durable Postgres `control_plane_launch_item` keyed `(owner, dispatch_id, candidate_key)`
  replaces the process-resident ledger; states accepted/started/completed/failed/unknown.
- `started` is committed **immediately before** gateway create and never reverted (§5.3);
  a Postgres advisory lock on the full item key blocks a second live actuator.
- An item interrupted from `accepted` or `started` is sealed terminal `unknown`, the same
  dispatch cannot re-spawn, retry requires a new dispatch id (§3.2, §5.3).
- The honest boundary is documented (§10 "Gateway process lifetime"): a run that spawned in
  the **Node** gateway can outlive a **Python** API restart; the durable row is a
  creation-fact ledger, not a liveness record; the orphan is rediscovered via Activity while
  the seal prevents a duplicate spawn under the same key. Retry-with-new-dispatch may
  duplicate, and the spec owns that tradeoff explicitly.
This is the correct property for a process-resident runtime: **no double-spawn under a key;
liveness delegated to Activity/`getRun`.** Airtight for the property that matters.

### LAUNCH-CONTRACT.md sealed-workspace-snapshot — RECORDED as explicit deviation (adequate)

§3.1 folds it in as a versioned deviation: `workspace_snapshot_id` always null,
`workspace_basis: "live_worktree"` on receipts and UI, L2 blocked until real sealing exists,
and a **required pre-merge doc edit**: qualify the `LAUNCH-CONTRACT.md:launch_batch request`
snapshot sentence by version. The eval-fairness knock-on is surfaced (§3.1, §10). Matches my
design-review condition exactly.

### My 3 design-review conditions — all MET

1. Contract snapshot reconciliation → §3.1 (recorded deviation + mandated doc qualification). ✓
2. `canvas_ref` out of the durable profile → §4.3 (profile forbids it; placement is invocation-time). ✓
3. `dispatch_id` stated as batch-unit identity → §2.2 ("batch unit is `(owner, dispatch_id)`…
   Canvas identity does not define a batch"). ✓

## 4. Drill sub-question — SOUND and bound to the real data-flow

The spec chooses create-time affinity + Activity reconstruction over a query filter, correctly:
`ManagedRunFilters` only filters the **process-resident** `/runs` registry, so it cannot
restore affinity after a browser reconnect or serve MCP roster (§3.4). Instead `canvas_id` is
persisted in `run_lifecycle_event` (durable Postgres, survives restart even though the run does
not) → projected through `ActivityWireRun`/`runToWire` → filtered in
`capturedRunAdoption.candidateFromWire` by the active real Canvas UUID (§6.3 steps 1-5). All
three seams exist. This is the minimal-hybrid done right: a durable affinity fact, no premature
server query surface, drill served by the existing Activity stream. It is strictly stronger than
pure client-localStorage grouping (fresh/second client can reconstruct), which resolves the
multi-client concern from my design review.

## 5. Migration safety — PASS, notably rigorous

- **Server (0030):** nullable `canvas_id` on `run_lifecycle_event`, no FK, no backfill,
  existing rows null. New batch/item tables. Audit uniqueness → null-safe `(actor, verb,
  dispatch_id, candidate_key)`; single launch writes a **non-null** `SINGLE_LAUNCH_CANDIDATE_KEY`
  so no new null-candidate rows are created and NULL-distinct semantics stay safe. §10 requires
  null/candidate/rollback/duplicate/concurrent-writer tests and row preservation.
- **Client (v7→v8):** per-record sanitizer keeps valid v7 records, strips only malformed
  `canvasId`/records, "one malformed or dangling affinity never returns `{ runs: {} }` and never
  resets Canvas panes." The Slice-3 data-loss gate fixtures a **v7 (old) record + malformed v8
  + dangling canvas + panes + layout** and asserts only-invalid-skipped, layout-bytes-present —
  i.e. a persist-OLD-then-rehydrate test, not a lying fresh round-trip.
- **Explicitly does NOT bump** `CANVAS_STORE_STORAGE_VERSION` because its `migrate` is a blanket
  reset (verified) that would wipe pane layout; §6.3 dangling-canvas rehydrate skips one binding,
  retains all siblings, and a failed `fetchCanvases` inventory defers pruning (fail-safe).
This internalizes the repo's prior persist/rehydrate wipe burn correctly.

## 6. Slice plan buildability — PASS

Dependency order is correct: S1 durable identity+restart-replay (migration, `DurableLaunchStore`,
single-launch cutover) → S2 item authority + candidate chain (`LaunchCallerContext` refactor,
new `ControlPlaneLauncher.launch(caller,item,identity)`) → S3 canvas affinity end-to-end +
client v8 → S4 batch semantic core → S5 REST/MCP skins → S6 trusted browser adapter+transport →
S7 Cmd K composer. Each starts with named failing tests and ends on `just check` +
`just test-affected` (repo-recipe gates, not bare tsc/pytest). S2's `ControlPlaneLauncher.launch`
signature break is contained in-slice with the single-launch adapter and gated by
`test_single_launch_receipt_survives_caller_context_refactor`. No slice bundles an unrelated
contract change: S1's migration adds the nullable lifecycle `canvas_id` column while S3 wires its
consumers — one additive nullable column landing before its readers, which is correct, not a
split contract.

## 7. Non-blocking notes (fold at build time; none gate sign-off)

1. **`busy_gateway` public code (§3.2)** is not in the `LAUNCH-CONTRACT.md` failure-code table.
   Either add it to that table or reuse an existing code so the item-interruption seal does not
   introduce undocumented client vocabulary. Small contract-alignment.
2. **Slice 3 is the heaviest** (11 interface changes across Python + Node + browser + the client
   v8 migration). It is cohesive by concern (thread one affinity field end-to-end), so it need
   not split, but it is the highest-risk review surface; if it exceeds one review's capacity,
   the clean cut is server-affinity (lifecycle/Activity/roster) vs client-persistence (v8
   sanitizer/rehydrate).
3. **Cross-migration replay boundary:** a pre-0030 single-launch dispatch replayed post-migration
   is not in the new (initially empty) item store and would be treated as new; given the repo's
   pre-release flag-day posture this is fine, but state it as an explicit non-goal so no one
   expects pre-migration replay identity.

## Verification evidence

- 49/49 reuse-map symbols confirmed present (parallel Explore pass + direct reads).
- `run_models.py::LaunchRequest`/`LaunchResult`/`GatewayCreateRunRequest` read directly; §4.1/§4.7
  decomposition is additive and field-preserving.
- File sizes, storage versions, concurrency const, migration head, and the
  `createCanvasPersistOptions` blanket-reset all confirmed against source.
- Tree pristine at `8c51797e01ef` before and after review.
