# S2 integration assumptions reconciliation

Date: 2026-07-23  
Spec: `~/.mdx/projects/tm-s2-claims-leases-spec-v1.md` §12  
Tree: `d7bfb9ac` (S1 + Space-CRUD + Canvas create/update)  
Method: read-only symbol checks against merged code. Prior scout: `tm-s2-integration-scout.md`.

Verdicts: **HOLD** (correct as written) / **ADJUST** (spec wrong or incomplete; real shape given) / **UNKNOWN**.

---

## Summary

| # | Assumption | Verdict |
|---|------------|---------|
| 1 | `ControlPlaneService.close` sole termination fanout | **HOLD** (with scope note) |
| 2 | `CaptureLeaseRegistry` / `prepare_capture` single capture-claim boundary | **ADJUST** |
| 3 | RunManager mint sites + pendingCreates; browser never supplies resourceId | **HOLD** |
| 4 | PlainTerminalSessions.open claim site + resolveCwd/spawn ordering | **ADJUST** |
| 5 | UPSERT_SESSION_SQL only session write path | **ADJUST** |
| 6 | resolve_launch_worktree → drop space_id entirely from claim | **ADJUST** |
| 7 | Session PK `session_id`; lock on it | **HOLD** |
| 8 | ProxyRunBinding + SharedProxyBindingPayload only proxy stamp carriers | **HOLD** (proxy plane) |
| 9 | dao_statements + RunManager must STEP 0 split | **ADJUST** |

**Totals: HOLD 4 · ADJUST 5 · UNKNOWN 0**

**#6:** Do **not** drop `space_id` from the claim/affinity stamp. Drop only the **Space membership authz check**.  
**#9:** `dao_statements.py` STEP 0 **not required** under UPSERT→function replacement. `RunManager.ts` STEP 0 **only if** claim mint/inventory land inline (~+40+ LOC); prefer support module without preemptive full-file split.

---

## 1. ControlPlaneService.close sole termination fanout

**Verdict: HOLD** (scoped correctly for S2 extraction)

Real surface:

- Multi-run control-plane fanout: **`ControlPlaneService.close`** (`controlplane/service.py`) — director-only, workspace-scoped known set, `asyncio.gather` of `_close_target` → `gateway.terminate_run`.
- Single-run primitives (not alternate multi-run fanouts):
  - `RunManagementPort.terminate_run` (`controlplane/activity.py`)
  - Gateway / `runtimeRouter` → `RunManager.terminate`
  - `RunManager.terminate` / `RunManager.close` (process-local settle)
  - `CaptureLeaseRegistry.close` / `release` (process capture lease, not CP fanout)

Spec §8 already says extract fanout from `close` and **reuse** `terminate_run` / `RunManager.terminate`. That matches the code: `close` is the only multi-target control-plane fanout worth extracting into `RunTerminationCoordinator`.

No second multi-run CP close path found.

---

## 2. CaptureLeaseRegistry / prepare_capture single capture-claim boundary

**Verdict: ADJUST**

Real registry seam (managed / gateway path):

```text
RunManager.createNew
  → capturePort.prepareCapture (CaptureRpcClient POST /v1/capture/prepare)
  → capture_rpc_routes.prepare_capture
  → CaptureLeaseRegistry.prepare_capture
       → prepare_captured_run (ports/proxy/home)
       → self._leases[run_id] = lease
       → self._facts[run_id] = _CaptureRunFacts(space_id, worktree_id, …)
       → emit RUN_STARTED
```

Symbols confirmed:

- `_CaptureRunFacts` — `capture_rpc.py`
- `CaptureLeaseRegistry._leases: dict[str, CaptureLeaseHandle]`
- `prepare_capture` is the **registry registration boundary** for HTTP capture

**Adjustment:** it is **not** the only call site of `prepare_captured_run`:

| Path | Uses CaptureLeaseRegistry? |
|------|----------------------------|
| HTTP `/v1/capture/prepare` → registry | **yes** |
| CLI `cli/_helpers._prepare_captured_run` → `prepare_captured_run` | **no** (bypasses registry) |

S2 claim-before-prepare for **canvas/managed runs** should hook at `CaptureLeaseRegistry.prepare_capture` (or immediately before it in the route after worktree resolve). CLI detached launches need an explicit decision (same claim API vs out of scope for S2).

