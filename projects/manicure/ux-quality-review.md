---
title: "Chars/Delta Display: UX and Quality Review"
type: research
tags: [manicure, ux, breakpoint-editor, stats, delta, tokens]
summary: Deep review of the chars/delta status display in the breakpoint editor, identifying the denominator problem and recommending a component-aware stats panel.
status: active
source: codebase-analyst
confidence: high
created: 2026-04-14
updated: 2026-04-14
---

## Executive Summary

The breakpoint editor's stats display (CHARS / DELTA in `EditorActions.tsx`) computes a single percentage against the total payload character count, including non-overridable message history. When a user has dozens of overrides active that strip 80% of tools and system content, the displayed delta can read "-3%" because message history dwarfs everything else. The signal the user actually needs when deciding forward/drop/modify is buried.

The backend already tracks per-override `chars_delta` in `OverrideAuditEntry`, and the `count_chars_parts` function separates system, tools, and messages into distinct buckets. The data to solve this is available today; the frontend simply does not surface it.

---

## 1. Current Implementation

### 1.1 Data Flow

1. **Backend** (`overrides.py:440-576`): `apply_overrides()` walks every `Override` in priority order, producing an `OverrideAudit` with:
   - `chars_before` / `chars_after`: total IR character count (system + tools + messages)
   - `entries[]`: each entry records `kind`, `target`, `applied`, and `chars_delta`

2. **Backend** (`overrides.py:148-150`): `_count_chars()` sums `count_chars_parts(ir)`, which returns the tuple `(system_chars, tools_chars, messages_chars)`. This decomposition is used to build `ReqStats` but is not exposed in the audit.

3. **SSE / REST**: The `PausedFlow` sent to the frontend includes the `OverrideAudit` (or `null` if overrides are disabled). The `PausedFlowDetail` REST response mirrors this.

4. **Frontend** (`EditorActions.tsx:58-61`): The component computes:
   ```ts
   const originalChars = audit?.chars_before ?? countChars(originalIr);
   const editedChars   = audit?.chars_after  ?? countChars(editedIr);
   const delta         = editedChars - originalChars;
   const deltaPct      = originalChars > 0
     ? Math.round((Math.abs(delta) / originalChars) * 100)
     : 0;
   ```
   This is a single scalar percentage against the full payload.

### 1.2 What the User Currently Sees

**Row 1 (EditorActions L77-108)**: Override count, toggle, delta percentage inline, clear button.
```
[toggle] * 12 overrides active . -3%   [Clear All]
```

**Row 2 (EditorActions L140-164)**: Provider/model, absolute char count, delta percentage.
```
anthropic / claude-sonnet-4-20250514       CHARS 48,291   DELTA -3%
```

**Section headers**: Each section (Messages, System, Tools) shows its own override count badge, but no per-section char reduction.

**Individual items**: ToolRow shows per-tool char count (`toolCharCount`). SystemCard shows `part.text.length`. BlockRow shows `JSON.stringify(block).length`. All display the *original* size, not the delta.

### 1.3 Post-Exchange Stats (ExchangeCard)

After forwarding, the `ExchangeCard` has a "Pipeline" tab that shows:
- A `CompressionBar` (before/after visual bar)
- Three `TokenStat` cells: before, after, saved (in chars)
- Per-override entries with individual `chars_delta`

This is the gold standard visualization, but it is only visible *after* the request has been forwarded. The user making the decision never sees it.

---

## 2. The Delta Denominator Problem

### 2.1 The Core Issue

Overrides affect three categories of content with very different proportions:

| Category | Typical Proportion | Overridable? |
|---|---|---|
| Messages (conversation history) | 60-90% of total chars | Partially (block toggle, text edit, strip thinking) |
| Tools (definitions + schemas) | 5-30% of total chars | Yes (toggle, description edit) |
| System (prompt parts) | 5-20% of total chars | Yes (toggle, text edit) |

When the user disables 40 out of 50 tools, that might remove 25% of tool chars, which is only 7% of tools-as-a-fraction-of-total, resulting in maybe 2% of the total payload. The percentage is technically accurate but fails to communicate the magnitude of what the user did.

