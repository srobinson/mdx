# Scout: motion pan grooming debts

Baseline: main @ 068988f. Scope: two debts named in the PR#133 review. Read-only
scout; no design commitment. All citations are `file:symbol`.

## Owned state touched by this work

| State | Writer(s) | Reader(s) | Precedence today |
| --- | --- | --- | --- |
| strip `scrollLeft` | `horizontalScrollPan:writeScrollLeft` (drag + inertia), native wheel, `PieceStateStrip` scrollIntoView | browser layout, tests | Latest user or selection intent wins; documented on `horizontalScrollPan:createHorizontalScrollPan` |
| dnd-kit `DragOperation` private `_transform` cache | the `DragOperation.transform` derived getter (only on read) | `DragOperation.snapshot`, hence every `event.operation.transform` seen by our handlers | Whoever last read the getter; during a pan drag the sole reader is `PanelDragCapabilityRoot:HorizontalPanTransformObserver` |
| click suppression (`clickSuppressionElement`/`clickSuppressionTimer`) | `horizontalScrollPan:suppressTrailingClick`, `horizontalScrollPan:clearClickSuppression` | capture click listener on the strip | One-shot; self-clears via `window.setTimeout(…, 0)` |
| drag/inertia sessions | `horizontalScrollPan:createHorizontalScrollPan` closure | same closure | Single writer, fine |

---

## Debt 1 — `PanelDragCapabilityRoot:HorizontalPanTransformObserver`

### 1. Dependency inventory

Every symbol the observer touches, with its 0.5.0 status:

| Symbol | Public? | Breakage mode |
| --- | --- | --- |
| `Plugin` (`@dnd-kit/abstract`) | Exported, documented (dndkit.com/extend/plugins) | Loud: tsc |
| `Plugin.registerEffect` | `protected`, in shipped `index.d.ts` with JSDoc, on the plugins docs page | Loud: tsc |
| `DragDropManager` (`@dnd-kit/dom`) | Exported | Loud: tsc |
| `manager.dragOperation` | Typed public property | Loud: tsc |
| `dragOperation.status.dragging`, `.source.data` | Typed public | Loud: tsc |
| `dragOperation.transform` getter | Typed public with JSDoc | Loud if removed; see below for the silent part |

The symbol surface is entirely typed public API. A rename or removal in an
upgrade fails `tsc` loudly. The silent dependency is behavioral, not
symbolic: `DragOperation.snapshot` returns the cached private `_transform`,
which is refreshed **only** when something reads the derived `transform`
getter. With `Feedback.configure({ feedback: "none" })`, the Feedback plugin
early-returns before its (untracked) `dragOperation.transform` read, and no
other core plugin reads the getter during a pan drag. Search evidence:
`rg "dragOperation\.transform|operation\.transform" node_modules/@dnd-kit/dom/index.js`
returns exactly one hit, inside `Feedback`, after the `feedback === "none"`
early return. So the observer's void read is the only thing keeping
`event.operation.transform` advancing in `usePanelDrag:onDragMove` and
`usePanelDrag:onDragEnd`. That cache-refresh invariant is undocumented: the
plugins docs page shows only monitor listeners, never a reactive-read
pattern (verified by fetching dndkit.com/extend/plugins).

### 2. Supported per-frame observation in 0.5.0

No dedicated API exists. None found for: a transform hook
(`@dnd-kit/react:useDragOperation` exposes only `source` and `target`,
verified in `index.js`), a subscription, or a render-prop. Searches run:
`rg useDragOperation node_modules/@dnd-kit/react`, docs fetch of
dndkit.com/extend/plugins, web search for a 0.5 transform observation API.

However, a fully supported replacement exists without any new API. The typed
handler contract is `(event, manager)`
(`@dnd-kit/abstract:DragDropEventHandlers`; the React provider passes
`manager` as the second argument to every handler, verified in
`@dnd-kit/react` provider wiring). `manager.dragOperation.transform` is the
documented public getter. Reading the live getter in `usePanelDrag:onDragMove`
and `usePanelDrag:onDragEnd`, instead of the snapshot's cached copy, removes
the need for the observer entirely: the getter computes fresh from
`position.delta` plus modifiers on every call.

