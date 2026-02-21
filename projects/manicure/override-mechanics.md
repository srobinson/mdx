# Override Mechanics Deep Dive

> Manicure intercepts LLM API requests and lets users modify them via "overrides" before forwarding. This document maps the full override system: types, data model, apply pipeline, char counting, and quality assessment.

## Architecture Overview

Overrides replace a traditional rules engine with direct user edits. When a request is paused at a breakpoint, the user modifies it in a browser-based editor. Each edit produces a typed `Override` that persists in a session-scoped `OverrideStore`. On resume (or on the next request if no breakpoint is active), all stored overrides are applied to the original IR via `apply_overrides()`.

**Data flow:**
```
Client request
  -> Adapter parses to InternalRequest (frozen Pydantic model)
    -> OverrideStore.get_all() collects active overrides
      -> apply_overrides(overrides, ir) produces (curated_ir, audit)
        -> curated_ir forwarded to LLM provider
```

The IR is immutable (`frozen=True`). Every override produces a new IR instance via `model_copy(update={...})`. No mutation ever occurs.

---

## Override Taxonomy

Eight override kinds exist, defined as a `Literal` union (`OverrideKind`):

| Kind | Target Format | Value Type | Effect | Char Delta |
|------|--------------|------------|--------|------------|
| `strip_thinking` | `"global"` | `bool` | Removes all `ThinkingBlock` entries from every message | Subtractive |
| `tool_toggle` | `"tool:{name}"` | `bool` | `false` removes the tool definition entirely | Subtractive |
| `tool_description` | `"tool:{name}"` | `str` | Replaces the tool's description text | Additive or subtractive |
| `system_part_toggle` | `"system:{index}"` | `bool` | `false` removes the system part at original index | Subtractive |
| `system_part_text` | `"system:{index}"` | `str` | Replaces the system part's text content | Additive or subtractive |
| `truncate_tool_result` | `"toolresult:{tool_use_id}"` | `int` (>0) | Truncates a tool result to N chars, appends `" [truncated]"` | Subtractive (net) |
| `message_block_toggle` | `"msg:{idx}:blk:{idx}"` | `bool` | `false` removes the content block at original indices | Subtractive |
| `message_text` | `"msg:{idx}:blk:{idx}"` | `str` | Replaces a `TextBlock`'s text content | Additive or subtractive |

### Value semantics

- `bool` values: `false` disables/removes, `true` is a no-op (re-enables). Only `false` produces a char delta.
- `str` values: The replacement text. Delta depends on length difference vs. original.
- `int` values: Truncation limit in characters. Must be `> 0`.
- `None`: Sentinel that removes the override from the store (not applied to IR).

---

## Data Model

### Override (Pydantic, frozen)

```python
class Override(BaseModel):
    kind: OverrideKind          # one of 8 literal strings
    target: str                 # addressing scheme varies by kind
    value: str | bool | int | None
```

Keyed by `(kind, target)` in the store. Upserting with `value=None` deletes the entry.

### OverrideStore

Session-scoped singleton. `OrderedDict[tuple[str, str], Override]` preserving insertion order. Has a global `enabled` toggle that bypasses all overrides when `False` (returns the original IR with an identity audit).

### OverrideAudit

Produced alongside every `apply_overrides()` call:

```python
class OverrideAuditEntry:
    kind: str
    target: str
    applied: bool        # False if target was missing or already removed
    chars_delta: int     # positive = added, negative = removed

class OverrideAudit:
    entries: list[OverrideAuditEntry]
    chars_before: int    # total chars of original IR
    chars_after: int     # total chars of curated IR
```

`chars_delta` is a computed property: `chars_after - chars_before`.

---

## Apply Pipeline

`apply_overrides()` (`overrides.py:440`) is the core function. All overrides execute in a **fixed priority order**, not insertion order:

```
0: strip_thinking
1: tool_toggle
2: tool_description
3: system_part_toggle
4: system_part_text
5: truncate_tool_result
6: message_block_toggle
7: message_text
```

