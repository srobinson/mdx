---
title: Override Store Lifecycle and Cross-Request Behavior
type: research
tags: [manicure, overrides, UX, bugs, lifecycle]
summary: The OverrideStore is a process-lifetime module singleton that persists across all requests; the frontend displays store count, not audit applied count, producing misleading UX on mismatched requests.
status: active
source: codebase-analyst
confidence: high
created: 2026-04-14
updated: 2026-04-14
---

# Override Store Lifecycle and Cross-Request Behavior

Investigation of the override store persistence model and the UX bug where 150 stale overrides display as "active" against a request that matches none of them.

## 1. OverrideStore Lifecycle

**Singleton pattern**: `_store = OverrideStore()` at module level (`overrides.py:102`). `get_store()` (line 105) returns it. The store lives for the entire mitmproxy addon process lifetime. There is no per-request, per-flow, or per-session scoping.

**Internal state**: `OrderedDict[tuple[str, str], Override]` keyed by `(kind, target)`. Plus a `_enabled: bool` toggle.

**Clearing mechanisms** (exhaustive list):
- `DELETE /api/overrides` calls `store.clear()` (empties the dict)
- `store.upsert(override)` with `value=None` removes a single entry
- `store.remove(kind, target)` removes a single entry

**Nothing else clears it.** Releasing a paused flow does not touch the store. Starting a new request does not touch the store. Disarming the breakpoint does not touch the store.

## 2. apply_overrides with Non-Matching Targets

When `_apply_tool_toggle` receives a tool name not present in the IR (`overrides.py:196-219`):

```python
for tool in ir.tools:
    if tool.name == tool_name:
        found = True
        # ...
if not found:
    return ir, 0, False  # IR unchanged, 0 delta, applied=False
```

The audit entry records `applied: false, chars_delta: 0`. The IR passes through unmodified.

This pattern holds for all target-specific override kinds:
- **`tool_toggle`/`tool_description`**: `applied=False` if tool name not in `ir.tools`
- **`system_part_toggle`/`system_part_text`**: `applied=False` if index out of range
- **`truncate_tool_result`**: `applied=False` if `tool_use_id` not in messages
- **`message_block_toggle`/`message_text`**: `applied=False` if message/block index invalid
- **`strip_thinking`**: always `applied=True` (unconditional at line 492)

## 3. The "Active" Count Problem

### Frontend display (`EditorActions.tsx:136-146`)

```tsx
{overrides.length > 0 && (
  <span className="text-[13px] text-amber metric-num">
    {overrides.length} override{overrides.length !== 1 ? "s" : ""} active
    {overridableDelta !== 0 && (
      <> &middot; {overridableDelta < 0 ? "−" : "+"}
        {deltaPct}%
      </>
    )}
  </span>
)}
```

**`overrides`** comes from `useOverrides()` which fetches `GET /api/overrides`, which returns `store.get_all()`. This is the full store contents, not filtered by what actually applied.

**The delta** comes from the `OverrideAudit` char counts, which correctly reflect zero impact. So the display reads: `150 overrides active · +0%` (the `+0%` part suppressed because `overridableDelta === 0`).

Actual display: **"150 overrides active"** with no delta indicator, no signal that zero of them matched.

### What should happen

The audit has the data needed to fix this. `audit.entries` contains per-override `applied: boolean`. The count of actually effective overrides is:
```ts
audit.entries.filter(e => e.applied).length
```
This value is never surfaced in the current UI.

## 4. Cross-Request Override Semantics

Overrides fall into two categories based on target stability:

### Potentially cross-request viable (name-based targets)
| Kind | Target format | Cross-request? |
|---|---|---|
| `tool_toggle` | `tool:<name>` | Works if same tool exists in new request |
| `tool_description` | `tool:<name>` | Same |
| `strip_thinking` | `_` (global) | Always applicable |

### Inherently request-specific (index/ID-based targets)
| Kind | Target format | Why request-bound |
|---|---|---|
| `system_part_toggle` | `system:<index>` | System prompt parts differ between requests |
| `system_part_text` | `system:<index>` | Same |
| `truncate_tool_result` | `tool_result:<id>` | Tool use IDs are per-conversation-turn |
| `message_block_toggle` | `msg:<idx>:blk:<idx>` | Message structure differs per request |
| `message_text` | `msg:<idx>:blk:<idx>` | Same |

Index-based overrides are guaranteed to be `applied: false` on a different request (unless by coincidence the same index points at compatible content).

## 5. SSE Re-Pause Flow

Each new pause gets a **fresh audit**. The flow in `ManicureAddon.request()` (`addon.py:337-360`):

1. New request arrives
2. `_run_pipeline(ir, flow.id)` calls `get_store()` and `apply_overrides(store.get_all(), ir)` against the **new** IR
3. Fresh `(curated_ir, audit)` is produced
4. If breakpoint armed, `_handle_breakpoint()` creates a new `PausedFlow` with this fresh audit
5. SSE broadcasts the `"paused"` event with the fresh audit

So the audit is always computed against the current request's IR. There is no audit inheritance from a previous flow. The bug is not stale audit data; it is:
- The store holding overrides that no longer match anything
- The UI counting store size instead of audit applied count

## 6. Scenario Walkthrough

1. **Request A** (Claude Code Opus): 150+ tools, large system prompt. User creates 150 `tool_toggle` overrides.
2. User releases Request A. Store retains 150 overrides.
3. **Request B** (Haiku): 0 tools, 838 chars system, 48 chars messages.
4. `_run_pipeline` applies 150 overrides to Request B. All 150 `_apply_tool_toggle` calls return `(ir, 0, False)`.
5. Audit: 150 entries, all `applied: false, chars_delta: 0`. `chars_before === chars_after`. `tools_chars_before === tools_chars_after === 0`.
6. Frontend shows "150 overrides active" (store count) with no delta (because delta is 0). No indication that zero overrides matched.

## 7. Potential Fix Directions

### Minimal: surface applied count
Show `audit.entries.filter(e => e.applied).length` instead of (or alongside) `overrides.length`. Display something like "3 of 150 overrides applied" or "150 overrides (0 matched)".

### Medium: auto-prune stale overrides
After `apply_overrides`, remove store entries where `applied === false` and the target kind is index-based. Keep name-based overrides (they may match a future request with similar tools).

### Structural: scope overrides to request shape
Tag overrides with the request signature (tool names present, system part count, message count). On new request, mark which overrides are "compatible" vs "orphaned". Let the user decide whether to keep orphaned overrides.

### UX-only: split display
Show two counts in the badge: "3 active · 147 stale" with stale overrides visually muted.
