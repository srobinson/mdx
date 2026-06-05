# Manicure Override Architecture

## Premise

The rules engine is replaced by a direct override model. Users edit request content in the breakpoint editor. Edits produce overrides. Overrides persist across exchanges within a session.

The original intercepted request is never mutated. Every user modification creates a typed override that layers on top.

---

## 1. Override Data Model

### Override Identity

Every override is keyed by a `(kind, target)` tuple. `kind` is the override type. `target` identifies what within the IR is being modified. This tuple is the override's natural primary key: there is exactly one override per `(kind, target)` pair.

### Override Types

```python
from typing import Literal
from pydantic import BaseModel, ConfigDict

OverrideKind = Literal[
    "tool_toggle",
    "tool_description",
    "system_part_toggle",
    "system_part_text",
    "message_text",
    "strip_thinking",
    "truncate_tool_result",
]


class Override(BaseModel):
    """Single user override. Frozen after creation; replaced on update."""
    model_config = ConfigDict(frozen=True)

    kind: OverrideKind
    target: str           # see target-key spec below
    value: str | bool | int | None
    # bool   -> toggles (tool_toggle, system_part_toggle, strip_thinking)
    # str    -> rewrites (tool_description, system_part_text, message_text)
    # int    -> truncation limits (truncate_tool_result)
    # None   -> reset to original (remove this override)
```

### Target Key Specification

| Kind                    | Target format               | Value type | Semantics                                |
|-------------------------|-----------------------------|------------|------------------------------------------|
| `tool_toggle`           | `tool:{tool_name}`          | `bool`     | `false` = tool stripped from request     |
| `tool_description`      | `tool:{tool_name}`          | `str`      | replacement description text             |
| `system_part_toggle`    | `system:{index}`            | `bool`     | `false` = part stripped from request     |
| `system_part_text`      | `system:{index}`            | `str`      | replacement text for this system part    |
| `message_text`          | `msg:{msg_idx}:blk:{blk_idx}` | `str`   | replacement text for a text block        |
| `strip_thinking`        | `global`                    | `bool`     | `true` = all thinking blocks removed     |
| `truncate_tool_result`  | `toolresult:{tool_use_id}`  | `int`      | max chars; content beyond is truncated   |

Target keys are deliberately human readable for debugging. The `tool_toggle` and `tool_description` use the tool name (stable across exchanges) rather than an index (position may shift). System parts use index because they lack a unique identifier. Message blocks use `msg_idx:blk_idx` because that is the only addressing scheme available.

### Why `value: None` means "remove"

Setting `value` to `None` deletes the override from the store. This avoids a separate "delete override" concept. The frontend sends `PATCH {kind, target, value: null}` and the backend drops the entry. Simple lifecycle: create, update, remove.

---

## 2. Override Store

### In-Memory, Session-Scoped

```python
from collections import OrderedDict

class OverrideStore:
    """Session-scoped override state. Lives in the addon process."""

    def __init__(self) -> None:
        self._overrides: OrderedDict[tuple[str, str], Override] = OrderedDict()

    def upsert(self, override: Override) -> None:
        key = (override.kind, override.target)
        if override.value is None:
            self._overrides.pop(key, None)
        else:
            self._overrides[key] = override

    def remove(self, kind: str, target: str) -> bool:
        return self._overrides.pop((kind, target), None) is not None

    def get_all(self) -> list[Override]:
        return list(self._overrides.values())

    def clear(self) -> None:
        self._overrides.clear()
```

**Why `OrderedDict`?** Insertion order determines application order. System part toggles must apply before system part text rewrites. Tool toggles must apply before tool description rewrites. The store preserves the order in which overrides were created, giving deterministic pipeline behavior.

**Why not disk?** Overrides are ephemeral. New proxy launch = clean slate. No persistence needed. No storage backend interaction.

**Why not per-flow?** Overrides are session-global. When you disable `mcp_bash`, it stays disabled for every subsequent paused flow. The store is a singleton in the addon process, not per `PausedFlow`.

### Module Placement

