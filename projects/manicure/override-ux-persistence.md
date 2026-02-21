---
title: Override Store Persistence - UX Analysis
category: projects
tags: [manicure, ux, overrides, breakpoint-editor]
created: 2026-04-14
---

# Override Store Persistence: UX Analysis

## Problem Statement

Overrides persist across requests in a session-scoped `OverrideStore`. A user configures 150 overrides for a large Claude Code request, then a completely different request arrives (different model, no tools, minimal system prompt). The UI shows "150 overrides active" with no distinction between stored and applied. The user sees no indication that their overrides had zero effect.

## Current Architecture

### Storage

- `OverrideStore` (`overrides.py:70-99`): session-scoped `OrderedDict` keyed by `(kind, target)`. Overrides accumulate until explicitly cleared.
- Store is process-global (`_store = OverrideStore()` at module level). No per-flow scoping.

### Application

- When a flow arrives, `_run_pipeline` calls `apply_overrides(store.get_all(), ir)` against the incoming IR.
- Each override produces an `OverrideAuditEntry` with `applied: bool` and `chars_delta: int`. An override is `applied=False` when its target is missing from the current IR (tool name not found, system index out of range, message index out of range, etc.).

### UI Display

**EditorActions status bar** (`EditorActions.tsx:136-164`):
- Shows `overrides.length` (total stored overrides), not applied count.
- Label: `"{N} overrides active"` where N = total stored.
- Delta percentage uses `overridableDelta` (system + tools delta only), which is 0 when targets are missing.

**Per-section headers** (ToolsSection, SystemSection, MessagesSection):
- Each counts overrides matching its own kind filters. These are purely store-based counts. No applied/skipped distinction.

**ExchangeCard** (post-forward, detail view, `ExchangeCard.tsx:148-173`):
- Already renders audit entries with `applied` status: unapplied entries get `opacity-40`. This pattern exists but is only visible after the request has been forwarded, not during editing.

### The Data Gap

The backend already produces `OverrideAudit.entries[].applied`. The frontend receives this audit when a flow is paused. The **editor** never surfaces the applied/skipped distinction, even though it has the data via the `audit` prop on `EditorActions`.

## Design Recommendation: Stored vs Applied Summary (Option A variant)

### Rationale for Option A

Options B and C either hide useful information (B discards stored count) or create noise (C shows warning toasts for an expected condition). Option D requires too much visual real estate. The cleanest solution extends the existing status line pattern.

### Proposed Display

Replace the current `"{N} overrides active"` with a two-part summary:

```
{stored} stored · {applied} applied · {delta}%
```

When all stored overrides match:
```
12 overrides · 12 applied · -23%
```

When some are skipped:
```
150 stored · 12 applied · -23%
```

When none match (the core problem case):
```
150 stored · 0 applied
```

The label change from "active" to "stored/applied" is the key semantic fix. "Active" conflates two states.

### Implementation Path

1. **EditorActions receives `audit` already.** Derive `appliedCount` from `audit.entries.filter(e => e.applied).length`.
2. **When audit is null** (no overrides enabled, or no flow yet), fall back to showing stored count only: `"{N} stored"`.
3. **Conditional rendering**: only show "applied" segment when `audit` is present and `appliedCount !== overrides.length` (avoids redundancy when all overrides match).

### Handling "tool defs 0"

**Current behavior**: `ComponentStat` shows `"tool defs 0"` when both before and after are 0.

**Recommendation**: hide zero-zero components. When `before === 0 && after === 0`, the stat carries no information. The component breakdown is useful for understanding what the request contains, but a line reading "tool defs 0" for a request that never had tools is just noise.

Implementation: wrap the `ComponentStat` render in EditorActions row 2 with `{(before.tools > 0 || after.tools > 0) && <ComponentStat ... />}`. Apply the same pattern to system and messages if desired, though those are rarely both zero.

### Always-Visible Total

**Current behavior**: total line only appears when `delta !== 0` (EditorActions.tsx:208-216).

**Recommendation**: always show the total. The request composition total (e.g., "total 12.4K") is useful context even with zero overrides. It tells the user what they are about to forward. The conditional check `delta !== 0` should become unconditional:

```tsx
<div className="flex items-baseline gap-1.5 pl-2 border-l border-edge">
  <span className="text-[11px] text-txt-3">total</span>
  <span className="text-[13px] text-txt metric-num">{formatChars(after.total)}</span>
  {delta !== 0 && (
    <span className={`text-[12px] metric-num ${delta < 0 ? "text-sage" : "text-amber"}`}>
      {delta < 0 ? "\u2212" : "+"}
      {formatChars(Math.abs(delta))}
    </span>
  )}
</div>
```

This shows `"total 12.4K"` when no delta, and `"total 12.4K +1,200"` when overrides produce a delta.

## Summary of Changes

| Area | Current | Proposed |
|------|---------|----------|
| Status label | `"{N} overrides active"` | `"{N} stored · {M} applied"` (contextual) |
| Zero-match case | `"150 overrides active · +0%"` | `"150 stored · 0 applied"` |
| Zero-zero stats | `"tool defs 0"` always shown | Hidden when both before and after are 0 |
| Total chars | Only shown when delta exists | Always shown; delta appended when non-zero |
| Audit data | Available but unused in editor | Used to derive applied count |

## Non-Goals

- Per-override applied/skipped indicators in the editor section headers. The ExchangeCard already does this post-forward; bringing it into the editor adds complexity for minimal gain during the editing phase.
- Override scoping per model or per request type. That would require a different store model entirely.
- Auto-clearing stale overrides. Users should retain control; the fix is making the mismatch visible, not silently removing overrides.
