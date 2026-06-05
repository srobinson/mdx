# S4 identity review: PR #328

Verdict: 1 blocker, 5 majors, 2 minors.

Reviewed exact range:

```text
base  d1f499e5c78c3aaf2c162644f9e40117d4443af1
head  be26765ba3642d0720f0e072cdc66f730bda4ec9
diff  30 files, +1271 / -115
```

## Required answers

1. **Is the dual write bridge total? No.** Every current production writer is bridged, but semantic totality fails for a child Canvas. [`syncActingContextFromCanvasState`](https://github.com/littleorgans/transport-matters/blob/be26765ba3642d0720f0e072cdc66f730bda4ec9/www/packages/canvas/src/model/canvasStoreLifecycle.ts#L118-L130) publishes the legacy default Worktree as the receipt's anchor Worktree, while [`useCanvasCommandHandler`](https://github.com/littleorgans/transport-matters/blob/be26765ba3642d0720f0e072cdc66f730bda4ec9/www/packages/canvas/src/workbench/CanvasCommandDispatcher.ts#L111-L130) correctly selects the Canvas anchor. A valid Canvas anchored to W1 with default W2 produces two identities for the same Canvas.

2. **Are the aggregate and S2 result structurally inert? No.** The S2 result is currently dataflow inert, but structural isolation is absent. [`useActingContextStore`](https://github.com/littleorgans/transport-matters/blob/be26765ba3642d0720f0e072cdc66f730bda4ec9/www/packages/space-client/src/actingContextStore.ts#L23-L47) exports the complete raw store, including mutation access, and [`beginClaim`](https://github.com/littleorgans/transport-matters/blob/be26765ba3642d0720f0e072cdc66f730bda4ec9/www/packages/space-client/src/actingContextStore.ts#L166-L190) uses shadow `context` to decide whether an S2 request occurs. `lastVerification` has no production reader. The compatibility receipt and navigation projections are deliberately live and already influence rendering, inventory requests, mutation scope, viewer props, and launch decisions.

3. **Does generation solve concurrent requests, intergeneration ordering, reuse, reset, and initialization? No.** [`resolveActingContext`](https://github.com/littleorgans/transport-matters/blob/be26765ba3642d0720f0e072cdc66f730bda4ec9/www/packages/space-client/src/domain/actingContext.ts#L67-L89) discards its watermark on clear. [`mirrorLegacyActingContext`](https://github.com/littleorgans/transport-matters/blob/be26765ba3642d0720f0e072cdc66f730bda4ec9/www/packages/space-client/src/actingContextStore.ts#L112-L139) can change the live receipt without advancing generation. [`resetActingContextStoreForTests`](https://github.com/littleorgans/transport-matters/blob/be26765ba3642d0720f0e072cdc66f730bda4ec9/www/packages/space-client/src/actingContextStore.ts#L162-L198) reuses generation values. Ordinary overlapping claims and a verification arriving after a newer complete selection are handled correctly.

4. **Is the `navigationSpaceId` split correct and complete? Yes.** No current browse or identity conflation was found. Local Arrow Right drilling remains an explicit launcher scope. Space, Worktree, and Canvas identity actions update aggregate navigation through [`activateSpace` and `activateWorktree`](https://github.com/littleorgans/transport-matters/blob/be26765ba3642d0720f0e072cdc66f730bda4ec9/www/packages/canvas/src/workbench/CanvasCommandDispatcher.ts#L154-L186). Inventory and mutation scope read navigation through [`useLauncherData`](https://github.com/littleorgans/transport-matters/blob/be26765ba3642d0720f0e072cdc66f730bda4ec9/www/packages/canvas/src/launcher/useLauncherData.ts#L1-L24) and the dispatcher. Local drill state never becomes acting identity.

## Findings

### Blocker 1: a child Canvas receives a contract invalid live receipt

Location: [`canvasStoreLifecycle.ts:syncActingContextFromCanvasState`](https://github.com/littleorgans/transport-matters/blob/be26765ba3642d0720f0e072cdc66f730bda4ec9/www/packages/canvas/src/model/canvasStoreLifecycle.ts#L118-L130)

The bridge maps `CanvasModel.defaultWorktreeId` to `ActingContextReceipt.worktreeId`. The receipt contract defines this field as the Worktree anchoring the Canvas at [`wire.ts:ActingContextReceipt`](https://github.com/littleorgans/transport-matters/blob/be26765ba3642d0720f0e072cdc66f730bda4ec9/packages/contract/src/space/wire.ts#L105-L110). A Canvas may be anchored to one Worktree and use another Worktree in the same Space as its default. Existing backend coverage demonstrates that valid shape at [`test_delete.py`](https://github.com/littleorgans/transport-matters/blob/be26765ba3642d0720f0e072cdc66f730bda4ec9/api/src/transport_matters/space/test_delete.py#L162-L175).

The command row preserves both concepts. The dispatcher selects `anchorWorktreeId` into the shadow context, rewrites the URL with `worktreeId`, then initializes legacy state from that default:

```text
Canvas C anchor  W1
Canvas C default W2

shadow context  { spaceId: S, worktreeId: W1, canvasId: C }
live receipt    { spaceId: S, worktreeId: W2, canvasId: C }
```

S2 rejects the live tuple with `canvas_worktree_mismatch` through [`resolveActingContext`](https://github.com/littleorgans/transport-matters/blob/be26765ba3642d0720f0e072cdc66f730bda4ec9/packages/space/src/domain/actingContext.ts#L78-L97). Current spawn behavior still follows W2, which preserves legacy launch behavior. The object exposed to migrated readers is nevertheless invalid under its declared contract, and the shadow aggregate cannot safely become authoritative in S5.

This also answers the receipt requirement. The projection mirrors legacy field values exactly, but those values do not carry receipt semantics for child Canvases.

### Major 1: supported partial legacy identity changes observable behavior

Locations:

* [`CommandCenter.tsx:CommandCenter`](https://github.com/littleorgans/transport-matters/blob/be26765ba3642d0720f0e072cdc66f730bda4ec9/www/packages/canvas/src/launcher/CommandCenter.tsx#L48-L60)
* [`CanvasWorkbench.tsx:CanvasWorkbench`](https://github.com/littleorgans/transport-matters/blob/be26765ba3642d0720f0e072cdc66f730bda4ec9/www/packages/canvas/src/workbench/CanvasWorkbench.tsx#L42-L47)
* [`actingContextStore.ts:getActingWorktreeId`](https://github.com/littleorgans/transport-matters/blob/be26765ba3642d0720f0e072cdc66f730bda4ec9/www/packages/space-client/src/actingContextStore.ts#L23-L34)

The store explicitly retains `projectedWorktreeId` for a supported Worktree only legacy seed. A legacy tuple `{spaceId: S, worktreeId: W, canvasId: null}` has no complete receipt.

Before this range, Command Center read `defaultWorktreeId` and marked W as Current. It now passes `receipt?.worktreeId ?? null`, so [`buildWorktreeRows`](https://github.com/littleorgans/transport-matters/blob/be26765ba3642d0720f0e072cdc66f730bda4ec9/www/packages/canvas/src/launcher/workdirRows.ts#L171-L200) drops that marker. Actions still target W through `getActingWorktreeId`, so display and action authority disagree.

CanvasWorkbench previously forwarded the legacy Space value. It now derives both Space and Canvas from the complete receipt, so it forwards a null Space to the pane layer for the same partial state. These changes sit outside the two named expected mismatches and violate S4's zero observable behavior requirement.

### Major 2: the generation watermark is incomplete

Locations:

* [`actingContext.ts:resolveActingContext`](https://github.com/littleorgans/transport-matters/blob/be26765ba3642d0720f0e072cdc66f730bda4ec9/www/packages/space-client/src/domain/actingContext.ts#L67-L89)
* [`actingContextStore.ts:mirrorLegacyActingContext`](https://github.com/littleorgans/transport-matters/blob/be26765ba3642d0720f0e072cdc66f730bda4ec9/www/packages/space-client/src/actingContextStore.ts#L112-L139)
* [`actingContextStore.ts:recordVerification`](https://github.com/littleorgans/transport-matters/blob/be26765ba3642d0720f0e072cdc66f730bda4ec9/www/packages/space-client/src/actingContextStore.ts#L193-L198)

Three sequences escape the intended stale response guarantee.

First, clear returns an unresolved state without a generation before the stale check:

```text
acting A, generation 2
clear
delayed workdir resolution B, generation 1
result: acting B is accepted
```

Second, a legacy mirror to an incomplete tuple updates `receipt`, `projectedWorktreeId`, and `navigationSpaceId` without incrementing generation. A verification issued for the former identity can then pass the equality check and be recorded as current. A complete mirror has the same problem while a claim is pending: the reducer rejects the `acting` event to preserve claim precedence, but the live receipt changes and generation does not.

Third, test reset restores generation zero. An unresolved old generation 1 request can collide with a new generation 1 request and pass the same equality check.

The S2 result remains record only in S4, which limits current product impact to incorrect shadow evidence. The reducer becomes unsafe when S5 applies results or workdir resolutions.

### Major 3: the expected mismatch ledger is self fulfilling

Locations:

* [`actingContextStore.test.ts:expected mismatch ledger`](https://github.com/littleorgans/transport-matters/blob/be26765ba3642d0720f0e072cdc66f730bda4ec9/www/packages/space-client/src/actingContextStore.test.ts#L111-L139)
* [`actingContext.test.ts:S2 corpus parity`](https://github.com/littleorgans/transport-matters/blob/be26765ba3642d0720f0e072cdc66f730bda4ec9/www/packages/space-client/src/domain/actingContext.test.ts#L141-L163)

The ledger manually constructs exactly the two expected cases, then compares only `canvasId`. The child Canvas defect above changes Worktree from W1 to W2 while retaining the same Canvas, so the gate reports no mismatch.

The domain parity test feeds each fixture's expected S2 result directly into the new reducer. It does not run S2 and the legacy projection over one shared input corpus, then compare all owner, Space, Worktree, and Canvas fields.

The two named entries are justified by the plan. The implementation does not prove that the ledger is exhaustive.

### Major 4: the Section 6 consumer gate does not enumerate consumers

Location: [`actingContextConsumerCoverage.test.ts`](https://github.com/littleorgans/transport-matters/blob/be26765ba3642d0720f0e072cdc66f730bda4ec9/www/packages/canvas/src/model/actingContextConsumerCoverage.test.ts#L4-L77)

The gate hard codes three migrated file groups and five deferred groups, then checks for one marker string in each file. `coveredSymbols` is declared and never asserted.

Two of the three `canvasActions` readers can return to legacy state while the third marker keeps the test green. A new reader in another file is invisible. The same weakness applies to Command Center. Downstream consumers such as `CanvasPaneLayer` and `ViewerCanvasContext` are outside the list.

Manual review found the current direct readers. The committed gate cannot enforce the checked inventory required by Section 6 or prevent a split authority regression.

### Major 5: shadow state has no structural isolation boundary

Locations:

* [`actingContextStore.ts:ActingContextStoreState`](https://github.com/littleorgans/transport-matters/blob/be26765ba3642d0720f0e072cdc66f730bda4ec9/www/packages/space-client/src/actingContextStore.ts#L23-L47)
* [`space-client/src/index.ts`](https://github.com/littleorgans/transport-matters/blob/be26765ba3642d0720f0e072cdc66f730bda4ec9/www/packages/space-client/src/index.ts#L1-L17)
* [`actingContextStore.ts:beginClaim`](https://github.com/littleorgans/transport-matters/blob/be26765ba3642d0720f0e072cdc66f730bda4ec9/www/packages/space-client/src/actingContextStore.ts#L166-L190)

The package exports the raw Zustand hook and full state type. Consumers can select `context` or `lastVerification`, and the hook exposes `setState`. No module or type boundary confines production code to approved legacy compatibility selectors.

Current source search found no production reader of `context`, `lastVerification`, or `discardedVerificationCount` outside the store. The S2 result is therefore dataflow inert today. Core `context` already controls whether URL and locator verification requests are issued, so the whole aggregate is not request inert under a literal reading.

The live compatibility fields have these current effects:

* `receipt` drives Command Center current state, CanvasWorkbench viewer props, terminal continuation, captured run launch, and other launch decisions.
* `navigationSpaceId` drives inventory query scope, mutation scope, reselect suppression, and Command Center Space state.
* `projectedWorktreeId` preserves launch decisions for partial legacy identity.
* No aggregate field is persisted.

A private store with narrow exported selectors and actions would make the shadow boundary enforceable.

### Minor 1: reducer precedence allows a later generic acting event to replace a verified claim

Location: [`actingContext.ts:resolveActingContext`](https://github.com/littleorgans/transport-matters/blob/be26765ba3642d0720f0e072cdc66f730bda4ec9/www/packages/space-client/src/domain/actingContext.ts#L75-L112)

An explicit selection is sticky. An acting state reached through `verified-claim` is not. A later `acting` event with `via: "workdir-context"` and a newer generation replaces it.

No S4 production path applies verification results into `context`, so this is an owner flip readiness defect rather than a current launch bug. The state machine should encode the intended URL versus workdir precedence before S5 makes either source authoritative.

### Minor 2: Space activation owns the same clear transition twice

Locations:

* [`CanvasCommandDispatcher.ts:activateSpace`](https://github.com/littleorgans/transport-matters/blob/be26765ba3642d0720f0e072cdc66f730bda4ec9/www/packages/canvas/src/workbench/CanvasCommandDispatcher.ts#L154-L167)
* [`canvasStoreLifecycle.ts:selectSpace`](https://github.com/littleorgans/transport-matters/blob/be26765ba3642d0720f0e072cdc66f730bda4ec9/www/packages/canvas/src/model/canvasStoreLifecycle.ts#L96-L116)

`activateSpace` clears aggregate identity, then calls `selectSpace`, which clears it again. The second call is currently a no op because the guard sees the same unresolved state and navigation Space.

Two functions now own one identity transition. Keeping the clear beside the legacy reset in one owner removes duplication and prevents the two paths from drifting.

## Legacy writer inventory

All current production writers were enumerated.

| Legacy write | Bridge |
| --- | --- |
| Module initialization through `createInitialCanvasModel` | No call is needed because both stores begin with null identity. |
| `initializeCanvas`, null Canvas branch | Writes legacy fields, then calls `syncActingContextFromCanvasState`. |
| `initializeCanvas`, switching Canvas branch | Replaces the model, rehydrates the Canvas cache, then synchronizes. |
| `initializeCanvas`, same Canvas branch | Patches launch identity, rehydrates, then synchronizes. |
| `selectSpace` | Replaces the legacy model, then clears aggregate identity. |
| `adoptDefaultWorktree` | Applies the legacy patch, then synchronizes. |
| Dispatcher Worktree and Canvas activation | Selects shadow identity, updates URL, then invokes verified Canvas initialization and its mirror. |
| Create Workdir completion | Routes through Worktree activation. |
| `resetCanvasStoreForTests` | Resets aggregate, resets legacy state, then synchronizes. |
| Persistence rehydration | Identity fields are excluded, so it is not a legacy identity writer. |

No unbridged direct production writer was found. The exported Zustand store still permits an external `setState` bypass, so totality is convention based. Blocker 1 makes the current bridge semantically incomplete even though writer coverage is complete.

## Other required checks

### Receipt and mismatch requirements

The receipt copies the three legacy identity fields and owner exactly when all three fields exist. The child Canvas case proves that exact field copying does not guarantee receipt semantics.

The two expected ledger entries match the build plan. The ledger is incomplete because it compares one field over two hand built cases.

### Detector quality

The late response test genuinely proves one narrow path: a verification arriving after a newer explicit selection is discarded. It does not cover complete to incomplete mirrors, a mirror rejected by reducer precedence, clear watermark loss, or reset reuse.

The field divergence tests exercise selected Command Center and Canvas action paths. The Section 6 marker test does not prove that every production reader was migrated or deferred.

### Persistence

`CANVAS_STORE_STORAGE_VERSION` remains `1` at [`canvasStore.persistence.ts`](https://github.com/littleorgans/transport-matters/blob/be26765ba3642d0720f0e072cdc66f730bda4ec9/www/packages/canvas/src/model/canvasStore.persistence.ts#L25-L39). The persistence implementation, persisted shape, and storage keys are byte identical between base and head. No acting context field is persisted.

### Reload to launch bug

The required bug remains unfixed.

[`parseCanvasLaunchContext`](https://github.com/littleorgans/transport-matters/blob/be26765ba3642d0720f0e072cdc66f730bda4ec9/www/packages/space-client/src/urlTupleCodec.ts#L16-L32) marks a URL Canvas unverified. [`SessionCanvasRoute`](https://github.com/littleorgans/transport-matters/blob/be26765ba3642d0720f0e072cdc66f730bda4ec9/www/packages/canvas/src/workbench/SessionCanvasRoute.tsx#L159-L175) initializes from the existing legacy resolution path and launches S2 verification separately. [`verifyActingContextClaim`](https://github.com/littleorgans/transport-matters/blob/be26765ba3642d0720f0e072cdc66f730bda4ec9/www/packages/space-client/src/actingContextStore.ts#L142-L160) records the result only. It cannot install the verified tuple into legacy state or the live receipt.

Consequently a fresh scoped URL still cannot recover a launch solely from the S2 result. This preserves the intended S4 boundary.

### `ActingContextResult` contract placement

The move to `@tm/contract/space` is correct. The browser transport and server domain share the same normalized success or failure union, the server reexports rather than redeclares it, and the browser transport converts the HTTP `{error}` envelope at its boundary. One declaration remains.

## Verification

* Exact head and base were confirmed through GitHub and local Git.
* The complete 30 file diff was inspected.
* `git diff --check` passed.
* Four focused domain, store, transport, and coverage test files passed, 27 tests total.
* Two browser test files passed under the shell package configuration, 19 tests total.
* Two focused existing regression tests passed, with 42 unrelated tests skipped. The route test emitted existing React `act` warnings.
* An initial attempt ran the two browser files under the root Node environment. They failed before collection because `localStorage` was unavailable. The correct shell package rerun passed.
* All nine GitHub checks on the exact head are green.
* No broad local suite, build, or typecheck was run.

## Navigation caveats

No current correctness defect was found in the browse split. Two sequencing facts remain worth carrying into later slices:

* Every legacy mirror writes `navigationSpaceId`, so its independence from acting identity is behavioral rather than structural.
* Dispatcher selection updates aggregate navigation before the URL and legacy writes complete. A synchronous failure between those steps can leave a transient split.

The asynchronous Create Workdir completion can also override an intervening user selection. That behavior predates this PR range and is outside the S4 finding count.
