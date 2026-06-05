---
title: Manicure Frontend UI Architecture Review
type: review
tags: [manicure, frontend, react, architecture, checkpoint]
summary: Checkpoint architecture review of the manicure React/TypeScript frontend. Well structured overall with clear separation of concerns. Three files exceed 300 lines. One duplicated utility and three unused props are the most actionable findings.
status: active
source: codebase-analyst
confidence: high
created: 2026-04-13
updated: 2026-04-13
---

## Summary

The manicure frontend is a ~2,600 LOC React + TypeScript application with a clean two-panel layout: exchange list on the left, detail/editor on the right. State management uses Zustand for UI state and TanStack Query for server state, with SSE for real-time updates. The architecture is well layered and consistent. The main issues are a duplicated `colorizeLine` function, three unused `onChange` props threaded through editor sections, and two files exceeding 300 lines that could benefit from extraction.

## Strengths

- **Zero `any` types.** The entire codebase uses proper typing. No escape hatches anywhere in the source.
- **Clean state architecture.** Zustand handles transient UI state (selected ID, paused flow, forwarding state). TanStack Query handles all server state. The SSE hook (`useExchangeStream`) pumps events into both stores without owning query state itself. This is textbook separation.
- **Hooks are well scoped.** Each hook has one job: `useExchanges` fetches the list, `useExchangeStream` manages the SSE connection, `useBreakpoint` handles arm/disarm, `useOverrides` wraps the override CRUD. None leak implementation details.
- **No barrel exports.** Direct file imports everywhere. No `index.ts` re-export files. This eliminates circular dependency risk and keeps the import graph explicit.
- **No circular dependencies.** The dependency graph flows strictly downward: `app.tsx` > `components/` > `hooks/`, `stores/`, `lib/`, `api.ts`, `types.ts`. No upward or lateral cycles.
- **Type design is comprehensive.** `types.ts` (197 lines) models the full domain: request/response IR, content blocks (discriminated union), overrides, pipeline stats, breakpoint state. All union types use string literal discriminants. `Record<string, unknown>` is used for genuinely opaque provider data, which is correct.
- **API layer is clean.** `api.ts` (153 lines) is a thin typed fetch wrapper. Every function returns a typed promise. Response types that are only relevant to the API layer (`OverrideListResponse`, `OverrideMutateResponse`, `ToggleResponse`) are defined in the API file, not in `types.ts`. Good boundary.
- **Component responsibilities are singular.** Each component does one thing: `TokenBar` renders a token distribution bar, `CompressionBar` renders a compression ratio bar, `Toggle` is a binary switch, `HoverCard` is a cursor-following tooltip. No god components.
- **Consistent visual language.** All components use the same design tokens (`.chip`, `.label`, `.card-flush`, `.hairline-x`, `.section-rule`). Color semantics are consistent: `text-sage` for positive, `text-amber` for warnings, `text-rose` for errors, `text-sky` for info.
- **Selective persistence.** `uiStore` uses Zustand's `persist` middleware but partializes to only persist `selectedId`, not transient state like `pausedFlow` or `forwardingFlowId`. Deliberate and correct.

## Issues

### 1. Duplicated `colorizeLine` function (Major)

**Files:** `www/src/components/detail/JsonView.tsx:11` and `www/src/components/editor/MessagesSection.tsx:7`

The exact same 55-line `colorizeLine` function exists in both files. Same regex, same color classes, same logic. This is a maintenance risk: a color change or regex fix must be applied in two places.

**Recommendation:** Extract to `www/src/lib/colorizeLine.ts` (or `www/src/lib/formatting.ts` since that file already exists and is only 5 lines). Both files import from the shared location.

### 2. Unused `onChange` props in editor sections (Major)

**Files:**
- `www/src/components/editor/ToolsSection.tsx:275` (`onChange: _onChange`)
- `www/src/components/editor/SystemSection.tsx:153` (`onChange: _onChange`)
- `www/src/components/editor/MessagesSection.tsx:347` (`onChange: _onChange`)

All three editor sections accept an `onChange` prop that is destructured, prefixed with underscore, and never used. The prop is defined in each component's interface (`ToolsSectionProps`, `SystemSectionProps`, `MessagesSectionProps`) and passed from `BreakpointEditor.tsx` (lines 147, 154, 160).

