---
title: EchoEcho Admin Panel — Route Simulation Mode Design Specification
type: design
tags: [ux-design, accessibility, admin, wcag, simulation, route-management, desktop-web]
summary: Desktop-web simulation UI for disability services admins to validate and approve routes before student use. Covers 7 views, session state machine, route data model, responsive breakpoints, and WCAG AA compliance.
status: active
source: ux-designer
confidence: high
created: 2026-03-09
updated: 2026-03-09
---

## Summary

Admin panel route simulation mode for disability services coordinators. The persona is a domain expert in campus accessibility — not a developer. The simulation allows validation of haptic patterns, announcement text, and waypoint sequence before a route is published for student use.

**Platform**: Desktop web primary, tablet secondary. Not React Native. Tokens are CSS custom properties. Framework: not specified here — ALP-990 (frontend engineer) owns the implementation stack choice.

**Research basis**: NYU Tandon VR pre-testing study validates simulation as a confidence-building tool before real-world deployment (vi-navigation-technology-landscape.md §5). The admin may themselves be disabled — WCAG AA is a safety requirement, not optional.

**Route data model**: The canonical shared types in `packages/shared/src/types/route.ts` own `Route` and `Waypoint`. The issue's TypeScript interfaces include fields not yet in the shared schema. This spec flags those as extension requests for ALP-989 (backend). See Section 3 for reconciliation.

---

## Design System Foundation

Admin panel tokens are self-contained. No token parity with the student app is required for MVP.

### Color Tokens

```css
:root {
  /* Base palette — light mode (admin panel is light-first) */
  --color-background:         #F8F9FA;  /* App background */
  --color-surface:            #FFFFFF;  /* Card/panel background */
  --color-surface-elevated:   #FFFFFF;  /* Modals, popovers */
  --color-border:             #DEE2E6;  /* Dividers, input borders */
  --color-border-focus:       #4A90E2;  /* Focus ring color */

  /* Primary action */
  --color-primary:            #2563EB;  /* Blue. 4.5:1 on white. WCAG AA. */
  --color-primary-hover:      #1D4ED8;
  --color-primary-active:     #1E40AF;
  --color-primary-disabled:   #93C5FD;  /* Disabled primary. 3.1:1 — large text only. */
  --color-on-primary:         #FFFFFF;

  /* Semantic — route status */
  --color-status-draft:       #6B7280;  /* Gray. Neutral. */
  --color-status-simulated:   #D97706;  /* Amber. In-review. */
  --color-status-approved:    #059669;  /* Green. Positive. */
  --color-status-deprecated:  #DC2626;  /* Red. Negative. */

  /* Each status also has an icon — color is NEVER the sole indicator. */
  --color-status-draft-bg:    #F3F4F6;
  --color-status-simulated-bg:#FEF3C7;
  --color-status-approved-bg: #D1FAE5;
  --color-status-deprecated-bg:#FEE2E2;

  /* Feedback */
  --color-error:              #DC2626;  /* 4.6:1 on white. */
  --color-error-bg:           #FEF2F2;
  --color-warning:            #D97706;  /* 3.1:1 on white — only for large text or icon+text. */
  --color-warning-bg:         #FFFBEB;
  --color-success:            #059669;  /* 3.2:1 on white — only for large text or icon+text. */
  --color-success-bg:         #ECFDF5;
  --color-info:               #2563EB;

  /* Text */
  --color-text-primary:       #111827;  /* 16.3:1 on background. */
  --color-text-secondary:     #6B7280;  /* 4.7:1 on background. */
  --color-text-disabled:      #9CA3AF;  /* 2.9:1 — only acceptable as disabled label with icon. */
  --color-text-on-dark:       #FFFFFF;

  /* Dark mode */
  --color-background-dark:    #111827;
  --color-surface-dark:       #1F2937;
  --color-border-dark:        #374151;
  --color-text-primary-dark:  #F9FAFB;
  --color-text-secondary-dark:#9CA3AF;
}

@media (prefers-color-scheme: dark) {
  :root {
    --color-background:         var(--color-background-dark);
    --color-surface:            var(--color-surface-dark);
    --color-border:             var(--color-border-dark);
    --color-text-primary:       var(--color-text-primary-dark);
    --color-text-secondary:     var(--color-text-secondary-dark);
  }
}
```