### 2.2 The Audit Already Has Per-Override Deltas

Each `OverrideAuditEntry` carries `chars_delta`. The frontend receives this data via `audit.entries` but only uses the aggregate `chars_before` / `chars_after` for display. The per-entry deltas are available and unused in the editor view.

### 2.3 `count_chars_parts` Returns a Decomposed Tuple

The backend function (`overrides.py:134-145`) already separates the three components:
```python
def count_chars_parts(ir: InternalRequest) -> tuple[int, int, int]:
    return system_chars, tools_chars, messages_chars
```

This decomposition powers `ReqStats` (used in the exchange list) but is not included in `OverrideAudit`. Adding it would be a small change.

---

## 3. Evaluation of Options

### Option A: Delta Relative to Overridable Content Only

**Concept**: Exclude message chars from the denominator when computing the percentage.

**Problem**: Messages *are* overridable (block toggle, text edit, strip thinking). The "overridable" boundary is not a clean system/tools vs. messages split. Some users strip thinking blocks from messages, which can be enormous. This framing is misleading in the other direction.

**Verdict**: Reject. The overridable/non-overridable split does not map cleanly to content categories.

### Option B: Show Absolute Char Reduction Alongside Percentage

**Concept**: Display something like `DELTA -14,200 (-3%)`.

**Improvement**: The absolute number gives a sense of magnitude even when the percentage is small. 14K chars removed is clearly significant regardless of the percentage.

**Limitation**: Still a single aggregate number. Does not tell the user *where* the reduction came from.

**Verdict**: Partial improvement. Easy to implement. Should be the minimum change.

### Option C: Per-Component Deltas

**Concept**: Show system, tools, and messages as separate stats with individual deltas.

```
SYSTEM  2,400 (-62%)   TOOLS  8,100 (-78%)   MSGS  37,791 (0%)
```

**Strength**: The user immediately sees that tools were compressed by 78% even though total payload only dropped 3%. This directly answers "what did my overrides do?"

**Complexity**: Requires the backend to include per-component chars in the audit, or the frontend to compute them from the before/after IRs (which it already has as `originalIr` and `editedIr`).

**Verdict**: Strong recommendation. The data is already available on the frontend (`countChars` could be refactored to return the tuple). The backend `count_chars_parts` could also be exposed in the audit for authoritative numbers.

### Option D: Both Overridable and Total Percentages

**Concept**: Two percentage displays, one for "context you control" and one for total.

**Problem**: Same as Option A; the boundary is not well-defined.

**Verdict**: Reject.

### Option E: Compression Summary Panel (Recommended)

**Concept**: Replace the single CHARS/DELTA line with a mini version of the ExchangeCard's Pipeline tab. This already exists in the codebase (`CompressionBar`, `TokenStat`) and is proven effective post-exchange. Bring it forward to the decision point.

**Implementation sketch**:
1. Compute per-component chars on the frontend (already have both IRs).
2. Show a compact 3-column stat row: system / tools / messages, each with absolute count and delta.
3. Show the aggregate compression bar below.
4. Optionally, group override entries by kind in a collapsible detail section (the `audit.entries` data is already on the frontend).

The `EditorActions` Row 2 currently occupies ~40px of vertical space. A component-aware panel could fit in ~80px without scrolling, since it replaces the current uninformative display.

---

## 4. Chars vs. Tokens

### 4.1 Current State

- The frontend shows only character counts.
- The backend `_build_pipeline_stats` (addon.py:266) computes a rough token estimate: `tokens_approx = abs(audit.chars_delta) // 4`. This is stored in `PipelineStats.tokens_approx` but not shown during the breakpoint decision.
- `ResStats` includes actual token counts from the provider response (`input_tokens`, `output_tokens`, `cache_read_input_tokens`), but these are only available after the response arrives.

### 4.2 Tradeoffs