These sections use the override system exclusively. The `onChange` callbacks (`setTools`, `setSystem`, `setMessages` defined in `BreakpointEditor.tsx:38-41`) are dead code paths. This suggests an earlier design where direct IR mutation and override-based mutation coexisted, and the direct path was removed but the plumbing left behind.

**Recommendation:** Remove the `onChange` prop from all three section interfaces and their parent. Remove the `setTools`, `setSystem`, `setMessages` callbacks from `BreakpointEditor` (lines 38-41).

### 3. `MessagesSection.tsx` at 399 lines (Minor)

**File:** `www/src/components/editor/MessagesSection.tsx` (399 lines)

This is the largest file in the frontend. It contains four components: `ColorizedPre`, `BlockRow`, `MessageCard`, and `MessagesSection`. The `BlockRow` component alone is 125 lines (143-267) and handles five different block type expansions.

Not critical at current size, but approaching the threshold where extraction would improve readability.

**Recommendation:** Consider extracting `BlockRow` and `ColorizedPre` into a shared `www/src/components/editor/BlockRow.tsx`. This would also resolve issue #1, since `ColorizedPre` already depends on the duplicated `colorizeLine`.

### 4. `ToolsSection.tsx` at 351 lines (Minor)

**File:** `www/src/components/editor/ToolsSection.tsx` (351 lines)

Contains three components: `ToolRow`, `ToolGroupSection`, and `ToolsSection`. The structure is clean but dense. The helper functions (`hasOverride`, `getToggleOverride`, `getDescOverride`, `toolCharCount`, `displayName`, `buildEditorGroups`) add 60 lines of preamble before any components.

Not urgent. The helpers are well-named and only used within this file.

### 5. Unsafe SSE message parsing (Minor)

**File:** `www/src/hooks/useExchangeStream.ts:27-50`

The SSE `onmessage` handler parses JSON into `Record<string, unknown>` and then casts each field individually with `as string`, `as number`, `as PausedFlow["ir"]`, etc. There is no runtime validation. A malformed server message would produce an object with correct TypeScript types but undefined/wrong runtime values.

The `try/catch` at line 63 catches parse errors but not type mismatches. If `data.id` is missing, the entry gets `id: undefined` typed as `string`.

**Recommendation:** This is low risk because the server is trusted. If validation is ever needed, a lightweight schema check (or a single type guard function) would be appropriate. Not blocking.

### 6. Inline SVG in `app.tsx` entry page (Minor)

**File:** `www/src/app.tsx:23-57`

The entry page renders a 35-line inline SVG for the Manicure logo. A `ManicureIcon` component already exists at `www/src/components/ManicureIcon.tsx` (146 lines) with a different, more detailed version of the icon.

Having two separate icon implementations is a minor consistency issue. The `app.tsx` version uses the simpler globe-with-curves design; `ManicureIcon.tsx` uses the detailed sunburst/cog design.

**Recommendation:** If both designs are intentional (entry page vs. elsewhere), document the distinction. If not, consolidate to one component with a `variant` prop.

### 7. Module-level mutable state in `ToolGroups.tsx` (Minor)

**File:** `www/src/components/detail/ToolGroups.tsx:40-52`

```typescript
const GROUP_HUES: Record<string, string> = {};
let _paletteIdx = 0;
```

Module-level mutable state outside React's lifecycle. The `groupColour` function mutates `GROUP_HUES` and `_paletteIdx` on every new plugin label. This works because the mapping is additive and stable, but it would break if the component tree unmounts and remounts with different data (the palette index would continue from where it left off, not reset).

**Recommendation:** Acceptable for current usage. If this ever causes visual bugs, convert to a `useMemo`-based approach or a `Map` scoped to the component.

### 8. `app.tsx` does property destructuring on `useUIStore` (Minor)

**File:** `www/src/app.tsx:14`

```typescript
const { selectedId, setSelectedId, pausedFlow, clearPausedFlow } = useUIStore();
```

This subscribes the `App` component to the entire store. Every state change triggers a re-render of the root component. The hooks (`useBreakpoint`, `useExchangeStream`) correctly use selector-based access (`useUIStore((s) => s.setPausedFlow)`), but the root component does not.

**Recommendation:** Use individual selectors for each value:
```typescript
const selectedId = useUIStore((s) => s.selectedId);
const setSelectedId = useUIStore((s) => s.setSelectedId);
```
This prevents unnecessary re-renders when unrelated store fields change (e.g., `forwardingFlowId`).