Also: process `CapturedRunLease` ≠ durable `WorktreeLease` (scout false-friend).

---

## 3. RunManager identity-mint sites; browser never supplies resourceId

**Verdict: HOLD**

| Symbol | File | Role |
|--------|------|------|
| `createWithDisposition` | `packages/runtime/src/service/RunManager.ts` | Public create + idempotency |
| `createNew` | same | Actual prepareCapture + PTY spawn + register |
| `PendingCreate` | same | `{ fingerprint, promise: Promise<string /* runId */> }` |
| `pendingCreates` | `Map<string, PendingCreate>` keyed `${owner}\u0000${idempotencyKey}` | In-flight/completed create inventory |

`CreateManagedRunInput` / `PrepareCaptureInput` / `runtimeRouter` create body: **no `resourceId` field**. Browser/router only pass owner, harness, cwd, spaceId, worktreeId, etc. (`runtimeRouter.ts` create handler). HOLD: callers never supply `resourceId` today; S2 mints server-side.

---

## 4. PlainTerminalSessions.open terminal claim site

**Verdict: ADJUST**

Real shape (`packages/runtime/src/service/PlainTerminalSessions.ts`, 154 LOC):

```text
open(input):
  1. cwd = await resolveCwd(input.cwd)   # absolute / no ".." / real dir else fallback home
  2. session = await ptyPort.spawn({ argv, env, cwd, cols, rows })
  3. sessionId = randomUUID()
  4. register fanout + onData/onExit
```

- **No** claim, lease, or durable identity today (docstring: deliberately not a run).
- **No** cancellation checks today.
- Ordering is **`resolveCwd` then `PtyPort.spawn`** — correct place to insert claim **between** those two steps later.

**Adjustment:** do not describe “two cancellation checks” as present. They are S2 design inserts (check cancelled after claim / before spawn). Spec should say “insert claim + two cancel checks between resolveCwd and spawn.”

Also: plain terminal `sessionId` is a random UUID local to the gateway process; re-plan wants `resource_id` as that id — greenfield rebinding, not an existing field.

---

## 5. UPSERT_SESSION_SQL only session write path

**Verdict: ADJUST**

| Path | SQL / method | Production? |
|------|--------------|-------------|
| General session upsert | `UPSERT_SESSION_SQL` via `AsyncSessionDao.upsert_session` | **yes** — only prod caller is `SessionWriter._commit_batch` |
| Space stamp backfill | `UPDATE_SESSION_SPACE_IDENTITY_SQL` via `update_session_space_identity` | **yes** — `backfill_session_spaces` |

**Adjustments:**

1. **`build_session` is not a caller of upsert.** It only builds `SessionRow` from `SessionBinding`; `SessionWriter` performs the upsert.
2. **Second stamp write path exists:** `update_session_space_identity` force-overwrites `space_id`/`worktree_id` and **bypasses** any future `upsert_session_with_affinity` unless S2 retires or routes it through the same immutability rules.
3. Replacing `UPSERT_SESSION_SQL` covers the live tailer/ingest write path only after Writer is wired to the new DAO method.

---

## 6. [CRITICAL] resolve_launch_worktree → drop space_id from claim?

**Verdict: ADJUST**

Real `SpaceCrudService.resolve_launch_worktree(worktree_id, owner, space_id=None)`:

```text
stored = get_worktree(worktree_id, owner=owner)   # owner-scoped durable existence
if path is None → None
if space_id is None:
    default Space caller
    require worktree_in_space(default)             # always true for default/computed-all
else:
    get_space(space_id) must exist
    # does NOT call worktree_in_space for named Space
project + return ResolvedWorktree(space_id=resolved_space_id, …)
```

Launch missing guard remains in `launch_resolution.resolve_run_worktree` (`missing is not False`, lifecycle ACTIVE).

| Claim aspect | Drop? | Reason |
|--------------|-------|--------|
| Space **membership** authz check | **yes** | Placement is owner-scoped; default path already reduces to owner worktree existence |
| Durable affinity **`space_id` stamp** | **no** | Model of record D3 + same spec §5: canvas no longer implies Space; claim must stamp selected `SpaceRef` |
| Optional `space_id` arg on resolve | keep or ignore | When provided today it only validates Space existence and sets response context; not a membership gate |

