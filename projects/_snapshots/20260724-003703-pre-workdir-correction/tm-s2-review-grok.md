# S2 claims/leases — large-context review + full gate (Grok)

Date: 2026-07-23  
Slice: S2 atomic claims, leases, immutable session affinity  
Spec: `~/.mdx/projects/tm-s2-claims-leases-spec-v1.md`  
Model of record: cm `019f8a57`  
Range: `d7bfb9ac..7df0d907` (107 files, +5670 / −484)  
Commits: `668a6695` feat + `7df0d907` docs  
Reviewer: `multi-launch:general:1:2.4` (read-only; whole-path + authoritative local CI)  
Tree: idle at `7df0d907`  
Note: merge verdict is shared with opus/codex; **this gate result is the green/red authority**.

## Verdict

**SHIP on gate.** Whole-path coheres with the locked S2 contracts across Python claim store, capture prepare, Node RunManager/terminals, affinity upsert, and migration 0031. No blockers found that the full suite missed. Razor-thin LOC on `RunManager.ts` is the only standing hygiene flag for S4–S6.

| Severity | Count | Summary |
|----------|------:|---------|
| blocker | 0 | — |
| major | 0 | — |
| minor | 2 | `RunManager.ts` **695** LOC (5 under 700); `store.py` **693** still razor-thin (S4 STEP 0 still owns its split; S2 correctly left it alone) |

## Gate (authoritative, independent)

| Gate | Result | Evidence |
|------|--------|----------|
| `just check` | **PASS** | desktop 102; shell format/lint/typecheck; api ruff "All checks passed!" + mypy **691** "Success" |
| `just test` | **PASS** | JS: desktop 102 + shell **1274** + common 24 + contract 8 + activity 288 (34 skip) + runtime **204** (2 skip) + gateway 21 = **1921** passed / **36** skipped. API: **3456 passed / 0 failed**. Combined **5377 passed / 36 skipped** |
| `just migration-smoke` | **PASS** | **9/9**; `alembic heads` = **`0031_claim_affinity`** (down_revision `0030_space_crud_reset`); `test_runtime_claim_and_affinity_are_the_migration_head` passed in full suite |

### Contract traps (must stay green on 107-file slices)

| Test | Result |
|------|--------|
| `test_private_import_boundary` | **PASSED** |
| `test_mcp_tool_schemas_are_the_agent_contract` | **PASSED** (allowlist gains optional `canvas_id` on launch; no new MCP tool set that would freeze-break) |

## Large-context whole-path map

### Architecture shape vs §0–§9

| Spec contract | Implementation | Coherence |
|---------------|----------------|-----------|
| New modules (no mandatory STEP 0) | `space/runtime_claims.py` (660), `controlplane/run_termination.py` (143), `runtimeClaims.ts` (190), `runManagerSupport.ts`, `ResourceLeaseHeartbeat.ts`, `runSettlement.ts` | Bulk off existing files as directed |
| Mig 0031 claim/lease/affinity | `0031_runtime_claim_and_session_affinity.py` (517); head `0031_claim_affinity` | Present; destructive reset charter |
| Claim-before-prep | `RuntimeClaimStore.claim_resource`: lock worktree FOR UPDATE → `lock_owner_scope(anchor)` → canvas stamp → lease → pending claim | Order matches §4; no Space membership check |
| Fail-closed missing/inactive | `lifecycle_state` + projected `missing is not False` → `worktree_unavailable` | Matches D4 / launch_resolution |
| Affinity stamp includes `space_id` | `SessionAffinityStamp.space_id: SpaceRef` | D3: canvas does not imply Space |
| Prepare validates durable claim | `capture_rpc_routes._validate_durable_claim` before registry prepare | Stamp/resource/owner/worktree/canvas must match |
| Node mint + claim before prepare | `RunManager.createNew`: `claimManagedRun` → cancel check → prepareCapture with `resourceId` → bind → transition running | Browser never supplies `resourceId` |
| Plain terminal claim first | `PlainTerminalSessions.open`: claim → cancel checks/heartbeat → spawn; `sessionId` = `resourceId` | §9 / seam #4 |
| Pending inventory union | `runtimeClaims` union durable + pendingCreates + registered runs + plain terminals | Pre-gateway window covered for in-product paths |
| Affinity upsert | `UPSERT_SESSION_SQL` → `upsert_session_with_affinity(...)`; writer handles `affinity_conflict` | Single apply/replay/conflict authority |
| Backfill fill-when-absent | `UPDATE_SESSION_SPACE_IDENTITY_SQL` uses `COALESCE` + match guards | §5.1; does not overwrite claim stamps |
| Termination coordinator | `RunTerminationCoordinator` + `force_resources`; cancel_requested on lease | Substrate for advisory S4/S6 force-kill |
| CLI gap accepted | `cli/_helpers._prepare_captured_run` still calls `prepare_captured_run` directly | Matches §0.1; no false claim of inventory for CLI-detached |

