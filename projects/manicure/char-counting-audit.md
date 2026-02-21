---
title: Char Counting Audit
type: research
tags: [manicure, char-counting, delta, overrides, audit]
summary: Audit of backend (Python) and frontend (TypeScript) char counting implementations, identifying parity gaps, per-override delta inconsistencies, and accuracy vs actual LLM context consumption.
status: active
source: codebase-analyst
confidence: high
created: 2026-04-14
updated: 2026-04-14
---

## Executive Summary

Manicure has two char counting implementations (backend Python, frontend TypeScript) that compute a "context size" metric displayed as chars + delta%. The top-level counting logic is structurally equivalent across both sides. However, there are meaningful inconsistencies in how per-override deltas are computed vs how blocks are counted, and the metric itself diverges from actual LLM context consumption for images and structural overhead.

## Implementations

### Backend: `count_chars_parts(ir)` (overrides.py:134-145)

```python
system_chars  = sum(len(sp.text) for sp in ir.system)
tools_chars   = sum(len(t.name) + len(t.description) + len(json.dumps(t.input_schema)) for t in ir.tools)
messages_chars = sum(len(block.model_dump_json()) for msg in ir.messages for block in msg.content)
```

`_count_chars(ir)` (line 148) sums all three.

### Frontend: `countChars(ir)` (EditorActions.tsx:22-35)

```typescript
systemChars   = ir.system.reduce((sum, p) => sum + p.text.length, 0)
toolsChars    = ir.tools.reduce((sum, t) => sum + t.name.length + t.description.length + JSON.stringify(t.input_schema).length, 0)
messagesChars = sum of JSON.stringify(block).length for each block in each message
```

### Usage Context

- `apply_overrides` (line 451, 571) calls `_count_chars()` independently for `chars_before` and `chars_after`. These totals are always correct.
- `EditorActions` (line 58-59) uses `audit.chars_before / chars_after` when available, falling back to `countChars()` when no audit exists.
- Per-override `chars_delta` entries are informational. `sum(entry.chars_delta)` is **not guaranteed** to equal `chars_after - chars_before`.

## Component Analysis

### System Parts

| Aspect | What's counted | What exists on the model |
|--------|---------------|------------------------|
| Backend | `len(sp.text)` | `type`, `text`, `cache_hint`, `provider_data` |
| Frontend | `p.text.length` | same fields |

**Verdict: Parity OK. Accuracy acceptable.**

- `cache_hint` is a cache control directive, not context. Correct to exclude.
- `provider_data` could carry provider-specific fields that add context (e.g., OpenAI system message `name`). Excluded. Minor gap for exotic payloads.
- `type` is always `"text"`. Constant overhead, correct to exclude.

### Tools

| Aspect | What's counted | What exists on the model |
|--------|---------------|------------------------|
| Backend | `len(name) + len(description) + len(json.dumps(input_schema))` | `name`, `description`, `input_schema`, `provider_data` |
| Frontend | `name.length + description.length + JSON.stringify(input_schema).length` | same fields |

**Verdict: Parity OK. Minor structural overhead missed.**

- `provider_data` excluded. Correct for Anthropic (no extra fields). OpenAI wraps tools in `{"type": "function", "function": {...}}` but that overhead is constant per tool and small.
- `json.dumps()` and `JSON.stringify()` produce equivalent output for dict/object data. Key ordering may differ but lengths are equal for the same data.
- The counted fields represent the semantic content the LLM processes. The wrapping JSON structure adds ~50-80 chars per tool definition. For a 20-tool request, that's ~1-1.5K uncounted chars, negligible against typical tool schema sizes.

### Messages

| Aspect | What's counted | What exists on the model |
|--------|---------------|------------------------|
| Backend | `len(block.model_dump_json())` per block | Full block structure |
| Frontend | `JSON.stringify(block).length` per block | Full block structure |

**Verdict: Parity has a subtle divergence. Accuracy varies by block type.**

#### `model_dump_json()` vs `JSON.stringify()` divergence

In normal operation, data roundtrips through Pydantic before reaching the frontend. Pydantic populates default values:

- `ThinkingBlock.provider_data` defaults to `None`, serialized as `"provider_data":null` (+21 chars)
- `ToolResultBlock.is_error` defaults to `False`, serialized as `"is_error":false` (+16 chars)

The frontend receives the Pydantic-serialized JSON, so these fields arrive as `null`/`false` in JS. `JSON.stringify()` preserves `null` values but omits `undefined`. Since the frontend receives explicit `null` (not `undefined`), the two should match.

