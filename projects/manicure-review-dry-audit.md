---
title: Manicure Frontend DRY Audit
category: projects
tags: [manicure, code-review, dry, refactoring]
created: 2026-04-13
---

# Manicure Frontend DRY Audit

## Summary

**Duplication severity: 6/10**

The codebase has one literal copy-paste (`colorizeLine`) and a structural duplication pattern across the three editor section components (SystemSection, ToolsSection, MessagesSection) that share toggle/expand/textarea/override logic. The detail view components (ContentBlocks) and editor components (MessagesSection) also share block rendering logic that diverged into read-only vs editable variants. Most other code is well-factored.

## Duplication Inventory

### 1. `colorizeLine` function (literal copy-paste)

**What:** Identical JSON syntax-highlighting function duplicated verbatim.

**Where:**
- `detail/JsonView.tsx:11-67`
- `editor/MessagesSection.tsx:7-55`

Both contain the same regex, the same color classes (`text-sky`, `text-sage`, `text-lavender`, `text-amber`, `text-txt-3`), and the same loop structure. The MessagesSection version is wrapped in a `ColorizedPre` component.

**Suggested extraction:** `lib/colorizeLine.ts` exporting `colorizeLine(line, lineIdx): ReactNode[]` and optionally a `ColorizedPre` component in `components/detail/ColorizedPre.tsx`.

**Impact:** ~60 duplicated lines removed from MessagesSection. Two files simplified.

---

### 2. `blockKey` function

**What:** Near-identical function to generate stable React keys for content blocks.

**Where:**
- `detail/ContentBlocks.tsx:37-46` (exported, uses `tu-`/`tr-` prefixes)
- `editor/MessagesSection.tsx:270-279` (local, uses `block.id`/`result-` prefixes)

**Suggested extraction:** Unify into the existing export in ContentBlocks. The prefix differences are cosmetic; either convention works.

**Impact:** ~10 lines. Minor, but removes a drift risk.

---

### 3. `blockSummary` vs `blockLabel`

**What:** Two functions that summarize a ContentBlock into a one-line string, switching on `block.type`. ~80% identical logic.

**Where:**
- `detail/ContentBlocks.tsx:18-35` (`blockSummary`, 220-char preview)
- `editor/MessagesSection.tsx:94-111` (`blockLabel`, 120-char preview)

**Suggested extraction:** Merge into a single `blockSummary(block, maxPreview?)` in ContentBlocks or `lib/formatting.ts`.

**Impact:** ~15 lines. Eliminates a logic fork that could silently diverge.

---

### 4. Textarea auto-size + override sync pattern (structural duplication)

**What:** Three editor components repeat the same hooks-based pattern:
- `useState` for `expanded`, `localText`
- `useEffect` to sync `localText` from override (with identical deps)
- `useEffect` for textarea auto-height (identical implementation, same biome-ignore comment)
- `commitText`/`commitDesc` on blur (identical commit-or-reset-override logic)
- `handleToggle` (toggle override on/off with same structure)
- `handleReset` (batch-clear overrides with same structure)

**Where:**
- `editor/SystemSection.tsx:28-147` (`SystemCard`)
- `editor/ToolsSection.tsx:60-179` (`ToolRow`)
- `editor/MessagesSection.tsx:143-267` (`BlockRow`)

**Suggested extraction:** A custom hook `useEditableOverride({ originalValue, overrideValue, onOverride, overrideKind, target })` that returns `{ localText, setLocalText, commitText, handleReset, textRef, expanded, setExpanded, checked, handleToggle }`. Alternatively, a `useAutoSizeTextarea(ref, deps)` hook for just the auto-sizing part, paired with a `useOverrideSync(original, override)` hook.

**Impact:** ~120 lines across three files. This is the largest single extraction opportunity.

---

### 5. Override lookup helpers

**What:** Functions to find overrides by kind + target in the overrides array. Same pattern, different parameter signatures.

**Where:**
- `editor/SystemSection.tsx:12-26` (`getToggleOverride`, `getTextOverride` by index)
- `editor/ToolsSection.tsx:40-58` (`getToggleOverride`, `getDescOverride`, `hasOverride` by tool name)
- `editor/MessagesSection.tsx:121-137` (`isBlockToggledOff`, `getTextOverride` by msgIdx/blkIdx)

**Suggested extraction:** A single `overrideLookup(overrides, kind, target)` utility in `lib/overrides.ts` that returns the override value or undefined. Callers compose target strings themselves.

**Impact:** ~40 lines across three files. Removes 6 near-identical helper functions.

---

### 6. Textarea class string

**What:** The same Tailwind class string for editable textareas repeated across four components.

**Where:**
- `editor/SamplingSection.tsx:8-9` (extracted to `inputClass` const, good)
- `editor/SystemSection.tsx:123` (inline)
- `editor/ToolsSection.tsx:153-154` (inline)
- `editor/MessagesSection.tsx:238` (inline)

The string: `"w-full min-h-24 resize-none overflow-hidden bg-canvas px-3 py-2 text-[13px] text-txt border border-edge focus:border-sky/50 focus:outline-none transition-colors font-mono"`

