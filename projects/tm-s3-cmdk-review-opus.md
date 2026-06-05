# S3-CMDK PR3 review — Opus (Anthropic-family MoE vote)

- **Range:** `git diff 97a80f56..8e240663` on `ml/s3-cmdk` (21 canvas frontend files, +899 / −157)
- **Lens:** UI correctness + state integrity + observable-end-state test rigor (+ builder-trust)
- **Tree:** pristine before and after (read-only; `git status --short` empty). Findings written to `~/.mdx`, outside the repo.
- **Authority:** `~/.mdx/projects/tm-s3-schema-scout.md` "Internal PR 3" (§4, plan lines 311-321); consumed PR1/PR2 backend contracts.

## Verdict: APPROVE — 0 blockers / 0 majors / 2 minors. Builder-trust: HIGH.

---

## Lens 1 — `useSpaces` full-inventory change ✓ (correct, no consumer regression)

- Old shape returned `query.data.showSwitcher === true ? items : []` — the sole Space was hidden entirely (`useSpaces.ts` pre-image). New `useSpaces` returns a structured `SpacesResult { items, count, showSwitcher, status, refetch }`, **always exposing the full inventory**, mirroring the established fetch-hook convention (`useCanvases`, `useSessionHistory`, `useRuntimeTemplates` all return `{ …, status, retry/refetch }` via the same `deriveFetchStatus`/`FetchStatus` from the `commandModel` barrel). Reuse fidelity is exact.
- New `fetchSpaceInventory` pages the REST cursor contract (`fetchSpaces({ limit: 100, cursor })`), OR-folds `showSwitcher` across pages, and guards against a repeated cursor (infinite-loop trap). Contract verified against `@tm/core`: `SpaceListResponse { items, nextCursor, showSwitcher }`, `FetchSpacesOptions { limit, cursor }`, path `/v1/spaces?limit=100[&cursor=…]`.
- Consumer sweep: the only consumer path was the Workdir scope. `useLauncherData` now spreads `spaces.items/count/showSwitcher/status/refetch`; `useCommandCenter` → `useLauncherRows` → `buildScopeRows` → `buildSpaceRows` all thread `spacesCount/spacesStatus/showSpaceSwitcher/activeSpaceId`. No stale consumer left reading the old array-only shape. `commandModel.testSupport.baseInputs` extended with the new fields so every existing row test keeps compiling.
- **Test:** `useSpaces.test.tsx` asserts the observable result object (loading→populated transition, count, showSwitcher) and pagination exhaustion with the **real request paths** `["/v1/spaces?limit=100", "/v1/spaces?limit=100&cursor=page-2"]`. The old "hides the sole default Space" test is correctly retired.

## Lens 2 — Active-Space state ✓ (single authority, empty Space selects cleanly, canvas unchanged)

- `select-space` → `activateSpace(spaceId)` → `spaceSwitchUrl` (sets `space_id`, deletes `workspace_hash/worktree_id/canvas_id/harness/run_id`) + `useCanvasStore.getState().selectSpace(spaceId)`. `selectSpace` lifecycle sets a fresh `createInitialCanvasModel` with `{ spaceId, worktreeId: null, canvasId: null, canvasIdVerified: false }`. `useCanvasStore.spaceId` remains the sole active-Space authority; **no second source of truth** was introduced. An empty Space selects cleanly (null Canvas/Worktree) without routing through a verified Canvas tuple.
- Canvas behavior UNCHANGED: `select-canvas` path untouched; `select-worktree` was only refactored into an `activateWorktree` helper with a byte-identical body (`worktreeSwitchUrl` + `initializeVerifiedCanvas`). No regression to existing canvas/worktree selection.
- State-integrity guard: `worktreeDefaults.adoptDefaultWorktreePatch` now rejects adopting a default worktree whose `spaceId` differs from the explicitly selected Space (`state.spaceId !== null && state.spaceId !== spaceId → {}`). This closes a real cross-Space contamination window opened by direct empty-Space selection. Locked by `canvasStore.test.ts` ("rejects a meta worktree from outside the explicitly selected Space" → `defaultWorktreeId` null, `spaceId` unchanged) and `route.test.ts::spaceSwitchUrl`.

## Lens 3 — Progressive disclosure ✓ (create-always; list/switch/rename/delete gated; last-delete CMDK-only)

- `buildSpaceRows` always emits `create-space` + `create-workdir` (+ `spaceStatusRows` for loading/error+retry). Management rows are appended **only when `showSwitcher && count > 1`**. Each disclosed Space yields switch (with `Current` trailing when active, and `advance→worktree` sub-scope only when it has worktrees), rename, and delete rows.
- Last-Space delete blocked in CMDK only, at two layers: (a) delete rows never render at `count <= 1`; (b) `deleteExistingSpace` early-returns when `inventory.items.length <= 1` before any transport call. Backend/REST/MCP still permit zero Spaces (not touched here), matching the scout requirement.
- **Tests:** `commandRows.test.ts` asserts the exact row `value`/`action` grammar for undisclosed (create-only) and disclosed (switch/rename/delete) states plus the loading/error+retry rows; `CanvasCommandDispatcher.test.tsx` "blocks deletion … only one Space" asserts the transport `request` is **never called**.

