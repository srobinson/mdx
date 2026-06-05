# Canvas Reset — Independent Architecture Assessment (Opus)

Solo assessment. Did not read any other agent's output. All claims grounded in fmm structure/dependency data and direct reads on `www/packages/canvas/src/session-canvas/`.

**Verdict: (A) reorganize in place.** Not close. Detail below.

---

## Measured ground truth (verified, not trusted)

fmm on `session-canvas` (source, tests excluded): **108 files · 11,855 LOC**, 12 buckets. The whole `@tm/canvas` package src is **164 files · 16,405 LOC**; `session-canvas` is ~72% of it.

Two structural checks came back **clean**, and they reframe the whole problem:

- `fmm_dependency_cycles filter=source` → **zero SCCs anywhere in the TS/TSX tree** (the only cycle reported is a Python pair, `override_state.py`↔`overrides.py`, out of scope).
- `fmm_dupe_clusters` at min_score 0.90 → **zero clusters** (400 candidates, 4320 comparisons).

So the pain is **not** cyclic dependency and **not** copy-paste duplication. That matters: a codebase with no cycles and no dupes is salvageable by *moving and renaming*, not by rewriting. This single fact is the strongest argument against a new-repo migration.

What is actually wrong is **inverted ownership** and **saturated god-objects** at the center, surrounded by boundaries that are already clean.

---

## 1. DIAGNOSIS — the precise failure mode

Four concrete defects, each grounded:

### D1. Domain model depends upward on the React viewer layer (the real rot)
`model/canvasStore.ts` and `model/spawn.ts` import `../viewers/registry` for `PICKER_PANE_ID`, `paneIdForRef`, `titleForRef` (confirmed via `fmm_dependency_graph` on `canvasStore.ts`: `local_deps` includes `viewers/registry.tsx`). Pane **identity and title** are domain vocabulary, but they are *defined in the presentation registry* and imported back up by the store. The model cannot be made React-free or unit-tested in isolation while this holds. This is the one genuinely inverted dependency in the tree.

### D2. `useCanvasStore` is a 263-line god-object
`model/canvasStore.ts` (503 LOC) exposes `useCanvasStore` as a *single* `create<CanvasStoreState>()(persist(...))` call whose body is ~263 lines (`fmm_file_outline`). Inside one closure: captured-run spawning (`addCapturedRun`), pane lifecycle (`spawnPane`/`closePane`/`minimizePane`/`restorePane`), docking (`dockPane`/`closeDockedPane`), affordance transitions (`expandPane`/`framePane`), layout replanning (`commitReorder`/`setBounds`/`resetViewport`), and route/persistence bootstrap (`initializeCanvas` alone carries the legacy-cache import + rehydrate dance). State shape, actions, and orchestration are fused.

### D3. `CanvasSurface` is a god-component spanning every domain
`components/CanvasSurface.tsx` (389 LOC; the `CanvasSurface` fn is 143 lines) imports **22 local modules** across `engine`, `keybindings`, `stores/{keymap,theme}`, `api/launchResolution`, `dnd/*` (4), `launcher/*` (2), `model/*` (3), `route`, `viewers/registry`, and `components/*` (6). It is simultaneously the workbench shell, the command dispatcher, the pane renderer, the DnD composer, the launcher bridge, and the route surface. There is no seam to reason about any one of those concerns alone.

### D4. Interactions reach into a specific viewer's internals
`dnd/canvasDrop.ts` imports `viewers/terminal/pasteRegistry.ts` (confirmed `fmm_dependency_graph`). Drag/drop — a generic interaction — knows the terminal viewer's paste implementation. Adding a second pasteable viewer means editing DnD.

