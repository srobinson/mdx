# S3 Canvas create/update — large-context review + full gate (Grok)

Date: 2026-07-23  
Slice: S3 Canvas create + update (`~/.mdx/projects/tm-s3-canvas-crud-spec-v1.md`)  
Model of record: cm `019f8a57` (canvas anchors on `anchor_worktree_id`, never `space_id`)  
Range: `0905622d..50b35bf5`  
Commits: `544c0174` (STEP 0 refactor) + `50b35bf5` (Canvas create/update)  
Reviewer: `multi-launch:general:1:2.4` (read-only; large-context + authoritative local CI)  
Tree at review: idle at `50b35bf5`

## Verdict

**SHIP.** Whole-path coheres with the locked S3 spec and model of record. Full gate green; former Space-CRUD contract traps (private import + MCP allowlist) stay green with `canvas_create` / `canvas_update` registered.

| Severity | Count | Summary |
|----------|------:|---------|
| blocker | 0 | — |
| major | 0 | — |
| minor | 1 | `store.py` **693** LOC (7 under hard 700); split before S4–S6 store growth |

## Gate (authoritative, independent)

| Gate | Result | Evidence |
|------|--------|----------|
| `just check` | **PASS** | desktop 102; shell format/lint/typecheck; api ruff "All checks passed!" + mypy **681** files "Success" |
| `just test` | **PASS** | JS: desktop 102 + shell **1273** + common 24 + contract 8 + activity 288 (34 skip) + runtime 190 (2 skip) + gateway 21 = **1906** passed / **36** skipped. API: **3433 passed / 0 failed**. Combined **5339 passed / 36 skipped** |
| `just migration-smoke` | **PASS** | **9/9**; `alembic heads` = `0030_space_crud_reset` only; no migration files in range |

### Contract traps from prior slice (must stay green)

| Test | Result |
|------|--------|
| `test_private_import_boundary` | **PASSED** — MCP imports public `space_contracts` / models only; no private route symbols |
| `test_mcp_tool_schemas_are_the_agent_contract` | **PASSED** — allowlist includes `canvas_create` + `canvas_update` with required-field assertions |

## STEP 0 (behavior-preserving refactor)

Own commit `544c0174` before feature work:

| Extraction | Status |
|------------|--------|
| `space/authz.py` | `require_director`, `require_bound_space`, `display_name`, `rest_director_caller` |
| `space/space_mutations.py` | five Space-mutation bodies as free async functions |
| `SpaceCrudService` | thin public delegators retained |
| Import graph | `authz` ← {service, mutations}; mutations ← service; no cycles |
| `test_reshape_structure.py` | asserts module boundaries + five methods still exposed |

**LOC effect:** `service.py` **698 → 597** (headroom for S3). Feature commit lands Canvas in `canvas_commands.py` (215 LOC), not ballooning the facade.

Full suite green at `50b35bf5` is independent proof that STEP 0 did not regress prior Space-CRUD / read / launch behavior (suite includes all prior space tests + moved reconciliation tests).

## Large-context review vs §0–§10 + model 019f8a57

### §2–§4 Store / service / commands — match

| Contract | Present | Notes |
|----------|---------|-------|
| `insert_user_canvas` | reused | inherits parent anchor; kind user |
| `update_canvas` | new | CASE partial update; `kind='user'` predicate; roots return None |
| `list_canvases_by_anchor` | new | owner + anchor scoped |
| `canvas_ancestry` | new | recursive CTE with cycle guard |
| `create_canvas` / `update_canvas` | `canvas_commands.py` | Director-only; **no** `require_bound_space` (owner-scoped, anchor from parent) |
| Advisory lock | `store.lock_owner_scope` on `(owner, anchor)` | under transaction; re-load after lock |
| `Patch[T]` | `Absent` / `Present` | set / clear / omit for `default_worktree_id` |
| Response `CanvasRecord` | default Space stamp + `canvas_records` over anchor list | no second tree walker for mutation response |
| Repo contract guard | extended | `update_canvas`, `list_canvases_by_anchor` |

Cross-anchor reparent: service → `canvas_root_mismatch`; DB backstop `canvas_parent_fk` proven in store test. Cycle / depth use CTE + subtree height. Default worktree is owner-scoped (cross-anchor default allowed per spec).

### §5 Errors — match

No new codes. Existing map covers forbidden / not-found / invalid_request / root_locked / cycle / depth / root_mismatch. REST `model_fields_set` correctly distinguishes omit vs `null` for default clear.

### §6 REST — match

`POST /v1/canvases` 201, `PATCH /v1/canvases/{id}` 200, not nested under spaces, origin-guarded, camelCase bodies. Response is `CanvasRecord` via `response_payload` (neutral models leaf — no private mapper import).

### §7 MCP — match

`canvas_create` / `canvas_update` via `director=True` unbound caller; `CanvasGetResult` reuse; `_crud_id` parsing. Explicit comment: MCP `None` means omit (clear default via REST only) — matches tool signature and avoids private Patch encoding. Agent-contract allowlist updated with inputSchema checks.

### §8 `@tm/core` — match

`createCanvas` / `updateCanvas` + `UpdateCanvasPatch`; `requestApiJson` + `detailAware`; tests for method/path/body.

### §9 Migration — match

No migration in range; head stays `0030`; smoke 9/9.

### Model 019f8a57 coherence

- Canvas create/update never take `space_id`; anchor comes from parent Worktree.
- Named Space membership not involved (mutations owner-scoped).
- Roots remain service/reconcile-created; public create always `user` under a parent.
- `CanvasRecord.space_id` is response context only (default Space stamp).

### Drift / dup / leak scan

| Check | Result |
|-------|--------|
| Second membership path | none |
| Canvas mutations Space-bound | none |
| Private cross-adapter import | none |
| MCP allowlist freeze | updated |
| New error code | none |
| New migration | none |
| Parallel Canvas service | none — facade still `SpaceCrudService` |
| Detection writing canvas tree | unchanged reconcile; user tree mutations isolated |

### LOC / preemptive split

| File | LOC | Note |
|------|----:|------|
| `space/service.py` | **597** | Healthy after STEP 0 |
| `space/store.py` | **693** | **Minor:** 7 under hard 700; S4 delete + S5/S6 worktree ops will touch store — split primitives (e.g. canvas store helpers) **before** those slices |
| `space/test_service.py` | **675** | Near limit but Canvas cases moved to `test_canvas_commands.py` (394) + `test_reconciliation.py` (102); acceptable |
| `space/canvas_commands.py` | 215 | Under limits |
| `space/space_mutations.py` | 115 | Under limits |
| `space/authz.py` | 38 | leaf |

## Sign-off

Large-context: STEP 0 + S3 feature match the locked path end-to-end.  
Full gate: **PASS** (check + test 5339/36skip + migration-smoke 9/9 head=0030).  
Contract traps: private_import + mcp agent-contract **PASS** with canvas tools listed.  
Only follow-up: preemptive `store.py` split before S4–S6.
