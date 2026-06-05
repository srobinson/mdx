# Canvas and Worktree CRUD, Slice 1 review

## Verdict

**1 blocker, 6 majors, 4 minors. Do not merge PR #316 at `25f20382f860d4371256319192bb295544b203f3`.**

Reviewed range: `b094e80d69ad7d57c5bba0ff8f4d71a986a837f2...25f20382f860d4371256319192bb295544b203f3`.

Authority: `tm-canvas-worktree-crud-spec-v1.md`, especially Slice 1 and the locked decisions in Context Matters entry `019f8910-846f-7900-bbce-0b22ae105dbc`.

## Blocker

### B1. The required frontend end to end gate is red

The exact head has [10 failing browser tests and 14 passing tests](https://github.com/littleorgans/transport-matters/actions/runs/29914059131/job/88903608933). Seven failures are in Canvas drop behavior, two are in persistence, and one is in desktop keybindings.

The production change correctly disables persistence until a durable Canvas UUID is available. The browser fixtures still open bare `/canvas` and seed the retired `transport-matters-canvas:direct-local` key. The persistence suite also requires importing the bare legacy key, contrary to the locked no migration decision. See [`canvas-drop-ux.spec.ts`](https://github.com/littleorgans/transport-matters/blob/25f20382f860d4371256319192bb295544b203f3/www/packages/shell/tests/e2e/canvas-drop-ux.spec.ts#L4-L23) and [`canvas-persistence.spec.ts`](https://github.com/littleorgans/transport-matters/blob/25f20382f860d4371256319192bb295544b203f3/www/packages/shell/tests/e2e/canvas-persistence.spec.ts#L13-L16). The legacy import remains asserted in [`canvas-persistence.spec.ts`](https://github.com/littleorgans/transport-matters/blob/25f20382f860d4371256319192bb295544b203f3/www/packages/shell/tests/e2e/canvas-persistence.spec.ts#L211-L220).

Required correction: give every affected fixture a valid durable Canvas UUID and matching namespaced cache key. Remove the obsolete legacy import case. Prove the corrected suite is green at the reviewed head.

## Majors

### M1. Observer refresh crosses the mutation authority boundary

`list_worktrees(refresh=True)` performs detection reconciliation for any `CrudCaller`. The MCP adapter exposes that option to observer principals. This can insert Worktrees and protected roots and update path, branch, head, missing state, and root labels. See [`service.py`](https://github.com/littleorgans/transport-matters/blob/25f20382f860d4371256319192bb295544b203f3/api/src/transport_matters/space/service.py#L178-L192) and [`space_mcp.py`](https://github.com/littleorgans/transport-matters/blob/25f20382f860d4371256319192bb295544b203f3/api/src/transport_matters/api/v1/space_mcp.py#L166-L176).

The REST form also performs the mutation through an origin unchecked GET route. See [`space_routes.py`](https://github.com/littleorgans/transport-matters/blob/25f20382f860d4371256319192bb295544b203f3/api/src/transport_matters/api/v1/space_routes.py#L273-L286).

Required correction: separate the read from reconciliation. Require Director authority for reconciliation. Expose REST reconciliation through an origin guarded mutation route.

### M2. Browser routes accept arbitrary Canvas strings and compose unverified identity tuples

The route parser trims `canvas_id` without validating a UUID. `defaultCanvasId` returns the string directly. Identity resolution checks Space and Worktree compatibility while preserving an explicit Canvas ID without confirming that the backend issued the complete tuple. See [`route.ts`](https://github.com/littleorgans/transport-matters/blob/25f20382f860d4371256319192bb295544b203f3/www/packages/canvas/src/route.ts#L11-L26) and [`route.ts`](https://github.com/littleorgans/transport-matters/blob/25f20382f860d4371256319192bb295544b203f3/www/packages/canvas/src/route.ts#L35-L49).

That string becomes the active store identity and local cache key before server validation. See [`canvasStoreLifecycle.ts`](https://github.com/littleorgans/transport-matters/blob/25f20382f860d4371256319192bb295544b203f3/www/packages/canvas/src/model/canvasStoreLifecycle.ts#L40-L61). Current tests codify values such as `canvas-9`.

Required correction: validate durable UUID syntax at the route boundary and accept an explicit Canvas only after resolving one consistent server issued Space, Worktree, and Canvas tuple. Invalid or mismatched identities must not activate persistence.

### M3. A missing or plain Worktree cannot later reconcile as a Git Worktree

On workspace identity conflict, `_upsert_worktree` moves the existing Worktree to the newly claimed Git Space and preserves its protected root UUID. See [`store.py`](https://github.com/littleorgans/transport-matters/blob/25f20382f860d4371256319192bb295544b203f3/api/src/transport_matters/space/store.py#L397-L417). `_ensure_worktree_root` then refuses that root because its Canvas still belongs to the original plain Space. See [`store.py`](https://github.com/littleorgans/transport-matters/blob/25f20382f860d4371256319192bb295544b203f3/api/src/transport_matters/space/store.py#L436-L468).

The practical sequence is straightforward: materialize a missing session path, create a Git repository at that path, then resolve it again. Reconciliation rolls back and the path remains anchored to the old Space. The same dead end follows `git init` in a previously plain directory.

Required correction: define and implement the identity transition atomically. Move the protected root with the Worktree or preserve the original Space according to the authority model. Add both transition cases to the reconciliation suite.

### M4. The deferred root reference does not enforce the Worktree and root pair

The foreign key validates owner, Space, and Canvas identity. It does not require the referenced Canvas to be a protected root or require its `default_worktree_id` to equal the referencing Worktree. See [`0030_space_crud_reset.py`](https://github.com/littleorgans/transport-matters/blob/25f20382f860d4371256319192bb295544b203f3/api/migrations/versions/0030_space_crud_reset.py#L18-L24) and the Canvas shape constraint in [`0030_space_crud_reset.py`](https://github.com/littleorgans/transport-matters/blob/25f20382f860d4371256319192bb295544b203f3/api/migrations/versions/0030_space_crud_reset.py#L88-L103).

PostgreSQL 18 accepted a user Canvas as `root_canvas_id`. It also accepted two protected roots whose pinned default Worktrees were swapped. The current service creates correct pairs, but the database accepts states prohibited by the durable identity contract.

Required correction: enforce the complete bidirectional pair with a deferred database mechanism and test rejected user roots, swapped roots, and mismatched defaults. This needs authority adjudication if the locked DDL cannot express the invariant.

### M5. The final schema cannot perform the specified Worktree deletion finalization

A protected root must have a nonnull default Worktree. Deleting the Worktree applies `ON DELETE SET NULL`, which immediately violates `canvas_kind_shape_ck`. Deleting the protected root first is immediately blocked by `space_worktree_root_canvas_fk`. See [`0030_space_crud_reset.py`](https://github.com/littleorgans/transport-matters/blob/25f20382f860d4371256319192bb295544b203f3/api/migrations/versions/0030_space_crud_reset.py#L91-L104) and [`0030_space_crud_reset.py`](https://github.com/littleorgans/transport-matters/blob/25f20382f860d4371256319192bb295544b203f3/api/migrations/versions/0030_space_crud_reset.py#L18-L24).

PostgreSQL 18 reproduced Worktree first deletion as SQLSTATE `23514`; root first deletion was rejected by the foreign key. Slice 6 requires deleting both records and the root subtree in one transaction.

Required correction: adjudicate and revise the cyclic delete design now, then add a migration test that performs the privileged pair deletion in the required order. Leaving this for Slice 6 requires another reset migration and invalidates the claim that Slice 1 installs the final schema.

### M6. REST and MCP publish incompatible JSON field names

REST serializes aliases such as `canvasId`, `spaceId`, and `rootCanvasId`. The shared MCP serializer calls `model_dump()` without `by_alias=True`, so MCP emits `canvas_id`, `space_id`, and `root_canvas_id`. See [`mcp_tooling.py`](https://github.com/littleorgans/transport-matters/blob/25f20382f860d4371256319192bb295544b203f3/api/src/transport_matters/api/v1/mcp_tooling.py#L18-L29). The new MCP test locks the divergent shape in [`test_space_mcp.py`](https://github.com/littleorgans/transport-matters/blob/25f20382f860d4371256319192bb295544b203f3/api/src/transport_matters/api/v1/test_space_mcp.py#L58-L73).

The typed shape contract says TypeScript mirrors JSON fields in camel case. Shared clients and fixtures cannot consume both read surfaces as one contract.

Required correction: serialize MCP results by alias and add caller parity assertions over successful result payloads, not only error semantics.

## Minors

### m1. Canvas names lack the locked normalization and length invariant

`Canvas.name` is unconstrained, and root name derivation returns branch, path basename, or workspace slug without trimming or limiting to 120 Unicode scalar values. See [`models.py`](https://github.com/littleorgans/transport-matters/blob/25f20382f860d4371256319192bb295544b203f3/api/src/transport_matters/space/models.py#L214-L224) and [`store.py`](https://github.com/littleorgans/transport-matters/blob/25f20382f860d4371256319192bb295544b203f3/api/src/transport_matters/space/store.py#L563-L570).

Add one shared name validator and use it for every root and future user mutation path. Add database protection if names are a durable invariant.

### m2. Public snapshots can mix committed generations

`get_space_snapshot` reads Space, Worktrees, and Canvases with separate statements under PostgreSQL `READ COMMITTED`. See [`store.py`](https://github.com/littleorgans/transport-matters/blob/25f20382f860d4371256319192bb295544b203f3/api/src/transport_matters/space/store.py#L81-L105). Concurrent reconciliation can make one response include a newly committed root without its Worktree, or the reverse. The rows converge on a later request, but a single public response can violate the atomic pair contract.

Read the projection from one statement or use a transaction isolation level that supplies one consistent snapshot.

### m3. Canvas loading and failures render as an authoritative empty tree

`useCanvases` collapses pending and error states to an empty array. See [`useCanvases.ts`](https://github.com/littleorgans/transport-matters/blob/25f20382f860d4371256319192bb295544b203f3/www/packages/canvas/src/launcher/useCanvases.ts#L4-L11). Command rows then report `No canvases available`. See [`commandRows.ts`](https://github.com/littleorgans/transport-matters/blob/25f20382f860d4371256319192bb295544b203f3/www/packages/canvas/src/launcher/commandRows.ts#L92-L107).

Preserve loading, error, data, and retry state so an operator can distinguish an empty authorized tree from a failed read.

### m4. The production command center hook crossed the 150 line guard

`useCommandCenter` grew from 143 lines to 152 lines in this PR. See [`useCommandCenter.ts`](https://github.com/littleorgans/transport-matters/blob/25f20382f860d4371256319192bb295544b203f3/www/packages/canvas/src/launcher/useCommandCenter.ts#L206-L216). It now owns navigation state, four query sources, focus restoration, hotkeys, row derivation, gesture dispatch, and output assembly.

Extract the Canvas and query orchestration at a coherent seam. The enlarged `describe` callbacks in `commandRows.test.ts` and `canvasStore.test.ts` also deserve suite decomposition, but they are not counted as separate findings.

## Code hygiene

- No new or modified file exceeds 700 lines. The largest new production file is `space/service.py` at 428 lines.
- New backend responsibilities are generally separated well. The shared service is the clear transaction and authorization seam.
- No confirmed duplicate production service path, stale React Query response race, or dependency boundary violation was found.
- `canvasSwitchUrl` and the `select-canvas` dispatcher lack direct integration coverage. Their behavior currently depends on the red browser suite.
- `git diff --check` passed.

## Verification

- PR #316 remained open and mergeable at the exact reviewed base and head.
- Exact head CI passed backend lint, backend tests, package, frontend unit checks, desktop, standalone desktop, Linux wheel gateway spawn, and product plane. Frontend end to end failed.
- Local frontend Vitest: 167 files and 1,249 tests passed.
- Local backend model, workspace, and release identity tests: 46 passed.
- Focused backend Ruff checks passed.
- PostgreSQL 18.4 migration module: 7 passed. Additional probes reproduced the delete cycle and invalid root pair states described above.
- The wider local database suite could not run because `TRANSPORT_MATTERS_TEST_DATABASE_URL` was unavailable. Remote PostgreSQL 17 backend CI passed.
- Review work made no tracked repository changes. The preexisting untracked `.serena/` directory remained untouched.

## Builder trust

**Verification-only. The service decomposition is disciplined, but the unchecked authority boundaries, irreconcilable identity transition, database lifecycle conflicts, and red end to end gate do not earn production trust.**

## Delta reverify at `91428dc4ccab97252c8c7c76115399113fbe5ae3`

Date: 2026-07-22

Verdict: **B1 and M2 remain open. The other requested findings are closed.** This was a bounded fix verification against `25f20382f860d4371256319192bb295544b203f3...91428dc4ccab97252c8c7c76115399113fbe5ae3`, not a fresh Slice 1 review.

### B1 remains open: one shared browser fixture still uses synthetic Canvas identity

At the committed head, `seedCanvasExchangePane` still writes `transport-matters-canvas:direct-local`. Its `/api/meta` fixture supplies no Space, Worktree, or Canvas tuple. See [`canvas.ts`](https://github.com/littleorgans/transport-matters/blob/91428dc4ccab97252c8c7c76115399113fbe5ae3/www/packages/shell/tests/visual/fixtures/canvas.ts#L21-L27) and [`canvas.ts`](https://github.com/littleorgans/transport-matters/blob/91428dc4ccab97252c8c7c76115399113fbe5ae3/www/packages/shell/tests/visual/fixtures/canvas.ts#L129-L133).

`keybindings-desktop.spec.ts` consumes that fixture and opens bare `/canvas`. Persistence therefore stays disabled, the exchange pane never hydrates, and the fullscreen control is absent. See [`keybindings-desktop.spec.ts`](https://github.com/littleorgans/transport-matters/blob/91428dc4ccab97252c8c7c76115399113fbe5ae3/www/packages/shell/tests/e2e/keybindings-desktop.spec.ts#L51-L64). Exact head CI failed this test on the initial attempt and both retries, with 22 tests passing: [frontend end to end job](https://github.com/littleorgans/transport-matters/actions/runs/29919992999/job/88922800118).

The dedicated drop and persistence fixtures now use durable UUIDs and matching namespaced keys, and the legacy import assertion is deleted. The remaining shared fixture needs the same durable tuple treatment.

Unstaged fixes to this fixture and `www/packages/shell/package.json` appeared during verification. They are absent from `91428dc4` and were excluded from this verdict. They were preserved untouched.

### M2 remains partially open: reconciliation still runs through GET

The service now separates list from reconcile, observer MCP refresh is forbidden, and REST refresh requires a trusted origin plus a Director caller. However, `GET /spaces/{space_id}/worktrees?refresh=true` still calls `reconcile_worktrees`. See [`space_routes.py`](https://github.com/littleorgans/transport-matters/blob/91428dc4ccab97252c8c7c76115399113fbe5ae3/api/src/transport_matters/api/v1/space_routes.py#L273-L291).

A same origin prefetch, retry, or automated GET can still mutate Worktrees, protected roots, branch and head facts, and missing state. Move reconciliation to an origin guarded mutation method. Keep the GET route read only.

### Requested findings verified closed

- M3: non UUID Canvas identities are rejected at the route boundary. Persistence activates only after one matching server supplied Space, Worktree, and Canvas tuple.
- M5: deferred constraint triggers reject a user Canvas as root, swapped roots, and mismatched defaults.
- M6: MCP serialization uses aliases. Successful REST and MCP list payloads are asserted equal.
- m1: Canvas names use one trim, nonempty, Unicode scalar, and 120 scalar validator.
- m2: Space, Worktree, and Canvas snapshot rows come from one PostgreSQL statement.
- m3: Canvas loading, error, empty, populated, and retry states remain distinct through CMDK.
- m4: `useCommandCenter` is 142 lines. Query orchestration moved into `useLauncherData`.
- M1 follow up: the root foreign key is `NO ACTION DEFERRABLE INITIALLY DEFERRED`. Lone root deletion fails at commit, root first pair deletion commits, direct lone Worktree deletion fails, and concurrent reconciliation remains serialized. No concurrent reconcile, crash, dangling pair, or lone deletion hole was found. Worktree first deletion still fails the immediate root shape check, so the adjudicated root first statement order remains required.

### Delta verification

- Exact head CI passed backend lint, backend tests, package, frontend unit checks, desktop, standalone desktop, Linux wheel gateway spawn, and product plane. Frontend end to end remained red as described above.
- Focused frontend tests: 6 files and 110 tests passed.
- PostgreSQL 18.4 migration tests: 11 passed.
- Focused reconciliation and root identity tests: 4 passed.
- Canvas model tests: 12 passed.
- PR #316 remained open at exact head `91428dc4ccab97252c8c7c76115399113fbe5ae3` throughout the bounded review.