`manicure/overrides.py` at the same level as `rules.py`. The import DAG extends: `ir -> overrides -> pipeline -> ...`

`overrides.py` imports only from `manicure.ir`. No dependency on storage, breakpoint, or server.

---

## 3. Apply Pipeline

### Replacing `pipeline.apply`

The current `pipeline.apply(rules, ir)` loads rules from storage, filters by scope, and applies them sequentially. The override pipeline replaces this entirely.

```python
def apply_overrides(
    overrides: list[Override],
    ir: InternalRequest,
) -> tuple[InternalRequest, OverrideAudit]:
    """Apply all overrides to an IR. Returns new IR + audit."""
```

### Order of Operations

Overrides apply in a fixed priority order, regardless of insertion order:

1. **`strip_thinking`** (global toggle, removes thinking blocks from all messages)
2. **`tool_toggle`** (remove disabled tools)
3. **`tool_description`** (rewrite descriptions on remaining tools)
4. **`system_part_toggle`** (remove disabled system parts)
5. **`system_part_text`** (rewrite text on remaining system parts)
6. **`truncate_tool_result`** (truncate specific tool results)
7. **`message_text`** (rewrite message text blocks)

**Why fixed order?** Toggles must fire before rewrites. If a user disables a tool and also rewrites its description, the disable wins and the rewrite is skipped (target no longer exists). Fixed ordering makes this deterministic without requiring the user to reason about sequencing.

### Missing Target Handling

When an override targets something absent from the incoming request:

- **`tool_toggle` for a tool not in this request**: skip silently. The tool may appear in a future exchange. The override stays in the store.
- **`tool_description` for a missing tool**: skip silently. Same reasoning.
- **`system_part_toggle` for index out of range**: skip silently. System part count may vary between exchanges.
- **`system_part_text` for index out of range**: skip silently.
- **`message_text` for out-of-range indices**: skip silently. Message arrays grow over a session.
- **`truncate_tool_result` for missing `tool_use_id`**: skip silently.

No override is ever removed from the store because the current request lacks its target. The override re-activates when a matching target appears.

### Audit Model

```python
class OverrideAuditEntry(BaseModel):
    model_config = ConfigDict(frozen=True)

    kind: str
    target: str
    applied: bool      # false if target was missing
    chars_delta: int    # positive = added, negative = removed

class OverrideAudit(BaseModel):
    entries: list[OverrideAuditEntry]
    chars_before: int
    chars_after: int

    @property
    def chars_delta(self) -> int:
        return self.chars_after - self.chars_before
```

---

## 4. API Surface

### Override Endpoints

All under `/api/v1/overrides`.

#### `GET /api/v1/overrides`

Returns the full override store state.

```json
{
  "overrides": [
    {"kind": "tool_toggle", "target": "tool:mcp_bash", "value": false},
    {"kind": "tool_description", "target": "tool:Read", "value": "Read a file."}
  ]
}
```

#### `PATCH /api/v1/overrides`

Accepts a batch of override mutations. Each entry is an upsert (or delete if `value` is `null`).

```json
{
  "overrides": [
    {"kind": "tool_toggle", "target": "tool:mcp_bash", "value": false},
    {"kind": "system_part_text", "target": "system:2", "value": null}
  ]
}
```

**Why PATCH with a batch?** A single user action can produce multiple overrides (e.g., toggling a tool off also triggers a re-audit). Batching avoids multiple round trips and ensures atomicity.

Response returns the updated store state plus a fresh audit against the currently paused flow (if any):

```json
{
  "overrides": [...],
  "audit": { "entries": [...], "chars_before": 42000, "chars_after": 38000 },
  "curated_ir": { ... }
}
```

If no flow is currently paused, `audit` and `curated_ir` are `null`. The overrides still apply to the next paused flow.

#### `DELETE /api/v1/overrides`

Clears all overrides. Returns `204`. Used for the "reset all" action in the UI.

### Breakpoint Route Changes

#### `POST /api/v1/breakpoint/release/{flow_id}`

No longer accepts a full `InternalRequest` body. Instead, the server applies overrides from the store to the paused flow's `original_ir` and forwards the result. The release endpoint becomes parameter-less (besides the flow_id).

