# Manicure UX Design: Direct Override Model

## 1. Layout

Two-panel layout. Right audit sidebar removed entirely.

```
[Left Sidebar 340px]  |  [Editor (flex-1)]
  Exchange Log only   |  PausedHeader
  (no rules tab)      |  Override Summary (collapsible)
                      |  EditorActions (stats + action buttons)
                      |  ─────────────────────────────────
                      |  Scrollable editor body:
                      |    Sampling
                      |    Messages
                      |    System
                      |    Tools
```

**Left sidebar** loses the tab bar. The rules tab and its creation form are removed. The sidebar becomes a single-purpose exchange log with the header and arm/disarm controls above it. The freed vertical space goes entirely to the exchange list.

**Central editor** gains the horizontal space previously consumed by the right sidebar. The editor body uses the full width minus the left sidebar. Sections remain vertically scrollable, each collapsible via its section-rule header. Click the section label to collapse/expand.

**Section ordering** stays Sampling > Messages > System > Tools. Sampling is compact (one row of inputs) and gives the user immediate context about the request shape. Messages and System are the primary editing surfaces. Tools sit last since tool toggling is less frequent than content editing.

## 2. Tool Overrides UX

The current grouped-toggle model is already strong. Refinements:

### Tool list

Each tool row renders as:

```
[Toggle] tool_name                    1,240 chars  [amber dot if modified]
```

The existing group structure (MCP prefix grouping, collapsible sections, All/None/Drop MCP bulk actions) remains unchanged.

### Description editing

Clicking a tool row expands it inline to reveal two read-only fields and one editable field:

```
[Toggle] bash_tool                              1,240 chars  [dot]
  ┌──────────────────────────────────────────────────────────────┐
  │ DESCRIPTION                                                  │
  │ ┌──────────────────────────────────────────────────────────┐ │
  │ │ Executes a given bash command and returns its output...  │ │  <- textarea, editable
  │ └──────────────────────────────────────────────────────────┘ │
  │ SCHEMA  (read-only, collapsed by default)                    │
  │  { "type": "object", "properties": { ... } }                │
  │                                                              │
  │ ORIGINAL  (visible only when description modified)           │
  │  Executes a given bash command and returns its output. The   │  <- pre, muted text-txt-3
  │  working directory persists between commands...              │
  └──────────────────────────────────────────────────────────────┘
```

The "ORIGINAL" block only appears when the user has edited the description. It uses `text-txt-3` color and sits below the editable textarea, giving the user a reference without consuming space by default.

### Reset

When a tool is modified (toggled off or description edited), a small reset button appears at the right edge of the expanded card: a `text-txt-3` "reset" label that reverts that single tool to its original state. Hovering shifts it to `text-txt`.

### Group-level override count

Each group header already shows `checked/total`. Add an override count when any tool in the group has been modified:

```
mcp__supabase  4/12  8,420 chars  [2 overrides]
```

The override count renders as a `chip` with `text-amber` styling.

## 3. Message Overrides UX

### Block-level toggling

The current model (per-block toggle with type chips) is preserved. Each block renders with its toggle, type chip (`text`, `tool_use`, `tool_result`, `thinking`), and size in chars.

### Text editing

Text blocks gain inline editing. Clicking the text preview (already clickable to expand) opens the block content in a textarea:

```
[Toggle] [text] 3,420 chars
  ┌────────────────────────────────────────────────────────┐
  │ The user wants to implement a billing system that...   │  <- textarea, editable
  └────────────────────────────────────────────────────────┘
  ORIGINAL (visible only when edited, text-txt-3)
  The user wants to implement a billing system that...
```

The textarea uses the same styling as SystemSection's textarea: `bg-canvas border border-edge`, monospace, `text-[11px]`. Max height `max-h-64` with `resize-y`.

### Thinking block toggle

Thinking blocks get a more prominent toggle treatment since stripping thinking is a high-frequency operation. The chip for thinking blocks renders in `text-lavender` (distinguishing it from other block types). When toggled off, the entire row fades to `opacity-40` (existing behavior).

### Tool result truncation

Tool result blocks gain a truncation control. When expanded, a small input appears:

```
[Toggle] [tool_result] toolu_abc123  12,840 chars
  Truncate to: [____] chars    [original: 12,840]
```

The input field uses `inputClass` styling from SamplingSection. Leaving it empty means no truncation. Setting a value truncates the content to that char limit. The original size is shown as a `label` reference.

### Message-level indicators

Each message card header (the `user`/`assistant` role row) gains an override indicator when any block within it has been modified:

```
[user] 4 blocks  [amber dot] 2 modified
```

The count of modified blocks appears as `label text-amber` next to the existing block count.

## 4. System Prompt Overrides UX

The current SystemSection design is already close to the target. Refinements:

### Enhanced card state

Each system part card shows three states:

1. **Unmodified**: Default appearance. Toggle on, original text displayed.
2. **Text edited**: Amber left border (`border-l-2 border-amber`). The original text is accessible via a "show original" toggle at the bottom of the card that reveals a `pre` block in `text-txt-3`.
3. **Toggled off**: `opacity-40` (existing behavior). The toggle is off.

### Reset per-part

When a part's text has been edited, a "reset" label appears in the card header row, right-aligned, in `text-txt-3`. Clicking it reverts the text to the original value.

### Section header

```
── System . 4 parts ── [1 modified, 1 removed]
```

The modification summary renders as `label text-amber` after the part count.

## 5. Override Indicators

A unified visual language for modification state across all sections.

