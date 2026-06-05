# S1 review synthesis — Canvas+Worktree CRUD (PR #316)

Date: 2026-07-22  
Head reviewed: `25f20382`  
Sources:
- `tm-canvas-crud-s1-review-opus.md` (0 blk, 1 maj, 3 min)
- `tm-canvas-crud-s1-review-gpt.md` (1 blk, 6 maj, 4 min)
- `tm-canvas-crud-s1-review-grok.md` (clean + local gate green)
Authority: `tm-canvas-worktree-crud-spec-v1.md` §15 Slice 1 + contract invariants  
Classification: **[IMPL]** fix against existing spec · **[DESIGN]** needs owner decision (spec/DDL gap or locked-decision conflict)

Dupes collapsed: **15 formal findings (opus+gpt) → 14 unique** (1 shared major: pair-delete DDL; private-store appears as opus minor + grok suggestion only).

---

## BLOCKER

### B1 — Frontend e2e gate red at head
| | |
| --- | --- |
| Severity | **blocker** |
| Class | **[IMPL]** |
| Families | gpt |
| Defect | Production disables persistence until a durable Canvas UUID; browser e2e fixtures still open bare `/canvas` and seed retired `transport-matters-canvas:direct-local` / legacy import paths, so the required frontend e2e job fails (10 failed / 14 passed on the reviewed head). |
| file:symbol | `www/packages/shell/tests/e2e/canvas-drop-ux.spec.ts`; `www/packages/shell/tests/e2e/canvas-persistence.spec.ts` (legacy import case); production: `route.defaultCanvasId`, `canvasStoreLifecycle` / `createCanvasCacheStorage` |
| Fix disposition | Give every affected fixture a valid durable Canvas UUID and matching namespaced cache key; delete the obsolete legacy-import assertion; re-run e2e to green. Do not reintroduce cache migration or synthetic keys (spec: no compat path). |

Note: grok's local `just check` / `just test` / migration-smoke were green and did not treat remote frontend e2e as blocking; gpt's required gate includes that job.

---

## MAJOR