### Cross-language contract (§9)

- `resourceId` required on prepare/claim surfaces; nullable `canvasId` threaded through launch skins (MCP agent-contract updated).
- Contract fixtures under `packages/contract` (`runtime-claim.json`, runtime index).
- Proxy carriers gain `affinityStamp` alongside space/worktree stamps.
- No compatibility decoder for pre-claim runs (greenfield).

### Drift / dup / leak scan (between domain and concurrency lenses)

| Risk | Finding |
|------|---------|
| Second session stamp writer fighting claim immutability | Mitigated: backfill is COALESCE fill-when-absent, not overwrite |
| Space membership reintroduced on claim | Not present; owner + worktree (+ canvas anchor) only |
| Capture process lease conflated with durable WorktreeLease | Separate: in-memory `CaptureLeaseRegistry._leases` vs `worktree_lifecycle_lease`; durable id bound into claim facts |
| Inventory gap before gateway for managed runs | Closed for in-product path via durable pending claim + `pendingCreates` union |
| Inventory gap for CLI-detached | **Known/accepted** §0.1 — not a ship blocker for S2 |
| Dual upsert SQL remaining | Production path routes through function; affinity conflict durable quarantine |
| New public HTTP error codes exploding agent freeze | Claim maps to existing `worktree_*` / internal claim codes; affinity conflict is ingest outcome, not HTTP client code (§10) |
| store.py growth | Untouched by S2 (claims live in `runtime_claims.py`) — correct |

### LOC / preemptive split

| File | LOC | Disposition |
|------|----:|-------------|
| `packages/runtime/src/service/RunManager.ts` | **695** | **Minor:** 5 under hard 700. Claim bulk correctly lives in `runtimeClaims.ts`; further S4/S6 wiring must stay out-of-file or extract first |
| `api/.../space/store.py` | **693** | **Minor (carry-forward):** S2 did not grow it; S4 STEP 0 still owns the split before canvas delete primitives |
| `session/dao_statements.py` | **660** | Net-down under UPSERT→function as predicted |
| `controlplane/service.py` | **612** | Shrank after termination extract |
| `space/runtime_claims.py` | **660** | Under 700 |

## Tests coverage signal (not a second gate)

Co-located suites present and green in the full run: `test_runtime_claims.py` (336), `test_session_affinity.py` (248), `test_runtime_claim_migration.py`, runtime claim routes, RunManager claim/idempotency, PlainTerminalSessions claim tests, contract fixtures.

## Sign-off

Large-context: path from mint → claim+lease → prepare/bind → stamp upsert → terminate/force-release is one coherent substrate matching the finalized S2 spec and model 019f8a57.  
Full gate: **PASS** (check + test **5377**/**36skip** + migration-smoke **9/9** head **`0031_claim_affinity`**).  
Contract traps: private_import + mcp agent-contract **PASS**.  
Follow-ups (non-blocking): keep `RunManager.ts` from absorbing S4/S6 logic; execute store split as S4 STEP 0; later thread CLI-detached claim path (§0.1).