**Design rationale:** Toggles (removals) fire before rewrites. Global operations fire before targeted ones. This prevents rewrites from targeting items that no longer exist.

### Index Adjustment

The trickiest aspect of the pipeline. Index-based overrides (`system_part_*`, `message_block_toggle`, `message_text`) always refer to positions in the **original** IR. When earlier overrides remove items, later overrides must adjust their indices.

Two tracking structures handle this:

1. **`removed_system_indices: set[int]`**: Tracks which original system part indices were removed by `system_part_toggle`. `_adjust_system_index()` subtracts the count of removed indices below the target index.

2. **`removed_blk_indices: dict[int, set[int]]`**: Per-message tracking of removed block indices from `strip_thinking` and `message_block_toggle`. `_adjust_blk_index()` returns `None` if the target block itself was removed, otherwise returns the shifted position.

Example: Original system `[A, B, C, D]`. Remove index 0 and index 2.
- Index 0 removes A directly. `removed = {0}`.
- Index 2: `_adjust_system_index(2, {0})` = `2 - 1` = `1`. Removes C (now at position 1). Correct.
- Result: `[B, D]`.

### Per-kind Application Logic

**`strip_thinking`**: Iterates all messages, removes `ThinkingBlock` instances, records removed block indices per message. Returns the removed indices map so later `message_text` and `message_block_toggle` can adjust.

**`tool_toggle`**: Filters the tools list by name. `enabled=True` is a no-op (the tool already exists). `enabled=False` removes the matching tool and accumulates `name + description + json.dumps(input_schema)` chars.

**`tool_description`**: Finds the tool by name, replaces `description` field. Delta = `len(new) - len(old)`.

**`system_part_toggle`**: Pops the system part at the adjusted index. Checks `removed_system_indices` first to skip already-removed targets. Adds original index to the tracking set on success.

**`system_part_text`**: Replaces `.text` at the adjusted index. Skips if the original index was already removed.

**`truncate_tool_result`**: Finds the `ToolResultBlock` by `tool_use_id` across user messages. Concatenates all `TextBlock` content within the result, truncates to `max_chars`, appends `" [truncated]"` marker. Only applies when the original text exceeds the limit. Collapses multi-block content into a single `TextBlock`.

**`message_block_toggle`**: Removes a content block at adjusted indices. Adds the original block index to `removed_blk_indices` tracking.

**`message_text`**: Replaces a `TextBlock`'s text at adjusted indices. Only applies to `TextBlock` instances; skips `ToolUseBlock`, `ToolResultBlock`, etc.

---

## Char Counting

`count_chars_parts()` breaks the count into three categories:

- **System chars**: `sum(len(sp.text) for sp in ir.system)`
- **Tools chars**: `sum(len(t.name) + len(t.description) + len(json.dumps(t.input_schema)) for t in ir.tools)`
- **Messages chars**: `sum(len(block.model_dump_json()) for block in msg.content for msg in ir.messages)`

The system and tools counting is "bare text" while messages uses `model_dump_json()` serialization. This means:

1. **System parts**: Only `.text` counted. `cache_hint` and `provider_data` excluded. Under-counts if these carry significant content.
2. **Tools**: `name + description + json.dumps(input_schema)`. `provider_data` excluded. Under-counts similarly.
3. **Messages**: Full JSON serialization of each block. Includes type discriminators, field names, JSON syntax characters. This is the most accurate count but measures different things than the system/tools counting.

### Inconsistency: messages use `model_dump_json()` while system/tools use `len(text)`

This is intentional for a "rough character count" (per the docstring) but means char deltas for message blocks include JSON overhead while system/tool deltas do not. The `tool_toggle` removal delta, for example, counts `name + description + json.dumps(schema)` but not the JSON envelope around the tool definition itself.

---

## Disable vs. Remove

Two distinct concepts with different semantics:

| Operation | Mechanism | Effect | Reversibility |
|-----------|-----------|--------|---------------|
| **Disable** (toggle) | `Override(kind="*_toggle", value=False)` | Item removed from IR before sending to provider | Override persists in store; can be re-enabled by upserting with `value=None` to remove the override |
| **Remove** (from store) | `Override(kind=..., value=None)` or `store.remove(kind, target)` | Override deleted from store; original IR item reappears on next application | Permanent within the session |