### Color: amber

All override indicators use `amber` as the accent. This is the existing warning/attention color in the palette, distinct from `sage` (success/armed), `rose` (destructive), and `sky` (primary action/selection).

### Per-item indicators

| State | Visual |
|---|---|
| Unmodified | No indicator |
| Toggled off | `opacity-40` on the row, no dot |
| Content edited | Amber dot (4px circle, `bg-amber`) to the right of the item label |
| Both toggled off and edited | `opacity-40` + amber dot |

The amber dot is a `span` with `h-1 w-1 rounded-full bg-amber`. Consistent 4px diameter across all sections.

### Per-section indicators

Each section-rule header shows an override count when overrides exist:

```
── Tools . 42 ──────────── [3 overrides] ──
── Messages . 8 ─────────── [5 overrides] ──
── System . 4 parts ──────── [2 overrides] ──
── Sampling ──────────────── [1 override] ──
```

The count renders as a `chip text-amber` positioned after the section label, before the trailing hairline.

### Revert controls

Two levels of revert:

1. **Per-item**: "reset" text button visible on hover or when the item is expanded. Reverts that single field/tool/part to its original value.
2. **Per-section**: A "Reset section" button in each section-rule header, visible only when that section has overrides. Styled as `label text-txt-3 hover:text-amber`, right-aligned.
3. **Global**: "Clear all overrides" in the Override Summary panel (see section 7).

## 6. Stats Bar (EditorActions)

The EditorActions bar gains override awareness. New layout:

```
Row 1: [Override summary: "8 overrides active · -22%"]  [Drop] [Pass Through] [Forward]
Row 2: anthropic / claude-sonnet-4-20250514          chars 124,200  delta -22%
```

### Row 1 changes

The override summary replaces dead space on the left side of the action button row. It renders as:

```
[amber dot] 8 overrides active · -22%    [Clear All]
```

- Amber dot: `h-1.5 w-1.5 rounded-full bg-amber pulse-dot` (uses existing pulse animation)
- Text: `text-[11px] text-amber metric-num`
- "Clear All": `label text-txt-3 hover:text-amber`, clears all persistent overrides
- When no overrides are active, this area shows nothing

### Row 2 changes

Char count and delta update live as the user makes edits. The `chars_before` baseline comes from the original (pre-pipeline, pre-edit) request. This means:
- `chars` always reflects the current edited state
- `delta` always shows the difference from the original request
- Negative delta renders in `text-sage` (savings), positive in `text-amber` (growth)

No structural changes to row 2 needed. The existing implementation already supports this via `countChars(editedIr)`.

## 7. Session Persistence Visibility

Overrides persist across exchanges within a session. This requires three affordances: awareness, inspection, and management.

### Awareness: persistent override banner

When a new exchange is paused and persistent overrides exist from previous edits, the PausedHeader gains a second line:

```
[amber dot] Paused · a1b2c3d4 · 00:42
[override icon] 8 persistent overrides active from this session
```

The second line uses `text-[11px] text-amber` and spans the full header width. It communicates immediately that this request will be modified by previously-set overrides before the user even scrolls down.

Clicking this line scrolls to the Override Summary in the EditorActions area or, if the summary panel is collapsed, expands it.

### Inspection: override manifest

The Override Summary panel (in EditorActions row 1, described above) expands on click to reveal a grouped list of all active overrides:

```
[amber dot] 8 overrides active · -22%    [Clear All]   [collapse]
  ┌──────────────────────────────────────────────────────────────┐
  │ TOOLS (3)                                                    │
  │   bash_tool ···· toggled off                      [revert]  │
  │   Read ·········· description edited              [revert]  │
  │   Write ········· description edited              [revert]  │
  │                                                              │
  │ MESSAGES (3)                                                 │
  │   [user] msg 2, block 0 ···· text edited          [revert]  │
  │   [assistant] msg 3, block 2 ···· thinking off    [revert]  │
  │   [user] msg 4, block 1 ···· tool_result truncated [revert] │
  │                                                              │
  │ SYSTEM (1)                                                   │
  │   part [1] ···· text edited                       [revert]  │
  │                                                              │
  │ SAMPLING (1)                                                 │
  │   temperature ···· 0.7 -> 0.3                     [revert]  │
  └──────────────────────────────────────────────────────────────┘
```

This panel uses `card-flush` styling with `bg-surface/40`. Group headers use `label`. Individual override rows use `text-[11px] text-txt-2`. Revert buttons use `label text-txt-3 hover:text-rose`.

The panel is collapsible. Collapsed state shows just the one-line summary. Collapsed by default to preserve information density.

### Management: clearing overrides

Three clearing strategies available:

1. **Individual**: Click "revert" next to any override in the manifest, or use per-item reset buttons in the editor sections
2. **Per-section**: "Reset section" in each section-rule header
3. **All**: "Clear All" button in the Override Summary row

"Clear All" shows a brief confirmation state: the button text changes to "Confirm clear" in `text-rose` for 3 seconds, then reverts to "Clear All" if not clicked. No modal dialog. The confirmation is inline and non-disruptive.

### Persistence scope

Overrides persist for the duration of the manicure session (tied to the proxy's session concept, not the browser tab). Closing the browser and reopening reloads persistent overrides from the server. A "Session overrides" indicator in the left sidebar header (next to the version number) shows that overrides are active even when viewing the exchange log:

```
MANICURE  v0.0.1   [amber dot] 8 overrides
```

This ensures the user is never unaware that they have active overrides modifying intercepted requests.
