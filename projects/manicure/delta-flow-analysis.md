---
title: Delta Calculation Flow Analysis
created: 2026-04-14
status: complete
tags: [manicure, delta, overrides, bug-analysis]
---

# Delta Calculation Flow: End to End

## 1. Origin: `apply_overrides()` in `api/src/manicure/overrides.py`

**Lines 440-576.**

`chars_before` is computed at line 451 by calling `_count_chars(ir)` on the **original, unmodified IR**. `chars_after` is computed at line 571 by calling `_count_chars(current_ir)` after all overrides have been applied.

Both use `_count_chars()` (lines 148-150), which calls `count_chars_parts()` (lines 134-145) and sums all three components:

```python
def count_chars_parts(ir: InternalRequest) -> tuple[int, int, int]:
    system_chars  = sum(len(sp.text) for sp in ir.system)
    tools_chars   = sum(len(t.name) + len(t.description) + len(json.dumps(t.input_schema)) for t in ir.tools)
    messages_chars = 0
    for msg in ir.messages:
        for block in msg.content:
            messages_chars += len(block.model_dump_json())
    return system_chars, tools_chars, messages_chars
```

Key observations:
- `chars_before` comes from the immutable `original_ir` (never mutated).
- `chars_after` comes from `current_ir`, the accumulated result of sequential override application.
- Per-entry `chars_delta` values inside each transform helper use inconsistent counting methods (e.g., `len(block.model_dump_json())` vs `len(block.text)`), so `sum(entry.chars_delta)` will not always equal `chars_after - chars_before`.

## 2. OverrideAudit Model (lines 112-128)

```python
class OverrideAuditEntry(BaseModel):
    model_config = ConfigDict(frozen=True)
    kind: str
    target: str
    applied: bool
    chars_delta: int

class OverrideAudit(BaseModel):
    entries: list[OverrideAuditEntry]
    chars_before: int
    chars_after: int

    @property
    def chars_delta(self) -> int:
        return self.chars_after - self.chars_before
```

**Missing fields that would enable per-component breakdowns:**

| Field | Source |
|---|---|
| `system_chars_before/after` | `count_chars_parts(ir)[0]` |
| `tools_chars_before/after` | `count_chars_parts(ir)[1]` |
| `messages_chars_before/after` | `count_chars_parts(ir)[2]` |

Also missing from `OverrideAuditEntry`: no `component` field to classify which IR section an entry affects.

## 3. API Layer: `_update_paused_preview()` in `api/src/manicure/api/v1/overrides.py` (lines 49-73)

```python
async def _update_paused_preview():
    paused = await bp.get_paused()
    pf = next(iter(paused.values()))
    if not store.enabled:
        audit = identity_audit(pf.original_ir)
        curated_ir = pf.original_ir
    else:
        curated_ir, audit = apply_overrides(store.get_all(), pf.original_ir)
    pf.curated_ir = curated_ir
    pf.audit = audit
    return audit, curated_ir
```

- **Always recomputes from `pf.original_ir`**. No cache, no dirty flag.
- Called from `PATCH /overrides` (line 94), `POST /overrides/toggle` (line 114), and `POST /breakpoint/re-audit/{flow_id}` (breakpoint_routes.py line 137).
- Only processes the first paused flow (`next(iter(paused.values()))`).
- `pf.curated_ir` and `pf.audit` are mutated in place; `pf.original_ir` is never touched.

## 4. SSE Transport: `_handle_breakpoint()` in `api/src/manicure/addon.py` (lines 185-234)

```python
broadcast.emit({
    "type": "paused",
    "flow_id": flow.id,
    "ir": curated_ir.model_dump(mode="json"),
    "original_tools": [t.model_dump(mode="json") for t in original_ir.tools],
    "audit": audit.model_dump(mode="json") if audit else None,
    "paused_at_ms": paused_at_ms,
})
```

**Included:** `flow_id`, full curated IR, original tools only, audit (entries + chars_before/after), timestamp.

**Not included:** Per-component breakdown, `original_ir.system`, `original_ir.messages`, `tokens_approx`.

The SSE event fires immediately on pause, before the user acts. `audit.model_dump()` will automatically pick up any new fields added to the model.

## 5. Frontend Consumption

### EditorActions.tsx (lines 58-61)

