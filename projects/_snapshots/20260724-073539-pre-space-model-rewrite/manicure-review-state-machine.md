---
title: "Manicure Frontend: State Machine Robustness Review"
category: projects
created: 2026-04-13
---

# State Machine Robustness Review

**Verdict: ADEQUATE**

The store is minimal, well typed, and correct for normal user flows. The coordination between SSE events, API calls, and Zustand state has two genuine race condition paths that can strand the UI in unrecoverable states. These are edge cases, not happy path failures, but they make the system fragile under concurrent traffic.

---

## State Shape Analysis

The Zustand store (`stores/uiStore.ts`) holds three values:

| Field | Type | Purpose |
|---|---|---|
| `selectedId` | `string \| null` | Currently selected exchange |
| `pausedFlow` | `PausedFlow \| null` | Active breakpoint flow in editor |
| `forwardingFlowId` | `string \| null` | Flow ID awaiting SSE completion |

**Well typed.** `UIState` interface covers all fields with proper nullability. `PausedFlow` is structurally sound (`types.ts:187-192`). The persist middleware correctly partializes to only `selectedId`, keeping transient state (`pausedFlow`, `forwardingFlowId`) session-scoped.

**One representable impossible state:** `forwardingFlowId` can theoretically hold a value unrelated to `pausedFlow.flow_id`. In practice, only `handleForward` and `handleForwardUnmodified` set it, always using `pausedFlow.flow_id`. A discriminated union or state machine encoding would prevent this by construction, but the current flat shape is acceptable given the low surface area.

---

## Transition Analysis

```
                    SSE "paused"
  IDLE ──────────────────────────────────► PAUSED
   ▲                                        │
   │                                        ├── Forward ──► FORWARDING (waiting for SSE exchange)
   │                                        ├── Pass Through ──► FORWARDING
   │                                        └── Drop ──► IDLE (immediate)
   │                                                        │
   │              SSE "exchange"                            │
   └────────────────────────────────────────────────────────┘
          (clears pausedFlow + forwardingFlowId)
```

Transitions are individually correct. Each handler in `BreakpointEditor.tsx` follows the pattern: clear error, set loading, try API call, set state on success, catch and show error on failure.

**One fragility in the Forward/Pass Through path:** After API success, `loading` stays `true` and is never reset to `false`. The component relies on being unmounted when `clearPausedFlow()` fires from the SSE exchange event. If the exchange event never arrives, the editor is permanently stuck in loading state. See Issue #1.

---

## Race Condition Analysis

### Race #1: New pause arrives during forwarding (Major)

Timeline:
1. Flow X pauses. SSE delivers `"paused"` event. `setPausedFlow(X)` fires, editor opens.
2. User clicks Forward. `releaseFlow(X)` API call succeeds. `setForwardingFlowId("X")`.
3. Flow Y pauses before X completes. SSE delivers `"paused"` for Y. `setPausedFlow(Y)` overwrites X. Editor now shows flow Y.
4. SSE delivers `"exchange"` for completed flow X. The check at `useExchangeStream.ts:59-61` evaluates `forwardingFlowId === data.id` which is `"X" === "X"` and is true. `clearPausedFlow()` fires.
5. Flow Y is silently discarded. The user never gets to edit it.

**Root cause:** `clearPausedFlow()` unconditionally clears `pausedFlow` without checking whether the current paused flow matches the forwarding flow.

**Fix:** Guard the clear: only call `clearPausedFlow()` if `pausedFlow?.flow_id === forwardingFlowId`. Or store `forwardingFlowId` alongside the flow it belongs to.

### Race #2: SSE disconnect gap (Minor)

`useExchanges.ts:9` sets `staleTime: Infinity` because SSE keeps the cache fresh. If SSE disconnects (and `connected` goes false), exchanges arriving during the gap are lost. EventSource auto-reconnects, but missed events are not replayed. The exchange list goes stale silently.

**Mitigated by:** The user can refresh the page, which triggers a fresh `fetchExchanges` call. But no in-app recovery exists.

### Race #3: Double click on Forward/Pass Through/Drop (Minor)

Between click and `setLoading(true)`, the buttons may still be clickable. A second click would fire a duplicate API call. Server-side idempotency likely handles this, but the UI could enter a confused state if both succeed.

---

## Error State Analysis

**Well handled:**
- All API functions (`api.ts`) throw on non-200 with descriptive messages.
- `BreakpointEditor.tsx` catches errors and shows them in a styled error banner. Error clears on next attempt (tested in `BreakpointEditor.test.tsx:155-169`).
- Override mutations use `onSuccess` callbacks for optimistic cache updates.

**Silently swallowed:**
- `useBreakpoint.ts:36`: `.catch(() => {})` on `fetchPausedFlowDetail`. If hydration fails after page refresh during a paused flow, the user sees no breakpoint editor and no error. The paused flow exists server-side but the UI doesn't know.
- `useExchangeStream.ts:64`: `catch {}` around the entire `onmessage` handler. Catches JSON parse errors (acceptable) but also catches any error in state update logic, hiding real bugs during development.

---

## Stale Data Analysis

| Data | Staleness risk | Mitigation |
|---|---|---|
| Exchange list | Medium. `staleTime: Infinity`. SSE keeps fresh, but gap during disconnect. | None in-app. Page refresh recovers. |
| Exchange detail | Low. No custom staleTime. Invalidated on Forward/Drop (`invalidateExchange`). | Correct. |
| Overrides | Low. Optimistic updates on patch/toggle. | `clearOverrides` uses `invalidateQueries` instead of `setQueryData`, creating a brief flash of stale data. Minor. |
| Breakpoint status | Low. Polling via default TanStack Query refetch. | Correct. |