| Metric | Pros | Cons |
|---|---|---|
| Characters | Instant, deterministic, no tokenizer dependency | Not what the provider bills on; 1 char != 1 token |
| Estimated tokens (chars/4) | Closer to billing reality | Inaccurate for non-Latin scripts, code, JSON; false precision |
| Actual tokens (tiktoken/etc.) | Accurate | Requires tokenizer in the browser or a round-trip; model-specific |

### 4.3 Recommendation

**Keep characters as primary, add estimated tokens as secondary.**

Rationale:
- The user's decision at the breakpoint is qualitative: "did my overrides significantly reduce context?" The relative magnitude matters more than exact token counts.
- Characters are deterministic and free to compute. The `/4` approximation is good enough for a directional signal.
- Actual tokenization would require bundling a tokenizer (tiktoken is ~4MB for the WASM build) or adding latency. The payoff does not justify the cost for a real-time editing UI.
- The response's actual token counts (already shown in ExchangeCard's TokenBar) provide ground truth after the fact.

A practical display:
```
SYSTEM  2,400 chars (~600 tk)   TOOLS  8,100 chars (~2K tk)   MSGS  37,791 chars (~9.4K tk)
```

The `~` prefix signals estimation. This is the same pattern the backend already uses with `tokens_approx`.

---

## 5. World-Class Standard: What is Missing

### 5.1 Comparison with Industry Tools

Power-user prompt engineering tools (Anthropic Workbench, LangSmith, Braintrust) typically show:

1. **Token budget**: How close to the model's context window the request is. Manicure knows the model name but does not display context window utilization.
2. **Cost estimate**: Approximate cost of the request. Manicure has no pricing data.
3. **Cache hit prediction**: Whether cache_control markers will trigger a cache hit. Manicure shows `cached` badges on system parts but does not predict the financial impact.
4. **Diff view**: Side-by-side or inline diff of original vs. modified content. Manicure has `OriginalPreview` for individual items but no aggregate diff.

### 5.2 Information the User Needs at the Decision Point

When staring at the "Forward / Pass Through / Drop" buttons, a power user wants to know:

1. **What changed**: Which overrides applied, what they removed/modified, and how much. (Partially available in section headers as override counts, but no aggregate summary.)
2. **How much was removed**: In terms they care about (chars, estimated tokens, percentage of overridable content). (Currently: a single unhelpful percentage.)
3. **Context window utilization**: How full is the model's context? Am I at 80% or 20%? (Not available.)
4. **Risk assessment**: Did any overrides fail to apply? (`applied: false` entries exist in the audit but are not surfaced.)
5. **Quick comparison**: What does the modified request look like vs. original? (Available per-item but not at aggregate level.)

### 5.3 Low-Hanging Improvements

Ranked by impact/effort ratio:

1. **Per-component char stats in Row 2** (Option C). Frontend-only change. The `countChars` function in `EditorActions.tsx` already iterates system, tools, and messages separately (L22-34). Refactor it to return three values instead of one. Display as three stat groups with individual deltas.

2. **Show failed overrides**. Filter `audit.entries` for `applied === false` and display a warning. The data is already on the frontend. A `0 applied` or "1 override did not match" indicator would prevent silent failures.

3. **Absolute char reduction in aggregate**. Add the raw char count next to the percentage: `DELTA -14.2K (-3%)`. This is a one-line change in `EditorActions.tsx`.

4. **Estimated token count**. Apply the `/4` heuristic to the per-component chars. No backend change needed.

5. **Compression bar in editor**. Reuse the existing `CompressionBar` component from `detail/CompressionBar.tsx` in the editor's Row 2 area. The props are identical: `savedPct`, `before`, `after`.

---

## 6. Specific Code Observations

### 6.1 Duplicate `countChars` Logic

`EditorActions.tsx:22-35` reimplements `count_chars_parts` from the backend. The frontend version differs slightly in message serialization (`JSON.stringify(block)` vs. `block.model_dump_json()`). This could diverge over time. Consider:
- Having the backend include per-component chars in the audit response, eliminating the frontend calculation entirely.
- Or at minimum, aligning the serialization approach.

### 6.2 ExchangeCard's `savedPct` Uses JSON.stringify on Full IRs