Timing parity traced in source: `actions.move` dispatches `dragmove`
synchronously and updates `position.current` in a queued microtask, so both
the snapshot path (cache refreshed by the observer effect after the position
write) and the live-getter path read the delta as of the previous event. Same
one-event lag; no behavior change. The handler wrapper (`trackRendering`)
only wraps callbacks in `startTransition` and tracks no signals, so the
getter read creates no subscription.

**Flag: Debt 1 is cheaper to eliminate than to guard.** The elimination is a
few lines in `usePanelDrag` (use the second handler argument) plus deleting
`HorizontalPanTransformObserver` and its entry in
`PanelDragCapabilityRoot:panelDragPlugins`. `Feedback` `"none"` and the
`AutoScroller` filter must stay; they exist for separate reasons (element must
not move; scrollLeft single-writer).

Build risks to verify, not blockers: final `dragend` value parity (the
sensor batches the last move through its scheduler, so confirm the end-of-drag
transform matches today's), and that the existing browser suite passes
unchanged, which it exercises directly.

### 3. Making breakage loud if the observer is kept

First, a correction to the debt as I originally framed it: the breakage is
already loud at the merge gate. `motionTimelinePan.browser.test.ts:
expectCompletedPanSuppressed` asserts `scrollLeft` advances under a real
Chromium drag, and all three cases run it. A dnd-kit upgrade that kills the
pan fails `pnpm test:all` deterministically. "Silent" is true only at the
unit level.

Options, costed against a hypothetical 0.5.x → 0.6 internals change:

- **Contract unit test** (drive a real `DragDropManager` via
  `manager.actions`, assert snapshot transform stays stale without a getter
  read and advances with one): medium cost, deterministic. Catches
  cache-semantics changes, which is the exact dependency. Misses adjacent
  changes (effect scheduling, sensor batching); the browser gate covers those.
- **Dev-only runtime invariant** (in `usePanelDrag:onDragMove`, throw when
  position advances while `transform.x` stays pinned; precedent for
  `import.meta.env.DEV` guards exists in `EditorStudio`): low cost. Catches
  the real failure on first dev pan, but not in CI, and adds a permanent
  branch to a per-frame path.
- **Browser test failing on a dead pan**: already exists, see above. Zero
  cost. It is the one signal that actually catches all variants of this
  breakage class.

### Recommendation

Eliminate. Switch both handlers to the live `manager.dragOperation.transform`
read and delete the observer. If Stuart prefers to keep the observer, add
nothing: the browser gate is already the loud signal, and the contract test is
worth its cost only if we expect to track 0.x upgrades frequently.

Deliberately not doing: keeping the observer while adding all three guards
(guard theater over a debt that can be deleted); adopting `useDragOperation`
(does not expose transform); accumulating `event.by` deltas in our own state
(adds a second writer to pan position).

---

## Debt 2 — `motionTimelinePan.browser.test.ts`, cancelled-pan case

### Why the current assertion cannot fail

`horizontalScrollPan:suppressTrailingClick` arms a one-shot capture click
listener cleared by a `window.setTimeout(…, 0)`. The test's follow-up
`target.click()` arrives many milliseconds later, so it can never be
suppressed, whatever the cancel plumbing did. Both realistic regression
classes pass the current test:

- (a) `usePanelDrag:onDragEnd` stops honoring `event.canceled`: `end(false)`
  arms suppression (expires unseen) and starts inertia (unasserted).
- (b) dnd-kit stops mapping `pointercancel` to a cancel: the drag survives the
  synthetic event, keeps panning through `mouse.move(1, 1)`, and ends at
  `mouse.up` as a normal pan.

Worse than briefed: `pan.end(true, …)` has **zero coverage repo-wide**, not
weak coverage. `rg "end\(true"` across `src` and `tests` returns nothing;
`horizontalScrollPan.test.ts` exercises only `end(false, …)`, and
`panelDragCapability.test.tsx` only `canceled: false`. The canceled path
(skip suppression, skip inertia) is entirely unguarded.

### 1. What an honest test must assert, costed

- **Unit test of `end(true)`** in `horizontalScrollPan.test.ts`: start, move
  with velocity, `end(true)`, then assert no animation frame is scheduled
  (inertia never starts; the file already stubs rAF) and a click dispatched at
  the element is not prevented (suppression never armed). Trivial cost, fully
  deterministic, and it is the missing guard the browser case was standing in
  for. Catches (a) at its source.
- **Browser post-cancel deadness**, in the existing case: after the cancel
  and before `mouse.up`, assert `cc-strip--dragging` is gone and a further
  `mouse.move` leaves `scrollLeft` unchanged (fails under (b)); then wait a
  few frames and assert `scrollLeft` still unchanged (fails under (a), since
  an 80 px flick is far above `horizontalScrollPanInertiaStopVelocityPxPerSecond
  = 12`). Self-validate against vacuity by first asserting the completed-pan
  control case **does** glide after release; if the gesture ever stops
  producing inertia, the control fails loudly instead of the cancel assertions
  passing emptily. Small cost; the control assertion is the flake mitigation.
- **Suppression-window probe from the browser** (racing a click into the 0 ms
  window): timing-dependent across the Playwright process boundary. Flaky by
  construction. The unit test asserts the same fact deterministically.

### 2. Real `pointercancel` drivability

Not practically drivable for a mouse pointer in this harness, and the pan is
mouse-only (`PanelDragCapabilityRoot:horizontalPanSensors` sets
`preventActivation` for every non-mouse pointer type), so CDP touch-cancel
cannot reach an active pan. Chromium fires a mouse `pointercancel` essentially
only when a native drag takes over, and dnd-kit forecloses that inside the
fixture: `PointerSensor.handlePointerDown` binds `dragstart` to
`preventDefault` for non-native-draggable sources. Plainly: keep synthesizing.

The synthetic dispatch is sound: `PointerSensor` binds `pointercancel` at the
document level with no `isTrusted` or `pointerId` filtering, and
`PointerSensor.handleCancel` goes straight to
`actions.stop({ canceled: true })` (verified in `@dnd-kit/dom` source).

Closest real-input alternative: **Escape**. `PointerSensor.handleKeyDown`
routes `Escape` to the same `handleCancel`, and `page.keyboard.press("Escape")`
produces a trusted event. It exercises our entire cancel plumbing end to end;
it does not exercise the `pointercancel` listener binding itself, so it
complements rather than replaces the synthetic dispatch.

### 3. The other two cases

- "pan suppresses the trailing State card click": honest. A dead pan fails the
  `scrollLeft` assertion; broken suppression fails the selections assertion.
  One noted fragility, not a defect: the injected click wins the race against
  the 0 ms clear timer only because dnd-kit dispatches `dragend` synchronously
  inside the `pointerup` dispatch; if a future dnd-kit defers `dragend`, this
  test fails loudly, which is the correct direction.
- "sub-threshold hand tremor still selects": honest for its purpose. It fails
  if the activation distance stops gating (6 px is under
  `horizontalScrollPanActivationDistancePx = 8`) or suppression over-arms. It
  passes if the whole pan feature is absent, which is inherent to a negative
  test and covered by the first case.

The weakness is unique to the cancelled-pan case.

### Recommendation

Add the `end(true)` unit test, and extend the browser cancel case with the
deadness assertions plus the control-glide assertion; add Escape as a second,
trusted-input cancellation path in the same file. Keep the synthetic
`pointercancel` dispatch.

Deliberately not doing: racing a synthetic click into the 0 ms suppression
window (flaky); touch-driven cancellation (cannot activate a mouse-only pan);
asserting suppression internals from the browser (the unit test owns that).

---

## Summary flags

- **Debt 1 is eliminable, not guardable-only**: the supported `(event,
  manager)` handler contract plus the public `transform` getter deletes the
  observer outright. Recommend elimination.
- **Debt 2 is a guard addition**: nothing to delete; the missing guard is a
  trivial unit test plus deadness assertions in the existing browser case.
- Correction to the original framing: a dnd-kit upgrade that kills the pan is
  already caught by the browser suite at `pnpm test:all`; the unit-level gap
  and the undocumented cache invariant are the real residue of Debt 1, and
  elimination clears both.
