# S4 design call

## Recommendation

Replace S4's live shadow aggregate and dual write bridge with a seam first migration. Keep the aggregate as the end state. Do not keep two mutable identity representations in production.

The safe expansion property is recoverable, but repairing PR #328 requires first building the single writer boundary that S4 assumed already existed. Once that boundary exists, a second live store provides little safety. Shadow comparison can be pure and diagnostic without becoming state or feeding readers.

## Why the current shape cannot prove totality

`canvasStore.ts:useCanvasStore` exposes `setState`. `CanvasStoreState` includes `spaceId`, `defaultWorktreeId`, and `canvasId`, while `canvasActions.ts` receives an unrestricted setter. A receipt type cannot force those writes through the bridge. A file list can show current coverage, but cannot prevent a future bypass.

Proof requires ownership:

1. Keep the raw Canvas store private and export a read hook plus named actions without `setState`.
2. Remove identity fields from generic Canvas patches and setters.
3. Route every identity change through one typed activation service accepting a closed `IdentityCommand` union.
4. Let that service own URL replacement, cache selection and rehydration, Space clear, selection, and workdir adoption.

The compiler then rejects a new identity writer outside the service. An absence grep remains useful defense, while the module boundary supplies the proof.

The verification route is a separate prerequisite. The browser calls the Python origin, while `SpaceContextService.verifyActingContext` is mounted only by the Gateway. Add a same origin product plane proxy with a production topology test. Keep verification in `@tm/space`; duplicating it in Python would violate the one control plane rule.

## Migration shape

First, land a behavior preserving refactor that introduces the activation service while writing only the legacy Canvas fields. Move every writer through it and encapsulate the raw store. Add no aggregate state and migrate no readers. This proves the choke point against current behavior.

Second, put `ActingContext` behind that service as the sole authority from its first production commit. URL and locator values remain candidates until Gateway verification. Inventory selections install receipts. Legacy getters become projections while readers migrate. A pure comparator may run old and new transitions over the same command, but must not persist a second result or drive rendering.

This order fixes the required outcomes directly:

* Reload verifies the URL candidate, installs the receipt, selects the Canvas cache, then rehydrates.
* Worktree switching becomes one atomic activation with sticky selection precedence.
* Desktop relaunch resolves workdir context through Gateway without creating rows.
* Persistence shape and `CANVAS_STORE_STORAGE_VERSION` remain untouched.
* CMDK and MCP use the same verification rule. Browser source ranking remains local.

## Cost

Roughly one third of PR #328 should survive as code: the contract move, failure vocabulary, much of the parity corpus, transport normalization, and parts of the reducer tests. The 203 line store, its 168 line suite, reader expansion, writer patches, and checklist gates need replacement or reversal. About half of the intent remains useful, but more than 35 to 40 percent implementation reuse is optimistic.

Repair also needs route wiring, anchor versus default separation, partial projection repair, a persistent generation watermark, stronger parity machinery, and two states until S6. That is more work and leaves safety dependent on understanding the bridge.

## Main counterargument

The strongest case for repair is that shadow expansion can expose parity before a flip. Once every write passes a compiler enforced choke point, that can be safe. The choke point creates the guarantee, however. A pure old versus new comparison over the same command then provides observation without a second store, generation lifecycle, or reader surface.

The aggregate is the right destination. The live shadow aggregate plus dual write bridge is the wrong route to it.

## Adjudication

### Reconciled write count

At base `d1f499e5`, there are **12 production acting identity mutation operations across three representations**.

Counting rule: count each direct production operation that can change the browser's active Space, Worktree, Canvas, or Canvas cache key. Count each branch local Zustand write, module assignment site, and identity URL rewrite once. Do not multiply a mutation by its transitive callers. Exclude tests, unused mutation capabilities, PR #328's new shadow state, and per-pane Worktree pins, which are launch bindings rather than the browser's acting context.

The 12 are:

* Six Canvas state paths: store initialization; the null, switching, and same Canvas branches of `initializeCanvas`; `selectSpace`; and `adoptDefaultWorktree`.
* Three `activeCanvasId` assignments: module initialization, the direct assignment in `initializeCanvas`, and `setActiveCanvasId`.
* Three URL writes: Canvas, Space, and Worktree activation.

Fable found the correct three acting identity representations, but counted the mirror's three assignments as one representation. Applying the operation rule changes its 10 to 12. It did not miss an acting identity surface.

Opus used a broader inventory. Its 19 reconciles as these 12, five per-pane pin or rehydration flows, the test reset, and the exported raw `setState` capability. Its numbered production tables actually stop at 18 before the shadow store because the raw capability is discussed outside the numbering. The five pin flows matter and need their own receipt-derived constructor boundary, but they do not replace or select the acting context. The reset and raw setter are representable writes, not current production execution paths.

The current 12 is knowable by inspection under this rule. Totality is still not provable by that inspection because the raw setter makes the next path unbounded. This distinction is the design reason for the seam.

### Enforcement ruling

Identity should leave `CanvasStoreState` entirely and live in a separate private identity owner. Two modules are acceptable; there must be one representation.

Fable is correct that persistence does not force separation. The Canvas persistence whitelist already excludes identity, so a private non-persisted slice could preserve the blob and version. Hiding the raw hook would also close the external `setState` escape.

That alone is insufficient. `canvasActions.ts:createCanvasActions` currently receives `StoreApi<CanvasStoreState>["setState"]`, so every Canvas action can write every field. TypeScript could enforce an in-store slice only if the raw store were private and every nonidentity action received a restricted capability that cannot return identity keys. That mechanism is adoptable, so an in-store slice is not impossible. It is more machinery and leaves identity lifecycle coupled to Canvas state replacement.

Field removal is the smaller proof. Existing Canvas actions may keep their current setter, while any attempted `spaceId`, `defaultWorktreeId`, or `canvasId` write becomes a compile error. The identity module keeps its raw store private, exports selectors and a closed command API, derives the persistence cache key, and owns the three URL writes. Per-pane pins remain a distinct launch override validated through a receipt-derived constructor.

This supplies the guarantee with the fewest new enforcement types. It changes no persisted shape, requires no storage version bump, preserves the no-seeding rule, and keeps browser precedence separate from the shared control plane verification rule.