`ExchangeCard.tsx:11-16`:
```ts
const totalBefore = detail.request_curated_ir
  ? JSON.stringify(detail.request_ir).length
  : (pipeline?.chars_before ?? 0);
```

This computes total before/after by stringifying the entire IR objects, which includes metadata, sampling params, and structural JSON overhead (keys, brackets, commas) that are not part of the content the user controls. This is a different denominator than `_count_chars` in the backend, which only counts content fields. The two numbers will never match. For consistency, ExchangeCard should prefer `pipeline.chars_before` / `pipeline.chars_after` when available and only fall back to JSON.stringify for manually-edited IRs where no pipeline ran.

### 6.3 `tokens_approx` is Computed But Unused in the UI

`addon.py:266`:
```python
tokens_approx=abs(audit.chars_delta) // 4,
```

This is stored in `PipelineStats` and available via the REST API, but neither `ExchangeCard` nor `EditorActions` displays it. If estimated tokens are going to be a first-class metric, this value should be surfaced.

### 6.4 Section Headers Show Override Counts But Not Char Impact

Each section (System, Tools, Messages) shows how many overrides are active in that section. For example, `ToolsSection.tsx:222-224`:
```ts
const totalOverrides = overrides.filter(
  (o) => o.kind === "tool_toggle" || o.kind === "tool_description",
).length;
```

But there is no indication of the char impact. The `audit.entries` array could be filtered by `kind` to sum up `chars_delta` per section, producing something like: `Tools . 50 . 12 overrides . -28.4K`

---

## 7. Recommended Implementation Priority

| Priority | Change | Effort | Impact |
|---|---|---|---|
| P0 | Refactor `countChars` to return `{system, tools, messages}` tuple; display per-component stats in Row 2 | Small (frontend only) | High: directly addresses the denominator problem |
| P0 | Show absolute char reduction alongside percentage | Trivial | Medium: gives immediate sense of magnitude |
| P1 | Show per-section char delta in section headers using `audit.entries` | Small (frontend only) | Medium: connects overrides to their impact |
| P1 | Surface `applied === false` audit entries as a warning | Small (frontend only) | Medium: prevents silent override failures |
| P2 | Add estimated token counts (`/4` heuristic) | Small | Low-medium: directional signal, not critical |
| P2 | Reuse `CompressionBar` in editor view | Small (frontend only) | Medium: visual consistency with post-exchange view |
| P3 | Add per-component chars to `OverrideAudit` on the backend | Small (backend) | Medium: eliminates frontend/backend char count divergence |
| P3 | Fix ExchangeCard's JSON.stringify denominator inconsistency | Small | Low: correctness fix, not user-visible in most cases |

---

## 8. Key File Reference

| File | Purpose | Lines of Interest |
|---|---|---|
| `www/src/components/editor/EditorActions.tsx` | CHARS/DELTA display | L22-35 (countChars), L58-61 (computation), L147-161 (render) |
| `www/src/components/editor/BreakpointEditor.tsx` | Orchestrates editor, passes audit | L31 (audit state), L136-150 (EditorActions props) |
| `api/src/manicure/overrides.py` | Override engine | L121-128 (OverrideAudit), L134-150 (count_chars_parts), L440-576 (apply_overrides) |
| `api/src/manicure/addon.py` | Pipeline stats | L42-53 (_build_req_stats), L258-267 (_build_pipeline_stats) |
| `www/src/components/detail/ExchangeCard.tsx` | Post-exchange stats (Pipeline tab) | L11-18 (savedPct), L114-147 (compression display) |
| `www/src/components/detail/CompressionBar.tsx` | Visual compression bar | L4-45 (reusable component) |
| `www/src/components/detail/TokenBar.tsx` | Token breakdown bar | L6-72 (TokenBar), L74-104 (TokenStat) |
| `www/src/components/editor/ToolsSection.tsx` | Tool group with char counts | L21-23 (toolCharCount), L174-178 (group chars display) |
| `www/src/components/editor/SystemSection.tsx` | System part cards | L46 (sizeLabel per part) |