### M1 — Worktree+root pair deletion is impossible under 0030 DDL
| | |
| --- | --- |
| Severity | **major** (latent for S6; baked into S1 “final schema”) |
| Class | **[DESIGN]** |
| Families | opus (M1), gpt (M5), grok (suggestion #4) |
| Defect | Spec §11 finalization deletes Worktree + protected root (+ cascade) in one txn, but 0030 creates a deadlock: `space_worktree_root_canvas_fk` **ON DELETE RESTRICT** fires immediately (RESTRICT is not deferrable in practice); Worktree-first delete **SET NULL**s root `default_worktree_id` via `canvas_default_worktree_fk`, which immediately violates `canvas_kind_shape_ck` (`worktree_root` requires nonnull default). No pair-delete test exists. |
| file:symbol | `0030_space_crud_reset` (`space_worktree_root_canvas_fk`, `canvas_default_worktree_fk`, `canvas_kind_shape_ck`); proven by `test_space_crud_migration.test_root_delete_is_restricted_immediately_even_when_constraint_is_deferred` |
| Fix disposition | **Owner decision before coding:** revise the cyclic delete design (opus proposal: root FK → `ON DELETE NO ACTION DEFERRABLE INITIALLY DEFERRED`, delete root first then Worktree so SET NULL never hits a surviving root CHECK; or alternate adjudicated order/constraints). Edit 0030 while still free; add pair-delete + direct-root-still-blocked tests. Leaving this to S6 forces another reset and breaks “S1 installs final schema.” |

### M2 — Observer `refresh` performs detection mutation
| | |
| --- | --- |
| Severity | **major** |
| Class | **[IMPL]** |
| Families | gpt (M1) |
| Defect | `list_worktrees(refresh=True)` runs `reconcile_detection` for any `CrudCaller`, including Observer MCP and origin-unchecked REST GET. That inserts Worktrees/roots and updates path/branch/HEAD/missing — a write under a read surface, violating “Observers read; Directors mutate.” |
| file:symbol | `space.service.SpaceCrudService.list_worktrees`; `api.v1.space_mcp` worktree_list; `api.v1.space_routes.list_space_worktrees` |
| Fix disposition | Split read list from reconciliation. Require Director (and REST origin-guarded mutation route) for reconcile; Observer gets refresh=false / read-only inventory only. |

### M3 — Browser accepts non-UUID Canvas strings as identity
| | |
| --- | --- |
| Severity | **major** |
| Class | **[IMPL]** |
| Families | gpt (M2) |
| Defect | Route parser trims `canvas_id` without UUID validation; `defaultCanvasId` returns the string; store/cache keys activate before server validation (tests still codify `canvas-9`). Spec: durable Canvas UUIDs only on routes and client keys. |
| file:symbol | `www/packages/canvas/src/route.ts` (`defaultCanvasId` / query parse); `canvasStoreLifecycle` |
| Fix disposition | Validate UUID syntax at the route boundary; activate persistence only for a server-consistent Space/Worktree/Canvas tuple; reject mismatched or non-UUID IDs. |

### M4 — Plain/missing Worktree cannot later reconcile as a Git Worktree
| | |
| --- | --- |
| Severity | **major** |
| Class | **[DESIGN]** |
| Families | gpt (M3) |
| Defect | On workspace-identity conflict, `_upsert_worktree` can move a row to a newly claimed Git Space while keeping the old protected root; `_ensure_worktree_root` then refuses because the Canvas still belongs to the plain Space. Sequence: materialize missing path → `git init` / claim repo → reconcile fails and rolls back. Spec does not define this identity transition. |
| file:symbol | `space.store.SpaceStore._upsert_worktree`; `SpaceStore._ensure_worktree_root` |
| Fix disposition | **Owner decision:** either move the protected root with the Worktree in one atomic transition, or keep the original Space and reject Git re-claim — then implement the chosen rule and test both transition cases. |

### M5 — Deferred root FK does not enforce the full Worktree↔root pair
| | |
| --- | --- |
| Severity | **major** |
| Class | **[IMPL]** |
| Families | gpt (M4) |
| Defect | FK checks owner/space/canvas id only. DB accepted a user Canvas as `root_canvas_id` and accepted two protected roots with swapped `default_worktree_id`. Service currently creates correct pairs; durable contract is not DB-enforced. Spec §6.1 requires the bidirectional pair. |
| file:symbol | `0030_space_crud_reset` (`space_worktree_root_canvas_fk`, `canvas_kind_shape_ck`) |
| Fix disposition | Add deferred DB mechanism(s) so `root_canvas_id` must reference a `worktree_root` whose `default_worktree_id` equals that Worktree; tests for user-as-root, swapped roots, mismatched defaults. If pure DDL cannot express it, escalate to owner ([DESIGN] fallback). |

### M6 — REST vs MCP JSON field naming diverge
| | |
| --- | --- |
| Severity | **major** |
| Class | **[IMPL]** |
| Families | gpt (M6) |
| Defect | REST uses camelCase aliases (`canvasId`, …); MCP `model_dump()` without `by_alias=True` emits snake_case. Spec: TS mirrors camelCase JSON; surfaces should share one result contract. MCP tests lock the divergent shape. |
| file:symbol | `api.v1.mcp_tooling` (`mcp_tool_result` / dump path); `api.v1.test_space_mcp` |
| Fix disposition | Serialize MCP results with aliases; add REST/MCP parity assertions on successful payloads (not only errors). |

---

## MINOR

### m1 — Canvas names lack 120-scalar / trim invariant
| | |
| --- | --- |
| Severity | minor · **[IMPL]** |
| Families | gpt (m1) |
| Defect | `Canvas.name` unconstrained; root name derivation from branch/path/slug skips trim and 120 Unicode scalar cap (spec §4.1). |
| file:symbol | `space.models.Canvas`; `space.store` root name helper |
| Fix disposition | One shared name validator for roots and future user mutations; optional DB check. |

### m2 — Snapshot reads can mix committed generations
| | |
| --- | --- |
| Severity | minor · **[IMPL]** |
| Families | gpt (m2) |
| Defect | `get_space_snapshot` uses separate statements under READ COMMITTED; concurrent reconcile can return a root without its Worktree (or reverse) in one response. |
| file:symbol | `space.store.SpaceStore.get_space_snapshot` |
| Fix disposition | Single-statement projection or isolation that yields one consistent pair snapshot. |

### m3 — Canvas load/error collapsed to empty tree in CMDK
| | |
| --- | --- |
| Severity | minor · **[IMPL]** |
| Families | gpt (m3) |
| Defect | `useCanvases` maps pending/error to `[]`; rows show “No canvases available,” hiding failures. |
| file:symbol | `www/packages/canvas/src/launcher/useCanvases.ts`; `commandRows` |
| Fix disposition | Preserve loading / error / data / retry in the switcher. |

### m4 — `useCommandCenter` over ~150 line function guard
| | |
| --- | --- |
| Severity | minor · **[IMPL]** |
| Families | gpt (m4) |
| Defect | Hook grew past the project ~150-line function threshold while owning navigation, queries, hotkeys, rows, and dispatch. |
| file:symbol | `www/packages/canvas/src/launcher/useCommandCenter.ts` |
| Fix disposition | Extract Canvas/query orchestration into a focused hook. |

### m5 — Service calls eight private `SpaceStore` methods
| | |
| --- | --- |
| Severity | minor · **[IMPL]** |
| Families | opus (m1), grok (suggestion 1) |
| Defect | `SpaceCrudService` reaches `_upsert_worktree`, `_ensure_worktree_root`, `_find_detection`, `_mark_missing_worktrees`, `_write_cache`, `_claim_git_space`, `_lookup_space_for_detection`, `_insert_space`. Import gate is AST-import-only and stays green. |
| file:symbol | `space.service.SpaceCrudService.reconcile_detection` / `resolve_cwd`; `space.store.SpaceStore` private methods |
| Fix disposition | Promote a public repository API (drop underscores) or one public reconcile seam on the store; stop cross-module private attribute use. |

### m6 — `director_tree` N+1 over spaces
| | |
| --- | --- |
| Severity | minor · **[IMPL]** |
| Families | opus (m2) |
| Defect | `list_spaces` then per-space `list_canvases` (and list_spaces already queries worktrees per space). Unbounded by owner space count. |
| file:symbol | `space.service.SpaceCrudService.director_tree` |
| Fix disposition | One joined roots-by-owner read when product surfaces need the aggregation. |

### m7 — Filesystem `_write_cache` still written, still unread
| | |
| --- | --- |
| Severity | minor · **[IMPL]** |
| Families | opus (m3) |
| Defect | Scout-stale parallel projection preserved on reconcile; no production reader. |
| file:symbol | `space.store.SpaceStore._write_cache` via `SpaceCrudService.reconcile_detection` |
| Fix disposition | Delete under break-freely, or document as diagnostic-only and stop production writes. |

---

## Out of S1 fix scope (record only)

| Note | Families | Disposition |
| --- | --- | --- |
| Launch resolution does not yet consult `lifecycle_state` (`deleting` / non-active) | grok | Correct for S1; required before S6 Git delete |
| `director_tree` is service-tested but not REST/MCP exposed | grok | Fine if intentional; expose when product needs it |
| Grok local gate green (check + 3342 API tests + migration-smoke) vs gpt red frontend e2e | grok / gpt | Blocker is remote/browser e2e contract, not backend unit suite |

---

## Fix order (recommended)

1. **B1** fixtures → green frontend e2e (unblocks merge ceremony).  
2. **Owner call on M1 [DESIGN]** (pair-delete DDL) and **M4 [DESIGN]** (plain→git identity) before more schema-dependent slices.  
3. **M2, M3, M5, M6** implementation against current spec.  
4. Minors as capacity allows; **m5** before S3/S5 grow store/service further.

## Severity counts (deduped)

| Severity | Count | Design vs impl (blk+maj only) |
| --- | --- | --- |
| Blocker | 1 | 1 [IMPL] |
| Major | 6 | 4 [IMPL] / 2 [DESIGN] |
| Minor | 7 | all [IMPL] |

Builder signal (merged): opus high trust on craftsmanship with latent schema miss; gpt verification-only distrust (authority, identity, DDL, red e2e); grok high trust on local gate. Synthesis preserves the **hard merge bar**: red required e2e + adjudicate final-schema delete before claiming S1 complete.