## Lens 4 — Bootstrap composition (createSpace → createWorkdir) ✓ with one minor

- `createWorkdirWithBootstrap` resolves `spaceId` from `command.spaceId ?? activeSpaceId ?? (sole space) ?? createSpace(...)`, then `createWorkdir(spaceId, path)`, then activates the returned worktree tuple and invalidates the query. Happy path and call **order** are directly tested: `CanvasCommandDispatcher.test.tsx` "composes createSpace then createWorkdir from a zero Space inventory" asserts `["POST /v1/spaces", "POST /v1/spaces/{id}/worktrees"]` **and** the observable store end-state (`spaceId/defaultWorktreeId/canvasId`).
- **m1 (minor):** In the zero-Space bootstrap, if `createWorkdir` throws **after** the fresh `createSpace` succeeded, the newly created empty Space is left behind — there is no compensating delete and no failure-path test. This partially misses the scout's "no partial/orphaned state on failure" criterion. Severity held to minor: the leftover is a **valid, first-class, deletable empty Space** (S3 makes zero/empty Spaces legal), the failure is user-recoverable (retry `create-workdir` into that Space, or delete it), and the single-user threat model bounds the blast radius. Worth a compensating delete or at least a red failure-path test.

## Lens 5 — Test rigor: observable end-state, red-first ✓ (avoids the PR#225/#227 footgun)

- Every new/changed test asserts what the user observes, not an internal mapping:
  - `CommandCenter.spaces.test.tsx` renders the real palette and asserts **rendered rows present/absent** (`getByText`/`queryByText`) for undisclosed vs disclosed, and active-Space reflected in the view via the `Current` trailing on **palette reopen** after clicking "Empty" (the exact live-behavior class that PR#225's intermediate-mapping test missed).
  - `CanvasCommandDispatcher.test.tsx` asserts transport **call sequence** + store end-state for bootstrap, the delete-active-Space **fallback** (`spaceId` becomes the surviving Space), and last-Space delete blocked (no request).
  - `commandRows.test.ts` asserts full row `value`/`action` arrays (observable grammar), replacing the retired single-worktree/missing assertions.
- Red-first (structural, gates not run under read-only): each assertion targets a live outcome that would fail against the pre-image (old `useSpaces` returned `[]`; old `buildSpaceRows` produced different `space:*` values with no create rows; old `adoptDefaultWorktree` kept the cross-space worktree).

## Contract parity (consumed PR1/PR2 surfaces) ✓

All `@tm/core` symbols the dispatcher/hook depend on exist and match: `createSpace(name)→SpaceSummary`, `renameSpace(id,name)`, `deleteSpace(id)→void`, `createWorkdir(spaceId,path)→WorktreeSummary` (unwraps `{worktree}`, route `/v1/spaces/{id}/worktrees`, exposes `spaceId/worktreeId/rootCanvasId`), `SpaceSummary { spaceId,label,worktrees }`. No signature drift that would let the fake-transport tests pass while production breaks; TS compilation binds the shapes.

## Minors

- **m1 (bootstrap, low):** zero-Space bootstrap leaves an orphaned empty Space if `createWorkdir` fails after `createSpace`; no rollback, no failure-path test. Benign + recoverable (empty Spaces are valid/deletable); see Lens 4.
- **m2 (UX, low):** `create-space`/`rename-space`/`create-workdir` collect input via blocking `window.prompt` (SSR-guarded with `typeof window === "undefined"`). Functional and correct, crude UX; not a correctness defect. A modeled input row is the eventual home.
- *(note, not counted)* `currentInventory` reads `queryClient.getQueryData(SPACES_QUERY_KEY) ?? fetchSpaceInventory()`; the delete-guard trusts possibly-stale cache. CMDK-UX-only (backend permits zero Spaces), single-user — negligible.

## Builder-trust verdict (codex build): HIGH

- **Craftsmanship:** async Space mutations extracted into a focused `spaceCommandDispatcher.ts` module rather than bloating `CanvasCommandDispatcher`; `select-worktree` refactored into a shared `activateWorktree` helper (DRY, no forked route logic); `selectSpace` added through the existing lifecycle/actions seam; the cross-Space default-worktree guard is a genuine state-integrity catch, not scope creep.
- **Test rigor:** strong and pointed at the known CMDK footgun — observable rendered rows, active-Space-on-reopen, transport call order, delete fallback, last-delete blocked. The one gap is the untested bootstrap failure path (m1).
- **Spec + reuse fidelity:** faithful to scout PR3 (create-always, count>1 gating, `useCanvasStore.spaceId` single authority, two-call client bootstrap, canvas behavior untouched); reuses the shared `deriveFetchStatus` barrel and the PR1/PR2 transport rather than re-inventing; `useSpaces` matches the sibling fetch-hook shape exactly.
- **Shortcuts:** none material. No second active-Space authority, no backend composite, contracts consumed as-is. Only soft edges: `window.prompt` UX (m2) and the missing bootstrap rollback/test (m1).