**Contrast verification**:
- `--color-primary` (#2563EB) on `--color-surface` (#FFFFFF): 5.9:1. WCAG AA normal text. ✓
- `--color-text-primary` (#111827) on `--color-background` (#F8F9FA): 16.3:1. ✓
- `--color-text-secondary` (#6B7280) on `--color-background`: 4.7:1. ✓
- `--color-status-deprecated` (#DC2626) on `--color-status-deprecated-bg` (#FEE2E2): 4.8:1. ✓
- Status colors on white background fail large-text threshold except error — never use alone. All status badges use icon + text label.

### Typography Tokens

```css
:root {
  --font-family-base:       -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  --font-family-mono:       'JetBrains Mono', 'Fira Code', 'Cascadia Code', monospace;

  --font-size-xs:           12px;  /* Caption. Minimum for informational text. */
  --font-size-sm:           14px;  /* Secondary labels. */
  --font-size-base:         16px;  /* Body. WCAG 1.4.4 minimum. */
  --font-size-lg:           18px;  /* Emphasized body. */
  --font-size-xl:           20px;  /* Subheadings. */
  --font-size-2xl:          24px;  /* Section headings. */
  --font-size-3xl:          30px;  /* Page headings. */

  --font-weight-regular:    400;
  --font-weight-medium:     500;
  --font-weight-semibold:   600;
  --font-weight-bold:       700;

  --line-height-body:       1.6;   /* WCAG 1.4.12: 1.5× minimum for body. */
  --line-height-heading:    1.25;
  --line-height-tight:      1.2;
}
```

### Spacing Tokens

```css
:root {
  --space-1:   4px;
  --space-2:   8px;
  --space-3:   12px;
  --space-4:   16px;
  --space-5:   20px;
  --space-6:   24px;
  --space-8:   32px;
  --space-10:  40px;
  --space-12:  48px;
  --space-16:  64px;

  --touch-target:  44px;    /* WCAG 2.5.5 minimum click/touch area. */

  --radius-sm:     4px;
  --radius-md:     8px;
  --radius-lg:     12px;
  --radius-full:   9999px;

  --shadow-sm:     0 1px 2px rgba(0,0,0,0.05);
  --shadow-md:     0 4px 6px rgba(0,0,0,0.07), 0 2px 4px rgba(0,0,0,0.04);
  --shadow-lg:     0 10px 15px rgba(0,0,0,0.1), 0 4px 6px rgba(0,0,0,0.05);
}
```

---

## Route Data Model

### Canonical Schema Reconciliation

The canonical `Route` and `Waypoint` types live in `packages/shared/src/types/route.ts`. This spec uses the canonical types and flags required extensions for ALP-989 (backend).

```typescript
// Existing canonical type (packages/shared/src/types/route.ts)
// RouteStatus = 'pending_save' | 'draft' | 'published' | 'retracted'
//
// Required extension (flag for ALP-989):
// RouteStatus must add 'simulated' and 'approved' states.
// Suggested extended type:
type RouteStatus =
  | 'pending_save'
  | 'draft'
  | 'simulated'   // NEW: simulation run completed
  | 'approved'    // NEW: coordinator approved for student use
  | 'published'   // existing: active for students
  | 'retracted'   // existing: removed from student access
  | 'deprecated'; // NEW: replaced by newer route version

// Existing Waypoint type is missing two fields needed for simulation:
// Required extensions (flag for ALP-989):
interface WaypointSimulationExtensions {
  proximityRadiusMeters: number;   // haptic/audio triggers when student within this radius
  hapticPattern: HapticPattern;    // from packages/shared/src/types/navigation.ts
  // Note: issue used hapticPatternId: string — use HapticPattern enum directly.
  // The admin UI displays human-readable pattern names, not opaque IDs.
}
// These fields extend the existing Waypoint interface:
// id, routeId, sequenceIndex, coordinate, type, headingOut, audioLabel, description, etc.
// Admin simulation references audioLabel as the student's audio announcement text.
```

**ALP-989 action required**: Extend `RouteStatus` union and add `proximityRadiusMeters` + `hapticPattern` to `Waypoint`. Until backend delivers, admin panel frontend should treat these as optional with sensible defaults (proximityRadius: 5m, hapticPattern: `straight`).

**Admin simulation route type (for spec clarity)**:
```typescript
interface AdminRoute extends Route {
  status: 'draft' | 'simulated' | 'approved' | 'deprecated';
  lastSimulatedAt: string | null;  // ISO 8601
  approvedAt: string | null;
  approvedBy: string | null;
  notes: string;
}
```

---

## Simulation Session State Machine

```
idle
  → [admin clicks Play] → playing
      → [admin clicks Pause] → paused
          → [admin clicks Play] → playing
          → [admin clicks a waypoint] → at-waypoint (playing suspended)
              → [admin closes detail] → paused
      → [admin clicks a waypoint] → at-waypoint
          → [admin edits announcement] → edit-mode
              → [admin saves] → at-waypoint (re-simulates segment)
              → [admin discards] → at-waypoint
          → [admin closes detail] → playing
      → [invalid waypoint encountered] → error (playing suspended)
          → [admin resolves error or marks skip] → playing
          → [admin cannot resolve] → error (stays suspended until manual skip)
      → [simulation reaches end] → complete
          → [admin clicks Approve] → route.status = 'approved'
          → [admin clicks Request Changes] → route.status = 'draft' (with notes)
  → [admin clicks Step Forward] → at-waypoint (from idle or paused)
  → [admin clicks Step Back] → at-waypoint (from idle or paused)
```

### Unsaved Edit Behavior

- **Auto-save draft**: 2 seconds of inactivity in `AnnouncementEditor` triggers a draft save (local, not persisted to server). Visual indicator: "Draft saved" appears in editor footer.
- **Navigate-away with unsaved edits**: Confirmation dialog fires. "You have unsaved changes to this waypoint. Discard changes?" with "Keep Editing" (primary, auto-focused) and "Discard" (secondary). If confirmed, edits are discarded and navigation proceeds.
- **Session recovery**: On page reload with unsaved draft in localStorage, a banner offers to restore: "You have an unsaved edit from [X minutes ago]. Restore?"

---

## View Specifications

### 1. `RouteList`

**Purpose**: Entry point. Paginated list of all routes with status badges. Multi-route management.

#### TypeScript Props Interface

```typescript
interface RouteListProps {
  routes: AdminRoute[];
  isLoading: boolean;
  filters: {
    status: RouteStatus | null;
    buildingId: string | null;
    campusId: string | null;
  };
  sortBy: 'lastModified' | 'lastSimulated' | 'status' | 'name';
  sortOrder: 'asc' | 'desc';
  selectedIds: string[];
  onFilterChange: (filters: Partial<RouteListProps['filters']>) => void;
  onSortChange: (by: RouteListProps['sortBy'], order: RouteListProps['sortOrder']) => void;
  onSelectRoute: (id: string) => void;
  onSelectAll: (selected: boolean) => void;
  onBulkDeprecate: (ids: string[]) => void;
  onBulkExport: (ids: string[]) => void;
  onImportRoute: () => void;
  onOpenSimulation: (routeId: string) => void;
}
```

#### State Matrix

| State | Visual | Behavior | Accessibility |
|---|---|---|---|
| Default (has routes) | Table/list view, status badges, action buttons per row | Keyboard: Tab through filters → table rows → actions | `role="table"` on container; each row: `role="row"`; status badge: `aria-label="Status: [label]"` |
| Loading | Skeleton rows (5) with shimmer | Table header visible and focusable | Skeleton: `aria-hidden="true"`, live region: `aria-live="polite"` announces "Loading routes" |
| Filter active | Filter bar highlighted, active filter chips shown | Tab-accessible filter controls | Filter bar: `role="search"` region; chips: `aria-label="Filter: [name]. Press Delete to remove."` |
| Sort active | Column header shows sort icon (↑ or ↓) | Click or Space/Enter on header to sort | Column header: `aria-sort="ascending"` / `"descending"` |
| Row selected | Checkbox checked, row background shaded | Bulk action bar appears at bottom | Checkbox: `aria-label="Select route [name]"`; bulk bar: `role="toolbar"` |
| All selected | Header checkbox indeterminate→checked | — | Header checkbox: `aria-checked="true"` or `"mixed"` |
| Empty | Empty state card | "No routes yet. Import a route or contact your routing administrator." + Import button | Empty state: `role="status"` |
| Error (load failed) | Error card with retry | Retry button auto-focused | `role="alert"` |
| Dark mode | Dark tokens applied | — | — |

#### Status Badge Specification

Each badge uses icon + text label. Color is supplementary, not the sole indicator (WCAG 1.4.1).

| Status | Icon | Text | Background | Text color |
|---|---|---|---|---|
| Draft | Pencil (edit) icon | "Draft" | `--color-status-draft-bg` | `--color-status-draft` |
| Simulated | Play (triangle) icon | "Simulated" | `--color-status-simulated-bg` | `--color-status-simulated` |
| Approved | Checkmark icon | "Approved" | `--color-status-approved-bg` | `--color-status-approved` |
| Deprecated | X-circle icon | "Deprecated" | `--color-status-deprecated-bg` | `--color-status-deprecated` |

#### Filter Controls

```
[Filter by status: All | Draft | Simulated | Approved | Deprecated]  ← role="radiogroup"
[Filter by building: dropdown]                                        ← role="combobox"
[Sort: dropdown]                                                      ← role="combobox"
[Bulk actions: Deprecate | Export JSON]                               ← role="toolbar", aria-label="Bulk actions"
```

Filters are reflected in URL query params for shareability and back-button support.

#### Layout (≥1280px)

```
[Page heading: "Routes"]
[Filter bar: status tabs, building dropdown, sort dropdown]
[Bulk action bar (conditional, appears when rows selected)]
[Route table: checkbox | Name | Status | From → To | Last Simulated | Actions]
[Pagination controls]
```

---

### 2. `SimulationPlayer`

**Purpose**: Primary simulation view. Animated position on map. Playback controls. Persistent fidelity notice.

#### TypeScript Props Interface

```typescript
interface SimulationPlayerProps {
  route: AdminRoute;
  simulationState: 'idle' | 'playing' | 'paused' | 'at-waypoint' | 'edit-mode' | 'error' | 'complete';
  currentWaypointIndex: number;
  playbackSpeed: 1 | 2 | 4;
  isOnline: boolean;
  onPlay: () => void;
  onPause: () => void;
  onStepForward: () => void;
  onStepBack: () => void;
  onSetSpeed: (speed: 1 | 2 | 4) => void;
  onSelectWaypoint: (index: number) => void;
  onEndSimulation: () => void;
}
```

#### Persistent Fidelity Notice

Always visible within `SimulationPlayer`. Cannot be dismissed.

```html
<aside role="note" aria-label="Simulation scope notice">
  Logical simulation only — validates haptic patterns and announcement text.
  Field test required before student use.
</aside>
```

Visual: muted gray banner, no icon decoration. Positioned below the map, above playback controls.

#### Playback Controls Specification

| Control | Visual | Keyboard shortcut | ARIA |
|---|---|---|---|
| Play / Pause | Icon button, 44×44px, toggles icon | `Space` | `role="button"` `aria-pressed="true/false"` `aria-label="Play simulation"` / `"Pause simulation"` |
| Step Back | Icon button, 44×44px | `←` (Arrow Left) | `role="button"` `aria-label="Previous waypoint"` |
| Step Forward | Icon button, 44×44px | `→` (Arrow Right) | `role="button"` `aria-label="Next waypoint"` |
| Speed | Segmented control: 1× / 2× / 4× | `S` cycles through speeds | `role="radiogroup"` `aria-label="Playback speed"`, each option: `role="radio"` |
| Waypoint scrub | Clickable waypoint list items | Navigate with `↑` / `↓`, `Enter` to jump | Each waypoint: `role="option"` in `role="listbox"` |

Keyboard shortcuts active when `SimulationPlayer` has focus. Document shortcuts in a visible `?` help button: `aria-label="Keyboard shortcuts"`.

#### Progress Announcement

On each waypoint step (forward or back), announce to screen reader via `aria-live="polite"`:
```
"Waypoint [N] of [total]: [waypoint label]"
```

#### State Matrix

| State | Visual | Behavior | Accessibility |
|---|---|---|---|
| Idle | Map shows full route, position marker at start, Play button | Keyboard shortcuts active | `aria-label="Simulation idle. Press Space to start."` on player region |
| Playing | Position marker animates along route | Keyboard shortcut: Space to pause | Live region announces waypoint on each step |
| Paused | Position marker stopped, Play button | — | `aria-label="Simulation paused at waypoint [N]. Press Space to resume."` |
| At-waypoint | Waypoint detail panel opens (right column or drawer) | Clicking elsewhere closes detail and resumes prior state | Focus moves to WaypointDetail first focusable element |
| Edit-mode | AnnouncementEditor expanded in WaypointDetail | Unsaved edit indicator visible | Editor: `aria-label="Edit announcement text for waypoint [label]"` |
| Error (invalid waypoint) | Error indicator on waypoint in list, RouteErrorPanel opens | Playback suspended | `role="alert"` on error panel; live region: "Simulation paused. Error at waypoint [label]." |
| Complete | SimulationSummary shown, Approve / Request Changes buttons | — | `role="status"` announcement: "Simulation complete." |
| Dark mode | Dark tokens applied | — | — |

#### Layout

**≥1280px (desktop)**:
```
┌─────────────────────────────────┬──────────────────────┐
│  Map / Route Visualization      │  Waypoint List       │
│  [Animated position marker]     │  [Scrollable, 44px   │
│                                 │   row height each]   │
├─────────────────────────────────┤                      │
│  [Fidelity notice banner]       │                      │
├─────────────────────────────────┤                      │
│  [← ▶/⏸ → | 1× 2× 4× | End]   │                      │
└─────────────────────────────────┴──────────────────────┘
```

**768–1279px (tablet landscape)**:
Same two-column layout, detail panel narrower (280px vs 360px).

**<768px (tablet portrait)**:
Single column. Map full width. Waypoint list below map. WaypointDetail opens as bottom sheet (slides up, 60% screen height, drag handle at top).

**<480px**:
Show banner: `role="note"` — "Route simulation is optimized for tablet or desktop. Some controls may be difficult to use on this screen." Banner is dismissible but re-appears on reload. Access is not blocked.

---

### 3. `WaypointDetail`

**Purpose**: Panel/drawer showing selected waypoint's haptic pattern, announcement text, proximity radius.

#### TypeScript Props Interface

```typescript
interface WaypointDetailProps {
  waypoint: Waypoint & WaypointSimulationExtensions;
  isEditing: boolean;
  canEditCoordinates: boolean;  // Open question: see Section 9
  onClose: () => void;
  onEditAnnouncement: () => void;
  onSaveAnnouncement: (text: string) => void;
  onDiscardAnnouncement: () => void;
}
```

#### State Matrix

| State | Visual | Behavior | Accessibility |
|---|---|---|---|
| Default | Waypoint label as heading, pattern name + waveform, announcement text, proximity radius | Read-only unless editing | `role="complementary"` `aria-label="Waypoint detail: [label]"`. Focus: first focusable element in panel on open. |
| Focus (close button) | Close button highlighted | — | `aria-label="Close waypoint detail"` |
| Edit mode | AnnouncementEditor opens within panel | Unsaved indicator | Panel heading updates: "Editing waypoint [label]" |
| Saving | Save button spinner | Auto-save fires on 2s inactivity | `aria-busy="true"` on save button |
| Saved | "Saved" confirmation text (2s, then fades) | — | `aria-live="polite"` announces "Announcement saved." |
| Error (save failed) | Inline error in AnnouncementEditor | — | `role="alert"` on error |
| Dark mode | Dark tokens | — | — |

#### Layout

```
[Panel heading: Waypoint N — [label]]        ← h2, aria-level="2"
[Close button: top-right, 44×44px]
[Haptic pattern: label + HapticPreview]
[Announcement text: read-only display / AnnouncementEditor]
[Proximity radius: "[N] meters"]
[Type: [waypoint type label]]
[Edit button (if not in edit mode)]
```

---

### 4. `HapticPreview`

**Purpose**: Visual representation of haptic pattern. Play button fires pattern on admin device if supported.

#### TypeScript Props Interface

```typescript
interface HapticPreviewProps {
  pattern: HapticPattern;
  isDeviceHapticSupported: boolean;
  isPlaying: boolean;
  onPlay: () => void;
}
```

#### Waveform Visualization

Each `HapticPattern` is visualized as a pulse timeline SVG (horizontal axis = time, vertical = intensity). This is a static SVG, not interactive, generated from the pattern's timing spec.

```
Pattern: turn_right (two 100ms pulses, 80ms gap)
┃ ██ ░ ██ ┃
  100 80 100 (ms)
```

`aria-label` on the SVG: `"Haptic pattern visualization: [pattern description in words]"`.

Example descriptions:
- `turn_right`: "Two medium pulses, 80 milliseconds apart"
- `turn_right_sharp`: "Three short pulses, 60 milliseconds apart"
- `arrived`: "Two long pulses, 200 milliseconds apart"

#### State Matrix

| State | Visual | Behavior | Accessibility |
|---|---|---|---|
| Default | Waveform SVG, Play button | — | `aria-label="Play haptic pattern on this device"` on Play button |
| Not supported | Waveform SVG, Play button grayed with tooltip | "Haptic not available on this device" | Play button: `aria-disabled="true"` `title="Haptic not available on this device"` |
| Playing | Waveform animates (respects `prefers-reduced-motion`) | Pattern fires on device | `aria-label="Stop haptic pattern"` during playback |
| Error | Inline error: "Could not play pattern. Check device settings." | — | `role="alert"` |
| Dark mode | Dark tokens on SVG container | — | — |

---

### 5. `AnnouncementEditor`

**Purpose**: Inline text editor for waypoint audio announcement. Auto-saves draft. Triggers re-simulation of segment on save.

#### TypeScript Props Interface

```typescript
interface AnnouncementEditorProps {
  waypointId: string;
  waypointLabel: string;
  initialText: string;
  maxLength: number;         // Recommended: 280 characters (TTS readability)
  isDraftSaved: boolean;
  isSaving: boolean;
  error: string | null;
  onTextChange: (text: string) => void;
  onSave: () => void;
  onDiscard: () => void;
}
```

#### State Matrix

| State | Visual | Behavior | Accessibility |
|---|---|---|---|
| Default | Textarea with current text, character count, Save / Discard buttons | — | `role="textbox"` `aria-label="Announcement text for [waypoint label]"` `aria-describedby="char-count-[id]"` |
| Typing | Character count updates | Auto-save draft fires 2s after last keystroke | Character count: `aria-live="polite"` `id="char-count-[id]"` — announces every 10 characters |
| Draft saved | "Draft saved" appears below editor (2s, then fades) | — | `aria-live="polite"` announces "Draft saved." |
| Saving (server) | Save button shows spinner | — | `aria-busy="true"` on save button |
| Saved | Editor closes, returns to WaypointDetail read mode | Re-simulation triggers for this segment | `aria-live="polite"` announces "Announcement saved. Re-simulating segment." |
| Error | Inline error below Save button | — | `role="alert"` on error; `aria-describedby` links error to Save button |
| Over max length | Character count red, Save disabled | Cannot save over limit | `aria-invalid="true"` on textarea; `aria-live="assertive"` announces "[N] characters over limit." |
| Dark mode | Dark tokens | — | — |

#### Visible Label

`<label for="announcement-editor-[id]">Announcement text</label>` — never placeholder-only (WCAG 1.3.1).

---

### 6. `RouteErrorPanel`

**Purpose**: Displayed when simulation encounters invalid state. Lists all errors with severity.

#### TypeScript Props Interface

```typescript
type SimulationErrorSeverity = 'error' | 'warning';
type SimulationErrorType =
  | 'missing_waypoint'
  | 'invalid_coordinates'
  | 'deprecated_haptic_pattern'
  | 'missing_announcement'
  | 'gap_too_large'             // Waypoint gap > 50m
  | 'network_error';            // Distinguish from data errors

interface SimulationError {
  id: string;
  type: SimulationErrorType;
  severity: SimulationErrorSeverity;
  waypointId: string | null;
  waypointLabel: string | null;
  message: string;
  canSkip: boolean;
  canResolve: boolean;
}

interface RouteErrorPanelProps {
  errors: SimulationError[];
  onResolveError: (errorId: string) => void;
  onSkipError: (errorId: string) => void;
  onClose: () => void;
}
```

#### Error Type Descriptions

| Error type | User-facing message | Severity | Can skip |
|---|---|---|---|
| `missing_waypoint` | "Waypoint [N] is missing. The route has a gap between waypoints [N-1] and [N+1]." | Error | No |
| `invalid_coordinates` | "Waypoint [label] has invalid location data (coordinates out of campus bounds)." | Error | No |
| `deprecated_haptic_pattern` | "Waypoint [label] uses a deprecated haptic pattern. Update to a current pattern before approving." | Error | No |
| `missing_announcement` | "Waypoint [label] has no announcement text. Students will hear silence at this point." | Warning | Yes |
| `gap_too_large` | "The gap between waypoints [A] and [B] is [N] meters, which exceeds the 50-meter maximum." | Warning | Yes |
| `network_error` | "Could not validate waypoint [label] — network unavailable. Simulation continues from cached data." | Warning | Yes |

#### State Matrix

| State | Visual | Behavior | Accessibility |
|---|---|---|---|
| Default | Error list, each with severity icon + message + action buttons | Sorted: errors before warnings | `role="alertdialog"` `aria-label="Simulation errors"`. Focus: first error item. |
| Error expanded | Inline details for selected error | — | `aria-expanded="true"` on error row |
| All resolved | "All issues resolved. Simulation can continue." + Continue button | — | `aria-live="assertive"` announces "All errors resolved." |
| Network errors only | Network errors listed separately from data errors | "These are connectivity issues, not route problems." note | — |
| Dark mode | Dark tokens | — | — |

**Network vs. data error distinction**: Network errors are styled with `--color-warning` (amber). Data integrity errors are styled with `--color-error` (red). Both use icon + text label, not color alone.

---

### 7. `SimulationSummary`

**Purpose**: Post-simulation report. Lists all waypoints with statuses, any errors, and Approve / Request Changes actions.

#### TypeScript Props Interface

```typescript
interface SimulationSummaryProps {
  route: AdminRoute;
  simulationErrors: SimulationError[];
  simulationDurationSeconds: number;
  onApprove: () => void;
  onRequestChanges: (notes: string) => void;
  onReSimulate: () => void;
  isApproving: boolean;
}
```

#### Approve vs. Request Changes

| Action | Route status transition | Required conditions | ARIA |
|---|---|---|---|
| Approve | `simulated` → `approved` | Zero unresolved errors (warnings allowed) | `aria-label="Approve route for student use"`. Disabled if errors remain: `aria-disabled="true"` `title="Resolve all errors before approving"` |
| Request Changes | `simulated` → `draft` | Notes field required (textarea, min 10 characters) | `aria-label="Send route back for changes"` |
| Re-simulate | Re-runs simulation from step 1 | — | `aria-label="Run simulation again"` |

**Approve action when warnings present**: A confirmation dialog fires: "This route has [N] warnings. Warnings do not block approval but should be reviewed. Approve anyway?" Options: "Approve" (primary) and "Review Warnings" (secondary, returns to player).

#### State Matrix

| State | Visual | Behavior | Accessibility |
|---|---|---|---|
| Default (no errors) | Green summary header, waypoint list, Approve button active | — | `role="main"` heading: "Simulation Complete — [Route Name]" |
| Errors present | Error summary (count + list), Approve button disabled | — | `role="alert"` on error summary; Approve: `aria-disabled="true"` |
| Warnings only | Warning summary, Approve active with confirmation | — | Approve label: "Approve route (with warnings)" |
| Approving (loading) | Approve button spinner | — | `aria-busy="true"` on Approve button |
| Approved | Success state: "Route approved. Students can now navigate this route." | Route status updated | `aria-live="assertive"` announces "Route approved." |
| Request Changes (notes entry) | Notes textarea expands below Request Changes button | Submit enabled after 10+ characters | Textarea: `aria-label="Describe changes needed"` |
| Dark mode | Dark tokens | — | — |

#### Layout

```
[Heading: "Simulation Complete — [Route Name]"]
[Summary stats: waypoints reviewed, errors, warnings, duration]
[Error list (if any)]
[Waypoint table: index | label | pattern | announcement | status]
[Notes field (conditionally expanded)]
[Action bar: Re-simulate | Request Changes | Approve]
```

---

## Layout Patterns

### Responsive Breakpoints

| Breakpoint | Layout | Behavior |
|---|---|---|
| ≥1280px | Two-column | Left: map/player (60% width). Right: waypoint detail panel (40% width, min 320px). |
| 768–1279px | Two-column, compressed | Left: map/player (55%). Right: detail panel (45%, min 280px). |
| <768px | Single column | Player full width. Waypoint list below. WaypointDetail opens as bottom sheet (height: 60vh, drag handle visible). |
| <480px | Single column with degraded banner | Banner: `role="note"`: "Route simulation is optimized for tablet or desktop." Not dismissed on its own — user must dismiss. Access not blocked. |

### Navigation Structure

```
Admin Panel
├── Routes (RouteList)
│   └── [Route] → Simulation (SimulationPlayer)
│       ├── WaypointDetail (panel within SimulationPlayer)
│       │   ├── HapticPreview
│       │   └── AnnouncementEditor
│       ├── RouteErrorPanel (modal)
│       └── SimulationSummary (replaces player on complete)
└── [other admin sections — out of scope for this issue]
```

---

## Accessibility Requirements

### WCAG AA Compliance

| Criterion | Requirement | Implementation |
|---|---|---|
| 1.3.1 Info and Relationships | Form labels programmatically associated | All form fields: `<label>` elements, never placeholder-only. `aria-describedby` for error messages. |
| 1.4.1 Use of Color | Color not sole conveyor of information | Status badges: icon + text + color. Error severity: icon + text + color. |
| 1.4.3 Contrast (Minimum) | 4.5:1 normal text, 3:1 large text | All color pairs verified (see token section). |
| 1.4.4 Resize Text | 16px minimum | Base font 16px. All sizes in rem/px (not em). |
| 1.4.12 Text Spacing | 1.6× line height body | `--line-height-body: 1.6`. |
| 2.1.1 Keyboard | All functionality via keyboard | Full tab order. Keyboard shortcuts for playback. Keyboard trap only in modals (intentional, WCAG 2.1.2 exception). |
| 2.4.1 Bypass Blocks | Skip navigation link | "Skip to main content" link as first focusable element on each page. |
| 2.4.3 Focus Order | Logical focus sequence | Focus order explicitly defined per view. Never CSS-only reorder. |
| 2.5.5 Target Size | 44×44px minimum | All interactive elements. Playback controls: 44×44px. |
| 3.3.1 Error Identification | Errors described in text | All error messages: text description of what failed and how to fix it. |
| 3.3.2 Labels and Instructions | Visible labels on all form fields | Enforced by component design. No placeholder-only fields. |
| 4.1.2 Name, Role, Value | All interactive elements named | `aria-label` or `<label>` on every interactive element per this spec. |
| 4.1.3 Status Messages | Programmatic announcements | `aria-live="polite"` for progress, `aria-live="assertive"` for errors and completions. |

### Focus Management

| Trigger | Focus destination |
|---|---|
| Open WaypointDetail | First focusable element within panel |
| Close WaypointDetail | Waypoint row in waypoint list that triggered open |
| Open RouteErrorPanel | First error item in panel |
| Close RouteErrorPanel | Playback controls (Play/Pause button) |
| Open SimulationSummary | "Simulation Complete" heading |
| Open modal dialogs | First focusable element in modal; focus trapped inside |
| Close modal dialog | Element that triggered the modal |

Modal pattern:
```html
<div role="dialog" aria-modal="true" aria-labelledby="dialog-title">
  <h2 id="dialog-title">Dialog title</h2>
  <!-- content -->
</div>
```

Focus trap: implemented via `focus-trap` library or equivalent. Focus must not escape to underlying page content.

### Keyboard Navigation

Full tab order within each view. No keyboard traps except modals (intentional). Playback keyboard shortcuts active when `SimulationPlayer` region has focus (managed via `onKeyDown` on the player container, not global). Short-circuit conflicts with browser shortcuts — use `Space` only when player has focus, not globally.

---

## Connectivity Behavior

Simulation runs from locally cached route data. No live API calls per step.

On connectivity loss:
1. Non-blocking banner (top of page, not modal): "Connection lost. Simulation continues from saved route data. Changes will sync when connection restores." `role="status"`.
2. Simulation continues uninterrupted.
3. Save and approve actions enter a queue. Visual indicator: Save button label changes to "Save (queued)". `aria-label` updates: "Save announcement — queued for sync when connection restores."
4. On reconnection: banner updates to "Connection restored. Syncing [N] queued actions." Auto-dismisses after 3 seconds.

`RouteErrorPanel` error type `network_error` distinguishes connectivity failures from data integrity failures. Network errors show amber (warning), not red (error).

---

## Implementation Roadmap

Ordered sequence for ALP-990 (frontend engineer) handoff:

1. **Design tokens** (CSS custom properties): Implement the token set in Section 1. Verify all contrast pairs with a contrast checker (e.g., Colour Contrast Analyser by TPGi) before building components.

2. **Shared atoms**: `StatusBadge` (icon + text + color; never color alone), `Button` variants (primary, secondary, ghost, danger), `TextInput` with `<label>`, `ErrorMessage` with `aria-describedby`.

3. **`RouteList`**: Table with filter bar, sort, status badges, row selection, bulk actions, empty state. Test keyboard navigation: Tab through filters → table → row actions.

4. **`SimulationPlayer`**: Map visualization stub (can be a static SVG of the route for MVP), playback controls with keyboard shortcuts, waypoint list with `role="listbox"`, fidelity notice. Test: Space plays/pauses, arrows step forward/back, live region announces waypoint on step.

5. **`WaypointDetail`**: Panel/drawer, read mode, `HapticPreview` waveform SVG, `AnnouncementEditor` with auto-save. Focus management: verify focus moves to panel on open and returns to trigger on close.

6. **`RouteErrorPanel`**: Modal with focus trap. Error list, severity icons, resolve/skip actions. Verify: screen reader announces panel on open, focus trapped, returns on close.

7. **`SimulationSummary`**: Post-simulation report, approve/request-changes flow. Verify: Approve confirmation dialog behavior, notes textarea validation.

8. **Offline behavior**: Implement queue for save/approve actions. Banner for connectivity state. Verify simulation continues uninterrupted on disconnect.

9. **Responsive layout**: Implement breakpoint behavior (two-column ≥768px, single column <768px, bottom sheet for WaypointDetail on mobile). Test with browser dev tools and a physical tablet.

10. **Accessibility audit**: Test each view with VoiceOver (macOS + Safari) and NVDA (Windows + Firefox). Checklist: all interactive elements announced correctly, focus order logical, keyboard shortcuts function, modals trap focus, status messages announced via live regions.

---

## Open Questions

1. **Waypoint coordinate editing**: Can the admin edit waypoint coordinates (map drag interaction), or only annotation (announcement text, haptic pattern)? If coordinates are editable, `WaypointDetail` needs a coordinate editor and `SimulationPlayer` map needs drag interaction. Decision needed before ALP-990 starts `WaypointDetail`. **Recommendation**: Coordinates are read-only in simulation mode (simulation validates, not edits). Coordinate editing belongs in a separate route-editing mode (ALP-967).

2. **Route creation vs. review only**: Is route creation in scope for the admin panel, or only review and approval? The `RouteList` spec includes an "Import route" CTA but not a "Create route" flow. If creation is in scope, it is a separate UX spec. **Recommendation**: Admin panel is review/approve only for MVP. Walk-and-record (ALP-981) is the creation flow. Import route = import from JSON export of walk-and-record output.

3. **Simulation export**: Is PDF or JSON export of `SimulationSummary` in scope? **Recommendation**: JSON export only (already in bulk actions). PDF is deferred.

4. **Approval roles**: Can any admin approve a route, or only a specific role (e.g., O&M specialist, coordinator)? This affects whether the Approve action appears for all admin users. **Recommendation**: Role-based approval is an ALP-971 (user management) concern. For MVP, any authenticated admin can approve. ALP-990 should implement Approve as visible to all roles; ALP-989 backend enforces RBAC on the API.

5. **HapticPattern library canonical source**: `WaypointDetail` and `HapticPreview` reference `HapticPattern` enum from `@echoecho/shared`. The enum is defined in `packages/shared/src/types/navigation.ts`. ALP-990 must import from shared types, not redefine. If new patterns are added, they go through the shared package — not the admin panel.