**Risk**: If any code path constructs IR objects on the frontend without going through the backend (e.g., optimistic updates), optional fields would be `undefined` and the counts would diverge by ~20 chars per ThinkingBlock.

#### Per block type accuracy

| Block Type | Counted | LLM actually sees | Gap |
|-----------|---------|-------------------|-----|
| TextBlock | `{"type":"text","text":"..."}` | The text content | JSON overhead (~17 chars) per block |
| ToolUseBlock | Full JSON with id, name, input | id + name + serialized input | Accurate proxy |
| ToolResultBlock | Full JSON with tool_use_id, content array, is_error | Text content of results | JSON overhead, but reasonable |
| ThinkingBlock | Full JSON with text + provider_data | Text content (if forwarded) | Reasonable |
| ImageBlock | Full JSON with base64 source | Fixed token cost by image dimensions | **Severely inaccurate** |
| UnknownBlock | Full JSON with raw dict | Unknown | Best effort |

#### Image blocks are the biggest accuracy problem

`JSON.stringify()` on an ImageBlock includes the full base64-encoded source data. A 1MB image produces ~1.3M chars of base64. But LLMs charge a fixed token cost based on image dimensions (e.g., Anthropic: ~1600 tokens for a 1568x1568 image). The char metric is meaningless for images and will dominate the total, making the delta% for text changes invisible.

#### Missing: message role labels

Neither implementation counts `msg.role` ("user"/"assistant"). These are ~4-9 chars per message, negligible.

## Per-Override Delta Inconsistencies

The override functions compute `chars_delta` per entry. These deltas use different measurement methods than `count_chars_parts`, creating inconsistencies.

### `_apply_strip_thinking` (line 158)

- **Delta**: `len(block.text)` per ThinkingBlock removed
- **count_chars_parts** measures: `len(block.model_dump_json())`
- **Gap**: Delta understates reduction. For a ThinkingBlock with 1000 chars of text, `model_dump_json()` produces ~1040 chars (JSON wrapping), but the delta only reports -1000.

### `_apply_message_text` (line 338)

- **Delta**: `len(new_text) - len(block.text)` (raw text difference)
- **count_chars_parts** measures: `len(block.model_dump_json())`
- **Gap**: Works correctly when text has no JSON-special characters. If text contains quotes, backslashes, or control characters, JSON escaping changes the `model_dump_json()` length differently than the raw text length. Edge case, but real.

### `_apply_truncate_tool_result` (line 266)

- **Delta**: `len(truncated_text) - len(original_text)` (raw text)
- **count_chars_parts** measures: `len(block.model_dump_json())` for the entire ToolResultBlock
- **Gap**: Truncation can collapse multiple TextBlocks into one, changing JSON structural overhead. The delta tracks only text content change, missing the structural simplification.

### `_apply_message_block_toggle` (line 317)

- **Delta**: `len(block.model_dump_json())` -- correctly matches `count_chars_parts`. **No gap.**

### `_apply_tool_toggle` (line 190)

- **Delta**: `len(name) + len(description) + len(json.dumps(input_schema))` -- matches `count_chars_parts` tool formula. **No gap.**

### `_apply_system_part_toggle` / `_apply_system_part_text` (lines 236, 251)

- Uses `len(text)` -- matches `count_chars_parts` system formula. **No gap.**

### Impact

The per-entry deltas are advisory only. `chars_before` and `chars_after` in `OverrideAudit` are independently recomputed via `_count_chars()` on the full IR, so **total delta shown to the user is always correct**. The per-entry deltas just won't sum to that total.

## Recommendations

### P0: None required

The system works correctly for its purpose. `chars_before`/`chars_after` are accurate. Backend/frontend parity is maintained in normal operation.

### P1: Consider

1. **Image block handling**: Either exclude ImageBlocks from char count or replace with a fixed token estimate. Current behavior makes the metric unreliable when images are present.

2. **Align per-entry deltas with counting method**: `_apply_strip_thinking` should use `len(block.model_dump_json())` instead of `len(block.text)` for its delta calculation. Same for `_apply_message_text` and `_apply_truncate_tool_result`. This would make `sum(deltas) == chars_after - chars_before`, which is a useful invariant.

### P2: Nice to have

3. **Add a `provider_data` flag**: For tools and system parts with `provider_data`, optionally include those chars. Low priority since `provider_data` is rare in practice.

4. **Document the metric**: Add a comment or docstring clarifying that the char count is an approximation of "context consumed", not a token count, and that it excludes structural JSON overhead and image token costs.
