---
title: AM Standalone Chat Interface - UX Review
type: design
tags: [ux-design, chat-ui, attention-matters, memory-explorer, review]
summary: UX review of ALP-1127 issue tree covering layout gaps, missing interaction states, two-mode toggle clarity, memory panel pattern, and sidebar design.
status: active
source: ux-designer
confidence: high
created: 2026-03-11
updated: 2026-03-11
---

# AM Standalone Chat Interface - UX Review

## Summary

Reviewed the full ALP-1127 issue tree (ALP-1137 through ALP-1144) for the AM Standalone Chat Interface. The architecture and feature scope are well-conceived. The primary gaps are: missing layout specification, undefined interaction states across all components, ambiguous placement decisions ("panel or modal", "sidebar or tab"), and an undertreated mode-switch UX. All feedback posted as Linear comments on the respective issues.

---

## Findings by Issue

### ALP-1127 - Parent: Layout Architecture

**Gap: No spatial layout spec.** Three-zone layout (settings header / chat / memory sidebar) has no defined proportions, min-widths, or breakpoints.

**Recommended CSS Grid:**
```css
.app-layout {
  display: grid;
  grid-template-areas:
    "header  header"
    "chat    sidebar";
  grid-template-rows: 56px 1fr;
  grid-template-columns: 1fr minmax(150px, 500px);
  height: 100vh;
  overflow: hidden;
}
```

**Responsive breakpoints:**
- >= 1024px: three-zone layout, sidebar visible
- < 1024px: sidebar collapses to icon strip; chat takes full width
- < 768px: settings header collapses to gear icon

**Missing:** Relationship between memory context panel (ALP-1138, per-message) and memory sidebar (ALP-1142, episode browser) needs explicit definition in a layout diagram.

---

### ALP-1137 - Chat Thread with Streaming

**Missing interaction states:**

| State | Required UX |
|-------|-------------|
| Empty (no messages) | Centered prompt, mode-aware placeholder queries |
| Stream error (connection drop) | Partial message preserved + "Response interrupted" + retry |
| Send failure (server/API key error) | Message stays in composer + inline error |
| Active streaming | Visible stop/cancel button |
| Canceled stream | Previous partial message marked canceled |

**Salient tag highlighting:** Use inline `<mark>` background at `#c9a66b` (matching dae-stand-alone). Clarify in implementation: not bold+color, not border.

**Cmd+Enter:** Non-standard but acceptable for developer tool. Require visible hint in composer placeholder: "Cmd+Enter to send · Shift+Enter for newline".

---

### ALP-1138 - Memory Context Panel per Message

**Collapsed label issue:** `con:X sub:Y novel:Z` is AM-internal. Add full-word labels on first expand, abbreviations after: "3 conscious · 2 subconscious · 1 novel". Add a `?` tooltip linking to a glossary.

**Feedback button timing:** Show on message hover (desktop) AND always visible when a neighborhood is expanded. Keyboard: `+`/`-` when neighborhood is focused. Confirmation: brief inline "Saved" indicator on submit.

**Context event sequencing contract:**
- Context arrives before streaming: show collapsed panel immediately
- Context arrives during streaming: animate panel in without scroll disruption
- Context arrives after streaming: panel fades in after message complete

**No-memory state:** Show "No memories recalled" indicator (not silence). Silence is ambiguous.

---

### ALP-1139 - Settings Panel

**Mode toggle gaps:**
- Mid-conversation switch: applies to next message only. Tooltip: "Applies to your next message."
- Visual differentiation by mode: composer placeholder text should change per mode ("Explore your memories..." vs "Ask anything...").

**Connection indicator - all four states:**
- No key: grey dot
- Key entered, unvalidated: amber dot / spinner
- Validation failed: red dot + "Invalid key" text
- Validated: green dot + "(provider) connected"

**Header overflow at < 1100px:** Priority collapse order:
1. Agent name field (lowest priority, default works)
2. Model selector -> compact icon + popover
3. API key -> moves to gear icon settings drawer

---

### ALP-1142 - Episode List Sidebar

**Resizable sidebar:** Keep drag handle pattern. Missing details:
- Default width: **280px**
- At 150px minimum: show only episode name + conscious indicator (truncate counts)
- Below 150px: collapse to icon strip with episode count badge
- Keyboard: arrow keys resize in 16px increments (WCAG 2.1 requirement)

**Conscious episodes:** Gold left-border (4px solid `#c9a66b`) on episode row. Not just icon/text color.

**Empty state:** "No episodes yet. Start a conversation to begin building memory."

**Loading state:** Skeleton shimmer (3-4 placeholder rows), not a spinner.

---

### ALP-1143 - Episode Detail View

**Modal vs panel: use panel.** A modal blocks chat context. Use sidebar push-navigation: episode list slides out, detail slides in, with a back button to return to list. Layout remains stable.

**Neighborhood highlight (recalled in session):** Gold left-border + "Recalled" badge. Must not visually conflict with conscious-episode gold border from ALP-1142 - use a different indicator shape (badge vs border) or a distinct accent color.

**Sort default:** By epoch (most recent first). Sort control is sticky within panel.

**superseded_by:** Strikethrough + muted text on superseded neighborhoods, with linked "Superseded by: [summary]" tooltip.

---

### ALP-1144 - Memory Search (Two-Phase Retrieval)

**Placement decision:** Use tab navigation within sidebar ("Episodes" | "Search"). Do not create a separate panel or route.

**Two-phase UX contract:**
- Phase 1 (query-index): Compact result list with "Preview results" header. Note: "Click to load full content." Show `total_tokens_if_fetched` as "Fetching all: ~X tokens" below list.
- Phase 2 (retrieve): Selected item expands in-place with skeleton loader. Successfully retrieved items show full source; failures show inline "Could not load" error.

**Score display:** Normalized 5-dot bar indicator, raw float on hover.

**Missing states:**
- No results: "No memories matched. Try broader terms."
- Partial retrieve failure: inline error per failed item, rest loads normally
- Rate limit / server error: inline + retry button
- Query in progress: spinner in search input field (not page-level loader)

---

## Cross-Cutting Issues

1. **"Panel or modal" ambiguity (ALP-1143):** Always panel. Resolved.
2. **"Sidebar or tab" ambiguity (ALP-1144):** Always sidebar tab. Resolved.
3. **Two memory surfaces (ALP-1138 + ALP-1142):** Need a visual hierarchy spec clarifying that the per-message panel is ephemeral context, the sidebar is the persistent archive.
4. **Gold overuse risk:** `#c9a66b` is used for conscious episodes (sidebar border), salient text highlights (chat), and recalled neighborhoods (detail view). Ensure each use has a distinct enough shape/element type to remain distinguishable.

---

## Implementation Roadmap (Recommended Sequencing)

1. CSS layout spec + design tokens (color, spacing, typography)
2. Settings bar with all four connection indicator states + mode toggle
3. Chat thread: empty state, streaming, error states, cancel button
4. Memory context panel: collapsed/expanded, feedback buttons, no-memory state
5. Episode list sidebar: loading, empty, resizable, gold border
6. Episode detail panel (push navigation from sidebar)
7. Memory search tab (two-phase retrieval)
8. Accessibility audit: keyboard navigation, ARIA labels, focus management

---

## Open Questions

1. Should the memory context panel be opt-in per message (show/hide toggle on the message) rather than always present? This reduces visual weight in long conversations.
2. What is the exact visual treatment when both the episode detail panel and the memory search are accessible via sidebar tabs - do they share the same panel width, or does episode detail expand wider?
3. Does the mode switch clear the current conversation thread, or is the same thread valid for both modes?