**Suggested extraction:** Export `inputClass` from a shared location (e.g., `editor/styles.ts` or `detail/atoms.tsx`).

**Impact:** Trivial line savings, but prevents class string drift.

---

### 7. "Original" preview block

**What:** Identical JSX block showing the original text when an override is active.

**Where:**
- `editor/SystemSection.tsx:136-140`
- `editor/ToolsSection.tsx:161-165`
- `editor/MessagesSection.tsx:244-248`

All render:
```tsx
<div className="space-y-1">
  <span className="label text-txt-3">Original</span>
  <pre className="max-h-32 overflow-auto bg-canvas p-3 text-[12px] text-txt-3 whitespace-pre-wrap border border-edge-subtle">
    {originalText}
  </pre>
</div>
```

**Suggested extraction:** `OriginalPreview` component in `detail/atoms.tsx`.

**Impact:** ~15 lines. Quick win.

---

### 8. Connection status indicator

**What:** Identical JSX for the live/off connection indicator rendered twice.

**Where:**
- `app.tsx:70-78` (entry page)
- `app.tsx:100-110` (main layout)

**Suggested extraction:** `ConnectionDot` component, co-located in `app.tsx` or in a small component file.

**Impact:** ~10 lines within a single file. Trivial.

---

### 9. Role tone mapping

**What:** User/assistant role-to-color mapping defined in two places.

**Where:**
- `detail/ContentBlocks.tsx:88-91` (`ROLE_TONE` constant)
- `editor/MessagesSection.tsx:292-294` (inline `roleTone` variable)

Both map `user -> sky`, `assistant -> sage`.

**Suggested extraction:** Export `ROLE_TONE` from ContentBlocks (already exported implicitly since it's used there) or move to `detail/atoms.tsx`.

**Impact:** ~4 lines. Prevents color drift between read and edit views.

---

### 10. `MAX_ENTRIES` constant

**What:** Same constant `500` declared in two hooks.

**Where:**
- `hooks/useExchangeStream.ts:6`
- `hooks/useExchanges.ts:5`

**Suggested extraction:** Single export from a constants file or from `api.ts`.

**Impact:** 2 lines. Prevents silent divergence.

---

### 11. `ContentBlockRow` vs `BlockRow` structural similarity

**What:** Both render an expandable content block with a chip type label, summary text, and a `<pre>` expansion. `BlockRow` adds toggle/override functionality but the visual structure is ~70% shared.

**Where:**
- `detail/ContentBlocks.tsx:52-81` (read-only)
- `editor/MessagesSection.tsx:143-267` (editable)

**Suggested extraction:** Not a straightforward merge. The editable version has significantly more logic. Consider extracting the shared visual shell (chip + summary + expand container) as a base component, with slots for the toggle and expanded content.

**Impact:** Medium. Would reduce MessagesSection by ~30 lines but adds abstraction complexity. This is a judgment call.

---

### 12. Error handling pattern in BreakpointEditor

**What:** Five async handlers each wrap the same try/catch with `setError(err instanceof Error ? err.message : "X failed")`.

**Where:** `editor/BreakpointEditor.tsx:43-119`

**Suggested extraction:** A small helper: `withError(setError, fn)` or a custom hook that wraps async actions.

**Impact:** ~25 lines, 5 handlers simplified. Quick win.

---

## Quick Wins (under 30 minutes each)

1. **Extract `colorizeLine`** to `lib/colorizeLine.ts`. Delete the copy in MessagesSection. (~15 min)
2. **Extract `OriginalPreview`** component to `detail/atoms.tsx`. Replace 3 inline blocks. (~10 min)
3. **Extract textarea class** to shared constant. Replace 3 inline strings. (~5 min)
4. **Extract `ConnectionDot`** inline in `app.tsx`. Replace 2 blocks. (~5 min)
5. **Unify `MAX_ENTRIES`** constant. (~2 min)
6. **Export and reuse `ROLE_TONE`** from ContentBlocks. (~5 min)
7. **Unify `blockKey`** to use the existing export from ContentBlocks. (~5 min)
8. **Merge `blockSummary`/`blockLabel`** with a `maxLength` parameter. (~10 min)

## Larger Refactors (need more thought)

1. **`useEditableOverride` hook**: Extract the repeated useState/useEffect/commit/reset pattern shared by SystemCard, ToolRow, and BlockRow. This is the highest-impact refactor. Needs careful API design to handle the different override kinds (system_part_toggle vs tool_toggle vs message_block_toggle) without over-abstracting. Estimated: 1-2 hours.

2. **Override lookup utilities**: Consolidate 6 helper functions across 3 files into a single `lib/overrides.ts` module. The target-string composition differs per section, so the utility should accept pre-composed targets. Estimated: 30-45 min.

3. **Read-only vs editable block rendering**: ContentBlockRow and BlockRow share visual structure but diverge on functionality. A shared base component with render props or slots could work but risks over-abstraction for two consumers. Consider only if more block renderers are planned. Estimated: 1-2 hours.