The frontend `useEditableOverride` hook makes this concrete: toggling "off" sends `value: false`, toggling "on" sends `value: null` (which removes the override). There is no persistent "enabled but present" state; un-toggling deletes the override entirely.

For text overrides, resetting sends `value: null` for both the text override and any associated toggle override.

---

## Integration Points

### Breakpoint Flow

When a request hits a breakpoint:
1. `PausedFlow` stores `original_ir` and `curated_ir` (initially equal)
2. User edits in the UI produce `PATCH /v1/overrides` calls
3. Each PATCH applies all stored overrides to the `original_ir` and updates `PausedFlow.curated_ir` and `.audit`
4. On resume, `curated_ir` is forwarded to the provider

The `_update_paused_preview()` helper in the overrides API always re-applies **all** overrides from scratch. No incremental application.

### Addon Pipeline

In the addon (`addon.py:175`), `apply_overrides()` is called during `request()`. If the store is disabled or empty, the original IR passes through. Failures are caught and logged; the original IR is forwarded on exception.

### Storage

The `OverrideAudit` is converted to `PipelineStats` for storage alongside each exchange. This persists `overrides_applied`, `chars_before`, `chars_after`, and an approximate token count.

---

## Quality Assessment

### Strengths

1. **Immutability discipline.** Frozen Pydantic models throughout. The apply pipeline is pure (no side effects). Each helper returns `(new_ir, chars_delta, applied)`. Clean functional style.

2. **Original-index addressing.** Overrides always reference positions in the original IR, with adjustment logic handling cascading removals. This means the UI never needs to recompute targets when other overrides change.

3. **Priority ordering.** Fixed priorities prevent nonsensical interactions (e.g., rewriting a tool's description after disabling it). The ordering is declared as data (`_PRIORITY` dict), not implicit in code flow.

4. **Audit trail.** Every override produces an audit entry recording whether it applied and its char impact. Full before/after accounting.

5. **Comprehensive test coverage.** Tests cover every kind, edge cases (missing targets, out-of-range indices, zero/negative values), priority interactions, and multi-level index shifting.

### Potential Issues

1. **Char count inconsistency across categories.** System/tools use bare text length; messages use `model_dump_json()`. The `chars_before`/`chars_after` totals mix these metrics, making the aggregate "rough" but not directly comparable across categories. Not a correctness bug, but could confuse users comparing delta breakdowns.

2. **`truncate_tool_result` collapses multi-block content.** If a `ToolResultBlock.content` has multiple `TextBlock` entries, truncation concatenates them into a single `TextBlock`. The original block structure is lost. This is probably fine for the truncation use case but would be surprising if someone expected structural preservation.

3. **No validation that `message_text` replacement preserves valid IR.** You can rewrite a text block to empty string, producing a `TextBlock(text="")`. Whether the LLM provider accepts this depends on the provider. No guard against it.

4. **`tool_toggle` with `enabled=True` is marked `applied=True` but does nothing.** The audit entry says it applied, which is semantically correct (the tool is enabled) but could be misleading when there's no corresponding delta. Same for `system_part_toggle(True)` and `message_block_toggle(True)`.

5. **Module-level singleton store.** `_store = OverrideStore()` means the store lives for the process lifetime. The `autouse` fixture resets it in tests, and `DELETE /v1/overrides` clears it. But in production, if the addon process handles multiple sessions (which it likely does not, given mitmproxy's model), overrides would leak. This appears intentional for single-session usage.

### Extensibility

The design is straightforward to extend:
- Add a new `OverrideKind` literal value
- Assign it a priority in `_PRIORITY`
- Write a `_apply_*` helper following the `(ir, ...) -> (ir, delta, applied)` pattern
- Add a case in `apply_overrides()`
- Add the kind to the frontend `OverrideKind` TypeScript union

No interfaces or registries to update. The priority dict and literal union are the only places that need coordination.
