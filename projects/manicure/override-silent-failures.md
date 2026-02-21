---
title: Override Apply Pipeline — Silent Failure Audit
category: projects
project: manicure
created: 2026-04-14
---

# Override Apply Pipeline: Silent Failure Audit

Audit of `apply_overrides()` in `api/src/manicure/overrides.py:457-601` and its consumption in the frontend.

## 1. Per-kind analysis

### `strip_thinking` (priority 0, line 487)

```python
if isinstance(value, bool) and value:
    current_ir, chars_delta, removed_blk_indices = _apply_strip_thinking(current_ir)
applied = True  # unconditional — outside the if block
```

**Bug.** `applied = True` runs regardless of the `if` branch. Three cases:

| Scenario | What happens | `applied` | `chars_delta` | Correct? |
|---|---|---|---|---|
| `value=True`, thinking blocks exist | Strips them | `True` | negative | Yes |
| `value=True`, no thinking blocks | Runs helper, finds nothing | `True` | `0` | Debatable — target class absent |
| `value=False` | Does nothing | `True` | `0` | **No** — no-op marked applied |

The `value=False` case is a dead-code artifact (a `strip_thinking` override with `value=False` should have been deleted from the store, not applied). Low impact but incorrect semantics.

### `tool_toggle` (priority 1, line 494)

```python
current_ir, chars_delta, applied = _apply_tool_toggle(current_ir, tool_name, value)
```

`_apply_tool_toggle` (line 196):

| Scenario | `applied` | `chars_delta` | Correct? |
|---|---|---|---|
| `enabled=False`, tool exists | `True` | negative | Yes |
| `enabled=False`, tool missing | `False` | `0` | Yes |
| `enabled=True`, any state | `True` | `0` | **No** |

**Bug.** `enabled=True` returns immediately with `(ir, 0, True)` at line 200 without checking whether the tool exists. A re-enable override targeting a tool that was never in the request silently claims success.

### `tool_description` (priority 2, line 501)

All paths correct. `_apply_tool_description` returns `applied=False` when the tool is not found (line 238).

### `system_part_toggle` (priority 3, line 508)

```python
if value:
    applied = True  # unconditional — no bounds check
```

**Bug.** Same pattern as `tool_toggle`. `enabled=True` for index 999 with 3 system parts returns `applied=True`. The disable path correctly bounds-checks via `_apply_system_part_toggle` (line 248).

### `system_part_text` (priority 4, line 525)

All paths correct. `_apply_system_part_text` returns `applied=False` on out-of-bounds (line 261). Removed-index check at line 528 also correct.

### `truncate_tool_result` (priority 5, line 538)

All paths correct. `_apply_truncate_tool_result` returns `applied=False` when the `tool_use_id` is not found (line 318). When found but already shorter than `max_chars`, returns `applied=True, chars_delta=0`, which is semantically valid (constraint satisfied).

### `message_block_toggle` (priority 6, line 545)

```python
if value:
    applied = True  # unconditional — no bounds check
```

**Bug.** Same pattern. `enabled=True` for `msg:99:blk:5` with 2 messages returns `applied=True`. The disable path correctly bounds-checks via `_apply_message_block_toggle` (lines 327-329).

### `message_text` (priority 7, line 566)

All paths correct. `_apply_message_text` returns `applied=False` on out-of-bounds (lines 348-349) and on non-TextBlock targets (line 356). Removed-block check at line 573 also correct.

## 2. The consistent anti-pattern

Three toggle kinds share the same bug:

```python
# tool_toggle (line 200), system_part_toggle (line 511), message_block_toggle (line 549)
if value:  # i.e. enabled=True
    applied = True  # no existence/bounds check
```

The "enable" path treats presence as the default state and returns a no-op success. This is wrong when the target does not exist in the current IR. The fix is to validate that the target exists before claiming `applied=True`:

- `tool_toggle(enabled=True)`: check `any(t.name == tool_name for t in ir.tools)`
- `system_part_toggle(enabled=True)`: check `0 <= index < len(ir.system)`
- `message_block_toggle(enabled=True)`: check bounds on both `msg_idx` and `blk_idx`

## 3. Frontend consumption of `applied`

### EditorActions.tsx (live editor view)

Shows `"{N} overrides active"` from `overrides.length` (the store count). **Never reads `audit.entries` or checks `applied`.** Users see "150 overrides active" with no indication that 138 are no-ops or target missing items.

### ExchangeCard.tsx:155 (post-exchange history view)

```tsx
className={`... ${o.applied ? "" : "opacity-40"}`}
```

This is the **only place** that visually distinguishes applied from non-applied. It dims non-applied entries to 40% opacity. But due to the bugs above, entries that should show as non-applied (`applied=False`) are incorrectly marked `applied=True` when they're enable-toggles targeting missing items. So even this visual signal is unreliable.

### BreakpointEditor.tsx

Passes `audit` to `EditorActions` but never reads `audit.entries` directly.

## 4. Edge cases (requested)

| Case | Result | Correct? |
|---|---|---|
| `tool_toggle(enabled=True)` for existing tool | `applied=True, delta=0` | Semantically fine |
| `tool_toggle(enabled=True)` for non-existent tool | `applied=True, delta=0` | **Wrong** — should be `False` |
| `tool_toggle(enabled=False)` for non-existent tool | `applied=False, delta=0` | Correct |
| `system_part_toggle` for index beyond array length | Enable: `applied=True`. Disable: `applied=False` | Enable is **wrong** |
| `message_block_toggle` for indices beyond array | Enable: `applied=True`. Disable: `applied=False` | Enable is **wrong** |
| `strip_thinking` when no thinking blocks exist | `applied=True, delta=0` | Debatable |

## 5. Proposed contract changes

### Backend: add summary properties to `OverrideAudit`

```python
class OverrideAudit(BaseModel):
    # ... existing fields ...

    @property
    def applied_count(self) -> int:
        return sum(1 for e in self.entries if e.applied)

    @property
    def skipped_count(self) -> int:
        return sum(1 for e in self.entries if not e.applied)

    @property
    def effective_count(self) -> int:
        """Applied entries that actually changed content."""
        return sum(1 for e in self.entries if e.applied and e.chars_delta != 0)
```

Serialize these in the JSON response so the frontend can consume them without iterating entries.

### Frontend: surface skip count in EditorActions

Replace the current display:

```
150 overrides active
```

With:

```
150 overrides · 12 applied · 138 skipped
```

Or more conservatively, only show a warning when `skipped_count > 0`.

### Fix the enable-toggle bug first

The summary counts are only meaningful after fixing the three enable-toggle paths. Without the fix, `skipped_count` will undercount because many skipped overrides are incorrectly marked `applied=True`.

## 6. Priority

1. **Fix enable-toggle `applied` semantics** (3 lines changed in `apply_overrides`, ~5 lines in helpers)
2. **Add summary properties to `OverrideAudit`** (trivial)
3. **Surface skip count in EditorActions** (small frontend change)
4. **Fix `strip_thinking` unconditional `applied=True`** (low priority, minor)