```ts
const originalChars = audit?.chars_before ?? countChars(originalIr);
const editedChars   = audit?.chars_after  ?? countChars(editedIr);
const delta         = editedChars - originalChars;
const deltaPct      = originalChars > 0
    ? Math.round((Math.abs(delta) / originalChars) * 100) : 0;
```

- Uses `audit.chars_before/after` when audit is present (normal path during breakpoint).
- Falls back to local `countChars()` when audit is null (initial state or after clear).
- `audit` is local state inside `BreakpointEditor`, not synced back to Zustand store.

### countChars() (EditorActions.tsx lines 22-35)

Private function mirroring the backend's `count_chars_parts`. Sums system + tools + messages. Uses `JSON.stringify(block)` instead of `model_dump_json()`.

### ExchangeCard.tsx (lines 11-18)

Post-hoc display uses `JSON.stringify` of full IR objects (includes envelope fields like `model`, `provider`, etc.), making the denominator even larger. Same dilution problem.

### State flow

1. SSE `"paused"` event sets `pausedFlow.audit` in Zustand `uiStore`.
2. `BreakpointEditor` initializes local `audit` state from `pausedFlow.audit`.
3. Every `handleUpsert`/`handleToggle` fetches fresh audit from backend response.
4. `handleClear` calls `reauditFlow()` and refreshes audit explicitly.

## 6. Root Cause

**The denominator includes messages_chars, which are not bulk-overridable.**

The formula divides the absolute char delta by `originalChars = system + tools + messages`. In a typical Claude Code session, `messages` (full conversation history, tool calls, results) is 80-90% of the total. System and tools are the overridable sections.

Example: `system=5000, tools=3000, messages=40000, total=48000`. User disables 50% of system blocks, removing 2500 chars. Delta: `2500/48000 = 5.2%`. The user removed half the system context but sees a single-digit percentage.

## 7. Race Conditions and Stale Data

| Risk | Status |
|---|---|
| Stale override accumulation | **None.** Always recomputes from immutable `original_ir`. |
| `_store` concurrent access | **Safe in practice.** Both mitmproxy hook and FastAPI router share the same asyncio event loop (single-threaded). |
| SSE event vs forwarded IR divergence | **By design.** The emitted `"ir"` in the SSE event may differ from the actually-forwarded IR if overrides change while paused. |
| Broadcast queue overflow | **Possible.** Queue full (maxsize=1000) silently drops events. Unlikely during normal operation. |

## 8. Recommended Fix: Per-Component Breakdown

### Backend: Extend OverrideAudit

```python
class OverrideAudit(BaseModel):
    entries: list[OverrideAuditEntry]
    chars_before: int
    chars_after: int
    system_chars_before: int
    system_chars_after: int
    tools_chars_before: int
    tools_chars_after: int
    messages_chars_before: int
    messages_chars_after: int
```

### Backend: Update apply_overrides() (lines 451, 571)

Replace `_count_chars()` with `count_chars_parts()`:

```python
# line 451
sys_before, tools_before, msgs_before = count_chars_parts(ir)
chars_before = sys_before + tools_before + msgs_before

# line 571
sys_after, tools_after, msgs_after = count_chars_parts(current_ir)
chars_after = sys_after + tools_after + msgs_after
```

Pass all six values into the `OverrideAudit` constructor.

Also update `identity_audit()` (line 384) to use `count_chars_parts()`.

### Frontend: Compute meaningful percentage

```ts
const overridableCharsBefore = (audit.system_chars_before + audit.tools_chars_before);
const overridableCharsAfter  = (audit.system_chars_after  + audit.tools_chars_after);
const delta = overridableCharsAfter - overridableCharsBefore;
const deltaPct = overridableCharsBefore > 0
    ? Math.round((Math.abs(delta) / overridableCharsBefore) * 100) : 0;
```

Or display per-component deltas individually for maximum transparency.

### SSE: No changes needed

`audit.model_dump(mode="json")` automatically serializes any new fields.

### Injection points summary

| File | Lines | Change |
|---|---|---|
| `api/src/manicure/overrides.py` | 112-128 | Add 6 per-component fields to `OverrideAudit` |
| `api/src/manicure/overrides.py` | 384 | Update `identity_audit()` |
| `api/src/manicure/overrides.py` | 451, 571 | Replace `_count_chars()` with `count_chars_parts()` |
| `www/src/components/editor/EditorActions.tsx` | 58-61 | Use per-component fields for denominator |
| `www/src/components/detail/ExchangeCard.tsx` | 11-18 | Same denominator fix for post-hoc display |