---

## Hook Dependency Analysis

**Correct:**
- `useExchangeStream.ts:70`: deps `[queryClient, setPausedFlow, clearPausedFlow, setSelectedId]`. All Zustand actions are stable references. The imperative `useUIStore.getState()` at line 59 avoids adding `forwardingFlowId` to deps, preventing unnecessary EventSource reconnections. Good pattern.
- `useBreakpoint.ts:31-37`: deps `[pausedFlows, pausedFlow, setPausedFlow]`. Correct guard against re-running when already paused.

**No missing dependencies detected.**

---

## Test Coverage Analysis

**Covered:**
- Store CRUD (set, clear, forwarding state reset)
- App rendering: title, entry page
- ExchangeList: rendering, click selection, empty state
- ExchangeDetail: rendering, caching, re-fetch on ID change
- BreakpointEditor: Forward, Pass Through, Drop (success and failure), error clearing, cache invalidation
- ToolsSection: grouping, default checked state
- MessagesSection: block toggle, re-toggle with null removal
- PausedHeader: flow ID truncation

**Gaps:**

| Missing scenario | Severity |
|---|---|
| SSE `"exchange"` event updating query cache and selecting exchange | High |
| SSE `"paused"` event opening the breakpoint editor | High |
| SSE `forwardingFlowId` matching and clearing pausedFlow | High |
| SSE disconnect and reconnection behavior | Medium |
| Race: new pause arriving during forwarding (Race #1) | High |
| `useBreakpoint` hydration on mount with existing paused flow | Medium |
| Override toggle/clear flows within BreakpointEditor | Medium |
| App component rendering BreakpointEditor when `pausedFlow` is set | Medium |
| App component rendering ExchangeDetail when `selectedId` is set | Low |
| Double-click / rapid fire on action buttons | Low |

---

## Cleanup Analysis

**Correct:** `useExchangeStream.ts:69` returns `() => source.close()`. EventSource is properly closed on unmount or effect re-run.

No other effects require cleanup. Zustand store is global. TanStack Query manages its own lifecycle.

---

## Derived State Analysis

No stored-but-should-be-derived state found. `showEntryPage` is derived inline in `app.tsx:17`. Local state in `BreakpointEditor` (`editedIr`, `audit`, `loading`, `error`) is correctly scoped to the component lifecycle and receives updates from multiple sources.

---

## Reactivity Correctness

**Issue in `app.tsx:14`:**
```tsx
const { selectedId, setSelectedId, pausedFlow, clearPausedFlow } = useUIStore();
```
This uses the default selector (entire state object). Any state change, including `forwardingFlowId` updates, triggers a re-render of the root `App` component. Should use individual selectors:
```tsx
const selectedId = useUIStore(s => s.selectedId);
```
Other call sites (`useExchangeStream.ts:16-18`, `BreakpointEditor.tsx:31`, `useBreakpoint.ts:19-20`) correctly use fine-grained selectors.

**Impact:** Low. The store is tiny (3 values) and `forwardingFlowId` changes are infrequent. But it violates the principle of minimal reactivity and would matter if the store grows.

---

## Issues

| # | Severity | Location | Description |
|---|---|---|---|
| 1 | **Critical** | `useExchangeStream.ts:59-61` | Race condition: new "paused" event during forwarding causes `clearPausedFlow()` to discard the new flow. See Race #1. |
| 2 | **Major** | `BreakpointEditor.tsx:82-93` | No timeout on forwarding state. If the SSE exchange event never arrives, the editor is stuck in loading forever with no recovery path. |
| 3 | **Minor** | `useBreakpoint.ts:36` | Silent `.catch(() => {})` on `fetchPausedFlowDetail`. Paused flow hydration failure is invisible to the user. |
| 4 | **Minor** | `useExchangeStream.ts:64` | Bare `catch {}` swallows all errors including state update bugs. Consider logging or narrowing to `SyntaxError`. |
| 5 | **Minor** | `app.tsx:14` | Whole-store selector causes unnecessary re-renders on `forwardingFlowId` changes. Use individual selectors. |
| 6 | **Minor** | `useExchanges.ts:9` | No recovery mechanism when SSE disconnects. `staleTime: Infinity` prevents refetch on reconnection. |

---

## Recommendations (Prioritized)

1. **Fix Race #1.** In `useExchangeStream.ts`, guard the `clearPausedFlow()` call: read `pausedFlow` from the store and only clear if `pausedFlow.flow_id === forwardingFlowId`. This is a one-line fix that eliminates the most dangerous edge case.

2. **Add forwarding timeout.** In `BreakpointEditor`, add a timeout (30-60s) that resets `forwardingFlowId` and `loading` if the SSE exchange event hasn't arrived. Show a "timed out" error with a retry option.

3. **Surface hydration errors.** Replace `.catch(() => {})` in `useBreakpoint.ts:36` with error state that renders in the UI, or at minimum `console.error`.

4. **Add SSE integration tests.** The entire SSE data flow (event parsing, cache updates, state transitions) is untested. These are the most critical paths and the hardest to debug in production.

5. **Narrow the catch in `useExchangeStream`.** `catch (e) { if (!(e instanceof SyntaxError)) throw e; }` or log unknown errors.

6. **Use fine-grained selectors in `app.tsx`.** Low effort, eliminates wasted renders as the store grows.

7. **Consider SSE reconnect refetch.** On reconnection (transition from `connected: false` to `true`), invalidate the exchanges query to backfill any gap.