### D5. Junk-drawer folders + one more latent god-file
`components/` (14 files · 1,228 LOC) and the `session-canvas/` root (3 files · 283 LOC) group by "React-ish" rather than by concern. And `launcher/commandModel.ts` (594 LOC) is D2-in-waiting: one file owning the nav-frame stack (`pushFrame`/`popFrame`/`topFrame`), fetch-status derivation, row grammar (`CommandRow`, `advanceGesture`, `interactionFor`), the `LauncherCommand` union, and six row builders (`buildAgentRows`, `buildCanvasRows`, `buildSettingsRows`, `buildSessionsRows`, `buildScopeRows`, …).

### What is already healthy (do not touch)
`src/engine/` (1,552 LOC, spatial/layout engine) is a clean sibling consumed through a contract; `src/ambient/`, `src/theme/`, `src/keybindings/`, `src/stores/` are already separated. `launcher/commandModel.ts` is *nearly pure* (deps: only `@tm/core`, `api/sessionClient`, `model/paneRecords`, `workdirRows`), so splitting it is low-risk pure extraction. `@tm/core` already holds shared contracts. **This is a codebase with good bones and a saturated core, not a rotten one.** That distinction drives the recommendation.

---

## 2. RECOMMENDATION — (A) reorganize in place

**Pick A. Decisively.** B (new repo) is the wrong tool for this failure mode and the worst possible timing.

Weighed against the evidence and Stuart's design values:

1. **The graph is salvageable by relocation.** Zero cycles + zero dupes means every defect above is fixed by *moving a symbol and adding a boundary test*. A rewrite/migration spends its budget re-deriving working code. Nothing here needs re-deriving.

2. **The one-wheel packaging is already elegant and would be endangered by B.** `www/packages/canvas/vite.config.ts` calls `productViteConfig({ bundleDir: "canvas", base: "/canvas", plugins: [react()] })`, which emits the built bundle straight into `api/src/transport_matters/canvas/`; `justfile build` runs `pnpm --filter @tm/canvas build` then `cd api && just build`. The wheel already embeds a front-end bundle produced from a *separate* source tree. B would, at best, reproduce this exact seam across a repo boundary; at worst break it. (Full mechanism in §5.)

3. **The boundary-enforcement harness already exists in-repo.** `www/packages/shell/src/testSupport/importGraph.ts` + `importGraphBoundary.test.ts` (cross-package, fail-closed on reach-ins) + `labBoundary.test.ts` (intra-`session-canvas` direction) already do exactly what the plan's "add boundary tests" step asks. The plan should **reuse and extend** this harness, not invent `sessionCanvasBoundary.test.ts` from zero (DRY). A new repo loses cheap access to it.

4. **t3code P1 is actively reshaping Canvas's infra edge — inside this repo.** Run lifecycle + terminal are being carved into root `packages/runtime` behind `@tm/gateway` (root `packages/` currently holds `activity`, `common`, `gateway`; `runtime` is the next slice). Canvas's `viewers/terminal/*`, `api/*`, and `stream/*` sit directly on that moving boundary. Forking Canvas to a new repo *now* means chasing a moving server boundary across a repo seam — maximal coordination cost for zero architectural gain. A reorg that defines the infra adapter seam (§3) *composes* with P1.

5. **Stuart's rubric is satisfiable without relocation.** Clear owners, explicit invariants, inspectable state, obvious extend paths — all delivered by the ownership split. The package *address* is not the pain; the draft plan says this correctly ("The pain is not the package address"), then partially contradicts itself with Task 10. Relocation is cosmetic until ownership is fixed, so it should be dropped from scope until after MVP.

**On the draft plan** (`docs/superpowers/plans/2026-07-05-canvas-repo-reset.md`): fundamentally sound; adopt ~90%. Its target mental model (workbench / model / viewers / interactions / launcher / infrastructure / lab), its dependency-direction table, and its lead with pane-identity extraction are all correct. Three corrections:
- **Reuse `importGraph.ts`**; do not build a new boundary mechanism.
- **Drop Task 10 (`apps/canvas` move)** from this effort. Keep `@tm/canvas` where it is. It is the one step that is pure address-churn.
- **Add an early infra-terminal adapter contract** so t3code's `@tm/gateway` client swaps in behind a seam rather than editing viewers later.