Alternatively, `release-with-snapshot` could accept an explicit `InternalRequest` for one-off edits that the user does not want persisted as overrides. This preserves the current "edit and send" capability for power users.

#### `POST /api/v1/breakpoint/re-audit/{flow_id}` (replaced)

This endpoint currently re-runs rules. It becomes:

`GET /api/v1/breakpoint/preview/{flow_id}`

Returns `original_ir` with current overrides applied, plus the audit. Used by the frontend to refresh the diff view after any override change.

### SSE Events

The `paused` SSE event continues to carry the full IR and audit. The IR is now `original_ir` with overrides applied (rather than rules-curated IR). The frontend receives both `original_ir` and `curated_ir` to render the diff.

```json
{
  "type": "paused",
  "flow_id": "abc123",
  "original_ir": { ... },
  "curated_ir": { ... },
  "audit": { ... },
  "paused_at_ms": 1713000000000
}
```

---

## 5. Re-audit Equivalent (Stats Refresh)

### Push Model

When overrides change via `PATCH /api/v1/overrides`, the response already includes the fresh `audit` and `curated_ir`. The frontend applies the update immediately. No polling needed.

For cases where the frontend needs to refresh without changing overrides (e.g., after reconnecting), `GET /api/v1/breakpoint/preview/{flow_id}` returns the current state.

### Stats Computation

The `OverrideAudit` provides per-override `chars_delta` and aggregate `chars_before`/`chars_after`. The frontend computes display values (token estimates, percentage savings) client-side from these numbers. No separate stats endpoint needed.

---

## 6. Migration Path

### What Gets Replaced

| Current                        | New                              | Status    |
|--------------------------------|----------------------------------|-----------|
| `rules.py` (Rule model, actions) | `overrides.py` (Override model, apply) | Replace   |
| `pipeline.py` (dispatch, apply)  | `overrides.py` (apply_overrides)       | Replace   |
| `api/v1/rules.py` (CRUD)         | `api/v1/overrides.py` (PATCH/GET/DELETE) | Replace |
| `storage.load_rules/modify_rules` | `OverrideStore` (in-memory)         | Remove    |
| `breakpoint_routes.py` re-audit   | preview endpoint                    | Rework    |

### What Gets Adapted

| Current                        | Change                           |
|--------------------------------|----------------------------------|
| `addon.py` `_run_pipeline`     | Call `apply_overrides` from the store instead of loading rules |
| `addon.py` `_handle_breakpoint` | Pass `original_ir` to SSE, let overrides compute `curated_ir` |
| `breakpoint.py` `PausedFlow`    | Drop `curated_ir` field; compute on demand from `original_ir` + overrides |
| `storage/base.py`               | Remove `load_rules` and `modify_rules` from `StorageBackend` |
| SSE `paused` event              | Include both `original_ir` and `curated_ir` |
| Frontend rules panel             | Remove entirely; override UI lives in the editor |

### What Stays Untouched

- `ir.py` (no changes to the IR model)
- `adapters/` (inbound/outbound parsing unchanged)
- `storage/` index and exchange persistence (only rules methods removed)
- `broadcast.py` (SSE infrastructure unchanged)

### Action Function Reuse

The pure transform functions in `rules.py` (`strip_tools`, `strip_thinking`, `rewrite_tool_description`, etc.) contain working logic. Extract them into `overrides.py` as internal helpers, stripped of the `Rule`/`RuleScope` scaffolding. The functions themselves are fine; only their wrapping changes.

### Incremental Approach

1. Add `overrides.py` with the `Override` model, `OverrideStore`, and `apply_overrides`
2. Add `api/v1/overrides.py` with the PATCH/GET/DELETE endpoints
3. Wire `apply_overrides` into the addon alongside the existing pipeline (feature flag or config toggle)
4. Update frontend to use override endpoints instead of rules CRUD
5. Remove `rules.py`, `pipeline.py`, `api/v1/rules.py`, and storage rules methods
6. Remove the rules panel from the frontend