### 9. Cross-subdirectory import between `editor/` and `detail/` (Minor)

**File:** `www/src/components/editor/ToolsSection.tsx:3`

```typescript
import { groupTools } from "../detail/ToolGroups";
```

The editor's `ToolsSection` imports `groupTools` from the detail view's `ToolGroups`. This is the only cross-boundary import between the two subdirectories. The function itself is a pure utility (takes tools array, returns grouped array).

**Recommendation:** If the editor and detail directories are meant to be independent feature modules, extract `groupTools` to `www/src/lib/toolGrouping.ts`. If they're just organizational subdirectories (which appears to be the case), the current import is fine.

## Recommendations (Prioritized)

1. **Extract `colorizeLine` to `lib/formatting.ts`.** Five-minute fix, eliminates the only code duplication in the codebase.

2. **Remove dead `onChange` props from editor sections.** Clean cut: delete the prop from three interfaces, three component signatures, and three call sites in `BreakpointEditor`. Remove four dead callbacks. Reduces confusion about which mutation path is active.

3. **Use Zustand selectors in `app.tsx`.** Switch from destructured `useUIStore()` to individual `useUIStore((s) => s.field)` selectors. Prevents the root component from re-rendering on every store mutation.

4. **Extract `BlockRow` from `MessagesSection.tsx`.** Brings the largest file under 300 lines. Natural seam: `BlockRow` is self-contained with its own state and effects.

5. **Consolidate or distinguish the two icon variants.** Either use `ManicureIcon` in the entry page, or document why the entry page has a different design.

## File Size Audit

| File | Lines | Status |
|------|-------|--------|
| `editor/MessagesSection.tsx` | 399 | Flag (>300) |
| `editor/ToolsSection.tsx` | 351 | Flag (>300) |
| `types.ts` | 197 | OK |
| `editor/SystemSection.tsx` | 188 | OK |
| `detail/ExchangeCard.tsx` | 185 | OK |
| `editor/BreakpointEditor.tsx` | 170 | OK |
| `editor/EditorActions.tsx` | 167 | OK |
| `api.ts` | 153 | OK |
| `ManicureIcon.tsx` | 146 | OK |
| `detail/JsonView.tsx` | 144 | OK |
| `app.tsx` | 133 | OK |
| `detail/ToolGroups.tsx` | 121 | OK |
| `detail/InspectTab.tsx` | 119 | OK |
| `detail/ContentBlocks.tsx` | 115 | OK |
| `ExchangeList.tsx` | 100 | OK |
| All others | <100 | OK |

## Dependency Graph (Simplified)

```
main.tsx
  + QueryClientProvider (lib/queryClient.ts)
  + App (app.tsx)
      + useExchanges (hooks/useExchanges.ts) --> api.fetchExchanges
      + useExchangeStream (hooks/useExchangeStream.ts) --> stores/uiStore
      + useBreakpoint (hooks/useBreakpoint.ts) --> api.*, stores/uiStore
      + stores/uiStore (Zustand)
      |
      +-- ExchangeList (components/ExchangeList.tsx)
      |     + lib/formatting.displayModel
      |
      +-- ExchangeDetail (components/ExchangeDetail.tsx)
      |     + api.fetchExchange (via react-query)
      |     + stores/uiStore (direct getState for 404 cleanup)
      |     +-- InspectTab (detail/InspectTab.tsx)
      |     |     +-- ExchangeCard (detail/ExchangeCard.tsx)
      |     |     +-- ContentBlocks (detail/ContentBlocks.tsx)
      |     |     +-- ToolGroups (detail/ToolGroups.tsx)
      |     +-- JsonView (detail/JsonView.tsx)
      |
      +-- BreakpointEditor (editor/BreakpointEditor.tsx)
            + useOverrides (hooks/useOverrides.ts) --> api.*
            + stores/uiStore
            +-- PausedHeader (editor/PausedHeader.tsx)
            +-- EditorActions (editor/EditorActions.tsx)
            +-- SamplingSection (editor/SamplingSection.tsx)
            +-- MessagesSection (editor/MessagesSection.tsx)
            +-- SystemSection (editor/SystemSection.tsx)
            +-- ToolsSection (editor/ToolsSection.tsx)
                  + detail/ToolGroups.groupTools (cross-boundary)
```