**Correct rewrite of §12.6:**  
Claim authz collapses to **owner + worktree existence (+ canvas anchor check when canvas_id set)**. Reuse `resolve_run_worktree` for projected missing fail-closed. **Still stamp `space_id`** from the Director-selected Space (or default Space from resolve when omitted).

---

## 7. Session PK is session_id; function locks on it

**Verdict: HOLD**

- Mig 0001: `"session"(session_id text PRIMARY KEY)`.
- No competing natural key for the affinity function.
- Advisory lock keyed on `session_id` is the right serialization unit (no existing session upsert advisory lock today; greenfield inside the DB function).

---

## 8. Proxy stamp carriers

**Verdict: HOLD** (as scoped to the proxy plane)

Proxy-plane stamp carriers today:

- `shared_proxy.binding.ProxyRunBinding.space_id` / `worktree_id`
- `shared_proxy.models.SharedProxyBindingPayload.space_id` / `worktree_id`  
  (`binding_payload_from_binding`, addon `_runtime_binding_from_payload`)

No other shared-proxy types carry space/worktree stamps.

**Note (not a FAIL):** full affinity stamp threading still touches non-proxy carriers (`SessionBinding`, `SessionRow`, `_CaptureRunFacts`, `CapturedRunRequest`, `RuntimeRunView`, launch inputs). Spec §5 already lists SessionRow/SessionBinding separately; §12.8 is only about the proxy plane.

Canvas-stamp group is **greenfield** on both proxy types.

---

## 9. [CRITICAL] STEP 0 — do files actually cross 700?

Measured @ `d7bfb9ac`:

| File | LOC now | S2 delta estimate | Cross 700? | STEP 0 required? |
|------|---------|-------------------|------------|------------------|
| `session/dao_statements.py` | **677** | UPSERT body **101–137 = 37 lines** → replace with ~5–8 line function call (**≈ −30**); canvas stamp names in `SESSION_COLUMN_NAMES` **+~4–6**; optional conflict SQL if co-located **+15–30** | **Unlikely** if UPSERT body removed: 677−30+6 ≈ **653**; with conflict SQL co-located ≈ **670–680** | **No** (unless you keep old UPSERT body *and* add affinity SQL) |
| `packages/runtime/src/service/RunManager.ts` | **664** | Thread `resourceId` only: **+10–25** → ~675–689; inline claim mint + pending-inventory export: **+40–80** → **704–744** | **Conditional** | **Only if claim/inventory logic stays inline** — prefer `runManagerSupport.ts` / new `runtimeClaims.ts` for mint; then no mandatory pre-split of RunManager |

**Net verdicts:**

1. **`dao_statements.py`:** Spec’s fear of “will push over 700” is **wrong if** UPSERT is replaced by a short function call. STEP 0 split is **unnecessary** as a hard gate; optional extraction of affinity SQL remains fine hygiene.
2. **`RunManager.ts`:** Do not pre-split the whole file on assumption. Put resource identity + pending-inventory helpers in support modules; keep RunManager as the orchestrator. STEP 0 only if a measured patch would land >700 in-file.

`space/store.py` (693) remains **untouched** by S2 if claims live in `space/runtime_claims.py` (or similar) as the spec already plans.

---

## Spec edits recommended (for opus)

1. §12.2 / claim boundary: name `CaptureLeaseRegistry.prepare_capture` as managed path; note CLI `prepare_captured_run` bypass.
2. §12.4: remove implication that cancel checks exist; state insert points between `resolveCwd` and `spawn`.
3. §12.5: `build_session` is builder not upsert caller; call out `update_session_space_identity` as second stamp writer to retire or affinity-gate.
4. §12.6: **drop Space membership check, not space_id stamp**.
5. §1 / §12.9: mark dao_statements STEP 0 as **optional**; RunManager STEP 0 as **conditional on inline LOC**.

---

## One-line for orchestrator

**9 assumptions: 4 HOLD / 5 ADJUST / 0 UNKNOWN; #6 ADJUST (drop Space membership check only, keep space_id on affinity stamp); #9 dao_statements STEP 0 unnecessary under UPSERT→fn, RunManager STEP 0 only if claim mint stays inline; ~/.mdx/projects/tm-s2-reconciliation.md**