---

## 3. TARGET SHAPE — ownership and dependency direction

Scope the reset to `session-canvas/` internals. Leave `engine/`, `ambient/`, `theme/`, `keybindings/`, `stores/` as the already-clean siblings they are.

```
www/packages/canvas/src/session-canvas/
  workbench/       composition root + command dispatch (no domain logic)
    CanvasWorkbench.tsx      composes owners; replaces CanvasSurface
    CanvasPaneLayer.tsx      pane rendering only
    CanvasCommandDispatcher.ts  command routing only
    CanvasRoute.tsx
  model/           pure domain: NO react, NO zustand-in-logic, NO viewers
    paneIdentity.ts   OWNS PICKER_PANE_ID, paneIdForRef, titleForRef (invariant home)
    paneRecords.ts / paneLifecycle.ts / paneAffordances.ts / layoutPlanning.ts
    canvasState.ts    initial state shape
    canvasActions.ts  action implementations
    canvasStore.ts    THIN zustand assembly of state+actions+lifecycle
  viewers/         React pane renderers only; consume model identity, never define it
  interactions/    dnd, gestures, dock; depend on a generic paste-target contract
    dropTargets/pasteTargetRegistry.ts   generic contract (owner of paste seam)
  launcher/        navigation.ts / commandTypes.ts / commandRows.ts / templateRows.ts
  infrastructure/  api/ stream/ persistence/ terminal/  (IO + transport adapters)
    terminal/terminalTransport.ts  adapter seam → future @tm/gateway client
  lab/             consumer of product APIs; product code never imports lab
```

**Dependency direction (enforced by test):**
`workbench → {launcher, interactions, viewers, model, infrastructure}`; `launcher/interactions/viewers → model contracts`; `infrastructure → model DTOs only at serialize boundaries`; `model → engine contracts + pure canvas contracts`.
**Forbidden (each maps to a defect above):** `model → viewers` (D1), `model → react|zustand-logic` (D2), `dnd → viewers/terminal` (D4), `viewers → components/workbench`, `product → lab` (already enforced by `labBoundary.test.ts`).

Ownership of the key invariant, stated plainly: **pane id and title are model vocabulary. The viewer registry renders content and *consumes* identity; it does not mint it.**

---

## 4. FIRST THREE SLICES — each PR-sized, independently shippable

Each is behavior-preserving and removes exactly one named coupling. Verify each with the repo recipe: `cd www/packages/shell && pnpm exec vitest run <names>` + `pnpm --filter @tm/canvas typecheck`.

**Slice 1 — Pane identity → model.** Move `PICKER_PANE_ID`, `paneIdForRef`, `titleForRef` from `viewers/registry.tsx` into `model/paneIdentity.ts`; registry consumes them; delete `model → viewers` from `canvasStore.ts` and `spawn.ts`. Add a `session-canvas` direction test reusing `importGraph.ts` (`isInside`, `resolveLocalSpecifier`, fail-closed) asserting `model/** ↛ viewers/**` and `model/** ↛ react|zustand`, with a documented temporary allow-list for any residual, mirroring `labBoundary.test.ts`.
→ **Breaks the D1 inverted domain dependency.** Prerequisite for a pure model; unblocks Slice 2. *Highest-value cut.*

**Slice 2 — Decompose `useCanvasStore`.** Extract `model/canvasState.ts` (initial shape), `model/canvasActions.ts` (action impls), `model/canvasStoreLifecycle.ts` (`initializeCanvas`/rehydrate/legacy-cache), leaving `canvasStore.ts` a thin `create(persist(...))` assembly. No behavior change; store tests pass with import-path updates only.
→ **Breaks the D2 god-store.** Riskiest because `initializeCanvas`'s persist/rehydrate ordering is subtle; keep it byte-for-byte, move don't rewrite.

**Slice 3 — Sever `dnd → viewers/terminal`.** Move the paste-target registry to `interactions/dropTargets/pasteTargetRegistry.ts` as a generic contract; the terminal viewer *registers* an adapter against it; `dnd/canvasDrop.ts` depends only on the contract. Add boundary rule `dnd/** ↛ viewers/terminal/**`.
→ **Breaks the D4 interaction↔viewer leak.** Makes a second pasteable viewer additive.

(Natural Slice 4, out of the requested three: decompose `CanvasSurface` into `CanvasWorkbench` + `CanvasPaneLayer` + `CanvasCommandDispatcher`. Deferred because it is larger and depends on Slice 2 landing first.)

---

## 5. PACKAGING — one wheel, both under A, and even under B

**Under A (recommended): the single-wheel model is already in place and is preserved as-is.** The mechanism is *build-time bundle vendoring*: `@tm/canvas`'s Vite build (`bundleDir: "canvas"`, `base: "/canvas"`) writes its compiled assets into `api/src/transport_matters/canvas/`, which the Python package includes as package data; the wheel ships one artifact serving `/canvas`. `justfile build` sequences it: front-end filters build first, then `cd api && just build`. No submodule, no second publish, no runtime coupling. The reorg does not touch this seam (Non-Goal in the plan: "Do not change `/canvas`, `/canvas-lab`, or bundle output paths" — correct).

**Could BOTH repos still yield one wheel if B were chosen?** Yes, technically, and the existing seam is the proof-of-concept. Three mechanisms, ranked:
1. **Prebuilt-bundle vendoring at wheel build (best of the B options).** The canvas repo publishes a versioned built bundle (npm tarball or CI artifact); the Python repo's build step fetches and unpacks it into `api/src/transport_matters/canvas/` before `uv build`. Same end state as today, but now gated on a cross-repo version pin. *Tradeoff:* introduces a release-ordering dependency and a version-skew failure mode that does not exist today.
2. **Git submodule** of the canvas repo under `www/packages/canvas`, built in place. Preserves the exact current build graph. *Tradeoff:* submodules are a well-known coordination and checkout tax; contributors routinely forget `--recurse`.
3. **Two wheels / separate served origin.** Rejected: breaks the "one install rooted at `~/.transport-matters/`, served at `/canvas`" invariant.

**Conclusion:** every B packaging path is strictly *more* moving parts than the status quo to arrive at the *same* single wheel. That is a net-negative trade with no offsetting architectural benefit, since the actual defects (D1–D5) are internal to `session-canvas/` and untouched by repo boundary. **A preserves the elegant seam for free; B, at best, laboriously reconstructs it.**

---

## 6. RISK — the single coupling to break FIRST

**`model → viewers/registry` (pane identity), broken via Slice 1.**

It is the only *inverted domain* dependency in the entire source tree (all other leaks are lateral or component-level). Pane id, title, and picker id — the store's core vocabulary — are currently defined in the React presentation registry and imported *upward* by `canvasStore.ts` and `spawn.ts`. While this holds, `model/` cannot become React-free, cannot be unit-tested without the viewer layer, and every subsequent slice inherits the tangle. It is also the lowest-risk to cut: pure symbol relocation, no behavior change, with an importGraph boundary test that fails-closed to prevent regression.

**How, precisely:** create `model/paneIdentity.ts` owning `PICKER_PANE_ID` + `paneIdForRef` + `titleForRef`; repoint `canvasStore.ts`, `spawn.ts`, `paneRecords.ts`, and `viewers/registry.tsx` to import *from the model*; add a `session-canvas` boundary test reusing `www/packages/shell/src/testSupport/importGraph.ts`, asserting `model/** ↛ viewers/**` with a one-line-per-violation temporary allow-list, exactly as `labBoundary.test.ts` already does. Ship it as the first PR; everything else composes on top.
